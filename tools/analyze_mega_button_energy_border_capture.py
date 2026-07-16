#!/usr/bin/env python3
"""Analyze the final MEGA Energy Border emulator capture at native pixel scale."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / "deliverables/mega-button-animation-proof/emulator-capture-final"
REPORT = ROOT / "deliverables/mega-button-animation-proof/final-emulator-pixel-analysis.txt"
CROP = (0, 336, 128, 384)


def load_crop(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB").crop(CROP))


armed_paths = sorted((CAPTURE / "frames").glob("armed_*.png"))
rearmed_paths = sorted((CAPTURE / "frames").glob("rearmed_*.png"))
if len(armed_paths) != 24:
    raise SystemExit(f"expected 24 armed frames, found {len(armed_paths)}")
if len(rearmed_paths) != 8:
    raise SystemExit(f"expected 8 rearmed frames, found {len(rearmed_paths)}")

armed = np.stack([load_crop(path) for path in armed_paths])
rearmed = np.stack([load_crop(path) for path in rearmed_paths])

# Build a per-pixel modal reference representing the stable armed button.
height, width = armed.shape[1:3]
modal = np.empty((height, width, 3), dtype=np.uint8)
for y in range(height):
    for x in range(width):
        modal[y, x] = Counter(map(tuple, armed[:, y, x])).most_common(1)[0][0]

changed = np.any(armed != modal[None, ...], axis=3)
changed_union = np.any(changed, axis=0)
changed_counts = changed.reshape(len(armed), -1).sum(axis=1)

# The center excludes the outer two 8x8 tile bands. It contains the fill and label.
inner = changed_union[16:40, 16:112]
inner_changed = int(inner.sum())
union_changed = int(changed_union.sum())

# Detect fill flashes only inside the central fill/label rectangle. Border tiles are
# intentionally dense because their bevel, outline, and shadow ink all animate together.
max_inner_window = 0
max_inner_window_xy = (16, 16)
for y in range(16, 40 - 7):
    for x in range(16, 112 - 7):
        count = int(changed_union[y : y + 8, x : x + 8].sum())
        if count > max_inner_window:
            max_inner_window = count
            max_inner_window_xy = (x, y)

inactive = load_crop(CAPTURE / "02_mega_cursor_inactive.png")
disarmed = load_crop(CAPTURE / "04_disarmed_cleanup.png")
cleanup_mask = np.any(inactive != disarmed, axis=2)
cleanup_difference = int(cleanup_mask.sum())
cleanup_panel_difference = int(cleanup_mask[8:48, 8:120].sum())
cleanup_inner_difference = int(cleanup_mask[16:40, 16:112].sum())
cleanup_points = np.argwhere(cleanup_mask)
cleanup_bbox = None if not len(cleanup_points) else (
    int(cleanup_points[:, 1].min()),
    int(cleanup_points[:, 0].min()),
    int(cleanup_points[:, 1].max()),
    int(cleanup_points[:, 0].max()),
)

unique_armed = len({frame.tobytes() for frame in armed})
unique_rearmed = len({frame.tobytes() for frame in rearmed})

checks = [
    (unique_armed >= 12, f"armed loop has substantial variation ({unique_armed}/24 unique native crops)"),
    (unique_rearmed >= 6, f"rearm restarts visible motion ({unique_rearmed}/8 unique native crops)"),
    (inner_changed == 0, f"central fill and MEGA label remain pixel-stable ({inner_changed} changed pixels)"),
    (max_inner_window == 0, f"no blocky interior fill flash remains (maximum changed pixels in an inner 8x8 window: {max_inner_window} at {max_inner_window_xy})"),
    (cleanup_inner_difference == 0, f"disarm cleanup restores the inactive button fill and label exactly ({cleanup_inner_difference} inner differences; panel={cleanup_panel_difference}; full_crop={cleanup_difference}; bbox={cleanup_bbox})"),
]

lines = [
    "MEGA ENERGY BORDER — FINAL EMULATOR PIXEL ANALYSIS",
    f"armed_frames={len(armed_paths)}",
    f"rearmed_frames={len(rearmed_paths)}",
    f"union_changed_pixels={union_changed}",
    f"per_frame_changed_pixels_min={int(changed_counts.min())}",
    f"per_frame_changed_pixels_max={int(changed_counts.max())}",
]
for passed, description in checks:
    lines.append(f"{'PASS' if passed else 'FAIL'}: {description}")
lines.append(f"SUMMARY: {sum(passed for passed, _ in checks)} passed, {sum(not passed for passed, _ in checks)} failed")
REPORT.write_text("\n".join(lines) + "\n")
print(REPORT.read_text(), end="")
if not all(passed for passed, _ in checks):
    raise SystemExit(1)
