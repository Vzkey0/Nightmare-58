#pragma once

#include <queue.hpp>

enum class PlayerAction { None, Dodge, Attack, Jump, AirAttack };

// Seconds from the start of the clip. duration must match the clip in
// art/characters/animate_protagonist.py.
struct ActionTiming
{
  float duration;
  float next_action; // A buffered action may interrupt from here on.
  float move_cancel; // Moving may end the action from here on.
};

class PlayerActions
{
public:
  static constexpr int BUFFER_SIZE = 2;
  static constexpr float BUFFER_TIME = 0.45f;
  static constexpr float TAP_TIME = 0.22f;

  static const ActionTiming & timing(PlayerAction action);

  // Oldest press is dropped when the buffer is full: the newest one is the player's intent.
  void press(PlayerAction action);

  // One button, as in Elden Ring: a tap dodges on release and holding it sprints.
  // The sprint starts on press: a tap ends before its speed shows, so it needs no wait.
  void update_dodge_button(bool held, float delta);
  bool sprinting() const { return button_held; }

  // Returns true on the step where a new action starts, so the caller can start its clip.
  // In the air an attack becomes an air attack; a dodge or jump waits for the ground.
  bool update(float delta, bool wants_to_move, bool grounded = true);

  PlayerAction current() const { return action; }
  float elapsed() const { return action_time; }

private:
  struct Press
  {
    PlayerAction action = PlayerAction::None;
    double time = 0.0;
  };

  // J-004: small fixed capacity, so reads and writes never reserve memory.
  Designar::FixedQueue<Press, BUFFER_SIZE> buffer;

  PlayerAction action = PlayerAction::None;
  float action_time = 0.f;
  float held_time = 0.f;
  bool button_held = false;
  double clock = 0.0;
};
