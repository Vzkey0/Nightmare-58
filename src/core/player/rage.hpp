#pragma once

// Modo Arrechera. The bar fills with every blow given or taken; once full it can be let loose for
// a while, hitting harder and taking more. While it burns the bar drains and nothing refills it.
class Rage
{
public:
  static constexpr float MAX = 100.f;
  static constexpr float DURATION = 12.f;
  static constexpr float PER_DAMAGE_DEALT = 0.8f; // About seven light blows fill it.
  static constexpr float PER_DAMAGE_TAKEN = 1.2f; // Being hit angers more than hitting.
  static constexpr float DEALT_SCALE = 1.4f;
  static constexpr float TAKEN_SCALE = 1.3f;

  void deal(int damage) { fill(damage * PER_DAMAGE_DEALT); }
  void take(int damage) { fill(damage * PER_DAMAGE_TAKEN); }

  bool activate()
  {
    if (!full() || active())
      return false;
    left = DURATION;
    return true;
  }

  void update(float delta)
  {
    if (!active())
      return;
    left = left > delta ? left - delta : 0.f;
    meter = MAX * left / DURATION;
  }

  void reset()
  {
    meter = 0.f;
    left = 0.f;
  }

  bool full() const { return meter >= MAX; }
  bool active() const { return left > 0.f; }
  float ratio() const { return meter / MAX; }
  float damage_dealt_scale() const { return active() ? DEALT_SCALE : 1.f; }
  float damage_taken_scale() const { return active() ? TAKEN_SCALE : 1.f; }

private:
  void fill(float amount)
  {
    if (!active())
      meter = meter + amount > MAX ? MAX : meter + amount;
  }

  float meter = 0.f;
  float left = 0.f;
};
