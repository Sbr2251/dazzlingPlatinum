#!/usr/bin/env python3
"""Synthesizes the placeholder test stream STRM_TEST_LOOP and encodes it.

  python3 tools/strm_encoder/make_test_stream.py [--wav /tmp/strm_test_loop.wav] [--out <strm>]

Music: a 1-bar intro (a bell run that sweeps from the left speaker to the right over an A pad),
then an 8-bar loop at 96 BPM (exactly 20 s): D - Bm - G - A - D - F#m - G - A.
  left:   plucked nylon-string arpeggio (Karplus-Strong)
  right:  electric-piano melody (2-operator FM)
  wide:   detuned string pad (different detune per side), plus stereo reverb
  centre: bass, soft kick; shaker slightly right, rim click slightly left
The loop body is rendered circularly (notes and reverb tails that run past bar 8 wrap into
bar 1) so the loop point is seamless. Deterministic (fixed random seed). Pure Python, ~1 min.
The WAV is only an intermediate file; keep it out of git.
"""
import argparse
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import strmlib as S  # noqa: E402
from wav2strm import encode  # noqa: E402

DEFAULT_OUT = os.path.join(HERE, "..", "..", "res", "sound", "pl_sound_data", "Files", "STRM", "STRM_TEST_LOOP.strm")

RATE = S.rate_for_timer(S.timer_for_rate(22050))  # 21819.0 Hz, what the DS actually plays
BPM = 96.0
BEAT = 60.0 / BPM
BAR = 4 * BEAT  # 2.5 s
LOOP_BARS = 8
TWO_PI = 2 * math.pi

# (root for the guitar, quality, bass note) per loop bar
CHORDS = [(50, "maj", 38), (47, "min", 35), (43, "maj", 43), (45, "maj", 45),
          (50, "maj", 38), (42, "min", 42), (43, "maj", 43), (45, "maj", 45)]
# melody (midi note, beats) per bar, right channel
MELODY = [
    [(69, 1), (74, 1), (78, 1.5), (76, 0.5)],
    [(74, 1), (71, 1), (74, 1), (78, 1)],
    [(79, 1.5), (78, 0.5), (76, 1), (74, 1)],
    [(76, 2), (73, 1), (69, 1)],
    [(69, 1), (74, 1), (78, 1), (81, 1)],
    [(81, 1), (78, 1), (76, 1), (73, 1)],
    [(74, 1), (76, 1), (79, 1), (78, 0.5), (76, 0.5)],
    [(76, 2), (73, 1), (69, 1)],
]


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12.0)


def pan_gains(p):
    return math.cos(p * math.pi / 2), math.sin(p * math.pi / 2)


class Track:
    """Stereo float buffer; circular=True wraps writes past the end to the start."""

    def __init__(self, n, circular):
        self.n = n
        self.circular = circular
        self.l = [0.0] * n
        self.r = [0.0] * n

    def add(self, start, mono, pan, gain=1.0, width=None):
        gl, gr = pan_gains(pan)
        gl *= gain
        gr *= gain
        n = self.n
        L, R = self.l, self.r
        s = int(round(start))
        for i, v in enumerate(mono):
            j = s + i
            if j >= n:
                if not self.circular:
                    break
                j %= n
            L[j] += v * gl
            R[j] += v * gr

    def add_stereo(self, start, left, right, gain=1.0):
        n = self.n
        s = int(round(start))
        for i in range(len(left)):
            j = s + i
            if j >= n:
                if not self.circular:
                    break
                j %= n
            self.l[j] += left[i] * gain
            self.r[j] += right[i] * gain


# ---------------------------------------------------------------- instruments

def pluck(freq, dur, rng, bright=0.5):
    """Karplus-Strong with a fractional (linearly interpolated) delay so it stays in tune."""
    n = int(dur * RATE)
    period = RATE / freq - 0.5  # the two-point average adds half a sample of delay
    ip = int(period)
    y = [0.0] * (n + 1)
    prev = 0.0
    for i in range(ip + 2):  # excitation: low-passed noise burst, one period long
        prev += bright * (rng.uniform(-1, 1) - prev)
        y[i] = prev
    decay = 0.996 ** (220.0 / freq)  # similar sustain time across the range
    for m in range(ip + 2, n + 1):
        pos = m - period
        i0 = int(pos)
        f = pos - i0
        a = y[i0] + f * (y[i0 + 1] - y[i0])
        b = y[i0 - 1] + f * (y[i0] - y[i0 - 1])
        y[m] = decay * 0.5 * (a + b)
    out = y[:n]
    for i in range(min(22, n)):  # 1 ms attack, 80 ms release
        out[i] *= i / 22.0
    rel = int(0.08 * RATE)
    for i in range(min(rel, n)):
        out[n - 1 - i] *= i / rel
    return out


def epiano(freq, dur, velocity=1.0):
    """Two-operator FM electric piano with a tine transient and slow tremolo."""
    n = int(dur * RATE)
    out = [0.0] * n
    w = TWO_PI * freq / RATE
    wt = TWO_PI * freq * 14.0 / RATE
    rel = int(0.12 * RATE)
    for i in range(n):
        t = i / RATE
        index = 1.6 * math.exp(-t * 3.0) + 0.25
        tine = 0.18 * math.exp(-t * 40.0) * math.sin(wt * i)
        env = math.exp(-t * 1.1) * min(1.0, t * 400.0)
        if i > n - rel:
            env *= (n - i) / rel
        trem = 1.0 + 0.06 * math.sin(TWO_PI * 4.5 * t)
        out[i] = velocity * env * trem * (math.sin(w * i + index * math.sin(w * i)) + tine)
    return out


def pad_voice(freq, dur, detune_cents):
    """Soft saw-ish pad oscillator (3 harmonics), slow attack and release."""
    n = int(dur * RATE)
    f = freq * 2 ** (detune_cents / 1200.0)
    w = TWO_PI * f / RATE
    att = int(0.45 * RATE)
    rel = int(0.6 * RATE)
    out = [0.0] * n
    for i in range(n):
        env = min(1.0, i / att) if i < att else 1.0
        if i > n - rel:
            env *= (n - i) / rel
        p = w * i
        out[i] = env * (math.sin(p) + 0.35 * math.sin(2 * p) + 0.15 * math.sin(3 * p))
    return out


def bass(freq, dur):
    n = int(dur * RATE)
    w = TWO_PI * freq / RATE
    out = [0.0] * n
    rel = int(0.05 * RATE)
    for i in range(n):
        t = i / RATE
        env = math.exp(-t * 2.2) * min(1.0, t * 300.0)
        if i > n - rel:
            env *= (n - i) / rel
        p = w * i
        out[i] = env * (math.sin(p) + 0.45 * math.sin(2 * p) + 0.2 * math.sin(3 * p))
    return out


def kick():
    n = int(0.3 * RATE)
    out = [0.0] * n
    ph = 0.0
    for i in range(n):
        t = i / RATE
        f = 48 + 90 * math.exp(-t * 30)
        ph += TWO_PI * f / RATE
        out[i] = math.exp(-t * 11) * math.sin(ph)
    return out


def noise_hit(rng, dur, decay, hp):
    n = int(dur * RATE)
    out = [0.0] * n
    prev_x = prev_y = 0.0
    for i in range(n):
        x = rng.uniform(-1, 1)
        y = hp * (prev_y + x - prev_x)  # one-pole high-pass
        prev_x, prev_y = x, y
        out[i] = y * math.exp(-i / RATE * decay) * min(1.0, i / 30.0)
    return out


def bell(freq, dur):
    """Inharmonic bell/celesta for the intro run."""
    n = int(dur * RATE)
    partials = ((1.0, 1.0, 2.2), (2.0, 0.45, 3.5), (3.01, 0.25, 5.0), (4.2, 0.12, 7.0))
    out = [0.0] * n
    for ratio, amp, dec in partials:
        w = TWO_PI * freq * ratio / RATE
        for i in range(n):
            out[i] += amp * math.exp(-i / RATE * dec) * math.sin(w * i)
    for i in range(min(40, n)):
        out[i] *= i / 40.0
    rel = int(0.05 * RATE)
    for i in range(min(rel, n)):
        out[n - 1 - i] *= i / rel
    return out


def reverb(left, right, wet=0.22, room=0.82, damp=0.35):
    """Small Freeverb-style stereo reverb (4 combs + 2 allpasses per side)."""
    scale = RATE / 44100.0
    combs = [1116, 1188, 1277, 1356]
    aps = [556, 441]
    spread = 23

    def run(x, extra):
        n = len(x)
        acc = [0.0] * n
        for d in combs:
            size = int((d + extra) * scale)
            buf = [0.0] * size
            store = 0.0
            k = 0
            for i in range(n):
                y = buf[k]
                store = y * (1 - damp) + store * damp
                buf[k] = x[i] * 0.015 + store * room
                acc[i] += y
                k += 1
                if k == size:
                    k = 0
        for d in aps:
            size = int((d + extra) * scale)
            buf = [0.0] * size
            k = 0
            for i in range(n):
                b = buf[k]
                y = -acc[i] + b
                buf[k] = acc[i] + b * 0.5
                acc[i] = y
                k += 1
                if k == size:
                    k = 0
        return acc

    mono = [(a + b) * 0.5 for a, b in zip(left, right)]
    wl = run(mono, 0)
    wr = run(mono, spread)
    return ([a + wet * b for a, b in zip(left, wl)], [a + wet * b for a, b in zip(right, wr)])


# ---------------------------------------------------------------- arrangement

def render_loop(rng):
    n = int(round(LOOP_BARS * BAR * RATE))
    t = Track(n, circular=True)
    beat = BEAT * RATE
    k = kick()
    for bar, (root, qual, bnote) in enumerate(CHORDS):
        third = 4 if qual == "maj" else 3
        b0 = bar * BAR * RATE
        # guitar arpeggio, left
        pattern = [0, 7, 12, 12 + third, 19, 12 + third, 12, 7]
        for s, off in enumerate(pattern):
            vel = 0.9 if s % 2 == 0 else 0.7
            t.add(b0 + s * beat / 2, pluck(hz(root + off), 1.6, rng, bright=0.45 if s else 0.6),
                  pan=0.12, gain=0.30 * vel)
        # pad, wide: left and right voices detuned differently
        dur = BAR + 0.5
        for off in (12, 12 + third, 19):
            f = hz(root + off)
            t.add_stereo(b0, pad_voice(f, dur, -7), pad_voice(f, dur, +7), gain=0.035)
        # bass: beat 1, the "and" of 2, beat 3
        f = hz(bnote)
        for pos, ln in ((0, 1.4), (1.5, 1.0), (2, 1.9)):
            t.add(b0 + pos * beat, bass(f, ln * BEAT), pan=0.5, gain=0.22)
        # drums
        for b in (0, 2):
            t.add(b0 + b * beat, k, pan=0.5, gain=0.30)
        for s in range(8):
            t.add(b0 + s * beat / 2, noise_hit(rng, 0.07, 55, 0.6), pan=0.68, gain=0.05 if s % 2 else 0.08)
        for b in (1, 3):
            t.add(b0 + b * beat, noise_hit(rng, 0.05, 90, 0.85), pan=0.36, gain=0.10)
        # melody, right
        pos = 0.0
        for note, beats in MELODY[bar]:
            t.add(b0 + pos * beat, epiano(hz(note), beats * BEAT + 0.6, 0.9), pan=0.86, gain=0.20)
            pos += beats
    # circular reverb: run over two copies, keep the second (steady state)
    wl, wr = reverb(t.l + t.l, t.r + t.r)
    return wl[n:], wr[n:]


def render_intro(rng):
    n = int(round(BAR * RATE))
    t = Track(n + int(1.5 * RATE), circular=False)
    beat = BEAT * RATE
    run = [57, 61, 64, 66, 69, 71, 73, 76, 78, 81, 83, 85]  # A major (add9/6) run
    for i, note in enumerate(run):
        start = i * beat / 4
        t.add(start, bell(hz(note), 1.4), pan=0.1 + 0.8 * i / (len(run) - 1), gain=0.16)
    for off in (57, 61, 64):
        f = hz(off)
        t.add_stereo(0, pad_voice(f, BAR, -7), pad_voice(f, BAR, +7), gain=0.035)
    wl, wr = reverb(t.l, t.r)
    # the intro has to be silent by the loop start (anything past it would be heard on every
    # pass): fade the last 0.35 s
    fade = int(0.35 * RATE)
    for i in range(fade):
        g = (i / fade) ** 2
        wl[n - 1 - i] *= g
        wr[n - 1 - i] *= g
    return wl[:n], wr[:n]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--wav", default="/tmp/strm_test_loop.wav", help="intermediate WAV (not committed)")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--peak", type=float, default=-1.0, help="peak normalization in dBFS")
    a = ap.parse_args()

    rng = random.Random(0x5EED)
    il, ir = render_intro(rng)
    ll, lr = render_loop(rng)
    left = il + ll
    right = ir + lr
    pk = max(max(abs(v) for v in left), max(abs(v) for v in right))
    g = 30000.0 / pk
    left = [int(round(v * g)) for v in left]
    right = [int(round(v * g)) for v in right]
    S.write_wav(a.wav, RATE, [left, right])
    print("wrote %s: %d samples at %.2f Hz, intro %d, loop %d samples (%.3f s)"
          % (a.wav, len(left), RATE, len(il), len(ll), len(ll) / RATE))

    # re-read so the WAV is exactly what gets encoded (the same path wav2strm.py takes)
    rate, chans = S.read_wav(a.wav)
    blob, info, notes = encode(chans, RATE, 22050, "adpcm", loop_start=len(il), peak_db=a.peak)
    problems = S.validate(blob)
    if problems:
        sys.exit("invalid STRM: " + "; ".join(problems))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "wb") as f:
        f.write(blob)
    print("wrote %s: %d bytes, %s" % (a.out, len(blob), info))
    print("  loop start aligned by %+d samples, gain %+.2f dB" % (notes["align_shift"], notes["gain_db"]))


if __name__ == "__main__":
    main()
