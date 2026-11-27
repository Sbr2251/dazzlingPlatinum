#!/usr/bin/env python3
"""Headless in-game verification for the Routes 206-207 Eclipse Supply Road (Linux/macOS SDL3 build,
SIM_CONTROL=stdio). Reuses the client helpers of tools/everspring/verify_route218.py.

Usage:
  python3 tools/routes/r206_207/verify_ingame.py <build_dir> <out_dir> [--night] [--save PATH] [--renderer gl|gpu]

Day pass: screenshots of the showcase viewpoints (layout.VIEWPOINTS) and extra spots; reads both new BG events
(Route 207 manifest crate, Route 206 ROAD CLOSED sign) through every page; walks the narrowed Route 206 plaza lane
into the Cycling Road south gate; walks the Route 207 road along the staging yard into Mt. Coronet's south entrance;
checks that the barricade and the manifest crate block. Night pass (--night): the viewpoints again at 22:00.
"""
import argparse
import json
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.append(os.path.join(ROOT, "tools", "everspring"))
import layout as L  # noqa: E402
import verify_route218 as V  # noqa: E402

R206 = "MAP_HEADER_ROUTE_206"
R207 = "MAP_HEADER_ROUTE_207"
GATE_S = "MAP_HEADER_ROUTE_206_CYCLING_ROAD_SOUTH_GATE"
CORONET = "MAP_HEADER_MT_CORONET_1F_SOUTH"
FACING = {"north": "DIR_NORTH", "south": "DIR_SOUTH", "east": "DIR_EAST", "west": "DIR_WEST"}
RTC = {"day": "2026-01-02T16:00:00", "night": "2026-01-02T22:00:00"}

SPOTS = [  # (name, map, x, z, facing)
    ("01_coronet_yard", R207, *L.VIEWPOINTS["coronet_yard"][:2], "DIR_NORTH"),
    ("02_supply_ruts", R207, *L.VIEWPOINTS["supply_ruts"][:2], "DIR_EAST"),
    ("03_r206_barricade", R206, *L.VIEWPOINTS["r206_barricade"][:2], "DIR_NORTH"),
    ("04_cave_mouth", R207, 338, 713, "DIR_EAST"),
    ("05_junction_outpost", R207, 305, 708, "DIR_SOUTH"),
    ("06_r206_underpass", R206, 302, 651, "DIR_NORTH"),
]


def map_of(x, z):
    return R207 if z >= 704 else R206


def blocked_step(game, direction, results, label):
    st0 = game.state()
    m0, p0 = V.where(st0)
    for _ in range(3):
        game.cmd({"cmd": "press", "keys": [direction], "frames": 8})
        game.cmd({"cmd": "step", "frames": 16})
    st = V.settle(game, 200)
    m, p = V.where(st)
    V.expect(m == m0 and p == p0, f"{label}: walking {direction} from {p0} is blocked (still at {p})", results)


def read_bg(game, out_dir, run, name, label, mapname, x, z, facing, results, shots):
    V.warp(game, x, z, facing, results, mapname=mapname)
    game.cmd({"cmd": "press", "keys": ["A"], "frames": 8})
    opened, st = False, game.state()
    for _ in range(30):
        game.cmd({"cmd": "step", "frames": 10})
        st = game.state()
        if st.get("message_waiting") or st.get("script") is not None:
            opened = True
            break
    V.expect(opened, f"{label} at ({x}, {z}) facing {facing} opened (script={st.get('script')})", results)
    game.cmd({"cmd": "step", "frames": 60})
    V.shoot(game, out_dir, f"{run}_{name}_p1", shots, results)
    pages, closed = 0, False
    for _ in range(40):
        st = game.state()
        if V.is_field_idle(st):
            closed = True
            break
        game.cmd({"cmd": "press", "keys": ["A"], "frames": 8})
        game.cmd({"cmd": "step", "frames": 50})
        pages += 1
        if pages == 2:
            V.shoot(game, out_dir, f"{run}_{name}_p2", shots, results)
    V.expect(closed, f"{label} paged through and closed ({pages} presses)", results)
    m, p = V.where(game.state())
    V.expect(m == mapname and p == (x, z), f"{label} left the player idle at {p}", results)


def tour(game, out_dir, run, results, shots, gameplay):
    # keep the Route 207 counterpart scene from hijacking the cave-mouth tiles
    game.cmd({"cmd": "set_var", "name": "VAR_ROUTE_207_COUNTERPART_TRIGGER_STATE", "value": 1})
    for name, mapname, x, z, facing in SPOTS:
        V.warp(game, x, z, facing, results, mapname=mapname)
        game.cmd({"cmd": "step", "frames": 30})
        V.shoot(game, out_dir, f"{run}_{name}", shots, results)
    if not gameplay:
        return
    b = L.BG_MANIFEST
    read_bg(game, out_dir, run, "07_manifest_crate", "Route 207 manifest crate", R207, *b["read_from"],
            "DIR_NORTH", results, shots)
    blocked_step(game, "UP", results, "manifest crate (333,710)")
    b = L.BG_CLOSED_SIGN
    read_bg(game, out_dir, run, "08_road_closed_sign", "Route 206 ROAD CLOSED sign", R206, *b["read_from"],
            "DIR_NORTH", results, shots)
    # the barricade blocks; the 4-wide lane leads into the Cycling Road south gate
    V.warp(game, 300, 692, "DIR_NORTH", results, mapname=R206)
    blocked_step(game, "UP", results, "plaza barricade (300,691)")
    V.warp(game, 302, 694, "DIR_NORTH", results, mapname=R206)
    for k in range(5):
        st = V.walk_one(game, "UP")
        V.expect(V.where(st) == (R206, (302, 693 - k)), f"plaza lane step {k + 1}/5 -> {V.where(st)[1]}", results)
    st = V.walk_until_map(game, "UP", GATE_S)
    V.expect(V.where(st)[0] == GATE_S, f"walked into the Cycling Road south gate ({V.where(st)})", results)
    V.shoot(game, out_dir, f"{run}_09_south_gate", shots, results)
    # the road along the staging yard into Mt. Coronet
    V.warp(game, 322, 712, "DIR_EAST", results, mapname=R207)
    for k in range(18):
        st = V.walk_one(game, "RIGHT")
    V.expect(V.where(st) == (R207, (340, 712)), f"walked the supply road past the yard to {V.where(st)[1]}", results)
    st = V.walk_until_map(game, "RIGHT", CORONET)
    V.expect(V.where(st)[0] == CORONET, f"entered Mt. Coronet's south entrance ({V.where(st)})", results)
    V.shoot(game, out_dir, f"{run}_10_coronet_1f", shots, results)


def run_one(build_dir, out_dir, run, args, results, shots, gameplay):
    run_dir = tempfile.mkdtemp(prefix=f"dz-r206-{run}-")
    env = {"SIM_FIXED_RTC": RTC[run], "SIM_RENDERER": args.renderer}
    if sys.platform.startswith("linux") and args.renderer != "gpu":
        env["SIM_G2_GPU"] = "0"
    ok = True
    with open(os.path.join(out_dir, f"log_{run}.txt"), "w") as log:
        game = V.Game(build_dir, run_dir, log, extra_env=env, scale=args.scale)
        try:
            V.boot(game, args.save, results)
            tour(game, out_dir, run, results, shots, gameplay)
        except V.Failure as e:
            ok = False
            results.append(f"FAIL {e}")
            print(f"FAIL {e}", flush=True)
            try:
                log.write("LAST_STATE: " + json.dumps(game.state()) + "\n")
                V.shoot(game, out_dir, f"{run}_failure", shots, results)
            except Exception:
                pass
        finally:
            game.close()
            if os.path.exists(game.stderr_path):
                shutil.copy(game.stderr_path, os.path.join(out_dir, f"game_{run}.stderr.log"))
            shutil.rmtree(run_dir, ignore_errors=True)
        log.write("\n".join(results) + "\n")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("build_dir")
    ap.add_argument("output_dir")
    ap.add_argument("--night", action="store_true")
    ap.add_argument("--save", default=V.DEFAULT_SAVE)
    ap.add_argument("--renderer", choices=["gl", "gpu"], default="gl")
    ap.add_argument("--scale", type=int, default=2)
    args = ap.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    t0, all_ok, shots = time.time(), True, []
    for i, run in enumerate(["day", "night"] if args.night else ["day"]):
        results = []
        print(f"=== Routes 206-207 verification: {run} ({RTC[run]}) ===", flush=True)
        all_ok &= run_one(os.path.abspath(args.build_dir), args.output_dir, run, args, results, shots, i == 0)
    print(f"{'PASS' if all_ok else 'FAIL'} in {time.time() - t0:.1f}s; {len(shots)} screenshots in {args.output_dir}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
