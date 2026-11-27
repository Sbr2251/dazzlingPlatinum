#!/usr/bin/env python3
"""Route 222 — Violet-Lit Coast events: the stranded Water Pokemon on the tide line, the blacked-out lamp sign and
the violet lamp sign. Rebuilds res/field/maps/route_222/{events.json, scripts.s} and res/text/route_222.json from
the stock files at build_art.BASE_REV plus the additions below, so reruns are idempotent and the stock entries keep
their order (object / bg / warp event indices, script entry numbers used by init.s, text indices) - everything new
is appended at the end. Coordinates come from build_art.py (STRANDED, SIGN_LAMP, VIOLET_SIGN_LAMP).

Usage:
  python3 tools/routes/r222/events.py            dry run (prints the additions)
  python3 tools/routes/r222/events.py --write    write the three files
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_art as BA  # noqa: E402

ROOT = BA.ROOT
SCRIPTS_REL = "res/field/maps/route_222/scripts.s"
TEXT_REL = "res/text/route_222.json"

TEXT = {
    "Route222_Text_StrandedPsyduck": [
        "Psyduck: Pwaa...\r",
        "It shivers, staring east at the\n",
        "violet light over the sea...",
    ],
    "Route222_Text_StrandedPiplup": [
        "Piplup: Pi... piplup...\r",
        "It shivers, staring east at the\n",
        "violet light over the sea...\r",
        "The strange tide must have washed\n",
        "it far from its home waters.",
    ],
    "Route222_Text_StrandedPrinplup": [
        "Prinplup: Prrrin...\r",
        "It shivers, staring east at the\n",
        "violet light over the sea...\r",
        "It won't go back into the water\n",
        "while that glow hangs over it.",
    ],
    "Route222_Text_BlackoutLamp": [
        "The coastal lamp is stone cold.\r",
        "Only a faint violet static hums\n",
        "inside the glass.",
    ],
    "Route222_Text_VioletLamp": [
        "The lamp's glass crackles with\n",
        "violet sparks.\r",
        "Sunyshore's grid is dead...\r",
        "The glow over Route 223 is\n",
        "lighting it from within.",
    ],
}

SCRIPTS = """
// Route 222 Violet-Lit Coast (routes-wave2, tools/routes/r222/events.py): stranded Water Pokemon on the tide line
// and the blacked-out coastal lamps. Appended after the stock entries so init.s's entry numbers stay valid.
Route222_StrandedPsyduck:
    PokemonCryAndMessage SPECIES_PSYDUCK, Route222_Text_StrandedPsyduck
    End

Route222_StrandedPiplup:
    PokemonCryAndMessage SPECIES_PIPLUP, Route222_Text_StrandedPiplup
    End

Route222_StrandedPrinplup:
    PokemonCryAndMessage SPECIES_PRINPLUP, Route222_Text_StrandedPrinplup
    End

Route222_BlackoutLamp:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    Message Route222_Text_BlackoutLamp
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End

Route222_VioletLamp:
    PlaySE SE_CONFIRM_sseq_3
    LockAll
    Message Route222_Text_VioletLamp
    WaitABPadPress
    CloseMessage
    ReleaseAll
    End
"""
NEW_ENTRIES = ["Route222_StrandedPsyduck", "Route222_StrandedPiplup", "Route222_StrandedPrinplup",
               "Route222_BlackoutLamp", "Route222_VioletLamp"]


def object_event(local_id, gfx, x, z, script):
    return {"id": local_id, "graphics_id": gfx, "movement_type": "MOVEMENT_TYPE_LOOK_EAST",
            "trainer_type": "TRAINER_TYPE_NONE", "hidden_flag": "0", "script": script, "initial_dir": "DIR_EAST",
            "data": [], "movement_range_x": 0, "movement_range_z": 0, "x": x, "z": z, "y": 0}


def bg_event(script, x, z, facing):
    return {"script": script, "type": "BG_EVENT_TYPE_FACING", "x": x, "z": z, "y": 0, "player_facing_dir": facing}


def build():
    ev = json.loads(BA.C.git_file(BA.BASE_REV, BA.EVENTS_REL))
    for local_id, gfx, species, x, z, script in BA.STRANDED:
        ev["object_events"].append(object_event(local_id, gfx, x, z, script))
    ev["bg_events"].append(bg_event("Route222_BlackoutLamp", *BA.SIGN_LAMP, "BG_EVENT_DIR_NORTH"))
    ev["bg_events"].append(bg_event("Route222_VioletLamp", *BA.VIOLET_SIGN_LAMP, "BG_EVENT_DIR_WEST"))
    events = json.dumps(ev, indent=4, ensure_ascii=False) + "\n"

    text = json.loads(BA.C.git_file(BA.BASE_REV, TEXT_REL).decode("utf-8"))
    for k, v in TEXT.items():
        text["messages"].append({"id": k, "en_US": v})
    text_out = json.dumps(text, indent=2, ensure_ascii=False) + "\n"

    src = BA.C.git_file(BA.BASE_REV, SCRIPTS_REL).decode("utf-8")
    marker = "    ScriptEntryEnd\n"
    assert src.count(marker) == 1
    entries = "".join(f"    ScriptEntry {e}\n" for e in NEW_ENTRIES)
    scripts = src.replace(marker, entries + marker).rstrip("\n") + "\n" + SCRIPTS
    return events, text_out, scripts


def checks(events, text_out, scripts):
    res = []
    new_text = "".join("".join(v) for v in TEXT.values()) + SCRIPTS
    res.append(("new text and scripts are ASCII only (straight apostrophes)", all(ord(c) < 128 for c in new_text)))
    longest = max(len(line.rstrip("\n\r")) for v in TEXT.values() for line in v)
    res.append((f"new message lines <= 33 characters (longest {longest})", longest <= 33))
    stock = json.loads(BA.C.git_file(BA.BASE_REV, BA.EVENTS_REL))
    ev = json.loads(events)
    res.append(("stock object / bg / warp / coord events unchanged and in order (additions appended)",
                all(ev[k][:len(stock[k])] == stock[k] for k in stock)))
    stock_text = json.loads(BA.C.git_file(BA.BASE_REV, TEXT_REL).decode("utf-8"))["messages"]
    res.append(("stock text indices unchanged (additions appended)", json.loads(text_out)["messages"][:len(stock_text)]
                == stock_text))
    src = BA.C.git_file(BA.BASE_REV, SCRIPTS_REL).decode("utf-8")
    old = [ln.split()[1] for ln in src.splitlines() if ln.strip().startswith("ScriptEntry ")]
    new = [ln.split()[1] for ln in scripts.splitlines() if ln.strip().startswith("ScriptEntry ")]
    res.append((f"stock script entries keep their numbers ({len(old)} stock + {len(new) - len(old)} new)",
                new[:len(old)] == old and new[len(old):] == NEW_ENTRIES))
    labels = {ln[:-1] for ln in scripts.splitlines() if ln.endswith(":") and not ln.startswith(" ")}
    used = [o["script"] for o in ev["object_events"] + ev["bg_events"] if "script" in o and o["script"].startswith("Route222_")]
    res.append(("every Route222_ script an event names is a ScriptEntry with a label", all(u in new and u in labels for u in used)))
    return res


def main():
    events, text_out, scripts = build()
    nfail = 0
    for desc, ok in checks(events, text_out, scripts):
        print(("PASS " if ok else "FAIL ") + desc)
        nfail += not ok
    for s in BA.STRANDED:
        print(f"object {s[0]}: {s[1]} at ({s[3]}, {s[4]}) -> {s[5]}")
    print(f"bg Route222_BlackoutLamp at {BA.SIGN_LAMP} (read facing north), Route222_VioletLamp at {BA.VIOLET_SIGN_LAMP} "
          f"(read facing west)")
    if "--write" in sys.argv:
        if nfail:
            print("refusing to write")
            return 1
        open(os.path.join(ROOT, BA.EVENTS_REL), "w", encoding="utf-8").write(events)
        open(os.path.join(ROOT, TEXT_REL), "w", encoding="utf-8").write(text_out)
        open(os.path.join(ROOT, SCRIPTS_REL), "w", encoding="utf-8").write(scripts)
        print("wrote", BA.EVENTS_REL, TEXT_REL, SCRIPTS_REL)
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
