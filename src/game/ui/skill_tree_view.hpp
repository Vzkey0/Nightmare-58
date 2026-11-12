#pragma once

#include <godot_cpp/classes/control.hpp>
#include <godot_cpp/classes/texture2d.hpp>
#include <godot_cpp/classes/tween.hpp>
#include <godot_cpp/variant/packed_string_array.hpp>

#include <core/progression/skill_tree.hpp>

// A skill tree drawn as holy cards: one gilded card per branch, each skill a medal, joined by lines.
// Positions come from SkillTree::layout, so the drawing follows the MTreeNode as it is.
class SkillTreeView : public godot::Control
{
  GDCLASS(SkillTreeView, godot::Control)

protected:
  static void _bind_methods() {}

public:
  enum State { LEARNED, AVAILABLE, LOCKED };

  struct Entry
  {
    SkillSlot slot;
    godot::String name;
    godot::String mark; // Drawn on the medal when there is no icon.
    godot::Ref<godot::Texture2D> icon;
    State state;
  };

  void _ready() override;
  void _draw() override;

  // Entries leave out the root, drawn on top joining every card; titles go one per branch.
  void show_tree(const Entry & root, const Designar::DynArray<Entry> & entries, const godot::PackedStringArray & titles, int cursor);

  // The entry nearest along a direction from the cursor, or the cursor when there is none.
  int toward(const godot::Vector2 & direction) const;
  int entry_at(const godot::Vector2 & global) const; // -1 off every medal.

  // The line into the entry fills and its medal flashes.
  void celebrate(int index);

private:
  godot::Vector2 center(int index) const; // -1 is the root.
  const Entry & entry(int index) const;
  godot::Rect2 card(int branch) const;
  void arrange();
  void draw_link(int index);
  void draw_medal(int index);
  void set_unlock(float value);
  void set_pulse(float value);

  Entry root;
  godot::Vector2 root_center;
  float medal = 84.f;
  Designar::DynArray<Entry> entries;
  Designar::DynArray<godot::Vector2> centers;
  godot::PackedStringArray titles;
  int cursor = 0;
  int celebrated = -1;
  float unlock = 1.f;
  float pulse = 0.f;
  godot::Ref<godot::Tween> unlock_tween;
  godot::Ref<godot::Texture2D> gold;
  godot::Ref<godot::Texture2D> tin;
  godot::Ref<godot::Texture2D> frame;
};
