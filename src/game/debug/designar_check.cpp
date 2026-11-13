#include "designar_check.hpp"

#include <exception>

#include <godot_cpp/variant/utility_functions.hpp>
#include <list.hpp>

void DesignarCheck::_ready()
{
  Designar::SLList<int> numbers;
  numbers.append(1);
  numbers.append(2);
  numbers.append(3);
  godot::UtilityFunctions::print("DeSiGNAR OK: ", (int)numbers.size(), " elements");

  try
  {
    Designar::SLList<int> empty;
    empty.get_first();
    godot::UtilityFunctions::print("No exception");
  }
  catch (const std::exception &e)
  {
    godot::UtilityFunctions::print("Exception caught: ", e.what());
  }
}
