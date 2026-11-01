#pragma once

#include <mtreenode.hpp>
#include <queue.hpp>

#include <core/attack.hpp>
#include <core/distance.hpp>

enum class BehaviorNodeType { Selector, Sequence, Condition, Action };
enum class BehaviorCondition { LowHealth, Near, Medium, Far, Unaware, LostSight, CanAttack, ChargeReady };
enum class BehaviorAction { None, Fury, Melee, Ranged, Approach, Charge, Watch, Investigate, Circle };

struct BehaviorNode
{
  BehaviorNodeType type;
  BehaviorCondition condition;
  BehaviorAction action;
};

struct EnemyContext
{
  float health_ratio;
  DistanceRange range;
  bool aware = true;
  bool sees_player = true;
  bool can_attack = true; // Rested, and with a free turn among the enemies around the player.
  bool charge_ready = true;
};

struct Decision
{
  BehaviorAction action;
  int attack_id;
};

class BehaviorTree
{
public:
  static constexpr int NO_ATTACK = -1;

  using AttackQueue = Designar::DynQueue<Attack>;

  BehaviorTree(const AttackQueue & fury, const AttackQueue & melee,
               const AttackQueue & ranged, const AttackQueue & charge);
  ~BehaviorTree();

  // Melee from close, a charge from the middle, and circling while it waits for a turn.
  static BehaviorTree skeleton(const AttackQueue & melee, const AttackQueue & charge);

  BehaviorTree(const BehaviorTree &) = delete;
  BehaviorTree & operator=(const BehaviorTree &) = delete;

  // Pure: it runs constantly, so it must not spend the attack it picks.
  Decision decide(const EnemyContext & context) const;

  // Called when the decision actually runs; moves its attack to the back.
  void commit(const Decision & decision);

private:
  using Node = Designar::MTreeNode<BehaviorNode>;

  BehaviorTree(Node * root, const AttackQueue & fury, const AttackQueue & melee,
               const AttackQueue & ranged, const AttackQueue & charge);

  bool evaluate(const Node * node, const EnemyContext & context, Decision & decision) const;
  const AttackQueue * queue_for(BehaviorAction action) const;

  // J-002: ordered children of any count, and their order is the priority.
  Node * root;

  // J-003: a queue rotates attacks with O(1) reads while deciding.
  AttackQueue fury_attacks;
  AttackQueue melee_attacks;
  AttackQueue ranged_attacks;
  AttackQueue charge_attacks;
};
