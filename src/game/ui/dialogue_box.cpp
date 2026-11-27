#include "dialogue_box.hpp"
#include "key_button.hpp"

#include <godot_cpp/classes/audio_stream.hpp>
#include <godot_cpp/classes/audio_stream_randomizer.hpp>
#include <godot_cpp/classes/box_container.hpp>
#include <godot_cpp/classes/engine.hpp>
#include <godot_cpp/classes/gradient.hpp>
#include <godot_cpp/classes/gradient_texture2d.hpp>
#include <godot_cpp/classes/resource_loader.hpp>
#include <godot_cpp/classes/theme.hpp>
#include <godot_cpp/classes/v_box_container.hpp>
#include <godot_cpp/classes/viewport.hpp>
#include <godot_cpp/core/math.hpp>

using namespace godot;

namespace
{
const Color SPEAKER_COLOR(0.85f, 0.71f, 0.35f);
const Color TEXT_COLOR(0.97f, 0.95f, 0.90f);
const Color OUTLINE_COLOR(0.f, 0.f, 0.f, 0.95f);
constexpr float TYPE_RATE = 38.f;
constexpr float KEY_GAP = 0.055f;
}

void DialogueBox::_ready()
{
  set_anchors_and_offsets_preset(PRESET_FULL_RECT);
  set_mouse_filter(MOUSE_FILTER_IGNORE);
  set_visible(false);

  // Soft bottom vignette for subtitle readability without a heavy box.
  Ref<Gradient> gradient;
  gradient.instantiate();
  gradient->set_color(0, Color(0.f, 0.f, 0.f, 0.f));
  gradient->set_color(1, Color(0.02f, 0.02f, 0.03f, 0.62f));
  Ref<GradientTexture2D> gradient_tex;
  gradient_tex.instantiate();
  gradient_tex->set_gradient(gradient);
  gradient_tex->set_fill_from(Vector2(0.f, 0.f));
  gradient_tex->set_fill_to(Vector2(0.f, 1.f));
  gradient_tex->set_width(8);
  gradient_tex->set_height(128);

  shade = memnew(TextureRect);
  shade->set_anchor_and_offset(SIDE_RIGHT, 1.f, 0.f);
  shade->set_anchor_and_offset(SIDE_BOTTOM, 1.f, 0.f);
  shade->set_anchor_and_offset(SIDE_LEFT, 0.f, 0.f);
  shade->set_anchor_and_offset(SIDE_TOP, 0.72f, 0.f);
  shade->set_texture(gradient_tex);
  shade->set_expand_mode(TextureRect::EXPAND_IGNORE_SIZE);
  shade->set_mouse_filter(MOUSE_FILTER_IGNORE);
  add_child(shade);

  VBoxContainer * stack = memnew(VBoxContainer);
  stack->set_anchor_and_offset(SIDE_RIGHT, 0.86f, 0.f);
  stack->set_anchor_and_offset(SIDE_BOTTOM, 0.965f, 0.f);
  stack->set_anchor_and_offset(SIDE_LEFT, 0.14f, 0.f);
  stack->set_anchor_and_offset(SIDE_TOP, 0.62f, 0.f);
  stack->set_alignment(BoxContainer::ALIGNMENT_END);
  stack->add_theme_constant_override("separation", 14);
  stack->set_mouse_filter(MOUSE_FILTER_IGNORE);
  add_child(stack);

  body = memnew(RichTextLabel);
  body->set_use_bbcode(true);
  body->set_scroll_active(false);
  body->set_fit_content(true);
  body->set_mouse_filter(MOUSE_FILTER_IGNORE);
  body->add_theme_font_size_override("normal_font_size", 30);
  body->add_theme_font_size_override("italics_font_size", 30);
  body->add_theme_color_override("default_color", TEXT_COLOR);
  body->add_theme_color_override("font_outline_color", OUTLINE_COLOR);
  body->add_theme_constant_override("outline_size", 8);
  stack->add_child(body);

  hint_button = memnew(KeyButton);
  const Ref<Theme> street_theme = ResourceLoader::get_singleton()->load("res://ui/street_theme.tres");
  if (street_theme.is_valid())
    hint_button->set_theme(street_theme);
  hint_button->set_align(1);
  hint_button->set_custom_minimum_size(Vector2(260.f, 46.f));
  hint_button->set_h_size_flags(SIZE_SHRINK_CENTER);
  hint_button->set_mouse_filter(MOUSE_FILTER_IGNORE);
  stack->add_child(hint_button);

  // Same typewriter key sound pool as the opening cinematic.
  Ref<AudioStreamRandomizer> keys;
  keys.instantiate();
  keys->set_random_pitch(1.1f);
  keys->set_random_volume_offset_db(2.f);
  for (int i = 1; i <= 6; ++i)
  {
    const Ref<AudioStream> clip = ResourceLoader::get_singleton()->load(vformat("res://audio/opening/key_%d.ogg", i));
    if (clip.is_valid())
      keys->add_stream(-1, clip);
  }
  typewriter = memnew(AudioStreamPlayer);
  typewriter->set_stream(keys);
  typewriter->set_volume_db(-10.f);
  typewriter->set_max_polyphony(3);
  add_child(typewriter);
}

bool DialogueBox::holds_input() const
{
  return open_state || Engine::get_singleton()->get_physics_frames() <= closed_frame + 1;
}

void DialogueBox::start(
  const std::vector<DialogueLine> & lines,
  const String & player_name,
  std::function<void(bool)> on_speaker_change,
  std::function<void()> on_complete)
{
  if (lines.empty())
    return;
  queue = lines;
  protagonist_name = player_name.is_empty() ? String::utf8("Tú") : player_name;
  speaker_callback = std::move(on_speaker_change);
  complete_callback = std::move(on_complete);
  index = 0;
  key_wait = 0.f;
  open_state = true;
  set_visible(true);
  show_current();
}

void DialogueBox::show_current()
{
  const DialogueLine & line = queue[index];
  const String speaker = (line.speaker.is_empty() || line.speaker == "P") ? protagonist_name : line.speaker;
  body->set_text(vformat("[center][color=#%s]%s:[/color] %s[/center]", SPEAKER_COLOR.to_html(false), speaker, line.text));
  typed = static_cast<float>(speaker.length() + 2);
  body->set_visible_characters(static_cast<int>(typed));
  typing = true;
  key_wait = 0.f;

  const bool last = (index + 1 >= static_cast<int>(queue.size()));
  hint_button->set_text(last ? String::utf8("E  Cerrar") : String::utf8("E  Continuar"));

  if (speaker_callback)
    speaker_callback(line.npc_speaks);
}

void DialogueBox::_process(double delta)
{
  key_wait = MAX(0.f, key_wait - static_cast<float>(delta));
  if (!open_state || !typing)
    return;
  const int before = static_cast<int>(typed);
  typed += TYPE_RATE * static_cast<float>(delta);
  const int total = body->get_total_character_count();
  const int shown = MIN(static_cast<int>(typed), total);
  body->set_visible_characters(shown);
  if (shown >= total)
    typing = false;
  if (key_wait > 0.f || shown == before)
    return;
  const String parsed = body->get_parsed_text();
  if (shown - 1 >= 0 && shown - 1 < parsed.length() && parsed[shown - 1] != ' ')
  {
    typewriter->play();
    key_wait = KEY_GAP;
  }
}

void DialogueBox::_unhandled_input(const Ref<InputEvent> & event)
{
  if (!open_state || !event->is_pressed() || event->is_echo())
    return;

  if (event->is_action_pressed("interact") || event->is_action_pressed("ui_accept"))
  {
    get_viewport()->set_input_as_handled();
    hint_button->press();
    advance();
    return;
  }
  if (event->is_action_pressed("pause") || event->is_action_pressed("ui_cancel"))
  {
    get_viewport()->set_input_as_handled();
    close();
  }
}

void DialogueBox::advance()
{
  if (typing)
  {
    body->set_visible_characters(body->get_total_character_count());
    typing = false;
    return;
  }
  if (index + 1 < static_cast<int>(queue.size()))
  {
    ++index;
    show_current();
    return;
  }
  close();
}

void DialogueBox::close()
{
  if (!open_state)
    return;
  open_state = false;
  typing = false;
  set_visible(false);
  closed_frame = Engine::get_singleton()->get_physics_frames();

  if (speaker_callback)
    speaker_callback(false);

  auto finish = std::move(complete_callback);
  speaker_callback = nullptr;
  complete_callback = nullptr;
  queue.clear();

  if (finish)
    finish();
}
