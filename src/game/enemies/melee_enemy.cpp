#include "melee_enemy.hpp"
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

#include <initializer_list>

using namespace godot;

namespace
{
const Vector3 UP(0, 1, 0);
const Vector3 MODEL_FORWARD(0, 0, 1);
const Vector3 PLAYER_CHEST(0, 1.2f, 0);
constexpr float PI = static_cast<float>(Math::PI);
constexpr uint32_t LEVEL_MASK = 1;
// The same as the enemy scenes: they block each other, and the player's Hitbox finds them.
constexpr uint32_t BODY_LAYERS = 12;
constexpr uint32_t BODY_MASK = 11;

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

constexpr float RANGE_MARGIN = 0.4f;

constexpr float ACCELERATION = 9.f;
constexpr float DECELERATION = 12.f;
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

constexpr float EYE_REST = 1.3f;
constexpr float EYE_FLARE = 7.f;
const Color CORE_GLOW(1.f, 0.32f, 0.08f);
constexpr float CORE_ENERGY = 4.f;

constexpr float BLEND_MOVE = 0.2f;
constexpr float BLEND_ACTION = 0.1f;
constexpr float MIN_STRIDE = 0.15f;

constexpr MeleeProfile NO_PROFILE{};

template <typename Actions>
BehaviorTree::AttackQueue attacks_of(const Actions & actions)
{
  BehaviorTree::AttackQueue attacks;
  for (const EnemyAction action : actions)
    if (action != EnemyAction::None)
      attacks.put(Attack{static_cast<int>(action)});
  return attacks;
}

const StringName & attack_clip(EnemyAction action)
{
  // In EnemyAction order. The dog's leap has the same clip name as the skeleton's lunge.
  static const StringName CLIPS[] = {"attack_chop",   "attack_sweep",  "attack_lunge", "attack_bite",   "attack_pounce",
                                     "attack_rake",   "attack_snap",   "attack_lunge", "attack_thrash", "attack_maul",
                                     "attack_crunch", "attack_whirl",  "attack_crash", "attack_frenzy", "attack_quake"};
  return CLIPS[static_cast<int>(action)];
}

// Under the Skeleton3D, in the order of the hitbox bits below.
const char * const HITBOX_PATHS[] = {"WeaponBone/Hitbox", "PawBoneL/Hitbox", "PawBoneR/Hitbox", "TailBone/Hitbox", "Slam"};
constexpr int WEAPON = 1;
constexpr int PAWS = 2 | 4;
constexpr int TAIL = 8;
constexpr int SLAM = 16;

int strikes_with(EnemyAction action)
{
  switch (action)
  {
    case EnemyAction::Maul: return PAWS;
    case EnemyAction::Frenzy: return PAWS | WEAPON;
    case EnemyAction::Whirl: return TAIL;
    case EnemyAction::Crash:
    case EnemyAction::Quake: return SLAM;
    default: return WEAPON;
  }
}

float damp(float rate, float delta)
{
  return 1.f - Math::exp(-rate * delta);
}
}

MeleeEnemy::MeleeEnemy()
  : MeleeEnemy(NO_PROFILE)
{
}

MeleeEnemy::MeleeEnemy(const MeleeProfile & profile)
  : profile(profile),
    tree(BehaviorTree::skeleton(attacks_of(profile.fury), attacks_of(profile.melee),
                                attacks_of(std::initializer_list<EnemyAction>{profile.charge})))
{
  health = Health(profile.max_health);
  aim_height = profile.aim_height;
  pinned_bar = profile.boss;
}

void MeleeEnemy::_ready()
{
  ready_target();
  player = Object::cast_to<PlayerController>(get_tree()->get_first_node_in_group("player"));
  model = get_node<Node3D>("Model");
  animator = get_node<AnimationPlayer>("Model/AnimationPlayer");
  const String model_name(profile.model);
  const String skeleton = "Model/armature_" + model_name + String("/Skeleton3D/");
  for (int i = 0; i < HITBOX_COUNT; ++i)
    hitboxes[i] = Object::cast_to<ShapeCast3D>(get_node_or_null(NodePath(skeleton + String(HITBOX_PATHS[i]))));
  dust = Object::cast_to<CPUParticles3D>(get_node_or_null(NodePath(skeleton + String("Slam/Dust"))));
  swing_sound = get_node<AudioStreamPlayer>("Swing");
  navigator = get_node<NavigationAgent3D>("Navigator");
  spawn_point = last_seen = get_global_position();

  // Placed with a rotation in the scene, which moves to the model as with the player.
  facing_yaw = spawn_yaw = get_rotation().y;
  set_rotation(Vector3());
  model->set_rotation(Vector3(0, facing_yaw, 0));

  root_path = NodePath("armature_" + model_name + String("/Skeleton3D:root"));
  animator->set_root_motion_track(root_path);

  MeshInstance3D * body = get_node<MeshInstance3D>(skeleton + model_name);
  const Ref<Mesh> mesh = body->get_mesh();
  for (int surface = 0; surface < mesh->get_surface_count(); ++surface)
  {
    const Ref<StandardMaterial3D> material = mesh->surface_get_material(surface);
    if (material.is_valid() && material->get_name() == "eye_glow")
    {
      eyes = material->duplicate();
      body->set_surface_override_material(surface, eyes);
    }
    else if (material.is_valid() && material->get_name() == "core" && profile.fury_clip != nullptr)
    {
      core = material->duplicate();
      body->set_surface_override_material(surface, core);
    }
  }

  // Started apart, so a group placed together does not look and ray on the same tick.
  think_time = UtilityFunctions::randf_range(0.f, THINK_TIME);
  sight_time = UtilityFunctions::randf_range(0.f, SIGHT_TIME);
  circle_gap = UtilityFunctions::randf_range(profile.circle_gap_min, profile.circle_gap_max);
  circle_side = UtilityFunctions::randf() < 0.5f ? -1.f : 1.f;
  wander_time = UtilityFunctions::randf_range(0.f, WANDER_PAUSE_MAX);
  play(idle_clip, 0.f);
  animator->seek(UtilityFunctions::randf_range(0.f, 4.f));
  if (beaten())
    queue_free();
}

void MeleeEnemy::_exit_tree()
{
  end_attack();
}

void MeleeEnemy::_process(double delta)
{
  update_health_bar(static_cast<float>(delta));
  if (eyes.is_valid())
    eyes->set_emission_energy_multiplier(actions.winding_up() ? EYE_FLARE : EYE_REST);
}

void MeleeEnemy::_physics_process(double delta_time)
{
  const float real_delta = static_cast<float>(delta_time);
  if (player == nullptr)
    return;
  if (player_respawns != player->respawn_count())
    reset();

  const int burned = statuses.update(real_delta);
  if (burned > 0)
    burn(burned);
  // Chilled, its own clock runs slow: actions, timers, steps and clips alike. Fury runs it fast.
  const float slow = statuses.slow_scale() * (enraged ? profile.fury_haste : 1.f);
  const float delta = real_delta * slow;
  animator->set_speed_scale(animator->get_speed_scale() / applied_slow);

  const EnemyAction before = actions.current();
  if (actions.update(delta) && before < EnemyAction::None)
  {
    end_attack();
    attack_wait = UtilityFunctions::randf_range(WAIT_MIN, WAIT_MAX);
  }
  attack_wait = MAX(attack_wait - delta, 0.f);
  charge_wait = MAX(charge_wait - delta, 0.f);
  circle_time -= delta;
  wander_time -= delta;
  alert_time -= delta;

  if (actions.current() == EnemyAction::Dead)
  {
    applied_slow = 1.f;
    go_down(real_delta);
    return;
  }

  think_time -= delta;
  sight_time -= delta;
  if (!actions.busy() && alert_time <= 0.f && think_time <= 0.f)
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
    const int window = actions.window();
    if (window >= 0 && EnemyActions::window_at(EnemyActions::timing(actions.current()), actions.elapsed() - delta) != window)
    {
      swing_sound->play();
      if (dust != nullptr && strikes_with(actions.current()) == SLAM)
        dust->restart();
    }
  }
  else if (actions.busy() || alert_time > 0.f)
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

  // Every clip speed set above is for a warm body; the chill scales whichever is playing.
  applied_slow = slow;
  animator->set_speed_scale(animator->get_speed_scale() * slow);
}

void MeleeEnemy::think()
{
  think_time = THINK_TIME + UtilityFunctions::randf_range(-THINK_JITTER, THINK_JITTER);
  sense();
  if (alert_time > 0.f)
    return;
  if (!enraged && profile.fury_clip != nullptr && context.aware && health.ratio() < BehaviorTree::FURY_HEALTH_RATIO)
  {
    enrage();
    return;
  }
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

void MeleeEnemy::wander()
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

void MeleeEnemy::sense()
{
  const Vector3 here = get_global_position();
  const Vector3 target = player->get_global_position();
  to_player = target - here;
  const float squared = entity_distance_squared(here, target);
  distance = Math::sqrt(squared);
  context.health_ratio = health.ratio();
  context.range = classify_distance(distance, profile.near_range, profile.medium_range, RANGE_MARGIN, context.range);

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
      notice();
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

  fighting = context.aware;
  context.charge_ready = charge_wait == 0.f && distance >= profile.charge_min_range;
  context.can_attack = attack_wait == 0.f && (has_turn || player->attack_turns().available());
}

// The first look at the player: a pause to react, or first a warning if it has one.
void MeleeEnemy::notice()
{
  think_time = UtilityFunctions::randf_range(REACTION_MIN, REACTION_MAX);
  if (profile.alert_clip == nullptr)
    return;
  wandering = false;
  alert_time = animator->get_animation(profile.alert_clip)->get_length();
  play(profile.alert_clip, BLEND_ACTION);
  animator->set_speed_scale(1.f);
}

// Once, the first time it can act below the fury line: a roar, the ribs lit up and the fury pace.
void MeleeEnemy::enrage()
{
  enraged = true;
  alert_time = animator->get_animation(profile.fury_clip)->get_length();
  play(profile.fury_clip, BLEND_ACTION);
  animator->set_speed_scale(1.f);
  if (core.is_valid())
  {
    core->set_feature(BaseMaterial3D::FEATURE_EMISSION, true);
    core->set_emission(CORE_GLOW);
    core->set_emission_energy_multiplier(CORE_ENERGY);
  }
}

// A beaten boss stays beaten: the inflation it froze is what remembers it.
bool MeleeEnemy::beaten() const
{
  return profile.boss && player != nullptr && player->progress().inflation_frozen(profile.zone);
}

bool MeleeEnemy::sees_player() const
{
  const Vector3 from = aim_point();
  const Vector3 to = player->get_global_position() + PLAYER_CHEST;
  return get_world_3d()->get_direct_space_state()->intersect_ray(PhysicsRayQueryParameters3D::create(from, to, LEVEL_MASK)).is_empty();
}

void MeleeEnemy::start_attack(const Decision & decision)
{
  const EnemyAction action = static_cast<EnemyAction>(decision.attack_id);
  actions.start(action);
  player->attack_turns().take();
  has_turn = true;
  if (action == profile.charge)
    charge_wait = CHARGE_WAIT;

  struck_window = -1;
  motion_animation = animator->get_animation(attack_clip(action));
  motion_track = motion_animation->find_track(root_path, Animation::TYPE_POSITION_3D);
  aim_step();
  play(attack_clip(action), BLEND_ACTION);
  animator->set_speed_scale(1.f);
}

void MeleeEnemy::end_attack()
{
  if (has_turn && player != nullptr)
    player->attack_turns().give_back();
  has_turn = false;
}

// Keeps the blow aimed while it can still turn, and bends its step to end by the player.
void MeleeEnemy::aim_step()
{
  to_player = player->get_global_position() - get_global_position();
  const float length = to_player.slide(UP).length();
  const float clip_step = motion_animation->position_track_interpolate(motion_track, motion_animation->get_length()).length();
  step_scale = PlayerActions::step_scale(length - profile.strike_reach, clip_step);
}

void MeleeEnemy::hit_player()
{
  // One hit per blow, whichever hitbox lands it. Asked on each tick, as with the player's weapon:
  // see PlayerController::hit_targets.
  const int window = actions.window();
  if (window == struck_window)
    return;
  const int strikes = strikes_with(actions.current());
  for (int i = 0; i < HITBOX_COUNT; ++i)
  {
    ShapeCast3D * hitbox = hitboxes[i];
    if ((strikes & (1 << i)) == 0 || hitbox == nullptr)
      continue;
    hitbox->force_shapecast_update();
    for (int k = 0; k < hitbox->get_collision_count(); ++k)
      if (Object::cast_to<PlayerController>(hitbox->get_collider(k)) != nullptr)
      {
        player->take_hit(EnemyActions::timing(actions.current()).damage, get_global_position());
        struck_window = window;
        return;
      }
  }
}

void MeleeEnemy::take_hit(int damage, const Vector3 & attacker, const Vector3 & point)
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

  if (!profile.boss && actions.hurt())
  {
    end_attack();
    alert_time = 0.f;
    set_velocity(away * HURT_PUSH);
    attack_wait = WAIT_MIN; // Room to punish, or it would answer every stagger with a blow.
    think_time = UtilityFunctions::randf_range(REACTION_MIN, REACTION_MAX);
    animator->set_speed_scale(1.f);
    current_clip = StringName();
    play(hurt_clip, BLEND_ACTION);
  }
}

void MeleeEnemy::fall()
{
  if (profile.boss)
    player->freeze_inflation(profile.zone);
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
void MeleeEnemy::burn(int damage)
{
  if (health.dead())
    return;
  receive_damage(damage, Vector3(), aim_point(), true);
  if (health.dead())
    fall();
}

void MeleeEnemy::pay_the_player()
{
  player->earn(profile.reward);

  const LootTable & table = profile.loot();
  const ItemId item = table.pick(UtilityFunctions::randi() % table.total_weight());
  if (item == NO_ITEM)
    return;

  const Ref<PackedScene> scene = ResourceLoader::get_singleton()->load("res://scenes/loot_pickup.tscn");
  LootPickup * pickup = Object::cast_to<LootPickup>(scene->instantiate());
  pickup->set_item_key(ItemCatalog::instance()[item].key);
  get_parent()->add_child(pickup);
  pickup->set_global_position(get_global_position());
}

void MeleeEnemy::go_down(float delta)
{
  // The body stays where it fell until the player rests or dies.
  vertical_speed = is_on_floor() ? 0.f : vertical_speed - GRAVITY * delta;
  set_velocity(Vector3(0, vertical_speed, 0));
  move_and_slide();
}

// The souls rule: dying or resting puts the whole street back, so the player never respawns
// surrounded. It is also the only way the fallen get up, which keeps kills from paying twice.
void MeleeEnemy::reset()
{
  if (beaten())
  {
    queue_free();
    return;
  }
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
  alert_time = 0.f;
  fighting = false;
  enraged = false;
  if (core.is_valid())
    core->set_feature(BaseMaterial3D::FEATURE_EMISSION, false);
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

Vector3 MeleeEnemy::root_motion_step(float delta) const
{
  // Read from the curve on each tick, for the reason given in PlayerController::root_motion_step.
  const float now = actions.elapsed();
  return motion_animation->position_track_interpolate(motion_track, now + delta) -
         motion_animation->position_track_interpolate(motion_track, now);
}

Vector3 MeleeEnemy::path_direction()
{
  const Vector3 here = get_global_position();
  Vector3 step = (navigator->get_next_path_position() - here).slide(UP);
  // At the end of the path, or on a scene with no mesh, the agent has nowhere to send it.
  if (step.length_squared() < MIN_PATH_STEP_SQUARED)
    step = (navigator->get_target_position() - here).slide(UP);
  return step.normalized();
}

Vector3 MeleeEnemy::walk_velocity()
{
  Vector3 toward = to_player.slide(UP);
  const float length = toward.length();
  if (length < 0.01f)
    return Vector3();
  toward /= length;

  switch (intent)
  {
    case BehaviorAction::Watch:
      return wandering ? path_direction() * profile.walk_speed : Vector3();
    case BehaviorAction::Approach:
      return path_direction() * (length > profile.run_from ? profile.run_speed : profile.walk_speed);
    case BehaviorAction::Investigate:
    {
      const float left = (last_seen - get_global_position()).slide(UP).length();
      if (left * left <= ARRIVE_SQUARED)
        return Vector3();
      return path_direction() * (left > profile.run_from ? profile.run_speed : profile.walk_speed);
    }
    case BehaviorAction::Circle:
    {
      // Around the player on its own ring, stepping in or out of it as the player moves.
      const Vector3 around = toward.cross(UP) * circle_side;
      const float in_out = CLAMP((length - circle_gap) * CIRCLE_IN_OUT, -1.f, 1.f);
      return (around + toward * in_out).normalized() * profile.circle_speed;
    }
    default:
      return Vector3();
  }
}

void MeleeEnemy::turn(float delta)
{
  if (actions.attacking() && !actions.tracking())
    return;

  Vector3 facing = to_player;
  // Walking around a car it looks where it goes; only a blow or a warning keeps its eyes on the player.
  const bool alerting = alert_time > 0.f;
  if (!actions.attacking() && intent != BehaviorAction::Circle && !alerting)
    facing = get_velocity();
  if ((intent == BehaviorAction::Watch && !wandering && !alerting) || actions.current() == EnemyAction::Hurt || facing.slide(UP).is_zero_approx())
    return;

  const float wanted = Math::atan2(facing.x, facing.z);
  const float rate = actions.attacking() ? TRACK_RATE : TURN_RATE;
  facing_yaw = Math::lerp_angle(facing_yaw, wanted, damp(rate, delta));
  model->set_rotation(Vector3(0, facing_yaw, 0));
}

void MeleeEnemy::play_locomotion(const Vector3 & velocity)
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
    const bool running = speed > (profile.walk_speed + profile.run_speed) * 0.5f;
    play(running ? run_clip : walk_clip, BLEND_MOVE);
    animator->set_speed_scale(speed / (running ? profile.run_speed : profile.walk_speed));
    return;
  }

  // ponytail: the main one of four directions, as PlayerController::strafe_clip_for does.
  const Vector3 local = velocity.rotated(UP, -facing_yaw);
  const bool back = local.z < 0.f && Math::abs(local.z) >= Math::abs(local.x);
  if (Math::abs(local.z) >= Math::abs(local.x))
    play(back ? walk_back_clip : walk_clip, BLEND_MOVE);
  else
    play(local.x > 0.f ? strafe_left_clip : strafe_right_clip, BLEND_MOVE);
  animator->set_speed_scale(speed / (back ? profile.back_speed : profile.circle_speed));
}

void MeleeEnemy::play(const StringName & clip, float blend)
{
  if (clip != current_clip)
  {
    animator->play(clip, blend);
    current_clip = clip;
  }
}
