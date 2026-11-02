#include "ui_sounds.hpp"

#include <godot_cpp/classes/audio_stream_player.hpp>
#include <godot_cpp/variant/node_path.hpp>
#include <godot_cpp/variant/string.hpp>

using namespace godot;

void UiSounds::play(Node * from, const char * sound)
{
  from->get_node<AudioStreamPlayer>(NodePath(String("/root/UiSounds/") + sound))->play();
}
