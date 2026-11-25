# Solaceon redesign: texture kit (textures workstream)

The kit holds 26 entries for set 010: 24 new textures and 2 palette-only recolours of stock set-010 texels. It is
built to look like it shipped with Platinum, and it fits the PLAN.md budget of +24 KB with about 11 KB to spare.
The town-art pass (section 6) applied it: `tools/solaceon_town/build_art.py --write` builds set 010 through
`textures_kit.build` together with the final chunks 072/073 and the candle animation. Town-art changed three
entries (the 3x3 toned-down emblem, the roof gradient, softer ruts) and dropped `sol_truck`.

![kit](art/kit_sheet.png)

## 1. The stock look (set 010 and Solaceon's buildings)

`tools/solaceon_town/art/decode_stock.py` decodes set 010 at `50482f890` (63 textures, 60 palettes,
44544 + 1408 = 45952 B VRAM). It also decodes the building texture sets of four towns, which are the
areabm_texset of each town's area. It measures texel density on chunks 072/073 and on the stock buildings.
Contact sheet: [art/stock_set010_sheet.png](art/stock_set010_sheet.png).

**Set 010 holds terrain only.** Every Solaceon building (the Pokemon Center `pc`, the Mart `fs`, the house `t4_h01`,
the Day Care `t4_s01`, and their doors) is a map prop. Each prop takes its textures from **areabm_texset 6**
(39120 B), not from set 010, and a terrain material cannot bind a prop texture. A terrain Sanctuary hall therefore
needs its wall, roof and door textures in set 010. That is why the kit exists.

| area | town | map set | props list (building textures) |
|---|---|---|---|
| 0xA | Solaceon (also Celestic, R209/210/211E/215) | 010 | 6: pc, fs, t4_h01, t4_s01, r209s01 (Lost Tower), t5_* (Celestic), c4_h01a, ... |
| 0x8 | Eterna | 008 | 4: t3_h01, t3_s01, c4_s01..04, d2_s01/02 (Galactic bldg), d4_s01, ... |
| 0x9 | Hearthome | 009 | 5: c5_h01, c5_s01, c5_b01, c5_s03 (contest hall), c1_s03, ... |
| 0xB | Veilstone | 011 | 7: c7_h01, c7_s01..04, souko (warehouse), container, parabola/para_asi (dish truss), ... |

**Texel density.** Ground is 16 texels per tile everywhere, measured as 16.0 on ngrass, nsand, lgreen, nhana and
tshadow in 072/073. Cliff faces run 22 to 24 (criffp). House walls are 16 (t4_h01_a), with 14 to 25 on the PC and
Mart. Roof slopes are lower, 6 to 13, because the roof atlases are stretched. Building atlases are a single 64x64
per building, plus the shared `h_mado` (pltt4 window glass) and `h_kage` (pltt4 shadow, drawn translucent by its
material). **The kit uses 16 texels per tile throughout.** Small cards (windows, plaque, pilasters) land at 20 to 26.

**Palettes.** The overworld is very light and saturated. Grass is (82,255,148) and (74,246,139). The sand road is
(255,230,156) to (255,238,180). Paving (blueglay) is a lilac grey, (172,180,189) to (197,205,222). Building palettes
run darker. The houses share an outline pair: ink (49,49,41) and (82,74,74). Ground textures use only 3 to 10
colours. Building atlases use 13 to 16.

**Dithering.** Ground uses a sparse 2-tone checker between two close tones (blueglay is pure checker with a few 2x2
blots) plus small repeated motifs: ngrass tufts, nhana flowers. Building textures are **not dithered**. They use
flat fills with 1 px highlight and shadow lines.

**Outlines.** Building parts have no black outline around the silhouette. Ink appears only inside shapes: door and
window frames, joints, the dark under-roof line. Small terrain props such as the imped pickets have no outline at
all.

**How stock draws each part:**
- **Roofs:** rows of round or scalloped tiles 4 to 8 px tall. Each row has a dark line under the row above (t3_h01).
  Alternatively, flat bands with a highlight strip (pcloof, fsloof).
- **Walls:** flat panels with 1 px courses (t4_h01 logs, r209s01 Lost Tower stone with a carved relief and
  lilac/violet stripes).
- **Fences:** imped, white pickets 4 px wide on an 8 px pitch, 3 tones.
- **Paving:** blueglay / blueglayp, 16x16 / 32x32, low-contrast checker.
- **Steps:** newstep, 4 treads per 2 tiles, with wooden cheeks.

**Stock textures to reuse as-is** (already in set 010, no VRAM cost):
- ground: `ngrass`, `nsand` / `nsandp` (road + edge), `lgreen` / `lgreenp`, `tshadow`
- flower beds: `nhana`, `shana`, `rhana`, `plant2` (planter)
- garden of names grass: `l_grass_d/m/u` (tall grass) and `nhana`
- paving: `blueglay` / `blueglayp`
- fence: `imped` (the white picket fence plus rocks and bushes)
- steps: `newstep`
- cliffs and the Ruins hill: `criff`, `criffp`, `criffp2/3`, `wcliff`, `enccliff`
- cave mouth: `dhole`, `dhole_05`
- planks: `bridge` / `nbridge` (used on the scaffold decks in the mock)
- trees: `tree2_01`, `conttree*`, `g1_treea`
- shadow: `shadowchip`, a flat (65,65,74) that makes a cheap translucent building shadow with a material alpha of
  about 12

## 2. The kit

All colours come from stock palettes that Solaceon already shows: set 010 or the Solaceon / Eterna / Hearthome /
Veilstone building sets. `tools/solaceon_town/art/palette.py` names every colour and its source. Only five are
blends (palette.DERIVED): two violet shades for roof shadow and glint, the eclipse disc, its rim, and a corona
flash. The main sources:
- pale stone and lilac: the Lost Tower, `r209s01_a`
- violet: Eterna house walls, `t3_h01`
- gold: Veilstone containers
- wood: the Solaceon house `t4_h01_a` and the Day Care `t4_s01_a/c`
- warm light: the PC roof oranges
- steel: the Veilstone dish truss
- plaza: Hearthome beige, `c5_s03_a`

`sol_steps` and `sol_spoil` are stock set-010 texels (`newstep`, `criffp`) with new palettes. That is the memorial
wall's blueglay -> sol_stone trick, and each costs 24 to 32 B.

Bytes are as `textures_kit.py` builds them: palettes are trimmed to the highest index each texture uses, the same as
`nsbtx.encode_texture`. `paint_kit.py` prints the conservative 32 B per palette figure, 15304 B in total.

| texture | group | format | size | frames | texel B | pal B | repeat | c0 | what / UV rule (16 texels per tile) |
|---|---|---|---|---|---|---|---|---|---|
| sol_hwall | hall | pltt16 | 32x32 | 1 | 512 | 16 | s t | 0 | pale ashlar, 16x8 blocks; hall walls and the compound wall |
| sol_hroof | hall | pltt16 | 32x32 | 1 | 512 | 16 | s | 0 | violet round tiles in 4 rows that darken from the ridge (v 0) to the eave (v 1), the stock light-to-dark roof band; v maps once across the whole slope (about 12 texels per tile down a 2.7-tile slope, inside the stock roof range 6 to 13); u 2 tiles per repeat |
| sol_htrim | hall | pltt16 | 32x32 | 1 | 512 | 32 | s | 0 | 4 bands of 8 px (0.5 tile): v 0-.25 ridge cap, .25-.5 eave tile ends over a gold fascia, .5-.75 lilac plinth, .75-1 violet coping |
| sol_hatlas | hall | pltt16 | 64x64 | 1 | 2048 | 32 | - | 0 | double door with eclipse (0,0 32x32 = 2x2 tiles); arched lit window (32,0 16x32); oculus (48,0); plaque (48,16); pilaster (0,32 16x32: capital rows 0-7, shaft 8-23 may stretch, base 24-31); gable medallion (16,32 32x16); sign board (16,48 32x16); gate post (48,32 16x32) |
| sol_gate | hall | pltt4 | 32x32 | 1 | 256 | 8 | s | 1 | iron bars, gold spear tips and rings, see-through; gate leaves or railings |
| sol_steps | hall | pltt16 | (newstep 32x32) | 1 | 0 | 24 | t | 0 | **palette only**: stock newstep + palette sol_steps (pale stone treads, lilac cheeks) |
| sol_fcpave | forecourt | pltt16 | 32x32 | 1 | 512 | 16 | s t | 0 | forecourt flags, one per tile, blueglay-style checker |
| sol_emblem | forecourt | pltt16 | 32x32 | 1 | 512 | 32 | - | 0 | quadrant (texels 0..23 = 1.5 tiles) of the **3x3-tile**, toned-down eclipse inlay: slate disc, thin gold ring, 8 thin gold rays and 8 short lilac ones, a faint lilac corona, a carved lilac double ring, the forecourt flags showing through; texels 24..31 mirror it. Drawn as 4 quads with mirrored UVs (no flip material) |
| sol_plaza | plaza | pltt16 | 32x32 | 1 | 512 | 16 | s t | 0 | warm beige setts, 4 per tile, running bond |
| sol_border | plaza | pltt16 | 32x16 | 1 | 256 | 32 | s | 0 | garden-of-names edge strip 2x1 tiles: grass + flowers (v 0), kerb stones with name lines, kerb shadow (v 1) |
| sol_furn | plaza | pltt16 | 32x32 | 1 | 512 | 32 | - | 1 | bench side (0,0 24x12 = 1.5x0.75 t), bench top (0,12 24x8), memorial card board (0,20 24x12), lantern post with lit lamp (24,0 8x32 = 0.5x2 t) |
| sol_offer | plaza | pltt16 | 32x32 | 1 | 512 | 32 | - | 1 | four 1x1 cards: lilies in violet paper, posy, wreath on easel, lit candles before a photo |
| sol_banner | plaza | pltt16 | 16x32 | 1 | 256 | 24 | - | 1 | violet Eclipse banner on its post, card 1x2 tiles |
| sol_candle | plaza | pltt16 | 16x16 | 3 | 128 | 16 | - | 1 | candle dish card; frames sol_candle.1..3 for fldtanime (6 VBlanks per frame) |
| sol_canvas | tent | pltt16 | 32x32 | 1 | 512 | 16 | s t | 0 | cream / pale-lilac pilgrim canvas, 2 panels per tile |
| sol_awning | tent | pltt16 | 32x16 | 1 | 256 | 16 | s | 1 | violet/cream striped valance, scalloped see-through lower edge |
| sol_tent | tent | pltt16 | 32x32 | 1 | 512 | 32 | - | 0 | table top with name cards and the open registry ledger (v 0-.5), front cloth with eclipse (.5-.75), REGISTRY board (.75-1) |
| sol_scaff | excavation | pltt16 | 32x32 | 1 | 512 | 24 | s t | 1 | scaffold face: a standard per tile, ledger, X brace, plank deck + toe board, see-through |
| sol_wfence | excavation | pltt16 | 32x16 | 1 | 256 | 16 | s | 1 | warning fence, yellow/black rails, red caps, see-through |
| sol_tarp | excavation | pltt16 | 32x32 | 1 | 512 | 16 | s t | 0 | blue tarp with folds |
| sol_exatlas | excavation | pltt16 | 64x32 | 1 | 1024 | 32 | - | 1 | work light (0,0 16x32), crate side / top (16,0 / 16,16), cable coil (32,0), cable run (32,16 16x8), sandbags (32,24), KEEP OUT board (48,0 16x32) |
| sol_spoil | excavation | pltt16 | (criffp 32x32) | 1 | 0 | 32 | s t | 0 | **palette only**: stock criffp + palette sol_spoil (raw-earth browns): pit face, spoil heap |
| sol_kwall | ranch | pltt16 | 32x32 | 1 | 512 | 24 | s | 0 | kennel front: Day Care boards, one arched kennel + name plate per 2 tiles, concrete footing; rows 0-8 alone = plain boards for sides |
| sol_kroof | ranch | pltt16 | 32x16 | 1 | 256 | 16 | s t | 0 | corrugated sheet in the Day Care roof green, ridges down the slope (t) |
| sol_yard | ranch | pltt16 | 32x32 | 1 | 512 | 16 | s t | 0 | packed yard dirt (darker than the road) |
| sol_ruts | ranch | pltt16 | 32x32 | 1 | 512 | 16 | s t | 0 | yard lane 2 tiles wide: same dirt, two soft tyre ruts (checker-edged pressed bands, sparse tread marks) 1 tile apart along t |
| **total** | | | | | **12416** | **584** | | | **13000 B** |

`sol_truck` (2080 B) was cut by town-art: the truck has to vanish in some story bands, so the bay gets ground and
ruts only and the story scripts put crate objects there.

**VRAM:** set 010 goes from 45952 B to **58992 B** (+13040 B with alignment; texels 44544 -> 56960, palettes
1408 -> 2032). The budget is +24576 B, and the set stays below the 76416 B proven ceiling of set 048. The set grows
from 63 to 87 textures and from 60 to 86 palettes. For scale: Solaceon's building textures, areabm_texset 6, take
another 39120 B in the same texture VRAM bank.

**Stretch items, cut first** (`textures_kit.STRETCH`): sol_ruts 528 B, sol_candle 144 B (fldtanime), sol_tarp
528 B and sol_border 288 B (sol_truck is already cut). Cutting all four saves about 1.5 KB. After those, sol_hatlas is
the biggest single item. Its regions could drop to 32x64, losing the gate post and the sign, which saves about
1 KB.

### Material rules for town-art

- Map materials as stock: lit (`poly_attr 0x001f8081`), back-face culled. The see-through c0 textures (gate, scaff,
  wfence, awning, furn, offer, banner, candle, exatlas) want `cull none` where both sides show.
  - The kit bakes light only into small accents: lit window glass, lamps, candle flames, the gold flash. It all
    follows the area light like stock.
- **Emblem (as applied, 3x3):** four quads over layout.EMBLEM (x 579..581, z 654..656), split at the centre
  (580.5, 655.5): NW u 0..0.75 / v 0..0.75, NE u 0.75..0, SW v 0.75..0, SE both mirrored; no repeat, no flip. The
  sol_fcpave UV origin is the emblem's NW corner (`u = (x - 579) / 2, v = (z - 654) / 2`), the rule above with a
  3x3 inlay whose edges fall on tile edges, so its flags and the forecourt's line up. (The 4x4 version needed a
  half-tile offset and a flip material; neither is used now.)
- **Palette-only entries:**
  - `sol_steps`: texture `newstep`, palette `sol_steps`
  - `sol_spoil`: texture `criffp`, palette `sol_spoil`
- Bands (sol_htrim, sol_tent, sol_kwall rows) are picked by v range; keep a 1/64 inset at band edges to avoid
  bleeding into the next band.
- **sol_candle animation:** append a fldtanime entry the way `build_art.py` / `tools/coronet_lava/add_lava_anim.py`
  do. Use texture name `sol_candle`, frames `sol_candle.1..3` (all three share one palette and index layout) and
  6 VBlanks per frame. Without the entry, the candle shows frame 1, still.
- **Tent orientation:** the field camera looks north at 55 degrees, so an open side only reads if it faces south. A
  table under a valance is hidden unless the valance bottom is at least about 1.4 tiles up and the table sits near
  the front (see the mock).

## 3. Previews

All previews are in `/tmp/Solaceon Update/textures/`. `~/Documents` cannot be written from these sessions;
`common.preview_dir()` uses `$SOL_PREVIEW_DIR` or `~/Documents/Solaceon Update/textures` when writable.

| file | what |
|---|---|
| `stock_set010_sheet.png`, `stock_set010_palettes.png`, `stock_set010/` | stock set 010, labelled, PNG + JSON per texture |
| `stock_props_{solaceon,eterna,hearthome,veilstone}_sheet.png` + dirs | stock building textures of those towns |
| `stock_density.txt` | density and extent table, area / props lists |
| `kit_sheet.png`, `kit_table.txt` | the kit, labelled |
| `kit_from_set/` | the kit decoded back out of the built set (`textures_kit.py --preview`); identical to the assets |
| `render/street_game.png` | **mock street**: the stock Pokemon Center beside the graybox Sanctuary hall wearing the kit |
| `render/hall_game.png` | hall front, forecourt emblem, compound wall, gate posts, open gate, banners, lanterns |
| `render/plaza_game.png` | memorial plaza: setts, benches, lanterns, card board, offerings, candles, garden of names with border |
| `render/tent_game.png` | registration tent (open front, table with ledger and cards, REGISTRY board) |
| `render/dig_game.png` | excavation: stock cliff and cave mouth, scaffold, warning fence, work lights, KEEP OUT, tarp pile, crates, cable, spoil heap |
| `render/ranch_game.png` | kennel block (green corrugated roof), yard and ruts, the truck |
| `render/street_top.png` | the whole mock from above, 16 px per tile |
| `render/street_lit_game.png`, `render/hall_lit_game.png` | the same with a sun (`--lit`) |

Copies in this repo: [art/street_game.png](art/street_game.png), [art/hall_game.png](art/hall_game.png),
[art/street_top.png](art/street_top.png). The game-camera renders are at half size.

![street](art/street_game.png)

**The mock** (`preview_kit.py`) is a test scene, not the town layout. The hall is 9x5 tiles (x 21..30, z 2.5..7.5)
with 2.5-tile walls and a hip roof ridged at 4.0. A front bay x 23..28 has 3.0-tile walls and a gable to 4.75. That
makes the hall about 4 tiles tall next to the Pokemon Center's 3.9. The bay holds the 2x2 door, the sign board above
it and the medallion in the gable. Pilasters are 0.75 tiles wide; windows are 0.8 x 1.55. The stock PC (prop 4 + door
70) and a Solaceon house (197 + door 246) are placed with the same prop offsets as in chunk 072, using their stock
textures. Every kit texture appears in the mock (the script checks this).

## 4. Rerun

```
python3 tools/solaceon_town/art/decode_stock.py          # stock sheets, density (about 5 s)
python3 tools/solaceon_town/art/paint_kit.py --sheet     # paints + exports tools/solaceon_town/assets/textures/
python3 tools/solaceon_town/textures_kit.py              # dry run: checks, table, VRAM (writes nothing)
python3 tools/solaceon_town/textures_kit.py --preview "/tmp/Solaceon Update/textures/kit_from_set"
python3 tools/solaceon_town/art/preview_kit.py [--lit] [--views street,hall,plaza,tent,dig,ranch,top]
# town-art, when applying the kit:
python3 tools/solaceon_town/textures_kit.py --write      # refuses if any check fails
```

- Everything is standard-library Python. The paint scripts are deterministic (seeded), and re-running gives
  byte-identical PNGs.
- `preview_kit.py` runs Blender through `art/blender_cpu.py`, which is `blender_preview.py` on Cycles CPU. EEVEE
  needs Metal shader compilation, and that crashes in sandboxed sessions. It needs a session where Blender may run
  unsandboxed.
- `textures_kit.SET_REL` is the one place the output path lives. On the macOS app branch (`solaceon-mac`), set 010
  is `res/field/mapmodels/texture_sets/map_texture_set_010.nsbtx`; the bytes are identical.

## 5. Open questions

- **Platinum feel** (judged from renders only, not on hardware):
  - (Resolved by town-art) the emblem is 3x3 and toned down; the roof has the ridge-to-eave gradient; the truck is
    cut.
- Checked in game by town-art (section 6): the sol_candle fldtanime entry animates (two screenshots 10 frames apart
  differ); the baked warm accents (windows, lamps) darken at night with everything else, as lit materials do.
- Banners: the moving Eclipse banners are object events. `sol_banner` should match their colours, but I have not
  compared it against the object sprite.
- The hall here is a graybox of my own. Its real footprint, heights and door tile come from the town-layout
  workstream, and the UV rules above work for any layout.

## 6. The town-art pass (applied; town-art workstream)

`tools/solaceon_town/build_art.py` turns the graybox into the final map_data_072/073 and applies the kit. It reads its
stock inputs from git at `BASE_REV = 50482f890` (chunks, set 010, build models, area data) and the kit from
`tools/solaceon_town/assets/textures/`, so reruns never feed back; a second `--write` is byte-identical.

```
python3 tools/solaceon_town/build_art.py                     # dry run: budgets + every check
python3 tools/solaceon_town/build_art.py --preview OUT       # OUT/art/: decoded chunk meshes, props, textures
python3 tools/solaceon_town/render.py OUT --art --cycles     # OUT/art_top.png + art_<view>_game.png (field camera)
python3 tools/solaceon_town/build_art.py --write             # map_data_072/073, set 010, fldtanime.narc
tools/macos/build.sh dev
python3 tools/solaceon_town/art_test.py build_macos OUT/game --night --skip-route-209   # in-game screenshots
```

It writes `res/field/mapmodels/data/map_data_072.bin` / `073.bin` (`OUT_MAP_DIR`), set 010 at
`textures_kit.SET_REL` (`res/field/mapmodels/texture_sets/`) and `res/prebuilt/data/fldtanime.narc`. The tile
contract is untouched: permissions and BDHC come from collision.py, the props are the graybox's (Day Care, PC, Mart,
three t4_h01 houses, the gym door 298 on the hall door), and the builder checks all of it.

![hall](art/game_day_07_hall_door.png)

### What it builds

Stock terrain outside `layout.REBUILD` stays byte for byte (the Day Care ranch with the memorial wall, untouched;
build_wall.py is not rerun; and the Ruins hill). Inside, everything is new, lit like stock and back-face culled
except the see-through cards (`<kit>_2s` materials, cull none):

- **Ground:** stock `ngrass`, `nsand`, the stock road-edge mapping of `nsandp`, stock `l_grass_u/m/d` tall grass;
  `sol_plaza` setts on the plaza and in front of the Pokemon Center; inside the compound a paved forecourt
  (`sol_fcpave`, x 575..585, z 653..657, UV origin on the emblem's NW corner) between lawns (`ngrass`) with two
  `nhana` flower beds; the 3x3 `sol_emblem` inlay (four quads); `sol_yard` dirt for the dig, the kennel block and the
  loading yard; the `sol_ruts` lane (2 tiles wide, z 666..668) from the truck bay's west end (x 550) to the road
  verge (x 557). No truck: the bay is ground and ruts only, for story crate objects.
- **Sanctuary hall** (footprint x 576..584, z 648..652): body x 576.1..584.9 from z 648.15; wing fronts at
  z 651.45, 2.5 tiles of pale ashlar on a 0.5-tile lilac plinth, corner pilasters, one lit arched window per wing;
  the front bay x 578.6..582.4 flush with the gym door prop (z 651.98 vs the prop's 652.0), walls 3.5, the opening
  behind the door dark (seen when it slides), pilasters either side, the sign board above the door and the
  medallion in the gable (apex 5.0 tiles, ridge cap 5.1, taller than a house's 4.7); a violet hip roof (eaves 2.5,
  ridge 4.0, 0.3 overhang, gold eave fascia, ridge cap) with the bay's gable roof running back into it. The
  blocked door row carries steps across the bay (`sol_steps`, two treads) and 0.4-tile flower planters (lilac
  plinth, `nhana` top) in front of the wings.
- **Compound:** a 0.95-tile wall (ashlar to 0.55, violet coping band and top) on the layout ring; iron railings
  (`sol_gate`, gold spear tips) on the street-side wall either side of the gate; gate pillars (the `sol_hatlas` gate
  post on three faces, coping caps); the gate itself stands open; forecourt lanterns; Eclipse supply crates
  (`sol_exatlas`) in the west yard.
- **Pilgrim road:** the four banner posts (`sol_banner` cards leaning back 18 degrees, like stock props lean toward
  the camera); the registration booth, open-topped so the TENT_CLERK object at (566,643) is visible (a pitched roof
  over the clerk sat on the camera's sight lines and hid the sprite; `clerk_sight_check` now guards this): canvas back
  just inside the fence row with a ridged cap leaning back over it, side walls whose tops fall toward the front, the
  striped valance across the open south front with its bottom 1.45 tiles up, front poles on the table row's edge, the table (ledger and cards on top, eclipse front cloth),
  record boxes either side of the clerk and the REGISTRY board over the valance; the tent sign is the `sol_hatlas`
  sign board on a post.
- **Plaza:** lanterns (`sol_furn`, 2 tiles, leaning 14 degrees so they do not cover the tile behind), the bench along
  x 563 facing the wall (slatted seat, backrest, end boards), offerings at both ends of the wall (wreath / photo
  cards 1 tile tall, lilies / posy, and the animated `sol_candle` dish), the memorial plaque lectern, the kerb with
  name lines along the garden's plaza side.
- **Excavation:** scaffold faces and ends along the cliff (the west deck under a blue tarp, the east one planks),
  work lights, the warning fence on z 659 with the gap, the KEEP OUT board on the warning-sign tile, a crate stack,
  a spoil heap (`sol_spoil`), a cable and sandbags as ground decals.
- **Ranch:** the kennel block (boards with one arched kennel per stall, the arch centred on each stall tile), a
  mono-pitch green corrugated roof, board dividers, the kennel sign plaque; stock picket fences around the yard.
- Stock-style trees (the 4 quads of a stock tree2_01 tree) and picket fences (imped) as in the graybox.

**Lighting:** every new material is lit (stock map attributes), so it follows the time-of-day light. Light is baked
only into small texture accents (window glass, lamp heads, candle flames), which darken at night with everything else
(see `art/game_night_07_hall_door.png`); the stock houses' night-lit windows are a prop feature the terrain does not
have.

**Candle animation:** fldtanime entry `sol_candle` (3 frames x 6 VBlanks), added or replaced by name in the work
tree's archive (entry 55 / member 56 on this branch). Its frames are checked to share the base texture's palette,
size and (frame 1) texels. After merging another branch that also appends to fldtanime, rerun `build_art.py --write`.

### Budgets (as written)

| chunk | polygons | stock kept | new | verts sent | model B | BDHC B | materials | props |
|---|---|---|---|---|---|---|---|---|
| 072 | 418 | 165 | 253 | 1670 | 26212 | 66 | 47 | 8 (391 polygons) |
| 073 | 765 | 479 | 286 | 2609 | 38320 | 172 | 35 | 5 (188 polygons) |

Limits: 1000 polygons and 45 KB (46080 B) of model per chunk, hard 0xF000. On screen (terrain of every loaded chunk
incl. 068/074/filler plus all props, frustum + back-face culling at every walkable tile): worst 343 polygons with
CAMERA_TYPE_DEFAULT and 354 with the zoomed-in camera; limit 2048. Set 010: 45952 -> 58992 B (+13040 B of the
+24576 B budget; ceiling 76416 B), 26 kit entries, stock textures and palettes unchanged.

### Checks (`--write` refuses on any FAIL)

Permissions and BDHC equal layout.py in both chunks; all 93 layout checks (anchors, seams, edges, signs, NPC spots,
reachability); every door tile has a building behind it and a door prop on it; props in area 0xA's list and identical
to the graybox's; untouched stock shapes and all stock materials byte-identical; every walkable rebuilt tile is drawn
at its layout height; nothing solid is drawn inside a walkable tile below 1.3 tiles (stock tree overhangs aside); no
tent face lies on the camera's sight lines to the tent clerk's sprite;
polygon / model / on-screen budgets; set 010 kit budget, ceiling and stock-unchanged checks (textures_kit.build); every
kit entry is used by the town; the candle frames' palette, size and texels.

### Verification

- **Renders** through the game camera (Cycles CPU): `/tmp/Solaceon Update/art_mac/art_top.png` and
  `art_{northroad,tent,wall,garden,gate,forecourt,door,gap,yard,southexit}_game.png`.
- **In game** (`tools/solaceon_town/art_test.py`, SIM_CONTROL=stdio, the Eterna Forest test save, warps): day (12:00)
  and night (22:00, SIM_FIXED_RTC) screenshots of 12 spots in `/tmp/Solaceon Update/art_mac/game/`; the candle
  changes between two frames; the player walks into the hall door (MAP_HEADER_SOLACEON_SANCTUARY, arrival (10,19))
  and back out to (580,652); across the north seam into Route 210 South and back, and the seam columns x 557 / 563.
  Copies of six top screens are in `art/game_*.png`.
- **Route 209:** on this branch every entry to Route 209 hangs (its `Route209_OnTransition` ends in
  `GoTo Route209_OnTransition`, a loop; it reproduces on the lead's build of 35c1c69f6, so it is not the art). With a
  temporary local fix (`GoTo Route209_OnTransitionStock`, reverted, not committed) the south seam was walked both ways
  and on x 557 / 563, day and night: `/tmp/Solaceon Update/art_mac/game/route209_crossing_tempfix/`. The committed
  test uses `--skip-route-209` (walks onto the seam row z 671) until the script is fixed.
- **walkcheck** (`tools/qa/walkcheck.py --map MAP_HEADER_SOLACEON_TOWN`, run on a shim tree with the devserver
  paths, since the tool reads `include/data/map_headers.h` and `res/field/maps/data`): 0 HIGH; against the graybox
  56 findings resolved and none new apart from 6 low-obstacle tiles, allowlisted with reasons in
  `tools/qa/walkcheck_allow.json` (the two hall planters on the blocked door row, the four warning-fence tiles).

### Open issues

- The stock gym door prop (298) is blue; it reads as glass doors in the pale facade, but the kit's violet double door
  (`sol_hatlas` 0,0 32x32, 512 B) is unused. A violet door needs its own door prop (a build model), not terrain,
  because the door must animate.
- The Eclipse banners on the four posts are terrain, so they stay in every band (also postgame); the Rowan banners
  that come down in band C are separate signboard objects.
- Lamps and windows do not glow at night (lit materials). An unlit lamp-head card per lantern would glow, at one
  more material per chunk.
- The memorial plaque lectern is terrain in every band (its text is band F only).
- `tools/qa/walkcheck.py` cannot read the macOS tree directly (paths); a shim tree was used.
