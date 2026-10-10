# Gen 5 species

This directory holds the tools that add Gen 5 Pokemon after Arceus. The B/W battle sprites
(`gen5_stream.py`) are covered in `docs/living_battle_stage/sprite_stream.md`. This file covers
the species themselves.

| tool | what it writes |
|---|---|
| `gen5_species.py` | `res/pokemon/<species>/`: data.json (stats, types, abilities, learnsets, evolutions, Pokedex data and text in six languages), icon.png, footprint.png, meson.build, sprite_data.json and the `.png.key` files (from an analogous Sinnoh species), plus placeholder PNG/PAL files for `gen5_stream.py` to overwrite. Substitutions go to `gen5_species_report.json`. |
| `gen5_stream.py` | the battle streams in `mon_stream.narc`, `{male,female}_{front,back}.png`, `normal.pal` and `shiny.pal` |
| `gen5_cries.py` | the cries: an SDAT bank and wave archive per species, at the species ID |
| `dex_numbers.json` | the national dex number of each species after Arceus (the PokeAPI/B/W art key) |

Sources: PokeAPI (stats, learnsets, dex text, B/W sprites) and pokeemerald-expansion (B/W icons,
footprints and cries). Both are downloaded once and cached under `~/.cache/gen5_sprites`.

## Adding a species

1. Add `SPECIES_<NAME>` to `generated/species.txt`, after the last Gen 5 species and before
   `SPECIES_EGG`. Add `(dir, national number, Sinnoh analogue)` to `SPECIES` in `gen5_species.py`,
   and the number to `dex_numbers.json`.
2. Run `~/.venvs/desmume/bin/python tools/gen5_sprites/gen5_species.py --species <dir>`. It stops on
   a Gen 5 move, ability or evolution method it has no rule for. Add the rule to `MOVE_SUBS`,
   `ABILITY_SUBS`, `TRADE_EVO_LEVEL` or `DEX_TEXT_OVERRIDES`.
3. Run `gen5_stream.py`. With no arguments it rebuilds the whole NARC, which takes seconds when the
   cache is warm.
4. Run `python3 tools/gen5_sprites/gen5_cries.py`.
5. Add the species to `res/pokemon/sinnoh_pokedex.json` if the player meets it before the National
   Dex. Without the National Dex, the Pokedex lists only Sinnoh dex species, and the summary shows
   no dex number for anything else.
6. Append its English entry to `res/text/species_pokedex_entry_{diamond,pearl,unused}.json`, as
   the earlier ones are.

## Numbering and the save file

- Species IDs: Deino, Zweilous and Hydreigon are 494-496. The Arc 1 lines are 497-517, in national
  order: Patrat ... Purrloin/Liepard, Pidove line, Roggenrola line, Drilbur/Excadrill, Timburr line,
  Sewaddle line. The in-game National Dex number is the species ID, so it doesn't match the real
  dex: Patrat is No. 497, not 504. Egg and Bad Egg come after the last species. Neither is ever
  stored by ID, so moving them is safe.
- Forms with their own data (Deoxys, Wormadam, Giratina, Shaymin, Rotom) follow `SPECIES_BAD_EGG`
  in pl_personal/wotbl. `Pokemon_GetFormNarcIndex` derives their indices from it.
- The Pokedex save block keeps vanilla's size, so old saves load:
  - The 16-word seen/caught/gender bitfields hold species 1-504. The top byte of the last caught
    and seen words is Deoxys's form record.
  - Species 505 and up keep their four bits (caught, seen, two genders) in bits 6-7 of the
    per-species language bytes. Those bytes only use bits 0-5, one per language.
  - `DexBit_Locate` in `src/pokedex.c` maps both, and a compile-time check allows up to species 750.
- The Battle Hall's per-species record (the frontier extra save page) is sized by `MAX_SPECIES` and
  grows with it. That page is post-game only. It has room up to about 680 species.

## Substitutions (Arc 1 lines)

Gen 5 data, with Gen 5 base stats: Stoutland and Unfezant have their B/W Attack, and Gigalith and
Leavanny their B/W Sp. Def. The engine has two ability slots and no Gen 5 moves:

| Gen 5 | Gen 4 stand-in | who |
|---|---|---|
| Big Pecks | Keen Eye | Pidove line |
| Sand Rush | Sand Veil | Herdier, Stoutland, Drilbur, Excadrill |
| Sheer Force | Iron Fist (their hidden ability) | Timburr line |
| (only one ability in Gen 5) | Sand Force, their hidden ability | Roggenrola line |
| Work Up | Howl | Patrat, Lillipup line |
| Hone Claws | Sharpen | Purrloin, Liepard, Drilbur, Excadrill |
| Retaliate | Facade | Lillipup line |
| After You | Helping Hand | Patrat, Watchog |
| Chip Away | Headbutt | Timburr line |
| Smack Down | Rock Throw | Roggenrola line |
| Struggle Bug | Silver Wind | Sewaddle, Leavanny |
| Entrainment | Worry Seed | Leavanny |
| Drill Run | Drill Peck | Drilbur, Excadrill |
| Autotomize (egg) | Rock Polish | Roggenrola |
| Heavy Slam (egg) | Gyro Ball | Roggenrola |
| Bestow, Foul Play, Wide Guard (egg) | dropped | Pidove, Purrloin, Timburr |

- Hidden abilities that don't fit the two slots are dropped: Analytic, Run Away (Lillipup),
  Scrappy, Prankster, Rivalry, Overcoat and Mold Breaker.
- Trade evolutions become levels, like Graveler and Machoke: Boldore -> Gigalith at 37 and
  Gurdurr -> Conkeldurr at 37.
- TMs: a species gets a Gen 4 TM when it can learn the move from a TM or tutor in any later game,
  or by level. Secret Power, Endure, Captivate, Sleep Talk and Natural Gift go to everyone, as
  they did in Gen 4. Some Gen 4-only TMs/HMs go where the Sinnoh analogues have them:
  - Steel Wing, Pluck and Defog: the birds;
  - Snatch: Purrloin's line;
  - Rock Climb: the Lillipup, Roggenrola, Drilbur and Timburr lines.
- Pokedex entries are Black/White's, wrapped to the widest vanilla line (192 px). Species names are
  in capitals, as in Platinum. Six entries that need four lines are shortened slightly; see
  `DEX_TEXT_OVERRIDES`.
