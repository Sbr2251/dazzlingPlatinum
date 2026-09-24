"""Builds res/sound/pl_sound_data/Files/SEQ/SEQ_PL_BA_TOTEM.mid, the Totem battle theme.

Usage: ~/.venvs/desmume/bin/python tools/totem_bgm/make_totem_bgm.py  (needs mido; safe to re-run)

Source: sm_vs_ultra_beast.mid, "Battle! VS Ultra Beast" (Pokemon Sun/Moon) sequenced by ShinkoNetCavy
(twitter.com/ShinkoNetCavy, youtube.com/user/ShinkoNet), who asks to be credited when remixing.

The output follows the conventions SDATTool's MIDI reader expects:
  - 48 ticks per beat, one MIDI track per channel, channels in ascending track order, tempo on the first track
  - every track opens with CC127, which SDATTool turns into "Poly 0" (poly mode). Without it a track stays in
    note-wait mode, where each note holds up the track until it ends, so chords smear and timing drifts
  - only controllers SDATTool maps (volume, pan, pitch bend range, priority) and explicit note-offs
  - the loop is a "Label_" text meta at the loop start and "Jump|Label_" + "TrackEnd" at the loop end
BANK_BGM_BATTLE does not follow the GM layout, so each GM program is mapped to the slot vanilla battle themes use
for the same role (bass, strings, guitar, ...). Its drum kit 1 does follow the GM key layout.
"""
import os

import mido

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "sm_vs_ultra_beast.mid")
OUT = os.path.join(HERE, "..", "..", "res/sound/pl_sound_data/Files/SEQ/SEQ_PL_BA_TOTEM.mid")

TPB = 48
# In source ticks (96 per beat): a 6-bar intro, then bars 6-49 repeat verbatim as bars 50-93.
LOOP_START = 6 * 4 * 96
LOOP_END = 50 * 4 * 96

DRUM_CHANNEL = 9
DRUM_KIT = 1
DRUM_RANGE = range(28, 89)
DRUM_MAX_LEN = TPB // 2  # drum samples are one-shots; long note-offs only eat voices

# Source GM program -> BANK_BGM_BATTLE instrument. None drops the channel.
PROGRAMS = {
    4: 29,  # electric piano -> piano (the Champion theme's piano)
    18: 17,  # rock organ -> sustained lead
    29: 20,  # overdrive guitar -> electric guitar (the Frontier Brain theme's guitar)
    30: 20,  # distortion guitar -> electric guitar
    35: 37,  # fretless bass -> bass (Galactic/legendary themes)
    38: 39,  # synth bass -> bass (Champion/Rival/Gym themes)
    48: 48,  # strings -> strings
    52: 60,  # choir -> sustained pad
    55: 81,  # orchestra hit -> orchestra hit
    80: 31,  # square lead -> PSG square wave
    81: 18,  # saw lead -> lead
    104: 14,  # sitar -> plucked keysplit
    122: None,  # seashore
}
PRIORITY = {0: 80, 5: 80, 1: 72, 2: 72}

EV_OFF, EV_LABEL, EV_CTRL, EV_ON = range(4)


def scale(tick):
    return round(tick * TPB / 96)


def collect(midi):
    """Returns {channel: [(abs source tick, message)]} and the tempo."""
    channels = {}
    tempo = 500000
    for track in midi.tracks:
        tick = 0
        for msg in track:
            tick += msg.time
            if msg.type == "set_tempo":
                tempo = msg.tempo
            elif not msg.is_meta and hasattr(msg, "channel"):
                channels.setdefault(msg.channel, []).append((tick, msg))
    return channels, tempo


def convert_channel(ch, events):
    """Returns [(new tick, order, message)] for one channel, or None if the channel is dropped."""
    out = []
    state = {"program": 0, 7: 100, 10: 64, 6: 2, "bend": 0}
    at_loop = None
    rpn = [127, 127]
    open_notes = {}

    def note_off(note, start, end):
        end = min(end, LOOP_END)
        if ch == DRUM_CHANNEL:
            end = min(end, start + DRUM_MAX_LEN * 2)
        out.append((max(scale(end), scale(start) + 1), EV_OFF, mido.Message("note_off", channel=ch, note=note)))

    for tick, msg in sorted(events, key=lambda e: e[0]):
        if at_loop is None and tick >= LOOP_START:
            at_loop = dict(state)
        if tick >= LOOP_END:
            break
        if msg.type == "note_on" and msg.velocity:
            if ch == DRUM_CHANNEL and msg.note not in DRUM_RANGE:
                continue
            open_notes.setdefault(msg.note, []).append(tick)
            out.append((scale(tick), EV_ON, msg.copy(time=0)))
        elif msg.type in ("note_on", "note_off"):
            if open_notes.get(msg.note):
                note_off(msg.note, open_notes[msg.note].pop(0), tick)
        elif msg.type == "program_change":
            if ch == DRUM_CHANNEL:
                program = DRUM_KIT
            else:
                program = PROGRAMS[msg.program]
                if program is None:
                    return None
            state["program"] = program
            out.append((scale(tick), EV_CTRL, mido.Message("program_change", channel=ch, program=program)))
        elif msg.type == "control_change":
            if msg.control in (100, 101):
                rpn[msg.control - 100] = msg.value
            elif msg.control == 6 and rpn == [0, 0]:
                state[6] = msg.value
                out.append((scale(tick), EV_CTRL, msg.copy(time=0)))
            elif msg.control in (7, 10):
                state[msg.control] = msg.value
                out.append((scale(tick), EV_CTRL, msg.copy(time=0)))
        elif msg.type == "pitchwheel":
            state["bend"] = msg.pitch
            out.append((scale(tick), EV_CTRL, msg.copy(time=0)))

    for note, starts in open_notes.items():
        for start in starts:
            note_off(note, start, LOOP_END)

    # Re-assert the loop-start state after the label, since the jump arrives with the loop-end state.
    loop = scale(LOOP_START)
    label = f"Label_Loop{ch}"
    out.append((loop, EV_LABEL, mido.MetaMessage("text", text=label)))
    s = at_loop or state
    for msg in (
        mido.Message("program_change", channel=ch, program=s["program"]),
        mido.Message("control_change", channel=ch, control=7, value=s[7]),
        mido.Message("control_change", channel=ch, control=10, value=s[10]),
        mido.Message("control_change", channel=ch, control=6, value=s[6]),
        mido.Message("pitchwheel", channel=ch, pitch=s["bend"]),
    ):
        out.append((loop, EV_LABEL, msg))

    out.append((0, -2, mido.Message("control_change", channel=ch, control=127, value=0)))
    out.append((0, EV_CTRL, mido.Message("control_change", channel=ch, control=22, value=PRIORITY.get(ch, 64))))

    end = scale(LOOP_END)
    out.append((end, EV_ON + 1, mido.MetaMessage("text", text=f"Jump|{label}")))
    out.append((end, EV_ON + 2, mido.MetaMessage("text", text="TrackEnd")))
    return out


def build():
    src = mido.MidiFile(SRC, clip=True)
    assert src.ticks_per_beat == 96
    channels, tempo = collect(src)

    midi = mido.MidiFile(type=1, ticks_per_beat=TPB)
    for ch in sorted(channels):
        events = convert_channel(ch, channels[ch])
        if events is None:
            continue
        if not midi.tracks:
            events.insert(0, (0, -1, mido.MetaMessage("set_tempo", tempo=tempo)))
        events.sort(key=lambda e: (e[0], e[1]))
        track = mido.MidiTrack()
        now = 0
        for tick, _, msg in events:
            track.append(msg.copy(time=tick - now))
            now = tick
        track.append(mido.MetaMessage("end_of_track", time=0))
        midi.tracks.append(track)
    return midi


def main():
    midi = build()
    midi.save(OUT)
    print(f"wrote {os.path.relpath(OUT)} ({len(midi.tracks)} tracks, {os.path.getsize(OUT)} bytes)")


if __name__ == "__main__":
    main()
