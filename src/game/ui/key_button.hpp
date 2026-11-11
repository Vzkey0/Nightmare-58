#pragma once

#include <godot_cpp/classes/control.hpp>
#include <godot_cpp/classes/tween.hpp>

// A small plaster plaque with its key boxed in ink, "E  aprender": a button, not loose letters.
// set_text takes "<key>  <action>"; text with no double space is a plaque without a key.
// It swells under the mouse, squashes when pressed and pops in whenever its text changes.
class KeyButton : public godot::Control
{
  GDCLASS(KeyButton, godot::Control)

protected:
  static void _bind_methods();
  void _notification(int what);

public:
  void _draw() override;

  void set_text(const godot::String & text);
  godot::String get_text() const { return text; }
  int get_align() const { return align; }
  void set_align(int value);

  // Greyed out while its action cannot happen; it still shows which key it would take.
  void set_disabled(bool value);

  // The squash of a pressed key, for presses made from the keyboard too.
  void press();

  // The plaque as drawn, which may be narrower than the control.
  godot::Rect2 plate_rect() const;

private:
  void hover(bool on);
  void scale_to(float value, float time);
  void set_flash(float value);

  godot::String text;
  godot::String key;
  godot::String action;
  int align = 0; // 0 left, 1 center, 2 right.
  bool hovered = false;
  bool disabled = false;
  float flash = 0.f;
  godot::Ref<godot::Tween> tween;
};
