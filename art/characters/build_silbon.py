# Builds El Silbón, the boss of chapter 1: a starved giant of 3.4 m with arms down to his knees, a
# wide straw hat and the sack with his father's bones in his left hand.
# PLACEHOLDER MESH: plain tubes on the final skeleton, so the animations can be written and
# programmed first. The real model replaces the tubes and keeps every bone name and position.
# Faces -Y with feet on the origin, in A-pose. +X is the character's left.
#   blender --background --python art/characters/build_silbon.py
# It writes the model rigged and without animations; animate_silbon.py adds them.
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "props"))

from beast_tools import Tags, mirrored, rig
from prop_tools import Shape, material

BLEND_PATH = os.path.join(HERE, "silbon.blend")

SHOULDER = (0.36, 0.0, 2.58)
ELBOW = (0.62, 0.0, 1.95)
WRIST = (0.86, -0.03, 1.3)
HAND_END = (0.93, -0.03, 1.16)
FINGER_END = (1.02, -0.03, 0.98)
THUMB_END = (0.88, -0.15, 1.17)
HIP = (0.14, 0.0, 1.75)
KNEE = (0.16, -0.02, 0.95)
ANKLE = (0.17, 0.02, 0.14)
BALL = (0.17, -0.13, 0.05)
TOE = (0.17, -0.3, 0.04)
# Where the left fist holds the neck of the sack; the sack hangs straight down from it.
GRIP = (0.95, -0.03, 1.12)


def flip(point):
  return (-point[0], point[1], point[2])


def bones():
  """Bones as name: (head, tail, parent), for the side +X; _l bones get a mirrored _r twin."""
  return mirrored({
    # Carries root motion, so it sits on the ground and has no vertex weights.
    "root": ((0, 0, 0), (0, 0.2, 0), None),
    "hips": ((0, 0, 1.75), (0, 0, 1.95), "root"),
    "spine": ((0, 0.02, 1.95), (0, 0.02, 2.25), "hips"),
    "chest": ((0, 0.02, 2.25), (0, 0.02, 2.6), "spine"),
    "neck": ((0, 0.04, 2.62), (0, 0.04, 2.85), "chest"),
    "head": ((0, 0.04, 2.85), (0, 0.04, 3.25), "neck"),
    "jaw": ((0, -0.04, 2.95), (0, -0.16, 2.8), "head"),
    "shoulder_l": ((0.08, 0, 2.6), SHOULDER, "chest"),
    "upper_arm_l": (SHOULDER, ELBOW, "shoulder_l"),
    "lower_arm_l": (ELBOW, WRIST, "upper_arm_l"),
    "hand_l": (WRIST, HAND_END, "lower_arm_l"),
    "fingers_l": (HAND_END, FINGER_END, "hand_l"),
    "thumb_l": (WRIST, THUMB_END, "hand_l"),
    "upper_leg_l": (HIP, KNEE, "hips"),
    "lower_leg_l": (KNEE, ANKLE, "upper_leg_l"),
    "foot_l": (ANKLE, BALL, "lower_leg_l"),
    "toes_l": (BALL, TOE, "foot_l"),
    # Points from the neck of the sack to its bottom. The clips swing it like a flail.
    "sack": (GRIP, (GRIP[0], GRIP[1], GRIP[2] - 0.3), "hand_l"),
  })


def reset():
  # Factory settings would also unload the add-ons of a Blender that is open, so only clear the data.
  if bpy.app.background:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return
  for data in (bpy.data.objects, bpy.data.meshes, bpy.data.armatures, bpy.data.materials, bpy.data.actions):
    for item in list(data):
      data.remove(item)


def build_body(shape, tag):
  skin = material("skin", (0.5, 0.54, 0.48))
  cloth = material("cloth", (0.72, 0.67, 0.55))
  straw = material("straw", (0.7, 0.57, 0.28))
  burlap = material("burlap", (0.42, 0.33, 0.2))
  eye = material("eye_glow", (0.85, 0.9, 1.0), glow=3.0)

  tag("hips", "spine", "chest")
  shape.tube([((0, 0, 1.68), 0.2, 0.14), ((0, 0.02, 2.0), 0.16, 0.11), ((0, 0.02, 2.3), 0.22, 0.15), ((0, 0.02, 2.62), 0.32, 0.15)], cloth, n=8)
  tag("neck")
  shape.tube([((0, 0.04, 2.58), 0.07, 0.07), ((0, 0.04, 2.9), 0.065, 0.065)], skin)
  tag("head")
  shape.tube([((0, 0.04, 2.86), 0.09, 0.1), ((0, 0.03, 2.98), 0.14, 0.15), ((0, 0.04, 3.12), 0.15, 0.16), ((0, 0.04, 3.24), 0.11, 0.12)], skin, n=8)
  for sign in (1, -1):
    shape.box((sign * 0.075 - 0.025, -0.14, 3.07), (sign * 0.075 + 0.025, -0.1, 3.11), eye)
  shape.lathe([(0.56, 0.0), (0.54, 0.03), (0.17, 0.06), (0.14, 0.22), (0.03, 0.26)], straw, n=10, at=Matrix.Translation((0, 0.04, 3.19)))
  tag("jaw")
  shape.tube([((0, -0.03, 2.93), 0.08, 0.035), ((0, -0.15, 2.86), 0.045, 0.03)], skin)

  for mirror in (lambda p: p, flip):
    side = "_l" if mirror(SHOULDER)[0] > 0 else "_r"
    tag("upper_arm" + side, "lower_arm" + side)
    shape.tube([(mirror(SHOULDER), 0.07, 0.07), (mirror(ELBOW), 0.05, 0.05), (mirror(WRIST), 0.04, 0.04)], skin)
    tag("hand" + side)
    shape.tube([(mirror(WRIST), 0.04, 0.03), (mirror(HAND_END), 0.06, 0.025)], skin, side=(0, 1, 0))
    tag("fingers" + side)
    for spread in (-0.04, 0.0, 0.04):
      knuckle = Vector(mirror(HAND_END)) + Vector((0, spread, 0))
      tip = Vector(mirror(FINGER_END)) + Vector((0, spread * 1.8, 0))
      shape.tube([(knuckle, 0.018, 0.018), (tip, 0.003, 0.003)], skin, n=4)
    tag("thumb" + side)
    shape.tube([(mirror(WRIST), 0.02, 0.02), (mirror(THUMB_END), 0.004, 0.004)], skin, n=4)
    tag("upper_leg" + side, "lower_leg" + side)
    shape.tube([(mirror(HIP), 0.1, 0.1), (mirror(KNEE), 0.065, 0.065), (mirror(ANKLE), 0.045, 0.045)], cloth)
    tag("foot" + side, "toes" + side)
    shape.tube([(mirror(ANKLE), 0.05, 0.05), (mirror(BALL), 0.07, 0.035), (mirror(TOE), 0.06, 0.02)], skin, side=(1, 0, 0))

  tag("sack")
  grip = Vector(GRIP)
  profile = ((0.0, 0.04), (-0.15, 0.06), (-0.45, 0.26), (-0.8, 0.32), (-1.02, 0.25), (-1.1, 0.1))
  shape.tube([(grip + Vector((0, 0, drop)), radius, radius) for drop, radius in profile], burlap, n=8, side=(1, 0, 0))


def main():
  reset()
  shape = Shape()
  tag = Tags(shape)
  build_body(shape, tag)
  silbon = shape.finish("silbon")
  rig(silbon, "silbon", bones(), tag.ranges())
  bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)


main()
