#pragma once

#include <godot_cpp/classes/animation.hpp>
#include <godot_cpp/classes/animation_player.hpp>
#include <godot_cpp/classes/audio_stream_player.hpp>
#include <godot_cpp/classes/shape_cast3d.hpp>
#include <godot_cpp/classes/standard_material3d.hpp>
#include <godot_cpp/variant/string_name.hpp>

#include <core/ai/behavior_tree.hpp>
#include <core/ai/enemy_actions.hpp>
#include <core/progression/loot_table.hpp>

#include "combat_target.hpp"

class PlayerController;

// The body of the skeleton: it gathers what the enemy knows, hands it to its BehaviorTree and
// carries out the answer through EnemyActions. Every instance is independent; the only thing
// they share is the player's AttackTurns, so a scene can hold any number of them.
class SkeletonEnemy : public CombatTarget
{
  GDCLASS(SkeletonEnemy, CombatTarget)

protected:
  static void _bind_methods() {}

public:
  SkeletonEnemy();

  void _ready() override;
  void _exit_tree() override;
  void _process(double delta) override;
  void _physics_process(double delta) override;

  void take_hit(int damage, const godot::Vector3 & attacker, const godot::Vector3 & point) override;

private:
  void think();
  void sense();
  bool sees_player() const;
  void start_attack(const Decision & decision);
  void end_attack();
  void hit_player();
  void go_down(float delta);
  void pay_the_player();
  void reset();

  godot::Vector3 root_motion_step(float delta) const;
  godot::Vector3 walk_velocity() const;
  void aim_step();
  void turn(float delta);
  void play_locomotion(const godot::Vector3 & velocity);
  void play(const godot::StringName & clip, float blend);

  BehaviorTree tree;
  EnemyActions actions;
  PlayerController * player = nullptr;

  godot::Node3D * model = nullptr;
  godot::AnimationPlayer * animator = nullptr;
  godot::ShapeCast3D * hitbox = nullptr;
  godot::AudioStreamPlayer * swing_sound = nullptr;
  godot::Ref<godot::StandardMaterial3D> eyes; // Local: each skeleton's eyes flare on their own.

  godot::Vector3 to_player;
  godot::Vector3 last_seen;
  godot::Vector3 spawn_point;
  EnemyContext context{1.f, DistanceRange::Far, false, false, false, false};
  BehaviorAction intent = BehaviorAction::Watch;

  float facing_yaw = 0.f;
  float spawn_yaw = 0.f;
  float vertical_speed = 0.f;
  float distance = 0.f;
  float think_time = 0.f;
  float sight_time = 0.f;
  float lost_time = 0.f;
  float attack_wait = 0.f;
  float charge_wait = 0.f;
  float circle_time = 0.f;
  float circle_side = 1.f;
  float circle_gap = 3.f; // Each skeleton keeps its own distance, so they spread around the player.
  float step_scale = 1.f;
  bool has_turn = false;
  int player_respawns = 0;

  godot::Ref<godot::Animation> motion_animation;
  int motion_track = -1;

  godot::StringName idle_clip = "idle";
  godot::StringName walk_clip = "walk";
  godot::StringName walk_back_clip = "walk_back";
  godot::StringName strafe_left_clip = "strafe_left";
  godot::StringName strafe_right_clip = "strafe_right";
  godot::StringName hurt_clip = "hurt";
  godot::StringName death_clip = "death";
  godot::StringName current_clip;
};
