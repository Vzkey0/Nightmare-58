#include <core/player/player_actions.hpp>

#include <algorithm>

const ActionTiming & PlayerActions::timing(PlayerAction action)
{
  static constexpr ActionTiming NONE{0.f, 0.f, 0.f};
  static constexpr ActionTiming DODGE{0.77f, 0.5f, 0.57f, 0.f, 0.f, 0, 0.f, 0.47f};
  static constexpr ActionTiming ATTACK{0.8f, 0.45f, 0.55f, 0.17f, 0.37f, 20, 0.37f};
  static constexpr ActionTiming ATTACK_2{0.87f, 0.5f, 0.6f, 0.12f, 0.36f, 22, 0.36f};
  static constexpr ActionTiming ATTACK_3{1.33f, 0.85f, 0.95f, 0.4f, 0.52f, 30, 0.55f, 0.47f};
  static constexpr ActionTiming ROLL_ATTACK{0.8f, 0.5f, 0.6f, 0.17f, 0.33f, 24, 0.33f};
  static constexpr ActionTiming RUN_ATTACK{1.f, 0.62f, 0.72f, 0.15f, 0.37f, 26, 0.4f};
  static constexpr ActionTiming JUMP{0.33f, 0.12f, 0.33f};
  // Past its duration on purpose: the clip must end before another air attack restarts it.
  static constexpr ActionTiming AIR_ATTACK{0.7f, 0.75f, 0.7f, 0.23f, 0.43f, 30};

  switch (action)
  {
    case PlayerAction::Attack:
      return ATTACK;
    case PlayerAction::Attack2:
      return ATTACK_2;
    case PlayerAction::Attack3:
      return ATTACK_3;
    case PlayerAction::RollAttack:
      return ROLL_ATTACK;
    case PlayerAction::RunAttack:
      return RUN_ATTACK;
    case PlayerAction::Jump:
      return JUMP;
    case PlayerAction::AirAttack:
      return AIR_ATTACK;
    case PlayerAction::Dodge:
      return DODGE;
    default:
      return NONE;
  }
}

float PlayerActions::step_scale(float gap, float clip_step)
{
  return std::clamp(gap / clip_step, MIN_STEP_SCALE, MAX_STEP_SCALE);
}

PlayerActions::PlayerActions()
{
  combo.append(PlayerAction::Attack);
  combo.append(PlayerAction::Attack2);
  combo.append(PlayerAction::Attack3);
}

PlayerAction PlayerActions::next_attack() const
{
  bool found = false;
  for (const PlayerAction step : combo)
  {
    if (found)
      return step;
    found = step == last_step;
  }
  return combo.get_first();
}

float PlayerActions::interrupt_time(PlayerAction pressed) const
{
  const ActionTiming & current_timing = timing(action);
  const bool dodge_early = pressed == PlayerAction::Dodge && current_timing.dodge_cancel > 0.f;
  return dodge_early ? current_timing.dodge_cancel : current_timing.next_action;
}

void PlayerActions::press(PlayerAction pressed)
{
  if (pressed == PlayerAction::Dodge)
    buffer.clear();
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

  const bool free = action == PlayerAction::None;
  if (!buffer.is_empty() && (free || action_time >= interrupt_time(buffer.front().action)) &&
      (grounded || buffer.front().action == PlayerAction::Attack))
  {
    const PlayerAction next = buffer.get().action;
    if (next != PlayerAction::Attack)
    {
      if (next != PlayerAction::Dodge)
        last_step = PlayerAction::None;
      action = next;
    }
    else if (!grounded)
      action = PlayerAction::AirAttack;
    else if (action == PlayerAction::Dodge)
      action = PlayerAction::RollAttack;
    else if (free && wants_to_move && button_held && held_time >= TAP_TIME)
      action = PlayerAction::RunAttack;
    else
      action = last_step = next_attack();
    action_time = 0.f;
    return true;
  }

  if (!free)
  {
    const ActionTiming & current_timing = timing(action);
    if (action_time >= current_timing.duration ||
        (wants_to_move && action_time >= current_timing.move_cancel))
    {
      action = PlayerAction::None;
      last_step = PlayerAction::None;
    }
  }
  return false;
}
