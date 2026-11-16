"""The lock file: where every sprite sits. It is the one source for the image, the JSON and the C++ header, and
it is what keeps placements stable from one bake to the next."""
import json
from pathlib import Path

VERSION = 1


def empty(layout):
    return {"version": VERSION, "layout": layout, "pages": [], "sprites": {}}


def load(path, layout):
    path = Path(path)
    if not path.exists():
        return empty(layout)
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != VERSION:
        raise ValueError(f"{path} is lock version {data.get('version')}, this tool writes {VERSION}; bake with --repack")
    if data.get("layout") != layout:
        raise ValueError(f"{path} was baked with layout {data.get('layout')}, the manifest says {layout}; "
                         f"bake with --repack to lay the atlas out again")
    return data


def dump(data):
    return json.dumps(data, indent=1, sort_keys=True) + "\n"
