#include "bronze_plate.hpp"
#include "ui_palette.hpp"

#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/core/math.hpp>
#include <godot_cpp/variant/packed_color_array.hpp>
#include <godot_cpp/variant/packed_vector2_array.hpp>

using namespace godot;

namespace
{
const Color SHEET_DARK(0.1f, 0.08f, 0.06f, 0.98f);
const Color SHEET_LIGHT(0.23f, 0.185f, 0.14f, 0.98f);
const Color PLATE_DARK(0.2f, 0.16f, 0.12f);
const Color PLATE_LIGHT(0.34f, 0.28f, 0.21f);
const Color BRIGHT_DARK(0.5f, 0.41f, 0.31f);
const Color BRIGHT_LIGHT(0.8f, 0.68f, 0.53f);
const Color SHINE(1.f, 0.92f, 0.78f, 0.55f);
const Color CLEAR(0.f, 0.f, 0.f, 0.f);

constexpr float SHEET_BAND = 240.f;
constexpr float PLATE_BAND = 150.f;
constexpr float COLUMN = 12.f;
constexpr float STREAK_GAP = 2.5f;
constexpr float STREAK_ALPHA = 0.1f;
constexpr int SHADOW_LAYERS = 4;
constexpr float SHEET_SHADOW = 90.f;

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
}

void Bronze::gradient(CanvasItem & canvas, const Rect2 & area, const Color & from, const Color & to, bool across)
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

void Bronze::metal(CanvasItem & canvas, const Rect2 & area, const Color & dark, const Color & light, float band)
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
    const Color tint = i % 2 == 0 ? Color(1.f, 0.93f, 0.8f) : Color(0.f, 0.f, 0.f);
    canvas.draw_line(Vector2(x, top), Vector2(x, bottom), Color(tint, STREAK_ALPHA * noise(i + 3000)), 1.f);
  }
}

void Bronze::bevel(CanvasItem & canvas, const Rect2 & area)
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
void Bronze::drop_shadow(CanvasItem & canvas, const Rect2 & area)
{
  for (int layer = SHADOW_LAYERS; layer > 0; --layer)
    canvas.draw_rect(area.grow(layer * 1.5f).grow_side(SIDE_BOTTOM, layer * 1.5f), Color(0.f, 0.f, 0.f, 0.14f));
}

void Bronze::well(CanvasItem & canvas, const Rect2 & area)
{
  gradient(canvas, area, UiPalette::WELL_TOP, UiPalette::WELL_BOTTOM, false);
  gradient(canvas, Rect2(area.position, Vector2(area.size.x, area.size.y * 0.16f)), Color(0.f, 0.f, 0.f, 0.6f), CLEAR, false);
  canvas.draw_rect(area, UiPalette::BORDER, false, 1.f);
  canvas.draw_line(area.position + Vector2(1.f, area.size.y + 1.f), area.position + area.size + Vector2(0.f, 1.f), Color(SHINE, 0.22f), 1.f);
}

void BronzePlate::_bind_methods()
{
  ClassDB::bind_method(D_METHOD("get_style"), &BronzePlate::get_style);
  ClassDB::bind_method(D_METHOD("set_style", "value"), &BronzePlate::set_style);
  ADD_PROPERTY(PropertyInfo(Variant::INT, "style", PROPERTY_HINT_ENUM, "Sheet,Plate,Bright"), "set_style", "get_style");
}

void BronzePlate::set_style(int value)
{
  style = value;
  queue_redraw();
}

void BronzePlate::_draw()
{
  const Rect2 area(Vector2(), get_size());
  if (style == STYLE_SHEET)
  {
    Bronze::gradient(*this, Rect2(-SHEET_SHADOW, 0.f, SHEET_SHADOW, area.size.y), CLEAR, Color(0.f, 0.f, 0.f, 0.65f), true);
    Bronze::metal(*this, area, SHEET_DARK, SHEET_LIGHT, SHEET_BAND);
    Bronze::gradient(*this, area, Color(1.f, 0.9f, 0.75f, 0.05f), Color(0.f, 0.f, 0.f, 0.5f), false);
    Bronze::gradient(*this, Rect2(0.f, 0.f, 3.f, area.size.y), SHINE, Color(SHINE, 0.1f), false);
    return;
  }

  Bronze::drop_shadow(*this, area);
  if (style == STYLE_BRIGHT)
    Bronze::metal(*this, area, BRIGHT_DARK, BRIGHT_LIGHT, PLATE_BAND);
  else
    Bronze::metal(*this, area, PLATE_DARK, PLATE_LIGHT, PLATE_BAND);
  Bronze::gradient(*this, area, Color(1.f, 0.95f, 0.85f, 0.14f), Color(0.f, 0.f, 0.f, 0.3f), false);
  Bronze::bevel(*this, area);
}
