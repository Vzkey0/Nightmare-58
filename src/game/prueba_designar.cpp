#include "prueba_designar.hpp"

#include <exception>

#include <godot_cpp/variant/utility_functions.hpp>
#include <list.hpp>

void PruebaDesignar::_ready()
{
  Designar::SLList<int> numeros;
  numeros.append(1);
  numeros.append(2);
  numeros.append(3);
  godot::UtilityFunctions::print("DeSiGNAR OK: ", (int)numeros.size(), " elementos");

  try
  {
    Designar::SLList<int> vacia;
    vacia.get_first();
    godot::UtilityFunctions::print("Sin excepcion");
  }
  catch (const std::exception &e)
  {
    godot::UtilityFunctions::print("Excepcion atrapada: ", e.what());
  }
}
