#include "lost_lochas.hpp"
#include <game/player/player_controller.hpp>

using namespace godot;

namespace
{
constexpr float TOUCH_RANGE_SQUARED = 2.5f * 2.5f;
}

void LostLochas::_ready()
{
  connect("body_entered", callable_mp(this, &LostLochas::on_body_entered));
}

void LostLochas::on_body_entered(Node3D * body)
{
  PlayerController * player = Object::cast_to<PlayerController>(body);
  if (player == nullptr || player->is_dead())
    return;
  // On the tick of a respawn the physics still has the body here, where it died.
  if (player->get_global_position().distance_squared_to(get_global_position()) < TOUCH_RANGE_SQUARED)
    player->recover_lochas();
}
