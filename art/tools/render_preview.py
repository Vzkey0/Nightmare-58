# Single-image 3x2 studio contact sheet renderer for Nightmare 58 characters/props.
# Outputs ONE composite PNG (<prefix>_sheet.png) with:
#   Top row:    Front (-Y) | 3/4 Front | Side Profile
#   Bottom row: Back (+Y)  | 3/4 Bust  | Front Face
# Usage:
#   blender --background model.blend --python art/tools/render_preview.py -- <out_dir> <prefix> [samples] [--keep]
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

argv = sys.argv
args = argv[argv.index("--") + 1:] if "--" in argv else []
keep_individual = "--keep" in args
pos_args = [a for a in args if not a.startswith("--")]
out_dir = pos_args[0] if len(pos_args) > 0 else "."
prefix = pos_args[1] if len(pos_args) > 1 else "preview"
samples = int(pos_args[2]) if len(pos_args) > 2 else 14
os.makedirs(out_dir, exist_ok=True)

scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = samples
scene.cycles.use_denoising = True
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
scene.view_settings.exposure = -0.15

for obj in list(bpy.data.objects):
  if obj.type in ("CAMERA", "LIGHT"):
    bpy.data.objects.remove(obj, do_unlink=True)

world = scene.world or bpy.data.worlds.new("PreviewWorld")
scene.world = world
bg = world.node_tree.nodes.get("Background")
if bg:
  bg.inputs["Color"].default_value = (0.14, 0.16, 0.21, 1.0)
  bg.inputs["Strength"].default_value = 0.55

meshes = [o for o in bpy.data.objects if o.type == "MESH" and not o.hide_render]
total_tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in meshes)
pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
if pts:
  min_v = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
  max_v = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
else:
  min_v, max_v = Vector((-0.5, -0.5, 0.0)), Vector((0.5, 0.5, 1.72))

center = (min_v + max_v) * 0.5
height = max(0.5, max_v.z - min_v.z)
print(f"PREVIEW AUDIT: meshes={len(meshes)} total_tris={total_tris} height={height:.3f}m min_z={min_v.z:.4f}")

# Grounding pedestal
bpy.ops.mesh.primitive_cylinder_add(vertices=36, radius=1.1, depth=0.02, location=(center.x, center.y, min_v.z - 0.01))
floor = bpy.context.active_object
floor.name = "_preview_floor"
fmat = bpy.data.materials.new("_preview_floor_mat")
fmat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.19, 0.21, 0.25, 1.0)
fmat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.92
floor.data.materials.append(fmat)


def add_light(name, loc, target, energy, color=(1, 1, 1), size=1.8):
  ldata = bpy.data.lights.new(name, type="AREA")
  ldata.energy = energy
  ldata.color = color
  ldata.size = size
  lobj = bpy.data.objects.new(name, ldata)
  scene.collection.objects.link(lobj)
  lobj.location = Vector(loc)
  lobj.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()


add_light("Key", (center.x - 1.9, center.y - 2.6, center.z + 1.4), center, 175, (1.0, 0.94, 0.86), size=1.5)
add_light("Fill", (center.x + 2.3, center.y - 1.9, center.z + 0.5), center, 95, (0.70, 0.82, 1.0), size=2.4)
add_light("Rim", (center.x + 1.1, center.y + 2.6, center.z + 1.5), center, 210, (0.94, 0.96, 1.0), size=1.4)
add_light("UnderFill", (center.x, center.y - 2.0, min_v.z + 0.35), (center.x, center.y, center.z - 0.2), 30, (0.85, 0.88, 0.95), size=2.0)

cam_data = bpy.data.cameras.new("PreviewCam")
cam_obj = bpy.data.objects.new("PreviewCam", cam_data)
scene.collection.objects.link(cam_obj)
scene.camera = cam_obj

TILE_W, TILE_H = 520, 600


def shoot(tag, cam_loc, target, lens=55):
  scene.render.resolution_x, scene.render.resolution_y = TILE_W, TILE_H
  cam_data.lens = lens
  cam_obj.location = Vector(cam_loc)
  cam_obj.rotation_euler = (Vector(target) - Vector(cam_loc)).to_track_quat("-Z", "Y").to_euler()
  path = os.path.join(out_dir, f"{prefix}_{tag}.png")
  scene.render.filepath = path
  bpy.ops.render.render(write_still=True)
  return path


d = height * 1.95
a = math.radians(36)
head_z = max_v.z - height * 0.175
face_z = max_v.z - height * 0.095

paths = [
  shoot("front", (center.x, center.y - d, center.z + 0.04), (center.x, center.y, center.z)),
  shoot("34", (center.x - d * math.sin(a), center.y - d * math.cos(a), center.z + 0.08), (center.x, center.y, center.z)),
  shoot("side", (center.x - d, center.y, center.z + 0.04), (center.x, center.y, center.z)),
  shoot("back", (center.x, center.y + d, center.z + 0.06), (center.x, center.y, center.z)),
  shoot("bust", (center.x - 0.44, center.y - 1.24, head_z + 0.09), (center.x, center.y - 0.04, head_z + 0.01), lens=54),
  shoot("face", (center.x, center.y - 0.92, face_z + 0.01), (center.x, center.y - 0.05, face_z - 0.01), lens=65),
]


def load_rgba(path):
  img = bpy.data.images.load(path)
  w, h = img.size
  arr = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
  bpy.data.images.remove(img)
  return arr


imgs = [load_rgba(p) for p in paths]
top = np.concatenate(imgs[:3], axis=1)
bot = np.concatenate(imgs[3:], axis=1)
# Blender image pixels are bottom-up, so bot goes first to appear on the bottom row.
sheet = np.concatenate([bot, top], axis=0)
sh, sw, _ = sheet.shape
out_img = bpy.data.images.new("_sheet", width=sw, height=sh, alpha=True)
out_img.pixels.foreach_set(sheet.ravel())
sheet_path = os.path.join(out_dir, f"{prefix}_sheet.png")
out_img.filepath_raw = sheet_path
out_img.file_format = "PNG"
out_img.save()

if not keep_individual:
  for p in paths:
    if os.path.exists(p):
      os.remove(p)

print("SAVED SHEET:", sheet_path)
