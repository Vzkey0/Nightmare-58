#pragma once

// The pale part of a health bar: it stays where the health was for a moment and then
// slides down, so the eye can read how much a hit took. Values go from 0 to 1.
class HealthTrail
{
public:
  static constexpr float HOLD_TIME = 0.45f;
  static constexpr float SLIDE_SPEED = 0.7f;

  void update(float health, float delta)
  {
    if (health < last_health)
      hold = HOLD_TIME;
    last_health = health;

    if (hold > 0.f)
      hold -= delta;
    else
      trail -= SLIDE_SPEED * delta;
    if (trail < health)
      trail = health;
  }

  float value() const { return trail; }

private:
  float trail = 1.f;
  float last_health = 1.f;
  float hold = 0.f;
};
