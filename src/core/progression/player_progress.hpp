#pragma once

#include <string>

#include <array.hpp>
#include <bitset.hpp>

#include <core/progression/inflation.hpp>
#include <core/progression/inventory.hpp>
#include <core/progression/machete_skills.hpp>
#include <core/progression/player_stats.hpp>
#include <core/progression/quick_slots.hpp>

// What the player left behind.
struct DeathMark
{
  int lochas = 0;
  float x = 0.f;
  float y = 0.f;
  float z = 0.f;
};

// Everything a saved game keeps. Rules only: the Godot side moves the player and shows it.
class PlayerProgress
{
public:
  static constexpr int NO_CHAPEL = -1;
  static constexpr int NOT_FROZEN = -1;
  static constexpr int DEATH_MARKUP = 10; // Percent the bachaquero adds per death.
  static constexpr int MAX_MARKUP = 100;
  static constexpr int START_COFFEE = 3;
  static constexpr int MAX_COFFEE = 6;
  static constexpr int MAX_PICKUPS = 256;
  static constexpr const char * DEFAULT_NAME = "Sin nombre";

  PlayerProgress();

  const std::string & player_name() const { return name; }
  void set_player_name(const std::string & value);

  int lochas() const { return wallet; }
  int day() const { return days; }
  int deaths() const { return death_count; }
  int chapel() const { return last_chapel; }
  int coffee_capacity() const { return coffee_limit; }
  const DeathMark & death_mark() const { return mark; }
  bool has_death_mark() const { return mark.lochas > 0; }

  Inventory & inventory() { return items; }
  const Inventory & inventory() const { return items; }
  const PlayerStats & stats() const { return levels; }
  const SkillTree & machete_tree() const { return machete; }
  QuickSlots & quick_slots() { return quick; }

  void earn(int amount) { wallet += amount; }

  // A coffee found raises the capacity for good; the rest just go into the bag.
  // Returns how many were actually kept: none once the coffee capacity is full.
  int collect(ItemId item, int amount = 1);

  // Prices are fixed in day-0 lochas; a zone pays them at its own day's rate.
  int inflation_day(Zone zone) const;
  int exchange_rate(Zone zone) const { return ::exchange_rate(inflation_day(zone)); }
  int price(int base, Zone zone) const { return inflate(base, inflation_day(zone)); }
  bool devalued_today(Zone zone) const { return inflation_day(zone) == days && devalues_on(days); }
  bool inflation_frozen(Zone zone) const { return frozen[static_cast<int>(zone)] != NOT_FROZEN; }

  // A boss beaten in a zone stops its prices where they are. Beating it again changes nothing.
  void freeze_inflation(Zone zone);

  // What the bachaquero charges: the zone's rate, and more each time the player has died.
  int shop_price(int base, Zone zone) const;
  int markup() const;
  // What he sells right now; it grows with the machete tree.
  Designar::DynArray<ItemId> shop_stock() const;
  bool can_buy(ItemId item, Zone zone) const;
  bool buy(ItemId item, Zone zone);
  // Collectibles never lose their worth, so he pays them at the day's rate: holding them beats
  // holding lochas.
  int sell_price(ItemId item, Zone zone) const { return price(ItemCatalog::instance()[item].value, zone); }
  bool sell(ItemId item, Zone zone);

  // The machete tree is paid to the bachaquero, at his prices.
  bool has_skill(int skill) const { return machete.is_unlocked(skill); }
  int skill_price(int skill, Zone zone) const { return shop_price(machete.cost(skill), zone); }
  bool can_learn(int skill, Zone zone) const;
  bool learn(int skill, Zone zone);
  float machete_damage_scale() const;

  int stat_cost(Zone zone) const { return price(levels.next_cost(), zone); }
  bool can_raise(Stat stat, Zone zone) const;
  bool raise(Stat stat, Zone zone);

  // Replaces the previous mark, whose lochas are lost: dying twice in a row costs them.
  void die(float x, float y, float z);
  int recover();

  void rest(int chapel);
  void refill_coffee() { items.set(ItemCatalog::COFFEE, coffee_limit); }

  // A false id from a scene is simply not remembered.
  void take_pickup(int id);
  bool pickup_taken(int id) const;

  std::string to_text() const;

  // Leaves this object untouched if the text is damaged, so a bad file never costs a game.
  bool from_text(const std::string & text);

private:
  Inventory items;
  PlayerStats levels;
  SkillTree machete = make_machete_tree();
  QuickSlots quick;
  DeathMark mark;
  std::string name = DEFAULT_NAME;

  // J-012: pickup ids are small and dense, so one bit each is the smallest and fastest answer.
  Designar::DynBitSet taken;

  int wallet = 0;
  int days = 0;
  int last_chapel = NO_CHAPEL;
  int coffee_limit = START_COFFEE;
  int death_count = 0;
  int frozen[ZONE_COUNT] = {NOT_FROZEN, NOT_FROZEN, NOT_FROZEN}; // The day each zone stopped at.
};
