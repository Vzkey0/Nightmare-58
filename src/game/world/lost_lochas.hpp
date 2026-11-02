#pragma once

#include <godot_cpp/classes/area3d.hpp>
#include <godot_cpp/classes/node3d.hpp>

// Marks where the player fell and holds the lochas left there, until the player comes back.
class LostLochas : public godot::Area3D
{
  GDCLASS(LostLochas, godot::Area3D)

protected:
  static void _bind_methods() {}

public:
  void _ready() override;

private:
  void on_body_entered(godot::Node3D * body);
};
