# The machete, shared by the loot prop and the skeleton's hand: long work blade with a straight back,
# a belly that widens toward the tip, a filed bevel and a chipped edge, all under painted rust.
# The grip sits on the origin, the blade runs along -Y and the back faces +Z.
import numpy as np
from mathutils import Matrix, Vector

from prop_tools import Canvas, Shape, fractal_noise, image_from, material

BLADE_LENGTH = 0.72
BLADE_START = 0.075
# (distance from the guard, top of the back, shoulder of the bevel, bottom of the edge). The two
# narrow dips are chips: the shoulder ignores them, so the bevel stays one clean line.
OUTLINE = [
  (0.0, 0.019, -0.01, -0.026), (0.09, 0.02, -0.015, -0.034), (0.2, 0.0205, -0.021, -0.043),
  (0.3, 0.021, -0.027, -0.051), (0.316, 0.021, -0.028, -0.041), (0.335, 0.021, -0.029, -0.054),
  (0.46, 0.022, -0.038, -0.068), (0.478, 0.022, -0.039, -0.06), (0.492, 0.022, -0.04, -0.069),
  (0.6, 0.024, -0.05, -0.084), (0.665, 0.03, -0.052, -0.089), (0.7, 0.043, -0.044, -0.07),
  (BLADE_LENGTH, 0.064, 0.03, 0.012),
]
# (distance behind the guard's front, top, bottom, half thickness), from the bolster to the hooked pommel.
HANDLE = [
  (-0.085, 0.022, -0.03, 0.0105), (-0.062, 0.024, -0.033, 0.0125), (-0.06, 0.021, -0.029, 0.0115),
  (-0.02, 0.021, -0.031, 0.0125), (0.03, 0.019, -0.029, 0.0125), (0.075, 0.018, -0.03, 0.012),
  (0.105, 0.019, -0.04, 0.012), (0.12, 0.017, -0.05, 0.01), (0.128, 0.012, -0.046, 0.008),
]
BOLSTER_RINGS = 2
RIVETS = (-0.035, 0.015, 0.065)
RIVET_HEIGHT = -0.005

SIZE = (1024, 512)
PIXELS_PER_METER = 1024 / 0.84
SIDE_ROWS = (0, 205)
SIDE_HEIGHT = 201
WOOD_ROW = 410
TOP_LIMIT = 0.07 # Height of a side row's first pixel row.
WOOD_TOP = 0.05
BOLSTER_SHIFT = 320 # Pixels: the bolster paints a paler patch of the wood row.

STEEL = (0.5, 0.53, 0.55)
STEEL_DARK = (0.3, 0.32, 0.34)
STEEL_FILED = (0.8, 0.82, 0.81)
RUST_STAIN = (0.3, 0.17, 0.11)
RUST_DEEP = (0.42, 0.18, 0.08)
RUST = (0.58, 0.29, 0.13)
RUST_CRUST = (0.72, 0.46, 0.24)


def paint_side(seed, stamped):
  """One face of the blade. Rust gathers at the guard, along the back, at the tip and around the chips."""
  canvas = Canvas(SIZE[0], SIDE_HEIGHT, STEEL)
  distance = canvas.x / PIXELS_PER_METER
  height = TOP_LIMIT - canvas.y / PIXELS_PER_METER
  stations = [row[0] for row in OUTLINE]
  top = np.interp(distance, stations, [row[1] for row in OUTLINE])
  shoulder = np.interp(distance, stations, [row[2] for row in OUTLINE])
  bottom = np.interp(distance, stations, [row[3] for row in OUTLINE])
  on_bevel = height < shoulder
  across = np.clip((height - shoulder) / np.maximum(top - shoulder, 1e-4), 0, 1)

  # Long brushed streaks, then soft grey patina.
  streaks = fractal_noise(SIZE[0], SIDE_HEIGHT, 3, 40, seed, 3)
  canvas.blend((streaks - 0.5) * 2.4, STEEL_DARK, 0.5)
  patina = fractal_noise(SIZE[0], SIDE_HEIGHT, 12, 5, seed + 1)
  canvas.blend((patina - 0.47) * 6.0, STEEL_DARK, 0.65)

  chips = np.exp(-((distance - 0.316) / 0.035) ** 2) + np.exp(-((distance - 0.478) / 0.03) ** 2)
  bias = (
    0.26 * np.exp(-distance / 0.1)
    + 0.13 * across ** 2
    + 0.2 * np.exp((distance - BLADE_LENGTH) / 0.09)
    + 0.14 * chips
  )
  rust = fractal_noise(SIZE[0], SIDE_HEIGHT, 16, 6, seed + 2, 5) + bias
  pits = fractal_noise(SIZE[0], SIDE_HEIGHT, 90, 30, seed + 3, 2)
  rust += (pits - 0.5) * 0.14
  rust = rust - on_bevel * 0.3

  # Hard bands instead of a gradient: painted rust, not a photo of it.
  canvas.blend((rust - 0.53) * 60.0, RUST_STAIN, 0.85)
  canvas.blend((rust - 0.575) * 60.0, RUST_DEEP)
  canvas.blend((rust - 0.64) * 60.0, RUST)
  canvas.blend((rust - 0.74) * 60.0, RUST_CRUST)
  canvas.blend(((pits - 0.74) * 60.0) * (rust > 0.5), RUST_STAIN)

  scratches = fractal_noise(SIZE[0], SIDE_HEIGHT, 8, 70, seed + 4, 2)
  filed = on_bevel & (rust < 0.64)
  canvas.blend(filed.astype(float), STEEL_FILED, 0.9)
  canvas.blend(filed * (scratches - 0.52) * 7.0, STEEL, 0.75)
  canvas.blend(1.0 - np.abs(height - shoulder) * PIXELS_PER_METER / 1.5, STEEL_DARK, 0.7)

  if stamped:
    five = [(92, 76), (78, 76), (78, 89), (91, 89), (92, 101), (77, 101)]
    eight = [(114, 88), (102, 88), (102, 76), (114, 76), (114, 101), (102, 101), (102, 88)]
    canvas.stroke(five, 3.0, STEEL_DARK)
    canvas.stroke(eight, 3.0, STEEL_DARK)
  return canvas.rgb


def paint_wood(height):
  """Warm grain darkened where the hand goes, with the bolster's paler patch further along."""
  canvas = Canvas(SIZE[0], height, (0.5, 0.31, 0.17))
  grain = fractal_noise(SIZE[0], height, 4, 22, 21, 4)
  canvas.blend((grain - 0.44) * 7.0, (0.31, 0.17, 0.09), 0.85)
  canvas.blend((grain - 0.62) * 14.0, (0.21, 0.11, 0.06), 0.9)
  canvas.blend((0.33 - grain) * 12.0, (0.66, 0.44, 0.25), 0.8)
  knots = fractal_noise(SIZE[0], height, 18, 6, 22, 3)
  canvas.blend((knots - 0.64) * 12.0, (0.12, 0.07, 0.05), 0.75)
  canvas.rect(BOLSTER_SHIFT - 8, 0, SIZE[0], height, (0.74, 0.52, 0.3), 0.72)
  return canvas.rgb


def paint_atlas():
  rgb = np.zeros((SIZE[1], SIZE[0], 3))
  for row, seed, stamped in ((SIDE_ROWS[0], 3, True), (SIDE_ROWS[1], 41, False)):
    rgb[row:row + SIDE_HEIGHT] = paint_side(seed, stamped)
  rgb[WOOD_ROW:] = paint_wood(SIZE[1] - WOOD_ROW)
  return image_from("machete_atlas", rgb)


def atlas_uv(pixel_x, pixel_y):
  return (pixel_x / SIZE[0], 1.0 - pixel_y / SIZE[1])


def blade_uv(row, distance, height):
  return atlas_uv(distance * PIXELS_PER_METER, row + (TOP_LIMIT - height) * PIXELS_PER_METER)


def build_blade(shape, mat, origin):
  thick = 0.0055
  sides = []
  for sign, row in ((1, SIDE_ROWS[0]), (-1, SIDE_ROWS[1])):
    verts = []
    for distance, top, shoulder, bottom in OUTLINE:
      y = origin.y - BLADE_START - distance
      half = sign * thick * (1.0 - 0.55 * distance / BLADE_LENGTH)
      verts += [(origin.x + half, y, origin.z + top), (origin.x + half, y, origin.z + shoulder), (origin.x, y, origin.z + bottom)]
    faces = []
    uvs = []
    for i in range(len(OUTLINE) - 1):
      a, b = i * 3, (i + 1) * 3
      for k in range(2):
        faces.append((a + k, a + k + 1, b + k + 1, b + k))
        corners = []
        for station, level in ((i, k), (i, k + 1), (i + 1, k + 1), (i + 1, k)):
          corners.append(blade_uv(row, OUTLINE[station][0], OUTLINE[station][level + 1]))
        uvs.append(corners)
    sides.append(len(shape.verts))
    shape.add(verts, faces, mat, uvs)
  front, back = sides
  for i in range(len(OUTLINE) - 1):
    a, b = i * 3, (i + 1) * 3
    distance, next_distance = OUTLINE[i][0], OUTLINE[i + 1][0]
    uv = [blade_uv(SIDE_ROWS[0], distance, OUTLINE[i][1] - 0.002), blade_uv(SIDE_ROWS[0], distance, OUTLINE[i][1] - 0.006),
          blade_uv(SIDE_ROWS[0], next_distance, OUTLINE[i + 1][1] - 0.006), blade_uv(SIDE_ROWS[0], next_distance, OUTLINE[i + 1][1] - 0.002)]
    shape.faces.append((front + a, back + a, back + b, front + b))
    shape.mats.append(mat)
    shape.uvs.append(uv)
  last = (len(OUTLINE) - 1) * 3
  shape.faces.append((front + last, front + last + 1, front + last + 2, back + last + 1, back + last))
  shape.mats.append(mat)
  shape.uvs.append([blade_uv(SIDE_ROWS[0], BLADE_LENGTH - 0.004, OUTLINE[-1][1])] * 5)


def handle_ring(origin, along, top, bottom, half):
  chamfer = min(half * 0.32, 0.0035)
  corners = [
    (half - chamfer, top), (half, top - chamfer), (half, bottom + chamfer), (half - chamfer, bottom),
    (-half + chamfer, bottom), (-half, bottom + chamfer), (-half, top - chamfer), (-half + chamfer, top),
  ]
  return [(origin.x + x, origin.y + along, origin.z + z) for x, z in corners]


def wood_uv(along, height, shift):
  return atlas_uv((along + 0.11) * PIXELS_PER_METER + shift, WOOD_ROW + (WOOD_TOP - height) * PIXELS_PER_METER)


def build_handle(shape, mat, origin):
  rings = [handle_ring(origin, along, top, bottom, half) for along, top, bottom, half in HANDLE]
  verts = [v for ring in rings for v in ring]
  faces = []
  uvs = []
  n = len(rings[0])
  for band in range(len(rings) - 1):
    shift = BOLSTER_SHIFT if band < BOLSTER_RINGS else 0
    for side in range(n):
      next_side = (side + 1) % n
      faces.append((band * n + side, band * n + next_side, (band + 1) * n + next_side, (band + 1) * n + side))
      corners = []
      for ring, index in ((band, side), (band, next_side), (band + 1, next_side), (band + 1, side)):
        corners.append(wood_uv(HANDLE[ring][0], verts[ring * n + index][2] - origin.z, shift))
      uvs.append(corners)
  last = (len(rings) - 1) * n
  faces.append(tuple(last + side for side in range(n)))
  uvs.append([wood_uv(HANDLE[-1][0], verts[last + side][2] - origin.z, 0) for side in range(n)])
  shape.add(verts, faces, mat, uvs)


def build_rivets(shape, steel, rim, origin):
  for along in RIVETS:
    for sign in (1, -1):
      at = (
        Matrix.Translation(origin + Vector((sign * 0.0122, along, RIVET_HEIGHT)))
        @ Matrix.Rotation(sign * np.pi / 2, 4, "Y")
      )
      shape.lathe([(0.0062, 0.0), (0.0062, 0.0008), (0.0043, 0.0016)], lambda band, side: rim if band == 0 else steel, n=8, at=at)


def build(origin=Vector((0, 0, 0))):
  atlas = material("machete_atlas", roughness=0.5, image=paint_atlas())
  steel = material("machete_rivet", (0.82, 0.83, 0.8), roughness=0.4)
  rim = material("machete_rivet_rim", (0.42, 0.28, 0.17))
  shape = Shape()
  build_blade(shape, atlas, origin)
  build_handle(shape, atlas, origin)
  build_rivets(shape, steel, rim, origin)
  return shape.finish("machete")
