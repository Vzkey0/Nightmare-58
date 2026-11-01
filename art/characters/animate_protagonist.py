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

STICK_BACK = 0.55
STICK_FRONT = 1.05
STICK_RADIUS = 0.019
PALM_LENGTH = 0.095
FINGER_CURL = 75.0

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

  def leg(self, side, ball, pitch, yaw):
    ankle_rest = self.head["foot" + side]
    ball_rest = at(ankle_rest.x, 0.1, 0.0)
    heel_rest = at(ankle_rest.x, -0.09, 0.0)
    delta = rot(pitch, yaw)
    # Up on the toes the foot turns around the ball, and on a heel strike around the heel.
    if pitch >= 0:
      ankle = ball + delta @ (ankle_rest - ball_rest)
    else:
      heel = ball + rot(0, yaw) @ (heel_rest - ball_rest)
      ankle = heel + delta @ (ankle_rest - heel_rest)
    pole = rot(0, yaw * 0.6) @ FORWARD
    self.limb("upper_leg" + side, "lower_leg" + side, ankle, pole + UP * 0.1, FORWARD)
    self.place("foot" + side, delta)
    grounded = 1.0 - min(ball.z / 0.04, 1.0)
    self.place("toes" + side, rot(pitch * (1.0 - grounded), yaw))

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
    root = at(0, pose["root"], 0)
    self.place("root", Quaternion(), root)

    x, forward, z = pose["hips_pos"]
    hips = rot(*pose["hips_rot"])
    spine = hips @ rot(*pose["spine_rot"])
    chest = spine @ rot(*pose["chest_rot"])
    head = rot(*pose["head_rot"])
    self.place("hips", hips, root + self.head["hips"] + at(x, forward, z))
    self.place("spine", spine)
    self.place("chest", chest)
    self.place("neck", chest.slerp(head, 0.5))
    self.place("head", head)

    for side, ball, foot_rot in (("_l", pose["foot_l"], pose["foot_l_rot"]), ("_r", pose["foot_r"], pose["foot_r_rot"])):
      self.leg(side, at(*ball), *foot_rot)

    stick = at(*pose["aim"]).normalized()
    grip = root + at(*pose["grip"])
    shoulder_r = root + self.head["hips"] + at(x, forward, z) + chest @ Vector((-0.2, 0, 0.47))
    shoulder_l = root + self.head["hips"] + at(x, forward, z) + chest @ Vector((0.2, 0, 0.47))

    grip_r, hand_axis = self.grip_delta("_r", shoulder_r, grip, stick)
    self.arm("_r", grip - hand_axis * PALM_LENGTH, at(*pose["pole_r"]), chest)
    self.hand("_r", grip_r, FINGER_CURL)
    self.place("weapon", aim_delta(FORWARD, self.direction("hand_r"), stick, hand_axis), grip - stick * pose["slide"])

    held = max(0.0, min(1.0, pose["left_on"]))
    grip_left = grip - stick * pose["left_dist"]
    grip_l, hand_axis_l = self.grip_delta("_l", shoulder_l, grip_left, stick)
    wrist_held = grip_left - hand_axis_l * PALM_LENGTH
    self.arm("_l", (root + at(*pose["hand_l"])).lerp(wrist_held, held), at(*pose["pole_l"]), chest)
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
RUN_FRAMES = 18
STANCE_SHARE = 0.3
LANDING_REACH = 0.3

SWING_LIFT = [(0.0, 0.0), (0.25, 0.3), (0.55, 0.23), (0.85, 0.09), (1.0, 0.0)]
FOOT_PITCH = [(0.0, -8.0), (0.09, 0.0), (0.2, 12.0), (0.3, 58.0), (0.42, 72.0), (0.72, 24.0), (0.93, -10.0)]


def run_foot(side_x, offset, speed, frames, stance):
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
    return (side_x, forward, interpolate(SWING_LIFT, u, 0))

  return position


def run_clip(name, speed, frames, stance, lean, drop, swing):
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
    "foot_l": run_foot(0.125, 0.0, speed, frames, stance),
    "foot_r": run_foot(-0.125, 0.5, speed, frames, stance),
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


def dodge_clip():
  """A low quickstep: the front foot flies ahead, the body slides over it, the back foot catches."""
  distance = 3.05
  end_r = (GUARD["foot_r"][0], GUARD["foot_r"][1] + distance, 0.0)
  end_l = (GUARD["foot_l"][0], GUARD["foot_l"][1] + distance, 0.0)
  return Clip("dodge_forward", 24, timeline(
    (0, dict(GUARD)),
    (2, {
      "root": 0.05, "hips_pos": (0.0, 0.03, -0.15), "hips_rot": (16, 8, 0), "chest_rot": (6, -3, 0),
      "foot_r": GUARD["foot_r"], "foot_r_rot": GUARD["foot_r_rot"],
      "foot_l": GUARD["foot_l"], "foot_l_rot": GUARD["foot_l_rot"],
    }),
    (3, {"foot_l": GUARD["foot_l"], "foot_l_rot": (28, 24)}),
    (4, {"root": 0.45, "foot_r": (-0.14, 0.75, 0.15), "foot_r_rot": (-5, -4)}),
    (5, {"foot_l": (0.16, 0.05, 0.14), "foot_l_rot": (62, 14)}),
    (7, {
      "root": 1.6, "hips_pos": (0.0, 0.06, -0.2), "hips_rot": (31, 0, -3), "spine_rot": (5, 2, 0), "chest_rot": (6, 3, 2),
      "head_rot": (15, 0, 0), "foot_r": (-0.13, 2.1, 0.2), "foot_r_rot": (-16, -4),
      "grip": (-0.34, -0.1, 0.92), "aim": (0.04, 0.92, 0.34), "slide": 0.45,
      "hand_l": (0.3, -0.34, 1.0), "pole_r": (-0.6, -0.8, -0.5), "pole_l": (0.7, -0.8, -0.4),
    }),
    (8, {"foot_l": (0.15, 1.25, 0.42), "foot_l_rot": (72, 8)}),
    (10, {"root": 2.4, "hips_pos": (0.0, 0.05, -0.21), "hips_rot": (29, 2, -2), "foot_r": (-0.14, 2.95, 0.1), "foot_r_rot": (-12, -8)}),
    (11, {"foot_l": (0.17, 2.1, 0.38), "foot_l_rot": (58, 14)}),
    (12, {
      "root": 2.72, "hips_pos": (0.0, 0.03, -0.25), "hips_rot": (25, 8, 2), "spine_rot": (5, -2, 0), "chest_rot": (5, -3, 0),
      "foot_r": end_r, "foot_r_rot": (-6, -10), "hand_l": (0.3, -0.08, 1.0),
    }),
    (14, {"foot_r": end_r, "foot_r_rot": GUARD["foot_r_rot"], "foot_l": (0.18, 2.6, 0.2), "foot_l_rot": (34, 20)}),
    (15, {"root": 2.95, "hips_pos": (0.0, 0.0, -0.22), "hips_rot": (17, 12, 1), "head_rot": (8, 0, 0)}),
    (17, {"foot_l": end_l, "foot_l_rot": GUARD["foot_l_rot"]}),
    (19, {"root": 3.03, "hips_pos": (0.0, -0.01, -0.12), "hips_rot": (8, 12, 0)}),
    (24, {
      "root": distance, "hips_pos": GUARD["hips_pos"], "hips_rot": GUARD["hips_rot"], "spine_rot": GUARD["spine_rot"],
      "chest_rot": GUARD["chest_rot"], "head_rot": GUARD["head_rot"], "foot_r": end_r, "foot_r_rot": GUARD["foot_r_rot"],
      "foot_l": end_l, "foot_l_rot": GUARD["foot_l_rot"], "grip": GUARD["grip"], "aim": GUARD["aim"],
      "slide": GUARD["slide"], "hand_l": GUARD["hand_l"], "pole_r": GUARD["pole_r"], "pole_l": GUARD["pole_l"],
    }),
  ))


def attack_clip():
  """A diagonal cut from the right shoulder, using the classic souls beats: opening pose,
  a swing faster than physics allows, a held end pose, and an unhurried return."""
  distance = 0.7
  end_r = (GUARD["foot_r"][0], GUARD["foot_r"][1] + distance, 0.0)
  end_l = (GUARD["foot_l"][0], GUARD["foot_l"][1] + distance, 0.0)
  return Clip("attack_light_1", 30, timeline(
    (0, dict(GUARD)),
    (4, {"grip": (-0.22, 0.2, 1.26), "aim": (-0.08, 0.3, 0.95), "slide": 0.0, "pole_r": (-0.6, -0.25, -1.0), "pole_l": (0.7, -0.25, -1.0)}),
    (5, {"left_on": 1.0}),
    (6, {"foot_r": GUARD["foot_r"], "foot_r_rot": GUARD["foot_r_rot"]}),
    (7, {
      "root": -0.05, "hips_pos": (0.03, -0.04, -0.075), "hips_rot": (-2, -12, 2), "spine_rot": (1, -12, 0),
      "chest_rot": (0, -14, 0), "head_rot": (5, -8, 0), "grip": (-0.3, -0.03, 1.5), "aim": (-0.42, -0.72, 0.52),
    }),
    (9, {
      "root": -0.03, "hips_pos": (0.03, -0.05, -0.085), "hips_rot": (-3, -14, 2), "chest_rot": (-1, -15, 0),
      "grip": (-0.32, -0.07, 1.54), "aim": (-0.46, -0.76, 0.46), "foot_r": (-0.15, 0.3, 0.1), "foot_r_rot": (-10, -10),
    }),
    (11, {"grip": (-0.24, 0.22, 1.42), "aim": (-0.1, 0.35, 0.93), "root": 0.2}),
    (13, {
      "root": 0.45, "hips_pos": (-0.02, 0.04, -0.13), "hips_rot": (14, 10, -2), "spine_rot": (5, 8, 0),
      "chest_rot": (6, 8, 0), "head_rot": (10, 2, 0), "grip": (-0.03, 0.55, 1.05), "aim": (0.3, 0.9, 0.2),
      "foot_r": end_r, "foot_r_rot": (-4, -10), "foot_l": GUARD["foot_l"], "foot_l_rot": GUARD["foot_l_rot"],
    }),
    (15, {
      "root": 0.6, "hips_pos": (-0.03, 0.06, -0.19), "hips_rot": (22, 24, -3), "spine_rot": (7, 10, 0),
      "chest_rot": (8, 10, 0), "head_rot": (14, 8, 0), "grip": (0.14, 0.42, 0.78), "aim": (0.66, 0.55, -0.5),
      "foot_r": end_r, "foot_r_rot": GUARD["foot_r_rot"], "foot_l": GUARD["foot_l"], "foot_l_rot": (30, 24),
    }),
    (17, {"foot_l": GUARD["foot_l"], "foot_l_rot": (38, 24)}),
    (19, {
      "root": 0.66, "hips_pos": (-0.03, 0.06, -0.2), "hips_rot": (22, 25, -3), "chest_rot": (8, 10, 0),
      "grip": (0.16, 0.4, 0.76), "aim": (0.68, 0.5, -0.53), "foot_l": (0.18, 0.12, 0.09), "foot_l_rot": (30, 24),
    }),
    (21, {"left_on": 1.0, "slide": 0.0}),
    (23, {"foot_l": end_l, "foot_l_rot": GUARD["foot_l_rot"], "hips_rot": (12, 20, -1)}),
    (30, {
      "root": distance, "hips_pos": GUARD["hips_pos"], "hips_rot": GUARD["hips_rot"], "spine_rot": GUARD["spine_rot"],
      "chest_rot": GUARD["chest_rot"], "head_rot": GUARD["head_rot"], "grip": GUARD["grip"], "aim": GUARD["aim"],
      "slide": GUARD["slide"], "left_on": GUARD["left_on"], "pole_r": GUARD["pole_r"], "pole_l": GUARD["pole_l"],
      "foot_r": end_r, "foot_r_rot": GUARD["foot_r_rot"], "foot_l": end_l, "foot_l_rot": GUARD["foot_l_rot"],
    }),
  ))


CLIPS = [
  idle_clip(),
  run_clip("run-loop", RUN_SPEED, RUN_FRAMES, STANCE_SHARE, lean=11, drop=-0.075, swing=0.25),
  # SPRINT_SPEED in PlayerController must match this speed.
  run_clip("sprint-loop", 6.8, 15, 0.26, lean=19, drop=-0.1, swing=0.34),
  jump_clip(),
  fall_clip(),
  land_clip(),
  dodge_clip(),
  attack_clip(),
  air_attack_clip(),
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
