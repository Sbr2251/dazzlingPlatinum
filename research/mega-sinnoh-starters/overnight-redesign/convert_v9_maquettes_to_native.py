from __future__ import annotations

import importlib.util
import json
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path('/home/ubuntu/dazzlingPlatinum')
WORK = ROOT / 'research/mega-sinnoh-starters/overnight-redesign'
SOURCE = WORK / 'v8-generated-underdrawings'
BUILDER_PATH = ROOT / 'tools/build_mega_sinnoh_sprites.py'

spec = importlib.util.spec_from_file_location('mega_builder', BUILDER_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f'Could not import {BUILDER_PATH}')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

SPECIES = ('torterra', 'infernape', 'empoleon')
VIEWS = ('front', 'back')
METHODS = {
    'nearest': Image.Resampling.NEAREST,
}


def flood_border_background(candidate: np.ndarray) -> np.ndarray:
    """Return the border-connected subset of a background-candidate mask."""
    h, w = candidate.shape
    seen = np.zeros((h, w), dtype=bool)
    queue: deque[tuple[int, int]] = deque()
    for x in range(w):
        if candidate[0, x]:
            seen[0, x] = True; queue.append((x, 0))
        if candidate[h - 1, x] and not seen[h - 1, x]:
            seen[h - 1, x] = True; queue.append((x, h - 1))
    for y in range(h):
        if candidate[y, 0] and not seen[y, 0]:
            seen[y, 0] = True; queue.append((0, y))
        if candidate[y, w - 1] and not seen[y, w - 1]:
            seen[y, w - 1] = True; queue.append((w - 1, y))
    while queue:
        x, y = queue.popleft()
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < w and 0 <= ny < h and candidate[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                queue.append((nx, ny))
    return seen


def largest_component(mask: np.ndarray) -> np.ndarray:
    """Keep the largest 8-connected foreground component."""
    h, w = mask.shape
    seen = np.zeros((h, w), dtype=bool)
    best: list[tuple[int, int]] = []
    for y0, x0 in zip(*np.nonzero(mask)):
        if seen[y0, x0]:
            continue
        seen[y0, x0] = True
        queue: deque[tuple[int, int]] = deque([(x0, y0)])
        comp: list[tuple[int, int]] = []
        while queue:
            x, y = queue.popleft()
            comp.append((x, y))
            for ny in range(max(0, y - 1), min(h, y + 2)):
                for nx in range(max(0, x - 1), min(w, x + 2)):
                    if mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        queue.append((nx, ny))
        if len(comp) > len(best):
            best = comp
    out = np.zeros_like(mask)
    for x, y in best:
        out[y, x] = True
    return out


def extract_subject(path: Path) -> tuple[Image.Image, dict]:
    im = Image.open(path).convert('RGBA')
    arr = np.asarray(im).copy()
    rgb = arr[:, :, :3].astype(np.int16)
    alpha = arr[:, :, 3]
    has_real_alpha = int((alpha < 16).sum()) > (im.width * im.height * 0.05)

    if has_real_alpha:
        # Generated front maquettes used a magenta transparency key. Remove the
        # remaining vivid key-color artifacts, then keep the principal creature.
        magenta = (rgb[:, :, 0] > 175) & (rgb[:, :, 2] > 150) & (rgb[:, :, 1] < 105)
        raw_mask = (alpha >= 96) & (~magenta)
        segmentation = 'alpha_plus_magenta_key'
    else:
        # Back maquettes are on white or checkerboard canvases. All of those
        # backgrounds are high-value neutral pixels connected to the border;
        # white features enclosed by dark outlines therefore remain intact.
        spread = rgb.max(axis=2) - rgb.min(axis=2)
        neutral_light = (spread <= 15) & (rgb.min(axis=2) >= 145)
        border_bg = flood_border_background(neutral_light)
        raw_mask = ~border_bg
        segmentation = 'border_connected_neutral_flood'

    subject_mask = largest_component(raw_mask)
    ys, xs = np.nonzero(subject_mask)
    if not len(xs):
        raise RuntimeError(f'No subject extracted from {path}')

    # Small source-space pad keeps antialiased edge colors without admitting
    # unrelated border artifacts. Final output is hard-thresholded to DS alpha.
    pad = 4
    x0 = max(0, int(xs.min()) - pad); x1 = min(im.width, int(xs.max()) + pad + 1)
    y0 = max(0, int(ys.min()) - pad); y1 = min(im.height, int(ys.max()) + pad + 1)
    arr[:, :, 3] = np.where(subject_mask, 255, 0).astype(np.uint8)
    subject = Image.fromarray(arr, 'RGBA').crop((x0, y0, x1, y1))
    meta = {
        'source': str(path),
        'segmentation': segmentation,
        'source_size': list(im.size),
        'source_bbox': [x0, y0, x1, y1],
        'source_foreground_pixels': int(subject_mask.sum()),
    }
    return subject, meta


def fit_native(subject: Image.Image, resample: Image.Resampling) -> tuple[Image.Image, dict]:
    max_w, max_h = 74, 74
    scale = min(max_w / subject.width, max_h / subject.height)
    out_w = max(1, round(subject.width * scale))
    out_h = max(1, round(subject.height * scale))
    resized = subject.resize((out_w, out_h), resample=resample)

    # Binary DS transparency; retain any source feature with meaningful coverage.
    a = np.asarray(resized).copy()
    threshold = 32 if resample == Image.Resampling.BOX else 96
    native_mask = a[:, :, 3] >= threshold
    native_mask = largest_component(native_mask)
    a[:, :, 3] = np.where(native_mask, 255, 0).astype(np.uint8)
    resized = Image.fromarray(a, 'RGBA')

    canvas = Image.new('RGBA', (80, 80), (0, 0, 0, 0))
    x = (80 - out_w) // 2
    y = 77 - out_h  # three-pixel floor margin and at least three-pixel top margin
    canvas.alpha_composite(resized, (x, y))
    return canvas, {
        'native_size': [out_w, out_h],
        'native_offset': [x, y],
        'alpha_threshold': threshold,
    }


def make_frame1(frame0: Image.Image, species: str, view: str) -> Image.Image:
    """Create a one-pixel upper-body heave while the lower legs and feet stay fixed.

    Rows above the species-specific anchor sample from one row below, moving all
    upper clusters upward. The anchor row is duplicated once, producing a safe
    one-pixel stretch instead of an alpha gap or a disconnected component.
    """
    anchors = {
        'torterra': 58,
        'infernape': 61,
        'empoleon': 65,
    }
    anchor = anchors[species]
    source = np.asarray(frame0).copy()
    out = source.copy()
    out[:anchor - 1] = source[1:anchor]
    out[anchor - 1] = source[anchor]
    out[anchor:] = source[anchor:]
    return Image.fromarray(out, 'RGBA')


def make_sheet(f0: Image.Image, f1: Image.Image) -> Image.Image:
    out = Image.new('RGBA', (160, 80), (0, 0, 0, 0))
    out.alpha_composite(f0, (0, 0))
    out.alpha_composite(f1, (80, 0))
    return out


def preview(method: str, raw_root: Path) -> None:
    scale = 6
    panel = Image.new('RGBA', (160 * scale, 80 * 6 * scale), (246, 244, 238, 255))
    row = 0
    for species in SPECIES:
        for view in VIEWS:
            sheet = Image.open(raw_root / species / f'{view}_rgba_sheet.png').convert('RGBA')
            panel.alpha_composite(sheet.resize((160 * scale, 80 * scale), Image.Resampling.NEAREST), (0, row * 80 * scale))
            row += 1
    panel.save(WORK / f'target-native-v9-{method}-preview.png')


def build_method(method: str, resample: Image.Resampling) -> dict:
    raw_root = WORK / f'target-native-v9-{method}'
    sheet_root = WORK / f'target-native-v9-{method}-sheets'
    raw_root.mkdir(parents=True, exist_ok=True)
    sheet_root.mkdir(parents=True, exist_ok=True)
    report: dict = {'method': method, 'species': {}}

    for species in SPECIES:
        raw_dir = raw_root / species
        out_dir = sheet_root / species
        raw_dir.mkdir(parents=True, exist_ok=True)
        out_dir.mkdir(parents=True, exist_ok=True)
        rgba_sheets: dict[str, Image.Image] = {}
        report['species'][species] = {}

        for view in VIEWS:
            source_path = SOURCE / f'{species}_{view}_maquette.png'
            subject, source_meta = extract_subject(source_path)
            f0, native_meta = fit_native(subject, resample)
            f1 = make_frame1(f0, species, view)
            f0.save(raw_dir / f'{view}_f0.png')
            f1.save(raw_dir / f'{view}_f1.png')
            rgba_sheets[view] = make_sheet(f0, f1)
            rgba_sheets[view].save(raw_dir / f'{view}_rgba_sheet.png')
            report['species'][species][view] = {**source_meta, **native_meta}

        colors = builder.extract_palette([rgba_sheets['front'], rgba_sheets['back']])
        for view in VIEWS:
            indexed = builder.indexed_image(rgba_sheets[view], colors)
            indexed.info['transparency'] = 0
            path = out_dir / f'{view}.png'
            indexed.save(path, transparency=0, optimize=True, bits=4)
            builder.write_key(path)
        builder.write_jasc_palette(out_dir / 'normal.pal', colors)
        builder.write_jasc_palette(out_dir / 'shiny.pal', [builder.shiny_color(species, color) for color in colors])
        report['species'][species]['palette'] = [list(c) for c in colors]

    report_path = WORK / f'target-native-v9-{method}-conversion-report.json'
    report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    preview(method, raw_root)
    return report


def main() -> None:
    for method, resample in METHODS.items():
        report = build_method(method, resample)
        print(method)
        for species in SPECIES:
            front = report['species'][species]['front']['native_size']
            back = report['species'][species]['back']['native_size']
            print(f'  {species}: front={front} back={back} colors={len(report["species"][species]["palette"])}')


if __name__ == '__main__':
    main()
