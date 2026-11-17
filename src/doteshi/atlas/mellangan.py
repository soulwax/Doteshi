"""Mellangan adapter: read its atlas through the declared bands, and bake sprites into named band cells.

A bake manifest places each sprite at a band and cell index, the addresses the game uses:

    [atlas]
    name = "doteshi"                  # lock and output file stem
    layout = "mellangan"
    bands = "../../atlas_layout.py"   # Mellangan's band table, relative to the manifest
    content = "content"               # sprite definitions, relative to the manifest
    style = "tiny"                    # optional, for every entry that does not name its own

    [[sprite]]
    id = "oddity_geode"
    band = "oddities b"
    index = 0                         # the first cell; a 32px sprite takes a 2x2 block of the band
    seed = 0                          # optional
    size = 16                         # optional, the sprite's first size by default
    style = "tiny"                    # optional

The bake writes <name>.png (the atlas size, clear except for baked cells) and <name>.json into the output folder,
and <name>.lock.json beside the manifest: every placement with a hash of its pixels, so a review sees which sprites
a code change touched. `check` leaves the lock alone and fails when it is stale.
"""
import argparse
import hashlib
import importlib.util
import json
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from .. import api
from . import lock as locks
from .bake import PIVOTS, Instance, render_all

LAYOUT = "mellangan"
ATLAS_KEYS = {"name", "layout", "bands", "content", "style"}
SPRITE_KEYS = {"id", "band", "index", "seed", "size", "style"}


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


@dataclass(frozen=True)
class Placement:
    instance: Instance
    band: BandInfo
    index: int


@dataclass(frozen=True)
class Manifest:
    path: Path
    name: str
    content: Path
    size: tuple
    placements: tuple

    @property
    def lock_path(self):
        return self.path.with_name(f"{self.name}.lock.json")


def atlas_size(band_list):
    return (max(b.origin[0] + b.columns * b.pitch for b in band_list),
            max(b.origin[1] + b.rows * b.pitch for b in band_list))


def read_manifest(path):
    path = Path(path)
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    atlas = data.get("atlas", {})
    extra = set(atlas) - ATLAS_KEYS
    if extra:
        raise ValueError(f"{path}: unknown [atlas] keys: {', '.join(sorted(extra))}")
    if atlas.get("layout") != LAYOUT or "bands" not in atlas:
        raise ValueError(f"{path}: a band manifest needs layout = \"{LAYOUT}\" and bands = <atlas_layout.py>")
    band_list = bands(path.parent / atlas["bands"])
    named = {b.name: b for b in band_list}
    content = path.parent / atlas.get("content", ".")
    api.load(content)
    placements, seen = [], set()
    for entry in data.get("sprite", []):
        extra = set(entry) - SPRITE_KEYS
        if extra:
            raise ValueError(f"{path}: unknown keys for {entry.get('id')}: {', '.join(sorted(extra))}")
        missing = {"id", "band", "index"} - set(entry)
        if missing:
            raise ValueError(f"{path}: a [[sprite]] entry lacks {', '.join(sorted(missing))}")
        id = entry["id"]
        if id not in api.REGISTRY:
            raise ValueError(f"{path}: no sprite named '{id}'")
        if entry["band"] not in named:
            raise ValueError(f"{path}: {id} names the unknown band '{entry['band']}'")
        size, seed = int(entry.get("size", api.REGISTRY[id].sizes[0])), int(entry.get("seed", 0))
        name = f"{id}_{size}_{seed}"
        if name in seen:
            raise ValueError(f"{path}: {name} is placed twice")
        seen.add(name)
        style = entry.get("style", atlas.get("style"))
        placements.append(Placement(Instance(name, id, size, seed, PIVOTS["bottom"], False, style),
                                    named[entry["band"]], int(entry["index"])))
    return Manifest(path, atlas.get("name", "doteshi"), content, atlas_size(band_list), tuple(placements))


def _cells(placement, px):
    """The cells one render covers, as (band index, x, y, piece), after checking it fits its band."""
    b, name = placement.band, placement.instance.name
    h, w = px.shape[:2]
    if w % b.cell or h % b.cell:
        raise ValueError(f"{name} is {w}x{h}; it must split into {b.cell}x{b.cell} cells")
    alpha = px[..., 3]
    if not alpha.any():
        raise ValueError(f"{name} is empty")
    if np.any((alpha != 0) & (alpha != 255)):
        raise ValueError(f"{name} has soft alpha; atlas cells take only clear or solid pixels")
    col, row, bc, br = placement.index % b.columns, placement.index // b.columns, w // b.cell, h // b.cell
    if placement.index < 0 or col + bc > b.columns or row + br > b.rows:
        raise ValueError(f"{name} ({bc}x{br} cells at {placement.index}) does not fit the "
                         f"{b.columns}x{b.rows} band {b.name}")
    g = (b.pitch - b.cell) // 2
    for r in range(br):
        for c in range(bc):
            yield (placement.index + r * b.columns + c, b.origin[0] + (col + c) * b.pitch + g,
                   b.origin[1] + (row + r) * b.pitch + g, px[r * b.cell:(r + 1) * b.cell, c * b.cell:(c + 1) * b.cell])


def compose(manifest, renders):
    """Draw every placement onto a clear page the size of the atlas. Returns the page and the lock records."""
    width, height = manifest.size
    page = np.zeros((height, width, 4), np.uint8)
    owner, records = {}, {}
    for p in manifest.placements:
        inst, px = p.instance, renders[p.instance.name]
        cells = list(_cells(p, px))
        for index, x, y, piece in cells:
            if (p.band.name, index) in owner:
                raise ValueError(f"{inst.name} and {owner[p.band.name, index]} share {p.band.name} cell {index}")
            owner[p.band.name, index] = inst.name
            page[y:y + p.band.cell, x:x + p.band.cell] = piece
        records[inst.name] = {"id": inst.id, "size": inst.size, "variant": inst.variant, "band": p.band.name,
                              "index": p.index, "cells": [c[0] for c in cells], "x": cells[0][1], "y": cells[0][2],
                              "w": px.shape[1], "h": px.shape[0], "living": bool(api.REGISTRY[inst.id].living),
                              "hash": hashlib.sha256(px.tobytes()).hexdigest()[:16]}
    return page, records


def changes(old, new):
    """What a bake did to the placements in a lock: new, changed pixels, moved, and removed sprites."""
    report = {"new": [], "changed": [], "moved": [], "removed": sorted(set(old) - set(new))}
    for name, r in sorted(new.items()):
        prev = old.get(name)
        if prev is None:
            report["new"].append(name)
            continue
        if (prev.get("band"), prev.get("index"), prev.get("cells")) != (r["band"], r["index"], r["cells"]):
            report["moved"].append(name)
        if prev.get("hash") != r["hash"]:
            report["changed"].append(name)
    return report


def bake_bands(manifest_path, out_dir, cache_dir=".cache/sprites", check=False):
    """Render a band manifest and write the page, its JSON and the lock. Returns (manifest, report).
    With check, the lock is left alone and a stale lock raises."""
    manifest = read_manifest(manifest_path)
    renders = render_all([p.instance for p in manifest.placements], manifest.content, cache_dir)
    page, records = compose(manifest, renders)
    old = locks.load(manifest.lock_path, LAYOUT)
    lock = {**locks.empty(LAYOUT), "pages": [list(manifest.size)], "sprites": records}
    report = changes(old["sprites"], records)
    text = locks.dump(lock)
    stale = not manifest.lock_path.exists() or manifest.lock_path.read_text(encoding="utf-8") != text
    if check and stale:
        found = "; ".join(f"{k} {', '.join(v)}" for k, v in report.items() if v) or "lock layout differs"
        raise ValueError(f"{manifest.lock_path.name} is stale ({found}); bake to update it")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    Image.fromarray(page, "RGBA").save(out_dir / f"{manifest.name}.png", compress_level=9)
    cells = [{"name": name, **{k: r[k] for k in ("id", "band", "index", "cells", "x", "y", "w", "h", "living")}}
             for name, r in sorted(records.items())]
    (out_dir / f"{manifest.name}.json").write_text(json.dumps(
        {"version": 1, "layout": LAYOUT, "size": list(manifest.size), "sprites": cells}, indent=1) + "\n",
        encoding="utf-8")
    if not check and stale:
        manifest.lock_path.write_text(text, encoding="utf-8", newline="\n")
    return manifest, report


def _import(a):
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


def _bake(a):
    try:
        manifest, report = bake_bands(a.manifest, a.out, None if a.no_cache else a.cache, a.check)
    except ValueError as error:
        print(f"doteshi: {error}", file=sys.stderr)
        return 1
    print(f"baked {len(manifest.placements)} sprites into {Path(a.out) / manifest.name}.png")
    for kind, names in report.items():
        if names:
            print(f"  {kind}: {', '.join(names)}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="doteshi.atlas.mellangan")
    sub = ap.add_subparsers(dest="command", required=True)
    imp = sub.add_parser("import", help="pin every cell of an atlas and check that it rebuilds pixel for pixel")
    imp.add_argument("--atlas", required=True)
    imp.add_argument("--layout", required=True)
    imp.add_argument("--out", default="out/mellangan-import")
    imp.set_defaults(run=_import)
    bk = sub.add_parser("bake", help="bake a band manifest into atlas cells")
    bk.add_argument("manifest")
    bk.add_argument("--out", default="out/mellangan")
    bk.add_argument("--cache", default=".cache/sprites")
    bk.add_argument("--no-cache", action="store_true")
    bk.add_argument("--check", action="store_true", help="fail on a stale lock instead of updating it")
    bk.set_defaults(run=_bake)
    a = ap.parse_args(argv)
    return a.run(a)


if __name__ == "__main__":
    sys.exit(main())
