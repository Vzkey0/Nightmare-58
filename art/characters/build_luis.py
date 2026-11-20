# Builds Luis, the friend who drives the protagonist in the opening, rigged and with his clips.
# A slim bearded man in an olive t-shirt, khaki cargo pants and a canvas backpack. Faceted like
# the rest of the world. Faces -Y with feet on the origin; bones share the protagonist's names.
#   blender --background --python art/characters/build_luis.py
# build_person() is also what build_drive.py dresses the street's people with.
import math
import os
import sys

import bpy
from mathutils import Quaternion, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "props"))

from animate_protagonist import FORWARD, UP, Clip, Rig, at, bake, rot, timeline
from beast_tools import Tags, mirrored, rig
from prop_tools import Shape, material

BLEND_PATH = os.path.join(HERE, "luis.blend")
GLB_PATH = os.path.join(HERE, "..", "..", "game", "models", "characters", "luis.glb")

LUIS = {
  "skin": (0.84, 0.68, 0.54),
  "hair": (0.22, 0.14, 0.09),
  "shirt": (0.33, 0.37, 0.22),
  "trim": (0.22, 0.25, 0.15),
  "pants": (0.56, 0.48, 0.31),
  "pants_dark": (0.44, 0.37, 0.23),
  "shoes": (0.27, 0.29, 0.32),
  "sole": (0.15, 0.15, 0.16),
  "pack": (0.62, 0.52, 0.34),
  "strap": (0.43, 0.35, 0.22),
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


# --- Mesh helpers ----------------------------------------------------------------------------
def ring(z, a, front, back, y=0.0, n=10, power=2.6, x=0.0):
  """A rounded-box section: half width a, depth front and back. Angle 0 faces the camera (-Y)."""
  points = []
  for k in range(n):
    phi = math.tau * (k + 0.5) / n
    s, c = math.sin(phi), math.cos(phi)
    px = a * math.copysign(abs(s) ** (2 / power), s)
    depth = front if c > 0 else back
    py = -depth * math.copysign(abs(c) ** (2 / power), c)
    points.append((x + px, y + py, z))
  return points


def mirror_x(points):
  return [(-x, y, z) for x, y, z in points]


def flip_path(path):
  return [((-p[0], p[1], p[2]), ru, rv) for p, ru, rv in path]


def shell(shape, rows, thickness, mat):
  """A curved plate from open rows of points: the outer face, an inner face pushed toward the
  head center and the rim, so it stays a closed solid and its normals point the right way."""
  center = Vector((0, 0.0, 1.64))
  inner = [[tuple(Vector(p) + (center - Vector(p)).normalized() * thickness) for p in row] for row in rows]
  cols = len(rows[0])
  verts = [p for row in rows for p in row] + [p for row in inner for p in row]
  base = len(rows) * cols
  faces = []
  for r in range(len(rows) - 1):
    for c in range(cols - 1):
      a, b = r * cols + c, r * cols + c + 1
      faces.append((a, b, b + cols, a + cols))
      faces.append((base + a + cols, base + b + cols, base + b, base + a))
  for r in range(len(rows) - 1):
    for c in (0, cols - 1):
      a, b = r * cols + c, (r + 1) * cols + c
      faces.append((a, b, base + b, base + a) if c else (b, a, base + a, base + b))
  for r in (0, len(rows) - 1):
    for c in range(cols - 1):
      a, b = r * cols + c, r * cols + c + 1
      faces.append((b, a, base + a, base + b) if r == 0 else (a, b, base + b, base + a))
  shape.add(verts, faces, mat)


HEAD = [
  # z, half width, front, back, center y
  (1.5, 0.05, 0.055, 0.05, 0.01),
  (1.528, 0.06, 0.083, 0.055, 0.0),
  (1.565, 0.083, 0.098, 0.075, 0.0),
  (1.605, 0.092, 0.104, 0.09, 0.0),
  (1.645, 0.097, 0.104, 0.1, 0.0),
  (1.69, 0.096, 0.1, 0.106, 0.002),
  (1.73, 0.089, 0.088, 0.104, 0.004),
  (1.762, 0.068, 0.06, 0.08, 0.006),
  (1.778, 0.03, 0.025, 0.035, 0.006),
]


def head_point(z, phi, grow=0.0):
  """A point on the head surface at height z and angle phi (0 is the face, + toward the left)."""
  for (z0, a0, f0, b0, y0), (z1, a1, f1, b1, y1) in zip(HEAD, HEAD[1:]):
    if z <= z1:
      t = max(0.0, min(1.0, (z - z0) / (z1 - z0)))
      break
  a, f, b, y = (u + (v - u) * t for u, v in zip((a0, f0, b0, y0), (a1, f1, b1, y1)))
  s, c = math.sin(phi), math.cos(phi)
  px = (a + grow) * math.copysign(abs(s) ** (2 / 2.6), s)
  depth = (f if c > 0 else b) + grow
  py = -depth * math.copysign(abs(c) ** (2 / 2.6), c)
  return (px, y + py, z)


def hairline(phi):
  """Where the hair starts, from the forehead (phi 0) round to the nape (pi)."""
  side = abs(math.atan2(math.sin(phi), math.cos(phi))) / math.pi
  nape = math.sin(math.pi / 2 * min(1.0, max(0.0, (side - 0.5) / 0.3)))  # Squared off at the back.
  return 1.74 - 0.075 * min(1.0, side / 0.45) ** 1.5 - 0.085 * nape


def beardline(phi):
  side = abs(math.atan2(math.sin(phi), math.cos(phi))) / math.pi
  return 1.622 + 0.045 * min(1.0, side / 0.55)


# --- The body --------------------------------------------------------------------------------
def build_person(look, name):
  """One mesh for the body and, if worn, one for the backpack, both tagged for rigging."""
  M = {key: material(f"{name}_{key}", value) for key, value in look.items() if isinstance(value, tuple)}
  M["eye"] = material(f"{name}_eye", (0.06, 0.045, 0.04), roughness=0.4)
  M["lip"] = material(f"{name}_lip", (0.2, 0.1, 0.08))
  M["stubble"] = material(f"{name}_stubble", tuple(s * 0.6 + h * 0.4 for s, h in zip(look["skin"], look["hair"])))
  M["eye_white"] = material(f"{name}_eye_white", (0.84, 0.8, 0.74), roughness=0.5)
  M["lid"] = material(f"{name}_lid", tuple(c * 0.72 for c in look["skin"]))
  w = look.get("build", 1.0)
  # Background people: no face, fingers or beard, and fewer sides, about a third of Luis.
  simple = look.get("simple", False)
  R = 8 if simple else 12
  L = 5 if simple else 8
  body = Shape()
  tag = Tags(body)

  # Head: skin, then beard and hair as plates over it.
  tag("head")
  body.loft([ring(z, a, f, b, y, n=R) for z, a, f, b, y in (HEAD[1::2] + HEAD[-1:] if simple else HEAD)], M["skin"], caps=(True, True))
  # Nose: a bridge from between the brows down to a rounded tip, with wings at the base.
  nose = [(0, -0.101, 1.686), (-0.01, -0.106, 1.664), (0.01, -0.106, 1.664), (0, -0.136, 1.634), (-0.023, -0.109, 1.627),
          (0.023, -0.109, 1.627), (0, -0.119, 1.617), (-0.02, -0.101, 1.648), (0.02, -0.101, 1.648), (-0.012, -0.124, 1.622), (0.012, -0.124, 1.622)]
  body.add(nose, [(0, 1, 3), (0, 3, 2), (1, 7, 4), (1, 4, 9, 3), (2, 3, 10, 5), (2, 5, 8), (3, 9, 6), (3, 6, 10), (9, 4, 6), (10, 6, 5)], M["skin"])
  for side in () if simple else (-1, 1):
    def on_face(dphi, z, grow):
      return head_point(z, side * (0.36 + dphi), grow)
    # Eye: an almond of white on the skin, a dark iris looking a touch inward, and a heavy upper lid.
    almond = [(-0.12, 0.0), (-0.06, 0.0055), (0.04, 0.006), (0.12, 0.001), (0.05, -0.0045), (-0.05, -0.0045)]
    white = [on_face(dp, 1.671 + dz, 0.001) for dp, dz in almond]
    body.add(white, [(0, 1, 2, 3, 4, 5)], M["eye_white"])
    body.add([on_face(dp * 0.55 - 0.02, 1.6712 + dz * 1.0, 0.0025) for dp, dz in almond], [(0, 1, 2, 3, 4, 5)], M["eye"])
    lid_low = [on_face(dp, 1.671 + dz + 0.0005, 0.002) for dp, dz in almond[:4]]
    lid_high = [on_face(dp * 1.05, 1.671 + dz + 0.0045, 0.0045) for dp, dz in almond[:4]]
    shell(body, [lid_low, lid_high], 0.003, M["lid"])
    # Brow: thick at the inner end, thinning and dropping toward the temple.
    brow = [(-0.2, 1.689, 1.700), (-0.05, 1.692, 1.703), (0.1, 1.693, 1.701), (0.24, 1.688, 1.694)]
    shell(body, [[on_face(dp, lo, 0.004) for dp, lo, hi in brow], [on_face(dp, hi, 0.007) for dp, lo, hi in brow]], 0.006, M["hair"])
    ear = [(side * 0.094, 0.01, 1.625), (side * 0.112, 0.02, 1.64), (side * 0.11, 0.025, 1.685), (side * 0.094, 0.0, 1.69)]
    ear_in = [(side * 0.088, p[1], p[2]) for p in ear]
    body.add(ear + ear_in, [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)], M["skin"])

  if look.get("beard") and not simple:
    # From under the jaw up to the cheeks, ear to ear; fuller on the chin.
    angles = [math.radians(a) for a in range(-100, 101, 20)]
    rows = []
    for k in range(6):
      t = k / 5
      row = []
      for phi in angles:
        side = abs(phi) / math.radians(100)
        bottom = 1.522 + 0.07 * side ** 2
        top = beardline(phi)
        z = bottom + (top - bottom) * t
        bulk = 0.004 + (0.012 * math.cos(phi) + 0.004) * math.sin(math.pi * min(1.0, 0.25 + t)) * (1 - 0.6 * side)
        row.append(head_point(z, phi, bulk if k else -0.004))
      rows.append(row)
    shell(body, rows, 0.016, M["hair"])
    # Moustache over a dark line of mouth.
    mo = [head_point(1.627, math.radians(a), 0.01) for a in (-34, -17, 0, 17, 34)]
    lo = [head_point(1.611, math.radians(a), 0.014) for a in (-40, -20, 0, 20, 40)]
    shell(body, [lo, mo], 0.01, M["hair"])
    mouth = [head_point(1.6, math.radians(a), 0.012) for a in (-16, 0, 16)]
    mouth_low = [head_point(1.594, math.radians(a), 0.012) for a in (-14, 0, 14)]
    shell(body, [mouth_low, mouth], 0.006, M["lip"])

  style = look.get("hairstyle")
  if style:
    # swept: Luis, volume combed up and back. short: close to the skull. long: swept, falling to
    # the shoulders behind. cap: short, under a baseball cap.
    volume = 0.0 if style in ("short", "cap") else 1.0
    angles = [math.radians(a) for a in range(-180, 181, 40 if simple else 20)]
    rows = []
    steps = 3 if simple else 6
    for k in range(steps + 1):
      t = k / steps
      row = []
      for phi in angles:
        low = hairline(phi)
        z = low + (1.783 - low) * t
        front = max(0.0, math.cos(phi))
        back = max(0.0, -math.cos(phi))
        grow = 0.005 + volume * (0.02 * t ** 1.3 * (0.35 + 0.65 * front) + (0.006 + 0.008 * back) * math.sin(math.pi * t))
        lift = volume * 0.028 * front ** 2 * math.sin(math.pi * min(1.0, t * 1.15))
        p = Vector(head_point(min(z, 1.778), phi, grow))
        p.z += lift
        row.append(tuple(p))
      rows.append(row)
    top = 1.808 if volume else 1.79
    rows[-1] = [tuple(Vector((0, 0.015, top)).lerp(Vector(p), 0.4)) for p in rows[-1]]
    shell(body, rows, 0.02, M["hair"])
    if not simple:
      # A faded nape: stubble from the hairline down to the neck, round the back only.
      back = [math.radians(a) for a in range(110, 251, 14)]
      fade = [[head_point(hairline(phi) + 0.004, phi, 0.003) for phi in back],
              [head_point(1.535, phi, 0.002) for phi in back]]
      shell(body, fade, 0.002, M["stubble"])
    if style == "long":
      back = [math.radians(a) for a in range(95, 266, 17)]
      fall = []
      for k, z in enumerate((1.7, 1.6, 1.5, 1.42, 1.36)):
        row = []
        for phi in back:
          p = Vector(head_point(max(z, 1.52), phi, 0.022 + 0.012 * k))
          p.z = z
          if z < 1.52:
            p.y += 0.03 * (1.52 - z) / 0.16
          row.append(tuple(p))
        fall.append(row)
      shell(body, fall, 0.025, M["hair"])
    if style == "cap":
      crown = [(head_point(1.72, phi, 0.016)) for phi in [math.tau * k / 12 for k in range(12)]]
      dome = [[(x, y, z) for x, y, z in crown], [tuple(Vector((0, 0.005, 1.8)).lerp(Vector(p), 0.75) + Vector((0, 0, 0.055))) for p in crown]]
      body.loft(dome, M["cap"])
      body.box((-0.085, -0.2, 1.71), (0.085, -0.09, 1.725), M["cap"])

  tag("neck", "head", "chest")
  body.tube([((0, 0.016, 1.43), 0.072, 0.06), ((0, 0.014, 1.47), 0.06, 0.054), ((0, 0.012, 1.5), 0.053, 0.051), ((0, 0.01, 1.55), 0.05, 0.05)], M["skin"], n=8)

  # Shirt: hem over the hips up to the shoulders, a V collar in the darker trim.
  tag("hips", "spine", "chest")
  shirt = [
    (0.83, 0.19, 0.13, 0.125, 0.0),
    (0.92, 0.178, 0.12, 0.118, 0.0),
    (1.02, 0.168, 0.112, 0.11, 0.0),
    (1.14, 0.178, 0.125, 0.112, -0.005),
    (1.26, 0.198, 0.132, 0.115, -0.01),
    (1.36, 0.205, 0.122, 0.112, -0.004),
    (1.43, 0.175, 0.1, 0.1, 0.0),
    (1.465, 0.09, 0.075, 0.07, 0.008),
  ]
  rings = [ring(z, a * w, f * w, b * w, y, n=R) for z, a, f, b, y in shirt]

  def shirt_mat(band, side):
    front = side in (0, 11)
    if band >= 6 and (front or not simple):
      return M["trim"]
    return M["shirt"]
  body.loft(rings, shirt_mat, caps=(False, True))
  def on_shirt(z, k, n=24, out=1.03):
    """Point k of n around the shirt at height z, pushed a touch off the cloth."""
    for row0, row1 in zip(shirt, shirt[1:]):
      if z <= row1[0]:
        break
    u = (z - row0[0]) / (row1[0] - row0[0])
    _, a, f, b, y = (p + (q - p) * u for p, q in zip(row0, row1))
    px, py, pz = ring(z, a * w * out, f * w * out, b * w * out, y, n=n)[k % n]
    return (px, py, pz)
  if not simple:
    # Shoulder seams, and folds pulled toward the spine by arms reaching for the wheel.
    for side in (-1, 1):
      body.tube([(on_shirt(1.43, 6 if side > 0 else 17), 0.004, 0.004), (on_shirt(1.4, 5 if side > 0 else 18), 0.004, 0.004),
                 (on_shirt(1.36, 4 if side > 0 else 19), 0.004, 0.004)], M["trim"], n=3)
      for z0, z1, k0, k1 in ((1.3, 1.16, 9, 11), (1.2, 1.06, 9, 11), (1.12, 1.0, 8, 10)):
        a, b = (k0, k1) if side > 0 else (23 - k0, 23 - k1)
        body.tube([(on_shirt(z0, a, out=1.02), 0.012, 0.004), (on_shirt(z1, b, out=1.02), 0.004, 0.003)], M["trim"], n=3)
  # The V: two trim strips down the chest.
  for side in () if simple else (-1, 1):
    body.tube([((side * 0.045, -0.08, 1.455), 0.006, 0.012), ((side * 0.012, -0.123, 1.36), 0.006, 0.012)], M["trim"], n=4)

  tag("hips", "upper_leg_l", "upper_leg_r")
  pelvis = [ring(z, a * w, f * w, b * w, n=R) for z, a, f, b in ((0.8, 0.17, 0.11, 0.11), (0.9, 0.172, 0.112, 0.112), (0.98, 0.165, 0.108, 0.108))[::2 if simple else 1]]
  body.loft(pelvis, M["pants"])

  for side, s in (("_l", 1), ("_r", -1)):
    tag("hips", "upper_leg" + side, "lower_leg" + side)
    leg = [
      ((s * 0.095, 0.0, 0.92), 0.088 * w, 0.09 * w),
      ((s * 0.098, -0.005, 0.72), 0.082 * w, 0.085 * w),
      ((s * 0.1, -0.015, 0.5), 0.068 * w, 0.072 * w),
      ((s * 0.103, -0.008, 0.3), 0.064 * w, 0.066 * w),
      ((s * 0.105, 0.005, 0.15), 0.066 * w, 0.066 * w),
    ]
    body.tube(leg[::2] if simple else leg, M["pants"], n=L, side=(1, 0, 0))
    body.tube([((s * 0.105, 0.005, 0.165), 0.071 * w, 0.071 * w), ((s * 0.105, 0.005, 0.12), 0.072 * w, 0.072 * w)], M["pants_dark"], n=L, side=(1, 0, 0))
    tag("upper_leg" + side)
    pocket_x = s * (0.098 + 0.082 * w)
    body.box((min(pocket_x, pocket_x + s * 0.03), -0.06, 0.56), (max(pocket_x, pocket_x + s * 0.03), 0.05, 0.71), M["pants_dark"])
    body.box((min(pocket_x, pocket_x + s * 0.036), -0.065, 0.69), (max(pocket_x, pocket_x + s * 0.036), 0.055, 0.725), M["pants_dark"])

    # Shoes, toe toward -Y.
    tag("foot" + side, "toes" + side, "lower_leg" + side)
    x = s * 0.105
    profile = [(0.07, 0.0), (0.07, 0.085), (0.02, 0.12), (-0.06, 0.1), (-0.15, 0.06), (-0.185, 0.03), (-0.185, 0.0)]
    for y0, half, mat, lift in ((0, 0.055, M["shoes"], 0.012), (0, 0.058, M["sole"], 0.0)):
      outline = [(-y, z + lift) for y, z in profile] if lift else [(-y, z) for y, z in ((0.075, 0.0), (0.075, 0.022), (-0.19, 0.022), (-0.19, 0.0))]
      verts = [(x + dx, py, pz) for dx in (-half, half) for py, pz in outline]
      count = len(outline)
      faces = [tuple(range(count))[::-1], tuple(range(count, 2 * count))]
      for k in range(count):
        n = (k + 1) % count
        faces.append((k, n, count + n, count + k))
      body.add(verts, faces, mat)

    # Sleeve and arm.
    tag("chest", "shoulder" + side, "upper_arm" + side)
    sh, el = SHOULDER.copy(), ELBOW.copy()
    if s < 0:
      sh.x, el.x = -sh.x, -el.x
    mid = sh.lerp(el, 0.55)
    body.tube([(sh - (el - sh).normalized() * 0.03, 0.075 * w, 0.07 * w), (sh.lerp(el, 0.3), 0.07 * w, 0.065 * w), (mid, 0.062 * w, 0.058 * w)], M["shirt"], n=L)
    body.tube([(sh.lerp(el, 0.5), 0.065 * w, 0.061 * w), (mid + (el - sh).normalized() * 0.02, 0.065 * w, 0.061 * w)], M["trim"], n=L)
    tag("upper_arm" + side, "lower_arm" + side)
    wr = WRIST.copy()
    if s < 0:
      wr.x = -wr.x
    body.tube([(sh.lerp(el, 0.4), 0.045 * w, 0.043 * w), (el, 0.041 * w, 0.039 * w), (el.lerp(wr, 0.5), 0.038 * w, 0.034 * w), (wr, 0.03, 0.026)], M["skin"], n=4 if simple else 6)
    tag("hand" + side, "fingers" + side, "lower_arm" + side)
    kn, tip, th = KNUCKLES.copy(), FINGER_TIP.copy(), THUMB_TIP.copy()
    if s < 0:
      kn.x, tip.x, th.x = -kn.x, -tip.x, -th.x
    body.tube([(wr, 0.034, 0.016), (kn, 0.042, 0.018), (kn.lerp(tip, 0.6), 0.038, 0.015), (tip, 0.025, 0.01)], M["skin"], n=4, side=(0, 1, 0))
    if simple:
      continue
    tag("thumb" + side, "hand" + side)
    body.tube([(wr.lerp(kn, 0.3) + Vector((0, -0.018, 0)), 0.012, 0.012), (th, 0.009, 0.009)], M["skin"], n=4)

  parts = [(body, tag)]
  if look.get("backpack"):
    pack = Shape()
    ptag = Tags(pack)
    ptag("chest", "spine")
    p = [ring(z, a, f, b, y=0.188, n=8, power=4) for z, a, f, b in ((1.02, 0.14, 0.06, 0.07), (1.12, 0.155, 0.07, 0.085), (1.3, 0.155, 0.07, 0.085), (1.4, 0.14, 0.06, 0.075))]
    pack.loft(p, M["pack"])
    pack.tube([((-0.15, 0.188, 1.43), 0.05, 0.05), ((0.15, 0.188, 1.43), 0.05, 0.05)], M["pack"], n=8, side=(0, 0, 1))
    pack.box((-0.11, 0.268, 1.06), (0.11, 0.305, 1.24), M["strap"])
    pack.box((-0.115, 0.27, 1.235), (0.115, 0.31, 1.27), M["strap"])
    for s in (-1, 1):
      ptag("chest", "spine")
      pack.tube([
        ((s * 0.09, 0.13, 1.42), 0.022, 0.006),
        ((s * 0.1, 0.03, 1.462), 0.022, 0.006),
        ((s * 0.11, -0.09, 1.4), 0.022, 0.006),
        ((s * 0.125, -0.135, 1.24), 0.02, 0.006),
        ((s * 0.14, -0.125, 1.1), 0.018, 0.006),
        ((s * 0.16, -0.06, 1.04), 0.016, 0.006),
      ], M["strap"], n=4)
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
