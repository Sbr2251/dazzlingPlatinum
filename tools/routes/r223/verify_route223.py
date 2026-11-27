#!/usr/bin/env python3
"""Headless verification for Route 223 (Rift Sea Route & Waterfall Summit): showcase screenshots by day and night,
the two new BG events (Route223_KingdraRift, Route223_SummitPillar) read from every reading tile, and every
existing Route 223 object still present where events.json puts it.

Standard library only; reuses the lockstep client of tools/everspring/verify_route218.py (SIM_CONTROL=stdio).

Usage:
  python3 tools/routes/r223/verify_route223.py <build_dir> <output_dir> [--evening] [--night] [--quick] [--save PATH]

Exit status 0 when every assertion passes. Screenshots: <output_dir>/<run>_<view>.png.
"""
import argparse
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "everspring"))
import verify_route218 as V  # noqa: E402

ROUTE_223 = "MAP_HEADER_ROUTE_223"
RTC = {"day": "2026-01-02T12:00:00", "evening": "2026-01-02T17:30:00", "night": "2026-01-02T22:00:00"}

# showcase viewpoints: (name, x, z, facing)
VIEWPOINTS = [
    ("01_waterfall_summit_gate", 847, 614, "DIR_NORTH"),
    ("02_kingdra_rift_rock", 853, 698, "DIR_NORTH"),
    ("03_south_sea_approach", 846, 724, "DIR_NORTH"),
    ("04_mid_route_cluster", 846, 657, "DIR_NORTH"),
]
# BG events: (label, reading tile x, z, facing)
INTERACTIONS = [
    ("summit_pillar_west", 845, 611, "DIR_WEST"),
    ("summit_pillar_east", 848, 612, "DIR_EAST"),
    ("kingdra_rift_a", 851, 698, "DIR_NORTH"),
    ("kingdra_rift_b", 852, 698, "DIR_NORTH"),
]


def read_bg(game, out_dir, run, label, x, z, facing, results, shots):
    V.warp(game, x, z, facing, results, mapname=ROUTE_223)
    game.cmd({"cmd": "press", "keys": ["A"], "frames": 8})
    opened, st = False, game.state()
    for _ in range(25):
        game.cmd({"cmd": "step", "frames": 10})
        st = game.state()
        if st.get("message_waiting") or st.get("script") is not None:
            opened = True
            break
    V.expect(opened, f"{label} at ({x}, {z}) {facing} opened (script={st.get('script')})", results)
    game.cmd({"cmd": "step", "frames": 90})
    V.shoot(game, out_dir, f"{run}_bg_{label}", shots, results)
    closed = False
    for _ in range(20):
        st = game.state()
        if V.is_field_idle(st):
            closed = True
            break
        game.cmd({"cmd": "press", "keys": ["A"], "frames": 8})
        game.cmd({"cmd": "step", "frames": 60})
    V.expect(closed, f"{label} closed cleanly", results)
    m, pos = V.where(game.state())
    V.expect(m == ROUTE_223 and pos == (x, z), f"{label} left the player at {pos}", results)


def run_one(build_dir, out_dir, run, save, results, shots, interactions):
    run_dir = tempfile.mkdtemp(prefix=f"r223_{run}_")
    log = open(os.path.join(out_dir, f"log_{run}.txt"), "w")
    env = {"SIM_FIXED_RTC": RTC[run], "SIM_RENDERER": "gl", "SIM_G2_GPU": "0"}
    game = V.Game(build_dir, run_dir, log, extra_env=env, scale=2)
    try:
        V.boot(game, save, results)
        for name, x, z, facing in VIEWPOINTS:
            V.warp(game, x, z, facing, results, mapname=ROUTE_223)
            game.cmd({"cmd": "step", "frames": 30})
            if name == VIEWPOINTS[0][0]:
                objs = game.cmd({"cmd": "objects"})
                log.write("## objects " + json.dumps(objs) + "\n")
            V.shoot(game, out_dir, f"{run}_{name}", shots, results)
        if interactions:
            for label, x, z, facing in INTERACTIONS:
                read_bg(game, out_dir, run, label, x, z, facing, results, shots)
            # every stock object still spawns at its events.json tile (those in the loaded area)
            ev = json.load(open(os.path.join(ROOT, "res/field/maps/route_223/events.json")))
            want = {o["id"]: (o["x"], o["z"]) for o in ev["object_events"] if "id" in o and "ITEM" not in o["id"]
                    and "TOTEM" not in o["id"]}
            seen = {}
            for vx, vz in ((847, 625), (847, 650), (847, 680), (847, 710)):
                V.warp(game, vx, vz, "DIR_NORTH", results, mapname=ROUTE_223)
                for o in game.cmd({"cmd": "objects"}).get("objects", []):
                    if o.get("name"):
                        seen.setdefault(o["name"], (o["x"], o["z"]))
            log.write("## seen " + json.dumps(seen) + "\n")
            missing = [k for k in want if k not in seen]
            V.expect(not missing, f"all {len(want)} Route 223 trainers spawned (missing {missing})", results)
    finally:
        game.close()
        log.close()
        shutil.rmtree(run_dir, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("build_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--night", action="store_true")
    ap.add_argument("--evening", action="store_true")
    ap.add_argument("--save", default=V.DEFAULT_SAVE)
    ap.add_argument("--quick", action="store_true", help="viewpoint screenshots only (no BG/object checks)")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    results, shots = [], []
    ok = True
    runs = ["day"] + (["evening"] if a.evening else []) + (["night"] if a.night else [])
    for run in runs:
        try:
            run_one(os.path.abspath(a.build_dir), os.path.abspath(a.out_dir), run, a.save, results, shots,
                    interactions=(run == "day" and not a.quick))
        except V.Failure as e:
            print("FAIL", e)
            ok = False
    print(f"{sum(r.startswith('ok') for r in results)} ok, {sum(r.startswith('FAIL') for r in results)} failed; "
          f"{len(shots)} screenshots in {a.out_dir}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
