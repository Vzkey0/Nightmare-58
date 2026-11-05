#pragma once

#include <mtreenode.hpp>

struct Skill
{
  int id;
  int cost;
  bool unlocked;
};

class SkillTree
{
public:
  explicit SkillTree(int root_id);
  ~SkillTree();

  SkillTree(const SkillTree &) = delete;
  SkillTree & operator=(const SkillTree &) = delete;

  // Moving hands the nodes over, so a loaded game can replace the current one.
  SkillTree(SkillTree && other) noexcept : root(other.root) { other.root = nullptr; }
  SkillTree & operator=(SkillTree && other) noexcept;

  bool add(int parent_id, int id, int cost);
  bool is_unlocked(int id) const;
  bool can_unlock(int id, int points) const;
  bool unlock(int id, int & points);

  int cost(int id) const; // -1 for an unknown id.

  // For a loaded game: unlocks without paying, but only under an unlocked parent.
  bool restore(int id);

  // Parents before children, so the order can be saved and restored as it is.
  template <class Visit>
  void visit(Visit && visit_skill) const
  {
    visit_from(root, 0, visit_skill);
  }

private:
  using Node = Designar::MTreeNode<Skill>;

  template <class Visit>
  static void visit_from(const Node * node, int depth, Visit & visit_skill)
  {
    visit_skill(node->get_key(), depth);
    for (const Node * child = node->get_first_child(); child != nullptr; child = child->get_right_sibling())
      visit_from(child, depth + 1, visit_skill);
  }

  // J-001: each skill has one parent and any number of children.
  Node * root;
};
