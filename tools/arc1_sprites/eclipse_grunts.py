"""Team Eclipse grunts (male and female): "the Eclipse look, dark, with a violet eclipse ring".

Design (docs/story/art/README.md):
  - A dark hooded uniform. The hood replaces Galactic's teal bowl cut, so the silhouette
    is a cowl that comes to a soft point at the back instead of a round helmet of hair.
  - The team mark is an eclipse: a black disc inside a glowing violet ring. It sits on
    the front of the hood, on the back of the hood and on the chest.
  - Violet trim: belt and cuffs. Charcoal trousers, dark boots.
  - Male: hood up, short dark fringe under the brim.
  - Female: the same hood with long lilac-silver hair falling out of it at the front and
    a ponytail out of the back, so the pair read as one uniformed team but are easy to
    tell apart.
Bodies (walk cycles) are the stock Galactic grunt walkers (members 0x67 / 0x68) with
every colour remapped and the head redrawn.
"""

from __future__ import annotations

from walker import DOWN, LEFT, UP, Character, Part

# One palette for both grunts (index 0 transparent).
PALETTE = [
    (255, 0, 255),    # 0  transparent
    (20, 16, 30),     # 1  K outline
    (50, 42, 74),     # 2  d uniform dark
    (86, 74, 122),    # 3  m uniform mid
    (132, 120, 172),  # 4  l uniform light
    (104, 40, 176),   # 5  v violet dark
    (168, 96, 248),   # 6  V violet
    (232, 208, 255),  # 7  g violet glow
    (123, 66, 66),    # 8  s skin outline
    (222, 156, 115),  # 9  n skin mid
    (255, 214, 189),  # 10 a skin light
    (56, 56, 72),     # 11 p trousers
    (112, 112, 132),  # 12 q grey
    (240, 240, 255),  # 13 w white
    (200, 184, 232),  # 14 h hair light (female)
    (128, 112, 168),  # 15 H hair dark (female)
]

LEGEND = {
    "K": 1, "d": 2, "m": 3, "l": 4, "v": 5, "V": 6, "g": 7,
    "s": 8, "n": 9, "a": 10, "p": 11, "q": 12, "w": 13, "h": 14, "H": 15,
}

# ---------------------------------------------------------------------------
# Male
# ---------------------------------------------------------------------------

# Stock grunt M palette: 1-3 hair, 4 outline, 5/6/9 skin, 7 dark, 8 white, A dark grey,
# B grey, C lavender, D gold "G", E unused.
MALE_MAP = {1: 2, 2: 4, 3: 3, 4: 1, 5: 8, 6: 9, 7: 2, 8: 4, 9: 10, 10: 2, 11: 3, 12: 3, 13: 6, 14: 3}

MALE_HEAD_DOWN = Part(
    """
    |......KKKKK......|
    |....KKdmmmdKK....|
    |...KdmmlllmmdK...|
    |..KdmmlVgVlmmdK..|
    |..KdmlVKKKVlmdK..|
    |.KddmlVKKKVlmddK.|
    |.KdmmmlvVvlmmmdK.|
    |.KdmKKKKKKKKKmdK.|
    |KddKdKdddddKdKddK|
    |KdmKnaaaaaaanKmdK|
    |KdmKaKaaaaaKaKmdK|
    |KddKaKaaaaaKaKddK|
    |.KdmKnaanaanKmdK.|
    |.KddmKsnnnsKmddK.|
    |..KKddKKKKKddKK..|
    """,
    7, 5,
)

MALE_HEAD_UP = Part(
    """
    |......KKKKK......|
    |....KKdmmmdKK....|
    |...KdmmlllmmdK...|
    |..KdmmllllmmmdK..|
    |..KdmmlllmmmmdK..|
    |.KddmmmlmmmmmddK.|
    |.KdmmmmmmmmmmmdK.|
    |.KddmmmVVVmmmddK.|
    |KdddmmVKKKVmmdddK|
    |KddddmVKKKVmddddK|
    |KdddddmvvvmdddddK|
    |KddddddmmmddddddK|
    |.KddddddmddddddK.|
    |.KKdddddddddddKK.|
    |...KKKKKKKKKKK...|
    """,
    7, 5,
)

MALE_HEAD_LEFT = Part(
    """
    |.......KKKK......|
    |.....KKdmmmKK....|
    |....KdmllllmdK...|
    |...KdmlllllmmdK..|
    |..KdmllllmmmmdK..|
    |..KdmlllmmVVmmdK.|
    |..KdmllmmVKKVmdK.|
    |.KdmmlmmmVKKVmddK|
    |.KdmmmmmmmvvmmddK|
    |.KKKKKdmmmmmmmddK|
    |.KdKdKKdmmmmmmddK|
    |.KaaaaKdmmmmmmddK|
    |.KaKaasKdmmmmmdK.|
    |.KaKaanKdmmmmddK.|
    |..KaaasKdmmmddK..|
    |...KssKKddddKK...|
    """,
    8, 5,
)

# Front: dark collar instead of Galactic's open neck, the eclipse on the chest, violet belt.
MALE_OVERLAYS = {
    DOWN: [
        Part("|KdmmmmmmmdK|", 10, 20),
        Part("|mmm|", 14, 21),
        Part(
            """
            |.VgV.|
            |VKKKV|
            |.vVv.|
            """,
            13, 22,
        ),
        Part("|VVVVVVV|", 11, 26),
    ],
    UP: [
        Part("|KdmmmmmmmdK|", 10, 20),
        Part("|VVVVVVV|", 11, 26),
    ],
    LEFT: [
        Part("|KdmmdK|", 12, 21),
    ],
}

GRUNT_M = Character(
    name="eclipse_grunt_m",
    base_member=0x67,
    palette=PALETTE,
    legend=LEGEND,
    index_map=MALE_MAP,
    cut={UP: 20, DOWN: 20, LEFT: 21},
    heads={DOWN: MALE_HEAD_DOWN, UP: MALE_HEAD_UP, LEFT: MALE_HEAD_LEFT},
    overlays=MALE_OVERLAYS,
    band_maps={d: [(26, 32, {10: 11, 7: 1}), (27, 32, {8: 12})] for d in (UP, DOWN, LEFT)},
)

# ---------------------------------------------------------------------------
# Female
# ---------------------------------------------------------------------------

# Stock grunt F palette: 1-3 hair, 4 outline, 5 dark, 6 lavender, 7 white, 8/9/A skin,
# B dark grey, C grey, D/E gold.
FEMALE_MAP = {1: 2, 2: 4, 3: 3, 4: 1, 5: 1, 6: 3, 7: 4, 8: 10, 9: 8, 10: 9, 11: 2, 12: 3, 13: 6, 14: 5}

FEMALE_HEAD_DOWN = Part(
    """
    |......KKKKK......|
    |....KKdmmmdKK....|
    |...KdmmlllmmdK...|
    |..KdmmlVgVlmmdK..|
    |..KdmlVKKKVlmdK..|
    |.KddmlVKKKVlmddK.|
    |.KdmmmlvVvlmmmdK.|
    |.KdmKKKKKKKKKmdK.|
    |KddKhhhHhHhhhKddK|
    |KdKhhHaaaaaHhhKdK|
    |KdKhaKaaaaaKahKdK|
    |KdKhaKaaaaaKahKdK|
    |KdKHhnaaaaanhHKdK|
    |.KKhHKsnnnsKHhKK.|
    |..KhHKKdddKKHhK..|
    """,
    7, 5,
)

FEMALE_HEAD_UP = Part(
    """
    |......KKKKK......|
    |....KKdmmmdKK....|
    |...KdmmlllmmdK...|
    |..KdmmllllmmmdK..|
    |..KdmmlllmmmmdK..|
    |.KddmmmlmmmmmddK.|
    |.KdmmmmmmmmmmmdK.|
    |.KddmmmVVVmmmddK.|
    |KdddmmVKKKVmmdddK|
    |KddddmVKKKVmddddK|
    |KdddddmvvvmdddddK|
    |KddddddmmmddddddK|
    |.KddddKhhHKddddK.|
    |.KKdddKhHhKdddKK.|
    |...KKKKHhHKKKK...|
    """,
    7, 5,
)

FEMALE_HEAD_LEFT = Part(
    """
    |.......KKKK......|
    |.....KKdmmmKK....|
    |....KdmllllmdK...|
    |...KdmlllllmmdK..|
    |..KdmllllmmmmdK..|
    |..KdmlllmmVVmmdK.|
    |..KdmllmmVKKVmdK.|
    |.KdmmlmmmVKKVmddK|
    |.KdmmmmmmmvvmmddK|
    |.KKKKKdmmmmmmmddK|
    |.KhhHKKdmmmmmmddK|
    |.KhaaaKdmmmmmmdKK|
    |.KaKaasKdmmmmdKhK|
    |.KaKaanKdmmmddKhK|
    |..KaaasKdmmmdKHhK|
    |...KssKKddddKhHK.|
    """,
    8, 5,
)

FEMALE_OVERLAYS = {
    DOWN: [
        Part("|KhH|", 8, 20),
        Part("|HhK|", 20, 20),
        Part("|KH|", 8, 21),
        Part("|HK|", 21, 21),
        Part("|KdmmmdK|", 12, 20),
        Part("|mmm|", 14, 21),
        Part(
            """
            |.VgV.|
            |VKKKV|
            |.vVv.|
            """,
            13, 22,
        ),
        Part("|VVVVVVV|", 11, 26),
    ],
    UP: [
        Part("|KdKhHhKdK|", 11, 20),
        Part("|KhHK|", 13, 21),
        Part("|KHK|", 13, 22),
        Part("|K|", 14, 23),
        Part("|VVVVVVV|", 11, 26),
    ],
    LEFT: [
        Part("|KdmmdK|", 12, 21),
        Part("|KhK|", 20, 21),
        Part("|K|", 21, 22),
    ],
}

GRUNT_F = Character(
    name="eclipse_grunt_f",
    base_member=0x68,
    palette=PALETTE,
    legend=LEGEND,
    index_map=FEMALE_MAP,
    cut={UP: 20, DOWN: 20, LEFT: 21},
    heads={DOWN: FEMALE_HEAD_DOWN, UP: FEMALE_HEAD_UP, LEFT: FEMALE_HEAD_LEFT},
    overlays=FEMALE_OVERLAYS,
    band_maps={d: [(26, 28, {11: 11}), (27, 32, {7: 12, 6: 12})] for d in (UP, DOWN, LEFT)},
)

CHARACTERS = [GRUNT_M, GRUNT_F]
