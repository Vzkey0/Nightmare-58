#include <core/progression/item_catalog.hpp>

namespace
{
// COFFEE and CANDLE in item_catalog.hpp must match their place here.
constexpr Item ITEMS[] = {
  {"coffee", "Café", "Cura una parte de la vida. Se recarga en las capillas.", ItemKind::Consumable, 0},
  {"return_candle", "Vela de retorno", "Te devuelve a la última capilla.", ItemKind::Consumable, 40},
  {"gaita_vinyl", "Vinilo de gaita", "Un diciembre que ya nadie canta.", ItemKind::Collectible, 150},
  {"baseball_card", "Cromo de béisbol", "El juego que antes se oía por radio.", ItemKind::Collectible, 90},
  {"domino_tile", "Ficha de dominó", "Doble seis. La mesa quedó incompleta.", ItemKind::Collectible, 60},
  {"family_photo", "Foto familiar", "Nadie en ella sigue en el país.", ItemKind::Collectible, 200},
};
}

const ItemCatalog & ItemCatalog::instance()
{
  static const ItemCatalog catalog;
  return catalog;
}

ItemCatalog::ItemCatalog()
{
  for (const Item & item : ITEMS)
  {
    ids.insert(std::string(item.key), size());
    items.append(item);
  }
}

ItemId ItemCatalog::find(const std::string & key) const
{
  const ItemId * id = ids.search(key);
  return id == nullptr ? NO_ITEM : *id;
}
