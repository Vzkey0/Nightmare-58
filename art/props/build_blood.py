# Builds the blood under Luis where the skeletons feed: one wide pool, a darker clotted middle,
# drops thrown around it and a smear dragged toward the curb.
#   blender --background --python art/props/build_blood.py
# Flat on the ground with its center on the origin; Godot (x, y, z) is Blender (x, -z, y).
import math
import os
import random
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from prop_tools import Shape, material

GLB_PATH = os.path.join(HERE, "..", "..", "game", "models", "props", "blood_pool.glb")


def splat(shape, center, radius, z, mat, rng, sides=14, wobble=0.35, stretch=(1.0, 1.0)):
  """An uneven disc: each rim point pushed in or out, so no two pools look round."""
  rim = []
  phase = rng.uniform(0, math.tau)
  for k in range(sides):
    a = math.tau * k / sides
    r = radius * (1 + wobble * (0.6 * math.sin(3 * a + phase) + 0.4 * rng.uniform(-1, 1)))
    rim.append((center[0] + math.cos(a) * r * stretch[0], center[1] + math.sin(a) * r * stretch[1], z))
  shape.add([(center[0], center[1], z)] + rim, [(0, 1 + k, 1 + (k + 1) % sides) for k in range(sides)], mat)


def build():
  rng = random.Random(58)
  M = {
    "pool": material("blood_pool", (0.42, 0.015, 0.02), roughness=0.2),
    "clot": material("blood_clot", (0.22, 0.005, 0.01), roughness=0.3),
    "smear": material("blood_smear", (0.33, 0.025, 0.025), roughness=0.5),
  }
  shape = Shape()
  # The pool, longer along the body (Y), and its dark heart under the chest.
  splat(shape, (0.0, 0.0), 0.75, 0.004, M["pool"], rng, sides=22, wobble=0.25, stretch=(0.8, 1.25))
  splat(shape, (0.08, 0.15), 0.4, 0.007, M["clot"], rng, sides=16, wobble=0.3, stretch=(0.9, 1.2))
  # Lobes running off the edge, where the street dips.
  for at, r in (((0.62, -0.5), 0.28), ((-0.55, 0.6), 0.22), ((0.3, 0.95), 0.2), ((-0.4, -0.75), 0.25)):
    splat(shape, at, r, 0.0045, M["pool"], rng, sides=12, wobble=0.35)
  # A smear dragged off one side, getting thinner.
  start, end = Vector((0.6, 0.2)), Vector((1.9, -0.3))
  for k in range(7):
    t = k / 6
    p = start.lerp(end, t)
    splat(shape, (p.x, p.y + rng.uniform(-0.04, 0.04)), 0.16 * (1 - 0.7 * t), 0.003, M["smear"], rng, sides=9, wobble=0.3, stretch=(1.6, 0.7))
  # Drops thrown around.
  for _ in range(26):
    a = rng.uniform(0, math.tau)
    d = rng.uniform(0.95, 1.9)
    splat(shape, (math.cos(a) * d * 0.8, math.sin(a) * d * 1.1), rng.uniform(0.02, 0.07), 0.003, M["pool"], rng, sides=7, wobble=0.3)
  return shape.finish("blood_pool")


def main():
  if bpy.app.background:
    bpy.ops.wm.read_factory_settings(use_empty=True)
  obj = build()
  for other in bpy.data.objects:
    other.hide_set(other is not obj)
  os.makedirs(os.path.dirname(GLB_PATH), exist_ok=True)
  bpy.ops.export_scene.gltf(filepath=GLB_PATH, export_format="GLB", use_visible=True)
  for other in bpy.data.objects:
    other.hide_set(False)
  return obj


if __name__ == "__main__":
  main()
