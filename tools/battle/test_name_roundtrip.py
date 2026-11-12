#!/usr/bin/env python3
"""Round-trip check for the headless name tables.

Offline (default): every species/move/item/ability id in generated/*.txt
must map name -> id -> name through the tables gen_headless_names.py emits,
and must agree with the build's generated enum headers
(build_linux/generated/*.h). This catches a table that drifts from the
build's own lists (e.g. an alias line silently renumbering later entries).

Live (--game, needs build_linux/main): the mega-test save's party must be
named by `state` exactly as tools/dazzling/save_tool.py reads it from the
raw save (this is the Luxray-as-SPECIES_EGG regression), and a start_battle
spec naming boundary species/moves/items/abilities by name must come back
with those same names in the battle state.

  python3 tools/battle/test_name_roundtrip.py [--game] [--build-dir build_linux]
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "dazzling"))
sys.path.insert(0, os.path.join(ROOT, "tools", "battle"))

TABLES = {
    "Species": ("generated/species.txt", "species.h"),
    "Moves": ("generated/moves.txt", "moves.h"),
    "Items": ("generated/items.txt", "items.h"),
    "Abilities": ("generated/abilities.txt", "abilities.h"),
}


def parse_enum_txt(path):
    values, order, nxt = {}, [], 0
    for raw in open(path):
        line = raw.split("#")[0].strip()
        if not line:
            continue
        if "=" in line:
            name, _, rhs = line.partition("=")
            name, rhs = name.strip(), rhs.strip()
            val = int(rhs, 0) if rhs.lstrip("-").isdigit() else values.get(rhs)
            if val is None:
                continue
        else:
            name, val = line, nxt
        values[name] = val
        order.append((name, val))
        nxt = val + 1
    return order


def parse_generated_header(path):
    out = {}
    for name, val in re.findall(r"^\s+([A-Z][A-Z_0-9]+)\s+=\s+(\d+),", open(path).read(), re.M):
        out[name] = int(val)
    return out


def offline(build_dir):
    errs = []
    outdir = tempfile.mkdtemp(prefix="headless-names-")
    subprocess.run(
        [sys.executable, os.path.join(ROOT, "tools/dazzling/gen_headless_names.py"), ROOT, outdir],
        check=True, capture_output=True, text=True,
    )
    generated_c = open(os.path.join(outdir, "headless_names.c")).read()
    for key, (txt_rel, hdr_rel) in TABLES.items():
        m = re.search(r"kHeadless%s\[\] = \{(.*?)\};" % key, generated_c, re.S)
        if not m:
            errs.append(f"{key}: table missing from generated headless_names.c")
            continue
        pairs = [(n, int(v)) for n, v in re.findall(r'\{"([^"]+)",(\d+)\}', m.group(1))]
        # name -> id -> name round-trip, and ids unique
        by_name, by_id = {}, {}
        for name, val in pairs:
            if name in by_name:
                errs.append(f"{key}: duplicate name {name}")
            if val in by_id:
                errs.append(f"{key}: duplicate id {val} ({by_id[val]}, {name})")
            by_name[name] = val
            by_id[val] = name
        for name, val in pairs:
            if by_id.get(by_name.get(name)) != name or by_name.get(by_id.get(val)) != val:
                errs.append(f"{key}: round-trip failed for {name}={val}")
        expected = parse_enum_txt(os.path.join(ROOT, txt_rel))
        if pairs != expected:
            errs.append(f"{key}: generated table != {txt_rel} ({len(pairs)} vs {len(expected)} rows)")
        hdr_path = os.path.join(ROOT, build_dir, "generated", hdr_rel)
        if os.path.exists(hdr_path):
            hdr = parse_generated_header(hdr_path)
            for name, val in expected:
                if hdr.get(name) != val:
                    errs.append(f"{key}: {name} txt={val} header={hdr.get(name)}")
        print(f"{key}: {len(pairs)} names round-trip OK")
    return errs


def live(build_dir):
    import sim as simmod
    import save_tool as st

    errs = []
    save = "/data/repos/dp-wt/pret-sync-notes/saves/raw_sav/dazzlingPlatinum-mega-test.sav"
    data = st.load(save)
    base, _, _ = st.regions(data)[0]
    party_off, count = st.find_party(data, base)
    expected_party = []
    for i in range(count):
        mon = st.Mon(data[party_off + 8 + i * st.MON_SIZE: party_off + 8 + (i + 1) * st.MON_SIZE])
        expected_party.append(st.SPECIES[mon.species])

    runner = simmod.BattleRunner(build_dir, save, seed=7, fast=True)
    try:
        runner.to_field()
        state = runner.state()
        got_party = [m.get("species") for m in state.get("party", [])]
        if got_party != expected_party:
            errs.append(f"state party species {got_party} != save {expected_party}")
        else:
            print(f"state party names OK: {got_party}")

        spec = {
            "battle_type": "wild",
            "seed": 42,
            "player": [{
                "species": "SPECIES_LUXRAY", "level": 50,
                "moves": ["MOVE_TACKLE", "MOVE_SWORDS_DANCE"],
                "held_item": "ITEM_LEFTOVERS", "ability": "ABILITY_INTIMIDATE",
            }, {
                "species": "SPECIES_CHANDELURE", "level": 50,
                "moves": ["MOVE_FLAMETHROWER"],
            }],
            "opponent": [{
                "species": "SPECIES_BULBASAUR", "level": 5,
                "moves": ["MOVE_TACKLE"],
            }],
        }
        # Drive through BattleRunner for a full battle; names are checked in
        # the final battle snapshot it records.
        result = runner.run_battle(spec, policy="first")
        battlers = (result.get("final_battle") or {}).get("battlers", [])
        names = {b.get("battler"): b.get("species") for b in battlers}
        if names.get(1) != "SPECIES_BULBASAUR":
            errs.append(f"opponent battler named {names.get(1)}, expected SPECIES_BULBASAUR")
        if names.get(0) not in ("SPECIES_LUXRAY", "SPECIES_CHANDELURE"):
            errs.append(f"player battler named {names.get(0)}, expected a spec species")
        party_after = [m.get("species") for m in (result.get("party_after") or [])]
        # restore_party defaults to true: the save party (not the spec party)
        # is back afterwards, and its names must round-trip too.
        if party_after != expected_party:
            errs.append(f"party after battle {party_after}, expected restored {expected_party}")
        else:
            print(f"start_battle/state names OK: battlers={names} party_after={party_after}")
    finally:
        runner.close()
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", action="store_true", help="also run the live headless checks (slow)")
    ap.add_argument("--build-dir", default="build_linux")
    args = ap.parse_args()
    errs = offline(args.build_dir)
    if args.game and not errs:
        errs += live(args.build_dir)
    for e in errs:
        print("FAIL", e)
    print("NAME_ROUNDTRIP_OK" if not errs else "NAME_ROUNDTRIP_FAILED")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
