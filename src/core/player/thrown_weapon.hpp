#pragma once

// The flight of a thrown machete: out in a straight line, then back to the hand wherever it is.
// The caller owns the positions; this only decides how far to move and when the flight turns.
class ThrownWeapon
{
public:
  static constexpr float RANGE = 9.f;
  static constexpr float OUT_SPEED = 17.f;
  static constexpr float BACK_SPEED = 19.f;
  static constexpr float CATCH_RADIUS = 0.5f;
  static constexpr float MAX_FLIGHT = 3.f; // A machete stuck behind a wall comes back anyway.
  static constexpr int DAMAGE = 18;

  enum class Phase { InHand, Out, Back };

  void release()
  {
    phase = Phase::Out;
    travelled = 0.f;
    flight_time = 0.f;
  }

  // How far to move on this tick. On the way out it turns back once it has gone its range.
  float step(float delta)
  {
    flight_time += delta;
    if (phase == Phase::Out)
    {
      const float length = travelled + OUT_SPEED * delta > RANGE ? RANGE - travelled : OUT_SPEED * delta;
      travelled += length;
      if (travelled >= RANGE)
        phase = Phase::Back;
      return length;
    }
    return phase == Phase::Back ? BACK_SPEED * delta : 0.f;
  }

  // Hitting a wall on the way out sends it back early.
  void turn_back()
  {
    if (phase == Phase::Out)
      phase = Phase::Back;
  }

  // True once it reaches the hand: close enough to cover in this step, or out for too long.
  bool caught(float distance_to_hand, float step_length)
  {
    if (phase != Phase::Back || (distance_to_hand > step_length + CATCH_RADIUS && flight_time < MAX_FLIGHT))
      return false;
    phase = Phase::InHand;
    return true;
  }

  void drop() { phase = Phase::InHand; } // The player died: it is simply back.

  Phase current() const { return phase; }
  bool in_air() const { return phase != Phase::InHand; }
  bool heading_out() const { return phase == Phase::Out; }

private:
  Phase phase = Phase::InHand;
  float travelled = 0.f;
  float flight_time = 0.f;
};
