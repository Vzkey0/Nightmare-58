#pragma once

#include <godot_cpp/variant/vector3.hpp>

// Y is ignored so height does not change the range. Squared to skip the root:
// compare it through classify_distance with squared limits.
inline float entity_distance_squared(const godot::Vector3 & a, const godot::Vector3 & b)
{
  const float x = a.x - b.x;
  const float z = a.z - b.z;
  return x * x + z * z;
}
