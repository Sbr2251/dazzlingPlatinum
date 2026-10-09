# Streamed, Adaptive Soundtrack with Live Audio Effects: Feasibility and Agent-Team Plan

Branch: `feat/adaptive-streamed-soundtrack` (cut from `main`)
Effort: L

## 1. Feasibility verdict

**It can be done.** Every engine piece already exists. What's missing is tooling, glue code and audio assets. Details below; file references are from this repo or from the NitroSystem/SDATTool subprojects.

| Claim in the feature brief | Verified? | Notes |
|---|---|---|
| The sound library's streaming code is already there | **Yes, with a nuance** | The low-level `NNS_SndStrm*` is linked today (used by `src/nintendo_wfc/voice_chat.c`). The SDAT stream player, `NNS_SndArcStrm*` (file-streaming thread, IMA-ADPCM decode, loop handling, per-channel volume), is fully decompiled in `NitroSystem/libraries/snd/src/sndarc_stream.c`. It isn't in the ROM yet only because nothing calls it; `libnnssnd.a` is already in `platinum.us/main.lsf`, so the linker picks it up once we call it. |
| The stream list in InfoBlock.json is empty | **Yes** | `strmInfo` = 0 entries. `player2Info`, the stream players, is **also empty**, and `NNS_SndArcStrmSetupPlayer` skips players that have no `player2Info`. We need to add at least one. |
| The sound-archive tool already supports adding streams | **Partly** | SDATTool (gen4 branch) reads and writes `STRMInfo`/`PLAYER2Info` and copies `Files/STRM/*.strm` **as-is**. It has **no WAV to STRM encoder**, so we have to write one (IMA-ADPCM with loop points). |
| Per-instrument volume and mute go into src/sound.c | **Yes** | `NNS_SndPlayerSetTrackMute`, `SetTrackMuteEx` and `SetTrackVolume` exist in NitroSystem `player.h`. `src/sound.c` already wraps the matching per-track Pitch/Pan calls. Multi-channel streams can also do layers with `NNS_SndArcStrmSetChannelVolume`. |
| Swap the existing low-pass filter for per-area effects | **Yes, but it isn't per-area today** | `Sound_Impl_FilterCallback` (a moving-average low-pass over `NNS_SndCaptureStartEffect`) is used **only by the Pokedex cry screen** (`src/applications/pokedex/crysub.c`). The title and ending use `NNS_SndCaptureStartReverb`. The capture unit can only do one thing at a time, so field effects must hand it over to the Pokedex, the title screen and battles. |

### Hard constraints the plan has to respect

1. **16 hardware channels.** Today's map: BGM player `0x07FF` (channels 0-10), SE players `0xD800` (11, 12, 14, 15), cries on WaveOut 14/15, and **channel 13 is unused**. Capture effects lock **channels 1 and 3**. A stereo stream needs 2 channels and a layered stream needs 4. Plan: while a stream plays, the BGM sequence is silent, so the stream player takes channels from the BGM range (for example 4, 5, 6, 7) and `NNS_SndPlayerSetAllocatableChannel(PLAYER_BGM, ...)` masks them out. The ME/fanfare player shares the BGM range and needs the same care.
2. **Streams can't pause.** There is no `NNS_SndArcStrmPause`. Fanfares that pause the BGM (item get, evolution and so on) must use `NNS_SndArcStrmGetCurrentPlayingPos`, then stop, then `NNS_SndArcStrmStart(..., offset)` to resume.
3. **ROM size.** IMA-ADPCM stereo costs about 1.3 MB/min at 22 kHz and about 1.9 MB/min at 32 kHz. The hack's current ROM size has to be measured on the devserver (Phase 0) to set a minutes budget under the 128 MB cart limit.
4. **Cartridge bandwidth.** The stream thread reads through FS while maps and overlays load. Buffer underruns show up as stutter on hardware and melonDS long before DeSmuME shows them. Thread priority and the buffer count (`BLOCK_NUM`) need tuning, and testing must use an accurate emulator.
5. **The capture effect processes the whole mix,** SFX and cries included. That's fine (even good) for cave echo, but it's a design choice, and battles probably want it off.
6. **ARM9 CPU budget.** The callback runs every 2 frames at 22 kHz (`SOUND_FILTER_INTERVAL`, `SOUND_FILTER_SAMPLE_RATE`). An echo or warp delay line is about 1 multiply-add per sample; a 0.25 s stereo delay line is about 22 KB of RAM. Affordable, but it needs measuring in busy maps.
7. **Audio assets and rights.** "Real recorded audio" has to come from somewhere. **The user has to supply or approve the source recordings.** The pipeline gets built and tested with placeholder renders of the existing sequences.

## 2. Architecture

```
            +------------------ sound_playback.c (Sound_PlayBGM / StopBGM / Fade / fanfare pause)
            |                          |
            |               sound_stream.c  (NEW)  SEQ->STRM override table, start/stop/fade,
            |                          |             pause-by-offset, channel handoff
            |                          v
            |               NNS_SndArcStrm*  (NitroSystem, already decompiled)
            |
 battle ----+--> sound_layers.c (NEW)  Sound_SetBGMLayer(layer, on, fadeFrames)
 (low HP,   |        -> NNS_SndPlayerSetTrackVolume/Mute   (sequenced BGM)
  Mega,     |        -> NNS_SndArcStrmSetChannelVolume     (4-ch layered STRM)
  Totem)    |
 field  ----+--> sound_area_fx.c (NEW)  zone -> {NONE, ECHO, MUFFLE, WARP}
 map change          -> NNS_SndCaptureStartEffect(callback per mode); arbitration with
                        Pokedex filter + title/ending reverb + battle entry
```

Key design decision: **existing scripts keep calling `SEQ_*` IDs.** An override table (`SEQ_X -> STRM_X`) in `sound_stream.c` decides at play time whether to stream. Removing a row goes back to the synthesized version, so every theme can be rolled back on its own and no map or event script changes.

## 3. Agent team

Each agent runs in its **own git worktree** and owns separate files so merges don't conflict. The lead merges, builds on the devserver (`make release` in `/data/repos/dazzlingPlatinum`, one build at a time) and runs smoke tests.

| Agent | Owns (write access) | Delivers |
|---|---|---|
| **Lead / Integrator** (main session) | branch, merges, `CLAUDE.md` notes | Phase gates, devserver builds, py-desmume smoke runs, final push |
| **A. Stream Tooling** | `tools/strm_encoder/`, `res/sound/pl_sound_data/Files/STRM/`, `strmInfo`/`player2Info` in `InfoBlock.json`, `FileBlock.json`, `res/sound/meson.build`, `generated/sdat.txt` | WAV to `.strm` encoder (IMA-ADPCM, loop start/end, mono/stereo/4-channel), round-trip decoder for verification, import script in the style of `tools/totem_bgm/import_totem_bgm.py` |
| **B. Stream Engine** | `src/sound_stream.c`, `include/sound_stream.h`; small, reviewed hooks in `src/sound_system.c` and `src/sound_playback.c` | `NNS_SndArcStrmInit` at boot (thread priority, heap budget), override table, play/stop/fade/swap parity with the sequenced BGM, fanfare pause via offset, channel handoff |
| **C. Adaptive Layers** | `src/sound_layers.c`, `include/sound_layers.h`; hook calls in `src/battle/*`, `src/totem_battle.c`; layered battle `.mid` files | Layer API; triggers for player's HP at or below 25% (with hysteresis), Mega Evolution, Totem ally call; one sequenced battle theme rewritten with muted "intensity" tracks as proof |
| **D. Area FX** | `src/sound_area_fx.c`, `include/sound_area_fx.h`, filter section of `src/sound.c`, `include/sound_system.h`; zone-to-effect table; field map-change hook | Effect callbacks (echo = feedback delay; muffle = one-pole IIR low-pass, replacing the moving average; warp = modulated delay or ring-mod or pitch wobble); capture ownership rules; the Pokedex cry filter keeps working |
| **E. QA / Perf** | `tools/audio_qa/` (test harness only) | py-desmume scripts that load save states, trigger BGM, capture SPU output to WAV, and check stream start, loop, fanfare resume and the effect switch; ROM-size budget report; underrun and CPU notes for melonDS/hardware checks |

A and D can start on day one. B needs A's first `.strm`. C's battle hooks don't depend on B, but stream-based layers do.

## 4. Phases and gates

**Phase 0: Spike (Lead + A + B, about 1 day). Go/no-go.**
- Measure current ROM size, work out the minutes budget, and confirm the channel map at runtime.
- A: encode a 20 s looped test WAV (placeholder render of `SEQ_BA_CHANP`), add one `strmInfo` plus one `player2Info` (channels 4, 5).
- B: minimal `Sound_DebugPlayStream()` from a debug hook. Build on the devserver and confirm with py-desmume that it plays, loops, and doesn't crash with the Pokedex filter.
- **Gate:** a stream plays from the ROM, the ROM stays within budget, and the linker pulls in `sndarc_stream.o` without overlay or ITCM issues.

**Phase 1: Parallel build-out (A, B, C, D, E at once).**
- A: finished encoder, batch import, loudness normalization so streams match sequenced BGM levels.
- B: full parity with `Sound_PlayBGM`, `StopBGM`, `FadeToBGM`, `SwapBGM` and fanfare pause/resume; map transitions that keep the same BGM must not restart the stream.
- C: layer API plus the three battle triggers on one layered sequenced theme.
- D: the three effects, a zone table for caves, water and the Distortion World, and capture arbitration (effect off on battle entry, Pokedex, title/ending).
- E: harness plus regression saves (cave, surfing, Distortion World, a Totem battle, a Mega battle).

**Phase 2: Integration (Lead).** Merge in the order A, B, D, C. One devserver build after each merge, run E's suite, fix regressions.

**Phase 3: Content and polish.** Pick the "big themes" (proposal: title, Champion, Giratina/Distortion World, Totem, Elite Four), put them into the override table with approved recordings, and optionally add a 4-channel layered stream for the Totem theme. Test for underruns on hardware or melonDS, then push the branch.

## 5. Decisions needed from the user

1. **Where do the recordings come from?** Own or commissioned arrangements, or placeholders only for now.
2. **Which themes get streamed,** and the ROM budget in MB.
3. **"Water muffles":** while surfing, in specific water maps, or during rain?
4. **Should the area effects also apply in battles** that start in caves or the Distortion World?

## 6. Main risks

| Risk | Mitigation |
|---|---|
| Stream stutter during map loads | Raise the stream thread priority, increase `BLOCK_NUM` (costs heap), test on melonDS/hardware in Phase 3 |
| Channel theft (notes cut off, cries missing) | Reserve stream channels only while a stream is active; E checks with cries plus fanfare plus stream together |
| Sound heap exhaustion | Stream buffers are `512 * BLOCK_NUM * channels`; set aside a heap state for them in `sound_system.c` |
| Fanfare resume jumps or clicks | Resume from offset with a short fade-in; accept that resume snaps to ADPCM block granularity |
| Existing Pokedex/title audio breaks | Area FX only takes the capture unit when it's free and hands it back at scene boundaries |
