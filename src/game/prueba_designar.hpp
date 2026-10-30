#pragma once

#include <godot_cpp/classes/node.hpp>

// Fase 0: comprueba que DeSiGNAR funciona dentro de Godot.
class PruebaDesignar : public godot::Node
{
  GDCLASS(PruebaDesignar, godot::Node)

protected:
  static void _bind_methods() {}

public:
  void _ready() override;
};
