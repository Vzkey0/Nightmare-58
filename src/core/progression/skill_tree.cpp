#include <core/progression/skill_tree.hpp>

using Node = Designar::MTreeNode<Skill>;

// J-001: O(n) traversal; it does not run per frame and the tree has few skills.
static Node * find(Node * node, int id)
{
  if (node->get_key().id == id)
    return node;

  for (Node * child = node->get_first_child(); child != nullptr;
       child = child->get_right_sibling())
  {
    Node * found = find(child, id);
    if (found != nullptr)
      return found;
  }

  return nullptr;
}

SkillTree::SkillTree(int root_id)
  : root(new Node(Skill{root_id, 0, true}))
{
}

SkillTree::~SkillTree()
{
  Node::destroy_tree(root);
}

bool SkillTree::add(int parent_id, int id, int cost)
{
  Node * parent = find(root, parent_id);
  if (parent == nullptr || find(root, id) != nullptr)
    return false;

  parent->append_child(new Node(Skill{id, cost, false}));
  return true;
}

bool SkillTree::is_unlocked(int id) const
{
  const Node * node = find(root, id);
  return node != nullptr && node->get_key().unlocked;
}

bool SkillTree::can_unlock(int id, int points) const
{
  const Node * node = find(root, id);
  if (node == nullptr || node->get_key().unlocked)
    return false;

  return node->get_parent()->get_key().unlocked
    && points >= node->get_key().cost;
}

bool SkillTree::unlock(int id, int & points)
{
  if (!can_unlock(id, points))
    return false;

  Skill & skill = find(root, id)->get_key();
  skill.unlocked = true;
  points -= skill.cost;
  return true;
}
