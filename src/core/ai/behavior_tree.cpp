#include <core/ai/behavior_tree.hpp>

using Node = Designar::MTreeNode<BehaviorNode>;

static constexpr float FURY_HEALTH_RATIO = 0.3f;

static Node * make_node(BehaviorNodeType type, BehaviorCondition condition, BehaviorAction action)
{
  return new Node(BehaviorNode{type, condition, action});
}

static Node * make_action(BehaviorAction action)
{
  return make_node(BehaviorNodeType::Action, BehaviorCondition{}, action);
}

static Node * make_selector()
{
  return make_node(BehaviorNodeType::Selector, BehaviorCondition{}, BehaviorAction::None);
}

static Node * make_guard(BehaviorCondition condition, Node * body)
{
  Node * sequence = make_node(BehaviorNodeType::Sequence, BehaviorCondition{}, BehaviorAction::None);
  sequence->append_child(make_node(BehaviorNodeType::Condition, condition, BehaviorAction::None));
  sequence->append_child(body);
  return sequence;
}

static bool holds(BehaviorCondition condition, const EnemyContext & context)
{
  switch (condition)
  {
    case BehaviorCondition::LowHealth: return context.health_ratio < FURY_HEALTH_RATIO;
    case BehaviorCondition::Near: return context.range == DistanceRange::Near;
    case BehaviorCondition::Medium: return context.range == DistanceRange::Medium;
    case BehaviorCondition::Far: return context.range == DistanceRange::Far;
    case BehaviorCondition::Unaware: return !context.aware;
    case BehaviorCondition::LostSight: return !context.sees_player;
    case BehaviorCondition::CanAttack: return context.can_attack;
    case BehaviorCondition::ChargeReady: return context.charge_ready;
  }
  return false;
}

BehaviorTree::BehaviorTree(Node * root, const AttackQueue & fury, const AttackQueue & melee,
                           const AttackQueue & ranged, const AttackQueue & charge)
  : root(root),
    fury_attacks(fury),
    melee_attacks(melee),
    ranged_attacks(ranged),
    charge_attacks(charge)
{
}

BehaviorTree::BehaviorTree(const AttackQueue & fury, const AttackQueue & melee,
                           const AttackQueue & ranged, const AttackQueue & charge)
  : BehaviorTree(make_selector(), fury, melee, ranged, charge)
{
  Node * medium_body = make_selector();
  medium_body->append_child(make_action(BehaviorAction::Ranged));
  medium_body->append_child(make_action(BehaviorAction::Approach));

  root->append_child(make_guard(BehaviorCondition::LowHealth, make_action(BehaviorAction::Fury)));
  root->append_child(make_guard(BehaviorCondition::Near, make_action(BehaviorAction::Melee)));
  root->append_child(make_guard(BehaviorCondition::Medium, medium_body));
  root->append_child(make_guard(BehaviorCondition::Far, make_action(BehaviorAction::Charge)));
}

BehaviorTree BehaviorTree::skeleton(const AttackQueue & melee, const AttackQueue & charge)
{
  using Condition = BehaviorCondition;
  using Action = BehaviorAction;

  Node * tree = make_selector();
  tree->append_child(make_guard(Condition::Unaware, make_action(Action::Watch)));
  tree->append_child(make_guard(Condition::LostSight, make_action(Action::Investigate)));
  tree->append_child(make_guard(Condition::Near, make_guard(Condition::CanAttack, make_action(Action::Melee))));
  tree->append_child(make_guard(Condition::Medium, make_guard(Condition::CanAttack,
                                                              make_guard(Condition::ChargeReady, make_action(Action::Charge)))));
  tree->append_child(make_guard(Condition::Far, make_action(Action::Approach)));
  tree->append_child(make_guard(Condition::CanAttack, make_action(Action::Approach)));
  tree->append_child(make_action(Action::Circle));
  return BehaviorTree(tree, AttackQueue(), melee, AttackQueue(), charge);
}

BehaviorTree::~BehaviorTree()
{
  Node::destroy_tree(root);
}

Decision BehaviorTree::decide(const EnemyContext & context) const
{
  Decision decision{BehaviorAction::None, NO_ATTACK};
  evaluate(root, context, decision);
  return decision;
}

void BehaviorTree::commit(const Decision & decision)
{
  // The queues are private members of this object, so dropping const is safe.
  AttackQueue * queue = const_cast<AttackQueue *>(queue_for(decision.action));
  if (queue != nullptr)
    queue->put(queue->get());
}

bool BehaviorTree::evaluate(const Node * node, const EnemyContext & context, Decision & decision) const
{
  const BehaviorNode & data = node->get_key();

  if (data.type == BehaviorNodeType::Condition)
    return holds(data.condition, context);

  if (data.type == BehaviorNodeType::Action)
  {
    const AttackQueue * queue = queue_for(data.action);
    if (queue != nullptr && queue->is_empty())
      return false;

    decision = Decision{data.action, queue != nullptr ? queue->front().id : NO_ATTACK};
    return true;
  }

  // A selector stops at the first success, a sequence at the first failure.
  const bool stop_on = data.type == BehaviorNodeType::Selector;
  for (const Node * child = node->get_first_child(); child != nullptr;
       child = child->get_right_sibling())
    if (evaluate(child, context, decision) == stop_on)
      return stop_on;

  return !stop_on;
}

const BehaviorTree::AttackQueue * BehaviorTree::queue_for(BehaviorAction action) const
{
  switch (action)
  {
    case BehaviorAction::Fury: return &fury_attacks;
    case BehaviorAction::Melee: return &melee_attacks;
    case BehaviorAction::Ranged: return &ranged_attacks;
    case BehaviorAction::Charge: return &charge_attacks;
    case BehaviorAction::None:
    case BehaviorAction::Approach:
    case BehaviorAction::Watch:
    case BehaviorAction::Investigate:
    case BehaviorAction::Circle: return nullptr;
  }
  return nullptr;
}
