#pragma once

enum class Zone { Avenue, Jungle, Plain };

constexpr int ZONE_COUNT = 3;

// Percent: 100 is what a locha was worth on day 0. It rises in steps, like announced devaluations.
int exchange_rate(int day);

// A price fixed in day-0 lochas, in the lochas of that day. Rounded up: the seller never loses.
int inflate(int base, int day);

// True on the days the rate takes a step, so the game can tell the player the locha fell.
bool devalues_on(int day);
