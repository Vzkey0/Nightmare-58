#pragma once

enum class Stat { Health, Stamina, Regeneration, Speed, AttackRate, Power };

constexpr int STAT_COUNT = 6;

// The values come from the PDD and get tuned by playing.
class PlayerStats
{
public:
  static constexpr int MAX_LEVEL = 5;
  static constexpr int BASE_HEALTH = 100;

  int level(Stat stat) const { return levels[static_cast<int>(stat)]; }
  bool can_raise(Stat stat) const { return level(stat) < MAX_LEVEL; }
  void raise(Stat stat) { ++levels[static_cast<int>(stat)]; }
  void restore(int stat, int level) { levels[stat] = level; } // For a loaded game.

  int total_levels() const
  {
    int total = 0;
    for (int level : levels)
      total += level;
    return total;
  }

  // Each level costs more than the last, whichever stat it goes to.
  int next_cost() const { return 80 + 40 * total_levels(); }

  int max_health() const { return BASE_HEALTH + BASE_HEALTH * level(Stat::Health) / 10; }
  float stamina_regen_scale() const { return 1.f + 0.1f * level(Stat::Stamina); }
  float regen_per_second() const { return 0.5f * level(Stat::Regeneration); }
  float speed_scale() const { return 1.f + 0.04f * level(Stat::Speed); }
  float attack_rate() const { return 1.f + 0.05f * level(Stat::AttackRate); }
  float damage_scale() const { return 1.f + 0.08f * level(Stat::Power); }

private:
  int levels[STAT_COUNT] = {};
};
