#include "title_screen.hpp"
#include "facet_plate.hpp"
#include "key_button.hpp"
#include "game_settings.hpp"
#include "ui_sounds.hpp"
#include <game/world/save_file.hpp>

#include <godot_cpp/classes/animation_player.hpp>
#include <godot_cpp/classes/input.hpp>
#include <godot_cpp/classes/input_event_mouse_button.hpp>
#include <godot_cpp/classes/property_tweener.hpp>
#include <godot_cpp/classes/tween.hpp>
#include <godot_cpp/classes/scene_tree.hpp>
#include <godot_cpp/classes/viewport.hpp>
#include <godot_cpp/core/math.hpp>

#include <core/progression/player_progress.hpp>

using namespace godot;

namespace
{
const char * const GAME_SCENE = "res://scenes/avenue.tscn";
const Vector2 STAGE_SIZE(1920.f, 1080.f);
constexpr int NO_ROW = -1;
constexpr float FADE_TIME = 2.2f;
constexpr float HINT_HEIGHT = 46.f;
const char * const HINT_GAP = "      ";
// The sheet comes in from the right once the street has faded up, as the chapel's does.
const Vector2 SHEET_ENTRY(520.f, 120.f);
constexpr float SHEET_ENTRY_TILT = 0.16f;
constexpr float SHEET_REST_TILT = -0.022f;
constexpr float SHEET_DELAY = 0.5f;
constexpr float SHEET_IN_TIME = 0.5f;
constexpr float DISABLED_ALPHA = 0.4f;

// A close-up with the hero left of center, leaving the right of the frame to the menu.
const Vector3 CAMERA_START(-0.5f, 1.5f, 32.15f);
const Vector3 CAMERA_AIM(0.42f, 1.3f, 30.f);
constexpr float CAMERA_PUSH = 0.008f; // Metres per second towards the hero.
constexpr float CAMERA_PUSH_LIMIT = 0.3f;
constexpr float CAMERA_SWAY = 0.012f;

String text(const char * value)
{
  return String::utf8(value);
}
}

void TitleScreen::_ready()
{
  GameSettings::load();
  stage = get_node<Control>("Stage");
  sheet = get_node<Control>("Stage/Sheet");
  rows = get_node<VBoxContainer>("Stage/Sheet/Rows");
  heading = get_node<Label>("Stage/Sheet/Heading");
  hints = get_node<HBoxContainer>("Stage/Sheet/Hints");
  name_box = get_node<Control>("Stage/Sheet/NameBox");
  name_field = get_node<LineEdit>("Stage/Sheet/NameBox/Field");
  fade = get_node<ColorRect>("Fade");
  camera = get_node<Camera3D>("../../Camera");

  name_field->connect("text_submitted", callable_mp(this, &TitleScreen::on_name_submitted));
  Object::cast_to<AnimationPlayer>(get_node<Node>("../../Hero")->find_child("AnimationPlayer", true, false))->play("idle");
  Input::get_singleton()->set_mouse_mode(Input::MOUSE_MODE_VISIBLE);

  count_saved_games();
  menu.open(MenuScreen::Title);
  place_stage();
  refresh();
  slide_sheet_in();
}

void TitleScreen::slide_sheet_in()
{
  const Vector2 rest = sheet->get_position();
  sheet->set_position(rest + SHEET_ENTRY);
  sheet->set_rotation(SHEET_ENTRY_TILT);
  sheet->set_modulate(Color(1.f, 1.f, 1.f, 0.f));
  Ref<Tween> tween = create_tween()->set_parallel();
  tween->tween_property(sheet, "position", rest, SHEET_IN_TIME)->set_delay(SHEET_DELAY)->set_trans(Tween::TRANS_BACK)->set_ease(Tween::EASE_OUT);
  tween->tween_property(sheet, "rotation", SHEET_REST_TILT, SHEET_IN_TIME)->set_delay(SHEET_DELAY)->set_trans(Tween::TRANS_BACK)->set_ease(Tween::EASE_OUT);
  tween->tween_property(sheet, "modulate:a", 1.f, SHEET_IN_TIME * 0.4f)->set_delay(SHEET_DELAY);
}

void TitleScreen::set_hints(const String & value)
{
  for (int i = hints->get_child_count() - 1; i >= 0; --i)
  {
    Node * hint = hints->get_child(i);
    hints->remove_child(hint);
    hint->queue_free();
  }
  const PackedStringArray keys = value.split(HINT_GAP, false);
  for (const String & key : keys)
  {
    KeyButton * hint = memnew(KeyButton);
    hints->add_child(hint);
    hint->set_text(key.strip_edges());
    hint->set_custom_minimum_size(Vector2(hint->plate_rect().size.x, HINT_HEIGHT));
  }
}

// A plaque does what its key does, and goes down as the key would.
bool TitleScreen::click_hint(const Vector2 & at)
{
  for (int i = 0; i < hints->get_child_count(); ++i)
  {
    KeyButton * hint = Object::cast_to<KeyButton>(hints->get_child(i));
    if (hint == nullptr || !hint->get_global_transform().xform(hint->plate_rect()).has_point(at))
      continue;
    hint->press();
    const String key = hint->get_text().get_slice("  ", 0);
    if (key == "Esc")
      go_back();
    else if (key == "R")
      delete_slot();
    else if (key == "Enter")
      on_name_submitted(name_field->get_text());
    else if (key == "E")
      accept();
    return true;
  }
  return false;
}

void TitleScreen::count_saved_games()
{
  any_saved = false;
  for (int slot = 0; slot < SaveFile::SLOTS; ++slot)
    any_saved = any_saved || SaveFile::exists(slot);
}

void TitleScreen::_process(double delta)
{
  clock += delta;
  place_stage();
  move_camera(static_cast<float>(clock));
  fade->set_modulate(Color(1.f, 1.f, 1.f, 1.f - MIN(static_cast<float>(clock) / FADE_TIME, 1.f)));
}

// Held against the right edge, so a wide window only shows more of the scene.
void TitleScreen::place_stage()
{
  const Vector2 window = get_viewport_rect().size;
  const float scale = window.y / STAGE_SIZE.y;
  stage->set_scale(Vector2(scale, scale));
  stage->set_position(Vector2(window.x - STAGE_SIZE.x * scale, 0.f));
}

void TitleScreen::move_camera(float time)
{
  const float push = MIN(time * CAMERA_PUSH, CAMERA_PUSH_LIMIT);
  const Vector3 sway(Math::sin(time * 0.17f) * CAMERA_SWAY, Math::sin(time * 0.11f) * CAMERA_SWAY * 0.5f, -push);
  camera->look_at_from_position(CAMERA_START + sway, CAMERA_AIM);
}

int TitleScreen::row_count() const
{
  switch (menu.screen())
  {
    case MenuScreen::Slots:
      return SaveFile::SLOTS;
    case MenuScreen::Confirm:
      return 2;
    case MenuScreen::Options:
      return GameSettings::ROWS;
    case MenuScreen::Name:
      return 0;
    default:
      return MAIN_ROWS;
  }
}

void TitleScreen::move_cursor(int step)
{
  const int from = menu.cursor();
  FacetPlate::select_row(rows, menu.cursor(), false);
  menu.move_cursor(step, row_count());
  if (menu.screen() == MenuScreen::Title && menu.cursor() == ROW_CONTINUE && !any_saved)
    menu.move_cursor(step, row_count());
  FacetPlate::select_row(rows, menu.cursor(), true);
  if (menu.cursor() != from)
    UiSounds::play(this, "Move");
}

void TitleScreen::adjust_option(int direction)
{
  UiSounds::play(this, GameSettings::step(menu.cursor(), direction) ? "Adjust" : "Deny");
  FacetPlate::set_row_value(rows, menu.cursor(), GameSettings::row_value(menu.cursor()));
}

void TitleScreen::_unhandled_input(const Ref<InputEvent> & event)
{
  if (handle_mouse(event))
  {
    get_viewport()->set_input_as_handled();
    return;
  }

  const bool options = menu.screen() == MenuScreen::Options;
  if (event->is_action_pressed("ui_cancel"))
    go_back();
  else if (menu.screen() == MenuScreen::Name)
    return;
  else if (event->is_action_pressed("ui_accept") || event->is_action_pressed("interact"))
    accept();
  else if (event->is_action_pressed("ui_up") || event->is_action_pressed("move_forward"))
    move_cursor(-1);
  else if (event->is_action_pressed("ui_down") || event->is_action_pressed("move_back"))
    move_cursor(1);
  else if (options && (event->is_action_pressed("ui_left") || event->is_action_pressed("move_left")))
    adjust_option(-1);
  else if (options && (event->is_action_pressed("ui_right") || event->is_action_pressed("move_right")))
    adjust_option(1);
  else if (menu.screen() == MenuScreen::Slots && event->is_action_pressed("use_item"))
    delete_slot();
  else
    return;

  get_viewport()->set_input_as_handled();
}

bool TitleScreen::handle_mouse(const Ref<InputEvent> & event)
{
  const InputEventMouse * mouse = Object::cast_to<InputEventMouse>(*event);
  if (mouse == nullptr)
    return false;

  const int row = row_at(mouse->get_position());
  const bool dead_row = menu.screen() == MenuScreen::Title && row == ROW_CONTINUE && !any_saved;
  if (row != NO_ROW && row != menu.cursor() && !dead_row)
    move_cursor(row - menu.cursor());
  // A hand over anything that answers a click; the plaques set their own.
  Input::get_singleton()->set_default_cursor_shape(row != NO_ROW && !dead_row ? Input::CURSOR_POINTING_HAND : Input::CURSOR_ARROW);

  const InputEventMouseButton * button = Object::cast_to<InputEventMouseButton>(*event);
  if (button == nullptr || !button->is_pressed())
    return true;
  if (button->get_button_index() == MOUSE_BUTTON_RIGHT)
    go_back();
  else if (button->get_button_index() == MOUSE_BUTTON_LEFT && click_hint(mouse->get_position()))
    return true;
  else if (button->get_button_index() == MOUSE_BUTTON_LEFT && row != NO_ROW && !dead_row)
  {
    if (menu.screen() != MenuScreen::Options)
      accept();
    else if (const int direction = GameSettings::click_direction(Object::cast_to<Control>(rows->get_child(row))->get_global_rect(), mouse->get_position().x))
      adjust_option(direction);
  }
  return true;
}

int TitleScreen::row_at(const Vector2 & at) const
{
  for (int i = 0; i < rows->get_child_count(); ++i)
    if (Object::cast_to<Control>(rows->get_child(i))->get_global_rect().has_point(at))
      return i;
  return NO_ROW;
}

void TitleScreen::go_back()
{
  if (menu.screen() == MenuScreen::Title)
    return;
  UiSounds::play(this, "Back");
  menu.back();
  refresh();
}

void TitleScreen::accept()
{
  switch (menu.screen())
  {
    case MenuScreen::Slots:
      accept_slot();
      break;
    case MenuScreen::Confirm:
      accept_confirm();
      break;
    case MenuScreen::Options:
      break;
    default:
      accept_main();
      break;
  }
}

void TitleScreen::accept_main()
{
  UiSounds::play(this, "Accept");
  switch (menu.cursor())
  {
    case ROW_CONTINUE:
      chosen_slot = SaveFile::active_slot();
      if (SaveFile::exists(chosen_slot))
        start_game();
      else
        open_slots(true);
      break;
    case ROW_NEW:
      open_slots(false);
      break;
    case ROW_LOAD:
      open_slots(true);
      break;
    case ROW_OPTIONS:
      menu.open(MenuScreen::Options);
      refresh();
      break;
    default:
      get_tree()->quit();
      break;
  }
}

void TitleScreen::open_slots(bool for_loading)
{
  loading = for_loading;
  menu.open(MenuScreen::Slots);
  refresh();
}

void TitleScreen::accept_slot()
{
  chosen_slot = menu.cursor();
  const bool taken = SaveFile::exists(chosen_slot);
  UiSounds::play(this, loading && !taken ? "Deny" : "Accept");
  if (loading && taken)
    start_game();
  else if (!loading && taken)
  {
    deleting = false;
    menu.open(MenuScreen::Confirm);
    refresh();
  }
  else if (!loading)
  {
    menu.open(MenuScreen::Name);
    refresh();
  }
}

void TitleScreen::delete_slot()
{
  chosen_slot = menu.cursor();
  if (!SaveFile::exists(chosen_slot))
  {
    UiSounds::play(this, "Deny");
    return;
  }
  UiSounds::play(this, "Accept");
  deleting = true;
  menu.open(MenuScreen::Confirm);
  refresh();
}

void TitleScreen::accept_confirm()
{
  const bool yes = menu.cursor() == 0;
  UiSounds::play(this, yes ? "Accept" : "Back");
  menu.back();
  if (yes && deleting)
  {
    SaveFile::erase(chosen_slot);
    count_saved_games();
  }
  else if (yes)
    menu.open(MenuScreen::Name);
  refresh();
}

void TitleScreen::on_name_submitted(const String & name)
{
  UiSounds::play(this, "Accept");
  PlayerProgress fresh;
  fresh.set_player_name(name.strip_edges().utf8().get_data());
  SaveFile::select(chosen_slot);
  SaveFile::write(fresh);
  enter_game();
}

void TitleScreen::start_game()
{
  SaveFile::select(chosen_slot);
  enter_game();
}

// Deferred: changing now takes this node out of the tree while it still handles the key.
void TitleScreen::enter_game()
{
  Input::get_singleton()->set_default_cursor_shape(Input::CURSOR_ARROW);
  get_tree()->call_deferred("change_scene_to_file", GAME_SCENE);
}

void TitleScreen::refresh()
{
  for (int i = rows->get_child_count() - 1; i >= 0; --i)
  {
    Node * row = rows->get_child(i);
    rows->remove_child(row);
    row->queue_free();
  }

  const bool naming = menu.screen() == MenuScreen::Name;
  name_box->set_visible(naming);
  if (naming)
    show_name();
  else if (menu.screen() == MenuScreen::Slots)
    show_slots();
  else if (menu.screen() == MenuScreen::Confirm)
    show_confirm();
  else if (menu.screen() == MenuScreen::Options)
    show_options();
  else
    show_main();
}

void TitleScreen::show_main()
{
  if (!any_saved && menu.cursor() == ROW_CONTINUE)
    menu.move_cursor(1, MAIN_ROWS);

  heading->set_text(text("Menú"));
  set_hints("E  elegir");
  const char * const names[MAIN_ROWS] = {"Continuar", "Nueva partida", "Cargar partida", "Opciones", "Salir"};
  for (int row = 0; row < MAIN_ROWS; ++row)
  {
    FacetPlate::add_row(rows, text(names[row]), menu.cursor() == row);
    if (row == ROW_CONTINUE && !any_saved)
      Object::cast_to<CanvasItem>(rows->get_child(row))->set_modulate(Color(1.f, 1.f, 1.f, DISABLED_ALPHA));
  }
}

void TitleScreen::show_slots()
{
  heading->set_text(loading ? "Cargar partida" : "Nueva partida");
  set_hints("E  elegir      R  borrar      Esc  volver");
  for (int slot = 0; slot < SaveFile::SLOTS; ++slot)
  {
    PlayerProgress game;
    const bool found = SaveFile::read_slot(slot, game);
    const String name = found ? String::utf8(game.player_name().c_str()) : text("Vacía");
    const String detail = found ? vformat(text("Día %d  ·  %d lochas"), game.day(), game.lochas()) : String();
    FacetPlate::add_row(rows, vformat("%d   %s", slot + 1, name), menu.cursor() == slot, detail);
  }
}

void TitleScreen::show_confirm()
{
  heading->set_text(deleting ? text("¿Borrar esta partida?") : text("¿Reemplazar esta partida?"));
  set_hints("E  elegir      Esc  volver");
  FacetPlate::add_row(rows, deleting ? "Borrar" : "Reemplazar", menu.cursor() == 0, text("No se puede deshacer"));
  FacetPlate::add_row(rows, "Cancelar", menu.cursor() == 1);
}

void TitleScreen::show_name()
{
  heading->set_text(text("¿Cómo te llamas?"));
  set_hints("Enter  empezar      Esc  volver");
  name_field->clear();
  name_field->grab_focus();
}

void TitleScreen::show_options()
{
  heading->set_text("Opciones");
  set_hints("A / D  ajustar      Esc  volver");
  for (int row = 0; row < GameSettings::ROWS; ++row)
    FacetPlate::add_row(rows, GameSettings::row_name(row), menu.cursor() == row, GameSettings::row_value(row));
}
