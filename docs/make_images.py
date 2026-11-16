"""Regenerates the images used by README.md. Run from the repository root, after a bake:

    uv run doteshi bake
    uv run python docs/make_images.py
"""
from pathlib import Path

from PIL import Image

from doteshi import api
from doteshi.lint import sheets

DOCS = Path(__file__).resolve().parent
ROOT = DOCS.parent
api.load(ROOT / "content" / "demo")
api.load(ROOT / "examples")


def up(image, k):
    return image.resize((image.width * k, image.height * k), Image.NEAREST)


# Twelve seeds of each 16x16 sprite, six times enlarged.
cells = [api.render(id, 16, seed) for id in ("slime", "beetle", "mushroom", "flower", "gem") for seed in range(12)]
sheets.sheet(cells, cols=12, scale=6, pad=10).save(DOCS / "tiny.png")

# Big structures: 32x32 trees, six times enlarged, with the 16-pixel cell boundaries marked.
big = []
for seed in range(1, 7):
    tree = up(api.render("tree", 32, seed), 6)
    marked = Image.new("RGBA", tree.size, sheets.GROUND + (255,))
    for at in (0, 96, 191):
        marked.paste((84, 90, 102, 255), (at, 0, at + 1, 192))
        marked.paste((84, 90, 102, 255), (0, at, 192, at + 1))
    marked.alpha_composite(tree)
    big.append(marked)
sheets.sheet(big, cols=6, pad=10).save(DOCS / "structures.png")

# The same definitions painted large, to show what the pixels are resolved from.
picks = [("slime", 2), ("beetle", 3), ("mushroom", 11), ("tree", 5), ("flower", 3), ("gem", 2)]
sheets.sheet([api.render(id, 160, seed, "painted") for id, seed in picks], cols=6, pad=14).save(DOCS / "showcase.png")

# The README example at 16 pixels (as shipped), 32 pixels, and painted.
berry = [up(api.render("berry", 16, 2), 12), up(api.render("berry", 32, 2), 6), api.render("berry", 192, 2, "painted")]
sheets.sheet(berry, ["16px", "32px", "192px, painted"], cols=3, pad=14).save(DOCS / "berry.png")

# The baked demo atlas, three times enlarged, on a neutral ground so the transparent areas show.
atlas = ROOT / "out" / "atlas.png"
if atlas.exists():
    image = up(Image.open(atlas).convert("RGBA"), 3)
    ground = Image.new("RGBA", image.size, sheets.GROUND + (255,))
    ground.alpha_composite(image)
    ground.save(DOCS / "atlas.png")
for old in ("sizes.png",):
    (DOCS / old).unlink(missing_ok=True)
print("wrote", ", ".join(sorted(p.name for p in DOCS.glob("*.png"))))
