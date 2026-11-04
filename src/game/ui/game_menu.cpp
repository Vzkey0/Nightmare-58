#include "game_menu.hpp"
#include "metal_plate.hpp"
#include "game_settings.hpp"
#include "item_slot.hpp"
#include "ui_sounds.hpp"
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

constexpr int CHAPEL_ROWS = 4;
enum ChapelRow { ROW_REST, ROW_LEVEL_UP, ROW_INVENTORY, ROW_LEAVE };

constexpr int SHOP_ROWS = 3;
enum ShopRow { ROW_BUY, ROW_SELL, ROW_SHOP_LEAVE };

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
  tab_middle = get_node<Label>("Sheet/TabMiddle");
  tab_right = get_node<Label>("Sheet/TabRight");
  tab_left_plate = get_node<MetalPlate>("Sheet/TabLeft/Plate");
  tab_middle_plate = get_node<MetalPlate>("Sheet/TabMiddle/Plate");
  tab_right_plate = get_node<MetalPlate>("Sheet/TabRight/Plate");
  title_icon = get_node<Control>("Sheet/TitleIcon");
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
  rested = false;
  // Paused at the chapel too: enemies may be near now that opening it no longer sends them back.
  get_tree()->set_pause(screen != MenuScreen::Inventory);
  Input::get_singleton()->set_mouse_mode(Input::MOUSE_MODE_VISIBLE);
  place_sheet();
  refresh();
  UiSounds::play(this, "Open");
}

void GameMenu::close()
{
  UiSounds::play(this, "Close");
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
  {
    UiSounds::play(this, "Back");
    refresh();
  }
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
  else if (event->is_action_pressed("menu_prev"))
    next_tab(-1);
  else if (event->is_action_pressed("menu_next"))
    next_tab(1);
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
  UiSounds::play(this, GameSettings::step(menu.cursor(), direction) ? "Adjust" : "Deny");
  MetalPlate::set_row_value(rows, menu.cursor(), GameSettings::row_value(menu.cursor()));
}

// Rows stay alive here, so the one left and the one reached can play their tween.
void GameMenu::move_row(int step)
{
  const int from = menu.cursor();
  if (menu.screen() == MenuScreen::Inventory)
  {
    menu.move_cursor(step, row_count());
    refresh();
  }
  else
  {
    MetalPlate::select_row(rows, menu.cursor(), false);
    menu.move_cursor(step, row_count());
    MetalPlate::select_row(rows, menu.cursor(), true);
  }
  if (menu.cursor() != from)
    UiSounds::play(this, "Move");
}

void GameMenu::next_tab(int step)
{
  show_tab(static_cast<ItemKind>((static_cast<int>(tab) + step + ITEM_KINDS) % ITEM_KINDS));
}

void GameMenu::show_tab(ItemKind kind)
{
  if (kind != tab)
    UiSounds::play(this, "Tab");
  tab = kind;
}

void GameMenu::next_sort()
{
  sort_mode = static_cast<InventorySort>((static_cast<int>(sort_mode) + 1) % INVENTORY_SORTS);
  UiSounds::play(this, "Tab");
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
    show_tab(ItemKind::Consumable);
  else if (inventory && tab_middle->get_global_rect().has_point(at))
    show_tab(ItemKind::Collectible);
  else if (inventory && tab_right->get_global_rect().has_point(at))
    show_tab(ItemKind::Weapon);
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
  if (target < 0 || target >= count)
    return;
  menu.move_cursor(step, count);
  UiSounds::play(this, "Move");
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
    case MenuScreen::Shop:
      return SHOP_ROWS;
    case MenuScreen::ShopBuy:
      return static_cast<int>(player->progress().shop_stock().size());
    case MenuScreen::ShopSell:
      return static_cast<int>(sellable().size());
    default:
      return static_cast<int>(tab_stacks().size());
  }
}

void GameMenu::accept()
{
  switch (menu.screen())
  {
    case MenuScreen::Chapel:
      if (menu.cursor() == ROW_LEAVE)
      {
        close();
        return;
      }
      if (menu.cursor() == ROW_REST)
      {
        rest();
        break;
      }
      menu.open(menu.cursor() == ROW_LEVEL_UP ? MenuScreen::Stats : MenuScreen::Inventory);
      UiSounds::play(this, "Accept");
      break;
    case MenuScreen::Stats:
      UiSounds::play(this, player->raise_stat(static_cast<Stat>(menu.cursor())) ? "Accept" : "Deny");
      break;
    case MenuScreen::Pause:
      accept_pause();
      return;
    case MenuScreen::Options:
      return;
    case MenuScreen::Shop:
      accept_shop();
      return;
    case MenuScreen::ShopBuy:
      if (row_count() > 0)
        UiSounds::play(this, player->buy(player->progress().shop_stock()[menu.cursor()]) ? "Accept" : "Deny");
      break;
    case MenuScreen::ShopSell:
      if (row_count() > 0)
        UiSounds::play(this, player->sell(sellable()[menu.cursor()].item) ? "Accept" : "Deny");
      break;
    default:
      break;
  }
  refresh();
}

void GameMenu::accept_shop()
{
  if (menu.cursor() == ROW_SHOP_LEAVE)
  {
    close();
    return;
  }
  menu.open(menu.cursor() == ROW_BUY ? MenuScreen::ShopBuy : MenuScreen::ShopSell);
  UiSounds::play(this, "Accept");
  refresh();
}

Designar::DynArray<ItemStack> GameMenu::sellable() const
{
  const ItemCatalog & catalog = ItemCatalog::instance();
  const Designar::DynArray<ItemStack> stacks = player->progress().inventory().sorted(InventorySort::Value);
  Designar::DynArray<ItemStack> shown;
  for (int i = 0; i < static_cast<int>(stacks.size()); ++i)
    if (catalog[stacks[i].item].kind == ItemKind::Collectible)
      shown.append(stacks[i]);
  return shown;
}

// Once per visit: each rest is a day of inflation, so a second press must not cost another.
void GameMenu::rest()
{
  UiSounds::play(this, rested ? "Deny" : "Accept");
  if (!rested)
    player->rest();
  rested = true;
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
  title_icon->set_visible(menu.screen() == MenuScreen::Chapel || menu.screen() == MenuScreen::Stats);
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
    case MenuScreen::Shop:
      show_shop();
      break;
    case MenuScreen::ShopBuy:
      show_shop_buy();
      break;
    case MenuScreen::ShopSell:
      show_shop_sell();
      break;
    default:
      show_inventory();
      break;
  }
}

void GameMenu::show_tabs(bool visible)
{
  tab_left->set_visible(visible);
  tab_middle->set_visible(visible);
  tab_right->set_visible(visible);
  tab_left->set_text("Z   Consumibles");
  tab_middle->set_text("Coleccionables");
  tab_right->set_text("Armas   C");
  paint_tab(tab_left, tab_left_plate, tab == ItemKind::Consumable);
  paint_tab(tab_middle, tab_middle_plate, tab == ItemKind::Collectible);
  paint_tab(tab_right, tab_right_plate, tab == ItemKind::Weapon);
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
  else
  {
    UiSounds::play(this, "Accept");
    if (menu.cursor() == ROW_TO_TITLE)
    {
      leave_to_title();
      return;
    }
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
  const Zone zone = player->chapel_zone();
  const int rate = progress.exchange_rate(zone);
  title->set_text(vformat(text("Capilla  ·  día %d  ·  tasa ×%d,%02d"), progress.day(), rate / 100, rate % 100));
  if (!rested)
    detail->set_text(text("El lugar sigue a salvo."));
  else if (progress.devalued_today(zone))
    detail->set_text(text("Pasó un día. La locha perdió valor."));
  else
    detail->set_text(text("Pasó un día. Los enemigos volvieron a su sitio."));
  add_row("Descansar", menu.cursor() == ROW_REST);
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
  detail->set_text(vformat(text("Costo: %d lochas  ·  Tienes: %d"), progress.stat_cost(player->chapel_zone()), progress.lochas()));
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

String GameMenu::shop_title() const
{
  const int rate = player->progress().exchange_rate(player->merchant_zone());
  return vformat(text("Bachaquero  ·  tasa ×%d,%02d"), rate / 100, rate % 100);
}

void GameMenu::show_shop()
{
  const PlayerProgress & progress = player->progress();
  title->set_text(shop_title());
  if (progress.markup() > 0)
    detail->set_text(vformat(text("\"Cada vez que te mueres, yo subo.\"  Recargo: +%d %%"), progress.markup()));
  else
    detail->set_text(text("\"Lo que tengo no pierde valor, pana.\""));
  add_row("Comprar", menu.cursor() == ROW_BUY);
  add_row("Vender", menu.cursor() == ROW_SELL);
  add_row("Salir", menu.cursor() == ROW_SHOP_LEAVE);
  hints->set_text("E  aceptar");
  hint_back->set_text("Esc  salir");
}

void GameMenu::show_shop_buy()
{
  const PlayerProgress & progress = player->progress();
  const ItemCatalog & catalog = ItemCatalog::instance();
  const Designar::DynArray<ItemId> stock = progress.shop_stock();
  const int count = static_cast<int>(stock.size());
  const Zone zone = player->merchant_zone();
  menu.keep_cursor_within(count);
  title->set_text(shop_title());
  for (int i = 0; i < count; ++i)
  {
    const Item & item = catalog[stock[i]];
    add_row(text(item.name), menu.cursor() == i, vformat("%d", progress.shop_price(item.value, zone)));
  }
  const String described = count > 0 ? text(catalog[stock[menu.cursor()]].description) + "\n" : String();
  detail->set_text(described + vformat(text("Tienes: %d lochas"), progress.lochas()));
  hints->set_text("E  comprar");
  hint_back->set_text("Esc  volver");
}

void GameMenu::show_shop_sell()
{
  const PlayerProgress & progress = player->progress();
  const ItemCatalog & catalog = ItemCatalog::instance();
  const Designar::DynArray<ItemStack> stacks = sellable();
  const int count = static_cast<int>(stacks.size());
  const Zone zone = player->merchant_zone();
  menu.keep_cursor_within(count);
  title->set_text(shop_title());
  for (int i = 0; i < count; ++i)
  {
    const Item & item = catalog[stacks[i].item];
    add_row(vformat("%s  x%d", text(item.name), stacks[i].count), menu.cursor() == i, vformat("%d", progress.sell_price(stacks[i].item, zone)));
  }
  if (count > 0)
    detail->set_text(vformat(text("Paga más mientras más cae la locha.\nTienes: %d lochas"), progress.lochas()));
  else
    detail->set_text(text("No tienes nada que le interese."));
  hints->set_text("E  vender");
  hint_back->set_text("Esc  volver");
}
