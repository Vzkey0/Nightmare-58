"""Builds game/audio from the CC0 packs listed in game/audio/CREDITS.md.

Usage: python build_sfx.py <folder with the packs unpacked> (needs numpy and ffmpeg)

Each sound is cut or layered here, so a sound can be redone by changing one line. Layers are
aligned on their attack and mixed at the gain beside them, in dB. A set of variants shares one
level, printed at the end; volume_db in the scenes starts from it.
"""
import glob
import os
import subprocess
import sys

import numpy as np

RATE = 44100
PACKS = sys.argv[1]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "game", "audio")
PEAK = 10 ** (-1 / 20) # Head room left on the loudest variant of a set.
ONSET = 0.3            # Share of the peak that marks an attack.

RPG = "x_kenney_rpg-audio/Audio/"
IMPACT = "x_kenney_impact-sounds/Audio/"
INTERFACE = "x_kenney_interface-sounds/Audio/"
OWLISH = "x_Owlish_Media_Sound_Effects/"
ROCK = "x_sfx_breaking_and_falling/"
WET = "x_sfx_100_v2/sfx100v2_footstep_wet_0%d.ogg"
BONE = "x_deep_breaks/Deep Break %d.wav"
BLANKET = OWLISH + "Cloth, Rustle/%s__owlstorm__blanket-movement-%d.wav"

# Starts of clean takes in the Medieval pack's recordings, in seconds: the two blades closest to a
# machete for the light cuts and the axe for the weight of the heavy ones.
LIGHT_TAKES = (("Seax", 0.34), ("Seax", 4.05), ("Seax", 6.94), ("Seax", 8.72), ("Katana", 0.36), ("Katana", 5.78))
HEAVY_TAKES = (("Axe", 2.36), ("Axe", 3.16), ("Axe", 5.07), ("Axe", 5.89))


def find(path):
  return glob.glob(os.path.join(PACKS, "**", path) if "*" in path else os.path.join(PACKS, path), recursive=True)[0]


def load(path, cut=""):
  command = ["ffmpeg", "-v", "error", "-i", find(path), "-ac", "1", "-ar", str(RATE)]
  if cut:
    command += ["-af", cut]
  raw = subprocess.run(command + ["-f", "f32le", "-"], capture_output=True, check=True).stdout
  return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


def envelope(x):
  window = RATE // 200
  return np.sqrt(np.convolve(x * x, np.ones(window) / window, "same"))


def onset(x):
  level = envelope(x)
  return int(np.argmax(level >= level.max() * ONSET))


def fade(x, length, tail=0.08):
  x = x[:int(length * RATE)].copy()
  count = min(int(tail * RATE), len(x))
  x[-count:] *= np.linspace(1, 0, count) ** 2
  rise = int(0.002 * RATE)
  x[:rise] *= np.linspace(0, 1, rise)
  return x


def layered(length, *layers):
  """Each layer is (path, gain in dB) or (path, gain, ffmpeg filter)."""
  out = np.zeros(int(length * RATE))
  lead = int(0.005 * RATE)
  for path, gain, *cut in layers:
    x = load(path, *cut)
    x = x[max(onset(x) - lead, 0):] / np.abs(x).max()
    count = min(len(x), len(out))
    out[:count] += x[:count] * 10 ** (gain / 20)
  return fade(out, length)


def punch(x, drive=6):
  """Saturates the peaks, so a sound with a sharp attack holds up at game volume."""
  return np.tanh(x / np.abs(x).max() * 10 ** (drive / 20))


def take(name, start, length):
  """One swing out of a long recording, with its rumble of air on the microphone filtered away."""
  x = load("x_med*/%s Swing.wav" % name, "highpass=f=220,highpass=f=220")
  begin = int(start * RATE)
  x = x[max(begin - int(0.1 * RATE), 0):begin + int(0.9 * RATE)]
  level = envelope(x)
  x = x[max(int(np.argmax(level >= level.max() * 0.1)) - int(0.02 * RATE), 0):]
  return fade(x, length, 0.15)


def cloth(number, stamp, length):
  """The loudest stretch of a blanket being moved."""
  x = load(BLANKET % (stamp, number), "highpass=f=140")
  start = max(int(np.argmax(envelope(x))) - int(0.3 * length * RATE), 0)
  x = fade(x[start:], length, 0.2)
  rise = int(0.06 * RATE)
  x[:rise] *= np.linspace(0, 1, rise)
  return x


def loudest(x):
  """The strongest 50 ms: a short sound's level, which its length would pull down on average."""
  window = RATE // 20
  return float(np.sqrt(np.convolve(x * x, np.ones(window) / window, "same").max()))


def write(group, names, clips):
  """Evens a set of variants and writes it, printing the set's level."""
  clips = [c / loudest(c) for c in clips]
  scale = PEAK / max(np.abs(c).max() for c in clips)
  os.makedirs(os.path.join(OUT, group), exist_ok=True)
  for name, clip in zip(names, clips):
    command = ["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(RATE), "-ac", "1", "-i", "-",
               "-c:a", "libvorbis", "-q:a", "6", os.path.join(OUT, group, name + ".ogg")]
    subprocess.run(command, input=(clip * scale).astype(np.float32).tobytes(), check=True)
  print(f"{group}/{names[0]:14s} x{len(names)} level {20 * np.log10(scale):6.1f} dB  length {max(len(c) for c in clips) / RATE:.2f} s")


def numbered(name, clips):
  write("player", ["%s_%d" % (name, i + 1) for i in range(len(clips))], clips)


numbered("swing", [punch(take(n, s, 0.42), 10) for n, s in LIGHT_TAKES])
numbered("swing_heavy", [punch(take(n, s, 0.62), 10) for n, s in HEAVY_TAKES])

# The blade, the bone giving way under it and the weight of the blow.
numbered("hit", [punch(layered(0.55,
  (BONE % bone, 0),
  (RPG + "chop.ogg", -5),
  (RPG + "knifeSlice2.ogg", -9),
  (IMPACT + "impactPunch_heavy_00%d.ogg" % body, -6),
)) for bone, body in ((1, 0), (2, 1), (3, 2), (8, 3), (10, 4))])

# The ground breaking, under the blade's ring and a low blow that carries it.
numbered("slam", [layered(1.0,
  (IMPACT + "impactMining_00%d.ogg" % mining, 0),
  (ROCK + "bfh1_rock_breaking_0%d.ogg" % rock, -7),
  (IMPACT + "impactMetal_heavy_00%d.ogg" % metal, -8),
  (IMPACT + "impactSoft_heavy_00%d.ogg" % soft, -3),
) for mining, rock, metal, soft in ((0, 2, 1, 0), (1, 3, 3, 1), (4, 1, 0, 2))])

numbered("roll", [cloth(4, 320142, 0.65), cloth(6, 320144, 0.65), cloth(5, 320143, 0.65)])

numbered("roll_land", [layered(0.42,
  (RPG + "dropLeather.ogg", 0),
  (IMPACT + "impactSoft_heavy_00%d.ogg" % soft, -6),
) for soft in (0, 1, 3)])

# A shoe on the pavement and the film of water under it: the avenue is always wet.
numbered("step", [punch(layered(0.34,
  (OWLISH + "Footsteps/%s.wav" % shoe, 0, "highpass=f=70"),
  (WET % wet, -8),
)) for shoe, wet in (("step1", 1), ("step2", 2), ("step3", 3), ("step4", 2), ("hard-footstep1", 3), ("hard-footstep4", 1))])

# Bronze and paper instead of beeps, to match the metal plates of the menus.
write("ui", ["move"], [layered(0.12, (RPG + "metalClick.ogg", 0, "highpass=f=500"))])
write("ui", ["adjust"], [layered(0.1, (INTERFACE + "tick_004.ogg", 0))])
write("ui", ["accept"], [layered(0.3, (RPG + "metalLatch.ogg", 0), (RPG + "bookPlace1.ogg", -7))])
write("ui", ["back"], [layered(0.2, (RPG + "bookClose.ogg", 0))])
write("ui", ["tab"], [layered(0.3, (RPG + "bookFlip2.ogg", 0))])
write("ui", ["open"], [layered(0.3, (RPG + "bookFlip3.ogg", -2), (RPG + "bookOpen.ogg", 0))])
write("ui", ["close"], [layered(0.26, (RPG + "bookPlace3.ogg", 0))])
write("ui", ["deny"], [layered(0.3, (IMPACT + "impactTin_medium_000.ogg", 0, "lowpass=f=2500"))])
