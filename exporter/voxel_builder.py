"""VoxelBuilder: places instanceable references to the single shared Block
asset (blocks.py) on an integer grid -- the Minecraft-style counterpart to
lego_builder/builder.py's brick placement, but far simpler since blocks
don't need footprint/auto-stack bookkeeping.
"""
from pxr import UsdGeom, Gf

from blocks import BLOCK_ASSET_PATH
from signs import SIGN_ASSET_PATH


class VoxelBuilder:
    def __init__(self, stage, root_path="/World/Blocks"):
        self.stage = stage
        self.root_path = root_path
        self.count = 0
        UsdGeom.Xform.Define(stage, root_path)

    def place(self, x: int, y: int, z: int, block_type: str):
        self.count += 1
        prim_path = f"{self.root_path}/Block_{self.count:04d}"
        prim = self.stage.DefinePrim(prim_path)
        prim.GetReferences().AddReference(f"./assets/{BLOCK_ASSET_PATH.name}")
        prim.GetVariantSets().GetVariantSet("blockType").SetVariantSelection(block_type)
        prim.SetInstanceable(True)
        UsdGeom.XformCommonAPI(prim).SetTranslate(Gf.Vec3d(x, y, z))
        return prim

    def place_sign(self, x: float, y: float, z: float, company: str, rotate_y: float = 0, scale: float = 1.0):
        self.count += 1
        prim_path = f"{self.root_path}/Sign_{self.count:04d}"
        prim = self.stage.DefinePrim(prim_path)
        prim.GetReferences().AddReference(f"./assets/{SIGN_ASSET_PATH.name}")
        prim.GetVariantSets().GetVariantSet("signCompany").SetVariantSelection(company)
        prim.SetInstanceable(True)
        xform = UsdGeom.XformCommonAPI(prim)
        xform.SetTranslate(Gf.Vec3d(x, y, z))
        xform.SetRotate(Gf.Vec3f(0, rotate_y, 0))
        if scale != 1.0:
            xform.SetScale(Gf.Vec3f(scale, scale, scale))
        return prim

    def box(self, x0, y0, z0, x1, y1, z1, block_type: str, hollow=False):
        """Fills (or outlines, if hollow) an axis-aligned integer box."""
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                for z in range(min(z0, z1), max(z0, z1) + 1):
                    if hollow:
                        on_shell = x in (x0, x1) or y in (y0, y1) or z in (z0, z1)
                        if not on_shell:
                            continue
                    self.place(x, y, z, block_type)
