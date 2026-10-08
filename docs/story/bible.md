# Dazzling Platinum story bible

Source of truth for story facts. Built from the "Dazzling Platinum PRD" Google Doc plus the owner's answers.
Anything marked **OPEN** isn't decided yet. Anything marked **PROPOSED** is Claude's suggestion, waiting for
the owner to approve it.

Companion doc: `secrets.md` (who knows what, and when).

## Premise

A parallel Sinnoh. It looks like the Sinnoh the player knows from Platinum, but its history went differently.
Team Eclipse, a new organization, promises to bring back the dead. To do it, its three leaders each try to
control one of the creation trio: Dialga (time), Palkia (space), and Giratina (the world of the dead).

At the start, Giratina throws the Cyrus from mainline Platinum out of the Distortion World and into this
world. He's the only person here who remembers the other Sinnoh, apart from the player.

## World rules

- **Team Galactic never existed here.** Nobody in this world knows Cyrus's face or what he did. Only the
  player does.
- **Map:** about 40% of the map changes (see `map_changes.md`).
- **Totems, rifts and field powers. There are no HMs.** Nothing is ever taught to your Pokemon. Each totem
  site has a portal into the Distortion World: step through, solve a puzzle (Cyrus guides), defeat the totem to
  calm it, and the rift closes. With that region's Gym badge **and** its totem calmed, the player can channel
  the totem's energy to clear one kind of field obstacle.

  | Gym | Totem | Site | Field power |
  |---|---|---|---|
  | 1 Oreburgh (Roark) | Hitmonlee | Ravaged Path, Route 204 | Smash rocks (Rock Smash) |
  | 2 Eterna (Gardenia) | Vespiquen | Eterna Forest | Cut trees (Cut) |
  | 3 Veilstone (Maylene) | Skarmory | Route 214 | Fly |
  | 4 Pastoria (Crasher Wake) | Lapras | Route 213, beside the dry Valor Basin | Surf |
  | 5 Hearthome (Fantina) | Spiritomb | Lost Tower, Route 209 | Clear fog (Defog) |
  | 6 Canalave (Byron) | Aggron | Iron Island | Push boulders (Strength) |
  | 7 Snowpoint (Candice) | Mamoswine | Acuity Lakefront | Climb cliffs (Rock Climb) |
  | 8 Sunyshore (Volkner) | Kingdra | Route 223 | Climb waterfalls (Waterfall) |

  Calmed totems go home. They can be caught in the postgame.

  **Story reason (approved):**
  - Calming a totem cleanses its shard: the pain drains out, it turns clear, and only the strength is left,
    given freely. A **Calm Shard**.
  - **Ruth builds the Resonator** after the first totem (early Arc 2) to hold Calm Shards. Using it on an
    obstacle: "Hitmonlee's energy surges through the Resonator!", and a ghostly Hitmonlee clears it.
  - The badge is the region vouching for the player: a calmed totem only answers a trainer its Gym Leader has
    vouched for. Gym Leaders are the wardens who notice the rifts and send the player (Roark sets this up at
    the end of Act 1).
  - Theme: Eclipse rips shard power out through pain; Darren is lent it freely. A Calm Shard is what turns
    Rowan. Cyrus, seeing one: "I took. You were given."
  - Every calmed totem closes a torture site and costs Eclipse shards, which is why the first Distortion World
    shard deposit matters so much to them.

  **OPEN (design and code):** eight Distortion World puzzle maps (the Act 1 wall-walk is the template). Replace
  the HM items and field-move menu with the Resonator, gated on the badge plus `FLAG_TOTEM_*_DEFEATED`. Surf now
  comes before Defog (reverse of stock), so map gating needs a check.
- **Two lakes have ancient palaces.** The Lake Verity castle was built long ago and dedicated to Palkia. Act 1
  happens there, and later Palkia is captured there. Lake Valor moves to southwest of Hearthome City
  (entrance in the top-left corner of Route 212) and has a clockwork palace (brass, gears, a giant clock)
  built in ancient times for Dialga.
- **The old Lake Valor site is the Valor Basin (PROPOSED):** a dry lakebed beside Valor Lakefront. Locals say
  it drained years ago in a research accident. It was really Eclipse's first torture experiment: the portal
  it tore open swallowed the lake into the Distortion World and killed Garius's father, who had come to stop it. He fought Eclipse and was against all of their work. Valor Lakefront has a memorial plaque listing the researchers who died, his father
  among them.
- **Umbral Palace (NEEDS DESIGN):** Giratina's home deep under Mt. Coronet, past the molten depths, where the
  Distortion World portal is. The third ancient palace: Verity (Palkia), Valor (Dialga), Umbral (Giratina).
- **Shards** (also called crystals; same thing). Eclipse tortures Pokemon at hidden sites all over Sinnoh.
  Holding a Pokemon near the brink of death for a long time tears a portal into the Distortion World, and
  shards form on the other side. Shards let Eclipse control the legendaries, and they're how Eclipse finds
  where Giratina can be summoned.
- **The first Distortion World shard deposit:** late in Arc 2, Darren finds one while searching for Cyrus. It
  reaches Eclipse through Garius, and Eclipse starts harvesting the Distortion World, which powers the Arc 3
  captures. The player's own discovery fuels the villains' endgame.
- **The totem Pokemon are the tortured Pokemon themselves (PROPOSED wording).** When a portal tears open, the
  Pokemon is pulled through, and shard energy swells it into a huge, enraged totem guarding the shards. Beating a totem in the Distortion World drains the shard energy and frees it. Arc 1 ends with
  Rowan studying the Eclipse Shard Cyrus gave the player and explaining that totems exist and must be beaten
  in the Distortion World; nobody knows yet where shards come from. At first totems look like native
  guardians. The
  Act 1 Mawile is the first one: it's agitated because a shard is stuck in it.
- The Distortion World has gravity-seam puzzles: walking on walls along seams (see `docs/arc1/revision/`).

## Cast

### Darren (protagonist)
A new character, not Lucas. The player can pick a girl or a boy and names them; "Darren" is the
screenplay name. No in-game line should assume the player's gender.

### Garius (rival)
- His **father is dead**. It's never said outright at first. The hints escalate (see `secrets.md`, track G).
- **His father fought Team Eclipse** and was against all of their work. He died at the Valor Basin trying to
  stop their first experiment. Darren and Cyrus learn this from Indra after Gym 8. Garius has spent the game
  helping the people his father died fighting.
- Admires Team Eclipse from his very first line ("Man, that Team Eclipse really is something").
- Brushes off the warning from Cynthia's grandma in Celestic Town.
- **Drifts in the open, spies in secret.** On the surface, Darren and the player watch him slip (arguments,
  clashing goals). In secret, he feeds Team Eclipse the group's plans. When Cyrus confesses in Jubilife, his
  anger is genuine and he demands Cyrus leave. Soon after, Eclipse recruits him by promising to bring his father
  back, and he realizes everyone will blame Cyrus for the leaks. Because his anger at the confession was real,
  that scene stays fair in hindsight.
- **Reveals himself** at the start of Arc 3, once a leak happens while Cyrus is provably away and Cyrus is cleared:
  "Darren, let's not play any more games. It was me all along." He then helps Eclipse capture Dialga and
  Palkia.
- **Inherits Dialga and Palkia.** Saros and Kahn capture them. Right after the player catches Giratina, the
  shards burn the two of them out, and Garius takes both, sure he's strong enough to avoid the same fate. The
  player stops him on Route 223 after Gym 8, before Victory Road, as the last remaining member of Team
  Eclipse.
- **Final battle:** the player, with Giratina, against Garius, with Dialga and Palkia.
- **Why the player faces him:** after Gym 8, Indra finds Darren and Cyrus. She warns them Garius is about to
  use Dialga and Palkia to bring his father back, and tells them the truth about his father. She's the leader
  who let go of her brother, warning about the one who won't let go of his father.
- **Redeemed.** On Route 223, Cyrus tells Garius the truth. Garius doesn't believe it for a second and battles
  anyway. Only after he's defeated does he realize that what he's doing is everything his father stood
  against.

### Cyrus (from mainline Platinum)
- **A good guy in this story.**
- **Arc 2, Jubilife City: confesses.** Right after Gym 1, passing back through Jubilife, he gathers Darren, Rowan
  and Garius, has everyone sit down, and tells them he led an evil organization in his world. Rowan defends
  him; Garius demands he leave.
- **A second rival.** After the confession, Rowan gives him the third starter: "This can be a new start for
  you." (PROPOSED: he came through the rift with no Pokemon.) His starter beats Garius's and loses to yours.
- **Battles throughout (schedule PROPOSED):** (1) Jubilife, right after he gets his starter; (2) Celestic,
  after grandma's legend; (3) late Arc 2, the confrontation at the peak of suspicion ("Words prove nothing.
  Judge me the way trainers do."); (4) Arc 3 after he's cleared, before Gym 7; (5) before the Umbral Palace.
- **The search:** after battle 3 he goes into the Distortion World alone. Darren searches for him and finds the
  first shard deposit instead, reports it to Rowan and Garius while Cyrus is still missing, and Eclipse learns
  about it anyway. That's the leak that clears him.
- **Red herring for the leak.** From Arc 2 on, Team Eclipse keeps learning the group's plans before they act.
  Everyone suspects Cyrus, and so does the player; even Rowan's trust wears thin, until the battle and the leak
  that clears him at the end of Arc 2.
- Thrown out of the Distortion World by Giratina. Lands on the castle at Lake Verity.
- Guides the kids through the Distortion World puzzles and helps them fight the totems.
- Sees Lucas in Darren and Garius ("You remind me of somebody I knew before").
- In Platinum he tortured the lake trio with the Red Chain. Eclipse's shard method mirrors exactly what he did.
- He is living proof that someone can come back out of Giratina's world. Eclipse doesn't know this at first.
- Recognizes himself in Garius: someone so sure a loss can be fixed by force that he'll do anything. **He's the
  one who reaches Garius at the end.**
- **OPEN:** whether he faces Giratina, the creature that threw him out, when the player catches it.

### Why Giratina sent Cyrus here

Cyrus asks in Act 1: "Did the shadow cast me out?" The late answer: no, **it sent him.**

- **Why this world:** it's the world where Giratina is about to be hunted.
- **Why Cyrus:** he can read the Distortion World's seams after years inside it, and he knows exactly how a
  legendary gets chained, because he once did it.
- **What for:** to guide a trainer to Giratina before Eclipse. Being caught by someone who won't use it is
  how Giratina protects itself.
- **How it finds Giratina:** Cyrus's sense for the seams is the compass in the Coronet race. Indra forces her
  way with shards (torture); the player is guided by the man Giratina sent (consent). That's why the player
  wins.
- **Plants:** Cyrus guiding the Distortion World puzzles from Act 1; a shadow watching at the edge of totem
  fights (only the player notices); Cynthia's grandma's legend that the renegade sends a guide back from its
  world when the creation trio is threatened.
- **Payoff:** at the capture, Cyrus faces the creature that threw him out and understands why.

### Professor Rowan
- Publicly calls Eclipse con artists: bringing back the dead is too good to be true.
- **Turning point:** learns that Cyrus came out of the Distortion World alive, and starts to believe it's
  possible.
- Then learns the way there is torturing Pokemon (the totems / shard victims) and rejects it. Looker's evidence
  in Pastoria is what shows him: "I was starting to believe it could be done. Not like this."

### Looker (International Police)
- Investigating Team Eclipse. He's the one who proves to the characters that Eclipse tortures Pokemon, and that
  the torture is why rifts open and totems appear.
- **Arc 1 cameo:** a man in a trench coat at the Jubilife rally, scribbling notes.
- **Arc 2, the Eclipse Haven (Eterna, after Gym 2):** the old Galactic building is a shelter where Eclipse takes
  in Pokemon whose trainers have died. Gardenia brought Pokemon there, but none were ever adopted. Looker is
  undercover as the janitor. Shipping manifests send crates to the rift sites: "Pokemon go in. Crates go out.
  And wherever the crates go, a rift tears open." Double battle: Darren and Gardenia against the Haven's staff.
- **Arc 2, Veilstone:** no record of Cyrus anywhere. "This man does not exist." The player knows why.
- **Arc 2, Pastoria (the proof):** a live Eclipse site on Route 213; they save the Pokemon in the frame, but the
  Lapras already pulled through is a totem. His evidence is Rowan's rejection beat.

### Ruth (Rowan's assistant)
A new character with a new sprite (not Dawn or Lucas). Runs the portal readings at the castle in Act 1. In the
ROM this replaces the stock counterpart, so `BufferCounterpartName` lines need the fixed name "Ruth".

### Garius's mom
Gives optional dialogue hinting at the father's death (Act 1 onward).

### Cynthia's grandma (Celestic Town)
After Gym 2, in Arc 2: the player crosses Mt. Coronet from Eterna to reach Celestic. The stock relic scene
is replaced: she warns about trying to control legendaries for personal reasons, and tells the legend that the
renegade sends a guide back from its world when the creation trio is threatened. Garius, still hiding that he's
the informant, brushes it off a little too hard, alongside an Eclipse leader. After the reveal, the two of them
agreeing reads as a clue.

### Team Eclipse leaders

**The three are equals:**
an uneasy alliance with no single boss.

| Name | Loss | Legendary | Logic |
|---|---|---|---|
| **Saros** (an eclipse cycle; history repeating) | his daughter | Dialga | Rewind time to before she died. |
| **Kahn** | his partner Pokemon | Palkia | Reach a parallel world where it still lives. |
| **Indra** (woman) | her brother | Giratina | Pull him back out of the world of the dead. |

- Each leader gets one scene the player sees and Darren doesn't, showing their loss, so the player understands
  them before Darren does.
- Saros and Kahn are burned out by the shards after capturing their legendaries.
- **Indra's ending:** after the player beats her, Giratina shows her brother for a few seconds in a
  cutscene. He tells her to move on. She cries, accepts it, and lets the player catch Giratina.
- **OPEN:** which leader is in the room at Cynthia's grandma's warning.

## Story spine (3 arcs, then the League)

Gym order (changed from stock): 1 Oreburgh, 2 Eterna, 3 Veilstone, 4 Pastoria, 5 Hearthome, 6 Canalave,
7 Snowpoint, 8 Sunyshore.

1. **Arc 1, buildup (start to Gym 1).** The drop-in at Lake Verity (written, built on `arc1-dropin-scene`),
   then on to Oreburgh. Ends with Rowan studying the Eclipse Shard and explaining the totems.
   Draft of the scenes from Twinleaf to Gym 1: `arc1_part2_screenplay.md`.
2. **Arc 2 (Gyms 2 to 5).** Opens in **Jubilife** right after Gym 1 with Cyrus's confession. Gym 2 Eterna; through Mt. Coronet (first look at the sealed-off heat below, which
   Cyrus can feel) to **Celestic Town** for grandma's warning; Gym 3 Veilstone; Gym 4 Pastoria; Gym 5
   Hearthome (passing the Valor Basin near Pastoria). Eclipse recruits Garius after the confession. **Cyrus confesses**; Rowan defends him; Garius demands he
   leave. Leaks escalate, and suspicion falls on Cyrus. Rowan gives Cyrus the third starter; Cyrus becomes a second rival.
   Totem fights with Cyrus (the first: Hitmonlee at Ravaged Path, Route 204). Late in the arc the player confronts and battles
   Cyrus; he leaves for the Distortion World alone. Searching for him, Darren finds the first shard deposit;
   Eclipse learns of it while Cyrus is still missing, which clears him.
3. **Arc 3 (Gym 6 to the League).**
   - Opens with the reveal: "Darren, let's not play any more games. It was me all along."
   - **Dialga falls** at the Lake Valor clockwork palace: right after Gym 5, the chase runs from Hearthome onto
     Route 212 and through the entrance in its top-left corner.
   - **Gym 6** (Canalave), then the chase across the new fairy route (Route 218) to Lake Verity: **Palkia
     falls** at the castle.
   - **Gym 7,** while Eclipse uses the shards to find where Giratina can be summoned.
   - **The race for Giratina** through the molten depths of Mt. Coronet to the **Umbral Palace**, guided by
     Cyrus. Indra's closure. The player **catches Giratina**. The shards burn out
     Saros and Kahn; Garius takes Dialga and Palkia.
   - **Gym 8.**
   - **Indra finds Darren and Cyrus:** Garius is about to use Dialga and Palkia to bring his father back, and
     his father fought Team Eclipse and was against all of this work.
   - **Stop Garius on a redesigned Route 223 (after Gym 8, before Victory Road):** he's the last remaining
     member of Team Eclipse. PROPOSED: calming the Kingdra totem on Route 223 gives the power to climb the
     waterfall at the end of the route, and Garius waits at the top, at the entrance to Victory Road,
     mid-ritual. Cyrus tells him the truth about his father; he doesn't believe it and battles anyway.
     Giratina vs. Dialga and Palkia. After losing, he realizes he's betrayed everything his father stood for.
   - **The Elite Four and the Champion.** The main game ends.

## Open questions (top priority first)

1. Names: Garius's father, Saros's daughter, and Kahn's partner Pokemon (species, and how it died).
2. Arc 2 is fully drafted (parts 1 to 3). Next: Arc 3.
