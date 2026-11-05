# Builds the giant rat of the avenue from code, so proportions can be tweaked and rebuilt.
# Faces -Y with feet on the origin. +X is the rat's left.
#   blender --background --python art/characters/build_rat.py
import math
import os
import random
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "props"))

from beast_tools import Body, Tags, both, chain_bones, leg_bones, mirrored, paw, rig, shade_fur
from prop_tools import Shape, material

BLEND_PATH = os.path.join(HERE, "rat.blend")

# The fur is painted per face by how much it faces the sky, so the shadows live in the model.
FUR_TONES = (
  ("fur_light", (0.4, 0.42, 0.46)),
  ("fur_mid", (0.26, 0.27, 0.31)),
  ("fur_dark", (0.15, 0.15, 0.18)),
  ("fur_shadow", (0.065, 0.065, 0.08)),
)
M = {}


def make_materials():
  M.update({
  "fur": material("fur"),
  "skin": material("skin", (0.62, 0.45, 0.44)),
  "skin_dark": material("skin_dark", (0.36, 0.23, 0.24)),
  "skin_raw": material("skin_raw", (0.47, 0.33, 0.33)),
  "tail_light": material("tail_light", (0.6, 0.5, 0.48)),
  "tail_dark": material("tail_dark", (0.5, 0.4, 0.39)),
  "teeth": material("teeth", (0.82, 0.68, 0.34), roughness=0.5),
  "gums": material("gums", (0.32, 0.06, 0.07)),
  "mouth": material("mouth", (0.04, 0.015, 0.015)),
  "claw": material("claw", (0.1, 0.085, 0.075), roughness=0.5),
  "socket": material("socket", (0.025, 0.02, 0.025)),
  # Same amber as the skeleton: red would read as the HUD's health.
  "eye": material("eye_glow", (1.0, 0.42, 0.02), glow=1.6),
  })
  for name, color in FUR_TONES:
    M[name] = material(name, color)

# From the tail to the nose. The peak over the middle is the hunch; the haunches are wider than the shoulders.
BODY = Body(tuple(station + (0.88,) for station in (
  (0.52, 0.4, 0.05, 0.05, 0.0),
  (0.45, 0.41, 0.15, 0.14, 0.01),
  (0.33, 0.43, 0.24, 0.21, 0.025),
  (0.18, 0.46, 0.27, 0.25, 0.04),
  (0.03, 0.49, 0.25, 0.26, 0.05),
  (-0.12, 0.48, 0.22, 0.23, 0.045),
  (-0.26, 0.46, 0.19, 0.2, 0.03),
  (-0.37, 0.45, 0.13, 0.14, 0.015),
  (-0.46, 0.45, 0.14, 0.13, 0.02),
  (-0.56, 0.425, 0.12, 0.105, 0.012),
  (-0.66, 0.39, 0.08, 0.075, 0.0),
  (-0.75, 0.365, 0.045, 0.046, 0.0),
  (-0.8, 0.355, 0.018, 0.02, 0.0),
)))
rng = random.Random(58)
tag = None

BODY_BONES = ("hips", "spine", "chest", "neck", "head", "tail_1")
TAIL = [(0, 0.49, 0.4), (0.02, 0.7, 0.32), (0.07, 0.94, 0.28), (0.16, 1.18, 0.31), (0.28, 1.38, 0.42), (0.37, 1.5, 0.6), (0.4, 1.53, 0.78)]


def build_head(shape):
  # Jaw hangs open under the snout: the dark mouth and the gums show between them.
  tag("head", "jaw")
  shape.tube([((0, -0.55, 0.345), 0.045, 0.02), ((0, -0.64, 0.325), 0.035, 0.02), ((0, -0.72, 0.31), 0.02, 0.014)], M["mouth"], n=6)
  tag("jaw")
  shape.tube([((0, -0.54, 0.335), 0.075, 0.035), ((0, -0.64, 0.29), 0.05, 0.027), ((0, -0.72, 0.268), 0.026, 0.018)], M["fur"], n=6, side=(1, 0, 0))
  tag("head")
  shape.tube([((-0.052, -0.67, 0.338), 0.011, 0.011), ((-0.03, -0.735, 0.33), 0.012, 0.012), ((0, -0.765, 0.327), 0.012, 0.012),
              ((0.03, -0.735, 0.33), 0.012, 0.012), ((0.052, -0.67, 0.338), 0.011, 0.011)], M["gums"], n=5)
  shape.tube([((0, -0.785, 0.358), 0.03, 0.024), ((0, -0.815, 0.352), 0.02, 0.016)], M["skin_dark"], n=6)

  # Long chisel incisors, chipped and yellow.
  for x, length in ((0.012, 0.046), (-0.012, 0.038)):
    shape.tube([((x, -0.762, 0.335), 0.011, 0.007), ((x, -0.772, 0.335 - length * 0.6), 0.011, 0.006),
                ((x, -0.768, 0.335 - length), 0.009, 0.002)], M["teeth"], n=4, side=(1, 0, 0))
  tag("jaw")
  for x in (0.01, -0.01):
    shape.tube([((x, -0.716, 0.272), 0.009, 0.006), ((x, -0.742, 0.306), 0.008, 0.002)], M["teeth"], n=4, side=(1, 0, 0))
  tag("head")
  # Snarl creases bunched up over the nose.
  for y, z in ((-0.7, 0.398), (-0.73, 0.39), (-0.675, 0.41)):
    shape.tube([((-0.045, y + 0.012, z - 0.012), 0.006, 0.004), ((0, y, z + 0.006), 0.008, 0.005), ((0.045, y + 0.012, z - 0.012), 0.006, 0.004)], M["fur_shadow"], n=4)

  # Small eyes sunk under a brow that drops toward the nose.
  for sign in (1, -1):
    out = Vector((sign * 1.0, -0.55, 0.45)).normalized()
    center = Vector((sign * 0.097, -0.58, 0.465))
    shape.tube([(center - out * 0.01, 0.031, 0.025), (center + out * 0.004, 0.029, 0.023)], M["socket"], n=7, side=(0, 0, 1))
    shape.tube([(center - out * 0.004, 0.017, 0.014), (center + out * 0.01, 0.012, 0.01)], M["eye"], n=6, side=(0, 0, 1))
  both(shape, [((0.055, -0.625, 0.47), 0.014, 0.012), ((0.09, -0.595, 0.495), 0.019, 0.015), ((0.115, -0.545, 0.505), 0.012, 0.01)], M["fur_dark"], n=4)

  for i, (dz, dy, length) in enumerate(((0.025, -0.02, 0.24), (0.0, 0.04, 0.27), (-0.03, 0.08, 0.22))):
    root = (0.04, -0.735, 0.355 + dz * 0.3)
    tip = (0.04 + length, -0.735 + dy + length * 0.35, 0.355 + dz * 2.4)
    both(shape, [(root, 0.003, 0.003), (tip, 0.0008, 0.0008)], M["fur_shadow"], n=3)


def ear(shape, flip, torn):
  outline = [(-0.035, 0.0), (-0.06, 0.04), (-0.066, 0.095), (-0.05, 0.14), (-0.015, 0.165), (0.025, 0.16)]
  outline += [(0.042, 0.135), (0.02, 0.112), (0.056, 0.09)] if torn else [(0.052, 0.125), (0.062, 0.07)]
  outline += [(0.04, 0.01)]
  at = (Matrix.Translation((0.105, -0.47, 0.535)) @ Matrix.Rotation(math.radians(38), 4, "Z")
        @ Matrix.Rotation(math.radians(22), 4, "Y") @ Matrix.Rotation(math.radians(-22), 4, "X"))
  if flip:
    at = Matrix.Scale(-1, 4, (1, 0, 0)) @ at
  shape.extrude(outline, -0.004, 0.004, M["skin_dark"], at=at)
  inner = [(x * 0.86, -0.005, 0.008 + z * 0.88) for x, z in outline]
  shape.add(inner, [tuple(range(len(inner)))], M["skin"], at=at)


def build_limbs(shape):
  for sign in (1, -1):
    side = "_l" if sign > 0 else "_r"
    def at(x, y, z):
      return Vector((sign * x, y, z))
    tag(f"upper_front{side}", f"lower_front{side}", f"foot_front{side}")
    # Front legs: short and bent, with hands that grip.
    shape.tube([(at(0.14, -0.27, 0.42), 0.085, 0.095), (at(0.165, -0.23, 0.22), 0.05, 0.052), (at(0.165, -0.33, 0.06), 0.026, 0.026)], M["fur"], n=6)
    tag(f"foot_front{side}", f"toes_front{side}")
    paw(shape, M["skin"], M["claw"], at(0.165, -0.33, 0.06), (sign * 0.15, -1, 0), (-0.024, -0.008, 0.008, 0.024), 0.04, sign)
    tag(f"upper_hind{side}", f"lower_hind{side}", f"foot_hind{side}")
    # Hind legs: heavy haunch, knee forward, long foot flat on the ground.
    shape.tube([(at(0.19, 0.26, 0.47), 0.15, 0.17), (at(0.24, 0.13, 0.25), 0.085, 0.09), (at(0.235, 0.29, 0.08), 0.032, 0.03)], M["fur"], n=7)
    tag(f"foot_hind{side}", f"toes_hind{side}")
    paw(shape, M["skin"], M["claw"], at(0.235, 0.29, 0.06), (sign * 0.1, -1, -0.22), (-0.03, -0.01, 0.01, 0.03), 0.06, sign)


def build_tail(shape):
  tag(*(f"tail_{i + 1}" for i in range(len(TAIL) - 1)))
  points = TAIL
  path = []
  for i, p in enumerate(points):
    radius = 0.055 * (1 - i / len(points)) ** 1.1 + 0.006
    path.append((p, radius, radius))
  # Ring every segment so it reads scaly, like a real rat's tail.
  fine = []
  for a, b in zip(path, path[1:]):
    for t in (0.0, 0.5):
      fine.append((Vector(a[0]).lerp(Vector(b[0]), t), a[1] + (b[1] - a[1]) * t, a[1] + (b[1] - a[1]) * t))
  fine.append((Vector(path[-1][0]), 0.004, 0.004))
  rings = len(fine)
  shape.tube(fine, M["tail_light"], n=6)
  # Darken every other band by swapping the materials the tube just added.
  start = len(shape.mats) - (rings - 1) * 6 - 2
  for band in range(rings - 1):
    if band % 2:
      for side in range(6):
        shape.mats[start + band * 6 + side] = M["tail_dark"]


def build_mange(shape):
  tag(*BODY_BONES)
  # Ragged tufts along the spine and over the haunches.
  for i in range(26):
    y = 0.4 - i * 0.03
    angle = 90 + rng.uniform(-50, 50)
    out = Vector((math.cos(math.radians(angle)), 0, math.sin(math.radians(angle))))
    base = BODY.surface(y, angle, -0.012)
    tip = base + out * rng.uniform(0.02, 0.045) + Vector((0, rng.uniform(0.07, 0.12), 0))
    shape.tube([(base, 0.03, 0.016), (tip, 0.002, 0.002)], M["fur_dark" if i % 3 else "fur_mid"], n=3, side=out)
  for sign in (1, -1):
    for y, angle in ((0.28, 20), (0.15, 5), (0.32, -10), (-0.2, 15), (-0.28, -10), (-0.42, 30)):
      a = angle if sign > 0 else 180 - angle
      out = Vector((math.cos(math.radians(a)), 0, math.sin(math.radians(a))))
      base = BODY.surface(y, a, -0.012)
      tip = base + out * 0.03 + Vector((0, 0.09, -0.02))
      shape.tube([(base, 0.028, 0.015), (tip, 0.002, 0.002)], M["fur_dark"], n=3, side=out)
  # A bald, scabbed patch on the left flank with the ribs showing through.
  for y in (-0.13, -0.07, -0.01, 0.05):
    path = [(BODY.surface(y - a * 0.0012, a, 0.003), 0.008, 0.005) for a in (40, 20, 0, -20)]
    shape.tube(path, M["skin_raw"], n=4)


def crouched(z, drop=0.07):
  """Lowers everything above the knees and squeezes the legs, so the belly hangs near the ground."""
  t = min(max((z - 0.05) / 0.25, 0.0), 1.0)
  return z - drop * t * t * (3 - 2 * t)


def crouch(shape):
  shape.verts = [(x, y, crouched(z)) for x, y, z in shape.verts]


def bones():
  """Bones as name: (head, tail, parent), placed on the model before the crouch and lowered with it."""
  table = {
    # Carries root motion, so it sits on the ground and has no vertex weights.
    "root": ((0, 0, 0), (0, 0.2, 0), None),
    "hips": ((0, 0.24, 0.46), (0, 0.48, 0.41), "root"),
    "spine": ((0, 0.24, 0.46), (0, -0.06, 0.49), "hips"),
    "chest": ((0, -0.06, 0.49), (0, -0.32, 0.46), "spine"),
    "neck": ((0, -0.32, 0.46), (0, -0.48, 0.45), "chest"),
    "head": ((0, -0.48, 0.45), (0, -0.8, 0.36), "neck"),
    "jaw": ((0, -0.52, 0.34), (0, -0.72, 0.27), "head"),
  }
  table.update(chain_bones("tail", TAIL, "hips"))
  table.update(leg_bones("front_l", "chest", (0.14, -0.27, 0.42), (0.165, -0.23, 0.22), (0.165, -0.33, 0.06), (0.172, -0.38, 0.03), (0.18, -0.44, 0.01)))
  table.update(leg_bones("hind_l", "hips", (0.19, 0.26, 0.47), (0.24, 0.13, 0.25), (0.235, 0.29, 0.08), (0.24, 0.24, 0.02), (0.246, 0.18, 0.0)))
  lower = lambda p: (p[0], p[1], crouched(p[2]))
  return {name: (lower(head), lower(tail), parent) for name, (head, tail, parent) in mirrored(table).items()}


def main():
  bpy.ops.wm.read_factory_settings(use_empty=True)
  make_materials()
  shape = Shape()
  global tag
  tag = Tags(shape)
  tag(*BODY_BONES)
  BODY.loft(shape, M["fur"], rng)
  build_head(shape)
  for flip in (False, True):
    ear(shape, flip, torn=flip)
  build_limbs(shape)
  build_tail(shape)
  build_mange(shape)
  crouch(shape)
  rat = shape.finish("rat")
  shade_fur(rat, M, [name for name, _ in FUR_TONES], rng, 0.4,
            lambda c: c.x > 0.12 and -0.17 < c.y < 0.1 and 0.31 < c.z < 0.55)
  rig(rat, "rat", bones(), tag.ranges())
  bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)


main()
