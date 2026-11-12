#!/usr/bin/env python3
"""Random-input soak driver for the headless game.

Drives one game process with seeded random presses/touches for N frames,
wandering the overworld and poking at menus (bag, party, summary, Pokedex,
PC box, battle menus when a battle starts). Any sanitizer report aborts the
game (ASAN_OPTIONS=abort_on_error=1 / UBSAN_OPTIONS=halt_on_error=1), which
surfaces here as a closed protocol stream / nonzero exit -> this script exits
nonzero. A clean run prints a one-line summary and exits 0.

Usage:
  LP_NUM_THREADS=2 python3 tools/dazzling/test/soak.py \
      --game build_asan/main --frames 6000 --seed 7 \
      [--save /path/to/A1-03....sav] [--work-dir /tmp/soak1]

Environment is inherited, so run with the sanitizer options set, e.g.
  ASAN_OPTIONS=detect_leaks=0:abort_on_error=1 \
  UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1
"""
import argparse
import json
import os
import random
import subprocess
import sys
import tempfile

KEYS = ["A", "B", "X", "Y", "START", "SELECT", "UP", "DOWN", "LEFT", "RIGHT", "L", "R"]

# Menu-driving sequences: open a menu, wander it, back out. Weighted so the
# soak spends most frames walking the overworld and some frames in menus.
MENU_SEQUENCES = [
    ["X"],                      # main menu
    ["X", "A"],                 # bag (first entry)
    ["X", "DOWN", "A"],         # party
    ["X", "DOWN", "DOWN", "A"],  # trainer card / Pokedex-ish entries
    ["START"],                  # Poketch / misc
]


class SoakError(Exception):
    pass


class QuietGame:
    """Minimal SIM_CONTROL=stdio client (HeadlessGame prints every line;
    a soak would spam thousands of lines, so this stays quiet)."""

    def __init__(self, game_path, work_dir, save=None, seed=12345):
        self.dir = work_dir
        os.makedirs(work_dir, exist_ok=True)
        game_dir = os.path.dirname(os.path.abspath(game_path))
        for entry in os.listdir(game_dir):
            if entry in ("meson-info", "save.bin", "save-backups") or entry.startswith("meson-") \
                    or entry.endswith((".p", ".log")) or entry.startswith("save.bin"):
                continue
            dst = os.path.join(work_dir, entry)
            if not os.path.lexists(dst):
                os.symlink(os.path.join(game_dir, entry), dst)
        with open(os.path.join(work_dir, "sim_config.ini"), "w") as f:
            f.write("InternalResolutionScale=1\n")
        env = dict(os.environ)
        env.update({
            "SIM_HEADLESS": "1", "SIM_CONTROL": "stdio",
            "SIM_FIXED_RTC": "2026-01-01T12:00:00", "SIM_SEED": str(seed),
            "SIM_SAVE_PATH": os.path.join(work_dir, "save.bin"),
            "SDL_MAC_BACKGROUND_APP": "1",
        })
        self._stderr = open(os.path.join(work_dir, "game.stderr.log"), "wb")
        self.proc = subprocess.Popen(
            ["./main"], cwd=work_dir, env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=self._stderr, text=True, bufsize=1)
        self.save = save

    def cmd(self, obj, timeout=120):
        if self.proc.poll() is not None:
            raise SoakError(f"game exited early (exit {self.proc.returncode}); "
                            f"see stderr in {self.dir}/game.stderr.log")
        try:
            self.proc.stdin.write(json.dumps(obj) + "\n")
            self.proc.stdin.flush()
        except BrokenPipeError:
            raise SoakError(f"game closed stdin (exit {self.proc.poll()}); "
                            f"see stderr in {self.dir}/game.stderr.log")
        line = self.proc.stdout.readline()
        if not line:
            raise SoakError(f"game closed stdout (exit {self.proc.poll()}); "
                            f"see stderr in {self.dir}/game.stderr.log")
        reply = json.loads(line)
        if isinstance(reply, dict) and reply.get("ok") is False:
            raise SoakError(f"command {obj} failed: {reply.get('error')}")
        return reply

    def close(self):
        try:
            if self.proc.poll() is None:
                try:
                    self.proc.stdin.write(json.dumps({"cmd": "quit"}) + "\n")
                    self.proc.stdin.flush()
                except Exception:
                    pass
                try:
                    self.proc.wait(timeout=5)
                except Exception:
                    self.proc.kill()
                    self.proc.wait()
        finally:
            try:
                self._stderr.close()
            except Exception:
                pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default="build_asan/main")
    ap.add_argument("--frames", type=int, default=6000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--save", default=None)
    ap.add_argument("--work-dir", default=None)
    args = ap.parse_args()

    save = args.save
    if not save:
        for cand in (
            "/data/repos/dp-wt/pret-sync-notes/saves/raw_sav/A1-03_route201_to_sandgem.sav",
            os.path.expanduser("~/Downloads/dazzling_platinum_test_saves_v2/raw_sav/A1-03_route201_to_sandgem.sav"),
            os.path.expanduser("~/Downloads/dazzlingPlatinum-mega-test.sav"),
        ):
            if os.path.exists(cand):
                save = cand
                break

    work = args.work_dir or tempfile.mkdtemp(prefix="dz-soak-")
    rng = random.Random(args.seed)
    game = QuietGame(args.game, work, save=save, seed=args.seed)
    try:
        if save:
            game.cmd({"cmd": "import_save", "path": os.path.abspath(save)})
        # Reach the field: mash A like the scenario runner does.
        for _ in range(200):
            game.cmd({"cmd": "press", "keys": ["A"], "frames": 2})
            game.cmd({"cmd": "step", "frames": 58})
            st = game.cmd({"cmd": "state"})
            if (st.get("state") or st).get("app") == "field" or st.get("app") == "field":
                break
        frames = 0
        presses = 0
        touches = 0
        while frames < args.frames:
            r = rng.random()
            if r < 0.55:
                # Walk: hold a direction for a while.
                key = rng.choice(["UP", "DOWN", "LEFT", "RIGHT"])
                n = rng.choice([10, 30, 60, 120])
                game.cmd({"cmd": "press", "keys": [key], "frames": min(n, args.frames - frames)})
                frames += n
            elif r < 0.85:
                # Single press / menu sequence.
                seq = rng.choice(MENU_SEQUENCES + [[rng.choice(KEYS)]])
                for key in seq:
                    if frames >= args.frames:
                        break
                    game.cmd({"cmd": "press", "keys": [key], "frames": 10})
                    game.cmd({"cmd": "step", "frames": 20})
                    frames += 30
                    presses += 1
                game.cmd({"cmd": "press", "keys": ["B"], "frames": 10})
                game.cmd({"cmd": "step", "frames": 20})
                frames += 30
            else:
                # Random touch (menus are touch-first).
                x = rng.randint(0, 255)
                y = rng.randint(0, 191)
                game.cmd({"cmd": "touch", "x": x, "y": y, "frames": 10})
                game.cmd({"cmd": "step", "frames": 20})
                frames += 30
                touches += 1
            if frames % 600 < 60:
                game.cmd({"cmd": "state"})
        st = game.cmd({"cmd": "state"})
        app = (st.get("state") or st).get("app", st.get("app"))
        print(f"soak: OK frames={frames} presses={presses} touches={touches} "
              f"seed={args.seed} final_app={app} work={work}")
        return 0
    except SoakError as e:
        print(f"soak: FAIL {e}", file=sys.stderr)
        return 1
    finally:
        game.close()


if __name__ == "__main__":
    sys.exit(main())
