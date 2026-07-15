#!/usr/bin/env python3
"""Validate mechanics and resource wiring for the three Sinnoh starter Megas."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEGAS = {
    "torterra": {
        "species": "SPECIES_TORTERRA",
        "form": "MEGA_FORM_TORTERRA",
        "stone": "ITEM_TORTERRITE",
        "ability": "ABILITY_THICK_FAT",
        "types": ("TYPE_GRASS", "TYPE_GROUND"),
        "stats": (95, 149, 145, 85, 115, 36),
        "resources": (276, 277, 282, 283),
        "item_id": 120,
        "script": 7335,
        "flag": "FLAG_UNK_0x0543",
    },
    "infernape": {
        "species": "SPECIES_INFERNAPE",
        "form": "MEGA_FORM_INFERNAPE",
        "stone": "ITEM_INFERNAPITE",
        "ability": "ABILITY_ADAPTABILITY",
        "types": ("TYPE_FIRE", "TYPE_FIGHTING"),
        "stats": (76, 134, 81, 134, 81, 128),
        "resources": (278, 279, 284, 285),
        "item_id": 121,
        "script": 7336,
        "flag": "FLAG_UNK_0x0544",
    },
    "empoleon": {
        "species": "SPECIES_EMPOLEON",
        "form": "MEGA_FORM_EMPOLEON",
        "stone": "ITEM_EMPOLEONITE",
        "ability": "ABILITY_FILTER",
        "types": ("TYPE_WATER", "TYPE_STEEL"),
        "stats": (84, 106, 118, 141, 121, 60),
        "resources": (280, 281, 286, 287),
        "item_id": 122,
        "script": 7337,
        "flag": "FLAG_UNK_0x0545",
    },
}


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def main() -> None:
    failures: list[str] = []
    mega_source = (ROOT / "src/pokemon_mega_data.c").read_text()
    pokemon_source = (ROOT / "src/pokemon.c").read_text()
    forms = (ROOT / "include/constants/forms.h").read_text()
    items = (ROOT / "generated/items.txt").read_text().splitlines()
    abilities = set((ROOT / "generated/abilities.txt").read_text().splitlines())
    types = set((ROOT / "generated/pokemon_types.txt").read_text().splitlines())
    scripts = (ROOT / "res/field/scripts/scripts_unk_0404.s").read_text()
    events = json.loads((ROOT / "res/field/events/events_route_206.json").read_text())
    object_events = {event["id"]: event for event in events["object_events"]}

    rows: list[str] = []
    for species, expected in MEGAS.items():
        base = json.loads((ROOT / f"res/pokemon/{species}/data.json").read_text())
        base_stats = base["base_stats"]
        base_ordered = (
            base_stats["hp"],
            base_stats["attack"],
            base_stats["defense"],
            base_stats["special_attack"],
            base_stats["special_defense"],
            base_stats["speed"],
        )
        mega_stats = expected["stats"]
        base_bst = sum(base_ordered)
        mega_bst = sum(mega_stats)
        require(mega_bst - base_bst == 100, f"{species}: Mega spread adds {mega_bst - base_bst}, expected 100", failures)
        require(expected["ability"] in abilities, f"{species}: missing existing ability {expected['ability']}", failures)
        require(all(type_name in types for type_name in expected["types"]), f"{species}: missing type identifier", failures)
        require(items[expected["item_id"]] == expected["stone"], f"{species}: stone is not item ID {expected['item_id']}", failures)
        require(f"#define {expected['form']} 1" in forms, f"{species}: missing form constant", failures)

        block_pattern = re.compile(
            rf"\.baseSpecies = {expected['species']},.*?"
            rf"\.megaForm = {expected['form']},.*?"
            rf"\.requiredItem = {expected['stone']},.*?"
            rf"\.baseStats = \{{{', '.join(map(str, mega_stats))}\}},.*?"
            rf"\.ability = {expected['ability']},.*?"
            rf"\.type1 = {expected['types'][0]},.*?"
            rf"\.type2 = {expected['types'][1]},",
            re.DOTALL,
        )
        require(bool(block_pattern.search(mega_source)), f"{species}: Mega data block differs from approved mechanics", failures)

        back, front, normal, shiny = expected["resources"]
        manifest = (ROOT / f"res/pokemon/{species}/meson.build").read_text()
        expected_manifest = {
            back: "forms/mega/back.png",
            front: "forms/mega/front.png",
            normal: "forms/mega/normal.pal",
            shiny: "forms/mega/shiny.pal",
        }
        for index, relative in expected_manifest.items():
            require(f"'{index}': files('{relative}')" in manifest, f"{species}: archive index {index} not mapped to {relative}", failures)
        require(f"spriteTemplate->character = {back} + (face / 2);" in pokemon_source, f"{species}: sprite routing missing", failures)
        require(f"spriteTemplate->palette = {normal} + shiny;" in pokemon_source, f"{species}: palette routing missing", failures)

        event_id = f"ROUTE_206_POKEBALL_{expected['stone'].removeprefix('ITEM_')}"
        event = object_events.get(event_id)
        require(event is not None, f"{species}: Route 206 event missing", failures)
        if event:
            require(event["script"] == expected["script"], f"{species}: pickup script ID differs", failures)
            require(event["hidden_flag"] == expected["flag"], f"{species}: pickup flag differs", failures)
        require(f"SetVar VAR_0x8008, {expected['stone']}" in scripts, f"{species}: pickup script item missing", failures)

        rows.append(
            f"{species:9} BST {base_bst}->{mega_bst} (+{mega_bst - base_bst}) "
            f"ability={expected['ability']} types={'/'.join(expected['types'])} "
            f"stone={expected['stone']}({expected['item_id']}) resources={expected['resources']}"
        )

    require("const int sMegaEvolutionTableSize = 10;" in mega_source, "Mega table size is not 10", failures)
    require("'--sprite-entries', '174'" in (ROOT / "res/pokemon/meson.build").read_text(), "Archive sprite count is not 174", failures)
    require("'--palette-entries', '114'" in (ROOT / "res/pokemon/meson.build").read_text(), "Archive palette count is not 114", failures)

    print("\n".join(rows))
    if failures:
        print("\nFAILURES:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)
    print("\nAll Mega Sinnoh starter mechanics and integration checks passed.")


if __name__ == "__main__":
    main()
