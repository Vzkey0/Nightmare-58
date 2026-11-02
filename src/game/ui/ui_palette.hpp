#pragma once

#include <godot_cpp/variant/color.hpp>

// The steel blue of every screen. Health and stamina keep their own colors to read in a fight.
namespace UiPalette
{
inline const godot::Color WELL_TOP(0.022f, 0.036f, 0.07f);
inline const godot::Color WELL_BOTTOM(0.055f, 0.085f, 0.15f);
inline const godot::Color BORDER(0.18f, 0.26f, 0.4f);
inline const godot::Color METAL(0.45f, 0.6f, 0.85f);
inline const godot::Color HIGHLIGHT(0.86f, 0.92f, 1.f);
inline const godot::Color MUTED(0.58f, 0.68f, 0.82f);
inline const godot::Color ON_BRIGHT(0.02f, 0.04f, 0.09f);
inline const godot::Color ICE(0.62f, 0.76f, 1.f);
inline const godot::Color TEXT_SHADOW(0.f, 0.f, 0.f, 0.8f);
}
