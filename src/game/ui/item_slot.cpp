#include "item_slot.hpp"
#include "bronze_plate.hpp"
#include "ui_palette.hpp"

#include <godot_cpp/classes/font.hpp>
#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/core/math.hpp>
#include <godot_cpp/variant/packed_vector2_array.hpp>

using namespace godot;

namespace
{
constexpr float ICON_SHARE = 0.62f;
constexpr float SELECTED_BORDER = 3.f;
constexpr float COUNT_SHARE = 0.22f;
constexpr int GLOW_LAYERS = 3;
}

void ItemSlot::_bind_methods()
{
  ClassDB::bind_method(D_METHOD("get_framed"), &ItemSlot::get_framed);
  ClassDB::bind_method(D_METHOD("set_framed", "value"), &ItemSlot::set_framed);
  ADD_PROPERTY(PropertyInfo(Variant::BOOL, "framed"), "set_framed", "get_framed");
}

void ItemSlot::show_item(ItemId value, int amount, bool is_selected)
{
  item = value;
  count = amount;
  selected = is_selected;
  queue_redraw();
}

void ItemSlot::_draw()
{
  const Vector2 size = get_size();
  const Rect2 area(Vector2(), size);
  if (framed)
  {
    Bronze::well(*this, area);
    if (selected)
    {
      for (int layer = GLOW_LAYERS; layer > 0; --layer)
        draw_rect(area.grow(layer * 2.f), Color(UiPalette::HIGHLIGHT, 0.12f), false, 2.f);
      draw_rect(area, UiPalette::HIGHLIGHT, false, SELECTED_BORDER);
    }
  }
  if (item == NO_ITEM)
    return;

  draw_set_transform(size * 0.5f);
  draw_icon(MIN(size.x, size.y) * ICON_SHARE);
  draw_set_transform(Vector2());

  const int font_size = static_cast<int>(size.y * COUNT_SHARE);
  draw_string(get_theme_default_font(), Vector2(0.f, size.y - font_size * 0.3f), String::num_int64(count),
              HORIZONTAL_ALIGNMENT_RIGHT, size.x - font_size * 0.4f, font_size, UiPalette::HIGHLIGHT);
}

// Each icon lives in a square of side s around the origin.
void ItemSlot::draw_icon(float s)
{
  const Color ink = selected || !framed ? UiPalette::HIGHLIGHT : UiPalette::BRONZE;
  const Color cut = UiPalette::WELL_BOTTOM;
  const float line = s * 0.07f;

  switch (item)
  {
    case ItemCatalog::COFFEE:
      draw_rect(Rect2(-s * 0.32f, -s * 0.3f, s * 0.5f, s * 0.55f), ink);
      draw_arc(Vector2(s * 0.2f, -s * 0.03f), s * 0.15f, -1.6f, 1.6f, 10, ink, line);
      draw_rect(Rect2(-s * 0.42f, s * 0.31f, s * 0.72f, line), ink);
      break;
    case ItemCatalog::CANDLE:
    {
      draw_rect(Rect2(-s * 0.1f, -s * 0.12f, s * 0.2f, s * 0.6f), ink);
      PackedVector2Array flame;
      flame.push_back(Vector2(0.f, -s * 0.5f));
      flame.push_back(Vector2(s * 0.12f, -s * 0.28f));
      flame.push_back(Vector2(0.f, -s * 0.17f));
      flame.push_back(Vector2(-s * 0.12f, -s * 0.28f));
      draw_colored_polygon(flame, ink);
      break;
    }
    case ItemCatalog::VINYL:
      draw_circle(Vector2(), s * 0.46f, ink);
      draw_circle(Vector2(), s * 0.14f, cut);
      draw_circle(Vector2(), s * 0.04f, ink);
      break;
    case ItemCatalog::CARD:
      draw_rect(Rect2(-s * 0.3f, -s * 0.44f, s * 0.6f, s * 0.88f), ink, false, line);
      draw_circle(Vector2(0.f, -s * 0.1f), s * 0.13f, ink);
      draw_rect(Rect2(-s * 0.18f, s * 0.14f, s * 0.36f, s * 0.14f), ink);
      break;
    case ItemCatalog::TILE:
      draw_rect(Rect2(-s * 0.24f, -s * 0.46f, s * 0.48f, s * 0.92f), ink);
      draw_rect(Rect2(-s * 0.2f, -line * 0.5f, s * 0.4f, line), cut);
      for (int y = -1; y <= 1; y += 2)
        for (int x = -1; x <= 1; x += 2)
          draw_circle(Vector2(x * s * 0.1f, y * s * 0.24f), s * 0.05f, cut);
      break;
    default:
      draw_rect(Rect2(-s * 0.44f, -s * 0.34f, s * 0.88f, s * 0.68f), ink, false, line);
      draw_circle(Vector2(-s * 0.13f, -s * 0.06f), s * 0.11f, ink);
      draw_circle(Vector2(s * 0.14f, -s * 0.03f), s * 0.09f, ink);
      draw_rect(Rect2(-s * 0.3f, s * 0.1f, s * 0.6f, s * 0.14f), ink);
      break;
  }
}
