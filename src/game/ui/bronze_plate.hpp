#pragma once

#include <godot_cpp/classes/canvas_item.hpp>
#include <godot_cpp/classes/control.hpp>

// Brushed bronze drawn from gradients and thin streaks, so it stays sharp and needs no texture.
// Canvas items keep what they drew, so all of this costs only when a menu changes.
namespace Bronze
{
void gradient(godot::CanvasItem & canvas, const godot::Rect2 & area, const godot::Color & from, const godot::Color & to, bool across);
void metal(godot::CanvasItem & canvas, const godot::Rect2 & area, const godot::Color & dark, const godot::Color & light, float band);
void bevel(godot::CanvasItem & canvas, const godot::Rect2 & area);
void drop_shadow(godot::CanvasItem & canvas, const godot::Rect2 & area);
void well(godot::CanvasItem & canvas, const godot::Rect2 & area);
}

// A surface behind text: the menu's sheet, a plate, the selected plate.
class BronzePlate : public godot::Control
{
  GDCLASS(BronzePlate, godot::Control)

protected:
  static void _bind_methods();

public:
  enum Style { STYLE_SHEET, STYLE_PLATE, STYLE_BRIGHT };

  void _draw() override;

  int get_style() const { return style; }
  void set_style(int value);

private:
  int style = STYLE_PLATE;
};
