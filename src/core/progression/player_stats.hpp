#pragma once

#include <core/progression/skill_tree.hpp>

enum class Stat { Health, Stamina, Regeneration, Speed, AttackRate, Power };

constexpr int STAT_COUNT = 6;

// Stats grow as three branches from the hero: each lead stat forks, after its first level, into its own
// higher levels and into a second stat that needs it.
constexpr int STAT_GROUPS = 3;
constexpr Stat STAT_LEADS[STAT_GROUPS] = {Stat::Health, Stat::Stamina, Stat::Power};
constexpr Stat STAT_FOLLOWERS[STAT_GROUPS] = {Stat::Regeneration, Stat::Speed, Stat::AttackRate};

// The values come from the PDD and get tuned by playing.
class PlayerStats
{
public:
  static constexpr int MAX_LEVEL = 5;
  static constexpr int BASE_HEALTH = 100;

  int level(Stat stat) const { return levels[static_cast<int>(stat)]; }
  bool can_raise(Stat stat) const { return level(stat) < MAX_LEVEL && opened(stat); }

  // A second stat opens with the first level of the one that leads its branch.
  bool opened(Stat stat) const
  {
    for (int group = 0; group < STAT_GROUPS; ++group)
      if (STAT_FOLLOWERS[group] == stat)
        return level(STAT_LEADS[group]) > 0;
    return true;
  }

  // One node per level, so the tree draws like the machete's. Node 0 is the hero.
  static int node(Stat stat, int level) { return 1 + static_cast<int>(stat) * MAX_LEVEL + level - 1; }
  static Stat stat_of(int node) { return static_cast<Stat>((node - 1) / MAX_LEVEL); }
  static int level_of(int node) { return (node - 1) % MAX_LEVEL + 1; }

  static SkillTree tree()
  {
    SkillTree tree(0);
    for (int group = 0; group < STAT_GROUPS; ++group)
    {
      const Stat lead = STAT_LEADS[group];
      const Stat follower = STAT_FOLLOWERS[group];
      tree.add(0, node(lead, 1), 0);
      for (int level = 2; level <= MAX_LEVEL; ++level)
        tree.add(node(lead, level - 1), node(lead, level), 0);
      tree.add(node(lead, 1), node(follower, 1), 0);
      for (int level = 2; level <= MAX_LEVEL; ++level)
        tree.add(node(follower, level - 1), node(follower, level), 0);
    }
    return tree;
  }
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
  int next_cost() const { return 50 + 25 * total_levels(); }

  int max_health() const { return BASE_HEALTH + BASE_HEALTH * level(Stat::Health) / 10; }
  float stamina_regen_scale() const { return 1.f + 0.1f * level(Stat::Stamina); }
  float regen_per_second() const { return 0.5f * level(Stat::Regeneration); }
  float speed_scale() const { return 1.f + 0.04f * level(Stat::Speed); }
  float attack_rate() const { return 1.f + 0.05f * level(Stat::AttackRate); }
  float damage_scale() const { return 1.f + 0.08f * level(Stat::Power); }

private:
  int levels[STAT_COUNT] = {};
};
