#include "game_menu.hpp"
#include "metal_plate.hpp"
#include "game_settings.hpp"
#include "item_slot.hpp"
#include "ui_palette.hpp"
#include <game/player/player_controller.hpp>

#include <godot_cpp/classes/engine.hpp>
#include <godot_cpp/classes/input.hpp>
#include <godot_cpp/classes/input_event_mouse_button.hpp>
#include <godot_cpp/classes/scene_tree.hpp>
#include <godot_cpp/classes/viewport.hpp>
#include <godot_cpp/variant/string.hpp>

using namespace godot;

namespace
{
constexpr float SHEET_WIDTH = 640.f;
constexpr float DESIGN_HEIGHT = 1080.f; // Sheet measures are for this height, as in the HUD.
constexpr float SLOT_SIZE = 106.f;
constexpr int NO_ENTRY = -1;
const char * const TITLE_SCENE = "res://scenes/title.tscn";
constexpr int PAUSE_ROWS = 3;
enum PauseRow { ROW_RESUME, ROW_OPTIONS, ROW_TO_TITLE };

constexpr int CHAPEL_ROWS = 3;
enum ChapelRow { ROW_LEVEL_UP, ROW_INVENTORY, ROW_LEAVE };

const char * const STAT_NAMES[STAT_COUNT] = {
  "Vida máxima", "Recuperación de stamina", "Regeneración de vida", "Velocidad al correr", "Cadencia de ataque", "Poder de ataque",
};

const char * const SORT_NAMES[INVENTORY_SORTS] = {"recientes", "tipo", "valor"};

String text(const char * value)
{
  return String::utf8(value);
}
}

void GameMenu::_ready()
{
  // A paused tree still has to hear the menu that resumes it.
  set_process_mode(PROCESS_MODE_ALWAYS);
  sheet = get_node<Control>("Sheet");
  title = get_node<Label>("Sheet/Title");
  tab_left = get_node<Label>("Sheet/TabLeft");
  tab_right = get_node<Label>("Sheet/TabRight");
  tab_left_plate = get_node<MetalPlate>("Sheet/TabLeft/Plate");
  tab_right_plate = get_node<MetalPlate>("Sheet/TabRight/Plate");
  item_name = get_node<Label>("Sheet/ItemName");
  detail = get_node<Label>("Sheet/Detail");
  hints = get_node<Label>("Sheet/Hints");
  hint_back = get_node<Label>("Sheet/HintBack");
  rows = get_node<VBoxContainer>("Sheet/Rows");
  grid = get_node<GridContainer>("Sheet/Grid");
  for (ItemSlot *& slot : slots)
  {
    slot = memnew(ItemSlot);
    slot->set_custom_minimum_size(Vector2(SLOT_SIZE, SLOT_SIZE));
    slot->set_mouse_filter(MOUSE_FILTER_IGNORE);
    grid->add_child(slot);
  }
  set_visible(false);
}

void GameMenu::open(MenuScreen screen)
{
  menu.close();
  menu.open(screen);
  set_visible(true);
  get_tree()->set_pause(screen == MenuScreen::Pause);
  Input::get_singleton()->set_mouse_mode(Input::MOUSE_MODE_VISIBLE);
  place_sheet();
  refresh();
}

void GameMenu::close()
{
  menu.close();
  set_visible(false);
  get_tree()->set_pause(false);
  Input::get_singleton()->set_mouse_mode(Input::MOUSE_MODE_CAPTURED);
  closed_tick = Engine::get_singleton()->get_physics_frames();
}

bool GameMenu::holds_input() const
{
  return menu.is_open() || Engine::get_singleton()->get_physics_frames() <= closed_tick + 1;
}

void GameMenu::place_sheet()
{
  const Vector2 window = get_viewport_rect().size;
  const float scale = window.y / DESIGN_HEIGHT;
  sheet->set_scale(Vector2(scale, scale));
  sheet->set_position(Vector2(window.x - SHEET_WIDTH * scale, 0.f));
}

void GameMenu::go_back()
{
  menu.back();
  if (menu.is_open())
    refresh();
  else
    close();
}

void GameMenu::_unhandled_input(const Ref<InputEvent> & event)
{
  if (!menu.is_open())
    return;

  if (handle_mouse(event))
  {
    get_viewport()->set_input_as_handled();
    return;
  }

  if (event->is_action_pressed("ui_cancel") || event->is_action_pressed("pause"))
    go_back();
  else if (event->is_action_pressed("inventory"))
    close();
  else if (menu.screen() == MenuScreen::Inventory && handle_inventory_input(event))
    refresh();
  else if (menu.screen() == MenuScreen::Options && handle_options_input(event))
    ;
  else if (event->is_action_pressed("ui_accept") || event->is_action_pressed("interact"))
    accept();
  else if (event->is_action_pressed("ui_up") || event->is_action_pressed("move_forward"))
    move_row(-1);
  else if (event->is_action_pressed("ui_down") || event->is_action_pressed("move_back"))
    move_row(1);
  else
    return; // Whatever else was pressed, the player's camera may still want it.

  get_viewport()->set_input_as_handled();
}

bool GameMenu::handle_inventory_input(const Ref<InputEvent> & event)
{
  if (event->is_action_pressed("ui_left") || event->is_action_pressed("move_left"))
    move_in_grid(-1);
  else if (event->is_action_pressed("ui_right") || event->is_action_pressed("move_right"))
    move_in_grid(1);
  else if (event->is_action_pressed("ui_up") || event->is_action_pressed("move_forward"))
    move_in_grid(-GRID_COLUMNS);
  else if (event->is_action_pressed("ui_down") || event->is_action_pressed("move_back"))
    move_in_grid(GRID_COLUMNS);
  else if (event->is_action_pressed("menu_prev") || event->is_action_pressed("menu_next"))
    tab = tab == ItemKind::Consumable ? ItemKind::Collectible : ItemKind::Consumable;
  else if (event->is_action_pressed("use_item"))
    next_sort();
  else
    return false;
  return true;
}

bool GameMenu::handle_options_input(const Ref<InputEvent> & event)
{
  if (event->is_action_pressed("ui_left") || event->is_action_pressed("move_left"))
    adjust_option(-1);
  else if (event->is_action_pressed("ui_right") || event->is_action_pressed("move_right"))
    adjust_option(1);
  else
    return false;
  return true;
}

void GameMenu::adjust_option(int direction)
{
  GameSettings::step(menu.cursor(), direction);
  MetalPlate::set_row_value(rows, menu.cursor(), GameSettings::row_value(menu.cursor()));
}

// Rows stay alive here, so the one left and the one reached can play their tween.
void GameMenu::move_row(int step)
{
  if (menu.screen() == MenuScreen::Inventory)
  {
    menu.move_cursor(step, row_count());
    refresh();
    return;
  }
  MetalPlate::select_row(rows, menu.cursor(), false);
  menu.move_cursor(step, row_count());
  MetalPlate::select_row(rows, menu.cursor(), true);
}

void GameMenu::next_sort()
{
  sort_mode = static_cast<InventorySort>((static_cast<int>(sort_mode) + 1) % INVENTORY_SORTS);
}

bool GameMenu::handle_mouse(const Ref<InputEvent> & event)
{
  const InputEventMouse * mouse = Object::cast_to<InputEventMouse>(*event);
  if (mouse == nullptr)
    return false;

  const Vector2 at = mouse->get_position();
  const int entry = entry_at(at);
  if (entry != NO_ENTRY && entry != menu.cursor())
    move_row(entry - menu.cursor());

  const InputEventMouseButton * button = Object::cast_to<InputEventMouseButton>(*event);
  if (button == nullptr || !button->is_pressed())
    return true;
  if (button->get_button_index() == MOUSE_BUTTON_RIGHT)
    go_back();
  else if (button->get_button_index() == MOUSE_BUTTON_LEFT)
    click(at, entry);
  return true;
}

void GameMenu::click(const Vector2 & at, int entry)
{
  const bool inventory = menu.screen() == MenuScreen::Inventory;
  if (hint_back->get_global_rect().has_point(at))
    go_back();
  else if (inventory && hints->get_global_rect().has_point(at))
    next_sort();
  else if (inventory && tab_left->get_global_rect().has_point(at))
    tab = ItemKind::Consumable;
  else if (inventory && tab_right->get_global_rect().has_point(at))
    tab = ItemKind::Collectible;
  else if (menu.screen() == MenuScreen::Options)
  {
    const int direction = entry == NO_ENTRY ? 0 : GameSettings::click_direction(Object::cast_to<Control>(rows->get_child(entry))->get_global_rect(), at.x);
    if (direction != 0)
      adjust_option(direction);
    return;
  }
  else if (!inventory && entry != NO_ENTRY)
  {
    accept();
    return;
  }
  else
    return;

  if (menu.is_open())
    refresh();
}

int GameMenu::entry_at(const Vector2 & at) const
{
  if (menu.screen() == MenuScreen::Inventory)
  {
    const int count = row_count();
    for (int i = 0; i < count && i < GRID_SLOTS; ++i)
      if (slots[i]->get_global_rect().has_point(at))
        return i;
    return NO_ENTRY;
  }

  for (int i = 0; i < rows->get_child_count(); ++i)
    if (Object::cast_to<Control>(rows->get_child(i))->get_global_rect().has_point(at))
      return i;
  return NO_ENTRY;
}

// A grid stops at its edges: wrapping around a half-full row lands on an unrelated slot.
void GameMenu::move_in_grid(int step)
{
  const int count = row_count();
  const int target = menu.cursor() + step;
  if (target >= 0 && target < count)
    menu.move_cursor(step, count);
}

Designar::DynArray<ItemStack> GameMenu::tab_stacks() const
{
  const ItemCatalog & catalog = ItemCatalog::instance();
  const Designar::DynArray<ItemStack> stacks = player->progress().inventory().sorted(sort_mode);
  Designar::DynArray<ItemStack> shown;
  for (int i = 0; i < static_cast<int>(stacks.size()); ++i)
    if (catalog[stacks[i].item].kind == tab)
      shown.append(stacks[i]);
  return shown;
}

int GameMenu::row_count() const
{
  switch (menu.screen())
  {
    case MenuScreen::Chapel:
      return CHAPEL_ROWS;
    case MenuScreen::Stats:
      return STAT_COUNT;
    case MenuScreen::Pause:
      return PAUSE_ROWS;
    case MenuScreen::Options:
      return GameSettings::ROWS;
    default:
      return static_cast<int>(tab_stacks().size());
  }
}

void GameMenu::accept()
{
  switch (menu.screen())
  {
    case MenuScreen::Chapel:
      if (menu.cursor() == ROW_LEVEL_UP)
        menu.open(MenuScreen::Stats);
      else if (menu.cursor() == ROW_INVENTORY)
        menu.open(MenuScreen::Inventory);
      else
      {
        close();
        return;
      }
      break;
    case MenuScreen::Stats:
      player->raise_stat(static_cast<Stat>(menu.cursor()));
      break;
    case MenuScreen::Pause:
      accept_pause();
      return;
    case MenuScreen::Options:
      return;
    default:
      break;
  }
  refresh();
}

void GameMenu::refresh()
{
  for (int i = rows->get_child_count() - 1; i >= 0; --i)
  {
    Node * row = rows->get_child(i);
    rows->remove_child(row);
    row->queue_free();
  }

  const bool inventory = menu.screen() == MenuScreen::Inventory;
  rows->set_visible(!inventory);
  grid->set_visible(inventory);
  show_tabs(inventory);
  item_name->set_text(String());

  switch (menu.screen())
  {
    case MenuScreen::Chapel:
      show_chapel();
      break;
    case MenuScreen::Stats:
      show_stats();
      break;
    case MenuScreen::Pause:
      show_pause();
      break;
    case MenuScreen::Options:
      show_options();
      break;
    default:
      show_inventory();
      break;
  }
}

void GameMenu::show_tabs(bool visible)
{
  tab_left->set_visible(visible);
  tab_right->set_visible(visible);
  tab_left->set_text("Z   Consumibles");
  tab_right->set_text("C   Coleccionables");
  paint_tab(tab_left, tab_left_plate, tab == ItemKind::Consumable);
  paint_tab(tab_right, tab_right_plate, tab == ItemKind::Collectible);
}

void GameMenu::paint_tab(Label * label, MetalPlate * plate, bool active)
{
  plate->set_style(active ? MetalPlate::STYLE_BRIGHT : MetalPlate::STYLE_PLATE);
  label->add_theme_color_override("font_color", active ? UiPalette::ON_BRIGHT : UiPalette::MUTED);
}

void GameMenu::add_row(const String & value, bool selected, const String & right)
{
  MetalPlate::add_row(rows, value, selected, right);
}

void GameMenu::accept_pause()
{
  if (menu.cursor() == ROW_RESUME)
    close();
  else if (menu.cursor() == ROW_TO_TITLE)
    leave_to_title();
  else
  {
    menu.open(MenuScreen::Options);
    refresh();
  }
}

// Everything that matters was saved when it happened, so there is nothing to write here.
void GameMenu::leave_to_title()
{
  menu.close();
  get_tree()->set_pause(false);
  // Deferred: changing now takes this node out of the tree while it still handles the key.
  get_tree()->call_deferred("change_scene_to_file", TITLE_SCENE);
}

void GameMenu::show_pause()
{
  title->set_text("Pausa");
  detail->set_text(String());
  add_row("Continuar", menu.cursor() == ROW_RESUME);
  add_row("Opciones", menu.cursor() == ROW_OPTIONS);
  add_row("Salir al inicio", menu.cursor() == ROW_TO_TITLE);
  hints->set_text("E  aceptar");
  hint_back->set_text("Esc  continuar");
}

void GameMenu::show_options()
{
  title->set_text("Opciones");
  detail->set_text(String());
  for (int row = 0; row < GameSettings::ROWS; ++row)
    add_row(GameSettings::row_name(row), menu.cursor() == row, GameSettings::row_value(row));
  hints->set_text("A / D  ajustar");
  hint_back->set_text("Esc  volver");
}

void GameMenu::show_chapel()
{
  const PlayerProgress & progress = player->progress();
  title->set_text(vformat(text("Capilla  ·  día %d"), progress.day()));
  detail->set_text(text("El lugar sigue a salvo. Los enemigos volvieron a su sitio."));
  add_row("Subir de nivel", menu.cursor() == ROW_LEVEL_UP);
  add_row("Inventario", menu.cursor() == ROW_INVENTORY);
  add_row("Salir", menu.cursor() == ROW_LEAVE);
  hints->set_text("E  aceptar");
  hint_back->set_text("Esc  salir");
}

void GameMenu::show_stats()
{
  const PlayerProgress & progress = player->progress();
  const PlayerStats & stats = progress.stats();
  title->set_text("Subir de nivel");
  detail->set_text(vformat(text("Costo: %d lochas  ·  Tienes: %d"), stats.next_cost(), progress.lochas()));
  for (int stat = 0; stat < STAT_COUNT; ++stat)
    add_row(text(STAT_NAMES[stat]), menu.cursor() == stat, vformat("%d / %d", stats.level(static_cast<Stat>(stat)), PlayerStats::MAX_LEVEL));
  hints->set_text("E  subir");
  hint_back->set_text("Esc  volver");
}

void GameMenu::show_inventory()
{
  const ItemCatalog & catalog = ItemCatalog::instance();
  const Designar::DynArray<ItemStack> stacks = tab_stacks();
  const int count = static_cast<int>(stacks.size());
  menu.keep_cursor_within(count);

  title->set_text("Inventario");
  for (int i = 0; i < GRID_SLOTS; ++i)
  {
    const bool filled = i < count;
    slots[i]->show_item(filled ? stacks[i].item : NO_ITEM, filled ? stacks[i].count : 0, filled && i == menu.cursor());
  }
  if (count > 0)
  {
    const Item & item = catalog[stacks[menu.cursor()].item];
    item_name->set_text(text(item.name));
    detail->set_text(text(item.description));
  }
  else
    detail->set_text(text("No llevas nada aquí."));
  hints->set_text(vformat("R  ordenar: %s", text(SORT_NAMES[static_cast<int>(sort_mode)])));
  hint_back->set_text("Esc  volver");
}
