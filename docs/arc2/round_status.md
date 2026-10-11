# Arc 2: built overnight (2026-10-10 → 11), status

Branch `arc2` (pushed). The plan is in `docs/arc2/PLAN.md`, the text in `docs/arc2/screenplay_v2.md`, and the contracts in `registry.md`,
`rift_contract.md` and `cutaways.md`.

## Verification
Integration QA ran one chained headless playthrough on the final tree, from the post-Gym 1 save (Oreburgh, `VAR_ARC1_PROGRESS` 16)
to END OF ARC 2 (`VAR_ARC2_PROGRESS` 99). Fantina through the end ran in one session, with no story-flag pokes.
- **Result:** 32/32 scenes PASS and 40/40 handoffs OK, checking progress, control, music, and no black-screen hangs.
- **Coverage:** all 5 Distortion World maps, all 4 cutaways (2.4, 2.13, 2.19, and the final one at 98) and all 4 suspect-ledger prompts.
- **Battles:** every gym leader, Cyrus 1-3, Garius ×2, Indra and both tag battles started with the right teams.
- **Report:** `/tmp/a2/qa/REPORT.md` on the devserver. Golden saves at each block are in `/tmp/a2/golden/arc2_*.sav`.

## Built (P1 + most of P2)
| Area | What |
|---|---|
| Story, 2.1-2.26 | Every scene in screenplay_v2, plus 2.16a (Solaceon wall, Indra), 2.17a-d (depot heist + Indra battle, Meteor Shrine trial, Route 215 crate, dawn plan) and 2.21a (Looker's briefing) |
| Spine fixes | C1-C11 applied in Arc 2: Indra wants to know what stopped Cyrus; the elder tells three stories of people who tried (each echoes a leader) and that "something rose from beneath"; Rowan's turn starts in Jubilife |
| Mechanics | The Resonator (Portal Reader + Calm Shard) gates field powers on badge + calmed totem, with a ghost-totem cut-in. Party-menu HMs are off. Resonator echoes replay what happened at 3 sites |
| Distortion World | 5 rifts: scars (Ravaged Path), ceiling + honeycomb (Eterna Forest), hops + boost choice (Route 214), the Drowned Lake with old Lake Valor hanging overhead (Route 213), and the Lost Tower alone with ghost totem acts |
| Mystery | Suspect ledger (`VAR_ARC2_SUSPECT`), fair clues (the call, no Poketch number, Route 215 crate red herring), the Basin night question, and the beach choice |
| Trainers | Gyms 2-5 per trainers.md, with a per-mon ability field, Mega Gyarados/Gengar and the Mega Lucario trial. Cyrus ×3, Garius ×2 (no Mega in Arc 2), Indra, 14 grunts, Arc 2 route levels |
| Pokemon | 19 new Gen 5 species (Woobat … Beheeyem); Gen 3/5 encounters on every Arc 2 map; the Sinnoh dex grows to 307 |
| Side content | Plusle/Minun reunion, Duchess reunion, Rowan's TV interview and retraction, 4 Mega stones placed, the Worn Trainer Card |
| World art | Route 212 brass gate, Solaceon memorial wall, Meteor Shrine, Route 210 violet rift mist, Route 203-style texture appends |
| Art | Indra, Kahn, Looker (janitor, newspaper), Eclipse crate/frame/rift/crystal, Eclipse class palettes, Cyrus's partner back sprite, Resonator icon, Eclipse battle transition |

## Fixed along the way (engine/data)
- **Battle message tags** were hard-coded and shifted by the Mega commit, so the tag/double battle intro and send-out text was wrong. The tags are now looked up by name. This also fixes Arc 1-era double battles.
- **narc tool** realloc bug; the build crashed past 5,000 Pokedex files.
- **Text paging:** chained messages whose last page wasn't terminated were overwritten unread (14 spots).
- **Totem battle text:** it opened with "A wild X appeared!"; it now reads "Totem X appeared!".
- **Story blockers from stock content that no longer gets cleaned up:** the Valor Lakefront TV crew, the Coronet tunnel grunts, and the Veilstone depot guards.

## Known open (none block the main path)
- **Cosmetic:** in Eterna Forest, the forest shade outside the Resonator cut-in band disappears while the band shows (likely stock `hm_cut_in.c` masking).
- **Placeholders:** Ruth, Darren and Garius still use stock overworld sprites (the sprite work is parked on `wip/ow-sprites`). Plusle/Minun, the Pip Budew and Litwick use stand-in sprites.
- **Not done:** the Absol "rift barometer" swap, real contest-prize hook for Gardevoirite (an NPC gives it), the depot as a noise-distraction variant, night tint on night scenes.
- **Arc 3 must pay off:** see `docs/arc2/PLAN.md` Appendix B and the critic's list (suspect ledger, Basin answer, beach choice, Elias card, Indra's role, Garius's Mega).
