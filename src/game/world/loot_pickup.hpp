#pragma once

#include <godot_cpp/classes/area3d.hpp>
#include <godot_cpp/classes/node3d.hpp>
#include <godot_cpp/variant/string.hpp>

// An item on the ground, taken by walking over it. One placed in a level has an id, so a saved
// game remembers it; what an enemy drops has none and does not outlive the session.
class LootPickup : public godot::Area3D
{
  GDCLASS(LootPickup, godot::Area3D)

protected:
  static void _bind_methods();

public:
  static constexpr int NO_ID = -1;

  void _ready() override;

  godot::String get_item_key() const { return item_key; }
  void set_item_key(const godot::String & value) { item_key = value; }
  int get_amount() const { return amount; }
  void set_amount(int value) { amount = value; }
  int get_pickup_id() const { return pickup_id; }
  void set_pickup_id(int value) { pickup_id = value; }

private:
  void on_body_entered(godot::Node3D * body);

  godot::String item_key = "coffee";
  int amount = 1;
  int pickup_id = NO_ID;
};
