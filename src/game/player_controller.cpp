#include "player_controller.hpp"
#include "training_dummy.hpp"

#include <godot_cpp/classes/animation_library.hpp>
#include <godot_cpp/classes/engine.hpp>
#include <godot_cpp/classes/input.hpp>
#include <godot_cpp/classes/input_event_mouse_motion.hpp>
#include <godot_cpp/classes/scene_tree.hpp>
#include <godot_cpp/classes/scene_tree_timer.hpp>
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
constexpr float ACCELERATION = 20.f;
constexpr float DECELERATION = 26.f;
constexpr float RUN_THRESHOLD = 0.4f;
constexpr float MIN_STRIDE_SPEED = 0.55f;
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

float damp(float rate, float delta)
{
  return 1.f - Math::exp(-rate * delta);
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
  model = get_node<Node3D>("Model");
  camera_pivot = get_node<Node3D>("CameraPivot");
  camera = get_node<Camera3D>("CameraPivot/SpringArm3D/Camera3D");
  animator = get_node<AnimationPlayer>("Model/AnimationPlayer");
  hitbox = get_node<ShapeCast3D>("Model/armature_male/Skeleton3D/WeaponBone/Hitbox");

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
  attack_animation = animator->get_animation(attack_clip[0]);
  dodge_root_track = dodge_animation->find_track(root_path, Animation::TYPE_POSITION_3D);
  attack_root_track = attack_animation->find_track(root_path, Animation::TYPE_POSITION_3D);

  Ref<AnimationLibrary> clips = animator->get_animation_library("");
  clips->add_animation(dodge_clip[1], dodge_animation);
  clips->add_animation(attack_clip[1], attack_animation);

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
  if (motion != nullptr && captured)
  {
    camera_yaw -= motion->get_relative().x * mouse_sensitivity;
    camera_pitch -= motion->get_relative().y * mouse_sensitivity;
  }
}

void PlayerController::_process(double delta)
{
  update_camera(static_cast<float>(delta));
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

  const bool started = actions.update(delta, wants_to_move, grounded);
  if (started)
    start_action(wish);

  if (actions.hitting())
    hit_targets();

  const PlayerAction action = actions.current();
  if (landed && !started && action == PlayerAction::None && !wants_to_move)
  {
    land_time = LAND_TIME;
    play(land_clip, BLEND_TO_LAND);
    animator->set_speed_scale(1.f);
  }

  Vector3 velocity = get_velocity();
  velocity.y = 0.f;

  if (action == PlayerAction::Dodge || action == PlayerAction::Attack)
    velocity = Vector3(root_motion_step(delta)).rotated(UP, facing_yaw) / delta;
  else if (action == PlayerAction::AirAttack && grounded)
    velocity = velocity.move_toward(Vector3(), DECELERATION * delta);
  else
  {
    const float top_speed = actions.sprinting() ? SPRINT_SPEED : run_speed;
    if (air_time < COYOTE_TIME && action != PlayerAction::Jump)
      velocity = velocity.move_toward(wish * top_speed, (wants_to_move ? ACCELERATION : DECELERATION) * delta);
    else
      // Keeps a sprint's momentum through the jump instead of braking to run speed.
      velocity = velocity.move_toward(wish * MAX(velocity.length(), run_speed), AIR_CONTROL * delta);
    if (wants_to_move && action != PlayerAction::AirAttack)
      target_yaw = Math::atan2(wish.x, wish.z);
    if (action == PlayerAction::None)
      update_locomotion_clip(velocity.length(), grounded, wants_to_move, delta);
  }

  const float speed = velocity.length();
  vertical_speed = on_floor && vertical_speed <= 0.f ? 0.f : vertical_speed - GRAVITY * delta;
  velocity.y = vertical_speed;
  set_velocity(velocity);
  set_wall_min_slide_angle(action == PlayerAction::Attack ? ATTACK_SLIDE_ANGLE : WALK_SLIDE_ANGLE);
  move_and_slide();

  turn_model(delta, speed);
}

void PlayerController::start_action(const Vector3 & wish)
{
  if (wish.length_squared() > 0.01f)
    target_yaw = Math::atan2(wish.x, wish.z);

  land_time = 0.f;
  animator->set_speed_scale(1.f);
  chain = 1 - chain;
  hitbox->clear_exceptions();

  switch (actions.current())
  {
    case PlayerAction::Dodge:
      play(dodge_clip[chain], BLEND_TO_DODGE);
      break;
    case PlayerAction::Attack:
      play(attack_clip[chain], BLEND_TO_ATTACK);
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

void PlayerController::hit_targets()
{
  // Asked on each tick: an Area3D on an animated bone reports nothing for a swing this fast.
  hitbox->force_shapecast_update();
  const int damage = PlayerActions::timing(actions.current()).damage;
  for (int i = 0; i < hitbox->get_collision_count(); ++i)
  {
    TrainingDummy * dummy = Object::cast_to<TrainingDummy>(hitbox->get_collider(i));
    if (dummy != nullptr)
    {
      dummy->take_hit(damage, get_global_position(), hitbox->get_collision_point(i));
      feel_hit(damage);
    }
    // Skipped until the next action, so one swing hits a target once.
    hitbox->add_exception_rid(hitbox->get_collider_rid(i));
  }
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

Vector3 PlayerController::root_motion_step(float delta) const
{
  // Reading the curve on each tick instead of the mixer's per-render-frame delta: a tick
  // holds two or three render frames, and that uneven share made the dodge shake.
  const bool dodge = actions.current() == PlayerAction::Dodge;
  const Ref<Animation> & clip = dodge ? dodge_animation : attack_animation;
  const int track = dodge ? dodge_root_track : attack_root_track;
  // Steps ahead of the clock, so the action already moves on the tick it starts.
  const float now = actions.elapsed();
  return clip->position_track_interpolate(track, now + delta) -
         clip->position_track_interpolate(track, now);
}

void PlayerController::update_locomotion_clip(float speed, bool grounded, bool moving, float delta)
{
  if (!grounded)
  {
    play(fall_clip, BLEND_TO_FALL);
    animator->set_speed_scale(1.f);
    return;
  }

  land_time = MAX(land_time - delta, 0.f);
  if (land_time > 0.f && !moving)
    return;

  const bool running = speed > RUN_THRESHOLD;
  const bool sprinting = speed > (run_speed + SPRINT_SPEED) * 0.5f;
  const float clip_speed = sprinting ? SPRINT_SPEED : run_speed;
  play(sprinting ? sprint_clip : (running ? run_clip : idle_clip), running ? BLEND_TO_RUN : BLEND_TO_IDLE);
  // A slower stride under a light stick push keeps the feet in step with the ground.
  animator->set_speed_scale(running ? CLAMP(speed / clip_speed, MIN_STRIDE_SPEED, 1.f) : 1.f);
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
  const Vector2 look = Input::get_singleton()->get_vector(camera_left, camera_right, camera_up, camera_down);
  camera_yaw -= look.x * CAMERA_STICK_SPEED * delta;
  camera_pitch = CLAMP(camera_pitch - look.y * CAMERA_STICK_SPEED * delta, CAMERA_MIN_PITCH, CAMERA_MAX_PITCH);

  const Vector3 focus = get_global_transform_interpolated().origin + UP * CAMERA_HEIGHT;
  camera_focus = camera_focus.lerp(focus, damp(CAMERA_FOLLOW, delta));
  camera_pivot->set_global_position(camera_focus);
  camera_pivot->set_rotation(Vector3(camera_pitch, camera_yaw, 0));

  // In real time: the shake has to keep going through a hitstop.
  camera_shake = MAX(camera_shake - SHAKE_FADE * delta / static_cast<float>(Engine::get_singleton()->get_time_scale()), 0.f);
  const float reach = camera_shake * camera_shake * SHAKE_SIZE;
  camera->set_h_offset(UtilityFunctions::randf_range(-reach, reach));
  camera->set_v_offset(UtilityFunctions::randf_range(-reach, reach));
}
