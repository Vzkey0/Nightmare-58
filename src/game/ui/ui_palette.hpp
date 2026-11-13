#pragma once

#include <godot_cpp/variant/color.hpp>

// The colors of the street itself: plaster, the green wash of the walls, terracotta and candle gold,
// with the hero's jacket for the accents. Health and stamina keep their own colors to read in a fight.
namespace UiPalette
{
inline const godot::Color PLASTER(0.9f, 0.85f, 0.73f);
inline const godot::Color PLASTER_SHADE(0.76f, 0.69f, 0.56f);
inline const godot::Color WALL(0.31f, 0.5f, 0.47f);
inline const godot::Color WALL_DARK(0.2f, 0.34f, 0.33f);
inline const godot::Color TERRACOTTA(0.7f, 0.36f, 0.23f);
inline const godot::Color CANDLE(0.95f, 0.72f, 0.3f);
inline const godot::Color GOLD_DARK(0.55f, 0.37f, 0.13f);
inline const godot::Color JACKET_YELLOW(0.98f, 0.8f, 0.16f);
inline const godot::Color JACKET_BLUE(0.13f, 0.27f, 0.62f);
inline const godot::Color JACKET_RED(0.78f, 0.14f, 0.13f);
inline const godot::Color INK(0.15f, 0.09f, 0.07f);
inline const godot::Color INK_MUTED(0.42f, 0.32f, 0.25f);
inline const godot::Color ON_PAINT(0.97f, 0.93f, 0.83f); // Text painted on a wall-colored strip.
inline const godot::Color SHADOW(0.1f, 0.06f, 0.05f, 0.6f); // Hard and offset, never blurred.
}

