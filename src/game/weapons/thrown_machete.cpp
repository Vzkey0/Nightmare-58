#include "thrown_machete.hpp"
#include <game/enemies/combat_target.hpp>
#include <game/player/player_controller.hpp>

#include <godot_cpp/classes/physics_direct_space_state3d.hpp>
#include <godot_cpp/classes/physics_ray_query_parameters3d.hpp>
#include <godot_cpp/classes/world3d.hpp>
#include <godot_cpp/core/math.hpp>

using namespace godot;

namespace
{
const Vector3 UP(0, 1, 0);
constexpr float SPIN_SPEED = 15.f; // Radians per second, around the vertical.
constexpr uint32_t LEVEL_MASK = 1;
}

void ThrownMachete::launch(PlayerController * thrower, const MeshInstance3D * hand_mesh, const Transform3D & mesh_from_bone,
                           const ShapeCast3D * hand_hitbox, const Node3D * hand_bone, const Vector3 & direction)
{
  owner = thrower;
  hand = hand_bone;
  heading = direction.normalized();
  set_global_position(hand->get_global_position());

  // The blade lies flat and spins like a frisbee: the bone's own axis (along the blade) turns
  // to the horizontal, and the spinner turns that around the vertical.
  spinner = memnew(Node3D);
  add_child(spinner);
  Node3D * blade = memnew(Node3D);
  blade->set_basis(Basis(Vector3(1, 0, 0), static_cast<float>(Math::PI) * 0.5f) * Basis().scaled(hand->get_global_basis().get_scale()));
  spinner->add_child(blade);

  MeshInstance3D * mesh = memnew(MeshInstance3D);
  mesh->set_mesh(hand_mesh->get_mesh());
  mesh->set_material_overlay(hand_mesh->get_material_overlay());
  mesh->set_transform(mesh_from_bone);
  blade->add_child(mesh);

  hitbox = Object::cast_to<ShapeCast3D>(hand_hitbox->duplicate());
  hitbox->set_enabled(false);
  blade->add_child(hitbox);

  flight.release();
}

void ThrownMachete::_physics_process(double delta_time)
{
  if (owner == nullptr)
    return;
  const float delta = static_cast<float>(delta_time);
  spin += SPIN_SPEED * delta;
  spinner->set_basis(Basis(UP, spin));

  const Vector3 here = get_global_position();
  const bool going = flight.heading_out(); // Before the step, which may turn it around.
  const float length = flight.step(delta);
  Vector3 next;
  if (going)
  {
    next = here + heading * length;
    if (blocked(here, next))
    {
      // Back from the wall, and the targets it passed may be hit again on the way home.
      flight.turn_back();
      hitbox->clear_exceptions();
      next = here;
    }
    else if (!flight.heading_out())
      hitbox->clear_exceptions(); // It just reached its range.
  }
  else
  {
    const Vector3 home = hand->get_global_position();
    const float distance = here.distance_to(home);
    if (flight.caught(distance, length))
    {
      owner->catch_machete();
      queue_free();
      return;
    }
    next = here + (home - here) / distance * length;
  }

  set_global_position(next);
  hit_targets();
}

void ThrownMachete::hit_targets()
{
  // Asked on each tick, as with the machete in the hand: see PlayerController::hit_targets.
  hitbox->force_shapecast_update();
  for (int i = 0; i < hitbox->get_collision_count(); ++i)
  {
    CombatTarget * target = Object::cast_to<CombatTarget>(hitbox->get_collider(i));
    if (target != nullptr)
      owner->throw_hit(target, hitbox->get_collision_point(i));
    // Once per leg: out and back may each hit the same target.
    hitbox->add_exception_rid(hitbox->get_collider_rid(i));
  }
}

bool ThrownMachete::blocked(const Vector3 & from, const Vector3 & to) const
{
  const Ref<PhysicsRayQueryParameters3D> ray = PhysicsRayQueryParameters3D::create(from, to, LEVEL_MASK);
  return !get_world_3d()->get_direct_space_state()->intersect_ray(ray).is_empty();
}
