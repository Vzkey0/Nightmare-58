#include "weapon_trail.hpp"

using namespace godot;

void WeaponTrail::_ready()
{
  ribbon.instantiate();
  set_mesh(ribbon);
}

void WeaponTrail::add_sample(const Vector3 & base, const Vector3 & tip)
{
  newest = (newest + 1) % SAMPLES;
  samples[newest] = Sample{base, tip, 0.f};
}

void WeaponTrail::_process(double delta)
{
  for (Sample & sample : samples)
    sample.age += static_cast<float>(delta);

  ribbon->clear_surfaces();

  int count = 0;
  while (count < SAMPLES)
  {
    const Sample & sample = samples[(newest - count + SAMPLES) % SAMPLES];
    if (sample.age >= LIFETIME)
      break;
    if (count > 0 && sample.age - samples[(newest - count + 1 + SAMPLES) % SAMPLES].age > MAX_GAP)
      break;
    ++count;
  }
  if (count < 2)
    return;

  ribbon->surface_begin(Mesh::PRIMITIVE_TRIANGLE_STRIP);
  for (int i = 0; i < count; ++i)
  {
    const Sample & sample = samples[(newest - i + SAMPLES) % SAMPLES];
    const float life = 1.f - sample.age / LIFETIME;
    ribbon->surface_set_color(Color(1.f, 1.f, 1.f, life * life));
    ribbon->surface_add_vertex(sample.base);
    ribbon->surface_add_vertex(sample.tip);
  }
  ribbon->surface_end();
}
