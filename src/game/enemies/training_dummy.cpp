#include "training_dummy.hpp"
#include <game/player/player_controller.hpp>

#include <godot_cpp/classes/mesh_instance3d.hpp>
#include <godot_cpp/classes/scene_tree.hpp>
#include <godot_cpp/core/math.hpp>

using namespace godot;

namespace
{
const Vector3 UP(0, 1, 0);
const Vector3 ARMS_REST(0, 1.42f, 0);

constexpr float HIT_KICK = 3.2f;
constexpr float TILT_STIFFNESS = 90.f;
constexpr float TILT_DAMPING = 7.f;
constexpr float FALLEN_TILT = 1.45f;
constexpr float DOWN_TIME = 2.5f;
constexpr float SHOVE_PER_HIT = 0.14f;
constexpr float SHOVE_RETURN = 9.f;
constexpr float FLASH_TIME = 0.12f;
constexpr float FLASH_ENERGY = 2.5f;

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
  ready_target();
  model = get_node<Node3D>("Model");
  arms = get_node<Node3D>("Model/Arms");
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

  receive_damage(damage, away, point);
  if (health.dead())
    down_time = DOWN_TIME;
}
