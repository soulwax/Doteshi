"""Command line: list, render, sheet, debug."""
import argparse
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
            _save(api.render(id, args.size, seed), Path(args.out) / f"{id}_{args.size}_{seed}.png")


def cmd_sheet(args):
    for id in _ids(args.sprite):
        seeds = _seeds(args.seeds)
        start = time.perf_counter()
        images = [api.render(id, args.size, s) for s in seeds]
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
            im = api.render(id, s, args.seed)
            k = max(1, top // s) if s < 96 else 1
            images.append(im.resize((im.width * k, im.height * k), 0) if k > 1 else im)
        _save(sheets.sheet(images, [f"{s}px" for s in sizes], len(sizes), title=f"{id}  seed {args.seed}"),
              Path(args.out) / f"{id}_ladder.png")


def cmd_debug(args):
    for id in _ids(args.sprite):
        gb = api.rasterize(id, args.size, args.seed, ss=2)
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


def main(argv=None):
    p = argparse.ArgumentParser(prog="sprites", description="Procedural sprites of any size and kind.")
    p.add_argument("--content", default="content", help="folder of sprite definitions (default: content)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="list registered sprites").set_defaults(run=cmd_list)

    r = sub.add_parser("render", help="render single sprites to PNG files")
    r.add_argument("sprite", nargs="+")
    r.add_argument("--size", type=int, default=256)
    r.add_argument("--seeds", default="0")
    r.add_argument("--out", default="out/render")
    r.set_defaults(run=cmd_render)

    s = sub.add_parser("sheet", help="a sheet of seed variants per sprite")
    s.add_argument("sprite", nargs="+")
    s.add_argument("--size", type=int, default=256)
    s.add_argument("--seeds", default="1..16")
    s.add_argument("--cols", type=int, default=None)
    s.add_argument("--scale", type=int, default=1)
    s.add_argument("--out", default="out/sheets")
    s.set_defaults(run=cmd_sheet)

    l = sub.add_parser("ladder", help="one sprite at a run of sizes, side by side")
    l.add_argument("sprite", nargs="+")
    l.add_argument("--sizes", default="16,24,32,48,64,128,256")
    l.add_argument("--seed", type=int, default=1)
    l.add_argument("--out", default="out/sheets")
    l.set_defaults(run=cmd_ladder)

    d = sub.add_parser("debug", help="the surface and lighting layers of one sprite")
    d.add_argument("sprite", nargs="+")
    d.add_argument("--size", type=int, default=256)
    d.add_argument("--seed", type=int, default=1)
    d.add_argument("--out", default="out/sheets")
    d.set_defaults(run=cmd_debug)

    args = p.parse_args(argv)
    if Path(args.content).is_dir():
        api.load(args.content)
    args.run(args)


if __name__ == "__main__":
    main()
