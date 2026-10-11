"""Probe: list panels (uniform-colour regions) and sprite bboxes in a sheet."""
import sys
from collections import deque
from PIL import Image

def panel_bbox(im, x, y):
    px = im.load(); W, H = im.size
    c = px[x, y]
    seen = bytearray(W * H)
    q = deque([(x, y)]); seen[y * W + x] = 1
    x0 = x1 = x; y0 = y1 = y
    while q:
        a, b = q.popleft()
        x0 = min(x0, a); x1 = max(x1, a); y0 = min(y0, b); y1 = max(y1, b)
        for na, nb in ((a+1,b),(a-1,b),(a,b+1),(a,b-1)):
            if 0 <= na < W and 0 <= nb < H and not seen[nb*W+na] and px[na, nb] == c:
                seen[nb*W+na] = 1; q.append((na, nb))
    return (x0, y0, x1 + 1, y1 + 1), c

def sprites(im, box, bg, gap=2):
    px = im.load(); x0, y0, x1, y1 = box
    W = x1 - x0; H = y1 - y0
    mask = [[px[x0+i, y0+j] != bg for i in range(W)] for j in range(H)]
    seen = [[False]*W for _ in range(H)]
    out = []
    for j in range(H):
        for i in range(W):
            if mask[j][i] and not seen[j][i]:
                q = deque([(i, j)]); seen[j][i] = True; bx0=bx1=i; by0=by1=j
                while q:
                    a, b = q.popleft()
                    bx0=min(bx0,a); bx1=max(bx1,a); by0=min(by0,b); by1=max(by1,b)
                    for da in range(-gap, gap+1):
                        for db in range(-gap, gap+1):
                            na, nb = a+da, b+db
                            if 0<=na<W and 0<=nb<H and mask[nb][na] and not seen[nb][na]:
                                seen[nb][na]=True; q.append((na,nb))
                if (bx1-bx0) > 4 and (by1-by0) > 4:
                    out.append((x0+bx0, y0+by0, x0+bx1+1, y0+by1+1))
    return out

if __name__ == '__main__':
    im = Image.open(sys.argv[1]).convert('RGB')
    for spec in sys.argv[2:]:
        x, y = map(int, spec.split(','))
        box, c = panel_bbox(im, x, y)
        sp = sprites(im, box, c)
        print('panel', box, c, 'n=', len(sp))
        rows = {}
        for s in sorted(sp, key=lambda s: (s[1], s[0])):
            print('   ', s, 'w', s[2]-s[0], 'h', s[3]-s[1])
