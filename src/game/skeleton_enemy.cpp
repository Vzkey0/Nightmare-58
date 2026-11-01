#include "skeleton_enemy.hpp"
#include "entity_distance.hpp"
#include "player_controller.hpp"

#include <godot_cpp/classes/mesh.hpp>
#include <godot_cpp/classes/mesh_instance3d.hpp>
#include <godot_cpp/classes/physics_direct_space_state3d.hpp>
#include <godot_cpp/classes/physics_ray_query_parameters3d.hpp>
#include <godot_cpp/classes/scene_tree.hpp>
#include <godot_cpp/classes/world3d.hpp>
#include <godot_cpp/core/math.hpp>
#include <godot_cpp/variant/utility_functions.hpp>

using namespace godot;

namespace
{
const Vector3 UP(0, 1, 0);
const Vector3 MODEL_FORWARD(0, 0, 1);
const Vector3 CHEST(0, 1.2f, 0);
constexpr float PI = static_cast<float>(Math::PI);
constexpr uint32_t LEVEL_MASK = 1;
// The same as skeleton_enemy.tscn: they block each other, and the player's Hitbox finds them.
constexpr uint32_t BODY_LAYERS = 12;
constexpr uint32_t BODY_MASK = 11;

constexpr int MAX_HEALTH = 70;
constexpr float GRAVITY = 18.f;

// J-005: ten looks a second are for acting like something alive; the tree itself costs nothing.
constexpr float THINK_TIME = 0.1f;
constexpr float THINK_JITTER = 0.03f;
constexpr float REACTION_MIN = 0.2f; // On noticing the player or finishing an action.
constexpr float REACTION_MAX = 0.35f;
constexpr float SIGHT_TIME = 0.2f; // A ray is the costly part of a look, so it is the rarest.

constexpr float SIGHT_RANGE_SQUARED = 15.f * 15.f;
constexpr float HEARING_RANGE_SQUARED = 3.5f * 3.5f; // Notices someone close from any side.
constexpr float SIGHT_COS = 0.2f;                    // About 78 degrees to each side.
constexpr float LOST_TIME = 3.f;
constexpr float SEARCH_TIME = 8.f; // Gives up this long after losing the player.
constexpr float ARRIVE_SQUARED = 0.6f * 0.6f;

constexpr float NEAR_RANGE = 1.9f;
constexpr float MEDIUM_RANGE = 4.4f;
constexpr float RANGE_MARGIN = 0.4f;
constexpr float CHARGE_MIN_RANGE = 2.6f; // The leap needs room, or it lands past the player.
constexpr float STRIKE_REACH = 1.25f;    // Where a blow ends its step, with the blade on the player.

constexpr float WALK_SPEED = 1.4f;   // Must match WALK_SPEED in animate_skeleton.py.
constexpr float CIRCLE_SPEED = 1.1f; // Same, for CIRCLE_SPEED.
constexpr float ACCELERATION = 9.f;
constexpr float DECELERATION = 12.f;
constexpr float CIRCLE_GAP_MIN = 2.5f;
constexpr float CIRCLE_GAP_MAX = 3.7f;
constexpr float CIRCLE_SWITCH_MIN = 1.6f;
constexpr float CIRCLE_SWITCH_MAX = 4.f;
constexpr float CIRCLE_IN_OUT = 1.5f;

constexpr float TURN_RATE = 6.f;
constexpr float TRACK_RATE = 3.2f;

constexpr float WAIT_MIN = 0.5f;
constexpr float WAIT_MAX = 1.4f;
constexpr float CHARGE_WAIT = 6.f;

constexpr float DOWN_TIME = 12.f;
constexpr float RISE_TIME = 2.2f; // Length of the death clip, played backwards.
constexpr float HURT_PUSH = 2.2f;

constexpr float EYE_REST = 1.3f;
constexpr float EYE_FLARE = 7.f;

constexpr float BLEND_MOVE = 0.2f;
constexpr float BLEND_ACTION = 0.1f;
constexpr float MIN_STRIDE = 0.15f;

BehaviorTree::AttackQueue melee_attacks()
{
  BehaviorTree::AttackQueue attacks;
  attacks.put(Attack{static_cast<int>(EnemyAction::Chop)});
  attacks.put(Attack{static_cast<int>(EnemyAction::Sweep)});
  return attacks;
}

BehaviorTree::AttackQueue charge_attacks()
{
  BehaviorTree::AttackQueue attacks;
  attacks.put(Attack{static_cast<int>(EnemyAction::Lunge)});
  return attacks;
}

const StringName & attack_clip(EnemyAction action)
{
  static const StringName CLIPS[] = {"attack_chop", "attack_sweep", "attack_lunge"};
  return CLIPS[static_cast<int>(action)];
}

float damp(float rate, float delta)
{
  return 1.f - Math::exp(-rate * delta);
}
}

SkeletonEnemy::SkeletonEnemy()
  : tree(BehaviorTree::skeleton(melee_attacks(), charge_attacks()))
{
  health = Health(MAX_HEALTH);
}

void SkeletonEnemy::_ready()
{
  ready_target();
  player = Object::cast_to<PlayerController>(get_tree()->get_first_node_in_group("player"));
  model = get_node<Node3D>("Model");
  animator = get_node<AnimationPlayer>("Model/AnimationPlayer");
  hitbox = get_node<ShapeCast3D>("Model/armature_skeleton/Skeleton3D/WeaponBone/Hitbox");
  swing_sound = get_node<AudioStreamPlayer>("Swing");
  spawn_point = last_seen = get_global_position();

  // Placed with a rotation in the scene, which moves to the model as with the player.
  facing_yaw = spawn_yaw = get_rotation().y;
  set_rotation(Vector3());
  model->set_rotation(Vector3(0, facing_yaw, 0));

  const NodePath root_path("armature_skeleton/Skeleton3D:root");
  animator->set_root_motion_track(root_path);
  motion_track = animator->get_animation(attack_clip(EnemyAction::Chop))->find_track(root_path, Animation::TYPE_POSITION_3D);

  MeshInstance3D * body = get_node<MeshInstance3D>("Model/armature_skeleton/Skeleton3D/skeleton");
  const Ref<Mesh> mesh = body->get_mesh();
  for (int surface = 0; surface < mesh->get_surface_count(); ++surface)
  {
    const Ref<StandardMaterial3D> material = mesh->surface_get_material(surface);
    if (material.is_valid() && material->get_name() == "eye_glow")
    {
      eyes = material->duplicate();
      body->set_surface_override_material(surface, eyes);
    }
  }

  // Started apart, so a group placed together does not look and ray on the same tick.
  think_time = UtilityFunctions::randf_range(0.f, THINK_TIME);
  sight_time = UtilityFunctions::randf_range(0.f, SIGHT_TIME);
  circle_gap = UtilityFunctions::randf_range(CIRCLE_GAP_MIN, CIRCLE_GAP_MAX);
  circle_side = UtilityFunctions::randf() < 0.5f ? -1.f : 1.f;
  play(idle_clip, 0.f);
  animator->seek(UtilityFunctions::randf_range(0.f, 4.f));
}

void SkeletonEnemy::_exit_tree()
{
  end_attack();
}

void SkeletonEnemy::_process(double delta)
{
  update_health_bar(static_cast<float>(delta));
  if (eyes.is_valid())
    eyes->set_emission_energy_multiplier(actions.winding_up() ? EYE_FLARE : EYE_REST);
}

void SkeletonEnemy::_physics_process(double delta_time)
{
  const float delta = static_cast<float>(delta_time);
  if (player == nullptr)
    return;
  if (player_respawns != player->respawn_count())
    reset();

  const EnemyAction before = actions.current();
  if (actions.update(delta) && before <= EnemyAction::Lunge)
  {
    end_attack();
    attack_wait = UtilityFunctions::randf_range(WAIT_MIN, WAIT_MAX);
  }
  attack_wait = MAX(attack_wait - delta, 0.f);
  charge_wait = MAX(charge_wait - delta, 0.f);
  circle_time -= delta;

  if (actions.current() == EnemyAction::Dead)
  {
    go_down(delta);
    return;
  }

  rise_time = MAX(rise_time - delta, 0.f);
  think_time -= delta;
  sight_time -= delta;
  if (!actions.busy() && rise_time == 0.f && think_time <= 0.f)
    think();

  Vector3 velocity = get_velocity();
  velocity.y = 0.f;
  if (actions.attacking())
  {
    if (actions.tracking())
      aim_step();
    if (actions.hitting())
      hit_player();
    velocity = root_motion_step(delta).rotated(UP, facing_yaw) * step_scale / delta;
    const EnemyTiming & timing = EnemyActions::timing(actions.current());
    if (actions.elapsed() >= timing.hit_start && actions.elapsed() - delta < timing.hit_start)
      swing_sound->play();
  }
  else if (actions.busy() || rise_time > 0.f)
    velocity = velocity.move_toward(Vector3(), DECELERATION * delta);
  else
  {
    const Vector3 wanted = walk_velocity();
    velocity = velocity.move_toward(wanted, (wanted.is_zero_approx() ? DECELERATION : ACCELERATION) * delta);
    play_locomotion(velocity);
  }

  turn(delta);
  vertical_speed = is_on_floor() ? 0.f : vertical_speed - GRAVITY * delta;
  velocity.y = vertical_speed;
  set_velocity(velocity);
  move_and_slide();
}

void SkeletonEnemy::think()
{
  think_time = THINK_TIME + UtilityFunctions::randf_range(-THINK_JITTER, THINK_JITTER);
  sense();
  const Decision decision = tree.decide(context);
  if (decision.attack_id != BehaviorTree::NO_ATTACK)
  {
    tree.commit(decision);
    start_attack(decision);
    return;
  }
  intent = decision.action;
}

void SkeletonEnemy::sense()
{
  const Vector3 here = get_global_position();
  const Vector3 target = player->get_global_position();
  to_player = target - here;
  const float squared = entity_distance_squared(here, target);
  distance = Math::sqrt(squared);
  context.health_ratio = health.ratio();
  context.range = classify_distance(distance, NEAR_RANGE, MEDIUM_RANGE, RANGE_MARGIN, context.range);

  if (player->is_dead())
  {
    context.aware = false;
    lost_time = 0.f;
    return;
  }

  if (sight_time <= 0.f)
  {
    sight_time = SIGHT_TIME;
    const bool ahead = to_player.slide(UP).normalized().dot(MODEL_FORWARD.rotated(UP, facing_yaw)) > SIGHT_COS;
    const bool can_notice = context.aware || squared < HEARING_RANGE_SQUARED || ahead;
    const bool seen = squared < SIGHT_RANGE_SQUARED && can_notice && sees_player();
    if (seen && !context.aware)
      think_time = UtilityFunctions::randf_range(REACTION_MIN, REACTION_MAX);
    context.aware = context.aware || seen;
    lost_time = seen ? 0.f : lost_time + SIGHT_TIME;
    if (seen)
      last_seen = target;
  }

  context.sees_player = lost_time < LOST_TIME;
  if (lost_time > SEARCH_TIME)
  {
    context.aware = false;
    last_seen = spawn_point;
  }

  context.charge_ready = charge_wait == 0.f && distance >= CHARGE_MIN_RANGE;
  context.can_attack = attack_wait == 0.f && (has_turn || player->attack_turns().available());
}

bool SkeletonEnemy::sees_player() const
{
  const Vector3 from = get_global_position() + CHEST;
  const Vector3 to = player->get_global_position() + CHEST;
  return get_world_3d()->get_direct_space_state()->intersect_ray(PhysicsRayQueryParameters3D::create(from, to, LEVEL_MASK)).is_empty();
}

void SkeletonEnemy::start_attack(const Decision & decision)
{
  const EnemyAction action = static_cast<EnemyAction>(decision.attack_id);
  actions.start(action);
  player->attack_turns().take();
  has_turn = true;
  if (action == EnemyAction::Lunge)
    charge_wait = CHARGE_WAIT;

  hitbox->clear_exceptions();
  motion_animation = animator->get_animation(attack_clip(action));
  aim_step();
  play(attack_clip(action), BLEND_ACTION);
  animator->set_speed_scale(1.f);
}

void SkeletonEnemy::end_attack()
{
  if (has_turn && player != nullptr)
    player->attack_turns().give_back();
  has_turn = false;
}

// Keeps the blow aimed while it can still turn, and bends its step to end by the player.
void SkeletonEnemy::aim_step()
{
  to_player = player->get_global_position() - get_global_position();
  const float length = to_player.slide(UP).length();
  const float clip_step = motion_animation->position_track_interpolate(motion_track, motion_animation->get_length()).length();
  step_scale = PlayerActions::step_scale(length - STRIKE_REACH, clip_step);
}

void SkeletonEnemy::hit_player()
{
  // Asked on each tick, as with the player's weapon: see PlayerController::hit_targets.
  hitbox->force_shapecast_update();
  for (int i = 0; i < hitbox->get_collision_count(); ++i)
  {
    if (Object::cast_to<PlayerController>(hitbox->get_collider(i)) != nullptr)
      player->take_hit(EnemyActions::timing(actions.current()).damage, get_global_position());
    hitbox->add_exception_rid(hitbox->get_collider_rid(i));
  }
}

void SkeletonEnemy::take_hit(int damage, const Vector3 & attacker, const Vector3 & point)
{
  if (health.dead())
    return;

  const Vector3 away = (get_global_position() - attacker).slide(UP).normalized();
  receive_damage(damage, away, point);

  // Being hit gives the attacker away, wherever it came from.
  context.aware = true;
  lost_time = 0.f;
  last_seen = attacker;

  if (health.dead())
  {
    end_attack();
    actions.die();
    down_time = DOWN_TIME;
    remove_from_group("targets");
    set_collision_layer(0);
    set_collision_mask(LEVEL_MASK);
    set_velocity(Vector3());
    animator->set_speed_scale(1.f);
    play(death_clip, BLEND_ACTION);
    return;
  }

  if (actions.hurt())
  {
    end_attack();
    set_velocity(away * HURT_PUSH);
    attack_wait = WAIT_MIN; // Room to punish, or it would answer every stagger with a blow.
    think_time = UtilityFunctions::randf_range(REACTION_MIN, REACTION_MAX);
    animator->set_speed_scale(1.f);
    current_clip = StringName();
    play(hurt_clip, BLEND_ACTION);
  }
}

void SkeletonEnemy::go_down(float delta)
{
  // The bones stay where they fell, and put themselves together again by playing it backwards.
  down_time -= delta;
  if (down_time <= 0.f)
    stand_up();

  vertical_speed = is_on_floor() ? 0.f : vertical_speed - GRAVITY * delta;
  set_velocity(Vector3(0, vertical_speed, 0));
  move_and_slide();
}

void SkeletonEnemy::stand_up()
{
  health.restore();
  actions.revive();
  add_to_group("targets");
  set_collision_layer(BODY_LAYERS);
  set_collision_mask(BODY_MASK);
  context.aware = false;
  lost_time = 0.f;
  intent = BehaviorAction::Watch;
  rise_time = RISE_TIME;
  attack_wait = WAIT_MAX;
  animator->play_backwards(death_clip);
  current_clip = StringName();
}

// The souls rule: dying puts the whole street back, so the player never respawns surrounded.
void SkeletonEnemy::reset()
{
  player_respawns = player->respawn_count();
  end_attack();
  stand_up();
  rise_time = 0.f;
  charge_wait = 0.f;
  set_global_position(spawn_point);
  set_velocity(Vector3());
  last_seen = spawn_point;
  facing_yaw = spawn_yaw;
  model->set_rotation(Vector3(0, facing_yaw, 0));
  animator->set_speed_scale(1.f);
  play(idle_clip, 0.f);
}

Vector3 SkeletonEnemy::root_motion_step(float delta) const
{
  // Read from the curve on each tick, for the reason given in PlayerController::root_motion_step.
  const float now = actions.elapsed();
  return motion_animation->position_track_interpolate(motion_track, now + delta) -
         motion_animation->position_track_interpolate(motion_track, now);
}

Vector3 SkeletonEnemy::walk_velocity() const
{
  Vector3 toward = to_player.slide(UP);
  const float length = toward.length();
  if (length < 0.01f)
    return Vector3();
  toward /= length;

  switch (intent)
  {
    case BehaviorAction::Approach:
      return toward * WALK_SPEED;
    case BehaviorAction::Investigate:
    {
      const Vector3 offset = (last_seen - get_global_position()).slide(UP);
      return offset.length_squared() > ARRIVE_SQUARED ? offset.normalized() * WALK_SPEED : Vector3();
    }
    case BehaviorAction::Circle:
    {
      // Around the player on its own ring, stepping in or out of it as the player moves.
      const Vector3 around = toward.cross(UP) * circle_side;
      const float in_out = CLAMP((length - circle_gap) * CIRCLE_IN_OUT, -1.f, 1.f);
      return (around + toward * in_out).normalized() * CIRCLE_SPEED;
    }
    default:
      return Vector3();
  }
}

void SkeletonEnemy::turn(float delta)
{
  // ponytail: walks straight at its goal, so a car stops it. NavigationAgent3D replaces this
  // when the avenue has a navigation mesh.
  if (actions.attacking() && !actions.tracking())
    return;

  Vector3 facing = to_player;
  if (intent == BehaviorAction::Investigate)
    facing = get_velocity();
  if (intent == BehaviorAction::Watch || actions.current() == EnemyAction::Hurt || facing.slide(UP).is_zero_approx())
    return;

  const float wanted = Math::atan2(facing.x, facing.z);
  const float rate = actions.attacking() ? TRACK_RATE : TURN_RATE;
  facing_yaw = Math::lerp_angle(facing_yaw, wanted, damp(rate, delta));
  model->set_rotation(Vector3(0, facing_yaw, 0));
}

void SkeletonEnemy::play_locomotion(const Vector3 & velocity)
{
  if (intent == BehaviorAction::Circle && circle_time <= 0.f)
  {
    circle_time = UtilityFunctions::randf_range(CIRCLE_SWITCH_MIN, CIRCLE_SWITCH_MAX);
    circle_side = -circle_side;
  }

  const float speed = velocity.length();
  if (speed < MIN_STRIDE)
  {
    play(idle_clip, BLEND_MOVE);
    animator->set_speed_scale(1.f);
    return;
  }

  if (intent != BehaviorAction::Circle)
  {
    play(walk_clip, BLEND_MOVE);
    animator->set_speed_scale(speed / WALK_SPEED);
    return;
  }

  // ponytail: the main one of four directions, as PlayerController::strafe_clip_for does.
  const Vector3 local = velocity.rotated(UP, -facing_yaw);
  if (Math::abs(local.z) >= Math::abs(local.x))
    play(local.z >= 0.f ? walk_clip : walk_back_clip, BLEND_MOVE);
  else
    play(local.x > 0.f ? strafe_left_clip : strafe_right_clip, BLEND_MOVE);
  animator->set_speed_scale(speed / CIRCLE_SPEED);
}

void SkeletonEnemy::play(const StringName & clip, float blend)
{
  if (clip != current_clip)
  {
    animator->play(clip, blend);
    current_clip = clip;
  }
}
