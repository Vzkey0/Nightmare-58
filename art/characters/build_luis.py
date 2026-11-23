# Builds Luis, the friend who drives the protagonist in the opening, rigged and with his clips.
# A slim bearded man in an olive t-shirt, khaki cargo pants and a canvas backpack. Faceted like
# the rest of the world. Faces -Y with feet on the origin; bones share the protagonist's names.
#   blender --background --python art/characters/build_luis.py
# build_person() is also what build_drive.py dresses the street's people with.
import math
import os
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "props"))

from animate_protagonist import FORWARD, UP, Clip, Rig, at, bake, rot, timeline
from beast_tools import Tags, mirrored, rig
from prop_tools import Shape, linear, material

BLEND_PATH = os.path.join(HERE, "luis.blend")
GLB_PATH = os.path.join(HERE, "..", "..", "game", "models", "characters", "luis.glb")

LUIS = {
  "skin": (0.80, 0.62, 0.48),
  "hair": (0.19, 0.12, 0.08),
  "shirt": (0.31, 0.36, 0.21),
  "trim": (0.20, 0.24, 0.14),
  "pants": (0.55, 0.47, 0.31),
  "pants_dark": (0.42, 0.35, 0.22),
  "shoes": (0.26, 0.28, 0.31),
  "sole": (0.14, 0.14, 0.15),
  "pack": (0.58, 0.48, 0.31),
  "strap": (0.36, 0.28, 0.18),
  "beard": True,
  "hairstyle": "swept",
  "backpack": True,
  "build": 1.0,
}

# Joints, for the side +X. The A pose keeps the arms 40 degrees off the body.
SHOULDER = Vector((0.17, 0.01, 1.42))
ELBOW = Vector((0.35, 0.02, 1.205))
WRIST = Vector((0.514, -0.0, 1.01))
KNUCKLES = Vector((0.566, -0.0, 0.944))
FINGER_TIP = Vector((0.61, -0.0, 0.89))
THUMB_TIP = Vector((0.55, -0.06, 0.955))
HIP = Vector((0.095, 0.0, 0.9))
KNEE = Vector((0.1, -0.012, 0.49))
ANKLE = Vector((0.105, 0.015, 0.09))
BALL = Vector((0.105, -0.085, 0.03))
TOE = Vector((0.105, -0.17, 0.025))


def bones():
  return mirrored({
    "root": ((0, 0, 0), (0, 0.2, 0), None),
    "hips": ((0, 0, 0.92), (0, 0, 1.02), "root"),
    "spine": ((0, 0, 1.02), (0, 0, 1.17), "hips"),
    "chest": ((0, 0, 1.17), (0, 0, 1.42), "spine"),
    "neck": ((0, 0.01, 1.44), (0, 0.0, 1.53), "chest"),
    "head": ((0, 0.0, 1.53), (0, 0.0, 1.78), "neck"),
    "shoulder_l": ((0.03, 0.01, 1.4), tuple(SHOULDER), "chest"),
    "upper_arm_l": (tuple(SHOULDER), tuple(ELBOW), "shoulder_l"),
    "lower_arm_l": (tuple(ELBOW), tuple(WRIST), "upper_arm_l"),
    "hand_l": (tuple(WRIST), tuple(KNUCKLES), "lower_arm_l"),
    "fingers_l": (tuple(KNUCKLES), tuple(FINGER_TIP), "hand_l"),
    "thumb_l": (tuple(WRIST), tuple(THUMB_TIP), "hand_l"),
    "upper_leg_l": (tuple(HIP), tuple(KNEE), "hips"),
    "lower_leg_l": (tuple(KNEE), tuple(ANKLE), "upper_leg_l"),
    "foot_l": (tuple(ANKLE), tuple(BALL), "lower_leg_l"),
    "toes_l": (tuple(BALL), tuple(TOE), "foot_l"),
  })


# --- Material & mesh helpers -----------------------------------------------------------------
def make_material(name, color, roughness=0.84, metallic=0.0):
  mat = material(name, color, roughness=roughness)
  bsdf = mat.node_tree.nodes.get("Principled BSDF")
  if bsdf is not None:
    bsdf.inputs["Metallic"].default_value = metallic
  return mat


def scale_rgb(rgb, factor):
  return tuple(max(0.0, min(1.0, c * factor)) for c in rgb)


def mix_rgb(a, b, t):
  return tuple(u + (v - u) * t for u, v in zip(a, b))


def ring(z, a, front, back, y=0.0, n=10, power=2.5, x=0.0):
  """A rounded-box section: half width a, depth front and back. Angle 0 faces the camera (-Y)."""
  points = []
  for k in range(n):
    phi = math.tau * (k + 0.5) / n
    s, c = math.sin(phi), math.cos(phi)
    px = a * math.copysign(abs(s) ** (2.0 / power), s)
    depth = front if c > 0 else back
    py = -depth * math.copysign(abs(c) ** (2.0 / power), c)
    points.append((x + px, y + py, z))
  return points


def mirror_x(points):
  return [(-x, y, z) for x, y, z in points]


def flip_path(path):
  return [((-p[0], p[1], p[2]), ru, rv) for p, ru, rv in path]


def solid_shell(shape, rows, thickness, mat_outer, mat_inner=None, mat_edge=None, inward_dir=None):
  """Closed faceted plate from open rows (r x c), with explicit inward normal direction."""
  mat_inner = mat_inner or mat_outer
  mat_edge = mat_edge or mat_outer
  rcount, ccount = len(rows), len(rows[0])
  outer = [[Vector(p) for p in row] for row in rows]
  inner = []
  for r in range(rcount):
    irow = []
    for c in range(ccount):
      p = outer[r][c]
      if inward_dir is not None:
        n = inward_dir(p, r, c)
      else:
        dr = outer[min(r + 1, rcount - 1)][c] - outer[max(r - 1, 0)][c]
        dc = outer[r][min(c + 1, ccount - 1)] - outer[r][max(c - 1, 0)]
        n = dc.cross(dr)
        n = n.normalized() if n.length > 1e-6 else Vector((0, 1, 0))
      irow.append(p + n * thickness)
    inner.append(irow)

  verts = [tuple(p) for row in outer for p in row] + [tuple(p) for row in inner for p in row]
  base = rcount * ccount
  faces, mats = [], []
  for r in range(rcount - 1):
    for c in range(ccount - 1):
      a, b = r * ccount + c, r * ccount + c + 1
      faces.append((a, b, b + ccount, a + ccount))
      mats.append(mat_outer)
      faces.append((base + a + ccount, base + b + ccount, base + b, base + a))
      mats.append(mat_inner)
  for r in range(rcount - 1):
    for c in (0, ccount - 1):
      a, b = r * ccount + c, (r + 1) * ccount + c
      faces.append((a, b, base + b, base + a) if c else (b, a, base + a, base + b))
      mats.append(mat_edge)
  for r in (0, rcount - 1):
    for c in range(ccount - 1):
      a, b = r * ccount + c, r * ccount + c + 1
      faces.append((b, a, base + a, base + b) if r == 0 else (a, b, base + b, base + a))
      mats.append(mat_edge)
  shape.add(verts, faces, mats)


def shell(shape, rows, thickness, mat):
  center = Vector((0.0, 0.004, 1.652))
  solid_shell(shape, rows, thickness, mat, inward_dir=lambda p, r, c: (center - p).normalized())


# --- Sculpted head surface -------------------------------------------------------------------
HEAD = [
  # z, half width, front, back, center y
  (1.522, 0.036, 0.062, 0.034, -0.004),  # Chin tip
  (1.544, 0.058, 0.088, 0.052, -0.002),  # Lower jaw
  (1.576, 0.078, 0.098, 0.074, 0.000),   # Jaw angle / mouth level
  (1.610, 0.088, 0.102, 0.090, 0.001),   # Lower cheeks
  (1.644, 0.095, 0.104, 0.100, 0.002),   # Cheekbones
  (1.668, 0.094, 0.101, 0.106, 0.004),   # Eye line (mid-skull)
  (1.694, 0.095, 0.104, 0.110, 0.005),   # Brow ridge
  (1.724, 0.090, 0.096, 0.108, 0.007),   # Forehead
  (1.752, 0.078, 0.078, 0.094, 0.009),   # Upper skull curve
  (1.770, 0.056, 0.055, 0.068, 0.010),   # Rounded dome
  (1.782, 0.024, 0.024, 0.030, 0.010),   # Crown apex
]


def head_point(z, phi, grow=0.0, sculpt=True):
  """Point on the sculpted head surface at height z and angle phi (0 is front -Y, + toward left +X)."""
  for (z0, a0, f0, b0, y0), (z1, a1, f1, b1, y1) in zip(HEAD, HEAD[1:]):
    if z <= z1:
      t = max(0.0, min(1.0, (z - z0) / (z1 - z0)))
      break
  else:
    (z0, a0, f0, b0, y0), (z1, a1, f1, b1, y1), t = HEAD[-2], HEAD[-1], 1.0
  a, f, b, y = (u + (v - u) * t for u, v in zip((a0, f0, b0, y0), (a1, f1, b1, y1)))
  abs_phi = abs(math.atan2(math.sin(phi), math.cos(phi)))
  s, c = math.sin(phi), math.cos(phi)

  relief = 0.0
  if sculpt and c > -0.15:
    # Recessed eye sockets
    eye_s = math.exp(-((z - 1.668) / 0.015) ** 2) * math.exp(-((abs_phi - 0.36) / 0.19) ** 2)
    relief -= 0.0085 * eye_s
    # Strong masculine brow ridge
    brow_s = math.exp(-((z - 1.693) / 0.013) ** 2) * math.exp(-((abs_phi) / 0.62) ** 2)
    relief += 0.0062 * brow_s
    # Defined cheekbones
    cheek_b = math.exp(-((z - 1.644) / 0.017) ** 2) * math.exp(-((abs_phi - 0.65) / 0.25) ** 2)
    relief += 0.0055 * cheek_b
    # Subtle cheek plane under zygomatic arch
    hollow = math.exp(-((z - 1.608) / 0.022) ** 2) * math.exp(-((abs_phi - 0.68) / 0.28) ** 2)
    relief -= 0.0052 * hollow
    # Flattened temples
    temple = math.exp(-((z - 1.698) / 0.022) ** 2) * math.exp(-((abs_phi - 1.12) / 0.22) ** 2)
    relief -= 0.0042 * temple
    # Firm chin
    chin = math.exp(-((z - 1.540) / 0.018) ** 2) * math.exp(-((abs_phi) / 0.36) ** 2)
    relief += 0.0050 * chin
    # Subtle philtrum / mouth recess
    mouth_r = math.exp(-((z - 1.590) / 0.011) ** 2) * math.exp(-((abs_phi) / 0.28) ** 2)
    relief -= 0.0032 * mouth_r

  power = 2.45
  px = (a + grow + relief * 0.62) * math.copysign(abs(s) ** (2.0 / power), s)
  depth = (f if c > 0 else b) + grow + relief
  py = y - depth * math.copysign(abs(c) ** (2.0 / power), c)
  return (px, py, z)


def hairline(phi):
  """Where the hair starts, from forehead (phi 0) round to nape (pi)."""
  side = abs(math.atan2(math.sin(phi), math.cos(phi))) / math.pi
  temple_dip = 0.014 * math.exp(-((side - 0.23) / 0.08) ** 2)
  nape = math.sin(math.pi / 2 * min(1.0, max(0.0, (side - 0.48) / 0.32)))
  return 1.726 + temple_dip - 0.064 * min(1.0, side / 0.45) ** 1.45 - 0.082 * nape


def beardline(phi):
  """Lower, natural cheek beardline curving up smoothly into sideburns by the ears."""
  side = abs(math.atan2(math.sin(phi), math.cos(phi))) / math.pi
  # Stays low across the cheeks (~1.586-1.600) and rises sharply only near the sideburn (side > 0.40)
  return 1.588 + 0.016 * (side ** 1.4) + 0.060 * max(0.0, (side - 0.36) / 0.24) ** 1.6


# --- Parametric torso surface (athletic-slim adult male, natural shirt drape) ----------------
SHIRT_STATIONS = [
  # z, half_w, front, back, y_shift, fold_amp
  (0.864, 0.184, 0.123, 0.123, 0.002, 0.006),  # Shirt hem cleanly above belt
  (0.930, 0.172, 0.114, 0.114, 0.002, 0.004),  # Upper hip
  (1.025, 0.161, 0.107, 0.108, 0.002, 0.004),  # Tapered waist
  (1.135, 0.173, 0.119, 0.114, -0.002, 0.003), # Lower ribcage
  (1.245, 0.194, 0.132, 0.118, -0.006, 0.002), # Pectorals / mid-back
  (1.345, 0.200, 0.124, 0.116, -0.003, 0.001), # Upper chest / shoulder blades
  (1.412, 0.164, 0.098, 0.102, 0.003, 0.000),  # Natural sloping trapezius
  (1.454, 0.084, 0.068, 0.072, 0.010, 0.000),  # Collar base
]


def shirt_params(z):
  if z <= SHIRT_STATIONS[0][0]:
    return SHIRT_STATIONS[0][1:]
  for s0, s1 in zip(SHIRT_STATIONS, SHIRT_STATIONS[1:]):
    if z <= s1[0]:
      t = (z - s0[0]) / (s1[0] - s0[0])
      return tuple(a + (b - a) * t for a, b in zip(s0[1:], s1[1:]))
  return SHIRT_STATIONS[-1][1:]


def shirt_point(z, phi, w=1.0, grow=0.0, folds=True):
  """Point on the sculpted shirt surface at height z and angle phi (0 is front -Y, +pi/2 is left +X)."""
  a, f, b, yc, famp = shirt_params(z)
  abs_phi = abs(math.atan2(math.sin(phi), math.cos(phi)))
  s, c = math.sin(phi), math.cos(phi)

  relief = 0.0
  if folds:
    # Subtle chest / shoulder-blade volume
    if c > 0.1:
      pec = math.exp(-((z - 1.275) / 0.065) ** 2) * math.exp(-((abs_phi - 0.42) / 0.34) ** 2)
      relief += 0.009 * pec
      sternum = math.exp(-((z - 1.28) / 0.07) ** 2) * math.exp(-((abs_phi) / 0.18) ** 2)
      relief -= 0.004 * sternum
    if c < -0.1:
      scap = math.exp(-((z - 1.305) / 0.075) ** 2) * math.exp(-((abs_phi - 2.65) / 0.35) ** 2)
      relief += 0.008 * scap
      spine_g = math.exp(-((z - 1.20) / 0.16) ** 2) * math.exp(-((math.pi - abs_phi) / 0.18) ** 2)
      relief -= 0.005 * spine_g
    # Soft natural cloth folds near waist & hem
    if famp > 0.0:
      relief += famp * (0.55 * math.cos(5.0 * phi + 0.3) + 0.45 * math.sin(3.0 * phi - 0.2))

  power = 2.45
  px = (a * w + grow + relief * 0.55) * math.copysign(abs(s) ** (2.0 / power), s)
  depth = (f if c > 0 else b) * w + grow + relief
  py = yc - depth * math.copysign(abs(c) ** (2.0 / power), c)
  return (px, py, z)


def vneck_z(phi):
  """Top edge z of the shirt around the neck, dipping into a crisp V in front."""
  abs_phi = abs(math.atan2(math.sin(phi), math.cos(phi)))
  if abs_phi < 0.62:
    # Linear-curved V dip down to z = 1.358 at center chest (phi = 0)
    t = 1.0 - abs_phi / 0.62
    return 1.456 - 0.098 * (t ** 1.25)
  return 1.456 + 0.006 * max(0.0, -math.cos(phi))


# --- The body --------------------------------------------------------------------------------
def build_person(look, name):
  """One mesh for the body and, if worn, one for the backpack, both tagged for rigging."""
  M = {key: make_material(f"{name}_{key}", value) for key, value in look.items() if isinstance(value, tuple)}
  M["eye"] = make_material(f"{name}_eye", (0.055, 0.036, 0.025), roughness=0.44)
  M["eye_white"] = make_material(f"{name}_eye_white", (0.86, 0.83, 0.78), roughness=0.48)
  M["lid"] = make_material(f"{name}_lid", scale_rgb(look["skin"], 0.76), roughness=0.86)
  M["skin_bag"] = make_material(f"{name}_skin_bag", scale_rgb(look["skin"], 0.85), roughness=0.86)
  M["lip"] = make_material(f"{name}_lip", mix_rgb(look["skin"], (0.46, 0.22, 0.19), 0.36), roughness=0.82)
  M["stubble"] = make_material(f"{name}_stubble", mix_rgb(look["skin"], look["hair"], 0.46), roughness=0.88)
  M["hair_dark"] = make_material(f"{name}_hair_dark", scale_rgb(look["hair"], 0.68), roughness=0.88)
  M["shirt_dark"] = make_material(f"{name}_shirt_dark", scale_rgb(look["trim"], 0.68), roughness=0.90)
  M["belt"] = make_material(f"{name}_belt", (0.16, 0.11, 0.075), roughness=0.72)
  M["buckle"] = make_material(f"{name}_buckle", (0.56, 0.50, 0.36), roughness=0.38, metallic=0.72)
  M["shoe_accent"] = make_material(f"{name}_shoe_accent", scale_rgb(look["shoes"], 0.62), roughness=0.86)
  M["shoe_lace"] = make_material(f"{name}_shoe_lace", (0.72, 0.70, 0.65), roughness=0.88)
  if "pack" in look:
    M["pack_dark"] = make_material(f"{name}_pack_dark", scale_rgb(look["strap"], 0.68), roughness=0.88)
    M["pack_roll"] = make_material(f"{name}_pack_roll", mix_rgb(look["pack"], (0.34, 0.35, 0.28), 0.55), roughness=0.90)
  M["watch_band"] = make_material(f"{name}_watch_band", (0.11, 0.10, 0.10), roughness=0.75)
  M["watch_case"] = make_material(f"{name}_watch_case", (0.62, 0.63, 0.66), roughness=0.32, metallic=0.82)
  M["watch_face"] = make_material(f"{name}_watch_face", (0.10, 0.14, 0.17), roughness=0.18)

  w = look.get("build", 1.0)
  simple = look.get("simple", False)
  R_HEAD = 10 if simple else 18
  R_TORSO = 8 if simple else 18
  L_LEG = 6 if simple else 10
  L_ARM = 5 if simple else 8
  body = Shape()
  tag = Tags(body)

  # --- 1. SCULPTED HEAD, FACE, EARS, BEARD & HAIR --------------------------------------------
  tag("head")
  head_zs = [st[0] for st in (HEAD[1::2] + HEAD[-1:] if simple else HEAD)]
  head_phis = [math.tau * (k + 0.5) / R_HEAD for k in range(R_HEAD)]
  head_rings = [[head_point(z, phi, sculpt=not simple) for phi in head_phis] for z in head_zs]
  body.loft(head_rings, M["skin"], caps=(True, True))

  # Nose: sculpted bridge, defined rounded tip and flared nostrils.
  nose_verts = [
    (0.0, -0.100, 1.686),      # 0 bridge root
    (-0.0085, -0.109, 1.664),  # 1 left mid-bridge
    (0.0085, -0.109, 1.664),   # 2 right mid-bridge
    (0.0, -0.130, 1.638),      # 3 nose tip
    (-0.020, -0.106, 1.630),   # 4 left nostril wing outer
    (0.020, -0.106, 1.630),    # 5 right nostril wing outer
    (0.0, -0.115, 1.622),      # 6 columella base
    (-0.015, -0.098, 1.650),   # 7 left nose side
    (0.015, -0.098, 1.650),    # 8 right nose side
    (-0.011, -0.120, 1.626),   # 9 left tip underside
    (0.011, -0.120, 1.626),    # 10 right tip underside
  ]
  body.add(
    nose_verts,
    [(0, 1, 3), (0, 3, 2), (1, 7, 4), (1, 4, 9, 3), (2, 3, 10, 5), (2, 5, 8),
     (3, 9, 6), (3, 6, 10), (9, 4, 6), (10, 6, 5)],
    M["skin"],
  )

  if not simple:
    for side in (-1, 1):
      def on_face(dphi, z, grow):
        return head_point(z, side * (0.36 + dphi), grow)

      # Calm, slightly weary almond eye with full dark iris and relaxed upper lid
      almond = [(-0.130, -0.001), (-0.055, 0.0062), (0.045, 0.0065), (0.130, 0.0005), (0.055, -0.0050), (-0.055, -0.0050)]
      body.add([on_face(dp, 1.667 + dz, 0.0020) for dp, dz in almond], [(0, 1, 2, 3, 4, 5)], M["eye_white"])
      body.add([on_face(dp * 0.70 - 0.008, 1.6672 + dz * 0.96, 0.0036) for dp, dz in almond], [(0, 1, 2, 3, 4, 5)], M["eye"])

      # Relaxed upper eyelid slightly covering top of iris (natural calm gaze, not startled)
      lid_low = [on_face(dp * 1.02, 1.667 + dz - 0.0004, 0.0038) for dp, dz in almond[:4]]
      lid_high = [on_face(dp * 1.08, 1.667 + dz + 0.0046, 0.0062) for dp, dz in almond[:4]]
      shell(body, [lid_low, lid_high], 0.0036, M["lid"])

      bag_top = [on_face(dp, 1.667 + dz - 0.0012, 0.0016) for dp, dz in (almond[0], almond[5], almond[4], almond[3])]
      bag_bot = [on_face(dp * 1.04, 1.667 + dz - 0.0060, 0.0018) for dp, dz in (almond[0], almond[5], almond[4], almond[3])]
      shell(body, [bag_bot, bag_top], 0.0020, M["skin_bag"])

      # Masculine, grounded eyebrows (lower, straighter inner brow)
      brow = [(-0.19, 1.682, 1.693), (-0.05, 1.684, 1.695), (0.10, 1.685, 1.694), (0.23, 1.681, 1.688)]
      shell(
        body,
        [[on_face(dp, lo, 0.0048) for dp, lo, hi in brow],
         [on_face(dp, hi, 0.0080) for dp, lo, hi in brow]],
        0.0060,
        M["hair"],
      )

      # Sculpted ears (outer helix + lobe + recessed inner backing)
      ear_outer = [
        (side * 0.094, 0.008, 1.622),
        (side * 0.111, 0.018, 1.630),
        (side * 0.115, 0.026, 1.656),
        (side * 0.111, 0.025, 1.684),
        (side * 0.096, 0.008, 1.690),
        (side * 0.092, 0.004, 1.656),
      ]
      ear_inner = [(side * 0.086, p[1] - 0.003, p[2]) for p in ear_outer]
      n_e = len(ear_outer)
      efaces = [tuple(range(n_e)), tuple(range(2 * n_e - 1, n_e - 1, -1))]
      for k in range(n_e):
        nk = (k + 1) % n_e
        efaces.append((k, nk, n_e + nk, n_e + k))
      body.add(ear_outer + ear_inner, efaces, M["skin"])

    # Sculpted trimmed full beard + moustache + clearly visible natural lips
    if look.get("beard"):
      angles = [math.radians(a) for a in range(-102, 103, 17)]
      rows = []
      for k in range(7):
        t = k / 6
        row = []
        for phi in angles:
          side_f = abs(phi) / math.radians(102)
          bottom = 1.514 + 0.072 * (side_f ** 1.9)
          top = beardline(phi)
          z = bottom + (top - bottom) * t
          chin_full = (0.010 * max(0.0, math.cos(phi)) ** 1.4 + 0.0035) * (1.0 - 0.55 * side_f)
          taper = math.sin(math.pi * min(1.0, 0.20 + 0.80 * t))
          if k == 0:
            bulk = -0.002
          elif k == 6:
            bulk = 0.0024
          else:
            bulk = 0.0030 + chin_full * taper
          row.append(head_point(z, phi, bulk))
        rows.append(row)
      shell(body, rows, 0.013, M["hair"])

      # Subtle narrow stubble fade along cheek beardline
      stubble_angles = [math.radians(a) for a in range(-96, 97, 16)]
      stubble_rows = [
        [head_point(beardline(phi) - 0.002, phi, 0.0018) for phi in stubble_angles],
        [head_point(beardline(phi) + 0.007, phi, 0.0012) for phi in stubble_angles],
      ]
      shell(body, stubble_rows, 0.0020, M["stubble"])

      # Sculpted moustache sitting cleanly above the upper lip, curving into beard at corners
      mo_top = [head_point(1.612 - 0.010 * (abs(a) / 42.0) ** 1.5, math.radians(a), 0.0065) for a in (-42, -26, -12, 0, 12, 26, 42)]
      mo_bot = [head_point(1.601 - 0.014 * (abs(a) / 46.0) ** 1.3, math.radians(a), 0.0092) for a in (-46, -28, -13, 0, 13, 28, 46)]
      shell(body, [mo_bot, mo_top], 0.0075, M["hair"])

      # Subtle natural lips peeking cleanly between moustache and chin beard
      lip_u = [head_point(1.597 - 0.002 * (abs(a) / 16.0), math.radians(a), 0.0082) for a in (-16, -8, 0, 8, 16)]
      lip_m = [head_point(1.592, math.radians(a), 0.0072) for a in (-15, -7, 0, 7, 15)]
      lip_l = [head_point(1.586 + 0.002 * (abs(a) / 14.0), math.radians(a), 0.0094) for a in (-14, -7, 0, 7, 14)]
      shell(body, [lip_m, lip_u], 0.0045, M["lip"])
      shell(body, [lip_l, lip_m], 0.0050, M["lip"])
    else:
      # Clean-shaven mouth
      lip_u = [head_point(1.596, math.radians(a), 0.004) for a in (-18, 0, 18)]
      lip_l = [head_point(1.588, math.radians(a), 0.005) for a in (-16, 0, 16)]
      shell(body, [lip_l, lip_u], 0.004, M["lip"])

  # Hair: base cap + cohesive swept-back layered quiff (for Luis) or short/long/cap variants
  style = look.get("hairstyle")
  if style:
    volume = 0.0 if style in ("short", "cap") else 1.0
    angles = [math.radians(a) for a in range(-180, 181, 40 if simple else 18)]
    rows = []
    steps = 3 if simple else 7
    for k in range(steps + 1):
      t = k / steps
      row = []
      for phi in angles:
        low = hairline(phi)
        z = low + (1.784 - low) * t
        front = max(0.0, math.cos(phi))
        back = max(0.0, -math.cos(phi))
        side_w = abs(math.sin(phi))
        # Subtle asymmetric swept-back crest (parted slightly toward +X left)
        asym = 0.005 * math.sin(phi + 0.35) * front
        grow = (
          0.0045
          + volume * (
            0.020 * (t ** 1.15) * (0.40 + 0.60 * front)
            + (0.007 + 0.009 * back) * math.sin(math.pi * t)
            + 0.003 * side_w * math.sin(math.pi * t)
            + asym * t
          )
        )
        lift = volume * (0.024 * (front ** 1.5) + 0.008 * max(0.0, math.sin(phi + 0.3))) * math.sin(math.pi * min(1.0, t * 1.10))
        p = Vector(head_point(min(z, 1.782), phi, grow, sculpt=not simple))
        p.z += lift
        row.append(tuple(p))
      rows.append(row)
    top_z = 1.812 if volume else 1.792
    rows[-1] = [tuple(Vector((0.004, 0.016, top_z)).lerp(Vector(p), 0.35)) for p in rows[-1]]
    shell(body, rows, 0.018, M["hair"])

    if not simple:
      # Clean faded nape and sideburn taper
      back_a = [math.radians(a) for a in range(106, 255, 14)]
      fade = [
        [head_point(hairline(phi) + 0.005, phi, 0.0028) for phi in back_a],
        [head_point(1.540, phi, 0.0018) for phi in back_a],
      ]
      shell(body, fade, 0.0022, M["stubble"])

      # Cohesive overlapping swept-back waves (no comb-tooth gaps!)
      if style == "swept":
        wave_specs = [
          # (phi_start_deg, phi_end_deg, lift_z, grow_extra, mat_key)
          (-52, 16, 0.028, 0.015, "hair"),
          (-14, 54, 0.022, 0.012, "hair_dark"),
          (-32, 34, 0.032, 0.018, "hair"),
        ]
        for p0_deg, p1_deg, lift_z, g_ex, mkey in wave_specs:
          w_rows = []
          for step in range(6):
            u = step / 5.0
            # Sweep smoothly from forehead hairline up over the crown to the back
            z_arc = 1.732 + (1.784 + lift_z - 1.732) * math.sin(math.pi * 0.52 * min(1.0, u * 1.15))
            if u > 0.65:
              uu = (u - 0.65) / 0.35
              z_arc -= 0.075 * (uu ** 1.35)
            y_pos = -0.098 + 0.215 * u
            taper = math.sin(math.pi * (0.08 + 0.84 * u))
            row = []
            for ci in range(5):
              v = ci / 4.0
              ang = math.radians(p0_deg + (p1_deg - p0_deg) * v)
              # Gentle diagonal sweep toward the right-back
              ang_swept = ang + math.radians(10.0 * u)
              arch = math.sin(math.pi * v)
              r_x = 0.092 * math.sin(ang_swept) * (0.86 + 0.14 * taper)
              ridge = (0.006 * arch + 0.003 * math.sin(math.tau * v)) * taper
              px = r_x
              py = y_pos - (0.012 + g_ex * arch) * (1.0 - u) + 0.008 * u
              pz = z_arc + ridge - 0.010 * (1.0 - arch)
              row.append((px, py, pz))
            w_rows.append(row)
          solid_shell(
            body, w_rows, 0.012, M[mkey], M["hair_dark"], M[mkey],
            inward_dir=lambda p, r, c: (Vector((0.0, 0.005, 1.66)) - p).normalized(),
          )

    if style == "long":
      back_a = [math.radians(a) for a in range(95, 266, 17)]
      fall = []
      for k, z in enumerate((1.7, 1.6, 1.5, 1.42, 1.36)):
        row = []
        for phi in back_a:
          p = Vector(head_point(max(z, 1.52), phi, 0.022 + 0.012 * k, sculpt=False))
          p.z = z
          if z < 1.52:
            p.y += 0.03 * (1.52 - z) / 0.16
          row.append(tuple(p))
        fall.append(row)
      shell(body, fall, 0.024, M["hair"])
    if style == "cap":
      crown = [head_point(1.72, phi, 0.016, sculpt=False) for phi in [math.tau * k / 12 for k in range(12)]]
      dome = [
        [(x, y, z) for x, y, z in crown],
        [tuple(Vector((0, 0.005, 1.8)).lerp(Vector(p), 0.75) + Vector((0, 0, 0.055))) for p in crown],
      ]
      body.loft(dome, M["cap"])
      body.box((-0.085, -0.2, 1.71), (0.085, -0.09, 1.725), M["cap"])

  # --- 2. ANATOMICAL NECK & UPPER CHEST SKIN (seals V-neck opening cleanly) ------------------
  tag("neck", "head", "chest")
  # Continuous inner chest/trapezius skin shell under the V-neck so no dark gap ever shows
  chest_skin_phis = [math.tau * k / (8 if simple else 14) for k in range(8 if simple else 14)]
  chest_skin_rings = [
    [shirt_point(1.315, phi, w=w, grow=-0.010, folds=False) for phi in chest_skin_phis],
    [shirt_point(1.385, phi, w=w, grow=-0.008, folds=False) for phi in chest_skin_phis],
    [shirt_point(1.430, phi, w=w, grow=-0.008, folds=False) for phi in chest_skin_phis],
    [ring(1.462, 0.066 * w, 0.058 * w, 0.060 * w, y=0.012, n=len(chest_skin_phis), power=2.2)[k] for k in range(len(chest_skin_phis))],
    [ring(1.505, 0.053 * w, 0.050 * w, 0.051 * w, y=0.010, n=len(chest_skin_phis), power=2.2)[k] for k in range(len(chest_skin_phis))],
    [ring(1.555, 0.049 * w, 0.049 * w, 0.049 * w, y=0.006, n=len(chest_skin_phis), power=2.2)[k] for k in range(len(chest_skin_phis))],
  ]
  body.loft(chest_skin_rings, M["skin"], caps=(True, True))

  # --- 3. SCULPTED OLIVE V-NECK T-SHIRT ------------------------------------------------------
  tag("hips", "spine", "chest")
  shirt_phis = [math.tau * k / R_TORSO for k in range(R_TORSO)]
  shirt_rings = []
  for idx, st in enumerate(SHIRT_STATIONS):
    z_base = st[0]
    row = []
    for phi in shirt_phis:
      if not simple and idx >= len(SHIRT_STATIONS) - 2:
        # Smoothly dip the top two rings down into a crisp V-neck in front
        v_top = vneck_z(phi)
        if idx == len(SHIRT_STATIONS) - 1:
          z_pt = v_top
        else:
          z_pt = min(z_base, v_top - 0.022)
        row.append(shirt_point(z_pt, phi, w=w, grow=0.0, folds=True))
      else:
        row.append(shirt_point(z_base, phi, w=w, grow=0.0, folds=not simple))
    shirt_rings.append(row)

  body.loft(shirt_rings, M["shirt"], caps=(False, simple))

  if not simple:
    # Inner hem lip at bottom of shirt so it reads as real cloth over the belt/pants
    hem_outer = shirt_rings[0]
    hem_inner = [shirt_point(SHIRT_STATIONS[0][0] + 0.006, phi, w=w, grow=-0.014, folds=False) for phi in shirt_phis]
    body.loft([hem_inner, hem_outer], M["shirt_dark"], caps=(False, False))

    # Real 3D V-neck ribbed collar trim following the neckline cleanly
    neck_phis = [math.tau * k / 24 for k in range(25)]
    trim_top = [shirt_point(vneck_z(phi) + 0.004, phi, w=w, grow=0.0042, folds=True) for phi in neck_phis]
    trim_bot = [shirt_point(vneck_z(phi) - 0.017, phi, w=w, grow=0.0048, folds=True) for phi in neck_phis]
    solid_shell(
      body, [trim_bot, trim_top], 0.007, M["trim"], M["shirt_dark"], M["trim"],
      inward_dir=lambda p, r, c: Vector((-p.x, -p.y, 0.0)).normalized(),
    )

    # Subtle side & shoulder seams on the shirt
    for s in (-1, 1):
      phi_side = s * math.pi * 0.5
      seam_pts = [(shirt_point(z, phi_side, w=w, grow=0.0018, folds=True), 0.0030, 0.0020) for z in (0.875, 1.00, 1.15, 1.29)]
      body.tube(seam_pts, M["trim"], n=4)

  # --- 4. PELVIS, BELT & CARGO PANTS ---------------------------------------------------------
  tag("hips", "upper_leg_l", "upper_leg_r")
  pelvis = [
    ring(z, a * w, f * w, b * w, y=yc, n=R_TORSO, power=2.4)
    for z, a, f, b, yc in (
      (0.775, 0.166, 0.106, 0.110, 0.002),
      (0.845, 0.172, 0.112, 0.114, 0.002),
      (0.915, 0.168, 0.109, 0.110, 0.002),
      (0.965, 0.162, 0.105, 0.106, 0.002),
    )[::2 if simple else 1]
  ]
  body.loft(pelvis, M["pants"], caps=(True, True))

  if not simple:
    # Clean dark belt sitting just beneath the shirt hem (zero z-fighting) + aged brass buckle
    belt_r = [
      ring(0.824, 0.175 * w, 0.117 * w, 0.119 * w, y=0.002, n=16, power=2.4),
      ring(0.854, 0.175 * w, 0.117 * w, 0.119 * w, y=0.002, n=16, power=2.4),
    ]
    body.loft(belt_r, M["belt"], caps=(True, True))
    body.box((-0.025, -0.124 * w, 0.820), (0.025, -0.110 * w, 0.858), M["buckle"])
    body.box((-0.015, -0.126 * w, 0.828), (0.015, -0.119 * w, 0.850), M["belt"])

    # Subtle rear pockets tucked cleanly on the seat of the cargo pants
    for s in (-1, 1):
      bx0, bx1 = sorted((s * 0.032 * w, s * 0.122 * w))
      body.box((bx0, 0.104 * w, 0.755), (bx1, 0.116 * w, 0.818), M["pants_dark"])

  # --- 5. LEGS, SCULPTED CARGO POCKETS, SHOES, SLEEVES, ARMS & HANDS -------------------------
  for side, s in (("_l", 1), ("_r", -1)):
    tag("hips", "upper_leg" + side, "lower_leg" + side)
    leg = [
      ((s * 0.095, 0.002, 0.905), 0.090 * w, 0.092 * w),
      ((s * 0.097, -0.002, 0.760), 0.086 * w, 0.088 * w),
      ((s * 0.099, -0.006, 0.620), 0.078 * w, 0.081 * w),
      ((s * 0.100, -0.014, 0.490), 0.068 * w, 0.073 * w),  # Knee
      ((s * 0.102, -0.004, 0.350), 0.069 * w, 0.072 * w),  # Calf fullness
      ((s * 0.104, 0.004, 0.210), 0.064 * w, 0.066 * w),
      ((s * 0.105, 0.008, 0.138), 0.066 * w, 0.068 * w),   # Natural trouser break above shoe
    ]
    body.tube(leg[::2] if simple else leg, M["pants"], n=L_LEG, side=(1, 0, 0))
    # Rolled / stitched cargo cuff at the ankle
    body.tube([
      ((s * 0.105, 0.008, 0.152), 0.070 * w, 0.071 * w),
      ((s * 0.105, 0.008, 0.118), 0.071 * w, 0.072 * w),
    ], M["pants_dark"], n=L_LEG, side=(1, 0, 0))
    # Ankle sock/inner pant shadow
    body.tube([
      ((s * 0.105, 0.008, 0.130), 0.048 * w, 0.050 * w),
      ((s * 0.105, 0.008, 0.065), 0.044 * w, 0.046 * w),
    ], M["sole"], n=6, side=(1, 0, 0))

    # Sculpted cargo pocket hugging the outer thigh curvature (bellows + bevelled flap + button)
    tag("upper_leg" + side)
    if simple:
      px = s * (0.098 + 0.080 * w)
      body.box((min(px, px + s * 0.026), -0.055, 0.56), (max(px, px + s * 0.026), 0.045, 0.71), M["pants_dark"])
    else:
      thigh_cx = s * 0.098
      thigh_cy = -0.004
      p_rows = []
      for kz, z_p in enumerate((0.555, 0.615, 0.675, 0.705)):
        r_thigh = (0.076 + 0.009 * (kz / 3.0)) * w
        bulge = 0.022 if kz in (1, 2) else 0.015
        row = []
        for ang_deg in (-36, -18, 0, 18, 36):
          ang = math.radians(ang_deg)
          pleat = 0.004 if ang_deg == 0 else 0.0
          r = r_thigh + bulge + pleat
          row.append((thigh_cx + s * r * math.cos(ang), thigh_cy + r * math.sin(ang), z_p))
        p_rows.append(row)
      solid_shell(
        body, p_rows, 0.018, M["pants_dark"], M["pants_dark"], M["pants_dark"],
        inward_dir=lambda p, r, c, cx=thigh_cx, cy=thigh_cy: Vector((cx - p.x, cy - p.y, 0.0)).normalized(),
      )
      # Bevelled top flap + dark snap button
      flap_rows = []
      for z_f, extra in ((0.682, 0.026), (0.718, 0.018)):
        r_thigh = 0.084 * w
        row = []
        for ang_deg in (-38, 0, 38):
          ang = math.radians(ang_deg)
          r = r_thigh + extra
          row.append((thigh_cx + s * r * math.cos(ang), thigh_cy + r * math.sin(ang), z_f))
        flap_rows.append(row)
      solid_shell(
        body, flap_rows, 0.012, M["pants"], M["pants_dark"], M["pants_dark"],
        inward_dir=lambda p, r, c, cx=thigh_cx, cy=thigh_cy: Vector((cx - p.x, cy - p.y, 0.0)).normalized(),
      )
      bx = thigh_cx + s * (0.084 * w + 0.028)
      body.box((bx - 0.005, thigh_cy - 0.007, 0.686), (bx + 0.005, thigh_cy + 0.007, 0.698), M["belt"])

    # Sculpted urban sneaker / low-cut boot, toe toward -Y
    tag("foot" + side, "toes" + side, "lower_leg" + side)
    x = s * 0.105
    if simple:
      profile = [(0.07, 0.0), (0.07, 0.085), (0.02, 0.12), (-0.06, 0.1), (-0.15, 0.06), (-0.185, 0.03), (-0.185, 0.0)]
      for half, mat, lift in ((0.054, M["shoes"], 0.012), (0.058, M["sole"], 0.0)):
        outline = [(y, z + lift) for y, z in profile] if lift else [(0.075, 0.0), (0.075, 0.022), (-0.19, 0.022), (-0.19, 0.0)]
        verts = [(x + dx, py, pz) for dx in (-half, half) for py, pz in outline]
        count = len(outline)
        faces = [tuple(range(count))[::-1], tuple(range(count, 2 * count))]
        for k in range(count):
          n = (k + 1) % count
          faces.append((k, n, count + n, count + k))
        body.add(verts, faces, mat)
    else:
      # Multi-station lofted sneaker: heel -> ankle -> instep -> forefoot -> rounded toe
      shoe_stations = [
        # (y_pos, z_bot, z_top, half_w_in, half_w_out)
        (0.076, 0.020, 0.088, 0.042, 0.044),   # Heel counter
        (0.025, 0.018, 0.106, 0.047, 0.050),   # Ankle collar
        (-0.042, 0.018, 0.092, 0.050, 0.054),  # Instep / laces
        (-0.115, 0.018, 0.062, 0.052, 0.057),  # Ball of foot
        (-0.168, 0.020, 0.044, 0.042, 0.047),  # Toe box
        (-0.190, 0.022, 0.034, 0.022, 0.025),  # Toe tip
      ]
      shoe_rings = []
      for py, zb, zt, wi, wo in shoe_stations:
        x_in = x - s * wi
        x_out = x + s * wo
        zm = zb + (zt - zb) * 0.52
        shoe_rings.append([
          (x_in * 0.85 + x * 0.15, py, zb),
          (x_out * 0.85 + x * 0.15, py, zb),
          (x_out, py, zm),
          (x_out * 0.72 + x * 0.28, py, zt),
          (x_in * 0.72 + x * 0.28, py, zt),
          (x_in, py, zm),
        ])
      body.loft(shoe_rings, M["shoes"], caps=(True, True))

      # Thick sculpted rubber sole with slight heel drop and toe bumper
      sole_rings = []
      for py, zb, zt, wi, wo in shoe_stations:
        x_in = x - s * (wi + 0.004)
        x_out = x + s * (wo + 0.004)
        z_top_s = zb + 0.006 if py > -0.15 else zb + 0.010
        sole_rings.append([
          (x_in, py, 0.0),
          (x_out, py, 0.0),
          (x_out, py, z_top_s),
          (x_in, py, z_top_s),
        ])
      body.loft(sole_rings, M["sole"], caps=(True, True))

      # Dark heel counter, padded ankle collar, tongue & 3 crisp laces
      body.box((x - 0.045, 0.056, 0.026), (x + 0.045, 0.080, 0.082), M["shoe_accent"])
      body.tube([
        ((x, 0.015, 0.104), 0.048, 0.046),
        ((x, 0.012, 0.120), 0.045, 0.044),
      ], M["shoe_accent"], n=8, side=(1, 0, 0))
      body.box((x - 0.026, -0.055, 0.085), (x + 0.026, -0.015, 0.114), M["shoe_accent"])
      for ly, lz in ((-0.032, 0.095), (-0.058, 0.084), (-0.084, 0.073)):
        body.box((x - 0.024, ly - 0.005, lz - 0.004), (x + 0.024, ly + 0.005, lz + 0.004), M["shoe_lace"])

    # --- SLEEVE, ANATOMICAL ARM & SCULPTED HAND ----------------------------------------------
    tag("chest", "shoulder" + side, "upper_arm" + side)
    sh, el, wr = SHOULDER.copy(), ELBOW.copy(), WRIST.copy()
    kn, tip, th = KNUCKLES.copy(), FINGER_TIP.copy(), THUMB_TIP.copy()
    if s < 0:
      sh.x, el.x, wr.x, kn.x, tip.x, th.x = -sh.x, -el.x, -wr.x, -kn.x, -tip.x, -th.x

    u_dir = (el - sh).normalized()
    # Smoothly integrated sloping shoulder & short sleeve (flows from trapezius, no spiky shoulder pads)
    sh_vis = Vector((s * 0.145 * w, 0.004, 1.372))
    deltoid = Vector((s * 0.192 * w, 0.008, 1.376))
    sleeve_mid = sh.lerp(el, 0.28) + Vector((0.0, 0.0, -0.012))
    sleeve_end = sh.lerp(el, 0.52)
    body.tube([
      (sh_vis, 0.052 * w, 0.056 * w),
      (deltoid, 0.064 * w, 0.064 * w),
      (sleeve_mid, 0.062 * w, 0.060 * w),
      (sleeve_end, 0.059 * w, 0.057 * w),
    ], M["shirt"], n=L_ARM)
    # Sleeve hem cuff + dark inner recess around the bicep
    body.tube([
      (sh.lerp(el, 0.48), 0.061 * w, 0.059 * w),
      (sleeve_end + u_dir * 0.018, 0.061 * w, 0.059 * w),
    ], M["trim"], n=L_ARM)
    if not simple:
      body.tube([
        (sleeve_end + u_dir * 0.017, 0.055 * w, 0.053 * w),
        (sleeve_end - u_dir * 0.015, 0.047 * w, 0.045 * w),
      ], M["shirt_dark"], n=L_ARM)

    # Anatomical upper arm + elbow + forearm (bicep/forearm fullness, tapering to wrist)
    tag("upper_arm" + side, "lower_arm" + side)
    body.tube([
      (sh.lerp(el, 0.36), 0.047 * w, 0.045 * w),
      (sh.lerp(el, 0.68), 0.045 * w, 0.043 * w),  # Bicep
      (el, 0.040 * w, 0.039 * w),                # Elbow
      (el.lerp(wr, 0.28), 0.042 * w, 0.039 * w), # Upper forearm (brachioradialis)
      (el.lerp(wr, 0.66), 0.035 * w, 0.032 * w), # Lower forearm
      (wr, 0.029 * w, 0.025 * w),                # Wrist
    ], M["skin"], n=5 if simple else 8)

    # Subtle wristwatch on Luis's left wrist
    if not simple and s > 0:
      f_dir = (wr - el).normalized()
      w_pos = wr - f_dir * 0.024
      body.tube([
        (w_pos - f_dir * 0.009, 0.033 * w, 0.029 * w),
        (w_pos + f_dir * 0.009, 0.033 * w, 0.029 * w),
      ], M["watch_band"], n=8)
      # Watch case on outer/dorsal wrist
      arm_up = Vector((-f_dir.z, 0.0, f_dir.x)).normalized()
      if arm_up.z < 0:
        arm_up = -arm_up
      wc = w_pos + arm_up * (0.028 * w)
      body.box((wc.x - 0.012, wc.y - 0.013, wc.z - 0.008), (wc.x + 0.012, wc.y + 0.013, wc.z + 0.008), M["watch_case"])
      body.box((wc.x - 0.009, wc.y - 0.010, wc.z + 0.004), (wc.x + 0.009, wc.y + 0.010, wc.z + 0.010), M["watch_face"])

    # Sculpted hand & grouped fingers (matching WRIST / KNUCKLES / FINGER_TIP / THUMB_TIP)
    tag("hand" + side, "fingers" + side, "lower_arm" + side)
    if simple:
      body.tube([(wr, 0.034, 0.016), (kn, 0.042, 0.018), (kn.lerp(tip, 0.6), 0.038, 0.015), (tip, 0.025, 0.01)], M["skin"], n=4, side=(0, 1, 0))
      continue

    h_dir = (kn - wr).normalized()
    # Local hand frame: h_dir along palm, h_front toward thumb (-Y), h_palm inward toward body
    h_front = Vector((0.0, -1.0, 0.0))
    h_palm = h_dir.cross(h_front).normalized()
    if h_palm.x * s > 0:
      h_palm = -h_palm

    # Trapezoidal sculpted palm overlapped cleanly into the wrist (no dark seam)
    body.tube([
      (wr - h_dir * 0.014, 0.027, 0.019),
      (wr, 0.029, 0.019),
      (wr.lerp(kn, 0.45) + h_palm * 0.002, 0.037, 0.019),
      (kn, 0.041, 0.017),
    ], M["skin"], n=6, side=tuple(h_palm))

    # Three sculpted finger groups (index, middle+ring, pinky) with gentle natural curl
    tag("fingers" + side, "hand" + side)
    f_len = (tip - kn).length
    finger_specs = [
      (0.024, 0.94, 0.0105, 0.0085),   # Index finger
      (0.000, 1.04, 0.0155, 0.0090),   # Middle + ring grouped
      (-0.023, 0.82, 0.0095, 0.0075),  # Pinky
    ]
    for f_off, scale_l, r_w, r_t in finger_specs:
      base_p = kn + h_front * f_off
      mid_p = base_p + h_dir * (f_len * 0.55 * scale_l) + h_palm * 0.008
      end_p = base_p + h_dir * (f_len * scale_l) + h_palm * 0.019
      body.tube([
        (base_p, r_w, r_t),
        (mid_p, r_w * 0.90, r_t * 0.88),
        (end_p, r_w * 0.68, r_t * 0.72),
      ], M["skin"], n=5, side=tuple(h_palm))

    # Articulated thumb with fleshy base (thenar eminence)
    tag("thumb" + side, "hand" + side)
    th_base = wr.lerp(kn, 0.34) + h_front * 0.020 + h_palm * 0.008
    th_mid = th_base.lerp(th, 0.52) + h_palm * 0.005
    body.tube([
      (th_base, 0.014, 0.012),
      (th_mid, 0.011, 0.010),
      (th, 0.0085, 0.0080),
    ], M["skin"], n=5)

  parts = [(body, tag)]

  # --- 6. DETAILED CANVAS BACKPACK (separate object for hiding inside the car) ---------------
  if look.get("backpack"):
    pack = Shape()
    ptag = Tags(pack)
    ptag("chest", "spine")

    if simple:
      p = [ring(z, a, f, b, y=0.188, n=8, power=4) for z, a, f, b in ((1.02, 0.14, 0.06, 0.07), (1.12, 0.155, 0.07, 0.085), (1.3, 0.155, 0.07, 0.085), (1.4, 0.14, 0.06, 0.075))]
      pack.loft(p, M["pack"])
      pack.tube([((-0.15, 0.188, 1.43), 0.05, 0.05), ((0.15, 0.188, 1.43), 0.05, 0.05)], M["pack"], n=8, side=(0, 0, 1))
      pack.box((-0.11, 0.268, 1.06), (0.11, 0.305, 1.24), M["strap"])
    else:
      # Main rucksack body: fuller at the bottom, softly rounded canvas bag
      bag_stations = [
        (0.995, 0.132, 0.052, 0.065, 0.186),
        (1.065, 0.158, 0.068, 0.090, 0.194),
        (1.185, 0.160, 0.072, 0.094, 0.196),
        (1.310, 0.150, 0.066, 0.086, 0.192),
        (1.392, 0.132, 0.055, 0.072, 0.186),
        (1.416, 0.085, 0.036, 0.044, 0.184),
      ]
      pack.loft([ring(z, a, f, b, y=yc, n=12, power=3.2) for z, a, f, b, yc in bag_stations], M["pack"], caps=(True, True))

      # Curved top flap lid over the rucksack
      flap_stations = [
        (1.295, 0.154, 0.050, 0.102, 0.196),
        (1.355, 0.156, 0.064, 0.098, 0.195),
        (1.408, 0.142, 0.062, 0.082, 0.190),
        (1.428, 0.112, 0.046, 0.056, 0.185),
      ]
      pack.loft([ring(z, a, f, b, y=yc, n=12, power=3.4) for z, a, f, b, yc in flap_stations], M["strap"], caps=(True, True))

      # Rolled tarp / bedroll strapped across top of the backpack
      pack.tube([
        ((-0.158, 0.186, 1.448), 0.038, 0.038),
        ((-0.140, 0.186, 1.452), 0.044, 0.044),
        ((0.0, 0.186, 1.454), 0.045, 0.045),
        ((0.140, 0.186, 1.452), 0.044, 0.044),
        ((0.158, 0.186, 1.448), 0.038, 0.038),
      ], M["pack_roll"], n=10, side=(0, 0, 1))
      # Two dark cinch straps tying the bedroll & securing the front flap with brass buckles
      for sx in (-0.085, 0.085):
        pack.tube([
          ((sx, 0.186, 1.452), 0.049, 0.049),
          ((sx + (0.016 if sx < 0 else -0.016), 0.186, 1.452), 0.049, 0.049),
        ], M["pack_dark"], n=10, side=(0, 0, 1))
        pack.box((sx - 0.012, 0.280, 1.215), (sx + 0.012, 0.302, 1.375), M["pack_dark"])
        pack.box((sx - 0.015, 0.292, 1.242), (sx + 0.015, 0.308, 1.266), M["buckle"])

      # Front zippered/flapped pouch
      pack.box((-0.106, 0.268, 1.035), (0.106, 0.312, 1.205), M["strap"])
      pack.box((-0.112, 0.272, 1.192), (0.112, 0.318, 1.224), M["pack_dark"])

      # Two small side utility pouches
      for s in (-1, 1):
        px0, px1 = sorted((s * 0.152, s * 0.184))
        pack.box((px0, 0.148, 1.045), (px1, 0.236, 1.185), M["strap"])
        pack.box((px0, 0.145, 1.174), (px1 + s * 0.004, 0.239, 1.198), M["pack_dark"])

      # Bottom leather reinforcement pad
      pack.box((-0.125, 0.140, 0.985), (0.125, 0.245, 1.010), M["pack_dark"])

    # Ergonomic shoulder straps arching smoothly over the trapezius and chest without clipping
    for s in (-1, 1):
      ptag("chest", "spine")
      strap_pts = [
        ((s * 0.105 * w, 0.132 * w, 1.398), 0.023, 0.008),
        ((s * 0.110 * w, 0.068 * w, 1.436), 0.024, 0.008),
        ((s * 0.114 * w, 0.002 * w, 1.442), 0.024, 0.008),
        ((s * 0.118 * w, -0.056 * w, 1.422), 0.024, 0.008),
        (shirt_point(1.345, s * 0.70, w=w, grow=0.017, folds=False), 0.024, 0.008),
        (shirt_point(1.235, s * 0.74, w=w, grow=0.016, folds=False), 0.022, 0.007),
        (shirt_point(1.120, s * 0.96, w=w, grow=0.015, folds=False), 0.019, 0.006),
        (shirt_point(1.045, s * 1.52, w=w, grow=0.015, folds=False), 0.017, 0.006),
        ((s * 0.135, 0.160, 1.035), 0.016, 0.006),
      ]
      pack.tube(strap_pts, M["strap"], n=6 if not simple else 4)
      if not simple:
        # Small chest adjustment buckle seated cleanly on the front strap
        bp = Vector(shirt_point(1.195, s * 0.80, w=w, grow=0.020, folds=False))
        pack.box((bp.x - 0.013, bp.y - 0.008, bp.z - 0.011), (bp.x + 0.013, bp.y + 0.008, bp.z + 0.011), M["buckle"])

    parts.append((pack, ptag))
  return parts


def rig_person(name, parts):
  """Joins the parts into one object each and rigs them to one armature."""
  table = bones()
  armature = None
  objects = []
  for i, (shape, tag) in enumerate(parts):
    obj = shape.finish(name if i == 0 else f"{name}_backpack")
    if armature is None:
      armature = rig(obj, name, table, tag.ranges())
    else:
      armature_data = armature
      groups = {}
      from beast_tools import distance_to
      segments = {bone: (Vector(h), Vector(t)) for bone, (h, t, _) in table.items()}
      for start, end, bone_names in tag.ranges():
        for bone in bone_names:
          if bone not in groups:
            groups[bone] = obj.vertex_groups.get(bone) or obj.vertex_groups.new(name=bone)
        for v in range(start, end):
          co = obj.data.vertices[v].co
          near = sorted((distance_to(co, *segments[b]), b) for b in bone_names)[:2]
          weights = [1.0 / (d + 0.005) ** 4 for d, _ in near]
          for weight, (_, bone) in zip(weights, near):
            groups[bone].add([v], weight / sum(weights), "REPLACE")
      obj.parent = armature_data
      obj.modifiers.new("armature", "ARMATURE").object = armature_data
    objects.append(obj)
  return armature, objects


# --- Poses -----------------------------------------------------------------------------------
FOLD = 1.0  # Sign of a finger curl around the hand bone's X axis.


class PersonRig(Rig):
  """Forward kinematics for the torso and head, two-bone IK for any limb given a target.

  Rotations are (pitch, yaw, roll) in degrees on top of the parent's. Targets are (x, forward, z)
  from the root: wrist_l / wrist_r with pole_l / pole_r, ankle_l / ankle_r with knee_l / knee_r.
  A limb without a target follows its own rotations instead."""

  def solve(self, pose):
    self.world.clear()
    self.local.clear()
    turned = {}
    self.place("root", Quaternion(), Vector((0, 0, 0)))
    turned["root"] = Quaternion()
    hips_at = self.head["hips"] + at(*pose.get("hips_pos", (0, 0, 0)))
    order = ["hips", "spine", "chest", "neck", "head"]
    for name in order:
      parent = self.parent[name]
      turned[name] = turned[parent] @ rot(*pose.get(name, (0, 0, 0)))
      self.place(name, turned[name], hips_at if name == "hips" else None)

    for side in ("_l", "_r"):
      sign = 1 if side == "_l" else -1
      shoulder = "shoulder" + side
      turned[shoulder] = turned["chest"] @ rot(*pose.get(shoulder, (0, 0, 0)))
      self.place(shoulder, turned[shoulder])
      wrist = pose.get("wrist" + side)
      if wrist is not None:
        pole = at(*pose.get("pole" + side, (sign * 0.6, -0.3, -0.5))).normalized()
        self.limb("upper_arm" + side, "lower_arm" + side, at(*wrist), pole, -FORWARD)
        lower = self.world["lower_arm" + side].to_quaternion() @ self.rest["lower_arm" + side].to_quaternion().inverted()
      else:
        upper = turned[shoulder] @ rot(*pose.get("upper_arm" + side, (0, 0, 0)))
        self.place("upper_arm" + side, upper)
        lower = upper @ rot(*pose.get("lower_arm" + side, (0, 0, 0)))
        self.place("lower_arm" + side, lower)
      hand = lower @ rot(*pose.get("hand" + side, (0, 0, 0)))
      self.place("hand" + side, hand)
      # Fingers fold around the hand bone's own X axis, toward the palm.
      curl = math.radians(pose.get("curl" + side, 20.0))
      fold_axis = self.world["hand" + side].to_3x3().col[0].normalized()
      self.place("fingers" + side, Quaternion(fold_axis, curl * FOLD) @ hand)
      self.place("thumb" + side, Quaternion(fold_axis, curl * FOLD * 0.4) @ hand)

      ankle = pose.get("ankle" + side)
      if ankle is not None:
        knee = at(*pose.get("knee" + side, (sign * 0.1, 1.0, 0.2))).normalized()
        self.limb("upper_leg" + side, "lower_leg" + side, at(*ankle), knee, FORWARD)
        foot = rot(*pose.get("foot" + side, (0, 0, 0)))
      else:
        upper = turned["hips"] @ rot(*pose.get("upper_leg" + side, (0, 0, 0)))
        self.place("upper_leg" + side, upper)
        lower = upper @ rot(*pose.get("lower_leg" + side, (0, 0, 0)))
        self.place("lower_leg" + side, lower)
        foot = lower @ rot(*pose.get("foot" + side, (0, 0, 0)))
      self.place("foot" + side, foot)
      self.place("toes" + side, foot @ rot(*pose.get("toes" + side, (0, 0, 0))))

    # Any other bone (the protagonist's jacket and hair chains, the weapon) rides on its parent,
    # with its own rotation if the pose names it.
    for name in self.rest:
      if name in self.local or self.parent[name] is None:
        continue
      parent = self.parent[name]
      carried = self.world[parent].to_quaternion() @ self.rest[parent].to_quaternion().inverted()
      self.place(name, carried @ rot(*pose.get(name, (0, 0, 0))))


def merged(*poses):
  result = {}
  for pose in poses:
    result.update(pose)
  return result


# Seated at the wheel. The root is the car floor under the seat, so the car scene places him with
# the root on its own floor. The wheel's center is 0.6 ahead and 0.98 up.
SEAT = {
  "hips_pos": (0, 0.06, -0.34),
  "hips": (-12, 0, 0),
  "spine": (4, 0, 0),
  "chest": (4, 0, 0),
  "neck": (2, 0, 0),
  "head": (6, 0, 0),
  "ankle_l": (0.15, 0.7, 0.3),
  "ankle_r": (-0.13, 0.72, 0.3),
  "knee_l": (0.2, 1, 0.8),
  "knee_r": (-0.2, 1, 0.8),
  "foot_l": (-10, 4, 0),
  "foot_r": (-14, -4, 0),
}
WHEEL_L = (0.16, 0.5, 1.03)
WHEEL_R = (-0.17, 0.5, 1.03)
DRIVE = merged(SEAT, {
  "wrist_l": WHEEL_L, "wrist_r": WHEEL_R,
  "pole_l": (0.45, 0.0, -0.9), "pole_r": (-0.45, 0.0, -0.9),
  "hand_l": (0, 0, 50), "hand_r": (0, 0, -50),
  "curl_l": 70.0, "curl_r": 70.0,
})


def drive_clip():
  """Loop (the last key wraps to the first): small corrections at the wheel and a look in the mirror."""
  return Clip("drive-loop", 180, timeline(
    (0, DRIVE),
    (40, {"head": (6, -4, 0), "wrist_l": (0.165, 0.5, 1.045), "wrist_r": (-0.165, 0.5, 1.015)}),
    (85, {"head": (4, 12, 2)}),
    (110, {"head": (5, 10, 1)}),
    (140, {"head": (6, 0, 0), "wrist_l": (0.155, 0.5, 1.02), "wrist_r": (-0.175, 0.5, 1.04)}),
  ), loop=True)


TALK = {"head": (4, -14, -2), "neck": (2, -8, 0)}


def talk_clip():
  """Loop: talking to the passenger, the right hand off the wheel to make the point."""
  open_hand = {"wrist_r": (-0.12, 0.42, 1.12), "pole_r": (-0.9, 0.1, -0.4), "hand_r": (-30, 0, -80), "curl_r": 15.0}
  return Clip("talk-loop", 150, timeline(
    (0, merged(DRIVE, TALK)),
    (20, open_hand),
    (45, {"wrist_r": (-0.1, 0.45, 1.08), "hand_r": (-10, 0, -70)}),
    (70, {"wrist_r": (-0.13, 0.42, 1.14), "head": (2, -10, -2)}),
    (95, {"wrist_r": (-0.1, 0.45, 1.09), "head": (5, -16, -1)}),
    (125, {"wrist_r": WHEEL_R, "hand_r": (0, 0, -50), "curl_r": 70.0, "pole_r": (-0.45, 0.0, -0.9)}),
  ), loop=True)


def laugh_clip():
  """A tired laugh: the head goes back and the shoulders shake twice."""
  return Clip("laugh", 54, timeline(
    (0, DRIVE),
    (10, {"chest": (-4, 0, 0), "head": (-14, -6, 0), "shoulder_l": (0, 0, 6), "shoulder_r": (0, 0, -6)}),
    (18, {"chest": (2, 0, 0), "head": (-6, -6, 0), "shoulder_l": (0, 0, 0), "shoulder_r": (0, 0, 0)}),
    (26, {"chest": (-3, 0, 0), "head": (-12, -8, 0), "shoulder_l": (0, 0, 5), "shoulder_r": (0, 0, -5)}),
    (36, {"chest": (3, 0, 0), "head": (8, -4, 0), "shoulder_l": (0, 0, 0), "shoulder_r": (0, 0, 0)}),
    (54, merged(DRIVE, TALK)),
  ))


# The car's center line is 0.38 to his right (-x): the radio and the gap between the seats.
POINTING = {"wrist_r": (-0.34, -0.36, 0.98), "pole_r": (-0.4, 0.5, -0.7), "hand_r": (10, 0, -20), "curl_r": 35.0,
            "chest": (2, -16, -2), "neck": (2, -14, 0), "head": (6, -40, 0),
            "wrist_l": (0.1, 0.5, 1.08)}


def point_back_clip():
  """Reaches back between the seats, at the machete on the back seat. Ends holding it."""
  return Clip("point_back", 30, timeline(
    (0, DRIVE),
    (10, {"wrist_r": (-0.3, 0.2, 1.05), "hand_r": (0, 0, -40), "curl_r": 40.0, "chest": (3, -8, 0), "head": (6, -20, 0)}),
    (22, POINTING),
    (30, merged(POINTING, {"wrist_r": (-0.35, -0.38, 0.97)})),
  ))


def let_go_clip():
  """From point_back back to the wheel."""
  return Clip("let_go", 24, timeline(
    (0, merged(DRIVE, POINTING, {"wrist_r": (-0.35, -0.38, 0.97)})),
    (12, {"wrist_r": (-0.28, 0.25, 1.05), "chest": (3, -4, 0), "head": (5, -8, 0), "neck": (2, -4, 0)}),
    (24, DRIVE),
  ))


def hit_radio_clip():
  """Two flat slaps on the radio, the eyes leaving the road for it."""
  radio = (-0.34, 0.5, 0.9)
  up = (-0.3, 0.44, 1.0)
  slap = {"pole_r": (-0.7, 0.2, -0.7), "hand_r": (-60, 0, -10), "curl_r": 10.0}
  return Clip("hit_radio", 45, timeline(
    (0, DRIVE),
    (8, merged(slap, {"wrist_r": up, "head": (12, -18, 0), "neck": (6, -6, 0), "chest": (12, -8, 0), "spine": (6, 0, 0)})),
    (13, {"wrist_r": radio}),
    (19, {"wrist_r": up}),
    (24, {"wrist_r": radio}),
    (33, {"wrist_r": up, "head": (10, -10, 0), "chest": (6, -4, 0), "spine": (4, 0, 0)}),
    (45, DRIVE),
  ))


def swerve_clip():
  """The wheel yanked hard left, arms locked, the body thrown against the door."""
  return Clip("swerve", 24, timeline(
    (0, DRIVE),
    (5, {"wrist_l": (0.05, 0.52, 1.17), "wrist_r": (-0.22, 0.5, 0.92), "head": (2, 0, 0), "chest": (6, 0, 0)}),
    (12, {"wrist_l": (-0.02, 0.5, 1.2), "wrist_r": (-0.19, 0.47, 0.88), "chest": (6, 4, -10), "head": (0, 6, -16), "hips": (-12, 0, -4)}),
    (24, {"chest": (8, 6, -14), "head": (2, 10, -20)}),
  ))


# Face down on the asphalt by the car, the head turned to the right and an arm reaching out.
LYING = {
  "hips_pos": (0, 0.0, -0.7),
  "hips": (88, 0, 4),
  "spine": (2, 0, 0),
  "chest": (-2, 2, 0),
  "neck": (-10, -20, 0),
  "head": (-12, -50, -14),
  "upper_arm_l": (-24, 10, 24),
  "lower_arm_l": (0, 0, -20),
  "hand_l": (0, 0, 0),
  "upper_arm_r": (-155, 0, -10),
  "lower_arm_r": (0, 0, 20),
  "hand_r": (10, 0, 0),
  "curl_r": 40.0,
  "upper_leg_l": (2, 0, 10),
  "lower_leg_l": (25, 0, 0),
  "foot_l": (-20, 0, 0),
  "upper_leg_r": (4, 0, -6),
  "lower_leg_r": (12, 0, 0),
  "foot_r": (-20, 0, 0),
}


def lying_clip():
  """Loop: hardly breathing."""
  return Clip("lying-loop", 120, timeline(
    (0, LYING),
    (60, {"chest": (-4, 2, 0), "hips_pos": (0, 0.0, -0.695)}),
  ), loop=True)


def reach_clip():
  """The right hand drags itself toward the protagonist, and stops."""
  return Clip("reach", 120, timeline(
    (0, LYING),
    (30, {"upper_arm_r": (-155, 0, -10), "curl_r": 60.0}),
    (70, {"upper_arm_r": (-158, 0, -26), "lower_arm_r": (0, 0, 10), "head": (-14, -56, -14), "curl_r": 30.0}),
    (110, {"upper_arm_r": (-162, 0, -34), "lower_arm_r": (0, 0, 4), "curl_r": 50.0}),
    (120, {"upper_arm_r": (-162, 0, -34), "lower_arm_r": (0, 0, 4), "curl_r": 50.0}),
  ))


CLIPS = [drive_clip, talk_clip, laugh_clip, point_back_clip, let_go_clip, hit_radio_clip, swerve_clip, lying_clip, reach_clip]


# The protagonist in the passenger seat. animate_protagonist.py bakes these on its own armature,
# which has the same bone names; the seat is the mirror of the driver's.
PASSENGER = merged(SEAT, {
  "hips": (-14, 0, 0),
  "head": (4, 0, 0),
  "ankle_l": (0.16, 0.66, 0.3),
  "ankle_r": (-0.15, 0.68, 0.3),
  "wrist_l": (0.15, 0.3, 0.68), "wrist_r": (-0.14, 0.28, 0.68),
  "pole_l": (0.6, 0.0, -0.8), "pole_r": (-0.6, 0.0, -0.8),
  "hand_l": (-20, 0, 0), "hand_r": (-20, 0, 0),
  "curl_l": 30.0, "curl_r": 30.0,
  # The long jacket: folded up the seat back behind him, over his thighs in front.
  "jacket_back_1_l": (85, 0, 0), "jacket_back_1_r": (85, 0, 0),
  "jacket_back_2_l": (80, 0, 0), "jacket_back_2_r": (80, 0, 0),
  "jacket_back_3_l": (10, 0, 0), "jacket_back_3_r": (10, 0, 0),
  "jacket_side_1_l": (60, 0, 25), "jacket_side_1_r": (60, 0, -25),
  "jacket_side_2_l": (30, 0, 0), "jacket_side_2_r": (30, 0, 0),
  "jacket_front_2_l": (-60, 0, 0), "jacket_front_2_r": (-60, 0, 0),
  "jacket_front_3_l": (-20, 0, 0), "jacket_front_3_r": (-20, 0, 0),
})


def sit_clip():
  """Loop: riding along, a slow breath and the head drifting with the road."""
  return Clip("sit-loop", 240, timeline(
    (0, PASSENGER),
    (80, {"head": (6, 6, 0), "chest": (5, 0, 0)}),
    (160, {"head": (3, -4, 0), "chest": (4, 0, 0)}),
  ), loop=True)


def sit_window_clip():
  """Turns to the window on the right and stays there."""
  looking = {"head": (2, -55, 0), "neck": (2, -15, 0), "chest": (4, -8, 0)}
  return Clip("sit_window", 24, timeline(
    (0, PASSENGER),
    (18, looking),
    (24, looking),
  ))


def sit_back_clip():
  """From the window back to the road."""
  looking = {"head": (2, -55, 0), "neck": (2, -15, 0), "chest": (4, -8, 0)}
  return Clip("sit_back", 24, timeline(
    (0, merged(PASSENGER, looking)),
    (24, PASSENGER),
  ))


def brace_clip():
  """Thrown sideways as the car spins, a hand against the dash."""
  return Clip("brace", 24, timeline(
    (0, PASSENGER),
    (8, {"wrist_r": (-0.1, 0.5, 0.95), "pole_r": (-0.6, 0.2, -0.7), "hand_r": (-70, 0, 0), "curl_r": 10.0, "head": (0, 10, 0)}),
    (16, {"chest": (6, 10, 14), "head": (0, 20, 18), "hips": (-14, 0, 6)}),
    (24, {"chest": (8, 12, 18), "head": (2, 24, 22)}),
  ))


PASSENGER_CLIPS = [sit_clip, sit_window_clip, sit_back_clip, brace_clip]


# --- Build ----------------------------------------------------------------------------------
def clear():
  if bpy.app.background:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return
  for collection in (bpy.data.objects, bpy.data.meshes, bpy.data.armatures, bpy.data.materials, bpy.data.actions):
    for item in list(collection):
      collection.remove(item)


def export(armature, objects):
  for other in bpy.data.objects:
    other.hide_set(other not in (armature, *objects))
  armature.animation_data.action = None
  for bone in armature.pose.bones:
    bone.matrix_basis.identity()
  os.makedirs(os.path.dirname(GLB_PATH), exist_ok=True)
  bpy.ops.export_scene.gltf(filepath=GLB_PATH, export_format="GLB", use_visible=True, export_animations=True,
                            export_animation_mode="ACTIONS", export_force_sampling=True, export_frame_step=1)
  for other in bpy.data.objects:
    other.hide_set(False)


def main(clips=True):
  clear()
  bpy.context.scene.render.fps = 60
  armature, objects = rig_person("luis", build_person(LUIS, "luis"))
  if clips:
    armature.animation_data_create()
    person = PersonRig(armature)
    for clip in CLIPS:
      bake(armature, person, clip(), moved=("root", "hips"))
    export(armature, objects)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
  return armature, objects


if __name__ == "__main__":
  main()
