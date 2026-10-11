# Arc 2 screenplay, version 2 (the build text)

This is the text every Arc 2 story workstream implements **verbatim**. It replaces `docs/story/arc2_part{1,2,3}_screenplay.md`
for the build. Sources: those drafts, with the fixes C1-C10 and the P1 suggestion lines (S1, S2, S3, S4, S5, S9, S10
private lines, S11 P1 rows) from `docs/arc2/PLAN.md`. Scene ids are the plan's; new scenes have letters.

Darren (the player, girl or boy) is silent apart from menu choices. No line assumes the player's gender.

## How to read this file

**Dialogue blocks** are the ```` ```text ```` fences. Inside one:

- Each line is one line of the 27-tile text box (max 197 px; `/tmp/a2/r0-script/lint_screenplay.py` checks every line).
- Consecutive lines are one box (at most 2 lines). A line `--` is a box break inside the same message (`\r`).
- A blank line starts a new message (a new `res/text` entry). Each message starts with its speaker, `Name: `, as in Arc 1.
- Inside a box, join line 1 and line 2 with `\n`; end each box but the last with `\r`.
- `{PLAYER}` is the player's name: `{STRVAR_1 3, 0, 0}` (call `BufferPlayerName 0` first).
- Lines in `[brackets]` are directives, not text: `[YESNO]`, `[MENU: a | b]`, branch labels.
- Messages with no speaker are narration or signs (same as Arc 1: item gets, sign text).

**Scene headers** give the owner (plan section 3, R2 table), the maps, the `VAR_ARC2_PROGRESS` value(s) the scene
**reads** (its trigger) and **sets**. Owners use only their own block. A cutaway is entered by warp and returns the
player to the point the caller passes (s-cutaways publishes the contract).

**Stage directions** (italic bullets) say what happens on screen in stock-script terms: `ApplyMovement`, `FadeScreen`,
`PlayFanfare`, emotes (`!`, `...`), object show/hide. Exact tiles are the owner's call.

**Choices** use stock commands: `ShowYesNo` (Yes/No), `InitGlobalTextMenu`/`AddMenuEntryImm`/`ShowMenu` (the 4-way ledger).
B on the ledger menu counts as **Bad luck**.

## Garius's whereabouts (must hold; S3)

Every leak must be explainable by either Cyrus or Garius. Scripters keep these facts true, on screen and off.

| Leak | Garius | Cyrus |
|---|---|---|
| L0 Ravaged Path (2.5) | Heard the plan at the school (2.2), stormed out, "cooled off in the flower fields" to the north; walks in from Floaroma's direction in 2.8 | Present; just confessed; the grunts know him |
| L1 Windworks (2.9) | Heard Ruth's plan in Floaroma; left for Eterna Forest that night | Scouted the Windworks road alone that night; was at the fence |
| (none) Haven (2.12) | Got his badge, battled the player, left Eterna for Celestic before Gardenia's request | Waited outside the Haven |
| L1b Celestic (2.15) | Knew Rowan's Celestic meeting (Rowan phoned everyone; Garius says so in 2.11) | Present; the stories are about people like him |
| L2 Route 214 (2.18) | At the Veilstone Pokemon Center when the dawn plan was made (2.17d), then "passing through" | At the Center all night |
| L3 Route 213 (2.21) | At Looker's briefing (2.21a); then watched the Route 213 gate during the raid | At the briefing; waited at the cave mouth |
| L-clear Lost Tower (2.25-2.26) | At Rowan's lab when the player phones the vein in | In the Distortion World, out of reach |

**The call (fair clue):** L1's worker says "one of them got a call". Looker (2.17) says Cyrus has "no Poketch number".
Garius checks his Poketch in 2.8 ("Nine missed calls. ...My mom."). Nobody connects these. Do not add a line that does.

## VAR_ARC2_PROGRESS by scene

| Scene | Owner | Reads | Sets |
|---|---|---|---|
| 2.1 Jubilife plaza | s-jubilife | ARC1 = 16, ARC2 = 0 | 1 |
| 2.2 Trainers' School | s-jubilife | 1 | 3 |
| 2.3 Cyrus battle 1 | s-jubilife | 3 | 5, then warp to 2.4 |
| 2.4 cutaway (Kahn, Indra) | s-cutaways | 5 | 9, return to Jubilife |
| 2.5 Ravaged Path, L0 | s-route204 | 9 | 10 (met at the entrance), 12 (tag battle won), 13 (L0 asked; rift opens) |
| 2.6-2.7 DW Ravaged Path, Hitmonlee | rift-a (s-route204 sets 14 on entry) | 14 | 15 on calm, exit warp |
| 2.8 Resonator, Garius back | s-route204 | 15 | 16 (night), 17 (Resonator given), 18 (rock), 19 (Garius gone) |
| 2.9 Floaroma, Windworks, L1 | s-floaroma | 19 | 20 (evening), 21 (Windworks morning), 22 (L1 asked) |
| 2.10 Eterna Forest | s-floaroma (outside), rift-a (DW) | 22 | 23 (rift seen), 24 (entered), 26 (Vespiquen calm, rift-a), 29 (aftermath done) |
| 2.11 Gym 2, Garius battle 1 | s-eterna | 29 | 31 (Forest Badge), 32 (Garius battle) |
| 2.12 Eclipse Haven | s-eterna | 32 | 33 (Gardenia asks), 34 (inside), 35 (Haven shut), then warp to 2.13 |
| 2.13 cutaway (Saros, Kahn) | s-cutaways | 35 | 39, return to Eterna |
| 2.14 Mt. Coronet | s-celestic | 39 | 40 |
| 2.15 Celestic shrine | s-celestic | 40 | 42 |
| 2.16 Rowan's question, Cyrus battle 2 | s-celestic | 42 | 44 |
| 2.16a Solaceon cutaway (Indra) | s-celestic | 44 | 47 at start, 49 at end |
| 2.17 Gym 3, Looker | s-veilstone | 49 | 51 |
| 2.17a depot heist, Indra | s-veilstone | 51 | 52 (inside), 54 (done) |
| 2.17b Meteor Shrine, Key Stone | s-veilstone | 54 | 57 |
| 2.17c Route 215 crate (optional, night) | s-veilstone | 49-59 | `VAR_ARC2_CHOICES` bit 3 |
| 2.17d Veilstone Center: the dawn plan | s-veilstone | 57 | 59 |
| 2.18 Route 214, L2 | s-route214 (outside), rift-b (DW) | 59 | 60 (grunts met), 61 (L2 asked), 62 (entered), 63 (Skarmory calm, rift-b), then warp to 2.19 |
| 2.19 cutaway (Kahn) | s-cutaways | 63 | 69, return to Route 214 |
| 2.20 Gym 4, the Basin | s-pastoria | 69 | 71 (Fen Badge), 72 (Looker's request), 73 (Basin done) |
| 2.21a Looker's briefing | s-pastoria | 73 | 75 |
| 2.21 Route 213 raid, L3 | s-raid (outside), rift-b (DW) | 75 | 80 (raid on), 82 (Psyduck saved, L3 asked), 83 (entered), 84 (Lapras calm, rift-b) |
| 2.22 Rowan sees the proof | s-pastoria | 84 | 86 |
| 2.23 beach, Cyrus battle 3 | s-raid | 86 | 88 (battle), 89 (Cyrus gone) |
| 2.24 Gym 5, Garius battle 2, Saros | s-hearthome | 89 | 91 (Relic Badge), 92 (Garius battle) |
| 2.25 Lost Tower alone, the call | s-hearthome (outside), rift-b (DW) | 92 | 93 (call made) |
| 2.26 grunts, Spiritomb, the end | s-hearthome, rift-b | 93 | 94 (grunts beaten), 95 (Spiritomb calm, rift-b), 99 END |

Fantina's vigil (2.24, before the Fen Badge) keys on the badge, not on progress.

## The suspect ledger (S2)

Four times, after a leak, someone asks who told Eclipse. The pick is stored in `VAR_ARC2_SUSPECT` and changes no scene
in Arc 2 except Garius's opening line in 2.23. **Every reaction is neutral**: one box, the same shape (the speaker weighs
the pick and does not settle it). No pick gets music, an emote or an extra line the others don't.

**Menu (shared, `arc2_common`):** `Cyrus` / `Garius` / `Ruth` / `Bad luck`. B = Bad luck. Menu labels are menu entries,
not text-box lines.

**Writing the pick** (no bit ops in stock scripts, so add constants; each prompt runs once, gated by progress):

| Leak | Cyrus | Garius | Ruth | Bad luck | "answered" (add as well) |
|---|---|---|---|---|---|
| L0 (2.5) | +0 | +1 | +2 | +3 | +256 |
| L1 (2.9) | +0 | +4 | +8 | +12 | +512 |
| L2 (2.18) | +0 | +16 | +32 | +48 | +1024 |
| L3 (2.21) | +0 | +64 | +128 | +192 | +2048 |

**Reading it (2.23, s-raid):** copy to a temp var, strip the answered bits (subtract 2048, 1024, 512, 256 each when
`GoToIfGe`), then peel digits from the top: if >= 192 the L3 pick is Bad luck, subtract 192; else if >= 128 Ruth, subtract
128; else if >= 64 Garius, subtract 64; else Cyrus. Repeat with 48/32/16 (L2), 12/8/4 (L1), 3/2/1 (L0). Use `VAR_0x8008` as the temp copy and count picks into
`VAR_0x8004` (Cyrus), `VAR_0x8005` (Garius), `VAR_0x8006` (Ruth), `VAR_0x8007` (Bad luck). Only `CompareVar`, `SubVar`,
`AddVar` and `GoToIf*` are needed.

The common prompt line (`arc2_common`), used at L0, L1 and L2 (L3 has Looker's own):

```text
Ruth: So who told them?
Who could have?
```

## Rift contract (rift and story workstreams both code to this)

The lead fills the exact coordinates in R0's registry commit. The flow is fixed here.

| DW map | Overworld rift object (owner) | Opens at | Entry sets | Calm sets | Exit warp |
|---|---|---|---|---|---|
| `DW_RAVAGED_PATH` | Ravaged Path, by the back wall, beside the frame (s-route204) | 13 | 14 | 15 | Ravaged Path, in front of the closed rift, facing down |
| `DW_ETERNA_FOREST` | Eterna Forest, off the main path between two trees (s-floaroma) | 23 | 24 | 26 | Eterna Forest, in front of the rift spot |
| `DW_ROUTE_214` | Route 214, at the grunts' machine (s-route214) | 61 | 62 | 63 | Route 214 rift spot; caller then warps to 2.19 |
| `DW_ROUTE_213` | Route 213 cave, the torn Lapras frame (s-raid) | 82 | 83 | 84 | Route 213 cave, in front of the frames |
| `DW_LOST_TOWER` | Lost Tower 2F (s-hearthome) | 92 (shadow wall opens at 94) | (no change) | 95 | First visit (92-93): back to Lost Tower 2F by the rift, progress unchanged, `FLAG_ARC2_VEIN_SEEN` set. Second visit (94): Route 209, outside the Lost Tower door |

Calming any totem: `{PLAYER} got a Calm Shard!` (with the stock item-get fanfare), then the totem's own lines below.

```text
{PLAYER} got a Calm Shard!
```

---

# Part 1: Jubilife to the Resonator

## 2.1 Jubilife City: finding Cyrus

Owner **s-jubilife** | `jubilife_city` | reads ARC1 = 16 and ARC2 = 0 | sets **1**

- *Remove the Arc 1 "To be continued" gate. On entering Jubilife at this state, Garius walks in beside the player.*
- *The plaza is empty. The big screen is dark (stock TV object off). Cyrus stands in front of it, back to the camera.*
- *Garius points (emote `!`).*

```text
Garius: There he is.
Spacesuit guy.

Cyrus: ...Rowan sent you.

Garius: He says you're our guide
now. Lucky us.

Cyrus: The rift opened again.
North of here. I felt it.
--
Bring Rowan to the Trainers'
School tonight. Everyone.
--
You should all hear what I am
before I take another step.
```

- *Cyrus walks off toward the Trainers' School. `FadeScreen` out; warp into `trainers_school` (evening). 2.2 runs on map load.*

## 2.2 Trainers' School, after hours: the confession

Owner **s-jubilife** | `trainers_school` | reads **1** | sets **3**

- *Evening. Rowan, Ruth and Garius sit at the students' desks; the player is placed at a desk too. Cyrus stands at the front, where the teacher would.*

```text
Rowan: Ruth's readings put the
Oreburgh rift on Route 204 now.
--
Inside Ravaged Path. I'd like you
to guide these two through it.

Ruth: The totem's in there too.
The readings are... loud.

Cyrus: I will. But not as a
stranger.

Cyrus: My name is Cyrus.
--
In the world I came from, I led
an organization. Team Galactic.

Cyrus: I believed spirit was a flaw.
--
Grief. Anger. Hope. I thought they
were why the world was broken.
--
So I set out to make a new world.
One without them.

Cyrus: To do it, I chained the
guardians of the lakes.
--
I tore at them until they gave me
the power to call Dialga and Palkia.

Ruth: ...The lake guardians?
Uxie, Mesprit and Azelf?

Cyrus: A boy stopped me. A boy,
and a Champion.
--
Then something rose out of the
dark and stopped me.
--
Then it took me into its world.

Cyrus: I don't know how long I was
there.
--
Long enough to stop counting.
```

- *Rowan stands slowly (face Cyrus). This line pays off lab msg 82 ("...Nobody.").*

```text
Rowan: I told these two that nobody
comes back from that place.
--
...Nobody.
--
And here you stand.
```

- *Garius stands up so fast his desk scrapes (SE_ bump sound; Garius jumps in place). Emote `!` over Ruth.*

```text
Garius: You're kidding me.
You CHAINED UP Pokemon?
--
Legendary Pokemon? And you want us
to follow you back in there?!

Garius: Some of us have actually
lost-
```

- *He stops. A beat (`WaitTime 30`).*

```text
Garius: ...Forget it.

Rowan: Sit down, Garius.

Garius: No! Professor, you heard
him!
--
He should go. Back wherever he
came from.

Cyrus: He's right to be angry.
I won't ask anyone to forgive me.

Rowan: I'm not asking you to ask.
```

- *Rowan sets his briefcase on the teacher's desk and opens it. One Poke Ball inside (show a Poke Ball object on the desk).*

```text
Rowan: I said this one would stay
with me.
--
Until I knew who it was meant for.

Rowan: It came out of that world in
this case. In a way, so did you.
--
This can be a new start for you.
```

- *Cyrus looks at the ball for a long moment (`WaitTime 45`), then takes it (hide the ball object). Cyrus gets the starter weak to the player's (the one that beats Garius's); trainers-story already builds his teams that way.*

```text
Cyrus: ...I have not held one of
these since I lost everything.

Garius: Unbelievable. Count me out.
--
I'm not following him anywhere.
```

- *Garius walks out the door (`ApplyMovement`, door sound, hide). Ruth steps after him one tile.*

```text
Ruth: Garius, wait-!

Rowan: Let him go. He'll cool off.

Rowan: We go to Ravaged Path in the
morning. Get some rest, all of you.
```

- *Garius heard the Ravaged Path plan before he left (L0). His anger is real: Eclipse hasn't recruited him yet.*
- *Cyrus walks outside. Set 3. 2.3 triggers when the player steps out of the school.*

## 2.3 Outside the Trainers' School: first battle with Cyrus

Owner **s-jubilife** | `jubilife_city` | reads **3** | sets **5**, then warps to 2.4

- *Cyrus waits by the school door, his new Poke Ball in hand. Rowan and Ruth stand nearby.*

```text
Cyrus: It has been a long time since
a Pokemon chose to stand with me.
--
Show me how it's done.
```

- *Battle: `CYRUS_ARC2_1_{starter}`. Losing doesn't end the game (`StartTrainerBattle` with the no-blackout path, as Arc 1's rival).*

```text
Cyrus: Hm. It listened to me.
I didn't expect that.

Cyrus: Ravaged Path is north, on
Route 204. I'll meet you there.

Rowan: Ruth will go with you and
watch the readings from outside.
--
Be careful. All of you.
```

- *Set 5. `FadeScreen`; warp to the violet room for 2.4 with the return point (Jubilife, outside the school, facing down).*

## 2.4 Cutaway: Team Eclipse

Owner **s-cutaways** | violet room (stock Galactic HQ room, lead picks) | reads **5** | sets **9**, returns to Jubilife

- *The player isn't in this scene (hide the player; camera on the table). A dark room lit violet. Kahn and Indra stand over a table. An Eclipse Shard pulses on it (shard object, palette flash).*

```text
Kahn: Word from our new friend.
--
The professor has a guide now.

Kahn: A man who walked out of the
Distortion World. Alive.

Indra: ...Out of it.

Kahn: He says something stopped
him. In his world.
--
Something older than all of us.

Indra: Something stopped a man who
held Dialga and Palkia.
--
Find out what.
--
Nothing stops this one.

Kahn: They go into Ravaged Path at
first light. That site is ours.

Indra: Then be there first.
```

- *Indra turns away from the table. `FadeScreen`; set 9; return to Jubilife.*
- *Never show who sent the message. The informant calls Cyrus "a man who walked out": Cyrus wouldn't describe himself that way. Cyrus never names Giratina.*

**Jubilife at 9 (s-jubilife):** Rowan and Ruth are gone (Ruth went ahead to Route 204). A Jubilife NPC line if the
player talks to the old school teacher outside the school:

```text
Odd. Someone was teaching in there
after hours. Nobody I knew.
```

## 2.5 Ravaged Path: Eclipse is waiting (leak L0)

Owner **s-route204** | `route_204_south`, `ravaged_path` | reads **9** | sets **10**, **12**, **13**

- *Ravaged Path entrance (inside the cave, first room). Ruth has her readings set up (Ruth object with a machine object). Cyrus is already there. Talking to either starts the scene. Set 10.*

```text
Ruth: The readings go wild past
that wall. Right where the rift is.
--
I'll stay here and watch. Shout if
anything... shouts back.

Cyrus: Stay close. Both of us.
```

- *The player and Cyrus walk to the back wall. Two Eclipse grunts stand beside a violet rift (rift object, inactive). The grunts turn (emote `!`).*

```text
Eclipse Grunt: Right on time.
Just like we were told.

Eclipse Grunt: So you're the one who
walked out. Huh.
--
Thought you'd be taller.
```

- *Tag battle: the player and Cyrus (`CYRUS_ARC2_1_*` as partner, `StartTagBattle`) against `ECLIPSE_GRUNT_ARC2_01` + `_02`. Set 12.*

```text
Eclipse Grunt: Doesn't matter.
--
This site's given us all it's
going to.
```

- *The grunts run out the north exit, toward Floaroma (`ApplyMovement`, hide).*
- *Bolted to the wall beside the rift: a cracked metal frame, scorched violet (`OBJ_EVENT_GFX_SHARD_FRAME`). Restraints hang from it, empty. Cyrus walks up to it and stops.*

```text
Cyrus: ...

Cyrus: I have seen a machine like
this before.
```

- *He doesn't say where. Ruth runs in from the entrance.*

```text
Ruth: How did they know we'd be
here? Only the five of us knew.

Cyrus: ...Yes.
I know how that looks.
```

- *Ledger L0: the common prompt, the menu, then one reaction. Then the closer.*

```text
[MENU: Cyrus | Garius | Ruth | Bad luck]

[Cyrus]
Ruth: Cyrus? He fought them right
beside you. Why help them first?

[Garius]
Ruth: Garius? He'd sooner eat his
badge than help a dark coat.

[Ruth]
Ruth: Me?! I took apart the
Professor's Poketch! That's IT!

[Bad luck]
Ruth: Bad luck? Maybe they've been
camped out here for weeks.

Ruth: ...Let's just keep our eyes
open. All of us.
```

- *Set 13. The rift object activates (violet pulse). Touching it: s-route204 sets 14 and warps into `DW_RAVAGED_PATH`.*

```text
Cyrus: Ruth stays with the
readings. We go through together.
```

## 2.6 Through the rift: scars

Owner **rift-a** | `DW_RAVAGED_PATH` | reads **14** | (no change)

- *Phase 0 clone. New verb: scar tiles, cracked wall tiles that crumble one step after you leave them. Falling resets to the last seam via the Arc 1 fall script. Cyrus is an NPC who walks ahead at fixed points.*
- *At the entry platform:*

```text
Cyrus: It's frightened. The whole
space is. Can you feel it shake?
```

- *At the first fork, the seam splits; one branch is scar tiles:*

```text
Cyrus: Follow the seam.
--
...Not that one.
That one is a scar.

Cyrus: A scar holds you once.
Then it remembers it was a wound.
```

- *First fall (once only):*

```text
Cyrus: Again. Slower. It doesn't
punish you for trying.
```

- *Halfway: a huge shadow passes far below the platforms (Giratina shadow fly-by from Arc 1), then is gone. Cyrus doesn't look down. No text.*

## 2.7 The Hitmonlee totem

Owner **rift-a** | `DW_RAVAGED_PATH` | reads **14** | sets **15**

- *The far platform. A Hitmonlee, far too big, violet aura, a shard lodged in its chest. It screams (cry, screen shake) when it sees them.*

```text
Cyrus: There. The shard is in its
chest. It's been fighting that
--
thing for days.
```

- *Totem battle: Hitmonlee (stock encounter: aura + ally summons). After: the aura drains, it shrinks (fade sprite), the shard falls and turns clear.*

```text
Cyrus: ...It's calm.
```

- *Hitmonlee nudges the clear shard toward the player, bows, and bounds off into the dark (hide).*

```text
{PLAYER} got a Calm Shard!

Cyrus: I took. You were given.

Cyrus: Come. The rift will close
behind us.
```

- *Set `FLAG_TOTEM_HITMONLEE_DEFEATED` (existing) and 15. Exit warp to Ravaged Path, in front of the closed rift.*

## 2.8 Route 204: the Resonator, and Garius comes back

Owner **s-route204** | `ravaged_path`, `route_204_north` | reads **15** | sets **16**, **17**, **18**, **19**

- *The rift object is gone. Ruth runs over from the entrance.*

```text
Ruth: The readings just dropped to
nothing! You did it!
--
...Wait. What is THAT?
```

- *The player holds up the Calm Shard (no item: a shard sprite above the player, or text only).*

```text
Ruth: It's clear. The Professor's
shard is violet. It pulses.
--
Like it hurts. This one's just...
warm.

Ruth: Give me one night. And give me
your Portal Reader. I have an idea.
```

- *`RemoveItem ITEM_PORTAL_READER 1`. `FadeScreen` to black; set 16. Fade in: morning, Route 204 north end (warp). Ruth and Cyrus are there. A cracked boulder blocks the path north.*

```text
Ruth: I call it the Resonator!
--
I built that Reader out of junk.
--
I think it was always meant to
be this.

Ruth: It holds your Calm Shard. And
it lets you borrow that Hitmonlee's
--
strength. Try it on that rock!
```

- *`AddItem ITEM_RESONATOR 1` with the key-item get message. Set 17.*

```text
{PLAYER} got the Resonator!
```

- *The player uses the Resonator on the boulder (the resonator workstream's field-move script: ghost Hitmonlee cut-in, "Hitmonlee's energy surges through the Resonator!", rock smashed). Set 18.*

```text
Ruth: It works!
--
Roark said that badge means
Oreburgh vouches for you.
--
I think the totem knew that.
```

- *Garius walks down from the north, from the direction of Floaroma. He is looking at his Poketch.*

```text
Garius: Nine missed calls.
--
...My mom.

Garius: Hey. I went to cool off in
the flower fields.
--
So. You beat the giant Hitmonlee?

Garius: Fine. Good. Whatever.
--
I'm heading to Eterna for my next
badge. Don't bring him.
```

- *Garius leaves north (hide). Cyrus speaks quietly (no emote).*

```text
Cyrus: He's not wrong to keep his
distance.

Ruth: I'll go ahead to Floaroma and
set up there. See you tonight!
```

- *Ruth and Cyrus leave north (hide). Set 19.*
- *Hindsight clue: the grunts fled north toward Floaroma, and Garius walks in from there soon after.*

---

# Part 2: Floaroma to Solaceon

## 2.9 Floaroma Town and Valley Windworks: the cold site (leak L1)

Owner **s-floaroma** | `floaroma_town`, `route_205_south`, `valley_windworks_outside`, `valley_windworks_building` |
reads **19** | sets **20**, **21**, **22**

- *Stock Galactic content here is neutralised: no Mars, no Windworks key, no meadow grunts.*
- *Floaroma, evening (scripted tint optional). Ruth checks her readings outside the Pokemon Center; Cyrus beside her. Garius is at the flower shop counter (Garius object by the shop). Entering town starts the scene.*

```text
Ruth: There's something at Valley
Windworks, east of here.
--
Faint. But it reads like Ravaged
Path did.
--
We'll check it first thing in the
morning.
```

- *Garius walks over from the shop, a jar of honey under his arm.*

```text
Garius: Whatever. I'm going through
the forest tonight.
```

- *Garius leaves north toward Eterna Forest (hide).*

```text
Cyrus: I'll scout the road to the
Windworks tonight.
--
I don't sleep much anymore.
```

- *Cyrus walks off east into the dark (hide). Ruth watches him go (face east, `WaitTime 30`).*

```text
Ruth: ...Get some sleep. I'll knock
when it's light.
```

- *`FadeScreen` to black; heal the party; set 20. Fade in: morning, at `valley_windworks_outside`. Ruth and Cyrus stand at the gate. Set 21.*
- *The building is empty. Bolt holes in the floor (floor sign events), drag marks, an empty cage, and a generator. Sign texts (the player reads them):*

```text
Four bolt holes in the floor.
The metal is scorched violet.

The generator is still warm.

Drag marks lead to the loading door.
Something heavy went out this way.

A small cage. The door is bent open.
--
A tag on it reads: PLUSLE, MINUN.
Only one Minun is left inside.
```

- *Talking to the cage: the Minun bolts out the loading door, east (a Minun object runs off; P2's quest picks it up).*

```text
Minun: Minu...!

The Minun ran out the loading door!
```

- *A Windworks worker (stock worker object) by the turbines.*

```text
Windworks Worker: Those folks in
the dark coats?
--
Cleared out about an hour ago.
--
One of them got a call, and they
packed up in a real hurry.

Ruth: ...A call.
```

- *Ruth looks at Cyrus (face him).*

```text
Cyrus: I saw lights here last night.
--
By the time I reached the fence,
they were loading trucks.
--
I came back to tell you.

Ruth: ...You could have woken us.
```

- *Ledger L1: the common prompt, the menu, one reaction, the closer.*

```text
[MENU: Cyrus | Garius | Ruth | Bad luck]

[Cyrus]
Ruth: Cyrus? He came back to tell us
about the trucks. Spies don't.

[Garius]
Ruth: Garius? He was halfway
through the forest by then. Maybe.

[Ruth]
Ruth: Me? I was asleep! I snore.
Ask anyone. ...Don't ask anyone.

[Bad luck]
Ruth: Bad luck? An hour early is a
lot of bad luck. But maybe.

Ruth: Whoever it was... the readings
point at Eterna Forest next.
```

- *Set 22.*

## 2.10 Eterna Forest: the Vespiquen totem

Owner **s-floaroma** (overworld), **rift-a** (DW) | `eterna_forest`, `DW_ETERNA_FOREST` | reads **22** | sets **23**,
**24**, (rift-a **26**), **29**

- *Eterna Forest is silent: no wild battles on the main path is not required, but the stock forest trainers stay. A violet rift hangs between two trees off the main path. Ruth and Cyrus wait beside it. Talking to Ruth starts the scene; set 23.*

```text
Ruth: It's the same signature as
Ravaged Path. Not one Combee hums.
--
Be careful in there.
```

- *Touching the rift: set 24, warp into `DW_ETERNA_FOREST`.*

**Inside (rift-a).** New verb: ceilings. A hive; the path climbs onto the ceiling (B4F record as template); ghost-prop
honeycomb fades in and out on a timer.

```text
Cyrus: The hive grew into the
ceiling.
--
So does the path. Walk where the
honey is. Not where it was.
```

- *When the honeycomb fades under the player for the first time:*

```text
Cyrus: Wait for it. It comes back.
Most things here do.
```

- *Totem battle: Vespiquen (stock encounter; it summons Combee waves). After: the aura drains, it shrinks, its shard turns clear. It hovers in front of the player, then flies off (hide).*

```text
{PLAYER} got a Calm Shard!
```

- *Cyrus looks at the empty platform. Only the player hears this.*

```text
Cyrus: Whoever did this knew exactly
how much a Pokemon can bear
--
before it breaks.

Cyrus: ...So did I, once.
```

- *rift-a sets `FLAG_TOTEM_VESPIQUEN_DEFEATED` and 26; exit warp to Eterna Forest by the rift spot.*

**Outside (s-floaroma).** Ruth checks the Resonator.

```text
Ruth: It's holding the new shard.
But it won't answer.
--
Like it's waiting for something.

Ruth: ...Oh! Gardenia's the Gym
Leader in Eterna.
--
Maybe it's waiting for her to vouch
for you.
```

- *Set 29. Ruth and Cyrus walk on toward Eterna (hide). The forest's wild encounters return to normal from 26 on (P2 if it needs an encounter swap).*

## 2.11 Eterna City: Gym 2, and Garius battle 1

Owner **s-eterna** | `eterna_city`, `eterna_city_gym` | reads **29** | sets **31**, **32**

- *Gym 2: Gardenia (trainers-gym team). On the win, set 31 and give the Forest Badge as stock. Gardenia, after the battle, in the Gym:*

```text
Gardenia: That forest has been
wrong for weeks. Too quiet.
--
This morning it woke up again.
--
...That was you, wasn't it?
Thank you.
```

- *The Resonator hums: a message box after the badge text.*

```text
The Resonator hums. Vespiquen's
energy answers now!
```

- *Stepping out of the Gym: Garius is waiting by the door, badge in hand. Cyrus stands a few tiles off. Garius walks up.*

```text
Garius: Took you long enough. I got
mine yesterday.

Garius: Is he still following you
around?
--
...Whatever. Listen.

Garius: Some old guy in Floaroma
said Eclipse gave him his wife's
--
Pokemon back. Gave it BACK.
--
...Battle me.
```

- *Battle: `GARIUS_ARC2_ETERNA_{starter}`. Set 32 after the battle whatever the result.*

```text
Garius: Tch. Fine. You're good.

Garius: Rowan called. He wants
everybody in Celestic. Even me.
--
Even HIM. I'm crossing the mountain
tonight.
```

- *Garius leaves east toward Route 211 (hide). He is gone before the Haven.*

## 2.12 The Eclipse Haven

Owner **s-eterna** | `eterna_city`, `team_galactic_eterna_building_1f`-`4f` | reads **32** | sets **33**, **34**, **35**

- *The old Galactic building, hung with an Eclipse banner (sign): A HOME FOR THE ONES LEFT BEHIND.*

```text
A HOME FOR THE ONES LEFT BEHIND
Eclipse Haven

The Resonator buzzes faintly near
the building.
```

- *Gardenia comes out of the Gym after the player (after 32). Set 33 when she finishes.*

```text
Gardenia: Can I ask you something?
Off the record?

Gardenia: There's a shelter in town.
The Eclipse Haven.
--
They take in Pokemon whose trainers
have passed on.
--
I brought them three last spring.

Gardenia: Not one has been adopted.
And now they won't let me visit.
--
Something's wrong. You can tell,
the way a plant isn't getting sun.
```

- *Gardenia and Ruth walk with the player to the Haven. Cyrus waits outside by the door (Cyrus object stays outside).*

```text
Cyrus: I'll wait here. A building
like this... I'd rather not.
```

- *1F lobby. Set 34 on entering.*

```text
Haven Receptionist: No visitors
today, I'm afraid.
--
The Pokemon are resting.

Gardenia: They're always resting.
```

- *A janitor mopping the lobby (`OBJ_EVENT_GFX_LOOKER_JANITOR`) edges over to the player.*
- *If `FLAG_UNK_0x091C` (crate tail) is set:*

```text
Janitor: Psst. You. The child from
the crates in Jubilife.
--
I said I would remember you.
--
Do not look at me. Look at the
floor.
```

- *If it isn't:*

```text
Janitor: Psst. You. With the
Pokedex.
--
Do not look at me. Look at the
floor. It is very clean.
```

- *Then, both cases:*

```text
Janitor: I am Looker. International
Police. ...You did not hear that.

Looker: There is a service door at
the back. In five minutes, it will
--
be unlocked. I will be... mopping
elsewhere.
```

- *Looker walks off (hide). The back door event is unlocked. The back corridor (2F): rows of kennels, every one empty, each with a name tag. Kennel signs (each is a sign event):*

```text
A name tag: BRAMBLE.
The kennel is empty.

A name tag: PIP.
The kennel is empty.

A name tag: CLOVER.
The kennel is empty.

A name tag: DUCHESS.
OWNER: DECEASED. LAKE VALOR.
--
The kennel is empty.
```

- *Gardenia stops at the first three (trigger on her walking past).*

```text
Gardenia: Bramble... Pip... Clover.
--
These are mine. Where are they?
```

- *A cramped office (3F). Looker at a filing cabinet.*

```text
Looker: Crates. Every week. Labeled
'supplies.' Look where they go.
```

- *Sign on the desk (the manifests):*

```text
Shipping manifests. Destinations:
--
RAVAGED PATH. VALLEY WINDWORKS.
ETERNA FOREST. ROUTE 214.

Ruth: Those are... those are my rift
readings. Every single one of them.

Looker: Pokemon go in.
Crates go out.
--
And wherever the crates go, a rift
tears open.
```

- *Two caretakers in aprons block the door (Eclipse grunt objects): emote `!`.*

```text
Haven Caretaker: Staff only,
sweetie.
--
You're going to have to leave.
Now.
```

- *Double battle: the player and Gardenia (partner) against `ECLIPSE_GRUNT_ARC2_03` + `_04`.*
- *4F loading bay: a handful of crates. One holds a Budew (Budew object beside a crate). Gardenia runs to it.*

```text
Gardenia: Pip! Oh, Pip...

Gardenia: ...Bramble and Clover
aren't here.
--
They already sent them.
```

- *Looker calls it in (stage: he talks into his collar). The Haven is shut.*

```text
Looker: This is bigger than one
building.
--
Whatever they do at those sites,
I intend to see it with my own eyes.

Looker: One more thing. The man who
travels with you.
--
In the... unusual suit.
What is his name?

Ruth: Cyrus.

Looker: Cyrus. Hm.
```

- *He writes it down (Looker faces up, `WaitTime 30`).*

```text
Looker: If you see me again,
you have not seen me.
```

- *Set 35. Fade out; warp to 2.13 with the return point (Eterna, outside the Haven).*
- *Fair-play: Garius left Eterna before Gardenia asked. This is the one raid Eclipse didn't see coming.*

## 2.13 Cutaway: Team Eclipse

Owner **s-cutaways** | violet room | reads **35** | sets **39**, returns to Eterna

- *The player isn't in this scene. The violet room. Saros and Kahn.*

```text
Saros: The Haven is gone.

Kahn: We have other ways to fill the
crates.

Saros: We didn't see it coming.
We always see them coming.

Kahn: Our friend wasn't told.
--
Our friend says they're crossing
Mt. Coronet to Celestic next.
--
Rowan wants them to meet someone.

Saros: Celestic. The old woman.
--
Then I'll go myself.
```

- *Set 39; return to Eterna. Never show who the friend is.*

## 2.14 Mt. Coronet, Route 211

Owner **s-celestic** | `route_211_west`, `mt_coronet_1f_tunnel_room` | reads **39** | sets **40**

- *Rowan asked everyone to meet in Celestic, so Garius is here too (he got turned around in the dark tunnels and is sitting on a rock when the group arrives), keeping his distance from Cyrus (Ruth, Cyrus, Garius objects in the tunnel room). A floor grate glows dull orange (palette-lit grate object or floor sign).*

```text
Ruth: It's hot. Mountains aren't
supposed to be hot on the inside.

Garius: Great. Even the mountain's
broken.
```

- *Cyrus stops and puts a hand flat on the rock wall (face the wall; `WaitTime 60`).*

```text
Ruth: Cyrus?

Cyrus: ...It's nothing.
Keep moving.
```

- *For a moment, deep under the grate, something shimmers violet-black (one-frame palette flash on the grate). No text. Only the player sees it.*
- *Set 40. The group walks on east (hide); they wait in Celestic.*
- *Gate check for the lead: whether the Route 211 tunnel needs Rock Smash in the new order is noted in R0's registry report. The Resonator (Hitmonlee) covers it if so.*

The grate, if the player reads it:

```text
A grate in the floor. Hot air rises
from somewhere far below.
```

## 2.15 Celestic Town: the elder's stories

Owner **s-celestic** | `celestic_town`, `celestic_town_cave` | reads **40** | sets **42**

- *Stock Celestic is replaced: no Galactic grunt at the ruins, no Cyrus speech, no relic scene, no Surf give.*
- *The shrine (cave interior with the stock mural). Rowan waits with the elder (Cynthia's grandmother). A tall man in a long coat stands by the wall, hands behind his back: Saros. Ruth, Cyrus and Garius come in with the player.*

```text
Rowan: Thank you for seeing us,
elder.
--
These are the two I told you
about.

Elder: The children who went into
the torn world. And came back.

Elder: Sit. Old women tell stories.
Sometimes the stories are true.

Elder: The three who made this
world. Time, and space,
--
and the world beneath.
--
They were never meant to be held.
Not by any hand.

Elder: Every age, someone tries.
--
Always for a reason that sounds
good. A love to save.
--
A grief to undo.

Elder: And every time, they bend
time and space to fix their sorrow,
--
and leave the world with more of it.

Elder: I know three such stories.
Listen.
```

- *Each story: the elder faces the mural (face up), then back. One message per story.*

```text
Elder: A king stopped the clock on
the morning his queen breathed.
--
His kingdom stood frozen in that
morning for a hundred years.
```

- *Saros's hands tighten behind his back (Saros faces away from the elder, `WaitTime 20`, faces back).*

```text
Elder: A sailor folded the sea to
find the world where his partner
--
never drowned.
--
He found it. He could never find
his way home.

Elder: A sister kept watch at a gate
for her brother.
--
She kept everyone else out, too.
--
Until there was no one left to
let in.

Elder: Each time, something rose
from beneath the world.
--
And set it right. Never gently.
```

- *Cyrus has been staring at the mural. He speaks without turning (emote `...` over Cyrus).*

```text
Cyrus: ...Every time?

Elder: Every time I know of.

Saros: With respect, elder, that's
what people say once they've made
--
their peace with losing.
--
Some of us haven't.

Garius: Yeah. Old stories.
--
It's easy to tell people to let go
when you've never lost anything.

Elder: Child. What have you lost?

Garius: ...Nothing. Forget it.
```

- *Saros turns to Garius (face him).*

```text
Saros: You're sharp.
--
Team Eclipse could use people like
you.

Garius: Not interested.
```

- *Saros bows to the elder and walks out (hide). Set 42.*
- *Hindsight (L1b, G4): Saros knew they'd be here; he and Garius talk like two people who already know each other.*

## 2.16 Celestic Town: Rowan's question, and Cyrus battle 2

Owner **s-celestic** | `celestic_town_cave`, `celestic_town` | reads **42** | sets **44**

- *In the shrine, straight after 2.15. Rowan steps up to the elder. Garius lingers by the door.*

```text
Rowan: Elder. One question. As a
scientist, if you'll allow it.
--
Can the dead come back?

Elder: The stories never say they
can't.
--
They say what it costs.

Rowan: ...I've spent my life saying
no.
--
I'm not sure I can anymore.

Garius: ...Huh.

Garius: I'm off to Veilstone. Third
badge. Don't wait up.
```

- *Garius leaves (hide).*

```text
Ruth: I'll go on ahead to Veilstone,
too. Maylene wants my readings.

Rowan: Go on. I'll stay and talk
with the elder a while.
```

- *Outside: Cyrus stands alone at the cliff edge in Celestic (Cyrus object, facing away). Talking to him:*

```text
Cyrus: A king. A sailor. A sister.
--
She could have told a fourth.

Cyrus: Battle me. I need to know my
hands are steady.
```

- *Battle: `CYRUS_ARC2_2_{starter}`. No blackout.*

```text
Cyrus: She told my story without
knowing it. She even knew the end.
--
Something rose from beneath, and
stopped me.
--
I have never been so glad to lose.
```

- *Set 44. Cyrus walks off south toward Route 210 (hide). Remove the stock Surf give. The Route 210 Psyduck blockade is cleared from the north side.*

**Route 210 north, the rift mist (text only, s-celestic).** A sign event or a one-time trigger at the fog's edge:

```text
A violet mist hangs over the path.
It thins as you walk on.
```

## 2.16a Solaceon Town: the memorial wall (cutaway, Indra)

Owner **s-celestic** | `solaceon_town` | reads **44** | sets **47** at start, **49** at end

- *The memorial wall (P1: sign events on the existing wall/fence tiles; the wall art is P2). Readable any time from 44:*

```text
A wall of photos. Each card has a
name, a date and a place.

A child's drawing of a man and a
Ponyta.
--
The card gives her name, her
birthday, and where it happened.

A card: ELIAS. VALOR BASIN.
--
No one signed for it.

A banner, pinned above the wall:
--
WHO DID YOU LOSE?
Team Eclipse
```

- *The first time the player walks up to the wall at 44: set 47. `FadeScreen`; hide the player; Indra stands at the wall (`OBJ_EVENT_GFX_INDRA`). This is shown to the player only; Darren isn't there.*
- *Indra pins up a fresh card (she faces the wall; small sound).*

```text
Indra: Another name today.
A boy from Floaroma.
--
His dad cried the whole time.
I wrote it all down anyway.

Indra: Somebody has to.

Indra: Saros wants a morning.
Kahn wants a door.
--
I don't care which one works, Teo.
--
Either one brings you home.

Indra: Saros's hands shake now.
Kahn doesn't sleep.
--
The shards are taking something
out of them.

Indra: So I keep the door.
--
Nobody gets through who could
break it.
```

- *Indra walks away (hide). Fade back; the player stands at the wall. Set 49. A new sign is now on the wall:*

```text
A new card: TEO. A boy, smiling.
The pin is still shiny.
```

---

# Part 3: Veilstone to the end of Arc 2

## 2.17 Veilstone City: Gym 3, and Looker's check

Owner **s-veilstone** | `veilstone_city`, `veilstone_city_gym` | reads **49** | sets **51**

- *Gym 3: Maylene. Cobble Badge. Remove the stock HM02 give. Maylene, after the battle:*

```text
Maylene: Ruth told me about the rift
on Route 214.
--
My students won't train down there
anymore.
--
They say the sky over it feels
wrong. Please, help it.

```

- *Outside the Gym: a man in a hat and sunglasses reads a newspaper upside down (`OBJ_EVENT_GFX_LOOKER_NEWSPAPER`). He lowers it as the player passes (trigger).*

```text
Looker: Do not be alarmed. It is me.
Looker. I am in disguise.

Looker: I ran the name you gave me.
Cyrus.
--
Every database in Sinnoh. The
international records. Everything.

Looker: No birth record. No Trainer
ID. No Poketch number.
--
No history. Nothing.

Looker: This man does not exist.

Looker: So I must ask.
Do you trust him?
[YESNO]

[Yes]
Looker: Hm. Then I hope you are
right. For your sake.

[No]
Looker: Hm. Then we understand
each other. Keep your eyes open.
```

- *Yes sets `VAR_ARC2_CHOICES` bit 0 (`AddVar VAR_ARC2_CHOICES 1`; this is the only write to bit 0).*

```text
Looker: Now. A favor.
--
There is an Eclipse depot here. The
old warehouse, by the east wall.
--
Tonight I copy their manifest.
I could use a small, quiet helper.

Looker: Meet me at the side door.
Do not wave.
```

- *Looker raises the newspaper (upside down again) and walks off. Set 51.*

## 2.17a The Eclipse depot: the heist, and Indra

Owner **s-veilstone** | `veilstone_city_galactic_warehouse` | reads **51** | sets **52**, **54**

- *The stock warehouse grunts are replaced. Entering at 51 sets 52. Night tint optional. Looker by the side door.*

```text
Looker: Two sentries. They look one
way, then the other.
--
We move when they look away.
If they see you, we start again.
```

- *Stealth: `ECLIPSE_GRUNT_ARC2_07` and `_08` are sentries with a look-cycle and sight cone (the crate-tail pattern from `scripts_jubilife_city.s`). Spotted: the line below, `FadeScreen`, reset to the door. No battle.*

```text
Eclipse Grunt: Hey! You! This is a
private depot! Scram, kid!

Looker: Again. Quieter. Like a
Glameow in socks.
```

- *The office: a desk sign (the manifest). Looker reads over the player's shoulder.*

```text
A shipping manifest. Next delivery:
--
ROUTE 213. THE CAVES.
TWO FRAMES. TWO SUBJECTS.

Looker: Route 213. There it is.
--
Go. I will finish copying.
Make a little noise by the trucks.
```

- *Looker stays at the desk (hide him after the player leaves the room). The loading bay: two guards, `ECLIPSE_GRUNT_ARC2_05` and `_06`, battled in turn.*

```text
Eclipse Grunt: A kid? In here?
--
Get away from the trucks!
```

- *After the second guard: a woman walks in from the bay door. The grunts step aside (they back off two tiles). Indra.*

```text
Indra: That's enough.

Indra: You're Rowan's. The one with
the guide.
--
Trucks, go. Now. I'll keep this one
busy.
```

- *Truck sound; the bay door shuts. Battle: `INDRA_DEPOT`.*

```text
Indra: Hm. You fight like somebody
who's never lost anything.
--
Keep it that way.

Indra: Go home, kid. Somebody's
waiting there.
--
Don't make them wait forever.
```

- *Indra leaves through the bay door (hide). Looker appears from the office.*

```text
Looker: I have it. Every page.
--
...Who was that woman?

Looker: She let you go. People like
that never do anything for free.
```

- *Set 54. Looker leaves. The manifest is why Looker's Route 213 raid exists.*

## 2.17b The Meteor Shrine: Maylene's trial

Owner **s-veilstone** | `veilstone_city` (the stock meteorite garden) | reads **54** | sets **57**

- *Maylene waits at the garden gate. Cyrus stands at the far edge, looking at the meteorites.*

```text
Maylene: You fought like your
Pokemon trusts you completely.
--
I want to show you something.

Maylene: Long ago, a star fell here.
--
Veilstone was built around the
pieces. My family keeps them.

Maylene: The star's light wakes
something in a Pokemon.
--
But only when the bond with its
Trainer is strong enough.
--
We call it Mega Evolution.

Maylene: It can't be forced. Ever.
It only answers a bond.

Cyrus: In my world, these were only
rocks.

Maylene: Show me your bond.
Lucario! Let's go!
```

- *Maylene's Lucario Mega Evolves. Trial battle: Maylene (trial id, Mega Lucario only).*

```text
Maylene: That's it. That's the bond.
This is yours now.

{PLAYER} got a Key Stone!
```

- *Maylene opens a stone box (object). Three Mega Stones inside glow.*

```text
Maylene: These sat dark in that box
for a hundred years.
--
They lit up the day your Pokemon
came out of that other world.

Maylene: This one is yours.
--
Ruth can take the other two. One
for Garius, one for Cyrus.
```

- *Give the Mega Stone for the player's starter line (`AddItem`; Torterrite/Infernapite/Empoleonite by the starter var). Set 57.*

## 2.17c Route 215 at night: the opened crate (optional)

Owner **s-veilstone** | `route_215` | reads **49-59**, night only | sets `VAR_ARC2_CHOICES` bit 3

- *A night-only object pair beside the path: Cyrus, crouched by a pried-open crate (`OBJ_EVENT_GFX_ECLIPSE_CRATE`). As the player nears, a Buneary bolts out of it into the grass (Buneary object runs, hide). Cyrus stands (emote `!`).*

```text
Cyrus: ...

Cyrus: You would not believe me if I
explained.
```

- *He walks off into the dark (hide). `AddVar VAR_ARC2_CHOICES 8` (bit 3; set once, guard with a map-local flag). The crate sign afterwards:*

```text
An Eclipse crate. The lid has been
pried off. It's empty.
```

## 2.17d Veilstone Pokemon Center: the dawn plan

Owner **s-veilstone** | `veilstone_city_pokecenter_1f` | reads **57** | sets **59**

- *Evening. Ruth and Cyrus at a table. Entering starts the scene.*

```text
Ruth: Maylene says the Route 214
rift gets worse every night.
--
So we go in at dawn. First light.
```

- *Garius comes in, heals at the counter, and walks past the table.*

```text
Garius: Don't mind me. Just passing
through.

Ruth: Garius! Route 214, at dawn.
You could come with us.

Garius: Pass. Got my badge this
morning. I'm heading south.

Cyrus: I'll be here.
--
I don't sleep much anyway.
```

- *Garius leaves (hide). `FadeScreen`; heal; set 59. Fade in: morning, the player by the counter.*

```text
Ruth: Morning! Let's go before the
sun's all the way up.
```

## 2.18 Route 214: the Skarmory totem (leak L2)

Owner **s-route214** (overworld), **rift-b** (DW) | `route_214`, `DW_ROUTE_214` | reads **59** | sets **60**, **61**,
**62**, (rift-b **63**)

- *Dawn. Two Eclipse grunts at the rift, packing up a humming machine pointed into it (machine object). Ruth and Cyrus come up behind the player. Emote `!` over the grunts. Set 60.*

```text
Eclipse Grunt: Ha! Too late.
--
We gave your bird a little boost.
Good luck in there.

Eclipse Grunt: Tell the one who
walked out his bird says hi.
```

- *Battles: `ECLIPSE_GRUNT_ARC2_09`, then `_10`. They flee south (hide).*

```text
Ruth: They knew we'd come at dawn.
--
They made it stronger on purpose.
```

- *Ruth doesn't look at Cyrus this time (she faces the rift, not him). Then the ledger L2: the common prompt, the menu, one reaction, the closer.*

```text
[MENU: Cyrus | Garius | Ruth | Bad luck]

[Cyrus]
Ruth: Cyrus? He was at the Center
all night. I heard him pacing.

[Garius]
Ruth: Garius? He was only passing
through. He didn't even sit down.

[Ruth]
Ruth: Me? I once told a plan to a
vending machine. ...That's not a no.

[Bad luck]
Ruth: Bad luck? Three times now.
I want to believe that too.

Ruth: ...Go.
I'll watch the readings.
```

- *Set 61. The rift opens. Touching it: set 62, warp into `DW_ROUTE_214`.*

**Inside (rift-b).** New verb: wall-to-wall hops across a chasm with no floor. Cyrus guides, quieter than before.

```text
Cyrus: No floor here. Only walls.
--
Jump when the far wall is under
you. Not before.
```

- *Before the totem platform: a frame with a violet shard jammed in it, wired to the platform (frame object). The boost choice.*

```text
Cyrus: Their machine left a shard in
that frame. It's feeding the bird.

Cyrus: I can pull it out.
--
It won't be gentle. For me.

Cyrus: Should I?
[YESNO]

[Yes]
Cyrus: ...

Cyrus: It's out.
--
It bit. These things take something
from whoever holds them.

[No]
Cyrus: Then it fights at full
strength. So must you.
```

- *Yes: screen flash, Cyrus kneels for a moment, the frame object goes dark; `AddVar VAR_ARC2_CHOICES 4` (bit 2). The totem fights unboosted. No: the totem gets +1 Atk/+1 Def (totem config boost field).*
- *Totem battle: Skarmory, L32. After: aura drains, shard clears, it flies off.*

```text
{PLAYER} got a Calm Shard!

Cyrus: It's free now. That's what
matters.
```

- *rift-b sets `FLAG_TOTEM_SKARMORY_DEFEATED` and 63; exit warp to the Route 214 rift spot; s-route214 warps to 2.19.*

**Valor Lakefront plaque (s-route214, sign at the overlook; readable any time):**

```text
IN MEMORY OF THOSE LOST IN THE
VALOR BASIN COLLAPSE.
--
A list of names follows.
--
...ELIAS, OF TWINLEAF TOWN...
```

## 2.19 Cutaway: Kahn

Owner **s-cutaways** | `route_222` (a cliff over the sea, unreachable in Arc 2) | reads **63** | sets **69**, returns to
Route 214

- *The player isn't in this scene. Night. Kahn alone at the cliff edge, holding an empty Poke Ball. Sea sound.*

```text
Kahn: Seven years today, Lucario.

Kahn: Everyone says there's no
world where you come back.

Kahn: There is.
Somewhere, you didn't fall.
--
Somewhere, you're still waiting for
me to come home.

Kahn: Palkia can take me there.
--
I just need enough shards to hold
it.
```

- *Kahn closes his hand over the ball. Set 69; return to Route 214.*

## 2.20 Pastoria City: Gym 4, and the Valor Basin

Owner **s-pastoria** | `pastoria_city`, `pastoria_city_gym`, `lake_valor_drained` | reads **69** | sets **71**, **72**, **73**

- *The Great Marsh grunt/bomb plot is cut; the Great Marsh stays a catching stop.*
- *Gym 4: Crasher Wake. Fen Badge. Set 71. Wake, after the battle:*

```text
Crasher Wake: Something's choking
the water on Route 213!
--
The fish won't bite! The Pokemon
won't swim!
--
A true Trainer would look into it!
WHAAAAH!
```

- *Outside the Gym: Looker, in his trench coat, by a lamppost. Set 72 after he speaks.*

```text
Looker: Do not be alarmed. It is me.

Looker: The manifest was true.
A live site. The Route 213 caves.
--
Tonight, we go in.

Looker: I want every pair of eyes.
Even your loud friend.
--
I saw him walk north, to the dry
lake. Bring him to the Center.
```

- *The Basin (`lake_valor_drained`, always drained per D12). Dusk tint optional. Fence sign:*

```text
VALOR BASIN
--
Keep out. Unstable ground.
```

- *Garius stands at the fence, staring at the basin. He doesn't turn at first. First talk:*

```text
Garius: ...Don't. Just don't, okay?

Garius: What? Looker sent you?
--
...Fine. Tell him I'll be there.
```

- *Set 73. Garius turns back to the fence and stays until the player leaves the map. Second talk (once):*

```text
Garius: Hey. If someone told you
they could fix the worst thing
--
that ever happened to you...
--
and all it cost was telling them
stuff nobody'd miss...
--
Would you?
[YESNO]

[Yes]
Garius: ...Yeah. Me too.

[No]
Garius: Must be nice.
```

- *Yes: `AddVar VAR_ARC2_CHOICES 2` (bit 1). Arc 3 reads it ("You said yes. At the Basin."). No reaction beyond the line; no music change. Garius is hidden once the player leaves the map.*
- *Hint G3b: a man from Twinleaf on the plaque, and Garius at this fence.*

## 2.21a Pastoria Pokemon Center: Looker's briefing

Owner **s-pastoria** | `pastoria_city_pokecenter_1f` | reads **73** | sets **75**

- *Looker, Ruth, Cyrus and Garius at a table. Entering starts the scene.*

```text
Looker: A live Eclipse site.
The caves on Route 213.
--
Tonight, we see it with our own
eyes.

Looker: Two go in. Me, and the quiet
one.
--
Five is not a raid. Five is a
parade.

Ruth: Cyrus and I will wait at the
cave mouth with the readings.

Garius: I'll watch the gate. If they
run, they run past me.
```

- *`FadeScreen`; heal; set 75. Fade in at night outside the Route 213 cave (warp; s-raid's map).*

## 2.21 Route 213: the raid, and Looker's proof (leak L3)

Owner **s-raid** (overworld), **rift-b** (DW) | `route_213`, `DW_ROUTE_213` | reads **75** | sets **80**, **82**, **83**,
(rift-b **84**)

- *Night, the cave. Entering sets 80. Looker beside the player; Ruth and Cyrus stay at the mouth (objects outside).*

```text
Looker: Two patrols. They look,
they turn, they look.
--
We move when they turn. And we do
not stop.
```

- *Stealth: two patrols with look-cycles and sight cones, and a step budget to the frames. Spotted: the line below, `FadeScreen`, reset to the last checkpoint (no fail state).*

```text
Eclipse Grunt: Hey! Who's there?!
Get out of here, kid! Scram!

Looker: Again. We still have time.
A little.
```

- *Half the step budget gone (once):*

```text
Looker: The air is splitting.
Faster!
```

- *The frames: two, bolted to the wall. In one, the Lapras is already gone: only a rift, torn wide and screaming (rift object, cry). In the other, a Psyduck hangs limp, the air around it splitting. Ruth and Cyrus run in from the mouth.*

```text
Ruth: No, no, no...
--
It's tearing! It's going to pull it
through!
```

- *Two guards turn: battles `ECLIPSE_GRUNT_ARC2_11`, then `_12`. Then Looker and the player cut the Psyduck free (Psyduck object drops beside the frame) just as the air around it snaps shut (flash).*
- *The other rift stays open. Something huge moves on the far side (Lapras cry, shadow).*

```text
Looker: They knew.
--
They knew we were coming, so they
rushed it.
--
They pushed that machine to finish
early.

Looker: That Lapras is in there
because someone told them.
```

- *Silence. Nobody looks at anybody (`WaitTime 60`; all objects face down).*

```text
Looker: Now I understand.
--
They are not just taking Pokemon.
--
They hurt them until the world
itself tears.
--
And whatever falls through comes
out like... that.
```

- *Ledger L3: Looker asks (his own prompt, not the common one); same menu, Looker reacts.*

```text
Looker: Someone told them. I must
ask. Who do you think it was?
[MENU: Cyrus | Garius | Ruth | Bad luck]

[Cyrus]
Looker: The man who does not exist.
Hm. I will write that down.

[Garius]
Looker: The loud one. Hm.
I will write that down.

[Ruth]
Looker: The assistant. Hm. I will
write that down. ...Do not cry.

[Bad luck]
Looker: Luck. I do not believe in it.
But I will write it down.
```

- *Set 82. The Lapras rift is the way in.*

```text
Cyrus: It's still in there.
We go now. Together.
```

- *Touching the rift: set 83, warp into `DW_ROUTE_213`.*

**Inside (rift-b): the Drowned Lake.** New verb: the lake hangs upside down as the ceiling; walk the ceiling under the
water; the debris on the old lakebed is the landmark. At the entry platform:

```text
Cyrus: In my world there was a lake
here. Lake Valor.
--
...So this is where it went.
```

- *Item beside the rusted frame prop (rift-b sets `FLAG_ARC2_ELIAS_CARD` 0x092E). Nobody comments; Cyrus is out of earshot.*

```text
An old Trainer Card. The name has
worn away.
--
Hometown: Twinleaf.
```

- *Totem battle: Lapras (with Mantyke/Shellos allies). After: aura drains, shard clears, it swims up into the hanging lake.*

```text
{PLAYER} got a Calm Shard!

Cyrus: It wasn't yours to fix. You
fixed it anyway.
```

- *rift-b sets `FLAG_TOTEM_LAPRAS_DEFEATED` and 84; exit warp to the cave, in front of the frames. Looker waits there.*

```text
Looker: I have photographs. Machine
parts. The frames.
--
Professor Rowan must see this.
Tonight.
```

## 2.22 Pastoria: Rowan sees the proof

Owner **s-pastoria** | `pastoria_city_pokecenter_1f` | reads **84** | sets **86**

- *Night. The player is warped to the Pastoria Center. Rowan is there with Looker; photos on the table (sign). Ruth and Cyrus stand by.*

```text
Rowan: ...

Rowan: Since that night in Jubilife,
I've believed it could be done.
--
That someone could come back.

Rowan: Not like this.
--
Never like this.

Rowan: Looker. Whatever you need
from my lab, it's yours.
```

- *Set 86. Cyrus walks out toward Route 213 (hide); Ruth follows him out.*

## 2.23 Route 213 beach: the confrontation (Cyrus battle 3)

Owner **s-raid** | `route_213` | reads **86** | sets **88**, **89**

- *Night on the beach. Cyrus stands apart, looking at the water. Garius walks up beside the player.*
- *Garius's opening line depends on the ledger (decode recipe above). First match wins:*

```text
[Cyrus picked 3 or 4 times]
Garius: You've known since Ravaged
Path. You just needed someone
--
to say it.

[Bad luck picked 3 or 4 times]
Garius: Bad luck, huh? Four times?
Nobody's that unlucky.

[Ruth picked 2 or more times]
Garius: And it's not Ruth. Come on.
She cried over a Psyduck tonight.

[Garius picked 2 or more times]
Garius: Yeah, I know you wondered
about me. Fine. Look all you want.

[anything else]
Garius: You keep changing your mind.
I get it. But count it up.
```

- *Then, every case:*

```text
Garius: Ravaged Path. Windworks.
Celestic. Route 214. Tonight.
--
Every time, he's there. Every time,
they know.

Garius: Looker can't find a single
thing about him.
--
Come on. You know it's him.

Garius: Make him prove it.
Battle him.
```

- *The player walks to Cyrus (`ApplyMovement`). Cyrus turns before the player reaches him.*

```text
Cyrus: You don't need to say it.
--
I've seen that look before. I used
to wear it.

Cyrus: Words prove nothing.
--
Judge me the way trainers do.
```

- *Battle: `CYRUS_ARC2_3_{starter}`. He fights hard. Set 88.*

```text
Cyrus: ...Whatever you've decided,
--
I won't stand here and wait to be
believed.

Cyrus: Ruth's readings show a rift
in the Lost Tower, near Hearthome.
--
I'll go in alone.
--
If there's proof of who's doing
this, it's in that world.
--
I'll find it.
```

- *Cyrus walks off west (hide). Ruth comes down the beach.*

```text
Ruth: I'm taking Looker's samples
back to the lab.
--
...Be careful. Both of you. All of
you.
```

- *Ruth leaves (hide); Garius leaves without a word (hide). Set 89.*
- *Irony in hindsight: the informant is the one who pushes for the trial.*

## 2.24 Hearthome City: Fantina's vigil, Gym 5, Garius battle 2, and Saros

Owner **s-hearthome** | `hearthome_city`, `hearthome_city_gym_*`, `route_209`, `route_209_lost_tower_1f`, `_5f` |
reads **89** (vigil: badge check) | sets **91**, **92**

**The vigil (any time before the Fen Badge).** The player can reach Hearthome early via Route 209. The Gym door is shut:

```text
The Gym Leader is away.
--
She keeps a vigil at the Lost Tower
every night.
```

- *Fantina sits at the Lost Tower 1F, by the stairs, blocking them (Fantina object). Talking to her:*

```text
Fantina: Not yet, mon ami.
Ze tower is not ready for you.

Fantina: Every night I sit here.
Ze dead, zey cry now.
--
Someone must listen.

Fantina: Once a month, a sad man
brings flowers to a grave upstairs.
--
He never speaks. I do not ask.
```

- *With the Fen Badge, Fantina is back in the Gym and the tower stairs are open.*

**Gym 5.** Fantina. Relic Badge. If the badge is won before progress 89, nothing else happens yet; set **91** the
first time the player is in Hearthome with the Relic Badge and progress 89 (or on the win, if already 89). Fantina,
after the battle:

```text
Fantina: Ze Lost Tower, on Route
209... it is a place for ze dead
--
to rest. But now it cries.
--
Even ze ghosts are afraid.
--
Please, mon ami. Go and listen.
```

**Garius battle 2** (reads 91, sets 92). Garius waits in the Hearthome plaza and walks up.

```text
Garius: So he walked off into a rift.
Alone.
--
And you're still worried about HIM?

Garius: Even Rowan asked if the dead
can come back. I was there.
--
I heard him.

Garius: Ruth gave me this stupid
stone. It won't do a thing for me.
--
...Whatever. Battle me.
```

- *Battle: `GARIUS_ARC2_HEARTHOME_{starter}` (no Mega in Arc 2; see the decisions). Set 92 whatever the result.*

```text
Garius: ...Forget it. Forget all of
it.
```

- *Garius leaves (hide).*

**2.24 cutaway: Saros at Mira's grave.** The first time the player enters Lost Tower 1F at 92: `FadeScreen`, hide the
player, show 5F. Saros kneels at a small grave with fresh flowers (Saros object, grave sign). Shown to the player only.

```text
Saros: Happy birthday, Mira.
You'd have been nine today.

Saros: Dialga can give me back one
morning. The morning before.
--
That's all I want.
--
Just one morning.
```

- *He stands, looks down the stairs toward the floor where his people work, and leaves without looking back (hide). Fade back to 1F. Mark seen with an s-hearthome flag.*

## 2.25 The Lost Tower rift: alone, and the vein

Owner **s-hearthome** (overworld), **rift-b** (DW) | `route_209_lost_tower_2f`, `DW_LOST_TOWER`,
`hearthome_city_pokecenter_1f` | reads **92** | sets **93**

- *Lost Tower 2F: a violet rift hums (rift object, shown at 92+). No Cyrus, no Ruth. Touching it warps into `DW_LOST_TOWER`.*

**Inside (rift-b), first visit.** The hardest rift so far, without a guide. At the first seam, Cyrus's words come back as
on-screen text (no speaker; a memory):

```text
...Follow the seam.
--
Not that one.
That one is a scar.
```

- *A cavern glittering violet: Eclipse Shards growing out of the rock like crystals (shard objects). Sign:*

```text
Violet crystals grow out of the
rock. Eclipse Shards.
--
A whole vein of them.
```

- *rift-b sets `FLAG_ARC2_VEIN_SEEN` (0x092F, from rift-b's block). The way deeper is blocked by a wall of shadow:*

```text
A wall of shadow. It won't move.
--
There's no sign of Cyrus.
```

- *The player has to go back (exit warp to 2F, progress still 92).*

**The call (s-hearthome).** Entering the Hearthome Center at 92 with `FLAG_ARC2_VEIN_SEEN`: the player calls Rowan
from the counter phone (no phone UI; message boxes).

```text
{PLAYER} called the Professor.

Rowan: {PLAYER}? Any sign of
Cyrus?

You told the Professor about the
vein.

Rowan: A whole vein? Growing in that
world?
--
...Tell no one else. Not yet.
Not until we understand it.

Rowan: Garius is here, by the way.
He came by asking about Cyrus.

Garius: Shards. Just sitting there.
--
Huh.

Rowan: I'll come to Hearthome first
thing. Get some rest.
```

- *Set 93. `FadeScreen`; heal; fade in: morning, in the Center. Only Rowan and Garius were told: this is the leak that clears Cyrus.*

## 2.26 The Lost Tower: the clearing leak, and finding Cyrus (end of Arc 2)

Owner **s-hearthome** (overworld), **rift-b** (DW) | `route_209_lost_tower_2f`, `route_209`, `DW_LOST_TOWER` |
reads **93** | sets **94**, (rift-b **95**), **99**

- *Lost Tower 2F: Eclipse grunts with picks and empty crates at the rift (2 grunt objects, crate objects).*

```text
Eclipse Grunt: Boss heard there's a
whole vein down there.
--
Grab everything.
```

- *Battles: `ECLIPSE_GRUNT_ARC2_13`, then `_14`. They flee downstairs (hide). Set 94.*
- *The player stands at the rift. Cyrus has been inside for two days, with no way to reach anyone. Rowan runs up the stairs (out of breath: emote `...`).*

```text
Rowan: I came as fast as I could.
--
They knew about the vein?

Rowan: ...But only you, me and
Garius knew.
--
And Cyrus has been in there the
whole time.

Rowan: ...It wasn't him.

Rowan: Go. Bring him back.
```

**Inside (rift-b), second visit (94).** The wall of shadow parts as the player nears (Giratina's shadow passes; no text).
Deeper, beside a towering Spiritomb, Cyrus is on his knees, exhausted, his starter fainted at his side.

```text
Cyrus: ...You came.

Cyrus: It's been alone down here
with a hundred voices.
--
I know how that is.
```

- *Totem battle: Spiritomb, L40. After: the aura drains, the shard clears, it sinks into the floor.*

```text
{PLAYER} got a Calm Shard!
```

- *rift-b sets `FLAG_TOTEM_SPIRITOMB_DEFEATED` and 95; exit warp out of the tower (s-hearthome: Route 209, outside the Lost Tower door). Rowan and Cyrus stand there.*

```text
Rowan: Cyrus. I doubted you.
I'm sorry.

Cyrus: You were right to. I would
have doubted me too.
```

- *Looker steps out from behind the tower (Looker object walks in).*

```text
Looker: Do not be alarmed. I was
never here.

Looker: Someone has been opening
Eclipse's crates on Route 215.
--
Every Pokemon, released.

Looker: ...I suspect I now know
who.
```

- *If `VAR_ARC2_CHOICES` bit 3 is set (the player saw 2.17c; test with a temp copy and the subtraction recipe):*

```text
Cyrus: I told you that you would not
believe me.
```

- *Looker leaves. Garius walks up from the Hearthome side. He looks at Cyrus for a long moment (`WaitTime 60`). His face gives nothing away.*

```text
Garius: ...Huh.
--
Guess it wasn't him.
```

- *Garius turns and walks off toward Hearthome (hide). `FadeScreen` to black. Set 99.*

```text
END OF ARC 2
```

- *Cyrus is cleared: he was lost in the Distortion World when the vein leaked. Only one person who knew is left. This is also when Eclipse learns the Distortion World holds shard veins.*

---

## Appendix A: P2 lines (round 3 workstreams; not needed for P1)

**S10 Rowan on TV (quests; Pokemon Center TV, from 44):**

```text
Rowan: I once called Team Eclipse
con artists.
--
I may have spoken too soon.
```

**S10 Solaceon banner (quests/world-art, from 47):**

```text
EVEN PROFESSOR ROWAN SAYS IT
MAY BE POSSIBLE.
--
WHO DID YOU LOSE?
```

**S10 2.22 retraction (quests; append after Rowan's 2.22 lines only if the TV line shipped):**

```text
Rowan: And I'll call the station
in the morning.
--
I owe them a retraction.
```

**S11 Duchess reunion (quests; the Route 202 old man in Jubilife, after 35):**

```text
I never once asked her if she'd want
to come back.
--
...But this one, I can ask.
```

**S11 Plusle/Minun (quests):** the Minun from 2.9 waits at a dropped crate on Route 205; the Resonator buzzes near it;
opening the crate frees the Plusle; both are given as a pair.

## Appendix B: Arc 3 callbacks (for the Arc 3 pass, not built in Arc 2)

| Where | Reads | Line |
|---|---|---|
| 3.2 reveal | Cyrus picked at every answered leak | Garius: "You picked him. Every single time." |
| 3.2 reveal | Garius picked at least once | Garius: "You almost had me at the Windworks. Then you looked away." (adapt the place to the first Garius pick) |
| 3.2 reveal | `VAR_ARC2_CHOICES` bit 1 | Garius: "You said yes. At the Basin." |
| 3.2 or later | `FLAG_ARC2_ELIAS_CARD` | The player can show Garius the worn Trainer Card (D5) |
| 3.6 / 3.11 / 3.12 | (C11) | "They have both. ...There is one thing left that can stand against them." / "Take it, and Saros's morning and Kahn's door both break. And Teo stays dead." / "You knew they would take the other two." |

`secrets.md` L1b's "Cyrus is the one the legend is about" now reads: "Cyrus is one of the people the stories are about" (C10).

## Appendix C: decisions made writing this version

1. **2.1 to 2.2 handoff:** Cyrus asks for the meeting at the Trainers' School "tonight"; 2.2 runs on map load after a fade. Rowan ends 2.2 with "We go to Ravaged Path in the morning", so Garius hears the plan (L0) explicitly.
2. **C8 split:** "A boy stopped me. A boy, and a Champion. Then something rose out of the dark and stopped me. Then it took me into its world." Both stoppings stay; the second is the Arc 3 plant.
3. **2.4 Indra's last line** is the plan's "Find out what. Nothing stops this one." kept verbatim (box per sentence).
4. **Ledger reactions:** Ruth reacts at L0-L2 with one box each, every one a weighing that doesn't settle; Looker reacts at L3 with "I will write that down" for every pick. B = Bad luck. Cyrus says nothing after any pick.
5. **2.23 variants:** five, first match wins (Cyrus 3+, Bad luck 3+, Ruth 2+, Garius 2+, else). Then the common list.
6. **L3 whereabouts:** only Looker and the player go into the cave; Ruth and Cyrus wait at the mouth and run in at the frames; Garius watches the Route 213 gate ("If they run, they run past me"). Both suspects could have told Eclipse between the briefing and nightfall.
7. **The Basin is mandatory, the question optional:** Looker sends the player to fetch Garius (2.20), so the Basin scene always plays; the Yes/No is the second talk. Unasked = No.
8. **Plaque location:** the ELIAS plaque is in Valor Lakefront (s-route214), passed on the way south from Route 214; the Basin (s-pastoria) gets a fence sign. The plan listed the plaque under both; one copy avoids a duplicate.
9. **Garius doesn't Mega Evolve in Arc 2** (bible: Garius Megas from Arc 3). His Hearthome line: "Ruth gave me this stupid stone. It won't do a thing for me." trainers-story: no Mega Stone on his Arc 2 teams.
10. **2.11 Garius battle 1** happens as the player leaves the Gym, then Garius says Rowan called everyone to Celestic and leaves town that night: this sets up the Haven exception and L1b.
11. **2.17a depot:** 4 grunt ids as 2 sentries (07, 08: spotted = reset, no battle) and 2 dock guards (05, 06: battles). Indra battles to cover the trucks; her extra line: "You fight like somebody who's never lost anything. Keep it that way."
12. **2.17d** (new id): the Veilstone Center scene that puts Garius in the room for the dawn plan (L2 whereabouts).
13. **2.21a** (new id): the Pastoria Center briefing, s-pastoria, 73 to 75.
14. **The vein call:** Rowan is at his lab, Garius is there "asking about Cyrus" (a hindsight clue); rift-b flags the vein with `FLAG_ARC2_VEIN_SEEN` = 0x092F (rift-b's block).
15. **S3 crate payoff** is in 2.26 (Looker appears at the tower), with a Cyrus line if the player saw 2.17c.
16. **Rowan's public retraction** (S10/D4) stays P2: the 2.22 retraction line is in Appendix A and only ships with the TV line.
17. **Gym 5 before progress 89** (possible once the Fen Badge opens the Gym): the badge is kept, and 91 is set the first time the player is in Hearthome with the badge at 89.
18. **ASCII spelling:** "Pokemon", "Poketch", "Poke Ball" (no accented e), per the brief.
