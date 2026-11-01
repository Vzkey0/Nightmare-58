#include <core/player/player_actions.hpp>

const ActionTiming & PlayerActions::timing(PlayerAction action)
{
  static constexpr ActionTiming DODGE{0.8f, 0.53f, 0.6f};
  static constexpr ActionTiming ATTACK{1.f, 0.63f, 0.73f};
  static constexpr ActionTiming JUMP{0.33f, 0.12f, 0.33f};
  // Past its duration on purpose: the clip must end before another air attack restarts it.
  static constexpr ActionTiming AIR_ATTACK{0.7f, 0.75f, 0.7f};

  switch (action)
  {
    case PlayerAction::Attack:
      return ATTACK;
    case PlayerAction::Jump:
      return JUMP;
    case PlayerAction::AirAttack:
      return AIR_ATTACK;
    default:
      return DODGE;
  }
}

void PlayerActions::press(PlayerAction pressed)
{
  if (buffer.is_full())
    buffer.get();
  buffer.put(Press{pressed, clock});
}

void PlayerActions::update_dodge_button(bool held, float delta)
{
  if (held)
    held_time += delta;
  else
  {
    if (button_held && held_time < TAP_TIME)
      press(PlayerAction::Dodge);
    held_time = 0.f;
  }
  button_held = held;
}

bool PlayerActions::update(float delta, bool wants_to_move, bool grounded)
{
  clock += delta;
  action_time += delta;

  while (!buffer.is_empty() && clock - buffer.front().time > BUFFER_TIME)
    buffer.get();

  if (action == PlayerAction::AirAttack && grounded)
    action = PlayerAction::None;

  const bool free = action == PlayerAction::None;
  if (!buffer.is_empty() && (free || action_time >= timing(action).next_action) &&
      (grounded || buffer.front().action == PlayerAction::Attack))
  {
    const PlayerAction next = buffer.get().action;
    action = next == PlayerAction::Attack && !grounded ? PlayerAction::AirAttack : next;
    action_time = 0.f;
    return true;
  }

  if (!free)
  {
    const ActionTiming & current_timing = timing(action);
    if (action_time >= current_timing.duration ||
        (wants_to_move && action_time >= current_timing.move_cancel))
      action = PlayerAction::None;
  }
  return false;
}
