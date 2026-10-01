# strm_encoder: streamed music (.strm) for the SDAT

Pure-Python tools (no dependencies) for making NitroSystem `.strm` files and registering them
in `res/sound/pl_sound_data` so the game can play them with `NNS_SndArcStrm*`
(NitroSystem `libraries/snd/src/sndarc_stream.c`).

## Scripts

| Script | What it does |
| --- | --- |
| `wav2strm.py` | WAV -> `.strm` encoder (IMA-ADPCM default, PCM16/PCM8 optional), loop points, resampling, normalizing |
| `strm2wav.py` | `.strm` -> WAV decoder that mirrors NNS `MakeWaveData`; use it to listen to what the game will play |
| `strmlib.py` | Shared library: STRM reader/writer, IMA-ADPCM codec, header validation, NNS player model, resampler |
| `selftest.py` | Encoder/decoder self-test (header fields, SNR, sample-exact loops, offset starts, resampler) |
| `make_test_stream.py` | Re-synthesizes the placeholder `STRM_TEST_LOOP.strm` (deterministic, about 1 min) |
| `verify_sdat.py` | Compares a baseline SDAT with a rebuilt one: only stream data may change |

### wav2strm.py

    python3 tools/strm_encoder/wav2strm.py in.wav out.strm [--rate 22050] [--format adpcm|pcm16|pcm8]
            [--loop-start N] [--loop-end N] [--loop-align pad|trim] [--peak -1 | --rms -16]

- Input: PCM WAV, 1-6 channels, 8/16/24/32-bit integer. Channel order is kept.
  NNS pans a 2-channel stream hard left/right. For any other channel count the game code
  has to set the pans.
- Rate: the DS plays a stream at `523656 / timer` Hz, so `--rate` snaps to the nearest such
  rate (22050 -> 21819 Hz, timer 24; 32728 -> 32728 Hz, timer 16). The audio is resampled to
  that exact rate, so pitch and tempo stay correct.
- Loops: `--loop-start`/`--loop-end` take input samples, or seconds with an `s` suffix
  (`12.5s`). The file is cut at the loop end. Looping is only turned on when `--loop-start` is
  given. An IMA-ADPCM loop start must sit on a block boundary (every 1016 samples). `pad`
  (the default) adds up to 1015 samples of silence at the front so the loop stays
  sample-exact. `trim` drops those samples instead.
- Level: `--peak -1` (dBFS) or `--rms -16`. If you use neither, the level is left as it is.

Example:

    python3 tools/strm_encoder/wav2strm.py champion.wav \
        res/sound/pl_sound_data/Files/STRM/STRM_CHAMPION.strm --loop-start 4.25s --loop-end 92.0s --peak -1

### strm2wav.py

    python3 tools/strm_encoder/strm2wav.py in.strm out.wav [--loops 2] [--offset-ms 0]
    python3 tools/strm_encoder/strm2wav.py in.strm --info      # header only
    python3 tools/strm_encoder/strm2wav.py in.strm out.wav --linear   # raw blocks, no loop

### selftest.py / make_test_stream.py

    python3 tools/strm_encoder/selftest.py                 # prints "all passed"
    python3 tools/strm_encoder/make_test_stream.py --wav /tmp/strm_test_loop.wav \
        --out res/sound/pl_sound_data/Files/STRM/STRM_TEST_LOOP.strm

Keep intermediate WAVs out of git.

### verify_sdat.py

Builds an SDAT from the tree before your change and another from the tree after it, both with
the same SDATTool command that `res/sound/meson.build` uses. Then run the check. SDATTool needs
`mido`. On macOS, `/usr/bin/python3` has it; otherwise run `pip3 install --user mido`. The
SDATTool `gen4` checkout is the one `subprojects/SDATTool.wrap` points at (for example
`subprojects/SDATTool` after `meson subprojects download`).

    BASE=<commit before the change>
    rm -rf /tmp/sd && mkdir -p /tmp/sd/base /tmp/sd/new /tmp/sd/bf_base /tmp/sd/bf_new
    git archive $BASE res/sound | tar -x -C /tmp/sd/base
    git archive HEAD  res/sound | tar -x -C /tmp/sd/new
    cd <SDATTool checkout>/SDATTool
    for v in base new; do
        timeout 900 /usr/bin/python3 __main__.py -b /tmp/sd/$v.sdat \
            /tmp/sd/$v/res/sound/pl_sound_data -bf /tmp/sd/bf_$v/pl_sound_data
    done
    cd -
    python3 tools/strm_encoder/verify_sdat.py /tmp/sd/base.sdat /tmp/sd/new.sdat \
        --src /tmp/sd/new/res/sound/pl_sound_data

Each build takes a few seconds. The script checks:

- the SEQ/SEQARC/BANK/WAVARC/PLAYER/GROUP INFO records are byte-identical, with the same
  SYMB names;
- every non-STRM file is unchanged and keeps its file ID;
- the STRM files come after all the other files;
- `player2Info`/`strmInfo` decode to the values in `InfoBlock.json`;
- every embedded `.strm` is byte-identical to its source and has a valid header;
- each stream's player has enough channels for it.

It exits with a non-zero code if any check fails.

## Registering a new stream (5 files)

Example: `STRM_CHAMPION` on the existing BGM stream player.

1. **The file**: `res/sound/pl_sound_data/Files/STRM/STRM_CHAMPION.strm` (from `wav2strm.py`).

2. **`res/sound/pl_sound_data/InfoBlock.json`**: append to `strmInfo`:

   ```json
   {
       "name": "STRM_CHAMPION",
       "fileName": "STRM_CHAMPION.strm",
       "unkA": 0,
       "vol": 127,
       "pri": 64,
       "ply": 0,
       "reserved": [0,0,0,0,0]
   }
   ```

   Field mapping to `NNSSndArcStrmInfo` (`include/nnsys/snd/sndarc.h`), 12 bytes on disk:
   - `fileName` + `unkA` = `u32 fileId`. SDATTool writes the low 16 bits as the file's index in
     `FileBlock.json` and the high 16 bits as `unkA`, so `unkA` must be 0.
   - `vol` = `volume` (0-127). `pri` = `playerPrio`. `ply` = `playerNo`, the index into
     `player2Info`, as a number (not a name).
   - `reserved[0]` = `flags`. Bit 0 is `NNS_SND_ARC_STRM_FORCE_STEREO`, which plays a mono
     file on 2 channels. The other 4 bytes are padding.

   Stream players live in `player2Info`, one record per player (`NNSSndArcStrmPlayerInfo`,
   24 bytes). There can be up to 4 (`NNS_SND_STRM_PLAYER_NUM`); `NNS_SndArcStrmSetupPlayer`
   skips any player that has no record. The current one:

   ```json
   {
       "name": "STRM_PLAYER_BGM",
       "count": 2,
       "v": [4,5,255,255,255,255,255,255,255,255,255,255,255,255,255,255],
       "reserved": [0,0,0,0,0,0,0]
   }
   ```

   - `count` = `numChannels`. `v` = `chNoList[16]`, the hardware channels; unused slots are
     0xFF.
   - NNS only reads the first `count` slots, and copies at most 6 of them
     (`STRM_CHANNEL_MAX`).
   - A stream with more channels than its player is cut down to the player's count, so a
     4-channel layered stream needs a player with `count` 4 (for example channels 4-7).
   - The BGM sequence player owns channels 0-10 (`allocChBitFlag` 0x07FF), so the game must
     mask the stream channels out with `NNS_SndPlayerSetAllocatableChannel` while a stream
     plays.
   - Each player takes `512 * 4 * count` bytes of sound heap (`BLOCK_SIZE * BLOCK_NUM`) in
     `NNS_SndArcStrmSetupPlayer`.

3. **`res/sound/pl_sound_data/FileBlock.json`**: append at the **end** of `file`:

   ```json
   {
       "name": "STRM_CHAMPION.strm",
       "type": "STRM",
       "MD5": "<md5 of the .strm>"
   }
   ```

   The order of this list is the FAT order, so it sets the file IDs. Every info record looks its
   file up by name, but appending keeps every existing file ID the same, and that is what
   `verify_sdat.py` checks. SDATTool copies `.strm` files as they are, from `Files/STRM/<name>`.
   It only uses the MD5 for `-o` de-duplication, but keep it correct (`md5 -q` / `md5sum`).

4. **`res/sound/meson.build`**: add `strm_folder / 'STRM_CHAMPION.strm',` to `sdat_resources`
   (`strm_folder` is already defined). If you skip this, meson won't rebuild the SDAT when the
   file changes.

5. **`generated/sdat.txt`**: add `STRM_CHAMPION` to the stream section at the end. The
   section starts at `STRM_TEST_LOOP = 0`, and its order must match `strmInfo`. Stream
   players have their own section (`STRM_PLAYER_BGM = 0`), which must match `player2Info`.
   metang turns this file into the `SDATID` enum (`generated/sdat.h`), where each `= 0`
   restarts the numbering.

Then run `verify_sdat.py` as shown above.

## ROM cost

IMA-ADPCM stores 1016 samples in every 512-byte block (4-byte header plus 1016 nibbles), which
works out to 0.504 bytes per sample per channel. The table shows the actual DS rates. MB is
10^6 bytes, MiB is 2^20 bytes.

| Rate (timer) | Channels | IMA-ADPCM MB/min | MiB/min | PCM16 MiB/min (for comparison) |
| --- | --- | --- | --- | --- |
| 21819 Hz (24) "22050" | 1 (mono) | 0.66 | 0.63 | 2.50 |
| 21819 Hz (24) "22050" | 2 (stereo) | 1.32 | 1.26 | 4.99 |
| 21819 Hz (24) "22050" | 4 (layers) | 2.64 | 2.52 | 9.99 |
| 32728 Hz (16) | 1 (mono) | 0.99 | 0.94 | 3.75 |
| 32728 Hz (16) | 2 (stereo) | 1.98 | 1.89 | 7.49 |
| 32728 Hz (16) | 4 (layers) | 3.96 | 3.78 | 14.98 |

For scale:

- the whole sequenced `pl_sound_data.sdat` is about 8.0 MB;
- `STRM_TEST_LOOP.strm` (2.5 s intro + 20 s loop, stereo at 21819 Hz) is 495,224 bytes;
- a 2-minute stereo theme at 21819 Hz is about 2.6 MB.

Only the part up to the loop end is stored, so a short intro plus one loop pass is all the
ROM pays for.
