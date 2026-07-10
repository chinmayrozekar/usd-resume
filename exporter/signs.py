"""Authors ONE reusable "Sign" asset: a thin cube with a `signCompany`
variant set (rit, amd, siemens). Same pattern as blocks.py's `blockType`
variant set, but the exporter maps this one to a full-bleed brand plaque
image (logos.py) instead of an atlas tile.
"""
from pathlib import Path

from pxr import Usd, UsdGeom, Gf

from logos import PLAQUES

ASSET_DIR = Path(__file__).parent / "assets"
SIGN_ASSET_PATH = ASSET_DIR / "sign.usda"
DEFAULT_COMPANY = "amd"

# rough plaque-background color, for USD-only viewers that don't see the texture
FALLBACK_COLOR = (0.95, 0.95, 0.95)


def generate_sign_asset() -> Path:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    SIGN_ASSET_PATH.unlink(missing_ok=True)

    stage = Usd.Stage.CreateNew(str(SIGN_ASSET_PATH))
    root = UsdGeom.Xform.Define(stage, "/Sign")
    stage.SetDefaultPrim(root.GetPrim())

    body = UsdGeom.Cube.Define(stage, "/Sign/Body")
    body.GetDisplayColorAttr().Set([Gf.Vec3f(*FALLBACK_COLOR)])
    # a thin, wide board: 2.2 wide x 1.1 tall x 0.1 deep, mounted flush on a facade
    UsdGeom.XformCommonAPI(body).SetScale(Gf.Vec3f(1.1, 0.55, 0.05))

    variant_set = root.GetPrim().GetVariantSets().AddVariantSet("signCompany")
    for company in PLAQUES:
        variant_set.AddVariant(company)
    variant_set.SetVariantSelection(DEFAULT_COMPANY)

    stage.GetRootLayer().Save()
    return SIGN_ASSET_PATH


if __name__ == "__main__":
    path = generate_sign_asset()
    print(f"Generated {path}")
