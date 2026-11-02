#pragma once

#include <array.hpp>

#include <core/progression/item_catalog.hpp>

// What an enemy may drop. NO_ITEM is a valid entry: most kills drop nothing.
class LootTable
{
public:
  void add(ItemId item, int weight)
  {
    total += weight;
    entries.append(Entry{item, total});
  }

  int total_weight() const { return total; }

  // roll goes from 0 to total_weight() - 1. The caller rolls, so the table can be tested.
  ItemId pick(int roll) const
  {
    // J-010: a straight scan beats a binary search at this size, by not missing branches.
    int at = 0;
    while (entries[at].upper <= roll)
      ++at;
    return entries[at].item;
  }

private:
  struct Entry
  {
    ItemId item;
    int upper; // The weight of this entry and every one before it.
  };

  Designar::DynArray<Entry> entries;
  int total = 0;
};
