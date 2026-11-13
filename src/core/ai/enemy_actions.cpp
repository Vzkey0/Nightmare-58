#include <core/ai/enemy_actions.hpp>

const EnemyTiming & EnemyActions::timing(EnemyAction action)
{
  static constexpr EnemyTiming NONE{0.f};
  static constexpr EnemyTiming CHOP{1.467f, 0.5f, 0.6f, 0.75f, 20};
  static constexpr EnemyTiming SWEEP{1.333f, 0.4f, 0.5f, 0.66f, 16};
  static constexpr EnemyTiming LUNGE{1.867f, 0.7f, 0.87f, 1.03f, 26};
  static constexpr EnemyTiming BITE{1.133f, 0.45f, 0.57f, 0.7f, 10};
  static constexpr EnemyTiming POUNCE{1.8f, 0.6f, 0.9f, 1.03f, 16};
  static constexpr EnemyTiming RAKE{1.667f, 0.5f, 0.63f, 0.73f, 14};
  static constexpr EnemyTiming SNAP{1.467f, 0.4f, 0.53f, 0.63f, 10, {0.77f}};
  static constexpr EnemyTiming LEAP{1.933f, 0.6f, 0.87f, 1.f, 22};
  static constexpr EnemyTiming THRASH{2.f, 0.4f, 0.53f, 0.66f, 20};
  // Güino keeps turning between the blows of a combo, which is most of what makes him hard.
  static constexpr EnemyTiming MAUL{2.4f, 1.2f, 0.667f, 0.8f, 22, {1.367f}};
  static constexpr EnemyTiming CRUNCH{1.867f, 0.5f, 0.667f, 0.833f, 30};
  static constexpr EnemyTiming WHIRL{2.f, 0.45f, 0.633f, 0.9f, 24};
  static constexpr EnemyTiming CRASH{2.4f, 0.7f, 1.033f, 1.167f, 32};
  static constexpr EnemyTiming FRENZY{2.8f, 1.35f, 0.433f, 0.567f, 18, {0.667f, 0.9f, 1.5f}};
  static constexpr EnemyTiming QUAKE{2.467f, 0.7f, 0.933f, 1.067f, 34};
  static constexpr EnemyTiming HURT{0.5f};
  // Only revive() ends it.
  static constexpr EnemyTiming DEAD{1e9f};

  switch (action)
  {
    case EnemyAction::Chop:
      return CHOP;
    case EnemyAction::Sweep:
      return SWEEP;
    case EnemyAction::Lunge:
      return LUNGE;
    case EnemyAction::Bite:
      return BITE;
    case EnemyAction::Pounce:
      return POUNCE;
    case EnemyAction::Rake:
      return RAKE;
    case EnemyAction::Snap:
      return SNAP;
    case EnemyAction::Leap:
      return LEAP;
    case EnemyAction::Thrash:
      return THRASH;
    case EnemyAction::Maul:
      return MAUL;
    case EnemyAction::Crunch:
      return CRUNCH;
    case EnemyAction::Whirl:
      return WHIRL;
    case EnemyAction::Crash:
      return CRASH;
    case EnemyAction::Frenzy:
      return FRENZY;
    case EnemyAction::Quake:
      return QUAKE;
    case EnemyAction::Hurt:
      return HURT;
    case EnemyAction::Dead:
      return DEAD;
    default:
      return NONE;
  }
}

int EnemyActions::window_at(const EnemyTiming & timing, float time)
{
  if (time >= timing.hit_start && time < timing.hit_end)
    return 0;
  const float length = timing.hit_end - timing.hit_start;
  for (int i = 0; i < EnemyTiming::MAX_AGAIN && timing.again[i] > 0.f; ++i)
    if (time >= timing.again[i] && time < timing.again[i] + length)
      return i + 1;
  return -1;
}

bool EnemyActions::update(float delta)
{
  stagger_guard = stagger_guard > delta ? stagger_guard - delta : 0.f;
  if (action == EnemyAction::None)
    return false;

  action_time += delta;
  if (action_time < timing(action).duration)
    return false;

  action = EnemyAction::None;
  action_time = 0.f;
  return true;
}

void EnemyActions::start(EnemyAction attack)
{
  action = attack;
  action_time = 0.f;
}

bool EnemyActions::hurt()
{
  const bool swinging = attacking() && !winding_up();
  if (swinging || stagger_guard > 0.f || action == EnemyAction::Dead)
    return false;

  action = EnemyAction::Hurt;
  action_time = 0.f;
  stagger_guard = STAGGER_GUARD;
  return true;
}

void EnemyActions::die()
{
  action = EnemyAction::Dead;
  action_time = 0.f;
}

void EnemyActions::revive()
{
  action = EnemyAction::None;
  action_time = 0.f;
  stagger_guard = 0.f;
}
