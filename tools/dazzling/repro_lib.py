#!/usr/bin/env python3
"""Reusable stdlib-only headless repro and assertion library for Dazzling Platinum.

Wraps the SIM_CONTROL=stdio lockstep protocol (docs/headless_protocol.md) in a
ReproSession context manager so repro scripts and regression checks share the
same boot, warp, walk, screenshot, and billboard/VRAM health-check plumbing.
"""

import json
import os
import select
import shutil
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
DEFAULT_SAVE = os.path.join(
    REPO_ROOT, "tools", "dazzling", "test", "fixtures", "eterna_forest_grass.sav"
)

TITLE_STEPS = (
    [{"step": 900}]
    + [{"press": "A", "frames": 10}, {"step": 290}] * 8
    + [{"step": 600}]
)

SKIP_ENTRIES = (
    "save.bin",
    "save-backups",
    "build.ninja",
    "compile_commands.json",
    "sim_config.ini",
    "sim_config_prj.ini",
)

DIR_TO_KEY = {
    "UP": "UP",
    "DOWN": "DOWN",
    "LEFT": "LEFT",
    "RIGHT": "RIGHT",
    "NORTH": "UP",
    "SOUTH": "DOWN",
    "WEST": "LEFT",
    "EAST": "RIGHT",
    "DIR_NORTH": "UP",
    "DIR_SOUTH": "DOWN",
    "DIR_WEST": "LEFT",
    "DIR_EAST": "RIGHT",
}

# In ov5_021EDEB4, field object billboards are positioned at object pos_fx with
# z += 6 * FX32_ONE (24576). One grid tile is 16 * FX32_ONE (65536).
FX32_ONE = 4096
PLAYER_BB_Z_OFFSET = 6 * FX32_ONE
PLAYER_BB_X_TOL = 4 * FX32_ONE       # 16384 (0.25 tile)
PLAYER_BB_Z_MIN = -4 * FX32_ONE      # -16384 (allows exact pos_fx too)
PLAYER_BB_Z_MAX = 10 * FX32_ONE      # +40960 (24576 +/- 16384; rejects 1-tile NPCs)


class ReproError(RuntimeError):
    """Protocol, process, or environment failure in a ReproSession."""


def detect_build_dir(repo_root=REPO_ROOT):
    """Auto-detect build_macos_release or build_macos under repo_root."""
    for candidate in ("build_macos_release", "build_macos"):
        path = os.path.join(repo_root, candidate)
        if os.path.exists(os.path.join(path, "main")):
            return path
    raise ReproError(
        "could not find build_macos_release/main or build_macos/main under "
        f"{repo_root}; pass build_dir explicitly or build first"
    )


def _normalize_direction(direction):
    key = DIR_TO_KEY.get(str(direction).upper())
    if not key:
        raise ValueError(f"unsupported walk direction: {direction!r}")
    return key


class ReproSession:
    """Context manager driving a headless Dazzling Platinum process over stdio."""

    def __init__(
        self,
        build_dir=None,
        save=None,
        layout="wide",
        renderer="gpu",
        cine=True,
        out_dir=None,
        extra_env=None,
        seed=12345,
        rtc="2026-01-02T12:00:00",
        resolution_scale=2,
        keep_run_dir=False,
    ):
        self.build_dir = os.path.abspath(build_dir) if build_dir else detect_build_dir()
        if not os.path.exists(os.path.join(self.build_dir, "main")):
            raise ReproError(f"game binary not found: {os.path.join(self.build_dir, 'main')}")

        if save is None:
            self.save = DEFAULT_SAVE
        elif save:
            self.save = os.path.abspath(os.path.expanduser(save))
        else:
            self.save = None

        self.layout = layout
        self.renderer = renderer
        self.cine = bool(cine)
        self.out_dir = os.path.abspath(out_dir) if out_dir else None
        self.extra_env = dict(extra_env or {})
        self.seed = str(seed)
        self.rtc = rtc
        self.resolution_scale = int(resolution_scale)
        self.keep_run_dir = bool(keep_run_dir)

        self.run_dir = None
        self.stderr_path = None
        self._stderr = None
        self.proc = None
        self._auto_out_dir = None

    def start(self):
        if self.proc is not None:
            return self
        if self.out_dir:
            os.makedirs(self.out_dir, exist_ok=True)

        self.run_dir = tempfile.mkdtemp(prefix="dz-repro-")
        for entry in os.listdir(self.build_dir):
            if (
                entry in SKIP_ENTRIES
                or entry.startswith(("meson-", "save.bin"))
                or entry.endswith((".p", ".log"))
            ):
                continue
            os.symlink(
                os.path.join(self.build_dir, entry),
                os.path.join(self.run_dir, entry),
            )

        with open(os.path.join(self.run_dir, "sim_config.ini"), "w", encoding="utf-8") as f:
            f.write("[General]\n")
            f.write(f"InternalResolutionScale={self.resolution_scale}\n")
            if self.layout:
                f.write(f"ScreenLayout={self.layout}\n")

        with open(os.path.join(self.run_dir, "sim_config_prj.ini"), "w", encoding="utf-8") as f:
            f.write("[General]\n")
            f.write(f"OverworldCinematics={'true' if self.cine else 'false'}\n")

        env = dict(os.environ)
        env.update(
            {
                "SIM_CONTROL": "stdio",
                "SIM_HEADLESS": "1",
                "SIM_MAC_BACKGROUND_APP": "1",
                "SDL_MAC_BACKGROUND_APP": "1",
                "SIM_FIXED_RTC": self.rtc,
                "SIM_SEED": self.seed,
                "SIM_SAVE_PATH": os.path.join(self.run_dir, "save.bin"),
                "SIM_FX_CINE": "1" if self.cine else "0",
            }
        )
        if self.renderer:
            env["SIM_RENDERER"] = self.renderer
        env.update(self.extra_env)

        self.stderr_path = os.path.join(self.run_dir, "game.stderr.log")
        self._stderr = open(self.stderr_path, "wb")
        self.proc = subprocess.Popen(
            ["./main"],
            cwd=self.run_dir,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self._stderr,
            text=True,
            bufsize=1,
        )
        return self

    def close(self):
        if self.proc is not None:
            try:
                if self.proc.poll() is None:
                    self.cmd({"cmd": "quit"}, timeout=10)
            except Exception:
                pass
            try:
                self.proc.wait(timeout=10)
            except Exception:
                try:
                    self.proc.kill()
                    self.proc.wait(timeout=5)
                except Exception:
                    pass
            self.proc = None

        if self._stderr is not None:
            try:
                self._stderr.close()
            except Exception:
                pass
            self._stderr = None

        if self.run_dir:
            if self.out_dir and self.stderr_path and os.path.exists(self.stderr_path):
                try:
                    shutil.copy(self.stderr_path, os.path.join(self.out_dir, "game.stderr.log"))
                except OSError:
                    pass
            if not self.keep_run_dir:
                shutil.rmtree(self.run_dir, ignore_errors=True)
            self.run_dir = None

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def stderr_tail(self, lines=25):
        if not self.stderr_path or not os.path.exists(self.stderr_path):
            return ""
        try:
            if self._stderr:
                self._stderr.flush()
            with open(self.stderr_path, "r", encoding="utf-8", errors="replace") as f:
                return "\n".join(f.read().splitlines()[-lines:])
        except OSError:
            return ""

    def cmd(self, obj, timeout=None):
        """Send one JSON protocol command and return its parsed reply."""
        if self.proc is None:
            raise ReproError("ReproSession is not started; use as a context manager or call start()")
        if self.proc.poll() is not None:
            raise ReproError(
                f"game exited with code {self.proc.returncode} before {obj}\n"
                f"{self.stderr_tail()}"
            )
        frames = obj.get("frames", 0) or 0
        if timeout is None:
            timeout = max(120, frames / 10 + 120)
        line = json.dumps(obj)
        self.proc.stdin.write(line + "\n")
        self.proc.stdin.flush()
        ready, _, _ = select.select([self.proc.stdout], [], [], timeout)
        if not ready:
            raise ReproError(
                f"no reply to {line} within {timeout:.0f}s\n{self.stderr_tail()}"
            )
        reply = self.proc.stdout.readline()
        if not reply:
            raise ReproError(
                f"game closed stdout (exit {self.proc.poll()}) after {line}\n"
                f"{self.stderr_tail()}"
            )
        return json.loads(reply)

    def step(self, frames=1):
        return self.cmd({"cmd": "step", "frames": int(frames)})

    def press(self, keys, frames=6):
        if isinstance(keys, str):
            key_list = [keys]
        else:
            key_list = list(keys)
        return self.cmd({"cmd": "press", "keys": key_list, "frames": int(frames)})

    def set_var(self, name, value):
        r = self.cmd({"cmd": "set_var", "name": str(name), "value": int(value)})
        if not r.get("ok"):
            raise ReproError(f"set_var({name!r}, {value!r}) failed: {r}")
        return r

    def set_flag(self, name, value):
        r = self.cmd({"cmd": "set_flag", "name": str(name), "value": bool(value)})
        if not r.get("ok"):
            raise ReproError(f"set_flag({name!r}, {value!r}) failed: {r}")
        return r

    def state(self, vars=None, flags=None, bag=None, memory=False, perf=False):
        req = {"cmd": "state"}
        if vars:
            req["vars"] = list(vars)
        if flags:
            req["flags"] = list(flags)
        if bag:
            req["bag"] = list(bag)
        if memory:
            req["memory"] = True
        if perf:
            req["perf"] = True
        return self.cmd(req)

    def objects(self):
        return self.cmd({"cmd": "objects"})

    def inspect(self, what):
        r = self.cmd({"cmd": "inspect", "what": str(what)})
        if not r.get("ok"):
            raise ReproError(f"inspect({what!r}) failed: {r}")
        return r

    def memory(self):
        r = self.cmd({"cmd": "memory"})
        if not r.get("ok"):
            raise ReproError(f"memory() failed: {r}")
        return r

    def settle(self, frames=600, chunk=20):
        """Step until the field is idle (no script, no message/signpost) or frames run out."""
        steps = max(1, int(frames) // int(chunk))
        for _ in range(steps):
            st = self.state()
            if (
                st.get("app") == "field"
                and st.get("script") is None
                and not st.get("message_waiting")
                and not st.get("signpost_active")
            ):
                return st
            self.step(chunk)
        return self.state()

    def boot_to_field(self):
        """Import save (if configured), advance past title/Continue/Journal, and settle on field."""
        if self.save:
            if not os.path.exists(self.save):
                raise ReproError(f"save file not found: {self.save}")
            r = self.cmd({"cmd": "import_save", "path": self.save})
            if not r.get("ok"):
                raise ReproError(f"import_save({self.save!r}) failed: {r}")

        for s in TITLE_STEPS:
            if "press" in s:
                self.press([s["press"]], frames=s.get("frames", 1))
            elif "step" in s:
                self.step(s["step"])

        # Continue opens the Journal first when the save has one; press B until
        # the player object is active on the field.
        for _ in range(120):
            st = self.state()
            if st.get("app") == "field" and st.get("player"):
                break
            self.press(["B"], frames=10)
            self.step(50)

        st = self.state()
        if st.get("app") != "field" or not st.get("player"):
            raise ReproError(f"failed to reach field after boot: {st}")
        return self.settle(frames=2400)

    def warp(self, map_name, x, z, dir="DIR_NORTH", settle_frames=240):
        """Warp to (map_name, x, z, dir), retrying briefly if a field task is finishing."""
        req = {
            "cmd": "warp",
            "map": str(map_name),
            "x": int(x),
            "z": int(z),
            "dir": str(dir),
        }
        last_reply = None
        for _ in range(30):
            last_reply = self.cmd(req)
            if last_reply.get("ok"):
                break
            self.press(["A"], frames=10)
            self.step(120)
        if not last_reply or not last_reply.get("ok"):
            raise ReproError(f"warp({map_name}, {x}, {z}, {dir}) failed: {last_reply}")
        if settle_frames > 0:
            self.step(settle_frames)
        return self.settle()

    def walk(self, direction, tiles=1, hold_frames=16, settle_frames=4):
        """Walk in `direction` for `tiles` step cycles and return the resulting state."""
        key = _normalize_direction(direction)
        for _ in range(int(tiles)):
            self.press([key], frames=hold_frames)
            if settle_frames > 0:
                self.step(settle_frames)
        return self.state()

    def screenshot(self, name, png=True):
        """Capture a BMP screenshot (and PNG via sips on macOS when png=True)."""
        if os.path.isabs(name):
            base, ext = os.path.splitext(name)
            bmp = name if ext.lower() == ".bmp" else base + ".bmp"
            os.makedirs(os.path.dirname(bmp), exist_ok=True)
        else:
            dest_dir = self.out_dir
            if not dest_dir:
                if not self._auto_out_dir:
                    self._auto_out_dir = tempfile.mkdtemp(prefix="dz-repro-shots-")
                dest_dir = self._auto_out_dir
            os.makedirs(dest_dir, exist_ok=True)
            stem = name[:-4] if name.lower().endswith((".bmp", ".png")) else name
            bmp = os.path.join(dest_dir, stem + ".bmp")

        r = self.cmd({"cmd": "screenshot", "path": bmp})
        if not r.get("ok"):
            raise ReproError(f"screenshot({bmp!r}) failed: {r}")

        if png and shutil.which("sips"):
            png_path = os.path.splitext(bmp)[0] + ".png"
            conv = subprocess.run(
                ["sips", "-s", "format", "png", bmp, "--out", png_path],
                capture_output=True,
            )
            if conv.returncode == 0 and os.path.exists(png_path):
                return png_path
        return bmp

    def assert_billboards_healthy(self, require_player=True):
        """Assert no OOB texture indices, no zero-texKey drawn billboards, and player drawn."""
        data = self.inspect("billboards").get("data") or {}
        billboards = data.get("billboards") or []
        oob_count = data.get("oob_count")
        if oob_count is None:
            oob_count = sum(1 for b in billboards if b.get("tex_oob"))
        zero_tex_count = data.get("zero_tex_count")
        if zero_tex_count is None:
            zero_tex_count = sum(
                1 for b in billboards if b.get("draw") and b.get("tex_addr") == 0
            )

        errors = []
        if oob_count != 0:
            bad = [b for b in billboards if b.get("tex_oob")]
            errors.append(f"oob_count={oob_count} (sample: {bad[:3]})")
        if zero_tex_count != 0:
            bad = [b for b in billboards if b.get("draw") and b.get("tex_addr") == 0]
            errors.append(f"zero_tex_count={zero_tex_count} (sample: {bad[:3]})")

        if require_player:
            st = self.state()
            player = st.get("player") or {}
            ppos = player.get("pos_fx")
            if not ppos or len(ppos) < 3:
                errors.append(f"player pos_fx unavailable in state: {st}")
            else:
                px, _, pz = ppos
                found = False
                for b in billboards:
                    if not b.get("draw"):
                        continue
                    bpos = b.get("pos_fx")
                    if not bpos or len(bpos) < 3:
                        continue
                    dx = abs(bpos[0] - px)
                    dz = bpos[2] - pz
                    if dx <= PLAYER_BB_X_TOL and PLAYER_BB_Z_MIN <= dz <= PLAYER_BB_Z_MAX:
                        found = True
                        break
                if not found:
                    errors.append(
                        f"no drawn billboard near player pos_fx={ppos} "
                        f"(drawn={data.get('drawn')}, count={data.get('count')}, "
                        f"truncated={data.get('truncated')})"
                    )

        if errors:
            raise AssertionError("billboard health check failed: " + "; ".join(errors))
        return data

    def assert_vram_healthy(self, min_tex_free=16384):
        """Assert sufficient free texture VRAM and zero OOM counters when reported."""
        mem = self.memory()
        vram = (mem.get("memory") or {}).get("vram") or {}
        tex_free = vram.get("tex_free")
        errors = []
        if tex_free is None or tex_free < min_tex_free:
            errors.append(f"tex_free={tex_free} < min_tex_free={min_tex_free}")
        for key in ("tex_oom", "pltt_oom", "pool_oom"):
            if key in vram and vram[key] != 0:
                errors.append(f"{key}={vram[key]} (expected 0)")
        if errors:
            raise AssertionError(
                "VRAM health check failed: " + "; ".join(errors) + f" (vram={vram})"
            )
        return vram
