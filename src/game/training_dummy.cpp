#include "training_dummy.hpp"
#include "player_controller.hpp"
#include "stat_bar.hpp"

#include <godot_cpp/classes/camera3d.hpp>
#include <godot_cpp/classes/label3d.hpp>
#include <godot_cpp/classes/mesh_instance3d.hpp>
#include <godot_cpp/classes/method_tweener.hpp>
#include <godot_cpp/classes/property_tweener.hpp>
#include <godot_cpp/classes/scene_tree.hpp>
#include <godot_cpp/classes/tween.hpp>
#include <godot_cpp/classes/viewport.hpp>
#include <godot_cpp/core/math.hpp>
#include <godot_cpp/variant/string.hpp>
#include <godot_cpp/variant/utility_functions.hpp>

using namespace godot;

namespace
{
const Vector3 UP(0, 1, 0);
const Vector3 BAR_ANCHOR(0, 2.1f, 0);
const Vector3 ARMS_REST(0, 1.42f, 0);
const Color NUMBER_COLOR(1.f, 0.85f, 0.25f);

constexpr float HIT_KICK = 3.2f;
constexpr float TILT_STIFFNESS = 90.f;
constexpr float TILT_DAMPING = 7.f;
constexpr float FALLEN_TILT = 1.45f;
constexpr float DOWN_TIME = 2.5f;
constexpr float SHOVE_PER_HIT = 0.14f;
constexpr float SHOVE_RETURN = 9.f;
constexpr float FLASH_TIME = 0.12f;
constexpr float FLASH_ENERGY = 2.5f;
constexpr float BAR_SHAKE_PER_DAMAGE = 0.25f; // Pixels.
constexpr float BAR_SHAKE_FADE = 28.f;
constexpr float NUMBER_RISE = 0.7f;
constexpr float NUMBER_TIME = 0.75f;
constexpr float BAR_TIME = 4.f;

// The reach must match what the player sees: the arms at their widest, plus the player's width.
constexpr float ATTACK_RANGE = 2.4f;
constexpr float SWING_REACH = 1.95f;
constexpr int SWING_DAMAGE = 18;
constexpr float WINDUP_TIME = 0.9f; // Long and glowing: it is here to practise reading attacks.
constexpr float SWING_TIME = 0.3f;
constexpr float ATTACK_WAIT = 2.5f;
constexpr float ARMS_RAISE = 0.14f;
constexpr float ARMS_STRETCH = 2.f; // Grows the arms to a half width of 1.65 m.
constexpr float GLOW_ENERGY = 1.6f;
}

void TrainingDummy::_ready()
{
  add_to_group("targets");
  model = get_node<Node3D>("Model");
  arms = get_node<Node3D>("Model/Arms");
  sparks = get_node<CPUParticles3D>("Sparks");
  health_bar = get_node<StatBar>("BarLayer/HealthBar");
  player = Object::cast_to<PlayerController>(get_tree()->get_first_node_in_group("player"));
  // The scene marks the material local, so each dummy flashes on its own.
  material = get_node<MeshInstance3D>("Model/Torso")->get_mesh()->get("material");
}

void TrainingDummy::_process(double delta_time)
{
  const float delta = static_cast<float>(delta_time);

  if (health.dead())
  {
    down_time -= delta;
    if (down_time <= 0.f)
      health.restore();
  }

  const float rest = health.dead() ? FALLEN_TILT : 0.f;
  tilt_speed += (TILT_STIFFNESS * (rest - tilt) - TILT_DAMPING * tilt_speed) * delta;
  tilt += tilt_speed * delta;
  shove = Math::lerp(shove, 0.f, 1.f - Math::exp(-SHOVE_RETURN * delta));
  model->set_basis(Basis(tilt_axis, tilt));
  model->set_position(tilt_axis.cross(UP) * shove);

  update_attack(delta);

  flash = MAX(flash - delta / FLASH_TIME, 0.f);
  material->set_emission_energy_multiplier(MAX(flash * FLASH_ENERGY, windup * GLOW_ENERGY));

  update_health_bar(delta);
}

void TrainingDummy::update_attack(float delta)
{
  const bool close = player != nullptr && player->get_global_position().distance_to(get_global_position()) < ATTACK_RANGE;
  attack_wait = MAX(attack_wait - delta, 0.f);
  const bool attacking = attack_time > 0.f || (close && attack_wait == 0.f);
  if (attacking && !health.dead())
  {
    const float previous = attack_time;
    attack_time += delta;
    const bool struck = previous < WINDUP_TIME && attack_time >= WINDUP_TIME;
    if (struck && player->get_global_position().distance_to(get_global_position()) < SWING_REACH)
      player->take_hit(SWING_DAMAGE, get_global_position());
  }
  else
    attack_time = 0.f;

  if (attack_time >= WINDUP_TIME + SWING_TIME)
  {
    attack_time = 0.f;
    attack_wait = ATTACK_WAIT;
  }

  windup = MIN(attack_time / WINDUP_TIME, 1.f);
  const float spin = MAX(attack_time - WINDUP_TIME, 0.f) / SWING_TIME;
  arms->set_position(ARMS_REST + UP * windup * ARMS_RAISE);
  arms->set_basis(Basis(UP, spin * Math::TAU).scaled_local(Vector3(1.f + windup * ARMS_STRETCH, 1.f, 1.f)));
}

void TrainingDummy::take_hit(int damage, const Vector3 & attacker, const Vector3 & point)
{
  if (health.dead())
    return;

  const Vector3 away = (get_global_position() - attacker).slide(UP).normalized();
  // Only a dummy at rest changes direction, or the swing would snap to the new axis.
  if (Math::abs(tilt) < 0.02f)
    tilt_axis = UP.cross(away);
  tilt_speed += HIT_KICK;
  shove = SHOVE_PER_HIT;
  flash = 1.f;
  bar_shake = damage * BAR_SHAKE_PER_DAMAGE;
  bar_time = BAR_TIME;

  sparks->set_global_position(point);
  sparks->set_direction(away + UP * 0.4f);
  sparks->restart();

  health.damage(damage);
  if (health.dead())
    down_time = DOWN_TIME;
  show_damage(damage);
}

void TrainingDummy::update_health_bar(float delta)
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

void TrainingDummy::show_damage(int damage)
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
