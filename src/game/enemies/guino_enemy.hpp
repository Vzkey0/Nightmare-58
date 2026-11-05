#pragma once

#include "melee_enemy.hpp"

// Güino, the giant husky that closes the avenue: two rakes, a crushing bite and a tail whip from
// close, and a six meter pounce from the middle. Below a third of his health he shakes himself,
// rears up roaring with his ribs aglow and fights faster, adding a flurry and a quake.
class GuinoEnemy : public MeleeEnemy
{
  GDCLASS(GuinoEnemy, MeleeEnemy)

protected:
  static void _bind_methods() {}

public:
  GuinoEnemy();
};
