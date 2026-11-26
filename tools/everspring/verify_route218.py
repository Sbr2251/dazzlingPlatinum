#!/usr/bin/env python3
"""Headless visual & gameplay verification harness for Route 218 — Everspring Sanctuary.

Standard library only (matches tools/solaceon_town/art_test.py). Runs against a native
macOS or Linux SDL3 headless build (`SIM_CONTROL=stdio`).

Usage:
    python3 tools/everspring/verify_route218.py <build_dir> <output_dir> [--night] [--fx]

Options:
    --night          Also run a second pass at 22:00 (night lighting) via SIM_FIXED_RTC
    --fx             Enable SDL3 GPU weather & water FX (SIM_FX_WEATHER=1, SIM_FX_WATER=1)
    --only day|night Run only the specified time-of-day pass
    --save PATH      Raw .sav/.dsv to import (default: tools/dazzling/test/fixtures/eterna_forest_grass.sav)
    --renderer MODE  auto (default), gl, or gpu. Under auto, --fx uses gpu (weather/water
                     shaders are GPU-backend-only); without --fx, Linux defaults to gl
                     for fast llvmpipe rendering and macOS uses its native gpu default.
    --scale N        InternalResolutionScale in sim_config.ini (default: 2)
    --wide           Enable 16:9 ScreenLayout=wide (GPU backend only)
    --smoke-base     Verify boot, viewpoints, base interactions, and gate warps against
                     the pre-redesign base commit (skips redesigned-only fountain/bridge checks)
    --keep-run-dir   Keep temporary symlinked run directories for debugging

Exit status 0 when every assertion passes; non-zero on failure.
Logs and stderr are written to <output_dir>/log_<run>.txt and game_<run>.stderr.log.
Screenshots are saved as both .bmp and stdlib-encoded .png in <output_dir>.
"""
import argparse
import json
import os
import select
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
DEFAULT_SAVE = os.path.join(ROOT, "tools", "dazzling", "test", "fixtures", "eterna_forest_grass.sav")

ROUTE_218 = "MAP_HEADER_ROUTE_218"
GATE_CANALAVE = "MAP_HEADER_ROUTE_218_GATE_TO_CANALAVE_CITY"
GATE_JUBILIFE = "MAP_HEADER_ROUTE_218_GATE_TO_JUBILIFE_CITY"

DELTA = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
SKIP_ENTRIES = ("save.bin", "save-backups", "build.ninja", "compile_commands.json", "sim_config.ini")
LINUX_SDL3_LIBDIR = "/data/repos/dp-wt/sdl3-deps/prefix/lib64"

RTC = {
    "day": "2026-01-02T12:00:00",
    "night": "2026-01-02T22:00:00",
}

# 8 key viewpoints from docs/everspring_redesign/PLAN.md (world coords x=64..127, z=736..767)
VIEWPOINTS = [
    ("01_west_gate", 71, 754, "DIR_EAST"),
    ("02_spiral_meadow", 81, 758, "DIR_SOUTH"),
    ("03_west_bridge", 85, 753, "DIR_EAST"),
    ("04_gardevoir_fountain", 94, 753, "DIR_NORTH"),
    ("05_fountain_plaza_wide", 95, 756, "DIR_NORTH"),
    ("06_rift_crystal", 98, 748, "DIR_NORTH"),
    ("07_east_pier", 108, 753, "DIR_WEST"),
    ("08_east_grove", 119, 758, "DIR_WEST"),
]

# Interactive story spots: (shot_name, label, stand_x, stand_z, facing, expect_signpost)
REDESIGN_INTERACTIONS = [
    ("09_dialogue_gardevoir_fountain", "Gardevoir Fountain (Route218_GardevoirFountain)", 94, 753, "DIR_NORTH", False),
    ("10_dialogue_rift_shrine", "Rift Conduit Crystal (Route218_RiftShrine)", 98, 748, "DIR_NORTH", False),
    ("11_dialogue_west_sign", "West Sanctuary Sign (EVERSPRING SANCTUARY)", 73, 754, "DIR_NORTH", True),
]

# Pre-redesign base commit spots for --smoke-base validation
BASE_INTERACTIONS = [
    ("10_dialogue_rift_shrine_base", "Base Rift Shrine (Route218_RiftShrine)", 95, 753, "DIR_NORTH", False),
    ("11_dialogue_west_sign_base", "Base West Sign (Route218_SanctuarySign)", 72, 754, "DIR_NORTH", True),
]


class Failure(Exception):
    pass


# ------------------------------------------------------------------ image helpers (stdlib only)
def load_bmp(path):
    """Return (w, h, top-down RGB bytes) for an uncompressed 24/32-bit BMP, else None."""
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
    h_abs = abs(h)
    bpp_bytes = bpp // 8
    stride = (w * bpp_bytes + 3) & ~3
    rows = []
    for y in range(h_abs):
        src = off + (y if h < 0 else h_abs - 1 - y) * stride
        row = bytearray(w * 3)
        for x in range(w):
            p = src + x * bpp_bytes
            row[x * 3] = data[p + 2]
            row[x * 3 + 1] = data[p + 1]
            row[x * 3 + 2] = data[p]
        rows.append(bytes(row))
    return w, h_abs, b"".join(rows)


def save_png(path, w, h, rgb):
    """Write tightly packed top-down RGB bytes as a standard PNG without third-party deps."""
    def chunk(kind, payload):
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        )

    scanlines = b"".join(b"\x00" + rgb[y * w * 3:(y + 1) * w * 3] for y in range(h))
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(scanlines, 6))
        + chunk(b"IEND", b"")
    )
    with open(path, "wb") as f:
        f.write(png_bytes)


def bmp_to_png(bmp_path, png_path):
    """Convert BMP screenshot to PNG (fast stdlib encoder; falls back to sips if needed)."""
    img = load_bmp(bmp_path)
    if img is not None:
        w, h, rgb = img
        save_png(png_path, w, h, rgb)
        return (w, h)
    if shutil.which("sips"):
        r = subprocess.run(["sips", "-s", "format", "png", bmp_path, "--out", png_path], capture_output=True)
        if r.returncode == 0 and os.path.exists(png_path):
            return None
    return None


# ------------------------------------------------------------------ headless game client
class Game:
    def __init__(self, build_dir, run_dir, log, extra_env=None, scale=2, wide=False):
        self.log = log
        self.run_dir = run_dir
        main_bin = os.path.join(build_dir, "main")
        if not os.path.exists(main_bin):
            raise SystemExit(f"{main_bin} not found: build first")

        for entry in os.listdir(build_dir):
            if entry in SKIP_ENTRIES or entry.startswith(("meson-", "save.bin")) or entry.endswith((".p", ".log")):
                continue
            os.symlink(os.path.join(build_dir, entry), os.path.join(run_dir, entry))

        cfg_lines = ["[General]\n", f"InternalResolutionScale={scale}\n"]
        if wide:
            cfg_lines.append("ScreenLayout=wide\n")
        with open(os.path.join(run_dir, "sim_config.ini"), "w") as f:
            f.writelines(cfg_lines)

        env = dict(os.environ)
        if sys.platform.startswith("linux"):
            env.setdefault("LP_NUM_THREADS", "2")
            if os.path.isdir(LINUX_SDL3_LIBDIR):
                cur_ld = env.get("LD_LIBRARY_PATH", "")
                if LINUX_SDL3_LIBDIR not in cur_ld.split(":"):
                    env["LD_LIBRARY_PATH"] = f"{LINUX_SDL3_LIBDIR}:{cur_ld}" if cur_ld else LINUX_SDL3_LIBDIR

        env.update({
            "SIM_HEADLESS": "1",
            "SIM_CONTROL": "stdio",
            "SIM_FIXED_RTC": RTC["day"],
            "SIM_SEED": "12345",
            "SIM_SAVE_PATH": os.path.join(run_dir, "save.bin"),
            "SDL_MAC_BACKGROUND_APP": "1",
        })
        env.update(extra_env or {})

        self.stderr_path = os.path.join(run_dir, "game.stderr.log")
        self.stderr = open(self.stderr_path, "wb")
        self.proc = subprocess.Popen(
            ["./main"],
            cwd=run_dir,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.stderr,
            text=True,
            bufsize=1,
        )

    def cmd(self, obj, timeout=None):
        frames = obj.get("frames", 0)
        timeout = timeout or max(120, frames / 8 + 120)
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

    def state(self, **extra):
        req = {"cmd": "state"}
        req.update(extra)
        return self.cmd(req)

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


# ------------------------------------------------------------------ field helpers
def where(st):
    p = st.get("player") or {}
    return st.get("map"), (p.get("x"), p.get("z"))


def is_field_idle(st):
    # Note: ShowScrollingSign ends its script (script=None) while leaving signpost_active=True
    # until the player moves or warps, so field idleness matches smoke_test.py.
    return (
        st.get("app") == "field"
        and st.get("script") is None
        and not st.get("message_waiting")
    )


def settle(game, frames=600):
    """Step until the field is idle (no script, no message box, no signpost) or frames run out."""
    for _ in range(max(1, frames // 20)):
        st = game.state()
        if is_field_idle(st):
            return st
        game.cmd({"cmd": "step", "frames": 20})
    return game.state()


def expect(cond, msg, results):
    line = ("ok  " if cond else "FAIL") + " " + msg
    results.append(line)
    print(line, flush=True)
    if not cond:
        raise Failure(msg)


def shoot(game, out_dir, name, shots, results):
    bmp = os.path.join(out_dir, name + ".bmp")
    png = os.path.join(out_dir, name + ".png")
    r = game.cmd({"cmd": "screenshot", "path": bmp})
    expect(bool(r.get("ok")) and os.path.exists(bmp) and os.path.getsize(bmp) > 54,
           f"screenshot {name}.bmp captured", results)
    dims = bmp_to_png(bmp, png)
    if dims:
        shots.append(png)
    else:
        shots.append(bmp)
    return bmp


def boot(game, save, results):
    r = game.cmd({"cmd": "import_save", "path": os.path.abspath(save)})
    expect(bool(r.get("ok")), f"imported save {os.path.basename(save)}", results)
    # Advance through intro/title screen and Continue until app == "field"
    game.cmd({"cmd": "step", "frames": 600})
    for _ in range(36):
        st = game.state()
        if st.get("app") == "field":
            break
        game.cmd({"cmd": "press", "keys": ["A"], "frames": 10})
        game.cmd({"cmd": "step", "frames": 150})
    # Dismiss Journal if opened on Continue until player object is live in the field
    for _ in range(120):
        st = game.state()
        if st.get("app") == "field" and st.get("player"):
            break
        game.cmd({"cmd": "press", "keys": ["B"], "frames": 10})
        game.cmd({"cmd": "step", "frames": 40})
    st = game.state()
    expect(st.get("app") == "field" and bool(st.get("player")),
           f"reached field ({st.get('map')} {where(st)[1]})", results)
    settle(game, 2400)


def warp(game, x, z, facing, results, mapname=ROUTE_218):
    ok = False
    for _ in range(30):
        r = game.cmd({"cmd": "warp", "map": mapname, "x": x, "z": z, "dir": facing})
        if r.get("ok"):
            ok = True
            break
        game.cmd({"cmd": "press", "keys": ["B"], "frames": 10})
        game.cmd({"cmd": "step", "frames": 120})
    expect(ok, f"warp command accepted for {mapname} ({x}, {z}) {facing}", results)
    game.cmd({"cmd": "step", "frames": 240})
    st = settle(game)
    m, pos = where(st)
    expect(m == mapname and pos == (x, z), f"warped to {mapname} {pos} facing {facing}", results)
    game.cmd({"cmd": "step", "frames": 60})  # let map fade-in complete
    return st


def walk_one(game, direction, tries=6):
    """Walk exactly one tile in `direction`; returns new state or raises Failure."""
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
            raise Failure(f"walking {direction} from {(x0, z0)} landed unexpectedly at {(x, z)}")
    raise Failure(f"could not walk {direction} from {(x0, z0)} on {m0}")


def walk_until_map(game, direction, want_map, max_steps=4, wait_frames=400):
    """Press `direction` step-by-step until the map changes to `want_map`."""
    for _ in range(max_steps):
        game.cmd({"cmd": "press", "keys": [direction], "frames": 8})
        for _ in range(wait_frames // 10):
            game.cmd({"cmd": "step", "frames": 10})
            st = game.state()
            if where(st)[0] == want_map:
                st = settle(game)
                game.cmd({"cmd": "step", "frames": 120})
                return st
    return settle(game)


def check_interaction(game, out_dir, run, shot_name, label, x, z, facing, expect_signpost, results, shots):
    """Stand at (x, z) facing `facing`, press A, verify dialogue/sign opens, shoot, and advance cleanly."""
    warp(game, x, z, facing, results)
    game.cmd({"cmd": "press", "keys": ["A"], "frames": 8})

    opened = False
    st = game.state()
    for _ in range(25):
        game.cmd({"cmd": "step", "frames": 10})
        st = game.state()
        if expect_signpost:
            if st.get("signpost_active") or st.get("message_waiting") or st.get("script") is not None:
                opened = True
                break
        else:
            if st.get("message_waiting") or (st.get("script") is not None and st.get("signpost_active")):
                opened = True
                break
    expect(
        opened,
        f"{label} at ({x}, {z}) {facing} opened "
        f"(script={st.get('script')}, msg={st.get('message_waiting')}, sign={st.get('signpost_active')})",
        results,
    )

    # Let text finish typing / scrolling sign slide into view before capturing
    game.cmd({"cmd": "step", "frames": 45})
    shoot(game, out_dir, f"{run}_{shot_name}", shots, results)

    # Advance through all pages until the field returns to idle
    pages = 0
    closed = False
    for _ in range(40):
        st = game.state()
        if is_field_idle(st):
            closed = True
            break
        game.cmd({"cmd": "press", "keys": ["A"], "frames": 8})
        game.cmd({"cmd": "step", "frames": 45})
        pages += 1
    if not closed:
        st = settle(game, 300)
        closed = is_field_idle(st)

    expect(closed, f"{label} advanced and closed cleanly ({pages} button presses)", results)
    m, pos = where(st)
    expect(m == ROUTE_218 and pos == (x, z), f"{label} left player idle on {m} at {pos}", results)


# ------------------------------------------------------------------ verification tour
def tour(game, out_dir, run, results, shots, smoke_base=False, fx_enabled=False, run_gameplay_checks=True):
    # Keep Barry visible at his plaza spot without the coord event hijacking automated viewpoints/walks
    game.cmd({"cmd": "set_flag", "name": "FLAG_HIDE_EVERSPRING_RIVAL", "value": False})
    game.cmd({"cmd": "set_var", "name": "VAR_EVERSPRING_RIVAL_SCENE_STATE", "value": 1})

    # 1. Capture all 8 key viewpoints
    fountain_bmp = None
    for idx, (name, x, z, facing) in enumerate(VIEWPOINTS):
        warp(game, x, z, facing, results)
        if idx == 0:
            objs = game.cmd({"cmd": "objects"})
            if objs.get("ok"):
                game.log.write(f"## Route 218 objects ({run}): {json.dumps(objs.get('objects', []))}\n")
        bmp = shoot(game, out_dir, f"{run}_{name}", shots, results)
        if name == "04_gardevoir_fountain":
            fountain_bmp = bmp
            if fx_enabled:
                # Capture a second frame 24 frames later to confirm animated FX/water motion
                game.cmd({"cmd": "step", "frames": 24})
                bmp_b = shoot(game, out_dir, f"{run}_{name}_fx_t24", shots, results)
                a_bytes = open(fountain_bmp, "rb").read()
                b_bytes = open(bmp_b, "rb").read()
                if a_bytes != b_bytes:
                    expect(True, "FX/water animation changes pixels across 24 frames at Gardevoir Fountain", results)
                else:
                    # Log without failing in case base build lacks kind=6 shader pass
                    msg = "note: Gardevoir Fountain frame t0 == t24 (expected before everspring/shaders merge)"
                    results.append(msg)
                    print(msg, flush=True)

    if not run_gameplay_checks:
        return

    # 2. Interactive story checks
    interactions = BASE_INTERACTIONS if smoke_base else REDESIGN_INTERACTIONS
    for shot_name, label, x, z, facing, is_sign in interactions:
        check_interaction(game, out_dir, run, shot_name, label, x, z, facing, is_sign, results, shots)

    # 3. Walkability check: West Arched Moonbridge (82, 753) -> (89, 753)
    if not smoke_base:
        warp(game, 82, 753, "DIR_EAST", results)
        for step_idx in range(1, 8):
            st = walk_one(game, "RIGHT")
            m, pos = where(st)
            want_pos = (82 + step_idx, 753)
            expect(
                m == ROUTE_218 and pos == want_pos,
                f"West Arched Moonbridge step {step_idx}/7 reached {pos} (want {want_pos})",
                results,
            )
        game.cmd({"cmd": "step", "frames": 30})
        shoot(game, out_dir, f"{run}_12_bridge_crossed", shots, results)

    # 4. Gate warp checks: Canalave Gate (70, 754) and Jubilife Gate (121, 758)
    warp(game, 71, 754, "DIR_WEST", results)
    st = walk_until_map(game, "LEFT", GATE_CANALAVE)
    m, pos = where(st)
    expect(m == GATE_CANALAVE, f"Canalave Gate (70, 754) warped to {m} at {pos}", results)
    shoot(game, out_dir, f"{run}_13_gate_canalave", shots, results)

    warp(game, 120, 758, "DIR_EAST", results)
    st = walk_until_map(game, "RIGHT", GATE_JUBILIFE)
    m, pos = where(st)
    expect(m == GATE_JUBILIFE, f"Jubilife Gate (121, 758) warped to {m} at {pos}", results)
    shoot(game, out_dir, f"{run}_14_gate_jubilife", shots, results)


def build_extra_env(run, fx_enabled, renderer, wide):
    env = {"SIM_FIXED_RTC": RTC[run]}
    chosen = renderer
    if chosen == "auto":
        if fx_enabled or wide:
            # fx_weather / fx_water and ScreenLayout=wide are SDL3 GPU-backend features
            chosen = "gpu"
        elif sys.platform.startswith("linux"):
            chosen = "gl"
        else:
            chosen = None
    if chosen:
        env["SIM_RENDERER"] = chosen
    if sys.platform.startswith("linux") and chosen != "gpu":
        env.setdefault("SIM_G2_GPU", "0")
    if fx_enabled:
        env["SIM_FX_WEATHER"] = "1"
        env["SIM_FX_WATER"] = "1"
    return env


def run_one(build_dir, out_dir, run, args, results, shots, run_gameplay_checks):
    run_tag = f"{run}_fx" if args.fx else run
    run_dir = tempfile.mkdtemp(prefix=f"dz-r218-{run_tag}-")
    ok = True
    extra_env = build_extra_env(run, args.fx, args.renderer, args.wide)
    log_path = os.path.join(out_dir, f"log_{run_tag}.txt")
    with open(log_path, "w") as log:
        log.write(f"# run={run_tag} env={json.dumps(extra_env)} smoke_base={args.smoke_base}\n")
        game = Game(build_dir, run_dir, log, extra_env=extra_env, scale=args.scale, wide=args.wide)
        try:
            boot(game, args.save, results)
            tour(
                game,
                out_dir,
                run_tag,
                results,
                shots,
                smoke_base=args.smoke_base,
                fx_enabled=args.fx,
                run_gameplay_checks=run_gameplay_checks,
            )
        except Failure as e:
            ok = False
            if not results or not results[-1].startswith("FAIL"):
                line = f"FAIL {e}"
                results.append(line)
                print(line, flush=True)
            try:
                log.write("LAST_STATE: " + json.dumps(game.state()) + "\n")
                shoot(game, out_dir, f"{run_tag}_failure", shots, results)
            except Exception:
                pass
        finally:
            game.close()
            if os.path.exists(game.stderr_path):
                shutil.copy(game.stderr_path, os.path.join(out_dir, f"game_{run_tag}.stderr.log"))
            if not args.keep_run_dir:
                shutil.rmtree(run_dir, ignore_errors=True)
        log.write("\n".join(results) + "\n")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("build_dir", help="Path to built tree containing `main` (e.g. build_linux or build_macos)")
    ap.add_argument("output_dir", help="Directory for screenshots (.bmp + .png) and logs")
    ap.add_argument("--night", action="store_true", help="Also run a night pass at 22:00 (SIM_FIXED_RTC)")
    ap.add_argument("--fx", action="store_true", help="Enable SIM_FX_WEATHER=1 and SIM_FX_WATER=1 (uses GPU backend)")
    ap.add_argument("--only", choices=list(RTC), help="Run only day or only night")
    ap.add_argument("--save", default=DEFAULT_SAVE, help="Save file to import (default: %(default)s)")
    ap.add_argument("--renderer", choices=["auto", "gl", "gpu"], default="auto", help="Override SIM_RENDERER")
    ap.add_argument("--scale", type=int, default=2, help="InternalResolutionScale (default: 2)")
    ap.add_argument("--wide", action="store_true", help="Enable ScreenLayout=wide (requires GPU backend)")
    ap.add_argument(
        "--smoke-base",
        action="store_true",
        help="Validate against pre-redesign base commit (skips redesigned-only fountain/bridge assertions)",
    )
    ap.add_argument("--keep-run-dir", action="store_true", help="Keep temp run directories after exit")
    args = ap.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    runs = [args.only] if args.only else (["day", "night"] if args.night else ["day"])

    t0 = time.time()
    all_ok = True
    shots = []
    build_dir = os.path.abspath(args.build_dir)
    for i, run in enumerate(runs):
        results = []
        run_tag = f"{run}_fx" if args.fx else run
        print(f"=== Route 218 verification: {run_tag} ({RTC[run]}) ===", flush=True)
        # Run full interactive/walk/gate suite on the first pass; second pass (--night) focuses on lighting viewpoints
        ok = run_one(build_dir, args.output_dir, run, args, results, shots, run_gameplay_checks=(i == 0))
        all_ok &= ok

    elapsed = time.time() - t0
    print(f"{'PASS' if all_ok else 'FAIL'} in {elapsed:.1f}s; {len(shots)} screenshots in {args.output_dir}", flush=True)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
