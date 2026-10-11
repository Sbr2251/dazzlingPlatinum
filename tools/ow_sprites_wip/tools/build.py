import sys, json, colorsys
sys.dont_write_bytecode = True
sys.path.insert(0, '/tmp/a1r3/tools')
from extract import *

CANDS = []
TSRU = 'https://www.spriters-resource.com/ds_dsi/'
PCCP_URL = 'https://www.pokecommunity.com/threads/playable-character-community-project.414973/'
PCCP_GH = 'https://github.com/Slawter666/pokeemerald/tree/costume/graphics/event_objects/pics/people/'


def add(char, key, name, walk, extras=(), run=None, **meta):
    titles = {'darren_boy': 'Darren (boy)', 'darren_girl': 'Darren (girl)', 'garius': 'Garius', 'ruth': 'Ruth'}
    meta['char_title'] = titles[char]
    c = Candidate(char, key, name, walk, extras, run=run, meta=meta).process().write()
    CANDS.append(c)
    print(char, key, 'shift', c.dx, c.dy, 'colours', c.orig_colors, '->', len(c.pal))
    return c


bw_hero_img = Image.open(SRC / 'tsr_34024.png')
nate_img = Image.open(SRC / 'tsr_48040.png')
rosa_img = Image.open(SRC / 'tsr_48044.png')
bw_ent = Image.open(SRC / 'tsr_34109.png')
b2_ent = Image.open(SRC / 'tsr_48049.png')

# ---------------- Darren, boy
w, r, e = pccp_hero('ethan')
add('darren_boy', 'B1_ethan', 'Ethan (HGSS)', w, e, run=r,
    sets='walk, run, bike, surf, fish (+ field move, watering)',
    source_short='HGSS art via Playable Character Community Project (Slawter666)',
    url=PCCP_GH + 'ethan', page=PCCP_URL)
w, r, e = bw_hero(bw_hero_img, 4, 4)
add('darren_boy', 'B2_hilbert', 'Hilbert (Black/White)', w, e, run=r,
    sets='walk, run, bike, surf, fish (+ misc poses)', source_short='TSR BW #34024, ripped by Barubary',
    url=TSRU + 'pokemonblackwhite/asset/34024/')
w, r, e = b2_hero(nate_img)
add('darren_boy', 'B3_nate', 'Nate (Black 2/White 2)', w, e, run=r,
    sets='walk, run, bike, surf, fish (+ misc poses)', source_short='TSR B2W2 #48040, ripped by Dazz',
    url=TSRU + 'pokemonblack2white2/asset/48040/')
w = walk_emerald(emerald_frames(PCCP / 'incomplete/brendan.png'))
add('darren_boy', 'B4_brendan_g4', 'Brendan, Gen 4 style (fan sprite)', w,
    sets='walk only', source_short='Kyle-Dove via Playable Character Community Project (incomplete set)',
    url=PCCP_GH + 'incomplete/brendan.png', page=PCCP_URL)

# ---------------- Darren, girl
w, r, e = pccp_hero('lyra')
add('darren_girl', 'G1_lyra', 'Lyra (HGSS)', w, e, run=r,
    sets='walk, run, bike, surf, fish (+ field move, watering)', source_short='HGSS art via Playable Character Community Project (Slawter666)',
    url=PCCP_GH + 'lyra', page=PCCP_URL)
w, r, e = bw_hero(bw_hero_img, 144, 268)
add('darren_girl', 'G2_hilda', 'Hilda (Black/White)', w, e, run=r,
    sets='walk, run, bike, surf, fish (+ misc poses)', source_short='TSR BW #34024, ripped by Barubary',
    url=TSRU + 'pokemonblackwhite/asset/34024/')
w, r, e = b2_hero(rosa_img)
add('darren_girl', 'G3_rosa', 'Rosa (Black 2/White 2)', w, e, run=r,
    sets='walk, run, bike, surf, fish (+ misc poses)', source_short='TSR B2W2 #48044, ripped by redblueyellow',
    url=TSRU + 'pokemonblack2white2/asset/48044/')
w, r, e = pccp_hero('leaf')
add('darren_girl', 'G4_leaf_g4', 'Leaf, Gen 4 style (fan sprite)', w,
    sets='walk only (the run/bike/surf/fish files in the repo are copies of Red, not Leaf)', source_short='tebited15 via Playable Character Community Project',
    url=PCCP_GH + 'leaf', page=PCCP_URL)

# ---------------- Garius
hugh_cells = grid(b2_ent, 928, 3936, 3, 6)
hugh_walk = walk_bw3(hugh_cells[:4])
hugh_extra = [('extra poses', hugh_cells[4] + hugh_cells[5][:2])]
add('garius', 'R1_hugh', 'Hugh (Black 2/White 2)', hugh_walk, hugh_extra,
    sets='walk (+5 cutscene poses)', source_short='TSR B2W2 #48049 Overworld Entities, ripped by Barubary',
    url=TSRU + 'pokemonblack2white2/asset/48049/')


def eclipse(c):
    r, g, b = c
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    hd = h * 360
    if s > 0.3 and (hd < 25 or hd > 330):          # red jacket -> Eclipse violet
        h, s, v = 272 / 360, min(1, s * 0.9), v * 0.85
    elif s > 0.25 and 190 < hd < 260:               # blue hair -> near-black slate
        h, s, v = 240 / 360, s * 0.45, v * 0.55
    elif s < 0.2 and v > 0.75:                      # whites -> cold lilac grey
        h, s, v = 270 / 360, 0.12, v * 0.82
    return tuple(int(round(x * 255)) for x in colorsys.hsv_to_rgb(h, s, v))


def recolor_frames(walk, fn):
    out = {}
    for f, frames in walk.items():
        out[f] = []
        for im in frames:
            o = im.copy(); px = o.load()
            for y in range(o.height):
                for x in range(o.width):
                    p = px[x, y]
                    if p[3]:
                        px[x, y] = fn(p[:3]) + (255,)
            out[f].append(o)
    return out


add('garius', 'R1e_hugh_eclipse', 'Hugh recoloured: "Eclipse" Garius (Arc 3)', recolor_frames(hugh_walk, eclipse),
    sets='walk (palette swap of R1)', source_short='palette swap of TSR B2W2 #48049 Hugh (this research)',
    url=TSRU + 'pokemonblack2white2/asset/48049/')
w = walk_emerald(emerald_frames(PCCP / 'rivals/silver.png'))
add('garius', 'R2_silver', 'Silver (HGSS)', w,
    sets='walk', source_short='HGSS art via Playable Character Community Project (also TSR HGSS #26955)',
    url=PCCP_GH + 'rivals/silver.png', page=PCCP_URL)
w = walk_emerald(emerald_frames(PCCP / 'rivals/blue.png'))
add('garius', 'R3_blue_g4', 'Blue, Gen 4 style (fan sprite)', w,
    sets='walk', source_short='Playable Character Community Project (rivals/blue.png)',
    url=PCCP_GH + 'rivals/blue.png', page=PCCP_URL)
w, _ = recolor_stock('OBJ_EVENT_GFX_ACE_TRAINER_M', {
    1: (96, 40, 24), 3: (184, 88, 40), 2: (240, 152, 72),            # copper hair
    13: (56, 104, 168), 14: (112, 160, 224), 11: (32, 48, 88), 12: (64, 64, 80),  # blue jacket
})
add('garius', 'R4_stock_acetrainer_recolour', 'Stock Ace Trainer M, recoloured', w,
    sets='walk (stock NPC member)', source_short='Platinum OBJ_EVENT_GFX_ACE_TRAINER_M (member 0x0B) palette swap',
    url='repo: res/prebuilt/data/mmodel/mmodel (stock member)')

# ---------------- Ruth
sci = grid(bw_ent, 928, 544, 2, 4)
add('ruth', 'T1_bw_scientist_f', 'Scientist F (Black/White)', walk_2col4(sci),
    sets='walk', source_short='TSR BW #34109 Overworld Entities, ripped by Barubary',
    url=TSRU + 'pokemonblackwhite/asset/34109/')
w, _ = recolor_stock('OBJ_EVENT_GFX_SCIENTIST_F', {
    1: (72, 32, 24), 2: (152, 64, 40), 3: (208, 112, 64),            # copper hair
    9: (240, 232, 200), 12: (208, 192, 144), 10: (144, 112, 80), 11: (176, 144, 104), 13: (96, 72, 64),  # canvas work coat
})
add('ruth', 'T2_stock_scientist_recolour', 'Stock Scientist F, recoloured', w,
    sets='walk (stock NPC member)', source_short='Platinum OBJ_EVENT_GFX_SCIENTIST_F palette swap',
    url='repo: res/prebuilt/data/mmodel/mmodel (stock member)')
bp = grid(bw_ent, 0, 416, 2, 4)
add('ruth', 'T3_bw_backpacker_f', 'Backpacker F (Black/White)', walk_bw2(bp),
    sets='walk', source_short='TSR BW #34109 Overworld Entities, ripped by Barubary',
    url=TSRU + 'pokemonblackwhite/asset/34109/')
rg = grid(bw_ent, 0, 288, 2, 4)
add('ruth', 'T4_bw_ranger_f', 'Pokemon Ranger F (Black/White)', walk_bw2(rg),
    sets='walk', source_short='TSR BW #34109 Overworld Entities, ripped by Barubary',
    url=TSRU + 'pokemonblackwhite/asset/34109/')

json.dump([{'char': c.char, 'key': c.key, 'name': c.name, 'colors_in': c.orig_colors, 'colors_out': len(c.pal),
            'shift': [c.dx, c.dy], **{k: v for k, v in c.meta.items() if k != 'char_title'}} for c in CANDS],
          open('/tmp/a1r3/ow_sprites/candidates.json', 'w'), indent=1)

# clipping report
for c in CANDS:
    lost = 0
    for f in FACINGS:
        for raw in c.walk_raw[f]:
            a = sum(1 for p in raw.getdata() if p[3] >= 128)
            b = sum(1 for p in shift(raw, c.dx, c.dy).getdata() if p[3] >= 128)
            lost += a - b
    top = min(bbox(fr)[1] for f in FACINGS for fr in c.walk[f])
    print('clip', c.key, 'lost px', lost, 'top row', top)
