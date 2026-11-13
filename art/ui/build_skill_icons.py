# Models one relief icon per skill and stat and renders it for the medals of the skill trees.
#   blender --background --python art/ui/build_skill_icons.py
# Saves skill_icons.blend and game/ui/street/skills/<key>.png. Each icon is a flat silhouette raised
# with a bevel of facets, in ink, so it reads as stamped into the gold or tin of a medal.
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "props"))

from build_ui_art import clear_scene, render, setup_render, write
from prop_tools import Shape, material

BLEND_PATH = os.path.join(HERE, "skill_icons.blend")
OUT = os.path.join(HERE, "..", "..", "game", "ui", "street", "skills")
SIZE = 128
INK = (0.24, 0.14, 0.09)
DEPTH = 0.16
BEVEL = 0.12  # How far the top face shrinks in, which gives the lit and shaded facets.


def arc(cx, cz, radius, start, end, steps):
  return [(cx + radius * math.cos(math.radians(start + (end - start) * i / steps)),
           cz + radius * math.sin(math.radians(start + (end - start) * i / steps))) for i in range(steps + 1)]


def band(points, width):
  """A stroke of the given width along an open path, as one closed outline."""
  left, right = [], []
  for i, (x, z) in enumerate(points):
    a = points[max(i - 1, 0)]
    b = points[min(i + 1, len(points) - 1)]
    dx, dz = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dz) or 1.0
    nx, nz = -dz / length * width * 0.5, dx / length * width * 0.5
    left.append((x + nx, z + nz))
    right.append((x - nx, z - nz))
  return left + right[::-1]


def heart():
  right = arc(0.42, 0.32, 0.44, 180, -45, 7)
  left = arc(-0.42, 0.32, 0.44, 225, 0, 7)
  return [(0.0, -0.95)] + right[::-1][:-1] + [(0.0, 0.42)] + left[::-1][1:]


def bolt():
  return [(0.15, 1.0), (-0.55, -0.05), (-0.05, -0.05), (-0.25, -1.0), (0.55, 0.15), (0.05, 0.15), (0.35, 1.0)]


def leaf():
  side = [(0.6 * math.sin(math.pi * t / 8), 1.0 - 1.7 * t / 8) for t in range(1, 8)]
  stem = [(0.08, -0.7), (0.08, -1.0), (-0.08, -1.0), (-0.08, -0.7)]
  return [(0.0, 1.0)] + side + stem + [(-x, z) for x, z in side[::-1]]


def chevrons():
  one = [(-0.9, 0.8), (-0.45, 0.8), (0.05, 0.0), (-0.45, -0.8), (-0.9, -0.8), (-0.4, 0.0)]
  return [one, [(x + 0.85, z) for x, z in one]]


def hourglass():
  return [[(-0.7, 1.0), (0.7, 1.0), (0.7, 0.8), (0.12, 0.05), (0.12, -0.05), (0.7, -0.8), (0.7, -1.0),
           (-0.7, -1.0), (-0.7, -0.8), (-0.12, -0.05), (-0.12, 0.05), (-0.7, 0.8)]]


def fist():
  knuckles = []
  for k in range(4):
    x0 = -0.72 + k * 0.38
    knuckles += [(x0, 0.55), (x0 + 0.06, 0.82), (x0 + 0.3, 0.82), (x0 + 0.36, 0.55)]
  return [(-0.72, -0.35)] + knuckles + [(0.82, 0.3), (0.82, -0.35), (0.45, -0.6), (0.45, -1.0), (-0.45, -1.0), (-0.45, -0.6)]


def machete():
  # A broad blade that widens toward its tip, on a short handle.
  blade = [(-0.45, -0.5), (0.45, 0.05), (0.92, 0.5), (1.0, 0.92), (0.62, 0.95), (0.1, 0.55), (-0.62, -0.12)]
  handle = [(-0.62, -0.12), (-0.45, -0.5), (-0.68, -0.72), (-0.98, -1.0), (-1.08, -0.82), (-0.85, -0.48)]
  return [blade, handle]


def edge():
  blade = [(-0.95, -0.6), (0.55, 0.35), (0.95, 0.95), (0.3, 0.75), (-1.05, -0.2)]
  spark = [(0.35, -0.05), (0.48, -0.35), (0.8, -0.48), (0.48, -0.61), (0.35, -0.95), (0.22, -0.61), (-0.1, -0.48), (0.22, -0.35)]
  return [blade, spark]


def can():
  body = [(-0.6, -1.0), (0.6, -1.0), (0.6, 0.35), (-0.6, 0.35)]
  lid = [(-0.7, 0.35), (0.7, 0.35), (0.7, 0.55), (-0.7, 0.55)]
  drop = [(0.0, 1.05)] + [(0.24 * math.cos(math.radians(a)), 0.72 + 0.24 * math.sin(math.radians(a))) for a in range(-20, -170, -30)]
  return [body, lid, drop]


def flame():
  return [(0.0, 1.0), (0.32, 0.45), (0.62, 0.05), (0.6, -0.5), (0.3, -0.92), (-0.3, -0.92), (-0.6, -0.5), (-0.55, 0.0), (-0.3, 0.3), (-0.12, 0.05)]


def crystal():
  arms = []
  for k in range(6):
    a = math.radians(90 + 60 * k)
    ux, uz = math.cos(a), math.sin(a)
    px, pz = -uz * 0.13, ux * 0.13
    arms.append([(px, pz), (ux * 0.95 + px * 0.5, uz * 0.95 + pz * 0.5), (ux * 1.05, uz * 1.05), (ux * 0.95 - px * 0.5, uz * 0.95 - pz * 0.5), (-px, -pz)])
  return arms


def swoosh():
  outer = arc(0.0, -0.35, 1.1, 160, 20, 9)
  inner = arc(0.15, -0.55, 0.85, 25, 150, 8)
  return [outer + inner]


def boomerang():
  path = arc(0.0, 0.0, 0.75, 210, -100, 12)
  head = [(0.05, -0.55), (0.55, -0.98), (0.6, -0.4)]
  return [band(path, 0.28), head]


def anger():
  marks = []
  for k in range(4):
    a = math.radians(45 + 90 * k)
    ux, uz = math.cos(a), math.sin(a)
    vx, vz = -uz, ux
    c = (ux * 0.55, uz * 0.55)
    arm = [(c[0] + vx * 0.5 - ux * 0.05, c[1] + vz * 0.5 - uz * 0.05), (c[0] - ux * 0.35, c[1] - uz * 0.35), (c[0] - vx * 0.5 - ux * 0.05, c[1] - vz * 0.5 - uz * 0.05)]
    marks.append(band(arm, 0.28))
  return marks


ICONS = {
  "health": heart, "stamina": bolt, "regeneration": leaf, "speed": chevrons, "attack_rate": hourglass, "power": fist,
  "machete": machete, "edge_1": edge, "grease": can, "fire": flame, "ice": crystal, "technique": swoosh,
  "throw": boomerang, "rage": anger,
}


def raise_outline(shape, outline, mat):
  cx = sum(x for x, _ in outline) / len(outline)
  cz = sum(z for _, z in outline) / len(outline)
  def scaled(k):
    return [(cx + (x - cx) * k, cz + (z - cz) * k) for x, z in outline]
  # Sides straight down, then a bevel in to a smaller top: the facets catch the key light.
  rings = [[(x, 0.0, z) for x, z in outline], [(x, -DEPTH, z) for x, z in outline], [(x, -DEPTH - BEVEL * 0.6, z) for x, z in scaled(0.84)]]
  shape.loft(rings, mat)


def main():
  os.makedirs(OUT, exist_ok=True)
  clear_scene()
  camera = setup_render()
  ink = material("ink", INK, 0.55)
  for key, build in ICONS.items():
    parts = build()
    if parts and isinstance(parts[0][0], (int, float)):
      parts = [parts]
    shape = Shape()
    for outline in parts:
      raise_outline(shape, outline, ink)
    obj = shape.finish(key)
    obj.matrix_world = Matrix.Rotation(math.radians(-6), 4, "Z")
    write(render(obj, camera, key, SIZE, span=2.3), os.path.join(OUT, key + ".png"))
  bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)


main()
