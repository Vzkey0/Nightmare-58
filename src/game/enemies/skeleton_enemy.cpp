#include "skeleton_enemy.hpp"
#include "entity_distance.hpp"
#include <game/player/player_controller.hpp>

#include <game/world/loot_pickup.hpp>

#include <godot_cpp/classes/mesh.hpp>
#include <godot_cpp/classes/mesh_instance3d.hpp>
#include <godot_cpp/classes/packed_scene.hpp>
#include <godot_cpp/classes/physics_direct_space_state3d.hpp>
#include <godot_cpp/classes/physics_ray_query_parameters3d.hpp>
#include <godot_cpp/classes/resource_loader.hpp>
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
constexpr float MIN_PATH_STEP_SQUARED = 0.1f * 0.1f;

constexpr float NEAR_RANGE = 1.9f;
constexpr float MEDIUM_RANGE = 4.4f;
constexpr float RANGE_MARGIN = 0.4f;
constexpr float CHARGE_MIN_RANGE = 2.6f; // The leap needs room, or it lands past the player.
constexpr float STRIKE_REACH = 1.25f;    // Where a blow ends its step, with the blade on the player.

constexpr float WALK_SPEED = 1.4f;   // Must match WALK_SPEED in animate_skeleton.py.
constexpr float CIRCLE_SPEED = 1.1f; // Same, for CIRCLE_SPEED.
constexpr float RUN_SPEED = 3.8f;    // Same, for RUN_SPEED: slower than the player, who can still get away.
constexpr float RUN_FROM = 4.f;      // Farther than this from where it is going, it runs.
constexpr float ACCELERATION = 9.f;
constexpr float DECELERATION = 12.f;
constexpr float CIRCLE_GAP_MIN = 2.5f;
constexpr float CIRCLE_GAP_MAX = 3.7f;
constexpr float CIRCLE_SWITCH_MIN = 1.6f;
constexpr float CIRCLE_SWITCH_MAX = 4.f;
constexpr float CIRCLE_IN_OUT = 1.5f;

// Unaware, it strolls around its post with pauses in between, so it looks and turns like
// something alive and can catch the player from any side.
constexpr float WANDER_RADIUS = 4.f;
constexpr float WANDER_PAUSE_MIN = 2.f;
constexpr float WANDER_PAUSE_MAX = 5.f;
constexpr float WANDER_GIVE_UP = 6.f; // A point it cannot reach is not worth more than this.

constexpr float TURN_RATE = 6.f;
constexpr float TRACK_RATE = 3.2f;

constexpr float WAIT_MIN = 0.5f;
constexpr float WAIT_MAX = 1.4f;
constexpr float CHARGE_WAIT = 6.f;

constexpr float HURT_PUSH = 2.2f;

constexpr int LOCHAS_REWARD = 30;

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

const LootTable & skeleton_loot()
{
  static const LootTable table = [] {
    const ItemCatalog & catalog = ItemCatalog::instance();
    LootTable loot;
    loot.add(NO_ITEM, 75);
    loot.add(ItemCatalog::COFFEE, 2);
    loot.add(ItemCatalog::CANDLE, 8);
    loot.add(catalog.find("gaita_vinyl"), 4);
    loot.add(catalog.find("baseball_card"), 4);
    loot.add(catalog.find("domino_tile"), 5);
    loot.add(catalog.find("family_photo"), 2);
    return loot;
  }();
  return table;
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
  navigator = get_node<NavigationAgent3D>("Navigator");
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
  wander_time = UtilityFunctions::randf_range(0.f, WANDER_PAUSE_MAX);
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
  const float real_delta = static_cast<float>(delta_time);
  if (player == nullptr)
    return;
  if (player_respawns != player->respawn_count())
    reset();

  const int burned = statuses.update(real_delta);
  if (burned > 0)
    burn(burned);
  // Chilled, its own clock runs slow: actions, timers, steps and clips alike.
  const float slow = statuses.slow_scale();
  const float delta = real_delta * slow;
  animator->set_speed_scale(animator->get_speed_scale() / applied_slow);

  const EnemyAction before = actions.current();
  if (actions.update(delta) && before <= EnemyAction::Lunge)
  {
    end_attack();
    attack_wait = UtilityFunctions::randf_range(WAIT_MIN, WAIT_MAX);
  }
  attack_wait = MAX(attack_wait - delta, 0.f);
  charge_wait = MAX(charge_wait - delta, 0.f);
  circle_time -= delta;
  wander_time -= delta;

  if (actions.current() == EnemyAction::Dead)
  {
    applied_slow = 1.f;
    go_down(real_delta);
    return;
  }

  think_time -= delta;
  sight_time -= delta;
  if (!actions.busy() && think_time <= 0.f)
    think();

  Vector3 velocity = get_velocity();
  velocity.y = 0.f;
  if (actions.attacking())
  {
    if (actions.tracking())
      aim_step();
    if (actions.hitting())
      hit_player();
    velocity = root_motion_step(delta).rotated(UP, facing_yaw) * step_scale / real_delta;
    const EnemyTiming & timing = EnemyActions::timing(actions.current());
    if (actions.elapsed() >= timing.hit_start && actions.elapsed() - delta < timing.hit_start)
      swing_sound->play();
  }
  else if (actions.busy())
    velocity = velocity.move_toward(Vector3(), DECELERATION * delta);
  else
  {
    const Vector3 wanted = walk_velocity() * slow;
    velocity = velocity.move_toward(wanted, (wanted.is_zero_approx() ? DECELERATION : ACCELERATION) * delta);
    play_locomotion(velocity);
  }

  turn(delta);
  vertical_speed = is_on_floor() ? 0.f : vertical_speed - GRAVITY * real_delta;
  velocity.y = vertical_speed;
  set_velocity(velocity);
  move_and_slide();

  // Every clip speed set above is for a warm skeleton; the chill scales whichever is playing.
  applied_slow = slow;
  animator->set_speed_scale(animator->get_speed_scale() * slow);
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
  if (intent == BehaviorAction::Watch)
    wander();
  else
    wandering = false;
  if (intent == BehaviorAction::Approach)
    navigator->set_target_position(player->get_global_position());
  else if (intent == BehaviorAction::Investigate)
    navigator->set_target_position(last_seen);
}

void SkeletonEnemy::wander()
{
  if (wandering)
  {
    const bool arrived = (wander_target - get_global_position()).slide(UP).length_squared() < ARRIVE_SQUARED;
    if (arrived || navigator->is_navigation_finished() || wander_time <= 0.f)
    {
      wandering = false;
      wander_time = UtilityFunctions::randf_range(WANDER_PAUSE_MIN, WANDER_PAUSE_MAX);
    }
    return;
  }
  if (wander_time > 0.f)
    return;

  const float angle = UtilityFunctions::randf_range(0.f, 2.f * PI);
  const float radius = UtilityFunctions::randf_range(1.f, WANDER_RADIUS);
  wander_target = spawn_point + Vector3(Math::cos(angle), 0.f, Math::sin(angle)) * radius;
  navigator->set_target_position(wander_target);
  wandering = true;
  wander_time = WANDER_GIVE_UP;
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
    fall();
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

void SkeletonEnemy::fall()
{
  end_attack();
  actions.die();
  statuses.clear();
  pay_the_player();
  remove_from_group("targets");
  set_collision_layer(0);
  set_collision_mask(LEVEL_MASK);
  set_velocity(Vector3());
  animator->set_speed_scale(1.f);
  play(death_clip, BLEND_ACTION);
}

// Fire keeps cutting without a blow: no stagger, and it does not give the player away.
void SkeletonEnemy::burn(int damage)
{
  if (health.dead())
    return;
  receive_damage(damage, Vector3(), get_global_position() + CHEST, true);
  if (health.dead())
    fall();
}

void SkeletonEnemy::pay_the_player()
{
  player->earn(LOCHAS_REWARD);

  const LootTable & loot = skeleton_loot();
  const ItemId item = loot.pick(UtilityFunctions::randi() % loot.total_weight());
  if (item == NO_ITEM)
    return;

  const Ref<PackedScene> scene = ResourceLoader::get_singleton()->load("res://scenes/loot_pickup.tscn");
  LootPickup * pickup = Object::cast_to<LootPickup>(scene->instantiate());
  pickup->set_item_key(ItemCatalog::instance()[item].key);
  get_parent()->add_child(pickup);
  pickup->set_global_position(get_global_position());
}

void SkeletonEnemy::go_down(float delta)
{
  // The bones stay where they fell until the player rests or dies.
  vertical_speed = is_on_floor() ? 0.f : vertical_speed - GRAVITY * delta;
  set_velocity(Vector3(0, vertical_speed, 0));
  move_and_slide();
}

// The souls rule: dying or resting puts the whole street back, so the player never respawns
// surrounded. It is also the only way the fallen get up, which keeps kills from paying twice.
void SkeletonEnemy::reset()
{
  player_respawns = player->respawn_count();
  end_attack();
  health.restore();
  statuses.clear();
  actions.revive();
  add_to_group("targets");
  set_collision_layer(BODY_LAYERS);
  set_collision_mask(BODY_MASK);
  context.aware = false;
  lost_time = 0.f;
  intent = BehaviorAction::Watch;
  wandering = false;
  wander_time = UtilityFunctions::randf_range(0.f, WANDER_PAUSE_MAX);
  attack_wait = WAIT_MAX;
  current_clip = StringName();
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

Vector3 SkeletonEnemy::path_direction()
{
  const Vector3 here = get_global_position();
  Vector3 step = (navigator->get_next_path_position() - here).slide(UP);
  // At the end of the path, or on a scene with no mesh, the agent has nowhere to send it.
  if (step.length_squared() < MIN_PATH_STEP_SQUARED)
    step = (navigator->get_target_position() - here).slide(UP);
  return step.normalized();
}

Vector3 SkeletonEnemy::walk_velocity()
{
  Vector3 toward = to_player.slide(UP);
  const float length = toward.length();
  if (length < 0.01f)
    return Vector3();
  toward /= length;

  switch (intent)
  {
    case BehaviorAction::Watch:
      return wandering ? path_direction() * WALK_SPEED : Vector3();
    case BehaviorAction::Approach:
      return path_direction() * (length > RUN_FROM ? RUN_SPEED : WALK_SPEED);
    case BehaviorAction::Investigate:
    {
      const float left = (last_seen - get_global_position()).slide(UP).length();
      if (left * left <= ARRIVE_SQUARED)
        return Vector3();
      return path_direction() * (left > RUN_FROM ? RUN_SPEED : WALK_SPEED);
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
  if (actions.attacking() && !actions.tracking())
    return;

  Vector3 facing = to_player;
  // Walking around a car it looks where it goes; only a blow keeps its eyes on the player.
  if (!actions.attacking() && intent != BehaviorAction::Circle)
    facing = get_velocity();
  if ((intent == BehaviorAction::Watch && !wandering) || actions.current() == EnemyAction::Hurt || facing.slide(UP).is_zero_approx())
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
    const bool running = speed > (WALK_SPEED + RUN_SPEED) * 0.5f;
    play(running ? run_clip : walk_clip, BLEND_MOVE);
    animator->set_speed_scale(speed / (running ? RUN_SPEED : WALK_SPEED));
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
