#include <gdextension_interface.h>
#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/core/defs.hpp>
#include <godot_cpp/godot.hpp>

#include <game/enemies/combat_target.hpp>
#include <game/debug/designar_check.hpp>
#include <game/player/player_controller.hpp>
#include <game/enemies/skeleton_enemy.hpp>
#include <game/ui/bronze_plate.hpp>
#include <game/ui/game_menu.hpp>
#include <game/ui/item_slot.hpp>
#include <game/ui/stat_bar.hpp>
#include <game/enemies/training_dummy.hpp>
#include <game/weapons/weapon_trail.hpp>
#include <game/world/chapel.hpp>
#include <game/world/loot_pickup.hpp>
#include <game/world/lost_lochas.hpp>

using namespace godot;

static void initialize(ModuleInitializationLevel level)
{
  if (level == MODULE_INITIALIZATION_LEVEL_SCENE)
  {
    GDREGISTER_CLASS(DesignarCheck);
    GDREGISTER_RUNTIME_CLASS(PlayerController);
    GDREGISTER_RUNTIME_CLASS(StatBar);
    GDREGISTER_RUNTIME_CLASS(CombatTarget);
    GDREGISTER_RUNTIME_CLASS(SkeletonEnemy);
    GDREGISTER_RUNTIME_CLASS(TrainingDummy);
    GDREGISTER_RUNTIME_CLASS(WeaponTrail);
    GDREGISTER_RUNTIME_CLASS(GameMenu);
    GDREGISTER_RUNTIME_CLASS(ItemSlot);
    GDREGISTER_RUNTIME_CLASS(BronzePlate);
    GDREGISTER_RUNTIME_CLASS(Chapel);
    GDREGISTER_RUNTIME_CLASS(LostLochas);
    GDREGISTER_RUNTIME_CLASS(LootPickup);
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
