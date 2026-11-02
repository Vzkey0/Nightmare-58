#pragma once

#include <godot_cpp/classes/control.hpp>
#include <godot_cpp/classes/grid_container.hpp>
#include <godot_cpp/classes/input_event.hpp>
#include <godot_cpp/classes/label.hpp>
#include <godot_cpp/classes/v_box_container.hpp>

#include <core/menu_stack.hpp>
#include <core/progression/inventory.hpp>

class MetalPlate;
class ItemSlot;
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
  static constexpr int GRID_COLUMNS = 5;
  // ponytail: three rows hold the whole catalog; a longer one needs a scrolling grid.
  static constexpr int GRID_SLOTS = 15;

  void accept();
  void go_back();
  void close();
  void refresh();
  void show_chapel();
  void show_stats();
  void show_inventory();
  void show_pause();
  void show_options();
  void accept_pause();
  void leave_to_title();
  bool handle_options_input(const godot::Ref<godot::InputEvent> & event);
  void show_tabs(bool visible);
  void add_row(const godot::String & text, bool selected, const godot::String & value = godot::String());
  void paint_tab(godot::Label * label, MetalPlate * plate, bool active);
  void move_in_grid(int step);
  void move_row(int step);
  void adjust_option(int direction);
  void place_sheet();
  bool handle_inventory_input(const godot::Ref<godot::InputEvent> & event);
  bool handle_mouse(const godot::Ref<godot::InputEvent> & event);
  void click(const godot::Vector2 & at, int entry);
  int entry_at(const godot::Vector2 & at) const;
  void next_sort();
  Designar::DynArray<ItemStack> tab_stacks() const;
  int row_count() const;

  MenuStack menu;
  InventorySort sort_mode = InventorySort::Recent;
  ItemKind tab = ItemKind::Consumable;
  uint64_t closed_tick = 0;
  PlayerController * player = nullptr;
  godot::Control * sheet = nullptr;
  godot::Label * title = nullptr;
  godot::Label * tab_left = nullptr;
  godot::Label * tab_right = nullptr;
  MetalPlate * tab_left_plate = nullptr;
  MetalPlate * tab_right_plate = nullptr;
  godot::Label * item_name = nullptr;
  godot::Label * detail = nullptr;
  godot::Label * hints = nullptr;
  godot::Label * hint_back = nullptr;
  godot::VBoxContainer * rows = nullptr;
  godot::GridContainer * grid = nullptr;
  ItemSlot * slots[GRID_SLOTS] = {};
};
