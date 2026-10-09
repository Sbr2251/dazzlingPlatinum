# Distortion World tools (Arc 1 wall-walk puzzle)

The Arc 1 puzzle map `MAP_HEADER_DISTORTION_WORLD_ARC1_SEAMS` is a standalone DW map cloned from DW B1F
(Phase 0 of `docs/arc1/revision/puzzle_wall_walk.md`), at DW offset (0,0,0) like the Giratina room.

| file | what |
|---|---|
| `twarc.py` | dump / build / check `res/prebuilt/fielddata/tornworld/tw_arc.narc` (per-map surfaces, jump points, cameras, ghost props) and `tw_arc_attr.narc` (32x32 wall collision grids) |
| `arc1_seams.json` | the puzzle map's record: B1F's record shifted to (0,0,0), its wall grid copied to attr 12 and edited (`rows`, top row first, column = z - 13) |
| `build_arc1_seams_map.py` | builds `map_data_667/668` from B1F's 602/603: walkable chasm lips (fall coord events) and blocked invisible landing zones |

Rebuild after editing: `python3 tools/distortion_world/build_arc1_seams_map.py`, then
`python3 tools/distortion_world/twarc.py build tools/distortion_world/arc1_seams.json` (both idempotent; `--check` /
`check` verify). `twarc.py` looks the map ID up in `generated/map_headers.txt`, so rerun `build` if the header enum
ever moves.

Wall grid (west wall x=11, z 13-22, y 2-5; `.` = walkable). It matches what the stock wall face draws, which is
B1F's own grid: y5 is the top rim, and the `#` block at z 15-18 is where the two wall trees grow out of the face.
A Phase 0 wall face looks the same everywhere, so any other blocked tile would be an invisible wall (and walkable
tiles over the trunks let the player walk through the trees).

    y5  ##########
    y4  ..####....   dead-end corner up the wall at z 19-22
    y3  ..####....   fork scene: first step onto z=19 (any row), see Arc1Seams_HandleStep
    y2  ..........   on at z=13 (from the ledge 12,14), under the trees, off at z=22 (to 12,23)

On the wall: LEFT = +z, RIGHT = -z, UP = climb, DOWN = descend (or hop off at the two ends).
Scripts: `res/field/scripts/scripts_distortion_world_arc1_seams.s`; objects and the fork / idle-hint step hook:
`src/overlay009/ov9_02249960.c` (`sArc1SeamsObjects`, `Arc1Seams_HandleStep`).
