# Solaceon Town redesign: the layout (town-layout workstream)

The tile contract is `tools/solaceon_town/layout.py`. Everything in this file comes from it; if they disagree,
layout.py wins. Overworld matrix 0: `map_data_072` = cell (17,20) = x 544..575, `map_data_073` = cell (18,20) =
x 576..607, z 640..671. The town is flat at h 1.0 (world y 32). The only other height is the stock ledge in front of
the Maniac Tunnel room (x 594..607, z 651..653, h 3.0), kept as stock.

## 1. The map

```
      4444445555555555666666666677777777778888888888999999999900000000
      4567890123456789012345678901234567890123456789012345678901234567
 640  #############.,,,,,.TTTTTTTTTTTTTTTTTTTTTTTTTTTT################
 641  #-----------#.,,,,,.TTTTTTTTTTTTTTTTTTTTTTTTTTTT--##############
 642  #-----------#.,,,,,.fffffHHHHTTHHHH.TTTTTTTTTTTT################
 643  #-----#######i,,,,,iftut.HHHHTTHHHH.TTTTTTTTTTTT################
 644  #-----######-.,,,,,.ixxx.HHHH..HHHH.TTTTTTTTTTTT################
 645  #-----###D##-.,,,,,......HDHH..HDHH.TTTTTTTTTTTT################
 646  #-----#------.,,,,,.,,,,,,,,,,,,,,,,............################
 647  #-----#------i,,,,,i.....,wwwwwwwwwwwwwwwwwwwwww################
 648  #-----#------.,,,,,......,wCC:::SSSSSSSSS::::::w################
 649  #-----#------l:::::l""""",wC::::SSSSSSSSS::::::w################
 650  #-----#------q::::::""""",w:::::SSSSSSSSS::::::w################
 651  #-----#######o::::::""""",w:::::SSSSSSSSS::::::w################
 652  #-----------#:::::::""""",w:::::SSSSDSSSS::::::w#####E##########
 653  #-----------#:::::::PPPPP,w::::::l:::::l:::::::w##^^^^^#########
 654  #-----------#::::::nPPPPP,w::::::::***:::::::::w################
 655  #-----------#::::::nPPPPP,w::::::::***:::::::::w###E############
 656  #~~~~-#######:::::::PPDPP,w::::::::***:::::::::wsss_ss##########
 657  #~~~~-#------o:::::::::::,w::::::::::::::::::::wL____L##########
 658  #~~~~-#------l:::::l:::::,wwwwwwwwwIGIwwwwwwwwwwC____C##########
 659  #-----#------:::::::,,,,,,,,,,,,,,,,,,,,,,,,,,,,fffgff##########
 660  #-----#------:::::::,,,,,,,,,,,,,,,,,,,,,,,,,,,,______##########
 661  #rr---#------.,,,,,...........TT................______##########
 662  #rrffffffffff.,,,,,.ffffff....TTHHHH......TTTTTT______##########
 663  #rrkkkkkkkk.f.,,,,,.fbbbbfMMMM..HHHH......TTTTTT______##########
 664  #rrmkmkmkmk.f.,,,,,.......MMMM..HHHH........TTTT################
 665  #TTyyyyyyyyyy.,,,,,.......MDMM..HDHH........TTTT################
 666  #TTyyyYYYzzzz.,,,,,.,,,,,,,,,,,,,,,,,,,,,,......################
 667  #TTyyyYYYzzzz.,,,,,.............................################
 668  #TTyyyyyyyyyy.,,,,,...TTTTTTTTTTTTTTTTTTTTTTTTTT################
 669  #ffffffffffff.,,,,,...TTTTTTTTTTTTTTTTTTTTTTTTTT################
 670  #TTTTTTTTTTTT.,,,,,.############################################
 671  #TTTTTTTTTTTT.,,,,,.############################################
```

Legend: `.` grass, `,` road (sand), `:` paving, `*` emblem paving, `"` tall grass (garden of names), `T` tree,
`H` house, `P` Pokemon Center, `M` Mart, `S` Sanctuary hall, `D` door (warp), `w` compound wall, `I` gate pillar,
`G` gate, `f` fence, `i` post (banner / sign), `l` lantern, `n` bench, `o` offerings, `q` memorial plaque, `t` tent,
`u` tent floor (clerk), `x` tent table (talk across), `k` kennel, `m` kennel stall, `r` trough, `y` loading yard,
`Y` truck bay, `z` ruts, `s` scaffolding, `C` crates, `L` work light, `_` dig dirt, `g` fence gap (guard),
`b` berry patch. Stock terrain kept: `-` walkable, `#` blocked, `~` puddle, `E` Ruins entrance, `^` raised (h 3).

What is rebuilt and what is stock:

- **Rebuilt** (`layout.REBUILD`): x 557..591 for the full height (road, plaza, the whole east side), the excavation
  front x 592..597 z 656..663, the south-west kennel yard x 545..556 z 662..671, and the road to Route 209.
- **Stock, byte for byte**: the Day Care ranch west of the road (Day Care, pens, ponds, the fences on x 556 and the
  memorial wall with its five boards), and the Ruins hill with both entrances.
- Overrides on stock tiles (permissions only): x 544 and the seam rows z 640 / z 671 blocked except x 557..563;
  the Day Care trough of prop 198 at (545..546, 661..664) blocked (the kennel yard now exposes it).

The zones (PLAN section 4):

1. **Pilgrim road** (x 557..563, z 640..648): banner posts at (557,643), (563,643), (557,647), (563,647). The
   **registration tent** is x 565..567, z 643..644 (3 x 2), open to the south: back row z 643 = card boxes at 565
   and 567, the clerk's tile (566,643) between; front row z 644 = the table (TILE_BEHAVIOR_TABLE, so the clerk is
   talked to across it from (566,645)). Fence behind it on z 642. The queue stands on x 565, z 645..648.
2. **Memorial plaza** (x 557..563, z 649..660, paved across the road): the wall on x 556 (stock), reading tiles
   x 557 z 652..656, offerings at (557,651) and (557,657), lanterns at (557,649), (557,658), (563,649), (563,658),
   the bench (563,654..655) facing the wall, the postgame plaque post at (557,650). **Garden of names**: tall grass
   x 564..568, z 649..652 (5 x 4), between the plaza and the Pokemon Center.
3. **Sanctuary compound** x 570..591, z 647..658: wall on the perimeter, one gate (580,658) between pillars (579,658)
   and (581,658). **Hall** x 576..584, z 648..652 (9 x 5), door (580,652) in the middle of the south face, walls
   3 tiles, hip roof to 4 tiles. Forecourt z 653..657 with the **emblem** x 579..581, z 654..656 on the path from
   the gate to the door; lanterns (577,653), (583,653); supply crates in the west yard (571..572,648), (571,649).
   It takes the News Press lot, the Northeast and East house lots and the ground in front of the Ruins hill.
4. **Excavation** x 592..597, z 656..658 in front of Ruins Room 1 (595,655): scaffolding along the cliff
   (592..594 and 596..597, z 656), work lights (592,657), (597,657), crates (592,658), (597,658), dig floor between.
   Fence on z 659 with **one gap (595,659)**; the compound wall (x 591) and the cliff close the other sides. Dig
   dirt x 592..597, z 660..663 in front. Checked: Room 1 is reachable only through the gap.
5. **Ranch**: Day Care and pens stock. **Kennel block** x 547..554, z 663..664: back row blocked, stalls
   (walkable, open to the yard) at (547,664), (549,664), (551,664), (553,664) between dividers. **Loading yard**
   x 547..556, z 665..668, opening onto the road at x 556 z 665..668; **truck bay** x 550..552, z 666..667 (3 x 2,
   a truck facing east); wheel ruts from the bay to the road on z 666 and z 667.
6. **Believers' houses** (stock house prop t4_h01 + c1_door1, 4 x 4 footprint, door at (x0+1, z0+3)):
   North House x 569..572 z 642..645, Northeast House x 575..578 z 642..645, East House x 576..579 z 662..665.

## 2. Anchors

### Doors and warps (`warp_events`, only x/z changed; order and destinations untouched)

| # | tile | destination | what | was |
|---|---|---|---|---|
| 0 | (553,645) | MAP_HEADER_POKEMON_DAY_CARE | Day Care | same |
| 1 | (576,645) | MAP_HEADER_SOLACEON_TOWN_NORTHEAST_HOUSE | Northeast House (believer's home) | (579,648) |
| 2 | (580,652) | MAP_HEADER_SOLACEON_TOWN_POKEMON_NEWS_PRESS (lead repoints it to the Sanctuary interior) | **Sanctuary hall door** | (571,656) |
| 3 | (570,645) | MAP_HEADER_SOLACEON_TOWN_NORTH_HOUSE | North House (believer's home) | (565,646) |
| 4 | (577,665) | MAP_HEADER_SOLACEON_TOWN_EAST_HOUSE | East House (believer's home) | (581,656) |
| 5 | (566,656) | MAP_HEADER_SOLACEON_TOWN_POKECENTER_1F | Pokemon Center | same |
| 6 | (571,665) | MAP_HEADER_SOLACEON_TOWN_MART | Poke Mart | same |
| 7 | (597,652) | MAP_HEADER_SOLACEON_RUINS_MANIAC_TUNNEL_ROOM | stock, on the h 3 ledge (not reachable from town, as stock) | same |
| 8 | (595,655) | MAP_HEADER_SOLACEON_RUINS_ROOM_1 | stock | same |

Every house is kept (no warp parked). All dest_warp_id are 0, unchanged. Door tiles are TILE_BEHAVIOR_DOOR | blocked
(0x8069) like stock; the Ruins entrances are 0x6E (walkable). The fly / blackout landing (566,657) is unchanged.

### Signs (bg events unless noted; read tile = where the player stands)

| sign | tile | read from, facing |
|---|---|---|
| town sign (stock map signpost OBJECT, keep) | (564,667) | (564,666) north |
| Sanctuary gate plaque | (579,658) (gate pillar) | (579,659) north |
| tent sign | (564,644) (post) | (564,645) north, or (563,644) east |
| excavation warning sign | (594,659) (fence) | (594,660) north |
| kennel sign | (554,664) (kennel end) | (554,665) north |
| postgame memorial plaque (band F) | (557,650) | (558,650) west |
| banner / torn-banner posts | (557,643), (563,643), (557,647), (563,647) | the road tile beside each, facing the post |
| 2.16a wall signs (unchanged) | (556,652..656) | (557,652..656) west |

The Rowan banner signboard objects (557,642) and (557,666) stand on walkable verge tiles and can stay.

### Rectangles

| what | tiles |
|---|---|
| wild grass (garden of names) | x 564..568, z 649..652 (20 tiles, TILE_BEHAVIOR_TALL_GRASS) |
| registration tent | x 565..567, z 643..644; clerk (566,643); talk tile (566,645) |
| Sanctuary compound | x 570..591, z 647..658 (wall ring), gate (580,658) |
| Sanctuary hall | x 576..584, z 648..652, door (580,652) |
| emblem | x 579..581, z 654..656 |
| excavation yard / gap | x 592..597, z 656..658 / (595,659) |
| kennel / stalls | x 547..554, z 663..664 / (547,664) (549,664) (551,664) (553,664) |
| loading yard / truck bay | x 547..556, z 665..668 / x 550..552, z 666..667 |
| plaza | x 557..563, z 649..660 |
| berry patches (stock objects) | (565..568, 663) |

### NPC spots (screenplay "Cast by zone")

| zone | role | tile | facing | note |
|---|---|---|---|---|
| 1 | TENT_CLERK | (566,643) | south | behind the table; talk from (566,645) |
| 1 | PILGRIM_FATHER | (565,645) | north | queue front, at the table's west end |
| 1 | PILGRIM_SAILOR | (565,646) | north | queue |
| 1 | PILGRIM_SISTER | (565,647) | north | queue |
| 1 | PILGRIM_SON | (565,648) | north | queue |
| 1 | ROAD_GREETER | (562,645) | west | between the banner posts |
| 2 | WALL_WIDOW | (558,652) | west | behind the reading line, keeps x 557 free |
| 2 | GARDEN_GIRL | (563,651) | east | edge of the garden |
| 2 | LANTERN_MAN | (562,650) | east | by lantern (563,649) |
| 2 | BELIEVER_MOTHER | (561,656) | west | |
| 2 | LOOKER (briefing) | (558,657) | north | south end of the wall |
| 2 | CYRUS (briefing) | (559,657) | north | beside Looker |
| 2 | postgame garden pilgrims 1-4 | (565,650), (567,650), (565,652), (567,651) | south, south, west, west | in the tall grass |
| 3 | GATE_GREETER | (581,657) | south | inside, beside the open gate |
| 3 | GATE_GRUNT_L | (579,659) | south | outside, left of the gate (band D: one steps onto (580,659)) |
| 3 | GATE_GRUNT_R | (581,659) | south | outside, right of the gate |
| 3 | FORECOURT_SWEEPER | (582,656) | west | at the emblem |
| 3 | IP_OFFICER_GATE | (581,659) | south | band E |
| 3 | IP_OFFICER_COURT | (575,655) | east | band E |
| 4 | DIG_WORKER | (593,657) | north | inside the yard |
| 4 | EXCAVATION_GRUNT_M | (595,659) | south | **on the gap** (blocks it); sight line (595,660..663) |
| 4 | EXCAVATION_GRUNT_F | (596,660) | west | beside the gap; sight line (595,660), (594,660), ... |
| 4 | step-aside after the raid battles | M -> (596,661), F -> (597,660) | | gap and (595,660) free |
| 4 | RUIN_MANIAC | (593,661) | north | |
| 4 | IP_OFFICER_DIG | (596,660) | west | band E |
| 4 | CYRUS at the fence (after the briefing) | (597,662) | west | a few tiles from the pair |
| 5 | KENNEL_KEEPER | (555,665) | west | |
| 5 | KENNEL_MON_1..4 | (547,664), (549,664), (551,664), (553,664) | south | in the stalls; talk from z 665 |
| 5 | LOADING_GRUNT | (553,668) | north | by the truck bay |
| 5 | RANCHER | (554,648) | south | Day Care yard (stock) |
| 5 | DAYCARE_KID | (552,647) | east | Day Care yard (stock) |
| 6 | SUNDAY_MAN | (573,644) | south | between the North and Northeast houses |
| 6 | DOUBTER | (579,666) | west | by the East House |
| 6 | POKETCH_MAN | (579,644) | south | east of the Northeast House |

`python3 tools/solaceon_town/layout.py --check` verifies each spot is walkable and reachable from the north road
(the clerk and kennel mons are behind a table / in stalls by design), that every sign tile is blocked with a
reachable read tile, and that no 1-wide lane is occupied (the north lane z 646 and the alley x 569 are kept free).

## 3. Props per chunk (map props = build models, all in area 0xA's prop list 6)

| chunk | model | name | tile (x, z) | world (chunk-centred) | |
|---|---|---|---|---|---|
| 072 | 5 | fs (Mart) | (572.0, 665.0) | (192, 32, 144) | stock |
| 072 | 70 | p_door | (571.5, 665.375) | (184, 32.62, 150) | stock |
| 072 | 198 | t4_s01 (Day Care + shed + troughs) | (553.5, 644.5) | (-104, 32, -184) | stock |
| 072 | 67 | t1_door1 | (554.12, 645.25) | (-94.06, 33.17, -172.02) | stock |
| 072 | 4 | pc | (566.5, 655.0) | (104, 32, -16) | stock |
| 072 | 70 | p_door | (566.5, 656.06) | (104, 32, 1) | stock |
| 072 | 197 | t4_h01 (North House) | (571.0, 644.5) | (176, 32, -184) | moved |
| 072 | 246 | c1_door1 | (571.11, 645.12) | (177.73, 33.27, -174.04) | moved |
| 073 | 197 | t4_h01 (Northeast House) | (577.0, 644.5) | (-240, 32, -184) | moved |
| 073 | 246 | c1_door1 | (577.11, 645.12) | (-238.27, 33.27, -174.04) | moved |
| 073 | 197 | t4_h01 (East House) | (578.0, 664.5) | (-224, 32, 136) | moved |
| 073 | 246 | c1_door1 | (578.11, 665.12) | (-222.27, 33.27, 145.96) | moved |
| 073 | 298 | gym_door00 (Sanctuary hall door) | (580.5, 652.0) | (-184, 32, -64) | new |

Removed: the News Press house (072) and the two east houses (073) with their doors; the old North House prop moved.
The hall door needs a door prop: `ov5_021D431C.c` looks one up from its list of door models and GF_ASSERTs if none
is found. 298 is placed like stock gym doors (tile centre x, the door row's north edge). Houses use the stock
offset house -> door (+7070, +5205, +40791 fx32).

The new buildings (hall, tent, kennel, scaffolding, compound wall, fences, posts) are terrain in the graybox,
using only stock set-010 textures and palettes: ngrass, nsand, nsandp, blueglay, shadowchip, l_grass_u/m/d,
tree2_01, imped, hanger, criff, nbridge, bridge, beach, rhana, sol_wall (the violet banner cell on the banner posts).

## 4. Budgets (`build_graybox.py`)

| chunk | polygons (stock kept + new) | stock | model B | stock B | BDHC B | materials | props (polygons) |
|---|---|---|---|---|---|---|---|
| 072 | 463 (165 + 298) | 436 | 25816 | 21360 | 66 (1 plate) | 35 | 8 (391) |
| 073 | 771 (479 + 292) | 772 | 36732 | 34536 | 172 (4 plates) | 24 | 5 (188) |

- Limits: 1000 polygons and 45 KB of model per chunk (hard 0xF000 = 61440).
- On screen (terrain of every loaded chunk incl. 068/074/filler + all props, frustum + back-face culling, the method
  of `assemble.camera_polys`): worst 339 with CAMERA_TYPE_DEFAULT (Solaceon's header camera) and 357 with the
  zoomed-in camera; limit 2048.
- Set 010 is not touched.

## 5. Checks and how to rerun

```
python3 tools/solaceon_town/layout.py --ascii --check      # the map + 93 contract checks
python3 tools/solaceon_town/collision.py                    # permissions/BDHC vs layout per chunk
python3 tools/solaceon_town/build_graybox.py                # dry run: budgets + all checks
python3 tools/solaceon_town/build_graybox.py --write        # writes map_data_072/073 (refuses on any FAIL)
python3 tools/solaceon_town/warps.py --write                # warp x/z from layout.DOORS
# previews (OUT = ~/Documents/Solaceon Update/layout)
python3 tools/solaceon_town/dump_stock.py OUT/stock [--report]
python3 tools/solaceon_town/build_graybox.py --preview OUT/gb
python3 tools/solaceon_town/render.py OUT [--cycles]        # graybox_top.png + game views (north, plaza, ...)
python3 tools/solaceon_town/compare_layout.py OUT/graybox_top.png OUT/graybox_vs_layout.png
```

`build_graybox.py` checks: permissions equal the layout; BDHC height at every tile centre equals the layout;
north seam z 640 = map_data_068 row z 639 and south seam z 671 = map_data_074 row z 672 (walkable x 557..563, h 1.0,
x 544..575); 073's seam rows and the x 544 / x 607 edges blocked; every door tile has a building behind it and a door
prop on it; all props in area 0xA's list; polygon / model / on-screen budgets; untouched stock shapes and materials
byte-identical. Output is deterministic (stock inputs read from git at BASE_REV 50482f890). Output paths are the
constants `MAP_DATA_DIR` / `EVENTS_JSON` at the top of layout.py (the macOS branch keeps chunks in
`res/field/mapmodels/data/` and events in `res/field/maps/solaceon_town/events.json`).

## 6. Open issues for other workstreams

- **Wild encounters**: `MAP_HEADER_SOLACEON_TOWN` has `wildEncountersArchiveID = ENCOUNTERS_NONE`. The garden of
  names is real tall grass (0x02) but yields nothing until the lead gives the header an encounter table (Yamask,
  Duskull).
- **The truck** is not in the graybox: there is no truck field sprite and a terrain truck would be there in every
  band (the screenplay has it gone in band C). The bay is reserved (3 x 2, walkable); town-art / town-scripts decide.
- **Existing objects for town-scripts to move** (they no longer fit): `SOLACEON_TOWN_SIGNBOARD_6` at (569,656) (the
  News Press sign) now stands in the 1-wide alley x 569 and blocks it; `COWGIRL_0` (563,652), `RANCHER_14` (569,650)
  and `RANCHER_2` (569,659) wander across the plaza / alley; `EXPERT_M_3` (POKETCH_MAN) is still at (555,648) in the
  Day Care yard. None is on a blocked tile.
- **News Press daily request** goes with the News Press door (warp 2 is now the hall), as screenplay Appendix C notes.
- **Not verified in game**: the gym door prop on a terrain facade (animation and sound), house props crossing the
  072/073 seam (the Northeast House prop sits in 073 at x 577 and overhangs into 072, as props do at chunk edges).
