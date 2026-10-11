# Overworld sprites, DS-only round (Darren, Garius, Ruth)

Third round. Hard rule from the owner: DS (Gen 4/5) style only, original characters only, explicit free licence
(CC0/PD first, credit-only flagged, everything else rejected). Gen 3 / GBA-styled sprites, Openmon included, are rejected.
Earlier rounds: `../ow_sprites/` (official rips, dropped) and `../ow_sprites_free/` (Openmon, Gen 3 style, dropped).
The repos were not touched.

DS test applied to every candidate (see each `*_vs_stock.png`):
- figure about 23-24 px tall in a 32x32 cell, head top y=7, feet y=29;
- Gen 4 proportions: head about 13 rows of 23, 2-3 px legs;
- multi-tone (3-step) shading, near-black outline;
- checked side by side with stock Lucas, Dawn, Barry, and the Ace Trainer M and Scientist F NPCs.

## Result of the search: no clean DS-style original character exists

| source | DS test | licence | verdict |
|---|---|---|---|
| Poltergeist / Coffee Cup "Character Customization Resources (Gen 4)", Eevee Expo 317 / PokeCommunity 421381 | **pass** (18x25 figure, Gen 4 bodies, walk + run + bike) | "You can freely use, edit and share it if you want. Credit and a link to your project would be appreciated, though!" | **FLAGGED**: the author says the bodies are made "from scratch (well, and from the vanilla sprites)", so they are derived from official sprites. Kit builds K1-K4 below |
| Openmon NPC Sprites Set 1 (Screen Smith, CC0) | fail (21 px, Gen 3 shading) | CC0 | rejected as sprites; its CC0 designs are the source of the redraws |
| Tuxemon character sprites (CC BY-SA) | fail (16x20 chibi) | CC BY / BY-SA | rejected |
| Cabbit / diamonddmgirl 24x32 (OGA, CC-BY) | fail (RPG-Maker VX proportions, 26-30 px) | CC-BY 3.0 | rejected |
| Pipoya 32x32, Superpowers, Corey Archer (OGA) | fail (fill the whole cell, or 16x16 chibi) | free / CC0 | rejected |
| Voltseon "1px Character Creator" (Eevee Expo 724) | likely DS-sized | **no licence stated** | rejected |
| Darkshock1 "Trainer Brenda" (Eevee Expo 1886) | has a Gen 4 overworld | "credit if used: Thibault", edits not addressed; Mediafire download blocked | rejected (terms incomplete, not fetched) |
| WhiteLotus9678 "Original Trainer Sprites" (PokeCommunity 353432) | RMXP standard, not DS | "credit me", no edit terms; includes official characters | rejected |
| Gen 5 characters in Gen 4 OW style, PCCP redraws, Project Octagram | DS | official characters, or zip behind login | rejected |
| Screen Smith "Pokemon Style Characters" packs | n/a | CC0 but AI-generated (Retro Diffusion) | rejected |

## The fallback: DS redraws of the four CC0 Openmon designs (authored here)

Files: `<character>/D*_redraw_*` (4x sheet, walk GIF, `_vs_stock.png` comparison, `_platinum_walk.png` repo-ready sheet).
Source code: `/tmp/a1r3/tools/ds_cast2.py` (the pixel grids), `dsdraw.py` / `dschars.py` (shading, outline and step-frame
engine).

How they were made:
- Heads are hand-authored, pixel by pixel, as explicit-colour ASCII grids: outline, 3-tone hair, 3-tone skin, eyes and
  glasses.
- Bodies are hand-drawn region masks (top, sleeves, hands, trim, bottoms, shoes). A deterministic pass adds a 3-tone
  ramp (light from the top-left), a near-black outline, outlines between the arms and torso, and shadow under the hair.
- Step frames: the upper body rises 1 px and one foot drops to y=30, the same timing as Platinum walkers. The legs come
  from hand-drawn leg masks: trousers, skirt with bare legs, or coat tails with tights.
- Stock sprites were used only to measure size: head top y=7, feet y=29, x 7..23, head about 13 rows, row widths. The
  redraw code reads no stock pixel data. No stock pixel was copied or traced.
- Colours and silhouettes follow the Openmon designs:
  - boy: dark skin, dark curly hair, teal jacket over a white shirt;
  - girl: light-blue hair, high ponytail;
  - Garius: maroon spiky hair, red shirt, dark trousers;
  - Ruth: wild purple hair, glasses, white coat, red tie.
  Additions: the girl's blue hairband and Ruth's coat over a light-blue shirt are mine.
- Garius Eclipse (D3e): the same grids with an Eclipse palette (slate hair, violet shirt, violet-black trim).

| role | file key | licence / credit |
|---|---|---|
| Darren, boy | D1_redraw_teal_jacket | CC0 design; new pixels are the project's. Credit optional: "Designs based on Openmon NPC Sprites Set 1 by Screen Smith (CC0)" |
| Darren, girl | D2_redraw_blue_ponytail | same |
| Garius | D3_redraw_garius + D3e_redraw_garius_eclipse | same |
| Ruth | D4_redraw_ruth | same |

### Honest quality self-check

- **Better than the Openmon originals for this game: yes.** They are the right size (head top and feet on Lucas's lines),
  have Gen 4 head/leg proportions and outline weight, and sit in a crowd of stock NPCs without looking shrunken. The
  Openmon sprites are visibly smaller and flatter next to stock.
- **As good as Game Freak's Platinum sprites: no.** In the comparisons:
  - hair is clustered but still a bit regular or noisy where stock hair has deliberate strands (most visible on the
    boy's curls and the girl's back view, which reads as stripes);
  - faces are simpler: 1x2 eyes, no brow or cheek modelling;
  - clothing has less detail (no pockets, zips or straps);
  - side-view arms are static (I turned off arm swing because it left outline seams), so side walks look stiffer than
    Lucas's.
- Per sprite:
  - D3 Garius is the strongest: spikes, brows and red shirt read clearly as a brash rival, and the Eclipse palette works.
  - D4 Ruth reads well from the front (glasses, coat, tie); the side view is fine, the back view is a plain hair dome.
  - D1 boy is solid; the curls are the weakest part.
  - D2 girl: the front is good; the side ponytail is acceptable; the back view is the weakest frame of the set.
- The upshot: these are usable placeholders-to-final for NPC-level presence. Before shipping them as the player
  character, a pixel artist should spend a pass on the hair textures, the faces and the side walk (about 1-2 h per
  character). Nothing here matches Lucas or Dawn's polish.

## The flagged DS-style find: Poltergeist kit builds (K1-K4)

- Built from the kit layers (base, bottoms, top, hair, accessories) at 1x density.
- They pass the DS test best of everything: they derive from vanilla bodies, so the proportions and walk/run/bike
  cycles match Platinum exactly.
- The kit has walk, run and bike for both genders (a swimming add-on exists at Eevee Expo 373); there are no
  surf-on-Pokemon or fishing frames.
- The designs are generic: kit hair and clothes, not the Openmon looks.

| role | key | build |
|---|---|---|
| Darren, boy | K1_kit_boy | dark skin base, green open jacket, navy jeans, brown "boy 1" hair |
| Darren, girl | K2_kit_girl | light base, white tee, navy capris, blue bag, cyan long "girl 1" hair |
| Garius | K3_kit_garius | light base, red tee, black jeans, red "boy 4" hair |
| Ruth | K4_kit_ruth | light base, beige trenchcoat, pencil skirt, purple long hair, blue glasses |

Licence quote (Eevee Expo 317): "You can freely use, edit and share it if you want. Credit and a link to your project
would be appreciated, though!" Credit line: "Overworld sprite built with Poltergeist's Character Customization Resources
(eeveeexpo.com/resources/317)". FLAG: "I created all resources from scratch (well, and from the vanilla sprites)".

## Integration effort

- Garius and Ruth (walk only): small. Drop `D3_redraw_garius_platinum_walk.png` over Barry's member (0x7F, same
  16-frame layout). Ruth needs a new gfx constant (the counterpart has no member of its own), following the
  `integrate_arc1_field_sprites.py` pattern.
- Darren (full protagonist set):
  - with the redraws: walk exists. Run, bike (24), surf (4), fish (16) and the minor poses (about 50 more frames per
    gender) can be built with the same engine: new leg/arm masks per pose with the same head grids. That is days of
    careful pixel work, not hours.
  - with the kit: walk, run and 16 of the 24 bike frames already exist; surf, fishing and the minor poses still need
    drawing.

## Files

- `ds_overview.png`: every candidate next to Lucas, Dawn and Barry at 4x (yellow rows = redraws, blue = kit, grey = stock).
- `ds_redraws_walk.gif`: the five redraws walking beside Lucas, Dawn and Barry.
- `<character>/<key>_sheet.png`, `_walk.gif`, `_run.gif` (kit only), `_vs_stock.png`, `_platinum_walk.png`,
  `_platinum_walk_run.png` (kit only).
- All 13 repo-format PNGs pass the repo's `read_indexed_png` (128x128 or 128x256, 4-bit, max index <= 15).
- `candidates.json`: machine-readable list.

## Uploaded previews (artifacts)

- `ds_overview.png`: https://artifacts.internalmeta.com/a/1599747234969726
- `ds_redraws_walk.gif`: https://artifacts.internalmeta.com/a/2283515575564516
- `darren_boy/D1_redraw_teal_jacket_vs_stock.png`: https://artifacts.internalmeta.com/a/1128579186410118
- `darren_girl/D2_redraw_blue_ponytail_vs_stock.png`: https://artifacts.internalmeta.com/a/1656281749472310
- `garius/D3_redraw_garius_vs_stock.png`: https://artifacts.internalmeta.com/a/1133475095913811
- `garius/D3e_redraw_garius_eclipse_vs_stock.png`: https://artifacts.internalmeta.com/a/3338456496339386
- `ruth/D4_redraw_ruth_vs_stock.png`: https://artifacts.internalmeta.com/a/940680658732571
- `darren_boy/D1_redraw_teal_jacket_walk.gif`: https://artifacts.internalmeta.com/a/1398980112292617
- `darren_girl/D2_redraw_blue_ponytail_walk.gif`: https://artifacts.internalmeta.com/a/1763552444936181
- `garius/D3_redraw_garius_walk.gif`: https://artifacts.internalmeta.com/a/2375217376579437
- `garius/D3e_redraw_garius_eclipse_walk.gif`: https://artifacts.internalmeta.com/a/1722672975484374
- `ruth/D4_redraw_ruth_walk.gif`: https://artifacts.internalmeta.com/a/1910344283282489
- `darren_boy/K1_kit_boy_vs_stock.png`: https://artifacts.internalmeta.com/a/1400324325414261
- `darren_girl/K2_kit_girl_vs_stock.png`: https://artifacts.internalmeta.com/a/2056940368265953
