#!/usr/bin/env python3
"""Integrate Mega Torterra, Mega Infernape, and Mega Empoleon.

This script is intentionally deterministic: each replacement asserts that the expected
pre-integration source text exists exactly once, making accidental double-application
or edits against an unexpected tree fail loudly.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(relative_path: str, old: str, new: str) -> None:
    path = ROOT / relative_path
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{relative_path}: expected one match, found {count}")
    path.write_text(text.replace(old, new, 1))


def append_once(relative_path: str, marker: str, addition: str) -> None:
    path = ROOT / relative_path
    text = path.read_text()
    if addition.strip() in text:
        raise RuntimeError(f"{relative_path}: addition already present")
    count = text.count(marker)
    if count != 1:
        raise RuntimeError(f"{relative_path}: expected one marker, found {count}")
    path.write_text(text.replace(marker, addition + marker, 1))


# Species-specific form constants.
replace_once(
    "include/constants/forms.h",
    "#define MEGA_FORM_SCIZOR 1\n#define SCIZOR_FORM_COUNT 2\n",
    "#define MEGA_FORM_SCIZOR 1\n#define SCIZOR_FORM_COUNT 2\n"
    "#define MEGA_FORM_TORTERRA 1\n#define TORTERRA_FORM_COUNT 2\n"
    "#define MEGA_FORM_INFERNAPE 1\n#define INFERNAPE_FORM_COUNT 2\n"
    "#define MEGA_FORM_EMPOLEON 1\n#define EMPOLEON_FORM_COUNT 2\n",
)

# Approved +100 BST spreads and existing Gen IV-compatible abilities.
replace_once(
    "src/pokemon_mega_data.c",
    "    // Mega Scizor\n"
    "    // Base stats: 70 HP, 150 Atk, 140 Def, 65 SpAtk, 100 SpDef, 75 Speed\n"
    "    // Ability: Technician (unchanged)\n"
    "    // Type: Bug/Steel (unchanged)\n"
    "    {\n"
    "        .baseSpecies = SPECIES_SCIZOR,\n"
    "        .megaForm = MEGA_FORM_SCIZOR,\n"
    "        .requiredItem = ITEM_SCIZORITE,\n"
    "        .baseStats = {70, 150, 140, 65, 100, 75},\n"
    "        .ability = ABILITY_TECHNICIAN,\n"
    "        .type1 = TYPE_BUG,\n"
    "        .type2 = TYPE_STEEL,\n"
    "    },\n"
    "};\n\n"
    "// Size of the mega evolution table\n"
    "const int sMegaEvolutionTableSize = 7;\n",
    "    // Mega Scizor\n"
    "    // Base stats: 70 HP, 150 Atk, 140 Def, 65 SpAtk, 100 SpDef, 75 Speed\n"
    "    // Ability: Technician (unchanged)\n"
    "    // Type: Bug/Steel (unchanged)\n"
    "    {\n"
    "        .baseSpecies = SPECIES_SCIZOR,\n"
    "        .megaForm = MEGA_FORM_SCIZOR,\n"
    "        .requiredItem = ITEM_SCIZORITE,\n"
    "        .baseStats = {70, 150, 140, 65, 100, 75},\n"
    "        .ability = ABILITY_TECHNICIAN,\n"
    "        .type1 = TYPE_BUG,\n"
    "        .type2 = TYPE_STEEL,\n"
    "    },\n"
    "    // Mega Torterra\n"
    "    // Base stats: 95 HP, 149 Atk, 145 Def, 85 SpAtk, 115 SpDef, 36 Speed\n"
    "    // Ability: Thick Fat\n"
    "    // Type: Grass/Ground (unchanged)\n"
    "    {\n"
    "        .baseSpecies = SPECIES_TORTERRA,\n"
    "        .megaForm = MEGA_FORM_TORTERRA,\n"
    "        .requiredItem = ITEM_TORTERRITE,\n"
    "        .baseStats = {95, 149, 145, 85, 115, 36},\n"
    "        .ability = ABILITY_THICK_FAT,\n"
    "        .type1 = TYPE_GRASS,\n"
    "        .type2 = TYPE_GROUND,\n"
    "    },\n"
    "    // Mega Infernape\n"
    "    // Base stats: 76 HP, 134 Atk, 81 Def, 134 SpAtk, 81 SpDef, 128 Speed\n"
    "    // Ability: Adaptability\n"
    "    // Type: Fire/Fighting (unchanged)\n"
    "    {\n"
    "        .baseSpecies = SPECIES_INFERNAPE,\n"
    "        .megaForm = MEGA_FORM_INFERNAPE,\n"
    "        .requiredItem = ITEM_INFERNAPITE,\n"
    "        .baseStats = {76, 134, 81, 134, 81, 128},\n"
    "        .ability = ABILITY_ADAPTABILITY,\n"
    "        .type1 = TYPE_FIRE,\n"
    "        .type2 = TYPE_FIGHTING,\n"
    "    },\n"
    "    // Mega Empoleon\n"
    "    // Base stats: 84 HP, 106 Atk, 118 Def, 141 SpAtk, 121 SpDef, 60 Speed\n"
    "    // Ability: Filter\n"
    "    // Type: Water/Steel (unchanged)\n"
    "    {\n"
    "        .baseSpecies = SPECIES_EMPOLEON,\n"
    "        .megaForm = MEGA_FORM_EMPOLEON,\n"
    "        .requiredItem = ITEM_EMPOLEONITE,\n"
    "        .baseStats = {84, 106, 118, 141, 121, 60},\n"
    "        .ability = ABILITY_FILTER,\n"
    "        .type1 = TYPE_WATER,\n"
    "        .type2 = TYPE_STEEL,\n"
    "    },\n"
    "};\n\n"
    "// Size of the mega evolution table\n"
    "const int sMegaEvolutionTableSize = 10;\n",
)

# Form sanitization.
replace_once(
    "src/pokemon.c",
    "    case SPECIES_SCIZOR:\n"
    "        if (monForm > SCIZOR_FORM_COUNT - 1) {\n"
    "            monForm = 0;\n"
    "        }\n"
    "        break;\n"
    "    }\n",
    "    case SPECIES_SCIZOR:\n"
    "        if (monForm > SCIZOR_FORM_COUNT - 1) {\n"
    "            monForm = 0;\n"
    "        }\n"
    "        break;\n"
    "    case SPECIES_TORTERRA:\n"
    "        if (monForm > TORTERRA_FORM_COUNT - 1) {\n"
    "            monForm = 0;\n"
    "        }\n"
    "        break;\n"
    "    case SPECIES_INFERNAPE:\n"
    "        if (monForm > INFERNAPE_FORM_COUNT - 1) {\n"
    "            monForm = 0;\n"
    "        }\n"
    "        break;\n"
    "    case SPECIES_EMPOLEON:\n"
    "        if (monForm > EMPOLEON_FORM_COUNT - 1) {\n"
    "            monForm = 0;\n"
    "        }\n"
    "        break;\n"
    "    }\n",
)

pl_cases = (
    "    case SPECIES_TORTERRA:\n"
    "        if (form == MEGA_FORM_TORTERRA) {\n"
    "            spriteTemplate->narcID = NARC_INDEX_POKETOOL__POKEGRA__PL_OTHERPOKE;\n"
    "            spriteTemplate->character = 276 + (face / 2);\n"
    "            spriteTemplate->palette = 282 + shiny;\n"
    "        } else {\n"
    "            spriteTemplate->narcID = NARC_INDEX_POKETOOL__POKEGRA__PL_POKEGRA;\n"
    "            spriteTemplate->character = species * 6 + face + (gender != GENDER_FEMALE ? 1 : 0);\n"
    "            spriteTemplate->palette = species * 6 + 4 + shiny;\n"
    "        }\n"
    "        break;\n\n"
    "    case SPECIES_INFERNAPE:\n"
    "        if (form == MEGA_FORM_INFERNAPE) {\n"
    "            spriteTemplate->narcID = NARC_INDEX_POKETOOL__POKEGRA__PL_OTHERPOKE;\n"
    "            spriteTemplate->character = 278 + (face / 2);\n"
    "            spriteTemplate->palette = 284 + shiny;\n"
    "        } else {\n"
    "            spriteTemplate->narcID = NARC_INDEX_POKETOOL__POKEGRA__PL_POKEGRA;\n"
    "            spriteTemplate->character = species * 6 + face + (gender != GENDER_FEMALE ? 1 : 0);\n"
    "            spriteTemplate->palette = species * 6 + 4 + shiny;\n"
    "        }\n"
    "        break;\n\n"
    "    case SPECIES_EMPOLEON:\n"
    "        if (form == MEGA_FORM_EMPOLEON) {\n"
    "            spriteTemplate->narcID = NARC_INDEX_POKETOOL__POKEGRA__PL_OTHERPOKE;\n"
    "            spriteTemplate->character = 280 + (face / 2);\n"
    "            spriteTemplate->palette = 286 + shiny;\n"
    "        } else {\n"
    "            spriteTemplate->narcID = NARC_INDEX_POKETOOL__POKEGRA__PL_POKEGRA;\n"
    "            spriteTemplate->character = species * 6 + face + (gender != GENDER_FEMALE ? 1 : 0);\n"
    "            spriteTemplate->palette = species * 6 + 4 + shiny;\n"
    "        }\n"
    "        break;\n\n"
)
replace_once(
    "src/pokemon.c",
    "    default:\n        spriteTemplate->narcID = NARC_INDEX_POKETOOL__POKEGRA__PL_POKEGRA;",
    pl_cases + "    default:\n        spriteTemplate->narcID = NARC_INDEX_POKETOOL__POKEGRA__PL_POKEGRA;",
)

dp_cases = pl_cases.replace("NARC_INDEX_POKETOOL__POKEGRA__PL_POKEGRA", "NARC_INDEX_POKETOOL__POKEGRA__POKEGRA")
replace_once(
    "src/pokemon.c",
    "    default:\n        spriteTemplate->narcID = NARC_INDEX_POKETOOL__POKEGRA__POKEGRA;",
    dp_cases + "    default:\n        spriteTemplate->narcID = NARC_INDEX_POKETOOL__POKEGRA__POKEGRA;",
)

# Preserve all canonical archive indices by allowing PNG sprite entries after PAL entries.
replace_once(
    "tools/scripts/make_pl_otherpoke.py",
    "# The first batch of files should all be sprites\n"
    "for i in range(args.sprite_entries):\n"
    "    infile = args.files[i]\n"
    "    target = private_dir / f'pl_otherpoke_{i:04}.NCGR'\n"
    "    subprocess.run([\n"
    "        args.nitrogfx,\n"
    "        infile,\n"
    "        target,\n"
    "        '-encodefronttoback',\n"
    "        '-scan',\n"
    "    ])\n\n"
    "# The next batch of files should all be palettes\n"
    "for i in range(args.sprite_entries, args.sprite_entries + args.palette_entries):\n"
    "    infile = args.files[i]\n"
    "    target = private_dir / f'pl_otherpoke_{i:04}.NCLR'\n"
    "    subprocess.run([\n"
    "        args.nitrogfx,\n"
    "        infile,\n"
    "        target,\n"
    "        '-bitdepth', '8',\n"
    "        '-nopad',\n"
    "        '-comp', '10'\n"
    "    ])\n",
    "# Core archive entries are normally sprites followed by palettes. New form\n"
    "# resources may be appended without renumbering canonical entries, so choose\n"
    "# the converter from the source extension rather than the numeric range.\n"
    "core_entries = args.sprite_entries + args.palette_entries\n"
    "for i in range(core_entries):\n"
    "    infile = pathlib.Path(args.files[i])\n"
    "    if infile.suffix.lower() == '.pal':\n"
    "        target = private_dir / f'pl_otherpoke_{i:04}.NCLR'\n"
    "        subprocess.run([\n"
    "            args.nitrogfx,\n"
    "            infile,\n"
    "            target,\n"
    "            '-bitdepth', '8',\n"
    "            '-nopad',\n"
    "            '-comp', '10'\n"
    "        ], check=True)\n"
    "    else:\n"
    "        target = private_dir / f'pl_otherpoke_{i:04}.NCGR'\n"
    "        subprocess.run([\n"
    "            args.nitrogfx,\n"
    "            infile,\n"
    "            target,\n"
    "            '-encodefronttoback',\n"
    "            '-scan',\n"
    "        ], check=True)\n",
)
replace_once(
    "res/pokemon/meson.build",
    "        '--sprite-entries', '168',\n        '--palette-entries', '108',",
    "        '--sprite-entries', '174',\n        '--palette-entries', '114',",
)

# Asset indices: six appended sprites, then six appended palettes.
manifest_entries = {
    "torterra": (276, 277, 282, 283),
    "infernape": (278, 279, 284, 285),
    "empoleon": (280, 281, 286, 287),
}
for species, (back, front, normal, shiny) in manifest_entries.items():
    append_once(
        f"res/pokemon/{species}/meson.build",
        "pokefoot_files += files('footprint.png')\n",
        "otherpoke_index += {\n"
        f"    '{back}': files('forms/mega/back.png'),\n"
        f"    '{front}': files('forms/mega/front.png'),\n"
        f"    '{normal}': files('forms/mega/normal.pal'),\n"
        f"    '{shiny}': files('forms/mega/shiny.pal'),\n"
        "}\n",
    )

# Reclaim three intentionally unused Gen IV item IDs; no existing item indices shift.
replace_once(
    "generated/items.txt",
    "ITEM_UNUSED_120\nITEM_UNUSED_121\nITEM_UNUSED_122\n",
    "ITEM_TORTERRITE\nITEM_INFERNAPITE\nITEM_EMPOLEONITE\n",
)
replace_once(
    "src/item.c",
    "    [ITEM_UNUSED_120] = {\n"
    "        .dataID = 0x0,\n"
    "        .iconID = none_NCGR,\n"
    "        .paletteID = none_NCLR,\n"
    "        .gen3ID = GBA_ITEM_NONE,\n"
    "    },\n"
    "    [ITEM_UNUSED_121] = {\n"
    "        .dataID = 0x0,\n"
    "        .iconID = none_NCGR,\n"
    "        .paletteID = none_NCLR,\n"
    "        .gen3ID = GBA_ITEM_NONE,\n"
    "    },\n"
    "    [ITEM_UNUSED_122] = {\n"
    "        .dataID = 0x0,\n"
    "        .iconID = none_NCGR,\n"
    "        .paletteID = none_NCLR,\n"
    "        .gen3ID = GBA_ITEM_NONE,\n"
    "    },\n",
    "    [ITEM_TORTERRITE] = {\n"
    "        .dataID = 0x1C5,\n"
    "        .iconID = mega_stone_NCGR,\n"
    "        .paletteID = mega_stone_NCLR,\n"
    "        .gen3ID = GBA_ITEM_NONE,\n"
    "    },\n"
    "    [ITEM_INFERNAPITE] = {\n"
    "        .dataID = 0x1C6,\n"
    "        .iconID = mega_stone_NCGR,\n"
    "        .paletteID = mega_stone_NCLR,\n"
    "        .gen3ID = GBA_ITEM_NONE,\n"
    "    },\n"
    "    [ITEM_EMPOLEONITE] = {\n"
    "        .dataID = 0x1C7,\n"
    "        .iconID = mega_stone_NCGR,\n"
    "        .paletteID = mega_stone_NCLR,\n"
    "        .gen3ID = GBA_ITEM_NONE,\n"
    "    },\n",
)

item_row_template = ",0,HOLD_EFFECT_NONE,0,0,0,0,0,31,false,false,POCKET_ITEMS,BATTLE_POCKET_MASK_NONE,ITEM_USE_FUNC_NONE,0,0,false,false,false,false,false,false,false,false,false,false,false,false,0,0,0,0,0,0,0,false,false,false,false,false,false,false,false,false,false,false,false,false,false,0,0,0,0,0,0,0,0,0,0,0\n"
append_once(
    "res/items/pl_item_data.csv",
    "ITEM_SCIZORITE" + item_row_template,
    "ITEM_TORTERRITE" + item_row_template
    + "ITEM_INFERNAPITE" + item_row_template
    + "ITEM_EMPOLEONITE" + item_row_template,
)

replace_once(
    "res/text/item_names.json",
    '      "id": "pl_msg_00000392_00120",\n      "en_US": "???"',
    '      "id": "pl_msg_00000392_00120",\n      "en_US": "Torterrite"',
)
replace_once(
    "res/text/item_names.json",
    '      "id": "pl_msg_00000392_00121",\n      "en_US": "???"',
    '      "id": "pl_msg_00000392_00121",\n      "en_US": "Infernapite"',
)
replace_once(
    "res/text/item_names.json",
    '      "id": "pl_msg_00000392_00122",\n      "en_US": "???"',
    '      "id": "pl_msg_00000392_00122",\n      "en_US": "Empoleonite"',
)
for item_id, species in ((120, "Torterra"), (121, "Infernape"), (122, "Empoleon")):
    replace_once(
        "res/text/item_descriptions.json",
        f'      "id": "pl_msg_00000391_{item_id:05}",\n      "garbage": 0',
        f'      "id": "pl_msg_00000391_{item_id:05}",\n'
        '      "en_US": [\n'
        f'        "A stone that enables {species} to\\n",\n'
        '        "Mega Evolve during battle when held."\n'
        '      ]',
    )

# Route 206: expose all three stones beside the existing seven-stone test/pickup line.
replace_once(
    "res/field/scripts/scripts_unk_0404.s",
    "    ScriptEntry _mega_scizorite\n    ScriptEntryEnd",
    "    ScriptEntry _mega_scizorite\n"
    "    ScriptEntry _mega_torterrite\n"
    "    ScriptEntry _mega_infernapite\n"
    "    ScriptEntry _mega_empoleonite\n"
    "    ScriptEntryEnd",
)
append_once(
    "res/field/scripts/scripts_unk_0404.s",
    "_mega_scizorite:\n"
    "    SetVar VAR_0x8008, ITEM_SCIZORITE\n"
    "    SetVar VAR_0x8009, 1\n"
    "    GoTo _1EAE\n"
    "    End\n",
    "_mega_torterrite:\n"
    "    SetVar VAR_0x8008, ITEM_TORTERRITE\n"
    "    SetVar VAR_0x8009, 1\n"
    "    GoTo _1EAE\n"
    "    End\n\n"
    "_mega_infernapite:\n"
    "    SetVar VAR_0x8008, ITEM_INFERNAPITE\n"
    "    SetVar VAR_0x8009, 1\n"
    "    GoTo _1EAE\n"
    "    End\n\n"
    "_mega_empoleonite:\n"
    "    SetVar VAR_0x8008, ITEM_EMPOLEONITE\n"
    "    SetVar VAR_0x8009, 1\n"
    "    GoTo _1EAE\n"
    "    End\n\n",
)

event_path = ROOT / "res/field/events/events_route_206.json"
event_text = event_path.read_text()
if '"id": "ROUTE_206_POKEBALL_TORTERRITE"' in event_text:
    raise RuntimeError("Route 206 starter Mega Stone events already present")
needle = "        }\n    ],\n    \"warp_events\": ["
pos = event_text.rfind(needle)
if pos < 0:
    raise RuntimeError("Could not locate end of Route 206 object event list")
new_events = """        },
        {
            "id": "ROUTE_206_POKEBALL_TORTERRITE",
            "graphics_id": "OBJ_EVENT_GFX_POKEBALL",
            "movement_type": "MOVEMENT_TYPE_NONE",
            "trainer_type": "TRAINER_TYPE_NONE",
            "hidden_flag": "FLAG_UNK_0x0543",
            "script": 7335,
            "initial_dir": 0,
            "data": [],
            "movement_range_x": 0,
            "movement_range_z": 0,
            "x": 312,
            "z": 678,
            "y": 0
        },
        {
            "id": "ROUTE_206_POKEBALL_INFERNAPITE",
            "graphics_id": "OBJ_EVENT_GFX_POKEBALL",
            "movement_type": "MOVEMENT_TYPE_NONE",
            "trainer_type": "TRAINER_TYPE_NONE",
            "hidden_flag": "FLAG_UNK_0x0544",
            "script": 7336,
            "initial_dir": 0,
            "data": [],
            "movement_range_x": 0,
            "movement_range_z": 0,
            "x": 314,
            "z": 678,
            "y": 0
        },
        {
            "id": "ROUTE_206_POKEBALL_EMPOLEONITE",
            "graphics_id": "OBJ_EVENT_GFX_POKEBALL",
            "movement_type": "MOVEMENT_TYPE_NONE",
            "trainer_type": "TRAINER_TYPE_NONE",
            "hidden_flag": "FLAG_UNK_0x0545",
            "script": 7337,
            "initial_dir": 0,
            "data": [],
            "movement_range_x": 0,
            "movement_range_z": 0,
            "x": 316,
            "z": 678,
            "y": 0
        }
    ],
    "warp_events": ["""
event_path.write_text(event_text[:pos] + new_events + event_text[pos + len(needle):])

print("Integrated Mega Torterra, Mega Infernape, and Mega Empoleon.")
