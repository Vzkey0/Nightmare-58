// J-002: compares MTreeNode with a flat DynArray walking the same worst case.
#include <iostream>

#include <array.hpp>
#include <mtreenode.hpp>
#include <now.hpp>
#include <sort.hpp>

enum class Type { Selector, Sequence, Condition, Action };

struct Data
{
  Type type;
  int key;
};

struct FlatNode
{
  Data data;
  int first_child;
  int right_sibling;
};

using TreeNode = Designar::MTreeNode<Data>;
using FlatTree = Designar::DynArray<FlatNode>;

static constexpr int SAMPLES = 101;
static constexpr int RUNS_PER_SAMPLE = 20000;

// A volatile input keeps the compiler from folding the walks away.
static volatile int input = -1;

static bool evaluate(const TreeNode * node, int value)
{
  const Data & data = node->get_key();
  if (data.type == Type::Condition)
    return data.key == value;
  if (data.type == Type::Action)
    return true;

  const bool stop_on = data.type == Type::Selector;
  for (const TreeNode * child = node->get_first_child(); child != nullptr;
       child = child->get_right_sibling())
    if (evaluate(child, value) == stop_on)
      return stop_on;

  return !stop_on;
}

static bool evaluate(const FlatTree & tree, int index, int value)
{
  const FlatNode & node = tree[index];
  if (node.data.type == Type::Condition)
    return node.data.key == value;
  if (node.data.type == Type::Action)
    return true;

  const bool stop_on = node.data.type == Type::Selector;
  for (int child = node.first_child; child != -1; child = tree[child].right_sibling)
    if (evaluate(tree, child, value) == stop_on)
      return stop_on;

  return !stop_on;
}

// A selector with one failing "condition -> action" sequence per branch, like
// the PDD tree when nothing matches: every branch is visited.
static TreeNode * build_tree(int branches)
{
  TreeNode * root = new TreeNode(Data{Type::Selector, 0});
  for (int i = 0; i < branches; ++i)
  {
    TreeNode * sequence = new TreeNode(Data{Type::Sequence, 0});
    sequence->append_child(new TreeNode(Data{Type::Condition, i}));
    sequence->append_child(new TreeNode(Data{Type::Action, 0}));
    root->append_child(sequence);
  }
  return root;
}

static FlatTree build_flat(int branches)
{
  FlatTree tree;
  tree.append(FlatNode{Data{Type::Selector, 0}, branches > 0 ? 1 : -1, -1});
  for (int i = 0; i < branches; ++i)
  {
    const int sequence = 1 + i * 3;
    const int next = i + 1 < branches ? sequence + 3 : -1;
    tree.append(FlatNode{Data{Type::Sequence, 0}, sequence + 1, next});
    tree.append(FlatNode{Data{Type::Condition, i}, -1, sequence + 2});
    tree.append(FlatNode{Data{Type::Action, 0}, -1, -1});
  }
  return tree;
}

template <class Walk>
static double median_ns(Walk walk)
{
  Designar::DynArray<double> samples;
  Designar::Now now(Designar::Now::Precision::NANOSECONDS);
  int matches = 0;

  for (int sample = 0; sample < SAMPLES; ++sample)
  {
    now.start();
    for (int run = 0; run < RUNS_PER_SAMPLE; ++run)
      matches += walk(input);
    samples.append(now.elapsed() / RUNS_PER_SAMPLE);
  }

  if (matches != 0)
    std::cout << "unexpected match\n";

  Designar::insertion_sort(samples);
  return samples[SAMPLES / 2];
}

static void measure(int branches)
{
  TreeNode * root = build_tree(branches);
  const FlatTree flat = build_flat(branches);

  const double tree_ns = median_ns([&](int value) { return evaluate(root, value); });
  const double flat_ns = median_ns([&](int value) { return evaluate(flat, 0, value); });

  std::cout << 1 + branches * 3 << " nodes: MTreeNode " << tree_ns
            << " ns, DynArray " << flat_ns << " ns\n";

  TreeNode::destroy_tree(root);
}

int main()
{
  measure(5);
  measure(50);
  return 0;
}
