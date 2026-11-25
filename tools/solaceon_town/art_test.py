#!/usr/bin/env python3
"""Headless in-game check of the Solaceon Town art pass (macOS app, SIM_CONTROL=stdio). Standard library only.

Usage: python3 tools/solaceon_town/art_test.py <build dir> <output dir> [--night] [--only day|night] [--save F]
       e.g. python3 tools/solaceon_town/art_test.py build_macos "/tmp/Solaceon Update/art_mac/game" --night

Built on tools/solaceon_town/interior/smoke_test.py (its Game client, walk/settle/shoot helpers and the boot: import
tools/battle_stage/emu/saves/eterna_forest_grass.sav, press through the title and Continue). Per run (day at
12:00; with --night a second process at 22:00 through SIM_FIXED_RTC):
  1. warps to each SPOTS tile in Solaceon Town and screenshots it (<out>/<run>_<spot>.bmp/.png);
  2. the offering candle twice, 10 frames apart (the fldtanime flicker: the two shots must differ there);
  3. walks north from (580,653) into the Sanctuary hall door, asserts MAP_HEADER_SOLACEON_SANCTUARY, walks back out
     and asserts the player is in front of the door again (screenshots in and out);
  4. walks both seams: from (560,642) north into Route 210 South and back, from (560,669) south into Route 209 and
     back, one tile at a time (every step must move the player; screenshots across each seam), and the seam columns
     x 557 / 563. --skip-route-209 stops on the seam row z 671 instead (Route 209 currently hangs on entry: its
     OnTransition script jumps to itself).
Exit status 0 when every assertion passed. <out>/log.txt has every command and reply.
"""
import argparse
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "interior"))
import smoke_test as S  # noqa: E402

TOWN = "MAP_HEADER_SOLACEON_TOWN"
SANCTUARY = "MAP_HEADER_SOLACEON_SANCTUARY"
NORTH, SOUTH = "MAP_HEADER_ROUTE_210_SOUTH", "MAP_HEADER_ROUTE_209"
# name -> (x, z, facing); the camera centres on the player
SPOTS = [
    ("01_north_road", 560, 643, "DIR_NORTH"),
    ("02_tent", 566, 646, "DIR_NORTH"),
    ("03_plaza_wall", 558, 654, "DIR_WEST"),
    ("04_garden", 562, 651, "DIR_EAST"),
    ("05_compound_gate", 580, 660, "DIR_NORTH"),
    ("06_forecourt_emblem", 580, 656, "DIR_NORTH"),
    ("07_hall_door", 580, 653, "DIR_NORTH"),
    ("08_excavation_gap", 595, 661, "DIR_NORTH"),
    ("09_kennel_yard", 552, 666, "DIR_NORTH"),
    ("10_south_exit", 560, 669, "DIR_SOUTH"),
    ("11_east_lane", 576, 666, "DIR_EAST"),
    ("12_compound_west", 573, 652, "DIR_EAST"),
]
CANDLE = (558, 657)          # beside the south offering (557,657)
RTC = {"day": "2026-01-02T12:00:00", "night": "2026-01-02T22:00:00"}


def boot(game, save, results):
    r = game.cmd({"cmd": "import_save", "path": os.path.abspath(save)})
    S.expect(r.get("ok"), f"imported {save}", results)
    for s in S.TITLE_STEPS:
        if "press" in s:
            game.cmd({"cmd": "press", "keys": [s["press"]], "frames": s.get("frames", 1)})
        else:
            game.cmd({"cmd": "step", "frames": s["step"]})
    for _ in range(120):
        st = game.state()
        if st.get("app") == "field" and st.get("player"):
            break
        game.cmd({"cmd": "press", "keys": ["B"], "frames": 10})
        game.cmd({"cmd": "step", "frames": 50})
    st = game.state()
    S.expect(st.get("app") == "field" and bool(st.get("player")), f"reached the field ({st.get('map')})", results)
    S.settle(game, 2400)


def warp(game, x, z, facing, results, mapname=TOWN):
    for _ in range(30):
        r = game.cmd({"cmd": "warp", "map": mapname, "x": x, "z": z, "dir": facing})
        if r.get("ok"):
            break
        game.cmd({"cmd": "press", "keys": ["B"], "frames": 10})
        game.cmd({"cmd": "step", "frames": 120})
    game.cmd({"cmd": "step", "frames": 240})
    st = S.settle(game)
    m, pos = S.where(st)
    S.expect(m == mapname and pos == (x, z), f"warped to {mapname} {pos}", results)
    game.cmd({"cmd": "step", "frames": 60})        # the fade-in finishes after the field is idle
    return st


def walk_until_map(game, key, want, frames=400):
    game.cmd({"cmd": "press", "keys": [key], "frames": 8})
    for _ in range(frames // 10):
        game.cmd({"cmd": "step", "frames": 10})
        if S.where(game.state())[0] == want:
            break
    st = S.settle(game)
    game.cmd({"cmd": "step", "frames": 120})
    return st


def tour(game, out, run, results, shots, cross_209=True):
    for name, x, z, facing in SPOTS:
        warp(game, x, z, facing, results)
        S.shoot(game, out, f"{run}_{name}", shots)
    # candle flicker: two frames of the fldtanime loop
    warp(game, CANDLE[0], CANDLE[1], "DIR_WEST", results)
    S.shoot(game, out, f"{run}_13_candle_a", shots)
    game.cmd({"cmd": "step", "frames": 10})
    S.shoot(game, out, f"{run}_13_candle_b", shots)
    a = open(os.path.join(out, f"{run}_13_candle_a.bmp"), "rb").read()
    b = open(os.path.join(out, f"{run}_13_candle_b.bmp"), "rb").read()
    S.expect(a != b, "the candle frames change (fldtanime sol_candle)", results)
    # the hall door: in and out
    warp(game, 580, 653, "DIR_NORTH", results)
    st = walk_until_map(game, "UP", SANCTUARY)
    m, pos = S.where(st)
    S.expect(m == SANCTUARY, f"walked into the hall door: {m} {pos}", results)
    S.shoot(game, out, f"{run}_14_hall_inside", shots)
    st = walk_until_map(game, "DOWN", TOWN)
    m, pos = S.where(st)
    S.expect(m == TOWN and pos in ((580, 652), (580, 653)), f"walked out of the hall: {m} {pos}", results)
    S.shoot(game, out, f"{run}_15_hall_out", shots)
    # seams, a tile at a time
    warp(game, 560, 642, "DIR_NORTH", results)
    for i in range(4):
        st = S.walk(game, "UP")
    m, pos = S.where(st)
    S.expect(m == NORTH and pos == (560, 638), f"north seam: walked into {m} {pos}", results)
    S.shoot(game, out, f"{run}_16_north_seam_r210", shots)
    for i in range(4):
        st = S.walk(game, "DOWN")
    m, pos = S.where(st)
    S.expect(m == TOWN and pos == (560, 642), f"north seam: walked back into {m} {pos}", results)
    S.shoot(game, out, f"{run}_17_north_seam_back", shots)
    warp(game, 560, 669, "DIR_SOUTH", results)
    if not cross_209:
        # Route 209's OnTransition loops forever on this branch (see --skip-route-209): walk to the seam row only
        for i in range(2):
            st = S.walk(game, "DOWN")
        m, pos = S.where(st)
        S.expect(m == TOWN and pos == (560, 671), f"south seam row reached: {m} {pos}", results)
        S.shoot(game, out, f"{run}_18_south_seam_edge", shots)
        for x in (557, 563):
            warp(game, x, 641, "DIR_NORTH", results)
            S.walk(game, "UP")
            st = S.walk(game, "UP")
            S.expect(S.where(st)[0] == NORTH, f"north seam column x {x} crosses into {NORTH}", results)
            warp(game, x, 670, "DIR_SOUTH", results)
            st = S.walk(game, "DOWN")
            S.expect(S.where(st)[1] == (x, 671), f"south seam column x {x}: walked onto the seam row", results)
        return
    for i in range(4):
        st = S.walk(game, "DOWN")
    m, pos = S.where(st)
    S.expect(m == SOUTH and pos == (560, 673), f"south seam: walked into {m} {pos}", results)
    S.shoot(game, out, f"{run}_18_south_seam_r209", shots)
    for i in range(4):
        st = S.walk(game, "UP")
    m, pos = S.where(st)
    S.expect(m == TOWN and pos == (560, 669), f"south seam: walked back into {m} {pos}", results)
    S.shoot(game, out, f"{run}_19_south_seam_back", shots)
    # walk the road edge to edge (x 557..563 seam columns at both ends are walkable)
    for x in (557, 563):
        warp(game, x, 641, "DIR_NORTH", results)
        st = S.walk(game, "UP")
        st = S.walk(game, "UP")
        S.expect(S.where(st)[0] == NORTH, f"north seam column x {x} crosses into {NORTH}", results)
        warp(game, x, 670, "DIR_SOUTH", results)
        st = S.walk(game, "DOWN")
        st = S.walk(game, "DOWN")
        S.expect(S.where(st)[0] == SOUTH, f"south seam column x {x} crosses into {SOUTH}", results)


def run_one(build_dir, out, run, save, results, shots, cross_209=True):
    run_dir = tempfile.mkdtemp(prefix=f"dz-solart-{run}-")
    ok = True
    with open(os.path.join(out, f"log_{run}.txt"), "w") as log:
        game = S.Game(build_dir, run_dir, log, extra_env={"SIM_FIXED_RTC": RTC[run]})
        try:
            boot(game, save, results)
            tour(game, out, run, results, shots, cross_209)
        except S.Failure as e:
            ok = False
            if not results or not results[-1].startswith("FAIL"):
                results.append(f"FAIL {e}")
                print(results[-1])
            try:
                S.shoot(game, out, f"{run}_failure", shots)
            except Exception:
                pass
        finally:
            game.close()
            shutil.copy(os.path.join(run_dir, "game.stderr.log"), os.path.join(out, f"game_{run}.stderr.log"))
            shutil.rmtree(run_dir, ignore_errors=True)
        log.write("\n".join(results) + "\n")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("build_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--save", default=S.DEFAULT_SAVE)
    ap.add_argument("--night", action="store_true", help="also run at 22:00")
    ap.add_argument("--only", choices=list(RTC))
    ap.add_argument("--skip-route-209", action="store_true",
                    help="do not cross into Route 209: on solaceon-mac its OnTransition script jumps to itself "
                         "(res/field/maps/route_209/scripts.s 'GoTo Route209_OnTransition'), so every entry to Route "
                         "209 hangs; walk onto the seam row z 671 instead")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    runs = [a.only] if a.only else (["day", "night"] if a.night else ["day"])
    t0 = time.time()
    ok = True
    shots = []
    for run in runs:
        results = []
        print(f"--- {run} ({RTC[run]})")
        ok &= run_one(os.path.abspath(a.build_dir), a.out_dir, run, a.save, results, shots, not a.skip_route_209)
    print(f"{'PASS' if ok else 'FAIL'} in {time.time() - t0:.0f}s; {len(shots)} screenshots in {a.out_dir}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
