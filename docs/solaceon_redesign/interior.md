# The Sanctuary hall (interior)

Team Eclipse's public hall in Solaceon. On the surface it is a calm, warm chapel for grief support: candlelight,
pale stone, a plum runner, pews, walls of photo cards. The player should notice what feels a little off. The emblem
is a black disc in a cold violet-and-gold corona, and its violet light seeps into the warm room. One card's photo is
just a dark square. The pins on every third card are Eclipse violet. Behind the hall is Indra's records office,
lined with filing shelves.

Workstream: sanctuary-interior (PLAN.md section 6). The tile contract for the town-scripts workstream is
`tools/solaceon_town/interior/layout.py`.

## IDs (all new, appended)

| What | Value |
|---|---|
| Map header | `MAP_HEADER_SOLACEON_SANCTUARY` (enum 601, appended after `MAP_HEADER_DW_LOST_TOWER`) |
| Map matrix | 296 (`map_matrix_296.json`, name `m_sol_sanct`, one chunk: `[[MAP_680]]`) |
| Map data | 680 (`map_data_680.bin`, `MAP_680` in `generated/maps.txt`) |
| Texture set | 076 (`map_texture_set_076.nsbtx`, 19 textures) |
| Area data | entry 0x4E (78) in `area_data.narc`: props list 21, texture set 76, light 1 |
| Text bank | `TEXT_BANK_SOLACEON_SANCTUARY` (`res/text/solaceon_sanctuary.json`, key 40231, one placeholder message) |
| Scripts | `scripts_solaceon_sanctuary.s` (one placeholder script), `scripts_init_solaceon_sanctuary.s` (empty) |
| Events | `events_solaceon_sanctuary.json` (only the exit warp) |

The IDs were the next free ones on `solaceon` (7d0005f2c): map_data 679, matrix 295, set 075, area 0x4D and header
600 were the last ones used. Props list 21 is the minimal stock indoor list `[78 d_mat01, 152]`, which holds the
indoor exit mat. Verity Castle 1F (area 0x4C) uses it too. Light 1 is the indoor area light, which the Foreign
Building (area 35) also uses.

Every builder output is registered in the same files Lake Verity's builder writes to. The new header, scripts,
events and text bank are registered where the DW rift maps registered theirs:

- `res/field/maps/data/meson.build`, `map_data.order`, `generated/maps.txt`
- `res/field/maps/matrices/meson.build`, `map_matrices.order`
- `res/field/maps/texture_sets/meson.build`, `map_texture_set.order`
- `generated/map_headers.txt`, `include/data/map_headers.h`
- `res/field/scripts/meson.build`, `scripts.order`
- `res/field/events/meson.build`, `zone_event.order`
- `generated/text_banks.txt` (text banks need nothing else; `res/text/meson.build` reads this list)

## Header

The fields are modelled on the News Press header (`MAP_HEADER_SOLACEON_TOWN_POKEMON_NEWS_PRESS`), the room whose door
this one takes over:

- `CAMERA_TYPE_INTERIOR_ORTHOGRAPHIC`, mapType 0x4, `BACKGROUND_INDOORS_1`, clear weather, `ENCOUNTERS_NONE`
- no bike, running, Escape Rope or Fly
- `mapLabelTextID = LocationNames_Text_SolaceonTown`, window 0x2
- **Music: `SEQ_CITY06_D` / `SEQ_CITY06_N`.** Solaceon's own theme carries on indoors. The hall is meant to feel like
  the warm heart of the town, and the town theme says that best. The one stock alternative is `SEQ_SILENCE_FIELD`,
  which Hearthome's chapel (the Foreign Building) uses. It would make the hall feel uneasy, so it could suit the
  Arc 3 "shut for the Return" state. That is the story workstream's choice; to switch, change the two fields in
  `build_interior.py` `HEADER_BLOCK` and in `map_headers.h`.

## Layout

The map is one chunk, so chunk tiles are absolute tiles. x runs east and z runs south. The rooms sit in the north-west
of the chunk and everything else is blocked. Every walkable tile has collision height h -1 (world y 0). The floor is
drawn 1/8 tile lower, as in stock. Run `python3 tools/solaceon_town/interior/layout.py` to print this map:

```
    x  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26
z  5  ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ##
z  6  ## Sc Pw Pw Pw Pw ## ## Em Em Em ## ## Pe Pe Pe Pe Dr ## ## ## ## Ma ## ## ##
z  7  ## .. .. Mo .. .. .. .. .. .. .. .. .. .. .. .. .. .. ## Sh Sh Sh .. Sh Sh ##
z  8  ## .. .. .. .. .. .. .. .. Sp .. .. .. .. .. .. .. .. ## .. .. .. .. .. .. ##
z  9  ## .. .. .. .. .. .. ca .. Lc .. ca .. .. .. .. .. .. ## .. .. .. In .. Cb ##
z 10  ## .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ## .. .. Lg Dk .. .. ##
z 11  ## .. .. .. pw pw pw pw .. .. .. pw pw pw pw .. .. .. ## .. .. .. .. .. .. ##
z 12  ## .. .. .. .. BA .. .. .. .. .. .. .. BB .. .. .. .. ## .. .. .. .. .. Bx ##
z 13  ## .. .. .. pw pw pw pw .. .. .. pw pw pw pw .. .. .. DD .. .. .. .. Bx Bx ##
z 14  ## .. .. .. .. .. BC .. .. .. .. .. .. .. .. .. .. .. ## ## ## ## ## ## ## ##
z 15  ## .. .. .. pw pw pw pw .. .. .. pw pw pw pw .. .. .. ## ## ## ## ## ## ## ##
z 16  ## .. .. .. .. .. .. .. .. .. .. .. BD .. .. .. .. .. ## ## ## ## ## ## ## ##
z 17  ## .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. .. ## ## ## ## ## ## ## ##
z 18  ## .. .. .. .. GB Gr .. .. .. .. .. .. .. .. .. .. .. ## ## ## ## ## ## ## ##
z 19  ## va .. .. .. .. .. .. .. EX .. .. .. .. .. .. .. va ## ## ## ## ## ## ## ##
z 20  ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ##
```

`..` floor (0x00), `##` blocked (0x8000), `EX` exit mat, `DD` office doorway, `pw` pew, `ca` candelabra, `va` lily
vase, `Dk` desk (TABLE). NPC spots and sign tiles are listed below.

- **Public hall:** x 2..18, z 7..19 (17 x 13), symmetric about x 10.5. Six pews (rows z 11, 13, 15; x 5..8 and
  12..15) face north on both sides of a 3-tile aisle, x 9..11. A plum runner with a gold hem leads from the door to a
  dais rug in front of the north wall.
- **North wall (z 6, drawn 7 tiles tall):**
  - Two framed photo-card boards, x 3..7 and 14..18, each with an offering ledge of candles.
  - The eclipse emblem, x 8.25..12.75 and 4.5 tiles high, between the boards.
  - Two high violet lancet windows.
  - A three-candle wall sconce at x 2.
  - The locked back door at x 18 (dark wood, iron bands, a brass lock and a small violet eclipse).
- **Lectern** (10, 9). Its collision is 0x8080 (TILE_BEHAVIOR_TABLE, blocked), so the speaker standing behind it at
  (10, 8) can be talked to from (10, 10), across the lectern. The lectern carries the emblem on its front and an open
  book on top. A brass candelabra stands on each side, at (8, 9) and (12, 9).
- **Entrance:** the exit mat at (10, 19) is collision 0x65 (WARP_ENTRANCE_SOUTH) plus the stock prop 78. A guest book
  on a stand is at (6, 18), and white lilies in vases are at (2, 19) and (18, 19).
- **Records office:** x 20..25, z 7..13 (6 x 7), wooden floor, walls 3.5 tiles high. It holds:
  - filing shelves (binders above, card drawers below) at (20..22, 7) and (24..25, 7);
  - a pinned map of Sinnoh on the wall above (23, 7), which is a walkable gap;
  - Indra's desk: (22, 10) with the open ledger (plain blocked) and (23, 10) with a card box and a candle lamp
    (TABLE, so Indra at (23, 9) can be talked to across it);
  - a card-drawer cabinet at (25, 9);
  - stacked card boxes at (24, 13), (25, 13) and (25, 12).
- **Walls and edges:** the hall/office wall is column x 19, z 6..12, and its end at the doorway carries a small brass
  plate. The south edges (z 20 under the hall, z 14 under the office) and the outer sides are left open and black, as
  in the stock interiors. Nothing tall stands south of a walkable tile in its column, so no wall top ever hides the
  player. This is why the doorway is at the south end of the inner wall, as in the Galactic Eterna building's 1F.

### Warp

| Map | # | Tile | Behaviour | Destination |
|---|---|---|---|---|
| Sanctuary | 0 | (10, 19) | 0x65 | `MAP_HEADER_SOLACEON_TOWN` warp 2 |

The player arrives on (10, 19), which is the exit mat. Its height is checked like every other tile's. **Solaceon Town
warp 2 still points at the News Press** (`events_solaceon_town.json`, which this workstream may not edit). The
town-scripts / town-layout workstream must set it to `MAP_HEADER_SOLACEON_SANCTUARY`, `dest_warp_id` 0, and put it on
the Sanctuary door tile.

### NPC spots (`layout.NPC_SPOTS`)

| Name | Tile | Facing | Note |
|---|---|---|---|
| SPEAKER | (10, 8) | south | the Eclipse speaker, behind the lectern (talk from (10, 10)) |
| BELIEVER_A | (6, 12) | north | in the pews, facing the emblem |
| BELIEVER_B | (14, 12) | north | |
| BELIEVER_C | (7, 14) | north | |
| BELIEVER_D | (13, 16) | north | |
| MOURNER | (4, 7) | north | at the west photo board |
| GREETER | (7, 18) | east | by the guest book, facing the aisle |
| INDRA | (23, 9) | south | behind her desk (talk from (23, 11)) |

### Sign tiles (`layout.SIGNS`)

All sign tiles are blocked. Each is read from the walkable tile listed, facing as given.

| Name | bg_event tile(s) | Read from |
|---|---|---|
| PHOTO_BOARD_WEST | (3..6, 6) | row 7, facing north (e.g. (4, 7)) |
| EMBLEM | (9..11, 6) | (10, 7), north |
| PHOTO_BOARD_EAST | (14..17, 6) | row 7, north |
| BACK_DOOR | (18, 6) | (18, 7), north: "It's locked." |
| SCONCE | (2, 6) | (2, 7), north |
| LECTERN | (10, 9) | (10, 10), north (a TABLE tile: an object standing behind it is talked to first) |
| GUEST_BOOK | (6, 18) | (6, 17) south, or (5, 18) / (6, 19) |
| SHELVES | (20..22, 7), (24..25, 7) | row 8, north |
| SINNOH_MAP | (23, 6) | (23, 7), north |
| LEDGER | (22, 10) | (22, 11), north, or (21, 10) east |
| CABINET | (25, 9) | (24, 9), east |
| CARD_BOXES | (24, 13), (25, 13), (25, 12) | (24, 12) and neighbours |

### Blocking the office (the method)

Collision in map data is fixed: the field has no script command that changes a tile's permissions at run time. The
office is therefore closed with an **object event on the doorway tile (19, 13)**. The doorway is the only way in and
is one tile wide, so one object closes it.

- Add an object event at x 19, z 13 (y 0) to `events_solaceon_sanctuary.json`. Give it a `hidden_flag` from the
  Sanctuary block, e.g. `FLAG_SOL_SANCTUARY_A`.
- Objects block movement whenever they are shown. The office is open while the flag is set (object hidden) and closed
  while it is clear. Use `SetFlag` / `ClearFlag` in the init or OnTransition script to follow the story state: open on
  the first visit (44-53), locked from 54.
- Suitable graphics: a robed grunt, `OBJ_EVENT_GFX_ECLIPSE_GRUNT_M/F`, which can also talk ("Records are closed to
  visitors."). Alternatively `OBJ_EVENT_GFX_ECLIPSE_CRATE`, or `OBJ_EVENT_GFX_SIGNBOARD` as a "Closed" board. The
  repo has no rope or stanchion sprite.
- A guard that turns the player back on a coord event at (18, 13) also works. The object is simpler and cannot be
  walked past.

## Art

The room is authored as Python geometry (`art/sanctuary_interior.py`), not in Blender, so it is reproducible with the
system `python3`. It follows the stock interiors: Hearthome's Foreign Building (map_data_244), the News Press (313)
and the Galactic Eterna building's 1F (333). The renders of those were made with `dump_stock.py`.

- **Lighting:** the materials are unlit (lights 0) with baked vertex colours, like every stock interior; the mean
  vertex colour is 0.60, against stock's 0.55-0.7.
  - The light is warm: the candle ledges, the candelabra, the sconce and Indra's desk lamp.
  - The emblem gives off a faint cold violet glow, and cool daylight comes in at the door.
  - The inner wall stops light between the two rooms, except for a spill at the doorway.
- **Geometry:** only the faces the fixed orthographic camera can see are drawn: tops and south-facing fronts. Wall
  faces sit 3/8 tile into the wall row, wall tops are black, and nothing is drawn on the south edges or outer sides.
  All furniture is terrain. The exit mat is the stock prop.
- **Textures:** 19 textures, all pltt16, painted in `art/sanctuary_textures.py` at stock density (16 texels per tile):
  - `sa_floor`, `sa_planks`, `sa_rug`, `sa_hem`, `sa_plaster`, `sa_wainscot`, `sa_trim`, `sa_wood`, `sa_brass`
  - `sa_cards`, `sa_emblem`, `sa_window`, `sa_door`, `sa_flame`, `sa_lily`
  - `sa_files`, `sa_box`, `sa_ledger`, `sa_map`

  The emblem, window, flame and lily textures use colour 0 as transparent. The east photo board shows the same
  texture as the west one, shifted half a board.

## Budgets

| Item | Value | Limit / precedent |
|---|---|---|
| Polygons | 522 quads (the whole room; the camera can't see more) | 1800 of the DS's 2048; soft 1000 per chunk |
| Model (NSBMD) | 27476 B | 0xF000 = 61440 B buffer; 45 KB plan budget |
| Vertices / materials | 1824 / 21 | |
| Texture set 076 VRAM | 5728 B texels + 400 B palettes = 6128 B | largest stock set 76416 B (048); Verity Castle's set 075 is 11008 B |
| BDHC | 66 B (one plate, x 1..27, z 6..21, y 0) | 0x9000 |
| map_data_680.bin | 29654 B | |

## Checks (`build_interior.py`, all pass; `--write` is refused if any fails)

- NSBMD build -> parse -> build gives identical bytes, the decoded faces equal the built faces, and the polygon count
  equals the mesh face count.
- NSBTX rebuild is identical, every texture decodes back to its PNG, all textures are 16-colour, and every material's
  texture is in set 076.
- map_data unpack -> pack is identical.
- Permissions equal `layout.grid()`.
- The BDHC height at all 1024 tile centres equals `layout.height()`. It is defined on all 223 walkable tiles,
  including the arrival tile (10, 19), which is the 0x65 exit mat at floor height.
- The office doorway is walkable, every NPC spot is walkable, every sign tile is blocked and every reading tile is
  walkable.
- The warps in `events_solaceon_sanctuary.json` equal `layout.WARPS`.
- Exit mat model 78 is in props list 21.
- Budgets pass (`assemble.check_budgets`, plus the whole-room polygon count).
- **Only appends in the shared registries:** every registry file keeps all of its `50482f890` lines in order.
  Entries added by other workstreams are reported, not failed. area_data entries 0..77 are byte-identical to stock,
  and map_data 680, set 076 and matrix 296 did not exist in stock.
- Idempotent: a second `--write` changed no byte (all written files hashed before and after), and re-running the art
  script gives identical assets.

## How to rerun

```
python3 tools/solaceon_town/interior/layout.py                     # print the tile map
python3 tools/solaceon_town/interior/art/sanctuary_interior.py     # textures + sanctuary.mesh.json
python3 tools/solaceon_town/interior/build_interior.py             # dry run: all checks + budgets
python3 tools/solaceon_town/interior/build_interior.py --write     # write + register (idempotent)
python3 tools/solaceon_town/interior/build_interior.py --preview /tmp/sanct_prev

# renders (Cycles on the CPU; use tools/lake_verity/blender_preview.py instead where EEVEE works)
B=/Applications/Blender.app/Contents/MacOS/Blender
$B -b --factory-startup -P tools/solaceon_town/interior/preview_cycles.py -- \
    --tex tools/solaceon_town/interior/assets/textures --tex /tmp/sanct_prev/textures \
    --out OUT/sanctuary_entrance --views top,game --camera interior --region 0,4,28,22 --px 24 \
    --target 10,17 --dscolor --bg 0,0,0 /tmp/sanct_prev/sanctuary.mesh.json /tmp/sanct_prev/exit_mat.mesh.json

# stock references (Foreign Building, News Press, Galactic Eterna 1F): meshes, textures and permission grids
python3 tools/solaceon_town/interior/dump_stock.py OUT/stock
```

The stub scripts, events and text file are only created if they are missing. The builder never overwrites them,
because the town-scripts workstream owns them. It still checks that the exit warp in the events file matches the
layout.

Renders: `sanctuary_entrance_game.png` (the in-game interior camera at the door), `sanctuary_entrance_top.png`
(top view), `sanctuary_north_game.png` (the north wall, emblem and lectern), `sanctuary_office_game.png` (the office
and doorway), and the stock references `stock_foreign_game.png`, `stock_foreign_n_game.png` and
`stock_galactic_game.png`.

## Open issues (need a ROM build)

- **Not built.** The new header block, the scripts and events compiling, the text bank, the NARC orders and the area
  entry are checked only by these tools, not by `make release`.
- **Solaceon Town warp 2** must be pointed at `MAP_HEADER_SOLACEON_SANCTUARY` warp 0 (town workstreams). Until then
  the hall can't be reached in game. The News Press header and its files are untouched.
- **Black edges:** like the stock interiors, the open edges depend on the field's black clear colour. No black
  geometry is drawn there.
- **Hardware look:** the baked brightness (mean 0.60), the depth of the decal offsets (0.03 tile), and the 1-bit
  alpha edges of the emblem, flames and lilies are unverified on a DS or emulator. The candle flames are static; no
  `fldtanime` entry was added.
- **Talking across the TABLE tiles** (the speaker at the lectern, Indra at the desk) follows `sub_0203C9D4`'s TABLE
  rule, which is unverified here.
- **ID collision risk:** `tools/lake_verity/build_art.py --new-set` would also write texture set 076. That path is
  optional and unused; if it is ever run, one of the two must move to 077.
- **Previews location:** `~/Documents` was not writable from this session (macOS denied it, even unsandboxed), so
  the renders are in `/tmp/Solaceon Update/interior/`. Copy them to `~/Documents/Solaceon Update/interior/`.
