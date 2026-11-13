"""Pose solver and gait helpers shared by the four-legged enemies' animations.

It builds on the rig solver of animate_protagonist.py. A pose sets the root, the hips, the spine,
an absolute head that stays on its target while the body moves, the jaw, the tail and the four
paws; inverse kinematics solves each leg so planted paws really stay planted.

Paws are keyed as (x, forward, lift) away from where they rest, and forward counts the root,
as with the protagonist's feet: an attack that moves the root moves the paws itself.
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Quaternion

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from animate_protagonist import AUTHOR_FPS, BAKE_FPS, UP, Clip, Rig, aim_delta, at, bake, interpolate, rot, solve_two_bones, timeline, wave

LEGS = ("front_l", "front_r", "hind_l", "hind_r")
TAIL_LAG = 2.5 # Frames each tail bone trails the one before it, so the tail whips.
# How far the top of a leg may slide toward a paw out of reach: the shoulder blade, and a little the hip.
GLIDE = {"front": 0.09, "hind": 0.04}


class BeastRig(Rig):
  def __init__(self, armature):
    super().__init__(armature)
    self.tail_bones = sorted((name for name in self.rest if name.startswith("tail_")), key=lambda name: int(name[5:]))
    self.poles = {}
    for leg in LEGS:
      top, joint, ankle = self.head["upper_" + leg], self.head["lower_" + leg], self.head["foot_" + leg]
      line = (ankle - top).normalized()
      offset = joint - top
      self.poles[leg] = (offset - offset.project(line)).normalized()
    # A leg already straight at rest must not slide before it stretches further.
    self.span = {leg: (self.head["foot_" + leg] - self.head["upper_" + leg]).length for leg in LEGS}

  def solve(self, pose):
    self.world.clear()
    self.local.clear()
    ground = at(0, pose["root"], 0)
    self.place("root", Quaternion(), ground)

    # A roll or a spin turns the body around a point above the root; feet_free says whether the paws go along.
    turn = rot(0, pose.get("spin", 0.0), pose.get("roll", 0.0))
    pivot = ground + UP * pose.get("pivot", 0.3)
    lift = UP * pose.get("lift", 0.0)
    turned = lambda point: pivot + turn @ (point - pivot) + lift
    free = pose.get("feet_free", 0.0)
    paw_turn = Quaternion().slerp(turn, free)

    hips_at = turned(ground + self.head["hips"] + at(*pose["hips_pos"]))
    hips = turn @ rot(*pose["hips_rot"])
    spine = hips @ rot(*pose["spine_rot"])
    chest = spine @ rot(*pose["chest_rot"])
    head = turn @ rot(*pose["head_rot"])
    self.place("hips", hips, hips_at)
    self.place("spine", spine)
    self.place("chest", chest)
    self.place("neck", chest.slerp(head, 0.5))
    self.place("head", head)
    self.place("jaw", head @ rot(pose["jaw"]))

    # tail_base turns the root of the tail alone, so it can stay on the ground while the body rears.
    bend = hips @ rot(*pose.get("tail_base", (0.0, 0.0)))
    for name, (pitch, yaw) in zip(self.tail_bones, pose["tail_chain"]):
      bend = bend @ rot(pitch, yaw)
      self.place(name, bend)

    for leg in LEGS:
      planted = self.tail["foot_" + leg] + at(*pose["paw_" + leg])
      ball = planted.lerp(turned(planted), free)
      self.leg(leg, ball, pose["paw_" + leg + "_rot"], chest if leg.startswith("front") else hips, paw_turn)

  def leg(self, leg, ball, pitch, parent, turn):
    foot = "foot_" + leg
    delta = turn @ rot(pitch)
    # The foot turns around the ball, so a paw that pushes off lifts the wrist or the hock.
    ankle = ball + delta @ (self.head[foot] - self.tail[foot])
    upper, lower = "upper_" + leg, "lower_" + leg
    origin = self.origin(upper)
    reach = self.length(upper) + self.length(lower)
    offset = ankle - origin
    slack = max(0.9 * reach, self.span[leg])
    origin = origin + offset.normalized() * min(max(offset.length - slack, 0.0), GLIDE[leg[:-2]])
    pole = parent @ self.poles[leg]
    joint, end = solve_two_bones(origin, ankle, self.length(upper), self.length(lower), pole)
    self.max_stretch = max(self.max_stretch, (ankle - end).length)
    self.place(upper, aim_delta(self.direction(upper), self.poles[leg], joint - origin, pole), origin)
    self.place(lower, aim_delta(self.direction(lower), self.poles[leg], end - joint, pole))
    self.place(foot, delta)
    grounded = 1.0 - min(max(ball.z - self.tail[foot].z, 0.0) / 0.03, 1.0)
    self.place("toes_" + leg, turn @ rot(pitch * (1.0 - grounded)))


class BeastClip(Clip):
  """Samples the tail once per bone, each a little later, so it trails the body."""

  def sample(self, frame):
    pose = super().sample(frame)
    channel = self.channels["tail"]
    period = self.frames if self.loop else 0
    chain = []
    for i in range(12):
      when = frame - i * TAIL_LAG
      chain.append(channel(when / self.frames % 1.0) if callable(channel) else interpolate(channel, when, period))
    pose["tail_chain"] = chain
    return pose


def stride(offset, speed, frames, stance, lift, curl, move=(0.0, 1.0), home=(0.0, 0.0)):
  """A paw that pushes back along move at exactly speed while planted, then swings forward.
  Returns the paw position and its pitch: it peels off the ground and curls in the air."""
  half = speed * frames / AUTHOR_FPS * stance * 0.5

  def position(phase):
    phase = (phase + offset) % 1.0
    if phase < stance:
      amount = half - 2.0 * half * phase / stance
      height = 0.0
    else:
      swing = (phase - stance) / (1.0 - stance)
      amount = -half + 2.0 * half * swing * swing * (3.0 - 2.0 * swing)
      height = lift * math.sin(math.pi * swing) ** 1.2
    return (home[0] + move[0] * amount, home[1] + move[1] * amount, height)

  def pitch(phase):
    phase = (phase + offset) % 1.0
    if phase < stance:
      return max(phase / stance - 0.7, 0.0) / 0.3 * curl * 0.4
    swing = (phase - stance) / (1.0 - stance)
    return curl * (0.4 + 0.6 * math.sin(math.pi * min(swing * 1.4, 1.0))) * (1.0 - swing) ** 0.5

  return position, pitch


def gait(channels, paws):
  """Adds the four paws of a gait, given as leg: stride(...)."""
  for leg, (position, pitch) in paws.items():
    channels["paw_" + leg] = position
    channels["paw_" + leg + "_rot"] = pitch
  return channels


def planted(forward, *legs):
  """Paw keys flat on the ground, the given distance ahead of where they rest; all four by default."""
  return {f"paw_{leg}": (0.0, forward, 0.0) for leg in legs or LEGS}


def export(armature, path):
  armature.animation_data.action = None
  for bone in armature.pose.bones:
    bone.matrix_basis = Matrix.Identity(4)
  os.makedirs(os.path.dirname(path), exist_ok=True)
  bpy.ops.export_scene.gltf(
    filepath=path,
    export_format="GLB",
    use_visible=True,
    export_animations=True,
    export_animation_mode="ACTIONS",
    export_force_sampling=True,
    export_frame_step=1,
  )


def run(armature_name, clips, path):
  bpy.context.scene.render.fps = BAKE_FPS
  armature = bpy.data.objects[armature_name]
  armature.animation_data_create()
  for bone in armature.pose.bones:
    bone.rotation_mode = "QUATERNION"
  rig = BeastRig(armature)
  moved = ("root", "hips") + tuple("upper_" + leg for leg in LEGS)
  for clip in clips:
    bake(armature, rig, clip, moved)
  export(armature, path)
  bpy.ops.wm.save_mainfile()
