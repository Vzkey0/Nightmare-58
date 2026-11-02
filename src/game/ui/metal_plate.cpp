#include "metal_plate.hpp"
#include "ui_palette.hpp"

#include <godot_cpp/classes/property_tweener.hpp>
#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/core/math.hpp>
#include <godot_cpp/variant/packed_color_array.hpp>
#include <godot_cpp/variant/packed_vector2_array.hpp>

using namespace godot;

namespace
{
const Color SHEET_DARK(0.035f, 0.055f, 0.1f, 0.97f);
const Color SHEET_LIGHT(0.09f, 0.14f, 0.25f, 0.97f);
const Color PLATE_DARK(0.075f, 0.115f, 0.2f);
const Color PLATE_LIGHT(0.14f, 0.21f, 0.35f);
const Color BRIGHT_DARK(0.3f, 0.42f, 0.66f);
const Color BRIGHT_LIGHT(0.64f, 0.78f, 1.f);
const Color SHINE(0.8f, 0.9f, 1.f, 0.55f);
const Color CLEAR(0.f, 0.f, 0.f, 0.f);

constexpr float SHEET_BAND = 240.f;
constexpr float PLATE_BAND = 150.f;
constexpr float COLUMN = 12.f;
constexpr float STREAK_GAP = 2.5f;
constexpr float STREAK_ALPHA = 0.1f;
constexpr int SHADOW_LAYERS = 4;
constexpr float SHEET_SHADOW = 90.f;
constexpr float ROW_HEIGHT = 58.f;
constexpr float ROW_MARGIN = 20.f;
constexpr float TITLE_ROW_HEIGHT = 70.f;
constexpr float TITLE_ROW_INDENT = 100.f;

constexpr float PLATE_SCALE = 1.02f;
constexpr float TITLE_SCALE = 1.14f;
constexpr float POP_OVERSHOOT = 0.05f;
constexpr float POP_RISE = 0.08f;
constexpr float POP_SETTLE = 0.13f;
constexpr float RELEASE_TIME = 0.12f;

// A fixed pattern: the same plate must not shimmer each time a menu redraws it.
float noise(int seed)
{
  const float value = Math::sin(seed * 12.9898f) * 43758.5453f;
  return value - Math::floor(value);
}

// Broad bands of unequal width, as light falls on a curved sheet of metal.
float sheen(float x, float band)
{
  return 0.5f + 0.32f * Math::sin(x / band * 3.1f + 0.6f) + 0.18f * Math::sin(x / band * 7.3f + 2.f);
}

Label * add_label(MetalPlate * row, const String & text, HorizontalAlignment align, int size)
{
  Label * label = memnew(Label);
  row->add_child(label);
  label->set_anchors_and_offsets_preset(Control::PRESET_FULL_RECT);
  label->set_text(text);
  label->set_horizontal_alignment(align);
  label->set_vertical_alignment(VERTICAL_ALIGNMENT_CENTER);
  label->add_theme_font_size_override("font_size", size);
  return label;
}
}

void Metal::gradient(CanvasItem & canvas, const Rect2 & area, const Color & from, const Color & to, bool across)
{
  PackedVector2Array points;
  points.push_back(area.position);
  points.push_back(area.position + Vector2(area.size.x, 0.f));
  points.push_back(area.position + area.size);
  points.push_back(area.position + Vector2(0.f, area.size.y));
  PackedColorArray colors;
  colors.push_back(from);
  colors.push_back(across ? to : from);
  colors.push_back(to);
  colors.push_back(across ? from : to);
  canvas.draw_polygon(points, colors);
}

void Metal::sheet(CanvasItem & canvas, const Rect2 & area, const Color & dark, const Color & light, float band)
{
  const int columns = MAX(1, static_cast<int>(area.size.x / COLUMN));
  const float width = area.size.x / columns;
  for (int i = 0; i < columns; ++i)
  {
    const Rect2 strip(area.position + Vector2(width * i, 0.f), Vector2(width, area.size.y));
    gradient(canvas, strip, dark.lerp(light, sheen(width * i, band)), dark.lerp(light, sheen(width * (i + 1), band)), true);
  }

  const int streaks = static_cast<int>(area.size.x / STREAK_GAP);
  for (int i = 0; i < streaks; ++i)
  {
    const float x = area.position.x + area.size.x * noise(i);
    const float top = area.position.y + area.size.y * noise(i + 1000) * 0.8f;
    const float length = area.size.y * (0.2f + 0.8f * noise(i + 2000));
    const float bottom = MIN(top + length, area.position.y + area.size.y);
    const Color tint = i % 2 == 0 ? Color(0.8f, 0.9f, 1.f) : Color(0.f, 0.f, 0.f);
    canvas.draw_line(Vector2(x, top), Vector2(x, bottom), Color(tint, STREAK_ALPHA * noise(i + 3000)), 1.f);
  }
}

void Metal::bevel(CanvasItem & canvas, const Rect2 & area)
{
  const Vector2 top_left = area.position;
  const Vector2 top_right = top_left + Vector2(area.size.x, 0.f);
  const Vector2 bottom_left = top_left + Vector2(0.f, area.size.y);
  const Vector2 bottom_right = top_left + area.size;
  canvas.draw_line(top_left, top_right, SHINE, 2.f);
  canvas.draw_line(top_left, bottom_left, Color(SHINE, 0.25f), 1.f);
  canvas.draw_line(bottom_left, bottom_right, Color(0.f, 0.f, 0.f, 0.7f), 2.f);
  canvas.draw_line(top_right, bottom_right, Color(0.f, 0.f, 0.f, 0.45f), 1.f);
}

// Stacked instead of blurred, like the bars of the HUD.
void Metal::drop_shadow(CanvasItem & canvas, const Rect2 & area)
{
  for (int layer = SHADOW_LAYERS; layer > 0; --layer)
    canvas.draw_rect(area.grow(layer * 1.5f).grow_side(SIDE_BOTTOM, layer * 1.5f), Color(0.f, 0.f, 0.f, 0.14f));
}

void Metal::well(CanvasItem & canvas, const Rect2 & area)
{
  gradient(canvas, area, UiPalette::WELL_TOP, UiPalette::WELL_BOTTOM, false);
  gradient(canvas, Rect2(area.position, Vector2(area.size.x, area.size.y * 0.16f)), Color(0.f, 0.f, 0.f, 0.6f), CLEAR, false);
  canvas.draw_rect(area, UiPalette::BORDER, false, 1.f);
  canvas.draw_line(area.position + Vector2(1.f, area.size.y + 1.f), area.position + area.size + Vector2(0.f, 1.f), Color(SHINE, 0.22f), 1.f);
}

Ref<Tween> Metal::pop(Control & control, float settle)
{
  const Vector2 rest(settle, settle);
  Ref<Tween> tween = control.create_tween();
  tween->tween_property(&control, "scale", rest * (1.f + POP_OVERSHOOT), POP_RISE)->set_trans(Tween::TRANS_BACK)->set_ease(Tween::EASE_OUT);
  tween->tween_property(&control, "scale", rest, POP_SETTLE)->set_trans(Tween::TRANS_SINE)->set_ease(Tween::EASE_IN_OUT);
  return tween;
}

void MetalPlate::_bind_methods()
{
  ClassDB::bind_method(D_METHOD("get_style"), &MetalPlate::get_style);
  ClassDB::bind_method(D_METHOD("set_style", "value"), &MetalPlate::set_style);
  ADD_PROPERTY(PropertyInfo(Variant::INT, "style", PROPERTY_HINT_ENUM, "Sheet,Plate,Bright,Line,None"), "set_style", "get_style");
}

void MetalPlate::_notification(int what)
{
  if (what == NOTIFICATION_RESIZED)
    set_pivot_offset(Vector2(title_row ? TITLE_ROW_INDENT : get_size().x * 0.5f, get_size().y * 0.5f));
}

void MetalPlate::set_style(int value)
{
  style = value;
  queue_redraw();
}

void MetalPlate::add_row(VBoxContainer * list, const String & text, bool is_selected, const String & value)
{
  MetalPlate * row = memnew(MetalPlate);
  row->set_custom_minimum_size(Vector2(0.f, ROW_HEIGHT));
  row->set_mouse_filter(MOUSE_FILTER_IGNORE);
  list->add_child(row);

  row->label = add_label(row, text, HORIZONTAL_ALIGNMENT_LEFT, 26);
  row->value_label = add_label(row, value, HORIZONTAL_ALIGNMENT_RIGHT, 24);
  for (Label * side : {row->label, row->value_label})
  {
    side->set_offset(SIDE_LEFT, ROW_MARGIN);
    side->set_offset(SIDE_RIGHT, -ROW_MARGIN);
  }
  row->selected = is_selected;
  row->paint();
  // Arranging its rows sets their scale back to 1, so a selected row waits for that.
  list->connect("sort_children", callable_mp(row, &MetalPlate::settle_scale));
}

void MetalPlate::add_title_row(VBoxContainer * list, const String & text, bool is_selected, bool disabled)
{
  MetalPlate * row = memnew(MetalPlate);
  row->title_row = true;
  row->set_custom_minimum_size(Vector2(0.f, TITLE_ROW_HEIGHT));
  row->set_mouse_filter(MOUSE_FILTER_IGNORE);
  list->add_child(row);

  row->label = add_label(row, text, HORIZONTAL_ALIGNMENT_LEFT, 32);
  row->label->set_offset(SIDE_LEFT, TITLE_ROW_INDENT);
  row->label->add_theme_color_override("font_shadow_color", UiPalette::TEXT_SHADOW);
  if (disabled)
    row->label->set_modulate(Color(1.f, 1.f, 1.f, 0.35f));
  row->selected = is_selected;
  row->paint();
  list->connect("sort_children", callable_mp(row, &MetalPlate::settle_scale));
}

void MetalPlate::settle_scale()
{
  if (selected)
    set_scale(Vector2(1.f, 1.f) * (title_row ? TITLE_SCALE : PLATE_SCALE));
}

void MetalPlate::paint()
{
  if (title_row)
  {
    set_style(selected ? STYLE_LINE : STYLE_NONE);
    label->add_theme_color_override("font_color", selected ? Color(1.f, 1.f, 1.f) : UiPalette::MUTED);
    return;
  }

  set_style(selected ? STYLE_BRIGHT : STYLE_PLATE);
  for (Label * side : {label, value_label})
  {
    side->add_theme_color_override("font_color", selected ? UiPalette::ON_BRIGHT : UiPalette::HIGHLIGHT);
    side->add_theme_color_override("font_shadow_color", selected ? Color(1.f, 1.f, 1.f, 0.3f) : UiPalette::TEXT_SHADOW);
  }
}

void MetalPlate::set_selected(bool value)
{
  selected = value;
  paint();
  if (tween.is_valid())
    tween->kill();

  if (selected)
    tween = Metal::pop(*this, title_row ? TITLE_SCALE : PLATE_SCALE);
  else
  {
    tween = create_tween();
    tween->tween_property(this, "scale", Vector2(1.f, 1.f), RELEASE_TIME)->set_trans(Tween::TRANS_SINE)->set_ease(Tween::EASE_OUT);
  }
}

void MetalPlate::select_row(VBoxContainer * list, int index, bool value)
{
  if (index >= 0 && index < list->get_child_count())
    Object::cast_to<MetalPlate>(list->get_child(index))->set_selected(value);
}

void MetalPlate::set_row_value(VBoxContainer * list, int index, const String & value)
{
  MetalPlate * row = Object::cast_to<MetalPlate>(list->get_child(index));
  row->value_label->set_text(value);
  row->set_selected(true);
}

void MetalPlate::_draw()
{
  const Rect2 area(Vector2(), get_size());
  if (style == STYLE_NONE)
    return;
  if (style == STYLE_LINE)
  {
    Metal::gradient(*this, Rect2(TITLE_ROW_INDENT - 12.f, area.size.y - 8.f, area.size.x - TITLE_ROW_INDENT + 12.f, 2.f), Color(1.f, 1.f, 1.f, 0.9f), Color(UiPalette::ICE, 0.2f), true);
    return;
  }
  if (style == STYLE_SHEET)
  {
    Metal::gradient(*this, Rect2(-SHEET_SHADOW, 0.f, SHEET_SHADOW, area.size.y), CLEAR, Color(0.f, 0.f, 0.f, 0.65f), true);
    Metal::sheet(*this, area, SHEET_DARK, SHEET_LIGHT, SHEET_BAND);
    Metal::gradient(*this, area, Color(0.75f, 0.85f, 1.f, 0.05f), Color(0.f, 0.f, 0.f, 0.5f), false);
    Metal::gradient(*this, Rect2(0.f, 0.f, 3.f, area.size.y), SHINE, Color(SHINE, 0.1f), false);
    return;
  }

  Metal::drop_shadow(*this, area);
  if (style == STYLE_BRIGHT)
    Metal::sheet(*this, area, BRIGHT_DARK, BRIGHT_LIGHT, PLATE_BAND);
  else
    Metal::sheet(*this, area, PLATE_DARK, PLATE_LIGHT, PLATE_BAND);
  Metal::gradient(*this, area, Color(0.85f, 0.92f, 1.f, 0.14f), Color(0.f, 0.f, 0.f, 0.3f), false);
  Metal::bevel(*this, area);
}
