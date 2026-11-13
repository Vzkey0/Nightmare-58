#pragma once

#include <godot_cpp/classes/control.hpp>
#include <godot_cpp/classes/environment.hpp>
#include <godot_cpp/classes/tween.hpp>
#include <godot_cpp/classes/grid_container.hpp>
#include <godot_cpp/classes/input_event.hpp>
#include <godot_cpp/classes/label.hpp>
#include <godot_cpp/classes/v_box_container.hpp>

#include <core/menu_stack.hpp>
#include <core/progression/inventory.hpp>

class FacetPlate;
class KeyButton;
class SkillTreeView;
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
  void rest();
  void go_back();
  void close();
  void refresh();
  void show_chapel();
  void show_stats();
  void show_inventory();
  void show_pause();
  void show_options();
  void show_shop();
  void show_shop_buy();
  void show_shop_sell();
  void accept_shop();
  void show_machete();
  void place_detail();
  godot::String shop_rate() const;
  Designar::DynArray<ItemStack> sellable() const;
  void accept_pause();
  void leave_to_title();
  bool handle_options_input(const godot::Ref<godot::InputEvent> & event);
  void show_tabs(bool visible);
  void add_row(const godot::String & text, bool selected, const godot::String & value = godot::String());
  void paint_tab(godot::Label * label, FacetPlate * plate, bool active);
  void hover_tab(godot::Label * label, bool on);
  void next_tab(int step);
  void show_tab(ItemKind kind);
  void move_in_grid(int step);
  void move_row(int step);
  void adjust_option(int direction);
  void place_sheet();
  bool tree_screen() const;
  bool handle_tree_input(const godot::Ref<godot::InputEvent> & event);
  void move_on_tree(const godot::Vector2 & direction);
  void accept_stat();
  void accept_skill();
  void show_skill_status(int state, const godot::String & action, int price);
  void slide_sheet(bool in);
  void dim_world(bool dim);
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
  bool rested = false;
  PlayerController * player = nullptr;
  godot::Vector2 sheet_rest;
  godot::Ref<godot::Tween> sheet_tween;
  godot::Ref<godot::Tween> world_tween;
  godot::Ref<godot::Environment> world;
  float world_saturation = 1.f;
  float world_brightness = 1.f;
  godot::Control * sheet = nullptr;
  godot::Control * shade = nullptr;
  SkillTreeView * board = nullptr;
  godot::Vector2 board_rest;
  godot::Ref<godot::Tween> board_tween;
  godot::Label * title = nullptr;
  godot::Label * subtitle = nullptr; // The day and the rate under a chapel's or a shop's title.
  KeyButton * tab_prev = nullptr;
  KeyButton * tab_next = nullptr;
  godot::Label * tab_left = nullptr;
  godot::Label * tab_middle = nullptr;
  godot::Label * tab_right = nullptr;
  FacetPlate * tab_left_plate = nullptr;
  FacetPlate * tab_middle_plate = nullptr;
  FacetPlate * tab_right_plate = nullptr;
  godot::Control * title_icon = nullptr;
  godot::Control * stencil = nullptr;
  godot::Label * item_name = nullptr;
  godot::Label * detail = nullptr;
  KeyButton * hints = nullptr;
  KeyButton * hint_back = nullptr;
  godot::VBoxContainer * rows = nullptr;
  godot::GridContainer * grid = nullptr;
  ItemSlot * slots[GRID_SLOTS] = {};
};
