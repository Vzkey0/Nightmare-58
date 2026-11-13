#include "skill_tree_view.hpp"
#include "facet_plate.hpp"
#include "ui_palette.hpp"

#include <godot_cpp/classes/font.hpp>
#include <godot_cpp/classes/method_tweener.hpp>
#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/core/math.hpp>

using namespace godot;

namespace
{
constexpr float CARD_GAP = 26.f;
constexpr float ROOT_SPACE = 150.f; // Above the cards, for the root medal and its lines.
constexpr float ROOT_SCALE = 1.3f;
constexpr float ROOT_JOIN = 26.f; // How far above the cards the root's lines fan out.
constexpr float CARD_TOP = 34.f;
constexpr float CARD_FOOT = 76.f; // The branch name sits at the foot, as the caption of a holy card.
constexpr float FRAME_MARGIN = 22.f; // Of frame.png, drawn as a nine-patch.
const Vector2 CARD_SHADOW(10.f, 12.f);
const Color CARD_PAPER(0.96f, 0.92f, 0.83f);

constexpr float MEDAL = 84.f;
constexpr float MEDAL_SHARE = 0.56f; // Of a row, so deep trees shrink their medals.
constexpr float MAX_ROW = 168.f;
constexpr float LINE_WIDTH = 6.f;
constexpr float LOCKED_LINE_WIDTH = 3.f;
constexpr float NAME_GAP = 12.f;
constexpr int NAME_SIZE = 18;
constexpr int MARK_SIZE = 30;
constexpr int TITLE_SIZE = 32;
constexpr float CURSOR_SCALE = 1.14f;
constexpr float BRACKET = 16.f;
constexpr float BRACKET_GROW = 10.f;

constexpr float UNLOCK_TIME = 0.6f;
constexpr float LINE_SHARE = 0.55f; // Of the unlock: the line fills first, then the medal flashes.
constexpr float PULSE_TIME = 0.7f;
constexpr float FOCUS_TIME = 0.22f;
constexpr float BRACKET_SLIDE = 22.f; // The brackets close in from this far out.
constexpr float HALO_SHARE = 0.78f;
constexpr float CARD_GLOW = 5.f;
const Vector2 MEDAL_SHADOW(3.f, 5.f);
constexpr float PATH_WIDTH = 3.f;

constexpr float TIP_GAP = 16.f;
constexpr float TIP_PAD = 16.f;
constexpr int TIP_NAME_SIZE = 30;
constexpr int TIP_LINE_SIZE = 25;
constexpr float TIP_RISE = 10.f;

const Color LOCKED_MEDAL(0.55f, 0.52f, 0.5f);
const Color LOCKED_LINE(UiPalette::INK_MUTED, 0.45f);

PackedVector2Array ring(const Vector2 & at, float radius, int sides)
{
  PackedVector2Array points;
  for (int i = 0; i <= sides; ++i)
  {
    const float angle = Math::TAU * (i + 0.5f) / sides;
    points.push_back(at + Vector2(Math::cos(angle), Math::sin(angle)) * radius);
  }
  return points;
}

// The first share of a polyline, so a line can fill from its parent down.
PackedVector2Array partial(const PackedVector2Array & points, float share)
{
  float total = 0.f;
  for (int i = 1; i < points.size(); ++i)
    total += points[i - 1].distance_to(points[i]);
  float left = total * share;
  PackedVector2Array part;
  part.push_back(points[0]);
  for (int i = 1; i < points.size() && left > 0.f; ++i)
  {
    const float step = points[i - 1].distance_to(points[i]);
    part.push_back(points[i - 1].move_toward(points[i], MIN(step, left)));
    left -= step;
  }
  return part;
}
}

void SkillTreeView::_ready()
{
  gold = Facet::texture("medal_gold_plain");
  tin = Facet::texture("medal_tin_plain");
  frame = Facet::texture("frame");
  set_texture_repeat(TEXTURE_REPEAT_ENABLED);
  set_texture_filter(TEXTURE_FILTER_LINEAR_WITH_MIPMAPS);
  Ref<Tween> tween = create_tween();
  tween->set_loops();
  tween->tween_method(callable_mp(this, &SkillTreeView::set_pulse), 0.f, 1.f, PULSE_TIME)->set_trans(Tween::TRANS_SINE);
  tween->tween_method(callable_mp(this, &SkillTreeView::set_pulse), 1.f, 0.f, PULSE_TIME)->set_trans(Tween::TRANS_SINE);
}

void SkillTreeView::set_pulse(float value)
{
  pulse = value;
  if (is_visible_in_tree())
    queue_redraw();
}

void SkillTreeView::set_focus(float value)
{
  focus = value;
  queue_redraw();
}

void SkillTreeView::set_unlock(float value)
{
  unlock = value;
  queue_redraw();
}

void SkillTreeView::show_tree(const Entry & top, const Designar::DynArray<Entry> & value, const PackedStringArray & branch_titles, int at)
{
  root = top;
  entries = value;
  titles = branch_titles;
  if (at != cursor && is_visible_in_tree())
  {
    // The new medal swells in while the old one settles back.
    previous = cursor;
    if (focus_tween.is_valid())
      focus_tween->kill();
    focus_tween = create_tween();
    focus_tween->tween_method(callable_mp(this, &SkillTreeView::set_focus), 0.f, 1.f, FOCUS_TIME)->set_trans(Tween::TRANS_BACK)->set_ease(Tween::EASE_OUT);
  }
  cursor = at;
  arrange();
  queue_redraw();
}

void SkillTreeView::celebrate(int index)
{
  celebrated = index;
  if (unlock_tween.is_valid())
    unlock_tween->kill();
  unlock_tween = create_tween();
  unlock_tween->tween_method(callable_mp(this, &SkillTreeView::set_unlock), 0.f, 1.f, UNLOCK_TIME);
}

// Cards share the width evenly and are only as tall as their deepest branch needs.
Rect2 SkillTreeView::card(int branch) const
{
  const int count = MAX(1, static_cast<int>(titles.size()));
  const float width = (get_size().x - CARD_GAP * (count - 1)) / count;
  int deepest = 1;
  for (Designar::nat_t e = 0; e < entries.size(); ++e)
    deepest = MAX(deepest, entries[e].slot.depth);
  const float room = get_size().y - ROOT_SPACE;
  const float row = MIN(MAX_ROW, (room - CARD_TOP - CARD_FOOT) / deepest);
  return Rect2((width + CARD_GAP) * branch, ROOT_SPACE, width, MIN(room, CARD_TOP + row * deepest + CARD_FOOT));
}

void SkillTreeView::arrange()
{
  int deepest = 1;
  for (Designar::nat_t e = 0; e < entries.size(); ++e)
    deepest = MAX(deepest, entries[e].slot.depth);
  const float row = MIN(MAX_ROW, (get_size().y - ROOT_SPACE - CARD_TOP - CARD_FOOT) / deepest);
  medal = MIN(MEDAL, row * MEDAL_SHARE);
  root_center = Vector2(get_size().x * 0.5f, ROOT_SPACE * 0.42f);

  centers = Designar::DynArray<Vector2>();
  for (Designar::nat_t e = 0; e < entries.size(); ++e)
  {
    const SkillSlot & slot = entries[e].slot;
    const Rect2 area = card(slot.branch);
    float leaves = 0.f;
    for (Designar::nat_t o = 0; o < entries.size(); ++o)
      if (entries[o].slot.branch == slot.branch)
        leaves = MAX(leaves, entries[o].slot.column + 1.f);
    centers.append(Vector2(area.position.x + area.size.x * (slot.column + 0.5f) / leaves, ROOT_SPACE + CARD_TOP + row * (slot.depth - 0.5f)));
  }
}

Vector2 SkillTreeView::center(int index) const
{
  return index < 0 ? root_center : centers[index];
}

const SkillTreeView::Entry & SkillTreeView::entry(int index) const
{
  return index < 0 ? root : entries[index];
}

bool SkillTreeView::on_path(int index) const
{
  if (entries.size() == 0)
    return false;
  for (int at = cursor; at >= 0;)
  {
    if (at == index)
      return true;
    int parent = -1;
    for (int i = 0; i < static_cast<int>(entries.size()); ++i)
      if (entries[i].slot.id == entries[at].slot.parent)
        parent = i;
    at = parent;
  }
  return false;
}

int SkillTreeView::toward(const Vector2 & direction) const
{
  if (entries.size() == 0)
    return cursor;
  const Vector2 from = center(cursor);
  int best = cursor;
  float best_score = 1e9f;
  for (int i = 0; i < static_cast<int>(entries.size()); ++i)
  {
    const Vector2 offset = center(i) - from;
    const float along = offset.dot(direction);
    if (i == cursor || along <= 1.f)
      continue;
    // Straight ahead wins over a closer medal off to the side.
    const float score = along + 2.5f * Math::abs(offset.cross(direction));
    if (score < best_score)
    {
      best_score = score;
      best = i;
    }
  }
  return best;
}

int SkillTreeView::entry_at(const Vector2 & global) const
{
  const Vector2 local = get_global_transform().affine_inverse().xform(global);
  for (int i = 0; i < static_cast<int>(entries.size()); ++i)
    if (local.distance_to(center(i)) < medal * 0.55f)
      return i;
  return -1;
}

void SkillTreeView::draw_link(int index)
{
  const Entry & child = entries[index];
  int parent = -1; // The root, unless another entry is the parent.
  for (int i = 0; i < static_cast<int>(entries.size()); ++i)
    if (entries[i].slot.id == child.slot.parent)
      parent = i;

  // Down from the parent, across, and down into the child: the elbow of a family tree.
  // The root's lines fan out above the cards, so they never cross a card's paper.
  const Vector2 from = center(parent) + Vector2(0.f, medal * (parent < 0 ? ROOT_SCALE : 1.f) * 0.5f);
  const Vector2 to = center(index) - Vector2(0.f, medal * 0.5f);
  const float middle = parent < 0 ? ROOT_SPACE - ROOT_JOIN : (from.y + to.y) * 0.5f;
  PackedVector2Array line;
  line.push_back(from);
  line.push_back(Vector2(from.x, middle));
  line.push_back(Vector2(to.x, middle));
  line.push_back(to);

  const bool learned = child.state == LEARNED;
  const bool filling = index == celebrated && unlock < LINE_SHARE;
  const bool path = on_path(index);
  if (!learned || filling)
    draw_polyline(line, path ? Color(UiPalette::INK, 0.75f) : LOCKED_LINE, path ? LINE_WIDTH * 0.7f : LOCKED_LINE_WIDTH);
  if (!learned)
    return;
  const PackedVector2Array lit = filling ? partial(line, unlock / LINE_SHARE) : line;
  if (lit.size() < 2)
    return;
  PackedVector2Array shadow = lit;
  for (int i = 0; i < shadow.size(); ++i)
    shadow[i] += Vector2(3.f, 3.f);
  draw_polyline(shadow, UiPalette::SHADOW, LINE_WIDTH);
  draw_polyline(lit, UiPalette::CANDLE, LINE_WIDTH);
  // The way down to the cursor shines brighter, so the chain it hangs from reads at a glance.
  if (path)
    draw_polyline(lit, Color(UiPalette::JACKET_YELLOW.lightened(0.4f), focus), PATH_WIDTH);
}

void SkillTreeView::draw_medal(int index)
{
  const Entry & entry = this->entry(index);
  const Vector2 at = center(index);
  const bool selected = index == cursor;
  const float grow = selected ? Math::lerp(1.f, CURSOR_SCALE, focus) : (index == previous ? Math::lerp(CURSOR_SCALE, 1.f, focus) : 1.f);
  float size = medal * grow * (index < 0 ? ROOT_SCALE : 1.f);

  const bool flashing = index == celebrated && unlock >= LINE_SHARE && unlock < 1.f;
  const float flash = flashing ? (unlock - LINE_SHARE) / (1.f - LINE_SHARE) : 0.f;
  if (flashing)
  {
    // A burst of candle light, faceted like the rest, that grows and fades.
    size *= 1.f + 0.25f * Math::sin(flash * Math::PI);
    draw_colored_polygon(ring(at, medal * (0.6f + 0.9f * flash), 8), Color(UiPalette::JACKET_YELLOW, 0.55f * (1.f - flash)));
  }

  if (selected)
  {
    // A faceted halo of candle light that breathes with the pulse.
    const float halo = size * (HALO_SHARE + 0.06f * pulse);
    draw_colored_polygon(ring(at, halo, 8), Color(UiPalette::CANDLE, 0.32f * focus));
    draw_colored_polygon(ring(at, halo * 0.86f, 8), Color(UiPalette::JACKET_YELLOW, 0.38f * focus));
  }
  if (entry.state == AVAILABLE)
    draw_polyline(ring(at, medal * 0.62f, 8), Color(UiPalette::JACKET_YELLOW, 0.45f + 0.55f * pulse), 4.f);

  const Rect2 box(at - Vector2(size, size) * 0.5f, Vector2(size, size));
  const Color tint = entry.state == LOCKED ? LOCKED_MEDAL : Color(1.f, 1.f, 1.f);
  const Ref<Texture2D> face = entry.state == LEARNED ? gold : tin;
  // A hard shadow under the medal, its own shape in ink, so it stands off the paper.
  draw_texture_rect(face, Rect2(box.position + MEDAL_SHADOW * grow, box.size), false, Color(UiPalette::SHADOW, 0.45f));
  draw_texture_rect(face, box, false, tint);

  const float faded = entry.state == LOCKED ? 0.75f : 1.f;
  if (entry.icon.is_valid())
  {
    const float side = size * 0.52f;
    draw_texture_rect(entry.icon, Rect2(at - Vector2(side, side) * 0.5f + Vector2(0.f, size * 0.04f), Vector2(side, side)), false, Color(1.f, 1.f, 1.f, faded));
  }
  else
  {
    const Ref<Font> font = get_theme_font("font", "TitleLabel");
    const int mark_size = static_cast<int>(MARK_SIZE * size / MEDAL);
    const Vector2 extent = font->get_string_size(entry.mark, HORIZONTAL_ALIGNMENT_LEFT, -1, mark_size);
    const Vector2 base = at + Vector2(-extent.x * 0.5f, mark_size * 0.42f + size * 0.04f);
    draw_string(font, base + Vector2(2.f, 2.f), entry.mark, HORIZONTAL_ALIGNMENT_LEFT, -1, mark_size, Color(UiPalette::ON_PAINT, 0.6f * faded));
    draw_string(font, base, entry.mark, HORIZONTAL_ALIGNMENT_LEFT, -1, mark_size, Color(UiPalette::INK, faded));
  }

  // Only the root carries a name, beside it; a skill's name is in the detail panel, so lines stay clear.
  if (index < 0)
  {
    const float width = get_size().x * 0.3f;
    const Vector2 name_at = at + Vector2(size * 0.5f + NAME_GAP, NAME_SIZE * 0.4f);
    const Ref<Font> sign = get_theme_font("font", "TitleLabel");
    draw_string(sign, name_at + Vector2(3.f, 3.f), entry.name.to_upper(), HORIZONTAL_ALIGNMENT_LEFT, width, TITLE_SIZE, UiPalette::SHADOW);
    draw_string(sign, name_at, entry.name.to_upper(), HORIZONTAL_ALIGNMENT_LEFT, width, TITLE_SIZE, UiPalette::ON_PAINT);
  }

  if (!selected)
    return;
  // Four corner brackets in the jacket's yellow, inked underneath.
  const float half = size * 0.5f + BRACKET_GROW + BRACKET_SLIDE * (1.f - MIN(focus, 1.f));
  for (int corner = 0; corner < 4; ++corner)
  {
    const Vector2 sign(corner % 2 ? 1.f : -1.f, corner / 2 ? 1.f : -1.f);
    const Vector2 tip = at + sign * half;
    PackedVector2Array bracket;
    bracket.push_back(tip - Vector2(sign.x * BRACKET, 0.f));
    bracket.push_back(tip);
    bracket.push_back(tip - Vector2(0.f, sign.y * BRACKET));
    PackedVector2Array shadow = bracket;
    for (int i = 0; i < shadow.size(); ++i)
      shadow[i] += Vector2(2.f, 2.f);
    draw_polyline(shadow, UiPalette::INK, 5.f);
    draw_polyline(bracket, UiPalette::JACKET_YELLOW, 5.f);
  }
}

void SkillTreeView::_draw()
{
  arrange(); // Cheap, and the size may have changed since the last draw.
  const Ref<Font> title_font = get_theme_font("font", "TitleLabel");
  for (int branch = 0; branch < titles.size(); ++branch)
  {
    const Rect2 area = card(branch);
    // A holy card: paper inside a gilded frame of facets.
    Facet::panel(*this, Facet::outline(area.grow(-6.f), branch + 3, 14.f, 0.f), CARD_PAPER, CARD_SHADOW);
    draw_texture_rect_region(frame, Rect2(area.position, Vector2(FRAME_MARGIN, FRAME_MARGIN)), Rect2(0, 0, FRAME_MARGIN, FRAME_MARGIN));
    const float side = frame->get_width();
    const Rect2 inner = area.grow(-FRAME_MARGIN);
    // Nine-patch by hand: corners as they are, edges stretched.
    const float m = FRAME_MARGIN;
    const float s = side;
    draw_texture_rect_region(frame, Rect2(area.position.x + area.size.x - m, area.position.y, m, m), Rect2(s - m, 0, m, m));
    draw_texture_rect_region(frame, Rect2(area.position.x, area.position.y + area.size.y - m, m, m), Rect2(0, s - m, m, m));
    draw_texture_rect_region(frame, Rect2(area.get_end() - Vector2(m, m), Vector2(m, m)), Rect2(s - m, s - m, m, m));
    draw_texture_rect_region(frame, Rect2(inner.position.x, area.position.y, inner.size.x, m), Rect2(m, 0, s - m * 2, m));
    draw_texture_rect_region(frame, Rect2(inner.position.x, area.get_end().y - m, inner.size.x, m), Rect2(m, s - m, s - m * 2, m));
    draw_texture_rect_region(frame, Rect2(area.position.x, inner.position.y, m, inner.size.y), Rect2(0, m, m, s - m * 2));
    draw_texture_rect_region(frame, Rect2(area.get_end().x - m, inner.position.y, m, inner.size.y), Rect2(s - m, m, m, s - m * 2));

    const Vector2 title_at(area.position.x, area.get_end().y - FRAME_MARGIN - 20.f);
    // A long name shrinks to fit its card rather than running past the frame.
    const String name = titles[branch].to_upper();
    const float room = area.size.x - FRAME_MARGIN * 2.f;
    const float wide = title_font->get_string_size(name, HORIZONTAL_ALIGNMENT_LEFT, -1, TITLE_SIZE).x;
    const int size = wide > room ? static_cast<int>(TITLE_SIZE * room / wide) : TITLE_SIZE;
    draw_string(title_font, title_at, name, HORIZONTAL_ALIGNMENT_CENTER, area.size.x, size, UiPalette::INK);
    const float rule_y = title_at.y - TITLE_SIZE - 8.f;
    draw_line(Vector2(area.position.x + area.size.x * 0.25f, rule_y), Vector2(area.position.x + area.size.x * 0.75f, rule_y), UiPalette::TERRACOTTA, 3.f);
  }
  if (cursor >= 0 && cursor < static_cast<int>(entries.size()))
    draw_card_glow(entries[cursor].slot.branch);
  for (int i = 0; i < static_cast<int>(entries.size()); ++i)
    draw_link(i);
  draw_medal(-1);
  for (int i = 0; i < static_cast<int>(entries.size()); ++i)
    draw_medal(i);
  draw_tip();
}

// The card holding the cursor is outlined in candle gold, so the branch in play stands out.
void SkillTreeView::draw_card_glow(int branch)
{
  const Rect2 area = card(branch);
  draw_rect(area.grow(CARD_GLOW * 2.f), Color(UiPalette::JACKET_YELLOW, 0.18f + 0.12f * pulse), false, CARD_GLOW);
  draw_rect(area.grow(CARD_GLOW * 0.5f), Color(UiPalette::JACKET_YELLOW, 0.6f + 0.3f * pulse), false, CARD_GLOW * 0.8f);
}

// A plaster tag beside the medal under the cursor: what it is and what it takes, without a click.
void SkillTreeView::draw_tip()
{
  if (cursor < 0 || cursor >= static_cast<int>(entries.size()) || entries[cursor].tip.is_empty())
    return;
  const String & tip = entries[cursor].tip;
  const int split = tip.find("\n");
  const String name = split < 0 ? tip : tip.substr(0, split);
  const String line = split < 0 ? String() : tip.substr(split + 1);
  const Ref<Font> sign = get_theme_font("font", "SignLabel");
  const Ref<Font> body = get_theme_font("font", "Label");
  const float width = MAX(sign->get_string_size(name, HORIZONTAL_ALIGNMENT_LEFT, -1, TIP_NAME_SIZE).x, body->get_string_size(line, HORIZONTAL_ALIGNMENT_LEFT, -1, TIP_LINE_SIZE).x) + TIP_PAD * 2.f;
  const float height = TIP_PAD * 2.f + TIP_NAME_SIZE + (line.is_empty() ? 0.f : TIP_LINE_SIZE + 6.f);

  // Right of the medal, or left of it when that would run off the board; it rises in with the focus.
  const Vector2 at = center(cursor);
  const float reach = medal * CURSOR_SCALE * 0.5f + TIP_GAP;
  float x = at.x + reach;
  if (x + width > get_size().x)
    x = at.x - reach - width;
  const Rect2 area(Vector2(x, at.y - height * 0.5f + TIP_RISE * (1.f - focus)), Vector2(width, height));
  const float alpha = CLAMP(focus, 0.f, 1.f);
  Facet::panel(*this, Facet::outline(area, cursor + 11, 7.f, 0.f), Color(UiPalette::PLASTER, alpha), Vector2(5.f, 6.f) * alpha);
  draw_rect(Rect2(area.position, Vector2(4.f, area.size.y)).grow_individual(0.f, -6.f, 0.f, -6.f), Color(UiPalette::TERRACOTTA, alpha));
  const float top = area.position.y + TIP_PAD + sign->get_ascent(TIP_NAME_SIZE);
  draw_string(sign, Vector2(area.position.x + TIP_PAD, top), name, HORIZONTAL_ALIGNMENT_LEFT, -1, TIP_NAME_SIZE, Color(UiPalette::INK, alpha));
  if (!line.is_empty())
    draw_string(body, Vector2(area.position.x + TIP_PAD, top + 6.f + body->get_ascent(TIP_LINE_SIZE) + 2.f), line, HORIZONTAL_ALIGNMENT_LEFT, -1, TIP_LINE_SIZE, Color(UiPalette::TERRACOTTA.darkened(0.25f), alpha));
}
