#include "rat_enemy.hpp"

namespace
{
const LootTable & rat_loot()
{
  static const LootTable table = [] {
    const ItemCatalog & catalog = ItemCatalog::instance();
    LootTable loot;
    loot.add(NO_ITEM, 80);
    loot.add(ItemCatalog::CANDLE, 6);
    loot.add(catalog.find("domino_tile"), 8);
    loot.add(catalog.find("baseball_card"), 6);
    return loot;
  }();
  return table;
}

// In MeleeProfile order. The speeds are those of animate_rat.py.
constexpr MeleeProfile RAT{
  "rat",
  40, 45, 0.4f,                 // Health, lochas, aim height.
  1.5f, 4.5f, 2.2f, 1.f,        // Near, medium, charge from, strike reach.
  0.9f, 4.8f, 1.2f, 0.9f, 2.5f, // Walk, run (faster than a jog, slower than a sprint), circle, back, run from.
  1.8f, 2.8f,                   // Circle gap.
  {EnemyAction::Bite, EnemyAction::Rake, EnemyAction::None},
  EnemyAction::Pounce,
  "threat",
  rat_loot,
};
}

RatEnemy::RatEnemy()
  : MeleeEnemy(RAT)
{
}
