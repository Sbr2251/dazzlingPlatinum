#!/usr/bin/env python3
"""Headless test of the Solaceon town scripts (town-scripts workstream) on the macOS app. Standard library only.

Usage: python3 tools/solaceon_town/town_test.py <build dir> <out dir> [--only NAME[,NAME]] [--keep-run-dir]
       e.g. python3 tools/solaceon_town/town_test.py build_macos "/tmp/Solaceon Update/scripts_mac"

Each scenario boots a fresh game (SIM_CONTROL=stdio, docs/headless_protocol.md) from the repo's Arc 2 save
(tools/dazzling/test/fixtures/eterna_forest_grass.sav) raised to level 100 by `tools/dazzling/save_tool.py edit
--level 100 --max-ivs --max-pp` (the fence grunts are level 38), sets the story state with set_var / set_flag and
warps into Solaceon Town. It uses the driver of tools/solaceon_ruins/raid_test.py (text boxes, battles, walking).

Scenarios (all by default, in this order); screenshots go to <out dir>/<scenario>/:
  cutaway  VAR_ARC2_PROGRESS 44: walking in from the north road plays the 2.16a Indra cutaway (47 during it, 49
           after, Indra gone, the player at the wall).
  A        50: band A objects; every NPC talked to, every sign read; the Sanctuary (door in, every NPC and sign,
           the office open, out by the mat); a wild battle in the garden of names (Yamask or Duskull).
  B        60: band B; the Sanctuary office blocked by the hall grunt on (19,13).
  C        90: band C (torn banners, the sister leaving, the girl back).
  D        99, Solaceon 0: band D; the hall door is locked (message, no warp); a player left inside the compound is
           let out by the gate grunt; the Sanctuary is empty (entered by warp, exit-only).
  briefing 99, Solaceon 10: Looker and Cyrus at the wall; the briefing (3.4a part 1) -> 20, the gate open, Cyrus at
           the fence; then band R: walking into the dig plays the fence scene (3.4a part 2), both battles, the pair
           step aside, Cyrus goes into the Ruins; the post-battle lines; Room 1 is reachable; R townspeople and the
           Sanctuary with Looker in the office.
  fence_talk 20: talking to the fence grunt instead of walking in runs the same scene.
  fence_loss 20, a level 5 party: SOL_07 beaten without SOL_08 is reset on load; losing at the fence whites out
           and the pair (and Cyrus) are back in place.
  E        50: the seizure (3.4a part 7) plays on the first load (Dusk Stone, FLAG_SOL_TOWN_A), not on the second
           (entered at (571,657): the scene first warps the player to its spot); band E objects, NPCs, signs, the
           Sanctuary.
  seizure_shots  50, entered on raid-scripts' landing spot (580,660): every box of the seizure.
  F        FLAG_GAME_COMPLETED: band F objects, NPCs, signs (memorial plaque), Indra at the wall once (the TEO card
           gets her text), the Sanctuary.
Every NPC talk and sign read is driven until the field is idle again (no script, no text box) and every text box
is screenshotted (BMP + PNG). Every line's width is checked statically first (tools/solaceon_town/
screenplay_text.py: 197 px, 2 lines per box). A log of every command and reply is <out dir>/log.txt.
Exit status 0 when every assertion passed.
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
sys.path.insert(0, os.path.join(ROOT, "tools", "solaceon_ruins"))
sys.path.insert(0, os.path.join(ROOT, "tools", "solaceon_town", "interior"))
sys.path.insert(0, HERE)
from smoke_test import Game, Failure  # noqa: E402
from raid_test import Raid, make_save  # noqa: E402
import screenplay_text  # noqa: E402
import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location("town_layout", os.path.join(HERE, "layout.py"))
LAYOUT = importlib.util.module_from_spec(_spec)   # (tools/solaceon_town/layout.py; other dirs have a layout.py too)
_spec.loader.exec_module(LAYOUT)

TOWN = "MAP_HEADER_SOLACEON_TOWN"
SANCT = "MAP_HEADER_SOLACEON_SANCTUARY"
ROOM1 = "MAP_HEADER_SOLACEON_RUINS_ROOM_1"
SOL, ARC2 = "VAR_SOLACEON_PROGRESS", "VAR_ARC2_PROGRESS"
FLAGS = ["FLAG_SOL_TOWN_A", "FLAG_SOL_TOWN_B", "FLAG_GAME_COMPLETED"]
BEAT07, BEAT08 = "FLAG_DEFEATED_TRAINER_DUMMY_833", "FLAG_DEFEATED_TRAINER_DUMMY_834"   # 1360 + SOL_07 / SOL_08
L = lambda n: "LOCALID_" + n     # noqa: E731

TOWN_OBJS = ["TENT_CLERK", "PILGRIM_FATHER", "PILGRIM_SAILOR", "PILGRIM_SISTER", "PILGRIM_SON", "ROAD_GREETER",
             "WALL_WIDOW", "GARDEN_GIRL", "LANTERN_MAN", "BELIEVER_MOTHER", "LOOKER", "CYRUS", "GATE_GREETER",
             "GATE_GRUNT_L", "GATE_GRUNT_R", "FORECOURT_SWEEPER", "IP_OFFICER_GATE", "IP_OFFICER_COURT", "DIG_WORKER",
             "EXCAVATION_GRUNT_M", "EXCAVATION_GRUNT_F", "RUIN_MANIAC", "IP_OFFICER_DIG", "KENNEL_KEEPER",
             "KENNEL_MON_1", "KENNEL_MON_2", "KENNEL_MON_3", "KENNEL_MON_4", "LOADING_GRUNT", "RANCHER",
             "DAYCARE_KID", "SUNDAY_MAN", "DOUBTER", "POKETCH_MAN", "ARC2_INDRA", "QUESTS_BANNER_NORTH",
             "QUESTS_BANNER_SOUTH"] + ["CRATE_%d" % i for i in range(1, 7)]
ALWAYS = ["WALL_WIDOW", "LANTERN_MAN", "BELIEVER_MOTHER", "KENNEL_KEEPER", "RANCHER", "DAYCARE_KID", "SUNDAY_MAN",
          "POKETCH_MAN"]
BANNERS = ["QUESTS_BANNER_NORTH", "QUESTS_BANNER_SOUTH"]
CR = lambda n: ["CRATE_%d" % i for i in range(1, n + 1)]   # noqa: E731
# band -> objects present (screenplay Part 2 "Out:" lists); anything else in TOWN_OBJS must be absent
BAND_OBJS = {
    "A": ALWAYS + ["TENT_CLERK", "PILGRIM_FATHER", "PILGRIM_SAILOR", "PILGRIM_SISTER", "PILGRIM_SON", "ROAD_GREETER",
                   "GARDEN_GIRL", "GATE_GREETER", "FORECOURT_SWEEPER", "DIG_WORKER", "RUIN_MANIAC", "KENNEL_MON_1",
                   "KENNEL_MON_2", "KENNEL_MON_3", "KENNEL_MON_4", "DOUBTER"] + BANNERS,
    "B": ALWAYS + ["TENT_CLERK", "PILGRIM_FATHER", "GATE_GRUNT_L", "GATE_GRUNT_R", "FORECOURT_SWEEPER",
                   "EXCAVATION_GRUNT_M", "EXCAVATION_GRUNT_F", "KENNEL_MON_1", "KENNEL_MON_2", "LOADING_GRUNT",
                   "DOUBTER"] + BANNERS + CR(4),
    "C": ALWAYS + ["TENT_CLERK", "PILGRIM_FATHER", "PILGRIM_SISTER", "GARDEN_GIRL", "GATE_GRUNT_L", "GATE_GRUNT_R",
                   "FORECOURT_SWEEPER", "EXCAVATION_GRUNT_M", "EXCAVATION_GRUNT_F", "KENNEL_MON_1",
                   "DOUBTER"] + BANNERS,
    "D": ALWAYS + ["TENT_CLERK", "PILGRIM_FATHER", "PILGRIM_SON", "GATE_GRUNT_L", "GATE_GRUNT_R",
                   "EXCAVATION_GRUNT_M", "EXCAVATION_GRUNT_F", "LOADING_GRUNT"] + BANNERS + CR(6),
    "R": ALWAYS + ["TENT_CLERK", "PILGRIM_FATHER", "PILGRIM_SON", "EXCAVATION_GRUNT_M", "EXCAVATION_GRUNT_F"]
    + BANNERS + CR(6),
    "E": ALWAYS + ["TENT_CLERK", "PILGRIM_FATHER", "GARDEN_GIRL", "IP_OFFICER_GATE", "IP_OFFICER_COURT", "RUIN_MANIAC",
                   "IP_OFFICER_DIG", "KENNEL_MON_1", "DOUBTER"] + BANNERS + CR(1),
    "F": ALWAYS + ["TENT_CLERK", "PILGRIM_FATHER", "PILGRIM_SAILOR", "PILGRIM_SISTER", "GARDEN_GIRL", "DIG_WORKER",
                   "RUIN_MANIAC", "KENNEL_MON_1", "KENNEL_MON_2", "KENNEL_MON_3", "KENNEL_MON_4", "DOUBTER"],
}
# positions that change per band (layout.md NPC spots)
BAND_POS = {
    "A": {"TENT_CLERK": (566, 643), "PILGRIM_FATHER": (565, 645), "POKETCH_MAN": (579, 644), "KENNEL_KEEPER": (555, 665)},
    "B": {"PILGRIM_FATHER": (558, 653), "GATE_GRUNT_L": (579, 659), "EXCAVATION_GRUNT_M": (595, 659)},
    "C": {"PILGRIM_SISTER": (561, 641), "PILGRIM_FATHER": (558, 653)},
    "D": {"GATE_GRUNT_L": (580, 659), "PILGRIM_SON": (567, 645), "EXCAVATION_GRUNT_M": (595, 659)},
    "F": {"TENT_CLERK": (567, 651), "PILGRIM_FATHER": (565, 650), "PILGRIM_SAILOR": (567, 650),
          "PILGRIM_SISTER": (565, 652)},
}
# town signs: name -> (read tile, facing key); bg events in res/field/maps/solaceon_town/events.json
SIGNS = {
    "gate_plaque": ((580, 658), "W"), "tent_sign": ((564, 645), "N"), "dig_sign": ((594, 660), "N"),
    "kennel_sign": ((554, 665), "N"), "memorial_plaque": ((558, 650), "W"), "banner_post_nw": ((558, 643), "W"),
    "banner_post_se": ((562, 647), "E"), "wall_photos": ((557, 652), "W"), "wall_ponyta": ((557, 653), "W"),
    "wall_elias": ((557, 654), "W"), "wall_banner": ((557, 655), "W"), "wall_teo": ((557, 656), "W"),
    "hall_door": ((580, 653), "N"),
}
SANCT_OBJS = ["SPEAKER", "HALL_ATTENDANT", "TESTIMONY_A", "TESTIMONY_B", "TESTIMONY_C", "RECORDS_CLERK", "HALL_GRUNT",
              "BACK_DOOR_GRUNT", "LOOKER", "IP_OFFICER_HALL", "IP_OFFICER_OFFICE"]
SANCT_BAND = {
    "A": ["SPEAKER", "HALL_ATTENDANT", "TESTIMONY_A", "TESTIMONY_B", "TESTIMONY_C", "RECORDS_CLERK"],
    "B": ["SPEAKER", "TESTIMONY_A", "TESTIMONY_C", "RECORDS_CLERK", "HALL_GRUNT", "BACK_DOOR_GRUNT"],
    "C": ["SPEAKER", "TESTIMONY_B", "TESTIMONY_C", "RECORDS_CLERK", "HALL_GRUNT", "BACK_DOOR_GRUNT"],
    "D": [], "R": ["LOOKER"], "E": ["TESTIMONY_A", "IP_OFFICER_HALL", "IP_OFFICER_OFFICE"], "F": ["RECORDS_CLERK"],
}
SANCT_SIGNS = {
    "lectern": ((9, 9), "E"), "notice_board": ((6, 17), "S"), "filing_drawers": ((20, 8), "N"),
    "ledger": ((22, 11), "N"), "indras_desk": ((24, 10), "W"), "back_door": ((18, 7), "N"),
}
OFFICE_SIGNS = ("filing_drawers", "ledger", "indras_desk")
DIRS = {"N": "DIR_NORTH", "S": "DIR_SOUTH", "W": "DIR_WEST", "E": "DIR_EAST"}


class Town(Raid):
    def __init__(self, game, out_dir, prefix, results, shots):
        os.makedirs(os.path.join(out_dir, prefix), exist_ok=True)
        super().__init__(game, os.path.join(out_dir, prefix), prefix, results, shots)

    def shoot(self, name):
        bmp = os.path.join(self.out, f"{name}.bmp")
        self.cmd({"cmd": "screenshot", "path": bmp})
        if shutil.which("sips"):
            subprocess.run(["sips", "-s", "format", "png", bmp, "--out", bmp[:-4] + ".png"], capture_output=True)
        self.shots.append(bmp)

    def state(self):
        return self.cmd({"cmd": "state", "vars": [SOL, ARC2], "flags": FLAGS + [BEAT07, BEAT08],
                         "bag": ["ITEM_DUSK_STONE"]})

    def var(self, name, st=None):
        return (st or self.state()).get("vars", {}).get(name)

    def flag(self, name, st=None):
        return bool((st or self.state()).get("flags", {}).get(name))

    def setstate(self, arc2=None, sol=None, flags=()):
        if arc2 is not None:
            self.cmd({"cmd": "set_var", "name": ARC2, "value": arc2})
        if sol is not None:
            self.cmd({"cmd": "set_var", "name": SOL, "value": sol})
        for f in FLAGS:
            self.cmd({"cmd": "set_flag", "name": f, "value": f in flags})

    def objs(self, prefix_ok=True):
        return self.objects()

    def check_band_objects(self, band, names=TOWN_OBJS, table=BAND_OBJS, pos=BAND_POS, extra=(), missing=()):
        want = (set(table[band]) | set(extra)) - set(missing)
        have = self.objects()
        present = {n for n in names if L(n) in have}
        miss, unexp = sorted(want - present), sorted(present - want)
        badpos = [f"{n} at {have[L(n)]} (want {p})" for n, p in pos.get(band, {}).items()
                  if L(n) in have and tuple(have[L(n)]) != tuple(p)]
        self.ok(not miss and not unexp and not badpos,
                f"band {band}: {len(present)} objects" + (f", MISSING {miss}" if miss else "")
                + (f", UNEXPECTED {unexp}" if unexp else "") + (f", MOVED {badpos}" if badpos else ""))
        return have

    def idle_check(self, label):
        st = self.state()
        self.ok(self.idle(st), f"{label}: back to the idle field at {self.where(st)[1]}")
        return st

    def near(self, name):
        """Warps next to a town object first (the free side `talk` picks: north, south, west, east), so `talk`'s own
        teleport stays short: a long jump leaves the map loader on the old chunks (black terrain in screenshots)."""
        if self.where()[0] != TOWN:
            return
        have = self.objects()
        if L(name) not in have:
            return
        ox, oz = have[L(name)]
        taken = {tuple(p) for n, p in have.items()}
        t = LAYOUT.tiles()
        for dx, dz, face in ((0, -1, "DIR_SOUTH"), (0, 1, "DIR_NORTH"), (-1, 0, "DIR_EAST"), (1, 0, "DIR_WEST")):
            x, z = ox + dx, oz + dz
            if LAYOUT.walkable(t, x, z) and (x, z) not in taken:
                self.warp(TOWN, x, z, face)
                return

    def talk(self, name, shots=6, prefix=""):
        self.near(name)
        r = self.cmd({"cmd": "talk", "localid": L(name)})
        self.ok(bool(r.get("ok")), f"talk {name}: {r.get('error', 'started')}")
        self.step(4)
        self.drive(shots={i: f"{prefix}{name.lower()}_{i}" for i in range(1, shots + 1)})
        self.after_battle()
        return self.idle_check(f"talk {name}")

    def read(self, name, tile, facing, map_=TOWN, shots=5):
        self.warp(map_, tile[0], tile[1], DIRS[facing])
        self.face(facing)
        self.press("A", 4)
        self.step(10)
        self.drive(shots={i: f"{name}_{i}" for i in range(1, shots + 1)})
        return self.idle_check(f"read {name}")

    def enter_town(self, x=560, z=648, d="DIR_SOUTH"):
        st = self.warp(TOWN, x, z, d)
        self.ok(self.where(st)[0] == TOWN, f"in Solaceon Town at {self.where(st)[1]}")
        return st

    def talk_all(self, band, skip=()):
        have = self.objects()
        for n in TOWN_OBJS:
            if L(n) not in have or n in skip or n.startswith("CRATE") or n == "ARC2_INDRA":
                continue
            if n == "TENT_CLERK" and tuple(have[L(n)]) == (566, 643):
                # behind the tent table: talked to across it from (566,645)
                self.warp(TOWN, 566, 645, "DIR_NORTH")
                self.face("N")
                self.press("A", 4)
                self.step(10)
                self.drive(shots={i: f"tent_clerk_{i}" for i in range(1, 6)})
                self.idle_check("talk TENT_CLERK (across the table)")
                continue
            self.talk(n)

    def read_all(self, band, skip=()):
        for name, (tile, facing) in SIGNS.items():
            if name in skip or (name == "hall_door" and band != "D"):
                continue    # (outside band D the door is a warp: facing it walks in; sanctuary() covers it)
            self.read(name, tile, facing)

    def sanctuary(self, band, door=True):
        """Into the hall through the town door, check the band's people, talk to all, read the signs, out by the
        mat."""
        if door:
            self.enter_town(580, 653, "DIR_NORTH")
            self.go("N")
            self.step(60)
            m, p = self.where()
            self.ok(m == SANCT and tuple(p) == (10, 19), f"through the hall door: {m} at {p}")
        else:
            self.warp(SANCT, 10, 19, "DIR_NORTH")
        self.shoot("sanctuary_entrance")
        self.check_band_objects(band, SANCT_OBJS, SANCT_BAND, {})
        have = self.objects()
        for n in SANCT_OBJS:
            if L(n) in have and not (band in "BC" and n == "RECORDS_CLERK"):
                self.talk(n, prefix="sanct_")
                self.warp(SANCT, 10, 19, "DIR_NORTH")
        for name, (tile, facing) in SANCT_SIGNS.items():
            if band in "BC" and (name in OFFICE_SIGNS or name == "back_door"):
                continue    # the office is shut and the back door guarded in B and C
            self.read("sanct_" + name, tile, facing, map_=SANCT)
        if band in "BC":
            self.warp(SANCT, 18, 13, "DIR_EAST")
            self.press("RIGHT", 6)
            self.step(20)
            self.ok(tuple(self.where()[1]) == (18, 13), "the office doorway (19,13) is blocked by the hall grunt")
        elif band != "D":
            self.warp(SANCT, 18, 13, "DIR_EAST")
            self.go("EEN")
            self.ok(tuple(self.where()[1]) == (20, 12), "into the records office through the doorway (19,13)")
            self.shoot("sanctuary_office")
        self.warp(SANCT, 10, 19, "DIR_SOUTH")
        self.press("DOWN", 8)
        for _ in range(40):
            self.step(10)
            if self.where()[0] == TOWN:
                break
        st = self.drive()
        m, p = self.where(st)
        self.ok(m == TOWN and tuple(p) in ((580, 652), (580, 653)), f"out of the hall by the mat: {m} at {p}")
        self.shoot("sanctuary_out")


# ------------------------------------------------------------------------------------------------- scenarios
def scenario_cutaway(t):
    t.setstate(arc2=44, sol=0)
    t.enter_town(560, 641, "DIR_NORTH")
    seen = set()

    def watch(st):
        seen.add(t.var(ARC2, st))
        return False
    t.press("UP", 6)
    t.step(12)
    t.drive(shots={i: f"cutaway_{i}" for i in range(1, 12)}, until=watch)
    st = t.state()
    t.ok(47 in seen and t.var(ARC2, st) == 49, f"cutaway: 47 seen during it ({sorted(v for v in seen if v)}), "
         f"49 after (now {t.var(ARC2, st)})")
    t.ok(tuple(t.where(st)[1]) == (557, 654) and L("ARC2_INDRA") not in t.objects(),
         f"cutaway: player at the wall {t.where(st)[1]}, Indra gone")
    t.read("wall_teo", (557, 656), "W")


def scenario_A(t):
    t.setstate(arc2=50, sol=0)
    t.enter_town()
    t.shoot("town")
    t.check_band_objects("A")
    t.talk_all("A")
    t.read_all("A")
    t.sanctuary("A")
    # wild encounter in the garden of names
    t.warp(TOWN, 565, 650, "DIR_EAST")
    species = None
    for i in range(300):
        t.press("RIGHT" if i % 6 < 3 else "LEFT", 8)     # x 565 <-> 568, all tall grass
        t.step(10)
        st = t.state()
        if st.get("app") != "field":
            for _ in range(60):
                st = t.state()
                bat = (st.get("battle") or {}).get("battlers") or []
                if len(bat) > 1 and bat[1].get("species"):
                    species = (bat[1]["species"], bat[1].get("level"))
                    break
                t.step(20)
            t.shoot("wild_battle")
            t.drive()
            t.after_battle()
            break
    t.ok(species is not None and species[0] in ("SPECIES_YAMASK", "SPECIES_DUSKULL"),
         f"garden of names: wild {species}")
    t.idle_check("after the wild battle")


def scenario_B(t):
    t.setstate(arc2=60, sol=0)
    t.enter_town()
    t.shoot("town")
    t.check_band_objects("B")
    t.talk_all("B")
    t.read_all("B")
    t.sanctuary("B")


def scenario_C(t):
    t.setstate(arc2=90, sol=0)
    t.enter_town()
    t.shoot("town")
    t.check_band_objects("C")
    t.talk_all("C")
    t.read_all("C")
    t.sanctuary("C")


def scenario_D(t):
    t.setstate(arc2=99, sol=0)
    t.enter_town()
    t.shoot("town")
    t.check_band_objects("D")
    t.talk_all("D", skip=("GATE_GRUNT_L",))
    t.read_all("D", skip=("hall_door",))
    # the gate is shut: the left grunt stands on the gate's front tile
    t.warp(TOWN, 580, 660, "DIR_NORTH")
    t.press("UP", 6)
    t.step(20)
    t.ok(tuple(t.where()[1]) == (580, 660), "band D: the gate is blocked by the grunt on (580,659)")
    t.interact(shots={1: "gate_grunt_l_1", 2: "gate_grunt_l_2"})
    t.idle_check("talk GATE_GRUNT_L (outside)")
    # the door: the locked message, no warp
    t.read("hall_door", (580, 653), "N")
    t.press("UP", 8)
    t.step(60)
    m, p = t.where()
    t.ok(m == TOWN and tuple(p) == (580, 653), f"band D: walking into the hall door does not warp ({m} {p})")
    # the hall is empty and exit-only; out by the mat, then the gate grunt lets the player out of the compound
    t.sanctuary("D", door=False)
    t.go("SSSSS")
    r = t.cmd({"cmd": "talk", "localid": L("GATE_GRUNT_L")})
    t.ok(bool(r.get("ok")) and r.get("player", {}).get("z") == 658, f"talk to the gate grunt from inside: {r}")
    t.step(4)
    t.drive(shots={1: "gate_grunt_let_out_1"})
    have = t.objects()
    t.ok(tuple(have.get(L("GATE_GRUNT_L"), ())) == (579, 659), f"the gate grunt stepped aside to {have.get(L('GATE_GRUNT_L'))}")
    t.go("SS")
    t.ok(tuple(t.where()[1]) == (580, 660), "out of the compound")


def scenario_briefing(t):
    t.setstate(arc2=99, sol=10)
    t.enter_town()
    t.check_band_objects("D", extra=("LOOKER", "CYRUS"))
    t.shoot("town_looker_cyrus")
    t.talk("LOOKER", shots=12)
    st = t.state()
    have = t.objects()
    t.ok(t.var(SOL, st) == 20, f"briefing: progress {t.var(SOL, st)} (want 20)")
    t.ok(L("LOOKER") not in have and L("GATE_GRUNT_L") not in have and L("GATE_GRUNT_R") not in have
         and L("LOADING_GRUNT") not in have and tuple(have.get(L("CYRUS"), ())) == (597, 662),
         f"after the briefing: Looker, the gate pair and the loading grunt gone, Cyrus at {have.get(L('CYRUS'))}")
    t.shoot("after_briefing")
    # band R: walk into the dig from the road (the trigger at x 592)
    t.warp(TOWN, 590, 660, "DIR_EAST")
    t.check_band_objects("R", extra=("CYRUS",))
    t.go("E")
    t.go("E", shots={i: f"fence_{i}" for i in range(1, 14)})
    st = t.drive(shots={i: f"fence_more_{i}" for i in range(1, 14)})
    t.after_battle()
    have = t.objects()
    t.ok(tuple(have.get(L("EXCAVATION_GRUNT_M"), ())) == (596, 661)
         and tuple(have.get(L("EXCAVATION_GRUNT_F"), ())) == (597, 660) and L("CYRUS") not in have,
         f"fence: the pair stepped aside (M {have.get(L('EXCAVATION_GRUNT_M'))}, F "
         f"{have.get(L('EXCAVATION_GRUNT_F'))}), Cyrus went in")
    t.shoot("fence_after")
    t.talk("EXCAVATION_GRUNT_M")
    t.talk("EXCAVATION_GRUNT_F")
    # reload: the pair stay aside, no trigger, Cyrus gone
    t.enter_town()
    t.check_band_objects("R")
    have = t.objects()
    t.ok(tuple(have.get(L("EXCAVATION_GRUNT_M"), ())) == (596, 661), "reload: the pair still stand aside")
    t.warp(TOWN, 590, 660, "DIR_EAST")
    t.go("EEEEEN")
    t.ok(tuple(t.where()[1]) == (595, 659), f"the gap is open: at {t.where()[1]}")
    t.go("NNN")
    t.go("N")
    t.step(60)
    m, p = t.where()
    t.ok(m == ROOM1, f"into Ruins Room 1: {m} {p}")
    t.drive(shots={i: f"room1_{i}" for i in range(1, 10)})
    # R townspeople and signs, the Sanctuary with Looker
    t.setstate(sol=20)
    t.enter_town()
    t.talk_all("R", skip=("EXCAVATION_GRUNT_M", "EXCAVATION_GRUNT_F"))
    t.read_all("R")
    t.sanctuary("R")


def scenario_fence_talk(t):
    t.setstate(arc2=99, sol=20)
    t.enter_town()
    t.check_band_objects("R", extra=("CYRUS",))
    t.talk("CYRUS")
    t.near("EXCAVATION_GRUNT_F")
    r = t.cmd({"cmd": "talk", "localid": L("EXCAVATION_GRUNT_F")})
    t.ok(bool(r.get("ok")), f"talk to the fence grunt F: {r}")
    t.step(4)
    t.drive(shots={i: f"fence_talk_{i}" for i in range(1, 14)})
    t.after_battle()
    have = t.objects()
    t.ok(t.battles >= 1 and tuple(have.get(L("EXCAVATION_GRUNT_M"), ())) == (596, 661) and L("CYRUS") not in have,
         f"fence (talk): {t.battles} battles, the pair aside, Cyrus gone")
    t.idle_check("fence (talk)")


def scenario_fence_loss(t):
    """Level 5 party: SOL_07 marked beaten but SOL_08 not (a loss to the second grunt) resets the pair on the next
    load; losing the fence battle is a stock whiteout and the pair stay at the gap."""
    t.losing = True
    t.setstate(arc2=99, sol=20)
    t.cmd({"cmd": "set_flag", "name": BEAT07, "value": True})
    t.enter_town()
    st = t.state()
    t.ok(not t.flag(BEAT07, st) and not t.flag(BEAT08, st), "pair reset: SOL_07's flag cleared on load (08 unbeaten)")
    t.check_band_objects("R", extra=("CYRUS",))
    t.near("EXCAVATION_GRUNT_F")
    r = t.cmd({"cmd": "talk", "localid": L("EXCAVATION_GRUNT_F")})
    t.ok(bool(r.get("ok")), f"talk to the fence grunt F: {r.get('error', 'started')}")
    t.step(4)
    t.drive(shots={i: f"fence_loss_{i}" for i in range(1, 8)})
    t.after_battle()
    st = t.state()
    m, p = t.where(st)
    t.ok(m != TOWN and t.var(SOL, st) == 20 and not t.flag(BEAT07, st),
         f"lost: whited out to {m} {p}, progress {t.var(SOL, st)}, SOL_07 unbeaten")
    t.shoot("whiteout")
    t.enter_town()
    have = t.objects()
    t.ok(tuple(have.get(L("EXCAVATION_GRUNT_M"), ())) == (595, 659) and tuple(have.get(L("CYRUS"), ())) == (597, 662),
         "back in town: the pair at the gap, Cyrus by the fence")


def scenario_E(t):
    t.setstate(arc2=99, sol=50)
    st0 = t.state()
    stones = (st0.get("bag") or {}).get("ITEM_DUSK_STONE", 0)
    t.warp(TOWN, 571, 657, "DIR_NORTH")    # not the landing spot: the scene warps the player to (580,660) first
    # the warp's drive() already ran the seizure scene; check its result
    st = t.state()
    have = t.objects()
    got = (st.get("bag") or {}).get("ITEM_DUSK_STONE", 0)
    t.ok(t.flag("FLAG_SOL_TOWN_A", st) and got == stones + 1,
         f"seizure: FLAG_SOL_TOWN_A {t.flag('FLAG_SOL_TOWN_A', st)}, Dusk Stone {stones} -> {got}")
    t.ok(L("LOOKER") not in have and L("CYRUS") not in have and tuple(t.where(st)[1]) == (580, 660),
         f"seizure: Looker and Cyrus left; the player at {t.where(st)[1]}")
    t.shoot("after_seizure")
    t.enter_town()
    t.ok(t.idle(t.state()) and L("LOOKER") not in t.objects(), "seizure: not replayed on the next load")
    t.check_band_objects("E")
    t.talk_all("E")
    t.read_all("E")
    t.sanctuary("E")


def scenario_seizure_shots(t):
    """The seizure once more from raid-scripts' landing spot (580,660), a screenshot of every box."""
    t.setstate(arc2=99, sol=50)
    r = None
    for _ in range(40):
        r = t.cmd({"cmd": "warp", "map": TOWN, "x": 580, "z": 660, "dir": "DIR_NORTH"})
        if r.get("ok"):
            break
        t.press("A", 6)
        t.step(60)
    t.step(120)
    t.drive(shots={i: f"seizure_{i}" for i in range(1, 20)})
    t.ok(t.flag("FLAG_SOL_TOWN_A"), "seizure (screenshots) played")


def scenario_F(t):
    t.setstate(arc2=99, sol=50, flags=("FLAG_SOL_TOWN_A", "FLAG_GAME_COMPLETED"))
    t.enter_town()
    t.shoot("town")
    t.check_band_objects("F", extra=("ARC2_INDRA",))
    t.talk_all("F")
    t.read_all("F")
    # Indra at the wall, once
    t.talk("ARC2_INDRA", shots=6)
    st = t.state()
    t.ok(t.flag("FLAG_SOL_TOWN_B", st) and L("ARC2_INDRA") not in t.objects(), "Indra at the wall: done, gone")
    t.read("wall_teo_after_indra", (557, 656), "W")
    t.enter_town()
    t.check_band_objects("F")
    t.sanctuary("F")


SCENARIOS = [("cutaway", scenario_cutaway), ("A", scenario_A), ("B", scenario_B), ("C", scenario_C),
             ("D", scenario_D), ("briefing", scenario_briefing), ("fence_talk", scenario_fence_talk),
             ("fence_loss", scenario_fence_loss),
             ("E", scenario_E), ("seizure_shots", scenario_seizure_shots), ("F", scenario_F)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("build_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--only", default="")
    ap.add_argument("--keep-run-dir", action="store_true")
    a = ap.parse_args()
    build_dir = os.path.abspath(a.build_dir)
    os.makedirs(a.out_dir, exist_ok=True)
    town, sanct = screenplay_text.build()
    problems = screenplay_text.check(town + sanct, screenplay_text.load_widths())
    for p in problems:
        print("FAIL text:", p)
    if problems:
        return 1
    print(f"ok   text: {len(town) + len(sanct)} messages, every line <= {screenplay_text.MAX_PX} px, <= 2 lines a box")
    save = make_save(os.path.join(a.out_dir, "town_test_lv100.sav"))
    weak = make_save(os.path.join(a.out_dir, "town_test_lv5.sav"), level=5)
    only = [s for s in a.only.split(",") if s]
    results, shots, failed = [], [], []
    t0 = time.time()
    with open(os.path.join(a.out_dir, "log.txt"), "w") as log:
        for name, fn in SCENARIOS:
            if only and name not in only:
                continue
            run_dir = tempfile.mkdtemp(prefix="dz-town-")
            game = Game(build_dir, run_dir, log)
            t = Town(game, a.out_dir, name, results, shots)
            log.write(f"\n===== {name}\n")
            try:
                t.boot(weak, 5) if name == "fence_loss" else t.boot(save)
                fn(t)
                results.append(f"PASS [{name}]")
                print(results[-1], flush=True)
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
