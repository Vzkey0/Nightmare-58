# Applies the project's Blender setup. Run once per machine:
#   blender --background --python art/setup_blender.py
import bpy

prefs = bpy.context.preferences
prefs.filepaths.save_version = 3
prefs.filepaths.use_auto_save_temporary_files = True
prefs.filepaths.auto_save_time = 5
prefs.edit.undo_steps = 64

cycles = prefs.addons["cycles"].preferences
available = [device_type[0] for device_type in cycles.get_device_types(bpy.context)]
for backend in ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL"):
  if backend in available:
    cycles.compute_device_type = backend
    cycles.get_devices()
    for device in cycles.devices:
      device.use = device.type == backend
    break

bpy.ops.wm.save_userpref()

for obj in list(bpy.data.objects):
  bpy.data.objects.remove(obj)

scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0
# AgX desaturates flat colors, so a model would look different in Godot.
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"

for screen in bpy.data.screens:
  for area in screen.areas:
    if area.type == "VIEW_3D":
      for space in area.spaces:
        if space.type == "VIEW_3D":
          space.overlay.show_stats = True
          space.shading.show_shadows = True
          space.shading.show_cavity = True

bpy.ops.wm.save_homefile()
