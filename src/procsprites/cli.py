"""Command line: list, render, sheet, debug."""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

from . import api
from .core.color import linear_to_srgb, oklab_to_linear
from .lint import sheets
from .resolve import painted
from .shade.light import shade


def _seeds(text):
    """'7', '1..16' or '1,4,9' -> list of ints."""
    out = []
    for part in text.split(","):
        if ".." in part:
            a, b = part.split("..")
            out += range(int(a), int(b) + 1)
        else:
            out.append(int(part))
    return out


def _ids(names):
    ids = []
    for name in names:
        hits = [k for k in api.REGISTRY if k == name or k.startswith(name + ".") or k.startswith(name + "/")]
        if not hits:
            sys.exit(f"error: no sprite named '{name}'. Known: {', '.join(sorted(api.REGISTRY)) or 'none'}")
        ids += hits
    return ids


def _save(image, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    print(f"wrote {path} ({image.width}x{image.height})")


def cmd_list(args):
    for k, d in sorted(api.REGISTRY.items()):
        print(f"{k:28} sizes {list(d.sizes)}  variants {d.variants}  aspect {d.aspect}")


def cmd_render(args):
    for id in _ids(args.sprite):
        for seed in _seeds(args.seeds):
            _save(api.render(id, args.size, seed, args.style), Path(args.out) / f"{id}_{args.size}_{seed}.png")


def cmd_sheet(args):
    for id in _ids(args.sprite):
        seeds = _seeds(args.seeds)
        start = time.perf_counter()
        images = [api.render(id, args.size, s, args.style) for s in seeds]
        took = (time.perf_counter() - start) / len(images)
        out = sheets.sheet(images, [f"seed {s}" for s in seeds], args.cols, args.scale,
                           title=f"{id}  {args.size}px  ({took:.2f}s each)")
        _save(out, Path(args.out) / f"{id}_{args.size}.png")


def cmd_ladder(args):
    for id in _ids(args.sprite):
        sizes = [int(s) for s in args.sizes.split(",")]
        top = max(sizes)
        images = []
        for s in sizes:
            im = api.render(id, s, args.seed, args.style)
            k = max(1, 192 // s) if s < 96 else 1
            images.append(im.resize((im.width * k, im.height * k), 0) if k > 1 else im)
        _save(sheets.sheet(images, [f"{s}px" for s in sizes], len(sizes), title=f"{id}  seed {args.seed}"),
              Path(args.out) / f"{id}_ladder.png")


def cmd_debug(args):
    for id in _ids(args.sprite):
        gb = api.rasterize(id, args.size, args.seed, ss=2)
        from .resolve import painted
        rgb, alpha, layers = shade(gb)
        a3 = gb.A[..., None]
        height = np.where(gb.A > 0.01, gb.H, np.nan)
        lo, hi = np.nanmin(height), np.nanmax(height)
        views = [
            ("base colour", sheets.rgb(linear_to_srgb(np.maximum(oklab_to_linear(gb.lab), 0)) * a3)),
            ("height", sheets.grey(np.nan_to_num(height, nan=lo), lo, hi)),
            ("normal", sheets.rgb((layers["normal"] * 0.5 + 0.5) * a3)),
            ("occlusion", sheets.grey(layers["ao"] * gb.A, 0, 1)),
            ("key light reach", sheets.grey(layers["lit"] * gb.A, 0, 1)),
            ("exposure", sheets.grey(layers["exposure"] * gb.A, -3, 3)),
            ("lit, no outline", painted.to_image(*painted.downsample(np.clip(rgb, 0, 1), alpha, 1))),
            ("final", painted.resolve(gb).resize((gb.W, gb.Hn))),
        ]
        _save(sheets.sheet([v for _, v in views], [n for n, _ in views], 4, title=f"{id}  seed {args.seed}"),
              Path(args.out) / f"{id}_debug.png")


def _cells(args):
    """Reference sprites cut from a grid atlas: `cell` pixels square on a `pitch` pixel grid."""
    from PIL import Image
    ref = Image.open(args.reference).convert("RGBA")
    out = []
    for i in _seeds(args.cells):
        x, y = i % args.columns * args.pitch + args.origin, i // args.columns * args.pitch + args.origin
        out.append(ref.crop((x, y, x + args.cell, y + args.cell)))
    return out


def cmd_compare(args):
    """Generated sprites in among reference ones, at the reference's size, with both sets' measurements."""
    from .lint import metrics
    refs = _cells(args)
    made = [api.render(id, args.cell, s, args.style) for id in _ids(args.sprite) for s in _seeds(args.seeds)]
    mixed, labels = [], []
    for i in range(max(len(refs), len(made))):
        for group, tag in ((refs, "ref"), (made, "new")):
            if i < len(group):
                mixed.append(group[i])
                labels.append(tag)
    line = lambda name, m: (f"{name}: {m['colours']:.1f} colours, {m['orphans']:.1f} orphans, "
                            f"{m['fill']:.0%} filled, {m['outlined']:.0%} outlined")
    a, b = metrics.summary(refs), metrics.summary(made)
    print(line("reference", a))
    print(line("generated", b))
    out = sheets.sheet(mixed, labels, args.cols, args.scale, ground=tuple(args.ground),
                       title=line("ref", a) + "   |   " + line("new", b))
    _save(out, Path(args.out) / "compare.png")


def cmd_bake(args):
    from .atlas import bake
    start = time.perf_counter()
    files, st = bake.bake(args.manifest, args.out, repack=args.repack, prune=args.prune,
                          cache_dir=None if args.no_cache else ".cache/sprites",
                          report=lambda name: print(f"  rendered {name}"))
    pages = ", ".join(f"{w}x{h}" for w, h in st["pages"])
    print(f"baked {st['sprites']} sprites onto {len(st['pages'])} page(s) ({pages}), {st['fill']:.0%} full, "
          f"in {time.perf_counter() - start:.1f}s")
    print(f"  {st['new']} new, {st['kept']} kept in place, {st['moved']} moved, {st['retired']} retired")
    for name in st["files"]:
        print(f"  wrote {Path(args.out) / name}")
    print(f"  lock  {st['lock']}")


def cmd_verify(args):
    """Bake twice from scratch, with no cache, and compare every byte; then check the placements."""
    import shutil
    import tempfile
    from .atlas import bake
    settings, _ = bake.read_manifest(args.manifest)
    lock_path = Path(args.manifest).with_name(f"{settings.name}.lock.json")
    runs = []
    with tempfile.TemporaryDirectory() as tmp:
        for k in ("a", "b"):
            work = Path(tmp) / k
            work.mkdir()
            if lock_path.exists():
                shutil.copy(lock_path, work / lock_path.name)
            files, _ = bake.bake(args.manifest, work / "out", lock_path=work / lock_path.name, cache_dir=None)
            files["lock"] = (work / lock_path.name).read_bytes()
            runs.append(files)
    errors = [f"{name} differs between two bakes" for name in runs[0] if runs[0][name] != runs[1].get(name)]
    errors += bake.check(json.loads(runs[0]["lock"]))
    for e in errors:
        print(f"error: {e}")
    if errors:
        sys.exit(1)
    digest = hashlib.sha256(b"".join(runs[0][k] for k in sorted(runs[0]))).hexdigest()[:16]
    print(f"verified: two bakes are byte-identical ({len(runs[0])} files, sha256 {digest}); placements are sound")


def main(argv=None):
    p = argparse.ArgumentParser(prog="sprites", description="Procedural sprites of any size and kind.")
    p.add_argument("--content", default="content", help="folder of sprite definitions (default: content)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="list registered sprites").set_defaults(run=cmd_list)

    r = sub.add_parser("render", help="render single sprites to PNG files")
    r.add_argument("sprite", nargs="+")
    r.add_argument("--size", type=int, default=256)
    r.add_argument("--seeds", default="0")
    r.add_argument("--style", default=None)
    r.add_argument("--out", default="out/render")
    r.set_defaults(run=cmd_render)

    s = sub.add_parser("sheet", help="a sheet of seed variants per sprite")
    s.add_argument("sprite", nargs="+")
    s.add_argument("--size", type=int, default=256)
    s.add_argument("--seeds", default="1..16")
    s.add_argument("--cols", type=int, default=None)
    s.add_argument("--scale", type=int, default=1)
    s.add_argument("--style", default=None, help="tiny, pixel-hd, painted or relief (default: by size)")
    s.add_argument("--out", default="out/sheets")
    s.set_defaults(run=cmd_sheet)

    l = sub.add_parser("ladder", help="one sprite at a run of sizes, side by side")
    l.add_argument("sprite", nargs="+")
    l.add_argument("--sizes", default="16,32,48,64,128,256")
    l.add_argument("--seed", type=int, default=1)
    l.add_argument("--style", default=None)
    l.add_argument("--out", default="out/sheets")
    l.set_defaults(run=cmd_ladder)

    d = sub.add_parser("debug", help="the surface and lighting layers of one sprite")
    d.add_argument("sprite", nargs="+")
    d.add_argument("--size", type=int, default=256)
    d.add_argument("--seed", type=int, default=1)
    d.add_argument("--out", default="out/sheets")
    d.set_defaults(run=cmd_debug)

    c = sub.add_parser("compare", help="generated sprites among reference sprites cut from a grid atlas")
    c.add_argument("sprite", nargs="+")
    c.add_argument("--reference", required=True, help="a grid atlas image to cut reference sprites from")
    c.add_argument("--cells", default="0..23", help="which cells of the reference, e.g. 84..95,108..119")
    c.add_argument("--cell", type=int, default=16)
    c.add_argument("--pitch", type=int, default=18)
    c.add_argument("--origin", type=int, default=1)
    c.add_argument("--columns", type=int, default=24)
    c.add_argument("--seeds", default="1..8")
    c.add_argument("--style", default=None)
    c.add_argument("--cols", type=int, default=12)
    c.add_argument("--scale", type=int, default=6)
    c.add_argument("--ground", type=int, nargs=3, default=[104, 158, 84], help="background colour")
    c.add_argument("--out", default="out/sheets")
    c.set_defaults(run=cmd_compare)

    b = sub.add_parser("bake", help="bake a manifest into atlas.png, atlas.json and a C++ header")
    b.add_argument("manifest", nargs="?", default="content/manifest.toml")
    b.add_argument("--out", default="out")
    b.add_argument("--repack", action="store_true", help="discard the lock file and lay everything out again")
    b.add_argument("--prune", action="store_true", help="free the slots of sprites no longer in the manifest")
    b.add_argument("--no-cache", action="store_true", help="render everything again")
    b.set_defaults(run=cmd_bake)

    v = sub.add_parser("verify", help="bake twice and compare bytes; check placements")
    v.add_argument("manifest", nargs="?", default="content/manifest.toml")
    v.set_defaults(run=cmd_verify)

    args = p.parse_args(argv)
    if Path(args.content).is_dir():
        api.load(args.content)
    args.run(args)


if __name__ == "__main__":
    main()
