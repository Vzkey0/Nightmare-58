# Builds El Padre, the elderly priest of the first chapel.
# Thin, stooped, weathered elder in a worn black cassock with shoulder capelet (pellegrina),
# white clerical collar, waist fascia, faded purple-and-gold liturgical stole, brass/wood
# pectoral cross, receding silver-gray hair, gaunt faceted face and round wire glasses.
# Faces -Y with feet on the origin (+X is the character's left). Flat-shaded low poly.
#   blender --background --python art/characters/build_priest.py
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "props"))

from prop_tools import Shape, linear, material

BLEND_PATH = os.path.join(HERE, "priest.blend")
GLB_PATH = os.path.abspath(os.path.join(HERE, "..", "..", "game", "models", "characters", "priest.glb"))


def reset():
  if bpy.app.background:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return
  for data in (bpy.data.objects, bpy.data.meshes, bpy.data.armatures, bpy.data.materials, bpy.data.actions):
    for item in list(data):
      data.remove(item)


def make_material(name, color, roughness=0.85, metallic=0.0, alpha=1.0):
  mat = material(name, color, roughness=roughness)
  bsdf = mat.node_tree.nodes.get("Principled BSDF")
  bsdf.inputs["Metallic"].default_value = metallic
  if alpha < 1.0:
    bsdf.inputs["Alpha"].default_value = alpha
    bsdf.inputs["IOR"].default_value = 1.48
    bsdf.inputs["Specular IOR Level"].default_value = 0.85
    mat.diffuse_color = linear(color)[:3] + (alpha,)
  return mat


# --- Spine & garment parametric surface ------------------------------------------------------
def spine_y(z):
  """Gentle elderly forward stoop from waist upward (negative Y is forward)."""
  if z <= 0.86:
    return 0.0
  t = min(1.0, (z - 0.86) / 0.56)
  return 0.022 * math.sin(math.pi * t) - 0.056 * (t ** 1.65)


# Cassock profile from hem (z=0.08) to base of neck (z=1.408):
# (z, half_width, front_depth, back_depth, pleat_amp)
CASSOCK_STATIONS = [
  (0.080, 0.312, 0.215, 0.278, 0.032),
  (0.180, 0.296, 0.203, 0.260, 0.028),
  (0.320, 0.272, 0.186, 0.233, 0.023),
  (0.500, 0.238, 0.163, 0.198, 0.016),
  (0.700, 0.196, 0.135, 0.156, 0.009),
  (0.840, 0.162, 0.112, 0.122, 0.004),
  (0.920, 0.145, 0.100, 0.108, 0.001),  # Narrow waist under fascia
  (1.030, 0.152, 0.104, 0.118, 0.000),
  (1.150, 0.166, 0.108, 0.134, 0.000),  # Mid ribcage, subtle stooped upper back
  (1.265, 0.180, 0.106, 0.142, 0.000),  # Upper chest / rounded elderly back
  (1.350, 0.168, 0.094, 0.122, 0.000),  # Narrow sloping shoulders
  (1.408, 0.080, 0.066, 0.072, 0.000),  # Neck base
]


def cassock_params(z):
  if z <= CASSOCK_STATIONS[0][0]:
    return CASSOCK_STATIONS[0][1:]
  for s0, s1 in zip(CASSOCK_STATIONS, CASSOCK_STATIONS[1:]):
    if z <= s1[0]:
      t = (z - s0[0]) / (s1[0] - s0[0])
      return tuple(a + (b - a) * t for a, b in zip(s0[1:], s1[1:]))
  return CASSOCK_STATIONS[-1][1:]


def cassock_point(z, phi, grow=0.0):
  """Point on the cassock surface at height z and angle phi (0 is front -Y, +pi/2 is left +X)."""
  a, f, b, pleat = cassock_params(z)
  s, c = math.sin(phi), math.cos(phi)
  fold = 0.0
  if pleat > 0.0:
    fold = pleat * (
      0.55 * math.cos(5.0 * phi + 0.18)
      + 0.45 * math.cos(3.0 * phi - 0.35)
      + 0.25 * math.sin(7.0 * phi)
    )
    center_calm = 1.0 - 0.72 * math.exp(-((phi / 0.28) ** 2))
    fold *= center_calm
  power = 2.45 if z > 0.85 else 2.2
  px = (a + grow + fold) * math.copysign(abs(s) ** (2.0 / power), s)
  depth = (f if c > 0 else b) + grow + fold * (0.75 if c > 0 else 1.0)
  py = spine_y(z) - depth * math.copysign(abs(c) ** (2.0 / power), c)
  dz = 0.0
  if z < 0.26 and pleat > 0.0:
    dz = 0.010 * math.cos(4.0 * phi + 0.25) * max(0.0, 1.0 - (z - 0.080) / 0.180)
  return (px, py, z + dz)


def solid_shell(shape, rows, thickness, mat_outer, mat_inner=None, mat_edge=None, inward_dir=None):
  """Builds a closed faceted cloth shell from an open grid of rows (r x c)."""
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


# --- Sculpted elderly head (natural proportions: eyes at mid-skull, gentle forward nod) ------
HEAD_CENTER = Vector((0.0, -0.086, 1.592))
HEAD_PITCH = math.radians(8.0)  # Positive rotation around +X nods chin gently forward & down.

# Local head profile around HEAD_CENTER (smooth rounded cranium dome, gaunt cheeks, bony chin)
# (lz, half_width, front, back, y_shift)
HEAD_RINGS = [
  (-0.114, 0.032, 0.056, 0.028, -0.008),  # Bony chin tip
  (-0.094, 0.052, 0.082, 0.044, -0.004),  # Lower jaw
  (-0.064, 0.072, 0.092, 0.068, -0.001),  # Mouth / jaw corner
  (-0.034, 0.082, 0.095, 0.084, 0.001),   # Gaunt sunken cheeks
  (-0.004, 0.091, 0.100, 0.096, 0.002),   # Prominent cheekbones
  (0.018, 0.089, 0.097, 0.103, 0.004),    # Eye line (exact mid-head)
  (0.042, 0.091, 0.103, 0.107, 0.005),    # Brow ridge
  (0.074, 0.087, 0.095, 0.106, 0.008),    # High weathered forehead
  (0.102, 0.076, 0.078, 0.094, 0.011),    # Upper skull curve
  (0.120, 0.054, 0.054, 0.068, 0.012),    # Rounded cranium dome
  (0.130, 0.024, 0.024, 0.030, 0.012),    # Crown apex
]


def head_to_world(local_vec):
  rot = Matrix.Rotation(HEAD_PITCH, 3, "X")
  return HEAD_CENTER + rot @ local_vec


def head_local(lz, phi, grow=0.0):
  """Sculpted gaunt elderly skull/face point in head-local coordinates (phi=0 is front -Y)."""
  for r0, r1 in zip(HEAD_RINGS, HEAD_RINGS[1:]):
    if lz <= r1[0]:
      t = max(0.0, min(1.0, (lz - r0[0]) / (r1[0] - r0[0])))
      break
  else:
    r0, r1, t = HEAD_RINGS[-2], HEAD_RINGS[-1], 1.0
  a, f, b, yc = (u + (v - u) * t for u, v in zip(r0[1:], r1[1:]))

  abs_phi = abs(math.atan2(math.sin(phi), math.cos(phi)))
  s, c = math.sin(phi), math.cos(phi)

  relief = 0.0
  if c > -0.15:
    eye_s = math.exp(-((lz - 0.017) / 0.016) ** 2) * math.exp(-((abs_phi - 0.36) / 0.19) ** 2)
    relief -= 0.0105 * eye_s
    brow_s = math.exp(-((lz - 0.042) / 0.013) ** 2) * math.exp(-((abs_phi) / 0.62) ** 2)
    relief += 0.0068 * brow_s
    cheek_b = math.exp(-((lz + 0.005) / 0.016) ** 2) * math.exp(-((abs_phi - 0.66) / 0.24) ** 2)
    relief += 0.0072 * cheek_b
    hollow = math.exp(-((lz + 0.040) / 0.024) ** 2) * math.exp(-((abs_phi - 0.68) / 0.28) ** 2)
    relief -= 0.0132 * hollow
    temple = math.exp(-((lz - 0.048) / 0.022) ** 2) * math.exp(-((abs_phi - 1.12) / 0.22) ** 2)
    relief -= 0.0050 * temple
    chin = math.exp(-((lz + 0.098) / 0.016) ** 2) * math.exp(-((abs_phi) / 0.34) ** 2)
    relief += 0.0055 * chin
    mouth_r = math.exp(-((lz + 0.062) / 0.011) ** 2) * math.exp(-((abs_phi) / 0.30) ** 2)
    relief -= 0.0040 * mouth_r

  power = 2.45
  px = (a + grow + relief * 0.65) * math.copysign(abs(s) ** (2.0 / power), s)
  depth = (f if c > 0 else b) + grow + relief
  py = yc - depth * math.copysign(abs(c) ** (2.0 / power), c)
  return Vector((px, py, lz))


def head_world(lz, phi, grow=0.0):
  return tuple(head_to_world(head_local(lz, phi, grow)))


# --- Arm joints (A-pose, narrow stooped shoulders) -------------------------------------------
SHOULDER = Vector((0.152, -0.036, 1.320))
ELBOW = Vector((0.312, -0.018, 1.100))
WRIST = Vector((0.456, -0.044, 0.915))


def build_priest():
  M = {
    "cassock": make_material("priest_cassock", (0.102, 0.102, 0.116), roughness=0.88),
    "cassock_dark": make_material("priest_cassock_dark", (0.056, 0.056, 0.065), roughness=0.90),
    "cassock_worn": make_material("priest_cassock_worn", (0.146, 0.134, 0.128), roughness=0.94),
    "sash": make_material("priest_sash", (0.130, 0.095, 0.138), roughness=0.86),
    "collar": make_material("priest_collar", (0.86, 0.84, 0.78), roughness=0.78),
    "stole": make_material("priest_stole", (0.28, 0.15, 0.29), roughness=0.87),
    "stole_dark": make_material("priest_stole_dark", (0.17, 0.09, 0.18), roughness=0.90),
    "gold": make_material("priest_gold", (0.64, 0.50, 0.26), roughness=0.48, metallic=0.52),
    "wood": make_material("priest_wood", (0.24, 0.13, 0.075), roughness=0.74),
    "brass": make_material("priest_brass", (0.58, 0.46, 0.24), roughness=0.36, metallic=0.78),
    "lens": make_material("priest_lens", (0.35, 0.45, 0.52), roughness=0.04, metallic=0.05, alpha=0.07),
    "skin": make_material("priest_skin", (0.71, 0.52, 0.39), roughness=0.82),
    "skin_lid": make_material("priest_skin_lid", (0.54, 0.37, 0.28), roughness=0.86),
    "skin_bag": make_material("priest_skin_bag", (0.62, 0.44, 0.33), roughness=0.85),
    "lip": make_material("priest_lip", (0.55, 0.37, 0.30), roughness=0.82),
    "eye_white": make_material("priest_eye_white", (0.84, 0.80, 0.74), roughness=0.45),
    "eye": make_material("priest_eye", (0.06, 0.04, 0.03), roughness=0.22),
    "hair": make_material("priest_hair", (0.69, 0.69, 0.67), roughness=0.86),
    "hair_dark": make_material("priest_hair_dark", (0.45, 0.45, 0.47), roughness=0.88),
    "shoe": make_material("priest_shoe", (0.14, 0.105, 0.09), roughness=0.66),
    "sole": make_material("priest_sole", (0.075, 0.068, 0.065), roughness=0.92),
  }

  body = Shape()

  # 1. SHOES & LOWER TROUSERS -----------------------------------------------------------------
  for s in (-1, 1):
    x = s * 0.095
    body.tube([
      ((x, 0.008, 0.065), 0.045, 0.047),
      ((x, 0.004, 0.25), 0.056, 0.058),
    ], M["cassock_dark"], n=8, side=(1, 0, 0))
    profile = [(0.065, 0.0), (0.065, 0.072), (0.015, 0.098), (-0.065, 0.082), (-0.150, 0.048), (-0.178, 0.025), (-0.175, 0.0)]
    for half, mat, lift in ((0.048, M["shoe"], 0.012), (0.051, M["sole"], 0.0)):
      outline = [(y, z + lift) for y, z in profile] if lift else [(0.068, 0.0), (0.068, 0.018), (-0.180, 0.018), (-0.180, 0.0)]
      verts = [(x + dx, py, pz) for dx in (-half, half) for py, pz in outline]
      count = len(outline)
      faces = [tuple(range(count))[::-1], tuple(range(count, 2 * count))]
      for k in range(count):
        n = (k + 1) % count
        faces.append((k, n, count + n, count + k))
      body.add(verts, faces, mat)

  # 2. CASSOCK (SOTANA): skirt + torso + inner hem thickness ----------------------------------
  N_CASS = 18
  phis = [math.tau * (k + 0.5) / N_CASS for k in range(N_CASS)]
  cassock_rings = [[cassock_point(st[0], phi) for phi in phis] for st in CASSOCK_STATIONS]

  def cassock_mat(band, side):
    # Clean dusty lower hem band all around, avoiding patchy squares on the back.
    if band == 0:
      return M["cassock_worn"]
    return M["cassock"]

  body.loft(cassock_rings, cassock_mat, caps=(False, True))

  hem_outer = cassock_rings[0]
  hem_inner_bot = [cassock_point(CASSOCK_STATIONS[0][0] + 0.004, phi, grow=-0.018) for phi in phis]
  hem_inner_top = [cassock_point(0.24, phi, grow=-0.030) for phi in phis]
  body.loft([hem_inner_top, hem_inner_bot, hem_outer], M["cassock_dark"], caps=(True, False))

  # Front center button placket & small faceted buttons.
  placket_zs = [0.22, 0.38, 0.55, 0.72, 0.86, 0.98, 1.12, 1.25, 1.36]
  placket_rows = [[cassock_point(z, -0.055, grow=0.005), cassock_point(z, 0.055, grow=0.005)] for z in placket_zs]
  solid_shell(body, placket_rows, 0.005, M["cassock_dark"], inward_dir=lambda p, r, c: Vector((0, 1, 0)))
  for z_btn in (0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 1.03, 1.11, 1.19, 1.27, 1.34):
    p = Vector(cassock_point(z_btn, 0.0, grow=0.008))
    body.box((p.x - 0.006, p.y - 0.0045, p.z - 0.006), (p.x + 0.006, p.y + 0.0035, p.z + 0.006), M["cassock_dark"])

  # 3. WAIST FASCIA (FAJA) + HANGING SASH TAILS ON LEFT HIP -----------------------------------
  fascia_zs = (0.875, 0.902, 0.935, 0.962)
  fascia_grows = (0.010, 0.015, 0.015, 0.009)
  body.loft([[cassock_point(z, phi, grow=g) for phi in phis] for z, g in zip(fascia_zs, fascia_grows)], M["sash"], caps=(True, True))

  knot_phi = math.radians(54)
  knot_c = Vector(cassock_point(0.915, knot_phi, grow=0.022))
  body.box(
    (knot_c.x - 0.026, knot_c.y - 0.020, knot_c.z - 0.028),
    (knot_c.x + 0.026, knot_c.y + 0.020, knot_c.z + 0.028),
    M["sash"],
  )
  for phi_off, z_end, w_rad, extra_g in ((0.0, 0.42, 0.135, 0.022), (0.14, 0.35, 0.125, 0.016)):
    t_rows = []
    for k in range(6):
      t = k / 5
      z = 0.895 + (z_end - 0.895) * t
      width = w_rad * (0.85 + 0.30 * t)
      phi_c = knot_phi + phi_off + 0.06 * t
      g = extra_g + 0.015 * t + 0.005 * math.sin(math.pi * t * 1.5)
      t_rows.append([
        cassock_point(z, phi_c - width * 0.5, grow=g),
        cassock_point(z, phi_c, grow=g + 0.004),
        cassock_point(z, phi_c + width * 0.5, grow=g),
      ])
    solid_shell(
      body, t_rows, 0.008, M["sash"], M["cassock_dark"], M["sash"],
      inward_dir=lambda p, r, c: Vector((-p.x, -p.y, 0)).normalized(),
    )
    f_top = [cassock_point(z_end, knot_phi + phi_off + 0.06 + d, grow=extra_g + 0.016) for d in (-w_rad * 0.54, 0.0, w_rad * 0.54)]
    f_bot = [cassock_point(z_end - 0.028, knot_phi + phi_off + 0.065 + d, grow=extra_g + 0.018) for d in (-w_rad * 0.56, 0.0, w_rad * 0.56)]
    solid_shell(body, [f_bot, f_top], 0.006, M["gold"], M["gold"], M["gold"],
                inward_dir=lambda p, r, c: Vector((-p.x, -p.y, 0)).normalized())

  # 4. SHOULDER CAPELET (PELLEGRINA) ----------------------------------------------------------
  cape_angles = [math.radians(a) for a in range(26, 335, 16)]
  cape_rows = []
  for r in range(6):
    t = r / 5
    row = []
    for phi in cape_angles:
      p_norm = math.atan2(math.sin(phi), math.cos(phi))
      back_factor = max(0.0, -math.cos(p_norm))
      side_factor = abs(math.sin(p_norm))
      front_factor = max(0.0, math.cos(p_norm))
      z_top = 1.404 - 0.010 * front_factor
      z_bot = 1.150 - 0.048 * back_factor + 0.024 * side_factor
      z = z_top + (z_bot - z_top) * t
      fold = 0.015 * (t ** 1.35) * (0.65 * math.cos(6.0 * p_norm) + 0.35 * math.cos(4.0 * p_norm + 0.5))
      front_calm = 1.0 - 0.75 * (front_factor ** 2)
      arm_flare = (0.082 * side_factor ** 1.6) * (t ** 1.15)
      back_flare = (0.044 * back_factor) * (t ** 1.2)
      front_flare = 0.008 * (t ** 1.1)
      grow = 0.010 + arm_flare + back_flare + front_flare + fold * front_calm
      shoulder_arch = 0.022 * math.sin(math.pi * (t ** 0.85)) * (0.35 + 0.65 * side_factor)
      pt = Vector(cassock_point(z, p_norm, grow=grow + shoulder_arch * 0.42))
      pt.z += shoulder_arch * 0.38
      row.append(tuple(pt))
    cape_rows.append(row)

  cape_rows.reverse()
  solid_shell(
    body, cape_rows, 0.009, M["cassock"], M["cassock_dark"], M["cassock_dark"],
    inward_dir=lambda p, r, c: Vector((-p.x, spine_y(p.z) - p.y, -0.25)).normalized(),
  )

  # 5. ROMAN CLERICAL COLLAR (ALZACUELLOS) ----------------------------------------------------
  neck_base_y = spine_y(1.408)
  white_collar = []
  for z, rad in ((1.404, 0.066), (1.446, 0.060)):
    yc = spine_y(z) - 0.005
    white_collar.append([(rad * math.sin(phi), yc - rad * 0.96 * math.cos(phi), z) for phi in phis])
  body.loft(white_collar, M["collar"], caps=(True, True))

  outer_angles = [math.radians(a) for a in range(20, 341, 20)]
  c_rows = []
  for z, rad in ((1.400, 0.073), (1.426, 0.069), (1.450, 0.065)):
    yc = spine_y(z) - 0.005
    c_rows.append([(rad * math.sin(phi), yc - rad * 0.96 * math.cos(phi), z) for phi in outer_angles])
  solid_shell(
    body, c_rows, 0.006, M["cassock_dark"], M["cassock_dark"], M["cassock_dark"],
    inward_dir=lambda p, r, c: Vector((-p.x, neck_base_y - p.y, 0.0)).normalized(),
  )
  for z0, z1 in ((1.400, 1.410), (1.440, 1.450)):
    rim_rows = []
    for z, rad in ((z0, 0.072 if z0 < 1.42 else 0.066), (z1, 0.071 if z0 < 1.42 else 0.065)):
      yc = spine_y(z) - 0.005
      rim_rows.append([(rad * math.sin(math.radians(a)), yc - rad * 0.96 * math.cos(math.radians(a)), z) for a in (-22, -11, 0, 11, 22)])
    solid_shell(body, rim_rows, 0.005, M["cassock_dark"], inward_dir=lambda p, r, c: Vector((0, 1, 0)))

  # 6. CONTINUOUS SEAMLESS LITURGICAL STOLE (SMOOTH TWIST-FREE SHOULDER WRAP) -----------------
  def front_stole_center(z, xc, clear):
    phi_est = math.atan2(xc, 0.13)
    base = Vector(cassock_point(z, phi_est, grow=clear))
    return Vector((xc, base.y, z))

  front_stations = [
    (0.550, 0.116, 0.030, 0.039),
    (0.605, 0.112, 0.030, 0.037),
    (0.760, 0.105, 0.032, 0.033),
    (0.920, 0.100, 0.034, 0.029),
    (1.060, 0.097, 0.032, 0.027),
    (1.165, 0.096, 0.056, 0.026),
    (1.265, 0.094, 0.064, 0.025),
    (1.350, 0.088, 0.056, 0.023),
  ]

  # Build smooth centerline + consistent outward normal + parallel-transported ribbon side vector!
  yc_neck = spine_y(1.412) - 0.004
  path_pts = []
  path_outs = []
  path_hws = []

  # Left front going UP
  for z, ax, clr, hw in front_stations:
    path_pts.append(front_stole_center(z, ax, clr))
    path_outs.append(Vector((0.08, -1.0, 0.05)).normalized())
    path_hws.append(hw)

  # Smoothly arch over left shoulder, around back of neck, and over right shoulder!
  # Use radial outward-and-up normal around the neck so the ribbon lies FLAT over the shoulders.
  arc_specs = [
    (36, 0.098, 1.404, 0.021),
    (68, 0.094, 1.414, 0.020),
    (108, 0.091, 1.412, 0.019),
    (145, 0.091, 1.409, 0.019),
    (180, 0.092, 1.407, 0.019),
    (215, 0.091, 1.409, 0.019),
    (252, 0.091, 1.412, 0.019),
    (292, 0.094, 1.414, 0.020),
    (324, 0.098, 1.404, 0.021),
  ]
  for deg, rad, z_arc, hw in arc_specs:
    phi = math.radians(deg)
    path_pts.append(Vector((rad * math.sin(phi), yc_neck - rad * math.cos(phi), z_arc)))
    # Smoothly tilts from forward-up on the shoulders to back-up behind the collar.
    path_outs.append(Vector((math.sin(phi) * 0.55, -math.cos(phi) * 0.75, 0.75)).normalized())
    path_hws.append(hw)

  # Right front going DOWN
  for z, ax, clr, hw in reversed(front_stations):
    path_pts.append(front_stole_center(z, -ax, clr))
    path_outs.append(Vector((-0.08, -1.0, 0.05)).normalized())
    path_hws.append(hw)

  # Compute twist-free ribbon side vector via tangent x out_v at every station!
  u_stops = (-1.0, -0.74, 0.0, 0.74, 1.0)
  st_outer, st_inner = [], []
  n_pts = len(path_pts)
  for i in range(n_pts):
    tang = (path_pts[min(i + 1, n_pts - 1)] - path_pts[max(i - 1, 0)]).normalized()
    out_v = path_outs[i]
    # Make out_v perpendicular to tangent so the ribbon thickness is uniform.
    out_v = (out_v - tang * out_v.dot(tang)).normalized()
    side_v = tang.cross(out_v).normalized()
    hw = path_hws[i]
    c_pt = path_pts[i]
    o_row, i_row = [], []
    for u in u_stops:
      p = c_pt + side_v * (u * hw)
      o_row.append(p + out_v * 0.0035)
      i_row.append(p - out_v * 0.0045)
    st_outer.append(o_row)
    st_inner.append(i_row)

  rc, cc = len(st_outer), len(u_stops)
  s_verts = [tuple(p) for row in st_outer for p in row] + [tuple(p) for row in st_inner for p in row]
  s_base = rc * cc
  s_faces, s_mats = [], []
  for r in range(rc - 1):
    is_end_band = (r == 0) or (r == rc - 2)
    for c in range(cc - 1):
      a, b = r * cc + c, r * cc + c + 1
      s_faces.append((a, b, b + cc, a + cc))
      is_border = (c in (0, cc - 2)) or is_end_band
      s_mats.append(M["gold"] if is_border else M["stole"])
      s_faces.append((s_base + a + cc, s_base + b + cc, s_base + b, s_base + a))
      s_mats.append(M["stole_dark"])
  for r in range(rc - 1):
    for c in (0, cc - 1):
      a, b = r * cc + c, (r + 1) * cc + c
      s_faces.append((a, b, s_base + b, s_base + a) if c else (b, a, s_base + a, s_base + b))
      s_mats.append(M["gold"])
  for r in (0, rc - 1):
    for c in range(cc - 1):
      a, b = r * cc + c, r * cc + c + 1
      s_faces.append((b, a, s_base + a, s_base + b) if r == 0 else (a, b, s_base + b, s_base + a))
      s_mats.append(M["gold"])
  body.add(s_verts, s_faces, s_mats)

  # Raised gold Latin cross & fringe tabs on each front stole end.
  for s in (-1, 1):
    c_anchor = front_stole_center(0.665, s * 0.110, 0.032)
    body.box((c_anchor.x - 0.0045, c_anchor.y - 0.007, c_anchor.z - 0.028),
             (c_anchor.x + 0.0045, c_anchor.y - 0.001, c_anchor.z + 0.024), M["gold"])
    body.box((c_anchor.x - 0.017, c_anchor.y - 0.007, c_anchor.z + 0.003),
             (c_anchor.x + 0.017, c_anchor.y - 0.001, c_anchor.z + 0.012), M["gold"])
    f_anchor = front_stole_center(0.550, s * 0.116, 0.030)
    for k in range(5):
      fx = -0.033 + 0.066 * (k / 4)
      body.box((f_anchor.x + fx - 0.005, f_anchor.y - 0.003, 0.518),
               (f_anchor.x + fx + 0.005, f_anchor.y + 0.003, 0.551), M["gold"])

  # 7. PECTORAL CROSS (CRUZ PECTORAL DE MADERA Y LATON) ---------------------------------------
  p_top_l = Vector((0.034, spine_y(1.402) - 0.072, 1.402))
  p_top_r = Vector((-0.034, spine_y(1.402) - 0.072, 1.402))
  p_mid_l = Vector((0.024, cassock_point(1.31, 0.18, grow=0.024)[1], 1.31))
  p_mid_r = Vector((-0.024, cassock_point(1.31, -0.18, grow=0.024)[1], 1.31))
  p_bail = Vector((0.0, cassock_point(1.235, 0.0, grow=0.024)[1], 1.235))
  body.tube([(p_top_l, 0.0026, 0.0026), (p_mid_l, 0.0026, 0.0026), (p_bail, 0.0026, 0.0026),
             (p_mid_r, 0.0026, 0.0026), (p_top_r, 0.0026, 0.0026)], M["brass"], n=4)

  cross_y_top = cassock_point(1.230, 0.0, grow=0.022)[1]
  cross_y_bot = cassock_point(1.125, 0.0, grow=0.024)[1]
  cross_tilt = math.atan2(cross_y_bot - cross_y_top, 1.230 - 1.125)
  cross_at = Matrix.Translation((0.0, (cross_y_top + cross_y_bot) * 0.5, 1.182)) @ Matrix.Rotation(-cross_tilt, 4, "X")
  body.box((-0.011, -0.003, -0.056), (0.011, 0.006, 0.048), M["brass"], at=cross_at)
  body.box((-0.036, -0.003, 0.007), (0.036, 0.006, 0.027), M["brass"], at=cross_at)
  body.box((-0.0075, -0.007, -0.051), (0.0075, 0.002, 0.043), M["wood"], at=cross_at)
  body.box((-0.031, -0.007, 0.0105), (0.031, 0.002, 0.0235), M["wood"], at=cross_at)
  body.box((-0.006, -0.0095, 0.011), (0.006, -0.005, 0.023), M["gold"], at=cross_at)
  body.box((-0.005, -0.004, 0.046), (0.005, 0.005, 0.057), M["brass"], at=cross_at)

  # 8. SLEEVES, CUFFS & RELAXED LOW-POLY HANDS (A-POSE) ---------------------------------------
  for s in (-1, 1):
    sh = Vector((s * SHOULDER.x, SHOULDER.y, SHOULDER.z))
    el = Vector((s * ELBOW.x, ELBOW.y, ELBOW.z))
    wr = Vector((s * WRIST.x, WRIST.y, WRIST.z))
    arm_dir = (wr - el).normalized()
    up_arm = (el - sh).normalized()

    body.tube([
      (sh - up_arm * 0.02, 0.066, 0.062),
      (sh.lerp(el, 0.45), 0.062, 0.058),
      (el, 0.060, 0.054),
      (el.lerp(wr, 0.55), 0.055, 0.050),
      (wr - arm_dir * 0.055, 0.056, 0.052),
      (wr - arm_dir * 0.015, 0.052, 0.048),
    ], M["cassock"], n=8)
    body.tube([
      (wr - arm_dir * 0.058, 0.059, 0.055),
      (wr - arm_dir * 0.018, 0.057, 0.053),
    ], M["cassock_worn"], n=8)
    body.tube([
      (wr - arm_dir * 0.020, 0.038, 0.034),
      (wr - arm_dir * 0.002, 0.034, 0.030),
    ], M["collar"], n=8)

    hand_fwd = arm_dir
    palm_in = Vector((-s * 0.42, -0.85, -0.32)).normalized()
    palm_side = hand_fwd.cross(palm_in).normalized()
    palm_in = palm_side.cross(hand_fwd).normalized()

    p_wr = wr - hand_fwd * 0.008
    p_kn = wr + hand_fwd * 0.066
    p_mid = p_kn + hand_fwd * 0.036 + palm_in * 0.011
    p_tip = p_mid + hand_fwd * 0.028 + palm_in * 0.018
    body.tube([
      (p_wr, 0.024, 0.017),
      (wr + hand_fwd * 0.022, 0.029, 0.016),
      (p_kn, 0.035, 0.015),
      (p_mid, 0.033, 0.012),
      (p_tip, 0.022, 0.008),
    ], M["skin"], n=6, side=palm_side)

    th_base = wr + hand_fwd * 0.024 - palm_side * (s * 0.024) + palm_in * 0.006
    th_mid = th_base + hand_fwd * 0.026 - palm_side * (s * 0.018) + palm_in * 0.016
    th_tip = th_mid + hand_fwd * 0.022 - palm_side * (s * 0.006) + palm_in * 0.016
    body.tube([
      (th_base, 0.012, 0.010),
      (th_mid, 0.0095, 0.0085),
      (th_tip, 0.0068, 0.0060),
    ], M["skin"], n=4)

  # 9. WEATHERED STOOPED NECK & SCULPTED GAUNT ELDERLY HEAD -----------------------------------
  body.tube([
    ((0.0, spine_y(1.408) - 0.004, 1.408), 0.056, 0.052),
    ((0.0, spine_y(1.408) - 0.018, 1.455), 0.048, 0.049),
    ((0.0, -0.078, 1.515), 0.047, 0.049),
  ], M["skin"], n=8)

  N_HEAD = 18
  h_phis = [math.tau * (k + 0.5) / N_HEAD for k in range(N_HEAD)]
  h_rings = [[head_world(row[0], phi) for phi in h_phis] for row in HEAD_RINGS]
  body.loft(h_rings, M["skin"], caps=(True, True))

  # Aquiline elderly nose aligned cleanly with the mid-head eye line.
  nose_local = [
    (0.0, -0.096, 0.038),
    (-0.0085, -0.106, 0.020),
    (0.0085, -0.106, 0.020),
    (0.0, -0.122, 0.010),
    (0.0, -0.132, -0.018),
    (-0.019, -0.105, -0.022),
    (0.019, -0.105, -0.022),
    (0.0, -0.113, -0.031),
    (-0.016, -0.095, 0.000),
    (0.016, -0.095, 0.000),
    (-0.010, -0.120, -0.026),
    (0.010, -0.120, -0.026),
  ]
  nose_verts = [tuple(head_to_world(Vector(p))) for p in nose_local]
  nose_faces = [
    (0, 1, 3), (0, 3, 2),
    (1, 3, 4), (2, 4, 3),
    (1, 8, 5), (1, 5, 10, 4),
    (2, 4, 11, 6), (2, 6, 9),
    (4, 10, 7), (4, 7, 11),
    (10, 5, 7), (11, 7, 6),
  ]
  body.add(nose_verts, nose_faces, M["skin"])

  # Expressive, clear tired eyes, sleek eyelids, subtle lower eye crease, silver brows & ears.
  for side in (-1, 1):
    def on_face(dphi, lz, grow):
      return head_world(lz, side * (0.36 + dphi), grow)

    # Larger, clearer almond eye so his gentle gaze reads cleanly through the round glasses!
    almond = [(-0.125, 0.0), (-0.06, 0.0072), (0.05, 0.0076), (0.12, -0.0005), (0.05, -0.0062), (-0.055, -0.0060)]
    body.add([on_face(dp, 0.016 + dz, 0.0022) for dp, dz in almond], [(0, 1, 2, 3, 4, 5)], M["eye_white"])
    body.add([on_face(dp * 0.56 - 0.012, 0.0162 + dz * 0.94, 0.0038) for dp, dz in almond], [(0, 1, 2, 3, 4, 5)], M["eye"])

    # Sleek tired upper eyelid hugging the top arc of the eye.
    lid_lo = [on_face(dp, 0.0175 + dz - 0.0012 * (dp + 0.1), 0.0042) for dp, dz in almond[:4]]
    lid_hi = [on_face(dp * 1.06, 0.0220 + dz - 0.0018 * (dp + 0.1), 0.0064) for dp, dz in almond[:4]]
    solid_shell(body, [lid_lo, lid_hi], 0.003, M["skin_lid"], inward_dir=lambda p, r, c: Vector((0, 1, 0)))

    # Soft, subtle under-eye shadow line (gentle age fatigue, never heavy bars).
    bag_hi = [on_face(dp * 0.85, 0.0095 + dz * 0.45, 0.0016) for dp, dz in almond[3:][::-1] + almond[:1]]
    bag_lo = [on_face(dp * 0.92, 0.0060 + dz * 0.35, 0.0022) for dp, dz in almond[3:][::-1] + almond[:1]]
    solid_shell(body, [bag_lo, bag_hi], 0.002, M["skin_bag"], inward_dir=lambda p, r, c: Vector((0, 1, 0)))

    # Bushy, compassionate silver-gray eyebrows clearly framed above the round glasses.
    brow_pts = [
      (-0.18, 0.038, 0.048),
      (-0.04, 0.040, 0.050),
      (0.09, 0.037, 0.046),
      (0.22, 0.031, 0.038),
    ]
    solid_shell(
      body,
      [[on_face(dp, lo, 0.005) for dp, lo, hi in brow_pts], [on_face(dp, hi, 0.009) for dp, lo, hi in brow_pts]],
      0.007, M["hair"], M["hair_dark"], M["hair_dark"],
      inward_dir=lambda p, r, c: Vector((0, 1, 0)),
    )

    # Weathered elderly ear.
    ear_out = [
      (side * 0.091, 0.008, -0.034),
      (side * 0.104, 0.014, -0.024),
      (side * 0.112, 0.024, 0.006),
      (side * 0.108, 0.024, 0.036),
      (side * 0.090, 0.008, 0.038),
    ]
    ear_in = [(side * 0.083, py - 0.004, pz) for _, py, pz in ear_out]
    ev = [tuple(head_to_world(Vector(p))) for p in ear_out + ear_in]
    ec = len(ear_out)
    ef = [tuple(range(ec)), tuple(range(2 * ec - 1, ec - 1, -1))]
    for k in range(ec):
      kn = (k + 1) % ec
      ef.append((k, kn, ec + kn, ec + k))
    body.add(ev, ef, M["skin"])

  # Refined thin somber mouth (narrower and subtler, resting cleanly in the lower face plane).
  mouth_angles = (-17, -8, 0, 8, 17)
  m_up = [head_world(-0.057 - 0.0025 * (abs(a) / 17) ** 1.5, math.radians(a), 0.0018) for a in mouth_angles]
  m_mid = [head_world(-0.060 - 0.0030 * (abs(a) / 17) ** 1.5, math.radians(a), 0.0002) for a in mouth_angles]
  m_lo = [head_world(-0.063 - 0.0020 * (abs(a) / 17) ** 1.5, math.radians(a), 0.0018) for a in mouth_angles]
  solid_shell(body, [m_mid, m_up], 0.0025, M["lip"], inward_dir=lambda p, r, c: Vector((0, 1, 0)))
  solid_shell(body, [m_lo, m_mid], 0.0025, M["lip"], inward_dir=lambda p, r, c: Vector((0, 1, 0)))

  # 10. SLEEK RECEDING SILVER-GRAY HAIR (NATURAL TAPERED TEMPLES & BALDING CROWN) -------------
  hair_angles = [math.radians(a) for a in range(58, 303, 15)]
  hair_rows = []
  H_STEPS = 5
  for k in range(H_STEPS + 1):
    t = k / H_STEPS
    row = []
    for phi in hair_angles:
      p_norm = math.atan2(math.sin(phi), math.cos(phi))
      abs_p = abs(p_norm)
      backness = max(0.0, (abs_p - math.radians(58)) / (math.pi - math.radians(58)))
      # Tapered sideburn that narrows smoothly toward the front instead of ending in a blunt block.
      front_taper = min(1.0, (abs_p - math.radians(56)) / math.radians(24))
      ear_lift = 0.032 * math.exp(-((abs_p - math.radians(95)) / 0.22) ** 2)
      low_z = (-0.008 - 0.016 * front_taper) - 0.050 * (backness ** 1.15) + ear_lift
      high_z = (0.028 + 0.018 * front_taper) + 0.048 * math.sin(math.pi * 0.5 * backness) + 0.004 * math.cos(7.0 * p_norm)
      lz = low_z + (high_z - low_z) * t
      bulge = (0.0025 + 0.0105 * math.sin(math.pi * (0.12 + 0.76 * t))) * (0.45 + 0.55 * backness) * (0.35 + 0.65 * front_taper)
      tuft_wave = 0.0025 * math.sin(9.0 * p_norm + k * 0.7) * math.sin(math.pi * t) * backness
      row.append(head_world(lz, p_norm, bulge + tuft_wave))
    hair_rows.append(row)

  rc, cc = len(hair_rows), len(hair_rows[0])
  h_out = [[Vector(p) for p in r] for r in hair_rows]
  h_in = [[p + (HEAD_CENTER - p).normalized() * 0.011 for p in r] for r in h_out]
  h_verts = [tuple(p) for r in h_out for p in r] + [tuple(p) for r in h_in for p in r]
  h_base = rc * cc
  h_faces, h_mats = [], []
  for r in range(rc - 1):
    for c in range(cc - 1):
      a, b = r * cc + c, r * cc + c + 1
      h_faces.append((a, b, b + cc, a + cc))
      h_mats.append(M["hair_dark"] if r == 0 else M["hair"])
      h_faces.append((h_base + a + cc, h_base + b + cc, h_base + b, h_base + a))
      h_mats.append(M["hair_dark"])
  for r in range(rc - 1):
    for c in (0, cc - 1):
      a, b = r * cc + c, (r + 1) * cc + c
      h_faces.append((a, b, h_base + b, h_base + a) if c else (b, a, h_base + a, h_base + b))
      h_mats.append(M["hair"])
  for r in (0, rc - 1):
    for c in range(cc - 1):
      a, b = r * cc + c, r * cc + c + 1
      h_faces.append((b, a, h_base + a, h_base + b) if r == 0 else (a, b, h_base + b, h_base + a))
      h_mats.append(M["hair_dark"] if r == 0 else M["hair"])
  body.add(h_verts, h_faces, h_mats)

  # 11. SIMPLE ROUND WIRE GLASSES -------------------------------------------------------------
  glass_y = -0.119
  glass_z = 0.015
  lens_r = 0.0205
  eye_x = 0.0355
  N_RIM = 12

  for side in (-1, 1):
    yaw = side * math.radians(6.0)
    cy, sy = math.cos(yaw), math.sin(yaw)

    def rim_pt(theta, r_val, dy=0.0):
      rx = r_val * math.cos(theta)
      rz = r_val * math.sin(theta)
      lx = side * eye_x + rx * cy
      ly = glass_y + dy + rx * sy
      lz = glass_z + rz
      return head_to_world(Vector((lx, ly, lz)))

    rim_loop = [rim_pt(math.tau * k / N_RIM, lens_r) for k in range(N_RIM)]
    ring_verts, ring_faces = [], []
    tube_r = 0.0020
    c_center = head_to_world(Vector((side * eye_x, glass_y, glass_z)))
    normal_axis = (head_to_world(Vector((side * eye_x, glass_y - 0.1, glass_z))) - c_center).normalized()
    for k in range(N_RIM):
      p = rim_loop[k]
      radial = (p - c_center).normalized()
      for m in range(4):
        ang = math.pi * 0.25 + math.tau * m / 4
        ring_verts.append(tuple(p + (radial * math.cos(ang) + normal_axis * math.sin(ang)) * tube_r))
    for k in range(N_RIM):
      kn = (k + 1) % N_RIM
      for m in range(4):
        mn = (m + 1) % 4
        ring_faces.append((k * 4 + m, kn * 4 + m, kn * 4 + mn, k * 4 + mn))
    body.add(ring_verts, ring_faces, M["brass"])

    lens_front = [tuple(rim_pt(math.tau * k / N_RIM, lens_r - 0.0012, dy=-0.0005)) for k in range(N_RIM)]
    lens_back = [tuple(rim_pt(math.tau * k / N_RIM, lens_r - 0.0012, dy=0.0005)) for k in range(N_RIM)]
    body.add(lens_front + lens_back, [tuple(range(N_RIM)), tuple(range(2 * N_RIM - 1, N_RIM - 1, -1))], M["lens"])

    lug = head_to_world(Vector((side * (eye_x + lens_r * cy + 0.003), glass_y + lens_r * sy + 0.002, glass_z + 0.004)))
    temple_mid = head_to_world(Vector((side * 0.090, -0.045, 0.026)))
    ear_top = head_to_world(Vector((side * 0.095, 0.012, 0.039)))
    ear_hook = head_to_world(Vector((side * 0.094, 0.030, 0.018)))
    body.tube([
      (lug, 0.0020, 0.0016),
      (temple_mid, 0.0018, 0.0015),
      (ear_top, 0.0018, 0.0015),
      (ear_hook, 0.0015, 0.0013),
    ], M["brass"], n=4)

  br_l = head_to_world(Vector((eye_x - lens_r * 0.96, glass_y + 0.001, glass_z + 0.004)))
  br_c = head_to_world(Vector((0.0, glass_y - 0.006, glass_z + 0.011)))
  br_r = head_to_world(Vector((-(eye_x - lens_r * 0.96), glass_y + 0.001, glass_z + 0.004)))
  body.tube([(br_l, 0.0018, 0.0016), (br_c, 0.0019, 0.0016), (br_r, 0.0018, 0.0016)], M["brass"], n=4)

  obj = body.finish("priest")
  return obj


def export_glb(obj):
  os.makedirs(os.path.dirname(GLB_PATH), exist_ok=True)
  for other in bpy.data.objects:
    other.hide_set(other is not obj)
  bpy.ops.export_scene.gltf(filepath=GLB_PATH, export_format="GLB", use_visible=True)
  for other in bpy.data.objects:
    other.hide_set(False)
  print("Exported", GLB_PATH)


def main():
  reset()
  obj = build_priest()
  bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
  print("Saved", BLEND_PATH)
  export_glb(obj)


if __name__ == "__main__":
  main()
