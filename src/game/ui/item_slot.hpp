#pragma once

#include <godot_cpp/classes/control.hpp>
#include <godot_cpp/classes/texture2d.hpp>
#include <godot_cpp/classes/tween.hpp>

#include <core/progression/item_catalog.hpp>

// One item, with the icon rendered from its own model. A slot of the inventory grid when framed,
// and the bare icon inside the HUD's medallion when not.
class ItemSlot : public godot::Control
{
  GDCLASS(ItemSlot, godot::Control)

protected:
  static void _bind_methods();
  void _notification(int what);

public:
  void _draw() override;

  void show_item(ItemId value, int amount, bool is_selected);

  bool get_framed() const { return framed; }
  void set_framed(bool value) { framed = value; }

private:
  ItemId item = NO_ITEM;
  godot::Ref<godot::Texture2D> icon;
  int count = 0;
  bool selected = false;
  bool framed = true;
  godot::Ref<godot::Tween> tween;
};
