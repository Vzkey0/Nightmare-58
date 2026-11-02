#include "save_file.hpp"

#include <godot_cpp/classes/dir_access.hpp>
#include <godot_cpp/classes/file_access.hpp>
#include <godot_cpp/variant/string.hpp>
#include <godot_cpp/variant/utility_functions.hpp>

#include <core/progression/player_progress.hpp>

using namespace godot;

namespace
{
const char * const SAVE_PATH = "user://save.txt";
const char * const TEMP_PATH = "user://save.tmp";
}

bool SaveFile::write(const PlayerProgress & progress)
{
  Ref<FileAccess> file = FileAccess::open(TEMP_PATH, FileAccess::WRITE);
  if (file.is_null())
  {
    UtilityFunctions::push_warning("Could not write the saved game.");
    return false;
  }
  file->store_string(String::utf8(progress.to_text().c_str()));
  file->close();

  return DirAccess::rename_absolute(TEMP_PATH, SAVE_PATH) == OK;
}

bool SaveFile::read(PlayerProgress & progress)
{
  if (!FileAccess::file_exists(SAVE_PATH))
    return false;

  const String text = FileAccess::get_file_as_string(SAVE_PATH);
  if (progress.from_text(text.utf8().get_data()))
    return true;

  UtilityFunctions::push_warning("The saved game is damaged and was not loaded.");
  return false;
}
