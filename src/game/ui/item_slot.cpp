#include "item_slot.hpp"
#include "facet_plate.hpp"
#include "ui_palette.hpp"

#include <godot_cpp/classes/font.hpp>
#include <godot_cpp/classes/resource_loader.hpp>
#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/core/math.hpp>

using namespace godot;

namespace
{
constexpr float ICON_SHARE = 0.86f;
constexpr float SELECTED_BORDER = 3.f;
constexpr float COUNT_SHARE = 0.22f;
constexpr float COUNT_OUTLINE = 6.f;
constexpr float SLOT_CUT = 10.f;
constexpr float SLOT_CHIP = 3.f;
const Vector2 SLOT_SHADOW(3.f, 4.f);
}

void ItemSlot::_bind_methods()
{
  ClassDB::bind_method(D_METHOD("get_framed"), &ItemSlot::get_framed);
  ClassDB::bind_method(D_METHOD("set_framed", "value"), &ItemSlot::set_framed);
  ADD_PROPERTY(PropertyInfo(Variant::BOOL, "framed"), "set_framed", "get_framed");
}

void ItemSlot::_notification(int what)
{
  if (what == NOTIFICATION_RESIZED)
    set_pivot_offset(get_size() * 0.5f);
  else if (what == NOTIFICATION_READY)
    {
    set_texture_filter(TEXTURE_FILTER_LINEAR_WITH_MIPMAPS); // Icons are drawn far smaller than rendered.
    set_texture_repeat(TEXTURE_REPEAT_ENABLED); // For the plaster grain.
  }
}

void ItemSlot::show_item(ItemId value, int amount, bool is_selected)
{
  if (is_selected && !selected && framed)
    tween = Facet::pop(*this, 1.f);
  if (value != item && value != NO_ITEM)
    icon = ResourceLoader::get_singleton()->load(vformat("res://ui/icons/%s.png", ItemCatalog::instance()[value].key));
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
    const PackedVector2Array shape = Facet::outline(area, get_index() + 1, SLOT_CUT, SLOT_CHIP);
    Facet::panel(*this, shape, selected ? UiPalette::JACKET_YELLOW : UiPalette::PLASTER_SHADE, SLOT_SHADOW);
    if (selected)
    {
      PackedVector2Array edge = shape;
      edge.push_back(shape[0]);
      draw_polyline(edge, UiPalette::JACKET_RED, SELECTED_BORDER);
    }
  }
  if (item == NO_ITEM)
    return;

  const float side = MIN(size.x, size.y) * ICON_SHARE;
  draw_texture_rect(icon, Rect2((size - Vector2(side, side)) * 0.5f, Vector2(side, side)), false);

  const int font_size = static_cast<int>(size.y * COUNT_SHARE);
  const Vector2 at(0.f, size.y - font_size * 0.3f);
  const float width = size.x - font_size * 0.4f;
  const String amount = String::num_int64(count);
  // Icons are bright, so the number needs its own edge to read on top of one.
  draw_string_outline(get_theme_default_font(), at, amount, HORIZONTAL_ALIGNMENT_RIGHT, width, font_size, COUNT_OUTLINE, UiPalette::INK);
  draw_string(get_theme_default_font(), at, amount, HORIZONTAL_ALIGNMENT_RIGHT, width, font_size, UiPalette::ON_PAINT);
}
