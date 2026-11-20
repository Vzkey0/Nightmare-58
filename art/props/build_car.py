# Builds Luis's car for the opening: a boxy 1980s sedan with its whole cabin, since most of the
# drive is shot from inside, and the same car crashed against the avenue's curb.
#   blender --background --python art/props/build_car.py
# The front points to +Y, so in Godot it faces -Z like the scene's car. One Blender unit is the
# same point in Godot's car frame: Godot (x, y, z) is Blender (x, -z, y).
# Exports car.glb (body and the radio's light), car_wheel.glb (the steering wheel alone, flat on
# XZ, for a pivot to tilt and turn) and car_crashed.glb (body and the kicked-open right door).
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from prop_tools import Shape, material

BLEND_PATH = os.path.join(HERE, "car.blend")
MODELS = os.path.join(HERE, "..", "..", "game", "models", "props")

# Where the people sit. build_luis.py reaches the wheel and the radio from the driver's seat.
SEAT_X = 0.38
SEAT_Y = -0.05
SEAT_TOP = 0.5
FLOOR = 0.22
WHEEL_HUB = Vector((-0.38, 0.45, 1.03))
WHEEL_TILT = math.radians(24)   # From vertical, the top leaning toward the driver.
WHEEL_RADIUS = 0.19
RADIO = Vector((0.0, 0.47, 0.9))
DOOR_HINGE = Vector((0.9, 0.82, 0.0))  # The right front door turns here when kicked.
DOOR_OPEN = 1.2

FIREWALL = 0.85
BELT = 0.98
ROOF = 1.52
FRONT = 2.35
REAR = -2.35
HALF = 0.9

M = {}


def make_materials():
  M.update({
    "paint": material("car_paint", (0.45, 0.17, 0.14), roughness=0.55),
    "paint_dull": material("car_paint_dull", (0.36, 0.14, 0.12), roughness=0.8),
    "chrome": material("car_chrome", (0.72, 0.72, 0.74), roughness=0.3),
    "hubcap": material("car_hubcap", (0.45, 0.45, 0.47), roughness=0.4),
    "rubber": material("car_rubber", (0.05, 0.05, 0.055), roughness=0.9),
    "under": material("car_under", (0.08, 0.08, 0.085)),
    "glass": material("car_glass", (0.55, 0.65, 0.72), roughness=0.05),
    "cracked": material("car_cracked", (0.82, 0.86, 0.88), roughness=0.3),
    "interior": material("car_interior", (0.13, 0.13, 0.14)),
    "carpet": material("car_carpet", (0.09, 0.085, 0.08), roughness=1.0),
    "seat": material("car_seat", (0.36, 0.27, 0.2), roughness=1.0),
    "seat_dark": material("car_seat_dark", (0.26, 0.19, 0.14), roughness=1.0),
    "seat_shell": material("car_seat_shell", (0.2, 0.155, 0.12), roughness=0.7),
    "vinyl": material("car_vinyl", (0.3, 0.23, 0.18), roughness=0.7),
    "belt": material("car_belt", (0.16, 0.16, 0.17), roughness=1.0),
    "headliner": material("car_headliner", (0.52, 0.5, 0.46), roughness=1.0),
    "dash": material("car_dash", (0.1, 0.1, 0.11)),
    "gauge": material("car_gauge", (0.02, 0.02, 0.025), roughness=0.3),
    "needle": material("car_needle", (0.95, 0.55, 0.2), glow=1.5),
    "dial": material("car_dial", (0.75, 0.85, 0.7), glow=0.6),
    "radio": material("car_radio", (0.035, 0.035, 0.04), roughness=0.4),
    "radio_light": material("car_radio_light", (0.35, 0.95, 0.55), glow=3.0),
    "headlight": material("car_headlight", (1.0, 0.95, 0.8), glow=2.0),
    "taillight": material("car_taillight", (0.7, 0.06, 0.05), glow=0.5),
    "plate": material("car_plate", (0.85, 0.83, 0.75)),
    "plate_text": material("car_plate_text", (0.1, 0.12, 0.3)),
    "bead": material("car_bead", (0.55, 0.42, 0.25), roughness=0.4),
    "pine": material("car_pine", (0.15, 0.55, 0.25)),
    "card": material("car_card", (0.78, 0.68, 0.42)),
  })
  glass = M["glass"]
  glass.surface_render_method = "BLENDED"
  bsdf = next(n for n in glass.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
  bsdf.inputs["Alpha"].default_value = 0.16
  cracked = M["cracked"]
  cracked.surface_render_method = "BLENDED"
  next(n for n in cracked.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Alpha"].default_value = 0.45


def slab(shape, corners, thickness, mat):
  """A flat panel from four corners in order, given a thickness so both faces show."""
  a, b, c, d = (Vector(p) for p in corners)
  normal = (b - a).cross(d - a).normalized() * (thickness / 2)
  verts = [tuple(p - normal) for p in (a, b, c, d)] + [tuple(p + normal) for p in (a, b, c, d)]
  faces = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
  shape.add(verts, faces, mat)


def bar(shape, a, b, radius, mat, n=4):
  shape.tube([(Vector(a), radius, radius), (Vector(b), radius, radius)], mat, n=n)


def side_loft(shape, stations, mat, x0, x1, chamfer=0.05):
  """A block lofted along Y from (y, bottom, top) stations, its top edges chamfered."""
  rings = []
  for y, bottom, top in stations:
    c = min(chamfer, (top - bottom) / 3)
    rings.append([(x0, y, bottom), (x1, y, bottom), (x1, y, top - c), (x1 - c, y, top), (x0 + c, y, top), (x0, y, top - c)])
  shape.loft(rings, mat)


# --- Outside ----------------------------------------------------------------------------------
def build_front(shape, crashed):
  if crashed:
    # The nose folded against the curb: shorter, skewed right, the hood buckled into a tent.
    side_loft(shape, [(FIREWALL - 0.05, 0.3, 0.95), (1.5, 0.32, 0.9), (1.95, 0.4, 0.76)], M["paint"], -HALF, HALF)
    slab(shape, [(-0.86, FIREWALL, 0.97), (0.86, FIREWALL, 0.97), (0.8, 1.42, 1.18), (-0.82, 1.4, 1.14)], 0.03, M["paint"])
    slab(shape, [(-0.82, 1.4, 1.14), (0.8, 1.42, 1.18), (0.9, 1.85, 0.82), (-0.75, 1.9, 0.8)], 0.03, M["paint"])
    bar(shape, (-0.95, 1.98, 0.42), (0.85, 2.02, 0.5), 0.07, M["chrome"])
    slab(shape, [(-0.7, 1.99, 0.5), (-0.45, 1.98, 0.48), (-0.46, 1.95, 0.62), (-0.71, 1.96, 0.64)], 0.02, M["headlight"])
    slab(shape, [(0.45, 2.01, 0.6), (0.72, 2.0, 0.66), (0.7, 1.95, 0.72), (0.44, 1.96, 0.68)], 0.02, M["cracked"])
    for k in range(3):
      slab(shape, [(-0.3 + k * 0.25, 1.98, 0.48), (-0.1 + k * 0.25, 1.98, 0.48), (-0.1 + k * 0.25, 1.98, 0.68), (-0.3 + k * 0.25, 1.98, 0.68)], 0.02, M["rubber"])
    return
  side_loft(shape, [(FIREWALL - 0.05, 0.28, 0.95), (1.6, 0.28, 0.93), (FRONT - 0.05, 0.3, 0.86), (FRONT, 0.34, 0.8)], M["paint"], -HALF, HALF)
  # Grille, headlights and the bumper.
  slab(shape, [(-0.42, FRONT + 0.005, 0.5), (0.42, FRONT + 0.005, 0.5), (0.42, FRONT + 0.005, 0.74), (-0.42, FRONT + 0.005, 0.74)], 0.02, M["rubber"])
  for k in range(5):
    x = -0.36 + k * 0.18
    bar(shape, (x, FRONT + 0.02, 0.52), (x, FRONT + 0.02, 0.72), 0.008, M["chrome"])
  for s in (-1, 1):
    slab(shape, [(s * 0.48, FRONT + 0.005, 0.54), (s * 0.78, FRONT + 0.005, 0.54), (s * 0.78, FRONT + 0.005, 0.72), (s * 0.48, FRONT + 0.005, 0.72)], 0.03, M["headlight"])
    slab(shape, [(s * 0.8, FRONT, 0.56), (s * 0.88, FRONT - 0.04, 0.56), (s * 0.88, FRONT - 0.04, 0.68), (s * 0.8, FRONT, 0.68)], 0.02, M["taillight"])
  shape.box((-0.92, FRONT - 0.02, 0.33), (0.92, FRONT + 0.1, 0.47), M["chrome"])
  shape.box((-0.22, FRONT + 0.1, 0.34), (0.22, FRONT + 0.12, 0.46), M["plate"])
  shape.box((-0.16, FRONT + 0.12, 0.38), (0.16, FRONT + 0.125, 0.42), M["plate_text"])


def build_rear(shape):
  side_loft(shape, [(REAR, 0.32, 0.92), (REAR + 0.1, 0.28, 1.0), (-1.3, 0.28, 1.0)], M["paint"], -HALF, HALF)
  for s in (-1, 1):
    slab(shape, [(s * 0.45, REAR - 0.005, 0.72), (s * 0.85, REAR - 0.005, 0.72), (s * 0.85, REAR - 0.005, 0.88), (s * 0.45, REAR - 0.005, 0.88)], 0.03, M["taillight"])
  shape.box((-0.92, REAR - 0.1, 0.33), (0.92, REAR + 0.02, 0.47), M["chrome"])
  shape.box((-0.22, REAR - 0.04, 0.56), (0.22, REAR - 0.02, 0.68), M["plate"])
  shape.box((-0.16, REAR - 0.045, 0.6), (0.16, REAR - 0.04, 0.64), M["plate_text"])


def wheel_at(shape, x, y, crashed_tilt=0.0):
  at = Matrix.Translation((x, y, 0.33)) @ Matrix.Rotation(math.radians(90), 4, "Y") @ Matrix.Rotation(crashed_tilt, 4, "X")
  shape.lathe([(0.0, -0.11), (0.2, -0.115), (0.33, -0.1), (0.33, 0.1), (0.2, 0.115), (0.0, 0.11)], M["rubber"], n=12, at=at)
  shape.lathe([(0.0, 0.112), (0.15, 0.116), (0.15, 0.12), (0.0, 0.122)], M["hubcap"], n=8, at=at if x > 0 else at @ Matrix.Rotation(math.pi, 4, "X"))


def build_sides(shape, crashed):
  for s in (-1, 1):
    # Rocker, doors and the arches over the wheels.
    rocker = sorted((s * HALF, s * (HALF - 0.04)))
    shape.box((rocker[0], -1.3, 0.28), (rocker[1], FIREWALL, 0.46), M["paint_dull"])
    for y0, y1 in ((-1.25, -0.17), (-0.15, FIREWALL - 0.03)):
      if crashed and s > 0 and y0 > -0.5:
        continue  # The kicked door is its own object.
      door(shape, s, y0, y1)
    for y in (-1.45, 1.45):
      if crashed and y > 0:
        wheel_at(shape, s * 0.82, 1.4, 0.15 * s)
      else:
        wheel_at(shape, s * 0.82, y)
    # Side trim along the doors.
    shape.box((s * HALF - 0.012, -1.25, 0.62), (s * HALF + 0.012, FIREWALL - 0.03, 0.66), M["chrome"])


def door(shape, s, y0, y1, origin=Vector()):
  """Outer skin with a handle and the inside card with its armrest, from rocker to belt line."""
  x_out = s * HALF
  x_in = s * (HALF - 0.07)
  lo, hi = min(x_out, x_in), max(x_out, x_in)
  o = origin
  shape.box(Vector((lo, y0, 0.45)) - o, Vector((hi, y1, BELT)) - o, M["paint"])
  handle = sorted((x_out, x_out + s * 0.015))
  shape.box(Vector((handle[0], y1 - 0.32, 0.82)) - o, Vector((handle[1], y1 - 0.18, 0.85)) - o, M["chrome"])
  # The inside card: carpet kick strip, a vinyl panel with a seam, the armrest and its pull cup,
  # the window crank and the lock knob on the sill.
  def x_span(a, b):
    return min(s * a, s * b), max(s * a, s * b)
  lo2, hi2 = x_span(HALF - 0.09, HALF - 0.07)
  shape.box(Vector((lo2, y0 + 0.03, 0.47)) - o, Vector((hi2, y1 - 0.03, 0.6)) - o, M["carpet"])
  shape.box(Vector((lo2, y0 + 0.03, 0.6)) - o, Vector((hi2, y1 - 0.03, BELT - 0.02)) - o, M["vinyl"])
  sl, sh = x_span(HALF - 0.095, HALF - 0.09)
  shape.box(Vector((sl, y0 + 0.06, 0.835)) - o, Vector((sh, y1 - 0.06, 0.845)) - o, M["seat_dark"])
  outer, inner = s * (HALF - 0.09), s * (HALF - 0.16)
  shape.extrude([(outer, 0.69), (inner, 0.69), (inner, 0.75), (outer, 0.775)], y0 + 0.2, y1 - 0.15, M["seat_dark"], at=Matrix.Translation(-o))
  cl, ch = x_span(HALF - 0.11, HALF - 0.095)
  shape.box(Vector((cl, y1 - 0.34, 0.72)) - o, Vector((ch, y1 - 0.24, 0.76)) - o, M["seat_shell"])
  crank = Vector((s * (HALF - 0.1), y1 - 0.42, 0.66)) - o
  bar(shape, crank, crank + Vector((-s * 0.025, 0, 0)), 0.012, M["chrome"], n=6)
  bar(shape, crank + Vector((-s * 0.025, 0, 0)), crank + Vector((-s * 0.025, -0.07, 0.03)), 0.006, M["chrome"])
  bar(shape, crank + Vector((-s * 0.025, -0.07, 0.03)), crank + Vector((-s * 0.05, -0.07, 0.03)), 0.01, M["seat_shell"], n=5)
  knob = Vector((s * (HALF - 0.1), y0 + 0.1, BELT - 0.02)) - o
  bar(shape, knob, knob + Vector((0, 0, 0.035)), 0.006, M["chrome"], n=5)
  # Window frame on top of the door, up to the roof rail.
  shape.box(Vector((lo, y0, BELT)) - o, Vector((hi, y1, BELT + 0.035)) - o, M["chrome"])


def build_greenhouse(shape, crashed):
  dent = 0.08 if crashed else 0.0
  inner = HALF - 0.16
  roof_front, roof_back = 0.25, -0.95
  for s in (-1, 1):
    x_belt = s * (HALF - 0.04)
    x_roof = s * inner
    # A, B and C pillars.
    bar(shape, (x_belt, FIREWALL - 0.02, BELT), (x_roof, roof_front, ROOF - dent * (s > 0)), 0.035, M["paint"])
    bar(shape, (x_belt, -0.16, BELT), (x_roof, -0.16, ROOF - dent * (s > 0)), 0.04, M["paint"])
    slab(shape, [(x_belt, -1.25, BELT), (x_belt, -1.32, BELT), (x_roof, roof_back - 0.05, ROOF), (x_roof, roof_back + 0.12, ROOF)], 0.05, M["paint"])
    # Side glass, front and rear.
    if not (crashed and s > 0):
      slab(shape, [(s * (HALF - 0.05), FIREWALL - 0.08, BELT + 0.04), (s * (HALF - 0.05), -0.14, BELT + 0.04), (s * (inner + 0.01), -0.14, ROOF - 0.03), (s * (inner + 0.01), roof_front - 0.04, ROOF - 0.03)], 0.006, M["glass"])
    slab(shape, [(s * (HALF - 0.05), -0.18, BELT + 0.04), (s * (HALF - 0.05), -1.22, BELT + 0.04), (s * (inner + 0.01), roof_back + 0.1, ROOF - 0.03), (s * (inner + 0.01), -0.18, ROOF - 0.03)], 0.006, M["glass"])
    # Roof rail and drip strip.
    bar(shape, (x_roof, roof_front, ROOF + 0.01), (x_roof, roof_back, ROOF + 0.01), 0.025, M["paint"])
  # Roof, with the headliner under it.
  roof = [(-inner, roof_front, ROOF), (inner, roof_front, ROOF - dent), (inner, roof_back, ROOF - dent * 0.5), (-inner, roof_back, ROOF)]
  slab(shape, [tuple(Vector(p) + Vector((0, 0, 0.03))) for p in roof], 0.05, M["paint"])
  slab(shape, [tuple(Vector(p) - Vector((0, 0, 0.012))) for p in roof], 0.02, M["headliner"])
  slab(shape, [(-inner + 0.02, roof_front - 0.02, ROOF - 0.035), (inner - 0.02, roof_front - 0.02, ROOF - 0.035), (inner - 0.02, 0.05, ROOF - 0.035), (-inner + 0.02, 0.05, ROOF - 0.035)], 0.01, M["headliner"])
  # Windshield and rear window.
  front = [(-HALF + 0.06, FIREWALL - 0.02, BELT - 0.01), (HALF - 0.06, FIREWALL - 0.02, BELT - 0.01), (inner - 0.02, roof_front + 0.02, ROOF - 0.02), (-inner + 0.02, roof_front + 0.02, ROOF - 0.02)]
  slab(shape, front, 0.008, M["cracked"] if crashed else M["glass"])
  if crashed:
    # The star where the head did not hit, and its cracks.
    center = Vector((0.25, 0.55, 1.26))
    for k in range(9):
      a = math.tau * k / 9 + 0.2
      tip = center + Vector((math.cos(a) * 0.5, -math.sin(a) * 0.25, math.sin(a) * 0.28))
      bar(shape, center, tip, 0.004, M["chrome"], n=3)
  slab(shape, [(-inner + 0.02, roof_back, ROOF - 0.02), (inner - 0.02, roof_back, ROOF - 0.02), (HALF - 0.08, -1.32, BELT + 0.02), (-HALF + 0.08, -1.32, BELT + 0.02)], 0.008, M["glass"])
  # Cowl under the windshield; the wipers are the scene's.
  shape.box((-HALF + 0.05, FIREWALL - 0.02, 0.94), (HALF - 0.05, FIREWALL + 0.12, BELT), M["rubber"])


# --- Inside -----------------------------------------------------------------------------------
def build_floor(shape):
  shape.box((-HALF + 0.04, -1.3, 0.2), (HALF - 0.04, FIREWALL, FLOOR), M["carpet"])
  shape.box((-0.12, -1.0, FLOOR), (0.12, 0.72, 0.33), M["carpet"])  # Transmission tunnel.
  shape.box((-HALF + 0.04, FIREWALL - 0.06, FLOOR), (HALF - 0.04, FIREWALL, 0.8), M["interior"])
  # Pedals for the driver and the shifter.
  for x in (-0.48, -0.36, -0.26):
    slab(shape, [(x - 0.04, 0.74, 0.3), (x + 0.04, 0.74, 0.3), (x + 0.04, 0.78, 0.4), (x - 0.04, 0.78, 0.4)], 0.02, M["rubber"])
  bar(shape, (0, 0.1, 0.33), (0.0, 0.05, 0.6), 0.012, M["chrome"])
  shape.box((-0.025, 0.02, 0.6), (0.025, 0.08, 0.66), M["rubber"])


def rounded(cx, cy, z, half_x, half_y, cut):
  """A horizontal rectangle ring with its corners cut, as eight points."""
  return [(cx - half_x + cut, cy - half_y, z), (cx + half_x - cut, cy - half_y, z), (cx + half_x, cy - half_y + cut, z),
          (cx + half_x, cy + half_y - cut, z), (cx + half_x - cut, cy + half_y, z), (cx - half_x + cut, cy + half_y, z),
          (cx - half_x, cy + half_y - cut, z), (cx - half_x, cy - half_y + cut, z)]


def seat(shape, x, y, width, rear=False):
  """A bucket seat (or the bench): cushion and back lofted with raised bolsters, a plastic shell
  behind the back and a rounded headrest on two posts. The fabric is two tones, bolsters darker."""
  front_y = y + 0.25
  back_y = y - 0.25
  w = width / 2
  wing = 0.035 if rear else 0.06  # How high the side bolsters stand over the center.
  # Base under the cushion, darker.
  shape.box((x - w + 0.02, back_y + 0.02, 0.28), (x + w - 0.02, front_y - 0.04, 0.4), M["seat_dark"])
  # Cushion: across it, outer edge, bolster crest, the dip where you sit; along it, a rolled nose.
  def cushion_ring(yy, top, nose=0.0):
    zs = [(-w, 0.4), (w, 0.4), (w, top + wing * 0.6 - nose), (w - 0.07, top + wing - nose),
          (w - 0.14, top - nose), (-w + 0.14, top - nose), (-w + 0.07, top + wing - nose), (-w, top + wing * 0.6 - nose)]
    return [(x + px, yy, pz) for px, pz in zs]
  stations = [cushion_ring(back_y, SEAT_TOP - 0.03), cushion_ring(front_y - 0.12, SEAT_TOP + 0.01),
              cushion_ring(front_y - 0.03, SEAT_TOP - 0.01, 0.01), cushion_ring(front_y, SEAT_TOP - 0.06, 0.03)]
  shape.loft(stations, lambda band, side: M["seat_dark"] if side in (1, 2, 6, 7) else M["seat"])
  # Back: horizontal sections from the hips up, leaning back; the face cupped by the bolsters.
  top = 1.02 if rear else 1.12
  lean = 0.1 if rear else 0.14
  rings = []
  heights = [SEAT_TOP - 0.02, SEAT_TOP + 0.15, SEAT_TOP + 0.35, top - 0.05, top]
  for k, z in enumerate(heights):
    t = (z - heights[0]) / (top - heights[0])
    cy = back_y - 0.06 - lean * t
    hw = w - 0.01 - (0.03 if k == len(heights) - 1 else 0.0)
    bol = wing * (1.2 - 0.9 * t) + (0.02 if k == 1 else 0.0)  # The lumbar swell.
    thick = 0.07 if k < len(heights) - 1 else 0.045
    rings.append([(x - hw, cy - thick, z), (x + hw, cy - thick, z), (x + hw, cy + thick * 0.5, z),
                  (x + hw - 0.06, cy + thick + bol, z), (x + hw - 0.13, cy + thick, z),
                  (x - hw + 0.13, cy + thick, z), (x - hw + 0.06, cy + thick + bol, z), (x - hw, cy + thick * 0.5, z)])
  # Faces 0-1-2 and 7-0 face the back: the plastic shell. 2-4 and 5-7 are the bolsters.
  def back_mat(band, side):
    if side in (0, 1, 7):
      return M["seat_shell"]
    return M["seat_dark"] if side in (2, 3, 6) else M["seat"]
  shape.loft(rings, back_mat)
  # A map pocket on the shell, for whoever rides behind.
  if not rear:
    shell = [Vector(rings[k][0]) for k in (1, 2)]
    shape.add([(x - w + 0.09, shell[0].y - 0.012, shell[0].z + 0.02), (x + w - 0.09, shell[0].y - 0.012, shell[0].z + 0.02),
               (x + w - 0.09, shell[1].y - 0.02, shell[1].z - 0.05), (x - w + 0.09, shell[1].y - 0.02, shell[1].z - 0.05)],
              [(0, 1, 2, 3), (3, 2, 1, 0)], M["seat_dark"])
    # Headrest: a soft rounded block on two chrome posts.
    hy = back_y - 0.06 - lean - 0.015
    for dx in (-0.07, 0.07):
      bar(shape, (x + dx, hy, top - 0.02), (x + dx, hy - 0.005, top + 0.07), 0.007, M["chrome"])
    hz = top + 0.07
    shape.loft([rounded(x, hy, hz, 0.115, 0.04, 0.025), rounded(x, hy - 0.004, hz + 0.03, 0.125, 0.055, 0.035),
                rounded(x, hy - 0.01, hz + 0.13, 0.12, 0.05, 0.035), rounded(x, hy - 0.012, hz + 0.16, 0.1, 0.035, 0.03)],
               lambda band, side: M["seat_dark"] if band == 0 else M["seat"])


def build_dash(shape):
  # Main body: deep under the windshield, a face toward the cabin.
  side_loft(shape, [(0.5, 0.58, 0.9), (0.6, 0.56, 0.95), (FIREWALL - 0.02, 0.6, 0.96)], M["dash"], -HALF + 0.05, HALF - 0.05, chamfer=0.06)
  # A padded roll along the edge toward the cabin.
  shape.tube([((-HALF + 0.08, 0.53, 0.93), 0.03, 0.025), ((HALF - 0.08, 0.53, 0.93), 0.03, 0.025)], M["vinyl"], n=6, side=(0, 1, 0))
  # Hood over the gauges in front of the driver.
  shape.box((-0.62, 0.52, 0.95), (-0.14, 0.66, 1.02), M["dash"])
  slab(shape, [(-0.6, 0.56, 0.86), (-0.16, 0.56, 0.86), (-0.16, 0.56, 0.98), (-0.6, 0.56, 0.98)], 0.01, M["gauge"])
  for x, r in ((-0.48, 0.05), (-0.29, 0.05)):
    ring_at = Matrix.Translation((x, 0.548, 0.92)) @ Matrix.Rotation(math.radians(90), 4, "X")
    shape.lathe([(0.0, 0.0), (r, 0.0), (r, 0.004), (0.0, 0.004)], M["dial"], n=10, at=ring_at)
    bar(shape, (x, 0.54, 0.92), (x + r * 0.7, 0.54, 0.92 + r * 0.5), 0.004, M["needle"], n=3)
  # Center stack with the radio, where Luis's hand lands.
  shape.box((-0.13, RADIO.y - 0.02, 0.6), (0.13, 0.6, 0.98), M["dash"])
  shape.box((-0.1, RADIO.y - 0.03, RADIO.z - 0.04), (0.1, RADIO.y, RADIO.z + 0.035), M["radio"])
  for x in (-0.085, 0.085):
    ring_at = Matrix.Translation((x, RADIO.y - 0.03, RADIO.z)) @ Matrix.Rotation(math.radians(90), 4, "X")
    shape.lathe([(0.0, 0.0), (0.012, 0.0), (0.012, 0.015), (0.0, 0.015)], M["chrome"], n=6, at=ring_at)
  for k in range(4):
    shape.box((-0.06 + k * 0.035, RADIO.y - 0.035, RADIO.z - 0.032), (-0.04 + k * 0.035, RADIO.y - 0.03, RADIO.z - 0.02), M["chrome"])
  # Vents and the glove box.
  for x in (-0.07, 0.02, 0.62):
    shape.box((x - 0.05, 0.495, 0.86), (x + 0.05, 0.5, 0.9), M["rubber"])
  shape.box((0.25, 0.555, 0.68), (0.7, 0.575, 0.84), M["interior"])
  # The column up to the wheel.
  bar(shape, (WHEEL_HUB.x, 0.62, 0.84), WHEEL_HUB + Vector((0, 0.06, -0.02)), 0.035, M["rubber"], n=6)


def steering_wheel(shape, at):
  """Rim, hub and three spokes, flat on XZ around the origin; at places it."""
  rim = []
  n = 14
  for k in range(n):
    a = math.tau * k / n
    rim.append((Vector((math.cos(a) * WHEEL_RADIUS, 0, math.sin(a) * WHEEL_RADIUS)), 0.016, 0.016))
  rim.append(rim[0])
  shape.tube([(at @ p, ru, rv) for p, ru, rv in rim], M["rubber"], n=5)
  hub = [(0.0, -0.02), (0.06, -0.02), (0.06, 0.03), (0.0, 0.04)]
  shape.lathe(hub, M["rubber"], n=8, at=at @ Matrix.Rotation(math.radians(-90), 4, "X"))
  for a in (0, math.pi, math.pi * 1.5):
    tip = Vector((math.cos(a) * WHEEL_RADIUS, 0, math.sin(a) * WHEEL_RADIUS))
    shape.tube([(at @ (tip * 0.25), 0.018, 0.008), (at @ (tip * 0.95), 0.014, 0.008)], M["rubber"], n=4, side=tuple(at.to_3x3() @ Vector((0, 1, 0))))


def wheel_matrix():
  """The wheel's frame in the car: on the hub, its face tilted back toward the driver."""
  return Matrix.Translation(WHEEL_HUB) @ Matrix.Rotation(WHEEL_TILT, 4, "X")


def build_mirror(shape):
  """Rear-view mirror with a rosary and a pine air freshener hanging from it."""
  top = Vector((0, 0.32, ROOF - 0.03))
  bar(shape, top, (0, 0.34, 1.4), 0.008, M["rubber"])
  shape.box((-0.12, 0.33, 1.36), (0.12, 0.37, 1.42), M["rubber"])
  shape.box((-0.11, 0.326, 1.365), (0.11, 0.33, 1.415), M["chrome"])
  beads = []
  for k in range(16):
    a = math.tau * k / 16
    beads.append(Vector((math.sin(a) * 0.05, 0.35, 1.355 - (1 - math.cos(a)) * 0.07)))
  for p in beads:
    shape.box(p - Vector((0.006, 0.006, 0.006)), p + Vector((0.006, 0.006, 0.006)), M["bead"])
  low = Vector((0, 0.35, 1.355 - 0.14))
  bar(shape, low, low - Vector((0, 0, 0.05)), 0.003, M["bead"], n=3)
  cross = low - Vector((0, 0, 0.07))
  shape.box(cross - Vector((0.004, 0.003, 0.025)), cross + Vector((0.004, 0.003, 0.025)), M["chrome"])
  shape.box(cross + Vector((-0.014, -0.003, 0.004)), cross + Vector((0.014, 0.003, 0.012)), M["chrome"])
  # The little tree, on its own string beside the beads.
  tree = Vector((0.07, 0.35, 1.25))
  bar(shape, (0.06, 0.35, 1.36), tree + Vector((0, 0, 0.06)), 0.002, M["card"], n=3)
  shape.add([tree + Vector((0, 0, 0.06)), tree + Vector((0.03, 0, -0.04)), tree + Vector((-0.03, 0, -0.04)),
             tree + Vector((0, 0.003, 0.06)), tree + Vector((0.03, 0.003, -0.04)), tree + Vector((-0.03, 0.003, -0.04))],
            [(0, 1, 2), (5, 4, 3), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)], M["pine"])
  # Sun visors folded up.
  for s in (-1, 1):
    visor = sorted((s * 0.12, s * 0.6))
    shape.box((visor[0], 0.12, ROOF - 0.06), (visor[1], 0.3, ROOF - 0.035), M["headliner"])


def build_cabin(shape, crashed):
  build_floor(shape)
  seat(shape, -SEAT_X, SEAT_Y, 0.52)
  seat(shape, SEAT_X, SEAT_Y, 0.52)
  seat(shape, 0.0, -0.85, 1.5, rear=True)
  build_dash(shape)
  build_mirror(shape)
  # A low console between the front seats, with the hand brake.
  shape.box((-0.11, -0.32, FLOOR), (0.11, 0.02, 0.4), M["seat_shell"])
  shape.box((-0.1, -0.31, 0.4), (0.1, -0.08, 0.43), M["vinyl"])
  bar(shape, (-0.0, -0.02, 0.4), (0.0, -0.22, 0.47), 0.016, M["seat_shell"], n=5)
  shape.box((-0.012, -0.25, 0.46), (0.012, -0.21, 0.49), M["chrome"])
  # Seat belts down the B pillars, and their buckles beside the seats.
  for s in (-1, 1):
    bx = s * (HALF - 0.11)
    shape.tube([((bx, -0.17, 1.36), 0.022, 0.003), ((bx, -0.19, 0.9), 0.022, 0.003), ((bx, -0.22, 0.45), 0.022, 0.003)], M["belt"], n=4, side=(1, 0, 0))
    shape.box((bx - 0.02, -0.19, 1.33), (bx + 0.02, -0.15, 1.38), M["seat_shell"])
    buckle = s * (SEAT_X - 0.3)
    shape.box((buckle - 0.015, -0.3, 0.4), (buckle + 0.015, -0.26, 0.5), M["seat_shell"])
  # A prayer card tucked in the dash, the kind every carrito por puesto has.
  slab(shape, [(0.35, 0.62, 0.965), (0.43, 0.62, 0.965), (0.43, 0.6, 1.07), (0.35, 0.6, 1.07)], 0.004, M["card"])
  if crashed:
    steering_wheel(shape, wheel_matrix() @ Matrix.Rotation(math.radians(70), 4, "Y"))


def build_body(crashed):
  shape = Shape()
  build_front(shape, crashed)
  build_rear(shape)
  build_sides(shape, crashed)
  build_greenhouse(shape, crashed)
  build_cabin(shape, crashed)
  # Underside, so a low camera never sees through the car.
  shape.box((-HALF + 0.05, REAR + 0.2, 0.2), (HALF - 0.05, FRONT - 0.3 if not crashed else 1.8, 0.28), M["under"])
  return shape


def build_door():
  """The right front door alone, with its origin on the hinge."""
  shape = Shape()
  # Its window burst in the crash: only a shard is left in the frame.
  door(shape, 1, -0.15, FIREWALL - 0.03, origin=DOOR_HINGE)
  slab(shape, [tuple(Vector(p) - DOOR_HINGE) for p in [(HALF - 0.05, FIREWALL - 0.08, BELT + 0.04), (HALF - 0.05, FIREWALL - 0.3, BELT + 0.04), (HALF - 0.08, FIREWALL - 0.12, BELT + 0.16)]][:3] + [tuple(Vector((HALF - 0.08, FIREWALL - 0.1, BELT + 0.16)) - DOOR_HINGE)], 0.006, M["cracked"])
  obj = shape.finish("door_right")
  obj.location = DOOR_HINGE
  obj.rotation_euler.z = DOOR_OPEN  # Kicked open, as the avenue finds it.
  return obj


# --- Build and export -------------------------------------------------------------------------
def clear():
  if bpy.app.background:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return
  for collection in (bpy.data.objects, bpy.data.meshes, bpy.data.materials):
    for item in list(collection):
      collection.remove(item)


def export(objects, name):
  for other in bpy.data.objects:
    other.hide_set(other not in objects)
  os.makedirs(MODELS, exist_ok=True)
  bpy.ops.export_scene.gltf(filepath=os.path.join(MODELS, name), export_format="GLB", use_visible=True)
  for other in bpy.data.objects:
    other.hide_set(False)


def main(write=True):
  clear()
  make_materials()
  body = build_body(False).finish("car_body")
  light = Shape()
  light.box((-0.075, RADIO.y - 0.034, RADIO.z - 0.005), (0.06, RADIO.y - 0.03, RADIO.z + 0.025), M["radio_light"])
  radio_light = light.finish("radio_light")
  wheel_shape = Shape()
  steering_wheel(wheel_shape, Matrix.Identity(4))
  wheel = wheel_shape.finish("steering_wheel")
  crashed = build_body(True).finish("car_crashed_body")
  door_right = build_door()
  for obj in (crashed, door_right):
    obj.location.x += 3.0
  if write:
    export([body, radio_light], "car.glb")
    export([wheel], "car_wheel.glb")
    for obj in (crashed, door_right):
      obj.location.x -= 3.0
    export([crashed, door_right], "car_crashed.glb")
    for obj in (crashed, door_right):
      obj.location.x += 3.0
    wheel.matrix_world = wheel_matrix()
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
  else:
    wheel.matrix_world = wheel_matrix()


if __name__ == "__main__":
  main()
