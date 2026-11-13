#pragma once

#include <godot_cpp/classes/node.hpp>

// The menus' sounds live in the UiSounds autoload (scenes/ui_sounds.tscn): the pause menu needs
// them with the tree paused, and the title screen's last click has to outlast its own scene.
namespace UiSounds
{
// sound: one of Move, Adjust, Accept, Back, Tab, Open, Close, Deny.
void play(godot::Node * from, const char * sound);
}
