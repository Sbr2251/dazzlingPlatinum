#!/usr/bin/env python3
"""Convert generated Mega Sinnoh starter concepts into Platinum 4bpp sprite assets."""

from __future__ import annotations

import colorsys
import struct
import zlib
from collections import deque
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "research/mega-sinnoh-starters/generated"
OUTPUTS = {
    "torterra": {
        "front": GENERATED / "mega_torterra_front_concept.png",
        "back": GENERATED / "mega_torterra_back_refined.png",
    },
    "infernape": {
        "front": GENERATED / "mega_infernape_front_refined.png",
        "back": GENERATED / "mega_infernape_back_concept.png",
    },
    "empoleon": {
        "front": GENERATED / "mega_empoleon_front_concept.png",
        "back": GENERATED / "mega_empoleon_back_concept.png",
    },
}

TRANSPARENT_RGB = (0, 128, 0)


def is_background_candidate(pixel: tuple[int, int, int, int]) -> bool:
    r, g, b, a = pixel
    if a < 128:
        return True
    if r > 180 and b > 180 and g < 110:  # generated magenta removal backdrop
        return True
    spread = max(r, g, b) - min(r, g, b)
    mean = (r + g + b) // 3
    return spread <= 14 and 18 <= mean <= 252  # generated checkerboard backdrop


def remove_generated_background(image: Image.Image) -> Image.Image:
    image = image.convert("RGBA")
    width, height = image.size
    pixels = image.load()
    background = bytearray(width * height)
    queue: deque[tuple[int, int]] = deque()

    def enqueue(x: int, y: int) -> None:
        index = y * width + x
        if background[index] or not is_background_candidate(pixels[x, y]):
            return
        background[index] = 1
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

    output = Image.new("RGBA", image.size, (0, 0, 0, 0))
    out = output.load()
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            index = y * width + x
            global_magenta = r > 180 and b > 180 and g < 110
            if not background[index] and not global_magenta and a >= 128:
                out[x, y] = (r, g, b, 255)
    return output


def nonempty_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    bbox = image.getchannel("A").getbbox()
    if bbox is None:
        raise RuntimeError("No foreground remained after background removal")
    return bbox


def fit_frame(frame: Image.Image, max_width: int, max_height: int, bottom: int) -> Image.Image:
    cropped = frame.crop(nonempty_bbox(frame))
    width, height = cropped.size
    scale = min(max_width / width, max_height / height)
    target = (max(1, round(width * scale)), max(1, round(height * scale)))
    cropped = cropped.resize(target, Image.Resampling.NEAREST)
    canvas = Image.new("RGBA", (80, 80), (0, 0, 0, 0))
    x = (80 - target[0]) // 2
    y = max(0, bottom - target[1])
    canvas.alpha_composite(cropped, (x, y))
    return canvas


def build_rgba_sheet(source: Path, view: str, species: str) -> Image.Image:
    cleaned = remove_generated_background(Image.open(source))
    width, height = cleaned.size
    panels = [cleaned.crop((0, 0, width // 2, height)), cleaned.crop((width // 2, 0, width, height))]

    if species == "torterra":
        max_width, max_height = (76, 74) if view == "front" else (76, 72)
    elif species == "infernape":
        max_width, max_height = (76, 74)
    else:
        max_width, max_height = (76, 75)
    bottom = 78 if view == "front" else 79

    fitted = [fit_frame(panel, max_width, max_height, bottom) for panel in panels]
    sheet = Image.new("RGBA", (160, 80), (0, 0, 0, 0))
    sheet.alpha_composite(fitted[0], (0, 0))
    sheet.alpha_composite(fitted[1], (80, 0))
    return sheet


def round_nds_channel(value: int) -> int:
    return max(0, min(248, int(round(value / 8.0)) * 8))


def round_nds_color(color: tuple[int, int, int]) -> tuple[int, int, int]:
    return tuple(round_nds_channel(value) for value in color)


def extract_palette(images: list[Image.Image]) -> list[tuple[int, int, int]]:
    foreground: list[tuple[int, int, int]] = []
    for image in images:
        for r, g, b, a in image.get_flattened_data():
            if a >= 128:
                foreground.append((r, g, b))
    if not foreground:
        raise ValueError("Cannot extract a palette from fully transparent sprite images")

    sample = Image.new("RGB", (len(foreground), 1))
    sample.putdata(foreground)
    quantized = sample.quantize(colors=15, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    raw_palette = quantized.getpalette() or []
    colors: list[tuple[int, int, int]] = []
    for index in range(0, min(len(raw_palette), 45), 3):
        triplet = raw_palette[index:index + 3]
        if len(triplet) == 3:
            colors.append(round_nds_color((triplet[0], triplet[1], triplet[2])))

    unique: list[tuple[int, int, int]] = []
    for color in colors:
        if color not in unique and color != TRANSPARENT_RGB:
            unique.append(color)
    while len(unique) < 15:
        candidate = round_nds_color((8 * len(unique) + 8, 8 * len(unique) + 8, 8 * len(unique) + 8))
        if candidate not in unique and candidate != TRANSPARENT_RGB:
            unique.append(candidate)
    return unique[:15]


def nearest_color_index(color: tuple[int, int, int], palette: list[tuple[int, int, int]]) -> int:
    if not palette:
        raise ValueError("Cannot map a sprite color into an empty palette")
    if any(len(entry) != 3 for entry in palette):
        raise ValueError(f"Malformed RGB palette entry in {palette!r}")
    r, g, b = color
    return min(
        range(len(palette)),
        key=lambda index: (r - palette[index][0]) ** 2 + (g - palette[index][1]) ** 2 + (b - palette[index][2]) ** 2,
    )


def indexed_image(image: Image.Image, colors: list[tuple[int, int, int]]) -> Image.Image:
    palette = [TRANSPARENT_RGB] + colors
    output = Image.new("P", image.size, 0)
    flat_palette = [channel for color in palette for channel in color]
    output.putpalette(flat_palette + [0] * (768 - len(flat_palette)))
    source = image.load()
    destination = output.load()
    cache: dict[tuple[int, int, int], int] = {}
    for y in range(image.height):
        for x in range(image.width):
            r, g, b, a = source[x, y]
            if a < 128:
                destination[x, y] = 0
                continue
            rgb = (r, g, b)
            if rgb not in cache:
                cache[rgb] = nearest_color_index(rgb, colors) + 1
            destination[x, y] = cache[rgb]
    return output


def shiny_color(species: str, color: tuple[int, int, int]) -> tuple[int, int, int]:
    r, g, b = color
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    if species == "torterra":
        if g > r * 1.08 and g > b * 1.15:
            h = 0.12  # autumn-gold foliage and shell
            s = min(0.75, max(0.35, s))
        elif r > g * 1.12 and g > b * 1.05:
            h = 0.55  # cool blue bark
            s = min(0.45, max(0.20, s))
    elif species == "infernape":
        if r > b * 1.25 and r > 96:
            h = 0.55  # blue/cyan flames and armor
            s = min(0.95, max(0.60, s))
        elif v < 0.42:
            h = 0.75
            s = max(0.25, s)
    elif species == "empoleon":
        if r > b * 1.35 and g > b * 1.15:
            h = 0.52  # cyan-silver gold trim
            s = min(0.45, max(0.15, s * 0.6))
            v = min(1.0, v * 1.12)
        elif b > r * 1.15:
            h = 0.78  # royal violet armor
            s = min(0.70, max(0.30, s))
    rr, gg, bb = colorsys.hsv_to_rgb(h, s, v)
    return round_nds_color((round(rr * 255), round(gg * 255), round(bb * 255)))


def write_jasc_palette(path: Path, colors: list[tuple[int, int, int]]) -> None:
    lines = ["JASC-PAL", "0100", "16"]
    for r, g, b in [TRANSPARENT_RGB] + colors:
        lines.append(f"{r} {g} {b}")
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def write_key(path: Path) -> None:
    key = zlib.crc32(path.read_bytes()) or 1
    path.with_suffix(path.suffix + ".key").write_bytes(struct.pack("<I", key))


def main() -> None:
    preview_frames: list[Image.Image] = []
    for species, sources in OUTPUTS.items():
        front = build_rgba_sheet(sources["front"], "front", species)
        back = build_rgba_sheet(sources["back"], "back", species)
        palette = extract_palette([front, back])
        output_dir = ROOT / f"res/pokemon/{species}/forms/mega"
        output_dir.mkdir(parents=True, exist_ok=True)

        for view, rgba in (("front", front), ("back", back)):
            path = output_dir / f"{view}.png"
            indexed_image(rgba, palette).save(path, optimize=True, bits=4)
            write_key(path)

        write_jasc_palette(output_dir / "normal.pal", palette)
        write_jasc_palette(output_dir / "shiny.pal", [shiny_color(species, color) for color in palette])

        for view, rgba in (("front", front), ("back", back)):
            indexed = indexed_image(rgba, palette).convert("RGB")
            indexed.info.clear()
            preview_frames.append(indexed.resize((640, 320), Image.Resampling.NEAREST))

    contact = Image.new("RGB", (1280, 960), TRANSPARENT_RGB)
    for index, preview in enumerate(preview_frames):
        x = (index % 2) * 640
        y = (index // 2) * 320
        contact.paste(preview, (x, y))
    preview_path = GENERATED / "mega_sinnoh_ingame_asset_preview.png"
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    contact.save(preview_path)
    print(f"Wrote six sprites, six keys, six palettes, and {preview_path}")


if __name__ == "__main__":
    main()
