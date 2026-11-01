#undef NDEBUG
#include <cassert>

#include <core/ai/attack_turns.hpp>
#include <core/ai/behavior_tree.hpp>
#include <core/ai/enemy_actions.hpp>
#include <core/distance.hpp>
#include <core/health.hpp>
#include <core/health_trail.hpp>
#include <core/lock_on.hpp>
#include <core/player/player_actions.hpp>
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
  return 0;
}
