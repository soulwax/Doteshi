# TODO

Plan for ProceduralSprites: a program that generates detailed, organic sprites of any size and any kind from code, and bakes them into `atlas.png` with generated metadata.

Tasks are small and independent where possible. Each names the files it owns and ends with a "Done when" check, so agents can take them separately. Milestones are ordered; tasks inside a milestone can run in parallel unless a task says otherwise.

## Status (2026-11-16)

- **M0 done. M1 built and waiting at its review gate.** Sheets to judge: `out/sheets/mushroom_256.png`, `out/sheets/beetle_256.png`.
- **M3 mostly done** (it does not depend on the gates): `uv run sprites bake` writes `out/atlas.png`, `out/atlas.json` and `out/atlas.gen.hpp` from `content/manifest.toml`. Imports and companion maps are still open.
- **M2 not started.** Below about 48px the painted resolver only blurs; see `out/sheets/beetle_ladder.png`.
- 50 tests pass (`uv run pytest`). `uv run sprites verify` confirms two bakes are byte-identical.
- Nothing is committed yet.

Commands: `sprites list | render | sheet | ladder | debug | bake | verify`.

## Goal and bar

- **Any size.** One sprite definition renders at 16px, 64px, 256px or larger, and each size is resolved for that size, not scaled from another.
- **Any kind.** Creatures, plants, fungi, minerals, items, buildings, ground tiles, effects, emblems. A new kind is a new library module, never an engine change.
- **Beautiful.** Form, material and light are computed. At large sizes the target is the bas-relief fidelity of Mellangan's `res/achievements.png`, straight from the renderer with no image model. At 16px the target is to sit beside Kenney Tiny Town and Tiny Dungeon tiles without standing out.
- **Organic.** Structure comes from growth processes and soft joins, not assembled primitives.
- **Much better than the inspiration.** The reference is `C:\Users\soulwax\Workspace\c++\mellangan\tools` (about 21k lines of `make_*.py`). See "Carried over" and "Replaced" below.

## Decisions already made

- **Stack:** Python, numpy and Pillow only, run through `uv` with a committed `uv.lock`. No scipy. Sprites are authored as Python code.
- **Standalone tool.** Mellangan is the first consumer through an adapter (M8), not the host repo.
- **Package name** `procsprites`, command `sprites`.
- **Sprite space:** origin at canvas centre, x right, y down, the canvas height spans -1 to 1, width scales by aspect ratio. Ground line at y = +1.
- **Light:** key light from the top left, matching `LIGHT = (-0.6, -0.8)` in Mellangan's `sprite_kit.py`.
- **Randomness:** an own hash-based generator seeded from `(sprite id, variant, stream name)`. numpy's random module is never used, so results do not depend on numpy's distribution code.
- **Determinism promise:** byte-identical output on the same machine with the same lock file. Cross-platform identity is a goal checked in M9, not a promise.

## Carried over from Mellangan's tools

- OKLab ramps grown from a base colour: lightness step 0.135, shadows hue-shifted toward 300°, lights toward 85°, optional snapping onto a reference palette (`sprite_kit.ramp`).
- Outline colour `(63, 38, 49)` and the 16px sprite in an 18px cell with a 1px gutter, as the `tiny` style profile.
- Lint numbers measured against reference art (Kenney characters average 7 colours and 4.7 orphan pixels).
- Double-build determinism check (`make_assets.py --verify`).
- Drafts and comparison sheets before the real atlas is touched.
- Stable cell indices: the game addresses sprites by index.
- Motion families from `make_motion_frames.py`: biped, heavy, quadruped, crawler, flyer, spirit, blob, rooted.

## Replaced

- Hand-typed 16×16 character maps become parts with form and material.
- Tones placed by hand become lighting on a relief surface.
- Band offsets repeated in `atlas_layout.py`, `make_assets.py` and `src/Atlas.hpp` (checked by regex) become one lock file with generated outputs. Evidence the old way has drifted: `res/atlas.yaml` says 432×1488, the atlas is 432×2352.
- Animation by shifting pixel rows becomes re-rendering a posed rig.
- Pure-Python pixel loops become vectorised numpy fields.
- Helpers redefined per script (`shade`, `draw`, `paint`, `remap`, `lerp` each exist four or five times) become one engine.

## Layout

```
pyproject.toml, uv.lock
src/procsprites/
  core/      rng.py  noise.py  sdf.py  curves.py  color.py  gbuffer.py
  form/      profile.py  part.py  scene.py  rig.py
  grow/      branch.py  phyllotaxis.py  cells.py  rd.py  strokes.py
  shade/     light.py  material.py  detail.py  weather.py
  resolve/   style.py  painted.py  pixel.py
  atlas/     pack.py  lock.py  bleed.py  export.py  imports.py
  lint/      metrics.py  sheets.py
  library/   creatures/  plants/  minerals/  items/  buildings/  tiles/  fx/  emblems/
  cli.py
content/     demo sprite sets and manifest.toml
tests/       unit tests and golden hashes
out/         atlas.png  atlas.json  Atlas.gen.hpp  sheets/   (not committed)
```

---

## M0. Skeleton

- [x] **Create the project.** `pyproject.toml` with numpy and Pillow pinned, `uv.lock`, `src/procsprites/` package, `sprites` entry point, `.gitignore` covering `out/` and caches, `git init`. Done when `uv run sprites --help` prints the command list.
- [x] **Test harness.** `tests/` with pytest and a `uv run pytest` path. Done when one placeholder test passes.
- [x] **Hash generator.** `core/rng.py`: splitmix64-style generator with named sub-streams, `float`, `int`, `choice`, `gauss`, `on_disc`. Done when a golden-value test pins the first 16 outputs of three seeds. *The test pins the first 4 outputs of three seeds, not 16.*
- [x] **Sheet writer, minimal.** `lint/sheets.py`: tile images onto a labelled background at an integer scale. Needed by every later review. Done when `sprites sheet` writes a PNG grid from a list of images.

## M1. Beauty slice (review gate)

The main risk is whether the renderer looks good. This milestone proves it on two subjects before anything else is built. Subjects: one mushroom and one beetle, 256×256, painted style.

- [x] **Colour.** `core/color.py`: sRGB, linear and OKLab conversions as numpy functions; `ramp(base, n)` ported from `sprite_kit.py`; a continuous ramp lookup `tone(base, light)` for painted output. Done when the ported `ramp` reproduces `sprite_kit.ramp` exactly for ten test colours.
- [x] **Noise.** `core/noise.py`: gradient noise, fBm, ridged noise, Worley cells, each with a tileable variant and an integer seed. Done when tileable variants match at opposite edges to within 1e-6 and golden hashes pin each function.
- [x] **Distance shapes.** `core/sdf.py`: circle, ellipse, box, rounded box, capsule, tapered capsule, polygon, and a variable-radius curve; smooth union, subtract and intersect; mirror, radial repeat, domain warp. Each evaluates on a numpy grid and exposes a bounding box so it is only evaluated where it can matter. Done when unit tests check signs and distances at known points for every shape. *Radial repeat is not written yet; lathe (solid of revolution) and leaf were added.*
- [x] **Curves.** `core/curves.py`: Catmull-Rom and cubic Bézier with arc-length parameterisation, tangents and normals. Done when arc-length sampling is uniform to within 1 percent on a test curve.
- [x] **Height profiles.** `form/profile.py`: flat, dome, bevel, ridge, tube, each mapping edge distance to height. Done when a rendered height sheet shows the five profiles on a disc.
- [x] **Surface buffer.** `core/gbuffer.py`: per-pixel coverage, height, normal, material id, part id, part coordinates (along and across), edge distance, glow. Parts composite by height with soft blending where a smooth join is requested. Done when debug views of each channel can be written as images. *`sprites debug <id>` writes the channel views.*
- [x] **Parts and scenes.** `form/part.py`, `form/scene.py`: a part is shape + profile + material + detail stack + priority; a scene holds parts, supports mirror with asymmetry jitter, and rasterises to a surface buffer at any resolution. Done when a three-part test scene renders at 64, 256 and 1024 with identical framing.
- [x] **Materials.** `shade/material.py`: base colour, roughness, shine, metal, translucency, glow, tone count. Presets: matte, glossy, metal, translucent, glowing. Done when a material-ball sheet shows the five presets on a dome.
- [x] **Lighting.** `shade/light.py`: key light, fill, cool rim; shadows cast across the height field toward the light; ambient occlusion from the height field; highlights per material; light wrap and back tint for translucent materials; glow that spills onto neighbours. Light indexes the ramp, it does not multiply RGB. Done when a sphere-on-slab test shows a cast shadow, contact darkening and a rim.
- [x] **Surface detail as bumps.** `shade/detail.py`: ridges along a part, scales, pores, grain, scratches, hammer marks, each perturbing height before normals are computed, each with a size in sprite units. Done when a sheet shows each detail on a lit dome and it reads as relief. *Lives in `shade/detail.py` as patterns usable for relief or colour: grain, ridges, rings, stripes, spots, speckle, pores, cracks, facets, dimples, scales, scratches, mottle, lumps.*
- [x] **Painted resolver.** `resolve/painted.py`: supersample, resolve to straight-alpha RGBA with clean edges, optional tinted outline. Done when edges show no stair-stepping at 256px and no dark fringe on a light background.
- [x] **Authoring API.** `@sprite(id, sizes, variants)` decorator and a registry in `form/scene.py`. Done when the two subjects are each under 60 lines of definition. *The subjects came out longer than the 60-line target: about 80 lines for the mushroom and 65 for the beetle, because they carry more parts than planned.*
- [x] **Subjects.** `content/demo/mushroom.py`, `content/demo/beetle.py`. Done when `sprites sheet demo --size 256 --seeds 1..16` writes two sheets of 16 variants.
- [ ] **Review gate.** The user approves the two sheets, or lists what falls short. Do not start M2 until this is settled.

## M2. Small sizes (review gate)

- [ ] **Style profiles.** `resolve/style.py`: `tiny` (16 to 24px, Kenney-compatible), `pixel-hd` (32 to 64px), `painted` (96px and up), `relief` (emblems). A profile sets tone count, outline, palette snapping, dither, edge handling. Done when a profile is chosen from size by default and can be forced per sprite.
- [ ] **Detail budget.** Every detail and part carries a size; anything under 1.5 output pixels is dropped before rasterising. Done when the size ladder shows detail appearing step by step with no noise at 16px. *Partly done: patterns under 1.5 pixels are dropped and tested; whole parts are not dropped yet.*
- [ ] **Pixel resolver.** `resolve/pixel.py`, working from an 8× surface buffer:
  - coverage by threshold, with thin parts widened to at least one pixel;
  - one material per pixel by majority;
  - light quantised to the material's ramp tones;
  - cluster cleanup: remove orphan pixels, merge one-pixel tone islands, straighten jagged tone borders;
  - 1px outline in the profile's outline colour, with soft parts exempt.
  Done when the beetle and mushroom at 16px pass the `tiny` lint thresholds from M4.
- [ ] **Key features.** Parts marked `keep=True` (eyes, teeth, gem glints) snap to whole pixels and are never dropped. Done when the beetle's eyes are one clean pixel each at 16px for all 16 seeds.
- [ ] **Per-size override.** A sprite may supply a hand-drawn character map or a separate definition for a named size. Done when one demo sprite uses a hand-drawn 16px cell and generated larger sizes.
- [x] **Size ladder sheet.** `sprites ladder <id>` renders 16, 24, 32, 48, 64, 128, 256 side by side, small sizes shown enlarged. Done when it works for any registered sprite.
- [ ] **Reference comparison.** A sheet placing generated 16px sprites among Kenney Tiny Town and Tiny Dungeon tiles. Done when the sheet is written from a path to the Kenney pack.
- [ ] **Review gate.** The user approves the 16px and 32px results on the comparison sheet.

## M3. Atlas baker

- [x] **Manifest.** `content/manifest.toml`: sprite sets, sizes, variant counts, style, layout group, padding. Done when `sprites bake content/manifest.toml` resolves the full list of sprite instances.
- [x] **Trim and pivot.** Trim transparent borders, record trim offset, original size and pivot (default: bottom centre for standing sprites, centre for the rest). Done when round-tripping trim data reconstructs the untrimmed image.
- [x] **Grid layout.** `atlas/pack.py`: uniform cells with gutters and append-only indices per group. Done when a 16px set lands in an 18px-pitch, 24-column grid matching Mellangan's `cell_position`.
- [x] **Packed layout.** MaxRects with a deterministic sort, power-of-two growth, multiple pages on overflow. Done when tests confirm no overlap, everything in bounds, and identical output on repeat runs.
- [x] **Lock file.** `atlas/lock.py`: `atlas.lock.json` records page, rectangle, index and content hash per sprite. Existing entries never move; new sprites take free space; `--repack` rebuilds from scratch. Done when adding ten sprites to a baked atlas changes no existing rectangle.
- [x] **Edges.** `atlas/bleed.py`: edge extrusion for tiles, transparent padding for sprites, colour bleed into transparent pixels so filtering shows no dark halo. Done when a bilinear-sampled test shows no seam between tiles and no fringe on sprites.
- [x] **Exports.** `atlas/export.py`: `atlas.png`, `atlas.json` (documented schema), `Atlas.gen.hpp` with named `constexpr` entries. All three come from the lock file. Done when the header compiles in a one-file test and the JSON validates against its schema. *The header compiles under `g++ -std=c++17 -Wall -Wextra -Werror`. The JSON layout is documented in `atlas/export.py`; there is no machine-readable schema file yet.*
- [ ] **Imports.** `atlas/imports.py`: bring in external sheets or single cells unchanged, with a recorded source hash, and pin them to fixed rectangles. Done when a Kenney sheet is imported and a hash mismatch fails the bake.
- [ ] **Companion maps.** Optional normal and glow atlases with the same layout. Done when `--maps normal,glow` writes matching files.
- [x] **Verify.** `sprites verify`: bake twice into temporary folders and compare RGBA bytes and PNG bytes. Done when it exits non-zero on any difference.

## M4. Lint and sheets

- [ ] **Metrics.** `lint/metrics.py`: colour count, orphan pixels (ported from `sprite_kit.orphans`), outline completeness, minimum feature width, fill ratio, contrast against a set of backgrounds, gutter cleanliness. Done when each metric has a unit test on a hand-made image.
- [ ] **Thresholds from reference art.** Measure the metrics on Kenney sheets and store the results in each style profile; no hand-picked numbers. Done when `sprites lint --calibrate <path>` writes the thresholds.
- [ ] **Look-alike check.** Flag pairs of sprites whose silhouette and tone layout are too close (as Mellangan's `collisions`). Done when two near-duplicates in a fixture are reported.
- [ ] **Lint command.** `sprites lint` prints one `error:` line per failure and exits non-zero; a per-sprite exception list needs a reason string. Done when the bake can run with `--strict`.
- [ ] **Review sheets.** Seed variants; on-ground previews over real tiles; height, normal and occlusion debug views; before/after diff against the previous `atlas.png`. Done when each is a `sprites sheet` mode.

## M5. Growth toolkit

Each generator outputs parts or curves for a scene, takes a seeded generator, and gets a review sheet.

- [ ] **Branching.** `grow/branch.py`: space colonisation and a simpler recursive brancher, with taper, droop and thickness from flow. For trees, roots, veins, antlers, coral, lightning.
- [ ] **Spiral placement.** `grow/phyllotaxis.py`: golden-angle placement with size and tilt curves. For petals, scales, seed heads, pine cones, feathers.
- [ ] **Cells.** `grow/cells.py`: Voronoi cells with relaxed points, edges and per-cell values. For cracks, scales, crystal facets, cobbles, dried mud.
- [ ] **Markings.** `grow/rd.py`: reaction-diffusion on a small grid, sampled in part coordinates. For spots, stripes, mottling. Fixed iteration count so it stays deterministic.
- [ ] **Strokes.** `grow/strokes.py`: short tapered strokes following a flow field over a part. For fur, feather barbs, grass, thatch, wood grain.
- [ ] **Edge growth.** Frilled and lobed outlines by differential growth of a closed curve. For lichen, fungus caps, leaves, petals.
- [ ] **Ageing.** `shade/weather.py`: moss on upward-facing creases, dirt in occluded areas, chips on exposed edges, wetness, frost, rust, each driven by the surface buffer.
- [ ] **Done when** each generator has a sheet of 16 seeds at 256px and the size ladder holds at 32px.

## M6. Kinds library

One module per kind under `library/`, each a parameterised builder with ranges, biome palettes and at least 16 approved variants on a sheet.

- [ ] **Minerals:** boulders, pebbles, crystals, ore, gems (faceted normals).
- [ ] **Plants:** broadleaf tree, conifer, palm, shrub, grass tuft, flower, vine, cactus, reed.
- [ ] **Fungi:** capped mushroom, bracket, puffball, cluster.
- [ ] **Creatures, one per body plan:** biped, heavy, quadruped, crawler, flyer, spirit, blob, rooted. Built on the rigs from M7; static pose until then.
- [ ] **Items:** blades, hafted weapons, bows, staves, shields, potions, food, tools, keys, scrolls, bags.
- [ ] **Buildings and props:** walls, roofs, doors, fences, tents, signs, barrels, graves, fires.
- [ ] **Ground tiles:** seamless grass, dirt, sand, stone, snow, water; transition sets between two grounds (edges and corners). Done when a 4×4 tiled preview shows no seams.
- [ ] **Effects:** glow, spark, slash, smoke, fire, splash, magic ring; additive-friendly alpha.
- [ ] **Emblems:** framed medal with a primary symbol and a small seal, `relief` style, at 96px. Done when a sheet stands beside Mellangan's `res/achievements.png`.
- [ ] **Palettes:** named biome palettes that re-colour any kind through its ramps.

## M7. Rigs and animation

- [ ] **Rig.** `form/rig.py`: joints in a tree, parts bound to joints, poses as joint angles and offsets. Done when a posed biped renders with parts overlapping correctly by depth.
- [ ] **Motion per family.** Walk, idle and attack for each of the eight families, as functions of phase. Blobs squash, spirits sway, rooted things lean, flyers beat. Done when each family has a looping strip sheet.
- [ ] **Frame stability at small sizes.** Outline and tone clusters must not flicker between frames at 16px. Done when a per-frame pixel-change metric stays under a threshold set from an approved strip.
- [ ] **Sway.** Wind phase for plants through growth parameters. Done when a tree and a grass tuft loop cleanly.
- [ ] **Atlas support.** Frames grouped under one sprite id with frame order and timing in `atlas.json` and the header. Done when a consumer can look up `walk` frames by name.

## M8. Mellangan adapter

- [ ] **Import the current atlas.** Read `res/atlas.png` through its declared bands and pin every cell at its current rectangle. Done when the baked output is pixel-identical to the input.
- [ ] **Emit the header.** Generate accessors equivalent to those in `src/Atlas.hpp`. Done when Mellangan builds against the generated header with no call-site changes.
- [ ] **Migrate one band.** Replace one band (suggested: `flora`) with generated sprites at the same indices, as a draft with a comparison sheet. Done when the user approves the sheet. Nothing in the Mellangan repo is written before that.
- [ ] **Regenerate `atlas.yaml`.** Emit it from the lock file so it can no longer drift.

## M9. Hardening

- [ ] **Cache.** Per-sprite cache keyed by definition source, seed, size, style and engine version. Done when a warm bake re-renders only changed sprites. *Partly done: bakes reuse renders from `.cache/sprites`, but any change to engine or content code invalidates every sprite, not only the changed ones.*
- [ ] **Parallel bake.** Process pool across sprites with ordered, deterministic assembly. Done when output is identical with 1 and N workers.
- [ ] **Speed targets** (to be confirmed on this machine once M1 exists): one 256px sprite under 1 second, a cold bake of 1,500 16px sprites under 60 seconds, a warm bake under 5 seconds. *Partly done: measured at 256px on this machine: beetle 1.0s, mushroom 2.3s. A warm bake of the 36-sprite demo atlas takes 0.7s, a cold one 44s.*
- [ ] **Cross-platform check.** Bake on Windows, Linux and macOS and compare hashes; list any functions that diverge and replace them. Done when hashes match or the divergent cases are documented.
- [ ] **Docs.** `README.md`: quick start, how to write a sprite, how to add a kind, the atlas schema.

---

## Open decisions

Defaults are in place for each; change them before the milestone named.

- **Fidelity target at large sizes** is the bas-relief look of `res/achievements.png`. Confirm at the M1 gate.
- **16px characters with faces** may stay hand-drawn through per-size overrides if generated ones fall short at the M2 gate.
- **Atlas format** is generic JSON plus a C++ header. Other engine formats (Godot, Unity) can be added as exporters in M3 if wanted.
- **Straight alpha with colour bleed** is the default; premultiplied output is a flag if the renderer wants it.

## Out of scope for now

- A live preview window or GUI editor.
- Image-model or learned generation of any kind.
- True 3D meshes or rotation to arbitrary view angles; sprites are authored for one view.
