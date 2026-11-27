#pragma once

enum class DistanceRange { Near, Medium, Far };

// First decision of the behavior tree: which range the player is in.
inline DistanceRange classify_distance(float distance, float near_limit, float medium_limit)
{
  if (distance <= near_limit)
    return DistanceRange::Near;
  return distance <= medium_limit ? DistanceRange::Medium : DistanceRange::Far;
}

// With a margin to leave a range: standing on a limit must not flip the decision on every look.
inline DistanceRange classify_distance(float distance, float near_limit, float medium_limit,
                                       float margin, DistanceRange previous)
{
  return classify_distance(distance,
                           near_limit + (previous == DistanceRange::Near ? margin : 0.f),
                           medium_limit + (previous != DistanceRange::Far ? margin : 0.f));
}
