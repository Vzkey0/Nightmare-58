#include "game_menu.hpp"
#include "facet_plate.hpp"
#include "game_settings.hpp"
#include "item_slot.hpp"
#include "key_button.hpp"
#include "skill_tree_view.hpp"
#include "ui_sounds.hpp"
#include "ui_palette.hpp"
#include <game/player/player_controller.hpp>

#include <godot_cpp/classes/engine.hpp>
#include <godot_cpp/classes/method_tweener.hpp>
#include <godot_cpp/classes/property_tweener.hpp>
#include <godot_cpp/classes/world3d.hpp>
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

// The plaster sheet comes in from the lower right on a slant and settles almost level.
const Vector2 SHEET_ENTRY(420.f, 260.f);
const Vector2 SHEET_EXIT(360.f, 300.f);
constexpr float SHEET_ENTRY_TILT = 0.2f;
constexpr float SHEET_REST_TILT = -0.022f;
constexpr float SHEET_IN_TIME = 0.34f;
constexpr float SHEET_OUT_TIME = 0.18f;
constexpr float SHEET_FADE_TIME = 0.1f;
constexpr float SHADE_FADE_TIME = 0.25f;
constexpr float HUD_RETURN_TIME = 0.3f;

// Behind a menu that stops the game, the street goes dark and grey: the environment's own
// adjustments, which the tonemap already applies, so it costs nothing.
constexpr float DIM_SATURATION = 0.28f;
constexpr float DIM_BRIGHTNESS = 0.55f;
constexpr float DIM_TIME = 0.25f;
const char * const TITLE_SCENE = "res://scenes/title.tscn";
constexpr int PAUSE_ROWS = 3;
enum PauseRow { ROW_RESUME, ROW_OPTIONS, ROW_TO_TITLE };

constexpr int CHAPEL_ROWS = 4;
enum ChapelRow { ROW_REST, ROW_LEVEL_UP, ROW_INVENTORY, ROW_LEAVE };

constexpr int SHOP_ROWS = 4;
enum ShopRow { ROW_BUY, ROW_SELL, ROW_MACHETE, ROW_SHOP_LEAVE };

// The machete tree without its root, which is always there.
constexpr int SKILL_ROWS = MacheteSkill::COUNT - 1;

// Where Rows and Detail sit in player.tscn, and how far apart FacetPlate stacks its rows.
constexpr float ROWS_TOP = 188.f;
constexpr float DETAIL_TOP = 596.f;
constexpr float ROW_PITCH = 66.f;
constexpr float DETAIL_GAP = 28.f;
constexpr float TAB_BANDS = 9.f; // How far an active tab's bands hang below its label.

const char * const STAT_NAMES[STAT_COUNT] = {
  "Vida máxima", "Recuperación de stamina", "Regeneración de vida", "Velocidad al correr", "Cadencia de ataque", "Poder de ataque",
};

// Short enough for the head of a holy card; the detail panel gives the full name.
const char * const STAT_TITLES[STAT_COUNT] = {"Vida", "Resuello", "Regeneración", "Carrera", "Cadencia", "Poder"};
const char * const STAT_KEYS[STAT_COUNT] = {"health", "stamina", "regeneration", "speed", "attack_rate", "power"};
const char * const STAT_DETAILS[STAT_COUNT] = {
  "Más vida antes de caer.", "El aliento vuelve más rápido.", "La vida se recupera sola, poco a poco.",
  "Corres más rápido.", "Golpeas más seguido.", "Cada golpe pega más fuerte.",
};
const char * const NUMERALS[] = {"I", "II", "III", "IV", "V"};
const char * const STAT_GROUP_TITLES[STAT_GROUPS] = {"Cuerpo", "Aliento", "Fuerza"};

// The skill board sits left of the sheet, in the same design units.
constexpr float BOARD_MARGIN = 44.f;
constexpr float BOARD_TOP = 70.f;
constexpr float BOARD_BOTTOM = 60.f;
const Vector2 BOARD_ENTRY(-120.f, 0.f);
constexpr float BOARD_IN_TIME = 0.3f;
// With the board open, the sheet is its detail panel: name and text under the status strip.
constexpr float TREE_NAME_TOP = 274.f;
constexpr float TREE_DETAIL_TOP = 326.f;
constexpr float ITEM_NAME_TOP = 548.f;

const char * const SORT_NAMES[INVENTORY_SORTS] = {"recientes", "tipo", "valor"};

// Outfits share the right tab with the machete: both are what the player carries on.
constexpr int INVENTORY_TABS = 3;

ItemKind tab_of(ItemKind kind)
{
  return kind == ItemKind::Outfit ? ItemKind::Weapon : kind;
}

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
  shade = get_node<Control>("Shade");
  title = get_node<Label>("Sheet/Title");
  subtitle = get_node<Label>("Sheet/Subtitle");
  tab_prev = get_node<KeyButton>("Sheet/TabPrev");
  tab_next = get_node<KeyButton>("Sheet/TabNext");
  tab_left = get_node<Label>("Sheet/TabLeft");
  tab_middle = get_node<Label>("Sheet/TabMiddle");
  tab_right = get_node<Label>("Sheet/TabRight");
  tab_left_plate = get_node<FacetPlate>("Sheet/TabLeft/Plate");
  tab_middle_plate = get_node<FacetPlate>("Sheet/TabMiddle/Plate");
  tab_right_plate = get_node<FacetPlate>("Sheet/TabRight/Plate");
  title_icon = get_node<Control>("Sheet/TitleIcon");
  stencil = get_node<Control>("Sheet/Stencil");
  item_name = get_node<Label>("Sheet/ItemName");
  detail = get_node<Label>("Sheet/Detail");
  hints = get_node<KeyButton>("Sheet/Hints");
  hint_back = get_node<KeyButton>("Sheet/HintBack");
  rows = get_node<VBoxContainer>("Sheet/Rows");
  board = get_node<SkillTreeView>("Board");
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
  slide_sheet(true);
  dim_world(screen != MenuScreen::Inventory);
  get_node<Control>("../Prompt")->set_visible(false); // The player shows it again once unpaused.
  UiSounds::play(this, "Open");
}

void GameMenu::close()
{
  UiSounds::play(this, "Close");
  menu.close();
  slide_sheet(false);
  dim_world(false);
  board->set_visible(false);
  // The HUD comes back faded in, not switched on, after a tree had hidden it.
  Control * panel = get_node<Control>("../Panel");
  if (!panel->is_visible())
  {
    panel->set_modulate(Color(1.f, 1.f, 1.f, 0.f));
    panel->set_visible(true);
    panel->create_tween()->tween_property(panel, "modulate:a", 1.f, HUD_RETURN_TIME);
  }
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
  // Turned about its center, which also scales about there: the corner moves by what the pivot loses.
  const Vector2 pivot = Vector2(SHEET_WIDTH, DESIGN_HEIGHT) * 0.5f;
  sheet->set_pivot_offset(pivot);
  sheet_rest = Vector2(window.x - SHEET_WIDTH * scale, 0.f) - pivot * (1.f - scale);

  board->set_scale(Vector2(scale, scale));
  board->set_size(Vector2((window.x - SHEET_WIDTH * scale) / scale - BOARD_MARGIN * 2.f, DESIGN_HEIGHT - BOARD_TOP - BOARD_BOTTOM));
  board_rest = Vector2(BOARD_MARGIN, BOARD_TOP) * scale;
}

bool GameMenu::tree_screen() const
{
  return menu.screen() == MenuScreen::Stats || menu.screen() == MenuScreen::Machete;
}

bool GameMenu::handle_tree_input(const Ref<InputEvent> & event)
{
  if (event->is_action_pressed("ui_left") || event->is_action_pressed("move_left"))
    move_on_tree(Vector2(-1.f, 0.f));
  else if (event->is_action_pressed("ui_right") || event->is_action_pressed("move_right"))
    move_on_tree(Vector2(1.f, 0.f));
  else if (event->is_action_pressed("ui_up") || event->is_action_pressed("move_forward"))
    move_on_tree(Vector2(0.f, -1.f));
  else if (event->is_action_pressed("ui_down") || event->is_action_pressed("move_back"))
    move_on_tree(Vector2(0.f, 1.f));
  else
    return false;
  return true;
}

// Arrows and sticks walk the drawing, not the list: the nearest medal that way.
void GameMenu::move_on_tree(const Vector2 & direction)
{
  const int target = board->toward(direction);
  if (target == menu.cursor())
    return;
  menu.move_cursor(target - menu.cursor(), row_count());
  UiSounds::play(this, "Move");
  refresh();
}

void GameMenu::slide_sheet(bool in)
{
  if (sheet_tween.is_valid())
    sheet_tween->kill();
  const float scale = sheet->get_scale().y;
  sheet_tween = create_tween();
  sheet_tween->set_parallel();
  if (in)
  {
    set_visible(true);
    sheet->set_position(sheet_rest + SHEET_ENTRY * scale);
    sheet->set_rotation(SHEET_ENTRY_TILT);
    sheet->set_modulate(Color(1.f, 1.f, 1.f, 0.f));
    sheet_tween->tween_property(sheet, "position", sheet_rest, SHEET_IN_TIME)->set_trans(Tween::TRANS_BACK)->set_ease(Tween::EASE_OUT);
    sheet_tween->tween_property(sheet, "rotation", SHEET_REST_TILT, SHEET_IN_TIME)->set_trans(Tween::TRANS_BACK)->set_ease(Tween::EASE_OUT);
    sheet_tween->tween_property(sheet, "modulate:a", 1.f, SHEET_FADE_TIME);
    shade->set_modulate(Color(1.f, 1.f, 1.f, 0.f));
    sheet_tween->tween_property(shade, "modulate:a", 1.f, SHADE_FADE_TIME);
    return;
  }
  sheet_tween->tween_property(sheet, "position", sheet_rest + SHEET_EXIT * scale, SHEET_OUT_TIME)->set_trans(Tween::TRANS_QUAD)->set_ease(Tween::EASE_IN);
  sheet_tween->tween_property(sheet, "rotation", SHEET_ENTRY_TILT * 0.7f, SHEET_OUT_TIME)->set_trans(Tween::TRANS_QUAD)->set_ease(Tween::EASE_IN);
  sheet_tween->tween_property(sheet, "modulate:a", 0.f, SHEET_OUT_TIME)->set_trans(Tween::TRANS_QUAD)->set_ease(Tween::EASE_IN);
  sheet_tween->tween_property(shade, "modulate:a", 0.f, SHEET_OUT_TIME);
  sheet_tween->chain()->tween_callback(callable_mp(static_cast<CanvasItem *>(this), &CanvasItem::set_visible).bind(false));
}

void GameMenu::dim_world(bool dim)
{
  const Ref<World3D> world_3d = get_viewport()->find_world_3d();
  const Ref<Environment> found = world_3d.is_valid() ? world_3d->get_environment() : Ref<Environment>();
  if (found.is_null())
    return;
  // Only the levels read from here; a dimmed one is never saved, but a second dim must not stack.
  if (dim && world != found)
  {
    world = found;
    world_saturation = world->get_adjustment_saturation();
    world_brightness = world->get_adjustment_brightness();
    world->set_adjustment_enabled(true);
  }
  if (world.is_null())
    return;
  if (world_tween.is_valid())
    world_tween->kill();
  world_tween = create_tween();
  world_tween->set_parallel();
  world_tween->tween_property(world.ptr(), "adjustment_saturation", dim ? world_saturation * DIM_SATURATION : world_saturation, DIM_TIME);
  world_tween->tween_property(world.ptr(), "adjustment_brightness", dim ? world_brightness * DIM_BRIGHTNESS : world_brightness, DIM_TIME);
  if (!dim)
    world.unref();
}

void GameMenu::go_back()
{
  hint_back->press();
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
  else if (tree_screen() && handle_tree_input(event))
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
  {
    hints->press();
    next_sort();
  }
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
  FacetPlate::set_row_value(rows, menu.cursor(), GameSettings::row_value(menu.cursor()));
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
    FacetPlate::select_row(rows, menu.cursor(), false);
    menu.move_cursor(step, row_count());
    FacetPlate::select_row(rows, menu.cursor(), true);
  }
  if (menu.cursor() != from)
    UiSounds::play(this, "Move");
}

void GameMenu::next_tab(int step)
{
  (step < 0 ? tab_prev : tab_next)->press();
  show_tab(static_cast<ItemKind>((static_cast<int>(tab) + step + INVENTORY_TABS) % INVENTORY_TABS));
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
  if (hint_back->get_global_transform().xform(hint_back->plate_rect()).has_point(at))
    go_back();
  else if (inventory && hints->get_global_transform().xform(hints->plate_rect()).has_point(at))
  {
    hints->press();
    next_sort();
  }
  else if (inventory && tab_prev->get_global_rect().has_point(at))
    next_tab(-1);
  else if (inventory && tab_next->get_global_rect().has_point(at))
    next_tab(1);
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

  if (tree_screen())
  {
    const int medal = board->entry_at(at);
    return medal < 0 ? NO_ENTRY : medal;
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
    if (tab_of(catalog[stacks[i].item].kind) == tab)
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
      return STAT_COUNT * PlayerStats::MAX_LEVEL;
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
    case MenuScreen::Machete:
      return SKILL_ROWS;
    default:
      return static_cast<int>(tab_stacks().size());
  }
}

void GameMenu::accept()
{
  hints->press();
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
      accept_stat();
      return;
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
    case MenuScreen::Machete:
      accept_skill();
      return;
    case MenuScreen::Inventory:
      if (row_count() > 0 && ItemCatalog::instance()[tab_stacks()[menu.cursor()].item].kind == ItemKind::Outfit)
        UiSounds::play(this, player->wear(tab_stacks()[menu.cursor()].item) ? "Accept" : "Deny");
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
  const MenuScreen screens[] = {MenuScreen::ShopBuy, MenuScreen::ShopSell, MenuScreen::Machete};
  menu.open(screens[menu.cursor()]);
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
  hints->set_disabled(false);
  subtitle->set_text(String());
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
  title_icon->set_visible(menu.screen() == MenuScreen::Chapel);
  const bool tree = tree_screen();
  if (tree && !board->is_visible())
  {
    // Slides in from the left, opposite the sheet.
    if (board_tween.is_valid())
      board_tween->kill();
    board->set_position(board_rest + BOARD_ENTRY * board->get_scale().y);
    board->set_modulate(Color(1.f, 1.f, 1.f, 0.f));
    board_tween = create_tween();
    board_tween->set_parallel();
    board_tween->tween_property(board, "position", board_rest, BOARD_IN_TIME)->set_trans(Tween::TRANS_BACK)->set_ease(Tween::EASE_OUT);
    board_tween->tween_property(board, "modulate:a", 1.f, BOARD_IN_TIME * 0.5f);
  }
  board->set_visible(tree);
  // The board covers the corner of the bars, so they step aside while it is up.
  get_node<Control>("../Panel")->set_visible(!tree);
  stencil->set_visible(menu.screen() == MenuScreen::Pause || menu.screen() == MenuScreen::Options);
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
    case MenuScreen::Machete:
      show_machete();
      break;
    default:
      show_inventory();
      break;
  }
  place_detail();
}

// The description sits right under the list, or where the grid ends when there is no list.
void GameMenu::place_detail()
{
  if (tree_screen())
  {
    item_name->set_position(Vector2(item_name->get_position().x, TREE_NAME_TOP));
    detail->set_position(Vector2(detail->get_position().x, TREE_DETAIL_TOP));
    return;
  }
  item_name->set_position(Vector2(item_name->get_position().x, ITEM_NAME_TOP));
  const float below_rows = ROWS_TOP + rows->get_child_count() * ROW_PITCH + DETAIL_GAP;
  detail->set_position(Vector2(detail->get_position().x, rows->is_visible() ? below_rows : DETAIL_TOP));
}

void GameMenu::show_tabs(bool visible)
{
  tab_left->set_visible(visible);
  tab_middle->set_visible(visible);
  tab_right->set_visible(visible);
  tab_prev->set_visible(visible);
  tab_next->set_visible(visible);
  tab_left->set_text("Consumibles");
  tab_middle->set_text("Coleccionables");
  tab_right->set_text("Equipo");
  paint_tab(tab_left, tab_left_plate, tab == ItemKind::Consumable);
  paint_tab(tab_middle, tab_middle_plate, tab == ItemKind::Collectible);
  paint_tab(tab_right, tab_right_plate, tab == ItemKind::Weapon);
}

void GameMenu::paint_tab(Label * label, FacetPlate * plate, bool active)
{
  const bool was_active = plate->get_style() == FacetPlate::STYLE_SELECTED;
  plate->set_style(active ? FacetPlate::STYLE_SELECTED : FacetPlate::STYLE_STRIP);
  // The blue and red bands hang under an active tab, so its name stays on the yellow.
  plate->set_offset(SIDE_BOTTOM, active ? TAB_BANDS : 0.f);
  label->add_theme_color_override("font_color", active ? UiPalette::INK : UiPalette::ON_PAINT);
  if (active && !was_active)
  {
    label->set_pivot_offset(label->get_size() * 0.5f);
    Facet::pop(*label, 1.f);
  }
}

void GameMenu::add_row(const String & value, bool selected, const String & right)
{
  FacetPlate::add_row(rows, value, selected, right);
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
  title->set_text("Capilla");
  subtitle->set_text(vformat(text("Día %d  ·  tasa ×%d,%02d"), progress.day(), rate / 100, rate % 100));
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

// Three branches from the hero; each lead stat forks into its own levels and a second stat.
void GameMenu::show_stats()
{
  const PlayerProgress & progress = player->progress();
  const PlayerStats & stats = progress.stats();
  const Designar::DynArray<SkillSlot> slots = PlayerStats::tree().layout();
  Designar::DynArray<SkillTreeView::Entry> entries;
  for (Designar::nat_t i = 1; i < slots.size(); ++i)
  {
    const Stat stat = PlayerStats::stat_of(slots[i].id);
    const int level = PlayerStats::level_of(slots[i].id);
    const int reached = stats.level(stat);
    const bool next = level == reached + 1 && stats.opened(stat);
    const SkillTreeView::State state = level <= reached ? SkillTreeView::LEARNED : (next ? SkillTreeView::AVAILABLE : SkillTreeView::LOCKED);
    const int index = static_cast<int>(stat);
    // The first medal of a stat carries its icon and name; the rest only their rank.
    const String name = level == 1 ? text(STAT_TITLES[index]) : String();
    entries.append(SkillTreeView::Entry{slots[i], name, text(NUMERALS[level - 1]), level == 1 ? Facet::skill_icon(STAT_KEYS[index]) : Ref<Texture2D>(), state});
  }
  PackedStringArray titles;
  for (int group = 0; group < STAT_GROUPS; ++group)
    titles.push_back(text(STAT_GROUP_TITLES[group]));
  const SkillTreeView::Entry hero{slots[0], vformat(text("Nivel %d"), stats.total_levels()), vformat("%d", stats.total_levels()), Ref<Texture2D>(), SkillTreeView::LEARNED};
  board->show_tree(hero, entries, titles, menu.cursor());

  const SkillTreeView::Entry & chosen = entries[menu.cursor()];
  const Stat stat = PlayerStats::stat_of(chosen.slot.id);
  const int index = static_cast<int>(stat);
  title->set_text("Subir de nivel");
  item_name->set_text(vformat("%s  %s", text(STAT_NAMES[index]), text(NUMERALS[PlayerStats::level_of(chosen.slot.id) - 1])));
  show_skill_status(chosen.state, text("Subir"), progress.stat_cost(player->chapel_zone()));
  String needs;
  if (chosen.state == SkillTreeView::LOCKED)
    needs = stats.opened(stat) ? text("Sube antes el nivel de arriba.\n") : text("Se abre con el primer nivel de la rama.\n");
  detail->set_text(text(STAT_DETAILS[index]) + "\n" + needs + text("Cada nivel cuesta más que el anterior, en cualquier rama.\n") + vformat(text("Tienes: %d lochas"), progress.lochas()));
  hints->set_text("E  subir");
  hint_back->set_text("Esc  volver");
}

void GameMenu::accept_stat()
{
  const int node = PlayerStats::tree().layout()[menu.cursor() + 1].id;
  const Stat stat = PlayerStats::stat_of(node);
  const int level = PlayerStats::level_of(node);
  // Only the next level of a branch can be bought, whichever medal of it is picked.
  const bool raised = level == player->progress().stats().level(stat) + 1 && player->raise_stat(stat);
  UiSounds::play(this, raised ? "Accept" : "Deny");
  refresh();
  if (raised)
    board->celebrate(menu.cursor());
}

// The strip under the title: what this medal is, and its price when it can be bought.
void GameMenu::show_skill_status(int state, const String & action, int price)
{
  hints->set_disabled(state != SkillTreeView::AVAILABLE);
  if (state == SkillTreeView::LEARNED)
    add_row(text("Aprendido"), false);
  else if (state == SkillTreeView::AVAILABLE)
    add_row(action, true, vformat(text("%d lochas"), price));
  else
    add_row(text("Bloqueado"), false, text("—"));
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
    const ItemId chosen = stacks[menu.cursor()].item;
    const Item & item = catalog[chosen];
    const bool worn = player->progress().worn() == chosen;
    item_name->set_text(worn ? text(item.name) + text("  ·  puesta") : text(item.name));
    detail->set_text(text(item.description));
    if (item.kind == ItemKind::Outfit)
    {
      hints->set_text(text(worn ? "E  quitar" : "E  poner"));
      hint_back->set_text("Esc  volver");
      return;
    }
  }
  else
    detail->set_text(text("No llevas nada aquí."));
  hints->set_text(vformat("R  ordenar: %s", text(SORT_NAMES[static_cast<int>(sort_mode)])));
  hint_back->set_text("Esc  volver");
}

String GameMenu::shop_rate() const
{
  const int rate = player->progress().exchange_rate(player->merchant_zone());
  return vformat(text("Tasa ×%d,%02d"), rate / 100, rate % 100);
}

void GameMenu::show_shop()
{
  const PlayerProgress & progress = player->progress();
  title->set_text("Bachaquero");
  subtitle->set_text(shop_rate());
  if (progress.markup() > 0)
    detail->set_text(vformat(text("\"Cada vez que te mueres, yo subo.\"\nRecargo: +%d%%"), progress.markup()));
  else
    detail->set_text(text("\"Lo que tengo no pierde valor, pana.\""));
  add_row("Comprar", menu.cursor() == ROW_BUY);
  add_row("Vender", menu.cursor() == ROW_SELL);
  add_row("Machete", menu.cursor() == ROW_MACHETE);
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
  title->set_text("Bachaquero");
  subtitle->set_text(shop_rate());
  for (int i = 0; i < count; ++i)
  {
    const Item & item = catalog[stock[i]];
    add_row(text(item.name), menu.cursor() == i, vformat(text("%d lochas"), progress.shop_price(item.value, zone)));
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
  title->set_text("Bachaquero");
  subtitle->set_text(shop_rate());
  for (int i = 0; i < count; ++i)
  {
    const Item & item = catalog[stacks[i].item];
    add_row(vformat("%s  x%d", text(item.name), stacks[i].count), menu.cursor() == i, vformat(text("%d lochas"), progress.sell_price(stacks[i].item, zone)));
  }
  if (count > 0)
    detail->set_text(vformat(text("Paga más mientras más cae la locha.\nTienes: %d lochas"), progress.lochas()));
  else
    detail->set_text(text("No tienes nada que le interese."));
  hints->set_text("E  vender");
  hint_back->set_text("Esc  volver");
}

void GameMenu::show_machete()
{
  const PlayerProgress & progress = player->progress();
  const Zone zone = player->merchant_zone();
  const Designar::DynArray<SkillSlot> slots = progress.machete_tree().layout();
  Designar::DynArray<SkillTreeView::Entry> entries;
  PackedStringArray titles;
  for (Designar::nat_t i = 1; i < slots.size(); ++i)
  {
    const MacheteSkillInfo & info = machete_skill(slots[i].id);
    if (slots[i].depth == 1)
      titles.push_back(text(info.name));
    const SkillTreeView::State state = slots[i].unlocked ? SkillTreeView::LEARNED : (progress.has_skill(info.parent) ? SkillTreeView::AVAILABLE : SkillTreeView::LOCKED);
    // Without an icon a medal shows its depth as a rank, as on the Filo chain.
    entries.append(SkillTreeView::Entry{slots[i], text(info.name), text(NUMERALS[slots[i].depth - 1]), Facet::skill_icon(info.key), state});
  }
  const SkillTreeView::Entry machete{slots[0], text(machete_skill(MacheteSkill::MACHETE).name), String(), Facet::skill_icon("machete"), SkillTreeView::LEARNED};
  board->show_tree(machete, entries, titles, menu.cursor());

  const SkillTreeView::Entry & chosen = entries[menu.cursor()];
  const MacheteSkillInfo & info = machete_skill(chosen.slot.id);
  title->set_text(text("Machete"));
  item_name->set_text(text(info.name));
  show_skill_status(chosen.state, text("Aprender"), progress.skill_price(chosen.slot.id, zone));
  const String needs = chosen.state == SkillTreeView::LOCKED ? vformat(text("Necesitas %s.\n"), text(machete_skill(info.parent).name)) : String();
  detail->set_text(text(info.description) + "\n" + needs + vformat(text("Tienes: %d lochas"), progress.lochas()));
  hints->set_text("E  aprender");
  hint_back->set_text("Esc  volver");
}

void GameMenu::accept_skill()
{
  const int id = player->progress().machete_tree().layout()[menu.cursor() + 1].id;
  const bool learned = player->learn(id);
  UiSounds::play(this, learned ? "Accept" : "Deny");
  refresh();
  if (learned)
    board->celebrate(menu.cursor());
}
