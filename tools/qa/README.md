# QA walkability-vs-graphics checker (`walkcheck.py`)

Compares what is *drawn* (chunk model faces, chunk props, DW ghost props)
against what the *collision* says (the permissions grid for the floor,
the `tw_arc_attr` grids for DW walls/ceilings) and reports tiles where
the two disagree. Catches the Route 214 class of bug -- 74 floor tiles
drawn as plain cobble whose collision was `0x8000` (blocked) -- that
every headless test missed because they only walked solution routes.

Standard library plus the repo's own modules only.

## Usage

```sh
python3 tools/qa/walkcheck.py --map MAP_HEADER_ROUTE_214
python3 tools/qa/walkcheck.py --map 293 --region 8,5,55,31
python3 tools/qa/walkcheck.py --all-dw            # the custom DW maps (QA gate)
python3 tools/qa/walkcheck.py --all               # every map with a matrix
python3 tools/qa/walkcheck.py --map MAP_HEADER_DW_ROUTE_214 --diff /path/to/other/tree
```

- `--map`: a `MAP_HEADER_*` name (the `MAP_HEADER_` prefix is optional),
  a matrix id (e.g. `293`), or `map_matrix_293`. Repeatable.
- `--region x0,z0,x1,z1`: only check that tile rectangle.
- `--rom-tree <path>`: check a different checkout (default: this repo).
  `--diff <other tree>` compares the two checkouts and reports
  mismatches added/fixed by the current tree.
- `--out-dir <dir>`: JSON report + overlay PNGs (default `walkcheck_out`).
- `--allowlist <path>`: allowlist JSON (default
  `tools/qa/walkcheck_allow.json` in `--rom-tree`).
- `--no-png`: skip overlay PNGs.

Exit code is 1 if any HIGH-severity mismatch exists, so QA can gate on
it. A one-line summary is printed per map.

## Outputs

- `walkcheck.json`: per-map counts plus a tile list with coords,
  surface, class, severity, drawn/collision classification and evidence.
- `<MAP>.png`: per-map overlay PNG, top-down, colour-coded, with a
  legend (green = drawn floor/walkable, red = HIGH looks-walkable-but-
  blocked, yellow = HIGH looks-blocked-but-walkable, blue = water,
  magenta = HIGH water mismatch, orange = tall obstacle/blocked,
  grey = raised/stairs, dark blue = void/blocked). DW maps also get
  `<MAP>_ceiling.png` and `<MAP>_wall.png` (wall: y top-to-bottom,
  z left-to-right).

## What each class means

| class | severity | meaning |
|---|---|---|
| `LOOKS_WALKABLE_BUT_BLOCKED` | HIGH | Drawn floor, nothing tall on the tile, no object, collision blocked. The Route 214 class and the main target. |
| `LOOKS_BLOCKED_BUT_WALKABLE` | HIGH | Drawn void/none, or a tall obstacle centred on the tile, but collision walkable. The "invisible floor" class (e.g. a DW ledge the player can walk through). On a DW wall, an undrawn walkable tile next to a drawn wall tile is MEDIUM (an edge/corner tile). |
| `WATER_MISMATCH` | HIGH | Drawn water with walkable non-water collision, or drawn floor with walkable water collision (surf) -- the player walks on drawn water, or surfs on drawn land. Drawn water that is blocked is decorative water and is not flagged. |
| `WATER_MISMATCH` (tall drawn, water collision) | MEDIUM | A tall obstacle drawn over a walkable water tile. |

A tile is *explained*, not a mismatch, when it holds an object
(`object_events`, including movement ranges -- MapObjects block through
the object system, so their perms need not be blocked), a warp tile, a
coord-event rect, a DW jump tile, or a DW ghost prop (any prop explains
a blocked tile; a stone-block prop, kind 23, on a walkable tile is
flagged). Allowlisted tiles are listed separately in the report and do
not gate the exit code.

## Drawn classification (floor surface)

From the chunk model faces, per tile, at the tile centre (DW
wall/ceiling faces use centre + subpoints, since wall faces end
mid-tile):

- `floor`: an upward face (`normal y > 0.7`) of a ground material, height
  in `[base-1.2, base+1.2]`, where `base` is the chunk's modal ground
  height (Jubilife chunks sit at h=1, Eterna Forest's at h=6). This
  generalises the Route 214 seed rule (upward face, normal y > 0.7,
  height in `[-0.6, 1.2]`, non-water material). Facade (`c\d+_f_*`) and
  ditch (`c\d+_d_*`) faces never count as floor, and the walkable
  cliff-path material `wcliff` does.
- `water`: an upward water-material face (`lake`, `lakep`, `bf_lake`,
  `bf_lakep`, `water`, `sea`, `river`, `pond`, `puddle`, `surf`) at the
  same heights, or a flat water-plane chunk prop.
- `stairs`: a sloped face (`0.3 < normal y <= 0.95`) spanning >= 0.5.
  Neutral -- a sloped face is as often a terrain skirt as stairs, so
  stairs are never flagged.
- `raised`: an upward face at `(base+1.2, base+3.5]` -- a ledge top,
  cliff top or bridge deck. Neutral.
- `tall`: a tall obstacle centred on the tile -- a gap-chain of faces
  whose centroids lie in the tile from the ground (`h <= base+0.6`)
  to the canopy/roof (`h >= base+1.5`); or a covering-centre chain of
  one material family from ground to canopy (this only explains a
  blocked tile -- a cone tree's canopy covers the tiles around the
  trunk too); or a tall building chunk prop; or a facade/ditch face
  covering the tile centre. Trees, rocks, buildings and cliff faces
  never count as floor.
- `canopy`: only tree-canopy faces cover the tile (no trunk on it).
  Neutral.
- `void`: nothing drawn at the tile centre. Shadow decals, the
  `s_land3_lm6` backdrop panel, and other non-surface faces are
  excluded.

Collision classification uses the permissions `u16` (bit 15 = blocked,
low byte = tile behaviour, names parsed from
`include/constants/field/map_tile_behaviors.h`). A blocked tile whose
behaviour is water / ledge / jump / warp / door / an interactable
(table, PC, berry patch, ...) is classed `behaviour`, not plain
blocked.

## DW support

A DW map's `tw_arc` record (`tools/distortion_world/twarc.py`) gives
its wall and ceiling platforms, whose collision comes from
`tw_arc_attr.narc` with the engine's indexing (ceiling:
`relVert = sizeX - (x - startX)`; east wall: `relVert = y - startY`;
west wall: `relVert = sizeY - (y - startY)`;
`relHoriz = z - startZ`; `index = relVert + relHoriz * tiles_v`).
The tw_arc record stores DW *world* coordinates; the tool subtracts
the index offset to get map-local coordinates (the custom DW maps
use offset `(0,0,0)`; the stock DW floors are stacked in world Y).
The platform geometry in the chunk models is what is drawn: a
ceiling tile is drawn if a solid face (not the `s_land3_lm6` backdrop,
not a hanging-lake water face; `bf_lake`/`bf_lakep` are lakebed,
i.e. solid) covers it at the platform height; a wall tile is drawn if
a thin face near the wall plane covers its `(y, z)` centre. Floor
tiles are checked only in chunks holding a floor-level puzzle feature
(entry, floor jump, coord/warp/object, low ghost prop); the rest of
a DW matrix is leftover stock Distortion World floor, not the puzzle.

## The allowlist

`tools/qa/walkcheck_allow.json` holds intentional cases (hidden
passages, puzzle tiles) as `{map, surface, class, x, z, reason}`.
Only add entries with a design reason; never to hide a bug.

## Known limits

- Tree trunks are only as good as the chain test: a walk-through
  trunk whose faces do not chain through the tile centre is not
  flagged; a canopy tile is never flagged (canopy vs trunk cannot be
  told apart from geometry alone).
- Edge structures: fences, fountains and building facades whose
  geometry sits on a tile's border but whose flat cap covers the tile
  centre are reported as floor+blocked (Jubilife's perimeter lines).
  They are visible structures, so they are false positives for the
  bug-finding purpose; they are not bugs.
- Stock `DISTORTION_WORLD_*` floors are excluded from `--all-dw`:
  their floor platforms use stock DW mechanics the tool does not
  model.
- Chunk props are footprints (bbox, rotation ignored), so a rotated
  prop can over-cover by a tile; a prop footprint only ever explains
  a blocked tile, never flags one.
- Water-plane chunk props are the only props whose drawn class is
  used; other props contribute only footprints.
- DW maps whose entry is not on drawn floor fall back to checking
  all their floor tiles.
- Interiors on a second storey in the same chunk share one chunk
  ground base; the modal-height rule is a heuristic.

## How to add it to a QA pass

1. Run `python3 tools/qa/walkcheck.py --all-dw` before any DW merge
   (the QA gate; see the "QA gate" section of
   `tools/distortion_world/README.md`).
2. For a suspect map: `python3 tools/qa/walkcheck.py --map <HEADER>`,
   open the overlay PNG, and spot-check up to 5 reported tiles in the
   emulator (place the player adjacent, step in, screenshot). If the
   drawn classification is wrong, note the pattern under Open; if
   the tile is a real discrepancy that is intentional, add an
   allowlist entry with a reason.
3. Run the Route 214 ground truth after touching the classifier:
   `python3 tools/qa/walkcheck.py --map MAP_HEADER_DW_ROUTE_214
   --region 8,5,55,31 --rom-tree <pre-fix checkout>` must report 74
   HIGH `LOOKS_WALKABLE_BUT_BLOCKED` tiles (the fix commit's 74), and
   0 HIGH on the current tree. A pre-fix checkout is a detached
   worktree at `121becabde^`.
4. Report the false-positive rate as a number: sampled tiles whose
   drawn classification the emulator check disproves, divided by the
   tiles sampled. As of this writing: 3/6 sampled HIGH tiles were
   false positives, all Jubilife edge structures (see Known limits);
   sampled Twinleaf tiles were 0/2 false positive.
