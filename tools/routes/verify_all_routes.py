#!/usr/bin/env python3
"""Unified headless visual verification harness for the Wave 2 route redesigns.

Standard library only (patterned on tools/everspring/verify_route218.py). Runs against a native
macOS or Linux SDL3 headless build (`SIM_CONTROL=stdio`), boots the game once per time of day,
warps to showcase spots on all five route packages and saves crisp .png screenshots:

    r215  Route 215 - Flooded Lowland              (SDL3 weather kind 8, rain mist)
    r206  Routes 206-207 - Eclipse Supply Road     (stock / clear)
    r216  Routes 216-217 - Memorial Ridge & Camp   (SDL3 weather kind 8, alpine snowdrift)
    r222  Route 222 - Violet-Lit Coast             (SDL3 weather kind 7, gentler violet rift)
    r223  Route 223 - Rift Sea Route & Summit      (SDL3 weather kind 7, violet rift sky)

Usage:
    python3 tools/routes/verify_all_routes.py <build_dir> <output_dir> [--fx] [--night]
        [--only r215,r206,r216,r222,r223] [--spots-json FILE] [--list-spots]

Options:
    --fx               Enable SDL3 GPU weather & water FX (SIM_FX_WEATHER=1, SIM_FX_WATER=1) and check
                       that the kind 7 (Route 223) and kind 8 (Route 215) passes animate: a second frame
                       24 frames after the first must differ (t0 vs t+24 delta).
    --night            Also run a second pass at 22:00 (SIM_FIXED_RTC); the default pass is 12:00.
    --only LIST        Comma-separated packages (r215, r206, r216, r222, r223; r207 / r217 are accepted
                       as aliases of r206 / r216). Default: all five.
    --spots-json FILE  Override showcase spots per package, so each route agent's exact landmark
                       coordinates plug in on integration. Either an object keyed by package:
                           {"r223": [{"name": "kingdra_rift_rock", "map": "MAP_HEADER_ROUTE_223",
                                      "x": 846, "z": 668, "dir": "DIR_NORTH", "fx_check": true}]}
                       or a list of spot objects each carrying "package". A package listed in the file
                       replaces that package's defaults; other packages keep theirs. "dir" defaults
                       to DIR_NORTH; "fx_check" marks the spot used for the t0/t+24 FX delta (default:
                       the first spot on Route 223 and on Route 215).
    --list-spots       Print the resolved spots plus static warnings (trainer sight lines, tiles
                       occupied by objects / warps / coord triggers, read from res/field/maps/*/events.json)
                       and exit without booting the game.
    --save PATH        Raw .sav/.dsv to import (default: tools/dazzling/test/fixtures/eterna_forest_grass.sav)
    --renderer MODE    auto (default), gl, or gpu. Under auto, --fx uses gpu (weather/water shaders are
                       GPU-backend-only); without --fx, Linux defaults to gl (fast llvmpipe) and macOS
                       uses its native gpu default.
    --scale N          InternalResolutionScale in sim_config.ini (default: 2)
    --wide             Enable 16:9 ScreenLayout=wide (GPU backend only)
    --keep-run-dir     Keep temporary symlinked run directories for debugging

Exit status 0 when every assertion passes; non-zero on failure.
Logs and stderr go to <output_dir>/log_<run>.txt and game_<run>.stderr.log; screenshots are written
as .png (stdlib encoder) with the source .bmp removed unless --keep-bmp is given.
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
MAPS_DIR = os.path.join(ROOT, "res", "field", "maps")

SKIP_ENTRIES = ("save.bin", "save-backups", "build.ninja", "compile_commands.json", "sim_config.ini")
LINUX_SDL3_LIBDIR = "/data/repos/dp-wt/sdl3-deps/prefix/lib64"

RTC = {
    "day": "2026-01-02T12:00:00",
    "night": "2026-01-02T22:00:00",
}

PACKAGES = ("r215", "r206", "r216", "r222", "r223")
ALIASES = {"r207": "r206", "r217": "r216", "r206-207": "r206", "r216-217": "r216"}

# Which SDL3 weather kind each map is wired to in src/fx_weather.c (for logs / reports).
FX_KIND = {
    "MAP_HEADER_ROUTE_215": (8, 0.60),
    "MAP_HEADER_ROUTE_216": (8, 0.65),
    "MAP_HEADER_ROUTE_217": (8, 0.65),
    "MAP_HEADER_ROUTE_222": (7, 0.55),
    "MAP_HEADER_ROUTE_223": (7, 0.80),
}

# Sensible default showcase spots (world tile coords) on every package. Each is a walkable tile
# outside every trainer's sight line and off object / warp / coord-trigger tiles (checked by
# --list-spots). Route agents replace them with exact landmark coordinates via --spots-json.
DEFAULT_SPOTS = {
    "r215": [
        {"name": "r215_01_flooded_boardwalk", "map": "MAP_HEADER_ROUTE_215", "x": 620, "z": 592,
         "dir": "DIR_NORTH", "fx_check": True},
        {"name": "r215_02_east_truck_ruts", "map": "MAP_HEADER_ROUTE_215", "x": 664, "z": 598, "dir": "DIR_EAST"},
    ],
    "r206": [
        {"name": "r206_01_cycling_road_barricade", "map": "MAP_HEADER_ROUTE_206", "x": 296, "z": 650,
         "dir": "DIR_NORTH"},
        {"name": "r207_01_eclipse_supply_yard", "map": "MAP_HEADER_ROUTE_207", "x": 344, "z": 722,
         "dir": "DIR_NORTH"},
    ],
    "r216": [
        {"name": "r216_01_teo_memorial_ridge", "map": "MAP_HEADER_ROUTE_216", "x": 334, "z": 398,
         "dir": "DIR_NORTH"},
        {"name": "r217_01_indra_snowy_camp", "map": "MAP_HEADER_ROUTE_217", "x": 300, "z": 330,
         "dir": "DIR_NORTH"},
    ],
    "r222": [
        {"name": "r222_01_violet_lit_coast", "map": "MAP_HEADER_ROUTE_222", "x": 790, "z": 786,
         "dir": "DIR_SOUTH"},
        {"name": "r222_02_stranded_tideline", "map": "MAP_HEADER_ROUTE_222", "x": 760, "z": 784,
         "dir": "DIR_SOUTH"},
    ],
    "r223": [
        {"name": "r223_01_rift_sea_approach", "map": "MAP_HEADER_ROUTE_223", "x": 849, "z": 730,
         "dir": "DIR_NORTH", "fx_check": True},
        {"name": "r223_02_waterfall_summit", "map": "MAP_HEADER_ROUTE_223", "x": 840, "z": 620,
         "dir": "DIR_NORTH"},
    ],
}

FX_DELTA_FRAMES = 24
# Fraction of main-screen pixels that must change between t0 and t+24 for the FX delta check.
FX_DELTA_MIN_FRACTION = 0.0005


class Failure(Exception):
    pass


# ------------------------------------------------------------------ spots
def normalize_package(name):
    key = name.strip().lower()
    key = ALIASES.get(key, key)
    if key not in PACKAGES:
        raise SystemExit(f"unknown package {name!r}; expected one of {', '.join(PACKAGES)} (aliases r207, r217)")
    return key


def normalize_spot(pkg, spot, idx):
    for field in ("map", "x", "z"):
        if field not in spot:
            raise SystemExit(f"--spots-json: spot {idx} of {pkg} lacks {field!r}")
    out = {
        "name": str(spot.get("name") or f"{pkg}_{idx + 1:02d}"),
        "map": str(spot["map"]),
        "x": int(spot["x"]),
        "z": int(spot["z"]),
        "dir": str(spot.get("dir", "DIR_NORTH")),
        "fx_check": bool(spot.get("fx_check", False)),
    }
    if not out["map"].startswith("MAP_HEADER_"):
        raise SystemExit(f"--spots-json: {out['name']}: map must be a MAP_HEADER_* constant")
    return out


def load_spots(spots_json):
    spots = {pkg: [dict(s) for s in lst] for pkg, lst in DEFAULT_SPOTS.items()}
    if spots_json:
        with open(spots_json) as f:
            data = json.load(f)
        override = {}
        if isinstance(data, dict):
            items = [(normalize_package(k), v) for k, v in data.items()]
            for pkg, lst in items:
                if not isinstance(lst, list):
                    raise SystemExit(f"--spots-json: {pkg} must map to a list of spots")
                override.setdefault(pkg, []).extend(lst)
        elif isinstance(data, list):
            for s in data:
                if "package" not in s:
                    raise SystemExit("--spots-json: list entries need a \"package\" key")
                override.setdefault(normalize_package(s["package"]), []).append(s)
        else:
            raise SystemExit("--spots-json: expected an object keyed by package or a list of spots")
        for pkg, lst in override.items():
            spots[pkg] = [normalize_spot(pkg, s, i) for i, s in enumerate(lst)]
    for pkg, lst in spots.items():
        for s in lst:
            s.setdefault("dir", "DIR_NORTH")
            s.setdefault("fx_check", False)
        # Default FX-delta spot: first Route 223 spot (kind 7) and first Route 215 spot (kind 8).
        for want in ("MAP_HEADER_ROUTE_223", "MAP_HEADER_ROUTE_215"):
            same = [s for s in lst if s["map"] == want]
            if same and not any(s["fx_check"] for s in same):
                same[0]["fx_check"] = True
    return spots


def map_dir(header):
    return os.path.join(MAPS_DIR, header[len("MAP_HEADER_"):].lower())


def static_spot_warnings(spot):
    """Warnings from events.json: trainer sight lines (any facing), occupied/trigger tiles."""
    path = os.path.join(map_dir(spot["map"]), "events.json")
    if not os.path.exists(path):
        return [f"no events.json at {os.path.relpath(path, ROOT)} (unknown map?)"]
    with open(path) as f:
        ev = json.load(f)
    x, z = spot["x"], spot["z"]
    warns = []
    for o in ev.get("object_events", []):
        if (o.get("x"), o.get("z")) == (x, z):
            warns.append(f"tile occupied by object {o.get('id')}")
        tr = o.get("trainer")
        if tr and o.get("trainer_type", "TRAINER_TYPE_NONE") != "TRAINER_TYPE_NONE":
            sight = int(tr.get("sight_range", 0)) + 1
            rx, rz = int(o.get("movement_range_x", 0)), int(o.get("movement_range_z", 0))
            tx, tz = o.get("x"), o.get("z")
            in_col = abs(tx - x) <= rx and abs(tz - z) <= sight + rz
            in_row = abs(tz - z) <= rz and abs(tx - x) <= sight + rx
            if in_col or in_row:
                warns.append(f"in sight line of trainer {o.get('id')} at ({tx}, {tz}) range {sight - 1}")
    for kind in ("warp_events", "coord_events"):
        for e in ev.get(kind, []):
            if (e.get("x"), e.get("z")) == (x, z):
                warns.append(f"tile is a {kind[:-7]} trigger ({e.get('script') or e.get('dest_header_id')})")
    return warns


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
    step = bpp // 8
    stride = (w * step + 3) & ~3
    rows = []
    for y in range(h_abs):
        src = off + (y if h < 0 else h_abs - 1 - y) * stride
        row = bytearray(w * 3)
        line = data[src:src + w * step]
        row[0::3] = line[2::step]
        row[1::3] = line[1::step]
        row[2::3] = line[0::step]
        rows.append(bytes(row))
    return w, h_abs, b"".join(rows)


def save_png(path, w, h, rgb):
    """Write tightly packed top-down RGB bytes as a standard PNG without third-party deps."""
    def chunk(kind, payload):
        return (struct.pack(">I", len(payload)) + kind + payload
                + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF))

    scanlines = b"".join(b"\x00" + rgb[y * w * 3:(y + 1) * w * 3] for y in range(h))
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n"
                + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(scanlines, 6))
                + chunk(b"IEND", b""))


def main_screen_rows(w, h):
    """Rows of the field (main) screen: the top half of a stacked capture, else the whole frame."""
    return (0, h // 2) if h > w else (0, h)


def frame_stats(img):
    """Mean RGB of the main screen and of its top quarter (horizon band) as 0..1 floats."""
    w, h, rgb = img
    y0, y1 = main_screen_rows(w, h)

    def mean(ya, yb):
        seg = rgb[ya * w * 3:yb * w * 3]
        n = max(1, len(seg) // 3)
        return tuple(round(sum(seg[c::3]) / n / 255.0, 4) for c in range(3))

    return {"main": mean(y0, y1), "top": mean(y0, y0 + max(1, (y1 - y0) // 4))}


def changed_fraction(a, b):
    """Fraction of main-screen pixels that differ between two same-size captures."""
    wa, ha, ra = a
    wb, hb, rb = b
    if (wa, ha) != (wb, hb):
        return 1.0
    y0, y1 = main_screen_rows(wa, ha)
    sa = ra[y0 * wa * 3:y1 * wa * 3]
    sb = rb[y0 * wa * 3:y1 * wa * 3]
    if sa == sb:
        return 0.0
    diff = 0
    for i in range(0, len(sa), 3):
        if sa[i:i + 3] != sb[i:i + 3]:
            diff += 1
    return diff / max(1, len(sa) // 3)


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
        cfg = ["[General]\n", f"InternalResolutionScale={scale}\n"]
        if wide:
            cfg.append("ScreenLayout=wide\n")
        with open(os.path.join(run_dir, "sim_config.ini"), "w") as f:
            f.writelines(cfg)

        env = dict(os.environ)
        if sys.platform.startswith("linux"):
            env.setdefault("LP_NUM_THREADS", "2")
            if os.path.isdir(LINUX_SDL3_LIBDIR):
                cur = env.get("LD_LIBRARY_PATH", "")
                if LINUX_SDL3_LIBDIR not in cur.split(":"):
                    env["LD_LIBRARY_PATH"] = f"{LINUX_SDL3_LIBDIR}:{cur}" if cur else LINUX_SDL3_LIBDIR
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
        self.proc = subprocess.Popen(["./main"], cwd=run_dir, env=env, stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=self.stderr, text=True, bufsize=1)

    def cmd(self, obj, timeout=None):
        frames = obj.get("frames", 0)
        timeout = timeout or max(120, frames / 8 + 120)
        line = json.dumps(obj)
        try:
            self.proc.stdin.write(line + "\n")
            self.proc.stdin.flush()
        except (BrokenPipeError, OSError):
            raise Failure(f"game exited ({self.proc.poll()}) before {line}; see game stderr log")
        ready, _, _ = select.select([self.proc.stdout], [], [], timeout)
        if not ready:
            raise Failure(f"no reply to {line} within {timeout}s")
        reply = self.proc.stdout.readline()
        if not reply:
            raise Failure(f"game exited ({self.proc.poll()}) after {line}; see game stderr log")
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


# ------------------------------------------------------------------ field helpers
def where(st):
    p = st.get("player") or {}
    return st.get("map"), (p.get("x"), p.get("z"))


def is_field_idle(st):
    return st.get("app") == "field" and st.get("script") is None and not st.get("message_waiting")


def settle(game, frames=600):
    """Step until the field is idle; advance any map-entry message boxes with A."""
    for _ in range(max(1, frames // 20)):
        st = game.state()
        if is_field_idle(st):
            return st
        if st.get("message_waiting"):
            game.cmd({"cmd": "press", "keys": ["A"], "frames": 8})
        game.cmd({"cmd": "step", "frames": 20})
    return game.state()


def expect(cond, msg, results):
    line = ("ok  " if cond else "FAIL") + " " + msg
    results.append(line)
    print(line, flush=True)
    if not cond:
        raise Failure(msg)


def note(msg, results):
    line = "note " + msg
    results.append(line)
    print(line, flush=True)


def shoot(game, out_dir, name, shots, results, keep_bmp=False):
    """Capture a screenshot; returns the decoded (w, h, rgb) image (or None) and writes <name>.png."""
    bmp = os.path.join(out_dir, name + ".bmp")
    png = os.path.join(out_dir, name + ".png")
    r = game.cmd({"cmd": "screenshot", "path": bmp})
    expect(bool(r.get("ok")) and os.path.exists(bmp) and os.path.getsize(bmp) > 54,
           f"screenshot {name} captured", results)
    img = load_bmp(bmp)
    if img is not None:
        save_png(png, *img)
        shots.append(png)
        if not keep_bmp:
            os.remove(bmp)
    else:
        shots.append(bmp)
    return img


def boot(game, save, results):
    r = game.cmd({"cmd": "import_save", "path": os.path.abspath(save)})
    expect(bool(r.get("ok")), f"imported save {os.path.basename(save)}", results)
    game.cmd({"cmd": "step", "frames": 600})
    for _ in range(36):
        if game.state().get("app") == "field":
            break
        game.cmd({"cmd": "press", "keys": ["A"], "frames": 10})
        game.cmd({"cmd": "step", "frames": 150})
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


def warp(game, spot, results):
    mapname, x, z, facing = spot["map"], spot["x"], spot["z"], spot["dir"]
    ok = False
    last = None
    for _ in range(30):
        last = game.cmd({"cmd": "warp", "map": mapname, "x": x, "z": z, "dir": facing})
        if last.get("ok"):
            ok = True
            break
        if last.get("error") == "unknown map":
            break
        game.cmd({"cmd": "press", "keys": ["B"], "frames": 10})
        game.cmd({"cmd": "step", "frames": 120})
    expect(ok, f"warp accepted for {mapname} ({x}, {z}) {facing}"
           + ("" if ok else f" (last reply {json.dumps(last)})"), results)
    game.cmd({"cmd": "step", "frames": 240})
    st = settle(game)
    m, pos = where(st)
    expect(m == mapname and pos == (x, z),
           f"warped to {m} {pos} facing {facing} (want {mapname} {(x, z)})", results)
    idle = is_field_idle(st)
    expect(idle, f"field idle at {spot['name']}" + ("" if idle else
           f" (script={st.get('script')}, app={st.get('app')}; a trainer or coord trigger may have fired"
           " - override the spot with --spots-json)"), results)
    game.cmd({"cmd": "step", "frames": 60})  # let the map fade-in complete
    return st


# ------------------------------------------------------------------ verification tour
def tour(game, out_dir, run_tag, packages, spots, fx_enabled, results, shots, report, keep_bmp):
    for pkg in packages:
        for spot in spots[pkg]:
            warp(game, spot, results)
            shot = f"{run_tag}_{spot['name']}"
            img0 = shoot(game, out_dir, shot, shots, results, keep_bmp)
            entry = {"package": pkg, "run": run_tag, "spot": spot, "shot": shot + ".png",
                     "fx_kind": FX_KIND.get(spot["map"], (0, 0.0))[0]}
            if img0 is not None:
                entry["stats"] = frame_stats(img0)
            if fx_enabled and spot.get("fx_check"):
                game.cmd({"cmd": "step", "frames": FX_DELTA_FRAMES})
                img1 = shoot(game, out_dir, f"{shot}_fx_t{FX_DELTA_FRAMES}", shots, results, keep_bmp)
                if img0 is None or img1 is None:
                    note(f"{spot['name']}: could not decode BMPs for the FX delta", results)
                else:
                    frac = changed_fraction(img0, img1)
                    entry["fx_delta_fraction"] = round(frac, 5)
                    kind = entry["fx_kind"]
                    expect(frac >= FX_DELTA_MIN_FRACTION,
                           f"FX kind={kind} animates at {spot['name']}: {frac * 100:.2f}% of main-screen "
                           f"pixels changed t0 -> t+{FX_DELTA_FRAMES}", results)
            report.append(entry)


def build_extra_env(run, fx_enabled, renderer, wide):
    env = {"SIM_FIXED_RTC": RTC[run]}
    chosen = renderer
    if chosen == "auto":
        if fx_enabled or wide:
            chosen = "gpu"  # fx_weather / fx_water and ScreenLayout=wide are SDL3 GPU-backend features
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


def run_one(build_dir, out_dir, run, args, packages, spots, results, shots, report):
    run_tag = f"{run}_fx" if args.fx else run
    run_dir = tempfile.mkdtemp(prefix=f"dz-routes-{run_tag}-")
    ok = True
    extra_env = build_extra_env(run, args.fx, args.renderer, args.wide)
    log_path = os.path.join(out_dir, f"log_{run_tag}.txt")
    with open(log_path, "w") as log:
        log.write(f"# run={run_tag} env={json.dumps(extra_env)} packages={','.join(packages)}\n")
        game = Game(build_dir, run_dir, log, extra_env=extra_env, scale=args.scale, wide=args.wide)
        try:
            boot(game, args.save, results)
            tour(game, out_dir, run_tag, packages, spots, args.fx, results, shots, report, args.keep_bmp)
        except Failure as e:
            ok = False
            if not results or not results[-1].startswith("FAIL"):
                line = f"FAIL {e}"
                results.append(line)
                print(line, flush=True)
            try:
                log.write("LAST_STATE: " + json.dumps(game.state()) + "\n")
                shoot(game, out_dir, f"{run_tag}_failure", shots, results, args.keep_bmp)
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


def list_spots(packages, spots):
    total_warn = 0
    for pkg in packages:
        print(f"[{pkg}]")
        for s in spots[pkg]:
            kind = FX_KIND.get(s["map"], (0, 0.0))
            flag = " fx_check" if s["fx_check"] else ""
            print(f"  {s['name']:34s} {s['map']:24s} ({s['x']}, {s['z']}) {s['dir']:9s} kind={kind[0]}{flag}")
            for w in static_spot_warnings(s):
                total_warn += 1
                print(f"      warning: {w}")
    print(f"{total_warn} warning(s)")
    return total_warn


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("build_dir", nargs="?", help="Built tree containing `main` (e.g. build_linux or build_macos)")
    ap.add_argument("output_dir", nargs="?", help="Directory for screenshots (.png), logs and report.json")
    ap.add_argument("--fx", action="store_true", help="Enable SIM_FX_WEATHER=1 / SIM_FX_WATER=1 (GPU backend)")
    ap.add_argument("--night", action="store_true", help="Also run a night pass at 22:00 (SIM_FIXED_RTC)")
    ap.add_argument("--only", help="Comma-separated packages: r215,r206,r216,r222,r223")
    ap.add_argument("--spots-json", help="JSON file overriding showcase spots per package")
    ap.add_argument("--list-spots", action="store_true", help="Print resolved spots + static warnings and exit")
    ap.add_argument("--save", default=DEFAULT_SAVE, help="Save file to import (default: %(default)s)")
    ap.add_argument("--renderer", choices=["auto", "gl", "gpu"], default="auto", help="Override SIM_RENDERER")
    ap.add_argument("--scale", type=int, default=2, help="InternalResolutionScale (default: 2)")
    ap.add_argument("--wide", action="store_true", help="Enable ScreenLayout=wide (requires GPU backend)")
    ap.add_argument("--keep-bmp", action="store_true", help="Keep the raw .bmp captures next to the .png files")
    ap.add_argument("--keep-run-dir", action="store_true", help="Keep temp run directories after exit")
    args = ap.parse_args()

    packages = list(PACKAGES)
    if args.only:
        packages = []
        for name in args.only.split(","):
            if name.strip():
                pkg = normalize_package(name)
                if pkg not in packages:
                    packages.append(pkg)
    spots = load_spots(args.spots_json)

    if args.list_spots:
        list_spots(packages, spots)
        return 0
    if not args.build_dir or not args.output_dir:
        ap.error("build_dir and output_dir are required (unless --list-spots)")

    os.makedirs(args.output_dir, exist_ok=True)
    for pkg in packages:
        for s in spots[pkg]:
            for w in static_spot_warnings(s):
                print(f"warning: {s['name']}: {w}", flush=True)

    runs = ["day", "night"] if args.night else ["day"]
    t0 = time.time()
    all_ok = True
    shots = []
    report = []
    build_dir = os.path.abspath(args.build_dir)
    for run in runs:
        results = []
        run_tag = f"{run}_fx" if args.fx else run
        print(f"=== Wave 2 routes verification: {run_tag} ({RTC[run]}) packages={','.join(packages)} ===",
              flush=True)
        all_ok &= run_one(build_dir, args.output_dir, run, args, packages, spots, results, shots, report)

    with open(os.path.join(args.output_dir, "report.json"), "w") as f:
        json.dump({"ok": all_ok, "fx": args.fx, "runs": runs, "packages": packages, "shots": report}, f, indent=1)
    elapsed = time.time() - t0
    print(f"{'PASS' if all_ok else 'FAIL'} in {elapsed:.1f}s; {len(shots)} screenshots in {args.output_dir}",
          flush=True)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
