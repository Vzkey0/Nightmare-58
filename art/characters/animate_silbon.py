"""Generates El Silbón's animations and exports them with its model.

Run it after build_silbon.py, which writes a model without animations:

  blender --background art/characters/silbon.blend --python art/characters/animate_silbon.py

It shares the rig solver of animate_protagonist.py. The differences: the right hand is an open claw,
the left one carries the sack of bones, which swings like a flail and arrives late because it is
heavy, and the jaw has its own key.

Times for the attack tables of enemy_actions.cpp, in seconds at 30 fps. Every attack leaves at
least 0.4 s between the tell and the blow, as art_guide.md asks.

  clip                length  advance  blow          what hits
  attack_rake         1.53    0.8 m    0.67 to 0.77  right claw, diagonal from above
  attack_sack_slam    2.2     0.6 m    0.97 to 1.07   sack overhead onto the ground: Slam
  attack_sack_sweep   2.0     0.4 m    0.73 to 0.9   sack, wide at waist height, from his left
  attack_lunge        2.13    5.0 m    0.97 to 1.1   right claw, landing from a leap
  attack_bone_throw   2.0     0        lets go 0.97  ranged: a bone out of the sack
  attack_scream       2.33    0        0.8 to 1.47   phase 3: whistle that hits all around him
  attack_flurry       2.8     1.6 m    0.6, 0.97 and 1.6 to 1.7  phase 2: rake, backhand, sack
  whistle             3.0                            on seeing the player
  enrage              3.2                            phase change
  death               4.0                            holds its last frame
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(bpy.data.filepath)))

from animate_protagonist import AUTHOR_FPS, BAKE_FPS, DELAYS, UP, Clip, Rig, aim_delta, at, bake, rot, timeline, wave

GLB_PATH = os.path.join(os.path.dirname(bpy.data.filepath), "..", "..", "game", "models", "characters", "silbon.glb")

# Follow-through of the channels the protagonist does not have. The sack is the heaviest thing he moves.
DELAYS.update({"hand_r": 1.4, "sack": 1.0, "sack_aim": 2.0})

DOWN = Vector((0, 0, -1))
SIDE = Vector((1, 0, 0))
# From the fist to the wrist, toward the shoulder.
FIST = 0.2


class SilbonRig(Rig):
  def solve(self, pose):
    self.world.clear()
    self.local.clear()
    root = at(0, pose["root"], 0)
    self.place("root", Quaternion(), root)

    hips_at = root + self.head["hips"] + at(*pose["hips_pos"])
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

    self.arm("_r", root + at(*pose["hand_r"]), at(*pose["pole_r"]), chest)
    self.hand("_r", self.forearm("_r"), pose["claw"])

    grip = root + at(*pose["sack"])
    toward = (self.origin("shoulder_l") - grip).normalized()
    self.arm("_l", grip + toward * FIST, at(*pose["pole_l"]), chest)
    self.hand("_l", self.forearm("_l"), 80.0)
    hang = at(*pose["sack_aim"]).normalized()
    # ponytail: the sack twists fast when it points straight to a side; give it a keyed reference if a clip needs that.
    reference = SIDE - SIDE.project(hang)
    if reference.length < 0.05:
      reference = UP - UP.project(hang)
    self.place("sack", aim_delta(DOWN, SIDE, hang, reference), grip)

  def forearm(self, side):
    name = "lower_arm" + side
    return self.world[name].to_quaternion() @ self.rest[name].to_quaternion().inverted()


# Bent almost double under the sack, which hangs down his back from the left fist at the shoulder.
GUARD = {
  "root": 0.0,
  "hips_pos": (0.0, 0.0, -0.28),
  "hips_rot": (14, -6, 0),
  "spine_rot": (16, 4, 0),
  "chest_rot": (22, 5, 0),
  "head_rot": (8, 0, 0),
  "jaw": 4.0,
  "foot_l": (0.3, 0.3, 0.0),
  "foot_l_rot": (0, 14),
  "foot_r": (-0.3, -0.35, 0.0),
  "foot_r_rot": (0, -16),
  "hand_r": (-0.5, 0.75, 1.15),
  "pole_r": (-0.8, -0.5, -0.2),
  "claw": 30.0,
  "sack": (0.28, 0.42, 2.4),
  "sack_aim": (0.15, -0.7, -0.7),
  "pole_l": (0.9, 0.1, -0.4),
}
# At his full height, for the whistle and the phase changes.
TALL = {
  "hips_pos": (0.0, 0.0, -0.12), "hips_rot": (-4, 0, 0), "spine_rot": (-4, 0, 0), "chest_rot": (-8, 0, 0),
  "sack": (0.4, -0.05, 2.9), "sack_aim": (0.1, -0.35, -0.95),
}


def rest_at(distance):
  """The guard again, moved by the distance an attack covered."""
  x_l, forward_l, z_l = GUARD["foot_l"]
  x_r, forward_r, z_r = GUARD["foot_r"]
  return dict(GUARD, root=distance, foot_l=(x_l, forward_l + distance, z_l), foot_r=(x_r, forward_r + distance, z_r))


def looped(overrides):
  channels = {name: [(0, value)] for name, value in GUARD.items()}
  channels.update(overrides)
  return channels


def idle_clip():
  """He listens: slow sway, the head tilting to one side like a bird, the claw opening and closing."""
  return Clip("idle-loop", 150, looped({
    "hips_pos": lambda p: (0.03 * wave(p, 0.0), 0.0, -0.28 + 0.015 * wave(p, 0.1, 2)),
    "chest_rot": lambda p: (22 + 2.0 * wave(p, 0.1, 2), 5 + 3.0 * wave(p, 0.0), 0),
    "head_rot": lambda p: (8 + 3.0 * wave(p, 0.6, 2), 10.0 * wave(p, 0.3), 14.0 * max(wave(p, 0.55), 0.0) ** 3),
    "jaw": lambda p: 4.0 + 5.0 * max(wave(p, 0.8, 3), 0.0) ** 8,
    "hand_r": lambda p: (-0.5 + 0.03 * wave(p, 0.0), 0.75, 1.15 + 0.04 * wave(p, 0.2, 2)),
    "claw": lambda p: 30.0 + 25.0 * max(wave(p, 0.4, 2), 0.0) ** 2,
    "sack_aim": lambda p: (0.15 + 0.05 * wave(p, 0.15), -0.7, -0.7),
  }), loop=True)


def step_foot(side_x, home, offset, speed, frames, stance, lift):
  """Stance moves back at exactly the walking speed, which is what stops the feet from sliding."""
  half = speed * frames / AUTHOR_FPS * stance * 0.5

  def position(phase):
    phase = (phase + offset) % 1.0
    if phase < stance:
      return (side_x, home + half - 2.0 * half * phase / stance, 0.0)
    swing = (phase - stance) / (1.0 - stance)
    blend = swing * swing * (3.0 - 2.0 * swing)
    return (side_x, home - half + 2.0 * half * blend, lift * math.sin(math.pi * swing) ** 1.5)

  def pitch(phase):
    phase = (phase + offset) % 1.0
    if phase < 0.1:
      return (-10.0 * (1.0 - phase / 0.1), 0.0)
    if phase < stance:
      return (max(phase - (stance - 0.2), 0.0) * 170.0, 0.0)
    swing = (phase - stance) / (1.0 - stance)
    return (34.0 - 44.0 * swing, 0.0)

  return position, pitch


# The speeds in silbon_enemy.cpp must match these, or the feet slide.
WALK_SPEED = 1.8
WALK_FRAMES = 36
RUN_SPEED = 6.0
RUN_FRAMES = 20
CIRCLE_SPEED = 1.5
CIRCLE_FRAMES = 28
CIRCLE_STANCE = 0.55


def walk_clip():
  """Long, slow strides. The sack thumps against his back on every step."""
  foot_l, pitch_l = step_foot(0.24, 0.05, 0.0, WALK_SPEED, WALK_FRAMES, 0.62, 0.28)
  foot_r, pitch_r = step_foot(-0.24, -0.05, 0.5, WALK_SPEED, WALK_FRAMES, 0.62, 0.28)
  return Clip("walk-loop", WALK_FRAMES, looped({
    "foot_l": foot_l, "foot_l_rot": pitch_l, "foot_r": foot_r, "foot_r_rot": pitch_r,
    "hips_pos": lambda p: (0.06 * wave(p, 0.05), 0.0, -0.32 + 0.05 * wave(p, 0.1, 2)),
    "hips_rot": lambda p: (16.0, -6.0 + 9.0 * wave(p, 0.0), 4.0 * wave(p, 0.05)),
    "chest_rot": lambda p: (22.0 + 3.0 * wave(p, 0.2, 2), 5.0 - 8.0 * wave(p, 0.0), 0.0),
    "head_rot": lambda p: (8.0 + 3.0 * wave(p, 0.3, 2), 5.0 * wave(p, 0.5), -5.0 * wave(p, 0.1)),
    "hand_r": lambda p: (-0.5, 0.7 + 0.35 * wave(p, 0.0), 1.1 + 0.05 * wave(p, 0.2, 2)),
    "sack": lambda p: (0.28, 0.42, 2.36 + 0.04 * wave(p, 0.15, 2)),
    "sack_aim": lambda p: (0.15 + 0.08 * wave(p, 0.1), -0.7 + 0.06 * wave(p, 0.2, 2), -0.7),
  }), loop=True)


def run_clip():
  """The chase: almost on all fours, the claw reaching ahead and the sack bouncing behind."""
  foot_l, pitch_l = step_foot(0.2, 0.1, 0.0, RUN_SPEED, RUN_FRAMES, 0.38, 0.45)
  foot_r, pitch_r = step_foot(-0.2, 0.05, 0.5, RUN_SPEED, RUN_FRAMES, 0.38, 0.45)
  return Clip("run-loop", RUN_FRAMES, looped({
    "foot_l": foot_l, "foot_l_rot": pitch_l, "foot_r": foot_r, "foot_r_rot": pitch_r,
    "hips_pos": lambda p: (0.05 * wave(p, 0.05), 0.1, -0.42 + 0.08 * wave(p, 0.15, 2)),
    "hips_rot": lambda p: (26.0, 12.0 * wave(p, 0.0), 5.0 * wave(p, 0.05)),
    "spine_rot": [(0, (18, 0, 0))],
    "chest_rot": lambda p: (24.0 + 4.0 * wave(p, 0.25, 2), -12.0 * wave(p, 0.0), 0.0),
    "head_rot": lambda p: (-8.0 + 4.0 * wave(p, 0.35, 2), 5.0 * wave(p, 0.5), 0.0),
    "jaw": lambda p: 14.0 + 6.0 * wave(p, 0.2, 2),
    "hand_r": lambda p: (-0.5, 1.2 + 0.4 * wave(p, 0.0), 1.2 + 0.1 * wave(p, 0.2, 2)),
    "claw": [(0, 10.0)],
    "sack": lambda p: (0.3, 0.75, 2.05 + 0.06 * wave(p, 0.15, 2)),
    "sack_aim": lambda p: (0.15 + 0.1 * wave(p, 0.1), -0.85, -0.45 + 0.15 * wave(p, 0.3, 2)),
  }), loop=True)


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
      lift = 0.2 * math.sin(math.pi * swing)
    return (home[0] + move[0] * amount, home[1] + move[1] * amount, lift)

  return position


def circle_clip(name, move):
  """Stalking around the player: wide spider steps, the head never leaving him."""
  return Clip(name, CIRCLE_FRAMES, looped({
    "foot_l": circle_foot((0.34, 0.15), 0.0, move),
    "foot_r": circle_foot((-0.34, -0.15), 0.5, move),
    "foot_l_rot": [(0, (0, 10))],
    "foot_r_rot": [(0, (0, -10))],
    "hips_pos": lambda p: (0.05 * wave(p, 0.1), 0.0, -0.36 + 0.03 * wave(p, 0.1, 2)),
    "hips_rot": lambda p: (14.0, -6.0, 4.0 * wave(p, 0.1)),
    "head_rot": lambda p: (8.0 + 2.0 * wave(p, 0.3, 2), 0.0, 8.0 * wave(p, 0.1)),
    "hand_r": lambda p: (-0.55, 0.8, 1.1 + 0.04 * wave(p, 0.2, 2)),
    "claw": lambda p: 20.0 + 15.0 * wave(p, 0.0, 2),
    "sack_aim": lambda p: (0.15 + 0.08 * wave(p, 0.1), -0.7, -0.7),
  }), loop=True)


RAKE_UP = {
  "hips_pos": (0.0, -0.1, -0.12), "hips_rot": (0, -20, 0), "spine_rot": (4, -8, 0), "chest_rot": (0, -12, 0), "head_rot": (6, 6, 0),
  "hand_r": (-0.9, -0.2, 3.0), "pole_r": (-0.9, -0.3, 0.4), "claw": 0.0, "jaw": 16.0,
}
RAKE_DOWN = {
  "hips_pos": (0.0, 0.1, -0.5), "hips_rot": (30, 22, 0), "spine_rot": (14, 8, 0), "chest_rot": (18, 12, 0), "head_rot": (20, 10, 0),
  "hand_r": (0.3, 1.1, 0.9), "pole_r": (-0.8, -0.3, -0.5), "claw": 40.0, "jaw": 10.0,
}


def attack_rake_clip():
  """The basic blow: the claw goes up behind the hat, hangs there, and rakes down across his body."""
  bottom = dict(RAKE_DOWN, root=0.8, foot_l=(0.32, 1.25, 0.0), foot_l_rot=(0, 16), foot_r_rot=(24, -16))
  return Clip("attack_rake", 46, timeline(
    (0, dict(GUARD)),
    (6, {"hips_pos": (0.0, 0.03, -0.34), "hand_r": (-0.7, 0.4, 1.6)}),
    (14, dict(RAKE_UP)),
    (19, dict(RAKE_UP, hips_pos=(0.0, -0.12, -0.1), hand_r=(-0.92, -0.25, 3.02))),
    (21, {"root": 0.3, "hand_r": (-0.4, 1.2, 2.2), "foot_l": (0.31, 0.8, 0.18), "foot_l_rot": (-10, 16)}),
    (23, dict(bottom)),
    (32, dict(bottom, hips_pos=(0.0, 0.1, -0.52))),
    (38, {"foot_r": (-0.3, 0.3, 0.16), "foot_r_rot": (18, -16)}),
    (46, rest_at(0.8)),
  ))


def attack_sack_slam_clip():
  """He hauls the sack off his back, stands to his full height with it overhead, and brings it down."""
  raised = {
    "hips_pos": (0.0, -0.1, -0.04), "hips_rot": (-8, 6, 0), "spine_rot": (-6, 0, 0), "chest_rot": (-10, 0, 0), "head_rot": (-6, 0, 0),
    "sack": (0.3, -0.25, 3.5), "sack_aim": (0.0, -0.75, 0.65), "pole_l": (0.9, 0.3, 0.2),
    "hand_r": (-0.15, -0.15, 3.3), "pole_r": (-0.9, 0.3, 0.2), "claw": 70.0, "jaw": 22.0,
  }
  down = {
    "root": 0.6, "hips_pos": (0.0, 0.2, -0.75), "hips_rot": (38, 0, 0), "spine_rot": (18, 0, 0), "chest_rot": (20, 0, 0), "head_rot": (24, 0, 0),
    "sack": (0.15, 1.35, 0.75), "sack_aim": (0.0, 0.93, -0.36), "pole_l": (0.9, -0.2, -0.3),
    "hand_r": (-0.35, 1.25, 0.6), "pole_r": (-0.9, -0.2, -0.3), "claw": 20.0, "jaw": 30.0,
    "foot_l": (0.34, 1.0, 0.0), "foot_l_rot": (0, 14), "foot_r_rot": (20, -16),
  }
  return Clip("attack_sack_slam", 66, timeline(
    (0, dict(GUARD)),
    (8, {"hips_pos": (0.0, 0.05, -0.4), "sack": (0.4, 0.3, 2.3), "sack_aim": (0.2, -0.6, -0.75)}),
    (17, dict(raised)),
    (24, dict(raised, hips_pos=(0.0, -0.13, -0.02), sack=(0.3, -0.3, 3.52))),
    (26, {"root": 0.3, "sack": (0.25, 0.7, 3.0), "sack_aim": (0.0, 0.4, 0.9), "foot_l": (0.33, 0.7, 0.2), "foot_l_rot": (-10, 14)}),
    (28, dict(down)),
    (40, dict(down, hips_pos=(0.0, 0.2, -0.77))),
    (52, {"hips_pos": (0.0, 0.05, -0.4), "sack": (0.4, 0.7, 1.6), "sack_aim": (0.1, 0.2, -0.95), "foot_r": (-0.3, 0.1, 0.16), "foot_r_rot": (18, -16)}),
    (66, rest_at(0.6)),
  ))


def attack_sack_sweep_clip():
  """He lets the sack drop to his left, winds his whole body after it and swings it across at waist height."""
  wound = {
    "hips_pos": (0.08, -0.05, -0.4), "hips_rot": (10, 34, 0), "spine_rot": (10, 14, 0), "chest_rot": (14, 16, 0), "head_rot": (10, -8, 0),
    "sack": (1.0, -0.35, 1.5), "sack_aim": (0.55, -0.6, -0.55), "pole_l": (0.6, -0.8, 0.2),
    "hand_r": (-0.2, 0.9, 1.5), "pole_r": (-0.8, -0.3, -0.4), "claw": 10.0, "jaw": 14.0,
  }
  out = {
    "root": 0.4, "hips_pos": (-0.06, 0.08, -0.45), "hips_rot": (14, -34, 0), "spine_rot": (10, -14, 0), "chest_rot": (12, -18, 0), "head_rot": (12, 10, 0),
    "sack": (-0.75, 0.85, 1.45), "sack_aim": (-0.85, 0.35, -0.35), "pole_l": (0.3, 0.6, 0.7),
    "hand_r": (-1.0, -0.2, 1.5), "pole_r": (-0.6, -0.8, 0.1), "claw": 40.0, "jaw": 24.0,
    "foot_l": (0.36, 0.95, 0.0), "foot_l_rot": (0, 4),
  }
  return Clip("attack_sack_sweep", 60, timeline(
    (0, dict(GUARD)),
    (7, {"sack": (0.7, 0.2, 2.0), "sack_aim": (0.4, -0.3, -0.85)}),
    (15, dict(wound)),
    (21, dict(wound, hips_pos=(0.1, -0.07, -0.41), sack=(1.03, -0.4, 1.5))),
    (24, {"root": 0.2, "sack": (0.35, 1.2, 1.4), "sack_aim": (0.5, 0.8, -0.3), "hips_rot": (12, 0, 0), "spine_rot": (10, 0, 0), "chest_rot": (12, 0, 0),
          "pole_l": (0.8, -0.2, 0.4), "foot_l": (0.35, 0.65, 0.15)}),
    (27, dict(out)),
    (37, dict(out, sack=(-0.8, 0.75, 1.4), sack_aim=(-0.8, -0.1, -0.6))),
    (48, {"sack": (0.1, 0.9, 1.7), "sack_aim": (-0.2, 0.1, -0.95), "foot_r": (-0.3, 0.05, 0.16), "foot_r_rot": (18, -16)}),
    (60, rest_at(0.4)),
  ))


def attack_lunge_clip():
  """Closes the distance: folds down to the ground, leaps with the claw high and lands driving it in."""
  distance = 5.0
  coil = {
    "hips_pos": (0.0, -0.2, -0.8), "hips_rot": (34, -10, 0), "spine_rot": (16, -4, 0), "chest_rot": (14, -6, 0), "head_rot": (-12, 4, 0),
    "hand_r": (-0.6, 0.5, 0.25), "pole_r": (-0.9, -0.3, 0.3), "claw": 0.0, "jaw": 26.0,
    "sack": (0.4, 0.5, 1.8), "sack_aim": (0.2, -0.8, -0.55),
  }
  land = {
    "root": distance, "hips_pos": (0.0, 0.15, -0.8), "hips_rot": (42, 10, 0), "spine_rot": (14, 4, 0), "chest_rot": (14, 6, 0), "head_rot": (18, 6, 0),
    "hand_r": (-0.1, 1.35, 0.35), "pole_r": (-0.9, -0.2, 0.2), "claw": 45.0, "jaw": 20.0,
    "sack": (0.45, 0.8, 1.6), "sack_aim": (0.2, -0.75, -0.6),
    "foot_l": (0.32, distance + 0.9, 0.0), "foot_l_rot": (0, 14), "foot_r": (-0.3, distance - 0.6, 0.0), "foot_r_rot": (22, -16),
  }
  return Clip("attack_lunge", 64, timeline(
    (0, dict(GUARD)),
    (13, dict(coil)),
    (21, dict(coil, hips_pos=(0.0, -0.24, -0.84), hand_r=(-0.6, 0.45, 0.75))),
    (23, {
      "root": 1.0, "hips_pos": (0.0, 0.0, -0.4), "hips_rot": (16, -8, 0), "spine_rot": (4, 0, 0), "chest_rot": (0, -10, 0), "head_rot": (10, 0, 0),
      "hand_r": (-0.7, 0.0, 2.9), "pole_r": (-0.9, -0.3, 0.4),
      "foot_l": (0.3, 1.3, 0.3), "foot_l_rot": (-10, 14), "foot_r": (-0.3, 0.8, 0.12), "foot_r_rot": (50, -16),
    }),
    (26, {"root": 2.9, "hips_pos": (0.0, 0.0, 0.3), "hand_r": (-0.75, -0.1, 3.3),
          "foot_l": (0.3, 3.6, 0.7), "foot_l_rot": (-16, 14), "foot_r": (-0.3, 2.0, 0.75), "foot_r_rot": (30, -16),
          "sack_aim": (0.2, -0.95, -0.2)}),
    (29, {"root": 4.5, "hips_pos": (0.0, 0.05, -0.3), "hand_r": (-0.4, 1.1, 2.4),
          "foot_l": (0.32, 5.3, 0.08), "foot_l_rot": (-8, 14), "foot_r": (-0.3, 4.0, 0.4), "foot_r_rot": (30, -16)}),
    (31, dict(land)),
    (43, dict(land, hips_pos=(0.0, 0.15, -0.82))),
    (52, {"foot_r": (-0.3, distance - 0.2, 0.18), "foot_r_rot": (18, -16)}),
    (64, rest_at(distance)),
  ))


def attack_bone_throw_clip():
  """Ranged: the claw digs into the sack over his shoulder, comes out with a bone and hurls it.
  The bone leaves the hand at frame 29; the game spawns it at the hand_r bone."""
  dig = {
    "hips_rot": (10, 14, 0), "chest_rot": (16, 18, 0), "head_rot": (6, 20, 8),
    "hand_r": (0.25, 0.1, 2.3), "pole_r": (-0.9, 0.2, 0.5), "claw": 60.0, "sack": (0.3, 0.45, 2.3), "sack_aim": (0.0, -0.75, -0.65),
  }
  back = {
    "hips_pos": (0.0, -0.15, -0.15), "hips_rot": (-4, -24, 0), "spine_rot": (0, -10, 0), "chest_rot": (-6, -16, 0), "head_rot": (4, 4, 0),
    "hand_r": (-0.95, -0.55, 2.9), "pole_r": (-0.9, -0.4, -0.3), "claw": 70.0, "jaw": 18.0,
  }
  thrown = {
    "hips_pos": (0.0, 0.15, -0.45), "hips_rot": (28, 24, 0), "spine_rot": (12, 8, 0), "chest_rot": (16, 14, 0), "head_rot": (10, 4, 0),
    "hand_r": (0.1, 1.4, 1.5), "pole_r": (-0.8, -0.4, -0.4), "claw": 0.0, "jaw": 26.0,
  }
  return Clip("attack_bone_throw", 60, timeline(
    (0, dict(GUARD)),
    (9, dict(dig)),
    (14, dict(dig, hand_r=(0.3, -0.1, 2.15))),
    (22, dict(back)),
    (26, dict(back, hand_r=(-0.98, -0.6, 2.92))),
    (30, dict(thrown)),
    (40, dict(thrown, hips_pos=(0.0, 0.15, -0.47))),
    (60, dict(GUARD)),
  ))


SCREAM = dict(TALL, **{
  "hips_pos": (0.0, -0.05, -0.1), "chest_rot": (-16, 0, 0), "head_rot": (-30, 0, 0), "jaw": 46.0,
  "hand_r": (-1.2, 0.1, 1.9), "pole_r": (-0.6, -0.9, -0.2), "claw": -10.0,
  "sack": (1.15, 0.0, 1.9), "sack_aim": (0.25, -0.1, -0.95), "pole_l": (0.6, -0.9, -0.2),
})
INHALE = {
  "hips_pos": (0.0, 0.05, -0.55), "hips_rot": (26, 0, 0), "spine_rot": (20, 0, 0), "chest_rot": (26, 0, 0), "head_rot": (40, 0, 0), "jaw": 0.0,
  "hand_r": (-0.25, 0.7, 1.3), "claw": 70.0, "sack": (0.3, 0.6, 1.7), "sack_aim": (0.1, -0.2, -0.97),
}


def whistle_clip():
  """On seeing the player: he unfolds to his full height, tilts the head back and whistles the scale."""
  held = dict(TALL, head_rot=(-22, 0, 0), jaw=8.0, hand_r=(-0.6, 0.2, 1.5), claw=50.0)
  keys = [(0, dict(GUARD)), (22, dict(held))]
  keys += [(frame, dict(held, head_rot=(-22 + 2.5 * math.sin(frame * 1.3), 4.0 * math.sin(frame * 0.9), 0), jaw=8.0 + 3.0 * math.sin(frame * 2.3))) for frame in range(26, 66, 4)]
  keys += [(74, dict(held, head_rot=(-6, 0, 12))), (90, dict(GUARD))]
  return Clip("whistle", 90, timeline(*keys))


def attack_scream_clip():
  """Phase 3: folds in to fill his chest, then throws the arms wide and the whistle hits everything near."""
  keys = [(0, dict(GUARD)), (14, dict(INHALE)), (21, dict(INHALE, hips_pos=(0.0, 0.05, -0.58))), (24, dict(SCREAM))]
  keys += [(frame, dict(SCREAM, head_rot=(-30 + 3.0 * math.sin(frame * 2.1), 5.0 * math.sin(frame * 1.7), 0), hips_pos=(0.0, -0.05, -0.1 + 0.02 * math.sin(frame * 2.6)))) for frame in range(27, 45, 3)]
  keys += [(54, {"hips_pos": (0.0, 0.0, -0.3), "jaw": 12.0}), (70, dict(GUARD))]
  return Clip("attack_scream", 70, timeline(*keys))


def enrage_clip():
  """Phase change: he drops to a knee clawing the ground, then rises screaming and shakes the sack overhead."""
  kneel = {
    "hips_pos": (0.0, 0.1, -0.95), "hips_rot": (30, 0, 0), "spine_rot": (22, 0, 0), "chest_rot": (24, 0, 0), "head_rot": (50, 0, 0), "jaw": 6.0,
    "hand_r": (-0.45, 1.0, 0.1), "claw": 60.0, "sack": (0.5, 0.9, 0.5), "sack_aim": (0.3, 0.3, -0.9),
  }
  risen = dict(SCREAM, sack=(0.5, 0.0, 3.6), sack_aim=(0.0, -0.3, -0.95), pole_l=(0.9, 0.3, 0.2), hand_r=(-1.1, 0.3, 2.4))
  keys = [(0, dict(GUARD)), (16, dict(kneel)), (30, dict(kneel, hand_r=(-0.5, 0.6, 0.1), head_rot=(56, 0, 0))), (38, dict(risen))]
  keys += [(frame, dict(risen, sack=(0.5 + 0.12 * math.sin(frame * 1.9), 0.0, 3.6), sack_aim=(0.5 * math.sin(frame * 1.9), -0.3, -0.9),
                        head_rot=(-30 + 3.0 * math.sin(frame * 2.1), 6.0 * math.sin(frame * 1.7), 0))) for frame in range(41, 72, 3)]
  keys += [(82, {"hips_pos": (0.0, 0.0, -0.3), "jaw": 12.0, "sack": (0.4, 0.3, 2.8)}), (96, dict(GUARD))]
  return Clip("enrage", 96, timeline(*keys))


def attack_flurry_clip():
  """Phase 2: the rake, a backhand on the way back and, while the player is still dodging, the sack."""
  first = dict(RAKE_DOWN, root=0.6, foot_l=(0.32, 1.05, 0.0), foot_l_rot=(0, 16))
  backhand = {
    "root": 1.1, "hips_pos": (0.0, 0.05, -0.4), "hips_rot": (16, -30, 0), "spine_rot": (8, -12, 0), "chest_rot": (8, -16, 0), "head_rot": (10, 10, 0),
    "hand_r": (-0.95, 0.7, 1.6), "pole_r": (-0.4, -0.9, 0.0), "claw": 0.0, "jaw": 22.0,
    "foot_r": (-0.32, 0.9, 0.0), "foot_r_rot": (0, -16),
    "sack": (0.5, 0.0, 3.3), "sack_aim": (0.1, -0.7, 0.7), "pole_l": (0.9, 0.3, 0.2),
  }
  slam = {
    "root": 1.6, "hips_pos": (0.0, 0.2, -0.75), "hips_rot": (38, 0, 0), "spine_rot": (18, 0, 0), "chest_rot": (20, 0, 0), "head_rot": (24, 0, 0),
    "sack": (0.15, 1.35, 0.75), "sack_aim": (0.0, 0.93, -0.36), "pole_l": (0.9, -0.2, -0.3),
    "hand_r": (-0.6, 0.6, 0.9), "claw": 30.0, "jaw": 30.0, "foot_l": (0.34, 2.0, 0.0), "foot_l_rot": (0, 14),
  }
  return Clip("attack_flurry", 84, timeline(
    (0, dict(GUARD)),
    (12, dict(RAKE_UP)),
    (16, dict(RAKE_UP, hand_r=(-0.92, -0.25, 3.02))),
    (19, dict(first)),
    (24, dict(first, hand_r=(0.5, 0.9, 1.0), claw=20.0)),
    (29, dict(backhand)),
    (40, dict(backhand, hips_pos=(0.0, -0.05, -0.15), hips_rot=(-2, -12, 0), spine_rot=(-4, -6, 0), chest_rot=(-6, -8, 0), sack=(0.4, -0.3, 3.3), sack_aim=(0.0, -0.75, 0.65), hand_r=(-1.0, 0.2, 1.8))),
    (46, dict(backhand, hips_pos=(0.0, -0.05, -0.15), hips_rot=(-2, -12, 0), spine_rot=(-4, -6, 0), chest_rot=(-6, -8, 0), sack=(0.4, -0.35, 3.32), sack_aim=(0.0, -0.75, 0.65), hand_r=(-1.0, 0.2, 1.8))),
    (48, {"hips_pos": (0.0, 0.05, -0.3), "hips_rot": (10, 0, 0), "sack": (0.25, 0.7, 2.9), "sack_aim": (0.0, 0.4, 0.9), "foot_l": (0.33, 1.6, 0.2), "foot_l_rot": (-10, 14)}),
    (50, dict(slam)),
    (62, dict(slam, hips_pos=(0.0, 0.2, -0.77))),
    (72, {"sack": (0.4, 0.7, 1.6), "sack_aim": (0.1, 0.2, -0.95), "foot_r": (-0.3, 1.3, 0.16), "foot_r_rot": (18, -16)}),
    (84, rest_at(1.6)),
  ))


def death_clip():
  """The whistle breaks. He drops the sack, goes down on his knees reaching for it and falls on his face."""
  struck = dict(TALL, hips_pos=(0.0, -0.15, -0.1), head_rot=(-34, 10, 0), jaw=40.0, hand_r=(-0.9, -0.2, 2.2), claw=0.0,
                sack=(0.9, 0.1, 2.0), sack_aim=(0.2, -0.2, -0.95))
  knees = {
    "hips_pos": (0.0, 0.35, -1.05), "hips_rot": (6, 0, 0), "spine_rot": (14, 0, 0), "chest_rot": (20, 0, 0), "head_rot": (30, 14, 0), "jaw": 16.0,
    "foot_l": (0.3, -0.5, 0.0), "foot_l_rot": (70, 14), "foot_r": (-0.3, -0.6, 0.0), "foot_r_rot": (70, -16),
    "hand_r": (-0.5, 1.2, 0.8), "claw": 20.0, "sack": (1.0, 0.7, 0.36), "sack_aim": (0.6, 0.4, -0.25), "pole_l": (0.9, -0.2, 0.3),
  }
  prone = dict(knees, **{
    "hips_pos": (0.0, 0.95, -1.46), "hips_rot": (82, 0, 4), "spine_rot": (4, 0, 0), "chest_rot": (2, 8, 0), "head_rot": (70, 34, 0), "jaw": 22.0,
    "hand_r": (-0.6, 2.3, 0.08), "pole_r": (-0.9, 0.0, 0.4), "claw": 35.0, "sack": (0.95, 1.6, 0.34), "sack_aim": (0.7, 0.6, -0.1),
  })
  return Clip("death", 120, timeline(
    (0, dict(GUARD)),
    (6, dict(struck)),
    (22, dict(struck, hips_pos=(0.05, -0.2, -0.14), head_rot=(-28, -8, 6))),
    (30, {"sack": (1.0, 0.3, 1.2), "sack_aim": (0.3, 0.0, -0.95), "foot_l": (0.3, 0.3, 0.0), "foot_l_rot": (0, 14), "foot_r": (-0.3, -0.35, 0.0), "foot_r_rot": (0, -16)}),
    (46, dict(knees)),
    (66, dict(knees, hips_pos=(0.0, 0.4, -1.08), hand_r=(-0.3, 1.5, 0.9), head_rot=(36, 20, 0))),
    (84, dict(prone)),
    (88, dict(prone, hips_pos=(0.0, 0.95, -1.43))),
    (94, dict(prone)),
    (120, dict(prone, claw=70.0, jaw=10.0)),
  ))


CLIPS = [
  idle_clip(),
  walk_clip(),
  run_clip(),
  circle_clip("strafe_left-loop", (1.0, 0.0)),
  circle_clip("strafe_right-loop", (-1.0, 0.0)),
  circle_clip("walk_back-loop", (0.0, -1.0)),
  whistle_clip(),
  attack_rake_clip(),
  attack_sack_slam_clip(),
  attack_sack_sweep_clip(),
  attack_lunge_clip(),
  attack_bone_throw_clip(),
  enrage_clip(),
  attack_flurry_clip(),
  attack_scream_clip(),
  death_clip(),
]


def export(armature):
  armature.animation_data.action = None
  for bone in armature.pose.bones:
    bone.matrix_basis = Matrix.Identity(4)
  os.makedirs(os.path.dirname(GLB_PATH), exist_ok=True)
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
  armature = bpy.data.objects["armature_silbon"]
  armature.animation_data_create()
  for bone in armature.pose.bones:
    bone.rotation_mode = "QUATERNION"
  rig = SilbonRig(armature)
  for clip in CLIPS:
    bake(armature, rig, clip, moved=("root", "hips", "sack"))
  export(armature)
  bpy.ops.wm.save_mainfile()


main()
