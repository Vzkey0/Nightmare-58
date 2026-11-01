# Builds the male and female protagonist from code so proportions can be tweaked and rebuilt.
# Faces -Y with feet on the origin, in A-pose for rigging. +X is the character's left.
#   blender --background --python art/characters/build_protagonist.py
import math
import os
import random

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
BLEND_PATH = os.path.join(HERE, "protagonist.blend")
GLB_DIR = os.path.join(HERE, "..", "..", "game", "models", "characters")

# Entries are (height, front-back radius, width radius, depth offset).
VARIANTS = {
  "male": {
    "height_scale": 1.0,
    "display_x": -0.7,
    "torso": [
      (0.98, 0.095, 0.14, 0), (1.08, 0.098, 0.15, 0), (1.20, 0.106, 0.168, 0), (1.32, 0.113, 0.195, 0),
      (1.40, 0.105, 0.195, 0), (1.445, 0.082, 0.145, 0.005), (1.49, 0.062, 0.075, 0.005),
    ],
    "skin": "skin_tan",
    "bare_arms": False,
    "pelvis_top": (0.112, 0.16),
    "neck": [(1.455, 0.07, 0.082, 0.014), (1.495, 0.058, 0.061, 0.012), (1.53, 0.052, 0.053, 0.008), (1.565, 0.053, 0.055, 0.004), (1.6, 0.055, 0.058, 0.002)],
    "head": [
      (1.518, 0.036, 0.04, -0.042), (1.535, 0.056, 0.062, -0.03), (1.56, 0.078, 0.074, -0.012),
      (1.585, 0.086, 0.076, -0.004), (1.61, 0.09, 0.078, 0), (1.635, 0.093, 0.081, 0), (1.66, 0.096, 0.083, 0),
      (1.69, 0.096, 0.083, 0), (1.72, 0.087, 0.075, 0.005), (1.75, 0.04, 0.036, 0.005),
    ],
    "head_bands": {0: "stubble", 1: "stubble"},
    "nose": None,
    "fingers": True,
    "arm_shift": -0.03,
    "arm_scale": 1.08,
  },
  "female": {
    "height_scale": 0.96,
    "display_x": 0.7,
    "skin": "skin",
    "bare_arms": True,
    "torso": [
      (0.98, 0.095, 0.14, 0), (1.06, 0.085, 0.118, 0), (1.18, 0.095, 0.128, 0), (1.30, 0.118, 0.16, -0.01),
      (1.38, 0.108, 0.172, -0.004), (1.44, 0.08, 0.145, 0.005), (1.49, 0.055, 0.052, 0.005),
    ],
    "shirt": [(1.17, 0.103, 0.136, 0), (1.30, 0.127, 0.168, -0.01), (1.375, 0.116, 0.18, -0.004)],
    "pelvis_top": (0.105, 0.135),
    "belt": ((0.122, 0.16), (0.112, 0.142)),
    "neck": [(1.47, 0.05, 0.052, 0.005), (1.56, 0.044, 0.044, 0)],
    "head": [
      (1.525, 0.03, 0.04, -0.022), (1.56, 0.066, 0.064, -0.008), (1.60, 0.085, 0.076, 0), (1.635, 0.093, 0.08, 0),
      (1.675, 0.095, 0.081, 0), (1.72, 0.085, 0.072, 0.005), (1.75, 0.04, 0.036, 0.005),
    ],
    # The band across the eyes stays dark, like the reference's shadowed face.
    "head_bands": {3: "skin_shadow", 4: "skin_shadow"},
    "nose": [
      ((0, -0.08, 1.635), 0.006, 0.007), ((0, -0.1, 1.602), 0.012, 0.015), ((0, -0.08, 1.59), 0.004, 0.005),
    ],
    "fingers": False,
    "arm_shift": -0.03,
    "arm_scale": 0.85,
    "strap_x": 0.1,
    "strap_depth": 0.93,
    "strap_lift": -0.007,
    "print_scale": 0.66,
    "print_z": 1.285,
  },
}

COLORS = {
  "skin": (0.80, 0.66, 0.62),
  "skin_shadow": (0.36, 0.28, 0.30),
  "hair": (0.10, 0.10, 0.12),
  "shirt": (0.11, 0.12, 0.15),
  "pants": (0.19, 0.22, 0.29),
  "pants_worn": (0.42, 0.44, 0.50),
  "leather": (0.08, 0.08, 0.09),
  "boots": (0.09, 0.09, 0.10),
  "metal": (0.70, 0.70, 0.72),
  "print_light": (0.88, 0.88, 0.85),
  "print_mid": (0.48, 0.48, 0.50),
  "skin_tan": (0.70, 0.49, 0.36),
  "stubble": (0.42, 0.30, 0.24),
  "lips": (0.56, 0.33, 0.28),
  "eye_white": (0.90, 0.88, 0.84),
  "iris": (0.13, 0.08, 0.06),
  "hair_dark": (0.12, 0.09, 0.08),
  "hair_light": (0.62, 0.55, 0.44),
  "flag_yellow": (0.98, 0.76, 0.10),
  "flag_blue": (0.10, 0.16, 0.62),
  "flag_red": (0.82, 0.08, 0.10),
  "white": (0.95, 0.95, 0.93),
  "pants_black": (0.13, 0.13, 0.15),
  "pants_pocket": (0.2, 0.2, 0.23),
  "flag_red_dark": (0.58, 0.05, 0.07),
  "seam": (0.27, 0.27, 0.31),
  "boot_leather": (0.15, 0.15, 0.16),
  "boot_sole": (0.06, 0.06, 0.065),
  "boot_soft": (0.34, 0.34, 0.36),
  "boot_stitch": (0.44, 0.44, 0.46),
  "stitch_yellow": (0.96, 0.77, 0.10),
}

ARM_PATH = [
  ((0.165, 0, 1.435), 0.05, 0.05),
  ((0.215, 0, 1.40), 0.06, 0.06),
  ((0.255, 0, 1.29), 0.052, 0.05),
  ((0.295, 0, 1.16), 0.04, 0.04),
  ((0.305, 0, 1.13), 0.039, 0.039),
  ((0.33, -0.01, 1.04), 0.044, 0.042),
  ((0.365, -0.015, 0.92), 0.03, 0.03),
  ((0.375, -0.02, 0.88), 0.028, 0.026),
]

HEAD_LIFT = 0.032

surfaces = {}
parts = []
head_parts = []
variant = None


def rings(entries):
  return [((0, depth, z), ru, rv) for z, ru, rv, depth in entries]


def arm_path(path):
  scale = variant["arm_scale"]
  return [((x + variant["arm_shift"], y, z), ru * scale, rv * scale) for (x, y, z), ru, rv in path]


def print_polygon(polygon):
  scale = variant["print_scale"]
  return [(x * scale, variant["print_z"] + (z - 1.2) * scale) for x, z in polygon]


def material(name):
  existing = bpy.data.materials.get(name)
  if existing:
    return existing
  mat = bpy.data.materials.new(name)
  linear = tuple(channel ** 2.2 for channel in COLORS[name]) + (1.0,)
  mat.diffuse_color = linear
  mat.use_nodes = True
  bsdf = mat.node_tree.nodes.get("Principled BSDF")
  bsdf.inputs["Base Color"].default_value = linear
  bsdf.inputs["Roughness"].default_value = 0.9
  return mat


def collection():
  result = bpy.data.collections.get("protagonist")
  if not result:
    result = bpy.data.collections.new("protagonist")
    bpy.context.scene.collection.children.link(result)
  return result


def add_object(name, verts, faces, face_materials, closed=True):
  mesh = bpy.data.meshes.new(name)
  mesh.from_pydata([tuple(v) for v in verts], [], faces)
  names = sorted(set(face_materials))
  for mat_name in names:
    mesh.materials.append(material(mat_name))
  for polygon, mat_name in zip(mesh.polygons, face_materials):
    polygon.material_index = names.index(mat_name)
  if closed:
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
  mesh.update()
  obj = bpy.data.objects.new(name, mesh)
  collection().objects.link(obj)
  parts.append(obj)
  surfaces[name] = BVHTree.FromPolygons([tuple(v) for v in verts], faces)
  return obj


def tube(name, path, mat, n=8, side=(0, 1, 0), zigzag=False, bands=None):
  """Lofts rings along path. Each entry is (position, radius along side, other radius)."""
  points = [Vector(entry[0]) for entry in path]
  verts = []
  u = Vector(side)
  for i, (_, ru, rv) in enumerate(path):
    tangent = (points[min(i + 1, len(points) - 1)] - points[max(i - 1, 0)]).normalized()
    u = (u - tangent * u.dot(tangent)).normalized()
    v = tangent.cross(u)
    # The half-step offset leaves flat faces on top and bottom, so boots sit level.
    offset = math.pi / n * (2 if zigzag and i % 2 else 1)
    for k in range(n):
      angle = offset + 2 * math.pi * k / n
      verts.append(points[i] + u * ru * math.cos(angle) + v * rv * math.sin(angle))
  faces = []
  face_materials = []
  for i in range(len(path) - 1):
    for k in range(n):
      j = (k + 1) % n
      faces.append((i * n + k, i * n + j, (i + 1) * n + j, (i + 1) * n + k))
      face_materials.append((bands or {}).get(i, mat))
  faces.append(tuple(reversed(range(n))))
  face_materials.append((bands or {}).get(0, mat))
  faces.append(tuple((len(path) - 1) * n + k for k in range(n)))
  face_materials.append(mat)
  return add_object(name, verts, faces, face_materials)


def mirrored(path, sign):
  return [((x * sign, y, z), ru, rv) for (x, y, z), ru, rv in path]


def both(name, path, mat, **kwargs):
  tube(name + "_l", path, mat, **kwargs)
  tube(name + "_r", mirrored(path, -1), mat, **kwargs)


def clump(name, position, scale, mat, seed):
  """Faceted blob used for the curly hair mass."""
  rng = random.Random(seed)
  bm = bmesh.new()
  bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
  verts = []
  for vert in bm.verts:
    jitter = 1.0 + rng.uniform(-0.18, 0.18)
    verts.append(Vector(position) + Vector(c * s * jitter for c, s in zip(vert.co, scale)))
  faces = [tuple(v.index for v in face.verts) for face in bm.faces]
  bm.free()
  add_object(name, verts, faces, [mat] * len(faces))


def decal(name, surface, polygon, mat, lift=0.006, back=False):
  """Projects an (x, z) polygon onto the front or back of a built surface as a color patch."""
  tree = surfaces[surface]
  facing = 1 if back else -1
  outline = list(polygon)
  center = (sum(p[0] for p in outline) / len(outline), sum(p[1] for p in outline) / len(outline))
  verts = []
  for x, z in [center] + outline:
    hit = tree.ray_cast(Vector((x, 2.0 * facing, z)), Vector((0, -facing, 0)))[0]
    if hit is None:
      raise ValueError(f"decal {name} misses {surface} at ({x}, {z})")
    verts.append(hit + Vector((0, lift * facing, 0)))
  count = len(outline)
  faces = [(0, 1 + i, 1 + (i + 1) % count) for i in range(count)]
  normal = (verts[faces[0][1]] - verts[0]).cross(verts[faces[0][2]] - verts[0])
  if normal.y * facing < 0:
    faces = [tuple(reversed(face)) for face in faces]
  add_object(name, verts, faces, [mat] * len(faces), closed=False)


def strip(name, surface, points, mat, depth=0.004, lift=0.0, n=4):
  """Raised band hugging a surface from the front. Points are (x, z, half height).

  Unlike decal(), it has volume, so it doesn't sink where it crosses the facets.
  """
  tree = surfaces[surface]
  path = []
  for x, z, half_height in points:
    hit = tree.ray_cast(Vector((x, -2.0, z)), Vector((0, 1, 0)))[0]
    if hit is None:
      raise ValueError(f"strip {name} misses {surface} at ({x}, {z})")
    path.append((tuple(hit - Vector((0, lift, 0))), half_height, depth))
  tube(name, path, mat, n=n, side=(0, 0, 1))


def clear():
  result = bpy.data.collections.get("protagonist")
  if result:
    for obj in list(result.objects):
      bpy.data.objects.remove(obj)
  for mesh in [m for m in bpy.data.meshes if m.users == 0]:
    bpy.data.meshes.remove(mesh)
  for armature in [a for a in bpy.data.armatures if a.users == 0]:
    bpy.data.armatures.remove(armature)
  surfaces.clear()


def build_body():
  skin = variant["skin"]
  tube("torso", rings(variant["torso"]), skin, n=10)
  tube("neck", rings(variant["neck"]), skin, n=10 if variant["fingers"] else 8)
  tube("head", rings(variant["head"]), skin, n=14 if variant["fingers"] else 10, bands=variant["head_bands"])
  if variant["nose"]:
    tube("nose", variant["nose"], skin, n=4)
  if variant["bare_arms"]:
    both("arm", arm_path(ARM_PATH), skin)
  if variant["fingers"]:
    both("hand", arm_path([
      ((0.375, -0.02, 0.89), 0.03, 0.02),
      ((0.395, -0.025, 0.83), 0.05, 0.023),
      ((0.405, -0.03, 0.79), 0.046, 0.019),
    ]), skin, n=6)
    for i, (y, length) in enumerate(((-0.066, 0.07), (-0.042, 0.082), (-0.018, 0.078), (0.006, 0.062))):
      both(f"finger_{i}", arm_path([
        ((0.404, y, 0.795), 0.0095, 0.0095),
        ((0.416, y, 0.795 - length * 0.55), 0.0085, 0.0085),
        ((0.424, y - 0.002, 0.795 - length), 0.0065, 0.0065),
      ]), skin, n=4)
  else:
    both("hand", arm_path([
      ((0.375, -0.02, 0.89), 0.03, 0.02),
      ((0.395, -0.025, 0.83), 0.048, 0.022),
      ((0.41, -0.03, 0.77), 0.042, 0.018),
      ((0.42, -0.03, 0.72), 0.02, 0.01),
    ]), skin, n=6)
  both("thumb", arm_path([
    ((0.375, -0.045, 0.86), 0.012, 0.012),
    ((0.38, -0.075, 0.81), 0.012, 0.011),
    ((0.385, -0.085, 0.775), 0.007, 0.007),
  ]), skin, n=5)


def build_pants():
  tube("pelvis", [
    ((0, 0, 0.78), 0.10, 0.13),
    ((0, 0, 0.92), 0.125, 0.178),
    ((0, 0, 1.00), 0.116, 0.166),
    ((0, 0, 1.05), *variant["pelvis_top"]),
  ], "pants", n=10)
  both("leg", [
    ((0.09, 0, 0.92), 0.115, 0.09),
    ((0.105, 0, 0.70), 0.135, 0.115),
    ((0.12, 0, 0.50), 0.14, 0.125),
    ((0.135, 0, 0.30), 0.15, 0.14),
    ((0.145, 0, 0.17), 0.158, 0.148),
    ((0.145, 0, 0.115), 0.125, 0.115),
    ((0.145, 0, 0.085), 0.105, 0.095),
  ], "pants", n=8)
  both("cargo_pocket", [
    ((0.238, 0.01, 0.64), 0.05, 0.016),
    ((0.242, 0.01, 0.42), 0.055, 0.016),
  ], "pants", n=4)
  both("cargo_flap", [
    ((0.243, 0.01, 0.645), 0.058, 0.02),
    ((0.243, 0.01, 0.6), 0.058, 0.02),
  ], "leather", n=4)
  both("boot_shaft", [
    ((0.145, 0.02, 0.0), 0.075, 0.07),
    ((0.145, 0.02, 0.16), 0.06, 0.06),
  ], "boots")
  both("boot_foot", [
    ((0.145, 0.095, 0.055), 0.05, 0.052),
    ((0.145, 0.02, 0.06), 0.062, 0.062),
    ((0.145, -0.09, 0.055), 0.058, 0.058),
    ((0.145, -0.17, 0.045), 0.046, 0.054),
    ((0.145, -0.205, 0.038), 0.03, 0.04),
  ], "boots", side=(0, 0, 1))
  belt_bottom, belt_top = variant["belt"]
  tube("belt", [
    ((0, 0, 1.012), *belt_bottom),
    ((0, 0, 1.05), *belt_top),
  ], "leather", n=10)
  decal("buckle", "belt", [(-0.042, 1.015), (0.042, 1.015), (0.042, 1.047), (-0.042, 1.047)], "metal")
  decal("buckle_center", "belt", [(-0.026, 1.022), (0.026, 1.022), (0.026, 1.04), (-0.026, 1.04)], "leather", lift=0.01)
  decal("fly", "pelvis", [(-0.009, 0.84), (0.009, 0.84), (0.009, 1.0), (-0.009, 1.0)], "pants_worn")
  decal("rip_thigh", "leg_l", [(0.07, 0.66), (0.125, 0.70), (0.145, 0.60), (0.105, 0.56)], "pants_worn")
  decal("rip_knee", "leg_r", [(-0.2, 0.43), (-0.1, 0.46), (-0.05, 0.41), (-0.13, 0.385)], "pants_worn")
  decal("rip_shin", "leg_r", [(-0.11, 0.33), (-0.05, 0.31), (-0.06, 0.2), (-0.12, 0.21)], "pants_worn")
  decal("rip_shin_center", "leg_r", [(-0.095, 0.3), (-0.07, 0.29), (-0.08, 0.235), (-0.1, 0.24)], "leather", lift=0.01)


def build_shirt():
  tube("shirt", rings(variant["shirt"]), "shirt", n=12)
  strap_x = variant["strap_x"]
  depth = variant["strap_depth"]
  lift = variant["strap_lift"]
  both("shirt_strap", [
    ((strap_x, y * depth, z + lift), 0.03, 0.007) for y, z in (
      (-0.116, 1.375), (-0.11, 1.41), (-0.08, 1.447), (-0.035, 1.472),
      (0.04, 1.474), (0.085, 1.447), (0.116, 1.41), (0.122, 1.375),
    )
  ], "shirt", n=4, side=(1, 0, 0))
  # Fanged face print, the design's signature.
  decal("print_crown", "shirt", print_polygon([
    (-0.125, 1.255), (-0.1, 1.31), (-0.07, 1.285), (-0.035, 1.325), (0, 1.295), (0.035, 1.325),
    (0.07, 1.285), (0.1, 1.31), (0.125, 1.255), (0.075, 1.125), (0, 1.09), (-0.075, 1.125),
  ]), "print_mid")
  decal("print_face", "shirt", print_polygon([
    (-0.082, 1.255), (-0.03, 1.285), (0.03, 1.285), (0.082, 1.255), (0.058, 1.14), (0, 1.11), (-0.058, 1.14),
  ]), "print_light", lift=0.01)
  for sign, side in ((1, "l"), (-1, "r")):
    decal("print_eye_" + side, "shirt", print_polygon([
      (sign * 0.018, 1.232), (sign * 0.062, 1.252), (sign * 0.055, 1.225), (sign * 0.024, 1.214),
    ]), "shirt", lift=0.014)
  decal("print_mouth", "shirt", print_polygon([
    (-0.052, 1.195), (0.052, 1.195), (0.035, 1.135), (0, 1.122), (-0.035, 1.135),
  ]), "shirt", lift=0.014)
  fangs = [(-0.044, 0.018, -1), (-0.018, 0.016, -1), (0.018, 0.016, -1), (0.044, 0.018, -1), (-0.022, 0.012, 1), (0.022, 0.012, 1)]
  for i, (x, half_width, direction) in enumerate(fangs):
    base = 1.195 if direction < 0 else 1.13
    tip = base + direction * 0.048 if direction < 0 else base + 0.03
    decal(f"print_fang_{i}", "shirt", print_polygon([(x - half_width, base), (x + half_width, base), (x, tip)]), "print_light", lift=0.018)


def build_hair():
  tube("hair_cap", [
    ((0, 0.05, 1.575), 0.065, 0.07),
    ((0, 0.03, 1.64), 0.09, 0.087),
    ((0, 0.01, 1.70), 0.1, 0.088),
    ((0, 0.005, 1.745), 0.09, 0.078),
    ((0, 0.005, 1.775), 0.04, 0.04),
  ], "hair", n=10)
  masses = [
    ((0.07, -0.01, 1.765), (0.06, 0.06, 0.05)),
    ((-0.07, -0.01, 1.765), (0.06, 0.06, 0.05)),
    ((0, 0.04, 1.795), (0.07, 0.07, 0.05)),
    ((0, -0.045, 1.78), (0.06, 0.05, 0.045)),
    ((0.105, 0.02, 1.70), (0.05, 0.065, 0.055)),
    ((-0.105, 0.02, 1.70), (0.05, 0.065, 0.055)),
    ((0.12, 0.03, 1.635), (0.05, 0.055, 0.05)),
    ((-0.12, 0.03, 1.635), (0.05, 0.055, 0.05)),
    ((0.06, 0.08, 1.735), (0.055, 0.05, 0.055)),
    ((-0.06, 0.08, 1.735), (0.055, 0.05, 0.055)),
    ((0, 0.095, 1.65), (0.065, 0.05, 0.06)),
  ]
  for i, (position, scale) in enumerate(masses):
    clump(f"hair_clump_{i}", position, scale, "hair", 58 + i)
  for i, x in enumerate((-0.062, -0.031, 0.0, 0.031, 0.062)):
    length = 0.125 if i in (1, 3) else 0.145
    tube(f"hair_bang_{i}", [
      ((x * 0.7, -0.07, 1.775), 0.022, 0.024),
      ((x, -0.103, 1.71), 0.018, 0.024),
      ((x, -0.108, 1.775 - length), 0.006, 0.012),
    ], "hair", n=5)
  both("hair_strand", [
    ((0.07, -0.06, 1.73), 0.009, 0.009),
    ((0.088, -0.075, 1.62), 0.008, 0.008),
    ((0.083, -0.07, 1.52), 0.005, 0.005),
  ], "hair", n=4)
  both("hair_braid", [
    ((0.115, 0.0, 1.66), 0.04, 0.04),
    ((0.15, -0.01, 1.625), 0.022, 0.022),
    ((0.17, -0.02, 1.59), 0.04, 0.04),
    ((0.178, -0.035, 1.55), 0.021, 0.021),
    ((0.178, -0.05, 1.515), 0.038, 0.038),
    ((0.172, -0.065, 1.475), 0.019, 0.019),
    ((0.164, -0.08, 1.44), 0.034, 0.034),
    ((0.155, -0.09, 1.405), 0.017, 0.017),
  ], "hair", n=6, zigzag=True)
  both("hair_ring", [
    ((0.154, -0.092, 1.41), 0.022, 0.022),
    ((0.151, -0.095, 1.385), 0.022, 0.022),
  ], "metal", n=6)
  both("hair_tip", [
    ((0.151, -0.095, 1.39), 0.017, 0.017),
    ((0.147, -0.098, 1.35), 0.003, 0.003),
  ], "hair", n=6)


def build_face():
  decal("mouth", "head", [(-0.027, 1.565), (0.027, 1.565), (0.022, 1.56), (-0.022, 1.56)], "skin_shadow", lift=0.003)
  for sign, side in ((1, "l"), (-1, "r")):
    strip("eye_" + side, "head", [
      (sign * 0.02, 1.625, 0.0015), (sign * 0.032, 1.631, 0.0085), (sign * 0.05, 1.631, 0.0085), (sign * 0.064, 1.628, 0.0015),
    ], "eye_white", depth=0.003)
    strip("iris_" + side, "head", [
      (sign * 0.035, 1.63, 0.0072), (sign * 0.048, 1.63, 0.0072),
    ], "iris", depth=0.0025, lift=0.0028)
    strip("eyelid_" + side, "head", [
      (sign * 0.018, 1.626, 0.0012), (sign * 0.032, 1.6375, 0.0028), (sign * 0.05, 1.6375, 0.0028), (sign * 0.068, 1.63, 0.0016),
    ], "hair", depth=0.004, lift=0.001)


def jacket_body():
  """Vest of the flag jacket; dropping the rings at the center draws the color chevrons."""
  # Entries are (height, front-back radius, width radius, center drop).
  levels = [
    (0.985, 0.13, 0.178, 0.0), (1.03, 0.13, 0.178, 0.0), (1.14, 0.125, 0.176, 0.02),
    (1.205, 0.124, 0.184, 0.09), (1.30, 0.128, 0.21, 0.07), (1.37, 0.124, 0.214, 0.05),
    (1.425, 0.11, 0.186, 0.0), (1.46, 0.092, 0.135, 0.0), (1.485, 0.074, 0.093, 0.0),
  ]
  band_colors = ["flag_red"] * 3 + ["flag_blue"] * 2 + ["flag_yellow"] * 3
  n = 16
  verts = []
  for z, front_back, width, drop in levels:
    for k in range(n):
      angle = 2 * math.pi * k / n
      verts.append(Vector((
        width * math.sin(angle),
        -front_back * math.cos(angle),
        z - drop * (1 - abs(math.sin(angle))),
      )))
  faces = []
  face_materials = []
  for i, color in enumerate(band_colors):
    for k in range(n):
      j = (k + 1) % n
      faces.append((i * n + k, i * n + j, (i + 1) * n + j, (i + 1) * n + k))
      face_materials.append(color)
  faces.append(tuple(reversed(range(n))))
  face_materials.append("flag_red")
  faces.append(tuple((len(levels) - 1) * n + k for k in range(n)))
  face_materials.append("flag_yellow")
  add_object("jacket", verts, faces, face_materials)


def star(name, surface, center, radius, back=False):
  points = []
  for k in range(10):
    angle = math.pi / 2 + math.pi * k / 5
    length = radius if k % 2 == 0 else radius * 0.42
    points.append((center[0] + length * math.cos(angle), center[1] + length * math.sin(angle)))
  decal(name, surface, points, "white", back=back)


def jacket_collar():
  """Folded collar, open at the front and higher at the back, so the neck can breathe."""
  steps = 12
  section = 4
  verts = []
  for k in range(steps + 1):
    angle = math.radians(32 + 296 * k / steps)
    top = 1.495 + 0.03 * (1 - math.cos(angle)) / 2
    for extra, z in ((0.0, 1.465), (-0.004, top), (0.01, top - 0.004), (0.016, 1.468)):
      verts.append(Vector((
        (0.086 + extra) * math.sin(angle),
        0.01 - (0.08 + extra) * math.cos(angle),
        z,
      )))
  faces = []
  for k in range(steps):
    for level in range(section):
      other = (level + 1) % section
      faces.append((
        k * section + level, k * section + other,
        (k + 1) * section + other, (k + 1) * section + level,
      ))
  faces.append((3, 2, 1, 0))
  last = steps * section
  faces.append((last, last + 1, last + 2, last + 3))
  add_object("collar", verts, faces, ["flag_yellow"] * len(faces))


def jersey_segment(left, bottom, width, height, code, digit):
  """One block of a 5 (digit 0) or 8 (digit 1) as an (x, z) rectangle."""
  thickness = 0.014
  right = left + width
  top = bottom + height
  middle = bottom + height / 2
  if code == "t":
    return [(left, top - thickness), (right, top - thickness), (right, top), (left, top)]
  if code == "b":
    return [(left, bottom), (right, bottom), (right, bottom + thickness), (left, bottom + thickness)]
  if code == "m":
    half = thickness / 2
    return [(left, middle - half), (right, middle - half), (right, middle + half), (left, middle + half)]
  if code == "l":
    low = middle if digit == 0 else bottom
    return [(left, low), (left + thickness, low), (left + thickness, top), (left, top)]
  if code == "c":
    return [(right - thickness, middle), (right, middle), (right, top), (right - thickness, top)]
  return [(right - thickness, bottom), (right, bottom), (right, middle), (right - thickness, middle)]


def build_jacket():
  jacket_body()
  sleeve = [(position, ru * 1.14, rv * 1.14) for position, ru, rv in arm_path(ARM_PATH)]
  # A smaller, lower start keeps the shoulder inside the jacket instead of peaking.
  (x, y, z), ru, rv = sleeve[0]
  sleeve[0] = ((x, y, z - 0.05), ru * 0.8, rv * 0.8)
  (x, y, z), ru, rv = sleeve[1]
  sleeve[1] = ((x, y, z - 0.03), ru * 0.9, rv * 0.9)
  bands = {0: "flag_yellow", 1: "flag_yellow", 2: "flag_blue", 3: "flag_blue"}
  both("sleeve", sleeve, "flag_red", bands=bands)
  tube("undershirt", [
    ((0, 0.01, 1.455), 0.08, 0.094),
    ((0, 0.01, 1.487), 0.066, 0.069),
  ], "white", n=10)
  jacket_collar()
  tree = surfaces["jacket"]
  zipper = []
  for step in range(17):
    z = 0.99 + step * 0.03
    zipper.append((tuple(tree.ray_cast(Vector((0.0005, -2.0, z)), Vector((0, 1, 0)))[0] - Vector((0, 0.003, 0))), 0.005, 0.009))
  tube("zipper", zipper, "white", n=4)
  # Eight stars, as on the flag: six on the chest and one on each sleeve.
  for sign, side in ((1, "l"), (-1, "r")):
    for i, (x, z) in enumerate(((0.05, 1.205), (0.11, 1.245), (0.172, 1.285))):
      star(f"star_{side}_{i}", "jacket", (sign * x, z), 0.03)
    star(f"star_{side}_sleeve", "sleeve_" + side, (sign * 0.242, 1.225), 0.025)
    # The third-person camera lives behind him, so the back carries the same stars.
    for i, (x, z) in enumerate(((0.04, 1.21), (0.1, 1.25), (0.158, 1.285))):
      star(f"star_back_{side}_{i}", "jacket", (sign * x, z), 0.03, back=True)
  # Jersey-style 58 on the back: the country code that names the game.
  for digit, (left, segments) in enumerate(((-0.062, "tlmrb"), (0.012, "tlcrbm"))):
    for code in segments:
      # Seen from behind, +X is on the viewer's left, so x flips to read correctly.
      polygon = [(-x, z) for x, z in jersey_segment(left, 1.03, 0.05, 0.078, code, digit)]
      decal(f"jersey_{digit}_{code}", "jacket", polygon, "white", back=True)
  # Chest patch: the flag with its arc of eight stars.
  left, right, top, stripe = 0.072, 0.138, 1.422, 0.0155
  for i, color in enumerate(("flag_yellow", "flag_blue", "flag_red")):
    upper = top - i * stripe
    decal(f"flag_{color}", "jacket", [(left, upper), (right, upper), (right, upper - stripe), (left, upper - stripe)], color, lift=0.012)
  decal("flag_border", "jacket", [(left - 0.004, top + 0.004), (right + 0.004, top + 0.004), (right + 0.004, top - 3 * stripe - 0.004), (left - 0.004, top - 3 * stripe - 0.004)], "white", lift=0.009)
  for i in range(8):
    angle = math.radians(155 - i * 130 / 7)
    x = (left + right) / 2 + 0.021 * math.cos(angle)
    z = top - 2.25 * stripe + 0.018 * math.sin(angle)
    decal(f"flag_star_{i}", "jacket", [(x - 0.0022, z - 0.0016), (x + 0.0022, z - 0.0016), (x, z + 0.0026)], "white", lift=0.0135)
  tube("jacket_hem", [
    ((0, 0, 0.982), 0.133, 0.181),
    ((0, 0, 1.012), 0.134, 0.182),
  ], "flag_red_dark", n=16)
  both("jacket_cuff", arm_path([
    ((0.367, -0.015, 0.93), 0.036, 0.036),
    ((0.378, -0.02, 0.885), 0.034, 0.032),
  ]), "flag_red_dark")
  pull_top, pull_bottom = (tree.ray_cast(Vector((0.0005, -2.0, z)), Vector((0, 1, 0)))[0] for z in (1.445, 1.41))
  tube("zipper_pull", [
    (tuple(pull_top - Vector((0, 0.008, 0))), 0.005, 0.007),
    (tuple(pull_bottom - Vector((0, 0.008, 0))), 0.004, 0.005),
  ], "metal", n=4)
  for sign, side in ((1, "l"), (-1, "r")):
    strip("jacket_pocket_" + side, "jacket", [(sign * 0.07, 1.115, 0.003), (sign * 0.14, 1.055, 0.003)], "flag_red_dark", depth=0.003)


def build_street_pants():
  tube("pelvis", [
    ((0, 0, 0.78), 0.10, 0.13),
    ((0, 0.008, 0.86), 0.128, 0.168),
    ((0, 0.004, 0.93), 0.126, 0.17),
    ((0, 0, 1.05), *variant["pelvis_top"]),
  ], "pants_black", n=10)
  both("leg", [
    ((0.09, 0, 0.92), 0.108, 0.088),
    ((0.098, 0, 0.76), 0.1, 0.09),
    ((0.106, -0.004, 0.54), 0.083, 0.078),
    ((0.112, 0, 0.5), 0.078, 0.073),
    ((0.12, 0.004, 0.34), 0.07, 0.066),
    ((0.125, 0.005, 0.24), 0.058, 0.052),
    ((0.125, 0.005, 0.2), 0.05, 0.046),
  ], "pants_black", n=10)
  for sign, side in ((1, "l"), (-1, "r")):
    surface = "leg_" + side
    # A raised piece, because a flat patch breaks across the pelvis and leg facets.
    pocket = []
    for z, width in ((0.95, 0.056), (0.9, 0.056), (0.86, 0.05), (0.84, 0.028)):
      hits = [
        tree.ray_cast(Vector((sign * 0.085, 2.0, z)), Vector((0, -1, 0)))[0]
        for tree in (surfaces["pelvis"], surfaces[surface])
      ]
      # The leg ends below the top of the pocket, so its ray can miss.
      depth = max(hit.y for hit in hits if hit is not None)
      pocket.append(((sign * 0.085, depth + 0.001, z), width, 0.004))
    tube("pants_back_pocket_" + side, pocket, "pants_pocket", n=4, side=(1, 0, 0))
    fold ={"depth": 0.003, "lift": 0.004}
    strip("pants_pocket_" + side, "pelvis", [(sign * 0.075, 0.975, 0.0025), (sign * 0.145, 0.915, 0.0025)], "seam", **fold)
    strip("pants_knee_a_" + side, surface, [(sign * 0.065, 0.565, 0.0025), (sign * 0.105, 0.55, 0.004), (sign * 0.15, 0.57, 0.0025)], "seam", **fold)
    strip("pants_knee_b_" + side, surface, [(sign * 0.07, 0.505, 0.0025), (sign * 0.11, 0.495, 0.004), (sign * 0.15, 0.51, 0.0025)], "seam", **fold)


def dashes(name, segments, mat):
  """Flat stitches. Each segment is (start, end, outward normal, half height vector)."""
  verts = []
  faces = []
  for start, end, normal, up in segments:
    base = len(verts)
    verts += [start - up, end - up, end + up, start + up]
    face = (base, base + 1, base + 2, base + 3)
    if (end - start).cross(up).dot(normal) < 0:
      face = tuple(reversed(face))
    faces.append(face)
  add_object(name, verts, faces, [mat] * len(faces), closed=False)


def boot_ring(x0, z, front, back, width, n):
  center = (front + back) / 2
  half_length = (back - front) / 2
  points = []
  for k in range(n):
    angle = 2 * math.pi * k / n
    forward = math.cos(angle)
    # Wider at the toe than at the heel, with a rounded, boxy outline.
    side = math.copysign(abs(math.sin(angle)) ** 0.8, math.sin(angle)) * width * (0.9 + 0.1 * forward)
    points.append(Vector((x0 + side, center - half_length * forward, z)))
  return points


def welt_stitches(x0, ring, center_y):
  lengths = [(ring[i + 1 - len(ring)] - ring[i]).length for i in range(len(ring))]
  perimeter = sum(lengths)

  def point_at(distance):
    distance %= perimeter
    for i, length in enumerate(lengths):
      if distance <= length:
        return ring[i].lerp(ring[i + 1 - len(ring)], distance / length)
      distance -= length
    return ring[0]

  segments = []
  count = int(perimeter / 0.022)
  for i in range(count):
    distance = perimeter * i / count
    start = point_at(distance)
    end = point_at(distance + 0.013)
    middle = (start + end) / 2
    normal = Vector((middle.x - x0, middle.y - center_y, 0)).normalized()
    offset = normal * 0.0015
    segments.append((start + offset, end + offset, normal, Vector((0, 0, 0.002))))
  return segments


def side_stitches(tree, x0):
  segments = []
  for direction in (1, -1):
    for radius in (0.078, 0.066):
      steps = 8
      for i in range(steps):
        points = []
        for fraction in (i, i + 0.65):
          angle = math.radians(150 - 135 * fraction / steps)
          origin = Vector((x0 + direction * 0.3, -0.012 + radius * math.cos(angle), 0.035 + radius * math.sin(angle)))
          points.append(tree.ray_cast(origin, Vector((-direction, 0, 0))))
        start, normal = points[0][0], points[0][1]
        end = points[1][0]
        if start is None or end is None:
          continue
        up = normal.cross(end - start).normalized() * 0.002
        offset = normal * 0.0015
        segments.append((start + offset, end + offset, normal, up))
  return segments


def boot(side, sign):
  x0 = sign * 0.125
  n = 16
  # Stacked outlines of one continuous shape: (height, toe, heel, width).
  levels = [
    (0.0, -0.2, 0.09, 0.06), (0.026, -0.212, 0.098, 0.066), (0.03, -0.206, 0.094, 0.062),
    (0.07, -0.2, 0.094, 0.061), (0.1, -0.172, 0.09, 0.057), (0.125, -0.125, 0.085, 0.054),
    (0.15, -0.085, 0.08, 0.052), (0.19, -0.068, 0.074, 0.052), (0.225, -0.066, 0.074, 0.056),
    (0.255, -0.068, 0.078, 0.063),
  ]
  rings_points = [boot_ring(x0, *level, n) for level in levels]
  verts = [point for ring in rings_points for point in ring]
  faces = []
  face_materials = []
  for i in range(len(levels) - 1):
    for k in range(n):
      j = (k + 1) % n
      faces.append((i * n + k, i * n + j, (i + 1) * n + j, (i + 1) * n + k))
      face_materials.append("boot_sole" if i < 2 else "boot_leather")
  faces.append(tuple(reversed(range(n))))
  face_materials.append("boot_sole")
  faces.append(tuple((len(levels) - 1) * n + k for k in range(n)))
  face_materials.append("boot_sole")
  surface = "boot_" + side
  add_object(surface, verts, faces, face_materials)
  tree = surfaces[surface]

  dashes("boot_welt_stitch_" + side, welt_stitches(x0, rings_points[1], -0.057), "stitch_yellow")
  dashes("boot_side_stitch_" + side, side_stitches(tree, x0), "boot_stitch")

  panel = []
  for z in (0.25, 0.21, 0.175, 0.15, 0.132, 0.118):
    hit = tree.ray_cast(Vector((x0 + 0.0004, -2.0, z)), Vector((0, 1, 0)))[0]
    panel.append((tuple(hit - Vector((0, 0.002, 0))), 0.026, 0.003))
  panel_name = "boot_panel_" + side
  tube(panel_name, panel, "boot_soft", n=4, side=(1, 0, 0))
  for i, z in enumerate((0.24, 0.215, 0.19, 0.165, 0.143, 0.127)):
    hexagon = [
      (x0 + 0.0068 * math.cos(math.pi * k / 3), z + 0.0068 * math.sin(math.pi * k / 3))
      for k in range(6)
    ]
    decal(f"boot_eyelet_{side}_{i}", panel_name, hexagon, "boot_sole", lift=0.0015)

  tube("boot_tongue_" + side, [
    ((x0, -0.068, 0.235), 0.03, 0.012),
    ((x0, -0.072, 0.262), 0.03, 0.012),
    ((x0, -0.068, 0.282), 0.022, 0.01),
  ], "boot_leather", n=6, side=(1, 0, 0))
  tube("boot_pull_tab_" + side, [
    ((x0, 0.078, 0.232), 0.016, 0.006),
    ((x0, 0.086, 0.268), 0.016, 0.006),
    ((x0, 0.082, 0.296), 0.015, 0.007),
    ((x0, 0.07, 0.305), 0.012, 0.006),
  ], "boot_soft", n=6, side=(1, 0, 0))


def build_boots():
  boot("l", 1)
  boot("r", -1)


def raise_head():
  """Lifts the head, hair and face together, leaving a visible neck under the jaw."""
  lift = Matrix.Translation((0, 0, HEAD_LIFT))
  for obj in parts:
    if obj.name.startswith(("head", "nose")) or obj in head_parts:
      obj.data.transform(lift)
      obj.data.update()


def build_curly_hair():
  head_parts_start = len(parts)
  build_curly_hair_parts()
  build_male_face()
  head_parts.extend(parts[head_parts_start:])
  raise_head()


def build_curly_hair_parts():
  tube("hair_cap", [
    ((0, 0.02, 1.565), 0.05, 0.058),
    ((0, 0.04, 1.60), 0.056, 0.072),
    ((0, 0.02, 1.65), 0.085, 0.086),
    ((0, 0.006, 1.705), 0.096, 0.09),
    ((0, 0.005, 1.75), 0.088, 0.08),
    ((0, 0.005, 1.778), 0.04, 0.04),
  ], "hair_dark", n=10)
  rng = random.Random(58)
  # Curls sit on top; the sides stay short, as in a fade.
  index = 0
  for radius, z, count, highlight in ((0.09, 1.725, 14, 0.08), (0.068, 1.76, 11, 0.22), (0.034, 1.78, 6, 0.35)):
    for k in range(count):
      angle = 2 * math.pi * (k + rng.random() * 0.4) / count
      position = (radius * math.cos(angle), 0.004 + radius * 1.05 * math.sin(angle), z + rng.uniform(-0.008, 0.008))
      size = rng.uniform(0.019, 0.027)
      color = "hair_light" if rng.random() < highlight else "hair_dark"
      clump(f"curl_{index}", position, (size, size, size * 0.85), color, 100 + index)
      index += 1
  for i, (x, z) in enumerate(((-0.05, 1.712), (-0.012, 1.703), (0.03, 1.708), (0.066, 1.72))):
    clump(f"curl_front_{i}", (x, -0.086, z), (0.022, 0.019, 0.02), "hair_light" if i == 1 else "hair_dark", 140 + i)


def male_nose():
  """One piece rooted in the face: bridge, tip and wings share the same surface."""
  # Entries are (height, root half width, root depth, side half width, side depth, ridge depth).
  levels = [
    (1.655, 0.011, -0.085, 0.007, -0.094, -0.097),
    (1.622, 0.014, -0.08, 0.009, -0.1, -0.106),
    (1.6, 0.024, -0.08, 0.018, -0.103, -0.114),
    (1.588, 0.024, -0.08, 0.018, -0.1, -0.11),
    (1.578, 0.016, -0.08, 0.011, -0.093, -0.098),
  ]
  n = 5
  verts = []
  for z, root_width, root_y, side_width, side_y, ridge_y in levels:
    verts += [
      Vector((-root_width, root_y, z)), Vector((-side_width, side_y, z)), Vector((0, ridge_y, z)),
      Vector((side_width, side_y, z)), Vector((root_width, root_y, z)),
    ]
  faces = []
  for i in range(len(levels) - 1):
    for k in range(n):
      j = (k + 1) % n
      faces.append((i * n + k, i * n + j, (i + 1) * n + j, (i + 1) * n + k))
  faces.append(tuple(reversed(range(n))))
  faces.append(tuple((len(levels) - 1) * n + k for k in range(n)))
  add_object("nose", verts, faces, [variant["skin"]] * len(faces))


def build_male_face():
  male_nose()
  chin = [
    surfaces["head"].ray_cast(Vector((0.0004, -2.0, z)), Vector((0, 1, 0)))[0]
    for z in (1.552, 1.54, 1.526)
  ]
  tube("goatee", [(tuple(point), 0.024, 0.004) for point in chin], "hair_dark", n=4, side=(1, 0, 0))
  strip("mustache", "head", [
    (-0.03, 1.578, 0.001), (-0.011, 1.581, 0.004), (0, 1.58, 0.003), (0.011, 1.581, 0.004), (0.03, 1.578, 0.001),
  ], "stubble", depth=0.003)
  strip("upper_lip", "head", [
    (-0.027, 1.569, 0.001), (-0.012, 1.572, 0.004), (0, 1.5705, 0.0035), (0.012, 1.572, 0.004), (0.027, 1.569, 0.001),
  ], "lips", depth=0.004)
  strip("lower_lip", "head", [(-0.021, 1.564, 0.001), (0, 1.561, 0.006), (0.021, 1.564, 0.001)], "lips", depth=0.005)
  strip("mouth_line", "head", [(-0.027, 1.568, 0.0012), (0, 1.5665, 0.0012), (0.027, 1.568, 0.0012)], "iris", depth=0.0055)
  for sign, side in ((1, "l"), (-1, "r")):
    strip("brow_ridge_" + side, "head", [
      (sign * 0.008, 1.648, 0.009), (sign * 0.04, 1.655, 0.013), (sign * 0.076, 1.653, 0.007),
    ], variant["skin"], depth=0.008)
    strip("brow_" + side, "head", [
      (sign * 0.011, 1.649, 0.006), (sign * 0.03, 1.657, 0.0085), (sign * 0.052, 1.661, 0.0075), (sign * 0.075, 1.657, 0.002),
    ], "hair_dark", depth=0.005, lift=0.008)
    strip("eye_" + side, "head", [
      (sign * 0.024, 1.634, 0.0012), (sign * 0.036, 1.638, 0.0065), (sign * 0.052, 1.637, 0.0065), (sign * 0.067, 1.634, 0.0012),
    ], "eye_white", depth=0.003)
    strip("iris_" + side, "head", [
      (sign * 0.04, 1.637, 0.0055), (sign * 0.051, 1.637, 0.0055),
    ], "iris", depth=0.0025, lift=0.0028)
    strip("eyelid_" + side, "head", [
      (sign * 0.021, 1.635, 0.0012), (sign * 0.036, 1.6425, 0.0026), (sign * 0.053, 1.6415, 0.0026), (sign * 0.07, 1.635, 0.0012),
    ], "hair_dark", depth=0.004, lift=0.001)
    tube("ear_" + side, [
      ((sign * 0.08, 0.008, 1.645), 0.012, 0.01),
      ((sign * 0.09, 0.012, 1.62), 0.022, 0.009),
      ((sign * 0.082, 0.004, 1.593), 0.01, 0.008),
    ], variant["skin"], n=5)
    tube("gauge_" + side, [
      ((sign * 0.082, 0.004, 1.586), 0.014, 0.014),
      ((sign * 0.086, 0.004, 1.586), 0.014, 0.014),
    ], "iris", n=8, side=(0, 1, 0))
  tube("nose_ring", [
    ((-0.006, -0.097, 1.582), 0.0018, 0.0018),
    ((0.0, -0.1, 1.574), 0.0018, 0.0018),
    ((0.006, -0.097, 1.582), 0.0018, 0.0018),
  ], "metal", n=4, side=(0, 0, 1))
  for sign, side in ((1, "l"), (-1, "r")):
    tube("sideburn_" + side, [
      ((sign * 0.079, 0.012, 1.68), 0.012, 0.005),
      ((sign * 0.08, 0.008, 1.64), 0.009, 0.004),
      ((sign * 0.079, 0.0, 1.615), 0.004, 0.002),
    ], "hair_dark", n=4)


def start(name):
  global variant
  variant = VARIANTS[name]
  surfaces.clear()
  parts.clear()
  head_parts.clear()


def skeleton():
  """Bones as name: (head, tail, parent), for the side +X; _l bones get a mirrored _r twin."""
  lift = HEAD_LIFT if variant["fingers"] else 0.0
  shoulder, elbow, wrist = (arm_path(ARM_PATH)[i][0] for i in (1, 4, 7))
  shift = variant["arm_shift"]
  hand_end = (0.405 + shift, -0.03, 0.79)
  finger_end = (0.424 + shift, -0.03, 0.72)
  thumb_end = (0.385 + shift, -0.085, 0.775)
  ankle_x = 0.125 if variant["fingers"] else 0.145
  hip = (0.095, 0, 0.93)
  knee = (0.11, -0.015, 0.5)
  ankle = (ankle_x, 0.01, 0.1)
  ball = (ankle_x, -0.1, 0.04)
  toe = (ankle_x, -0.2, 0.04)
  return {
    # Carries root motion, so it sits on the ground and has no vertex weights.
    "root": ((0, 0, 0), (0, 0.2, 0), None),
    "hips": ((0, 0, 0.93), (0, 0, 1.05), "root"),
    "spine": ((0, 0, 1.05), (0, 0, 1.2), "hips"),
    "chest": ((0, 0, 1.2), (0, 0, 1.42), "spine"),
    "neck": ((0, 0.01, 1.45), (0, 0.004, 1.55 + lift), "chest"),
    "head": ((0, 0.004, 1.55 + lift), (0, 0.004, 1.77 + lift), "neck"),
    "shoulder_l": ((0.05, 0, 1.42), shoulder, "chest"),
    "upper_arm_l": (shoulder, elbow, "shoulder_l"),
    "lower_arm_l": (elbow, wrist, "upper_arm_l"),
    "hand_l": (wrist, hand_end, "lower_arm_l"),
    "fingers_l": (hand_end, finger_end, "hand_l"),
    "thumb_l": ((0.375 + shift, -0.045, 0.86), thumb_end, "hand_l"),
    "upper_leg_l": (hip, knee, "hips"),
    "lower_leg_l": (knee, ankle, "upper_leg_l"),
    "foot_l": (ankle, ball, "lower_leg_l"),
    "toes_l": (ball, toe, "foot_l"),
    # Grip point of whatever the hand holds; it points along the weapon.
    "weapon": ((-hand_end[0], hand_end[1], hand_end[2]), (-hand_end[0], hand_end[1] - 0.2, hand_end[2]), "hand_r"),
  }


def mirrored_bones(bones):
  result = {}
  for name, (head, tail, parent) in bones.items():
    result[name] = (head, tail, parent)
    if name.endswith("_l"):
      flip = lambda point: (-point[0], point[1], point[2])
      twin_parent = parent[:-2] + "_r" if parent.endswith("_l") else parent
      result[name[:-2] + "_r"] = (flip(head), flip(tail), twin_parent)
  return result


def bone_candidates(part_name, side):
  """Bones a part may follow, so a thigh never gets pulled by the hand next to it."""
  name = part_name.split(".")[0]
  if name.startswith(("arm", "sleeve", "hand", "jacket_cuff")) or (name.startswith("star") and "sleeve" in name):
    return ["chest", "shoulder" + side, "upper_arm" + side, "lower_arm" + side, "hand" + side, "fingers" + side]
  if name.startswith("finger"):
    return ["hand" + side, "fingers" + side]
  if name.startswith("thumb"):
    return ["hand" + side, "thumb" + side]
  if name.startswith(("boot", "shoe")):
    return ["lower_leg" + side, "foot" + side, "toes" + side]
  if name.startswith(("leg", "rip", "cargo", "pants")):
    return ["hips", "upper_leg" + side, "lower_leg" + side]
  if name.startswith(("pelvis", "belt", "buckle", "fly", "jacket_hem")):
    return ["hips", "spine", "upper_leg_l", "upper_leg_r"]
  if name == "neck":
    return ["chest", "neck", "head"]
  if name.startswith(("collar", "undershirt")):
    return ["chest", "neck"]
  return ["hips", "spine", "chest", "shoulder_l", "shoulder_r"]


HEAD_PREFIXES = (
  "head", "nose", "hair", "curl", "mouth", "eye", "iris", "brow", "ear", "gauge", "goatee",
  "mustache", "upper_lip", "lower_lip", "lips", "sideburn",
)


def segment_distance(point, head, tail):
  axis = tail - head
  amount = max(0.0, min(1.0, (point - head).dot(axis) / axis.length_squared))
  return (point - (head + axis * amount)).length


def assign_weights(part, bones):
  name = part.name.split(".")[0]
  if name.startswith(HEAD_PREFIXES):
    part.vertex_groups.new(name="head").add(list(range(len(part.data.vertices))), 1.0, "REPLACE")
    return
  middle = sum((v.co for v in part.data.vertices), Vector()) / len(part.data.vertices)
  side = "_l" if middle.x >= 0 else "_r"
  names = bone_candidates(name, side)
  segments = [(bone, Vector(bones[bone][0]), Vector(bones[bone][1])) for bone in names]
  groups = {bone: part.vertex_groups.new(name=bone) for bone in names}
  for vertex in part.data.vertices:
    closeness = sorted(
      ((1.0 / (segment_distance(vertex.co, head, tail) + 0.015) ** 4, bone) for bone, head, tail in segments),
      reverse=True,
    )[:3]
    total = sum(weight for weight, _ in closeness)
    for weight, bone in closeness:
      groups[bone].add([vertex.index], weight / total, "REPLACE")


def build_armature(name, bones, scale):
  data = bpy.data.armatures.new(name + "_armature")
  armature = bpy.data.objects.new("armature_" + name, data)
  collection().objects.link(armature)
  bpy.context.view_layer.objects.active = armature
  bpy.ops.object.mode_set(mode="EDIT")
  created = {}
  for bone, (head, tail, _) in bones.items():
    edit_bone = data.edit_bones.new(bone)
    edit_bone.head = Vector(head) * scale
    edit_bone.tail = Vector(tail) * scale
    created[bone] = edit_bone
  for bone, (_, _, parent) in bones.items():
    if parent:
      created[bone].parent = created[parent]
  bpy.ops.object.mode_set(mode="OBJECT")
  return armature


def finish(name):
  bones = mirrored_bones(skeleton())
  for part in parts:
    assign_weights(part, bones)
  window = bpy.context.window_manager.windows[0] if bpy.context.window_manager.windows else None
  with bpy.context.temp_override(window=window, active_object=parts[0], selected_editable_objects=list(parts)):
    bpy.ops.object.join()
  body = parts[0]
  body.name = "protagonist_" + name
  body.data.name = body.name
  body.data.transform(Matrix.Scale(variant["height_scale"], 4))
  body.data.update()
  armature = build_armature(name, bones, variant["height_scale"])
  body.parent = armature
  body.modifiers.new("armature", "ARMATURE").object = armature
  triangles = sum(len(polygon.vertices) - 2 for polygon in body.data.polygons)
  z_values = [v.co.z for v in body.data.vertices]
  print(name, "triangles", triangles, "z", round(min(z_values), 3), round(max(z_values), 3))

  os.makedirs(GLB_DIR, exist_ok=True)
  for other in bpy.data.objects:
    other.hide_set(other not in (body, armature))
  bpy.ops.export_scene.gltf(
    filepath=os.path.join(GLB_DIR, body.name + ".glb"),
    export_format="GLB",
    use_visible=True,
  )
  for other in bpy.data.objects:
    other.hide_set(False)
  # Only for viewing both in Blender; the exported file stays centered.
  armature.location.x = variant["display_x"]


def save():
  bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)


def stages_for(name, builders):
  return [lambda: start(name), build_body] + builders + [lambda: finish(name)]


STAGES = (
  [clear]
  + stages_for("male", [build_street_pants, build_boots, build_jacket, build_curly_hair])
  + stages_for("female", [build_pants, build_shirt, build_hair, build_face])
  + [save]
)

if __name__ == "__main__":
  for stage in STAGES:
    stage()
