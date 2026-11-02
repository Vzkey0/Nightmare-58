#pragma once

#include <string>

#include <array.hpp>
#include <map.hpp>

using ItemId = int;

constexpr ItemId NO_ITEM = -1;

enum class ItemKind { Consumable, Collectible };

struct Item
{
  const char * key; // Scenes and saves name items by this, so reordering the table breaks neither.
  const char * name;
  const char * description;
  ItemKind kind;
  int value;
};

// Every item in the game. An ItemId is an index into the table, so everything after the first
// lookup is a plain array access.
class ItemCatalog
{
public:
  static constexpr ItemId COFFEE = 0;
  static constexpr ItemId CANDLE = 1;
  static constexpr ItemId VINYL = 2;
  static constexpr ItemId CARD = 3;
  static constexpr ItemId TILE = 4;
  static constexpr ItemId PHOTO = 5;

  static const ItemCatalog & instance();

  ItemId find(const std::string & key) const;
  const Item & operator[](ItemId id) const { return items[id]; }
  int size() const { return static_cast<int>(items.size()); }

private:
  ItemCatalog();

  Designar::DynArray<Item> items;

  // J-007: text keys arrive from scenes and saves; a hash answers in the same time at any size.
  Designar::HashMap<std::string, ItemId> ids;
};
