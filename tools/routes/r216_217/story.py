#!/usr/bin/env python3
"""Routes 216-217 story pass: the two inspectable BG events (Teo's Memorial Marker on Route 216, Indra's camp
journal / scanner crate on Route 217), their scripts and their text. Idempotent: entries are added or replaced by
label / message id; existing events, scripts and message order are kept (new messages are appended at the end).
Straight ASCII apostrophes only (msgenc has no em dash, so the inscription uses ' - ').

Usage: python3 tools/routes/r216_217/story.py [--check]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)

TEO_MARKER = (317, 401)
CAMP_EVENTS = [(312, 360), (311, 360)]

TEXT = {
    "route_216": [
        ("Route216_Text_TeoMemorialStone", [
            "A carved stone marker stands on the\n", "ledge, facing south to Mt. Coronet.\r",
            "Someone has brushed the snow from\n", "its dark plaque. It reads...\r"]),
        ("Route216_Text_TeoMemorialInscription", ["TEO - Lost to the mountain wind."]),
        ("Route216_Text_TeoMemorialOfferings", [
            "A wreath of frozen winter flowers\n", "rests at its foot, and a violet\r",
            "scarf is knotted around the stone.\n", "The little lantern still glows warm.\r"]),
        ("Route216_Text_TeoMemorialFootprints", [
            "Fresh footprints lead up to the\n", "marker... and away again.\r",
            "Where someone stood, a faint trace\n", "of violet dust glitters in the snow,\r",
            "as if a shard had been held up,\n", "pointing at Mt. Coronet."]),
    ],
    "route_217": [
        ("Route217_Text_IndraCampTent", [
            "A weathered violet expedition tent\n", "stands in the snow. Nobody is here.\r",
            "A lantern still burns on a supply\n", "crate, beside an open field journal.\r"]),
        ("Route217_Text_IndraCampJournal", [
            "The handwriting is small and neat.\r",
            "Day 9. The shard will not settle.\n", "Every night it pulls to the south.\r",
            "Day 12. Not up the mountain. Down.\n", "Under it. Under all of that dark.\r",
            "Teo, you always said I worried\n", "too much. I'm coming anyway."]),
        ("Route217_Text_IndraCampCompass", [
            "An Eclipse shard-compass hums\n", "faintly in its open case.\r",
            "Its dim violet needle points due\n", "south... toward Mt. Coronet\r",
            "and the molten depths beneath it."]),
    ],
}

SCRIPTS = {
    "route_216": ("Route216_TeoMemorial", """Route216_TeoMemorial:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    Message Route216_Text_TeoMemorialStone
    WaitABPadPress
    Message Route216_Text_TeoMemorialInscription
    WaitABPadPress
    Message Route216_Text_TeoMemorialOfferings
    WaitABPadPress
    PlaySE SEQ_SE_DP_KIRAKIRA_sseq
    Message Route216_Text_TeoMemorialFootprints
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End
"""),
    "route_217": ("Route217_IndraCamp", """Route217_IndraCamp:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    Message Route217_Text_IndraCampTent
    WaitABPadPress
    Message Route217_Text_IndraCampJournal
    WaitABPadPress
    PlaySE SEQ_SE_DP_KIRAKIRA_sseq
    Message Route217_Text_IndraCampCompass
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End
"""),
}

EVENTS = {
    "route_216": [("Route216_TeoMemorial", TEO_MARKER)],
    "route_217": [("Route217_IndraCamp", xz) for xz in CAMP_EVENTS],
}


def patch_text(m):
    path = os.path.join(ROOT, "res/text", m + ".json")
    raw = open(path, encoding="utf-8").read()
    d = json.loads(raw)
    ids = [x["id"] for x in d["messages"]]
    for mid, lines in TEXT[m]:
        for ln in lines:
            assert all(ord(c) < 128 for c in ln), (mid, ln)
            assert len(ln.rstrip("\n\r")) <= 36, (mid, ln)
        entry = {"id": mid, "en_US": lines if len(lines) > 1 else lines[0]}
        if mid in ids:
            d["messages"][ids.index(mid)] = entry
        else:
            d["messages"].append(entry)
    out = json.dumps(d, indent=2, ensure_ascii=False) + ("\n" if raw.endswith("\n") else "")
    return path, raw, out


def patch_scripts(m):
    path = os.path.join(ROOT, "res/field/maps", m, "scripts.s")
    raw = open(path).read()
    label, body = SCRIPTS[m]
    s = raw
    if f"ScriptEntry {label}\n" not in s:
        s = s.replace("    ScriptEntryEnd\n", f"    ScriptEntry {label}\n    ScriptEntryEnd\n", 1)
    if f"\n{label}:\n" in s:
        a = s.index(f"\n{label}:\n") + 1
        b = s.index("    End\n", a) + len("    End\n")
        s = s[:a] + body + s[b:]
    else:
        k = s.find("    .balign 4, 0")
        s = (s[:k] + body + "\n" + s[k:]) if k >= 0 else (s.rstrip("\n") + "\n\n" + body)
    return path, raw, s


def patch_events(m):
    path = os.path.join(ROOT, "res/field/maps", m, "events.json")
    raw = open(path).read()
    d = json.loads(raw)
    labels = {lab for lab, _ in EVENTS[m]}
    d["bg_events"] = [b for b in d["bg_events"] if b.get("script") not in labels]
    for lab, (x, z) in EVENTS[m]:
        d["bg_events"].append({"script": lab, "type": "BG_EVENT_TYPE_FACING", "x": x, "z": z, "y": 0,
                               "player_facing_dir": "BG_EVENT_DIR_NORTH"})
    out = json.dumps(d, indent=4) + ("\n" if raw.endswith("\n") else "")
    return path, raw, out


def main():
    changes = []
    for m in ("route_216", "route_217"):
        for fn in (patch_text, patch_scripts, patch_events):
            changes.append(fn(m))
    for path, raw, out in changes:
        rel = os.path.relpath(path, ROOT)
        if "--check" in sys.argv:
            print(("UP TO DATE " if raw == out else "WOULD CHANGE ") + rel)
        elif raw != out:
            open(path, "w", encoding="utf-8").write(out)
            print("wrote", rel)


if __name__ == "__main__":
    main()
