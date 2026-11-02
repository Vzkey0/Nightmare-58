#pragma once

class PlayerProgress;

// One text file per saved game. Every write goes to the active slot, the one chosen on the title
// screen; it outlives the change of scene because it lives here and not in a node.
namespace SaveFile
{
constexpr int SLOTS = 5;

int active_slot();
void select(int slot);
bool exists(int slot);
void erase(int slot);

bool write(const PlayerProgress & progress);
bool read(PlayerProgress & progress);
bool read_slot(int slot, PlayerProgress & progress);
}
