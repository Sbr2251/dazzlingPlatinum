"""NDS STRM (NitroSystem stream) reader/writer, IMA-ADPCM codec and a decoder that mirrors
NNS_SndArcStrm (NitroSystem libraries/snd/src/sndarc_stream.c). Pure Python, no dependencies.

File layout written here (all little endian), matching NNSSndStrmData in sndarc_stream.c:

  0x00  "STRM", u16 0xFEFF, u16 version 0x0100, u32 file size, u16 header size 0x10, u16 blocks 2
  0x10  "HEAD", u32 0x50
  0x18  u8 format (0 PCM8, 1 PCM16, 2 IMA-ADPCM), u8 loop flag, u8 channels, u8 pad
  0x1C  u16 sample rate (Hz, only used for ms <-> sample conversion), u16 timer
  0x20  u32 loop start (samples), u32 loop end (= total samples)
  0x28  u32 data offset (absolute, 0x68), u32 block count
  0x30  u32 block size, u32 samples per block, u32 last block size, u32 last block samples
  0x40  32 reserved bytes
  0x60  "DATA", u32 size (8 + data)
  0x68  block 0 ch 0, block 0 ch 1, ..., block 1 ch 0, ...   (the last block of every channel is
        "last block size" bytes long, so channels stay contiguous at that stride)

IMA-ADPCM blocks start with the AdpcmState {s16 predictor, u8 step index, u8 pad}; the predictor
is not an output sample. Nibbles: low nibble first. The hardware channel timer is timer << 5, so
the real playback rate is SND_TIMER_CLOCK / (32 * timer) = 523656 / timer Hz.
"""
import math
import struct
import wave

SND_TIMER_CLOCK = 16756991  # ARM7 bus clock / 2, NitroSDK SND_TIMER_CLOCK

FORMAT_PCM8 = 0
FORMAT_PCM16 = 1
FORMAT_ADPCM = 2
FORMAT_NAMES = {FORMAT_PCM8: "pcm8", FORMAT_PCM16: "pcm16", FORMAT_ADPCM: "adpcm"}

HEADER_SIZE = 0x68
BLOCK_SIZE = 512  # bytes per channel per block; see block_size_limit()

# sndarc_stream.c: BLOCK_SIZE 512, BLOCK_NUM 4 -> every channel buffer holds 2048 bytes (1024 PCM16
# samples). NNS_SndStrmSetup fills the whole buffer once (interval 1) at setup.
NNS_CH_BUFFER_BYTES = 512 * 4
NNS_CALLBACK_BYTES = 512  # bytes per channel per StrmCallback while playing
NNS_MAX_CHANNELS = 6  # STRM_CHANNEL_MAX

INDEX_TABLE = (-1, -1, -1, -1, 2, 4, 6, 8, -1, -1, -1, -1, 2, 4, 6, 8)
STEP_TABLE = (
    7, 8, 9, 10, 11, 12, 13, 14, 16, 17,
    19, 21, 23, 25, 28, 31, 34, 37, 41, 45,
    50, 55, 60, 66, 73, 80, 88, 97, 107, 118,
    130, 143, 157, 173, 190, 209, 230, 253, 279, 307,
    337, 371, 408, 449, 494, 544, 598, 658, 724, 796,
    876, 963, 1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066,
    2272, 2499, 2749, 3024, 3327, 3660, 4026, 4428, 4871, 5358,
    5894, 6484, 7132, 7845, 8630, 9493, 10442, 11487, 12635, 13899,
    15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794, 32767,
)

# DIFF[index][code & 7]: the magnitude DecodeAdpcm adds for a code (step>>3 + step/step>>1/step>>2)
DIFF = [[(s >> 3) + (s if c & 4 else 0) + ((s >> 1) if c & 2 else 0) + ((s >> 2) if c & 1 else 0)
         for c in range(8)] for s in STEP_TABLE]
NEXT_INDEX = [[min(88, max(0, i + INDEX_TABLE[c])) for c in range(16)] for i in range(89)]


# ---------------------------------------------------------------- rates

def timer_for_rate(rate):
    """Header timer for a requested sample rate (nearest representable)."""
    timer = int(round(SND_TIMER_CLOCK / 32.0 / rate))
    return max(1, min(2047, timer))  # NNS_SND_STRM_TIMER_MIN/MAX


def rate_for_timer(timer):
    """Exact playback rate of a header timer value."""
    return SND_TIMER_CLOCK / 32.0 / timer


def block_samples_for(fmt, block_size):
    if fmt == FORMAT_ADPCM:
        return (block_size - 4) * 2
    if fmt == FORMAT_PCM16:
        return block_size // 2
    return block_size


def block_size_limit(fmt):
    """Largest block size NNS can play. When a stream starts at an offset (fanfare resume) the
    first ADPCM block is decoded from its header up to the offset into the 2048-byte setup
    buffer, so an ADPCM block may hold at most 1025 samples. PCM has no such path."""
    if fmt == FORMAT_ADPCM:
        return 4 + (NNS_CH_BUFFER_BYTES // 2 + 1) // 2
    return 0x10000


# ---------------------------------------------------------------- IMA-ADPCM

def adpcm_decode_sample(code, state):
    """DecodeAdpcm() from sndarc_stream.c. state = [sample, index]. Returns the new sample."""
    sample, index = state
    d = DIFF[index][code & 7]
    if code & 8:
        sample -= d
        if sample < -32768:
            sample = -32768
    else:
        sample += d
        if sample > 32767:
            sample = 32767
    state[0] = sample
    state[1] = NEXT_INDEX[index][code]
    return sample


def adpcm_encode(samples, block_samples, state=None):
    """Encodes one channel (list of ints) into IMA-ADPCM blocks of block_samples samples,
    starting from state (predictor, index); default (first sample, 0).
    Returns (list of block bytes with headers, unpadded; final (predictor, index)). The
    encoder tracks the decoder's exact state and every block header holds that state, so
    decoding from any block header reproduces exactly what continuous decoding produces."""
    diff_tab = DIFF
    next_tab = NEXT_INDEX
    if state is None:
        state = (samples[0] if samples else 0, 0)
    pred = max(-32768, min(32767, state[0]))
    index = state[1]
    blocks = []
    n = len(samples)
    for start in range(0, n, block_samples):
        chunk = samples[start:start + block_samples]
        out = bytearray(struct.pack("<hBB", pred, index, 0))
        lo = None
        for x in chunk:
            dt = diff_tab[index]
            diff = x - pred
            if diff < 0:
                sign = 8
                mag = -diff
            else:
                sign = 0
                mag = diff
            step = STEP_TABLE[index]
            q = (mag << 2) // step
            if q > 7:
                q = 7
            # reconstruct q and its neighbour, keep the closer (decoder rounding is not exact)
            best = q
            if sign:
                r = pred - dt[q]
                if r < -32768:
                    r = -32768
                err = abs(x - r)
                if q < 7:
                    r2 = pred - dt[q + 1]
                    if r2 < -32768:
                        r2 = -32768
                    if abs(x - r2) < err:
                        best, r = q + 1, r2
            else:
                r = pred + dt[q]
                if r > 32767:
                    r = 32767
                err = abs(x - r)
                if q < 7:
                    r2 = pred + dt[q + 1]
                    if r2 > 32767:
                        r2 = 32767
                    if abs(x - r2) < err:
                        best, r = q + 1, r2
            code = sign | best
            pred = r
            index = next_tab[index][code]
            if lo is None:
                lo = code
            else:
                out.append(lo | (code << 4))
                lo = None
        if lo is not None:
            out.append(lo)
        blocks.append(bytes(out))
    return blocks, (pred, index)


def adpcm_encode_looped(samples, block_samples, loop_start):
    """Like adpcm_encode, for a looping stream (loop_start block aligned). NNS reloads the
    header of the loop start block after every loop jump, so that header is set to the
    encoder state at the loop end: the predictor then continues from the last sample of the
    loop instead of from whatever preceded the loop start on the first pass (an intro that
    ends in silence would otherwise make every loop start with the predictor slewing up from
    zero, i.e. a click). The first pass reaches the loop block the same way, through its
    header, so both passes decode identically."""
    head, state = adpcm_encode(samples[:loop_start], block_samples) if loop_start else ([], None)
    body = samples[loop_start:]
    blocks, end = adpcm_encode(body, block_samples, state)
    for _ in range(3):  # the state at the loop end converges immediately in practice
        blocks, new_end = adpcm_encode(body, block_samples, end)
        if new_end == end:
            break
        end = new_end
    return head + blocks


def adpcm_decode_block(data, count):
    """Decodes count samples from one block (header included)."""
    pred, index, _ = struct.unpack_from("<hBB", data, 0)
    state = [pred, index]
    out = []
    for i in range(count):
        byte = data[4 + (i >> 1)]
        code = (byte >> 4) if (i & 1) else (byte & 0x0F)
        out.append(adpcm_decode_sample(code, state))
    return out


# ---------------------------------------------------------------- STRM container

class StrmInfo:
    """The HEAD fields NNS reads (NNSSndStrmData)."""
    FIELDS = ("format", "loop_flag", "channels", "sample_rate", "timer", "loop_start", "loop_end",
              "data_offset", "num_blocks", "block_size", "block_samples", "last_block_size",
              "last_block_samples")

    def __init__(self, **kw):
        for f in self.FIELDS:
            setattr(self, f, kw.get(f, 0))

    def as_dict(self):
        return {f: getattr(self, f) for f in self.FIELDS}

    def __repr__(self):
        return "StrmInfo(%s)" % ", ".join("%s=%s" % kv for kv in self.as_dict().items())


def _pad4(b):
    return b + b"\x00" * ((-len(b)) & 3)


def build_strm(channels, fmt, timer, sample_rate, loop_start=None, block_size=BLOCK_SIZE):
    """channels: list of per-channel sample lists (ints, equal length). loop_start: None for a
    one-shot stream. For ADPCM, loop_start must be a multiple of the block sample count.
    Returns (bytes, StrmInfo)."""
    nch = len(channels)
    if not 1 <= nch <= NNS_MAX_CHANNELS:
        raise ValueError("NNS streams support 1..%d channels" % NNS_MAX_CHANNELS)
    total = len(channels[0])
    if total == 0 or any(len(c) != total for c in channels):
        raise ValueError("channels must be non-empty and of equal length")
    if block_size % 4 or block_size > block_size_limit(fmt):
        raise ValueError("block size must be a multiple of 4 and <= %d" % block_size_limit(fmt))
    bsamp = block_samples_for(fmt, block_size)
    if loop_start is not None:
        if not 0 <= loop_start < total:
            raise ValueError("loop start outside the stream")
        if fmt == FORMAT_ADPCM and loop_start % bsamp:
            raise ValueError("ADPCM loop start must be a multiple of %d samples" % bsamp)
    num_blocks = (total + bsamp - 1) // bsamp
    last_samples = total - (num_blocks - 1) * bsamp

    per_ch = []
    for ch in channels:
        if fmt == FORMAT_ADPCM and loop_start is not None:
            blocks = adpcm_encode_looped(ch, bsamp, loop_start)
        elif fmt == FORMAT_ADPCM:
            blocks = adpcm_encode(ch, bsamp)[0]
        elif fmt == FORMAT_PCM16:
            raw = struct.pack("<%dh" % total, *[max(-32768, min(32767, int(s))) for s in ch])
            blocks = [raw[i * block_size:(i + 1) * block_size] for i in range(num_blocks)]
        else:
            raw = struct.pack("<%db" % total, *[max(-128, min(127, int(s) >> 8)) for s in ch])
            blocks = [raw[i * block_size:(i + 1) * block_size] for i in range(num_blocks)]
        per_ch.append(blocks)
    last_size = max(len(_pad4(per_ch[c][-1])) for c in range(nch))

    data = bytearray()
    for b in range(num_blocks):
        size = block_size if b < num_blocks - 1 else last_size
        for c in range(nch):
            blk = per_ch[c][b]
            data += blk + b"\x00" * (size - len(blk))

    info = StrmInfo(format=fmt, loop_flag=1 if loop_start is not None else 0, channels=nch,
                    sample_rate=int(round(sample_rate)), timer=timer,
                    loop_start=loop_start or 0, loop_end=total, data_offset=HEADER_SIZE,
                    num_blocks=num_blocks, block_size=block_size, block_samples=bsamp,
                    last_block_size=last_size, last_block_samples=last_samples)
    file_size = HEADER_SIZE + len(data)
    out = bytearray()
    out += struct.pack("<4sHHIHH", b"STRM", 0xFEFF, 0x0100, file_size, 0x10, 2)
    out += struct.pack("<4sI", b"HEAD", 0x50)
    out += struct.pack("<BBBBHHIIIIIIII", fmt, info.loop_flag, nch, 0, info.sample_rate, timer,
                       info.loop_start, info.loop_end, info.data_offset, num_blocks, block_size,
                       bsamp, last_size, last_samples)
    out += b"\x00" * 32
    out += struct.pack("<4sI", b"DATA", 8 + len(data))
    assert len(out) == HEADER_SIZE
    out += data
    return bytes(out), info


def parse_strm(blob):
    """Parses the header the way OpenFileStream does (a raw read of NNSSndStrmData), plus the
    container checks NNS itself skips."""
    if blob[:4] != b"STRM":
        raise ValueError("not a STRM file")
    bom, version, fsize, hsize, nblk = struct.unpack_from("<HHIHH", blob, 4)
    if blob[0x10:0x14] != b"HEAD":
        raise ValueError("missing HEAD block")
    v = struct.unpack_from("<BBBBHHIIIIIIII", blob, 0x18)
    info = StrmInfo(format=v[0], loop_flag=v[1], channels=v[2], sample_rate=v[4], timer=v[5],
                    loop_start=v[6], loop_end=v[7], data_offset=v[8], num_blocks=v[9],
                    block_size=v[10], block_samples=v[11], last_block_size=v[12],
                    last_block_samples=v[13])
    info.file_size = fsize
    info.bom, info.version, info.header_size, info.blocks = bom, version, hsize, nblk
    return info


def validate(blob, info=None):
    """Returns a list of problems that would make NNS misbehave (empty = good)."""
    info = info or parse_strm(blob)
    p = []
    if info.bom != 0xFEFF or info.header_size != 0x10 or info.blocks != 2:
        p.append("unexpected file header fields")
    if info.file_size != len(blob):
        p.append("file size field %d != %d" % (info.file_size, len(blob)))
    if blob[0x60:0x64] != b"DATA" or info.data_offset != HEADER_SIZE:
        p.append("DATA block not at 0x60 / data offset not 0x68")
    if info.format not in FORMAT_NAMES:
        p.append("bad format %d" % info.format)
    if not 1 <= info.channels <= NNS_MAX_CHANNELS:
        p.append("bad channel count %d" % info.channels)
    if not 1 <= info.timer <= 2047:
        p.append("timer %d out of NNS_SND_STRM_TIMER range" % info.timer)
    if info.block_samples != block_samples_for(info.format, info.block_size):
        p.append("samples per block does not match block size")
    if info.block_size > block_size_limit(info.format):
        p.append("block size %d too large for offset starts" % info.block_size)
    exp_total = (info.num_blocks - 1) * info.block_samples + info.last_block_samples
    if info.loop_end != exp_total:
        p.append("loop end %d != block sample total %d" % (info.loop_end, exp_total))
    if info.format == FORMAT_ADPCM and info.last_block_size < 4 + (info.last_block_samples + 1) // 2:
        p.append("last block too short")
    exp_len = info.data_offset + ((info.num_blocks - 1) * info.block_size + info.last_block_size) * info.channels
    if exp_len > len(blob):
        p.append("file truncated: need %d bytes, have %d" % (exp_len, len(blob)))
    if info.loop_flag:
        if info.loop_start >= info.loop_end:
            p.append("loop start past loop end")
        if info.format == FORMAT_ADPCM and info.loop_start % info.block_samples:
            p.append("ADPCM loop start %d not block aligned (NNS keeps the end-of-stream ADPCM "
                     "state when it jumps to a mid-block loop start)" % info.loop_start)
    return p


def decode_linear(blob):
    """Straight decode of every channel from sample 0 to loop end. Returns (info, channels)."""
    info = parse_strm(blob)
    out = [[] for _ in range(info.channels)]
    for b in range(info.num_blocks):
        last = b == info.num_blocks - 1
        size = info.last_block_size if last else info.block_size
        count = info.last_block_samples if last else info.block_samples
        base = info.data_offset + b * info.block_size * info.channels
        for c in range(info.channels):
            blk = blob[base + c * size: base + (c + 1) * size]
            if info.format == FORMAT_ADPCM:
                out[c].extend(adpcm_decode_block(blk, count))
            elif info.format == FORMAT_PCM16:
                out[c].extend(struct.unpack_from("<%dh" % count, blk))
            else:
                out[c].extend(s << 8 for s in struct.unpack_from("<%db" % count, blk))
    return info, out


class NnsStrmPlayer:
    """Re-implementation of MakeWaveData() from sndarc_stream.c: reads the file in the same
    chunks, with the same block/offset arithmetic, ADPCM state carry, dirty-start and loop
    handling. Used to verify files exactly as the game will play them."""

    def __init__(self, blob, offset_ms=0):
        self.blob = blob
        self.info = parse_strm(blob)
        i = self.info
        self.cur = i.sample_rate * offset_ms // 1000  # PrepareStrm
        self.dirty = self.cur != 0 and i.format == FORMAT_ADPCM
        self.finish = False
        self.state = [[0, 0] for _ in range(i.channels)]

    def _read(self, size, offset):
        return self.blob[offset:offset + size]

    def make_wave_data(self, buf_len):
        """One StrmCallback worth of data: buf_len bytes per channel (PCM16 out, or PCM8)."""
        i = self.info
        nch = i.channels
        bps = 1 if i.format == FORMAT_PCM8 else 2
        out = [[0] * (buf_len // bps) for _ in range(nch)]
        dest = 0  # in samples
        rest = buf_len
        while rest > 0:
            if self.finish:
                break
            block_no = self.cur // i.block_samples
            if block_no < i.num_blocks - 1:
                block_size, block_samples = i.block_size, i.block_samples
            else:
                block_size, block_samples = i.last_block_size, i.last_block_samples
            bos = self.cur - block_no * i.block_samples
            samples = rest // bps
            if self.dirty:
                if bos == 0:
                    self.dirty = False
                else:
                    samples = bos
                    bos = 0
            loop = False
            if bos + samples >= block_samples:
                samples = block_samples - bos
                if block_no >= i.num_blocks - 1:
                    if i.loop_flag:
                        loop = True
                    else:
                        self.finish = True
            if i.format == FORMAT_PCM8:
                boff, read_size, size = bos, samples, samples
            elif i.format == FORMAT_PCM16:
                boff, read_size, size = bos * 2, samples * 2, samples * 2
            else:
                end_sample = (bos + samples + 1) >> 1
                boff = bos >> 1
                read_size = end_sample - boff
                if bos == 0:
                    read_size += 4
                else:
                    boff += 4
                size = samples * 2
            offset = boff + block_no * i.block_size * nch + i.data_offset
            dirty_pass = self.dirty
            for ch in range(nch):
                src = self._read(read_size, offset + ch * block_size)
                if len(src) != read_size:
                    self.finish = True
                    size = samples = 0
                    loop = False
                    break
                if i.format == FORMAT_ADPCM:
                    st = self.state[ch]
                    p = 0
                    if bos == 0:
                        st[0], st[1], _ = struct.unpack_from("<hBB", src, 0)
                        p = 4
                    end = bos + samples
                    k = bos
                    vals = []
                    if k & 1:
                        vals.append(adpcm_decode_sample((src[p] >> 4) & 0x0F, st))
                        k += 1
                        p += 1
                    while k < (end & ~1):
                        vals.append(adpcm_decode_sample(src[p] & 0x0F, st))
                        vals.append(adpcm_decode_sample((src[p] >> 4) & 0x0F, st))
                        k += 2
                        p += 1
                    if k < end:
                        vals.append(adpcm_decode_sample(src[p] & 0x0F, st))
                elif i.format == FORMAT_PCM16:
                    vals = list(struct.unpack("<%dh" % samples, src))
                else:
                    vals = list(struct.unpack("<%db" % samples, src))
                if not dirty_pass:  # the dirty pass decodes into the buffer and is overwritten
                    out[ch][dest:dest + len(vals)] = vals
            if self.dirty:
                self.dirty = False
                continue
            if loop:
                self.cur = i.loop_start
            else:
                self.cur += samples
            dest += size // bps
            rest -= size
        return out

    def render(self, total_samples):
        """Plays like NNS: one 1024-sample setup fill, then 256-sample callbacks."""
        nch = self.info.channels
        res = [[] for _ in range(nch)]
        first = True
        while len(res[0]) < total_samples:
            chunk = self.make_wave_data(NNS_CH_BUFFER_BYTES if first else NNS_CALLBACK_BYTES)
            first = False
            for c in range(nch):
                res[c].extend(chunk[c])
            if self.finish and not self.info.loop_flag:
                break
        return [c[:total_samples] for c in res]


# ---------------------------------------------------------------- WAV I/O and DSP

def read_wav(path):
    """Returns (rate, [channel sample lists]) with samples scaled to 16-bit ints."""
    with wave.open(path, "rb") as w:
        nch, width, rate, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    if width == 1:
        vals = [(b - 128) << 8 for b in raw]
    elif width == 2:
        vals = list(struct.unpack("<%dh" % (len(raw) // 2), raw))
    elif width == 3:
        vals = [int.from_bytes(raw[i:i + 3], "little", signed=True) >> 8 for i in range(0, len(raw), 3)]
    elif width == 4:
        vals = [v >> 16 for v in struct.unpack("<%di" % (len(raw) // 4), raw)]
    else:
        raise ValueError("unsupported sample width %d" % width)
    return rate, [vals[c::nch] for c in range(nch)]


def write_wav(path, rate, channels):
    nch = len(channels)
    n = len(channels[0])
    inter = [0] * (n * nch)
    for c, ch in enumerate(channels):
        inter[c::nch] = [max(-32768, min(32767, int(round(s)))) for s in ch]
    with wave.open(path, "wb") as w:
        w.setnchannels(nch)
        w.setsampwidth(2)
        w.setframerate(int(round(rate)))
        w.writeframes(struct.pack("<%dh" % len(inter), *inter))


def resample(x, rate_in, rate_out, half_taps=24, phases=512, tail=None):
    """Windowed-sinc (Blackman) resampler with a quantized phase table. x: list of numbers.
    tail: optional samples appended as right-hand context (e.g. the loop start, for loops).
    Returns a list of floats of length round(len(x) * rate_out / rate_in)."""
    if abs(rate_in - rate_out) < 1e-9:
        return [float(v) for v in x]
    ratio = rate_out / rate_in
    cutoff = min(1.0, ratio) * 0.97  # relative to the input Nyquist
    taps = 2 * half_taps
    table = []
    for p in range(phases + 1):
        frac = p / phases
        k = []
        for t in range(taps):
            pos = t - (half_taps - 1) - frac  # distance from the output point, in input samples
            arg = pos * cutoff
            s = cutoff if arg == 0 else math.sin(math.pi * arg) / (math.pi * pos)
            w = 0.42 + 0.5 * math.cos(math.pi * pos / half_taps) + 0.08 * math.cos(2 * math.pi * pos / half_taps)
            k.append(s * w if abs(pos) < half_taps else 0.0)
        norm = sum(k)
        table.append([v / norm for v in k])
    padded = [0.0] * half_taps + [float(v) for v in x] + [float(v) for v in (tail or [])] + [0.0] * (half_taps + 2)
    n_out = int(round(len(x) * ratio))
    out = [0.0] * n_out
    step = 1.0 / ratio
    for j in range(n_out):
        pos = j * step
        base = int(pos)
        frac = pos - base
        kern = table[int(frac * phases + 0.5)]
        start = base + half_taps - (half_taps - 1)
        out[j] = sum(map(float.__mul__, kern, padded[start:start + taps]))
    return out


def peak(channels):
    return max((abs(v) for ch in channels for v in ch), default=0)


def rms(channels):
    n = sum(len(ch) for ch in channels)
    if not n:
        return 0.0
    return math.sqrt(sum(v * v for ch in channels for v in ch) / n)


def db_to_lin(db):
    return 10 ** (db / 20.0)


def snr_db(ref, test):
    num = sum(float(a) * a for a in ref)
    den = sum((float(a) - b) ** 2 for a, b in zip(ref, test))
    if den == 0:
        return float("inf")
    return 10 * math.log10(num / den)
