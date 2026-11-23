#!/usr/bin/env python3
"""Scenario runner for the Dazzling Platinum Mac app (headless lockstep).

Scenario format: JSON (chosen over YAML: stdlib-only, no PyYAML dependency
on CI runners). See README.md in this directory for the full schema.

Usage:
  python3 tools/dazzling/test/run.py [--game build_macos/main] [-j 4]
          [--record] [--filter SUBSTR] [--scenarios DIR] [--timeout SEC]
          [--mock] [scenario.json ...]
Exit 1 if any scenario fails. On failure prints the step, the last game
state, and the last screenshot path.
"""
import argparse, concurrent.futures, json, os, re, select, shutil, struct, subprocess, sys, tempfile, time, zlib

FIXED_RTC = "2026-01-01T12:00:00"
FIXED_SEED = "12345"

# ---------------------------------------------------------------- images
def load_bmp(path):
    """Return (w, h, bytes RGB rows) for an uncompressed BMP, else None."""
    with open(path, "rb") as f:
        data = f.read()
    if data[:2] != b"BM" or len(data) < 54:
        return None
    off = struct.unpack_from("<I", data, 10)[0]
    w = struct.unpack_from("<i", data, 18)[0]
    h = struct.unpack_from("<i", data, 22)[0]
    bpp = struct.unpack_from("<H", data, 28)[0]
    if bpp not in (24, 32) or w <= 0 or h == 0:
        return None
    h_abs, step = abs(h), w * (bpp // 8)
    rows = []
    for y in range(h_abs):
        src = off + (y if h < 0 else h_abs - 1 - y) * ((step + 3) & ~3)
        row = bytearray()
        for x in range(w):
            p = src + x * (bpp // 8)
            row += data[p:p + 3][::-1]  # BGR -> RGB
        rows.append(bytes(row))
    return w, h_abs, b"".join(rows)

def load_image(path):
    img = load_bmp(path)
    if img:
        return img
    if sys.platform == "darwin" and shutil.which("sips"):
        tmp = path + ".conv.bmp"
        r = subprocess.run(["sips", "-s", "format", "bmp", path, "--out", tmp],
                           capture_output=True)
        if r.returncode == 0 and os.path.exists(tmp):
            img = load_bmp(tmp)
            os.unlink(tmp)
            return img
    raise ValueError(f"unsupported screenshot format (need BMP, or PNG on macOS): {path}")

def save_bmp(path, w, h, rgb):
    """Write RGB rows (top-down) as a 24-bit BMP (bottom-up on disk)."""
    stride = (w * 3 + 3) & ~3
    body = bytearray()
    for y in range(h - 1, -1, -1):
        for x in range(w):
            i = (y * w + x) * 3
            body += bytes((rgb[i + 2], rgb[i + 1], rgb[i]))
        body += b"\x00" * (stride - w * 3)
    with open(path, "wb") as f:
        f.write(b"BM" + struct.pack("<IHHI", 54 + len(body), 0, 0, 54))
        f.write(struct.pack("<IiiHHIIiiII", 40, w, h, 1, 24, 0, len(body), 2835, 2835, 0, 0))
        f.write(bytes(body))

def save_png(path, w, h, rgb):
    """Write tightly packed top-down RGB bytes as a small stdlib-only PNG."""
    if w <= 0 or h <= 0 or len(rgb) != w * h * 3:
        raise ValueError(f"invalid PNG image {w}x{h} with {len(rgb)} RGB bytes")

    def chunk(kind, payload):
        return (struct.pack(">I", len(payload)) + kind + payload
                + struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff))

    scanlines = b"".join(b"\x00" + rgb[y * w * 3:(y + 1) * w * 3] for y in range(h))
    data = (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(scanlines, 9)) + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(data)

def crop_image(img, crop):
    """crop=[x,y,w,h] in pixels; returns cropped (w,h,rgb)."""
    if not crop:
        return img
    w, h, rgb = img
    x, y, cw, ch = (int(v) for v in crop)
    if x < 0 or y < 0 or cw <= 0 or ch <= 0 or x + cw > w or y + ch > h:
        raise ValueError(f"crop {crop} outside image {w}x{h}")
    out = bytearray()
    for yy in range(y, y + ch):
        out += rgb[(yy * w + x) * 3:(yy * w + x + cw) * 3]
    return cw, ch, bytes(out)

def write_diff_images(actual_path, ref_path, workdir, shot_name, crop=None):
    """Write BMP artifacts and an expected|actual|diff PNG contact sheet.

    Returns ``(expected_bmp, actual_bmp, diff_bmp, contact_png, bbox,
    max_delta)``.  The inclusive bbox and max channel delta use exact pixel
    differences (not the comparison epsilon), making diagnostics unambiguous.
    """
    a, b = load_image(actual_path), load_image(ref_path)
    if crop:
        a = crop_image(a, crop)  # references are stored already cropped
        if a[:2] != b[:2]:
            b = crop_image(b, crop)  # legacy full-size reference
    os.makedirs(workdir, exist_ok=True)
    ep, ap, dp = (os.path.join(workdir, f"{shot_name}.{k}.bmp") for k in ("expected", "actual", "diff"))
    cp = os.path.join(workdir, f"{shot_name}.contact.png")
    save_bmp(ep, b[0], b[1], b[2]); save_bmp(ap, a[0], a[1], a[2])

    pw, ph = max(a[0], b[0]), max(a[1], b[1])
    dark = bytes((24, 24, 24))
    expected_panel = bytearray(dark * (pw * ph))
    actual_panel = bytearray(dark * (pw * ph))
    diff_panel = bytearray(dark * (pw * ph))
    for image, panel in ((b, expected_panel), (a, actual_panel)):
        for y in range(image[1]):
            panel[(y * pw) * 3:(y * pw + image[0]) * 3] = image[2][y * image[0] * 3:(y + 1) * image[0] * 3]

    bbox = None
    max_delta = 0
    if a[:2] == b[:2]:
        diff = bytearray()
        x0, y0, x1, y1 = a[0], a[1], -1, -1
        for i in range(0, len(a[2]), 3):
            deltas = [abs(a[2][i + c] - b[2][i + c]) for c in range(3)]
            delta = max(deltas)
            if delta:
                pixel = i // 3
                x, y = pixel % a[0], pixel // a[0]
                x0, y0, x1, y1 = min(x0, x), min(y0, y), max(x1, x), max(y1, y)
                max_delta = max(max_delta, delta)
            if delta > 8:
                diff += bytes((255, 0, 0))
            else:
                diff += bytes((a[2][i] // 3, a[2][i + 1] // 3, a[2][i + 2] // 3))
        bbox = None if x1 < 0 else (x0, y0, x1, y1)
        save_bmp(dp, a[0], a[1], bytes(diff))
        for y in range(a[1]):
            diff_panel[(y * pw) * 3:(y * pw + a[0]) * 3] = diff[y * a[0] * 3:(y + 1) * a[0] * 3]
    else:
        dp = None
        bbox = (0, 0, pw - 1, ph - 1)
        max_delta = 255
        # A red panel makes a dimension mismatch obvious at thumbnail size.
        diff_panel[:] = bytes((255, 0, 0)) * (pw * ph)

    divider = bytes((12, 12, 12)) * 2
    contact = bytearray()
    for y in range(ph):
        lo, hi = y * pw * 3, (y + 1) * pw * 3
        contact += expected_panel[lo:hi] + divider + actual_panel[lo:hi] + divider + diff_panel[lo:hi]
    save_png(cp, pw * 3 + 4, ph, bytes(contact))
    return ep, ap, dp, cp, bbox, max_delta

def compare_images(actual_path, ref_path, tolerance=0.01, channel_eps=8, crop=None):
    """Return (ok, differing_fraction, message)."""
    a, b = load_image(actual_path), load_image(ref_path)
    if crop:
        a = crop_image(a, crop)  # references are stored already cropped
        if a[:2] != b[:2]:
            b = crop_image(b, crop)  # legacy full-size reference
    if a[:2] != b[:2]:
        return False, 1.0, f"size differs: actual {a[0]}x{a[1]} vs reference {b[0]}x{b[1]}"
    # Exact goldens are overwhelmingly the common case. bytes equality is a
    # native memcmp-like operation and avoids hundreds of thousands of Python
    # loop iterations.
    if a[2] == b[2]:
        total = len(a[2]) // 3
        return True, 0.0, f"0/{total} pixels differ (0.0000%), tolerance {tolerance:.4%}"
    diff = total = 0
    for i in range(0, len(a[2]), 3):
        total += 1
        if any(abs(a[2][i + c] - b[2][i + c]) > channel_eps for c in range(3)):
            diff += 1
    frac = diff / total if total else 0.0
    return frac <= tolerance, frac, f"{diff}/{total} pixels differ ({frac:.4%}), tolerance {tolerance:.4%}"

# ---------------------------------------------------------------- state
def state_get(state, path):
    cur = state
    for part in path.split("."):
        if isinstance(cur, dict):
            if part not in cur:
                raise KeyError(path)
            cur = cur[part]
        elif isinstance(cur, list):
            cur = cur[int(part)]
        else:
            raise KeyError(path)
    return cur

OPS = {
    "eq": lambda a, b: a == b, "ne": lambda a, b: a != b,
    "gt": lambda a, b: a > b, "ge": lambda a, b: a >= b,
    "lt": lambda a, b: a < b, "le": lambda a, b: a <= b,
    "contains": lambda a, b: b in a, "in": lambda a, b: a in b,
}

def check_assertion(state, assertion):
    """Assertion: {"path": "player.map", "op": "eq", "value": ...}
    or shorthand {path: expected, ...}. Returns failure string or None."""
    if "path" in assertion:
        items = [(assertion["path"], assertion.get("op", "eq"), assertion.get("value"))]
    else:
        items = [(p, "eq", v) for p, v in assertion.items()]
    for path, op, expected in items:
        try:
            actual = state_get(state, path)
        except (KeyError, IndexError, ValueError):
            return f"state has no '{path}' (state: {json.dumps(state)[:400]})"
        if op not in OPS:
            return f"unknown assertion op '{op}'"
        if not OPS[op](actual, expected):
            return f"expected state {path} {op} {expected!r}, got {actual!r}"
    return None

def condition_met(state, condition):
    return check_assertion(state, condition) is None

# ---------------------------------------------------------------- client
class GameError(Exception):
    pass

SKIP_ENTRIES = ("save.bin", "save-backups", "build.ninja", "compile_commands.json", "sim_config.ini")

def write_sim_config(run_dir, config_extra):
    """Return sim_config.ini lines for a run dir. Without config_extra this keeps
    the historical behaviour byte for byte (a bare InternalResolutionScale=2
    line, no section header). With config_extra the overrides go under a
    [General] header, which the inih parser requires to match them; the
    runner's intended InternalResolutionScale=2 is then honoured too, so a
    scenario that sets config also pins the scale explicitly (pass it in
    config_extra to choose another scale). A [General] header is only ever
    added for scenarios that opt into config, so existing scenarios and
    their references are unaffected."""
    # Pure: returns the lines; the caller writes them (one open per file).
    if not config_extra:
        return ["InternalResolutionScale=2\n"]
    lines = ["[General]\n"]
    if "InternalResolutionScale" not in config_extra:
        lines.append("InternalResolutionScale=2\n")
    for k, v in config_extra.items():
        lines.append(f"{k}={v}\n")
    return lines

def make_run_dir(game_path, work_root, name, config_extra=None):
    """Per-scenario run dir: symlinks to the build dir's contents (the game
    reads its files relative to cwd), plus our OWN sim_config.ini (a copy,
    never a symlink) with InternalResolutionScale=2 so several parallel
    games don't crawl at the default 10x. Returns (dir, argv)."""
    run_dir = tempfile.mkdtemp(prefix=f"dz-{name}-", dir=work_root)
    if game_path.endswith(".py"):
        return run_dir, [sys.executable, os.path.abspath(game_path)]
    game_dir = os.path.dirname(os.path.abspath(game_path))
    for entry in os.listdir(game_dir):
        if entry in SKIP_ENTRIES or entry.startswith(("meson-", "save.bin")) or entry.endswith((".p", ".log")):
            continue
        src = os.path.join(game_dir, entry)
        os.symlink(src, os.path.join(run_dir, entry))
    if config_extra:
        # Overrides replace same-named keys from a build-dir config, if any.
        # A build-dir sim_config.ini is a stale artifact of a direct game
        # run, not a test input: never inherit its Renderer (it would pin
        # the backend for every scenario). A scenario that wants one sets
        # it in config_extra, which write_sim_config writes below.
        src_cfg = os.path.join(game_dir, "sim_config.ini")
        if os.path.exists(src_cfg):
            kept = [l for l in open(src_cfg)
                    if not l.startswith("Renderer=")
                    and not any(l.startswith(f"{k}=") for k in config_extra)]
            with open(os.path.join(run_dir, "sim_config.ini"), "w") as f:
                f.writelines(kept)
                f.writelines(write_sim_config(run_dir, config_extra))
        else:
            with open(os.path.join(run_dir, "sim_config.ini"), "w") as f:
                f.writelines(write_sim_config(run_dir, config_extra))
    else:
        config_lines = ["InternalResolutionScale=2\n"]
        src_cfg = os.path.join(game_dir, "sim_config.ini")
        if os.path.exists(src_cfg):
            config_lines = [l for l in open(src_cfg)
                            if not l.startswith("InternalResolutionScale=")
                            and not l.startswith("Renderer=")]
            config_lines.append("InternalResolutionScale=2\n")
        with open(os.path.join(run_dir, "sim_config.ini"), "w") as f:
            f.writelines(config_lines)
    return run_dir, ["./main"]

class GameClient:
    _live = set()  # Popen objects not yet closed (self-test / leak guard)

    @classmethod
    def live_count(cls):
        return len([p for p in cls._live if p.poll() is None])

    def __init__(self, game_path, work_root, name, record_env_extra=None, env_extra=None, config_extra=None):
        self.name = name
        self.dir, argv = make_run_dir(game_path, work_root, name, config_extra=config_extra)
        self.save_path = os.path.join(self.dir, "save.bin")
        self.coverage_path = os.path.join(self.dir, "coverage.txt")
        self.stderr_path = os.path.join(self.dir, "game.stderr.log")
        env = dict(os.environ)
        # llvmpipe spawns a thread per core per game; cap it (team rule,
        # shared devserver load). Does not affect pixels (lockstep).
        env.setdefault("LP_NUM_THREADS", "2")
        # On Linux the GPU 2D path runs on llvmpipe (software GL), where it is
        # several times slower than CPU 2D and long scenarios time out. The two
        # paths are byte-identical (see --compare-renderers), and the Mac (the
        # target) keeps the GPU default; so default to CPU 2D on Linux only.
        if sys.platform.startswith("linux"):
            env.setdefault("SIM_G2_GPU", "0")
            # The game defaults to the GPU renderer now (Metal on the Mac),
            # but on Linux it runs on lavapipe (software Vulkan), where the
            # suite is several times slower and long scenarios time out.
            # Keep the suite's default run on gl on Linux (the reference);
            # --compare-backends sets SIM_RENDERER explicitly per run and
            # wins over this pin, and a SIM_RENDERER already in the
            # environment wins over both. On the Mac the suite runs the
            # game's default (gpu).
            env.setdefault("SIM_RENDERER", "gl")
        env.update({
            # Never register in the owner's Dock/app switcher (team rule).
            "SDL_MAC_BACKGROUND_APP": "1",
            "SIM_HEADLESS": "1", "SIM_CONTROL": "stdio",
            "SIM_FIXED_RTC": FIXED_RTC, "SIM_SEED": FIXED_SEED,
            "SIM_SAVE_PATH": self.save_path,
            "SIM_SCRIPT_COVERAGE": self.coverage_path,
        })
        if record_env_extra:
            env.update(record_env_extra)
        if env_extra:
            env.update(env_extra)
        self._stderr = open(self.stderr_path, "wb")
        self.proc = subprocess.Popen(argv, cwd=self.dir,
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=self._stderr, env=env, text=True, bufsize=1)
        GameClient._live.add(self.proc)
        self.last_state = None
        self.last_screenshot = None
        self._reply_count = 0

    def _boot_banner_count(self):
        try:
            self._stderr.flush()
            with open(self.stderr_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read().count("SIM headless=1")
        except OSError:
            return 0

    def _boot_loop_detected(self, count_at_command):
        """Three resets without a protocol reply means boot never stabilised.

        Successful import_save operations intentionally restart once, and a
        scenario may import more than once, so banners accumulated over the
        whole scenario must not be mistaken for a loop.
        """
        count = self._boot_banner_count()
        return count >= 3 if self._reply_count == 0 else count - count_at_command >= 3

    def stderr_tail(self, lines=20):
        try:
            self._stderr.flush()
            with open(self.stderr_path, "r", encoding="utf-8", errors="replace") as f:
                return "\n".join(f.read().splitlines()[-lines:])
        except OSError as e:
            return f"<unable to read stderr: {e}>"

    def cmd(self, obj, timeout=120):
        if self.proc.poll() is not None:
            raise GameError(f"game exited with {self.proc.returncode}; stderr: {self.stderr_path}")
        # A long step/press legitimately takes wall-clock time proportional
        # to its frames (a 3000-frame battle step can exceed the 120s reply
        # timeout under -j4 llvmpipe load, which used to fail core_trainer
        # and core_wild_catch identically on gl and gpu). Scale the reply
        # timeout with frames, capped; a truly hung game is still caught by
        # the game-side watchdog, which closes stdout.
        if obj.get("cmd") in ("step", "press", "touch", "finger") and obj.get("frames"):
            timeout = max(timeout, min(1200, obj["frames"] / 10 + 120))
        count_at_command = self._boot_banner_count()
        self.proc.stdin.write(json.dumps(obj) + "\n")
        self.proc.stdin.flush()
        deadline = time.monotonic() + timeout
        ready = []
        while not ready:
            if self.proc.poll() is not None:
                raise GameError(f"game exited with {self.proc.returncode} waiting for {obj}; stderr: {self.stderr_path}")
            if self._boot_loop_detected(count_at_command):
                raise GameError(f"boot soft-reset loop detected (3+ 'SIM headless=1' banners); stderr: {self.stderr_path}")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise GameError(f"timeout ({timeout}s) waiting for reply to {obj}; stderr: {self.stderr_path}")
            ready, _, _ = select.select([self.proc.stdout], [], [], min(0.5, remaining))
        if self.proc.poll() is not None and not ready:
            raise GameError(f"game exited with {self.proc.returncode} waiting for {obj}; stderr: {self.stderr_path}")
        line = self.proc.stdout.readline()
        if not line:
            raise GameError(f"game closed stdout on {obj}; stderr: {self.stderr_path}")
        reply = json.loads(line)
        self._reply_count += 1
        if isinstance(reply, dict) and reply.get("ok") is False and not obj.pop("_expect_error", False):
            raise GameError(f"command {obj} failed: {reply.get('error')}")
        if isinstance(reply, dict) and "state" in reply:
            self.last_state = reply["state"]
        elif obj.get("cmd") == "state" and isinstance(reply, dict):
            self.last_state = reply
        return reply

    def state(self, extra=None):
        req = {"cmd": "state"}
        if extra:
            req.update(extra)
        reply = self.cmd(req)
        st = reply.get("state", reply) if isinstance(reply, dict) else {}
        if isinstance(st, dict):
            st = dict(st)
            if "app" not in st and "application" in st:
                st["app"] = st["application"]
            # Step-3 state: map is top level, player has x/z/dir, battle is
            # {"waiting":..., "battlers":[...]}. Normalize to the scenario
            # paths (player.map, in_battle) documented in README.md.
            player = dict(st.get("player") or {})
            for key in ("map", "map_header", "map_name"):
                if key in st:
                    player.setdefault("map", st[key])
            for key in ("x", "z", "dir"):
                if key in st and key not in player:
                    player[key] = st[key]
            if player:
                st["player"] = player
            if "in_battle" not in st:
                st["in_battle"] = st.get("app") == "battle" or "battle" in st
        self.last_state = st
        return st

    def close(self):
        """End the game no matter what: quit, wait briefly, terminate, kill, reap."""
        try:
            if self.proc.poll() is None:
                try:
                    self.cmd({"cmd": "quit"}, timeout=2)
                except Exception:
                    pass
            try:
                self.proc.wait(timeout=2)
            except Exception:
                pass
            if self.proc.poll() is None:
                try:
                    self.proc.terminate()
                except Exception:
                    pass
                try:
                    self.proc.wait(timeout=2)
                except Exception:
                    pass
            if self.proc.poll() is None:
                try:
                    self.proc.kill()
                except Exception:
                    pass
                try:
                    self.proc.wait(timeout=5)
                except Exception:
                    pass
        finally:
            GameClient._live.discard(self.proc)
            for pipe in (self.proc.stdin, self.proc.stdout):
                try:
                    pipe.close()
                except Exception:
                    pass
            self._stderr.close()

# ---------------------------------------------------------------- runner
class ScenarioFailure(Exception):
    def __init__(self, step_idx, step, message, state=None, screenshot=None):
        super().__init__(message)
        self.step_idx, self.step, self.message = step_idx, step, message
        self.state, self.screenshot = state, screenshot

def as_keys(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)

def platform_reference(ref_path):
    """Per-platform golden images. 3D output differs by a few pixels between GL
    drivers (Apple GL vs Mesa llvmpipe rasterization), so on macOS a reference
    under references/<dir>/ is looked up in references/<dir>_mac/ instead
    (recorded there with --record/--update on a Mac). Linux keeps the base dir."""
    d, f = os.path.split(ref_path)
    # Only subdirectories of references/ (e.g. visual/) are per platform; the
    # legacy top-level references (title, dex entry) match on both.
    if sys.platform != "darwin" or os.path.basename(d) == "references":
        return ref_path
    return os.path.join(d + "_mac", f)


def run_scenario(path, game_path, record=False, timeout=600, work_root=None, mock=False, env_extra=None, update=False, use_gpu_tolerance=False):
    with open(path, encoding="utf-8") as f:
        sc = json.load(f)
    # A scenario may declare its own timeout floor (e.g. the naming
    # scenario replays the whole catch flow, ~750s on llvmpipe).
    timeout = max(timeout, int(sc.get("timeout") or 0))
    name = sc.get("name") or os.path.splitext(os.path.basename(path))[0]
    scen_dir = os.path.dirname(os.path.abspath(path))
    if sc.get("pending_step3"):
        return name, True, f"SKIP (pending step 3: {sc['pending_step3']})", None
    if sc.get("known_issue"):
        return name, True, f"SKIP (known issue: {sc['known_issue']})", None
    for req in sc.get("requires_exists") or []:
        rp = os.path.expanduser(req)
        if not os.path.isabs(rp):
            rp = os.path.join(scen_dir, rp)
        if not os.path.exists(rp):
            return name, True, f"SKIP (missing {req}; local-only scenario)", None
    # Scenario-level env/config: "env" sets process env (e.g. SIM_HIRESTEXT,
    # SIM_2D_UPSCALE, SIM_RENDERER for a single scenario); "config" sets
    # sim_config.ini [General] keys (e.g. ScreenLayout, SwapScreens,
    # Upscale2DFilter, InternalResolutionScale). Caller env_extra wins on
    # conflict (it carries the --compare-* variant being run).
    scen_env = dict(sc.get("env") or {})
    if env_extra:
        scen_env.update(env_extra)
    client = GameClient(game_path, work_root, name, env_extra=scen_env,
                        config_extra=sc.get("config") or None)
    started = time.time()
    try:
        def resolve(p):
            p = os.path.expanduser(p)
            return p if os.path.isabs(p) else os.path.join(scen_dir, p)
        # ---- start
        start = sc.get("start") or {}
        if start.get("save"):
            client.cmd({"cmd": "import_save", "path": os.path.abspath(resolve(start["save"]))})
        if start.get("warp"):
            w = start["warp"]
            client.cmd({"cmd": "warp", "map": w["map"], "x": w.get("x", 0), "z": w.get("z", 0),
                        "dir": w.get("dir", "DIR_SOUTH")})
        for k, v in (start.get("vars") or {}).items():
            client.cmd({"cmd": "set_var", "name": k, "value": v})
        for k, v in (start.get("flags") or {}).items():
            client.cmd({"cmd": "set_flag", "name": k, "value": bool(v)})
        for item in (start.get("items") or []):
            client.cmd({"cmd": "give_item", "item": item["item"], "qty": item.get("qty", 1)})
        if start.get("start_battle"):
            sb = start["start_battle"] if isinstance(start["start_battle"], dict) else {}
            req = {"cmd": "start_battle"}
            if sb.get("spec"):
                req["spec_path"] = os.path.abspath(resolve(sb["spec"]))
            elif sb.get("spec_path"):
                req["spec_path"] = os.path.abspath(resolve(sb["spec_path"]))
            else:
                req.update({k: v for k, v in sb.items() if k not in ("spec", "spec_path")})
            client.cmd(req)
        state = client.state()
        seen_events = []  # battle_events drains on read; accumulate for event-anchored steps
        # ---- steps
        for idx, step in enumerate(sc.get("steps") or []):
            if time.time() - started > timeout:
                raise ScenarioFailure(idx, step, f"scenario timeout ({timeout}s)", client.last_state, client.last_screenshot)
            try:
                if "panel" in step:
                    req={"cmd":"panel"}
                    if isinstance(step["panel"], dict) and "open" in step["panel"]: req["open"]=bool(step["panel"]["open"])
                    client.cmd(req)
                elif "press" in step or "hold" in step:
                    keys = as_keys(step.get("press", step.get("hold")))
                    client.cmd({"cmd": "press", "keys": keys, "frames": step.get("frames", 1)})
                elif "step" in step:
                    client.cmd({"cmd": "step", "frames": step["step"]})
                elif "touch" in step:
                    x, y = step["touch"]
                    client.cmd({"cmd": "touch", "x": x, "y": y, "frames": step.get("frames", 1)})
                elif "finger" in step:  # ios-controls hook: window-normalised finger through overlay/DS routing
                    x, y = step["finger"]
                    client.cmd({"cmd": "finger", "x": x, "y": y, "frames": step.get("frames", 1)})
                elif "talk" in step:
                    req = {"cmd": "talk"}
                    req.update(step["talk"] if isinstance(step["talk"], dict) else {"localid": step["talk"]})
                    client.cmd(req)
                elif "wait_until" in step:
                    cond = step["wait_until"]
                    budget = step.get("timeout_frames", 600)
                    waited = 0
                    while True:
                        st = client.state()
                        if condition_met(st, cond):
                            break
                        if waited >= budget:
                            raise ScenarioFailure(idx, step, f"wait_until {cond} not met within {budget} frames",
                                                  st, client.last_screenshot)
                        client.cmd({"cmd": "step", "frames": 10})
                        waited += 10
                elif "press_until" in step:
                    cond = step["press_until"]
                    budget = step.get("timeout_frames", 7200)
                    waited = 0
                    while True:
                        st = client.state()
                        if condition_met(st, cond):
                            break
                        if waited >= budget:
                            raise ScenarioFailure(idx, step, f"press_until {cond} not met within {budget} frames",
                                                  st, client.last_screenshot)
                        client.cmd({"cmd": "press", "keys": as_keys(step.get("keys", "A")),
                                    "frames": step.get("press_frames", 10)})
                        client.cmd({"cmd": "step", "frames": step.get("interval_frames", 300)})
                        waited += step.get("press_frames", 10) + step.get("interval_frames", 300)
                elif "advance_dialogue" in step:
                    cfg = step["advance_dialogue"] if isinstance(step["advance_dialogue"], dict) else {}
                    until = cfg.get("until", {"script": None})
                    budget = int(cfg.get("timeout_frames", 14400))
                    poll_f = int(cfg.get("poll_frames", 10))
                    press_f = int(cfg.get("press_frames", 6))
                    settle_f = int(cfg.get("settle_frames", 8))
                    max_lines = int(cfg.get("max_lines", 250))
                    captures = cfg.get("capture_on_text") or []
                    captured_names = set()
                    transcript = []
                    waited = 0
                    presses = 0
                    # If the caller expects dialogue/cutscene lines and we are waiting for script==null,
                    # give a just-triggered coord-event/talk a short window to start the script first.
                    if (until == {"script": None} and (cfg.get("expect_min_lines", 0) > 0 or cfg.get("expect_text_contains"))):
                        start_wait = int(cfg.get("start_timeout_frames", 60))
                        sw = 0
                        while sw < start_wait:
                            st0 = client.state()
                            if st0.get("script") is not None or st0.get("message_waiting") or st0.get("signpost_active"):
                                break
                            client.cmd({"cmd": "step", "frames": 4})
                            sw += 4
                    while True:
                        st = client.state()
                        if condition_met(st, until):
                            break
                        if waited >= budget:
                            raise ScenarioFailure(
                                idx, step,
                                f"advance_dialogue did not reach {until} within {budget} frames "
                                f"(presses={presses}, transcript={transcript[-6:]})",
                                st, client.last_screenshot)
                        if st.get("message_waiting") or st.get("signpost_active"):
                            # Read decoded dialogue line from headless_inspect when available.
                            txt = ""
                            try:
                                ir = client.cmd({"cmd": "inspect", "what": "text", "_expect_error": True})
                                if isinstance(ir, dict) and ir.get("ok"):
                                    txt = ((ir.get("data") or {}).get("text") or "").strip()
                            except Exception:
                                txt = ""
                            if txt and (not transcript or transcript[-1] != txt):
                                transcript.append(txt)
                                for cap_spec in captures:
                                    cname = cap_spec.get("name", f"line_{len(transcript)}")
                                    needle = (cap_spec.get("contains") or "").lower()
                                    if cname not in captured_names and needle and needle in txt.lower():
                                        cap_delay = int(cap_spec.get("delay_frames", cfg.get("capture_delay_frames", 45)))
                                        if cap_delay > 0:
                                            client.cmd({"cmd": "step", "frames": cap_delay})
                                            waited += cap_delay
                                        bmp_tmp = os.path.join(client.dir, cname + ".bmp")
                                        png_out = os.path.join(client.dir, cname + ".png")
                                        client.cmd({"cmd": "screenshot", "path": bmp_tmp})
                                        w_i, h_i, rgb_i = load_image(bmp_tmp)
                                        save_png(png_out, w_i, h_i, rgb_i)
                                        client.last_screenshot = png_out
                                        captured_names.add(cname)
                            if len(transcript) > max_lines:
                                raise ScenarioFailure(
                                    idx, step,
                                    f"advance_dialogue exceeded max_lines={max_lines} (last={transcript[-4:]})",
                                    st, client.last_screenshot)
                            client.cmd({"cmd": "press", "keys": as_keys(cfg.get("keys", "A")), "frames": press_f})
                            client.cmd({"cmd": "step", "frames": settle_f})
                            waited += press_f + settle_f
                            presses += 1
                        else:
                            client.cmd({"cmd": "step", "frames": poll_f})
                            waited += poll_f
                    min_lines = int(cfg.get("expect_min_lines", 0))
                    if len(transcript) < min_lines:
                        raise ScenarioFailure(
                            idx, step,
                            f"advance_dialogue expected >= {min_lines} lines, got {len(transcript)} ({transcript})",
                            client.last_state, client.last_screenshot)
                    joined = "\n".join(transcript).lower()
                    for needle in (cfg.get("expect_text_contains") or []):
                        if needle.lower() not in joined:
                            raise ScenarioFailure(
                                idx, step,
                                f"advance_dialogue missing expected text {needle!r} in transcript ({len(transcript)} lines): {transcript}",
                                client.last_state, client.last_screenshot)
                elif "walk_to" in step:
                    wt = step["walk_to"] if isinstance(step["walk_to"], dict) else {}
                    tx, tz = int(wt["x"]), int(wt["z"])
                    budget = int(wt.get("timeout_frames", 600))
                    step_f = int(wt.get("step_frames", 8))
                    stop_on_script = bool(wt.get("stop_on_script", True))
                    prefer = wt.get("prefer_axis", "x")
                    waited = 0
                    stuck_tries = 0
                    alt_axis = False
                    while True:
                        st = client.state()
                        if stop_on_script and st.get("script") is not None:
                            break
                        pl = st.get("player") or {}
                        cx, cz = pl.get("x"), pl.get("z")
                        if cx is None or cz is None:
                            raise ScenarioFailure(idx, step, "walk_to requires player.x and player.z in state", st, client.last_screenshot)
                        if cx == tx and cz == tz:
                            # Let the final tile's step animation finish so coord-events fire.
                            settle = int(wt.get("settle_frames", 16))
                            if settle > 0:
                                client.cmd({"cmd": "step", "frames": settle})
                            break
                        if waited >= budget:
                            raise ScenarioFailure(idx, step, f"walk_to ({tx},{tz}) timed out at ({cx},{cz}) after {budget} frames", st, client.last_screenshot)
                        dx, dz = tx - cx, tz - cz
                        x_key = "RIGHT" if dx > 0 else ("LEFT" if dx < 0 else None)
                        z_key = "DOWN" if dz > 0 else ("UP" if dz < 0 else None)
                        if alt_axis:
                            key = (z_key if prefer == "x" else x_key) or (x_key if prefer == "x" else z_key)
                        else:
                            key = (x_key if prefer == "x" else z_key) or (z_key if prefer == "x" else x_key)
                        client.cmd({"cmd": "press", "keys": [key], "frames": step_f})
                        waited += step_f
                        st2 = client.state()
                        if stop_on_script and st2.get("script") is not None:
                            break
                        pl2 = st2.get("player") or {}
                        if pl2.get("x") == cx and pl2.get("z") == cz:
                            stuck_tries += 1
                            if x_key and z_key and not alt_axis:
                                alt_axis = True
                            elif stuck_tries >= 6:
                                raise ScenarioFailure(
                                    idx, step,
                                    f"walk_to ({tx},{tz}) stuck at ({cx},{cz}) pressing {key} (blocked by collision/object)",
                                    st2, client.last_screenshot)
                        else:
                            stuck_tries = 0
                            alt_axis = False
                elif "inspect" in step:
                    ins = step["inspect"]
                    what = ins if isinstance(ins, str) else ins["what"]
                    reply = client.cmd({"cmd": "inspect", "what": what})
                    data = reply.get("data") if isinstance(reply, dict) else {}
                    ins_assert = step.get("assert") if isinstance(ins, str) else ins.get("assert")
                    if ins_assert:
                        err = check_assertion(data, ins_assert)
                        if err:
                            raise ScenarioFailure(idx, step, f"inspect {what}: {err}", client.last_state, client.last_screenshot)
                    present = step.get("expect_present") if isinstance(ins, str) else ins.get("expect_present")
                    absent = step.get("expect_absent") if isinstance(ins, str) else ins.get("expect_absent")
                    if present or absent:
                        objs = (data or {}).get("objects") or []
                        have = set()
                        for o in objs:
                            if o.get("name"):
                                have.add(o["name"])
                            if "localid" in o:
                                have.add(o["localid"])
                        for want_id in (present or []):
                            if want_id not in have:
                                raise ScenarioFailure(idx, step, f"inspect {what}: expected {want_id!r} to be present (have={sorted(str(h) for h in have)})", client.last_state, client.last_screenshot)
                        for ban_id in (absent or []):
                            if ban_id in have:
                                raise ScenarioFailure(idx, step, f"inspect {what}: expected {ban_id!r} to be absent", client.last_state, client.last_screenshot)
                elif "screenshot" in step:
                    shot_name = step["screenshot"] if isinstance(step["screenshot"], str) else step["screenshot"].get("name", f"step{idx}")
                    shot_stage = step.get("stage") or (step["screenshot"].get("stage") if isinstance(step["screenshot"], dict) else None)
                    out = os.path.join(client.dir, shot_name + ".bmp")
                    shot_cmd = {"cmd": "screenshot", "path": out}
                    if shot_stage:
                        shot_cmd["stage"] = shot_stage
                    client.cmd(shot_cmd)
                    client.last_screenshot = out
                    ref = step.get("reference") or (step["screenshot"].get("reference") if isinstance(step["screenshot"], dict) else None)
                    if ref:
                        ref_path = platform_reference(resolve(ref))
                        if record or update:
                            os.makedirs(os.path.dirname(ref_path), exist_ok=True)
                            crop = step.get("crop") or (step["screenshot"].get("crop") if isinstance(step["screenshot"], dict) else None)
                            if crop:
                                cw, ch, rgb = crop_image(load_image(out), crop)
                                save_bmp(ref_path, cw, ch, rgb)
                            else:
                                shutil.copyfile(out, ref_path)
                        else:
                            if not os.path.exists(ref_path):
                                if step.get("optional_reference"):
                                    continue
                                raise ScenarioFailure(idx, step, f"reference screenshot missing: {ref_path} (run with --record)",
                                                      client.last_state, out)
                            crop = step.get("crop") or (step["screenshot"].get("crop") if isinstance(step["screenshot"], dict) else None)
                            tol = step.get("tolerance", 0.01)
                            if use_gpu_tolerance and "tolerance_gpu" in step:
                                tol = step["tolerance_gpu"]
                            ok, _frac, msg = compare_images(out, ref_path, tol, crop=crop)
                            if not ok:
                                ep, ap, dp, cp, bbox, max_delta = write_diff_images(
                                    out, ref_path, client.dir, shot_name, crop=crop)
                                raise ScenarioFailure(idx, step,
                                                      f"screenshot differs from {ref}: {msg}\n  expected: {ep}\n  actual:   {ap}\n  diff:     {dp}\n  contact_png: {cp}\n  diff_bbox: {bbox}\n  max_delta: {max_delta}",
                                                      client.last_state, out)
                elif "assert" in step:
                    st = client.state(step.get("state_request"))
                    err = check_assertion(st, step["assert"])
                    if err:
                        raise ScenarioFailure(idx, step, err, st, client.last_screenshot)
                elif "start_battle" in step:
                    sb = step["start_battle"] if isinstance(step["start_battle"], dict) else {}
                    req = {"cmd": "start_battle"}
                    if sb.get("spec"):
                        req["spec_path"] = os.path.abspath(resolve(sb["spec"]))
                    elif sb.get("spec_path"):
                        req["spec_path"] = os.path.abspath(resolve(sb["spec_path"]))
                    else:
                        req.update({k: v for k, v in sb.items() if k not in ("spec", "spec_path")})
                    client.cmd(req)
                elif "battle_decide" in step:
                    req = {"cmd": "battle_decide", "battler": 0, "action": "move"}
                    req.update(step["battle_decide"] if isinstance(step["battle_decide"], dict) else {})
                    client.cmd(req)
                elif "wait_battle_event" in step:
                    # Event-anchored wait: step until the engine emits a matching
                    # event (stat_stage/status/damage/mega_evolution/totem_aura...).
                    # Timing-proof: presentation-speed changes (fps60) move frames,
                    # not the rules event. A short fixed settle after it is fine.
                    want = step["wait_battle_event"]
                    budget = step.get("timeout_frames", 7200)
                    waited = 0
                    while True:
                        reply = client.cmd({"cmd": "battle_events"})
                        seen_events.extend(reply.get("events") or [])
                        if any(isinstance(ev, dict) and all(ev.get(k) == v for k, v in want.items()) for ev in seen_events):
                            break
                        if waited >= budget:
                            raise ScenarioFailure(idx, step, f"wait_battle_event {want} not seen within {budget} frames (last events: {seen_events[-8:]})",
                                                  client.last_state, client.last_screenshot)
                        client.cmd({"cmd": "step", "frames": 10})
                        waited += 10
                elif "battle_event" in step:
                    # Drain engine events and require one matching {type:..., ...}
                    reply = client.cmd({"cmd": "battle_events"})
                    seen_events.extend(reply.get("events") or [])
                    want = step["battle_event"]
                    if not any(isinstance(ev, dict) and all(ev.get(k) == v for k, v in want.items()) for ev in seen_events):
                        raise ScenarioFailure(idx, step, f"no battle event matching {want} in {seen_events[-8:]}",
                                              client.last_state, client.last_screenshot)
                elif "warp" in step:
                    w = step["warp"]
                    req = {"cmd": "warp", "map": w["map"], "x": w.get("x", 0), "z": w.get("z", 0), "dir": w.get("dir", "DIR_SOUTH")}
                    # "expect_error": true asserts the warp is refused (ok:false)
                    # and the game stays alive, instead of raising on the refusal.
                    # Used by the Distortion World regression: a warp issued
                    # while the entry script is still running must be refused,
                    # not crash the game on the CreateTask assert.
                    if w.get("expect_error"):
                        req["_expect_error"] = True
                        reply = client.cmd(req)
                        if reply.get("ok") is not False:
                            raise ScenarioFailure(idx, step, f"expected warp to be refused, got {reply}", client.last_state, client.last_screenshot)
                    else:
                        client.cmd(req)
                elif "set_var" in step:
                    client.cmd({"cmd": "set_var", "name": step["set_var"], "value": step.get("value", 0)})
                elif "set_flag" in step:
                    client.cmd({"cmd": "set_flag", "name": step["set_flag"], "value": bool(step.get("value", True))})
                elif "give_item" in step:
                    client.cmd({"cmd": "give_item", "item": step["give_item"], "qty": step.get("qty", 1)})
                elif "reload_config" in step:
                    # Mid-run config change. The headless protocol has no
                    # set-config command, so this rewrites sim_config.ini in
                    # the run dir and re-imports the scenario's start save:
                    # import_save restarts the process (fds survive execv),
                    # so the new config is read at startup. The scenario
                    # must re-establish its position afterwards (press
                    # through title/Continue, warp, ...), exactly as after
                    # start. Requires a start.save.
                    cfg = step["reload_config"]
                    if not isinstance(cfg, dict):
                        raise ScenarioFailure(idx, step, "reload_config needs a {key: value} mapping",
                                              client.last_state, client.last_screenshot)
                    with open(os.path.join(client.dir, "sim_config.ini"), "w") as f:
                        f.writelines(write_sim_config(client.dir, cfg))
                    start_save = (sc.get("start") or {}).get("save")
                    if not start_save:
                        raise ScenarioFailure(idx, step, "reload_config needs start.save to restart from",
                                              client.last_state, client.last_screenshot)
                    client.cmd({"cmd": "import_save", "path": os.path.abspath(resolve(start_save))})
                elif "import_save" in step:
                    client.cmd({"cmd": "import_save", "path": os.path.abspath(resolve(step["import_save"]))})
                else:
                    raise ScenarioFailure(idx, step, f"unknown step: {step}", client.last_state, client.last_screenshot)
            except ScenarioFailure:
                raise
            except Exception as e:
                raise ScenarioFailure(idx, step, str(e), client.last_state, client.last_screenshot)
        # ---- final assertions
        for assertion in sc.get("assertions") or []:
            st = client.state()
            err = check_assertion(st, assertion)
            if err:
                raise ScenarioFailure(len(sc.get("steps") or []), {"assert": assertion}, err, st, client.last_screenshot)
        # Assertions on step-3-only state (player.map, party, battle, ...):
        # checked when the engine provides the fields, reported pending
        # (not failed) while basic state lacks them.
        pending_notes = []
        for assertion in sc.get("pending_step3_assertions") or []:
            st = client.state()
            try:
                for path in ([assertion["path"]] if "path" in assertion else list(assertion)):
                    state_get(st, path)
            except (KeyError, IndexError, ValueError):
                pending_notes.append(f"pending-step-3: {assertion}")
                continue
            err = check_assertion(st, assertion)
            if err:
                raise ScenarioFailure(len(sc.get("steps") or []), {"assert": assertion}, err, st, client.last_screenshot)
        suffix = ("; " + "; ".join(pending_notes)) if pending_notes else ""
        return name, True, f"ok ({time.time() - started:.1f}s, workdir {client.dir}){suffix}", client
    except ScenarioFailure as e:
        tail = client.stderr_tail()
        return name, False, (f"FAIL step {e.step_idx}: {json.dumps(e.step)}\n  {e.message}\n"
                             f"  state: {json.dumps(e.state)[:600]}\n  last screenshot: {e.screenshot}\n"
                             f"  workdir: {client.dir} (stderr + coverage there)\n"
                             f"  stderr: {client.stderr_path}\n  stderr_tail:\n{tail}"), client
    except Exception as e:
        tail = client.stderr_tail()
        return name, False, (f"FAIL (runner/start): {e}\n  state: {json.dumps(client.last_state)[:600]}\n"
                             f"  last screenshot: {client.last_screenshot}\n"
                             f"  workdir: {client.dir} (stderr + coverage there)\n"
                             f"  stderr: {client.stderr_path}\n  stderr_tail:\n{tail}"), client

SMOKE_SCENARIOS = {
    "core_title_screen_animation", "core_save_and_reload",
    "visual_overworld_lake_verity_arrival", "core_trainer_battle",
    "visual_battlehud_command", "visual_menu_bag",
    "visual_capture_totem_mamoswine", "visual_touchpad_classic",
    "visual_weather_fog_field", "visual_widelayout_field_panel",
}


def classify_tags(path, sc=None):
    """Return explicit plus deterministic inferred scenario tags."""
    if sc is None:
        with open(path, encoding="utf-8") as f:
            sc = json.load(f)
    explicit = sc.get("tags") or []
    if not isinstance(explicit, list) or not all(isinstance(x, str) for x in explicit):
        raise ValueError(f"{path}: tags must be an array of strings")
    tags = {x.lower() for x in explicit}
    stem = os.path.splitext(os.path.basename(path))[0].lower()
    text = stem + " " + json.dumps(sc, sort_keys=True).lower()
    if stem in SMOKE_SCENARIOS:
        tags.add("smoke")
    if stem.startswith(("core_", "bug_")) or "title" in stem:
        tags.add("core")
    if stem.startswith("visual_") or "screenshot" in text or "reference" in text:
        tags.add("visual")
    inference = {
        "battle": ("battle", "trainer", "totem", "mega", "intimidate", "swords_dance", "thunder_wave"),
        "field": ("field", "overworld", "lake_verity", "route", "twinleaf", "jubilife", "eterna", "warp", "story_"),
        "story": ("story_", "rally", "advance_dialogue", "walk_to"),
        "menu": ("menu", "bag", "party", "pokedex", "town_map", "summary"),
        "save": ("save", "reload", "import_save"),
        "touchpad": ("touchpad", "\"finger\""),
        "wide": ("wide", "horizontal"),
        "weather": ("weather", "fog", "rain", "storm", "blizzard", "shafts", "heat"),
        "capture": ("capture", "catch", "naming"),
        "particles": ("particles", "flamethrower", "thunderbolt", "mega_burst"),
        "hirestext": ("hirestext", "sim_hirestext"),
    }
    for tag, needles in inference.items():
        if any(n in text for n in needles):
            tags.add(tag)
    return tags


def scenario_selected(path, tier, wanted_tags):
    with open(path, encoding="utf-8") as f:
        sc = json.load(f)
    tags = classify_tags(path, sc)
    stem = os.path.splitext(os.path.basename(path))[0].lower()
    if tier == "smoke" and stem not in SMOKE_SCENARIOS and "smoke" not in tags:
        return False
    if tier == "fast" and not ({"smoke", "core"} & tags):
        return False
    return not wanted_tags or bool(tags & set(wanted_tags))


def _result_details(name, ok, msg, elapsed):
    skipped = ok and msg.startswith("SKIP")
    def value(label):
        match = re.search(rf"(?m)^\s*{label}:\s*(.+)$", msg)
        return match.group(1).strip() if match else None
    bbox_text = value("diff_bbox")
    bbox = None
    if bbox_text and bbox_text != "None":
        nums = [int(x) for x in re.findall(r"-?\d+", bbox_text)]
        bbox = nums[:4] if len(nums) >= 4 else None
    step = re.search(r"FAIL step (\d+)", msg)
    tail = msg.split("stderr_tail:\n", 1)[1] if "stderr_tail:\n" in msg else ""
    workdir = value("workdir")
    if workdir:
        workdir = workdir.split(" (stderr", 1)[0]
    else:
        pass_workdir = re.search(r"\bworkdir ([^)]+)\)", msg)
        workdir = pass_workdir.group(1) if pass_workdir else None
    return {"name": name, "ok": bool(ok and not skipped), "skipped": skipped,
            "elapsed_sec": round(elapsed, 3),
            "failure_step": int(step.group(1)) if step else None,
            "error": None if ok else msg, "diff_bbox": bbox,
            "max_delta": int(value("max_delta")) if value("max_delta") else None,
            "contact_png": value("contact_png"), "workdir": workdir,
            "stderr_tail": tail}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scenarios", nargs="*")
    default_game = "build_macos/main" if sys.platform == "darwin" else "build_linux/main"
    ap.add_argument("--game", default=default_game,
                    help=f"game executable (auto-detected default: {default_game})")
    ap.add_argument("--mock", action="store_true", help="use tools/dazzling/test/fake_game.py")
    ap.add_argument("--scenarios-dir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "scenarios"))
    ap.add_argument("--filter", default="")
    ap.add_argument("--tier", choices=("smoke", "fast", "full"), default="full")
    ap.add_argument("--tag", action="append", default=[], help="select scenarios with this tag (repeatable; tags are ORed)")
    ap.add_argument("--json-report", help="write a machine-readable result report")
    ap.add_argument("-j", "--jobs", type=int, default=2, help="max live game processes (default 2 on this shared Mac)")
    ap.add_argument("--record", action="store_true", help="write reference screenshots")
    ap.add_argument("--update", action="store_true", help="accept current output as new references (same writes as --record; use after reviewing diffs)")
    ap.add_argument("--compare-renderers", action="store_true",
                    help="run each scenario twice, SIM_G2_GPU=0 (CPU 2D) and =1 (GPU 2D), both against the same references")
    ap.add_argument("--compare-backends", action="store_true",
                    help="run each scenario twice, SIM_RENDERER=gl and =gpu, both against the same references; "
                    "the gpu run uses each screenshot step's tolerance_gpu when present, else its tolerance. "
                    "Combinable with --compare-renderers")
    ap.add_argument("--interactive-fx", action="store_true",
                    help="use interactive sim_config_prj.ini FX defaults even under SIM_HEADLESS")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--work-root", default=None)
    args = ap.parse_args(argv)
    started_all = time.monotonic()
    if args.interactive_fx:
        os.environ["SIM_HEADLESS_INTERACTIVE_FX"] = "1"
    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
        os.environ.setdefault("SDL_VIDEO_DRIVER", "offscreen")
    game = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_game.py") if args.mock else args.game
    paths = args.scenarios or sorted(
        os.path.join(args.scenarios_dir, f) for f in os.listdir(args.scenarios_dir) if f.endswith(".json"))
    if args.filter:
        paths = [p for p in paths if args.filter in os.path.basename(p)]
    try:
        paths = [p for p in paths if scenario_selected(p, args.tier, [t.lower() for t in args.tag])]
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f"run.py: scenario selection failed: {e}"); return 2
    if not paths:
        print("run.py: no scenarios selected"); return 2
    work_root = args.work_root or tempfile.mkdtemp(prefix="dz-run-")
    os.makedirs(work_root, exist_ok=True)
    print(f"run.py: {len(paths)} scenario(s), tier={args.tier}, tags={args.tag or '-'}, game={game}, jobs={args.jobs}, record={args.record}, work={work_root}")

    def one(p):
        client = None
        began = time.monotonic()
        try:
            if (args.compare_renderers or args.compare_backends) and not (args.record or args.update):
                backends = (("gl", "gpu") if args.compare_backends else ("gl",))
                g2s = (("0", "1") if args.compare_renderers else (None,))
                msgs, ok_all, name, last_workdir = [], True, os.path.basename(p), None
                for backend in backends:
                    for g2 in g2s:
                        env, labels = {"SIM_RENDERER": backend}, [f"SIM_RENDERER={backend}"]
                        if g2 is not None:
                            env["SIM_G2_GPU"] = g2; labels.append(f"SIM_G2_GPU={g2}")
                        name, ok, msg, client = run_scenario(
                            p, game, timeout=args.timeout, work_root=work_root,
                            env_extra=env, use_gpu_tolerance=(backend == "gpu"))
                        msgs.append(f"{', '.join(labels)}: {'ok' if ok else msg}")
                        ok_all = ok_all and ok
                        if client is not None:
                            last_workdir = client.dir
                            client.close(); client = None
                msg = "; ".join(msgs)
                details = _result_details(name, ok_all, msg, time.monotonic() - began)
                details["workdir"] = details["workdir"] or last_workdir
                return name, ok_all, msg, details
            try:
                with open(p, encoding="utf-8") as f:
                    sc0 = json.load(f)
            except Exception:
                sc0 = {}
            scen_env0, scen_cfg0 = sc0.get("env") or {}, sc0.get("config") or {}
            if scen_env0.get("SIM_RENDERER"):
                use_gpu_tol = scen_env0["SIM_RENDERER"] == "gpu"
            elif os.environ.get("SIM_RENDERER"):
                use_gpu_tol = os.environ["SIM_RENDERER"] == "gpu"
            elif sys.platform.startswith("linux"):
                use_gpu_tol = False
            elif scen_cfg0.get("Renderer"):
                use_gpu_tol = scen_cfg0["Renderer"] == "gpu"
            else:
                use_gpu_tol = True
            name, ok, msg, client = run_scenario(
                p, game, record=args.record, timeout=args.timeout,
                work_root=work_root, update=args.update,
                use_gpu_tolerance=use_gpu_tol)
            return name, ok, msg, _result_details(name, ok, msg, time.monotonic() - began)
        except Exception as e:
            name, msg = os.path.splitext(os.path.basename(p))[0], f"FAIL (runner): {e}"
            return name, False, msg, _result_details(name, False, msg, time.monotonic() - began)
        finally:
            if client is not None:
                client.close()

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.jobs)) as ex:
        for name, ok, msg, details in (f.result() for f in concurrent.futures.as_completed([ex.submit(one, p) for p in paths])):
            print(f"[{'PASS' if ok else 'FAIL'}] {name}: {msg}" if ok else f"[FAIL] {name}\n{msg}", flush=True)
            results.append(details)
    failures = sum(not r["ok"] and not r["skipped"] for r in results)
    skipped = sum(r["skipped"] for r in results)
    report = {"passed": len(results) - failures - skipped, "failed": failures,
              "skipped": skipped, "total_sec": round(time.monotonic() - started_all, 3),
              "scenarios": sorted(results, key=lambda r: r["name"])}
    if args.json_report:
        parent = os.path.dirname(os.path.abspath(args.json_report))
        os.makedirs(parent, exist_ok=True)
        with open(args.json_report, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, sort_keys=True); f.write("\n")
    print(f"run.py: {report['passed']}/{len(paths)} passed, {skipped} skipped, {failures} failed")
    return 1 if failures else 0

if __name__ == "__main__":
    sys.exit(main())
