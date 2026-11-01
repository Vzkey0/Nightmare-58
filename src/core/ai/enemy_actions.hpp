#pragma once

// Chop, Sweep and Lunge stay first: their value is the attack id the behavior tree hands out.
enum class EnemyAction { Chop, Sweep, Lunge, None, Hurt, Dead };

// Seconds from the start of the clip. duration must match art/characters/animate_skeleton.py.
struct EnemyTiming
{
  float duration;
  float track_end = 0.f; // It stops turning to the player here, so a late dodge escapes the blow.
  float hit_start = 0.f;
  float hit_end = 0.f;
  int damage = 0;
};

// What an enemy is doing, once the behavior tree has chosen. Walking can always change; an
// attack runs to its end unless a blow staggers it before the swing.
class EnemyActions
{
public:
  static constexpr float STAGGER_GUARD = 2.5f; // A combo staggers once, not until the enemy dies.

  static const EnemyTiming & timing(EnemyAction action);

  // Returns true on the step where an action ends by itself.
  bool update(float delta);

  void start(EnemyAction attack);

  // Returns true if the blow staggers: the swing itself cannot be stopped.
  bool hurt();
  void die();
  void revive();

  EnemyAction current() const { return action; }
  float elapsed() const { return action_time; }
  bool busy() const { return action != EnemyAction::None; }
  bool attacking() const { return action <= EnemyAction::Lunge; }
  bool tracking() const { return attacking() && action_time < timing(action).track_end; }
  bool winding_up() const { return attacking() && action_time < timing(action).hit_start; }

  bool hitting() const
  {
    return attacking() && action_time >= timing(action).hit_start && action_time < timing(action).hit_end;
  }

private:
  EnemyAction action = EnemyAction::None;
  float action_time = 0.f;
  float stagger_guard = 0.f;
};
