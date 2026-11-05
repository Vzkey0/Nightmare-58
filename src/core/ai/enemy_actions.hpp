#pragma once

// The attacks stay first: their value is the attack id the behavior tree hands out.
// Chop, Sweep and Lunge are the skeleton's; Bite, Pounce and Rake the rat's; Snap, Leap and Thrash the dog's;
// the rest are Güino's, the last two only in his fury.
enum class EnemyAction
{
  Chop, Sweep, Lunge, Bite, Pounce, Rake, Snap, Leap, Thrash,
  Maul, Crunch, Whirl, Crash, Frenzy, Quake,
  None, Hurt, Dead
};

// Seconds from the start of the clip. duration must match the animate_*.py of its enemy in art/characters.
struct EnemyTiming
{
  static constexpr int MAX_AGAIN = 3;

  float duration;
  float track_end = 0.f; // It stops turning to the player here, so a late dodge escapes the blow.
  float hit_start = 0.f;
  float hit_end = 0.f;
  int damage = 0;
  // Where the later blows of a combo start, each as long as the first; 0 ends the list. Until
  // track_end it keeps turning to the player between blows, but never during one.
  float again[MAX_AGAIN] = {};
};

// What an enemy is doing, once the behavior tree has chosen. Walking can always change; an
// attack runs to its end unless a blow staggers it before the swing.
class EnemyActions
{
public:
  static constexpr float STAGGER_GUARD = 2.5f; // A combo staggers once, not until the enemy dies.

  static const EnemyTiming & timing(EnemyAction action);

  // Which blow of the attack is landing at time, or -1 between them.
  static int window_at(const EnemyTiming & timing, float time);

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
  bool attacking() const { return action < EnemyAction::None; }
  bool winding_up() const { return attacking() && action_time < timing(action).hit_start; }
  int window() const { return attacking() ? window_at(timing(action), action_time) : -1; }
  bool hitting() const { return window() >= 0; }
  bool tracking() const { return attacking() && action_time < timing(action).track_end && !hitting(); }

private:
  EnemyAction action = EnemyAction::None;
  float action_time = 0.f;
  float stagger_guard = 0.f;
};
