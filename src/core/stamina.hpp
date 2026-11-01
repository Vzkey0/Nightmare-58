#pragma once

#include <algorithm>

// Stops at 0: an action with anything left still comes out, and the wait pays for it.
// Emptying the bar also stops the sprint until a share of it is back.
class Stamina
{
public:
  static constexpr float REGEN_RATE = 42.f;
  static constexpr float REGEN_DELAY = 0.5f;
  static constexpr float WINDED_UNTIL = 0.25f;

  explicit Stamina(float maximum) : maximum(maximum), current(maximum) {}

  void spend(float amount)
  {
    current = std::max(current - amount, 0.f);
    wait = REGEN_DELAY;
    out_of_breath = out_of_breath || current == 0.f;
  }

  void update(float delta, bool resting)
  {
    if (!resting)
      return;
    if (wait > 0.f)
    {
      wait -= delta;
      return;
    }
    current = std::min(current + REGEN_RATE * delta, maximum);
    out_of_breath = out_of_breath && ratio() < WINDED_UNTIL;
  }

  void restore()
  {
    current = maximum;
    wait = 0.f;
    out_of_breath = false;
  }

  float ratio() const { return current / maximum; }
  bool can_act() const { return current > 0.f; }
  bool winded() const { return out_of_breath; }

private:
  float maximum;
  float current;
  float wait = 0.f;
  bool out_of_breath = false;
};
