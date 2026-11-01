#pragma once

class Health
{
public:
  explicit Health(int maximum) : maximum(maximum), current(maximum) {}

  void damage(int amount) { current = amount < current ? current - amount : 0; }
  void restore() { current = maximum; }

  int value() const { return current; }
  bool dead() const { return current == 0; }

private:
  int maximum;
  int current;
};
