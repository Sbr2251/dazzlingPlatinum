#!/usr/bin/env python3
"""Self-test for the STRM encoder/decoder: python3 tools/strm_encoder/selftest.py

Encodes synthetic signals, decodes them with the NNS MakeWaveData re-implementation and checks
header fields, SNR, sample-exact looping, offset starts and the resampler."""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import strmlib as S  # noqa: E402
from wav2strm import encode  # noqa: E402

FAILS = []


def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


def tone(n, rate, freqs, amp=9000, phase=0.0):
    return [int(sum(amp * math.sin(2 * math.pi * f * i / rate + phase) for f in freqs) / len(freqs))
            for i in range(n)]


def test_adpcm_stereo_loop():
    rate_req = 22050
    timer = S.timer_for_rate(rate_req)
    rate = S.rate_for_timer(timer)
    n = 30000
    # loop start deliberately not block aligned (exercise the pad path); signal periodic in the
    # loop so that looping is seamless
    left = tone(n, rate, [440.0, 660.0])
    right = tone(n, rate, [330.0, 550.0], phase=1.0)
    random.seed(1)
    right = [v + random.randint(-300, 300) for v in right]
    loop_start = 5000
    blob, info, notes = encode([left, right], rate, rate_req, "adpcm", loop_start=loop_start,
                               log=lambda *_: None)
    check(not S.validate(blob), "adpcm stereo: validate() clean")
    h = S.parse_strm(blob)
    bs = 1016
    shift = (-loop_start) % bs
    check(h.format == S.FORMAT_ADPCM and h.channels == 2 and h.loop_flag == 1, "header format/channels/loop flag")
    check(h.timer == 24 and h.sample_rate == 21819, "timer 24 / rate 21819 for 22050 request (%d/%d)" % (h.timer, h.sample_rate))
    check(h.block_size == 512 and h.block_samples == bs, "block size 512 / 1016 samples")
    check(notes["align_shift"] == shift and h.loop_start == loop_start + shift and h.loop_start % bs == 0,
          "loop start padded to block boundary (%d -> %d)" % (loop_start, h.loop_start))
    check(h.loop_end == n + shift, "loop end = samples + pad (%d)" % h.loop_end)
    check(h.num_blocks == (h.loop_end + bs - 1) // bs and
          h.last_block_samples == h.loop_end - (h.num_blocks - 1) * bs, "block count / last block samples")
    check(h.last_block_size % 4 == 0 and h.last_block_size >= 4 + (h.last_block_samples + 1) // 2, "last block size")
    check(len(blob) == h.file_size == 0x68 + ((h.num_blocks - 1) * 512 + h.last_block_size) * 2, "file size")

    # linear decode vs NNS playback of the first pass must agree exactly
    _, lin = S.decode_linear(blob)
    loop_len = h.loop_end - h.loop_start
    play = S.NnsStrmPlayer(blob).render(h.loop_end + 2 * loop_len)
    check(play[0][:h.loop_end] == lin[0] and play[1][:h.loop_end] == lin[1], "NNS playback == linear decode (pass 1)")
    # after the loop jump NNS reloads the block header state: passes 2 and 3 are bit-identical
    check(all(play[c][h.loop_end:h.loop_end + loop_len] == lin[c][h.loop_start:] for c in range(2)),
          "loop pass 2 identical to loop region")
    check(all(play[c][h.loop_end + loop_len:] == lin[c][h.loop_start:] for c in range(2)), "loop pass 3 identical")
    ref_l = [0] * shift + left
    ref_r = [0] * shift + right
    snr_l = S.snr_db(ref_l, lin[0])
    snr_r = S.snr_db(ref_r, lin[1])
    check(snr_l > 25 and snr_r > 25, "ADPCM SNR L %.1f dB, R %.1f dB (> 25)" % (snr_l, snr_r))

    # offset start (fanfare resume): NNS decodes from the block header up to the offset
    for ms in (1, 500, 777):
        start = h.sample_rate * ms // 1000
        got = S.NnsStrmPlayer(blob, ms).render(4000)
        check(all(got[c] == lin[c][start:start + 4000] for c in range(2)), "offset start %d ms is sample exact" % ms)


def test_loop_seam_after_silent_intro():
    # intro of silence, then a loud tone: the loop block header must continue from the loop end
    rate = S.rate_for_timer(24)
    bs = 1016
    period = 127  # 171.8 Hz; the 20-block loop body holds exactly 160 periods
    body = [int(12000 * math.sin(2 * math.pi * i / period)) for i in range(bs * 20)]
    x = [0] * (bs * 3) + body
    blob, _ = S.build_strm([x], S.FORMAT_ADPCM, 24, rate, loop_start=bs * 3)
    h = S.parse_strm(blob)
    play = S.NnsStrmPlayer(blob).render(h.loop_end + 3000)[0]
    seam = [abs(play[h.loop_end + k] - x[h.loop_start + k]) for k in range(64)]
    first = [abs(play[h.loop_start + k] - x[h.loop_start + k]) for k in range(64)]
    check(max(seam) < 1500 and max(first) < 1500,
          "no slew at the loop start (max error pass1 %d, after jump %d)" % (max(first), max(seam)))
    check(play[h.loop_end:] == play[h.loop_start:h.loop_start + 3000], "pass 2 identical to pass 1")


def test_unaligned_loop_is_detected():
    rate = S.rate_for_timer(24)
    x = tone(5000, rate, [500.0])
    try:
        S.build_strm([x], S.FORMAT_ADPCM, 24, rate, loop_start=100)
        check(False, "unaligned ADPCM loop start rejected")
    except ValueError:
        check(True, "unaligned ADPCM loop start rejected")


def test_pcm16_mono_and_4ch():
    rate = S.rate_for_timer(16)  # 32728 Hz
    n = 12345
    x = tone(n, rate, [1000.0, 1234.5])
    blob, info, _ = encode([x], rate, 32728, "pcm16", loop_start=777, log=lambda *_: None)
    h = S.parse_strm(blob)
    check(not S.validate(blob) and h.format == S.FORMAT_PCM16 and h.timer == 16 and h.channels == 1,
          "pcm16 mono header (timer 16)")
    check(h.loop_start == 777 and h.block_samples == 256, "pcm16 loop start kept as is (no alignment needed)")
    play = S.NnsStrmPlayer(blob).render(n + (n - 777))
    check(play[0][:n] == x and play[0][n:] == x[777:], "pcm16 lossless, loop exact")

    chans = [tone(9000, rate, [220.0 * (k + 1)], phase=k) for k in range(4)]
    blob, info, _ = encode(chans, rate, 32728, "adpcm", loop_start=2032, log=lambda *_: None)
    h = S.parse_strm(blob)
    check(not S.validate(blob) and h.channels == 4 and h.loop_start == 2032, "adpcm 4ch header, aligned loop kept")
    _, lin = S.decode_linear(blob)
    play = S.NnsStrmPlayer(blob).render(9000 + 5000)
    check(all(play[c][:9000] == lin[c] and play[c][9000:] == lin[c][2032:2032 + 5000] for c in range(4)),
          "adpcm 4ch NNS playback and loop")
    check(min(S.snr_db(chans[c], lin[c]) for c in range(4)) > 25, "adpcm 4ch SNR > 25 dB")


def test_no_loop():
    rate = S.rate_for_timer(24)
    x = tone(3000, rate, [300.0])
    blob, info, _ = encode([x, x], rate, 22050, "adpcm", log=lambda *_: None)
    h = S.parse_strm(blob)
    p = S.NnsStrmPlayer(blob)
    out = p.render(10000)
    check(h.loop_flag == 0 and h.loop_start == 0 and p.finish, "one-shot stream finishes")
    check(len(out[0]) >= 3000 and all(v == 0 for v in out[0][3000:]), "silence after the end of a one-shot stream")


def test_resampler():
    rin, rout = 44100.0, S.rate_for_timer(24)
    n = 8000
    f = 1000.0
    x = [10000 * math.sin(2 * math.pi * f * i / rin) for i in range(n)]
    y = S.resample(x, rin, rout)
    ref = [10000 * math.sin(2 * math.pi * f * j / rout) for j in range(len(y))]
    m = len(y)
    snr = S.snr_db(ref[100:m - 100], y[100:m - 100])
    check(abs(len(y) - n * rout / rin) <= 1, "resampled length %d" % len(y))
    check(snr > 60, "resampler SNR %.1f dB (> 60)" % snr)
    # a tone above the output Nyquist must be attenuated
    z = S.resample([10000 * math.sin(2 * math.pi * 14000 * i / rin) for i in range(n)], rin, rout)
    check(S.rms([z[100:-100]]) < 10000 / math.sqrt(2) * 0.01, "aliasing tone suppressed (> 40 dB)")


def test_normalize():
    rate = S.rate_for_timer(24)
    x = tone(4000, rate, [440.0], amp=3000)
    blob, info, notes = encode([x], rate, 22050, "pcm16", peak_db=-1.0, log=lambda *_: None)
    _, lin = S.decode_linear(blob)
    pk = S.peak(lin)
    check(abs(20 * math.log10(pk / 32767.0) + 1.0) < 0.05, "peak normalized to -1 dBFS (%.2f)" % (20 * math.log10(pk / 32767.0)))


def main():
    for t in (test_adpcm_stereo_loop, test_loop_seam_after_silent_intro, test_unaligned_loop_is_detected, test_pcm16_mono_and_4ch,
              test_no_loop, test_resampler, test_normalize):
        print("--", t.__name__)
        t()
    print()
    if FAILS:
        print("%d FAILED" % len(FAILS))
        sys.exit(1)
    print("all passed")


if __name__ == "__main__":
    main()
