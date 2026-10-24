"""Regression runner: play every rift from its entry to its totem fight
start (and the Lost Tower visit-1 shadow-wall exit), using the
recorded solutions in dwlib.SOLUTIONS. One worker process per
(rift, leg) -- py-desmume segfaults on a second DeSmuME() per process,
so the parent spawns a worker per leg and aggregates.

Usage:

    SDL_VIDEODRIVER=dummy ~/.venvs/desmume39/bin/python \\
        tools/distortion_world/emu/rifts_regress.py OUTDIR [--rift rp ef ...]
    SDL_VIDEODRIVER=dummy ~/.venvs/desmume39/bin/python \\
        tools/distortion_world/emu/rifts_regress.py --worker rp --leg totem \\
        --rom out/dazzlingPlatinum.nds --outdir /tmp/x

Output: <OUTDIR>/report.md + report.json, and a labelled frame strip
per leg at <OUTDIR>/<rift>_<leg>/strip.png.

Legs:
  totem  replay the recorded solution; for totem rifts, pump the
         totem script's intro until the battle menu is up; for
         Arc 1 / Lost Tower visit 1, reaching the goal tile is the pass.
  exit   Lost Tower visit 1 only: after the vein, step to the shadow
         wall (15,23) and assert the warp lands on Lost Tower 2F
         (7,8). The other rifts have no pre-calm exit in the stubs;
         their post-calm exit warps are QA's chained playthrough.

Eterna Forest's honeycomb is timed (213-frame cycle, solid 153): the
crossing is 9 fast steps, and the worker retries it across cycles --
after a fall it walks the (fast) prefix back from the hive and shifts
its wait by 30 frames, up to 12 attempts. Cost note: the retry loop
is the only non-deterministic part of the runner; a honeycomb fall
mid-run is expected evidence (the fall path works), not a failure.

Exit status 1 if any leg fails.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import dwlib
from dwlib import DwSession, RIFTS, SOLUTIONS

ALL_RIFTS = ["arc1", "rp", "ef", "r214", "r213", "lt1", "lt2"]
TOTEM_RIFTS = {"rp", "ef", "r214", "r213", "lt2"}
# Rifts whose entry + route are proven in dwlib.SOLUTIONS. The rest
# report NO SOLUTION until their exploration lands (their worker is
# skipped, not failed).
HAVE_SOLUTION = {"arc1", "rp", "ef", "r214", "r213", "lt1", "lt2"}

# EF: split of SOLUTIONS["ef"] into the slow prefix to (45,10,32) and
# the 9 fast crossing steps to the totem tile (45,10,41).
EF_PREFIX = "L L L " + "R " * 15 + "U " * 14 + "L " * 4
EF_CROSS = "U " * 9
EF_FAST_PREFIX = "R " * 15 + "U " * 14 + "L " * 4  # from the hive, after a fall

# LT1 exit: after the vein (13,23), two steps east to the shadow wall.
LT1_EXIT_TAIL = "R R"


def _snap_frames(session, frames, label):
    session.emu.snap(label, frames)


def _run_totem(session, key, frames):
    """Returns (passed, detail)."""
    rift = RIFTS[key]
    if key == "ef":
        return _run_ef(session, frames)
    # Stop the moment the battle menu is up: a totem hook can fire
    # before the last recorded move (r213's island), and the rest of
    # the string would then press into the battle menu's cursor.
    stop = (lambda _trace: session.emu.battle_menu_up()) \
        if key in TOTEM_RIFTS else None
    session.replay(SOLUTIONS[key], frames_out=frames, label=f"{key}-totem",
                   stop=stop)
    tile = session.player_tile_or_none()
    if key in TOTEM_RIFTS:
        if session.wait_battle_menu(max_frames=3000):
            return True, f"totem battle menu up at {tile}"
        return False, f"no battle menu after totem script (tile {tile})"
    if tile == rift.goal_tile:
        return True, f"reached goal {tile}"
    return False, f"ended at {tile}, want goal {rift.goal_tile}"


def _run_ef(session, frames):
    """Eterna Forest: slow prefix to (45,10,32), then adaptive fast
    crossings of the honeycomb."""
    session.replay(EF_PREFIX, frames_out=frames, label="ef-prefix")
    wait = 0
    for attempt in range(12):
        if session.player_tile_or_none() != (45, 10, 32):
            return False, f"attempt {attempt}: not at (45,10,32) but {session.player_tile_or_none()}"
        session.emu.run(wait)
        trace = session.replay(EF_CROSS, frames_out=frames, label=f"ef-cross{attempt}",
                               fast=True)
        tile = session.player_tile_or_none()
        if tile == (45, 10, 41):
            if session.wait_battle_menu(max_frames=3000):
                return True, f"totem battle menu up after {attempt + 1} crossing attempt(s)"
            return False, "totem tile reached, no battle menu"
        fell = any(st.get("fell") for st in trace) or tile == (40, 1, 22)
        if fell:
            # Back from the hive, fast, and shift the phase.
            session.replay(EF_FAST_PREFIX, frames_out=frames,
                           label=f"ef-back{attempt}", fast=True)
            wait += 30
            continue
        return False, f"attempt {attempt}: ended at {tile} (not the totem, no fall)"
    return False, "honeycomb crossing failed after 12 attempts"


def _run_exit_lt1(session, frames):
    session.replay(SOLUTIONS["lt1"], frames_out=frames, label="lt1-vein")
    session.replay(LT1_EXIT_TAIL, frames_out=frames, label="lt1-wall")
    session.pump_text(max_frames=1800)
    tile = session.player_tile_or_none()
    if session.current_map() == 358 and tile is not None \
            and (tile[0], tile[2]) == (7, 8):
        return True, f"shadow-wall exit landed on Lost Tower 2F at {tile}"
    return False, f"exit ended map {session.current_map()} tile {tile}, want 358 (7,8)"


class CappedList(list):
    """A frame list that drops the oldest frames past 200, so a
    long retry loop (the honeycomb) cannot balloon memory (a full
    frame is ~300 KB). The strip is built from what survives."""

    def append(self, item):
        if len(self) >= 200:
            del self[:40]
        super().append(item)


def worker(args):
    key, leg = args.rift, args.leg
    outdir = pathlib.Path(args.outdir) / f"{key}_{leg}"
    outdir.mkdir(parents=True, exist_ok=True)
    result = {"rift": key, "leg": leg, "pass": False, "detail": "",
              "tile": None, "frames": 0, "strip": None, "error": None,
              "seconds": 0.0}
    start = time.time()
    frames = CappedList()
    try:
        with DwSession(args.rom, outdir=str(outdir)) as session:
            session.boot_overworld_rift(key)
            if leg == "totem":
                ok, detail = _run_totem(session, key, frames)
            elif leg == "exit" and key == "lt1":
                ok, detail = _run_exit_lt1(session, frames)
            else:
                ok, detail = False, f"no {leg} leg for {key}"
            result["pass"], result["detail"] = ok, detail
            result["tile"] = list(session.player_tile_or_none() or [])
            result["frames"] = session.emu.frame
            strip = session.strip(frames, outdir / "strip.png",
                                  f"{key} {leg}", cols=8, scale=0.5)
            result["strip"] = str(strip) if strip else None
    except Exception as exc:  # noqa: BLE001 -- worker reports, never raises
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["detail"] = "worker exception"
    result["seconds"] = round(time.time() - start, 1)
    (outdir / "result.json").write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))
    return 0 if result["pass"] else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("outdir_pos", nargs="?", default=None)
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--rift", nargs="*", default=ALL_RIFTS)
    ap.add_argument("--rom", default="out/dazzlingPlatinum.nds")
    ap.add_argument("--worker", action="store_true")
    ap.add_argument("--leg", default="totem")
    a = ap.parse_args()
    a.outdir = a.outdir or a.outdir_pos or "/tmp/dwp/harness/rifts_regress"
    if a.worker:
        a.rift = a.rift[0] if isinstance(a.rift, list) else a.rift
        return worker(a)
    outdir = pathlib.Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    legs = []
    for key in a.rift:
        if key not in HAVE_SOLUTION:
            legs.append((key, "totem", "NO SOLUTION"))
            continue
        legs.append((key, "totem", None))
        if key == "lt1":
            legs.append((key, "exit", None))
    results = []
    for key, leg, skip in legs:
        if skip:
            results.append({"rift": key, "leg": leg, "pass": False,
                            "detail": skip, "tile": None, "frames": 0,
                            "strip": None, "error": None, "seconds": 0.0,
                            "skipped": True})
            continue
        cmd = [sys.executable, str(pathlib.Path(__file__).resolve()), "--worker",
               "--rift", key, "--leg", leg, "--rom", a.rom,
               "--outdir", str(outdir)]
        import os
        env = dict(os.environ)
        env["SDL_VIDEODRIVER"] = "dummy"
        proc = subprocess.run(cmd, capture_output=True, text=True, env=env,
                              timeout=3600)
        try:
            res = json.loads((outdir / f"{key}_{leg}" / "result.json").read_text())
        except Exception:  # noqa: BLE001
            res = {"rift": key, "leg": leg, "pass": False,
                   "detail": "worker produced no result.json",
                   "tile": None, "frames": 0, "strip": None,
                   "error": (proc.stdout + proc.stderr)[-2000:], "seconds": 0.0}
        res["skipped"] = False
        results.append(res)
    (outdir / "report.json").write_text(json.dumps(results, indent=1))
    lines = ["# Rifts regression", "",
             "| rift | leg | result | tile | frames | detail |",
             "|---|---|---|---|---|---|"]
    for r in results:
        status = "SKIP" if r.get("skipped") else ("PASS" if r["pass"] else "FAIL")
        lines.append(f"| {r['rift']} | {r['leg']} | {status} | {r['tile']} | "
                     f"{r['frames']} | {r['detail']} |")
        if r.get("error"):
            lines.append(f"| | | | | | error: {r['error'][:300]} |")
    lines += ["", "Frame strips: `<rift>_<leg>/strip.png` (labels are `label @frame`)."]
    (outdir / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0 if all(r["pass"] or r.get("skipped") for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
