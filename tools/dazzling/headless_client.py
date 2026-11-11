#!/usr/bin/env python3
"""Minimal example client for the SIM_CONTROL=stdio lockstep protocol.

Starts the game headless, sends one JSON command per line on stdin and reads one
JSON reply per line from stdout (game logs go to the game's stderr, inherited here).
See docs/headless_protocol.md for the full protocol. The scenario runner and test
suite live with debug-suite; this is only a demonstrable example.

Usage:
    python3 tools/dazzling/headless_client.py --run-dir <dir> [--save <file.sav>] \
        [--shot out.bmp] [--steps 600]

<dir> is a run directory whose entries symlink to the build directory's contents
(the game reads its files relative to the cwd), e.g. build_linux on Linux or
build_macos on macOS.
"""
import argparse
import json
import os
import subprocess
import sys


class HeadlessGame:
    def __init__(self, run_dir, save=None, seed=12345, rtc="2026-01-02T03:04:05", extra_env=None):
        env = dict(os.environ)
        env.update({
            "SIM_HEADLESS": "1",
            "SIM_CONTROL": "stdio",
            "SIM_FIXED_RTC": rtc,
            "SIM_SEED": str(seed),
            # macOS: never show the game in the Dock/app switcher
            "SDL_MAC_BACKGROUND_APP": "1",
        })
        if save:
            env["SIM_SAVE_PATH"] = os.path.join(run_dir, "save.bin")
        if extra_env:
            env.update(extra_env)
        self.proc = subprocess.Popen(
            ["./main"], cwd=run_dir, env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1,
        )
        self.save = save

    def cmd(self, obj):
        """Send one command, return its parsed reply. step/press/touch reply when done."""
        line = json.dumps(obj)
        print(">>", line)
        self.proc.stdin.write(line + "\n")
        self.proc.stdin.flush()
        reply = self.proc.stdout.readline()
        if not reply:
            raise RuntimeError("game closed the protocol stream (exit %s)" % self.proc.poll())
        print("<<", reply.strip())
        return json.loads(reply)

    def close(self):
        """Quit the game and always reap it (kill if it does not exit)."""
        try:
            self.cmd({"cmd": "quit"})
        except Exception:
            pass
        try:
            self.proc.wait(timeout=10)
        except Exception:
            self.proc.kill()
            self.proc.wait()

    def __del__(self):
        try:
            if self.proc.poll() is None:
                self.proc.kill()
                self.proc.wait()
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, help="run dir with symlinks to the build output")
    ap.add_argument("--save", help="raw .sav to import at boot")
    ap.add_argument("--steps", type=int, default=600)
    ap.add_argument("--shot", default="shot.bmp")
    args = ap.parse_args()

    game = HeadlessGame(args.run_dir, save=args.save)
    try:
        if args.save:
            print(game.cmd({"cmd": "import_save", "path": os.path.abspath(args.save)}))
        print(game.cmd({"cmd": "step", "frames": args.steps}))
        print(game.cmd({"cmd": "state"}))
        print(game.cmd({"cmd": "screenshot", "path": os.path.abspath(os.path.join(args.run_dir, args.shot))}))
        print(game.cmd({"cmd": "press", "keys": ["A"], "frames": 2}))
        print(game.cmd({"cmd": "state"}))
    finally:
        game.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
