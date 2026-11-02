#include "save_file.hpp"

#include <godot_cpp/classes/dir_access.hpp>
#include <godot_cpp/classes/file_access.hpp>
#include <godot_cpp/variant/string.hpp>
#include <godot_cpp/variant/utility_functions.hpp>

#include <core/progression/player_progress.hpp>

using namespace godot;

namespace
{
const char * const OLD_PATH = "user://save.txt"; // From before there were slots.
const char * const LAST_SLOT_PATH = "user://last_slot.txt";
constexpr int NO_SLOT = -1;

int current = NO_SLOT;

String slot_path(int slot)
{
  return vformat("user://save_%d.txt", slot + 1);
}

void adopt_old_save()
{
  if (FileAccess::file_exists(OLD_PATH) && !FileAccess::file_exists(slot_path(0)))
    DirAccess::rename_absolute(OLD_PATH, slot_path(0));
}
}

int SaveFile::active_slot()
{
  if (current != NO_SLOT)
    return current;

  adopt_old_save();
  const int last = FileAccess::file_exists(LAST_SLOT_PATH) ? FileAccess::get_file_as_string(LAST_SLOT_PATH).to_int() : 0;
  current = last >= 0 && last < SLOTS ? last : 0;
  return current;
}

void SaveFile::select(int slot)
{
  current = slot;
  Ref<FileAccess> file = FileAccess::open(LAST_SLOT_PATH, FileAccess::WRITE);
  if (file.is_valid())
    file->store_string(String::num_int64(slot));
}

bool SaveFile::exists(int slot)
{
  adopt_old_save();
  return FileAccess::file_exists(slot_path(slot));
}

void SaveFile::erase(int slot)
{
  DirAccess::remove_absolute(slot_path(slot));
}

bool SaveFile::write(const PlayerProgress & progress)
{
  const String path = slot_path(active_slot());
  const String temp = path + String(".tmp");
  Ref<FileAccess> file = FileAccess::open(temp, FileAccess::WRITE);
  if (file.is_null())
  {
    UtilityFunctions::push_warning("Could not write the saved game.");
    return false;
  }
  file->store_string(String::utf8(progress.to_text().c_str()));
  file->close();

  return DirAccess::rename_absolute(temp, path) == OK;
}

bool SaveFile::read(PlayerProgress & progress)
{
  return read_slot(active_slot(), progress);
}

bool SaveFile::read_slot(int slot, PlayerProgress & progress)
{
  if (!exists(slot))
    return false;

  const String text = FileAccess::get_file_as_string(slot_path(slot));
  if (progress.from_text(text.utf8().get_data()))
    return true;

  UtilityFunctions::push_warning("The saved game is damaged and was not loaded.");
  return false;
}
