"""Paints the male protagonist into one texture. Run it after build_protagonist.py:

  blender --background art/characters/protagonist.blend --python art/characters/paint_protagonist.py

Everything is painted by position on the body, not by UV, so seams can't show and the unwrap can
change freely. Cycles bakes position, normal, region and occlusion into the atlas; the paint is
then computed for each texel, in the same order a painter works: flat colors, details, form
shadows in a few broken bands, and brush noise.

+X is the character's left, the front looks at -Y, and colors are sRGB, as a painter picks them.
"""

import math

import bpy
import numpy as np
from mathutils import Quaternion

SIZE = 2048
MARGIN = 8
AO_SAMPLES = 96
# Texture density by region: the face is seen up close on the title screen.
UV_SCALE = {"head_skin": 2.7, "skin_tan": 1.9, "boot_leather": 0.8, "boot_sole": 0.6, "hair_lock": 0.8, "pants_black": 0.8}

JACKET_YELLOW = (0.97, 0.74, 0.11)
JACKET_BLUE = (0.09, 0.15, 0.56)
JACKET_RED = (0.76, 0.08, 0.11)
WHITE = (0.94, 0.93, 0.89)
# Multiplies the color in shadow. Shadows lean cool on cloth and warm on skin, never plain black.
SHADOW_TINT = {
  "skin_tan": (0.5, 0.3, 0.3), "head_skin": (0.5, 0.3, 0.3), "white": (0.54, 0.58, 0.74),
  "tee_rib": (0.54, 0.58, 0.74), "jacket_shell": (0.42, 0.34, 0.56), "jacket_sleeve": (0.42, 0.34, 0.56),
  "jacket_lining": (0.4, 0.3, 0.4), "pants_black": (0.5, 0.52, 0.62), "hair_lock": (0.5, 0.42, 0.5),
}
DEFAULT_SHADOW = (0.46, 0.42, 0.54)

rng = np.random.default_rng(58)
lattice = rng.random((64, 64, 64), dtype=np.float32)


def sstep(edge0, edge1, value):
  t = np.clip((value - edge0) / (edge1 - edge0), 0.0, 1.0)
  return t * t * (3 - 2 * t)


def mix(a, b, amount):
  amount = np.asarray(amount)[..., None] if np.ndim(amount) else amount
  return np.asarray(a, dtype=np.float32) * (1 - amount) + np.asarray(b, dtype=np.float32) * amount


def over(color, tint, mask):
  """Paints tint where mask is 1, in place on a selection."""
  color[:] = mix(color, tint, mask)


def noise(points, scale):
  """Tiling value noise in [0, 1]; scale is one number or one per axis."""
  p = points * np.asarray(scale, dtype=np.float32)
  cell = np.floor(p).astype(np.int32)
  t = p - cell
  t = t * t * (3 - 2 * t)
  a = cell & 63
  b = (cell + 1) & 63
  result = 0.0
  for pick_x, weight_x in ((a[:, 0], 1 - t[:, 0]), (b[:, 0], t[:, 0])):
    for pick_y, weight_y in ((a[:, 1], 1 - t[:, 1]), (b[:, 1], t[:, 1])):
      for pick_z, weight_z in ((a[:, 2], 1 - t[:, 2]), (b[:, 2], t[:, 2])):
        result = result + lattice[pick_x, pick_y, pick_z] * weight_x * weight_y * weight_z
  return result


def fractal(points, scale, octaves=3):
  scale = np.asarray(scale, dtype=np.float32)
  total = 0.0
  amplitude = 1.0
  norm = 0.0
  for octave in range(octaves):
    total = total + noise(points + 13.7 * octave, scale * 2 ** octave) * amplitude
    norm += amplitude
    amplitude *= 0.5
  return total / norm


def blur(image, passes):
  """Box blur on the atlas: it softens baked occlusion, and the UV margin hides the islands' edges."""
  for _ in range(passes):
    image = (
      image + np.roll(image, 1, 0) + np.roll(image, -1, 0) + np.roll(image, 1, 1) + np.roll(image, -1, 1)
    ) / 5
  return image


def unwrap(body):
  mesh = body.data
  bpy.context.view_layer.objects.active = body
  body.select_set(True)
  bpy.ops.object.mode_set(mode="EDIT")
  bpy.ops.mesh.select_all(action="SELECT")
  bpy.ops.uv.smart_project(angle_limit=math.radians(58), island_margin=0.0, scale_to_bounds=False)
  bpy.ops.object.mode_set(mode="OBJECT")
  regions = list(body["regions"])
  region = mesh.attributes["region"].data
  uv = mesh.uv_layers.active.uv
  for polygon in mesh.polygons:
    factor = UV_SCALE.get(regions[int(region[polygon.index].value) - 1], 1.0)
    for loop in polygon.loop_indices:
      uv[loop].vector *= factor
  bpy.ops.object.mode_set(mode="EDIT")
  bpy.ops.mesh.select_all(action="SELECT")
  bpy.ops.uv.select_all(action="SELECT")
  bpy.ops.uv.pack_islands(margin=2.0 * MARGIN / SIZE, rotate=True, shape_method="CONCAVE")
  bpy.ops.object.mode_set(mode="OBJECT")


class Baker:
  def __init__(self, body):
    self.body = body
    self.material = bpy.data.materials.get("paint_bake") or bpy.data.materials.new("paint_bake")
    self.material.use_nodes = True
    tree = self.material.node_tree
    tree.nodes.clear()
    self.tree = tree
    self.emission = tree.nodes.new("ShaderNodeEmission")
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    tree.links.new(self.emission.outputs[0], output.inputs["Surface"])
    self.target = tree.nodes.new("ShaderNodeTexImage")
    tree.nodes.active = self.target
    body.data.materials.clear()
    body.data.materials.append(self.material)
    body.data.polygons.foreach_set("material_index", np.zeros(len(body.data.polygons), dtype=np.int32))
    image = bpy.data.images.get("paint_bake_target")
    if image:
      bpy.data.images.remove(image)
    self.image = bpy.data.images.new("paint_bake_target", SIZE, SIZE, alpha=True, float_buffer=True)
    self.image.colorspace_settings.name = "Non-Color"
    self.target.image = self.image

  def read(self):
    pixels = np.empty(SIZE * SIZE * 4, dtype=np.float32)
    self.image.pixels.foreach_get(pixels)
    return pixels.reshape(SIZE, SIZE, 4)[..., :3].copy()

  def emit(self, node_type, output, attribute=None):
    node = self.tree.nodes.new(node_type)
    if attribute:
      node.attribute_name = attribute
    self.tree.links.new(node.outputs[output], self.emission.inputs["Color"])
    bpy.ops.object.bake(type="EMIT", margin=MARGIN, margin_type="EXTEND", use_clear=True)
    self.tree.nodes.remove(node)
    return self.read()

  def occlusion(self, distance):
    bpy.context.scene.world.light_settings.distance = distance
    bpy.ops.object.bake(type="AO", margin=MARGIN, margin_type="EXTEND", use_clear=True)
    return self.read()[..., 0]


def spread_arms(armature, degrees):
  """Occlusion is baked with the arms out: in the A-pose they would print a shadow on the chest."""
  for side, sign in (("_l", 1), ("_r", -1)):
    bone = armature.pose.bones["upper_arm" + side]
    rest = bone.bone.matrix_local.to_quaternion()
    bone.rotation_mode = "QUATERNION"
    bone.rotation_quaternion = rest.inverted() @ Quaternion((0, 1, 0), math.radians(-sign * degrees)) @ rest


def setup_cycles():
  scene = bpy.context.scene
  scene.render.engine = "CYCLES"
  scene.cycles.samples = AO_SAMPLES
  scene.cycles.use_denoising = False
  scene.render.bake.target = "IMAGE_TEXTURES"
  scene.render.bake.use_selected_to_active = False
  if not scene.world:
    scene.world = bpy.data.worlds.new("paint_world")


def digit_mask(u, z, left, bottom, width, height, thick, segments):
  """Block digit as in old jerseys; each letter of segments is one bar."""
  right = left + width
  top = bottom + height
  middle = bottom + height / 2
  def box(x0, x1, z0, z1):
    return (u >= x0) & (u <= x1) & (z >= z0) & (z <= z1)
  mask = np.zeros(u.shape, dtype=bool)
  for code in segments:
    if code == "t":
      mask |= box(left, right, top - thick, top)
    elif code == "b":
      mask |= box(left, right, bottom, bottom + thick)
    elif code == "m":
      mask |= box(left, right, middle - thick / 2, middle + thick / 2)
    elif code == "l":
      mask |= box(left, left + thick, middle, top)
    elif code == "L":
      mask |= box(left, left + thick, bottom, top)
    elif code == "c":
      mask |= box(right - thick, right, middle, top)
    elif code == "r":
      mask |= box(right - thick, right, bottom, middle)
  return mask


def star_mask(u, v, center_u, center_v, radius, feather):
  """Five-point star, tip up, as a soft mask."""
  du = u - center_u
  dv = v - center_v
  r = np.hypot(du, dv)
  sector = math.tau / 5
  angle = np.arctan2(du, dv)
  folded = np.abs((angle + sector / 2) % sector - sector / 2)
  inner = radius * 0.4
  # Line from the tip to the notch, measured in the folded wedge.
  tip = np.array([radius, 0.0])
  notch = np.array([inner * math.cos(sector / 2), inner * math.sin(sector / 2)])
  edge = notch - tip
  normal = np.array([edge[1], -edge[0]]) / np.linalg.norm(edge)
  px = r * np.cos(folded) - tip[0]
  py = r * np.sin(folded) - tip[1]
  return sstep(-feather, feather, -(px * normal[0] + py * normal[1]))


def band_edges(angle, y):
  """Heights of the flag stripes: they drop towards the front zip, as a chevron."""
  drop = np.where(y < 0, 1 - np.abs(np.sin(angle)), 0.0)
  return 1.325 - 0.06 * drop, 1.165 - 0.075 * drop


def paint_jacket(color, pos):
  x, y, z = pos[:, 0], pos[:, 1], pos[:, 2]
  angle = np.arctan2(x, -y)
  upper, lower = band_edges(angle, y)
  wobble = (fractal(pos, 24, 2) - 0.5) * 0.004
  color[:] = JACKET_RED
  over(color, JACKET_BLUE, sstep(-0.0015, 0.0015, z + wobble - lower))
  over(color, JACKET_YELLOW, sstep(-0.0015, 0.0015, z + wobble - upper))
  # Thin white piping between the colors, as on a track jacket.
  piping = (np.abs(z - upper) < 0.0035) | (np.abs(z - lower) < 0.0035)
  over(color, WHITE, piping)

  radius = 0.2
  u = angle * radius
  # Eight stars, as on the flag: three per chest side, one per sleeve. The back repeats them.
  for sign in (1, -1):
    for degrees in (31, 49, 67):
      center = math.radians(degrees) * sign
      height = 1.245 - 0.0675 * (1 - abs(math.sin(center)))
      over(color, WHITE, star_mask(u, z, center * radius, height, 0.028, 0.0012) * (y < 0))
    for degrees in (118, 138, 158):
      center = math.radians(degrees) * sign
      over(color, WHITE, star_mask(u, z, center * radius, 1.245, 0.028, 0.0012) * (y > 0))

  # 58 across the back, big enough to read from the camera behind him.
  v = -x
  for digit, left, segments in ((0, -0.122, "tlmrb"), (1, 0.012, "tLcrbm")):
    shade = digit_mask(v - 0.005, z + 0.005, left, 0.94, 0.11, 0.185, 0.031, segments) & (y > 0)
    over(color, (0.42, 0.04, 0.07), shade)
    over(color, WHITE, digit_mask(v, z, left, 0.94, 0.11, 0.185, 0.031, segments) & (y > 0))

  # Flag patch on the left chest, with a white border and its arc of stars.
  left, right, top, stripe = 0.1, 0.176, 1.432, 0.0175
  patch = (y < 0) & (x > left - 0.005) & (x < right + 0.005) & (z < top + 0.005) & (z > top - 3 * stripe - 0.005)
  over(color, WHITE, patch)
  inner = (y < 0) & (x > left) & (x < right) & (z < top) & (z > top - 3 * stripe)
  for i, tint in enumerate((JACKET_YELLOW, JACKET_BLUE, JACKET_RED)):
    over(color, tint, inner & (z <= top - i * stripe) & (z > top - (i + 1) * stripe))
  for i in range(8):
    a = math.radians(155 - i * 130 / 7)
    px = (left + right) / 2 + 0.024 * math.cos(a)
    pz = top - 2.1 * stripe + 0.02 * math.sin(a)
    over(color, WHITE, inner & (np.hypot(x - px, z - pz) < 0.0026))

  # Side seam with dashed stitching.
  seam = np.abs(np.abs(angle) - math.pi / 2)
  over(color, color * 0.62, sstep(0.0035, 0.0015, seam * 0.2))
  stitch = (np.abs(seam * 0.2 - 0.008) < 0.0011) & ((z * 110) % 1 < 0.6)
  over(color, color * 0.72 + 0.12, stitch)
  # Stitching follows the front edge and the hem.
  over(color, color * 0.78 + 0.1, (np.abs(z - 0.59) < 0.0012) & ((np.abs(x) * 90) % 1 < 0.6))


def paint_sleeve(color, pos):
  x, z = np.abs(pos[:, 0]), pos[:, 2]
  # Measured along the arm, so the stripes cross it square.
  along = (x - 0.19) * 0.32 + (1.38 - z) * 0.95
  color[:] = JACKET_RED
  over(color, JACKET_BLUE, sstep(0.0015, -0.0015, along - 0.215))
  over(color, JACKET_YELLOW, sstep(0.0015, -0.0015, along - 0.09))
  piping = (np.abs(along - 0.215) < 0.0035) | (np.abs(along - 0.09) < 0.0035)
  over(color, WHITE, piping)
  # The sleeve star sits on the outside of the arm.
  over(color, WHITE, star_mask(pos[:, 1], along, 0.0, 0.153, 0.027, 0.0012) * (x > 0.2))


def paint_zipper(color, pos):
  z = pos[:, 2]
  color[:] = (0.13, 0.14, 0.19)
  teeth = (z * 150) % 1 < 0.5
  over(color, (0.4, 0.41, 0.42), teeth * 0.6)


def paint_tee(color, pos):
  color[:] = WHITE
  # Loose folds that hang from the chest and gather at the belt.
  slanted = pos + pos[:, [2, 2, 0]] * (0.7, 0, 0)
  pull = fractal(slanted, (34, 34, 7), 2)
  gather = sstep(1.2, 1.02, pos[:, 2])
  over(color, (0.72, 0.75, 0.84), sstep(0.53, 0.66, pull) * (0.3 + 0.5 * gather))
  over(color, (0.82, 0.84, 0.88), sstep(0.5, 0.7, fractal(pos, (9, 9, 5), 2)) * 0.5)


def paint_pants(color, pos, normal):
  z = pos[:, 2]
  color[:] = (0.13, 0.135, 0.165)
  # Wrinkles gather behind the knee, at the ankle and at the crotch.
  stretched = fractal(pos, (9, 9, 95), 2)
  gathered = np.clip(np.exp(-((z - 0.5) / 0.045) ** 2) + np.exp(-((z - 0.235) / 0.04) ** 2), 0, 1)
  over(color, (0.24, 0.25, 0.3), sstep(0.56, 0.7, stretched) * gathered * 0.8)
  over(color, (0.07, 0.07, 0.09), sstep(0.44, 0.3, stretched) * gathered * 0.7)
  # Worn cloth lightens over the knee and the shin.
  worn = np.exp(-((z - 0.5) / 0.08) ** 2) * (normal[:, 1] < -0.3)
  over(color, (0.24, 0.25, 0.3), worn * 0.45 * fractal(pos, 30, 3))


def paint_hair(color, pos, panel):
  across, along, seed = panel[:, 0], panel[:, 1], panel[:, 2]
  # Strands run the length of each lock, so the noise barely changes along it.
  strand_space = np.stack((across * 1.4, along * 0.5, seed * 41.0), axis=1)
  streak = fractal(strand_space, (4.5, 1.2, 1), 2)
  color[:] = mix((0.075, 0.05, 0.05), (0.2, 0.125, 0.085), sstep(0.1, 0.62, along))
  # A band of light across the hair, broken by the strands.
  sheen = np.exp(-((along - 0.42) / 0.13) ** 2) * (1 - 0.6 * across) * sstep(0.32, 0.62, streak)
  over(color, (0.44, 0.29, 0.2), sheen * 0.75)
  over(color, (0.045, 0.03, 0.03), sstep(0.5, 0.3, streak) * 0.55)
  # Lighter tips, as he always wore them.
  tips = sstep(0.64, 0.96, along + (streak - 0.5) * 0.35)
  over(color, mix((0.72, 0.5, 0.26), (0.92, 0.76, 0.48), sstep(0.8, 1.0, along)), tips)


def paint_skin(color, pos):
  x, z = pos[:, 0], pos[:, 2]
  blush = fractal(pos, 14, 2)
  over(color, (0.76, 0.42, 0.33), sstep(0.5, 0.75, blush) * 0.22)
  over(color, (0.82, 0.6, 0.46), sstep(0.5, 0.25, blush) * 0.16)
  # Knuckles and fingertips run redder.
  over(color, (0.74, 0.38, 0.3), sstep(0.84, 0.76, z) * 0.35 * (np.abs(x) > 0.3))


def paint_head(color, pos):
  x, y, z = pos[:, 0], pos[:, 1], pos[:, 2]
  side = np.abs(x)
  paint_skin(color, pos)
  # Warmth across the nose and cheeks, cool in the temples, as in the painted reference.
  over(color, (0.78, 0.42, 0.34), np.exp(-((side - 0.05) / 0.035) ** 2 - ((z - 1.625) / 0.024) ** 2) * 0.32)
  over(color, (0.78, 0.42, 0.34), np.exp(-(x / 0.014) ** 2 - ((z - 1.628) / 0.02) ** 2) * 0.28)
  # Form shadows the low mesh can't cast: eye sockets, under the nose, lower lip, jaw.
  shade = (0.34, 0.2, 0.17)
  over(color, shade, np.exp(-((side - 0.04) / 0.032) ** 2 - ((z - 1.672) / 0.0085) ** 2) * 0.34)
  over(color, shade, np.exp(-(x / 0.018) ** 2 - ((z - 1.607) / 0.0055) ** 2) * 0.42)
  over(color, shade, np.exp(-(x / 0.024) ** 2 - ((z - 1.57) / 0.0048) ** 2) * 0.34)
  over(color, shade, sstep(0.05, 0.095, side) * sstep(1.62, 1.565, z) * 0.45)
  over(color, (0.84, 0.62, 0.48), np.exp(-(x / 0.0085) ** 2 - ((z - 1.635) / 0.024) ** 2) * 0.3)
  over(color, (0.86, 0.66, 0.5), np.exp(-((side - 0.066) / 0.014) ** 2 - ((z - 1.636) / 0.0085) ** 2) * 0.3)

  # Short beard: stipple along the jaw, with a mustache and a goatee in the solid color.
  beard_color = (0.17, 0.11, 0.09)
  stipple = fractal(pos, 520, 2)
  jaw = sstep(1.606, 1.585, z - 0.28 * np.maximum(side - 0.04, 0)) * sstep(0.022, 0.05, side + 0.6 * (1.6 - z))
  over(color, beard_color, jaw * (0.34 + 0.34 * stipple))
  upper_lip = np.abs(z - 1.6015 + 0.3 * side) < 0.0036 + 0.002 * (1 - side / 0.03)
  over(color, beard_color, upper_lip * (side < 0.03) * (0.72 + 0.2 * stipple))
  over(color, beard_color, sstep(0.021, 0.015, side) * sstep(1.547, 1.553, z) * sstep(1.577, 1.572, z) * (0.74 + 0.2 * stipple))

  # Mouth.
  mouth = 1.5868 - 3.5 * side ** 2
  over(color, (0.44, 0.22, 0.2), (side < 0.0265) * sstep(0.0, 0.002, z - mouth) * sstep(0.0065, 0.004, z - mouth + 40 * side ** 2 * 0.1))
  over(color, (0.62, 0.36, 0.3), (side < 0.021) * sstep(0.0, -0.0015, z - mouth) * sstep(-0.0085, -0.0065, z - mouth))
  over(color, (0.78, 0.52, 0.44), np.exp(-(x / 0.012) ** 2 - ((z - mouth + 0.0052) / 0.0016) ** 2) * 0.5)
  over(color, (0.15, 0.07, 0.07), sstep(0.0012, 0.0004, np.abs(z - mouth)) * (side < 0.0275))
  # Nostrils.
  nostril = np.exp(-((side - 0.0098) / 0.0042) ** 2 - ((z - 1.6185) / 0.0024) ** 2)
  over(color, (0.18, 0.09, 0.08), sstep(0.3, 0.7, nostril) * 0.8)

  # Brows, thick and slanted towards the nose: they carry his expression.
  brow_z = 1.6815 + 0.0095 * sstep(0.012, 0.06, side) - 0.012 * sstep(0.06, 0.086, side)
  thickness = 0.0078 * (1 - 0.72 * sstep(0.05, 0.086, side))
  strands = fractal(pos, (420, 420, 120), 2)
  brow = sstep(thickness, thickness * 0.72, np.abs(z - brow_z)) * sstep(0.0095, 0.014, side) * sstep(0.087, 0.08, side)
  over(color, (0.075, 0.05, 0.05), brow * (0.72 + 0.4 * strands))

  paint_eyes(color, x, y, z)

  # Hair painted on the skull, under the locks, with a broken hairline.
  angle = np.degrees(np.abs(np.arctan2(x, -y)))
  hairline = np.interp(angle, (0, 40, 70, 88, 100, 130, 180), (1.744, 1.736, 1.722, 1.69, 1.655, 1.59, 1.56))
  edge = (fractal(pos, 90, 2) - 0.5) * 0.016
  over(color, (0.09, 0.06, 0.055), sstep(-0.004, 0.004, z - hairline + edge))


def paint_eyes(color, x, y, z):
  side = np.abs(x)
  eye_x, eye_z = 0.0432, 1.6585
  half = 0.0242
  front = y < 0
  # Slightly lifted at the outer corner.
  u = np.clip((side - eye_x) / half, -1.3, 1.3)
  v = z - eye_z - 0.0028 * u
  shape = np.clip(1 - u * u, 0.0, 1.0)
  upper = 0.0118 * shape ** 0.62 * (1 - 0.14 * u)
  lower = -0.0072 * shape ** 0.72
  eye = sstep(-0.0005, 0.0003, upper - v) * sstep(-0.0005, 0.0003, v - lower) * (np.abs(u) < 1) * front

  over(color, (0.9, 0.88, 0.84), eye)
  # Light comes from one side, so the catchlight doesn't mirror.
  iris_x = eye_x + 0.0006
  iris_z = eye_z + 0.0012
  distance = np.hypot(side - iris_x, z - iris_z)
  iris = sstep(0.0112, 0.0104, distance) * eye
  depth = sstep(0.0035, 0.0108, distance)
  lit = sstep(1.0, -1.0, (z - iris_z) / 0.0105)
  iris_color = mix(mix((0.3, 0.16, 0.08), (0.62, 0.37, 0.13), lit), (0.08, 0.045, 0.03), depth ** 2.5)
  color[:] = color * (1 - iris[:, None]) + iris_color * iris[:, None]
  over(color, (0.03, 0.02, 0.02), sstep(0.0056, 0.0049, distance) * eye)
  # Shadow from the lid across the top of the eye.
  over(color, (0.16, 0.11, 0.12), sstep(0.0058, 0.0, upper - v) * eye * 0.72)
  glint_x = np.where(x > 0, eye_x - 0.0036, eye_x + 0.0036)
  over(color, (1.0, 0.98, 0.94), sstep(0.0026, 0.0019, np.hypot(side - glint_x, z - iris_z - 0.0044)) * eye)
  over(color, (0.92, 0.86, 0.8), sstep(0.0013, 0.0009, np.hypot(side - glint_x - 0.0072 * np.sign(x), z - iris_z + 0.0046)) * eye * 0.7)

  # Lash line, heavy on top and running past the outer corner.
  wing = (u > -1.06) & (u < 1.22) & front
  lid = np.maximum(upper, 0.0) + 0.0016 * sstep(1.0, 1.2, u)
  over(color, (0.07, 0.045, 0.045), sstep(0.0024, 0.0016, np.abs(v - lid - 0.0009)) * wing)
  over(color, (0.24, 0.13, 0.11), sstep(0.0011, 0.0006, np.abs(v - lower + 0.0004)) * (np.abs(u) < 1) * front * 0.8)
  # Fold of the eyelid.
  over(color, (0.36, 0.2, 0.17), sstep(0.0011, 0.0005, np.abs(v - upper - 0.0058)) * (np.abs(u) < 0.95) * front * 0.55)


def shade(color, names, region, pos, normal, occlusion, contact):
  """Form shadows in a few broken bands, which is what makes it read as gouache and not as a render."""
  strokes = fractal(pos + normal * 0.03, (26, 26, 9), 3)
  # A soft key light from above and to one side: it is what draws the folds of the coat.
  key = normal @ np.array((-0.34, -0.53, 0.78), dtype=np.float32)
  light = occlusion * (0.6 + 0.4 * contact) + (strokes - 0.5) * 0.16 + 0.26 * (key - 0.2)
  deep = sstep(0.2, 0.4, light)
  mid = sstep(0.46, 0.64, light)
  high = sstep(0.8, 0.94, light + 0.1 * normal[:, 2])
  value = 0.42 + 0.26 * deep + 0.26 * mid + 0.06 * high
  tints = np.array([SHADOW_TINT.get(name, DEFAULT_SHADOW) for name in names], dtype=np.float32)[region]
  amount = ((1 - value) / 0.58)[:, None]
  shaded = color * (1 - amount * (1 - tints))
  # Pure brush variation, so flat areas don't look printed.
  grain = fractal(pos, (70, 70, 24), 2)[:, None]
  return shaded * (0.95 + 0.1 * grain)


def paint(body, maps):
  names = list(body["regions"])
  palette = body["palette"]
  region_map, pos_map, normal_map, panel_map, occlusion_map, contact_map = maps
  region_index = np.rint(region_map[..., 0]).astype(np.int32) - 1
  mask = region_index >= 0
  region = region_index[mask]
  pos = pos_map[mask]
  normal = normal_map[mask]
  panel = panel_map[mask]
  occlusion = blur(occlusion_map, 2)[mask]
  contact = blur(contact_map, 1)[mask]
  color = np.array([tuple(palette[name]) for name in names], dtype=np.float32)[region]

  def pick(name):
    return np.nonzero(region == names.index(name))[0] if name in names else np.zeros(0, dtype=np.int64)

  for name, painter, extra in (
    ("jacket_shell", paint_jacket, ()),
    ("jacket_sleeve", paint_sleeve, ()),
    ("zipper_tape", paint_zipper, ()),
    ("white", paint_tee, ()),
    ("pants_black", paint_pants, (normal,)),
    ("hair_lock", paint_hair, (panel,)),
    ("skin_tan", paint_skin, ()),
    ("head_skin", paint_head, ()),
  ):
    picked = pick(name)
    if picked.size:
      local = color[picked]
      painter(local, pos[picked], *[array[picked] for array in extra])
      color[picked] = local

  # Sleeve and jacket overlap at the shoulder at rest, and that hidden cloth shows as the arm swings.
  picked = np.concatenate((pick("jacket_sleeve"), pick("jacket_shell")))
  inside = picked[np.hypot(np.abs(pos[picked, 0]) - 0.2, pos[picked, 2] - 1.36) < 0.12]
  occlusion[inside] = np.maximum(occlusion[inside], 0.8)
  contact[inside] = np.maximum(contact[inside], 0.9)

  painted = shade(color, names, region, pos, normal, occlusion, contact)
  # The face keeps its own painted shadows; occlusion alone would muddy it.
  picked = pick("head_skin")
  painted[picked] = mix(painted[picked], color[picked] * (0.86 + 0.14 * occlusion[picked, None]), 0.75)

  result = np.zeros((SIZE, SIZE, 4), dtype=np.float32)
  result[..., 3] = 1.0
  result[mask, :3] = np.clip(painted, 0.0, 1.0)
  return result


def apply(body, pixels):
  image = bpy.data.images.get("protagonist_paint")
  if image:
    bpy.data.images.remove(image)
  image = bpy.data.images.new("protagonist_paint", SIZE, SIZE, alpha=False)
  image.colorspace_settings.name = "sRGB"
  image.pixels.foreach_set(pixels.ravel())
  image.file_format = "PNG"
  image.pack()
  material = bpy.data.materials.get("protagonist_paint") or bpy.data.materials.new("protagonist_paint")
  material.use_nodes = True
  tree = material.node_tree
  tree.nodes.clear()
  shader = tree.nodes.new("ShaderNodeBsdfPrincipled")
  texture = tree.nodes.new("ShaderNodeTexImage")
  output = tree.nodes.new("ShaderNodeOutputMaterial")
  texture.image = image
  shader.inputs["Roughness"].default_value = 0.82
  tree.links.new(texture.outputs["Color"], shader.inputs["Base Color"])
  tree.links.new(shader.outputs[0], output.inputs["Surface"])
  body.data.materials.clear()
  body.data.materials.append(material)
  bake = bpy.data.materials.get("paint_bake")
  if bake:
    bpy.data.materials.remove(bake)
  stale = bpy.data.images.get("paint_bake_target")
  if stale:
    bpy.data.images.remove(stale)


def main():
  body = bpy.data.objects["protagonist_male"]
  armature = bpy.data.objects["armature_male"]
  armature.data.pose_position = "REST"
  setup_cycles()
  for other in bpy.data.objects:
    other.select_set(False)
  unwrap(body)
  baker = Baker(body)
  body.select_set(True)
  bpy.context.view_layer.objects.active = body
  region = baker.emit("ShaderNodeAttribute", "Vector", "region")
  position = baker.emit("ShaderNodeTexCoord", "Object")
  normal = baker.emit("ShaderNodeNewGeometry", "Normal")
  panel = baker.emit("ShaderNodeAttribute", "Vector", "panel")
  armature.data.pose_position = "POSE"
  spread_arms(armature, 50)
  bpy.context.view_layer.update()
  occlusion = baker.occlusion(0.3)
  contact = baker.occlusion(0.035)
  spread_arms(armature, 0)
  apply(body, paint(body, (region, position, normal, panel, occlusion, contact)))
  bpy.ops.wm.save_mainfile()
  print("painted", SIZE)


if __name__ == "__main__":
  main()
