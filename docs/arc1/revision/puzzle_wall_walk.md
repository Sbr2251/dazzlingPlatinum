I've finished the plan. The main finding: the stock Distortion World already handles wall walking through a data-driven system, so the "camera rotated 90°" fake isn't needed. A new standalone Distortion World map can reuse it with almost no new engine code. Nothing was edited or built, and none of this has been tested in-game yet.

## 1. How stock wall-walking works

It's all in `src/overlay009/ov9_02249960.c`, plus avatar code in `src/unk_0205F180.c` and `src/player_avatar.c:841-912`. Each Distortion World map loads:

- **Normal land data.** Floors use the usual terrain model, permissions and height data (BDHC). The engine shifts each map into one shared coordinate space with per-map offsets (`fieldmap.c:827-833`).
- **One record per map in `tw_arc.narc`** (`res/prebuilt/fielddata/tornworld/`, a prebuilt binary). Member 0 is a table of `{mapHeaderID, member index, offset x/y/z}`, read at `:3684-3745`. The per-map member is loaded at `:3761`. It holds four sections, with the header struct at `:338`:
  - **Wall/ceiling/floor surfaces** (`:259`): kind (floor, west wall, east wall, ceiling), a 3D bounding box, and an id into `tw_arc_attr.narc`.
  - **Jump points** (`:267`): a tile plus the direction pressed. Stepping there hops the player onto a surface over 16 frames, rotates them ±90° and changes gravity (`:2387-2533`). They fire from the player's movement input (`ov9_0224A59C`, `:2135`).
  - **Camera angles** (`:284`): tile plus direction, giving a camera tilt with a 16-step transition.
  - **Ghost props**: the stock floating rocks that fade in and out.
- **Collision on a wall** comes from a 32x32 attribute grid in `tw_arc_attr.narc`: `0x8000` means blocked, the low byte is the tile behaviour (`:4140`, `:9423`). **A seam is simply the walkable tiles in that grid.**

I decoded the archive (11 members in `tw_arc`, 12 in `tw_arc_attr`):

| Floor (enum) | Surfaces / jumps / cameras | Useful as a reference for |
|---|---|---|
| B1F (574) | 1 west wall, 4 jumps, 4 cameras | Floor → wall → floor along a chasm. The wall is 4 tiles tall by 10 long and its grid already has blocked holes. Closest to Beat 1. |
| B2F (575) | west wall + 4 raised floors | Climbing a wall onto a raised floor (jump at (30,233,15)). Closest to Beat 3. |
| B4F (577) | east wall + ceiling | Hopping from one wall onto another surface |
| Giratina room (582) / Turnback (583) | standalone | A map with no neighbouring floors. Giratina is the one at offset (0,0,0). |

**Constraints:**
- Only west walls, east walls and ceilings exist; there are no north/south walls. Walls must sit on x-planes, and the camera yaws (stock uses 40–45°) so you can see them.
- Only one surface is active at a time, and each gravity change is a hop, not a smooth walk.
- Build-model props are not loaded in the Distortion World (`fieldmap.c:833`), so seams can't be map props.

## 2. Recommended approach

Build a new standalone Distortion World map, `MAP_HEADER_DISTORTION_WORLD_ARC1_SEAMS`, at offset (0,0,0) like the Giratina room, using the stock engine.

**Phase 0 — clone B1F as the new map.** Point it at copies of map data 602/603 and a copy of B1F's `tw_arc` record. This proves the whole integration path (header, archive entry, scripts, warp, battle, return) with zero art work.

**Phase 1 — build our own one-chunk terrain** with the existing Lake Verity pipeline (`tools/lake_verity/`, following `build_interior.py`; see `docs/lake_verity_redesign/interior_1f.md`). Then write our own surfaces, jumps, cameras and seam grids.

**Fallback (about 3 days):** ship Phase 0 as the puzzle. Edit only B1F's wall grid (copied to a new attribute id) so the seam goes up, forks to a dead-end alcove, and comes back down to the exit. You keep stock B1F visuals and lose the "over the crest" beat.

**Why not the doc's fake:** it would need custom camera code and still wouldn't rotate the player sprite. The stock path gives real wall walking, dust effects and the hop sound for free.

## 3. Layout sketch (one chunk, floor height y=1)

```
Elevation, looking north (x →):
y9          ┌─T T T─┐           T = crest ridge, raised floor (y9)
y5   A      │       │           A = alcove ledge (y5), Revive
     ↑fork  W2      W1 ← seam climbs W1 (west wall at x=20)
y1 B B B B  │       │  E E E E  E = entry (east), B = briefcase platform (west)
   ~~~~~~~ void / chasm ~~~~~~   floor lips over the void = fall triggers

W1 face, unfolded (z →, y ↑):   # = blocked, s = seam
y9  # # s s s #     → hop onto T
y5  A s s # s #     ← fork: left to A (dead end), right continues up
y2  # # # # s #
y1  jump-on tile (from E, pressing west)
```

- E → W1: jump (floor → west wall), like B1F's (12,257,49).
- W1 → A (land on a height-data ledge) and A → W1: a pair of jumps.
- W1 → T: wall → raised floor, using B2F's (30,233,15) as the template.
- T → W2 (east wall, going down) → B: the reverse of the climb.
- In plan view, E, A, T and B must not overlap, because permissions are 2D.
- Add camera entries at every jump tile.

## 4. Individual questions

- **Soft-reset fall.** The stock Distortion World has no falling. Recommended: make non-seam wall tiles blocked (`0x8000`) so the player can't step off a wall, which is how stock behaves. Put falls only at the walkable lips of the chasm: coord events there run a fall script (jump/hide → fade → `ResetDistortionWorldPersistedCameraAngles` → `Warp` to this same map's entry tile → fade in → Cyrus's line once, gated by a var). The same-map warp re-runs `InitPersistedMapFeaturesForDistortionWorld`, which wipes the saved surface index and camera (`persisted_map_features_init.c:145`).
  - *Optional extra:* "crumbling" wall tiles with their own behaviour byte, checked in the step hook `ov9_0224A71C` (`:2217`). It would copy the hardcoded per-map checks for maps 581/582 at `:2240-2257` and call `ScriptManager_Set`. Plain coord events can't do this on a wall: they check x and z only, and x is constant on a west wall.
- **Seam visuals.** Use an emissive (lights-off) seam material in the terrain model, animated through `fldtanime` by texture name. `TextureResourceManager_LoadTexture` runs in the Distortion World too (`fieldmap.c:953`). Precedents are `tools/coronet_lava/add_lava_anim.py` and the `build_art.py` frames support.
- **Followers.** No. Following only copies the player's x/z, has no gravity state, and would float or clip. Cyrus and Barry wait on E. When the player reaches B, do a short fade or flash and reposition them there. The more stock-looking option is the Distortion World ghost fade-in/out (`ScrCmd_311`/`312`), which needs entries in the overlay's NPC table (`Unk_ov9_02252EB4`, `:13186`). The Arc 1 flashback in the Giratina room already uses that.
- **Item and briefcase.** The Revive is a standard ground item (CLAUDE.md §5) on ledge A. The briefcase is a coord event in front of the briefcase object on B. Its script is Cyrus's line, then the existing block from `scripts_lake_verity.s:576-603` (`StartChooseStarterScene`, `SaveChosenStarter`, `GivePokemon`, `StartArc1MawileBattle`, `HealParty`), then `Warp MAP_HEADER_LAKE_VERITY, 0, 32, 31, DIR_NORTH`.

## 5. Files to add or change

| Piece | Files | Effort |
|---|---|---|
| Map header | `generated/map_headers.txt` (append), `include/data/map_headers.h` (copy B1F's fields), `res/text/location_names.json` | 0.5 d |
| Matrix, terrain, area | `res/field/maps/matrices/map_matrix_N.json`, `map_data_N.bin` (+ meson/order files), texture set and area entry (or reuse the Distortion World area 0x4A) | Phase 0: 0.5 d; Phase 1: 2–4 d |
| Overlay code | `ov9_02249960.c`: raise `DISTORTION_WORLD_MAP_COUNT` from 10 to 11 and add a standalone connection entry (`:88`, `:10042`). Optional: NPC table entries and the crumble hook. | 0.5 d |
| New `tw_arc` tool (JSON ↔ archive, using the record layouts above and `tools/coronet_lava/narc.py`) | `tools/distortion_world/twarc.py`; append to `tw_arc.narc` member 0 plus one new member; add new `tw_arc_attr` members (one per wall) | 0.5 d |
| Surface/jump/camera data and tuning | JSON for the tool above | 1–2 d (in emulator) |
| Seam animation | fldtanime entry and frames | 0.5–1 d |
| Scripts, events, text | `scripts_distortion_world_arc1_seams.s` (first entry: `InitPersistedMapFeaturesForDistortionWorld`), its init script, events JSON, text bank. Change the launchpad warp at `scripts_lake_verity.s:347`. | 1 d |

No new script commands are needed. The total is about **7–11 days**, or about **3 days** for the fallback.

## 6. Top risks

1. **Unknown fields in the archive records.** The jump record has a ±90 value (`unk_1A`) and fields `unk_1E`/`unk_20` I couldn't identify. Mitigation: build every record by copying a stock one and changing only bounds and displacement.
2. **The descent over the crest has no exact stock example.** Only the climb (B2F) exists. The jump vectors and camera angles need tuning in the emulator, and the hop could look wrong against our terrain.
3. **Objects from the events JSON are unproven in the Distortion World.** Every stock Distortion World NPC comes from the overlay's table. Test this in Phase 0; if it fails, move the NPCs, item and briefcase into that table.
4. **Coming back from the starter scene and the battle reloads the map.** The Giratina battle is a precedent, so this should be safe, but it needs a test.
5. **Ownership.** `src/overlay009` isn't in the ownership table in `docs/arc1/spec.md`. Lake Verity owns the warp, and the starter/Mawile scene currently on the terrace would move. Both workstreams need to agree.