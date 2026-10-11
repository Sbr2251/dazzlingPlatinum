"""Saros, a leader of Team Eclipse (docs/story/bible.md: "Team Eclipse leaders").

A grieving father who wants Dialga to rewind time to before his daughter Mira died.
Design (docs/story/art/README.md):
  - Long dark coat, blue-black like a night sky, with a tall stiff collar that rises to
    the jaw on both sides: the collar points are his silhouette (no other Arc 1 NPC has
    them; Cyrus has spikes, Looker a trench coat and hat, Rowan white hair).
  - A violet waistcoat under the coat and the Eclipse mark (black disc, violet ring) as
    a brooch at the throat and as a large ring on the back of the coat.
  - Swept-back slate hair gone silver at the temples, a gaunt pale face, heavy brows
    over tired eyes: grief has aged him.
Body (walk cycle and long-coat cut) is the stock Prof. Rowan walker (member 0x5E),
recoloured, with the head and collar redrawn.
"""

from __future__ import annotations

from walker import DOWN, LEFT, UP, Character, Part

PALETTE = [
    (255, 0, 255),    # 0  transparent
    (16, 14, 26),     # 1  K outline
    (34, 34, 54),     # 2  c coat dark
    (56, 58, 88),     # 3  C coat mid
    (92, 96, 136),    # 4  L coat light (sheen)
    (86, 36, 152),    # 5  v violet dark
    (164, 96, 244),   # 6  V violet
    (232, 208, 255),  # 7  g violet glow
    (128, 80, 80),    # 8  s skin outline
    (212, 160, 132),  # 9  n skin mid
    (246, 220, 202),  # 10 a skin light (pale)
    (50, 54, 70),     # 11 H hair dark
    (86, 92, 112),    # 12 h hair mid
    (160, 166, 186),  # 13 x silver
    (228, 232, 244),  # 14 w silver light
    (64, 32, 104),    # 15 u violet lining
]

LEGEND = {
    "K": 1, "c": 2, "C": 3, "L": 4, "v": 5, "V": 6, "g": 7, "s": 8, "n": 9, "a": 10,
    "H": 11, "h": 12, "x": 13, "w": 14, "u": 15,
}

# Stock Rowan palette: 1 lavender shade, 2 light grey, 3 white (coat), 4 outline,
# 5 dark teal (trousers), 6/7/8 skin, 9 dark teal (coat edge), A blue, B light blue (waistcoat).
INDEX_MAP = {1: 2, 2: 3, 3: 4, 4: 1, 5: 1, 6: 9, 7: 10, 8: 8, 9: 2, 10: 5, 11: 15}

HEAD_DOWN = Part(
    """
    |.......KKKKK.......|
    |....KKKhhhhhKKK....|
    |...KhhHhwwhhHhhK...|
    |..KxhhHhwhhHhhhxK..|
    |..KxxhHhhhhHhhxxK..|
    |..KxxHhhhhhhhHxxK..|
    |..KxxHaaHhHaaHxxK..|
    |..KxHaaaaaaaaaHxK..|
    |..KxaKKaaaaaKKaxK..|
    |.KKnaaKaaaaaKaanKK.|
    |KCKnaaKaaaaaKaanKcK|
    |KLuKnaaaaaaaaanKucK|
    |KLuKsnaannnaansKucK|
    |KLCuKsnaaaaansKuCcK|
    |KLCCuKKsssssKKuCCcK|
    """,
    6, 5,
)

HEAD_UP = Part(
    """
    |.......KKKKK.......|
    |....KKKhhhhhKKK....|
    |...KhhHhwwhhHhhK...|
    |..KxhhHhwhhHhhhxK..|
    |..KxhhHhhhhHhhhxK..|
    |..KxxhHhhhhHhhxxK..|
    |..KxxHhhhhhhhHxxK..|
    |..KxxHHhhhhhHHxxK..|
    |..KxxHHHhhhHHHxxK..|
    |.KKKxHHHHHHHHHxKKK.|
    |KLCKKxHHHHHHHxKKCcK|
    |KLCCKKHKHHHKHKKCCcK|
    |KLCCCCKKCKCKKCCCCcK|
    |KLCCCCCLLLLLCCCCCcK|
    |KKLCCCCCCCCCCCCCcKK|
    """,
    6, 5,
)

HEAD_LEFT = Part(
    """
    |.....KKKKKK......|
    |...KKhhhhhhKK....|
    |..KhhwwhhhhhhKK..|
    |.KhhwhhhhhhhhhhK.|
    |.KhhhhhhhhhhhhhhK|
    |KHhhhhhhhhhhhhKK.|
    |KaHHhhhhhxxhhhhK.|
    |KaaHHhhhxxxhhhK..|
    |KaKKaHhhxxwxhhK..|
    |KaaKaaHxxxxhhKK..|
    |KaaKaanKxxHHKLK..|
    |.KaaaanKKHHKLCK..|
    |.KsaannKuKKLCCK..|
    |.KKsnnKuuKLCCcK..|
    |KLKKKKKuKLCCccK..|
    """,
    8, 5,
)

OVERLAYS = {
    DOWN: [
        Part("|KLCCCuKKVgVKKuCCCcK|", 6, 20),
    ],
    UP: [
        Part("|KLCCCCCCCCCCCCCCCcK|", 6, 20),
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
    LEFT: [
        Part("|KLCKuuKLCCcK|", 8, 20),
    ],
}

SAROS = Character(
    name="saros",
    base_member=0x5E,
    palette=PALETTE,
    legend=LEGEND,
    index_map=INDEX_MAP,
    cut={UP: 20, DOWN: 20, LEFT: 20},
    heads={DOWN: HEAD_DOWN, UP: HEAD_UP, LEFT: HEAD_LEFT},
    overlays=OVERLAYS,
    band_maps={UP: [(20, 28, {10: 2, 11: 3, 6: 2, 7: 3, 8: 2})]},
)

CHARACTERS = [SAROS]
