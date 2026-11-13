# Builds every loot prop and renders its icon from the same mesh, so a model and its icon never differ.
#   blender --background --python art/props/build_loot.py
# Saves loot.blend, one game/models/props/<key>.glb per prop and game/ui/icons/<key>.png per icon.
# Each prop stands on real sizes; LootPickup scales small ones up to be seen on the ground.
import math
import os
import random
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import machete
from prop_tools import Canvas, Shape, face_up, image_from, material

BLEND_PATH = os.path.join(HERE, "loot.blend")
MODELS = os.path.join(HERE, "..", "..", "game", "models", "props")
ICONS = os.path.join(HERE, "..", "..", "game", "ui", "icons")

RENDER_SIZE = 512
ICON_SIZE = 256
ICON_MARGIN = 1.14
OUTLINE_WIDTH = 6
OUTLINE_INK = (0.015, 0.02, 0.04)
OUTLINE_GLOW = (0.45, 0.6, 0.85)

ENAMEL = (0.9, 0.89, 0.83)
ENAMEL_BLUE = (0.13, 0.27, 0.55)
RUST = (0.42, 0.18, 0.08)
WAX = (0.93, 0.87, 0.68)
VINYL = (0.05, 0.05, 0.06)
VINYL_SHEEN = (0.14, 0.14, 0.17)
LABEL = (0.76, 0.16, 0.1)
LABEL_GOLD = (0.93, 0.74, 0.25)
IVORY = (0.92, 0.87, 0.74)
BAKELITE = (0.09, 0.15, 0.13)
INK = (0.05, 0.05, 0.05)
BRASS = (0.78, 0.58, 0.24)
PLASTER = (0.76, 0.78, 0.74)
PLASTER_DIRTY = (0.58, 0.58, 0.54)
CHAPEL_BLUE = (0.2, 0.36, 0.56)
CHAPEL_BLUE_DARK = (0.09, 0.15, 0.27)
BRICK = (0.56, 0.27, 0.17)
TIN = (0.52, 0.55, 0.56)
TIN_DARK = (0.36, 0.39, 0.42)
IRON = (0.1, 0.09, 0.09)
FLAME = (1.0, 0.55, 0.12)
FLAME_CORE = (1.0, 0.86, 0.4)
LEAF = (0.17, 0.33, 0.14)
LEAF_LIGHT = (0.28, 0.46, 0.17)
SILVER = (0.6, 0.64, 0.7)
SILVER_DARK = (0.34, 0.38, 0.46)
SOUL_GLOW = (0.5, 0.85, 1.0)
TAR = (0.035, 0.04, 0.06)
TAR_LIGHT = (0.08, 0.1, 0.16)


def flame(shape, x, y, z, height, core, tip, n=5):
  shape.lathe(
    [(height * 0.04, z), (height * 0.3, z + height * 0.22), (height * 0.21, z + height * 0.55), (height * 0.02, z + height)],
    lambda band, side: core if band == 0 else tip,
    n=n, at=Matrix.Translation((x, y, 0)),
  )


def build_coffee():
  """A chipped enamel mug: what a kitchen in a blackout still has. Sits centered, like the old cup."""
  enamel = material("enamel", ENAMEL, 0.4)
  blue = material("enamel_blue", ENAMEL_BLUE, 0.4)
  rust = material("enamel_rust", RUST)
  coffee = material("coffee", (0.09, 0.045, 0.02), 0.2)
  chips = {(1, 3), (2, 8), (3, 4), (0, 10), (3, 11)}

  def body(band, side):
    if band >= 5:
      return blue
    return rust if (band, side) in chips else enamel

  shape = Shape()
  shape.lathe([
    (0.029, -0.045), (0.0305, -0.042), (0.0325, -0.02), (0.0345, 0.0), (0.0365, 0.022), (0.0378, 0.036),
    (0.0385, 0.042), (0.038, 0.045), (0.0352, 0.045), (0.0342, 0.022),
  ], body, n=12)
  shape.lathe([(0.0342, 0.0225), (0.0001, 0.0225)], coffee, n=12, caps=(False, False))
  shape.tube([
    ((0.033, 0, 0.029), 0.0075, 0.0035), ((0.056, 0, 0.033), 0.0075, 0.0035), ((0.0675, 0, 0.012), 0.0075, 0.0035),
    ((0.0595, 0, -0.012), 0.0075, 0.0035), ((0.0325, 0, -0.022), 0.0075, 0.0035),
  ], enamel, n=6, side=(0, 1, 0))
  return shape.finish("coffee")


def build_candle():
  """A church taper with wax run down its side and a paper collar for the hand."""
  wax = material("wax", WAX, 0.6)
  wax_dark = material("wax_dark", (0.8, 0.7, 0.48), 0.6)
  paper = material("candle_paper", (0.66, 0.2, 0.15))
  wick = material("wick", (0.08, 0.06, 0.05))
  flame_tip = material("flame_tip", FLAME, glow=3.0)
  flame_core = material("flame_core", FLAME_CORE, glow=5.0)
  shape = Shape()
  shape.lathe([
    (0.0125, -0.1), (0.014, -0.096), (0.0143, -0.03), (0.0137, 0.04), (0.0146, 0.09), (0.0132, 0.097), (0.0085, 0.093),
  ], lambda band, side: wax_dark if band in (0, 5) else wax, n=8)
  for turn, stop in ((0.5, 0.03), (2.3, 0.058), (4.2, -0.012)):
    x, y = math.cos(turn), math.sin(turn)
    shape.tube([
      ((x * 0.0135, y * 0.0135, 0.096), 0.0024, 0.0024),
      ((x * 0.0148, y * 0.0148, (0.096 + stop) * 0.5), 0.0034, 0.0025),
      ((x * 0.0156, y * 0.0156, stop), 0.0044, 0.0034),
      ((x * 0.0142, y * 0.0142, stop - 0.008), 0.0016, 0.0016),
    ], wax, n=5, side=(-y, x, 0))
  shape.lathe([(0.0146, -0.042), (0.033, -0.026), (0.032, -0.022), (0.0146, -0.037)], paper, n=8, caps=(False, False))
  shape.tube([((0, 0, 0.092), 0.0014, 0.0014), ((0.0012, 0, 0.114), 0.0009, 0.0009)], wick, n=4)
  flame(shape, 0.001, 0, 0.106, 0.052, flame_core, flame_tip)
  return shape.finish("return_candle")


def letter(canvas, strokes, x, y, size, width, color):
  for stroke in strokes:
    canvas.stroke([(x + px * size, y + py * size) for px, py in stroke], width, color)


GAITA = (
  [[(0.85, 0.12), (0.2, 0), (0, 0.5), (0.2, 1), (0.85, 0.9), (0.9, 0.5), (0.5, 0.5)]],
  [[(0, 1), (0.45, 0), (0.9, 1)], [(0.2, 0.62), (0.7, 0.62)]],
  [[(0.45, 0), (0.45, 1)]],
  [[(0, 0), (0.9, 0)], [(0.45, 0), (0.45, 1)]],
  [[(0, 1), (0.45, 0), (0.9, 1)], [(0.2, 0.62), (0.7, 0.62)]],
)


def paint_sleeve():
  """A December record from the seventies: sunburst, maracas and the word in hand-cut letters."""
  size = 512
  canvas = Canvas(size, size, (0.82, 0.3, 0.1))
  center = (256, 312)
  for k in range(0, 18, 2):
    a, b = math.tau * k / 18, math.tau * (k + 1) / 18
    canvas.polygon([center, (center[0] + 760 * math.cos(a), center[1] + 760 * math.sin(a)), (center[0] + 760 * math.cos(b), center[1] + 760 * math.sin(b))], (0.93, 0.66, 0.16))
  canvas.circle(*center, 118, (0.97, 0.88, 0.62))
  canvas.circle(*center, 104, (0.11, 0.2, 0.42))
  for flip_x, turn in ((-1, 0.48), (1, -0.48)):
    head = (center[0] + flip_x * 34, center[1] - 28)
    tail = (head[0] + 118 * math.sin(turn) * -1, head[1] + 118 * math.cos(turn))
    canvas.stroke([head, tail], 13, (0.95, 0.86, 0.62))
    canvas.circle(*head, 45, (0.78, 0.16, 0.12))
    canvas.circle(head[0] - 12, head[1] - 12, 11, (0.97, 0.56, 0.34))
  canvas.rect(0, 0, size, 132, (0.97, 0.9, 0.72))
  canvas.rect(0, 132, size, 145, (0.11, 0.2, 0.42))
  for i, strokes in enumerate(GAITA):
    letter(canvas, strokes, 58 + i * 84, 28, 74, 15, (0.74, 0.14, 0.1))
  canvas.age(5, 0.5)
  canvas.stroke([(40, 512), (190, 372), (225, 398)], 3, (0.92, 0.84, 0.68), 0.75)
  return canvas.rgb


def build_vinyl():
  """The record half out of its sleeve: the disc gives the silhouette, the sleeve gives the color."""
  vinyl = material("vinyl", VINYL, 0.25)
  sheen = material("vinyl_sheen", VINYL_SHEEN, 0.25)
  label = material("vinyl_label", LABEL)
  gold = material("vinyl_label_gold", LABEL_GOLD)
  card = material("sleeve_back", (0.72, 0.62, 0.44))
  cover = material("sleeve_cover", image=image_from("sleeve_cover", paint_sleeve()))

  half = 0.1575
  shape = Shape()
  front = [(-half, -0.004, half), (half, -0.004, half), (half, -0.004, -half), (-half + 0.022, -0.004, -half), (-half, -0.004, -half + 0.022)]
  uvs = [[((x + half) / (2 * half), (z + half) / (2 * half)) for x, _, z in front]]
  shape.add(front, [(0, 1, 2, 3, 4)], cover, uvs)
  back = [(x, 0.004, z) for x, _, z in front]
  shape.add(back, [(4, 3, 2, 1, 0)], card)
  for i in (4, 0, 2, 3):
    j = (i + 1) % 5
    shape.add([front[i], front[j], back[j], back[i]], [(0, 1, 2, 3)], card)

  bands = {0: label, 1: label, 2: gold, 3: label, 4: vinyl, 5: sheen, 6: vinyl, 7: sheen, 8: vinyl, 9: sheen, 10: vinyl}
  groove = [
    (0.0036, -0.0012), (0.018, -0.0012), (0.034, -0.0012), (0.037, -0.0012), (0.05, -0.0012), (0.054, -0.0012),
    (0.078, -0.0012), (0.083, -0.0012), (0.108, -0.0012), (0.113, -0.0012), (0.145, -0.0012), (0.15, -0.0012),
  ]
  profile = groove + [(0.15, 0.0012), (0.0036, 0.0012)]
  at = Matrix.Translation((0.112, 0, 0)) @ face_up()
  shape.lathe(profile, lambda band, side: bands.get(band, vinyl), n=20, at=at, caps=(False, False))
  return shape.finish("gaita_vinyl")


def paint_card():
  """A faded batter from a winter-league card: red frame, night sky, yellow name band."""
  width, height = 320, 445
  canvas = Canvas(width, height, (0.93, 0.89, 0.76))
  canvas.rect(16, 16, width - 16, height - 16, (0.72, 0.13, 0.1))
  canvas.rect(32, 32, width - 32, height - 94, (0.16, 0.29, 0.5))
  canvas.rect(32, 262, width - 32, height - 94, (0.2, 0.42, 0.22))
  canvas.polygon([(32, 351), (160, 268), (288, 351)], (0.68, 0.48, 0.28))
  shirt = (0.96, 0.93, 0.85)
  skin = (0.56, 0.34, 0.22)
  canvas.stroke([(150, 158), (146, 252)], 58, shirt)
  canvas.stroke([(136, 262), (108, 340)], 26, (0.86, 0.83, 0.76))
  canvas.stroke([(158, 262), (194, 340)], 26, (0.86, 0.83, 0.76))
  canvas.stroke([(128, 164), (196, 136)], 19, shirt)
  canvas.stroke([(178, 164), (206, 140)], 17, shirt)
  canvas.stroke([(206, 142), (278, 42)], 10, (0.58, 0.38, 0.2))
  canvas.circle(156, 106, 28, skin)
  canvas.polygon([(126, 104), (130, 74), (184, 74), (190, 98), (206, 103), (176, 106)], (0.72, 0.13, 0.1))
  canvas.circle(150, 200, 7, (0.72, 0.13, 0.1))
  canvas.rect(32, 362, width - 32, 424, (0.95, 0.76, 0.2))
  for i in range(11):
    canvas.rect(58 + i * 19, 380, 70 + i * 19, 402 - (i % 3) * 3, (0.1, 0.12, 0.2))
  canvas.age(11, 0.42)
  return canvas.rgb


def paper_sheet(shape, width, height, columns, rows, warp, front, back, torn=None):
  """Two sides of a bent sheet. torn is the (column, row) cell that lost its outer corner."""
  verts = []
  for row in range(rows + 1):
    for column in range(columns + 1):
      x = (column / columns - 0.5) * width
      z = (0.5 - row / rows) * height
      verts.append((x, warp(x, z), z))
  uv = [(column / columns, 1.0 - row / rows) for row in range(rows + 1) for column in range(columns + 1)]
  faces = []
  for row in range(rows):
    for column in range(columns):
      a = row * (columns + 1) + column
      corners = (a, a + 1, a + columns + 2, a + columns + 1)
      if (column, row) == torn:
        corners = (a, a + columns + 2, a + columns + 1)
      faces.append(corners)
  shape.add(verts, faces, front, [[uv[i] for i in face] for face in faces])
  behind = [(x, y + 0.0007, z) for x, y, z in verts]
  shape.add(behind, [tuple(reversed(face)) for face in faces], back)


def build_card():
  front = material("card_front", image=image_from("card_front", paint_card()))
  back = material("card_back", (0.72, 0.68, 0.56))
  shape = Shape()
  paper_sheet(shape, 0.064, 0.089, 3, 4, lambda x, z: -0.0035 * max(0.0, (x + z - 0.03) / 0.04) ** 2 + 0.0009 * math.sin(x * 70), front, back)
  return shape.finish("baseball_card")


def build_tile():
  """Double six in ivory on a dark back, the two-tone tile of a street table."""
  ivory = material("tile_ivory", IVORY, 0.35)
  bakelite = material("tile_back", BAKELITE, 0.35)
  pip = material("tile_pip", INK, 0.4)
  brass = material("tile_brass", BRASS, 0.35)

  def ring(y, half_x, half_z, cut):
    return [
      (half_x - cut, y, half_z), (half_x, y, half_z - cut), (half_x, y, -half_z + cut), (half_x - cut, y, -half_z),
      (-half_x + cut, y, -half_z), (-half_x, y, -half_z + cut), (-half_x, y, half_z - cut), (-half_x + cut, y, half_z),
    ]

  rings = [
    ring(-0.0058, 0.0108, 0.0232, 0.0022), ring(-0.0044, 0.0125, 0.025, 0.0026), ring(0.0, 0.0125, 0.025, 0.0026),
    ring(0.0004, 0.0125, 0.025, 0.0026), ring(0.0044, 0.0125, 0.025, 0.0026), ring(0.0058, 0.0108, 0.0232, 0.0022),
  ]
  shape = Shape()
  shape.loft(rings, lambda band, side: ivory if band < 2 else bakelite)
  # The cap of the loft faces outward at both ends; the front one takes the ivory band's material.
  shape.mats[-2] = ivory
  for half in (1, -1):
    for row in (-1, 0, 1):
      for column in (-1, 1):
        at = Matrix.Translation((column * 0.0058, -0.00585, half * 0.0118 + row * 0.0065)) @ face_up()
        shape.lathe([(0.0027, 0.0), (0.0027, 0.0003)], pip, n=6, at=at)
  shape.box((-0.0092, -0.0061, -0.0006), (0.0092, -0.0057, 0.0006), pip)
  shape.lathe([(0.0022, 0.0), (0.0018, 0.0008)], brass, n=6, at=Matrix.Translation((0, -0.0059, 0)) @ face_up())
  return shape.finish("domino_tile")


def build_hallaca():
  """A December hallaca: a plantain-leaf parcel tied with string, a corner of leaf folded over the top."""
  leaf = material("hallaca_leaf", (0.12, 0.27, 0.1), 0.55)
  leaf_light = material("hallaca_leaf_light", (0.2, 0.38, 0.13), 0.55)
  leaf_dry = material("hallaca_leaf_dry", (0.45, 0.4, 0.2), 0.7)
  string = material("hallaca_string", (0.86, 0.82, 0.7))

  def ring(z, half_x, half_y, cut):
    return [
      (half_x - cut, half_y, z), (half_x, half_y - cut, z), (half_x, -half_y + cut, z), (half_x - cut, -half_y, z),
      (-half_x + cut, -half_y, z), (-half_x, -half_y + cut, z), (-half_x, half_y - cut, z), (-half_x + cut, half_y, z),
    ]

  # A pillow: low edges, a rounded middle.
  rings = [ring(z, hx, hy, c) for z, hx, hy, c in (
    (0.0, 0.062, 0.042, 0.012), (0.008, 0.07, 0.048, 0.014), (0.026, 0.071, 0.049, 0.016),
    (0.04, 0.064, 0.043, 0.016), (0.046, 0.05, 0.032, 0.014),
  )]
  shape = Shape()
  shape.loft(rings, lambda band, side: leaf_light if side % 2 else leaf)
  # The fold of leaf over the top, slightly lifted at its tip.
  shape.add([(-0.05, -0.032, 0.0462), (0.03, -0.032, 0.0462), (0.012, 0.018, 0.0475), (-0.05, 0.024, 0.0462)],
            [(0, 1, 2, 3)], leaf_dry)
  # Two loops of string each way, crossing on top.
  for x in (-0.024, 0.024):
    shape.tube([((x, 0.04, 0.0), 0.0012, 0.0012), ((x, 0.05, 0.03), 0.0012, 0.0012), ((x, 0.03, 0.0485), 0.0012, 0.0012),
                ((x, -0.03, 0.0485), 0.0012, 0.0012), ((x, -0.05, 0.03), 0.0012, 0.0012), ((x, -0.04, 0.0), 0.0012, 0.0012)],
               string, n=4, side=(1, 0, 0))
  shape.tube([((0.06, 0, 0.0), 0.0012, 0.0012), ((0.072, 0, 0.03), 0.0012, 0.0012), ((0.05, 0, 0.0485), 0.0012, 0.0012),
              ((-0.05, 0, 0.0485), 0.0012, 0.0012), ((-0.072, 0, 0.03), 0.0012, 0.0012), ((-0.06, 0, 0.0), 0.0012, 0.0012)],
             string, n=4, side=(0, 1, 0))
  return shape.finish("hallaca")


def build_papelon():
  """Papelón con limón in a tall glass: cane-sugar amber, a lime wheel on the rim and a striped straw."""
  drink = material("papelon_drink", (0.62, 0.36, 0.08), 0.15)
  drink_top = material("papelon_foam", (0.8, 0.6, 0.3), 0.4)
  glass = material("papelon_glass", (0.78, 0.88, 0.86), 0.08)
  rind = material("lime_rind", (0.22, 0.52, 0.1), 0.5)
  pulp = material("lime_pulp", (0.72, 0.86, 0.36), 0.5)
  straw = material("straw_red", (0.82, 0.12, 0.1), 0.4)
  straw_white = material("straw_white", (0.92, 0.9, 0.86), 0.4)

  shape = Shape()
  shape.lathe([(0.025, 0.0), (0.027, 0.004), (0.0333, 0.1), (0.0335, 0.104)],
              lambda band, side: drink_top if band == 2 else drink, n=12)
  shape.lathe([(0.0335, 0.104), (0.0348, 0.122), (0.0332, 0.122), (0.0322, 0.104)], glass, n=12, caps=(False, False))
  shape.lathe([(0.0275, -0.004), (0.0275, 0.0)], glass, n=12)
  # The lime wheel stands on the rim, cut to sit over the glass.
  at = Matrix.Translation((0.03, -0.004, 0.122)) @ Matrix.Rotation(math.radians(90), 4, "X")
  shape.lathe([(0.017, -0.0025), (0.017, 0.0025)], lambda band, side: rind, n=10, at=at, caps=(False, False))
  shape.lathe([(0.0158, -0.0026), (0.0158, 0.0026)], lambda band, side: pulp, n=10, at=at, caps=(True, True))
  path = [((-0.008 - 0.0026 * i, 0.004, 0.03 + 0.0145 * i), 0.0028, 0.0028) for i in range(11)]
  shape.tube(path, lambda band, side: straw if band % 2 == 0 else straw_white, n=6)
  return shape.finish("papelon")


def build_holy_water():
  """The plastic Virgin-blue bottle every chapel keeps: holy water behind a cross label and a screw cap."""
  water = material("holy_water", (0.55, 0.75, 0.9), 0.1)
  label = material("holy_label", (0.92, 0.9, 0.82), 0.6)
  blue = material("holy_cap", CHAPEL_BLUE, 0.4)
  cross = material("holy_cross", CHAPEL_BLUE_DARK, 0.5)

  shape = Shape()
  shape.lathe([
    (0.019, 0.0), (0.022, 0.003), (0.0225, 0.02), (0.0225, 0.065), (0.02, 0.08), (0.011, 0.094), (0.0085, 0.1),
  ], lambda band, side: label if band in (2,) else water, n=12)
  shape.lathe([(0.0105, 0.1), (0.0105, 0.116), (0.009, 0.118)], blue, n=10)
  # The cross on the label, toward the camera.
  shape.box((-0.0018, -0.0235, 0.03), (0.0018, -0.0225, 0.058), cross)
  shape.box((-0.009, -0.0235, 0.046), (0.009, -0.0225, 0.0495), cross)
  return shape.finish("holy_water")


def figure(canvas, x, ground, height, tone, width_share=0.2):
  canvas.stroke([(x, ground - height * 0.72), (x, ground - height * 0.08)], height * width_share, tone)
  canvas.circle(x, ground - height * 0.9, height * 0.1, tone)


def paint_photo():
  """Five people in front of a house, faded to sepia. The father's side of it is worn pale."""
  width, height = 560, 400
  canvas = Canvas(width, height, (0.94, 0.9, 0.8))
  sky = (0.74, 0.63, 0.46)
  canvas.rect(22, 22, width - 22, height - 22, sky)
  canvas.polygon([(22, 216), (130, 112), (214, 172), (330, 96), (440, 168), (538, 128), (538, 300), (22, 300)], (0.58, 0.47, 0.32))
  canvas.rect(22, 268, width - 22, 378, (0.46, 0.35, 0.23))
  canvas.rect(58, 150, 246, 300, (0.66, 0.55, 0.38))
  canvas.polygon([(42, 156), (152, 104), (262, 156)], (0.34, 0.24, 0.16))
  canvas.rect(128, 206, 176, 300, (0.28, 0.2, 0.13))
  dark = (0.2, 0.14, 0.1)
  mid = (0.31, 0.22, 0.15)
  shirt = (0.86, 0.78, 0.62)
  figure(canvas, 262, 342, 196, dark)
  figure(canvas, 330, 342, 178, mid)
  figure(canvas, 396, 342, 142, shirt)
  figure(canvas, 448, 342, 104, dark, 0.26)
  figure(canvas, 298, 342, 88, shirt, 0.28)
  noise_mask = np.exp(-((canvas.x - 262) / 90.0) ** 2) * np.exp(-((canvas.y - 170) / 120.0) ** 2)
  canvas.blend(noise_mask * 0.45, sky)
  canvas.age(17, 0.5)
  canvas.stroke([(300, 0), (292, 180), (306, 400)], 3, (0.94, 0.9, 0.8), 0.7)
  return canvas.rgb


def build_photo():
  front = material("photo_front", image=image_from("photo_front", paint_photo()))
  back = material("photo_back", (0.86, 0.82, 0.71))
  shape = Shape()
  # Folded down the middle once and kept in a wallet: the crease is the shape.
  paper_sheet(shape, 0.14, 0.1, 6, 4, lambda x, z: 0.007 * abs(x) / 0.07 - 0.0028 * max(0.0, (x - z) / 0.1) ** 2, front, back, torn=(5, 0))
  return shape.finish("family_photo")


def coin(shape, at, face, edge, mark):
  """A locha, far wider than a real coin so it reads at the game's camera."""
  shape.lathe([(0.05, 0.0), (0.05, 0.01), (0.042, 0.012), (0.04, 0.0103)], lambda band, side: edge if band == 0 else face, n=8, at=at)
  star = [(0.0, 0.0, 0.0108)]
  for k in range(10):
    reach = 0.031 if k % 2 == 0 else 0.0125
    star.append((reach * math.cos(math.tau * k / 10), reach * math.sin(math.tau * k / 10), 0.0108))
  shape.add(star, [(0, k + 1, (k + 1) % 10 + 1) for k in range(10)], mark, at=at)


def coin_stack(shape, x, y, levels, face, edge, mark):
  for level in range(levels):
    twist = Matrix.Rotation(level * 1.1, 4, "Z")
    shift = Matrix.Translation((x + 0.004 * math.sin(level * 2.3), y + 0.004 * math.cos(level * 1.7), level * 0.0124))
    coin(shape, shift @ twist, face, edge, mark)


def coin_materials():
  return (
    material("coin", SILVER, 0.35, glow=0.04),
    material("coin_edge", SILVER_DARK, 0.45),
    material("coin_mark", (0.86, 0.72, 0.36), 0.3, glow=0.08),
  )


def blot(radius, seed, points):
  rng = random.Random(seed)
  outline = []
  for k in range(points):
    angle = math.tau * k / points
    reach = radius * rng.uniform(0.58, 1.08)
    outline.append((math.cos(angle) * reach, math.sin(angle) * reach * 0.82))
  return outline


def flat_outline(shape, outline, center, height, mat, grow=1.0):
  cx, cy = center
  verts = [(cx + x * grow, cy + y * grow, height) for x, y in outline]
  shape.add(verts, [tuple(range(len(verts)))], mat)


def build_stain(coins):
  """What a death leaves on the asphalt: a tar blot with a pale rim and the lost coins in it."""
  tar = material("stain_tar", TAR, 0.2)
  tar_light = material("stain_sheen", TAR_LIGHT, 0.2)
  rim = material("stain_rim", SOUL_GLOW, 0.6, glow=0.6)
  shape = Shape()
  outline = blot(0.62, 58, 16)
  flat_outline(shape, outline, (0, 0), 0.004, rim, 1.06)
  flat_outline(shape, outline, (0, 0), 0.008, tar)
  flat_outline(shape, blot(0.3, 7, 10), (0.1, -0.08), 0.011, tar_light)
  for center, radius, seed in (((0.72, 0.25), 0.07, 3), ((-0.68, -0.34), 0.09, 4), ((-0.44, 0.58), 0.05, 5)):
    drop = blot(radius, seed, 7)
    flat_outline(shape, drop, center, 0.004, rim, 1.2)
    flat_outline(shape, drop, center, 0.008, tar)

  face, edge, mark = coins
  coin_stack(shape, 0.0, 0.0, 4, face, edge, mark)
  coin_stack(shape, -0.14, 0.1, 2, face, edge, mark)
  for x, y, turn in ((0.22, -0.13, 0.4), (-0.2, -0.22, 1.2), (0.26, 0.2, 2.2), (-0.36, 0.05, 0.9), (0.05, 0.3, 1.8)):
    coin(shape, Matrix.Translation((x, y, 0.009)) @ Matrix.Rotation(turn, 4, "Z"), face, edge, mark)
  coin(shape, Matrix.Translation((0.13, 0.03, 0.05)) @ Matrix.Rotation(1.1, 4, "X"), face, edge, mark)
  return shape.finish("lost_lochas")


def build_lochas_icon(coins):
  shape = Shape()
  face, edge, mark = coins
  coin_stack(shape, 0.0, 0.0, 6, face, edge, mark)
  coin(shape, Matrix.Translation((0.075, -0.052, 0.058)) @ Matrix.Rotation(1.3, 4, "X"), face, edge, mark)
  return shape.finish("lochas")


def scaled_arch(points, grow):
  """Pushes the opening outward from the arch's center, for the painted band around it."""
  center = Vector((0, 1.55))
  return [center + (Vector(point) - center) * grow for point in points]


def build_chapel():
  """A roadside chapel in the avenue: whitewashed block, blue arch, tin roof, candles still lit.

  Faces -Y with its base on the origin. The solid part stays within 1.15 m of the origin toward
  the front, because the player respawns 1.6 m in front of it.
  """
  plaster = material("plaster", PLASTER)
  dirty = material("plaster_dirty", PLASTER_DIRTY)
  stone = material("chapel_stone", (0.48, 0.46, 0.43))
  stone_light = material("chapel_step", (0.6, 0.58, 0.54))
  blue = material("chapel_blue", CHAPEL_BLUE)
  niche = material("chapel_niche", CHAPEL_BLUE_DARK)
  brick = material("chapel_brick", BRICK)
  brick_dark = material("chapel_brick_dark", (0.34, 0.2, 0.14))
  tin = material("chapel_tin", TIN, 0.5)
  tin_dark = material("chapel_tin_dark", TIN_DARK, 0.5)
  rust = material("chapel_rust", RUST)
  rust_light = material("chapel_rust_light", (0.66, 0.3, 0.1))
  iron = material("chapel_iron", IRON, 0.5)
  cloth = material("chapel_cloth", (0.93, 0.91, 0.84))
  red = material("chapel_red", (0.62, 0.1, 0.09))
  robe = material("chapel_robe", (0.3, 0.46, 0.72), 0.6)
  robe_dark = material("chapel_robe_dark", (0.17, 0.27, 0.48), 0.6)
  skin = material("chapel_skin", (0.74, 0.56, 0.42), 0.6)
  gold = material("chapel_gold", BRASS, 0.35, glow=0.5)
  wax = material("chapel_wax", WAX, 0.6)
  flame_tip = material("chapel_flame", FLAME, glow=4.0)
  flame_core = material("chapel_flame_core", FLAME_CORE, glow=6.0)
  leaf = material("chapel_leaf", LEAF)
  leaf_light = material("chapel_leaf_light", LEAF_LIGHT)
  can = material("chapel_can", TIN_DARK, 0.5)

  floor, spring, radius, eave, peak, half = 0.24, 1.55, 0.55, 2.1, 2.8, 0.95
  front, back, niche_back = -0.8, 0.8, -0.22
  opening = [(-radius, floor)]
  opening += [(radius * math.cos(math.pi - math.pi * k / 8), spring + radius * math.sin(math.pi * k / 8)) for k in range(9)]
  opening += [(radius, floor)]
  outer = [(-half, floor), (-half, spring), (-half, eave), (-0.62, 2.33), (-0.31, 2.57), (0, peak)]
  outer += [(-x, z) for x, z in reversed(outer[:-1])]

  shape = Shape()
  shape.box((-1.25, -1.15, 0.0), (1.25, 0.95, 0.12), stone)
  shape.box((-1.08, -0.98, 0.12), (1.08, 0.88, 0.24), stone_light)

  verts = [(x, front, z) for x, z in outer + opening]
  count = len(opening)
  faces = [(k, k + 1, count + k + 1, count + k) for k in range(count - 1)]
  shape.add(verts, faces, [dirty if k in (0, 9) else plaster for k in range(count - 1)])
  shape.loft([[(x, y, z) for x, z in outer] for y in (front, back)], lambda band, side: dirty if side in (1, 8) else plaster, caps=(False, True))
  # The wall's own bottom edge is hidden by the steps, so the outline only needs to read as closed.
  shape.loft([[(x, y, z) for x, z in opening] for y in (front, niche_back)], niche, caps=(False, True))

  # Painted band around the arch, a touch proud of the wall.
  band = opening[1:-1]
  ring_path = [((-radius - 0.075, front - 0.015, floor), 0.05, 0.075)]
  ring_path += [((p.x, front - 0.015, p.y), 0.05, 0.075) for p in scaled_arch(band, 1.14)]
  ring_path += [((radius + 0.075, front - 0.015, floor), 0.05, 0.075)]
  shape.tube(ring_path, blue, n=4, side=(0, 1, 0))
  shape.box((-0.09, front - 0.075, 2.03), (0.09, front + 0.02, 2.27), plaster)

  for side in (-1, 1):
    shape.box((side * half - 0.09, front - 0.04, floor), (side * half + 0.09, front + 0.1, eave), dirty)
    shape.box((side * half - 0.1, front - 0.06, floor), (side * half + 0.1, front + 0.12, 0.52), blue)
    shape.box((side * half - 0.015, front + 0.3, floor), (side * half + 0.015, back - 0.3, 0.72), niche if side > 0 else blue)
  shape.tube([((-1.06, front - 0.03, 2.04), 0.05, 0.07), ((0, front - 0.03, 2.87), 0.05, 0.07), ((1.06, front - 0.03, 2.04), 0.05, 0.07)], plaster, n=4, side=(0, 1, 0))

  # Plaster fallen off: the bricks show through in three places.
  for (x0, z0, wide, tall), y in (((-0.86, 1.12, 0.22, 0.34), front - 0.006), ((0.68, 0.62, 0.17, 0.26), front - 0.006)):
    shape.extrude([(x0, z0), (x0 + wide, z0 + 0.03), (x0 + wide - 0.03, z0 + tall), (x0 + 0.05, z0 + tall - 0.04)], y, y + 0.01, brick)
    for row in range(1, 3):
      shape.box((x0 + 0.03, y - 0.002, z0 + row * tall * 0.3), (x0 + wide - 0.05, y + 0.002, z0 + row * tall * 0.3 + 0.012), brick_dark)
  shape.box((half + 0.0, -0.2, 1.22), (half + 0.012, 0.28, 1.56), brick)

  # Corrugated tin, one sheet per side, with its low edge eaten away.
  sheets = 9
  for side in (-1, 1):
    rows = 3
    verts = []
    for row in range(rows + 1):
      share = row / rows
      for k in range(sheets * 2 + 1):
        y = -1.03 + 2.06 * k / (sheets * 2)
        lift = 0.018 if k % 2 else 0.0
        verts.append((side * 1.18 * (1 - share), y, 1.93 + 0.98 * share + lift))
    faces = []
    mats = []
    width = sheets * 2 + 1
    for row in range(rows):
      for k in range(sheets * 2):
        faces.append((row * width + k, row * width + k + 1, (row + 1) * width + k + 1, (row + 1) * width + k))
        sheet = k // 2
        if row == 0 and (sheet + side) % 3 != 1:
          mats.append(rust_light if k % 2 else rust)
        elif (sheet * 3 + row + side) % 7 == 0:
          mats.append(rust)
        else:
          mats.append(tin_dark if k % 2 else tin)
    shape.add(verts, faces, mats)
  shape.tube([((0, -1.05, 2.92), 0.06, 0.04), ((0, 1.05, 2.92), 0.06, 0.04)], tin_dark, n=4, side=(1, 0, 0))

  shape.box((-0.035, -0.84, 2.87), (0.035, -0.77, 3.5), iron)
  shape.box((-0.2, -0.84, 3.2), (0.2, -0.77, 3.27), iron)

  # The altar inside: a cloth on a ledge, the Virgin, and what people left her.
  shape.box((-0.52, -0.74, floor), (0.52, niche_back, 0.8), plaster)
  shape.box((-0.53, -0.75, 0.8), (0.53, niche_back, 0.835), cloth)
  fringe = [(-0.53, 0.8)]
  for k in range(6):
    fringe += [(-0.53 + (k + 0.5) * 0.1767, 0.66), (-0.53 + (k + 1) * 0.1767, 0.8)]
  shape.extrude(fringe, -0.76, -0.75, red)
  shape.box((-0.17, -0.5, 0.835), (0.17, -0.3, 0.9), plaster)
  at = Matrix.Translation((0, -0.4, 0.9))
  shape.lathe([(0.13, 0.0), (0.135, 0.09), (0.115, 0.28), (0.082, 0.47), (0.095, 0.56), (0.07, 0.61), (0.03, 0.64)], lambda band, side: robe_dark if band in (0, 3) or side % 3 == 0 else robe, n=8, at=at)
  shape.lathe([(0.03, 0.62), (0.058, 0.665), (0.052, 0.71), (0.02, 0.74)], skin, n=6, at=at)
  shape.lathe([(0.065, 0.62), (0.076, 0.67), (0.062, 0.735), (0.022, 0.762)], robe, n=6, at=Matrix.Translation((0, -0.387, 0.9)))
  halo = [((0.115 * math.cos(math.tau * k / 8), -0.34, 1.55 + 0.115 * math.sin(math.tau * k / 8)), 0.012, 0.012) for k in range(9)]
  shape.tube(halo, gold, n=4)

  rng = random.Random(58)
  for x, y, tall in ((-0.42, -0.62, 0.1), (-0.3, -0.68, 0.16), (-0.2, -0.61, 0.07), (0.22, -0.63, 0.12), (0.33, -0.69, 0.08), (0.43, -0.6, 0.17)):
    at = Matrix.Translation((x, y, 0.835))
    shape.lathe([(0.026, 0.0), (0.027, tall * 0.7), (0.024, tall), (0.016, tall)], wax, n=6, at=at)
    flame(shape, x, y, 0.835 + tall, 0.075, flame_core, flame_tip, n=4)
  for x, y in ((-0.43, -0.34), (0.43, -0.34)):
    at = Matrix.Translation((x, y, 0.835))
    shape.lathe([(0.042, 0.0), (0.042, 0.13), (0.036, 0.13)], can, n=7, at=at)
    for k in range(5):
      lean = (rng.uniform(-0.055, 0.055), rng.uniform(-0.04, 0.04))
      tip = Vector((x + lean[0], y + lean[1], 1.09 + k * 0.02))
      shape.tube([((x, y, 0.95), 0.004, 0.004), (tip, 0.003, 0.003)], leaf, n=3)
      turn = rng.uniform(0.0, math.tau)
      petals = [tip + Vector((0.038 * math.cos(turn + j * 2.1), 0.038 * math.sin(turn + j * 2.1), 0.01 * j)) for j in range(3)]
      shape.add(petals + [tip + Vector((0, 0, 0.03))], [(0, 1, 3), (1, 2, 3), (2, 0, 3)], red)

  # Thank-you plaques beside the arch, each laid by someone different.
  for x, z, wide in ((-0.79, 1.68, 0.11), (-0.77, 1.86, 0.08), (0.76, 1.72, 0.1), (0.78, 1.53, 0.08), (0.77, 1.38, 0.09), (-0.78, 0.92, 0.09)):
    shape.box((x - wide, front - 0.02, z - 0.06), (x + wide, front + 0.01, z + 0.06), stone_light)
    shape.box((x - wide * 0.7, front - 0.024, z - 0.008), (x + wide * 0.7, front - 0.018, z + 0.012), iron)

  # Ivy climbing the left corner, in the same loose triangles as the avenue's.
  for k in range(26):
    z = rng.uniform(0.24, 1.0 + 1.2 * rng.random() ** 2)
    center = Vector((-half - 0.1 + rng.uniform(-0.03, 0.34) * (1.2 - z / 2.2), front - 0.075 + rng.uniform(0.0, 0.03), z))
    turn = rng.uniform(0.0, math.tau)
    size = rng.uniform(0.07, 0.13)
    points = [center + Vector((size * math.cos(turn + j * 2.2), rng.uniform(-0.02, 0.02), size * math.sin(turn + j * 2.2))) for j in range(3)]
    shape.add(points, [(0, 1, 2)], leaf_light if k % 3 == 0 else leaf)
  return shape.finish("chapel")


def turn(x=0.0, y=0.0, z=0.0):
  return (
    Matrix.Rotation(math.radians(y), 4, "Y")
    @ Matrix.Rotation(math.radians(x), 4, "X")
    @ Matrix.Rotation(math.radians(z), 4, "Z")
  )


def setup_render():
  scene = bpy.context.scene
  scene.render.engine = "CYCLES"
  scene.cycles.samples = 96
  scene.cycles.use_denoising = False
  scene.render.film_transparent = True
  scene.render.resolution_x = RENDER_SIZE
  scene.render.resolution_y = RENDER_SIZE
  scene.render.image_settings.file_format = "PNG"
  scene.render.image_settings.color_mode = "RGBA"
  scene.view_settings.view_transform = "Standard"
  scene.view_settings.look = "None"

  world = bpy.data.worlds.new("icon_world")
  world.use_nodes = True
  world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.42, 0.45, 0.52, 1)
  world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.75
  scene.world = world

  for name, energy, rotation, color in (
    ("key", 3.2, (60, 0, -35), (1.0, 0.95, 0.86)),
    ("fill", 0.9, (75, 0, 50), (0.72, 0.82, 1.0)),
    ("rim", 2.2, (-65, 0, 18), (0.85, 0.92, 1.0)),
  ):
    data = bpy.data.lights.new(name, "SUN")
    data.energy = energy
    data.color = color
    data.angle = math.radians(14)
    sun = bpy.data.objects.new(name, data)
    sun.rotation_euler = tuple(math.radians(value) for value in rotation)
    scene.collection.objects.link(sun)

  data = bpy.data.cameras.new("icon_camera")
  data.type = "ORTHO"
  camera = bpy.data.objects.new("icon_camera", data)
  camera.location = (0, -30, 0)
  camera.rotation_euler = (math.radians(90), 0, 0)
  data.clip_end = 100.0
  scene.collection.objects.link(camera)
  scene.camera = camera
  return camera


def dilate(alpha, steps):
  grown = alpha
  for _ in range(steps):
    neighbors = [grown]
    for axis in (0, 1):
      for shift in (-1, 1):
        neighbors.append(np.roll(grown, shift, axis))
    grown = np.maximum.reduce(neighbors)
  return grown


def shrink(pixels, factor):
  height, width, channels = pixels.shape
  return pixels.reshape(height // factor, factor, width // factor, factor, channels).mean(axis=(1, 3))


def finish_icon(rendered, path):
  """Adds the contour that lifts an icon off the dark UI, then halves the render for clean edges."""
  source = bpy.data.images.load(rendered)
  source.colorspace_settings.name = "Non-Color"
  size = source.size[0]
  pixels = np.empty(size * size * 4, dtype=np.float32)
  source.pixels.foreach_get(pixels)
  bpy.data.images.remove(source)
  pixels = pixels.reshape(size, size, 4).astype(float)

  alpha = pixels[..., 3]
  ink = dilate(alpha, OUTLINE_WIDTH)
  glow = dilate(ink, 2)
  under = glow * 0.55
  color = np.ones((size, size, 3)) * np.array(OUTLINE_GLOW)
  color = color * (1 - ink[..., None]) + np.array(OUTLINE_INK) * ink[..., None]
  under = np.maximum(under, ink)
  over = alpha[..., None]
  merged = pixels[..., :3] * over + color * under[..., None] * (1 - over)
  total = alpha + under * (1 - alpha)
  premultiplied = np.dstack((merged, total))
  small = shrink(premultiplied, RENDER_SIZE // ICON_SIZE)
  covered = np.maximum(small[..., 3:], 1e-5)
  small[..., :3] = np.clip(small[..., :3] / covered, 0.0, 1.0)

  icon = bpy.data.images.new("icon", ICON_SIZE, ICON_SIZE, alpha=True)
  icon.colorspace_settings.name = "Non-Color"
  icon.pixels.foreach_set(small.ravel().astype(np.float32))
  icon.filepath_raw = path
  icon.file_format = "PNG"
  icon.save()
  bpy.data.images.remove(icon)


def render_icon(obj, pose, camera, others):
  scene = bpy.context.scene
  for other in others:
    other.hide_render = other is not obj
  points = [pose @ Vector(corner) for corner in (v.co for v in obj.data.vertices)]
  low = Vector((min(p.x for p in points), 0, min(p.z for p in points)))
  high = Vector((max(p.x for p in points), 0, max(p.z for p in points)))
  obj.matrix_world = Matrix.Translation(-(low + high) * 0.5) @ pose
  camera.data.ortho_scale = max(high.x - low.x, high.z - low.z) * ICON_MARGIN
  rendered = os.path.join(bpy.app.tempdir, obj.name + ".png")
  scene.render.filepath = rendered
  bpy.ops.render.render(write_still=True)
  finish_icon(rendered, os.path.join(ICONS, obj.name + ".png"))
  obj.matrix_world = Matrix.Identity(4)


def export_glb(obj, others):
  for other in others:
    other.select_set(other is obj)
  bpy.context.view_layer.objects.active = obj
  bpy.ops.export_scene.gltf(
    filepath=os.path.join(MODELS, obj.name + ".glb"),
    export_format="GLB",
    use_selection=True,
    export_apply=True,
    export_extras=False,
  )


def main():
  bpy.ops.wm.read_factory_settings(use_empty=True)
  os.makedirs(MODELS, exist_ok=True)
  os.makedirs(ICONS, exist_ok=True)

  coins = coin_materials()
  icon_only = build_lochas_icon(coins)
  # (object, pose for its icon)
  props = [
    (build_coffee(), turn(x=14, z=-24)),
    (build_candle(), turn(y=-16, x=6)),
    (build_vinyl(), turn(y=-8, z=-14, x=6)),
    (build_card(), turn(y=8, z=-14, x=4)),
    (build_tile(), turn(y=-20, z=-22, x=5)),
    (build_photo(), turn(y=6, z=-12, x=4)),
    (build_hallaca(), turn(x=34, z=-22)),
    (build_papelon(), turn(x=8, z=-18)),
    (build_holy_water(), turn(x=6, z=-16)),
    (machete.build(), turn(y=-54, z=-86, x=2)),
    (build_chapel(), turn(x=6, z=-24)),
  ]
  stain = build_stain(coins) # Named on screen by the coin icon: the blot alone says nothing at HUD size.
  objects = [obj for obj, _ in props] + [stain, icon_only]
  for obj in objects[:-1]:
    export_glb(obj, objects)

  camera = setup_render()
  for obj, pose in props:
    render_icon(obj, pose, camera, objects)
  render_icon(icon_only, turn(x=20, z=-18), camera, objects)

  # Only the blend spreads them out, for browsing; the exports above all sit on the origin.
  for index, obj in enumerate(objects):
    obj.location.x = index * 3.2
  bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)


main()
