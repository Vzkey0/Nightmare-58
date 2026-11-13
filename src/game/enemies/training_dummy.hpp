#pragma once

#include <godot_cpp/classes/standard_material3d.hpp>

#include "combat_target.hpp"

class PlayerController;

// A target for trying attacks: it rocks when hit, falls at zero health and stands up again.
// When the player comes close it winds up and spins its arms, to try dodges and taking hits.
class TrainingDummy : public CombatTarget
{
  GDCLASS(TrainingDummy, CombatTarget)

protected:
  static void _bind_methods() {}

public:
  void _ready() override;
  void _process(double delta) override;

  void take_hit(int damage, const godot::Vector3 & attacker, const godot::Vector3 & point) override;

private:
  void update_attack(float delta);

  godot::Node3D * model = nullptr;
  godot::Node3D * arms = nullptr;
  PlayerController * player = nullptr;
  godot::Ref<godot::StandardMaterial3D> material;

  godot::Vector3 tilt_axis = godot::Vector3(1, 0, 0);
  float tilt = 0.f;
  float tilt_speed = 0.f;
  float shove = 0.f;
  float flash = 0.f;
  float down_time = 0.f;
  float attack_time = 0.f;
  float attack_wait = 0.f;
  float windup = 0.f;
};
