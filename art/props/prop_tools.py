# Mesh and paint helpers shared by the prop scripts. Colors are sRGB, as in the other art scripts.
import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector


def linear(color):
  return tuple(channel ** 2.2 for channel in color) + (1.0,)


def material(name, color=(1, 1, 1), roughness=0.85, glow=0.0, image=None):
  mat = bpy.data.materials.new(name)
  mat.use_nodes = True
  mat.diffuse_color = linear(color)
  bsdf = mat.node_tree.nodes.get("Principled BSDF")
  bsdf.inputs["Base Color"].default_value = linear(color)
  bsdf.inputs["Roughness"].default_value = roughness
  if glow > 0.0:
    bsdf.inputs["Emission Color"].default_value = linear(color)
    bsdf.inputs["Emission Strength"].default_value = glow
  if image is not None:
    texture = mat.node_tree.nodes.new("ShaderNodeTexImage")
    texture.image = image
    mat.node_tree.links.new(texture.outputs["Color"], bsdf.inputs["Base Color"])
  return mat


class Shape:
  """Geometry gathered in plain lists, so one prop ends up as one mesh with flat faces."""

  def __init__(self):
    self.verts = []
    self.faces = []
    self.mats = []
    self.uvs = []

  def add(self, verts, faces, mats, uvs=None, at=None):
    """mats is one material or one per face; uvs holds one (u, v) per corner of each face."""
    base = len(self.verts)
    self.verts += [tuple(at @ Vector(v)) if at else tuple(v) for v in verts]
    self.faces += [tuple(base + i for i in face) for face in faces]
    self.mats += list(mats) if isinstance(mats, (list, tuple)) else [mats] * len(faces)
    self.uvs += list(uvs) if uvs else [None] * len(faces)

  def loft(self, rings, mat, caps=(True, True), at=None):
    """Joins closed rings of equal size. mat is a material or a function of (band, side)."""
    n = len(rings[0])
    verts = [v for ring in rings for v in ring]
    pick = mat if callable(mat) else lambda band, side: mat
    faces = []
    mats = []
    for band in range(len(rings) - 1):
      for side in range(n):
        next_side = (side + 1) % n
        faces.append((band * n + side, band * n + next_side, (band + 1) * n + next_side, (band + 1) * n + side))
        mats.append(pick(band, side))
    if caps[0]:
      faces.append(tuple(reversed(range(n))))
      mats.append(pick(0, 0))
    if caps[1]:
      faces.append(tuple((len(rings) - 1) * n + side for side in range(n)))
      mats.append(pick(len(rings) - 2, 0))
    self.add(verts, faces, mats, at=at)

  def lathe(self, profile, mat, n=12, at=None, caps=(True, True), turn=0.0):
    """Spins (radius, height) around Z. The half-step turn keeps a flat side toward the camera."""
    rings = []
    for radius, height in profile:
      rings.append([
        (radius * math.cos(turn + math.tau * (k + 0.5) / n), radius * math.sin(turn + math.tau * (k + 0.5) / n), height)
        for k in range(n)
      ])
    self.loft(rings, mat, caps, at)

  def tube(self, path, mat, n=6, side=None):
    """Lofts rings along path. Each entry is (position, radius along side, other radius)."""
    points = [Vector(entry[0]) for entry in path]
    first = (points[1] - points[0]).normalized()
    u = Vector(side) if side else (Vector((0, 1, 0)) if abs(first.y) < 0.8 else Vector((0, 0, 1)))
    rings = []
    for i, (_, ru, rv) in enumerate(path):
      tangent = (points[min(i + 1, len(points) - 1)] - points[max(i - 1, 0)]).normalized()
      u = (u - tangent * u.dot(tangent)).normalized()
      v = tangent.cross(u)
      rings.append([
        points[i] + u * ru * math.cos(math.pi / n + math.tau * k / n) + v * rv * math.sin(math.pi / n + math.tau * k / n)
        for k in range(n)
      ])
    self.loft(rings, mat)

  def extrude(self, outline, y0, y1, mat, at=None):
    """Pushes an (x, z) outline along Y."""
    self.loft([[(x, y, z) for x, z in outline] for y in (y0, y1)], mat, at=at)

  def box(self, low, high, mat, at=None):
    x0, y0, z0 = low
    x1, y1, z1 = high
    self.extrude([(x0, z0), (x1, z0), (x1, z1), (x0, z1)], y0, y1, mat, at)

  def finish(self, name):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(self.verts, [], self.faces)
    used = list(dict.fromkeys(self.mats))
    for mat in used:
      mesh.materials.append(mat)
    for polygon, mat in zip(mesh.polygons, self.mats):
      polygon.material_index = used.index(mat)
    if any(self.uvs):
      layer = mesh.uv_layers.new(name="uv")
      for polygon, corners in zip(mesh.polygons, self.uvs):
        for loop, uv in zip(polygon.loop_indices, corners or [(0.0, 0.0)] * polygon.loop_total):
          layer.data[loop].uv = uv
    solid = bmesh.new()
    solid.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(solid, faces=solid.faces)
    solid.to_mesh(mesh)
    solid.free()
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    print(name, "triangles", sum(len(polygon.vertices) - 2 for polygon in mesh.polygons))
    return obj


def face_up():
  """A lathe's Z axis turned to point at the camera, along -Y."""
  return Matrix.Rotation(math.radians(90), 4, "X")


def smooth_noise(width, height, cells_x, cells_y, rng):
  grid = rng.random((cells_y + 2, cells_x + 2))
  xs = np.linspace(0, cells_x, width)
  ys = np.linspace(0, cells_y, height)
  left = xs.astype(int)
  top = ys.astype(int)
  fx = xs - left
  fy = ys - top
  fx = fx * fx * (3 - 2 * fx)
  fy = (fy * fy * (3 - 2 * fy))[:, None]
  rows = grid[:, left] * (1 - fx) + grid[:, left + 1] * fx
  return rows[top] * (1 - fy) + rows[top + 1] * fy


def fractal_noise(width, height, cells_x, cells_y, seed, octaves=4):
  """Noise stretched to 0..1, so a threshold covers the same share of any image."""
  rng = np.random.default_rng(seed)
  total = np.zeros((height, width))
  weight = 1.0
  for octave in range(octaves):
    total += weight * smooth_noise(width, height, cells_x << octave, cells_y << octave, rng)
    weight *= 0.5
  return (total - total.min()) / (total.max() - total.min())


class Canvas:
  """A small painter in pixels: every shape is an antialiased mask over an RGB array."""

  def __init__(self, width, height, color):
    self.rgb = np.ones((height, width, 3)) * np.array(color, dtype=float)
    self.y, self.x = np.mgrid[0:height, 0:width] + 0.5

  def blend(self, mask, color, alpha=1.0):
    mask = np.clip(mask, 0.0, 1.0)[..., None] * alpha
    self.rgb = self.rgb * (1 - mask) + mask * np.array(color, dtype=float)

  def rect(self, x0, y0, x1, y1, color, alpha=1.0):
    mask = np.minimum.reduce([self.x - x0, x1 - self.x, self.y - y0, y1 - self.y]) + 0.5
    self.blend(mask, color, alpha)

  def circle(self, cx, cy, radius, color, alpha=1.0):
    self.blend(radius - np.hypot(self.x - cx, self.y - cy) + 0.5, color, alpha)

  def stroke(self, points, width, color, alpha=1.0):
    nearest = np.full(self.x.shape, np.inf)
    for (ax, ay), (bx, by) in zip(points, points[1:]):
      dx, dy = bx - ax, by - ay
      t = np.clip(((self.x - ax) * dx + (self.y - ay) * dy) / max(dx * dx + dy * dy, 1e-9), 0, 1)
      nearest = np.minimum(nearest, np.hypot(self.x - ax - t * dx, self.y - ay - t * dy))
    self.blend(width * 0.5 - nearest + 0.5, color, alpha)

  def polygon(self, points, color, alpha=1.0):
    inside = np.zeros(self.x.shape, dtype=bool)
    for (ax, ay), (bx, by) in zip(points, points[1:] + points[:1]):
      crosses = (ay > self.y) != (by > self.y)
      inside ^= crosses & (self.x < (bx - ax) * (self.y - ay) / (by - ay + 1e-9) + ax)
    self.blend(inside.astype(float), color, alpha)

  def age(self, seed, stain=0.35):
    """Yellowed paper: brown blotches and a darker, handled border."""
    height, width = self.x.shape
    blotches = fractal_noise(width, height, 5, 5, seed)
    self.blend((blotches - 0.5) * 3.0, (0.42, 0.3, 0.17), stain)
    border = np.minimum.reduce([self.x, width - self.x, self.y, height - self.y]) / (0.06 * min(width, height))
    self.blend(1.0 - border, (0.3, 0.22, 0.13), stain)


def image_from(name, rgb):
  """Packs an sRGB array, first row on top, into the blend so the exporter embeds it."""
  height, width, _ = rgb.shape
  image = bpy.data.images.new(name, width, height, alpha=False)
  pixels = np.ones((height, width, 4))
  pixels[..., :3] = np.clip(rgb, 0.0, 1.0)
  image.pixels.foreach_set(pixels[::-1].ravel().astype(np.float32))
  image.file_format = "PNG"
  image.pack()
  return image
