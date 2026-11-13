#include <core/progression/inflation.hpp>

#include <array.hpp>
#include <sort.hpp>

namespace
{
struct RateStep
{
  int day;
  int rate;
};

struct ByDay
{
  bool operator()(const RateStep & a, const RateStep & b) const { return a.day < b.day; }
};

// Sorted by day. Gentle on purpose: a rest is also how the player heals and levels, so it must
// sting without making the next purchase unreachable. Tuned by playing.
constexpr RateStep STEPS[] = {
  {0, 100}, {1, 110}, {3, 120}, {5, 135}, {8, 155}, {12, 180}, {17, 220}, {24, 280},
};

Designar::DynArray<RateStep> build_table()
{
  Designar::DynArray<RateStep> table;
  for (const RateStep & step : STEPS)
    table.append(step);
  return table;
}

// The step in force on that day: the last one that starts on it or before.
const RateStep & step_for(int day)
{
  static const Designar::DynArray<RateStep> table = build_table();
  ByDay by_day;
  // J-015: the table grows with each chapter; a binary search keeps the lookup at O(lg n).
  Designar::int_t at = Designar::binary_search(table, RateStep{day, 0}, by_day);
  // On a miss DeSiGNAR returns where the day would go, so the step in force is the one before.
  const Designar::int_t size = static_cast<Designar::int_t>(table.size());
  if (at >= size || table[static_cast<Designar::nat_t>(at)].day != day)
    --at;
  return table[static_cast<Designar::nat_t>(at < 0 ? 0 : at)];
}
}

int exchange_rate(int day)
{
  return step_for(day).rate;
}

int inflate(int base, int day)
{
  return static_cast<int>((static_cast<long long>(base) * exchange_rate(day) + 99) / 100);
}

bool devalues_on(int day)
{
  return day > 0 && step_for(day).day == day;
}
