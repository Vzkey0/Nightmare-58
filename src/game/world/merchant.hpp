#pragma once

#include <godot_cpp/classes/area3d.hpp>
#include <godot_cpp/classes/node3d.hpp>

#include <core/progression/inflation.hpp>

// The bachaquero: tells the player when they are close enough to trade. His prices follow the
// inflation of the zone he stands in.
class Merchant : public godot::Area3D
{
  GDCLASS(Merchant, godot::Area3D)

protected:
  static void _bind_methods();

public:
  void _ready() override;

  int get_zone() const { return zone; }
  void set_zone(int value) { zone = value; }
  Zone zone_kind() const { return static_cast<Zone>(zone); }

private:
  void on_body_entered(godot::Node3D * body);
  void on_body_exited(godot::Node3D * body);

  int zone = 0;
};
