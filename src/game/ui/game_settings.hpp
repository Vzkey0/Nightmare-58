#pragma once

#include <godot_cpp/variant/rect2.hpp>
#include <godot_cpp/variant/string.hpp>

// Volume and mouse sensitivity, shared by the title screen and the pause menu.
namespace GameSettings
{
constexpr int ROWS = 2;

void load();
float mouse_scale();

// Moves a row one notch, applies it at once and writes it to disk.
void step(int row, int direction);

// Which way a click on a row moves it: its < lowers, its > raises, and its name does nothing.
int click_direction(const godot::Rect2 & row, float x);
godot::String row_name(int row);
godot::String row_value(int row);
}
