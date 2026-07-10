"""Builds the actual interactive-resume world: one long grass street with a
distinct small structure for each career chapter, positioned along X to
match resume-data.ts's cameraX waypoints (frontend/src/lib/resume-data.ts)
-- scrolling the page dollies the camera down this street. Each
organization (RIT, AMD, Siemens) gets its own building AND its own brand
plaque (logos.py / signs.py) standing beside the path in front of it.

Run with:
    .venv/bin/python exporter/build_career_street.py
"""
from pathlib import Path

from pxr import Usd, UsdGeom, UsdLux

import blocks
import signs
from voxel_builder import VoxelBuilder

OUTPUT = Path(__file__).parent / "career_street.usda"

STREET_X0, STREET_X1 = -30, 70
STREET_Z0, STREET_Z1 = -25, 25
PATH_Z0, PATH_Z1 = -1, 1

# foliage stays within the original, tree-tuned street width -- the ground
# beyond this on either side (north/south) is a bare-grass buffer so the
# horizon never shows sky, without turning into more forest
FOLIAGE_Z0, FOLIAGE_Z1 = -10, 10

POND_X0, POND_X1 = 24, 36
POND_Z0, POND_Z1 = 7, 9

# (cx, cz, half) of every building, so foliage placement can steer clear
# of all of them with a margin, no matter how the street layout changes
BUILDING_BOUNDS = [
    (6, -3, 3),
    (18, -3, 4),
    (30, 3, 3),
    (42, -3, 3),
    (54, 3, 3),
    (64, 0, 2),
]


def _face_z(cz: int, half: int) -> int:
    """The wall/edge of a footprint that faces the CAMERA. The camera dolly
    always sits south of the street (large +Z, see CameraRig.tsx) looking
    north, so the visible face of every building -- whichever side of the
    path it's on -- is always its south (max-Z) wall."""
    return cz + half


def gable_roof(b: VoxelBuilder, x0, x1, z0, z1, y0, material, eave=1):
    """A proper pitched roof: ridge along X, sloping down in Z, each row
    stepping in by one block until it closes to a single ridge line."""
    zc0, zc1 = z0 - eave, z1 + eave
    xc0, xc1 = x0 - eave, x1 + eave
    y = y0
    while zc0 <= zc1:
        b.box(xc0, y, zc0, xc1, y, zc1, material)
        zc0 += 1
        zc1 -= 1
        y += 1


def brand_tower(b: VoxelBuilder, cx, cz, half, height, wall, trim, company, sign_scale=2.0):
    """A tall building in an organization's own brand color, with a large
    brand panel mounted flush on the facade near the top -- big and on the
    building's own face (not a flag on a pole, which is both too small to
    read at a distance and easy to occlude with the pole itself)."""
    x0, x1 = cx - half, cx + half
    z0, z1 = cz - half, cz + half
    door_z = _face_z(cz, half)
    window_cols = [c for c in range(x0 + 1, x1) if c != cx] or [x0, x1]
    for y in range(1, height + 1):
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                on_shell = x in (x0, x1) or z in (z0, z1)
                if not on_shell:
                    continue
                if y in (1, 2) and z == door_z and x == cx:
                    continue  # door
                if y % 3 == 0 and z == door_z and x in window_cols:
                    b.place(x, y, z, "glass")
                    continue
                corner = x in (x0, x1) and z in (z0, z1)
                b.place(x, y, z, trim if corner else wall)
    b.box(x0 - 1, height + 1, z0 - 1, x1 + 1, height + 1, z1 + 1, trim)

    # mounted on the south (camera-facing) wall, standing slightly proud of it
    standoff = 0.5 + 0.15 * sign_scale
    sign_y = height - 1.5
    b.place_sign(cx, sign_y, door_z + standoff, company, scale=sign_scale)
    return door_z


def signal_tower(b: VoxelBuilder, cx: int, cz: int):
    """AI & Agentic Systems: a glassy modern structure with an antenna."""
    half = 2
    x0, x1 = cx - half, cx + half
    z0, z1 = cz - half, cz + half
    door_z = _face_z(cz, half)
    for y in range(1, 6):
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                on_shell = x in (x0, x1) or z in (z0, z1)
                if not on_shell:
                    continue
                if y == 1 and z == door_z and x == cx:
                    continue  # door
                corner = x in (x0, x1) and z in (z0, z1)
                b.place(x, y, z, "log" if corner else "glass")
    b.box(x0, 6, z0, x1, 6, z1, "stone")
    # antenna
    b.box(cx, 7, cz, cx, 10, cz, "log")
    b.place(cx - 1, 9, cz, "glass")
    b.place(cx + 1, 9, cz, "glass")


def construction(b: VoxelBuilder, cx: int, cz: int):
    """OpenUSD chapter: deliberately unfinished -- partial walls, exposed
    scaffolding, no roof. This is the 'now' chapter."""
    x0, x1 = cx - 2, cx + 2
    z0, z1 = cz - 2, cz + 2
    for y in (1, 2):
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                on_shell = x in (x0, x1) or z in (z0, z1)
                if not on_shell:
                    continue
                if z == z1 or (x == x0 and y == 2):
                    continue  # missing wall sections -- unfinished
                b.place(x, y, z, "planks")
    # scaffolding posts, uneven heights
    for sx, sz, h in [(x0 - 1, z0 - 1, 4), (x1 + 1, z0 - 1, 3), (x0 - 1, z1 + 1, 5), (x1 + 1, z1 + 1, 2)]:
        b.box(sx, 1, sz, sx, h, sz, "log")


def signpost(b: VoxelBuilder, cx: int, cz: int):
    b.box(cx, 1, cz, cx, 4, cz, "log")
    b.box(cx - 1, 4, cz, cx + 1, 4, cz, "planks")


def plant_tree(b: VoxelBuilder, x: int, z: int, trunk_height: int = 3):
    b.box(x, 1, z, x, trunk_height, z, "log")
    top = trunk_height
    b.box(x - 1, top, z - 1, x + 1, top + 1, z + 1, "leaves")
    b.place(x, top + 2, z, "leaves")


def plant_bush(b: VoxelBuilder, x: int, z: int):
    b.place(x, 1, z, "leaves")


def _clear_of_buildings(x, z, margin=2):
    return all(
        abs(x - cx) > half + margin or abs(z - cz) > half + margin
        for cx, cz, half in BUILDING_BOUNDS
    )


def _clear_of_pond(x, z, margin=1):
    return not (POND_X0 - margin <= x <= POND_X1 + margin and POND_Z0 - margin <= z <= POND_Z1 + margin)


def scatter_foliage(b: VoxelBuilder):
    """Sprinkles trees and bushes across the street -- enough to feel alive,
    sparse enough to not swallow the buildings -- steering clear of every
    building, the pond, and the path itself. Deterministic, not random, so
    rebuilds are reproducible: which spots get a tree vs a bush vs nothing
    comes from a fixed hash of position, not RNG state."""
    for x in range(STREET_X0 + 2, STREET_X1 - 1, 3):
        for z in range(FOLIAGE_Z0 + 2, FOLIAGE_Z1 - 1, 3):
            if PATH_Z0 - 1 <= z <= PATH_Z1 + 1:
                continue  # keep the path itself clear
            if not _clear_of_buildings(x, z, margin=3):
                continue
            if not _clear_of_pond(x, z):
                continue
            bucket = (x * 7 + z * 13) % 9
            if bucket <= 4:
                continue  # mostly open grass -- sparse, not a forest
            if bucket in (5, 6):
                plant_tree(b, x, z, trunk_height=3 + (bucket % 2))
            else:
                plant_bush(b, x, z)


def build():
    blocks.generate_block_asset()
    signs.generate_sign_asset()

    OUTPUT.unlink(missing_ok=True)
    stage = Usd.Stage.CreateNew(str(OUTPUT))
    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())

    light = UsdLux.DomeLight.Define(stage, "/World/Light")
    light.CreateIntensityAttr(1.0)

    b = VoxelBuilder(stage)

    # ---- the street: grass either side of a gravel walking path -- the
    # pond's whole footprint (rim + interior) is carved out here so grass
    # never gets placed underneath the sand/water and z-fights with them ----
    b.box(STREET_X0, -2, STREET_Z0, STREET_X1, -1, STREET_Z1, "dirt")
    for x in range(STREET_X0, STREET_X1 + 1):
        for z in range(STREET_Z0, STREET_Z1 + 1):
            if POND_X0 - 1 <= x <= POND_X1 + 1 and POND_Z0 - 1 <= z <= POND_Z1 + 1:
                continue  # pond owns this cell instead
            on_path = PATH_Z0 <= z <= PATH_Z1
            b.place(x, 0, z, "gravel" if on_path else "grass")

    # ---- pond, in front of (south of) the Siemens building -- sand rim and
    # water interior are mutually exclusive per cell, and the ground loop
    # above already left this whole footprint untouched, so each pond cell
    # is owned by exactly one block, top to bottom -- no z-fighting ----
    for x in range(POND_X0 - 1, POND_X1 + 2):
        for z in range(POND_Z0 - 1, POND_Z1 + 2):
            interior = POND_X0 <= x <= POND_X1 and POND_Z0 <= z <= POND_Z1
            b.place(x, 0, z, "water" if interior else "sand")

    # ---- one tower per chapter, positioned to match cameraX, each flying
    # its own brand-colored flag high above the roofline ----
    brand_tower(b, cx=6, cz=-3, half=2, height=8, wall="orange", trim="brick", company="rit", sign_scale=1.8)
    brand_tower(b, cx=18, cz=-3, half=3, height=13, wall="cobblestone", trim="charcoal", company="amd", sign_scale=2.6)
    brand_tower(b, cx=30, cz=3, half=2, height=11, wall="stone", trim="teal", company="siemens", sign_scale=1.8)

    signal_tower(b, cx=42, cz=-3)
    construction(b, cx=54, cz=3)
    signpost(b, cx=64, cz=0)

    # ---- foliage ----
    scatter_foliage(b)

    stage.GetRootLayer().Save()
    print(f"Placed {b.count} blocks")
    print(f"Saved to {OUTPUT}")


if __name__ == "__main__":
    build()
