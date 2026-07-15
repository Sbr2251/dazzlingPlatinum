#!/usr/bin/env python3
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
for species in ("torterra", "infernape", "empoleon"):
    for face in ("front", "back"):
        for label, path in (
            ("base", ROOT / "res" / "pokemon" / species / f"male_{face}.png"),
            ("mega", ROOT / "res" / "pokemon" / species / "forms" / "mega" / f"{face}.png"),
        ):
            image = Image.open(path)
            background = image.getpixel((0, 0))
            bounds = []
            for frame_number in range(2):
                frame = image.crop((frame_number * 80, 0, (frame_number + 1) * 80, 80))
                mask = frame.point(lambda value: 0 if value == background else 255, mode="1")
                bounds.append(mask.getbbox())
            print(f"{species:9} {face:5} {label:4}: {bounds}")
