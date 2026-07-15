#!/usr/bin/env python3
"""Build native test assets from the strict Mega Sinnoh starter redesign sources."""

from __future__ import annotations

import sys
from collections import deque
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from build_mega_sinnoh_sprites import (  # noqa: E402
    build_rgba_sheet as original_build_rgba_sheet,
    extract_palette,
    indexed_image,
    remove_generated_background,
    shiny_color,
    write_jasc_palette,
    write_key,
)

SOURCE = ROOT / "research/mega-sinnoh-starters/redesign/source"
NATIVE = ROOT / "research/mega-sinnoh-starters/redesign/native"
SOURCES = {
    "torterra": {
        "front": SOURCE / "mega_torterra_front_v3.png",
        "back": SOURCE / "mega_torterra_back_v3.png",
    },
    "infernape": {
        "front": SOURCE / "mega_infernape_front_v2.png",
        "back": SOURCE / "mega_infernape_back_v2.png",
    },
    "empoleon": {
        "front": SOURCE / "mega_empoleon_front_v2.png",
        "back": SOURCE / "mega_empoleon_back_v2.png",
    },
}


def remove_edge_connected_artifacts(image: Image.Image) -> Image.Image:
    """Remove opaque components touching the sheet edge (bands, borders, baselines)."""
    image = image.convert("RGBA")
    width, height = image.size
    pixels = image.load()
    marked = bytearray(width * height)
    queue: deque[tuple[int, int]] = deque()

    def enqueue(x: int, y: int) -> None:
        index = y * width + x
        if marked[index] or pixels[x, y][3] < 128:
            return
        marked[index] = 1
        queue.append((x, y))

    for x in range(width):
        enqueue(x, 0)
        enqueue(x, height - 1)
    for y in range(height):
        enqueue(0, y)
        enqueue(width - 1, y)

    while queue:
        x, y = queue.popleft()
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < width and 0 <= ny < height:
                enqueue(nx, ny)

    output = image.copy()
    out = output.load()
    for y in range(height):
        for x in range(width):
            if marked[y * width + x]:
                out[x, y] = (0, 0, 0, 0)
    return output


def cleaned_source(path: Path) -> Image.Image:
    cleaned = remove_generated_background(Image.open(path))
    pixels = cleaned.load()
    for y in range(cleaned.height):
        for x in range(cleaned.width):
            r, g, b, a = pixels[x, y]
            # Remove anti-aliased variants of the deliberately artificial magenta backdrop.
            # None of the approved starter designs uses magenta, so this is safe and local
            # to the strict-revision conversion path.
            if a >= 128 and r > 145 and b > 145 and g < 155 and r + b > 2 * g + 120:
                pixels[x, y] = (0, 0, 0, 0)
    return remove_edge_connected_artifacts(cleaned)


def build_rgba_sheet(source: Path, view: str, species: str) -> Image.Image:
    """Reuse production fitting with a temporary pre-cleaned source."""
    clean_path = NATIVE / f".{species}_{view}_clean.png"
    clean_path.parent.mkdir(parents=True, exist_ok=True)
    cleaned_source(source).save(clean_path)
    try:
        return original_build_rgba_sheet(clean_path, view, species)
    finally:
        clean_path.unlink(missing_ok=True)


def main() -> None:
    previews: list[Image.Image] = []
    for species, sources in SOURCES.items():
        front = build_rgba_sheet(sources["front"], "front", species)
        back = build_rgba_sheet(sources["back"], "back", species)
        palette = extract_palette([front, back])
        output_dir = NATIVE / species
        output_dir.mkdir(parents=True, exist_ok=True)

        for view, rgba in (("front", front), ("back", back)):
            path = output_dir / f"{view}.png"
            indexed_image(rgba, palette).save(path, optimize=True, bits=4)
            write_key(path)
            previews.append(indexed_image(rgba, palette).convert("RGB").resize((640, 320), Image.Resampling.NEAREST))

        write_jasc_palette(output_dir / "normal.pal", palette)
        write_jasc_palette(output_dir / "shiny.pal", [shiny_color(species, color) for color in palette])

    contact = Image.new("RGB", (1280, 960), (0, 128, 0))
    for index, preview in enumerate(previews):
        contact.paste(preview, ((index % 2) * 640, (index // 2) * 320))
    contact.save(NATIVE / "mega_sinnoh_redesign_native_preview.png")
    print(f"Wrote native redesign assets and preview to {NATIVE}")


if __name__ == "__main__":
    main()
