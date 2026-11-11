#!/usr/bin/env python3
"""CPU-vs-GPU 2D comparison suite (perf-g2gpu), headless lockstep.

Runs each scenario twice with identical deterministic inputs
(SIM_HEADLESS=1 SIM_CONTROL=stdio SIM_FIXED_RTC SIM_SEED, private
SIM_SAVE_PATH), once with SIM_G2_GPU=0 (CPU reference) and once with
SIM_G2_GPU=1, and pixel-diffs every screenshot.

Usage: g2gpu_compare_suite.py [--only NAME] [--keep] [--explore]
  --explore: run CPU only, keep all shots (for scripting new scenarios)
Exit 0 iff every compared screenshot is pixel-exact.
ASCII only.
"""
import json, os, struct, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BUILD = os.path.join(ROOT, "build_macos")
SAVES = os.path.expanduser("~/Downloads/dazzling_platinum_test_saves_v2/raw_sav")
MEGA = os.path.expanduser("~/Downloads/dazzlingPlatinum-mega-test.sav")
OUTROOT = "/tmp/perf-g2gpu/suite"

 # ---------------------------------------------------------------- client
class Game:
    def __init__(self, run_dir, gpu, save_path):
        env = dict(os.environ)
        env.update({
            "SIM_HEADLESS": "1", "SIM_CONTROL": "stdio",
            "SIM_FIXED_RTC": "2026-01-01T12:00:00", "SIM_SEED": "1",
            "SIM_SAVE_PATH": save_path, "SIM_G2_GPU": str(gpu),
            "SDL_MAC_BACKGROUND_APP": "1",
        })
        self.proc = subprocess.Popen(["./main"], cwd=run_dir, env=env,
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=open(os.path.join(run_dir, "stderr.log"), "w"),
                                     text=True, bufsize=1)
    def cmd(self, obj):
        self.proc.stdin.write(json.dumps(obj) + "\n"); self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError("game exited (rc=%s), see stderr.log" % self.proc.poll())
        r = json.loads(line)
        if not r.get("ok"):
            raise RuntimeError("cmd %s failed: %s" % (obj, r))
        return r
    def step(self, n): return self.cmd({"cmd": "step", "frames": n})
    def press(self, keys, n=10):
        if isinstance(keys, str): keys = [keys]
        return self.cmd({"cmd": "press", "keys": keys, "frames": n})
    def touch(self, x, y, n=5): return self.cmd({"cmd": "touch", "x": x, "y": y, "frames": n})
    def state(self): return self.cmd({"cmd": "state"})
    def shot(self, path): return self.cmd({"cmd": "screenshot", "path": path})
    def wait_app(self, app, timeout=3600):
        for _ in range(timeout // 10):
            if self.state().get("app") == app: return True
            self.step(10)
        return self.state().get("app") == app
    def wait_battle_waiting(self, timeout=3600):
        for _ in range(timeout // 10):
            st = self.state()
            if st.get("battle", {}).get("waiting"): return True
            self.step(10)
        return False
    def close(self):
        try: self.cmd({"cmd": "quit"})
        except Exception: pass
        self.proc.wait(timeout=15)

# ---------------------------------------------------------------- bmp diff
def load_bmp(path):
    with open(path, "rb") as f: data = f.read()
    off = struct.unpack_from("<I", data, 10)[0]
    w = struct.unpack_from("<i", data, 18)[0]
    h = struct.unpack_from("<i", data, 22)[0]
    return w, abs(h), data[off:]

def diff_count(a_path, b_path):
    wa, ha, pa = load_bmp(a_path); wb, hb, pb = load_bmp(b_path)
    if (wa, ha) != (wb, hb) or len(pa) != len(pb): return -1
    return sum(1 for i in range(0, len(pa), 4) if pa[i:i+4] != pb[i:i+4])

# ---------------------------------------------------------------- scenarios
# Each scenario: fn(g, shots) where shots(name) records a screenshot point.
def boot_to_field(g, shots, save_frames=600):
    # Synchronize on reaching the field (state-polled), so the number of
    # frames the boot/import restart happened to take cannot shift the
    # timeline (wandering NPCs make that visible). Press A through the
    # title/Continue flow until the field is live, then run fixed frames.
    for _ in range(120):
        st = g.state()
        if st.get("app") == "field":
            break
        g.press("A", 5); g.step(55)
    g.step(save_frames)
    shots("field")

def sc_title(g, shots):
    g.step(3000); shots("title")
    g.step(600); shots("title_anim")

def sc_intro_dw(g, shots):
    # New game intro (Rowan dialogue). Advance a fixed number of message
    # pages (press only while a message is waiting) so boot-phase frame
    # counts cannot shift which page is on screen.
    g.step(900)
    pages = 0
    for _ in range(200):
        if pages >= 8: break
        if g.state().get("message_waiting"):
            g.press("A", 5); pages += 1; g.step(200)
        else:
            g.step(60)
    g.step(300); shots("intro")

def sc_overworld(save):
    def fn(g, shots):
        boot_to_field(g, shots)
        g.press("UP", 30); g.step(60); shots("walk1")
        g.press("RIGHT", 30); g.step(60); shots("walk2")
    return fn

def menu_open(g):
    g.press("X", 10); g.step(300)

def sc_start_menu(g, shots):
    boot_to_field(g, shots)
    menu_open(g); shots("menu")

def sc_party_summary(g, shots):
    boot_to_field(g, shots)
    menu_open(g)
    g.press("DOWN", 10); g.step(120)                      # POKEMON
    g.press("A", 10); g.step(600); shots("party")
    g.press("A", 10); g.step(600); shots("summary1")
    g.press("RIGHT", 10); g.step(300); shots("summary2")
    g.press("RIGHT", 10); g.step(300); shots("summary3")
    g.press("RIGHT", 10); g.step(300); shots("summary4")

def sc_bag(g, shots):
    boot_to_field(g, shots)
    menu_open(g)
    g.press("DOWN", 10); g.step(60); g.press("DOWN", 10); g.step(120)   # BAG
    g.press("A", 10); g.step(600); shots("bag")
    g.press("RIGHT", 10); g.step(300); shots("bag2")

def sc_dex_card_map(g, shots):
    boot_to_field(g, shots)
    g.cmd({"cmd": "give_item", "item": "ITEM_TOWN_MAP", "qty": 1})
    menu_open(g); shots("menu")
    g.press("A", 10); g.step(900); shots("dex_list")       # POKEDEX
    g.press("A", 10); g.step(900); shots("dex_entry")
    g.press("B", 10); g.step(300); g.press("B", 10); g.step(600)
    menu_open(g)
    for _ in range(3):
        g.press("DOWN", 10); g.step(60)                    # trainer name
    g.press("A", 10); g.step(900); shots("trainer_card")
    g.press("B", 10); g.step(600)
    menu_open(g)
    g.press("DOWN", 10); g.step(60); g.press("DOWN", 10); g.step(120)   # BAG
    g.press("A", 10); g.step(600)
    for _ in range(7):
        g.press("RIGHT", 10); g.step(120)                  # Key Items pocket
    shots("bag_key_items")
    g.press("A", 10); g.step(600); shots("bag_key_use")
    g.press("A", 10); g.step(900); shots("town_map")

def sc_textbox_battle(g, shots):
    boot_to_field(g, shots)
    g.cmd({"cmd": "warp", "map": "MAP_HEADER_ROUTE_202", "x": 160, "z": 810, "dir": "DIR_EAST"})
    g.step(300)
    g.cmd({"cmd": "talk", "localid": "LOCALID_YOUNGSTER_TRISTAN"})
    g.press("A", 10); g.step(300); shots("textbox")
    for _ in range(6):
        g.press("A", 10); g.step(600)
    g.wait_app("battle", 3600); shots("battle_intro")
    g.wait_battle_waiting(3600); shots("battle_menu")
    g.press("A", 10); g.step(600); shots("battle_moves")

def sc_wild_battle(g, shots):
    boot_to_field(g, shots)
    g.cmd({"cmd": "warp", "map": "MAP_HEADER_ROUTE_201", "x": 125, "z": 850, "dir": "DIR_EAST"})
    g.step(300)
    for _ in range(40):
        if g.state().get("app") == "battle": break
        g.press("LEFT", 20); g.press("RIGHT", 20)
    shots("wild_intro")
    g.wait_battle_waiting(3600); shots("wild_menu")
    g.press("A", 10); g.step(600); shots("wild_moves")
    # Mega button screen (move menu with L available on this save if Mega-ready)
    g.press("L", 10); g.step(300); shots("wild_mega_button")

def sc_distortion(g, shots):
    boot_to_field(g, shots)
    g.press("UP", 60); g.step(300); shots("lake1")
    for _ in range(10):
        g.press("A", 10); g.step(240)
    shots("prologue")
    for _ in range(10):
        g.press("A", 10); g.step(240)
    shots("prologue2")

SCENARIOS = [
    ("title", None, sc_title),
    ("intro", None, sc_intro_dw),
    ("overworld_a103", os.path.join(SAVES, "A1-03_route201_to_sandgem.sav"), sc_overworld("a103")),
    ("overworld_a249", os.path.join(SAVES, "A2-49_solaceon_memorial_wall.sav"), sc_overworld("a249")),
    ("overworld_a299", os.path.join(SAVES, "A2-99_end_of_arc2.sav"), sc_overworld("a299")),
    ("start_menu", os.path.join(SAVES, "A2-99_end_of_arc2.sav"), sc_start_menu),
    ("party_summary", os.path.join(SAVES, "A2-99_end_of_arc2.sav"), sc_party_summary),
    ("bag", os.path.join(SAVES, "A2-99_end_of_arc2.sav"), sc_bag),
    ("dex_card_map", os.path.join(SAVES, "A2-99_end_of_arc2.sav"), sc_dex_card_map),
    ("trainer_battle", os.path.join(SAVES, "A1-03_route201_to_sandgem.sav"), sc_textbox_battle),
    ("wild_battle", os.path.join(SAVES, "A1-03_route201_to_sandgem.sav"), sc_wild_battle),
    ("mega_battle", MEGA, sc_wild_battle),
    ("distortion", os.path.join(SAVES, "A1-01_lake_verity_arrival.sav"), sc_distortion),
]

# ---------------------------------------------------------------- driver
def make_run_dir(path):
    os.makedirs(path, exist_ok=True)
    for name in os.listdir(BUILD):
        src = os.path.join(BUILD, name)
        dst = os.path.join(path, name)
        if not os.path.lexists(dst):
            os.symlink(src, dst)
    # scale=2 config copy (team rule for functional runs)
    cfg = os.path.join(path, "sim_config.ini")
    if os.path.lexists(cfg): os.remove(cfg)
    src = os.path.join(BUILD, "sim_config.ini")
    if os.path.exists(src):
        with open(src) as f: text = f.read()
        text = "\n".join(("InternalResolutionScale=2" if l.startswith("InternalResolutionScale=") else l) for l in text.splitlines())
    else:
        text = "[General]\nInternalResolutionScale=2\n"
    with open(cfg, "w") as f: f.write(text + "\n")

def run_scenario(name, save, fn, gpu, explore=False):
    out = os.path.join(OUTROOT, name, "gpu" if gpu else "cpu")
    os.makedirs(out, exist_ok=True)
    run_dir = os.path.join(out, "run")
    make_run_dir(run_dir)
    save_path = os.path.join(out, "save.bin")
    if os.path.exists(save_path): os.remove(save_path)
    g = Game(run_dir, gpu, save_path)
    taken = []
    def shots(n):
        p = os.path.join(out, n + ".bmp")
        g.shot(p); taken.append(n)
    try:
        if save:
            g.cmd({"cmd": "import_save", "path": save})
            g.step(120)
        fn(g, shots)
    finally:
        g.close()
    return taken

def main():
    args = sys.argv[1:]
    only = args[args.index("--only") + 1] if "--only" in args else None
    explore = "--explore" in args
    bad = 0; total = 0
    for name, save, fn in SCENARIOS:
        if only and name != only: continue
        if save and not os.path.exists(save):
            print("%s: SKIP (missing %s)" % (name, save)); continue
        try:
            taken_cpu = run_scenario(name, save, fn, gpu=0)
            if explore:
                print("%s: explored %s" % (name, taken_cpu)); continue
            taken_gpu = run_scenario(name, save, fn, gpu=1)
        except Exception as e:
            print("%s: ERROR %s" % (name, e)); bad += 1; continue
        for shot in taken_cpu:
            total += 1
            a = os.path.join(OUTROOT, name, "cpu", shot + ".bmp")
            b = os.path.join(OUTROOT, name, "gpu", shot + ".bmp")
            d = diff_count(a, b)
            if d != 0:
                bad += 1
                print("%s/%s: %s pixels differ" % (name, shot, d))
            else:
                print("%s/%s: exact" % (name, shot))
    print("shots=%d mismatched=%d" % (total, bad))
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
