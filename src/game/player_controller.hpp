#pragma once

#include <godot_cpp/classes/animation.hpp>
#include <godot_cpp/classes/animation_player.hpp>
#include <godot_cpp/classes/audio_stream_player.hpp>
#include <godot_cpp/classes/camera3d.hpp>
#include <godot_cpp/classes/character_body3d.hpp>
#include <godot_cpp/classes/cpu_particles3d.hpp>
#include <godot_cpp/classes/input_event.hpp>
#include <godot_cpp/classes/shape_cast3d.hpp>
#include <godot_cpp/variant/string_name.hpp>

#include <core/player/player_actions.hpp>

class WeaponTrail;

// Translates input and animation into movement; the rules live in PlayerActions.
// The body never rotates: the Model child turns, and CameraPivot follows on its own.
class PlayerController : public godot::CharacterBody3D
{
  GDCLASS(PlayerController, godot::CharacterBody3D)

protected:
  static void _bind_methods();

public:
  void _ready() override;
  void _process(double delta) override;
  void _physics_process(double delta) override;
  void _unhandled_input(const godot::Ref<godot::InputEvent> & event) override;

  float get_run_speed() const { return run_speed; }
  void set_run_speed(float value) { run_speed = value; }
  float get_mouse_sensitivity() const { return mouse_sensitivity; }
  void set_mouse_sensitivity(float value) { mouse_sensitivity = value; }

private:
  void start_action(const godot::Vector3 & wish);
  void bend_towards_target(const godot::Vector3 & wish);
  godot::Vector3 root_motion_step(float delta) const;
  void start_flourish(const godot::StringName & clip, float time);
  void update_locomotion_clip(float speed, bool grounded, float push, bool reversing, float delta);
  bool is_stride(const godot::StringName & clip) const;
  void play(const godot::StringName & clip, float blend);
  void turn_model(float delta, float speed);
  void update_camera(float delta);
  void hit_targets();
  void update_weapon_effects(float delta);
  void kick_dust(const godot::Vector3 & where);
  void feel_hit(int damage);
  void end_hitstop();

  static constexpr int ATTACK_CLIPS = 3;

  PlayerActions actions;

  godot::Node3D * model = nullptr;
  godot::Node3D * camera_pivot = nullptr;
  godot::Camera3D * camera = nullptr;
  godot::AnimationPlayer * animator = nullptr;
  godot::ShapeCast3D * hitbox = nullptr;
  WeaponTrail * trail = nullptr;
  godot::CPUParticles3D * dust = nullptr;
  godot::AudioStreamPlayer * swing_sound = nullptr;
  godot::AudioStreamPlayer * heavy_swing_sound = nullptr;
  godot::AudioStreamPlayer * hit_sound = nullptr;
  godot::AudioStreamPlayer * slam_sound = nullptr;
  godot::AudioStreamPlayer * roll_sound = nullptr;
  godot::AudioStreamPlayer * roll_land_sound = nullptr;
  godot::AudioStreamPlayer * step_sound = nullptr;

  // Must match RUN_SPEED in animate_protagonist.py, or the feet slide.
  float run_speed = 4.6f;
  float mouse_sensitivity = 0.0025f;

  float facing_yaw = 0.f;
  float target_yaw = 0.f;
  float lean = 0.f;
  float tilt = 0.f;
  float previous_speed = 0.f;
  float vertical_speed = 0.f;
  float air_time = 0.f;
  float land_time = 0.f;
  float flourish_time = 0.f; // Left of a clip that plays once over the stride: start, stop or turn.
  float step_scale = 1.f;
  int stride_half = 0;
  float camera_yaw = 0.f;
  float camera_pitch = -0.2f;
  float camera_shake = 0.f;
  float camera_kick = 0.f;
  float base_fov = 65.f;
  godot::Vector3 camera_focus;

  godot::Ref<godot::Animation> dodge_animation;
  godot::Ref<godot::Animation> attack_animation[ATTACK_CLIPS];
  int dodge_root_track = -1;
  int attack_root_track[ATTACK_CLIPS] = {};
  godot::Ref<godot::Animation> roll_attack_animation;
  int roll_attack_root_track = -1;
  godot::Ref<godot::Animation> run_attack_animation;
  int run_attack_root_track = -1;
  godot::Ref<godot::Animation> motion_animation;
  int motion_track = -1;

  // A dodge has two names for one clip: a blend needs two different animations, so
  // chaining a dodge into a dodge would otherwise snap.
  int chain = 0;
  godot::StringName dodge_clip[2] = {"dodge_forward", "dodge_forward_chain"};
  godot::StringName attack_clip[ATTACK_CLIPS] = {"attack_light_1", "attack_light_2", "attack_light_3"};
  godot::StringName attack_roll_clip = "attack_roll";
  godot::StringName attack_run_clip = "attack_run";
  godot::StringName idle_clip = "idle";
  godot::StringName walk_clip = "walk";
  godot::StringName run_clip = "run";
  godot::StringName sprint_clip = "sprint";
  godot::StringName run_start_clip = "run_start";
  godot::StringName run_stop_clip = "run_stop";
  godot::StringName run_turn_clip = "run_turn";
  godot::StringName jump_clip = "jump";
  godot::StringName fall_clip = "fall";
  godot::StringName land_clip = "land";
  godot::StringName attack_air_clip = "attack_air";
  godot::StringName current_clip;

  godot::StringName move_left = "move_left";
  godot::StringName move_right = "move_right";
  godot::StringName move_forward = "move_forward";
  godot::StringName move_back = "move_back";
  godot::StringName camera_left = "camera_left";
  godot::StringName camera_right = "camera_right";
  godot::StringName camera_up = "camera_up";
  godot::StringName camera_down = "camera_down";
  godot::StringName dodge_input = "dodge";
  godot::StringName jump_input = "jump";
  godot::StringName attack_input = "attack";
};
