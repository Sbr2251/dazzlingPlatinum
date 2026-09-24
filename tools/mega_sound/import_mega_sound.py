"""Imports the Mega Evolution sound effects (SEQ_SE_MEGA_CHARGE and SEQ_SE_MEGA_BURST).

Usage: ~/.venvs/desmume/bin/python tools/mega_sound/import_mega_sound.py [mega-evolution.ogg] [--preview DIR]
(needs numpy, mido and ffmpeg; safe to re-run). Without an argument the clip is downloaded from SOURCE_URL.

Source and credit:
  - The sound is the Mega Evolution sound effect from the Pokemon games, by Nintendo, Game Freak,
    Creatures Inc. and The Pokemon Company.
  - The clip used is audio/se/mega-evolution.ogg from Pokemon Workshop's PSDK Technical Demo. It was added in
    https://github.com/PokemonWorkshop/PSDKTechnicalDemo/pull/21 and is pinned below at commit 1a6456a4.
  - Its tags credit the rip to Lumiose Sounds, https://www.youtube.com/watch?v=dZx-13hUhsg. That video is titled
    "Mega Evolution Sound Effect (Pokemon Let's go Pikachu/Eevee)", and its tags say #pokemonxy.

The clip is used as is, not resynthesised. It is 5 s long: a rising charge (0-3.54 s), then a crystalline burst
at 3.54 s whose sparkle tail decays by 5 s. It is cut in two so each half lines up with a step of the Mega
Evolution script (res/battle/scripts/subscripts/subscript_mega_evolution.s).

  - SEQ_SE_MEGA_CHARGE plays with the charge (AffinePulse 0 and ChangeForm). The script plays the burst 47
    frames after the charge (measured in battle), so this uses the last 47 frames (0.79 s) of the charge at
    its original speed: a fade-in over its quiet stretch, then the swell that peaks straight into the burst.
  - SEQ_SE_MEGA_BURST plays with the reveal (AffinePulse 1). The new form's cry starts about 6 frames later, so
    the burst keeps its full-level crack for 0.1 s and then ducks its tail 9 dB, leaving the cry on top.
  - Both are on PLAYER_SE_2 at the same priority, like the SEQ_SE_DP_W100/W107 pair they replace. Starting the
    burst therefore cuts off whatever is left of the charge.

Both halves are mono, high-passed at 150 Hz (the DS speakers cannot play the clip's rumble), resampled to
13379 Hz (the rate of vanilla battle SEs), normalised together so the burst stays louder than the charge, as
in the clip, and stored as IMA-ADPCM SWAVs in WAVE_ARC_SE_MEGA. BANK_SE_MEGA holds one Single instrument per SWAV
at its native pitch, and each sequence plays one note. The sequences are in GROUP_SE_BATTLE, so their bank and
wave archive are resident during battles.

The InfoBlock.json entries (seqInfo 1793/1794, bankInfo and wavarcInfo 707, GROUP_SE_BATTLE) and the
generated/sdat.txt names are maintained by hand. This script regenerates the files, their FileBlock.json
entries and their res/sound/meson.build lines. With --preview it also writes listening WAVs of the reference and
of the SWAVs as the DS decodes them.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
import wave

import mido
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
SOURCE_URL = ("https://raw.githubusercontent.com/PokemonWorkshop/PSDKTechnicalDemo/"
              "1a6456a48346f6f1a1d06c2d493d711d4e14acf1/audio/se/mega-evolution.ogg")
SOURCE_MD5 = "1a6737d9de2bc91c9dae644a12d5dd69"
SOUND = os.path.join(ROOT, "res/sound")
DATA = os.path.join(SOUND, "pl_sound_data")
FILES = os.path.join(DATA, "Files")

RATE = 13379
TIMER = 16756991 // RATE
BANK = "BANK_SE_MEGA"
WAVE_ARC = "WAVE_ARC_SE_MEGA"
BURST_AT = 3.54  # seconds into the clip
CHARGE_FRAMES = 47  # frames from the charge PlaySound to the burst PlaySound in subscript_mega_evolution.s
FPS = 59.8261

# name, SWAV/program index, clip window (s), fade in (s), fade out (s), rest before the note (ticks)
SOUNDS = [
    ("SEQ_SE_MEGA_CHARGE", 0, BURST_AT - CHARGE_FRAMES / FPS, BURST_AT, 0.25, 0.01, 0),
    ("SEQ_SE_MEGA_BURST", 1, BURST_AT - 0.005, BURST_AT + 0.70, 0.005, 0.30, 0),
]
BURST_DUCK = (0.10, 0.20, -9.0)  # full level until 0.10 s, then down 9 dB by 0.20 s
TICKS_PER_SECOND = 48 * 1000000 / 400000  # 48 ppq at 150 bpm


# --- IMA-ADPCM, as the DS sound hardware decodes it (GBATEK "DS Sound") ---
STEPS = [7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55, 60, 66, 73, 80, 88,
         97, 107, 118, 130, 143, 157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408, 449, 494, 544, 598, 658,
         724, 796, 876, 963, 1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066, 2272, 2499, 2749, 3024, 3327, 3660,
         4026, 4428, 4871, 5358, 5894, 6484, 7132, 7845, 8630, 9493, 10442, 11487, 12635, 13899, 15289, 16818,
         18500, 20350, 22385, 24623, 27086, 29794, 32767]
INDEX_STEP = [-1, -1, -1, -1, 2, 4, 6, 8]


def adpcm_step(pcm, index, nibble):
    step = STEPS[index]
    diff = step >> 3
    if nibble & 1:
        diff += step >> 2
    if nibble & 2:
        diff += step >> 1
    if nibble & 4:
        diff += step
    pcm = max(pcm - diff, -0x7FFF) if nibble & 8 else min(pcm + diff, 0x7FFF)
    return pcm, min(max(index + INDEX_STEP[nibble & 7], 0), 88)


def adpcm_encode(samples):
    """Returns the SWAV sample data: a 4-byte header, then one nibble per sample after the first."""
    samples = list(samples) + [0] * (-(len(samples) - 1) % 8)  # whole 32-bit words
    pcm, index = int(samples[0]), 0
    nibbles = []
    for target in samples[1:]:
        best = min(range(16), key=lambda n: abs(adpcm_step(pcm, index, n)[0] - target))
        pcm, index = adpcm_step(pcm, index, best)
        nibbles.append(best)
    body = bytes(nibbles[i] | nibbles[i + 1] << 4 for i in range(0, len(nibbles), 2))
    return int(samples[0]).to_bytes(2, "little", signed=True) + b"\0\0" + body


def adpcm_decode(data):
    pcm = int.from_bytes(data[:2], "little", signed=True)
    index = data[2]
    out = [pcm]
    for byte in data[4:]:
        for nibble in (byte & 15, byte >> 4):
            pcm, index = adpcm_step(pcm, index, nibble)
            out.append(pcm)
    return np.array(out, dtype=np.int16)


def swav(data):
    """Wraps IMA-ADPCM sample data in a one-shot SWAV (loop start after the ADPCM header word)."""
    info = bytes([2, 0]) + RATE.to_bytes(2, "little") + TIMER.to_bytes(2, "little") + (1).to_bytes(2, "little") \
        + (len(data) // 4 - 1).to_bytes(4, "little")
    block = b"DATA" + (8 + len(info) + len(data)).to_bytes(4, "little") + info + data
    return b"SWAV\xff\xfe\x00\x01" + (16 + len(block)).to_bytes(4, "little") + b"\x10\x00\x01\x00" + block


# --- audio ---
def decode(ogg, rate, highpass=True):
    """Returns the clip as mono floats at `rate`."""
    filters = ["-af", "highpass=f=150:poles=2"] if highpass else []
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", ogg, "-ac", "1", *filters, "-ar", str(rate),
                          "-f", "s16le", "-"], check=True, stdout=subprocess.PIPE).stdout
    return np.frombuffer(raw, np.int16).astype(np.float64) / 32768


def fade(n, rate, seconds):
    k = max(1, int(seconds * rate))
    return 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, min(k, n)))


def cut(clip, start, end, fade_in, fade_out, duck=None):
    x = clip[int(start * RATE):int(end * RATE)].copy()
    a = fade(len(x), RATE, fade_in)
    x[:len(a)] *= a
    b = fade(len(x), RATE, fade_out)[::-1]
    x[len(x) - len(b):] *= b
    if duck:
        t = np.arange(len(x)) / RATE
        hold, down, db = duck
        ramp = np.clip((t - hold) / (down - hold), 0, 1)
        x *= 10 ** (db * ramp / 20)
    return x


def write_wav(path, samples, rate):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(np.asarray(samples, dtype=np.int16).tobytes())


# --- sound archive files ---
def write_seq(path, program, rest, seconds):
    track = mido.MidiTrack()
    length = int(seconds * TICKS_PER_SECOND) + 4
    track += [
        mido.Message("control_change", channel=0, control=127, value=0, time=0),
        mido.MetaMessage("set_tempo", tempo=400000, time=0),
        mido.Message("program_change", channel=0, program=program, time=0),
        mido.Message("control_change", channel=0, control=7, value=127, time=0),
        mido.Message("note_on", channel=0, note=60, velocity=127, time=rest),
        mido.Message("note_off", channel=0, note=60, velocity=127, time=length),
        mido.MetaMessage("text", text="TrackEnd", time=1),
        mido.MetaMessage("end_of_track", time=0),
    ]
    mid = mido.MidiFile(type=1, ticks_per_beat=48)
    mid.tracks.append(track)
    mid.save(path)


def md5(path):
    return hashlib.md5(open(path, "rb").read()).hexdigest()


def update_file_block(swavs):
    path = os.path.join(DATA, "FileBlock.json")
    block = json.load(open(path))
    files = block["file"]
    names = [f["name"] for f in files]

    def upsert(entry, after):
        if entry["name"] in names:
            files[names.index(entry["name"])] = entry
        else:
            files.insert(names.index(after) + 1, entry)
            names.insert(names.index(after) + 1, entry["name"])

    after = "SEQ_SE_DP_KIRAN.sseq"
    for name, *_ in SOUNDS:
        upsert({"name": f"{name}.sseq", "type": "SEQ", "MD5": md5(os.path.join(FILES, "SEQ", f"{name}.mid"))}, after)
        after = f"{name}.sseq"
    upsert({"name": f"{BANK}.sbnk", "type": "BANK", "MD5": md5(os.path.join(FILES, "BANK", f"{BANK}.txt"))},
           "BANK_BGM_TOTEM.sbnk")
    upsert({"name": f"{WAVE_ARC}.swar", "type": "WAVARC", "MD5": hashlib.md5(b"".join(swavs)).hexdigest(),
            "subFile": [f"{i:02X}.swav" for i in range(len(swavs))]}, "WAVE_ARC_BGM_TOTEM.swar")
    open(path, "w").write(json.dumps(block, indent=4))


def update_meson(count):
    path = os.path.join(SOUND, "meson.build")
    names = [name for name, *_ in SOUNDS]
    lines = [l for l in open(path).read().splitlines()
             if BANK not in l and WAVE_ARC not in l and not any(f"'{n}.mid'" in l for n in names)]
    at = lines.index("    seq_folder / 'SEQ_SE_DP_KIRAN.mid',") + 1
    lines[at:at] = [f"    seq_folder / '{n}.mid'," for n in names]
    at = lines.index("    bank_folder / 'BANK_BGM_TOTEM.txt',") + 1
    lines.insert(at, f"    bank_folder / '{BANK}.txt',")
    at = max(i for i, l in enumerate(lines) if "'WAVE_ARC_BGM_TOTEM' /" in l) + 1
    lines[at:at] = [f"    wavarc_folder / '{WAVE_ARC}' / '{i:02X}.swav'," for i in range(count)]
    open(path, "w").write("\n".join(lines) + "\n")


def main():
    args = sys.argv[1:]
    preview = None
    if "--preview" in args:
        i = args.index("--preview")
        preview = args[i + 1]
        del args[i:i + 2]
    with tempfile.TemporaryDirectory() as tmp:
        ogg = args[0] if args else os.path.join(tmp, "mega-evolution.ogg")
        if not args:
            urllib.request.urlretrieve(SOURCE_URL, ogg)
        if md5(ogg) != SOURCE_MD5:
            print(f"warning: {ogg} is not the pinned clip (MD5 {md5(ogg)})")
        clip = decode(ogg, RATE)
        if preview:
            os.makedirs(preview, exist_ok=True)
            write_wav(os.path.join(preview, "reference_full_32k.wav"),
                      np.round(decode(ogg, 32000, highpass=False) * 32767), 32000)

    cuts = [cut(clip, start, end, fade_in, fade_out, BURST_DUCK if name.endswith("BURST") else None)
            for name, _, start, end, fade_in, fade_out, _ in SOUNDS]
    gain = 0.97 * 32767 / max(np.abs(x).max() for x in cuts)  # one gain keeps the burst louder than the charge
    swavs, bank = [], []
    for (name, index, start, end, fade_in, fade_out, rest), x in zip(SOUNDS, cuts):
        pcm = np.round(x * gain).astype(np.int32)
        data = adpcm_encode(pcm)
        swavs.append(swav(data))
        bank.append(f"{index}, Single, {index}, 0, 60, 127, 127, 127, 126, 64")
        write_seq(os.path.join(FILES, "SEQ", f"{name}.mid"), index, rest, len(pcm) / RATE)
        if preview:
            write_wav(os.path.join(preview, f"{name}_ds.wav"), adpcm_decode(data), RATE)
        print(f"{name}: {start:.3f}-{end:.3f} s of the clip, {len(pcm) / RATE:.2f} s, SWAV {len(swavs[-1])} bytes")

    open(os.path.join(FILES, "BANK", f"{BANK}.txt"), "w").write("\n".join(bank) + "\n")
    out = os.path.join(FILES, "WAVARC", WAVE_ARC)
    os.makedirs(out, exist_ok=True)
    for old in os.listdir(out):
        os.remove(os.path.join(out, old))
    for i, data in enumerate(swavs):
        open(os.path.join(out, f"{i:02X}.swav"), "wb").write(data)
    update_file_block(swavs)
    update_meson(len(swavs))
    # SDATTool never rebuilds a .swar that already exists in the build folder (its newest-SWAV check keeps
    # max_mtime at 0), so delete the built copy to make the next build pick up the new samples.
    stale = os.path.join(ROOT, "build", "res/sound", os.path.relpath(out, SOUND) + ".swar")
    if os.path.exists(stale):
        os.remove(stale)
        print(f"removed stale {os.path.relpath(stale, ROOT)}")
    print(f"{WAVE_ARC}: {len(swavs)} samples, {sum(map(len, swavs))} bytes")


if __name__ == "__main__":
    main()
