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
  // ponytail: one window over both snaps, so it bites once; a second window if it should bite twice.
  static constexpr EnemyTiming SNAP{1.467f, 0.4f, 0.53f, 0.82f, 14};
  static constexpr EnemyTiming LEAP{1.933f, 0.6f, 0.87f, 1.f, 22};
  static constexpr EnemyTiming THRASH{2.f, 0.4f, 0.53f, 0.66f, 20};
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
    case EnemyAction::Hurt:
      return HURT;
    case EnemyAction::Dead:
      return DEAD;
    default:
      return NONE;
  }
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
