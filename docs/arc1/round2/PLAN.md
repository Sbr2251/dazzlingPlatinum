# Arc 1 round 2: critic improvements, Roark, Gen 3/5 Pokemon

Base: `arc1-part2` @ 3ebc4f26ac. The owner approved every improvement in the critic's review (6.5/10, 2026-10-10)
and asked for Roark's team and for Gen 3/Gen 5 Pokemon in Arc 1 (`docs/story/route_pokemon.md`,
`docs/story/trainers.md`). Each workstream has its own worktree and branch, `/data/repos/dp-wt/<ws>` on `a1r2/<ws>`.

## Story decisions go through the orchestrator
The owner wants to talk through story decisions with the orchestrator (session
`d816fabe-d2df-4828-867e-21c297ab25a0`). Agents don't make story calls on their own.
- The critic's proposed lines (quoted below) are approved, and you may implement them as written. Small edits
  to fit the box width are fine.
- Anything beyond that needs the orchestrator first: new lines the critic didn't write, changing what a
  character knows or says, a different beat, or cutting something. Batch those questions with
  `message__send(to="d816fabe-d2df-4828-867e-21c297ab25a0", body=...)`. List the options and say which one you
  recommend. Then keep working on everything that isn't blocked, and end your turn with a one-line status if
  you're blocked. The reply starts your next turn.

## Workstreams

### S1 `story-verity`: Lake Verity, the castle, the Distortion World
Owns: `scripts_lake_verity.s`, `scripts_init_lake_verity.s`, `events_lake_verity.json`, `res/text/lake_verity.json`,
`scripts_distortion_world_arc1_seams*.s`, `res/text/distortion_world_arc1_seams.json`, `events_distortion_world_arc1_seams.json`,
and the DW fly-by table in `src/overlay009/ov9_02249960.c` (only add entries).
- **Critic #2 (castle half):** Rowan's "You came out of that portal, didn't you?" (msg 34) and Cyrus's "I came from
  that world" (msg 38) give away Rowan's Arc 2 turn. Keep Cyrus's claim, but Rowan must not accept it. Bring the
  exact wording to the orchestrator.
- **Critic #3:** Before he leaves, Rowan says "And you, sir. My lab is in Sandgem. I would very much like to
  talk." / Cyrus: "...Perhaps." Replace msgs 53-54 with the stronger parting: "You remind me of somebody I knew
  before. They had this fire within them. / I once called that fire a flaw. Something to be purged. / ...It is the
  reason I am still standing. / This was inside that Mawile. Show it to the professor. Not me. Not yet. / I need to
  understand what I am, here, before I stand in front of anyone."
- **Critic #4b:** Keep "It was wild with pain." Replace "Someone has been... harvesting." (`CyrusHarvesting`) with
  "...I know this hum. I have heard it before. From a lake."
- **Critic #5 (DW half):** During the seam climb, play the stock DW Giratina shadow fly-by once, and nobody
  reacts. Make sure "Something moved down there" (msg 7) no longer reads as the Mawile.
- **Critic #6 (Cyrus has no Pokemon):** When the Mawile lunges: "I have no Pokemon to stand with. ...It falls to you."
- **Critic #7:** Castle sign page 2: "Raised in an age before memory, for the lord of space." Add a terrace
  inscription Cyrus reads: "Palkia... Even here, they built it a throne."

### S2 `story-lab`: Sandgem lab, Oreburgh, Jubilife, Route 202, items, Twinleaf
Owns: `scripts_sandgem_town_pokemon_research_lab.s` + text, `scripts_oreburgh_mine_b2f.s` + text, `res/text/oreburgh_city.json`,
`scripts_jubilife_city.s` + `events_jubilife_city.json` + text, `scripts_route_202.s` + text, `res/text/item_names*.json`,
`res/text/item_descriptions.json`, Twinleaf scripts/events/text (one NPC line).
- **Critic #1:** Replace crowd msg 120 (`JubilifeCity_Text_Arc1CrowdEveryWeek`) with "My gran always said the dead
  go somewhere twisted, behind a door nobody can open. / Team Eclipse says they've found the door." Add the
  optional Rowan lab line: "Old Sinnoh stories call that place the world behind ours. Where the dead go.
  Superstition."
- **Critic #2 (lab and mine half):** after "Who is he?" (lab msg 70): Ruth: "He said he came *from* there,
  Professor. Like he'd been living in it." / Rowan: "Then he was confused. A few minutes in that place nearly
  swallowed these two. Nobody comes back from longer than that. ...Nobody." Mine msg 21 becomes "There's one man
  who walks that world like he's been there before."
- **Critic #4a:** In the lab, Garius adds "It fell out of that crazy Mawile!", so Rowan knows where the shard came
  from. **#4b:** cut one of the two "tear open on their own" lines (route_202 msg 21 or mine msg 16).
  **#4c:** rename the item "Eclipse Shard" to "Violet Shard" in all four item text files. Description: "It fell from
  a raging Mawile in the Distortion World." Leave the constant `ITEM_ECLIPSE_SHARD` and the icon alone.
- **Critic #5 (mine half):** replace the 1-frame black fade (`scripts_oreburgh_mine_b2f.s:~200`) with a dark
  silhouette crossing behind the violet Hitmonlee for about 20 frames. If that isn't feasible, bring the cut
  option to the orchestrator.
- **Critic #6:**
  - Lab: Garius: "Hey, there's still one in there!" / Rowan: "That one stays with me. Until I know who it's
    meant for."
  - Looker goes into the rally camera pan: he glances east at Cyrus and says "...Hm. That suit. Hm hm."
- **Critic #8:**
  - Ruth (in place of the old tutorial line): "That portal reader? I built it myself from a Poketch and a broken
    Dowsing Machine. Don't tell the Professor."
  - Saros, after "A child." (msg 102): "My daughter would have turned nine this spring."
  - Garius's Oreburgh dad slip (`oreburgh_city.json:14`) goes back to present tense.
  - Drop the narration in jubilife msg 107.
- **Bible:** a Twinleaf NPC mentions that Lake Valor was drained "years ago". Check whether the Town Map still
  shows Lake Valor at its stock site, and report what you find.

### M `mons`: Gen 3 encounters, Arc 1 trainer teams, Roark
Owns: `res/field/encounters/**`, `res/trainers/**`, `generated/trainers.txt` (only if needed).
- **Roark:** the team from `docs/story/trainers.md` Gym 1. Geodude Lv13 with Focus Sash (Stealth Rock, Rock
  Throw, Magnitude, Defense Curl), Onix Lv14 with Oran Berry (Rock Tomb, Screech, Rock Throw, Bind), Cranidos Lv16
  with Sitrus Berry and Mold Breaker (Headbutt, Pursuit, Zen Headbutt, Leer). IVs (power) about 150. AI flags
  BASIC, EVAL_ATTACK, EXPERT, CHECK_HP.
- **Gen 3 wild Pokemon** per `route_pokemon.md` "Arc 1":
  - Route 201: Zigzagoon, Wurmple.
  - Route 202: Poochyena (night), Taillow.
  - Route 203: Ralts (rare), Whismur.
  - Oreburgh Gate and Mine: Aron, Nosepass, Makuhita.
  - Lake Verity: Surskit, Lotad (Surf).

  Add them, don't replace: Sinnoh's own Pokemon stay. Use the day/night and special slots where the doc says so.
- **Route trainers, Routes 201-203, Oreburgh Gate and Oreburgh Mine:** rework the teams to feature the new Gen 3
  species (and leave room for Gen 5 later), at levels that fit the new curve up to Roark's 13-16. **Send the full
  proposed list to the orchestrator before you write it.** It's a design call.
- **Gen 5 placement** (Patrat and Lillipup on 201, Pidove and Purrloin on 202, Sewaddle on 203; Roggenrola,
  Drilbur and Timburr in the Mine) waits until workstream G lands the species. Do it as a follow-up.

### G `gen5`: Gen 5 species, starting with Arc 1's eight lines
Owns: `generated/species.txt`, `res/pokemon/<new>/**`, species-related `src/`/`include/`, Pokedex data and graphics,
cries and icons, `tools/gen5_sprites/**`.
- **Precedent:** commit a7a6b38db1 added Deino, Zweilous and Hydreigon as #494-496. Follow that pattern. Read its
  diff first, then `route_pokemon.md` "The rules" (the save-file Pokedex size and the form IDs after #493).
- **Scope now:** the eight Arc 1 lines, complete enough to catch, battle, evolve and register in the Pokedex:
  Patrat, Lillipup, Pidove, Purrloin, Sewaddle, Roggenrola, Drilbur, Timburr (with their evolutions, about 22
  species).
  - Data: base stats, types, abilities, learnsets, evolutions, Pokedex text, sprites (gen5_stream.py), icons,
    cries, footprints.
  - Moves and abilities the engine doesn't have get the closest Gen 4 substitute. Report each one.
- **Decisions to bring to the orchestrator first:**
  - Whether this breaks existing saves.
  - Whether to reserve IDs for all of Gen 5 now.
  - How Gen 5 species are numbered in the Sinnoh dex.
- Don't edit encounter tables. M places the new species after you land.

## Rules (every workstream)
- Edit only files you own; anything else goes in your report. `generated/vars_flags.txt` and `docs/arc1/**`
  belong to the lead.
- Build in your own worktree with `make release` (never plain `make`). Text: use `\r` to clear the box and `\f`
  to scroll (this repo swaps them). ASCII quotes only, no `"` inside text, 27-tile boxes.
- Verify headlessly with `~/.venvs/desmume/bin/python`. Earlier harnesses are in `/tmp/a1fix/*/harness/`. Evidence
  goes under `/tmp/a1r2/<ws>/`.
- Commit to `a1r2/<ws>`, one commit per item. Don't push or merge. Your final report gives each item, its files,
  the evidence, and anything still open.
