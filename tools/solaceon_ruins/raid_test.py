#!/usr/bin/env python3
"""Headless play-through of the Solaceon raid in the Ruins (screenplay.md scene 3.4a parts 3-6) on the macOS app.
Standard library only.

Usage: python3 tools/solaceon_ruins/raid_test.py <build dir> <out dir> [--only NAME[,NAME]] [--keep-run-dir]
       e.g. python3 tools/solaceon_ruins/raid_test.py build_macos "/tmp/Solaceon Update/raid_mac"

<build dir> is a built tree with `main` (tools/macos/build.sh dev -> build_macos). Each scenario boots a fresh game
(SIM_CONTROL=stdio, docs/headless_protocol.md) from a test-only save: the repo's Arc 2 save
tools/dazzling/test/fixtures/eterna_forest_grass.sav with its party raised to level 100 (IVs 31) by
`tools/dazzling/save_tool.py edit --level 100 --max-ivs` and Luxio (Bite, the fangs) in the lead, because the
save's level 29-30 party can't beat the level 38-43 raid trainers. Battles are fought with the headless
`battle_decide` queue (the lead's moves in turn, the next move when one does no damage, a switch if none do).

Scenarios (all run by default, in this order):
  pre_raid    progress 0: Room 1 is stock apart from the rope (rope present, no raid crew, the stair to Room 2 is
              blocked, the rope's sign text).
  run_abc     progress 20 -> 50 walking the whole route from the town: Room 1 scene (-> 30), SOL_01, Room 2,
              generator A (SOL_02, -> 31), Room 3 (SOL_03), Room 4, generator B (SOL_04, -> 32), Room 5 (SOL_05),
              Room 6, a visit to Room 7 with the barrier up (Cyrus "not yet", the barrier text), generator C
              (SOL_06, -> 33, FLAG_SOL_RAID_D), the vault: Indra (-> 40 -> 45), Looker, the switch (No, then Yes:
              FLAG_SOL_RAID_E), the warp to town (-> 50, FLAG_SOL_RAID_F).
  run_cab     progress 30, the generators in the order C, A, B by warping to each dead end (answering No once),
              then Room 7 at 33 (barrier gone, Cyrus aside: "It's down").
  post_raid   progress 50 with the raid flags: Room 1, a generator room and Room 7 are empty (the scorched vault:
              rubble, no racks, no barrier, no Cyrus/Indra/Looker; the stock item balls are there); the Room 2
              Hiker is back and, shown TM30, asks the way down and gives the Green Shard.
  indra_loss  a level 5 party (same save, --level 5) loses to Indra: whiteout, progress stays 40, and walking back
              into the vault replays the scene from "You turned off all three.".
Every beat asserts the map, position, VAR_SOLACEON_PROGRESS, FLAG_SOL_RAID_* and the objects present
(the headless `objects` command), and takes a screenshot (BMP + PNG) into <out dir>. A log of every command and
reply is in <out dir>/log.txt. Exit status 0 when every assertion passed.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "solaceon_town", "interior"))
from smoke_test import Game, Failure, TITLE_STEPS  # noqa: E402

BASE_SAVE = os.path.join(ROOT, "tools", "dazzling", "test", "fixtures", "eterna_forest_grass.sav")
SAVE_TOOL = os.path.join(ROOT, "tools", "dazzling", "save_tool.py")

TOWN = "MAP_HEADER_SOLACEON_TOWN"
R = "MAP_HEADER_SOLACEON_RUINS_"
R1, R2, R3, R4, R5, R6, R7 = (R + "ROOM_%d" % i for i in range(1, 8))
GEN_A, GEN_B, GEN_C = R + "ROOM_2_NORTHEAST_DEAD_END", R + "ROOM_4_SOUTHEAST_DEAD_END", R + "ROOM_6_NORTHWEST_DEAD_END"
RUINS_DOOR = (595, 655)          # Solaceon Town -> Room 1
PROGRESS = "VAR_SOLACEON_PROGRESS"
RAID_FLAGS = ["FLAG_SOL_RAID_" + c for c in "ABCDEFG"]
DELTA = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
KEY = {"N": "UP", "S": "DOWN", "W": "LEFT", "E": "RIGHT"}
TEXT_FRAMES = 90                # a box prints in well under this at the save's text speed


def make_save(out_path, level=100):
    r = subprocess.run([sys.executable, SAVE_TOOL, "edit", BASE_SAVE, "-o", out_path, "--level", str(level),
                        "--max-ivs", "--max-pp", "--lead", "3"], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("save_tool failed: " + r.stderr)
    return out_path


class Raid:
    def __init__(self, game, out_dir, prefix, results, shots):
        self.g, self.out, self.prefix, self.results, self.shots = game, out_dir, prefix, results, shots
        self.battles = 0
        self.losing = False      # (indra_loss: never switch on misses, the fainted mons are replaced in order)

    # ----------------------------------------------------------------------------------------------- basics
    def cmd(self, obj, **kw):
        return self.g.cmd(obj, **kw)

    def step(self, n):
        self.cmd({"cmd": "step", "frames": n})

    def press(self, key, n=6):
        self.cmd({"cmd": "press", "keys": [key], "frames": n})

    def state(self):
        return self.cmd({"cmd": "state", "vars": [PROGRESS], "flags": RAID_FLAGS})

    def where(self, st=None):
        st = st or self.state()
        p = st.get("player") or {}
        return st.get("map"), (p.get("x"), p.get("z"))

    def objects(self):
        r = self.cmd({"cmd": "objects"})
        if not r.get("ok"):
            raise Failure(f"objects: {r}")
        return {o["name"]: (o["x"], o["z"]) for o in r["objects"] if o["name"]}

    def shoot(self, name):
        bmp = os.path.join(self.out, f"{self.prefix}_{name}.bmp")
        self.cmd({"cmd": "screenshot", "path": bmp})
        if shutil.which("sips"):
            subprocess.run(["sips", "-s", "format", "png", bmp, "--out", bmp[:-4] + ".png"], capture_output=True)
        self.shots.append(bmp)

    def ok(self, cond, msg):
        self.results.append(("ok  " if cond else "FAIL") + f" [{self.prefix}] " + msg)
        print(self.results[-1], flush=True)
        if not cond:
            raise Failure(msg)

    # ------------------------------------------------------------------------------------------ assertions
    def expect(self, map_=None, pos=None, progress=None, flags=None, present=(), absent=(), label=""):
        st = self.state()
        m, p = self.where(st)
        v = st.get("vars", {}).get(PROGRESS)
        fl = {k for k, on in (st.get("flags") or {}).items() if on}
        objs = self.objects() if (present or absent) else {}
        parts = []
        if map_ is not None:
            parts.append(m == map_)
        if pos is not None:
            parts.append(tuple(p) == tuple(pos))
        if progress is not None:
            parts.append(v == progress)
        if flags is not None:
            parts.append(fl == {"FLAG_SOL_RAID_" + c for c in flags})
        miss = [o for o in present if o not in objs]
        extra = [o for o in absent if o in objs]
        parts.append(not miss and not extra)
        desc = (f"{label}: map {m.replace(R, 'R_') if m else m} at {p}, progress {v}, flags "
                f"{''.join(sorted(f[-1] for f in fl)) or '-'}")
        if miss:
            desc += f", MISSING {miss}"
        if extra:
            desc += f", UNEXPECTED {extra}"
        want = []
        if map_ is not None and m != map_:
            want.append(f"map {map_}")
        if pos is not None and tuple(p) != tuple(pos):
            want.append(f"pos {pos}")
        if progress is not None and v != progress:
            want.append(f"progress {progress}")
        if flags is not None and fl != {"FLAG_SOL_RAID_" + c for c in flags}:
            want.append(f"flags {flags or '-'}")
        if want:
            desc += " (want " + ", ".join(want) + ")"
        self.ok(all(parts), desc)
        return st

    # ------------------------------------------------------------------------------------------ the driver
    def idle(self, st):
        return st.get("app") == "field" and st.get("player") and st.get("script") is None \
            and not st.get("message_waiting")

    def drive(self, answer="A", shots=None, max_iters=3000, until=None):
        """Advances scripts and battles until the field is idle. `answer` is the key pressed at text and menus
        (A: Yes; B: No - B also advances text). `shots` maps the n-th text box (1-based) to a screenshot name."""
        shots = dict(shots or {})
        boxes, idle_n, busy = 0, 0, 0
        for _ in range(max_iters):
            st = self.state()
            if until and until(st):
                return st
            if st.get("app") == "battle":
                self.battle_tick(st)
                idle_n = 0
                continue
            if self.idle(st):
                # idle for a while: a trainer battle's encounter effect runs with no script and no text box
                idle_n += 1
                if idle_n >= 5:
                    return st
                self.step(40)
                continue
            idle_n = 0
            if st.get("message_waiting"):
                # a text box is open: let the box finish printing, then press (one press = one box)
                busy = 0
                self.step(TEXT_FRAMES)
                boxes += 1
                if boxes in shots:
                    self.shoot(shots.pop(boxes))
                self.press(answer, 4)
                self.step(6)
            else:
                # a script that waits on something that isn't a text box (a long movement, a fade): after a while
                # press the answer key (harmless during movements)
                busy += 1
                if busy >= 12:
                    busy = 0
                    self.press(answer, 4)
                self.step(20)
        raise Failure(f"drive: no idle field after {max_iters} iterations ({self.where()})")

    def battle_tick(self, st):
        b = st.get("battle") or {}
        if not getattr(self, "_in_battle", False):
            self._in_battle, self._move, self._miss, self._last, self._pushed = True, 0, 0, None, False
            self._slot, self._frames, self._shot, self._stuck, self._switch_queued = 0, 0, False, 0, False
            self._fainted = set()
            self.battles += 1
        self._frames += 1
        if self._frames > 4000:
            raise Failure("battle did not end")
        mine = (b.get("battlers") or [{}])[0]
        if not b.get("waiting"):
            self._pushed = False
            if mine.get("hp") == 0 and not self._switch_queued:
                # our battler fainted: answer "Use next Pokemon?" with the next party member that hasn't fainted
                # in this battle ("party" in the state is the field copy, so its HP is not the battle's)
                self._fainted.add(self._slot)
                party = st.get("party") or []
                nxt = next((i for i in range(len(party)) if i not in self._fainted), None)
                if nxt is not None:
                    self.cmd({"cmd": "battle_decide", "battler": 0, "action": "switch", "party_slot": nxt})
                    self._slot, self._switch_queued = nxt, True
            elif mine.get("hp"):
                self._switch_queued = False
            self.step(15)
            return
        if self._pushed:
            self._stuck += 1
            if self._stuck < 30:
                self.step(15)
                return
            # the decision was refused (no PP left, a Taunted status move...): try the next move
            self._move = (self._move + 1) % 4
            self._last = None
        if not self._shot:
            self.step(10)
            self.shoot(f"battle{self.battles}")
            self._shot = True
        opp = (b.get("battlers") or [{}, {}])[1] if len(b.get("battlers") or []) > 1 else {}
        key = (opp.get("species"), opp.get("hp"))
        # the lead's moves in turn (spreads the PP); a move that did no damage counts as a miss
        self._miss = self._miss + 1 if self._last == key else 0
        self._move = (self._move + 1) % 4
        self._last = key
        if self._miss >= 4 and not self.losing:   # nothing the lead knows hurts this one: send in the next member
            self._slot += 1
            self.cmd({"cmd": "battle_decide", "battler": 0, "action": "switch", "party_slot": self._slot})
            self._miss, self._move = 0, 0
        else:
            self.cmd({"cmd": "battle_decide", "battler": 0, "action": "move", "move_index": self._move})
        self._pushed, self._stuck = True, 0
        self.step(15)

    def after_battle(self):
        self._in_battle = False

    # --------------------------------------------------------------------------------------------- moving
    def boot(self, save, level=100):
        r = self.cmd({"cmd": "import_save", "path": os.path.abspath(save)})
        self.ok(bool(r.get("ok")), "imported the test save")
        for s in TITLE_STEPS:
            if "press" in s:
                self.press(s["press"], s.get("frames", 1))
            else:
                self.step(s["step"])
        for _ in range(120):
            st = self.state()
            if st.get("app") == "field" and st.get("player"):
                break
            self.press("B", 10)
            self.step(50)
        st = self.drive()
        lead = (st.get("party") or [{}])[0]
        self.ok(lead.get("level") == level, f"in the field, lead {lead.get('species')} Lv{lead.get('level')}")

    def set(self, progress=None, flags=None):
        if progress is not None:
            self.cmd({"cmd": "set_var", "name": PROGRESS, "value": progress})
        if flags is not None:
            for f in RAID_FLAGS:
                self.cmd({"cmd": "set_flag", "name": f, "value": f[-1] in flags})

    def warp(self, map_, x, z, d="DIR_SOUTH"):
        for _ in range(40):
            r = self.cmd({"cmd": "warp", "map": map_, "x": x, "z": z, "dir": d})
            if r.get("ok"):
                break
            self.press("A", 6)
            self.step(60)
        else:
            raise Failure(f"warp to {map_} refused")
        self.step(120)
        return self.drive()

    def go(self, path, answer="A", shots=None):
        """Walks a path like "NNE" one tile at a time. A step that starts a script (a trainer's eye, a trigger) is
        driven to the end; if it kept the player in place (a trainer who stopped the step), the step is tried
        again. A stair is entered by stepping onto it and once more in the same direction; the map change runs as
        a field task and is waited for. Fails if a step neither moves nor starts anything."""
        for c in path:
            m0, p0 = self.where()
            dx, dz = DELTA[KEY[c]]
            target = (p0[0] + dx, p0[1] + dz)
            for attempt in range(6):
                self.press(KEY[c], 6)
                self.step(12)
                st = self.state()
                m, p = self.where(st)
                if m == m0 and tuple(p) == tuple(p0) and self.idle(st):
                    continue                     # turned on the spot, or the press was lost: press again
                if m == m0:
                    for _ in range(6):           # a stair: give the warp time to change the map
                        self.step(15)
                        if self.where()[0] != m0:
                            break
                if self.where()[0] != m0:
                    for _ in range(20):
                        self.step(20)
                        if self.idle(self.state()):
                            break
                    self.step(40)
                st = self.state()
                ran = False
                if not self.idle(st) or st.get("app") == "battle":
                    self.drive(answer=answer, shots=shots)
                    self.after_battle()
                    ran = True
                m, p = self.where()
                if m != m0 or tuple(p) == target or (ran and tuple(p) != tuple(p0)):
                    break                        # (a script that moved the player: its position is the result)
                if tuple(p) != tuple(p0):
                    raise Failure(f"walking {c} from {p0} on {m0} ended at {p}")
            else:
                raise Failure(f"could not walk {c} from {p0} on {m0}")

    def face(self, c):
        self.press(KEY[c], 2)
        self.step(10)

    def interact(self, answer="A", shots=None):
        self.press("A", 4)
        self.step(10)
        st = self.drive(answer=answer, shots=shots)
        self.after_battle()
        return st


# ---------------------------------------------------------------------------------------------- scenarios
R1_CREW = ["LOCALID_R1_GRUNT_01", "LOCALID_R1_CRATE_0", "LOCALID_R1_CRATE_1"]
R7_LIT = ["LOCALID_R7_RACK_%d_LIT" % i for i in range(6)] + ["LOCALID_R7_CRYSTAL_LIT"]
R7_DARK = ["LOCALID_R7_RACK_%d_DARK" % i for i in range(6)] + ["LOCALID_R7_CRYSTAL_DARK"]
R7_BARRIER = ["LOCALID_R7_BARRIER_%d" % i for i in range(7)]
R7_CRATES = ["LOCALID_R7_CRATE_%d" % i for i in range(6)]
R7_BALLS = ["LOCALID_ITEM_MIND_PLATE", "LOCALID_ITEM_ODD_INCENSE", "LOCALID_ITEM_NUGGET", "LOCALID_ITEM_TM30"]


def gen_room(x):
    return {"A": GEN_A, "B": GEN_B, "C": GEN_C}[x]


GEN_OBJS = lambda x: ["LOCALID_GEN_%s_ON" % x, "LOCALID_GEN_%s_RACK_ON" % x]           # noqa: E731
GEN_OFF = lambda x: ["LOCALID_GEN_%s_OFF" % x, "LOCALID_GEN_%s_RACK_OFF" % x]          # noqa: E731
# arrival tile, the path to the guard's sight, the path from there to the generator's talk tile, the way back out
GEN_ROUTE = {
    "A": dict(arrive=(4, 3), fight="E", to_switch="SEEN", back="SWWNWW"),
    "B": dict(arrive=(2, 3), fight="E", to_switch="SEEN", back="SWWNWW"),
    "C": dict(arrive=(5, 3), fight="W", to_switch="SWWN", back="SEENEE"),
}


def enter_from_town(t):
    t.warp(TOWN, RUINS_DOOR[0], RUINS_DOOR[1] + 1, "DIR_NORTH")
    t.shoot("00_town_ruins_door")
    for _ in range(10):
        t.press("UP", 16)
        for _ in range(20):
            t.step(10)
            if t.where()[0] == R1:
                break
        if t.where()[0] == R1:
            break
    t.step(60)


def generator(t, x, expect_progress, done_flags, answer_no_first=False):
    room = gen_room(x)
    r = GEN_ROUTE[x]
    t.expect(room, r["arrive"], present=GEN_OBJS(x) + ["LOCALID_GEN_%s_GUARD" % x], absent=GEN_OFF(x),
             label=f"generator {x} room, on")
    t.shoot(f"gen{x}_1_arrive")
    t.go(r["fight"], shots={1: f"gen{x}_2_guard_text"})
    t.ok(t.battles >= 1, f"fought the generator {x} guard ({t.battles} battle(s) so far)")
    t.go(r["to_switch"])
    t.face("N")
    if answer_no_first:
        t.interact(answer="B")
        t.expect(room, progress=expect_progress - 1, present=GEN_OBJS(x), label=f"generator {x}: answered No, still on")
    t.interact(shots={2: f"gen{x}_3_prompt", 3: f"gen{x}_4_switched_off", 5: f"gen{x}_5_poketch", 6: f"gen{x}_5_ruth"})
    st = t.expect(room, progress=expect_progress, flags=done_flags, present=GEN_OFF(x), absent=GEN_OBJS(x),
                  label=f"generator {x} switched off")
    t.shoot(f"gen{x}_6_off")
    t.interact(shots={1: f"gen{x}_7_already_off"})
    t.expect(room, progress=expect_progress, label=f"generator {x}: talking again says it is off, nothing changes")
    return st


def scenario_pre_raid(t):
    t.set(progress=0, flags="")
    enter_from_town(t)
    t.expect(R1, (5, 11), progress=0, present=["LOCALID_R1_ROPE"],
             absent=R1_CREW + ["LOCALID_R1_CYRUS"], label="pre-raid Room 1: rope only, no raid crew")
    t.go("NNNNNNN")                          # up the middle to (5,4)
    t.go("N")                                # (5,3), beside the roped stair
    t.expect(R1, (5, 3), progress=0, label="beside the roped stair")
    t.shoot("pre_1_rope")
    t.press("RIGHT", 6)
    t.step(30)
    t.expect(R1, (5, 3), progress=0, label="the rope blocks the stair to Room 2 (6,3)")
    t.interact(shots={1: "pre_2_rope_sign_a", 2: "pre_3_rope_sign_b"})
    t.expect(R1, (5, 3), progress=0, label="read the rope sign")
    t.go("SSSSSSSS")
    t.expect(R1, (5, 11), progress=0, label="back at the exit")


def scenario_run_abc(t):
    t.set(progress=20, flags="")
    enter_from_town(t)
    # Room 1: the entry scene plays at once (init frame table)
    t.drive(shots={1: "r1_1_cyrus_hum", 3: "r1_2_cyrus_three_lines", 7: "r1_3_poketch", 8: "r1_4_ruth"})
    t.expect(R1, (5, 7), progress=30, flags="", present=R1_CREW, absent=["LOCALID_R1_CYRUS", "LOCALID_R1_ROPE"],
             label="Room 1 scene done: 30, Cyrus gone ahead, crew on the stair")
    t.shoot("r1_5_after_scene")
    t.go("NN")
    t.go("E", shots={1: "r1_6_sol01_text"})               # (6,5): SOL_01's eye
    t.ok(t.battles == 1, "SOL_01 battle")
    t.expect(R1, progress=30, label="beat SOL_01")
    t.shoot("r1_7_after_sol01")
    t.face("N")
    t.interact(shots={1: "r1_8_sol01_post_battle"})      # his TRMSG_POST_BATTLE
    t.go("WNNEE")                                        # round him onto the stair (6,3), then off east
    t.expect(R2, progress=30, present=["LOCALID_R2_CRATE_0", "LOCALID_R2_FRAME_0"], absent=["LOCALID_HIKER"],
             label="Room 2: crates, the Hiker hidden during the raid")
    t.shoot("r2_1_arrive")
    t.go("EEE")                                          # the stair to generator A (6,3), off east
    generator(t, "A", 31, "A")
    t.go(GEN_ROUTE["A"]["back"])
    t.expect(R2, label="back in Room 2")
    t.go("W" + "S" * 7 + "WW")                           # down to the stair to Room 3 (4,10), off west
    t.expect(R3, progress=31, present=["LOCALID_R3_GRUNT_03", "LOCALID_RUIN_MANIAC_KARL"], label="Room 3")
    t.shoot("r3_1_arrive")
    before = t.battles
    t.go("NN", shots={1: "r3_2_sol03_text"})             # (6,8): SOL_03's eye
    t.ok(t.battles == before + 1, "SOL_03 battle")
    t.go("NWWNNENNEE")                                   # around SOL_03, Karl and the crate to the stair (6,3)
    t.expect(R4, progress=31, present=["LOCALID_R4_FRAME_0"], label="Room 4")
    t.go("EEE")                                          # the stair to generator B (6,10), off east
    generator(t, "B", 32, "AB")
    t.go(GEN_ROUTE["B"]["back"])
    t.go("W" + "N" * 7 + "WW")                           # up to the stair to Room 5 (4,3), off west
    t.expect(R5, progress=32, present=["LOCALID_R5_GRUNT_05"], label="Room 5")
    t.shoot("r5_1_arrive")
    before = t.battles
    t.go("WWWW", shots={1: "r5_2_sol05_text"})           # to the stair to Room 6 (2,3), SOL_05 below it
    t.ok(t.battles == before + 1 or t.where()[0] == R6, f"SOL_05 ({t.battles - before} battle)")
    if t.where()[0] != R6:
        t.go("W")
    t.expect(R6, progress=32, present=["LOCALID_R6_CRYSTAL_0"], label="Room 6")
    # a look at the barrier before the last generator
    t.go("SWW" + "S" * 6 + "W")                          # to the stair to Room 7 (4,10), off west
    t.expect(R7, (8, 3), progress=32, present=R7_BARRIER + ["LOCALID_R7_CYRUS", "LOCALID_R7_INDRA"] + R7_LIT,
             absent=["LOCALID_R7_LOOKER", "LOCALID_R7_RUBBLE"] + R7_DARK, label="Room 7 at 32: barrier up")
    t.shoot("r7_1_barrier_up")
    t.go("S", shots={1: "r7_2_barrier_text"})            # (8,4): walking up to the barrier
    t.go("WW")
    t.expect(R7, (6, 4), progress=32, label="standing behind the barrier")
    t.shoot("r7_3_player_behind_barrier")
    t.face("W")
    t.interact(shots={1: "r7_4_cyrus_not_yet"})
    t.face("S")
    t.interact(shots={1: "r7_5_barrier_talk"})
    t.warp(R6, 4, 9, "DIR_NORTH")                        # back to Room 6 (the test warps instead of walking back)
    t.go("N" * 6 + "W")                                  # to the stair to generator C (4,3), off west
    generator(t, "C", 33, "ABCD")
    t.go(GEN_ROUTE["C"]["back"])
    t.go("S" * 7 + "W")                                  # down to the stair to Room 7 (4,10), off west
    st = t.expect(R7, (8, 3), progress=33, flags="ABCD", present=["LOCALID_R7_CYRUS", "LOCALID_R7_INDRA"] + R7_LIT,
                  absent=R7_BARRIER + ["LOCALID_R7_LOOKER"] + R7_DARK, label="Room 7 at 33: barrier down")
    objs = t.objects()
    t.ok(objs.get("LOCALID_R7_CYRUS") == (6, 4), f"Cyrus stands aside at {objs.get('LOCALID_R7_CYRUS')}")
    t.shoot("r7_6_barrier_down")
    t.go("SW")
    t.face("W")
    t.interact(shots={1: "r7_7_cyrus_its_down"})
    # the vault
    before = t.battles
    t.go("SS", shots={1: "r7_8_indra_all_three", 3: "r7_9_indra_rowans_kid", 9: "r7_10_indra_late",
                      14: "r7_11_indra_hm", 17: "r7_12_indra_what_stopped", 21: "r7_13_indra_dont_follow",
                      22: "r7_14_cyrus_let_her_go", 23: "r7_15_looker_gone", 30: "r7_16_looker_families",
                      31: "r7_17_looker_destroyed", 32: "r7_18_cyrus_racks", 35: "r7_19_switch_yours"})
    t.ok(t.battles == before + 1, "Indra battle")
    t.expect(R7, (5, 8), progress=45, flags="ABCDG",
             present=["LOCALID_R7_RUBBLE", "LOCALID_R7_LOOKER", "LOCALID_R7_CYRUS"] + R7_LIT,
             absent=["LOCALID_R7_INDRA"] + R7_DARK, label="Indra beaten and gone, the cave-in, Looker")
    objs = t.objects()
    t.ok(objs.get("LOCALID_R7_LOOKER") == (6, 8) and objs.get("LOCALID_R7_CYRUS") == (5, 7),
         f"Looker at {objs.get('LOCALID_R7_LOOKER')}, Cyrus at {objs.get('LOCALID_R7_CYRUS')}")
    t.shoot("r7_20_after_indra")
    t.go("SS")
    t.face("S")
    t.expect(R7, (5, 10), progress=45, label="at the main rack's switch")
    t.interact(answer="B", shots={2: "r7_21_switch_prompt", 3: "r7_22_switch_no"})
    t.expect(R7, (5, 10), progress=45, flags="ABCDG", present=R7_LIT, label="switch: No, nothing changes")
    t.interact(shots={3: "r7_23_drained", 4: "r7_23b_grey", 6: "r7_24_ruth_gone", 10: "r7_25_ledger_elias",
                      12: "r7_26_ledger_teo", 14: "r7_27_looker_police"})
    t.step(240)
    t.drive()
    t.expect(TOWN, progress=50, flags="ABCDEFG", label="the switch drained the racks; warped to town at 50")
    t.shoot("r7_28_town_after")


def scenario_run_cab(t):
    t.set(progress=30, flags="")
    t.warp(GEN_C, *GEN_ROUTE["C"]["arrive"], "DIR_WEST")
    generator(t, "C", 31, "C", answer_no_first=True)
    t.warp(GEN_A, *GEN_ROUTE["A"]["arrive"], "DIR_EAST")
    generator(t, "A", 32, "AC")
    t.warp(GEN_B, *GEN_ROUTE["B"]["arrive"], "DIR_EAST")
    generator(t, "B", 33, "ABCD")
    t.warp(R6, 4, 9, "DIR_SOUTH")
    t.go("SW")
    t.expect(R7, (8, 3), progress=33, flags="ABCD", present=["LOCALID_R7_CYRUS"], absent=R7_BARRIER,
             label="Room 7 at 33 after C, A, B: barrier down")
    t.shoot("r7_barrier_down")
    t.go("SW")
    t.face("W")
    t.interact(shots={1: "r7_cyrus_its_down"})


def scenario_post_raid(t):
    t.set(progress=50, flags="ABCDEFG")
    # the town plays the seizure (3.4a part 7, town-scripts) on the first load at 50 unless it has been seen
    t.cmd({"cmd": "set_flag", "name": "FLAG_SOL_TOWN_A", "value": True})
    enter_from_town(t)
    t.expect(R1, (5, 11), progress=50, absent=R1_CREW + ["LOCALID_R1_ROPE", "LOCALID_R1_CYRUS"],
             label="Room 1 after the raid: open and empty")
    t.shoot("post_1_room1")
    t.warp(GEN_B, *GEN_ROUTE["B"]["arrive"], "DIR_EAST")
    t.expect(GEN_B, absent=GEN_OBJS("B") + GEN_OFF("B") + ["LOCALID_GEN_B_GUARD", "LOCALID_GEN_B_CRATE_0"],
             label="generator B room after the raid: empty")
    t.shoot("post_2_gen_b")
    t.warp(R2, 4, 4, "DIR_SOUTH")
    t.expect(R2, present=["LOCALID_HIKER"], absent=["LOCALID_R2_CRATE_0", "LOCALID_R2_FRAME_0"],
             label="Room 2 after the raid: the Hiker is back, no crates")
    shards = t.cmd({"cmd": "state", "bag": ["ITEM_GREEN_SHARD"]}).get("bag", {}).get("ITEM_GREEN_SHARD", 0)
    t.cmd({"cmd": "give_item", "item": "ITEM_TM30", "qty": 1})
    r = t.cmd({"cmd": "talk", "localid": "LOCALID_HIKER"})
    t.ok(bool(r.get("ok")), f"talked to the Hiker: {r}")
    t.drive(shots={3: "post_2b_hiker_tm30", 7: "post_2c_hiker_way_down"})
    st = t.cmd({"cmd": "state", "bag": ["ITEM_GREEN_SHARD"]})
    t.ok(st.get("bag", {}).get("ITEM_GREEN_SHARD", 0) == shards + 1,
         f"the Hiker gave a Green Shard ({shards} -> {st.get('bag', {}).get('ITEM_GREEN_SHARD')})")
    t.warp(R7, 8, 4, "DIR_SOUTH")
    t.expect(R7, progress=50, present=["LOCALID_R7_RUBBLE"] + R7_BALLS,
             absent=R7_LIT + R7_DARK + R7_BARRIER + R7_CRATES +
             ["LOCALID_R7_CYRUS", "LOCALID_R7_INDRA", "LOCALID_R7_LOOKER"],
             label="Room 7 after the raid: scorched and empty (rubble, the stock balls)")
    t.shoot("post_3_vault_empty")
    t.go("WWWSSSSS")                                     # into the vault, (5,9)
    t.shoot("post_4_vault_inside")
    t.go("S")
    t.face("S")
    t.interact(shots={1: "post_5_switch_turned"})
    t.expect(R7, (5, 10), progress=50, label="the switch after the raid only describes the dial")


def scenario_indra_loss(t):
    """A level 5 party loses to Indra: stock whiteout, progress stays 40, and the vault scene replays."""
    t.losing = True
    t.set(progress=33, flags="ABCD")
    t.warp(R6, 4, 9, "DIR_SOUTH")
    t.go("SW")
    t.expect(R7, (8, 3), progress=33, absent=R7_BARRIER, label="Room 7 at 33 with a level 5 party")
    t.go("SWSS")                                          # (7,6): the vault scene, the battle, the loss
    st = t.expect(progress=40, flags="ABCD", label="lost to Indra: whited out, progress stays 40")
    t.ok(st.get("map") != R7, f"whited out to {st.get('map')}")
    t.shoot("loss_1_whited_out")
    t.warp(R6, 4, 9, "DIR_SOUTH")
    t.go("SW")
    t.expect(R7, (8, 3), progress=40, present=["LOCALID_R7_INDRA", "LOCALID_R7_CYRUS"] + R7_LIT,
             absent=R7_BARRIER + ["LOCALID_R7_LOOKER", "LOCALID_R7_RUBBLE"], label="back in Room 7 at 40")
    t.go("SWS")
    t.press("DOWN", 6)                                    # onto row 6: the scene starts again
    st = t.drive(until=lambda s: s.get("message_waiting"))
    t.step(TEXT_FRAMES)
    t.shoot("loss_2_scene_replays")
    st = t.state()
    t.ok(st.get("vars", {}).get(PROGRESS) == 40 and st.get("message_waiting"),
         "the vault scene replays from the start at 40 (Indra: You turned off all three.)")


SCENARIOS = [("pre_raid", scenario_pre_raid), ("run_abc", scenario_run_abc), ("run_cab", scenario_run_cab),
             ("post_raid", scenario_post_raid), ("indra_loss", scenario_indra_loss)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("build_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--only", default="")
    ap.add_argument("--keep-run-dir", action="store_true")
    a = ap.parse_args()
    build_dir = os.path.abspath(a.build_dir)
    os.makedirs(a.out_dir, exist_ok=True)
    save = make_save(os.path.join(a.out_dir, "raid_test_lv100.sav"))
    weak = make_save(os.path.join(a.out_dir, "raid_test_lv5.sav"), level=5)
    only = [s for s in a.only.split(",") if s]
    results, shots, failed = [], [], []
    t0 = time.time()
    with open(os.path.join(a.out_dir, "log.txt"), "w") as log:
        for name, fn in SCENARIOS:
            if only and name not in only:
                continue
            run_dir = tempfile.mkdtemp(prefix="dz-raid-")
            game = Game(build_dir, run_dir, log)
            t = Raid(game, a.out_dir, name, results, shots)
            log.write(f"\n===== {name}\n")
            try:
                t.boot(weak if name == "indra_loss" else save, 5 if name == "indra_loss" else 100)
                fn(t)
                results.append(f"PASS [{name}]")
            except Failure as e:
                failed.append(name)
                if not results or not results[-1].startswith("FAIL"):
                    results.append(f"FAIL [{name}] {e}")
                print(results[-1], flush=True)
                try:
                    log.write(json.dumps(t.state()) + "\n")
                    t.shoot("failure")
                except Exception:
                    pass
            finally:
                game.close()
                shutil.copy(os.path.join(run_dir, "game.stderr.log"),
                            os.path.join(a.out_dir, f"game_{name}.stderr.log"))
                if not a.keep_run_dir:
                    shutil.rmtree(run_dir, ignore_errors=True)
        log.write("\n".join(results) + "\n")
    print(f"{'PASS' if not failed else 'FAIL ' + ','.join(failed)} in {time.time() - t0:.0f}s; "
          f"{len(shots)} screenshots in {a.out_dir}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
