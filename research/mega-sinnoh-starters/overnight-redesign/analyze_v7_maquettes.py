from pathlib import Path
from collections import Counter
from PIL import Image
import numpy as np

ROOT = Path(__file__).resolve().parent / "v7-generated-underdrawings"
for path in sorted(ROOT.glob("*_maquette.png")):
    im = Image.open(path).convert("RGBA")
    a = np.asarray(im)
    h, w = a.shape[:2]
    alpha = a[:, :, 3]
    border = np.concatenate([
        a[0, :, :3], a[-1, :, :3], a[:, 0, :3], a[:, -1, :3]
    ], axis=0)
    border_counts = Counter(map(tuple, border.tolist()))
    rgb_counts = Counter(map(tuple, a[:, :, :3].reshape(-1, 3).tolist()))
    print(f"\n{path.name}: mode={im.mode} size={im.size}")
    print(f"  alpha min={int(alpha.min())} max={int(alpha.max())} nonopaque={int((alpha < 255).sum())} transparent={int((alpha == 0).sum())}")
    print(f"  unique_rgb={len(rgb_counts)} top_rgb={rgb_counts.most_common(8)}")
    print(f"  border_top={border_counts.most_common(8)}")

    # Candidate foreground excludes near-white, checkerboard grays, vivid magenta, and exact black only when it dominates borders.
    rgb = a[:, :, :3]
    near_white = (rgb.min(axis=2) >= 245)
    checker_gray = ((rgb.max(axis=2) - rgb.min(axis=2)) <= 3) & (rgb[:, :, 0] >= 180) & (rgb[:, :, 0] <= 245)
    magenta = (rgb[:, :, 0] >= 170) & (rgb[:, :, 2] >= 130) & (rgb[:, :, 1] <= 90)
    exact_black = (rgb.max(axis=2) <= 5)
    dominant_border_black = border_counts.get((0, 0, 0), 0) > (2 * (w + h)) * 0.25
    bg = near_white | checker_gray | magenta
    if dominant_border_black:
        bg |= exact_black
    fg = (~bg) & (alpha > 0)
    ys, xs = np.nonzero(fg)
    if len(xs):
        print(f"  candidate_bbox=({xs.min()},{ys.min()})-({xs.max()},{ys.max()}) count={len(xs)}")
    else:
        print("  candidate_bbox=NONE")
