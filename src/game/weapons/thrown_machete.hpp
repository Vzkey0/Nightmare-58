#pragma once

#include <godot_cpp/classes/mesh_instance3d.hpp>
#include <godot_cpp/classes/node3d.hpp>
#include <godot_cpp/classes/shape_cast3d.hpp>

#include <core/player/thrown_weapon.hpp>

class PlayerController;

// The machete in the air. It copies the mesh and the hitbox of the one in the hand, so it looks
// the same and hits with the whole weapon on its way out and on its way back.
class ThrownMachete : public godot::Node3D
{
  GDCLASS(ThrownMachete, godot::Node3D)

protected:
  static void _bind_methods() {}

public:
  // hand is the weapon bone: its frame is the one the hitbox and the mesh's rest are built in.
  void launch(PlayerController * thrower, const godot::MeshInstance3D * hand_mesh, const godot::Transform3D & mesh_from_bone,
              const godot::ShapeCast3D * hand_hitbox, const godot::Node3D * hand, const godot::Vector3 & direction);
  void _physics_process(double delta) override;

private:
  void hit_targets();
  bool blocked(const godot::Vector3 & from, const godot::Vector3 & to) const;

  ThrownWeapon flight;
  PlayerController * owner = nullptr;
  const godot::Node3D * hand = nullptr;
  godot::Node3D * spinner = nullptr;
  godot::ShapeCast3D * hitbox = nullptr;
  godot::Vector3 heading;
  float spin = 0.f;
};
