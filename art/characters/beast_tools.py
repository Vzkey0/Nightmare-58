# Helpers shared by the four-legged enemies: a body lofted from stations, paws and fur shading.
import math

import bpy
from mathutils import Vector

SIDES = 12


class Body:
  """Stations from the tail to the front: (y, center z, half width, half height, spine ridge, belly).
  belly scales the half height below the center, so a value under 1 flattens it and over 1 deepens it."""

  def __init__(self, stations):
    self.stations = stations

  def at(self, y):
    for a, b in zip(self.stations, self.stations[1:]):
      if b[0] <= y <= a[0]:
        t = (a[0] - y) / (a[0] - b[0])
        return tuple(pa + (pb - pa) * t for pa, pb in zip(a, b))
    return self.stations[0] if y > self.stations[0][0] else self.stations[-1]

  def surface(self, y, angle, lift=0.0):
    """A point on the body at y; angle 90 is the spine, 0 the left flank."""
    _, zc, w, h, ridge, belly = self.at(y)
    a = math.radians(angle)
    below = belly if math.sin(a) < 0 else 1.0
    return Vector(((w + lift) * math.cos(a), y, zc + (h * below + lift) * math.sin(a) + ridge * max(0.0, math.sin(a)) ** 12))

  def loft(self, shape, mat, rng):
    rings = []
    for y, zc, w, h, ridge, belly in self.stations:
      ring = []
      for k in range(SIDES):
        a = math.pi / 2 + math.tau * k / SIDES
        below = belly if math.sin(a) < 0 else 1.0
        jitter = 0.035 * min(w, h)
        ring.append((
          w * math.cos(a) + rng.uniform(-jitter, jitter),
          y + rng.uniform(-0.008, 0.008),
          zc + h * below * math.sin(a) + (ridge if k == 0 else 0.0) + rng.uniform(-jitter, jitter),
        ))
      rings.append(ring)
    shape.loft(rings, mat)


def along(path, y):
  """Center and radii of a tube path at y, for paths that run toward -Y."""
  for a, b in zip(path, path[1:]):
    if b[0][1] <= y <= a[0][1]:
      t = (a[0][1] - y) / (a[0][1] - b[0][1])
      return Vector(a[0]).lerp(Vector(b[0]), t), a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t
  end = path[0] if y > path[0][0][1] else path[-1]
  return Vector(end[0]), end[1], end[2]


def mirror(path):
  return [((-p[0], p[1], p[2]), ru, rv) for p, ru, rv in path]


def both(shape, path, mat, n=6, side=None):
  shape.tube(path, mat, n=n, side=side)
  shape.tube(mirror(path), mat, n=n, side=side)


def paw(shape, skin, claw, wrist, forward, spread, toe_length, sign, size=1.0, claw_length=0.03):
  forward = Vector(forward).normalized()
  across = Vector((sign, 0, 0))
  palm_end = wrist + forward * 0.05 * size + Vector((0, 0, -0.03 * size))
  shape.tube([(wrist, 0.03 * size, 0.022 * size), (palm_end, 0.035 * size, 0.014 * size)], skin, n=6, side=(1, 0, 0))
  for offset in spread:
    knuckle = palm_end + across * offset
    direction = (forward + across * offset * 6 / size).normalized()
    tip = knuckle + direction * toe_length + Vector((0, 0, -0.012 * size))
    shape.tube([(knuckle, 0.009 * size, 0.008 * size), (tip, 0.007 * size, 0.006 * size)], skin, n=4)
    shape.tube([(tip, 0.006 * size, 0.005 * size), (tip + direction * claw_length + Vector((0, 0, -0.016 * size)), 0.001, 0.001)], claw, n=4)


def tuft(shape, mat, base, out, length, sweep, width=0.03):
  """A clump of fur: a flat three-sided spike combed back along +Y."""
  tip = base + out * length + Vector((0, sweep, 0))
  shape.tube([(base, width, width * 0.53), (tip, 0.002, 0.002)], mat, n=3, side=out)


def shade_fur(obj, materials, tones, rng, mid, bald=None, bald_name="skin_raw", scale=1.0):
  """Picks a fur tone per face from its normal, its height around mid and a little noise.
  tones go from lit to shadowed, or are a function of the face center that returns them, for coats
  with a pattern. Faces where bald(center) is true get the bare skin instead. scale is how much the
  model was enlarged, so the height gradient spans the same share of the body."""
  palette = tones if callable(tones) else lambda c: tones
  mesh = obj.data
  names = [mat.name for mat in mesh.materials]
  fur = names.index("fur")

  def index(name):
    if name not in names:
      mesh.materials.append(materials[name])
      names.append(name)
    return names.index(name)

  for polygon in mesh.polygons:
    if polygon.material_index != fur:
      continue
    n = polygon.normal
    c = polygon.center
    light = n.z * 0.7 - n.y * 0.15 + (c.z / scale - mid) * 1.2 + rng.uniform(-0.28, 0.28)
    if bald and bald(c):
      polygon.material_index = index(bald_name)
      continue
    shades = palette(c)
    tone = shades[0] if light > 0.5 else shades[1] if light > 0.05 else shades[2] if light > -0.4 else shades[3]
    polygon.material_index = index(tone)
  mesh.materials[fur] = materials[palette(Vector())[-1]]


class Tags:
  """Marks which bones may move each run of vertices, from where it is called to the next call."""

  def __init__(self, shape):
    self.shape = shape
    self.marks = []

  def __call__(self, *bones):
    self.marks.append((len(self.shape.verts), bones))

  def ranges(self):
    ends = [start for start, _ in self.marks[1:]] + [len(self.shape.verts)]
    return [(start, end, bones) for (start, bones), end in zip(self.marks, ends)]


def leg_bones(leg, parent, top, joint, ankle, ball, tip):
  """A leg as upper, lower, foot and toes; the IK solves the first two to reach the ankle."""
  return {
    f"upper_{leg}": (top, joint, parent),
    f"lower_{leg}": (joint, ankle, f"upper_{leg}"),
    f"foot_{leg}": (ankle, ball, f"lower_{leg}"),
    f"toes_{leg}": (ball, tip, f"foot_{leg}"),
  }


def chain_bones(prefix, points, parent):
  """A chain like the tail: one bone between each pair of points, each child of the one before."""
  table = {}
  for i, (a, b) in enumerate(zip(points, points[1:])):
    table[f"{prefix}_{i + 1}"] = (a, b, parent if i == 0 else f"{prefix}_{i}")
  return table


def mirrored(table):
  """Adds an _r twin, flipped on X, for every bone that ends in _l."""
  result = dict(table)
  for name, (head, tail, parent) in table.items():
    if name.endswith("_l"):
      flip = lambda p: (-p[0], p[1], p[2])
      twin = parent[:-2] + "_r" if parent.endswith("_l") else parent
      result[name[:-2] + "_r"] = (flip(head), flip(tail), twin)
  return result


def rig(body, name, table, ranges):
  """Builds the armature and weights each tagged run of vertices to its nearest two bones."""
  data = bpy.data.armatures.new(f"{name}_armature")
  armature = bpy.data.objects.new(f"armature_{name}", data)
  bpy.context.scene.collection.objects.link(armature)
  bpy.context.view_layer.objects.active = armature
  bpy.ops.object.mode_set(mode="EDIT")
  created = {}
  for bone, (head, tail, _) in table.items():
    edit_bone = data.edit_bones.new(bone)
    edit_bone.head = head
    edit_bone.tail = tail
    created[bone] = edit_bone
  for bone, (_, _, parent) in table.items():
    if parent:
      created[bone].parent = created[parent]
  bpy.ops.object.mode_set(mode="OBJECT")

  segments = {bone: (Vector(head), Vector(tail)) for bone, (head, tail, _) in table.items()}
  groups = {}
  for start, end, bones in ranges:
    for bone in bones:
      if bone not in groups:
        groups[bone] = body.vertex_groups.new(name=bone)
    for i in range(start, end):
      co = body.data.vertices[i].co
      near = sorted((distance_to(co, *segments[bone]), bone) for bone in bones)[:2]
      weights = [1.0 / (d + 0.005) ** 4 for d, _ in near]
      for weight, (_, bone) in zip(weights, near):
        groups[bone].add([i], weight / sum(weights), "REPLACE")
  body.parent = armature
  body.modifiers.new("armature", "ARMATURE").object = armature
  return armature


def distance_to(point, head, tail):
  span = tail - head
  t = max(0.0, min(1.0, (point - head).dot(span) / span.length_squared))
  return (point - head.lerp(tail, t)).length
