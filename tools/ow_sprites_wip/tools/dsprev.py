import sys, importlib
sys.dont_write_bytecode = True
sys.path.insert(0, '/tmp/a1r3/tools')
from contact import stock_walk
from owlib import upscale, on_bg, font
from PIL import Image, ImageDraw


def preview(design, path, S=8, ref='OBJ_EVENT_GFX_PLAYER_M'):
    w = design.walk()
    r = stock_walk(ref)
    cols = [('down', 0), ('down', 1), ('down', 3), ('left', 0), ('left', 1), ('left', 3), ('up', 0), ('up', 1), ('right', 0)]
    out = Image.new('RGB', (len(cols) * 32 * S, 2 * 32 * S), (196, 198, 190))
    d = ImageDraw.Draw(out)
    for c, (f, k) in enumerate(cols):
        out.paste(upscale(on_bg(w[f][k]), S), (c * 32 * S, 0))
        out.paste(upscale(on_bg(r[f][k]), S), (c * 32 * S, 32 * S))
    for y in (7, 29):
        d.line([(0, y * S), (out.width, y * S)], fill=(255, 0, 0))
        d.line([(0, (32 + y) * S), (out.width, (32 + y) * S)], fill=(255, 0, 0))
    out.save(path)


if __name__ == '__main__':
    mod = importlib.import_module(sys.argv[1])
    design = getattr(mod, sys.argv[2])
    preview(design, sys.argv[3], ref=sys.argv[4] if len(sys.argv) > 4 else 'OBJ_EVENT_GFX_PLAYER_M')
