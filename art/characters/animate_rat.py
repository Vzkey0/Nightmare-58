"""Generates the giant rat's animations and exports them with its model.

Run it after build_rat.py, which writes the rigged model without animations:

  blender --background art/characters/rat.blend --python art/characters/animate_rat.py

The rat is the flanker of the pack: low, twitchy and fast. Attacks put at least 12 frames
(0.4 s) between the tell and the blow, as art_guide.md asks.
"""

import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(bpy.data.filepath)))

from beast_anim import LEGS, BeastClip, gait, planted, run, stride, timeline, wave

GLB_PATH = os.path.join(os.path.dirname(bpy.data.filepath), "..", "..", "game", "models", "characters", "rat.glb")

REST = {
  "root": 0.0,
  "hips_pos": (0.0, 0.0, 0.0),
  "hips_rot": (0, 0, 0),
  "spine_rot": (0, 0, 0),
  "chest_rot": (0, 0, 0),
  "head_rot": (-4, 0, 0),
  "jaw": 4.0,
  "tail": (1.0, 0.0),
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
  # Sniffs in bursts, shifts its weight and lifts a hand off the ground now and then.
  sniff = lambda p: max(wave(p, 0.3, 2), 0.0) ** 6
  return BeastClip("idle-loop", 120, channels(
    hips_pos=lambda p: (0.012 * wave(p, 0.0), 0.0, 0.005 * wave(p, 0.1, 6)),
    chest_rot=lambda p: (1.5 * wave(p, 0.1, 6), 2.0 * wave(p, 0.0), 0.0),
    head_rot=lambda p: (-4.0 + 3.0 * wave(p, 0.6, 2) + 2.5 * sniff(p) * wave(p, 0.0, 24), 10.0 * wave(p, 0.2), 3.0 * wave(p, 0.4)),
    jaw=lambda p: 4.0 + 4.0 * sniff(p) * max(wave(p, 0.0, 24), 0.0),
    tail=lambda p: (1.0 + 0.8 * wave(p, 0.3, 2), 4.0 * wave(p, 0.0)),
    paw_front_l=[(0, (0.0, 0.0, 0.0)), (60, (0.0, 0.0, 0.0)), (66, (0.0, 0.02, 0.06)), (73, (0.0, 0.0, 0.0))],
    paw_front_l_rot=[(0, 0.0), (60, 0.0), (66, 40.0), (73, 0.0)],
  ), loop=True)


# RatEnemy must use these speeds, or the paws slide.
WALK_SPEED = 0.9
WALK_FRAMES = 16
RUN_SPEED = 4.8
RUN_FRAMES = 8
CIRCLE_SPEED = 1.2
CIRCLE_FRAMES = 12


def walk_clip():
  """A sneaking four-beat walk: the spine snakes from side to side and the head stays on its target."""
  paw = lambda offset, lift: stride(offset, WALK_SPEED, WALK_FRAMES, 0.62, lift, 35.0)
  return BeastClip("walk-loop", WALK_FRAMES, gait(channels(
    hips_pos=lambda p: (0.015 * wave(p, 0.1), 0.0, -0.01 + 0.008 * wave(p, 0.1, 2)),
    hips_rot=lambda p: (0.0, 6.0 * wave(p, 0.0), 3.0 * wave(p, 0.25)),
    chest_rot=lambda p: (0.0, -9.0 * wave(p, 0.25), -2.0 * wave(p, 0.5)),
    head_rot=lambda p: (-2.0 + 2.0 * wave(p, 0.2, 2), 3.0 * wave(p, 0.6), 0.0),
    jaw=[(0, 6.0)],
    tail=lambda p: (1.0, 6.0 * wave(p, 0.1)),
  ), {"hind_l": paw(0.0, 0.06), "front_l": paw(0.75, 0.05), "hind_r": paw(0.5, 0.06), "front_r": paw(0.25, 0.05)}), loop=True)


def run_clip():
  """A bound: the hind legs land together and throw the body forward, the spine folds and unfolds."""
  paw = lambda offset, lift: stride(offset, RUN_SPEED, RUN_FRAMES, 0.28, lift, 70.0)
  return BeastClip("run-loop", RUN_FRAMES, gait(channels(
    hips_pos=lambda p: (0.0, 0.04 * wave(p, 0.1), 0.02 + 0.05 * wave(p, 0.4)),
    hips_rot=lambda p: (10.0 * wave(p, 0.65), 0.0, 0.0),
    spine_rot=lambda p: (-12.0 * wave(p, 0.65), 0.0, 0.0),
    chest_rot=lambda p: (-9.0 * wave(p, 0.7), 0.0, 0.0),
    head_rot=lambda p: (-8.0 + 3.0 * wave(p, 0.5), 0.0, 0.0),
    jaw=lambda p: 12.0 + 4.0 * wave(p, 0.3),
    tail=lambda p: (2.5 + 2.0 * wave(p, 0.5), 0.0),
  ), {"hind_l": paw(0.0, 0.13), "hind_r": paw(0.94, 0.13), "front_l": paw(0.55, 0.12), "front_r": paw(0.48, 0.12)}), loop=True)


def circle_clip(name, move, speed=CIRCLE_SPEED, frames=CIRCLE_FRAMES):
  """Circling the player: a quick trot sideways, head low, teeth bared and the tail lashing."""
  paw = lambda offset: stride(offset, speed, frames, 0.55, 0.06, 30.0, move)
  lean = 4.0 * move[0]
  return BeastClip(name, frames, gait(channels(
    hips_pos=lambda p: (0.0, 0.0, -0.03 + 0.006 * wave(p, 0.1, 2)),
    hips_rot=lambda p: (0.0, 2.0 * wave(p, 0.0), lean),
    chest_rot=lambda p: (2.0, -2.0 * wave(p, 0.0), lean * 0.5),
    head_rot=lambda p: (6.0 + 1.5 * wave(p, 0.3, 2), 0.0, -lean),
    jaw=lambda p: 16.0 + 3.0 * wave(p, 0.2, 2),
    tail=lambda p: (1.5, 7.0 * wave(p, 0.0)),
  ), {"front_l": paw(0.0), "hind_r": paw(0.0), "front_r": paw(0.5), "hind_l": paw(0.5)}), loop=True)


def attack_bite_clip():
  """The quick one: rears its head back with the incisors out, then snaps forward a short way."""
  reach = 0.35
  coil = {"hips_pos": (0.0, -0.07, -0.03), "spine_rot": (-4, 0, 0), "chest_rot": (-8, 0, 0), "head_rot": (-28, 0, 0), "jaw": 38.0, "tail": (3.0, 3.0)}
  coil.update(planted(0.0))
  snap = {"root": reach, "hips_pos": (0.0, 0.1, 0.02), "spine_rot": (0, 0, 0), "chest_rot": (-4, 0, 0), "head_rot": (-6, 0, 0), "jaw": 0.0, "tail": (1.0, -3.0)}
  snap.update(planted(reach + 0.05, "front_l", "front_r"))
  snap.update(planted(0.0, "hind_l", "hind_r"))
  return BeastClip("attack_bite", 34, timeline(
    (0, dict(REST)),
    (12, coil),
    (15, dict(coil, hips_pos=(0.0, -0.08, -0.035))),
    (17, {"root": reach * 0.6, "head_rot": (0, 0, 0), "jaw": 44.0, "paw_front_l": (0.0, reach * 0.6 + 0.08, 0.07), "paw_front_r": (0.0, reach * 0.6 + 0.04, 0.06)}),
    (19, snap),
    (25, dict(snap, hips_pos=(0.0, 0.09, 0.01), jaw=3.0)),
    (29, {"paw_hind_l": (0.0, reach * 0.5, 0.05), "paw_hind_r": (0.0, reach * 0.3, 0.03)}),
    (34, rest_at(reach)),
  ))


def attack_pounce_clip():
  """The leap from range: crouches with a wiggle of the hips, flies claws first and lands biting."""
  distance = 2.5
  crouch = {"hips_pos": (0.0, -0.08, -0.1), "spine_rot": (4, 0, 0), "chest_rot": (4, 0, 0), "head_rot": (8, 0, 0), "jaw": 20.0, "tail": (2.5, 0.0)}
  crouch.update(planted(0.0))
  air = lambda root, z, tilt, front, hind: dict({
    "root": root, "hips_pos": (0.0, 0.0, z), "hips_rot": (tilt, 0, 0), "spine_rot": (-tilt * 0.4, 0, 0), "chest_rot": (0, 0, 0),
    "paw_front_l": (0.0, root + front[0], front[1]), "paw_front_r": (0.0, root + front[0] - 0.04, front[1]),
    "paw_hind_l": (0.0, root + hind[0], hind[1]), "paw_hind_r": (0.0, root + hind[0] + 0.04, hind[1]),
  })
  land = {"root": distance, "hips_pos": (0.0, 0.08, -0.06), "hips_rot": (8, 0, 0), "spine_rot": (2, 0, 0), "chest_rot": (2, 0, 0), "head_rot": (4, 0, 0), "jaw": 48.0,
          "paw_front_l_rot": 0.0, "paw_front_r_rot": 0.0}
  land.update(planted(distance + 0.18, "front_l", "front_r"))
  return BeastClip("attack_pounce", 54, timeline(
    (0, dict(REST)),
    (13, crouch),
    (15, dict(crouch, hips_pos=(0.025, -0.08, -0.1), tail=(2.5, 8.0))),
    (17, dict(crouch, hips_pos=(-0.025, -0.08, -0.1), tail=(2.5, -8.0))),
    (19, dict(crouch, hips_pos=(0.0, -0.09, -0.11), tail=(2.5, 0.0), paw_hind_l_rot=0.0, paw_hind_r_rot=0.0)),
    (21, dict(air(0.25, 0.14, -16, (0.3, 0.16), (-0.25, 0.0)), head_rot=(-6, 0, 0), jaw=46.0, paw_front_l_rot=-30.0, paw_front_r_rot=-30.0,
              paw_hind_l_rot=45.0, paw_hind_r_rot=45.0)),
    (24, air(1.0, 0.4, -6, (0.36, 0.36), (-0.3, 0.3))),
    (27, dict(air(1.9, 0.24, 6, (0.3, 0.2), (-0.3, 0.26)), paw_hind_l_rot=20.0, paw_hind_r_rot=20.0)),
    (29, dict(land, **{"paw_hind_l": (0.0, distance - 0.25, 0.1), "paw_hind_r": (0.0, distance - 0.2, 0.1)})),
    (31, {"jaw": 0.0, "hips_pos": (0.0, 0.1, -0.08)}),
    (34, dict(planted(distance - 0.05, "hind_l", "hind_r"), paw_hind_l_rot=0.0, paw_hind_r_rot=0.0)),
    (40, {"hips_pos": (0.0, 0.08, -0.06), "jaw": 6.0, "head_rot": (4, 0, 0), "hips_rot": (6, 0, 0)}),
    (54, rest_at(distance)),
  ))


def attack_rake_clip():
  """Rears up on its hind legs hissing, claws over the head, and rakes both hands down at once."""
  reach = 0.3
  reared = {"hips_pos": (0.0, -0.06, 0.05), "hips_rot": (-50, 0, 0), "spine_rot": (-6, 0, 0), "chest_rot": (8, 0, 0), "head_rot": (-12, 0, 0), "jaw": 52.0,
            "tail": (2.0, 0.0), "tail_base": (48, 0), "paw_front_l": (0.07, 0.0, 0.62), "paw_front_r": (-0.07, 0.0, 0.64), "paw_front_l_rot": -70.0, "paw_front_r_rot": -70.0}
  reared.update(planted(0.0, "hind_l", "hind_r"))
  down = {"root": reach, "hips_pos": (0.0, 0.08, -0.02), "hips_rot": (4, 0, 0), "spine_rot": (2, 0, 0), "chest_rot": (3, 0, 0), "head_rot": (6, 0, 0), "jaw": 10.0,
          "tail": (1.0, 0.0), "tail_base": (0, 0), "paw_front_l_rot": 20.0, "paw_front_r_rot": 20.0}
  down.update(planted(reach + 0.28, "front_l", "front_r"))
  return BeastClip("attack_rake", 50, timeline(
    (0, dict(REST)),
    (6, {"hips_rot": (-20, 0, 0), "tail_base": (18, 0), "paw_front_l": (0.0, 0.0, 0.18), "paw_front_r": (0.0, 0.02, 0.16), "paw_front_l_rot": 10.0, "paw_front_r_rot": 10.0}),
    (13, reared),
    (17, dict(reared, hips_pos=(0.0, -0.07, 0.07), hips_rot=(-54, 0, 0), paw_front_l=(0.08, -0.04, 0.68), paw_front_r=(-0.08, -0.04, 0.7))),
    (19, {"root": reach * 0.5, "hips_rot": (-20, 0, 0), "tail_base": (18, 0), "paw_front_l": (0.0, reach * 0.5 + 0.2, 0.36), "paw_front_r": (0.0, reach * 0.5 + 0.2, 0.36),
          "paw_front_l_rot": -10.0, "paw_front_r_rot": -10.0}),
    (21, down),
    (29, dict(down, hips_pos=(0.0, 0.09, -0.03))),
    (34, {"paw_hind_l": (0.0, reach * 0.5, 0.05), "paw_hind_r": (0.0, reach * 0.4, 0.04)}),
    (38, dict(planted(reach, "hind_l", "hind_r"))),
    (50, rest_at(reach)),
  ))


def threat_clip():
  """The warning when it spots the player: half rears, mouth wide, trembling, tail lashing."""
  shake = [(0, (0.0, 0.0, 0.0))]
  for frame in range(10, 40, 2):
    shake.append((frame, (0.012 * (1 if frame % 4 else -1), -0.04, 0.03)))
  shake += [(44, (0.0, 0.0, 0.0)), (54, (0.0, 0.0, 0.0))]
  return BeastClip("threat", 54, timeline(
    (0, dict(REST)),
    (10, {"hips_rot": (-24, 0, 0), "chest_rot": (6, 0, 0), "head_rot": (-20, 0, 0), "jaw": 58.0, "tail": (4.0, 8.0),
          "paw_front_l": (0.0, -0.04, 0.2), "paw_front_r": (0.0, -0.02, 0.16), "paw_front_l_rot": -20.0, "paw_front_r_rot": -20.0}),
    (22, {"tail": (4.0, -8.0), "head_rot": (-24, 6, 4)}),
    (34, {"tail": (4.0, 8.0), "head_rot": (-20, -6, -4), "hips_rot": (-24, 0, 0), "jaw": 58.0,
          "paw_front_l": (0.0, -0.04, 0.2), "paw_front_r": (0.0, -0.02, 0.16), "paw_front_l_rot": -20.0, "paw_front_r_rot": -20.0}),
    (44, {"hips_rot": (0, 0, 0), "chest_rot": (0, 0, 0), "head_rot": (-4, 0, 0), "jaw": 8.0, "tail": (1.0, 0.0)}),
    (46, planted(0.0, "front_l", "front_r")),
    (54, dict(REST)),
  ) | {"hips_pos": shake})


HIT_POSE = {"hips_pos": (0.0, -0.04, 0.0), "hips_rot": (-3, 8, 0), "spine_rot": (-2, 8, 0), "chest_rot": (-3, 10, 4), "head_rot": (-22, 18, 10), "jaw": 34.0, "tail": (3.0, -6.0)}


def hurt_clip():
  """The head snaps away and the body flinches back, the paws stay put."""
  return BeastClip("hurt", 16, timeline(
    (0, dict(REST)),
    (3, dict(HIT_POSE)),
    (6, dict(HIT_POSE, hips_pos=(0.0, -0.05, 0.0))),
    (16, dict(REST)),
  ))


def death_clip():
  """Staggers, rolls onto its back and kicks the air until it goes still. Holds its last frame."""
  belly_up = {"roll": -155.0, "pivot": 0.28, "lift": -0.02, "feet_free": 1.0, "hips_rot": (0, 0, 0), "head_rot": (-10, 20, 0), "jaw": 40.0, "tail": (-2.0, 6.0)}
  kick = lambda a, b: {"paw_front_l": (0.0, 0.0, a), "paw_front_r": (0.0, 0.03, b), "paw_hind_l": (0.0, 0.03, b), "paw_hind_r": (0.0, 0.0, a),
                       "paw_front_l_rot": 40.0 * a / 0.12, "paw_hind_l_rot": 40.0 * b / 0.12}
  return BeastClip("death", 70, timeline(
    (0, dict(REST)),
    (4, dict(HIT_POSE)),
    (10, {"roll": 0.0, "feet_free": 0.0, "hips_pos": (0.0, -0.1, -0.06), "head_rot": (10, 24, 14), "jaw": 30.0}),
    (14, {"roll": -40.0, "feet_free": 0.4, "lift": 0.0, "pivot": 0.28}),
    (22, dict(belly_up, hips_pos=(0.0, -0.1, 0.0), **kick(0.0, 0.0))),
    (26, kick(0.12, 0.04)),
    (30, kick(0.03, 0.12)),
    (35, kick(0.1, 0.05)),
    (42, kick(0.02, 0.08)),
    (52, dict(kick(0.05, 0.05), jaw=40.0, head_rot=(-10, 20, 0))),
    (70, dict(belly_up, hips_pos=(0.0, -0.1, 0.0), jaw=46.0, head_rot=(-14, 26, 0), **kick(0.07, 0.06))),
  ))


CLIPS = [
  idle_clip(),
  walk_clip(),
  run_clip(),
  circle_clip("strafe_left-loop", (1.0, 0.0)),
  circle_clip("strafe_right-loop", (-1.0, 0.0)),
  circle_clip("walk_back-loop", (0.0, -1.0), WALK_SPEED, WALK_FRAMES),
  attack_bite_clip(),
  attack_pounce_clip(),
  attack_rake_clip(),
  threat_clip(),
  hurt_clip(),
  death_clip(),
]

run("armature_rat", CLIPS, GLB_PATH)
