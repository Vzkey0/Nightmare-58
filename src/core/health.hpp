#pragma once

class Health
{
public:
  explicit Health(int maximum) : maximum(maximum), current(maximum) {}

  void damage(int amount) { current = amount < current ? current - amount : 0; }
  void restore() { current = maximum; }

  int value() const { return current; }
  float ratio() const { return static_cast<float>(current) / maximum; }
  bool dead() const { return current == 0; }

private:
  int maximum;
  int current;
};
