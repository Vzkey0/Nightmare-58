#undef NDEBUG
#include <cassert>

#include <core/ai/behavior_tree.hpp>
#include <core/distance.hpp>
#include <core/player/player_actions.hpp>
#include <core/progression/skill_tree.hpp>

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
  assert(chained.current() == PlayerAction::Attack);

  // A press from too long ago is no longer what the player wants.
  PlayerActions stale;
  stale.press(PlayerAction::Attack);
  stale.update(STEP, false);
  stale.press(PlayerAction::Dodge);
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
  assert(full.current() == PlayerAction::Attack);
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
  air.update(STEP, false, true);
  assert(air.current() == PlayerAction::None);

  PlayerActions waits;
  waits.press(PlayerAction::Dodge);
  assert(!waits.update(STEP, false, false));
  assert(waits.update(STEP, false, true));
  assert(waits.current() == PlayerAction::Dodge);
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
  test_player_action_lifetime();
  test_player_action_buffer();
  test_player_move_cancel();
  test_player_dodge_button();
  test_player_air_rules();
  return 0;
}
