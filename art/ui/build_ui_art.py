# Models the in-game UI pieces low-poly and renders them to small PNGs for Godot.
#   blender --background --python art/ui/build_ui_art.py
# Saves ui_art.blend and game/ui/street/<name>.png. Colors are sRGB, as in the other art scripts.
import math
import os
import random
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "props"))

from prop_tools import Shape, face_up, material

BLEND_PATH = os.path.join(HERE, "ui_art.blend")
OUT = os.path.join(HERE, "..", "..", "game", "ui", "street")

RENDER_SIZE = 256
MARGIN = 1.08

WAX = (0.93, 0.87, 0.7)
WAX_SHADE = (0.8, 0.7, 0.52)
GLASS_RED = (0.72, 0.14, 0.12)
FLAME = (1.0, 0.58, 0.14)
FLAME_CORE = (1.0, 0.9, 0.5)
GOLD = (0.93, 0.7, 0.28)
GOLD_DARK = (0.6, 0.4, 0.14)
GOLD_LIGHT = (1.0, 0.86, 0.5)
TIN = (0.62, 0.6, 0.56)
TIN_DARK = (0.38, 0.36, 0.33)
PLASTER = (1.0, 1.0, 1.0)


def metal(name, color, roughness=0.42):
  mat = material(name, color, roughness)
  next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Metallic"].default_value = 0.55
  return mat


def clear_scene():
  for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj)


def setup_render():
  scene = bpy.context.scene
  scene.render.engine = "CYCLES"
  scene.cycles.samples = 64
  scene.cycles.use_denoising = False
  scene.render.film_transparent = True
  scene.render.resolution_x = RENDER_SIZE
  scene.render.resolution_y = RENDER_SIZE
  scene.render.image_settings.file_format = "PNG"
  scene.render.image_settings.color_mode = "RGBA"
  scene.view_settings.view_transform = "Standard"
  scene.view_settings.look = "None"

  world = bpy.data.worlds.new("ui_world")
  world.use_nodes = True
  background = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
  background.inputs["Color"].default_value = (0.55, 0.5, 0.42, 1)
  background.inputs["Strength"].default_value = 0.8
  scene.world = world

  # Warm key from the top left, like candle light on a wall; the facets read from it.
  for name, energy, rotation, color in (
    ("key", 3.4, (55, 0, -40), (1.0, 0.92, 0.78)),
    ("fill", 0.7, (80, 0, 60), (0.78, 0.9, 0.86)),
  ):
    data = bpy.data.lights.new(name, "SUN")
    data.energy = energy
    data.color = color
    data.angle = math.radians(6)
    sun = bpy.data.objects.new(name, data)
    sun.rotation_euler = tuple(math.radians(value) for value in rotation)
    scene.collection.objects.link(sun)

  data = bpy.data.cameras.new("ui_camera")
  data.type = "ORTHO"
  camera = bpy.data.objects.new("ui_camera", data)
  camera.location = (0, -30, 0)
  camera.rotation_euler = (math.radians(90), 0, 0)
  data.clip_end = 100.0
  scene.collection.objects.link(camera)
  scene.camera = camera
  return camera


def shrink(pixels, factor):
  height, width, channels = pixels.shape
  return pixels.reshape(height // factor, factor, width // factor, factor, channels).mean(axis=(1, 3))


def read(path):
  image = bpy.data.images.load(path)
  image.colorspace_settings.name = "Non-Color"
  width, height = image.size
  pixels = np.empty(width * height * 4, dtype=np.float32)
  image.pixels.foreach_get(pixels)
  bpy.data.images.remove(image)
  return pixels.reshape(height, width, 4).astype(float)


def write(pixels, path):
  height, width, _ = pixels.shape
  image = bpy.data.images.new("out", width, height, alpha=True)
  image.colorspace_settings.name = "Non-Color"
  image.pixels.foreach_set(pixels.ravel().astype(np.float32))
  image.filepath_raw = path
  image.file_format = "PNG"
  image.save()
  bpy.data.images.remove(image)
  print("saved", path, width, height)


def render(obj, camera, name, size, span=None):
  """Frames obj, renders it and halves the render for clean edges."""
  scene = bpy.context.scene
  for other in scene.objects:
    if other.type == "MESH":
      other.hide_render = other is not obj
  points = [obj.matrix_world @ v.co for v in obj.data.vertices]
  low = Vector((min(p.x for p in points), 0, min(p.z for p in points)))
  high = Vector((max(p.x for p in points), 0, max(p.z for p in points)))
  obj.matrix_world = Matrix.Translation(-(low + high) * 0.5) @ obj.matrix_world
  camera.data.ortho_scale = span or max(high.x - low.x, high.z - low.z) * MARGIN
  rendered = os.path.join(bpy.app.tempdir, name + ".png")
  scene.render.filepath = rendered
  bpy.ops.render.render(write_still=True)
  pixels = read(rendered)
  premultiplied = np.dstack((pixels[..., :3] * pixels[..., 3:], pixels[..., 3:]))
  small = shrink(premultiplied, RENDER_SIZE // size)
  covered = np.maximum(small[..., 3:], 1e-5)
  small[..., :3] = np.clip(small[..., :3] / covered, 0.0, 1.0)
  return small


def hard_shadow(pixels, offset):
  """A copy of the silhouette pushed down and right, in ink, without blur: the shadow style of the UI."""
  shadow = np.zeros_like(pixels)
  shadow[:-offset, offset:, 3] = pixels[offset:, :-offset, 3] * 0.7
  over = pixels[..., 3:]
  color = pixels[..., :3] * over + np.array((0.12, 0.07, 0.05)) * shadow[..., 3:] * (1 - over)
  alpha = over + shadow[..., 3:] * (1 - over)
  return np.dstack((color / np.maximum(alpha, 1e-5), alpha))


def build_candle():
  """A votive in red glass with its flame: the cursor of every menu."""
  shape = Shape()
  glass = material("glass_red", GLASS_RED, 0.3)
  wax = material("wax", WAX)
  wax_shade = material("wax_shade", WAX_SHADE)
  flame = material("flame", FLAME, glow=6.0)
  core = material("flame_core", FLAME_CORE, glow=9.0)
  shape.lathe([(0.0, 0.0), (0.42, 0.0), (0.48, 0.12), (0.46, 0.7), (0.0, 0.7)], glass, n=7)
  shape.lathe([(0.0, 0.7), (0.36, 0.7), (0.0, 0.74)], wax, n=7)
  shape.lathe([(0.0, 0.72), (0.14, 0.82), (0.17, 0.98), (0.1, 1.2), (0.0, 1.46)], flame, n=5, turn=0.3)
  shape.lathe([(0.0, 0.78), (0.07, 0.86), (0.08, 0.98), (0.0, 1.12)], core, n=5, at=Matrix.Translation((0, -0.12, 0)))
  obj = shape.finish("candle")
  obj.matrix_world = Matrix.Rotation(math.radians(12), 4, "X") # Tipped toward the eye to show the wax.
  return obj


def build_medal(name, face, rim, light, cross=True):
  """An oval saint's medal with a faceted rim, and a raised cross unless a skill's mark goes on it."""
  shape = Shape()
  face_mat = metal(name + "_face", face)
  rim_mat = metal(name + "_rim", rim)
  light_mat = metal(name + "_light", light, 0.3)
  n = 10
  squash = Matrix.Scale(0.82, 4, Vector((1, 0, 0)))
  # Rings from the outer edge in: rim up, rim down, then the low face.
  profile = [(1.0, 0.0), (1.0, 0.1), (0.9, 0.22), (0.8, 0.18), (0.76, 0.1), (0.0, 0.14)]
  pick = lambda band, side: (light_mat if side in (3, 4, 5) else rim_mat) if band < 3 else face_mat
  shape.lathe(profile, pick, n=n, at=squash @ face_up(), turn=math.pi / n)
  # The loop it hangs from.
  shape.lathe([(0.0, 0.0), (0.14, 0.0), (0.14, 0.12), (0.0, 0.12)], rim_mat, n=6, at=Matrix.Translation((0, -0.06, 1.06)) @ face_up())
  # A cross in relief, each arm a faceted bar.
  for low, high in () if not cross else (((-0.09, -0.28, -0.5), (0.09, -0.16, 0.5)), ((-0.32, -0.28, 0.08), (0.32, -0.16, 0.24))):
    x0, y0, z0 = low
    x1, y1, z1 = high
    ridge = (y0 - 0.06)
    shape.extrude([(x0, z0), (x1, z0), (x1, z1), (x0, z1)], y0, y1, light_mat)
    mid_x = (x0 + x1) * 0.5
    mid_z = (z0 + z1) * 0.5
    long_x = (x1 - x0) > (z1 - z0)
    top = [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)]
    if long_x:
      a, b = (x0 + 0.06, ridge, mid_z), (x1 - 0.06, ridge, mid_z)
      shape.add(top + [a, b], [(0, 1, 5, 4), (1, 2, 5), (2, 3, 4, 5), (3, 0, 4)], [light_mat, rim_mat, rim_mat, light_mat])
    else:
      a, b = (mid_x, ridge, z0 + 0.06), (mid_x, ridge, z1 - 0.06)
      shape.add(top + [a, b], [(0, 1, 4), (1, 2, 5, 4), (2, 3, 5), (3, 0, 4, 5)], [rim_mat, rim_mat, light_mat, light_mat])
  return shape.finish(name)


def build_frame():
  """A square gilded frame of bevelled facets, cut at the corners: drawn as a nine-patch in Godot."""
  shape = Shape()
  dark = metal("frame_dark", GOLD_DARK)
  mid = metal("frame_mid", GOLD)
  light = metal("frame_light", GOLD_LIGHT, 0.3)

  def ring(half, cut, depth):
    return [(x, depth, z) for x, z in (
      (-half + cut, -half), (half - cut, -half), (half, -half + cut), (half, half - cut),
      (half - cut, half), (-half + cut, half), (-half, half - cut), (-half, -half + cut))]

  rings = [ring(1.0, 0.18, 0.0), ring(0.96, 0.17, -0.08), ring(0.88, 0.15, -0.12), ring(0.8, 0.12, -0.04), ring(0.78, 0.12, 0.0)]
  # Sides 0..7 run bottom, bottom-right, right, ... so the lit ones face the top-left key.
  lit = {3, 4, 5, 6}

  def pick(band, side):
    if band == 1:
      return light if side in lit else dark
    if band == 2:
      return mid if side in lit else dark
    return mid

  shape.loft(rings, pick, caps=(False, False))
  return shape.finish("frame")


def build_plaster():
  """A tileable patch of faceted plaster seen from the front: the grain of every panel."""
  rng = random.Random(58)
  cells = 11
  step = 2.0 / cells
  heights = [[rng.uniform(-0.05, 0.05) for _ in range(cells)] for _ in range(cells)]
  jitter = [[(rng.uniform(-0.3, 0.3) * step, rng.uniform(-0.3, 0.3) * step) for _ in range(cells)] for _ in range(cells)]
  shape = Shape()
  mat = material("plaster", PLASTER, 0.95)
  verts = []
  # One extra ring repeats the first, so the patch wraps without a seam.
  for row in range(cells + 1):
    for col in range(cells + 1):
      dx, dz = jitter[row % cells][col % cells]
      verts.append((-1 + col * step + dx, heights[row % cells][col % cells], -1 + row * step + dz))
  faces = []
  for row in range(cells):
    for col in range(cells):
      a = row * (cells + 1) + col
      b, c, d = a + 1, a + cells + 2, a + cells + 1
      faces += [(a, b, c), (a, c, d)] if (row + col) % 2 else [(a, b, d), (b, c, d)]
  # The patch is drawn three times wide so its edges are covered whatever the jitter.
  for ox in (-2, 0, 2):
    for oz in (-2, 0, 2):
      shape.add(verts, faces, mat, at=Matrix.Translation((ox, 0, oz)))
  return shape.finish("plaster")


def main():
  os.makedirs(OUT, exist_ok=True)
  clear_scene()
  camera = setup_render()

  candle = build_candle()
  write(hard_shadow(render(candle, camera, "candle", 64), 3), os.path.join(OUT, "candle.png"))

  gold = build_medal("medal_gold", GOLD, GOLD_DARK, GOLD_LIGHT)
  write(hard_shadow(render(gold, camera, "medal_gold", 128), 4), os.path.join(OUT, "medal_gold.png"))
  tin = build_medal("medal_tin", TIN, TIN_DARK, TIN)
  write(hard_shadow(render(tin, camera, "medal_tin", 128), 4), os.path.join(OUT, "medal_tin.png"))

  for name, colors in (("medal_gold_plain", (GOLD, GOLD_DARK, GOLD_LIGHT)), ("medal_tin_plain", (TIN, TIN_DARK, TIN))):
    plain = build_medal(name, *colors, cross=False)
    write(hard_shadow(render(plain, camera, name, 128), 4), os.path.join(OUT, name + ".png"))

  frame = build_frame()
  write(render(frame, camera, "frame", 128, span=2.0), os.path.join(OUT, "frame.png"))

  plaster = build_plaster()
  bpy.context.scene.render.film_transparent = False
  pixels = render(plaster, camera, "plaster", 128, span=2.0)
  # Only the light on the facets is kept, centered just under white, so tinting a panel stays close to its color.
  value = pixels[..., :3].mean(axis=2)
  value = (value - value.mean()) / max(value.std(), 1e-5)
  value = np.clip(0.94 + value * 0.02, 0.0, 1.0)
  write(np.dstack((value, value, value, np.ones_like(value))), os.path.join(OUT, "plaster.png"))

  bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)


if __name__ == "__main__":
  main()
