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

add_library(nightmare58_core STATIC src/core/progression/skill_tree.cpp)
target_include_directories(nightmare58_core PUBLIC src)
target_link_libraries(nightmare58_core PUBLIC Designar::Designar)

enable_testing()
add_executable(test_core tests/test_core.cpp)
target_link_libraries(test_core PRIVATE nightmare58_core)
add_test(NAME core COMMAND test_core)

add_executable(Nightmare58 src/main.cpp)
target_link_libraries(Nightmare58 PRIVATE Designar::Designar)

add_library(nightmare58_ext SHARED src/game/designar_check.cpp src/game/register_types.cpp)
target_include_directories(nightmare58_ext PRIVATE src)
target_link_libraries(nightmare58_ext PRIVATE godot-cpp Designar::Designar)
get_target_property(GODOT_SUFFIX godot-cpp GODOTCPP_SUFFIX)
set_target_properties(nightmare58_ext PROPERTIES
  PREFIX ""
  OUTPUT_NAME "nightmare58${GODOT_SUFFIX}"
  LIBRARY_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}/game/bin"
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}/game/bin")
