#undef NDEBUG
#include <cassert>

#include <core/ai/behavior_tree.hpp>
#include <core/distance.hpp>
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
  return 0;
}
