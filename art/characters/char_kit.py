# Reusable low-poly humanoid character kit for Nightmare 58 (Blender 5.2+).
# Encodes all art conventions (-Y forward, z=0 feet, flat-shaded color-by-material, tuned clearances)
# so each new character script only defines its unique silhouette, outfit, and props.
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
PROPS_DIR = os.path.abspath(os.path.join(HERE, "..", "props"))
if PROPS_DIR not in sys.path:
  sys.path.insert(0, PROPS_DIR)

from prop_tools import Shape, material  # noqa: E402


# --- Materials & colors ----------------------------------------------------------------------
def make_material(name, color, roughness=0.84, metallic=0.0):
  mat = material(name, color, roughness=roughness)
  bsdf = mat.node_tree.nodes.get("Principled BSDF")
  if bsdf is not None:
    bsdf.inputs["Metallic"].default_value = metallic
  return mat


def scale_rgb(rgb, factor):
  return tuple(max(0.0, min(1.0, c * factor)) for c in rgb)


def mix_rgb(a, b, t):
  return tuple(u + (v - u) * t for u, v in zip(a, b))


def face_materials(prefix, skin, hair, eye=(0.055, 0.036, 0.025)):
  """Standard tuned facial materials (eye roughness 0.44 avoids gray specular glare)."""
  return {
    "skin": make_material(f"{prefix}_skin", skin, roughness=0.84),
    "hair": make_material(f"{prefix}_hair", hair, roughness=0.88),
    "hair_dark": make_material(f"{prefix}_hair_dark", scale_rgb(hair, 0.68), roughness=0.88),
    "eye": make_material(f"{prefix}_eye", eye, roughness=0.44),
    "eye_white": make_material(f"{prefix}_eye_white", (0.86, 0.83, 0.78), roughness=0.48),
    "lid": make_material(f"{prefix}_lid", scale_rgb(skin, 0.76), roughness=0.86),
    "skin_bag": make_material(f"{prefix}_skin_bag", scale_rgb(skin, 0.85), roughness=0.86),
    "lip": make_material(f"{prefix}_lip", mix_rgb(skin, (0.46, 0.22, 0.19), 0.34), roughness=0.82),
    "stubble": make_material(f"{prefix}_stubble", mix_rgb(skin, hair, 0.46), roughness=0.88),
  }


# --- Geometry primitives ---------------------------------------------------------------------
def ring(z, a, front, back, y=0.0, n=12, power=2.5, x=0.0):
  """Rounded-box horizontal ring: half-width a, front (-Y) and back (+Y) depths."""
  pts = []
  for k in range(n):
    phi = math.tau * (k + 0.5) / n
    s, c = math.sin(phi), math.cos(phi)
    px = a * math.copysign(abs(s) ** (2.0 / power), s)
    depth = front if c > 0 else back
    py = -depth * math.copysign(abs(c) ** (2.0 / power), c)
    pts.append((x + px, y + py, z))
  return pts


def mirror_x(points):
  return [(-x, y, z) for x, y, z in points]


def solid_shell(shape, rows, thickness, mat_outer, mat_inner=None, mat_edge=None, inward_dir=None):
  """Closed faceted plate from open rows (r x c), extruded along inward_dir."""
  mat_inner = mat_inner or mat_outer
  mat_edge = mat_edge or mat_outer
  rcount, ccount = len(rows), len(rows[0])
  outer = [[Vector(p) for p in row] for row in rows]
  inner = []
  for r in range(rcount):
    irow = []
    for c in range(ccount):
      p = outer[r][c]
      if inward_dir is not None:
        n = inward_dir(p, r, c)
      else:
        dr = outer[min(r + 1, rcount - 1)][c] - outer[max(r - 1, 0)][c]
        dc = outer[r][min(c + 1, ccount - 1)] - outer[r][max(c - 1, 0)]
        n = dc.cross(dr)
        n = n.normalized() if n.length > 1e-6 else Vector((0, 1, 0))
      irow.append(p + n * thickness)
    inner.append(irow)

  verts = [tuple(p) for row in outer for p in row] + [tuple(p) for row in inner for p in row]
  base = rcount * ccount
  faces, mats = [], []
  for r in range(rcount - 1):
    for c in range(ccount - 1):
      a, b = r * ccount + c, r * ccount + c + 1
      faces.append((a, b, b + ccount, a + ccount))
      mats.append(mat_outer)
      faces.append((base + a + ccount, base + b + ccount, base + b, base + a))
      mats.append(mat_inner)
  for r in range(rcount - 1):
    for c in (0, ccount - 1):
      a, b = r * ccount + c, (r + 1) * ccount + c
      faces.append((a, b, base + b, base + a) if c else (b, a, base + a, base + b))
      mats.append(mat_edge)
  for r in (0, rcount - 1):
    for c in range(ccount - 1):
      a, b = r * ccount + c, r * ccount + c + 1
      faces.append((b, a, base + a, base + b) if r == 0 else (a, b, base + b, base + a))
      mats.append(mat_edge)
  shape.add(verts, faces, mats)


# --- Parametric sculpted head ----------------------------------------------------------------
DEFAULT_HEAD_STATIONS = [
  # (dz from base_z, half_w, front, back, center_y)
  (0.000, 0.036, 0.062, 0.034, -0.004),  # Chin tip
  (0.022, 0.058, 0.088, 0.052, -0.002),  # Lower jaw
  (0.054, 0.078, 0.098, 0.074, 0.000),   # Jaw angle / mouth
  (0.088, 0.088, 0.102, 0.090, 0.001),   # Lower cheeks
  (0.122, 0.095, 0.104, 0.100, 0.002),   # Cheekbones
  (0.146, 0.094, 0.101, 0.106, 0.004),   # Eye line
  (0.172, 0.095, 0.104, 0.110, 0.005),   # Brow ridge
  (0.202, 0.090, 0.096, 0.108, 0.007),   # Forehead
  (0.230, 0.078, 0.078, 0.094, 0.009),   # Upper skull
  (0.248, 0.056, 0.055, 0.068, 0.010),   # Dome
  (0.260, 0.024, 0.024, 0.030, 0.010),   # Crown apex
]


class HeadBuilder:
  """Parametric sculpted low-poly head. Anchor at chin base_z (default 1.522 for ~1.78m adult)."""

  def __init__(
    self,
    base_z=1.522,
    y_offset=0.0,
    width_scale=1.0,
    depth_scale=1.0,
    height_scale=1.0,
    cheek_hollow=0.0052,
    brow_strength=0.0062,
    chin_strength=0.0050,
    jaw_width=1.0,
  ):
    self.base_z = base_z
    self.y_offset = y_offset
    self.ws = width_scale
    self.ds = depth_scale
    self.hs = height_scale
    self.cheek_hollow = cheek_hollow
    self.brow_strength = brow_strength
    self.chin_strength = chin_strength
    self.stations = []
    for dz, a, f, b, yc in DEFAULT_HEAD_STATIONS:
      jw = jaw_width if dz < 0.09 else 1.0
      self.stations.append((
        base_z + dz * height_scale,
        a * width_scale * jw,
        f * depth_scale,
        b * depth_scale,
        y_offset + yc * depth_scale,
      ))
    self.center = Vector((0.0, y_offset + 0.004, base_z + 0.130 * height_scale))

  def z_at(self, dz):
    return self.base_z + dz * self.hs

  def point(self, z, phi, grow=0.0, sculpt=True):
    st = self.stations
    for s0, s1 in zip(st, st[1:]):
      if z <= s1[0]:
        t = max(0.0, min(1.0, (z - s0[0]) / max(1e-6, s1[0] - s0[0])))
        break
    else:
      s0, s1, t = st[-2], st[-1], 1.0
    a, f, b, y = (u + (v - u) * t for u, v in zip(s0[1:], s1[1:]))
    abs_phi = abs(math.atan2(math.sin(phi), math.cos(phi)))
    s, c = math.sin(phi), math.cos(phi)

    dz = (z - self.base_z) / self.hs
    relief = 0.0
    if sculpt and c > -0.15:
      eye_s = math.exp(-((dz - 0.146) / 0.015) ** 2) * math.exp(-((abs_phi - 0.36) / 0.19) ** 2)
      relief -= 0.0085 * eye_s
      brow_s = math.exp(-((dz - 0.171) / 0.013) ** 2) * math.exp(-(abs_phi / 0.62) ** 2)
      relief += self.brow_strength * brow_s
      cheek_b = math.exp(-((dz - 0.122) / 0.017) ** 2) * math.exp(-((abs_phi - 0.65) / 0.25) ** 2)
      relief += 0.0055 * cheek_b
      hollow = math.exp(-((dz - 0.086) / 0.022) ** 2) * math.exp(-((abs_phi - 0.68) / 0.28) ** 2)
      relief -= self.cheek_hollow * hollow
      temple = math.exp(-((dz - 0.176) / 0.022) ** 2) * math.exp(-((abs_phi - 1.12) / 0.22) ** 2)
      relief -= 0.0042 * temple
      chin = math.exp(-((dz - 0.018) / 0.018) ** 2) * math.exp(-(abs_phi / 0.36) ** 2)
      relief += self.chin_strength * chin
      mouth_r = math.exp(-((dz - 0.068) / 0.011) ** 2) * math.exp(-(abs_phi / 0.28) ** 2)
      relief -= 0.0032 * mouth_r

    power = 2.45
    px = (a + grow + relief * 0.62) * math.copysign(abs(s) ** (2.0 / power), s)
    depth = (f if c > 0 else b) + grow + relief
    py = y - depth * math.copysign(abs(c) ** (2.0 / power), c)
    return (px, py, z)

  def shell(self, shape, rows, thickness, mat):
    c = self.center
    solid_shell(shape, rows, thickness, mat, inward_dir=lambda p, r, k: (c - p).normalized())

  def hairline(self, phi, recede=0.0):
    side = abs(math.atan2(math.sin(phi), math.cos(phi))) / math.pi
    temple_dip = (0.014 + recede) * math.exp(-((side - 0.23) / 0.08) ** 2)
    nape = math.sin(math.pi / 2 * min(1.0, max(0.0, (side - 0.48) / 0.32)))
    dz = 0.204 + recede * 0.5 + temple_dip - 0.064 * min(1.0, side / 0.45) ** 1.45 - 0.082 * nape
    return self.z_at(dz)

  def beardline(self, phi):
    side = abs(math.atan2(math.sin(phi), math.cos(phi))) / math.pi
    dz = 0.066 + 0.016 * (side ** 1.4) + 0.060 * max(0.0, (side - 0.36) / 0.24) ** 1.6
    return self.z_at(dz)

  def build_skull_and_face(self, shape, mats, n_ring=18, brow_tilt=0.0, nose_scale=1.0, ears=True):
    """Builds sculpted cranium, nose, calm almond eyes, lids, bags, brows, and ears."""
    phis = [math.tau * (k + 0.5) / n_ring for k in range(n_ring)]
    rings = [[self.point(st[0], phi) for phi in phis] for st in self.stations]
    shape.loft(rings, mats["skin"], caps=(True, True))

    # Nose anchored to head offset
    yo, ns = self.y_offset, nose_scale
    nose_rel = [
      (0.0, -0.100, 0.164),
      (-0.0085 * ns, -0.109, 0.142),
      (0.0085 * ns, -0.109, 0.142),
      (0.0, -0.100 - 0.030 * ns, 0.116),
      (-0.020 * ns, -0.106, 0.108),
      (0.020 * ns, -0.106, 0.108),
      (0.0, -0.115, 0.100),
      (-0.015 * ns, -0.098, 0.128),
      (0.015 * ns, -0.098, 0.128),
      (-0.011 * ns, -0.120, 0.104),
      (0.011 * ns, -0.120, 0.104),
    ]
    nose_verts = [(x, yo + y * self.ds, self.z_at(dz)) for x, y, dz in nose_rel]
    shape.add(
      nose_verts,
      [(0, 1, 3), (0, 3, 2), (1, 7, 4), (1, 4, 9, 3), (2, 3, 10, 5), (2, 5, 8),
       (3, 9, 6), (3, 6, 10), (9, 4, 6), (10, 6, 5)],
      mats["skin"],
    )

    eye_z = self.z_at(0.145)
    almond = [(-0.130, -0.001), (-0.055, 0.0062), (0.045, 0.0065), (0.130, 0.0005), (0.055, -0.0050), (-0.055, -0.0050)]
    for side in (-1, 1):
      def on_face(dphi, z, grow, s=side):
        return self.point(z, s * (0.36 + dphi), grow)

      shape.add([on_face(dp, eye_z + dz, 0.0020) for dp, dz in almond], [(0, 1, 2, 3, 4, 5)], mats["eye_white"])
      shape.add([on_face(dp * 0.70 - 0.008, eye_z + 0.0002 + dz * 0.96, 0.0036) for dp, dz in almond], [(0, 1, 2, 3, 4, 5)], mats["eye"])

      lid_low = [on_face(dp * 1.02, eye_z + dz - 0.0004, 0.0038) for dp, dz in almond[:4]]
      lid_high = [on_face(dp * 1.08, eye_z + dz + 0.0046, 0.0062) for dp, dz in almond[:4]]
      self.shell(shape, [lid_low, lid_high], 0.0036, mats["lid"])

      bag_top = [on_face(dp, eye_z + dz - 0.0012, 0.0016) for dp, dz in (almond[0], almond[5], almond[4], almond[3])]
      bag_bot = [on_face(dp * 1.04, eye_z + dz - 0.0060, 0.0018) for dp, dz in (almond[0], almond[5], almond[4], almond[3])]
      self.shell(shape, [bag_bot, bag_top], 0.0020, mats["skin_bag"])

      # brow_tilt < 0 lowers inner brow (stern/furrowed); > 0 raises inner brow (worried)
      brow = [
        (-0.19, self.z_at(0.160 + brow_tilt), self.z_at(0.171 + brow_tilt)),
        (-0.05, self.z_at(0.162 + brow_tilt * 0.4), self.z_at(0.173 + brow_tilt * 0.4)),
        (0.10, self.z_at(0.163), self.z_at(0.172)),
        (0.23, self.z_at(0.159), self.z_at(0.166)),
      ]
      self.shell(
        shape,
        [[on_face(dp, lo, 0.0048) for dp, lo, hi in brow],
         [on_face(dp, hi, 0.0080) for dp, lo, hi in brow]],
        0.0060,
        mats["hair"],
      )

      if ears:
        ew = self.ws
        ear_outer = [
          (side * 0.094 * ew, yo + 0.008, self.z_at(0.100)),
          (side * 0.111 * ew, yo + 0.018, self.z_at(0.108)),
          (side * 0.115 * ew, yo + 0.026, self.z_at(0.134)),
          (side * 0.111 * ew, yo + 0.025, self.z_at(0.162)),
          (side * 0.096 * ew, yo + 0.008, self.z_at(0.168)),
          (side * 0.092 * ew, yo + 0.004, self.z_at(0.134)),
        ]
        ear_inner = [(side * 0.086 * ew, p[1] - 0.003, p[2]) for p in ear_outer]
        ne = len(ear_outer)
        efaces = [tuple(range(ne)), tuple(range(2 * ne - 1, ne - 1, -1))]
        for k in range(ne):
          nk = (k + 1) % ne
          efaces.append((k, nk, ne + nk, ne + k))
        shape.add(ear_outer + ear_inner, efaces, mats["skin"])

  def build_lips(self, shape, mats, over_beard=False):
    g_u = 0.0082 if over_beard else 0.0042
    g_m = 0.0072 if over_beard else 0.0034
    g_l = 0.0094 if over_beard else 0.0052
    lip_u = [self.point(self.z_at(0.075) - 0.002 * (abs(a) / 16.0), math.radians(a), g_u) for a in (-16, -8, 0, 8, 16)]
    lip_m = [self.point(self.z_at(0.070), math.radians(a), g_m) for a in (-15, -7, 0, 7, 15)]
    lip_l = [self.point(self.z_at(0.064) + 0.002 * (abs(a) / 14.0), math.radians(a), g_l) for a in (-14, -7, 0, 7, 14)]
    self.shell(shape, [lip_m, lip_u], 0.0045, mats["lip"])
    self.shell(shape, [lip_l, lip_m], 0.0050, mats["lip"])

  def build_beard(self, shape, mats, thickness=1.0, moustache=True):
    angles = [math.radians(a) for a in range(-102, 103, 17)]
    rows = []
    for k in range(7):
      t = k / 6
      row = []
      for phi in angles:
        side_f = abs(phi) / math.radians(102)
        bottom = self.z_at(-0.008 + 0.072 * (side_f ** 1.9))
        top = self.beardline(phi)
        z = bottom + (top - bottom) * t
        chin_full = (0.010 * thickness * max(0.0, math.cos(phi)) ** 1.4 + 0.0035) * (1.0 - 0.55 * side_f)
        taper = math.sin(math.pi * min(1.0, 0.20 + 0.80 * t))
        bulk = -0.002 if k == 0 else (0.0024 if k == 6 else 0.0030 + chin_full * taper)
        row.append(self.point(z, phi, bulk))
      rows.append(row)
    self.shell(shape, rows, 0.013, mats["hair"])

    stubble_angles = [math.radians(a) for a in range(-96, 97, 16)]
    self.shell(
      shape,
      [[self.point(self.beardline(phi) - 0.002, phi, 0.0018) for phi in stubble_angles],
       [self.point(self.beardline(phi) + 0.007, phi, 0.0012) for phi in stubble_angles]],
      0.0020,
      mats["stubble"],
    )
    if moustache:
      mo_top = [self.point(self.z_at(0.090) - 0.010 * (abs(a) / 42.0) ** 1.5, math.radians(a), 0.0065) for a in (-42, -26, -12, 0, 12, 26, 42)]
      mo_bot = [self.point(self.z_at(0.079) - 0.014 * (abs(a) / 46.0) ** 1.3, math.radians(a), 0.0092) for a in (-46, -28, -13, 0, 13, 28, 46)]
      self.shell(shape, [mo_bot, mo_top], 0.0075, mats["hair"])


# --- Reusable limbs, hands & footwear --------------------------------------------------------
def add_hand(shape, wr, kn, tip, th, s, skin_mat, tag=None, side_suffix=None):
  """Sculpted palm + 3 finger groups + thumb with 0.014m wrist overlap (zero seam)."""
  wr, kn, tip, th = Vector(wr), Vector(kn), Vector(tip), Vector(th)
  h_dir = (kn - wr).normalized()
  h_front = Vector((0.0, -1.0, 0.0))
  h_palm = h_dir.cross(h_front).normalized()
  if h_palm.x * s > 0:
    h_palm = -h_palm

  if tag and side_suffix:
    tag("hand" + side_suffix, "fingers" + side_suffix, "lower_arm" + side_suffix)
  shape.tube([
    (wr - h_dir * 0.014, 0.027, 0.019),
    (wr, 0.029, 0.019),
    (wr.lerp(kn, 0.45) + h_palm * 0.002, 0.037, 0.019),
    (kn, 0.041, 0.017),
  ], skin_mat, n=6, side=tuple(h_palm))

  if tag and side_suffix:
    tag("fingers" + side_suffix, "hand" + side_suffix)
  f_len = (tip - kn).length
  for f_off, scale_l, r_w, r_t in ((0.024, 0.94, 0.0105, 0.0085), (0.000, 1.04, 0.0155, 0.0090), (-0.023, 0.82, 0.0095, 0.0075)):
    base_p = kn + h_front * f_off
    mid_p = base_p + h_dir * (f_len * 0.55 * scale_l) + h_palm * 0.008
    end_p = base_p + h_dir * (f_len * scale_l) + h_palm * 0.019
    shape.tube([(base_p, r_w, r_t), (mid_p, r_w * 0.90, r_t * 0.88), (end_p, r_w * 0.68, r_t * 0.72)], skin_mat, n=5, side=tuple(h_palm))

  if tag and side_suffix:
    tag("thumb" + side_suffix, "hand" + side_suffix)
  th_base = wr.lerp(kn, 0.34) + h_front * 0.020 + h_palm * 0.008
  th_mid = th_base.lerp(th, 0.52) + h_palm * 0.005
  shape.tube([(th_base, 0.014, 0.012), (th_mid, 0.011, 0.010), (th, 0.0085, 0.0080)], skin_mat, n=5)


def add_footwear(shape, x, s, shoe_mat, sole_mat, accent_mat, lace_mat=None, boot_height=0.0):
  """Lofted sneaker or work boot grounded cleanly at z=0, toe toward -Y."""
  bh = boot_height
  stations = [
    (0.076, 0.020, 0.088 + bh, 0.042, 0.044),
    (0.025, 0.018, 0.106 + bh, 0.047, 0.050),
    (-0.042, 0.018, 0.092 + bh * 0.4, 0.050, 0.054),
    (-0.115, 0.018, 0.062, 0.052, 0.057),
    (-0.168, 0.020, 0.044, 0.042, 0.047),
    (-0.190, 0.022, 0.034, 0.022, 0.025),
  ]
  shoe_rings, sole_rings = [], []
  for py, zb, zt, wi, wo in stations:
    xi, xo = x - s * wi, x + s * wo
    zm = zb + (zt - zb) * 0.52
    shoe_rings.append([
      (xi * 0.85 + x * 0.15, py, zb), (xo * 0.85 + x * 0.15, py, zb),
      (xo, py, zm), (xo * 0.72 + x * 0.28, py, zt),
      (xi * 0.72 + x * 0.28, py, zt), (xi, py, zm),
    ])
    xsi, xso = x - s * (wi + 0.004), x + s * (wo + 0.004)
    zts = zb + (0.006 if py > -0.15 else 0.010)
    sole_rings.append([(xsi, py, 0.0), (xso, py, 0.0), (xso, py, zts), (xsi, py, zts)])
  shape.loft(shoe_rings, shoe_mat, caps=(True, True))
  shape.loft(sole_rings, sole_mat, caps=(True, True))
  shape.box((x - 0.045, 0.056, 0.026), (x + 0.045, 0.080, 0.082 + bh * 0.5), accent_mat)
  shape.tube([((x, 0.015, 0.104 + bh), 0.048, 0.046), ((x, 0.012, 0.120 + bh), 0.045, 0.044)], accent_mat, n=8, side=(1, 0, 0))
  shape.box((x - 0.026, -0.055, 0.085), (x + 0.026, -0.015, 0.114 + bh * 0.6), accent_mat)
  if lace_mat is not None:
    for ly, lz in ((-0.032, 0.095), (-0.058, 0.084), (-0.084, 0.073)):
      shape.box((x - 0.024, ly - 0.005, lz - 0.004), (x + 0.024, ly + 0.005, lz + 0.004), lace_mat)


# --- Geometry audit --------------------------------------------------------------------------
def audit_scene():
  """Prints triangle counts, bounding box, and grounding check."""
  meshes = [o for o in bpy.data.objects if o.type == "MESH" and not o.hide_render and not o.name.startswith("_")]
  total_tris = 0
  pts = []
  for o in meshes:
    tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
    total_tris += tris
    pts.extend(o.matrix_world @ Vector(c) for c in o.bound_box)
    print(f"AUDIT mesh={o.name} tris={tris}")
  if pts:
    min_z = min(p.z for p in pts)
    max_z = max(p.z for p in pts)
    min_x, max_x = min(p.x for p in pts), max(p.x for p in pts)
    min_y, max_y = min(p.y for p in pts), max(p.y for p in pts)
    print(f"AUDIT total_tris={total_tris} height={max_z - min_z:.3f}m min_z={min_z:.4f} x=[{min_x:.2f},{max_x:.2f}] y=[{min_y:.2f},{max_y:.2f}]")
    if abs(min_z) > 0.015:
      print(f"AUDIT WARNING: feet not grounded at z=0 (min_z={min_z:.4f})")
