#undef NDEBUG
#include <cassert>

#include <core/distancia.hpp>

int main()
{
  assert(clasificar_distancia(2.f, 3.f, 8.f) == RangoDistancia::Cerca);
  assert(clasificar_distancia(3.f, 3.f, 8.f) == RangoDistancia::Cerca);
  assert(clasificar_distancia(5.f, 3.f, 8.f) == RangoDistancia::Media);
  assert(clasificar_distancia(9.f, 3.f, 8.f) == RangoDistancia::Lejos);
  return 0;
}
