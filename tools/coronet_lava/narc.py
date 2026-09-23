"""Minimal NARC reader/writer for unnamed archives (BTAF + empty BTNF + GMIF), as used by the prebuilt field NARCs."""
import struct


def read_files(path):
    """Returns (header, btnf, files)."""
    d = open(path, "rb").read()
    assert d[:4] == b"NARC"
    hdr_size, n_sections = struct.unpack_from("<HH", d, 12)
    sections, o = {}, hdr_size
    for _ in range(n_sections):
        magic, size = d[o:o + 4], struct.unpack_from("<I", d, o + 4)[0]
        sections[magic] = d[o:o + size]
        o += size
    btaf, gmif = sections[b"BTAF"], sections[b"GMIF"]
    n = struct.unpack_from("<H", btaf, 8)[0]
    files = []
    for i in range(n):
        start, end = struct.unpack_from("<II", btaf, 12 + 8 * i)
        files.append(gmif[8 + start:8 + end])
    return d[:hdr_size], sections[b"BTNF"], files


def write_files(path, header, btnf, files):
    """Files are 4-byte aligned with 0xFF padding, matching the stock archives."""
    offsets, blob = [], b""
    for f in files:
        blob += b"\xff" * (-len(blob) % 4)
        offsets.append((len(blob), len(blob) + len(f)))
        blob += f
    blob += b"\xff" * (-len(blob) % 4)
    btaf = b"BTAF" + struct.pack("<IHH", 12 + 8 * len(files), len(files), 0)
    btaf += b"".join(struct.pack("<II", a, b) for a, b in offsets)
    gmif = b"GMIF" + struct.pack("<I", 8 + len(blob)) + blob
    body = btaf + btnf + gmif
    header = bytearray(header)
    struct.pack_into("<I", header, 8, len(header) + len(body))
    with open(path, "wb") as f:
        f.write(bytes(header) + body)
