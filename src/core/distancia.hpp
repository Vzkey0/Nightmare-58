#pragma once

enum class RangoDistancia { Cerca, Media, Lejos };

// Primera decisión del árbol de comportamiento: en qué rango está el jugador.
inline RangoDistancia clasificar_distancia(float distancia, float cerca, float media)
{
  if (distancia <= cerca)
    return RangoDistancia::Cerca;
  return distancia <= media ? RangoDistancia::Media : RangoDistancia::Lejos;
}
