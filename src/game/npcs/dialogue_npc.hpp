#pragma once

#include <godot_cpp/classes/animation_player.hpp>
#include <godot_cpp/classes/area3d.hpp>
#include <godot_cpp/classes/node3d.hpp>
#include <godot_cpp/variant/string.hpp>

// An NPC the player can talk to (e.g., El Padre at the first chapel). Plays 'idle' and 'talk'
// clips from its child Model's AnimationPlayer.
class DialogueNpc : public godot::Area3D
{
  GDCLASS(DialogueNpc, godot::Area3D)

protected:
  static void _bind_methods();

public:
  void _ready() override;

  int get_npc_id() const { return npc_id; }
  void set_npc_id(int value) { npc_id = value; }

  godot::String get_prompt_text() const { return prompt_text; }
  void set_prompt_text(const godot::String & value) { prompt_text = value; }

  void set_talking(bool talking);

private:
  void on_body_entered(godot::Node3D * body);
  void on_body_exited(godot::Node3D * body);

  int npc_id = 0;
  godot::String prompt_text = "E  Padre";
  godot::AnimationPlayer * animator = nullptr;
};
