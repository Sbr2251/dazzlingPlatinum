# Arc 1 round 3: new content after Rowan's lab (as built)

Owner-approved additions (2026-10-10) so that Arc 1 part 2 stops playing like stock Platinum. All five are merged into
`arc1-part2` and verified headlessly on the combined build. Evidence: `/tmp/a1r3/integrated/` on the devserver.
None of them changes the `VAR_ARC1_PROGRESS` ladder (9-16, see `docs/arc1/part2/spec.md`).

## Lab gift: Portal Reader (end of scene 9)
- Rowan keeps the Violet Shard. At the end of the lab scene he gives the player a spare of Ruth's homemade reader:
  "Ruth built it from spare parts... If it ever starts buzzing, you call us. At once." Ruth: "It's a spare! I built
  two. ...Okay, three."
- Key item **Portal Reader** in the unused slot 126 (the Violet Shard took 125). Bag icon: violet recolour of the Poke
  Radar icon. It has no bag use; story scripts check for it.
- Route 202: Ruth's line now ends "Don't tell the Professor whose Poketch it was."

## Route 202: pilgrims (scene 10)
- Five people walk to the rally, each carrying a photo of someone they lost: an old man (wife; Lake Valor honeymoon
  "back when there was a lake"; the same sprite as the rally's "one more day" man), a father (daughter), a sailor
  (his Machoke), a young woman (big brother), a teen (mother).
- Visible at progress 11-12. At 13-15 only the old man and the father remain, walking home with new lines. All gone
  at 16. Hide flags are map-local temporaries (0x30/0x31).

## Jubilife: "Follow the crate" (after the rally, progress 13-15, optional)
- Looker (still "Man in a Trench Coat") stands at the east exit and asks the player to tail an Eclipse grunt who
  drags a crate (stock briefcase sprite) from the Pokemon Center to the Route 204 mouth.
- Stealth tail: 3 stops. At each stop the grunt runs a look cycle that advances one beat per player step, with
  hand-made sight cones. "Huh? ...Kid, scram." resets the player to the stop's checkpoint.
- Handoff: "Another one for the Ravaged Path." / "Did it just move?" / "Don't ask what's inside." Looker: "Pokemon go
  in. Crates come out. And I do not yet know what happens in between." Reward: 3 Great Balls.
- Flags: `FLAG_UNK_0x091C` = done, `0x091D-0x091F` = hide flags recomputed per load. Suggested names:
  `FLAG_ARC1_CRATE_DONE`, `FLAG_HIDE_ARC1_CRATE_LOOKER/GRUNT/RECEIVER`.
- Plants the Arc 2 Eterna Haven manifests and the Ravaged Path (Hitmonlee) totem. No torture is revealed.

## Route 203: the rift scar (scene 12)
- Chunk `map_data_019` only: a violet glowing fissure, scorched and cracked ground, and a split tree fallen across the
  old road. Detour north around the crack through a 2-tile gap at its tip. Works both ways; the old ledge row is
  removed.
- Art is appended to texture set 006 (palette swaps of stock texels plus two 32x32 overlays). Other maps that use the
  set are pixel-identical. Tools: `tools/route_203/`.
- Garius's second battle (D10 team, Yes/No) moved to the crack tip; the trigger is the gap column (x210, z744-745). New
  first line: "Whoa... check out this crack! The news said lightning. ...Since when is lightning purple?"
- Flavour: a Hiker ("Lightning, they say. ...I didn't hear any thunder."), a Picnicker ("...Then why won't it wash
  off?"), and two Starly that flee over the crack.

## Oreburgh: "The shard hums" (optional, from progress 14, open after Gym 1)
- A miner's Machop is missing after the tremors. The Portal Reader buzzes faint, then loud, then found, at the
  coal-yard and the west back alley (a kid saw it), then down the Mine B2F north shaft to a crack behind old crates.
- New map `MAP_HEADER_OREBURGH_MINE_SIDE_TUNNEL` (reuses the stock Ruin Maniac Cave long geometry): Roggenrola,
  Drilbur and Timburr Lv 7-10 make up about 90% of encounters. It stays open as a Gen 5 spot.
- Calming is a scripted beat, not a battle. The violet sliver slides out and crumbles; the reader goes quiet.
- Reunion: the "two days... a week" lesson ("what's a week doing to whatever's behind that seal?"), reward Black
  Belt. If the player has the reader, the sealed B2F bay gets an extra line.
- Flags `FLAG_UNK_0x0958-0x095B`. It never touches `VAR_ARC1_PROGRESS`, and Gym 1 and the rift scene work in every
  quest state.

## Oreburgh Gym: rock-slide puzzle
- Two Machop winch crews each slide a rubble pile between two gates (the west winch: lower stairs <-> east path; the east
  winch: upper stairs <-> lower stairs). Both winches are needed to reach Roark; an exhaustive search found no
  soft-lock state.
- Stock terrain and trainers (Jonathon, Darius) are kept. Map-local vars plus hide flags 0x30-0x33. After the badge, all
  rubble is cleared. Roark's script is unchanged apart from one silent rubble-clear call after the badge.

## Open
- The Town Map still draws Lake Valor full, at its stock site (needs map art).
- The crate tail runs about 110 s with one catch (the target was 60-90 s). The grunt could walk faster between stops.
- Workstream S2's Looker cameo in the rally pan and the crate tail's Looker are the same man. The rally line "...Hm.
  That suit." comes first, so the order works.
