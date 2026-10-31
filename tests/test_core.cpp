#undef NDEBUG
#include <cassert>

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

int main()
{
  assert(classify_distance(2.f, 3.f, 8.f) == DistanceRange::Near);
  assert(classify_distance(3.f, 3.f, 8.f) == DistanceRange::Near);
  assert(classify_distance(5.f, 3.f, 8.f) == DistanceRange::Medium);
  assert(classify_distance(9.f, 3.f, 8.f) == DistanceRange::Far);
  test_skill_tree();
  return 0;
}
