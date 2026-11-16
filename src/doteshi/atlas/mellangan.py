"""Mellangan adapter, step one: read its atlas through the declared bands and pin every cell where it is."""
import argparse
import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from . import lock as locks

LAYOUT = "mellangan"


@dataclass(frozen=True)
class BandInfo:
    name: str
    origin: tuple
    columns: int
    rows: int
    pitch: int
    cell: int


def _load_layout(layout_py):
    layout_py = Path(layout_py).resolve()
    folder = str(layout_py.parent)
    sys.path.insert(0, folder)
    try:
        spec = importlib.util.spec_from_file_location(f"_mellangan_{layout_py.stem}", layout_py)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(folder)
    return module


def bands(layout_py_path):
    m = _load_layout(layout_py_path)
    return [BandInfo(b.name, (b.x, b.y), b.cols, b.rows, m.CELL, m.TILE) for b in m.BANDS]


def _slug(name):
    return name.replace(" ", "-")


def cell_id(band, index):
    return f"mellangan/{_slug(band)}/{index}"


def import_atlas(atlas_png, layout_py):
    image = Image.open(atlas_png).convert("RGBA")
    px = np.asarray(image)
    covered = np.zeros(px.shape[:2], bool)
    records = []
    for b in bands(layout_py):
        for index in range(b.columns * b.rows):
            sx = b.origin[0] + index % b.columns * b.pitch
            sy = b.origin[1] + index // b.columns * b.pitch
            if sx + b.pitch > image.width or sy + b.pitch > image.height:
                raise ValueError(f"{b.name} cell {index} lies outside the {image.width}x{image.height} atlas")
            covered[sy:sy + b.pitch, sx:sx + b.pitch] = True
            slot = px[sy:sy + b.pitch, sx:sx + b.pitch]
            g = (b.pitch - b.cell) // 2
            records.append({"id": cell_id(b.name, index), "kind": "cell", "band": b.name, "index": index,
                            "x": sx + g, "y": sy + g, "w": b.cell, "h": b.cell,
                            "slot": [sx, sy, b.pitch, b.pitch], "empty": not slot.any()})
    records += _base_regions(px, covered)
    return image, records


def _base_regions(px, covered):
    """Pixels outside every band cell (the Kenney base area and anything between bands), as one bounding rectangle
    per run of rows that holds such pixels. Any nonzero channel counts, so hidden colour under alpha 0 is kept."""
    rest = ~covered & px.any(axis=2)
    rows = rest.any(axis=1)
    out, y = [], 0
    while y < len(rows):
        if not rows[y]:
            y += 1
            continue
        y1 = y
        while y1 < len(rows) and rows[y1]:
            y1 += 1
        cols = np.flatnonzero(rest[y:y1].any(axis=0))
        out.append((int(cols[0]), y, int(cols[-1]) + 1 - int(cols[0]), y1 - y))
        y = y1
    return [{"id": f"mellangan/base-region/{i}", "kind": "region", "band": "base-region", "index": i,
             "x": x, "y": y, "w": w, "h": h, "slot": [x, y, w, h], "empty": False}
            for i, (x, y, w, h) in enumerate(out)]


def write_lock(records, path, size=None):
    data = locks.empty(LAYOUT)
    if size:
        data["pages"] = [list(size)]
    for r in records:
        data["sprites"][r["id"]] = {"live": True, "pinned": True, "page": 0, "kind": r["kind"], "band": r["band"],
                                    "index": r["index"], "x": r["x"], "y": r["y"], "w": r["w"], "h": r["h"],
                                    "slot": dict(zip(("x", "y", "w", "h"), r["slot"])), "empty": r["empty"]}
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(locks.dump(data).encode("utf-8"))


def rebuild(atlas_png, records):
    src = np.asarray(Image.open(atlas_png).convert("RGBA"))
    out = np.zeros_like(src)
    for r in records:
        x, y, w, h = r["slot"]
        out[y:y + h, x:x + w] = src[y:y + h, x:x + w]
    return Image.fromarray(out, "RGBA")


def free_cells(records, band=None):
    return [r for r in records if r["kind"] == "cell" and r["empty"] and (band is None or r["band"] == band)]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="doteshi.atlas.mellangan")
    ap.add_argument("--atlas", required=True)
    ap.add_argument("--layout", required=True)
    ap.add_argument("--out", default="out/mellangan-import")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    image, records = import_atlas(a.atlas, a.layout)
    write_lock(records, out / "mellangan.lock.json", image.size)
    free = free_cells(records)
    (out / "free_cells.json").write_text(json.dumps(
        [{"id": r["id"], "band": r["band"], "index": r["index"], "x": r["x"], "y": r["y"]} for r in free], indent=1) + "\n")
    rebuilt = rebuild(a.atlas, records)
    rebuilt.save(out / "rebuilt.png")
    same = rebuilt.size == image.size and np.array_equal(np.asarray(rebuilt), np.asarray(image))
    cells = [r for r in records if r["kind"] == "cell"]
    print(f"cells {len(cells)}, base regions {len(records) - len(cells)}, free {len(free)}, "
          f"pixel-identical {'yes' if same else 'NO'}")
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
