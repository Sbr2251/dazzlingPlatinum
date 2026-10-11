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
   a Gen 5 move, ability or evolution method it has no rule for. Add the rule to `MOVE_SUBS` (or
   `LEVEL_MOVE_SUBS` for a level-up-only rule), `ABILITY_SUBS`, `TRADE_EVO_LEVEL`,
   `ITEM_EVO_FALLBACK_LEVEL` or `DEX_TEXT_OVERRIDES`. A `--species` run keeps the other species'
   entries in `gen5_species_report.json`; a run with no arguments rewrites every species and the
   whole report (the Arc 1 files come out byte-identical).
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
  Sewaddle line. The Arc 2 lines are 518-536, also in national order: Woobat 518, Swoobat 519,
  Cottonee 520, Whimsicott 521, Sandile 522, Krokorok 523, Krookodile 524, Yamask 525, Cofagrigus 526,
  Frillish 527, Jellicent 528, Klink 529, Klang 530, Klinklang 531, Elgyem 532, Beheeyem 533,
  Litwick 534, Lampent 535, Chandelure 536. The in-game National Dex number is the species ID, so it doesn't match the real
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

## Substitutions (Arc 2 lines)

Same rules as Arc 1: Gen 5 base stats and B2W2 learnsets. Cottonee and Whimsicott keep their Gen 6
Grass/Fairy typing, like the hack's other Fairies (commit ba8051fd9e), and learn the hack's Fairy moves
at their X/Y levels: Fairy Wind (Cottonee, Lv1) and Moonblast (Whimsicott, Lv50).

| Gen 5 | Gen 4 stand-in | who |
|---|---|---|
| Prankster | Chlorophyll (their hidden ability) | Cottonee, Whimsicott |
| Infiltrator | Mold Breaker | Cottonee, Whimsicott |
| Moxie | Anger Point (their hidden ability) | Sandile line |
| Mummy (their only ability) | Rough Skin; second slot empty | Yamask, Cofagrigus |
| Cursed Body | Cute Charm | Frillish, Jellicent |
| Telepathy | Forewarn | Elgyem, Beheeyem |
| Heart Stamp | Zen Headbutt | Woobat, Swoobat |
| Cotton Guard | Barrier | Cottonee |
| Hurricane | Air Slash | Whimsicott |
| Foul Play (level-up) | Night Slash | Sandile line (the egg-move rule still drops it) |
| Gear Grind | Iron Head | Klink line |
| Shift Gear | Dragon Dance | Klink line |
| Autotomize | Rock Polish | Klink line |
| Guard Split / Power Split | Guard Swap / Power Swap | Yamask, Cofagrigus, Elgyem, Beheeyem |
| Hex | Ominous Wind | Yamask, Frillish and Litwick lines |
| Flame Burst | Lava Plume | Litwick line |
| Inferno | Fire Blast | Litwick, Lampent |
| Simple Beam | Worry Seed | Elgyem, Beheeyem |
| Synchronoise | Extrasensory | Elgyem, Beheeyem; Woobat (egg) |
| Wonder Room | Trick Room | Elgyem, Beheeyem |
| Stored Power (egg) | Psybeam | Woobat |
| Clear Smog (egg) | Smog | Litwick |

- A substitute the species already learns at another level is kept once, at the earlier level (Hex
  becomes Ominous Wind at Lv17 for Yamask, so its Lv25 Ominous Wind goes; Frillish keeps its own Lv27).
- Hidden abilities that don't fit the two slots are dropped: Simple (Woobat), Damp (Frillish), Clear
  Body (Klink), Analytic (Elgyem), Shadow Tag (Litwick).
- Evolutions: Cottonee uses a Sun Stone and Lampent a Dusk Stone, as in B/W (both items exist; if
  one didn't, `ITEM_EVO_FALLBACK_LEVEL` gives Lampent level 41). Woobat evolves by friendship;
  Sandile 29, Krokorok 40, Yamask 34, Frillish 40, Klink 38, Klang 49, Elgyem 42 and Litwick 41 by
  level. Yamask's Galarian branch (Runerigus) is skipped.
- Four English entries are shortened slightly to fit three lines: Woobat, Swoobat, Cottonee, Yamask.
- Sinnoh Pokedex: Cottonee after Roserade (Route 204), Woobat after Crobat (Ravaged Path), Elgyem
  after Clefable (Veilstone and the Meteor Shrine), Litwick after Spiritomb (the Lost Tower and
  Hallowed Tower), Yamask after Unown (Solaceon), Sandile after Hippowdon (the Valor Basin), Klink
  after Azumarill (Route 212 north) and Frillish after Tentacruel (Route 213). The Sinnoh dex grows
  from 250 to 269.
- The Arc 2 Gen 3 lines then took the Sinnoh dex from 269 to 307, by the same rule (see the git log of
  `res/pokemon/sinnoh_pokedex.json`). Everything sized by it reads `SINNOH_DEX_COUNT`, which
  `tools/scripts/make_shinzukan.py` generates from the json, so adding a species needs no other edit. The
  one exception was Rowan's Pokedex rating (`Pokedex_GetRatingMessageID_Local`), whose vanilla tiers ended at
  209 seen; they now scale with `SINNOH_DEX_COUNT`.
