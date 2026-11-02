# Builds the male and female protagonist from code so proportions can be tweaked and rebuilt.
# Faces -Y with feet on the origin, in A-pose for rigging. +X is the character's left.
# The male is colored afterwards by paint_protagonist.py; the female keeps flat materials.
#   blender --background --python art/characters/build_protagonist.py
import bisect
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
    "skin": "skin_tan",
    "fingers": True,
    "arm_shift": -0.03,
    "arm_scale": 1.08,
  },
  "female": {
    "height_scale": 0.96,
    "display_x": 0.7,
    "skin": "skin",
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
  "skin_tan": (0.66, 0.44, 0.31),
  "head_skin": (0.66, 0.44, 0.31),
  "ear_gauge": (0.10, 0.09, 0.09),
  "eye_white": (0.90, 0.88, 0.84),
  "iris": (0.13, 0.08, 0.06),
  "hair_lock": (0.13, 0.09, 0.07),
  "flag_yellow": (0.98, 0.76, 0.10),
  "flag_red": (0.82, 0.08, 0.10),
  "white": (0.95, 0.95, 0.93),
  "tee_rib": (0.84, 0.84, 0.82),
  "jacket_shell": (0.82, 0.08, 0.10),
  "jacket_sleeve": (0.82, 0.08, 0.10),
  "jacket_lining": (0.30, 0.06, 0.09),
  "zipper_tape": (0.12, 0.13, 0.17),
  "pants_black": (0.13, 0.13, 0.15),
  "flag_red_dark": (0.58, 0.05, 0.07),
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
# Per lock: how far along it each vertex sits, and the two bones of its chain, if any.
hair_weights = {}
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
  tube("neck", rings(variant["neck"]), skin, n=8)
  tube("head", rings(variant["head"]), skin, n=10, bands=variant["head_bands"])
  tube("nose", variant["nose"], skin, n=4)
  both("arm", arm_path(ARM_PATH), skin)
  both("hand", arm_path([
    ((0.375, -0.02, 0.89), 0.03, 0.02),
    ((0.395, -0.025, 0.83), 0.048, 0.022),
    ((0.41, -0.03, 0.77), 0.042, 0.018),
    ((0.42, -0.03, 0.72), 0.02, 0.01),
  ]), skin, n=6)
  thumb(skin)


def thumb(skin):
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


def smooth(edge0, edge1, value):
  amount = max(0.0, min(1.0, (value - edge0) / (edge1 - edge0)))
  return amount * amount * (3 - 2 * amount)


def gauss(value, center, width):
  return math.exp(-((value - center) / width) ** 2)


def spline(path, steps):
  """Catmull-Rom through tube entries, so a few key rings give a soft form."""
  rows = [(*position, ru, rv) for position, ru, rv in path]
  last = len(rows) - 1
  result = []
  for i in range(last):
    a, b, c, d = rows[max(i - 1, 0)], rows[i], rows[i + 1], rows[min(i + 2, last)]
    for step in range(steps):
      t = step / steps
      result.append(tuple(
        0.5 * (2 * q + (r - p) * t + (2 * p - 5 * q + 4 * r - s) * t * t + (3 * q - p - 3 * r + s) * t ** 3)
        for p, q, r, s in zip(a, b, c, d)
      ))
  result.append(rows[last])
  return [((x, y, z), ru, rv) for x, y, z, ru, rv in result]


def profile(table):
  """Smooth curve through (input, output) pairs."""
  table = sorted(table)
  keys = [key for key, _ in table]
  values = [value for _, value in table]
  last = len(table) - 1
  slopes = [
    (values[min(i + 1, last)] - values[max(i - 1, 0)]) / (keys[min(i + 1, last)] - keys[max(i - 1, 0)])
    for i in range(last + 1)
  ]

  def evaluate(x):
    x = max(keys[0], min(keys[last], x))
    i = min(bisect.bisect_right(keys, x) - 1, last - 1)
    span = keys[i + 1] - keys[i]
    t = (x - keys[i]) / span
    return (
      (2 * t ** 3 - 3 * t ** 2 + 1) * values[i] + (t ** 3 - 2 * t ** 2 + t) * span * slopes[i]
      + (3 * t ** 2 - 2 * t ** 3) * values[i + 1] + (t ** 3 - t ** 2) * span * slopes[i + 1]
    )

  return evaluate


def ring_faces(rows, columns, closed=True):
  faces = []
  for i in range(rows - 1):
    for k in range(columns if closed else columns - 1):
      j = (k + 1) % columns
      faces.append((i * columns + k, i * columns + j, (i + 1) * columns + j, (i + 1) * columns + k))
  return faces


def set_panel(obj, values):
  """Per-vertex (across, along, seed) for the painter; hair streaks and fades with it."""
  attribute = obj.data.attributes.new("panel", "FLOAT_VECTOR", "POINT")
  attribute.data.foreach_set("vector", [channel for value in values for channel in value])


# The skull is a stack of rings and the face a relief on it, so features stay where the texture expects.
HEAD_WIDTH = profile([
  (1.543, 0.016), (1.548, 0.036), (1.556, 0.053), (1.57, 0.068), (1.59, 0.077), (1.61, 0.083), (1.63, 0.088),
  (1.66, 0.093), (1.70, 0.097), (1.74, 0.095), (1.78, 0.083), (1.81, 0.058), (1.828, 0.03), (1.835, 0.006),
])
HEAD_FRONT = profile([
  (1.543, 0.074), (1.55, 0.086), (1.57, 0.095), (1.60, 0.098), (1.64, 0.1), (1.70, 0.108), (1.74, 0.106),
  (1.78, 0.09), (1.81, 0.062), (1.828, 0.03), (1.835, 0.006),
])
HEAD_BACK = profile([
  (1.543, 0.004), (1.56, 0.02), (1.60, 0.055), (1.64, 0.09), (1.70, 0.116), (1.76, 0.105), (1.80, 0.075),
  (1.825, 0.035), (1.835, 0.006),
])
HEAD_ROWS = (
  1.543, 1.548, 1.553, 1.559, 1.565, 1.571, 1.577, 1.583, 1.589, 1.595, 1.602, 1.609, 1.616, 1.623, 1.63,
  1.637, 1.645, 1.653, 1.661, 1.669, 1.677, 1.686, 1.70, 1.72, 1.745, 1.77, 1.795, 1.815, 1.829, 1.835,
)


def face_relief(x, z):
  side = abs(x)
  return (
    0.005 * gauss(z, 1.688, 0.012) * gauss(side, 0.04, 0.036)
    - 0.009 * gauss(z, 1.663, 0.015) * gauss(side, 0.044, 0.026)
    + 0.012 * gauss(x, 0, 0.0095) * smooth(1.685, 1.645, z) * smooth(1.6, 1.625, z)
    + 0.015 * gauss(x, 0, 0.0125) * gauss(z, 1.63, 0.013)
    + 0.0065 * gauss(side, 0.0165, 0.007) * gauss(z, 1.622, 0.0075)
    - 0.002 * gauss(x, 0, 0.006) * gauss(z, 1.604, 0.005)
    + 0.0042 * gauss(x, 0, 0.022) * gauss(z, 1.594, 0.0055)
    + 0.0045 * gauss(x, 0, 0.017) * gauss(z, 1.58, 0.0062)
    - 0.0022 * gauss(x, 0, 0.018) * gauss(z, 1.57, 0.0048)
    + 0.0065 * gauss(x, 0, 0.027) * gauss(z, 1.554, 0.012)
    + 0.0042 * gauss(side, 0.066, 0.02) * gauss(z, 1.628, 0.02)
  )


def head_point(angle, z):
  """angle 0 looks at the front and grows towards the character's left."""
  sine = math.sin(angle)
  cosine = math.cos(angle)
  x = HEAD_WIDTH(z) * math.copysign(abs(sine) ** 0.92, sine)
  y = -cosine * (HEAD_FRONT(z) if cosine > 0 else HEAD_BACK(z))
  if cosine > 0:
    y -= face_relief(x, z) * smooth(0.0, 0.5, cosine)
  return Vector((x, y, z))


def build_head():
  columns = 32
  verts = []
  for z in HEAD_ROWS:
    for k in range(columns):
      s = -1 + 2 * k / columns
      verts.append(head_point(math.pi * (0.55 * s + 0.45 * s ** 3), z))
  faces = ring_faces(len(HEAD_ROWS), columns)
  faces.append(tuple(reversed(range(columns))))
  faces.append(tuple((len(HEAD_ROWS) - 1) * columns + k for k in range(columns)))
  add_object("head", verts, faces, ["head_skin"] * len(faces))
  tube("neck", spline([
    ((0, 0.014, 1.455), 0.084, 0.1), ((0, 0.016, 1.5), 0.068, 0.078), ((0, 0.014, 1.54), 0.062, 0.067),
    ((0, 0.01, 1.58), 0.062, 0.064), ((0, 0.006, 1.625), 0.064, 0.066),
  ], 2), "skin_tan", n=12)
  for sign, side in ((1, "l"), (-1, "r")):
    tube("ear_" + side, spline([
      ((sign * 0.086, 0.012, 1.682), 0.01, 0.006),
      ((sign * 0.1, 0.022, 1.672), 0.021, 0.0065),
      ((sign * 0.103, 0.026, 1.652), 0.021, 0.0065),
      ((sign * 0.097, 0.018, 1.632), 0.015, 0.0065),
      ((sign * 0.09, 0.008, 1.622), 0.011, 0.006),
    ], 1), "skin_tan", n=6, side=(0, 1, 0))
    tube("gauge_" + side, [
      ((sign * 0.088, 0.012, 1.625), 0.012, 0.012),
      ((sign * 0.104, 0.012, 1.625), 0.012, 0.012),
    ], "ear_gauge", n=8, side=(0, 1, 0))
  tip = [
    surfaces["head"].ray_cast(Vector((x, -2.0, z)), Vector((0, 1, 0)))[0]
    for x, z in ((-0.008, 1.616), (0.0004, 1.61), (0.008, 1.616))
  ]
  tube("nose_ring", [
    ((-0.0055, tip[0].y + 0.004, 1.613), 0.0012, 0.0012),
    ((-0.0028, tip[1].y - 0.002, 1.606), 0.0012, 0.0012),
    ((0.0028, tip[1].y - 0.002, 1.606), 0.0012, 0.0012),
    ((0.0055, tip[2].y + 0.004, 1.613), 0.0012, 0.0012),
  ], "metal", n=5, side=(0, 0, 1))


# Hair grows over this shell, which sits just outside the skull, so a lock can't enter the head.
HAIR_CENTER = Vector((0, 0.004, 1.695))
HAIR_RADII = Vector((0.102, 0.122, 0.15))
# Across a lock: pointed to the sides, ridged on the outside.
LOCK_SECTION = ((-1.0, 0.0), (0.0, 0.62), (1.0, 0.0), (0.45, -0.4), (-0.45, -0.4))
# (start azimuth, start elevation, end azimuth, end elevation, width, tip flick, chain). Azimuth is
# 0 at the front and grows towards the character's left. Mirrored entries are written out because
# a parted head of hair is never symmetric.
HAIR_LOCKS = [
  # Fringe, parted left of center.
  (6, 82, -34, 14, 0.066, 0.1, None),
  (-10, 78, -58, 4, 0.062, 0.14, "front"),
  (-28, 70, -74, -10, 0.056, 0.16, "front"),
  (22, 80, 30, 16, 0.06, 0.1, None),
  (38, 72, 60, 2, 0.058, 0.14, "front"),
  (12, 74, 4, 24, 0.036, 0.06, None),
  # Strands that frame the face.
  (-56, 46, -82, -44, 0.04, 0.14, "front"),
  (58, 44, 84, -40, 0.04, 0.14, "front"),
  # Sides, tucked behind the ears so the gauges show.
  (74, 64, 106, 4, 0.06, 0.2, "side"),
  (92, 68, 124, -24, 0.062, 0.2, "side"),
  (112, 66, 142, -36, 0.064, 0.2, "side"),
  (-76, 62, -108, 2, 0.06, 0.2, "side"),
  (-94, 68, -126, -26, 0.062, 0.2, "side"),
  (-114, 66, -144, -34, 0.064, 0.2, "side"),
  # Back of the head, over a longer layer that reaches the collar.
  (134, 74, 152, -36, 0.066, 0.18, "back"),
  (156, 80, 170, -42, 0.068, 0.14, "back"),
  (184, 82, 198, -40, 0.068, 0.16, "back"),
  (208, 78, 222, -36, 0.066, 0.18, "back"),
  (128, 26, 144, -52, 0.05, 0.24, "back"),
  (152, 30, 164, -56, 0.052, 0.22, "back"),
  (176, 32, 184, -58, 0.052, 0.22, "back"),
  (200, 30, 210, -54, 0.052, 0.22, "back"),
  (224, 26, 232, -48, 0.05, 0.24, "back"),
  # Top, for volume; the skull is painted as hair underneath.
  (20, 88, 92, 46, 0.068, 0.1, None),
  (-20, 88, -96, 42, 0.068, 0.1, None),
  (70, 84, 150, 44, 0.07, 0.1, None),
  (-70, 84, -150, 46, 0.07, 0.1, None),
  (170, 88, 186, 30, 0.07, 0.1, None),
  (50, 76, 118, 30, 0.056, 0.12, None),
  (-48, 76, -122, 28, 0.056, 0.12, None),
]
HAIR_CHAINS = {}


def shell_point(azimuth, elevation, lift):
  a = math.radians(azimuth)
  e = math.radians(elevation)
  direction = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
  return HAIR_CENTER + Vector(d * r * (1 + lift) for d, r in zip(direction, HAIR_RADII))


def lock_path(entry, seed):
  az0, el0, az1, el1, _, flick, _ = entry
  rng = random.Random(seed)
  az1 += rng.uniform(-3, 3)
  el1 += rng.uniform(-3, 3)
  bulge = rng.uniform(0.11, 0.19)
  wave = rng.uniform(5, 10) * rng.choice((-1, 1))
  path = []
  for i in range(7):
    t = i / 6
    # Falls off the crown quickly, then hangs and flicks out at the tip.
    along = 1 - (1 - t) ** 1.6
    lift = bulge * math.sin(min(t * 1.15, 1.0) * math.pi) + flick * t ** 3
    azimuth = az0 + (az1 - az0) * t ** 0.8 + wave * math.sin(t * 5.5)
    path.append(shell_point(azimuth, el0 + (el1 - el0) * along, lift))
  return path


def lock(name, path, width, chain):
  verts = []
  panel = []
  count = len(path)
  seed = random.Random(name).random()
  for i, point in enumerate(path):
    t = i / (count - 1)
    tangent = (path[min(i + 1, count - 1)] - path[max(i - 1, 0)]).normalized()
    outward = point - HAIR_CENTER
    outward = (outward - outward.project(tangent)).normalized()
    across = tangent.cross(outward)
    half = width * 0.75 * min(1.0, 0.6 + t * 2.2) * (1 - t) ** 0.7 + 0.0008
    for k, (a, b) in enumerate(LOCK_SECTION):
      verts.append(point + across * a * half + outward * b * half)
      panel.append((abs(a), t, seed))
  columns = len(LOCK_SECTION)
  faces = ring_faces(count, columns)
  faces.append(tuple(reversed(range(columns))))
  faces.append(tuple((count - 1) * columns + k for k in range(columns)))
  obj = add_object(name, verts, faces, ["hair_lock"] * len(faces))
  set_panel(obj, panel)
  hair_weights[name] = ([value[1] for value in panel], chain)
  return obj


def chain_bones(prefix, path):
  """Two bones along a lock; the mirrored side gets the same chain."""
  name = f"hair_{prefix}"
  if name in HAIR_CHAINS:
    return
  count = len(path) - 1
  points = [path[round(count * t)] for t in (0.33, 0.66, 1.0)]
  HAIR_CHAINS[name] = points


def build_hair_locks():
  for i, entry in enumerate(HAIR_LOCKS):
    path = lock_path(entry, 58 + i)
    prefix = entry[6]
    if prefix and entry[0] > 0:
      chain_bones(prefix, path)
    side = "_l" if entry[0] >= 0 and entry[0] < 180 else "_r"
    names = (f"hair_{prefix}_1{side}", f"hair_{prefix}_2{side}") if prefix else None
    lock(f"lock_{i}", path, entry[4], names)


JACKET_WIDTH = profile([
  (0.56, 0.232), (0.64, 0.225), (0.72, 0.218), (0.80, 0.21), (0.88, 0.203), (0.96, 0.196), (1.03, 0.19),
  (1.10, 0.188), (1.18, 0.192), (1.26, 0.205), (1.34, 0.222), (1.40, 0.226), (1.44, 0.198), (1.47, 0.14), (1.495, 0.092),
])
JACKET_DEPTH = profile([
  (0.56, 0.168), (0.64, 0.16), (0.72, 0.152), (0.80, 0.146), (0.88, 0.14), (0.96, 0.134), (1.03, 0.128),
  (1.10, 0.125), (1.18, 0.128), (1.26, 0.132), (1.34, 0.132), (1.40, 0.126), (1.44, 0.114), (1.47, 0.098), (1.495, 0.08),
])
# How far from the center each front edge hangs: the jacket opens wider towards the hem.
JACKET_EDGE = profile([
  (0.56, 0.2), (0.75, 0.16), (0.96, 0.125), (1.1, 0.104), (1.26, 0.092), (1.40, 0.074), (1.495, 0.048),
])
JACKET_HEM = 0.56
JACKET_TOP = 1.495
JACKET_ROWS = 24
JACKET_COLUMNS = 46


def jacket_gap(z):
  return math.asin(JACKET_EDGE(z) / JACKET_WIDTH(z))


def jacket_folds(angle, z):
  """Long folds that open towards the hem; a real coat hangs in tubes, not as a cone."""
  amount = 0.024 * smooth(1.04, 0.62, z)
  return amount * (
    0.62 * math.sin(7 * angle + 0.6) + 0.34 * math.sin(11 * angle + 2.1 + z * 3) + 0.5 * math.sin(4 * angle + 1.0)
  )


def jacket_point(angle, z, inset=0.0, folds=True):
  fold = jacket_folds(angle, z) if folds else 0.0
  return Vector((
    (JACKET_WIDTH(z) - inset + fold) * math.sin(angle),
    -(JACKET_DEPTH(z) - inset + fold) * math.cos(angle),
    z,
  ))


def jacket_row(row):
  return JACKET_TOP - (JACKET_TOP - JACKET_HEM) * (row / (JACKET_ROWS - 1)) ** 0.92


def jacket_ring(z, inset=0.0):
  gap = jacket_gap(z)
  return [
    jacket_point(gap + (2 * math.pi - 2 * gap) * column / JACKET_COLUMNS, z, inset)
    for column in range(JACKET_COLUMNS + 1)
  ]


def build_jacket():
  columns = JACKET_COLUMNS + 1
  rows = [jacket_ring(jacket_row(row)) for row in range(JACKET_ROWS)]
  faces = [tuple(reversed(face)) for face in ring_faces(JACKET_ROWS, columns, closed=False)]
  add_object("jacket", [point for row in rows for point in row], faces, ["jacket_shell"] * len(faces), closed=False)
  # The lining only shows when the front swings, so every other row is enough.
  lining_rows = [jacket_ring(jacket_row(row), 0.008) for row in range(0, JACKET_ROWS, 2)]
  faces = ring_faces(len(lining_rows), columns, closed=False)
  add_object("jacket_lining", [point for row in lining_rows for point in row], faces, ["jacket_lining"] * len(faces), closed=False)
  for sign, side in ((1, "l"), (-1, "r")):
    path = []
    for row in range(0, JACKET_ROWS, 2):
      z = jacket_row(row)
      gap = jacket_gap(z)
      path.append((tuple(jacket_point(sign * gap, z, 0.004)), 0.0055, 0.008))
    tube("jacket_zip_" + side, path, "zipper_tape", n=6)
  hem = jacket_ring(JACKET_HEM, 0.004)
  tube("jacket_hem", [(tuple(point), 0.009, 0.0075) for point in hem[::2]], "flag_red_dark", n=4, side=(0, 0, 1))
  jacket_collar()
  build_sleeves()
  for sign, side in ((1, "l"), (-1, "r")):
    strip("jacket_pocket_" + side, "jacket", [
      (sign * 0.16, 0.9, 0.013), (sign * 0.2, 0.872, 0.013),
    ], "flag_red_dark", depth=0.0045, lift=0.002)


def jacket_collar():
  """Folded collar, open at the front and higher at the back, so the neck can breathe."""
  steps = 14
  section = 4
  verts = []
  for k in range(steps + 1):
    angle = math.radians(34 + 292 * k / steps)
    top = 1.508 + 0.038 * (1 - math.cos(angle)) / 2
    for extra, z in ((0.0, 1.478), (-0.004, top), (0.012, top - 0.004), (0.02, 1.482)):
      verts.append(Vector((
        (0.087 + extra) * math.sin(angle),
        0.008 - (0.082 + extra) * math.cos(angle),
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


def build_sleeves():
  keys = [
    ((0.15, 0, 1.37), 0.05, 0.05),
    ((0.197, 0, 1.362), 0.069, 0.071),
    ((0.228, 0, 1.29), 0.065, 0.066),
    ((0.25, -0.002, 1.22), 0.059, 0.06),
    ((0.272, 0, 1.145), 0.057, 0.055),
    ((0.29, -0.004, 1.095), 0.055, 0.054),
    ((0.31, -0.01, 1.02), 0.053, 0.052),
    ((0.33, -0.015, 0.955), 0.046, 0.046),
    ((0.341, -0.018, 0.915), 0.042, 0.042),
    ((0.347, -0.02, 0.89), 0.038, 0.038),
  ]
  rings_list = spline(keys, 2)
  # Cloth bunches where the arm bends, as rings that alternate in size.
  bunched = []
  for i, (position, ru, rv) in enumerate(rings_list):
    wrinkle = 0.0035 * (-1) ** i * (gauss(position[2], 1.12, 0.07) + 0.6 * gauss(position[2], 0.97, 0.05))
    bunched.append((position, ru + wrinkle, rv + wrinkle))
  both("sleeve", bunched, "jacket_sleeve", n=10)
  both("jacket_cuff", [
    ((0.336, -0.017, 0.93), 0.041, 0.041),
    ((0.344, -0.019, 0.9), 0.044, 0.044),
    ((0.352, -0.021, 0.872), 0.04, 0.04),
    ((0.354, -0.021, 0.866), 0.034, 0.034),
  ], "flag_red_dark", n=10)


def build_tee():
  tube("torso", spline([
    ((0, 0, 0.99), 0.1, 0.148), ((0, 0, 1.08), 0.104, 0.154), ((0, -0.002, 1.18), 0.112, 0.167),
    ((0, -0.006, 1.28), 0.119, 0.18), ((0, -0.004, 1.36), 0.114, 0.186), ((0, 0, 1.42), 0.098, 0.16),
    ((0, 0.006, 1.46), 0.08, 0.108), ((0, 0.01, 1.485), 0.066, 0.074),
  ], 2), "white", n=16)
  tube("tee_rib", [
    ((0, 0.012, 1.458), 0.086, 0.1),
    ((0, 0.012, 1.474), 0.078, 0.088),
    ((0, 0.012, 1.486), 0.072, 0.078),
  ], "tee_rib", n=14)


def build_legs():
  tube("pelvis", spline([
    ((0, 0, 0.84), 0.07, 0.09), ((0, 0.006, 0.9), 0.118, 0.166), ((0, 0.002, 0.97), 0.11, 0.158),
    ((0, 0, 1.03), 0.104, 0.152),
  ], 2), "pants_black", n=14)
  both("leg", spline([
    ((0.092, 0, 0.92), 0.105, 0.092), ((0.098, -0.004, 0.8), 0.098, 0.088), ((0.102, -0.01, 0.68), 0.09, 0.08),
    ((0.107, -0.014, 0.56), 0.08, 0.07), ((0.11, -0.02, 0.5), 0.074, 0.066), ((0.113, -0.012, 0.44), 0.074, 0.067),
    ((0.118, 0.004, 0.36), 0.076, 0.067), ((0.122, 0.006, 0.28), 0.066, 0.058), ((0.125, 0.006, 0.22), 0.061, 0.055),
    ((0.125, 0.006, 0.18), 0.05, 0.046),
  ], 2), "pants_black", n=12)
  tube("belt", [
    ((0, 0, 0.99), 0.113, 0.164),
    ((0, 0, 1.0), 0.116, 0.167),
    ((0, 0, 1.04), 0.112, 0.161),
    ((0, 0, 1.05), 0.108, 0.157),
  ], "leather", n=16)
  decal("buckle", "belt", [(-0.03, 1.0), (0.03, 1.0), (0.03, 1.042), (-0.03, 1.042)], "metal", lift=0.004)
  decal("buckle_center", "belt", [(-0.018, 1.01), (0.018, 1.01), (0.018, 1.032), (-0.018, 1.032)], "leather", lift=0.007)


def build_hands():
  skin = variant["skin"]
  both("hand", arm_path(spline([
    ((0.372, -0.02, 0.9), 0.028, 0.02),
    ((0.382, -0.022, 0.86), 0.04, 0.021),
    ((0.395, -0.025, 0.83), 0.05, 0.023),
    ((0.404, -0.03, 0.795), 0.047, 0.019),
  ], 1)), skin, n=8)
  for i, (y, length) in enumerate(((-0.066, 0.07), (-0.042, 0.082), (-0.018, 0.078), (0.006, 0.062))):
    both(f"finger_{i}", arm_path(spline([
      ((0.404, y, 0.8), 0.0098, 0.0098),
      ((0.414, y, 0.8 - length * 0.5), 0.0088, 0.0088),
      ((0.42, y - 0.003, 0.8 - length * 0.85), 0.0078, 0.0078),
      ((0.423, y - 0.006, 0.8 - length), 0.0048, 0.0048),
    ], 1)), skin, n=5)
  thumb(skin)


def start(name):
  global variant
  variant = VARIANTS[name]
  surfaces.clear()
  parts.clear()
  hair_weights.clear()


JACKET_CHAINS = (
  # Name, position from the front edge (0) to the back center (1), heights, parent.
  ("jacket_front", 0.1, (1.26, 1.03, 0.8, 0.565), "chest"),
  ("jacket_side", 0.46, (1.03, 0.88, 0.72, 0.565), "hips"),
  ("jacket_back", 0.84, (1.03, 0.88, 0.72, 0.565), "hips"),
)


def cloth_bones():
  bones = {}
  for prefix, along, heights, parent in JACKET_CHAINS:
    for i in range(len(heights) - 1):
      points = [
        jacket_point(jacket_gap(z) + (math.pi - jacket_gap(z)) * along, z, folds=False)
        for z in (heights[i], heights[i + 1])
      ]
      bones[f"{prefix}_{i + 1}_l"] = (tuple(points[0]), tuple(points[1]), f"{prefix}_{i}_l" if i else parent)
  for chain, points in HAIR_CHAINS.items():
    for i in range(len(points) - 1):
      bones[f"{chain}_{i + 1}_l"] = (tuple(points[i]), tuple(points[i + 1]), f"{chain}_{i}_l" if i else "head")
  return bones


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
  return (cloth_bones() if variant["fingers"] else {}) | {
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
  if name.startswith(("arm", "sleeve", "hand", "jacket_cuff")):
    return ["chest", "shoulder" + side, "upper_arm" + side, "lower_arm" + side, "hand" + side, "fingers" + side]
  if name.startswith("finger"):
    return ["hand" + side, "fingers" + side]
  if name.startswith("thumb"):
    return ["hand" + side, "thumb" + side]
  if name.startswith(("boot", "shoe")):
    return ["lower_leg" + side, "foot" + side, "toes" + side]
  if name.startswith(("leg", "rip", "cargo", "pants")):
    return ["hips", "upper_leg" + side, "lower_leg" + side]
  if name.startswith("jacket"):
    cloth = [f"{chain}_{i}{twin}" for chain, *_ in JACKET_CHAINS for i in (1, 2, 3) for twin in ("_l", "_r")]
    return ["hips", "spine", "chest", "shoulder_l", "shoulder_r"] + cloth
  if name.startswith(("belt", "buckle")):
    return ["hips", "spine"]
  if name.startswith(("pelvis", "fly")):
    return ["hips", "spine", "upper_leg_l", "upper_leg_r"]
  if name == "neck":
    return ["chest", "neck", "head"]
  if name.startswith(("collar", "undershirt")):
    return ["chest", "neck"]
  return ["hips", "spine", "chest", "shoulder_l", "shoulder_r"]


HEAD_PREFIXES = ("head", "nose", "hair", "mouth", "eye", "iris", "ear", "gauge")


def segment_distance(point, head, tail):
  axis = tail - head
  amount = max(0.0, min(1.0, (point - head).dot(axis) / axis.length_squared))
  return (point - (head + axis * amount)).length


def assign_lock_weights(part, along, chain):
  head = part.vertex_groups.new(name="head")
  if chain is None:
    head.add(list(range(len(along))), 1.0, "REPLACE")
    return
  first = part.vertex_groups.new(name=chain[0])
  second = part.vertex_groups.new(name=chain[1])
  for index, t in enumerate(along):
    if t < 0.4:
      head.add([index], 1 - t / 0.4, "REPLACE")
      first.add([index], t / 0.4, "REPLACE")
    else:
      amount = min((t - 0.4) / 0.35, 1.0)
      first.add([index], 1 - amount, "REPLACE")
      second.add([index], amount, "REPLACE")


def assign_weights(part, bones):
  name = part.name.split(".")[0]
  if name in hair_weights:
    assign_lock_weights(part, *hair_weights[name])
    return
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
    )[:4]
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


def finish_painted(body):
  """Soft shading, and what paint_protagonist.py needs to color each face."""
  mesh = body.data
  mesh.shade_smooth()
  mesh.set_sharp_from_angle(angle=math.radians(62))
  region = mesh.attributes.new("region", "FLOAT", "FACE")
  region.data.foreach_set("value", [polygon.material_index + 1 for polygon in mesh.polygons])
  body["regions"] = [slot.name for slot in mesh.materials]
  body["palette"] = {slot.name: list(COLORS[slot.name]) for slot in mesh.materials}


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
  if variant["fingers"]:
    finish_painted(body)
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
  return [lambda: start(name)] + builders + [lambda: finish(name)]


STAGES = (
  [clear]
  + stages_for("male", [build_head, build_hair_locks, build_tee, build_legs, build_boots, build_jacket, build_hands])
  + stages_for("female", [build_body, build_pants, build_shirt, build_hair, build_face])
  + [save]
)

if __name__ == "__main__":
  for stage in STAGES:
    stage()
