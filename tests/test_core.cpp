#undef NDEBUG
#include <cassert>

#include <core/distance.hpp>
#include <core/progression/skill_tree.hpp>
#include "core/ai/DecisionTree.hpp"
#include "core/attack.hpp"

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

static void test_DecisionTree(){

  Designar::DynQueue<Attack> near_qs;
    near_qs.put(Attack{});
    near_qs.put(Attack{});

    Designar::DynQueue<Attack> medium_qs;
    medium_qs.put(Attack{});

    Designar::DynQueue<Attack> far_qs;
    far_qs.put(Attack{});

    DecisionTree tree(near_qs, medium_qs, far_qs);

    Attack eval_near_1 = tree.evaluate(DistanceRange::Near);
    Attack eval_near_2 = tree.evaluate(DistanceRange::Near);
    Attack eval_medium = tree.evaluate(DistanceRange::Medium);
    Attack eval_far    = tree.evaluate(DistanceRange::Far);

    Attack eval_default = tree.evaluate(DistanceRange::Far);

}


int main()
{
  assert(classify_distance(2.f, 3.f, 8.f) == DistanceRange::Near);
  assert(classify_distance(3.f, 3.f, 8.f) == DistanceRange::Near);
  assert(classify_distance(5.f, 3.f, 8.f) == DistanceRange::Medium);
  assert(classify_distance(9.f, 3.f, 8.f) == DistanceRange::Far);
  test_skill_tree();
  test_DecisionTree();
  return 0;
}
