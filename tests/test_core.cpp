#undef NDEBUG
#include <cassert>

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
#include <core/progression/inventory.hpp>
#include <core/progression/item_catalog.hpp>
#include <core/progression/loot_table.hpp>
#include <core/progression/player_progress.hpp>
#include <core/progression/quick_slots.hpp>
#include <core/progression/skill_tree.hpp>
#include <core/stamina.hpp>

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
  assert(stats.next_cost() == 80);
  stats.raise(Stat::Health);
  assert(stats.max_health() == 110);
  assert(stats.next_cost() == 120);
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
  assert(!progress.raise(Stat::Power));

  progress.earn(100);
  assert(progress.raise(Stat::Power));
  assert(progress.lochas() == 20);
  assert(!progress.raise(Stat::Power)); // The next level costs more than what is left.

  progress.earn(100);
  assert(progress.raise(Stat::Power));
  assert(progress.lochas() == 0);
  assert(progress.stats().level(Stat::Power) == 2);
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
  saved.raise(Stat::Regeneration);
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
  assert(loaded.death_mark().lochas == 420);
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
  return 0;
}
