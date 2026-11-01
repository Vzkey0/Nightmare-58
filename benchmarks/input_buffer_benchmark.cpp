// J-004: compares FixedQueue with DynQueue on the input buffer's per-frame work.
#include <iostream>

#include <array.hpp>
#include <now.hpp>
#include <queue.hpp>
#include <sort.hpp>

struct Press
{
  int action = 0;
  double time = 0.0;
};

static constexpr int SAMPLES = 101;
static constexpr int FRAMES_PER_SAMPLE = 20000;

// A press arrives every 16 frames, roughly five per second of play at 60 FPS.
static constexpr int FRAMES_PER_PRESS = 16;

template <class Queue>
static double median_ns(Queue & queue, int capacity)
{
  Designar::DynArray<double> samples;
  Designar::Now now(Designar::Now::Precision::NANOSECONDS);
  double oldest = 0.0;

  for (int sample = 0; sample < SAMPLES; ++sample)
  {
    now.start();
    for (int frame = 0; frame < FRAMES_PER_SAMPLE; ++frame)
    {
      if (frame % FRAMES_PER_PRESS == 0)
      {
        if (static_cast<int>(queue.size()) == capacity)
          queue.get();
        queue.put(Press{1, static_cast<double>(frame)});
      }
      if (!queue.is_empty())
        oldest += queue.front().time;
    }
    samples.append(now.elapsed() / FRAMES_PER_SAMPLE);
  }

  if (oldest < 0.0)
    std::cout << "unexpected time\n";

  Designar::insertion_sort(samples);
  return samples[SAMPLES / 2];
}

template <int CAPACITY>
static void measure()
{
  Designar::FixedQueue<Press, CAPACITY> fixed_queue;
  Designar::DynQueue<Press> dynamic_queue;

  const double fixed_ns = median_ns(fixed_queue, CAPACITY);
  const double dynamic_ns = median_ns(dynamic_queue, CAPACITY);

  std::cout << CAPACITY << " presses: FixedQueue " << fixed_ns << " ns, DynQueue " << dynamic_ns
            << " ns per frame\n";
}

int main()
{
  measure<2>();
  measure<20>();
  return 0;
}
