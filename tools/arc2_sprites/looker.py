"""Looker's two Arc 2 disguises, both edits of the stock Platinum Looker walker (member 0x178).

OBJ_EVENT_GFX_LOOKER_JANITOR (scene 2.12, the Haven lobby: "A janitor mopping the lobby edges over")
    Looker's own face, sideburns and dark spiky hair, but the brown trench coat is recoloured into
    slate-blue coveralls (the tie becomes the coverall zip), a matching flat cap with a white badge
    covers the top of his hair, and he carries a mop (wooden handle, grey-white strands). The mop is
    drawn behind the body and fixed to the cell, so it stays planted while he walks.

OBJ_EVENT_GFX_LOOKER_NEWSPAPER (scene 2.17, Veilstone: "a man in a hat and sunglasses reads a
newspaper upside down")
    The stock Looker with a brown fedora, black sunglasses, and an open newspaper held up in front
    of his chest in both hands. The paper's headline bar is at the BOTTOM edge: it is upside down.
    From behind, the paper's corners show past his shoulders; side-on, it is held out in front.
"""

from __future__ import annotations

from common import DOWN, LEFT, NO_HEAD, UP, Character, Part, get_px, set_px

LOOKER = 0x178

# Stock Looker palette (index: colour): 1 near-black, 2/3 hair greys, 4-7 coat browns (dark to light),
# 8/9 tie (magenta/dark violet), A/B/C skin (outline/mid/light), D black outline, E lavender shirt,
# F white.
STOCK = [
    (214, 189, 247), (41, 41, 33), (66, 66, 66), (90, 90, 82), (66, 49, 24), (99, 82, 49),
    (132, 107, 66), (148, 123, 90), (132, 66, 115), (90, 41, 74), (123, 66, 66), (222, 156, 115),
    (255, 214, 189), (0, 0, 0), (173, 165, 206), (239, 239, 255),
]

LEGEND = {str(i): i for i in range(10)} | {"A": 10, "B": 11, "C": 12, "D": 13, "E": 14, "F": 15}

# ---------------------------------------------------------------------------
# Janitor
# ---------------------------------------------------------------------------

JANITOR_PALETTE = list(STOCK)
JANITOR_PALETTE[4] = (34, 48, 70)     # coverall dark
JANITOR_PALETTE[5] = (58, 82, 112)    # coverall mid
JANITOR_PALETTE[6] = (86, 116, 150)   # coverall light
JANITOR_PALETTE[7] = (132, 160, 190)  # coverall sheen
JANITOR_PALETTE[8] = (184, 140, 84)   # mop handle (wood)
JANITOR_PALETTE[9] = (120, 86, 50)    # mop handle shade

# The tie becomes the coverall zip; 8/9 are then free for the mop handle.
JANITOR_MAP = {8: 6, 9: 4}

JANITOR_CAP_DOWN = Part(
    """
    |........DDDDD......|
    |......DD66666DD....|
    |.....D666F666666D..|
    |....D66666666666D..|
    |...D6666666666666D.|
    |...D5555555555555D.|
    |.__D4444444444444D_|
    |..DD7777777777777DD|
    |...DDDDDDDDDDDDDDD.|
    """,
    5, 3,
)

JANITOR_CAP_UP = Part(
    """
    |........DDDDD......|
    |......DD66666DD....|
    |.....D66666666D....|
    |....D666666666666D.|
    |...D6666666666666D.|
    |...D6666666666666D.|
    |...D5555555555555D.|
    |..._D5555D4D5555D__|
    """,
    5, 3,
)

JANITOR_CAP_LEFT = Part(
    """
    |.........DDDDD.....|
    |.......DD66666DD...|
    |......D6666666F6D..|
    |.....D66666666666D.|
    |.....D66666666666D.|
    |.....D55555555555D.|
    |.DDDD444445555555D.|
    |D77777DDDDD4444DD..|
    |.DDDDD.....DDDD....|
    """,
    3, 3,
)


def _mop(frame: list[int], direction: int, column: int) -> list[int]:
    """A mop on the cell, behind the body (only transparent pixels are painted)."""
    out = list(frame)
    if direction == DOWN:
        hx, top, head_cx = 5, 11, 5
    elif direction == UP:
        hx, top, head_cx = 25, 11, 25
    else:  # LEFT (RIGHT is the mirror)
        hx, top, head_cx = 8, 12, 7

    def put(x, y, v):
        if get_px(out, x, y) == 0:
            set_px(out, x, y, v)

    for y in range(top, 26):
        put(hx, y, 8)
        put(hx + 1, y, 9 if y % 5 else 13)  # shade, with a grip band every 5 px
    put(hx, top - 1, 13)
    put(hx + 1, top - 1, 13)
    # mop head: a band then a fan of strands on the floor
    for x in range(head_cx - 2, head_cx + 4):
        put(x, 26, 13)
    for x in range(head_cx - 3, head_cx + 5):
        put(x, 27, 14 if (x + column) % 2 else 15)
        put(x, 28, 3 if (x + column) % 3 == 0 else 14)
    for x in range(head_cx - 3, head_cx + 5):
        put(x, 29, 13)
    put(head_cx - 4, 28, 13)
    put(head_cx + 5, 28, 13)
    return out


LOOKER_JANITOR = Character(
    name="looker_janitor",
    base_member=LOOKER,
    palette=JANITOR_PALETTE,
    legend=LEGEND,
    index_map=JANITOR_MAP,
    cut={UP: 0, DOWN: 0, LEFT: 0},
    heads={UP: JANITOR_CAP_UP, DOWN: JANITOR_CAP_DOWN, LEFT: JANITOR_CAP_LEFT},
    post=_mop,
)

# ---------------------------------------------------------------------------
# Newspaper and sunglasses
# ---------------------------------------------------------------------------

NEWS_PALETTE = list(STOCK)
NEWS_PALETTE[8] = (196, 192, 176)  # newsprint shade (the tie keeps 9, now a dark wine)
NEWS_PALETTE[9] = (96, 40, 56)

NEWS_MAP = {8: 9}

FEDORA_DOWN = Part(
    """
    |.......DDDDDDD.....|
    |......D6666666D....|
    |.....D666676666D...|
    |.....D666666666D...|
    |....D11111111111D..|
    |.DDD5555555555555DD|
    |D77777777777777777D|
    |.DDDDDDDDDDDDDDDDD.|
    """,
    5, 3,
)

FEDORA_UP = Part(
    """
    |.......DDDDDDD.....|
    |......D6666666D....|
    |.....D666666666D...|
    |.....D666666666D...|
    |....D11111111111D..|
    |.DDD5555555555555DD|
    |D55555555555555555D|
    |.DDDDDDDDDDDDDDDDD.|
    """,
    5, 3,
)

FEDORA_LEFT = Part(
    """
    |........DDDDDDD....|
    |.......D6666666D...|
    |......D666676666D..|
    |......D666666666D..|
    |.....D11111111111D.|
    |.DDDD5555555555555D|
    |D7777777777777775D.|
    |.DDDDDDDDDDDDDDDD..|
    """,
    3, 3,
)

SUNGLASSES_DOWN = Part(
    """
    |DDDDDDDDDD|
    |DFDD..DFDD|
    |.DD....DD.|
    """,
    11, 15,
)

SUNGLASSES_LEFT = Part(
    """
    |DDDDDD|
    |DFD...|
    """,
    10, 15,
)

PAPER_DOWN = """
    |CFFFFFFFFFFFFC|
    |DFE2EE2E2EE2FD|
    |DFFFFFFFFFFFFD|
    |DF2E2EEE2E2EFD|
    |DFFFFFFFFFFFFD|
    |DFE2E2EE2E2EFD|
    |DF2222222222FD|
    |DDDDDDDDDDDDDD|
"""

PAPER_LEFT = """
    |.DDDD.|
    |DFFFFD|
    |DE2E2D|
    |DFFFFD|
    |D2EEED|
    |DFFFFD|
    |DE2E2D|
    |D2222D|
    |DDDDDD|
"""


def _paper(frame: list[int], direction: int, column: int) -> list[int]:
    from common import paint, parse_grid, top_row

    out = list(frame)
    bob = top_row(frame) - 3  # the fedora's top row is 3 in the stand frames
    if direction == DOWN:
        # Hold still: clear the swinging forearms outside the paper, then paint paper and hands.
        for y in range(18 + bob, 27 + bob):
            for x in list(range(0, 9)) + list(range(23, 32)):
                set_px(out, x, y, 0)
        grid = parse_grid(PAPER_DOWN)
        # 'C' (skin light) in the grid's top corners is a thumb; '.' keeps the shirt/tie showing
        out = paint(out, grid, LEGEND, 9, 19 + bob)
        for x, y in ((8, 20), (8, 21), (23, 20), (23, 21)):
            set_px(out, x, y + bob, 11)
        for x, y in ((8, 19), (8, 22), (23, 19), (23, 22)):
            set_px(out, x, y + bob, 10)
    elif direction == UP:
        # corners of the paper past both shoulders
        for side, rows in ((6, ("DD", "DF", "DE", "DF", "DD")), (24, ("DD", "FD", "ED", "FD", "DD"))):
            for dy, row in enumerate(rows):
                for dx, ch in enumerate(row):
                    set_px(out, side + dx, 18 + bob + dy, LEGEND[ch])
    else:  # LEFT: paper held out in front, seen almost edge-on
        for y in range(18 + bob, 26 + bob):
            for x in range(0, 12):
                if get_px(out, x, y) in (9, 10, 11, 12):
                    set_px(out, x, y, 0)
        out = paint(out, parse_grid(PAPER_LEFT), LEGEND, 5, 17 + bob)
        set_px(out, 11, 20 + bob, 11)
        set_px(out, 11, 21 + bob, 10)
    return out


LOOKER_NEWSPAPER = Character(
    name="looker_newspaper",
    base_member=LOOKER,
    palette=NEWS_PALETTE,
    legend=LEGEND,
    index_map=NEWS_MAP,
    cut={UP: 0, DOWN: 0, LEFT: 0},
    heads={UP: FEDORA_UP, DOWN: FEDORA_DOWN, LEFT: FEDORA_LEFT},
    overlays={DOWN: [SUNGLASSES_DOWN], LEFT: [SUNGLASSES_LEFT]},
    post=_paper,
)

CHARACTERS = [LOOKER_JANITOR, LOOKER_NEWSPAPER]
__all__ = ["LOOKER_JANITOR", "LOOKER_NEWSPAPER", "NO_HEAD"]
