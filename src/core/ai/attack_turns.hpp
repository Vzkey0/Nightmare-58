#pragma once

// J-006: who may attack the player right now. The player owns one, so any number of enemies
// share it without knowing about each other, and without a list of them.
class AttackTurns
{
public:
  static constexpr int MAX_TURNS = 2;
  static constexpr float GAP = 0.7f; // Between two attacks starting, so they never land together.

  void update(float delta) { gap = gap > delta ? gap - delta : 0.f; }

  bool available() const { return used < MAX_TURNS && gap == 0.f; }

  void take()
  {
    ++used;
    gap = GAP;
  }

  void give_back() { --used; }

private:
  int used = 0;
  float gap = 0.f;
};
