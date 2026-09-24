#!/usr/bin/env python3
"""Restore the Mega Gengar battle sprites.

The sprites from commit 2bb0d86b2 were a clean 16-colour Mega Gengar. A later
"direction fix" swapped the front for a different sprite whose background was
palette index 1 (a green box), and edited the palette so the back rendered as
noise. This restores the 2bb0d86b2 art and palettes, then:

  - mirrors both front frames so Gengar faces left like other Gen 4 fronts
    (its face sat 5-9 px right of centre);
  - lifts the darkest purples a little so the mostly index-2 back still reads
    against dark battle backgrounds. The shiny ramp is already light grey, so
    only the normal palette changes.

The .png.key files are left alone; they are arbitrary encryption seeds.

Run with a Python that has Pillow, e.g. ~/.venvs/desmume/bin/python.
"""

import io
import subprocess
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
MEGA_DIR = ROOT / "res/pokemon/gengar/forms/mega"
SOURCE_REV = "2bb0d86b2"
FRAME_SIZE = 80
FRAME_COUNT = 2
TRANSPARENT_RGB = (0, 128, 0)

# index: (old, new). Old values are checked so a changed source fails loudly.
NORMAL_LIFT = {
    1: ((32, 16, 48), (40, 24, 64)),
    2: ((56, 32, 80), (72, 40, 96)),
    3: ((80, 48, 112), (96, 56, 128)),
    4: ((112, 64, 144), (120, 72, 152)),
    14: ((64, 24, 64), (80, 32, 80)),
    15: ((96, 40, 96), (104, 48, 104)),
}


def git_show(name: str) -> bytes:
    path = f"res/pokemon/gengar/forms/mega/{name}"
    return subprocess.check_output(["git", "show", f"{SOURCE_REV}:{path}"], cwd=ROOT)


def read_jasc(data: bytes) -> list[tuple[int, int, int]]:
    lines = [line for line in data.decode("ascii").splitlines()[3:] if line.strip()]
    colors = [tuple(int(v) for v in line.split()) for line in lines]
    assert len(colors) == 16, len(colors)
    return colors


def write_jasc(path: Path, colors: list[tuple[int, int, int]]) -> None:
    lines = ["JASC-PAL", "0100", "16"] + [f"{r} {g} {b}" for r, g, b in colors]
    path.write_bytes(("\r\n".join(lines) + "\r\n").encode("ascii"))


def load_indices(data: bytes) -> Image.Image:
    im = Image.open(io.BytesIO(data))
    assert im.mode == "P" and im.size == (FRAME_SIZE * FRAME_COUNT, FRAME_SIZE), (im.mode, im.size)
    # Image.point() on a P image maps the palette, so read the raw indices.
    return Image.frombytes("L", im.size, im.tobytes())


def mirror_frames(indices: Image.Image) -> Image.Image:
    out = indices.copy()
    for frame in range(FRAME_COUNT):
        box = (frame * FRAME_SIZE, 0, (frame + 1) * FRAME_SIZE, FRAME_SIZE)
        out.paste(indices.crop(box).transpose(Image.Transpose.FLIP_LEFT_RIGHT), box[:2])
    return out


def save_indexed(path: Path, indices: Image.Image, colors: list[tuple[int, int, int]]) -> None:
    im = Image.frombytes("P", indices.size, indices.tobytes())
    im.putpalette([c for rgb in colors for c in rgb])
    im.save(path, bits=4, optimize=False)


def main() -> None:
    normal = read_jasc(git_show("normal.pal"))
    shiny = read_jasc(git_show("shiny.pal"))
    assert normal[0] == TRANSPARENT_RGB and shiny[0] == TRANSPARENT_RGB

    for index, (old, new) in NORMAL_LIFT.items():
        assert normal[index] == old, (index, normal[index])
        normal[index] = new

    front = mirror_frames(load_indices(git_show("front.png")))
    back = load_indices(git_show("back.png"))

    save_indexed(MEGA_DIR / "front.png", front, normal)
    save_indexed(MEGA_DIR / "back.png", back, normal)
    write_jasc(MEGA_DIR / "normal.pal", normal)
    write_jasc(MEGA_DIR / "shiny.pal", shiny)
    print(f"Restored Mega Gengar from {SOURCE_REV} into {MEGA_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
