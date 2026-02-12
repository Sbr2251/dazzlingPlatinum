#!/usr/bin/env python3
"""
Process downloaded mega Pokemon sprites into NDS-compatible format.
- Input: front sprites (256x64 4-frame sheets or 160x160 single) and back sprites (160x160)
- Output: 160x80 4-bit indexed PNGs (two 80x80 frames), JASC-PAL palette files
"""

import sys
import os
import struct
import zlib

# Use the Xcode python which has PIL
sys.path.insert(0, '/Users/sreddy9/Library/Python/3.9/lib/python/site-packages')

from PIL import Image

PROJECT_ROOT = '/Users/sreddy9/Desktop/Pokemon RomHack/dazzlingPlatinum'
SPRITE_DIR = '/tmp/mega_sprites'

SPECIES = [
    'lucario',
    'gengar',
    'gardevoir',
    'alakazam',
    'gyarados',
    'scizor',
]

TRANSPARENT_COLOR = (0, 128, 0)  # NDS transparent marker


def extract_front_sprite(img):
    """Extract a single 64x64 frame from front sprite sheet."""
    w, h = img.size
    if w == 256 and h == 64:
        # 4-frame animation sheet - take first frame
        return img.crop((0, 0, 64, 64))
    elif w == 160 and h == 160:
        # Single large sprite - crop to content area
        # Find bounding box of non-transparent content
        if img.mode == 'RGBA':
            bbox = img.split()[3].getbbox()  # alpha channel bbox
        else:
            bbox = img.getbbox()
        if bbox:
            cropped = img.crop(bbox)
            # Scale to fit in 64x64
            cropped.thumbnail((64, 64), Image.NEAREST)
            result = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
            offset_x = (64 - cropped.width) // 2
            offset_y = 64 - cropped.height  # bottom-align
            result.paste(cropped, (offset_x, offset_y))
            return result
        return img.crop((48, 48, 112, 112))  # center crop
    elif w >= 64 and h >= 64:
        # Take center 64x64
        cx, cy = w // 2, h // 2
        return img.crop((cx - 32, cy - 32, cx + 32, cy + 32))
    else:
        # Scale up
        return img.resize((64, 64), Image.NEAREST)


def extract_back_sprite(img):
    """Extract a single sprite from back sprite image."""
    w, h = img.size
    if img.mode == 'RGBA':
        bbox = img.split()[3].getbbox()
    elif img.mode == 'P':
        # Convert to RGBA to find content bounds
        rgba = img.convert('RGBA')
        bbox = rgba.split()[3].getbbox()
    else:
        bbox = img.getbbox()

    if bbox:
        cropped = img.crop(bbox)
        # Scale to fit in 64x64
        cropped.thumbnail((64, 64), Image.NEAREST)
        result = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        offset_x = (64 - cropped.width) // 2
        offset_y = 64 - cropped.height  # bottom-align
        result.paste(cropped, (offset_x, offset_y))
        return result

    return img.resize((64, 64), Image.NEAREST)


def place_in_80x80(sprite_64):
    """Place a 64x64 sprite centered in an 80x80 canvas."""
    sprite_64 = sprite_64.convert('RGBA')
    canvas = Image.new('RGBA', (80, 80), (0, 0, 0, 0))
    offset_x = (80 - 64) // 2
    offset_y = 80 - 64  # bottom-align
    canvas.paste(sprite_64, (offset_x, offset_y), sprite_64)
    return canvas


def make_sprite_sheet(frame_80):
    """Duplicate an 80x80 frame into a 160x80 sprite sheet (frame 0 + frame 1)."""
    sheet = Image.new('RGBA', (160, 80), (0, 0, 0, 0))
    sheet.paste(frame_80, (0, 0), frame_80)
    sheet.paste(frame_80, (80, 0), frame_80)
    return sheet


def build_shared_palette(front_rgba, back_rgba):
    """Build a shared 16-color palette from both front and back sprites.

    Collects only opaque pixels from both images, quantizes to 15 colors,
    and places the NDS transparent marker at index 0.
    """
    # Collect all opaque pixel colors from both images
    opaque_pixels = []
    for img in [front_rgba, back_rgba]:
        alpha = img.split()[3]
        for y in range(img.height):
            for x in range(img.width):
                if alpha.getpixel((x, y)) >= 128:
                    r, g, b, _ = img.getpixel((x, y))
                    opaque_pixels.append((r, g, b))

    if not opaque_pixels:
        # Fallback: all transparent
        return [TRANSPARENT_COLOR] + [(0, 0, 0)] * 15

    # Build a small image of just the opaque pixels for quantization
    n = len(opaque_pixels)
    quant_img = Image.new('RGB', (n, 1))
    for i, (r, g, b) in enumerate(opaque_pixels):
        quant_img.putpixel((i, 0), (r, g, b))

    quantized = quant_img.quantize(colors=15, method=Image.Quantize.MEDIANCUT)
    pal_data = quantized.getpalette()

    palette = [TRANSPARENT_COLOR]
    for i in range(15):
        color = (pal_data[i * 3], pal_data[i * 3 + 1], pal_data[i * 3 + 2])
        # Avoid any quantized color colliding with the transparent marker
        if color == TRANSPARENT_COLOR:
            color = (0, 127, 0)
        palette.append(color)

    while len(palette) < 16:
        palette.append((0, 0, 0))

    return palette


def map_pixels_to_palette(img_rgba, palette):
    """Map an RGBA image's pixels to the nearest color in palette.

    Transparent pixels (alpha < 128) map to index 0.
    Opaque pixels map to the closest palette entry (indices 1-15).
    Returns a 2D list of palette indices.
    """
    alpha = img_rgba.split()[3]
    result_pixels = []
    # Pre-compute opaque palette entries for distance matching
    opaque_palette = palette[1:]  # indices 1..15

    for y in range(img_rgba.height):
        row = []
        for x in range(img_rgba.width):
            if alpha.getpixel((x, y)) < 128:
                row.append(0)
            else:
                r, g, b, _ = img_rgba.getpixel((x, y))
                # Find closest palette color
                best_idx = 0
                best_dist = float('inf')
                for i, (pr, pg, pb) in enumerate(opaque_palette):
                    dist = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
                    if dist < best_dist:
                        best_dist = dist
                        best_idx = i
                row.append(best_idx + 1)  # +1 because index 0 is transparent
        result_pixels.append(row)

    return result_pixels


def write_4bit_png(filename, width, height, pixels, palette):
    """Write a 4-bit indexed PNG file."""
    # Build PNG manually for 4-bit depth
    def chunk(chunk_type, data):
        c = chunk_type + data
        crc = struct.pack('>I', zlib.crc32(c) & 0xffffffff)
        return struct.pack('>I', len(data)) + c + crc

    signature = b'\x89PNG\r\n\x1a\n'

    # IHDR
    ihdr_data = struct.pack('>IIBBBBB', width, height, 4, 3, 0, 0, 0)
    ihdr = chunk(b'IHDR', ihdr_data)

    # PLTE
    plte_data = b''
    for r, g, b in palette:
        plte_data += struct.pack('BBB', r, g, b)
    plte = chunk(b'PLTE', plte_data)

    # IDAT - pack pixels as 4-bit
    raw_data = b''
    for row in pixels:
        raw_data += b'\x00'  # filter type: none
        for x in range(0, width, 2):
            hi = row[x] & 0x0F
            lo = row[x + 1] & 0x0F if x + 1 < width else 0
            raw_data += struct.pack('B', (hi << 4) | lo)

    compressed = zlib.compress(raw_data)
    idat = chunk(b'IDAT', compressed)

    # IEND
    iend = chunk(b'IEND', b'')

    with open(filename, 'wb') as f:
        f.write(signature + ihdr + plte + idat + iend)


def write_jasc_pal(filename, palette):
    """Write a JASC-PAL palette file with CRLF line endings."""
    lines = ['JASC-PAL', '0100', '16']
    for r, g, b in palette:
        lines.append(f'{r} {g} {b}')
    with open(filename, 'wb') as f:
        f.write('\r\n'.join(lines).encode('ascii'))
        f.write(b'\r\n')


def process_species(species):
    """Process front and back sprites for one species."""
    front_path = os.path.join(SPRITE_DIR, 'front', f'mega_{species}.png')
    back_path = os.path.join(SPRITE_DIR, 'back', f'mega_{species}.png')
    output_dir = os.path.join(PROJECT_ROOT, 'res', 'pokemon', species, 'forms', 'mega')

    print(f'Processing {species}...')

    # Load sprites
    front_img = Image.open(front_path)
    back_img = Image.open(back_path)

    print(f'  Front: {front_img.size} {front_img.mode}')
    print(f'  Back: {back_img.size} {back_img.mode}')

    # Extract single frames
    front_64 = extract_front_sprite(front_img)
    back_64 = extract_back_sprite(back_img)

    # Convert to RGBA for processing
    front_64 = front_64.convert('RGBA')
    back_64 = back_64.convert('RGBA')

    # Place in 80x80 canvases
    front_80 = place_in_80x80(front_64)
    back_80 = place_in_80x80(back_64)

    # Build shared palette from both sprites
    palette = build_shared_palette(front_80, back_80)

    # Create separate 160x80 sheets: each duplicates its frame for both halves
    front_sheet = make_sprite_sheet(front_80)
    back_sheet = make_sprite_sheet(back_80)

    # Map pixels to the shared palette
    front_pixels = map_pixels_to_palette(front_sheet, palette)
    back_pixels = map_pixels_to_palette(back_sheet, palette)

    # Write separate front.png and back.png
    front_out = os.path.join(output_dir, 'front.png')
    back_out = os.path.join(output_dir, 'back.png')
    write_4bit_png(front_out, 160, 80, front_pixels, palette)
    write_4bit_png(back_out, 160, 80, back_pixels, palette)

    # Write palette files
    normal_pal = os.path.join(output_dir, 'normal.pal')
    write_jasc_pal(normal_pal, palette)

    # Create a shiny palette variant (shift hues)
    shiny_palette = create_shiny_palette(palette)
    shiny_pal = os.path.join(output_dir, 'shiny.pal')
    write_jasc_pal(shiny_pal, shiny_palette)

    print(f'  Output: {front_out}')
    print(f'  Output: {back_out}')
    print(f'  Palette colors: {len(palette)}')
    print(f'  Done!')


def create_shiny_palette(palette):
    """Create a shiny variant by rotating hues."""
    import colorsys
    shiny = [palette[0]]  # keep transparent color
    for i in range(1, len(palette)):
        r, g, b = palette[i]
        h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
        # Rotate hue by ~180 degrees and slightly increase saturation
        h = (h + 0.5) % 1.0
        s = min(1.0, s * 1.2)
        r2, g2, b2 = colorsys.hsv_to_rgb(h, s, v)
        shiny.append((int(r2*255), int(g2*255), int(b2*255)))
    return shiny


if __name__ == '__main__':
    for species in SPECIES:
        try:
            process_species(species)
        except Exception as e:
            print(f'ERROR processing {species}: {e}')
            import traceback
            traceback.print_exc()
