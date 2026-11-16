"""Regenerates the images used by README.md. Run from the repository root:

    uv run python docs/make_images.py
"""
from pathlib import Path

from PIL import Image

from doteshi import api
from doteshi.lint import sheets

DOCS = Path(__file__).resolve().parent
api.load(DOCS.parent / "content" / "demo")

PICKS = [("mushroom", 11), ("beetle", 13), ("tree", 5), ("flower", 3), ("gem", 2)]


def up(image, to=192):
    k = max(1, to // image.height)
    return image.resize((image.width * k, image.height * k), Image.NEAREST)


# One definition each, painted at 192px.
sheets.sheet([api.render(id, 192, seed) for id, seed in PICKS], cols=5, pad=16).save(DOCS / "showcase.png")

# The same definitions at 16, 32, 48 and 64 pixels, enlarged to a common size with hard pixels.
cells, labels = [], []
for id, seed in PICKS[:4]:
    for size in (16, 32, 48, 64):
        cells.append(up(api.render(id, size, seed)))
        labels.append(f"{id} {size}px")
sheets.sheet(cells, labels, cols=4, pad=14).save(DOCS / "sizes.png")

# Eight seeds of each at 16px, six times enlarged.
cells = [api.render(id, 16, seed) for id in ("mushroom", "beetle", "tree", "flower") for seed in range(1, 9)]
sheets.sheet(cells, cols=8, scale=6, pad=12).save(DOCS / "tiny.png")

# The baked demo atlas, on a neutral ground so the transparent areas show.
atlas = DOCS.parent / "out" / "atlas.png"
if atlas.exists():
    image = Image.open(atlas).convert("RGBA")
    ground = Image.new("RGBA", image.size, sheets.GROUND + (255,))
    ground.alpha_composite(image)
    ground.save(DOCS / "atlas.png")
print("wrote", ", ".join(sorted(p.name for p in DOCS.glob("*.png"))))
