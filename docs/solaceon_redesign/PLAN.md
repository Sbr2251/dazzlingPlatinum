# Solaceon Town redesign: the Sanctuary town and the Ruins raid

Owner decisions (2026-11-24):

1. Canon framing stays as the bible says: Solaceon is **the heart of Team Eclipse's public support**. It is not
   Eclipse's headquarters. Eclipse runs a public Sanctuary here (grief support, the memorial wall, the registry of
   the dead), and believers live here because they lost someone.
2. There is a **playable raid**, and it **reuses the Solaceon Ruins**. Under the Sanctuary's "excavation" of the
   Ruins, Eclipse keeps a shard vault. The raid goes through the existing Ruins rooms.
3. It is a **sizable rebuild**: overworld chunks 072 and 073 get a new layout and new art, the Sanctuary gets its
   own new interior map, and the Ruins are dressed for the raid.

This file is the contract every workstream codes against. If you need something that is not here (another flag,
another trainer slot, a new map header), stop and report it in your final message. Do not invent shared IDs.

## 1. Story placement

| When | What the player sees in Solaceon | Keys on |
|---|---|---|
| Arc 2, first visit (state 44-53) | Pilgrim season. The Sanctuary is open, the memorial wall, the registry tent, the banners (from 47). The 2.16a Indra cutaway (existing, keep it working). Characters have no proof Eclipse tortures anyone, so the town must read as warm and kind; the menace is for the player only. | `VAR_ARC2_PROGRESS` |
| Arc 2, after the depot heist (54-85) | Security tightens: robed grunts at the Sanctuary gate and at the Ruins "excavation" fence. Back rooms locked. | `VAR_ARC2_PROGRESS` |
| Arc 2, after Rowan's retraction (86-99) | Banners quoting Rowan are torn down. Some believers leave; the town is split. | `VAR_ARC2_PROGRESS` |
| Arc 3, before the raid | Eclipse holds Dialga (3.3). The Sanctuary is shut "for the Return". Believers wait at the wall. | `VAR_ARC2_PROGRESS` = 99 and `VAR_SOLACEON_PROGRESS` < 10 |
| **Arc 3, scene 3.4a: the raid** | New scene between 3.4 (Hearthome, the morning after) and 3.5 (Canalave). Looker has traced the shard stockpile from the Distortion World vein to the vault under the Ruins. Destroying it buys time before Palkia. The group goes in. | `VAR_SOLACEON_PROGRESS` 10-49 |
| Arc 3, after the raid | The Sanctuary is seized by the International Police. The wall stays; believers mourn. | `VAR_SOLACEON_PROGRESS` 50 |
| Postgame | The wall becomes a real memorial garden. | `FLAG_GAME_COMPLETED` |

Raid outline (story workstream writes the real scene; these are the fixed beats):

- 3.4 ends with Ruth/Looker's reading: the vein's shards are being stored at Solaceon. (3.4 is not built yet: the
  future Arc 3 work sets `VAR_SOLACEON_PROGRESS` to 10. Until then, test saves set it.)
- Looker meets Darren and Cyrus at Solaceon. The way in is through the Ruins (the "excavation").
- The Ruins rooms are held by grunts; Eclipse equipment fills the rooms (crates, shard frames, violet crystals).
- **Mechanic (fixed):** the vault in the last Ruins room (Room 7) is sealed by a shard-powered barrier fed by three
  generators in Ruins dead-end rooms. Switch all three off and the barrier drops. Generators and barrier are object
  events or permission toggles, never terrain, so scripts can switch them.
- The vault is the last Ruins room. **Indra** guards it (her second battle; the first was the depot, 2.17a). She
  guards the plan, as the bible says. She loses and escapes; she is not caught (her ending is the Umbral Palace,
  3.11).
- The stockpile is destroyed, but **Kahn already left with enough for Palkia** (so 3.6 still happens). Looker
  recovers the registry ledger (every card on the wall was copied into it).
- The Sanctuary is seized.
- Must not contradict: bible.md, secrets.md, arc3_screenplay.md 3.5-3.18. Garius is revealed at 3.2, so he can be
  mentioned; he is with Kahn, not in the vault.

## 2. Registry (shared IDs)

All new; registered by the lead (the orchestrator) on branch `solaceon`. Rename only these, only by these names.

### Vars (`generated/vars_flags.txt`)

| Name | Slot | Use |
|---|---|---|
| `VAR_SOLACEON_PROGRESS` | `VAR_UNK_0x40AF` | the raid ladder below |
| `VAR_ARC3_PROGRESS` | `VAR_UNK_0x40B0` | reserved for the future Arc 3 work. Do not use. |

`VAR_SOLACEON_PROGRESS` ladder:

| Value | Meaning |
|---|---|
| 0 | not started |
| 10 | raid briefed (set by Arc 3 scene 3.4; test saves set it today) |
| 20 | met Looker at Solaceon, raid on |
| 30 | inside the Ruins |
| 40 | reached the vault |
| 45 | Indra beaten |
| 50 | raid done, Sanctuary seized |

Intermediate values inside a band belong to the raid workstream (for example 31-39 for room progress).

### Flags (`generated/vars_flags.txt`, slots `FLAG_UNK_0x0A40`-`0x0A5F`)

| Owner | Names | Slots |
|---|---|---|
| town-scripts | `FLAG_SOL_TOWN_A..H` | 0x0A40-0x0A47 |
| town-scripts (Sanctuary interior) | `FLAG_SOL_SANCTUARY_A..D` | 0x0A48-0x0A4B |
| raid-scripts | `FLAG_SOL_RAID_A..P` | 0x0A4C-0x0A5B |
| lead | `FLAG_SOL_LEAD_A..D` | 0x0A5C-0x0A5F |

Object-event `hidden_flag`s use these too. The existing `FLAG_UNK_0x0030` (Indra cutaway) and `FLAG_UNK_0x0031`
(banners) in `events_solaceon_town.json` stay as they are.

### Trainers (reuse dummy slots; never append to `generated/trainers.txt`)

| Slot | Name | Use |
|---|---|---|
| 810 | `TRAINER_INDRA_SANCTUARY` | Indra, battle 2, the vault. Class `TRAINER_CLASS_ECLIPSE_LEADER` |
| 811-816 | `TRAINER_ECLIPSE_GRUNT_SOL_01..06` | raid grunts (odd M, even F) |
| 833-834 | `TRAINER_ECLIPSE_GRUNT_SOL_07..08` | raid grunts, or the Sanctuary gate pair |

Script id for trainer T: 3000 + T - 1 (singles), 5000 + T - 1 (doubles). Trainer-defeated flag = 1360 + T.

### Existing assets to reuse

- Field sprites: `OBJ_EVENT_GFX_INDRA`, `OBJ_EVENT_GFX_ECLIPSE_GRUNT_M/F`, `OBJ_EVENT_GFX_LOOKER_JANITOR`,
  `OBJ_EVENT_GFX_ECLIPSE_CRATE`, `OBJ_EVENT_GFX_SHARD_FRAME`, `OBJ_EVENT_GFX_VIOLET_CRYSTAL`,
  `OBJ_EVENT_GFX_RIFT_ARC2` (see `docs/arc2/registry.md`). Cyrus and Looker field sprites exist from Arc 1/2.
- Text banks: `TEXT_BANK_SOLACEON_TOWN` and the Ruins/interior banks. Append messages at the end only.

## 3. The overworld: fixed anchors

Solaceon is overworld matrix 0, cells (17,20) = `map_data_072` (x 544-575, z 640-671) and (18,20) = `map_data_073`
(x 576-607, z 640-671). Area 0xA, texture set 010. **Set 010 and area 0xA are shared** with Routes 209, 210,
211 East, 215 and Celestic: append textures only, never change or remove stock ones. Set 010 is about 46 KB; the
proven-safe ceiling is 76,416 B (set 048). Budget for this redesign: **+24 KB** in set 010, leaving headroom.

Fixed (do not move without asking the lead):

| What | Tiles | Why |
|---|---|---|
| Pokemon Center door | (566,656) | warp; the Arc 2 Center TV/viewer scripts |
| Mart door | (571,665) | warp |
| Day Care door | (553,645) | warp; Day Care gameplay |
| Memorial wall signs + reading tiles | wall x 556, z 652-656; reading tiles x 557, z 652-656 | 2.16a sign events and the Indra cutaway (Indra at (557,654)) |
| Ruins entrances | (595,655) Ruins Room 1, (597,652) Maniac Tunnel room | the raid route |
| North seam z 640 | must match Route 210 South (`map_data_068`) row z 639: same walkable columns and heights | |
| South seam z 671 | must match Route 209 (`map_data_074`) row z 672 | |
| East/west edges | x 544 and x 607 border filler `map_data_176` | keep them blocked |

Free to change: everything else, including the News Press, North House, Northeast House and East House (their doors
may move or go away; report the final door tiles). Interiors can be reused for believers' homes.

## 4. Town concept (zones)

The layout workstream turns this into `tools/solaceon_town/layout.py` (the tile contract) and reports exact tiles.

1. **The pilgrim road (north, from Route 210).** The main road comes in from the north between banner posts. A
   **registration tent** beside the road, where Eclipse writes down each death (name, date, place). Pilgrims queue.
2. **The memorial plaza (centre, around the existing wall).** The stock fence wall becomes the centrepiece of a
   paved plaza: benches, lanterns, flower offerings. A small patch of grass by the plaza (the "garden of names") is
   where Yamask and Duskull live.
3. **The Sanctuary compound (east; takes the News Press lot, the east houses and the space in front of the Ruins
   hill).** A walled compound with a gate, a forecourt with an eclipse emblem in the paving, and the **Sanctuary
   hall**: a bespoke building, **footprint 9 tiles wide x 5 deep, door at the middle of the south face, about 4 tiles
   tall**, wider and taller than a house, violet roof, pale stone, Platinum proportions. Its door
   leads to the new Sanctuary interior map.
4. **The excavation (the Ruins hill, behind the compound).** The Ruins entrances are fenced off with Eclipse
   scaffolding, work lights and crates; a grunt stands at the gap from state 54 (object event). In the raid this is
   the way in.
5. **The ranch (south-west).** Keep the Day Care and its pens. Add a kennel block "for the Pokemon of the departed"
   (an echo of the Eterna Haven) and a loading yard with a truck by the south exit; ruts lead toward Route 209.
6. **Believers' houses** on the remaining lots, reusing stock house props.

Style rules (how we stay true to Platinum):
- Reuse and recolour stock props and textures first. New models only where nothing stock fits (the Sanctuary hall,
  the tent, the excavation scaffolding, the plaza paving).
- 16-colour textures at stock pixel density; palettes sampled from stock set 010 so the town sits in the same light.
- Map materials lit like stock (they follow the time-of-day light). Bake lighting only into small accents.
- Read through the real field camera (`blender_preview.py --views game`): it sees about 15x11 tiles at a 55 degree
  pitch, so silhouettes and roofs matter more than detail.
- Budgets: 1000 polygons and 45 KB of model per chunk (hard limit 0xF000 bytes uncompressed); 2048 polygons on
  screen.

## 5. Tech stack

All standard-library Python run with the system `python3`, plus Blender 5 (`/Applications/Blender.app`) for
authoring and previews. Nothing needs the ROM toolchain until the build.

- `tools/lake_verity/`: `nsbmd.py`, `nsbtx.py`, `mapdata.py`, `collision.py`, `assemble.py`, `png.py`,
  `blender_preview.py`, `compare_layout.py`; full docs in `docs/lake_verity_redesign/pipeline.md`.
- `tools/world_art/chunkedit.py`: in-place chunk edits that keep untouched stock shapes byte for byte.
- `tools/lake_verity/build_interior.py` + `interior_layout.py`: the pattern for a new interior map (header, matrix,
  map_data, texture set, area entry, registration).
- Examples: `tools/solaceon_town/` (the existing wall), `tools/veilstone_city/`, `tools/route_212_north/`,
  `tools/distortion_world/`.
- Every builder reads its stock inputs from git at a fixed `BASE_REV` (use `50482f890`), so re-running never feeds
  back on itself, and has a dry run, a `--preview DIR` and a `--write`.
- Previews go to `~/Documents/Solaceon Update/` (create it).

The build target is the **macOS app** on branch `solaceon-mac` (see section 7). No devserver.

## 6. Workstreams

Each workstream works in its own git worktree on its own branch, commits there, and does not push. The lead merges
into `solaceon`.

| Workstream | Phase | Owns (writes) | Delivers |
|---|---|---|---|
| **story** | 1 | `docs/solaceon_redesign/screenplay.md`; edits to `docs/story/bible.md`, `map_changes.md`, `artwork.md`, `build_backlog.md`, `trainers.md`, `secrets.md` (Solaceon/raid lines only) | Every Solaceon scene and NPC line per state, the raid scene 3.4a, trainer teams and levels, rewards |
| **town-layout** | 1 | `tools/solaceon_town/layout.py`, `collision.py`-style builders, the graybox builder, `map_data_072/073.bin` (graybox), `docs/solaceon_redesign/layout.md` | The tile contract, a graybox that a build can walk, exact tiles for every door, sign, NPC spot and the Sanctuary door |
| **textures** | 1 | `tools/solaceon_town/assets/textures/` (PNG + JSON in the lake_verity format), `tools/solaceon_town/art/` (paint scripts), `docs/solaceon_redesign/art.md` | The texture kit (town, Sanctuary exterior, plaza, tent, excavation, vault dressing), a contact sheet, VRAM totals. Does **not** write set 010. |
| **sanctuary-interior** | 1 | a new interior map: header, matrix, map_data, own texture set, area entry, registration lines; `tools/solaceon_town/interior/`; `docs/solaceon_redesign/interior.md` | A walkable Sanctuary hall interior (public hall, records office, locked back door) with its exit warp and spots for NPCs |
| **raid-maps** | 1 | Ruins `map_data` and their texture set (append only); `tools/solaceon_ruins/`; `docs/solaceon_redesign/raid_maps.md` | The raid route through the existing Ruins rooms, vault dressing in the last room, exact tiles for grunts, objects and Indra |
| town-art | 2 | final `map_data_072/073`, set 010 appends | The art pass over the graybox |
| town-scripts | 2 | `events_solaceon_town*.json`, `scripts_solaceon_town*.s`, `solaceon_town*.json` text, the Sanctuary interior's events/scripts/text | All town states |
| raid-scripts | 2 | Ruins events/scripts/text, `res/trainers/data` for slots 810-816, 833-834 | The playable raid |
| lead | 3 | registry, merges, build, headless test, commit, push | |

Rules:
- ASCII only in text and JSON (straight apostrophes; no curly quotes).
- Append-only on shared files (`generated/*.txt`, `.order` files, `meson.build` lists, text banks).
- Never change a stock texture, palette or another map's chunk.
- Every builder prints its budgets and refuses `--write` if a check fails.

## 7. Target: the macOS app (owner decision, 2026-11-24; supersedes the devserver)

The redesign ships in the native macOS port, branch **`solaceon-mac`**, cut from `perf/integ-mac` (it already contains
`main` and all of Arc 2). Build: `tools/macos/build.sh dev` (about 15 minutes from clean, incremental after) ->
`build_macos/Dazzling Platinum.app`. The lead's worktree is `/tmp/dpmac/dazzlingPlatinum` (home and `~/Documents` are
not writable from these sessions).

What is different on `solaceon-mac` (it merged current upstream pret):

| What | `main` / `solaceon` | `solaceon-mac` |
|---|---|---|
| Map chunks, texture sets | `res/field/maps/data/`, `res/field/maps/texture_sets/` | `res/field/mapmodels/data/`, `res/field/mapmodels/texture_sets/` (same bytes) |
| Per-map header, events, scripts, init, encounters | `include/data/map_headers.h`, `res/field/events/events_<map>.json`, `res/field/scripts/scripts_<map>.s` | one folder per map: `res/field/maps/<map>/header.json`, `events.json`, `scripts.s`, `init.s`, `encounters.json` |
| Flags 0x0B00-0x0B5F | `FLAG_UNK_*` | **daily flags** (cleared every day). The Solaceon flags therefore moved to **0x0A40-0x0A5F** (section 2). |
| Unused vars | `VAR_UNK_0x40AF/B0` | `VAR_UNUSED_0x40AF/B0` (same slots) |
| Trainer JSON | `"power"` | `"iv_scale"` |

Headless testing (`docs/headless_protocol.md`): `SIM_CONTROL=stdio build_macos/main` takes JSON commands
(`warp`, `set_var`, `set_flag`, `give_item`, `talk`, `press`, `step`, `screenshot`, `state`). Scenarios live in
`tools/dazzling/test/scenarios/` and run with `python3 tools/dazzling/test/run.py`. The golden saves in `~/Downloads` are
not readable from these sessions, so Solaceon scenarios start from the new-game prologue and set the state with
`set_var` / `set_flag` / `warp`.
