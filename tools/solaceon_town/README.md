# Solaceon Town

## The redesign layout and graybox (Solaceon redesign, town-layout workstream)

The Sanctuary-town redesign (docs/solaceon_redesign/PLAN.md) rebuilds chunks 072/073 around the memorial wall. The
tile contract, exact tiles for every door, sign and NPC spot, budgets and open issues are in
`docs/solaceon_redesign/layout.md`. All tools read their stock inputs from git at `BASE_REV = 50482f890` (the stock
town with the memorial wall below), so reruns never feed back; output paths are the constants `MAP_DATA_DIR` /
`EVENTS_JSON` at the top of `layout.py`.

| file | what |
|---|---|
| `layout.py` | The tile contract: collision, height and kind per tile, rebuilt regions, anchors, signs, NPC spots. `--ascii`, `--anchors`, `--check`. |
| `collision.py` | Permissions and BDHC from layout.py (after tools/lake_verity/collision.py), and the checks against it. |
| `build_graybox.py` | Writes map_data_072/073: stock terrain outside the rebuilt regions byte for byte (chunkedit), graybox terrain inside from stock set-010 textures, the props (Day Care, PC, Mart kept; three houses moved; the gym door on the hall), permissions and BDHC. Dry run by default, `--preview DIR`, `--write` (refuses if a check fails). |
| `warps.py` | Moves the warps to layout.DOORS (x/z only, never reorders). `--write`. |
| `dump_stock.py` | Stock 072/073 + neighbours to mesh.json, set-010 textures to PNG, a stock report. |
| `preview.py` | blender_preview.py with Solaceon's real field camera (CAMERA_TYPE_DEFAULT); `SOL_PREVIEW_ENGINE=cycles` for a CPU render. |
| `render.py` | Runs Blender for the top view and the game views (north, plaza, compound, dig, kennel, south). |
| `compare_layout.py` | Layout colours / render / render with blocked tiles darkened, side by side. |

```
python3 tools/solaceon_town/layout.py --ascii --check
python3 tools/solaceon_town/build_graybox.py --write
python3 tools/solaceon_town/warps.py --write
```

## The art pass (town-art workstream)

`build_art.py` replaces the graybox with the final art (docs/solaceon_redesign/art.md section 6): the same tile
contract, props, permissions and BDHC, with the hall, compound, tent, plaza furniture, excavation and kennel built from
the set-010 kit, plus the kit append to set 010 and the sol_candle fldtanime entry. It supersedes build_graybox.py's
output (rerunning build_graybox.py --write would put the graybox back).

| file | what |
|---|---|
| `build_art.py` | Writes map_data_072/073 (to `res/field/mapmodels/data/`), set 010 (`textures_kit.SET_REL`) and fldtanime.narc. Dry run by default, `--preview DIR` (DIR/art/), `--write` (refuses if a check fails; idempotent). |
| `art_test.py` | Headless in-game test on the macOS app: screenshots of 12 spots by day and night, the candle animation, the hall door in and out, both seams. `--skip-route-209` while Route 209's OnTransition loops. |
| `render.py --art` | Field-camera renders of the art preview (views north, tent, wall, garden, gate, forecourt, door, gap, yard, southexit, ...). |
| `textures_kit.py` | The kit append (now driven by build_art.py; still runs alone as a dry run). |
| `art/paint_kit.py` | Paints the kit (town-art changed sol_emblem to the 3x3 toned-down inlay, sol_hroof to the ridge-to-eave gradient, softened sol_ruts and cut sol_truck). |

```
python3 tools/solaceon_town/build_art.py --preview "/tmp/Solaceon Update/art_mac"
python3 tools/solaceon_town/render.py "/tmp/Solaceon Update/art_mac" --art --cycles
python3 tools/solaceon_town/build_art.py --write
tools/macos/build.sh dev
python3 tools/solaceon_town/art_test.py build_macos "/tmp/Solaceon Update/art_mac/game" --night --skip-route-209
```

The graybox notes below describe the layout pass, which the art keeps. `textures.py` and
`build_wall.py` below are the earlier Arc 2 wall edit; their output is part of BASE_REV and is kept by the graybox
(do not rerun build_wall.py over the graybox: it rebuilds 072 from the older stock).

# The memorial wall (Arc 2)

Arc 2 round 3 (workstream world-art), plan S4 / scene 2.16a: Team Eclipse's memorial wall, "every photo labelled with a
name, a date and a place". s-celestic owns the scene and placed its five sign events on the white fence west of the
main road (`events_solaceon_town.json` on `a2/s-celestic`: x 556, z 652..656, read from x 557 facing west; Indra stands
at (557,654) in the cutaway). This tool builds the wall itself, as terrain, on exactly those tiles.

Only overworld chunk `map_data_072` (matrix cell 17,20: x 544..575, z 640..671) and texture set 010 change.
Permissions, BDHC, props and every other chunk are stock.

## Files

| file | what |
|---|---|
| `textures.py` | Appends `sol_wall` (128x16, five 16x16 cells of pixel art) and the `sol_stone` palette to set 010, append-only, rebuilt from `BASE_REV`. |
| `build_wall.py` | Builds `map_data_072` from the stock chunk at `BASE_REV`: drops the fence segment, adds the wall and its five boards. Prints budgets and checks; refuses `--write` if one fails. |

```
python3 tools/solaceon_town/textures.py --write
python3 tools/solaceon_town/build_wall.py --write
tools/macos/build.sh release
```

## What it looks like

```
      x 550 ....... 555 556 557 558..562
 651  F F F F F F F F  #   .   road        F  stock picket fence of the flower pen (stays)
 652  .  flowers  .    P   r   road        P  board: photo cards              (sign 652: photos)
 653  .           .    D   r   road        D  board: a child's Ponyta drawing (sign 653)
 654  .           .    E   r   road        E  board: one card, ELIAS          (sign 654); Indra's spot is (557,654)
 655  .           .    B   r   road        B  the violet Eclipse banner       (sign 655)
 656  F F F F F F F F  T   r   road        T  board: Teo's new card, shiny pin (sign 656)
                                           r  reading tiles (walk), x 557
```

- The stock picket fence along x 556 (a flat strip at h 1.375 plus two corner posts) is dropped; the pen's east-west
  fences stay and end against the wall.
- A low stone wall (stock `blueglay` texels, new `sol_stone` palette, warm grey), x 556.06..556.94, z 651.55..656.8,
  0.55 tiles high.
- Five boards stand on it, one per sign tile, in stone frames, leaning back 40 degrees so the fixed camera and the
  road both see them. Like the stock north-south fences (drawn as flat strips), they are drawn for the camera rather
  than literally on the wall's east face.
- All lit like stock. Set 010 grows by 1072 B of VRAM (44880 -> 45952 B). Chunk 072: 426 -> 436 polygons,
  20568 -> 21360 B of model.

## Not done here

- Teo's card is terrain, so it is on the wall in every story state (the sign only reads from state 49). A card that
  appears when Indra pins it would need an object event (s-celestic's file), not map data.
