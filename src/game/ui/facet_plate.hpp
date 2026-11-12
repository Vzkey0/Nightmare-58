#pragma once

#include <godot_cpp/classes/canvas_item.hpp>
#include <godot_cpp/classes/control.hpp>
#include <godot_cpp/classes/label.hpp>
#include <godot_cpp/classes/texture_rect.hpp>
#include <godot_cpp/classes/tween.hpp>
#include <godot_cpp/classes/v_box_container.hpp>

// Broken plaster and painted strips, drawn as flat polygons with a small tiled grain.
// Canvas items keep what they drew, so all of this costs only when a menu changes.
namespace Facet
{
// A rectangle with its corners cut and its edges chipped; the same seed always breaks the same way.
godot::PackedVector2Array outline(const godot::Rect2 & area, int seed, float cut, float chip);

// Fills a shape with plaster grain under a hard shadow pushed down and right, never blurred.
void panel(godot::CanvasItem & canvas, const godot::PackedVector2Array & shape, const godot::Color & color, const godot::Vector2 & shadow);

godot::Ref<godot::Texture2D> texture(const char * name);

// The icon rendered for a skill or stat, or none when it has not been modeled.
godot::Ref<godot::Texture2D> skill_icon(const char * key);

// Swells a control past its size and settles it there: the small pop of anything picked.
godot::Ref<godot::Tween> pop(godot::Control & control, float settle);

// The candle flame bobbing in place; its tween loops until the candle is freed.
void flicker(godot::Control & candle);
}

// A surface behind text: the plaster sheet of a menu, one painted strip of it, or a small plaque.
class FacetPlate : public godot::Control
{
  GDCLASS(FacetPlate, godot::Control)

protected:
  static void _bind_methods();
  void _notification(int what);

public:
  enum Style { STYLE_SHEET, STYLE_STRIP, STYLE_SELECTED, STYLE_TAG, STYLE_HEADER, STYLE_NONE };

  static void add_row(godot::VBoxContainer * list, const godot::String & text, bool selected, const godot::String & value = godot::String());

  // Clearing or picking a row in place keeps it alive, so its tween can play.
  static void select_row(godot::VBoxContainer * list, int index, bool selected);
  static void set_row_value(godot::VBoxContainer * list, int index, const godot::String & value);

  void _draw() override;

  int get_style() const { return style; }
  void set_style(int value);
  int get_seed() const { return seed; }
  void set_seed(int value);

private:
  void paint();
  void set_selected(bool value);
  void settle_scale();

  int style = STYLE_STRIP;
  int seed = 0;
  bool selected = false;
  godot::Label * label = nullptr;
  godot::Label * value_label = nullptr;
  godot::TextureRect * candle = nullptr;
  godot::Ref<godot::Tween> tween;
};
