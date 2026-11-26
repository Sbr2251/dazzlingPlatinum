#!/usr/bin/env python3
"""Headless smoke test of the Sanctuary hall (MAP_HEADER_SOLACEON_SANCTUARY) in the macOS app. Standard library only.

Usage: python3 tools/solaceon_town/interior/smoke_test.py <build dir> <output dir> [--save F | --new-game] [--arc2 N]
                                                           [--keep-run-dir]
       e.g. python3 tools/solaceon_town/interior/smoke_test.py build_macos "/tmp/Solaceon Update/interior_mac"

<build dir> is a built tree with `main` (tools/macos/build.sh dev -> build_macos). The game runs with
SIM_CONTROL=stdio (docs/headless_protocol.md) from a run dir of symlinks into the build dir, with a fresh save.

What it does:
  1. Boot to the field. Default: import a save (--save; default the repo's own
     tools/dazzling/test/fixtures/eterna_forest_grass.sav, an Arc 2 save in Eterna Forest) and press through the
     title and Continue, as the save_load_* scenarios do. --new-game instead replays
     tools/dazzling/test/scenarios/core_new_game_distortion_world_prologue.json; on solaceon-mac (49269afc8) that
     route hangs after the Distortion World flashback: the warp to Lake Verity runs LakeVerity_OnTransition and the
     map load never finishes (black screen, a field task running for good, so `warp` is refused). Same on the
     unmodified baseline build.
  2. Optionally sets VAR_ARC2_PROGRESS (--arc2), then warps to Solaceon Town one tile south of warp 2 (the door
     that leads to the Sanctuary) and walks north into it.
  3. Asserts the map is MAP_HEADER_SOLACEON_SANCTUARY and the player is on the arrival tile (10, 19).
  4. Walks entrance -> hall centre -> in front of the lectern -> under the emblem -> office doorway -> into the
     office, taking a
     screenshot at each spot (BMP, plus PNG when `sips` is available), then walks back to the exit mat, presses
     south and asserts the player is back in Solaceon Town on warp 2's tile.
Exit status 0 when every assertion passed. A log of every command and reply is written to <output dir>/log.txt.
"""
import argparse
import json
import os
import select
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
PROLOGUE = os.path.join(ROOT, "tools", "dazzling", "test", "scenarios", "core_new_game_distortion_world_prologue.json")
DEFAULT_SAVE = os.path.join(ROOT, "tools", "dazzling", "test", "fixtures", "eterna_forest_grass.sav")
TITLE_STEPS = [{"step": 900}] + [{"press": "A", "frames": 10}, {"step": 290}] * 8 + [{"step": 600}]

SANCTUARY = "MAP_HEADER_SOLACEON_SANCTUARY"
TOWN = "MAP_HEADER_SOLACEON_TOWN"
TOWN_DOOR = (580, 652)          # Solaceon Town warp 2 (res/field/maps/solaceon_town/events.json)
ARRIVAL = (10, 19)              # the Sanctuary's warp 0, the exit mat (tools/solaceon_town/interior/layout.py)
DELTA = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
# (name, path of moves from the previous spot); tiles in layout.py
TOUR = [
    ("1_entrance", []),
    ("2_hall_centre", ["UP"] * 6),                                   # (10, 13), the aisle between the pews
    ("3_emblem", ["UP"] * 3),                                        # (10, 10), in front of the lectern
    ("3b_north_wall", ["LEFT"] * 3 + ["UP"] * 3 + ["RIGHT"] * 3),    # (10, 7), under the emblem (reading tile)
    ("4_office_doorway", ["RIGHT"] * 8 + ["DOWN"] * 6 + ["RIGHT"]),  # (19, 13), the doorway
    ("5_office", ["RIGHT", "RIGHT", "UP", "UP"]),                    # (21, 11), inside the office
]
BACK = ["DOWN", "DOWN", "LEFT", "LEFT", "LEFT", "UP", "UP", "UP"] + ["LEFT"] * 8 + ["DOWN"] * 9   # -> (10, 19)
SKIP_ENTRIES = ("save.bin", "save-backups", "build.ninja", "compile_commands.json", "sim_config.ini")


class Failure(Exception):
    pass


class Game:
    def __init__(self, build_dir, run_dir, log, extra_env=None, prj_config=None):
        self.log = log
        main = os.path.join(build_dir, "main")
        if not os.path.exists(main):
            raise SystemExit(f"{main} not found: build first (tools/macos/build.sh dev)")
        for entry in os.listdir(build_dir):
            if entry in SKIP_ENTRIES or entry.startswith(("meson-", "save.bin")) or entry.endswith((".p", ".log")):
                continue
            os.symlink(os.path.join(build_dir, entry), os.path.join(run_dir, entry))
        with open(os.path.join(run_dir, "sim_config.ini"), "w") as f:
            f.write("InternalResolutionScale=2\n")
        if prj_config:   # sim_config_prj.ini [General] overrides (the game writes the rest with defaults)
            with open(os.path.join(run_dir, "sim_config_prj.ini"), "w") as f:
                f.write("[General]\n" + "".join(f"{k}={v}\n" for k, v in prj_config.items()))
        env = dict(os.environ)
        env.update({"SIM_HEADLESS": "1", "SIM_CONTROL": "stdio", "SIM_FIXED_RTC": "2026-01-02T12:00:00",
                    "SIM_SEED": "12345", "SIM_SAVE_PATH": os.path.join(run_dir, "save.bin"),
                    "SDL_MAC_BACKGROUND_APP": "1"})
        env.update(extra_env or {})
        self.stderr = open(os.path.join(run_dir, "game.stderr.log"), "wb")
        self.proc = subprocess.Popen(["./main"], cwd=run_dir, env=env, stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=self.stderr, text=True, bufsize=1)

    def cmd(self, obj, timeout=None):
        frames = obj.get("frames", 0)
        timeout = timeout or max(120, frames / 10 + 120)
        line = json.dumps(obj)
        self.proc.stdin.write(line + "\n")
        self.proc.stdin.flush()
        ready, _, _ = select.select([self.proc.stdout], [], [], timeout)
        if not ready:
            raise Failure(f"no reply to {line} within {timeout}s")
        reply = self.proc.stdout.readline()
        if not reply:
            raise Failure(f"game exited ({self.proc.poll()}) after {line}; see game.stderr.log")
        if obj.get("cmd") not in ("step", "press") or frames > 60:
            self.log.write(f">> {line}\n<< {reply.strip()}\n")
        return json.loads(reply)

    def state(self):
        return self.cmd({"cmd": "state"})

    def close(self):
        try:
            if self.proc.poll() is None:
                self.cmd({"cmd": "quit"}, timeout=10)
        except Exception:
            pass
        try:
            self.proc.wait(timeout=10)
        except Exception:
            self.proc.kill()
        self.stderr.close()


def where(st):
    p = st.get("player") or {}
    return st.get("map"), (p.get("x"), p.get("z"))


def settle(game, frames=600):
    """Steps until the field is idle (no script, no message) or `frames` run out."""
    for _ in range(frames // 20):
        st = game.state()
        if st.get("app") == "field" and st.get("script") is None and not st.get("message_waiting"):
            return st
        game.cmd({"cmd": "step", "frames": 20})
    return game.state()


def walk(game, direction, tries=6):
    """One tile in `direction`; returns the new state. Fails if the player does not move."""
    st0 = game.state()
    m0, (x0, z0) = where(st0)
    dx, dz = DELTA[direction]
    for _ in range(tries):
        game.cmd({"cmd": "press", "keys": [direction], "frames": 6})
        game.cmd({"cmd": "step", "frames": 14})
        st = game.state()
        m, (x, z) = where(st)
        if m != m0 or (x, z) == (x0 + dx, z0 + dz):
            return st
        if (x, z) != (x0, z0):
            raise Failure(f"walking {direction} from {(x0, z0)} ended at {(x, z)}")
    raise Failure(f"could not walk {direction} from {(x0, z0)} on {m0}")


def shoot(game, out_dir, name, shots):
    bmp = os.path.join(out_dir, name + ".bmp")
    game.cmd({"cmd": "screenshot", "path": bmp})
    if shutil.which("sips"):
        png = os.path.join(out_dir, name + ".png")
        subprocess.run(["sips", "-s", "format", "png", bmp, "--out", png], capture_output=True)
    shots.append(bmp)


def expect(cond, msg, results):
    results.append(("ok  " if cond else "FAIL") + " " + msg)
    print(results[-1])
    if not cond:
        raise Failure(msg)


def run(game, out_dir, arc2, save, results, shots):
    # 1. boot to the field: a save through title/Continue, or a new game through the prologue
    if save:
        r = game.cmd({"cmd": "import_save", "path": os.path.abspath(save)})
        expect(r.get("ok"), f"imported {save}", results)
        steps = TITLE_STEPS
    else:
        steps = json.load(open(PROLOGUE))["steps"]
    for s in steps:
        if "press" in s:
            game.cmd({"cmd": "press", "keys": [s["press"]], "frames": s.get("frames", 1)})
        elif "step" in s:
            game.cmd({"cmd": "step", "frames": s["step"]})
    # Continue opens the Journal first when the save has one (FieldTask_LoadSavedGameMap waits for it): until the
    # player object exists, press B to close it.
    for _ in range(120):
        st = game.state()
        if st.get("app") == "field" and st.get("player"):
            break
        game.cmd({"cmd": "press", "keys": ["B"], "frames": 10})
        game.cmd({"cmd": "step", "frames": 50})
    st = game.state()
    expect(st.get("app") == "field" and bool(st.get("player")),
           f"reached the field ({st.get('map')} {where(st)[1]})", results)
    st = settle(game, 2400)

    # 2. story state, warp next to the door, walk in
    if arc2 is not None:
        game.cmd({"cmd": "set_var", "name": "VAR_ARC2_PROGRESS", "value": arc2})
    for _ in range(30):
        r = game.cmd({"cmd": "warp", "map": TOWN, "x": TOWN_DOOR[0], "z": TOWN_DOOR[1] + 1, "dir": "DIR_NORTH"})
        if r.get("ok"):
            break
        game.cmd({"cmd": "press", "keys": ["A"], "frames": 10})   # a field script still running: finish it
        game.cmd({"cmd": "step", "frames": 120})
    game.cmd({"cmd": "step", "frames": 240})
    st = settle(game)
    m, pos = where(st)
    expect(m == TOWN and pos == (TOWN_DOOR[0], TOWN_DOOR[1] + 1), f"warped to {TOWN} {pos} (below warp 2)", results)
    shoot(game, out_dir, "0_town_door", shots)
    game.cmd({"cmd": "press", "keys": ["UP"], "frames": 8})
    for _ in range(40):
        game.cmd({"cmd": "step", "frames": 10})
        if where(game.state())[0] == SANCTUARY:
            break
    st = settle(game)
    m, pos = where(st)
    expect(m == SANCTUARY, f"walked into the door: map {m}", results)
    expect(pos == ARRIVAL, f"arrived on the exit mat {pos} (want {ARRIVAL})", results)
    game.cmd({"cmd": "step", "frames": 120})   # the warp's fade-in runs on after the field is idle

    # 3. tour
    for name, path in TOUR:
        for d in path:
            walk(game, d)
        st = settle(game, 200)
        m, pos = where(st)
        expect(m == SANCTUARY, f"{name}: at {pos}", results)
        shoot(game, out_dir, name, shots)

    # 4. back out
    for d in BACK:
        walk(game, d)
    m, pos = where(game.state())
    expect((m, pos) == (SANCTUARY, ARRIVAL), f"back on the exit mat {pos}", results)
    game.cmd({"cmd": "press", "keys": ["DOWN"], "frames": 8})
    for _ in range(40):
        game.cmd({"cmd": "step", "frames": 10})
        if where(game.state())[0] == TOWN:
            break
    st = settle(game)
    game.cmd({"cmd": "step", "frames": 120})
    m, pos = where(st)
    expect(m == TOWN, f"left through the exit mat: map {m} at {pos}", results)
    expect(pos in (TOWN_DOOR, (TOWN_DOOR[0], TOWN_DOOR[1] + 1)), f"outside the door {pos} (warp 2 {TOWN_DOOR})",
           results)
    shoot(game, out_dir, "6_back_in_town", shots)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("build_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--save", default=DEFAULT_SAVE, help="raw .sav/.dsv to import (default: %(default)s)")
    ap.add_argument("--new-game", action="store_true", help="start a new game instead (see the note above)")
    ap.add_argument("--arc2", type=int, default=None, help="set VAR_ARC2_PROGRESS before warping (e.g. 45)")
    ap.add_argument("--keep-run-dir", action="store_true")
    a = ap.parse_args()
    build_dir = os.path.abspath(a.build_dir)
    os.makedirs(a.out_dir, exist_ok=True)
    run_dir = tempfile.mkdtemp(prefix="dz-sanctuary-")
    results, shots = [], []
    t0 = time.time()
    with open(os.path.join(a.out_dir, "log.txt"), "w") as log:
        game = Game(build_dir, run_dir, log)
        try:
            run(game, a.out_dir, a.arc2, None if a.new_game else a.save, results, shots)
            ok = True
        except Failure as e:
            ok = False
            if not results or not results[-1].startswith("FAIL"):
                print(f"FAIL {e}")
                results.append(f"FAIL {e}")
            try:
                log.write(json.dumps(game.state()) + "\n")
                shoot(game, a.out_dir, "failure", shots)
            except Exception:
                pass
        finally:
            game.close()
            shutil.copy(os.path.join(run_dir, "game.stderr.log"), os.path.join(a.out_dir, "game.stderr.log"))
            if not a.keep_run_dir:
                shutil.rmtree(run_dir, ignore_errors=True)
        log.write("\n".join(results) + "\n")
    print(f"{'PASS' if ok else 'FAIL'} in {time.time() - t0:.0f}s; screenshots: " + ", ".join(shots))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
