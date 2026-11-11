#!/usr/bin/env python3
"""Determinism invariant: same seed + same fixed-frame inputs => identical
battle events in normal and SIM_BATTLE_FAST=1 modes (docs/battle_engine.md).
Fixed frame script (no state-dependent branching) drives the Route 202
Youngster Tristan battle from the A1-03 test save both ways and diffs JSONL.
Usage: python3 tools/battle/test_determinism.py --build build_linux --save <A1-03.sav> [--keep]
AI-assisted (Metamate)
"""
import argparse, json, os, shutil, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "dazzling"))
from headless_client import HeadlessGame

def make_run(build, tmp, name):
    d = os.path.join(tmp, name); os.makedirs(d)
    for e in os.listdir(build):
        if e.startswith(("save.bin", "meson-")) or e in ("build.ninja",) or e.endswith((".p", ".log")): continue
        src = os.path.join(build, e)
        os.symlink(os.path.abspath(src), os.path.join(d, e))
    with open(os.path.join(d, "sim_config.ini"), "w") as f:
        f.write("[General]\nInternalResolutionScale=1\nWindowHeight=0\nWindowWidth=0\nFullScreen=false\nMasterVolume=127\nScreenLayout=vertical\nSwapScreens=false\nVsyncInterval=0\nCapFrameRate=false\nMacAddr=98e255c2da7e\n")
    return d

def drive(run, save, fast, events_path):
    extra = {"SIM_BATTLE_EVENTS": events_path, "SIM_BATTLE_SEED": "777"}
    if fast: extra["SIM_BATTLE_FAST"] = "1"
    g = HeadlessGame(run, extra_env=extra)
    try:
        g.cmd({"cmd": "import_save", "path": os.path.abspath(save)})
        for _ in range(120):
            g.cmd({"cmd": "press", "keys": ["A"], "frames": 2}); g.cmd({"cmd": "step", "frames": 58})
            if g.cmd({"cmd": "state"}).get("app") == "field": break
        g.cmd({"cmd": "warp", "map": "MAP_HEADER_ROUTE_202", "x": 160, "z": 810, "dir": "DIR_EAST"})
        g.cmd({"cmd": "step", "frames": 300})
        g.cmd({"cmd": "talk", "localid": "LOCALID_YOUNGSTER_TRISTAN"})
        for _ in range(20):
            g.cmd({"cmd": "press", "keys": ["A"], "frames": 10}); g.cmd({"cmd": "step", "frames": 300})
            if g.cmd({"cmd": "state"}).get("app") == "battle": break
        for _ in range(200):
            g.cmd({"cmd": "press", "keys": ["A"], "frames": 2}); g.cmd({"cmd": "step", "frames": 58})
            if g.cmd({"cmd": "state"}).get("app") != "battle": break
        return g.cmd({"cmd": "state"}).get("app")
    finally:
        g.close()

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--build", default="build_linux"); ap.add_argument("--save", required=True); ap.add_argument("--keep", action="store_true")
    a = ap.parse_args(); tmp = tempfile.mkdtemp(prefix="battle_det_")
    try:
        results = {}
        for name, fast in (("normal", False), ("fast", True)):
            run = make_run(a.build, tmp, name); ev = os.path.join(tmp, name + ".jsonl")
            app = drive(run, a.save, fast, ev)
            lines = open(ev).read().splitlines() if os.path.exists(ev) else []
            results[name] = lines; print(f"{name}: {len(lines)} events, end app={app}")
            print(f"{name} types: {[json.loads(x).get('type') for x in lines]}")
        if results["normal"] == results["fast"] and any('"battle_start"' in x for x in results["normal"]):
            print("DETERMINISM_OK"); return 0
        print("DETERMINISM_MISMATCH"); return 1
    finally:
        if not a.keep: shutil.rmtree(tmp, ignore_errors=True)
        else: print("kept", tmp)
if __name__ == "__main__": sys.exit(main())
