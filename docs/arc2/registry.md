# Arc 2 registry (R0)

Everything shared that Arc 2 workstreams code against, registered on `a2/r0` (merged into `arc2`). Nobody else
appends to these registries. If a workstream needs another entry, it asks the orchestrator.

## Vars and flags (`generated/vars_flags.txt`)

| Name | Value | Use |
|---|---|---|
| `VAR_ARC2_PROGRESS` | 0x4070 | the Arc 2 ladder (PLAN.md section 3) |
| `VAR_ARC2_SUSPECT` | 0x4073 | ledger picks: 2 bits per leak (L0 bits 0-1 ... L3 bits 6-7; 0 Cyrus, 1 Garius, 2 Ruth, 3 bad luck); "answered" bits 8-11 |
| `VAR_ARC2_CHOICES` | 0x4090 | bit 0 Looker trust, bit 1 Basin answer, bit 2 Skarmory boost pulled, bit 3 Cyrus crate seen |

Flags, named by owner. Workstreams can rename their own flags to meaningful names; the lead applies the rename
at merge.

| Owner | Flags |
|---|---|
| lead | `FLAG_ARC2_LEAD_A..D` (0x0920-0x0923) |
| resonator | `FLAG_ARC2_RESONATOR_A..B` (0x0924-0x0925) |
| rift-a | `FLAG_ARC2_RIFTA_A..D` (0x0926-0x0929) |
| rift-b | `FLAG_ARC2_RIFTB_A..D` (0x092A-0x092D), `FLAG_ARC2_ELIAS_CARD` (0x092E), `FLAG_ARC2_RIFTB_E` (0x092F); `FLAG_ARC2_RIFTB_C` = Lost Tower vein found (rift contract) |
| s-jubilife | `FLAG_ARC2_JUBILIFE_A..D` (0x0930-0x0933) |
| s-cutaways | `FLAG_ARC2_CUTAWAYS_A..B` (0x0934-0x0935) |
| s-route204 | `FLAG_ARC2_ROUTE204_A..D` (0x0936-0x0939) |
| s-floaroma | `FLAG_ARC2_FLOAROMA_A..D` (0x093A-0x093D) |
| s-eterna | `FLAG_ARC2_ETERNA_A..D` (0x093E-0x0941) |
| s-celestic | `FLAG_ARC2_CELESTIC_A..D` (0x0942-0x0945) |
| s-veilstone | `FLAG_ARC2_VEILSTONE_A..E` (0x0946-0x094A) |
| s-route214 | `FLAG_ARC2_ROUTE214_A..B` (0x094B-0x094C) |
| s-pastoria | `FLAG_ARC2_PASTORIA_A..D` (0x094D-0x0950) |
| s-raid | `FLAG_ARC2_RAID_A..D` (0x0951-0x0954) |
| s-hearthome | `FLAG_ARC2_HEARTHOME_A..G` (A-C 0x0955-0x0957, D-G 0x095C-0x095F) |

## Distortion World maps

| Header (id) | Owner | Files (all owned by the rift workstream) |
|---|---|---|
| `MAP_HEADER_DW_RAVAGED_PATH` (596) | rift-a | `scripts_dw_ravaged_path.s`, `scripts_init_dw_ravaged_path.s`, `events_dw_ravaged_path.json`, `res/text/dw_ravaged_path.json` (`TEXT_BANK_DW_RAVAGED_PATH`), matrix 291 (`map_data_669/670`), `tools/distortion_world/ravaged_path.json` (attr 13-16), location `LocationNames_Text_DWRavagedPath` |
| `MAP_HEADER_DW_ETERNA_FOREST` (597) | rift-a | `..._dw_eterna_forest...`, matrix 292 (`map_data_671/672`), attr 17-20, `LocationNames_Text_DWEternaForest` |
| `MAP_HEADER_DW_ROUTE_214` (598) | rift-b | `..._dw_route_214...`, matrix 293 (`map_data_673/674`), attr 21-24, `LocationNames_Text_DWRoute214` |
| `MAP_HEADER_DW_ROUTE_213` (599) | rift-b | `..._dw_route_213...`, matrix 294 (`map_data_675/676`), attr 25-28, `LocationNames_Text_DWRoute213` |
| `MAP_HEADER_DW_LOST_TOWER` (600) | rift-b | `..._dw_lost_tower...`, matrix 295 (`map_data_677/678`), attr 29-32, `LocationNames_Text_DWLostTower` |

- Each map is a working stub: a copy of the arc1 seams floor (a B1F clone) at DW offset (0,0,0). It has an
  entry at (20,12) facing west and an exit coord event at (17,12). The rift contract is in
  `docs/arc2/rift_contract.md`.
- In `src/overlay009/ov9_02249960.c`, each map has its own object list (`sArc2Dw<Name>Objects`, local IDs
  0x80+) and its own step hook (`Arc2Dw<Name>_HandleStep`). Edit only your own. rift-a also owns the crumble
  hook in `ov9_0224A71C`.
- The location names all read "Distortion World" for now. Each rift workstream can change only its own entry.
- `tools/distortion_world/register_arc2_dw.py` did the registration and is idempotent.
- `tw_arc.narc` / `tw_arc_attr.narc` are binary, so both rift workstreams will conflict on them. To resolve,
  take either side, then run `python3 tools/distortion_world/twarc.py build tools/distortion_world/<map>.json`
  for each of the other side's maps. The builds are idempotent and the attr ids are reserved per map.
  `twarc.py check <spec>` verifies the result.

## Items and text

- `ITEM_RESONATOR` reuses the `ITEM_UNUSED_127` slot (key item, data row 0x1CC). Its 4 text files are written.
  It uses the Portal Reader icon (`src/item.c`; the resonator workstream owns that line until art lands).
- `TEXT_BANK_ARC2_COMMON` (`res/text/arc2_common.json`): the ledger prompt and its four choices
  (`Arc2Common_Text_LedgerWhoKnew`, `_LedgerCyrus`, `_LedgerGarius`, `_LedgerRuth`, `_LedgerBadLuck`), plus
  `Arc2Common_Text_ResonatorMissing` and `Arc2Common_Text_ResonatorSurge` ({STRVAR_1 1, 0, 0} = the totem
  species). The resonator workstream owns the Resonator lines; append new messages at the end.

## Trainers

- Classes: `TRAINER_CLASS_ECLIPSE_GRUNT_M`, `TRAINER_CLASS_ECLIPSE_GRUNT_F`, `TRAINER_CLASS_ECLIPSE_LEADER`.
  - Placeholder front sprites: Galactic grunt M/F and Mars.
  - Class names: "Eclipse" for the grunts (shown as "Eclipse Grunt") and "Eclipse Leader".
  - Galactic encounter effects, eye music and victory music.
  - Gender: M / F / F. The leader is female for Indra, the only Arc 2 user. Kahn and Saros need their own
    class or this one in Arc 3.
- The ids reuse the unused `TRAINER_DUMMY_779..809` slots. They are **not appended**: trainer-defeated flags
  are 1360 + id, so any id past 943 would alias `FLAG_TOTEM_*` (0x900+). Never append to
  `generated/trainers.txt`.

| Id (slot) | Placeholder (data owner fills it in) |
|---|---|
| `TRAINER_LEADER_MAYLENE_METEOR_TRIAL` (779) | Lucario 31 (trainers-gym) |
| `TRAINER_CYRUS_ARC2_{1,2,3}_{TURTWIG,CHIMCHAR,PIPLUP}` (780-788) | the starter weak to the player's: 17 / 27 / 36 (trainers-story) |
| `TRAINER_GARIUS_ARC2_{ETERNA,HEARTHOME}_{TURTWIG,CHIMCHAR,PIPLUP}` (789-794) | the starter strong vs the player's: 26 / 38, class `TRAINER_CLASS_RIVAL` |
| `TRAINER_INDRA_DEPOT` (795) | Honchkrow 30, class `TRAINER_CLASS_ECLIPSE_LEADER` |
| `TRAINER_ECLIPSE_GRUNT_ARC2_01..14` (796-809) | odd numbers M, even numbers F. 01-02 Ravaged Path (Lv 15), 03-04 Haven (22), 05-06 Route 214 (30), 07-10 depot (28), 11-12 Route 213 (33), 13-14 Lost Tower (38) |

- **The suffix is the player's starter** (the stock rival convention). `CYRUS_ARC2_1_TURTWIG` is the battle
  when the player chose Turtwig, so Cyrus holds Piplup.
- An event `"script"` for trainer id T is 3000 + T - 1 (singles) or 5000 + T - 1 (doubles), as in stock
  (`Script_GetTrainerID`).
- Cyrus's placeholder class is `TRAINER_CLASS_GALACTIC_BOSS`, which shows as "Galactic Boss Cyrus".
  trainers-story should pick the class he should show.

## Field sprites (`generated/object_events_gfx.txt`)

| Constant | mmodel member | Layout | Placeholder from |
|---|---|---|---|
| `OBJ_EVENT_GFX_INDRA` | 484 | walker | Jupiter |
| `OBJ_EVENT_GFX_KAHN` | 485 | walker | Sailor |
| `OBJ_EVENT_GFX_LOOKER_JANITOR` | 486 | walker | Looker |
| `OBJ_EVENT_GFX_LOOKER_NEWSPAPER` | 487 | walker | Looker |
| `OBJ_EVENT_GFX_ECLIPSE_CRATE` | 488 | idle2 | Rock Smash rock |
| `OBJ_EVENT_GFX_SHARD_FRAME` | 489 | idle2 | Rock Smash rock |
| `OBJ_EVENT_GFX_RIFT_ARC2` | 490 | idle2 | Rock Smash rock |

- art-ph replaces only `res/field/objects/arc2/<name>.png`. The sheet rules are in
  `docs/arc1/part2/sprites.md` (walker 128x128, idle2 64x32, 16 colours, index 0 transparent).
- Tool: `tools/integrate_arc2_field_sprites.py` (`check`, `extract-placeholder`).

## Decisions applied in R0

- **D14** (`src/totem_battle.c`): Skarmory 32 and Spiritomb 40, each with allies 2 levels below (30 and 38).
  The other totems are unchanged. The Skarmory +1/+1 boost field is rift-b's job.
- **D16, the violet room:** `MAP_HEADER_GALACTIC_HQ_CONTROL_ROOM` (id 494).
  - A small room with one warp (to the HQ Laboratory, deep inside the Galactic HQ), unreachable in Arc 2.
  - It holds the stock lake-trio tubes, dim lighting, and no map-name popup on entry (checked headlessly).
  - s-cutaways owns its scripts, events and text. The stock objects (Saturn, Charon, the trio) are hidden by
    stock flags and should stay hidden.
  - If the header's "Galactic HQ" label ever shows, ask the lead to change `mapLabelTextID`.

## Harness

`/tmp/a2/harness/` (see its README): `setstate.py` (start at any block), `textlint.py`, `a2lib.py`, and the
golden save `/tmp/a2/golden/post_gym1.sav`.
