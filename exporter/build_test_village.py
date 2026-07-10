"""Builds a small Minecraft-style test structure (grass field, a house with
log corner posts and a stepped roof, a tree, a pond) -- purely a rehearsal
scene to prove the textured-voxel USD -> glTF pipeline end to end before
any real resume content gets authored this way.

Run with:
    .venv/bin/python exporter/build_test_village.py
"""
from pathlib import Path

from pxr import Usd, UsdGeom, UsdLux, Gf

import blocks
from voxel_builder import VoxelBuilder

OUTPUT = Path(__file__).parent / "village.usda"


def build():
    blocks.generate_block_asset()

    OUTPUT.unlink(missing_ok=True)
    stage = Usd.Stage.CreateNew(str(OUTPUT))
    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())

    light = UsdLux.DomeLight.Define(stage, "/World/Light")
    light.CreateIntensityAttr(1.0)

    b = VoxelBuilder(stage)

    # ---- Ground: grass on top of two layers of dirt ----
    b.box(-7, -2, -7, 6, -1, 6, "dirt")
    b.box(-7, 0, -7, 6, 0, 6, "grass")

    # ---- Pond ----
    b.box(-6, 0, 3, -4, 0, 5, "water")

    # ---- House walls: plank shell, log corner posts, a door, two windows ----
    corners = {(-2, -2), (2, -2), (-2, 2), (2, 2)}
    door = {(0, -2, 1)}  # (x, z, y) left open
    windows = {(-2, 0, 2), (2, 0, 2)}  # (x, z, y) -> glass instead of plank
    for y in range(1, 4):
        for x in range(-2, 3):
            for z in range(-2, 3):
                on_shell = x in (-2, 2) or z in (-2, 2)
                if not on_shell:
                    continue
                if (x, z, y) in door:
                    continue
                if (x, z, y) in windows:
                    b.place(x, y, z, "glass")
                elif (x, z) in corners:
                    b.place(x, y, z, "log")
                else:
                    b.place(x, y, z, "planks")

    # ---- Stepped roof ----
    b.box(-3, 4, -3, 3, 4, 3, "cobblestone")
    b.box(-2, 5, -2, 2, 5, 2, "cobblestone")
    b.box(-1, 6, -1, 1, 6, 1, "cobblestone")
    b.place(0, 7, 0, "cobblestone")

    # ---- Tree ----
    b.box(4, 1, 4, 4, 3, 4, "log")
    b.box(3, 4, 3, 5, 4, 5, "leaves")
    b.place(4, 5, 4, "leaves")

    stage.SetDefaultPrim(world.GetPrim())
    stage.GetRootLayer().Save()

    print(f"Placed {b.count} blocks")
    print(f"Saved to {OUTPUT}")


if __name__ == "__main__":
    build()
