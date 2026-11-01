#pragma once

#include <godot_cpp/classes/immediate_mesh.hpp>
#include <godot_cpp/classes/mesh_instance3d.hpp>

// A ribbon behind the weapon: the controller adds a sample per tick while it swings, and each
// one fades on its own. Coarse on purpose, so the ribbon stays faceted like everything else.
class WeaponTrail : public godot::MeshInstance3D
{
  GDCLASS(WeaponTrail, godot::MeshInstance3D)

protected:
  static void _bind_methods() {}

public:
  void _ready() override;
  void _process(double delta) override;

  void add_sample(const godot::Vector3 & base, const godot::Vector3 & tip);

private:
  static constexpr int SAMPLES = 20;
  static constexpr float LIFETIME = 0.2f;
  static constexpr float MAX_GAP = 0.05f; // Older than this next to a neighbour: another swing.

  struct Sample
  {
    godot::Vector3 base;
    godot::Vector3 tip;
    float age = LIFETIME;
  };

  Sample samples[SAMPLES];
  int newest = 0;
  godot::Ref<godot::ImmediateMesh> ribbon;
};
