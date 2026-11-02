#include <core/progression/player_progress.hpp>

#include <algorithm>
#include <sstream>

namespace
{
constexpr int SAVE_VERSION = 1;
constexpr const char * SAVE_HEADER = "nightmare58";
constexpr int MAX_AMOUNT = 1000000000; // Anything above this comes from a damaged file.

bool in_range(int value, int low, int high)
{
  return value >= low && value <= high;
}
}

PlayerProgress::PlayerProgress() : taken(static_cast<Designar::nat_t>(MAX_PICKUPS), false)
{
  items.add(ItemCatalog::COFFEE, START_COFFEE);
  quick.add(ItemCatalog::COFFEE);
}

void PlayerProgress::collect(ItemId item, int amount)
{
  if (item == ItemCatalog::COFFEE)
  {
    const int gained = std::min(amount, MAX_COFFEE - coffee_limit);
    coffee_limit += gained;
    items.add(item, gained);
    return;
  }
  items.add(item, amount);
  if (ItemCatalog::instance()[item].kind == ItemKind::Consumable)
    quick.add(item);
}

bool PlayerProgress::can_raise(Stat stat) const
{
  return levels.can_raise(stat) && wallet >= levels.next_cost();
}

bool PlayerProgress::raise(Stat stat)
{
  if (!can_raise(stat))
    return false;
  wallet -= levels.next_cost();
  levels.raise(stat);
  return true;
}

void PlayerProgress::die(float x, float y, float z)
{
  mark = DeathMark{wallet, x, y, z};
  wallet = 0;
}

int PlayerProgress::recover()
{
  const int recovered = mark.lochas;
  wallet += recovered;
  mark.lochas = 0;
  return recovered;
}

void PlayerProgress::rest(int chapel)
{
  ++days;
  last_chapel = chapel;
  refill_coffee();
}

void PlayerProgress::take_pickup(int id)
{
  if (in_range(id, 0, MAX_PICKUPS - 1))
    taken[static_cast<Designar::nat_t>(id)] = true;
}

bool PlayerProgress::pickup_taken(int id) const
{
  return in_range(id, 0, MAX_PICKUPS - 1) && taken.get_bit(static_cast<Designar::nat_t>(id));
}

std::string PlayerProgress::to_text() const
{
  std::ostringstream out;
  out << SAVE_HEADER << ' ' << SAVE_VERSION << '\n';
  out << "lochas " << wallet << '\n';
  out << "day " << days << '\n';
  out << "chapel " << last_chapel << '\n';
  out << "coffee " << coffee_limit << '\n';

  for (int stat = 0; stat < STAT_COUNT; ++stat)
    out << "stat " << stat << ' ' << levels.level(static_cast<Stat>(stat)) << '\n';

  // By key and not by id: a save outlives any reordering of the catalog.
  const ItemCatalog & catalog = ItemCatalog::instance();
  for (ItemId item = 0; item < catalog.size(); ++item)
    if (items.count(item) > 0)
      out << "item " << catalog[item].key << ' ' << items.count(item) << ' ' << items.order(item) << '\n';

  for (int id = 0; id < MAX_PICKUPS; ++id)
    if (pickup_taken(id))
      out << "taken " << id << '\n';

  if (has_death_mark())
    out << "mark " << mark.lochas << ' ' << mark.x << ' ' << mark.y << ' ' << mark.z << '\n';
  return out.str();
}

bool PlayerProgress::from_text(const std::string & text)
{
  std::istringstream in(text);
  std::string word;
  int version = 0;
  if (!(in >> word >> version) || word != SAVE_HEADER || version != SAVE_VERSION)
    return false;

  PlayerProgress loaded;
  loaded.items.set(ItemCatalog::COFFEE, 0);
  const ItemCatalog & catalog = ItemCatalog::instance();

  while (in >> word)
  {
    bool good = false;
    if (word == "lochas")
      good = static_cast<bool>(in >> loaded.wallet) && in_range(loaded.wallet, 0, MAX_AMOUNT);
    else if (word == "day")
      good = static_cast<bool>(in >> loaded.days) && in_range(loaded.days, 0, MAX_AMOUNT);
    else if (word == "chapel")
      good = static_cast<bool>(in >> loaded.last_chapel) && in_range(loaded.last_chapel, NO_CHAPEL, MAX_AMOUNT);
    else if (word == "coffee")
      good = static_cast<bool>(in >> loaded.coffee_limit) && in_range(loaded.coffee_limit, 0, MAX_COFFEE);
    else if (word == "stat")
    {
      int stat = 0;
      int level = 0;
      good = (in >> stat >> level) && in_range(stat, 0, STAT_COUNT - 1) && in_range(level, 0, PlayerStats::MAX_LEVEL);
      if (good)
        loaded.levels.restore(stat, level);
    }
    else if (word == "item")
    {
      std::string key;
      int amount = 0;
      int order = 0;
      good = (in >> key >> amount >> order) && in_range(amount, 0, MAX_AMOUNT) && in_range(order, 0, MAX_AMOUNT);
      // An item that left the catalog is dropped, not a reason to refuse the save.
      const ItemId item = catalog.find(key);
      if (good && item != NO_ITEM)
      {
        loaded.items.restore(item, amount, order);
        if (catalog[item].kind == ItemKind::Consumable)
          loaded.quick.add(item);
      }
    }
    else if (word == "taken")
    {
      int id = 0;
      good = (in >> id) && in_range(id, 0, MAX_PICKUPS - 1);
      if (good)
        loaded.take_pickup(id);
    }
    else if (word == "mark")
    {
      DeathMark & place = loaded.mark;
      good = (in >> place.lochas >> place.x >> place.y >> place.z) && in_range(place.lochas, 0, MAX_AMOUNT);
    }
    if (!good)
      return false;
  }

  *this = loaded;
  return true;
}
