# Arc 1 playtest fixes: parallel plan

Base: `arc1-part2` @ 90df400a3d. Five workstreams run in parallel, each in its own worktree and branch, so
builds never share `build/`. The lead merges, does a full playthrough, commits and pushes.

## Setup (lead, before launch)

```
cd /data/repos/dazzlingPlatinum
for s in opening verity battle route202 jubilife; do
  git worktree add -b a1fix/$s /data/repos/dp-wt/fix-$s arc1-part2
done
```
Copy or symlink the untracked `subprojects/*` toolchain dirs into each worktree, the same way the
`a1p2/*` worktrees were set up.

## Workstreams

### A. Opening: bugs 1, 2
Owns: `src/applications/title_screen.c`, `res/graphics/title_screen/giratina_prerender.bin`,
`tools/giratina_title/**`, `scripts_distortion_world_giratina_room.s`, `scripts_init_new_game.s`,
`src/location.c`, and their text.

1. **Title Giratina 1.3x faster.** The loop is 848 frames (14.2 s) now; the target is about 652 frames
   (10.9 s). Use the same repack path as the 1.7x pass (`pack_frames.py --schedule`, checked with
   `simulate.py`). Scale `LOGO_FLASH_FIRST_STEP` to match. Don't use the code-only VBlank accumulator,
   because decoding can't keep up.
2. **Black caption card before the flashback.** Before `DistortionWorldGiratinaRoom_Arc1Flashback` fades
   in: a black screen with centered text, "The last moments from Pokémon Platinum...", held for about 2 s,
   then fade into the scene. Cheapest route: keep the screen black and show a message on it (the
   flashback already has a caption mechanism, `ScrCmd_322`; reuse it).

### B. Lake Verity + Distortion World: bugs 3, 4, 6
Owns: `scripts_lake_verity.s`, `scripts_init_lake_verity.s`, `events_lake_verity.json`,
`res/text/lake_verity.json`, `scripts_distortion_world_arc1_seams*.s`, `res/text/distortion_world_arc1_seams.json`.

3. **Lake Verity arrival: replace the pan and teleport (owner's design).** Today
   (`scripts_lake_verity.s:486-538`) the camera pans in three separate legs that stop between each, Barry
   and the player teleport to the stairs with `SetPosition`, and the terrace cast pops in with `AddObject`.
   New flow:
   (a) On arrival, Barry and the player **hear something from the castle top**: a sound effect, a short
       `ShakeCamera` or a flash at the portal, and an exclamation emote on both. No camera pan, or at most one
       short continuous tilt toward the castle and back, with no stops in the middle.
   (b) Barry: "Hey, did you hear that? Something's going on up at the castle! We have to go see!" plus a
       warning: "Stay out of the tall grass, though. We don't have any Pokemon yet!"
   (c) **The player walks up to the castle themselves, with Barry following** (use the stock follower or a
       scripted tail; check how Route 201 or HGSS-style followers are done in this repo). Nobody teleports.
   (d) **Grass guard:** trigger tiles (coord events) on every edge of the path that leads into tall grass.
       Stepping onto one makes Barry run up and say "Whoa! No Pokemon, no grass!", then the player is walked
       back one tile. This is the same pattern as stock Route 201's "Barry blocks the grass".
   (e) When the player reaches the foot of the stairs (a coord trigger), the existing stair or terrace scene
       continues. Cyrus, Rowan and Dawn must already exist and be drawn by then: place them while they're off
       screen, during the walk, never `AddObject` in front of the camera.
   If the walk is unreasonably long, report its length and keep it anyway. Don't add a fade-teleport without
   asking. Verify with a frame strip of the walk, one grass-guard trigger, and the hand-off into the terrace
   scene.
4. **DW Cyrus line.** `CyrusTheVoidSendsItBack` ("Falling costs us nothing but time") contradicts the
   rift jump. Reword to: "I will experiment. Let us see if we can jump straight there. Why don't you try
   to find another path?" Fit it to the 27-tile box. Check that it reads right before Barry's "walk
   through thin air?!"
6. **"Woof" to "Phew".** `LakeVerity_Text_Arc1BarryPerfectTiming` (`lake_verity.json:524`).

### C. Battle stage: bugs 5, 7 (hardest; give it the most effort)
Owns: `src/battle/battle_stage*.c`, `src/pokemon_sprite.c`, `src/battle/` and `src/overlay012/` anim
helpers, `docs/living_battle_stage/**`.

5. **Fake Tears stat drop lands on a "clone".** The stock stat-change effect draws a copy of the target
   sprite (a tinted overlay that scrolls), placed at the static 2D position. The living stage now moves
   or deforms the real mesh, so the copy doesn't line up with it. Find where the stat up/down anim makes
   that copy, and either bind it to the live mesh transform each frame or hide the mesh and drive the copy
   instead. Test Fake Tears, Growl, Leer, Swords Dance and Defense Curl, on both sides.
7. **The opponent trainer's sprite is missing at the start of the battle, during the send-out.** Reported on
   Barry (first rival battle, Piplup). Treat it as possibly affecting every trainer battle on the living
   stage until a stock trainer (Route 202 or 203 Youngster) proves otherwise. The intro should show the
   trainer sliding in, then the throw animation as the Poke Ball goes out, then the trainer sliding off.
   Find where the stage hides or draws over the OBJ trainer pic (the 3D layer or the BG priority, the
   camera intro, or the stage sprite stream), and fix it for every trainer.

### D. Route 202 + Pokédex: bugs 8, 9
Owns: `scripts_route_202.s`, `res/text/route_202.json`, `src/applications/pokedex/**`, and the Pokédex
graphics.

8. **No catching tutorial.** In `_0174` (`scripts_route_202.s:~109`), drop `StartCatchingTutorial` and its
   walk-in movement. Ruth just hands over 5 Poké Balls, which the script already gives. Rewrite
   `Arc1RuthWeakenItFirst` so it doesn't teach (for example: "You've done this before, right? Take these.").
   Keep the Town Map gift and her exit.
9. **Shinx Pokédex entry shows the wrong type icon** (beside "Flash Pokémon"; reported as Dragon).
   `res/pokemon/shinx/data.json` is correct (Electric). Suspect the type icons got out of sync after Fairy
   was added (`TYPE_FAIRY` is index 18; `src/type_icon.c` was patched, the Pokédex has its own
   `type_icons` cell/anim set in `ov21_021E0C68.c` / `ov21_021DE668.c`). Check several species of
   different types, not just Shinx.

### E. Jubilife + bag: bugs 10–13
Owns: `scripts_jubilife_city.s`, `events_jubilife_city.json`, `res/text/jubilife_city.json`, `src/item.c`,
`res/graphics/item_icons/**`.

10. **Rally Cyrus says something.** `JubilifeCity_Arc1Cyrus` only shows `Arc1CyrusEllipsis`. Write 1–2 lines
    in his voice that fit the screenplay (`docs/story/arc1_part2_screenplay.md`): wary, sizing up
    Saros's pitch to bring back the dead.
11. **Saros "below the TV."** `LOCALID_ARC1_SAROS` is an overworld object at (164,751) that flickers in and
    out under the screen (`scripts_jubilife_city.s:1870-1901`). Remove that object from the speech: the
    TV switches on and his lines play as "Saros (on screen)", with only the two side grunts visible.
12. ~~Clown/Pokétch coupon freeze~~: already fixed in 90df400a3d (owner confirmed). Out of scope.
13. **Close Bag icon.** Root cause: `src/item.c:3063-3077` hardcodes icon NARC members 707/708 (none)
    and 709/710 (return/close). `mega_stone` and `eclipse_shard` were inserted before `none` in
    `item_icon.order`, which moved those to 711–714. Use the generated NAIX constants
    (`none_NCGR`, …) instead of the numbers, so the next icon added can't break it again.

## Rules for every workstream
- Edit only files you own. If you need something from another stream (a flag, a shared macro), put it in
  your report and don't edit it. `generated/vars_flags.txt` belongs to the lead.
- Build in your own worktree with `make release` (never plain `make`). ASCII quotes and apostrophes only.
  Keep message lines to the stock box width.
- Verify headlessly with `~/.venvs/desmume/bin/python`. Save screenshots or frame strips under
  `/tmp/a1fix/<stream>/`.
- Commit to your `a1fix/<stream>` branch. Don't push and don't merge.
- Report: what changed (files), how it was verified (evidence paths), and anything left open.

## Lead integration
Merge `a1fix/*` into `arc1-part2` and run `make release`. Then do a headless run through all 13 fixes in
story order: title, caption, flashback, Lake Verity, DW, Mawile battle, Route 201 Barry, Route 202, Shinx
catch and Pokédex, Jubilife rally, clown, bag. Push `arc1-part2` and hand over `out/dazzlingPlatinum.nds`.
