#include <core/progression/inventory.hpp>

#include <algorithm>

#include <sort.hpp>

namespace
{
struct NewestFirst
{
  bool operator()(const ItemStack & a, const ItemStack & b) const { return a.order > b.order; }
};

struct ByKind
{
  bool operator()(const ItemStack & a, const ItemStack & b) const
  {
    const ItemCatalog & catalog = ItemCatalog::instance();
    return catalog[a.item].kind < catalog[b.item].kind;
  }
};

struct MostValuable
{
  bool operator()(const ItemStack & a, const ItemStack & b) const
  {
    const ItemCatalog & catalog = ItemCatalog::instance();
    return catalog[a.item].value > catalog[b.item].value;
  }
};
}

Inventory::Inventory()
  : counts(static_cast<Designar::nat_t>(ItemCatalog::instance().size()), 0),
    orders(static_cast<Designar::nat_t>(ItemCatalog::instance().size()), 0)
{
}

void Inventory::add(ItemId item, int amount)
{
  if (counts[item] == 0)
    orders[item] = next_order++;
  counts[item] += amount;
}

bool Inventory::remove(ItemId item, int amount)
{
  if (counts[item] < amount)
    return false;
  counts[item] -= amount;
  return true;
}

void Inventory::set(ItemId item, int amount)
{
  if (counts[item] == 0 && amount > 0)
    orders[item] = next_order++;
  counts[item] = amount;
}

void Inventory::restore(ItemId item, int amount, int order)
{
  counts[item] = amount;
  orders[item] = order;
  next_order = std::max(next_order, order + 1);
}

bool Inventory::is_empty() const
{
  for (int amount : counts)
    if (amount > 0)
      return false;
  return true;
}

Designar::DynArray<ItemStack> Inventory::sorted(InventorySort mode) const
{
  Designar::DynArray<ItemStack> stacks;
  for (ItemId item = 0; item < static_cast<ItemId>(counts.size()); ++item)
    if (counts[item] > 0)
      stacks.append(ItemStack{item, counts[item], orders[item]});

  // J-009: stable, so a second key keeps the newest items first among equals.
  Designar::merge_sort(stacks, NewestFirst());
  if (mode == InventorySort::Kind)
    Designar::merge_sort(stacks, ByKind());
  else if (mode == InventorySort::Value)
    Designar::merge_sort(stacks, MostValuable());
  return stacks;
}
