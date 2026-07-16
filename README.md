# usd-resume

**Live: [chinmay-rozekar.vercel.app](https://chinmay-rozekar.vercel.app)**

An interactive, Minecraft-styled 3D resume. Scroll down a career street and
each building is a chapter — RIT, AMD, Siemens EDA, current work in AI &
agentic systems, and this site itself (still under construction, on
purpose).

Built by [Chinmay Rozekar](https://github.com/chinmayrozekar).

## How it's built

The whole scene is authored in **OpenUSD** with Python (`pxr`), not
modeled by hand in a DCC tool:

- `exporter/texture_atlas.py` — procedurally paints an original, pixel-art
  voxel texture atlas (grass, stone, wood, water, ...) with PIL/numpy. No
  Minecraft assets, just noise-speckled tiles in the same spirit.
- `exporter/blocks.py` / `exporter/signs.py` — generate reusable USD assets
  (a unit voxel block, a sign board) with `variantSet`s selecting block
  type / company branding.
- `exporter/voxel_builder.py` — a small API for placing instanced block/sign
  references on an integer grid.
- `exporter/build_career_street.py` — the actual scene: ground, path, pond,
  one building per career chapter, foliage.
- `exporter/usd_to_gltf.py` — a hand-built USD → glTF exporter (no
  off-the-shelf converter). Walks the composed stage with instance proxies
  enabled, dedupes geometry/materials by shape+material pair, embeds
  textures directly in the `.glb`.

The `.glb` is loaded client-side with **react-three-fiber**; scrolling
drives a camera dolly down the street in sync with each chapter's HTML
card (`frontend/src/components/CameraRig.tsx`).

## Run it locally

```bash
# regenerate the scene (requires exporter/.venv with usd-core, pygltflib, pillow, numpy)
cd exporter
.venv/bin/python build_career_street.py
.venv/bin/python usd_to_gltf.py career_street.usda career_street.glb
cp career_street.glb ../frontend/public/models/career_street.glb

# run the site
cd ../frontend
npm install
npm run dev
```

Open http://localhost:3000.

## Deploy

Vercel's remote build machine reliably OOMs on this app's build (the
three.js/drei dependency tree is heavy enough that it dies during
minification regardless of Node heap settings -- confirmed this isn't
fixable from `next.config.ts` alone). Pushing to `master` will *not*
auto-deploy successfully as a result.

Instead, build locally (plenty of memory there) and upload the prebuilt
output straight to production:

```bash
./deploy.sh
```

Requires the Vercel CLI to be authenticated (`npx vercel login`) and the
repo linked to the `chinmay-rozekar` project (`npx vercel link`).
