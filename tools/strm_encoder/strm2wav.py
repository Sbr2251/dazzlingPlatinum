#!/usr/bin/env python3
"""NDS .strm -> WAV decoder, for checking encoder output.

  python3 tools/strm_encoder/strm2wav.py in.strm out.wav [--loops 2] [--offset-ms 0] [--info]

Default mode plays the file through a re-implementation of NNS MakeWaveData
(sndarc_stream.c): same block/offset arithmetic, ADPCM state handling, start offset and loop
jump, so what you hear is what the game produces. --loops N renders the intro plus N passes of
the loop; --offset-ms starts where NNS_SndArcStrmStart(..., offset) would. --linear decodes the
blocks straight through instead (no loop). --info only prints the header.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import strmlib as S  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("strm")
    ap.add_argument("wav", nargs="?")
    ap.add_argument("--loops", type=int, default=2, help="loop passes to render (default 2)")
    ap.add_argument("--offset-ms", type=int, default=0)
    ap.add_argument("--linear", action="store_true")
    ap.add_argument("--info", action="store_true")
    a = ap.parse_args()

    blob = open(a.strm, "rb").read()
    info = S.parse_strm(blob)
    rate = S.rate_for_timer(info.timer) if info.timer else info.sample_rate
    print("%s: %s %dch, rate field %d Hz, timer %d (plays at %.2f Hz), %d samples (%.2f s), %s"
          % (a.strm, S.FORMAT_NAMES.get(info.format, info.format), info.channels, info.sample_rate,
             info.timer, rate, info.loop_end, info.loop_end / rate,
             ("loop start %d" % info.loop_start) if info.loop_flag else "no loop"))
    print("  blocks %d x %d bytes (%d samples), last %d bytes (%d samples), data at 0x%X, file %d bytes"
          % (info.num_blocks, info.block_size, info.block_samples, info.last_block_size,
             info.last_block_samples, info.data_offset, len(blob)))
    for p in S.validate(blob, info):
        print("  PROBLEM:", p)
    if a.info or not a.wav:
        return
    if a.linear:
        _, chans = S.decode_linear(blob)
    else:
        start = info.sample_rate * a.offset_ms // 1000
        n = info.loop_end - start
        if info.loop_flag:
            n += (info.loop_end - info.loop_start) * max(0, a.loops - 1)
        chans = S.NnsStrmPlayer(blob, a.offset_ms).render(n)
    S.write_wav(a.wav, rate, chans)
    print("wrote %s (%d samples)" % (a.wav, len(chans[0])))


if __name__ == "__main__":
    main()
