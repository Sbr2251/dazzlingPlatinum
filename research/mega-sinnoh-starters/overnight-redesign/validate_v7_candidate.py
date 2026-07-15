from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path('/home/ubuntu/dazzlingPlatinum')
SPECIES = ('torterra', 'infernape', 'empoleon')
VIEWS = ('front', 'back')


def components(mask: np.ndarray) -> list[int]:
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    sizes: list[int] = []
    for y0, x0 in zip(*np.nonzero(mask)):
        if seen[y0, x0]:
            continue
        seen[y0, x0] = True
        q: deque[tuple[int, int]] = deque([(x0, y0)])
        size = 0
        while q:
            x, y = q.popleft(); size += 1
            for ny in range(max(0, y - 1), min(h, y + 2)):
                for nx in range(max(0, x - 1), min(w, x + 2)):
                    if mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True; q.append((nx, ny))
        sizes.append(size)
    return sorted(sizes, reverse=True)


def bbox(mask: np.ndarray) -> list[int] | None:
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)]


def iou(a: np.ndarray, b: np.ndarray) -> float:
    union = np.logical_or(a, b).sum()
    return float(np.logical_and(a, b).sum() / union) if union else 1.0


def load_palette(path: Path) -> list[tuple[int, int, int]]:
    values = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('JASC') and not line.isdigit():
            values.append(tuple(int(v) for v in line.split()))
    return values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('candidate_root', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()

    failures: list[str] = []
    report: dict = {'candidate_root': str(args.candidate_root), 'species': {}}

    for species in SPECIES:
        folder = args.candidate_root / species
        report['species'][species] = {}
        for palette_name in ('normal', 'shiny'):
            p = folder / f'{palette_name}.pal'
            colors = load_palette(p)
            report['species'][species][f'{palette_name}_palette_size'] = len(colors)
            if len(colors) != 16:
                failures.append(f'{species} {palette_name}.pal has {len(colors)} colors, expected 16')

        masks: dict[str, np.ndarray] = {}
        for view in VIEWS:
            path = folder / f'{view}.png'
            image = Image.open(path)
            if image.size != (160, 80):
                failures.append(f'{species} {view}: size={image.size}, expected 160x80')
            if image.mode != 'P':
                failures.append(f'{species} {view}: mode={image.mode}, expected P')
            used = sorted(set(image.getdata()))
            if not used or used[0] != 0 or max(used) > 15:
                failures.append(f'{species} {view}: invalid indices {used}')
            key_path = path.with_suffix(path.suffix + '.key')
            if not key_path.exists() or key_path.stat().st_size != 4:
                failures.append(f'{species} {view}: invalid or absent .key')

            frames = []
            frame_meta = []
            for frame_index in range(2):
                frame = np.array(image.crop((frame_index * 80, 0, (frame_index + 1) * 80, 80)))
                mask = frame != 0
                frames.append(mask)
                bounds = bbox(mask)
                comp = components(mask)
                occupied = int(mask.sum())
                largest_share = float(comp[0] / occupied) if occupied else 0.0
                margins = None if bounds is None else [bounds[0], bounds[1], 80 - bounds[2], 80 - bounds[3]]
                if bounds is None:
                    failures.append(f'{species} {view} frame{frame_index}: empty')
                elif min(margins[0], margins[1], margins[2]) < 2:
                    failures.append(f'{species} {view} frame{frame_index}: unsafe left/top/right margin {margins}')
                if largest_share < 0.985:
                    failures.append(f'{species} {view} frame{frame_index}: largest component share {largest_share:.4f} < 0.985')
                frame_meta.append({
                    'bbox': bounds,
                    'margins_ltrb': margins,
                    'occupied': occupied,
                    'component_sizes': comp[:8],
                    'largest_component_share': largest_share,
                })

            diff = int(np.logical_xor(frames[0], frames[1]).sum())
            overlap = iou(frames[0], frames[1])
            if diff < 30:
                failures.append(f'{species} {view}: animation diff {diff} < 30')
            if overlap < 0.80 or overlap > 0.99:
                failures.append(f'{species} {view}: animation silhouette IoU {overlap:.4f} outside 0.80..0.99')
            masks[view] = frames[0]
            report['species'][species][view] = {
                'mode': image.mode,
                'size': list(image.size),
                'used_indices': used,
                'frames': frame_meta,
                'animation_xor_pixels': diff,
                'animation_iou': overlap,
            }

        front_rear_iou = iou(masks['front'], masks['back'])
        if front_rear_iou > 0.80:
            failures.append(f'{species}: front/rear silhouette IoU {front_rear_iou:.4f} > 0.80')
        report['species'][species]['front_rear_iou'] = front_rear_iou

        canonical_path = ROOT / 'res/pokemon' / species / 'male_front.png'
        canonical = np.array(Image.open(canonical_path).crop((0, 0, 80, 80))) != 0
        base_iou = iou(masks['front'], canonical)
        if base_iou > 0.72:
            failures.append(f'{species}: Mega/base front silhouette IoU {base_iou:.4f} > 0.72')
        report['species'][species]['mega_base_front_iou'] = base_iou

    report['failures'] = failures
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    if failures:
        raise SystemExit(1)
    print('All v7 candidate technical and differentiation gates passed.')


if __name__ == '__main__':
    main()
