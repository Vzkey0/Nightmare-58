#include "shortcut_gate.hpp"
#include <game/player/player_controller.hpp>

#include <godot_cpp/classes/scene_tree.hpp>
#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/core/math.hpp>

using namespace godot;

namespace
{
constexpr float OPEN_ANGLE = -static_cast<float>(Math::PI) * 0.5f; // The leaf swings towards +X, away from whoever opens it.
constexpr float SWING_TIME = 1.4f;
}

void ShortcutGate::_bind_methods()
{
  ClassDB::bind_method(D_METHOD("get_gate_id"), &ShortcutGate::get_gate_id);
  ClassDB::bind_method(D_METHOD("set_gate_id", "value"), &ShortcutGate::set_gate_id);
  ADD_PROPERTY(PropertyInfo(Variant::INT, "gate_id"), "set_gate_id", "get_gate_id");
}

void ShortcutGate::_ready()
{
  leaf = get_node<Node3D>("Leaf");
  blocker = get_node<CollisionShape3D>("Leaf/Body/Shape");
  const PlayerController * player = Object::cast_to<PlayerController>(get_tree()->get_first_node_in_group("player"));
  if (player != nullptr && player->progress().pickup_taken(gate_id))
  {
    swing = 1.f;
    leaf->set_rotation(Vector3(0.f, OPEN_ANGLE, 0.f));
    blocker->set_disabled(true);
    return;
  }
  connect("body_entered", callable_mp(this, &ShortcutGate::on_body_entered));
  connect("body_exited", callable_mp(this, &ShortcutGate::on_body_exited));
}

void ShortcutGate::_process(double delta)
{
  if (!opening)
    return;
  swing = MIN(swing + static_cast<float>(delta) / SWING_TIME, 1.f);
  // Heavy start, then the rusty hinge lets go.
  leaf->set_rotation(Vector3(0.f, OPEN_ANGLE * swing * swing, 0.f));
  if (swing >= 1.f)
    opening = false;
}

bool ShortcutGate::openable_by(const Node3D * body) const
{
  return (body->get_global_position() - get_global_position()).dot(get_global_basis().get_column(0)) > 0.f;
}

void ShortcutGate::open(PlayerController & player)
{
  if (opening || swing > 0.f || !openable_by(&player))
    return;
  opening = true;
  blocker->set_disabled(true);
  player.remember(gate_id);
  player.set_nearby_gate(nullptr);
}

void ShortcutGate::on_body_entered(Node3D * body)
{
  PlayerController * player = Object::cast_to<PlayerController>(body);
  if (player != nullptr && swing == 0.f)
    player->set_nearby_gate(this);
}

void ShortcutGate::on_body_exited(Node3D * body)
{
  PlayerController * player = Object::cast_to<PlayerController>(body);
  if (player != nullptr)
    player->set_nearby_gate(nullptr);
}
