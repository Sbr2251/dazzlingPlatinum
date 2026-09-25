"""Draw Mega Alakazam's cry frame 2 (front and back) from frame 1.

Mega Alakazam shows frame 1 for ~18 ticks, frame 2 for ~26 ticks and then
stops, so frame 2 is a one-shot gesture on battle entry and has to read at 1x.

FRONT, "Rising up for the cry" (round 8)
  - Two rigid layers (build_front): the shoulder pads with the right pad's
    dark tail and the top 1-3 px of both upper arms (FRONT_BLOCK) rise 2 px
    and lean 1 px right (FRONT_PAD_MOVE); the head -- crest, face, gem and
    the upper mustache down to frame 1's row 43 (FRONT_HEAD) -- throws back
    3 px up and 2 px right (FRONT_HEAD_MOVE).  Frame 1's lower mustache
    (rows 44+), hands, elbows, forearms and legs stay put.
  - Seams are hand-painted (FRONT_FIXES, first block): pad brown against
    the head, frame 1's b/cc edge under the jaw shadow, frame 1's own row
    43 as the mustache bridge (rows 41-42 only continue the three grey
    strands the moved top ends in), the beard's right 1/6 edge meeting the
    risen tail, and two rows of each 2-px upper arm joining the risen top
    to the fixed elbow (so each arm is only 2 px longer, not a rod).
  - The mustache tufts flick up and out 2 px, drawn behind the arms and
    legs; their roots stay attached.  The left tuft's underside has white
    diagonal strands; the right tuft's bottom reuses frame 1's ragged fur
    tips and its short leg-side edge has a V notch.
  - The centre spoon is frame 1's full spoon, unmoved (it reaches y1, as in
    frame 1).  The crest tip is trimmed 1 px so a clear pixel separates it
    from the spoon's end cap at (38,14).  The other four spoons burst out.
  - The forehead gem gets one white core pixel (7 body, 2 ring kept).

BACK, "Arms raised, elbows out" (round 8)
  - Both hands and their sleeves lift 6 px and move out (left 4, right 3,
    which puts both hands the same distance from the crest's centre line)
    as rigid pieces (no stretch).  The short yellow upper arms are redrawn
    as limbs (BACK_BANDS) in frame 1's arm colours: a 5 highlight line, 8
    body, 4 outline, one e highlight and no 3 shade row.  Each is 3 px
    (5,8,8) from the torso to the cuff, like frame 1's upper arm; its top
    outline steps down 3-3-2 toward the torso with an 8 midtone ending each
    higher run.  The cuffs are mirror-image stepped c diagonals; both
    sleeve bottoms are rounded.
  - The crest rises 1 px rigidly; only the two torso rows under its old tip
    are repainted.
  - The hip tufts and the right fur strip the sleeves used to cover are
    repainted at frame 1's width.  The tuft tops are one smooth contour
    stepping up toward the fur strip with a soft grey b/6 rim over white
    fur (no single-pixel peaks or notches); the right fur strip's f edge is
    broken by strand pixels.
  - The spoons burst outward and up.

Frame 1 is copied byte for byte from the real sprites.  Frame 2 is built only
from frame 1 (rigid moves of whole parts) plus the explicit hand-painted
pixels below, using only palette indices frame 1 already uses.

Usage (from the repo root):
  ~/.venvs/desmume/bin/python tools/mega_sprites/animate_alakazam_cry.py [--install] [--previews]

  default     write tools/mega_sprites/previews/alakazam_{front,back}.png
  --install   write res/pokemon/alakazam/forms/mega/{front,back}.png instead
  --previews  also write the preview GIFs and alakazam_frames.png
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
MEGA = ROOT / "res/pokemon/alakazam/forms/mega"
PREVIEWS = ROOT / "tools/mega_sprites/previews"
W = 80

# Palette indices (normal.pal), for reading the pixel art below:
#   1 white        2 dark brown   3 orange shade  4 black      5 yellow
#   6 light grey   7 brown        8 dark yellow   9 pale grey  a light yellow
#   b grey         c darkest brown d blue grey    e warm yellow f dark grey
# Hand-painted rows are (y, x of first char, pixels): hex palette indices,
# '.' keeps the pixel underneath, '0' clears it to transparent.

# ---------------------------------------------------------------- FRONT ----

# Spoons: (x0, y0, x1, y1) box in frame 1 (inclusive) -> (dx, dy).
FRONT_SPOONS = [
    ((21, 5, 29, 17), (-5, -2)),
    ((47, 5, 56, 17), (5, -2)),
    ((12, 15, 23, 23), (-8, -4)),
    ((54, 16, 67, 24), (8, -4)),
]

# The upper body rises in two rigid layers (spans are frame-1 coordinates,
# {y: (x0, x1) or [(x0, x1), ...]}, clipped to the body):
#   FRONT_BLOCK, the shoulder pads with the right pad's dark tail and the top
#   of each yellow upper arm, moves FRONT_PAD_MOVE (2 up, 1 toward the
#   viewer's right);
#   FRONT_HEAD, the crest and face with the whole upper mustache hanging from
#   it (frame-1 rows <= 43 between the pads), moves FRONT_HEAD_MOVE (3 up,
#   2 right), so the head throws back 1 px further than the shoulders and the
#   mustache stays attached under the jaw exactly as drawn in frame 1.
# The elbows, clasped hands, forearms, lower mustache (rows >= 44), legs and
# tufts stay put; the 2-3 rows each moved part leaves open (the arm elbows
# and the mustache between its moved top and its fixed bottom) are filled in
# FRONT_FIXES from frame 1's own rows.
FRONT_PAD_MOVE = (1, -2)
FRONT_HEAD_MOVE = (2, -3)
FRONT_BLOCK = {y: (0, 79) for y in range(0, 28)}
FRONT_BLOCK.update({y: (20, 59) for y in range(28, 42)})
FRONT_BLOCK.update({
    42: [(23, 23), (45, 55)],   # left arm top; right tail, arm top, pad tip
    43: [(22, 23), (46, 54)],
    44: [(22, 23), (46, 53)],
    45: (46, 53),
    46: (46, 53),
    47: [(46, 49), (52, 54)],   # tail; right upper arm down to its elbow
    48: (47, 49),               # the tail's tip
    49: (47, 48),
})
FRONT_HEAD = {y: (26, 51) for y in range(12, 32)}
FRONT_HEAD.update({
    32: (29, 44), 33: (28, 44), 34: (28, 44), 35: (27, 44), 36: (26, 45),
    37: (28, 45), 38: (26, 46),
    # the upper mustache: its last column slides under the right pad's edge
    39: (26, 41), 40: (25, 42), 41: (24, 42), 42: (24, 42), 43: (24, 42),
})

# Mustache tufts (the white fur at each hip): they flick up and out with the
# head.  (x0, x1, y0, y1, fur-only x range) -> (dx, dy).  A tuft is its fur
# pixels (plus its own dark outline outside the fur-only columns); it is
# pasted behind the arms and legs, and its root is filled from the tuft
# itself moved straight up, so no gap opens next to the leg.
FRONT_FUR = (1, 6, 9, 0xB, 0xD, 0xF)
FRONT_TUFT_ROOT = 2
FRONT_TUFTS = [
    ((6, 21, 54, 63), (18, 21), (-2, -2)),
    ((48, 69, 57, 70), (48, 56), (2, -2)),
]


FRONT_FIXES = [
    # Left pad against the head (the head moved 1 px further right): the
    # pad's brown fills the column the crest point and mustache left.
    (34, 27, "222"), (36, 27, "2"),
    # Right pad under the jaw's shadow (the shadow moved up with the head):
    # frame 1's b/cc edge one row under it, as in frame 1's rows 38-39.
    (36, 44, "bcc2"),
    # Mustache's left edge below the pad tip: frame 1's f edge and 6/9 band,
    # stepping from the moved top (x26) back toward the fixed bottom (x24).
    # These are frame 1's rows 41-44 next to the arm, moved with the arm.
    (39, 25, "f11"), (40, 25, "f69"),
    (41, 25, "66"), (42, 25, "6f"),
    # Mustache bridge, rows 41-43: white hair between the moved top and the
    # fixed bottom.  Row 43 is frame 1's row 43 itself (same place, the
    # hand's fingers below it are fixed too); rows 41-42 only continue the
    # three grey strands the moved top ends in -- (30,40), (40,40), (44,40)
    # -- one pixel down-left per row into frame 1's own strands at (28,43),
    # (38,43) and (42,43), so every grey pixel belongs to a line.
    (41, 27, "11" "6" "111111111" "6" "111" "6" "11"),
    (42, 27, "1" "9" "111111111" "9" "111" "9" "11"),
    (43, 24, "661161111111116111" "9" "11"),
    (40, 45, "1"),
    # Its right edge where the tail rose: frame 1's b/6 edge column moved
    # 1 px right with the tail, so the white meets the tail's own outline.
    (41, 45, "1b"), (42, 45, "16"), (43, 45, "16"),
    (44, 45, "16"), (45, 45, "16"), (46, 45, "166"), (47, 46, "66"),
    (48, 47, "6"), (49, 47, "6"),   # beard edge straight down to frame 1's x47
    # Left upper arm: its top rose with the pad (rows 40-42); the elbow
    # (rows 45-47) is frame 1's; two rows join them on the same diagonal.
    (43, 22, "83"), (44, 22, "33"),
    # Right upper arm: top rose with the pad (rows 40-45), the elbow stays;
    # two rows of the same 2-px limb join them.
    (46, 53, "55"), (47, 53, "55"),
]
FRONT_FIXES += [
    # Left tuft's underside: frame 1's fur bottom (66f, no line) then a 4
    # edge under the root running into the knee's outline.
    (61, 15, "6.6"), (63, 16, "0"),
    # Right tuft: one 4 edge from the knee to the moved bottom, with frame
    # 1's notch between two strands kept; one stray f cleared on top.
    (69, 57, "40"), (55, 56, "0"),
    (70, 58, "0"),              # frame 1's old tuft-bottom pixel
    (55, 58, "0"),              # its lone f nub on top (it hung off the leg)
    # Right tuft root: frame 1's root fur plus the moved tuft made a solid
    # grey block; keep a 3-5 px grey root along the leg (as frame 1 does)
    # and open the rest into white hair with frame 1's 1/6 strand pattern.
    (61, 53, "1"),
    (62, 52, "1111111"),
    (63, 52, "1116111"),
    (64, 54, "111611"),
    (65, 56, "1161"),
    (66, 58, "11"),
    # Left tuft's bottom row: frame 1's own "44466f4" underside (its row 63,
    # moved with the tuft), not a flat 7-px black line (round 8).
    (61, 14, "6.6"), (62, 12, "44466f4"),
    # Left tuft's underside near the leg: white strands on frame 1's
    # diagonal rhythm (down-right in pairs) so rows 59-61 are not a flat
    # grey slab.
    (59, 15, "66116"), (60, 13, "6116661"), (61, 16, "1"),
    # Right tuft's underside: frame 1's own ragged bottom moved with the
    # tuft (the zigzag right edge (67,64)/(66,65)/(67,66), the "d411b" and
    # "66 4 49" fur tips), joined to the leg by a short 4 edge (58-61,68)
    # that steps down to the knee at (57,69); a V notch at (60,68) keeps
    # that edge from reading as a ruled line.
    (67, 55, "666111" "66d411b"),
    (68, 56, "66" "44" "04" "66404" "9"), (67, 60, "4"),   # V notch at (60,68)
    # Forehead gem, lit from inside: frame 1's gem core brightened to white.
    (26, 34, "1"),
    # Crest tip: its second row's left outline would sit diagonally against
    # the fixed centre spoon's end cap (38,14); the outline steps in 1 px so
    # a clear pixel stays between them.
    (15, 39, "07"),
    # The face's outline where it lifted off the pads: left, the crest's 2
    # outline continues one more pixel down to the pad; right, a 4 corner
    # between the cheek and the right pad's c edge.
    (29, 30, "2"), (31, 29, "7"), (31, 47, "4"),
]

# ----------------------------------------------------------------- BACK ----

BACK_SPOONS = [
    ((38, 5, 41, 17), (0, -2)),
    ((24, 8, 31, 20), (-3, -4)),
    ((47, 8, 56, 20), (3, -4)),
    ((13, 16, 25, 25), (-5, -5)),
    ((54, 16, 67, 25), (5, -5)),
]

# Arms: each hand and its forearm sleeve are the body pixels in the column
# range and rows given, minus the white fur below them and minus the short
# yellow upper arm (its pixels are listed in BACK_UPPER and are redrawn by
# hand).  The piece moves rigidly by (dx, dy): no stretch, so the hand and
# sleeve keep their frame 1 shape exactly.
BACK_ARMS = [
    # x0, x1, y0, y1, (dx, dy)
    (9, 23, 28, 53, (-4, -6)),
    (52, 71, 28, 55, (3, -6)),
]
FUR = (1, 6, 9, 0xB, 0xD, 0xF)
BACK_UPPER = [          # frame 1 upper-arm pixels: {y: (x0, x1)}
    {46: (25, 27), 47: (23, 27), 48: (24, 27), 49: (22, 25), 50: (22, 24),
     51: (23, 23)},
    {46: (46, 49), 47: (46, 49), 48: (46, 50), 49: (48, 52), 50: (49, 53),
     51: (50, 53), 52: (51, 54), 53: (52, 54)},
]

# Head: the crest plus its own dark shadow row on the collar (row 38) and
# its bottom tip (row 39) rise 1 px rigidly.  Only the two torso rows the
# tip and shadow leave behind are repainted (BACK_FIXES, first block).
BACK_CREST_ROWS = {y: (26, 51) for y in range(0, 38)}
BACK_CREST_ROWS.update({38: (29, 50), 39: (34, 43)})
BACK_CREST_MOVE = (0, -1)

BACK_FIXES = [
    # Torso under the risen crest: plain back brown, continuing the left
    # shoulder highlight one pixel and filling frame 1's (33,39) notch.
    (38, 29, "72222"), (38, 44, "2222222"),
    (39, 32, "2222222c2222"),
    # Sleeve cuffs: the elbow end frame 1's upper arm used to hide is closed
    # with the sleeve's own edge colour (c), cut on a diagonal across the
    # sleeve's axis (1 px per 2 rows).  The band runs into the opening, the
    # opening itself is c (no lone 2), and the band's lower outline tucks
    # under the cuff's lower corner.
    # Left: c at x19 (rows 41-42), x18 (43-45), x17 (45-46).
    (41, 19, "c"), (42, 19, "c"),
    (43, 18, "c8"), (44, 18, "cc"),
    (45, 17, "cc4"), (46, 17, "c40"),
    (47, 16, "4400"),
    # Right (mirror): c at x55 (rows 42-43), x56 (44-46), x57 (46-47).
    (42, 55, "c"), (43, 55, "c"),
    (44, 55, "8c"), (45, 55, "cc"),
    (46, 55, "4cc"), (47, 56, "4c"),
    # Right sleeve bottom rounded: a 3-px run at row 49, stepping up to row 48.
    (48, 55, "004"), (48, 61, "44"), (49, 56, "004440"),
    # Band roots: the torso's edge (4) beside the widened root column.
    (44, 28, "4"), (45, 28, "4"), (46, 28, "4"), (47, 28, "4"),
    (48, 28, "f"),
    (45, 45, "4"), (46, 45, "4"),
    # Band top edges (round 8): an 8 midtone ends each higher run of the
    # outline, so the steps read as a slope, not a black staircase.
    (42, 22, "8"), (43, 25, "8"),
    (42, 52, "8"), (43, 49, "8"),
    # Left sleeve's bottom: its outer corner is maroon (2) instead of 4, so
    # the tip rounds into the 2-px cap as frame 1's sleeve edge does.
    (46, 15, "2"),
    # Right fur strip: frame 1's strands; the diagonal edge the old upper
    # arm covered gets a dark f edge, broken by a b strand tip poking out
    # at (50,50) and a 6 at (51,52) so it is not a ruled line.
    (50, 49, "fb"), (51, 50, "f"), (52, 51, "6"),
    (53, 52, "f"), (54, 52, "f"),
    (48, 51, "0"),   # old strip edge left dangling under the band
    # Hip tufts: the tops the sleeves used to cover.  Round 8: one smooth
    # contour stepping 1 px per run (runs of 3-5 px) up toward the fur
    # strip, with a soft grey rim (b at each step, then 6) over white fur,
    # like frame 1's outer fur edges -- no single-pixel peaks or notches.
    # Left: rim at row 53 x17-19 (frame 1's "fb6"), row 52 x20-23, row 51
    # x24-27, meeting the strip's "66" at row 50 x28-29.
    (51, 22, "00b666"), (51, 28, "b"),
    (52, 18, "00b6661111bb"),
    (53, 18, "b6111111"),
    # Right: rim at row 54 x53-57 and row 55 x58-61 (frame 1's "bd"),
    # meeting frame 1's own edge at row 56 (x62-63).
    (54, 53, "b66660"),
    (55, 53, "1111166b"),
    # The strip's edge under the right band: rows 49-51 end one pixel
    # further right each row ((49,49) b, (50,50) b, (51,50) f), no notch.
    (49, 48, "6b"),
]


# Upper arms, elbows out and raised: each is a yellow limb in frame 1's
# arm colours (one 5 highlight line on top, 8 body, 4 outline above and
# below, one e highlight; no 3 shade row), rising from the torso root to
# the sleeve.  Round 8: the body is 3 px (5,8,8) all the way, as frame 1's
# upper arm is, instead of a 4-5 px wedge at the torso; the top outline
# steps down 3-3-2 px from cuff to torso and the last pixel before each
# step is an 8 midtone (BACK_FIXES) rather than a hard black corner, the
# way frame 1's own arm top reads "484".
# {x: (top outline row, fill)}.
BACK_BANDS = {
    # left: from the cuff opening (x19) down to the torso root (x27)
    19: (42, "8c"), 20: (42, "588"), 21: (42, "e88"), 22: (42, "588"),
    23: (43, "588"), 24: (43, "588"), 25: (43, "588"),
    26: (44, "588"), 27: (44, "588"),
    # right: from the torso root (x46) up to the cuff opening (x55)
    46: (44, "588"), 47: (44, "588"), 48: (44, "588"),
    49: (43, "588"), 50: (43, "588"), 51: (43, "588"),
    52: (42, "588"), 53: (42, "e88"), 54: (42, "588"), 55: (43, "8c"),
}


# ---------------------------------------------------------------- tools ----

def read_sheet(path):
    im = Image.open(path)
    idx = np.array(Image.frombytes("L", im.size, im.tobytes()))
    return idx, im.getpalette()[: 16 * 3]


def read_pal(path):
    lines = path.read_text().splitlines()
    n = int(lines[2])
    return [tuple(int(v) for v in ln.split()) for ln in lines[3:3 + n]]


def label(mask):
    lab = np.zeros(mask.shape, int)
    n = 0
    for y, x in zip(*np.where(mask)):
        if lab[y, x]:
            continue
        n += 1
        lab[y, x] = n
        stack = [(y, x)]
        while stack:
            cy, cx = stack.pop()
            for ny in (cy - 1, cy, cy + 1):
                for nx in (cx - 1, cx, cx + 1):
                    if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] \
                            and mask[ny, nx] and not lab[ny, nx]:
                        lab[ny, nx] = n
                        stack.append((ny, nx))
    return lab, n


def body_mask(f1):
    lab, n = label(f1 > 0)
    sizes = [(lab == i).sum() for i in range(1, n + 1)]
    return lab == 1 + int(np.argmax(sizes))


def dilate(mask, r):
    out = mask.copy()
    for _ in range(r):
        m = out.copy()
        m[1:] |= out[:-1]
        m[:-1] |= out[1:]
        m[:, 1:] |= out[:, :-1]
        m[:, :-1] |= out[:, 1:]
        out = m
    return out


def paint(img, rows):
    for y, x0, pixels in rows:
        for i, ch in enumerate(pixels):
            if ch != ".":
                img[y, x0 + i] = int(ch, 16)


def take_spoons(f1, f2, spoons, body):
    """Clear the spoons from f2; return (mask, dx, dy) layers to paste."""
    layers = []
    for (x0, y0, x1, y1), (dx, dy) in spoons:
        box = np.zeros_like(body)
        box[y0:y1 + 1, x0:x1 + 1] = True
        sel = box & ~body & (f1 > 0)
        layers.append((sel, dx, dy))
        f2[sel] = 0
    return layers


def put_layers(f1, f2, layers):
    for sel, dx, dy in layers:
        ys, xs = np.where(sel)
        f2[ys + dy, xs + dx] = f1[ys, xs]


# ---------------------------------------------------------------- front ----

def spans_mask(shape, spans):
    m = np.zeros(shape, bool)
    for y, sp in spans.items():
        for x0, x1 in (sp if isinstance(sp, list) else [sp]):
            m[y, x0:x1 + 1] = True
    return m


def build_front(f1):
    body = body_mask(f1)
    f2 = f1.copy()
    spoons = take_spoons(f1, f2, FRONT_SPOONS, body)
    head = spans_mask(f1.shape, FRONT_HEAD) & body
    block = spans_mask(f1.shape, FRONT_BLOCK) & body & ~head
    f2[head | block] = 0
    put_layers(f1, f2, [(block, *FRONT_PAD_MOVE), (head, *FRONT_HEAD_MOVE)])
    tufts = []
    for (tx0, tx1, ty0, ty1), (fx0, fx1), move in FRONT_TUFTS:
        m = box_mask(f1.shape, tx0, tx1, ty0, ty1) & body
        fur = np.isin(f1, FRONT_FUR)
        edge = (f1 == 4) & ~box_mask(f1.shape, fx0, fx1, ty0, ty1)
        m &= fur | edge
        tufts.append((m, move))
        f2[m] = 0
    for m, (dx, dy) in tufts:
        for sx in (dx, 0):
            ys, xs = np.where(m)
            ok = f2[ys + dy, xs + sx] == 0
            f2[ys[ok] + dy, xs[ok] + sx] = f1[ys[ok], xs[ok]]
        # Root: where the tuft left a hole right next to the leg or arm it
        # grows from, the frame 1 fur stays (the tuft bends at its root).
        near = dilate((f2 > 0) & ~m & body, FRONT_TUFT_ROOT)
        keep = m & near & (f2 == 0)
        f2[keep] = f1[keep]
    put_layers(f1, f2, spoons)
    paint(f2, FRONT_FIXES)
    return f2


# ----------------------------------------------------------------- back ----

def box_mask(shape, x0, x1, y0, y1):
    m = np.zeros(shape, bool)
    m[y0:y1 + 1, x0:x1 + 1] = True
    return m


def build_back(f1):
    body = body_mask(f1)
    f2 = f1.copy()
    spoons = take_spoons(f1, f2, BACK_SPOONS, body)
    ys = np.arange(f1.shape[0])[:, None]
    arms = []
    for (x0, x1, y0, y1, (dx, dy)), spans in zip(BACK_ARMS, BACK_UPPER):
        upper = np.zeros_like(body)
        for y, (ux0, ux1) in spans.items():
            upper[y, ux0:ux1 + 1] = True
        upper &= f1 > 0
        arm = box_mask(f1.shape, x0, x1, y0, y1) & body & ~upper
        arm &= ~(np.isin(f1, FUR) & (ys >= 52))
        arms.append((arm, dx, dy))
        f2[arm | upper] = 0
    crest = np.zeros_like(body)
    for y, (x0, x1) in BACK_CREST_ROWS.items():
        crest[y, x0:x1 + 1] = body[y, x0:x1 + 1]
    f2[crest] = 0
    dx, dy = BACK_CREST_MOVE
    put_layers(f1, f2, [(crest, dx, dy)])
    put_layers(f1, f2, arms)
    put_layers(f1, f2, spoons)
    for x, (top, fill) in BACK_BANDS.items():
        paint(f2, [(top + i, x, ch) for i, ch in enumerate("4" + fill + "4")])
    paint(f2, BACK_FIXES)
    return f2


# ------------------------------------------------------------- checks ----

def check(real, f1, f2):
    assert np.array_equal(f1, real[:, :W]), "frame 1 differs from res/"
    extra = set(np.unique(f2)) - set(np.unique(f1))
    assert not extra, f"frame 2 uses indices frame 1 does not: {extra}"
    border = np.ones(f2.shape, bool)
    border[1:-1, 1:-1] = False
    assert not f2[border].any(), "frame 2 touches the 1 px border"
    # Art must keep 2 px from the edge; the only exception allowed is a pixel
    # frame 1 already has in exactly that place (the front centre spoon tip).
    margin = np.ones(f2.shape, bool)
    margin[2:-2, 2:-2] = False
    bad = margin & (f2 > 0) & (f2 != f1)
    assert not bad.any(), f"frame 2 art within 2 px of the edge at {np.argwhere(bad)[:5]}"


# ------------------------------------------------------------- previews ----

BG = (200, 208, 216)


def to_rgb(frame, pal, scale):
    rgb = np.zeros(frame.shape + (3,), np.uint8)
    rgb[:] = BG
    for i, c in enumerate(pal):
        if i:
            rgb[frame == i] = c
    im = Image.fromarray(rgb)
    return im.resize((im.width * scale, im.height * scale), Image.NEAREST)


def write_gif(path, f1, f2, pal, scale):
    frames = []
    flat = list(BG) + [v for c in pal[1:16] for v in c]
    flat += [0] * (768 - len(flat))
    for fr in (f1, f2, f1):
        im = Image.fromarray(fr.astype(np.uint8), "P")
        im.putpalette(flat)
        frames.append(im.resize((W * scale, W * scale), Image.NEAREST))
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=[300, 430, 1000], loop=0, optimize=False,
                   disposal=1)
    chk = Image.open(path)
    assert chk.n_frames == 3 and chk.info.get("loop") == 0, path


def write_previews(sheets):
    normal = read_pal(MEGA / "normal.pal")
    shiny = read_pal(MEGA / "shiny.pal")
    rows = []
    for side in ("front", "back"):
        sheet = sheets[side]
        f1, f2 = sheet[:, :W], sheet[:, W:]
        write_gif(PREVIEWS / f"alakazam_{side}.gif", f1, f2, normal, 4)
        write_gif(PREVIEWS / f"alakazam_{side}_shiny.gif", f1, f2, shiny, 4)
        write_gif(PREVIEWS / f"alakazam_{side}_1x.gif", f1, f2, normal, 1)
        for pal in (normal, shiny):
            rows.append((to_rgb(f1, pal, 5), to_rgb(f2, pal, 5)))
    cell = W * 5
    gap = 4
    out = Image.new("RGB", (2 * cell + gap, 4 * cell + 3 * gap), (255, 255, 255))
    for j, (a, b) in enumerate(rows):
        out.paste(a, (0, j * (cell + gap)))
        out.paste(b, (cell + gap, j * (cell + gap)))
    out.save(PREVIEWS / "alakazam_frames.png")


# ----------------------------------------------------------------- main ----

def build_sheet(path, builder):
    real, palette = read_sheet(path)
    f1 = real[:, :W].copy()
    f2 = builder(f1)
    check(real, f1, f2)
    return np.hstack([f1, f2]).astype(np.uint8), palette, real


def save_sheet(path, sheet, palette, real):
    im = Image.fromarray(sheet, "P")
    im.putpalette(palette)
    im.save(path, bits=4, transparency=0)
    back, _ = read_sheet(path)
    assert np.array_equal(back, sheet), f"{path} did not round-trip"
    assert np.array_equal(back[:, :W], real[:, :W]), "frame 1 changed on save"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--install", action="store_true",
                    help="write the real sprites under res/ instead of previews")
    ap.add_argument("--previews", action="store_true",
                    help="also write the preview GIFs and alakazam_frames.png")
    args = ap.parse_args()

    PREVIEWS.mkdir(parents=True, exist_ok=True)
    sheets = {}
    for side, builder in (("front", build_front), ("back", build_back)):
        sheet, palette, real = build_sheet(MEGA / f"{side}.png", builder)
        sheets[side] = sheet
        out = MEGA / f"{side}.png" if args.install \
            else PREVIEWS / f"alakazam_{side}.png"
        save_sheet(out, sheet, palette, real)
        print("wrote", out.relative_to(ROOT))
    if args.previews:
        write_previews(sheets)
        print("wrote previews in", PREVIEWS.relative_to(ROOT))


if __name__ == "__main__":
    main()
