# Arc 1 revision: scene-by-scene change plan

I made no edits. Branch `arc1-story-revision` is clean. All paths are relative to the repo root.

**Headline:** the starter picker, the Mawile battle and the Distortion World (DW) warp cutscene all work from any map, so the story side needs **no new engine work**. The real costs are a rewrite of the Lake Verity scene, the DW map itself (another agent's job), and keeping the story-state ladder airtight.

## Proposed `VAR_ARC1_PROGRESS` values

| val | state | change |
|---|---|---|
| 0–3 | flashback / roof landing / TV / heading to the lake | unchanged |
| **4** | castle-top briefing done, portal open, player must step in | **new meaning** (was "done") |
| **5** | inside the DW, puzzle running | new |
| **6** | starter picked and Mawile fought, about to leave the DW | new |
| **7** | back on the terrace, return scene pending | new |
| **8** | Arc 1 done; Route 201 shows "to be continued" | was 4 |

Places that have to move from 4 to 8:
- `scripts_route_201.s:28` (`CallIfGe …, 4`)
- `events_route_201.json` coord event for script 19 (`value 4`)
- `docs/lake_verity_redesign/gameplay.md:176`

Two risks:
- **Playtest saves sitting at the old value 4 will break.** Those players need a new game.
- **Route 201's coord events check for exact values** (18 = 3, 19 = 4). At states 4–7 the player could walk out and reach Sandgem without a starter. Fix: at state 4, Barry blocks the terrace stairs ("The briefcase is in there!"). States 5–6 are inside the DW and 7 is a scene on arrival, so state 4 is the only gap.

## Warps

- **Into the DW:** add an Arc 1 branch at the top of `LakeVerity_Launchpad` (`scripts_lake_verity.s:326`). The launchpad is the 18 portal-edge background events (script 8) in `events_lake_verity.json`, so the player chooses to step in, which is the player-driven moment the feedback asked for. When the state is 4:
  - Yes/No prompt; Cyrus and Barry walk in and disappear.
  - `ScrCmd_320` plays the stock DW warp cutscene (`src/unk_0203D1B8.c:1805-1815`, overlay `dw_warp`; stock already uses it at lines 337-350).
  - `SetVar 5`, then `Warp <DW map>, entry platform`.
- **Back out:** after the battle: `ScrCmd_320`, `SetVar 7`, then `Warp MAP_HEADER_LAKE_VERITY, 0, 32, 31, DIR_NORTH`. That is the tile the flashback already lands on.
- **DW map choice belongs to the puzzle agent.** The DW system is hard-wired to the stock DW map headers:
  - `sDistWorldMapConnectionList` at `ov9_02249960.c:10042`
  - range checks at `encounter.c:863` and `item_use_functions.c:832`
  - so reusing or editing a stock DW map is much cheaper than adding a new header. Stock wall-walking already exists (`AVATAR_DISTORTION_STATE_*`, `include/constants/player_avatar.h:30-36`).
  - If DW 1F is used, its "go back?" event (`scripts_distortion_world_1f.s` `_001A`, which warps to Spear Pillar) needs an Arc 1 guard.
- **Persisted DW state:** an Arc 1 visit writes into the save data the post-game DW reuses (ghost-prop groups, camera angles). The flashback already overrides this for the Giratina room (`ov9_02249960.c:3029`). The puzzle map needs the same care.

## Scene by scene

**1. Rowan intro** (`src/applications/rowan_intro/rowan_intro_app.c:1360-1366`, `res/text/rowan_intro.json` `RowanIntro_Text_HelloThere`)
- Now: one line ("…a parallel dimension, a Sinnoh like no other.").
- Change: the doc's three-part speech plus a "the map differs from the Sinnoh you know" line, because playtesters were confused by the castle. Either add new messages and chain them in `RI_STATE_DIALOGUE_WELCOME`, or split `HelloThere` into several pages. Rival naming stays skipped.

**2. Flashback** (`scripts_distortion_world_giratina_room.s:177-231`, text 15/8/9/10/17/18; caption in `src/field_map_change.c:457-593`)
- Mostly keep.
- The doc says "Cyrus, Cynthia, and **Lucas**", and the feedback says the protagonist is a new character. Today the player's own avatar plays the hero. Proposal: hide the player and use them only as a camera anchor (as the roof landing does), and add a Lucas NPC (`OBJ_EVENT_GFX_PLAYER_M`). Owner decides.
- The doc also says the "Giratina Custom Opening Intro is too slow, needs ~1.7x" (storydoc line 275). It's unclear whether that means this flashback or the title screen.

**3. Roof landing** (`LakeVerity_Arc1OnFrameRoofLanding`, lines 382-419)
- Edit `LakeVerity_Text_Arc1CyrusWhereAmI` to add "Is this a dream?".
- The doc says he "staggers… wanders the rooftop". Extend `LakeVerity_Movement_Arc1CyrusLookAround` (677) into a short walk.
- Optional first reaction to a map difference: "A castle… at Verity?"

**4. Bedroom TV** (`scripts_twinleaf_town_player_house_2f.s:28-43`)
- Reword `ThatConcludesOurSpecialProgram` so it no longer says "Broadcast live from Lake Verity".
- Add a `BREAKING NEWS` message after `SeeYouNextWeek`: a portal above the castle, Rowan and Dawn on site. Text with a sound effect works; a drawn banner graphic would be engine/UI work. Owner's call.

**5. Barry** (same file, lines 97-158)
- Replace `ThatTeamEclipseReallyIsSomething` with the doc line (news, portal, "go help, Rowan would owe us starters").
- Retune `WereGoingToSeeProfRowanAndGetPokemon` to match.
- Flow and state 3 stay as they are.

**6. Mom** (`scripts_twinleaf_town_player_house_1f.s`, `OnFrame_RivalAlreadyLeft`): already gives the Running Shoes at once. **Keep.**

**7. Twinleaf exit / Route 201** (`scripts_route_201.s:1285-1376`): the grass block already works the D/P way. **Keep**, plus an optional reword of `Route201_Text_Arc1ImGoingToLakeVerity` ("help Rowan out").

**8. Lake Verity castle top** (`LakeVerity_Arc1OnFrameArrival`, 430-660)
- **Keep:** Barry's intro (434-441) and the camera pan (443-452).
- **Delete:**
  - the Mawile emergence, portal closing, chase, briefcase drop and Rowan fleeing (466-575)
  - the Barry starter/charge/flee/"ran off" block (586-618; the pick moves into the DW)
  - the Cyrus thank-you and briefcase pickup (619-642)
  - the movements built around the chase (`ChaseLapK*`, `*Scatter`, `RunToLanding`, `*Downstairs`, `*LapFromLanding`, `*Corner`, `*Charge*`, `*Flee`)
  - texts `CounterpartDidYouFallOut`, `CyrusI`, `RowanAPokemonCameOut`, `CounterpartAnotherOne`, `RowanGetBack`, `RowanMyBriefcase`, `RowanOutOfTheWay`, `BarryThatGuysBeingChased`, `BarryMawileRanOff`, `CyrusICalledThatAFlaw`, `CyrusThankYou`, `CyrusTheProfessorRan`
  - Lake Verity objects `LOCALID_MAWILE_1` and `_2` (last in the list, so removing them shifts no other ids)
- **New flow:**
  - Rowan, Dawn and Cyrus are already on the terrace; move Cyrus "apart", e.g. (28,24).
  - Hand control to the player for the stair climb instead of the scripted `SetPosition`/`ClimbStairs`.
  - A new coord event at the top of the stairs (≈x23-24, z29) when the state is 3 runs the briefing: Dawn's readings, Rowan's briefcase story, Barry "we go in", Rowan's warning, Cyrus volunteers (plus a "this lake had no castle" reaction).
  - Then `SetVar 4`.
  - **Do not** call `SetLakeVerityPortalHidden 1` here; the portal must stay open.
- **Supporting changes:**
  - `LakeVerity_OnTransition` (38) re-shows the cast on reload at states 4 and 7.
  - Add `InitScriptGoToIfEqual VAR_ARC1_PROGRESS, 7, <return script>` to `scripts_init_lake_verity.s`.

**9. Entering the rift:** see Warps above.

**10. Inside the DW (hook points only)**
- A frame script when the state is 5 runs Cyrus's "Careful. This world is confusing…" line.
- Hint triggers at the first wall and the fork.
- A fall/reset hook that plays the retry line.
- The optional item alcove: a standard ground item (`_1EAE`-style; needs a new hidden flag).
- The briefcase trigger, preferably the player pressing A on an `OBJ_EVENT_GFX_BRIEFCASE` object.
- **Followers:** the stock partner system (`SetHasPartner` + `SetMovementType 0, 48` = `MOVEMENT_TYPE_FOLLOW_PLAYER`, `scripts_eterna_forest.s:60-63`) supports only **one** follower. It also turns wild battles into tag battles, and wall-walking states apply to the player only. **Recommendation:** no live followers. Cyrus and Barry are placed by script at each beat, the way stock DW places Cynthia.

**11. Starter pick + Mawile** (in the DW)
- Reuse the Lake Verity sequence from lines 577-602:
  - `StartChooseStarterScene`, `SaveChosenStarter`, `ReturnToField`, `GetPlayerStarterSpecies`, `GivePokemon 5`
  - `BufferRivalStarterSpeciesName` for Barry's line
  - one Mawile lunges (`Mawile2ChargePlayer` movement, line 957)
  - `StartArc1MawileBattle`, `HealParty`, then `SetVar 6`
- **Why this works off-map:**
  - The picker is a standalone app (`scrcmd.c:4251-4277`, `unk_0203D1B8.c:1289`) and already runs fine away from Route 201.
  - `Encounter_NewArc1MawileBattle` (`encounter.c:756-784`) has no map check, and the battle backdrop comes from the DW map header.
  - `BATTLE_STATUS_DISTORTION` is not set, but it only matters for Giratina's form (`battle_lib.c:6536`).
- **Things to test:**
  - `ReturnToField` rebuilding the DW system; do the pick while the player is on a floor.
  - The picker's own backdrop may not fit the DW visually.
- Rename the "Lake Verity" wording in the comments at `scrcmd.inc:4207` and `encounter.c:703` (comments only).

**12. Return to the castle** (new frame script, state 7)
- Rowan, Dawn, Barry and Cyrus are added by `AddObject` on the terrace. There is no draw-on-load issue (see the comment at line 453), because the field loads around the terrace.
- The player hands the briefcase back; Rowan says "A deal is a deal — the starters are yours."
- Close the portal here with the white flash from lines 493-498 and `SetLakeVerityPortalHidden 1`.

**13. Cyrus parting**
- A new text replaces `CyrusYouRemindMeOfSomeone`.
- Give the item with `SetVar VAR_0x8004, ITEM_X` / `SetVar VAR_0x8005, 1` / `GiveItemQuantity` (pattern from `scripts_sandgem_town.s:451-453`).
- Cyrus leaves with the existing `Arc1CyrusLeave` movement (1037).

**14. Barry closing**
- Rewrite `Arc1BarryPerfectTiming`: "Woof!…", "is wearing", "heading home to heal".
- Keep the exit and the state setters from 651-658, with `SetVar 8` in place of 4.

**15. Route 201 "to be continued"**: only the value moves from 4 to 8, as above.

## Questions for the owner

1. **Cyrus's gift:** which item? Candidates: Revive or Dusk Stone (named in the puzzle doc), a Poké Ball set, or a key item that sets up a later plot point.
2. **Barry:** does he also pick a starter in the DW (the current code does, the doc implies it), with no Mawile battle of his own, since the doc has only one Mawile?
3. **Dawn:** does she come into the DW? (The doc says no.) Is the assistant always "Dawn", or still opposite gender to the player (today: `BufferCounterpartName`)? And "Dawn and Lucas will be replaced with new MCs".
4. **Flashback hero:** Lucas NPC, or the player's avatar?
5. **BREAKING NEWS:** text-only, or a drawn banner?
6. **After the return:** do Rowan and Dawn leave, or stay on the terrace as NPCs?
7. **Healing:** heal after the Mawile battle (current) or not ("heading home to heal")?
8. **The 1.7x speed note:** the flashback, or the title screen intro?