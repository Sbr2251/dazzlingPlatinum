#!/usr/bin/env python3
"""WAV -> NDS .strm (NitroSystem stream) encoder. Pure Python.

  python3 tools/strm_encoder/wav2strm.py in.wav out.strm [--rate 22050] [--format adpcm|pcm16]
          [--loop-start N] [--loop-end N] [--loop-align pad|trim] [--peak -1 | --rms -16]

Input: PCM WAV, 1-6 channels (mono, stereo, 4-channel layers), 8/16/24/32-bit integer.
Channel order in the .strm is the WAV channel order (NNS pans a 2-channel stream hard L/R;
for other counts the engine has to set pans with NNS_SndArcStrmSetChannelPan).

Sample rate: the DS plays a stream at 523656 / timer Hz (hardware timer = header timer << 5),
so --rate is snapped to the nearest such rate (22050 -> 21819 Hz, timer 24; 32728 -> timer 16)
and the audio is resampled to that exact rate, keeping pitch and tempo right.

Loops: --loop-start / --loop-end are in input samples (suffix "s" for seconds, e.g. 12.5s).
The file is cut at the loop end. For IMA-ADPCM NNS can only restart decoding from a block
header, so the loop start must fall on a block boundary (every 1016 samples). By default
("pad") silence is added in front so it does (at most 1015 samples, ~47 ms at 21819 Hz), which
keeps the loop sample-exact; "trim" drops the samples before the boundary instead.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import strmlib as S  # noqa: E402


def parse_pos(text, rate):
    if text is None:
        return None
    if text.endswith("s"):
        return int(round(float(text[:-1]) * rate))
    return int(text)


def encode(channels, in_rate, rate=22050, fmt="adpcm", loop_start=None, loop_end=None,
           loop_align="pad", peak_db=None, rms_db=None, block_size=S.BLOCK_SIZE, log=print):
    """channels: per-channel sample lists at in_rate. loop_start/loop_end in input samples.
    Returns (strm bytes, StrmInfo, notes dict)."""
    fmt_id = {"adpcm": S.FORMAT_ADPCM, "pcm16": S.FORMAT_PCM16, "pcm8": S.FORMAT_PCM8}[fmt]
    timer = S.timer_for_rate(rate)
    out_rate = S.rate_for_timer(timer)
    n = len(channels[0])
    if loop_end is None or loop_end > n:
        loop_end = n
    if loop_start is not None and not 0 <= loop_start < loop_end:
        raise ValueError("loop start %d outside 0..%d" % (loop_start, loop_end))

    # resample; for a loop the right-hand filter context wraps to the loop start
    ratio = out_rate / in_rate
    res = []
    for ch in channels:
        body = ch[:loop_end]
        tail = ch[loop_start:loop_start + 64] if loop_start is not None else None
        res.append(S.resample(body, in_rate, out_rate, tail=tail))
    total = len(res[0])
    ls = int(round(loop_start * ratio)) if loop_start is not None else None
    if ls is not None and ls >= total:
        ls = total - 1

    # normalize
    gain = 1.0
    if peak_db is not None:
        pk = S.peak(res)
        if pk:
            gain = S.db_to_lin(peak_db) * 32767 / pk
    elif rms_db is not None:
        r = S.rms(res)
        if r:
            gain = S.db_to_lin(rms_db) * 32767 / r
    clipped = 0
    ints = []
    for ch in res:
        o = []
        for v in ch:
            v = int(round(v * gain))
            if v > 32767:
                v, clipped = 32767, clipped + 1
            elif v < -32768:
                v, clipped = -32768, clipped + 1
            o.append(v)
        ints.append(o)
    if clipped:
        log("warning: %d samples clipped after normalization" % clipped)

    # ADPCM loop alignment
    shift = 0
    bsamp = S.block_samples_for(fmt_id, block_size)
    if ls is not None and fmt_id == S.FORMAT_ADPCM and ls % bsamp:
        if loop_align == "pad":
            shift = (-ls) % bsamp
            ints = [[0] * shift + ch for ch in ints]
        elif loop_align == "trim":
            shift = -(ls % bsamp)
            ints = [ch[-shift:] for ch in ints]
        else:
            raise ValueError("bad loop alignment mode %r" % loop_align)
        ls += shift

    blob, info = S.build_strm(ints, fmt_id, timer, out_rate, loop_start=ls, block_size=block_size)
    notes = {"timer": timer, "exact_rate": out_rate, "gain_db": 20 * S.math.log10(gain) if gain else 0,
             "align_shift": shift, "clipped": clipped}
    return blob, info, notes


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("wav")
    ap.add_argument("strm")
    ap.add_argument("--rate", type=float, default=22050, help="target rate, snapped to 523656/n (default 22050)")
    ap.add_argument("--format", choices=("adpcm", "pcm16", "pcm8"), default="adpcm")
    ap.add_argument("--loop-start", help="loop start in input samples (or seconds with 's'); enables looping")
    ap.add_argument("--loop-end", help="loop end in input samples (or seconds); the file is cut here")
    ap.add_argument("--loop-align", choices=("pad", "trim"), default="pad")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--peak", type=float, help="normalize the peak to this dBFS (e.g. -1)")
    g.add_argument("--rms", type=float, help="normalize the RMS level to this dBFS (e.g. -16)")
    ap.add_argument("--block-size", type=int, default=S.BLOCK_SIZE, help=argparse.SUPPRESS)
    a = ap.parse_args()

    in_rate, channels = S.read_wav(a.wav)
    if len(channels) > S.NNS_MAX_CHANNELS:
        sys.exit("error: %d channels; NNS streams support at most %d" % (len(channels), S.NNS_MAX_CHANNELS))
    blob, info, notes = encode(channels, in_rate, a.rate, a.format, parse_pos(a.loop_start, in_rate),
                               parse_pos(a.loop_end, in_rate), a.loop_align, a.peak, a.rms, a.block_size)
    problems = S.validate(blob)
    if problems:
        sys.exit("internal error, invalid STRM: " + "; ".join(problems))
    with open(a.strm, "wb") as f:
        f.write(blob)
    secs = info.loop_end / notes["exact_rate"]
    print("%s: %s %dch, %d Hz (timer %d, exact %.2f Hz), %d samples (%.2f s), %s, %d bytes (%.2f MB/min)"
          % (a.strm, S.FORMAT_NAMES[info.format], info.channels, info.sample_rate, info.timer,
             notes["exact_rate"], info.loop_end, secs,
             ("loop %d..%d" % (info.loop_start, info.loop_end)) if info.loop_flag else "no loop",
             len(blob), len(blob) / 1048576.0 / secs * 60))
    if notes["align_shift"]:
        print("  loop start aligned to a block: %+d samples at the start" % notes["align_shift"])
    if a.peak is not None or a.rms is not None:
        print("  gain %+.2f dB" % notes["gain_db"])


if __name__ == "__main__":
    main()
