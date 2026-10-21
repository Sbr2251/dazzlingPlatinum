# Arc 2 plan: Gym 1 to Gym 5 (draft for the owner)

Base: `main` @ 43f6445ca2. Sources: `docs/story/bible.md` (new spine, commit 833771761e), `secrets.md`,
`arc2_part{1,2,3}_screenplay.md` (identical to the Google Doc "Arc 2 Screenplay" tab, checked line by line),
`arc3_screenplay.md` (= the doc's Arc 3 tab), the Arc 1 round docs, and the real Arc 1 text in `res/text/*.json`.
Scene ids (2.x) are the drafts'; new scenes get letters (2.9a). Msg ids are `res/text` indices.

---

## 1. Arc 2 at a glance

### What Arc 1 actually hands to Arc 2 (from the built text, not the screenplay)

| Plant in the ROM | Where | Arc 2 must pay it off |
|---|---|---|
| Rowan: "Nobody comes back from longer than that. ...Nobody." | lab msg 82 `Arc1RowanNobody` | The confession (2.2) is where Rowan eats that word. His turn starts here, not at Celestic. |
| Rowan: "That one stays with me. Until I know who it's meant for." | lab msg 79 | 2.2: he gives Cyrus that ball and says so. |
| Rowan keeps the Violet Shard; gives the **Portal Reader** ("If it ever starts buzzing, you call us.") | lab msgs 84-87, `ITEM_PORTAL_READER` | The Reader is the seed of the Resonator (suggestion 8). |
| Rowan never accepted Cyrus's claim ("From that world? Sir, you've had a shock") | lake_verity msg 40 | Draft 2.2's "You came out of that portal" must change (C7). |
| Crowd: "they don't need the door. They'll just undo the day it closed." | jubilife msg 119 | Already on the new spine (Dialga + Palkia undo a death). Saros/Kahn scenes should echo it. |
| Pilgrim father: "They asked for her name. Her birthday. Where it happened." | route_202 msg 28 | Eclipse catalogues deaths: the Solaceon memorial wall (suggestion 4). |
| Crate tail: "Another one for the Ravaged Path." / "Pokemon go in. Crates come out." | jubilife msgs 132, 136, `FLAG_UNK_0x091C` | Looker recognises the player at the Haven if the flag is set; the 2.5 frame pays it off. |
| Machop's splinter: "If two days did that... what's a week doing?" | oreburgh_city msgs 40-42 | The small version of S4; the Hitmonlee totem is the "week". |
| Garius: "how he compares to my dad... ...Huh? Forget it." (present tense) | oreburgh_city msg 0 | Track G stays subtle until 2.20. |
| Cyrus: "I know this hum. From a lake." / "Did the shadow cast me out?" | lake_verity msgs 25, critic #4b | 2.2 sharpens "it stopped me"; the "sent" answer stays in 3.12. |

### Beat list, adjusted for the new spine

| # | Draft scene | Beat (as drafted) | Spine adjustment |
|---|---|---|---|
| 1 | 2.1-2.3 Jubilife | Cyrus found; confession at the Trainers' School; Garius storms out; Rowan gives the third starter; Cyrus battle 1 | Rowan's turn starts here (pays off msg 82). Cyrus: something "rose up and stopped me" (plant for Arc 3's "it stood against me"). |
| 2 | 2.4 cutaway | Kahn + Indra get the first tip | Indra's line rewritten (C1): she fixes on *what stopped him*. Her Arc 3 race starts here. |
| 3 | 2.5-2.8 Route 204 | L0 at Ravaged Path; tag battle; DW puzzle; Hitmonlee totem; Calm Shard; Resonator; Garius back "from Floaroma" | Resonator is built *from the Portal Reader* (S8). First "Who knew?" prompt (S2). |
| 4 | 2.9 Floaroma/Windworks | L1: site packed up after "a call" | Windworks becomes a cold-site investigation, not a walk-through (S11). The call is a fair clue (S3). |
| 5 | 2.10-2.11 Eterna Forest, Gym 2 | Vespiquen totem (badge-locked power), Gardenia | Garius rival battle 1 of Arc 2 (S5). |
| 6 | 2.12-2.13 Eclipse Haven | Looker undercover; manifests; double battle with Gardenia; the raid that worked | Pilgrim reunion thread (S11). Cutaway unchanged. |
| 7 | 2.14 Coronet | Heat under the grate; Cyrus's hand on the wall | Keep. It's Cyrus's sense, not Eclipse's target. |
| 8 | 2.15-2.16 Celestic | Elder's warning; Saros; G4; Cyrus battle 2 | Rewrite (C2-C5): three stories of people who tried, each ending with "the one beneath"; Cyrus recognises his own story (S1). |
| 9 | *new* 2.16a Solaceon | (no draft scene; Solaceon redesign is approved for Arc 2) | Indra's loss scene at the memorial wall (S4). |
| 10 | 2.17-2.17b Veilstone | Gym 3; Looker: "This man does not exist."; Meteor Shrine, Key Stone, starter stones | Plus the depot heist with Looker and the first Indra battle (S4, S11). |
| 11 | 2.18-2.19 Route 214, Kahn | L2: boosted Skarmory; Kahn's cliff | Boost becomes a player choice before the totem (S9). |
| 12 | 2.20 Pastoria, Valor Basin | Gym 4; Garius at the fence (G3b) | Playable night scene with a Yes/No that reads as a confession later (S5). |
| 13 | 2.21-2.22 Route 213 | L3: Looker's raid; Psyduck saved; Lapras pulled through; Rowan rejects | Raid becomes a timed stealth rescue; the rift opens onto the swallowed Lake Valor (S6). Rowan's line fixed (C6). |
| 14 | 2.23 beach | Garius lists the leaks; Cyrus battle 3; Cyrus leaves for the Lost Tower | Garius's list reflects the player's own ledger (S2). |
| 15 | 2.24 Hearthome | Gym 5; Saros at Mira's grave | Fantina's "wait" replaced by the tower vigil (S11). |
| 16 | 2.25-2.26 Lost Tower | Solo DW; the vein; told only to Rowan and Garius; grunts mine it; Cyrus cleared; Spiritomb | The Resonator guides instead of Cyrus (S7). END OF ARC 2. |

### Contradictions with the new spine (and the fixes)

| # | Draft location | What it says | Why it conflicts | Fix |
|---|---|---|---|---|
| C1 | 2.4, Indra + its Note | "...Out of it. Then the door opens both ways." Note: "if someone can come out of that world, her brother can too." | Old spine: Indra pulls Teo out of Giratina's world. Now she has no legendary, guards Saros's and Kahn's plan, and races to stop the player. | Kahn: "He says something stopped him, in his world. Something older than all of us." / Indra: "Something stopped a man who held Dialga and Palkia." / "Find out what. Nothing stops this one." (The informant heard 2.2; Cyrus never names Giratina.) |
| C2 | 2.15, elder | "When the three are threatened, the renegade one... sends someone back through the torn world. A guide." | Owner removed the guide legend (bible: "tells the old stories of those who tried"). | Three short stories of people who tried (S1). Their shared ending ("something rose from beneath") is a **proposed** addition, flagged in D1. |
| C3 | 2.15 | "Rowan's eyes go to Cyrus." | Reacts to the removed legend. | Cyrus reacts to the stories instead: he *is* the fourth one. |
| C4 | 2.16, Rowan | "A guide from the world beneath... the old stories say it happens for a reason." | Rowan's turn depended on the guide legend. | Turn moves to 2.2 ("...Nobody." payoff). At Celestic he asks the elder if the dead can come back; she answers; he admits he hopes (S10). |
| C5 | 2.16, Cyrus | "'Sent.' ...I was sent." / "If I was sent, then something believes..." | Steals 3.12's payoff ("No. You sent me.") and depended on the legend. | "She told my story. She left out the ending. Something rose from beneath and stopped me. I have never been so glad to lose." Plants "it stood against me" for Arc 3. |
| C6 | 2.22, Rowan | "I went to Celestic believing, for the first time, that it could be done." | Belief now starts in Jubilife. | "Since that night in Jubilife, I've believed it could be done." |
| C7 | 2.2, Rowan | "You came out of that portal and walked straight back in." | Arc 1 text has Rowan *dismissing* the claim (lake_verity msg 40, lab msg 82). | "I told these two that nobody comes back from that place. ...Nobody. And here you stand." |
| C8 | 2.2, Cyrus | "something older than all of us dragged me into its world for what I'd done" | Compatible, but too soft to carry Arc 3's "it stopped me". | "...rose out of the dark and stopped me. Then it took me into its world." |
| C9 | Arc 2 overall | Saros (2.24) and Kahn (2.19) get loss scenes; Indra's only loss scene is 3.7, written for the old spine | Bible: each leader gets one; Indra's new role needs Arc 2 setup. | New 2.16a Solaceon cutaway (S4); 3.7 becomes her hearing the plan (Arc 3 rewrite). |
| C10 | secrets.md L1b | "Cyrus is the one the legend is about" | Legend removed. | "Cyrus is one of the people the stories are about." Still points at him. |
| C11 | Arc 3 lines Arc 2 sets up | 3.6 Cyrus "Two of three. Only Giratina is left."; 3.7 shard compass to Coronet, "I'm coming to get you"; 3.8 Looker "they mean to take it", Cyrus "She's found its home"; 3.11 Indra "So can my brother"; 3.12 "You knew they would come for you" | All assume Eclipse hunts Giratina. | Out of scope here; list for the Arc 3 pass: 3.6 "They have both. ...There is one thing left that can stand against them."; 3.11 "Take it, and Saros's morning and Kahn's door both break. And Teo stays dead."; 3.12 "You knew they would take the other two." |

No contradiction: 2.25-2.26 "the wall of shadow parts" (Giratina helping the trainer fits the new spine); 2.19 and 2.24
(Kahn wants Palkia, Saros wants Dialga); 2.26's note that the vein powers the Arc 3 captures.

---

## 2. Story suggestions (ranked by impact)

Cost key: **script** (scripts/events/text only), **map edit** (existing map changed), **new map**, **engine** (C code).

### S1. Celestic: three stories, one ending
- **What:** The elder tells three short stories of people who tried to hold the creation trio, each a mirror of a
  leader the player hasn't fully met yet, and each ending the same way. Cyrus realises he is the fourth story.
- **Where:** 2.15-2.16, the Celestic shrine; the stock ruins mural is the backdrop.
- **Why:** Fixes C2-C5 with the owner's own wording ("controlling the legendaries for personal goals has never
  ended well"). It humanises all three leaders before Arc 3 (players will match each story to a cutaway), and
  plants the one idea Arc 3 turns on: something beneath can stand against Dialga and Palkia.
- **Replaces:** Stock Celestic: the Galactic grunt at the ruins, Cyrus's speech, the elder's relic scene.
- **Beat:**
  - Elder: "A king stopped the clock on the morning his queen still breathed. His kingdom stood frozen in that morning for a hundred years." *(Saros)*
  - Elder: "A sailor folded the sea to find the world where his partner never drowned. He found it. He could never find his way home." *(Kahn)*
  - Elder: "A sister kept watch at a gate for her brother. She kept everyone else out too, until there was no one left to let in." *(Indra)*
  - Elder: "Each time, something rose from beneath the world and set it right. Never gently."
  - Cyrus (2.16, after battle 2): "She told my story. She only left out the ending. Something rose from beneath, and stopped me."
- **Cost:** script. Optional: one mural sign event (map edit).

### S2. "Who knew?": the player keeps the suspect ledger
- **What:** After each leak (L0, L1, L2, L3), Ruth asks who could have told Eclipse. Multi-choice: Cyrus / Garius / Ruth /
  "Bad luck". The game stores picks in one var (`VAR_ARC2_SUSPECT`, 2 bits per leak). Reactions stay neutral, so Garius
  picks get no special treatment.
- **Where:** End of 2.5, 2.9, 2.18, 2.21. Callbacks in 2.23 and Arc 3's 3.2.
- **Why:** Track L's misdirection is the player's own Platinum knowledge. This makes them commit to it on the record,
  so the reveal accuses them too. It's agency without branching the plot.
- **Replaces:** Nothing in stock; turns the drafts' four "everyone looks at Cyrus" moments into choices.
- **Beat:**
  - Pick Ruth: "Me?! The worst thing I've ever done is take the Professor's Pokétch apart!" (pays off route_202 msg 21, "Don't tell the Professor whose Pokétch it was.")
  - Pick Garius (2.5): Ruth: "Garius? He'd sooner eat his own badge than help anyone in a dark coat."
  - 2.23 Garius, if you picked Cyrus 3+ times: "You've known since Ravaged Path. You just needed somebody to say it."
  - 3.2 (Arc 3 rewrite), Garius: "You picked him. Every single time." or, if you ever picked Garius: "You almost had me at the Windworks. Then you looked away."
- **Cost:** script.

### S3. Fair-play clue kit: the call, the crate, the words
- **What:** Three planted clues for Garius and one new red herring for Cyrus, plus a whereabouts table the scripters
  must keep true.
  1. **The call (fair):** L1's worker: "One of them got a call, and they packed up." In 2.17 Looker adds:
     "No Trainer ID. No Pokétch number. Nothing." Cyrus can't make a call. Nobody says so; Garius checks his Pokétch
     on Route 204 ("Nine missed calls. ...My mom.").
  2. **The words (fair):** already drafted. Grunts call Cyrus "the one who walked out" (2.5), the informant's phrase
     (2.4). Keep it in 2.18 too: "Tell the one who walked out his bird says hi."
  3. **The crate (red herring):** 2.17c, Route 215 at night: Darren finds Cyrus beside a pried-open Eclipse crate,
     a Buneary bolting into the grass. Cyrus: "You would not believe me if I explained." Paid off in 2.26: Looker,
     "Someone has been opening Eclipse's crates on Route 215. Every Pokemon released. ...I suspect I now know who."
  4. **The Haven (fair):** keep the draft's exception (the one raid Garius didn't know about worked).
- **Whereabouts (must hold):** L0 Garius heard the plan, then "cooled off in the flower fields" north; L1 Garius left
  Floaroma that night; Haven Garius already in Eterna Gym's queue, then gone; L1b Garius knew Rowan's Celestic
  meeting; L2 at the Veilstone Pokemon Center; L3 at Looker's briefing; vein told by phone to Rowan with Garius beside him.
- **Cost:** script; one night-only event pair on Route 215.

### S4. Indra, the warden (set up her Arc 3 race)
- **What:** Indra is Eclipse's security and its record-keeper. Three Arc 2 touches:
  1. 2.4 rewrite (C1): she asks what stopped Cyrus.
  2. **2.16a Solaceon, cutaway** (the player only): the approved memorial wall, every photo labelled with a name,
     a date and a place (the pilgrims' photos from Route 202 are up there; the father's Ponyta drawing too).
     Indra pins up a fresh card for Teo. "Saros wants a morning. Kahn wants a door. I don't care which one works,
     Teo. Either one brings you home." / "Saros's hands shake now. Kahn doesn't sleep. The shards are taking
     something out of them." / "So I keep the door. Nobody gets through who could break it."
  3. **2.17a Veilstone depot**: first face-to-face, at the end of the heist (S11). She battles the player to cover
     the trucks, then lets them go: "Go home, kid. Somebody's waiting there. Don't make them wait forever."
- **Why:** Her new role ("guards the plan, races to stop the player") has zero setup in the drafts. This gives her a
  motive, a habit (keeping people out), a fear Arc 3 cashes in, and the S9 plant (shards burn their users), which
  currently has no plant before Arc 3.
- **Replaces:** Stock Solaceon (no story beat) and the stock Veilstone warehouse grunts.
- **Cost:** map edit (Solaceon wall, already approved), new trainer (Indra team 1), script. Needs Indra's sprites.

### S5. Garius in the open: two rival battles and the Basin question
- **What:** The drafts give Garius no Arc 2 battles. Add two, and turn G3b into a playable choice.
  - **Eterna (after Gym 2):** "Some old guy in Floaroma said Eclipse gave him his wife's Pokemon back. Gave it BACK.
    ...Battle me." (in hindsight he's half-recruited and wants it to be true).
  - **2.20 Valor Basin at night:** if the player walks to the fence, Garius stays. "If someone told you they could
    fix the worst thing that ever happened to you... and all it cost was telling them stuff nobody'd miss. Would
    you?" Yes/No. Yes: "...Yeah. Me too." No: "Must be nice." Stored for Arc 3's reveal ("You said yes. At the
    Basin.").
  - **Hearthome (after 2.23):** a sour battle with his Mega starter; he's angry Darren hasn't cut Cyrus loose.
- **Optional plant:** a card on the Solaceon wall: "ELIAS. Valor Basin." No submitter. Readers who saw the Basin
  plaque connect it.
- **Why:** "Drifts in the open, spies in secret" needs the open drift to be on screen. The Basin question is a
  confession only after the reveal.
- **Replaces:** Stock Barry's Pastoria/Hearthome battles.
- **Cost:** script plus trainer data (2 Garius teams).

### S6. Set piece: the Drowned Lake (Route 213, Looker's proof)
- **What:** Two halves.
  1. **The raid, played:** the cave on Route 213 at night. A stealth approach past two patrols (the crate tail's
     look-cycle and sight-cone tech), then a step budget to reach the Psyduck frame before the air splits.
     Spotted = "Kid, scram"-style checkpoint reset, no fail state. The Lapras frame is already torn (L3: they rushed it).
  2. **Through the Lapras rift: the lake that vanished.** The bible says the Valor Basin portal "swallowed the lake into
     the Distortion World". Here it is: Lake Valor hangs upside down as the ceiling, its old bed is the floor, and
     everything it swallowed is still lying there (a rowboat, a lakefront sign, a rusted first-generation frame).
     The seams climb the west wall onto the ceiling surface beneath the water. The Lapras totem waits on the hanging
     lake's one island.
  - **Plant (S5b, player only):** an item beside the old frame: "An old Trainer Card. The name has worn away.
    Hometown: Twinleaf." Nobody comments. In Arc 3, after Indra's 3.14, the player can show it to Garius (D5).
- **Why:** S4 (totems are tortured Pokemon) becomes something the player does under pressure, not watches. It shows
  Eclipse's first crime in the same world the player is fighting in, beside Garius's father's death, without telling.
- **Replaces:** Stock Pastoria Great Marsh grunt chase and the Lake Valor explosion.
- **Cost:** new map (Phase 1 DW terrain, the expensive one), engine small (ceiling surface data via
  `tools/distortion_world/twarc.py`), script (raid reuses the crate-tail stealth pattern).

### S7. Set piece: the Lost Tower alone (end of Arc 2)
- **What:** In the first DW map without Cyrus, the totems he helped you calm are your guides. At each seam, the
  Resonator glows and a ghost totem acts: ghost Hitmonlee kicks a scar shut, ghost Vespiquen lights the true seam,
  ghost Skarmory carries you across a gap, ghost Lapras lifts a submerged path. Cyrus's words from 2.6 come back as
  on-screen text at the first seam (kept from the draft). The Resonator's "dissonance" buzz leads to the shard vein.
  The wall of shadow, then (2.26) Giratina's shadow parting it.
- **Why:** It pays off the theme ("I took. You were given."): freely given strength guides you where Cyrus can't. The
  player's own tool finds the vein Eclipse then steals, which is the bible's "the player's own discovery fuels the
  villains' endgame" made literal.
- **Replaces:** Stock Lost Tower (a plain climb) and Hearthome's filler.
- **Cost:** new map (Phase 1 DW), engine small (ghost cut-ins inside the DW overlay), script.

### S8. The Resonator grows: Reader, Resonator, Echo, Guide
- **What:** One device with four stages.

  | Stage | When | What it does |
  |---|---|---|
  | Portal Reader | Arc 1 (built) | Buzz-trail toward hurt Pokemon (Oreburgh hum) |
  | Resonator | 2.8 | Ruth fits the Calm Shard into the Reader: "I built three. I think this one was always meant to be this." Field powers with badge + totem. |
  | Echo | from 2.10 (2 shards) | At a torture frame, the Resonator replays a few seconds of what happened (ghost-palette sprites, like Teo's in 3.11): a crate opened, a Pokemon strapped in. Used at Ravaged Path, the Windworks, the Route 214 site. The player learns S4 gradually and *before* Darren does. |
  | Guide | 2.25 | Ghost totems solve seams in the DW (S7). |
- **Why:** The brief asks for a mechanic that grows; this one also carries the evidence chain toward Looker's proof.
- **Replaces:** HM menu, HM items, and the Bidoof cut-in from commit 12b35ff530.
- **Cost:** engine small (per-totem cut-in sprite in `src/field_move_tasks.c`; key-item swap), script (echoes are
  scripted cutscenes, no new scrcmd), art (5 ghost cut-ins for Arc 2).

### S9. Rifts and totems that escalate
- **What:** Each rift adds one verb, using only what the stock DW engine supports (west/east walls, ceilings, hops,
  fading ghost props, a step hook for crumbling tiles; see `docs/arc1/revision/puzzle_wall_walk.md`).

  | Rift | New verb | Totem twist |
  |---|---|---|
  | Ravaged Path (2.6) | **Scars:** cracked wall tiles crumble one step after you leave them (step hook `ov9_0224A71C`). Cyrus: "That one is a scar." | Baseline Hitmonlee (aura + allies). |
  | Eterna Forest (2.10) | **Ceilings:** a hive; walk the ceiling (B4F record as template), ghost-prop honeycomb that fades in and out | Vespiquen summons Combee waves. |
  | Route 214 (2.18) | **Wall-to-wall hops** across a chasm with no floor (B4F "wall to another surface") | **Choice:** before the fight, pull the grunts' boost shard out (Yes: Cyrus burns his hand doing it; the totem fights unboosted) or leave it (totem +1 Atk/+1 Def). Totem config gains a boost field. |
  | Drowned Lake (2.21) | **Upside-down lake:** ceiling walking under water; read the hanging debris as landmarks | Lapras with Mantyke/Shellos; Perish-free rain. |
  | Lost Tower (2.25) | **Guided:** ghost totems act (S7), no Cyrus | Spiritomb fought after finding Cyrus beside it; his fainted starter is at its side. |
- **Level fix (current `src/totem_battle.c`):** Skarmory 35 sits above Maylene's 31 ace: set it 32 (+boost if
  left on). Lapras 36 vs Wake 35: OK. Spiritomb 30 to 40 (backlog): set 40.
- **Cost:** engine small (crumble hook, boost field), new maps (5 DW maps; see D8 for the cheaper tiers).

### S10. Rowan's turn costs something
- **What:** Rowan's belief goes public, and Eclipse uses it.
  - 2.2: "I told these two that nobody comes back from that place. ...Nobody. And here you stand."
  - 2.16: he asks the elder: "Can the dead come back?" Elder: "The stories never say they can't. They say what it
    costs." Rowan: "...I've spent my life saying no. I'm not sure I can anymore."
  - 2.16b, TV in any Pokemon Center: Rowan, interviewed: "I once called Team Eclipse con artists. I may have spoken
    too soon." By Solaceon, Eclipse banners quote him. Garius at Eterna/Hearthome: "Even Rowan says it's possible."
  - 2.22 (C6 fix): "Since that night in Jubilife, I've believed it could be done. Not like this. Never like this."
    Then he calls the station back to retract.
- **Why:** Track R is currently all private realisation. Making his hope feed Eclipse's recruiting gives the
  rejection weight and mirrors the vein: good people's discoveries fuel the villains.
- **Replaces:** Stock TV filler.
- **Cost:** script (TV message, banner signs). **Change flag:** the public retraction is new; see D4.

### S11. Stock filler becomes story stops

| Stock stretch | Becomes | Cost |
|---|---|---|
| Valley Windworks (Mars, the key) | **Cold site (2.9):** bolt holes, a warm generator, an Echo (S8). A Minun left behind in a cage; its Plusle went in the trucks. The Minun follows the Resonator buzz to a crate dropped on Route 205: reunite them (optional, rewards both as a gift pair). Gen 3 per `route_pokemon.md`. | map edit, script |
| Eterna Galactic building | **Eclipse Haven** (drafted). Add: one kennel tag reads "Duchess. Owner: deceased. Lake Valor." She's the Route 202 old man's late wife's Clefairy (msg 25). Return her to him in Jubilife: "I never once asked her if she'd want to come back. ...But this one, I can ask." The anti-Eclipse answer to grief, in a side quest. | map edit (interior), script |
| Veilstone warehouse | **Eclipse depot heist (2.17a):** with Looker (newspaper disguise), sneak through the depot (stealth sight cones) to copy the manifest naming the Route 213 site. That manifest is why Looker's raid exists. Ends with Indra (S4). | map edit, script |
| Pastoria Great Marsh bomb plot | Cut. Great Marsh stays a catching stop (Stunfisk, Tympole). The Drowned Lake (S6) carries Pastoria. | encounters |
| Hearthome: Fantina away (stock gate) | **The vigil:** the Gym is shut because Fantina sits nightly in the Lost Tower, where the dead "cry". The player can reach Hearthome early via Route 208/209; Fantina is at the tower base: "Not yet, mon ami. Ze tower is not ready for you." She mentions "a sad man who brings flowers to a small grave every month" (Saros). She returns to the Gym once the Fen Badge is in the bag. | script |
| Route 210 north fog (comes before Defog) | **Rift mist:** violet, thins near Absol; no blocker. | map edit |
| Route 212 top-left | **Plant:** a brass gate in the rock, ticking. Klink in the grass beside it. Arc 3's Lake Valor entrance. | map edit, encounters |

### S12. Story-coded encounters

| Species | Where | Story job |
|---|---|---|
| Plusle / Minun (Gen 3) | Valley Windworks | The separated pair (S11) |
| Absol (Gen 3, rare) | Within a few tiles of an uncalmed rift (Routes 210, 214) | Rift barometer; gone after the totem is calmed (encounter swap keyed on `FLAG_TOTEM_*`: engine small, or a second map header) |
| Yamask (Gen 5) | Solaceon | Grief town, the memorial wall |
| Litwick (Gen 5) | Lost Tower, the solo DW | Candle light at the seams; soul-eater lore beside the 108-spirit Spiritomb |
| Frillish (Gen 5) | Route 213 near the rift | The drowned; the swallowed lake |
| Sandile (Gen 5) | Valor Basin | The dry lakebed |
| Klink (Gen 5) | Route 212 by the brass gate | Leaks out of Arc 3's clockwork palace |
| Elgyem (Gen 5) | Meteor Shrine | The fallen star |
| Woobat, Cottonee (Gen 5) | Ravaged Path, Route 204 | Arc 2's first new catches |

Rest of the Arc 2 Gen 5 list (Venipede, Throh, Sawk, Mienfoo, Sigilyph, Tympole, Scraggy, Pawniard, Stunfisk) follows
in round 3 (D9). **Cost:** species data per the a7a6b38db1 / `a1r2/gen5` pattern, then encounter JSON.

---

## 3. Implementation plan (executable)

### Decided (recommendation taken; the owner can redirect later)

| # | Decision | Taken |
|---|---|---|
| D1 | Celestic rewrite (S1), including the shared ending "something rose from beneath" | Yes. It's the one addition beyond the bible's wording; mark it in `bible.md` as orchestrator-approved. |
| D2 | Indra in Arc 2: Solaceon cutaway (2.16a) + depot battle (2.17a); her loss scene moves from 3.7 into Arc 2 | Yes |
| D3 | Suspect ledger with Arc 3 callbacks (S2) | Yes. `VAR_ARC2_SUSPECT` is written in Arc 2; the Arc 3 lines are listed for the Arc 3 pass. |
| D4 | Rowan's public retraction (S10) | Yes, as a TV message and Solaceon banner text (P2; the private lines are P1) |
| D5 | Elias's worn Trainer Card in the Drowned Lake | Plant only (an item flavour text, `FLAG` set). The "show it to Garius" payoff is deferred to Arc 3. |
| D6 | Lake Valor's water hangs in the DW (S6) | Yes; dressing is P2 (Phase 1 terrain), the P1 map is a Phase 0 clone with the same script |
| D7 | Garius rival battles in Arc 2 | Two: Eterna (after Gym 2) and Hearthome (after 2.23), plus the Basin question |
| D8 | DW map tiers | P1: all five rifts as Phase 0 clones of stock DW floors with edited wall grids. P2: Phase 1 custom terrain for the Drowned Lake and the Lost Tower only. |
| D9 | Gen 5 in Arc 2 | P2. Story-critical 8 lines first (Woobat, Cottonee, Yamask, Litwick, Frillish, Sandile, Klink, Elgyem); placement waits on species. |
| D10 | Resonator vs Portal Reader | Ruth converts the Reader: `RemoveItem ITEM_PORTAL_READER` / `AddItem ITEM_RESONATOR` (slot `ITEM_UNUSED_127`). Calm Shards are not items; the totem flags are the shards. |
| D11 | HM moves | HM items are no longer given (each story workstream removes its town's HM give); the moves stay learnable by TM-style tutors later (P2). Field use is Resonator-only. |
| D12 | Valor Basin map | Reuse stock `MAP_HEADER_LAKE_VALOR_DRAINED` as the Basin, always in its drained state |
| D13 | Hearthome gate | Fantina's vigil at the Lost Tower replaces the stock wait; the Gym opens with the Fen Badge |
| D14 | Totem levels | Skarmory 32 (+1/+1 if the boost stays on), Spiritomb 40; others unchanged |
| D15 | Where the totems are fought | Inside each DW map (the bible's rule). The overworld `StartTotemBattle` objects are deleted by the story workstream that owns the map. |
| D16 | Cutaway staging | One "violet room" for 2.4/2.13 = stock Team Galactic HQ room unreachable in Arc 2 (lead picks the header in R0); Kahn's cliff (2.19) staged on Route 222 (unreachable in Arc 2) |

### Priorities

| Priority | Content | Rounds |
|---|---|---|
| **P1: playable post-Gym 1 to Gym 5** | All 26 scenes with spine fixes (C1-C9); S1, S2, S3, S4 (2.4 rewrite, 2.16a, 2.17a), S5, S9 (verbs + boost choice + levels), S11 rows Windworks/Haven/depot/Great Marsh cut/Fantina vigil/Route 210 mist (text-only mist); Resonator (S8 stages 1-2); 5 rifts at Phase 0; Gym 2-5 and story trainers; Mega side plot (2.17b); Arc 2 Gen 3 encounters | R0, R1, R2 |
| **P2: nice-to-have** | S6/S7 Phase 1 terrain and ghost-totem acts; S8 Echo; S10 TV/banners; S11 Plusle/Minun and Duchess quests; S12 Gen 5 + Absol barometer; Route 212 brass gate; Meteor Shrine and Solaceon wall map art; final Indra/Kahn/ghost art | R3 |
| **Integration** | Full headless run from the golden post-Gym 1 save to END OF ARC 2; level pass; critic review | R2 end (lead), R4 |

### Shared files: append-only care

R0 pre-registers everything below on `main`, so no workstream edits them. If a workstream finds it needs another entry,
it asks the lead (orchestrator) and never appends on its own branch.

| Shared file | Registered in R0 |
|---|---|
| `generated/vars_flags.txt` | Renames listed under "Flag and var allocation"; nothing else |
| `generated/map_headers.txt`, `include/data/map_headers.h`, `res/text/location_names.json` | 5 DW maps: `MAP_HEADER_DW_RAVAGED_PATH`, `_DW_ETERNA_FOREST`, `_DW_ROUTE_214`, `_DW_ROUTE_213`, `_DW_LOST_TOWER` (fields copied from `DISTORTION_WORLD_ARC1_SEAMS`). Append only; never insert before 594 (the arc1 seams map stores its numeric id; see revision STATUS). |
| `generated/text_banks.txt` | One bank per DW map, plus `arc2_common` (shared ledger prompt, Resonator messages) |
| `res/field/scripts/meson.build`, `scripts.order`, `res/field/events/meson.build`, `zone_event.order` | Stub script + events files for the 5 DW maps (copies of the arc1 seams stubs) |
| `src/overlay009/ov9_02249960.c` | `DISTORTION_WORLD_MAP_COUNT` raised and 5 standalone entries (pointing at copies of the arc1 seams record) so rift-a/rift-b only edit their own `tw_arc` JSON |
| `src/encounter.c` | Untouched by R1/R2; only the lead edits it if a DW map needs an encounter hook |
| `generated/items.txt`, 4 item text files, `res/items/pl_item_data.csv` | `ITEM_UNUSED_127` renamed `ITEM_RESONATOR` with text; icon = the Portal Reader's until art lands |
| `generated/trainers.txt` | All Arc 2 trainer ids (table below). Data files are owned by trainers-gym / trainers-story. |
| `generated/trainer_classes` list and class graphics | `TRAINER_CLASS_ECLIPSE_GRUNT_M/F`, `TRAINER_CLASS_ECLIPSE_LEADER` (placeholder: Galactic grunt/commander graphics) |
| `generated/object_events_gfx.txt` + `res/field/objects/...` | `OBJ_EVENT_GFX_INDRA`, `_KAHN`, `_LOOKER_JANITOR`, `_LOOKER_NEWSPAPER`, `_ECLIPSE_CRATE`, `_SHARD_FRAME`, `_RIFT_ARC2` (placeholder copies, as in Arc 1 D1-D3) |
| `res/graphics/item_icons/meson.build`, `item_icon.order` | Untouched in P1 |

### Flag and var allocation

Free and verified unreferenced in `res/ src/ include/ asm/` (grep, 2026-10-10): `FLAG_UNK_0x0920-0x0957`,
`0x095C-0x095F`, the spares `FLAG_ARC1_SPARE_A/B/D` (0x0918, 0x0919, 0x091B). Already used: 0x091C-0x091F (crate tail),
0x0958-0x095B (Oreburgh hum). Leave `FLAG_UNK_0x09F7-0x0A9F` alone until the lead proves no stock code indexes it.
Per-map hide flags use map-local temporaries 0x30-0x3F (Arc 1 round 3 practice).

| Owner | Flags | Vars |
|---|---|---|
| lead (R0) | 0x0920-0x0923 | Rename `VAR_UNUSED_0x406F` (0x4070) to **`VAR_ARC2_PROGRESS`**; `VAR_UNK_0x4072` (0x4073) to **`VAR_ARC2_SUSPECT`** (2 bits per leak: L0 bits 0-1, L1 2-3, L2 4-5, L3 6-7; 0 Cyrus, 1 Garius, 2 Ruth, 3 bad luck; bit 8 = "answered L0" etc. in bits 8-11); `VAR_UNK_0x408F` (0x4090) to **`VAR_ARC2_CHOICES`** (bit 0 Looker trust, bit 1 Basin answer, bit 2 Skarmory boost pulled, bit 3 Cyrus crate seen) |
| resonator | 0x0924-0x0925 | - |
| rift-a | 0x0926-0x0929 | map-local only |
| rift-b | 0x092A-0x092F (0x092E = `FLAG_ARC2_ELIAS_CARD`) | map-local only |
| s-jubilife | 0x0930-0x0933 | - |
| s-cutaways | 0x0934-0x0935 | - |
| s-route204 | 0x0936-0x0939 | - |
| s-floaroma | 0x093A-0x093D | - |
| s-eterna | 0x093E-0x0941 | - |
| s-celestic | 0x0942-0x0945 | - |
| s-veilstone | 0x0946-0x094A | - |
| s-route214 | 0x094B-0x094C | - |
| s-pastoria | 0x094D-0x0950 | - |
| s-raid | 0x0951-0x0954 | - |
| s-hearthome | 0x0955-0x0957, 0x095C-0x095F | - |
| P2 workstreams | 0x0918, 0x0919, 0x091B, then by request | - |

Each workstream names its flags in a comment block at the top of its main script (`FLAG_UNK_0x0930 = FLAG_ARC2_...`);
the lead renames them in `vars_flags.txt` at merge time.

**`VAR_ARC2_PROGRESS` ladder (blocks; each owner uses only its block, and sets the first value of the next block when its last scene ends):**

| Block | Owner | Key values |
|---|---|---|
| 0 | (Arc 1 left `VAR_ARC1_PROGRESS` = 16) | 0 = Arc 2 not started |
| 1-9 | s-jubilife (9 set by the 2.4 cutaway) | 1 Cyrus found, 3 confession done, 5 Cyrus battle 1 done |
| 10-19 | s-route204; rift-a sets 15 on Hitmonlee calm | 12 L0 tag battle won, 14 entered DW, 17 Resonator given, 19 Garius back |
| 20-29 | s-floaroma; rift-a sets 26 on Vespiquen calm | 22 Windworks done (L1 asked) |
| 30-39 | s-eterna (39 set by the 2.13 cutaway) | 31 Forest Badge, 32 Garius battle, 35 Haven shut |
| 40-49 | s-celestic | 42 Celestic scene, 44 Cyrus battle 2, 47 Solaceon cutaway seen |
| 50-59 | s-veilstone | 51 Cobble Badge + Looker, 54 depot + Indra, 57 Key Stone |
| 60-69 | s-route214; rift-b sets 63 on Skarmory calm; 69 set by the 2.19 cutaway | 61 L2 grunts beaten (L2 asked) |
| 70-79 | s-pastoria | 71 Fen Badge, 73 Basin night, 75 Looker briefing |
| 80-89 | s-raid (80-84, 87-89); rift-b sets 84 on Lapras calm; s-pastoria 85-86 (2.22 Rowan) | 82 Psyduck saved (L3 asked), 88 Cyrus battle 3 |
| 90-99 | s-hearthome; rift-b sets 95 on Spiritomb calm | 91 Relic Badge, 92 Garius battle, 93 vein call, 94 grunts at the tower, 99 END OF ARC 2 |

### Trainer ids (registered in R0; data owned as shown)

| Owner | Trainers |
|---|---|
| trainers-gym | Gardenia, Maylene (Gym), Maylene (Meteor Shrine trial), Crasher Wake, Fantina: teams exactly as `docs/story/trainers.md` |
| trainers-story | `CYRUS_ARC2_{1,2,3}_{TURTWIG,CHIMCHAR,PIPLUP}` (9; Cyrus holds the starter weak to the player's), `GARIUS_ARC2_{ETERNA,HEARTHOME}_{x3}` (6), `INDRA_DEPOT`, `ECLIPSE_GRUNT_ARC2_01..14` (Ravaged Path 2 as a double, Windworks 0, Haven caretakers 2, Route 214 2, depot 4, Route 213 raid 2, Lost Tower 2), `LOOKER`-free (no Looker battles) |

### Round 0: lead pre-work (about 1.5 h, on `main`, before anything else)
1. Registry commit (everything in the two tables above). Build `make release`; boot to title headlessly.
2. `docs/arc2/screenplay_v2.md`: the drafts with C1-C9 and the P1 suggestion lines applied (the text every story
   workstream implements verbatim; small box-fit edits allowed).
3. Golden save `/tmp/a2/golden/post_gym1.dsv` at `VAR_ARC1_PROGRESS` = 16 (reuse `/tmp/arc1/lead/flow.py`), and a
   harness helper `/tmp/a2/harness/setstate.py` that pokes `VAR_ARC2_PROGRESS`, badges and `FLAG_TOTEM_*` so any
   workstream can start at its block.
4. Text lint `/tmp/a2/harness/textlint.py`: ASCII only, no `"` in text, 27-tile boxes, `\r`/`\f` usage.
5. Rift contract table in `docs/arc2/screenplay_v2.md`: for each DW map, the overworld entry tile (rift object) and
   the exit warp (map, x, z, dir) plus the progress value set on calm. Rift and story workstreams both code to it.
6. D14 in `src/totem_battle.c` (Skarmory 32, Spiritomb 40). Check whether the Route 211 Coronet tunnel needs Rock
   Smash in the new order and note it in the screenplay doc.

### Common rules (every workstream)
- Branch `a2/<ws>`, worktree `/data/repos/dp-wt/a2-<ws>` (`git worktree add /data/repos/dp-wt/a2-<ws> -b a2/<ws> main`).
- Edit only owned files. Anything else goes in the final report. Story lines come from `docs/arc2/screenplay_v2.md`;
  new lines, changed beats or cuts go to the orchestrator (`d816fabe-d2df-4828-867e-21c297ab25a0`) first, batched,
  with a recommended option.
- Build `make release` in the worktree (never plain `make`). Verify with `~/.venvs/desmume/bin/python`; evidence
  (screenshots, logs, the harness script) under `/tmp/a2/<ws>/`. Commit one item per commit; no push, no merge.
- Every story workstream: start from `setstate.py` at its block, play its scenes end to end, assert the next block's
  first value is set, re-enter each map after every state (no stale NPCs), and run `textlint.py`.

### Round 1: foundations (all parallel, start right after R0)

| WS | Owns (exact) | Deliverables | Verify | Depends |
|---|---|---|---|---|
| **resonator** (5 h) | `src/field_move_tasks.c`, `include/field_move_tasks.h`, `res/field/scripts/scripts_field_moves.s`, `res/text/field_moves.json`, `src/item.c` (Resonator icon line only), `res/text/arc2_common.json` (Resonator msgs) | Replace the Bidoof cut-in (commit 12b35ff530) with the matching totem's front sprite as a ghost (palette fade) and "{Totem}'s energy surges through the Resonator!"; requires `ITEM_RESONATOR` + badge + `FLAG_TOTEM_*`; party-menu HM path disabled for field obstacles; message when the Resonator is missing | Headless: for rock, tree, water, rocky wall, set/unset badge, totem flag, item; screenshot each message; no softlock | R0 |
| **rift-a** (6 h) | `tools/distortion_world/{ravaged_path,eterna_forest}.json`, the `tw_arc*.narc` members for those two, their map data/matrix copies, `scripts_dw_ravaged_path.s`, `scripts_dw_eterna_forest.s` (+ init scripts), `events_dw_*.json`, `res/text/dw_ravaged_path.json`, `dw_eterna_forest.json`; the crumble step hook in `src/overlay009/ov9_02249960.c` (`ov9_0224A71C` only) | Phase 0 maps: Ravaged Path with **scar** tiles (crumble one step after leaving; reset via the arc1 fall script); Eterna Forest with a **ceiling** stretch (B4F record as template) and ghost-prop timing. Cyrus's lines (2.6, 2.10), the Giratina shadow fly-by (2.6), totem battle at the end (`StartTotemBattle`, set `FLAG_TOTEM_*`, Calm Shard text, "I took. You were given."), exit warp to the overworld coordinate the story workstream publishes in R0's screenplay doc | Headless: enter, fall and reset, finish, battle, return; progress var set to 15/26 | R0 |
| **rift-b** (6 h) | Same pattern for `dw_route_214`, `dw_route_213`, `dw_lost_tower` (tools JSON, narc members, map copies, scripts, events, text) | Route 214: wall-to-wall hops, the **boost choice** (reads/sets `VAR_ARC2_CHOICES` bit 2), Skarmory. Route 213: ceiling walk under the "lake", rusted frame prop, the worn Trainer Card (sets 0x092E), Lapras. Lost Tower: solo, the shadow wall (closed below state 94, open after), the vein room, Spiritomb with Cyrus kneeling beside it; Cyrus's 2.6 line as text at the first seam | Headless per map at the right block; Lost Tower both visits; progress var 63/84/95 | R0; uses rift-a's crumble hook only after rift-a merges (Lost Tower doesn't need it) |
| **trainers-gym** (5 h) | `res/trainers/data/` files for Gardenia, Maylene x2, Wake, Fantina; the trainer ability field (`src/trainer_data.c`, the trainer JSON schema/converter); Mega form abilities in `res/pokemon/` mega forms (Gengar Shadow Tag, Gyarados Mold Breaker, Lucario Adaptability) | Teams per `trainers.md`; abilities set (Chlorophyll, Swift Swim, Shadow Tag); Mega lines | Headless quick-battle (`src/debug_quick_battle.c` path) per leader: Mega triggers, ability shown; build | R0 |
| **trainers-story** (4 h) | Data files for every trainers-story id; route trainer levels on Routes 204-215 and 209 (only `res/trainers/data/` files of trainers placed on those maps) | Teams: Cyrus 1-3 (L 17/27/36 approx., one starter + 0/2/4 others), Garius (L 26/38), Indra (L 30: Honchkrow-led Dark team, three Pokemon), grunts (Gen 3/4 mixes per `route_pokemon.md`); curve fits Gym levels | Quick-battle each Cyrus/Garius variant; level table in report | R0 |
| **mons** (4 h) | `res/field/encounters/**` for Arc 2 maps; `res/field/scripts/scripts_unk_0404.s` (Route 206 test items) | Arc 2 Gen 3 adds per `route_pokemon.md` (Arc 2 table), levels on the new curve; remove the Key Stone/Mega Stone test pickups from Route 206 | Encounter dump per map; walk 200 steps on 3 routes; Route 206 items gone | R0 |
| **art-ph** (4 h) | PNGs/palettes behind the R0 gfx constants; `tools/arc2_sprites/**`; `docs/story/art/arc2/**` | Indra, Kahn overworld sprites (real design), Looker janitor/newspaper variants, Eclipse crate/frame/rift objects, Eclipse grunt + leader battle sprites (placeholder-quality OK) | Build; screenshot each sprite on a test map | R0 |

### Round 2: story scripts, P1 (parallel; R2a and R2b can overlap, no shared files)
Each owns the scripts, init scripts, events JSON and `res/text` bank of the maps listed, and removes stock content
that collides there (Galactic events, HM gives, overworld totem objects).

| WS | Owns (maps) | Scenes and deliverables | Depends |
|---|---|---|---|
| **R2a s-jubilife** (4 h) | `jubilife_city` (Arc 2 states only; leave Arc 1 states intact), `trainers_school` | Remove the Arc 1 "To be continued" gate at state 16 (`JubilifeCity_Text_Arc1ToBeContinued`); 2.1-2.3 with C7/C8 lines; Rowan gives the third ball ("I said this one would stay with me until I knew who it was meant for."); Cyrus battle 1; warp to the 2.4 cutaway | trainers-story |
| **R2a s-cutaways** (3 h) | violet room map (R0 picks), `route_222` (cutaway states only) | 2.4 (C1 text), 2.13, 2.19; each a self-contained scene entered by warp with a return point passed in `VAR_0x8004`-style temp vars; contract doc for callers | art-ph (Kahn/Indra sprites; placeholders fine) |
| **R2a s-route204** (5 h) | `route_204_south`, `route_204_north`, `ravaged_path` | 2.5 (tag battle, L0, ledger prompt from `arc2_common`), rift entrance object into `DW_RAVAGED_PATH`, delete overworld Hitmonlee totem object, 2.8 Resonator conversion (D10), Garius from the north (Pokétch line, S3) | resonator, rift-a, trainers-story |
| **R2a s-floaroma** (4 h) | `floaroma_town`, `floaroma_meadow`, `route_205_south/north`, `valley_windworks_outside/building`, `eterna_forest`, `eterna_forest_outside` | 2.9 cold site (worker "One of them got a call"), ledger L1; neutralise Mars/Windworks key/meadow grunts; Eterna Forest silence, rift entrance into `DW_ETERNA_FOREST`, delete overworld Vespiquen; 2.10 aftermath (locked power) | rift-a |
| **R2a s-eterna** (5 h) | `eterna_city`, `eterna_city_gym`, `eterna_city_pokecenter_1f`, `team_galactic_eterna_building_1f-4f` | Gym 2 hooks (Gardenia's lines), Resonator wakes; Garius battle 1; Cynthia's HM01 give removed; Haven (2.12): Looker janitor (recognises the player if `FLAG_UNK_0x091C`), kennels, manifests, double battle with Gardenia, Pip; warp to 2.13 | trainers-story, trainers-gym, art-ph |
| **R2a s-celestic** (5 h) | `route_211_west/east`, `mt_coronet_1f_north_room_1/2`, `mt_coronet_1f_tunnel_room`, `celestic_town`, `celestic_town_cave`, `route_210_north/south`, `solaceon_town` | 2.14; 2.15-2.16 (S1 text, Saros, G4, Rowan's question, Cyrus battle 2 with C5 line); Surf give from the elder removed; Route 210 fog off (weather via script/flag only; header edits go to the lead) and the Psyduck blockade cleared from the north side; 2.16a Solaceon wall signs + Indra cutaway | trainers-story |
| **R2b s-veilstone** (5 h) | `veilstone_city`, `veilstone_city_gym`, `veilstone_city_galactic_warehouse`, `veilstone_city_pokecenter_1f`, `route_215` | 2.17 Looker (trust Yes/No to bit 0; "No Pokétch number" line); 2.17a depot heist (crate-tail stealth pattern, `scripts_jubilife_city.s` crate code as reference) + Indra battle; 2.17b Key Stone trial staged at the stock meteorite garden + starter stones (`GivePokemon`-free item gives); 2.17c Route 215 night crate (bit 3); HM02 give removed | trainers-gym, trainers-story, art-ph |
| **R2b s-route214** (3 h) | `route_214`, `route_214_gate_to_veilstone_city`, `valor_lakefront` | 2.18 dawn grunts, ledger L2, rift entrance into `DW_ROUTE_214`, delete overworld Skarmory; warp to 2.19 after calm; Valor Lakefront plaque sign | rift-b, trainers-story |
| **R2b s-pastoria** (5 h) | `pastoria_city`, `pastoria_city_gym`, `pastoria_city_pokecenter_1f`, `lake_valor_drained`, `lake_valor` (header logic only via script) | Gym 4 hooks; Basin forced drained (D12), plaque "ELIAS, OF TWINLEAF TOWN", Garius at the fence + night question (bit 1); Looker briefing (2.21 start); 2.22 Rowan (C6 line); Great Marsh grunt plot neutralised | trainers-gym |
| **R2b s-raid** (5 h) | `route_213`, `route_213_gate_to_pastoria_city` | 2.21 night raid: two patrols, step budget, checkpoint reset, Psyduck saved, ledger L3; rift entrance into `DW_ROUTE_213`, delete overworld Lapras; 2.23 beach (Garius's list adapts to `VAR_ARC2_SUSPECT`), Cyrus battle 3 | rift-b, trainers-story |
| **R2b s-hearthome** (6 h) | `hearthome_city`, `hearthome_city_gym_*` (entrance + leader rooms), `hearthome_city_pokecenter_1f`, `route_209`, `route_209_lost_tower_1f/2f/5f`, `route_208_gate_to_hearthome_city`, `route_209_gate_to_hearthome_city` | Fantina vigil gate (Gym closed until the Fen Badge; Fantina at the tower base before that); Gym 5 hooks; Garius battle 2; 2.24 Saros at Mira's grave (5F); 2.25 rift entrance into `DW_LOST_TOWER`, the vein call (Rowan + Garius); 2.26 grunts, Rowan "...It wasn't him.", second DW entry, Spiritomb aftermath, Garius "Guess it wasn't him", END OF ARC 2 (state 99) | rift-b, trainers-gym, trainers-story |

**R2 end (lead, about 2 h):** merge order R0 → R1 (resonator, rift-a, rift-b, trainers-*, mons, art-ph) → R2a → R2b,
renaming flags in `vars_flags.txt` at each merge. One full headless run from `post_gym1.dsv` to state 99 (harness
chains the per-workstream scripts), plus a level check against the Gym table.

### Round 3: nice-to-haves (P2, parallel after R2 merges)

| WS | Owns | Deliverables | Depends |
|---|---|---|---|
| **set-lake** (6 h) | `dw_route_213` terrain/tools/narc member (from rift-b) | Phase 1 terrain: the hanging lake ceiling, lakebed debris, island; script unchanged | R2 merge |
| **set-tower** (6 h) | `dw_lost_tower` (from rift-b), ghost-act hook in `src/overlay009/ov9_02249960.c` | Ghost totem acts at seams (S7), Litwick candles; Phase 1 terrain if time allows | R2 merge |
| **echo** (4 h) | new `res/text/arc2_echo.json` + echo labels added to `ravaged_path`, `valley_windworks_building`, `route_214` scripts (ownership passes from the R2 owners) | S8 Echo scenes (ghost-palette replays) | R2 merge |
| **quests** (5 h) | `route_205_*`, `valley_windworks_*` (side states), `jubilife_city` (old-man reunion state), Pokemon Center TV text bank | Plusle/Minun reunion; Duchess reunion; Rowan TV retraction + Solaceon banner text (S10) | R2 merge |
| **gen5-arc2** (6 h) | `generated/species.txt` (append), `res/pokemon/<new>/**`, species `src/include` touches per a7a6b38db1 | 8 story lines (D9) complete; then mons places them | R2 merge |
| **world-art** (6 h) | map data/texture for `solaceon_town` (wall), Veilstone meteorite garden (Meteor Shrine), `route_212_north` (brass gate), Route 210 rift-mist weather | Visible-change items; Klink by the gate; Absol barometer (encounter swap keyed on the totem flag) if cheap | R2 merge |
| **art-final** (5 h) | art-ph's files + `res/graphics/item_icons/` (Resonator icon, its meson/order lines) | Final Indra/Kahn/grunt battle sprites; 5 ghost cut-ins designed (not tinted totem sprites); Resonator icon | R2 merge |

### Round 4: integration and review
Lead merges R3; full headless run; a critic pass on Arc 2 (same format as Arc 1's 6.5/10 review), with fixes routed
through the orchestrator; `docs/arc2/round_status.md` written as built.

---

## 4. Risks and open questions

| Risk | Impact | Mitigation |
|---|---|---|
| DW maps are the long pole (Arc 1's Phase 1 estimate: 7-11 days per map; Phase 0 was a clone with uniform wall art) | Five rifts in one night only work at Phase 0 | D8: Phase 0 for P1; the verbs (scars, ceiling, hops, choice) live in grids/scripts, not art. Phase 1 only for two set pieces in R3. |
| `tw_arc` unknown record fields (`unk_1A/1E/20`), hop vectors for ceilings and wall-to-wall | Hops look wrong or soft-lock | Copy stock B2F/B4F records and change only bounds/offsets (revision plan section 6.1); every rift workstream records a fall/reset test |
| Gating in the new order: Route 209 reaches Hearthome and the Lost Tower right after Solaceon; Fly (Skarmory, Gym 3) opens visited towns early; Route 210 Psyduck from the north; Surf (Gym 4) before Defog (Gym 5); whether the Route 211 Coronet tunnel needs Rock Smash | Sequence breaks | D13 gate covers Hearthome; s-hearthome blocks the Lost Tower rift below state 90; s-celestic clears Route 210; lead checks Route 211 in R0 and reports |
| Lake Valor drained state (D12) is set by stock logic tied to Galactic's bomb, and the Town Map still draws the lake | Basin shows full water, or the Town Map lies | s-pastoria finds the stock switch first and reports; Town Map art is P2 (round 3 open item) |
| Ledger fairness: if Garius picks get any unique reaction, careful players get the twist early; if Cyrus picks get extra drama, it tips the game's hand | Mystery weakened | Neutral reactions only (S2); the orchestrator reviews the 4 prompts' reaction text before merge |
| The call clue (S3) proves Cyrus innocent of L1 to a sharp player | Breaks "every leak explainable by either" | Keep the worker vague ("One of them got a call"); Cyrus was at the fence and could have spoken in person. No character connects it. |
| Skarmory/Spiritomb totem level changes touch `src/totem_battle.c`, which no workstream owns | Unowned edit | Lead applies D14 in R0 |
| Cutaway warps return to the wrong map state | Stuck after a cutaway | `s-cutaways` publishes a return contract (map, x, z, dir, next state) and tests each caller's handoff from a set state |
| Overnight parallelism: 7 R1 + 11 R2 workstreams | Merge conflicts, build-dir locks | Separate worktrees (separate `build/`); all shared registrations done in R0; R2a/R2b can be serialised if agent slots are short |
| Arc 3 drafts still assume Eclipse hunts Giratina (C11) | Arc 2 plants pay off into wrong scenes | Arc 3 rewrite pass before Arc 3 implementation; the C11 fixes are listed |

**Open questions (not blocking; defaults in brackets):**
- Does Garius's Arc 2 team already carry anything from Eclipse (a shard-scarred Pokemon as a clue)? [No: too strong.]
- Should Cyrus fight beside the player against Spiritomb (a totem tag battle needs engine work: P2 is inactive in totem battles)? [No: he kneels beside it; P2 if the engine allows.]
- Maylene's trial uses Maylene's Gym team or a trial team? [Separate trial id with Mega Lucario only, L31.]

---

## 5. Execution notes (orchestrator, 2026-10-10 night)

The owner asked for Arc 2 to be built overnight with no approval step. All decisions above are taken as written. Changes
to the process above:

- **Integration branch `arc2`** (from `main` @ 6dcc03be85). Every workstream branches from `arc2` after R0 merges, and the
  lead merges back into `arc2`. `main` is not touched overnight; `arc2` is pushed.
- **R0 creates stubs for everything shared**, so R1 and R2 run in parallel instead of in sequence: the 5 DW map headers
  with stub scripts, events and text that build and warp; placeholder trainer data for every registered Arc 2 trainer id
  (one Lv-appropriate Pokemon each); the placeholder gfx constants; `ITEM_RESONATOR`; the `arc2_common` bank. Story
  workstreams code against these contracts and keep working while R1 fills them in.
- **Story calls overnight:** `docs/arc2/screenplay_v2.md` is the text. If a workstream needs a line or beat it doesn't
  cover, it makes the call itself, consistent with `bible.md` and this plan, and lists it under "Decided by the agent"
  in its report. Nobody blocks on the orchestrator for story.
- **Order:** R0 (registry + screenplay_v2, in parallel) → R1 and R2a together → R2b as slots free up → lead integration
  and a full headless playthrough from the post-Gym 1 save to END OF ARC 2 → R3 if time remains.
- `mons` and `trainers-gym` start immediately alongside R0 (they don't touch R0's shared files).
