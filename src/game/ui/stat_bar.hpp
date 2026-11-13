#pragma once

#include <godot_cpp/classes/control.hpp>
#include <godot_cpp/variant/color.hpp>
#include <godot_cpp/variant/packed_vector2_array.hpp>

// A pointed metal frame whose fill has the same point, so the fill always fits the frame.
// Drawn from polygons with flat facets instead of images: it stays sharp at any resolution.
class StatBar : public godot::Control
{
  GDCLASS(StatBar, godot::Control)

protected:
  static void _bind_methods();

public:
  void _draw() override;

  // Values go from 0 to 1. A trail of 0 draws no trail.
  void set_values(float new_fill, float new_trail);

  godot::Color get_fill_color() const { return fill_color; }
  void set_fill_color(const godot::Color & value);
  float get_tip() const { return tip; }
  void set_tip(float value) { tip = value; }
  float get_start() const { return start; }
  void set_start(float value) { start = value; }

private:
  godot::PackedVector2Array frame_shape(float inset) const;
  godot::PackedVector2Array filled_shape(float ratio) const;
  godot::PackedVector2Array facets(float edge, float direction) const;
  void draw_clipped(const godot::PackedVector2Array & shape, const godot::PackedVector2Array & band, const godot::Color & color);

  godot::Color fill_color = godot::Color(1, 1, 1);
  float tip = 10.f;
  float start = 3.f; // Where a value of 0 ends: a frame's end may hide under another element.
  float fill = 1.f;
  float trail = 0.f;
};
