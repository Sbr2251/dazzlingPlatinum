# Cut-line guard (follow-up to chunk 4, camera.md)

## The problem

Many Gen 4 back sprites are only the top part of the Pokemon: the art runs into the bottom row of
the 80x80 frame (89 of 568 back PNGs, for example Garchomp, Lucario). At home the textbox
(y 144..191) hides that edge. Off home the camera can lift the player's battler, for example
`StageCameraMove STAGE_CAMERA_FOCUS_ATTACKER` in `mega_evolution.s`, which brings its foot
towards the middle of the screen. The flat bottom of the sprite then shows as a hard cut line.

## The rule

While the camera is off home, the cut edge of every cut sprite must stay at or below the limit:
- **144**, the textbox top, while the battle textbox window is shown;
- **192**, the screen bottom, while it is hidden.

At home nothing changes. The guard only runs on the off-home path, so the home frame stays
byte-identical, and `stage_ab` stays an exact match.

## Detection (per sprite, at char load)

A sprite is **cut** when frame 0 of its loaded art has any non-zero (opaque) pixel in its
bottom row, row 79.
- Compute this where the char data is buffered (`BufferPokemonSpriteCharData` in
  `src/pokemon_sprite.c`), or read it from `charRawData` right after.
- Store it as a per-sprite bit, recomputed on every char reload. A Mega Evolution swaps the art
  mid-animation, and Mega Garchomp may not be cut.
- Expose it through a small accessor.
- Only player-side battlers (`type & 1 == 0`) are guarded. Front sprites are not.
- A vertically flipped sprite (`flipV`) counts as not cut. That is rare, and happens only in
  anims.

## Where the edge lands

- **At home:** the cut edge is the bottom edge of the sprite quad, `cutHomeY`. It is the same
  y the classic draw gives the bottom of the 80-px frame, including the sprite's y offset.
  Take it from the same transforms `DrawHook` in `battle_stage_sprites.c` uses.
- **Off home:** the battler's similarity maps it to
  `edgeY = nowY + scale * (cutHomeY - homeY)`, with `anchors[i]`.

## The pan

- Let `need = max over the guarded battlers of (limit + 1 - edgeY)`, rounded up to whole px:
  the shortfall of the highest cut edge below the limit plus a 1 px margin (screen y grows
  downward, so an edge above the limit has `edgeY < limit`).
- If `need > 0`, pan the view so the whole picture moves **down** by `need` px. The margin sits
  inside `need`, so the pan starts from 0 and stays continuous.
- Do it with the same screen-space offset `BuildView` already applies for `ShakePixels`: an
  extra pixel dy added to the shake dy, converted at focus depth. The arena, blobs, sprites
  and particles then move together, since the anchors are projected from that view.
- After panning, rebuild the view and the anchors once more. The pan is exact only at focus
  depth, so recompute `edgeY` and top it up if it is still short. Two passes at most.
- The pan never goes the other way. The guard only pushes down, and never lifts anything.
- **Continuity:** the required pan is a continuous function of the eased pose, so apply it
  directly. When the limit itself jumps (the textbox showing or hiding while off home), ease
  the limit towards its new value over about 8 frames instead of popping. If the textbox state
  can't be read cheaply and reliably, use 144 whenever off home.
- The guard applies to every off-home pose, the debug views included.

## Mega re-aim (player branch)

`mega_evolution.s` `L_player` should frame the upper body, so the guard rarely has to push.
- Pull back (a larger distancePct), pitch up, or both. Alternatively use a focus that isn't
  the raw attacker foot.
- The Mega should still read as a close-up.
- The enemy branch is unchanged.

## Debug fields (sBattleStage +120..+139, right after compat)

`BattleStageCutGuardFields cutGuard` is inserted right after `compat`. Nothing the critic reads
moves.

| offset | field | meaning |
|---|---|---|
| +120 | `s16 cutEdgeY[4]` | per battler: the final on-screen y of its cut edge this frame; `0x7FFF` when not cut, not guarded (enemy side), invalid, or at home |
| +128 | `s16 cutLimit` | the limit used this frame (144 or 192, or between while easing) |
| +130 | `u16 guardPanPx` | the downward pan applied this frame, in px (0 at home) |
| +132 | `u32 guardFrames` | drawn frames with `guardPanPx > 0` |
| +136 | `u32 cutViolations` | drawn off-home frames where some `cutEdgeY < cutLimit - 1` after the guard; must stay 0 |

A cut sprite whose battler's edge would be off home by definition still gets its `cutEdgeY`
written while off home. That tells the critic detection worked.

## Critic checks

- **`mega`:** Garchomp's back sprite is cut.
  - While off home, at least one frame has `cutEdgeY[0] != 0x7FFF`.
  - `cutViolations == 0` at the end.
  - Every sampled off-home frame has `cutEdgeY[0] >= cutLimit - 1` (or `0x7FFF`).
  - Note `guardFrames`, and the largest `guardPanPx` seen.
- **`camera`, `move_tester`:** `cutViolations == 0` after every move.
- At home: `guardPanPx == 0`, and every `cutEdgeY` is `0x7FFF`.
- On a ROM without these fields (sBattleStage under 188 bytes; the fade fields that used to follow compat already made it 168), skip with a note, like the older
  field groups.
