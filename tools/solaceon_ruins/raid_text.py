#!/usr/bin/env python3
"""The raid's field text (screenplay.md scene 3.4a parts 3-6, Appendix B 7), appended to the Ruins text banks.
Standard library only.

    python3 tools/solaceon_ruins/raid_text.py           # dry run: width/ASCII checks, prints what would change
    python3 tools/solaceon_ruins/raid_text.py --write

Messages are written in the screenplay's notation: consecutive lines are one box (at most 2), a line "--" is a box
break ("\\r"), and each entry is one message. {PLAYER} becomes {STRVAR_1 3, 0, 0} (BufferPlayerName 0).
New messages are appended at the end of each bank (existing entries keep their index). REPLACE lists stock
messages that are rewritten in place (the Room 2 Hiker's HM05 lines; HMs don't exist in this hack and Room 7's
HM05 ball is TM30 now, Appendix A).

Text that the screenplay does not have (marked NEW below) is short object text: rack, rubble, Looker's reminder.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
from textwidth import width, MAX_W  # noqa: E402

TEXT = os.path.join(ROOT, "res", "text")

POKETCH = "The Poketch buzzes."

GENERATOR = [
    ("GeneratorOn", """
A machine wired to a rack of violet
shards. It hums. The air is warm.
--
Switch it off?"""),
    ("GeneratorSwitchedOff", """
{PLAYER} switched the machine off.
--
The shards on the rack go dim."""),
    ("GeneratorOff", """
The machine is off. The shards on
the rack are dim."""),
    ("PoketchBuzzes", POKETCH),
    ("Ruth31", """
Ruth: One of the sources just
dropped! Two to go."""),
    ("Ruth32", """
Ruth: That's two! The big one at the
bottom is flickering now."""),
    ("Ruth33", """
Ruth: All three are down! The
reading on the vault door
--
just went flat!
--
Go. Before somebody switches them
back on."""),
]

BANKS = {
    "solaceon_ruins_room_1": ("SolaceonRuinsRoom1_Text_", [
        ("RaidRopeSign", """
DIG SITE. STAFF ONLY.
--
The rope has a little bell on it."""),
        ("RaidCyrusHum", """
Cyrus: That hum. I know it.
--
I heard it in my own machines,
a long time ago."""),
        ("RaidCyrusThreeLines", """
Cyrus: The door below is fed from
three places. Three lines.
--
I can feel them, like seams.
--
Cut all three, and it falls."""),
        ("RaidCyrusGoAhead", """
Cyrus: I'll go ahead to the door
and read it. You find the lines."""),
        ("RaidPoketchBuzzes", POKETCH),
        ("RaidRuthReadings", """
Ruth: Can you hear me? I've got the
shard readings up!
--
Three strong sources, deeper in.
And one huge one at the bottom.
--
That has to be the vault.
--
...Be careful. Please."""),
    ]),
    "solaceon_ruins_room_2_northeast_dead_end": ("SolaceonRuinsRoom2NortheastDeadEnd_Text_", GENERATOR),
    "solaceon_ruins_room_4_southeast_dead_end": ("SolaceonRuinsRoom4SoutheastDeadEnd_Text_", GENERATOR),
    "solaceon_ruins_room_6_northwest_dead_end": ("SolaceonRuinsRoom6NorthwestDeadEnd_Text_", GENERATOR),
    "solaceon_ruins_room_7": ("SolaceonRuinsRoom7_Text_", [
        ("RaidBarrier", """
A wall of violet light. It hums.
It won't let you through."""),
        ("RaidCyrusNotYet", """
Cyrus: Not yet. Something is still
feeding it.
--
Find the other lines."""),
        ("RaidCyrusItsDown", """
Cyrus: It's down.
--
Someone is in there. Waiting."""),
        ("RaidIndraAllThree", """
Indra: You turned off all three.
--
Do you know how long it took to
grow what's on these racks?"""),
        ("RaidIndraRowansKid", """
Indra: Rowan's kid. The one from the
depot.
--
I told you to go home."""),
        ("RaidIndraManWhoWalkedOut", """
Indra: And the man who walked out.
Garius told us all about you."""),
        ("RaidCyrusSilent", "Cyrus: ..."),
        ("RaidIndraLate", """
Indra: You're late, by the way.
--
Kahn came for his share at dawn.
He took what he needs.
--
Palkia's as good as his. This is
just what's left."""),
        ("RaidIndraSaros", """
Indra: Saros wanted a morning. He
has his clock now.
--
Kahn wants a door. He'll have it
soon."""),
        ("RaidIndraKeepTheDoor", """
Indra: And I keep the door. That's
all I've ever done."""),
        ("RaidIndraHm", """
Indra: Hm.
--
Still fighting like somebody who's
never lost anything."""),
        ("RaidIndraWhatStoppedYou", """
Indra: You. You held Dialga and
Palkia once. In your world.
--
And something stopped you.
--
What was it?"""),
        ("RaidIndraKeepIt", """
Indra: Keep it, then.
--
I'll find it without you."""),
        ("RaidIndraDontFollow", """
Indra: Don't follow me. The roof
in here doesn't like visitors."""),
        ("RaidCyrusLetHerGo", """
Cyrus: Let her go. She isn't the
one who has Palkia."""),
        ("RaidLookerGone", """
Looker: She is gone? ...Of course
she is gone.
--
Never mind. I have this."""),
        ("RaidLookerRegistry", """
Looker: The registry. Every card
on that wall, copied into a book.
--
Name. Date. Place. And one more
column."""),
        ("RaidLookerLeftBehind", """
Looker: The Pokemon they left
behind. And where each one went.
--
Kennel, then truck. Every one."""),
        ("RaidLookerFamilies", """
Looker: The families came here to
remember.
--
Eclipse wrote it all down, and sent
their Pokemon to the frames."""),
        ("RaidLookerDestroyed", """
Looker: And these? Can they be
destroyed?"""),
        ("RaidCyrusRacks", """
Cyrus: These racks pull pain out of
something and hold it.
--
Run one backward, and it pushes.
Every rack would empty at once.
--
I built machines like these once.
I know how they break."""),
        ("RaidCyrusSwitchYours", """
Cyrus: {PLAYER}. The switch is
yours."""),
        ("RaidSwitch", """
The main rack's switch. A dial with
an arrow on it.
--
Turn it backward?"""),
        ("RaidSwitchTurned", """
The main rack's switch. A dial with
an arrow on it."""),
        ("RaidCyrusTakeYourTime", """
Cyrus: Take your time. They're not
going anywhere."""),
        ("RaidDrained", """
The light runs out of every shard
on the racks.
--
They're grey now. Just stones."""),
        ("RaidPoketchBuzzes", POKETCH),
        ("RaidRuthGone", """
Ruth: The big reading's gone!
It's gone!
--
...But Lake Verity hasn't changed.
It's still climbing."""),
        ("RaidLookerKahnHasEnough", """
Looker: Then Kahn has enough.
--
We came to buy time. We bought a
little. Not enough."""),
        ("RaidLedgerElias", """
A page in the ledger:
ELIAS. VALOR BASIN.
--
In the margin, one letter: I."""),
        ("RaidLedgerTeo", """
A page near the back:
TEO.
--
The place is left blank."""),
        ("RaidLookerPolice", """
Looker: Enough. The International
Police are on their way.
--
By tonight, the Sanctuary is ours."""),
        # NEW (object text the screenplay doesn't write)
        ("RaidRackLit", """
A rack of violet shards. It hums,
and the air around it is warm."""),
        ("RaidRackDark", "They're grey now. Just stones."),
        ("RaidRubble", """
Rubble fills the hole. The tunnel
behind it is gone."""),
        ("RaidLookerSwitch", """
Looker: The switch is at the main
rack, my friend. Cyrus says so."""),
    ]),
}

# Stock Room 2 Hiker lines rewritten in place (same order, new ids). The Hiker no longer wants HM05 Defog (there
# are no HMs); he wants to know the way down to the room where TM30 lies, and pays the same Green Shard.
REPLACE = {
    "solaceon_ruins_room_2": {
        "SolaceonRuinsRoom2_Text_HMDefogInRuins": ("SolaceonRuinsRoom2_Text_TMInRuins", """
I'd heard there was a TM somewhere
in these ruins. Way down deep.
--
It's just that I seem to be lost,
with everything looking the same.
--
Now what?
I could use help here."""),
        "SolaceonRuinsRoom2_Text_HMDefogInRuins2": ("SolaceonRuinsRoom2_Text_TMInRuins2", """
I'd heard there was a TM somewhere
in these ruins. Way down deep.
--
It's just that I seem to be lost,
with everything looking the same.
--
Now what?
I could use help here.
--"""),
        "SolaceonRuinsRoom2_Text_CanYouLoanHMDefog": ("SolaceonRuinsRoom2_Text_CanYouShowTheWay", """
Hey!
Now looky here!
--
What you have there!
That's TM30, Shadow Ball!
--
Can you tell me the way down?
I'll make it worth your while."""),
        "SolaceonRuinsRoom2_Text_ThanksYoureMyRescuer": ("SolaceonRuinsRoom2_Text_ThanksYoureMyRescuer", """
Down the stairs, and down again...
Got it! Every last turn!
--
Thanks! You're my rescuer! Hahaha!
Here you go, my thanks as promised.
--"""),
        "SolaceonRuinsRoom2_Text_ItsNotLikeItWearsOut": ("SolaceonRuinsRoom2_Text_ItsNotLikeItWearsOut", """
It's not like the way down will
wear out! Cheapskate!"""),
        "SolaceonRuinsRoom2_Text_IveFinallyGotDefog": ("SolaceonRuinsRoom2_Text_IKnowTheWayDown", """
I know the way down now, and it's all
thanks to you.
--
I'll find a TM of my own down there
one of these days."""),
    },
}

# Messages that end with a box break even at the end (the script calls a common script that keeps writing to the
# same box, e.g. CommonScript_AddItemQuantityNoLineFeed), marked with a trailing "--" above.


def to_lines(text, player="{STRVAR_1 3, 0, 0}"):
    raw = text.strip("\n").split("\n")
    trailing_break = raw and raw[-1] == "--"
    if trailing_break:
        raw = raw[:-1]
    boxes, cur = [], []
    for ln in raw:
        if ln == "--":
            boxes.append(cur)
            cur = []
        else:
            cur.append(ln.replace("{PLAYER}", player))
    boxes.append(cur)
    out = []
    for b, box in enumerate(boxes):
        for i, ln in enumerate(box):
            if i < len(box) - 1:
                out.append(ln + "\n")
            elif b < len(boxes) - 1 or trailing_break:
                out.append(ln + "\r")
            else:
                out.append(ln)
    return out if len(out) > 1 else out[0]


def check(mid, lines, problems):
    lines = lines if isinstance(lines, list) else [lines]
    in_box = 0
    for ln in lines:
        if any(ord(c) > 126 for c in ln):
            problems.append(f"{mid}: non-ASCII {ln!r}")
        if width(ln) > MAX_W:
            problems.append(f"{mid}: {width(ln)} px > {MAX_W}: {ln!r}")
        in_box += 1
        if in_box > 2:
            problems.append(f"{mid}: 3 lines in a box at {ln!r}")
        if ln.endswith("\r"):
            in_box = 0


def main():
    write = "--write" in sys.argv
    problems, report = [], []
    out = {}
    for bank in sorted(set(BANKS) | set(REPLACE)):
        path = os.path.join(TEXT, bank + ".json")
        data = json.load(open(path)) if os.path.exists(path) else None
        if data is None:
            # a new bank: key = one past the largest key among the hack's own banks (40xxx), as Arc 2 did
            keys = [json.load(open(os.path.join(TEXT, f))).get("key", 0) for f in os.listdir(TEXT)
                    if f.endswith(".json")]
            data = {"key": max(k for k in keys if 40000 <= k < 41000) + 1, "messages": []}
            for o in out.values():   # banks created in this run
                data["key"] = max(data["key"], o["key"] + 1)
            report.append(f"{bank}: new bank, key {data['key']}")
        msgs = data["messages"]
        ids = [m["id"] for m in msgs]
        for old_id, (new_id, text) in REPLACE.get(bank, {}).items():
            lines = to_lines(text)
            check(new_id, lines, problems)
            if old_id in ids and msgs[ids.index(old_id)] != {"id": new_id, "en_US": lines}:
                i = ids.index(old_id)
                msgs[i] = {"id": new_id, "en_US": lines}
                ids[i] = new_id
                report.append(f"{bank}: rewrote {old_id} -> {new_id}")
            elif new_id in ids:
                msgs[ids.index(new_id)]["en_US"] = lines
        if bank in BANKS:
            prefix, entries = BANKS[bank]
            for name, text in entries:
                mid = prefix + name
                lines = to_lines(text)
                check(mid, lines, problems)
                if mid in ids:
                    msgs[ids.index(mid)]["en_US"] = lines
                else:
                    msgs.append({"id": mid, "en_US": lines})
                    ids.append(mid)
                    report.append(f"{bank}: + {mid}")
        out[bank] = data
    if problems:
        print("\n".join(problems))
        print(f"{len(problems)} problem(s); nothing written")
        return 1
    changed = []
    for bank, data in out.items():
        path = os.path.join(TEXT, bank + ".json")
        text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        old = open(path).read() if os.path.exists(path) else ""
        if text != old:
            changed.append(bank)
            if write:
                with open(path, "w") as f:
                    f.write(text)
    print(f"{len(report)} change(s); " + ("wrote " if write else "would write ") + (", ".join(changed) or "nothing"))
    if "-v" in sys.argv:
        print("\n".join(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
