# Builds the route past the avenue: tower square with the looted store, earthquake alley,
# chapel square, street to the cathedral and the cathedral square where Guino waits.
# Reuses the avenue's helpers, so both stages share one look and the same five materials.
# Godot's x is Blender's x and Godot's z is minus Blender's y.
#   blender --background --python art/environments/build_route.py
import math
import os
import sys

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_avenue as A  # noqa: E402
from build_avenue import (  # noqa: E402
  LEAVES, Layer, blade_plant, box, cable, car, clump, crown_dome, flat_blob, grass_tuft, ivy_curtain,
  rng, shop_front, tree, tube, window,
)

BLEND_PATH = os.path.join(HERE, "route.blend")
GLB_PATH = os.path.join(HERE, "..", "..", "game", "models", "environments", "route.glb")
GATE_GLB_PATH = os.path.join(HERE, "..", "..", "game", "models", "environments", "shortcut_gate.glb")

A.MATERIALS.update({
  "paint_mint": ((0.50, 0.62, 0.52), 0.95, 0.0),
  "paint_cream": ((0.78, 0.72, 0.58), 0.95, 0.0),
  "plaster_white": ((0.84, 0.81, 0.73), 0.95, 0.0),
  "plaster_ochre": ((0.80, 0.56, 0.28), 0.95, 0.0),
  "plaster_blue": ((0.30, 0.46, 0.64), 0.95, 0.0),
  "terracotta": ((0.60, 0.28, 0.15), 0.95, 0.0),
  "tile_white": ((0.72, 0.72, 0.68), 0.8, 0.0),
  "tile_red": ((0.52, 0.22, 0.15), 0.9, 0.0),
  "cooler_red": ((0.66, 0.10, 0.09), 0.5, 0.1),
  "sign_green": ((0.10, 0.50, 0.25), 0.7, 0.0),
  "cardboard": ((0.55, 0.41, 0.25), 1.0, 0.0),
  "fabric_blue": ((0.16, 0.24, 0.42), 1.0, 0.0),
  "fabric_red": ((0.50, 0.12, 0.12), 1.0, 0.0),
  "mattress": ((0.66, 0.62, 0.52), 1.0, 0.0),
  "mattress_stain": ((0.40, 0.31, 0.19), 1.0, 0.0),
  "bone": ((0.85, 0.81, 0.68), 0.9, 0.0),
  "tarp_blue": ((0.12, 0.30, 0.58), 0.9, 0.0),
  "tarp_orange": ((0.85, 0.40, 0.10), 0.9, 0.0),
  "court_green": ((0.18, 0.34, 0.30), 0.9, 0.0),
  "court_line": ((0.82, 0.82, 0.76), 0.9, 0.0),
  "chain_link": ((0.46, 0.47, 0.48), 0.6, 0.6),
  "candle": ((0.92, 0.88, 0.74), 0.9, 0.0),
  "fruit": ((0.62, 0.42, 0.10), 1.0, 0.0),
})
A.GRIME_NAMES |= {"paint_mint", "paint_cream", "plaster_white", "plaster_ochre", "plaster_blue"}

# Everything the player and the camera can reach on this route, the store's upper floor included.
A.PLAY_CORNERS = [
  Vector((x, y, z)) for x in (-30.0, 30.0) for y in (46.0, 125.0) for z in (0.2, 8.6)
] + [
  Vector((x, y, z)) for x in (30.0, 312.0) for y in (85.0, 145.0) for z in (0.2, 8.6)
]


def collection():
  result = bpy.data.collections.get("route")
  if not result:
    result = bpy.data.collections.new("route")
    bpy.context.scene.collection.children.link(result)
  return result


A.collection = collection

# (world matrix, size, section): boxes merged into one -colonly mesh per section.
colliders = []
section = "square"


def collide(layer, center, size, rotation=(0, 0, 0)):
  matrix = layer.matrix @ Matrix.Translation(center) @ Euler(rotation).to_matrix().to_4x4()
  colliders.append((matrix, Vector(size), section))


def solid(layer, center, size):
  """Hides faces buried in this box. Only for boxes that stay axis aligned in the world."""
  half = Vector(size) / 2
  corners = [layer.matrix @ (Vector(center) + Vector((sx * half.x, sy * half.y, sz * half.z))) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
  low = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
  high = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
  margin = Vector((0.03, 0.03, 0.03))
  A.solids.append((low + margin, high - margin))


def block(layer, center, size, mat, rotation=(0, 0, 0), hide=False):
  box(layer, center, size, mat, rotation)
  collide(layer, center, size, rotation)
  if hide:
    solid(layer, center, size)


def frame(layer, a, b):
  """Local frame for a wall from a to b: +Y runs along it, -X faces the play side on its left."""
  a = Vector((a[0], a[1], 0.0))
  d = Vector((b[0], b[1], 0.0)) - a
  layer.matrix = Matrix.Translation(a) @ Euler((0, 0, math.atan2(d.y, d.x) - math.pi / 2)).to_matrix().to_4x4()
  return d.length


def holed_wall(layer, along_x, fixed, start, end, bottom, top, holes, outer, inner=None, inward=1, thickness=0.3):
  """Axis-aligned wall split around rectangular holes (s0, s1, z0, z1), painted inside with inner."""
  pieces = []
  cursor = start
  for s0, s1, z0, z1 in sorted(holes):
    if s0 > cursor:
      pieces.append((cursor, s0, bottom, top))
    if z0 > bottom:
      pieces.append((s0, s1, bottom, z0))
    if z1 < top:
      pieces.append((s0, s1, z1, top))
    cursor = s1
  if cursor < end:
    pieces.append((cursor, end, bottom, top))
  for s0, s1, z0, z1 in pieces:
    along = (s0 + s1) / 2
    z = (z0 + z1) / 2
    skin = fixed + inward * (thickness / 2 + 0.012)
    if along_x:
      block(layer, (along, fixed, z), (s1 - s0, thickness, z1 - z0), outer)
      if inner:
        box(layer, (along, skin, z), (s1 - s0, 0.02, z1 - z0), inner)
    else:
      block(layer, (fixed, along, z), (thickness, s1 - s0, z1 - z0), outer)
      if inner:
        box(layer, (skin, along, z), (0.02, s1 - s0, z1 - z0), inner)


def holed_slab(layer, x0, x1, y0, y1, z0, z1, holes, mat, floor_mat=None):
  """Floor slab cut into strips around rectangular holes (x0, x1, y0, y1)."""
  xs = sorted({x0, x1, *[h[0] for h in holes], *[h[1] for h in holes]})
  ys = sorted({y0, y1, *[h[2] for h in holes], *[h[3] for h in holes]})
  for a, b in zip(xs, xs[1:]):
    run = None
    for c, d in zip(ys, ys[1:]):
      mx, my = (a + b) / 2, (c + d) / 2
      empty = any(h[0] <= mx <= h[1] and h[2] <= my <= h[3] for h in holes)
      if not empty:
        run = (run[0], d) if run else (c, d)
      if (empty or d == ys[-1]) and run:
        center = ((a + b) / 2, (run[0] + run[1]) / 2, (z0 + z1) / 2)
        size = (b - a, run[1] - run[0], z1 - z0)
        block(layer, center, size, mat)
        if floor_mat:
          box(layer, (center[0], center[1], z1 + 0.01), (size[0], size[1], 0.02), floor_mat)
        run = None


def ramp(layer, start, end, width, along_x=True):
  """Walkable incline from start to end (x, y, z) with filled steps below for the eye and the body."""
  start, end = Vector(start), Vector(end)
  run = (end - start).length
  flat = math.hypot(end.x - start.x, end.y - start.y)
  angle = math.atan2(end.z - start.z, flat)
  normal_drop = Vector((0, 0, -0.1 * math.cos(angle)))
  center = (start + end) / 2 + normal_drop
  if along_x:
    collide(layer, center, (run, width, 0.2), (0, -angle * math.copysign(1, end.x - start.x), 0))
  else:
    collide(layer, center, (width, run, 0.2), (angle * math.copysign(1, end.y - start.y), 0, 0))


def crack(layer, y, z, length, angle_start):
  """Zigzag earthquake crack on a local wall face (x = 0, facing -x)."""
  angle = angle_start
  for _ in range(rng.randint(3, 6)):
    step = length * rng.uniform(0.15, 0.3)
    next_y = y + math.cos(angle) * step
    next_z = z - abs(math.sin(angle)) * step
    box(layer, (-0.03, (y + next_y) / 2, (z + next_z) / 2), (0.05, step + 0.05, rng.uniform(0.05, 0.11)), "crack", (math.atan2(next_z - z, next_y - y), 0, 0))
    y, z = next_y, next_z
    angle += rng.uniform(-0.7, 0.7)


def rebar(layer, origin, out, count=5, length=0.9):
  """Bent reinforcing bars sticking out of broken concrete."""
  origin, out = Vector(origin), Vector(out).normalized()
  side = out.cross(Vector((0, 0, 1)))
  if side.length < 0.1:
    side = Vector((1, 0, 0))
  side.normalize()
  for _ in range(count):
    base = origin + side * rng.uniform(-0.8, 0.8)
    mid = base + out * length * 0.5 + Vector((0, 0, rng.uniform(-0.3, 0.1)))
    tip = base + out * length + Vector((0, 0, rng.uniform(-0.8, 0.0))) + side * rng.uniform(-0.3, 0.3)
    tube(layer, [(tuple(base), 0.016), (tuple(mid), 0.016), (tuple(tip), 0.014)], "rust", n=3)


def rubble(layer, center, spread, count, height=1.0, solid_height=0.0):
  """Pile of broken concrete and brick; solid_height > 0 also blocks the way."""
  x, y = center
  for _ in range(count):
    size = rng.uniform(0.3, 1.1) * height
    clump(layer, (x + rng.uniform(-spread[0], spread[0]), y + rng.uniform(-spread[1], spread[1]), size * 0.35), (size * 1.2, size, size * 0.7), rng.choice(("concrete_grey", "concrete_stain", "brick_red", "concrete_warm", "brick_dark")), 0.3)
  for _ in range(count // 4):
    box(layer, (x + rng.uniform(-spread[0], spread[0]), y + rng.uniform(-spread[1], spread[1]), rng.uniform(0.2, height)), (rng.uniform(0.8, 2.0), rng.uniform(0.6, 1.4), 0.18), rng.choice(("concrete_warm", "concrete_grey")), (rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5), rng.random() * 3))
  if solid_height > 0:
    collide(layer, (x, y, solid_height / 2), (spread[0] * 1.6, spread[1] * 1.6, solid_height))


def weeds(layer, a, b, count, reach=1.4):
  """Plants along the foot of a wall from a to b, on its play side."""
  a, b = Vector((a[0], a[1], 0)), Vector((b[0], b[1], 0))
  d = (b - a).normalized()
  left = Vector((-d.y, d.x, 0))
  for _ in range(count):
    point = a.lerp(b, rng.random()) + left * rng.uniform(0.2, reach)
    if rng.random() < 0.3:
      blade_plant(layer, (point.x, point.y, 0.02), rng.uniform(0.6, 1.3))
    else:
      grass_tuft(layer, (point.x, point.y, 0.02), rng.uniform(0.3, 0.7))


def building(layer, a, b, floors, style="concrete", depth=10.0, shops=False, ivy=2, cracks=2, door=True):
  """City block whose facade runs from a to b with the play side on the left."""
  length = frame(layer, a, b)
  story = 3.3
  height = floors * story + 0.6
  wall = {
    "concrete": rng.choice(("concrete_warm", "concrete_stain", "concrete_grey", "brick_orange")),
    "brick": rng.choice(("brick_red", "brick_dark", "brick_orange")),
    "plaster": rng.choice(("plaster_ochre", "plaster_white", "plaster_blue", "paint_mint")),
  }[style]
  trim = "concrete_grey" if style == "concrete" else "stone_cream"
  block(layer, (depth / 2, length / 2, height / 2), (depth, length, height), wall, hide=True)
  columns = max(1, int(length / 3.1))
  span = length / columns
  door_column = rng.randrange(columns) if door and not shops else -1
  for k in range(columns):
    y = (k + 0.5) * span
    if shops:
      shop_front(layer, 0, -1, y, span - 0.35)
    elif k == door_column:
      box(layer, (-0.05, y, 1.25), (0.1, 1.2, 2.5), rng.choice(("wood", "iron", "shutter")))
      box(layer, (-0.1, y, 2.6), (0.2, 1.5, 0.15), trim)
    else:
      window(layer, 0, y, 1.7, 1.1, 1.4, -1, grille=True, frame=trim)
  for floor in range(1, floors):
    z = floor * story + 1.6
    box(layer, (-0.08, length / 2, floor * story + 0.1), (0.16, length, 0.22), trim)
    for k in range(columns):
      y = (k + 0.5) * span
      roll = rng.random()
      if roll < 0.12:
        # Boarded up after the quake.
        box(layer, (-0.05, y, z), (0.1, 1.3, 1.7), "wood_old")
        for plank in range(3):
          box(layer, (-0.12, y, z - 0.55 + plank * 0.55), (0.04, 1.45, 0.22), "wood", (rng.uniform(-0.1, 0.1), 0, 0))
      elif roll < 0.22:
        box(layer, (-0.02, y, z), (0.06, 1.4, 1.8), "window_dark")
      else:
        window(layer, 0, y, z, 1.2, 1.6, -1, grille=rng.random() < 0.25, frame=trim if rng.random() < 0.5 else "window_frame")
      if style == "concrete" and floor % 2 == 0 and rng.random() < 0.5:
        box(layer, (-0.6, y, floor * story + 0.1), (1.2, span - 0.2, 0.2), trim)
        box(layer, (-1.15, y, floor * story + 0.6), (0.1, span - 0.2, 0.9), trim)
      if rng.random() < 0.12:
        A.add_air_conditioner(layer, 0, y + 0.9, z - 0.6, -1)
  box(layer, (-0.12, length / 2, height + 0.2), (0.4, length + 0.1, 0.4), trim)
  for _ in range(cracks):
    crack(layer, rng.uniform(1, length - 1), rng.uniform(height * 0.5, height - 0.5), rng.uniform(2.5, 5.0), rng.uniform(-2.4, -0.7))
  A.stains(layer, 0, -1, 0, length, height, int(length / 3))
  # Rooftop: black water tanks and the bare rebar of a floor never finished.
  tank = rng.uniform(1, length - 1)
  tube(layer, [((depth * 0.4, tank, height), 0.6), ((depth * 0.4, tank, height + 1.2), 0.6), ((depth * 0.4, tank, height + 1.35), 0.2)], "trash", n=8)
  for k in range(int(length / 4)):
    y = 1 + k * 4
    if rng.random() < 0.5:
      box(layer, (0.4, y, height + 0.6), (0.3, 0.3, 1.2), trim)
      for _ in range(3):
        tube(layer, [((0.4 + rng.uniform(-0.1, 0.1), y + rng.uniform(-0.1, 0.1), height + 1.2), 0.012), ((0.4 + rng.uniform(-0.3, 0.3), y + rng.uniform(-0.3, 0.3), height + 2.1), 0.012)], "rust", n=3)
  for k in range(ivy):
    y = (k + 0.5) * length / max(ivy, 1) + rng.uniform(-1, 1)
    top = height - rng.uniform(0, 2)
    ivy_curtain(layer, 0, -1, y, top, top * rng.uniform(0.4, 0.9), 0.15, 0.0)
  layer.reset()
  weeds(layer, a, b, int(length * 1.2))
  return height


def streetlight(layer, x, y, yaw, broken=False):
  layer.place((x, y, 0.0), (0, 0.12 if broken else 0, yaw))
  tube(layer, [((0, 0, 0), 0.13), ((0, 0, 0.8), 0.1), ((0, 0, 5.8), 0.06)], "metal_grey", n=6)
  tube(layer, [((0, 0, 5.8), 0.06), ((0.25, 0, 6.5), 0.05), ((0.9, 0, 6.85), 0.045), ((1.8, 0, 6.85), 0.04)], "metal_grey", n=5)
  box(layer, (2.05, 0, 6.82), (0.75, 0.28, 0.1), "metal_grey")
  box(layer, (2.05, 0, 6.76), (0.55, 0.2, 0.04), "glass")
  layer.reset()
  collide(layer, (x, y, 2.0), (0.3, 0.3, 4.0))


def bench(layer, x, y, yaw, broken=False):
  layer.place((x, y, 0.0), (0, 0, yaw))
  for side in (-0.7, 0.7):
    box(layer, (side, 0, 0.22), (0.12, 0.5, 0.44), "concrete_grey")
  for k in range(3 if not broken else 2):
    box(layer, (0, -0.15 + k * 0.15, 0.47), (1.8, 0.12, 0.05), "wood_old", (0, 0.15 if broken and k == 1 else 0, 0))
  box(layer, (0, 0.25, 0.75), (1.8, 0.06, 0.3), "wood_old")
  collide(layer, (0, 0, 0.3), (1.9, 0.6, 0.6))
  layer.reset()


def plastic_chair(layer, x, y, z, yaw, fallen=False):
  layer.place((x, y, z), (1.5 if fallen else 0, 0, yaw))
  color = "sign_white"
  box(layer, (0, 0, 0.42), (0.45, 0.45, 0.05), color)
  box(layer, (0, 0.22, 0.68), (0.45, 0.04, 0.5), color)
  for sx in (-0.2, 0.2):
    for sy in (-0.2, 0.2):
      box(layer, (sx, sy, 0.21), (0.04, 0.04, 0.42), color)
  layer.reset()


def puddles(layer, area, count):
  x0, x1, y0, y1 = area
  for _ in range(count):
    center = (rng.uniform(x0, x1), rng.uniform(y0, y1))
    radii = (rng.uniform(0.8, 2.2), rng.uniform(0.8, 2.2))
    flat_blob(layer, center, radii, "puddle", 0.025, points=10)


def floor_cracks(layer, area, count, z=0.006):
  x0, x1, y0, y1 = area
  for _ in range(count):
    x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
    angle = rng.random() * math.tau
    for _ in range(rng.randint(3, 7)):
      step = rng.uniform(0.4, 1.0)
      angle += rng.uniform(-0.8, 0.8)
      nx, ny = x + math.cos(angle) * step, y + math.sin(angle) * step
      box(layer, ((x + nx) / 2, (y + ny) / 2, z), (step + 0.05, rng.uniform(0.04, 0.1), 0.012), "crack", (0, 0, angle))
      if rng.random() < 0.25:
        grass_tuft(layer, (x, y, z), rng.uniform(0.2, 0.5))
      x, y = nx, ny


def litter(layer, area, count, z=0.0):
  """Trash bags, papers, cans and broken bits on a floor."""
  x0, x1, y0, y1 = area
  for _ in range(count):
    x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
    roll = rng.random()
    if roll < 0.35:
      box(layer, (x, y, z + 0.006), (rng.uniform(0.2, 0.32), rng.uniform(0.25, 0.4), 0.008), rng.choice(("sign_white", "paint_cream", "cardboard")), (0, 0, rng.random() * 3))
    elif roll < 0.6:
      size = rng.uniform(0.2, 0.4)
      clump(layer, (x, y, z + size * 0.6), (size, size, size * 0.8), "trash", 0.25)
    elif roll < 0.8:
      tube(layer, [((x, y, z + 0.035), 0.035), ((x + 0.11, y + rng.uniform(-0.05, 0.05), z + 0.035), 0.035)], rng.choice(("sign_red", "metal_grey", "sign_yellow")), n=6)
    else:
      clump(layer, (x, y, z + 0.06), (0.12, 0.1, 0.08), rng.choice(("concrete_grey", "brick_red")), 0.3)


# --- Tower square -------------------------------------------------------------------------------

STORE = (10.0, 30.0, 99.0, 113.0)
FLOOR2 = 3.6
ROOF = 7.1
STAIR = (12.0, 19.0, 111.0, 112.7)  # 1.7 m wide: the navigation needs the room to reach upstairs.
FLOOR_HOLE = (18.9, 21.4, 105.0, 108.0)


def build_square_ground():
  layer = Layer("route_square_ground")
  block(layer, (0, 87.0, -0.25), (62, 78, 0.5), "sidewalk")
  # Big square tiles of the old plaza, with a lighter ring around the tower.
  for k in range(25):
    box(layer, (-30 + k * 2.5, 87.0, 0.004), (0.05, 76, 0.008), "crack")
  for k in range(31):
    box(layer, (0, 49 + k * 2.5, 0.004), (60, 0.05, 0.008), "crack")
  box(layer, (0, 72.0, 0.01), (29, 29, 0.02), "stone_cream")
  box(layer, (0, 72.0, 0.03), (26.4, 26.4, 0.02), "concrete_grey")
  # Slabs lifted by the quake along a fissure that crosses the square.
  for k in range(9):
    x = -26 + k * 2.6 + rng.uniform(-0.4, 0.4)
    y = 92 + k * 2.4 + rng.uniform(-0.6, 0.6)
    box(layer, (x, y, 0.06), (2.4, 2.4, 0.1), rng.choice(("sidewalk", "concrete_grey", "concrete_stain")), (rng.uniform(-0.05, 0.05), rng.uniform(-0.05, 0.05), rng.uniform(-0.2, 0.2)))
    box(layer, (x + 1.3, y + 0.4, 0.012), (0.25, 2.6, 0.012), "crack", (0, 0, 0.85))
  floor_cracks(layer, (-28, 28, 52, 123), 40)
  puddles(layer, (-26, 26, 52, 96), 9)
  for _ in range(260):
    grass_tuft(layer, (rng.uniform(-29, 29), rng.uniform(51, 124), 0.0), rng.uniform(0.2, 0.6))
  layer.build()


def build_square_buildings():
  layer = Layer("route_square_buildings")
  # Each facade runs with the square on its left.
  building(layer, (-30, 50), (-21.5, 50), 6, "concrete", depth=8)
  building(layer, (21.5, 50), (30, 50), 5, "brick", depth=8)
  building(layer, (30, 50), (30, 72), 7, "concrete", shops=True)
  building(layer, (30, 72), (30, 94), 4, "brick")
  building(layer, (-30, 125), (-30, 100), 5, "brick", depth=12)
  building(layer, (-30, 100), (-30, 75), 6, "concrete", depth=12, shops=True)
  building(layer, (-30, 75), (-30, 50), 4, "brick", depth=12)
  building(layer, (-12, 125), (-30, 125), 7, "concrete", depth=12)
  building(layer, (10, 125), (-12, 125), 4, "brick", depth=12)
  building(layer, (30, 125), (10, 125), 5, "concrete", depth=12)
  layer.build()

  # A dark skyline over the roofs, as the avenue has, so the square never ends in the sky.
  # Named backdrop so the import script keeps it from casting shadows, as with the avenue's.
  backdrop = Layer("backdrop_square")
  for x0, x1, y0, y1 in ((-75, -45, 45, 140), (-45, 45, 140, 160), (42, 70, 40, 92)):
    y = y0
    while y < y1:
      width = rng.uniform(10, 18)
      height = rng.uniform(24, 55)
      x = rng.uniform(x0, x1)
      box(backdrop, (x, y + width / 2, height / 2), (rng.uniform(10, 16), width, height), "skyline")
      for row in range(int(height / 7)):
        box(backdrop, (x, y + width / 2, 4 + row * 7), (rng.uniform(10.2, 16.2), width * 0.86, 2.2), "window_dark")
      y += width + rng.uniform(0, 4)
  backdrop.build()


def gondola(layer, x, y0, y1, stock=0.25):
  """Double-sided supermarket shelf along y, mostly emptied by looters."""
  length = y1 - y0
  mid = (y0 + y1) / 2
  block(layer, (x, mid, 0.08), (0.7, length, 0.16), "metal_grey")
  box(layer, (x, mid, 0.9), (0.06, length, 1.6), "shutter")
  for level in range(4):
    z = 0.3 + level * 0.42
    box(layer, (x, mid, z), (0.7, length, 0.03), "metal_grey")
    for side in (-1, 1):
      y = y0 + 0.2
      while y < y1 - 0.2:
        if rng.random() < stock:
          w = rng.uniform(0.12, 0.3)
          h = rng.uniform(0.12, 0.3)
          box(layer, (x + side * rng.uniform(0.12, 0.25), y, z + h / 2 + 0.02), (0.18, w, h), rng.choice(("sign_red", "sign_yellow", "sign_blue", "sign_white", "cardboard", "sign_green")), (0, 0, rng.uniform(-0.3, 0.3)))
        y += rng.uniform(0.25, 0.6)
  collide(layer, (x, mid, 0.85), (0.72, length, 1.7))


def fallen_gondola(layer, start, end):
  """A shelf tipped onto its side, goods spilled around it."""
  start, end = Vector((*start, 0)), Vector((*end, 0))
  d = end - start
  angle = math.atan2(d.y, d.x)
  mid = (start + end) / 2
  layer.place((mid.x, mid.y, 0.0), (0, 0, angle))
  box(layer, (0, 0, 0.35), (d.length, 0.06, 0.7), "shutter")
  for level in range(4):
    box(layer, (0, -0.3 + level * 0.2, 0.35), (d.length, 0.03, 0.7), "metal_grey")
  box(layer, (0, 0.35, 0.08), (d.length, 0.16, 0.7), "metal_grey", (math.pi / 2, 0, 0))
  layer.reset()
  collide(layer, (mid.x, mid.y, 0.4), (d.length, 0.9, 0.8), (0, 0, angle))
  for _ in range(14):
    t = rng.random()
    p = start.lerp(end, t)
    box(layer, (p.x + rng.uniform(-1.2, 1.2), p.y + rng.uniform(-1.2, 1.2), 0.07), (0.2, 0.14, 0.14), rng.choice(("sign_red", "sign_yellow", "sign_blue", "cardboard")), (rng.uniform(0, 1.5), 0, rng.random() * 3))


def cooler(layer, x, y, fallen=False):
  """Upright drinks cooler against the east wall, glass door hanging open."""
  if fallen:
    # Face down on the tiles, its top towards the aisles.
    layer.place((x - 0.35, y, 0.35), (0, -math.pi / 2, 0))
  else:
    layer.place((x, y, 0.0))
  box(layer, (0, 0, 1.0), (0.7, 1.9, 2.0), "cooler_red")
  box(layer, (-0.36, 0, 1.0), (0.04, 1.7, 1.75), "window_dark")
  for level in range(4):
    box(layer, (-0.1, 0, 0.45 + level * 0.4), (0.5, 1.7, 0.03), "metal_grey")
  box(layer, (-0.36, 0, 2.02), (0.06, 1.8, 0.2), "sign_white")
  if not fallen:
    box(layer, (-0.95, -0.55, 1.0), (1.3, 0.05, 1.7), "glass", (0, 0, -0.9))
  layer.reset()
  if fallen:
    collide(layer, (x - 1.35, y, 0.38), (2.0, 1.9, 0.76))
    for _ in range(10):
      tube(layer, [((x - rng.uniform(0.5, 3.0), y + rng.uniform(-1.5, 1.5), 0.04), 0.04), ((x - rng.uniform(0.5, 3.0), y + rng.uniform(-1.5, 1.5), 0.04), 0.04)], rng.choice(("glass", "sign_red", "metal_grey")), n=6)
  else:
    collide(layer, (x, y, 1.0), (0.72, 1.92, 2.0))


def boarded_window(layer, along_x, fixed, s0, s1, z0, z1, outward):
  """Planks nailed over a window hole, with gaps that let thin blades of light in."""
  middle = (s0 + s1) / 2
  width = s1 - s0 + 0.3
  planks = 3
  for k in range(planks):
    z = z0 + 0.22 + k * (z1 - z0 - 0.3) / (planks - 1)
    tilt = rng.uniform(-0.08, 0.08)
    offset = fixed + outward * 0.18
    if along_x:
      box(layer, (middle, offset, z), (width, 0.04, 0.24), rng.choice(("wood", "wood_old")), (0, tilt, 0))
    else:
      box(layer, (offset, middle, z), (0.04, width, 0.24), rng.choice(("wood", "wood_old")), (tilt, 0, 0))


def build_store():
  """The looted abasto with its pharmacy: two walkable floors, the loot and inventory lesson."""
  layer = Layer("route_store")
  x0, x1, y0, y1 = STORE
  t = 0.3
  # Ground floor walls, painted mint inside. The front faces the tower.
  door = (16.0, 19.0, 0.0, 2.4)
  holed_wall(layer, True, y0 + t / 2, x0, x1, 0.0, FLOOR2, [door], "concrete_warm", "paint_mint", 1)
  west_windows = [(102.0, 103.4, 1.0, 2.2), (105.6, 107.0, 1.0, 2.2)]
  holed_wall(layer, False, x0 + t / 2, y0 + t, y1 - t, 0.0, FLOOR2, west_windows, "concrete_warm", "paint_mint", 1)
  holed_wall(layer, True, y1 - t / 2, x0, x1, 0.0, FLOOR2, [], "concrete_warm", "paint_mint", -1)
  holed_wall(layer, False, x1 - t / 2, y0 + t, y1 - t, 0.0, FLOOR2, [], "concrete_warm", "paint_mint", -1)
  # Upper floor: boarded windows and the broken east wall that leads onto the fallen house.
  front_up = [(12.3, 13.7, 4.4, 5.8), (16.8, 18.2, 4.4, 5.8), (22.3, 23.7, 4.4, 5.8), (27.0, 28.4, 4.4, 5.8)]
  west_up = [(101.5, 102.9, 4.4, 5.8), (109.0, 110.4, 4.4, 5.8)]
  north_up = [(25.0, 26.4, 4.4, 5.8)]
  exit_hole = (101.0, 104.0, FLOOR2, 6.3)
  holed_wall(layer, True, y0 + t / 2, x0, x1, FLOOR2, ROOF + 0.6, front_up, "concrete_warm", "paint_cream", 1)
  holed_wall(layer, False, x0 + t / 2, y0 + t, y1 - t, FLOOR2, ROOF + 0.6, west_up, "concrete_warm", "paint_cream", 1)
  holed_wall(layer, True, y1 - t / 2, x0, x1, FLOOR2, ROOF + 0.6, north_up, "concrete_warm", "paint_cream", -1)
  holed_wall(layer, False, x1 - t / 2, y0 + t, y1 - t, FLOOR2, ROOF + 0.6, [exit_hole], "concrete_warm", "paint_cream", -1)
  for s0, s1, z0, z1 in front_up:
    boarded_window(layer, True, y0 + t / 2, s0, s1, z0, z1, -1)
  for s0, s1, z0, z1 in west_up + west_windows:
    boarded_window(layer, False, x0 + t / 2, s0, s1, z0, z1, -1)
  for s0, s1, z0, z1 in north_up:
    boarded_window(layer, True, y1 - t / 2, s0, s1, z0, z1, 1)
  # Broken edge of the exit, its rebar bent out over the fallen house.
  rebar(layer, (x1, 102.5, FLOOR2 + 2.7), (1, 0, -0.4), 6, 0.8)
  for _ in range(6):
    clump(layer, (x1 + rng.uniform(-0.1, 0.2), rng.choice((100.8, 104.2)), rng.uniform(FLOOR2 + 0.3, 6.0)), (0.25, 0.3, 0.3), "concrete_warm", 0.3)

  # Floors: tiles below, the slab with its stairwell and the hole torn in it, the roof.
  box(layer, ((x0 + x1) / 2, (y0 + y1) / 2, 0.012), (x1 - x0 - 2 * t, y1 - y0 - 2 * t, 0.024), "tile_white")
  for k in range(1, 20):
    box(layer, (x0 + k, (y0 + y1) / 2, 0.026), (0.03, y1 - y0 - 0.6, 0.004), "concrete_stain")
  for k in range(1, 14):
    box(layer, ((x0 + x1) / 2, y0 + k, 0.026), (x1 - x0 - 0.6, 0.03, 0.004), "concrete_stain")
  stairwell = (STAIR[0], STAIR[1], STAIR[2], y1 - t)
  holed_slab(layer, x0 + t, x1 - t, y0 + t, y1 - t, FLOOR2 - 0.3, FLOOR2, [stairwell, FLOOR_HOLE], "paint_cream", "tile_red")
  block(layer, ((x0 + x1) / 2, (y0 + y1) / 2, ROOF - 0.15), (x1 - x0, y1 - y0, 0.3), "paint_cream")
  box(layer, ((x0 + x1) / 2, (y0 + y1) / 2, ROOF + 0.02), (x1 - x0 - 0.2, y1 - y0 - 0.2, 0.04), "concrete_stain")
  hx0, hx1, hy0, hy1 = FLOOR_HOLE
  for edge in ((hx0, (hy0 + hy1) / 2, (-1, 0, 0)), (hx1, (hy0 + hy1) / 2, (1, 0, 0)), ((hx0 + hx1) / 2, hy0, (0, -1, 0))):
    rebar(layer, (edge[0], edge[1], FLOOR2 - 0.2), (-edge[2][0], -edge[2][1], -1.2), 4, 0.7)
  rubble(layer, ((hx0 + hx1) / 2, (hy0 + hy1) / 2), (1.0, 1.2), 14, 0.5)
  # Water from the roof drips through the hole into a dark puddle.
  flat_blob(layer, ((hx0 + hx1) / 2 + 0.6, hy0 + 0.6), (0.9, 0.7), "puddle", 0.03)

  # Concrete stair along the north wall, from the back of the shop up to the landing.
  sx0, sx1, sy0, sy1 = STAIR
  steps = 18
  run = (sx1 - sx0) / steps
  for k in range(steps):
    rise = (k + 1) * FLOOR2 / steps
    box(layer, (sx0 + (k + 0.5) * run, (sy0 + sy1) / 2, rise / 2), (run + 0.01, sy1 - sy0, rise), "concrete_grey")
    box(layer, (sx0 + (k + 0.5) * run, (sy0 + sy1) / 2, rise + 0.01), (run - 0.02, sy1 - sy0 - 0.04, 0.02), "tile_red")
  ramp(layer, (sx0, (sy0 + sy1) / 2, 0.0), (sx1, (sy0 + sy1) / 2, FLOOR2), sy1 - sy0)
  for k in range(1, 7):
    # Fill under the ramp so nothing walks into the stair's belly.
    x = sx0 + k
    top = FLOOR2 * k / (sx1 - sx0) - 0.15
    collide(layer, (x + 0.5, (sy0 + sy1) / 2, top / 2), (1.0, sy1 - sy0, top))
  tube(layer, [((sx0, sy0 + 0.05, 1.0), 0.03), ((sx1, sy0 + 0.05, FLOOR2 + 1.0), 0.03)], "iron", n=4)
  # Railing around the stairwell upstairs.
  tube(layer, [((sx0 + 0.1, sy0 - 0.05, FLOOR2 + 1.0), 0.03), ((sx1 - 0.4, sy0 - 0.05, FLOOR2 + 1.0), 0.03)], "iron", n=4)
  for k in range(8):
    box(layer, (sx0 + 0.2 + k * (sx1 - sx0 - 0.6) / 7, sy0 - 0.05, FLOOR2 + 0.5), (0.04, 0.04, 1.0), "iron")
  collide(layer, ((sx0 + sx1 - 0.4) / 2, sy0 - 0.05, FLOOR2 + 0.55), (sx1 - sx0 - 0.4, 0.12, 1.1))

  # Ground floor: pharmacy counter and shelves, the aisles, coolers and the storeroom.
  block(layer, (13.5, 104.0, 0.5), (1.0, 6.0, 1.0), "wood")
  box(layer, (13.5, 104.0, 1.03), (1.1, 6.1, 0.06), "metal_grey")
  box(layer, (13.5, 102.0, 1.2), (0.4, 0.5, 0.3), "metal_grey")
  box(layer, (13.5, 106.0, 1.25), (0.9, 1.6, 0.4), "glass", (0, 0, 0.1))
  litter(layer, (13.0, 14.0, 101.0, 107.0), 6, 1.06)
  block(layer, (10.6, 104.5, 1.1), (0.6, 9.0, 2.2), "wood_old")
  for level in range(5):
    z = 0.3 + level * 0.45
    box(layer, (10.95, 104.5, z), (0.1, 9.0, 0.03), "wood")
    for _ in range(int(rng.uniform(2, 8))):
      box(layer, (10.95, rng.uniform(100.4, 108.6), z + 0.1), (0.2, 0.15, 0.18), rng.choice(("sign_white", "sign_green", "sign_blue", "sign_red")), (0, 0, rng.uniform(-0.4, 0.4)))
  box(layer, (10.32, 104.5, 2.65), (0.04, 3.5, 0.6), "sign_green")
  gondola(layer, 18.0, 101.0, 108.0)
  gondola(layer, 21.5, 103.0, 108.0, 0.15)
  gondola(layer, 25.0, 101.0, 108.0)
  fallen_gondola(layer, (22.2, 103.0), (25.6, 101.6))
  cooler(layer, 29.35, 101.0)
  cooler(layer, 29.35, 103.0, fallen=True)
  cooler(layer, 29.35, 105.0)
  # Storeroom with a kitchenette where the workers made their coffee.
  holed_wall(layer, False, 23.08, 108.0, y1 - t, 0.0, FLOOR2 - 0.3, [(108.9, 110.9, 0.0, 2.2)], "paint_mint", None, thickness=0.15)
  holed_wall(layer, True, 108.08, 23.0, x1 - t, 0.0, FLOOR2 - 0.3, [], "paint_mint", None, thickness=0.15)
  block(layer, (28.65, 112.35, 0.45), (2.1, 0.6, 0.9), "wood")
  box(layer, (28.65, 112.35, 0.92), (2.15, 0.65, 0.04), "tile_white")
  box(layer, (29.1, 112.35, 0.98), (0.7, 0.45, 0.08), "iron")
  for bx in (28.92, 29.28):
    tube(layer, [((bx, 112.35, 1.02), 0.09), ((bx, 112.35, 1.04), 0.09)], "rust", n=8)
  tube(layer, [((27.8, 112.3, 0.0), 0.16), ((27.8, 112.3, 0.55), 0.16), ((27.8, 112.3, 0.65), 0.05)], "sign_red", n=8)
  block(layer, (26.2, 110.6, 0.38), (1.2, 0.8, 0.76), "wood_old")
  plastic_chair(layer, 25.6, 111.4, 0.0, 0.3)
  plastic_chair(layer, 27.0, 111.5, 0.0, 2.5, fallen=True)
  # Boxes along the walls, clear of the door.
  for x, y in ((24.0, 112.2), (25.0, 112.25)):
    for k in range(rng.randint(1, 3)):
      box(layer, (x + rng.uniform(-0.05, 0.05), y, 0.25 + k * 0.48), (0.7, 0.55, 0.45), "cardboard", (0, 0, rng.uniform(-0.15, 0.15)))
    collide(layer, (x, y, 0.5), (0.75, 0.6, 1.0))
  for k in range(3):
    box(layer, (28.6, 109.1 + k * 0.1, 0.06 + k * 0.12), (1.2, 1.0, 0.1), "wood", (0, 0, rng.uniform(-0.1, 0.1)))
  collide(layer, (28.6, 109.2, 0.2), (1.2, 1.0, 0.4))
  litter(layer, (x0 + 0.6, x1 - 0.6, y0 + 0.6, y1 - 0.6), 70, 0.02)

  # Upper floor: the manager's office, his sitting room and the open store room by the exit.
  f = FLOOR2
  holed_wall(layer, True, 105.08, x0 + t, 18.0, f, ROOF - 0.3, [(13.6, 15.6, f, f + 2.2)], "paint_cream", None, thickness=0.15)
  holed_wall(layer, False, 18.08, 105.0, STAIR[2] - 0.1, f, ROOF - 0.3, [], "paint_cream", None, thickness=0.15)
  holed_wall(layer, False, 23.08, 106.0, y1 - t, f, ROOF - 0.3, [(108.0, 110.0, f, f + 2.2)], "paint_cream", None, thickness=0.15)
  holed_wall(layer, True, 106.08, 23.0, x1 - t, f, ROOF - 0.3, [], "paint_cream", None, thickness=0.15)
  # Office: desk, filing cabinets, a calendar stopped in 2016 and the fan that fell.
  block(layer, (13.45, 108.55, f + 0.37), (2.9, 1.1, 0.74), "wood")
  box(layer, (13.45, 108.55, f + 0.76), (3.0, 1.2, 0.04), "wood_old")
  box(layer, (12.6, 108.4, f + 0.84), (0.5, 0.35, 0.12), "metal_grey")
  litter(layer, (12.2, 14.8, 108.1, 109.0), 5, f + 0.79)
  plastic_chair(layer, 13.8, 109.6, f, math.pi)
  for k in range(3):
    block(layer, (10.65, 106.0 + k * 0.6, f + 0.65), (0.5, 0.55, 1.3), "metal_grey")
  box(layer, (13.0, 111.25, f + 1.8), (0.6, 0.02, 0.8), "sign_white")
  box(layer, (13.0, 111.24, f + 2.15), (0.6, 0.02, 0.15), "sign_red")
  layer.place((15.2, 107.0, f + 0.05), (0, 0, 0.6))
  tube(layer, [((0, 0, 0), 0.12), ((0, 0, 0.18), 0.1)], "metal_grey", n=8)
  for k in range(3):
    box(layer, (math.cos(k * 2.1) * 0.45, math.sin(k * 2.1) * 0.45, 0.06), (0.7, 0.14, 0.02), "wood_old", (0, 0, k * 2.1))
  layer.reset()
  litter(layer, (x0 + 0.5, 17.8, 105.3, 111.0), 18, f + 0.02)
  # Sitting room: sofa, hammock, television and the record player with its gaitas.
  block(layer, (25.8, 112.1, f + 0.25), (3.6, 0.9, 0.5), "fabric_blue")
  box(layer, (25.8, 112.5, f + 0.6), (3.6, 0.2, 0.8), "fabric_blue")
  for side in (-1, 1):
    box(layer, (25.8 + side * 1.75, 112.1, f + 0.45), (0.2, 0.9, 0.4), "fabric_blue")
  block(layer, (29.2, 108.25, f + 0.4), (0.8, 1.3, 0.8), "wood")
  box(layer, (29.2, 108.25, f + 0.84), (0.6, 0.6, 0.08), "metal_grey")
  tube(layer, [((29.2, 108.25, f + 0.88), 0.22), ((29.2, 108.25, f + 0.9), 0.22)], "trash", n=10)
  for _ in range(8):
    box(layer, (rng.uniform(26.0, 29.0), rng.uniform(106.6, 110.5), f + 0.02), (0.31, 0.31, 0.01), rng.choice(("sign_red", "sign_yellow", "sign_blue", "trash", "sign_white")), (0, 0, rng.random() * 3))
  block(layer, (25.0, 107.4, f + 0.3), (1.2, 0.6, 0.6), "wood_old")
  box(layer, (25.0, 107.4, f + 0.85), (0.8, 0.5, 0.5), "trash")
  tube(layer, [((23.3, 110.2, f + 1.6), 0.02), ((26.4, 110.6, f + 0.75), 0.18), ((29.6, 111.0, f + 1.6), 0.02)], "fabric_red", n=5)
  box(layer, (29.68, 110.5, f + 1.7), (0.02, 0.4, 0.55), "sign_blue")
  # Open room by the exit: somebody slept here before the rats came.
  box(layer, (26.5, 101.0, f + 0.1), (1.0, 1.9, 0.2), "mattress", (0, 0, 0.2))
  flat_blob(layer, (26.6, 101.2), (0.3, 0.5), "mattress_stain", f + 0.21)
  tube(layer, [((24.3, 100.0, f), 0.15), ((24.3, 100.0, f + 0.35), 0.18)], "sign_blue", n=8)
  for x, y in ((20.8, 100.2), (21.4, 100.3), (11.2, 99.9)):
    box(layer, (x, y, f + 0.25), (0.55, 0.45, 0.5), "cardboard", (0, 0, rng.uniform(-0.3, 0.3)))
  litter(layer, (x0 + 0.5, x1 - 0.5, y0 + 0.5, 104.6), 26, f + 0.02)

  # Front: two pulled-down shutters, the one at the door rolled up, the green pharmacy cross.
  frame(layer, (x1, y0), (x0, y0))
  shop_front(layer, 0, -1, 5.1, 9.6)
  shop_front(layer, 0, -1, 17.3, 4.6)
  for k in range(4):
    box(layer, (-0.12, 12.5, 2.5 + k * 0.15), (0.06, 3.0, 0.16), "shutter")
  box(layer, (-0.3, 12.5, 2.35), (0.08, 3.0, 0.14), "rust", (0.35, 0, 0))
  for side in (-1.55, 1.55):
    box(layer, (-0.12, 12.5 + side, 1.3), (0.1, 0.1, 2.6), "iron")
  box(layer, (-0.25, 12.5, 3.9), (0.12, 7.0, 0.7), "sign_white")
  box(layer, (-0.32, 12.5, 3.9), (0.02, 6.4, 0.25), "sign_red")
  box(layer, (-0.7, 0.4, 4.3), (0.9, 0.18, 0.9), "sign_green")
  box(layer, (-0.7, 0.4, 4.3), (0.3, 0.2, 0.9), "sign_white")
  box(layer, (-0.7, 0.4, 4.3), (0.9, 0.2, 0.3), "sign_white")
  box(layer, (-0.3, 0.4, 4.3), (0.6, 0.06, 0.06), "iron")
  for _ in range(3):
    crack(layer, rng.uniform(2, 18), rng.uniform(5, 7), 4.0, rng.uniform(-2.4, -0.7))
  ivy_curtain(layer, 0, -1, 1.5, ROOF + 0.4, 5.0, 0.15, 0.0)
  ivy_curtain(layer, 0, -1, 19.0, ROOF + 0.4, 3.5, 0.15, 0.0)
  layer.reset()
  box(layer, ((x0 + x1) / 2, y0 - 0.1, ROOF + 0.4), (x1 - x0 + 0.2, 0.5, 0.3), "concrete_grey")
  weeds(layer, (x1, y0), (x0, y0), 24)
  weeds(layer, (x0, y0), (x0, y1), 18)
  weeds(layer, (x0, y1), (x1, y1), 18)
  layer.build()


def build_fallen_house():
  """Its upper floor slid down inside, a ramp out of the store's broken wall into the alley."""
  layer = Layer("route_fallen_house")
  x0, x1 = 30.0, 43.7
  holed_wall(layer, True, 107.85, x0, x1, 0.0, 5.5, [(33.0, 34.4, 3.9, 5.0), (37.0, 38.4, 3.9, 5.0), (41.0, 42.4, 3.9, 5.0)], "brick_red", "plaster_ochre", -1)
  holed_wall(layer, True, 99.15, x0, x1, 0.0, 5.5, [], "brick_red", "plaster_ochre", 1)
  frame(layer, (x1, 108.0), (x0, 108.0))
  for y in (2.0, 6.0, 10.5):
    box(layer, (-0.05, y, 1.6), (0.1, 1.2, 1.4), "wood_old")
    for plank in range(3):
      box(layer, (-0.12, y, 1.1 + plank * 0.5), (0.04, 1.4, 0.2), "wood", (rng.uniform(-0.1, 0.1), 0, 0))
  for _ in range(3):
    crack(layer, rng.uniform(1, 12), rng.uniform(3.5, 5.3), 3.5, rng.uniform(-2.4, -0.7))
  box(layer, (-0.12, 6.85, 5.6), (0.3, 13.9, 0.25), "stone_cream")
  ivy_curtain(layer, 0, -1, 4.0, 5.5, 3.0, 0.15, 0.0)
  layer.reset()
  frame(layer, (x0, 99.0), (x1, 99.0))
  for _ in range(2):
    crack(layer, rng.uniform(1, 12), rng.uniform(3.5, 5.3), 3.5, rng.uniform(-2.4, -0.7))
  layer.reset()
  # The slab: 3.5 m at the store, 2.3 m at the far end, too high to climb back.
  tilt = math.atan2(1.2, 13.7)
  block(layer, (37.0, 103.5, 2.75), (13.9, 8.4, 0.3), "concrete_warm", (0, tilt, 0))
  box(layer, (37.0, 103.5, 2.92), (13.4, 7.9, 0.04), "tile_red", (0, tilt, 0))
  for _ in range(18):
    x = rng.uniform(31.5, 43.0)
    z = 3.55 - (x - 30.3) * 1.2 / 13.7
    size = rng.uniform(0.15, 0.4)
    clump(layer, (x, rng.uniform(100.0, 107.0), z + size * 0.3), (size, size * 0.9, size * 0.5), rng.choice(("brick_red", "concrete_grey", "tile_red")), 0.3)
  # A bathtub rode the floor down.
  layer.place((40.5, 101.0, 2.62), (0, tilt, 0.3))
  box(layer, (0, 0, 0.28), (1.6, 0.75, 0.5), "sign_white")
  box(layer, (0, 0, 0.5), (1.4, 0.55, 0.08), "window_dark")
  layer.reset()
  rebar(layer, (43.8, 103.5, 2.2), (1, 0, -0.6), 8, 0.9)
  # Rubble closes the space under the slab's low end.
  rubble(layer, (43.8, 103.5), (0.5, 4.0), 22, 1.6)
  collide(layer, (43.7, 103.5, 1.0), (0.6, 8.4, 2.0))
  layer.build()


def build_square_props():
  layer = Layer("route_square_props")
  car(layer, (-20.0, 70.0, 0.0), (0, 0, 1.45), "car_blue")
  collide(layer, (-20.0, 70.0, 0.75), (4.8, 2.0, 1.5), (0, 0, 1.45 - math.pi / 2))
  car(layer, (14.0, 55.0, 0.0), (0, 0, 0.12), "car_red")
  collide(layer, (14.0, 55.0, 0.75), (2.0, 4.8, 1.5), (0, 0, 0.12))
  # Taxi that went into a lamp post when the ground shook.
  car(layer, (-23.0, 108.0, 0.0), (0, 0, 0.6), "car_yellow")
  collide(layer, (-23.0, 108.0, 0.75), (2.0, 4.8, 1.5), (0, 0, 0.6))
  A.overgrow(layer, (-23.0, 108.0, 1.3), (0.6, 1.2, 0.3), 10)
  streetlight(layer, -24.6, 110.8, 2.2, broken=True)
  for x, y, yaw in ((-14.0, 90.0, 0.0), (22.0, 62.0, 3.14), (-24.0, 58.0, 1.57)):
    streetlight(layer, x, y, yaw)
  for x, y, height, crown in ((-22.0, 88.0, 7.0, 4.0), (22.0, 66.0, 6.5, 3.6), (-6.0, 116.0, 6.0, 3.4), (-26.0, 120.0, 5.5, 3.0)):
    tree(layer, x, y, height, crown)
    collide(layer, (x, y, 2.0), (0.8, 0.8, 4.0))
    for _ in range(4):
      blade_plant(layer, (x + rng.uniform(-1.5, 1.5), y + rng.uniform(-1.5, 1.5), 0.0), rng.uniform(0.8, 1.5))
  # Planter ring around each tree.
  for x, y in ((-22.0, 88.0), (22.0, 66.0)):
    for k in range(4):
      angle = k * math.pi / 2
      box(layer, (x + math.cos(angle) * 1.4, y + math.sin(angle) * 1.4, 0.2), (2.9 if k % 2 == 0 else 0.25, 0.25 if k % 2 == 0 else 2.9, 0.4), "concrete_grey", (0, 0, angle))
  bench(layer, -10.0, 92.0, 0.0)
  bench(layer, 6.0, 90.0, 0.1, broken=True)
  bench(layer, -18.0, 82.0, 1.57)
  A.kiosk(layer, -25.0, 64.0)
  collide(layer, (-25.0, 64.0, 1.4), (1.9, 2.2, 2.8))
  A.phone_booth(layer, -26.5, 96.0)
  collide(layer, (-26.5, 96.0, 1.2), (0.8, 0.8, 2.4))
  # The radio left on a crate, still muttering testimonies about El Silbon.
  block(layer, (-14.0, 56.0, 0.3), (0.7, 0.5, 0.6), "wood_old")
  box(layer, (-14.0, 56.0, 0.72), (0.45, 0.16, 0.25), "metal_grey")
  box(layer, (-14.0, 55.91, 0.72), (0.18, 0.02, 0.16), "iron")
  tube(layer, [((-13.82, 56.0, 0.84), 0.008), ((-13.7, 56.1, 1.3), 0.006)], "metal_grey", n=3)
  plastic_chair(layer, -14.7, 56.8, 0.0, 0.4)
  # Rubble that fell into the square, a heap that narrows the way north of the store.
  rubble(layer, (8.0, 118.0), (3.0, 2.0), 30, 1.4, 1.2)
  rubble(layer, (-18.0, 98.0), (2.0, 1.5), 20, 1.2, 1.0)
  rubble(layer, (27.0, 52.0), (2.0, 1.5), 14, 1.0)
  for position, angle in (((-3.0, 49.0, 0.0), 0.1), ((3.5, 49.5, 0.0), -0.15)):
    A.concrete_barrier(layer, position, angle)
    collide(layer, (position[0], position[1], 0.45), (2.5, 0.8, 0.9), (0, 0, angle))
  litter(layer, (-28, 28, 52, 123), 70)
  cable(layer, (-24.0, 110.8, 6.6), (-12.0, 125.0, 9.0), 1.5)
  cable(layer, (-14.0, 90.0, 6.6), (-29.5, 92.0, 8.0), 1.0)
  cable(layer, (22.0, 62.0, 6.6), (29.5, 64.0, 9.0), 0.8)
  layer.build()


# --- Earthquake alley and the service lane behind it --------------------------------------------

HOUSE = (86.0, 98.0, 113.0, 123.0)


def back_wall(layer, a, b, height):
  """Plain rear wall over a lane: small windows, drain pipes and somebody's washing."""
  length = frame(layer, a, b)
  y = 1.5
  while y < length - 1:
    if rng.random() < 0.6:
      window(layer, 0, y, rng.choice((1.8, 4.6)) if height > 5 else 1.8, 0.8, 0.9, -1, grille=True)
    if rng.random() < 0.3:
      tube(layer, [((-0.12, y + 1.0, 0.0), 0.06), ((-0.12, y + 1.0, height - 0.2), 0.06)], rng.choice(("iron", "sign_white", "rust")), n=5)
    y += rng.uniform(2.5, 4.5)
  for _ in range(2):
    crack(layer, rng.uniform(1, length - 1), height - 0.5, 3.0, rng.uniform(-2.4, -0.7))
  A.stains(layer, 0, -1, 0, length, height, int(length / 4))
  layer.reset()


def clothesline(layer, start, end, z):
  cable(layer, (*start, z), (*end, z), 0.25, 0.008)
  for _ in range(rng.randint(2, 5)):
    t = rng.uniform(0.15, 0.85)
    x = start[0] + (end[0] - start[0]) * t
    y = start[1] + (end[1] - start[1]) * t
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    box(layer, (x, y, z - 0.45 - 0.25 * 4 * t * (1 - t)), (0.6, 0.02, 0.8), rng.choice(("sign_white", "sign_red", "sign_blue", "fabric_blue", "sign_yellow")), (0, 0, angle))


def graffiti(layer, length, z0, z1):
  """Painted testimonies on a local wall face: dashes of white and red, not readable up close."""
  for _ in range(int(length * 2)):
    y = rng.uniform(0.5, length - 0.5)
    z = rng.uniform(z0, z1)
    box(layer, (-0.04, y, z), (0.02, rng.uniform(0.15, 0.6), rng.uniform(0.04, 0.09)), rng.choice(("sign_white", "sign_white", "sign_red", "trash")), (rng.uniform(-0.6, 0.6), 0, 0))


def build_alley():
  layer = Layer("route_alley_ground")
  block(layer, (80.0, 109.5, -0.25), (100, 31, 0.5), "asphalt")
  for _ in range(14):
    box(layer, (rng.uniform(32, 128), rng.uniform(100, 124), 0.008), (rng.uniform(1.5, 4.0), rng.uniform(1.0, 3.0), 0.012), rng.choice(("asphalt_patch", "concrete_grey")), (0, 0, rng.uniform(-0.2, 0.2)))
  floor_cracks(layer, (31, 129, 100, 124), 50)
  puddles(layer, (32, 128, 109, 124), 12)
  for _ in range(220):
    grass_tuft(layer, (rng.uniform(31, 129), rng.uniform(95, 124), 0.0), rng.uniform(0.2, 0.6))
  layer.build()

  layer = Layer("route_alley_buildings")
  # North row: facades step in and out, so the way zigzags between them.
  building(layer, (46, 121), (30, 121), 4, "brick", depth=12)
  building(layer, (62, 125), (46, 125), 5, "concrete", depth=12)
  building(layer, (84, 116), (62, 116), 3, "brick", depth=18, cracks=6)
  building(layer, (98, 123.2), (84, 123.2), 4, "concrete", depth=12)
  building(layer, (120, 115), (101, 115), 4, "concrete", depth=12, cracks=4)
  building(layer, (130, 125), (120, 125), 5, "brick", depth=12)
  block(layer, (99.5, 125.0, 4.0), (3.0, 4.0, 8.0), "concrete_stain", hide=True)
  # South row: their backs are the lane's north wall.
  for x0, x1, floors, style in ((50, 64, 3, "brick"), (64, 86, 2, "concrete"), (86, 101, 3, "brick"), (101, 118, 3, "concrete"), (118, 130, 4, "brick")):
    building(layer, (x0, 108), (x1, 108), floors, style, depth=9, cracks=3)
  # Paint left by the ones who heard him: it whistles close when it is far.
  frame(layer, (104, 108), (117, 108))
  graffiti(layer, 13, 0.6, 2.6)
  layer.reset()
  layer.build()

  layer = Layer("route_alley_props")
  # Rubble narrowing the mouth, and the facade that fell across the first bend.
  rubble(layer, (39.0, 110.0), (3.0, 1.8), 30, 1.4, 1.3)
  block(layer, (57.0, 110.65, 2.6), (10.0, 0.4, 7.0), "concrete_warm", (0.735, 0, 0))
  layer.place((57.0, 110.65, 2.6), (0.735, 0, 0))
  for k in range(3):
    window(layer, -3.0 + k * 3.0, 0.2, 1.0, 1.2, 1.4, 1, along_x=True)
  layer.reset()
  rebar(layer, (57.0, 113.2, 0.3), (0, 1, 0.3), 8, 1.0)
  rubble(layer, (57.0, 114.8), (5.0, 1.6), 36, 1.3, 1.3)
  # Slab bridging the street overhead, three metres up at its lowest.
  block(layer, (75.0, 112.0, 4.8), (6.0, 8.2, 0.35), "concrete_grey", (0.197, 0, 0))
  rebar(layer, (75.0, 108.2, 4.0), (0, 0.2, -1), 6, 0.9)
  for _ in range(4):
    x = rng.uniform(72.5, 77.5)
    tube(layer, [((x, 111.0, 4.5), 0.016), ((x + rng.uniform(-0.4, 0.4), 111.2, rng.uniform(2.6, 3.4)), 0.016)], "cable", n=3)
  # The collapsed fronts south of the split house close that side.
  rubble(layer, (92.0, 110.5), (6.0, 2.4), 50, 2.2, 2.6)
  block(layer, (92.0, 111.5, 2.0), (9.0, 0.35, 5.0), "brick_red", (-0.5, 0.1, 0.05))
  rubble(layer, (110.0, 109.0), (2.0, 0.8), 10, 0.8)
  rubble(layer, (125.0, 123.5), (2.0, 1.0), 12, 1.0, 0.9)
  # Animita by the north wall: candles and flowers for somebody who died here.
  block(layer, (56.0, 124.5, 0.4), (0.9, 0.6, 0.8), "plaster_white")
  box(layer, (56.0, 124.5, 1.25), (0.8, 0.5, 0.7), "plaster_blue")
  box(layer, (56.0, 124.24, 1.25), (0.5, 0.02, 0.5), "window_dark")
  box(layer, (56.0, 124.5, 1.66), (1.1, 0.8, 0.08), "rust", (0.15, 0, 0))
  for k in range(5):
    tube(layer, [((55.6 + k * 0.2, 124.1, 0.8), 0.03), ((55.6 + k * 0.2, 124.1, 0.8 + rng.uniform(0.08, 0.2)), 0.03)], "candle", n=5)
  for k in range(3):
    blade_plant(layer, (55.4 + k * 0.6, 123.9, 0.0), 0.5, blades=6, mat="leaf_light")
  # Cables and washing strung between both rows.
  for x in (36.0, 49.0, 66.0, 81.0, 104.0, 114.0, 126.0):
    cable(layer, (x, 108.0, rng.uniform(6.0, 8.0)), (x + rng.uniform(-3, 3), 121.0 if x < 46 else 125.0 if x < 62 or x > 120 else 116.0 if x < 84 else 115.0, rng.uniform(6.0, 8.5)), rng.uniform(0.6, 1.4))
  for x in (52.0, 70.0, 108.0):
    clothesline(layer, (x, 108.2), (x + 1.5, 115.8 if x < 84 else 114.8), 3.4)
  for x in (40.0, 90.0, 116.0):
    tube(layer, [((x, 108.0, 7.0), 0.016), ((x + 1.0, 109.5, 3.0), 0.016), ((x + 1.5, 110.0, 0.05), 0.016)], "cable", n=3)
  streetlight(layer, 47.0, 108.6, 1.57, broken=True)
  litter(layer, (31, 129, 108, 124), 80)
  layer.build()

  build_split_house()
  build_lane()


def build_split_house():
  """Two storeys torn along the middle: the way goes in by the door and out of the kitchen."""
  layer = Layer("route_split_house")
  x0, x1, y0, y1 = HOUSE
  top = 6.4
  holed_wall(layer, False, x0 + 0.15, y0, y1, 0.0, top, [(117.0, 119.5, 0.0, 2.3), (114.2, 115.6, 1.0, 2.2), (120.8, 122.2, 3.8, 5.2)], "brick_red", "paint_cream", 1)
  holed_wall(layer, False, x1 - 0.15, y0, y1, 0.0, top, [(116.0, 120.0, 0.0, 3.2)], "brick_red", "plaster_ochre", -1)
  holed_wall(layer, True, y0 + 0.15, x0 + 0.3, x1 - 0.3, 0.0, top, [], "brick_red", "paint_cream", 1)
  holed_wall(layer, True, y1 - 0.15, x0 + 0.3, x1 - 0.3, 0.0, top, [], "brick_red", "plaster_ochre", -1)
  # The crack: a dark seam on the floor and walls, and a roof open in the middle.
  for k in range(12):
    x = x0 + 0.5 + k
    box(layer, (x, 118.2 + rng.uniform(-0.25, 0.25), 0.02), (1.05, 0.18, 0.02), "crack", (0, 0, rng.uniform(-0.3, 0.3)))
  box(layer, (x0 + 0.33, 118.2, 4.5), (0.02, 0.25, 3.8), "crack", (0.1, 0, 0))
  box(layer, (x1 - 0.33, 118.2, 4.6), (0.02, 0.3, 3.6), "crack", (-0.1, 0, 0))
  box(layer, ((x0 + x1) / 2, 118.2, 0.012), (x1 - x0 - 0.6, y1 - y0 - 0.6, 0.02), "tile_red")
  block(layer, ((x0 + x1) / 2, 114.95, top - 0.1), (x1 - x0 + 0.4, 3.9, 0.3), "concrete_grey", (-0.05, 0, 0))
  box(layer, ((x0 + x1) / 2, 114.95, top + 0.12), (x1 - x0 + 0.5, 4.1, 0.12), "terracotta", (-0.05, 0, 0))
  block(layer, ((x0 + x1) / 2, 121.3, top - 0.6), (x1 - x0 + 0.4, 3.6, 0.3), "concrete_grey", (0.22, 0.04, 0))
  box(layer, ((x0 + x1) / 2, 121.3, top - 0.38), (x1 - x0 + 0.5, 3.8, 0.12), "terracotta", (0.22, 0.04, 0))
  rebar(layer, ((x0 + x1) / 2, 116.9, top - 0.3), (0, 1, -0.5), 10, 0.8)
  # The upper floor fell in: slabs leaning on the south wall, out of the way.
  for k, x in enumerate((88.5, 93.5)):
    block(layer, (x, 114.0, 1.6), (3.5, 0.3, 3.4), "concrete_grey", (-0.45 - k * 0.1, 0, rng.uniform(-0.1, 0.1)))
  rubble(layer, (91.0, 114.3), (4.0, 0.6), 20, 0.7)
  # Living room: sofa, television, the table still set and the Virgin on the wall.
  block(layer, (88.6, 122.2, 0.25), (2.4, 0.8, 0.5), "fabric_red")
  box(layer, (88.6, 122.55, 0.6), (2.4, 0.2, 0.7), "fabric_red")
  block(layer, (90.6, 115.8, 0.35), (1.0, 0.5, 0.7), "wood_old")
  box(layer, (90.6, 115.8, 0.95), (0.8, 0.45, 0.5), "trash", (0, 0.4, 0))
  block(layer, (90.5, 120.7, 0.38), (1.6, 0.9, 0.76), "wood")
  for k in range(3):
    tube(layer, [((89.9 + k * 0.6, 120.7, 0.78), 0.13), ((89.9 + k * 0.6, 120.7, 0.8), 0.13)], "sign_white", n=8)
  plastic_chair(layer, 89.5, 119.9, 0.0, 0.0)
  plastic_chair(layer, 91.6, 121.6, 0.0, 2.8, fallen=True)
  box(layer, (x0 + 0.34, 121.0, 1.8), (0.02, 0.45, 0.6), "plaster_blue")
  box(layer, (x0 + 0.33, 121.0, 1.8), (0.02, 0.25, 0.4), "sign_white")
  # Kitchen: counter, sink, stove and the fridge that walked across the floor.
  block(layer, (95.5, 122.35, 0.45), (4.0, 0.6, 0.9), "tile_white")
  box(layer, (95.5, 122.35, 0.92), (4.05, 0.65, 0.04), "stone_cream")
  box(layer, (94.5, 122.35, 0.9), (0.6, 0.4, 0.06), "metal_grey")
  box(layer, (96.8, 122.35, 0.98), (0.6, 0.5, 0.06), "iron")
  block(layer, (96.6, 114.5, 0.9), (0.75, 0.7, 1.8), "sign_white", (0, 0, 0.3))
  for k in range(3):
    tube(layer, [((94.0 + k * 0.5, 122.6, 2.0), 0.012), ((94.0 + k * 0.5, 122.6, 1.6), 0.012)], "iron", n=3)
    tube(layer, [((94.0 + k * 0.5, 122.5, 1.5), 0.13), ((94.0 + k * 0.5, 122.5, 1.65), 0.13)], "rust", n=8)
  litter(layer, (x0 + 0.5, x1 - 0.5, y0 + 1.5, y1 - 0.5), 30, 0.02)
  # Outside: the door frame and the broken edges of the kitchen wall.
  box(layer, (x0 - 0.05, 118.25, 2.4), (0.15, 2.8, 0.2), "stone_cream")
  rubble(layer, (x1 + 0.6, 121.5), (0.6, 1.2), 10, 0.8)
  rubble(layer, (x1 + 0.6, 114.6), (0.5, 1.0), 8, 0.7)
  weeds(layer, (x0, y1), (x0, y0), 16)
  for k in range(3):
    ivy_curtain(layer, x0, -1, 114.0 + k * 3.5, top, 4.0, 0.15, 0.0)
  layer.build()


def build_lane():
  """Service lane from the square to the chapel, behind the alley's south row."""
  layer = Layer("route_lane")
  # Back yards on the south side, low enough to see the sky over them.
  for x0, x1, floors in ((40, 62, 2), (62, 80, 3), (80, 104, 2), (104, 130, 3)):
    building(layer, (x0, 94), (x1, 94), floors, rng.choice(("brick", "plaster")), depth=8, ivy=1, cracks=1)
  for x0, x1, height in ((50, 64, 10.5), (64, 86, 7.2), (86, 101, 10.5), (101, 118, 10.5), (118, 130, 13.8)):
    back_wall(layer, (x1, 99), (x0, 99), height)
  block(layer, (47.0, 99.0, 2.0), (6.0, 0.6, 4.0), "brick_dark")
  # Clutter of the yards that spilled into the lane, but never closing it.
  for x in (38.0, 58.0, 77.0, 98.0, 118.0):
    clothesline(layer, (x, 94.2), (x + rng.uniform(-1, 1), 98.8), 2.5)
  for x, y in ((45.0, 94.8), (73.0, 98.2), (112.0, 94.8)):
    tube(layer, [((x, y, 0.0), 0.55), ((x, y, 1.1), 0.55), ((x, y, 1.25), 0.2)], "trash", n=8)
    collide(layer, (x, y, 0.6), (1.1, 1.1, 1.2))
  # The dog's kennel, chain still tied to it.
  block(layer, (88.0, 95.0, 0.45), (1.0, 1.0, 0.9), "wood_old")
  box(layer, (88.0, 95.0, 1.0), (1.2, 1.2, 0.08), "rust", (0.2, 0, 0))
  for k in range(8):
    box(layer, (88.0 + k * 0.12, 95.6 + k * 0.08, 0.03), (0.1, 0.05, 0.04), "iron", (0, 0, k * 0.8))
  for k in range(6):
    tube(layer, [((63.0 + k * 9, 94.4, 0.0), 0.2), ((63.0 + k * 9, 94.4, 0.35), 0.24)], "terracotta", n=7)
    crown_dome(layer, (63.0 + k * 9, 94.4, 0.45), 0.4, 0.4, segments=7)
  plastic_chair(layer, 52.0, 95.0, 0.0, 0.6)
  plastic_chair(layer, 101.0, 98.0, 0.0, 1.9, fallen=True)
  tube(layer, [((67.5, 97.6, 0.4), 0.33), ((67.5, 97.65, 0.4), 0.33)], "iron", n=12)
  tube(layer, [((69.0, 97.6, 0.4), 0.33), ((69.0, 97.65, 0.4), 0.33)], "iron", n=12)
  tube(layer, [((67.5, 97.6, 0.4), 0.02), ((68.3, 97.6, 0.9), 0.02), ((69.0, 97.6, 0.4), 0.02)], "rust", n=3)
  for _ in range(5):
    box(layer, (rng.uniform(35, 125), rng.uniform(95, 98), 0.2), (0.5, 0.4, 0.4), "cardboard", (0, 0, rng.random()))
  litter(layer, (31, 129, 94.5, 98.5), 40)
  weeds(layer, (130, 99), (30, 99), 60, 0.8)
  layer.build()


# --- Chapel square and the shortcut gate --------------------------------------------------------

GATE_HINGE = (130.0, 94.5)
GATE_WIDTH = 4.0


def build_chapel_square():
  layer = Layer("route_chapel_square")
  block(layer, (145.0, 117.0, -0.25), (30, 46, 0.5), "stone_cream")
  for k in range(13):
    box(layer, (130.0 + k * 2.5, 117.0, 0.004), (0.05, 46, 0.008), "concrete_stain")
  for k in range(19):
    box(layer, (145.0, 94.0 + k * 2.5, 0.004), (30, 0.05, 0.008), "concrete_stain")
  floor_cracks(layer, (131, 159, 95, 139), 12)
  for _ in range(90):
    grass_tuft(layer, (rng.uniform(131, 159), rng.uniform(95, 139), 0.0), rng.uniform(0.2, 0.5))
  # Low colonial houses, painted, the only cheerful colors left in the zone.
  building(layer, (130, 94), (160, 94), 2, "plaster", depth=8)
  building(layer, (160, 140), (130, 140), 2, "plaster", depth=10, ivy=3)
  building(layer, (160, 94), (160, 105), 2, "plaster", depth=8)
  building(layer, (160, 125), (160, 140), 2, "plaster", depth=8)
  # A little in front of the alley's end walls, so the faces never fight.
  building(layer, (130.3, 112), (130.3, 99), 3, "plaster", depth=2, door=False)
  building(layer, (130.3, 140), (130.3, 124), 3, "plaster", depth=2, door=False)
  # Stone pillars of the gate to the lane.
  for y in (GATE_HINGE[1] - 0.35, GATE_HINGE[1] + GATE_WIDTH + 0.35):
    block(layer, (GATE_HINGE[0], y, 1.5), (0.7, 0.7, 3.0), "stone_cream")
    box(layer, (GATE_HINGE[0], y, 3.1), (0.9, 0.9, 0.2), "concrete_grey")
  # The mango tree everybody sat under, with its round bench.
  tree(layer, 138.0, 104.0, 8.0, 5.0)
  for k in range(10):
    angle = k * math.tau / 10
    block(layer, (138.0 + math.cos(angle) * 2.3, 104.0 + math.sin(angle) * 2.3, 0.25), (1.5, 0.45, 0.5), "stone_cream", (0, 0, angle + math.pi / 2))
  for _ in range(12):
    blade_plant(layer, (138.0 + rng.uniform(-1.8, 1.8), 104.0 + rng.uniform(-1.8, 1.8), 0.0), rng.uniform(0.6, 1.1), mat="leaf_light")
  for _ in range(14):
    fruit = (138.0 + rng.uniform(-4, 4), 104.0 + rng.uniform(-4, 4), 0.06)
    clump(layer, fruit, (0.08, 0.06, 0.06), "fruit", 0.1)
  bench(layer, 138.0, 128.0, 0.0)
  bench(layer, 152.0, 128.0, 0.0)
  bench(layer, 155.5, 100.0, 1.57)
  streetlight(layer, 152.5, 112.0, 3.14)
  # Pots of plants along the houses and candles left at the foot of the chapel.
  for x, y in ((133.0, 95.2), (141.0, 95.2), (149.0, 95.2), (157.0, 95.2), (133.0, 138.8), (157.0, 138.8), (158.8, 108.0), (158.8, 130.0)):
    tube(layer, [((x, y, 0.0), 0.32), ((x, y, 0.55), 0.4)], "terracotta", n=8)
    crown_dome(layer, (x, y, 0.62), 0.6, 0.6, segments=8)
    collide(layer, (x, y, 0.3), (0.8, 0.8, 0.6))
  for k in range(9):
    x = 143.2 + k * 0.45 + rng.uniform(-0.1, 0.1)
    tube(layer, [((x, 136.0 - rng.uniform(0, 0.4), 0.0), 0.04), ((x, 136.0, rng.uniform(0.1, 0.3)), 0.04)], "candle", n=5)
  litter(layer, (131, 159, 95, 139), 10)
  layer.build()
  build_gate()


def build_gate():
  """The iron gate as its own model: hinge at the origin, the leaf along +Y, opened by the game."""
  corners = A.PLAY_CORNERS
  A.PLAY_CORNERS = [Vector((x, y, z)) for x in (-8.0, 8.0) for y in (-8.0, 12.0) for z in (0.2, 4.0)]
  layer = Layer("shortcut_gate")
  w = GATE_WIDTH
  for z in (0.15, 1.3, 2.45):
    box(layer, (0, w / 2, z), (0.08, w - 0.1, 0.08), "iron")
  for k in range(15):
    y = 0.15 + k * (w - 0.3) / 14
    box(layer, (0, y, 1.35), (0.04, 0.04, 2.5), "iron")
    tube(layer, [((0, y, 2.6), 0.03), ((0, y, 2.75), 0.005)], "iron", n=4)
  box(layer, (0, 0.05, 1.3), (0.1, 0.1, 2.6), "iron")
  box(layer, (0, w - 0.05, 1.3), (0.1, 0.1, 2.6), "iron")
  for _ in range(10):
    box(layer, (0.03, rng.uniform(0.2, w - 0.2), rng.uniform(0.2, 2.4)), (0.02, rng.uniform(0.1, 0.4), rng.uniform(0.05, 0.2)), "rust")
  # Bolted from the chapel side (+X): a bar and a padlocked chain.
  box(layer, (0.12, w - 0.6, 1.2), (0.06, 0.9, 0.08), "metal_grey")
  for k in range(7):
    box(layer, (0.1, w - 0.25, 1.0 + k * 0.08), (0.04, 0.09, 0.05), "iron", (0, 0, (k % 2) * 1.57))
  box(layer, (0.15, w - 0.25, 0.92), (0.06, 0.12, 0.14), "hazard_yellow")
  layer.build()
  A.PLAY_CORNERS = corners


# --- Street to the cathedral ------------------------------------------------------------------


def stall(layer, x, y, tarp, fallen=False):
  """Market stall: four poles, a sagging tarp, a table and crates of fruit gone bad."""
  for sx in (-1.2, 1.2):
    for sy in (-0.9, 0.9):
      if fallen and sx > 0:
        tube(layer, [((x + sx, y + sy, 0.0), 0.04), ((x + sx + 0.9, y + sy, 0.25), 0.04)], "metal_grey", n=4)
      else:
        tube(layer, [((x + sx, y + sy, 0.0), 0.04), ((x + sx, y + sy, 2.3), 0.04)], "metal_grey", n=4)
  if fallen:
    box(layer, (x + 0.6, y, 1.2), (3.2, 2.4, 0.04), tarp, (0, 0.65, 0))
  else:
    box(layer, (x, y, 2.35), (2.8, 2.2, 0.04), tarp, (rng.uniform(-0.12, 0.12), rng.uniform(-0.05, 0.05), 0))
  block(layer, (x, y, 0.4), (2.0, 1.0, 0.8), "wood_old")
  for k in range(rng.randint(2, 4)):
    cx, cy = x + rng.uniform(-0.7, 0.7), y + rng.uniform(-0.3, 0.3)
    box(layer, (cx, cy, 0.95), (0.5, 0.35, 0.3), "wood")
    for _ in range(4):
      clump(layer, (cx + rng.uniform(-0.15, 0.15), cy + rng.uniform(-0.1, 0.1), 1.12), (0.08, 0.07, 0.07), rng.choice(("fruit", "brick_dark", "leaf_olive")), 0.15)


def tarp_heap(layer, x, y):
  """Tarp fallen over crates: a hump where a rat can sleep."""
  for _ in range(3):
    box(layer, (x + rng.uniform(-0.4, 0.4), y + rng.uniform(-0.3, 0.3), 0.25), (0.6, 0.45, 0.5), "wood")
  crown_dome(layer, (x, y, 0.05), 1.3, 0.75, segments=8)
  box(layer, (x + 0.8, y - 0.4, 0.02), (1.6, 1.4, 0.02), rng.choice(("tarp_blue", "tarp_orange")), (0, 0, rng.random()))


def chain_link(layer, x0, x1, y, height, gap=()):
  """Chain-link fence along x at y; gap is (x_from, x_to) torn open."""
  x = x0
  while x <= x1 + 0.01:
    if not gap or not gap[0] < x < gap[1]:
      tube(layer, [((x, y, 0.0), 0.04), ((x, y, height), 0.04)], "chain_link", n=5)
    x += 3.0
  for z in (0.1, height):
    for a, b in ((x0, gap[0]), (gap[1], x1)) if gap else ((x0, x1),):
      if b - a < 0.1:
        continue
      box(layer, ((a + b) / 2, y, z), (b - a, 0.04, 0.04), "chain_link")
  step = 0.45
  for a, b in ((x0, gap[0]), (gap[1], x1)) if gap else ((x0, x1),):
    if b - a < 0.1:
      continue
    k = a
    while k < b - 0.1:
      for direction in (1, -1):
        box(layer, (k + 0.225, y, height / 2), (0.015, 0.015, height * 1.42), "chain_link", (0, direction * 0.24, 0))
      k += step
    collide(layer, ((a + b) / 2, y, height / 2), (b - a, 0.12, height))
  if gap:
    # The torn flap, rolled back where the dogs push through.
    box(layer, (gap[0] + 0.6, y + 0.4, 1.2), (1.2, 0.03, 2.2), "chain_link", (0.3, 0, 0.8))


def build_street():
  layer = Layer("route_street_ground")
  block(layer, (210.0, 115.0, -0.25), (100, 20, 0.5), "asphalt")
  for y in (106.5, 123.5):
    block(layer, (204.0, y, 0.09), (88, 3, 0.18), "sidewalk")
    box(layer, (204.0, y + (1.4 if y > 115 else -1.4) * -1, 0.1), (88, 0.26, 0.2), "curb")
  y = 115.0
  for k in range(20):
    box(layer, (163.0 + k * 4.5, y, 0.012), (2.2, 0.16, 0.012), "road_paint")
  floor_cracks(layer, (161, 259, 108.5, 121.5), 40)
  puddles(layer, (162, 258, 109, 121), 10)
  for _ in range(160):
    grass_tuft(layer, (rng.uniform(161, 259), rng.uniform(106, 124), 0.18), rng.uniform(0.2, 0.6))
  layer.build()

  layer = Layer("route_street_buildings")
  # Both rows start past the chapel square's corner houses (x 160 to 168).
  for x0, x1, floors in ((168, 176, 2), (176, 196, 3), (196, 216, 2), (216, 234, 4), (234, 248, 3)):
    building(layer, (x0, 105), (x1, 105), floors, "concrete", depth=9, shops=True)
  for x1, x0, floors in ((178, 168, 3), (196, 178, 2), (216, 196, 3)):
    building(layer, (x1, 125), (x0, 125), floors, "concrete", depth=12, shops=True)
  # The court behind its fence, closed by houses on three sides.
  building(layer, (244, 140), (216, 140), 3, "brick", depth=10)
  building(layer, (216, 140), (216, 125), 3, "brick", depth=2, door=False)
  building(layer, (244, 125), (244, 140), 3, "concrete", depth=4, door=False)
  # Where the street narrows, the last houses lean in towards the cathedral square.
  building(layer, (248, 112), (260, 112), 2, "plaster", depth=7, cracks=4)
  building(layer, (260, 118), (248, 118), 2, "plaster", depth=7, cracks=4)
  # Claw marks: three deep grooves at shoulder height of something huge.
  for x, y, side in ((251.0, 112.0, 1), (255.0, 118.0, -1), (257.5, 112.0, 1)):
    for k in range(3):
      box(layer, (x + k * 0.25, y + side * 0.03, 1.9), (0.06, 0.05, 1.1), "crack", (0, -0.35, 0))
  layer.build()

  layer = Layer("route_street_props")
  # Bachaquero's shop: a rolled-up shutter, a counter and his goods.
  block(layer, (172.0, 107.9, 0.5), (3.0, 0.8, 1.0), "wood")
  box(layer, (172.0, 107.9, 1.03), (3.1, 0.9, 0.06), "metal_grey")
  for k in range(6):
    box(layer, (170.9 + k * 0.42, 107.9, 1.2), (0.25, 0.25, 0.3), rng.choice(("sign_red", "sign_yellow", "cardboard", "sign_blue")))
  box(layer, (172.0, 107.0, 2.8), (3.6, 2.4, 0.04), "tarp_blue", (0.15, 0, 0))
  for x in (170.3, 173.7):
    tube(layer, [((x, 108.1, 0.18), 0.04), ((x, 108.1, 2.9), 0.04)], "metal_grey", n=4)
  # Market of tarps.
  for x, y, tarp, fallen in ((186.0, 109.5, "tarp_blue", False), (191.0, 109.5, "tarp_orange", True), (197.0, 109.5, "tarp_blue", False), (205.0, 120.5, "tarp_orange", False), (210.0, 120.5, "tarp_blue", True), (188.0, 120.5, "tarp_orange", False)):
    stall(layer, x, y, tarp, fallen)
  for x, y in ((192.0, 112.0), (200.0, 121.0), (204.0, 112.5)):
    tarp_heap(layer, x, y)
  box(layer, (199.0, 115.0, 0.02), (3.4, 2.6, 0.02), "tarp_blue", (0.04, 0.02, 0.4))
  # Cars and the bus that blocks half the way.
  car(layer, (195.0, 111.0, 0.0), (0, 0, 1.57), "car_red")
  collide(layer, (195.0, 111.0, 0.75), (4.8, 2.0, 1.5))
  car(layer, (222.0, 120.0, 0.0), (0, 0, 1.45), "car_blue")
  collide(layer, (222.0, 120.0, 0.75), (4.8, 2.0, 1.5), (0, 0, -0.12))
  A.bus(layer, (240.0, 110.0, 0.0), (0, 0.03, 1.57))
  collide(layer, (240.0, 110.0, 1.5), (10.6, 3.6, 3.0))
  A.overgrow(layer, (240.0, 110.0, 3.1), (2.6, 0.7, 0.2), 20)
  # The court: lines, two hoops and the dogs' corner with what is left of their meals.
  block(layer, (230.0, 132.5, -0.25), (28, 15, 0.5), "asphalt")
  box(layer, (230.0, 132.5, 0.015), (28, 15, 0.03), "court_green")
  for x in (217.5, 230.0, 242.5):
    box(layer, (x, 132.5, 0.035), (0.08, 13.0, 0.01), "court_line")
  for y in (126.0, 139.0):
    box(layer, (230.0, y, 0.035), (25.0, 0.08, 0.01), "court_line")
  tube(layer, [((230.0, 132.5, 0.035), 1.8), ((230.0, 132.5, 0.04), 1.8)], "court_line", n=16)
  tube(layer, [((230.0, 132.5, 0.036), 1.7), ((230.0, 132.5, 0.045), 1.7)], "court_green", n=16)
  for x, out in ((217.0, 1), (243.0, -1)):
    block(layer, (x, 132.5, 1.6), (0.18, 0.18, 3.2), "metal_grey")
    box(layer, (x + out * 0.5, 132.5, 3.3), (0.06, 1.8, 1.05), "sign_white")
    tube(layer, [((x + out * 0.9, 132.5, 3.05), 0.23), ((x + out * 0.9, 132.5, 3.07), 0.23)], "hazard_yellow" if out > 0 else "rust", n=10)
  chain_link(layer, 216.0, 244.0, 125.0, 3.5, gap=(216.0, 219.5))
  box(layer, (236.0, 137.5, 0.12), (2.0, 1.4, 0.24), "mattress")
  flat_blob(layer, (236.2, 137.4), (0.6, 0.4), "mattress_stain", 0.25)
  for _ in range(14):
    x, y = rng.uniform(220, 242), rng.uniform(127, 139)
    tube(layer, [((x, y, 0.04), 0.035), ((x + rng.uniform(-0.3, 0.3), y + rng.uniform(-0.3, 0.3), 0.04), 0.03)], "bone", n=4)
  tube(layer, [((226.0, 130.0, 0.3), 0.3), ((226.2, 130.0, 0.3), 0.3)], "tire", n=10)
  # Narrowing to the square: bones, the broken chain and a collar.
  rubble(layer, (251.0, 113.0), (2.0, 0.8), 12, 1.0, 0.9)
  rubble(layer, (257.0, 117.2), (1.6, 0.6), 10, 0.9, 0.8)
  for _ in range(24):
    x, y = rng.uniform(247, 259), rng.uniform(113.5, 116.8)
    tube(layer, [((x, y, 0.04), rng.uniform(0.025, 0.05)), ((x + rng.uniform(-0.5, 0.5), y + rng.uniform(-0.2, 0.2), 0.05), 0.025)], "bone", n=4)
  clump(layer, (253.0, 114.5, 0.12), (0.14, 0.12, 0.12), "bone", 0.1)
  for k in range(14):
    box(layer, (249.0 + k * 0.22, 115.6 + math.sin(k * 0.7) * 0.25, 0.04), (0.2, 0.08, 0.05), "rust", (0, 0, k * 1.57 % 3.14))
  tube(layer, [((255.0, 115.2, 0.03), 0.2), ((255.0, 115.25, 0.03), 0.2)], "fabric_red", n=10)
  # Overturned kiosk by the narrowing.
  layer.place((252.0, 116.4, 0.6), (0, 1.45, 0.3))
  box(layer, (0, 0, 0), (1.2, 1.6, 2.2), "sign_blue")
  box(layer, (0, -0.82, 0), (0.9, 0.04, 1.1), "shutter")
  layer.reset()
  collide(layer, (252.0, 116.4, 0.6), (2.2, 1.6, 1.2), (0, 0, 0.3))
  for x, y, yaw in ((168.0, 123.6, 4.7), (226.0, 106.4, 1.57)):
    streetlight(layer, x, y, yaw)
  for x in (175.0, 200.0, 228.0):
    cable(layer, (x, 105.0, 7.0), (x + 4.0, 125.0, 7.5), 1.2)
  litter(layer, (161, 259, 108, 122), 70)
  layer.build()


# --- Cathedral square: Guino's arena -----------------------------------------------------------

FOUNTAIN = (285.0, 115.0)


def build_cathedral_square():
  layer = Layer("route_arena_ground")
  block(layer, (286.0, 115.0, -0.25), (54, 62, 0.5), "stone_cream")
  for k in range(20):
    angle = k * math.tau / 20
    box(layer, (FOUNTAIN[0] + math.cos(angle) * 14, FOUNTAIN[1] + math.sin(angle) * 14, 0.004), (21, 0.06, 0.008), "concrete_stain", (0, 0, angle))
  for radius in (6.0, 12.0, 18.0):
    for k in range(int(radius * 2)):
      angle = k * math.tau / int(radius * 2)
      box(layer, (FOUNTAIN[0] + math.cos(angle) * radius, FOUNTAIN[1] + math.sin(angle) * radius, 0.004), (0.06, radius * math.tau / int(radius * 2), 0.008), "concrete_stain", (0, 0, angle))
  floor_cracks(layer, (262, 308, 87, 143), 50)
  puddles(layer, (264, 306, 89, 141), 10)
  for _ in range(240):
    grass_tuft(layer, (rng.uniform(261, 309), rng.uniform(86, 144), 0.0), rng.uniform(0.2, 0.6))
  # Scratches all over the stones where he turns and lands.
  for _ in range(30):
    x, y = rng.uniform(268, 302), rng.uniform(95, 135)
    angle = rng.random() * math.tau
    for k in range(3):
      box(layer, (x + math.cos(angle + 1.57) * k * 0.18, y + math.sin(angle + 1.57) * k * 0.18, 0.007), (rng.uniform(0.8, 1.5), 0.04, 0.008), "crack", (0, 0, angle))
  layer.build()

  layer = Layer("route_arena_buildings")
  # The narrowing street's houses close the west side between y 105 and 125.
  building(layer, (260, 145), (260, 125), 2, "plaster", depth=10)
  building(layer, (260, 105), (260, 85), 2, "plaster", depth=10)
  building(layer, (260, 85), (310, 85), 2, "plaster", depth=10, ivy=3)
  building(layer, (310, 145), (260, 145), 2, "plaster", depth=10, ivy=3)
  building(layer, (310, 85), (310, 96), 2, "plaster", depth=3, door=False)
  building(layer, (310, 134), (310, 145), 2, "plaster", depth=3, door=False)
  layer.build()
  build_cathedral()

  layer = Layer("route_arena_props")
  # The dry fountain: a broken octagon, its pedestal cracked and the top bowl fallen in.
  radius = 3.5
  side = 2 * radius * math.tan(math.pi / 8)
  for k in range(8):
    angle = k * math.pi / 4 + math.pi / 8
    x = FOUNTAIN[0] + math.cos(angle) * radius
    y = FOUNTAIN[1] + math.sin(angle) * radius
    drop = 0.12 if k == 2 else 0.0
    block(layer, (x, y, 0.225 - drop), (0.45, side + 0.1, 0.45), "stone_cream", (0.08 if k == 2 else 0, 0, angle))
    box(layer, (x, y, 0.47 - drop), (0.55, side + 0.15, 0.06), "concrete_grey", (0.08 if k == 2 else 0, 0, angle))
  tube(layer, [((FOUNTAIN[0], FOUNTAIN[1], 0.0), radius - 0.2), ((FOUNTAIN[0], FOUNTAIN[1], 0.08), radius - 0.2)], "concrete_stain", n=8)
  flat_blob(layer, (FOUNTAIN[0] + 1.0, FOUNTAIN[1] - 0.8), (1.6, 1.2), "puddle", 0.1)
  tube(layer, [((FOUNTAIN[0], FOUNTAIN[1], 0.0), 0.8), ((FOUNTAIN[0], FOUNTAIN[1], 0.5), 0.6), ((FOUNTAIN[0], FOUNTAIN[1], 1.3), 0.4), ((FOUNTAIN[0], FOUNTAIN[1], 1.5), 0.55)], "stone_cream", n=8)
  collide(layer, (FOUNTAIN[0], FOUNTAIN[1], 0.75), (1.4, 1.4, 1.5))
  layer.place((FOUNTAIN[0] + 1.3, FOUNTAIN[1] + 0.6, 0.35), (0.5, 0.3, 0))
  tube(layer, [((0, 0, 0), 1.2), ((0, 0, 0.25), 1.4)], "stone_cream", n=10)
  layer.reset()
  box(layer, (FOUNTAIN[0], FOUNTAIN[1] - 1.1, 0.1), (0.1, 2.2, 0.04), "crack", (0, 0, 0.3))
  # Low cover along the edges only: the middle stays clear for his leaps and his tail.
  for x, y, yaw in ((264.0, 92.0, 1.57), (264.0, 128.0, 1.57), (282.0, 142.5, 0.0), (276.0, 87.5, 0.0)):
    bench(layer, x, y, yaw, broken=rng.random() < 0.5)
  for x, y in ((264.5, 140.0), (270.0, 88.5), (296.0, 142.0), (264.5, 102.0)):
    block(layer, (x, y, 0.45), (1.6, 1.6, 0.9), "concrete_grey")
    crown_dome(layer, (x, y, 0.95), 0.9, 0.7, segments=8)
  car(layer, (299.0, 88.6, 0.0), (0, 0, 1.62), "car_yellow")
  collide(layer, (299.0, 88.6, 0.75), (4.8, 2.0, 1.5), (0, 0, 0.05))
  A.overgrow(layer, (299.0, 88.6, 1.3), (1.2, 0.5, 0.3), 10)
  # The north tower's top lies in the corner where it fell.
  rubble(layer, (305.0, 140.5), (3.5, 3.0), 50, 2.0, 1.6)
  block(layer, (302.5, 138.5, 1.2), (3.0, 3.0, 2.4), "plaster_white", (0.3, -0.2, 0.5))
  for x, y, yaw in ((262.5, 96.0, 0.0), (262.5, 134.0, 0.0), (307.5, 100.0, 3.14)):
    streetlight(layer, x, y, yaw, broken=yaw == 3.14)
  litter(layer, (262, 308, 87, 143), 40)
  layer.build()


def build_cathedral():
  """Colonial cathedral, half fallen. Its porch is Guino's den; the doors lead to the jungle."""
  layer = Layer("route_cathedral")
  fx = 312.0
  # Nave and facade.
  block(layer, (fx + 14.0, 115.0, 8.0), (28.0, 26.0, 16.0), "plaster_white", hide=True)
  frame(layer, (fx, 102.0), (fx, 128.0))
  for z, depth in ((0.3, 0.3), (8.0, 0.35), (15.8, 0.5)):
    box(layer, (-depth / 2, 13.0, z), (depth, 26.2, 0.4), "stone_cream")
  for y in (1.0, 7.5, 18.5, 25.0):
    box(layer, (-0.25, y, 8.0), (0.5, 1.0, 16.0), "stone_cream")
  # Big door under a round arch, two side doors, a rose window.
  box(layer, (-0.06, 13.0, 2.9), (0.12, 4.2, 5.8), "wood")
  for k in range(4):
    box(layer, (-0.14, 11.4 + k * 1.05, 2.9), (0.04, 0.12, 5.4), "wood_old")
  for k in range(9):
    angle = math.pi * k / 8
    box(layer, (-0.3, 13.0 + math.cos(angle) * 2.5, 5.8 + math.sin(angle) * 2.5), (0.5, 0.9, 0.5), "stone_cream", (-angle, 0, 0))
  for y in (5.0, 21.0):
    box(layer, (-0.06, y, 2.0), (0.12, 2.0, 4.0), "wood_old")
    box(layer, (-0.2, y, 4.2), (0.3, 2.6, 0.4), "stone_cream")
  tube(layer, [((-0.2, 13.0, 11.5), 1.6), ((-0.05, 13.0, 11.5), 1.6)], "window_dark", n=12)
  tube(layer, [((-0.3, 13.0, 11.5), 1.9), ((-0.22, 13.0, 11.5), 1.9)], "stone_cream", n=12)
  # Gable: two deep slabs whose lower halves sink into the nave, with the bell wall on top.
  slope = math.atan2(5.5, 13.0)
  for side in (-1, 1):
    middle = Vector((0.25, 13.0 + side * 6.5, 18.75))
    normal = Vector((0, side * math.sin(slope), math.cos(slope)))
    box(layer, tuple(middle - normal * 3.5), (0.4, 14.3, 7.0), "plaster_white", (-side * slope, 0, 0))
    box(layer, tuple(middle + normal * 0.15 + Vector((-0.2, 0, 0))), (0.5, 14.4, 0.3), "stone_cream", (-side * slope, 0, 0))
  box(layer, (-0.2, 13.0, 22.5), (0.6, 4.0, 2.4), "plaster_white")
  box(layer, (-0.25, 13.0, 22.4), (0.7, 1.4, 1.6), "window_dark")
  for _ in range(5):
    crack(layer, rng.uniform(2, 24), rng.uniform(8, 15), 5.0, rng.uniform(-2.4, -0.7))
  for k in range(3):
    ivy_curtain(layer, 0, -1, 3.0 + k * 10.0, 15.5, 9.0, 0.5, 0.0)
  layer.reset()
  # Fallen beam across the main door: closed until the way to the jungle opens.
  block(layer, (fx - 0.6, 115.0, 1.6), (0.5, 5.6, 0.5), "wood_old", (0.45, 0, 0))
  collide(layer, (fx - 0.4, 115.0, 3.0), (0.6, 4.4, 6.0))
  for side in (-1, 1):
    # Bell towers: the south one whole, the north one snapped above the belfry.
    y = 115.0 + side * 16.0
    broken = side > 0
    height = 18.0 if broken else 22.0
    block(layer, (fx + 3.0, y, height / 2), (6.0, 6.0, height), "plaster_white", hide=True)
    for z in (0.4, 8.0, 15.8):
      box(layer, (fx + 3.0, y, z), (6.4, 6.4, 0.4), "stone_cream")
    for k in range(2):
      box(layer, (fx - 0.05, y, 5.0 + k * 6.0), (0.1, 1.0, 2.0), "window_dark")
    if broken:
      for _ in range(14):
        size = rng.uniform(0.6, 1.6)
        clump(layer, (fx + 3.0 + rng.uniform(-2.6, 2.6), y + rng.uniform(-2.6, 2.6), height + size * 0.3), (size, size, size * 0.8), rng.choice(("plaster_white", "brick_red", "stone_cream")), 0.35)
      rebar(layer, (fx + 0.2, y, height), (-1, 0, 0.6), 8, 1.2)
      continue
    for dx in (-2.5, 2.5):
      for dy in (-2.5, 2.5):
        box(layer, (fx + 3.0 + dx, y + dy, height + 3.0), (1.0, 1.0, 6.0), "plaster_white")
    tube(layer, [((fx + 3.0, y, height + 2.5), 0.9), ((fx + 3.0, y, height + 3.8), 0.6)], "rust", n=8)
    box(layer, (fx + 3.0, y, height + 6.2), (6.6, 6.6, 0.5), "stone_cream")
    tube(layer, [((fx + 3.0, y, height + 6.4), 3.0), ((fx + 3.0, y, height + 11.0), 0.3)], "terracotta", n=4)
    box(layer, (fx + 3.0, y, height + 12.2), (0.12, 0.12, 2.0), "iron")
    box(layer, (fx + 3.0, y, height + 12.6), (0.12, 1.0, 0.12), "iron")
  # The porch: four columns with arches, a tiled roof, and the den underneath.
  px = 305.0
  for y in (105.0, 111.7, 118.3, 125.0):
    block(layer, (px, y, 3.0), (0.8, 0.8, 6.0), "stone_cream")
    box(layer, (px, y, 0.25), (1.1, 1.1, 0.5), "concrete_grey")
  for y0, y1 in ((105.0, 111.7), (111.7, 118.3), (118.3, 125.0)):
    for k in range(7):
      angle = math.pi * (k + 0.5) / 7
      mid = (y0 + y1) / 2
      r = (y1 - y0) / 2
      box(layer, (px, mid - math.cos(angle) * r, 4.6 + math.sin(angle) * 1.2), (0.7, 1.1, 0.6), "stone_cream", (-(angle - math.pi / 2) * 0.6, 0, 0))
  block(layer, ((px + fx) / 2, 115.0, 6.3), (fx - px + 1.0, 21.0, 0.5), "plaster_white")
  box(layer, ((px + fx) / 2 - 0.2, 115.0, 6.75), (fx - px + 1.6, 21.6, 0.3), "terracotta", (0, -0.12, 0))
  for y0, y1 in ((104.6, 105.4), (124.6, 125.4)):
    block(layer, ((px + fx) / 2, (y0 + y1) / 2, 3.0), (fx - px, 0.6, 6.0), "plaster_white")
  # Den: torn mattresses, heaps of bones and the rusted plates somebody kept filling.
  for x, y, angle in ((308.5, 109.0, 0.2), (309.0, 113.5, -0.1), (308.0, 119.0, 0.4), (309.5, 122.5, 0.0)):
    box(layer, (x, y, 0.14), (2.0, 1.4, 0.28), "mattress", (0, 0, angle))
    flat_blob(layer, (x + 0.2, y), (0.6, 0.4), "mattress_stain", 0.29)
  for _ in range(60):
    x, y = rng.uniform(306.0, 311.5), rng.uniform(106.0, 124.0)
    tube(layer, [((x, y, 0.06), rng.uniform(0.03, 0.06)), ((x + rng.uniform(-0.6, 0.6), y + rng.uniform(-0.6, 0.6), 0.06), 0.03)], "bone", n=4)
  for x, y in ((307.0, 116.0), (310.5, 111.0), (306.8, 107.5)):
    for _ in range(6):
      clump(layer, (x + rng.uniform(-0.4, 0.4), y + rng.uniform(-0.4, 0.4), 0.15), (0.2, 0.08, 0.08), "bone", 0.2)
    clump(layer, (x, y, 0.2), (0.16, 0.16, 0.14), "bone", 0.1)
  for x, y in ((306.5, 112.5), (307.2, 113.2), (306.4, 120.3), (310.8, 117.0)):
    tube(layer, [((x, y, 0.0), 0.22), ((x, y, 0.06), 0.25)], "rust", n=10)
  tube(layer, [((310.6, 106.0, 0.3), 0.32), ((310.8, 106.0, 0.3), 0.32)], "tire", n=10)
  for k in range(16):
    box(layer, (305.4 + k * 0.08, 118.3 + math.sin(k) * 0.1, 0.5 - k * 0.03), (0.09, 0.06, 0.06), "rust", (0, 0, k * 1.57 % 3.14))
  layer.build()


def build_colliders():
  # Godot turns meshes named -colonly into static collision and does not draw them.
  groups = {}
  for matrix, size, name in colliders:
    groups.setdefault(name, []).append((matrix, size))
  for name, boxes in groups.items():
    verts = []
    faces = []
    for matrix, size in boxes:
      half = size / 2
      offset = len(verts)
      verts.extend(matrix @ Vector((sx * half.x, sy * half.y, sz * half.z)) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1))
      faces.extend(tuple(i + offset for i in face) for face in A.BOX_FACES)
    mesh = bpy.data.meshes.new(f"route_{name}_collision")
    mesh.from_pydata([tuple(v) for v in verts], [], faces)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(f"route_{name}_collision-colonly", mesh)
    obj.display_type = "WIRE"
    obj.hide_render = True
    collection().objects.link(obj)


def start_section(name):
  global section
  section = name


def clear():
  A.clear()
  result = bpy.data.collections.get("route")
  if result:
    for obj in list(result.objects):
      bpy.data.objects.remove(obj)
  colliders.clear()


def finish():
  bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
  os.makedirs(os.path.dirname(GLB_PATH), exist_ok=True)
  gate = bpy.data.objects.get("shortcut_gate")
  if gate:
    gate.hide_set(True)
  bpy.ops.export_scene.gltf(filepath=GLB_PATH, export_format="GLB", use_visible=True)
  if gate:
    gate.hide_set(False)
    bpy.ops.object.select_all(action="DESELECT")
    gate.select_set(True)
    bpy.ops.export_scene.gltf(filepath=GATE_GLB_PATH, export_format="GLB", use_selection=True)


STAGES = [
  clear,
  lambda: start_section("square"), build_square_ground, build_square_buildings, build_store, build_fallen_house, build_square_props,
  lambda: start_section("alley"), build_alley,
  lambda: start_section("chapel"), build_chapel_square,
  lambda: start_section("street"), build_street,
  lambda: start_section("cathedral"), build_cathedral_square,
  build_colliders, finish,
]

if __name__ == "__main__":
  for stage in STAGES:
    stage()
