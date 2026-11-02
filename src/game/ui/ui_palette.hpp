#pragma once

#include <godot_cpp/variant/color.hpp>

// The bronze of every screen. Health and stamina keep their own colors to read in a fight.
namespace UiPalette
{
inline const godot::Color WELL_TOP(0.055f, 0.043f, 0.033f);
inline const godot::Color WELL_BOTTOM(0.115f, 0.092f, 0.07f);
inline const godot::Color BORDER(0.3f, 0.245f, 0.185f);
inline const godot::Color BRONZE(0.66f, 0.54f, 0.41f);
inline const godot::Color HIGHLIGHT(0.95f, 0.87f, 0.75f);
inline const godot::Color MUTED(0.74f, 0.66f, 0.56f);
inline const godot::Color ON_BRIGHT(0.09f, 0.065f, 0.045f);
inline const godot::Color TEXT_SHADOW(0.f, 0.f, 0.f, 0.8f);
}
