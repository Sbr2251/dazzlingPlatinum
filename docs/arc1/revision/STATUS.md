# Arc 1 revision: implementation status

Implemented on branch `arc1-story-revision` by four workstreams (see `spec.md`), then integrated and validated
by the lead.

## Validation

A full headless playthrough on the integrated build (py-desmume): new game, the Rowan intro, the flashback,
the roof landing, the bedroom TV with breaking news, Barry, Mom, Twinleaf, Route 201, Lake Verity arrival, the
stair climb and briefing (state 4), the launchpad Yes/No and the warp into the Distortion World (state 5),
the puzzle (Barry's demo fall, the player's fall and reset, the seam, the fork scene, the alcove Poke Balls, the
dead end, back down to the briefcase), the starter pick, the Mawile battle, the shard, the exit rift (states 6-7),
the return scene with the Eclipse Shard (state 8), then the walk back to Route 201 for "To be continued...".
There were no hangs or softlocks. The harness lives outside the repo (`/tmp/arc1/lead/flow.py`).

Each workstream also tested its own scenes; evidence is under `/tmp/arc1/{intro,lv,dw,items}/` on the
devserver.

## Known issues / follow-ups

- **DW puzzle is Phase 0** (a cloned B1F). The seam isn't visually distinct from the rest of the wall: the
  stock wall face looks the same everywhere, so Cyrus's hint carries the teaching. The climb is short (3
  walkable rows), so there's no real "over the crest" beat. The exit rift is a flash plus the stock warp swirl.
  The debris dressing and the unreachable flickering seam were skipped. All of these need Phase 1 custom
  terrain.
- The DW map stores its numeric header ID (594) in `tw_arc`. If a map header is ever inserted before it,
  rerun `python3 tools/distortion_world/twarc.py build tools/distortion_world/arc1_seams.json`.
- After the battle reload, the Mawile reappears one tile from where it lunged. The ball pickup message says
  "Obtained" rather than "found".
- `VAR_VISITED_LAKE_VERITY_WITH_RIVAL` is now set at the end of the Lake Verity arrival (state 3), not at the
  end of Arc 1, so the Twinleaf NPC lines keyed on it switch slightly earlier.
- Cyrus now uses Barry's hide flag (`FLAG_HIDE_LAKE_VERITY_LOW_WATER_RIVAL`) at Lake Verity.
- Flashback: Lucas pops in about 10 frames after the caption fades. Cyrus's knock-back ends one tile over
  the void for a few frames before the flash.
- Title loop: repacked from frames decoded out of the old bin, so it's no sharper than before. The loop is now
  848 frames (14.2 s), down from 1,440 (24.1 s).
- `scripts_route_201.s:28` (hiding Barry from state 4) intentionally stays at 4.
- Old playtest saves at the old state 4 need a new game.
- The Eclipse Shard reuses an unused item slot (this repo's practice) rather than appending before
  `MAX_ITEMS` as CLAUDE.md describes.
