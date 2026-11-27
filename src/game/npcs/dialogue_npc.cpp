#include "dialogue_npc.hpp"
#include <game/player/player_controller.hpp>

#include <godot_cpp/classes/animation.hpp>
#include <godot_cpp/core/class_db.hpp>

using namespace godot;

void DialogueNpc::_bind_methods()
{
  ClassDB::bind_method(D_METHOD("get_npc_id"), &DialogueNpc::get_npc_id);
  ClassDB::bind_method(D_METHOD("set_npc_id", "value"), &DialogueNpc::set_npc_id);
  ADD_PROPERTY(PropertyInfo(Variant::INT, "npc_id"), "set_npc_id", "get_npc_id");

  ClassDB::bind_method(D_METHOD("get_prompt_text"), &DialogueNpc::get_prompt_text);
  ClassDB::bind_method(D_METHOD("set_prompt_text", "value"), &DialogueNpc::set_prompt_text);
  ADD_PROPERTY(PropertyInfo(Variant::STRING, "prompt_text"), "set_prompt_text", "get_prompt_text");
}

void DialogueNpc::_ready()
{
  connect("body_entered", callable_mp(this, &DialogueNpc::on_body_entered));
  connect("body_exited", callable_mp(this, &DialogueNpc::on_body_exited));

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

void DialogueNpc::set_talking(bool talking)
{
  if (animator == nullptr)
    return;
  const char * clip = talking ? "talk" : "idle";
  if (animator->has_animation(clip) && animator->get_current_animation() != StringName(clip))
    animator->play(clip, 0.22);
}

void DialogueNpc::on_body_entered(Node3D * body)
{
  PlayerController * player = Object::cast_to<PlayerController>(body);
  if (player != nullptr)
    player->set_nearby_npc(this);
}

void DialogueNpc::on_body_exited(Node3D * body)
{
  PlayerController * player = Object::cast_to<PlayerController>(body);
  if (player != nullptr)
    player->set_nearby_npc(nullptr);
}
