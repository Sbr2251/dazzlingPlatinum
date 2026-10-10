#!/usr/bin/env python3
"""Adds the cries of the species after Hydreigon (gen5_species.py's SPECIES) to the SDAT.

A cry plays SEQ_PV with bank = species ID (Sound_PlayPokemonCry), and the Pokedex reads the wave
archive with ID = species ID, so each species needs BANK_* and WAVE_ARC_* info entries at its own
species ID (497 onward are free up to BANK_BASIC = 700). For each species this writes:

    res/sound/pl_sound_data/Files/WAVARC/WAVE_ARC_PV_<NAME>/00.swav   PCM8, the source's rate
    res/sound/pl_sound_data/Files/BANK/BANK_PV_<NAME>.txt             one Single instrument, like PV494

and adds the entries to InfoBlock.json (at the species ID), FileBlock.json, res/sound/meson.build and
generated/sdat.txt. Text edits only, so the rest of those files keeps its formatting. Running it
again changes nothing.

Source: the Black/White cries in pokeemerald-expansion (sound/direct_sound_samples/cries/<name>.wav,
8-bit mono, 13379 Hz), cached in ~/.cache/gen5_sprites/expansion/<name>/cry.wav. A species without
one gets the cry named in SUBSTITUTE_CRIES (an existing PV wave archive) instead.
"""

import ast
import hashlib
import os
import struct
import sys
import urllib.request
import wave

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SDAT = os.path.join(ROOT, "res", "sound", "pl_sound_data")
CACHE = os.path.expanduser("~/.cache/gen5_sprites/expansion")
EXPANSION = "https://raw.githubusercontent.com/rh-hideout/pokeemerald-expansion/master"
ARM7_CLOCK = 16756991
BANK_TEXT = "0, Single, 0, 0, 60, 127, 127, 127, 127, 64\r\nUnused, 0, 0\r\n"  # CRLF, as .gitattributes checks res/**/*.txt out
SUBSTITUTE_CRIES = {}  # species -> existing WAVE_ARC_* directory, when no B/W cry is available
LAST_OLD = 496         # BANK_PV496 / WAVE_ARC_PV496 (Hydreigon) are the entries before ours


def species_list():
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "gen5_species.py")).read()
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == "SPECIES":
            return [name for name, _, _ in ast.literal_eval(node.value)]
    raise SystemExit("SPECIES not found in gen5_species.py")


def species_ids():
    with open(os.path.join(ROOT, "generated", "species.txt")) as f:
        names = [ln.strip() for ln in f if ln.strip()]
    return {n[len("SPECIES_"):].lower(): i for i, n in enumerate(names)}


def fetch_cry(name):
    path = os.path.join(CACHE, name, "cry.wav")
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        url = f"{EXPANSION}/sound/direct_sound_samples/cries/{name}.wav"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60) as r:
                data = r.read()
        except urllib.error.HTTPError:
            return None
        with open(path, "wb") as f:
            f.write(data)
    return path


def swav_from_wav(path):
    w = wave.open(path)
    if w.getnchannels() != 1 or w.getsampwidth() != 1:
        raise SystemExit(f"{path}: expected 8-bit mono")
    rate = w.getframerate()
    pcm = bytes(b ^ 0x80 for b in w.readframes(w.getnframes()))  # unsigned -> signed PCM8
    pcm += bytes((-len(pcm)) % 4)
    info = struct.pack("<BBHHHI", 0, 0, rate, ARM7_CLOCK // rate, 0, len(pcm) // 4)
    data = b"DATA" + struct.pack("<I", 8 + len(info) + len(pcm)) + info + pcm
    return b"SWAV" + struct.pack("<HHIHH", 0xFEFF, 0x0100, 16 + len(data), 16, 1) + data, rate, len(pcm)


def insert_after_line(path, anchor, new_lines):
    with open(path) as f:
        lines = f.read().split("\n")
    todo = [ln for ln in new_lines if ln not in lines]
    if not todo:
        return False
    i = lines.index(anchor)
    while i + 1 < len(lines) and lines[i + 1] in new_lines:
        i += 1
    lines[i + 1:i + 1] = todo
    with open(path, "w") as f:
        f.write("\n".join(lines))
    return True


def info_block(entries):
    """Fills the empty {"name": ""} slots after the PV496 entries of bankInfo and wavarcInfo."""
    path = os.path.join(SDAT, "InfoBlock.json")
    text = open(path).read()
    for section, anchor, render in (
        ("bankInfo", f'"name": "BANK_PV{LAST_OLD}"',
         lambda e: ('        {\n'
                    f'            "name": "{e["bank"]}",\n'
                    f'            "fileName": "{e["bank"]}.sbnk",\n'
                    '            "unkA": 0,\n'
                    '            "wa": [\n'
                    f'                "{e["wavarc"]}",\n'
                    '                "",\n'
                    '                "",\n'
                    '                ""]\n'
                    '        },')),
        ("wavarcInfo", f'"name": "WAVE_ARC_PV{LAST_OLD}"',
         lambda e: ('        {\n'
                    f'            "name": "{e["wavarc"]}",\n'
                    f'            "fileName": "{e["wavarc"]}.swar",\n'
                    '            "unkA": 0\n'
                    '        },')),
    ):
        start = text.index(f'"{section}": [')
        pos = text.index(anchor, start)
        pos = text.index("\n        },\n", pos) + len("\n        },\n")
        for e in entries:
            key = e["bank"] if section == "bankInfo" else e["wavarc"]
            if f'"name": "{key}"' in text:
                pos = text.index("\n        },\n", text.index(f'"name": "{key}"')) + len("\n        },\n")
                continue
            empty = '        {"name": ""},\n'
            if not text.startswith(empty, pos):
                raise SystemExit(f"{section}: no empty slot for {key} at species {e['id']}")
            block = render(e) + "\n"
            text = text[:pos] + block + text[pos + len(empty):]
            pos += len(block)
    with open(path, "w") as f:
        f.write(text)


def file_block(entries):
    path = os.path.join(SDAT, "FileBlock.json")
    text = open(path).read()
    for kind, ext, key in (("BANK", "sbnk", "bank"), ("WAVARC", "swar", "wavarc")):
        last = text.rindex(f'"type": "{kind}"')
        pos = text.index("\n        },\n", last) + len("\n        },\n")
        for e in entries:
            fname = f'{e[key]}.{ext}'
            if f'"name": "{fname}"' in text:
                continue
            block = ('        {\n'
                     f'            "name": "{fname}",\n'
                     f'            "type": "{kind}",\n'
                     f'            "MD5": "{e["md5_" + key]}"' + (',\n            "subFile": [\n                "00.swav"\n            ]\n'
                                                                    if kind == "WAVARC" else "\n") +
                     '        },\n')
            text = text[:pos] + block + text[pos:]
            pos += len(block)
    with open(path, "w") as f:
        f.write(text)


def main():
    ids = species_ids()
    entries = []
    for name in species_list():
        if name not in ids:
            raise SystemExit(f"{name} is not in generated/species.txt")
        e = {"name": name, "id": ids[name], "bank": f"BANK_PV_{name.upper()}", "wavarc": f"WAVE_ARC_PV_{name.upper()}"}
        wavdir = os.path.join(SDAT, "Files", "WAVARC", e["wavarc"])
        os.makedirs(wavdir, exist_ok=True)
        src = fetch_cry(name)
        if src:
            swav, rate, n = swav_from_wav(src)
            e["source"] = f"B/W cry ({rate} Hz, {n} samples)"
        else:
            sub = SUBSTITUTE_CRIES[name]
            swav = open(os.path.join(SDAT, "Files", "WAVARC", sub, "00.swav"), "rb").read()
            e["source"] = f"substitute: {sub}"
        with open(os.path.join(wavdir, "00.swav"), "wb") as f:
            f.write(swav)
        with open(os.path.join(SDAT, "Files", "BANK", e["bank"] + ".txt"), "w", newline="") as f:
            f.write(BANK_TEXT)
        e["md5_wavarc"] = hashlib.md5(swav).hexdigest()
        e["md5_bank"] = "0b957e3b8d070b82138ba5e79ac59bca"  # every PV bank compiles to the same SBNK
        entries.append(e)
    entries.sort(key=lambda e: e["id"])
    if [e["id"] for e in entries] != list(range(LAST_OLD + 1, LAST_OLD + 1 + len(entries))):
        raise SystemExit("the new species must follow Hydreigon in species.txt, in SPECIES order")

    info_block(entries)
    file_block(entries)
    meson = os.path.join(ROOT, "res", "sound", "meson.build")
    insert_after_line(meson, f"    bank_folder / 'BANK_PV{LAST_OLD}.txt',",
                      [f"    bank_folder / '{e['bank']}.txt'," for e in entries])
    insert_after_line(meson, f"    wavarc_folder / 'WAVE_ARC_PV{LAST_OLD}' / '00.swav',",
                      [f"    wavarc_folder / '{e['wavarc']}' / '00.swav'," for e in entries])
    sdat_txt = os.path.join(ROOT, "generated", "sdat.txt")
    insert_after_line(sdat_txt, f"WAVE_ARC_PV{LAST_OLD}", [e["wavarc"] for e in entries])
    insert_after_line(sdat_txt, f"BANK_PV{LAST_OLD}", [e["bank"] for e in entries])
    for e in entries:
        print(f"{e['id']} {e['name']}: {e['source']}")


if __name__ == "__main__":
    sys.exit(main())
