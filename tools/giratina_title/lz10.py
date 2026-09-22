"""Nintendo LZ10 ("LZ77 type 0x10") codec, as read by MI_UncompressLZ8.

Stream: u32 header (0x10 | uncompressed_size << 8), then groups of one flag
byte (MSB first) followed by 8 tokens. Flag 0 = literal byte; flag 1 = two
bytes: ((len - 3) << 4) | ((disp - 1) >> 8), (disp - 1) & 0xFF, copying
`len` (3..18) bytes from `disp` (1..4096) bytes back.
"""

MIN_MATCH = 3
MAX_MATCH = 18
WINDOW = 4096


def compress(data: bytes, max_chain: int = 64) -> bytes:
    data = bytes(data)
    n = len(data)
    if n >= 1 << 24:
        raise ValueError("LZ10 input too large")
    out = bytearray((0x10 | (n << 8)).to_bytes(4, "little"))
    heads = {}
    pos = 0
    while pos < n:
        flag_index = len(out)
        out.append(0)
        flags = 0
        for bit in range(8):
            if pos >= n:
                break
            best_len = 0
            best_disp = 0
            if pos + MIN_MATCH <= n:
                key = data[pos:pos + MIN_MATCH]
                chain = heads.get(key)
                if chain:
                    limit = min(MAX_MATCH, n - pos)
                    for cand in reversed(chain[-max_chain:]):
                        disp = pos - cand
                        if disp > WINDOW:
                            break
                        length = MIN_MATCH
                        while length < limit and data[cand + length] == data[pos + length]:
                            length += 1
                        if length > best_len:
                            best_len = length
                            best_disp = disp
                            if length == limit:
                                break
            if best_len >= MIN_MATCH:
                flags |= 0x80 >> bit
                d = best_disp - 1
                out.append(((best_len - MIN_MATCH) << 4) | (d >> 8))
                out.append(d & 0xFF)
                step = best_len
            else:
                out.append(data[pos])
                step = 1
            for p in range(pos, min(pos + step, n - MIN_MATCH + 1)):
                heads.setdefault(data[p:p + MIN_MATCH], []).append(p)
            pos += step
        out[flag_index] = flags
    while len(out) % 4:
        out.append(0)
    return bytes(out)


def decompress(src: bytes) -> bytes:
    header = int.from_bytes(src[0:4], "little")
    if header & 0xFF != 0x10:
        raise ValueError("not LZ10")
    size = header >> 8
    out = bytearray()
    i = 4
    while len(out) < size:
        flags = src[i]
        i += 1
        for bit in range(8):
            if len(out) >= size:
                break
            if flags & (0x80 >> bit):
                b0, b1 = src[i], src[i + 1]
                i += 2
                length = (b0 >> 4) + MIN_MATCH
                disp = (((b0 & 0xF) << 8) | b1) + 1
                if disp > len(out):
                    raise ValueError("LZ10 back-reference before start")
                for _ in range(length):
                    out.append(out[-disp])
            else:
                out.append(src[i])
                i += 1
    return bytes(out[:size])
