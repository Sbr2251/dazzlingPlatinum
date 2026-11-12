"""Image helpers for render_compare: BMP reading, PNG writing, pixel diffing.

Stdlib only. Images are held as an RGBImage: width, height and three
top-down byte planes (R, G, B), so row slices and plane comparisons stay fast
in pure Python.
"""
import struct
import zlib


class RGBImage:
    __slots__ = ("w", "h", "r", "g", "b")

    def __init__(self, w, h, r, g, b):
        self.w, self.h, self.r, self.g, self.b = w, h, r, g, b

    def row(self, plane, y):
        return plane[y * self.w:(y + 1) * self.w]


def _mask_shift(mask):
    if mask == 0:
        return None
    shift = 0
    while not (mask >> shift) & 1:
        shift += 1
    return shift


def load_bmp(path):
    """Read an uncompressed 24/32-bit BMP (BI_RGB or BI_BITFIELDS)."""
    with open(path, "rb") as f:
        data = f.read()
    if data[:2] != b"BM" or len(data) < 54:
        raise ValueError("%s: not a BMP" % path)
    off = struct.unpack_from("<I", data, 10)[0]
    hdr = struct.unpack_from("<I", data, 14)[0]
    w, h = struct.unpack_from("<ii", data, 18)
    bpp, comp = struct.unpack_from("<HI", data, 28)
    if bpp not in (24, 32) or comp not in (0, 3) or w <= 0 or h == 0:
        raise ValueError("%s: unsupported BMP (bpp=%d compression=%d)" % (path, bpp, comp))
    bytes_pp = bpp // 8
    # Byte offset of each channel inside a pixel (little-endian pixel word).
    pos = {"b": 0, "g": 1, "r": 2}
    if comp == 3:
        if hdr >= 40:
            masks = struct.unpack_from("<III", data, 54)
        else:
            masks = struct.unpack_from("<III", data, 14 + hdr)
        for name, m in zip("rgb", masks):
            sh = _mask_shift(m)
            if sh is None or sh % 8 or (m >> sh) != 0xFF:
                raise ValueError("%s: unsupported BMP channel mask %#x" % (path, m))
            pos[name] = sh // 8
    top_down = h < 0
    h = abs(h)
    stride = (w * bytes_pp + 3) & ~3
    planes = {"r": bytearray(w * h), "g": bytearray(w * h), "b": bytearray(w * h)}
    for y in range(h):
        src = off + (y if top_down else h - 1 - y) * stride
        row = data[src:src + w * bytes_pp]
        for name in "rgb":
            planes[name][y * w:(y + 1) * w] = row[pos[name]::bytes_pp]
    return RGBImage(w, h, bytes(planes["r"]), bytes(planes["g"]), bytes(planes["b"]))


def write_png(path, w, h, rgb_rows):
    """rgb_rows: iterable of h bytes objects, each 3*w bytes (RGB)."""
    raw = bytearray()
    for row in rgb_rows:
        raw.append(0)
        raw += row

    def chunk(tag, payload):
        body = tag + payload
        return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 1)) + chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


def _interleave(img, y):
    row = bytearray(3 * img.w)
    row[0::3] = img.row(img.r, y)
    row[1::3] = img.row(img.g, y)
    row[2::3] = img.row(img.b, y)
    return bytes(row)


def write_image_png(path, img):
    write_png(path, img.w, img.h, (_interleave(img, y) for y in range(img.h)))


def _region_stats(a, b, y0, y1, thresh):
    """Stats over rows [y0, y1). thresh: a pixel counts as 'over' when its max
    channel delta is > thresh. Returns a dict."""
    w = a.w
    any_diff = over = 0
    max_delta = 0
    bbox = None  # x0, y0, x1, y1 inclusive, of pixels with any difference
    obox = None
    for y in range(y0, y1):
        ra, rb = a.row(a.r, y), b.row(b.r, y)
        ga, gb = a.row(a.g, y), b.row(b.g, y)
        ba, bb = a.row(a.b, y), b.row(b.b, y)
        if ra == rb and ga == gb and ba == bb:
            continue
        xs = None
        for x in range(w):
            d = max(abs(ra[x] - rb[x]), abs(ga[x] - gb[x]), abs(ba[x] - bb[x]))
            if not d:
                continue
            any_diff += 1
            if d > max_delta:
                max_delta = d
            if bbox is None:
                bbox = [x, y, x, y]
            else:
                if x < bbox[0]: bbox[0] = x
                if x > bbox[2]: bbox[2] = x
                bbox[3] = y
            if d > thresh:
                over += 1
                if obox is None:
                    obox = [x, y, x, y]
                else:
                    if x < obox[0]: obox[0] = x
                    if x > obox[2]: obox[2] = x
                    obox[3] = y
    total = w * (y1 - y0)
    return {
        "pixels": total,
        "diff_pixels": any_diff,
        "diff_pct": 100.0 * any_diff / total if total else 0.0,
        "over_pixels": over,
        "over_pct": 100.0 * over / total if total else 0.0,
        "max_delta": max_delta,
        "bbox": bbox,
        "over_bbox": obox,
    }


def compare(a, b, max_delta=0):
    """Compare two RGBImages. Returns a dict (see keys below); screens are
    the two DS screens of the vertical layout (top half, bottom half)."""
    if (a.w, a.h) != (b.w, b.h):
        return {"size_mismatch": True, "a_size": [a.w, a.h], "b_size": [b.w, b.h],
                "identical": False, "max_delta": 255, "over_pct": 100.0, "diff_pct": 100.0}
    res = _region_stats(a, b, 0, a.h, max_delta)
    res["size_mismatch"] = False
    res["identical"] = res["diff_pixels"] == 0
    res["size"] = [a.w, a.h]
    half = a.h // 2
    res["screens"] = {
        "top": _region_stats(a, b, 0, half, max_delta),
        "bottom": _region_stats(a, b, half, a.h, max_delta),
    }
    # Bounding boxes of the bottom screen are reported in its own coordinates.
    bot = res["screens"]["bottom"]
    for key in ("bbox", "over_bbox"):
        if bot[key]:
            bot[key] = [bot[key][0], bot[key][1] - half, bot[key][2], bot[key][3] - half]
    return res


def write_diff_png(path, a, b, amp=8):
    """Side-by-side A | B | amplified difference. Any non-zero delta is shown at
    least at brightness 80 so single-LSB differences are visible."""
    if (a.w, a.h) != (b.w, b.h):
        w, h = max(a.w, b.w), max(a.h, b.h)
        pad = lambda img: _pad(img, w, h)
        a, b = pad(a), pad(b)
    w, h = a.w, a.h
    rows = []
    for y in range(h):
        ra, rb = _interleave(a, y), _interleave(b, y)
        if ra == rb:
            drow = bytes(3 * w)
        else:
            drow = bytearray(3 * w)
            for x in range(w):
                i = 3 * x
                d = max(abs(ra[i] - rb[i]), abs(ra[i + 1] - rb[i + 1]), abs(ra[i + 2] - rb[i + 2]))
                if d:
                    v = min(255, max(80, d * amp))
                    drow[i] = v
                    drow[i + 1] = v // 3
                    drow[i + 2] = 0
            drow = bytes(drow)
        rows.append(ra + rb + drow)
    write_png(path, 3 * w, h, rows)


def _pad(img, w, h):
    def padplane(plane):
        out = bytearray(w * h)
        for y in range(img.h):
            out[y * w:y * w + img.w] = plane[y * img.w:(y + 1) * img.w]
        return bytes(out)
    return RGBImage(w, h, padplane(img.r), padplane(img.g), padplane(img.b))
