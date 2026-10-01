"""Adds the adaptive-music intensity layer to the wild battle theme (SEQ_BA_POKE, SEQ_BATTLE_WILD_POKEMON).

Usage: /usr/bin/python3 tools/battle_layers/add_intensity_layer.py   (needs mido; safe to re-run)

The layer is one extra MIDI track on channel 11, which SDATTool turns into sequence track 11. It is a
percussion ostinato on the song's own drum kit (program 1 of BANK_BGM_BATTLE), so no new samples:
  - 16th-note closed hi-hats (kit note 42) with accents on the 8ths
  - a descending tom fill (kit notes 47/45/43/41) on the last beat of bars 17, 25 and 33
  - rests through the drum break (bars 37-39), then a rising tom roll in bar 40 back into the drums
It only plays inside the loop (from tick 1920); the intro is silent, so the few frames before the game
holds the track silent can't be heard. In game src/sound_layers.c keeps track 11 at track volume 0
(NNS_SndPlayerSetTrackVolume) and fades it in when a layer turns on. The track's own volume stays normal
because track volume can only attenuate. Its priority is lowered (CC 22 -> SSEQ Priority) so its notes
never take a hardware channel from the base arrangement.

The script also refreshes the sequence's FileBlock.json MD5 (the MD5 of the .mid, as
tools/totem_bgm/import_totem_bgm.py does).
"""
import hashlib
import json
import os

import mido

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
DATA = os.path.join(ROOT, "res/sound/pl_sound_data")
SEQ = "SEQ_BA_POKE"
MIDI_PATH = os.path.join(DATA, "Files", "SEQ", f"{SEQ}.mid")

LAYER_CHANNEL = 11
BAR = 192  # 4/4 at 48 ticks per quarter note
STEP = BAR // 16
LOOP_START_BAR = 10  # tick 1920, the song's loop point
LOOP_END_BAR = 54  # tick 10368, where every track jumps back
FILL_BARS = (17, 25, 33)
REST_BARS = (37, 38, 39)
ROLL_BAR = 40

DRUM_KIT = 1
HAT = 42
TOMS = (47, 45, 43, 41)
HAT_LEN = 10
TOM_LEN = 12

LOOP_LABEL = "Label_0x1F00"
SUB_HATS = "Label_0x1F10"
SUB_HATS_FILL = "Label_0x1F20"


def hat_velocity(step):
    if step % 4 == 0:
        return 96
    if step % 2 == 0:
        return 84
    return 68


def bar_hats():
    return [(step * STEP, HAT, hat_velocity(step), HAT_LEN) for step in range(16)]


def bar_hats_fill():
    notes = [n for n in bar_hats() if n[0] < 12 * STEP]
    for i in range(4):
        tom = TOMS[i]
        notes.append(((12 + i) * STEP, tom, 104, TOM_LEN))
    return notes


def bar_roll():
    notes = []
    for step in range(16):
        tom = TOMS[0] if step < 4 else TOMS[1] if step < 8 else TOMS[2] if step < 12 else TOMS[3]
        notes.append((step * STEP, tom, 56 + step * 4, TOM_LEN))
    return notes


def build_events():
    """Returns (absolute tick, order, message) tuples for the layer track."""
    events = []
    order = 0

    def add(tick, msg):
        nonlocal order
        events.append((tick, order, msg))
        order += 1

    ch = LAYER_CHANNEL
    add(0, mido.Message("control_change", channel=ch, control=127, value=ch))  # SSEQ Poly 0, like every track
    add(0, mido.Message("control_change", channel=ch, control=7, value=112))  # Volume
    add(0, mido.Message("control_change", channel=ch, control=10, value=76))  # Pan
    add(0, mido.Message("control_change", channel=ch, control=22, value=32))  # Priority, below the default 64
    add(0, mido.Message("program_change", channel=ch, program=DRUM_KIT))

    loop_start = LOOP_START_BAR * BAR
    add(loop_start, mido.MetaMessage("text", text=LOOP_LABEL))

    for bar in range(LOOP_START_BAR, LOOP_END_BAR):
        start = bar * BAR

        if bar in REST_BARS:
            continue

        if bar == ROLL_BAR:
            notes, sub = bar_roll(), None
        elif bar in FILL_BARS:
            notes, sub = bar_hats_fill(), SUB_HATS_FILL
        else:
            notes, sub = bar_hats(), SUB_HATS

        # A bar in braces becomes one SSEQ subroutine that every copy of the bar calls
        if sub is not None:
            add(start, mido.MetaMessage("text", text="{"))
            add(start, mido.MetaMessage("text", text=sub))

        for offset, note, velocity, length in notes:
            add(start + offset, mido.Message("note_on", channel=ch, note=note, velocity=velocity))
            add(start + offset + length, mido.Message("note_off", channel=ch, note=note, velocity=velocity))

        if sub is not None:
            add(start + BAR, mido.MetaMessage("text", text="}"))

    loop_end = LOOP_END_BAR * BAR
    add(loop_end, mido.MetaMessage("text", text=f"Jump|{LOOP_LABEL}"))
    add(loop_end, mido.MetaMessage("text", text="TrackEnd"))
    return events


def to_track(events):
    # Stable sort by tick: a note_off at a bar line stays ahead of the bar's closing brace
    track = mido.MidiTrack()
    last = 0
    for tick, _, msg in sorted(events, key=lambda e: (e[0], e[1])):
        track.append(msg.copy(time=tick - last))
        last = tick
    track.append(mido.MetaMessage("end_of_track", time=0))
    return track


def track_channel(track):
    channels = [msg.channel for msg in track if hasattr(msg, "channel")]
    return channels[-1] if channels else None


def main():
    midi = mido.MidiFile(MIDI_PATH)
    tracks = [t for t in midi.tracks if track_channel(t) != LAYER_CHANNEL]

    # SDATTool pairs MIDI tracks with sequence tracks in channel order, so the layer must come last
    assert all(track_channel(t) < LAYER_CHANNEL for t in tracks), "an existing track uses a higher channel"

    end_ticks = {sum(msg.time for msg in t) for t in tracks}
    assert end_ticks == {LOOP_END_BAR * BAR}, f"unexpected track lengths {end_ticks}"

    labels = {msg.text for t in tracks for msg in t if msg.type == "text"}
    assert not labels & {LOOP_LABEL, SUB_HATS, SUB_HATS_FILL}, "layer label names clash with the song's"

    tracks.append(to_track(build_events()))
    midi.tracks[:] = tracks
    midi.save(MIDI_PATH)

    path = os.path.join(DATA, "FileBlock.json")
    with open(path) as f:
        fileblock = json.load(f)
    digest = hashlib.md5(open(MIDI_PATH, "rb").read()).hexdigest()
    for entry in fileblock["file"]:
        if entry["name"] == f"{SEQ}.sseq":
            entry["MD5"] = digest
    with open(path, "w") as f:
        f.write(json.dumps(fileblock, indent=4))  # the file has no trailing newline

    print(f"{SEQ}: {len(tracks)} MIDI tracks, layer on channel {LAYER_CHANNEL}")


if __name__ == "__main__":
    main()
