import sys, json
sys.dont_write_bytecode = True
sys.path.insert(0, '/tmp/a1r3/tools')
from owlib import *
from btx import load, gfx_member_map
from PIL import Image, ImageDraw

S = 4
CW = CELL * S


def png_walk(path):
    p = Image.open(path)
    pal = p.getpalette()
    rgba = Image.new('RGBA', p.size, (0, 0, 0, 0))
    po = rgba.load()
    for i, v in enumerate(p.get_flattened_data() if hasattr(p,'get_flattened_data') else p.getdata()):
        if v:
            po[i % p.width, i // p.width] = (pal[3 * v], pal[3 * v + 1], pal[3 * v + 2], 255)
    return {f: [rgba.crop((c * 32, r * 32, c * 32 + 32, r * 32 + 32)) for c in range(4)] for r, f in enumerate(FACINGS)}


def stock_walk(const):
    t, p, _ = load(gfx_member_map()[const])
    fr = []
    for n, w, h, f, px in t[:16]:
        o = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
        o.putdata([(0, 0, 0, 0) if v == 0 else p[v] + (255,) for v in px])
        fr.append(o)
    return {f: fr[4 * i: 4 * i + 4] for i, f in enumerate(FACINGS)}


SHOW = [('down', 0), ('down', 1), ('down', 3), ('left', 0), ('left', 1), ('up', 0), ('up', 1), ('right', 0)]
SHOW_LAB = ['down', 'step A', 'step B', 'left', 'step', 'up', 'step', 'right']


def row_img(label_lines, walk, highlight=False, width_lab=420):
    W = width_lab + len(SHOW) * (CW + 4) + 10
    H = CW + 16
    im = Image.new('RGB', (W, H), (250, 244, 214) if highlight else (238, 238, 232))
    d = ImageDraw.Draw(im)
    y = 10
    for i, l in enumerate(label_lines):
        d.text((10, y), l, fill=(15, 15, 15) if i == 0 else (70, 70, 70), font=font(19 if i == 0 else 13))
        y += 26 if i == 0 else 18
    for k, (f, c) in enumerate(SHOW):
        im.paste(upscale(on_bg(walk[f][c]), S), (width_lab + k * (CW + 4), 8))
    return im


def contact(char, title, rows, path, note=None):
    hdr = Image.new('RGB', (rows[0].width, 80), (225, 225, 218))
    d = ImageDraw.Draw(hdr)
    d.text((10, 8), title, fill=(10, 10, 10), font=font(26))
    if note:
        d.text((10, 44), note, fill=(60, 60, 60), font=font(14))
    lab = Image.new('RGB', (rows[0].width, 22), (225, 225, 218))
    dl = ImageDraw.Draw(lab)
    for k, l in enumerate(SHOW_LAB):
        dl.text((420 + k * (CW + 4) + 4, 2), l, fill=(40, 40, 40), font=font(14))
    H = hdr.height + lab.height + sum(r.height + 4 for r in rows)
    out = Image.new('RGB', (rows[0].width, H), (205, 205, 198))
    out.paste(hdr, (0, 0)); out.paste(lab, (0, hdr.height))
    y = hdr.height + lab.height
    for r in rows:
        out.paste(r, (0, y)); y += r.height + 4
    out.save(path)
    return out


def main(OUT):
    cands = json.load(open(OUT / 'candidates.json'))
    rec = json.load(open(OUT / 'recommendations.json')) if (OUT / 'recommendations.json').exists() else {}
    refs = {
        'darren_boy': [('Stock ref: Lucas (scale)', 'OBJ_EVENT_GFX_PLAYER_M')],
        'darren_girl': [('Stock ref: Dawn (scale)', 'OBJ_EVENT_GFX_PLAYER_F')],
        'garius': [('Stock ref: Barry (replaced)', 'OBJ_EVENT_GFX_BARRY')],
        'ruth': [('Stock ref: Dawn (counterpart)', 'OBJ_EVENT_GFX_PLAYER_F')],
    }
    titles = {'darren_boy': 'Darren (boy): overworld candidates', 'darren_girl': 'Darren (girl): overworld candidates',
              'garius': 'Garius (rival): overworld candidates', 'ruth': "Ruth (Rowan's assistant): overworld candidates"}
    for char in titles:
        rows = []
        for lab, const in refs[char]:
            rows.append(row_img([lab, 'stock Platinum sprite, not a candidate'], stock_walk(const)))
        for c in [c for c in cands if c['char'] == char]:
            walk = png_walk(OUT / char / f"{c['key']}_platinum_walk.png")
            star = rec.get(char, {}).get(c['key'])
            name = c['key'].split('_')[0] + '  ' + c['name'] + (f'   [{star}]' if star else '')
            rows.append(row_img([name, c['source_short'][:60], 'licence: ' + c.get('licence', '')[:52], 'sets: ' + c['sets'][:56]], walk, highlight=bool(star)))
        contact(char, titles[char], rows, OUT / char / f'{char}_overview.png',
                note=NOTE if 'NOTE' in globals() else 'All frames converted to the Platinum walker layout (32x32, 16 colours, index 0 transparent), shown at 4x.')
        print('wrote', char)


if __name__ == '__main__':
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else OUT)
