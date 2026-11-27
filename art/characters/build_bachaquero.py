# Builds El Bachaquero, the Caracas black-market street merchant of Nightmare 58.
# Stocky, pot-bellied ~45-year-old Venezuelan street hustler in a worn multi-pocket olive utility
# vest over an off-white tee, dark jeans, old sneakers, worn red-terracotta baseball cap, dark
# sunglasses, thick mustache & goatee, gold chain & watch, crossbody chest koala (fanny pack)
# for lochas, and a bulky merchant backpack with grease tins, bottles, and a rolled tarp peeking out.
# Faces -Y with feet grounded at z=0 (+X is the character's left). Flat-shaded low poly.
#   blender --background --python art/characters/build_bachaquero.py
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
  sys.path.insert(0, HERE)
PROPS_DIR = os.path.abspath(os.path.join(HERE, "..", "props"))
if PROPS_DIR not in sys.path:
  sys.path.insert(0, PROPS_DIR)

from char_kit import (  # noqa: E402
  HeadBuilder,
  add_footwear,
  add_hand,
  audit_scene,
  face_materials,
  make_material,
  ring,
  solid_shell,
)
from prop_tools import Shape  # noqa: E402

BLEND_PATH = os.path.join(HERE, "bachaquero.blend")
GLB_PATH = os.path.abspath(os.path.join(HERE, "..", "..", "game", "models", "characters", "bachaquero.glb"))


def reset():
  if bpy.app.background:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return
  for data in (bpy.data.objects, bpy.data.meshes, bpy.data.armatures, bpy.data.materials, bpy.data.actions):
    for item in list(data):
      data.remove(item)


def build_materials():
  M = face_materials(
    "bachaquero",
    skin=(0.66, 0.45, 0.31),
    hair=(0.11, 0.085, 0.07),
    eye=(0.055, 0.036, 0.025),
  )
  M.update({
    "shirt": make_material("bachaquero_shirt", (0.78, 0.73, 0.63), roughness=0.90),
    "shirt_dark": make_material("bachaquero_shirt_dark", (0.61, 0.56, 0.47), roughness=0.90),
    "vest": make_material("bachaquero_vest", (0.24, 0.27, 0.17), roughness=0.88),
    "vest_dark": make_material("bachaquero_vest_dark", (0.16, 0.19, 0.11), roughness=0.90),
    "vest_inner": make_material("bachaquero_vest_inner", (0.12, 0.14, 0.09), roughness=0.92),
    "jeans": make_material("bachaquero_jeans", (0.14, 0.19, 0.29), roughness=0.88),
    "jeans_dark": make_material("bachaquero_jeans_dark", (0.10, 0.14, 0.22), roughness=0.90),
    "leather": make_material("bachaquero_leather", (0.16, 0.10, 0.06), roughness=0.76),
    "gold": make_material("bachaquero_gold", (0.80, 0.63, 0.18), roughness=0.28, metallic=0.85),
    "brass": make_material("bachaquero_brass", (0.66, 0.52, 0.20), roughness=0.38, metallic=0.72),
    "cap": make_material("bachaquero_cap", (0.54, 0.17, 0.13), roughness=0.86),
    "cap_dark": make_material("bachaquero_cap_dark", (0.36, 0.11, 0.09), roughness=0.88),
    "mustard": make_material("bachaquero_mustard", (0.76, 0.56, 0.15), roughness=0.84),
    "mustard_dark": make_material("bachaquero_mustard_dark", (0.58, 0.42, 0.11), roughness=0.88),
    "glasses_frame": make_material("bachaquero_glasses_frame", (0.09, 0.09, 0.10), roughness=0.36, metallic=0.25),
    "glasses_lens": make_material("bachaquero_glasses_lens", (0.025, 0.030, 0.038), roughness=0.16, metallic=0.18),
    "koala": make_material("bachaquero_koala", (0.10, 0.10, 0.11), roughness=0.80),
    "koala_strap": make_material("bachaquero_koala_strap", (0.15, 0.15, 0.16), roughness=0.86),
    "pack": make_material("bachaquero_pack", (0.38, 0.29, 0.19), roughness=0.88),
    "pack_dark": make_material("bachaquero_pack_dark", (0.25, 0.19, 0.12), roughness=0.90),
    "shoe": make_material("bachaquero_shoe", (0.56, 0.54, 0.50), roughness=0.84),
    "sole": make_material("bachaquero_sole", (0.18, 0.16, 0.14), roughness=0.92),
    "lace": make_material("bachaquero_lace", (0.74, 0.70, 0.62), roughness=0.88),
    "grease_fire": make_material("bachaquero_grease_fire", (0.82, 0.36, 0.08), roughness=0.45, metallic=0.20),
    "grease_ice": make_material("bachaquero_grease_ice", (0.20, 0.62, 0.76), roughness=0.45, metallic=0.20),
    "bottle": make_material("bachaquero_bottle", (0.46, 0.23, 0.06), roughness=0.24, metallic=0.05),
    "tin_lid": make_material("bachaquero_tin_lid", (0.68, 0.68, 0.66), roughness=0.36, metallic=0.78),
  })
  return M


# --- Parametric torso surface (stocky, broad-shouldered, beer belly) -------------------------
# (z, half_width, front_depth, back_depth, center_y)
TORSO_STATIONS = [
  (0.878, 0.198, 0.156, 0.136, 0.002),  # Tucked cleanly inside belt
  (0.920, 0.214, 0.194, 0.140, -0.002),  # Lower belly overhang
  (1.000, 0.226, 0.232, 0.138, -0.006),  # Peak beer belly
  (1.085, 0.224, 0.222, 0.140, -0.004),  # Upper belly
  (1.170, 0.224, 0.192, 0.146, 0.000),  # Lower ribcage
  (1.260, 0.236, 0.174, 0.150, 0.004),  # Broad chest
  (1.345, 0.242, 0.154, 0.144, 0.007),  # Shoulder line
  (1.398, 0.166, 0.110, 0.112, 0.005),  # Trapezius taper
  (1.428, 0.088, 0.078, 0.080, 0.000),  # Snug collar rim
]


def torso_params(z):
  if z <= TORSO_STATIONS[0][0]:
    return TORSO_STATIONS[0][1:]
  for s0, s1 in zip(TORSO_STATIONS, TORSO_STATIONS[1:]):
    if z <= s1[0]:
      t = (z - s0[0]) / max(1e-6, s1[0] - s0[0])
      return tuple(u + (v - u) * t for u, v in zip(s0[1:], s1[1:]))
  return TORSO_STATIONS[-1][1:]


def torso_point(z, phi, grow=0.0):
  """Point on torso surface: phi=0 is front (-Y), +pi/2 is left (+X)."""
  a, f, b, yc = torso_params(z)
  s, c = math.sin(phi), math.cos(phi)
  power = 2.45
  px = (a + grow) * math.copysign(abs(s) ** (2.0 / power), s)
  depth = (f if c > 0 else b) + grow
  py = yc - depth * math.copysign(abs(c) ** (2.0 / power), c)
  return (px, py, z)


def add_angled_box(shape, center, x_axis, y_axis, z_axis, hx, hy, hz, mat):
  """Oriented box centered at `center` with local orthonormal axes and half-extents."""
  c = Vector(center)
  xa, ya, za = Vector(x_axis).normalized(), Vector(y_axis).normalized(), Vector(z_axis).normalized()
  corners = []
  for sx in (-1, 1):
    for sy in (-1, 1):
      for sz in (-1, 1):
        corners.append(tuple(c + xa * (sx * hx) + ya * (sy * hy) + za * (sz * hz)))
  faces = [
    (0, 2, 3, 1),  # -x
    (4, 5, 7, 6),  # +x
    (0, 1, 5, 4),  # -y
    (2, 6, 7, 3),  # +y
    (0, 4, 6, 2),  # -z
    (1, 3, 7, 5),  # +z
  ]
  shape.add(corners, faces, mat)


def build_head_and_accessories(body, M):
  head = HeadBuilder(
    base_z=1.488,
    y_offset=-0.014,
    width_scale=1.08,
    depth_scale=1.04,
    height_scale=0.98,
    cheek_hollow=0.0018,  # Fuller middle-aged cheeks
    brow_strength=0.0072,
    chin_strength=0.0065,
    jaw_width=1.09,  # Broad sturdy jaw
  )
  head.build_skull_and_face(body, M, n_ring=18, brow_tilt=-0.0022, nose_scale=1.12, ears=True)
  head.build_lips(body, M, over_beard=True)

  # Subtle double-chin / neck-jaw fullness
  jaw_rings = [
    ring(1.462, 0.072, 0.068, 0.068, y=-0.006, n=12, power=2.2),
    ring(1.498, 0.074, 0.078, 0.066, y=-0.012, n=12, power=2.2),
  ]
  body.loft(jaw_rings, M["skin"], caps=(True, True))

  # Thick mustache + goatee (barba de candado)
  # Mustache arching cleanly over upper lip down to mouth corners
  mo_angles = (-44, -30, -16, 0, 16, 30, 44)
  mo_top = [head.point(head.z_at(0.094) - 0.012 * (abs(a) / 44.0) ** 1.5, math.radians(a), 0.0075) for a in mo_angles]
  mo_bot = [head.point(head.z_at(0.080) - 0.017 * (abs(a) / 44.0) ** 1.25, math.radians(a), 0.0105) for a in mo_angles]
  head.shell(body, [mo_bot, mo_top], 0.0085, M["hair"])

  # Goatee / candado around chin and mouth sides
  go_angles = [math.radians(a) for a in (-42, -28, -14, 0, 14, 28, 42)]
  go_rows = []
  for k in range(5):
    t = k / 4.0
    row = []
    for phi in go_angles:
      side_f = abs(phi) / math.radians(42)
      z_bot = head.z_at(-0.007 + 0.022 * (side_f ** 1.6))
      z_top = head.z_at(0.056 + 0.018 * (side_f ** 1.4))
      z = z_bot + (z_top - z_bot) * t
      bulk = 0.0035 + 0.0095 * math.sin(math.pi * (0.18 + 0.72 * t)) * (1.0 - 0.35 * side_f)
      row.append(head.point(z, phi, bulk))
    go_rows.append(row)
  head.shell(body, go_rows, 0.011, M["hair"])

  # Soul patch / chin-to-mustache side connectors
  for s in (-1, 1):
    side_bar_in = [head.point(head.z_at(z), s * math.radians(a), 0.0075) for z, a in ((0.054, 28), (0.068, 34), (0.080, 36))]
    side_bar_out = [head.point(head.z_at(z), s * math.radians(a), 0.0075) for z, a in ((0.054, 42), (0.068, 46), (0.080, 44))]
    head.shell(body, [side_bar_in, side_bar_out] if s > 0 else [side_bar_out, side_bar_in], 0.0075, M["hair"])

  # Cheek & jaw stubble for weathered 45yo look
  st_angles = [math.radians(a) for a in range(-96, 97, 16)]
  head.shell(
    body,
    [
      [head.point(head.z_at(0.028 + 0.052 * (abs(phi) / 1.7) ** 1.5), phi, 0.0018) for phi in st_angles],
      [head.point(head.z_at(0.072 + 0.048 * (abs(phi) / 1.7) ** 1.4), phi, 0.0015) for phi in st_angles],
    ],
    0.0022,
    M["stubble"],
  )

  # Short side & back hair peeking cleanly under the cap
  hair_phis = [math.radians(a) for a in range(80, 281, 16)]
  hair_rows = []
  for k in range(4):
    t = k / 3.0
    row = []
    for phi in hair_phis:
      backness = max(0.0, -math.cos(phi))
      z_lo = head.z_at(0.124 - 0.044 * backness)
      z_hi = head.z_at(0.180 - 0.010 * backness)
      z = z_lo + (z_hi - z_lo) * t
      bulk = 0.0040 + 0.0055 * math.sin(math.pi * (0.2 + 0.65 * t))
      row.append(head.point(z, phi, bulk))
    hair_rows.append(row)
  head.shell(body, hair_rows, 0.0085, M["hair_dark"])

  # --- Worn baseball cap (gorra gastada) ---
  # Snug fit over hair & brow so there is zero temple gap while sunglasses stay fully readable
  cap_phis = [math.tau * k / 16 for k in range(16)]
  cap_rings = []
  for r_idx, (t, extra_r, z_lift) in enumerate([
    (0.00, 0.009, 0.000),
    (0.28, 0.012, 0.004),
    (0.58, 0.014, 0.010),
    (0.82, 0.014, 0.016),
    (0.96, 0.008, 0.020),
  ]):
    r_pts = []
    for phi in cap_phis:
      frontness = math.cos(phi)
      # Brim sits snugly above brows in front (dz=0.180), lower at back (dz=0.158)
      z_base = head.z_at(0.169 + 0.011 * frontness)
      z_top = head.z_at(0.264)
      z = z_base + (z_top - z_base) * t + z_lift * t
      if t >= 0.95:
        r_pts.append((0.0, head.y_offset + 0.006, z))
      else:
        p = head.point(min(z, head.z_at(0.258)), phi, grow=extra_r, sculpt=False)
        r_pts.append((p[0], p[1], z))
    cap_rings.append(r_pts)
  body.loft(cap_rings[:-1], M["cap"], caps=(True, True))

  # Top cap button
  btn_z = head.z_at(0.278)
  body.tube([
    ((0.0, head.y_offset + 0.006, btn_z - 0.004), 0.012, 0.012),
    ((0.0, head.y_offset + 0.006, btn_z + 0.005), 0.010, 0.010),
  ], M["cap_dark"], n=8)

  # Mustard emblem patch on front of cap
  patch_angles = (-22, -11, 0, 11, 22)
  p_bot = [head.point(head.z_at(0.196), math.radians(a), grow=0.0155, sculpt=False) for a in patch_angles]
  p_top = [head.point(head.z_at(0.228), math.radians(a), grow=0.0160, sculpt=False) for a in patch_angles]
  head.shell(body, [p_bot, p_top], 0.004, M["mustard"])

  # Curved front visor extending forward (-Y)
  vis_angles = [math.radians(a) for a in (-68, -48, -28, -10, 10, 28, 48, 68)]
  vis_rows = []
  for row_i, (reach, drop) in enumerate([(0.004, 0.000), (0.044, -0.007), (0.088, -0.019)]):
    row = []
    for phi in vis_angles:
      base_p = Vector(head.point(head.z_at(0.178 + 0.004 * math.cos(phi)), phi, grow=0.010, sculpt=False))
      fwd_scale = max(0.0, math.cos(phi * 1.15)) ** 0.72
      curve_drop = -0.010 * (math.sin(phi) ** 2) * (row_i / 2.0)
      pt = Vector((
        base_p.x * (1.0 + 0.06 * (row_i / 2.0)),
        base_p.y - reach * fwd_scale,
        base_p.z + drop * fwd_scale + curve_drop,
      ))
      row.append(tuple(pt))
    vis_rows.append(row)
  solid_shell(
    body,
    vis_rows,
    0.006,
    M["cap_dark"],
    mat_inner=M["cap_dark"],
    mat_edge=M["cap"],
    inward_dir=lambda p, r, c: Vector((0.0, 0.0, -1.0)),
  )

  # --- Dark street sunglasses (lentes oscuros) ---
  gl_y = head.y_offset - 0.118
  gl_z = head.z_at(0.145)
  for s in (-1, 1):
    yaw = s * math.radians(10.0)
    cy, sy = math.cos(yaw), math.sin(yaw)
    cx = s * 0.042
    lens_uv = [
      (-0.027, 0.015),
      (0.027, 0.016),
      (0.029, -0.003),
      (0.018, -0.016),
      (-0.015, -0.016),
      (-0.027, -0.002),
    ]
    def g_pt(u, v, dy=0.0):
      return (cx + u * cy, gl_y + dy + u * sy, gl_z + v)

    # Dark lens plate
    l_front = [g_pt(u, v, -0.0025) for u, v in lens_uv]
    l_back = [g_pt(u, v, 0.0020) for u, v in lens_uv]
    n_l = len(lens_uv)
    l_faces = [tuple(range(n_l)), tuple(range(2 * n_l - 1, n_l - 1, -1))]
    for k in range(n_l):
      nk = (k + 1) % n_l
      l_faces.append((k, nk, n_l + nk, n_l + k))
    body.add(l_front + l_back, l_faces, M["glasses_lens"])

    # Outer frame rim (slightly larger)
    for k in range(n_l):
      u0, v0 = lens_uv[k]
      u1, v1 = lens_uv[(k + 1) % n_l]
      body.tube([
        (g_pt(u0 * 1.07, v0 * 1.07, -0.001), 0.0030, 0.0032),
        (g_pt(u1 * 1.07, v1 * 1.07, -0.001), 0.0030, 0.0032),
      ], M["glasses_frame"], n=4)

    # Temple arm back to ear
    lug = g_pt(s * 0.028, 0.012, 0.001)
    t_mid = (s * 0.099, head.y_offset - 0.050, head.z_at(0.156))
    t_ear = (s * 0.104, head.y_offset + 0.012, head.z_at(0.163))
    t_hook = (s * 0.102, head.y_offset + 0.032, head.z_at(0.144))
    body.tube([
      (lug, 0.0032, 0.0038),
      (t_mid, 0.0028, 0.0032),
      (t_ear, 0.0026, 0.0028),
      (t_hook, 0.0022, 0.0022),
    ], M["glasses_frame"], n=4)

  # Gold double-bridge bar between lenses
  body.tube([
    ((-0.016, gl_y - 0.003, gl_z + 0.015), 0.0024, 0.0024),
    ((0.0, gl_y - 0.006, gl_z + 0.016), 0.0024, 0.0024),
    ((0.016, gl_y - 0.003, gl_z + 0.015), 0.0024, 0.0024),
  ], M["gold"], n=4)
  body.tube([
    ((-0.015, gl_y - 0.002, gl_z + 0.005), 0.0020, 0.0020),
    ((0.0, gl_y - 0.005, gl_z + 0.006), 0.0020, 0.0020),
    ((0.015, gl_y - 0.002, gl_z + 0.005), 0.0020, 0.0020),
  ], M["gold"], n=4)


def build_torso_and_vest(body, M):
  # 1. Inner neck & upper chest skin seal (zero gap under open tee collar)
  neck_rings = [
    ring(1.280, 0.132, 0.118, 0.112, y=0.002, n=12, power=2.3),
    ring(1.375, 0.106, 0.088, 0.090, y=0.000, n=12, power=2.3),
    ring(1.425, 0.075, 0.072, 0.074, y=-0.004, n=12, power=2.2),
    ring(1.495, 0.069, 0.068, 0.069, y=-0.008, n=12, power=2.2),
    ring(1.535, 0.064, 0.062, 0.064, y=-0.010, n=12, power=2.2),
  ]
  body.loft(neck_rings, M["skin"], caps=(True, True))

  # 2. Franela (t-shirt) with realistic beer-belly silhouette
  n_ring = 16
  phis = [math.tau * (k + 0.5) / n_ring for k in range(n_ring)]
  shirt_rings = [[torso_point(st[0], phi, grow=0.0) for phi in phis] for st in TORSO_STATIONS]
  body.loft(shirt_rings, M["shirt"], caps=(True, True))

  # Collar rib band around neck opening
  collar_phis = [math.tau * k / 16 for k in range(16)]
  c_bot = []
  c_top = []
  for phi in collar_phis:
    front_dip = 0.022 * max(0.0, math.cos(phi)) ** 1.4
    z_c = 1.424 - front_dip
    c_bot.append(torso_point(z_c - 0.012, phi, grow=0.004))
    c_top.append(torso_point(z_c + 0.006, phi, grow=0.005))
  solid_shell(
    body,
    [c_bot, c_top],
    0.008,
    M["shirt_dark"],
    inward_dir=lambda p, r, c: Vector((-p.x, -p.y, 0.0)).normalized(),
  )

  # Gold chain resting cleanly inside the open vest on the franela neckline
  chain_pts = []
  for k in range(13):
    ang = math.radians(-58 + 116 * (k / 12.0))
    frontness = max(0.0, math.cos(ang))
    z_ch = 1.425 - 0.110 * (frontness ** 1.35)
    p = torso_point(z_ch, ang, grow=0.0065 + 0.0025 * frontness)
    chain_pts.append((p, 0.0046, 0.0040))
  body.tube(chain_pts, M["gold"], n=6)
  # Small gold pendant / coin medallion at bottom of chain
  pend_p = torso_point(1.300, 0.0, grow=0.012)
  body.tube([
    ((pend_p[0], pend_p[1] - 0.003, pend_p[2] - 0.013), 0.011, 0.004),
    ((pend_p[0], pend_p[1] - 0.003, pend_p[2] + 0.009), 0.011, 0.004),
  ], M["gold"], n=6)

  # 3. Open multi-pocket olive utility vest (chaleco multibolsillos)
  # Wraps from front-left edge (phi=+0.27) around the back to front-right edge (phi=2*pi-0.27)
  vest_zs = [0.876, 0.945, 1.025, 1.115, 1.210, 1.300, 1.375, 1.414]
  n_v = 19
  vest_phis = [0.27 + (math.tau - 0.54) * (k / (n_v - 1)) for k in range(n_v)]
  vest_rows = []
  for z in vest_zs:
    row = []
    for phi in vest_phis:
      # Slight armhole cutout near top sides (|sin(phi)| near 1, z in 1.18..1.38)
      grow = 0.015
      if z > 1.34:
        grow = 0.014
      row.append(torso_point(z, phi, grow=grow))
    vest_rows.append(row)
  solid_shell(
    body,
    vest_rows,
    0.011,
    M["vest"],
    mat_inner=M["vest_inner"],
    mat_edge=M["vest_dark"],
    inward_dir=lambda p, r, c: Vector((-p.x, -p.y, 0.0)).normalized(),
  )

  # Vest stand-up collar around back & sides of neck
  vc_phis = [0.42 + (math.tau - 0.84) * (k / 12.0) for k in range(13)]
  vc_bot = [torso_point(1.404, phi, grow=0.014) for phi in vc_phis]
  vc_top = [torso_point(1.434, phi, grow=0.017) for phi in vc_phis]
  solid_shell(
    body,
    [vc_bot, vc_top],
    0.009,
    M["vest_dark"],
    mat_inner=M["vest_inner"],
    inward_dir=lambda p, r, c: Vector((-p.x, -p.y, 0.0)).normalized(),
  )

  # Vest front trim / zipper strips along both open edges
  for s in (-1, 1):
    phi_e = s * 0.27
    z_pts = [(torso_point(z, phi_e, grow=0.017), 0.007, 0.006) for z in (0.862, 0.980, 1.120, 1.260, 1.385)]
    body.tube(z_pts, M["vest_dark"], n=4)

  # 4. Chunky utility pockets on the vest (2 lower cargo, 2 upper chest, 2 side utility)
  def add_vest_pocket(z_center, phi_center, half_w, half_h, depth, has_snap=True):
    p = Vector(torso_point(z_center, phi_center, grow=0.016))
    # Outward normal approximately radial in XY
    out = Vector((math.sin(phi_center), -math.cos(phi_center), 0.0)).normalized()
    tangent = Vector((math.cos(phi_center), math.sin(phi_center), 0.0)).normalized()
    up = Vector((0.0, 0.0, 1.0))
    # Main pocket body
    add_angled_box(body, p + out * (depth * 0.5), tangent, out, up, half_w, depth * 0.5, half_h, M["vest_dark"])
    # Top flap slightly overhanging
    flap_c = p + out * (depth * 0.62) + up * (half_h * 0.68)
    add_angled_box(body, flap_c, tangent, out, up, half_w * 1.04, depth * 0.55, half_h * 0.34, M["vest"])
    if has_snap:
      snap_c = flap_c + out * (depth * 0.52) - up * (half_h * 0.10)
      add_angled_box(body, snap_c, tangent, out, up, 0.007, 0.004, 0.007, M["brass"])

  for s in (-1, 1):
    # Lower big cargo pockets on belly/hip front
    add_vest_pocket(0.955, s * 0.62, 0.052, 0.062, 0.028, has_snap=True)
    # Upper chest pockets (keep left slightly out of koala pouch center)
    add_vest_pocket(1.190, s * 0.68, 0.042, 0.044, 0.022, has_snap=True)
    # Side hip pockets
    add_vest_pocket(0.960, s * 1.32, 0.046, 0.056, 0.024, has_snap=True)


def build_arms_and_hands(body, M):
  # Confident relaxed stance, arms held slightly clear of wide belly & vest pockets
  for s in (-1, 1):
    sh = Vector((s * 0.228, 0.006, 1.330))
    bicep_mid = Vector((s * 0.285, 0.016, 1.210))
    sleeve_end = Vector((s * 0.304, 0.020, 1.155))
    elbow = Vector((s * 0.320, 0.026, 1.065))
    forearm_mid = Vector((s * 0.312, -0.006, 0.955))
    wrist = Vector((s * 0.296, -0.044, 0.848))
    knuckle = Vector((s * 0.286, -0.058, 0.778))
    tip = Vector((s * 0.272, -0.068, 0.708))
    thumb = Vector((s * 0.268, -0.098, 0.778))

    # Short franela sleeve
    body.tube([
      (sh - Vector((s * 0.032, 0.0, 0.0)), 0.072, 0.074),
      (sh, 0.074, 0.074),
      (bicep_mid, 0.068, 0.068),
      (sleeve_end, 0.066, 0.066),
    ], M["shirt"], n=10)
    # Sleeve hem cuff
    body.tube([
      (sleeve_end + Vector((0, 0, 0.012)), 0.068, 0.068),
      (sleeve_end - Vector((0, 0, 0.004)), 0.067, 0.067),
    ], M["shirt_dark"], n=10)

    # Sturdy bare arms & forearms (smooth wrist blend into add_hand)
    body.tube([
      (bicep_mid, 0.060, 0.060),
      (sleeve_end, 0.058, 0.058),
      (elbow, 0.052, 0.053),
      (forearm_mid, 0.049, 0.048),
      (wrist, 0.036, 0.031),
    ], M["skin"], n=10)

    # Chunky gold wristwatch on left wrist (+X)
    if s > 0:
      w_dir = (wrist - forearm_mid).normalized()
      w_pos = wrist - w_dir * 0.024
      body.tube([
        (w_pos - w_dir * 0.011, 0.038, 0.035),
        (w_pos + w_dir * 0.011, 0.038, 0.035),
      ], M["gold"], n=10)
      # Watch dial on outer wrist
      add_angled_box(
        body,
        w_pos + Vector((0.034, -0.010, 0.0)),
        Vector((0.0, 1.0, 0.0)),
        Vector((1.0, 0.0, 0.0)),
        Vector((0.0, 0.0, 1.0)),
        0.014,
        0.007,
        0.014,
        M["glasses_frame"],
      )

    # Reusable hand with 0.014m wrist overlap
    add_hand(body, wrist, knuckle, tip, thumb, s, M["skin"])


def build_legs_belt_and_shoes(body, M):
  # Pelvis / hips jeans block
  pelvis_rings = [
    ring(0.755, 0.200, 0.140, 0.144, y=0.004, n=14, power=2.35),
    ring(0.825, 0.210, 0.152, 0.150, y=0.002, n=14, power=2.35),
    ring(0.895, 0.208, 0.168, 0.144, y=0.000, n=14, power=2.40),
    ring(0.925, 0.205, 0.172, 0.140, y=0.000, n=14, power=2.40),
  ]
  body.loft(pelvis_rings, M["jeans"], caps=(True, True))

  # Belt strictly wider than pelvis/waistband (pelvis + 0.009m clearance)
  belt_rings = [
    ring(0.868, 0.220, 0.178, 0.156, y=0.000, n=16, power=2.40),
    ring(0.908, 0.221, 0.184, 0.155, y=0.000, n=16, power=2.40),
  ]
  body.loft(belt_rings, M["leather"], caps=(True, True))

  # Brass belt buckle at front (-Y)
  body.box((-0.034, -0.194, 0.864), (0.034, -0.176, 0.912), M["brass"])
  body.box((-0.020, -0.196, 0.874), (0.020, -0.184, 0.902), M["leather"])

  # Sturdy jeans legs + cargo thigh pockets + cuffed hems
  for s in (-1, 1):
    x_hip = s * 0.116
    x_knee = s * 0.130
    x_ank = s * 0.135
    leg_rings = [
      ring(0.790, 0.112, 0.118, 0.120, y=0.002, n=12, power=2.3, x=x_hip),
      ring(0.640, 0.104, 0.108, 0.110, y=-0.002, n=12, power=2.3, x=x_hip * 0.5 + x_knee * 0.5),
      ring(0.490, 0.094, 0.096, 0.098, y=-0.006, n=12, power=2.3, x=x_knee),
      ring(0.320, 0.088, 0.090, 0.092, y=0.004, n=12, power=2.3, x=x_knee * 0.4 + x_ank * 0.6),
      ring(0.145, 0.082, 0.084, 0.084, y=0.010, n=12, power=2.3, x=x_ank),
      ring(0.112, 0.084, 0.086, 0.086, y=0.010, n=12, power=2.3, x=x_ank),
    ]
    body.loft(leg_rings, M["jeans"], caps=(True, True))

    # Jeans cuff rim
    cuff_rings = [
      ring(0.108, 0.087, 0.089, 0.089, y=0.010, n=12, power=2.3, x=x_ank),
      ring(0.134, 0.087, 0.089, 0.089, y=0.010, n=12, power=2.3, x=x_ank),
    ]
    body.loft(cuff_rings, M["jeans_dark"], caps=(True, True))

    # Cargo pocket on outer thigh
    px_out = x_hip + s * 0.108
    add_angled_box(
      body,
      (px_out, 0.000, 0.610),
      (0.0, 1.0, 0.0),
      (s, 0.0, 0.0),
      (0.0, 0.0, 1.0),
      0.054,
      0.018,
      0.070,
      M["jeans_dark"],
    )

    # Worn street sneakers grounded at z=0
    add_footwear(
      body,
      x_ank,
      s,
      shoe_mat=M["shoe"],
      sole_mat=M["sole"],
      accent_mat=M["cap"],  # Muted terracotta/red sneaker accent
      lace_mat=M["lace"],
      boot_height=0.0,
    )


def build_koala(body, M):
  """Crossbody chest fanny pack (koala) for lochas — signature Venezuelan street merchant prop."""
  # Diagonal strap wrapping cleanly outside the vest from left shoulder (+X) to right waist (-X)
  strap_path = [
    (1.395, 0.78),   # Left shoulder top
    (1.320, 0.42),   # Upper left chest
    (1.200, 0.05),   # Center chest (passes through pouch)
    (1.075, -0.42),  # Right upper belly
    (0.955, -0.98),  # Right waist side
    (0.925, -1.65),  # Right lower back
    (1.020, -2.35),  # Mid back
    (1.180, -2.92),  # Upper back
    (1.335, 2.58),   # Back left shoulder
    (1.402, 1.65),   # Top left shoulder
    (1.395, 0.78),   # Close loop
  ]
  strap_tube = []
  for z, phi in strap_path:
    # Extra clearance over vest, chest, and shoulder backpack strap
    grow = 0.034 if (abs(phi) < 1.3 or z > 1.34) else 0.028
    strap_tube.append((torso_point(z, phi, grow=grow), 0.022, 0.008))
  body.tube(strap_tube, M["koala_strap"], n=6)

  # Chunky angled koala pouch resting diagonally on chest
  pouch_c = Vector(torso_point(1.185, 0.02, grow=0.058))
  # Diagonal axis along the strap from upper-left (+X, +Z) to lower-right (-X, -Z)
  x_ax = Vector((0.82, 0.0, 0.57)).normalized()
  y_ax = Vector((0.0, -1.0, 0.14)).normalized()
  z_ax = x_ax.cross(y_ax).normalized()
  y_ax = z_ax.cross(x_ax).normalized()

  # Main rounded pouch body (3-station lofted box-like capsule along x_ax)
  pouch_rings = []
  for u, sy, sz in [
    (-0.118, 0.022, 0.032),
    (-0.088, 0.038, 0.052),
    (0.000, 0.044, 0.058),
    (0.088, 0.038, 0.052),
    (0.118, 0.022, 0.032),
  ]:
    ctr = pouch_c + x_ax * u
    r_pts = []
    for k in range(8):
      ang = math.tau * (k + 0.5) / 8
      r_pts.append(tuple(ctr + y_ax * (sy * math.cos(ang)) + z_ax * (sz * math.sin(ang))))
    pouch_rings.append(r_pts)
  body.loft(pouch_rings, M["koala"], caps=(True, True))

  # Front flat zippered pocket on koala
  add_angled_box(body, pouch_c + y_ax * 0.036 - z_ax * 0.008, x_ax, y_ax, z_ax, 0.072, 0.014, 0.032, M["koala_strap"])

  # Warm mustard zipper piping & pull tab across top of koala
  add_angled_box(body, pouch_c + y_ax * 0.030 + z_ax * 0.036, x_ax, y_ax, z_ax, 0.082, 0.008, 0.007, M["mustard"])
  add_angled_box(body, pouch_c + x_ax * 0.052 + y_ax * 0.040 + z_ax * 0.022, x_ax, y_ax, z_ax, 0.008, 0.005, 0.016, M["gold"])

  # Side release buckle on lower-right chest strap
  b_pos = Vector(torso_point(1.065, -0.48, grow=0.034))
  add_angled_box(body, b_pos, x_ax, y_ax, z_ax, 0.022, 0.010, 0.018, M["glasses_frame"])


def build_backpack_and_goods(body, M):
  """Bulky merchant backpack with fire/ice grease tins, papelón bottle, and rolled mustard tarp."""
  # Main bulging canvas pack seated flush against the back of the vest (y +0.14 to +0.38)
  pack_rings = [
    ring(0.900, 0.168, 0.095, 0.105, y=0.246, n=12, power=2.6),
    ring(1.010, 0.186, 0.112, 0.125, y=0.256, n=12, power=2.6),
    ring(1.160, 0.192, 0.115, 0.130, y=0.261, n=12, power=2.6),
    ring(1.310, 0.182, 0.108, 0.118, y=0.256, n=12, power=2.6),
    ring(1.415, 0.158, 0.092, 0.098, y=0.246, n=12, power=2.5),
  ]
  body.loft(pack_rings, M["pack"], caps=(True, True))

  # Top flap lid
  lid_rings = [
    ring(1.345, 0.190, 0.114, 0.128, y=0.260, n=12, power=2.6),
    ring(1.425, 0.175, 0.102, 0.110, y=0.252, n=12, power=2.5),
    ring(1.445, 0.140, 0.080, 0.086, y=0.244, n=12, power=2.5),
  ]
  body.loft(lid_rings, M["pack_dark"], caps=(True, True))

  # Two leather/webbing closure straps & brass buckles down the back of the pack
  for s in (-1, 1):
    sx = s * 0.088
    body.box((sx - 0.016, 0.358, 0.980), (sx + 0.016, 0.394, 1.425), M["leather"])
    body.box((sx - 0.020, 0.381, 1.245), (sx + 0.020, 0.402, 1.285), M["brass"])

  # Rear lower pocket on the backpack
  body.box((-0.135, 0.341, 0.935), (0.135, 0.424, 1.155), M["pack_dark"])
  body.box((-0.140, 0.356, 1.125), (0.140, 0.430, 1.168), M["pack"])

  # Backpack shoulder straps hooking cleanly over the shoulders
  for s in (-1, 1):
    st_pts = [
      (torso_point(1.385, s * 2.45, grow=0.022), 0.026, 0.010),
      (torso_point(1.412, s * 1.48, grow=0.024), 0.028, 0.010),
      (torso_point(1.335, s * 0.85, grow=0.024), 0.026, 0.010),
      (torso_point(1.185, s * 0.92, grow=0.024), 0.024, 0.009),
      (torso_point(1.015, s * 1.35, grow=0.024), 0.022, 0.009),
      (torso_point(0.960, s * 2.20, grow=0.022), 0.022, 0.009),
    ]
    body.tube(st_pts, M["leather"], n=6)

  # Rolled mustard tarp / lona strapped across the top of the backpack (strong silhouette!)
  body.tube([
    ((-0.235, 0.254, 1.490), 0.056, 0.056),
    ((-0.180, 0.254, 1.495), 0.064, 0.064),
    ((0.000, 0.254, 1.498), 0.066, 0.066),
    ((0.180, 0.254, 1.495), 0.064, 0.064),
    ((0.235, 0.254, 1.490), 0.056, 0.056),
  ], M["mustard"], n=10, side=(0, 1, 0))
  # Inner dark roll spiral ends + binding straps
  for s in (-1, 1):
    body.tube([
      ((s * 0.232, 0.254, 1.490), 0.032, 0.032),
      ((s * 0.242, 0.254, 1.490), 0.028, 0.028),
    ], M["mustard_dark"], n=8, side=(0, 1, 0))
    body.tube([
      ((s * 0.115, 0.254, 1.496), 0.069, 0.069),
      ((s * 0.145, 0.254, 1.496), 0.069, 0.069),
    ], M["leather"], n=10, side=(0, 1, 0))

  # Side pockets with visible merchant goods (fire grease, ice grease, papelón bottle)
  for s in (-1, 1):
    px = s * 0.212
    # Open-top side pocket
    body.box((px - 0.044, 0.181, 0.960), (px + 0.044, 0.326, 1.155), M["pack_dark"])
    # Rim trim
    body.box((px - 0.047, 0.178, 1.142), (px + 0.047, 0.330, 1.164), M["leather"])

  # Left side pocket (+X): Fire-grease tin (orange-amber) peeking prominently
  body.tube([
    ((0.218, 0.241, 1.120), 0.038, 0.038),
    ((0.224, 0.241, 1.245), 0.038, 0.038),
  ], M["grease_fire"], n=10)
  body.tube([
    ((0.224, 0.241, 1.244), 0.040, 0.040),
    ((0.225, 0.241, 1.262), 0.038, 0.038),
  ], M["tin_lid"], n=10)

  # Right side pocket (-X): Ice-grease tin (cyan) + amber glass bottle sticking up
  body.tube([
    ((-0.218, 0.218, 1.120), 0.034, 0.034),
    ((-0.222, 0.218, 1.225), 0.034, 0.034),
  ], M["grease_ice"], n=10)
  body.tube([
    ((-0.222, 0.218, 1.224), 0.036, 0.036),
    ((-0.223, 0.218, 1.240), 0.034, 0.034),
  ], M["tin_lid"], n=10)

  # Amber papelón bottle behind ice tin in right pocket
  body.tube([
    ((-0.214, 0.288, 1.120), 0.030, 0.030),
    ((-0.218, 0.291, 1.220), 0.029, 0.029),
    ((-0.220, 0.293, 1.262), 0.014, 0.014),
    ((-0.222, 0.294, 1.310), 0.013, 0.013),
  ], M["bottle"], n=8)
  body.tube([
    ((-0.222, 0.294, 1.308), 0.015, 0.015),
    ((-0.223, 0.295, 1.326), 0.015, 0.015),
  ], M["cap"], n=8)


def build_bachaquero():
  M = build_materials()
  body = Shape()
  build_head_and_accessories(body, M)
  build_torso_and_vest(body, M)
  build_arms_and_hands(body, M)
  build_legs_belt_and_shoes(body, M)
  build_koala(body, M)
  build_backpack_and_goods(body, M)
  obj = body.finish("bachaquero")
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
  obj = build_bachaquero()
  audit_scene()
  bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
  print("Saved", BLEND_PATH)
  export_glb(obj)


if __name__ == "__main__":
  main()
