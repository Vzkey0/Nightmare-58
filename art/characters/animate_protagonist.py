"""Generates the protagonist's animations and exports them with the male model.

Run it after build_protagonist.py, which writes a model without animations:

  blender --background art/characters/protagonist.blend --python art/characters/animate_protagonist.py

Clips are authored like a control rig: key poses set the root, hips, spine, feet and the
stick, and inverse kinematics solves legs and arms on every sampled frame. Feet therefore
stay planted and both hands stay on the stick, which plain bone keys cannot guarantee.

Keys are written in frames at 30 fps, the usual unit for reading timing, and baked at 60 fps.
Forward is the character's front; +x is its left, as in the skeleton.
"""

import math
import os

import bpy
from mathutils import Matrix, Quaternion, Vector

HERE = os.path.dirname(os.path.abspath(bpy.data.filepath or __file__))
GLB_PATH = os.path.join(HERE, "..", "..", "game", "models", "characters", "protagonist_male.glb")

AUTHOR_FPS = 30
BAKE_FPS = 60

# Follow-through: the farther from the hips, the later a part arrives.
DELAYS = {
  "spine_rot": 0.4, "chest_rot": 0.8, "head_rot": 1.4,
  "grip": 1.0, "aim": 1.4, "slide": 1.0, "hand_l": 1.6,
}

# The Hitbox in game/scenes/player.tscn must cover the stick from end to end.
STICK_BACK = 0.55
STICK_FRONT = 1.05
STICK_RADIUS = 0.019
PALM_LENGTH = 0.095
FINGER_CURL = 75.0
TUMBLE_PIVOT = 0.44

FORWARD = Vector((0, -1, 0))
UP = Vector((0, 0, 1))


def at(x, forward, z):
  return Vector((x, -forward, z))


def rot(pitch=0.0, yaw=0.0, roll=0.0):
  """Armature-space rotation: +pitch leans forward, +yaw turns left, +roll leans left."""
  return (
    Quaternion(UP, math.radians(yaw))
    @ Quaternion((1, 0, 0), math.radians(pitch))
    @ Quaternion((0, 1, 0), math.radians(roll))
  )


def axes(axis, reference):
  """Orientation with bone Y along axis and Z towards reference, so limbs never twist."""
  y = axis.normalized()
  z = (reference - reference.project(y)).normalized()
  return Matrix((y.cross(z), y, z)).transposed().to_quaternion()


def aim_delta(rest_axis, rest_reference, axis, reference):
  return axes(axis, reference) @ axes(rest_axis, rest_reference).inverted()


def solve_two_bones(origin, target, upper, lower, pole):
  """Returns the joint and the reachable end; the leg eases into full extension to avoid a pop."""
  offset = target - origin
  distance = offset.length
  reach = upper + lower
  soft = reach * 0.95
  if distance > soft:
    room = reach * 0.998 - soft
    distance = soft + room * (1.0 - math.exp(-(distance - soft) / room))
  direction = offset.normalized()
  along = (upper * upper - lower * lower + distance * distance) / (2.0 * distance)
  height = math.sqrt(max(upper * upper - along * along, 0.0))
  bend = (pole - pole.project(direction)).normalized()
  return origin + direction * along + bend * height, origin + direction * distance


class Rig:
  """Turns a pose into bone transforms, working on posed matrices in armature space."""

  def __init__(self, armature):
    bones = armature.data.bones
    self.rest = {bone.name: bone.matrix_local.copy() for bone in bones}
    self.parent = {bone.name: bone.parent.name if bone.parent else None for bone in bones}
    self.head = {bone.name: bone.head_local.copy() for bone in bones}
    self.tail = {bone.name: bone.tail_local.copy() for bone in bones}
    self.world = {}
    self.local = {}
    self.max_stretch = 0.0

  def place(self, name, delta, head=None):
    """Poses a bone by its rotation from rest in armature axes, optionally moving its head."""
    rest = self.rest[name]
    parent = self.parent[name]
    base = self.world[parent] @ self.rest[parent].inverted() @ rest if parent else rest
    origin = base.translation if head is None else head
    target = Matrix.Translation(origin) @ (delta @ rest.to_quaternion()).to_matrix().to_4x4()
    self.world[name] = target
    location, rotation, _ = (base.inverted() @ target).decompose()
    self.local[name] = (location, rotation)

  def origin(self, name):
    parent = self.parent[name]
    base = self.world[parent] @ self.rest[parent].inverted() @ self.rest[name]
    return base.translation.copy()

  def direction(self, name):
    return (self.tail[name] - self.head[name]).normalized()

  def length(self, name):
    return (self.tail[name] - self.head[name]).length

  def limb(self, upper, lower, target, pole, rest_pole):
    origin = self.origin(upper)
    joint, end = solve_two_bones(origin, target, self.length(upper), self.length(lower), pole)
    self.max_stretch = max(self.max_stretch, (target - end).length)
    self.place(upper, aim_delta(self.direction(upper), rest_pole, joint - origin, pole))
    self.place(lower, aim_delta(self.direction(lower), rest_pole, end - joint, pole))

  def leg(self, side, ball, pitch, yaw, turn):
    ankle_rest = self.head["foot" + side]
    ball_rest = at(ankle_rest.x, 0.1, 0.0)
    heel_rest = at(ankle_rest.x, -0.09, 0.0)
    delta = turn @ rot(pitch, yaw)
    # Up on the toes the foot turns around the ball, and on a heel strike around the heel.
    if pitch >= 0:
      ankle = ball + delta @ (ankle_rest - ball_rest)
    else:
      heel = ball + turn @ rot(0, yaw) @ (heel_rest - ball_rest)
      ankle = heel + delta @ (ankle_rest - heel_rest)
    pole = turn @ rot(0, yaw * 0.6) @ FORWARD
    self.limb("upper_leg" + side, "lower_leg" + side, ankle, pole + UP * 0.1, FORWARD)
    self.place("foot" + side, delta)
    grounded = 1.0 - min(ball.z / 0.04, 1.0)
    self.place("toes" + side, turn @ rot(pitch * (1.0 - grounded), yaw))

  def arm(self, side, wrist, pole, chest):
    shoulder = "shoulder" + side
    origin = self.origin(shoulder)
    rest_dir = chest @ (self.head["upper_arm" + side] - self.head[shoulder]).normalized()
    # The collarbone follows the hand a little, as a straight bar would look stiff.
    lift = Quaternion().slerp(rest_dir.rotation_difference((wrist - origin).normalized()), 0.15)
    self.place(shoulder, lift @ chest)
    self.limb("upper_arm" + side, "lower_arm" + side, wrist, pole, -FORWARD)

  def hand(self, side, delta, curl):
    self.place("hand" + side, delta)
    hand_axis = self.direction("hand" + side)
    palm = Vector((1 if side == "_r" else -1, 0, 0))
    fold = (delta @ hand_axis.cross(palm)).normalized()
    self.place("fingers" + side, Quaternion(fold, math.radians(curl)) @ delta)
    self.place("thumb" + side, Quaternion(fold, math.radians(curl * 0.3)) @ delta)

  def grip_delta(self, side, shoulder, grip, stick):
    """Hand orientation around the stick: the thumb runs along it, as with a bat."""
    toward = grip - shoulder
    hand_axis = (toward - toward.project(stick)).normalized()
    return aim_delta(self.direction("hand" + side), FORWARD, hand_axis, stick), hand_axis

  def solve(self, pose):
    self.world.clear()
    self.local.clear()
    ground = at(0, pose["root"], 0)
    self.place("root", Quaternion(), ground)

    # Rolls and spins turn the whole body around a point above the root, so the keys can stay
    # in a pose that never rotates. Only the foot positions may stay on the ground instead.
    turn = rot(pose.get("tumble", 0.0), pose.get("spin", 0.0))
    lift = UP * pose.get("lift", 0.0)
    root = ground + lift
    pivot = root + UP * TUMBLE_PIVOT
    turned = lambda point: pivot + turn @ (point - pivot)
    free = pose.get("feet_free", 0.0)
    foot_turn = Quaternion().slerp(turn, free)

    x, forward, z = pose["hips_pos"]
    hips_at = turned(root + self.head["hips"] + at(x, forward, z))
    hips = turn @ rot(*pose["hips_rot"])
    spine = hips @ rot(*pose["spine_rot"])
    chest = spine @ rot(*pose["chest_rot"])
    head = turn @ rot(*pose["head_rot"])
    self.place("hips", hips, hips_at)
    self.place("spine", spine)
    self.place("chest", chest)
    self.place("neck", chest.slerp(head, 0.5))
    self.place("head", head)

    for side, ball, foot_rot in (("_l", pose["foot_l"], pose["foot_l_rot"]), ("_r", pose["foot_r"], pose["foot_r_rot"])):
      planted = at(*ball)
      self.leg(side, planted.lerp(turned(planted + lift), free), *foot_rot, foot_turn)

    stick = turn @ at(*pose["aim"]).normalized()
    grip = turned(root + at(*pose["grip"]))
    shoulder_r = hips_at + chest @ Vector((-0.2, 0, 0.47))
    shoulder_l = hips_at + chest @ Vector((0.2, 0, 0.47))

    grip_r, hand_axis = self.grip_delta("_r", shoulder_r, grip, stick)
    self.arm("_r", grip - hand_axis * PALM_LENGTH, turn @ at(*pose["pole_r"]), chest)
    self.hand("_r", grip_r, FINGER_CURL)
    self.place("weapon", aim_delta(FORWARD, self.direction("hand_r"), stick, hand_axis), grip - stick * pose["slide"])

    held = max(0.0, min(1.0, pose["left_on"]))
    grip_left = grip - stick * pose["left_dist"]
    grip_l, hand_axis_l = self.grip_delta("_l", shoulder_l, grip_left, stick)
    wrist_held = grip_left - hand_axis_l * PALM_LENGTH
    self.arm("_l", turned(root + at(*pose["hand_l"])).lerp(wrist_held, held), turn @ at(*pose["pole_l"]), chest)
    lower = self.world["lower_arm_l"].to_quaternion() @ self.rest["lower_arm_l"].to_quaternion().inverted()
    self.hand("_l", lower.slerp(grip_l, held), 25.0 + (FINGER_CURL - 25.0) * held)


def tangents(times, values):
  """Monotone cubic slopes: nothing overshoots, so a held foot really holds."""
  count = len(times)
  secants = [(values[i + 1] - values[i]) / (times[i + 1] - times[i]) for i in range(count - 1)]
  slopes = [0.0] * count
  for i in range(1, count - 1):
    before, after = secants[i - 1], secants[i]
    if before * after > 0:
      slopes[i] = 2.0 * before * after / (before + after)
  return slopes


def interpolate(keys, frame, period):
  if period:
    frame %= period
    keys = [(t - period, v) for t, v in keys[-2:]] + keys + [(t + period, v) for t, v in keys[:2]]
  if frame <= keys[0][0]:
    return keys[0][1]
  if frame >= keys[-1][0]:
    return keys[-1][1]
  times = [t for t, _ in keys]
  vector = isinstance(keys[0][1], (tuple, list))
  size = len(keys[0][1]) if vector else 1
  result = []
  index = next(i for i in range(len(times) - 1) if frame < times[i + 1])
  span = times[index + 1] - times[index]
  u = (frame - times[index]) / span
  for component in range(size):
    values = [v[component] if vector else v for _, v in keys]
    slopes = tangents(times, values)
    a, b = values[index], values[index + 1]
    result.append(
      (2 * u**3 - 3 * u**2 + 1) * a
      + (u**3 - 2 * u**2 + u) * span * slopes[index]
      + (-2 * u**3 + 3 * u**2) * b
      + (u**3 - u**2) * span * slopes[index + 1]
    )
  return tuple(result) if vector else result[0]


class Clip:
  def __init__(self, name, frames, channels, loop=False):
    self.name = name
    self.frames = frames
    self.channels = channels
    self.loop = loop

  def sample(self, frame):
    period = self.frames if self.loop else 0
    pose = {}
    for name, channel in self.channels.items():
      when = frame - DELAYS.get(name, 0.0)
      if callable(channel):
        pose[name] = channel(when / self.frames % 1.0)
      else:
        pose[name] = interpolate(channel, when, period)
    return pose


def timeline(*poses):
  """Merges (frame, sparse pose) pairs into one key list per channel."""
  channels = {}
  for frame, pose in poses:
    for name, value in pose.items():
      channels.setdefault(name, []).append((frame, value))
  return channels


GUARD = {
  "root": 0.0,
  "hips_pos": (0.015, -0.01, -0.105),
  "hips_rot": (9, 14, 0),
  "spine_rot": (4, -6, 0),
  "chest_rot": (4, -7, 0),
  "head_rot": (5, 0, 0),
  "foot_r": (-0.16, 0.16, 0.0),
  "foot_r_rot": (0, -8),
  "foot_l": (0.19, -0.2, 0.0),
  "foot_l_rot": (0, 28),
  # One-handed and out to the side: the camera sits behind, so a stick held in front hides.
  "grip": (-0.34, 0.1, 0.86),
  "aim": (-0.3, 0.75, -0.59),
  "slide": -0.05,
  "left_on": 0.0,
  "left_dist": 0.38,
  "hand_l": (0.33, 0.04, 0.84),
  "pole_r": (-0.2, -0.8, -0.4),
  "pole_l": (0.2, -0.8, -0.4),
}


def wave(phase, center=0.0, cycles=1.0):
  return math.cos(2.0 * math.pi * cycles * (phase - center))


def idle_clip():
  # Two sway rates that do not line up, so the loop has no visible beat.
  def add(base, offsets):
    return lambda phase: tuple(b + o(phase) for b, o in zip(base, offsets))

  breath = lambda phase: wave(phase, 0.1, 3)
  sway = lambda phase: wave(phase, 0.0, 1)
  still = lambda phase: 0.0
  channels = dict(GUARD)
  channels.update({
    "hips_pos": add(GUARD["hips_pos"], (lambda p: 0.012 * sway(p), still, lambda p: 0.006 * breath(p))),
    "chest_rot": add(GUARD["chest_rot"], (lambda p: 1.1 * breath(p), lambda p: 0.8 * sway(p), still)),
    "head_rot": add(GUARD["head_rot"], (lambda p: -0.6 * breath(p), lambda p: 1.5 * wave(p, 0.3, 1), still)),
    "grip": add(GUARD["grip"], (still, still, lambda p: 0.008 * breath(p))),
    "aim": add(GUARD["aim"], (lambda p: 0.012 * sway(p), still, lambda p: 0.01 * breath(p))),
  })
  for name, value in list(channels.items()):
    if not callable(value):
      channels[name] = [(0, value)]
  return Clip("idle-loop", 150, channels, loop=True)


RUN_SPEED = 4.6
WALK_SPEED = 1.9
RUN_FRAMES = 18
STANCE_SHARE = 0.3
LANDING_REACH = 0.3

SWING_LIFT = [(0.0, 0.0), (0.25, 0.3), (0.55, 0.23), (0.85, 0.09), (1.0, 0.0)]
FOOT_PITCH = [(0.0, -8.0), (0.09, 0.0), (0.2, 12.0), (0.3, 58.0), (0.42, 72.0), (0.72, 24.0), (0.93, -10.0)]


def run_foot(side_x, offset, speed, frames, stance, step):
  """Stance moves back at exactly the run speed: that is what stops the feet from sliding."""
  duration = frames / AUTHOR_FPS
  slope = -speed * duration

  def position(phase):
    phase = (phase + offset) % 1.0
    if phase < stance:
      return (side_x, LANDING_REACH + slope * phase, 0.0)
    u = (phase - stance) / (1.0 - stance)
    start = LANDING_REACH + slope * stance
    span_slope = slope * (1.0 - stance)
    forward = (
      (2 * u**3 - 3 * u**2 + 1) * start
      + (u**3 - 2 * u**2 + u) * span_slope
      + (-2 * u**3 + 3 * u**2) * LANDING_REACH
      + (u**3 - u**2) * span_slope
    )
    return (side_x, forward, step * interpolate(SWING_LIFT, u, 0))

  return position


def run_clip(name, speed, frames, stance, lean, drop, swing, step=1.0):
  def foot_rot(offset, yaw):
    return lambda phase: (interpolate(FOOT_PITCH, (phase + offset) % 1.0, 1.0), yaw)

  lift = 0.028
  channels = {
    "root": [(0, 0.0)],
    "hips_pos": lambda p: (0.018 * wave(p, 0.15), 0.05, drop + lift * wave(p, 0.35, 2)),
    "hips_rot": lambda p: (lean + 1.5 * wave(p, 0.3, 2), -9 * wave(p, 0.04), -4 * wave(p, 0.15)),
    "spine_rot": lambda p: (5, 7 * wave(p, 0.04), 1.5 * wave(p, 0.15)),
    "chest_rot": lambda p: (3 + 1.0 * wave(p, 0.1, 2), 8 * wave(p, 0.04), 1.5 * wave(p, 0.15)),
    "head_rot": lambda p: (6 + 1.0 * wave(p, 0.2, 2), 1.5 * wave(p, 0.04), 0),
    "foot_l": run_foot(0.125, 0.0, speed, frames, stance, step),
    "foot_r": run_foot(-0.125, 0.5, speed, frames, stance, step),
    "foot_l_rot": foot_rot(0.0, 5),
    "foot_r_rot": foot_rot(0.5, -5),
    # The right arm swings less: it carries the stick, trailing low behind the run.
    "grip": lambda p: (-0.33, 0.08 + 0.11 * wave(p, 0.04), 0.99 - 0.03 * wave(p, 0.04)),
    "aim": lambda p: (0.05 + 0.02 * wave(p, 0.04), 0.93, 0.36 + 0.03 * wave(p, 0.04)),
    "slide": [(0, 0.5)],
    "left_on": [(0, 0.0)],
    "left_dist": [(0, 0.38)],
    "hand_l": lambda p: (0.25, 0.1 - swing * wave(p, 0.04), 1.04 - 0.08 * wave(p, 0.04)),
    "pole_r": [(0, (-0.5, -0.8, -0.6))],
    "pole_l": [(0, (0.5, -0.9, -0.5))],
  }
  return Clip(name, frames, channels, loop=True)


# Pose in the air, with feet relative to the body: the jump's height comes from physics.
AIR = dict(GUARD)
AIR.update({
  "hips_pos": (0.0, 0.0, -0.05), "hips_rot": (4, 0, 0), "spine_rot": (2, 0, 0), "chest_rot": (2, 0, 0),
  "foot_r": (-0.13, 0.14, 0.4), "foot_r_rot": (5, -5), "foot_l": (0.13, -0.16, 0.3), "foot_l_rot": (45, 5),
  "grip": (-0.35, 0.12, 1.12), "aim": (0.05, 0.9, 0.3), "slide": 0.4,
  "hand_l": (0.32, 0.22, 1.2), "pole_r": (-0.5, -0.8, -0.6), "pole_l": (0.5, -0.9, -0.5),
})


def jump_clip():
  """No crouch before leaving the ground: it starts mid-push so the button answers at once."""
  return Clip("jump", 10, timeline(
    (0, dict(AIR, **{
      "hips_pos": (0.0, 0.03, -0.16), "hips_rot": (14, 0, 0), "head_rot": (9, 0, 0),
      "foot_r": (-0.13, 0.1, 0.0), "foot_r_rot": (30, -5), "foot_l": (0.13, -0.12, 0.0), "foot_l_rot": (40, 5),
      "hand_l": (0.28, -0.15, 0.95),
    })),
    (3, {
      "hips_pos": (0.0, 0.02, -0.02), "hips_rot": (6, 0, 0), "head_rot": (3, 0, 0),
      "foot_r": (-0.12, 0.22, 0.34), "foot_r_rot": (-10, -5), "foot_l": (0.12, -0.2, 0.12), "foot_l_rot": (55, 5),
    }),
    (10, {key: AIR[key] for key in ("hips_pos", "hips_rot", "head_rot", "foot_r", "foot_r_rot", "foot_l", "foot_l_rot", "hand_l")}),
  ))


def fall_clip():
  return Clip("fall-loop", 24, timeline(
    (0, dict(AIR, **{
      "foot_r": (-0.14, 0.1, 0.22), "foot_l": (0.14, -0.12, 0.14), "foot_l_rot": (30, 5), "hand_l": (0.36, 0.1, 1.22),
    })),
    (12, {"foot_r": (-0.14, 0.16, 0.26), "foot_l": (0.14, -0.06, 0.2), "hand_l": (0.38, 0.08, 1.27)}),
  ), loop=True)


def land_clip():
  return Clip("land", 12, timeline(
    (0, dict(GUARD, **{
      "hips_pos": (0.0, 0.02, -0.1), "grip": AIR["grip"], "aim": AIR["aim"], "slide": 0.3, "hand_l": (0.34, 0.15, 1.05),
    })),
    (3, {
      "hips_pos": (0.0, 0.05, -0.3), "hips_rot": (24, 10, 0), "head_rot": (12, 0, 0),
      "grip": (-0.36, 0.2, 0.74), "aim": (-0.1, 0.9, -0.2), "hand_l": (0.34, 0.22, 0.72),
    }),
    (6, {"hips_pos": (0.0, 0.03, -0.24), "hips_rot": (18, 12, 0)}),
    (12, {key: GUARD[key] for key in ("hips_pos", "hips_rot", "head_rot", "grip", "aim", "slide", "hand_l")}),
  ))


def air_attack_clip():
  """A falling overhead blow; the knees stay tucked so the swing reads against the jump."""
  tucked = {"foot_r": (-0.13, 0.3, 0.2), "foot_r_rot": (-5, -5), "foot_l": (0.13, 0.1, 0.24), "foot_l_rot": (25, 5)}
  return Clip("attack_air", 21, timeline(
    (0, dict(AIR, **{"grip": (-0.24, 0.2, 1.3), "aim": (-0.08, 0.3, 0.95), "slide": 0.0, "left_on": 0.3})),
    (4, {"grip": (-0.12, -0.02, 1.62), "aim": (-0.15, -0.8, 0.55), "left_on": 1.0, "hips_rot": (-10, 0, 0), "chest_rot": (-6, 0, 0)}),
    (6, {"grip": (-0.12, -0.06, 1.64), "aim": (-0.15, -0.85, 0.48)}),
    (8, {"grip": (-0.08, 0.35, 1.45), "aim": (-0.05, 0.45, 0.9)}),
    (10, {"grip": (-0.04, 0.6, 0.98), "aim": (0.03, 0.92, 0.1), "hips_rot": (18, 0, 0)}),
    (12, dict(tucked, **{"grip": (0.0, 0.5, 0.72), "aim": (0.05, 0.75, -0.65), "hips_rot": (28, 0, 0), "chest_rot": (8, 0, 0)})),
    (17, dict(tucked, **{"grip": (0.0, 0.5, 0.72), "aim": (0.05, 0.75, -0.65), "left_on": 1.0, "slide": 0.0, "hips_rot": (26, 0, 0)})),
    (21, {key: AIR[key] for key in ("hips_rot", "chest_rot", "foot_r", "foot_r_rot", "foot_l", "foot_l_rot", "grip", "aim", "slide")}),
    (21, {"left_on": 0.0}),
  ))


# The body curled into a ball around TUMBLE_PIVOT, both hands on a stick held across the
# shins: the stick lies along the roll's axis, the only way 1.6 m fits through a roll.
TUCK = {
  "hips_pos": (0.0, -0.24, -0.52), "hips_rot": (58, 0, 0), "spine_rot": (24, 0, 0), "chest_rot": (22, 0, 0), "head_rot": (72, 0, 0),
  "grip": (-0.2, 0.28, 0.3), "aim": (-1.0, 0.02, 0.0), "slide": 0.45, "left_on": 1.0, "left_dist": 0.4,
  "pole_r": (-0.7, 0.2, 0.6), "pole_l": (0.7, 0.2, 0.6),
}


def tucked_feet(root):
  return {
    "root": root,
    "foot_r": (-0.13, root - 0.02, 0.1), "foot_r_rot": (40, -4),
    "foot_l": (0.13, root - 0.08, 0.1), "foot_l_rot": (40, 4),
  }


def dodge_clip():
  """A forward roll: it dives on the first frames, carries its speed through the ball, and the
  cost is in getting up. The next action may start at landing, so it leaves no dead time."""
  distance = 3.2
  landed = 2.92
  land_r = (-0.15, landed + 0.12, 0.0)
  land_l = (0.15, landed - 0.12, 0.0)
  return Clip("dodge_forward", 23, timeline(
    (0, dict(GUARD, tumble=0.0, feet_free=0.0)),
    (2, {
      "root": 0.42, "tumble": 16.0, "feet_free": 0.0,
      "hips_pos": (0.0, 0.08, -0.3), "hips_rot": (38, 4, 0), "spine_rot": (14, 0, 0), "chest_rot": (14, 0, 0), "head_rot": (30, 0, 0),
      "foot_r": (GUARD["foot_r"][0], GUARD["foot_r"][1] + 0.3, 0.0), "foot_r_rot": (0, -6),
      "foot_l": GUARD["foot_l"], "foot_l_rot": (42, 20),
      "grip": (-0.26, 0.3, 0.68), "aim": (-0.78, 0.45, -0.25), "slide": 0.3, "left_on": 0.3,
    }),
    (4, dict(TUCK, tumble=66.0, feet_free=1.0, **tucked_feet(1.05))),
    (7, dict(TUCK, tumble=160.0, feet_free=1.0, **tucked_feet(1.8))),
    (10, dict(TUCK, tumble=258.0, feet_free=1.0, **tucked_feet(2.42))),
    (13, dict(TUCK, tumble=340.0, feet_free=1.0, **tucked_feet(2.8))),
    (15, {
      "root": landed, "tumble": 360.0, "feet_free": 0.0,
      "hips_pos": (0.0, -0.1, -0.46), "hips_rot": (40, 4, 0), "spine_rot": (14, 0, 0), "chest_rot": (12, 0, 0), "head_rot": (22, 0, 0),
      "foot_r": land_r, "foot_r_rot": (0, -8), "foot_l": land_l, "foot_l_rot": (0, 12),
      "grip": (-0.26, 0.24, 0.5), "aim": (-0.9, 0.42, -0.1), "slide": 0.4, "left_on": 1.0,
    }),
    (17, {"left_on": 0.4, "foot_r": land_r, "foot_r_rot": (24, -8), "foot_l": land_l, "foot_l_rot": (0, 18)}),
    (18, {"root": 3.08, "hips_pos": (0.0, -0.03, -0.3), "hips_rot": (24, 10, 0), "head_rot": (12, 0, 0)}),
    (20, {"foot_r": (-0.16, distance + 0.1, 0.07), "foot_r_rot": (6, -8), "foot_l": (0.18, distance - 0.2, 0.0), "foot_l_rot": (0, 26)}),
    (23, recovery(distance)),
  ))


def recovery(distance):
  """Back to guard, standing where the clip's root motion ended."""
  return {
    "root": distance, "hips_pos": GUARD["hips_pos"], "hips_rot": GUARD["hips_rot"], "spine_rot": GUARD["spine_rot"],
    "chest_rot": GUARD["chest_rot"], "head_rot": GUARD["head_rot"], "grip": GUARD["grip"], "aim": GUARD["aim"],
    "slide": GUARD["slide"], "left_on": GUARD["left_on"], "hand_l": GUARD["hand_l"], "pole_r": GUARD["pole_r"], "pole_l": GUARD["pole_l"],
    "foot_r": (GUARD["foot_r"][0], GUARD["foot_r"][1] + distance, 0.0), "foot_r_rot": GUARD["foot_r_rot"],
    "foot_l": (GUARD["foot_l"][0], GUARD["foot_l"][1] + distance, 0.0), "foot_l_rot": GUARD["foot_l_rot"],
  }


def held(pose, root):
  """A chain pose at some point of its own clip: its feet are stored relative to the root."""
  shifted = dict(pose, root=root)
  for foot in ("foot_r", "foot_l"):
    x, forward, z = pose[foot]
    shifted[foot] = (x, forward + root, z)
  return shifted


# Where each blow stands when the next step may start, with feet relative to its root: the
# next one opens here, so the blend between them has nothing to travel.
AFTER_CUT = dict(GUARD, **{
  "hips_pos": (-0.03, 0.07, -0.21), "hips_rot": (24, 38, -4), "spine_rot": (7, 14, 0), "chest_rot": (8, 16, 0),
  "head_rot": (14, 10, 0), "grip": (0.22, 0.4, 0.74), "aim": (0.74, 0.46, -0.5), "slide": 0.0, "left_on": 1.0,
  "foot_r": (-0.16, 0.21, 0.0), "foot_l": (0.18, -0.6, 0.09), "foot_l_rot": (30, 24),
  "pole_r": (-0.6, -0.25, -1.0), "pole_l": (0.7, -0.25, -1.0),
})

# The stick reaches its full length here: the right hand slides to its end and the left lets go.
AFTER_SWEEP = dict(GUARD, **{
  "hips_pos": (0.03, 0.04, -0.2), "hips_rot": (5, -44, 4), "spine_rot": (2, -12, 0), "chest_rot": (-3, -20, 0),
  "head_rot": (6, -12, 0), "grip": (-0.46, 0.2, 1.36), "aim": (-0.86, -0.1, 0.46), "slide": -0.42, "left_on": 0.0,
  "hand_l": (0.42, -0.1, 1.05), "foot_r": (-0.16, -0.25, 0.0), "foot_r_rot": (30, -12), "foot_l": (0.19, 0.09, 0.0), "foot_l_rot": (0, 8),
  "pole_r": (-0.6, -0.25, -1.0), "pole_l": (0.7, -0.25, -1.0),
})

# dodge_forward at the frame the next action may start.
AFTER_ROLL = dict(GUARD, **{
  "hips_pos": (0.0, -0.1, -0.46), "hips_rot": (40, 4, 0), "spine_rot": (14, 0, 0), "chest_rot": (12, 0, 0), "head_rot": (22, 0, 0),
  "foot_r": (-0.15, 0.12, 0.0), "foot_r_rot": (0, -8), "foot_l": (0.15, -0.12, 0.0), "foot_l_rot": (0, 12),
  "grip": (-0.26, 0.24, 0.5), "aim": (-0.9, 0.42, -0.1), "slide": 0.4, "left_on": 1.0, "left_dist": 0.4,
})


def attack_clip():
  """The opener: a fast diagonal cut from the right shoulder on a long step. The hips travel
  from -26 to 38 degrees, and that turn is what sells the swing."""
  distance = 0.85
  end_r = (GUARD["foot_r"][0], GUARD["foot_r"][1] + distance, 0.0)
  raised = {
    "hips_pos": (0.03, -0.05, -0.085), "hips_rot": (-3, -26, 3), "spine_rot": (1, -14, 0), "chest_rot": (-1, -20, 0), "head_rot": (5, -8, 0),
    "grip": (-0.32, -0.07, 1.54), "aim": (-0.46, -0.76, 0.46),
  }
  return Clip("attack_light_1", 24, timeline(
    (0, dict(GUARD)),
    (2, {"grip": (-0.22, 0.2, 1.26), "aim": (-0.08, 0.3, 0.95), "slide": 0.0, "pole_r": (-0.6, -0.25, -1.0), "pole_l": (0.7, -0.25, -1.0)}),
    (3, {"left_on": 1.0, "foot_r": GUARD["foot_r"], "foot_r_rot": GUARD["foot_r_rot"]}),
    (4, dict(raised, root=-0.05)),
    (5, dict(raised, root=-0.03, foot_r=(-0.15, 0.3, 0.1), foot_r_rot=(-10, -10), foot_l=GUARD["foot_l"], foot_l_rot=GUARD["foot_l_rot"])),
    (6, {"root": 0.25, "grip": (-0.24, 0.22, 1.42), "aim": (-0.1, 0.35, 0.93)}),
    (7, {
      "root": 0.55, "hips_pos": (-0.02, 0.05, -0.14), "hips_rot": (14, 10, -2), "spine_rot": (5, 8, 0), "chest_rot": (6, 10, 0), "head_rot": (10, 2, 0),
      "grip": (-0.03, 0.55, 1.05), "aim": (0.3, 0.9, 0.2), "foot_r": end_r, "foot_r_rot": (-4, -10),
      "foot_l": (0.18, -0.05, 0.05), "foot_l_rot": (28, 22),
    }),
    (9, dict(held(AFTER_CUT, 0.74), foot_r=end_r, foot_r_rot=GUARD["foot_r_rot"], foot_l=(0.18, 0.02, 0.03), foot_l_rot=(32, 24))),
    (11, {"foot_l": (0.18, 0.12, 0.07), "foot_l_rot": (34, 24)}),
    (13, held(AFTER_CUT, 0.8)),
    (15, held(AFTER_CUT, 0.8)),
    (19, {"foot_l": (0.18, 0.65, 0.0), "foot_l_rot": GUARD["foot_l_rot"], "hips_rot": (12, 26, -1), "root": 0.83}),
    (24, recovery(distance)),
  ))


def attack_2_clip():
  """The sweep: the cut's low pose winds further, the left foot crosses over and the stick
  whips around at full length, pulled through the right hand as the left lets go."""
  distance = 0.75
  planted_r = AFTER_CUT["foot_r"]
  planted_l = (0.19, 0.55, 0.0)
  return Clip("attack_light_2", 26, timeline(
    (0, dict(AFTER_CUT)),
    (2, {
      "hips_rot": (20, 46, -3), "chest_rot": (8, 22, 0), "grip": (0.32, 0.28, 0.76), "aim": (0.86, 0.24, -0.46),
      "foot_r": planted_r, "foot_r_rot": GUARD["foot_r_rot"],
    }),
    (3, {"root": 0.05, "grip": (0.33, 0.3, 0.8), "aim": (0.88, 0.3, -0.38), "foot_l": (0.2, -0.3, 0.1), "foot_l_rot": (24, 18)}),
    (5, {
      "root": 0.25, "hips_pos": (0.0, 0.05, -0.15), "hips_rot": (10, 0, 1), "spine_rot": (4, -6, 0), "chest_rot": (2, -10, 0), "head_rot": (8, -2, 0),
      "grip": (0.02, 0.6, 1.02), "aim": (0.12, 0.93, 0.3), "slide": 0.0, "left_on": 1.0, "hand_l": (0.3, 0.3, 1.0), "foot_l": (0.2, 0.3, 0.12), "foot_l_rot": (-8, 10),
    }),
    (7, {
      "root": 0.36, "hips_rot": (6, -30, 3), "spine_rot": (2, -12, 0), "chest_rot": (-2, -18, 0), "head_rot": (6, -12, 0),
      "grip": (-0.3, 0.5, 1.3), "aim": (-0.78, 0.5, 0.34), "slide": -0.25, "left_on": 0.2, "foot_l": planted_l, "foot_l_rot": (-4, 8),
    }),
    (9, dict(held(AFTER_SWEEP, 0.42), foot_r=planted_r, foot_l=planted_l)),
    (14, dict(held(AFTER_SWEEP, 0.46), foot_r=planted_r, foot_l=planted_l)),
    (19, {"foot_r": (-0.16, 0.72, 0.1), "foot_r_rot": (6, -10), "foot_l": planted_l, "foot_l_rot": (0, 8), "root": 0.62}),
    (26, recovery(distance)),
  ))


def attack_3_clip():
  """The closer: it jumps out of the sweep, whirls the stick overhead through a full turn in the
  air and comes down with both hands into the ground, staying low long enough to pay for it."""
  distance = 1.15
  high = {"grip": (-0.05, 0.25, 1.72), "aim": (0.0, 1.0, 0.03), "slide": 0.2}
  raised = {"grip": (-0.12, -0.08, 1.66), "aim": (-0.12, -0.88, 0.42), "slide": 0.0}
  body = {"hips_pos": (0.0, 0.0, -0.1), "hips_rot": (0, -10, 0), "spine_rot": (0, 0, 0), "chest_rot": (-4, 0, 0), "head_rot": (4, 0, 0)}
  slam = {
    "hips_pos": (-0.01, 0.09, -0.36), "hips_rot": (36, 6, 0), "spine_rot": (10, 0, 0), "chest_rot": (12, 0, 0), "head_rot": (18, 0, 0),
    "grip": (0.0, 0.6, 0.62), "aim": (0.02, 0.8, -0.6), "slide": 0.0, "left_on": 1.0,
    "foot_r": (-0.17, 1.14, 0.0), "foot_r_rot": GUARD["foot_r_rot"], "foot_l": (0.19, 0.6, 0.0), "foot_l_rot": (36, 8),
  }
  air_feet = lambda root: {
    "foot_r": (-0.14, root - 0.1, 0.26), "foot_r_rot": (20, -5), "foot_l": (0.14, root + 0.14, 0.42), "foot_l_rot": (-10, 5),
  }
  return Clip("attack_light_3", 40, timeline(
    (0, dict(AFTER_SWEEP, spin=0.0, lift=0.0, feet_free=0.0)),
    (2, {
      "hips_pos": (0.02, -0.02, -0.32), "hips_rot": (16, -30, 2), "spine_rot": (4, -8, 0), "chest_rot": (6, -16, 0), "head_rot": (8, -8, 0),
      "grip": (-0.3, 0.1, 1.5), "aim": (-0.4, -0.4, 0.82), "slide": 0.0, "feet_free": 0.0, "lift": 0.0,
      "foot_r": AFTER_SWEEP["foot_r"], "foot_r_rot": (10, -12), "foot_l": AFTER_SWEEP["foot_l"], "foot_l_rot": (0, 8),
    }),
    (3, {"left_on": 1.0, "spin": 8.0}),
    (5, dict(body, **high, **air_feet(0.25), root=0.25, lift=0.2, spin=70.0, feet_free=1.0)),
    (8, dict(high, **air_feet(0.5), root=0.5, lift=0.4, spin=205.0, feet_free=1.0)),
    (10, dict(raised, **air_feet(0.7), root=0.7, lift=0.42, spin=320.0, hips_rot=(-8, 0, 0), chest_rot=(-10, 0, 0), head_rot=(2, 0, 0), feet_free=1.0)),
    (11, dict(raised, root=0.78, lift=0.36, spin=360.0)),
    (12, {"root": 0.86, "lift": 0.26, "grip": (-0.08, 0.42, 1.46), "aim": (-0.05, 0.5, 0.86), "hips_rot": (10, 0, 0)}),
    (13, {
      "root": 0.92, "lift": 0.12, "feet_free": 0.6, "grip": (-0.03, 0.66, 1.0), "aim": (0.0, 0.94, 0.08),
      "hips_pos": (-0.01, 0.06, -0.2), "hips_rot": (26, 4, 0), "spine_rot": (8, 0, 0), "chest_rot": (10, 0, 0), "head_rot": (16, 0, 0),
    }),
    (14, dict(slam, root=0.96, lift=0.0, feet_free=0.0)),
    (16, dict(slam, root=0.98, hips_pos=(-0.01, 0.1, -0.42))),
    (26, dict(slam, root=1.0, hips_pos=(-0.01, 0.1, -0.4), hips_rot=(33, 6, 0))),
    (32, {"foot_l": (0.19, 0.85, 0.1), "foot_l_rot": (20, 14), "root": 1.08}),
    (40, recovery(distance)),
  ))


def attack_roll_clip():
  """Out of a roll: it stays low, pulls the stick back at the hip and drives a one-handed thrust
  on a long lunge. The stick's whole length goes ahead of the hand."""
  distance = 1.1
  lunge_r = (-0.17, 1.45, 0.0)
  lunge_l = (0.18, 0.34, 0.0)
  thrust = {
    "hips_pos": (-0.02, 0.12, -0.32), "hips_rot": (30, 20, -2), "spine_rot": (8, 8, 0), "chest_rot": (8, 10, 0), "head_rot": (12, 8, 0),
    "grip": (-0.05, 0.75, 1.12), "aim": (0.02, 1.0, 0.02), "slide": -0.38, "left_on": 0.0, "hand_l": (0.34, -0.3, 1.0),
    "pole_r": (-0.6, -0.5, -0.8), "pole_l": (0.6, -0.6, -0.6),
    "foot_r": lunge_r, "foot_r_rot": GUARD["foot_r_rot"], "foot_l": lunge_l, "foot_l_rot": (40, 22),
  }
  return Clip("attack_roll", 24, timeline(
    (0, dict(AFTER_ROLL)),
    (3, {
      "root": 0.1, "hips_pos": (0.0, -0.06, -0.36), "hips_rot": (24, -20, 0), "chest_rot": (6, -16, 0), "head_rot": (12, -2, 0),
      "grip": (-0.2, -0.2, 0.95), "aim": (0.05, 0.95, 0.05), "slide": 0.0, "left_on": 0.8,
      "foot_r": AFTER_ROLL["foot_r"], "foot_r_rot": AFTER_ROLL["foot_r_rot"], "foot_l": AFTER_ROLL["foot_l"], "foot_l_rot": (24, 14),
    }),
    (5, {"root": 0.5, "foot_r": (-0.16, 0.9, 0.12), "foot_r_rot": (-10, -8), "foot_l": AFTER_ROLL["foot_l"]}),
    (7, dict(thrust, root=0.85)),
    (13, dict(thrust, root=0.95)),
    (18, {"foot_l": (0.18, 0.75, 0.08), "foot_l_rot": (24, 18), "root": 1.02}),
    (24, recovery(distance)),
  ))


def attack_run_clip():
  """Out of a sprint: the left foot plants and the run's speed throws the stick from low behind
  the body up over the left shoulder, on two hands. The root brakes from sprint speed."""
  distance = 2.35
  plant_l = (0.13, 0.78, 0.0)
  finish = {
    "hips_pos": (0.01, 0.03, -0.14), "hips_rot": (-6, 34, -4), "spine_rot": (-2, 10, 0), "chest_rot": (-10, 16, 0), "head_rot": (-6, 10, 0),
    "grip": (0.26, 0.24, 1.55), "aim": (0.55, 0.08, 0.83),
  }
  landed_r = (-0.16, 2.4, 0.0)
  return Clip("attack_run", 30, timeline(
    (0, {
      "root": 0.0, "hips_pos": (0.0, 0.05, -0.1), "hips_rot": (19, 0, 0), "spine_rot": (5, 0, 0), "chest_rot": (3, 0, 0), "head_rot": (6, 0, 0),
      "foot_r": (-0.125, -0.35, 0.12), "foot_r_rot": (30, -5), "foot_l": (0.125, 0.3, 0.06), "foot_l_rot": (-6, 5),
      "grip": (-0.33, 0.08, 0.99), "aim": (0.05, 0.93, 0.36), "slide": 0.5, "left_on": 0.0, "left_dist": 0.38,
      "hand_l": (0.25, 0.1, 1.04), "pole_r": (-0.5, -0.8, -0.6), "pole_l": (0.5, -0.9, -0.5),
    }),
    (2, {
      "root": 0.44, "hips_pos": (0.0, 0.02, -0.2), "hips_rot": (26, -22, 3), "spine_rot": (6, -8, 0), "chest_rot": (6, -10, 0), "head_rot": (8, 0, 0),
      "foot_l": plant_l, "foot_l_rot": (-4, 5), "foot_r": (-0.14, 0.1, 0.2), "foot_r_rot": (40, -5),
      "grip": (-0.42, -0.2, 0.82), "aim": (-0.3, -0.62, -0.5), "slide": 0.0, "left_on": 0.6,
    }),
    (3, {"left_on": 1.0}),
    (4, {"root": 0.9, "hips_rot": (22, -14, 2), "grip": (-0.4, -0.05, 0.72), "aim": (-0.35, 0.4, -0.55), "foot_l": plant_l, "pole_r": (-0.6, -0.25, -1.0), "pole_l": (0.7, -0.25, -1.0)}),
    (6, {
      "root": 1.3, "hips_pos": (0.0, 0.06, -0.24), "hips_rot": (14, 8, -1), "spine_rot": (4, 6, 0), "chest_rot": (0, 10, 0), "head_rot": (2, 4, 0),
      "grip": (-0.12, 0.5, 0.82), "aim": (0.0, 0.85, -0.5), "foot_l": plant_l, "foot_l_rot": (22, 6), "foot_r": (-0.15, 1.1, 0.22), "foot_r_rot": (-12, -6),
    }),
    (8, {
      "root": 1.62, "hips_rot": (0, 22, -3), "chest_rot": (-8, 14, 0), "head_rot": (-4, 8, 0), "grip": (0.1, 0.52, 1.25), "aim": (0.3, 0.75, 0.6),
      "foot_r": (-0.16, 2.1, 0.1), "foot_r_rot": (-10, -6), "foot_l": (0.14, 1.0, 0.1), "foot_l_rot": (48, 10),
    }),
    (10, dict(finish, root=1.85, foot_r=landed_r, foot_r_rot=(-2, -8), foot_l=(0.15, 1.35, 0.16), foot_l_rot=(40, 14))),
    (13, dict(finish, root=2.1, foot_r=landed_r, foot_r_rot=GUARD["foot_r_rot"], foot_l=(0.17, 1.85, 0.06), foot_l_rot=(20, 18))),
    (18, dict(finish, root=2.25, foot_r=landed_r, foot_l=(0.18, 2.05, 0.0), foot_l_rot=GUARD["foot_l_rot"], left_on=1.0, slide=0.0)),
    (30, recovery(distance)),
  ))


def attack_heavy_clip():
  """The heavy blow: both hands haul the stick behind the head, the body holds there leaning back
  long enough to read, and all of it comes down on a long step into the ground."""
  distance = 0.9
  raised = {"grip": (-0.14, -0.1, 1.62), "aim": (-0.1, -0.86, 0.5), "slide": 0.0}
  slam = {
    "hips_pos": (-0.01, 0.09, -0.38), "hips_rot": (38, 6, 0), "spine_rot": (10, 0, 0), "chest_rot": (12, 0, 0), "head_rot": (18, 0, 0),
    "grip": (0.0, 0.6, 0.6), "aim": (0.02, 0.8, -0.6), "slide": 0.0,
    "foot_r": (-0.17, 0.92, 0.0), "foot_r_rot": GUARD["foot_r_rot"], "foot_l": (0.19, 0.2, 0.0), "foot_l_rot": (36, 8),
  }
  return Clip("attack_heavy", 36, timeline(
    (0, dict(GUARD)),
    (3, {"grip": (-0.24, 0.18, 1.3), "aim": (-0.1, 0.3, 0.95), "slide": 0.0, "left_on": 0.6, "pole_r": (-0.6, -0.25, -1.0), "pole_l": (0.7, -0.25, -1.0)}),
    (6, dict(raised, root=-0.06, left_on=1.0, hips_pos=(0.0, -0.06, -0.14), hips_rot=(-8, -14, 0), chest_rot=(-8, -10, 0), head_rot=(0, -4, 0))),
    (11, dict(raised, root=-0.08, hips_pos=(0.0, -0.08, -0.16), foot_r=GUARD["foot_r"], foot_r_rot=GUARD["foot_r_rot"], foot_l=GUARD["foot_l"], foot_l_rot=GUARD["foot_l_rot"])),
    (13, {
      "root": 0.4, "hips_pos": (0.0, 0.02, -0.2), "hips_rot": (10, 2, 0), "chest_rot": (0, 4, 0), "head_rot": (8, 0, 0),
      "grip": (-0.08, 0.42, 1.46), "aim": (-0.05, 0.5, 0.86), "foot_r": (-0.16, 0.62, 0.12), "foot_r_rot": (-10, -8),
    }),
    (14, {"root": 0.7, "grip": (-0.03, 0.66, 1.0), "aim": (0.0, 0.94, 0.08)}),
    (16, dict(slam, root=0.84)),
    (18, dict(slam, root=0.86, hips_pos=(-0.01, 0.1, -0.43))),
    (27, dict(slam, root=0.88, hips_rot=(35, 6, 0))),
    (32, {"foot_l": (0.19, 0.7, 0.08), "foot_l_rot": (20, 14)}),
    (36, recovery(distance)),
  ))


def hurt_clip():
  """Thrown back by a blow: the chest goes first, the left foot catches the weight and the stick
  flies out to the side before the guard comes back."""
  return Clip("hurt", 15, timeline(
    (0, dict(GUARD)),
    (3, {
      "hips_pos": (0.02, -0.1, -0.18), "hips_rot": (-8, 22, -3), "spine_rot": (-6, 6, 0), "chest_rot": (-12, 8, 0), "head_rot": (-16, 6, 0),
      "grip": (-0.42, 0.02, 1.06), "aim": (-0.55, 0.6, 0.55), "hand_l": (0.42, -0.05, 1.1), "foot_l": (0.19, -0.34, 0.04), "foot_l_rot": (18, 26),
    }),
    (6, {"hips_pos": (0.01, -0.08, -0.2), "foot_l": (0.19, -0.38, 0.0), "foot_l_rot": (0, 28)}),
    (15, recovery(0.0)),
  ))


def death_clip():
  """The knees give first, then the whole body tips back onto the ground. It holds its last frame."""
  return Clip("death", 27, timeline(
    (0, dict(GUARD, tumble=0.0, lift=0.0, feet_free=0.0)),
    (5, {
      "hips_pos": (0.0, -0.05, -0.42), "hips_rot": (-6, 20, 4), "chest_rot": (-14, 0, 0), "head_rot": (-10, 8, 0),
      "grip": (-0.42, 0.04, 0.92), "aim": (-0.6, 0.6, -0.5), "hand_l": (0.42, 0.02, 0.82),
    }),
    (8, {"tumble": 0.0, "feet_free": 0.0, "lift": 0.0}),
    (16, {"tumble": -55.0, "feet_free": 0.7, "lift": -0.08}),
    (22, {"tumble": -93.0, "feet_free": 1.0, "lift": -0.3}),
    (25, {"tumble": -86.0}),
    (27, {"tumble": -88.0}),
  ))


# PlayerController::LOCK_SPEED must match this speed.
LOCK_SPEED = 2.2
LOCK_FRAMES = 12
LOCK_STANCE = 0.5


def lock_foot(home_x, offset, move):
  """A run foot's path, centred under the body and turned towards the direction of travel."""
  path = run_foot(0.0, offset, LOCK_SPEED, LOCK_FRAMES, LOCK_STANCE, 0.45)
  center = LANDING_REACH - LOCK_SPEED * LOCK_FRAMES / AUTHOR_FPS * LOCK_STANCE * 0.5

  def position(phase):
    _, along, height = path(phase)
    return (home_x + move[0] * (along - center), move[1] * (along - center), height)

  return position


def lock_clip(name, move, feet_apart):
  """Walking around a locked target in guard. The stride is short and the feet wide, so a
  sidestep does not cross the legs. move is (left, forward)."""
  hips_x, hips_forward, hips_z = GUARD["hips_pos"]
  pitch, yaw, _ = GUARD["hips_rot"]
  channels = {key: [(0, GUARD[key])] for key in (
    "spine_rot", "chest_rot", "head_rot", "grip", "aim", "slide", "left_on", "left_dist", "hand_l", "pole_r", "pole_l",
  )}
  channels.update({
    "root": [(0, 0.0)],
    "hips_pos": lambda p: (hips_x + 0.02 * wave(p, 0.25), hips_forward, hips_z + 0.014 * wave(p, 0.1, 2)),
    "hips_rot": lambda p: (pitch, yaw, 5 * move[0] + 1.5 * wave(p, 0.25)),
    "foot_l": lock_foot(feet_apart, 0.0, move),
    "foot_r": lock_foot(-feet_apart, 0.5, move),
    "foot_l_rot": [(0, (0, 10))],
    "foot_r_rot": [(0, (0, -10))],
  })
  return Clip(name, LOCK_FRAMES, channels, loop=True)


def run_start_clip():
  """The first two steps from a stand. Ends on the frame the run clip's left foot lands, and
  the stance foot moves back at run speed from the moment it touches down."""
  step = RUN_SPEED / AUTHOR_FPS
  return Clip("run_start", 10, timeline(
    (0, dict(GUARD)),
    (2, {"hips_pos": (0.0, 0.04, -0.14), "hips_rot": (20, 8, 0), "foot_r": (-0.15, 0.2, 0.14), "foot_r_rot": (-5, -6), "foot_l": GUARD["foot_l"], "foot_l_rot": (30, 20)}),
    (5, {
      "hips_pos": (0.0, 0.05, -0.1), "hips_rot": (22, -6, -3), "spine_rot": (5, 6, 0), "chest_rot": (4, 8, 0), "head_rot": (7, 0, 0),
      "foot_r": (-0.125, LANDING_REACH, 0.0), "foot_r_rot": (-8, -5), "foot_l": (0.125, -0.25, 0.22), "foot_l_rot": (58, 5),
      "grip": (-0.33, 0.0, 0.98), "aim": (0.05, 0.93, 0.36), "slide": 0.5, "hand_l": (0.25, 0.3, 1.0),
      "pole_r": (-0.5, -0.8, -0.6), "pole_l": (0.5, -0.9, -0.5),
    }),
    (10, {
      "hips_pos": (0.018, 0.05, -0.05), "hips_rot": (13, -9, -2), "spine_rot": (5, 7, 0), "chest_rot": (4, 8, 0), "head_rot": (7, 0, 0),
      "foot_r": (-0.125, LANDING_REACH - 5 * step, 0.0), "foot_r_rot": (24, -5), "foot_l": (0.125, LANDING_REACH, 0.0), "foot_l_rot": (-8, 5),
      "grip": (-0.33, 0.19, 0.96), "aim": (0.07, 0.93, 0.39), "hand_l": (0.25, -0.15, 1.12),
    }),
  ))


def run_stop_clip():
  """Braking from a run: the right foot digs in ahead, the body leans back against its own
  weight and the stick carries on forward before it settles."""
  return Clip("run_stop", 15, timeline(
    (0, {
      "root": 0.0, "hips_pos": (0.0, 0.05, -0.075), "hips_rot": (11, 0, 0), "spine_rot": (5, 0, 0), "chest_rot": (3, 0, 0), "head_rot": (6, 0, 0),
      "foot_r": (-0.125, -0.1, 0.1), "foot_r_rot": (20, -5), "foot_l": (0.125, 0.1, 0.0), "foot_l_rot": (0, 5),
      "grip": (-0.33, 0.08, 0.99), "aim": (0.05, 0.93, 0.36), "slide": 0.5, "left_on": 0.0, "left_dist": 0.38,
      "hand_l": (0.25, 0.1, 1.04), "pole_r": (-0.5, -0.8, -0.6), "pole_l": (0.5, -0.9, -0.5),
    }),
    (3, {
      "hips_pos": (0.0, -0.1, -0.2), "hips_rot": (-6, 6, 0), "chest_rot": (-2, -4, 0), "head_rot": (2, 0, 0),
      "foot_r": (-0.15, 0.42, 0.0), "foot_r_rot": (-14, -6), "foot_l": (0.14, -0.1, 0.0), "foot_l_rot": (26, 10),
      "grip": (-0.34, 0.3, 0.96), "aim": (-0.1, 0.9, 0.0), "hand_l": (0.3, 0.2, 1.0),
    }),
    (6, {"hips_pos": (0.0, -0.05, -0.2), "hips_rot": (3, 10, 0), "foot_r": (-0.15, 0.42, 0.0), "foot_r_rot": (0, -8), "grip": (-0.34, 0.26, 0.9), "aim": (-0.22, 0.86, -0.3), "slide": 0.1}),
    (10, {"foot_r": (-0.15, 0.3, 0.05), "foot_r_rot": (4, -8), "foot_l": GUARD["foot_l"], "foot_l_rot": GUARD["foot_l_rot"], "hips_pos": (0.01, -0.02, -0.14)}),
    (15, recovery(0.0)),
  ))


def run_turn_clip():
  """A hard turn at speed, played while the model swings around: the outside foot plants wide,
  the body drops into the corner and the stick trails."""
  return Clip("run_turn", 13, timeline(
    (0, {
      "root": 0.0, "hips_pos": (0.0, 0.05, -0.075), "hips_rot": (11, 0, 0), "spine_rot": (5, 0, 0), "chest_rot": (3, 0, 0), "head_rot": (6, 0, 0),
      "foot_r": (-0.125, 0.1, 0.0), "foot_r_rot": (0, -5), "foot_l": (0.125, -0.1, 0.1), "foot_l_rot": (20, 5),
      "grip": (-0.33, 0.08, 0.99), "aim": (0.05, 0.93, 0.36), "slide": 0.5, "left_on": 0.0, "left_dist": 0.38,
      "hand_l": (0.25, 0.1, 1.04), "pole_r": (-0.5, -0.8, -0.6), "pole_l": (0.5, -0.9, -0.5),
    }),
    (3, {
      "hips_pos": (0.08, -0.04, -0.24), "hips_rot": (6, 22, 8), "spine_rot": (6, 8, 4), "chest_rot": (4, 10, 3), "head_rot": (6, 24, 0),
      "foot_r": (-0.38, 0.2, 0.0), "foot_r_rot": (-10, -28), "foot_l": (0.2, -0.22, 0.14), "foot_l_rot": (34, 14),
      "grip": (-0.4, -0.12, 0.92), "aim": (-0.3, 0.84, 0.44), "hand_l": (0.4, 0.2, 1.1),
    }),
    (7, {"hips_pos": (0.06, 0.0, -0.2), "hips_rot": (10, 12, 6), "foot_r": (-0.34, 0.14, 0.0), "foot_r_rot": (6, -20), "foot_l": (0.18, 0.2, 0.16), "foot_l_rot": (-6, 8)}),
    (13, {
      "hips_pos": (0.018, 0.05, -0.05), "hips_rot": (13, -9, -2), "spine_rot": (5, 7, 0), "chest_rot": (4, 8, 0), "head_rot": (7, 0, 0),
      "foot_r": (-0.125, -0.05, 0.05), "foot_r_rot": (24, -5), "foot_l": (0.125, LANDING_REACH, 0.0), "foot_l_rot": (-8, 5),
      "grip": (-0.33, 0.19, 0.96), "aim": (0.07, 0.93, 0.39), "hand_l": (0.25, -0.15, 1.12),
    }),
  ))


CLIPS = [
  idle_clip(),
  run_clip("run-loop", RUN_SPEED, RUN_FRAMES, STANCE_SHARE, lean=11, drop=-0.075, swing=0.25),
  # SPRINT_SPEED in PlayerController must match this speed.
  run_clip("sprint-loop", 6.8, 15, 0.26, lean=19, drop=-0.1, swing=0.34),
  # WALK_SPEED in PlayerController must match this speed.
  run_clip("walk-loop", WALK_SPEED, 24, 0.58, lean=4, drop=-0.05, swing=0.12, step=0.35),
  run_start_clip(),
  run_stop_clip(),
  run_turn_clip(),
  jump_clip(),
  fall_clip(),
  land_clip(),
  dodge_clip(),
  attack_clip(),
  attack_2_clip(),
  attack_3_clip(),
  attack_roll_clip(),
  attack_run_clip(),
  air_attack_clip(),
  attack_heavy_clip(),
  hurt_clip(),
  death_clip(),
  lock_clip("walk_back-loop", (0.0, -1.0), 0.15),
  lock_clip("strafe_left-loop", (1.0, 0.0), 0.2),
  lock_clip("strafe_right-loop", (-1.0, 0.0), 0.2),
]


def build_stick(armature):
  """Placeholder weapon: it follows the weapon bone, so swapping the mesh keeps every clip."""
  stale = bpy.data.objects.get("stick")
  if stale:
    bpy.data.objects.remove(stale)
  rest = armature.data.bones["weapon"]
  sides = 6
  verts = []
  for along in (-STICK_BACK, STICK_FRONT):
    for side in range(sides):
      angle = math.tau * side / sides
      offset = Vector((math.cos(angle) * STICK_RADIUS, along, math.sin(angle) * STICK_RADIUS))
      verts.append(tuple(rest.head_local + rest.matrix_local.to_3x3() @ offset))
  faces = [[i, (i + 1) % sides, sides + (i + 1) % sides, sides + i] for i in range(sides)]
  faces += [list(range(sides - 1, -1, -1)), list(range(sides, sides * 2))]
  mesh = bpy.data.meshes.new("stick")
  mesh.from_pydata(verts, [], faces)
  material = bpy.data.materials.get("stick") or bpy.data.materials.new("stick")
  material.diffuse_color = (0.22, 0.13, 0.07, 1.0)
  # The exporter reads the node, not the viewport color.
  material.use_nodes = True
  bsdf = material.node_tree.nodes.get("Principled BSDF")
  bsdf.inputs["Base Color"].default_value = material.diffuse_color
  bsdf.inputs["Roughness"].default_value = 0.9
  mesh.materials.append(material)
  stick = bpy.data.objects.new("stick", mesh)
  bpy.context.scene.collection.objects.link(stick)
  stick.parent = armature
  stick.vertex_groups.new(name="weapon").add(list(range(len(verts))), 1.0, "REPLACE")
  stick.modifiers.new("armature", "ARMATURE").object = armature
  return stick


def bake(armature, rig, clip):
  stale = bpy.data.actions.get(clip.name)
  if stale:
    bpy.data.actions.remove(stale)
  action = bpy.data.actions.new(clip.name)
  action.use_fake_user = True
  armature.animation_data.action = action
  bones = armature.pose.bones
  moved = ("root", "hips", "weapon")
  previous = {}
  rig.max_stretch = 0.0
  steps = clip.frames * BAKE_FPS // AUTHOR_FPS
  for step in range(steps + 1):
    rig.solve(clip.sample(step * AUTHOR_FPS / BAKE_FPS))
    for name, (location, rotation) in rig.local.items():
      # A quaternion and its negative are the same turn, but they interpolate the long way.
      if name in previous and previous[name].dot(rotation) < 0:
        rotation = -rotation
      previous[name] = rotation
      bone = bones[name]
      bone.rotation_quaternion = rotation
      bone.keyframe_insert("rotation_quaternion", frame=step)
      if name in moved:
        bone.location = location
        bone.keyframe_insert("location", frame=step)
  print("clip", clip.name, "frames", steps, "seconds", round(steps / BAKE_FPS, 3), "max stretch", round(rig.max_stretch, 3))


def export(armature, body, stick):
  for other in bpy.data.objects:
    other.hide_set(other not in (armature, body, stick))
  display_x = armature.location.x
  armature.location.x = 0.0
  armature.animation_data.action = None
  for bone in armature.pose.bones:
    bone.matrix_basis = Matrix.Identity(4)
  bpy.ops.export_scene.gltf(
    filepath=GLB_PATH,
    export_format="GLB",
    use_visible=True,
    export_animations=True,
    export_animation_mode="ACTIONS",
    export_force_sampling=True,
    export_frame_step=1,
  )
  armature.location.x = display_x
  for other in bpy.data.objects:
    other.hide_set(False)


def main():
  scene = bpy.context.scene
  scene.render.fps = BAKE_FPS
  armature = bpy.data.objects["armature_male"]
  body = bpy.data.objects["protagonist_male"]
  stick = build_stick(armature)
  armature.animation_data_create()
  rig = Rig(armature)
  for clip in CLIPS:
    bake(armature, rig, clip)
  export(armature, body, stick)
  bpy.ops.wm.save_mainfile()


main()
