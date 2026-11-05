#include "guino_enemy.hpp"

namespace
{
// He always leaves something worth selling.
const LootTable & guino_loot()
{
  static const LootTable table = [] {
    const ItemCatalog & catalog = ItemCatalog::instance();
    LootTable loot;
    loot.add(catalog.find("family_photo"), 1);
    loot.add(catalog.find("gaita_vinyl"), 1);
    return loot;
  }();
  return table;
}

// In MeleeProfile order. The speeds are those of animate_guino.py.
constexpr MeleeProfile GUINO{
  "guino",
  750, 300, 1.9f,               // Health, lochas, aim height.
  4.2f, 11.f, 6.5f, 2.2f,       // Near, medium, charge from, strike reach.
  1.6f, 7.5f, 1.5f, 1.2f, 6.f,  // Walk, run, circle, back, run from.
  4.8f, 6.f,                    // Circle gap.
  {EnemyAction::Maul, EnemyAction::Crunch, EnemyAction::Whirl},
  EnemyAction::Crash,
  "howl",
  guino_loot,
  {EnemyAction::Frenzy, EnemyAction::Whirl, EnemyAction::Quake, EnemyAction::Maul},
  "enrage",
  1.2f,                         // Fury haste.
  true,
  Zone::Avenue,
};
}

GuinoEnemy::GuinoEnemy()
  : MeleeEnemy(GUINO)
{
}
