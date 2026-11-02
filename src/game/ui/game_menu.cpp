#include "game_menu.hpp"
#include <game/player/player_controller.hpp>

#include <godot_cpp/classes/engine.hpp>
#include <godot_cpp/classes/viewport.hpp>
#include <godot_cpp/variant/string.hpp>

using namespace godot;

namespace
{
const Color ROW_SELECTED(1.f, 0.86f, 0.5f);
const Color ROW_NORMAL(0.82f, 0.8f, 0.76f);

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
  title = get_node<Label>("Title");
  detail = get_node<Label>("Detail");
  rows = get_node<VBoxContainer>("Rows");
  set_visible(false);
}

void GameMenu::open(MenuScreen screen)
{
  menu.close();
  menu.open(screen);
  set_visible(true);
  refresh();
}

void GameMenu::close()
{
  menu.close();
  set_visible(false);
  closed_tick = Engine::get_singleton()->get_physics_frames();
}

bool GameMenu::holds_input() const
{
  return menu.is_open() || Engine::get_singleton()->get_physics_frames() <= closed_tick + 1;
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

  if (event->is_action_pressed("ui_cancel"))
    go_back();
  else if (event->is_action_pressed("inventory"))
    close();
  else if (event->is_action_pressed("ui_accept") || event->is_action_pressed("interact"))
    accept();
  else if (event->is_action_pressed("ui_up") || event->is_action_pressed("move_forward"))
  {
    menu.move_cursor(-1, row_count());
    refresh();
  }
  else if (event->is_action_pressed("ui_down") || event->is_action_pressed("move_back"))
  {
    menu.move_cursor(1, row_count());
    refresh();
  }
  else if (menu.screen() == MenuScreen::Inventory && (event->is_action_pressed("ui_left") || event->is_action_pressed("ui_right")))
  {
    const int step = event->is_action_pressed("ui_left") ? INVENTORY_SORTS - 1 : 1;
    sort_mode = static_cast<InventorySort>((static_cast<int>(sort_mode) + step) % INVENTORY_SORTS);
    refresh();
  }
  else
    return; // Whatever else was pressed, the player's camera may still want it.

  get_viewport()->set_input_as_handled();
}

int GameMenu::row_count() const
{
  switch (menu.screen())
  {
    case MenuScreen::Chapel:
      return CHAPEL_ROWS;
    case MenuScreen::Stats:
      return STAT_COUNT;
    default:
      return static_cast<int>(player->progress().inventory().sorted(sort_mode).size());
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

  switch (menu.screen())
  {
    case MenuScreen::Chapel:
      show_chapel();
      break;
    case MenuScreen::Stats:
      show_stats();
      break;
    default:
      show_inventory();
      break;
  }
}

void GameMenu::add_row(const String & value, bool selected)
{
  Label * row = memnew(Label);
  row->set_text(selected ? "> " + value : "  " + value);
  row->add_theme_color_override("font_color", selected ? ROW_SELECTED : ROW_NORMAL);
  row->add_theme_font_size_override("font_size", 26);
  rows->add_child(row);
}

void GameMenu::show_chapel()
{
  const PlayerProgress & progress = player->progress();
  title->set_text(vformat(text("Capilla  ·  día %d"), progress.day()));
  detail->set_text(text("El lugar sigue a salvo. Los enemigos volvieron a su sitio."));
  add_row("Subir de nivel", menu.cursor() == ROW_LEVEL_UP);
  add_row("Inventario", menu.cursor() == ROW_INVENTORY);
  add_row("Salir", menu.cursor() == ROW_LEAVE);
}

void GameMenu::show_stats()
{
  const PlayerProgress & progress = player->progress();
  const PlayerStats & stats = progress.stats();
  title->set_text("Subir de nivel");
  detail->set_text(vformat(text("Costo: %d lochas  ·  Tienes: %d"), stats.next_cost(), progress.lochas()));
  for (int stat = 0; stat < STAT_COUNT; ++stat)
    add_row(vformat("%s   %d / %d", text(STAT_NAMES[stat]), stats.level(static_cast<Stat>(stat)), PlayerStats::MAX_LEVEL), menu.cursor() == stat);
}

void GameMenu::show_inventory()
{
  const ItemCatalog & catalog = ItemCatalog::instance();
  const Designar::DynArray<ItemStack> stacks = player->progress().inventory().sorted(sort_mode);
  menu.keep_cursor_within(static_cast<int>(stacks.size()));

  title->set_text(vformat(text("Inventario  ·  por %s"), text(SORT_NAMES[static_cast<int>(sort_mode)])));
  detail->set_text(stacks.is_empty() ? text("No llevas nada.") : text(catalog[stacks[menu.cursor()].item].description));
  for (int i = 0; i < static_cast<int>(stacks.size()); ++i)
    add_row(vformat("%s  x%d", text(catalog[stacks[i].item].name), stacks[i].count), menu.cursor() == i);
}
