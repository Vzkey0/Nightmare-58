# Builds the skeleton enemy and its machete from code so proportions can be tweaked and rebuilt.
# Faces -Y with feet on the origin, in A-pose for rigging. +X is the character's left.
#   blender --background --python art/characters/build_skeleton.py
import math
import os

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
BLEND_PATH = os.path.join(HERE, "skeleton.blend")
GLB_PATH = os.path.join(HERE, "..", "..", "game", "models", "characters", "skeleton.glb")

COLORS = {
  "bone_light": (0.9, 0.83, 0.66),
  "bone_mid": (0.74, 0.66, 0.49),
  "bone_dark": (0.47, 0.39, 0.28),
  "socket": (0.025, 0.02, 0.025),
  "steel": (0.42, 0.45, 0.47),
  "steel_edge": (0.88, 0.9, 0.88),
  "rust": (0.42, 0.18, 0.08),
  "wood": (0.25, 0.14, 0.08),
  "brass": (0.72, 0.52, 0.2),
}
EYE_COLOR = (1.0, 0.42, 0.02)
EYE_ENERGY = 1.3

# Same names as the protagonist's rig, plus jaw. Each part follows one bone: nothing here bends.
SHOULDER = (0.225, 0.0, 1.295)
ELBOW = (0.44, 0.0, 1.03)
WRIST = (0.625, -0.02, 0.79)
HAND_END = (0.68, -0.02, 0.718)
FINGER_END = (0.745, -0.02, 0.635)
THUMB_END = (0.635, -0.1, 0.72)
HIP = (0.095, 0.0, 0.86)
KNEE = (0.105, -0.015, 0.47)
ANKLE = (0.115, 0.015, 0.09)
BALL = (0.115, -0.09, 0.035)
TOE = (0.115, -0.2, 0.03)
GRIP = (-0.69, -0.02, 0.705)
BLADE_LENGTH = 0.72

parts = []


def material(name):
  existing = bpy.data.materials.get(name)
  if existing:
    return existing
  mat = bpy.data.materials.new(name)
  mat.use_nodes = True
  bsdf = mat.node_tree.nodes.get("Principled BSDF")
  if name == "eye_glow":
    linear = tuple(channel ** 2.2 for channel in EYE_COLOR) + (1.0,)
    bsdf.inputs["Emission Color"].default_value = linear
    bsdf.inputs["Emission Strength"].default_value = EYE_ENERGY
  else:
    linear = tuple(channel ** 2.2 for channel in COLORS[name]) + (1.0,)
  mat.diffuse_color = linear
  # The eye gets its color only from emission: sunlight on top of it would wash it out to yellow.
  bsdf.inputs["Base Color"].default_value = (0, 0, 0, 1) if name == "eye_glow" else linear
  bsdf.inputs["Roughness"].default_value = 0.45 if name.startswith("steel") else 0.85
  return mat


def add_mesh(name, verts, faces, face_materials):
  mesh = bpy.data.meshes.new(name)
  mesh.from_pydata([tuple(v) for v in verts], [], faces)
  names = sorted(set(face_materials))
  for mat_name in names:
    mesh.materials.append(material(mat_name))
  for polygon, mat_name in zip(mesh.polygons, face_materials):
    polygon.material_index = names.index(mat_name)
  mesh.update()
  obj = bpy.data.objects.new(name, mesh)
  bpy.context.scene.collection.objects.link(obj)
  return obj


def fix_normals(obj):
  bpy.context.view_layer.objects.active = obj
  with bpy.context.temp_override(active_object=obj, selected_editable_objects=[obj], object=obj):
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def part(name, verts, faces, face_materials, bone):
  obj = add_mesh(name, verts, faces, face_materials)
  fix_normals(obj)
  parts.append((obj, bone))
  return obj


def tube(name, path, mat, bone, n=6, side=None, bands=None):
  """Lofts rings along path. Each entry is (position, radius along side, other radius)."""
  points = [Vector(entry[0]) for entry in path]
  first = (points[1] - points[0]).normalized()
  u = Vector(side) if side else (Vector((0, 1, 0)) if abs(first.y) < 0.8 else Vector((0, 0, 1)))
  verts = []
  for i, (_, ru, rv) in enumerate(path):
    tangent = (points[min(i + 1, len(points) - 1)] - points[max(i - 1, 0)]).normalized()
    u = (u - tangent * u.dot(tangent)).normalized()
    v = tangent.cross(u)
    for k in range(n):
      angle = math.pi / n + 2 * math.pi * k / n
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
  face_materials.append((bands or {}).get(len(path) - 2, mat))
  return part(name, verts, faces, face_materials, bone)


def flip(point):
  return (-point[0], point[1], point[2])


def mirrored(path):
  return [(flip(position), ru, rv) for position, ru, rv in path]


def both(name, path, mat, bone, **kwargs):
  tube(name + "_l", path, mat, bone + "_l" if not bone.endswith("!") else bone[:-1], **kwargs)
  tube(name + "_r", mirrored(path), mat, bone + "_r" if not bone.endswith("!") else bone[:-1], **kwargs)


def long_bone_path(a, b, radius, knob_a, knob_b):
  """A shaft with a knob on each end, wider than a real bone so it reads from the game's camera."""
  a, b = Vector(a), Vector(b)
  stations = (
    (-0.03, knob_a * 0.55), (0.03, knob_a), (0.11, knob_a * 0.72), (0.2, radius * 1.05),
    (0.8, radius), (0.89, knob_b * 0.72), (0.97, knob_b), (1.03, knob_b * 0.55),
  )
  return [(a.lerp(b, t), r, r) for t, r in stations]


def long_bone(name, a, b, radius, knob_a, knob_b, bone, n=6):
  ends = {0: "bone_light", 1: "bone_light", 5: "bone_light", 6: "bone_light"}
  both(name, long_bone_path(a, b, radius, knob_a, knob_b), "bone_mid", bone, n=n, bands=ends)


def carve(obj, outline, center, front, back, tighten=0.72):
  """Cuts a real hole along Y, so sockets have depth instead of being painted on."""
  cx, cz = center
  verts = [(cx + x * 1.15, front, cz + z * 1.15) for x, z in outline]
  verts += [(cx + x * tighten, back, cz + z * tighten) for x, z in outline]
  n = len(outline)
  faces = [tuple(range(n)), tuple(reversed(range(n, 2 * n)))]
  faces += [(k, n + k, n + (k + 1) % n, (k + 1) % n) for k in range(n)]
  cutter = add_mesh("cutter", verts, faces, ["socket"] * len(faces))
  fix_normals(cutter)
  modifier = obj.modifiers.new("cut", "BOOLEAN")
  modifier.operation = "DIFFERENCE"
  modifier.solver = "EXACT"
  modifier.material_mode = "TRANSFER"
  modifier.object = cutter
  bpy.context.view_layer.objects.active = obj
  bpy.ops.object.modifier_apply(modifier=modifier.name)
  mesh = cutter.data
  bpy.data.objects.remove(cutter)
  bpy.data.meshes.remove(mesh)


def disc(name, center, radius, bone, mat, n=8):
  x, y, z = center
  verts = [(x + radius * math.cos(2 * math.pi * k / n), y, z + radius * math.sin(2 * math.pi * k / n)) for k in range(n)]
  verts += [(vx, y + 0.012, vz) for vx, _, vz in verts]
  faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
  faces += [(k, (k + 1) % n, n + (k + 1) % n, n + k) for k in range(n)]
  return part(name, verts, faces, [mat] * len(faces), bone)


SOCKET = [(-0.056, -0.016), (-0.008, 0.024), (0.056, 0.05), (0.07, -0.002), (0.044, -0.052), (-0.016, -0.058)]
NOSE = [(0.0, 0.04), (0.012, 0.008), (0.033, -0.026), (0.008, -0.02), (0.0, -0.034), (-0.008, -0.02), (-0.033, -0.026), (-0.012, 0.008)]
CRACK = [
  (0.0, 0.0), (0.03, -0.042), (0.016, -0.066), (0.052, -0.11), (0.036, -0.145), (0.062, -0.2),
  (0.018, -0.146), (0.026, -0.112), (-0.004, -0.074), (0.004, -0.046),
]
SKULL_RINGS = [
  (1.782, 0.05, 0.05, 0.012), (1.768, 0.11, 0.1, 0.012), (1.73, 0.16, 0.148, 0.012),
  (1.675, 0.183, 0.17, 0.01), (1.62, 0.182, 0.172, 0.006), (1.575, 0.166, 0.16, 0.0),
  (1.53, 0.145, 0.138, -0.012), (1.49, 0.122, 0.112, -0.024), (1.455, 0.1, 0.094, -0.036),
  (1.425, 0.09, 0.086, -0.04),
]


def build_skull():
  skull = tube("skull", [((0, depth, z), ru, rv) for z, ru, rv, depth in SKULL_RINGS], "bone_light", "head", n=12, side=(0, 1, 0), bands={
    6: "bone_mid", 7: "bone_mid", 8: "bone_mid",
  })
  for sign in (1, -1):
    carve(skull, [(x * sign, z) for x, z in SOCKET], (sign * 0.076, 1.575), -0.28, -0.075)
  carve(skull, NOSE, (0, 1.505), -0.24, -0.09, tighten=0.6)
  carve(skull, CRACK, (0.03, 1.79), -0.26, -0.12, tighten=0.4)

  for sign, side in ((1, "l"), (-1, "r")):
    disc("eye_" + side, (sign * 0.08, -0.112, 1.572), 0.027, "head", "eye_glow")

  # A heavy brow that drops toward the nose: this is what turns a cute skull into a mean one.
  both("brow", [
    ((0.012, -0.176, 1.572), 0.012, 0.012),
    ((0.05, -0.176, 1.604), 0.018, 0.018),
    ((0.1, -0.158, 1.635), 0.02, 0.02),
    ((0.142, -0.112, 1.635), 0.015, 0.015),
    ((0.165, -0.06, 1.62), 0.005, 0.005),
  ], "bone_light", "head!", n=4, side=(0, -0.5, 1))
  both("cheek", [
    ((0.07, -0.118, 1.515), 0.014, 0.012),
    ((0.118, -0.106, 1.505), 0.027, 0.015),
    ((0.142, -0.068, 1.514), 0.019, 0.013),
    ((0.126, -0.005, 1.54), 0.007, 0.006),
  ], "bone_light", "head!", n=5, side=(0, 0, 1))


def tooth(name, x, y, top, bottom, width, bone, turn):
  half = width * 0.5
  c, s = math.cos(turn), math.sin(turn)
  corners = [(-half, -0.016), (half, -0.016), (half * 0.86, 0.012), (-half * 0.86, 0.012)]
  verts = [(x + cx * c - cy * s, y + cx * s + cy * c, top) for cx, cy in corners]
  verts += [(x + cx * 0.74 * c - cy * s, y + cx * 0.74 * s + cy * c, bottom) for cx, cy in corners]
  faces = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
  part(name, verts, faces, ["bone_light"] * 6, bone)


def tooth_row(prefix, radius, center_y, top, bottom, angles, bone):
  for i, angle in enumerate(angles):
    if angle is None:
      continue
    turn = math.radians(angle)
    tall = bottom - (0.006 if i % 2 else 0.0)
    tooth(f"{prefix}_{i}", radius * math.sin(turn), center_y - radius * math.cos(turn), top, tall, 0.03, bone, turn)


def build_jaw():
  # One gap on each row: a perfect grin looks like a toy.
  tooth_row("tooth_top", 0.09, -0.04, 1.43, 1.392, (-63, -45, -29, -10, 10, None, 45, 63), "head")
  tooth_row("jaw_tooth", 0.084, -0.038, 1.352, 1.388, (-60, -42, None, -9, 9, 27, 42, 60), "jaw")
  tube("jaw_bone", [
    ((0.118, -0.02, 1.5), 0.02, 0.012),
    ((0.114, -0.035, 1.41), 0.03, 0.015),
    ((0.096, -0.07, 1.35), 0.024, 0.015),
    ((0.052, -0.118, 1.335), 0.022, 0.016),
    ((0, -0.134, 1.33), 0.024, 0.018),
    ((-0.052, -0.118, 1.335), 0.022, 0.016),
    ((-0.096, -0.07, 1.35), 0.024, 0.015),
    ((-0.114, -0.035, 1.41), 0.03, 0.015),
    ((-0.118, -0.02, 1.5), 0.02, 0.012),
  ], "bone_mid", "jaw", n=4, side=(0, 0, 1))


def rib(name, height, width, depth, reach, droop):
  path = []
  steps = 6
  for i in range(steps):
    angle = math.radians(12 + reach * i / (steps - 1))
    fall = droop * (1 - math.cos(angle)) * 0.5
    path.append(((width * math.sin(angle), 0.015 + depth * math.cos(angle), height - fall), 0.017 - i * 0.0012, 0.008))
  return path


def build_torso():
  ribs = (
    (1.27, 0.14, 0.095, 150, 0.04), (1.225, 0.178, 0.11, 150, 0.06), (1.178, 0.19, 0.116, 148, 0.07),
    (1.13, 0.183, 0.11, 142, 0.07), (1.085, 0.158, 0.098, 112, 0.05),
  )
  for i, (height, width, depth, reach, droop) in enumerate(ribs):
    path = rib("rib", height, width, depth, reach, droop)
    tube(f"rib_{i}_l", path, "bone_light", "chest", n=4, side=(0, 0, 1))
    # A snapped rib: the asymmetry reads even with the model mirrored everywhere else.
    tube(f"rib_{i}_r", mirrored(path[:4] if i == 2 else path), "bone_light", "chest", n=4, side=(0, 0, 1))
  tube("sternum", [((0, -0.09, 1.292), 0.012, 0.024), ((0, -0.104, 1.24), 0.012, 0.03), ((0, -0.112, 1.16), 0.012, 0.019), ((0, -0.104, 1.11), 0.008, 0.004)], "bone_mid", "chest", n=4, side=(0, 1, 0))

  spine_height = (0.94, 0.985, 1.03, 1.075, 1.12, 1.165, 1.21, 1.255, 1.3)
  for i, z in enumerate(spine_height):
    bone = "hips" if z < 0.98 else "spine" if z < 1.13 else "chest"
    y = 0.03 + 0.016 * math.sin((z - 0.94) * 5.2)
    tube(f"vertebra_{i}", [((0, y, z - 0.016), 0.03, 0.036), ((0, y, z + 0.016), 0.03, 0.036)], "bone_mid", bone, n=5)
    tube(f"spinous_{i}", [((0, y + 0.018, z + 0.006), 0.012, 0.009), ((0, y + 0.062, z - 0.014), 0.004, 0.004)], "bone_dark", bone, n=4)
  for i, z in enumerate((1.33, 1.365, 1.4, 1.435)):
    tube(f"neck_{i}", [((0, 0.03, z - 0.012), 0.032, 0.036), ((0, 0.03, z + 0.012), 0.032, 0.036)], "bone_mid", "neck", n=5)

  both("clavicle", [
    ((0.018, -0.082, 1.298), 0.014, 0.014), ((0.09, -0.078, 1.325), 0.016, 0.016),
    ((0.16, -0.035, 1.325), 0.017, 0.017), ((0.215, -0.008, 1.31), 0.022, 0.022),
  ], "bone_light", "chest!", n=5)
  both("scapula", [
    ((0.07, 0.102, 1.28), 0.012, 0.012), ((0.13, 0.105, 1.285), 0.075, 0.008),
    ((0.18, 0.07, 1.285), 0.05, 0.008), ((0.215, 0.025, 1.3), 0.018, 0.012),
  ], "bone_mid", "chest!", n=4, side=(0, 0, 1))


def build_pelvis():
  both("ilium", [
    ((0.105, -0.01, 0.875), 0.03, 0.022), ((0.125, 0.0, 0.93), 0.052, 0.014),
    ((0.14, 0.012, 0.985), 0.098, 0.014), ((0.145, 0.018, 1.025), 0.07, 0.012), ((0.14, 0.02, 1.04), 0.022, 0.008),
  ], "bone_light", "hips!", n=4, side=(0.72, 0.7, 0))
  both("pubis", [
    ((0.115, -0.03, 0.885), 0.03, 0.03), ((0.07, -0.07, 0.83), 0.022, 0.022), ((0.012, -0.088, 0.81), 0.021, 0.021),
  ], "bone_mid", "hips!", n=5)
  both("ischium", [
    ((0.115, 0.0, 0.885), 0.03, 0.03), ((0.09, 0.03, 0.8), 0.024, 0.024), ((0.05, -0.04, 0.785), 0.016, 0.016), ((0.018, -0.08, 0.805), 0.014, 0.014),
  ], "bone_dark", "hips!", n=5)
  tube("sacrum", [((0, 0.045, 0.975), 0.03, 0.058), ((0, 0.062, 0.9), 0.024, 0.04), ((0, 0.04, 0.83), 0.01, 0.012)], "bone_mid", "hips", n=5)


def along(a, b, t):
  return Vector(a).lerp(Vector(b), t)


def build_limbs():
  long_bone("humerus", SHOULDER, ELBOW, 0.026, 0.048, 0.036, "upper_arm")
  ulna_shift = Vector((0.0, 0.016, 0.0))
  radius_shift = Vector((0.0, -0.016, 0.0))
  long_bone("ulna", Vector(ELBOW) + ulna_shift, Vector(WRIST) + ulna_shift, 0.012, 0.024, 0.016, "lower_arm", n=5)
  long_bone("radius", Vector(ELBOW) + radius_shift, Vector(WRIST) + radius_shift, 0.012, 0.016, 0.024, "lower_arm", n=5)
  long_bone("femur", HIP, KNEE, 0.033, 0.056, 0.05, "upper_leg")
  long_bone("tibia", along(KNEE, ANKLE, 0.02), ANKLE, 0.027, 0.045, 0.034, "lower_leg")
  fibula = Vector((0.036, 0.008, 0.0))
  long_bone("fibula", along(KNEE, ANKLE, 0.06) + fibula, Vector(ANKLE) + fibula, 0.009, 0.014, 0.016, "lower_leg", n=4)

  both("heel", [
    ((0.115, 0.075, 0.03), 0.028, 0.034), ((0.115, 0.03, 0.058), 0.05, 0.045),
    ((0.115, -0.03, 0.05), 0.04, 0.052), ((0.115, -0.085, 0.034), 0.026, 0.056),
  ], "bone_mid", "foot", n=5, side=(0, 0, 1))
  for i, spread in enumerate((-0.04, 0.0, 0.04)):
    both(f"toe_{i}", [
      ((0.115 + spread, -0.085, 0.032), 0.02, 0.018),
      ((0.115 + spread * 1.25, -0.145, 0.024), 0.016, 0.014),
      ((0.115 + spread * 1.5, -0.215 + abs(spread) * 0.8, 0.012), 0.012, 0.01),
    ], "bone_light", "toes", n=4, side=(0, 0, 1))

  # Left hand: open claws, reaching out.
  direction = (Vector(HAND_END) - Vector(WRIST)).normalized()
  across = Vector((0, 1, 0))
  bend = direction.cross(across).normalized()
  center = Vector(WRIST) + direction * 0.05
  tube("hand_l", [(Vector(WRIST) + direction * 0.01, 0.02, 0.022), (center, 0.042, 0.018), (Vector(HAND_END) + direction * 0.01, 0.048, 0.016)], "bone_mid", "hand_l", n=5, side=across)
  for i, spread in enumerate((-0.04, -0.013, 0.014, 0.04)):
    knuckle = Vector(HAND_END) + across * spread + direction * 0.01
    length = (0.1, 0.122, 0.116, 0.09)[i]
    tip = direction + across * spread * 2.2
    tube(f"finger_{i}_l", [
      (knuckle, 0.011, 0.011),
      (knuckle + tip * length * 0.5 + bend * 0.008, 0.009, 0.009),
      (knuckle + tip * length + bend * 0.03, 0.002, 0.002),
    ], "bone_light", "fingers_l", n=4)
  thumb = Vector(WRIST) + direction * 0.05 + across * -0.04
  tube("thumb_l", [(thumb, 0.012, 0.012), (Vector(THUMB_END) + direction * -0.02, 0.009, 0.009), (Vector(THUMB_END) + direction * 0.02 + bend * 0.015, 0.002, 0.002)], "bone_light", "thumb_l", n=4)

  # Right hand: modeled shut around the grip, which runs along Y.
  grip = Vector(GRIP)
  wrist = Vector(flip(WRIST))
  tube("hand_r", [(wrist, 0.02, 0.022), (wrist.lerp(grip, 0.6), 0.04, 0.02), (grip + Vector((-0.03, 0, 0.035)), 0.05, 0.016)], "bone_mid", "hand_r", n=5, side=(0, 1, 0))
  for i, offset in enumerate((-0.042, -0.014, 0.014, 0.042)):
    path = []
    for angle in (135, 60, -20, -100, -170):
      turn = math.radians(angle)
      radius = 0.034 + (0.007 if angle in (135, -170) else 0.0)
      path.append((grip + Vector((radius * math.cos(turn), offset, radius * math.sin(turn))), 0.011, 0.011))
    tube(f"finger_{i}_r", path, "bone_light", "hand_r", n=4)


def build_machete():
  """A long, worn work machete: straight back, belly that widens toward the tip, chipped edge."""
  grip = Vector(GRIP)
  # (distance from the guard, top of the back, bottom of the edge), all on the plane Y-Z.
  outline = [
    (0.0, 0.018, -0.024), (0.14, 0.02, -0.038), (0.3, 0.021, -0.05), (0.32, 0.021, -0.04),
    (0.34, 0.021, -0.054), (0.5, 0.022, -0.072), (0.52, 0.022, -0.062), (0.54, 0.022, -0.078),
    (0.64, 0.024, -0.09), (BLADE_LENGTH - 0.03, 0.034, -0.08), (BLADE_LENGTH, 0.06, -0.012),
  ]
  start = 0.075
  thick = 0.009
  verts = []
  for distance, top, bottom in outline:
    y = grip.y - start - distance
    middle = bottom + (top - bottom) * 0.42
    verts += [
      (grip.x, y, grip.z + top),
      (grip.x + thick, y, grip.z + middle),
      (grip.x, y, grip.z + bottom),
      (grip.x - thick, y, grip.z + middle),
    ]
  faces = []
  face_materials = []
  for i in range(len(outline) - 1):
    a, b = i * 4, (i + 1) * 4
    worn = i == 5
    faces.append((a, a + 1, b + 1, b))
    face_materials.append("rust" if i == 0 else "steel")
    faces.append((a + 1, a + 2, b + 2, b + 1))
    face_materials.append("rust" if worn else "steel_edge")
    faces.append((a + 2, a + 3, b + 3, b + 2))
    face_materials.append("rust" if worn else "steel_edge")
    faces.append((a + 3, a, b, b + 3))
    face_materials.append("rust" if i == 0 else "steel")
  last = (len(outline) - 1) * 4
  faces += [(3, 2, 1, 0), (last, last + 1, last + 2, last + 3)]
  face_materials += ["steel", "steel"]
  part("machete_blade", verts, faces, face_materials, "weapon")

  handle = grip + Vector((0, 0.09, 0))
  tube("machete_handle", [
    (handle + Vector((0, 0.022, -0.008)), 0.016, 0.011),
    (handle + Vector((0, 0.004, -0.008)), 0.03, 0.017),
    (handle + Vector((0, -0.08, -0.002)), 0.024, 0.016),
    (grip + Vector((0, -0.07, 0)), 0.03, 0.015),
    (grip + Vector((0, -0.08, 0)), 0.024, 0.013),
  ], "wood", "weapon", n=6, side=(0, 0, 1))
  for i, y in enumerate((0.105, 0.075)):
    rivet = grip + Vector((0, y, -0.006))
    tube(f"machete_rivet_{i}", [(rivet + Vector((-0.019, 0, 0)), 0.007, 0.007), (rivet + Vector((0.019, 0, 0)), 0.007, 0.007)], "brass", "weapon", n=4)


def bones():
  """Bones as name: (head, tail, parent), for the side +X; _l bones get a mirrored _r twin."""
  return {
    # Carries root motion, so it sits on the ground and has no vertex weights.
    "root": ((0, 0, 0), (0, 0.2, 0), None),
    "hips": ((0, 0, 0.86), (0, 0, 0.98), "root"),
    "spine": ((0, 0.01, 0.98), (0, 0.01, 1.13), "hips"),
    "chest": ((0, 0.01, 1.13), (0, 0.01, 1.3), "spine"),
    "neck": ((0, 0.03, 1.31), (0, 0.03, 1.43), "chest"),
    "head": ((0, 0.03, 1.43), (0, 0.03, 1.73), "neck"),
    "jaw": ((0, -0.03, 1.49), (0, -0.13, 1.36), "head"),
    "shoulder_l": ((0.05, 0, 1.3), SHOULDER, "chest"),
    "upper_arm_l": (SHOULDER, ELBOW, "shoulder_l"),
    "lower_arm_l": (ELBOW, WRIST, "upper_arm_l"),
    "hand_l": (WRIST, HAND_END, "lower_arm_l"),
    "fingers_l": (HAND_END, FINGER_END, "hand_l"),
    "thumb_l": (WRIST, THUMB_END, "hand_l"),
    "upper_leg_l": (HIP, KNEE, "hips"),
    "lower_leg_l": (KNEE, ANKLE, "upper_leg_l"),
    "foot_l": (ANKLE, BALL, "lower_leg_l"),
    "toes_l": (BALL, TOE, "foot_l"),
    # Grip point of the machete; it points along the blade, like the protagonist's.
    "weapon": (GRIP, (GRIP[0], GRIP[1] - 0.2, GRIP[2]), "hand_r"),
  }


def mirrored_bones(table):
  result = {}
  for name, (head, tail, parent) in table.items():
    result[name] = (head, tail, parent)
    if name.endswith("_l"):
      twin_parent = parent[:-2] + "_r" if parent.endswith("_l") else parent
      result[name[:-2] + "_r"] = (flip(head), flip(tail), twin_parent)
  return result


def build_armature(table):
  data = bpy.data.armatures.new("skeleton_armature")
  armature = bpy.data.objects.new("armature_skeleton", data)
  bpy.context.scene.collection.objects.link(armature)
  bpy.context.view_layer.objects.active = armature
  bpy.ops.object.mode_set(mode="EDIT")
  created = {}
  for name, (head, tail, _) in table.items():
    edit_bone = data.edit_bones.new(name)
    edit_bone.head = head
    edit_bone.tail = tail
    created[name] = edit_bone
  for name, (_, _, parent) in table.items():
    if parent:
      created[name].parent = created[parent]
  bpy.ops.object.mode_set(mode="OBJECT")
  return armature


def finish():
  for obj, bone in parts:
    obj.vertex_groups.new(name=bone).add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
  objects = [obj for obj, _ in parts]
  with bpy.context.temp_override(active_object=objects[0], selected_editable_objects=objects):
    bpy.ops.object.join()
  body = objects[0]
  body.name = "skeleton"
  body.data.name = "skeleton"
  armature = build_armature(mirrored_bones(bones()))
  body.parent = armature
  body.modifiers.new("armature", "ARMATURE").object = armature

  triangles = sum(len(polygon.vertices) - 2 for polygon in body.data.polygons)
  z_values = [v.co.z for v in body.data.vertices]
  print("skeleton triangles", triangles, "z", round(min(z_values), 3), round(max(z_values), 3))

  os.makedirs(os.path.dirname(GLB_PATH), exist_ok=True)
  bpy.ops.export_scene.gltf(filepath=GLB_PATH, export_format="GLB", use_visible=True)
  bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)


def main():
  bpy.ops.wm.read_factory_settings(use_empty=True)
  build_skull()
  build_jaw()
  build_torso()
  build_pelvis()
  build_limbs()
  build_machete()
  finish()


main()
