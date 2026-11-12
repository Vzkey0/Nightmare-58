#include "key_button.hpp"
#include "facet_plate.hpp"
#include "ui_palette.hpp"

#include <godot_cpp/classes/font.hpp>
#include <godot_cpp/classes/method_tweener.hpp>
#include <godot_cpp/classes/property_tweener.hpp>
#include <godot_cpp/core/class_db.hpp>

using namespace godot;

namespace
{
constexpr float PAD = 10.f;
constexpr float GAP = 10.f;
constexpr float CAP_INSET = 6.f;  // Room between the plaque's edge and the key box.
constexpr float CAP_PAD = 8.f;
constexpr float CAP_DEPTH = 4.f;  // The darker lip under the key, as on a real keycap.
constexpr int KEY_SIZE = 20;
constexpr int ACTION_SIZE = 22;
const Vector2 SHADOW(4.f, 5.f);

constexpr float HOVER_SCALE = 1.07f;
constexpr float HOVER_TIME = 0.14f;
constexpr float PRESS_SCALE = 0.88f;
constexpr float PRESS_TIME = 0.06f;
constexpr float RELEASE_TIME = 0.28f;
constexpr float POP_FROM = 0.6f;
constexpr float POP_TIME = 0.26f;
constexpr float FLASH_TIME = 0.35f;
constexpr float DISABLED_ALPHA = 0.45f;

Ref<Font> font_of(const Control & control, const char * type)
{
  return control.get_theme_font("font", type);
}
}

void KeyButton::_bind_methods()
{
  ClassDB::bind_method(D_METHOD("set_text", "text"), &KeyButton::set_text);
  ClassDB::bind_method(D_METHOD("get_text"), &KeyButton::get_text);
  ClassDB::bind_method(D_METHOD("set_align", "value"), &KeyButton::set_align);
  ClassDB::bind_method(D_METHOD("get_align"), &KeyButton::get_align);
  ADD_PROPERTY(PropertyInfo(Variant::STRING, "text"), "set_text", "get_text");
  ADD_PROPERTY(PropertyInfo(Variant::INT, "align", PROPERTY_HINT_ENUM, "Left,Center,Right"), "set_align", "get_align");
}

void KeyButton::_notification(int what)
{
  switch (what)
  {
    case NOTIFICATION_READY:
      set_mouse_filter(MOUSE_FILTER_PASS);
      set_texture_repeat(TEXTURE_REPEAT_ENABLED);
      [[fallthrough]];
    case NOTIFICATION_RESIZED:
      set_pivot_offset(plate_rect().get_center());
      break;
    case NOTIFICATION_MOUSE_ENTER:
      hover(true);
      break;
    case NOTIFICATION_MOUSE_EXIT:
      hover(false);
      break;
    default:
      break;
  }
}

void KeyButton::set_align(int value)
{
  align = value;
  queue_redraw();
}

void KeyButton::set_text(const String & value)
{
  if (value == text)
    return;
  const bool was_empty = text.is_empty();
  text = value;
  const int split = text.find("  ");
  key = split < 0 ? String() : text.substr(0, split).strip_edges();
  action = split < 0 ? text : text.substr(split).strip_edges();
  if (!is_inside_tree())
    return;
  set_pivot_offset(plate_rect().get_center());
  queue_redraw();
  if (text.is_empty())
    return;

  // A new prompt fades in from small; a changed one just pops.
  if (tween.is_valid())
    tween->kill();
  set_scale(Vector2(POP_FROM, POP_FROM));
  if (was_empty)
    set_modulate(Color(1, 1, 1, 0));
  tween = create_tween()->set_parallel();
  const float rest = hovered ? HOVER_SCALE : 1.f;
  tween->tween_property(this, "scale", Vector2(rest, rest), POP_TIME)->set_trans(Tween::TRANS_BACK)->set_ease(Tween::EASE_OUT);
  tween->tween_property(this, "modulate:a", 1.f, POP_TIME * 0.6f);
}

void KeyButton::hover(bool on)
{
  hovered = on;
  scale_to(on ? HOVER_SCALE : 1.f, HOVER_TIME);
}

void KeyButton::scale_to(float value, float time)
{
  if (tween.is_valid())
    tween->kill();
  tween = create_tween();
  tween->tween_property(this, "scale", Vector2(value, value), time)->set_trans(Tween::TRANS_BACK)->set_ease(Tween::EASE_OUT);
}

void KeyButton::press()
{
  if (tween.is_valid())
    tween->kill();
  if (disabled)
  {
    // A refused key shakes its head instead of going down.
    tween = create_tween();
    for (float turn : {0.07f, -0.06f, 0.03f, 0.f})
      tween->tween_property(this, "rotation", turn, 0.045f);
    return;
  }
  const float rest = hovered ? HOVER_SCALE : 1.f;
  tween = create_tween();
  tween->tween_property(this, "scale", Vector2(PRESS_SCALE, PRESS_SCALE), PRESS_TIME)->set_ease(Tween::EASE_OUT);
  tween->tween_property(this, "scale", Vector2(rest, rest), RELEASE_TIME)->set_trans(Tween::TRANS_BACK)->set_ease(Tween::EASE_OUT);
  // The key lights candle gold and cools back to ink.
  Ref<Tween> glow = create_tween();
  glow->tween_method(callable_mp(this, &KeyButton::set_flash), 1.f, 0.f, FLASH_TIME);
}

void KeyButton::set_disabled(bool value)
{
  disabled = value;
  set_self_modulate(Color(1, 1, 1, disabled ? DISABLED_ALPHA : 1.f));
}

void KeyButton::set_flash(float value)
{
  flash = value;
  queue_redraw();
}

Rect2 KeyButton::plate_rect() const
{
  const Vector2 size = get_size();
  float width = PAD * 2.f;
  if (!action.is_empty())
    width += font_of(*this, "Label")->get_string_size(action, HORIZONTAL_ALIGNMENT_LEFT, -1, ACTION_SIZE).x;
  if (!key.is_empty())
  {
    const float side = size.y - CAP_INSET * 2.f;
    width += MAX(side, font_of(*this, "SignLabel")->get_string_size(key, HORIZONTAL_ALIGNMENT_LEFT, -1, KEY_SIZE).x + CAP_PAD * 2.f);
    if (!action.is_empty())
      width += GAP;
    else
      width -= PAD * 2.f - CAP_INSET * 2.f; // A lone key sits in a thin frame.
  }
  const float x = align == 0 ? 0.f : (align == 1 ? (size.x - width) * 0.5f : size.x - width);
  return Rect2(x, 0.f, width, size.y);
}

void KeyButton::_draw()
{
  if (text.is_empty())
    return;
  const Rect2 plate = plate_rect();
  Facet::panel(*this, Facet::outline(plate, text.length(), 7.f, 0.f), hovered && !disabled ? UiPalette::JACKET_YELLOW : UiPalette::PLASTER, SHADOW);

  float x = plate.position.x + (action.is_empty() ? CAP_INSET : PAD);
  const float middle = plate.size.y * 0.5f;
  if (!key.is_empty())
  {
    const Ref<Font> sign = font_of(*this, "SignLabel");
    const Vector2 label = sign->get_string_size(key, HORIZONTAL_ALIGNMENT_LEFT, -1, KEY_SIZE);
    const float side = plate.size.y - CAP_INSET * 2.f;
    const Rect2 cap(x, CAP_INSET - CAP_DEPTH * 0.5f, MAX(side, label.x + CAP_PAD * 2.f), side);
    const Color ink = UiPalette::INK.lerp(UiPalette::CANDLE, flash);
    Facet::panel(*this, Facet::outline(Rect2(cap.position + Vector2(0.f, CAP_DEPTH), cap.size), 3, 4.f, 0.f), ink.darkened(0.4f), Vector2());
    Facet::panel(*this, Facet::outline(cap, 3, 4.f, 0.f), ink, Vector2());
    const Vector2 at(cap.position.x + (cap.size.x - label.x) * 0.5f, cap.get_center().y + sign->get_ascent(KEY_SIZE) * 0.5f - sign->get_descent(KEY_SIZE) * 0.5f);
    draw_string(sign, at, key, HORIZONTAL_ALIGNMENT_LEFT, -1, KEY_SIZE, UiPalette::PLASTER.lerp(UiPalette::INK, flash));
    x += cap.size.x + GAP;
  }
  const Ref<Font> body = font_of(*this, "Label");
  draw_string(body, Vector2(x, middle + body->get_ascent(ACTION_SIZE) * 0.5f - body->get_descent(ACTION_SIZE) * 0.5f), action, HORIZONTAL_ALIGNMENT_LEFT, -1, ACTION_SIZE, UiPalette::INK);
}
