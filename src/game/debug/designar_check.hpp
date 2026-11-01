#pragma once

#include <godot_cpp/classes/node.hpp>

// Phase 0: checks that DeSiGNAR works inside Godot.
class DesignarCheck : public godot::Node
{
  GDCLASS(DesignarCheck, godot::Node)

protected:
  static void _bind_methods() {}

public:
  void _ready() override;
};
