#pragma once

#include <list.hpp>

// Holy only coats the blade: it hurts the dead more and leaves nothing on them.
enum class Status { Burn, Chill, Holy };

// What a greased blade leaves on an enemy. Each burn keeps its own clock and they stack up to a
// limit; a chill only refreshes, since being twice as slow would freeze the enemy in place.
class StatusEffects
{
public:
  static constexpr float BURN_TIME = 4.f;
  static constexpr float BURN_TICK = 0.5f;
  static constexpr int BURN_DAMAGE = 2; // Per tick and burn: 16 over a whole burn.
  static constexpr int MAX_BURNS = 3;
  static constexpr float CHILL_TIME = 3.f;
  static constexpr float CHILL_SLOW = 0.5f;

  void apply(Status kind)
  {
    if (kind == Status::Chill || count(Status::Burn) == MAX_BURNS)
    {
      // A full stack refreshes the oldest burn instead of adding one.
      for (Effect & effect : effects)
        if (effect.kind == kind)
        {
          effect.left = time_for(kind);
          return;
        }
    }
    effects.append(Effect{kind, time_for(kind), BURN_TICK});
  }

  // Advances every effect, drops the spent ones and returns the burn damage due on this tick.
  int update(float delta)
  {
    int damage = 0;
    // J-016: removing in the middle of the walk is O(1) on a list.
    auto it = effects.begin();
    while (it.has_current())
    {
      Effect & effect = it.get_current();
      effect.left -= delta;
      effect.tick -= delta;
      if (effect.kind == Status::Burn && effect.tick <= 0.f)
      {
        damage += BURN_DAMAGE;
        effect.tick += BURN_TICK;
      }
      if (effect.left <= 0.f)
        it.del();
      else
        it.next();
    }
    return damage;
  }

  int count(Status kind) const
  {
    int found = 0;
    for (const Effect & effect : effects)
      found += effect.kind == kind ? 1 : 0;
    return found;
  }

  bool has(Status kind) const { return count(kind) > 0; }
  float slow_scale() const { return has(Status::Chill) ? CHILL_SLOW : 1.f; }

  void clear()
  {
    while (!effects.is_empty())
      effects.remove_first();
  }

private:
  struct Effect
  {
    Status kind;
    float left;
    float tick; // Until the next burn damage.
  };

  static float time_for(Status kind) { return kind == Status::Burn ? BURN_TIME : CHILL_TIME; }

  // J-016: a few effects at once, of any kind, each with its own clock, and they come and go.
  Designar::SLList<Effect> effects;
};

// The grease on the player's blade. It lasts a minute whether the player swings or not.
class WeaponCoat
{
public:
  static constexpr float DURATION = 60.f;

  void apply(Status kind)
  {
    coat = kind;
    left = DURATION;
  }

  void update(float delta) { left = left > delta ? left - delta : 0.f; }
  void clear() { left = 0.f; }
  bool active() const { return left > 0.f; }
  Status kind() const { return coat; }
  float ratio() const { return left / DURATION; }

private:
  Status coat = Status::Burn;
  float left = 0.f;
};
