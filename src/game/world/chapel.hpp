#pragma once

#include <godot_cpp/classes/area3d.hpp>
#include <godot_cpp/classes/node3d.hpp>
#include <godot_cpp/variant/vector3.hpp>

// A checkpoint: tells the player when it is close enough to rest. The ids are saved, so they
// must stay the same once a level ships.
class Chapel : public godot::Area3D
{
  GDCLASS(Chapel, godot::Area3D)

protected:
  static void _bind_methods();

public:
  void _enter_tree() override; // Before _ready, so the player can find it whatever the scene order.
  void _ready() override;

  int get_chapel_id() const { return chapel_id; }
  void set_chapel_id(int value) { chapel_id = value; }

  godot::Vector3 respawn_point() const;

private:
  void on_body_entered(godot::Node3D * body);
  void on_body_exited(godot::Node3D * body);

  int chapel_id = 0;
};
