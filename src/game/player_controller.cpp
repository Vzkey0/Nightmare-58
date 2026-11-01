#include "player_controller.hpp"
#include "combat_target.hpp"
#include "stat_bar.hpp"
#include "weapon_trail.hpp"

#include <godot_cpp/classes/animation_library.hpp>
#include <godot_cpp/classes/engine.hpp>
#include <godot_cpp/classes/input.hpp>
#include <godot_cpp/classes/input_event_mouse_motion.hpp>
#include <godot_cpp/classes/physics_direct_space_state3d.hpp>
#include <godot_cpp/classes/physics_ray_query_parameters3d.hpp>
#include <godot_cpp/classes/scene_tree.hpp>
#include <godot_cpp/classes/scene_tree_timer.hpp>
#include <godot_cpp/classes/viewport.hpp>
#include <godot_cpp/classes/world3d.hpp>
#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/core/math.hpp>
#include <godot_cpp/variant/utility_functions.hpp>

using namespace godot;

namespace
{
const Vector3 UP(0, 1, 0);
const Vector3 MODEL_FORWARD(0, 0, 1);
const Vector3 MODEL_RIGHT(1, 0, 0);
constexpr float PI = static_cast<float>(Math::PI);

constexpr float GRAVITY = 18.f;
constexpr float JUMP_SPEED = 6.3f; // About 1.1 m high.
constexpr float AIR_CONTROL = 6.f;
constexpr float COYOTE_TIME = 0.1f;
constexpr float LAND_TIME = 0.4f;
constexpr float SPRINT_SPEED = 6.8f; // Must match the sprint clip in animate_protagonist.py.
constexpr float WALK_SPEED = 1.9f;   // Same, for the walk clip.
constexpr float ACCELERATION = 20.f;
constexpr float DECELERATION = 26.f;
constexpr float RUN_THRESHOLD = 0.4f;
constexpr float MIN_STRIDE_SPEED = 0.55f;
constexpr float MAX_WALK_STRIDE = 1.7f; // A half push walks faster than the clip's own speed.
constexpr float MIN_PUSH = 0.1f;
constexpr float FULL_PUSH = 0.7f;   // Below this, a stick walks instead of running.
constexpr float BRAKE_SPEED = 0.6f; // Share of the run speed that needs a stop or a turn clip.
constexpr float REVERSE_DOT = -0.3f;
constexpr float WALK_SLIDE_ANGLE = 0.26f; // Godot's default.
constexpr float ATTACK_SLIDE_ANGLE = 1.2f; // An attack's step stops at a target instead of rounding it.

constexpr float TURN_RATE = 11.f;
constexpr float ACTION_TURN_RATE = 34.f;
constexpr float ACTION_TURN_TIME = 0.12f;
constexpr float LEAN_PER_TURN = 0.05f;
constexpr float TILT_PER_ACCELERATION = 0.012f;
constexpr float MAX_LEAN = 0.14f;
constexpr float LEAN_RATE = 9.f;

constexpr float BLEND_TO_RUN = 0.15f;
constexpr float BLEND_TO_IDLE = 0.24f;
constexpr float BLEND_TO_DODGE = 0.05f;
constexpr float BLEND_TO_ATTACK = 0.09f;
constexpr float BLEND_TO_FALL = 0.25f;
constexpr float BLEND_TO_LAND = 0.05f;
constexpr float BLEND_TO_FLOURISH = 0.07f;

constexpr float RUN_START_TIME = 0.33f;
constexpr float RUN_STOP_TIME = 0.5f;
constexpr float RUN_TURN_TIME = 0.43f;

constexpr float MAGNET_RANGE = 4.5f;
constexpr float MAGNET_COS = 0.25f;  // About 75 degrees to each side of the input.
constexpr float STRIKE_REACH = 1.3f; // How far from a target a blow should end its step.

constexpr float CAMERA_HEIGHT = 1.5f;
constexpr float CAMERA_FOLLOW = 11.f;
constexpr float CAMERA_STICK_SPEED = 2.8f;
constexpr float CAMERA_MIN_PITCH = -1.05f;
constexpr float CAMERA_MAX_PITCH = 0.6f;

constexpr float HITSTOP_PER_DAMAGE = 0.0027f;
constexpr float HITSTOP_TIME_SCALE = 0.02f; // Not 0: the shake divides by it to stay in real time.
constexpr float SHAKE_PER_DAMAGE = 0.03f;
constexpr float SHAKE_SIZE = 0.13f;
constexpr float SHAKE_FADE = 3.5f;
constexpr float SLAM_SHAKE = 0.7f;
constexpr float KICK_FOV = 6.f;
constexpr float KICK_FADE = 5.f;

constexpr float STICK_HALF = 0.8f;   // Half of the Hitbox capsule in player.tscn.
constexpr float WHIRL_START = 0.12f; // The third blow's overhead spin, before its hit window.

constexpr int HEAVY_DAMAGE = 24; // From here on, a blow uses the heavy swing sound.

constexpr float HURT_PUSH = 4.f;
constexpr float RESPAWN_TIME = 3.f;

constexpr float LOCK_SPEED = 2.2f; // Must match LOCK_SPEED in animate_protagonist.py.
constexpr float LOCK_RANGE = 12.f;
constexpr float LOCK_BREAK_RANGE = 16.f;
constexpr float LOCK_VIEW_ANGLE = 1.05f;
constexpr float LOCK_HIDDEN_TIME = 1.f;
constexpr float LOCK_HEIGHT = 1.2f; // Aims at the chest.
constexpr float LOCK_CAMERA_FOLLOW = 9.f;
constexpr float LOCK_CAMERA_PITCH = -0.2f; // Over the shoulder, so the player stays in view.
constexpr float LOCK_MIN_CAMERA_GAP = 0.8f; // Closer than this, the direction spins too fast.
constexpr float LOCK_PITCH_MIN_GAP = 4.f;   // Up close, the camera would stare at the floor.
constexpr float LOCK_FLICK = 140.f; // Pixels.
constexpr float LOCK_FLICK_FADE = 8.f;
constexpr float LOCK_STICK_FLICK = 0.75f;
constexpr float LOCK_STICK_REST = 0.3f;
constexpr uint32_t LEVEL_MASK = 1;

constexpr float HUD_BASE_HEIGHT = 1080.f; // The HUD's sizes in player.tscn are for this height.
const Color HEALTH_HIGH(0.12f, 0.9f, 0.34f);
const Color HEALTH_MID(1.f, 0.74f, 0.12f);
const Color HEALTH_LOW(1.f, 0.46f, 0.08f);
const Color HEALTH_CRITICAL(0.9f, 0.1f, 0.15f);
const Color STAMINA_READY(0.08f, 0.78f, 0.96f);
const Color STAMINA_WINDED(0.5f, 0.55f, 0.62f);

constexpr float STEP_VOLUME_WALK = -18.f;
constexpr float STEP_VOLUME_RUN = -12.f;
constexpr float STEP_VOLUME_SPRINT = -8.f;

float damp(float rate, float delta)
{
  return 1.f - Math::exp(-rate * delta);
}

const Color & health_color(float ratio)
{
  if (ratio > 0.6f)
    return HEALTH_HIGH;
  if (ratio > 0.35f)
    return HEALTH_MID;
  return ratio > 0.15f ? HEALTH_LOW : HEALTH_CRITICAL;
}
}

void PlayerController::_bind_methods()
{
  ClassDB::bind_method(D_METHOD("get_run_speed"), &PlayerController::get_run_speed);
  ClassDB::bind_method(D_METHOD("set_run_speed", "value"), &PlayerController::set_run_speed);
  ClassDB::bind_method(D_METHOD("get_mouse_sensitivity"), &PlayerController::get_mouse_sensitivity);
  ClassDB::bind_method(D_METHOD("set_mouse_sensitivity", "value"), &PlayerController::set_mouse_sensitivity);
  ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "run_speed"), "set_run_speed", "get_run_speed");
  ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "mouse_sensitivity"), "set_mouse_sensitivity", "get_mouse_sensitivity");
}

void PlayerController::_ready()
{
  add_to_group("player");
  spawn_point = get_global_position();
  model = get_node<Node3D>("Model");
  camera_pivot = get_node<Node3D>("CameraPivot");
  camera = get_node<Camera3D>("CameraPivot/SpringArm3D/Camera3D");
  animator = get_node<AnimationPlayer>("Model/AnimationPlayer");
  hitbox = get_node<ShapeCast3D>("Model/armature_male/Skeleton3D/WeaponBone/Hitbox");
  trail = get_node<WeaponTrail>("WeaponTrail");
  dust = get_node<CPUParticles3D>("Dust");
  swing_sound = get_node<AudioStreamPlayer>("Sounds/Swing");
  heavy_swing_sound = get_node<AudioStreamPlayer>("Sounds/HeavySwing");
  hit_sound = get_node<AudioStreamPlayer>("Sounds/Hit");
  slam_sound = get_node<AudioStreamPlayer>("Sounds/Slam");
  roll_sound = get_node<AudioStreamPlayer>("Sounds/Roll");
  roll_land_sound = get_node<AudioStreamPlayer>("Sounds/RollLand");
  step_sound = get_node<AudioStreamPlayer>("Sounds/Step");
  hud_panel = get_node<Control>("Hud/Panel");
  health_bar = get_node<StatBar>("Hud/Panel/HealthBar");
  stamina_bar = get_node<StatBar>("Hud/Panel/StaminaBar");
  lock_marker = get_node<Node2D>("Hud/LockMarker");
  base_fov = camera->get_fov();

  // The scene places the player with a rotation; it moves to the model and the camera.
  facing_yaw = target_yaw = get_rotation().y;
  camera_yaw = facing_yaw + PI;
  set_rotation(Vector3());
  model->set_rotation(Vector3(0, facing_yaw, 0));
  camera_focus = get_global_position() + UP * CAMERA_HEIGHT;

  // Declared as the root motion track only so the bone stays out of the mixed pose.
  const NodePath root_path("armature_male/Skeleton3D:root");
  animator->set_root_motion_track(root_path);
  dodge_animation = animator->get_animation(dodge_clip[0]);
  dodge_root_track = dodge_animation->find_track(root_path, Animation::TYPE_POSITION_3D);
  for (int step = 0; step < ATTACK_CLIPS; ++step)
  {
    attack_animation[step] = animator->get_animation(attack_clip[step]);
    attack_root_track[step] = attack_animation[step]->find_track(root_path, Animation::TYPE_POSITION_3D);
  }
  roll_attack_animation = animator->get_animation(attack_roll_clip);
  roll_attack_root_track = roll_attack_animation->find_track(root_path, Animation::TYPE_POSITION_3D);
  run_attack_animation = animator->get_animation(attack_run_clip);
  run_attack_root_track = run_attack_animation->find_track(root_path, Animation::TYPE_POSITION_3D);
  heavy_attack_animation = animator->get_animation(attack_heavy_clip);
  heavy_attack_root_track = heavy_attack_animation->find_track(root_path, Animation::TYPE_POSITION_3D);

  Ref<AnimationLibrary> clips = animator->get_animation_library("");
  clips->add_animation(dodge_clip[1], dodge_animation);

  play(idle_clip, 0.f);
  Input::get_singleton()->set_mouse_mode(Input::MOUSE_MODE_CAPTURED);
}

void PlayerController::_unhandled_input(const Ref<InputEvent> & event)
{
  Input * input = Input::get_singleton();
  const bool captured = input->get_mouse_mode() == Input::MOUSE_MODE_CAPTURED;

  if (event->is_action_pressed("ui_cancel"))
  {
    input->set_mouse_mode(captured ? Input::MOUSE_MODE_VISIBLE : Input::MOUSE_MODE_CAPTURED);
    return;
  }

  const InputEventMouseMotion * motion = Object::cast_to<InputEventMouseMotion>(*event);
  if (motion == nullptr || !captured)
    return;
  if (locked_target() != nullptr)
  {
    lock_flick += motion->get_relative().x;
    return;
  }
  camera_yaw -= motion->get_relative().x * mouse_sensitivity;
  camera_pitch -= motion->get_relative().y * mouse_sensitivity;
}

void PlayerController::_process(double delta)
{
  update_camera(static_cast<float>(delta));
  update_hud(static_cast<float>(delta));
}

void PlayerController::_physics_process(double delta_time)
{
  const float delta = static_cast<float>(delta_time);
  Input * input = Input::get_singleton();

  const Vector2 stick = input->get_vector(move_left, move_right, move_forward, move_back);
  const Vector3 wish = Vector3(stick.x, 0, stick.y).rotated(UP, camera_yaw);
  const bool wants_to_move = wish.length_squared() > 0.01f;

  // A short grace period, so a small step down does not count as falling.
  const bool on_floor = is_on_floor();
  const bool landed = on_floor && air_time >= COYOTE_TIME;
  air_time = on_floor ? 0.f : air_time + delta;
  const bool grounded = air_time < COYOTE_TIME;

  actions.update_dodge_button(input->is_action_pressed(dodge_input), delta);
  if (input->is_action_just_pressed(jump_input))
    actions.press(PlayerAction::Jump);
  if (input->is_action_just_pressed(attack_input))
    actions.press(PlayerAction::Attack);
  if (input->is_action_just_pressed(heavy_attack_input))
    actions.press(PlayerAction::HeavyAttack);

  update_lock(delta);
  turns.update(delta);

  const bool started = actions.update(delta, wants_to_move, grounded);
  if (started)
    start_action(wish);

  if (actions.hitting())
    hit_targets();
  update_weapon_effects(delta);

  const PlayerAction action = actions.current();
  const bool attacking = actions.stepping_attack();
  const bool stunned = action == PlayerAction::Hurt || action == PlayerAction::Dead;
  const CombatTarget * locked = locked_target();
  const bool strafing = locked != nullptr && !actions.sprinting();

  if (action == PlayerAction::Dead)
  {
    respawn_time -= delta;
    if (respawn_time <= 0.f)
      respawn();
  }

  if (landed)
    step_sound->play();
  if (landed && !started && action == PlayerAction::None && !wants_to_move)
  {
    land_time = LAND_TIME;
    play(land_clip, BLEND_TO_LAND);
    animator->set_speed_scale(1.f);
  }

  Vector3 velocity = get_velocity();
  velocity.y = 0.f;

  if (action == PlayerAction::Dodge || attacking)
    velocity = Vector3(root_motion_step(delta)).rotated(UP, facing_yaw) * step_scale / delta;
  else if ((action == PlayerAction::AirAttack && grounded) || stunned)
    velocity = velocity.move_toward(Vector3(), DECELERATION * delta);
  else
  {
    const float top_speed = actions.sprinting() ? SPRINT_SPEED : (strafing ? LOCK_SPEED : run_speed);
    if (air_time < COYOTE_TIME && action != PlayerAction::Jump)
      velocity = velocity.move_toward(wish * top_speed, (wants_to_move ? ACCELERATION : DECELERATION) * delta);
    else
      // Keeps a sprint's momentum through the jump instead of braking to run speed.
      velocity = velocity.move_toward(wish * MAX(velocity.length(), run_speed), AIR_CONTROL * delta);
    if (wants_to_move && action != PlayerAction::AirAttack)
      target_yaw = Math::atan2(wish.x, wish.z);
    if (strafing && action != PlayerAction::AirAttack)
      target_yaw = yaw_towards(locked);
    if (action == PlayerAction::None)
    {
      const bool reversing = wants_to_move && velocity.dot(wish) < REVERSE_DOT * velocity.length() * wish.length();
      update_locomotion_clip(velocity.length(), grounded, wish.length(), reversing, strafing ? strafe_clip_for(velocity) : StringName(), delta);
    }
  }

  const float speed = velocity.length();
  vertical_speed = on_floor && vertical_speed <= 0.f ? 0.f : vertical_speed - GRAVITY * delta;
  velocity.y = vertical_speed;
  set_velocity(velocity);
  set_wall_min_slide_angle(attacking ? ATTACK_SLIDE_ANGLE : WALK_SLIDE_ANGLE);
  move_and_slide();

  turn_model(delta, speed);
}

void PlayerController::start_action(const Vector3 & wish)
{
  if (wish.length_squared() > 0.01f)
    target_yaw = Math::atan2(wish.x, wish.z);

  land_time = 0.f;
  flourish_time = 0.f;
  step_scale = 1.f;
  animator->set_speed_scale(1.f);
  chain = 1 - chain;
  hitbox->clear_exceptions();

  switch (actions.current())
  {
    case PlayerAction::Dodge:
      play(dodge_clip[chain], BLEND_TO_DODGE);
      motion_animation = dodge_animation;
      motion_track = dodge_root_track;
      kick_dust(get_global_position());
      roll_sound->play();
      break;
    case PlayerAction::Attack:
    case PlayerAction::Attack2:
    case PlayerAction::Attack3:
      play(attack_clip[actions.combo_step()], BLEND_TO_ATTACK);
      motion_animation = attack_animation[actions.combo_step()];
      motion_track = attack_root_track[actions.combo_step()];
      bend_towards_target(wish);
      break;
    case PlayerAction::RollAttack:
      play(attack_roll_clip, BLEND_TO_ATTACK);
      motion_animation = roll_attack_animation;
      motion_track = roll_attack_root_track;
      bend_towards_target(wish);
      break;
    case PlayerAction::RunAttack:
      play(attack_run_clip, BLEND_TO_ATTACK);
      motion_animation = run_attack_animation;
      motion_track = run_attack_root_track;
      bend_towards_target(wish);
      break;
    case PlayerAction::HeavyAttack:
      play(attack_heavy_clip, BLEND_TO_ATTACK);
      motion_animation = heavy_attack_animation;
      motion_track = heavy_attack_root_track;
      bend_towards_target(wish);
      break;
    case PlayerAction::Jump:
      vertical_speed = JUMP_SPEED;
      air_time = COYOTE_TIME;
      play(jump_clip, BLEND_TO_DODGE);
      break;
    default:
      play(attack_air_clip, BLEND_TO_ATTACK);
      break;
  }
}

void PlayerController::bend_towards_target(const Vector3 & wish)
{
  // A locked target wins over the direction pushed: that blow is aimed at it.
  const CombatTarget * locked = locked_target();
  if (locked != nullptr)
    target_yaw = yaw_towards(locked);
  const bool pushing = locked == nullptr && wish.length_squared() > 0.01f;
  const Vector3 heading = pushing ? wish.normalized() : MODEL_FORWARD.rotated(UP, locked != nullptr ? target_yaw : facing_yaw);
  Vector3 closest;
  float distance = MAGNET_RANGE;
  const TypedArray<Node> targets = get_tree()->get_nodes_in_group("targets");
  for (int i = 0; i < targets.size(); ++i)
  {
    const Vector3 offset = (Object::cast_to<Node3D>(targets[i])->get_global_position() - get_global_position()).slide(UP);
    const float length = offset.length();
    if (length < distance && offset.dot(heading) > MAGNET_COS * length)
    {
      closest = offset;
      distance = length;
    }
  }
  if (distance == MAGNET_RANGE)
    return;

  target_yaw = Math::atan2(closest.x, closest.z);
  const float clip_step = motion_animation->position_track_interpolate(motion_track, motion_animation->get_length()).length();
  step_scale = PlayerActions::step_scale(distance - STRIKE_REACH, clip_step);
}

void PlayerController::hit_targets()
{
  // Asked on each tick: an Area3D on an animated bone reports nothing for a swing this fast.
  hitbox->force_shapecast_update();
  const int damage = PlayerActions::timing(actions.current()).damage;
  for (int i = 0; i < hitbox->get_collision_count(); ++i)
  {
    CombatTarget * target = Object::cast_to<CombatTarget>(hitbox->get_collider(i));
    if (target != nullptr)
    {
      target->take_hit(damage, get_global_position(), hitbox->get_collision_point(i));
      feel_hit(damage);
      hit_sound->play();
    }
    // Skipped until the next action, so one swing hits a target once.
    hitbox->add_exception_rid(hitbox->get_collider_rid(i));
  }
}

void PlayerController::update_weapon_effects(float delta)
{
  const PlayerAction action = actions.current();
  const Transform3D stick = hitbox->get_global_transform();
  const Vector3 tip = stick.xform(Vector3(0, STICK_HALF, 0));
  const bool whirling = action == PlayerAction::Attack3 && actions.elapsed() >= WHIRL_START &&
                        actions.elapsed() < PlayerActions::timing(action).hit_end;
  if (whirling || actions.hitting())
    trail->add_sample(stick.origin, tip);

  const ActionTiming & timing = PlayerActions::timing(action);
  const float time = actions.elapsed();
  if (time >= timing.hit_start && time - delta < timing.hit_start && timing.hit_end > timing.hit_start)
    (timing.damage >= HEAVY_DAMAGE ? heavy_swing_sound : swing_sound)->play();
  if (action == PlayerAction::Attack3 && time >= WHIRL_START && time - delta < WHIRL_START)
    heavy_swing_sound->play();

  if (!actions.hit_ground(delta))
    return;
  if (action == PlayerAction::Dodge)
  {
    kick_dust(get_global_position());
    roll_land_sound->play();
    return;
  }
  kick_dust(Vector3(tip.x, get_global_position().y, tip.z));
  slam_sound->play();
  camera_shake = MIN(camera_shake + SLAM_SHAKE, 1.f);
  camera_kick = 1.f;
}

void PlayerController::kick_dust(const Vector3 & where)
{
  dust->set_global_position(where);
  dust->restart();
}

void PlayerController::feel_hit(int damage)
{
  camera_shake = MIN(camera_shake + damage * SHAKE_PER_DAMAGE, 1.f);

  Engine::get_singleton()->set_time_scale(HITSTOP_TIME_SCALE);
  Ref<SceneTreeTimer> timer = get_tree()->create_timer(damage * HITSTOP_PER_DAMAGE, true, false, true);
  timer->connect("timeout", callable_mp(this, &PlayerController::end_hitstop));
}

void PlayerController::end_hitstop()
{
  Engine::get_singleton()->set_time_scale(1.0);
}

void PlayerController::take_hit(int damage, const Vector3 & attacker)
{
  if (actions.invulnerable())
    return;

  const Vector3 away = (get_global_position() - attacker).slide(UP).normalized();
  target_yaw = Math::atan2(-away.x, -away.z);
  set_velocity(away * HURT_PUSH);
  land_time = 0.f;
  flourish_time = 0.f;
  animator->set_speed_scale(1.f);
  feel_hit(damage);
  hit_sound->play();

  health.damage(damage);
  if (health.dead())
  {
    actions.die();
    release_lock();
    respawn_time = RESPAWN_TIME;
    play(death_clip, BLEND_TO_DODGE);
    return;
  }
  actions.hurt();
  play(hurt_clip, BLEND_TO_DODGE);
}

void PlayerController::respawn()
{
  set_global_position(spawn_point);
  set_velocity(Vector3());
  health.restore();
  actions.revive();
  ++respawns;
  play(idle_clip, BLEND_TO_IDLE);
}

CombatTarget * PlayerController::locked_target() const
{
  return Object::cast_to<CombatTarget>(ObjectDB::get_instance(lock_id));
}

float PlayerController::yaw_towards(const Node3D * node) const
{
  const Vector3 offset = node->get_global_position() - get_global_position();
  return Math::atan2(offset.x, offset.z);
}

bool PlayerController::sees(const CombatTarget * target) const
{
  const Vector3 from = get_global_position() + UP * CAMERA_HEIGHT;
  const Vector3 to = target->get_global_position() + UP * LOCK_HEIGHT;
  const Dictionary hit = get_world_3d()->get_direct_space_state()->intersect_ray(PhysicsRayQueryParameters3D::create(from, to, LEVEL_MASK));
  return hit.is_empty() || static_cast<uint64_t>(hit["collider_id"]) == target->get_instance_id();
}

float PlayerController::view_side(const CombatTarget * target) const
{
  const Vector3 offset = (target->get_global_position() - camera_focus).slide(UP);
  return Math::wrapf(Math::atan2(-offset.x, -offset.z) - camera_yaw, -PI, PI);
}

void PlayerController::gather_lock_candidates()
{
  lock_candidates.clear();
  const TypedArray<Node> targets = get_tree()->get_nodes_in_group("targets");
  for (int i = 0; i < targets.size(); ++i)
  {
    const CombatTarget * target = Object::cast_to<CombatTarget>(targets[i]);
    if (target == nullptr || target->is_down())
      continue;
    const float distance = target->get_global_position().distance_to(camera_focus);
    const float side = view_side(target);
    if (distance < LOCK_RANGE && Math::abs(side) < LOCK_VIEW_ANGLE)
      lock_candidates.add(LockCandidate{i, distance, side});
  }
  lock_candidates.sort();
}

void PlayerController::lock_nearest()
{
  gather_lock_candidates();
  const TypedArray<Node> targets = get_tree()->get_nodes_in_group("targets");
  for (int i = 0; i < lock_candidates.size(); ++i)
  {
    CombatTarget * target = Object::cast_to<CombatTarget>(targets[lock_candidates[i].id]);
    if (sees(target))
    {
      lock_onto(target);
      return;
    }
  }
}

void PlayerController::lock_onto(CombatTarget * target)
{
  release_lock();
  lock_id = target->get_instance_id();
  target->set_targeted(true);
}

void PlayerController::switch_lock(int direction)
{
  gather_lock_candidates();
  const int next = lock_candidates.next_to(view_side(locked_target()), direction);
  if (next == LockOnList::NONE)
    return;
  const TypedArray<Node> targets = get_tree()->get_nodes_in_group("targets");
  CombatTarget * target = Object::cast_to<CombatTarget>(targets[next]);
  if (sees(target))
    lock_onto(target);
}

void PlayerController::release_lock()
{
  CombatTarget * target = locked_target();
  if (target != nullptr)
    target->set_targeted(false);
  lock_id = 0;
  lock_hidden_time = 0.f;
  lock_flick = 0.f;
}

void PlayerController::update_lock(float delta)
{
  Input * input = Input::get_singleton();
  if (input->is_action_just_pressed(lock_input) && actions.current() != PlayerAction::Dead)
  {
    if (locked_target() != nullptr)
      release_lock();
    else
      lock_nearest();
  }

  const CombatTarget * target = locked_target();
  if (target == nullptr)
    return;

  lock_hidden_time = sees(target) ? 0.f : lock_hidden_time + delta;
  if (target->is_down() || lock_hidden_time > LOCK_HIDDEN_TIME ||
      target->get_global_position().distance_to(get_global_position()) > LOCK_BREAK_RANGE)
  {
    release_lock();
    return;
  }

  const float stick = input->get_axis(camera_left, camera_right);
  const bool stick_flicked = stick_centered && Math::abs(stick) > LOCK_STICK_FLICK;
  stick_centered = Math::abs(stick) < LOCK_STICK_REST || (stick_centered && !stick_flicked);
  lock_flick = Math::lerp(lock_flick, 0.f, damp(LOCK_FLICK_FADE, delta));
  if (stick_flicked || Math::abs(lock_flick) > LOCK_FLICK)
  {
    const float push = stick_flicked ? stick : lock_flick;
    lock_flick = 0.f;
    switch_lock(push > 0.f ? -1 : 1);
  }
}

void PlayerController::update_hud(float delta)
{
  const float scale = get_viewport()->get_visible_rect().size.y / HUD_BASE_HEIGHT;
  hud_panel->set_scale(Vector2(scale, scale));

  health_trail.update(health.ratio(), delta);
  health_bar->set_values(health.ratio(), health_trail.value());
  health_bar->set_fill_color(health_color(health.ratio()));
  stamina_bar->set_values(actions.stamina_ratio(), 0.f);
  stamina_bar->set_fill_color(actions.winded() ? STAMINA_WINDED : STAMINA_READY);

  const CombatTarget * target = locked_target();
  const Vector3 aim = target != nullptr ? target->get_global_position() + UP * LOCK_HEIGHT : Vector3();
  lock_marker->set_visible(target != nullptr && !camera->is_position_behind(aim));
  if (lock_marker->is_visible())
    lock_marker->set_position(camera->unproject_position(aim));
}

Vector3 PlayerController::root_motion_step(float delta) const
{
  // Reading the curve on each tick instead of the mixer's per-render-frame delta: a tick
  // holds two or three render frames, and that uneven share made the dodge shake.
  // Steps ahead of the clock, so the action already moves on the tick it starts.
  const float now = actions.elapsed();
  return motion_animation->position_track_interpolate(motion_track, now + delta) -
         motion_animation->position_track_interpolate(motion_track, now);
}

void PlayerController::start_flourish(const StringName & clip, float time)
{
  play(clip, BLEND_TO_FLOURISH);
  animator->set_speed_scale(1.f);
  flourish_time = time;
}

void PlayerController::update_locomotion_clip(float speed, bool grounded, float push, bool reversing, const StringName & strafe, float delta)
{
  if (!grounded)
  {
    flourish_time = 0.f;
    play(fall_clip, BLEND_TO_FALL);
    animator->set_speed_scale(1.f);
    return;
  }

  const bool moving = push > MIN_PUSH;
  land_time = MAX(land_time - delta, 0.f);
  if (land_time > 0.f && !moving)
    return;

  const bool strafing = !strafe.is_empty();
  const bool striding = is_stride(current_clip);
  const bool fast = speed > run_speed * BRAKE_SPEED;
  // Pushing against a wall stays idle, or the start would replay on every failed step.
  if (moving && push >= FULL_PUSH && current_clip == idle_clip && !is_on_wall() && !strafing)
    start_flourish(run_start_clip, RUN_START_TIME);
  else if (!moving && fast && (striding || current_clip == run_start_clip))
  {
    start_flourish(run_stop_clip, RUN_STOP_TIME);
    kick_dust(get_global_position());
    step_sound->play();
  }
  else if (reversing && fast && striding)
  {
    start_flourish(run_turn_clip, RUN_TURN_TIME);
    kick_dust(get_global_position());
    step_sound->play();
  }

  flourish_time = MAX(flourish_time - delta, 0.f);
  const bool changed_mind = (current_clip == run_stop_clip && moving) || (current_clip == run_start_clip && !moving);
  if (flourish_time > 0.f && !changed_mind)
    return;
  flourish_time = 0.f;

  const bool running = speed > RUN_THRESHOLD;
  const bool sprinting = !strafing && speed > (run_speed + SPRINT_SPEED) * 0.5f;
  const bool walking = strafing || (moving ? push < FULL_PUSH : speed < (run_speed + WALK_SPEED) * 0.5f);
  const StringName & stride = strafing ? strafe : (sprinting ? sprint_clip : (walking ? walk_clip : run_clip));
  const StringName & clip = !running ? idle_clip : stride;
  const float clip_speed = sprinting ? SPRINT_SPEED : (clip == walk_clip ? WALK_SPEED : (strafing ? LOCK_SPEED : run_speed));

  // The stride clips share a phase, so the feet stay in step when one blends into another.
  const bool keep_phase = striding && is_stride(clip) && clip != current_clip;
  const double phase = keep_phase ? animator->get_current_animation_position() / animator->get_current_animation_length() : 0.0;
  play(clip, running ? BLEND_TO_RUN : BLEND_TO_IDLE);
  if (keep_phase)
    animator->seek(phase * animator->get_current_animation_length());

  // A slower stride under a light stick push keeps the feet in step with the ground.
  animator->set_speed_scale(running ? CLAMP(speed / clip_speed, MIN_STRIDE_SPEED, walking ? MAX_WALK_STRIDE : 1.f) : 1.f);

  if (!is_stride(clip))
    return;
  // Each foot lands at the start of its half of the clip.
  const int half = static_cast<int>(animator->get_current_animation_position() / animator->get_current_animation_length() * 2.0);
  if (half != stride_half)
  {
    stride_half = half;
    step_sound->set_volume_db(sprinting ? STEP_VOLUME_SPRINT : (walking ? STEP_VOLUME_WALK : STEP_VOLUME_RUN));
    step_sound->play();
  }
}

const StringName & PlayerController::strafe_clip_for(const Vector3 & velocity) const
{
  // ponytail: picks the main one of four directions, so a diagonal slides a little. An
  // AnimationTree would blend them, if that ever shows.
  const Vector3 local = velocity.rotated(UP, -facing_yaw);
  if (Math::abs(local.z) >= Math::abs(local.x))
    return local.z >= 0.f ? walk_clip : walk_back_clip;
  return local.x > 0.f ? strafe_left_clip : strafe_right_clip;
}

bool PlayerController::is_stride(const StringName & clip) const
{
  return clip == walk_clip || clip == run_clip || clip == sprint_clip || clip == walk_back_clip ||
         clip == strafe_left_clip || clip == strafe_right_clip;
}

void PlayerController::play(const StringName & clip, float blend)
{
  if (clip != current_clip)
  {
    animator->play(clip, blend);
    current_clip = clip;
  }
}

void PlayerController::turn_model(float delta, float speed)
{
  const PlayerAction action = actions.current();
  const bool acting = action != PlayerAction::None && action != PlayerAction::Jump;
  const bool committed = acting && actions.elapsed() > ACTION_TURN_TIME;
  const float rate = acting ? ACTION_TURN_RATE : TURN_RATE;

  const float previous = facing_yaw;
  if (!committed)
    facing_yaw = Math::lerp_angle(facing_yaw, target_yaw, damp(rate, delta));
  const float turn = Math::wrapf(facing_yaw - previous, -PI, PI) / delta;

  // Leaning into turns and speed changes sells the weight without extra clips.
  const float wanted_lean = acting ? 0.f : -turn * LEAN_PER_TURN * MIN(speed / run_speed, 1.f);
  const float wanted_tilt = acting ? 0.f : (speed - previous_speed) / delta * TILT_PER_ACCELERATION;
  lean = Math::lerp(lean, CLAMP(wanted_lean, -MAX_LEAN, MAX_LEAN), damp(LEAN_RATE, delta));
  tilt = Math::lerp(tilt, CLAMP(wanted_tilt, -MAX_LEAN, MAX_LEAN), damp(LEAN_RATE, delta));
  previous_speed = speed;

  model->set_basis(Basis(UP, facing_yaw) * Basis(MODEL_FORWARD, lean) * Basis(MODEL_RIGHT, tilt));
}

void PlayerController::update_camera(float delta)
{
  const CombatTarget * locked = locked_target();
  if (locked == nullptr)
  {
    const Vector2 look = Input::get_singleton()->get_vector(camera_left, camera_right, camera_up, camera_down);
    camera_yaw -= look.x * CAMERA_STICK_SPEED * delta;
    camera_pitch -= look.y * CAMERA_STICK_SPEED * delta;
  }
  camera_pitch = CLAMP(camera_pitch, CAMERA_MIN_PITCH, CAMERA_MAX_PITCH);

  const Vector3 focus = get_global_transform_interpolated().origin + UP * CAMERA_HEIGHT;
  camera_focus = camera_focus.lerp(focus, damp(CAMERA_FOLLOW, delta));
  if (locked != nullptr)
  {
    const Vector3 offset = locked->get_global_position() + UP * LOCK_HEIGHT - camera_focus;
    const float gap = offset.slide(UP).length();
    if (gap > LOCK_MIN_CAMERA_GAP)
      camera_yaw = Math::lerp_angle(camera_yaw, Math::atan2(-offset.x, -offset.z), damp(LOCK_CAMERA_FOLLOW, delta));
    camera_pitch = Math::lerp(camera_pitch, Math::atan2(offset.y, MAX(gap, LOCK_PITCH_MIN_GAP)) + LOCK_CAMERA_PITCH, damp(LOCK_CAMERA_FOLLOW, delta));
  }
  camera_pivot->set_global_position(camera_focus);
  camera_pivot->set_rotation(Vector3(camera_pitch, camera_yaw, 0));

  // In real time: the shake has to keep going through a hitstop.
  const float real_delta = delta / static_cast<float>(Engine::get_singleton()->get_time_scale());
  camera_shake = MAX(camera_shake - SHAKE_FADE * real_delta, 0.f);
  camera_kick = MAX(camera_kick - KICK_FADE * real_delta, 0.f);
  camera->set_fov(base_fov - camera_kick * camera_kick * KICK_FOV);
  const float reach = camera_shake * camera_shake * SHAKE_SIZE;
  camera->set_h_offset(UtilityFunctions::randf_range(-reach, reach));
  camera->set_v_offset(UtilityFunctions::randf_range(-reach, reach));
}
