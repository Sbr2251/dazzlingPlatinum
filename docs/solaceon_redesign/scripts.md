# Solaceon redesign: the town scripts (town-scripts workstream)

What the town, the Sanctuary hall and the town side of scene 3.4a do in each state band, the flags and vars they
use, and the headless test. The text is `screenplay.md`, verbatim; the tiles are `layout.md` (town) and
`interior.md` (hall). Branch `sol-mac/town-scripts` (macOS tree, `solaceon-mac`).

Files:

| File | What |
|---|---|
| `res/field/maps/solaceon_town/events.json` | objects, signs, the fence coord trigger (warps untouched) |
| `res/field/maps/solaceon_town/scripts.s`, `init.s` | band selection, every NPC and sign, scenes 3.4a parts 1, 2 and 7 |
| `res/field/maps/solaceon_town/encounters.json`, `header.json` | the garden of names; `preloaded` 15 (see "Sprite budget") |
| `res/field/maps/solaceon_sanctuary/events.json`, `scripts.s`, `init.s` | the hall (new `init.s`; `scripts_init_solaceon_sanctuary` appended to `res/field/scripts.order`) |
| `res/text/solaceon_town.json`, `res/text/solaceon_sanctuary.json` | appended messages (stock and Arc 2 entries untouched) |
| `res/field/encounters.order` | `encounters_solaceon_town` appended |
| `tools/solaceon_town/screenplay_text.py` | writes the text banks from `screenplay.md` (`--write`), checks widths |
| `tools/solaceon_town/town_test.py` | the headless test |

## State bands

Both maps pick the band on every load (`SolaceonTown_GetBand` / `SolaceonSanctuary_GetBand`, into
`VAR_MAP_LOCAL_0x04`; init scripts have no script manager, so the special vars 0x8000+ can't be used there), first
match wins:

| Band | Test |
|---|---|
| F | `FLAG_GAME_COMPLETED` |
| E | `VAR_SOLACEON_PROGRESS` >= 50 |
| R | `VAR_SOLACEON_PROGRESS` >= 20 |
| D | `VAR_ARC2_PROGRESS` >= 99 (with `VAR_SOLACEON_PROGRESS` < 20; Looker and Cyrus from 10) |
| C | `VAR_ARC2_PROGRESS` 86-98 |
| B | `VAR_ARC2_PROGRESS` 54-85 |
| A | below 54 (also below 44, a sequence break) |

`OnTransition` hides every band object (`HideAll`), then shows the band's set (`ShowA`..`ShowF`) and moves the
objects that stand elsewhere in that band (`SetObjectEventPos/Dir/MovementType`, the stock pattern). Every NPC and
sign script computes the band again when it runs.

### The town

| Band | Out (besides the always-there wall widow, lantern man, believer mother, kennel keeper, rancher, Day Care kid, Sunday man, Poketch man) | Notes |
|---|---|---|
| A | tent clerk, the four Route 202 pilgrims in the queue (565,645..648), road greeter, garden girl, gate greeter, forecourt sweeper, dig worker, ruin maniac, kennel Pokemon 1-4, doubter; Rowan banners from 47 | the 2.16a cutaway at 44 (unchanged); no crates (see "Sprite budget") |
| B | clerk, father at the wall (558,653), gate grunts L/R, sweeper, fence grunts M/F, kennel 1-2, loading grunt, doubter, crates 1-4 | |
| C | clerk, father at the wall, the sister leaving at the north road (561,641), garden girl, gate grunts, sweeper, fence grunts, kennel 1 (Skitty), doubter | Rowan banners and the four banner posts read the torn banner |
| D | clerk, father at the wall, the son beside the closed tent (567,645), gate grunts (L on the gate's front tile (580,659)), fence grunts, loading grunt, crates 1-6; from progress 10 Looker (558,657) and Cyrus (559,657) | hall door warp parked inside the hall, the door gives the locked message |
| R | D's townspeople (clerk, father, son, fence grunts, crates), with the R lines for clerk, widow and mother; Cyrus at the fence (597,662) until the pair is beaten | gate guards and loading grunt gone, door open |
| E | clerk at the empty tent, father, garden girl, IP officers at the gate (581,659), in the forecourt (575,655) and at the fence (596,660), ruin maniac, kennel 1 (the Skitty), doubter, crate 1 | the seizure plays on the first load; wall banner E text |
| F | the clerk as garden keeper (567,651), father (565,650), sailor (567,650), sister (565,652) in the garden, garden girl, dig worker, ruin maniac, kennel 1-4, doubter; Indra at the wall once | Rowan banners hidden, memorial plaque text, wall banner F text |

Signs (bg events, one text per band, nearest earlier band when the screenplay lists none): gate plaque (579,658,
readable from the gate tile and from inside too, because the left gate grunt stands on the front tile in B/C), tent
sign (564,644), excavation sign (594,659), kennel sign (554,664), postgame memorial plaque (557,650; F only), the four
banner posts (557/563, 643/647: the Rowan quote from 47 in A/B, the torn banner in C-E, nothing in F), the hall door
(580,652; band D only). The 2.16a wall signs are unchanged except the banner (E/F texts) and TEO (Indra's card after
the postgame scene).

Stock objects: the wandering cowgirl, rancher, Sunday cowgirl, "nothing but a road" rancher and twin are now the
kennel keeper, rancher, Sunday man (Gentleman), lantern man (Old Man) and Day Care kid at their layout spots, not
wandering. The News Press signboard is gone (its door is the Sanctuary's; the News Press map and its daily request are
unreachable, nothing else references them). The Pokemon History app giver is the stock wandering Ruin Maniac object
(`SolaceonTown_RuinManiac`), not `EXPERT_M_3` as layout.md says: that object is the Day Care Man
(`DayCareCommon_Man`), who stays at (555,648). The app giver is now `POKETCH_MAN` at (579,644) (sprite `EXPERT_M`, as
the screenplay suggests; script and text stock), and the new `RUIN_MANIAC` role is a separate object.

Kennel Pokemon: Skitty, Psyduck, Buneary, Pachirisu (cry on talk). The screenplay suggests Machop and Starly for 3-4;
Buneary and Pachirisu reuse the ranch's sprites (sprite budget).

### The Sanctuary hall

| Band | Out |
|---|---|
| A | speaker (10,8), hall attendant (7,18), testimonies A (6,12), B (14,12), C (13,16), records clerk (21,8); office open |
| B | speaker, testimonies A and C, hall grunt on the office doorway (19,13) (office shut), back door grunt (18,7), the clerk inside |
| C | speaker, testimony B leaving (12,18), testimony C, hall grunt, back door grunt, the clerk inside |
| D | nobody (the town door is locked; only a player who saved inside gets here, and leaves by the mat) |
| R | Looker at Indra's desk (23,9) until progress 40 |
| E | the last believer (testimony A's man) on the front bench, IP officers (11,14) and (24,11) |
| F | the reading keeper (the clerk) in the office |

Signs: lectern (10,9; readable from its sides too, because the speaker stands behind it in A-C), notice board = the
guest book stand (6,18), filing drawers = the shelves (20..22,7), (24..25,7) and the cabinet (25,9), the ledger
(22,10; in R it gives Looker's "Not now. I am reading."; in E/F the bare desk), Indra's desk (23,10), the back door
(18,6). The office is shut by the hall grunt object on the doorway, the method in interior.md.

## Scene 3.4a in town

- **Part 1, the briefing** (D, progress 10): talking to Looker or Cyrus. Both face the player; the nine messages;
  fade, `HealParty`, progress 20, Looker, the gate pair and the loading grunt removed, the door warp restored, Cyrus
  placed at the fence (597,662) facing west, the fence trigger armed. Talking to Cyrus there in R gives his "The vault
  is sealed" line.
- **Part 2, the fence** (R): a coord trigger on the only way into the dig dirt (x 592, z 660-661, armed through
  `VAR_MAP_LOCAL_0x03` while SOL_08 is unbeaten) walks the player to (594,660); talking to either grunt runs the same
  scene (the player walks to (594,660) from (595,660), (596,661) or (597,660), the tiles a grunt can be talked to
  from). Cyrus walks up beside the player (594,661); the three grunt
  lines; `TRAINER_ECLIPSE_GRUNT_SOL_07` then `_SOL_08` back to back (no heal; their trainer flags are set by the
  script after each win: `StartTrainerBattle` doesn't). Losing is `BlackOutFromBattle`; on the next load a beaten
  SOL_07 without SOL_08 is cleared (the pair reset). After both, F steps to (597,660), M to (596,661) (the gap and
  (595,660) are free), Cyrus's two lines, and he walks through the gap to the Room 1 entrance and is removed. From
  then on the pair stand aside with their post-battle lines (TRMSG_POST_BATTLE, duplicated in the town bank).
- **Part 7, the seizure** (E): raid-scripts sets 50 and warps to town (Room 7; this workstream moved
  `SOL_RAID_TOWN_X/Z` from (571,657) to (580,660), south of the gate). The first load at 50 arms
  `VAR_MAP_LOCAL_0x02`, and the frame table (before the city-entry cinematic) runs `SolaceonTown_Seizure`: if the
  player isn't on (580,660) it warps there (same map) and the reload plays it; then `FLAG_SOL_TOWN_A`, fade, Looker
  in front of the gate (580,659), Cyrus beside the player (579,660); Looker's lines; `ITEM_DUSK_STONE` x1 with the
  stock item-get message (skipped if the bag is full); Looker, Cyrus; the Poketch beep and Ruth; Looker walks into
  the compound and Cyrus off west, both removed.
- **Postgame Indra** (F, once): Indra (the 2.16a object) at (557,654); talking to her plays her three messages, she
  pins the card and leaves by the south road; `FLAG_SOL_TOWN_B`; the TEO sign reads her card from then on.

**No `SetPosition` of the player.** Moving the player to another row and column with `SetPosition` asserts in the map
loader (`land_data.c`, `LandDataManager_Tick`: a jump in x and z at once; fatal in the headless build, and on the DS
the loader stops following the player), and a locked player's sprite is not redrawn at the new tile (only its
shadow moves). The `AddFreeCamera` / `RestoreCamera` resync keeps the loader quiet but leaves the camera behind
(it follows by deltas). So the scripts walk the player (the fence) or use a same-map `Warp` behind the black screen
(the seizure fallback, and the 2.16a cutaway: on this tree its `SetPosition` to the wall crashed the headless build;
it now warps to (558,654) and steps back to the reading tile (557,654); what the player sees is unchanged). Arc 1/2
scripts elsewhere (Jubilife, Route 213) still use `SetPosition` that way.

## Flags and vars

| What | Use |
|---|---|
| `FLAG_SOL_TOWN_A` (0x0A40) | the seizure (3.4a part 7) has played |
| `FLAG_SOL_TOWN_B` (0x0A41) | postgame Indra at the wall done |
| `FLAG_SOL_TOWN_C`..`H`, `FLAG_SOL_SANCTUARY_A`..`D` | unused (band visibility uses map-local flags) |
| `VAR_SOLACEON_PROGRESS` | read; the briefing sets 20 |
| town map-local flags | `FLAG_MAP_LOCAL_HIDE_OBSTACLE_1..30` and `FLAG_MAP_LOCAL_0x10`: one per band object (the table is at the top of the town `scripts.s`; 16 = Indra and 17 = the Rowan banners as before) |
| town map-local vars | `VAR_MAP_LOCAL_0x04` band, `0x02` seizure trigger (frame table), `0x03` fence trigger (coord event) |
| hall map-local flags | `FLAG_MAP_LOCAL_HIDE_OBSTACLE_1..11` (table at the top of the hall `scripts.s`) |
| trainers | `TRAINER_ECLIPSE_GRUNT_SOL_07/08` (data by raid-scripts), defeated flags 1360 + 833/834 |

No flags outside the town-scripts ranges.

## Wild encounters

`res/field/maps/solaceon_town/encounters.json` (mapgen gives the header `encounters_solaceon_town` when the file
exists): the garden of names, land rate 25, Yamask and Duskull at 25-28 (Route 209 is 26-29 on this tree, the Veilstone
Gym 31), half and half; day/swarm/radar slots Yamask, night Duskull. Minccino and Gothita (route_pokemon.md "phase 2")
are not in the game's species list yet. The Pokedex area map uses Route 209's field index (11).

## Sprite budget

The field has 32 sprite slots, of which `preloaded count + 3` are reserved for the header's preloaded list
(`ov5_021ECE40.c`; a map that needs more asserts in `ov5_021ED858`). Solaceon's stock list (4) preloads twelve
sprites the town mostly doesn't use and left 17 slots: band A needs about 25 distinct sprites (+ the berry plants +
Indra in the 2.16a cutaway), so the header now uses list 15 (empty, like most maps: 29 slots), band A has no crates,
and kennel Pokemon 3-4 reuse the ranch's Buneary and Pachirisu. Adding sprites to band A needs a recount.

## Text

`python3 tools/solaceon_town/screenplay_text.py --write` regenerates the entries from screenplay.md (dry run without
`--write`): one bank entry per screenplay message, boxes split at `--`, appended after the stock/Arc 2 entries and
replaced in place on a re-run. It checks ASCII, at most 2 lines a box, every line at most 197 px in
`res/fonts/font_message.json` (`{PLAYER}` counted as 7 wide letters), and that every id the two scripts use exists.
The lantern man's and the Sunday man's first messages are the stock ones.

## The test

```
tools/macos/build.sh dev
python3 tools/dazzling/check_script_targets.py && python3 tools/dazzling/test/static_checks.py
python3 tools/solaceon_town/town_test.py build_macos "/tmp/Solaceon Update/scripts_mac" [--only A,briefing]
```

It builds a level-100 test copy of the repo's Arc 2 save (`save_tool.py edit --level 100 --max-ivs --max-pp`; a
level-5 copy for the loss), and per scenario boots it, sets the state, warps in and asserts with the headless
`objects` command which objects exist (and where) for the band; talks to every object (`talk`, after a warp next to
it so the headless teleport stays inside the loaded chunks; the tent clerk across the table), reads every sign, drives each to the idle field and screenshots every text box into
`<out>/<scenario>/`. Scenarios: `cutaway` (44 -> 47 -> 49), `A` (+ the hall, the office, a wild battle in the
garden), `B` (+ the blocked office), `C`, `D` (+ the blocked gate, the locked door, the empty hall and the gate grunt
letting a player out), `briefing` (10 -> 20, the fence walk-in with both battles, the reload, Room 1, R townspeople,
Looker in the office), `fence_talk`, `fence_loss` (the reset and the whiteout), `E` (the seizure and the Dusk Stone,
once), `seizure_shots`, `F` (+ Indra at the wall).

`tools/solaceon_ruins/raid_test.py` still passes on this branch: its run ends on the new landing tile (580,660) and
its driver plays the seizure through; its `post_raid` scenario (which warps into town at 50) now sets
`FLAG_SOL_TOWN_A` first, so the seizure doesn't play there.

Result (2026-11-25, `sol-mac/town-scripts` with the town art merged): every scenario PASS, 550 checks, 676
screenshots in `/tmp/Solaceon Update/scripts_mac/<scenario>/`.

## Open issues

- The tent clerk (566,643) stands behind the tent table; the final tent art (the REGISTRY front) hides her sprite from the
  field camera (she is talked to fine across the table). Town-art or the lead: lower the tent front, or move her.
- `talk` in the headless protocol teleports the player; a long jump across chunks leaves the map loader on the old
  chunks (black terrain in screenshots; the test warps next to each object first). Scripts must not do that either
  (see "No SetPosition").
- In band D the hall door is unreachable (the gate grunt), so its locked message is only seen by a player who left
  the hall in D (a save inside); the gate grunt then lets them out.
- The Pokemon History app giver now uses the `EXPERT_M` sprite (the Day Care Man's); layout.md's `EXPERT_M_3` note was
  the Day Care Man, who stays.
