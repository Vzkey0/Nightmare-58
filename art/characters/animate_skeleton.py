"""Generates the skeleton enemy's animations and exports them with its model.

Run it after build_skeleton.py, which writes a model without animations:

  blender --background art/characters/skeleton.blend --python art/characters/animate_skeleton.py

It shares the rig solver of animate_protagonist.py. The differences: the machete is one-handed and
its hand is modeled shut around the grip, so the blade decides the hand; the jaw has its own key;
and in death the bones stop following each other and fall one by one.

Attacks put at least 12 frames (0.4 s) between the tell and the blow, as art_guide.md asks.
"""

import math
import os
import random
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(bpy.data.filepath)))

from animate_protagonist import AUTHOR_FPS, BAKE_FPS, FORWARD, UP, Clip, Rig, aim_delta, at, bake, rot, timeline, wave

GLB_PATH = os.path.join(os.path.dirname(bpy.data.filepath), "..", "..", "game", "models", "characters", "skeleton.glb")

# Where the wrist sits seen from the grip, in the rest pose. It must follow build_skeleton.py.
WRIST_FROM_GRIP = Vector((0.065, 0.0, 0.085))
SHOULDER_HEIGHT = 0.435
SHOULDER_WIDTH = 0.225

GRAVITY = 9.8
FALL_START = 7
FALL_FRAMES = 66


class SkeletonRig(Rig):
  def __init__(self, armature, body):
    super().__init__(armature)
    self.fall_plan = fall_plan(self, body)

  def solve(self, pose):
    self.world.clear()
    self.local.clear()
    self.place("root", Quaternion(), at(0, pose["root"], 0))
    root = at(0, pose["root"], 0)

    x, forward, z = pose["hips_pos"]
    hips_at = root + self.head["hips"] + at(x, forward, z)
    hips = rot(*pose["hips_rot"])
    spine = hips @ rot(*pose["spine_rot"])
    chest = spine @ rot(*pose["chest_rot"])
    head = rot(*pose["head_rot"])
    self.place("hips", hips, hips_at)
    self.place("spine", spine)
    self.place("chest", chest)
    self.place("neck", chest.slerp(head, 0.5))
    self.place("head", head)
    self.place("jaw", head @ rot(pose["jaw"]))

    for side, ball, foot_rot in (("_l", pose["foot_l"], pose["foot_l_rot"]), ("_r", pose["foot_r"], pose["foot_r_rot"])):
      self.leg(side, at(*ball), *foot_rot, Quaternion())

    self.machete_arm(pose, root, hips_at, chest)
    self.arm("_l", root + at(*pose["hand_l"]), at(*pose["pole_l"]), chest)
    lower = self.world["lower_arm_l"].to_quaternion() @ self.rest["lower_arm_l"].to_quaternion().inverted()
    self.hand("_l", lower, pose["claw"])

    if "fall" in pose:
      self.fall(pose["fall"])

  def machete_arm(self, pose, root, hips_at, chest):
    grip = root + at(*pose["grip"])
    blade = at(*pose["aim"]).normalized()
    shoulder = hips_at + chest @ Vector((-SHOULDER_WIDTH, 0, SHOULDER_HEIGHT))
    toward = shoulder - grip
    delta = aim_delta(FORWARD, WRIST_FROM_GRIP, blade, toward - toward.project(blade))
    delta = Quaternion(blade, math.radians(pose["edge"])) @ delta
    self.arm("_r", grip + delta @ WRIST_FROM_GRIP, at(*pose["pole_r"]), chest)
    self.place("hand_r", delta)
    self.place("fingers_r", delta)
    self.place("thumb_r", delta)
    self.place("weapon", delta)

  def fall(self, frame):
    """From FALL_START on, each bone drops on its own to its spot on the ground."""
    seconds = (frame - FALL_START) / AUTHOR_FPS
    if seconds <= 0.0:
      return
    # Parents first: every bone is placed against where its parent has already gone.
    for name in list(self.world):
      start = self.world[name]
      begin = start.translation.copy()
      held = start.to_quaternion() @ self.rest[name].to_quaternion().inverted()
      if name not in self.fall_plan or not self.parent[name]:
        if self.parent[name]:
          self.place(name, held, begin)
        continue
      delay, spot, turn, height = self.fall_plan[name]
      now = seconds - delay
      if now <= 0.0:
        self.place(name, held, begin)
        continue
      flight = math.sqrt(2.0 * max(begin.z - height, 0.02) / GRAVITY)
      progress = min(now / flight, 1.0)
      place = begin.lerp(spot, progress)
      place.z = begin.z + (height - begin.z) * progress * progress
      after = now - flight
      if 0.0 < after < 0.26:
        place.z += 0.07 * math.sin(math.pi * after / 0.26)
      self.place(name, held.slerp(turn, min(progress * 1.1, 1.0)), place)


def fall_plan(rig, body):
  """Spot and lying orientation of each bone, resting exactly on the ground."""
  rng = random.Random(58)
  points = {}
  for group in body.vertex_groups:
    points[group.name] = []
  names = {group.index: group.name for group in body.vertex_groups}
  for vertex in body.data.vertices:
    points[names[vertex.groups[0].group]].append(vertex.co.copy())

  plan = {}
  for name, verts in points.items():
    if not verts:
      continue
    head = rig.head[name]
    middle = sum(verts, Vector()) / len(verts)
    angle = rng.uniform(0.0, 2.0 * math.pi)
    lying = rig.direction(name).rotation_difference(Vector((math.cos(angle), math.sin(angle), 0.0)))
    turn = Quaternion(lying.axis, lying.angle)
    height = -min((turn @ (vertex - head)).z for vertex in verts)
    # Near where each bone stood, pulled together into a heap, and the skull rolls off further.
    spread = 1.1 if name in ("head", "jaw") else 0.5
    spot = Vector((middle.x * 0.55 + rng.uniform(-0.1, 0.1), rng.uniform(-0.18, 0.2) - spread * 0.25, height))
    plan[name] = (rng.uniform(0.0, 0.1), spot, turn, height)
  return plan


GUARD = {
  "root": 0.0,
  "hips_pos": (0.0, 0.0, -0.16),
  "hips_rot": (12, -8, 0),
  "spine_rot": (14, 5, 0),
  "chest_rot": (20, 7, 0),
  "head_rot": (12, -3, 0),
  "jaw": 8.0,
  "foot_l": (0.2, 0.2, 0.0),
  "foot_l_rot": (0, 14),
  "foot_r": (-0.2, -0.24, 0.0),
  "foot_r_rot": (0, -16),
  "grip": (-0.44, 0.36, 0.76),
  "aim": (-0.42, 0.8, 0.42),
  "edge": 0.0,
  "pole_r": (-0.75, -0.45, -0.3),
  "hand_l": (0.42, 0.2, 0.7),
  "pole_l": (0.75, -0.45, -0.3),
  "claw": 25.0,
}


def rest_at(distance):
  """The guard again, moved by the distance an attack covered."""
  x_l, forward_l, z_l = GUARD["foot_l"]
  x_r, forward_r, z_r = GUARD["foot_r"]
  return dict(GUARD, root=distance, foot_l=(x_l, forward_l + distance, z_l), foot_r=(x_r, forward_r + distance, z_r))


def idle_clip():
  def add(base, offsets):
    return lambda phase: tuple(b + o(phase) for b, o in zip(base, offsets))

  # No lungs to breathe with: slow sway, and a jaw that clicks now and then.
  sway = lambda phase: wave(phase, 0.0, 1)
  twitch = lambda phase: wave(phase, 0.2, 3)
  still = lambda phase: 0.0
  channels = {name: [(0, value)] for name, value in GUARD.items()}
  channels.update({
    "hips_pos": add(GUARD["hips_pos"], (lambda p: 0.014 * sway(p), still, lambda p: 0.008 * twitch(p))),
    "chest_rot": add(GUARD["chest_rot"], (lambda p: 1.8 * twitch(p), lambda p: 2.0 * sway(p), still)),
    "head_rot": add(GUARD["head_rot"], (lambda p: 2.2 * wave(p, 0.6, 2), lambda p: 5.0 * wave(p, 0.3, 1), lambda p: 3.0 * sway(p))),
    "jaw": lambda phase: 8.0 + 7.0 * max(wave(phase, 0.45, 5), 0.0) ** 12,
    "grip": add(GUARD["grip"], (still, lambda p: 0.012 * sway(p), lambda p: 0.012 * twitch(p))),
    "hand_l": add(GUARD["hand_l"], (lambda p: 0.012 * sway(p), still, lambda p: 0.014 * wave(p, 0.5, 3))),
    "claw": lambda phase: 25.0 + 8.0 * wave(phase, 0.1, 2),
  })
  return Clip("idle-loop", 120, channels, loop=True)


WALK_SPEED = 1.4
WALK_FRAMES = 30
WALK_STANCE = 0.62


def walk_foot(side_x, home, offset):
  half = WALK_SPEED * WALK_FRAMES / AUTHOR_FPS * WALK_STANCE * 0.5

  def position(phase):
    phase = (phase + offset) % 1.0
    if phase < WALK_STANCE:
      return (side_x, home + half - 2.0 * half * phase / WALK_STANCE, 0.0)
    swing = (phase - WALK_STANCE) / (1.0 - WALK_STANCE)
    blend = swing * swing * (3.0 - 2.0 * swing)
    return (side_x, home - half + 2.0 * half * blend, 0.15 * math.sin(math.pi * swing) ** 1.5)

  def pitch(phase):
    phase = (phase + offset) % 1.0
    if phase < 0.1:
      return (-10.0 * (1.0 - phase / 0.1), 0.0)
    if phase < WALK_STANCE:
      return (max(phase - 0.42, 0.0) * 170.0, 0.0)
    swing = (phase - WALK_STANCE) / (1.0 - WALK_STANCE)
    return (34.0 - 44.0 * swing, 0.0)

  return position, pitch


def walk_clip():
  """A lurch: the right leg drags, the machete hangs, and the skull rocks against the hips."""
  foot_l, pitch_l = walk_foot(0.17, 0.02, 0.0)
  foot_r, pitch_r = walk_foot(-0.17, -0.02, 0.5)
  channels = {name: [(0, value)] for name, value in GUARD.items()}
  channels.update({
    "foot_l": foot_l, "foot_l_rot": pitch_l, "foot_r": foot_r, "foot_r_rot": pitch_r,
    "hips_pos": lambda p: (0.035 * wave(p, 0.05), 0.0, -0.13 + 0.03 * wave(p, 0.1, 2)),
    "hips_rot": lambda p: (14.0, -8.0 + 10.0 * wave(p, 0.0), 5.0 * wave(p, 0.05)),
    "chest_rot": lambda p: (20.0 + 3.0 * wave(p, 0.2, 2), 7.0 - 9.0 * wave(p, 0.0), 0.0),
    "head_rot": lambda p: (12.0 + 3.0 * wave(p, 0.3, 2), -3.0 + 6.0 * wave(p, 0.5), -6.0 * wave(p, 0.1)),
    "jaw": lambda p: 11.0 + 4.0 * wave(p, 0.15, 2),
    "grip": lambda p: (-0.44, 0.34 + 0.13 * wave(p, 0.5), 0.76 + 0.03 * wave(p, 0.2, 2)),
    "hand_l": lambda p: (0.4, 0.2 + 0.2 * wave(p, 0.0), 0.72 + 0.03 * wave(p, 0.2, 2)),
  })
  return Clip("walk-loop", WALK_FRAMES, channels, loop=True)


# SkeletonEnemy::CIRCLE_SPEED must match this speed.
CIRCLE_SPEED = 1.1
CIRCLE_FRAMES = 24
CIRCLE_STANCE = 0.55


def circle_foot(home, offset, move):
  half = CIRCLE_SPEED * CIRCLE_FRAMES / AUTHOR_FPS * CIRCLE_STANCE * 0.5

  def position(phase):
    phase = (phase + offset) % 1.0
    if phase < CIRCLE_STANCE:
      amount = half - 2.0 * half * phase / CIRCLE_STANCE
      lift = 0.0
    else:
      swing = (phase - CIRCLE_STANCE) / (1.0 - CIRCLE_STANCE)
      amount = -half + 2.0 * half * swing * swing * (3.0 - 2.0 * swing)
      lift = 0.1 * math.sin(math.pi * swing)
    return (home[0] + move[0] * amount, home[1] + move[1] * amount, lift)

  return position


def circle_clip(name, move):
  """Waiting for a turn: short steps with the skull fixed on the player and the machete ready."""
  channels = {name: [(0, value)] for name, value in GUARD.items()}
  channels.update({
    "foot_l": circle_foot((0.2, 0.12), 0.0, move),
    "foot_r": circle_foot((-0.2, -0.12), 0.5, move),
    "foot_l_rot": [(0, (0, 10))],
    "foot_r_rot": [(0, (0, -10))],
    "hips_pos": lambda p: (0.03 * wave(p, 0.1), 0.0, -0.17 + 0.02 * wave(p, 0.1, 2)),
    "hips_rot": lambda p: (12.0, -8.0, 4.0 * wave(p, 0.1)),
    "head_rot": lambda p: (12.0 + 2.0 * wave(p, 0.3, 2), -3.0, -3.0 * wave(p, 0.1)),
    "grip": lambda p: (-0.44, 0.36, 0.76 + 0.02 * wave(p, 0.2, 2)),
    "hand_l": lambda p: (0.42, 0.2, 0.7 + 0.02 * wave(p, 0.2, 2)),
  })
  return Clip(name, CIRCLE_FRAMES, channels, loop=True)


def attack_chop_clip():
  """The basic blow: hauls the machete behind the skull, jaw open, and chops down across its body."""
  raised = {
    "hips_pos": (0.0, -0.07, -0.1), "hips_rot": (0, -26, 0), "spine_rot": (4, -10, 0), "chest_rot": (6, -12, 0), "head_rot": (8, 8, 0),
    "grip": (-0.4, -0.08, 1.46), "aim": (-0.3, -0.5, 0.8), "pole_r": (-0.9, 0.0, 0.25), "jaw": 24.0,
    "hand_l": (0.34, 0.42, 1.0), "pole_l": (0.8, -0.2, -0.5), "claw": 8.0,
  }
  bottom = {
    "root": 0.42, "hips_pos": (0.0, 0.08, -0.3), "hips_rot": (32, 22, 0), "spine_rot": (10, 8, 0), "chest_rot": (14, 10, 0), "head_rot": (24, 12, 0),
    "grip": (-0.12, 0.62, 0.72), "aim": (0.42, 0.85, -0.26), "pole_r": (-0.7, -0.1, -0.6), "jaw": 16.0, "hand_l": (0.46, 0.2, 0.86), "claw": 30.0,
    "foot_l": (0.22, 0.72, 0.0), "foot_l_rot": (0, 18), "foot_r": (-0.2, -0.24, 0.0), "foot_r_rot": (24, -16),
  }
  return Clip("attack_chop", 44, timeline(
    (0, dict(GUARD)),
    (5, {"hips_pos": (0.0, 0.02, -0.2), "grip": (-0.48, 0.18, 0.95), "aim": (-0.5, 0.5, 0.72)}),
    (13, dict(raised)),
    (18, dict(raised, hips_pos=(0.0, -0.08, -0.11), grip=(-0.41, -0.11, 1.48))),
    (20, {"root": 0.14, "grip": (-0.3, 0.42, 1.42), "aim": (-0.15, 0.82, 0.55), "foot_l": (0.21, 0.42, 0.1), "foot_l_rot": (-10, 16)}),
    (22, dict(bottom)),
    (31, dict(bottom, hips_pos=(0.0, 0.08, -0.31))),
    (36, {"foot_r": (-0.2, 0.02, 0.1), "foot_r_rot": (18, -16)}),
    (44, rest_at(0.42)),
  ))


def attack_sweep_clip():
  """A backhand: it winds the blade across its chest, then sweeps out wide at waist height."""
  wound = {
    "hips_pos": (0.0, 0.0, -0.17), "hips_rot": (10, 34, 0), "spine_rot": (10, 14, 0), "chest_rot": (14, 14, 0), "head_rot": (10, -6, 0),
    "grip": (0.3, 0.26, 1.02), "aim": (0.9, -0.2, 0.3), "pole_r": (-0.7, -0.1, 0.6), "edge": 40.0, "jaw": 18.0,
    "hand_l": (0.5, -0.18, 0.86), "pole_l": (0.8, -0.5, -0.2), "claw": 10.0,
  }
  out = {
    "root": 0.34, "hips_pos": (0.0, 0.04, -0.2), "hips_rot": (14, -32, 0), "spine_rot": (10, -14, 0), "chest_rot": (12, -14, 0), "head_rot": (12, 12, 0),
    "grip": (-0.62, 0.62, 0.98), "aim": (-0.96, 0.15, -0.1), "pole_r": (-0.2, -0.8, 0.1), "edge": 40.0, "jaw": 12.0,
    "hand_l": (0.5, 0.42, 0.9), "pole_l": (0.8, -0.2, -0.4), "claw": 30.0,
    "foot_l": (0.24, 0.56, 0.0), "foot_l_rot": (0, 8),
  }
  return Clip("attack_sweep", 40, timeline(
    (0, dict(GUARD)),
    (11, dict(wound)),
    (15, dict(wound, grip=(0.32, 0.24, 1.03))),
    (17, {"root": 0.14, "grip": (0.05, 0.8, 1.02), "aim": (0.35, 0.9, 0.0), "hips_rot": (12, 0, 0), "chest_rot": (12, 0, 0), "spine_rot": (10, 0, 0), "pole_r": (-0.6, -0.5, 0.5)}),
    (19, dict(out)),
    (27, dict(out, grip=(-0.64, 0.56, 0.96))),
    (33, {"foot_r": (-0.2, 0.0, 0.1), "foot_r_rot": (18, -16)}),
    (40, rest_at(0.34)),
  ))


def attack_lunge_clip():
  """The rush that closes distance: coils low, leaps with the machete overhead and lands chopping."""
  distance = 2.4
  coil = {
    "hips_pos": (0.0, -0.16, -0.36), "hips_rot": (28, -14, 0), "spine_rot": (14, -6, 0), "chest_rot": (16, -6, 0), "head_rot": (-4, 4, 0),
    "grip": (-0.5, -0.3, 0.72), "aim": (-0.3, -0.7, 0.62), "pole_r": (-0.8, 0.5, 0.3), "jaw": 30.0,
    "hand_l": (0.34, 0.62, 0.3), "pole_l": (0.8, -0.2, 0.1), "claw": 6.0,
  }
  land = {
    "root": distance, "hips_pos": (0.0, 0.1, -0.38), "hips_rot": (40, 10, 0), "spine_rot": (12, 4, 0), "chest_rot": (14, 4, 0), "head_rot": (20, 6, 0),
    "grip": (-0.1, 0.72, 0.52), "aim": (0.1, 0.85, -0.5), "pole_r": (-0.8, -0.1, 0.4), "jaw": 22.0,
    "hand_l": (0.46, 0.2, 0.62), "pole_l": (0.8, -0.4, -0.2), "claw": 30.0,
    "foot_l": (0.22, distance + 0.5, 0.0), "foot_l_rot": (0, 14), "foot_r": (-0.2, distance - 0.3, 0.0), "foot_r_rot": (20, -16),
  }
  return Clip("attack_lunge", 56, timeline(
    (0, dict(GUARD)),
    (12, dict(coil)),
    (20, dict(coil, hips_pos=(0.0, -0.18, -0.38))),
    (22, {
      "root": 0.5, "hips_pos": (0.0, 0.0, -0.02), "hips_rot": (10, -8, 0), "spine_rot": (0, 0, 0), "chest_rot": (0, 0, 0), "head_rot": (14, 0, 0),
      "grip": (-0.3, 0.25, 1.5), "aim": (-0.15, -0.3, 0.92), "pole_r": (-0.9, 0.0, 0.3),
      "foot_l": (0.2, 0.6, 0.12), "foot_l_rot": (-10, 14), "foot_r": (-0.2, 0.2, 0.0), "foot_r_rot": (50, -16),
    }),
    (25, {"root": 1.45, "hips_pos": (0.0, 0.0, 0.2), "foot_l": (0.2, 1.8, 0.36), "foot_l_rot": (-16, 14), "foot_r": (-0.2, 1.05, 0.34), "foot_r_rot": (30, -16),
          "grip": (-0.3, 0.4, 1.72), "aim": (-0.1, -0.1, 1.0)}),
    (28, {"root": 2.2, "hips_pos": (0.0, 0.04, -0.12), "foot_l": (0.22, 2.75, 0.04), "foot_l_rot": (-8, 14), "foot_r": (-0.2, 1.9, 0.2), "foot_r_rot": (30, -16),
          "grip": (-0.2, 0.85, 1.36), "aim": (0.0, 0.9, 0.45)}),
    (30, dict(land)),
    (40, dict(land, hips_pos=(0.0, 0.1, -0.39))),
    (47, {"foot_r": (-0.2, distance - 0.02, 0.1), "foot_r_rot": (18, -16)}),
    (56, rest_at(distance)),
  ))


HIT_POSE = {
  "hips_pos": (0.02, -0.08, -0.2), "hips_rot": (2, 16, 4), "spine_rot": (4, 8, 0), "chest_rot": (6, 12, 0), "head_rot": (-14, 16, 8),
  "jaw": 26.0, "grip": (-0.56, 0.2, 0.84), "aim": (-0.7, 0.6, 0.3), "hand_l": (0.5, 0.0, 0.9), "claw": 5.0,
}


def hurt_clip():
  """The skull snaps back first and the jaw hangs, then it hunches again."""
  return Clip("hurt", 15, timeline(
    (0, dict(GUARD)),
    (3, dict(HIT_POSE)),
    (6, dict(HIT_POSE, hips_pos=(0.02, -0.09, -0.22))),
    (15, dict(GUARD)),
  ))


class DeathClip(Clip):
  def sample(self, frame):
    pose = super().sample(frame)
    pose["fall"] = frame
    return pose


def death_clip():
  """It takes the last blow standing, then every bone lets go at once. Holds its last frame."""
  return DeathClip("death", FALL_FRAMES, timeline(
    (0, dict(GUARD)),
    (4, dict(HIT_POSE)),
    (FALL_FRAMES, dict(HIT_POSE)),
  ))


CLIPS = [
  idle_clip(),
  walk_clip(),
  circle_clip("strafe_left-loop", (1.0, 0.0)),
  circle_clip("strafe_right-loop", (-1.0, 0.0)),
  circle_clip("walk_back-loop", (0.0, -1.0)),
  attack_chop_clip(),
  attack_sweep_clip(),
  attack_lunge_clip(),
  hurt_clip(),
]


def export(armature, body):
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


def main():
  bpy.context.scene.render.fps = BAKE_FPS
  armature = bpy.data.objects["armature_skeleton"]
  body = bpy.data.objects["skeleton"]
  armature.animation_data_create()
  for bone in armature.pose.bones:
    bone.rotation_mode = "QUATERNION"
  rig = SkeletonRig(armature, body)
  for clip in CLIPS:
    bake(armature, rig, clip)
  bake(armature, rig, death_clip(), moved=tuple(bone.name for bone in armature.pose.bones))
  export(armature, body)
  bpy.ops.wm.save_mainfile()


main()
