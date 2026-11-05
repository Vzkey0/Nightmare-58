#pragma once

#include "melee_enemy.hpp"

// The giant rat: a short bite and a rearing rake from close, a pounce from the middle. Fast and
// frail, it hisses a warning when it spots the player.
class RatEnemy : public MeleeEnemy
{
  GDCLASS(RatEnemy, MeleeEnemy)

protected:
  static void _bind_methods() {}

public:
  RatEnemy();
};
