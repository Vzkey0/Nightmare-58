#pragma once

#include <functional>
#include <vector>

#include <godot_cpp/classes/audio_stream_player.hpp>
#include <godot_cpp/classes/control.hpp>
#include <godot_cpp/classes/input_event.hpp>
#include <godot_cpp/classes/rich_text_label.hpp>
#include <godot_cpp/classes/texture_rect.hpp>
#include <godot_cpp/variant/string.hpp>

class KeyButton;

struct DialogueLine
{
  godot::String speaker; // Empty or "P" uses the player's chosen name; any other string is an NPC name.
  godot::String text;
  bool npc_speaks = true;
};

// Minimalist bottom-screen cinematic subtitles with typewriter audio and a KeyButton prompt.
class DialogueBox : public godot::Control
{
  GDCLASS(DialogueBox, godot::Control)

protected:
  static void _bind_methods() {}

public:
  void _ready() override;
  void _process(double delta) override;
  void _unhandled_input(const godot::Ref<godot::InputEvent> & event) override;

  bool is_open() const { return open_state; }
  bool holds_input() const;

  void start(
    const std::vector<DialogueLine> & lines,
    const godot::String & player_name,
    std::function<void(bool)> on_speaker_change = nullptr,
    std::function<void()> on_complete = nullptr);

  void close();

private:
  void show_current();
  void advance();

  godot::TextureRect * shade = nullptr;
  godot::RichTextLabel * body = nullptr;
  KeyButton * hint_button = nullptr;
  godot::AudioStreamPlayer * typewriter = nullptr;

  std::vector<DialogueLine> queue;
  godot::String protagonist_name;
  std::function<void(bool)> speaker_callback;
  std::function<void()> complete_callback;

  int index = 0;
  bool open_state = false;
  bool typing = false;
  float typed = 0.f;
  float key_wait = 0.f;
  uint64_t closed_frame = 0;
};
