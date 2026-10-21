#!/usr/bin/env python3
"""Shadow x offsets of the Gen 5 species this hack added (res/pokemon/<species>/sprite_data.json).

gen5_species.py copied each one's sprite_data.json from a Sinnoh stand-in, so its classic shadow
x_offset (the blob's and the stage-off shadow's x, in pixels from the 80x80 frame's centre) belonged to
the stand-in's Platinum art. This measures the B/W art instead (frame 0 of male_front.png) and writes the
values chosen in CHOSEN.

Measure: the median of four estimates of the body's centre line, each in pixels from x 40: the opaque
bounding box's centre, the opaque pixels' mean x, and the same two over the bottom quarter of the body
(the feet). Over the 475 Platinum species with a shadow it lands within 2.6 px of Platinum's own
x_offset at the median (4.6 px at p75). CHOSEN keeps the stand-in's value where the measure is within
that p75 of it, and was checked by eye on the art (docs/living_battle_stage/shadows.md); a tail, a
hook or a raised arm pulls the estimates, so a few are set by eye between them.

    ~/.venvs/desmume39/bin/python tools/battle_shadow/gen5_x_offsets.py [--write]
Without --write it prints the table: species, stand-in value, measure, chosen.
"""
import json
import pathlib
import statistics
import sys

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[2]
MON = ROOT / "res" / "pokemon"
GEN5 = ["patrat", "watchog", "lillipup", "herdier", "stoutland", "purrloin", "liepard", "pidove", "tranquill",
        "unfezant", "roggenrola", "boldore", "gigalith", "drilbur", "excadrill", "timburr", "gurdurr", "conkeldurr",
        "sewaddle", "swadloon", "leavanny", "woobat", "swoobat", "cottonee", "whimsicott", "sandile", "krokorok",
        "krookodile", "yamask", "cofagrigus", "frillish", "jellicent", "klink", "klang", "klinklang", "elgyem",
        "beheeyem", "litwick", "lampent", "chandelure", "deino", "zweilous", "hydreigon"]
# Changed from the stand-in's value (the rest keep it)
CHOSEN = {
    "patrat": -6,  # stand-in Bidoof 1
    "liepard": -4,  # Purugly -9
    "tranquill": -5,  # Staravia 0
    "unfezant": -6,  # Staraptor -1; the measure (-9) is pulled by the tail
    "drilbur": -2,  # Sandshrew 5
    "leavanny": 1,  # Beautifly -12
    "krokorok": -3,  # Croconaw 0; the measure (-8) is pulled by the tail
    "krookodile": 2,  # Feraligatr 8; the measure (7) is pulled by the tail, the feet straddle 0
    "stoutland": 1,  # Arcanine 5
    "cofagrigus": -2,  # Dusclops -6
    "deino": 4,  # 0 (added before gen5_species.py); the feet stand right of centre
}


def measure(name):
    im = Image.open(MON / name / "male_front.png")
    px = im.load()
    pts = [(x, y) for y in range(80) for x in range(80) if px[x, y] != 0]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    bottom = max(ys)
    band = [x for x, y in pts if y > bottom - max(6, (bottom - min(ys)) // 4)]
    return statistics.median([(min(xs) + max(xs) + 1) / 2 - 40, sum(xs) / len(xs) + 0.5 - 40,
                              (min(band) + max(band) + 1) / 2 - 40, sum(band) / len(band) + 0.5 - 40])


def main():
    write = "--write" in sys.argv
    for name in GEN5:
        path = MON / name / "sprite_data.json"
        data = json.loads(path.read_text())
        cur = data["shadow"]["x_offset"]
        new = CHOSEN.get(name, cur)
        print(f"{name:12s} {cur:4d} {measure(name):6.1f} {new:4d}{'  *' if new != cur else ''}")
        if write and new != cur:
            data["shadow"]["x_offset"] = new
            path.write_text(json.dumps(data, indent=4) + "\n")


if __name__ == "__main__":
    main()
