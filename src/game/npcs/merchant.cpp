#include "merchant.hpp"
#include <game/player/player_controller.hpp>

#include <godot_cpp/classes/animation.hpp>
#include <godot_cpp/core/class_db.hpp>

using namespace godot;

void Merchant::_bind_methods()
{
  ClassDB::bind_method(D_METHOD("get_zone"), &Merchant::get_zone);
  ClassDB::bind_method(D_METHOD("set_zone", "value"), &Merchant::set_zone);
  // Same order as the Zone enum in inflation.hpp.
  ADD_PROPERTY(PropertyInfo(Variant::INT, "zone", PROPERTY_HINT_ENUM, "Avenue,Jungle,Plain"), "set_zone", "get_zone");
}

void Merchant::_ready()
{
  connect("body_entered", callable_mp(this, &Merchant::on_body_entered));
  connect("body_exited", callable_mp(this, &Merchant::on_body_exited));

  Node * model = get_node_or_null("Model");
  if (model != nullptr)
    animator = Object::cast_to<AnimationPlayer>(model->find_child("AnimationPlayer", true, false));

  if (animator != nullptr)
  {
    for (const char * clip : {"idle", "talk"})
    {
      if (animator->has_animation(clip))
      {
        Ref<Animation> anim = animator->get_animation(clip);
        if (anim.is_valid())
          anim->set_loop_mode(Animation::LOOP_LINEAR);
      }
    }
    if (animator->has_animation("idle"))
      animator->play("idle");
  }
}

void Merchant::set_talking(bool talking)
{
  if (animator == nullptr)
    return;
  const char * clip = talking ? "talk" : "idle";
  if (animator->has_animation(clip) && animator->get_current_animation() != StringName(clip))
    animator->play(clip, 0.22);
}

void Merchant::on_body_entered(Node3D * body)
{
  PlayerController * player = Object::cast_to<PlayerController>(body);
  if (player != nullptr)
    player->set_nearby_merchant(this);
}

void Merchant::on_body_exited(Node3D * body)
{
  PlayerController * player = Object::cast_to<PlayerController>(body);
  if (player != nullptr)
    player->set_nearby_merchant(nullptr);
}
