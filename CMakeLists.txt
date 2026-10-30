cmake_minimum_required(VERSION 3.20)
project(Nightmare58 CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(NOT EXISTS "${CMAKE_SOURCE_DIR}/extern/DeSiGNAR/CMakeLists.txt")
  message(FATAL_ERROR "Falta DeSiGNAR. Ejecuta: git submodule update --init")
endif()

set(DESIGNAR_BUILD_SAMPLES OFF)
set(DESIGNAR_BUILD_TESTS OFF)
add_subdirectory(extern/DeSiGNAR)

add_executable(Nightmare58 src/main.cpp)
target_link_libraries(Nightmare58 PRIVATE Designar::Designar)
