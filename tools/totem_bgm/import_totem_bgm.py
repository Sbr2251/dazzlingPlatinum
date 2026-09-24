"""Imports the Totem battle theme (SEQ_PL_BA_TOTEM) from Pokemon HeartGold/SoulSilver.

Usage: ~/.venvs/desmume/bin/python tools/totem_bgm/import_totem_bgm.py [gs_sound_data.sdat]
(needs mido; safe to re-run). Without an argument the HGSS sound archive is downloaded from the pret
decompilation (github.com/pret/pokeheartgold, files/data/sound/gs_sound_data.sdat).

The theme is HGSS's "Battle! Raikou" (SEQ_GS_VS_RAIKOU), used as is: HGSS runs the same sound engine, and
SDATTool's MIDI form of the sequence rebuilds it byte for byte. Its instruments come from HGSS's
BANK_BGM_BATTLE6, trimmed to what the song plays:
  - Files/BANK/BANK_BGM_TOTEM.txt keeps only the programs the song uses (the rest are NULL)
  - samples identical to one in Platinum's WAVE_ARC_BASIC point there, since that archive stays loaded
  - every other sample the song can reach goes into Files/WAVARC/WAVE_ARC_BGM_TOTEM. Key/drum regions the
    song never plays borrow a sample from a region it does play, so they cost nothing
The bank and wave archive entries in InfoBlock.json and generated/sdat.txt are maintained by hand; this
script regenerates the files, their FileBlock.json entries and their res/sound/meson.build lines.
"""
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request

import mido

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
SDAT_URL = "https://raw.githubusercontent.com/pret/pokeheartgold/master/files/data/sound/gs_sound_data.sdat"
SDATTOOL = os.path.join(ROOT, "subprojects/SDATTool/SDATTool")
SOUND = os.path.join(ROOT, "res/sound")
DATA = os.path.join(SOUND, "pl_sound_data")
FILES = os.path.join(DATA, "Files")

SRC_SEQ = "SEQ_GS_VS_RAIKOU"
SRC_BANK = "BANK_BGM_BATTLE6"
SRC_WAVE_ARCS = ["WAVE_ARC_BASIC", "WAVE_ARC_BGM_BATTLE6"]  # the bank's wa slots 0 and 1
SEQ = "SEQ_PL_BA_TOTEM"
BANK = "BANK_BGM_TOTEM"
WAVE_ARC = "WAVE_ARC_BGM_TOTEM"
WA_BASIC, WA_TOTEM = 0, 1  # BANK_BGM_TOTEM's wa slots in InfoBlock.json


def md5(path):
    return hashlib.md5(open(path, "rb").read()).hexdigest()


def unpack(sdat, out):
    subprocess.run([sys.executable, "__main__.py", "-u", os.path.abspath(sdat), out], cwd=SDATTOOL, check=True,
                   stdout=subprocess.DEVNULL)


def played_notes(mid):
    """Returns {program: set of keys it plays}."""
    notes = {}
    for track in mido.MidiFile(mid).tracks:
        program = None
        for msg in track:
            if msg.type == "program_change":
                program = msg.program
            elif msg.type == "note_on" and msg.velocity:
                notes.setdefault(program, set()).add(msg.note)
    return notes


def read_bank(path):
    """Returns {program: (header fields, [region fields])}, resolving SameAsAbove and dropping Unused data."""
    insts = {}
    last = None
    for line in open(path).read().splitlines():
        if line.startswith("\t"):
            last[1].append(line.strip().split(", "))
            continue
        fields = line.split(", ")
        if fields[0] == "Unused":
            continue
        if fields[1] == "SameAsAbove":
            insts[int(fields[0])] = last
            continue
        last = (fields, [])
        insts[int(fields[0])] = last
    return insts


def reachable(header, regions, keys):
    """Yields (index, region, reachable) for each region of a Keysplit or Drums instrument."""
    if header[1] == "Keysplit":
        low = 0
        for i, top in enumerate(int(k) for k in header[2:2 + len(regions)]):
            yield i, regions[i], any(low <= k <= top for k in keys)
            low = top + 1
    else:
        low = int(header[2])
        for i, region in enumerate(regions):
            yield i, region, low + i in keys


def build_bank(insts, notes, src_arcs):
    """Returns the bank text and the list of sample paths for WAVE_ARC_BGM_TOTEM."""
    basic = {md5(p): int(os.path.basename(p)[:-5], 16)
             for p in glob.glob(os.path.join(FILES, "WAVARC/WAVE_ARC_BASIC/*.swav"))}
    samples = []

    def remap(swav, wa):
        path = os.path.join(src_arcs[int(wa)], f"{int(swav):02X}.swav")
        digest = md5(path)
        if digest in basic:
            return basic[digest], WA_BASIC
        if path not in samples:
            samples.append(path)
        return samples.index(path), WA_TOTEM

    lines = []
    for program in range(max(notes) + 1):
        if program not in notes:
            lines.append(f"{program}, NULL")
            continue
        header, regions = insts[program]
        header = list(header)
        header[0] = str(program)
        if header[1] == "Single":
            header[2], header[3] = map(str, remap(header[2], header[3]))
        lines.append(", ".join(header))
        if not regions:
            continue
        hit = [(i, r) for i, r, ok in reachable(header, regions, notes[program]) if ok]
        regions = [list(r) for r in regions]
        for i, region, ok in reachable(header, regions, notes[program]):
            if region[0] != "1":  # PSG regions have no sample
                continue
            if not ok:
                donor = min(hit, key=lambda h: abs(h[0] - i))[1]
                region[1], region[2] = donor[1], donor[2]
            region[1], region[2] = map(str, remap(region[1], region[2]))
        lines += ["\t" + ", ".join(r) for r in regions]
    return "\n".join(lines) + "\n", samples


def update_file_block(samples):
    path = os.path.join(DATA, "FileBlock.json")
    block = json.load(open(path))
    files = block["file"]
    names = [f["name"] for f in files]

    def upsert(entry, after):
        if entry["name"] in names:
            files[names.index(entry["name"])] = entry
        else:
            files.insert(names.index(after) + 1, entry)
            names.insert(names.index(after) + 1, entry["name"])

    upsert({"name": f"{SEQ}.sseq", "type": "SEQ", "MD5": md5(os.path.join(FILES, "SEQ", f"{SEQ}.mid"))},
           f"{SEQ}.sseq")
    upsert({"name": f"{BANK}.sbnk", "type": "BANK", "MD5": md5(os.path.join(FILES, "BANK", f"{BANK}.txt"))},
           "BANK_BGM_DEMO01.sbnk")
    digest = hashlib.md5(b"".join(open(p, "rb").read() for p in samples)).hexdigest()
    upsert({"name": f"{WAVE_ARC}.swar", "type": "WAVARC", "MD5": digest,
            "subFile": [f"{i:02X}.swav" for i in range(len(samples))]}, "WAVE_ARC_BGM_DEMO01.swar")
    open(path, "w").write(json.dumps(block, indent=4))


def update_meson(count):
    path = os.path.join(SOUND, "meson.build")
    lines = [l for l in open(path).read().splitlines() if BANK not in l and WAVE_ARC not in l]
    bank_at = lines.index("    bank_folder / 'BANK_BGM_DEMO01.txt',") + 1
    lines.insert(bank_at, f"    bank_folder / '{BANK}.txt',")
    wave_at = max(i for i, l in enumerate(lines) if "'WAVE_ARC_BGM_DEMO01' /" in l) + 1
    lines[wave_at:wave_at] = [f"    wavarc_folder / '{WAVE_ARC}' / '{i:02X}.swav'," for i in range(count)]
    open(path, "w").write("\n".join(lines) + "\n")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        sdat = sys.argv[1] if len(sys.argv) > 1 else os.path.join(tmp, "gs_sound_data.sdat")
        if len(sys.argv) <= 1:
            urllib.request.urlretrieve(SDAT_URL, sdat)
        src = os.path.join(tmp, "gs")
        unpack(sdat, src)
        src_files = os.path.join(src, "Files")

        mid = os.path.join(src_files, "SEQ", f"{SRC_SEQ}.mid")
        shutil.copyfile(mid, os.path.join(FILES, "SEQ", f"{SEQ}.mid"))

        src_arcs = [os.path.join(src_files, "WAVARC", a) for a in SRC_WAVE_ARCS]
        insts = read_bank(os.path.join(src_files, "BANK", f"{SRC_BANK}.txt"))
        text, samples = build_bank(insts, played_notes(mid), src_arcs)
        open(os.path.join(FILES, "BANK", f"{BANK}.txt"), "w").write(text)

        out = os.path.join(FILES, "WAVARC", WAVE_ARC)
        shutil.rmtree(out, ignore_errors=True)
        os.makedirs(out)
        for i, path in enumerate(samples):
            shutil.copyfile(path, os.path.join(out, f"{i:02X}.swav"))

        update_file_block(samples)
    update_meson(len(samples))
    size = sum(os.path.getsize(p) for p in glob.glob(os.path.join(out, "*.swav")))
    print(f"{SEQ} <- {SRC_SEQ}; {BANK}: {text.count(chr(10))} lines; {WAVE_ARC}: {len(samples)} samples, {size} bytes")


if __name__ == "__main__":
    main()
