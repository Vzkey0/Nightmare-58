# Builds Güino, the giant dog that closes the avenue, from code so proportions can be tweaked and rebuilt.
# A starved husky: black and white mask, glowing bulging eyes, a cheek-to-cheek grin of flat teeth,
# a tongue curling out of the mouth, the ribcage bare, bone spikes down the back, a spiked collar
# and a broken chain dragging on the ground.
# Modeled at the size of the common dog and scaled up at the end. Faces -Y with feet on the origin.
#   blender --background --python art/characters/build_guino.py
import math
import os
import random
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "props"))

from beast_tools import Body, along, paw, shade_fur, tuft
from prop_tools import Shape, material

BLEND_PATH = os.path.join(HERE, "guino.blend")
# About 2.7 m at the withers: the protagonist reaches its elbow.
SCALE = 2.7

BLACK = (
  ("black_light", (0.2, 0.2, 0.22)),
  ("black_mid", (0.12, 0.12, 0.135)),
  ("black_dark", (0.07, 0.07, 0.08)),
  ("black_shadow", (0.03, 0.03, 0.035)),
)
WHITE = (
  ("white_light", (0.9, 0.89, 0.85)),
  ("white_mid", (0.7, 0.69, 0.66)),
  ("white_dark", (0.44, 0.43, 0.41)),
  ("white_shadow", (0.2, 0.19, 0.19)),
)
# White gone grey and brown with street dirt, on the legs and belly.
GRIME = (
  ("grime_light", (0.62, 0.57, 0.5)),
  ("grime_mid", (0.47, 0.42, 0.36)),
  ("grime_dark", (0.3, 0.27, 0.23)),
  ("grime_shadow", (0.15, 0.13, 0.12)),
)
# Old blood soaked into the white, under the mouth and down the chest.
DRIED = (
  ("dried_light", (0.48, 0.16, 0.13)),
  ("dried_mid", (0.36, 0.1, 0.09)),
  ("dried_dark", (0.24, 0.06, 0.06)),
  ("dried_shadow", (0.12, 0.03, 0.03)),
)
M = {}


def make_materials():
  M.update({
    "fur": material("fur"),
    "bone": material("bone", (0.82, 0.76, 0.62)),
    "bone_dark": material("bone_dark", (0.5, 0.44, 0.34)),
    # The cavity inside the ribs. Phase two lights it up like embers.
    "core": material("core", (0.18, 0.03, 0.03)),
    "skin_ear": material("skin_ear", (0.62, 0.5, 0.5)),
    "skin_dark": material("skin_dark", (0.2, 0.17, 0.17)),
    "nose": material("nose", (0.03, 0.03, 0.035), roughness=0.3),
    "mouth": material("mouth", (0.16, 0.02, 0.03)),
    "gums": material("gums", (0.45, 0.07, 0.08)),
    "tongue": material("tongue", (0.62, 0.28, 0.3), roughness=0.4),
    "teeth": material("teeth", (0.9, 0.82, 0.58), roughness=0.4),
    "blood": material("blood", (0.42, 0.02, 0.03), roughness=0.2),
    "drool": material("drool", (0.78, 0.82, 0.8), roughness=0.1),
    "claw": material("claw", (0.13, 0.11, 0.1), roughness=0.4),
    "leather": material("leather", (0.2, 0.1, 0.07)),
    "leather_worn": material("leather_worn", (0.36, 0.22, 0.15)),
    "brass": material("brass", (0.72, 0.56, 0.26), roughness=0.3),
    "engraving": material("engraving", (0.25, 0.18, 0.08), roughness=0.5),
    "scar": material("scar", (0.58, 0.38, 0.38)),
    "metal": material("metal", (0.5, 0.5, 0.52), roughness=0.35),
    "socket": material("socket", (0.02, 0.015, 0.02)),
    # White light with no pupil: it reads in the dark arena from across the plaza.
    "eye": material("eye_glow", (1.0, 0.97, 0.9), glow=3.0),
  })
  for name, color in BLACK + WHITE + GRIME + DRIED:
    M[name] = material(name, color)


# Fur only over the shoulders and the hips: between them the ribs are bare. The hump over the shoulders
# is the highest point and the back drops from it to a narrow, bony rear.
FRONT = Body((
  (-0.02, 0.76, 0.12, 0.16, 0.04, 1.2),
  (-0.08, 0.78, 0.2, 0.24, 0.08, 1.25),
  (-0.18, 0.82, 0.25, 0.28, 0.14, 1.2),
  (-0.28, 0.82, 0.25, 0.26, 0.12, 1.1),
  (-0.38, 0.8, 0.2, 0.2, 0.06, 1.0),
  (-0.46, 0.76, 0.13, 0.13, 0.02, 1.0),
))
HIND = Body((
  (0.5, 0.64, 0.04, 0.04, 0.0, 1.0),
  (0.44, 0.65, 0.1, 0.09, 0.02, 1.2),
  (0.34, 0.66, 0.13, 0.12, 0.04, 1.15),
  (0.24, 0.69, 0.1, 0.1, 0.04, 1.0),
  (0.16, 0.71, 0.08, 0.08, 0.03, 1.0),
))
BARE = (0.16, -0.02)
NECK = (((0, -0.4, 0.92), 0.15, 0.17), ((0, -0.52, 0.78), 0.14, 0.15), ((0, -0.63, 0.68), 0.13, 0.13))
COLLAR_Y = -0.53
# Head space: origin at the back of the skull, facing -Y. The neck reaches forward and down, so the
# head hangs below the hump.
HEAD = Matrix.Translation((0, -0.66, 0.66)) @ Matrix.Rotation(math.radians(14), 4, "X")
HEAD_INV = HEAD.inverted()
UPPER = (
  ((0, 0.06, 0.02), 0.09, 0.09), ((0, 0.0, 0.03), 0.17, 0.16), ((0, -0.09, 0.03), 0.2, 0.17),
  ((0, -0.18, 0.01), 0.18, 0.13), ((0, -0.26, -0.01), 0.13, 0.095), ((0, -0.33, -0.02), 0.095, 0.08),
  ((0, -0.39, -0.025), 0.07, 0.065), ((0, -0.42, -0.03), 0.045, 0.045),
)
# The lower jaw is built closed and swung open around the hinge.
JAW = (((0, -0.01, -0.1), 0.16, 0.05), ((0, -0.12, -0.12), 0.18, 0.06), ((0, -0.24, -0.12), 0.13, 0.05),
       ((0, -0.34, -0.115), 0.09, 0.04), ((0, -0.4, -0.11), 0.05, 0.035))
JAW_OPEN = Matrix.Translation((0, -0.01, -0.1)) @ Matrix.Rotation(math.radians(34), 4, "X") @ Matrix.Translation((0, 0.01, 0.1))
EYE = Vector((0.115, -0.14, 0.1))
rng = random.Random(58)
BLOOD = []
TAG = []


def ring_path(points):
  return [(p, ru, rv) for p, ru, rv in points] + [points[0]]


def sphere(shape, center, radius, mat, facing, n=8, squash=1.0):
  rotation = Vector((0, 0, 1)).rotation_difference(Vector(facing).normalized()).to_matrix().to_4x4()
  profile = [(radius * math.sin(math.radians(a)), radius * squash * math.cos(math.radians(a))) for a in (12, 45, 80, 115, 150, 172)]
  shape.lathe(profile, mat, n=n, at=Matrix.Translation(center) @ rotation)


def tooth(shape, root, direction, length, width, depth, mat="teeth"):
  """A flat, human-like tooth: wide and squared, narrowing a little at the edge."""
  direction = direction.normalized()
  shape.tube([(root, width, depth), (root + direction * length * 0.7, width * 0.95, depth * 0.9),
              (root + direction * length, width * 0.7, depth * 0.5)], M[mat], n=4, side=(1, 0, 0))


def fang(shape, root, direction, length, width):
  direction = direction.normalized()
  shape.tube([(root, width, width * 0.8), (root + direction * length * 0.6 + Vector((0, -0.01, 0)), width * 0.7, width * 0.6),
              (root + direction * length + Vector((0, -0.02, 0)), 0.002, 0.002)], M["teeth"], n=4)


def grin_rows(head, jaw):
  """Teeth from cheek to cheek, upper on the head and lower on the jaw, both in head space."""
  for sign in (1, -1):
    upper = []
    lower = []
    for i in range(9):
      t = i / 8
      y = -0.08 - 0.33 * t
      center, ru, rv = along(UPPER, y)
      upper.append(Vector((sign * ru * (0.9 - 0.25 * t * t), y, center.z - rv * 0.82)))
      jaw_y = -0.1 - 0.29 * t
      center, ru, rv = along(JAW, jaw_y)
      lower.append(Vector((sign * ru * (0.86 - 0.25 * t * t), jaw_y, center.z + rv * 0.85)))
    head.tube([(p + Vector((0, 0, 0.01)), 0.016, 0.013) for p in upper], M["gums"], n=5)
    jaw.tube([(p - Vector((0, 0, 0.008)), 0.015, 0.012) for p in lower], M["gums"], n=5)
    for i, (top, bottom) in enumerate(zip(upper, lower)):
      # One tooth missing on each row and one snapped: a perfect grin looks like a toy.
      broken = 0.4 if (sign, i) == (-1, 5) else 1.0
      if i == 7:
        fang(head, top, Vector((0, -0.2, -1)), 0.1, 0.018)
        fang(jaw, bottom, Vector((0, -0.25, 1)), 0.08, 0.016)
        continue
      size = 1.0 - 0.3 * abs(i - 4) / 4
      if (sign, i) != (1, 2):
        tooth(head, top, Vector((0, -0.1, -1)), 0.055 * size * broken, 0.019, 0.011)
      if (sign, i) != (-1, 3):
        tooth(jaw, bottom, Vector((0, -0.15, 1)), 0.045 * size, 0.018, 0.01)
    BLOOD.extend(lower[1:4])
  for x in (0.014, -0.014):
    tooth(head, Vector((x, -0.42, -0.06)), Vector((0, -0.1, -1)), 0.05, 0.013, 0.01)


def build_face(head):
  head.tube(UPPER, M["fur"], n=12, side=(1, 0, 0))
  head.tube([((0, -0.38, 0.03), 0.065, 0.045), ((0, -0.44, 0.015), 0.062, 0.045), ((0, -0.47, 0.0), 0.04, 0.03)], M["nose"], n=8, side=(1, 0, 0))
  # Bulging eyes in dark sockets, with a tiny pupil, under brows that crease down toward the nose.
  for sign in (1, -1):
    center = Vector((sign * EYE.x, EYE.y, EYE.z))
    facing = Vector((sign * 0.75, -1, 0.25))
    sphere(head, center - facing.normalized() * 0.02, 0.074, M["socket"], facing, n=9, squash=0.6)
    sphere(head, center, 0.056, M["eye"], facing, n=10)
    # The lid slants down toward the nose and the brow sits on it: a glare, not a stare.
    f = facing.normalized()
    up = (Vector((0, 0, 1)) - f * f.z).normalized()
    out = (Vector((sign, 0, 0)) - f * f.x * sign).normalized()
    for lift, push, size in ((0.0, 0.035, 1.0), (0.04, 0.02, 1.35)):
      head.tube([
        (center + f * push + up * (0.0 + lift) - out * 0.07, 0.016 * size, 0.012 * size),
        (center + f * (push + 0.012) + up * (0.03 + lift) - out * 0.015, 0.028 * size, 0.02 * size),
        (center + f * push + up * (0.055 + lift) + out * 0.05, 0.02 * size, 0.014 * size),
        (center + up * (0.05 + lift) + out * 0.085, 0.008, 0.006),
      ], M["fur"], n=6)
    head.tube([
      ((sign * 0.06, center.y - 0.04, center.z - 0.07), 0.012, 0.01),
      ((sign * (EYE.x + 0.02), center.y, center.z - 0.08), 0.018, 0.012),
      ((sign * (EYE.x + 0.07), center.y + 0.06, center.z - 0.05), 0.01, 0.008),
    ], M["fur"], n=5)
    # Snarl creases up the muzzle.
    for k in range(3):
      y = -0.27 - 0.035 * k
      center_m, ru, rv = along(UPPER, y)
      head.tube([((sign * ru * 0.75, y + 0.02, center_m.z + rv * 0.55), 0.008, 0.006),
                 ((sign * ru * 0.25, y, center_m.z + rv * 0.98), 0.009, 0.006)], M["fur"], n=4)
    # Claw scars: three on the left, raking from the brow down the cheek, one across the right muzzle.
    rakes = ((-0.04, 0.0), (-0.07, 0.025), (-0.1, 0.05)) if sign > 0 else ((-0.22, 0.0),)
    for start, shift in rakes:
      path = []
      for k, angle in enumerate((70, 45, 20, -5)):
        y = start - 0.045 * k - shift * 0.3
        center_s, ru, rv = along(UPPER, y)
        a = math.radians(angle - shift * 200)
        path.append((center_s + Vector((sign * ru * math.cos(a) * 1.01, 0, rv * math.sin(a) * 1.01)), 0.009, 0.005))
      head.tube(path, M["scar"], n=4)
    # Husky cheek fluff hanging off the corners of the jaw.
    for k in range(4):
      base = Vector((sign * 0.17, -0.02 - 0.03 * k, -0.06 - 0.02 * k))
      tuft(head, M["fur"], base, Vector((sign, 0.3, -0.5)).normalized(), 0.08, 0.04, width=0.04)


def ear(head, sign):
  if sign > 0:
    # Bitten: two bites out of the edges.
    outline = [(-0.08, 0.0), (-0.085, 0.08), (-0.07, 0.13), (-0.035, 0.145), (-0.052, 0.18), (-0.02, 0.25), (0.0, 0.28),
               (0.03, 0.2), (0.045, 0.17), (0.015, 0.152), (0.058, 0.128), (0.07, 0.11), (0.085, 0.0)]
  else:
    outline = [(-0.08, 0.0), (-0.085, 0.08), (-0.06, 0.17), (-0.02, 0.25), (0.0, 0.28), (0.03, 0.2), (0.07, 0.11), (0.085, 0.0)]
  at = (Matrix.Translation((0.13 * sign, 0.02, 0.13)) @ Matrix.Rotation(math.radians(-30 * sign), 4, "Z")
        @ Matrix.Rotation(math.radians(-24 * sign), 4, "Y") @ Matrix.Rotation(math.radians(-12), 4, "X"))
  head.extrude(outline, -0.008, 0.008, M["fur"], at=at)
  inner = [(x * 0.72, -0.009, 0.015 + z * 0.8) for x, z in outline]
  head.add(inner, [tuple(range(len(inner)))], M["skin_ear"], at=at)
  # White fur tufts spilling out of the inner ear.
  for k in range(4):
    base = at @ Vector(((k - 1.5) * 0.03, -0.012, 0.02))
    tuft(head, M["fur"], base, (at.to_3x3() @ Vector((0, -0.4, 1))).normalized(), 0.09 + 0.02 * (k % 2), 0.0, width=0.025)


def build_jaw(jaw):
  jaw.tube(JAW, M["fur"], n=10, side=(1, 0, 0))
  # The tongue spills over the lower teeth and curls out to the left, like a whip.
  jaw.tube([
    ((0, -0.04, -0.09), 0.075, 0.02), ((0, -0.2, -0.1), 0.07, 0.02), ((0.01, -0.36, -0.085), 0.06, 0.018),
    ((0.05, -0.45, -0.07), 0.055, 0.016), ((0.09, -0.5, -0.12), 0.05, 0.016), ((0.12, -0.52, -0.2), 0.045, 0.015), ((0.18, -0.5, -0.3), 0.038, 0.014),
    ((0.19, -0.43, -0.37), 0.03, 0.012), ((0.14, -0.39, -0.37), 0.024, 0.01), ((0.11, -0.42, -0.33), 0.015, 0.008),
  ], M["tongue"], n=6, side=(1, 0, 0))


def build_head(shape):
  shape.tube(NECK, M["fur"], n=12, side=(1, 0, 0))
  head = Shape()
  jaw = Shape()
  build_face(head)
  for sign in (1, -1):
    ear(head, sign)
  build_jaw(jaw)
  grin_rows(head, jaw)
  # The throat fills the open mouth behind the teeth.
  head.tube([((0, 0.02, -0.05), 0.14, 0.09), ((0, -0.15, -0.14), 0.15, 0.1), ((0, -0.3, -0.18), 0.1, 0.08)], M["mouth"], n=10, side=(1, 0, 0))
  shape.add(jaw.verts, jaw.faces, jaw.mats, at=HEAD @ JAW_OPEN)
  shape.add(head.verts, head.faces, head.mats, at=HEAD)
  # Drool in strings off the lower lip, each ending in a drop, and blood running from the grin.
  opened = HEAD @ JAW_OPEN
  for x, length in ((0.12, 0.13), (0.075, 0.2), (-0.09, 0.16), (-0.14, 0.1)):
    center, ru, rv = along(JAW, -0.3 + abs(x) * 0.6)
    top = opened @ Vector((x, center.y, center.z - rv * 0.6))
    bottom = top + Vector((0, 0, -length))
    shape.tube([(top, 0.012, 0.012), (top.lerp(bottom, 0.5), 0.005, 0.005), (bottom, 0.006, 0.006),
                (bottom + Vector((0, 0, -0.025)), 0.014, 0.014), (bottom + Vector((0, 0, -0.045)), 0.004, 0.004)], M["drool"], n=5)
  for k, point in enumerate(BLOOD):
    top = opened @ (point + Vector((0, -0.012, -0.02)))
    shape.tube([(top, 0.013, 0.007), (top + Vector((0, 0, -0.05 - 0.025 * (k % 3))), 0.007, 0.004),
                (top + Vector((0, 0, -0.07 - 0.03 * (k % 3))), 0.002, 0.002)], M["blood"], n=4, side=(1, 0, 0))


def build_collar(shape):
  points = []
  outward = []
  for k in range(16):
    a = math.tau * k / 16
    center, rx, rz = along(NECK, COLLAR_Y + 0.05 * math.sin(a))
    direction = Vector((math.cos(a), 0, math.sin(a)))
    points.append((center + Vector((direction.x * (rx + 0.016), 0, direction.z * (rz + 0.016))), 0.05, 0.022))
    outward.append((Vector(points[-1][0]), direction))
  shape.tube(ring_path(points), M["leather"], n=4, side=(0, 1, 0))
  # Scuffs where the leather wore through.
  for k in (2, 6, 9):
    base, direction = outward[k]
    shape.tube([(base + direction * 0.012 + Vector((0, -0.03, 0)), 0.02, 0.008), (base + direction * 0.012 + Vector((0, 0.03, 0)), 0.02, 0.008)],
               M["leather_worn"], n=4, side=direction)
  for k, (base, direction) in enumerate(outward):
    if k in (11, 12, 13):
      continue
    tip = base + direction * (0.12 if k % 2 else 0.09)
    shape.tube([(base, 0.032, 0.032), (base.lerp(tip, 0.4), 0.02, 0.02), (tip, 0.002, 0.002)], M["metal"], n=5)
  ring = outward[12][0] + Vector((0, -0.03, -0.035))
  link(shape, ring, Vector((0, 0, 1)), Vector((1, 0, 0)), 0.055, 0.04)
  # A tag shaped like a bone hangs beside the chain, with his name on it.
  tag_ring = outward[11][0] + Vector((0, -0.03, -0.03))
  link(shape, tag_ring, Vector((0, 0, 1)), Vector((0, 1, 0)), 0.04, 0.03)
  TAG.append(tag_ring + Vector((0.0, -0.012, -0.06)))
  bone = [(-0.035, 0.009), (-0.044, 0.02), (-0.056, 0.016), (-0.058, 0.0), (-0.056, -0.016), (-0.044, -0.02), (-0.035, -0.009),
          (0.035, -0.009), (0.044, -0.02), (0.056, -0.016), (0.058, 0.0), (0.056, 0.016), (0.044, 0.02), (0.035, 0.009)]
  shape.extrude(bone, -0.004, 0.004, M["brass"], at=Matrix.Translation(TAG[0]) @ Matrix.Rotation(math.radians(-8), 4, "Y"))
  return ring + Vector((0, 0, -0.045))


def link(shape, center, along_dir, across, length, width):
  points = []
  for k in range(8):
    a = math.tau * k / 8
    points.append((center + along_dir * math.cos(a) * length * 0.5 + across * math.sin(a) * width * 0.5, 0.008, 0.008))
  shape.tube(ring_path(points), M["metal"], n=4)


def build_chain(shape, start):
  """A broken chain hanging from the collar and dragging behind on the ground."""
  route = [start, Vector((0.06, -0.62, 0.3)), Vector((0.1, -0.6, 0.04)), Vector((0.08, -0.4, 0.012)),
           Vector((0.06, -0.1, 0.012)), Vector((0.1, 0.2, 0.012)), Vector((0.05, 0.42, 0.012))]
  step = 0.04
  carry = 0.0
  k = 0
  for a, b in zip(route, route[1:]):
    direction = (b - a).normalized()
    distance = (b - a).length
    side = direction.cross(Vector((0, 0, 1)))
    side = side.normalized() if side.length > 0.01 else Vector((1, 0, 0))
    up = side.cross(direction).normalized()
    d = carry
    while d < distance:
      link(shape, a + direction * d, direction, side if k % 2 else up, 0.055, 0.032)
      d += step
      k += 1
    carry = d - distance


def spine_z(y):
  """Height of the top of the back at y, across the bare ribs too."""
  if y <= BARE[1]:
    return FRONT.surface(y, 90).z
  if y >= BARE[0]:
    return HIND.surface(y, 90).z
  t = (BARE[0] - y) / (BARE[0] - BARE[1])
  return HIND.surface(BARE[0], 90).z + (FRONT.surface(BARE[1], 90).z - HIND.surface(BARE[0], 90).z) * t


def build_ribs(shape):
  # The bare middle: a dark cavity, the spine on top, thin ribs with gaps between them and the sternum below.
  shape.tube([((0, 0.2, 0.68), 0.07, 0.08), ((0, 0.08, 0.7), 0.1, 0.12), ((0, -0.06, 0.72), 0.12, 0.15)], M["core"], n=8, side=(1, 0, 0))
  shape.tube([((0, y, spine_z(y) - 0.04), 0.03, 0.03) for y in (0.2, 0.1, 0.0, -0.08)], M["bone"], n=6)
  shape.tube([((0, 0.12, 0.5), 0.022, 0.012), ((0, 0.0, 0.48), 0.026, 0.014), ((0, -0.12, 0.49), 0.026, 0.014)], M["bone"], n=5, side=(1, 0, 0))
  for i in range(9):
    y = 0.14 - i * 0.03
    top = spine_z(y) - 0.05
    center_z = (top + 0.48) / 2
    half = (top - 0.48) / 2
    reach = 1.0 - abs(i - 5) * 0.05
    path = []
    for a in (84, 58, 30, 0, -30, -58, -84):
      r = math.radians(a)
      path.append(((0.18 * reach * math.cos(r), y + (84 - a) * 0.0006, center_z + half * math.sin(r)), 0.011, 0.008))
    for side in (1, -1):
      rib = [((side * p[0], p[1], p[2]), ru, rv) for p, ru, rv in path]
      # Two snapped ribs, one each side, ending in a jagged point that sticks out of the body.
      if (side, i) in ((1, 3), (-1, 6)):
        rib = rib[:4]
        end = Vector(rib[-1][0])
        rib.append((end + Vector((side * 0.05, 0.015, -0.02)), 0.002, 0.002))
      shape.tube(rib, M["bone"], n=4, side=(0, 1, 0))


# Long and raised, a whip for the tail swipe.
TAIL = (((0, 0.48, 0.68), 0.05, 0.05), ((0, 0.62, 0.8), 0.045, 0.045), ((0.03, 0.8, 0.92), 0.038, 0.038),
        ((0.07, 0.98, 0.95), 0.03, 0.03), ((0.12, 1.14, 0.9), 0.022, 0.022), ((0.15, 1.26, 0.8), 0.014, 0.014),
        ((0.16, 1.32, 0.7), 0.005, 0.005))


def point_on(path, t):
  points = [Vector(p) for p, _, _ in path]
  lengths = [(b - a).length for a, b in zip(points, points[1:])]
  goal = t * sum(lengths)
  for a, b, length in zip(points, points[1:], lengths):
    if goal <= length:
      return a.lerp(b, goal / length)
    goal -= length
  return points[-1]


def build_spikes(shape):
  # Bone spikes break through the spine, tallest over the hump, and grow again toward the tip of the tail.
  heights = {-0.42: 0.07, -0.34: 0.11, -0.26: 0.15, -0.18: 0.17, -0.1: 0.14, -0.02: 0.11, 0.06: 0.08, 0.14: 0.07,
             0.22: 0.06, 0.3: 0.06, 0.38: 0.05, 0.46: 0.04}
  for y, height in heights.items():
    base = Vector((0, y, spine_z(y) - 0.02))
    tip = base + Vector((0, 0.05 + height * 0.35, height))
    shape.tube([(base, 0.028, 0.038), (base.lerp(tip, 0.5), 0.017, 0.022), (tip, 0.002, 0.002)], M["bone"], n=4, side=(1, 0, 0))
  for t, height in ((0.2, 0.04), (0.35, 0.05), (0.5, 0.06), (0.65, 0.08), (0.8, 0.1), (0.92, 0.11)):
    base = point_on(TAIL, t)
    ahead = point_on(TAIL, min(t + 0.05, 1.0))
    back = (ahead - base).normalized()
    up = (Vector((0, 0, 1)) - back * back.z).normalized()
    tip = base + up * height + back * height * 0.4
    shape.tube([(base, 0.02, 0.026), (base.lerp(tip, 0.5), 0.012, 0.015), (tip, 0.002, 0.002)], M["bone"], n=4, side=(1, 0, 0))


def build_tail(shape):
  shape.tube(TAIL, M["fur"], n=7)
  # Fur bristling off both sides of the tail.
  for t in (0.15, 0.3, 0.45, 0.6, 0.75, 0.88):
    base = point_on(TAIL, t)
    for side in (1, -1):
      strand(shape, base + Vector((side * 0.02, 0, 0)), Vector((side, 0, 0.6)).normalized(), 0.07 - t * 0.03, 0.022, sweep=0.04)


def build_limbs(shape):
  for sign in (1, -1):
    def at(x, y, z):
      return Vector((sign * x, y, z))
    # Front legs planted wide with the elbows out: a heavy upper arm, a forearm swelling with muscle
    # before it thins at the wrist, and hands spread flat on the asphalt.
    elbow = at(0.3, -0.14, 0.5)
    shape.tube([(at(0.18, -0.22, 0.86), 0.14, 0.17), (at(0.25, -0.18, 0.68), 0.12, 0.13), (elbow, 0.085, 0.09),
                (at(0.3, -0.2, 0.38), 0.085, 0.09), (at(0.285, -0.27, 0.24), 0.065, 0.065), (at(0.275, -0.31, 0.15), 0.048, 0.05),
                (at(0.28, -0.34, 0.09), 0.046, 0.046)], M["fur"], n=8)
    shape.tube([(elbow + Vector((0, 0.03, 0)), 0.04, 0.04), (elbow + Vector((sign * 0.02, 0.09, -0.02)), 0.022, 0.022)], M["bone_dark"], n=5)
    strand(shape, elbow + Vector((0, 0.05, -0.03)), Vector((sign * 0.3, 0.6, -1)).normalized(), 0.06, 0.03, sweep=0.02)
    paw(shape, M["skin_dark"], M["claw"], at(0.28, -0.34, 0.085), (sign * 0.35, -1, 0), (-0.06, -0.02, 0.02, 0.06), 0.08, sign,
        size=1.8, claw_length=0.11)
    # Hind legs: thin and bony, with the hock sticking out.
    hock = at(0.18, 0.44, 0.22)
    shape.tube([(at(0.1, 0.34, 0.66), 0.11, 0.13), (at(0.17, 0.24, 0.48), 0.07, 0.075), (at(0.19, 0.2, 0.42), 0.055, 0.06),
                (hock, 0.04, 0.045), (at(0.17, 0.38, 0.08), 0.035, 0.035)], M["fur"], n=8)
    shape.tube([(hock + Vector((0, 0.01, 0.01)), 0.035, 0.035), (hock + Vector((0, 0.06, 0.0)), 0.02, 0.02)], M["bone_dark"], n=5)
    paw(shape, M["skin_dark"], M["claw"], at(0.17, 0.38, 0.075), (sign * 0.12, -1, 0), (-0.045, -0.015, 0.015, 0.045), 0.06, sign,
        size=1.5, claw_length=0.08)


def strand(shape, base, out, length, width, sweep=0.0, droop=0.0):
  """A lock of fur that bends as it grows: combed back by sweep, pulled down at the end by droop."""
  mid = base + out * length * 0.55 + Vector((0, sweep * 0.35, -droop * 0.15))
  tip = base + out * length + Vector((0, sweep, -droop))
  shape.tube([(base, width, width * 0.5), (mid, width * 0.65, width * 0.32), (tip, 0.002, 0.002)], M["fur"], n=3, side=out)


def build_fur(shape):
  # Mane: long, heavy locks over the neck and the hump that hang down the sides.
  for y in (-0.62, -0.57, -0.52, -0.47, -0.42):
    for angle in range(-30, 211, 18):
      a = math.radians(angle + rng.uniform(-7, 7))
      center, rx, rz = along(NECK, y)
      base = center + Vector(((rx - 0.02) * math.cos(a), 0, (rz - 0.02) * math.sin(a)))
      out = Vector((math.cos(a), 0, math.sin(a)))
      hang = 1.0 - abs(math.sin(a))
      strand(shape, base, out, rng.uniform(0.1, 0.16), 0.055, sweep=rng.uniform(0.06, 0.1), droop=0.04 + 0.1 * hang)
  for y in (-0.38, -0.32, -0.26, -0.2, -0.14, -0.08):
    for angle in range(20, 161, 20):
      a = angle + rng.uniform(-8, 8)
      out = Vector((math.cos(math.radians(a)), 0, math.sin(math.radians(a))))
      hang = 1.0 - abs(math.sin(math.radians(a)))
      strand(shape, FRONT.surface(y, a, -0.02), out, rng.uniform(0.09, 0.14), 0.05, sweep=rng.uniform(0.07, 0.11), droop=0.03 + 0.09 * hang)
  # Rough, short fur over the starved hips.
  for y in (0.2, 0.28, 0.36, 0.44):
    for angle in (150, 115, 65, 30):
      a = angle + rng.uniform(-10, 10)
      out = Vector((math.cos(math.radians(a)), 0, math.sin(math.radians(a))))
      strand(shape, HIND.surface(y, a, -0.012), out, rng.uniform(0.04, 0.06), 0.03, sweep=0.06)
  # Bristles standing up along the spine, between the bone spikes.
  y = -0.44
  while y < 0.48:
    for x in (0.03, -0.03):
      base = Vector((x, y, spine_z(y) - 0.01))
      strand(shape, base, Vector((x * 6, 0.25, 1)).normalized(), rng.uniform(0.05, 0.08), 0.016, sweep=0.02)
    y += 0.04
  # Ragged fringes where the fur gives out, hanging down over the ribs.
  for side in (1, -1):
    for angle in (75, 50, 25, 0, -25, -50):
      a = angle if side > 0 else 180 - angle
      strand(shape, FRONT.surface(BARE[1] + 0.01, a, -0.01), Vector((side * 0.35, 0.8, -0.5)).normalized(), rng.uniform(0.08, 0.13), 0.04, droop=0.05)
      strand(shape, HIND.surface(BARE[0] - 0.01, a, -0.01), Vector((side * 0.4, -0.2, -1)).normalized(), rng.uniform(0.05, 0.09), 0.035, droop=0.02)


def grime(p):
  return math.sin(p.x * 29 + p.y * 17) * math.cos(p.z * 23 - p.y * 11) + 0.5 * math.sin(p.x * 61 - p.z * 47)


def coat(c):
  """Husky markings: black over the back and the top of the head, white on the face, chest, belly and legs."""
  local = HEAD_INV @ (c / SCALE)
  if local.y < 0.12 and abs(local.x) < 0.3 and -0.3 < local.z < 0.35:
    eye = Vector((math.copysign(EYE.x, local.x), EYE.y, EYE.z))
    stripe = abs(local.x) < 0.03 and local.z > 0.02 and local.y > -0.3
    cap = local.z > 0.1 and local.y > -0.22 and (local - eye).length > 0.13
    ear = local.z > 0.12 and abs(local.x) > 0.08
    if stripe or cap or ear:
      return BLACK_NAMES
    return DRIED_NAMES if local.z < -0.04 and grime(local) > 0.15 else WHITE_NAMES
  p = c / SCALE
  if p.z < 0.4:
    return GRIME_NAMES if grime(p) > 0.2 else WHITE_NAMES
  body = FRONT if p.y < 0.07 else HIND
  _, zc, _, _, _, _ = body.at(p.y)
  if p.y < -0.33:
    zc -= 0.06
  if p.z > zc - 0.03:
    return BLACK_NAMES
  if p.y < -0.4 and p.z < 0.7 and grime(p) > 0.3:
    return DRIED_NAMES
  return GRIME_NAMES if p.z < 0.55 and grime(p) > 0.2 else WHITE_NAMES


BLACK_NAMES = [name for name, _ in BLACK]
WHITE_NAMES = [name for name, _ in WHITE]
GRIME_NAMES = [name for name, _ in GRIME]
DRIED_NAMES = [name for name, _ in DRIED]


def engrave_name(guino):
  """Raised letters on the tag, joined into the body so they move with the collar."""
  curve = bpy.data.curves.new("tag_name", "FONT")
  curve.body = "GÜINO"
  curve.size = 0.021 * SCALE
  curve.extrude = 0.0015 * SCALE
  curve.align_x = "CENTER"
  curve.align_y = "CENTER"
  text = bpy.data.objects.new("tag_name", curve)
  bpy.context.scene.collection.objects.link(text)
  text.location = (TAG[0] + Vector((0, -0.006, 0))) * SCALE
  text.rotation_euler = (math.radians(90), math.radians(-8), 0)
  with bpy.context.temp_override(active_object=text, selected_editable_objects=[text], object=text):
    bpy.ops.object.convert(target="MESH")
  text.data.materials.clear()
  text.data.materials.append(M["engraving"])
  with bpy.context.temp_override(active_object=guino, selected_editable_objects=[guino, text]):
    bpy.ops.object.join()


def main():
  bpy.ops.wm.read_factory_settings(use_empty=True)
  make_materials()
  shape = Shape()
  FRONT.loft(shape, M["fur"], rng)
  HIND.loft(shape, M["fur"], rng)
  build_ribs(shape)
  build_head(shape)
  ring = build_collar(shape)
  build_chain(shape, ring)
  build_spikes(shape)
  build_tail(shape)
  build_limbs(shape)
  build_fur(shape)
  shape.verts = [(x * SCALE, y * SCALE, z * SCALE) for x, y, z in shape.verts]
  guino = shape.finish("guino")
  shade_fur(guino, M, coat, rng, 0.7, scale=SCALE)
  engrave_name(guino)
  bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)


main()
