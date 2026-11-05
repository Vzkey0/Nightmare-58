#pragma once

#include "melee_enemy.hpp"

// The street dog: a double snap and a bite that thrashes from close, a leap from the middle. It
// barks when it spots the player.
class DogEnemy : public MeleeEnemy
{
  GDCLASS(DogEnemy, MeleeEnemy)

protected:
  static void _bind_methods() {}

public:
  DogEnemy();
};
