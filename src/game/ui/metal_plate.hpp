#pragma once

#include <godot_cpp/classes/canvas_item.hpp>
#include <godot_cpp/classes/control.hpp>
#include <godot_cpp/classes/label.hpp>
#include <godot_cpp/classes/tween.hpp>
#include <godot_cpp/classes/v_box_container.hpp>

// Brushed metal drawn from gradients and thin streaks, so it stays sharp and needs no texture.
// Canvas items keep what they drew, so all of this costs only when a menu changes.
namespace Metal
{
void gradient(godot::CanvasItem & canvas, const godot::Rect2 & area, const godot::Color & from, const godot::Color & to, bool across);
void sheet(godot::CanvasItem & canvas, const godot::Rect2 & area, const godot::Color & dark, const godot::Color & light, float band);
void bevel(godot::CanvasItem & canvas, const godot::Rect2 & area);
void drop_shadow(godot::CanvasItem & canvas, const godot::Rect2 & area);
void well(godot::CanvasItem & canvas, const godot::Rect2 & area);

// Swells a control past its size and settles it there: the small pop of anything picked.
godot::Ref<godot::Tween> pop(godot::Control & control, float settle);
}

// A surface behind text: the menu's sheet, or one row of a menu.
class MetalPlate : public godot::Control
{
  GDCLASS(MetalPlate, godot::Control)

protected:
  static void _bind_methods();
  void _notification(int what);

public:
  enum Style { STYLE_SHEET, STYLE_PLATE, STYLE_BRIGHT, STYLE_LINE, STYLE_NONE };

  static void add_row(godot::VBoxContainer * list, const godot::String & text, bool selected, const godot::String & value = godot::String());
  static void add_title_row(godot::VBoxContainer * list, const godot::String & text, bool selected, bool disabled);

  // Clearing or picking a row in place keeps it alive, so its tween can play.
  static void select_row(godot::VBoxContainer * list, int index, bool selected);
  static void set_row_value(godot::VBoxContainer * list, int index, const godot::String & value);

  void _draw() override;

  int get_style() const { return style; }
  void set_style(int value);

private:
  void paint();
  void settle_scale();
  void set_selected(bool value);

  int style = STYLE_PLATE;
  bool selected = false;
  bool title_row = false;
  godot::Label * label = nullptr;
  godot::Label * value_label = nullptr;
  godot::Ref<godot::Tween> tween;
};
