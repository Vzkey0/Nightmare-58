#include "facet_plate.hpp"
#include "ui_palette.hpp"

#include <godot_cpp/classes/geometry2d.hpp>
#include <godot_cpp/classes/property_tweener.hpp>
#include <godot_cpp/classes/resource_loader.hpp>
#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/core/math.hpp>
#include <godot_cpp/variant/typed_array.hpp>

using namespace godot;

namespace
{
constexpr float GRAIN_TILE = 128.f; // Screen pixels per tile of plaster.png.
constexpr float EDGE_WIDTH = 2.f;
constexpr float EDGE_DARKEN = 0.28f;
constexpr float CHIP_CHANCE = 0.45f;
constexpr float CHIP_GAP = 70.f; // Average room along an edge for one chip.

const Vector2 SHEET_SHADOW(14.f, 16.f);
const Vector2 STRIP_SHADOW(5.f, 6.f);
constexpr float SHEET_CUT = 30.f;
constexpr float SHEET_CHIP = 12.f;
constexpr float STRIP_CUT = 9.f;
constexpr float STRIP_CHIP = 4.f;
constexpr float BASEBOARD_SHARE = 0.085f; // The terracotta band at the foot of a sheet, as on the walls.
constexpr float SIGN_BORDER = 7.f;
constexpr float BAND_SHARE = 0.16f; // Each of the blue and red bands under the selected yellow.

constexpr float ROW_HEIGHT = 58.f;
constexpr float ROW_MARGIN = 20.f;
constexpr float CANDLE_SIZE = 50.f;
constexpr float CANDLE_INDENT = 64.f;
constexpr float ROW_SCALE = 1.03f;

constexpr float POP_OVERSHOOT = 0.05f;
constexpr float POP_RISE = 0.08f;
constexpr float POP_SETTLE = 0.13f;
constexpr float RELEASE_TIME = 0.12f;
constexpr float FLICKER_TIME = 0.32f;
constexpr float FLICKER_STRETCH = 0.1f;

// A fixed pattern: the same plate must not shift each time a menu redraws it.
float noise(int seed)
{
  const float value = Math::sin(seed * 12.9898f) * 43758.5453f;
  return value - Math::floor(value);
}

// The points from one corner cut to the next, notched now and then where the plaster fell off.
void chipped_edge(PackedVector2Array & points, const Vector2 & from, const Vector2 & to, int seed, float chip)
{
  points.push_back(from);
  const Vector2 along = to - from;
  const float length = along.length();
  if (chip <= 0.f || length < CHIP_GAP)
    return;
  const Vector2 direction = along / length;
  const Vector2 inward(-direction.y, direction.x); // The outline runs clockwise on screen.
  const int slots = static_cast<int>(length / CHIP_GAP);
  for (int i = 0; i < slots; ++i)
  {
    if (noise(seed * 31 + i) > CHIP_CHANCE)
      continue;
    const float center = (i + 0.25f + 0.5f * noise(seed * 17 + i)) * length / slots;
    const float half = chip * (0.8f + 1.6f * noise(seed * 13 + i));
    const float depth = chip * (0.4f + 0.6f * noise(seed * 7 + i));
    points.push_back(from + direction * (center - half));
    points.push_back(from + direction * (center - half * 0.2f) + inward * depth);
    points.push_back(from + direction * (center + half * 0.6f) + inward * depth * 0.55f);
    points.push_back(from + direction * (center + half));
  }
}

Label * add_label(FacetPlate * row, const String & text, HorizontalAlignment align)
{
  Label * label = memnew(Label);
  row->add_child(label);
  label->set_anchors_and_offsets_preset(Control::PRESET_FULL_RECT);
  label->set_text(text);
  label->set_horizontal_alignment(align);
  label->set_vertical_alignment(VERTICAL_ALIGNMENT_CENTER);
  label->set_theme_type_variation("SignLabel");
  return label;
}

PackedVector2Array clip(const PackedVector2Array & shape, const Rect2 & band)
{
  PackedVector2Array box;
  box.push_back(band.position);
  box.push_back(band.position + Vector2(band.size.x, 0.f));
  box.push_back(band.position + band.size);
  box.push_back(band.position + Vector2(0.f, band.size.y));
  const TypedArray<PackedVector2Array> pieces = Geometry2D::get_singleton()->intersect_polygons(shape, box);
  return pieces.is_empty() ? PackedVector2Array() : PackedVector2Array(pieces[0]);
}
}

PackedVector2Array Facet::outline(const Rect2 & area, int seed, float cut, float chip)
{
  const float x0 = area.position.x;
  const float y0 = area.position.y;
  const float x1 = area.get_end().x;
  const float y1 = area.get_end().y;
  // Each corner is cut a little differently, as broken plaster would be.
  float cuts[4];
  for (int i = 0; i < 4; ++i)
    cuts[i] = cut * (0.55f + 0.9f * noise(seed * 5 + i));

  PackedVector2Array points;
  chipped_edge(points, Vector2(x0 + cuts[0], y0), Vector2(x1 - cuts[1], y0), seed + 1, chip);
  chipped_edge(points, Vector2(x1, y0 + cuts[1]), Vector2(x1, y1 - cuts[2]), seed + 2, chip);
  chipped_edge(points, Vector2(x1 - cuts[2], y1), Vector2(x0 + cuts[3], y1), seed + 3, chip);
  chipped_edge(points, Vector2(x0, y1 - cuts[3]), Vector2(x0, y0 + cuts[0]), seed + 4, chip);
  return points;
}

void Facet::panel(CanvasItem & canvas, const PackedVector2Array & shape, const Color & color, const Vector2 & shadow)
{
  if (shape.size() < 3)
    return;
  if (shadow != Vector2())
  {
    PackedVector2Array moved = shape;
    for (int i = 0; i < moved.size(); ++i)
      moved[i] += shadow;
    canvas.draw_colored_polygon(moved, UiPalette::SHADOW);
  }
  PackedVector2Array uvs;
  uvs.resize(shape.size());
  for (int i = 0; i < shape.size(); ++i)
    uvs[i] = shape[i] / GRAIN_TILE;
  static Ref<Texture2D> grain = texture("plaster");
  canvas.draw_colored_polygon(shape, color, uvs, grain);
  PackedVector2Array edge = shape;
  edge.push_back(shape[0]);
  canvas.draw_polyline(edge, color.darkened(EDGE_DARKEN), EDGE_WIDTH);
}

Ref<Texture2D> Facet::texture(const char * name)
{
  return ResourceLoader::get_singleton()->load(vformat("res://ui/street/%s.png", name));
}

Ref<Texture2D> Facet::skill_icon(const char * key)
{
  const String path = vformat("res://ui/street/skills/%s.png", key);
  return ResourceLoader::get_singleton()->exists(path) ? Ref<Texture2D>(ResourceLoader::get_singleton()->load(path)) : Ref<Texture2D>();
}

Ref<Tween> Facet::pop(Control & control, float settle)
{
  const Vector2 rest(settle, settle);
  Ref<Tween> tween = control.create_tween();
  tween->tween_property(&control, "scale", rest * (1.f + POP_OVERSHOOT), POP_RISE)->set_trans(Tween::TRANS_BACK)->set_ease(Tween::EASE_OUT);
  tween->tween_property(&control, "scale", rest, POP_SETTLE)->set_trans(Tween::TRANS_SINE)->set_ease(Tween::EASE_IN_OUT);
  return tween;
}

void Facet::flicker(Control & candle)
{
  candle.set_pivot_offset(Vector2(candle.get_size().x * 0.5f, candle.get_size().y));
  Ref<Tween> tween = candle.create_tween();
  tween->set_loops();
  tween->tween_property(&candle, "scale", Vector2(1.f - FLICKER_STRETCH * 0.4f, 1.f + FLICKER_STRETCH), FLICKER_TIME)->set_trans(Tween::TRANS_SINE);
  tween->tween_property(&candle, "scale", Vector2(1.f, 1.f), FLICKER_TIME * 1.3f)->set_trans(Tween::TRANS_SINE);
}

void FacetPlate::_bind_methods()
{
  ClassDB::bind_method(D_METHOD("get_style"), &FacetPlate::get_style);
  ClassDB::bind_method(D_METHOD("set_style", "value"), &FacetPlate::set_style);
  ClassDB::bind_method(D_METHOD("get_seed"), &FacetPlate::get_seed);
  ClassDB::bind_method(D_METHOD("set_seed", "value"), &FacetPlate::set_seed);
  ADD_PROPERTY(PropertyInfo(Variant::INT, "style", PROPERTY_HINT_ENUM, "Sheet,Strip,Selected,Tag,Header,None"), "set_style", "get_style");
  ADD_PROPERTY(PropertyInfo(Variant::INT, "seed"), "set_seed", "get_seed");
}

void FacetPlate::_notification(int what)
{
  if (what == NOTIFICATION_RESIZED)
    set_pivot_offset(get_size() * 0.5f);
  else if (what == NOTIFICATION_READY)
    set_texture_repeat(TEXTURE_REPEAT_ENABLED); // The grain tiles across the whole shape.
}

void FacetPlate::set_style(int value)
{
  style = value;
  queue_redraw();
}

void FacetPlate::set_seed(int value)
{
  seed = value;
  queue_redraw();
}

void FacetPlate::add_row(VBoxContainer * list, const String & text, bool is_selected, const String & value)
{
  FacetPlate * row = memnew(FacetPlate);
  row->seed = list->get_child_count() + 1;
  row->set_custom_minimum_size(Vector2(0.f, ROW_HEIGHT));
  row->set_mouse_filter(MOUSE_FILTER_IGNORE);
  list->add_child(row);

  row->candle = memnew(TextureRect);
  row->add_child(row->candle);
  row->candle->set_texture(Facet::texture("candle"));
  row->candle->set_expand_mode(TextureRect::EXPAND_IGNORE_SIZE);
  row->candle->set_texture_filter(TEXTURE_FILTER_LINEAR);
  row->candle->set_position(Vector2(8.f, (ROW_HEIGHT - CANDLE_SIZE) * 0.5f - 3.f));
  row->candle->set_size(Vector2(CANDLE_SIZE, CANDLE_SIZE));
  row->candle->set_mouse_filter(MOUSE_FILTER_IGNORE);
  Facet::flicker(*row->candle);

  row->label = add_label(row, text, HORIZONTAL_ALIGNMENT_LEFT);
  row->value_label = add_label(row, value, HORIZONTAL_ALIGNMENT_RIGHT);
  row->label->set_offset(SIDE_LEFT, CANDLE_INDENT);
  row->value_label->set_offset(SIDE_RIGHT, -ROW_MARGIN);
  // Centered on the yellow of a selected strip, over its blue and red.
  for (Label * side : {row->label, row->value_label})
    side->set_offset(SIDE_BOTTOM, -ROW_HEIGHT * BAND_SHARE);
  row->selected = is_selected;
  row->paint();
  // Arranging its rows sets their scale back to 1, so a selected row waits for that.
  list->connect("sort_children", callable_mp(row, &FacetPlate::settle_scale));
}

void FacetPlate::settle_scale()
{
  if (selected)
    set_scale(Vector2(ROW_SCALE, ROW_SCALE));
}

void FacetPlate::paint()
{
  set_style(selected ? STYLE_SELECTED : STYLE_STRIP);
  candle->set_visible(selected);
  for (Label * side : {label, value_label})
    side->add_theme_color_override("font_color", selected ? UiPalette::INK : UiPalette::ON_PAINT);
}

void FacetPlate::set_selected(bool value)
{
  selected = value;
  paint();
  if (tween.is_valid())
    tween->kill();

  if (selected)
    tween = Facet::pop(*this, ROW_SCALE);
  else
  {
    tween = create_tween();
    tween->tween_property(this, "scale", Vector2(1.f, 1.f), RELEASE_TIME)->set_trans(Tween::TRANS_SINE)->set_ease(Tween::EASE_OUT);
  }
}

void FacetPlate::select_row(VBoxContainer * list, int index, bool value)
{
  if (index >= 0 && index < list->get_child_count())
    Object::cast_to<FacetPlate>(list->get_child(index))->set_selected(value);
}

void FacetPlate::set_row_value(VBoxContainer * list, int index, const String & value)
{
  FacetPlate * row = Object::cast_to<FacetPlate>(list->get_child(index));
  row->value_label->set_text(value);
  row->set_selected(true);
}

void FacetPlate::_draw()
{
  const Rect2 area(Vector2(), get_size());
  switch (style)
  {
    case STYLE_SHEET:
    {
      const PackedVector2Array shape = Facet::outline(area, seed, SHEET_CUT, SHEET_CHIP);
      Facet::panel(*this, shape, UiPalette::PLASTER, SHEET_SHADOW);
      const float foot = area.size.y * (1.f - BASEBOARD_SHARE);
      Facet::panel(*this, clip(shape, Rect2(0.f, foot, area.size.x, area.size.y)), UiPalette::TERRACOTTA, Vector2());
      break;
    }
    case STYLE_STRIP:
      Facet::panel(*this, Facet::outline(area, seed, STRIP_CUT, STRIP_CHIP), UiPalette::WALL, STRIP_SHADOW);
      break;
    case STYLE_SELECTED:
    {
      // The jacket's yellow over its blue and red, as on the back with the 58.
      const PackedVector2Array shape = Facet::outline(area, seed, STRIP_CUT, STRIP_CHIP);
      const float band = area.size.y * BAND_SHARE;
      Facet::panel(*this, shape, UiPalette::JACKET_RED, STRIP_SHADOW);
      Facet::panel(*this, clip(shape, Rect2(0.f, 0.f, area.size.x, area.size.y - band)), UiPalette::JACKET_BLUE, Vector2());
      Facet::panel(*this, clip(shape, Rect2(0.f, 0.f, area.size.x, area.size.y - band * 2.f)), UiPalette::JACKET_YELLOW, Vector2());
      break;
    }
    case STYLE_TAG:
      Facet::panel(*this, Facet::outline(area, seed, STRIP_CUT, STRIP_CHIP), UiPalette::PLASTER, STRIP_SHADOW);
      break;
    case STYLE_HEADER:
    {
      // A street-name sign: the wall's green with a painted border inset.
      Facet::panel(*this, Facet::outline(area, seed, STRIP_CUT, STRIP_CHIP), UiPalette::WALL_DARK, STRIP_SHADOW);
      PackedVector2Array border = Facet::outline(area.grow(-SIGN_BORDER), seed, STRIP_CUT * 0.6f, 0.f);
      border.push_back(border[0]);
      draw_polyline(border, Color(UiPalette::ON_PAINT, 0.75f), 2.f);
      break;
    }
    default:
      break;
  }
}
