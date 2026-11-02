// J-007 to J-012: the structures behind items, loot and the saved world. Each one is
// compared with its real alternatives, at the expected size and ten times that.
#include <iostream>
#include <string>

#include <array.hpp>
#include <bitset.hpp>
#include <map.hpp>
#include <now.hpp>
#include <set.hpp>
#include <sort.hpp>

#include <core/progression/player_progress.hpp>

static constexpr int SAMPLES = 101;
static constexpr int RUNS_PER_SAMPLE = 200;

static volatile int volatile_seed = 12345;

template <class Run>
static double median_ns(Run run)
{
  Designar::DynArray<double> samples;
  Designar::Now now(Designar::Now::Precision::NANOSECONDS);

  for (int sample = 0; sample < SAMPLES; ++sample)
  {
    now.start();
    for (int i = 0; i < RUNS_PER_SAMPLE; ++i)
      run(i);
    samples.append(now.elapsed() / RUNS_PER_SAMPLE);
  }

  Designar::insertion_sort(samples);
  return samples[SAMPLES / 2];
}

static unsigned next_random(unsigned & state)
{
  state = state * 1664525u + 1013904223u;
  return state >> 8;
}

static void measure_lookup(int count)
{
  Designar::DynArray<std::string> keys;
  Designar::HashMap<std::string, int> table(static_cast<Designar::nat_t>(count * 2));
  for (int i = 0; i < count; ++i)
  {
    keys.append("item_key_" + std::to_string(i));
    table.insert(keys[i], i);
  }
  Designar::DynArray<std::string> sorted = keys;
  Designar::insertion_sort(sorted);

  // A probe through a volatile index, so the compiler cannot see which key is asked for.
  int sink = 0;
  const double hash = median_ns([&](int i) { sink += *table.search(keys[(i * 7 + volatile_seed) % count]); });
  const double binary = median_ns([&](int i) {
    const std::string & key = keys[(i * 7 + volatile_seed) % count];
    sink += static_cast<int>(Designar::binary_search(sorted, key));
  });
  const double linear = median_ns([&](int i) {
    const std::string & key = keys[(i * 7 + volatile_seed) % count];
    int found = 0;
    while (keys[found] != key)
      ++found;
    sink += found;
  });

  std::cout << "lookup " << count << " keys, ns: hash " << hash << ", binary search " << binary
            << ", linear " << linear << " (" << sink % 2 << ")\n";
}

struct Stack
{
  int item;
  int count;
};

static void measure_counts(int count)
{
  Designar::DynArray<int> counts(static_cast<Designar::nat_t>(count), 0);
  Designar::DynArray<Stack> stacks;
  for (int i = 0; i < count; ++i)
    stacks.append(Stack{i, 0});

  const double indexed = median_ns([&](int i) { ++counts[(i * 7 + volatile_seed) % count]; });
  const double scanned = median_ns([&](int i) {
    const int item = (i * 7 + volatile_seed) % count;
    int found = 0;
    while (stacks[found].item != item)
      ++found;
    ++stacks[found].count;
  });

  std::cout << "add to inventory " << count << " items, ns: count per id " << indexed
            << ", scanning stacks " << scanned << " (" << counts[0] + stacks[0].count << ")\n";
}

struct Row
{
  int kind;
  int order;
};

struct RowLess
{
  bool operator()(const Row & a, const Row & b) const { return a.kind < b.kind; }
};

static void measure_sort(int count)
{
  Designar::DynArray<Row> shuffled;
  unsigned state = static_cast<unsigned>(volatile_seed);
  for (int i = 0; i < count; ++i)
    shuffled.append(Row{static_cast<int>(next_random(state) % 4), i});

  int sink = 0;
  const double merge = median_ns([&](int) {
    Designar::DynArray<Row> rows = shuffled;
    Designar::merge_sort(rows, RowLess());
    sink += rows[0].order;
  });
  const double insertion = median_ns([&](int) {
    Designar::DynArray<Row> rows = shuffled;
    Designar::insertion_sort(rows, RowLess());
    sink += rows[0].order;
  });
  const double copy_only = median_ns([&](int) {
    Designar::DynArray<Row> rows = shuffled;
    sink += rows[0].order;
  });

  std::cout << "sort " << count << " rows, ns: merge_sort " << merge << ", insertion_sort " << insertion
            << ", copy alone " << copy_only << " (" << sink % 2 << ")\n";
}

struct CumulativeLess
{
  bool operator()(int a, int b) const { return a < b; }
};

static void measure_loot(int count)
{
  Designar::DynArray<int> cumulative;
  int total = 0;
  for (int i = 0; i < count; ++i)
  {
    total += 1 + i % 5;
    cumulative.append(total);
  }

  int sink = 0;
  unsigned state = static_cast<unsigned>(volatile_seed);
  CumulativeLess less;
  const double binary = median_ns([&](int) {
    const int roll = static_cast<int>(next_random(state) % total);
    int found = static_cast<int>(Designar::binary_search(cumulative, roll, less));
    found = found < count && cumulative[found] <= roll ? found + 1 : found;
    sink += found;
  });
  const double linear = median_ns([&](int) {
    const int roll = static_cast<int>(next_random(state) % total);
    int found = 0;
    while (cumulative[found] <= roll)
      ++found;
    sink += found;
  });

  std::cout << "loot roll " << count << " entries, ns: binary search " << binary << ", linear " << linear
            << " (" << sink % 2 << ")\n";
}

static void measure_taken(int count)
{
  Designar::DynBitSet bits(static_cast<Designar::nat_t>(count));
  Designar::HashSet<int> table;
  Designar::DynArray<int> list;
  for (int i = 0; i < count; i += 2)
  {
    bits[i] = true;
    table.insert(i);
    list.append(i);
  }

  int sink = 0;
  const double bit = median_ns([&](int i) { sink += bits[(i * 7 + volatile_seed) % count]; });
  const double hash = median_ns([&](int i) { sink += table.search((i * 7 + volatile_seed) % count) != nullptr; });
  const double scan = median_ns([&](int i) {
    const int wanted = (i * 7 + volatile_seed) % count;
    int found = 0;
    for (int at = 0; at < static_cast<int>(list.size()); ++at)
      found += list[at] == wanted;
    sink += found;
  });

  std::cout << "taken check " << count << " pickups, ns: DynBitSet " << bit << ", HashSet " << hash
            << ", scanning a list " << scan << " (" << sink % 2 << ")\n";
}

// A full game: every item, half the pickups taken and a death mark.
static void measure_save()
{
  PlayerProgress progress;
  progress.earn(5000);
  const ItemCatalog & catalog = ItemCatalog::instance();
  for (ItemId item = 0; item < catalog.size(); ++item)
    progress.collect(item, 2);
  for (int id = 0; id < PlayerProgress::MAX_PICKUPS; id += 2)
    progress.take_pickup(id);
  progress.die(1.f, 2.f, 3.f);

  const std::string text = progress.to_text();
  size_t sink = 0;
  const double write = median_ns([&](int) { sink += progress.to_text().size(); });
  PlayerProgress loaded;
  const double read = median_ns([&](int) { sink += loaded.from_text(text); });

  std::cout << "save, " << text.size() << " bytes, ns: to_text " << write << ", from_text " << read << " (" << sink % 2 << ")\n";
}

int main()
{
  measure_lookup(30);
  measure_lookup(300);
  measure_counts(30);
  measure_counts(300);
  measure_sort(30);
  measure_sort(300);
  measure_loot(6);
  measure_loot(60);
  measure_taken(40);
  measure_taken(400);
  measure_save();
  return 0;
}
