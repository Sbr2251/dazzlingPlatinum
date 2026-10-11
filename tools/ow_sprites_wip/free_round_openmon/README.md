# Overworld sprite candidates, free-licence round (Darren, Garius, Ruth)

Second round, after the owner's new rules: only fan-made sprites of ORIGINAL characters, under a licence written down where
they are published. Preference order: CC0 first, then CC-BY / "free with credit" (flagged). Rejected: "ask first",
non-commercial-only, no-edits, no stated terms, redraws of official characters, and AI-generated packs. The first round, built
from official rips, stays in `../ow_sprites/` for reference only. Nothing in the repo was touched.

## Files

| file | what |
|---|---|
| `recommended_cast_overview.png` | the picks (Darren boy, Darren girl, Garius plus his Eclipse look, Ruth) plus the two flagged kit builds with run/bike, at 4x |
| `recommended_cast_walk.gif` | the same seven walking together through all four facings |
| `<character>/<character>_overview.png` | every candidate for the role next to the stock sprite it replaces |
| `<character>/README.md` | per candidate: source URL, creator, licence, **quoted licence text**, exact credit line, sets, fit notes |
| `<character>/<key>_sheet.png`, `_walk.gif`, `_run.gif` | labelled 4x sheet (4 facings x stand/step A/stand/step B + extra sets) and animations |
| `<character>/<key>_platinum_walk.png` | ready for the repo's walker tools: 128x128, 4-bit indexed, 16 colours, index 0 transparent, BGR555-snapped, rows up/down/left/right, feet on y=29, centred on x=15. All 19 pass the repo's `read_indexed_png` |
| `<character>/<key>_platinum_walk_run.png` | kit builds only: 128x256, walk + run in the stock 32-frame `PLAYER_M` layout |
| `_sources/` | the downloaded source sheets and Tuxemon's ATTRIBUTIONS.md |
| `candidates.json` | machine-readable list with licence fields |
| `../tools/build_free.py`, `free_src.py` | re-cut everything from `/tmp/a1r3/src2/` |

## Picks

| role | pick | licence | runner-up(s) |
|---|---|---|---|
| Darren, boy | **B1 Openmon NPC: dark-skinned boy, teal jacket** | CC0 | B4 kit boy (walk+run+bike, flagged), B2 Openmon navy hair |
| Darren, girl | **G1 Openmon NPC: light-blue ponytail girl** | CC0 | G4 kit girl (walk+run+bike, flagged), G3 Tuxemon Heroine (CC BY-SA 4.0) |
| Garius | **R1 Openmon NPC: spiky maroon hair, red shirt** + **R1e Eclipse recolour** | CC0 (the edit is ours, allowed) | R2 Tuxemon Cool Dude (CC BY / BY-SA), R3 Openmon green spiky |
| Ruth | **T1 Openmon NPC: purple hair, glasses, white coat** | CC0 | T2 Openmon green hood (CC0), T3 Tuxemon Professor (CC BY-SA 4.0) |
| fallback | stock Platinum recolours (R4 Ace Trainer M, T4 Scientist F) | the game's own asset | n/a |

Every pick comes from one human-drawn CC0 pack, "Openmon NPC Sprites Set 1" by Screen Smith
(https://screensmith.itch.io/openmon-npc-sprites-set-1). Licence text: "NOT AI GENERATED, MADE BY A FIVERR ARTIST ... These
sprites are released under a CC0 License. They were created as a part of commissions that I ordered and have the full rights
to. Use them however you want, no attribution needed." No credit line is required. Optional: "Overworld sprites: Openmon NPC
Sprites Set 1 by Screen Smith (CC0)".

Caveats:
- The Openmon characters are about 21 px tall against Platinum's 24 px, so they look a little small and young next to stock NPCs.
- **No free candidate of an original character has a complete protagonist set.** Openmon, Tuxemon and the OGA packs are walk
  only. The only set with run and bike is Poltergeist's character-creation kit (Eevee Expo 317 / PokeCommunity 421381). It has
  an explicit licence ("You can freely use, edit and share it if you want. Credit and a link to your project would be
  appreciated"), but the author says its bodies were made "from scratch (well, and from the vanilla sprites)". It is FLAGGED
  for the owner's call. A swimming add-on (TechSkylander1518, Eevee Expo 373) exists. Nobody provides surf-on-Pokemon or
  fishing frames.

## Integration effort

- **Garius, Ruth (walk only): small.** Drop the `_platinum_walk.png` into the existing walker pipeline (the
  `tools/integrate_arc1_field_sprites.py` pattern). Garius can overwrite Barry's member (0x7F, same 16-frame layout). Ruth needs
  a new gfx constant, because `OBJ_EVENT_GFX_COUNTERPART` has no member of its own (it resolves to the other player sprite).
  Running = walk frames played faster, as for all NPCs.
- **Darren (full protagonist set): large, and mostly new pixel work.**
  - Walk exists. Run, bike, surf, fishing, holding Poke Ball, Sprayduck, contest, Poketch, save, VS Seeker and the Resonator
    pose must be drawn for the Openmon picks. Roughly 100+ frames per gender. The walk gives the head/body for each facing,
    and the stock Lucas/Dawn members give the poses to trace over.
  - The flagged kit builds cut this to about half: walk, run and bike already exist (the stock bike member has 24 frames, the
    kit gives 16, so 8 must be added), and they have the same Gen 4 proportions as Platinum.
  - Both options also need a battle back sprite, a trainer card and the intro full-body art (not covered here).

## Searched and rejected

| source | why not |
|---|---|
| Screen Smith's other "Pokemon Style Characters" packs (Townspeople 1-2, Water Trainers, Forest NPCs, Miners) | CC0, but "generated with Retro Diffusion" (AI), so not fan art |
| PIPOYA FREE RPG Character Sprites 32x32 (itch.io) | licence fine ("For commercial or personal use. Use and edit freely. Not redistribute or resell"), but fantasy chibi that fills the whole 32x32 cell, too big for Platinum |
| Cabbit / diamonddmgirl 24x32 packs (OGA, CC-BY 3.0) | licence fine (credit "Svetlana Kushnariova, lana-chan@yandex.ru"), but RPG-Maker-VX fantasy townsfolk, tall adult proportions (26-30 px). Tried (punk townsman for Garius) and dropped |
| Corey Archer "Top Down Pokemon-esque Sprites" (OGA, CC0) | CC0, but 16x16 Game Boy-era chibis, far below DS detail |
| Superpowers asset pack characters (OGA, CC0) | CC0, but 16x16 Ninja-Adventure chibis |
| scarloxy "Monster Taming Game Essentials" (itch.io) | "fully original and can be used commercially", 10 Pokemon-like walkers, but edits are not addressed and the download is gated behind itch's purchase flow, which the scripted fetch couldn't pass |
| N3Cloud "Pocket Creature Tamer" kit | free tier is non-commercial only |
| Anima_nel GBC NPC packs | non-commercial only, and GBC style |
| Voltseon "1px Character Creator" (Eevee Expo 724; has walk/run/bike/fish/surf bases) | no licence stated on the page |
| SalyaDarken "My Characters" (Eevee Expo 1503) | no licence; built on the kit + another base |
| Darkshock1 "Pokemon Trainer Brenda" (Eevee Expo 1886) | "shared ... for public use", "credit if used: Thibault", but edits not addressed and the Mediafire download is IP-locked, so it couldn't be fetched |
| deoxysacid "Random Trainer Graphics" (Eevee Expo 1852) | "go wild, just credit me", but the overworlds' characters are unidentified (the same author's packs include official characters) and the Mediafire download couldn't be fetched |
| TobalCRV Horizons pack, PCCP Gen 4 redraws, Project Octagram | official characters, or no download |
| DeviantArt resource stocks | not reachable without a browser session |

## Uploaded previews (artifacts)

- `recommended_cast_overview.png`: https://artifacts.internalmeta.com/a/1433582895539908
- `recommended_cast_walk.gif`: https://artifacts.internalmeta.com/a/1074518161959131
- `darren_boy/darren_boy_overview.png`: https://artifacts.internalmeta.com/a/2650317622069230
- `darren_girl/darren_girl_overview.png`: https://artifacts.internalmeta.com/a/29060965976840991
- `garius/garius_overview.png`: https://artifacts.internalmeta.com/a/1542915010935799
- `ruth/ruth_overview.png`: https://artifacts.internalmeta.com/a/1633509228407136
- `darren_boy/B1_openmon_teal_jacket_walk.gif`: https://artifacts.internalmeta.com/a/1406786961039651
- `darren_boy/B4_kit_boy_sheet.png`: https://artifacts.internalmeta.com/a/1111274517947001
- `darren_boy/B4_kit_boy_run.gif`: https://artifacts.internalmeta.com/a/1879253040181119
- `darren_girl/G1_openmon_blue_walk.gif`: https://artifacts.internalmeta.com/a/1763862851335131
- `darren_girl/G3_tuxemon_heroine_walk.gif`: https://artifacts.internalmeta.com/a/1079614181630403
- `darren_girl/G4_kit_girl_run.gif`: https://artifacts.internalmeta.com/a/1824683725234563
- `garius/R1_openmon_red_spiky_walk.gif`: https://artifacts.internalmeta.com/a/1103836682032239
- `garius/R1e_openmon_red_eclipse_walk.gif`: https://artifacts.internalmeta.com/a/1809222227292401
- `garius/R2_tuxemon_cooldude_walk.gif`: https://artifacts.internalmeta.com/a/1455198696517244
- `ruth/T1_openmon_purple_glasses_walk.gif`: https://artifacts.internalmeta.com/a/2171220160441939
- `ruth/T2_openmon_green_hood_walk.gif`: https://artifacts.internalmeta.com/a/1128769006279948
