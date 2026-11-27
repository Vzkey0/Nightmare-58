"""Rigs and animates El Padre and El Bachaquero with lightweight idle + talk loops.

Loads art/characters/priest.blend and art/characters/bachaquero.blend, adds a clean
upper-body + arm armature with smooth geometric weights (feet and lower body stay planted
at z=0), bakes looping 'idle' and 'talk' actions, and exports priest.glb / bachaquero.glb.

  blender --background --python art/characters/animate_npcs.py
"""

import math
import os

import bpy
from mathutils import Euler, Quaternion, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
GLB_DIR = os.path.abspath(os.path.join(HERE, "..", "..", "game", "models", "characters"))
FPS = 30


def smoothstep(edge0, edge1, x):
  if edge1 <= edge0:
    return 1.0 if x >= edge1 else 0.0
  t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
  return t * t * (3.0 - 2.0 * t)


def seg_proj(p, a, b):
  ab = b - a
  ab_len2 = ab.length_squared
  if ab_len2 < 1e-8:
    return 0.0, (p - a).length
  t = max(0.0, min(1.0, (p - a).dot(ab) / ab_len2))
  return t, (p - (a + ab * t)).length


def world_rot_to_bone_local(pbone, pitch_deg=0.0, yaw_deg=0.0, roll_deg=0.0):
  """Converts armature-space (+pitch forward/-Y nod, +yaw turn left, +roll lean left) to bone-local quat."""
  # Character faces -Y, +X is character's left, +Z is up.
  # Positive X rotation tilts +Z toward -Y (nod/lean forward).
  # Positive Z rotation turns -Y toward +X (turn left).
  # Positive Y rotation tilts +Z toward +X (lean left).
  q_arm = (
    Quaternion((0.0, 0.0, 1.0), math.radians(yaw_deg))
    @ Quaternion((1.0, 0.0, 0.0), math.radians(pitch_deg))
    @ Quaternion((0.0, 1.0, 0.0), math.radians(roll_deg))
  )
  rest_q = pbone.bone.matrix_local.to_quaternion()
  return rest_q.inverted() @ q_arm @ rest_q


def create_armature(name, spec):
  arm_data = bpy.data.armatures.new(f"armature_{name}")
  arm_obj = bpy.data.objects.new(f"armature_{name}", arm_data)
  bpy.context.collection.objects.link(arm_obj)
  bpy.context.view_layer.objects.active = arm_obj
  bpy.ops.object.mode_set(mode="EDIT")

  eb = arm_data.edit_bones
  bones = {}

  def add_bone(bname, head, tail, parent=None):
    b = eb.new(bname)
    b.head = Vector(head)
    b.tail = Vector(tail)
    if parent is not None:
      b.parent = bones[parent]
    bones[bname] = b
    return b

  add_bone("root", (0.0, 0.0, 0.0), spec["spine_base"])
  add_bone("spine", spec["spine_base"], spec["chest_base"], "root")
  add_bone("chest", spec["chest_base"], spec["neck_base"], "spine")
  add_bone("head", spec["neck_base"], spec["head_top"], "chest")

  for side, s in (("l", 1.0), ("r", -1.0)):
    sh = Vector((s * spec["shoulder"].x, spec["shoulder"].y, spec["shoulder"].z))
    el = Vector((s * spec["elbow"].x, spec["elbow"].y, spec["elbow"].z))
    wr = Vector((s * spec["wrist"].x, spec["wrist"].y, spec["wrist"].z))
    hand_tip = wr + (wr - el).normalized() * 0.14
    add_bone(f"upper_arm_{side}", sh, el, "chest")
    add_bone(f"forearm_{side}", el, hand_tip, f"upper_arm_{side}")

  bpy.ops.object.mode_set(mode="OBJECT")
  return arm_obj


def assign_weights(mesh_obj, arm_obj, spec):
  mesh_obj.vertex_groups.clear()
  groups = {}
  for b in arm_obj.data.bones:
    groups[b.name] = mesh_obj.vertex_groups.new(name=b.name)

  z_spine0, z_spine1 = spec["z_spine"]
  z_chest0, z_chest1 = spec["z_chest"]
  z_head0, z_head1 = spec["z_head"]
  arm_x0, arm_x1 = spec["arm_x"]
  arm_y_max = spec["arm_y_max"]
  arm_z_min = spec["arm_z_min"]
  arm_radius = spec["arm_radius"]

  sh_l = spec["shoulder"]
  el_l = spec["elbow"]
  wr_l = spec["wrist"]
  tip_l = wr_l + (wr_l - el_l).normalized() * 0.16

  sh_r = Vector((-sh_l.x, sh_l.y, sh_l.z))
  el_r = Vector((-el_l.x, el_l.y, el_l.z))
  wr_r = Vector((-wr_l.x, wr_l.y, wr_l.z))
  tip_r = Vector((-tip_l.x, tip_l.y, tip_l.z))

  for v in mesh_obj.data.vertices:
    p = v.co
    weights = {}

    # Check if vertex belongs to left (+X) or right (-X) arm
    arm_w = 0.0
    arm_side = None
    elbow_t = 0.0
    if p.z >= arm_z_min and p.y <= arm_y_max and abs(p.x) > arm_x0:
      if p.x > 0.0:
        side = "l"
        sh, el, tip = sh_l, el_l, tip_l
      else:
        side = "r"
        sh, el, tip = sh_r, el_r, tip_r
      t_up, d_up = seg_proj(p, sh, el)
      t_lo, d_lo = seg_proj(p, el, tip)
      d_arm = min(d_up, d_lo)
      if d_arm < arm_radius:
        x_factor = smoothstep(arm_x0, arm_x1, abs(p.x))
        r_factor = 1.0 - smoothstep(arm_radius * 0.72, arm_radius, d_arm)
        arm_w = x_factor * r_factor
        arm_side = side
        # Smooth elbow blend
        if d_lo < d_up:
          elbow_t = smoothstep(0.0, 0.22, t_lo)
        else:
          elbow_t = 0.0 if t_up < 0.82 else smoothstep(0.82, 1.0, t_up) * 0.45

    torso_w = 1.0 - arm_w
    if arm_w > 1e-4 and arm_side is not None:
      w_fore = arm_w * elbow_t
      w_up = arm_w * (1.0 - elbow_t)
      if w_up > 1e-4:
        weights[f"upper_arm_{arm_side}"] = w_up
      if w_fore > 1e-4:
        weights[f"forearm_{arm_side}"] = w_fore

    if torso_w > 1e-4:
      # Vertical blend along spine -> chest -> head
      s_root_to_spine = smoothstep(z_spine0, z_spine1, p.z)
      s_spine_to_chest = smoothstep(z_chest0, z_chest1, p.z)
      s_chest_to_head = smoothstep(z_head0, z_head1, p.z)

      w_root = (1.0 - s_root_to_spine)
      w_spine = s_root_to_spine * (1.0 - s_spine_to_chest)
      w_chest = s_spine_to_chest * (1.0 - s_chest_to_head)
      w_head = s_chest_to_head

      for bname, bw in (("root", w_root), ("spine", w_spine), ("chest", w_chest), ("head", w_head)):
        if bw * torso_w > 1e-4:
          weights[bname] = weights.get(bname, 0.0) + bw * torso_w

    total = sum(weights.values())
    if total > 1e-6:
      for bname, bw in weights.items():
        groups[bname].add([v.index], bw / total, "REPLACE")
    else:
      groups["root"].add([v.index], 1.0, "REPLACE")

  mesh_obj.parent = arm_obj
  mod = mesh_obj.modifiers.new(name="Armature", type="ARMATURE")
  mod.object = arm_obj


def bake_action(arm_obj, clip_name, frames, pose_fn):
  act = bpy.data.actions.new(name=clip_name)
  act.use_fake_user = True
  arm_obj.animation_data.action = act

  for pbone in arm_obj.pose.bones:
    pbone.rotation_mode = "QUATERNION"

  for f in range(frames + 1):
    # u in [0, 1], periodic at 0 and 1 for seamless looping
    u = f / float(frames)
    pose = pose_fn(u)
    bpy.context.scene.frame_set(f)
    for bname, pbone in arm_obj.pose.bones.items():
      pitch, yaw, roll = pose.get(bname, (0.0, 0.0, 0.0))
      pbone.rotation_quaternion = world_rot_to_bone_local(pbone, pitch, yaw, roll)
      pbone.keyframe_insert(data_path="rotation_quaternion", frame=f)

  return act


# --- Priest poses (calm elderly presence, hands gathered in front, gentle gestures) ---------
# Note: for downward-pointing arm bones (-Z), -pitch swings the arm FORWARD (-Y),
# +roll brings the left arm (+X) INWARD/DOWN, and -roll brings the right arm (-X) INWARD/DOWN.
def priest_idle(u):
  s1 = math.sin(math.tau * u)
  c1 = math.cos(math.tau * u)
  s2 = math.sin(math.tau * 2.0 * u)
  return {
    "spine": (1.2 * s1, 0.8 * c1, 0.4 * s1),
    "chest": (1.6 * s1, 0.6 * c1, 0.3 * s2),
    "head": (2.2 * s1 + 1.0, 3.2 * c1, 1.2 * s1),
    # Bring A-pose arms gently down and forward into a calm resting stance
    "upper_arm_l": (-10.0 - 1.2 * s1, 8.0, 24.0),
    "forearm_l": (-34.0 - 2.0 * s1, 22.0, 10.0),
    "upper_arm_r": (-10.0 - 1.2 * s1, -8.0, -24.0),
    "forearm_r": (-34.0 - 2.0 * s1, -22.0, -10.0),
  }


def priest_talk(u):
  s1 = math.sin(math.tau * u)
  s2 = math.sin(math.tau * 2.0 * u)
  c2 = math.cos(math.tau * 2.0 * u)
  s3 = math.sin(math.tau * 3.0 * u)
  return {
    "spine": (2.5 + 1.8 * s1, 1.5 * s1, 0.6 * c2),
    "chest": (3.0 + 2.2 * s2, 2.5 * s1, 0.8 * s1),
    "head": (4.0 * s2 + 1.5 * s3, 6.5 * s1, 2.2 * c2),
    # Left hand stays steadier near waist/chest; right hand lifts gently in measured gestures
    "upper_arm_l": (-12.0 - 2.0 * s1, 8.0, 22.0),
    "forearm_l": (-38.0 - 4.0 * s1, 20.0, 8.0),
    "upper_arm_r": (-22.0 - 8.0 * s2, -6.0 + 6.0 * s1, -18.0 + 5.0 * s2),
    "forearm_r": (-46.0 - 14.0 * s2 - 4.0 * s3, -12.0 + 10.0 * c2, -6.0),
  }


# --- Bachaquero poses (street-smart stance behind counter, expressive vendor hands) ---------
def bachaquero_idle(u):
  s1 = math.sin(math.tau * u)
  c1 = math.cos(math.tau * u)
  s2 = math.sin(math.tau * 2.0 * u)
  return {
    "spine": (1.0 * s1, 1.8 * c1, 1.2 * s1),
    "chest": (1.4 * s1, 1.5 * c1, 0.8 * s2),
    "head": (1.8 * s2, 7.5 * s1, 1.8 * c1),
    # Relaxed arms clear of beer belly and vest pockets
    "upper_arm_l": (-8.0 - 1.5 * s1, 4.0, 8.0),
    "forearm_l": (-22.0 - 2.5 * s1, 8.0, 4.0),
    "upper_arm_r": (-8.0 - 1.5 * c1, -4.0, -8.0),
    "forearm_r": (-22.0 - 2.5 * c1, -8.0, -4.0),
  }


def bachaquero_talk(u):
  s1 = math.sin(math.tau * u)
  c1 = math.cos(math.tau * u)
  s2 = math.sin(math.tau * 2.0 * u)
  c2 = math.cos(math.tau * 2.0 * u)
  s3 = math.sin(math.tau * 3.0 * u)
  return {
    "spine": (3.2 + 2.0 * s2, 3.0 * s1, 1.4 * c1),
    "chest": (3.8 + 2.4 * s2, 4.0 * s1, 1.2 * s2),
    "head": (4.5 * s2 + 2.0 * s3, 9.0 * s1, 3.5 * c2),
    # Alternating lively vendor hand gestures
    "upper_arm_l": (-22.0 - 9.0 * s2, 6.0 - 5.0 * c1, 6.0 - 4.0 * s2),
    "forearm_l": (-46.0 - 16.0 * s2, 12.0 - 10.0 * s1, 6.0),
    "upper_arm_r": (-22.0 + 9.0 * s2, -6.0 + 5.0 * c1, -6.0 + 4.0 * s2),
    "forearm_r": (-46.0 + 16.0 * s2 - 5.0 * s3, -12.0 + 10.0 * s1, -6.0),
  }


SPECS = {
  "priest": {
    "blend": os.path.join(HERE, "priest.blend"),
    "glb": os.path.join(GLB_DIR, "priest.glb"),
    "mesh_name": "priest",
    "spine_base": (0.0, 0.0, 0.86),
    "chest_base": (0.0, -0.008, 1.12),
    "neck_base": (0.0, -0.048, 1.40),
    "head_top": (0.0, -0.086, 1.68),
    "shoulder": Vector((0.152, -0.036, 1.320)),
    "elbow": Vector((0.312, -0.018, 1.100)),
    "wrist": Vector((0.456, -0.044, 0.915)),
    "z_spine": (0.82, 1.06),
    "z_chest": (1.06, 1.26),
    "z_head": (1.39, 1.45),
    "arm_x": (0.165, 0.215),
    "arm_y_max": 0.14,
    "arm_z_min": 0.72,
    "arm_radius": 0.115,
    "clips": [
      ("idle", 108, priest_idle),
      ("talk", 96, priest_talk),
    ],
  },
  "bachaquero": {
    "blend": os.path.join(HERE, "bachaquero.blend"),
    "glb": os.path.join(GLB_DIR, "bachaquero.glb"),
    "mesh_name": "bachaquero",
    "spine_base": (0.0, 0.0, 0.88),
    "chest_base": (0.0, 0.002, 1.14),
    "neck_base": (0.0, 0.0, 1.42),
    "head_top": (0.0, -0.014, 1.72),
    "shoulder": Vector((0.228, 0.006, 1.330)),
    "elbow": Vector((0.320, 0.026, 1.065)),
    "wrist": Vector((0.296, -0.044, 0.848)),
    "z_spine": (0.86, 1.08),
    "z_chest": (1.08, 1.28),
    "z_head": (1.41, 1.47),
    "arm_x": (0.215, 0.265),
    "arm_y_max": 0.130,  # Strictly excludes backpack and side pockets (y >= 0.15)
    "arm_z_min": 0.66,
    "arm_radius": 0.115,
    "clips": [
      ("idle", 96, bachaquero_idle),
      ("talk", 84, bachaquero_talk),
    ],
  },
}


def process_npc(name, spec):
  bpy.ops.wm.open_mainfile(filepath=spec["blend"])
  bpy.context.scene.render.fps = FPS

  mesh_obj = bpy.data.objects.get(spec["mesh_name"])
  if mesh_obj is None:
    raise RuntimeError(f"Mesh '{spec['mesh_name']}' not found in {spec['blend']}")

  # Remove any previous armature/actions if re-running
  for obj in list(bpy.data.objects):
    if obj.type == "ARMATURE":
      bpy.data.objects.remove(obj, do_unlink=True)
  for act in list(bpy.data.actions):
    bpy.data.actions.remove(act)
  for mod in list(mesh_obj.modifiers):
    if mod.type == "ARMATURE":
      mesh_obj.modifiers.remove(mod)
  mesh_obj.parent = None

  arm_obj = create_armature(name, spec)
  assign_weights(mesh_obj, arm_obj, spec)
  arm_obj.animation_data_create()

  for clip_name, frames, pose_fn in spec["clips"]:
    bake_action(arm_obj, clip_name, frames, pose_fn)

  # Reset pose before export
  arm_obj.animation_data.action = None
  for pbone in arm_obj.pose.bones:
    pbone.matrix_basis.identity()

  for other in bpy.data.objects:
    other.hide_set(other not in (arm_obj, mesh_obj))

  os.makedirs(os.path.dirname(spec["glb"]), exist_ok=True)
  bpy.ops.export_scene.gltf(
    filepath=spec["glb"],
    export_format="GLB",
    use_visible=True,
    export_animations=True,
    export_animation_mode="ACTIONS",
    export_force_sampling=True,
    export_frame_step=1,
  )

  for other in bpy.data.objects:
    other.hide_set(False)

  print(f"Animated and exported {spec['glb']} ({len(spec['clips'])} clips)")


def main():
  for name, spec in SPECS.items():
    process_npc(name, spec)


if __name__ == "__main__":
  main()
