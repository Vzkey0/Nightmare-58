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

  bool add(int parent_id, int id, int cost);
  bool is_unlocked(int id) const;
  bool can_unlock(int id, int points) const;
  bool unlock(int id, int & points);

private:
  // J-001: each skill has one parent and any number of children.
  Designar::MTreeNode<Skill> * root;
};
