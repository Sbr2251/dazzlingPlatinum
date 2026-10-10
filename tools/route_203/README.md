# Route 203: the scar

Arc 1 round 3 (workstream R). The west field of Route 203, right after the Jubilife exit, is torn: an old violet
fissure, scorched and cracked ground, and a tree that split at its base and fell across the road. The road is cut, so
the route detours north around the scar and through a 2-tile gap at the fissure's tip, where Garius waits (scene 12).
Nobody in game knows what it is ("the scar", "lightning, they say").

Only overworld chunk `map_data_019` (matrix cell 6,23: x 192..223, z 736..767) changes. Chunk 020, the map matrix,
the BDHC and the middle and east sections of the route are stock.

## Files

| file | what |
|---|---|
| `scar_layout.py` | The tile contract: the field x 196..213, z 744..760 as a character grid, plus the gap, Garius's spot, the Starly and their trigger row. `--ascii` prints it. The flood fill (`check`) proves the barrier is airtight. |
| `textures.py` | Appends the scar's textures and palettes to overworld texture set 006, append-only and rebuilt from `BASE_REV`. `--preview DIR` writes PNGs. |
| `build_scar.py` | Builds `map_data_019` from the stock chunk at `BASE_REV` and the layout: cut, new ground, decals, fissure, fallen tree, trees, permissions. It prints budgets and gameplay checks, and refuses `--write` if one fails. |

Regenerate (run from the repo root with the system `python3`; standard library only):

```
python3 tools/route_203/textures.py --write
python3 tools/route_203/build_scar.py --write
make release
```

Both scripts read their stock inputs from git (`BASE_REV` = 68ae1fadde, arc1-part2 before the scar), so re-running
them is deterministic and never feeds back on itself. The NSBMD, NSBTX and map_data writers are the Lake Verity
pipeline's (`tools/lake_verity/`, see `docs/lake_verity_redesign/pipeline.md`).

## Layout

```
      x 196 ........... 213
 744  ..........:::::...      g = gap (210,744..745): Garius's trigger, the only way past
 745  .........::%%%%:..
 746  wwww....:%%%%%X%:.      X  fissure (blocked)          %  violet-cracked ash (walk)
 747  wwww...:%%%%%XXG:.      :  scorched ash (walk)        w  tall grass
 748  wwwwTT.:%%%%%X%%:.      T  tree   K  charred tree     o  debris boulder
 749  wwwwTT.:%%%XXX%%:w      S  root end of the fallen tree, L  trunk, C  crown (blocked)
 750  wwwwTT.:%%XX%%%o:w      G  Garius (211,747)           =  stock road
 751  wwwwTT:%%%X%%%::.w
 752  wwwwKK:%%XX%%:..ww
 753  .ww.KK:%XX%%:...ww
 754  .....:%%X%%:......      z 754, x 196..203: the Starly trigger row
 755  ....:%%%S%::......
 756  ....::%LL%:.......
 757  ======LL==========      -> the stock x 214 stairs up to the middle section
 758  =====LL===========
 759  ===CCC============
 760  ===CCC============
```

## Art

Everything comes from stock set-006 texels. Most of it is a palette swap; only two small decals are new.

| surface | texels | palette | lit |
|---|---|---|---|
| scorched ground | `criff` 16x16, a random flip/rotation per tile | `r203_ash` (new) | yes |
| scorch blots at the ash/grass edge | `r203_scorch` 32x32, new, colour 0 transparent | `r203_scorch_pl` | yes |
| violet cracks | `r203_crack` 32x32, new, colour 0 transparent | `r203_crack_pl` | no: it glows at night |
| fissure walls | `criffp` | `r203_rockv` (new) | yes |
| fissure floor | `asasea`; keeps the stock fldtanime ripple | `r203_rift` (new) | no |
| fallen trunk | `nbridge` wood grain | `r203_bark` (new) | yes |
| fallen crown, root plate | `tree01` | `r203_dead` / `r203_char` (new) | yes |
| charred tree | `tree01` | `r203_char` | yes |
| trees, grass, tall grass, shadows, boulder | stock | stock | yes |

Set 006 is shared by 12 overworld headers (Twinleaf, Sandgem, Jubilife, Routes 201-204S, 219-221, Verity
Lakefront). The additions cost 1248 B of VRAM (46544 -> 47792 B, the largest stock set is 76416). Stock entries are
asserted byte-identical, so those maps don't change.

The fissure is built from eighth-tile cells along a jittered, Chaikin-smoothed polyline through the X tiles. Open
cells get the floor at h -0.9; closed cells get ash. Walls are added only on the edges the fixed field camera can see:
the north, east and west sides of an opening. The decals sit 0.03 to 0.08 tiles above the ground.

Budgets: chunk 019 goes from 500 to about 930 polygons and from 24992 to about 44 KB of model, against the 0xF000
land-data buffer. Stock Lake Verity chunks reach 1176 polygons.

## Events (events_route_203.json, scripts_route_203.s, route_203.json)

- Garius (local 5) at (211,747), facing the fissure. Coord script 6 sits at x 210, z 744..745
  (`VAR_UNK_0x4088 == 0`). He walks up 2-3 tiles, says the crack line, then the stock D10 rematch, battle,
  Yes/No, and "Race you to Oreburgh!". He then runs east, south down x 212 and east up the stairs, and is removed.
  This sets 0x4088 = 1 and progress = 14. A loss is the stock blackout, and the trigger re-arms.
- Starly (locals 17 and 18, hide flag `FLAG_UNK_0x0028`, map-local). Coord script 9 sits on row z 754, x 196..203
  (`VAR_MAP_LOCAL_0 == 0`). It plays a cry and "!", and they fly off over the fissure. This replays on every visit.
- Hiker (local 15) on the road west of the trunk, and Picnicker (local 16) on the scar's east side. These are new
  flavour lines.
- Michael moves to (205,745), facing west. The (211,750) Poke Ball moves to (205,755).
