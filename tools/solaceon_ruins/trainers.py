#!/usr/bin/env python3
"""Writes the Solaceon raid trainers (slots 810-816, 833-834) from docs/story/trainers.md (Solaceon section) and the
trainer messages from docs/solaceon_redesign/screenplay.md Part 5. Standard library only.

    python3 tools/solaceon_ruins/trainers.py           # dry run: checks every name, prints what would change
    python3 tools/solaceon_ruins/trainers.py --write   # writes res/trainers/data/{indra_sanctuary,eclipse_grunt_sol_0N}.json

"Power" in trainers.md is the mac tree's "iv_scale". Text is ASCII with straight apostrophes; a line `--` in the
screenplay (a box break) is "\\r" here, as in the Arc 2 texts.
"""
import json
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
DATA = os.path.join(ROOT, "res", "trainers", "data")

GRUNT_AI = ["AI_FLAG_BASIC", "AI_FLAG_EVAL_ATTACK"]
INDRA_AI = ["AI_FLAG_BASIC", "AI_FLAG_EVAL_ATTACK", "AI_FLAG_EXPERT", "AI_FLAG_CHECK_HP"]

# (file stem, name, class, items, ai, iv_scale, party[(species, level, ability, item, moves)], messages{type: boxes})
# boxes: list of boxes, each a list of 1-2 lines.
TRAINERS = [
    ("indra_sanctuary", "Indra", "TRAINER_CLASS_ECLIPSE_LEADER", ["ITEM_HYPER_POTION", "ITEM_HYPER_POTION"], INDRA_AI, 190, [
        ("MIGHTYENA", 40, "INTIMIDATE", "SITRUS_BERRY", ["TAUNT", "SUCKER_PUNCH", "CRUNCH", "ROAR"]),
        ("SABLEYE", 41, "KEEN_EYE", "LEFTOVERS", ["WILL_O_WISP", "KNOCK_OFF", "RECOVER", "SHADOW_SNEAK"]),
        ("COFAGRIGUS", 41, "ROUGH_SKIN", "LEFTOVERS", ["WILL_O_WISP", "SHADOW_BALL", "HAZE", "PROTECT"]),
        ("ABSOL", 42, "SUPER_LUCK", "SCOPE_LENS", ["NIGHT_SLASH", "PSYCHO_CUT", "SWORDS_DANCE", "SUCKER_PUNCH"]),
        ("HONCHKROW", 43, "SUPER_LUCK", "RAZOR_CLAW", ["NIGHT_SLASH", "BRAVE_BIRD", "SUCKER_PUNCH", "ROOST"]),
    ], {
        # pre-battle is unused (the vault scene speaks first): its first line, as Part 5 says
        "TRMSG_PRE_BATTLE": [["You turned off all three."]],
        "TRMSG_DEFEAT": [["...Fine. It was only ever", "the leftovers."]],
        "TRMSG_LAST_BATTLER": [["Nobody gets through. Nobody."]],
    }),
    ("eclipse_grunt_sol_01", "Grunt", "TRAINER_CLASS_ECLIPSE_GRUNT_M", [], GRUNT_AI, 130, [
        ("GURDURR", 39, "GUTS", None, ["ROCK_SLIDE", "LOW_KICK", "BULK_UP", "DYNAMIC_PUNCH"]),
        ("GOLBAT", 39, "INNER_FOCUS", None, ["POISON_FANG", "WING_ATTACK", "CONFUSE_RAY", "AIR_CUTTER"]),
    ], {
        "TRMSG_PRE_BATTLE": [["Hey! Nobody comes down here!"], ["Who let you past the fence?"]],
        "TRMSG_DEFEAT": [["Gah! I just dig here!", "They don't pay me for this!"]],
        "TRMSG_POST_BATTLE": [["I was hired to dig. Dig, and not", "ask what's in the crates."], ["...I didn't ask."]],
    }),
    ("eclipse_grunt_sol_02", "Grunt", "TRAINER_CLASS_ECLIPSE_GRUNT_F", [], GRUNT_AI, 140, [
        ("LAMPENT", 39, "FLASH_FIRE", None, ["LAVA_PLUME", "OMINOUS_WIND", "CONFUSE_RAY", "MEMENTO"]),
        ("DUSCLOPS", 40, "PRESSURE", None, ["SHADOW_PUNCH", "WILL_O_WISP", "CONFUSE_RAY", "CURSE"]),
    ], {
        "TRMSG_PRE_BATTLE": [["Don't touch that machine!"], ["It keeps the door shut!"]],
        "TRMSG_DEFEAT": [["No! If that door opens,", "Indra will..."]],
        "TRMSG_POST_BATTLE": [["Go ahead. Switch it off."], ["You'll never get past her anyway."]],
    }),
    ("eclipse_grunt_sol_03", "Grunt", "TRAINER_CLASS_ECLIPSE_GRUNT_M", [], GRUNT_AI, 140, [
        ("SEVIPER", 40, "SHED_SKIN", None, ["CRUNCH", "POISON_TAIL", "GLARE", "NIGHT_SLASH"]),
        ("KLANG", 40, "PLUS", None, ["CHARGE_BEAM", "MIRROR_SHOT", "SCREECH", "ROCK_POLISH"]),
    ], {
        "TRMSG_PRE_BATTLE": [["I wired every machine down here."], ["You're not unplugging my work."]],
        "TRMSG_DEFEAT": [["My wiring! Do you know how", "long that took?"]],
        "TRMSG_POST_BATTLE": [["My Klang? Found it at that palace", "by the new lake."],
                              ["It was ticking. It followed me", "home."]],
    }),
    ("eclipse_grunt_sol_04", "Grunt", "TRAINER_CLASS_ECLIPSE_GRUNT_F", [], GRUNT_AI, 140, [
        ("DRIFBLIM", 40, "UNBURDEN", None, ["OMINOUS_WIND", "PAYBACK", "STOCKPILE", "BATON_PASS"]),
        ("BANETTE", 40, "INSOMNIA", None, ["SHADOW_BALL", "WILL_O_WISP", "SUCKER_PUNCH", "FAINT_ATTACK"]),
    ], {
        "TRMSG_PRE_BATTLE": [["My sister's card is on that wall."], ["You don't get to switch her off."]],
        "TRMSG_DEFEAT": [["...She'd have liked you.", "That's the worst part."]],
        "TRMSG_POST_BATTLE": [["They promised me one more day with", "her. Just one."], ["Is that so much to want?"]],
    }),
    ("eclipse_grunt_sol_05", "Grunt", "TRAINER_CLASS_ECLIPSE_GRUNT_M", [], GRUNT_AI, 140, [
        ("SKUNTANK", 41, "AFTERMATH", None, ["FLAMETHROWER", "NIGHT_SLASH", "TOXIC", "SCREECH"]),
        ("CROBAT", 41, "INNER_FOCUS", None, ["CROSS_POISON", "AIR_CUTTER", "CONFUSE_RAY", "BITE"]),
    ], {
        "TRMSG_PRE_BATTLE": [["The vault's past this room."], ["Nobody gets that far. Nobody."]],
        "TRMSG_DEFEAT": [["...Indra's going to hear", "about this."]],
        "TRMSG_POST_BATTLE": [["She doesn't yell, you know."], ["She just writes it down."]],
    }),
    ("eclipse_grunt_sol_06", "Grunt", "TRAINER_CLASS_ECLIPSE_GRUNT_F", [], GRUNT_AI, 150, [
        ("HAUNTER", 41, "LEVITATE", None, ["SHADOW_BALL", "HYPNOSIS", "DREAM_EATER", "CURSE"]),
        ("SABLEYE", 41, "KEEN_EYE", None, ["SHADOW_CLAW", "POWER_GEM", "KNOCK_OFF", "FAKE_OUT"]),
    ], {
        "TRMSG_PRE_BATTLE": [["My Sableye's been staring at those", "shards all week."], ["Want to see why?"]],
        "TRMSG_DEFEAT": [["Sableye, no!", "Don't eat that!"]],
        "TRMSG_POST_BATTLE": [["Last machine, huh?"], ["Then it's just you and her."]],
    }),
    ("eclipse_grunt_sol_07", "Grunt", "TRAINER_CLASS_ECLIPSE_GRUNT_M", [], GRUNT_AI, 130, [
        ("HOUNDOOM", 38, "FLASH_FIRE", None, ["FIRE_FANG", "FAINT_ATTACK", "THUNDER_FANG", "ROAR"]),
        ("GOLBAT", 38, "INNER_FOCUS", None, ["BITE", "WING_ATTACK", "CONFUSE_RAY", "AIR_CUTTER"]),
    ], {
        "TRMSG_PRE_BATTLE": [["The dig's closed. Turn around."]],
        "TRMSG_DEFEAT": [["Tch.", "Indra said nobody gets in."]],
        "TRMSG_POST_BATTLE": [["Go on, then. Go down there."], ["See how far you get."]],
    }),
    ("eclipse_grunt_sol_08", "Grunt", "TRAINER_CLASS_ECLIPSE_GRUNT_F", [], GRUNT_AI, 130, [
        ("LIEPARD", 38, "LIMBER", None, ["FAKE_OUT", "SLASH", "TAUNT", "ASSURANCE"]),
        ("KROKOROK", 38, "INTIMIDATE", None, ["CRUNCH", "DIG", "SAND_TOMB", "SCARY_FACE"]),
    ], {
        "TRMSG_PRE_BATTLE": [["Nobody's walking in."]],
        "TRMSG_DEFEAT": [["Ugh! Krokorok, dig us out", "of here!"]],
        "TRMSG_POST_BATTLE": [["Every night I stand at this fence.", "Every night, nothing happens."], ["Then you."]],
    }),
]

ORDER = ["TRMSG_PRE_BATTLE", "TRMSG_DEFEAT", "TRMSG_POST_BATTLE", "TRMSG_LAST_BATTLER"]


def constants(name):
    with open(os.path.join(ROOT, "generated", name)) as f:
        return {ln.split("=")[0].strip() for ln in f if ln.strip() and not ln.startswith("#")}


def species_ok(sp):
    return os.path.isdir(os.path.join(ROOT, "res", "pokemon", sp.lower()))


def move_ok(mv):
    return os.path.isdir(os.path.join(ROOT, "res", "moves", mv.lower()))


def item_ok(it):
    return os.path.isfile(os.path.join(ROOT, "res", "items", "data", it.lower() + ".json"))


def text_lines(boxes):
    """[[l1, l2], [l3]] -> ["l1\\n", "l2\\r", "l3"] (\\r = box break, the last line has no terminator)."""
    out = []
    for b, box in enumerate(boxes):
        for i, line in enumerate(box):
            last_in_box = i == len(box) - 1
            if not last_in_box:
                out.append(line + "\n")
            elif b < len(boxes) - 1:
                out.append(line + "\r")
            else:
                out.append(line)
    return out


def check_text(line, problems, where):
    if any(ord(c) > 126 for c in line):
        problems.append(f"{where}: non-ASCII in {line!r}")
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from textwidth import width
        w = width(line)
        if w > 197:
            problems.append(f"{where}: {line!r} is {w} px (> 197)")
    except ImportError:
        pass


def build(entry, abilities, classes, problems):
    stem, name, cls, items, ai, iv, party, messages = entry
    if cls not in classes:
        problems.append(f"{stem}: unknown class {cls}")
    mons = []
    for sp, lv, ab, it, moves in party:
        for ok, what in ((species_ok(sp), f"SPECIES_{sp}"), (f"ABILITY_{ab}" in abilities, f"ABILITY_{ab}"),
                         (it is None or item_ok(it), f"ITEM_{it}")):
            if not ok:
                problems.append(f"{stem}: unknown {what}")
        for mv in moves:
            if not move_ok(mv):
                problems.append(f"{stem}: unknown MOVE_{mv}")
        mons.append({
            "species": f"SPECIES_{sp}", "form": 0, "level": lv, "item": f"ITEM_{it}" if it else None,
            "moves": [f"MOVE_{m}" for m in moves], "iv_scale": iv, "ball_seal": 0, "ability": f"ABILITY_{ab}",
        })
    for it in items:
        if not item_ok(it[len("ITEM_"):]):
            problems.append(f"{stem}: unknown {it}")
    msgs = []
    for t in ORDER:
        if t in messages:
            for box in messages[t]:
                for line in box:
                    check_text(line, problems, f"{stem} {t}")
            msgs.append({"type": t, "en_US": text_lines(messages[t])})
    return {"name": name, "class": cls, "items": items, "ai_flags": ai, "double_battle": False, "party": mons,
            "messages": msgs}


def main():
    write = "--write" in sys.argv
    abilities, classes = constants("abilities.txt"), constants("trainer_classes.txt")
    problems, changed = [], []
    out = {}
    for entry in TRAINERS:
        out[entry[0]] = build(entry, abilities, classes, problems)
    if problems:
        print("\n".join(problems))
        print(f"{len(problems)} problem(s); nothing written")
        return 1
    for stem, data in out.items():
        path = os.path.join(DATA, stem + ".json")
        text = json.dumps(data, indent=4) + "\n"
        old = open(path).read() if os.path.exists(path) else ""
        if old != text:
            changed.append(stem)
            if write:
                with open(path, "w") as f:
                    f.write(text)
    print(("wrote " if write else "would write ") + (", ".join(changed) or "nothing (up to date)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
