#pragma once

#include <string>

#include <bitset.hpp>

#include <core/progression/inventory.hpp>
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
  static constexpr int START_COFFEE = 3;
  static constexpr int MAX_COFFEE = 6;
  static constexpr int MAX_PICKUPS = 256;
  static constexpr const char * DEFAULT_NAME = "Sin nombre";

  PlayerProgress();

  const std::string & player_name() const { return name; }
  void set_player_name(const std::string & value);

  int lochas() const { return wallet; }
  int day() const { return days; }
  int chapel() const { return last_chapel; }
  int coffee_capacity() const { return coffee_limit; }
  const DeathMark & death_mark() const { return mark; }
  bool has_death_mark() const { return mark.lochas > 0; }

  Inventory & inventory() { return items; }
  const Inventory & inventory() const { return items; }
  const PlayerStats & stats() const { return levels; }
  QuickSlots & quick_slots() { return quick; }

  void earn(int amount) { wallet += amount; }

  // A coffee found raises the capacity for good; the rest just go into the bag.
  // Returns how many were actually kept: none once the coffee capacity is full.
  int collect(ItemId item, int amount = 1);

  bool can_raise(Stat stat) const;
  bool raise(Stat stat);

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
  QuickSlots quick;
  DeathMark mark;
  std::string name = DEFAULT_NAME;

  // J-012: pickup ids are small and dense, so one bit each is the smallest and fastest answer.
  Designar::DynBitSet taken;

  int wallet = 0;
  int days = 0;
  int last_chapel = NO_CHAPEL;
  int coffee_limit = START_COFFEE;
};
