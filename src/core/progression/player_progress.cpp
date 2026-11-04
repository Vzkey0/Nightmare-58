#include <core/progression/player_progress.hpp>

#include <algorithm>
#include <utility>
#include <sstream>

namespace
{
// 2 added frozen zones and 3 the bachaquero and the machete tree. Older saves still load: missing lines keep their defaults.
constexpr int SAVE_VERSION = 3;
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
  items.add(ItemCatalog::MACHETE, 1);
  quick.add(ItemCatalog::COFFEE);
}

// One line per field in the save, so a name may hold spaces but never a line break.
void PlayerProgress::set_player_name(const std::string & value)
{
  name = value.empty() ? DEFAULT_NAME : value.substr(0, value.find_first_of("\r\n"));
  if (name.empty())
    name = DEFAULT_NAME;
}

int PlayerProgress::collect(ItemId item, int amount)
{
  if (item == ItemCatalog::COFFEE)
  {
    const int gained = std::min(amount, MAX_COFFEE - coffee_limit);
    coffee_limit += gained;
    items.add(item, gained);
    return gained;
  }
  items.add(item, amount);
  if (ItemCatalog::instance()[item].kind == ItemKind::Consumable)
    quick.add(item);
  return amount;
}

int PlayerProgress::inflation_day(Zone zone) const
{
  const int stopped = frozen[static_cast<int>(zone)];
  return stopped == NOT_FROZEN ? days : stopped;
}

void PlayerProgress::freeze_inflation(Zone zone)
{
  if (!inflation_frozen(zone))
    frozen[static_cast<int>(zone)] = days;
}

int PlayerProgress::markup() const
{
  return std::min(death_count * DEATH_MARKUP, MAX_MARKUP);
}

int PlayerProgress::shop_price(int base, Zone zone) const
{
  return (price(base, zone) * (100 + markup()) + 99) / 100;
}

Designar::DynArray<ItemId> PlayerProgress::shop_stock() const
{
  Designar::DynArray<ItemId> stock;
  stock.append(ItemCatalog::CANDLE);
  if (has_skill(MacheteSkill::FIRE))
    stock.append(ItemCatalog::FIRE_GREASE);
  if (has_skill(MacheteSkill::ICE))
    stock.append(ItemCatalog::ICE_GREASE);
  return stock;
}

bool PlayerProgress::can_buy(ItemId item, Zone zone) const
{
  const Designar::DynArray<ItemId> stock = shop_stock();
  bool offered = false;
  for (Designar::nat_t i = 0; i < stock.size(); ++i)
    offered = offered || stock[i] == item;
  return offered && wallet >= shop_price(ItemCatalog::instance()[item].value, zone);
}

bool PlayerProgress::buy(ItemId item, Zone zone)
{
  if (!can_buy(item, zone))
    return false;
  wallet -= shop_price(ItemCatalog::instance()[item].value, zone);
  collect(item);
  return true;
}

bool PlayerProgress::sell(ItemId item, Zone zone)
{
  if (ItemCatalog::instance()[item].kind != ItemKind::Collectible || !items.remove(item))
    return false;
  wallet += sell_price(item, zone);
  return true;
}

bool PlayerProgress::can_learn(int skill, Zone zone) const
{
  // The tree checks the parent; the price is the bachaquero's, not the tree's own cost.
  return machete.can_unlock(skill, machete.cost(skill)) && wallet >= skill_price(skill, zone);
}

bool PlayerProgress::learn(int skill, Zone zone)
{
  if (!can_learn(skill, zone))
    return false;
  wallet -= skill_price(skill, zone);
  int base = machete.cost(skill);
  machete.unlock(skill, base);
  return true;
}

float PlayerProgress::machete_damage_scale() const
{
  int edge = 0;
  for (int skill : {MacheteSkill::EDGE_1, MacheteSkill::EDGE_2, MacheteSkill::EDGE_3})
    edge += has_skill(skill) ? 1 : 0;
  return 1.f + EDGE_DAMAGE * edge;
}

bool PlayerProgress::can_raise(Stat stat, Zone zone) const
{
  return levels.can_raise(stat) && wallet >= stat_cost(zone);
}

bool PlayerProgress::raise(Stat stat, Zone zone)
{
  if (!can_raise(stat, zone))
    return false;
  wallet -= stat_cost(zone);
  levels.raise(stat);
  return true;
}

void PlayerProgress::die(float x, float y, float z)
{
  mark = DeathMark{wallet, x, y, z};
  ++death_count;
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
  out << "name " << name << '\n';
  out << "lochas " << wallet << '\n';
  out << "day " << days << '\n';
  out << "chapel " << last_chapel << '\n';
  out << "coffee " << coffee_limit << '\n';
  out << "deaths " << death_count << '\n';

  for (int zone = 0; zone < ZONE_COUNT; ++zone)
    if (frozen[zone] != NOT_FROZEN)
      out << "frozen " << zone << ' ' << frozen[zone] << '\n';

  for (int stat = 0; stat < STAT_COUNT; ++stat)
    out << "stat " << stat << ' ' << levels.level(static_cast<Stat>(stat)) << '\n';

  // By key and not by id: a save outlives any reordering of the catalog.
  const ItemCatalog & catalog = ItemCatalog::instance();
  for (ItemId item = 0; item < catalog.size(); ++item)
    if (items.count(item) > 0)
      out << "item " << catalog[item].key << ' ' << items.count(item) << ' ' << items.order(item) << '\n';

  // Parents first, so loading can restore them in the same order.
  machete.visit([&out](const Skill & skill, int depth) {
    if (depth > 0 && skill.unlocked)
      out << "skill " << machete_skill(skill.id).key << '\n';
  });

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
  if (!(in >> word >> version) || word != SAVE_HEADER || !in_range(version, 1, SAVE_VERSION))
    return false;

  PlayerProgress loaded;
  loaded.items.set(ItemCatalog::COFFEE, 0);
  const ItemCatalog & catalog = ItemCatalog::instance();

  while (in >> word)
  {
    bool good = false;
    if (word == "name")
    {
      std::string value;
      std::getline(in >> std::ws, value);
      loaded.set_player_name(value);
      good = true;
    }
    else if (word == "lochas")
      good = static_cast<bool>(in >> loaded.wallet) && in_range(loaded.wallet, 0, MAX_AMOUNT);
    else if (word == "day")
      good = static_cast<bool>(in >> loaded.days) && in_range(loaded.days, 0, MAX_AMOUNT);
    else if (word == "chapel")
      good = static_cast<bool>(in >> loaded.last_chapel) && in_range(loaded.last_chapel, NO_CHAPEL, MAX_AMOUNT);
    else if (word == "coffee")
      good = static_cast<bool>(in >> loaded.coffee_limit) && in_range(loaded.coffee_limit, 0, MAX_COFFEE);
    else if (word == "deaths")
      good = static_cast<bool>(in >> loaded.death_count) && in_range(loaded.death_count, 0, MAX_AMOUNT);
    else if (word == "frozen")
    {
      int zone = 0;
      int day = 0;
      good = (in >> zone >> day) && in_range(zone, 0, ZONE_COUNT - 1) && in_range(day, 0, MAX_AMOUNT);
      if (good)
        loaded.frozen[zone] = day;
    }
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
    else if (word == "skill")
    {
      std::string key;
      good = (in >> key) && loaded.machete.restore(find_machete_skill(key));
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

  *this = std::move(loaded);
  return true;
}
