import sys
from PIL import Image, ImageDraw
src, out, x0, y0, x1, y1 = sys.argv[1], sys.argv[2], *map(int, sys.argv[3:7])
S = 2
im = Image.open(src).convert('RGB').crop((x0, y0, x1, y1))
im = im.resize((im.width * S, im.height * S), Image.NEAREST)
d = ImageDraw.Draw(im)
for gx in range(0, x1 - x0, 32):
    d.line([(gx * S, 0), (gx * S, im.height)], fill=(255, 0, 0))
for gy in range(0, y1 - y0, 32):
    d.line([(0, gy * S), (im.width, gy * S)], fill=(255, 0, 0))
for gx in range(0, x1 - x0, 32):
    for gy in range(0, y1 - y0, 32):
        d.text((gx * S + 1, gy * S + 1), f"{(x0+gx)//32},{(y0+gy)//32}", fill=(255, 255, 0))
im.save(out)
