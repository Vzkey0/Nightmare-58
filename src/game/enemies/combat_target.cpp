#include "combat_target.hpp"
#include <game/ui/stat_bar.hpp>

#include <godot_cpp/classes/camera3d.hpp>
#include <godot_cpp/classes/label3d.hpp>
#include <godot_cpp/classes/method_tweener.hpp>
#include <godot_cpp/classes/property_tweener.hpp>
#include <godot_cpp/classes/tween.hpp>
#include <godot_cpp/classes/viewport.hpp>
#include <godot_cpp/variant/string.hpp>
#include <godot_cpp/variant/utility_functions.hpp>

using namespace godot;

namespace
{
const Vector3 UP(0, 1, 0);
const Vector3 BAR_ANCHOR(0, 2.1f, 0);
const Color NUMBER_COLOR(1.f, 0.85f, 0.25f);

constexpr float BAR_SHAKE_PER_DAMAGE = 0.25f; // Pixels.
constexpr float BAR_SHAKE_FADE = 28.f;
constexpr float NUMBER_RISE = 0.7f;
constexpr float NUMBER_TIME = 0.75f;
constexpr float BAR_TIME = 4.f;
}

void CombatTarget::ready_target()
{
  add_to_group("targets");
  sparks = get_node<CPUParticles3D>("Sparks");
  health_bar = get_node<StatBar>("BarLayer/HealthBar");
}

void CombatTarget::receive_damage(int damage, const Vector3 & away, const Vector3 & point)
{
  bar_shake = damage * BAR_SHAKE_PER_DAMAGE;
  bar_time = BAR_TIME;

  sparks->set_global_position(point);
  sparks->set_direction(away + UP * 0.4f);
  sparks->restart();

  health.damage(damage);
  show_damage(damage);
}

void CombatTarget::update_health_bar(float delta)
{
  const Camera3D * camera = get_viewport()->get_camera_3d();
  const Vector3 anchor = get_global_position() + BAR_ANCHOR;
  bar_time = MAX(bar_time - delta, 0.f);
  health_bar->set_visible((targeted || bar_time > 0.f) && camera != nullptr && !camera->is_position_behind(anchor));
  if (!health_bar->is_visible())
    return;

  const float ratio = health.ratio();
  trail.update(ratio, delta);
  health_bar->set_values(ratio, trail.value());

  bar_shake = MAX(bar_shake - BAR_SHAKE_FADE * delta, 0.f);
  const Vector2 jitter(UtilityFunctions::randf_range(-bar_shake, bar_shake), UtilityFunctions::randf_range(-bar_shake, bar_shake));
  health_bar->set_position(camera->unproject_position(anchor) - health_bar->get_size() * 0.5f + jitter);
}

void CombatTarget::show_damage(int damage)
{
  Label3D * number = memnew(Label3D);
  number->set_text(String::num_int64(damage));
  number->set_billboard_mode(BaseMaterial3D::BILLBOARD_ENABLED);
  number->set_draw_flag(Label3D::FLAG_DISABLE_DEPTH_TEST, true);
  number->set_pixel_size(0.008f);
  number->set_font_size(52);
  number->set_outline_size(14);
  number->set_modulate(NUMBER_COLOR);
  const Vector3 start = BAR_ANCHOR + Vector3(UtilityFunctions::randf_range(-0.3f, 0.3f), -0.35f, 0);
  number->set_position(start);
  number->set_scale(Vector3(1.8f, 1.8f, 1.8f));
  add_child(number);

  // Pops in big, jumps up and then fades, while the health bar settles behind it.
  Ref<Tween> tween = create_tween();
  tween->set_parallel(true);
  tween->tween_property(number, NodePath("scale"), Vector3(1, 1, 1), 0.16);
  tween->tween_property(number, NodePath("position"), start + UP * NUMBER_RISE, NUMBER_TIME)
    ->set_trans(Tween::TRANS_CUBIC)
    ->set_ease(Tween::EASE_OUT);
  tween->tween_property(number, NodePath("modulate:a"), 0.f, NUMBER_TIME * 0.5f)->set_delay(NUMBER_TIME * 0.5f);
  tween->tween_property(number, NodePath("outline_modulate:a"), 0.f, NUMBER_TIME * 0.5f)->set_delay(NUMBER_TIME * 0.5f);
  tween->chain()->tween_callback(Callable(number, "queue_free"));
}
