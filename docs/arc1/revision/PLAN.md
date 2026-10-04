# Arc 1 revision plan (part 1 v2)

Branch `arc1-story-revision` (off `main` @ e017ef2da). Planning only: nothing in `src/` or `res/` has changed.

Source: the "Dazzling Platinum Planning" Google Doc (new Arc 1 script, playtest feedback, and the
"Distortion World Puzzle 1 - Wall Walk" tab). This replaces `docs/arc1/screenplay.md` once the owner approves it.

Detailed agent reports, with file paths and line numbers:

- `scenes_audit.md`: every scene, now vs. new, plus the story-state ladder and warps
- `puzzle_wall_walk.md`: how stock Distortion World wall walking works, and how to build the puzzle on it
- `intro_tv_title_backlog.md`: Rowan intro, TV breaking news, the 1.7x intro speed, Barry lines, backlog

## TL;DR

- **The story side needs no new engine work.** Three things already run from any map: the starter picker
  (`StartChooseStarterScene`), `StartArc1MawileBattle`, and the stock DW warp cutscene (`ScrCmd_320`). So
  starter select and the Mawile battle can move into the Distortion World.
- **The real puzzle is cheaper than the doc's fake.** Stock Platinum already walks on walls through data
  (`tw_arc.narc` surfaces, jump points and camera angles in `src/overlay009/ov9_02249960.c`). A new standalone DW
  map at offset (0,0,0), like the Giratina room, gets real wall walking, the player rotation, the hop sound and
  the camera tilt for free. So the doc's "fake it with a 90-degree camera" note goes away.
- **Biggest change:** the Lake Verity castle-top scene. The Mawile chase is cut, and the scene becomes a
  briefing that ends with the player choosing to step into the portal.
- **Estimate:** about 7-11 dev days for a custom-terrain puzzle, or about 3 days for a cloned-B1F fallback.
  The story and script changes are about 3-4 days on top of that.

## New story-state ladder (`VAR_ARC1_PROGRESS`)

| val | state | notes |
|---|---|---|
| 0-3 | flashback / roof landing / TV / heading to the lake | unchanged |
| 4 | castle briefing done, portal open, player must step in | **was "Arc 1 done"** |
| 5 | inside the DW, puzzle running | new |
| 6 | starter picked and Mawile fought, about to leave the DW | new |
| 7 | back on the terrace, return scene pending | new |
| 8 | Arc 1 done; Route 201 shows "to be continued" | moved from 4 |

- Places to change 4 to 8: `scripts_route_201.s:28`, the `events_route_201.json` coord event for script 19,
  and `docs/lake_verity_redesign/gameplay.md:176`.
- **Old playtest saves at value 4 need a new game.**
- **Gap:** at state 4 the player could walk back to Route 201 with no starter. Barry should block the terrace
  stairs at state 4 ("The briefcase is in there!").

## Scene changes

| # | Scene | Change | Owner (spec.md workstream) |
|---|---|---|---|
| 1 | Rowan intro | Text only: grow `RowanIntro_Text_HelloThere` from 2 to about 6-7 pages. Adds the parallel-Sinnoh speech, a "the map differs" line and "after Team Galactic fell". No C change. | Intro & home |
| 2 | Flashback | Keep. Change the swoop into a **throw**: add a shake and a white flash, then Cyrus knocked back before `ScrCmd_312 130`, with msg 18 reworded to "It threw him... through a rift." Optionally an extra fly-by entry so Giratina "rises". Open question: should the hero be a Lucas NPC instead of the player's avatar? | Opening |
| 3 | Roof landing | Add "Is this a dream?" and one map-difference line ("A castle... on Lake Verity? There was never a castle here."). Make Cyrus wander a few steps. | Lake Verity |
| 4 | Bedroom TV | After the interview: TV-noise sound effect, then a BREAKING NEWS message (portal above the castle, Rowan and the assistant on site; `BufferCounterpartName`). Drop or reorder the "broadcast live from Lake Verity" outro, which contradicts it. | Intro & home |
| 5 | Barry | New bedroom line (news, portal, go help, Rowan owes us starters). Retune `WereGoingToSeeProfRowan...` and `Route201_Text_Arc1ImGoingToLakeVerity`. | Intro & home |
| 6 | Mom | Already gives the Running Shoes. Keep. | - |
| 7 | Twinleaf exit / Route 201 gating | Keep. Fix one stock curly apostrophe in `ISaidTheLakesNotThatWay`. | Intro & home |
| 8 | Castle top | **Delete** the Mawile emergence, portal close, chase, briefcase drop, Rowan fleeing, the terrace starter pick, and the Cyrus thank-you, plus their movements, texts and `LOCALID_MAWILE_1/2`. **New:** the player climbs the stairs themselves; a coord event at the top runs the briefing (Dawn's readings, Rowan's briefcase story, Barry, Rowan's warning, Cyrus volunteers); then `SetVar 4`. The portal stays open. | Lake Verity |
| 9 | Enter the rift | Arc 1 branch at the top of `LakeVerity_Launchpad`: Yes/No, Cyrus and Barry step in, `ScrCmd_320` warp cutscene, `SetVar 5`, `Warp` to the DW entry platform. | Lake Verity |
| 10 | DW puzzle | New map, see below. Cyrus and Barry are **not** live followers: the stock follower system supports one partner, turns battles into tag battles, and doesn't handle gravity. Script-place them at each beat with the DW ghost fade (`ScrCmd_311/312`). | new: Distortion World |
| 11 | Starter + Mawile | Move the existing block (`scripts_lake_verity.s:576-603`) to the briefcase trigger on the DW platform. One Mawile lunges, then `StartArc1MawileBattle`, `HealParty`, `SetVar 6`. | Distortion World |
| 12 | Return | `ScrCmd_320`, `SetVar 7`, warp to Lake Verity (32,31). New state-7 frame script: hand the briefcase back, Rowan's "A deal is a deal", then **now** close the portal (flash + `SetLakeVerityPortalHidden 1`). | Lake Verity |
| 13 | Cyrus parting | New line, then `GiveItemQuantity` (item still to be decided), then the existing `Arc1CyrusLeave`. | Lake Verity |
| 14 | Barry closing | Rewrite `Arc1BarryPerfectTiming`, then `SetVar 8`. | Lake Verity |
| 15 | Route 201 TBC | Only the threshold moves (4 to 8). | Intro & home |

## Distortion World Puzzle 1: build plan

The approach is a new standalone map, `MAP_HEADER_DISTORTION_WORLD_ARC1_SEAMS`, on the stock wall-walk engine.

- **Phase 0: clone B1F (map data 602/603 plus its `tw_arc` record) as the new map.**
  - B1F's floor-to-wall-to-floor along a chasm is already beat 1.
  - This proves the header, `DISTORTION_WORLD_MAP_COUNT` 10 to 11, the archive entry, the warp in, the starter
    scene, the battle and the return.
  - About 3 days, with zero art. **It's also the fallback ship**: edit only the wall's attribute grid to get the
    fork.
- **Phase 1: custom one-chunk terrain** with the Lake Verity pipeline (`tools/lake_verity/`), a new
  `tools/distortion_world/twarc.py` (JSON to and from `tw_arc`/`tw_arc_attr`), and our own surfaces, jumps and
  cameras. About 4-8 more days.
- **Seams:**
  - **Walkable:** the walkable tiles in the 32x32 wall attribute grid. Non-seam tiles are blocked (`0x8000`), so
    you can't step off a wall, the same as stock.
  - **Visible:** an emissive seam material animated through `fldtanime`, the same way as the Coronet lava.
- **Falls:** only at the chasm lips. Coord events run a fall script: hide, fade, reset the DW camera, warp
  back to the entry on the same map, then Cyrus's retry line once.
- **Engine constraints the design has to respect:**
  - Only **west/east walls and ceilings** exist; there are no north/south walls.
  - Each gravity change is a 16-frame **hop**, not a smooth walk.
  - Map props don't load in the DW.
  - The descent over the crest has no exact stock precedent, so tune it in the emulator.

Layout (one chunk): `E` entry, then a jump onto `W1`; the seam climbs `W1` and forks to alcove `A` (dead end,
item) or on up to crest `T`; `T` leads down `W2` to briefcase platform `B`. ASCII sketch in
`puzzle_wall_walk.md` section 3.

## Suggested improvements

### Puzzle

1. **Swap the Revive for something usable.** The player picks the alcove up before owning a Pokemon, the
   Mawile battle sets `BATTLE_STATUS_FIRST_BATTLE` (no bag), and a single-Pokemon party can't use a Revive
   anyway. Better: 5 Poke Balls (you're about to need them), an Oran Berry, or a lore item (see story #4).
2. **Let Barry demonstrate the fail state.** Barry charges straight at the chasm ("I'll just jump it!"),
   "falls", and fades back in at the entry, embarrassed. The player learns that falling is safe without being
   punished for it, and Barry gets his D/P impatience moment.
3. **Show, then hint.** The feedback says the story should "unfold rather than be explained". Cyrus's "walk the
   seam" line should only fire after a fall or about 20 idle steps; the first time, the seam's glow and a camera
   tilt toward it do the teaching. His entry line stays.
4. **Foreshadow the Mawile.** Glimpse it on the crest (a ghost-fade sprite that vanishes) when the player
   reaches the fork. That way its ambush at the briefcase pays off instead of coming out of nowhere.
5. **Don't make the player re-solve the puzzle to leave.** After the battle a new small rift opens beside the
   briefcase (reuse the portal flash): "The world is closing. This way." Faster, and it matches the doc's
   "Cyrus guides everyone back out".
6. **Plant a seam you can't reach yet.** A flickering seam off to the side that leads nowhere for now. It sets up
   later puzzles (flicker timers, per the doc's escalation notes) and follows the "see areas you'll come back
   to" tip in the doc.
7. **Sell "Giratina pulls things into the DW".** Scatter displaced Lake Verity debris on the floating rocks: a
   castle banner, a signpost, a park bench. It's cheap terrain dressing that tells the theme without dialogue.

### Arc 1 story

1. **Give the player the choice to go in.** Rowan forbids the kids from going. Cyrus volunteers; Barry runs in
   before anyone can stop him; the player decides to follow (the Yes/No on the launchpad). That's the
   "player-driven action" the playtest asked for, and it makes Rowan less of a pushover than "sure, go into the
   hell dimension for me".
2. **Have Cyrus notice the parallel world through people, not just the castle.** Rowan doesn't recognize Cyrus,
   and Cyrus clocks it: "...He doesn't know me. In this world, perhaps there is no reason he should." It's
   dramatic irony the player gets and the protagonist doesn't, which is exactly the doc's "player pieces
   together the timeline" goal.
3. **Give Dawn a job.** She stays at the portal running the readings and is the one who closes it on your
   return ("Readings are dropping, it's closing!"). That explains why the portal stays open the whole time and
   why it closes when it does.
4. **Tie Arc 1 to Team Eclipse beyond the TV.** Right now the villain is just a TV mention. Suggestions:
   - The alcove item could be a cracked violet **shard** (the doc's shards from torturing Pokemon), with Cyrus
     reacting darkly: "Someone has been... harvesting."
   - The Mawile is agitated because it's wearing one or near one.
   - Pay it off in Arc 2 when Rowan identifies it.
5. **Make Cyrus's gift matter.** Instead of a generic item, he could give something that pays off later: a key
   item that lets you sense seams in later DW puzzles, or the shard from #4 ("Take it to Rowan. He'll want to
   see this."). Either way it settles open question 1.
6. **Barry's starter.** Keep Barry picking (the stock "strong against yours" rule) so the Route 201 rival battle
   in Arc 2 still works. Optional upgrade: a **tag battle** with Barry against two Mawile, since the stock
   partner system turns wild battles into tag battles. It's more memorable and uses the original two-Mawile
   idea, but it needs a new encounter variant.
7. **Pacing.**
   - Trim Rowan's intro to about 5 pages: the parallel-world framing is what matters; "some people you may
     recognize" can go.
   - Speed up the flashback waits (about 254 frames now, scale by 1/1.7).
   - Combine the TV interview and breaking news into one continuous broadcast.
8. **Flashback hero.** Use a Lucas NPC rather than the player's avatar, and keep the player as a hidden camera
   anchor. Otherwise the player reads it as "I am the old hero", which contradicts "protag is a new character".

## Open questions for the owner

1. Cyrus's gift: which item? (see story #5)
2. Barry: picks a starter in the DW? Fights off screen, or a tag battle? (story #6)
3. Does the assistant come into the DW? Is the assistant always Dawn, or still the opposite gender to the
   player? (The doc says "Dawn"; the current code uses `BufferCounterpartName`.)
4. Flashback hero: Lucas NPC or player avatar?
5. BREAKING NEWS: text only (cheap) or a drawn banner graphic (UI work)?
6. After the return, do Rowan and Dawn leave or stay as terrace NPCs?
7. Heal after the Mawile battle (current), or leave it to Barry's "heading home to heal" line?
8. "Giratina custom opening intro too slow, 1.7x": the **title-screen pre-rendered loop** (most likely: repack
   to 212 steps, `LOGO_FLASH_FIRST_STEP` 219 to about 129) or the **new-game flashback** pacing? Details in
   `intro_tv_title_backlog.md` section 2.
9. Puzzle scope: custom terrain (Phase 1, about 7-11 days) or ship the cloned-B1F fallback first (about 3 days)?

## Suggested work order (for an implementation team)

1. **Lead:** update `spec.md` with the new var values and ownership (add a **Distortion World** workstream that
   owns `src/overlay009/**`, the new map files and the DW scripts), and `vars_flags.txt`.
2. **In parallel:**
   - Intro & home: text (scenes 1, 4, 5, 7, 15)
   - Opening: flashback throw and pacing (scene 2)
   - DW: Phase 0 clone map plus warp plumbing
3. **Lake Verity:** strip the chase, then add the briefing, the launchpad branch and the return scene (scenes 3,
   8, 9, 12-14), once the DW map header exists.
4. **DW:** puzzle beats, starter and Mawile at the briefcase, the fall script, the seam animation; then Phase 1
   terrain if approved.
5. **Headless smoke test of the full flow** (states 0 to 8) with py-desmume, then push for a hardware test.
