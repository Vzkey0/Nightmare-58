#include "loot_pickup.hpp"
#include <game/player/player_controller.hpp>

#include <godot_cpp/classes/mesh_instance3d.hpp>
#include <godot_cpp/classes/packed_scene.hpp>
#include <godot_cpp/classes/resource_loader.hpp>
#include <godot_cpp/classes/scene_tree.hpp>
#include <godot_cpp/core/class_db.hpp>

using namespace godot;

namespace
{
constexpr float SPIN_SPEED = 1.2f;
constexpr float SHOWN_SIZE = 0.42f; // Longest side on the ground: a domino at its real size is a speck.
}

void LootPickup::_bind_methods()
{
  ClassDB::bind_method(D_METHOD("get_item_key"), &LootPickup::get_item_key);
  ClassDB::bind_method(D_METHOD("set_item_key", "value"), &LootPickup::set_item_key);
  ClassDB::bind_method(D_METHOD("get_amount"), &LootPickup::get_amount);
  ClassDB::bind_method(D_METHOD("set_amount", "value"), &LootPickup::set_amount);
  ClassDB::bind_method(D_METHOD("get_pickup_id"), &LootPickup::get_pickup_id);
  ClassDB::bind_method(D_METHOD("set_pickup_id", "value"), &LootPickup::set_pickup_id);
  ADD_PROPERTY(PropertyInfo(Variant::STRING, "item_key"), "set_item_key", "get_item_key");
  ADD_PROPERTY(PropertyInfo(Variant::INT, "amount"), "set_amount", "get_amount");
  ADD_PROPERTY(PropertyInfo(Variant::INT, "pickup_id"), "set_pickup_id", "get_pickup_id");
}

void LootPickup::_ready()
{
  const PlayerController * player = Object::cast_to<PlayerController>(get_tree()->get_first_node_in_group("player"));
  if (player != nullptr && pickup_id != NO_ID && player->progress().pickup_taken(pickup_id))
  {
    queue_free();
    return;
  }
  connect("body_entered", callable_mp(this, &LootPickup::on_body_entered));
  show_model();
}

void LootPickup::_process(double delta)
{
  if (spinner != nullptr)
    spinner->rotate_y(static_cast<float>(delta) * SPIN_SPEED);
}

// Props share their icon's key, so a new item needs no change here.
void LootPickup::show_model()
{
  const Ref<PackedScene> scene = ResourceLoader::get_singleton()->load("res://models/props/" + item_key + ".glb");
  Node3D * model = Object::cast_to<Node3D>(scene->instantiate());
  spinner = get_node<Node3D>("Spinner");
  spinner->add_child(model);

  const MeshInstance3D * mesh = Object::cast_to<MeshInstance3D>(model->find_children("*", "MeshInstance3D", true, false)[0]);
  const AABB bounds = mesh->get_aabb();
  const float scale = MAX(1.f, SHOWN_SIZE / bounds.get_longest_axis_size());
  model->set_scale(Vector3(scale, scale, scale));
  model->set_position(-bounds.get_center() * scale);
}

void LootPickup::on_body_entered(Node3D * body)
{
  PlayerController * player = Object::cast_to<PlayerController>(body);
  if (player == nullptr || player->is_dead())
    return;
  player->pick_up(item_key, amount, pickup_id);
  queue_free();
}
