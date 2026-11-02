cmake_minimum_required(VERSION 3.20)
project(Nightmare58 CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

foreach(dep DeSiGNAR godot-cpp)
  if(NOT EXISTS "${CMAKE_SOURCE_DIR}/extern/${dep}/CMakeLists.txt")
    message(FATAL_ERROR "Missing ${dep}. Run: git submodule update --init")
  endif()
endforeach()

set(DESIGNAR_BUILD_SAMPLES OFF)
set(DESIGNAR_BUILD_TESTS OFF)
add_subdirectory(extern/DeSiGNAR)

# DeSiGNAR throws exceptions; godot-cpp disables them by default.
set(GODOTCPP_DISABLE_EXCEPTIONS OFF CACHE BOOL "" FORCE)
set(GODOTCPP_API_VERSION "4.7" CACHE STRING "" FORCE)
add_subdirectory(extern/godot-cpp)

add_library(nightmare58_core STATIC
  src/core/progression/inventory.cpp
  src/core/progression/item_catalog.cpp
  src/core/progression/player_progress.cpp
  src/core/progression/skill_tree.cpp
  src/core/ai/behavior_tree.cpp
  src/core/ai/enemy_actions.cpp
  src/core/player/player_actions.cpp)
target_include_directories(nightmare58_core PUBLIC src)
target_link_libraries(nightmare58_core PUBLIC Designar::Designar)

enable_testing()
add_executable(test_core tests/test_core.cpp)
target_link_libraries(test_core PRIVATE nightmare58_core)
add_test(NAME core COMMAND test_core)

add_executable(behavior_tree_benchmark benchmarks/behavior_tree_benchmark.cpp)
target_link_libraries(behavior_tree_benchmark PRIVATE Designar::Designar)

add_executable(input_buffer_benchmark benchmarks/input_buffer_benchmark.cpp)
target_link_libraries(input_buffer_benchmark PRIVATE Designar::Designar)

add_executable(enemy_ai_benchmark benchmarks/enemy_ai_benchmark.cpp)
target_link_libraries(enemy_ai_benchmark PRIVATE nightmare58_core)

add_executable(progression_benchmark benchmarks/progression_benchmark.cpp)
target_link_libraries(progression_benchmark PRIVATE nightmare58_core)

add_executable(Nightmare58 src/main.cpp)
target_link_libraries(Nightmare58 PRIVATE Designar::Designar)

add_library(nightmare58_ext SHARED
  src/game/enemies/combat_target.cpp
  src/game/debug/designar_check.cpp
  src/game/player/player_controller.cpp
  src/game/register_types.cpp
  src/game/enemies/skeleton_enemy.cpp
  src/game/ui/bronze_plate.cpp
  src/game/ui/game_menu.cpp
  src/game/ui/item_slot.cpp
  src/game/ui/stat_bar.cpp
  src/game/enemies/training_dummy.cpp
  src/game/weapons/weapon_trail.cpp
  src/game/world/chapel.cpp
  src/game/world/loot_pickup.cpp
  src/game/world/lost_lochas.cpp
  src/game/world/save_file.cpp)
target_include_directories(nightmare58_ext PRIVATE src)
target_link_libraries(nightmare58_ext PRIVATE godot-cpp nightmare58_core)
get_target_property(GODOT_SUFFIX godot-cpp GODOTCPP_SUFFIX)
set_target_properties(nightmare58_ext PROPERTIES
  PREFIX ""
  OUTPUT_NAME "nightmare58${GODOT_SUFFIX}"
  LIBRARY_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}/game/bin"
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}/game/bin")
