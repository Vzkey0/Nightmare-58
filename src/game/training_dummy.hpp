#pragma once

#include <godot_cpp/classes/cpu_particles3d.hpp>
#include <godot_cpp/classes/standard_material3d.hpp>
#include <godot_cpp/classes/static_body3d.hpp>

#include <core/health.hpp>
#include <core/health_trail.hpp>

class PlayerController;
class StatBar;

// A target for trying attacks: it rocks when hit, falls at zero health and stands up again.
// When the player comes close it winds up and spins its arms, to try dodges and taking hits.
class TrainingDummy : public godot::StaticBody3D
{
  GDCLASS(TrainingDummy, godot::StaticBody3D)

protected:
  static void _bind_methods() {}

public:
  void _ready() override;
  void _process(double delta) override;

  void take_hit(int damage, const godot::Vector3 & attacker, const godot::Vector3 & point);
  bool is_down() const { return health.dead(); }
  void set_targeted(bool value) { targeted = value; }

private:
  void update_attack(float delta);
  void update_health_bar(float delta);
  void show_damage(int damage);

  static constexpr int MAX_HEALTH = 100;

  Health health{MAX_HEALTH};
  HealthTrail trail;

  godot::Node3D * model = nullptr;
  godot::Node3D * arms = nullptr;
  godot::CPUParticles3D * sparks = nullptr;
  StatBar * health_bar = nullptr;
  PlayerController * player = nullptr;
  godot::Ref<godot::StandardMaterial3D> material;

  godot::Vector3 tilt_axis = godot::Vector3(1, 0, 0);
  float tilt = 0.f;
  float tilt_speed = 0.f;
  float shove = 0.f;
  float flash = 0.f;
  float bar_shake = 0.f;
  float bar_time = 0.f; // Left to show the bar after a hit.
  float down_time = 0.f;
  float attack_time = 0.f;
  float attack_wait = 0.f;
  float windup = 0.f;
  bool targeted = false;
};
