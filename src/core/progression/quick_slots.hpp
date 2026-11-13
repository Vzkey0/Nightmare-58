#pragma once

#include <queue.hpp>

#include <core/progression/inventory.hpp>

// The front of the queue is the item in hand; cycling sends it to the back.
class QuickSlots
{
public:
  static constexpr int CAPACITY = 4;

  void add(ItemId item)
  {
    if (slots.is_full() || holds(item))
      return;
    slots.put(item);
  }

  ItemId current() const { return slots.is_empty() ? NO_ITEM : slots.front(); }

  // Skips what the player has run out of, unless nothing else is left.
  void next(const Inventory & inventory)
  {
    const int size = static_cast<int>(slots.size());
    for (int turn = 1; turn < size; ++turn)
    {
      rotate();
      if (inventory.count(slots.front()) > 0)
        return;
    }
    if (size > 0)
      rotate();
  }

  // Ends where it started, however the queue is laid out.
  bool holds(ItemId item)
  {
    bool found = false;
    for (int turn = static_cast<int>(slots.size()); turn > 0; --turn)
    {
      found = found || slots.front() == item;
      rotate();
    }
    return found;
  }

private:
  void rotate() { slots.put(slots.get()); }

  // J-013: rotating is two O(1) steps, and the capacity is small and known.
  Designar::FixedQueue<ItemId, CAPACITY> slots;
};
