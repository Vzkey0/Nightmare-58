#pragma once

#include <godot_cpp/classes/character_body3d.hpp>
#include <godot_cpp/classes/cpu_particles3d.hpp>

#include <core/health.hpp>
#include <core/health_trail.hpp>

class StatBar;

// Anything the player can hit and lock on to. It owns what they all show when hit: sparks, the
// floating health bar and the damage number. Its scene needs Sparks and BarLayer/HealthBar.
class CombatTarget : public godot::CharacterBody3D
{
  GDCLASS(CombatTarget, godot::CharacterBody3D)

protected:
  static void _bind_methods() {}

  void ready_target();
  void receive_damage(int damage, const godot::Vector3 & away, const godot::Vector3 & point);
  void update_health_bar(float delta);

  static constexpr int MAX_HEALTH = 100;

  Health health{MAX_HEALTH};

public:
  virtual void take_hit(int damage, const godot::Vector3 & attacker, const godot::Vector3 & point) {}
  bool is_down() const { return health.dead(); }
  void set_targeted(bool value) { targeted = value; }

private:
  void show_damage(int damage);

  HealthTrail trail;
  godot::CPUParticles3D * sparks = nullptr;
  StatBar * health_bar = nullptr;
  float bar_shake = 0.f;
  float bar_time = 0.f; // Left to show the bar after a hit.
  bool targeted = false;
};
