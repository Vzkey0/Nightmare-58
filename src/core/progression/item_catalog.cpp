#include <core/progression/item_catalog.hpp>

namespace
{
// The ids in item_catalog.hpp must match their place here.
constexpr Item ITEMS[] = {
  {"coffee", "Café", "Cura una parte de la vida. Se recarga en las capillas.", ItemKind::Consumable, 0},
  {"return_candle", "Vela de retorno", "Te devuelve a la última capilla.", ItemKind::Consumable, 30},
  {"gaita_vinyl", "Vinilo de gaita", "Un diciembre que ya nadie canta. Como recuerdo, recuperas el aliento más rápido.", ItemKind::Collectible, 150},
  {"baseball_card", "Cromo de béisbol", "El juego que antes se oía por radio. Como recuerdo, el machete lanzado pega más y vuelve antes.", ItemKind::Collectible, 90},
  {"domino_tile", "Ficha de dominó", "Doble seis. La mesa quedó incompleta. Como recuerdo, los enemigos sueltan más lochas.", ItemKind::Collectible, 60},
  {"family_photo", "Foto familiar", "Nadie en ella sigue en el país.", ItemKind::Collectible, 200},
  {"machete", "Machete", "El óxido se comió el lomo. El filo sigue ahí.", ItemKind::Weapon, 0},
  {"fire_grease", "Grasa de fuego", "Un minuto de hoja ardiendo. Lo que cortas sigue quemándose.", ItemKind::Consumable, 25},
  {"ice_grease", "Grasa de hielo", "Un minuto de hoja helada. Lo que cortas se mueve más lento.", ItemKind::Consumable, 25},
  {"cap", "Gorra", "Tricolor y gastada, como la chaqueta. Más fuerza mientras la llevas puesta.", ItemKind::Outfit, 120},
  {"hallaca", "Hallaca", "La de diciembre, en familia. Cura toda la vida y sigue curando un rato.", ItemKind::Consumable, 0},
  {"papelon", "Papelón con limón", "Frío y dulce. Devuelve todo el aliento y lo recupera más rápido un rato.", ItemKind::Consumable, 20},
  {"holy_water", "Agua bendita", "El padre la da en la capilla. Un minuto de hoja bendita: más daño a los muertos y a las leyendas.", ItemKind::Consumable, 0},
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
