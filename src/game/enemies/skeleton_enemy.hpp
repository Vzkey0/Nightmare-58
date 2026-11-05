#pragma once

#include "melee_enemy.hpp"

// Machete in hand: two cuts from close and a leaping slash from the middle.
class SkeletonEnemy : public MeleeEnemy
{
  GDCLASS(SkeletonEnemy, MeleeEnemy)

protected:
  static void _bind_methods() {}

public:
  SkeletonEnemy();
};
