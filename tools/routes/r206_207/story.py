#!/usr/bin/env python3
"""Routes 206-207 story hooks: the two inspectable BG events, their scripts and their text (append-only, idempotent).

  Route 207  Staging Yard Manifest Crate  BG event (333, 710), read from (333, 711) facing north
             -> Route207_ManifestCrate, message Route207_Text_ManifestCrate (appended to res/text/route_207.json)
  Route 206  Road-Closed Barricade Sign   BG event (305, 693), read from (305, 694) facing north
             -> Route206_RoadClosedSign, message Route206_Text_RoadClosedSign (appended to res/text/route_206.json)

Existing ScriptEntry order, scripts, events and message indices are untouched: the new ScriptEntry goes last (before
ScriptEntryEnd), the new script body before the trailing `.balign`, the new message at the end of the bank, the new
BG event at the end of bg_events. Straight ASCII apostrophes only.

Usage: python3 tools/routes/r206_207/story.py [--write]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as K  # noqa: E402
import layout as L  # noqa: E402

MAX_LINE = 32

HOOKS = [
    dict(map="route_207", bg=L.BG_MANIFEST, label="Route207_ManifestCrate", text_id="Route207_Text_ManifestCrate",
         lines=[
             "A clipboard is strapped to the\n",
             "crate. It's a shipping manifest.\r",
             "TEAM ECLIPSE - STAGING YARD 207\n",
             "Consignee: Mt. Coronet Survey.\r",
             "Contents: shard containment\n",
             "canisters, heat-shielded drills.\r",
             "Destination: the molten depths\n",
             "beyond the south cave.\r",
             "Scrawled at the bottom...\n",
             "Night convoy rolls at dusk.\r",
             "Keep the racks sealed. If a\n",
             "shard glows, don't touch it!",
         ]),
    dict(map="route_206", bg=L.BG_CLOSED_SIGN, label="Route206_RoadClosedSign", text_id="Route206_Text_RoadClosedSign",
         lines=[
             "ROAD CLOSED\n",
             "Heavy Transport Ahead\r",
             "Partial Lane Closure -\n",
             "Mt. Coronet Survey.\r",
             "Cycling Road west lanes closed\n",
             "for Eclipse supply convoys.\r",
             "Cyclists, keep to the open lane.\n",
             "Walkers, use the center path.",
         ]),
]


def script_body(h):
    return (f"{h['label']}:\n"
            f"    EventMessage {h['text_id']}\n"
            f"    End\n")


def apply(write):
    changed, problems = [], []
    for h in HOOKS:
        mdir = os.path.join(K.ROOT, "res/field/maps", h["map"])
        # text
        tpath = os.path.join(K.ROOT, f"res/text/{h['map']}.json")
        bank = json.load(open(tpath))
        for ln in h["lines"]:
            body = ln.rstrip("\n\r")
            if len(body) > MAX_LINE:
                problems.append(f"{h['text_id']}: line over {MAX_LINE} chars: {body!r}")
            if any(ord(c) > 126 for c in ln if c not in "\n\r"):
                problems.append(f"{h['text_id']}: non-ASCII character in {body!r}")
        ids = [m["id"] for m in bank["messages"]]
        if h["text_id"] in ids:
            i = ids.index(h["text_id"])
            if i != len(ids) - 1 and bank["messages"][i]["en_US"] != h["lines"]:
                problems.append(f"{h['text_id']} exists at index {i} with different text")
            bank["messages"][i]["en_US"] = h["lines"]
        else:
            bank["messages"].append({"id": h["text_id"], "en_US": h["lines"]})
        new_text = json.dumps(bank, indent=2, ensure_ascii=False) + "\n"
        old_text = open(tpath).read()
        # keep the stock file's formatting: only rewrite when the content differs
        if json.loads(old_text) != json.loads(new_text):
            changed.append(tpath)
            if write:
                open(tpath, "w").write(new_text)
        # events
        epath = os.path.join(mdir, "events.json")
        ev = json.load(open(epath))
        bg = h["bg"]
        entry = {"script": h["label"], "type": "BG_EVENT_TYPE_FACING", "x": bg["x"], "z": bg["z"], "y": 0,
                 "player_facing_dir": bg["dir"]}
        have = [b for b in ev["bg_events"] if b.get("script") == h["label"]]
        if not have:
            ev["bg_events"].append(entry)
            changed.append(epath)
            if write:
                open(epath, "w").write(json.dumps(ev, indent=4, ensure_ascii=False) + "\n")
        elif have[0] != entry:
            problems.append(f"{epath}: {h['label']} BG event differs from layout: {have[0]}")
        # scripts
        spath = os.path.join(mdir, "scripts.s")
        s = open(spath).read()
        if f"ScriptEntry {h['label']}\n" not in s:
            s = s.replace("    ScriptEntryEnd\n", f"    ScriptEntry {h['label']}\n    ScriptEntryEnd\n", 1)
        if f"\n{h['label']}:\n" not in s:
            tail = "\n    .balign 4, 0\n"
            k = s.rindex(tail)
            s = s[:k] + "\n" + script_body(h) + s[k:]
        if s != open(spath).read():
            changed.append(spath)
            if write:
                open(spath, "w").write(s)
    return changed, problems


def main():
    write = "--write" in sys.argv
    changed, problems = apply(False)
    if write and not problems:
        changed, problems = apply(True)
    for p in problems:
        print("FAIL", p)
    print(("wrote " if write else "would change ") + ", ".join(os.path.relpath(c, K.ROOT) for c in changed)
          if changed else "up to date")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
