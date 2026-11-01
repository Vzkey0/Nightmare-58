@tool
extends EditorScenePostImport

# Faces the player can never see were removed from the mesh, so shells must cast shadows
# from both sides. The backdrop is too far away to shadow the street.
func _post_import(scene: Node) -> Object:
	for mesh_instance: MeshInstance3D in scene.find_children("*", "MeshInstance3D", true, false):
		if mesh_instance.name.begins_with("backdrop"):
			mesh_instance.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		else:
			mesh_instance.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_DOUBLE_SIDED
		for surface in mesh_instance.mesh.get_surface_count():
			var material := mesh_instance.mesh.surface_get_material(surface) as BaseMaterial3D
			if material:
				material.vertex_color_use_as_albedo = true
				# Blender exports these colors already linear; another conversion darkens them.
				material.vertex_color_is_srgb = false
	return scene
