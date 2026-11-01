#include <gdextension_interface.h>
#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/core/defs.hpp>
#include <godot_cpp/godot.hpp>

#include "designar_check.hpp"
#include "player_controller.hpp"
#include "training_dummy.hpp"
#include "weapon_trail.hpp"

using namespace godot;

static void initialize(ModuleInitializationLevel level)
{
  if (level == MODULE_INITIALIZATION_LEVEL_SCENE)
  {
    GDREGISTER_CLASS(DesignarCheck);
    GDREGISTER_RUNTIME_CLASS(PlayerController);
    GDREGISTER_RUNTIME_CLASS(TrainingDummy);
    GDREGISTER_RUNTIME_CLASS(WeaponTrail);
  }
}

static void terminate(ModuleInitializationLevel) {}

extern "C" GDExtensionBool GDE_EXPORT nightmare58_init(
  GDExtensionInterfaceGetProcAddress get_proc_address,
  GDExtensionClassLibraryPtr library,
  GDExtensionInitialization *initialization)
{
  GDExtensionBinding::InitObject init(get_proc_address, library, initialization);
  init.register_initializer(initialize);
  init.register_terminator(terminate);
  init.set_minimum_library_initialization_level(MODULE_INITIALIZATION_LEVEL_SCENE);
  return init.init();
}
