"""Game process handling for render_compare: one headless lockstep game per
configuration, driven in pairs so both configurations always see the same
command stream."""
import json
import os
import select
import shlex
import subprocess
import time

FIXED_RTC = "2026-01-01T12:00:00"
FIXED_SEED = "12345"

# Build-directory entries not linked into a run dir: saves, build metadata and
# files the game may write at run time (those would otherwise be written
# through the symlink into the build directory).
SKIP_ENTRIES = {"save.bin", "save-backups", "build.ninja", "compile_commands.json",
                "sim_config.ini", "imgui.ini", "DbgLog.txt", "log.txt"}


class GameDied(Exception):
    def __init__(self, side, msg):
        super().__init__(msg)
        self.side = side


class CommandFailed(Exception):
    def __init__(self, cmd, reply):
        super().__init__("command %s failed: %s" % (json.dumps(cmd), json.dumps(reply)))
        self.cmd, self.reply = cmd, reply


def parse_env(text):
    """'A=1 B="x y"' -> {'A': '1', 'B': 'x y'}."""
    env = {}
    for tok in shlex.split(text or ""):
        if "=" not in tok:
            raise ValueError("expected NAME=VALUE in %r" % tok)
        k, v = tok.split("=", 1)
        env[k] = v
    return env


def make_run_dir(game_path, run_dir, scale, layout="vertical"):
    """Run dir whose entries link to the game's directory (the game reads its
    data relative to cwd) plus a private sim_config.ini. Returns the argv."""
    game_path = os.path.abspath(game_path)
    game_dir = os.path.dirname(game_path)
    os.makedirs(run_dir, exist_ok=True)
    for entry in os.listdir(game_dir):
        if entry in SKIP_ENTRIES or entry.startswith(("meson-", "save.bin")) or entry.endswith((".p", ".log")):
            continue
        dst = os.path.join(run_dir, entry)
        if not os.path.lexists(dst):
            os.symlink(os.path.join(game_dir, entry), dst)
    with open(os.path.join(run_dir, "sim_config.ini"), "w") as f:
        f.write("[General]\nInternalResolutionScale=%d\nWindowHeight=0\nWindowWidth=0\nFullScreen=false\n"
                "MasterVolume=127\nScreenLayout=%s\nSwapScreens=false\nVsyncInterval=0\nCapFrameRate=false\n"
                "MacAddr=98e255c2da7e\n" % (scale, layout))
    return ["./" + os.path.basename(game_path)]


class Game:
    """One headless game process speaking the SIM_CONTROL=stdio protocol."""

    def __init__(self, side, game_path, work_dir, env_extra, scale=2, nice=10, save=None):
        self.side = side
        self.dir = os.path.join(work_dir, "run")
        argv = make_run_dir(game_path, self.dir, scale)
        self.save_path = os.path.join(work_dir, "save.bin")
        self.stderr_path = os.path.join(work_dir, "game.stderr.log")
        env = dict(os.environ)
        env.update({"SIM_HEADLESS": "1", "SIM_CONTROL": "stdio", "SIM_FIXED_RTC": FIXED_RTC,
                    "SIM_SEED": FIXED_SEED, "SIM_SAVE_PATH": self.save_path})
        env.update(env_extra)
        if nice:
            argv = ["nice", "-n", str(nice)] + argv
        self._stderr = open(self.stderr_path, "wb")
        self.proc = subprocess.Popen(argv, cwd=self.dir, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=self._stderr, env=env, text=True, bufsize=1)
        self.frame = 0

    # -- low level
    def stderr_tail(self, n=1500):
        try:
            with open(self.stderr_path, "rb") as f:
                f.seek(0, 2)
                f.seek(max(0, f.tell() - n))
                return f.read().decode("utf-8", "replace")
        except OSError:
            return ""

    def send(self, obj):
        if self.proc.poll() is not None:
            raise GameDied(self.side, "exited with %s before %s\n%s" % (self.proc.returncode, json.dumps(obj), self.stderr_tail()))
        try:
            self.proc.stdin.write(json.dumps(obj) + "\n")
            self.proc.stdin.flush()
        except (BrokenPipeError, OSError):
            raise GameDied(self.side, "pipe closed sending %s\n%s" % (json.dumps(obj), self.stderr_tail()))

    def recv(self, obj, timeout):
        ready, _, _ = select.select([self.proc.stdout], [], [], timeout)
        if not ready:
            raise GameDied(self.side, "no reply to %s within %ds\n%s" % (json.dumps(obj), timeout, self.stderr_tail()))
        line = self.proc.stdout.readline()
        if not line:
            self.proc.poll()
            raise GameDied(self.side, "stdout closed after %s (rc=%s)\n%s" % (json.dumps(obj), self.proc.poll(), self.stderr_tail()))
        reply = json.loads(line)
        if isinstance(reply, dict) and "frame" in reply:
            self.frame = reply["frame"]
        return reply

    def close(self):
        try:
            if self.proc.poll() is None:
                try:
                    self.send({"cmd": "quit"})
                    self.proc.wait(timeout=5)
                except Exception:
                    pass
            if self.proc.poll() is None:
                self.proc.kill()
                self.proc.wait()
        finally:
            self._stderr.close()


class Pair:
    """Two games driven with the same command stream. jobs=2 sends each
    command to both before reading either reply, so both render concurrently;
    jobs=1 finishes A before starting B."""

    def __init__(self, a, b, jobs=2, timeout=900):
        self.a, self.b, self.jobs, self.timeout = a, b, jobs, timeout

    def cmd(self, obj):
        if self.jobs >= 2:
            self.a.send(obj)
            self.b.send(obj)
            ra = self.a.recv(obj, self.timeout)
            rb = self.b.recv(obj, self.timeout)
        else:
            self.a.send(obj)
            ra = self.a.recv(obj, self.timeout)
            self.b.send(obj)
            rb = self.b.recv(obj, self.timeout)
        return ra, rb

    def close(self):
        for g in (self.a, self.b):
            g.close()
