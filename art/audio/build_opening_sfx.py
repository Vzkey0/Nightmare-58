"""Builds game/audio/opening from the Pixabay sounds listed in game/audio/CREDITS.md.

Usage: python build_opening_sfx.py <folder with the mp3s> (needs numpy and ffmpeg)

The files keep the names they were saved with: a short name plus the Pixabay id. Loops are cut
with a crossfade so they repeat without a click; one-shots start on their attack. Loops are left
at one loudness and one-shots at one peak, so volume_db in opening.tscn does the mixing.
"""
import os
import subprocess
import sys

import numpy as np

RATE = 44100
SOURCE = sys.argv[1]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "game", "audio", "opening")
LOOP_RMS = 10 ** (-20 / 20)
PEAK = 10 ** (-1 / 20)
ONSET = 0.3

# A car radio: no lows, no highs, a little crunch.
RADIO = "highpass=f=350,lowpass=f=3200,acompressor=threshold=0.2:ratio=4,volume=2"


def load(name, start=0.0, length=None, cut=""):
  command = ["ffmpeg", "-v", "error", "-ss", str(start)]
  if length:
    command += ["-t", str(length)]
  command += ["-i", os.path.join(SOURCE, name), "-ac", "1", "-ar", str(RATE)]
  if cut:
    command += ["-af", cut]
  raw = subprocess.run(command + ["-f", "f32le", "-"], capture_output=True, check=True).stdout
  return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


def envelope(x):
  window = RATE // 200
  return np.sqrt(np.convolve(x * x, np.ones(window) / window, "same"))


def onsets(x, gap=0.12, share=ONSET):
  """Every attack that rises over the share of the peak, at least gap seconds apart."""
  level = envelope(x)
  above = level >= level.max() * share
  found = []
  for i in np.flatnonzero(above[1:] & ~above[:-1]) + 1:
    if not found or i - found[-1] > gap * RATE:
      found.append(int(i))
  return found


def fade(x, rise=0.002, tail=0.08):
  x = x.copy()
  count = min(int(tail * RATE), len(x))
  x[-count:] *= np.linspace(1, 0, count) ** 2
  up = int(rise * RATE)
  x[:up] *= np.linspace(0, 1, up)
  return x


def one_shot(x, length, lead=0.005, tail=0.08):
  start = max(onsets(x)[0] - int(lead * RATE), 0)
  return fade(x[start:start + int(length * RATE)], tail=tail)


def loop(x, overlap=1.0):
  """The tail fades into the head, so the end runs into the start."""
  n = int(overlap * RATE)
  body, tail = x[:-n].copy(), x[-n:]
  ramp = np.linspace(0, 1, n)
  body[:n] = body[:n] * np.sqrt(ramp) + tail * np.sqrt(1 - ramp)
  return body


def at_peak(x):
  return x * PEAK / np.abs(x).max()


def at_loudness(x):
  return np.clip(x * LOOP_RMS / np.sqrt(np.mean(x * x)), -PEAK, PEAK)


def save(name, x):
  os.makedirs(OUT, exist_ok=True)
  pcm = (np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()
  subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(RATE), "-ac", "1", "-i", "-",
                  "-c:a", "libvorbis", "-q:a", "5", os.path.join(OUT, name + ".ogg")], input=pcm, check=True)
  print(f"{name}: {len(x) / RATE:.2f} s")


def main():
  # Loops.
  save("rain", at_loudness(loop(load("rain_inside_car_53318.mp3", 230, 31))))
  save("engine", at_loudness(loop(load("vehicle_interior_26577.mp3", 1, 31))))
  save("radio_music", at_loudness(loop(load("joropo_atlas_venezuela_562346.mp3", 0, 137.5, RADIO), 1.5)))
  save("radio_static", at_loudness(loop(load("radio_static_26831.mp3", 10, 11))))
  # Chewing with bones cracking under it, nine seconds in.
  feeding = load("creature_eating_482885.mp3", 0, 36.2)
  crunch = load("bone_crunching_102136.mp3")[:len(feeding) - 9 * RATE] * 0.5
  feeding[9 * RATE:9 * RATE + len(crunch)] += crunch
  save("feeding", at_loudness(loop(feeding)))

  # The radio searching in the dark before the first shot.
  save("radio_tuning", fade(at_loudness(load("tuning_radio_7150.mp3", 20, 9)), rise=0.5, tail=0.6))

  # One-shots.
  wiper = load("wiper_33418.mp3", 2, 4)
  save("wiper", at_peak(fade(wiper[onsets(wiper, gap=0.5)[0]:][:int(0.65 * RATE)], tail=0.15)))
  save("knock", at_peak(one_shot(load("knock_on_door_6228.mp3", 0, 2), 0.25)))
  save("door_kick", at_peak(one_shot(load("car_door_slamming_545188.mp3"), 1.2, tail=0.4)))
  save("thunder", at_peak(fade(load("thunder_city_377703.mp3", 0, 10), tail=2.0)))
  save("bones", at_peak(one_shot(load("rattling_bones_105394.mp3", 0.5, 4), 3.0, tail=0.6)))
  save("whistle", fade(at_peak(load("creepy_whistles_66703.mp3", 3, 8)), rise=0.4, tail=1.5))
  save("tinnitus", fade(at_peak(load("tinnitus_71519.mp3", 2, 9)), rise=0.05, tail=4.0))

  # The squeal runs up to the hit, which lands at CRASH_HIT; the car is in black right after.
  crash = load("car_accident_6054.mp3")
  hit = int(np.argmax(envelope(crash)))
  hit = onsets(crash[hit - RATE // 2:hit + 1], share=0.6)[0] + hit - RATE // 2
  CRASH_HIT = 1.0
  start = max(hit - int(CRASH_HIT * RATE), 0)
  save("crash", at_peak(fade(crash[start:hit + int(0.6 * RATE)], tail=0.25)))

  # Single keys out of a typing take, for the subtitles.
  typing = load("typewriter_typing_68696.mp3", 1, 8)
  keys = onsets(typing, gap=0.09, share=0.35)
  for i, key in enumerate(keys[:6]):
    save(f"key_{i + 1}", at_peak(fade(typing[max(key - 40, 0):key + int(0.07 * RATE)], tail=0.03)))


main()
