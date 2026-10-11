"""Overworld sprite candidate pipeline: cut, convert to the Platinum walker layout, preview."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent))

CELL = 32
FACINGS = ['up', 'down', 'left', 'right']
OUT = Path('/tmp/a1r3/ow_sprites')
SRC = Path('/tmp/a1r3/src')
BG = (196, 198, 190)          # neutral preview background
TRANSPARENT_RGB = (128, 160, 128)
SCALE = 4


def font(size):
    return ImageFont.load_default(size=size)


# ---------------------------------------------------------------- cutting

def to_rgba_cell(img, box, bg_colors):
    """Crop box from an RGB image; colours in bg_colors become transparent. Pads to 32x32."""
    c = img.crop(box).convert('RGBA')
    px = c.load()
    for y in range(c.height):
        for x in range(c.width):
            r, g, b, a = px[x, y]
            if a == 0 or (r, g, b) in bg_colors:
                px[x, y] = (0, 0, 0, 0)
    if c.size != (CELL, CELL):
        o = Image.new('RGBA', (CELL, CELL), (0, 0, 0, 0))
        o.paste(c, (0, 0))
        c = o
    return c


def grid(img, ox, oy, cols, rows, pitch=32, size=32, bg=None, extra_bg=()):
    """Cells of a block whose top-left cell starts at (ox, oy). bg defaults to the pixel at (ox, oy)."""
    rgb = img.convert('RGB')
    if bg is None:
        bg = rgb.getpixel((ox, oy))
    bgs = {bg, *extra_bg}
    out = []
    for r in range(rows):
        row = []
        for c in range(cols):
            x, y = ox + c * pitch, oy + r * pitch
            cell = rgb.crop((x, y, x + size, y + size)).convert('RGBA')
            px = cell.load()
            for j in range(size):
                for i in range(size):
                    if px[i, j][:3] in bgs:
                        px[i, j] = (0, 0, 0, 0)
            row.append(cell)
        out.append(row)
    return out


def mirror(im):
    return ImageOps.mirror(im)


def walk_bw3(cells):
    """Rows up/down/left/right, cols stand/stepA/stepB."""
    return {f: [cells[i][0], cells[i][1], cells[i][0], cells[i][2]] for i, f in enumerate(FACINGS)}


def walk_bw2(cells):
    """BW simple NPC: rows up/down/left (stand, step) + right (stand only)."""
    up, down, left = cells[0], cells[1], cells[2]
    w = {
        'up': [up[0], up[1], up[0], mirror(up[1])],
        'down': [down[0], down[1], down[0], mirror(down[1])],
        'left': [left[0], left[1], left[0], left[1]],
    }
    w['right'] = [mirror(x) for x in w['left']]
    return w


def emerald_frames(path):
    """pret pokeemerald sheet: index 0 transparent, 32x32 frames in a row."""
    p = Image.open(path)
    pal = p.getpalette()
    n = p.width // CELL
    frames = []
    for k in range(n):
        c = p.crop((k * CELL, 0, (k + 1) * CELL, CELL))
        o = Image.new('RGBA', (CELL, CELL), (0, 0, 0, 0))
        po = o.load()
        data = list(c.getdata())
        for i, v in enumerate(data):
            if v:
                po[i % CELL, i // CELL] = (pal[3 * v], pal[3 * v + 1], pal[3 * v + 2], 255)
        frames.append(o)
    return frames


def walk_emerald(fr):
    """frames: 0 down, 1 up, 2 left, 3-4 down steps, 5-6 up steps, 7-8 left steps."""
    w = {
        'up': [fr[1], fr[5], fr[1], fr[6]],
        'down': [fr[0], fr[3], fr[0], fr[4]],
        'left': [fr[2], fr[7], fr[2], fr[8]],
    }
    w['right'] = [mirror(x) for x in w['left']]
    return w


# ---------------------------------------------------------------- normalising

def bbox(im):
    return im.getchannel('A').getbbox()


def shift(im, dx, dy):
    o = Image.new('RGBA', im.size, (0, 0, 0, 0))
    o.paste(im, (dx, dy), im)
    return o


def placement_shift(walk):
    """Shift so the down-facing stand frame has feet on y=29 and is centred on x=15 (stock placement)."""
    b = bbox(walk['down'][0])
    dy = 29 - (b[3] - 1)
    dx = 15 - (b[0] + b[2] - 1) // 2
    return dx, dy


def apply_shift(frames, dx, dy):
    if isinstance(frames, dict):
        return {k: [shift(f, dx, dy) for f in v] for k, v in frames.items()}
    return [shift(f, dx, dy) for f in frames]


def snap(c):
    """BGR555 round trip, as the DS shows it."""
    return tuple(((v >> 3) << 3) | (v >> 5) for v in c[:3])


def opaque_colors(frames):
    cols = {}
    for f in frames:
        for p in f.getdata():
            if p[3] >= 128:
                cols[p[:3]] = cols.get(p[:3], 0) + 1
    return cols


def build_palette(frames, max_colors=15):
    """Return (palette list of RGB for indices 1.., mapping rgb->index, original count, snapped count)."""
    cols = opaque_colors(frames)
    orig = len(cols)
    snapped = {}
    for c, n in cols.items():
        s = snap(c)
        snapped[s] = snapped.get(s, 0) + n
    if len(snapped) <= max_colors:
        pal = sorted(snapped, key=lambda c: -snapped[c])
        mapping = {c: pal.index(snap(c)) + 1 for c in cols}
        return pal, mapping, orig, len(snapped)
    # quantize: build a strip weighted by counts, median cut to max_colors
    strip = Image.new('RGB', (len(snapped), 1))
    strip.putdata(list(snapped))
    q = strip.quantize(colors=max_colors, method=Image.Quantize.MEDIANCUT)
    qp = q.getpalette()[: 3 * max_colors]
    pal = [snap(tuple(qp[3 * i: 3 * i + 3])) for i in range(max_colors)]
    def nearest(c):
        return min(range(len(pal)), key=lambda i: sum((a - b) ** 2 for a, b in zip(c, pal[i])))
    mapping = {c: nearest(snap(c)) + 1 for c in cols}
    return pal, mapping, orig, len(snapped)


def indexize(frame, mapping, pal):
    """RGBA frame -> list of indices (0 transparent) and the re-rendered RGBA."""
    idx = []
    out = Image.new('RGBA', frame.size, (0, 0, 0, 0))
    po = out.load()
    for i, p in enumerate(frame.getdata()):
        if p[3] < 128:
            idx.append(0)
        else:
            k = mapping[p[:3]]
            idx.append(k)
            po[i % frame.width, i // frame.width] = pal[k - 1] + (255,)
    return idx, out


def write_indexed(path, frames_rows, pal, cols=4):
    """frames_rows: list of rows, each a list of index lists (32x32). Writes a 4-bit indexed PNG."""
    rows = len(frames_rows)
    W, H = cols * CELL, rows * CELL
    im = Image.new('P', (W, H), 0)
    data = [0] * (W * H)
    for r, row in enumerate(frames_rows):
        for c, idx in enumerate(row):
            for i, v in enumerate(idx):
                x, y = c * CELL + i % CELL, r * CELL + i // CELL
                data[y * W + x] = v
    im.putdata(data)
    full = list(TRANSPARENT_RGB) + [v for c in pal for v in c]
    full += [0] * (48 - len(full))
    im.putpalette(full[:48])
    im.save(path, bits=4, optimize=False)


# ---------------------------------------------------------------- previews

def upscale(im, s=SCALE):
    return im.resize((im.width * s, im.height * s), Image.NEAREST)


def on_bg(im, bg=BG):
    o = Image.new('RGBA', im.size, bg + (255,))
    o.alpha_composite(im)
    return o.convert('RGB')


def render_sheet(title, subtitle, walk, extras, pal, path):
    """Labelled 4x preview: walk rows plus extra sets."""
    s = SCALE
    cw = CELL * s
    lab_w = 110
    pad = 10
    f_t, f_s, f_l = font(22), font(14), font(15)
    col_labels = ['stand', 'step A', 'stand', 'step B']
    extra_rows = []
    for name, frames in extras:
        extra_rows.append((name, frames))
    max_extra = max([sum(f.width + 2 for f in fr) // CELL for _, fr in extra_rows] + [4])
    W = lab_w + max(4, max_extra) * (cw + 6) + pad * 2
    header = 70
    H = header + 24 + 4 * (cw + 6) + (sum(max(f.height for f in fr) * s + 30 for _, fr in extra_rows) + (34 if extra_rows else 0)) + 50
    im = Image.new('RGB', (W, H), (238, 238, 232))
    d = ImageDraw.Draw(im)
    d.text((pad, 8), title, fill=(20, 20, 20), font=f_t)
    d.text((pad, 38), subtitle, fill=(70, 70, 70), font=f_s)
    y = header
    for c, lab in enumerate(col_labels):
        d.text((lab_w + c * (cw + 6) + 4, y), lab, fill=(40, 40, 40), font=f_l)
    y += 24
    for r, fac in enumerate(FACINGS):
        d.text((pad, y + cw // 2 - 8), fac, fill=(40, 40, 40), font=f_l)
        for c in range(4):
            x = lab_w + c * (cw + 6)
            im.paste(upscale(on_bg(walk[fac][c])), (x, y))
        y += cw + 6
    if extra_rows:
        y += 6
        d.text((pad, y), 'Extra sets in the source (raw frames, same 4x scale):', fill=(40, 40, 40), font=f_l)
        y += 28
        for name, frames in extra_rows:
            d.text((pad, y + 8), name, fill=(40, 40, 40), font=f_l)
            x = lab_w
            for f in frames:
                im.paste(upscale(on_bg(f)), (x, y))
                x += f.width * s + 6
            y += max(f.height for f in frames) * s + 30
    # palette swatches
    x = pad
    d.text((x, H - 30), 'palette:', fill=(40, 40, 40), font=f_s)
    x += 64
    for c in pal:
        d.rectangle([x, H - 32, x + 18, H - 14], fill=c, outline=(0, 0, 0))
        x += 22
    im.save(path)


def render_gif(walk, path, order=('down', 'left', 'up', 'right'), cycles=2, ms=140, label=None):
    frames = []
    seq = [1, 0, 3, 2]  # stepA, stand, stepB, stand
    for fac in order:
        for _ in range(cycles):
            for k in seq:
                fr = upscale(on_bg(walk[fac][k]))
                if label:
                    canvas = Image.new('RGB', (fr.width, fr.height + 22), BG)
                    canvas.paste(fr, (0, 22))
                    ImageDraw.Draw(canvas).text((4, 3), label, fill=(30, 30, 30), font=font(13))
                    fr = canvas
                frames.append(fr.convert('P', palette=Image.Palette.ADAPTIVE, colors=64))
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=ms, loop=0, disposal=1)


# ---------------------------------------------------------------- candidate

class Candidate:
    def __init__(self, char, key, name, walk, extras=(), run=None, meta=None):
        self.char, self.key, self.name = char, key, name
        self.walk_raw, self.extras_raw, self.run_raw = walk, list(extras), run
        self.meta = meta or {}

    def process(self):
        dx, dy = placement_shift(self.walk_raw)
        self.dx, self.dy = dx, dy
        walk = apply_shift(self.walk_raw, dx, dy)
        run = apply_shift(self.run_raw, dx, dy) if self.run_raw else None
        allf = [f for fac in FACINGS for f in walk[fac]]
        if run:
            allf += [f for fac in FACINGS for f in run[fac]]
        pal, mapping, orig, snapped = build_palette(allf)
        self.pal, self.orig_colors, self.snapped_colors = pal, orig, snapped
        self.walk = {}
        self.walk_idx = {}
        for fac in FACINGS:
            self.walk_idx[fac], self.walk[fac] = zip(*[indexize(f, mapping, pal) for f in walk[fac]])
        self.run = self.run_idx = None
        if run:
            self.run, self.run_idx = {}, {}
            for fac in FACINGS:
                self.run_idx[fac], self.run[fac] = zip(*[indexize(f, mapping, pal) for f in run[fac]])
        # clipping check: anything shifted out of the cell?
        self.clipped = any(
            (bbox(f) is None) for fac in FACINGS for f in walk[fac])
        self.extras = []
        for name, frames in self.extras_raw:
            fr = [shift(f, dx, dy) if f.size == (CELL, CELL) else f for f in frames]
            self.extras.append((name, fr))
        return self

    def write(self):
        d = OUT / self.char
        d.mkdir(parents=True, exist_ok=True)
        base = d / self.key
        write_indexed(f'{base}_platinum_walk.png', [list(self.walk_idx[f]) for f in FACINGS], self.pal)
        if self.run:
            write_indexed(f'{base}_platinum_walk_run.png',
                          [list(self.walk_idx[f]) for f in FACINGS] + [list(self.run_idx[f]) for f in FACINGS], self.pal)
        sets = self.meta.get('sets', 'walk')
        sub = f"{self.meta.get('source_short', '')} | sets: {sets} | colours {self.orig_colors} -> {len(self.pal)} (+transparent)"
        extras = list(self.extras)
        if self.run:
            extras = [('run', [self.run[f][k] for f in FACINGS for k in (0, 1, 3)])] + extras
        render_sheet(f'{self.meta.get("char_title", self.char)}: {self.name}', sub, self.walk, extras, self.pal,
                     f'{base}_sheet.png')
        render_gif(self.walk, f'{base}_walk.gif', label=self.name)
        if self.run:
            render_gif(self.run, f'{base}_run.gif', ms=90, label=self.name + ' (run)')
        return self
