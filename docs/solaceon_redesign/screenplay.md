# Solaceon Town: the Sanctuary town and the Ruins raid (screenplay)

The build text for the Solaceon redesign. town-scripts and raid-scripts implement it **verbatim**; layout,
sanctuary-interior and raid-maps place what it names. Written by the story workstream against `PLAN.md` (the
contract), `docs/story/bible.md`, `secrets.md`, `docs/arc2/screenplay_v2.md` (2.16a, 2.17a, 2.21-2.26) and
`docs/story/arc3_screenplay.md` (3.4-3.18).

Darren (the player, girl or boy) is silent apart from menu choices. No line assumes the player's gender.

## How to read this file

Same rules as `docs/arc2/screenplay_v2.md`:

- **Dialogue blocks** are the ```` ```text ```` fences. Each line is one line of the 27-tile text box (max 197 px;
  every line here was measured with `res/fonts/font_message.json` widths). Consecutive lines are one box (at most 2
  lines). A line `--` is a box break inside the same message (`\r`). A blank line starts a new message (a new
  `res/text` entry).
- Named characters start with `Name: ` (Looker, Cyrus, Ruth, Indra, Eclipse Grunt in cutscenes). Townspeople,
  believers and trainers' TRMSG lines have no speaker, as in stock Platinum. Messages with no speaker that read like
  description are signs or narration.
- `{PLAYER}` is the player's name (`BufferPlayerName 0`, then `{STRVAR_1 3, 0, 0}`).
- `[brackets]` are directives: `[YESNO]`, `[Yes]`/`[No]` branches, `[A]`..`[F]` state bands.
- *Italic bullets* are stage directions in stock-script terms. Exact tiles are the layout/raid-maps owners' call.
- Role tags in `CAPS` (`TENT_CLERK`) are object-event ids for the layout workstream (prefix them with
  `SOLACEON_TOWN_` or the interior's map name). Sprites in the cast tables are suggestions from
  `generated/object_events_gfx.txt`.

## State bands

Every NPC below is keyed on one of these bands. Town-scripts picks the band once per map load (`OnTransition`) and
shows/hides objects with the `FLAG_SOL_TOWN_*` / `FLAG_SOL_SANCTUARY_*` flags (town-scripts allocates them; PLAN
section 2).

| Band | When | Test | What the player sees |
|---|---|---|---|
| **A** | Arc 2, first visit | `VAR_ARC2_PROGRESS` 44-53 (also below 44, a sequence break) | Pilgrim season. Warm. Sanctuary open, tent queue, kennel full, banners from 47. |
| **B** | Arc 2, after the depot | `VAR_ARC2_PROGRESS` 54-85 | Robed grunts at the gate and the dig fence. Records office locked. Kennel thinning. |
| **C** | Arc 2, after Rowan's retraction | `VAR_ARC2_PROGRESS` 86-98 | Rowan banners torn down. Some believers leave. |
| **D** | Arc 3, before the raid | `VAR_ARC2_PROGRESS` 99 and `VAR_SOLACEON_PROGRESS` 0-19 | Sanctuary shut "for the Return". Believers wait at the wall. Trucks at night. At 10, Looker and Cyrus wait at the plaza. |
| **R** | The raid | `VAR_SOLACEON_PROGRESS` 20-49 | Gate open (the guards are "at lunch"), Looker in the office, the dig pair beaten. |
| **E** | After the raid | `VAR_SOLACEON_PROGRESS` 50 | Sanctuary seized by the International Police. The wall stays; believers mourn. |
| **F** | Postgame | `FLAG_GAME_COMPLETED` (the raid is mandatory, so progress is 50) | The memorial garden. |

> Note: C vs D. Arc 3 has no progress var of its own yet (`VAR_ARC3_PROGRESS` is reserved, do not use). Until the
> Arc 3 work exists, `VAR_ARC2_PROGRESS` 99 is both "end of Arc 2" and "Arc 3 before the raid". Town-scripts:
> treat 86-98 as C and 99 as D. That makes D the end-of-content state for today's test saves, which is right: by
> 99 the player has the Relic Badge and Arc 3 opens next.

The existing 2.16a content stays exactly as built: the five wall signs (photos, Ponyta drawing, ELIAS, the WHO DID
YOU LOSE? banner, TEO from 49) and the Indra cutaway at 44 (Indra at (557,654), `FLAG_UNK_0x0030`). The Arc 2
quests content stays: the Rowan banners (`FLAG_UNK_0x0031`) and the Pokemon Center viewer and TV lines. Their only
change is in band C and later (below: the Rowan banners come down at 86).

## Cast by zone (for layout)

Zones are PLAN section 4. "Bands" lists where the object is shown; outside those bands it is hidden.

### Zone 1: the pilgrim road and the registration tent

| Role | Sprite (suggested) | Bands | Who |
|---|---|---|---|
| `TENT_CLERK` | `MIDDLE_AGED_WOMAN` | A B C D E (in F she is `GARDEN_KEEPER`) | Believer volunteer behind the tent table. Writes every name. Kind, tired. |
| `PILGRIM_FATHER` | `MIDDLE_AGED_MAN` | A (queue), B C D E (at the wall instead), F (garden) | The Route 202 father; his daughter's Ponyta drawing is on the wall. |
| `PILGRIM_SAILOR` | `SAILOR` | A (queue), F (garden) | The Route 202 sailor; his Machoke drowned saving him. |
| `PILGRIM_SISTER` | `LASS` | A (queue), C (leaving), F (garden) | The Route 202 sister; older now than her big brother got to be. |
| `PILGRIM_SON` | `YOUNGSTER` | A (queue), D (at the tent) | The Route 202 son; his mom is only half a thumb in the photos. |
| `ROAD_GREETER` | `LADY` | A B | Believer handing out flyers between the banner posts. |

### Zone 2: the memorial plaza and the garden of names

| Role | Sprite | Bands | Who |
|---|---|---|---|
| `WALL_WIDOW` | `OLD_WOMAN` | all | Comes to the wall every day. Her husband's card is the first one up. |
| `GARDEN_GIRL` | `TWIN` | A C E F | Plays at the edge of the grass patch, watching the Yamask. |
| `LANTERN_MAN` | `OLD_MAN` | all | Lights the plaza lanterns. Town memory (stock "nothing but a road" line, kept). |
| `BELIEVER_MOTHER` | `MIDDLE_AGED_WOMAN` | all | Lost her son. The kindest believer in town, and the most certain. |
| `LOOKER` (raid) | `LOOKER` | D at progress 10 only | Waiting at the wall, "in disguise". |
| `CYRUS` (raid) | `CYRUS` | D at progress 10 only | Beside Looker. |

### Zone 3: the Sanctuary compound (exterior)

| Role | Sprite | Bands | Who |
|---|---|---|---|
| `GATE_GREETER` | `LADY` | A | Robed believer at the open gate. |
| `GATE_GRUNT_L`, `GATE_GRUNT_R` | `ECLIPSE_GRUNT_M`, `ECLIPSE_GRUNT_F` | B C D | Robed grunts either side of the gate. Not trainers; they block the gate in D. |
| `FORECOURT_SWEEPER` | `OLD_MAN` | A B C | Believer sweeping the eclipse emblem in the paving. |
| `IP_OFFICER_GATE` | `POLICEMAN` | E | International Police at the gate. |
| `IP_OFFICER_COURT` | `POLICEMAN` | E | Carrying boxes across the forecourt. |

### Zone 4: the excavation (the Ruins hill)

| Role | Sprite | Bands | Who |
|---|---|---|---|
| `DIG_WORKER` | `WORKER` | A, F | Hired local digger (A); works for real archaeologists in F. |
| `EXCAVATION_GRUNT_M` | `ECLIPSE_GRUNT_M` | B C D (not a trainer), R (trainer `SOL_07`, then stays beaten) | The fence pair, at the gap. Same two people from 54 to the raid. |
| `EXCAVATION_GRUNT_F` | `ECLIPSE_GRUNT_F` | B C D (not a trainer), R (trainer `SOL_08`, then stays beaten) | |
| `RUIN_MANIAC` | `RUIN_MANIAC` | A, E, F | Digs the Maniac Tunnel. Furious about the fence (A); Indra used his tunnel (E). |
| `IP_OFFICER_DIG` | `POLICEMAN` | E | At the fence gap. |

### Zone 5: the ranch (Day Care, kennel block, loading yard)

| Role | Sprite | Bands | Who |
|---|---|---|---|
| `KENNEL_KEEPER` | `COWGIRL` | all | Local woman the Sanctuary pays to run the kennel. Loves the Pokemon. Never asked where the trucks went. |
| `KENNEL_MON_1..4` | `SKITTY`, `PSYDUCK`, `MACHOP`, `STARLY` | A: 1-4; B: 1-2; C: 1; D: none; E: 1; F: 1-4 | Kennel Pokemon (cry on talk, no text). |
| `LOADING_GRUNT` | `ECLIPSE_GRUNT_M` | B D | At the truck in the loading yard. Not a trainer. |
| `RANCHER` | `RANCHER` | all | Stock ranch hand by the pens (keeps the Buneary and Pachirisu objects). |
| `DAYCARE_KID` | `TWIN` | all | Stock "I'm too little" line, unchanged. |

### Zone 6: believers' houses

| Role | Sprite | Bands | Who |
|---|---|---|---|
| `SUNDAY_MAN` | `GENTLEMAN` | all | Stock "Every Sunday, I visit the Lost Tower" man, given a reason. |
| `DOUBTER` | `MIDDLE_AGED_MAN` | A B C (packing), E F | Lost his wife. Doubts first; leaves in C, comes back in E. |
| `POKETCH_MAN` | `EXPERT_M` | all | Stock Pokemon History app giver. Stock text, unchanged (gameplay). |

### The Sanctuary hall interior (new map; sanctuary-interior places these)

| Role | Sprite | Bands | Room |
|---|---|---|---|
| `SPEAKER` | `MIDDLE_AGED_WOMAN` (robed) | A B C | Public hall, at the lectern. |
| `HALL_ATTENDANT` | `LADY` | A | Public hall, by the door. |
| `TESTIMONY_A` | `OLD_MAN` | A B | Public hall, front bench. |
| `TESTIMONY_B` | `ACE_TRAINER_F` | A C | Public hall, middle bench. |
| `TESTIMONY_C` | `SCHOOL_KID_M` | A B C | Public hall, back bench. |
| `RECORDS_CLERK` | `SCIENTIST_F` | A (in F she is `READING_KEEPER`) | Records office, at the filing drawers. |
| `HALL_GRUNT` | `ECLIPSE_GRUNT_F` | B C | Public hall, at the records office door (blocks it). |
| `BACK_DOOR_GRUNT` | `ECLIPSE_GRUNT_M` | B C | Public hall, at the locked back door. |
| `LOOKER` | `LOOKER` | R (20-39) | Records office, at Indra's desk. |
| `IP_OFFICER_HALL` | `POLICEMAN` | E | Public hall. |
| `IP_OFFICER_OFFICE` | `POLICEMAN` | E | Records office. |
| `LAST_BELIEVER` | `TESTIMONY_A`'s sprite | E | Public hall, front bench (same man as `TESTIMONY_A`). |
| `READING_KEEPER` | `SCIENTIST_F` | F | Records office (same woman as `RECORDS_CLERK`). |

In band D the Sanctuary door is shut (see the door message below); the interior is not entered until R.

---

# Part 1: Signs

All signs are `bg_events` (or signboard objects where layout prefers). One text per band; if a band is not listed,
use the nearest earlier band.

**Town sign** (stock `ShowMapSign 12`, unchanged in every band; the irony does the work):

```text
Solaceon Town
Free of Worry!
```

**Sanctuary gate plaque** (Zone 3, beside the gate):

```text
[A]
THE SOLACEON SANCTUARY
Team Eclipse
--
No one you love is ever truly
gone.

[B C]
THE SOLACEON SANCTUARY
Team Eclipse
--
No one you love is ever truly
gone.
--
Visitors: the hall only, please.

[D R]
A notice over the plaque:
--
CLOSED FOR THE RETURN.
Keep your cards close.
--
Wait for us by the wall.

[E]
SEIZED BY ORDER OF THE
INTERNATIONAL POLICE.
--
The old plaque is still under the
notice.

[F]
The plaque is gone. Four bolt
holes, and a small sign:
--
GARDEN OPEN. COME IN.
```

**Sanctuary hall door** (band D only, when the player tries the door; the door warp is disabled in D):

```text
The doors are locked. A card is
tucked in the handle:
--
CLOSED FOR THE RETURN.
```

**Tent sign** (Zone 1, on the tent post):

```text
[A B C]
REGISTRY OF THE DEPARTED
--
Tell us who you lost.
We will write down every name.

[D R]
REGISTRY CLOSED.
ALL NAMES ARE KEPT.

[E]
The tent is empty. A police notice
is taped to the post.

[F]
WRITE A NAME. TAKE A CANDLE.
--
No charge. No promises.
```

**Excavation warning sign** (Zone 4, on the fence):

```text
[A]
SOLACEON RUINS EXCAVATION
The Sanctuary
--
Visitors welcome in the first
room. Please mind the crates.

[B C D R]
EXCAVATION. KEEP OUT.
--
Unstable ruins.
By order of the Sanctuary.

[E]
EXCAVATION CLOSED.
International Police.

[F]
SOLACEON RUINS
--
Open to visitors.
Mind the rubble.
```

**Kennel sign** (Zone 5, on the kennel block):

```text
[A]
KENNEL OF THE DEPARTED
--
Their Pokemon wait here for new
homes. Ask the keeper.
--
The Sanctuary

[B C]
KENNEL OF THE DEPARTED
--
Their Pokemon wait here for new
homes. Ask the keeper.
--
Adoptions paused.

[D R]
KENNEL OF THE DEPARTED
--
CLOSED.

[E]
KENNEL OF THE DEPARTED
--
Someone has scratched out the
last word.

[F]
SOLACEON KENNEL
--
Every Pokemon here goes home.
```

**Rowan banners** (the Arc 2 quests signboards, `FLAG_UNK_0x0031`): band A-B as built (from 47). From 86 the
banners are torn down; town-scripts shows the same two signboard objects with this text instead (or a new object;
their call):

```text
[C D R E]
A torn banner. Only one word is
left: POSSIBLE.

[F: hidden]
```

**The wall banner** (2.16a sign, `SolaceonTown_Text_Arc2WallBanner`): unchanged through D and R. From E:

```text
[E]
The banner is down. Someone has
folded it and left it by the wall.

[F]
The banner is gone. Fresh flowers
where it used to hang.
```

**Postgame memorial plaque** (Zone 2, a new sign at the head of the plaza, band F only):

```text
THE GARDEN OF NAMES
--
For everyone whose name was
written on this wall,
--
and for every Pokemon that was
taken in their name.
--
They are not coming back.
They are remembered.
```

---

# Part 2: The town, band by band

Each band lists who is out, then their lines. Roles not listed in a band are hidden.

## Band A: pilgrim season (44-53)

- *Out: `TENT_CLERK`, `PILGRIM_FATHER`, `PILGRIM_SAILOR`, `PILGRIM_SISTER`, `PILGRIM_SON` (in the tent queue),
  `ROAD_GREETER`, `WALL_WIDOW`, `GARDEN_GIRL`, `LANTERN_MAN`, `BELIEVER_MOTHER`, `GATE_GREETER`,
  `FORECOURT_SWEEPER`, `DIG_WORKER`, `RUIN_MANIAC`, `KENNEL_KEEPER`, `KENNEL_MON_1..4`, `RANCHER`, `DAYCARE_KID`,
  `SUNDAY_MAN`, `DOUBTER`, `POKETCH_MAN`. Rowan banners from 47 (as built). The 2.16a cutaway plays first (44).*
- *Everyone here is kind. Nobody has proof of anything. The menace is only for the player.*

`TENT_CLERK`:

```text
Welcome. Are you here to register
someone?
--
Take your time. Nobody here is in
a hurry.

Name, date, and place. That's all
we ask.
--
Some people talk for an hour.
I write it all down.
```

`PILGRIM_FATHER` (the Route 202 father):

```text
I've seen you before. On the road
to Jubilife, I think.
--
I brought her drawing all this
way. It's on the wall now.
--
Right in the middle. The Ponyta
one. She'd like that.
```

`PILGRIM_SAILOR`:

```text
Third time in this line. I keep
getting to the front
--
and walking away.
--
How do you write down a Machoke
who hated boats?
```

`PILGRIM_SISTER`:

```text
They asked how old he was.
--
I said nineteen. Then I said he's
still nineteen.
--
The lady wrote that down too.
```

`PILGRIM_SON`:

```text
I'm putting up the thumb photo.
--
It's the only one with any of
Mom in it. Half a thumb counts.
```

`ROAD_GREETER`:

```text
Welcome to Solaceon! Here, take a
flyer.
--
WHO DID YOU LOSE?
--
You don't have to answer. Most
people don't, the first time.
```

`WALL_WIDOW`:

```text
That card at the top is my
husband's. First one up.
--
Every morning I come and say hello.
--
The Sanctuary people bring me tea.
They're so kind here.
```

`GARDEN_GIRL` (by the grass patch):

```text
There are Yamask in the grass.
--
Grandma says each one carries a
face. The face of who it was.
--
I keep looking for Grandpa's.
```

`LANTERN_MAN` (stock msg 8, kept, plus a second message):

```text
There used to be nothing here but
a road that went straight through.
--
Over time, Pokemon and people just
gathered, and the town came to be.

Now it's lanterns. I light one for
every new card.
--
I've run out of oil twice this
month.
```

`BELIEVER_MOTHER`:

```text
My boy would be about your age.
--
Team Eclipse says he can come home.
Not a memory. Him.
--
I know how that sounds. I don't
care how it sounds.
```

`GATE_GREETER`:

```text
The Sanctuary is open to everyone.
Come in, sit, stay as long as
--
you like.
--
Nobody in there will tell you to
move on.
```

`FORECOURT_SWEEPER`:

```text
The black sun in the paving. That's
the eclipse.
--
The sun goes dark for a while, and
then it comes back.
--
That's the whole idea, they told
me.
```

`DIG_WORKER`:

```text
The Sanctuary hired a few of us to
dig. Pays well.
--
We clear the first room. The deep
rooms are for their own people.
--
Lot of crates for an old ruin.
```

`RUIN_MANIAC`:

```text
They fenced off MY ruins!
--
I've been digging a tunnel out of
there for years. Years!
--
Now I need a pass to visit my own
tunnel.
```

`KENNEL_KEEPER`:

```text
Their trainers passed away, so the
Sanctuary takes them in.
--
I feed them, brush them, tell them
their names.
--
Every week a truck comes and takes
some to new homes. In the city.
```

`RANCHER` (by the pens):

```text
Busy season. Pilgrims all week.
--
They all stop and watch the
Buneary. I think it helps.
```

`SUNDAY_MAN` (stock msg 7, plus a second message):

```text
Every Sunday, I visit the Lost
Tower...

My wife's grave is up there.
--
The rest of the week, I come to the
wall. It's closer.
```

`DOUBTER`:

```text
My wife's card is on that wall.
I put it there myself.
--
I just keep wondering who pays for
all of this.
--
Hope doesn't run trucks.
```

`DAYCARE_KID` and `POKETCH_MAN`: stock text, unchanged.

`KENNEL_MON_1..4`: cry only (`PlayCry`, then `WaitCry`), no text.

## Band B: security (54-85)

- *Changes from A: `GATE_GREETER` and `ROAD_GREETER` gone; `GATE_GRUNT_L/R` at the gate; `EXCAVATION_GRUNT_M/F` at
  the fence gap; `LOADING_GRUNT` at the truck; `KENNEL_MON_3..4` gone; `DIG_WORKER` and `RUIN_MANIAC` gone. The
  Pilgrims have finished registering: `PILGRIM_FATHER` stands at the wall, the others are gone.*
- *The player knows (2.17a) where the crates go. The town does not.*

`TENT_CLERK`:

```text
There are guards now. Did you see?
--
Someone broke into our depot in
Veilstone. Thieves.
--
Who steals from a place like this?
```

`PILGRIM_FATHER` (at the wall):

```text
I meant to go home after I pinned
it up.
--
I keep finding reasons to stay one
more day.
```

`WALL_WIDOW`:

```text
They've put guards at the gate.
Young ones. In robes.
--
One of them carried my chair to the
wall this morning.
```

`GARDEN_GIRL`: hidden in B.

`LANTERN_MAN` (stock msg 8 first, then):

```text
They asked me to stop lighting the
lanterns by the gate.
--
Security. Whatever that means in
a town like this.
```

`BELIEVER_MOTHER`:

```text
Rowan himself said it might be
possible. On the TV!
--
Even the professor who called them
con artists.
--
I knew. I always knew.
```

`GATE_GRUNT_L`:

```text
The hall's open. The back rooms
aren't.
--
Go on in, if you're here to sit.
```

`GATE_GRUNT_R`:

```text
There was a break-in at our depot.
So now there's us.
--
...You look like you've had a long
walk. Go sit down.
```

`FORECOURT_SWEEPER`:

```text
More trucks than pilgrims lately.
--
I sweep up after both.
```

`EXCAVATION_GRUNT_M` (not a trainer; `TRAINER_ECLIPSE_GRUNT_SOL_07` in the raid):

```text
The ruins are closed. Unstable.
Very unstable.
--
Go look at the wall or something.
```

`EXCAVATION_GRUNT_F` (not a trainer; `SOL_08` in the raid):

```text
Excavation business. Sanctuary
business.
--
Not your business.
```

`LOADING_GRUNT`:

```text
Back away from the truck, please.
--
It's donations. For the hall.
...Heavy donations.
```

`KENNEL_KEEPER`:

```text
The truck came at night this time.
Took four.
--
I didn't even get to say goodbye.
--
New homes, they said. That's good.
That's good, isn't it?
```

`RANCHER`:

```text
The trucks cut ruts through my
south pasture.
--
Nobody asked. Nobody here asks
anything anymore.
```

`SUNDAY_MAN`: stock msg 7 and his A line.

`DOUBTER`:

```text
Guards, for a grief hall.
--
I asked one what's in the crates.
He told me to have a nice day.
```

## Band C: the town splits (86-98)

- *Changes from B: Rowan banners replaced by the torn banner sign. `KENNEL_MON_2` gone. `PILGRIM_SISTER` back,
  standing at the north road with a bag (leaving). `DOUBTER` stands at his door with a bag. `GARDEN_GIRL` back.
  `LOADING_GRUNT` gone (the truck is out).*
- *Rowan retracted on TV (Arc 2 quests, 86-99). The town has heard.*

`TENT_CLERK`:

```text
Fewer people in line this week.
--
The professor went on TV and took
it all back.
--
I still write down every name.
That part was never his.
```

`PILGRIM_FATHER`:

```text
The professor says he was wrong.
--
Maybe. But nobody else ever wrote
her name down.
--
I'm not taking the drawing back.
```

`PILGRIM_SISTER` (leaving):

```text
I'm going home.
--
I watched the professor on TV, and
I thought about my brother.
--
If he came back because something
got hurt... he'd hate that.
--
He'd hate it so much.
```

`WALL_WIDOW`:

```text
People are leaving. I heard them
packing last night.
--
I'm not going anywhere. My
husband's card is right there.
```

`GARDEN_GIRL`:

```text
Mom says we might move away.
--
I asked if the Yamask can come.
She didn't answer.
```

`LANTERN_MAN` (stock msg 8 first, then):

```text
Half the lanterns are out. I didn't
put them out.
--
People take their candles with
them when they go.
```

`BELIEVER_MOTHER`:

```text
He was wrong the first time,
calling them con artists.
--
He's wrong now.
--
Somebody scared that old man.
That's all this is.
```

`GATE_GRUNT_L`:

```text
Hall's still open. Still free.
--
Whatever you heard on TV.
```

`GATE_GRUNT_R`:

```text
They tore down the banners with the
professor's words on them.
--
Took me all morning to put them
up, too.
```

`FORECOURT_SWEEPER`:

```text
I sweep the same emblem every day.
--
Lately I sweep it slower. Gives me
time to think.
```

`EXCAVATION_GRUNT_M`:

```text
Some of the believers left this
week.
--
More shifts for us. Great.
```

`EXCAVATION_GRUNT_F`:

```text
Still closed. Still not your
business.
--
Go home, kid.
```

`KENNEL_KEEPER`:

```text
One left. Just the little Skitty.
--
I asked to see the new homes. They
said they'd send photos.
--
They haven't sent any photos.
```

`RANCHER`:

```text
A family from the north road came
to say goodbye to the Buneary.
--
That's how I know who's leaving.
```

`SUNDAY_MAN` (stock msg 7 first, then):

```text
I go to the Lost Tower on Sundays.
To the wall the rest of the week.
--
Now I just go to the tower.
--
At least a grave doesn't promise
anything.
```

`DOUBTER` (at his door, with a bag):

```text
I'm going to my sister's in
Hearthome.
--
I'm leaving the card up. It's
still true. She's still gone.
--
I'm just done waiting for anyone to
say otherwise.
```

## Band D: Arc 3, before the raid ("the Return")

- *Changes from C: the Sanctuary door is locked (door message in Part 1); `FORECOURT_SWEEPER`, `GARDEN_GIRL`,
  `PILGRIM_SISTER`, `DOUBTER` gone; `PILGRIM_SON` back at the tent; `LOADING_GRUNT` back at a full truck;
  `KENNEL_MON_1` gone (the kennel is empty). Believers stand at the wall.*
- *Eclipse holds Dialga (3.3). The Sanctuary has told its people the Return has begun.*
- *At `VAR_SOLACEON_PROGRESS` 10: `LOOKER` and `CYRUS` stand at the plaza by the wall (scene 3.4a part 1).*

`TENT_CLERK`:

```text
The registry's closed. They said
every name is already kept.
--
They said to wait by the wall.
They said it's begun.
--
So we wait.
```

`PILGRIM_FATHER`:

```text
They say the Return has started.
--
I keep looking down the road for a
little girl with a drawing.
--
I know. I know.
```

`PILGRIM_SON` (at the closed tent):

```text
I came back to take the thumb photo
down.
--
Nobody's allowed near the tent.
So I'm just standing here.
```

`WALL_WIDOW`:

```text
They told us to wait by the wall.
So I wait.
--
Forty years I waited for him to
come home from work.
--
I'm good at it.
```

`LANTERN_MAN` (stock msg 8 first, then):

```text
They asked me to light every
lantern tonight. All of them.
--
For the Return.
--
I haven't got the heart to tell
them I'm out of oil.
```

`BELIEVER_MOTHER`:

```text
It's started. Something happened at
a lake. A big thing.
--
They said it was the first step.
--
I made his bed this morning. Just
in case.
```

`GATE_GRUNT_L`:

```text
Sanctuary's closed. For the Return.
--
Wait by the wall like everybody
else.
```

`GATE_GRUNT_R`:

```text
Nobody goes in. Orders from the
registrar herself.
```

`EXCAVATION_GRUNT_M`:

```text
Trucks all night, from the south
road.
--
Don't ask what's in them. I don't.
```

`EXCAVATION_GRUNT_F`:

```text
The Return's coming. We're not
letting anybody spoil it.
--
Especially not you.
```

`LOADING_GRUNT`:

```text
Another load up from the Lost Tower
road.
--
Back off. This stuff hums.
```

`KENNEL_KEEPER`:

```text
They're all gone. Every one.
--
The last truck didn't even stop at
the kennel. It just drove past
--
with the crates rattling.
--
...I keep their bowls out anyway.
```

`RANCHER`:

```text
Ruts so deep now I lost a Buneary
in one.
--
Found her. She was fine. I wasn't.
```

`SUNDAY_MAN` (stock msg 7 first, then):

```text
Everybody's at the wall, waiting.
--
I went up the tower instead.
Somebody should be with the dead.
```

## Band R: during the raid (20-49)

- *Changes from D: `GATE_GRUNT_L/R` hidden (Looker's "long lunch"); the Sanctuary door is open; `LOADING_GRUNT`
  hidden; `LOOKER` is in the records office (interior) until 40; `CYRUS` is in the Ruins. `EXCAVATION_GRUNT_M/F`
  stay at the fence after their battles (scene 3.4a part 2) and use their post-battle lines.*
- *Townspeople are D's, with these lines instead:*

`TENT_CLERK`:

```text
The guards at the gate just...
left. Both of them.
--
I've never seen that gate open
with nobody in it.
```

`WALL_WIDOW`:

```text
There was shouting by the ruins.
--
I'm staying right here. Whatever it
is, it's not for an old woman.
```

`BELIEVER_MOTHER`:

```text
Something's wrong in the ruins.
The ground hums.
--
Is it the Return? Is it starting?
--
...Why are you looking at me like
that?
```

`PILGRIM_FATHER`, `PILGRIM_SON`, `LANTERN_MAN`, `KENNEL_KEEPER`, `RANCHER`, `SUNDAY_MAN`: their D lines.

## Band E: after the raid (50)

- *Changes from R: `IP_OFFICER_GATE`, `IP_OFFICER_COURT`, `IP_OFFICER_DIG` out; `EXCAVATION_GRUNT_M/F` gone
  (arrested); `RUIN_MANIAC`, `GARDEN_GIRL`, `DOUBTER` back; `KENNEL_MON_1` back (the Skitty, found in the loading
  yard); the tent stays up, empty. The wall stays.*
- *The seizure is news. The town knows now what the registry was for.*

`TENT_CLERK` (sitting at the empty tent table):

```text
They took the registry. As
evidence.
--
A police officer told me what the
fourth column was.
--
...I wrote those names. Every one.
I was so careful.
```

`PILGRIM_FATHER`:

```text
They're saying the kennel Pokemon
went into machines.
--
She wanted a Ponyta so badly.
Her own.
--
I'm glad she never had one to
leave behind.
```

`WALL_WIDOW`:

```text
The police said the wall can stay.
That those are our cards.
--
Of course they're our cards.
--
He's still at the top. First one
up.
```

`GARDEN_GIRL`:

```text
Mom says we're staying after all.
--
I told the Yamask. I think it was
happy. It's hard to tell.
```

`LANTERN_MAN` (stock msg 8 first, then):

```text
Nobody asked me to light the
lanterns tonight.
--
I'm lighting them anyway. One for
every card.
--
I bought more oil.
```

`BELIEVER_MOTHER`:

```text
I made his bed again this morning.
--
I don't know how to stop doing
that.
--
...Don't. Don't say anything. I
know.
```

`IP_OFFICER_GATE`:

```text
This building is closed by order of
the International Police.
--
The wall stays. The cards belong to
the families.
```

`IP_OFFICER_COURT`:

```text
Boxes and boxes of records.
--
Every person who walked in here
crying got a file.
```

`IP_OFFICER_DIG`:

```text
The ruins are closed while we
search them.
--
We had every exit watched. Except,
it seems, the one she dug.
```

`RUIN_MANIAC`:

```text
A woman in a black coat came out of
MY tunnel last night!
--
Out of the wall! Dust everywhere!
--
She didn't even say thank you.
```

`KENNEL_KEEPER`:

```text
The police found this Skitty in the
loading yard. In a crate.
--
The last one. They let me keep her
here.
--
I never asked where the trucks
went. I should have asked.
```

`RANCHER`:

```text
The ruts are still there. I'm going
to plant over them.
--
Grass grows over anything, given
time.
```

`SUNDAY_MAN` (stock msg 7 first, then):

```text
People came up the tower today.
Lots of them.
--
Easier to visit a grave than a wall
with a lie on top of it.
```

`DOUBTER` (back from Hearthome):

```text
I heard about the raid in Hearthome
and came straight back.
--
I didn't come back to say I told
you so.
--
I came back because she's still on
that wall.
```

## Band F: postgame (the memorial garden)

- *Changes from E: police gone; the tent is a candle table; the plaza plaque is up (Part 1); `TENT_CLERK` becomes
  `GARDEN_KEEPER` (same sprite, in the plaza); `PILGRIM_FATHER`, `PILGRIM_SAILOR`, `PILGRIM_SISTER` in the garden;
  `DIG_WORKER` at the open Ruins; `KENNEL_MON_1..4` (new rescues).*
- *Optional, NEW (approved 2026-11-24): `INDRA` at the wall, once (see the end of this band).*

`GARDEN_KEEPER` (was `TENT_CLERK`):

```text
I wrote down a thousand names for
them.
--
Now I just plant something for
each one.
--
No promises this time. Only
flowers.
```

`PILGRIM_FATHER`:

```text
I planted a little tree by the
drawing.
--
Next year, I said. Like always.
...This time I mean it.
```

`PILGRIM_SAILOR`:

```text
Finally got to the front of the
line.
--
Wrote MACHOKE on a card and stuck
it in the garden.
--
He'd hate the flowers. I left them
anyway.
```

`PILGRIM_SISTER`:

```text
I came back for the garden.
--
I'm older than him now. By a lot.
--
I think he'd make fun of me for
that. I hope so.
```

`WALL_WIDOW`:

```text
He's still at the top. First one
up.
--
They built a garden around him.
He'd have liked the bench.
```

`GARDEN_GIRL`:

```text
The Yamask live in the garden now.
--
I don't look for Grandpa's face
anymore.
--
I just say hi to all of them.
```

`LANTERN_MAN` (stock msg 8 first, then):

```text
Every lantern, every night. Nobody
asks me to.
--
That's how I know it's for them.
```

`BELIEVER_MOTHER`:

```text
I put his card in the garden.
--
I still talk to him. I just don't
wait for an answer.
```

`DIG_WORKER`:

```text
Real archaeologists now. From
Canalave.
--
They pay worse, but nobody tells
me not to look in the crates.
```

`RUIN_MANIAC`:

```text
They gave me my tunnel back!
--
They even fixed the hole that
woman made. ...Mostly.
```

`KENNEL_KEEPER`:

```text
It's a real shelter now.
--
Every Pokemon here goes to a home
I've seen with my own eyes.
--
I visit every one.
```

`RANCHER`:

```text
Planted over the ruts.
--
Grass came up thick. The Buneary
love it.
```

`SUNDAY_MAN`:

```text
Every Sunday, I visit the Lost
Tower...
--
And every other day, the garden.
--
Turns out I just like being near
her.
```

`DOUBTER`:

```text
I thought being right would feel
better.
--
Mostly I just sit with her card.
```

**Optional, NEW (approved 2026-11-24): Indra at the wall.** Band F, once (town-scripts flag). Indra stands at the wall
(her 2.16a spot), coat off (the 3.14 look). Talking to her:

```text
Indra: ...You.
--
Don't worry. I'm not here for
anything.

Indra: I wrote down everyone's
place. Every card on this wall.
--
Except his.

Indra: I'm writing it now.
```

- *She pins a card next to TEO's, walks away down the south road (hide), and never comes back. The TEO sign gets a
  second text from then on:*

```text
TEO. A boy, smiling. A second card
beside it, in neat writing:
--
Go live. For both of us.
```

> Note: Pays off the blank place on Teo's filed card (records office, band A) and the ledger page in 3.4a, and
> repeats Teo's 3.11 words in Indra's hand. It shows Indra free in the postgame; the bible doesn't say where she
> goes after 3.14. Drop it if the owner wants her gone after 3.14.

---

# Part 3: The Sanctuary hall interior

New map (sanctuary-interior). Three areas: the **public hall** (benches, the lectern, the eclipse emblem), **Indra's
records office** (filing drawers, Indra's desk, the ledger), and a **locked back door** (staff only; it never
opens in game).

**Signs inside (all bands unless noted):**

```text
[Lectern, A B C]
A lectern with a black sun carved
in the front.
--
A note on it: TONIGHT, SHARE ONE
MEMORY. THAT'S ALL.

[Lectern, E]
The lectern is wrapped in police
tape.

[Lectern, F]
The black sun has been sanded off.
Someone carved a flower instead.

[Notice board, A B C]
GRIEF CIRCLE, EVERY EVENING.
--
Tea after. Everyone welcome.

[Filing drawers, A]
Drawer after drawer of cards. Each
one has a name, a date, a place.

[Filing drawers, E]
The drawers are empty. Police
labels on every one.

[Filing drawers, F]
The drawers are open. A note:
--
TAKE YOUR CARD HOME IF YOU WANT
IT. ASK AT THE DESK.

[The ledger, A: on the clerk's desk]
A thick ledger. Names, dates and
places, in neat rows.
--
There's a fourth column, in smaller
writing.
--
The clerk closes the book before
you can read it.

[Indra's desk, A]
A tidy desk. One card on it, not
filed yet:
--
TEO. The date is written in.
--
The place is left blank.

[Indra's desk, E]
The desk is bare. The police took
everything but the chair.

[Back door, A]
STAFF ONLY.

[Back door, B C D R]
STAFF ONLY. KEEP OUT.
--
It's locked.

[Back door, E]
Police seal. It's locked.

[Back door, F]
Bricked up. Someone has chalked a
flower on the bricks.
```

> Note: The ledger (A) and Teo's card (A) are the plants for the 3.4a ledger pages. In B and C the records office
> is locked (`HALL_GRUNT` at its door), so the player sees them only in A or R.

## Band A

`SPEAKER` (at the lectern):

```text
Welcome. Sit anywhere.
--
Nobody here will tell you to let
go. Hold on as tight as you like.
--
Team Eclipse is working on the
rest.
```

`HALL_ATTENDANT`:

```text
Tea's at the back. Cards are by
the door, if you want one.
--
Write a name. Pin it on the wall
outside. It helps.
```

`TESTIMONY_A`:

```text
I stood up and talked about my
wife last night.
--
Forty minutes. Nobody looked at the
clock.
--
I didn't know I had forty minutes
in me.
```

`TESTIMONY_B`:

```text
My Luxray. Eight years together.
--
People say it was just a
Pokemon.
--
Nobody here says that.
```

`TESTIMONY_C`:

```text
My grandpa taught me to fish.
--
They said when he comes back, he
can teach me the rest.
--
I'm saving the hard parts for him.
```

`RECORDS_CLERK` (records office):

```text
Every card on the wall has a twin
in here.
--
We copy them all into the ledger.
In case the rain gets them.
--
The registrar is very particular.
Every name. Every detail.
```

## Band B

- *`HALL_ATTENDANT` and `TESTIMONY_B` gone. `HALL_GRUNT` blocks the records office door; `BACK_DOOR_GRUNT` stands at
  the back door. `RECORDS_CLERK` is in the locked office (unreachable).*

`SPEAKER`:

```text
Welcome. Sit anywhere.
--
Don't mind the guards. Someone
broke into our depot.
--
Grief makes people do strange
things. Even steal.
```

`TESTIMONY_A`:

```text
They locked the back rooms. Fine.
I only need the bench.
```

`TESTIMONY_C`:

```text
Professor Rowan said it might be
possible!
--
I'm telling Grandpa the second he's
back.
```

`HALL_GRUNT`:

```text
Records office is closed. Staff
only.
--
The hall's open. Sit down. Have
some tea.
```

`BACK_DOOR_GRUNT`:

```text
That door's for staff. Always has
been.
```

## Band C

- *`TESTIMONY_A` gone. `TESTIMONY_B` back, on her feet, about to leave. Fewer benches filled.*

`SPEAKER`:

```text
The professor was frightened. That
is all.
--
Frightened men take things back.
--
We don't. We keep everything.
```

`TESTIMONY_B`:

```text
The professor said not to let his
name sell their promise.
--
I keep thinking about how they'd
bring my Luxray back.
--
What would it cost? Who would pay
it?
--
I'm going home.
```

`TESTIMONY_C`:

```text
Mom says the professor was wrong.
--
I don't care. I'm saving the hard
parts for Grandpa.
```

`HALL_GRUNT`, `BACK_DOOR_GRUNT`: their B lines.

## Band D

The doors are locked (Part 1). Nobody is inside.

## Band R (20-49)

- *The hall is empty. `LOOKER` sits at Indra's desk in the records office, reading, until 40. From 40 he is in the
  vault (hidden here).*

`LOOKER`:

```text
Looker: Not now. I am reading.
--
This registrar keeps very good
records. Too good.

Looker: Go. The door under the
ruins. I will find you.
```

## Band E

- *`IP_OFFICER_HALL`, `IP_OFFICER_OFFICE` out. `LAST_BELIEVER` (the `TESTIMONY_A` man) on the front bench.*

`LAST_BELIEVER`:

```text
I came to say my piece anyway. Like
every evening.
--
Forty minutes about my wife.
--
...Nobody's at the lectern. I'll
just talk to the bench.
```

`IP_OFFICER_HALL`:

```text
We're cataloguing everything. It'll
take weeks.
--
They kept a file on every person
who ever cried in here.
```

`IP_OFFICER_OFFICE`:

```text
The registrar's office. She left in
a hurry, but nothing was out of
--
place. Not one card.
```

## Band F

- *`READING_KEEPER` (the `RECORDS_CLERK` woman) in the office. The hall is open; nobody speaks at the lectern.*

`READING_KEEPER`:

```text
I copied every card into that
ledger. I thought I was helping.
--
Now I give them back. One family at
a time.
--
It's slower. It's better.
```

---

# Part 4: Scene 3.4a, the Solaceon raid

New scene between 3.4 (Hearthome, the morning after) and 3.5 (Canalave). Owners: **town-scripts** (parts 1, 2, 7:
`solaceon_town`, the Sanctuary interior), **raid-scripts** (parts 3-6: `solaceon_ruins_*`). Party: Looker leads;
Cyrus goes with Darren; Ruth is on the Poketch (message boxes, no phone UI, as in 2.25). Garius is with Kahn, not
here.

**Story job.** Looker has traced the vein's shards (the Lost Tower, 2.25-2.26) up Route 209 to a vault under the
Ruins. Breaking it is meant to buy time before Palkia. It does break, but Kahn already left with enough (so 3.6
happens), and the town's kindness turns out to have fed the frames.

**The mechanic (fixed with raid-maps; PLAN section 1).** The vault in Room 7 is sealed by a shard-powered barrier
fed by three generators in Ruins dead-end rooms. Beat the guard in each, switch the generator off, and the barrier
drops. Generators can be done in any order.

**Progress and flags (proposal; raid-scripts owns 31-39 and `FLAG_SOL_RAID_*` and may rename).**

| Value / flag | Set when | Used for |
|---|---|---|
| `VAR_SOLACEON_PROGRESS` 10 | end of 3.4 (future Arc 3 work; test saves set it) | Looker and Cyrus appear at the plaza |
| 20 | Looker's briefing ends (part 1) | band R; the dig pair turn into trainers |
| 30 | first entry into Ruins Room 1 at 20 (part 3) | Cyrus's Room 1 lines once |
| 31, 32, 33 | each generator switched off (`AddVar` 1) | Ruth's count line; 33 drops the barrier |
| `FLAG_SOL_RAID_A`, `_B`, `_C` | generator A, B, C switched off | the generator's own state (off look, "already off" text) |
| `FLAG_SOL_RAID_D` | at 33 | hides the barrier object(s) |
| 40 | first step into the vault past the barrier (part 5) | Indra's scene |
| 45 | Indra beaten | aftermath |
| `FLAG_SOL_RAID_E` | the racks drained (part 6) | the racks' grey look; hides Indra's tunnel-rubble trigger |
| 50 | the seizure (part 7) | band E |

**Trainer placement (raid-maps places the objects; `trainers.md` has the teams).**

| Trainer | Where | Role tag |
|---|---|---|
| `TRAINER_ECLIPSE_GRUNT_SOL_07` (M) | Town, Zone 4, the fence gap | `EXCAVATION_GRUNT_M` (same object as bands B-D) |
| `TRAINER_ECLIPSE_GRUNT_SOL_08` (F) | Town, Zone 4, the fence gap | `EXCAVATION_GRUNT_F` |
| `TRAINER_ECLIPSE_GRUNT_SOL_01` (M) | Room 1, main path | `RAID_DIGGER` |
| `TRAINER_ECLIPSE_GRUNT_SOL_02` (F) | Generator A dead end | `RAID_GEN_A_GUARD` |
| `TRAINER_ECLIPSE_GRUNT_SOL_03` (M) | Room 3, main path | `RAID_TECH` |
| `TRAINER_ECLIPSE_GRUNT_SOL_04` (F) | Generator B dead end | `RAID_GEN_B_GUARD` |
| `TRAINER_ECLIPSE_GRUNT_SOL_05` (M) | Room 5, main path | `RAID_VAULT_WATCH` |
| `TRAINER_ECLIPSE_GRUNT_SOL_06` (F) | Generator C dead end | `RAID_GEN_C_GUARD` |
| `TRAINER_INDRA_SANCTUARY` | Room 7, the vault | `RAID_INDRA` |

Generator rooms: the text never names a room, so raid-maps can pick any three dead ends. Suggested spread (one per
stretch of the route): A = Room 2 northeast dead end, B = Room 4 southeast dead end, C = Room 6 northwest dead end.
Grunts 07-08 are the dig pair: non-battle fence guards from 54 to the raid, trainers at 20. Using the same two
people pays off three bands of "not your business".

## 3.4a part 1: the plaza, Looker's briefing

Owner **town-scripts** | `solaceon_town` | reads **10** | sets **20**

- *Band D town. `LOOKER` (plain coat, a wide hat) and `CYRUS` stand at the plaza by the wall. Talking to either, or
  a coord ring around them (town-scripts' call), starts the scene. Both face the player.*

```text
Looker: Do not be alarmed. It is me.
--
I am in disguise. A pilgrim.

Cyrus: He bought a hat.

Looker: Ruth followed the readings
for me. From the Lost Tower,
--
up Route 209, to here. Every night
since the vein.

Looker: The shards come here.
--
Under the ruins. Under their
so-called excavation.
--
They keep them in a vault.

Looker: Kahn needs shards to hold
Palkia. A great many.
--
If we break the vault, we buy
time. Maybe enough.

Cyrus: The vault is sealed. I can
feel it from here.
--
Something under those ruins is
holding a door shut. It hums.

Looker: Then, the plan.
--
I go into the Sanctuary. The
registrar's office. Her records.
--
You two go into the ruins and open
that door.

Looker: The guards at the gate are
at lunch. A long lunch.
--
I arranged it.

Looker: Ruth will listen on the
Poketch. If it goes badly, run.
--
It is a good plan. I made it this
morning.
```

- *`FadeScreen`; heal the party (as 2.21a); set **20**. Fade in: `LOOKER` is gone (hidden; he is in the records
  office now), `GATE_GRUNT_L/R` hidden, the Sanctuary door open. `CYRUS` stands by the excavation fence, a few
  tiles from the dig pair, facing it.*

## 3.4a part 2: the dig fence (grunts 07 and 08)

Owner **town-scripts** (script) / **raid-scripts** (trainer data) | `solaceon_town` | reads **20**

- *Walking up to the fence gap (coord trigger in front of `EXCAVATION_GRUNT_M/F`). Cyrus walks up beside the
  player.*

```text
Eclipse Grunt: The dig's closed.
It's been closed for weeks.
--
Turn around.

Eclipse Grunt: Hey. Wait.
--
That's him. The one who walked
out.

Eclipse Grunt: Then nobody's
walking in. Get them!
```

- *Battle `TRAINER_ECLIPSE_GRUNT_SOL_07`, then `TRAINER_ECLIPSE_GRUNT_SOL_08` (singles, back to back; heal is not
  given between). Losing either: stock whiteout, the pair reset. After both, they step aside one tile each and
  stay (post-battle lines below until 50).*

```text
Cyrus: They knew my face.
--
Garius told them everything. Of
course he did.

Cyrus: Come. The hum is louder
here.
```

- *Cyrus walks through the gap into the Room 1 entrance (hide). The fence gap is open from now on.*

## 3.4a part 3: Ruins Room 1, Cyrus and the lines

Owner **raid-scripts** | `solaceon_ruins_room_1` | reads **20** | sets **30**

- *First entry at 20 sets 30. The room is dressed (crates, work lights, cables running deeper; raid-maps). `CYRUS`
  stands a few tiles in, facing the wall, a hand on the stone.*

```text
Cyrus: That hum. I know it.
--
I heard it in my own machines,
a long time ago.

Cyrus: The door below is fed from
three places. Three lines.
--
I can feel them, like seams.
--
Cut all three, and it falls.

Cyrus: I'll go ahead to the door
and read it. You find the lines.
```

- *The Poketch buzzes (sound effect, then narration).*

```text
The Poketch buzzes.

Ruth: Can you hear me? I've got the
shard readings up!
--
Three strong sources, deeper in.
And one huge one at the bottom.
--
That has to be the vault.
--
...Be careful. Please.
```

- *Cyrus walks deeper (hide). He waits at the barrier (part 5). `RAID_DIGGER` (`SOL_01`) stands on the main path
  ahead (eye-contact trainer).*

## 3.4a part 4: the generators

Owner **raid-scripts** | the three generator dead ends | reads **30-32** | sets **31**, **32**, **33**,
`FLAG_SOL_RAID_A/B/C`, `_D`

- *Each generator dead end: a generator object wired to a rack of violet shards (`OBJ_EVENT_GFX_SHARD_FRAME` /
  `VIOLET_CRYSTAL` dressing), and a guard grunt in front of it (eye-contact trainer: A `SOL_02`, B `SOL_04`, C
  `SOL_06`). The guard blocks the generator until beaten.*
- *Talking to a generator that is on:*

```text
A machine wired to a rack of violet
shards. It hums. The air is warm.
--
Switch it off?
[YESNO]

[Yes]
{PLAYER} switched the machine off.
--
The shards on the rack go dim.

[No: nothing happens; the machine keeps humming]
```

- *On Yes: set that generator's flag, `AddVar VAR_SOLACEON_PROGRESS 1`, sound (`SEQ_SE_DP_*` power-down), swap to the
  "off" look. Then the Poketch, by the new value:*

```text
[31]
The Poketch buzzes.

Ruth: One of the sources just
dropped! Two to go.

[32]
The Poketch buzzes.

Ruth: That's two! The big one at the
bottom is flickering now.

[33]
The Poketch buzzes.

Ruth: All three are down! The
reading on the vault door
--
just went flat!
--
Go. Before somebody switches them
back on.
```

- *At 33 also set `FLAG_SOL_RAID_D` (the barrier object hides on Room 7's next load, or at once if raid-maps puts
  the barrier in view).*
- *Talking to a generator that is off:*

```text
The machine is off. The shards on
the rack are dim.
```

## 3.4a part 5: the barrier and the vault, Indra

Owner **raid-scripts** | `solaceon_ruins_room_7` (or Room 6 at its door to 7; raid-maps' call) | reads **30-33** |
sets **40**, **45**

**The barrier.** `CYRUS` stands at it, facing it.

```text
[30-32, talking to Cyrus]
Cyrus: Not yet. Something is still
feeding it.
--
Find the other lines.

[30-32, walking into the barrier]
A wall of violet light. It hums.
It won't let you through.

[33, talking to Cyrus]
Cyrus: It's down.
--
Someone is in there. Waiting.
```

- *At 33 Cyrus moves aside. The first step past the barrier line sets **40** and starts the vault scene.*

**The vault (40).** Racks of violet shards fill the room (raid-maps' vault dressing), crates stamped with the
black sun, and at the back a rough hole in the wall (a fresh tunnel, dark). `RAID_INDRA` stands at the main rack
with her back turned. Cyrus walks in behind the player.

```text
Indra: You turned off all three.
--
Do you know how long it took to
grow what's on these racks?
```

- *She turns.*

```text
Indra: Rowan's kid. The one from the
depot.
--
I told you to go home.

Indra: And the man who walked out.
Garius told us all about you.

Cyrus: ...

Indra: You're late, by the way.
--
Kahn came for his share at dawn.
He took what he needs.
--
Palkia's as good as his. This is
just what's left.

Indra: Saros wanted a morning. He
has his clock now.
--
Kahn wants a door. He'll have it
soon.

Indra: And I keep the door. That's
all I've ever done.
```

- *Battle: `TRAINER_INDRA_SANCTUARY`. Losing: stock whiteout to the Solaceon Center; progress stays 40 and the
  scene replays from "You turned off all three." Winning sets **45**.*

```text
Indra: Hm.
--
Still fighting like somebody who's
never lost anything.
```

- *Indra turns to Cyrus.*

```text
Indra: You. You held Dialga and
Palkia once. In your world.
--
And something stopped you.
--
What was it?

Cyrus: ...

Indra: Keep it, then.
--
I'll find it without you.
```

- *She walks to the hole in the back wall and stops at the edge.*

```text
Indra: Don't follow me. The roof
in here doesn't like visitors.
```

- *She goes in (hide). A rumble (screen shake), dust (flash): rubble fills the hole (show a rock object; raid-maps
  places it). Indra is not caught. The tunnel comes out at the Maniac Tunnel side (the `RUIN_MANIAC` line in band
  E); the player never walks it.*

```text
Cyrus: Let her go. She isn't the
one who has Palkia.
```

> Note: Indra asking what stopped Cyrus picks up her 2.4 order ("Something stopped a man who held Dialga and
> Palkia. Find out what."). Cyrus never names Giratina (2.4 rule). In 3.7 she finds it herself with the shards,
> and in 3.8 Cyrus says "She's found its home": this is the scene that tells the player she was looking.

## 3.4a part 6: the stockpile and the ledger

Owner **raid-scripts** | `solaceon_ruins_room_7` | reads **45** | sets `FLAG_SOL_RAID_E`

- *`LOOKER` runs in from the barrier side (show; walk in), a thick book under his arm.*

```text
Looker: She is gone? ...Of course
she is gone.
--
Never mind. I have this.

Looker: The registry. Every card
on that wall, copied into a book.
--
Name. Date. Place. And one more
column.

Looker: The Pokemon they left
behind. And where each one went.
--
Kennel, then truck. Every one.

Looker: The families came here to
remember.
--
Eclipse wrote it all down, and sent
their Pokemon to the frames.
```

- *Silence (`WaitTime 60`; all face down). Then Looker looks at the racks.*

```text
Looker: And these? Can they be
destroyed?

Cyrus: These racks pull pain out of
something and hold it.
--
Run one backward, and it pushes.
Every rack would empty at once.
--
I built machines like these once.
I know how they break.

Cyrus: {PLAYER}. The switch is
yours.
```

- *The main rack's switch (an object at the main rack). Talking to it:*

```text
The main rack's switch. A dial with
an arrow on it.
--
Turn it backward?
[YESNO]

[No]
Cyrus: Take your time. They're not
going anywhere.

[Yes: continue below]
```

- *Yes: the switch turns (sound); every rack flares violet (palette flash, screen shake), then the light drains out
  (fade the shard objects to grey; `FLAG_SOL_RAID_E` swaps them to their dark look).*

```text
The light runs out of every shard
on the racks.
--
They're grey now. Just stones.

The Poketch buzzes.

Ruth: The big reading's gone!
It's gone!
--
...But Lake Verity hasn't changed.
It's still climbing.

Looker: Then Kahn has enough.
--
We came to buy time. We bought a
little. Not enough.
```

- *Looker opens the ledger again, turning pages. The player reads over his shoulder. Nobody comments.*

```text
A page in the ledger:
ELIAS. VALOR BASIN.
--
In the margin, one letter: I.

A page near the back:
TEO.
--
The place is left blank.
```

- *Looker closes the book.*

```text
Looker: Enough. The International
Police are on their way.
--
By tonight, the Sanctuary is ours.
```

- *`FadeScreen`; warp to `solaceon_town` in front of the Sanctuary gate (town-scripts' spot); set **50** on the way
  (raid-scripts sets it before the warp so the town loads in band E).*

> Note: Plants and their payoffs. ELIAS with "I." in the margin: the wall card says "No one signed for it"
> (2.16a); in 3.14 Indra says "I knew his father." Nobody remarks on the letter, so the player can connect it and
> Darren doesn't (secrets.md "plant"). TEO with no place: the player knows who Teo is from 2.16a; Looker doesn't.
> Indra's 3.7 line ("you're still down there, aren't you, Teo? Somewhere under all that dark") is why she never
> wrote the place: she doesn't think he's gone.

## 3.4a part 7: the seizure

Owner **town-scripts** | `solaceon_town` | reads **50**

- *Band E town. `LOOKER` and `CYRUS` stand at the gate with the player; `IP_OFFICER_GATE` and `IP_OFFICER_COURT`
  carry boxes behind them.*

```text
Looker: It is done. The Sanctuary is
closed, by order of my office.
--
The wall stays. Those cards belong
to the families.

Looker: Take this. It was in the
vault. A stone. Not a shard.
--
I checked twice.
```

- *Give `ITEM_DUSK_STONE` x1 (stock item-get message and fanfare).*

```text
{PLAYER} received a Dusk Stone!
```

```text
Looker: I will read every page of
this book. Every name.
--
...Somebody should.

Cyrus: She asked what stopped me.
I didn't tell her.
--
She'll look anyway. People like her
always do.
--
I would have.

The Poketch buzzes.

Ruth: The Professor says come back.
Canalave's next.
--
Byron will want to hear all this,
and Iron Island has a rift of its
--
own.
```

- *Looker walks into the compound (hide). Cyrus walks off toward the south road (hide); he travels with Darren to
  Canalave (3.5's boat). The scene ends; band E is live. 3.5 picks up in Canalave.*

> Note: "Somebody should" answers Indra's "Somebody has to" (2.16a). The same record, kept for the opposite reason.

---

# Part 5: Trainer messages

Eye-contact trainers use `TRMSG_PRE_BATTLE` (shown before the battle), `TRMSG_DEFEAT` (in battle, when they lose) and
`TRMSG_POST_BATTLE` (talking to them after). Grunts 07 and 08 and Indra are scripted: their pre-battle text is the
scene text above, and their `TRMSG_PRE_BATTLE` is unused (fill it with the first line of their scene text). Defeat
lines are 2 lines at most (one battle box).

**`SOL_07`, `EXCAVATION_GRUNT_M` (the fence, M)**

```text
[TRMSG_PRE_BATTLE]
The dig's closed. Turn around.

[TRMSG_DEFEAT]
Tch.
Indra said nobody gets in.

[TRMSG_POST_BATTLE]
Go on, then. Go down there.
--
See how far you get.
```

**`SOL_08`, `EXCAVATION_GRUNT_F` (the fence, F)**

```text
[TRMSG_PRE_BATTLE]
Nobody's walking in.

[TRMSG_DEFEAT]
Ugh! Krokorok, dig us out
of here!

[TRMSG_POST_BATTLE]
Every night I stand at this fence.
Every night, nothing happens.
--
Then you.
```

**`SOL_01`, `RAID_DIGGER` (Room 1, main path)**

```text
[TRMSG_PRE_BATTLE]
Hey! Nobody comes down here!
--
Who let you past the fence?

[TRMSG_DEFEAT]
Gah! I just dig here!
They don't pay me for this!

[TRMSG_POST_BATTLE]
I was hired to dig. Dig, and not
ask what's in the crates.
--
...I didn't ask.
```

**`SOL_02`, `RAID_GEN_A_GUARD` (generator A)**

```text
[TRMSG_PRE_BATTLE]
Don't touch that machine!
--
It keeps the door shut!

[TRMSG_DEFEAT]
No! If that door opens,
Indra will...

[TRMSG_POST_BATTLE]
Go ahead. Switch it off.
--
You'll never get past her anyway.
```

**`SOL_03`, `RAID_TECH` (Room 3, main path)**

```text
[TRMSG_PRE_BATTLE]
I wired every machine down here.
--
You're not unplugging my work.

[TRMSG_DEFEAT]
My wiring! Do you know how
long that took?

[TRMSG_POST_BATTLE]
My Klang? Found it at that palace
by the new lake.
--
It was ticking. It followed me
home.
```

**`SOL_04`, `RAID_GEN_B_GUARD` (generator B)**

```text
[TRMSG_PRE_BATTLE]
My sister's card is on that wall.
--
You don't get to switch her off.

[TRMSG_DEFEAT]
...She'd have liked you.
That's the worst part.

[TRMSG_POST_BATTLE]
They promised me one more day with
her. Just one.
--
Is that so much to want?
```

**`SOL_05`, `RAID_VAULT_WATCH` (Room 5, main path)**

```text
[TRMSG_PRE_BATTLE]
The vault's past this room.
--
Nobody gets that far. Nobody.

[TRMSG_DEFEAT]
...Indra's going to hear
about this.

[TRMSG_POST_BATTLE]
She doesn't yell, you know.
--
She just writes it down.
```

**`SOL_06`, `RAID_GEN_C_GUARD` (generator C)**

```text
[TRMSG_PRE_BATTLE]
My Sableye's been staring at those
shards all week.
--
Want to see why?

[TRMSG_DEFEAT]
Sableye, no!
Don't eat that!

[TRMSG_POST_BATTLE]
Last machine, huh?
--
Then it's just you and her.
```

**`INDRA_SANCTUARY` (the vault)**

```text
[TRMSG_PRE_BATTLE]
You turned off all three.

[TRMSG_DEFEAT]
...Fine. It was only ever
the leftovers.

[TRMSG_POST_BATTLE]
[unused: she leaves in the scene]
```

> Note: Indra has no `TRMSG_MEGA_EVOLUTION` (the bible's Mega list doesn't include her). Optional
> `TRMSG_LAST_BATTLER`: "Nobody gets through. Nobody." (one line).

---

# Appendix A: NEW facts (approved by the owner, 2026-11-24, all ten, with the recommended options: Dusk Stone reward, the News Press quest removed, the Room 7 HM05 ball becomes TM30)

1. **The registry's fourth column.** The Sanctuary's ledger records, next to each dead person, the Pokemon they
   left behind and where it went ("Kennel. Then truck."). The Solaceon kennel ships Pokemon to the frames, like the
   Eterna Haven (PLAN calls the kennel "an echo of the Eterna Haven"; this makes the echo literal).
2. **Indra filed Elias's card.** The ledger page for ELIAS has "I." in the margin. It plants 3.14 ("I knew his
   father") without telling Darren anything.
3. **Teo's card has no place.** Indra's own card for Teo (records office, band A; ledger page in 3.4a) leaves the
   place blank. Fits 3.7 (she thinks he's "still down there").
4. **The vault's racks can be drained.** Run a rack backward and the stored shards empty and go grey (the same "go
   dark" as Indra's dropped shards in 3.11). Cyrus knows how because he built machines like them. Destroying the
   stockpile is the player's act.
5. **Indra's escape tunnel** comes out at the Maniac Tunnel side; the Ruin Maniac complains in band E.
6. **"The Return"** is Eclipse's public word for its promise (PLAN already uses it for the closure notice).
7. **Klink from the clockwork palace.** Grunt `SOL_03`'s Klang "followed me home" from the palace by the new lake
   (3.3). Flavor only.
8. **The Route 202 pilgrims (father, sailor, sister, son) came to Solaceon.** The father's Ponyta drawing on the wall
   is already canon (PLAN S4); the others are new placements.
9. **Optional postgame Indra at the wall** (band F). Shows Indra free after 3.14 and pins "Go live. For both of
   us." beside Teo's card. Cut it if she should stay gone.
10. **Reward:** a Dusk Stone from Looker (no Mega Stone; the bible's table is full and none is Solaceon's).

# Appendix B: decisions made writing this

1. **The split.** Looker takes the Sanctuary office (the ledger); Darren and Cyrus take the Ruins; Ruth reads the
   shards on the Poketch. The player does all three generators. Cyrus reads the barrier and waits at it, so he
   guides (his job since Act 1) without needing a follower or a tag-battle partner (no free trainer slot for an
   Arc 3 Cyrus partner team).
2. **Grunts 07-08 are the dig pair**, not the gate pair. The gate pair (`GATE_GRUNT_L/R`) never battle: they are
   public-facing in a town that must read as kind, and they are sent "to lunch" before the raid.
3. **Generators are order-free** (flags A-C, progress counts 31-33), so raid-maps can put them in any three dead
   ends.
4. **Losing to Indra** replays the vault scene from 40; losing to a grunt is a stock whiteout.
5. **The raid's result is mixed on purpose.** The vault breaks, but Lake Verity keeps climbing (3.4's "We have time,
   but not much" holds, and 3.6 happens). Looker: "We bought a little. Not enough."
6. **3.4's last lines change** (see `arc3_screenplay.md`): Rowan sends the player to Solaceon, and Ruth's Canalave
   line moves to the end of 3.4a.
7. **The Ruins before the raid.** The excavation sign in band A says visitors are welcome in the first room. Whether
   the deeper rooms are roped off before 20 is raid-maps' and raid-scripts' call; if they are, use this rope sign:

```text
DIG SITE. STAFF ONLY.
--
The rope has a little bell on it.
```

# Appendix C: open items

- **News Press.** The compound takes the News Press lot (PLAN section 4). If its door goes, the stock daily Pokemon
  request goes with it. Town-scripts and the lead decide whether to move it into a believer's house.
- **Room 7's stock items** (Mind Plate, Odd Incense, Nugget, HM05). The bible removes HMs; the HM05 ball should
  become something else (suggestion: TM30 Shadow Ball). raid-maps' call.
- **Band C/D boundary** depends on `VAR_ARC2_PROGRESS` 99 until the Arc 3 work gives Arc 3 its own var.
- **Saros's 3.3 team** isn't designed yet; Indra's levels (40-43) assume Saros sits around 40-42.
- **The Pokemon Center TV** keeps its Arc 2 quests lines; no Solaceon-specific Arc 3 TV line is written here.
