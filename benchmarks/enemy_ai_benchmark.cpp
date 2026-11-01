// J-005 and J-006: what the enemies' decisions cost per physics tick. Compares thinking on every
// tick with thinking ten times a second, and a turn counter with scanning a list of enemies.
#include <iostream>

#include <array.hpp>
#include <now.hpp>
#include <sort.hpp>

#include <core/ai/attack_turns.hpp>
#include <core/ai/behavior_tree.hpp>
#include <core/ai/enemy_actions.hpp>

static constexpr int SAMPLES = 101;
static constexpr int TICKS_PER_SAMPLE = 6000;
static constexpr int TICKS_PER_THINK = 6; // Ten times a second at 60 ticks.
static constexpr float TICK = 1.f / 60.f;

// A volatile input keeps the compiler from folding the decisions away.
static volatile float volatile_distance = 3.f;

struct Enemy
{
  BehaviorTree tree;
  EnemyActions actions;
  bool holds_turn = false;
};

static BehaviorTree::AttackQueue queue_of(int id)
{
  BehaviorTree::AttackQueue attacks;
  attacks.put(Attack{id});
  return attacks;
}

template <class Tick>
static double median_ns(Tick tick)
{
  Designar::DynArray<double> samples;
  Designar::Now now(Designar::Now::Precision::NANOSECONDS);

  for (int sample = 0; sample < SAMPLES; ++sample)
  {
    now.start();
    for (int run = 0; run < TICKS_PER_SAMPLE; ++run)
      tick(run);
    samples.append(now.elapsed() / TICKS_PER_SAMPLE);
  }

  Designar::insertion_sort(samples);
  return samples[SAMPLES / 2];
}

// The longest walk of the tree: every branch fails until the last one, which circles.
static EnemyContext context_of(float distance)
{
  return EnemyContext{1.f, classify_distance(distance, 1.9f, 4.4f), true, true, false, false};
}

static void measure(int count)
{
  Enemy ** enemies = new Enemy *[count];
  for (int i = 0; i < count; ++i)
    enemies[i] = new Enemy{BehaviorTree::skeleton(queue_of(0), queue_of(2))};

  int sink = 0;
  const double every_tick = median_ns([&](int) {
    for (int i = 0; i < count; ++i)
    {
      enemies[i]->actions.update(TICK);
      sink += static_cast<int>(enemies[i]->tree.decide(context_of(volatile_distance)).action);
    }
  });
  const double staggered = median_ns([&](int run) {
    for (int i = 0; i < count; ++i)
    {
      enemies[i]->actions.update(TICK);
      if ((run + i) % TICKS_PER_THINK == 0)
        sink += static_cast<int>(enemies[i]->tree.decide(context_of(volatile_distance)).action);
    }
  });

  AttackTurns turns;
  const double counter = median_ns([&](int) {
    for (int i = 0; i < count; ++i)
      sink += turns.available();
  });
  const double scan = median_ns([&](int) {
    for (int i = 0; i < count; ++i)
    {
      int used = 0;
      for (int other = 0; other < count; ++other)
        used += enemies[other]->holds_turn;
      sink += used < AttackTurns::MAX_TURNS;
    }
  });

  std::cout << count << " enemies, ns per tick: thinking every tick " << every_tick
            << ", ten times a second " << staggered << "; turn counter " << counter
            << ", scanning the enemies " << scan << " (" << sink % 2 << ")\n";

  for (int i = 0; i < count; ++i)
    delete enemies[i];
  delete[] enemies;
}

int main()
{
  measure(8);
  measure(80);
  return 0;
}
