"""Generates the feral dog's animations and exports them with its model.

Run it after build_dog.py, which writes the rigged model without animations:

  blender --background art/characters/dog.blend --python art/characters/animate_dog.py

The dog is the hunter of the pack: it stalks with the head low and commits to its attacks.
Attacks put at least 12 frames (0.4 s) between the tell and the blow, as art_guide.md asks.
"""

import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(bpy.data.filepath)))

from beast_anim import LEGS, BeastClip, gait, planted, run, stride, timeline, wave

GLB_PATH = os.path.join(os.path.dirname(bpy.data.filepath), "..", "..", "game", "models", "characters", "dog.glb")

# Lower than the model stands: front legs bent, head below the withers, lips back.
REST = {
  "root": 0.0,
  "hips_pos": (0.0, 0.0, -0.05),
  "hips_rot": (0, 0, 0),
  "spine_rot": (3, 0, 0),
  "chest_rot": (2, 0, 0),
  "head_rot": (8, 0, 0),
  "jaw": 10.0,
  "tail": (2.0, 0.0),
}
REST.update(planted(0.0))
REST.update({f"paw_{leg}_rot": 0.0 for leg in LEGS})


def channels(**changes):
  result = {name: [(0, value)] for name, value in REST.items()}
  result.update(changes)
  return result


def rest_at(distance):
  return dict(REST, root=distance, **planted(distance))


def idle_clip():
  # Growling: quick shallow pants, a low shiver through the body and the head swaying on its target.
  return BeastClip("idle-loop", 90, channels(
    hips_pos=lambda p: (0.004 * wave(p, 0.0, 15), 0.006 * wave(p, 0.0), -0.05 + 0.005 * wave(p, 0.1, 9)),
    chest_rot=lambda p: (2.0 + 1.2 * wave(p, 0.1, 9), 2.0 * wave(p, 0.3), 0.0),
    head_rot=lambda p: (8.0 + 2.0 * wave(p, 0.5, 2), 6.0 * wave(p, 0.2), 2.0 * wave(p, 0.6)),
    jaw=lambda p: 12.0 + 4.0 * wave(p, 0.0, 9),
    tail=lambda p: (2.0, 3.0 * wave(p, 0.3)),
  ), loop=True)


# DogEnemy must use these speeds, or the paws slide.
WALK_SPEED = 1.3
WALK_FRAMES = 20
RUN_SPEED = 5.8
RUN_FRAMES = 12
CIRCLE_SPEED = 1.3
CIRCLE_FRAMES = 16
BACK_SPEED = 1.0
BACK_FRAMES = 18


def walk_clip():
  """The stalk: a four-beat walk with the head held still and low, shoulders rolling."""
  paw = lambda offset, lift: stride(offset, WALK_SPEED, WALK_FRAMES, 0.62, lift, 40.0)
  return BeastClip("walk-loop", WALK_FRAMES, gait(channels(
    hips_pos=lambda p: (0.012 * wave(p, 0.1), 0.0, -0.06 + 0.01 * wave(p, 0.1, 2)),
    hips_rot=lambda p: (0.0, 4.0 * wave(p, 0.0), 3.0 * wave(p, 0.25)),
    chest_rot=lambda p: (2.0, -5.0 * wave(p, 0.25), -3.0 * wave(p, 0.5)),
    head_rot=lambda p: (12.0, 2.0 * wave(p, 0.6), 0.0),
    jaw=[(0, 12.0)],
    tail=lambda p: (1.0, 4.0 * wave(p, 0.15)),
  ), {"hind_l": paw(0.0, 0.08), "front_l": paw(0.75, 0.09), "hind_r": paw(0.5, 0.08), "front_r": paw(0.25, 0.09)}), loop=True)


def run_clip():
  """A rotary gallop: hind, hind, front, front, a flight, and the spine folding and stretching with it."""
  paw = lambda offset, lift: stride(offset, RUN_SPEED, RUN_FRAMES, 0.26, lift, 80.0)
  return BeastClip("run-loop", RUN_FRAMES, gait(channels(
    hips_pos=lambda p: (0.0, 0.04 * wave(p, 0.1), -0.03 + 0.06 * wave(p, 0.35)),
    hips_rot=lambda p: (9.0 * wave(p, 0.7), 0.0, 0.0),
    spine_rot=lambda p: (3.0 - 12.0 * wave(p, 0.7), 0.0, 0.0),
    chest_rot=lambda p: (2.0 - 8.0 * wave(p, 0.75), 0.0, 0.0),
    head_rot=lambda p: (4.0 + 5.0 * wave(p, 0.6), 0.0, 0.0),
    jaw=lambda p: 20.0 + 6.0 * wave(p, 0.4),
    tail=lambda p: (6.0 + 3.0 * wave(p, 0.5), 0.0),
  ), {"hind_l": paw(0.0, 0.16), "hind_r": paw(0.9, 0.16), "front_r": paw(0.55, 0.18), "front_l": paw(0.45, 0.18)}), loop=True)


def circle_clip(name, move, speed=CIRCLE_SPEED, frames=CIRCLE_FRAMES):
  """Circling the player: a stiff trot sideways, head down and fixed, teeth bared."""
  paw = lambda offset: stride(offset, speed, frames, 0.55, 0.08, 35.0, move)
  lean = 3.0 * move[0]
  return BeastClip(name, frames, gait(channels(
    hips_pos=lambda p: (0.0, 0.0, -0.07 + 0.008 * wave(p, 0.1, 2)),
    hips_rot=lambda p: (0.0, 2.0 * wave(p, 0.0), lean),
    chest_rot=lambda p: (3.0, -2.0 * wave(p, 0.0), lean * 0.5),
    head_rot=lambda p: (14.0 + 1.5 * wave(p, 0.3, 2), 0.0, -lean),
    jaw=lambda p: 18.0 + 3.0 * wave(p, 0.2, 2),
    tail=lambda p: (1.0, 3.0 * wave(p, 0.0)),
  ), {"front_l": paw(0.0), "hind_r": paw(0.0), "front_r": paw(0.5), "hind_l": paw(0.5)}), loop=True)


def attack_snap_clip():
  """Two snaps in a row: the head drops with the lips curled back, then bites twice, stepping in."""
  first, second = 0.3, 0.55
  coil = {"hips_pos": (0.0, -0.07, -0.08), "spine_rot": (5, 0, 0), "chest_rot": (6, 0, 0), "head_rot": (18, 0, 0), "jaw": 30.0, "tail": (0.0, 0.0)}
  coil.update(planted(0.0))
  bite = lambda root, jaw: {"root": root, "hips_pos": (0.0, 0.08, -0.04), "spine_rot": (2, 0, 0), "chest_rot": (-2, 0, 0), "head_rot": (0, 0, 0), "jaw": jaw}
  return BeastClip("attack_snap", 44, timeline(
    (0, dict(REST)),
    (12, coil),
    (14, dict(coil, hips_pos=(0.0, -0.08, -0.09), jaw=40.0)),
    (16, dict(bite(first * 0.7, 52.0), paw_front_l=(0.0, first * 0.7 + 0.1, 0.08))),
    (18, dict(bite(first, 2.0), **planted(first + 0.06, "front_l"))),
    (21, {"root": first, "hips_pos": (0.0, 0.02, -0.06), "head_rot": (8, 0, 0), "jaw": 46.0,
          "paw_front_r": (0.0, first * 0.5, 0.08), "paw_hind_l": (0.0, first * 0.5, 0.06)}),
    (24, dict(bite(second, 2.0), head_rot=(-4, 0, 0),
              **planted(second + 0.05, "front_r"), **planted(first, "hind_l"))),
    (30, dict(bite(second, 4.0), hips_pos=(0.0, 0.07, -0.05), head_rot=(2, 0, 0))),
    (34, {"paw_hind_r": (0.0, second * 0.5, 0.06), "paw_front_l": (0.0, first + 0.06, 0.0)}),
    (37, dict(planted(second, "hind_r", "front_l"), paw_hind_l=(0.0, (first + second) * 0.5, 0.05))),
    (44, rest_at(second)),
  ))


def attack_lunge_clip():
  """The leap: crouches low with the jaws open, launches mouth first and lands biting."""
  distance = 3.0
  crouch = {"hips_pos": (0.0, -0.1, -0.15), "spine_rot": (6, 0, 0), "chest_rot": (6, 0, 0), "head_rot": (14, 0, 0), "jaw": 36.0, "tail": (-2.0, 0.0)}
  crouch.update(planted(0.0))
  air = lambda root, z, tilt, front, hind: {
    "root": root, "hips_pos": (0.0, 0.0, z), "hips_rot": (tilt, 0, 0), "spine_rot": (-tilt * 0.3, 0, 0), "chest_rot": (0, 0, 0),
    "paw_front_l": (0.0, root + front[0], front[1]), "paw_front_r": (0.0, root + front[0] - 0.06, front[1]),
    "paw_hind_l": (0.0, root + hind[0], hind[1]), "paw_hind_r": (0.0, root + hind[0] + 0.06, hind[1]),
  }
  land = {"root": distance, "hips_pos": (0.0, 0.1, -0.12), "hips_rot": (8, 0, 0), "spine_rot": (4, 0, 0), "chest_rot": (2, 0, 0), "head_rot": (4, 0, 0), "jaw": 50.0,
          "paw_front_l_rot": 0.0, "paw_front_r_rot": 0.0}
  land.update(planted(distance + 0.25, "front_l", "front_r"))
  return BeastClip("attack_lunge", 58, timeline(
    (0, dict(REST)),
    (14, crouch),
    (18, dict(crouch, hips_pos=(0.0, -0.11, -0.16), jaw=40.0, paw_hind_l_rot=0.0, paw_hind_r_rot=0.0)),
    (20, dict(air(0.35, 0.06, -16, (0.45, 0.2), (-0.3, 0.0)), head_rot=(-4, 0, 0), jaw=56.0, tail=(8.0, 0.0),
              paw_front_l_rot=-40.0, paw_front_r_rot=-40.0, paw_hind_l_rot=50.0, paw_hind_r_rot=50.0)),
    (23, air(1.3, 0.3, -8, (0.5, 0.36), (-0.4, 0.3))),
    (26, dict(air(2.3, 0.22, 4, (0.45, 0.22), (-0.42, 0.34)), paw_hind_l_rot=30.0, paw_hind_r_rot=30.0)),
    (28, dict(land, **{"paw_hind_l": (0.0, distance - 0.35, 0.12), "paw_hind_r": (0.0, distance - 0.3, 0.12)})),
    (30, {"jaw": 0.0, "hips_pos": (0.0, 0.12, -0.14)}),
    (33, dict(planted(distance - 0.1, "hind_l", "hind_r"), paw_hind_l_rot=0.0, paw_hind_r_rot=0.0, tail=(2.0, 0.0))),
    (40, {"hips_pos": (0.0, 0.08, -0.1), "jaw": 8.0, "head_rot": (8, 0, 0), "hips_rot": (4, 0, 0)}),
    (58, rest_at(distance)),
  ))


def attack_thrash_clip():
  """Bites and does not let go: thrashes the head from side to side, pulling back, then releases."""
  reach = 0.4
  coil = {"hips_pos": (0.0, -0.06, -0.07), "spine_rot": (4, 0, 0), "chest_rot": (5, 0, 0), "head_rot": (16, 0, 0), "jaw": 44.0}
  coil.update(planted(0.0))
  hold = {"root": reach, "hips_pos": (0.0, 0.06, -0.06), "spine_rot": (2, 0, 0), "chest_rot": (0, 0, 0), "head_rot": (4, 0, 0), "jaw": 4.0}
  hold.update(planted(reach + 0.05, "front_l", "front_r"))
  poses = [
    (0, dict(REST)),
    (12, coil),
    (14, dict(coil, hips_pos=(0.0, -0.07, -0.08))),
    (16, {"root": reach * 0.7, "head_rot": (0, 0, 0), "jaw": 50.0, "paw_front_l": (0.0, reach * 0.7 + 0.1, 0.08), "paw_front_r": (0.0, reach * 0.7 + 0.05, 0.07)}),
    (18, dict(hold, **planted(0.0, "hind_l", "hind_r"))),
  ]
  # Each jerk pulls back a little more, and the body follows the head the other way.
  for i, frame in enumerate(range(22, 44, 4)):
    side = 1 if i % 2 == 0 else -1
    pull = min(i, 3) * 0.02
    poses.append((frame, {"head_rot": (6, 34 * side, -16 * side), "chest_rot": (0, -10 * side, 4 * side), "hips_rot": (0, 6 * side, 0),
                          "hips_pos": (0.0, 0.04 - pull, -0.07), "tail": (2.0, -10.0 * side), "jaw": 4.0}))
  poses += [
    (46, {"head_rot": (-6, 0, 0), "chest_rot": (-4, 0, 0), "hips_rot": (0, 0, 0), "hips_pos": (0.0, -0.04, -0.05), "jaw": 46.0, "tail": (2.0, 0.0)}),
    (50, {"paw_front_l": (0.0, reach - 0.05, 0.07)}),
    (53, planted(reach - 0.1, "front_l")),
    (60, dict(REST, root=reach - 0.1, **planted(reach - 0.1, "front_l"), **planted(reach + 0.05, "front_r"),
              **planted(0.0, "hind_l", "hind_r"))),
  ]
  return BeastClip("attack_thrash", 60, timeline(*poses))


def bark_clip():
  """Calls the pack: plants its feet, lifts the head and barks three times, each one heaving the chest."""
  braced = {"hips_pos": (0.0, -0.05, -0.04), "chest_rot": (-6, 0, 0), "head_rot": (-14, 0, 0), "jaw": 6.0, "tail": (5.0, 0.0)}
  poses = [(0, dict(REST)), (8, braced)]
  for frame in (12, 22, 32):
    poses += [
      (frame, {"jaw": 48.0, "head_rot": (-4, 0, 0), "chest_rot": (2, 0, 0), "hips_pos": (0.0, 0.0, -0.06)}),
      (frame + 4, {"jaw": 8.0, "head_rot": (-16, 0, 0), "chest_rot": (-6, 0, 0), "hips_pos": (0.0, -0.05, -0.04)}),
    ]
  poses.append((46, dict(REST)))
  return BeastClip("bark", 46, timeline(*poses))


HIT_POSE = {"hips_pos": (0.0, -0.05, -0.04), "hips_rot": (-2, 10, 0), "spine_rot": (0, 8, 0), "chest_rot": (-4, 12, 5), "head_rot": (-20, 22, 12), "jaw": 40.0, "tail": (-4.0, -8.0)}


def hurt_clip():
  """A yelp: the head snaps up and away and the body cringes."""
  return BeastClip("hurt", 16, timeline(
    (0, dict(REST)),
    (3, dict(HIT_POSE)),
    (6, dict(HIT_POSE, hips_pos=(0.0, -0.06, -0.05))),
    (16, dict(REST)),
  ))


def death_clip():
  """Its legs give out and it drops on its side, paddles a few times and goes still. Holds its last frame."""
  on_side = {"roll": -90.0, "pivot": 0.17, "lift": 0.0, "feet_free": 1.0, "hips_pos": (0.0, 0.0, -0.05), "hips_rot": (0, 0, 0),
             "spine_rot": (0, 0, 0), "chest_rot": (0, 0, 0), "head_rot": (10, 0, 10), "jaw": 30.0, "tail": (0.0, 2.0)}
  paddle = lambda a, b: {"paw_front_l": (0.0, a, 0.0), "paw_front_r": (0.0, b, 0.0), "paw_hind_l": (0.0, b, 0.0), "paw_hind_r": (0.0, a, 0.0),
                         "paw_front_l_rot": 30.0 * abs(a) / 0.15, "paw_hind_r_rot": 30.0 * abs(a) / 0.15}
  return BeastClip("death", 74, timeline(
    (0, dict(REST)),
    (4, dict(HIT_POSE)),
    (12, {"roll": 0.0, "feet_free": 0.0, "pivot": 0.17, "hips_pos": (0.0, -0.06, -0.2), "hips_rot": (6, 0, 0), "head_rot": (24, 10, -10), "jaw": 24.0}),
    (16, {"roll": -30.0, "feet_free": 0.5}),
    (22, dict(on_side, **paddle(0.0, 0.0))),
    (27, paddle(0.15, -0.1)),
    (32, paddle(-0.1, 0.15)),
    (38, paddle(0.12, -0.06)),
    (46, paddle(-0.04, 0.08)),
    (56, dict(paddle(0.02, 0.0), jaw=34.0)),
    (74, dict(on_side, jaw=38.0, head_rot=(14, 0, 14), **paddle(0.02, 0.0))),
  ))


CLIPS = [
  idle_clip(),
  walk_clip(),
  run_clip(),
  circle_clip("strafe_left-loop", (1.0, 0.0)),
  circle_clip("strafe_right-loop", (-1.0, 0.0)),
  circle_clip("walk_back-loop", (0.0, -1.0), BACK_SPEED, BACK_FRAMES),
  attack_snap_clip(),
  attack_lunge_clip(),
  attack_thrash_clip(),
  bark_clip(),
  hurt_clip(),
  death_clip(),
]

run("armature_dog", CLIPS, GLB_PATH)
