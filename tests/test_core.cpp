#undef NDEBUG
#include <cassert>
#include <utility>

#include <sort.hpp>

#include <core/ai/attack_turns.hpp>
#include <core/ai/behavior_tree.hpp>
#include <core/ai/enemy_actions.hpp>
#include <core/distance.hpp>
#include <core/health.hpp>
#include <core/health_trail.hpp>
#include <core/lock_on.hpp>
#include <core/menu_stack.hpp>
#include <core/player/player_actions.hpp>
#include <core/player/rage.hpp>
#include <core/player/thrown_weapon.hpp>
#include <core/progression/inflation.hpp>
#include <core/progression/inventory.hpp>
#include <core/progression/item_catalog.hpp>
#include <core/progression/machete_skills.hpp>
#include <core/progression/loot_table.hpp>
#include <core/progression/player_progress.hpp>
#include <core/progression/quick_slots.hpp>
#include <core/progression/skill_tree.hpp>
#include <core/stamina.hpp>
#include <core/status_effects.hpp>

static void test_skill_tree()
{
  SkillTree tree(1);
  assert(tree.is_unlocked(1));

  assert(tree.add(1, 2, 3));
  assert(tree.add(1, 3, 1));
  assert(tree.add(2, 4, 2));
  assert(!tree.add(99, 5, 1));
  assert(!tree.add(1, 2, 1));

  int points = 5;
  assert(!tree.unlock(4, points));
  assert(!tree.unlock(99, points));
  assert(points == 5);

  assert(tree.unlock(2, points));
  assert(tree.is_unlocked(2));
  assert(points == 2);
  assert(!tree.unlock(2, points));
  assert(points == 2);

  assert(tree.unlock(4, points));
  assert(points == 0);
  assert(!tree.unlock(3, points));
  assert(!tree.is_unlocked(3));
}

static BehaviorTree::AttackQueue make_attacks(int id)
{
  BehaviorTree::AttackQueue attacks;
  attacks.put(Attack{id});
  return attacks;
}

static bool decides(const BehaviorTree & tree, float health, DistanceRange range,
                    BehaviorAction action, int attack_id)
{
  const Decision decision = tree.decide(EnemyContext{health, range});
  return decision.action == action && decision.attack_id == attack_id;
}

static void test_behavior_tree_priorities()
{
  BehaviorTree tree(make_attacks(1), make_attacks(2), make_attacks(3), make_attacks(4));

  assert(decides(tree, 0.2f, DistanceRange::Near, BehaviorAction::Fury, 1));
  assert(decides(tree, 0.2f, DistanceRange::Far, BehaviorAction::Fury, 1));
  assert(decides(tree, 0.8f, DistanceRange::Near, BehaviorAction::Melee, 2));
  assert(decides(tree, 0.8f, DistanceRange::Medium, BehaviorAction::Ranged, 3));
  assert(decides(tree, 0.8f, DistanceRange::Far, BehaviorAction::Charge, 4));

  // The limit is strict: exactly 30 % is not low health.
  assert(decides(tree, 0.3f, DistanceRange::Near, BehaviorAction::Melee, 2));
}

static void test_behavior_tree_rotation()
{
  BehaviorTree::AttackQueue melee = make_attacks(1);
  melee.put(Attack{2});
  BehaviorTree tree(make_attacks(9), melee, make_attacks(9), make_attacks(9));

  const EnemyContext context{0.8f, DistanceRange::Near};
  assert(tree.decide(context).attack_id == 1);
  assert(tree.decide(context).attack_id == 1);

  tree.commit(tree.decide(context));
  assert(tree.decide(context).attack_id == 2);

  tree.commit(tree.decide(context));
  assert(tree.decide(context).attack_id == 1);
}

static void test_behavior_tree_empty_queues()
{
  const BehaviorTree::AttackQueue none;
  BehaviorTree tree(none, make_attacks(2), none, none);

  // Without that attack, each branch gives way to the next option.
  assert(decides(tree, 0.2f, DistanceRange::Near, BehaviorAction::Melee, 2));
  assert(decides(tree, 0.8f, DistanceRange::Medium, BehaviorAction::Approach,
                 BehaviorTree::NO_ATTACK));
  assert(decides(tree, 0.8f, DistanceRange::Far, BehaviorAction::None,
                 BehaviorTree::NO_ATTACK));

  const Decision approach = tree.decide(EnemyContext{0.8f, DistanceRange::Medium});
  tree.commit(approach);
  tree.commit(tree.decide(EnemyContext{0.8f, DistanceRange::Far}));
  assert(tree.decide(EnemyContext{0.8f, DistanceRange::Near}).attack_id == 2);
}

static void test_skeleton_tree()
{
  BehaviorTree::AttackQueue melee = make_attacks(1);
  melee.put(Attack{2});
  BehaviorTree tree = BehaviorTree::skeleton(melee, make_attacks(3));

  EnemyContext context{1.f, DistanceRange::Near};
  assert(tree.decide(context).action == BehaviorAction::Melee);
  assert(tree.decide(context).attack_id == 1);
  tree.commit(tree.decide(context));
  assert(tree.decide(context).attack_id == 2);

  context.range = DistanceRange::Medium;
  assert(tree.decide(context).action == BehaviorAction::Charge);
  context.charge_ready = false;
  assert(tree.decide(context).action == BehaviorAction::Approach);

  // Without a turn it never attacks, however close: it circles.
  context.can_attack = false;
  assert(tree.decide(context).action == BehaviorAction::Circle);
  context.range = DistanceRange::Near;
  assert(tree.decide(context).action == BehaviorAction::Circle);
  context.range = DistanceRange::Far;
  assert(tree.decide(context).action == BehaviorAction::Approach);

  context.sees_player = false;
  assert(tree.decide(context).action == BehaviorAction::Investigate);
  context.aware = false;
  assert(tree.decide(context).action == BehaviorAction::Watch);
}

static void test_distance_margin()
{
  // Entering a range uses the plain limit; leaving it needs the margin too.
  assert(classify_distance(2.1f, 2.f, 4.f, 0.4f, DistanceRange::Medium) == DistanceRange::Medium);
  assert(classify_distance(2.1f, 2.f, 4.f, 0.4f, DistanceRange::Near) == DistanceRange::Near);
  assert(classify_distance(2.5f, 2.f, 4.f, 0.4f, DistanceRange::Near) == DistanceRange::Medium);
  assert(classify_distance(4.1f, 2.f, 4.f, 0.4f, DistanceRange::Far) == DistanceRange::Far);
  assert(classify_distance(4.1f, 2.f, 4.f, 0.4f, DistanceRange::Medium) == DistanceRange::Medium);
  assert(classify_distance(4.1f, 2.f, 4.f, 0.4f, DistanceRange::Near) == DistanceRange::Medium);
}

static void test_attack_turns()
{
  AttackTurns turns;
  assert(turns.available());
  turns.take();
  assert(!turns.available()); // Attacks never start together.
  turns.update(AttackTurns::GAP);
  assert(turns.available());
  turns.take();
  turns.update(AttackTurns::GAP);
  assert(!turns.available()); // Full.
  turns.give_back();
  assert(turns.available());
}

static void run_enemy(EnemyActions & actions, float seconds)
{
  for (float time = 0.f; time < seconds; time += 1.f / 60.f)
    actions.update(1.f / 60.f);
}

static void test_enemy_attack()
{
  const EnemyTiming & chop = EnemyActions::timing(EnemyAction::Chop);
  assert(chop.track_end < chop.hit_start && chop.hit_start < chop.hit_end && chop.hit_end < chop.duration);

  EnemyActions actions;
  assert(!actions.busy());
  actions.start(EnemyAction::Chop);
  assert(actions.busy() && actions.tracking() && actions.winding_up() && !actions.hitting());

  run_enemy(actions, chop.track_end + 0.02f);
  assert(!actions.tracking() && actions.winding_up());
  run_enemy(actions, chop.hit_start - chop.track_end + 0.02f);
  assert(actions.hitting());

  bool ended = false;
  for (float time = 0.f; time < chop.duration; time += 1.f / 60.f)
    ended = actions.update(1.f / 60.f) || ended;
  assert(ended && !actions.busy());
}

static void test_enemy_stagger()
{
  const EnemyTiming & chop = EnemyActions::timing(EnemyAction::Chop);
  EnemyActions actions;

  // A blow during the windup stops the attack.
  actions.start(EnemyAction::Chop);
  assert(actions.hurt());
  assert(actions.current() == EnemyAction::Hurt && !actions.attacking());

  // The next ones in the combo only do damage, so it cannot be locked in place.
  assert(!actions.hurt());
  run_enemy(actions, EnemyActions::STAGGER_GUARD + 0.02f);
  assert(!actions.busy());

  // The swing itself cannot be stopped.
  actions.start(EnemyAction::Chop);
  run_enemy(actions, chop.hit_start + 0.02f);
  assert(!actions.hurt());
  assert(actions.current() == EnemyAction::Chop);

  actions.die();
  assert(!actions.hurt());
  run_enemy(actions, 10.f);
  assert(actions.current() == EnemyAction::Dead);
  actions.revive();
  assert(!actions.busy());
}

static constexpr float STEP = 1.f / 60.f;

static void advance(PlayerActions & actions, float seconds, bool moving = false)
{
  for (float time = 0.f; time < seconds; time += STEP)
    actions.update(STEP, moving);
}

static void test_player_action_lifetime()
{
  PlayerActions actions;
  assert(!actions.update(STEP, false));
  assert(actions.current() == PlayerAction::None);

  actions.press(PlayerAction::Dodge);
  assert(actions.update(STEP, false));
  assert(actions.current() == PlayerAction::Dodge);

  const ActionTiming & timing = PlayerActions::timing(PlayerAction::Dodge);
  advance(actions, timing.duration - 0.1f);
  assert(actions.current() == PlayerAction::Dodge);
  advance(actions, 0.2f);
  assert(actions.current() == PlayerAction::None);
}

static void test_player_action_buffer()
{
  const ActionTiming & timing = PlayerActions::timing(PlayerAction::Dodge);

  PlayerActions chained;
  chained.press(PlayerAction::Dodge);
  chained.update(STEP, false);
  advance(chained, timing.next_action - 0.2f);
  chained.press(PlayerAction::Attack);
  advance(chained, 0.1f);
  assert(chained.current() == PlayerAction::Dodge);
  advance(chained, 0.2f);
  assert(chained.current() == PlayerAction::RollAttack);

  // A press from too long ago is no longer what the player wants.
  PlayerActions stale;
  stale.press(PlayerAction::Dodge);
  stale.update(STEP, false);
  stale.press(PlayerAction::Attack);
  advance(stale, PlayerActions::BUFFER_TIME + 0.1f);
  advance(stale, 1.f);
  assert(stale.current() == PlayerAction::None);

  // With a full buffer the oldest press gives way to the newest.
  PlayerActions full;
  full.press(PlayerAction::Dodge);
  full.update(STEP, false);
  full.press(PlayerAction::Dodge);
  full.press(PlayerAction::Dodge);
  full.press(PlayerAction::Attack);
  advance(full, 0.45f);
  full.press(PlayerAction::Attack);
  advance(full, timing.next_action - 0.45f + 0.02f);
  assert(full.current() == PlayerAction::RollAttack);

  // A dodge does not wait behind attacks already queued.
  PlayerActions mashed;
  mashed.press(PlayerAction::Attack);
  mashed.update(STEP, false);
  mashed.press(PlayerAction::Attack);
  mashed.press(PlayerAction::Dodge);
  advance(mashed, PlayerActions::timing(PlayerAction::Attack).dodge_cancel + STEP);
  assert(mashed.current() == PlayerAction::Dodge);
}

static void test_player_dodge_cancel()
{
  for (const PlayerAction blow : {PlayerAction::Attack, PlayerAction::Attack2, PlayerAction::Attack3, PlayerAction::RollAttack, PlayerAction::RunAttack})
  {
    const ActionTiming & timing = PlayerActions::timing(blow);
    // The swing always finishes first, and a dodge comes before the next blow can.
    assert(timing.dodge_cancel >= timing.hit_end);
    assert(timing.dodge_cancel < timing.next_action);
  }

  const ActionTiming & timing = PlayerActions::timing(PlayerAction::Attack);
  PlayerActions actions;
  actions.press(PlayerAction::Attack);
  actions.update(STEP, false);
  advance(actions, timing.dodge_cancel - 3.f * STEP);
  actions.press(PlayerAction::Dodge);
  actions.update(STEP, false);
  assert(actions.current() == PlayerAction::Attack);
  advance(actions, 4.f * STEP);
  assert(actions.current() == PlayerAction::Dodge);

  // An attack still waits for next_action.
  PlayerActions chain;
  chain.press(PlayerAction::Attack);
  chain.update(STEP, false);
  advance(chain, timing.dodge_cancel);
  chain.press(PlayerAction::Attack);
  chain.update(STEP, false);
  assert(chain.current() == PlayerAction::Attack);
}

static void test_player_step_scale()
{
  assert(PlayerActions::step_scale(1.f, 1.f) == 1.f);
  assert(PlayerActions::step_scale(0.5f, 1.f) == 0.5f);
  assert(PlayerActions::step_scale(-2.f, 1.f) == PlayerActions::MIN_STEP_SCALE);
  assert(PlayerActions::step_scale(9.f, 1.f) == PlayerActions::MAX_STEP_SCALE);
}

static void test_player_move_cancel()
{
  const ActionTiming & timing = PlayerActions::timing(PlayerAction::Attack);

  PlayerActions actions;
  actions.press(PlayerAction::Attack);
  actions.update(STEP, true);
  advance(actions, timing.move_cancel - 0.1f, true);
  assert(actions.current() == PlayerAction::Attack);
  advance(actions, 0.2f, true);
  assert(actions.current() == PlayerAction::None);
}

static void chain_attack(PlayerActions & actions)
{
  const float wait = PlayerActions::timing(actions.current()).next_action - actions.elapsed();
  advance(actions, wait - 0.1f);
  actions.press(PlayerAction::Attack);
  advance(actions, 0.1f + 2.f * STEP);
}

static void test_player_combo()
{
  PlayerActions actions;
  assert(actions.combo_step() == PlayerActions::NO_COMBO_STEP);

  actions.press(PlayerAction::Attack);
  actions.update(STEP, false);
  assert(actions.current() == PlayerAction::Attack);
  assert(actions.combo_step() == 0);

  chain_attack(actions);
  assert(actions.current() == PlayerAction::Attack2);
  assert(actions.combo_step() == 1);

  chain_attack(actions);
  assert(actions.current() == PlayerAction::Attack3);
  assert(actions.combo_step() == 2);

  // The last blow is the strongest and the slowest to recover from.
  const ActionTiming & last = PlayerActions::timing(PlayerAction::Attack3);
  assert(last.damage > PlayerActions::timing(PlayerAction::Attack).damage);
  assert(last.next_action > PlayerActions::timing(PlayerAction::Attack).next_action);

  chain_attack(actions);
  assert(actions.current() == PlayerAction::Attack);

  // Letting a step end starts over.
  PlayerActions ended;
  ended.press(PlayerAction::Attack);
  ended.update(STEP, false);
  chain_attack(ended);
  advance(ended, PlayerActions::timing(PlayerAction::Attack2).duration);
  assert(ended.current() == PlayerAction::None);
  ended.press(PlayerAction::Attack);
  ended.update(STEP, false);
  assert(ended.current() == PlayerAction::Attack);

  PlayerActions dodged;
  dodged.press(PlayerAction::Attack);
  dodged.update(STEP, false);
  advance(dodged, PlayerActions::timing(PlayerAction::Attack).next_action);
  dodged.press(PlayerAction::Dodge);
  dodged.update(STEP, false);
  assert(dodged.current() == PlayerAction::Dodge);
  advance(dodged, PlayerActions::timing(PlayerAction::Dodge).next_action);
  dodged.press(PlayerAction::Attack);
  dodged.update(STEP, false);

  // The roll keeps the combo's place: its attack comes in between, and the combo carries on.
  assert(dodged.current() == PlayerAction::RollAttack);
  assert(dodged.combo_step() == PlayerActions::NO_COMBO_STEP);
  assert(dodged.stepping_attack());
  chain_attack(dodged);
  assert(dodged.current() == PlayerAction::Attack2);

  // Letting the roll finish starts over.
  PlayerActions rolled;
  rolled.press(PlayerAction::Attack);
  rolled.update(STEP, false);
  advance(rolled, PlayerActions::timing(PlayerAction::Attack).next_action);
  rolled.press(PlayerAction::Dodge);
  rolled.update(STEP, false);
  advance(rolled, PlayerActions::timing(PlayerAction::Dodge).duration + 0.1f);
  assert(rolled.current() == PlayerAction::None);
  rolled.press(PlayerAction::Attack);
  rolled.update(STEP, false);
  assert(rolled.current() == PlayerAction::Attack);
}

static void test_player_run_attack()
{
  // Only a real sprint counts: a held button without moving, or a tap, stays a normal attack.
  PlayerActions sprinting;
  for (float time = 0.f; time < PlayerActions::TAP_TIME + 0.1f; time += STEP)
    sprinting.update_dodge_button(true, STEP);
  sprinting.press(PlayerAction::Attack);
  sprinting.update(STEP, true);
  assert(sprinting.current() == PlayerAction::RunAttack);
  assert(sprinting.stepping_attack());
  assert(sprinting.combo_step() == PlayerActions::NO_COMBO_STEP);

  // The combo starts over after it.
  chain_attack(sprinting);
  assert(sprinting.current() == PlayerAction::Attack);

  PlayerActions standing;
  for (float time = 0.f; time < PlayerActions::TAP_TIME + 0.1f; time += STEP)
    standing.update_dodge_button(true, STEP);
  standing.press(PlayerAction::Attack);
  standing.update(STEP, false);
  assert(standing.current() == PlayerAction::Attack);

  PlayerActions tapped;
  tapped.update_dodge_button(true, STEP);
  tapped.press(PlayerAction::Attack);
  tapped.update(STEP, true);
  assert(tapped.current() == PlayerAction::Attack);
}

static void test_player_dodge_button()
{
  PlayerActions tap;
  tap.update_dodge_button(true, STEP);
  tap.update_dodge_button(false, STEP);
  assert(!tap.sprinting());
  assert(tap.update(STEP, false));
  assert(tap.current() == PlayerAction::Dodge);

  PlayerActions hold;
  hold.update_dodge_button(true, STEP);
  assert(hold.sprinting());
  for (float time = 0.f; time < PlayerActions::TAP_TIME + 0.1f; time += STEP)
    hold.update_dodge_button(true, STEP);
  assert(hold.sprinting());
  hold.update_dodge_button(false, STEP);
  assert(!hold.sprinting());
  assert(!hold.update(STEP, false));
}

static void test_player_air_rules()
{
  PlayerActions air;
  air.press(PlayerAction::Attack);
  assert(air.update(STEP, false, false));
  assert(air.current() == PlayerAction::AirAttack);

  // Landing right after the press must not cut the swing.
  const ActionTiming & timing = PlayerActions::timing(PlayerAction::AirAttack);
  while (air.elapsed() < timing.hit_start)
  {
    air.update(STEP, false, true);
    assert(air.current() == PlayerAction::AirAttack);
  }
  air.update(STEP, false, true);
  assert(air.hitting());
  for (float time = 0.f; time < timing.duration; time += STEP)
    air.update(STEP, false, true);
  assert(air.current() == PlayerAction::None);

  PlayerActions waits;
  waits.press(PlayerAction::Dodge);
  assert(!waits.update(STEP, false, false));
  assert(waits.update(STEP, false, true));
  assert(waits.current() == PlayerAction::Dodge);
}

static void test_player_hit_window()
{
  const ActionTiming & timing = PlayerActions::timing(PlayerAction::Attack);

  PlayerActions attack;
  assert(!attack.hitting());
  attack.press(PlayerAction::Attack);
  attack.update(STEP, false);
  assert(!attack.hitting());
  advance(attack, timing.hit_start + STEP);
  assert(attack.hitting());
  advance(attack, timing.hit_end - timing.hit_start);
  assert(!attack.hitting());

  PlayerActions dodge;
  dodge.press(PlayerAction::Dodge);
  dodge.update(STEP, false);
  for (float time = 0.f; time < 1.f; time += STEP)
  {
    dodge.update(STEP, false);
    assert(!dodge.hitting());
  }
}

static void test_player_ground_hit()
{
  // Only actions that land report it, and the clock keeps running after an action ends.
  PlayerActions jump;
  jump.press(PlayerAction::Jump);
  jump.update(STEP, false);
  for (float time = 0.f; time < 1.f; time += STEP)
  {
    jump.update(STEP, false);
    assert(!jump.hit_ground(STEP));
  }
  assert(jump.current() == PlayerAction::None);

  PlayerActions roll;
  roll.press(PlayerAction::Dodge);
  roll.update(STEP, false);
  int landings = 0;
  for (float time = 0.f; time < 1.5f; time += STEP)
  {
    roll.update(STEP, false);
    landings += roll.hit_ground(STEP) ? 1 : 0;
  }
  assert(landings == 1);
}

static void test_health()
{
  Health health(50);
  health.damage(20);
  assert(health.value() == 30);
  assert(!health.dead());

  health.damage(40);
  assert(health.value() == 0);
  assert(health.dead());

  health.restore();
  assert(health.value() == 50);

  health.damage(25);
  assert(health.ratio() == 0.5f);
}

static void test_stamina()
{
  Stamina stamina(100.f);
  stamina.spend(30.f);
  assert(stamina.ratio() == 0.7f);

  // Nothing comes back during an action or right after one.
  stamina.update(1.f, false);
  assert(stamina.ratio() == 0.7f);
  stamina.update(Stamina::REGEN_DELAY, true);
  assert(stamina.ratio() == 0.7f);
  stamina.update(STEP, true);
  assert(stamina.ratio() > 0.7f);

  stamina.spend(1000.f);
  assert(stamina.ratio() == 0.f);
  assert(!stamina.can_act());
  assert(stamina.winded());

  // Actions are back with the first sliver, the sprint only with a share of the bar.
  stamina.update(Stamina::REGEN_DELAY, true);
  stamina.update(STEP, true);
  assert(stamina.can_act());
  assert(stamina.winded());
  for (float time = 0.f; time < 1.f; time += STEP)
    stamina.update(STEP, true);
  assert(!stamina.winded());
}

static void test_player_stamina()
{
  // The last action comes out with whatever is left, and the next press has to wait.
  PlayerActions actions;
  const float full = PlayerActions::MAX_STAMINA;
  for (float spent = 0.f; spent < full; spent += PlayerActions::timing(PlayerAction::Dodge).stamina_cost)
  {
    actions.press(PlayerAction::Dodge);
    actions.update(STEP, false);
    assert(actions.current() == PlayerAction::Dodge);
    advance(actions, PlayerActions::timing(PlayerAction::Dodge).next_action);
  }
  assert(actions.stamina_ratio() == 0.f);
  actions.press(PlayerAction::Attack);
  assert(!actions.update(STEP, false));

  // A sprint drains the bar and ends by itself; only moving counts.
  PlayerActions sprint;
  const auto hold = [&sprint](float seconds, bool moving) {
    for (float time = 0.f; time < seconds; time += STEP)
    {
      sprint.update_dodge_button(true, STEP);
      sprint.update(STEP, moving);
    }
  };
  hold(1.f, false);
  assert(sprint.stamina_ratio() == 1.f);
  hold(1.f, true);
  assert(sprint.stamina_ratio() < 1.f);
  assert(sprint.sprinting());
  hold(full / PlayerActions::SPRINT_COST, true);
  assert(sprint.winded());
  assert(!sprint.sprinting());
}

static void test_player_hurt()
{
  const ActionTiming & roll = PlayerActions::timing(PlayerAction::Dodge);

  PlayerActions rolling;
  assert(!rolling.invulnerable());
  rolling.press(PlayerAction::Dodge);
  rolling.update(STEP, false);
  assert(rolling.invulnerable());
  advance(rolling, PlayerActions::DODGE_SAFE_TIME);
  assert(!rolling.invulnerable());
  assert(rolling.current() == PlayerAction::Dodge);
  assert(PlayerActions::DODGE_SAFE_TIME < roll.ground_hit);

  // A hit cancels the action and what was queued, and cannot land twice in a row.
  PlayerActions hit;
  hit.press(PlayerAction::Attack);
  hit.update(STEP, false);
  hit.press(PlayerAction::Attack);
  hit.hurt();
  assert(hit.current() == PlayerAction::Hurt);
  assert(hit.invulnerable());
  advance(hit, PlayerActions::timing(PlayerAction::Hurt).duration + 0.1f);
  assert(hit.current() == PlayerAction::None);

  PlayerActions dead;
  dead.press(PlayerAction::Dodge);
  dead.update(STEP, false);
  dead.die();
  dead.press(PlayerAction::Attack);
  advance(dead, 30.f, true);
  assert(dead.current() == PlayerAction::Dead);
  dead.revive();
  assert(dead.current() == PlayerAction::None);
  assert(dead.stamina_ratio() == 1.f);
}

static void test_player_heavy_attack()
{
  const ActionTiming & heavy = PlayerActions::timing(PlayerAction::HeavyAttack);
  assert(heavy.damage > PlayerActions::timing(PlayerAction::Attack3).damage);
  assert(heavy.dodge_cancel >= heavy.hit_end);
  assert(heavy.dodge_cancel < heavy.next_action);

  // It breaks the combo: the next light blow starts over.
  PlayerActions actions;
  actions.press(PlayerAction::Attack);
  actions.update(STEP, false);
  chain_attack(actions);
  assert(actions.current() == PlayerAction::Attack2);
  const float wait = PlayerActions::timing(PlayerAction::Attack2).next_action;
  advance(actions, wait);
  actions.press(PlayerAction::HeavyAttack);
  actions.update(STEP, false);
  assert(actions.current() == PlayerAction::HeavyAttack);
  assert(actions.stepping_attack());
  chain_attack(actions);
  assert(actions.current() == PlayerAction::Attack);
}

static void test_lock_on()
{
  LockOnList list;
  list.sort();
  assert(list.size() == 0);
  assert(list.next_to(0.f, 1) == LockOnList::NONE);

  list.add(LockCandidate{0, 9.f, 0.5f});
  list.add(LockCandidate{1, 3.f, -0.4f});
  list.add(LockCandidate{2, 6.f, 0.1f});
  list.add(LockCandidate{3, 4.f, -0.9f});
  list.sort();
  assert(list[0].id == 1 && list[1].id == 3 && list[2].id == 2 && list[3].id == 0);

  assert(list.next_to(0.1f, 1) == 0);
  assert(list.next_to(0.1f, -1) == 1);
  assert(list.next_to(-0.4f, -1) == 3);
  assert(list.next_to(0.5f, 1) == LockOnList::NONE);
}

static void test_health_trail()
{
  HealthTrail trail;
  trail.update(0.6f, STEP);
  assert(trail.value() == 1.f);

  for (float time = 0.f; time < HealthTrail::HOLD_TIME - 0.1f; time += STEP)
    trail.update(0.6f, STEP);
  assert(trail.value() == 1.f);

  for (float time = 0.f; time < 0.3f; time += STEP)
    trail.update(0.6f, STEP);
  assert(trail.value() < 1.f && trail.value() > 0.6f);

  for (float time = 0.f; time < 1.f; time += STEP)
    trail.update(0.6f, STEP);
  assert(trail.value() == 0.6f);

  // A second hit during the slide holds the trail again.
  trail.update(0.4f, STEP);
  const float held = trail.value();
  trail.update(0.4f, STEP);
  assert(trail.value() == held);

  trail.update(1.f, STEP);
  assert(trail.value() == 1.f);
}

static void test_item_catalog()
{
  const ItemCatalog & catalog = ItemCatalog::instance();
  assert(catalog.find("coffee") == ItemCatalog::COFFEE);
  assert(catalog.find("return_candle") == ItemCatalog::CANDLE);
  assert(catalog.find("no_such_item") == NO_ITEM);
  for (ItemId item = 0; item < catalog.size(); ++item)
    assert(catalog.find(catalog[item].key) == item);
  assert(catalog.find("machete") == ItemCatalog::MACHETE);
  assert(catalog[ItemCatalog::MACHETE].kind == ItemKind::Weapon);
}

static void test_inventory_counts()
{
  Inventory bag;
  assert(bag.is_empty());
  assert(!bag.remove(ItemCatalog::CANDLE));

  bag.add(ItemCatalog::CANDLE, 2);
  assert(bag.count(ItemCatalog::CANDLE) == 2);
  assert(!bag.remove(ItemCatalog::CANDLE, 3));
  assert(bag.count(ItemCatalog::CANDLE) == 2);
  assert(bag.remove(ItemCatalog::CANDLE, 2));
  assert(bag.is_empty());
  assert(bag.sorted(InventorySort::Recent).is_empty());
}

struct ByItem
{
  bool operator()(const ItemStack & a, const ItemStack & b) const { return a.item < b.item; }
};

// PDD: merge_sort is only the right choice if DeSiGNAR's version is stable.
static void test_inventory_sort_is_stable()
{
  const ItemCatalog & catalog = ItemCatalog::instance();
  const ItemId vinyl = catalog.find("gaita_vinyl");
  const ItemId card = catalog.find("baseball_card");
  const ItemId tile = catalog.find("domino_tile");
  const ItemId photo = catalog.find("family_photo");

  Inventory bag;
  bag.add(vinyl);
  bag.add(ItemCatalog::CANDLE);
  bag.add(card);
  bag.add(tile);
  bag.add(photo);

  const auto recent = bag.sorted(InventorySort::Recent);
  assert(recent.size() == 5);
  assert(recent[0].item == photo);
  assert(recent[4].item == vinyl);

  // Same kind: the newest stays first, because the second sort keeps the first one's order.
  const auto kinds = bag.sorted(InventorySort::Kind);
  assert(kinds[0].item == ItemCatalog::CANDLE);
  assert(kinds[1].item == photo);
  assert(kinds[2].item == tile);
  assert(kinds[3].item == card);
  assert(kinds[4].item == vinyl);

  const auto worth = bag.sorted(InventorySort::Value);
  assert(worth[0].item == photo);
  assert(worth[4].item == ItemCatalog::CANDLE);

  // Six rows may never reach the merge step, so also a size that really splits.
  Designar::DynArray<ItemStack> rows;
  for (int i = 0; i < 400; ++i)
    rows.append(ItemStack{i % 3, 0, i});
  Designar::merge_sort(rows, ByItem());
  for (int i = 1; i < 400; ++i)
    assert(rows[i - 1].item < rows[i].item || rows[i - 1].order < rows[i].order);
}

static void test_quick_slots()
{
  Inventory bag;
  bag.add(ItemCatalog::COFFEE, 2);
  bag.add(ItemCatalog::CANDLE);

  QuickSlots slots;
  assert(slots.current() == NO_ITEM);
  slots.next(bag);
  assert(slots.current() == NO_ITEM);

  slots.add(ItemCatalog::COFFEE);
  slots.add(ItemCatalog::CANDLE);
  slots.add(ItemCatalog::COFFEE);
  assert(slots.current() == ItemCatalog::COFFEE);
  assert(slots.holds(ItemCatalog::CANDLE));
  assert(!slots.holds(ItemCatalog::instance().find("domino_tile")));
  assert(slots.current() == ItemCatalog::COFFEE);

  slots.next(bag);
  assert(slots.current() == ItemCatalog::CANDLE);
  slots.next(bag);
  assert(slots.current() == ItemCatalog::COFFEE);

  // Out of candles: the turn skips them and lands back on the coffee.
  bag.remove(ItemCatalog::CANDLE);
  slots.next(bag);
  assert(slots.current() == ItemCatalog::COFFEE);

  // Out of everything: stays where it is.
  bag.remove(ItemCatalog::COFFEE, 2);
  slots.next(bag);
  assert(slots.current() == ItemCatalog::COFFEE);
}

static void test_loot_table()
{
  LootTable table;
  table.add(NO_ITEM, 6);
  table.add(ItemCatalog::CANDLE, 3);
  const ItemId tile = ItemCatalog::instance().find("domino_tile");
  table.add(tile, 1);
  assert(table.total_weight() == 10);
  assert(table.pick(0) == NO_ITEM);
  assert(table.pick(5) == NO_ITEM);
  assert(table.pick(6) == ItemCatalog::CANDLE);
  assert(table.pick(8) == ItemCatalog::CANDLE);
  assert(table.pick(9) == tile);
}

static void test_player_stats()
{
  PlayerStats stats;
  assert(stats.max_health() == 100);
  assert(stats.next_cost() == 50);
  stats.raise(Stat::Health);
  assert(stats.max_health() == 110);
  assert(stats.next_cost() == 75);
  stats.raise(Stat::Speed);
  assert(stats.speed_scale() > 1.03f && stats.speed_scale() < 1.05f);
  assert(stats.total_levels() == 2);
  for (int i = 0; i < 4; ++i)
    stats.raise(Stat::Health);
  assert(!stats.can_raise(Stat::Health));
  assert(stats.max_health() == 150);
}

static void test_raising_a_stat()
{
  PlayerProgress progress;
  assert(!progress.raise(Stat::Power, Zone::Avenue));

  progress.earn(60);
  assert(progress.raise(Stat::Power, Zone::Avenue));
  assert(progress.lochas() == 10);
  assert(!progress.raise(Stat::Power, Zone::Avenue)); // The next level costs more than what is left.

  progress.earn(65);
  assert(progress.raise(Stat::Power, Zone::Avenue));
  assert(progress.lochas() == 0);
  assert(progress.stats().level(Stat::Power) == 2);
}

static void test_exchange_rate()
{
  assert(exchange_rate(0) == 100);
  assert(exchange_rate(1) == 110);
  assert(exchange_rate(2) == 110); // Between steps the rate holds.
  assert(exchange_rate(3) == 120);
  assert(exchange_rate(4) == 120);
  assert(exchange_rate(24) == 280);
  assert(exchange_rate(500) == 280); // Past the last step it stays put.
  assert(inflate(80, 0) == 80);
  assert(inflate(80, 1) == 88);
  assert(inflate(15, 1) == 17); // 16.5 rounds up.
  assert(!devalues_on(0));
  assert(devalues_on(1) && !devalues_on(2) && devalues_on(3));
}

static void test_inflation_by_zone()
{
  PlayerProgress progress;
  progress.earn(1000);
  assert(progress.stat_cost(Zone::Avenue) == 50);
  progress.rest(0);
  assert(progress.devalued_today(Zone::Avenue));
  assert(progress.stat_cost(Zone::Avenue) == 55);

  progress.freeze_inflation(Zone::Avenue);
  progress.rest(0);
  progress.rest(0);
  assert(progress.day() == 3);
  assert(progress.exchange_rate(Zone::Avenue) == 110);
  assert(!progress.devalued_today(Zone::Avenue));
  assert(progress.exchange_rate(Zone::Jungle) == 120);
  assert(progress.devalued_today(Zone::Jungle));
  progress.freeze_inflation(Zone::Avenue); // A second win keeps the first day.
  assert(progress.inflation_day(Zone::Avenue) == 1);

  assert(progress.raise(Stat::Power, Zone::Jungle));
  assert(progress.lochas() == 1000 - 60);

  PlayerProgress loaded;
  assert(loaded.from_text(progress.to_text()));
  assert(loaded.inflation_frozen(Zone::Avenue) && !loaded.inflation_frozen(Zone::Plain));
  assert(loaded.exchange_rate(Zone::Avenue) == 110);
  assert(!loaded.from_text("nightmare58 2\nfrozen 3 1\n"));
  assert(!loaded.from_text("nightmare58 2\nfrozen 0 -1\n"));

  // A version 1 save has no frozen zones and still loads.
  assert(loaded.from_text("nightmare58 1\nlochas 9\nday 4\n"));
  assert(loaded.lochas() == 9 && !loaded.inflation_frozen(Zone::Avenue));
  assert(loaded.exchange_rate(Zone::Avenue) == 120);
}

static void test_coffee_capacity()
{
  PlayerProgress progress;
  assert(progress.inventory().count(ItemCatalog::COFFEE) == PlayerProgress::START_COFFEE);
  assert(progress.quick_slots().current() == ItemCatalog::COFFEE);

  progress.inventory().remove(ItemCatalog::COFFEE, 3);
  progress.collect(ItemCatalog::COFFEE);
  assert(progress.coffee_capacity() == PlayerProgress::START_COFFEE + 1);
  assert(progress.inventory().count(ItemCatalog::COFFEE) == 1);

  progress.rest(4);
  assert(progress.inventory().count(ItemCatalog::COFFEE) == PlayerProgress::START_COFFEE + 1);
  assert(progress.chapel() == 4);
  assert(progress.day() == 1);

  progress.collect(ItemCatalog::COFFEE, 50);
  assert(progress.coffee_capacity() == PlayerProgress::MAX_COFFEE);
  assert(progress.collect(ItemCatalog::COFFEE) == 0);
}

static void test_death_and_recovery()
{
  PlayerProgress progress;
  progress.earn(300);

  progress.die(500.f, 1.f, 2.f);
  assert(progress.lochas() == 0);
  assert(progress.has_death_mark());
  const DeathMark & mark = progress.death_mark();
  assert(mark.lochas == 300);
  assert(mark.x == 500.f);

  // Dying again before getting back loses the first mark for good.
  progress.earn(40);
  progress.die(1.f, 0.f, 0.f);
  assert(progress.death_mark().lochas == 40);

  assert(progress.recover() == 40);
  assert(progress.lochas() == 40);
  assert(!progress.has_death_mark());

  PlayerProgress broke;
  broke.die(0.f, 0.f, 0.f);
  assert(!broke.has_death_mark());
}

static void test_pickups_taken()
{
  PlayerProgress progress;
  assert(!progress.pickup_taken(3));
  progress.take_pickup(3);
  assert(progress.pickup_taken(3));
  assert(!progress.pickup_taken(4));
  progress.take_pickup(-1);
  progress.take_pickup(PlayerProgress::MAX_PICKUPS);
  assert(!progress.pickup_taken(-1));
  assert(!progress.pickup_taken(PlayerProgress::MAX_PICKUPS));
}

static void test_save_round_trip()
{
  PlayerProgress saved;
  saved.earn(500);
  saved.raise(Stat::Regeneration, Zone::Avenue);
  saved.collect(ItemCatalog::COFFEE);
  saved.collect(ItemCatalog::CANDLE, 2);
  saved.collect(ItemCatalog::instance().find("family_photo"));
  saved.rest(2);
  saved.take_pickup(7);
  saved.take_pickup(200);
  saved.die(3.f, 0.5f, 9.f);
  saved.earn(11);

  PlayerProgress loaded;
  assert(loaded.from_text(saved.to_text()));
  assert(loaded.lochas() == 11);
  assert(loaded.day() == 1);
  assert(loaded.chapel() == 2);
  assert(loaded.coffee_capacity() == PlayerProgress::START_COFFEE + 1);
  assert(loaded.stats().level(Stat::Regeneration) == 1);
  assert(loaded.inventory().count(ItemCatalog::COFFEE) == PlayerProgress::START_COFFEE + 1);
  assert(loaded.inventory().count(ItemCatalog::CANDLE) == 2);
  assert(loaded.inventory().order(ItemCatalog::CANDLE) == saved.inventory().order(ItemCatalog::CANDLE));
  assert(loaded.quick_slots().holds(ItemCatalog::CANDLE));
  assert(loaded.pickup_taken(7) && loaded.pickup_taken(200) && !loaded.pickup_taken(8));
  assert(loaded.has_death_mark());
  assert(loaded.death_mark().lochas == 450);
  assert(loaded.death_mark().z == 9.f);
  assert(loaded.to_text() == saved.to_text());
}

static void test_damaged_saves()
{
  PlayerProgress progress;
  progress.earn(77);
  const std::string good = progress.to_text();

  const char * damaged[] = {
    "",
    "something else 1\n",
    "nightmare58 999\nlochas 5\n",
    "nightmare58 1\nlochas -5\n",
    "nightmare58 1\nlochas many\n",
    "nightmare58 1\nstat 99 1\n",
    "nightmare58 1\nstat 0 99\n",
    "nightmare58 1\nitem coffee\n",
    "nightmare58 1\ntaken 9999\n",
    "nightmare58 1\nunknown 1\n",
  };
  for (const char * text : damaged)
  {
    assert(!progress.from_text(text));
    assert(progress.lochas() == 77); // Refused without touching anything.
  }
  assert(progress.to_text() == good);

  // An item the catalog no longer has is skipped, and the rest of the game survives.
  assert(progress.from_text("nightmare58 1\nlochas 9\nitem old_item 2 1\n"));
  assert(progress.lochas() == 9);
}

static void test_health_changes()
{
  Health health(100);
  health.damage(30);
  health.heal(10);
  assert(health.value() == 80);
  health.heal(500);
  assert(health.value() == 100);

  health.damage(40);
  health.set_maximum(110);
  assert(health.value() == 70);
  assert(health.ratio() < 0.64f);
}

static void test_stamina_regen_scale()
{
  Stamina plain(100.f);
  Stamina trained(100.f);
  trained.set_regen_scale(2.f);
  plain.spend(90.f);
  trained.spend(90.f);
  plain.update(1.f, true);
  trained.update(1.f, true);
  plain.update(0.1f, true);
  trained.update(0.1f, true);
  assert(trained.ratio() > plain.ratio());
}

static void test_player_use_item()
{
  PlayerActions actions;
  const float effect = PlayerActions::timing(PlayerAction::UseItem).ground_hit;

  actions.press(PlayerAction::UseItem);
  assert(actions.update(0.016f, false));
  assert(actions.current() == PlayerAction::UseItem);
  assert(!actions.hit_ground(0.016f));

  bool took_effect = false;
  for (float time = 0.f; time < effect + 0.1f; time += 0.016f)
  {
    actions.update(0.016f, true);
    took_effect = took_effect || actions.hit_ground(0.016f);
  }
  assert(took_effect);
  assert(actions.current() == PlayerAction::UseItem); // Moving does not cancel it.

  // A blow before the effect leaves nothing to take effect.
  PlayerActions hit;
  hit.press(PlayerAction::UseItem);
  hit.update(0.016f, false);
  hit.hurt();
  assert(hit.current() == PlayerAction::Hurt);
}

static void test_player_name()
{
  PlayerProgress progress;
  assert(progress.player_name() == PlayerProgress::DEFAULT_NAME);

  progress.set_player_name("Ana María");
  PlayerProgress loaded;
  assert(loaded.from_text(progress.to_text()));
  assert(loaded.player_name() == "Ana María");

  progress.set_player_name("Ana\nlochas 999");
  assert(progress.player_name() == "Ana");

  PlayerProgress old;
  assert(old.from_text("nightmare58 1\nlochas 5\n"));
  assert(old.player_name() == PlayerProgress::DEFAULT_NAME);
  assert(old.lochas() == 5);
}

static void test_menu_stack()
{
  MenuStack menu;
  assert(!menu.is_open());

  menu.open(MenuScreen::Chapel);
  menu.move_cursor(1, 3);
  menu.move_cursor(1, 3);
  assert(menu.cursor() == 2);
  menu.move_cursor(1, 3);
  assert(menu.cursor() == 0);
  menu.move_cursor(-1, 3);
  assert(menu.cursor() == 2);

  menu.open(MenuScreen::Inventory);
  assert(menu.screen() == MenuScreen::Inventory);
  assert(menu.cursor() == 0);
  menu.move_cursor(1, 0); // An empty list has nowhere to go.
  assert(menu.cursor() == 0);

  menu.back();
  assert(menu.screen() == MenuScreen::Chapel);
  assert(menu.cursor() == 2);
  menu.keep_cursor_within(2);
  assert(menu.cursor() == 1);

  menu.close();
  assert(!menu.is_open());
}

static void test_shop()
{
  const ItemCatalog & catalog = ItemCatalog::instance();
  const ItemId vinyl = ItemCatalog::VINYL;
  const int candle = catalog[ItemCatalog::CANDLE].value;

  PlayerProgress progress;
  assert(progress.shop_price(candle, Zone::Avenue) == candle);
  assert(!progress.buy(ItemCatalog::CANDLE, Zone::Avenue)); // No lochas yet.
  assert(!progress.buy(ItemCatalog::COFFEE, Zone::Avenue)); // Not for sale.

  progress.earn(candle);
  assert(progress.buy(ItemCatalog::CANDLE, Zone::Avenue));
  assert(progress.lochas() == 0);
  assert(progress.inventory().count(ItemCatalog::CANDLE) == 1);
  assert(progress.quick_slots().holds(ItemCatalog::CANDLE));

  // Only collectibles sell, at the day's rate.
  assert(!progress.sell(ItemCatalog::CANDLE, Zone::Avenue));
  assert(!progress.sell(vinyl, Zone::Avenue));
  progress.collect(vinyl, 2);
  progress.rest(0);
  progress.rest(0);
  progress.rest(0);
  assert(progress.sell_price(vinyl, Zone::Avenue) == catalog[vinyl].value * 120 / 100);
  assert(progress.sell(vinyl, Zone::Avenue));
  assert(progress.lochas() == catalog[vinyl].value * 120 / 100);
  assert(progress.inventory().count(vinyl) == 1);

  // Each death raises his prices, up to a cap, on top of inflation.
  progress.die(0.f, 0.f, 0.f);
  assert(progress.deaths() == 1 && progress.markup() == PlayerProgress::DEATH_MARKUP);
  assert(progress.shop_price(100, Zone::Avenue) == 126);
  for (int i = 0; i < 20; ++i)
    progress.die(0.f, 0.f, 0.f);
  assert(progress.markup() == PlayerProgress::MAX_MARKUP);
  assert(progress.sell_price(vinyl, Zone::Avenue) == catalog[vinyl].value * 120 / 100); // Selling is not marked up.

  PlayerProgress loaded;
  assert(loaded.from_text(progress.to_text()));
  assert(loaded.deaths() == 21);
  assert(!loaded.from_text("nightmare58 3\ndeaths -1\n"));
}

static void test_machete_tree()
{
  SkillTree tree = make_machete_tree();
  assert(tree.is_unlocked(MacheteSkill::MACHETE));
  assert(tree.cost(MacheteSkill::EDGE_2) == machete_skill(MacheteSkill::EDGE_2).cost);
  assert(tree.cost(99) == -1);

  // Visited parents first, in the order of the table.
  int expected = 0;
  tree.visit([&expected](const Skill & skill, int depth) {
    assert(skill.id == expected++);
    assert(depth == 0 || machete_skill(skill.id).parent != MacheteSkill::NONE);
  });
  assert(expected == MacheteSkill::COUNT);

  assert(!tree.restore(MacheteSkill::EDGE_2)); // Its parent is still locked.
  assert(tree.restore(MacheteSkill::EDGE_1) && tree.restore(MacheteSkill::EDGE_2));
  assert(!tree.restore(MacheteSkill::MACHETE) && !tree.restore(99));

  SkillTree moved = std::move(tree);
  assert(moved.is_unlocked(MacheteSkill::EDGE_2));
  assert(find_machete_skill("throw") == MacheteSkill::THROW);
  assert(find_machete_skill("nothing") == MacheteSkill::NONE);
}

static void test_learning_machete_skills()
{
  PlayerProgress progress;
  assert(progress.machete_damage_scale() == 1.f);
  assert(!progress.learn(MacheteSkill::EDGE_1, Zone::Avenue));

  progress.earn(2000);
  assert(!progress.learn(MacheteSkill::EDGE_2, Zone::Avenue)); // Filo comes first.
  assert(progress.learn(MacheteSkill::EDGE_1, Zone::Avenue));
  assert(progress.lochas() == 2000 - 60);
  assert(!progress.learn(MacheteSkill::EDGE_1, Zone::Avenue)); // Already known.

  // Paid at the bachaquero's prices: inflation and the death markup.
  progress.rest(0);
  progress.die(0.f, 0.f, 0.f);
  progress.recover();
  assert(progress.skill_price(MacheteSkill::EDGE_2, Zone::Avenue) == 139); // 132 at the rate, then +5 %, rounded up.
  assert(progress.learn(MacheteSkill::EDGE_2, Zone::Avenue));
  assert(progress.machete_damage_scale() > 1.29f && progress.machete_damage_scale() < 1.31f);
  assert(progress.learn(MacheteSkill::TECHNIQUE, Zone::Avenue) && progress.learn(MacheteSkill::THROW, Zone::Avenue));

  PlayerProgress loaded;
  assert(loaded.from_text(progress.to_text()));
  assert(loaded.has_skill(MacheteSkill::EDGE_2) && loaded.has_skill(MacheteSkill::THROW));
  assert(!loaded.has_skill(MacheteSkill::RAGE));
  assert(loaded.to_text() == progress.to_text());
  assert(!loaded.from_text("nightmare58 3\nskill edge_2\n")); // A child without its parent is damage.
  assert(!loaded.from_text("nightmare58 3\nskill nothing\n"));
}

static void test_status_effects()
{
  StatusEffects effects;
  assert(effects.update(1.f) == 0 && effects.slow_scale() == 1.f);

  effects.apply(Status::Burn);
  assert(effects.update(0.4f) == 0);
  assert(effects.update(0.1f) == StatusEffects::BURN_DAMAGE); // First tick at 0.5 s.

  // Burns stack up to the limit; past it the oldest one starts over.
  for (int i = 0; i < 5; ++i)
    effects.apply(Status::Burn);
  assert(effects.count(Status::Burn) == StatusEffects::MAX_BURNS);

  effects.apply(Status::Chill);
  effects.apply(Status::Chill);
  assert(effects.count(Status::Chill) == 1);
  assert(effects.slow_scale() == StatusEffects::CHILL_SLOW);

  int total = 0;
  for (int tick = 0; tick < 600; ++tick)
    total += effects.update(1.f / 60.f);
  assert(!effects.has(Status::Burn) && !effects.has(Status::Chill));
  assert(total > 0 && total <= StatusEffects::MAX_BURNS * 8 * StatusEffects::BURN_DAMAGE);

  effects.apply(Status::Burn);
  effects.clear();
  assert(!effects.has(Status::Burn));

  WeaponCoat coat;
  assert(!coat.active());
  coat.apply(Status::Chill);
  assert(coat.active() && coat.kind() == Status::Chill && coat.ratio() == 1.f);
  coat.update(WeaponCoat::DURATION - 1.f);
  assert(coat.active());
  coat.update(2.f);
  assert(!coat.active() && coat.ratio() == 0.f);
}

static void test_grease_in_the_shop()
{
  PlayerProgress progress;
  progress.earn(5000);
  auto offers = [&progress](ItemId item) {
    const Designar::DynArray<ItemId> stock = progress.shop_stock();
    for (Designar::nat_t i = 0; i < stock.size(); ++i)
      if (stock[i] == item)
        return true;
    return false;
  };
  assert(!offers(ItemCatalog::FIRE_GREASE) && !progress.buy(ItemCatalog::FIRE_GREASE, Zone::Avenue));
  assert(progress.learn(MacheteSkill::GREASE, Zone::Avenue) && progress.learn(MacheteSkill::FIRE, Zone::Avenue));
  assert(offers(ItemCatalog::FIRE_GREASE) && !offers(ItemCatalog::ICE_GREASE));
  assert(progress.buy(ItemCatalog::FIRE_GREASE, Zone::Avenue));
  assert(progress.inventory().count(ItemCatalog::FIRE_GREASE) == 1);
  assert(progress.quick_slots().holds(ItemCatalog::FIRE_GREASE));
}

static void test_thrown_weapon_flight()
{
  ThrownWeapon flight;
  assert(!flight.in_air());
  flight.release();
  assert(flight.heading_out());

  // Out in a straight line until its range, never past it.
  float out = 0.f;
  while (flight.heading_out())
    out += flight.step(1.f / 60.f);
  assert(out > ThrownWeapon::RANGE - 0.001f && out < ThrownWeapon::RANGE + 0.001f);
  assert(flight.current() == ThrownWeapon::Phase::Back);

  // Back until the hand is within reach of the step.
  const float step = flight.step(1.f / 60.f);
  assert(!flight.caught(5.f, step));
  assert(flight.caught(step + ThrownWeapon::CATCH_RADIUS, step));
  assert(!flight.in_air());

  // A wall sends it back early, and a hand it never reaches still gets it after a while.
  flight.release();
  flight.step(0.1f);
  flight.turn_back();
  assert(flight.current() == ThrownWeapon::Phase::Back);
  for (int tick = 0; tick < 300; ++tick)
    flight.step(1.f / 60.f);
  assert(flight.caught(100.f, 0.3f));
}

static void test_player_throw()
{
  PlayerActions actions;
  actions.press(PlayerAction::Throw);
  assert(actions.update(0.016f, false));
  assert(actions.current() == PlayerAction::Throw);
  assert(PlayerActions::timing(PlayerAction::Throw).hit_end == 0.f); // The flying weapon hits, not the swing.

  // Once it is in the air, nothing that needs it gets through, not even a second throw.
  actions.release_weapon();
  actions.press(PlayerAction::Attack);
  actions.press(PlayerAction::HeavyAttack);
  for (int tick = 0; tick < 60; ++tick)
    actions.update(0.016f, false);
  assert(actions.current() == PlayerAction::None);
  actions.press(PlayerAction::Throw);
  assert(!actions.update(0.016f, false));
  actions.press(PlayerAction::Attack);
  assert(!actions.update(0.016f, false));
  actions.press(PlayerAction::Dodge);
  assert(actions.update(0.016f, false) && actions.current() == PlayerAction::Dodge);

  // Caught mid-dodge it is just back; caught while idle it plays the catch.
  assert(!actions.catch_weapon());
  assert(!actions.weapon_away());
  for (int tick = 0; tick < 60; ++tick)
    actions.update(0.016f, false);
  actions.release_weapon();
  assert(actions.catch_weapon() && actions.current() == PlayerAction::Catch);
  for (int tick = 0; tick < 30; ++tick)
    actions.update(0.016f, false);
  actions.press(PlayerAction::Attack);
  assert(actions.update(0.016f, false) && actions.current() == PlayerAction::Attack);

  actions.release_weapon();
  actions.revive(); // Death puts it back in the hand.
  assert(!actions.weapon_away());
}

static void test_rage()
{
  Rage rage;
  assert(!rage.activate()); // Empty.
  assert(rage.damage_dealt_scale() == 1.f && rage.damage_taken_scale() == 1.f);

  rage.deal(20);
  assert(rage.ratio() > 0.15f && rage.ratio() < 0.17f);
  rage.take(20);
  assert(rage.ratio() > 0.39f && rage.ratio() < 0.41f); // Being hit fills it faster.
  for (int i = 0; i < 10; ++i)
    rage.deal(20);
  assert(rage.full() && rage.ratio() == 1.f);

  assert(rage.activate());
  assert(!rage.activate()); // Already burning.
  assert(rage.damage_dealt_scale() == Rage::DEALT_SCALE && rage.damage_taken_scale() == Rage::TAKEN_SCALE);
  rage.deal(50); // Nothing refills it while it burns.
  rage.update(Rage::DURATION * 0.5f);
  assert(rage.active() && rage.ratio() > 0.49f && rage.ratio() < 0.51f);
  rage.update(Rage::DURATION);
  assert(!rage.active() && rage.ratio() == 0.f && rage.damage_dealt_scale() == 1.f);

  rage.deal(200);
  rage.reset();
  assert(rage.ratio() == 0.f);
}

static void test_wearing_the_cap()
{
  const ItemCatalog & catalog = ItemCatalog::instance();
  assert(catalog[ItemCatalog::CAP].kind == ItemKind::Outfit);

  PlayerProgress progress;
  assert(!progress.wear(ItemCatalog::CAP)); // Not owned yet.
  assert(!progress.wear(ItemCatalog::MACHETE)); // Not an outfit.
  assert(progress.outfit_damage_scale() == 1.f);

  progress.earn(1000);
  assert(progress.buy(ItemCatalog::CAP, Zone::Avenue));
  assert(!progress.buy(ItemCatalog::CAP, Zone::Avenue)); // Only one.
  assert(!progress.quick_slots().holds(ItemCatalog::CAP));

  assert(progress.wear(ItemCatalog::CAP) && progress.worn() == ItemCatalog::CAP);
  assert(progress.outfit_damage_scale() == PlayerProgress::CAP_STRENGTH);

  PlayerProgress loaded;
  assert(loaded.from_text(progress.to_text()));
  assert(loaded.worn() == ItemCatalog::CAP);
  assert(loaded.to_text() == progress.to_text());

  assert(progress.wear(ItemCatalog::CAP) && progress.worn() == NO_ITEM); // Taken off.
  assert(loaded.from_text(progress.to_text()) && loaded.worn() == NO_ITEM);

  assert(!loaded.from_text("nightmare58 3\nwear coffee\n"));
  assert(!loaded.from_text("nightmare58 3\nwear cap\n")); // Worn but not in the bag.
  assert(loaded.from_text("nightmare58 3\nlochas 4\nwear old_hat\n") && loaded.worn() == NO_ITEM);
}

static void test_endless_lochas()
{
  PlayerProgress progress;
  progress.set_endless(true);
  const int wallet = progress.lochas();
  assert(wallet == PlayerProgress::ENDLESS_WALLET);
  assert(progress.learn(MacheteSkill::TECHNIQUE, Zone::Avenue) && progress.learn(MacheteSkill::THROW, Zone::Avenue));
  assert(progress.raise(Stat::Power, Zone::Avenue) && progress.buy(ItemCatalog::CAP, Zone::Avenue));
  assert(progress.lochas() == wallet);

  progress.die(1.f, 2.f, 3.f);
  assert(!progress.has_death_mark() && progress.lochas() == wallet && progress.deaths() == 1);

  PlayerProgress loaded;
  assert(loaded.from_text(progress.to_text()) && loaded.endless());
  assert(!loaded.from_text("nightmare58 3\nendless 2\n"));
  PlayerProgress normal;
  assert(loaded.from_text(normal.to_text()) && !loaded.endless());
}

int main()
{
  assert(classify_distance(2.f, 3.f, 8.f) == DistanceRange::Near);
  assert(classify_distance(3.f, 3.f, 8.f) == DistanceRange::Near);
  assert(classify_distance(5.f, 3.f, 8.f) == DistanceRange::Medium);
  assert(classify_distance(9.f, 3.f, 8.f) == DistanceRange::Far);
  test_skill_tree();
  test_behavior_tree_priorities();
  test_behavior_tree_rotation();
  test_behavior_tree_empty_queues();
  test_skeleton_tree();
  test_distance_margin();
  test_attack_turns();
  test_enemy_attack();
  test_enemy_stagger();
  test_player_action_lifetime();
  test_player_action_buffer();
  test_player_dodge_cancel();
  test_player_step_scale();
  test_player_move_cancel();
  test_player_combo();
  test_player_run_attack();
  test_player_dodge_button();
  test_player_air_rules();
  test_player_hit_window();
  test_player_ground_hit();
  test_health();
  test_health_trail();
  test_stamina();
  test_player_stamina();
  test_player_hurt();
  test_player_heavy_attack();
  test_lock_on();
  test_item_catalog();
  test_inventory_counts();
  test_inventory_sort_is_stable();
  test_quick_slots();
  test_loot_table();
  test_player_stats();
  test_raising_a_stat();
  test_exchange_rate();
  test_inflation_by_zone();
  test_coffee_capacity();
  test_death_and_recovery();
  test_pickups_taken();
  test_save_round_trip();
  test_damaged_saves();
  test_health_changes();
  test_stamina_regen_scale();
  test_player_use_item();
  test_menu_stack();
  test_player_name();
  test_shop();
  test_machete_tree();
  test_learning_machete_skills();
  test_status_effects();
  test_grease_in_the_shop();
  test_thrown_weapon_flight();
  test_player_throw();
  test_rage();
  test_wearing_the_cap();
  test_endless_lochas();
  return 0;
}
