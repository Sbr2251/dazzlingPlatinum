"""Indra, a leader of Team Eclipse (docs/story/bible.md: her brother Teo is gone; Saros's rewind or Kahn's
parallel world would bring him back, so she guards the plan and keeps everyone else in line).

Design: a tired, hard woman in a dark violet/black coat.
  - Built on the stock Cynthia walker (member 0x75) for its long-coat cut and walk, with the head,
    collar and shoulders redrawn and every colour remapped, so nothing of Cynthia's look survives:
    Cynthia's long blonde hair is gone (it is painted out of the back of the coat).
  - Short, severe dark-auburn hair cut at the jaw, a heavy fringe swept across from her right.
  - A pale face with heavy lids and shadows under the eyes and a flat, hard mouth.
  - A long violet-black coat buttoned to a high collar with a dark violet lining, the Eclipse mark
    (violet ring, black disc) as a clasp at the throat and as a large ring on the back of the coat,
    violet buttons down the front. Black boots.
She shares the leaders' Eclipse mark with Saros (brooch and back ring) but not his silhouette: Saros
has tall collar points and silver hair; Indra is shorter, with a round auburn bob and square shoulders.
"""

from __future__ import annotations

from common import DOWN, LEFT, UP, Character, Part

PALETTE = [
    (255, 0, 255),    # 0  transparent
    (14, 10, 22),     # 1  K outline
    (34, 26, 50),     # 2  c coat darkest
    (64, 48, 98),     # 3  C coat dark violet
    (108, 88, 152),   # 4  L coat light
    (100, 42, 170),   # 5  v violet dark
    (170, 104, 250),  # 6  V violet
    (232, 210, 255),  # 7  g violet glow
    (124, 70, 70),    # 8  s skin outline / shadow
    (206, 148, 124),  # 9  n skin mid
    (244, 208, 186),  # 10 a skin light
    (46, 20, 28),     # 11 H hair dark
    (88, 38, 40),     # 12 h hair mid
    (138, 64, 56),    # 13 x hair light
    (236, 232, 244),  # 14 w eye white
    (66, 30, 110),    # 15 u lining violet
]
LEGEND = {"K": 1, "c": 2, "C": 3, "L": 4, "v": 5, "V": 6, "g": 7, "s": 8, "n": 9, "a": 10, "H": 11, "h": 12,
          "x": 13, "w": 14, "u": 15}

CYNTHIA = 0x75

# Stock Cynthia palette: 1 brown (hair edge), 2 cream, 3 blonde, 4 black outline, 5 dark blonde, 6 skin
# light, 7 coat black, 8 coat grey, 9 lavender, A blue (eyes), B skin outline, C lilac grey (coat
# light), D white (buttons), E skin mid. Hair left below the cut becomes coat.
INDEX_MAP = {1: 3, 2: 10, 3: 3, 4: 1, 5: 3, 6: 10, 7: 2, 8: 3, 9: 4, 10: 5, 11: 8, 12: 4, 13: 6, 14: 9}

HEAD_DOWN = Part(
    """
    |......KKKKKKK......|
    |....KKhhhhhhhKK....|
    |...KhhxxhhhhhhhK...|
    |..KhxxhhhhhhhhhhK..|
    |..KhhhhhhhhhhhHhK..|
    |..KHhhhhhhhhHHahK..|
    |..KHhhhhhHHHaaaHK..|
    |..KHhhHHHaaaaaaHK..|
    |..KHhHKKKaaKKKaHK..|
    |..KHHaawKaaKwaaHK..|
    |..KHHnasaaaasanHK..|
    |..KHHnaaaaaaaanHK..|
    |.KKKHHnaaaaanHHKKK.|
    |.KLcKHKsnnnsKHKcLK.|
    |.KLCcKKKKsKKKKcCLK.|
    |.KLCvuKKVgVKKuvCLK.|
    """,
    6, 6,
)

HEAD_UP = Part(
    """
    |......KKKKKKK......|
    |....KKhhhhhhhKK....|
    |...KhhxxxhhhhhhK...|
    |..KhxxhhhhhhhhhhK..|
    |..KhhhhhhhhhhhhhK..|
    |..KhhhhhhhhhhhhhK..|
    |..KHhhhhhhhhhhhHK..|
    |..KHhhhhhhhhhhhHK..|
    |..KHHhhhhhhhhhHHK..|
    |..KHHHhhhhhhhHHHK..|
    |..KHHHHhhhhhHHHHK..|
    |..KKHHHHHHHHHHHKK..|
    |.KKcKHHHHHHHHHKcKK.|
    |.KcLcKKKKKKKKKcLcK.|
    |.KcLCCuuuuuuuCCLcK.|
    |.KcLCCCCCCCCCCCLcK.|
    """,
    6, 6,
)

HEAD_LEFT = Part(
    """
    |.....KKKKK.....|
    |...KKhhhhhKK...|
    |..KhhxxhhhhhK..|
    |.KhxxhhhhhhhhK.|
    |.KhhhhhhhhhhhhK|
    |KHHhhhhhhhhhhhK|
    |KaHHHhhhhhhhhHK|
    |KaaaHHhhhhhhhHK|
    |KKKKaHhhhhhhHHK|
    |KawKaHHhhhhhHHK|
    |KasaanHhhhhhHHK|
    |.KaaanHHHhhHHK.|
    |.KsaasKHHHHHKK.|
    |..KKsKKcKKKKcK.|
    |...KKKucLLCCcK.|
    |....KKucLCCCcK.|
    """,
    7, 6,
)

OVERLAYS = {
    DOWN: [
        Part("|VgV|", 14, 22),  # top button of the coat front, below the clasp
    ],
    UP: [
        Part(
            """
            |.VVV.|
            |VKKKV|
            |VKKKV|
            |.vvv.|
            """,
            13, 22,
        ),
    ],
}

INDRA = Character(
    name="indra",
    base_member=CYNTHIA,
    palette=PALETTE,
    legend=LEGEND,
    index_map=INDEX_MAP,
    cut={UP: 22, DOWN: 22, LEFT: 22},
    heads={DOWN: HEAD_DOWN, UP: HEAD_UP, LEFT: HEAD_LEFT},
    overlays=OVERLAYS,
    # the long blonde hair down the back of Cynthia's coat (and the light trim) becomes plain coat
    band_maps={UP: [(22, 30, {5: 2, 1: 2, 3: 2, 12: 3})], LEFT: [(22, 30, {5: 3, 1: 3, 3: 3})]},
)

CHARACTERS = [INDRA]
