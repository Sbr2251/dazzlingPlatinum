#!/usr/bin/env python3
"""Bit-exact preview of the area FX capture effects (src/sound_area_fx.c).

Runs a Python port of SoundAreaFx_CaptureCallback() over a WAV file (or a
generated test signal) and writes before/after WAVs so the effects can be
auditioned on a computer without building the ROM.

The AREA_FX_* constants and the sine table are parsed from
src/sound_area_fx.c, so tuning the C file and re-running this script is
enough. The port uses the same integer math (s32 products, arithmetic shifts,
s16 saturation) and the same callback chunking (512 samples per callback,
mode switches only at block boundaries).

Usage:
    python3 tools/audio_fx_preview/preview.py                 # test signal
    python3 tools/audio_fx_preview/preview.py song.wav        # your audio
    python3 tools/audio_fx_preview/preview.py song.wav --seconds 15 --strict

Outputs go to /tmp/audio_fx_preview/ (override with --out):
    <name>_before.wav       input resampled to the capture rate (~21819 Hz)
    <name>_echo.wav         cave echo
    <name>_muffle.wav       water muffle
    <name>_warp.wav         Distortion World warp
    <name>_transitions.wav  echo -> muffle -> warp -> none, to hear the ramps

Not modelled: the capture unit's ~47 ms latency, and the DS mixer/DAC
(10-bit output, its own clipping). Only the PCM16 path is ported.
"""

import argparse
import math
import os
import re
import struct
import sys
import wave

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
C_SOURCE = os.path.join(REPO_ROOT, "src", "sound_area_fx.c")

# NNS_SndCaptureStartEffect(..., SOUND_FILTER_SAMPLE_RATE = 22000, SOUND_FILTER_INTERVAL = 2)
# with SOUND_SYSTEM_CAPTURE_BUFFER_SIZE = 0x1000: timer = ((16756991 // 22000) + 16) & ~31
SND_TIMER_CLOCK = 33513982 // 2
CAPTURE_TIMER = ((SND_TIMER_CLOCK // 22000) + 16) & ~0x1F
SAMPLE_RATE = SND_TIMER_CLOCK / CAPTURE_TIMER
CAPTURE_BUFFER_SIZE = 0x1000
CAPTURE_INTERVAL = 2
BLOCK_BYTES = (CAPTURE_BUFFER_SIZE // 2) // CAPTURE_INTERVAL
BLOCK_SAMPLES = BLOCK_BYTES >> 1  # 'count' in the callback (PCM16)

MODE_NONE, MODE_ECHO, MODE_MUFFLE, MODE_WARP = 0, 1, 2, 3
MODE_NAMES = {"none": MODE_NONE, "echo": MODE_ECHO, "muffle": MODE_MUFFLE, "warp": MODE_WARP}

U32 = 0xFFFFFFFF


def parse_c_source(path):
    with open(path, "r", encoding="ascii") as f:
        text = f.read()

    raw = {}
    for m in re.finditer(r"^#define\s+(AREA_FX_\w+)\s+(.+?)\s*(?://.*)?$", text, re.M):
        raw[m.group(1)] = m.group(2).strip()

    consts = {}

    def evaluate(name, depth=0):
        if name in consts:
            return consts[name]
        if depth > 10:
            raise ValueError("recursive define " + name)
        expr = raw[name]
        expr = expr.replace("TRUE", "1").replace("FALSE", "0")
        expr = re.sub(r"\b(AREA_FX_\w+)\b", lambda mm: str(evaluate(mm.group(1), depth + 1)), expr)
        if not re.fullmatch(r"[0-9xXa-fA-F()+\-*/<>&| ~]+", expr):
            raise ValueError("cannot evaluate %s = %s" % (name, raw[name]))
        consts[name] = int(eval(expr, {"__builtins__": {}}))
        return consts[name]

    for name in raw:
        evaluate(name)

    m = re.search(r"sSineTable\[257\]\s*=\s*\{(.*?)\};", text, re.S)
    if not m:
        raise ValueError("sSineTable not found in " + path)
    table = [int(v) for v in re.findall(r"-?\d+", m.group(1))]
    if len(table) != 257:
        raise ValueError("sSineTable has %d entries" % len(table))

    return consts, table


class AreaFx:
    """Port of AreaFxDsp + SoundAreaFx_CaptureCallback()."""

    def __init__(self, consts, sine, strict=False):
        self.c = consts
        self.sine = sine
        self.strict = strict
        self.line = [0] * consts["AREA_FX_LINE_LEN"]
        self.requested = MODE_NONE
        self.reset(MODE_NONE)

    # --- helpers -------------------------------------------------------
    def chk(self, v):
        if self.strict and not (-0x80000000 <= v <= 0x7FFFFFFF):
            raise OverflowError("s32 overflow: %d" % v)
        return v

    @staticmethod
    def sat16(v):
        if v > 32767:
            return 32767
        if v < -32768:
            return -32768
        return v

    def sine_at(self, phase):
        index = phase >> 24
        frac = (phase >> 8) & 0xFFFF
        a = self.sine[index]
        b = self.sine[index + 1]
        return a + (self.chk((b - a) * frac) >> 16)

    def step_ramp(self, ramp, target):
        step = self.c["AREA_FX_RAMP_STEP"]
        if ramp < target:
            ramp += step
            if ramp > target:
                ramp = target
        elif ramp > target:
            ramp -= step
            if ramp < target:
                ramp = target
        return ramp

    # --- SoundAreaFx_ResetDsp -------------------------------------------
    def reset(self, mode):
        self.ramp = 0
        self.write_pos = 0
        self.echo_damp = 0
        self.muffle = [[0, 0], [0, 0]]
        self.lfo = 0
        self.ring = 0
        if mode in (MODE_ECHO, MODE_WARP):
            for i in range(len(self.line)):
                self.line[i] = 0
        self.mode = mode

    # --- effects --------------------------------------------------------
    def process_echo(self, bl, br, count, target):
        c = self.c
        one = c["AREA_FX_Q15_ONE"]
        mask = c["AREA_FX_LINE_MASK"]
        delay = c["AREA_FX_ECHO_DELAY"]
        fb = c["AREA_FX_ECHO_FEEDBACK"]
        wet_max = c["AREA_FX_ECHO_WET"]
        damp_k = c["AREA_FX_ECHO_DAMP"]
        line = self.line
        chk = self.chk
        ramp, pos, damp = self.ramp, self.write_pos, self.echo_damp
        for i in range(count):
            l = bl[i]
            r = br[i]
            mono = (l + r) >> 1
            tap = line[(pos - delay) & mask]
            damp += chk((tap - damp) * damp_k) >> 12
            line[pos] = self.sat16(mono + (chk(damp * fb) >> 15))
            pos = (pos + 1) & mask
            ramp = self.step_ramp(ramp, target)
            wet = chk(ramp * wet_max) >> 15
            dry = one - (wet >> 1)
            bl[i] = self.sat16(chk(chk(l * dry) + chk(damp * wet)) >> 15)
            br[i] = self.sat16(chk(chk(r * dry) + chk(damp * wet)) >> 15)
        self.ramp, self.write_pos, self.echo_damp = ramp, pos, damp

    def process_muffle(self, bl, br, count, target):
        c = self.c
        one = c["AREA_FX_Q15_ONE"]
        k = c["AREA_FX_MUFFLE_COEF"]
        wet_max = c["AREA_FX_MUFFLE_WET"]
        chk = self.chk
        ramp = self.ramp
        (l1, l2), (r1, r2) = self.muffle
        for i in range(count):
            l = bl[i]
            r = br[i]
            l1 += chk((l * 16 - l1) * k) >> 12
            l2 += chk((l1 - l2) * k) >> 12
            r1 += chk((r * 16 - r1) * k) >> 12
            r2 += chk((r1 - r2) * k) >> 12
            ramp = self.step_ramp(ramp, target)
            wet = chk(ramp * wet_max) >> 15
            dry = one - wet
            bl[i] = self.sat16(chk(chk(l * dry) + chk((l2 >> 4) * wet)) >> 15)
            br[i] = self.sat16(chk(chk(r * dry) + chk((r2 >> 4) * wet)) >> 15)
        self.muffle = [[l1, l2], [r1, r2]]
        self.ramp = ramp

    def warp_channel(self, x, base, pos, phase):
        c = self.c
        mask = c["AREA_FX_WARP_MASK"]
        delay = (c["AREA_FX_WARP_BASE_DELAY"] << 8) + (self.chk(c["AREA_FX_WARP_DEPTH"] * self.sine_at(phase)) >> 7)
        whole = (delay >> 8) & U32
        frac = delay & 0xFF
        a = self.line[base + ((pos - whole) & mask)]
        b = self.line[base + ((pos - whole - 1) & mask)]
        tap = a + (self.chk((b - a) * frac) >> 8)
        self.line[base + pos] = self.sat16(x + (self.chk(tap * c["AREA_FX_WARP_FEEDBACK"]) >> 15))
        return tap

    def process_warp(self, bl, br, count, target):
        c = self.c
        one = c["AREA_FX_Q15_ONE"]
        mask = c["AREA_FX_WARP_MASK"]
        half = c["AREA_FX_WARP_LEN"]
        stereo = c["AREA_FX_WARP_STEREO_PHASE"]
        lfo_inc = c["AREA_FX_WARP_LFO_INC"]
        ring_inc = c["AREA_FX_WARP_RING_INC"]
        ring_depth = c["AREA_FX_WARP_RING_DEPTH"]
        wet_max = c["AREA_FX_WARP_WET"]
        chk = self.chk
        ramp, pos, lfo, ring = self.ramp, self.write_pos, self.lfo, self.ring
        for i in range(count):
            l = bl[i]
            r = br[i]
            tap_l = self.warp_channel(l, 0, pos, lfo)
            tap_r = self.warp_channel(r, half, pos, (lfo + stereo) & U32)
            ring_gain = (one - ring_depth) + (chk(ring_depth * self.sine_at(ring)) >> 15)
            tap_l = chk(tap_l * ring_gain) >> 15
            tap_r = chk(tap_r * ring_gain) >> 15
            pos = (pos + 1) & mask
            lfo = (lfo + lfo_inc) & U32
            ring = (ring + ring_inc) & U32
            ramp = self.step_ramp(ramp, target)
            wet = chk(ramp * wet_max) >> 15
            dry = one - wet
            bl[i] = self.sat16(chk(chk(l * dry) + chk(tap_l * wet)) >> 15)
            br[i] = self.sat16(chk(chk(r * dry) + chk(tap_r * wet)) >> 15)
        self.ramp, self.write_pos, self.lfo, self.ring = ramp, pos, lfo, ring

    # --- SoundAreaFx_CaptureCallback ------------------------------------
    def callback(self, bl, br):
        count = len(bl)
        requested = self.requested
        if self.mode != requested and self.ramp == 0:
            self.reset(requested)
        target = self.c["AREA_FX_Q15_ONE"] if self.mode == requested else 0
        if self.mode == MODE_ECHO:
            self.process_echo(bl, br, count, target)
        elif self.mode == MODE_MUFFLE:
            self.process_muffle(bl, br, count, target)
        elif self.mode == MODE_WARP:
            self.process_warp(bl, br, count, target)


def run(consts, sine, left, right, schedule, strict):
    """schedule(block_index) -> requested mode. Mirrors SoundAreaFx_Update():
    the DSP is reset to the first requested mode before capture starts."""
    fx = AreaFx(consts, sine, strict)
    first = schedule(0)
    fx.reset(first)
    fx.requested = first
    out_l = list(left)
    out_r = list(right)
    n = len(out_l)
    pad = (-n) % BLOCK_SAMPLES
    out_l += [0] * pad
    out_r += [0] * pad
    for b, start in enumerate(range(0, len(out_l), BLOCK_SAMPLES)):
        fx.requested = schedule(b)
        bl = out_l[start:start + BLOCK_SAMPLES]
        br = out_r[start:start + BLOCK_SAMPLES]
        fx.callback(bl, br)
        out_l[start:start + BLOCK_SAMPLES] = bl
        out_r[start:start + BLOCK_SAMPLES] = br
    return out_l[:n], out_r[:n]


# --- WAV I/O ------------------------------------------------------------------

def read_wav(path, max_seconds):
    with wave.open(path, "rb") as w:
        ch = w.getnchannels()
        width = w.getsampwidth()
        rate = w.getframerate()
        frames = min(w.getnframes(), int(max_seconds * rate))
        data = w.readframes(frames)
    count = len(data) // (width * ch)
    samples = []
    for i in range(count * ch):
        off = i * width
        if width == 1:
            v = (data[off] - 128) << 8
        elif width == 2:
            v = struct.unpack_from("<h", data, off)[0]
        elif width == 3:
            v = int.from_bytes(data[off:off + 3], "little", signed=True) >> 8
        elif width == 4:
            v = struct.unpack_from("<i", data, off)[0] >> 16
        else:
            raise ValueError("unsupported sample width %d" % width)
        samples.append(v)
    left = samples[0::ch]
    right = samples[1::ch] if ch > 1 else list(left)
    return left, right, rate


def resample(x, src_rate, dst_rate):
    if abs(src_rate - dst_rate) < 1e-6:
        return list(x)
    n = int(len(x) * dst_rate / src_rate)
    ratio = src_rate / dst_rate
    out = []
    last = len(x) - 1
    for i in range(n):
        p = i * ratio
        j = int(p)
        f = p - j
        a = x[min(j, last)]
        b = x[min(j + 1, last)]
        out.append(int(round(a + (b - a) * f)))
    return out


def write_wav(path, left, right, rate):
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(int(round(rate)))
        buf = bytearray()
        for l, r in zip(left, right):
            buf += struct.pack("<hh", max(-32768, min(32767, l)), max(-32768, min(32767, r)))
        w.writeframes(bytes(buf))


def test_signal(rate, seconds):
    """Plucked arpeggio panned left/right, a soft pad, and percussive clicks
    (like SFX), so echo tails, muffling and pitch wobble are all audible."""
    n = int(rate * seconds)
    left = [0.0] * n
    right = [0.0] * n
    notes = [220.0, 277.18, 329.63, 440.0, 329.63, 277.18]
    step = int(rate * 0.375)
    for k, start in enumerate(range(0, n - step, step)):
        freq = notes[k % len(notes)]
        pan = 0.25 if k % 2 == 0 else 0.75
        length = min(int(rate * 0.9), n - start)
        for i in range(length):
            t = i / rate
            env = math.exp(-t * 5.0)
            v = env * (0.5 * math.sin(2 * math.pi * freq * t)
                       + 0.25 * math.sin(2 * math.pi * 2 * freq * t)
                       + 0.12 * math.sin(2 * math.pi * 3 * freq * t))
            left[start + i] += v * (1.0 - pan)
            right[start + i] += v * pan
    for i in range(n):
        t = i / rate
        pad = 0.08 * (math.sin(2 * math.pi * 110.0 * t) + 0.5 * math.sin(2 * math.pi * 164.81 * t))
        left[i] += pad
        right[i] += pad
    seed = 12345
    for start in range(int(rate * 0.1), n, int(rate * 1.5)):
        for i in range(min(int(rate * 0.03), n - start)):
            seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
            v = ((seed >> 8) / float(1 << 22) - 1.0) * math.exp(-i / (rate * 0.006)) * 0.6
            left[start + i] += v
            right[start + i] += v
    scale = 0.7 * 32767
    return [int(round(v * scale)) for v in left], [int(round(v * scale)) for v in right]


def peak_db(x):
    p = max(1, max(abs(v) for v in x))
    return 20 * math.log10(p / 32768.0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", nargs="?", help="input WAV (default: generated test signal)")
    ap.add_argument("--out", default="/tmp/audio_fx_preview", help="output directory")
    ap.add_argument("--seconds", type=float, default=20.0, help="max seconds of input to process")
    ap.add_argument("--modes", default="echo,muffle,warp", help="comma-separated modes to render")
    ap.add_argument("--no-transitions", action="store_true", help="skip the transitions demo")
    ap.add_argument("--strict", action="store_true", help="assert that no s32 product overflows (slower)")
    ap.add_argument("--source", default=C_SOURCE, help="path to sound_area_fx.c")
    args = ap.parse_args()

    consts, sine = parse_c_source(args.source)
    os.makedirs(args.out, exist_ok=True)

    if args.input:
        left, right, rate = read_wav(args.input, args.seconds)
        left = resample(left, rate, SAMPLE_RATE)
        right = resample(right, rate, SAMPLE_RATE)
        name = os.path.splitext(os.path.basename(args.input))[0]
    else:
        left, right = test_signal(SAMPLE_RATE, min(args.seconds, 12.0))
        name = "test_signal"

    print("capture rate %.3f Hz, %d samples per callback, %.2f s of audio" % (SAMPLE_RATE, BLOCK_SAMPLES, len(left) / SAMPLE_RATE))

    outputs = []
    path = os.path.join(args.out, name + "_before.wav")
    write_wav(path, left, right, SAMPLE_RATE)
    outputs.append((path, left, right))

    for mode_name in [m.strip() for m in args.modes.split(",") if m.strip()]:
        mode = MODE_NAMES[mode_name]
        out_l, out_r = run(consts, sine, left, right, lambda b, m=mode: m, args.strict)
        path = os.path.join(args.out, "%s_%s.wav" % (name, mode_name))
        write_wav(path, out_l, out_r, SAMPLE_RATE)
        outputs.append((path, out_l, out_r))

    if not args.no_transitions:
        blocks = (len(left) + BLOCK_SAMPLES - 1) // BLOCK_SAMPLES
        tail = int(2.0 * SAMPLE_RATE) // BLOCK_SAMPLES
        span = max(1, (blocks - tail) // 3)

        def schedule(b):
            if b < span:
                return MODE_ECHO
            if b < 2 * span:
                return MODE_MUFFLE
            if b < 3 * span:
                return MODE_WARP
            return MODE_NONE

        out_l, out_r = run(consts, sine, left, right, schedule, args.strict)
        path = os.path.join(args.out, name + "_transitions.wav")
        write_wav(path, out_l, out_r, SAMPLE_RATE)
        outputs.append((path, out_l, out_r))

    for path, l, r in outputs:
        print("  %-60s peak %6.1f dBFS" % (path, max(peak_db(l), peak_db(r))))

    return 0


if __name__ == "__main__":
    sys.exit(main())
