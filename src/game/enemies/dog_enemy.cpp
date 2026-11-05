#include "dog_enemy.hpp"

namespace
{
const LootTable & dog_loot()
{
  static const LootTable table = [] {
    const ItemCatalog & catalog = ItemCatalog::instance();
    LootTable loot;
    loot.add(NO_ITEM, 76);
    loot.add(ItemCatalog::COFFEE, 3);
    loot.add(ItemCatalog::CANDLE, 7);
    loot.add(catalog.find("gaita_vinyl"), 5);
    loot.add(catalog.find("family_photo"), 4);
    loot.add(catalog.find("domino_tile"), 5);
    return loot;
  }();
  return table;
}

// In MeleeProfile order. The speeds are those of animate_dog.py.
constexpr MeleeProfile DOG{
  "dog",
  60, 55, 0.65f,                // Health, lochas, aim height.
  1.7f, 5.f, 2.6f, 1.05f,       // Near, medium, charge from, strike reach.
  1.3f, 5.8f, 1.3f, 1.f, 3.f,   // Walk, run, circle, back, run from.
  2.4f, 3.6f,                   // Circle gap.
  {EnemyAction::Snap, EnemyAction::Thrash},
  EnemyAction::Leap,
  "bark",
  dog_loot,
};
}

DogEnemy::DogEnemy()
  : MeleeEnemy(DOG)
{
}
