import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/tmp/a1r3/tools')
from contact import png_walk
from owlib import *
from PIL import Image, ImageDraw

PICKS = [
    ('Darren (boy)', 'darren_boy', 'B1_ethan', 'Ethan (HGSS)', 'full set: walk/run/bike/surf/fish'),
    ('Darren (girl)', 'darren_girl', 'G1_lyra', 'Lyra (HGSS)', 'full set: walk/run/bike/surf/fish'),
    ('Garius', 'garius', 'R1_hugh', 'Hugh (B2W2)', 'walk (+ cutscene poses)'),
    ('Garius, Eclipse (Arc 3)', 'garius', 'R1e_hugh_eclipse', 'Hugh, Eclipse recolour', 'walk (palette swap)'),
    ('Ruth', 'ruth', 'T1_bw_scientist_f', 'Scientist F (BW)', 'walk'),
]
S = 4
CW = 32 * S
walks = [(t, png_walk(OUT / ch / f'{k}_platinum_walk.png'), n, s) for t, ch, k, n, s in PICKS]
order = ['down', 'left', 'up', 'right']
colw = 4 * (CW + 4) + 30
W = 20 + len(walks) * colw
H = 120 + 4 * (CW + 4) + 40
im = Image.new('RGB', (W, H), (238, 238, 232))
d = ImageDraw.Draw(im)
d.text((20, 10), 'Recommended cast: overworld sprites in the Platinum walker format (4x)', fill=(10, 10, 10), font=font(26))
for i, (t, w, n, s) in enumerate(walks):
    x0 = 20 + i * colw
    d.text((x0, 50), t, fill=(10, 10, 10), font=font(20))
    d.text((x0, 76), n, fill=(60, 60, 60), font=font(14))
    d.text((x0, 94), s, fill=(90, 90, 90), font=font(12))
    for r, f in enumerate(order):
        for c in range(4):
            im.paste(upscale(on_bg(w[f][c]), S), (x0 + c * (CW + 4), 120 + r * (CW + 4)))
d.text((20, H - 30), 'Rows: down, left, up, right. Columns: stand, step A, stand, step B.', fill=(60, 60, 60), font=font(14))
im.save(OUT / 'recommended_cast_overview.png')

# animated: all five walking together, cycling directions
frames = []
seq = [1, 0, 3, 2]
gw = 20 + len(walks) * (CW + 40)
for f in order:
    for _ in range(2):
        for k in seq:
            fr = Image.new('RGB', (gw, CW + 60), BG)
            dd = ImageDraw.Draw(fr)
            for i, (t, w, n, s) in enumerate(walks):
                x = 20 + i * (CW + 40)
                fr.paste(upscale(on_bg(w[f][k]), S), (x, 40))
                dd.text((x, 8), t.replace(', Eclipse (Arc 3)', ' (Eclipse)'), fill=(20, 20, 20), font=font(14))
            frames.append(fr.convert('P', palette=Image.Palette.ADAPTIVE, colors=128))
frames[0].save(OUT / 'recommended_cast_walk.gif', save_all=True, append_images=frames[1:], duration=140, loop=0)
print('ok', im.size)
