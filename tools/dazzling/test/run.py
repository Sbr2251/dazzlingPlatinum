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
import argparse, concurrent.futures, json, os, select, shutil, struct, subprocess, sys, tempfile, time

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
    """Write <shot>.expected/.actual/.diff.bmp into workdir; return paths.
    Diff pixels: differing pixels bright red, matching pixels darkened actual."""
    a, b = load_image(actual_path), load_image(ref_path)
    if crop:
        a = crop_image(a, crop)  # references are stored already cropped
        if a[:2] != b[:2]:
            b = crop_image(b, crop)  # legacy full-size reference
    os.makedirs(workdir, exist_ok=True)
    ep, ap, dp = (os.path.join(workdir, f"{shot_name}.{k}.bmp") for k in ("expected", "actual", "diff"))
    save_bmp(ep, b[0], b[1], b[2]); save_bmp(ap, a[0], a[1], a[2])
    if a[:2] == b[:2]:
        diff = bytearray()
        for i in range(0, len(a[2]), 3):
            if any(abs(a[2][i + c] - b[2][i + c]) > 8 for c in range(3)):
                diff += bytes((255, 0, 0))
            else:
                diff += bytes((a[2][i] // 3, a[2][i + 1] // 3, a[2][i + 2] // 3))
        save_bmp(dp, a[0], a[1], bytes(diff))
    else:
        dp = None
    return ep, ap, dp

def compare_images(actual_path, ref_path, tolerance=0.01, channel_eps=8, crop=None):
    """Return (ok, differing_fraction, message)."""
    a, b = load_image(actual_path), load_image(ref_path)
    if crop:
        a = crop_image(a, crop)  # references are stored already cropped
        if a[:2] != b[:2]:
            b = crop_image(b, crop)  # legacy full-size reference
    if a[:2] != b[:2]:
        return False, 1.0, f"size differs: actual {a[0]}x{a[1]} vs reference {b[0]}x{b[1]}"
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
        src_cfg = os.path.join(game_dir, "sim_config.ini")
        if os.path.exists(src_cfg):
            kept = [l for l in open(src_cfg)
                    if not any(l.startswith(f"{k}=") for k in config_extra)]
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
            config_lines = [l for l in open(src_cfg) if not l.startswith("InternalResolutionScale=")]
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

    def cmd(self, obj, timeout=120):
        if self.proc.poll() is not None:
            raise GameError(f"game exited with {self.proc.returncode}; stderr: {self.stderr_path}")
        self.proc.stdin.write(json.dumps(obj) + "\n")
        self.proc.stdin.flush()
        ready, _, _ = select.select([self.proc.stdout], [], [], timeout)
        if not ready:
            raise GameError(f"timeout ({timeout}s) waiting for reply to {obj}; stderr: {self.stderr_path}")
        line = self.proc.stdout.readline()
        if not line:
            raise GameError(f"game closed stdout on {obj}; stderr: {self.stderr_path}")
        reply = json.loads(line)
        if isinstance(reply, dict) and reply.get("ok") is False:
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
                if "press" in step or "hold" in step:
                    keys = as_keys(step.get("press", step.get("hold")))
                    client.cmd({"cmd": "press", "keys": keys, "frames": step.get("frames", 1)})
                elif "step" in step:
                    client.cmd({"cmd": "step", "frames": step["step"]})
                elif "touch" in step:
                    x, y = step["touch"]
                    client.cmd({"cmd": "touch", "x": x, "y": y, "frames": step.get("frames", 1)})
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
                elif "screenshot" in step:
                    shot_name = step["screenshot"] if isinstance(step["screenshot"], str) else step["screenshot"].get("name", f"step{idx}")
                    out = os.path.join(client.dir, shot_name + ".bmp")
                    client.cmd({"cmd": "screenshot", "path": out})
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
                                ep, ap, dp = write_diff_images(out, ref_path, client.dir, shot_name, crop=crop)
                                raise ScenarioFailure(idx, step,
                                                      f"screenshot differs from {ref}: {msg}\n  expected: {ep}\n  actual:   {ap}\n  diff:     {dp}",
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
                    client.cmd({"cmd": "warp", "map": w["map"], "x": w.get("x", 0), "z": w.get("z", 0), "dir": w.get("dir", "DIR_SOUTH")})
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
        return name, False, (f"FAIL step {e.step_idx}: {json.dumps(e.step)}\n  {e.message}\n"
                             f"  state: {json.dumps(e.state)[:600]}\n  last screenshot: {e.screenshot}\n"
                             f"  workdir: {client.dir} (stderr + coverage there)"), client
    except Exception as e:
        return name, False, (f"FAIL (runner/start): {e}\n  state: {json.dumps(client.last_state)[:600]}\n"
                             f"  last screenshot: {client.last_screenshot}\n"
                             f"  workdir: {client.dir} (stderr + coverage there)"), client

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scenarios", nargs="*")
    ap.add_argument("--game", default="build_macos/main")
    ap.add_argument("--mock", action="store_true", help="use tools/dazzling/test/fake_game.py")
    ap.add_argument("--scenarios-dir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "scenarios"))
    ap.add_argument("--filter", default="")
    ap.add_argument("-j", "--jobs", type=int, default=2, help="max live game processes (default 2 on this shared Mac)")
    ap.add_argument("--record", action="store_true", help="write reference screenshots")
    ap.add_argument("--update", action="store_true", help="accept current output as new references (same writes as --record; use after reviewing diffs)")
    ap.add_argument("--compare-renderers", action="store_true",
                    help="run each scenario twice, SIM_G2_GPU=0 (CPU 2D) and =1 (GPU 2D), both against the same references")
    ap.add_argument("--compare-backends", action="store_true",
                    help="run each scenario twice, SIM_RENDERER=gl and =gpu, both against the same references; "
                    "the gpu run uses each screenshot step's tolerance_gpu when present, else its tolerance. "
                    "Until the gpu backend exists the game falls back to gl, so both runs must pass. "
                    "Combinable with --compare-renderers (four runs: gl/gpu x CPU/GPU 2D)")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--work-root", default=None)
    args = ap.parse_args(argv)
    game = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_game.py") if args.mock else args.game
    paths = args.scenarios or sorted(
        os.path.join(args.scenarios_dir, f) for f in os.listdir(args.scenarios_dir) if f.endswith(".json"))
    if args.filter:
        paths = [p for p in paths if args.filter in os.path.basename(p)]
    if not paths:
        print("run.py: no scenarios selected"); return 2
    work_root = args.work_root or tempfile.mkdtemp(prefix="dz-run-")
    os.makedirs(work_root, exist_ok=True)
    print(f"run.py: {len(paths)} scenario(s), game={game}, jobs={args.jobs}, record={args.record}, work={work_root}")
    failures = 0
    def one(p):
        client = None
        try:
            if (args.compare_renderers or args.compare_backends) and not (args.record or args.update):
                # Variant list: (label, env_extra, use_gpu_tolerance).
                backends = (("gl", "gpu") if args.compare_backends else ("gl",))
                g2s = (("0", "1") if args.compare_renderers else ("0",))
                if not args.compare_renderers:
                    g2s = (None,)
                msgs, ok_all = [], True
                for backend in backends:
                    for g2 in g2s:
                        env = {}
                        label_parts = []
                        if backend is not None:
                            env["SIM_RENDERER"] = backend
                            label_parts.append(f"SIM_RENDERER={backend}")
                        if g2 is not None:
                            env["SIM_G2_GPU"] = g2
                            label_parts.append(f"SIM_G2_GPU={g2}")
                        name, ok, msg, client = run_scenario(p, game, record=False,
                                                             timeout=args.timeout, work_root=work_root, mock=args.mock,
                                                             env_extra=env,
                                                             use_gpu_tolerance=(backend == "gpu"))
                        msgs.append(f"{', '.join(label_parts) or 'default'}: {'ok' if ok else msg}")
                        ok_all = ok_all and ok
                        if client is not None:
                            client.close(); client = None
                return name, ok_all, "; ".join(msgs)
            name, ok, msg, client = run_scenario(p, game, record=args.record,
                                                 timeout=args.timeout, work_root=work_root, mock=args.mock,
                                                 update=args.update)
            return name, ok, msg
        finally:
            if client is not None:
                client.close()   # every scenario ends its game, on any outcome
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.jobs)) as ex:
        futures = [ex.submit(one, p) for p in paths]
        for fut in concurrent.futures.as_completed(futures):
            name, ok, msg = fut.result()
            print(f"[{ 'PASS' if ok else 'FAIL'}] {name}: {msg}" if ok else f"[FAIL] {name}\n{msg}", flush=True)
            failures += 0 if ok else 1
    print(f"run.py: {len(paths) - failures}/{len(paths)} passed")
    return 1 if failures else 0

if __name__ == "__main__":
    sys.exit(main())
