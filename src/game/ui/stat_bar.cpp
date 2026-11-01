#include "stat_bar.hpp"

#include <godot_cpp/classes/geometry2d.hpp>
#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/core/math.hpp>
#include <godot_cpp/variant/typed_array.hpp>

using namespace godot;

namespace
{
const Color FRAME_LIT(0.6f, 0.57f, 0.6f);
const Color FRAME_SHADE(0.34f, 0.32f, 0.36f);
const Color BACK(0.075f, 0.07f, 0.1f, 0.92f);
const Color TRAIL(0.85f, 0.79f, 0.66f);
const Color OUTLINE(0.015f, 0.015f, 0.025f);
const Vector2 SHADOW_OFFSET(4.f, 5.f);

constexpr float BORDER = 3.f;
constexpr float OUTLINE_WIDTH = 2.5f;
// Stacked instead of blurred: stepped like the rest of the art, and it needs no shader.
constexpr int SHADOW_LAYERS = 3;
constexpr float SHADOW_SPREAD[SHADOW_LAYERS] = {8.f, 5.5f, 3.f};
constexpr float SHADOW_ALPHA = 0.24f;
constexpr float EDGE_WIDTH = 2.f;
constexpr float EDGE_LIGHTEN = 0.7f;
constexpr float FACET_WIDTH = 2.6f; // In bar heights.
constexpr float FACET_LIGHTEN = 0.38f;
constexpr float FACET_DARKEN = 0.2f;
constexpr int DEPTHS = 7;
constexpr float DEPTH[DEPTHS] = {0.34f, 0.14f, 0.42f, 0.2f, 0.38f, 0.1f, 0.28f}; // Share of the height.

PackedVector2Array pointed(float left, float apex, float top, float bottom, float tip)
{
  PackedVector2Array shape;
  shape.push_back(Vector2(left, top));
  shape.push_back(Vector2(apex - tip, top));
  shape.push_back(Vector2(apex, (top + bottom) * 0.5f));
  shape.push_back(Vector2(apex - tip, bottom));
  shape.push_back(Vector2(left, bottom));
  return shape;
}

float inset_half(float height, float inset)
{
  return height * 0.5f - inset;
}

float inset_tip(float tip, float height, float inset)
{
  return tip * inset_half(height, inset) / (height * 0.5f);
}

// Moving the slanted edges in by an inset moves the point further than that.
float inset_apex(float width, float height, float tip, float inset)
{
  const float half = height * 0.5f;
  return width - inset * Math::sqrt(half * half + tip * tip) / half;
}
}

void StatBar::_bind_methods()
{
  ClassDB::bind_method(D_METHOD("get_fill_color"), &StatBar::get_fill_color);
  ClassDB::bind_method(D_METHOD("set_fill_color", "value"), &StatBar::set_fill_color);
  ClassDB::bind_method(D_METHOD("get_tip"), &StatBar::get_tip);
  ClassDB::bind_method(D_METHOD("set_tip", "value"), &StatBar::set_tip);
  ClassDB::bind_method(D_METHOD("get_start"), &StatBar::get_start);
  ClassDB::bind_method(D_METHOD("set_start", "value"), &StatBar::set_start);
  ADD_PROPERTY(PropertyInfo(Variant::COLOR, "fill_color"), "set_fill_color", "get_fill_color");
  ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "tip"), "set_tip", "get_tip");
  ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "start"), "set_start", "get_start");
}

void StatBar::set_values(float new_fill, float new_trail)
{
  if (new_fill == fill && new_trail == trail)
    return;
  fill = new_fill;
  trail = new_trail;
  queue_redraw();
}

void StatBar::set_fill_color(const Color & value)
{
  if (value == fill_color)
    return;
  fill_color = value;
  queue_redraw();
}

// The frame's outline moved in by inset, or out with a negative one.
PackedVector2Array StatBar::frame_shape(float inset) const
{
  const Vector2 size = get_size();
  return pointed(inset, inset_apex(size.x, size.y, tip, inset), inset, size.y - inset, inset_tip(tip, size.y, inset));
}

PackedVector2Array StatBar::filled_shape(float ratio) const
{
  const Vector2 size = get_size();
  const float half = inset_half(size.y, BORDER);
  const float point = inset_tip(tip, size.y, BORDER);
  const float reach = start + (inset_apex(size.x, size.y, tip, BORDER) - start) * ratio;
  // From the frame's own end: start only sets where 0 is, or a gap shows behind the hidden end.
  if (reach - point >= BORDER)
    return pointed(BORDER, reach, size.y * 0.5f - half, size.y * 0.5f + half, point);

  // Shorter than the point: only its end fits, with the same slope.
  const float shrink = half * (reach - BORDER) / point;
  PackedVector2Array shape;
  shape.push_back(Vector2(BORDER, size.y * 0.5f - shrink));
  shape.push_back(Vector2(reach, size.y * 0.5f));
  shape.push_back(Vector2(BORDER, size.y * 0.5f + shrink));
  return shape;
}

// An uneven strip along one long edge of the bar, the second tone of its flat shading.
PackedVector2Array StatBar::facets(float edge, float direction) const
{
  const Vector2 size = get_size();
  const float width = size.y * FACET_WIDTH;
  const int teeth = static_cast<int>(Math::ceil(size.x / width));

  PackedVector2Array band;
  band.push_back(Vector2(0.f, edge));
  band.push_back(Vector2(teeth * width, edge));
  for (int tooth = teeth; tooth >= 0; --tooth)
    band.push_back(Vector2(tooth * width, edge + direction * size.y * DEPTH[tooth % DEPTHS]));
  return band;
}

void StatBar::draw_clipped(const PackedVector2Array & shape, const PackedVector2Array & band, const Color & color)
{
  const TypedArray<PackedVector2Array> pieces = Geometry2D::get_singleton()->intersect_polygons(shape, band);
  for (int i = 0; i < pieces.size(); ++i)
    draw_colored_polygon(pieces[i], color);
}

void StatBar::_draw()
{
  const Vector2 size = get_size();
  const float middle = size.y * 0.5f;
  const float half = inset_half(size.y, BORDER);

  draw_set_transform(SHADOW_OFFSET);
  for (int layer = 0; layer < SHADOW_LAYERS; ++layer)
    draw_colored_polygon(frame_shape(-SHADOW_SPREAD[layer]), Color(0.f, 0.f, 0.f, SHADOW_ALPHA));
  draw_set_transform(Vector2());

  draw_colored_polygon(frame_shape(-OUTLINE_WIDTH), OUTLINE);
  draw_colored_polygon(frame_shape(0.f), FRAME_SHADE);
  PackedVector2Array lit;
  lit.push_back(Vector2(0.f, 0.f));
  lit.push_back(Vector2(size.x - tip, 0.f));
  lit.push_back(Vector2(size.x, middle));
  lit.push_back(Vector2(0.f, middle));
  draw_colored_polygon(lit, FRAME_LIT);
  draw_colored_polygon(frame_shape(BORDER), BACK);

  if (trail > fill)
    draw_colored_polygon(filled_shape(trail), TRAIL);
  if (fill <= 0.f)
    return;

  const PackedVector2Array shape = filled_shape(fill);
  draw_colored_polygon(shape, fill_color);
  draw_clipped(shape, facets(middle - half, 1.f), fill_color.lightened(FACET_LIGHTEN));
  draw_clipped(shape, facets(middle + half, -1.f), fill_color.darkened(FACET_DARKEN));

  // A bright edge where the fill ends, on the three points of its tip.
  const int first = shape.size() - 4 > 0 ? 1 : 0;
  draw_polyline(shape.slice(first, first + 3), fill_color.lightened(EDGE_LIGHTEN), EDGE_WIDTH);
}
