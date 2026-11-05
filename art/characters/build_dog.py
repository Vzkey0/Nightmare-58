# Builds the feral dog of the avenue from code, so proportions can be tweaked and rebuilt.
# Starved and mangy: bald flanks with the ribs showing, a ragged mane and a jaw hanging open.
# Faces -Y with feet on the origin. +X is the dog's left.
#   blender --background --python art/characters/build_dog.py
import math
import os
import random
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "props"))

from beast_tools import Body, Tags, along, both, chain_bones, leg_bones, mirrored, paw, rig, shade_fur, tuft
from prop_tools import Shape, material

BLEND_PATH = os.path.join(HERE, "dog.blend")

FUR_TONES = (
  ("fur_light", (0.36, 0.28, 0.22)),
  ("fur_mid", (0.24, 0.18, 0.14)),
  ("fur_dark", (0.14, 0.1, 0.085)),
  ("fur_shadow", (0.06, 0.045, 0.04)),
)
M = {}


def make_materials():
  M.update({
    "fur": material("fur"),
    "skin_bald": material("skin_bald", (0.44, 0.34, 0.34)),
    "rib": material("rib", (0.52, 0.41, 0.4)),
    "skin_dark": material("skin_dark", (0.28, 0.2, 0.2)),
    "nose": material("nose", (0.05, 0.04, 0.04), roughness=0.4),
    "mouth": material("mouth", (0.2, 0.03, 0.035)),
    "gums": material("gums", (0.42, 0.08, 0.09)),
    "tongue": material("tongue", (0.5, 0.2, 0.22), roughness=0.5),
    "teeth": material("teeth", (0.86, 0.78, 0.55), roughness=0.5),
    "claw": material("claw", (0.5, 0.42, 0.27), roughness=0.5),
    "socket": material("socket", (0.025, 0.02, 0.02)),
    # Hotter than the skeleton's amber, like an ember, but still not the HUD's health red.
    "eye": material("eye_glow", (1.0, 0.22, 0.03), glow=2.0),
  })
  for name, color in FUR_TONES:
    M[name] = material(name, color)


# From the tail to the chest. High withers, a back that slopes to the hips, a waist sucked in by hunger
# and a deep chest.
BODY = Body((
  (0.5, 0.72, 0.04, 0.04, 0.0, 1.0),
  (0.44, 0.71, 0.11, 0.09, 0.015, 1.2),
  (0.34, 0.7, 0.14, 0.13, 0.03, 1.15),
  (0.2, 0.71, 0.115, 0.11, 0.035, 1.0),
  (0.07, 0.71, 0.125, 0.14, 0.035, 1.25),
  (-0.06, 0.7, 0.155, 0.19, 0.04, 1.35),
  (-0.18, 0.71, 0.165, 0.2, 0.05, 1.3),
  (-0.29, 0.72, 0.145, 0.17, 0.04, 1.15),
  (-0.37, 0.72, 0.09, 0.1, 0.02, 1.0),
))
NECK = (((0, -0.3, 0.78), 0.1, 0.11), ((0, -0.42, 0.74), 0.085, 0.095), ((0, -0.5, 0.69), 0.085, 0.09))
# The head hangs below the withers: it stalks with the head low.
SKULL = (
  ((0, -0.47, 0.71), 0.085, 0.085), ((0, -0.53, 0.69), 0.115, 0.1), ((0, -0.61, 0.665), 0.11, 0.095),
  ((0, -0.69, 0.625), 0.075, 0.07), ((0, -0.78, 0.6), 0.055, 0.055), ((0, -0.85, 0.585), 0.042, 0.042),
  ((0, -0.875, 0.58), 0.025, 0.025),
)
JAW = (((0, -0.54, 0.58), 0.085, 0.04), ((0, -0.66, 0.52), 0.06, 0.03), ((0, -0.78, 0.465), 0.045, 0.025), ((0, -0.84, 0.44), 0.03, 0.02))
rng = random.Random(58)
tag = None

BODY_BONES = ("hips", "spine", "chest", "neck", "tail_1")
NECK_BONES = ("chest", "neck", "head")
TAIL = [(0, 0.48, 0.74), (0.02, 0.58, 0.62), (0.04, 0.66, 0.48), (0.07, 0.7, 0.36), (0.1, 0.72, 0.27)]


def tooth(shape, root, direction, length, width):
  direction = direction.normalized()
  bend = Vector((0, -0.25, 0)) * length
  shape.tube([
    (root, width, width * 0.75),
    (root + direction * length * 0.55, width * 0.85, width * 0.65),
    (root + direction * length + bend, 0.0015, 0.0015),
  ], M["teeth"], n=4)


def build_head(shape):
  tag(*NECK_BONES)
  shape.tube(NECK, M["fur"], n=10, side=(1, 0, 0))
  tag("head")
  shape.tube(SKULL, M["fur"], n=10, side=(1, 0, 0))
  tag("jaw")
  shape.tube(JAW, M["fur"], n=8, side=(1, 0, 0))
  tag("head", "jaw")
  shape.tube([((0, -0.53, 0.62), 0.07, 0.06), ((0, -0.68, 0.55), 0.055, 0.04), ((0, -0.8, 0.5), 0.035, 0.03)], M["mouth"], n=8, side=(1, 0, 0))
  tag("jaw")
  shape.tube([((0, -0.6, 0.53), 0.035, 0.012), ((0, -0.74, 0.49), 0.032, 0.01), ((0.008, -0.83, 0.462), 0.024, 0.008),
              ((0.016, -0.865, 0.44), 0.014, 0.006)], M["tongue"], n=6, side=(1, 0, 0))
  tag("head")
  shape.tube([((0, -0.86, 0.6), 0.03, 0.025), ((0, -0.895, 0.595), 0.028, 0.022), ((0, -0.905, 0.588), 0.015, 0.012)], M["nose"], n=8, side=(1, 0, 0))

  # Lips peeled all the way back: gums and a full row of teeth on both jaws.
  for sign in (1, -1):
    upper = []
    lower = []
    for i in range(7):
      t = i / 6
      y = -0.6 - 0.25 * t
      center, ru, rv = along(SKULL, y)
      upper.append(Vector((sign * ru * 0.78, y, center.z - rv * 0.88)))
      center, _, rv = along(JAW, -0.6 - 0.22 * t)
      lower.append(Vector((sign * (0.075 - 0.047 * t) * 0.92, center.y, center.z + rv * 0.9)))
    tag("head")
    shape.tube([(p, 0.009, 0.007) for p in upper], M["gums"], n=5)
    tag("jaw")
    shape.tube([(p, 0.008, 0.007) for p in lower], M["gums"], n=5)
    for i, (top, bottom) in enumerate(zip(upper, lower)):
      canine = i == 5
      length = 0.068 if canine else 0.022 + rng.uniform(0, 0.014)
      tilt = Vector((rng.uniform(-0.15, 0.15), -0.15, -1))
      tag("head")
      tooth(shape, top, tilt, length, 0.013 if canine else 0.008)
      tag("jaw")
      length = 0.055 if canine else 0.02 + rng.uniform(0, 0.012)
      tooth(shape, bottom, Vector((rng.uniform(-0.15, 0.15), -0.25, 1)), length, 0.012 if canine else 0.008)
  for x in (0.011, 0.03):
    for sign in (1, -1):
      tag("head")
      tooth(shape, Vector((sign * x, -0.857, 0.552)), Vector((0, -0.2, -1)), 0.026, 0.007)
      tag("jaw")
      tooth(shape, Vector((sign * x * 0.85, -0.83, 0.455)), Vector((0, -0.4, 1)), 0.022, 0.007)

  tag("head")
  # Snarl creases bunched up over the muzzle.
  for y, z in ((-0.7, 0.69), (-0.73, 0.677), (-0.76, 0.664)):
    shape.tube([((-0.05, y + 0.015, z - 0.022), 0.006, 0.004), ((0, y, z + 0.006), 0.008, 0.005), ((0.05, y + 0.015, z - 0.022), 0.006, 0.004)], M["fur_shadow"], n=4)

  # Sunken eyes under a brow that drops toward the nose.
  for sign in (1, -1):
    out = Vector((sign * 1.0, -0.9, 0.25)).normalized()
    center = Vector((sign * 0.088, -0.62, 0.71))
    shape.tube([(center - out * 0.012, 0.034, 0.026), (center + out * 0.004, 0.031, 0.024)], M["socket"], n=7, side=(0, 0, 1))
    shape.tube([(center - out * 0.004, 0.019, 0.015), (center + out * 0.011, 0.014, 0.011)], M["eye"], n=6, side=(0, 0, 1))
  both(shape, [((0.035, -0.665, 0.712), 0.015, 0.013), ((0.08, -0.635, 0.748), 0.022, 0.016), ((0.122, -0.575, 0.752), 0.014, 0.011)], M["fur_dark"], n=4)

  for flip in (False, True):
    ear(shape, flip, torn=not flip)


def ear(shape, flip, torn):
  if torn:
    outline = [(-0.045, 0.0), (-0.036, 0.07), (-0.016, 0.13), (-0.002, 0.118), (0.008, 0.148), (0.03, 0.08), (0.046, 0.0)]
  else:
    outline = [(-0.045, 0.0), (-0.036, 0.07), (-0.014, 0.15), (0.0, 0.175), (0.02, 0.12), (0.046, 0.0)]
  at = (Matrix.Translation((0.072, -0.5, 0.765)) @ Matrix.Rotation(math.radians(22), 4, "Z")
        @ Matrix.Rotation(math.radians(14), 4, "Y") @ Matrix.Rotation(math.radians(-14), 4, "X"))
  if flip:
    at = Matrix.Scale(-1, 4, (1, 0, 0)) @ at
  shape.extrude(outline, -0.006, 0.006, M["fur_dark"], at=at)
  inner = [(x * 0.7, -0.007, 0.01 + z * 0.78) for x, z in outline]
  shape.add(inner, [tuple(range(len(inner)))], M["skin_bald"], at=at)


def build_limbs(shape):
  for sign in (1, -1):
    side = "_l" if sign > 0 else "_r"
    def at(x, y, z):
      return Vector((sign * x, y, z))
    # Long, bony legs with the joints sticking out.
    elbow = at(0.125, -0.15, 0.46)
    tag(f"upper_front{side}", f"lower_front{side}", f"foot_front{side}")
    shape.tube([(at(0.11, -0.22, 0.75), 0.075, 0.095), (elbow, 0.045, 0.05), (at(0.12, -0.22, 0.17), 0.026, 0.028), (at(0.12, -0.25, 0.08), 0.025, 0.025)], M["fur"], n=7)
    shape.tube([(elbow + Vector((0, 0.01, 0.01)), 0.03, 0.03), (elbow + Vector((0, 0.045, -0.01)), 0.018, 0.018)], M["skin_bald"], n=5)
    tag(f"lower_front{side}", f"foot_front{side}")
    shape.tube([(at(0.12, -0.21, 0.19), 0.03, 0.03), (at(0.12, -0.205, 0.15), 0.03, 0.03)], M["skin_dark"], n=6)
    tag(f"foot_front{side}", f"toes_front{side}")
    paw(shape, M["skin_dark"], M["claw"], at(0.12, -0.25, 0.07), (sign * 0.1, -1, 0), (-0.03, -0.01, 0.01, 0.03), 0.045, sign, size=1.2, claw_length=0.04)

    hock = at(0.135, 0.42, 0.22)
    tag(f"upper_hind{side}", f"lower_hind{side}", f"foot_hind{side}")
    shape.tube([(at(0.12, 0.33, 0.72), 0.09, 0.12), (at(0.14, 0.2, 0.46), 0.055, 0.06), (hock, 0.03, 0.035), (at(0.13, 0.36, 0.08), 0.025, 0.025)], M["fur"], n=7)
    shape.tube([(hock + Vector((0, -0.01, 0.01)), 0.03, 0.03), (hock + Vector((0, 0.03, 0.0)), 0.02, 0.02)], M["skin_bald"], n=5)
    tag(f"foot_hind{side}", f"toes_hind{side}")
    paw(shape, M["skin_dark"], M["claw"], at(0.13, 0.36, 0.07), (sign * 0.05, -1, 0), (-0.03, -0.01, 0.01, 0.03), 0.045, sign, size=1.2, claw_length=0.04)


def build_tail(shape):
  tag(*(f"tail_{i + 1}" for i in range(len(TAIL) - 1)))
  path = list(zip(TAIL, (0.04, 0.03, 0.022, 0.016, 0.006), (0.04, 0.03, 0.022, 0.016, 0.006)))
  shape.tube(path, M["fur"], n=6)
  for (p, r, _), (q, _, _) in zip(path, path[1:]):
    for side in (1, -1):
      base = Vector(p) + Vector((side * r * 0.7, 0, 0))
      tuft(shape, M["fur_dark"], base, Vector((side, 0, -0.4)).normalized(), 0.04, 0.0, width=0.02)


def neck_point(y, angle, lift=-0.01):
  center, rx, rz = along(NECK, y)
  a = math.radians(angle)
  return center + Vector(((rx + lift) * math.cos(a), 0, (rz + lift) * math.sin(a)))


def build_mange(shape):
  # A ragged mane over the neck and shoulders.
  tag(*NECK_BONES)
  for y in (-0.48, -0.44, -0.4, -0.36, -0.32):
    for angle in range(-10, 200, 24):
      a = angle + rng.uniform(-10, 10)
      out = Vector((math.cos(math.radians(a)), 0, math.sin(math.radians(a))))
      tuft(shape, M["fur_dark" if rng.random() < 0.7 else "fur_mid"], neck_point(y, a), out, rng.uniform(0.04, 0.08), rng.uniform(0.06, 0.11), width=0.035)
  # Clumps down the spine and over the haunches; the flanks between them are bare.
  tag(*BODY_BONES)
  for i in range(30):
    y = 0.44 - i * 0.026
    angle = 90 + rng.uniform(-45, 45)
    out = Vector((math.cos(math.radians(angle)), 0, math.sin(math.radians(angle))))
    tuft(shape, M["fur_dark" if i % 3 else "fur_mid"], BODY.surface(y, angle, -0.012), out, rng.uniform(0.02, 0.05), rng.uniform(0.06, 0.1))
  for sign in (1, -1):
    for y, angle in ((0.36, 10), (0.3, -15), (0.4, -30), (0.27, 30), (-0.26, 20), (-0.3, -5), (-0.24, -30)):
      a = angle if sign > 0 else 180 - angle
      out = Vector((math.cos(math.radians(a)), 0, math.sin(math.radians(a))))
      tuft(shape, M["fur_dark"], BODY.surface(y, a, -0.012), out, 0.035, 0.08, width=0.028)
    # Ribs pressing through the bare skin, slanting back as they go down.
    for y in (-0.21, -0.16, -0.11, -0.06, -0.01, 0.04):
      angles = (30, 5, -20, -45) if sign > 0 else (150, 175, 200, 225)
      path = [(BODY.surface(y + abs(30 - (a if sign > 0 else 180 - a)) * 0.0011, a, 0.002), 0.009, 0.006) for a in angles]
      shape.tube(path, M["rib"], n=4)


def bones():
  """Bones as name: (head, tail, parent), for the side +X; _l bones get a mirrored _r twin."""
  table = {
    # Carries root motion, so it sits on the ground and has no vertex weights.
    "root": ((0, 0, 0), (0, 0.2, 0), None),
    "hips": ((0, 0.3, 0.72), (0, 0.48, 0.74), "root"),
    "spine": ((0, 0.3, 0.72), (0, 0.0, 0.71), "hips"),
    "chest": ((0, 0.0, 0.71), (0, -0.3, 0.77), "spine"),
    "neck": ((0, -0.3, 0.77), (0, -0.5, 0.7), "chest"),
    "head": ((0, -0.5, 0.7), (0, -0.9, 0.59), "neck"),
    "jaw": ((0, -0.55, 0.6), (0, -0.84, 0.44), "head"),
  }
  table.update(chain_bones("tail", TAIL, "hips"))
  table.update(leg_bones("front_l", "chest", (0.11, -0.22, 0.75), (0.125, -0.15, 0.46), (0.12, -0.22, 0.17), (0.12, -0.31, 0.035), (0.125, -0.365, 0.015)))
  table.update(leg_bones("hind_l", "hips", (0.12, 0.33, 0.72), (0.14, 0.2, 0.46), (0.135, 0.42, 0.22), (0.13, 0.3, 0.035), (0.13, 0.245, 0.015)))
  return mirrored(table)


def bald(c):
  """A ragged patch on each flank, plus the lower legs."""
  dy = (c.y + 0.07) / 0.18
  dz = (c.z - 0.6) / 0.18
  edge = 1.0 + 0.45 * math.sin(c.y * 61 + c.z * 37) * math.cos(c.z * 53 - c.y * 19)
  return (abs(c.x) > 0.06 and dy * dy + dz * dz < edge) or c.z < 0.26


def main():
  bpy.ops.wm.read_factory_settings(use_empty=True)
  make_materials()
  shape = Shape()
  global tag
  tag = Tags(shape)
  tag(*BODY_BONES)
  BODY.loft(shape, M["fur"], rng)
  build_head(shape)
  build_limbs(shape)
  build_tail(shape)
  build_mange(shape)
  dog = shape.finish("dog")
  shade_fur(dog, M, [name for name, _ in FUR_TONES], rng, 0.65, bald, "skin_bald")
  rig(dog, "dog", bones(), tag.ranges())
  bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)


main()
