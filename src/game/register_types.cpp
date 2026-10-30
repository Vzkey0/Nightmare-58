#include <gdextension_interface.h>
#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/core/defs.hpp>
#include <godot_cpp/godot.hpp>

#include "prueba_designar.hpp"

using namespace godot;

static void iniciar(ModuleInitializationLevel nivel)
{
  if (nivel == MODULE_INITIALIZATION_LEVEL_SCENE)
    GDREGISTER_CLASS(PruebaDesignar);
}

static void terminar(ModuleInitializationLevel) {}

extern "C" GDExtensionBool GDE_EXPORT nightmare58_init(
  GDExtensionInterfaceGetProcAddress get_proc_address,
  GDExtensionClassLibraryPtr library,
  GDExtensionInitialization *initialization)
{
  GDExtensionBinding::InitObject init(get_proc_address, library, initialization);
  init.register_initializer(iniciar);
  init.register_terminator(terminar);
  init.set_minimum_library_initialization_level(MODULE_INITIALIZATION_LEVEL_SCENE);
  return init.init();
}
