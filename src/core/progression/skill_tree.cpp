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
  if (root != nullptr)
    Node::destroy_tree(root);
}

SkillTree & SkillTree::operator=(SkillTree && other) noexcept
{
  if (this != &other)
  {
    if (root != nullptr)
      Node::destroy_tree(root);
    root = other.root;
    other.root = nullptr;
  }
  return *this;
}

int SkillTree::cost(int id) const
{
  const Node * node = find(root, id);
  return node == nullptr ? -1 : node->get_key().cost;
}

bool SkillTree::restore(int id)
{
  Node * node = find(root, id);
  if (node == nullptr || node == root || !node->get_parent()->get_key().unlocked)
    return false;
  node->get_key().unlocked = true;
  return true;
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

// Leaves take the next free column; a parent goes midway between its first and last child.
static float place(const Node * node, int depth, int branch, int parent, float & next_leaf, Designar::DynArray<SkillSlot> & slots)
{
  const Skill & skill = node->get_key();
  const Designar::nat_t index = slots.size();
  slots.append(SkillSlot{skill.id, parent, branch, depth, 0.f, skill.cost, skill.unlocked});
  float first = -1.f;
  float last = -1.f;
  for (const Node * child = node->get_first_child(); child != nullptr; child = child->get_right_sibling())
  {
    last = place(child, depth + 1, branch, skill.id, next_leaf, slots);
    if (first < 0.f)
      first = last;
  }
  const float column = first < 0.f ? next_leaf++ : (first + last) * 0.5f;
  slots[index].column = column;
  return column;
}

Designar::DynArray<SkillSlot> SkillTree::layout() const
{
  Designar::DynArray<SkillSlot> slots;
  const Skill & top = root->get_key();
  slots.append(SkillSlot{top.id, -1, -1, 0, 0.f, top.cost, top.unlocked});
  int branch = 0;
  for (const Node * child = root->get_first_child(); child != nullptr; child = child->get_right_sibling())
  {
    float next_leaf = 0.f;
    place(child, 1, branch++, top.id, next_leaf, slots);
  }
  return slots;
}
