"""Exports a USD stage's geometry to a static glTF binary (.glb) for
real-time web rendering with Three.js.

This is NOT a general USD-to-glTF converter -- it only understands the
primitive shapes this project's scenes actually author (Cube, Cylinder,
Sphere with flat displayColor, arranged via references/instancing). Mesh
templates are generated once per unique shape "recipe" and shared across
every glTF node that uses them, the same author-once/reuse-many pattern
the USD side already gets from references + instanceable prims -- so a
scene with hundreds of instanced bricks still collapses to a handful of
glTF meshes and materials.

Instancing is resolved by traversing with instance proxies enabled, so
each instanceable reference (see lego_builder/builder.py) is walked as if
inlined, and every prim's WORLD transform (including the instance's own
placement) is baked directly into its glTF node -- the export is a static
snapshot at one time code, not a live re-composition.

Run standalone:
    .venv/bin/python exporter/usd_to_gltf.py <in.usda> <out.glb> [--frame N]
"""
from __future__ import annotations

import argparse
import math
import struct
from pathlib import Path

import pygltflib as gltf
from pxr import Usd, UsdGeom

from texture_atlas import BLOCK_FACES, generate_atlas, generate_water_tile, tile_uv_bounds
from logos import PLAQUES, generate_plaque

CYLINDER_SEGMENTS = 20
SPHERE_LAT_SEGMENTS = 10
SPHERE_LON_SEGMENTS = 20


def _cube_mesh():
    """Unit cube spanning -1..1, matching UsdGeom.Cube's own default (size=2)
    convention -- so a prim's world matrix (which already carries any
    xformOp:scale) places this template correctly with no extra scaling."""
    faces = [
        ((0, 0, 1), [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]),
        ((0, 0, -1), [(1, -1, -1), (-1, -1, -1), (-1, 1, -1), (1, 1, -1)]),
        ((1, 0, 0), [(1, -1, 1), (1, -1, -1), (1, 1, -1), (1, 1, 1)]),
        ((-1, 0, 0), [(-1, -1, -1), (-1, -1, 1), (-1, 1, 1), (-1, 1, -1)]),
        ((0, 1, 0), [(-1, 1, 1), (1, 1, 1), (1, 1, -1), (-1, 1, -1)]),
        ((0, -1, 0), [(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)]),
    ]
    positions, normals, indices = [], [], []
    for normal, quad in faces:
        base = len(positions)
        positions.extend(quad)
        normals.extend([normal] * 4)
        indices += [base, base + 1, base + 2, base, base + 2, base + 3]
    return positions, normals, indices


_CUBE_FACES = [
    ("top", (0, 0, 1), [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]),
    ("bottom", (0, 0, -1), [(1, -1, -1), (-1, -1, -1), (-1, 1, -1), (1, 1, -1)]),
    ("side", (1, 0, 0), [(1, -1, 1), (1, -1, -1), (1, 1, -1), (1, 1, 1)]),
    ("side", (-1, 0, 0), [(-1, -1, -1), (-1, -1, 1), (-1, 1, 1), (-1, 1, -1)]),
    ("top", (0, 1, 0), [(-1, 1, 1), (1, 1, 1), (1, 1, -1), (-1, 1, -1)]),
    ("bottom", (0, -1, 0), [(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)]),
]
# _CUBE_FACES' first column is only a face-normal-direction label reused as a
# fallback; the real semantic (top/bottom/side of a VOXEL, i.e. facing +Y vs
# -Y vs horizontal) is recomputed from each face's own normal below.


def _voxel_face_semantic(normal):
    if normal == (0, 1, 0):
        return "top"
    if normal == (0, -1, 0):
        return "bottom"
    return "side"


def _cube_mesh_textured(face_tiles: dict):
    """Unit voxel cube (-0.5..0.5, so integer grid coordinates land on block
    centers) with per-face UVs into the shared texture atlas."""
    positions, normals, uvs, indices = [], [], [], []
    for _, normal, quad in _CUBE_FACES:
        semantic = _voxel_face_semantic(normal)
        tile = face_tiles[semantic]
        u0, v0, u1, v1 = tile_uv_bounds(tile)
        base = len(positions)
        positions.extend((x * 0.5, y * 0.5, z * 0.5) for x, y, z in quad)
        normals.extend([normal] * 4)
        uvs.extend([(u0, v1), (u1, v1), (u1, v0), (u0, v0)])
        indices += [base, base + 1, base + 2, base, base + 2, base + 3]
    return positions, normals, uvs, indices


def _voxel_mesh_full_uv():
    """Unit voxel cube (-0.5..0.5, integer-grid-aligned like
    _cube_mesh_textured) but with each face mapped to the FULL 0..1 UV range
    of its own dedicated texture -- for water, which gets its own
    REPEAT-wrapped texture instead of an atlas tile, so its UVs can be
    animated (scrolled) at render time without bleeding into neighboring
    atlas tiles."""
    positions, normals, uvs, indices = [], [], [], []
    for _, normal, quad in _CUBE_FACES:
        base = len(positions)
        positions.extend((x * 0.5, y * 0.5, z * 0.5) for x, y, z in quad)
        normals.extend([normal] * 4)
        uvs.extend([(0, 1), (1, 1), (1, 0), (0, 0)])
        indices += [base, base + 1, base + 2, base, base + 2, base + 3]
    return positions, normals, uvs, indices


def _full_texture_cube_mesh():
    """Unit cube (-1..1, matching UsdGeom.Cube's own size=2 convention, so
    an authored xformOp:scale sizes it correctly) with every face mapped to
    the FULL 0..1 UV range of its own dedicated texture -- for a sign board
    showing one full-bleed image rather than an atlas tile."""
    positions, normals, uvs, indices = [], [], [], []
    for _, normal, quad in _CUBE_FACES:
        base = len(positions)
        positions.extend(quad)
        normals.extend([normal] * 4)
        uvs.extend([(0, 1), (1, 1), (1, 0), (0, 0)])
        indices += [base, base + 1, base + 2, base, base + 2, base + 3]
    return positions, normals, uvs, indices


def _cylinder_mesh(radius, height, segments=CYLINDER_SEGMENTS):
    """Y-axis cylinder, actual size baked in (USD's Cylinder has no mesh of
    its own -- it's an implicit quadric defined purely by radius/height/axis
    attributes, so unlike Cube there's no shared unit template possible;
    identical (radius, height) pairs still dedupe via the mesh cache)."""
    half_h = height / 2
    positions, normals, indices = [], [], []

    top_center = len(positions)
    positions.append((0, half_h, 0))
    normals.append((0, 1, 0))
    bottom_center = len(positions)
    positions.append((0, -half_h, 0))
    normals.append((0, -1, 0))

    top_ring, bottom_ring = [], []
    for i in range(segments):
        theta = 2 * math.pi * i / segments
        x, z = radius * math.cos(theta), radius * math.sin(theta)
        top_ring.append(len(positions))
        positions.append((x, half_h, z))
        normals.append((0, 1, 0))
        bottom_ring.append(len(positions))
        positions.append((x, -half_h, z))
        normals.append((0, -1, 0))

    side_top, side_bottom = [], []
    for i in range(segments):
        theta = 2 * math.pi * i / segments
        nx, nz = math.cos(theta), math.sin(theta)
        x, z = radius * nx, radius * nz
        side_top.append(len(positions))
        positions.append((x, half_h, z))
        normals.append((nx, 0, nz))
        side_bottom.append(len(positions))
        positions.append((x, -half_h, z))
        normals.append((nx, 0, nz))

    for i in range(segments):
        j = (i + 1) % segments
        indices += [top_center, top_ring[i], top_ring[j]]
        indices += [bottom_center, bottom_ring[j], bottom_ring[i]]
        a, b, c, d = side_top[i], side_top[j], side_bottom[j], side_bottom[i]
        indices += [a, b, c, a, c, d]

    return positions, normals, indices


def _sphere_mesh(radius, lat=SPHERE_LAT_SEGMENTS, lon=SPHERE_LON_SEGMENTS):
    positions, normals, indices = [], [], []
    for i in range(lat + 1):
        phi = math.pi * i / lat
        for j in range(lon + 1):
            theta = 2 * math.pi * j / lon
            nx = math.sin(phi) * math.cos(theta)
            ny = math.cos(phi)
            nz = math.sin(phi) * math.sin(theta)
            positions.append((radius * nx, radius * ny, radius * nz))
            normals.append((nx, ny, nz))
    for i in range(lat):
        for j in range(lon):
            a = i * (lon + 1) + j
            b = a + lon + 1
            indices += [a, b, a + 1, a + 1, b, b + 1]
    return positions, normals, indices


class _BufferBuilder:
    """Accumulates one flat binary blob and hands back Accessor indices --
    pygltflib models buffers/bufferViews/accessors as separate arrays you
    wire up by index, this just hides that bookkeeping."""

    def __init__(self, g: gltf.GLTF2):
        self.g = g
        self.blob = bytearray()

    def _pad(self):
        while len(self.blob) % 4:
            self.blob.append(0)

    def add_vec3(self, values, component_type, target, minmax=False):
        self._pad()
        offset = len(self.blob)
        for v in values:
            self.blob += struct.pack("<3f", *v)
        view = gltf.BufferView(
            buffer=0, byteOffset=offset, byteLength=len(self.blob) - offset, target=target
        )
        self.g.bufferViews.append(view)
        view_index = len(self.g.bufferViews) - 1

        accessor = gltf.Accessor(
            bufferView=view_index,
            componentType=component_type,
            count=len(values),
            type=gltf.VEC3,
        )
        if minmax:
            xs, ys, zs = zip(*values)
            accessor.min = [min(xs), min(ys), min(zs)]
            accessor.max = [max(xs), max(ys), max(zs)]
        self.g.accessors.append(accessor)
        return len(self.g.accessors) - 1

    def add_vec2(self, values, component_type, target):
        self._pad()
        offset = len(self.blob)
        for v in values:
            self.blob += struct.pack("<2f", *v)
        view = gltf.BufferView(
            buffer=0, byteOffset=offset, byteLength=len(self.blob) - offset, target=target
        )
        self.g.bufferViews.append(view)
        view_index = len(self.g.bufferViews) - 1

        accessor = gltf.Accessor(
            bufferView=view_index,
            componentType=component_type,
            count=len(values),
            type=gltf.VEC2,
        )
        self.g.accessors.append(accessor)
        return len(self.g.accessors) - 1

    def add_image_bytes(self, data: bytes) -> int:
        """Embeds raw bytes (e.g. a PNG) as a bufferView, for a glTF Image
        that references it by bufferView instead of an external URI."""
        self._pad()
        offset = len(self.blob)
        self.blob += data
        view = gltf.BufferView(buffer=0, byteOffset=offset, byteLength=len(data))
        self.g.bufferViews.append(view)
        return len(self.g.bufferViews) - 1

    def add_indices(self, indices):
        self._pad()
        offset = len(self.blob)
        for i in indices:
            self.blob += struct.pack("<I", i)
        view = gltf.BufferView(
            buffer=0,
            byteOffset=offset,
            byteLength=len(self.blob) - offset,
            target=gltf.ELEMENT_ARRAY_BUFFER,
        )
        self.g.bufferViews.append(view)
        view_index = len(self.g.bufferViews) - 1

        accessor = gltf.Accessor(
            bufferView=view_index,
            componentType=gltf.UNSIGNED_INT,
            count=len(indices),
            type=gltf.SCALAR,
        )
        self.g.accessors.append(accessor)
        return len(self.g.accessors) - 1


class UsdToGltfExporter:
    def __init__(self):
        self.g = gltf.GLTF2()
        self.g.scenes.append(gltf.Scene(nodes=[]))
        self.g.scene = 0
        self.buf = _BufferBuilder(self.g)
        # Geometry (accessors) is cached per shape -- a cube is a cube
        # regardless of color. glTF materials are a property of a mesh's
        # PRIMITIVE, not of a node, so the actual Mesh objects (which
        # reference this shared geometry plus one material) are cached
        # per (shape, material) pair instead, one level up.
        self._geometry_cache: dict[tuple, tuple] = {}
        self._mesh_cache: dict[tuple, int] = {}
        self._material_cache: dict[tuple, int] = {}
        self._atlas_material_index: int | None = None

    def _get_or_create_geometry(self, key, positions, normals, indices, uvs=None):
        if key in self._geometry_cache:
            return self._geometry_cache[key]
        pos_idx = self.buf.add_vec3(positions, gltf.FLOAT, gltf.ARRAY_BUFFER, minmax=True)
        norm_idx = self.buf.add_vec3(normals, gltf.FLOAT, gltf.ARRAY_BUFFER)
        uv_idx = self.buf.add_vec2(uvs, gltf.FLOAT, gltf.ARRAY_BUFFER) if uvs else None
        idx_idx = self.buf.add_indices(indices)
        self._geometry_cache[key] = (pos_idx, norm_idx, uv_idx, idx_idx)
        return self._geometry_cache[key]

    def _get_or_create_mesh(self, shape_key, material_index):
        mesh_key = (shape_key, material_index)
        if mesh_key in self._mesh_cache:
            return self._mesh_cache[mesh_key]
        pos_idx, norm_idx, uv_idx, idx_idx = self._geometry_cache[shape_key]
        attributes = gltf.Attributes(POSITION=pos_idx, NORMAL=norm_idx)
        if uv_idx is not None:
            attributes.TEXCOORD_0 = uv_idx
        primitive = gltf.Primitive(attributes=attributes, indices=idx_idx, material=material_index)
        mesh_index = len(self.g.meshes)
        self.g.meshes.append(gltf.Mesh(primitives=[primitive]))
        self._mesh_cache[mesh_key] = mesh_index
        return mesh_index

    def _get_or_create_material(self, rgb):
        key = tuple(round(c, 4) for c in rgb)
        if key in self._material_cache:
            return self._material_cache[key]
        material = gltf.Material(
            pbrMetallicRoughness=gltf.PbrMetallicRoughness(
                baseColorFactor=[*key, 1.0], metallicFactor=0.05, roughnessFactor=0.6
            )
        )
        material_index = len(self.g.materials)
        self.g.materials.append(material)
        self._material_cache[key] = material_index
        return material_index

    def _get_or_create_atlas_material(self) -> int:
        """The one shared material every textured voxel block uses -- built
        lazily so scenes with no voxel blocks never embed the atlas at all."""
        if self._atlas_material_index is not None:
            return self._atlas_material_index

        import io

        png_bytes = io.BytesIO()
        generate_atlas().save(png_bytes, format="PNG")
        buffer_view = self.buf.add_image_bytes(png_bytes.getvalue())

        self.g.images.append(gltf.Image(bufferView=buffer_view, mimeType="image/png"))
        image_index = len(self.g.images) - 1

        # NEAREST filtering on both axes keeps the pixel-art crisp/blocky
        # instead of blurring it -- the whole point of a voxel look.
        self.g.samplers.append(
            gltf.Sampler(
                magFilter=gltf.NEAREST,
                minFilter=gltf.NEAREST_MIPMAP_LINEAR,
                wrapS=gltf.CLAMP_TO_EDGE,
                wrapT=gltf.CLAMP_TO_EDGE,
            )
        )
        sampler_index = len(self.g.samplers) - 1

        self.g.textures.append(gltf.Texture(source=image_index, sampler=sampler_index))
        texture_index = len(self.g.textures) - 1

        material = gltf.Material(
            pbrMetallicRoughness=gltf.PbrMetallicRoughness(
                baseColorTexture=gltf.TextureInfo(index=texture_index),
                metallicFactor=0.0,
                roughnessFactor=0.95,
            )
        )
        self._atlas_material_index = len(self.g.materials)
        self.g.materials.append(material)
        return self._atlas_material_index

    def _get_or_create_water_material(self) -> int:
        """Water gets its own dedicated, REPEAT-wrapped texture (not an
        atlas tile) and a materials.name the frontend can look up at
        runtime to animate the texture's UV offset for a flowing look."""
        cache_key = ("water_material",)
        if cache_key in self._material_cache:
            return self._material_cache[cache_key]

        import io

        png_bytes = io.BytesIO()
        generate_water_tile().save(png_bytes, format="PNG")
        buffer_view = self.buf.add_image_bytes(png_bytes.getvalue())

        self.g.images.append(gltf.Image(bufferView=buffer_view, mimeType="image/png"))
        image_index = len(self.g.images) - 1

        self.g.samplers.append(
            gltf.Sampler(
                magFilter=gltf.NEAREST,
                minFilter=gltf.NEAREST_MIPMAP_LINEAR,
                wrapS=gltf.REPEAT,
                wrapT=gltf.REPEAT,
            )
        )
        sampler_index = len(self.g.samplers) - 1

        self.g.textures.append(gltf.Texture(source=image_index, sampler=sampler_index))
        texture_index = len(self.g.textures) - 1

        material = gltf.Material(
            name="Water",
            pbrMetallicRoughness=gltf.PbrMetallicRoughness(
                baseColorTexture=gltf.TextureInfo(index=texture_index),
                metallicFactor=0.1,
                roughnessFactor=0.3,
            ),
        )
        material_index = len(self.g.materials)
        self.g.materials.append(material)
        self._material_cache[cache_key] = material_index
        return material_index

    def _water_shape_key(self):
        key = ("voxel_water",)
        if key not in self._geometry_cache:
            positions, normals, uvs, indices = _voxel_mesh_full_uv()
            self._get_or_create_geometry(key, positions, normals, indices, uvs=uvs)
        return key

    def _block_type_of(self, prim):
        """A voxel Block instance's `blockType` variant set lives on the
        instance root (see blocks.py), not on the Cube prim itself -- the
        Cube is that root's child. Returns None for any non-voxel geometry."""
        if not UsdGeom.Cube(prim):
            return None
        parent = prim.GetParent()
        if not parent or not parent.IsValid():
            return None
        variant_set = parent.GetVariantSet("blockType")
        selection = variant_set.GetVariantSelection()
        return selection if selection in BLOCK_FACES else None

    def _voxel_shape_key_for_prim(self, prim, block_type: str):
        key = ("voxel", block_type)
        if key not in self._geometry_cache:
            positions, normals, uvs, indices = _cube_mesh_textured(BLOCK_FACES[block_type])
            self._get_or_create_geometry(key, positions, normals, indices, uvs=uvs)
        return key

    def _get_or_create_logo_material(self, company: str) -> int:
        cache_key = ("logo_material", company)
        if cache_key in self._material_cache:
            return self._material_cache[cache_key]

        import io

        png_bytes = io.BytesIO()
        generate_plaque(company).save(png_bytes, format="PNG")
        buffer_view = self.buf.add_image_bytes(png_bytes.getvalue())

        self.g.images.append(gltf.Image(bufferView=buffer_view, mimeType="image/png"))
        image_index = len(self.g.images) - 1

        self.g.samplers.append(
            gltf.Sampler(
                magFilter=gltf.LINEAR,
                minFilter=gltf.LINEAR_MIPMAP_LINEAR,
                wrapS=gltf.CLAMP_TO_EDGE,
                wrapT=gltf.CLAMP_TO_EDGE,
            )
        )
        sampler_index = len(self.g.samplers) - 1

        self.g.textures.append(gltf.Texture(source=image_index, sampler=sampler_index))
        texture_index = len(self.g.textures) - 1

        material = gltf.Material(
            pbrMetallicRoughness=gltf.PbrMetallicRoughness(
                baseColorTexture=gltf.TextureInfo(index=texture_index),
                metallicFactor=0.0,
                roughnessFactor=0.8,
            )
        )
        material_index = len(self.g.materials)
        self.g.materials.append(material)
        self._material_cache[cache_key] = material_index
        return material_index

    def _sign_shape_key(self):
        key = ("sign",)
        if key not in self._geometry_cache:
            positions, normals, uvs, indices = _full_texture_cube_mesh()
            self._get_or_create_geometry(key, positions, normals, indices, uvs=uvs)
        return key

    def _sign_company_of(self, prim):
        if not UsdGeom.Cube(prim):
            return None
        parent = prim.GetParent()
        if not parent or not parent.IsValid():
            return None
        variant_set = parent.GetVariantSet("signCompany")
        selection = variant_set.GetVariantSelection()
        return selection if selection in PLAQUES else None

    def _shape_key_for_prim(self, prim):
        """Returns a cache key for this prim's geometry (ensuring it's been
        built), or None if the prim isn't a shape this exporter understands."""
        cube = UsdGeom.Cube(prim)
        if cube:
            key = ("cube",)
            if key not in self._geometry_cache:
                positions, normals, indices = _cube_mesh()
                self._get_or_create_geometry(key, positions, normals, indices)
            return key

        cylinder = UsdGeom.Cylinder(prim)
        if cylinder:
            radius = round(cylinder.GetRadiusAttr().Get() or 1.0, 4)
            height = round(cylinder.GetHeightAttr().Get() or 2.0, 4)
            key = ("cylinder", radius, height)
            if key not in self._geometry_cache:
                positions, normals, indices = _cylinder_mesh(radius, height)
                self._get_or_create_geometry(key, positions, normals, indices)
            return key

        sphere = UsdGeom.Sphere(prim)
        if sphere:
            radius = round(sphere.GetRadiusAttr().Get() or 1.0, 4)
            key = ("sphere", radius)
            if key not in self._geometry_cache:
                positions, normals, indices = _sphere_mesh(radius)
                self._get_or_create_geometry(key, positions, normals, indices)
            return key

        return None

    def export_stage(self, stage: Usd.Stage, time_code: Usd.TimeCode) -> gltf.GLTF2:
        xf_cache = UsdGeom.XformCache(time_code)
        root_nodes = []

        for prim in stage.Traverse(Usd.TraverseInstanceProxies(Usd.PrimDefaultPredicate)):
            gprim = UsdGeom.Gprim(prim)
            if not gprim:
                continue
            imageable = UsdGeom.Imageable(prim)
            if imageable.ComputeVisibility(time_code) == UsdGeom.Tokens.invisible:
                continue

            sign_company = self._sign_company_of(prim)
            block_type = self._block_type_of(prim)
            if sign_company is not None:
                shape_key = self._sign_shape_key()
                material_index = self._get_or_create_logo_material(sign_company)
            elif block_type == "water":
                shape_key = self._water_shape_key()
                material_index = self._get_or_create_water_material()
            elif block_type is not None:
                shape_key = self._voxel_shape_key_for_prim(prim, block_type)
                material_index = self._get_or_create_atlas_material()
            else:
                shape_key = self._shape_key_for_prim(prim)
                if shape_key is None:
                    continue
                color_attr = gprim.GetDisplayColorAttr().Get(time_code)
                rgb = tuple(color_attr[0]) if color_attr else (0.7, 0.7, 0.7)
                material_index = self._get_or_create_material(rgb)

            mesh_index = self._get_or_create_mesh(shape_key, material_index)

            world = xf_cache.GetLocalToWorldTransform(prim)
            matrix = [world[i][j] for i in range(4) for j in range(4)]

            node = gltf.Node(mesh=mesh_index, matrix=matrix, name=str(prim.GetPath()))
            node_index = len(self.g.nodes)
            self.g.nodes.append(node)
            root_nodes.append(node_index)

        self.g.scenes[0].nodes = root_nodes

        self.g.buffers.append(gltf.Buffer(byteLength=len(self.buf.blob)))
        self.g.set_binary_blob(bytes(self.buf.blob))
        return self.g


def export(usda_path: str, glb_path: str, frame: float | None = None):
    stage = Usd.Stage.Open(usda_path)
    if frame is not None:
        time_code = Usd.TimeCode(frame)
    elif stage.HasAuthoredTimeCodeRange():
        time_code = Usd.TimeCode(stage.GetEndTimeCode())
    else:
        time_code = Usd.TimeCode.Default()

    exporter = UsdToGltfExporter()
    g = exporter.export_stage(stage, time_code)
    Path(glb_path).parent.mkdir(parents=True, exist_ok=True)
    g.save(glb_path)

    mesh_count = len(g.meshes)
    node_count = len(g.nodes)
    material_count = len(g.materials)
    print(
        f"Exported {node_count} nodes -> {mesh_count} shared meshes, "
        f"{material_count} materials @ time {time_code}"
    )
    print(f"Saved to {glb_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("usda_path")
    parser.add_argument("glb_path")
    parser.add_argument("--frame", type=float, default=None)
    args = parser.parse_args()
    export(args.usda_path, args.glb_path, args.frame)
