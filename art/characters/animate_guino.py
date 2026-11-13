"""Generates Güino's animations and exports them with his model.

Run it after build_guino.py, which writes the rigged model without animations:

  blender --background art/characters/guino.blend --python art/characters/animate_guino.py

Güino closes the avenue: a giant starved husky. He is heavy, not slow. Every opening blow has a long,
readable tell (at least 14 frames, 0.47 s) and then lands faster than his size suggests; the blows
that follow inside a combo come quicker. Phase two adds the flurry and the quake, and GuinoEnemy plays
every clip faster. Distances are in meters at his full size.
"""

import math
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(bpy.data.filepath)))

from beast_anim import LEGS, BeastClip, gait, planted, run, stride, timeline, wave

GLB_PATH = os.path.join(os.path.dirname(bpy.data.filepath), "..", "..", "game", "models", "characters", "guino.glb")

# Hunched over the shoulders with the head hanging. The jaw is modeled open in the full grin: 0 keeps
# it there, -34 shuts it and anything above opens it wider.
REST = {
  "root": 0.0,
  "hips_pos": (0.0, 0.0, -0.08),
  "hips_rot": (0, 0, 0),
  "spine_rot": (2, 0, 0),
  "chest_rot": (4, 0, 0),
  "head_rot": (8, 0, 0),
  "jaw": -14.0,
  "tail": (-1.0, 0.0),
  "tail_base": (0.0, 0.0),
  "spin": 0.0,
  "roll": 0.0,
  "lift": 0.0,
  "feet_free": 0.0,
}
REST.update(planted(0.0))
REST.update({f"paw_{leg}_rot": 0.0 for leg in LEGS})
SHUT = -34.0


def channels(**changes):
  result = {name: [(0, value)] for name, value in REST.items()}
  result.update(changes)
  return result


def rest_at(distance):
  return dict(REST, root=distance, **planted(distance))


def pulse(p, start, end):
  """0 outside start..end, rising smoothly to 1 halfway."""
  if not start < p < end:
    return 0.0
  return math.sin(math.pi * (p - start) / (end - start)) ** 2


def idle_clip():
  # Slow breaths that lift the bare ribs, the head hanging and swaying on its target. Halfway it cocks
  # the head sideways like a curious dog, which on him is the worst part, and one paw scrapes the asphalt.
  tilt = lambda p: pulse(p, 0.45, 0.8)
  return BeastClip("idle-loop", 150, channels(
    hips_pos=lambda p: (0.03 * wave(p, 0.0), 0.0, -0.08 + 0.03 * wave(p, 0.1, 3)),
    spine_rot=lambda p: (2.0 + 1.5 * wave(p, 0.12, 3), 0.0, 0.0),
    chest_rot=lambda p: (4.0 + 2.0 * wave(p, 0.15, 3), 2.0 * wave(p, 0.3), 1.5 * wave(p, 0.0)),
    head_rot=lambda p: (8.0 + 3.0 * wave(p, 0.2, 3) - 6.0 * tilt(p), 7.0 * wave(p, 0.25), 24.0 * tilt(p)),
    jaw=lambda p: -14.0 + 7.0 * max(wave(p, 0.0, 3), 0.0),
    tail=lambda p: (-1.0 + 0.6 * wave(p, 0.2, 3), 4.0 * wave(p, 0.35)),
    paw_front_r=[(0, (0.0, 0.0, 0.0)), (24, (0.0, 0.0, 0.0)), (30, (0.0, 0.35, 0.25)), (36, (0.0, -0.12, 0.03)),
                 (40, (0.0, -0.22, 0.0)), (46, (0.0, -0.05, 0.15)), (52, (0.0, 0.0, 0.0))],
    paw_front_r_rot=[(0, 0.0), (24, 0.0), (30, 30.0), (36, -10.0), (40, 0.0), (46, 25.0), (52, 0.0)],
  ), loop=True)


# GuinoEnemy must use these speeds, or the paws slide.
WALK_SPEED = 1.6
WALK_FRAMES = 36
RUN_SPEED = 7.5
RUN_FRAMES = 20
CIRCLE_SPEED = 1.5
CIRCLE_FRAMES = 28
BACK_SPEED = 1.2
BACK_FRAMES = 30


def walk_clip():
  """A heavy prowl: a four-beat walk, the shoulders rolling over each planted forepaw and the head low
  and still, locked on its prey."""
  paw = lambda offset, lift: stride(offset, WALK_SPEED, WALK_FRAMES, 0.62, lift, 32.0)
  return BeastClip("walk-loop", WALK_FRAMES, gait(channels(
    hips_pos=lambda p: (0.05 * wave(p, 0.1), 0.0, -0.12 + 0.035 * wave(p, 0.1, 2)),
    hips_rot=lambda p: (0.0, 4.0 * wave(p, 0.0), 4.0 * wave(p, 0.25)),
    spine_rot=lambda p: (2.0, -2.0 * wave(p, 0.1), 0.0),
    chest_rot=lambda p: (5.0 + 1.5 * wave(p, 0.35, 2), -5.0 * wave(p, 0.25), -5.0 * wave(p, 0.5)),
    head_rot=lambda p: (14.0 + 1.5 * wave(p, 0.4, 2), 2.0 * wave(p, 0.6), 0.0),
    jaw=lambda p: -16.0 + 3.0 * wave(p, 0.3, 2),
    tail=lambda p: (-1.5, 5.0 * wave(p, 0.15)),
  ), {"hind_l": paw(0.0, 0.32), "front_l": paw(0.75, 0.38), "hind_r": paw(0.5, 0.32), "front_r": paw(0.25, 0.38)}), loop=True)


def run_clip():
  """A rotary gallop that shakes the street: hind, hind, front, front and a short flight, the spine
  folding and stretching and the head driving forward."""
  paw = lambda offset, lift: stride(offset, RUN_SPEED, RUN_FRAMES, 0.28, lift, 55.0)
  return BeastClip("run-loop", RUN_FRAMES, gait(channels(
    hips_pos=lambda p: (0.0, 0.12 * wave(p, 0.1), -0.06 + 0.16 * wave(p, 0.35)),
    hips_rot=lambda p: (9.0 * wave(p, 0.7), 0.0, 0.0),
    spine_rot=lambda p: (2.0 - 10.0 * wave(p, 0.7), 0.0, 0.0),
    chest_rot=lambda p: (4.0 - 7.0 * wave(p, 0.75), 0.0, 0.0),
    head_rot=lambda p: (6.0 + 5.0 * wave(p, 0.6), 0.0, 0.0),
    jaw=lambda p: -6.0 + 6.0 * wave(p, 0.4),
    tail=lambda p: (-3.0 + 2.0 * wave(p, 0.5), 0.0),
  ), {"hind_l": paw(0.0, 0.45), "hind_r": paw(0.9, 0.45), "front_r": paw(0.55, 0.55), "front_l": paw(0.45, 0.55)}), loop=True)


def circle_clip(name, move, speed=CIRCLE_SPEED, frames=CIRCLE_FRAMES):
  """Circling the player: a stiff, heavy trot sideways with the head down and fixed and the hackles up."""
  paw = lambda offset: stride(offset, speed, frames, 0.55, 0.28, 28.0, move)
  lean = 4.0 * move[0]
  return BeastClip(name, frames, gait(channels(
    hips_pos=lambda p: (0.0, 0.0, -0.14 + 0.025 * wave(p, 0.1, 2)),
    hips_rot=lambda p: (0.0, 2.0 * wave(p, 0.0), lean),
    chest_rot=lambda p: (6.0, -2.0 * wave(p, 0.0), lean * 0.5),
    head_rot=lambda p: (16.0 + 1.5 * wave(p, 0.3, 2), 0.0, -lean),
    jaw=lambda p: -22.0 + 3.0 * wave(p, 0.2, 2),
    tail=lambda p: (-0.5, 4.0 * wave(p, 0.0)),
  ), {"front_l": paw(0.0), "hind_r": paw(0.0), "front_r": paw(0.5), "hind_l": paw(0.5)}), loop=True)


def howl_clip():
  """On first sight: gathers itself, throws the head to the sky and howls with the chest heaving, then
  drops it toward the player with a snarl. The root stays put: a warning, not a move."""
  sky = {"hips_pos": (0.0, -0.15, -0.2), "hips_rot": (-6, 0, 0), "spine_rot": (-6, 0, 0), "chest_rot": (-10, 0, 0),
         "head_rot": (-55, 0, 0), "jaw": 22.0, "tail": (-3.0, 0.0)}
  return BeastClip("howl", 84, timeline(
    (0, dict(REST)),
    (10, {"hips_pos": (0.0, -0.08, -0.15), "chest_rot": (8, 0, 0), "head_rot": (24, 0, 0), "jaw": SHUT}),
    (14, {"paw_front_l": (0.0, 0.25, 0.22), "paw_front_l_rot": 30.0}),
    (20, dict(planted(0.15, "front_l"), paw_front_l_rot=0.0)),
    (22, sky),
    (30, dict(sky, head_rot=(-60, 3, 2), jaw=26.0)),
    (40, dict(sky, head_rot=(-58, -3, -2), jaw=24.0, chest_rot=(-12, 0, 0))),
    (50, dict(sky, head_rot=(-62, 2, 0), jaw=25.0)),
    (56, {"head_rot": (-50, 0, 0), "jaw": 10.0}),
    (64, {"hips_pos": (0.0, 0.05, -0.18), "hips_rot": (0, 0, 0), "spine_rot": (3, 0, 0), "chest_rot": (8, 0, 0),
          "head_rot": (22, 0, 0), "jaw": 16.0, "tail": (-1.0, 0.0)}),
    (70, {"head_rot": (18, 6, -8), "jaw": 12.0, "paw_front_l": (0.0, 0.15, 0.0), "paw_front_l_rot": 0.0}),
    (75, {"paw_front_l": (0.0, 0.15, 0.18), "paw_front_l_rot": 25.0}),
    (80, dict(planted(0.0, "front_l"), paw_front_l_rot=0.0)),
    (84, dict(REST)),
  ))


def enrage_clip():
  """Phase two: shakes the street off like a wet dog, rears up on the hind legs with the ribs aglow
  and slams the forepaws down, roaring at the player."""
  poses = [(0, dict(REST)), (6, {"hips_pos": (0.0, 0.0, -0.18), "head_rot": (14, 0, 0), "jaw": SHUT})]
  # The shake runs from the head back to the tail, each jerk a little smaller.
  for i, frame in enumerate(range(8, 30, 3)):
    side = 1 if i % 2 == 0 else -1
    fade = 1.0 - i / 9
    poses.append((frame, {"head_rot": (10, 38 * side * fade, -24 * side * fade), "chest_rot": (4, -12 * side * fade, 10 * side * fade),
                          "hips_rot": (0, 8 * side * fade, -8 * side * fade), "tail": (0.0, -14.0 * side * fade), "jaw": -20.0}))
  reared = {"hips_pos": (0.0, -0.45, -0.3), "hips_rot": (-38, 0, 0), "spine_rot": (-5, 0, 0), "chest_rot": (-5, 0, 0),
            "head_rot": (-35, 0, 0), "jaw": 28.0, "tail": (-1.0, 0.0), "tail_base": (30.0, 0.0),
            "paw_front_l": (0.1, -0.5, 1.8), "paw_front_r": (-0.1, -0.55, 1.75), "paw_front_l_rot": 55.0, "paw_front_r_rot": 55.0}
  slammed = {"hips_pos": (0.0, 0.25, -0.2), "hips_rot": (8, 0, 0), "spine_rot": (6, 0, 0), "chest_rot": (8, 0, 0),
             "head_rot": (-12, 0, 0), "jaw": 32.0, "tail": (-1.0, 0.0), "tail_base": (0.0, 0.0),
             "paw_front_l_rot": 0.0, "paw_front_r_rot": 0.0}
  slammed.update(planted(0.4, "front_l", "front_r"))
  poses += [
    (31, {"head_rot": (10, 0, 0), "chest_rot": (4, 0, 0), "hips_rot": (0, 0, 0), "tail": (-1.0, 0.0), "hips_pos": (0.0, -0.1, -0.25),
          "paw_front_l_rot": 0.0, "paw_front_r_rot": 0.0, **planted(0.0, "front_l", "front_r")}),
    (44, reared),
    (50, dict(reared, hips_rot=(-42, 0, 0), head_rot=(-40, 0, 0), paw_front_l=(0.12, -0.45, 2.0), paw_front_r=(-0.12, -0.5, 1.95))),
    (53, slammed),
    (56, dict(slammed, hips_pos=(0.0, 0.25, -0.32), chest_rot=(12, 0, 0))),
  ]
  # Roars on the ground, the head trembling.
  for i, frame in enumerate(range(60, 76, 4)):
    poses.append((frame, {"head_rot": (-8, 5 * (1 if i % 2 else -1), 0), "jaw": 30.0 + 3 * (i % 2), "hips_pos": (0.0, 0.2, -0.24)}))
  poses += [
    (76, planted(0.4, "front_l", "front_r")),
    (80, {"head_rot": (14, 0, 0), "jaw": 4.0, "paw_front_l": (0.0, 0.25, 0.2), "paw_front_l_rot": 25.0, **planted(0.4, "front_r")}),
    (85, dict(planted(0.0, "front_l"), paw_front_l_rot=0.0, paw_front_r=(0.0, 0.25, 0.2), paw_front_r_rot=25.0)),
    (90, dict(planted(0.0, "front_r"), paw_front_r_rot=0.0)),
    (96, dict(REST)),
  ]
  return BeastClip("enrage", 96, timeline(*poses))


def swipe(paw, frame, start, end, side, height=0.55):
  """A forepaw raking across the front from the side given by side (+1 his left) to the other, while
  the root steps from start to end."""
  return [
    (frame, {"root": start, paw: (0.5 * side, start + 1.0, 0.9)}),
    (frame + 2, {"root": start + (end - start) * 0.7, paw: (0.0, end + 1.4, height)}),
    (frame + 4, {"root": end, paw: (-0.75 * side, end + 1.1, 0.3), f"{paw}_rot": -20.0}),
  ]


def attack_maul_clip():
  """Two rakes of the forepaws: the right one from his right, then the left one back from his left,
  stepping in with each. The second comes quicker: dodging the first is not enough."""
  wind_right = {"hips_pos": (0.22, -0.1, -0.16), "chest_rot": (2, -14, 8), "head_rot": (6, 12, -6), "jaw": -26.0, "tail": (0.0, 6.0),
                "paw_front_r": (-0.7, 0.2, 1.3), "paw_front_r_rot": 40.0}
  wind_left = {"hips_pos": (-0.22, 0.4, -0.16), "chest_rot": (2, 14, -8), "head_rot": (6, -12, 6), "tail": (0.0, -6.0),
               "paw_front_l": (0.7, 0.85, 1.25), "paw_front_l_rot": 40.0}
  poses = [
    (0, dict(REST)),
    (14, wind_right),
    (18, dict(wind_right, paw_front_r=(-0.82, 0.1, 1.45), chest_rot=(0, -18, 10), **planted(0.0, "front_l", "hind_l", "hind_r"))),
  ]
  poses += swipe("paw_front_r", 20, 0.0, 0.5, -1)
  poses += [
    (21, {"chest_rot": (6, 16, -6), "hips_pos": (0.0, 0.25, -0.2), "head_rot": (10, -10, 4), "jaw": -6.0}),
    (26, {"paw_front_r": (0.55, 1.5, 0.12), "paw_hind_l": (0.0, 0.25, 0.3)}),
    (29, dict(planted(0.0, "front_l", "hind_r"), paw_front_r=(0.3, 1.45, 0.0), paw_front_r_rot=0.0, paw_front_l_rot=0.0, **planted(0.45, "hind_l"))),
    (32, {"paw_hind_r": (0.0, 0.25, 0.3)}),
    (33, wind_left),
    (35, planted(0.5, "hind_r")),
    (39, dict(wind_left, paw_front_l=(0.85, 0.75, 1.4), chest_rot=(0, 18, -10))),
  ]
  poses += swipe("paw_front_l", 41, 0.5, 1.0, 1)
  poses += [
    (42, {"chest_rot": (6, -16, 6), "hips_pos": (0.0, 0.3, -0.2), "head_rot": (10, 10, -4), "jaw": -6.0}),
    (44, planted(0.45, "hind_l")),
    (48, {"paw_front_l": (-0.6, 1.95, 0.12), "paw_hind_l": (0.0, 0.75, 0.3)}),
    (52, dict(planted(1.0, "hind_l"), paw_front_l=(-0.35, 1.9, 0.0), paw_front_l_rot=0.0, paw_front_r=(0.3, 1.45, 0.0))),
    (54, {"paw_hind_r": (0.0, 0.8, 0.3)}),
    (56, {"paw_front_r": (0.15, 1.25, 0.25), "chest_rot": (5, 0, 0), "hips_pos": (0.0, 0.1, -0.12),
          "head_rot": (10, 0, 0), "jaw": -16.0, "tail": (-1.0, 0.0), "paw_front_l": (-0.35, 1.9, 0.0)}),
    (58, planted(1.0, "hind_r")),
    (60, dict(planted(1.0, "front_r"), paw_front_l=(-0.15, 1.45, 0.25))),
    (64, planted(1.0, "front_l")),
    (72, rest_at(1.0)),
  ]
  return BeastClip("attack_maul", 72, timeline(*poses))


def crunch_poses(base, root, held, coil_frames=16, hold=3):
  """The bite: pulls the head back and up with the jaws as wide as they go, then lunges root meters
  from base and snaps them shut, shaking what it caught. held keeps the paws where they stand until
  the lunge."""
  coil = dict(held, root=base, **{"hips_pos": (0.0, -0.35, -0.2), "hips_rot": (0, 0, 0), "spine_rot": (-4, 0, 0), "chest_rot": (-10, 0, 0),
          "head_rot": (-22, 0, 0), "jaw": 20.0, "tail": (2.0, 0.0)})
  bite = {"root": base + root, "hips_pos": (0.0, 0.3, -0.12), "spine_rot": (4, 0, 0), "chest_rot": (10, 0, 0),
          "head_rot": (18, 0, 0), "jaw": SHUT, "tail": (-2.0, 0.0)}
  bite.update(planted(base + root + 0.3, "front_l", "front_r"))
  f = coil_frames
  return f, [
    (f, coil),
    (f + hold, dict(coil, head_rot=(-26, 0, 4), jaw=26.0)),
    (f + hold + 2, {"root": base + root * 0.55, "hips_pos": (0.0, 0.2, -0.05), "spine_rot": (2, 0, 0), "chest_rot": (6, 0, 0),
                    "head_rot": (8, 0, 0), "jaw": 28.0, "paw_front_l": (0.0, base + root * 0.55 + 0.7, 0.35), "paw_front_r": (0.0, base + root * 0.55 + 0.6, 0.3),
                    "paw_hind_l": (0.0, base + 0.1, 0.25), "paw_hind_r": (0.0, base, 0.2)}),
    (f + hold + 4, dict(bite, **planted(base + root - 0.4, "hind_l", "hind_r"))),
    (f + hold + 6, {"head_rot": (16, 10, -6)}),
    (f + hold + 8, {"head_rot": (16, -8, 5)}),
    (f + hold + 10, {"head_rot": (14, 0, 0), "jaw": SHUT}),
    (f + hold + 13, {"jaw": 0.0, "head_rot": (10, 0, 0), "hips_pos": (0.0, 0.15, -0.1)}),
  ]


def attack_crunch_clip():
  root = 1.6
  frame, poses = crunch_poses(0.0, root, planted(0.0))
  end = frame + 16
  poses = [(0, dict(REST))] + poses + [
    (end + 4, {"paw_hind_l": (0.0, root - 0.1, 0.3)}),
    (end + 8, dict(planted(root, "hind_l"), paw_hind_r=(0.0, root - 0.1, 0.3))),
    (end + 12, dict(planted(root, "hind_r"), paw_front_l=(0.0, root + 0.15, 0.2))),
    (end + 16, dict(planted(root, "front_l"), paw_front_r=(0.0, root + 0.15, 0.2))),
    (end + 20, planted(root, "front_r")),
    (56, rest_at(root)),
  ]
  return BeastClip("attack_crunch", 56, timeline(*poses))


def attack_whirl_clip():
  """The tail whip: crouches with the tail cocked and the head turning over the right shoulder, then
  spins a full turn in a low hop. The tail drops to chest height and sweeps everything around him; only
  hugging his flank is safe. It cracks past the end of the spin and settles."""
  crouch = {"hips_pos": (0.0, 0.0, -0.35), "spine_rot": (6, 0, 0), "chest_rot": (8, 0, 0), "head_rot": (16, -25, 0),
            "jaw": -30.0, "tail": (4.0, 8.0), "spin": 0.0, "lift": 0.0, "feet_free": 0.0}
  crouch.update(planted(0.0))
  spin = lambda turn, lift, tuck: {
    "spin": turn, "lift": lift, "feet_free": 1.0, "pivot": 1.4, "hips_pos": (0.0, 0.0, -0.3), "head_rot": (10, -10, 0),
    "tail": (-3.5, 10.0), "tail_base": (-40.0, 0.0),
    **{f"paw_{leg}": (0.0, 0.1, tuck) for leg in LEGS}, **{f"paw_{leg}_rot": 40.0 * tuck / 0.35 for leg in LEGS},
  }
  return BeastClip("attack_whirl", 60, timeline(
    (0, dict(REST)),
    (14, crouch),
    (18, dict(crouch, hips_pos=(0.0, 0.0, -0.4), tail=(5.0, 10.0))),
    (19, dict(spin(-20.0, 0.12, 0.15), root=0.0)),
    (21, spin(-115.0, 0.24, 0.35)),
    (23, spin(-225.0, 0.26, 0.35)),
    (25, dict(spin(-320.0, 0.15, 0.25), root=0.3)),
    (27, dict(spin(-360.0, 0.0, 0.0), tail=(-3.0, -14.0), **planted(0.3))),
    (29, {"hips_pos": (0.0, 0.0, -0.42), "tail": (-2.5, -18.0), "chest_rot": (10, 0, 0)}),
    (33, {"tail": (-1.5, 8.0), "tail_base": (-15.0, 0.0), "hips_pos": (0.0, 0.0, -0.3)}),
    (38, {"tail": (-1.0, -3.0), "tail_base": (0.0, 0.0), "head_rot": (12, 0, 0), "jaw": -20.0}),
    (46, {"hips_pos": (0.0, 0.0, -0.12), "spine_rot": (3, 0, 0), "chest_rot": (5, 0, 0)}),
    (60, dict(rest_at(0.3), spin=-360.0, feet_free=1.0, lift=0.0, pivot=1.4)),
  ))


def attack_crash_clip():
  """From range: drops low and wiggles his rump like a cat about to pounce, then flies six meters with
  the forepaws reaching and lands on both of them, shaking the street. A bad dodge forward lands under him."""
  distance = 6.0
  low = {"hips_pos": (0.0, -0.15, -0.35), "spine_rot": (6, 0, 0), "chest_rot": (8, 0, 0), "head_rot": (16, 0, 0), "jaw": SHUT, "tail": (-2.0, 0.0)}
  low.update(planted(0.0))
  poses = [(0, dict(REST)), (10, low)]
  for i, frame in enumerate(range(12, 22, 2)):
    side = 1 if i % 2 == 0 else -1
    poses.append((frame, {"hips_rot": (0, 8 * side, 0), "hips_pos": (0.08 * side, -0.18, -0.38), "tail": (-2.0, -10.0 * side),
                          "paw_hind_l": (0.0, 0.0, 0.08 if side > 0 else 0.0), "paw_hind_r": (0.0, 0.0, 0.0 if side > 0 else 0.08)}))
  air = lambda root, z, tilt, front, hind: {
    "root": root, "hips_pos": (0.0, 0.0, z), "hips_rot": (tilt, 0, 0), "spine_rot": (-tilt * 0.3, 0, 0), "chest_rot": (0, 0, 0),
    "paw_front_l": (0.0, root + front[0], front[1]), "paw_front_r": (0.0, root + front[0] - 0.15, front[1]),
    "paw_hind_l": (0.0, root + hind[0], hind[1]), "paw_hind_r": (0.0, root + hind[0] + 0.15, hind[1]),
  }
  land = {"root": distance, "hips_pos": (0.0, 0.1, -0.25), "hips_rot": (10, 0, 0), "spine_rot": (5, 0, 0), "chest_rot": (8, 0, 0),
          "head_rot": (-12, 0, 0), "jaw": 10.0, "paw_front_l_rot": 0.0, "paw_front_r_rot": 0.0}
  land.update(planted(distance + 0.6, "front_l", "front_r"))
  poses += [
    (22, dict(low, root=0.0, hips_rot=(0, 0, 0), hips_pos=(0.0, -0.25, -0.45), head_rot=(20, 0, 0), tail=(-2.0, 0.0),
              paw_hind_l_rot=0.0, paw_hind_r_rot=0.0)),
    (24, dict(air(1.0, 0.4, -18, (0.9, 1.05), (-0.8, 0.2)), head_rot=(0, 0, 0), jaw=20.0, tail=(-4.0, 0.0),
              paw_front_l_rot=-30.0, paw_front_r_rot=-30.0, paw_hind_l_rot=60.0, paw_hind_r_rot=60.0)),
    (27, air(3.0, 1.4, -6, (1.1, 1.75), (-0.6, 1.2))),
    (30, dict(air(4.8, 0.9, 10, (1.25, 1.2), (-0.7, 1.0)), paw_hind_l_rot=30.0, paw_hind_r_rot=30.0, head_rot=(14, 0, 0))),
    (32, dict(land, paw_hind_l=(0.0, distance - 0.6, 0.6), paw_hind_r=(0.0, distance - 0.5, 0.6))),
    (34, dict(planted(distance - 0.3, "hind_l", "hind_r"), hips_pos=(0.0, 0.1, -0.34), chest_rot=(11, 0, 0),
              paw_hind_l_rot=0.0, paw_hind_r_rot=0.0, tail=(-1.0, 0.0))),
    (38, {"hips_pos": (0.0, 0.05, -0.2), "chest_rot": (8, 0, 0), "head_rot": (10, 0, 0)}),
    (44, {"head_rot": (12, 18, -10), "jaw": 16.0}),
    (48, {"head_rot": (12, -14, 8), "jaw": 0.0}),
    (52, dict(planted(distance + 0.6, "front_l", "front_r"), head_rot=(10, 0, 0), jaw=-14.0)),
    (56, dict(planted(distance + 0.6, "front_r"), paw_front_l=(0.0, distance + 0.3, 0.2))),
    (60, dict(planted(distance, "front_l"), paw_front_r=(0.0, distance + 0.3, 0.2), **planted(distance - 0.3, "hind_l"))),
    (64, dict(planted(distance, "front_r"), paw_hind_l=(0.0, distance - 0.1, 0.25), **planted(distance - 0.3, "hind_r"))),
    (68, dict(planted(distance, "hind_l"), paw_hind_r=(0.0, distance - 0.1, 0.25))),
    (72, rest_at(distance)),
  ]
  return BeastClip("attack_crash", 72, timeline(*poses))


def attack_frenzy_clip():
  """Phase two: three rakes in a row, right, left, right, stepping in with each, then a pause as he
  rears his head back and a late bite to catch whoever rolled out too early."""
  poses = [
    (0, dict(REST)),
    (12, {"hips_pos": (0.2, -0.1, -0.14), "chest_rot": (0, -14, 8), "head_rot": (-6, 8, 0), "jaw": 24.0, "tail": (2.0, 6.0),
          "paw_front_r": (-0.7, 0.3, 1.25), "paw_front_r_rot": 40.0, **planted(0.0, "front_l", "hind_l", "hind_r")}),
  ]
  poses += swipe("paw_front_r", 13, 0.0, 0.4, -1)
  poses += [
    (15, dict(planted(0.0, "front_l"), paw_front_l_rot=0.0)),
    (17, {"chest_rot": (4, 14, -6), "hips_pos": (-0.15, 0.2, -0.16), "head_rot": (6, -8, 0), "jaw": 10.0,
          "paw_front_l": (0.7, 0.8, 1.1), "paw_front_l_rot": 40.0}),
    (19, {"paw_front_r": (0.25, 1.4, 0.0), "paw_front_r_rot": 0.0}),
  ]
  poses += swipe("paw_front_l", 20, 0.4, 0.8, 1)
  poses += [
    (22, planted(0.0, "hind_l", "hind_r")),
    (23, {"paw_front_r": (0.25, 1.4, 0.0)}),
    (24, {"chest_rot": (4, -14, 6), "hips_pos": (0.15, 0.3, -0.16), "head_rot": (6, 8, 0), "jaw": 16.0,
          "paw_front_r": (-0.7, 1.4, 1.1), "paw_front_r_rot": 40.0, "paw_hind_l": (0.0, 0.5, 0.3), "paw_hind_r": (0.0, 0.3, 0.3)}),
    (26, {"paw_front_l": (-0.25, 1.7, 0.0), "paw_front_l_rot": 0.0, **planted(0.8, "hind_l"), **planted(0.6, "hind_r")}),
  ]
  poses += swipe("paw_front_r", 27, 0.8, 1.2, -1)
  poses += [
    (31, {"chest_rot": (6, 10, -4), "hips_pos": (0.0, 0.2, -0.18)}),
    (33, {"paw_front_r": (0.25, 1.7, 0.0), "paw_front_r_rot": 0.0}),
  ]
  held = {"paw_front_r": (0.25, 1.7, 0.0), "paw_front_l": (-0.25, 1.7, 0.0)}
  held.update(planted(0.8, "hind_l"))
  held.update(planted(0.6, "hind_r"))
  frame, bite = crunch_poses(1.2, 1.0, held, coil_frames=36, hold=8)
  poses += bite + [
    (frame + 25, {"paw_hind_l": (0.0, 2.0, 0.3), "paw_hind_r": (0.0, 1.6, 0.25)}),
    (frame + 29, dict(planted(2.2, "hind_l"), paw_hind_r=(0.0, 2.1, 0.3), paw_front_r=(0.0, 2.4, 0.2))),
    (frame + 33, dict(planted(2.2, "hind_r", "front_r"), paw_front_l=(0.0, 2.4, 0.2))),
    (frame + 37, planted(2.2, "front_l")),
    (84, rest_at(2.2)),
  ]
  return BeastClip("attack_frenzy", 84, timeline(*poses))


def attack_quake_clip():
  """Phase two: rears up on the hind legs, towering and roaring, and drops onto both forepaws with all
  his weight. The shock runs along the ground around him: from close up, only a roll gets out."""
  reared = {"hips_pos": (0.0, -0.45, -0.3), "hips_rot": (-38, 0, 0), "spine_rot": (-5, 0, 0), "chest_rot": (-5, 0, 0),
            "head_rot": (-30, 0, 0), "jaw": 26.0, "tail": (-1.0, 0.0), "tail_base": (30.0, 0.0),
            "paw_front_l": (0.1, -0.5, 1.8), "paw_front_r": (-0.1, -0.55, 1.75), "paw_front_l_rot": 50.0, "paw_front_r_rot": 50.0}
  slam = {"root": 0.5, "hips_pos": (0.0, 0.3, -0.2), "hips_rot": (10, 0, 0), "spine_rot": (6, 0, 0), "chest_rot": (8, 0, 0),
          "head_rot": (-12, 0, 0), "jaw": 30.0, "tail_base": (0.0, 0.0), "paw_front_l_rot": 0.0, "paw_front_r_rot": 0.0}
  slam.update(planted(1.0, "front_l", "front_r"))
  poses = [
    (0, dict(REST)),
    (8, {"hips_pos": (0.0, -0.1, -0.22), "head_rot": (16, 0, 0), "jaw": SHUT}),
    (10, dict(planted(0.0, "front_l", "front_r"), paw_front_l_rot=0.0, paw_front_r_rot=0.0)),
    (22, reared),
    (26, dict(reared, root=0.0, hips_rot=(-43, 0, 0), head_rot=(-36, 0, 0), paw_front_l=(0.15, -0.45, 2.05), paw_front_r=(-0.15, -0.5, 2.0))),
    (29, slam),
    (32, dict(slam, hips_pos=(0.0, 0.3, -0.32), chest_rot=(12, 0, 0))),
    (38, planted(0.0, "hind_l", "hind_r")),
    (42, {"paw_hind_l": (0.0, 0.3, 0.3)}),
    (46, dict(planted(0.5, "hind_l"), paw_hind_r=(0.0, 0.3, 0.3))),
    (50, dict(planted(0.5, "hind_r"), **planted(1.0, "front_l", "front_r"))),
  ]
  for i, frame in enumerate(range(36, 50, 4)):
    poses.append((frame, {"head_rot": (-8, 6 * (1 if i % 2 else -1), 0), "jaw": 30.0, "hips_pos": (0.0, 0.25, -0.26)}))
  poses += [
    (54, {"head_rot": (12, 0, 0), "jaw": -10.0, "chest_rot": (6, 0, 0), "hips_pos": (0.0, 0.1, -0.14), "paw_front_l": (0.0, 0.8, 0.2),
          **planted(1.0, "front_r")}),
    (58, dict(planted(0.5, "front_l"), paw_front_r=(0.0, 0.8, 0.2))),
    (62, planted(0.5, "front_r")),
    (74, rest_at(0.5)),
  ]
  return BeastClip("attack_quake", 74, timeline(*poses))


def death_clip():
  """Struck down: staggers, throws his head back in a last howl, the forelegs buckle and he drops onto
  his chest, then rolls onto his side. Two last breaths and the head and the tail go still. Holds its
  last frame. The root stays put, as death plays without root motion."""
  hit = {"hips_pos": (0.0, -0.1, -0.1), "chest_rot": (-6, 10, 6), "head_rot": (-20, 25, 15), "jaw": 20.0, "tail": (-2.0, -8.0)}
  howl = {"hips_pos": (0.0, -0.3, -0.2), "hips_rot": (-8, 0, 0), "chest_rot": (-12, 0, 0), "head_rot": (-50, 0, 0), "jaw": 26.0, "tail": (-3.0, 0.0)}
  chest_down = {"hips_pos": (0.0, -0.1, -0.35), "hips_rot": (16, 0, 0), "spine_rot": (10, 0, 0), "chest_rot": (14, 0, 0),
                "head_rot": (-30, 0, 10), "jaw": 20.0, "tail": (-4.0, 0.0), "paw_front_l": (0.15, 0.3, 0.0), "paw_front_r": (-0.15, 0.25, 0.0)}
  side = {"roll": -88.0, "pivot": 0.62, "feet_free": 1.0, "hips_pos": (0.0, 0.0, -0.08), "hips_rot": (0, 0, 0), "spine_rot": (0, 0, 0),
          "chest_rot": (0, 0, 0), "head_rot": (12, 0, 14), "jaw": 22.0, "tail": (-2.0, 3.0), "tail_base": (-20.0, 0.0),
          "paw_front_l": (-0.3, 0.2, 0.0), "paw_front_r": (0.6, 0.1, 0.0), "paw_hind_l": (-0.3, 0.1, 0.0), "paw_hind_r": (0.6, -0.05, 0.0),
          "paw_front_l_rot": 20.0, "paw_front_r_rot": 10.0, "paw_hind_l_rot": 15.0, "paw_hind_r_rot": 5.0}
  return BeastClip("death", 120, timeline(
    (0, dict(REST)),
    (5, hit),
    (16, howl),
    (24, dict(howl, head_rot=(-56, 3, 0), jaw=28.0)),
    (32, {"head_rot": (10, 0, 0), "hips_pos": (0.0, -0.05, -0.2), "hips_rot": (6, 0, 0), "chest_rot": (6, 0, 0), "jaw": 10.0, **planted(0.0)}),
    (40, chest_down),
    (44, dict(chest_down, hips_pos=(0.0, -0.1, -0.42), chest_rot=(16, 0, 0), head_rot=(-26, 0, 12))),
    (52, {"roll": -20.0, "pivot": 0.62, "feet_free": 0.4, "hips_pos": (0.0, -0.05, -0.4), "hips_rot": (8, 0, 0)}),
    (62, side),
    (66, dict(side, roll=-92.0)),
    (72, dict(side, chest_rot=(-4, 0, 0), jaw=28.0)),
    (80, dict(side, chest_rot=(2, 0, 0))),
    (88, dict(side, chest_rot=(-3, 0, 0), jaw=26.0, head_rot=(16, 0, 18))),
    (100, dict(side, head_rot=(20, 0, 22), jaw=30.0, tail=(-2.5, 1.0))),
    (120, dict(side, head_rot=(22, 0, 24), jaw=30.0, tail=(-2.5, 1.0))),
  ))


CLIPS = [
  idle_clip(),
  walk_clip(),
  run_clip(),
  circle_clip("strafe_left-loop", (1.0, 0.0)),
  circle_clip("strafe_right-loop", (-1.0, 0.0)),
  circle_clip("walk_back-loop", (0.0, -1.0), BACK_SPEED, BACK_FRAMES),
  howl_clip(),
  enrage_clip(),
  attack_maul_clip(),
  attack_crunch_clip(),
  attack_whirl_clip(),
  attack_crash_clip(),
  attack_frenzy_clip(),
  attack_quake_clip(),
  death_clip(),
]

run("armature_guino", CLIPS, GLB_PATH)
