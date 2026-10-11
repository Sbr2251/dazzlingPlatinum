"""Kahn, a leader of Team Eclipse (docs/story/bible.md: his Lucario fell from a sea cliff protecting him;
he wants Palkia to open a door to a world where it lived).

Design: a quiet sailor turned leader, in sea colours plus Eclipse violet.
  - Built on the stock Platinum Sailor walker (member 0x36): the sailor's walk, cap and build stay,
    so he still reads as a man of the sea.
  - The white sailor cap becomes a dark navy officer's cap with an Eclipse-violet band and a small
    Eclipse badge (violet ring, black disc) on the front.
  - The sailor top becomes a sea-teal jersey under a navy pea coat whose sleeves cover the sailor's
    bare arms; the red neckerchief becomes Eclipse violet.
  - Dark trousers and boots; weathered tan skin, dark hair, and a short dark beard: older and
    heavier than the stock sailor, and he never smiles.
"""

from __future__ import annotations

from common import CELL, DOWN, LEFT, UP, Character, NO_HEAD, Part, get_px, set_px

PALETTE = [
    (255, 0, 255),    # 0  transparent
    (16, 18, 28),     # 1  K outline
    (46, 40, 40),     # 2  H hair / beard
    (26, 34, 60),     # 3  n navy dark
    (42, 58, 98),     # 4  N navy
    (74, 98, 146),    # 5  L navy light
    (44, 124, 138),   # 6  t sea teal
    (120, 192, 198),  # 7  T sea teal light
    (96, 40, 160),    # 8  v violet dark
    (166, 98, 246),   # 9  V violet
    (110, 62, 54),    # 10 s skin outline
    (196, 136, 100),  # 11 k skin mid
    (236, 190, 152),  # 12 a skin light
    (40, 44, 58),     # 13 p trousers
    (76, 82, 102),    # 14 P trousers light
    (232, 228, 250),  # 15 w glint
]
LEGEND = {"K": 1, "H": 2, "n": 3, "N": 4, "L": 5, "t": 6, "T": 7, "v": 8, "V": 9, "s": 10, "k": 11, "a": 12,
          "p": 13, "P": 14, "w": 15}

SAILOR = 0x36

# Stock sailor palette: 1 lavender (cap edge, hair, folds), 2 white (cap, trousers), 3 outline, 4 light
# grey (cap shade, shirt, trousers), 5 dark navy, 6 navy (band, collar, shoes), 7 dark slate, 8/9/A skin
# (mid/outline/light), B light blue (collar stripes), C red (neckerchief).
INDEX_MAP = {1: 3, 2: 13, 3: 1, 4: 14, 5: 3, 6: 4, 7: 3, 8: 11, 9: 10, 10: 12, 11: 7, 12: 9}

CAP = {1: 1, 2: 4, 4: 3, 6: 9, 5: 8, 7: 3, 3: 1}           # rows 5-11: the officer's cap
BRIM = {4: 3, 1: 1, 6: 8, 5: 8, 7: 1}                      # row 12
TORSO = {4: 6, 6: 4, 11: 7, 2: 7, 5: 3, 7: 3}              # rows 18-24: jersey, collar

BAND_MAPS = {
    DOWN: [(5, 12, CAP), (12, 13, BRIM), (13, 14, {1: 2}), (14, 18, {2: 15}), (19, 25, TORSO)],
    UP: [(5, 12, CAP), (12, 13, BRIM), (13, 18, {1: 2, 7: 2, 5: 2}), (18, 19, {5: 4, 7: 4}),
         (19, 25, TORSO | {5: 4, 7: 4, 2: 4, 11: 4})],
    LEFT: [(5, 12, CAP), (12, 13, BRIM), (13, 19, {1: 2, 7: 2, 5: 2, 2: 15}), (19, 25, TORSO)],
}

BADGE = Part(
    """
    |.V.|
    |VKV|
    |.V.|
    """,
    14, 7,
)

BEARD_DOWN = Part(
    """
    |H.........H|
    |.HH.HsH.HH.|
    |...HHHHH...|
    """,
    10, 17,
)

BEARD_LEFT = Part(
    """
    |H.....HH|
    |.HHHHHH.|
    """,
    9, 17,
)

OVERLAYS = {
    DOWN: [BADGE, BEARD_DOWN],
    LEFT: [Part("|VK|", 9, 8), BEARD_LEFT],
}


def _sleeves(frame: list[int], direction: int, column: int) -> list[int]:
    """Navy pea-coat sleeves over the sailor's bare arms (hands stay bare)."""
    out = list(frame)
    top = next(y for y in range(CELL) if any(out[y * CELL:(y + 1) * CELL]))
    bob = top - 5
    if direction in (DOWN, UP):
        for y in range(17 + bob, 23 + bob):
            for x in range(CELL):
                if 10 <= x <= 20:
                    continue
                v = get_px(out, x, y)
                if v in (11, 12):
                    set_px(out, x, y, 4 if v == 11 else 5)
                elif v == 10:
                    set_px(out, x, y, 3)
    else:
        for y in range(19 + bob, 25 + bob):
            for x in range(CELL):
                v = get_px(out, x, y)
                if v in (11, 12, 7):
                    # keep the very lowest skin pixels (the hand)
                    if v != 7 and get_px(out, x, y + 1) in (0, 1) and get_px(out, x, y + 2) in (0, 1):
                        continue
                    set_px(out, x, y, 4 if v in (11, 7) else 5)
                elif v == 10:
                    set_px(out, x, y, 3)
    return out


KAHN = Character(
    name="kahn",
    base_member=SAILOR,
    palette=PALETTE,
    legend=LEGEND,
    index_map=INDEX_MAP,
    cut={UP: 0, DOWN: 0, LEFT: 0},
    heads={UP: NO_HEAD, DOWN: NO_HEAD, LEFT: NO_HEAD},
    overlays=OVERLAYS,
    band_maps=BAND_MAPS,
    post=_sleeves,
)

CHARACTERS = [KAHN]
