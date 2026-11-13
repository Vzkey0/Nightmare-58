#include "skeleton_enemy.hpp"

namespace
{
const LootTable & skeleton_loot()
{
  static const LootTable table = [] {
    const ItemCatalog & catalog = ItemCatalog::instance();
    LootTable loot;
    loot.add(NO_ITEM, 75);
    loot.add(ItemCatalog::COFFEE, 2);
    loot.add(ItemCatalog::CANDLE, 8);
    loot.add(catalog.find("gaita_vinyl"), 4);
    loot.add(catalog.find("baseball_card"), 4);
    loot.add(catalog.find("domino_tile"), 5);
    loot.add(catalog.find("family_photo"), 2);
    return loot;
  }();
  return table;
}

// In MeleeProfile order.
constexpr MeleeProfile SKELETON{
  "skeleton",
  70, 30, 1.2f,                // Health, lochas, aim height.
  1.9f, 4.4f, 2.6f, 1.25f,     // Near, medium, charge from, strike reach.
  1.4f, 3.8f, 1.1f, 1.1f, 4.f, // Walk, run (slower than the player), circle, back, run from.
  2.5f, 3.7f,                  // Circle gap.
  {EnemyAction::Chop, EnemyAction::Sweep, EnemyAction::None},
  EnemyAction::Lunge,
  nullptr,
  skeleton_loot,
};
}

SkeletonEnemy::SkeletonEnemy()
  : MeleeEnemy(SKELETON)
{
}
