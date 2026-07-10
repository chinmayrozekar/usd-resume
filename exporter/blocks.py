"""Authors ONE reusable voxel "Block" asset: a plain unit cube with a
`blockType` variant set (grass, dirt, stone, planks, log, leaves, ...).

The variant doesn't change geometry -- a block is always a unit cube --
it's purely a tag the exporter reads to decide which texture-atlas tiles
to UV-map onto each face. This keeps the same references+instancing+
variant-sets composition pattern as lego_builder/bricks.py, just applied
to texture selection instead of color.

A rough flat displayColor per variant is also authored so the asset still
looks reasonable in USD-only viewers (Quick Look, usdview) that don't
know about the exporter's texture atlas.
"""
from pathlib import Path

from pxr import Usd, UsdGeom, Gf

from texture_atlas import BLOCK_FACES, BLOCK_AVERAGE_COLOR

ASSET_DIR = Path(__file__).parent / "assets"
BLOCK_ASSET_PATH = ASSET_DIR / "block.usda"
DEFAULT_BLOCK_TYPE = "stone"


def generate_block_asset() -> Path:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    BLOCK_ASSET_PATH.unlink(missing_ok=True)

    stage = Usd.Stage.CreateNew(str(BLOCK_ASSET_PATH))
    root = UsdGeom.Xform.Define(stage, "/Block")
    stage.SetDefaultPrim(root.GetPrim())

    body = UsdGeom.Cube.Define(stage, "/Block/Body")
    body.GetSizeAttr().Set(1.0)

    variant_set = root.GetPrim().GetVariantSets().AddVariantSet("blockType")
    for block_type in BLOCK_FACES:
        variant_set.AddVariant(block_type)
    for block_type, rgb in BLOCK_AVERAGE_COLOR.items():
        variant_set.SetVariantSelection(block_type)
        with variant_set.GetVariantEditContext():
            body.GetDisplayColorAttr().Set([Gf.Vec3f(*rgb)])
    variant_set.SetVariantSelection(DEFAULT_BLOCK_TYPE)

    stage.GetRootLayer().Save()
    return BLOCK_ASSET_PATH


if __name__ == "__main__":
    path = generate_block_asset()
    print(f"Generated {path}")
