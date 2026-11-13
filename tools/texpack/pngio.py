"""Minimal PNG read/write (8-bit, stdlib only) shared by texpack tools."""
import struct, zlib

def read_png(path):
    data = open(path, 'rb').read()
    assert data[:8] == b'\x89PNG\r\n\x1a\n', path
    pos, idat, plte, trns = 8, b'', None, None
    w = h = depth = ctype = None
    while pos < len(data):
        ln, typ = struct.unpack('>I4s', data[pos:pos+8]); pos += 8
        chunk = data[pos:pos+ln]; pos += ln + 4
        if typ == b'IHDR':
            w, h, depth, ctype, _, _, _ = struct.unpack('>IIBBBBB', chunk)
        elif typ == b'PLTE': plte = chunk
        elif typ == b'tRNS': trns = chunk
        elif typ == b'IDAT': idat += chunk
    assert depth == 8, (path, depth)
    ch = {0:1, 2:3, 3:1, 4:2, 6:4}[ctype]
    raw = zlib.decompress(idat)
    stride = w*ch
    out = bytearray(w*h*4)
    prev = bytearray(stride)
    p = 0
    for y in range(h):
        f = raw[p]; p += 1
        line = bytearray(raw[p:p+stride]); p += stride
        for i in range(stride):
            a = line[i-ch] if i >= ch else 0
            b = prev[i]
            c = prev[i-ch] if i >= ch else 0
            if f == 1: line[i] = (line[i] + a) & 255
            elif f == 2: line[i] = (line[i] + b) & 255
            elif f == 3: line[i] = (line[i] + ((a+b)//2)) & 255
            elif f == 4:
                pa, pb, pc = abs(b-c), abs(a-c), abs(a+b-2*c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 255
        prev = line
        for x in range(w):
            s = line[x*ch:(x+1)*ch]
            o = (y*w+x)*4
            if ctype == 6: out[o:o+4] = s
            elif ctype == 2: out[o:o+3] = s; out[o+3] = 255
            elif ctype == 0: out[o:o+3] = bytes((s[0],)*3); out[o+3] = 255
            elif ctype == 4: out[o:o+3] = bytes((s[0],)*3); out[o+3] = s[1]
            elif ctype == 3:
                idx = s[0]; out[o:o+3] = plte[idx*3:idx*3+3]
                out[o+3] = trns[idx] if trns and idx < len(trns) else 255
    return w, h, bytes(out)

def write_png(path, w, h, rgba):
    def chunk(typ, payload):
        c = struct.pack('>I', len(payload)) + typ + payload
        return c + struct.pack('>I', zlib.crc32(typ + payload) & 0xffffffff)
    raw = b''.join(b'\x00' + rgba[y*w*4:(y+1)*w*4] for y in range(h))
    png = (b'\x89PNG\r\n\x1a\n'
           + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(raw, 6))
           + chunk(b'IEND', b''))
    open(path, 'wb').write(png)
