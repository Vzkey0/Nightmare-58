#pragma once

#include <array.hpp>

#include <core/progression/item_catalog.hpp>

struct ItemStack
{
  ItemId item;
  int count;
  int order; // Raised on each new item, so a higher one was picked up later.
};

enum class InventorySort { Recent, Kind, Value };

constexpr int INVENTORY_SORTS = 3;

class Inventory
{
public:
  Inventory();

  void add(ItemId item, int amount = 1);
  bool remove(ItemId item, int amount = 1);
  void set(ItemId item, int amount);
  void restore(ItemId item, int amount, int order); // For a loaded game.
  int count(ItemId item) const { return counts[item]; }
  int order(ItemId item) const { return orders[item]; }
  bool is_empty() const;

  // Rebuilt on each call: only a menu asks, and only when it changes.
  Designar::DynArray<ItemStack> sorted(InventorySort mode) const;

private:
  // J-008: an ItemId is an index, so adding and asking never search.
  Designar::DynArray<int> counts;
  Designar::DynArray<int> orders;
  int next_order = 1;
};
