import sys, json
sys.dont_write_bytecode = True
sys.path.insert(0, '/tmp/a1r3/tools')
import owlib
from owlib import *
from contact import stock_walk, png_walk
from free_src import kit_compose, kit_walk, openmon, OM1, OM2
from ds_cast2 import BOY2, GIRL2, GARIUS2, GARIUS2_ECLIPSE, RUTH2
from PIL import Image, ImageDraw

OUT3 = Path('/tmp/a1r3/ow_sprites_ds')
owlib.OUT = OUT3
CANDS = []

OM_LIC = ('"NOT AI GENERATED, MADE BY A FIVERR ARTIST ... These sprites are released under a CC0 License. They were created '
          'as a part of commissions that I ordered and have the full rights to. Use them however you want, no attribution needed."')
KIT_LIC = ('"You can freely use, edit and share it if you want. Credit and a link to your project would be appreciated, though!" '
           '... "even though some of the clothes are inspired by the game I created all resources from scratch (well, and from the vanilla sprites)."')


def add(char, key, name, walk, extras=(), run=None, **meta):
    titles = {'darren_boy': 'Darren (boy)', 'darren_girl': 'Darren (girl)', 'garius': 'Garius', 'ruth': 'Ruth'}
    meta['char_title'] = titles[char]
    c = Candidate(char, key, name, walk, extras, run=run, meta=meta).process()
    owlib.OUT = OUT3
    c.write()
    CANDS.append(c)
    print(char, key, 'shift', c.dx, c.dy, 'colours', c.orig_colors, '->', len(c.pal))
    return c


# ------------------------------------------------------------- redraws (fallback, CC0 designs)
REDRAW = dict(kind='redraw', licence='CC0 1.0 (source design) + new pixels authored for this project',
              lic_quote='Source design licence (Openmon NPC Sprites Set 1, https://screensmith.itch.io/openmon-npc-sprites-set-1): ' + OM_LIC,
              credit='none required (optional: "Designs based on Openmon NPC Sprites Set 1 by Screen Smith, CC0")',
              url='https://screensmith.itch.io/openmon-npc-sprites-set-1',
              creator='pixels: this project (tools/ds_cast2.py, hand-authored grids); design: Openmon (Screen Smith, commissioned Fiverr artist)',
              sets='walk only (redraw); run/bike/surf/fish would follow the same grids')
add('darren_boy', 'D1_redraw_teal_jacket', 'DS redraw: teal-jacket boy', BOY2.walk(), source_short='DS redraw of Openmon teal-jacket boy (CC0 design)', om=('OM2', 5), **REDRAW)
add('darren_girl', 'D2_redraw_blue_ponytail', 'DS redraw: light-blue ponytail girl', GIRL2.walk(), source_short='DS redraw of Openmon light-blue ponytail girl (CC0 design)', om=('OM2', 1), **REDRAW)
add('garius', 'D3_redraw_garius', 'DS redraw: maroon spiky Garius', GARIUS2.walk(), source_short='DS redraw of Openmon spiky maroon-hair boy (CC0 design)', om=('OM2', 6), **REDRAW)
add('garius', 'D3e_redraw_garius_eclipse', 'DS redraw: Garius, Eclipse palette', GARIUS2_ECLIPSE.walk(), source_short='palette variant of D3 (Arc 3 look)', om=('OM2', 6), **REDRAW)
add('ruth', 'D4_redraw_ruth', 'DS redraw: purple-hair Ruth with glasses', RUTH2.walk(), source_short='DS redraw of Openmon purple-hair glasses girl (CC0 design)', om=('OM2', 4), **REDRAW)

# ------------------------------------------------------------- found DS-style free sprites: Poltergeist kit builds
KIT = dict(kind='found', licence='Free use, edits allowed; credit appreciated  [FLAG: bodies derived from vanilla Pokemon sprites]',
           lic_quote='Eevee Expo resource 317 / PokeCommunity thread 421381 (Poltergeist / Coffee Cup): ' + KIT_LIC,
           credit='"Overworld sprite built with Poltergeist\'s Character Customization Resources (eeveeexpo.com/resources/317)"',
           url='https://eeveeexpo.com/resources/317/', creator='Poltergeist / Coffee Cup (layer kit); combination built here')


def kit(layers_m, sets='walk, run, bike'):
    w, _ = kit_walk(kit_compose('walk', layers_m))
    r, _ = kit_walk(kit_compose('run', layers_m))
    b, _ = kit_walk(kit_compose('bike', layers_m))
    return w, r, [('bike', [b[f][k] for f in FACINGS for k in (0, 1, 3)])]


w, r, e = kit([('bases mf', ['m base dark']), ('bottoms', ['jeans', 'navy']), ('tops', ['open jacket', 'green']), ('hair', ['boy 1/', 'brown'])])
add('darren_boy', 'K1_kit_boy', 'Kit build: dark skin, green open jacket, black hair', w, e, run=r,
    sets='walk, run, bike in kit (+ swimming add-on, Eevee Expo 373); no surf-on-Pokemon or fishing', source_short='Poltergeist kit build (FLAG: vanilla-derived bodies)', **KIT)
w, r, e = kit([('bases mf', ['f base light']), ('bottoms', ['capris', 'navy']), ('tops', ['t-shirt', 'white']), ('carrying stuff', ['bag', 'blue']), ('hair', ['girl 1/', 'cyan'])])
add('darren_girl', 'K2_kit_girl', 'Kit build: cyan long hair, white tee, blue bag', w, e, run=r,
    sets='walk, run, bike in kit (+ swimming add-on); no surf-on-Pokemon or fishing', source_short='Poltergeist kit build (FLAG: vanilla-derived bodies)', **KIT)
w, r, e = kit([('bases mf', ['m base light']), ('bottoms', ['jeans', 'black']), ('tops', ['t-shirt', 'red']), ('hair', ['boy 4/', 'red'])])
add('garius', 'K3_kit_garius', 'Kit build: red hair, red tee, black jeans', w, e, run=r,
    sets='walk, run, bike in kit', source_short='Poltergeist kit build (FLAG: vanilla-derived bodies)', **KIT)
w, r, e = kit([('bases mf', ['f base light']), ('bottoms', ['pencil skirt']), ('tops', ['trenchcoat', 'beige']), ('hair', ['girl 1/', 'purple']), ('hats', ['glasses', 'blue'])])
add('ruth', 'K4_kit_ruth', 'Kit build: purple hair, glasses, beige coat', w, e, run=r,
    sets='walk, run, bike in kit', source_short='Poltergeist kit build (FLAG: vanilla-derived bodies)', **KIT)

json.dump([{'char': c.char, 'key': c.key, 'name': c.name, 'colors_in': c.orig_colors, 'colors_out': len(c.pal),
            **{k: v for k, v in c.meta.items() if k not in ('char_title',)}} for c in CANDS],
          open(OUT3 / 'candidates.json', 'w'), indent=1, default=str)

# ------------------------------------------------------------- comparison sheets vs stock
REFS = [('Lucas', 'OBJ_EVENT_GFX_PLAYER_M'), ('Dawn', 'OBJ_EVENT_GFX_PLAYER_F'), ('Barry', 'OBJ_EVENT_GFX_BARRY'),
        ('NPC: Ace Trainer M', 'OBJ_EVENT_GFX_ACE_TRAINER_M'), ('NPC: Scientist F', 'OBJ_EVENT_GFX_SCIENTIST_F')]
S = 4


def compare_sheet(c, path):
    rows = [(c.name + '  (candidate)', c.walk, True)]
    if c.meta.get('om'):
        sh, idx = c.meta['om']
        rows.append(('Openmon original (Gen 3 style, CC0)', openmon(OM1 if sh == 'OM1' else OM2, idx), False))
    for lab, const in REFS:
        rows.append(('stock ' + lab, stock_walk(const), False))
    fac = [('down', 0), ('down', 1), ('left', 0), ('left', 1), ('up', 0), ('right', 0)]
    lab_w = 300
    W = lab_w + len(fac) * (32 * S + 6) + 10
    H = 70 + len(rows) * (32 * S + 8)
    im = Image.new('RGB', (W, H), (236, 236, 230))
    d = ImageDraw.Draw(im)
    d.text((10, 8), f'{c.meta["char_title"]}: {c.name} vs stock Platinum (4x)', fill=(10, 10, 10), font=font(20))
    d.text((10, 38), 'red lines: y=7 and y=29 (stock Lucas head top / feet). Columns: down, down step, left, left step, up, right',
           fill=(70, 70, 70), font=font(13))
    y = 64
    for lab, w, hi in rows:
        if hi:
            d.rectangle([0, y - 3, W, y + 32 * S + 3], fill=(250, 242, 210))
        d.text((10, y + 50), lab[:40], fill=(20, 20, 20), font=font(14))
        for k, (f, i) in enumerate(fac):
            x = lab_w + k * (32 * S + 6)
            im.paste(upscale(on_bg(w[f][i]), S), (x, y))
            for gy in (7, 29):
                d.line([(x, y + gy * S), (x + 32 * S - 1, y + gy * S)], fill=(230, 60, 60))
        y += 32 * S + 8
    im.save(path)


for c in CANDS:
    compare_sheet(c, OUT3 / c.char / f'{c.key}_vs_stock.png')

# ------------------------------------------------------------- overview (all candidates, one row each, with refs)
def overview(path):
    rows = [(f'stock {lab}', stock_walk(const), 'reference') for lab, const in REFS[:3]]
    rows += [(f'{c.key.split("_")[0]}  {c.name}', c.walk, c.meta['kind']) for c in CANDS]
    fac = [('down', 0), ('down', 1), ('down', 3), ('left', 0), ('left', 1), ('up', 0), ('right', 0)]
    lab_w = 430
    W = lab_w + len(fac) * (32 * S + 4) + 10
    H = 90 + len(rows) * (32 * S + 6)
    im = Image.new('RGB', (W, H), (236, 236, 230))
    d = ImageDraw.Draw(im)
    d.text((10, 8), 'DS-only round: DS redraws (fallback, CC0 designs) + DS-style free kit builds, vs stock (4x)', fill=(10, 10, 10), font=font(22))
    d.text((10, 42), 'yellow rows = DS redraws authored here; blue rows = Poltergeist kit (DS-style, flagged); grey = stock reference', fill=(60, 60, 60), font=font(14))
    y = 80
    for lab, w, kind in rows:
        bg = {'redraw': (250, 242, 210), 'found': (222, 234, 250), 'reference': (226, 226, 222)}[kind]
        d.rectangle([0, y - 2, W, y + 32 * S + 2], fill=bg)
        d.text((10, y + 54), lab[:52], fill=(20, 20, 20), font=font(15))
        for k, (f, i) in enumerate(fac):
            im.paste(upscale(on_bg(w[f][i]), S), (lab_w + k * (32 * S + 4), y))
        y += 32 * S + 6
    im.save(path)


overview(OUT3 / 'ds_overview.png')

# ------------------------------------------------------------- cast GIF (redraws)
frames = []
cast = [c for c in CANDS if c.meta['kind'] == 'redraw']
refs = [('Lucas', stock_walk('OBJ_EVENT_GFX_PLAYER_M')), ('Dawn', stock_walk('OBJ_EVENT_GFX_PLAYER_F')), ('Barry', stock_walk('OBJ_EVENT_GFX_BARRY'))]
items = [(c.meta['char_title'] + (' (Eclipse)' if 'eclipse' in c.key else ''), c.walk) for c in cast] + refs
gw = 20 + len(items) * (32 * S + 30)
for f in ('down', 'left', 'up', 'right'):
    for _ in range(2):
        for k in (1, 0, 3, 2):
            fr = Image.new('RGB', (gw, 32 * S + 40), BG)
            dd = ImageDraw.Draw(fr)
            for i, (t, w) in enumerate(items):
                x = 20 + i * (32 * S + 30)
                fr.paste(upscale(on_bg(w[f][k]), S), (x, 34))
                dd.text((x, 8), t, fill=(20, 20, 20), font=font(13))
            frames.append(fr.convert('P', palette=Image.Palette.ADAPTIVE, colors=128))
frames[0].save(OUT3 / 'ds_redraws_walk.gif', save_all=True, append_images=frames[1:], duration=140, loop=0)
print('done')
