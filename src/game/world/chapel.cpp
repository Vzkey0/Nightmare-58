#include "chapel.hpp"
#include <game/player/player_controller.hpp>

#include <godot_cpp/core/class_db.hpp>

using namespace godot;

namespace
{
constexpr float RESPAWN_GAP = 1.6f; // In front of the altar, not inside it.
}

void Chapel::_bind_methods()
{
  ClassDB::bind_method(D_METHOD("get_chapel_id"), &Chapel::get_chapel_id);
  ClassDB::bind_method(D_METHOD("set_chapel_id", "value"), &Chapel::set_chapel_id);
  ADD_PROPERTY(PropertyInfo(Variant::INT, "chapel_id"), "set_chapel_id", "get_chapel_id");
  ClassDB::bind_method(D_METHOD("get_zone"), &Chapel::get_zone);
  ClassDB::bind_method(D_METHOD("set_zone", "value"), &Chapel::set_zone);
  // Same order as the Zone enum in inflation.hpp.
  ADD_PROPERTY(PropertyInfo(Variant::INT, "zone", PROPERTY_HINT_ENUM, "Avenue,Jungle,Plain"), "set_zone", "get_zone");
}

void Chapel::_enter_tree()
{
  add_to_group("chapels");
}

void Chapel::_ready()
{
  connect("body_entered", callable_mp(this, &Chapel::on_body_entered));
  connect("body_exited", callable_mp(this, &Chapel::on_body_exited));
}

Vector3 Chapel::respawn_point() const
{
  return get_global_position() + get_global_basis().get_column(2).normalized() * RESPAWN_GAP;
}

void Chapel::on_body_entered(Node3D * body)
{
  PlayerController * player = Object::cast_to<PlayerController>(body);
  if (player != nullptr)
    player->set_nearby_chapel(this);
}

void Chapel::on_body_exited(Node3D * body)
{
  PlayerController * player = Object::cast_to<PlayerController>(body);
  if (player != nullptr)
    player->set_nearby_chapel(nullptr);
}
