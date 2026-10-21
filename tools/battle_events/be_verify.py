#!/usr/bin/env python3
"""Headless checks for the battle-events workstream (docs/battle_events.md).

    SDL_VIDEODRIVER=dummy ~/.venvs/desmume39/bin/python tools/battle_events/be_verify.py ROM XMAP OUTDIR \
        --scenario intimidate weather leader lowhp lowhp_trainer crit [--leaders 5] [--tag base]

Scenarios (each boots its own emulator from an offline-edited copy of the critic's Eterna Forest save):
  intimidate     lead Gyarados (Intimidate) vs a wild Gyarados (Intimidate) from the L+R launcher: both banners
  weather        lead Hippowdon (Sand Stream) vs a wild Gyarados: the weather ability's banner and the foe's
  leader         L+R+Y Gym Leader battles (Roark, Gardenia, Maylene, Wake, Fantina) with a Lv100 lead using Surf,
                 to each leader's last Pokemon: the BGM on the sequence player before and after, and Maylene's
                 Hitmontop (Intimidate) sent out against the Gyarados lead
  lowhp          lead at 15% HP in a wild battle (the theme with the low-HP layer): the HINSI beep and the layer
  lowhp_trainer  the same in a Gym Leader battle (a theme without the layer): the beep must stay
  crit           a wild Bidoof, forceCriticalCapture on, a Poke Ball thrown: one shake, the flash and SE
Frames and per-frame state (debug block + sequence players) go to OUTDIR/<scenario>/.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import belib  # noqa: E402
from belib import AudioProbe, EventsDebug, SEQ, SEQ_ID, edit_save  # noqa: E402

import critic  # noqa: E402
from emu import Emu, Frame, contact_sheet, dedupe, top  # noqa: E402

SAVE = belib.ROOT / "tools/battle_stage/emu/saves/eterna_forest_grass.sav"
SPECIES_GYARADOS, SPECIES_HIPPOWDON = 130, 450
ABILITY_INTIMIDATE, ABILITY_SAND_STREAM = 22, 45
MOVE_SURF, MOVE_FALSE_SWIPE, MOVE_SPLASH, MOVE_ENERGY_BALL = 57, 206, 150, 412
LAUNCHER_GYARADOS = 13          # RIGHT presses in the launcher's opponent list
LAUNCHER_BIDOOF = 0
PLAIN_ENTRY = 1                 # DOWN presses: entry 01 Plain + Plain
STRONG = (400, 999, 999, 999, 999, 999)


class Run:
    def __init__(self, rom, xmap, outdir, name, tag):
        self.sc = critic.Scenario(name, pathlib.Path(outdir))
        self.rom, self.xmap, self.tag = rom, xmap, tag
        self.log = []
        self.frames = []

    def start(self, sav):
        self.e = Emu(self.rom, sav)
        self.audio = AudioProbe(self.e, self.xmap)
        self.dbg = EventsDebug(self.e, self.xmap)
        critic.XMAP_PATH = None
        return self.e

    def state(self, label=""):
        d = self.dbg.read()
        st = dict(frame=self.e.frame, label=label, seqs=self.audio.seqs(), bgm=self.audio.bgm())
        if d:
            st.update({k: d[k] for k in d if k != "magic"})
        self.log.append(st)
        return st

    def step(self, n=1, every=2, label="", keep=lambda st: True):
        """Runs n frames, logging state each frame and keeping a frame every `every` frames when keep(st)."""
        for i in range(n):
            self.e.run(1)
            st = self.state(label)
            if i % every == 0 and keep(st):
                self.frames.append(Frame(f"{label} s{','.join(SEQ.get(s, str(s))[8:] for s in st['seqs'])}"
                                         f" p{st.get('popupState0', '-')}{st.get('popupState1', '-')}",
                                         self.e.frame, self.e.screens()))

    def finish(self):
        (self.sc.dir / f"state_{self.tag}.json").write_text(json.dumps(self.log))
        self.e.close()


def launch_wild(r: Run, species_right: int) -> bool:
    e = r.e
    if not critic.boot(r.sc, e):
        return False
    panel = []
    started = critic._qb_start(r.sc, e, "A", PLAIN_ENTRY, species_right, panel, "wild", tod_taps=1)
    return bool(started)


def wait_menu(r: Run, timeout=3000, label="intro", every=2, keep=lambda st: True, advance=False):
    e = r.e
    start = e.frame
    last_b = e.frame
    while e.frame - start < timeout:
        if e.battle_menu_up():
            r.step(10, every, label, keep)
            if e.battle_menu_up():
                return e.frame - start
        if advance and e.frame - last_b >= 30:
            e.tap("B", 0)
            last_b = e.frame
        r.step(4, every, label, keep)
    return None


def popup_on(st):
    return st.get("popupState0", 0) or st.get("popupState1", 0)


def sheet(r: Run, frames, key, title, screen="top", cols=8):
    frames = dedupe(frames, "top", threshold=0.001) if len(frames) > 2 else frames
    if not frames:
        return None
    return r.sc.sheet(frames, f"{key}_{r.tag}", title, screen=screen, cols=cols, scale=1.0 if screen == "top" else 0.5)


# ------------------------------------------------------------------------------------------------ scenarios

def sc_ability(r: Run, lead_species, lead_ability, what):
    sav = r.sc.dir / f"{what}.sav"
    info = edit_save(SAVE, sav, species=lead_species, ability=lead_ability, moves=[MOVE_FALSE_SWIPE, MOVE_SPLASH, 0, 0])
    r.sc.note(f"lead edited offline: {info}")
    r.start(sav)
    if not launch_wild(r, LAUNCHER_GYARADOS):
        return
    waited = wait_menu(r, label="intro", every=2)
    r.sc.check(f"{what}: battle menu reached", waited is not None, f"{waited} frames")
    r.step(150, 2, "menu")
    shows = [st for st in r.log if popup_on(st)]
    d = r.dbg.read()
    if d is not None:
        first = {}
        for st in r.log:
            for side in (0, 1):
                if st.get(f"popupState{side}") and side not in first:
                    first[side] = st
        r.sc.note(f"debug at the menu: {d}")
        for side, name in ((0, "player"), (1, "enemy")):
            ok = d[f"popupShows{side}"] >= 1
            ab = d[f"popupAbility{side}"]
            r.sc.check(f"{what}: {name}-side banner shown", ok,
                       f"shows={d[f'popupShows{side}']} ability={ab} first at frame {first.get(side, {}).get('frame')}")
        # The banner must have left again by the command menu + 150 frames
        r.sc.check(f"{what}: banners gone at the menu", not popup_on(r.log[-1]), f"states {r.log[-1].get('popupState0')}/{r.log[-1].get('popupState1')}")
        r.sc.check(f"{what}: no banner skipped for lack of VRAM/palette", d["popupSkipped"] == 0, f"skipped={d['popupSkipped']}")
        # Timing: slide frames (state 1) per side
        for side in (0, 1):
            states = [st.get(f"popupState{side}", 0) for st in r.log]
            counts = {s: states.count(s) for s in range(1, 6)}
            xs = [st.get(f"popupX{side}") for st in r.log if st.get(f"popupState{side}") == 1]
            r.sc.note(f"side {side}: frames per state (1 slide-in, 2 reveal, 3 flash, 4 hold, 5 slide-out) {counts}; slide-in x {xs}")
    # sheets: all intro frames (deduped), and the frames with a banner
    sheet(r, r.frames, "intro", f"{what}: battle start to the command menu, every 2 frames ({r.tag})")
    on_frames = [f for f in r.frames if not f.label.endswith("p00") and not f.label.endswith("p--")]
    if on_frames:
        sheet(r, on_frames, "banner", f"{what}: frames with a banner up ({r.tag})")
    r.finish()


def sc_totem(r: Run):
    """L+R+X: the Totem battle. The Totem's Pressure line is a PrintGlobalMessage (TAG_GLOBAL_MESSAGE on the tags)."""
    sav = r.sc.dir / "totem.sav"
    edit_save(SAVE, sav, moves=[MOVE_FALSE_SWIPE, MOVE_SPLASH, 0, 0])
    r.start(sav)
    e = r.e
    if not critic.boot(r.sc, e):
        return
    # Totem Spiritomb (Pressure): B steps the Totem choice from Hitmonlee (0) to Spiritomb (2)
    if critic.hold_overlay(e, threshold=0.10) is None:
        r.sc.check("L+R panel", False)
        return
    critic.tap_held(e, "DOWN", PLAIN_ENTRY)
    critic.tap_held(e, "SELECT", 1)
    critic.tap_held(e, "B", 2)
    e.run(4)
    r.frames.append(Frame("panel", e.frame, e.screens()))
    e.hold("X", 6, 0)
    e.release("L+R")
    if not r.sc.check("L+R+X started the Totem battle", e.wait_until(lambda em: not em.in_overworld(), timeout=240, step=4) is not None):
        return
    waited = wait_menu(r, timeout=4000, label="intro", every=2)
    r.sc.check("totem: battle menu reached", waited is not None, f"{waited} frames")
    r.step(60, 2, "menu")
    d = r.dbg.read()
    if d is not None:
        r.sc.note(f"debug at the menu: {d}")
        r.sc.check("totem: enemy-side banner shown (Pressure, a global message)", d["popupShows1"] >= 1,
                   f"shows={d['popupShows1']} ability={d['popupAbility1']}")
    sheet(r, r.frames, "intro", f"totem intro ({r.tag})")
    on_frames = [f for f in r.frames if not f.label.endswith("p00") and not f.label.endswith("p--")]
    if on_frames:
        sheet(r, on_frames, "banner", f"totem: frames with a banner up ({r.tag})")
    r.finish()


def sc_lowhp(r: Run, trainer: bool):
    sav = r.sc.dir / "lowhp.sav"
    stats = STRONG if trainer else None
    info = edit_save(SAVE, sav, hp_frac=0.15, moves=[MOVE_SPLASH, MOVE_FALSE_SWIPE, 0, 0],
                     level=100 if trainer else None, stats=stats)
    r.sc.note(f"lead edited offline: {info}")
    r.start(sav)
    e = r.e
    if trainer:
        if not critic.boot(r.sc, e):
            return
        d = critic.hold_overlay(e, threshold=0.10)
        critic.tap_held(e, "DOWN", PLAIN_ENTRY)
        e.hold("Y", 6, 0)
        e.release("L+R")
    else:
        if not launch_wild(r, LAUNCHER_BIDOOF):
            return
    waited = wait_menu(r, label="intro", every=4, advance=trainer)
    r.sc.check("battle menu reached", waited is not None, f"{waited} frames")
    r.step(240, 6, "menu")
    hinsi = SEQ_ID["SEQ_SE_DP_HINSI"]
    menu_log = [st for st in r.log if st["label"] == "menu"]
    hinsi_frames = sum(1 for st in menu_log if hinsi in st["seqs"])
    bgm = menu_log[-1]["bgm"]
    d = r.dbg.read()
    r.sc.note(f"BGM {bgm} ({SEQ.get(bgm)}); HINSI held by a sequence player on {hinsi_frames}/{len(menu_log)} menu frames; debug {d}")
    r.state("end")
    sheet(r, r.frames[-12:], "menu", f"low HP at the command menu ({r.tag})")
    r.finish()
    return dict(bgm=bgm, hinsi_frames=hinsi_frames, frames=len(menu_log), dbg=d)


def sweep_to_last(r: Run, max_turns=12, slot=0):
    """At the command menu: Surf every turn (B through text and 'switch?' prompts) until the debug block shows
    the leader music switch, or the battle ends. Returns the log index where the switch began."""
    e = r.e
    for turn in range(max_turns):
        if not e.battle_menu_up():
            if wait_menu(r, timeout=2400, label=f"t{turn}", every=6, advance=True) is None:
                return None
        before = r.audio.bgm()
        e.battle_fight(slot)
        # follow the turn with frames every 3 until the next menu
        start = e.frame
        while e.frame - start < 2400:
            r.step(3, 3, f"t{turn}")
            if e.battle_menu_up():
                break
            if e.in_overworld():
                return None
            if (e.frame - start) % 30 == 0:
                e.tap("B", 0)
        st = r.state(f"t{turn}")
        if st.get("leaderBgm"):
            return turn
    return None


def sc_leader(r: Run, leader: int):
    sav = r.sc.dir / "leader.sav"
    info = edit_save(SAVE, sav, species=SPECIES_GYARADOS, ability=ABILITY_INTIMIDATE, level=100, stats=STRONG,
                     moves=[MOVE_SURF, MOVE_ENERGY_BALL, 0, 0])
    r.sc.note(f"lead edited offline: {info}")
    r.start(sav)
    e = r.e
    if not critic.boot(r.sc, e):
        return
    if critic.hold_overlay(e, threshold=0.10) is None:
        r.sc.check("L+R panel", False)
        return
    critic.tap_held(e, "DOWN", PLAIN_ENTRY)
    critic.tap_held(e, "SELECT", 1)
    e.run(4)
    r.frames.append(Frame("panel", e.frame, e.screens()))
    # The leader choice advances after each Y battle; within one boot step it by starting battles? No: B, the
    # totem key, is free to press but does not move it. The panel cycles the leader with each Y battle only, so
    # leader `leader` is reached through sLeaderChoice in RAM: written here before Y, a launcher-only main-RAM byte.
    syms = belib.read_xmap_syms(r.xmap, {"sLeaderChoice"})
    if "sLeaderChoice" in syms and leader:
        e.write(syms["sLeaderChoice"][0], bytes([leader]))
        e.run(2)
    e.hold("Y", 6, 0)
    e.release("L+R")
    left = e.wait_until(lambda em: not em.in_overworld(), timeout=240, step=4)
    if not r.sc.check("L+R+Y started a leader battle", left is not None):
        return
    waited = wait_menu(r, timeout=4000, label="intro", every=4, advance=True)
    r.sc.check("leader battle: menu reached", waited is not None, f"{waited} frames")
    st = r.state("menu0")
    r.sc.note(f"first menu: BGM {st['bgm']} ({SEQ.get(st['bgm'])}), debug popups {st.get('popupShows0')}/{st.get('popupShows1')}")
    turn = sweep_to_last(r, slot=1 if leader == 3 else 0)   # Wake's Quagsire absorbs Surf: Energy Ball
    # let the music switch finish and record
    r.step(120, 4, "after")
    end = r.state("end")
    sw = [st for st in r.log if st.get("leaderBgm")]
    bgms = []
    for st in r.log:
        if st["bgm"] is not None and (not bgms or bgms[-1][1] != st["bgm"]):
            bgms.append((st["frame"], st["bgm"]))
    r.sc.note("BGM on player 0 over the battle: " + ", ".join(f"@{f} {SEQ.get(b, b)}" for f, b in bgms))
    r.sc.check("leader music switched to SEQ_BATTLE_FRONTIER_BRAIN at the last Pokemon",
               end["bgm"] == SEQ_ID["SEQ_BATTLE_FRONTIER_BRAIN"],
               f"turn {turn}; BGM now {SEQ.get(end['bgm'], end['bgm'])}; trigger msg {end.get('leaderBgmTrainerMsg')}")
    sheet(r, [f for f in r.frames if f.label.startswith(("intro", "panel"))], "intro", f"leader {leader}: intro ({r.tag})")
    if sw:
        at = sw[0]["frame"]
        win = [f for f in r.frames if at - 300 <= f.frame <= at + 120]
        sheet(r, win, "switch", f"leader {leader}: the last-Pokemon line and the music switch at @{at} ({r.tag})")
    sheet(r, r.frames[-60:], "last", f"leader {leader}: last turns ({r.tag})")
    r.finish()
    return dict(turn=turn, bgms=bgms, end=end)


def throw_ball(r: Run):
    """Command menu -> BAG -> Poke Balls pocket -> first ball -> USE. Coordinates from the battle bag layout
    (src/battle_sub_menus/battle_bag_buttons.c)."""
    e = r.e
    e.touch(*critic.BTN_BAG if hasattr(critic, "BTN_BAG") else (40, 172), after=60)
    r.frames.append(Frame("bag", e.frame, e.screens()))
    e.touch(192, 60, after=50)       # POKe BALLS pocket (top right of the four)
    r.frames.append(Frame("balls", e.frame, e.screens()))
    e.touch(64, 32, after=50)        # first entry
    r.frames.append(Frame("ball", e.frame, e.screens()))
    e.touch(120, 172, after=10)      # USE
    r.frames.append(Frame("use", e.frame, e.screens()))


def sc_crit(r: Run, force: int):
    sav = r.sc.dir / "crit.sav"
    info = edit_save(SAVE, sav, moves=[MOVE_FALSE_SWIPE, MOVE_SPLASH, 0, 0])
    r.start(sav)
    e = r.e
    if not launch_wild(r, LAUNCHER_BIDOOF):
        return
    waited = wait_menu(r, label="intro", every=8)
    r.sc.check("battle menu reached", waited is not None, f"{waited} frames")
    forced = r.dbg.force_critical(force)
    r.sc.note(f"forceCriticalCapture={force} written: {forced}")
    throw_ball(r)
    start = e.frame
    r.frames = r.frames[-4:]
    r.step(700, 2, "throw")
    end = r.state("end")
    r.sc.note(f"after the throw: {({k: end.get(k) for k in ('lastCaptureCritical', 'lastCaptureShakes', 'criticalCaptures', 'lastCriticalThreshold', 'dexCaught', 'criticalFlashes')})}")
    sheet(r, r.frames, "throw", f"capture, force={force} ({r.tag})", screen="top", cols=10)
    r.finish()
    return end


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom")
    ap.add_argument("xmap")
    ap.add_argument("out")
    ap.add_argument("--scenario", nargs="+", default=["intimidate"])
    ap.add_argument("--tag", default="ours")
    ap.add_argument("--leaders", default="0,1,2,3,4")
    ap.add_argument("--force", type=int, default=1)
    a = ap.parse_args()
    results = {}
    for name in a.scenario:
        t = time.time()
        r = Run(a.rom, a.xmap, a.out, name, a.tag)
        print(f"== {name} ({a.tag})", flush=True)
        try:
            if name == "intimidate":
                results[name] = sc_ability(r, SPECIES_GYARADOS, ABILITY_INTIMIDATE, "intimidate")
            elif name == "weather":
                results[name] = sc_ability(r, SPECIES_HIPPOWDON, ABILITY_SAND_STREAM, "weather")
            elif name == "totem":
                results[name] = sc_totem(r)
            elif name == "lowhp":
                results[name] = sc_lowhp(r, False)
            elif name == "lowhp_trainer":
                results[name] = sc_lowhp(r, True)
            elif name == "crit":
                results[name] = sc_crit(r, a.force)
            elif name == "leader":
                out = {}
                for i in [int(x) for x in a.leaders.split(",")]:
                    rr = Run(a.rom, a.xmap, a.out, f"leader{i}", a.tag)
                    try:
                        out[i] = sc_leader(rr, i)
                    finally:
                        try:
                            rr.e.close()
                        except Exception:
                            pass
                    json.dump(rr.sc.dump(), open(rr.sc.dir / f"result_{a.tag}.json", "w"), indent=1, default=str)
                results[name] = out
        finally:
            try:
                r.e.close()
            except Exception:
                pass
        r.sc.seconds = time.time() - t
        json.dump(r.sc.dump(), open(r.sc.dir / f"result_{a.tag}.json", "w"), indent=1, default=str)
    json.dump(results, open(pathlib.Path(a.out) / f"results_{a.tag}.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
