# Builds what the opening drives past, from the avenue's own parts: Caracas in 2018, still lived in
# but already falling apart. Each piece is its own model under game/models/environments/drive/,
# and opening.tscn lines them up and slides them past the car.
#   blender --background --python art/environments/build_drive.py
# The street runs along Y with its center on x = 0 and the right sidewalk at +x, so in Godot the
# right side stays +x and Godot z is -y. Buildings are made for the right side; the scene turns
# them half a turn for the left.
import math
import os
import random
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "characters"))
sys.path.insert(0, os.path.join(HERE, "..", "props"))

import build_avenue as av
from build_avenue import Layer, box, tube
from build_luis import PersonRig, build_person, merged, rig_person

OUT = os.path.join(HERE, "..", "..", "game", "models", "environments", "drive")
SEGMENT = 40.0

# Faces turned away from every point the cameras can be, in the car on either lane and looking
# both ways down the street, are dropped like the avenue's.
av.PLAY_CORNERS = [Vector((x, y, z)) for x in (-4.0, 4.0) for y in (-160.0, 160.0) for z in (0.4, 3.0)]

av.MATERIALS.update({
  "paint_pink": ((0.86, 0.62, 0.62), 0.9, 0.0),
  "paint_blue": ((0.56, 0.7, 0.8), 0.9, 0.0),
  "paint_yellow": ((0.88, 0.8, 0.52), 0.9, 0.0),
  "paint_green": ((0.6, 0.76, 0.58), 0.9, 0.0),
  "tile": ((0.7, 0.68, 0.62), 0.6, 0.0),
  "fabric": ((0.3, 0.38, 0.55), 1.0, 0.0),
  "sheet": ((0.85, 0.83, 0.78), 1.0, 0.0),
  "canvas": ((0.1, 0.1, 0.12), 0.9, 0.0),
  "lamp_glow": ((1.0, 0.85, 0.55), 0.5, 0.0),
  "suitcase": ((0.15, 0.2, 0.32), 0.6, 0.0),
})


# --- People -----------------------------------------------------------------------------------
SKINS = [(0.88, 0.74, 0.62), (0.8, 0.62, 0.48), (0.68, 0.48, 0.34), (0.52, 0.35, 0.24), (0.38, 0.25, 0.18)]
HAIRS = [(0.06, 0.05, 0.05), (0.16, 0.1, 0.06), (0.27, 0.17, 0.1), (0.5, 0.48, 0.46)]
SHIRTS = [(0.78, 0.78, 0.74), (0.2, 0.3, 0.55), (0.6, 0.15, 0.15), (0.86, 0.7, 0.2), (0.42, 0.08, 0.12),
          (0.3, 0.48, 0.35), (0.15, 0.15, 0.17), (0.88, 0.56, 0.6), (0.55, 0.6, 0.65)]
PANTS = [(0.18, 0.24, 0.38), (0.12, 0.14, 0.2), (0.3, 0.3, 0.32), (0.55, 0.48, 0.32), (0.1, 0.1, 0.1)]
SHOES = [(0.1, 0.1, 0.1), (0.82, 0.82, 0.8), (0.35, 0.22, 0.12)]

STAND = {
  "hips": (0, 0, 2), "spine": (-2, 0, 0), "chest": (2, 0, -2), "head": (4, 0, 0),
  "upper_arm_l": (8, 0, 32), "lower_arm_l": (-12, 0, 0), "upper_arm_r": (8, 0, -32), "lower_arm_r": (-12, 0, 0),
  "curl_l": 35.0, "curl_r": 35.0,
}
POSES = {
  "stand": STAND,
  "weight": merged(STAND, {"hips": (0, 6, 5), "chest": (2, -6, -4), "head": (2, 8, 2), "upper_leg_r": (-4, 0, -4), "lower_leg_r": (6, 0, 0)}),
  "umbrella": merged(STAND, {"wrist_r": (-0.06, 0.24, 1.14), "pole_r": (-0.7, 0.1, -0.7), "hand_r": (0, 0, -80), "curl_r": 80.0}),
  "crossed": merged(STAND, {"wrist_l": (-0.1, 0.17, 1.13), "wrist_r": (0.1, 0.19, 1.1), "pole_l": (0.8, 0.2, -0.5), "pole_r": (-0.8, 0.2, -0.5),
                            "hand_l": (0, 0, 30), "hand_r": (0, 0, -30)}),
  "phone": merged(STAND, {"wrist_r": (-0.06, 0.3, 1.13), "pole_r": (-0.7, 0.0, -0.7), "hand_r": (-50, 0, -40), "curl_r": 50.0,
                          "wrist_l": (0.04, 0.28, 1.1), "pole_l": (0.7, 0.0, -0.7), "hand_l": (-50, 0, 40), "head": (24, 0, 0)}),
  "walk": merged(STAND, {"upper_leg_l": (-16, 0, 0), "lower_leg_l": (14, 0, 0), "upper_leg_r": (14, 0, 0), "lower_leg_r": (22, 0, 0),
                         "foot_r": (-10, 0, 0), "upper_arm_l": (-14, 0, 30), "upper_arm_r": (18, 0, -30), "chest": (6, 4, 0)}),
  "carry": merged(STAND, {"upper_leg_l": (12, 0, 0), "lower_leg_l": (20, 0, 0), "upper_leg_r": (-14, 0, 0), "lower_leg_r": (10, 0, 0),
                          "upper_arm_l": (0, 0, 14), "lower_arm_l": (0, 0, 0), "curl_l": 80.0, "chest": (6, -4, -4)}),
}


def look_for(rng, pack=False, style=None):
  shirt = rng.choice(SHIRTS)
  pants = rng.choice(PANTS)
  return {
    "skin": rng.choice(SKINS),
    "hair": rng.choice(HAIRS),
    "shirt": shirt,
    "trim": tuple(c * 0.75 for c in shirt),
    "pants": pants,
    "pants_dark": tuple(c * 0.8 for c in pants),
    "shoes": rng.choice(SHOES),
    "sole": (0.12, 0.12, 0.12),
    "pack": rng.choice([(0.2, 0.24, 0.35), (0.12, 0.12, 0.13), (0.5, 0.25, 0.18)]),
    "strap": (0.1, 0.1, 0.1),
    "cap": rng.choice(SHIRTS),
    "beard": rng.random() < 0.3,
    "hairstyle": style or rng.choice(["short", "short", "swept", "long", "long", "cap"]),
    "backpack": pack,
    "build": rng.uniform(0.92, 1.12),
    "simple": True,
  }


def umbrella(at):
  """A black umbrella over the hand at 'at'."""
  layer = Layer("umbrella")
  top = at + Vector((0, 0, 0.95))
  tube(layer, [(tuple(at - Vector((0, 0, 0.08))), 0.012), (tuple(top + Vector((0, 0, 0.05))), 0.01)], "iron", n=4)
  rim = [top + Vector((math.cos(a) * 0.55, math.sin(a) * 0.55, -0.22)) for a in (math.tau * k / 8 for k in range(8))]
  peak = top + Vector((0, 0, 0.04))
  for a, b in zip(rim, rim[1:] + rim[:1]):
    layer.add([peak, a, b], [(0, 1, 2)], "canvas", True)
  return layer.build_chunk("umbrella", list(range(len(layer.faces))))


def person(rng, pose, at, yaw, pack=False, style=None, umbrella_up=False):
  """A posed, frozen person: built and rigged like Luis, then the pose is applied for good."""
  look = look_for(rng, pack, style)
  name = f"person_{rng.randrange(10**6)}"
  armature, objects = rig_person(name, build_person(look, name))
  rig = PersonRig(armature)
  rig.solve(POSES[pose])
  for bone, (location, rotation) in rig.local.items():
    pose_bone = armature.pose.bones[bone]
    pose_bone.rotation_mode = "QUATERNION"
    pose_bone.rotation_quaternion = rotation
    if bone in ("root", "hips"):
      pose_bone.location = location
  bpy.context.view_layer.update()
  frozen = []
  depsgraph = bpy.context.evaluated_depsgraph_get()
  for obj in objects:
    mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph))
    still = bpy.data.objects.new(obj.name + "_still", mesh)
    bpy.context.scene.collection.objects.link(still)
    frozen.append(still)
  if umbrella_up:
    hand = rig.world["hand_r"].translation
    frozen.append(umbrella(Vector(hand)))
  for obj in objects + [armature]:
    bpy.data.objects.remove(obj)
  turn = Vector((math.cos(yaw), math.sin(yaw)))
  for obj in frozen:
    for v in obj.data.vertices:
      x, y = v.co.x, v.co.y
      v.co.x = at[0] + x * turn.x - y * turn.y
      v.co.y = at[1] + x * turn.y + y * turn.x
      v.co.z += at[2] if len(at) > 2 else 0.0
    obj.data.update()
  for obj in frozen:
    to_vertex_colors(obj)
  return frozen


def to_vertex_colors(obj):
  """Material colors into the vertices and the avenue's matte master instead, so a crowd is
  one draw call like the rest of the street."""
  mesh = obj.data
  if mesh.color_attributes.get("color"):
    return
  layer = mesh.color_attributes.new("color", "FLOAT_COLOR", "CORNER")
  for polygon in mesh.polygons:
    mat = mesh.materials[polygon.material_index]
    color = [c ** (1 / 2.2) for c in mat.diffuse_color[:3]]
    for loop in polygon.loop_indices:
      layer.data[loop].color = (*color, 1.0)
  mesh.materials.clear()
  for master in av.MASTER_NAMES:
    mesh.materials.append(av.material(master))
  for polygon in mesh.polygons:
    polygon.material_index = 0
  mesh.color_attributes.active_color_index = 0
  mesh.color_attributes.render_color_index = 0


def join(objects, name):
  objects = [o for o in objects if o is not None]
  with bpy.context.temp_override(active_object=objects[0], selected_editable_objects=objects):
    bpy.ops.object.join()
  objects[0].name = name
  return objects[0]


# --- Street -----------------------------------------------------------------------------------
def lamp(layer, x, y, side):
  """Concrete street lamp leaning its head over the road."""
  tube(layer, [((x, y, 0.15), 0.12), ((x, y, 5.5), 0.08), ((x, y, 7.4), 0.06)], "pole_concrete", n=6)
  tube(layer, [((x, y, 7.2), 0.04), ((x - side * 1.0, y, 7.6), 0.04), ((x - side * 1.6, y, 7.5), 0.04)], "iron", n=4)
  box(layer, (x - side * 1.75, y, 7.42), (0.55, 0.26, 0.12), "metal_grey")
  box(layer, (x - side * 1.75, y, 7.35), (0.4, 0.18, 0.03), "lamp_glow")


def street(variant):
  rng = av.rng
  layer = Layer(f"street_{variant}")
  half = SEGMENT / 2
  box(layer, (0, 0, -0.25), (12.0, SEGMENT, 0.5), "asphalt")
  for side in (-1, 1):
    x = side * (av.STREET_HALF + av.SIDEWALK_EDGE) / 2
    width = av.SIDEWALK_EDGE - av.STREET_HALF
    box(layer, (x, 0, 0.09), (width, SEGMENT, 0.18), "sidewalk")
    box(layer, (side * (av.STREET_HALF + 0.12), 0, 0.1), (0.26, SEGMENT, 0.2), "curb")
    y = -half
    while y < half:
      box(layer, (x, y, 0.182), (width - 0.34, 0.03, 0.01), "crack")
      y += 2.5
    for y in (-10.0, 10.0):
      lamp(layer, side * 6.5, y + (3.0 if variant == "b" else 0.0), side)
    # A tree in each of the sidewalk's planting squares, and the odd trash bag.
    for y in ((-15.0, 3.0) if variant == "a" else (-4.0, 14.0)):
      box(layer, (side * 7.2, y, 0.19), (1.2, 1.2, 0.02), "dirt")
      av.tree(layer, side * 7.2, y, rng.uniform(4.5, 6.0), rng.uniform(2.2, 3.0))
    for _ in range(rng.randint(1, 3)):
      av.clump(layer, (side * rng.uniform(8.6, 9.2), rng.uniform(-half + 1, half - 1), 0.4), (0.35, 0.3, 0.3), "trash")
  # Lane marks and wear.
  for k in range(8):
    y = -half + 2.5 + k * 5.0
    if rng.random() > 0.15:
      box(layer, (0, y, 0.012), (0.16, 2.6, 0.012), "road_paint")
    for side in (-1, 1):
      if rng.random() > 0.4:
        box(layer, (side * 3.0, y, 0.012), (0.12, 1.6, 0.012), "road_white")
  for _ in range(5):
    box(layer, (rng.uniform(-5, 5), rng.uniform(-half + 2, half - 2), 0.008), (rng.uniform(1, 2.5), rng.uniform(1.5, 4), 0.012), "asphalt_patch", (0, 0, rng.uniform(-0.1, 0.1)))
  for _ in range(2):
    av.flat_blob(layer, (rng.uniform(-5, 5), rng.uniform(-half + 2, half - 2)), (rng.uniform(1.2, 2.5), rng.uniform(1.5, 3)), "puddle", 0.03, points=12)
  # Parked cars, nose to tail along both curbs.
  for side in (-1, 1):
    for y in (-12.0, 6.0) if variant == "a" else (-2.0, 15.0):
      if rng.random() < 0.7:
        av.car(layer, (side * 4.9, y + rng.uniform(-1.5, 1.5), 0.0), (0, 0, rng.uniform(-0.04, 0.04) + (math.pi if side < 0 else 0)), rng.choice(("car_yellow", "car_red", "car_blue", "concrete_grey")))
  # Cables strung across the street between the lamp posts.
  av.cable(layer, (-6.5, -10.0, 7.0), (6.5, -9.0, 7.2), 0.5, 0.012)
  layer.build()


# --- Scripted pieces ------------------------------------------------------------------------
LETTERS = {
  "A": [".###.", "#...#", "#####", "#...#", "#...#"],
  "B": ["####.", "#...#", "####.", "#...#", "####."],
  "S": [".####", "#....", ".###.", "....#", "####."],
  "T": ["#####", "..#..", "..#..", "..#..", "..#.."],
  "O": [".###.", "#...#", "#...#", "#...#", ".###."],
}


def sign_text(layer, text, x, y_center, z_top, pixel, mat):
  """Block letters on a wall facing -x, read left to right from the street."""
  width = len(text) * 6 * pixel
  y = y_center + width / 2
  for char in text:
    for row, line in enumerate(LETTERS[char]):
      for col, on in enumerate(line):
        if on == "#":
          box(layer, (x, y - (col + 0.5) * pixel, z_top - (row + 0.5) * pixel), (0.05, pixel * 0.95, pixel * 0.95), mat)
    y -= 6 * pixel


def store():
  """The abasto: shutters half up, a hand-painted sign and the queue in the rain."""
  rng = random.Random(23)
  layer = Layer("store_front")
  wall = av.SIDEWALK_EDGE
  # One storey with a parapet, the sign painted on it, like most abastos.
  box(layer, (wall + 4.0, 0, 2.3), (8.0, 14.0, 4.6), "concrete_warm")
  box(layer, (wall + 0.1, 0, 4.75), (0.3, 14.2, 0.3), "concrete_stain")
  box(layer, (wall - 0.1, 0, 3.75), (0.12, 13.4, 1.5), "sign_red")
  box(layer, (wall - 0.14, 0, 3.75), (0.04, 13.0, 1.3), "sign_white")
  box(layer, (wall - 0.17, 0, 3.75), (0.04, 12.7, 1.14), "sign_red")
  sign_text(layer, "ABASTO", wall - 0.21, 0.0, 4.3, 0.2, "sign_white")
  # Closed shutters down the rest of the front, rusted at the bottom.
  for k in range(3):
    y = -5.2 + k * 3.3
    box(layer, (wall - 0.05, y, 1.45), (0.08, 3.1, 2.9), "shutter")
    for rib in range(9):
      box(layer, (wall - 0.1, y, 0.25 + rib * 0.32), (0.03, 3.1, 0.05), "iron" if rib else "rust")
  # Door at the +y end, its shutter half up over a dim, empty shop.
  box(layer, (wall - 0.15, 5.0, 1.5), (0.1, 3.0, 2.8), "window_dark")
  for k in range(5):
    box(layer, (wall - 0.25, 5.0, 2.75 - k * 0.2), (0.05, 3.0, 0.18), "shutter")
  box(layer, (wall - 0.4, 6.7, 1.2), (0.1, 0.15, 2.4), "iron")
  # A guard rope from the door, and cardboard on the wet sidewalk.
  tube(layer, [((wall - 0.4, 3.4, 1.0), 0.02), ((wall - 2.0, 3.4, 0.9), 0.02)], "sign_yellow", n=3)
  for _ in range(4):
    box(layer, (rng.uniform(7.0, 9.0), rng.uniform(-6.0, 4.0), 0.19), (0.6, 0.45, 0.01), "wood", (0, 0, rng.uniform(0, 1)))
  layer.build()
  people = []
  poses = ["umbrella", "stand", "phone", "crossed", "weight", "umbrella", "stand", "crossed", "phone", "weight", "umbrella", "stand"]
  for i, pose in enumerate(poses):
    y = 4.0 - i * 0.95 + rng.uniform(-0.15, 0.15)
    x = 8.3 + rng.uniform(-0.35, 0.35)
    people += person(rng, pose, (x, y, 0.18), rng.uniform(-0.35, 0.35) + math.pi, umbrella_up=pose == "umbrella")
  join(people, "queue")


def bus():
  """A bus broken down in the left lane, its roof piled with luggage, and people walking out of
  the city with everything they own."""
  rng = random.Random(31)
  layer = Layer("bus")
  av.bus(layer, (-4.4, 0.0, 0.0), (0.0, 0.05, 0.06))
  for k in range(7):
    box(layer, (-4.4 + rng.uniform(-0.6, 0.6), -3.5 + k * 1.1, 3.2 + rng.uniform(0, 0.15)), (rng.uniform(0.6, 1.0), rng.uniform(0.5, 0.9), rng.uniform(0.3, 0.5)),
        rng.choice(("suitcase", "fabric", "canvas", "wood_old")), (0, 0, rng.uniform(-0.2, 0.2)))
  av.car(layer, (-1.9, -12.0, 0.0), (0, 0, -0.3), "car_blue")
  layer.build()
  people = []
  for i in range(7):
    pose = "walk" if i % 2 else "carry"
    y = 6.0 - i * 2.3 + rng.uniform(-0.4, 0.4)
    x = -7.6 + rng.uniform(-0.6, 0.6)
    group = person(rng, pose, (x, y, 0.18), rng.uniform(-0.1, 0.1), pack=True)
    if pose == "carry":
      bag = Layer("suitcase")
      box(bag, (x + 0.28, y - 0.05, 0.45), (0.12, 0.45, 0.55), "suitcase")
      group.append(bag.build_chunk("suitcase", list(range(len(bag.faces)))))
    people += group
  join(people, "walkers")


def split_building():
  """Split by the earthquake: half a block standing, its rooms open to the street, the rest
  fallen into the sidewalk."""
  rng = random.Random(41)
  av.concrete_block(1, -9.0, -1.0, 7)
  av.brick_row_house(1, 5.0, 9.0, 5)
  layer = Layer("split")
  wall = av.SIDEWALK_EDGE
  rooms = ("paint_pink", "paint_blue", "paint_yellow", "paint_green", "sign_white", "paint_blue", "paint_pink")
  for floor in range(7):
    z = floor * 3.3 + 0.3
    sag = floor * 0.12
    # Slab broken off toward the street, the back wall still painted.
    box(layer, (wall + 6.0 + sag * 0.5, 2.0, z), (12.0 - floor * 0.6, 6.0, 0.28), "concrete_grey", (0.0, -0.04 * floor, rng.uniform(-0.03, 0.03)))
    box(layer, (wall + 11.8, 2.0, z + 1.65), (0.2, 5.8, 3.0), rooms[floor])
    box(layer, (wall + 6.0, -0.98, z + 1.65), (12.0, 0.15, 3.0), rooms[(floor + 2) % len(rooms)])
    box(layer, (wall + 6.0, 4.98, z + 1.65), (12.0, 0.15, 3.0), rooms[(floor + 4) % len(rooms)])
    for _ in range(5):
      bar_y = rng.uniform(-0.8, 4.8)
      tube(layer, [((wall + 0.3, bar_y, z), 0.02), ((wall - 0.2, bar_y + rng.uniform(-0.3, 0.3), z - rng.uniform(0.3, 0.9)), 0.015)], "rust", n=3)
    if floor in (2, 3, 4, 5):
      # What people left: a bed, a fridge, a sofa, a picture on the wall.
      if floor == 3:
        box(layer, (wall + 4.0, 3.2, z + 0.4), (2.0, 1.5, 0.5), "wood")
        box(layer, (wall + 4.0, 3.2, z + 0.7), (1.9, 1.4, 0.14), "sheet")
      if floor == 4:
        box(layer, (wall + 7.0, 4.3, z + 0.95), (0.7, 0.7, 1.7), "sign_white")
      if floor == 2:
        box(layer, (wall + 5.0, 0.6, z + 0.45), (0.9, 2.2, 0.6), "fabric")
        box(layer, (wall + 5.4, 0.6, z + 0.9), (0.2, 2.2, 0.5), "fabric")
      if floor == 5:
        box(layer, (wall + 11.6, 2.4, z + 1.9), (0.06, 0.9, 0.7), "wood")
        box(layer, (wall + 11.55, 2.4, z + 1.9), (0.04, 0.75, 0.55), "sign_yellow")
  # The fallen half, in the street.
  for _ in range(26):
    av.clump(layer, (rng.uniform(wall - 3.5, wall + 4.0), rng.uniform(-0.5, 5.0), rng.uniform(0.2, 1.4)),
             (rng.uniform(0.6, 1.6), rng.uniform(0.6, 1.6), rng.uniform(0.4, 1.0)), rng.choice(("concrete_grey", "concrete_stain", "brick_orange", "concrete_warm")))
  for _ in range(8):
    box(layer, (rng.uniform(wall - 3, wall + 3), rng.uniform(-0.5, 5.0), rng.uniform(0.6, 2.0)), (rng.uniform(2, 4), rng.uniform(0.6, 1.5), 0.25),
        "concrete_grey", (rng.uniform(-0.6, 0.6), rng.uniform(-0.6, 0.6), rng.uniform(0, 3)))
  layer.build()


# --- Export ---------------------------------------------------------------------------------
def export_piece(name, build):
  before = set(bpy.data.objects)
  av.facades.clear()
  av.solids.clear()
  av.rng.seed(hash(name) % 10000)
  build()
  new = [obj for obj in bpy.data.objects if obj not in before]
  triangles = sum(sum(len(p.vertices) - 2 for p in obj.data.polygons) for obj in new if obj.type == "MESH")
  print(f"{name}: {len(new)} objects, {triangles} triangles")
  if WRITE:
    for obj in bpy.data.objects:
      obj.select_set(obj in new)
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, name + ".glb"), export_format="GLB", use_selection=True)
    for obj in new:
      bpy.data.objects.remove(obj)
  return new


WRITE = True
# Only what the camera sees: one street tile the scene repeats under the car, and the three
# pieces the dialogue points at. The far city stays as the scene's plain blocks in the fog.
PIECES = [
  ("street", lambda: street("a")),
  ("store", store),
  ("bus", bus),
  ("split_building", split_building),
]


def main(only=None):
  if bpy.app.background:
    bpy.ops.wm.read_factory_settings(use_empty=True)
  for name, build in PIECES:
    if only is None or name in only:
      export_piece(name, build)


if __name__ == "__main__":
  main()
