import sys, importlib
sys.dont_write_bytecode = True
sys.path.insert(0, '/tmp/a1r3/tools')
from owlib import upscale, on_bg
from contact import stock_walk
from PIL import Image
mod = importlib.import_module(sys.argv[1]); d = getattr(mod, sys.argv[2]); ref = stock_walk(sys.argv[3])
S = 10
fr = [d.frame('down', 'stand'), ref['down'][0], d.frame('left', 'stand'), ref['left'][0], d.frame('up', 'stand'), ref['up'][0]]
o = Image.new('RGB', (len(fr) * 32 * S, 32 * S), (196, 198, 190))
for i, im in enumerate(fr):
    o.paste(upscale(on_bg(im), S), (i * 32 * S, 0))
o.save(sys.argv[4])
