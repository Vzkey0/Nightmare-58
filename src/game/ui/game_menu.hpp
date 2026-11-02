#pragma once

#include <godot_cpp/classes/control.hpp>
#include <godot_cpp/classes/input_event.hpp>
#include <godot_cpp/classes/label.hpp>
#include <godot_cpp/classes/v_box_container.hpp>

#include <core/menu_stack.hpp>
#include <core/progression/inventory.hpp>

class PlayerController;

// The chapel and inventory screens. Runs only on input, so an open menu costs nothing per frame.
class GameMenu : public godot::Control
{
  GDCLASS(GameMenu, godot::Control)

protected:
  static void _bind_methods() {}

public:
  void _ready() override;
  void _unhandled_input(const godot::Ref<godot::InputEvent> & event) override;

  void bind(PlayerController * value) { player = value; }
  bool is_open() const { return menu.is_open(); }

  // Also true on the tick a menu closes: the key that closed it must not reach the player too.
  bool holds_input() const;
  void open(MenuScreen screen);

private:
  void accept();
  void go_back();
  void close();
  void refresh();
  void show_chapel();
  void show_stats();
  void show_inventory();
  void add_row(const godot::String & text, bool selected);
  int row_count() const;

  MenuStack menu;
  InventorySort sort_mode = InventorySort::Recent;
  uint64_t closed_tick = 0;
  PlayerController * player = nullptr;
  godot::Label * title = nullptr;
  godot::Label * detail = nullptr;
  godot::VBoxContainer * rows = nullptr;
};
