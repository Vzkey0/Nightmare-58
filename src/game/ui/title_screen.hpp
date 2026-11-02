#pragma once

#include <godot_cpp/classes/camera3d.hpp>
#include <godot_cpp/classes/color_rect.hpp>
#include <godot_cpp/classes/control.hpp>
#include <godot_cpp/classes/input_event.hpp>
#include <godot_cpp/classes/label.hpp>
#include <godot_cpp/classes/line_edit.hpp>
#include <godot_cpp/classes/v_box_container.hpp>

#include <core/menu_stack.hpp>

// The game's first screen: the main menu, the five saved games, the new player's name and options.
class TitleScreen : public godot::Control
{
  GDCLASS(TitleScreen, godot::Control)

protected:
  static void _bind_methods() {}

public:
  void _ready() override;
  void _process(double delta) override;
  void _unhandled_input(const godot::Ref<godot::InputEvent> & event) override;

private:
  enum MainRow { ROW_CONTINUE, ROW_NEW, ROW_LOAD, ROW_OPTIONS, ROW_QUIT, MAIN_ROWS };

  void refresh();
  void show_main();
  void show_slots();
  void show_confirm();
  void show_name();
  void show_options();
  void accept();
  void accept_main();
  void accept_slot();
  void accept_confirm();
  void go_back();
  void open_slots(bool for_loading);
  void start_game();
  void enter_game();
  void delete_slot();
  void count_saved_games();
  void on_name_submitted(const godot::String & name);
  void move_cursor(int step);
  void adjust_option(int direction);
  bool handle_mouse(const godot::Ref<godot::InputEvent> & event);
  int row_at(const godot::Vector2 & at) const;
  int row_count() const;
  void place_stage();
  void move_camera(float time);

  MenuStack menu;
  bool loading = false;   // The slots screen picks a game to load, or a place for a new one.
  bool deleting = false;  // The confirmation is for erasing a slot, or for writing over it.
  bool any_saved = false;
  int chosen_slot = 0;
  double clock = 0.0;

  godot::Control * stage = nullptr;
  godot::VBoxContainer * rows = nullptr;
  godot::Label * heading = nullptr;
  godot::Label * hints = nullptr;
  godot::Control * name_box = nullptr;
  godot::LineEdit * name_field = nullptr;
  godot::ColorRect * fade = nullptr;
  godot::Camera3D * camera = nullptr;
};
