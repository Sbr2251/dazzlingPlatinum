#!/usr/bin/env python3
"""Headless in-game verification for the Route 215 flooded-lowland redesign (Linux or macOS SDL3 build,
SIM_CONTROL=stdio). Reuses the Route 218 harness client (tools/everspring/verify_route218.py).

Usage:
  python3 tools/routes/r215/verify_r215.py <build_dir> <out_dir> [--night] [--save PATH]

Checks: boot -> warp to each showcase viewpoint (screenshot), both BG_EVENT signs open and close cleanly, the west
boardwalk can be walked end to end, the puddle tiles splash (behaviour
0x16), the Route 210 seam walk (x 576 -> 575 changes map) and the Veilstone gate warp (x 671).
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

ROUTE = "MAP_HEADER_ROUTE_215"
GATE = "MAP_HEADER_ROUTE_215_GATE_TO_VEILSTONE_CITY"

# (name, x, z, facing): the showcase viewpoints
VIEWPOINTS = [
    ("01_west_entry_boardwalk", 582, 598, "DIR_EAST"),
    ("02_flooded_boardwalk", 600, 592, "DIR_EAST"),
    ("03_lowland_boardwalk_070", 618, 592, "DIR_EAST"),
    ("04_north_ruts_crates", 634, 586, "DIR_EAST"),
    ("05_south_field_ruts_crates", 650, 591, "DIR_EAST"),
    ("06_lane_ruts", 652, 598, "DIR_EAST"),
    ("07_veilstone_approach", 663, 598, "DIR_EAST"),
]
INTERACTIONS = [
    ("08_sign_eclipse_crates", "Eclipse crate stack (Route215_EclipseCrates)", 654, 592, "DIR_EAST"),
    ("09_sign_drainage", "Flooded drainage sign (Route215_DrainageSign)", 595, 590, "DIR_WEST"),
]


def player_obj(game):
    r = game.cmd({"cmd": "inspect", "what": "objects"})
    for o in r.get("objects", []) if isinstance(r, dict) else []:
        if o.get("player") or o.get("local_id") in (255, 0xFF) or o.get("id") == "player":
            return o
    return None


def interact(game, out_dir, run, shot, label, x, z, facing, results, shots):
    V.warp(game, x, z, facing, results, mapname=ROUTE)
    game.cmd({"cmd": "press", "keys": ["A"], "frames": 8})
    opened, st = False, game.state()
    for _ in range(25):
        game.cmd({"cmd": "step", "frames": 10})
        st = game.state()
        if st.get("message_waiting") or st.get("script") is not None:
            opened = True
            break
    V.expect(opened, f"{label} at ({x}, {z}) {facing} opened (script={st.get('script')})", results)
    game.cmd({"cmd": "step", "frames": 60})
    V.shoot(game, out_dir, f"{run}_{shot}", shots, results)
    closed, pages = False, 0
    for _ in range(40):
        st = game.state()
        if V.is_field_idle(st):
            closed = True
            break
        game.cmd({"cmd": "press", "keys": ["A"], "frames": 8})
        game.cmd({"cmd": "step", "frames": 45})
        pages += 1
    V.expect(closed, f"{label} closed cleanly after {pages} presses", results)
    m, pos = V.where(st)
    V.expect(m == ROUTE and pos == (x, z), f"{label} left the player idle at {pos}", results)


def tour(game, out_dir, run, results, shots):
    for name, x, z, facing in VIEWPOINTS:
        V.warp(game, x, z, facing, results, mapname=ROUTE)
        V.shoot(game, out_dir, f"{run}_{name}", shots, results)
    if run != "day":
        return
    for shot, label, x, z, facing in INTERACTIONS:
        interact(game, out_dir, run, shot, label, x, z, facing, results, shots)
    # walk the flooded boardwalk end to end (x 595 -> 606 on z 592; the Max Ether ball sits on z 591)
    V.warp(game, 595, 592, "DIR_EAST", results, mapname=ROUTE)
    # (the deck sits 0.03 tiles over the unchanged stock BDHC floor: build_art.py checks the height statically)
    for k in range(1, 12):
        st = V.walk_one(game, "RIGHT")
        m, pos = V.where(st)
        V.expect(m == ROUTE and pos == (595 + k, 592), f"boardwalk step {k}/11 reached {pos}", results)
    game.cmd({"cmd": "step", "frames": 30})
    V.shoot(game, out_dir, f"{run}_10_boardwalk_walked", shots, results)
    # the Route 210 seam: walk west off x 576
    V.warp(game, 577, 597, "DIR_WEST", results, mapname=ROUTE)
    V.shoot(game, out_dir, f"{run}_11_route210_seam", shots, results)
    V.walk_one(game, "LEFT")
    st = V.walk_one(game, "LEFT")
    m, pos = V.where(st)
    V.expect(m != ROUTE and pos == (575, 597), f"seam: walked from Route 215 (576, 597) into {m} at {pos}", results)
    V.shoot(game, out_dir, f"{run}_12_route210_side", shots, results)
    # the Veilstone gate
    V.warp(game, 669, 598, "DIR_EAST", results, mapname=ROUTE)
    st = V.walk_until_map(game, "RIGHT", GATE)
    m, pos = V.where(st)
    V.expect(m == GATE, f"Veilstone gate warp (671, 598) -> {m} at {pos}", results)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("build_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--night", action="store_true")
    ap.add_argument("--save", default=V.DEFAULT_SAVE)
    ap.add_argument("--scale", type=int, default=2)
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    runs = ["day"] + (["night"] if a.night else [])
    all_results, shots, failed = [], [], False
    for run in runs:
        run_dir = tempfile.mkdtemp(prefix=f"r215_{run}_")
        log = open(os.path.join(a.out_dir, f"log_{run}.txt"), "w")
        results = []
        env = {"SIM_FIXED_RTC": V.RTC[run], "SIM_RENDERER": "gl"} if sys.platform.startswith("linux") else \
            {"SIM_FIXED_RTC": V.RTC[run]}
        game = V.Game(os.path.abspath(a.build_dir), run_dir, log, extra_env=env, scale=a.scale)
        try:
            V.boot(game, a.save, results)
            tour(game, a.out_dir, run, results, shots)
        except V.Failure as e:
            failed = True
            results.append(f"FAIL {e}")
            print(f"FAIL {e}", flush=True)
        finally:
            game.close()
            shutil.copy(game.stderr_path, os.path.join(a.out_dir, f"game_{run}.stderr.log"))
            log.close()
            shutil.rmtree(run_dir, ignore_errors=True)
        all_results += [f"[{run}] {r}" for r in results]
    with open(os.path.join(a.out_dir, "results.txt"), "w") as f:
        f.write("\n".join(all_results) + "\n")
    print(json.dumps({"failed": failed, "shots": len(shots)}))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
