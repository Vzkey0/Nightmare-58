#pragma once

enum class DistanceRange { Near, Medium, Far };

// First decision of the behavior tree: which range the player is in.
inline DistanceRange classify_distance(float distance, float near_limit, float medium_limit)
{
  if (distance <= near_limit)
    return DistanceRange::Near;
  return distance <= medium_limit ? DistanceRange::Medium : DistanceRange::Far;
}
