#pragma once

class PlayerProgress;

namespace SaveFile
{
// Writes a new file and then swaps it in, so a crash midway leaves the old save whole.
bool write(const PlayerProgress & progress);

// False with no save yet or a damaged one, and the progress stays as it was.
bool read(PlayerProgress & progress);
}
