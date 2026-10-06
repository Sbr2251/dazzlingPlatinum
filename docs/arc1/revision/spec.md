# Arc 1 revision: implementation contract (v2)

Branch `arc1-story-revision`. Read `docs/arc1/revision/PLAN.md` first. The owner approved ALL of its
"Suggested improvements". This file is the contract between the workstreams: decisions, shared names,
story state, file ownership, handoffs, build and test rules. It supersedes `docs/arc1/spec.md` where they
disagree.

## Decisions (answers to PLAN.md open questions)

1. Cyrus's gift is a new key item, **`ITEM_ECLIPSE_SHARD`** ("Eclipse Shard": a cracked violet shard). The
   agitated Mawile drops it after the battle in the DW, Cyrus picks it up ("Someone has been... harvesting."),
   and he gives it to the player at the Lake Verity parting ("Take it to Rowan when he's ready to listen.
   ...Maybe this will help you out."). It's a key item with no use effect.
2. Barry picks a starter in the DW (stock rule: strong against the player's) and fights nothing on screen.
   Only one Mawile, the player's battle. No tag battle in this pass.
3. Dawn (the assistant, still opposite gender to the player via `BufferCounterpartName`, the existing
   behaviour) stays at the portal on the terrace, does not enter the DW, and closes the portal on return
   ("Readings are dropping, it's closing!").
4. Flashback hero is a **Lucas NPC** (`OBJ_EVENT_GFX_PLAYER_M` or equivalent), with the player hidden as a
   camera anchor.
5. BREAKING NEWS is text plus a sound effect, merged into one continuous broadcast with the interview.
6. After the return scene, Rowan and Dawn leave the terrace (walk off and are removed), then Cyrus, then Barry.
7. Heal after the Mawile battle (keep `HealParty`).
8. "1.7x": do BOTH. The title-screen pre-rendered Giratina loop plays at 1.7x, and the flashback's waits are
   scaled by about 1/1.7.
9. Puzzle: **Phase 0 / fallback first** (a new standalone DW map cloned from B1F, with the wall grid edited for
   the fork). Phase 1 custom terrain is out of scope for this pass.
10. No alcove item: the dead-end alcove stays walkable but holds nothing, so the player has no Poke Balls before the Mawile fight and cannot catch it.
11. The player chooses to go in: Rowan forbids the kids; Cyrus volunteers; Barry runs into the portal before
    anyone can stop him; the player steps in via the launchpad Yes/No.

## Story state (`generated/vars_flags.txt`, owned by the lead; already edited)

| name | meaning |
|---|---|
| `VAR_ARC1_PROGRESS` | ladder below |
| `VAR_ARC1_DW_HINTS` (was `VAR_UNUSED_0x406D`) | DW puzzle hint/idle bookkeeping; DW workstream defines values |
| `VAR_ARC1_DW_FALLS` (was `VAR_UNUSED_0x406E`) | DW fall counter (0 = Barry's demo fall not yet played) |
| `FLAG_UNUSED_2448` (was `FLAG_ARC1_DW_ALCOVE_ITEM`, removed with the alcove Poke Balls) | spare; ask the lead before using |
| `FLAG_LAKE_VERITY_PORTAL_HIDDEN` | unchanged |

Spare, ask the lead before using: `VAR_UNUSED_0x406F`, `VAR_UNUSED_0x4031`, `FLAG_UNUSED_2449`, `FLAG_UNUSED_2421`.

| val | state | set by |
|---|---|---|
| 0 | new game; flashback | default |
| 1 | flashback done; roof landing plays | Opening |
| 2 | roof landing done; bedroom TV | Lake Verity |
| 3 | TV/Barry done; heading to the lake | Intro & home |
| 4 | castle briefing done; portal open; player must step in (Barry blocks the stairs down) | Lake Verity |
| 5 | inside the DW, puzzle running | Lake Verity (launchpad, just before the warp) |
| 6 | starter picked, Mawile fought, shard picked up; leaving the DW | DW |
| 7 | back on the terrace; return scene pending | DW (just before the warp out) |
| 8 | Arc 1 done; Route 201 "to be continued" | Lake Verity (end of return scene) |

## Handoffs

| from | to | how |
|---|---|---|
| Lake Verity launchpad (state 4) | DW puzzle entry | Lake Verity: Yes/No, `ScrCmd_320` warp cutscene, `SetVar VAR_ARC1_PROGRESS, 5`, `Warp <DW header>, 0, <x>, <z>, <dir>`. **The DW workstream publishes the header name and entry tile in `/tmp/arc1/dw_entry.txt` once the map builds. Lake Verity must not reference the new header constant before that file exists** (it would break everyone's build). Until then, keep the warp behind a placeholder (for example the stock DW 1F header). |
| DW (after battle) | Lake Verity terrace | DW: exit rift beside the briefcase, `ScrCmd_320`, `SetVar VAR_ARC1_PROGRESS, 7`, `Warp MAP_HEADER_LAKE_VERITY, 0, 32, 31, DIR_NORTH`. Lake Verity's init/frame script takes over at state 7. |
| Route 201 | Lake Verity | unchanged (state 3) |
| return scene | free roam | `SetVar VAR_ARC1_PROGRESS, 8`; Route 201 "to be continued" now keys on 8 |

`ITEM_ECLIPSE_SHARD`: the Items workstream adds the constant, CSV row and the 4 text entries **first** (within
its first build), then the icon. Until `grep -q ITEM_ECLIPSE_SHARD generated/items.txt` succeeds, the DW
and Lake Verity workstreams must not reference it.

## File ownership

Only edit files you own. If the build fails in a file you don't own, it's another workstream's WIP: wait a
minute and rebuild (up to about 15 minutes), and don't touch that file. Anything you need from a file you
don't own goes in your final report (exact patch).

| workstream | owns |
|---|---|
| **Intro & Opening** | `res/text/rowan_intro.json` (and `src/applications/rowan_intro/**` only if needed); `scripts_twinleaf_town*.s`, `scripts_init_twinleaf_town*.s`, `events_twinleaf_town*.json`, their text JSONs; `scripts_route_201.s`, `scripts_init_route_201.s`, `events_route_201.json`, `res/text/route_201.json`; `scripts_distortion_world_giratina_room.s`, `scripts_init_distortion_world_giratina_room.s`, `events_distortion_world_giratina_room.json`, `res/text/distortion_world_giratina_room.json`; `src/field_map_change.c` (flashback caption) |
| **Distortion World** | `src/overlay009/**` (sole editor; the flashback's fly-by table entries too, on request); new map header lines in `generated/map_headers.txt`, `include/data/map_headers.h`, `res/text/location_names.json`; new matrix/map data/area files and the meson/order lines that register them; `res/prebuilt/fielddata/tornworld/**`; `tools/distortion_world/**` (new); the new DW map's scripts, init script, events and text bank (new files, plus the meson/order registration for them); `scripts_distortion_world_1f.s` (only an Arc 1 guard, if needed); `src/encounter.c` / `include/encounter.h` comments only |
| **Lake Verity** | `scripts_lake_verity.s`, `scripts_init_lake_verity.s`, `events_lake_verity.json`, `res/text/lake_verity.json`, Lake Verity movement data; `docs/lake_verity_redesign/gameplay.md` |
| **Items & Title** | `generated/items.txt`, `res/items/pl_item_data.csv`, the 4 item text JSONs, `res/graphics/item_icons/**`, `src/item.c`; `src/applications/title_screen.c`, `res/graphics/title_screen/**`, `tools/giratina_title/**` |
| **lead** | `generated/vars_flags.txt`, `docs/arc1/**` |

Shared registries that more than one workstream may need to append to (`res/field/scripts/meson.build` or
script order files, `res/text/meson.build` or the text bank order, `generated/text_banks*` and so on): **only
append a line, never reorder or reformat**, and re-read the file right before editing. If a registry needs
anything more than an append, ask the lead.

Nobody commits, pushes, switches branches, stashes, or runs `git checkout`/`git restore`/`git reset` on files.
The lead commits by path at the end.

## Build and test

- Always build with `flock /tmp/dp-build.lock make release` (from `/data/repos/dazzlingPlatinum`). An
  incremental build takes about 20 s. Never plain `make`, never delete the Meson lock, and never build without
  the flock.
- The ROM is `out/dazzlingPlatinum.nds`. Copy it somewhere private before testing
  (`cp out/dazzlingPlatinum.nds /tmp/arc1/<you>.nds`); the next build overwrites it.
- Headless emulator: `~/.venvs/desmume/bin/python` with py-desmume. Helpers are in `tools/`:
  `make_desmume_dsv.py`, `platinum_save_utils.py`, `verify_platinum_save.py`, `tools/debug/`. Put your test
  harnesses, saves and screenshots under `/tmp/arc1/<you>/`, not in the repo.
- Validate your own scenes in the emulator: get to the state (edit the save's `VAR_ARC1_PROGRESS` and
  position, or play through), take screenshots at key beats, and check there are no hangs or softlocks.
- Text: ASCII apostrophes and quotes only. Keep message boxes to the stock line width: 27-tile boxes,
  2 lines per page, about 192-197 px max per line (measure with `res/fonts/font_message.json`). Write
  "Pokemon" with the e-acute the way neighbouring stock messages do.
