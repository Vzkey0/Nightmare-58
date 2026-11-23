#pragma once

#include <godot_cpp/classes/audio_stream_player.hpp>
#include <godot_cpp/classes/color_rect.hpp>
#include <godot_cpp/classes/control.hpp>
#include <godot_cpp/classes/label.hpp>
#include <godot_cpp/classes/node3d.hpp>
#include <godot_cpp/classes/rich_text_label.hpp>
#include <godot_cpp/classes/input_event.hpp>

// The opening drive. The AnimationPlayer holds the whole script (docs/opening.md) and calls back
// here for what a timeline cannot do on its own: the street passing the windows, camera cuts,
// subtitles with the player's chosen name, and holding a key to skip to the avenue.
class OpeningCutscene : public godot::Node3D
{
  GDCLASS(OpeningCutscene, godot::Node3D)

protected:
  static void _bind_methods();

public:
  void _ready() override;
  void _process(double delta) override;
  void _unhandled_input(const godot::Ref<godot::InputEvent> & event) override;

  // The car never moves: the street goes by under it at this speed, in metres per second.
  float get_drive_speed() const { return drive_speed; }
  void set_drive_speed(float value) { drive_speed = value; }

  // Called from the animation's method track.
  void cut(const godot::String & camera);
  void say(const godot::String & who, const godot::String & line);
  void send(const godot::String & prop);
  void finish();

private:
  void scroll(godot::Node3D * strip, float distance);
  void make_room();
  void draw_skip_ring();
  void type(double delta);

  float drive_speed = 0.f;
  float skip_hold = 0.f;
  float hint_time = 0.f;
  double clock = 0.0;
  bool leaving = false;
  // The line being typed out: characters shown so far, counted as a float to pace them.
  float typed = 0.f;
  float key_wait = 0.f;
  bool typing = false;
  bool quiet = false;
  godot::String player_name;

  godot::Node3D * road = nullptr;
  godot::Node3D * skyline = nullptr;
  godot::Node3D * props = nullptr;
  godot::Node3D * camera_rig = nullptr;
  godot::RichTextLabel * subtitle = nullptr;
  godot::Control * skip_hint = nullptr;
  godot::Control * skip_ring = nullptr;
  godot::ColorRect * fade = nullptr;
  godot::AudioStreamPlayer * typewriter = nullptr;
  godot::AudioStreamPlayer * engine = nullptr;
};
