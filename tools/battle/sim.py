#!/usr/bin/env python3
"""Battle simulator CLI: run a battle spec headless and report the result.

Usage:
  python3 tools/battle/sim.py --spec spec.json [--policy first|random|script]
      [--build-dir build_linux] [--save A1-03....sav] [--seed 42]
      [--events out.jsonl] [--record replay.json] [--fast]
  python3 tools/battle/sim.py --n 100 --random [--seed 1]   # fuzz-ish batch

A spec is the JSON documented in docs/battle_engine.md. Decisions come from
the spec's "decisions" list (script policy) or a policy:
  first  - always the first move
  random - a random move each turn (seeded by --seed)
  script - spec decisions, then first-move
  ai     - placeholder for trainer-AI-for-player: currently first-move
           (the engine has no headless hook to drive the player with AI yet)

Output: the synthesized event log (from state diffs; real engine events via
the `battle_events` command / SIM_BATTLE_EVENTS when engine-core lands),
then {"winner": ..., "turns": ..., "result": ...}.

Exit 0 when the battle completes, 1 on crash/assert/hang/timeout.
"""
import argparse, json, os, random, shutil, subprocess, sys, tempfile, time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dazzling"))
from headless_client import HeadlessGame  # noqa: E402

DEFAULT_SAVES = [
    "/data/repos/dp-wt/pret-sync-notes/saves/raw_sav/A1-03_route201_to_sandgem.sav",
    os.path.expanduser("~/Downloads/dazzling_platinum_test_saves_v2/raw_sav/A1-03_route201_to_sandgem.sav"),
    os.path.expanduser("~/Downloads/dazzlingPlatinum-mega-test.sav"),
]
POOL = [
    ("SPECIES_INFERNAPE", ["MOVE_FLARE_BLITZ", "MOVE_CLOSE_COMBAT", "MOVE_MACH_PUNCH", "MOVE_U_TURN"]),
    ("SPECIES_GARCHOMP", ["MOVE_EARTHQUAKE", "MOVE_DRAGON_CLAW", "MOVE_STONE_EDGE", "MOVE_SWORDS_DANCE"]),
    ("SPECIES_GENGAR", ["MOVE_SHADOW_BALL", "MOVE_SLUDGE_BOMB", "MOVE_FOCUS_BLAST", "MOVE_THUNDERBOLT"]),
    ("SPECIES_GYARADOS", ["MOVE_WATERFALL", "MOVE_EARTHQUAKE", "MOVE_ICE_FANG", "MOVE_DRAGON_DANCE"]),
    ("SPECIES_ALAKAZAM", ["MOVE_PSYCHIC", "MOVE_SHADOW_BALL", "MOVE_FOCUS_BLAST", "MOVE_CALM_MIND"]),
    ("SPECIES_BIDOOF", ["MOVE_TACKLE", "MOVE_GROWL"]),
    ("SPECIES_STARLY", ["MOVE_QUICK_ATTACK", "MOVE_WING_ATTACK", "MOVE_GROWL"]),
    ("SPECIES_SHINX", ["MOVE_SPARK", "MOVE_BITE", "MOVE_LEER"]),
]


def make_run_dir(build_dir, work):
    os.makedirs(work, exist_ok=True)
    for e in os.listdir(build_dir):
        if e.startswith(("save.bin", "meson-", "build.ninja", "compile_commands")) or e.endswith(".p"):
            continue
        dst = os.path.join(work, e)
        if not os.path.exists(dst):
            try:
                os.symlink(os.path.abspath(os.path.join(build_dir, e)), dst)
            except OSError:
                pass
    with open(os.path.join(work, "sim_config.ini"), "w") as f:
        f.write("[General]\nInternalResolutionScale=1\nWindowHeight=0\nWindowWidth=0\n"
                "FullScreen=false\nMasterVolume=127\nScreenLayout=vertical\nSwapScreens=false\n"
                "VsyncInterval=0\nCapFrameRate=false\nMacAddr=98e255c2da7e\n")
    return work


def press(game, keys, step=70):
    if isinstance(keys, str):
        keys = [keys]
    game.cmd({"cmd": "press", "keys": keys, "frames": 2})
    game.cmd({"cmd": "step", "frames": step})


def touch(game, x, y, step=70):
    # Battle menus are touch-first (battle_subscreen.c rects, 256x192).
    game.cmd({"cmd": "touch", "x": x, "y": y, "frames": 10})
    game.cmd({"cmd": "step", "frames": step})


class BattleRunner:
    def __init__(self, build_dir, save, seed=42, fast=False, work=None, quiet=True):
        self.work = work or tempfile.mkdtemp(prefix="battlesim-")
        make_run_dir(build_dir, self.work)
        extra = {}
        if fast:
            extra["SIM_BATTLE_FAST"] = "1"
        self.events_file = os.path.join(self.work, "battle_events.jsonl")
        extra["SIM_BATTLE_EVENTS"] = self.events_file
        self.game = HeadlessGame(self.work, save=save, seed=seed, extra_env=extra)
        self.save = save
        self.quiet = quiet
        self.events = []
        self.turns = 0
        self.last_battle = None
        self.fled = False

    def log(self, ev):
        self.events.append(ev)
        if not self.quiet:
            print(json.dumps(ev))

    def state(self):
        return self.game.cmd({"cmd": "state"})

    def to_field(self, timeout_steps=200):
        if self.save:
            self.game.cmd({"cmd": "import_save", "path": os.path.abspath(self.save)})
        for _ in range(timeout_steps):
            self.game.cmd({"cmd": "press", "keys": ["A"], "frames": 2})
            self.game.cmd({"cmd": "step", "frames": 58})
            st = self.state()
            if st.get("app") == "field":
                return st
        raise RuntimeError("never reached the field")

    def poll_events(self):
        # Real engine events when engine-core lands; probe once, then stop asking.
        if not getattr(self, "_ev_unsupported", False):
            try:
                r = self.game.cmd({"cmd": "battle_events"})
                if not r.get("ok"):
                    self._ev_unsupported = True
                for ev in r.get("events", []) if r.get("ok") else []:
                    self.log(ev if isinstance(ev, dict) else {"type": "engine", "raw": ev})
            except Exception:
                self._ev_unsupported = True
        if os.path.exists(self.events_file):
            try:
                with open(self.events_file) as f:
                    lines = f.readlines()
                if len(lines) > getattr(self, "_ev_lines", 0):
                    for ln in lines[getattr(self, "_ev_lines", 0):]:
                        try:
                            self.log(json.loads(ln))
                        except Exception:
                            pass
                    self._ev_lines = len(lines)
            except OSError:
                pass

    def diff_events(self, prev, cur):
        if not prev or not cur:
            return
        pb = {b["battler"]: b for b in prev.get("battlers", [])}
        for b in cur.get("battlers", []):
            o = pb.get(b["battler"])
            if not o:
                self.log({"type": "switch_in", "battler": b["battler"], "species": b["species"]})
                continue
            if o["species"] != b["species"]:
                self.log({"type": "switch", "battler": b["battler"], "from": o["species"], "to": b["species"]})
            if b["hp"] < o["hp"]:
                self.log({"type": "damage", "battler": b["battler"], "species": b["species"],
                          "amount": o["hp"] - b["hp"], "hp": b["hp"], "max_hp": b["max_hp"]})
            if b["hp"] == 0 and o["hp"] > 0:
                self.log({"type": "faint", "battler": b["battler"], "species": b["species"]})

    def try_decide(self, dec):
        # battle_decide adapter (engine-core decision queue): move/run only,
        # singles only; switch/item sub-menus are not hooked yet. Returns
        # True when the decision was queued. One-line switch: set
        # self.use_decide False to force press driving.
        if getattr(self, "use_decide", None) is False or getattr(self, "is_double", False):
            return False
        ty = dec.get("type", "move")
        if ty == "move":
            cmd = {"cmd": "battle_decide", "battler": 0, "action": "move",
                   "move_index": int(dec.get("index", 0)), "mega": bool(dec.get("mega"))}
            if dec.get("move"):
                cmd["move"] = dec["move"]
        elif ty in ("run", "flee"):
            cmd = {"cmd": "battle_decide", "battler": 0, "action": "run"}
            self.fled = True
        else:
            return False
        try:
            r = self.game.cmd(cmd)
        except Exception:
            self.use_decide = False
            return False
        if r.get("ok"):
            self.use_decide = True
            return True
        self.use_decide = False
        return False

    def do_decision(self, dec):
        if self.try_decide(dec):
            self.game.cmd({"cmd": "step", "frames": 30})
            return
        # Battle menus are touch-first: the D-pad cursor starts inactive and
        # the first key press only activates it (BattleSystem_MenuKeys).
        # `waiting` fires before the menu finishes opening; let it settle or
        # the activation press is swallowed and the cursor path shifts.
        self.game.cmd({"cmd": "step", "frames": 90})
        t = dec.get("type", "move")
        press(self.game, "A", 30)  # activate cursor
        if t == "move":
            idx = int(dec.get("index", 0))
            press(self.game, "A", 50)                      # FIGHT
            press(self.game, "A", 30)                      # activate move-menu cursor
            if dec.get("mega"):
                press(self.game, "L", 30)                  # Mega toggle (move menu)
            if idx % 2:
                press(self.game, "RIGHT", 30)
            if idx >= 2:
                press(self.game, "DOWN", 30)
            press(self.game, "A", 50)                      # pick the move
        elif t in ("run", "flee"):
            self.fled = True
            press(self.game, "DOWN", 30)                   # BAG row
            press(self.game, "RIGHT", 30)                  # RUN
            press(self.game, "A", 50)
        elif t == "switch":
            slot = int(dec.get("slot", 1))
            press(self.game, "DOWN", 30); press(self.game, "RIGHT", 30); press(self.game, "RIGHT", 30)
            press(self.game, "A", 50)                      # POKEMON
            press(self.game, "A", 30)
            for _ in range(max(0, slot - 1)):
                press(self.game, "DOWN", 30)
            press(self.game, "A", 50); press(self.game, "A", 50)
        elif t == "item":
            press(self.game, "DOWN", 30)                   # BAG
            press(self.game, "A", 50)
            press(self.game, "A", 50)
        else:
            press(self.game, "A", 50)

    def run_battle(self, spec, policy="first", max_steps=1200):
        self.to_field()
        self.is_double = bool(spec.get("double") or spec.get("battle_type") in ("double", "totem"))
        spec_path = os.path.join(self.work, "spec.json")
        with open(spec_path, "w") as f:
            json.dump(spec, f)
        r = self.game.cmd({"cmd": "start_battle", "spec_path": os.path.abspath(spec_path)})
        if not r.get("ok"):
            raise RuntimeError("start_battle failed: %s" % r)
        if self.is_double:
            # Doubles: pre-queue move decisions for both player battlers
            # (0 and 2); their menu tasks consume them in turn order.
            for battler in (0, 2):
                for i in range(40):
                    try:
                        self.game.cmd({"cmd": "battle_decide", "battler": battler, "action": "move", "target": 1 if battler == 0 else 3, "move_index": i % max(1, len((spec.get("player") or [{}])[min(battler // 2, len(spec.get("player") or [1]) - 1)].get("moves", [1])))})
                    except Exception:
                        break
        decisions = list(spec.get("decisions", []))
        rng = random.Random(spec.get("seed", 0) + 999)
        moves_count = max(1, len((spec.get("player") or [{}])[0].get("moves", ["MOVE_TACKLE"])))
        prev = None
        saw_battle = False
        for step_i in range(max_steps):
            self.game.cmd({"cmd": "step", "frames": 45})
            st = self.state()
            self.poll_events()
            if st.get("app") == "battle":
                saw_battle = True
                cur = st["battle"]
                self.diff_events(prev, cur)
                prev = cur
                self.last_battle = cur
                if cur.get("waiting"):
                    if self.is_double:
                        # Decisions are pre-queued; A only confirms target /
                        # forced-switch prompts and advances text.
                        press(self.game, "A", 40)
                        continue
                    if decisions:
                        dec = decisions.pop(0)
                    elif policy == "random":
                        dec = {"type": "move", "index": rng.randrange(moves_count)}
                    elif policy == "script":
                        dec = {"type": "move", "index": 0}
                    else:  # first / ai
                        dec = {"type": "move", "index": 0}
                    self.turns += 1
                    self.log({"type": "decision", "turn": self.turns, **dec})
                    self.do_decision(dec)
            elif saw_battle and st.get("app") == "field":
                break
            if saw_battle and st.get("app") == "battle" and step_i % 8 == 7:
                # Party/target/text prompts are not always `waiting`.
                # Doubles also has a SHIFT-position prompt (touch menu).
                if self.is_double:
                    touch(self.game, 128, 100, 20)
                press(self.game, "A", 20)
            elif saw_battle:
                # messages / transitions between battle and field: advance text
                press(self.game, "A", 30)
        else:
            raise RuntimeError("battle did not finish within max_steps")
        if not saw_battle:
            raise RuntimeError("battle never started")
        self.poll_events()
        # Winner from the last battle snapshot.
        battlers = (self.last_battle or {}).get("battlers", [])
        enemy = [b for b in battlers if b["battler"] >= 1]
        mine = [b for b in battlers if b["battler"] == 0]
        if self.fled and enemy and enemy[0]["hp"] > 0:
            winner = "fled"
        elif enemy and all(b["hp"] == 0 for b in enemy):
            winner = "player"
        elif mine and mine[0]["hp"] == 0:
            winner = "opponent"
        else:
            winner = "unknown"
        ends = [e for e in self.events if e.get("type") == "battle_end"]
        if ends and isinstance(ends[-1].get("turns"), int):
            self.turns = max(self.turns, ends[-1]["turns"])
        result = {"winner": winner, "turns": self.turns, "events_count": len(self.events),
                  "final_battle": self.last_battle, "party_after": (st.get("party") if 'st' in dir() else None)}
        self.log({"type": "battle_end", "winner": winner, "turns": self.turns})
        return result

    def close(self):
        try:
            self.game.close()
        except Exception:
            pass


def random_spec(rng):
    def team(n):
        out = []
        for _ in range(n):
            sp, moves = rng.choice(POOL)
            out.append({"species": sp, "level": rng.choice([5, 20, 50]),
                        "moves": moves[: rng.randint(1, len(moves))]})
        return out
    return {"battle_type": "wild", "player": team(1), "opponent": team(1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec")
    ap.add_argument("--build-dir", default="build_linux")
    ap.add_argument("--save")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--policy", default=None, choices=["first", "random", "script", "ai"])
    ap.add_argument("--events")
    ap.add_argument("--record", help="write a replay record (spec+seed+events) to this file")
    ap.add_argument("--fast", action="store_true", help="SIM_BATTLE_FAST=1 (engine-core fast mode)")
    ap.add_argument("--n", type=int, default=1)
    ap.add_argument("--random", action="store_true", help="randomized teams (with --n, a crash fuzzer)")
    ap.add_argument("--work", help="run dir to keep (default: temp, removed unless --keep)")
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()

    save = args.save
    if not save:
        for c in DEFAULT_SAVES:
            if os.path.exists(c):
                save = c
                break
    if not save:
        print("no test save found; pass --save", file=sys.stderr)
        return 2
    spec = None
    if args.spec:
        with open(args.spec) as f:
            spec = json.load(f)
    elif not args.random:
        print("--spec or --random required", file=sys.stderr)
        return 2

    work = args.work or tempfile.mkdtemp(prefix="battlesim-")
    runner = BattleRunner(args.build_dir, save, seed=args.seed, fast=args.fast, work=work)
    failures = 0
    try:
        for i in range(args.n):
            rng = random.Random(args.seed + i)
            s = random_spec(rng) if args.random else spec
            s = dict(s); s.setdefault("seed", args.seed + i)
            t0 = time.time()
            try:
                result = runner.run_battle(s, policy=args.policy or s.get("policy", "first"))
                print(json.dumps({"battle": i, "ok": True, "seconds": round(time.time() - t0, 1), **result}))
                if args.record:
                    with open(args.record, "w") as f:
                        json.dump({"spec": s, "seed": args.seed + i, "events": runner.events, "result": result}, f, indent=1)
                if args.events:
                    with open(args.events, "w") as f:
                        for ev in runner.events:
                            f.write(json.dumps(ev) + "\n")
            except Exception as e:
                failures += 1
                print(json.dumps({"battle": i, "ok": False, "error": str(e)}))
                if args.n == 1:
                    raise
            runner.events = []; runner.turns = 0; runner.last_battle = None; runner.fled = False
    finally:
        runner.close()
        if not args.keep and not args.work:
            shutil.rmtree(work, ignore_errors=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
