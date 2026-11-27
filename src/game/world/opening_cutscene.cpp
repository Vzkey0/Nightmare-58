#include "opening_cutscene.hpp"
#include "save_file.hpp"

#include <godot_cpp/classes/animation_player.hpp>
#include <godot_cpp/classes/camera3d.hpp>
#include <godot_cpp/classes/input.hpp>
#include <godot_cpp/classes/input_event_joypad_button.hpp>
#include <godot_cpp/classes/input_event_key.hpp>
#include <godot_cpp/classes/property_tweener.hpp>
#include <godot_cpp/classes/scene_tree.hpp>
#include <godot_cpp/classes/tween.hpp>
#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/core/math.hpp>

#include <core/progression/player_progress.hpp>

using namespace godot;

namespace
{
const char * const GAME_SCENE = "res://scenes/levels/avenue.tscn";
constexpr float SKYLINE_RATIO = 0.2f; // The far city crawls; that is what gives the windows depth.
constexpr float SEND_AHEAD = 180.f;    // Where a scripted piece enters the street, deep in the fog.
constexpr float GONE_BEHIND = 30.f;
constexpr float SWAY = 0.005f;         // Half a centimetre, at the engine's beat.
constexpr float SWAY_HZ = 1.7f;
constexpr float SKIP_TIME = 1.f;       // Held, so nobody skips it by accident the first time.
constexpr float SKIP_DECAY = 3.f;
constexpr float HINT_TIME = 3.f;
constexpr float FADE_OUT = 0.6f;
constexpr float RING_RADIUS = 14.f;
constexpr float RING_WIDTH = 3.f;
const Color SPEAKER_COLOR(0.85f, 0.71f, 0.35f);
constexpr float TYPE_RATE = 38.f;     // Characters a second: fast enough to keep up, slow enough to follow.
constexpr float KEY_GAP = 0.055f;     // At most one key sound this often, or the typing turns into a buzz.
constexpr float ENGINE_IDLE = 0.75f;  // Engine pitch stopped, and how much each m/s raises it.
constexpr float ENGINE_RISE = 0.03f;
}

void OpeningCutscene::_bind_methods()
{
  ClassDB::bind_method(D_METHOD("get_drive_speed"), &OpeningCutscene::get_drive_speed);
  ClassDB::bind_method(D_METHOD("set_drive_speed", "value"), &OpeningCutscene::set_drive_speed);
  ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "drive_speed"), "set_drive_speed", "get_drive_speed");

  ClassDB::bind_method(D_METHOD("cut", "camera"), &OpeningCutscene::cut);
  ClassDB::bind_method(D_METHOD("say", "who", "line"), &OpeningCutscene::say);
  ClassDB::bind_method(D_METHOD("send", "prop"), &OpeningCutscene::send);
  ClassDB::bind_method(D_METHOD("finish"), &OpeningCutscene::finish);
}

void OpeningCutscene::_ready()
{
  road = get_node<Node3D>("Road");
  skyline = get_node<Node3D>("Skyline");
  props = get_node<Node3D>("Props");
  camera_rig = get_node<Node3D>("Car/CameraRig");
  subtitle = get_node<RichTextLabel>("Screen/Subtitle");
  skip_hint = get_node<Control>("Screen/SkipHint");
  skip_ring = get_node<Control>("Screen/SkipHint/Ring");
  fade = get_node<ColorRect>("Screen/Fade");
  typewriter = get_node<AudioStreamPlayer>("Screen/Typewriter");
  engine = get_node<AudioStreamPlayer>("Car/Engine");

  skip_ring->connect("draw", callable_mp(this, &OpeningCutscene::draw_skip_ring));
  Input::get_singleton()->set_mouse_mode(Input::MOUSE_MODE_HIDDEN);

  // The protagonist is whoever the player named; Luis never says it, the subtitles do.
  PlayerProgress progress;
  SaveFile::read(progress);
  player_name = String::utf8(progress.player_name().c_str());
}

void OpeningCutscene::_process(double delta)
{
  clock += delta;
  const float distance = drive_speed * static_cast<float>(delta);
  scroll(road, distance);
  scroll(skyline, distance * SKYLINE_RATIO);

  for (int i = 0; i < props->get_child_count(); ++i)
  {
    Node3D * prop = Object::cast_to<Node3D>(props->get_child(i));
    if (prop == nullptr || !prop->is_visible())
      continue;
    prop->translate(Vector3(0, 0, distance));
    if (prop->get_position().z > GONE_BEHIND)
      prop->hide();
  }
  make_room();

  const float sway = drive_speed > 0.f ? SWAY * Math::sin(static_cast<float>(clock) * static_cast<float>(Math::TAU) * SWAY_HZ) : 0.f;
  camera_rig->set_position(Vector3(0, sway, 0));
  engine->set_pitch_scale(ENGINE_IDLE + drive_speed * ENGINE_RISE);
  type(delta);

  if (leaving)
    return;
  if (Input::get_singleton()->is_action_pressed("interact"))
    skip_hold += static_cast<float>(delta);
  else
    skip_hold = MAX(0.f, skip_hold - static_cast<float>(delta) * SKIP_DECAY);
  hint_time = MAX(0.f, hint_time - static_cast<float>(delta));
  skip_hint->set_visible(hint_time > 0.f || skip_hold > 0.f);
  skip_ring->queue_redraw();
  if (skip_hold >= SKIP_TIME)
    finish();
}

// Any key or button shows how to skip, without skipping.
void OpeningCutscene::_unhandled_input(const Ref<InputEvent> & event)
{
  if ((Object::cast_to<InputEventKey>(*event) != nullptr || Object::cast_to<InputEventJoypadButton>(*event) != nullptr) && event->is_pressed())
    hint_time = HINT_TIME;
}

// Each strip is a row of evenly spaced pieces; the one that leaves behind the car goes back to
// the front of the row.
void OpeningCutscene::scroll(Node3D * strip, float distance)
{
  const int count = strip->get_child_count();
  const float spacing = strip->get_meta("spacing");
  for (int i = 0; i < count; ++i)
  {
    Node3D * piece = Object::cast_to<Node3D>(strip->get_child(i));
    Vector3 at = piece->get_position();
    at.z += distance;
    if (at.z > spacing)
      at.z -= spacing * count;
    piece->set_position(at);
  }
}

// A scripted building stands where a street one already is: the street one steps aside while
// they overlap. Pieces and buildings carry their half length and side as metadata.
void OpeningCutscene::make_room()
{
  for (int i = 0; i < road->get_child_count(); ++i)
  {
    Node3D * piece = Object::cast_to<Node3D>(road->get_child(i));
    for (const char * side : {"Left", "Right"})
    {
      Node * row = piece->get_node<Node>(side);
      for (int j = 0; j < row->get_child_count(); ++j)
      {
        Node3D * building = Object::cast_to<Node3D>(row->get_child(j));
        const float z = piece->get_position().z + building->get_position().z;
        const float half = building->get_meta("half");
        bool blocked = false;
        for (int k = 0; k < props->get_child_count() && !blocked; ++k)
        {
          Node3D * prop = Object::cast_to<Node3D>(props->get_child(k));
          blocked = prop->is_visible() && prop->get_meta("side", "") == String(side) &&
                    Math::abs(prop->get_position().z - z) < half + static_cast<float>(prop->get_meta("half", 0.f));
        }
        building->set_visible(!blocked);
      }
    }
  }
}

void OpeningCutscene::cut(const String & camera)
{
  get_node<Camera3D>(NodePath("%" + camera))->make_current();
}

// The line types itself out with a typewriter under it; the speaker's name is there from the start.
void OpeningCutscene::say(const String & who, const String & line)
{
  typing = !line.is_empty();
  quiet = who.is_empty();
  typed = 0.f;
  if (!typing)
  {
    subtitle->set_text("");
    return;
  }
  // No speaker is a sound, captioned for whoever plays without it, and typed without keys.
  if (quiet)
  {
    subtitle->set_text(vformat("[center][i]%s[/i][/center]", line));
  }
  else
  {
    const String name = who == "L" ? String("Luis") : player_name;
    subtitle->set_text(vformat("[center][color=#%s]%s:[/color] %s[/center]", SPEAKER_COLOR.to_html(false), name, line));
    typed = static_cast<float>(name.length() + 2);
  }
  subtitle->set_visible_characters(static_cast<int>(typed));
}

void OpeningCutscene::type(double delta)
{
  key_wait = MAX(0.f, key_wait - static_cast<float>(delta));
  if (!typing)
    return;
  const int before = static_cast<int>(typed);
  typed += TYPE_RATE * static_cast<float>(delta);
  const int total = subtitle->get_total_character_count();
  const int now = MIN(static_cast<int>(typed), total);
  subtitle->set_visible_characters(now);
  if (now >= total)
    typing = false;
  if (quiet || key_wait > 0.f || now == before)
    return;
  const String text = subtitle->get_parsed_text();
  if (now - 1 < text.length() && text[now - 1] != ' ')
  {
    typewriter->play();
    key_wait = KEY_GAP;
  }
}

void OpeningCutscene::send(const String & prop)
{
  Node3D * piece = props->get_node<Node3D>(NodePath(prop));
  Vector3 at = piece->get_position();
  at.z = -SEND_AHEAD;
  piece->set_position(at);
  piece->show();
}

void OpeningCutscene::draw_skip_ring()
{
  const Vector2 center = skip_ring->get_size() / 2.f;
  skip_ring->draw_arc(center, RING_RADIUS, 0.f, static_cast<float>(Math::TAU), 32, Color(1, 1, 1, 0.25f), RING_WIDTH, true);
  if (skip_hold > 0.f)
    skip_ring->draw_arc(center, RING_RADIUS, -static_cast<float>(Math::PI) / 2.f, -static_cast<float>(Math::PI) / 2.f + static_cast<float>(Math::TAU) * MIN(skip_hold / SKIP_TIME, 1.f), 32, Color(1, 1, 1), RING_WIDTH, true);
}

// The script's last key and the skip both end here: to black, then the avenue.
void OpeningCutscene::finish()
{
  if (leaving)
    return;
  leaving = true;
  get_node<AnimationPlayer>("AnimationPlayer")->pause();
  skip_hint->hide();
  typing = false;
  subtitle->set_text("");
  Ref<Tween> tween = create_tween();
  tween->tween_property(fade, "color:a", 1.f, FADE_OUT);
  tween->tween_callback(Callable(get_tree(), "change_scene_to_file").bind(GAME_SCENE));
}
