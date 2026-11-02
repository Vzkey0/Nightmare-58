#pragma once

#include <godot_cpp/classes/animation.hpp>
#include <godot_cpp/classes/animation_player.hpp>
#include <godot_cpp/classes/audio_stream_player.hpp>
#include <godot_cpp/classes/camera3d.hpp>
#include <godot_cpp/classes/character_body3d.hpp>
#include <godot_cpp/classes/control.hpp>
#include <godot_cpp/classes/cpu_particles3d.hpp>
#include <godot_cpp/classes/input_event.hpp>
#include <godot_cpp/classes/label.hpp>
#include <godot_cpp/classes/node2d.hpp>
#include <godot_cpp/classes/shape_cast3d.hpp>
#include <godot_cpp/variant/string_name.hpp>

#include <core/ai/attack_turns.hpp>
#include <core/health.hpp>
#include <core/health_trail.hpp>
#include <core/lock_on.hpp>
#include <core/player/player_actions.hpp>
#include <core/progression/player_progress.hpp>

class Chapel;
class CombatTarget;
class GameMenu;
class LostLochas;
class StatBar;
class WeaponTrail;

// Translates input and animation into movement; the rules live in PlayerActions.
// The body never rotates: the Model child turns, and CameraPivot follows on its own.
class PlayerController : public godot::CharacterBody3D
{
  GDCLASS(PlayerController, godot::CharacterBody3D)

protected:
  static void _bind_methods();

public:
  void _enter_tree() override; // Loads the game before any _ready, so pickups can ask about it.
  void _ready() override;
  void _process(double delta) override;
  void _physics_process(double delta) override;
  void _unhandled_input(const godot::Ref<godot::InputEvent> & event) override;

  float get_run_speed() const { return run_speed; }
  void set_run_speed(float value) { run_speed = value; }
  float get_mouse_sensitivity() const { return mouse_sensitivity; }
  void set_mouse_sensitivity(float value) { mouse_sensitivity = value; }

  // Does nothing while the player is invulnerable, as during a roll.
  void take_hit(int damage, const godot::Vector3 & attacker);
  bool is_dead() const { return health.dead(); }
  int respawn_count() const { return respawns; } // Enemies go back to their places on each one.

  const PlayerProgress & progress() const { return save; }
  void earn(int lochas);
  void pick_up(const godot::String & item_key, int amount, int pickup_id);
  void set_nearby_chapel(Chapel * chapel);
  void recover_lochas();
  bool raise_stat(Stat stat);

  // Shared by every enemy around the player, however many there are.
  AttackTurns & attack_turns() { return turns; }

private:
  void start_action(const godot::Vector3 & wish);
  void bend_towards_target(const godot::Vector3 & wish);
  godot::Vector3 root_motion_step(float delta) const;
  void start_flourish(const godot::StringName & clip, float time);
  void update_locomotion_clip(float speed, bool grounded, float push, bool reversing, const godot::StringName & strafe, float delta);
  const godot::StringName & strafe_clip_for(const godot::Vector3 & velocity) const;
  bool is_stride(const godot::StringName & clip) const;
  void play(const godot::StringName & clip, float blend);
  void turn_model(float delta, float speed);
  void update_camera(float delta);
  void hit_targets();
  void update_weapon_effects(float delta);
  void kick_dust(const godot::Vector3 & where);
  void feel_hit(int damage);
  void end_hitstop();
  void respawn();
  void rest();
  void apply_stats();
  void place_at_saved_chapel();
  void drop_lochas();
  void clear_dropped_lochas();
  void read_item_input();
  void use_item();
  void update_progress(float delta);
  void update_hud(float delta);
  void refresh_hud();
  void show_toast(const godot::String & text);

  CombatTarget * locked_target() const;
  float yaw_towards(const godot::Node3D * node) const;
  bool sees(const CombatTarget * target) const;
  float view_side(const CombatTarget * target) const;
  void gather_lock_candidates();
  void lock_nearest();
  void lock_onto(CombatTarget * target);
  void switch_lock(int direction);
  void release_lock();
  void update_lock(float delta);

  static constexpr int ATTACK_CLIPS = 3;

  PlayerActions actions;
  PlayerProgress save;
  Health health{PlayerStats::BASE_HEALTH};
  HealthTrail health_trail;
  LockOnList lock_candidates;
  AttackTurns turns;

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
  godot::Control * hud_panel = nullptr;
  StatBar * health_bar = nullptr;
  StatBar * stamina_bar = nullptr;
  godot::Node2D * lock_marker = nullptr;
  godot::Label * lochas_label = nullptr;
  godot::Label * item_label = nullptr;
  godot::Label * prompt_label = nullptr;
  godot::Label * toast_label = nullptr;
  GameMenu * menu = nullptr;
  Chapel * nearby_chapel = nullptr;
  LostLochas * dropped_lochas = nullptr;

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
  godot::Vector3 spawn_point;
  float respawn_time = 0.f;
  int respawns = 0;
  float regen_carry = 0.f; // Health comes in whole points; a slow rate adds up across ticks.
  float toast_time = 0.f;
  ItemId item_in_use = NO_ITEM;

  uint64_t lock_id = 0; // An id and not a pointer: a target may be freed while locked.
  float lock_hidden_time = 0.f;
  float lock_flick = 0.f; // Mouse travel towards the next target.
  bool stick_centered = true;

  godot::Ref<godot::Animation> dodge_animation;
  godot::Ref<godot::Animation> attack_animation[ATTACK_CLIPS];
  int dodge_root_track = -1;
  int attack_root_track[ATTACK_CLIPS] = {};
  godot::Ref<godot::Animation> roll_attack_animation;
  int roll_attack_root_track = -1;
  godot::Ref<godot::Animation> run_attack_animation;
  int run_attack_root_track = -1;
  godot::Ref<godot::Animation> heavy_attack_animation;
  int heavy_attack_root_track = -1;
  godot::Ref<godot::Animation> motion_animation;
  int motion_track = -1;

  // A dodge has two names for one clip: a blend needs two different animations, so
  // chaining a dodge into a dodge would otherwise snap.
  int chain = 0;
  godot::StringName dodge_clip[2] = {"dodge_forward", "dodge_forward_chain"};
  godot::StringName attack_clip[ATTACK_CLIPS] = {"attack_light_1", "attack_light_2", "attack_light_3"};
  godot::StringName attack_roll_clip = "attack_roll";
  godot::StringName attack_run_clip = "attack_run";
  godot::StringName attack_heavy_clip = "attack_heavy";
  godot::StringName hurt_clip = "hurt";
  godot::StringName death_clip = "death";
  godot::StringName idle_clip = "idle";
  godot::StringName walk_clip = "walk";
  godot::StringName walk_back_clip = "walk_back";
  godot::StringName strafe_left_clip = "strafe_left";
  godot::StringName strafe_right_clip = "strafe_right";
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
  godot::StringName heavy_attack_input = "attack_heavy";
  godot::StringName lock_input = "lock_on";
  godot::StringName interact_input = "interact";
  godot::StringName use_item_input = "use_item";
  godot::StringName next_item_input = "next_item";
  godot::StringName inventory_input = "inventory";
};
