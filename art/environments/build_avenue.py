# Builds the first stage from code: an abandoned Caracas avenue taken over by plants.
# The street runs along Y; the player walks towards +Y, with El Avila behind the tower.
#   blender --background --python art/environments/build_avenue.py
import math
import os
import random

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
BLEND_PATH = os.path.join(HERE, "avenue.blend")
GLB_PATH = os.path.join(HERE, "..", "..", "game", "models", "environments", "avenue.glb")

STREET_HALF = 6.0
SIDEWALK_EDGE = 9.5
AVENUE_START = -46.0
AVENUE_END = 46.0

# name: (sRGB color, roughness, metallic)
MATERIALS = {
  "asphalt": ((0.20, 0.20, 0.21), 0.95, 0.0),
  "asphalt_patch": ((0.15, 0.15, 0.16), 0.95, 0.0),
  "crack": ((0.05, 0.05, 0.055), 1.0, 0.0),
  "road_paint": ((0.72, 0.62, 0.30), 0.9, 0.0),
  "road_white": ((0.68, 0.68, 0.64), 0.9, 0.0),
  "sidewalk": ((0.47, 0.45, 0.41), 0.95, 0.0),
  "curb": ((0.60, 0.58, 0.53), 0.95, 0.0),
  "puddle": ((0.06, 0.08, 0.09), 0.05, 0.45),
  "dirt": ((0.27, 0.20, 0.13), 1.0, 0.0),
  "brick_red": ((0.56, 0.21, 0.13), 0.95, 0.0),
  "brick_orange": ((0.74, 0.34, 0.12), 0.95, 0.0),
  "brick_dark": ((0.38, 0.15, 0.10), 0.95, 0.0),
  "concrete_warm": ((0.70, 0.40, 0.16), 0.95, 0.0),
  "concrete_stain": ((0.33, 0.24, 0.16), 1.0, 0.0),
  "concrete_grey": ((0.42, 0.42, 0.42), 0.95, 0.0),
  "stone_cream": ((0.76, 0.68, 0.52), 0.9, 0.0),
  "window_dark": ((0.05, 0.06, 0.07), 0.25, 0.3),
  "window_frame": ((0.33, 0.30, 0.26), 0.8, 0.0),
  "iron": ((0.09, 0.09, 0.10), 0.7, 0.6),
  "rust": ((0.36, 0.17, 0.09), 0.9, 0.3),
  "shutter": ((0.40, 0.40, 0.42), 0.6, 0.6),
  "wood": ((0.34, 0.21, 0.11), 0.95, 0.0),
  "wood_old": ((0.25, 0.20, 0.15), 1.0, 0.0),
  "metal_grey": ((0.52, 0.53, 0.55), 0.5, 0.7),
  "pole_concrete": ((0.48, 0.48, 0.46), 0.95, 0.0),
  "cable": ((0.03, 0.03, 0.035), 0.8, 0.0),
  "tire": ((0.05, 0.05, 0.05), 0.95, 0.0),
  "bus_red": ((0.74, 0.08, 0.07), 0.55, 0.1),
  "bus_yellow": ((0.86, 0.64, 0.12), 0.55, 0.1),
  "car_yellow": ((0.82, 0.60, 0.10), 0.6, 0.1),
  "car_red": ((0.60, 0.07, 0.08), 0.6, 0.1),
  "car_blue": ((0.12, 0.20, 0.38), 0.6, 0.1),
  "glass": ((0.10, 0.14, 0.15), 0.1, 0.5),
  "hydrant": ((0.72, 0.06, 0.05), 0.6, 0.1),
  "hazard_yellow": ((0.85, 0.66, 0.08), 0.8, 0.0),
  "hazard_black": ((0.06, 0.06, 0.06), 0.8, 0.0),
  "sign_blue": ((0.08, 0.20, 0.50), 0.7, 0.0),
  "sign_yellow": ((0.88, 0.70, 0.10), 0.7, 0.0),
  "sign_red": ((0.70, 0.10, 0.08), 0.7, 0.0),
  "sign_white": ((0.82, 0.82, 0.78), 0.7, 0.0),
  "trash": ((0.06, 0.06, 0.07), 0.35, 0.0),
  "vine": ((0.20, 0.25, 0.09), 0.9, 0.0),
  "bark": ((0.22, 0.15, 0.09), 1.0, 0.0),
  "leaf_dark": ((0.11, 0.26, 0.07), 0.8, 0.0),
  "leaf_mid": ((0.19, 0.38, 0.09), 0.8, 0.0),
  "leaf_light": ((0.34, 0.50, 0.12), 0.8, 0.0),
  "leaf_olive": ((0.33, 0.37, 0.12), 0.8, 0.0),
  "grass": ((0.25, 0.42, 0.11), 0.9, 0.0),
  "deer": ((0.52, 0.33, 0.17), 0.9, 0.0),
  "bird": ((0.03, 0.03, 0.035), 0.8, 0.0),
  "mountain": ((0.10, 0.17, 0.11), 1.0, 0.0),
  "mountain_far": ((0.16, 0.21, 0.19), 1.0, 0.0),
  "skyline": ((0.20, 0.21, 0.24), 1.0, 0.0),
  "cloud": ((0.16, 0.17, 0.20), 1.0, 0.0),
  "cloud_light": ((0.28, 0.29, 0.32), 1.0, 0.0),
}

LEAVES = ("leaf_dark", "leaf_mid", "leaf_light", "leaf_olive")

rng = random.Random(58)
tint_rng = random.Random(58)
colliders = []
facades = []
solids = []
BOX_FACES = (
  (0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5),
)
ICO_VERTS = []
ICO_FACES = []


# The whole stage shares these few materials; color lives in the vertices, so the
# named colors above cost no extra draw calls. name: (roughness, metallic, one sided)
MASTERS = {
  "matte": (0.92, 0.0, True),
  "wet": (0.32, 0.0, True),
  "metal": (0.55, 0.45, True),
  "glossy": (0.06, 0.7, False),
  "cards": (0.8, 0.0, False),
}
MASTER_NAMES = list(MASTERS)
WET_NAMES = {"asphalt", "asphalt_patch", "crack", "road_paint", "road_white", "sidewalk", "curb"}
GRIME_NAMES = {
  "brick_red", "brick_orange", "brick_dark", "concrete_warm", "concrete_stain", "concrete_grey", "stone_cream",
  "sidewalk", "curb", "pole_concrete",
}

# Where the player and the third-person camera can ever be. Solid faces turned away
# from all of this box can never be seen, whatever the exact camera position.
PLAY_CORNERS = [
  Vector((x, y, z))
  for x in (-SIDEWALK_EDGE, SIDEWALK_EDGE) for y in (AVENUE_START, AVENUE_END) for z in (0.2, 5.0)
]


def master_for(name, double_sided):
  if name == "puddle" or name == "glass" or name == "window_dark":
    return "glossy"
  if double_sided:
    return "cards"
  if name in WET_NAMES:
    return "wet"
  if MATERIALS[name][2] >= 0.1:
    return "metal"
  return "matte"


def linear_color(name):
  # Stored unconverted: the export path to Godot already applies the display curve.
  return Vector(MATERIALS[name][0])


def material(name):
  existing = bpy.data.materials.get("avenue_" + name)
  if existing:
    return existing
  roughness, metallic, one_sided = MASTERS[name]
  mat = bpy.data.materials.new("avenue_" + name)
  mat.use_nodes = True
  mat.use_backface_culling = one_sided
  nodes = mat.node_tree
  bsdf = nodes.nodes.get("Principled BSDF")
  bsdf.inputs["Roughness"].default_value = roughness
  bsdf.inputs["Metallic"].default_value = metallic
  vertex_color = nodes.nodes.new("ShaderNodeVertexColor")
  vertex_color.layer_name = "color"
  nodes.links.new(vertex_color.outputs["Color"], bsdf.inputs["Base Color"])
  return mat


def collection():
  result = bpy.data.collections.get("avenue")
  if not result:
    result = bpy.data.collections.new("avenue")
    bpy.context.scene.collection.children.link(result)
  return result


class Layer:
  """Collects geometry and becomes one object, which keeps the stage to a few draw calls."""

  def __init__(self, name, chunk=0.0):
    self.name = name
    # Long layers split along the street so Godot can skip what is behind the camera.
    self.chunk = chunk
    self.verts = []
    self.faces = []
    self.face_materials = []
    self.face_double = []
    self.face_tints = []
    self.matrix = Matrix.Identity(4)

  def add(self, verts, faces, mat, double_sided=False):
    offset = len(self.verts)
    self.verts.extend(self.matrix @ Vector(v) for v in verts)
    self.faces.extend(tuple(i + offset for i in face) for face in faces)
    self.face_materials.extend([mat] * len(faces))
    self.face_double.extend([double_sided] * len(faces))
    # One shade per object, so foliage and rubble never look stamped out.
    spread = 0.22 if mat in LEAVES else 0.08
    self.face_tints.extend([tint_rng.uniform(1.0 - spread, 1.0 + spread)] * len(faces))

  def place(self, position, rotation=(0, 0, 0)):
    self.matrix = Matrix.Translation(position) @ Euler(rotation).to_matrix().to_4x4()

  def reset(self):
    self.matrix = Matrix.Identity(4)

  def build(self):
    buckets = {}
    for index, face in enumerate(self.faces):
      key = 0
      if self.chunk:
        middle = sum(self.verts[i].y for i in face) / len(face)
        key = int(middle // self.chunk)
      buckets.setdefault(key, []).append(index)
    for key, indices in sorted(buckets.items()):
      name = f"{self.name}_{key + 50}" if self.chunk else self.name
      self.build_chunk(name, indices)

  def build_chunk(self, name, indices):
    remap = {}
    verts = []
    faces = []
    for index in indices:
      for vertex in self.faces[index]:
        if vertex not in remap:
          remap[vertex] = len(verts)
          verts.append(tuple(self.verts[vertex]))
      faces.append(tuple(remap[vertex] for vertex in self.faces[index]))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    color_layer = bm.loops.layers.float_color.new("color")
    hidden = []
    triangles_before = 0
    for face, index in zip(bm.faces, indices):
      mat = self.face_materials[index]
      master = master_for(mat, self.face_double[index])
      face.material_index = MASTER_NAMES.index(master)
      triangles_before += len(face.verts) - 2
      if is_hidden(face, MASTERS[master][2]):
        hidden.append(face)
        continue
      base = linear_color(mat) * self.face_tints[index]
      grime = mat in GRIME_NAMES
      for loop in face.loops:
        # Dirt and damp climb from the ground, and it costs no geometry at all.
        shade = 0.68 + 0.32 * min(1.0, loop.vert.co.z / 4.5) if grime else 1.0
        color = base * shade
        loop[color_layer] = (color.x, color.y, color.z, 1.0)
    bmesh.ops.delete(bm, geom=hidden, context="FACES")
    bm.to_mesh(mesh)
    bm.free()
    for master in MASTER_NAMES:
      mesh.materials.append(material(master))
    mesh.color_attributes.active_color_index = 0
    mesh.color_attributes.render_color_index = 0
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection().objects.link(obj)
    triangles_after = sum(len(p.vertices) - 2 for p in mesh.polygons)
    print(name, "triangles", triangles_before, "->", triangles_after)
    return obj


def is_hidden(face, one_sided):
  """True for faces no player can see: buried in a solid, or turned away from the play area."""
  center = face.calc_center_median()
  if all(v.co.z < -0.02 for v in face.verts):
    return True
  for low, high in solids:
    if all(low.x < v.co.x < high.x and low.y < v.co.y < high.y and low.z < v.co.z < high.z for v in face.verts):
      return True
  if not one_sided:
    return False
  normal = face.normal
  if normal.length < 0.5:
    return False
  return all(normal.dot(corner - center) <= 0.0 for corner in PLAY_CORNERS)


def add_solid(center, size):
  half = Vector(size) / 2 - Vector((0.03, 0.03, 0.03))
  solids.append((Vector(center) - half, Vector(center) + half))


def box(layer, center, size, mat, rotation=(0, 0, 0)):
  half = Vector(size) / 2
  transform = Matrix.Translation(center) @ Euler(rotation).to_matrix().to_4x4()
  verts = [
    transform @ Vector((sx * half.x, sy * half.y, sz * half.z))
    for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)
  ]
  layer.add(verts, BOX_FACES, mat)


def tube(layer, path, mat, n=6):
  """Lofts rings along path, whose entries are (position, radius)."""
  points = [Vector(entry[0]) for entry in path]
  first = (points[1] - points[0]).normalized()
  axis = min(((1, 0, 0), (0, 1, 0), (0, 0, 1)), key=lambda a: abs(first.dot(Vector(a))))
  u = Vector(axis)
  verts = []
  for i, (_, radius) in enumerate(path):
    tangent = (points[min(i + 1, len(points) - 1)] - points[max(i - 1, 0)]).normalized()
    u = (u - tangent * u.dot(tangent)).normalized()
    v = tangent.cross(u)
    for k in range(n):
      angle = 2 * math.pi * (k + 0.5) / n
      verts.append(points[i] + u * radius * math.cos(angle) + v * radius * math.sin(angle))
  faces = []
  for i in range(len(path) - 1):
    for k in range(n):
      j = (k + 1) % n
      faces.append((i * n + k, i * n + j, (i + 1) * n + j, (i + 1) * n + k))
  faces.append(tuple(reversed(range(n))))
  faces.append(tuple((len(path) - 1) * n + k for k in range(n)))
  layer.add(verts, faces, mat)


def wheel(layer, center, radius, width, mat="tire"):
  x, y, z = center
  tube(layer, [((x - width / 2, y, z), radius), ((x + width / 2, y, z), radius)], mat, n=10)
  tube(layer, [((x - width / 2 - 0.01, y, z), radius * 0.5), ((x + width / 2 + 0.01, y, z), radius * 0.5)], "metal_grey", n=8)


def clump(layer, position, scale, mat, jitter=0.2):
  """Faceted blob, the base of ivy, tree crowns, rubble and clouds."""
  global ICO_VERTS, ICO_FACES
  if not ICO_VERTS:
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
    ICO_VERTS = [v.co.copy() for v in bm.verts]
    ICO_FACES = [tuple(v.index for v in face.verts) for face in bm.faces]
    bm.free()
  origin = Vector(position)
  verts = []
  for co in ICO_VERTS:
    amount = 1.0 + rng.uniform(-jitter, jitter)
    verts.append(origin + Vector((co.x * scale[0] * amount, co.y * scale[1] * amount, co.z * scale[2] * amount)))
  layer.add(verts, ICO_FACES, mat)


def leaf_shade(row, column, phase):
  """Picks a leaf color from slow waves, so tones form patches instead of confetti."""
  wave = math.sin(row * 0.8 + phase) + math.cos(column * 1.3 + phase * 2.0) + rng.uniform(-0.5, 0.5)
  if wave > 0.9:
    return "leaf_light"
  if wave > 0.0:
    return "leaf_mid"
  if wave > -0.8:
    return "leaf_olive"
  return "leaf_dark"


def grid_triangles(layer, grid, close_columns=False):
  """Triangulates rows of points with a random diagonal, for hand-faceted foliage."""
  phase = rng.random() * math.tau
  for row in range(len(grid) - 1):
    columns = len(grid[row]) if close_columns else len(grid[row]) - 1
    for column in range(columns):
      next_column = (column + 1) % len(grid[row])
      a = grid[row][column]
      b = grid[row][next_column]
      c = grid[row + 1][next_column]
      d = grid[row + 1][column]
      first, second = ((a, b, c), (a, c, d)) if rng.random() < 0.5 else ((a, b, d), (b, c, d))
      layer.add(first, [(0, 1, 2)], leaf_shade(row, column, phase), True)
      layer.add(second, [(0, 1, 2)], leaf_shade(row, column + 0.5, phase), True)


def crown_dome(layer, center, radius, height, segments=12):
  """Lumpy foliage dome: one shell that replaces dozens of separate blobs."""
  center = Vector(center)
  profile = ((0.02, 1.0), (0.45, 0.86), (0.8, 0.42), (1.0, 0.0), (0.72, -0.3), (0.02, -0.38))
  offsets = [rng.uniform(0.82, 1.18) for _ in range(segments)]
  grid = []
  for ring, (amount, level) in enumerate(profile):
    row = []
    for k in range(segments):
      angle = math.tau * (k + (ring % 2) * 0.5) / segments
      reach = radius * amount * offsets[k] * rng.uniform(0.94, 1.06)
      row.append(center + Vector((math.cos(angle) * reach, math.sin(angle) * reach, height * level * rng.uniform(0.92, 1.08))))
    grid.append(row)
  grid_triangles(layer, grid, close_columns=True)


def blade_plant(layer, position, size, blades=8, mat="leaf_mid"):
  """Star-shaped ground plant with long folded leaves, like the ones in reference 08."""
  x, y, z = position
  for k in range(blades):
    angle = 2 * math.pi * (k + rng.random() * 0.5) / blades
    out = Vector((math.cos(angle), math.sin(angle), 0))
    side = Vector((-out.y, out.x, 0))
    length = size * rng.uniform(0.75, 1.15)
    rise = rng.uniform(0.35, 0.7)
    base = Vector((x, y, z))
    mid = base + out * length * 0.5 + Vector((0, 0, length * rise))
    tip = base + out * length + Vector((0, 0, length * rise * 0.45))
    width = size * 0.17
    verts = [base, mid + side * width, tip, mid - side * width, mid + Vector((0, 0, -width * 0.5))]
    layer.add(verts, [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)], rng.choice((mat, "leaf_dark", "leaf_olive")), True)


def grass_tuft(layer, position, size):
  x, y, z = position
  for _ in range(3):
    angle = rng.random() * math.tau
    lean = Vector((math.cos(angle), math.sin(angle), 0)) * size * 0.45
    side = Vector((-lean.y, lean.x, 0)).normalized() * size * 0.09
    base = Vector((x, y, z)) + lean * rng.random() * 0.5
    layer.add([base - side, base + side, base + lean + Vector((0, 0, size))], [(0, 1, 2)], rng.choice(("grass", "leaf_olive", "leaf_light")), True)


def flat_blob(layer, center, radii, mat, height, points=9):
  x, y = center
  verts = []
  for k in range(points):
    angle = 2 * math.pi * k / points
    amount = rng.uniform(0.7, 1.15)
    verts.append((x + radii[0] * amount * math.cos(angle), y + radii[1] * amount * math.sin(angle), height))
  layer.add(verts, [tuple(range(points))], mat, True)


def cable(layer, start, end, sag, radius=0.018):
  start = Vector(start)
  end = Vector(end)
  path = []
  for i in range(9):
    amount = i / 8
    point = start.lerp(end, amount) - Vector((0, 0, 4 * sag * amount * (1 - amount)))
    path.append((tuple(point), radius))
  tube(layer, path, "cable", n=3)


def add_collider(center, size):
  colliders.append((center, size))


def clear():
  result = bpy.data.collections.get("avenue")
  if result:
    for obj in list(result.objects):
      bpy.data.objects.remove(obj)
  for mesh in [m for m in bpy.data.meshes if m.users == 0]:
    bpy.data.meshes.remove(mesh)
  colliders.clear()
  facades.clear()
  solids.clear()
  rng.seed(58)
  tint_rng.seed(58)


def build_ground():
  layer = Layer("ground")
  length = 170.0
  box(layer, (0, 0, -0.25), (130, length, 0.5), "asphalt")
  add_collider((0, 0, -0.25), (130, length, 0.5))
  for side in (-1, 1):
    x = side * (STREET_HALF + SIDEWALK_EDGE) / 2
    width = SIDEWALK_EDGE - STREET_HALF
    box(layer, (x, 0, 0.09), (width, length, 0.18), "sidewalk")
    add_collider((x, 0, 0.09), (width, length, 0.18))
    box(layer, (side * (STREET_HALF + 0.12), 0, 0.1), (0.26, length, 0.2), "curb")
    y = -length / 2
    while y < length / 2:
      box(layer, (x, y, 0.182), (width - 0.34, 0.03, 0.01), "crack")
      y += 2.4
    box(layer, (side * 8.0, 0, 0.182), (0.03, length, 0.01), "crack")
    y = AVENUE_START
    while y < AVENUE_END:
      # Cracked or lifted slabs, each slightly tilted.
      if rng.random() < 0.35:
        tilt = (rng.uniform(-0.05, 0.05), rng.uniform(-0.05, 0.05), 0)
        box(layer, (x + rng.uniform(-0.9, 0.9), y, 0.2), (1.5, 2.2, 0.1), rng.choice(("sidewalk", "concrete_grey", "concrete_stain")), tilt)
      y += 2.4

  # Faded center line and a crosswalk.
  y = AVENUE_START
  while y < AVENUE_END:
    if rng.random() > 0.2:
      box(layer, (rng.uniform(-0.03, 0.03), y, 0.012), (0.16, rng.uniform(1.4, 2.6), 0.012), "road_paint")
    y += 4.5
  for side in (-1, 1):
    y = AVENUE_START
    while y < AVENUE_END:
      if rng.random() > 0.45:
        box(layer, (side * 3.1, y, 0.012), (0.12, 1.5, 0.012), "road_white")
      y += 6.0
  for k in range(11):
    if rng.random() > 0.2:
      box(layer, (-5.0 + k, -18.0, 0.012), (0.55, 3.4, 0.012), "road_white")

  # Repairs, cracks, potholes and water.
  for _ in range(16):
    center = (rng.uniform(-5.3, 5.3), rng.uniform(-44, 44))
    box(layer, (center[0], center[1], 0.008), (rng.uniform(1.0, 2.6), rng.uniform(1.4, 4.2), 0.012), "asphalt_patch", (0, 0, rng.uniform(-0.1, 0.1)))
  for _ in range(55):
    x = rng.uniform(-5.6, 5.6)
    y = rng.uniform(-45, 45)
    angle = rng.random() * math.tau
    for _ in range(rng.randint(3, 8)):
      step = rng.uniform(0.35, 0.9)
      angle += rng.uniform(-0.8, 0.8)
      next_x = x + math.cos(angle) * step
      next_y = y + math.sin(angle) * step
      box(layer, ((x + next_x) / 2, (y + next_y) / 2, 0.016), (step + 0.05, rng.uniform(0.04, 0.1), 0.012), "crack", (0, 0, angle))
      if rng.random() < 0.3:
        grass_tuft(layer, (x, y, 0.01), rng.uniform(0.2, 0.5))
      x, y = next_x, next_y
  for _ in range(9):
    center = (rng.uniform(-5.2, 5.2), rng.uniform(-44, 44))
    flat_blob(layer, center, (rng.uniform(0.5, 1.0), rng.uniform(0.5, 1.2)), "asphalt_patch", 0.02)
    flat_blob(layer, center, (rng.uniform(0.3, 0.45), rng.uniform(0.3, 0.5)), "crack", 0.024)
  for center, radii in (
    ((-2.6, -30.0), (2.0, 3.2)), ((2.4, -22.5), (2.8, 2.0)), ((-1.2, -9.0), (3.0, 2.2)), ((3.2, 2.0), (1.8, 3.4)),
    ((-3.4, 11.0), (1.7, 2.6)), ((1.0, 24.0), (3.4, 2.4)), ((-2.2, 33.0), (2.2, 1.8)), ((3.6, 38.0), (1.4, 2.4)),
  ):
    flat_blob(layer, center, radii, "puddle", 0.03, points=12)
    flat_blob(layer, (center[0] + radii[0] * 0.8, center[1] - radii[1] * 0.5), (0.7, 0.9), "puddle", 0.03)
  for y in (-34.0, -6.0, 18.0, 36.0):
    x = rng.choice((-3.2, 3.2))
    tube(layer, [((x, y, 0.0), 0.42), ((x, y, 0.045), 0.42)], "iron", n=12)
    for k in range(4):
      box(layer, (x, y - 0.27 + k * 0.18, 0.05), (0.56, 0.04, 0.012), "rust")
  for side in (-1, 1):
    y = AVENUE_START + 4
    while y < AVENUE_END:
      box(layer, (side * (STREET_HALF - 0.1), y, 0.03), (0.2, 0.8, 0.04), "iron")
      y += rng.uniform(11, 17)
  layer.build()


def window(layer, x, y, z, width, height, street, along_x=False, grille=False, frame="window_frame"):
  """One window on a wall that faces the street direction, with frame, sill and glass."""

  def place(depth, along, up, size_depth, size_along, size_up, mat):
    if along_x:
      box(layer, (x + along, y + street * depth, z + up), (size_along, size_depth, size_up), mat)
    else:
      box(layer, (x + street * depth, y + along, z + up), (size_depth, size_along, size_up), mat)

  place(0.03, 0, 0, 0.1, width, height, "window_dark")
  place(0.08, 0, height / 2 + 0.05, 0.12, width + 0.2, 0.12, frame)
  place(0.08, 0, -height / 2 - 0.05, 0.12, width + 0.2, 0.12, frame)
  place(0.08, -width / 2 - 0.05, 0, 0.12, 0.12, height, frame)
  place(0.08, width / 2 + 0.05, 0, 0.12, 0.12, height, frame)
  place(0.08, 0, 0, 0.08, 0.07, height, frame)
  place(0.08, 0, height * 0.12, 0.08, width, 0.06, frame)
  place(0.15, 0, -height / 2 - 0.15, 0.3, width + 0.4, 0.09, "stone_cream")
  if rng.random() < 0.25:
    # Broken pane, the frame stays and a shard of light shows through.
    place(0.1, -width * 0.24, height * 0.3, 0.04, width * 0.3, height * 0.3, "glass")
  if grille:
    # Burglar bars, as on almost every Venezuelan ground and first floor.
    bars = 6
    for k in range(bars):
      place(0.2, -width / 2 + width * k / (bars - 1), 0, 0.03, 0.03, height + 0.1, "iron")
    for up in (-height * 0.48, 0, height * 0.48):
      place(0.2, 0, up, 0.03, width + 0.1, 0.03, "iron")


def add_air_conditioner(layer, x, y, z, street):
  box(layer, (x + street * 0.3, y, z), (0.55, 0.75, 0.45), "metal_grey")
  for k in range(4):
    box(layer, (x + street * 0.58, y, z - 0.15 + k * 0.1), (0.02, 0.62, 0.03), "iron")
  box(layer, (x + street * 0.3, y + 0.46, z - 0.6), (0.03, 0.03, 0.8), "rust")


def stains(layer, wall_x, street, y0, y1, height, count):
  for _ in range(count):
    y = rng.uniform(y0 + 1, y1 - 1)
    z = rng.uniform(0.8, height - 0.5)
    box(layer, (wall_x + street * 0.02, y, z), (0.05, rng.uniform(0.5, 2.0), rng.uniform(0.8, 3.0)), rng.choice(("concrete_stain", "brick_dark")))


def shop_front(layer, wall_x, street, y, width, height=3.0):
  """Ground-floor shop with a pulled-down steel shutter, a sign and a torn awning."""
  box(layer, (wall_x + street * 0.04, y, height / 2 + 0.18), (0.1, width, height - 0.2), "window_dark")
  ribs = 12
  closed = rng.uniform(0.45, 1.0)
  for k in range(ribs):
    if k / ribs > closed:
      continue
    z = height - 0.25 - k * (height - 0.3) / ribs
    box(layer, (wall_x + street * 0.11, y, z), (0.05, width - 0.1, 0.2), rng.choice(("shutter", "shutter", "rust")))
  for offset in (-width / 2, width / 2):
    box(layer, (wall_x + street * 0.12, y + offset, height / 2 + 0.1), (0.1, 0.1, height), "iron")
  sign = rng.choice(("sign_blue", "sign_yellow", "sign_red", "sign_white"))
  tilt = rng.uniform(-0.05, 0.05)
  box(layer, (wall_x + street * 0.2, y, height + 0.55), (0.12, width * 0.92, 0.8), sign, (tilt, 0, 0))
  box(layer, (wall_x + street * 0.27, y - width * 0.2, height + 0.55), (0.02, width * 0.3, 0.32), "sign_white")
  box(layer, (wall_x + street * 0.27, y + width * 0.22, height + 0.55), (0.02, width * 0.28, 0.16), "iron")
  if rng.random() < 0.65:
    color = rng.choice(("sign_red", "sign_blue", "sign_yellow"))
    stripes = int(width / 0.55)
    for k in range(stripes):
      if rng.random() < 0.18:
        continue
      along = -width / 2 + (k + 0.5) * width / stripes
      box(
        layer,
        (wall_x + street * 0.75, y + along, height + 0.02),
        (1.5, width / stripes * 0.92, 0.04),
        color if k % 2 else "sign_white",
        (0, street * 0.45, 0),
      )


def side_walls(layer, center_x, y0, y1, depth, height, story, trim):
  """Fills the end walls that show above shorter neighbours."""
  for wall_y, outward in ((y0 + 0.1, -1), (y1 - 0.1, 1)):
    rows = int(height / story)
    for row in range(1, rows):
      z = row * story + 1.4
      box(layer, (center_x, wall_y + outward * 0.03, z + 1.3), (depth - 0.4, 0.08, 0.18), trim)
      for k in range(4):
        x = center_x - depth / 2 + 1.8 + k * (depth - 3.6) / 3
        box(layer, (x, wall_y + outward * 0.04, z), (1.3, 0.08, 1.7), rng.choice(("window_dark", "window_dark", "brick_dark")))
        box(layer, (x, wall_y + outward * 0.08, z - 0.95), (1.6, 0.16, 0.12), trim)


def concrete_block(side, y0, y1, floors):
  """Reference 08: stacked slabs with deep balconies, pillars and dark window bands."""
  layer = Layer(f"block_{'r' if side > 0 else 'l'}_{int(y0 + 50)}")
  street = -side
  wall_x = side * SIDEWALK_EDGE
  depth = 12.0
  mid = (y0 + y1) / 2
  length = y1 - y0 - 0.3
  story = 3.3
  center_x = wall_x + side * depth / 2
  base = rng.choice(("concrete_warm", "brick_orange", "brick_orange"))
  height = floors * story + 0.6
  box(layer, (center_x, mid, height / 2), (depth, length, height), "concrete_stain")
  add_collider((center_x, mid, height / 2), (depth + 0.2, length + 0.5, height))
  add_solid((center_x, mid, height / 2), (depth, length, height))
  side_walls(layer, center_x, y0, y1, depth, height, story, base)
  spans = max(3, int(length / 3.2))
  span = length / spans

  shop_y = y0 + 0.15 + span / 2
  for k in range(spans):
    shop_front(layer, wall_x, street, shop_y + k * span, span - 0.35)
  for k in range(spans + 1):
    box(layer, (wall_x + street * 0.18, y0 + 0.15 + k * span, 2.0), (0.4, 0.4, 3.9), base)

  for floor in range(1, floors):
    z = floor * story + 0.3
    collapsed = set(rng.sample(range(spans), rng.randint(0, 1)))
    box(layer, (wall_x + street * 0.02, mid, z + 1.65), (0.1, length, 2.7), "window_dark")
    for k in range(spans):
      y = y0 + 0.15 + (k + 0.5) * span
      if rng.random() < 0.22:
        box(layer, (wall_x + street * 0.05, y, z + 1.65), (0.08, span - 0.3, 2.7), rng.choice(("shutter", "wood_old", "brick_dark")))
      if k in collapsed:
        # Balcony fell off: stub of slab and hanging reinforcing bars.
        box(layer, (wall_x + street * 0.2, y, z + 0.12), (0.5, span, 0.24), base)
        for _ in range(6):
          bar_y = y + rng.uniform(-span / 2, span / 2)
          bar_z = z + 0.1
          tube(layer, [
            ((wall_x + street * 0.4, bar_y, bar_z), 0.015),
            ((wall_x + street * 0.8, bar_y, bar_z - 0.25), 0.015),
            ((wall_x + street * 0.95, bar_y + 0.05, bar_z - 0.8), 0.015),
          ], "rust", n=3)
        continue
      tilt = rng.uniform(-0.012, 0.012)
      box(layer, (wall_x + street * 0.65, y, z + 0.12), (1.5, span + 0.04, 0.3), base, (tilt, 0, 0))
      box(layer, (wall_x + street * 1.42, y, z + 0.03), (0.1, span + 0.04, 0.16), "concrete_stain")
      # Parapet with slats, so the balcony reads as a deep ledge from the street.
      box(layer, (wall_x + street * 1.34, y, z + 0.62), (0.16, span + 0.04, 0.7), base)
      box(layer, (wall_x + street * 1.34, y, z + 1.06), (0.2, span + 0.06, 0.14), "concrete_grey")
      box(layer, (wall_x + street * 1.43, y, z + 0.62), (0.03, span - 0.2, 0.14), "concrete_stain")
      for rail in range(2):
        box(layer, (wall_x + street * 0.65, y - span / 2 + rail * span, z + 0.75), (1.4, 0.14, 1.0), base)
      if rng.random() < 0.55:
        add_air_conditioner(layer, wall_x + street * 0.4, y + rng.uniform(-0.7, 0.7), z + 0.55, street)
      if rng.random() < 0.3:
        # Abandoned clothesline.
        line_z = z + 2.3
        cable(layer, (wall_x + street * 1.3, y - span * 0.42, line_z), (wall_x + street * 1.3, y + span * 0.42, line_z), 0.12, 0.008)
        for _ in range(rng.randint(2, 4)):
          box(
            layer,
            (wall_x + street * 1.3, y + rng.uniform(-span * 0.3, span * 0.3), line_z - 0.5),
            (0.02, 0.5, 0.75),
            rng.choice(("sign_white", "sign_red", "sign_blue", "wood_old")),
            (rng.uniform(-0.08, 0.08), 0, 0),
          )
      if rng.random() < 0.25:
        box(layer, (wall_x + street * 1.1, y, z + 0.5), (0.5, 0.7, 0.5), rng.choice(("rust", "wood", "metal_grey")))
    for k in range(spans + 1):
      box(layer, (wall_x + street * 0.2, y0 + 0.15 + k * span, z + 1.65), (0.4, 0.42, 2.9), base)
    box(layer, (wall_x + street * 0.2, mid, z + 3.05), (0.42, length, 0.22), base)
  # Side wall details and roof clutter.
  roof = floors * story + 0.6
  box(layer, (center_x, mid, roof + 0.4), (depth + 0.3, length + 0.3, 0.8), base)
  box(layer, (wall_x + street * -0.1, mid, roof + 0.85), (0.4, length + 0.4, 0.14), "concrete_grey")
  box(layer, (center_x + side * 1, mid + 2, roof + 2.1), (3.0, 3.0, 2.6), "concrete_stain")
  box(layer, (center_x + side * 1, mid + 2, roof + 3.5), (3.3, 3.3, 0.2), "concrete_grey")
  for dx in (-1.1, 1.1):
    for dy in (-1.1, 1.1):
      box(layer, (center_x + side * 1 + dx, mid + 2 + dy, roof + 0.8), (0.14, 0.14, 0.8), "rust")
  tube(layer, [((center_x - side * 2, mid - 3, roof + 0.8), 0.04), ((center_x - side * 2, mid - 3, roof + 4.6), 0.02)], "iron", n=4)
  for k in range(4):
    z = roof + 1.8 + k * 0.7
    box(layer, (center_x - side * 2, mid - 3, z), (0.03, 1.5 - k * 0.3, 0.03), "iron")
  dish_x, dish_y = center_x + side * 3, mid - 2
  tube(layer, [((dish_x, dish_y, roof + 0.8), 0.04), ((dish_x, dish_y, roof + 1.6), 0.04)], "metal_grey", n=4)
  tube(layer, [
    ((dish_x + street * 0.25, dish_y, roof + 1.6), 0.02),
    ((dish_x + street * 0.05, dish_y, roof + 1.7), 0.45),
    ((dish_x - street * 0.05, dish_y, roof + 1.75), 0.45),
  ], "metal_grey", n=8)
  layer.build()
  facades.append((wall_x, street, y0, y1, roof, 1.52, 3.4))


def brick_row_house(side, y0, y1, floors):
  """Reference 07: brick facades with stone trim, cornices and front stoops."""
  layer = Layer(f"brick_{'r' if side > 0 else 'l'}_{int(y0 + 50)}")
  street = -side
  wall_x = side * SIDEWALK_EDGE
  depth = 12.0
  mid = (y0 + y1) / 2
  length = y1 - y0 - 0.3
  story = 3.4
  center_x = wall_x + side * depth / 2
  brick = rng.choice(("brick_red", "brick_red", "brick_dark"))
  height = floors * story + 1.2
  box(layer, (center_x, mid, height / 2), (depth, length, height), brick)
  add_collider((center_x, mid, height / 2), (depth + 0.2, length + 0.5, height))
  add_solid((center_x, mid, height / 2), (depth, length, height))
  side_walls(layer, center_x, y0, y1, depth, height, story, "stone_cream")
  box(layer, (wall_x + street * 0.06, mid, 0.85), (0.14, length, 1.7), "stone_cream")
  box(layer, (wall_x + street * 0.1, mid, 1.75), (0.22, length + 0.04, 0.18), "stone_cream")

  columns = max(3, int(length / 2.7))
  spacing = length / columns
  door_column = rng.randrange(columns)
  for floor in range(floors):
    z = 2.9 + floor * story
    for k in range(columns):
      y = y0 + 0.15 + (k + 0.5) * spacing
      if floor == 0 and k == door_column:
        continue
      window(layer, wall_x, y, z, 1.25, 2.1, street, grille=floor == 0 or rng.random() < 0.2, frame="stone_cream" if rng.random() < 0.5 else "window_frame")
      box(layer, (wall_x + street * 0.12, y, z + 1.32), (0.28, 1.75, 0.26), "stone_cream")
      if floor > 0 and rng.random() < 0.18:
        add_air_conditioner(layer, wall_x, y + rng.uniform(-0.2, 0.2), z - 0.55, street)
    box(layer, (wall_x + street * 0.05, mid, z + 1.72), (0.12, length, 0.12), "stone_cream")

  # Brick courses, lost plaster and old repairs.
  for _ in range(int(length * floors * 0.9)):
    y = rng.uniform(y0 + 0.5, y1 - 0.5)
    z = rng.uniform(2.0, height - 1.5)
    box(layer, (wall_x + street * 0.03, y, z), (0.06, rng.uniform(0.25, 0.6), 0.09), rng.choice(("brick_dark", "brick_orange", "concrete_stain")))

  # Stoop with steps, walls, railings and a door.
  door_y = y0 + 0.15 + (door_column + 0.5) * spacing
  steps = 7
  for k in range(steps):
    run = 0.32
    box(
      layer,
      (wall_x + street * (2.35 - k * run), door_y, 0.18 + (k + 0.5) * 0.24),
      (run + 0.02, 1.9, (k + 1) * 0.24 + 0.05),
      "stone_cream",
    )
  box(layer, (wall_x + street * 0.3, door_y, 1.86), (0.62, 2.1, 0.22), "stone_cream")
  add_collider((wall_x + street * 1.2, door_y, 0.9), (2.4, 2.0, 1.8))
  for offset in (-1.05, 1.05):
    box(layer, (wall_x + street * 1.3, door_y + offset, 0.7), (2.5, 0.2, 1.05), "stone_cream")
    tube(layer, [
      ((wall_x + street * 2.45, door_y + offset, 1.42), 0.03),
      ((wall_x + street * 0.2, door_y + offset, 2.75), 0.03),
    ], "iron", n=4)
    for k in range(6):
      amount = k / 5
      post_x = wall_x + street * (2.4 - amount * 2.2)
      top = 1.45 + amount * 1.28
      box(layer, (post_x, door_y + offset, top - 0.45), (0.03, 0.03, 0.9), "iron")
    tube(layer, [((wall_x + street * 2.5, door_y + offset, 1.2), 0.09), ((wall_x + street * 2.5, door_y + offset, 1.55), 0.13), ((wall_x + street * 2.5, door_y + offset, 1.7), 0.05)], "stone_cream", n=6)
  box(layer, (wall_x + street * 0.06, door_y, 3.2), (0.1, 1.5, 2.65), "wood")
  for up in (2.55, 3.65):
    box(layer, (wall_x + street * 0.12, door_y, up), (0.04, 1.1, 0.8), "wood_old")
  box(layer, (wall_x + street * 0.15, door_y + 0.55, 3.2), (0.08, 0.07, 0.07), "metal_grey")
  box(layer, (wall_x + street * 0.15, door_y, 4.62), (0.3, 1.9, 0.2), "stone_cream")
  for offset in (-0.82, 0.82):
    box(layer, (wall_x + street * 0.14, door_y + offset, 3.25), (0.24, 0.22, 2.9), "stone_cream")

  # Heavy roof cornice with brackets.
  top = floors * story + 1.1
  box(layer, (wall_x + street * 0.28, mid, top), (0.62, length + 0.1, 0.34), "stone_cream")
  box(layer, (wall_x + street * 0.42, mid, top + 0.28), (0.9, length + 0.2, 0.24), "window_frame")
  bracket = 0
  while bracket < length:
    box(layer, (wall_x + street * 0.3, y0 + 0.3 + bracket, top - 0.3), (0.45, 0.2, 0.42), "stone_cream")
    bracket += 0.9
  box(layer, (center_x, mid, top + 0.5), (depth, length, 0.5), "concrete_grey")
  for k in range(2):
    chimney_y = mid - 3 + k * 6
    box(layer, (center_x + side * 2, chimney_y, top + 1.5), (1.0, 1.4, 2.2), brick)
    box(layer, (center_x + side * 2, chimney_y, top + 2.7), (1.2, 1.6, 0.2), "stone_cream")
  layer.build()
  facades.append((wall_x, street, y0, y1, top, 0.4, 0.4))


def build_buildings():
  plan = {
    -1: [(concrete_block, 14.0, 7), (brick_row_house, 16.0, 5), (concrete_block, 15.0, 6), (brick_row_house, 13.0, 4), (concrete_block, 15.0, 8), (brick_row_house, 13.0, 5), (concrete_block, 14.0, 6)],
    1: [(brick_row_house, 15.0, 5), (concrete_block, 15.0, 8), (brick_row_house, 12.0, 4), (concrete_block, 16.0, 6), (brick_row_house, 14.0, 6), (concrete_block, 14.0, 7), (brick_row_house, 14.0, 4)],
  }
  for side, row in plan.items():
    y = -50.0
    for builder, length, floors in row:
      builder(side, y, y + length, floors)
      y += length


def build_landmarks():
  layer = Layer("landmarks")
  # Stepped tower closing the avenue, reference 08's spire adapted to a Caracas landmark.
  tower_y = 72.0
  levels = 7
  for k in range(levels):
    size = 22.0 - k * 2.2
    base = k * 9.0
    box(layer, (0, tower_y, base + 4.5), (size, size, 9.0), "concrete_stain")
    box(layer, (0, tower_y, base + 0.4), (size + 1.8, size + 1.8, 0.8), "concrete_warm")
    box(layer, (0, tower_y, base + 7.8), (size + 0.8, size + 0.8, 0.5), "concrete_warm")
    columns = max(4, int(size / 1.9))
    for row in range(2):
      z = base + 2.6 + row * 3.2
      box(layer, (0, tower_y - size / 2 - 0.05, z), (size - 1.0, 0.1, 1.6), "window_dark")
      for c in range(columns + 1):
        box(layer, (-size / 2 + 0.5 + c * (size - 1) / columns, tower_y - size / 2 - 0.12, z), (0.34, 0.2, 1.8), "concrete_warm")
      if rng.random() < 0.6:
        for c in range(rng.randint(1, 3)):
          box(layer, (rng.uniform(-size / 2, size / 2), tower_y - size / 2 - 0.1, z), (1.4, 0.08, 1.5), "brick_dark")
      for sign in (-1, 1):
        box(layer, (sign * (size / 2 + 0.05), tower_y, z), (0.1, size - 1.0, 1.6), "window_dark")
        for c in range(columns + 1):
          box(layer, (sign * (size / 2 + 0.12), tower_y - size / 2 + 0.5 + c * (size - 1) / columns, z), (0.2, 0.34, 1.8), "concrete_warm")
  spire_base = levels * 9.0
  tube(layer, [((0, tower_y, spire_base), 5.6), ((0, tower_y, spire_base + 6), 4.0), ((0, tower_y, spire_base + 20), 0.2)], "concrete_warm", n=4)
  tube(layer, [((0, tower_y, spire_base + 19), 0.15), ((0, tower_y, spire_base + 28), 0.03)], "iron", n=4)
  for k in range(3):
    box(layer, (0, tower_y, spire_base + 21 + k * 2), (2.6 - k * 0.7, 0.05, 0.05), "iron")

  # Collapsed apartment block closing the back of the avenue.
  box(layer, (0, -60, 11), (48, 12, 22), "concrete_stain")
  for row in range(6):
    z = 2.0 + row * 3.4
    box(layer, (0, -53.9, z + 1.2), (46, 0.2, 1.8), "window_dark")
    box(layer, (0, -53.4, z), (48, 1.2, 0.3), "concrete_warm")
    for k in range(17):
      box(layer, (-24 + k * 3, -53.7, z + 1.4), (0.4, 0.5, 2.8), "concrete_warm")
  add_collider((0, -60, 11), (48, 12, 22))
  add_solid((0, -60, 11), (48, 12, 22))

  # Rubble barriers at both ends of the playable street.
  for y, spread in ((46.5, 2.4), (-47.0, 2.0)):
    for _ in range(46):
      x = rng.uniform(-9.5, 9.5)
      size = rng.uniform(0.7, 2.2)
      clump(layer, (x, y + rng.uniform(-spread, spread), size * 0.5), (size * 1.2, size, size * 0.8), rng.choice(("concrete_grey", "concrete_stain", "brick_red", "concrete_warm")), 0.3)
    for _ in range(14):
      box(
        layer,
        (rng.uniform(-9, 9), y + rng.uniform(-2, 2), rng.uniform(0.8, 2.6)),
        (rng.uniform(2, 5), rng.uniform(1, 3), 0.28),
        "concrete_warm",
        (rng.uniform(-0.6, 0.6), rng.uniform(-0.6, 0.6), rng.uniform(-0.8, 0.8)),
      )
    for _ in range(18):
      bar_x = rng.uniform(-9, 9)
      bar_y = y + rng.uniform(-2, 2)
      tube(layer, [((bar_x, bar_y, 1.2), 0.02), ((bar_x + rng.uniform(-1, 1), bar_y + rng.uniform(-1, 1), rng.uniform(2.4, 4)), 0.02)], "rust", n=3)
    add_collider((0, y, 2.5), (19.5, 6.0, 5.0))
  layer.build()


def bus(layer, position, rotation):
  """Abandoned city bus, the Caracas stand-in for reference 08's tram."""
  layer.place(position, rotation)
  half_width = 1.25
  half_length = 5.0
  box(layer, (0, 0, 1.0), (2.5, 10.0, 1.1), "bus_red")
  box(layer, (0, 0, 0.42), (2.46, 9.9, 0.12), "iron")
  box(layer, (0, 0, 1.6), (2.54, 10.04, 0.12), "bus_yellow")
  box(layer, (0, 0, 0.9), (2.53, 10.03, 0.08), "bus_yellow")
  box(layer, (0, 0, 1.0), (2.2, 9.6, 1.0), "iron")
  for sign in (-1, 1):
    k = 0
    while k <= 12:
      y = -half_length + 0.1 + k * 0.82
      box(layer, (sign * half_width, y, 2.15), (0.1, 0.14, 1.0), "bus_yellow")
      k += 1
    box(layer, (sign * half_width, 0, 1.72), (0.08, 10, 0.04), "iron")
    if sign < 0:
      for k in range(4):
        box(layer, (sign * (half_width + 0.02), -4.2 + k * 0.5, 1.1), (0.04, 0.34, 0.2), "rust")
    for y in (-3.2, 3.1):
      wheel(layer, (sign * 1.15, y, 0.52), 0.52, 0.34)
      tube(layer, [((sign * 1.27, y + dy, 0.55 + abs(dy) * 0.55), 0.03) for dy in ()] or [((sign * 1.27, y - 0.7, 0.55), 0.03), ((sign * 1.27, y + 0.7, 0.55), 0.03)], "iron", n=3)
  for k in range(10):
    y = -4.1 + k * 0.9
    for sign in (-1, 1):
      box(layer, (sign * 0.75, y, 1.65), (0.82, 0.42, 0.14), "sign_blue")
      box(layer, (sign * 0.75, y + 0.22, 2.0), (0.82, 0.1, 0.6), "sign_blue")
  box(layer, (0, 0, 2.72), (2.5, 10.0, 0.14), "bus_red")
  box(layer, (0, 0, 2.86), (2.2, 9.6, 0.14), "bus_red")
  box(layer, (0, 0, 2.99), (1.6, 8.8, 0.12), "metal_grey")
  for y in (-5.0, 5.0):
    box(layer, (0, y, 1.0), (2.5, 0.12, 1.1), "bus_red")
    box(layer, (0, y, 2.15), (2.5, 0.08, 1.0), "glass")
    box(layer, (0, y, 2.55), (2.5, 0.14, 0.3), "sign_yellow")
    box(layer, (0, y * 1.02, 0.5), (2.6, 0.2, 0.26), "metal_grey")
    for sign in (-1, 1):
      box(layer, (sign * 0.9, y * 1.012, 0.92), (0.34, 0.06, 0.2), "sign_white")
      box(layer, (sign * 1.32, y, 2.2), (0.08, 0.18, 1.1), "bus_yellow")
  box(layer, (0, 5.03, 2.0), (0.06, 0.04, 1.0), "iron")
  box(layer, (-1.28, -4.6, 2.5), (0.3, 0.1, 0.36), "iron")
  box(layer, (1.28, -4.6, 2.5), (0.3, 0.1, 0.36), "iron")
  layer.reset()


def car(layer, position, rotation, paint):
  """Boxy 1980s sedan, the classic Caracas carrito por puesto."""
  layer.place(position, rotation)
  box(layer, (0, 0, 0.62), (1.8, 4.7, 0.5), paint)
  box(layer, (0, 2.0, 0.84), (1.74, 0.9, 0.06), paint)
  box(layer, (0, -2.1, 0.84), (1.74, 0.6, 0.06), paint)
  box(layer, (0, 0, 1.36), (1.48, 2.0, 0.08), paint)
  box(layer, (0, -0.1, 1.08), (1.4, 2.1, 0.54), "glass")
  for sign in (-1, 1):
    for y in (-1.02, 0.0, 0.94):
      box(layer, (sign * 0.72, y - 0.1, 1.08), (0.07, 0.12, 0.56), paint)
    box(layer, (sign * 0.9, 0, 0.72), (0.03, 4.6, 0.05), "metal_grey")
    for y in (-1.45, 1.45):
      wheel(layer, (sign * 0.82, y, 0.34), 0.34, 0.22)
    box(layer, (sign * 0.6, 2.36, 0.68), (0.34, 0.03, 0.18), "sign_white")
    box(layer, (sign * 0.6, -2.36, 0.68), (0.34, 0.03, 0.18), "sign_red")
  for y in (-2.38, 2.38):
    box(layer, (0, y, 0.42), (1.84, 0.1, 0.14), "metal_grey")
  box(layer, (0, 2.37, 0.68), (0.8, 0.03, 0.2), "iron")
  layer.reset()


def traffic_barrier(layer, position, angle):
  layer.place(position, (0, 0, angle))
  for sign in (-1, 1):
    box(layer, (sign * 0.95, 0, 0.6), (0.08, 0.08, 1.2), "wood_old")
    box(layer, (sign * 0.95, 0, 0.06), (0.1, 0.8, 0.1), "wood_old")
  for z in (0.55, 1.0):
    stripes = 6
    for k in range(stripes):
      box(layer, (-0.95 + (k + 0.5) * 1.9 / stripes, 0, z), (1.9 / stripes, 0.04, 0.24), "hazard_yellow" if k % 2 else "hazard_black")
  layer.reset()


def concrete_barrier(layer, position, angle):
  layer.place(position, (0, 0, angle))
  box(layer, (0, 0, 0.14), (2.4, 0.6, 0.28), "concrete_grey")
  box(layer, (0, 0, 0.55), (2.4, 0.3, 0.6), "concrete_grey")
  stripes = 7
  for k in range(stripes):
    box(layer, (-1.2 + (k + 0.5) * 2.4 / stripes, -0.16, 0.6), (2.4 / stripes, 0.02, 0.3), "hazard_yellow" if k % 2 else "hazard_black", (0, 0.5, 0))
  layer.reset()


def hydrant(layer, x, y, z=0.18):
  tube(layer, [((x, y, z), 0.15), ((x, y, z + 0.1), 0.13), ((x, y, z + 0.55), 0.12), ((x, y, z + 0.62), 0.15), ((x, y, z + 0.72), 0.1), ((x, y, z + 0.82), 0.03)], "hydrant", n=8)
  tube(layer, [((x - 0.22, y, z + 0.42), 0.06), ((x + 0.22, y, z + 0.42), 0.06)], "hydrant", n=6)
  tube(layer, [((x, y - 0.2, z + 0.42), 0.07), ((x, y - 0.25, z + 0.42), 0.09)], "metal_grey", n=6)


def bus_stop(layer, x, y, street):
  for offset in (-2.0, 2.0):
    box(layer, (x, y + offset, 1.4), (0.1, 0.1, 2.5), "metal_grey")
    box(layer, (x + street * -0.7, y + offset, 1.4), (0.1, 0.1, 2.5), "metal_grey")
  box(layer, (x + street * -0.35, y, 2.72), (1.8, 4.6, 0.1), "metal_grey", (0, street * 0.06, 0))
  box(layer, (x + street * -0.72, y, 1.65), (0.05, 3.9, 1.5), "glass")
  box(layer, (x + street * -0.72, y, 2.45), (0.1, 4.0, 0.4), "sign_blue")
  box(layer, (x + street * -0.4, y, 0.7), (0.4, 3.0, 0.08), "wood")
  for offset in (-1.2, 1.2):
    box(layer, (x + street * -0.4, y + offset, 0.44), (0.1, 0.1, 0.5), "iron")


def kiosk(layer, x, y):
  box(layer, (x, y, 1.45), (1.9, 2.2, 2.5), "sign_blue")
  box(layer, (x, y, 2.85), (2.5, 2.9, 0.14), "shutter", (0.06, 0, 0))
  box(layer, (x, y - 1.13, 1.7), (1.5, 0.06, 1.1), "shutter")
  box(layer, (x, y - 1.2, 1.05), (1.6, 0.3, 0.08), "sign_white")
  for k in range(4):
    box(layer, (x, y - 1.15, 1.4 + k * 0.25), (1.5, 0.02, 0.08), "rust")
  box(layer, (x, y + 1.12, 2.45), (1.8, 0.06, 0.5), "sign_yellow")


def phone_booth(layer, x, y):
  box(layer, (x, y, 1.3), (0.7, 0.7, 2.1), "sign_blue")
  box(layer, (x, y - 0.36, 1.45), (0.56, 0.04, 1.4), "window_dark")
  box(layer, (x, y - 0.4, 1.5), (0.26, 0.05, 0.42), "metal_grey")
  box(layer, (x, y, 2.42), (0.8, 0.8, 0.14), "sign_yellow")


def deer(layer, position, angle, grazing):
  layer.place(position, (0, 0, angle))
  tube(layer, [((0, -0.5, 0.82), 0.1), ((0, -0.3, 0.87), 0.2), ((0, 0.25, 0.9), 0.21), ((0, 0.5, 0.92), 0.14)], "deer", n=6)
  head_z = 0.28 if grazing else 1.45
  head_y = 0.86 if grazing else 0.74
  tube(layer, [((0, 0.45, 0.98), 0.1), ((0, head_y - 0.08, (head_z + 0.98) / 2), 0.065), ((0, head_y, head_z), 0.07)], "deer", n=5)
  tube(layer, [((0, head_y - 0.02, head_z + 0.02), 0.075), ((0, head_y + 0.18, head_z - 0.08), 0.03)], "deer", n=5)
  for sign in (-1, 1):
    for y in (-0.42, 0.42):
      tube(layer, [((sign * 0.1, y, 0.82), 0.05), ((sign * 0.11, y, 0.42), 0.025), ((sign * 0.11, y, 0.0), 0.018)], "deer", n=4)
    box(layer, (sign * 0.09, head_y - 0.08, head_z + 0.06), (0.14, 0.03, 0.06), "deer", (0, sign * 0.5, 0))
    tube(layer, [
      ((sign * 0.03, head_y - 0.06, head_z + 0.06), 0.012), ((sign * 0.14, head_y - 0.12, head_z + 0.3), 0.01),
      ((sign * 0.2, head_y - 0.04, head_z + 0.5), 0.006),
    ], "bark", n=3)
    tube(layer, [((sign * 0.1, head_y - 0.1, head_z + 0.2), 0.008), ((sign * 0.02, head_y + 0.04, head_z + 0.36), 0.005)], "bark", n=3)
  layer.reset()


def vulture(layer, position, angle):
  """Zamuros perched on the poles, the local answer to reference 08's fauna."""
  layer.place(position, (0, 0, angle))
  clump(layer, (0, 0, 0.2), (0.11, 0.2, 0.15), "bird", 0.1)
  tube(layer, [((0, 0.15, 0.3), 0.05), ((0, 0.24, 0.42), 0.035), ((0, 0.3, 0.42), 0.02)], "bird", n=4)
  layer.add([(-0.1, 0.05, 0.28), (0.1, 0.05, 0.28), (0, -0.45, 0.05)], [(0, 1, 2)], "bird")
  layer.reset()


def overgrow(layer, center, spread, clumps, cards=40):
  """Foliage piled on a prop, as vines reclaim it."""
  x, y, z = center
  for _ in range(max(2, clumps // 4)):
    radius = rng.uniform(0.6, 1.1)
    crown_dome(
      layer,
      (x + rng.gauss(0, spread[0]), y + rng.gauss(0, spread[1]), z + rng.gauss(0, spread[2])),
      radius,
      radius * 0.5,
      segments=8,
    )


def build_vehicles():
  layer = Layer("vehicles")
  bus(layer, (2.2, -4.0, 0.0), (0, 0.02, 0.32))
  add_collider((2.2, -4.0, 1.5), (3.6, 10.6, 3.0))
  overgrow(layer, (2.0, -5.0, 3.1), (0.7, 2.6, 0.2), 26, 110)
  overgrow(layer, (3.1, -1.0, 1.0), (0.3, 1.6, 0.8), 14, 60)
  car(layer, (-3.6, -24.0, 0.0), (0, 0, 0.14), "car_yellow")
  add_collider((-3.6, -24.0, 0.75), (2.0, 4.8, 1.5))
  overgrow(layer, (-3.6, -23.0, 1.2), (0.5, 1.0, 0.2), 8, 30)
  # Car pitched up against the curb, as the red one on the steps in reference 08.
  car(layer, (5.4, 15.0, 0.95), (0.42, -0.1, -0.16), "car_red")
  add_collider((5.4, 15.0, 0.95), (2.1, 4.8, 2.0))
  overgrow(layer, (5.0, 13.8, 0.8), (0.4, 0.9, 0.3), 8, 40)
  car(layer, (-4.2, 21.0, 0.0), (0, 0.06, -0.08), "car_blue")
  add_collider((-4.2, 21.0, 0.75), (2.0, 4.8, 1.5))
  car(layer, (4.0, 33.0, 0.0), (0, 0, 2.9), "car_yellow")
  add_collider((4.0, 33.0, 0.75), (2.2, 5.0, 1.5))
  overgrow(layer, (4.0, 33.0, 1.3), (0.6, 1.2, 0.3), 10, 40)
  layer.build()


def build_street_furniture():
  layer = Layer("street_furniture", chunk=24.0)
  # Utility poles carrying sagging cables down both sidewalks.
  poles = {-1: [], 1: []}
  heights = {}
  for side in (-1, 1):
    y = AVENUE_START + 3
    while y < AVENUE_END:
      lean = (rng.uniform(-0.03, 0.03), rng.uniform(-0.03, 0.03), 0)
      x = side * 8.8
      height = 9.0
      layer.place((x, y, 0.18), lean)
      tube(layer, [((0, 0, 0), 0.17), ((0, 0, 6), 0.12), ((0, 0, height), 0.09)], "pole_concrete", n=6)
      for z, width in ((height - 0.4, 2.5), (height - 1.3, 1.8)):
        box(layer, (0, 0, z), (width, 0.12, 0.12), "wood_old")
        for offset in (-width / 2 + 0.1, 0, width / 2 - 0.1):
          tube(layer, [((offset, 0, z + 0.06), 0.045), ((offset, 0, z + 0.2), 0.03)], "glass", n=5)
      if rng.random() < 0.5:
        tube(layer, [((0.32, 0, height - 3.4), 0.26), ((0.32, 0, height - 2.3), 0.26)], "metal_grey", n=8)
        box(layer, (0.1, 0, height - 2.9), (0.2, 0.1, 0.6), "iron")
      box(layer, (0, -0.15, 2.6), (0.28, 0.02, 0.4), rng.choice(("sign_white", "sign_yellow", "rust")))
      for k in range(7):
        box(layer, (0, 0.14, 3.2 + k * 0.45), (0.3, 0.04, 0.04), "rust")
      layer.reset()
      top = (x + lean[1] * height, y - lean[0] * height, height + 0.18)
      poles[side].append(top)
      y += 15.0
  for side, tops in poles.items():
    for a, b in zip(tops, tops[1:]):
      for offset in (-1.15, 0.0, 1.15):
        cable(layer, (a[0] + offset, a[1], a[2] - 0.3), (b[0] + offset, b[1], b[2] - 0.3), rng.uniform(0.5, 1.1))
      cable(layer, (a[0] - 0.8, a[1], a[2] - 1.15), (b[0] - 0.8, b[1], b[2] - 1.15), rng.uniform(0.7, 1.3))
  # Spans across the avenue and loose ends hanging over the street.
  for index in (1, 3, 5):
    left = poles[-1][index]
    right = poles[1][index]
    cable(layer, (left[0] + 1, left[1], left[2] - 0.3), (right[0] - 1, right[1], right[2] - 0.3), 1.7)
    cable(layer, (left[0] + 1, left[1], left[2] - 1.15), (right[0] - 1, right[1], right[2] - 1.15), 2.3)
  for side, index in ((-1, 2), (1, 1), (1, 4), (-1, 5)):
    top = poles[side][index]
    for _ in range(3):
      end_x = top[0] - side * rng.uniform(1.0, 3.4)
      end_y = top[1] + rng.uniform(-3, 3)
      tube(layer, [
        ((top[0], top[1], top[2] - 0.5), 0.016),
        (((top[0] + end_x) / 2, (top[1] + end_y) / 2, top[2] - 2.6), 0.016),
        ((end_x, end_y, rng.uniform(0.04, 1.8)), 0.016),
      ], "cable", n=3)
  # Pole snapped by the storm, resting across the bus with its wires still attached.
  fallen = (-7.8, 2.2, 0.1)
  layer.place(fallen, (0, 1.2, 0.35))
  tube(layer, [((0, 0, 0), 0.17), ((0, 0, 6), 0.12), ((0, 0, 9.5), 0.09)], "pole_concrete", n=6)
  box(layer, (0, 0, 9.0), (2.5, 0.12, 0.12), "wood_old", (0, 0, 0.4))
  layer.reset()
  tip = Vector((-7.8, 2.2, 0.1)) + Euler((0, 1.2, 0.35)).to_matrix() @ Vector((0, 0, 9.0))
  cable(layer, tip, (6.0, 8.0, 0.03), 0.6, 0.02)
  cable(layer, tip, (8.8, -0.5, 8.5), -0.5, 0.02)
  cable(layer, tip, (-1.0, 6.0, 0.03), 0.3, 0.02)
  clump(layer, (-7.9, 2.1, 0.2), (0.5, 0.4, 0.3), "concrete_grey")

  # Curved street lights.
  for side, y in ((1, -36.0), (-1, -14.0), (1, 8.0), (-1, 28.0), (1, 40.0)):
    x = side * 6.9
    layer.place((x, y, 0.18), (rng.uniform(-0.04, 0.04), 0, 0))
    tube(layer, [((0, 0, 0), 0.13), ((0, 0, 0.8), 0.1), ((0, 0, 0.9), 0.08), ((0, 0, 5.8), 0.06)], "metal_grey", n=6)
    tube(layer, [
      ((0, 0, 5.8), 0.06), ((-side * 0.25, 0, 6.5), 0.05), ((-side * 0.9, 0, 6.85), 0.045), ((-side * 1.8, 0, 6.85), 0.04),
    ], "metal_grey", n=5)
    box(layer, (-side * 2.05, 0, 6.82), (0.75, 0.28, 0.1), "metal_grey")
    box(layer, (-side * 2.05, 0, 6.76), (0.55, 0.2, 0.04), "glass")
    layer.reset()

  # Dead traffic light hanging from its arm.
  layer.place((-6.9, -16.5, 0.18))
  tube(layer, [((0, 0, 0), 0.14), ((0, 0, 6.6), 0.09)], "iron", n=6)
  tube(layer, [((0, 0, 6.2), 0.07), ((4.0, 0, 6.5), 0.05), ((5.2, 0, 6.4), 0.04)], "iron", n=5)
  for x in (2.6, 4.8):
    box(layer, (x, 0, 5.7), (0.34, 0.26, 1.0), "hazard_yellow")
    box(layer, (x, -0.14, 5.7), (0.42, 0.02, 1.1), "iron")
    for k in range(3):
      tube(layer, [((x, -0.14, 5.42 + k * 0.28), 0.1), ((x, -0.17, 5.42 + k * 0.28), 0.1)], "glass", n=8)
    box(layer, (x, 0, 6.28), (0.03, 0.03, 0.2), "cable")
  layer.reset()

  hydrant(layer, -6.7, -9.2)
  hydrant(layer, 6.8, 23.0)
  bus_stop(layer, 8.4, 2.0, -1)
  add_collider((7.9, 2.0, 1.4), (1.2, 4.2, 2.8))
  kiosk(layer, -8.0, 7.5)
  add_collider((-8.0, 7.5, 1.4), (1.9, 2.2, 2.8))
  phone_booth(layer, -8.6, 11.2)
  add_collider((-8.6, 11.2, 1.2), (0.8, 0.8, 2.4))
  phone_booth(layer, 8.6, -19.0)
  add_collider((8.6, -19.0, 1.2), (0.8, 0.8, 2.4))

  for position, angle in (((-1.8, -36.0, 0.0), 0.2), ((0.6, -37.2, 0.0), -0.3), ((2.8, 28.0, 0.0), 0.9), ((-2.4, 41.0, 0.0), -0.1)):
    traffic_barrier(layer, position, angle)
  for position, angle in (((-4.6, -39.0, 0.0), 0.1), ((4.4, -40.0, 0.0), -0.2), ((-1.0, 42.0, 0.0), 0.05), ((1.8, 42.4, 0.0), -0.08), ((-4.8, 42.0, 0.0), 0.2)):
    concrete_barrier(layer, position, angle)
    add_collider((position[0], position[1], 0.45), (2.5, 0.8, 0.9))

  # Planks, tires, crates, pallets and trash left by people who are gone.
  for _ in range(14):
    x = rng.uniform(-5.5, 5.5)
    y = rng.uniform(-40, 40)
    for k in range(rng.randint(2, 4)):
      box(layer, (x + rng.uniform(-0.3, 0.3), y + rng.uniform(-0.4, 0.4), 0.05 + k * 0.06), (rng.uniform(1.6, 3.2), 0.22, 0.05), rng.choice(("wood", "wood_old")), (0, rng.uniform(-0.05, 0.05), rng.random() * 3))
  for _ in range(12):
    x = rng.choice((-1, 1)) * rng.uniform(5.2, 9.0)
    y = rng.uniform(-42, 42)
    z = 0.18 if abs(x) > 6.2 else 0.0
    tube(layer, [((x, y - 0.14, z + 0.32), 0.3), ((x, y + 0.14, z + 0.32), 0.3)], "tire", n=9)
  for _ in range(16):
    x = rng.choice((-1, 1)) * rng.uniform(6.6, 9.2)
    y = rng.uniform(-42, 42)
    size = rng.uniform(0.3, 0.55)
    for k in range(rng.randint(2, 5)):
      clump(layer, (x + rng.uniform(-0.5, 0.5), y + rng.uniform(-0.5, 0.5), 0.18 + size * 0.7), (size, size, size * 0.8), "trash", 0.25)
  for _ in range(9):
    x = rng.choice((-1, 1)) * rng.uniform(6.6, 9.0)
    y = rng.uniform(-42, 42)
    box(layer, (x, y, 0.42), (0.7, 0.5, 0.42), "sign_red", (0, 0, rng.random()))
    for k in range(3):
      box(layer, (x, y, 0.3 + k * 0.13), (0.72, 0.52, 0.05), "wood_old", (0, 0, rng.random() * 0.1))
  for _ in range(40):
    size = rng.uniform(0.12, 0.5)
    clump(layer, (rng.uniform(-9, 9), rng.uniform(-44, 44), size * 0.4), (size, size * 0.8, size * 0.6), rng.choice(("concrete_grey", "concrete_stain", "brick_red")), 0.3)

  deer(layer, (-2.8, 10.6, 0.03), 2.2, True)
  deer(layer, (-0.9, 13.0, 0.0), 2.9, False)
  for index, side in ((1, 1), (1, -1), (3, 1), (4, -1), (5, 1)):
    top = poles[side][index]
    for k in range(rng.randint(1, 3)):
      vulture(layer, (top[0] + rng.uniform(-1.0, 1.0), top[1], top[2] - 0.34), rng.random() * math.tau)
  layer.build()


def ivy_sheet(layer, wall_x, street, center_y, top, bottom, half_width, relief):
  """One continuous, wall-hugging skin of ivy with a scalloped edge and a pillowed middle."""
  cell = 0.6
  rows = max(2, int((top - bottom) / cell))
  columns = 8
  drift = 0.0
  grid = []
  for row in range(rows + 1):
    amount = row / rows
    # Wide near the top, then narrowing into the point the ivy hangs from.
    width = half_width * (0.5 + 0.5 * math.cos(amount * math.pi / 2)) * rng.uniform(0.82, 1.18)
    drift += rng.uniform(-0.22, 0.22)
    points = []
    for column in range(columns + 1):
      across = column / columns * 2 - 1
      edge = column in (0, columns) or row in (0, rows)
      scallop = rng.uniform(0.0, 0.42) * (1 if across > 0 else -1) if column in (0, columns) else 0.0
      bulge = 0.0 if edge else rng.uniform(0.14, 0.38)
      points.append(Vector((
        wall_x + street * (relief + 0.03 + bulge),
        center_y + drift + across * width + scallop,
        top - amount * (top - bottom) + rng.uniform(-0.22, 0.22),
      )))
    grid.append(points)
  grid_triangles(layer, grid)


def tendril(layer, wall_x, street, y, top, length):
  """Hanging stem with paired leaves laid flat towards the street, not scattered."""
  points = []
  z = top
  while z > top - length:
    points.append(((wall_x + street * rng.uniform(0.0, 0.08), y + rng.uniform(-0.1, 0.1), z), 0.022))
    z -= 0.7
  if len(points) < 2:
    return
  tube(layer, points, "vine", n=3)
  for position, _ in points[1:]:
    for side in (-1, 1):
      base = Vector(position) + Vector((street * 0.04, 0, 0))
      out = Vector((0, side * 0.22, -0.1))
      tip = base + out + Vector((0, 0, -0.12))
      layer.add(
        [base, base + out * 0.5 + Vector((street * 0.04, 0, 0.07)), tip, base + out * 0.5 + Vector((street * 0.04, 0, -0.1))],
        [(0, 1, 2, 3)],
        rng.choice(LEAVES),
        True,
      )


def ivy_curtain(layer, wall_x, street, y, top, drop, relief, floor):
  """Large sheet, a few overlapping patches for depth, and stems hanging past the edge."""
  bottom = max(top - drop, floor)
  face = wall_x + street * relief
  half_width = rng.uniform(1.3, 2.1)
  ivy_sheet(layer, wall_x, street, y, top, bottom, half_width, relief)
  for _ in range(rng.randint(2, 4)):
    # Smaller skins on top give the foliage layers without adding many faces.
    patch_top = rng.uniform(bottom + 1.0, top)
    ivy_sheet(
      layer, wall_x, street, y + rng.uniform(-half_width, half_width) * 0.7, patch_top,
      max(bottom, patch_top - rng.uniform(1.6, 3.0)), rng.uniform(0.55, 0.95), relief + 0.14,
    )
  for _ in range(rng.randint(2, 3)):
    tendril(layer, wall_x, street, y + rng.uniform(-half_width, half_width) * 0.8, bottom + 0.6, rng.uniform(1.0, 2.6))


def tree(layer, x, y, height, crown):
  """Mushroom-shaped crowns as in reference 07, grown through the broken sidewalk."""
  z = 0.1
  bend = rng.uniform(-1.0, 1.0)
  tube(layer, [
    ((x, y, z), 0.42), ((x, y, z + 0.5), 0.3), ((x + bend * 0.25, y, z + height * 0.45), 0.24),
    ((x + bend * 0.7, y, z + height * 0.8), 0.18), ((x + bend, y, z + height), 0.1),
  ], "bark", n=6)
  for k in range(4):
    angle = k * math.pi / 2 + rng.random()
    tube(layer, [
      ((x + math.cos(angle) * 0.2, y + math.sin(angle) * 0.2, z + 0.25), 0.14),
      ((x + math.cos(angle) * 0.9, y + math.sin(angle) * 0.9, z), 0.05),
    ], "bark", n=4)
  top = Vector((x + bend, y, z + height))
  for k in range(5):
    angle = k * math.tau / 5 + rng.random()
    reach = rng.uniform(0.5, 0.8) * crown
    end = top + Vector((math.cos(angle) * reach, math.sin(angle) * reach, rng.uniform(0.0, 0.6)))
    tube(layer, [(tuple(top - Vector((0, 0, 1.2))), 0.12), (tuple(end), 0.04)], "bark", n=4)
  crown_dome(layer, top + Vector((0, 0, 0.5)), crown, crown * 0.44)
  for k in range(6):
    # Lobes around the rim keep the mushroom outline of the reference.
    angle = k * math.tau / 6 + rng.random() * 0.5
    reach = crown * rng.uniform(0.55, 0.85)
    lobe = crown * rng.uniform(0.34, 0.46)
    crown_dome(layer, top + Vector((math.cos(angle) * reach, math.sin(angle) * reach, 0.45)), lobe, lobe * 0.55, segments=8)


def build_vegetation():
  layer = Layer("vegetation", chunk=24.0)
  for wall_x, street, y0, y1, top, relief, floor in facades:
    length = y1 - y0
    masses = max(2, int(length / 4.2))
    for k in range(masses):
      y = y0 + (k + 0.5) * length / masses + rng.uniform(-0.9, 0.9)
      start = top - rng.uniform(0.0, 2.0)
      ivy_curtain(layer, wall_x, street, y, start, top * rng.uniform(0.45, 1.0), relief, floor)
    for _ in range(int(length / 2.5)):
      # Weeds taking the foot of the wall and the balconies.
      plant_y = rng.uniform(y0 + 0.5, y1 - 0.5)
      blade_plant(layer, (wall_x + street * rng.uniform(0.3, 1.4), plant_y, 0.18), rng.uniform(0.7, 1.6))
    for _ in range(int(length * 1.6)):
      grass_tuft(layer, (wall_x + street * rng.uniform(0.2, 3.3), rng.uniform(y0, y1), 0.18), rng.uniform(0.3, 0.75))
    for _ in range(int(length / 6)):
      size = rng.uniform(0.5, 1.0)
      crown_dome(layer, (wall_x + street * rng.uniform(0.3, 1.8), rng.uniform(y0, y1), 0.2), size, size * 0.75, segments=7)

  for x, y, height, crown in (
    (-8.2, -29.0, 6.5, 3.6), (8.1, -12.0, 7.5, 4.0), (-8.0, 17.0, 6.0, 3.4), (8.2, 28.5, 7.0, 3.8),
    (-5.2, 36.0, 5.5, 3.2), (-7.9, -42.0, 5.5, 3.0),
  ):
    tree(layer, x, y, height, crown)
    add_collider((x, y, 2.0), (0.8, 0.8, 4.0))
    for _ in range(4):
      blade_plant(layer, (x + rng.uniform(-1.5, 1.5), y + rng.uniform(-1.5, 1.5), 0.15), rng.uniform(0.8, 1.5))

  for _ in range(44):
    blade_plant(layer, (rng.uniform(-5.6, 5.6), rng.uniform(-44, 44), 0.02), rng.uniform(0.5, 1.2))
  for _ in range(320):
    grass_tuft(layer, (rng.uniform(-6.0, 6.0), rng.uniform(-44, 44), 0.01), rng.uniform(0.18, 0.55))
  for side in (-1, 1):
    for _ in range(110):
      grass_tuft(layer, (side * rng.uniform(5.6, 6.6), rng.uniform(-44, 44), 0.05), rng.uniform(0.3, 0.8))
  for x, y, size in ((-1.8, 4.5, 1.6), (0.2, -3.6, 1.3), (3.9, 8.0, 1.5), (-3.4, -7.6, 1.2), (5.2, -9.0, 1.6)):
    blade_plant(layer, (x, y, 0.02), size, blades=10)
  # Thick roots crossing the street, as if the avenue had been buried for years.
  for start, end in (((-5.9, -30.0), (-1.5, -28.0)), ((5.9, 5.0), (2.4, 7.2)), ((-5.9, 26.0), (-2.2, 29.0))):
    mid_x = (start[0] + end[0]) / 2
    mid_y = (start[1] + end[1]) / 2 + 0.7
    tube(layer, [
      ((start[0], start[1], 0.2), 0.2), ((mid_x, mid_y, 0.16), 0.15), ((end[0], end[1], 0.0), 0.05),
    ], "bark", n=5)
  layer.build()


def build_backdrop():
  layer = Layer("backdrop")
  # Dark city blocks that fill the gaps above the street walls.
  for side in (-1, 1):
    for k in range(13):
      x = side * rng.uniform(34, 62)
      y = -66 + k * 13 + rng.uniform(-3, 3)
      width = rng.uniform(12, 20)
      height = rng.uniform(26, 60)
      box(layer, (x, y, height / 2), (width, 12, height), "skyline")
      for row in range(int(height / 7)):
        box(layer, (x - side * (width / 2 + 0.05), y, 4 + row * 7), (0.1, 10.5, 2.2), "window_dark")
      if rng.random() < 0.5:
        box(layer, (x, y, height + 2), (6, 5, 4), "skyline")
      tube(layer, [((x, y, height), 0.2), ((x, y, height + 9), 0.03)], "iron", n=3)
  for side in (-1, 1):
    for k in range(6):
      y = rng.uniform(-30, 40)
      size = rng.uniform(5, 9)
      clump(layer, (side * 25, y, 14 + rng.uniform(0, 10)), (size, size * 1.5, size * 0.7), rng.choice(("leaf_dark", "mountain")))

  # El Avila, the mountain that closes every view north of Caracas.
  columns = 44
  rows = 12
  span = 720.0
  depth = 280.0
  grid = []
  for row in range(rows + 1):
    for column in range(columns + 1):
      x = -span / 2 + column * span / columns
      amount = row / rows
      y = 170 + amount * depth
      ridge = math.sin(amount * math.pi) ** 0.8
      wave = 0.62 + 0.26 * math.sin(x * 0.017 + 0.8) + 0.16 * math.sin(x * 0.047 + 2.0) + 0.08 * math.sin(x * 0.11)
      height = 215 * ridge * wave + rng.uniform(-9, 9) * ridge
      grid.append((x, y, height))
  faces = []
  for row in range(rows):
    for column in range(columns):
      a = row * (columns + 1) + column
      faces.append((a, a + 1, a + columns + 2, a + columns + 1))
  layer.add(grid, faces, "mountain")
  far = []
  for column in range(columns + 1):
    x = -span / 2 + column * span / columns
    far.append((x, 330, 0.0))
    far.append((x, 330, 155 + 80 * abs(math.sin(x * 0.012)) + rng.uniform(-15, 15)))
  far_faces = [(k * 2, k * 2 + 1, k * 2 + 3, k * 2 + 2) for k in range(columns)]
  layer.add(far, far_faces, "mountain_far")
  for _ in range(70):
    # Trees climbing the lower slopes.
    size = rng.uniform(6, 16)
    clump(layer, (rng.uniform(-300, 300), rng.uniform(150, 215), rng.uniform(4, 45)), (size * 1.5, size, size * 0.7), rng.choice(("mountain", "leaf_dark", "mountain_far")))

  # Low storm clouds. Their undersides are what the player sees between the buildings.
  for _ in range(90):
    x = rng.uniform(-260, 260)
    y = rng.uniform(-160, 340)
    z = rng.uniform(80, 150)
    for _ in range(rng.randint(3, 6)):
      width = rng.uniform(22, 60)
      clump(
        layer,
        (x + rng.uniform(-45, 45), y + rng.uniform(-30, 30), z + rng.uniform(-9, 9)),
        (width, width * 0.7, width * 0.22),
        rng.choice(("cloud", "cloud", "cloud_light")),
        0.3,
      )
  layer.build()


def build_colliders():
  # Godot turns meshes named -colonly into static collision and does not draw them.
  for side in (-1, 1):
    add_collider((side * 16.0, 0, 15.0), (1.0, 170.0, 30.0))
  for i, (center, size) in enumerate(colliders):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
    obj = bpy.context.object
    obj.dimensions = size
    bpy.ops.object.transform_apply(scale=True)
    obj.name = f"avenue_collider_{i}-colonly"
    obj.display_type = "WIRE"
    obj.hide_render = True
    for owner in list(obj.users_collection):
      owner.objects.unlink(obj)
    collection().objects.link(obj)


def finish():
  bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
  os.makedirs(os.path.dirname(GLB_PATH), exist_ok=True)
  bpy.ops.export_scene.gltf(filepath=GLB_PATH, export_format="GLB")


STAGES = [
  clear, build_ground, build_buildings, build_landmarks, build_vehicles, build_street_furniture,
  build_vegetation, build_backdrop, build_colliders, finish,
]

if __name__ == "__main__":
  for stage in STAGES:
    stage()
