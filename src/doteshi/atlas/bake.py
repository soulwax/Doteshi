"""Baking: manifest -> rendered sprites -> stable placements -> atlas.png, atlas.json, atlas.gen.hpp.

A manifest is a TOML file:

    [atlas]
    name = "atlas"            # output file stem
    layout = "packed"         # "packed" (mixed sizes, trimmed) or "grid" (uniform cells, numbered)
    padding = 2               # packed: transparent gap round every sprite
    max_size = 2048           # packed: largest page edge before a new page is started
    namespace = "atlas::gen"  # for the C++ header
    content = "."             # folder of sprite definitions, relative to the manifest
    cell = 16                 # grid: sprite size
    gutter = 1                # grid: transparent border inside each cell
    columns = 24              # grid: cells per row
    style = "tiny"            # style for every entry that does not name its own

    [[sprite]]
    id = "mushroom"
    size = 128                # or sizes = [64, 128]
    variants = 8              # seeds 0..7, or seeds = [3, 5, 11]
    pivot = "bottom"          # "bottom", "center" or [x, y] as fractions of the sprite
    tile = false              # true: repeat edge pixels into the padding instead of leaving it clear
    style = "pixel-hd"        # tiny, pixel-hd, painted or relief; by default it follows the size

The lock file sits beside the manifest as <name>.lock.json. Sprites already in it keep their place; new ones take
free space. Sprites dropped from the manifest keep their slot reserved until a bake with prune or repack.
"""
import hashlib
import tomllib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from .. import api
from . import bleed, export
from . import lock as locks
from .pack import place

PIVOTS = {"bottom": (0.5, 1.0), "center": (0.5, 0.5), "top": (0.5, 0.0)}


@dataclass(frozen=True)
class Instance:
    name: str
    id: str
    size: int
    variant: int
    pivot: tuple
    tile: bool
    style: str = None


@dataclass
class Settings:
    name: str = "atlas"
    layout: str = "packed"
    padding: int = 2
    max_size: int = 2048
    namespace: str = "atlas::gen"
    content: str = "."
    cell: int = 16
    gutter: int = 1
    columns: int = 24
    style: str = None


def read_manifest(path):
    path = Path(path)
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    known = Settings.__dataclass_fields__
    extra = set(data.get("atlas", {})) - set(known)
    if extra:
        raise ValueError(f"{path}: unknown [atlas] keys: {', '.join(sorted(extra))}")
    settings = Settings(**data.get("atlas", {}))
    if settings.layout not in ("packed", "grid"):
        raise ValueError(f"{path}: layout must be 'packed' or 'grid', not '{settings.layout}'")
    api.load(path.parent / settings.content)
    instances, seen = [], set()
    for entry in data.get("sprite", []):
        id = entry["id"]
        if id not in api.REGISTRY:
            raise ValueError(f"{path}: no sprite named '{id}'. Known: {', '.join(sorted(api.REGISTRY))}")
        sizes = entry.get("sizes") or [entry.get("size") or api.REGISTRY[id].sizes[0]]
        seeds = entry.get("seeds") or list(range(entry.get("variants", 1)))
        pivot = entry.get("pivot", "bottom")
        pivot = PIVOTS[pivot] if isinstance(pivot, str) else tuple(pivot)
        for size in sizes:
            for seed in seeds:
                name = f"{id}_{size}_{seed}"
                if name in seen:
                    raise ValueError(f"{path}: {name} is listed twice")
                seen.add(name)
                instances.append(Instance(name, id, int(size), int(seed), pivot, bool(entry.get("tile", False)),
                                          entry.get("style", settings.style)))
    return settings, instances


def _source_key(content):
    """One hash over the engine and the content: any code change makes every cached render stale."""
    h = hashlib.sha256()
    for root in (Path(__file__).resolve().parents[1], Path(content).resolve()):
        for file in sorted(root.rglob("*.py")):
            h.update(file.relative_to(root).as_posix().encode())
            h.update(file.read_bytes())
    return h.hexdigest()[:16]


def render_all(instances, content, cache_dir=None, report=None):
    """Render every instance to an RGBA array, reusing cached renders when the code has not changed."""
    key = _source_key(content) if cache_dir else None
    out = {}
    for inst in instances:
        file = Path(cache_dir) / key / f"{inst.name}.png" if cache_dir else None
        if file is not None and file.exists():
            out[inst.name] = np.asarray(Image.open(file).convert("RGBA"))
            continue
        image = api.render(inst.id, inst.size, inst.variant, inst.style)
        if file is not None:
            file.parent.mkdir(parents=True, exist_ok=True)
            image.save(file)
        if report:
            report(inst.name)
        out[inst.name] = np.asarray(image)
    return out


def _record(inst, px, page, x, y, ox, oy, slot):
    sh, sw = px.shape[:2]
    return {"id": inst.id, "size": inst.size, "variant": inst.variant, "live": True, "page": page,
            "x": x, "y": y, "w": slot["cw"], "h": slot["ch"], "ox": ox, "oy": oy, "sw": sw, "sh": sh,
            "px": round(inst.pivot[0] * sw - ox, 2), "py": round(inst.pivot[1] * sh - oy, 2),
            "living": bool(api.REGISTRY[inst.id].living),
            "slot": [slot["x"], slot["y"], slot["w"], slot["h"]], "hash": slot["hash"]}


def layout_packed(settings, instances, renders, lock):
    pad = settings.padding
    old = lock["sprites"]
    cuts, need, kept, stats = {}, {}, {}, {"new": 0, "kept": 0, "moved": 0}
    for inst in instances:
        crop, ox, oy = bleed.trim(renders[inst.name])
        cuts[inst.name] = (crop, ox, oy)
        want = (crop.shape[1] + 2 * pad, crop.shape[0] + 2 * pad)
        prev = old.get(inst.name)
        if prev and prev["slot"][2] >= want[0] and prev["slot"][3] >= want[1]:
            kept[inst.name] = (prev["page"], *prev["slot"])
            stats["kept"] += 1
        else:
            need[inst.name] = want
            stats["moved" if prev else "new"] += 1
    # Slots of sprites no longer in the manifest stay reserved, as do outgrown ones (they become holes).
    reserved = dict(kept)
    for name, prev in old.items():
        if name not in kept:
            reserved[f"\0{name}"] = (prev["page"], *prev["slot"])
    placed, pages = place(need, reserved, lock["pages"], settings.max_size)
    sprites = {}
    for name, prev in old.items():
        if name not in cuts:
            sprites[name] = {**prev, "live": False}
    for inst in instances:
        crop, ox, oy = cuts[inst.name]
        page, sx, sy, sw, sh = placed[inst.name]
        slot = {"x": sx, "y": sy, "w": sw, "h": sh, "cw": crop.shape[1], "ch": crop.shape[0],
                "hash": hashlib.sha256(crop.tobytes()).hexdigest()[:16]}
        sprites[inst.name] = _record(inst, renders[inst.name], page, sx + pad, sy + pad, ox, oy, slot)
    return {"version": locks.VERSION, "layout": "packed", "pages": [list(p) for p in pages], "sprites": sprites}, stats


def layout_grid(settings, instances, renders, lock):
    """Uniform cells, numbered row by row. A sprite larger than one cell must be a whole number of cells each
    way; it is cut into cells and takes a block of them, so every piece is an ordinary cell to the game."""
    cell, pitch, cols = settings.cell, settings.cell + 2 * settings.gutter, settings.columns
    old = lock["sprites"]
    sprites = {name: {**prev, "live": False} for name, prev in old.items()}
    block = lambda index, bc, br: {index + r * cols + c for r in range(br) for c in range(bc)}
    taken = set()
    for prev in old.values():
        taken |= block(prev["index"], prev.get("cols", 1), prev.get("rows", 1))
    stats = {"new": 0, "kept": 0, "moved": 0}
    for inst in instances:
        px = renders[inst.name]
        h, w = px.shape[:2]
        if w % cell or h % cell:
            raise ValueError(f"{inst.name} is {w}x{h}; every sprite in this grid must be a multiple of {cell} "
                             f"pixels each way, so that it splits cleanly into {cell}x{cell} cells")
        bc, br = w // cell, h // cell
        if bc > cols:
            raise ValueError(f"{inst.name} is {bc} cells wide; the grid has {cols} columns")
        prev = old.get(inst.name)
        if prev and (prev.get("cols", 1), prev.get("rows", 1)) == (bc, br):
            index = prev["index"]
            stats["kept"] += 1
        else:
            index = 0
            while index % cols + bc > cols or block(index, bc, br) & taken:
                index += 1
            taken |= block(index, bc, br)
            stats["moved" if prev else "new"] += 1
        x, y = index % cols * pitch, index // cols * pitch
        slot = {"x": x, "y": y, "w": bc * pitch, "h": br * pitch, "cw": cell, "ch": cell,
                "hash": hashlib.sha256(px.tobytes()).hexdigest()[:16]}
        sprites[inst.name] = {**_record(inst, px, 0, x + settings.gutter, y + settings.gutter, 0, 0, slot),
                              "index": index, "cols": bc, "rows": br}
    rows = (max(taken) // cols + 1) if taken else 1
    return {"version": locks.VERSION, "layout": "grid", "pages": [[cols * pitch, rows * pitch]],
            "sprites": sprites}, stats


def compose(settings, instances, renders, lock):
    """Draw every live sprite onto its page."""
    pad = settings.padding if settings.layout == "packed" else settings.gutter
    pages = [np.zeros((h, w, 4), np.uint8) for w, h in lock["pages"]]
    for inst in instances:
        s = lock["sprites"][inst.name]
        if settings.layout == "grid":
            cell, pitch = settings.cell, settings.cell + 2 * settings.gutter
            for r in range(s["rows"]):
                for c in range(s["cols"]):
                    piece = renders[inst.name][r * cell:(r + 1) * cell, c * cell:(c + 1) * cell]
                    x, y = s["x"] + c * pitch, s["y"] + r * pitch
                    if inst.tile:
                        pages[0][y - pad:y + cell + pad, x - pad:x + cell + pad] = bleed.extrude(piece, pad)
                    else:
                        pages[0][y:y + cell, x:x + cell] = piece
            continue
        px = renders[inst.name][s["oy"]:s["oy"] + s["h"], s["ox"]:s["ox"] + s["w"]]
        if inst.tile:
            px = bleed.extrude(px, pad)
            pages[s["page"]][s["y"] - pad:s["y"] + s["h"] + pad, s["x"] - pad:s["x"] + s["w"] + pad] = px
        else:
            pages[s["page"]][s["y"]:s["y"] + s["h"], s["x"]:s["x"] + s["w"]] = px
    # Grid cells keep a strictly clear gutter (the game samples them unfiltered); packed sprites get colour bleed.
    return [bleed.bleed(p, pad) for p in pages] if settings.layout == "packed" else pages


def bake(manifest, out_dir, lock_path=None, repack=False, prune=False, cache_dir=".cache/sprites", report=None):
    """Bake a manifest. Returns (files written, stats). The lock file is updated in place."""
    manifest = Path(manifest)
    settings, instances = read_manifest(manifest)
    lock_path = Path(lock_path) if lock_path else manifest.with_name(f"{settings.name}.lock.json")
    lock = locks.empty(settings.layout) if repack else locks.load(lock_path, settings.layout)
    if prune:
        names = {i.name for i in instances}
        lock["sprites"] = {k: v for k, v in lock["sprites"].items() if k in names}
    renders = render_all(instances, manifest.parent / settings.content, cache_dir, report)
    layout = layout_packed if settings.layout == "packed" else layout_grid
    lock, stats = layout(settings, instances, renders, lock)
    pages = compose(settings, instances, renders, lock)
    grid = None if settings.layout != "grid" else {"cell": settings.cell, "pitch": settings.cell + 2 * settings.gutter,
                                                     "columns": settings.columns}
    files = export.files(settings.name, settings.namespace, settings.layout, settings.padding, lock, pages, grid)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (out_dir / name).write_bytes(data)
    lock_path.write_bytes(locks.dump(lock).encode("utf-8"))
    used = sum(s["slot"][2] * s["slot"][3] for s in lock["sprites"].values())
    stats.update(pages=[tuple(p) for p in lock["pages"]], sprites=len(instances),
                 retired=sum(not s["live"] for s in lock["sprites"].values()),
                 fill=used / max(1, sum(p[0] * p[1] for p in lock["pages"])), files=sorted(files), lock=lock_path)
    return files, stats


def check(lock):
    """Structural faults in a set of placements: overlaps and anything off its page."""
    from .pack import overlaps
    errors = []
    items = sorted(lock["sprites"].items())
    for i, (name, s) in enumerate(items):
        x, y, w, h = s["slot"]
        pw, ph = lock["pages"][s["page"]]
        if x < 0 or y < 0 or x + w > pw or y + h > ph:
            errors.append(f"{name} lies outside page {s['page']}")
        for other, t in items[i + 1:]:
            if s["page"] == t["page"] and overlaps(s["slot"], t["slot"]):
                errors.append(f"{name} overlaps {other}")
    return errors
