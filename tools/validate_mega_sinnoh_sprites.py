#!/usr/bin/env python3
"""Validate native-format Mega Sinnoh starter sprite assets."""

from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SPECIES = ("torterra", "infernape", "empoleon")
FACES = ("front", "back")


def occupied_bbox(frame: Image.Image) -> tuple[int, int, int, int] | None:
    # Palette index 0 is the transparent battle-sprite background.
    mask = frame.point(lambda value: 0 if value == 0 else 255, mode="1")
    return mask.getbbox()


def edge_labels(bbox: tuple[int, int, int, int] | None) -> str:
    if bbox is None:
        return "empty"
    left, top, right, bottom = bbox
    return "".join(
        label
        for label, condition in (
            ("L", left == 0),
            ("T", top == 0),
            ("R", right == 80),
            ("B", bottom == 80),
        )
        if condition
    ) or "none"


def main() -> None:
    failures: list[str] = []
    rows: list[str] = []

    for species in SPECIES:
        folder = ROOT / "res" / "pokemon" / species / "forms" / "mega"
        palette_colors: dict[str, list[tuple[int, int, int]]] = {}
        for palette_name in ("normal", "shiny"):
            values = []
            for line in (folder / f"{palette_name}.pal").read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("JASC") and not line.isdigit():
                    values.append(tuple(int(channel) for channel in line.split()))
            palette_colors[palette_name] = values
            if len(values) != 16:
                failures.append(f"{species} {palette_name}.pal has {len(values)} colors, expected 16")

        for face in FACES:
            path = folder / f"{face}.png"
            image = Image.open(path)
            canonical = Image.open(folder.parent.parent / f"male_{face}.png")
            if image.size != (160, 80):
                failures.append(f"{path}: size {image.size}, expected (160, 80)")
            if image.mode != "P":
                failures.append(f"{path}: mode {image.mode}, expected P")

            used = sorted(set(image.get_flattened_data()))
            if not used or used[0] != 0 or max(used) > 15:
                failures.append(f"{path}: palette indices must stay within 0..15 and include 0; got {used}")

            key_path = path.with_suffix(path.suffix + ".key")
            key_size = key_path.stat().st_size if key_path.exists() else -1
            if key_size != 4:
                failures.append(f"{key_path}: size {key_size}, expected 4")

            bounds = []
            edge_touches = []
            for frame_number in range(2):
                frame_box = (frame_number * 80, 0, (frame_number + 1) * 80, 80)
                frame = image.crop(frame_box)
                canonical_frame = canonical.crop(frame_box)
                bbox = occupied_bbox(frame)
                canonical_bbox = occupied_bbox(canonical_frame)
                bounds.append(bbox)
                touches = edge_labels(bbox)
                canonical_touches = edge_labels(canonical_bbox)
                edge_touches.append(touches)
                if bbox is None:
                    failures.append(f"{path}: frame {frame_number + 1} is empty")
                else:
                    # Bottom contact is acceptable for grounding. Canonical rear views may
                    # deliberately crop at lateral/top edges; fail only newly introduced contact.
                    new_clipped_edges = (
                        set(touches).intersection({"L", "T", "R"})
                        - set(canonical_touches).intersection({"L", "T", "R"})
                    )
                    if new_clipped_edges:
                        failures.append(
                            f"{path}: frame {frame_number + 1} introduces clipped edges "
                            f"({''.join(sorted(new_clipped_edges))}); canonical={canonical_touches}, mega={touches}"
                        )

            rows.append(
                f"{species:9} {face:5} mode={image.mode} size={image.size[0]}x{image.size[1]} "
                f"indices={len(used):2}/{max(used):2} key={key_size} "
                f"frame1={bounds[0]} edges={edge_touches[0]} "
                f"frame2={bounds[1]} edges={edge_touches[1]}"
            )

    print("\n".join(rows))
    if failures:
        print("\nFAILURES:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)
    print("\nAll six Mega Sinnoh starter sprite sheets passed native-format validation.")


if __name__ == "__main__":
    main()
