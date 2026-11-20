"""Writes game/scenes/opening.tscn and game/scenes/crashed_car.tscn: the drive, the crash site and
the whole script of docs/opening.md as one AnimationPlayer timeline.
  py art/scenes/build_opening.py
Both scenes are this script's output: change them here and run it again, hand edits are lost."""
import math
import os
import random

GAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "game", "scenes")
rng = random.Random(58)


def num(v):
  s = f"{v:.4f}".rstrip("0")
  return s + "0" if s.endswith(".") else s


class Raw(str):
  """Text written into the scene as it is: resource references and dictionaries."""


def val(v):
  if isinstance(v, Raw):
    return str(v)
  if isinstance(v, bool):
    return "true" if v else "false"
  if isinstance(v, int):
    return str(v)
  if isinstance(v, float):
    return num(v)
  if isinstance(v, str):
    return '"' + v.replace('"', '\\"') + '"'
  kind, *xs = v
  return f"{kind}({', '.join(num(x) for x in xs)})"


def V3(x, y, z):
  return ("Vector3", x, y, z)


def C(r, g, b, a=1.0):
  return ("Color", r, g, b, a)


def look(frm, to):
  dx, dy, dz = (to[i] - frm[i] for i in range(3))
  return V3(math.atan2(dy, math.hypot(dx, dz)), math.atan2(-dx, -dz), 0)


class Scene:
  def __init__(self):
    self.ext = []
    self.subs = []
    self.nodes = []
    self.cache = {}

  def ext_res(self, kind, path, rid):
    self.ext.append(f'[ext_resource type="{kind}" path="{path}" id="{rid}"]')
    return Raw(f'ExtResource("{rid}")')

  def sub(self, kind, props, key=None):
    if key is not None and key in self.cache:
      return self.cache[key]
    rid = f"{kind.lower()}_{len(self.subs)}"
    lines = [f'[sub_resource type="{kind}" id="{rid}"]'] + [f"{k} = {val(v)}" for k, v in props.items()]
    self.subs.append("\n".join(lines))
    ref = Raw(f'SubResource("{rid}")')
    if key is not None:
      self.cache[key] = ref
    return ref

  def mat(self, color, glow=0.0, alpha=1.0):
    props = {"albedo_color": C(*color, alpha), "roughness": 0.9}
    if glow:
      props.update({"emission_enabled": True, "emission": C(*color), "emission_energy_multiplier": glow})
    if alpha < 1.0:
      props.update({"transparency": 1, "cull_mode": 2})
    return self.sub("StandardMaterial3D", props, ("mat", color, glow, alpha))

  def mesh(self, kind, dims, color, glow=0.0, alpha=1.0):
    m = self.mat(color, glow, alpha)
    props = dict(dims)
    props["material"] = m
    return self.sub(kind, props, (kind, tuple(sorted(dims.items())), color, glow, alpha))

  def node(self, name, kind, parent, props=None, extra=""):
    head = f'[node name="{name}"' + (f' type="{kind}"' if kind else "") + (f' parent="{parent}"' if parent is not None else "") + extra + "]"
    body = []
    for k, v in (props or {}).items():
      body.append(f"{k} = {val(v)}")
    self.nodes.append("\n".join([head] + body))
    return name if parent in (None,) else (name if parent == "." else f"{parent}/{name}")

  def box(self, name, parent, size, at, color, rot=None, glow=0.0, alpha=1.0, meta=None):
    props = {"mesh": self.mesh("BoxMesh", {"size": V3(*size)}, color, glow, alpha), "position": V3(*at)}
    if rot:
      props["rotation"] = V3(*rot)
    for k, v in (meta or {}).items():
      props[f"metadata/{k}"] = v
    return self.node(name, "MeshInstance3D", parent, props)

  def shape(self, name, parent, kind, dims, at, color, rot=None):
    props = {"mesh": self.mesh(kind, dims, color), "position": V3(*at)}
    if rot:
      props["rotation"] = V3(*rot)
    return self.node(name, "MeshInstance3D", parent, props)

  def write(self, path):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
      f.write("[gd_scene format=3]\n\n")
      for block in (self.ext, self.subs, self.nodes):
        if block:
          f.write("\n\n".join(block) + "\n\n")


# --- Palette ---------------------------------------------------------------------------------
SKIN = (0.55, 0.38, 0.27)
HAIR = (0.06, 0.05, 0.05)
LUIS_SHIRT = (0.52, 0.2, 0.14)
HERO_JACKET = (0.17, 0.19, 0.23)
INTERIOR = (0.1, 0.1, 0.11)
SEAT = (0.22, 0.16, 0.12)
DASH = (0.07, 0.07, 0.075)
PAINT = (0.62, 0.6, 0.55)
HEADLINER = (0.3, 0.29, 0.27)
STEEL = (0.62, 0.64, 0.66)
HANDLE = (0.25, 0.15, 0.08)
FACADES = [(0.72, 0.66, 0.55), (0.66, 0.5, 0.4), (0.56, 0.6, 0.58), (0.7, 0.62, 0.42), (0.5, 0.5, 0.52), (0.62, 0.45, 0.42)]


def seats(s, parent):
  for side, name in ((-1, "SeatLuis"), (1, "SeatHero")):
    x = side * 0.38
    s.box(name, parent, (0.5, 0.12, 0.5), (x, 0.45, 0.0), SEAT)
    s.box(name + "Back", parent, (0.5, 0.62, 0.12), (x, 0.8, 0.27), SEAT, rot=(-0.12, 0, 0))
    s.box(name + "Rest", parent, (0.26, 0.18, 0.1), (x, 1.15, 0.32), SEAT)
  s.box("RearSeat", parent, (1.45, 0.12, 0.5), (0, 0.45, 1.0), SEAT)
  s.box("RearSeatBack", parent, (1.45, 0.6, 0.12), (0, 0.78, 1.28), SEAT, rot=(-0.15, 0, 0))


def machete(s, parent, at, yaw, visible=True):
  m = s.node("Machete", "Node3D", parent, {"visible": visible, "position": V3(*at), "rotation": V3(0, yaw, 0)})
  s.box("Blade", m, (0.05, 0.01, 0.48), (0, 0, -0.1), STEEL)
  s.box("Handle", m, (0.04, 0.03, 0.13), (0, 0, 0.2), HANDLE)


def shell(s, parent, paint, crushed=False):
  s.box("Floor", parent, (1.66, 0.05, 2.7), (0, 0.33, 0.4), INTERIOR)
  s.box("Dashboard", parent, (1.6, 0.22, 0.35), (0, 0.84, -0.78), DASH)
  for side in (-1, 1):
    tag = "L" if side < 0 else "R"
    if not (crushed and side > 0):
      s.box("Door" + tag, parent, (0.07, 0.6, 2.4), (side * 0.83, 0.65, 0.45), paint)
    s.box("PillarA" + tag, parent, (0.06, 0.65, 0.07), (side * 0.78, 1.185, -0.625), paint, rot=(0.76, 0, 0))
    s.box("PillarB" + tag, parent, (0.07, 0.5, 0.1), (side * 0.8, 1.18, 0.45), paint)
    s.box("PillarC" + tag, parent, (0.06, 0.68, 0.08), (side * 0.78, 1.19, 1.6), paint, rot=(-0.8, 0, 0))
  s.box("Roof", parent, (1.62, 0.06, 1.75), (0, 1.43, 0.47), paint if crushed else HEADLINER, rot=(0, 0, 0.06 if crushed else 0))
  s.box("RearBody", parent, (1.8, 0.55, 0.75), (0, 0.6, 2.0), paint)
  s.box("Trunk", parent, (1.7, 0.06, 0.7), (0, 0.9, 2.0), paint)
  if crushed:
    s.box("Hood", parent, (1.7, 0.08, 1.1), (0.05, 1.0, -1.45), paint, rot=(0.4, 0.08, 0.1))
    s.box("Nose", parent, (1.9, 0.5, 0.8), (0.08, 0.55, -1.75), paint, rot=(0, 0.18, 0))
  else:
    s.box("Hood", parent, (1.7, 0.08, 1.25), (0, 0.88, -1.55), paint)
    s.box("Nose", parent, (1.8, 0.55, 1.3), (0, 0.58, -1.55), paint)


LUIS_LOCAL = (2.3, 0.0, 1.5)  # Where Luis fell, in the crashed car's frame: clear of the sidewalk plants.


# --- The crashed car, shared by the opening and the avenue ------------------------------------
MACHETE_AT = (0.02, 0.54, 0.8)   # Flat in the middle of the back seat, seen between the front ones.
MACHETE_ROT = (0, 1.2, 1.5708)


def build_crashed_car():
  s = Scene()
  model = s.ext_res("PackedScene", "res://models/props/car_crashed.glb", "car")
  machete_res = s.ext_res("PackedScene", "res://models/props/machete.glb", "machete")
  root = "."
  s.node("CrashedCar", "Node3D", None)
  # The model's right door (door_right) is open; the opening closes it and kicks it open again.
  s.node("Model", None, root, extra=f" instance={model}")
  # Hidden: by the time the avenue loads, the protagonist carries it. The opening shows it.
  s.node("Machete", None, root, {"visible": False, "position": V3(*MACHETE_AT), "rotation": V3(*MACHETE_ROT)}, extra=f" instance={machete_res}")
  # Where Luis falls and the skeletons feed: it stays on the avenue after he is gone.
  blood = s.ext_res("PackedScene", "res://models/props/blood_pool.glb", "blood")
  s.node("Blood", None, root, {"position": V3(*LUIS_LOCAL), "rotation": V3(0, 0.4 + math.pi, 0)}, extra=f" instance={blood}")
  s.node("DomeLight", "OmniLight3D", root, {"position": V3(0, 1.3, 0.3), "light_color": C(1, 0.85, 0.6), "light_energy": 0.5, "omni_range": 2.2})
  s.node("Headlight", "SpotLight3D", root, {"position": V3(-0.58, 0.57, -2.0), "rotation": V3(-0.1, 0.5, 0), "light_color": C(1, 0.93, 0.75), "light_energy": 2.5, "spot_range": 14.0, "spot_angle": 35.0})
  body = s.node("Body", "StaticBody3D", root)
  s.node("Shape", "CollisionShape3D", body, {"shape": s.sub("BoxShape3D", {"size": V3(1.9, 1.5, 4.4)}), "position": V3(0, 0.75, 0.15)})
  s.write(os.path.join(GAME, "crashed_car.tscn"))


# --- The timeline ------------------------------------------------------------------------------
class Timeline:
  def __init__(self):
    self.values = {}   # path -> [(time, value, transition)]
    self.discrete = set()
    self.methods = {}  # path -> [(time, method, args)]
    self.sends = []    # (prop, time it must reach z_goal, z_goal)
    self.t = 0.0

  def key(self, path, t, v, trans=1.0, discrete=False):
    self.values.setdefault(path, []).append((t, v, trans))
    if discrete:
      self.discrete.add(path)

  def call(self, t, method, *args, path="."):
    self.methods.setdefault(path, []).append((t, method, list(args)))

  def cut(self, cam, t=None):
    self.call(self.t if t is None else t, "cut", cam)

  def wait(self, seconds):
    self.t += seconds

  def say(self, who, line, cam=None, gap=0.45):
    if cam:
      self.cut(cam)
    self.call(self.t, "say", who, line)
    self.t += max(2.0, 0.9 + len(line) / 15.0)
    self.call(self.t, "say", who, "")
    self.t += gap

  def speed_at(self, t):
    keys = sorted(self.values["drive_speed"])
    if t <= keys[0][0]:
      return keys[0][1]
    for (t0, v0, _), (t1, v1, _) in zip(keys, keys[1:]):
      if t0 <= t <= t1:
        return v0 + (v1 - v0) * (t - t0) / (t1 - t0) if t1 > t0 else v1
    return keys[-1][1]

  # The piece must stand at z_goal when the timeline reaches `when`: walk back until the street
  # has carried it there from the fog.
  def resolve_sends(self, ahead):
    for prop, when, z_goal in self.sends:
      need, t, dt = ahead + z_goal, when, 0.01
      while need > 0 and t > 0:
        need -= self.speed_at(t) * dt
        t -= dt
      self.call(max(t, 0.02), "send", prop)

  def write(self, s, name, length):
    lines = [f'resource_name = "{name}"', f"length = {num(length)}"]
    i = 0
    for path, keys in self.values.items():
      keys.sort(key=lambda k: k[0])
      lines += [f'tracks/{i}/type = "value"', f"tracks/{i}/imported = false", f"tracks/{i}/enabled = true",
                f'tracks/{i}/path = NodePath("{path}")', f"tracks/{i}/interp = 1", f"tracks/{i}/loop_wrap = true",
                f"tracks/{i}/keys = {{",
                f'"times": PackedFloat32Array({", ".join(num(k[0]) for k in keys)}),',
                f'"transitions": PackedFloat32Array({", ".join(num(k[2]) for k in keys)}),',
                f'"update": {1 if path in self.discrete else 0},',
                f'"values": [{", ".join(val(k[1]) for k in keys)}]', "}"]
      i += 1
    for path, keys in self.methods.items():
      keys.sort(key=lambda k: k[0])
      # A track keeps one key per instant: calls made together go ten milliseconds apart (Godot merges keys closer than its relative tolerance), in order.
      for j in range(1, len(keys)):
        if keys[j][0] <= keys[j - 1][0]:
          keys[j] = (keys[j - 1][0] + 0.01,) + keys[j][1:]
      calls = ", ".join('{"args": [' + ", ".join(val(a) for a in k[2]) + f'], "method": &"{k[1]}"}}' for k in keys)
      lines += [f'tracks/{i}/type = "method"', f"tracks/{i}/imported = false", f"tracks/{i}/enabled = true",
                f'tracks/{i}/path = NodePath("{path}")', f"tracks/{i}/interp = 1", f"tracks/{i}/loop_wrap = true",
                f"tracks/{i}/keys = {{",
                f'"times": PackedFloat32Array({", ".join(num(k[0]) for k in keys)}),',
                f'"transitions": PackedFloat32Array({", ".join("1" for _ in keys)}),',
                f'"values": [{calls}]', "}"]
      i += 1
    rid = f"animation_{len(s.subs)}"
    s.subs.append(f'[sub_resource type="Animation" id="{rid}"]\n' + "\n".join(lines))
    return Raw(f'SubResource("{rid}")')


# --- The opening -------------------------------------------------------------------------------
SPACING = 40.0
SEGMENTS = 6
SKY_SPACING = 80.0
SEND_AHEAD = 180.0             # Must match OpeningCutscene.
LANE = -2.5                    # The street sits left so the car drives in the right lane.
CRASH = (3000.0, 0.0, 0.0)     # The avenue, far from the drive, for the awakening.
CAR_AT = (-7.2, 0.0, 30.0)     # Avenue coordinates; avenue.tscn uses the same.
CAR_YAW = math.pi / 2
SPAWN = (-3.6, 0.1, 30.2)      # Where the player takes over, in avenue.tscn too: clear of Luis and the feeding.
RAIN = ("RainLeft", "RainRight", "RainFront")
CAMERA_HEIGHT, ARM, PITCH = 1.5, 3.4, -0.2


def car_point(local):
  """A point in the crashed car's frame, in avenue coordinates."""
  lx, ly, lz = local
  c, s_ = math.cos(CAR_YAW), math.sin(CAR_YAW)
  return (CAR_AT[0] + lx * c + lz * s_, ly, CAR_AT[2] - lx * s_ + lz * c)


def building(s, parent, name, side, z, width, height, color, setback=9.5):
  depth = 10.0
  b = s.node(name, "Node3D", parent, {"position": V3(side * (setback + depth / 2), 0, z), "metadata/half": width / 2})
  s.box("Block", b, (depth, height, width), (0, height / 2, 0), color)
  for floor in range(int(height // 3)):
    s.box(f"Windows{floor}", b, (0.1, 1.1, width - 1.2), (-side * depth / 2, floor * 3 + 1.7, 0), (0.08, 0.09, 0.11))


def building_row(s, row, side, setback, widths, heights, gap):
  z, i = -SPACING / 2, 0
  while z < SPACING / 2 - gap:
    width = min(rng.uniform(*widths), SPACING / 2 - z)
    building(s, row, f"Building{i}", side, z + width / 2, width, rng.choice(heights), rng.choice(FACADES), setback)
    z += width
    i += 1


def street_segment(s, parent, k, street):
  seg = s.node(f"Piece{k}", "Node3D", parent, {"position": V3(0, 0, -k * SPACING)})
  s.node("Street", None, seg, extra=f" instance={street}")
  for side, name in ((-1, "Left"), (1, "Right")):
    # The row on the sidewalk steps aside for the scripted pieces; the ones behind stay, taller and
    # taller, so a gap or a low roof shows more city instead of fog.
    building_row(s, s.node(name, "Node3D", seg), side, 9.5, (8, 14), (6, 9, 12, 15, 18, 24), 4)
    behind = s.node("Behind" + name, "Node3D", seg)
    building_row(s, behind, side, 22.0, (10, 16), (15, 18, 24, 30, 36), 1)
    far = s.node("Far" + name, "Node3D", seg)
    building_row(s, far, side, 34.0, (12, 18), (24, 30, 36, 42), 1)


def skyline_piece(s, parent, k):
  piece = s.node(f"Piece{k}", "Node3D", parent, {"position": V3(0, 0, -k * SKY_SPACING)})
  for side in (-1, 1):
    for i in range(4):
      h = rng.uniform(20, 60)
      s.box(f"Tower{side}_{i}", piece, (rng.uniform(12, 22), h, rng.uniform(12, 18)),
            (side * rng.uniform(45, 80), h / 2, -SKY_SPACING / 2 + i * 20 + rng.uniform(0, 6)), (0.36, 0.38, 0.42))


def scripted(s, parent, name, model, half, side=None):
  props = {"visible": False, "position": V3(0, 0, 100), "metadata/half": half}
  if side:
    props["metadata/side"] = side
  p = s.node(name, "Node3D", parent, props)
  s.node("Model", None, p, extra=f" instance={model}")


def skeletons(s, parent, skeleton):
  p = s.node("Skeletons", "Node3D", parent, {"visible": False, "position": V3(0, 0, 100)})
  for i, (x, z, yaw) in enumerate(((1.6, 0.0, 0.3), (3.0, -1.4, -0.4), (4.3, 0.6, 0.1), (2.2, -3.0, 2.8))):
    s.node(f"Skeleton{i}", None, p, {"position": V3(x, 0, z), "rotation": V3(0, yaw, 0)}, extra=f" instance={skeleton}")


def build_opening():
  s = Scene()
  avenue = s.ext_res("PackedScene", "res://models/environments/avenue.glb", "avenue")
  skeleton = s.ext_res("PackedScene", "res://models/characters/skeleton.glb", "skeleton")
  hero = s.ext_res("PackedScene", "res://models/characters/protagonist_male.glb", "hero")
  luis_res = s.ext_res("PackedScene", "res://models/characters/luis.glb", "luis")
  crashed = s.ext_res("PackedScene", "res://scenes/crashed_car.tscn", "crashed")

  sky = s.sub("Environment", {"background_mode": 1, "background_color": C(0.55, 0.58, 0.62), "ambient_light_source": 2,
                              "ambient_light_color": C(0.6, 0.63, 0.7), "ambient_light_energy": 0.6, "tonemap_mode": 2,
                              "fog_enabled": True, "fog_light_color": C(0.55, 0.58, 0.62), "fog_density": 0.012,
                              "adjustment_enabled": True, "adjustment_contrast": 1.1, "adjustment_saturation": 0.75})

  s.node("Opening", "OpeningCutscene", None, {"physics_interpolation_mode": 2})  # Cameras move on the timeline, not in physics.
  s.node("WorldEnvironment", "WorldEnvironment", ".", {"environment": sky})
  s.node("Sun", "DirectionalLight3D", ".", {"rotation": V3(-0.9, 0.6, 0), "light_color": C(0.8, 0.85, 1), "light_energy": 0.8, "shadow_enabled": True})

  # The drive: a still car, a street running under it, the far city crawling behind.
  road = s.node("Road", "Node3D", ".", {"position": V3(LANE, 0, 0), "metadata/spacing": SPACING})
  street = s.ext_res("PackedScene", "res://models/environments/drive/street.glb", "street")
  for k in range(SEGMENTS):
    street_segment(s, road, k, street)
  skyline = s.node("Skyline", "Node3D", ".", {"metadata/spacing": SKY_SPACING})
  for k in range(6):
    skyline_piece(s, skyline, k)
  s.shape("Avila", ".", "PrismMesh", {"size": V3(140, 150, 1400)}, (-260, 60, -500), (0.13, 0.19, 0.16), rot=(0, 0.25, 0))
  props = s.node("Props", "Node3D", ".", {"position": V3(LANE, 0, 0)})
  scripted(s, props, "Store", s.ext_res("PackedScene", "res://models/environments/drive/store.glb", "store"), 7.0, "Right")
  scripted(s, props, "Bus", s.ext_res("PackedScene", "res://models/environments/drive/bus.glb", "bus"), 6.0)
  scripted(s, props, "SplitBuilding", s.ext_res("PackedScene", "res://models/environments/drive/split_building.glb", "split"), 9.0, "Right")
  skeletons(s, props, skeleton)

  car = s.node("Car", "Node3D", ".")
  s.node("Model", None, car, extra=f" instance={s.ext_res('PackedScene', 'res://models/props/car.glb', 'car')}")
  # The wheel turns around its own axis on a pivot tilted like the column.
  pivot = s.node("WheelPivot", "Node3D", car, {"position": V3(-0.38, 1.03, -0.45), "rotation": V3(0.419, 0, 0)})
  s.node("Wheel", None, pivot, extra=f" instance={s.ext_res('PackedScene', 'res://models/props/car_wheel.glb', 'wheel')}")
  for tag, x in (("WiperLeft", -0.5), ("WiperRight", 0.1)):
    w = s.node(tag, "Node3D", car, {"position": V3(x, 1.0, -0.82), "rotation": V3(0.76, 0, 0)})
    arm = s.node("Arm", "Node3D", w)
    s.box("Blade", arm, (0.55, 0.012, 0.02), (0.27, 0, 0.01), DASH)
  machete_res = s.ext_res("PackedScene", "res://models/props/machete.glb", "machete")
  s.node("Machete", None, car, {"position": V3(*MACHETE_AT), "rotation": V3(*MACHETE_ROT)}, extra=f" instance={machete_res}")
  s.node("Headlights", "SpotLight3D", car, {"position": V3(0, 0.7, -2.4), "light_color": C(1, 0.93, 0.75), "light_energy": 0.0, "spot_range": 45.0, "spot_angle": 28.0})
  # Both sit with their root on the car's floor line, facing the road.
  s.node("Luis", None, car, {"position": V3(-0.38, 0, 0.05), "rotation": V3(0, math.pi, 0)}, extra=f" instance={luis_res}")
  s.node("luis_backpack", None, "Car/Luis/armature_luis/Skeleton3D", {"visible": False})
  s.node("Hero", None, car, {"position": V3(0.38, 0, 0.05), "rotation": V3(0, math.pi, 0)}, extra=f" instance={hero}")
  s.node("machete", None, "Car/Hero/armature_male/Skeleton3D", {"visible": False})
  rig = s.node("CameraRig", "Node3D", car)
  cams = {"CamA": ((0, 1.4, 1.15), (0, 1.15, -3)),
          "CamB": ((0.3, 1.27, 0.8), (-0.4, 1.12, -0.25)),
          "CamC": ((-0.3, 1.27, 0.8), (0.4, 1.12, -0.25)),
          "CamD": ((0.5, 1.15, 0.8), (4.0, 1.8, -1.0))}  # The right rear window, at the street going by.
  for name, (at, to) in cams.items():
    s.node(name, "Camera3D", rig, {"position": V3(*at), "rotation": look(at, to), "fov": 70.0, "far": 1500.0, "current": name == "CamA", "unique_name_in_owner": True})
  rain = s.sub("ParticleProcessMaterial", {"emission_shape": 3, "emission_box_extents": V3(14, 0.5, 18), "direction": V3(0, -1, 0.45),
                                            "spread": 2.0, "initial_velocity_min": 9.0, "initial_velocity_max": 12.0, "gravity": V3(0, -3, 0)})
  drop = s.sub("QuadMesh", {"material": s.sub("StandardMaterial3D", {"transparency": 1, "shading_mode": 0, "albedo_color": C(0.72, 0.8, 1, 0.18), "billboard_mode": 3, "billboard_keep_scale": True}),
                            "size": ("Vector2", 0.004, 0.35)})
  # Three emitters around the cabin, so no drop falls through the roof in front of the cameras:
  # the strip over the car starts far enough ahead to land before the hood.
  side = s.sub("ParticleProcessMaterial", {"emission_shape": 3, "emission_box_extents": V3(6.8, 0.5, 18), "direction": V3(0, -1, 0.45),
                                            "spread": 2.0, "initial_velocity_min": 9.0, "initial_velocity_max": 12.0, "gravity": V3(0, -3, 0)})
  front = s.sub("ParticleProcessMaterial", {"emission_shape": 3, "emission_box_extents": V3(1.2, 0.5, 7), "direction": V3(0, -1, 0.45),
                                             "spread": 2.0, "initial_velocity_min": 9.0, "initial_velocity_max": 12.0, "gravity": V3(0, -3, 0)})
  for name, at, amount, process in (("RainLeft", (-8, 12, -6), 2400, side), ("RainRight", (8, 12, -6), 2400, side), ("RainFront", (0, 12, -17), 200, front)):
    s.node(name, "GPUParticles3D", ".", {"position": V3(*at), "amount": amount, "amount_ratio": 0.3, "preprocess": 1.0,
                                         "visibility_aabb": ("AABB", -20, -20, -30, 40, 34, 60), "process_material": process, "draw_pass_1": drop})

  # The awakening, on the avenue itself, so the last shot is where the game picks up.
  site = s.node("CrashSite", "Node3D", ".", {"position": V3(*CRASH)})
  s.node("Avenue", None, site, extra=f" instance={avenue}")
  s.node("CrashedCar", None, site, {"position": V3(*CAR_AT), "rotation": V3(0, CAR_YAW, 0)}, extra=f" instance={crashed}")
  # Luis, where he fell: beside the passenger door, face down, his head toward the front. Only the
  # opening has him; an exported game drops overrides inside instanced scenes, so he can't be hidden later.
  s.node("Luis", None, "CrashSite/CrashedCar", {"position": V3(*LUIS_LOCAL), "rotation": V3(0, 0.4 + math.pi, 0)}, extra=f" instance={luis_res}")
  s.node("Spill", "OmniLight3D", site, {"position": V3(-5.5, 2.2, 28.5), "light_color": C(1, 0.8, 0.55), "light_energy": 1.2, "omni_range": 8.0})
  s.node("Rain", "GPUParticles3D", site, {"position": V3(-6, 14, 28), "amount": 4000, "preprocess": 1.0,
                                          "visibility_aabb": ("AABB", -20, -20, -30, 40, 34, 60), "process_material": rain, "draw_pass_1": drop})
  luis_at = car_point(LUIS_LOCAL)
  crouched = []
  def facing(frm, to):  # Characters face +Z.
    return math.atan2(to[0] - frm[0], to[2] - frm[2])

  # Past Luis seen from the seat, so he shows; the third rises where CrashSkeleton stands.
  stoops = ((1.0, -0.3), (0.1, -1.1), (-1.3, -1.2))
  for i, (dx, dz) in enumerate(stoops):
    at = (luis_at[0] + dx, 0, luis_at[2] + dz)
    yaw = facing(at, luis_at)
    crouched.append(s.node(f"Skeleton{i}", None, site, {"position": V3(*at), "rotation": V3(0, yaw, 0)}, extra=f" instance={skeleton}"))
  hero_inside = car_point((0.38, 0, -0.1))
  hero_door = car_point((1.4, 0, -0.1))
  s.node("Hero", None, site, {"visible": False, "position": V3(*hero_inside), "rotation": V3(0, math.pi, 0)}, extra=f" instance={hero}")
  seat_cam = car_point((0.5, 1.32, 0.05))
  back_cam = car_point((0.0, 1.3, 0.15))  # Between the front seats, down at the back seat.
  shots = {"CamSeat": (seat_cam, (luis_at[0], 0.25, luis_at[2]), 0.25),
           "CamBack": (back_cam, car_point(MACHETE_AT), 0.0),
           "CamOut": ((-0.8, 1.9, 31.0), (-6.6, 0.8, 27.8), 0.0)}
  for name, (at, to, roll) in shots.items():
    r = look(at, to)
    s.node(name, "Camera3D", site, {"position": V3(*at), "rotation": V3(r[1], r[2], roll), "fov": 60.0, "far": 1500.0, "unique_name_in_owner": True})

  # Screen: black, the date, subtitles and the skip ring.
  screen = s.node("Screen", "CanvasLayer", ".")
  s.node("Fade", "ColorRect", screen, {"anchors_preset": 15, "anchor_right": 1.0, "anchor_bottom": 1.0, "mouse_filter": 2, "color": C(0, 0, 0, 1)})
  s.node("Card", "Label", screen, {"modulate": C(1, 1, 1, 0), "anchors_preset": 15, "anchor_right": 1.0, "anchor_bottom": 1.0,
                                   "theme_override_font_sizes/font_size": 30, "text": "Caracas, 19 de mayo de 2018",
                                   "horizontal_alignment": 1, "vertical_alignment": 1})
  s.node("Subtitle", "RichTextLabel", screen, {"anchor_left": 0.1, "anchor_top": 0.8, "anchor_right": 0.9, "anchor_bottom": 0.96,
                                               "mouse_filter": 2, "bbcode_enabled": True, "scroll_active": False,
                                               "theme_override_colors/font_outline_color": C(0, 0, 0, 1),
                                               "theme_override_constants/outline_size": 7,
                                               "theme_override_font_sizes/normal_font_size": 24,
                                               "theme_override_font_sizes/italics_font_size": 24})
  hint = s.node("SkipHint", "HBoxContainer", screen, {"visible": False, "anchors_preset": 3, "anchor_left": 1.0, "anchor_top": 1.0,
                                                      "anchor_right": 1.0, "anchor_bottom": 1.0, "offset_left": -300.0, "offset_top": -70.0,
                                                      "offset_right": -30.0, "offset_bottom": -30.0, "grow_horizontal": 0, "grow_vertical": 0,
                                                      "alignment": 2, "theme_override_constants/separation": 10})
  s.node("Ring", "Control", hint, {"custom_minimum_size": ("Vector2", 36, 36)})
  s.node("Label", "Label", hint, {"text": "Mantén E para saltar", "vertical_alignment": 1, "theme_override_font_sizes/font_size": 18})

  # Sound: art/audio/build_opening_sfx.py makes the files. All of it is heard from inside the car,
  # so none of it is positional; the timeline starts, stops and fades each player.
  def ogg(name):
    return s.ext_res("AudioStreamOggVorbis", f"res://audio/opening/{name}.ogg", f"sfx_{name}")
  keys = s.sub("AudioStreamRandomizer", dict({"playback_mode": 0, "random_pitch": 1.12, "random_volume_offset_db": 2.0, "streams_count": 6},
                                             **{f"stream_{i}/stream": ogg(f"key_{i + 1}") for i in range(6)}))
  s.node("Typewriter", "AudioStreamPlayer", screen, {"stream": keys, "volume_db": -10.0, "max_polyphony": 3})
  s.node("Engine", "AudioStreamPlayer", "Car", {"stream": ogg("engine"), "volume_db": -12.0, "autoplay": True})
  sound = s.node("Sound", "Node", ".")
  for name, volume in (("Rain", -16.0), ("Tuning", -18.0), ("Radio", -15.0), ("Static", -20.0), ("Knock", -8.0), ("Wiper", -20.0),
                       ("Thunder", -6.0), ("Whistle", -9.0), ("Crash", -2.0), ("Tinnitus", -16.0), ("Feeding", -40.0),
                       ("DoorKick", -4.0), ("Bones", -8.0)):
    file = {"Tuning": "radio_tuning", "Radio": "radio_music", "Static": "radio_static", "DoorKick": "door_kick"}.get(name, name.lower())
    s.node(name, "AudioStreamPlayer", sound, {"stream": ogg(file), "volume_db": volume})

  # --- The script ---
  T = Timeline()
  DAY = {"bg": C(0.55, 0.58, 0.62), "amb": 0.6, "fog": C(0.55, 0.58, 0.62), "density": 0.012, "sun": 0.8}
  DUSK = {"bg": C(0.24, 0.26, 0.32), "amb": 0.35, "fog": C(0.24, 0.26, 0.32), "density": 0.015, "sun": 0.3}
  NIGHT = {"bg": C(0.03, 0.04, 0.07), "amb": 0.15, "fog": C(0.1, 0.15, 0.28), "density": 0.03, "sun": 0.06}
  STREET = dict(NIGHT, density=0.05)  # The avenue's own heavy fog, for the awakening.

  def sky_at(t, state):
    T.key("WorldEnvironment:environment:background_color", t, state["bg"])
    T.key("WorldEnvironment:environment:ambient_light_energy", t, state["amb"])
    T.key("WorldEnvironment:environment:fog_light_color", t, state["fog"])
    T.key("WorldEnvironment:environment:fog_density", t, state["density"])
    T.key("Sun:light_energy", t, state["sun"])

  def speed(t, v):
    T.key(".:drive_speed", t, v)

  def fade(t, a, hard=False):
    if hard:
      T.key("Screen/Fade:color", t - 0.01, C(0, 0, 0, 1 - a))
    T.key("Screen/Fade:color", t, C(0, 0, 0, a))

  T.values["drive_speed"] = []  # Mirror of .:drive_speed for the send solver.

  def drive(t, v):
    speed(t, v)
    T.values["drive_speed"].append((t, v, 1.0))

  def luis(clip, t=None, blend=0.4):
    T.call(T.t if t is None else t, "play", clip, blend, path="Car/Luis/AnimationPlayer")

  def hero(clip, t=None, blend=0.4):
    T.call(T.t if t is None else t, "play", clip, blend, path="Car/Hero/AnimationPlayer")

  # 0. Black.
  fade(0, 1)
  T.key("Screen/Card:modulate", 0, C(1, 1, 1, 0))
  T.key("Screen/Card:modulate", 2.0, C(1, 1, 1, 0))
  T.key("Screen/Card:modulate", 3.5, C(1, 1, 1, 1))
  T.key("Screen/Card:modulate", 7.0, C(1, 1, 1, 1))
  T.key("Screen/Card:modulate", 8.5, C(1, 1, 1, 0))
  drive(0, 9.0)
  sky_at(0, DAY)
  T.key("Car/Headlights:light_energy", 0, 0.0)
  T.key("Car/Model/radio_light:visible", 0, True, discrete=True)
  T.key("Car:rotation", 0, V3(0, 0, 0))
  for name in RAIN:
    T.key(name + ":amount_ratio", 0, 0.3)
  T.key("Car/WheelPivot/Wheel:rotation", 0, V3(0, 0, 0))
  T.key("CrashSite/CrashedCar/Model/door_right:rotation", 0, V3(0, 0, 0))
  T.key("CrashSite/CrashedCar/Machete:visible", 0, True, discrete=True)
  T.key("CrashSite/Hero:visible", 0, False, discrete=True)
  T.key("CrashSite/Hero:position", 0, V3(*hero_inside))
  # Keyed, not overridden: an exported game drops overrides inside instanced scenes. The machete
  # only reaches his hand when the game takes over.
  for path in ("Car/Hero", "CrashSite/Hero"):
    T.key(path + "/armature_male/Skeleton3D/machete:visible", 0, False, discrete=True)
  T.key("Car/Luis/armature_luis/Skeleton3D/luis_backpack:visible", 0, False, discrete=True)
  T.cut("CamA", 0.02)
  for i, path in enumerate(["Props/Skeletons/Skeleton0", "Props/Skeletons/Skeleton1", "Props/Skeletons/Skeleton2", "Props/Skeletons/Skeleton3", "CrashSite/Hero"]):
    T.call(0.02, "play", "idle", path=path + "/AnimationPlayer")
  # Out of step with each other, so the three do not bite together.
  for i, start in enumerate((0.02, 1.1, 2.3)):
    T.call(start, "play", "feed", path=f"CrashSite/Skeleton{i}/AnimationPlayer")
  luis("drive", 0.02)
  hero("sit", 0.02)
  T.call(0.02, "play", "lying", path="CrashSite/CrashedCar/Luis/AnimationPlayer")
  T.call(0.02, "play", path="Sound/Rain")
  T.call(1.0, "play", path="Sound/Tuning")
  T.call(9.6, "play", path="Sound/Radio")
  T.key("Sound/Rain:volume_db", 0, -16.0)
  T.key("Car/Engine:volume_db", 0, -12.0)
  T.key("Sound/Wiper:volume_db", 0, -20.0)
  T.t = 10.0
  fade(10.0, 0, hard=True)

  # 1. Arrival.
  T.call(T.t, "say", "", "(Una gaita en la radio.)")
  T.wait(2.2)
  T.call(T.t, "say", "", "")
  T.wait(0.4)
  luis("talk")
  T.say("L", "Diez años, mano. Diez años y te vienes justo ahora.", "CamA")
  T.say("P", "Mi mamá no contesta desde diciembre.", "CamC")
  T.say("L", "Aquí nadie contesta desde diciembre. No te lo tomes personal.", "CamB")
  T.say("L", "Te iba a decir que pusieras el aire, pero se dañó en 2016 y el repuesto cuesta más que el carro.")
  T.cut("CamA")
  T.wait(1.2)

  # 2. Money.
  sky_at(T.t, DAY)
  drive(T.t, 9.0)
  drive(T.t + 2.0, 5.0)
  luis("drive")
  T.wait(1.0)
  T.cut("CamD")
  T.wait(1.5)
  T.sends.append(("Store", T.t + 1.0, -6.0))
  T.say("L", "¿Ves esa cola? No saben qué llega. Hacen la cola por si acaso.")
  T.say("P", "¿Y la gente cómo hace?")
  luis("talk")
  T.say("L", "Los precios los cambian dos veces al día. En la mañana un kilo de harina, en la tarde lo mismo cuesta el doble.", "CamB")
  T.say("L", "Ya nadie cuenta los billetes. Los pesan.")
  T.say("L", "Lo que hay lo tienen los bachaqueros, y te lo venden a lo que les da la gana.")
  T.cut("CamC")
  hero("sit_window")
  T.wait(0.8)
  T.say("L", "Mi abuelo guardaba lochas en una lata de galletas. Nos reíamos de él. Ahora valen más que un sueldo.")
  hero("sit_back")
  hero("sit", T.t + 0.8)
  T.wait(0.6)

  # 3. People.
  drive(T.t, 5.0)
  drive(T.t + 2.0, 9.0)
  T.cut("CamA")
  luis("drive")
  T.sends.append(("Bus", T.t + 3.0, -14.0))
  T.wait(1.0)
  T.say("L", "Mi hermana se fue a Bogotá. Mis primos a Lima. Los del edificio... ni sé.")
  T.say("L", "Antes la gente se iba por el aeropuerto. Ahora se va caminando.")
  T.say("P", "¿Y tú por qué te quedaste?")
  T.cut("CamB")
  T.call(T.t, "say", "", "(Luis se ríe sin ganas.)")
  luis("laugh", blend=0.2)
  luis("talk", T.t + 1.8)
  T.wait(1.6)
  T.say("L", "Alguien tenía que buscarte en el aeropuerto, ¿no?")
  luis("point_back")
  T.say("L", "Ahí atrás hay un machete. No preguntes. Aquí ya nadie sale sin uno.")
  luis("let_go", T.t - 0.4, 0.15)
  luis("drive", T.t + 0.4, 0.0)
  T.wait(0.8)

  # 4. The earthquake.
  sky_at(T.t, DAY)
  drive(T.t, 9.0)
  drive(T.t + 2.5, 4.0)
  T.key("Car/Headlights:light_energy", T.t, 0.0)
  T.cut("CamD")
  T.wait(2.0)
  T.sends.append(("SplitBuilding", T.t + 2.5, -8.0))
  T.say("L", "Y después vino el terremoto. Cuarenta segundos.")
  T.say("L", "Cuarenta segundos y se cayó media ciudad. Lo que la crisis no tumbó, lo tumbó eso.")
  T.say("P", "No salió casi nada afuera.")
  T.say("L", "Porque no quedó nadie para contarlo. Se cayeron las antenas y la luz, y después ya nadie volvió a levantarlas.", "CamB")
  T.say("L", "Del otro lado, donde vive tu mamá, no se sabe nada desde entonces.")
  sky_at(T.t, DUSK)
  T.key("Car/Headlights:light_energy", T.t, 1.5)
  drive(T.t, 4.0)
  drive(T.t + 3.0, 8.0)
  T.cut("CamA")
  T.wait(3.5)
  luis("talk")
  T.say("L", "Pero la vieja es dura, mano. Si alguien aguantó, fue ella.")
  T.wait(0.8)
  T.key("Car/Model/radio_light:visible", T.t, False, discrete=True)
  luis("drive")
  T.call(T.t, "say", "", "(La gaita se corta. Estática.)")
  T.call(T.t, "stop", path="Sound/Radio")
  T.call(T.t, "play", path="Sound/Static")
  T.wait(1.6)
  T.call(T.t, "say", "", "")
  luis("hit_radio", blend=0.2)
  T.call(T.t + 0.45, "play", path="Sound/Knock")
  T.call(T.t + 0.82, "play", path="Sound/Knock")
  T.call(T.t + 0.85, "stop", path="Sound/Static")
  luis("drive", T.t + 1.5, 0.0)
  T.wait(1.5)
  T.say("L", "Esta radio también se está muriendo.")

  # 5. The road.
  sky_at(T.t, DUSK)
  sky_at(T.t + 6.0, NIGHT)
  T.key("Car/Headlights:light_energy", T.t + 3.0, 3.0)
  for name in RAIN:
    T.key(name + ":amount_ratio", T.t, 0.3)
    T.key(name + ":amount_ratio", T.t + 5.0, 1.0)
  T.key("Sound/Rain:volume_db", T.t, -16.0)
  T.key("Sound/Rain:volume_db", T.t + 5.0, -8.0)
  T.call(T.t + 4.0, "play", path="Sound/Thunder")
  drive(T.t, 8.0)
  drive(T.t + 3.0, 12.0)
  T.wait(6.0)
  T.call(T.t, "say", "", "(Bajo la lluvia, un silbido. Lejos.)")
  T.call(T.t - 0.6, "play", path="Sound/Whistle")
  T.wait(2.6)
  T.call(T.t, "say", "", "")
  T.wait(0.5)
  T.say("P", "¿Oíste eso?")
  T.say("L", "¿Qué cosa?", gap=0.3)
  swerve = T.t + 2.2
  T.sends.append(("Skeletons", swerve, -14.0))
  T.call(T.t + 0.6, "say", "L", "¿Y eso qué...?")
  T.call(T.t + 1.5, "say", "L", "¡Agárrate!")
  luis("swerve", swerve - 0.15, 0.1)
  hero("brace", swerve - 0.05, 0.1)
  T.key("Car/WheelPivot/Wheel:rotation", swerve - 0.15, V3(0, 0, 0))
  T.key("Car/WheelPivot/Wheel:rotation", swerve + 0.25, V3(0, 0, 1.8), trans=0.5)
  T.key("Car:rotation", swerve, V3(0, 0, 0))
  T.key("Car:rotation", swerve + 0.35, V3(0, 0.5, -0.04), trans=0.5)
  T.key("Car:rotation", swerve + 0.75, V3(0, 1.1, 0.06), trans=2.0)
  impact = swerve + 0.75
  T.call(impact - 1.0, "play", path="Sound/Crash")  # The file's hit is one second in.
  for path, before in (("Sound/Rain:volume_db", -8.0), ("Car/Engine:volume_db", -12.0), ("Sound/Wiper:volume_db", -20.0)):
    T.key(path, impact - 0.01, before)
    T.key(path, impact, -80.0)
  T.call(impact, "say", "", "")
  fade(impact, 1, hard=True)
  drive(impact, 12.0)
  drive(impact + 0.01, 0.0)

  # 6. Awakening.
  T.cut("CamSeat", impact + 0.1)
  sky_at(impact + 0.1, STREET)
  wake = impact + 2.6
  T.call(wake - 0.4, "say", "", "(Un pito en los oídos.)")
  T.call(wake - 1.2, "play", path="Sound/Tinnitus")
  T.call(wake + 0.5, "play", path="Sound/Feeding")
  T.key("Sound/Rain:volume_db", wake + 0.5, -80.0)
  T.key("Sound/Rain:volume_db", wake + 4.0, -12.0, trans=0.4)
  T.key("Sound/Feeding:volume_db", 0, -40.0)
  T.key("Sound/Feeding:volume_db", wake + 0.5, -40.0)
  T.key("Sound/Feeding:volume_db", wake + 4.0, -13.0, trans=0.4)
  for t, a in ((0.0, 1.0), (0.9, 0.55), (1.5, 0.9), (2.5, 0.35), (3.4, 0.0)):
    T.key("Screen/Fade:color", wake + t, C(0, 0, 0, a), trans=-2.0)
  T.call(wake + 3.0, "say", "", "")
  T.call(wake + 3.6, "play", "reach", 0.5, path="CrashSite/CrashedCar/Luis/AnimationPlayer")
  T.t = wake + 5.4
  T.say("L", "(Débil) Vete...", gap=1.4)
  T.cut("CamBack")
  T.wait(3.0)
  T.cut("CamOut")
  door = "CrashSite/CrashedCar/Model/door_right:rotation"
  kick = T.t + 1.0
  T.key(door, kick, V3(0, 0, 0))
  T.call(kick, "play", path="Sound/DoorKick")
  T.key(door, kick + 0.18, V3(0, 1.3, 0), trans=0.4)
  T.key(door, kick + 0.5, V3(0, 1.2, 0))
  T.key("CrashSite/Hero:visible", kick + 0.1, True, discrete=True)
  T.key("CrashSite/CrashedCar/Machete:visible", kick + 0.1, False, discrete=True)
  T.key("CrashSite/Hero:position", kick + 0.1, V3(*hero_inside))
  T.key("CrashSite/Hero:position", kick + 0.6, V3(*hero_door), trans=-2.0)
  T.call(kick + 0.6, "play", "walk", path="CrashSite/Hero/AnimationPlayer")
  T.key("CrashSite/Hero:position", kick + 2.0, V3(*SPAWN))
  T.call(kick + 2.0, "play", "idle", path="CrashSite/Hero/AnimationPlayer")
  T.key("CrashSite/Hero:rotation", kick + 0.6, V3(0, facing(hero_door, SPAWN), 0))
  T.key("CrashSite/Hero:rotation", kick + 1.8, V3(0, facing(hero_door, SPAWN), 0))
  T.key("CrashSite/Hero:rotation", kick + 2.4, V3(0, math.pi, 0), trans=-2.0)
  rising = crouched[2]
  rising_at = (luis_at[0] + stoops[2][0], 0, luis_at[2] + stoops[2][1])
  rise_at = kick + 1.6
  T.key(rising + ":rotation", 0, V3(0, facing(rising_at, luis_at), 0))
  T.key(rising + ":rotation", rise_at, V3(0, facing(rising_at, luis_at), 0))
  T.key(rising + ":rotation", rise_at + 1.4, V3(0, facing(rising_at, SPAWN), 0), trans=-2.0)
  T.call(rise_at, "play", "feed_rise", 0.1, path=rising + "/AnimationPlayer")
  T.call(rise_at, "play", path="Sound/Bones")
  T.call(rise_at + 1.2, "play", "idle", 0.2, path=rising + "/AnimationPlayer")
  print("crash skeleton at", rising_at, "spawn", SPAWN)
  # The camera settles where the player's own camera starts.
  play_focus = (SPAWN[0], SPAWN[1] + CAMERA_HEIGHT, SPAWN[2])
  play_cam = V3(play_focus[0], play_focus[1] - math.sin(PITCH) * ARM, play_focus[2] + math.cos(PITCH) * ARM)
  out_at, out_to, _ = shots["CamOut"]
  out_rot = look(out_at, out_to)
  settle = rise_at + 1.6
  T.key("CrashSite/CamOut:position", 0, V3(*out_at))
  T.key("CrashSite/CamOut:position", settle, V3(*out_at))
  T.key("CrashSite/CamOut:position", settle + 2.2, play_cam, trans=-2.0)
  T.key("CrashSite/CamOut:rotation", 0, V3(out_rot[1], out_rot[2], 0))
  T.key("CrashSite/CamOut:rotation", settle, V3(out_rot[1], out_rot[2], 0))
  T.key("CrashSite/CamOut:rotation", settle + 2.2, V3(PITCH, 0, 0), trans=-2.0)
  end = settle + 2.4
  T.call(end, "finish")

  # drive_speed mirror is only for the solver; the real track is ".:drive_speed".
  T.resolve_sends(SEND_AHEAD)
  del T.values["drive_speed"]
  anim = T.write(s, "opening", end + 0.1)
  lib = s.sub("AnimationLibrary", {"_data": Raw('{&"opening": ' + anim + "}")})

  wipe_t = Timeline()
  for tag in ("WiperLeft", "WiperRight"):
    path = f"Car/{tag}/Arm:rotation"
    for t, z in ((0, 0.0), (0.7, 1.35), (1.4, 0.0), (1.8, 0.0)):
      wipe_t.key(path, t, V3(0, 0, z), trans=-2.0)
  wipe_t.call(0.0, "play", path="Sound/Wiper")
  wipe_t.call(0.7, "play", path="Sound/Wiper")
  wipe = wipe_t.write(s, "wipe", 1.8)
  s.subs[-1] += "\nloop_mode = 1"
  wipe_lib = s.sub("AnimationLibrary", {"_data": Raw('{&"wipe": ' + wipe + "}")})

  s.node("AnimationPlayer", "AnimationPlayer", ".", {"libraries": Raw('{&"": ' + lib + "}"), "autoplay": Raw('&"opening"')})
  s.node("Wipers", "AnimationPlayer", ".", {"libraries": Raw('{&"": ' + wipe_lib + "}"), "autoplay": Raw('&"wipe"')})
  s.write(os.path.join(GAME, "opening.tscn"))
  print(f"opening: {end:.1f} s, {len(s.nodes)} nodes")


build_crashed_car()
build_opening()
