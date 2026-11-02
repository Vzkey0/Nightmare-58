#pragma once

#include <list.hpp>
#include <queue.hpp>

#include <core/stamina.hpp>

// Attack, Attack2 and Attack3 stay together: PlayerController::attack_clip follows this order.
enum class PlayerAction { None, Dodge, Attack, Attack2, Attack3, Jump, AirAttack, RollAttack, RunAttack, HeavyAttack, Hurt, Dead, UseItem };

// Seconds from the start of the clip. duration must match the clip in
// art/characters/animate_protagonist.py.
struct ActionTiming
{
  float duration;
  float next_action; // A buffered action may interrupt from here on.
  float move_cancel; // Moving may end the action from here on.
  // The whole swing, from leaving the raised pose until the weapon stops: see the weapon
  // rules in docs/art_guide.md. An action without a swing has an empty window.
  float hit_start = 0.f;
  float hit_end = 0.f;
  int damage = 0;
  float dodge_cancel = 0.f; // A dodge may interrupt from here on; 0 waits for next_action.
  float ground_hit = 0.f;   // When the body or the weapon lands, or an item takes effect; 0 never does.
  float stamina_cost = 0.f;
};

class PlayerActions
{
public:
  static constexpr int BUFFER_SIZE = 2;
  static constexpr float BUFFER_TIME = 0.45f;
  static constexpr float TAP_TIME = 0.22f;
  static constexpr float MIN_STEP_SCALE = 0.25f;
  static constexpr float MAX_STEP_SCALE = 1.6f;
  static constexpr float MAX_STAMINA = 100.f;
  static constexpr float SPRINT_COST = 14.f; // Per second.
  static constexpr float DODGE_SAFE_TIME = 0.43f; // Invulnerable until the roll starts to land.

  static constexpr int NO_COMBO_STEP = -1;

  static const ActionTiming & timing(PlayerAction action);

  // How much of an attack's root motion to use so that it ends gap metres ahead, within
  // limits: a blow bends towards its target, it does not teleport.
  static float step_scale(float gap, float clip_step);

  PlayerActions();

  // Oldest press is dropped when the buffer is full: the newest one is the player's intent.
  // A dodge also replaces what was queued: it must not wait behind a mashed attack.
  void press(PlayerAction action);

  // One button, as in Elden Ring: a tap dodges on release and holding it sprints.
  // The sprint starts on press: a tap ends before its speed shows, so it needs no wait.
  void update_dodge_button(bool held, float delta);
  bool sprinting() const { return button_held && !stamina.winded(); }

  // Returns true on the step where a new action starts, so the caller can start its clip.
  // An attack pressed during a combo step becomes the next step, and the last leads back to
  // the first. One pressed during a dodge becomes a roll attack, and the combo carries on
  // after it. One pressed while sprinting becomes a run attack. In the air an attack becomes
  // an air attack, which finishes its swing if it lands; a dodge or jump waits for the ground.
  // A press with no stamina left waits in the buffer.
  bool update(float delta, bool wants_to_move, bool grounded = true);

  // The caller plays the clip: these interrupt anything, and drop what was queued.
  void hurt() { interrupt(PlayerAction::Hurt); }
  void die() { interrupt(PlayerAction::Dead); }
  void revive();

  PlayerAction current() const { return action; }
  float elapsed() const { return action_time; }
  float stamina_ratio() const { return stamina.ratio(); }
  bool winded() const { return stamina.winded(); }
  void set_stamina_regen(float scale) { stamina.set_regen_scale(scale); }

  bool invulnerable() const
  {
    return action == PlayerAction::Hurt || action == PlayerAction::Dead ||
           (action == PlayerAction::Dodge && action_time < DODGE_SAFE_TIME);
  }

  int combo_step() const
  {
    const bool attacking = action >= PlayerAction::Attack && action <= PlayerAction::Attack3;
    return attacking ? static_cast<int>(action) - static_cast<int>(PlayerAction::Attack) : NO_COMBO_STEP;
  }

  // The attacks that walk on their clip's root motion.
  bool stepping_attack() const
  {
    return combo_step() != NO_COMBO_STEP || action == PlayerAction::RollAttack ||
           action == PlayerAction::RunAttack || action == PlayerAction::HeavyAttack;
  }

  bool hitting() const
  {
    const ActionTiming & current_timing = timing(action);
    return action_time >= current_timing.hit_start && action_time < current_timing.hit_end;
  }

  // True on the one step where the action lands.
  bool hit_ground(float delta) const
  {
    const float landing = timing(action).ground_hit;
    return landing > 0.f && action_time >= landing && action_time - delta < landing;
  }

private:
  struct Press
  {
    PlayerAction action = PlayerAction::None;
    double time = 0.0;
  };

  PlayerAction next_attack() const;
  float interrupt_time(PlayerAction pressed) const;
  void interrupt(PlayerAction forced);

  // A list so a weapon upgrade can append a step.
  Designar::SLList<PlayerAction> combo;

  // J-004: small fixed capacity, so reads and writes never reserve memory.
  Designar::FixedQueue<Press, BUFFER_SIZE> buffer;

  Stamina stamina{MAX_STAMINA};
  PlayerAction action = PlayerAction::None;
  PlayerAction last_step = PlayerAction::None;
  float action_time = 0.f;
  float held_time = 0.f;
  bool button_held = false;
  double clock = 0.0;
};
