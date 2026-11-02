#include "game_settings.hpp"

#include <godot_cpp/classes/audio_server.hpp>
#include <godot_cpp/classes/config_file.hpp>
#include <godot_cpp/core/math.hpp>
#include <godot_cpp/variant/utility_functions.hpp>

using namespace godot;

namespace
{
const char * const PATH = "user://settings.cfg";
const char * const SECTION = "game";
constexpr int MAX_NOTCH = 10;
constexpr int DEFAULT_SENSITIVITY = 4; // The notch that means the player's own mouse_sensitivity.
constexpr float VALUE_START = 0.66f;     // Shares of a row's width.
constexpr float VALUE_MIDDLE = 0.85f;

int volume = MAX_NOTCH;
int sensitivity = DEFAULT_SENSITIVITY;
bool loaded = false;

void apply_volume()
{
  AudioServer::get_singleton()->set_bus_volume_db(0, UtilityFunctions::linear_to_db(volume / static_cast<float>(MAX_NOTCH)));
}

void write()
{
  Ref<ConfigFile> file;
  file.instantiate();
  file->set_value(SECTION, "volume", volume);
  file->set_value(SECTION, "sensitivity", sensitivity);
  file->save(PATH);
}
}

void GameSettings::load()
{
  if (loaded)
    return;
  loaded = true;

  Ref<ConfigFile> file;
  file.instantiate();
  if (file->load(PATH) == OK)
  {
    volume = CLAMP(static_cast<int>(file->get_value(SECTION, "volume", volume)), 0, MAX_NOTCH);
    sensitivity = CLAMP(static_cast<int>(file->get_value(SECTION, "sensitivity", sensitivity)), 1, MAX_NOTCH);
  }
  apply_volume();
}

float GameSettings::mouse_scale()
{
  return sensitivity / static_cast<float>(DEFAULT_SENSITIVITY);
}

void GameSettings::step(int row, int direction)
{
  if (row == 0)
  {
    volume = CLAMP(volume + direction, 0, MAX_NOTCH);
    apply_volume();
  }
  else
    sensitivity = CLAMP(sensitivity + direction, 1, MAX_NOTCH);
  write();
}

int GameSettings::click_direction(const Rect2 & row, float x)
{
  const float share = (x - row.position.x) / row.size.x;
  if (share < VALUE_START)
    return 0;
  return share < VALUE_MIDDLE ? -1 : 1;
}

String GameSettings::row_name(int row)
{
  return row == 0 ? "Volumen" : "Sensibilidad";
}

String GameSettings::row_value(int row)
{
  return vformat("<  %d / %d  >", row == 0 ? volume : sensitivity, MAX_NOTCH);
}
