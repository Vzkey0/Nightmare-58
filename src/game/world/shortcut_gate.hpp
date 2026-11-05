#pragma once

#include <godot_cpp/classes/area3d.hpp>
#include <godot_cpp/classes/collision_shape3d.hpp>
#include <godot_cpp/classes/node3d.hpp>

class PlayerController;

// A gate that only opens from its +X side and then stays open for good. Its state is kept as a
// pickup bit, so the save file needs no new field: gate_id must not collide with a pickup_id.
class ShortcutGate : public godot::Area3D
{
  GDCLASS(ShortcutGate, godot::Area3D)

protected:
  static void _bind_methods();

public:
  void _ready() override;
  void _process(double delta) override;

  int get_gate_id() const { return gate_id; }
  void set_gate_id(int value) { gate_id = value; }

  bool openable_by(const godot::Node3D * body) const;
  void open(PlayerController & player);

private:
  void on_body_entered(godot::Node3D * body);
  void on_body_exited(godot::Node3D * body);

  int gate_id = 200;
  float swing = 0.f; // 0 closed, 1 fully open.
  bool opening = false;
  godot::Node3D * leaf = nullptr;
  godot::CollisionShape3D * blocker = nullptr;
};
