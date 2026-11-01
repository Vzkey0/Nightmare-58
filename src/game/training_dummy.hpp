#pragma once

#include <godot_cpp/classes/color_rect.hpp>
#include <godot_cpp/classes/control.hpp>
#include <godot_cpp/classes/cpu_particles3d.hpp>
#include <godot_cpp/classes/standard_material3d.hpp>
#include <godot_cpp/classes/static_body3d.hpp>

#include <core/health.hpp>
#include <core/health_trail.hpp>

// A target for trying attacks: it rocks when hit, falls at zero health and stands up again.
class TrainingDummy : public godot::StaticBody3D
{
  GDCLASS(TrainingDummy, godot::StaticBody3D)

protected:
  static void _bind_methods() {}

public:
  void _ready() override;
  void _process(double delta) override;

  void take_hit(int damage, const godot::Vector3 & attacker, const godot::Vector3 & point);

private:
  void update_health_bar(float delta);
  void show_damage(int damage);

  static constexpr int MAX_HEALTH = 100;

  Health health{MAX_HEALTH};
  HealthTrail trail;

  godot::Node3D * model = nullptr;
  godot::CPUParticles3D * sparks = nullptr;
  godot::Control * health_bar = nullptr;
  godot::ColorRect * bar_trail = nullptr;
  godot::ColorRect * bar_fill = nullptr;
  godot::Ref<godot::StandardMaterial3D> material;
  float bar_width = 0.f;

  godot::Vector3 tilt_axis = godot::Vector3(1, 0, 0);
  float tilt = 0.f;
  float tilt_speed = 0.f;
  float shove = 0.f;
  float flash = 0.f;
  float bar_shake = 0.f;
  float down_time = 0.f;
};
