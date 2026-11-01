#pragma once

#include <godot_cpp/classes/animation.hpp>
#include <godot_cpp/classes/animation_player.hpp>
#include <godot_cpp/classes/camera3d.hpp>
#include <godot_cpp/classes/character_body3d.hpp>
#include <godot_cpp/classes/input_event.hpp>
#include <godot_cpp/classes/shape_cast3d.hpp>
#include <godot_cpp/variant/string_name.hpp>

#include <core/player/player_actions.hpp>

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
  godot::Vector3 root_motion_step(float delta) const;
  void update_locomotion_clip(float speed, bool grounded, bool moving, float delta);
  void play(const godot::StringName & clip, float blend);
  void turn_model(float delta, float speed);
  void update_camera(float delta);
  void hit_targets();
  void feel_hit(int damage);
  void end_hitstop();

  PlayerActions actions;

  godot::Node3D * model = nullptr;
  godot::Node3D * camera_pivot = nullptr;
  godot::Camera3D * camera = nullptr;
  godot::AnimationPlayer * animator = nullptr;
  godot::ShapeCast3D * hitbox = nullptr;

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
  float camera_yaw = 0.f;
  float camera_pitch = -0.2f;
  float camera_shake = 0.f;
  godot::Vector3 camera_focus;

  godot::Ref<godot::Animation> dodge_animation;
  godot::Ref<godot::Animation> attack_animation;
  int dodge_root_track = -1;
  int attack_root_track = -1;

  // Each action has two names for one clip: a blend needs two different animations,
  // so chaining a dodge into a dodge would otherwise snap.
  int chain = 0;
  godot::StringName dodge_clip[2] = {"dodge_forward", "dodge_forward_chain"};
  godot::StringName attack_clip[2] = {"attack_light_1", "attack_light_1_chain"};
  godot::StringName idle_clip = "idle";
  godot::StringName run_clip = "run";
  godot::StringName sprint_clip = "sprint";
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
