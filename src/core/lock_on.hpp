#pragma once

#include <array.hpp>
#include <sort.hpp>

struct LockCandidate
{
  int id;
  float distance;
  float side; // Radians from the centre of the view; positive is to the left.
};

// Sorted by distance so the caller can test line of sight, which is expensive, nearest first.
class LockOnList
{
public:
  static constexpr int NONE = -1;

  void clear() { candidates.clear(); }
  void add(const LockCandidate & candidate) { candidates.append(candidate); }

  void sort()
  {
    Designar::insertion_sort(candidates, static_cast<Designar::int_t>(candidates.size()),
                             [](const LockCandidate & a, const LockCandidate & b) { return a.distance < b.distance; });
  }

  int size() const { return static_cast<int>(candidates.size()); }
  const LockCandidate & operator[](int index) const { return candidates[index]; }

  // The candidate nearest to `from` towards that side: +1 is left and -1 is right.
  int next_to(float from, int direction) const
  {
    int best = NONE;
    float best_gap = 0.f;
    for (int i = 0; i < size(); ++i)
    {
      const float gap = (candidates[i].side - from) * direction;
      if (gap > 0.f && (best == NONE || gap < best_gap))
      {
        best = candidates[i].id;
        best_gap = gap;
      }
    }
    return best;
  }

private:
  Designar::DynArray<LockCandidate> candidates;
};
