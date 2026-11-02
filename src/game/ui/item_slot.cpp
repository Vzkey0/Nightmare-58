#include "item_slot.hpp"
#include "metal_plate.hpp"
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
constexpr int GLOW_LAYERS = 3;
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
    set_texture_filter(TEXTURE_FILTER_LINEAR_WITH_MIPMAPS); // Icons are drawn far smaller than rendered.
}

void ItemSlot::show_item(ItemId value, int amount, bool is_selected)
{
  if (is_selected && !selected && framed)
    tween = Metal::pop(*this, 1.f);
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
    Metal::well(*this, area);
    if (selected)
    {
      for (int layer = GLOW_LAYERS; layer > 0; --layer)
        draw_rect(area.grow(layer * 2.f), Color(UiPalette::ICE, 0.14f), false, 2.f);
      draw_rect(area, UiPalette::HIGHLIGHT, false, SELECTED_BORDER);
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
  draw_string_outline(get_theme_default_font(), at, amount, HORIZONTAL_ALIGNMENT_RIGHT, width, font_size, COUNT_OUTLINE, UiPalette::ON_BRIGHT);
  draw_string(get_theme_default_font(), at, amount, HORIZONTAL_ALIGNMENT_RIGHT, width, font_size, UiPalette::HIGHLIGHT);
}
