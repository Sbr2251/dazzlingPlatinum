#!/usr/bin/env python3
"""Emulator critic: plays scripted scenarios on a ROM and writes frames, contact
sheets and a report for a (vision-capable) reviewer.

    SDL_VIDEODRIVER=dummy ~/.venvs/desmume39/bin/python tools/battle_stage/emu/critic.py \\
        out/dazzlingPlatinum.nds /tmp/bs_critic [--scenario boot wild_battle ...]

Every scenario boots a fresh emulator from saves/eterna_forest_grass.sav (a
unique temp copy of the ROM each time) and records checks as PASS / WARN / FAIL.
Output layout:

    <outdir>/report.md            summary + per-scenario checks + sheet paths
    <outdir>/report.json          the same, machine readable
    <outdir>/<scenario>/sheet_*.png   labelled contact sheets ("label @frame")
    <outdir>/<scenario>/frames/<sheet>/NNNNNN_label.png   the frames in each sheet

Exit status is 1 if any check FAILed. See README.md for what each scenario does.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import struct
import subprocess
import sys
import threading
import time
import traceback
from typing import Callable, Dict, List, Optional

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from emu import (  # noqa: E402
    BTN_BAG, BTN_CANCEL, BTN_FIGHT, BTN_MEGA, BTN_POKEMON, LAYER_BG0, LAYERS_2D, MOVE_SLOTS, RAM_BASE, RAM_END,
    Emu, Frame, bottom,
    contact_sheet, dedupe, diff_fraction, looks_broken, marker_fraction, mean_brightness, read_xmap, screen_health,
    top,
)
from PIL import Image, ImageChops, ImageDraw  # noqa: E402

DEFAULT_SAV = HERE / "saves" / "eterna_forest_grass.sav"
MOVE_ID_POUND = 1
FALSE_SWIPE_SLOT = 3                   # the committed save's lead has False Swipe here (never KOs)
MOVE_ID_MAX = 473                      # move tester wraps within 1..473
QB_ENTRIES = 31                        # quick-battle background entries 0..30
BAG_POCKET_HP = (64, 40)               # battle bag: HP/PP RESTORE pocket (bottom-screen coords)

# The top-screen message window (field message box / battle text box) where both
# debug overlays draw their two lines.
TEXT_BOX = (8, 146, 248, 190)

DEFAULT_MOVES = [
    1,    # Pound          - contact baseline
    52,   # Ember          - small particle projectile
    53,   # Flamethrower   - particle stream
    57,   # Surf           - full-screen wave / background
    85,   # Thunderbolt    - flashes, palette effects
    89,   # Earthquake     - screen shake
    94,   # Psychic        - background swap + wobble
    104,  # Double Team    - sprite duplication
    144,  # Transform      - sprite swap
    164,  # Substitute     - sprite replacement
    326,  # Extrasensory
    332,  # Aerial Ace
    399,  # Dark Pulse
    63,   # Hyper Beam     - big beam + recharge visuals
]
# Moves that hide, shrink, replace or swap a battler's sprite (chunk 3: the sprite mesh must follow them
# and come back). move_tester plays them after --moves (--sprite-moves) and checks the normal look returns.
SPRITE_MOVES = [
    107,  # Minimize       - sprite scale
    91,   # Dig            - attacker hides underground
    19,   # Fly            - attacker leaves the screen
    164,  # Substitute     - sprite replaced by the doll
    144,  # Transform      - sprite swap
]
# Sprite moves whose look lasts after the animation in a real battle (the doll until it breaks, the
# copied look until the switch): the move tester leaves it on screen, so "normal look restored" only WARNs.
LASTING_MOVES = {164: "the Substitute doll", 144: "the Transform look"}


# --------------------------------------------------------------------------- result bookkeeping

class Scenario:
    def __init__(self, name: str, outdir: pathlib.Path):
        self.name = name
        self.dir = outdir / name
        self.dir.mkdir(parents=True, exist_ok=True)
        self.checks: List[dict] = []
        self.sheets: List[dict] = []
        self.notes: List[str] = []
        self.seconds = 0.0
        self.frames_emulated = 0

    def check(self, name: str, ok: bool, detail: str = "", warn_only: bool = False, why: str = "") -> bool:
        """Records a check. `why` is only reported when the check does not pass."""
        status = "PASS" if ok else ("WARN" if warn_only else "FAIL")
        if not ok and why:
            detail = f"{detail}; {why}" if detail else why
        self.checks.append({"check": name, "status": status, "detail": detail})
        print(f"  [{status}] {name}{': ' + detail if detail else ''}", flush=True)
        return ok

    def warn(self, name: str, detail: str) -> None:
        self.check(name, False, detail, warn_only=True)

    def grade(self, name: str, status: str, detail: str = "", why: str = "") -> bool:
        """Records a check whose PASS / WARN / FAIL was decided by the caller."""
        return self.check(name, status == "PASS", detail, warn_only=status == "WARN", why=why)

    def note(self, msg: str) -> None:
        self.notes.append(msg)
        print(f"  note: {msg}", flush=True)

    def dump(self) -> dict:
        return {"name": self.name, "status": self.status, "seconds": round(self.seconds, 1),
                "frames": self.frames_emulated, "checks": self.checks, "notes": self.notes, "sheets": self.sheets}

    def load(self, d: dict) -> None:
        self.checks, self.notes, self.sheets = d["checks"], d["notes"], d["sheets"]
        self.seconds, self.frames_emulated = d["seconds"], d["frames"]

    @property
    def status(self) -> str:
        st = {c["status"] for c in self.checks}
        return "FAIL" if "FAIL" in st else ("WARN" if "WARN" in st else "PASS")

    def sheet(self, frames: List[Frame], key: str, title: str, screen: str = "both",
              dedupe_screen: Optional[str] = None, cols: int = 8, scale: float = 0.5,
              save_frames: bool = True) -> Optional[str]:
        """Writes sheet_<key>.png (and the frames) and registers it for the report."""
        if dedupe_screen:
            frames = dedupe(frames, dedupe_screen)
        if not frames:
            return None
        path = contact_sheet(frames, self.dir / f"sheet_{key}.png", f"{self.name}: {title}",
                             screen=screen, cols=cols, scale=scale)
        if save_frames:
            fdir = self.dir / "frames" / key
            fdir.mkdir(parents=True, exist_ok=True)
            for f in frames:
                safe = re.sub(r"[^A-Za-z0-9_.+-]", "_", f.label)[:40]
                f.img.save(fdir / f"{f.frame:06d}_{safe}.png")
        self.sheets.append({"sheet": str(path), "title": title, "frames": len(frames), "screen": screen})
        return path


# --------------------------------------------------------------------------- shared steps

def text_box(img: Image.Image) -> Image.Image:
    return img.crop(TEXT_BOX)


def health_detail(img: Image.Image) -> str:
    t, b = screen_health(top(img)), screen_health(bottom(img))
    return f"top {t}, bottom {b}"


def check_screens(sc: Scenario, img: Image.Image, what: str, bottom_too: bool = True) -> bool:
    problems = []
    for name, crop in (("top", top), ("bottom", bottom)) if bottom_too else (("top", top),):
        why = looks_broken(crop(img))
        if why:
            problems.append(f"{name}: {why}")
    return sc.check(f"{what}: screens not black/garbage", not problems,
                    "; ".join(problems) or health_detail(img))


def noisy_frames(frames: List[Frame], screen=top, noise_max: float = 45.0) -> List[str]:
    out = []
    for f in frames:
        h = screen_health(screen(f.img))
        if h["noise"] > noise_max:
            out.append(f"{f.label}@{f.frame} (noise {h['noise']})")
    return out


# (address of sDebugClockHour in src/rtc.c, hour) set by run_in_process from --clock-hour and the xMAP
CLOCK_PIN: Optional[tuple] = None


def boot(sc: Scenario, e: Emu, frames: Optional[list] = None) -> bool:
    t = time.time()
    ok = e.boot(into=frames)
    sc.check("booted to overworld", ok, f"{e.frame} frames, {time.time() - t:.1f}s"
             if ok else "Poketch never appeared on the bottom screen")
    if ok and CLOCK_PIN:
        # The game re-reads the RTC every 11 frames and applies the pinned hour then
        e.write(CLOCK_PIN[0], bytes([CLOCK_PIN[1]]))
        e.run(24)
        sc.note(f"clock pinned to {CLOCK_PIN[1]:02d}:xx (sDebugClockHour at {CLOCK_PIN[0]:#x})")
    return ok


def enter_wild_battle(sc: Scenario, e: Emu, intro: Optional[list] = None) -> bool:
    steps = e.walk_until_battle(max_steps=300)
    if not sc.check("wild encounter", steps is not None,
                    f"after {steps} steps in the grass" if steps else "no encounter after 300 steps"):
        return False
    waited = e.wait_battle_menu(timeout=2400, snap_every=8 if intro is not None else 0, label="intro", into=intro)
    return sc.check("battle menu reached", waited is not None,
                    f"{waited} frames after the encounter" if waited is not None
                    else "command menu (red FIGHT button) never appeared")


def run_away(sc: Scenario, e: Emu, frames: Optional[list] = None) -> bool:
    ok = e.battle_run(timeout=2400, into=frames)
    if frames is not None:
        e.record(60, every=15, label="field", into=frames)
    if sc.check("returned to overworld", ok, why="still not in the field after RUN/B for 2400 frames"):
        check_screens(sc, e.screens(), "after battle")
        sc.check("overworld not frozen", e.is_alive(frames=120, every=20, region="top") or _turn_changes(e),
                 why="top screen static for 120 frames and turning did not change it")
    return ok


def _turn_changes(e: Emu) -> bool:
    before = top(e.screens())
    for key in ("LEFT", "RIGHT"):
        e.hold(key, 3, 20)                   # a short press only turns the player in place
        if diff_fraction(before, top(e.screens()), threshold=16) > 0.001:
            return True
    return False


def idle_samples(e: Emu, n: int = 12, every: int = 5) -> List[Image.Image]:
    """Top-screen samples across the command-menu idle bob, to compare a later frame against."""
    out = []
    for _ in range(n):
        out.append(top(e.screens()))
        e.run(every)
    return out


def min_diff(samples: List[Image.Image], img: Image.Image) -> float:
    return min(diff_fraction(s, img) for s in samples)


def hold_overlay(e: Emu, tries: int = 4, threshold: float = 0.03) -> Optional[float]:
    """Presses L+R (and keeps them held) until the top text box changes. Returns the diff or None.
    On None, L+R have been released again."""
    for i in range(tries):
        base = e.screens()
        e.press("L+R")
        e.run(12)
        d = diff_fraction(text_box(base), text_box(e.screens()))
        if d > threshold:
            return d
        e.release("L+R")
        e.run(60 if i else 10)               # an animation may still be swallowing input
    return None


# Move tester overlay, line 2 minus the trailing ON/OFF: "A/Y play  SELECT 3D stage".
# It is the same for every move, so it tells "overlay up" apart from the battle text.
OVERLAY_KEY = (14, 168, 146, 184)
# Top-screen HUD (enemy / player healthbar boxes): hidden by many animations, so masked
# out when deciding whether an animation drew anything.
HUD_BOXES = [(0, 18, 128, 58), (136, 92, 256, 146)]
SCENE = (0, 0, 256, 144)                 # top screen above the text box


def scene(img: Image.Image) -> Image.Image:
    out = top(img).crop(SCENE)
    for box in HUD_BOXES:
        out.paste((0, 0, 0), box)
    return out


class Overlay:
    """The in-battle move tester overlay (hold L+R at the command menu). While an animation
    plays the overlay stays up and the command menu ignores input; once it ends with L+R
    released the overlay is hidden and the original battle text restored."""

    def __init__(self, e: Emu):
        self.e = e
        self.key: Optional[Image.Image] = None

    def up(self, img: Optional[Image.Image] = None) -> bool:
        if self.key is None:
            return False
        img = img if img is not None else self.e.screens()
        return diff_fraction(self.key, img.crop(OVERLAY_KEY)) < 0.03

    def show(self, tries: int = 4) -> bool:
        """Presses (and keeps holding) L+R until the overlay is up. False if it never comes."""
        if self.key is None:
            if hold_overlay(self.e, tries=tries) is None:
                return False
            self.e.run(4)
            self.key = self.e.screens().crop(OVERLAY_KEY)
            return True
        for _ in range(tries):
            self.e.press("L+R")
            if self.e.wait_until(lambda em: self.up(), timeout=30, step=2) is not None:
                return True
            self.e.release("L+R")
            self.e.run(60)
        return False

    def play(self, key: str, frames: int, label: str) -> tuple:
        """With the overlay up: taps A/Y, releases L+R and records every 3 frames until the
        overlay goes away (the animation ended). Returns (frames, finished_after or None)."""
        start = self.e.frame
        self.e.hold(key, 6, 0)
        self.e.release("L+R")
        anim = self.e.record(frames, every=3, label=label, stop=lambda em: not self.up(), min_frames=12)
        return anim, (self.e.frame - start if not self.up() else None)


def menu_responds(e: Emu) -> bool:
    """True if touching FIGHT opens the move list (then CANCELs back). The red FIGHT button
    alone proves nothing: a soft-locked command menu keeps drawing it."""
    e.touch(*BTN_FIGHT, after=40)
    if not e.move_list_up():
        return False
    e.touch(*BTN_CANCEL, after=60)
    return True


def froze(sc: Scenario, e: Emu, frames: List[Frame], what: str) -> bool:
    """FAILs and returns True if the game stopped drawing: the recorded frames never changed
    and the top screen stays static for another 120 frames (the menu idle bob is gone)."""
    if len(dedupe(frames, "both", threshold=0.0005)) > 1 or e.is_alive(frames=120, every=15, region="top"):
        return False
    sc.check(f"{what}: game still running", False,
             f"no pixel changed for {len(frames) * 3 + 120} frames after {what}: the game froze "
             "(see the emulator log check for a CPU exception). Stopping this scenario.")
    return True


def tap_held(e: Emu, key: str, n: int = 1, press: int = 6, gap: int = 4) -> None:
    """Taps `key` n times while other keys (L+R) stay held: a 6-frame tap is one step."""
    for _ in range(n):
        e.hold(key, press, gap)


# --------------------------------------------------------------------------- scenarios

def sc_boot(sc: Scenario, e: Emu, args) -> None:
    frames: List[Frame] = []
    if not boot(sc, e, frames):
        sc.sheet(frames, "boot", "boot attempt (failed)")
        return
    img = e.screens()
    check_screens(sc, img, "overworld")
    alive = e.is_alive(frames=120, every=20, region="top")
    turned = _turn_changes(e)
    e.snap("after turn", frames)
    sc.check("overworld responds (not frozen)", alive or turned,
             f"idle motion={alive}, turning changed the screen={turned}")
    sc.sheet(frames, "boot", "title -> Continue -> overworld")


def sc_wild_battle(sc: Scenario, e: Emu, args) -> None:
    if not boot(sc, e):
        return
    intro: List[Frame] = []
    e.snap("field", intro)
    ok = enter_wild_battle(sc, e, intro)
    e.snap("menu", intro)
    sc.sheet(intro, "1_intro", "encounter -> intro -> command menu (every ~8 frames)", dedupe_screen="both")
    bad = noisy_frames(intro)
    if bad:
        sc.warn("intro frames look sane", f"{len(bad)} noisy top frames: {', '.join(bad[:6])}")
    if not ok:
        return
    check_screens(sc, e.screens(), "command menu")
    sc.check("battle not frozen at the menu", e.is_alive(frames=120, every=15, region="top"),
             why="top screen did not change for 120 frames at the command menu")

    # Damaging move, every 3 frames until the menu comes back.
    if not sc.check("FIGHT opened the move list", e.battle_fight(FALSE_SWIPE_SLOT),
                    f"used move slot {FALSE_SWIPE_SLOT} (False Swipe on the committed save)"):
        e.touch(128, 176, after=30)
    else:
        anim = e.record(args.max_anim_frames, every=3, label="move",
                        stop=lambda em: em.battle_menu_up(), min_frames=60)
        distinct = len(dedupe(anim, "top"))
        sc.sheet(anim, "2_move", "FIGHT -> move + enemy turn, every 3 frames (deduped)",
                 screen="top", dedupe_screen="top")
        sc.check("move animation played", distinct >= 10, f"{distinct} distinct top frames over {len(anim) * 3} frames")
        bad = noisy_frames(anim)
        if bad:
            sc.warn("move frames look sane", f"{len(bad)} noisy top frames: {', '.join(bad[:6])}")
        if not sc.check("menu returned after the turn", e.battle_menu_up(),
                        why=f"no command menu within {args.max_anim_frames} frames"):
            e.wait_battle_menu(timeout=1800, advance_text=True)

    # Bag round trip: the bag swaps VRAM; the battle scene must come back identical.
    bag: List[Frame] = []
    if e.battle_menu_up():
        _sprite_flags(sc, e, args, FREEZE_IDLE)   # compared against idle frames below
        before = idle_samples(e)
        e.snap("before bag", bag)
        opened = e.battle_open_bag()
        e.snap("bag", bag)
        e.touch(*BAG_POCKET_HP, after=60)
        e.snap("bag pocket", bag)
        sc.check("bag opened", opened, "bottom screen changed to the bag" if opened else "bag did not open")
        closed = e.battle_close_bag()
        e.run(20)
        after = e.snap("after bag", bag)
        sc.check("bag closed back to the menu", closed)
        d = min_diff(before, top(after.img))
        detail = f"{d:.2%} of top pixels differ from the closest pre-bag idle frame"
        if d > 0.02:
            diff = ImageChops.difference(before[0].convert("RGB"), top(after.img).convert("RGB"))
            p = sc.dir / "bag_top_diff.png"
            diff.point(lambda v: min(255, v * 4)).save(p)
            detail += f" (diff image {p})"
        if d <= 0.02:
            sc.check("battle scene intact after bag (VRAM)", True, detail)
        else:
            sc.check("battle scene intact after bag (VRAM)", False, detail, warn_only=d <= 0.08)
        check_screens(sc, after.img, "after bag")
        sc.sheet(bag, "3_bag", "command menu -> bag -> pocket -> back")

    ret: List[Frame] = []
    e.snap("before run", ret)
    run_away(sc, e, ret)
    sc.sheet(ret, "4_run", "RUN -> overworld")


# ---- debug combos (chunk 0) ------------------------------------------------------------------

def _no_combo(sc: Scenario, what: str, feature: str) -> None:
    sc.check(what, False, f"holding L+R changed nothing in the top message box: {feature} is not in this ROM "
             "(or the save uses the 'L=A' button mode). Skipping the rest of this scenario.")


def _qb_start(sc: Scenario, e: Emu, key: str, entries_down: int, species_right: int, panel: List[Frame],
              label: str, tod_taps: int = 0) -> Optional[bool]:
    """Opens the quick-battle panel, moves the selectors (entries_down < 0 = UP; tod_taps SELECTs step
    the time of day, see TODS), presses `key` (A/X).
    True if a battle started, False if not, None if the panel never opened."""
    d = hold_overlay(e, threshold=0.10)
    if d is None:
        _no_combo(sc, f"{label}: L+R panel opened", "the overworld quick-battle panel")
        return None
    e.snap(f"{label} panel", panel)
    tap_held(e, "SELECT", tod_taps)
    before = text_box(e.screens())
    tap_held(e, "DOWN" if entries_down >= 0 else "UP", abs(entries_down))
    tap_held(e, "RIGHT", species_right)
    e.run(4)
    e.snap(f"{label} selected", panel)
    if entries_down or species_right:
        # The panel is static, so an unchanged box diffs at 0.0. Changing only a digit or two
        # ("07/29 Indoors 1" -> "08/29 Indoors 2") touches ~0.25% of the box, under 1%.
        changed = diff_fraction(before, text_box(e.screens())) > 0.001
        sc.check(f"{label}: panel responds to the d-pad", changed,
                 f"{'DOWN' if entries_down >= 0 else 'UP'} x{abs(entries_down)}, RIGHT x{species_right}" + ("" if changed else " did not change the panel text"),
                 warn_only=True)
    e.hold(key, 6, 0)
    e.release("L+R")
    left = e.wait_until(lambda em: not em.in_overworld(), timeout=240, step=4)
    return sc.check(f"{label}: L+R+{key} started a battle", left is not None,
                    f"field left after {left} frames" if left is not None else
                    "still in the overworld 240 frames after the combo")


def sc_quick_battle(sc: Scenario, e: Emu, args) -> None:
    if not boot(sc, e):
        return
    panel: List[Frame] = []
    current = 0
    for n, bg in enumerate(args.bgs if args.bgs is not None else [0, 1, 29]):
        label = f"bg{bg:02d}"
        steps = (bg - current) % QB_ENTRIES                # DOWN = +1, UP = -1, both wrap
        if steps > QB_ENTRIES // 2:
            steps -= QB_ENTRIES
        species = args.species_steps if n == 0 else 0
        started = _qb_start(sc, e, "A", steps, species, panel, label)
        if started is None:                                  # no panel at all: feature missing
            break
        current = bg
        if not started:
            e.run(60)
            if not e.in_overworld():
                e.battle_escape()
                continue
            # Tell a hung game and a half-run transition apart here; otherwise the next entry
            # misreports either one as "panel not in this ROM".
            responds = _turn_changes(e)
            e.snap(f"{label} after failed combo", panel)
            if not sc.check(f"{label}: overworld still takes input after the failed combo", responds,
                            "the player turns" if responds else
                            "the player no longer turns: the game hung or a field task is stuck. Stopping here."):
                break
            reopened = hold_overlay(e, threshold=0.10) is not None
            e.snap(f"{label} panel reopened", panel)
            e.release("L+R")
            e.run(10)
            if not sc.check(f"{label}: L+R panel reopens after the failed combo", reopened,
                            "the panel is back" if reopened else
                            "holding L+R no longer shows the panel: the failed transition left the field "
                            "display broken (e.g. BG layers off). Stopping here."):
                break
            continue
        intro: List[Frame] = []
        waited = e.wait_battle_menu(timeout=2400, snap_every=8, label="intro", into=intro)
        e.snap("menu", intro)
        ok = sc.check(f"{label}: battle menu reached", waited is not None,
                      f"{waited} frames" if waited is not None else "no command menu within 2400 frames")
        if ok:
            check_screens(sc, e.screens(), f"{label} menu")
            sc.check(f"{label}: battle not frozen", e.is_alive(frames=120, every=15))
            e.record(120, every=10, label="idle", into=intro)
        sc.sheet(intro, f"{label}_intro", f"quick battle, background entry {bg}: transition -> intro -> menu",
                 dedupe_screen="both")
        if not run_away(sc, e):
            break
    sc.sheet(panel, "panel", "L+R panel before each battle (top screen)", screen="top", cols=4, scale=1.0)


def sc_totem_battle(sc: Scenario, e: Emu, args) -> None:
    if not boot(sc, e):
        return
    panel: List[Frame] = []
    if not _qb_start(sc, e, "X", 0, 0, panel, "totem"):
        sc.sheet(panel, "panel", "L+R panel", screen="top", cols=4, scale=1.0)
        return
    intro: List[Frame] = []
    waited = e.wait_battle_menu(timeout=3000, snap_every=4, label="intro", into=intro)
    e.snap("menu" if waited is not None else "timeout", intro)
    sc.check("totem: battle menu reached", waited is not None,
             f"{waited} frames" if waited is not None else "no command menu within 3000 frames", warn_only=True)
    check_screens(sc, e.screens(), "totem battle")
    sc.sheet(intro, "intro", "Totem cut-in -> intro -> menu (every 4 frames, deduped)", dedupe_screen="both")
    sc.sheet(panel, "panel", "L+R panel", screen="top", cols=4, scale=1.0)
    sc.note("Totem battles cannot be fled; the scenario ends in battle.")


def sc_debug_party(sc: Scenario, e: Emu, args) -> None:
    if not boot(sc, e):
        return
    from make_save import PARTY_OFFSET, PK4_PARTY_SIZE, newest_partition
    raw = pathlib.Path(args.sav).read_bytes()
    base = newest_partition(raw)
    try:
        e.find_party(raw[base + PARTY_OFFSET:base + PARTY_OFFSET + PK4_PARTY_SIZE])
        before = e.party_species()
    except RuntimeError as exc:
        before = None
        sc.warn("party located in RAM", str(exc))
    panel: List[Frame] = []
    if hold_overlay(e, threshold=0.10) is None:
        _no_combo(sc, "L+R panel opened", "the overworld quick-battle panel")
        return
    e.snap("panel", panel)
    e.hold("START", 6, 20)
    e.snap("after START", panel)
    e.release("L+R")
    e.run(30)
    e.snap("released", panel)
    sc.sheet(panel, "panel", "L+R + START (top screen)", screen="top", cols=3, scale=1.0)
    if before is not None:
        after = e.party_species()
        sc.note(f"party before: {[(p['species'], p['level'], p['item']) for p in before]}")
        sc.note(f"party after:  {[(p['species'], p['level'], p['item']) for p in after]}")
        sc.check("debug party given", after != before, "party unchanged after L+R+START" if after == before
                 else f"new/changed: {[p for p in after if p not in before]}")
    sc.check("still in the overworld", e.in_overworld())


def _battle_ready(sc: Scenario, e: Emu) -> bool:
    return boot(sc, e) and enter_wild_battle(sc, e)


def _nav_move(e: Emu, cur: int, target: int) -> None:
    delta = target - cur
    tens, ones = int(delta / 10), delta - 10 * int(delta / 10)
    tap_held(e, "UP" if tens > 0 else "DOWN", abs(tens))
    tap_held(e, "RIGHT" if ones > 0 else "LEFT", abs(ones))
    e.run(4)


def _fight_turn(sc: Scenario, e: Emu, args, what: str) -> bool:
    """Uses False Swipe and waits for the turn (ours and the enemy's) to play out. Returns True
    once the command menu is back. After the move tester this proves the battle still runs a
    real turn: the tester swaps the trainer AI overlay out for the animation overlay and back,
    and a wrong swap only shows up when the turn ends and the battle swaps them itself."""
    if not sc.check(f"{what}: FIGHT opened the move list", e.battle_fight(FALSE_SWIPE_SLOT),
                    why="touching FIGHT did not open the move list: the command menu is soft-locked"):
        return False
    anim = e.record(args.max_anim_frames, every=3, label="fight", stop=lambda em: em.battle_menu_up(), min_frames=60)
    distinct = len(dedupe(anim, "top"))
    sc.sheet(anim, what.replace(" ", "_"), f"{what}: FIGHT -> False Swipe + enemy turn, every 3 frames (deduped)",
             screen="top", dedupe_screen="top")
    sc.check(f"{what}: move animation played", distinct >= 10, f"{distinct} distinct top frames over {len(anim) * 3} frames")
    return sc.check(f"{what}: menu returned after the turn", e.battle_menu_up(),
                    why=f"no command menu within {args.max_anim_frames} frames of picking the move")


def _tester_move(sc: Scenario, e: Emu, args, ov: "Overlay", baseline: tuple, cur: int, mid: int,
                 direction: str, key: str, tag: str, overlays: List[Frame], after: List[Frame],
                 restore: bool = False) -> bool:
    """Picks move `mid` in the tester (currently on `cur`), plays it with `key` and checks that it
    drew, ended and gave the battle text back (with `restore`, also the scene: see restore_check).
    Returns False if the battle is stuck."""
    idle, base_boxes = baseline
    if not ov.up() and not ov.show():
        sc.check(f"{tag}: overlay shown", False, "holding L+R did not bring the overlay back")
        return True
    _nav_move(e, cur, mid)
    e.snap(f"overlay {mid:03d}", overlays)
    anim, done = ov.play(key, args.anim_frames, f"{mid:03d}{direction}")
    if froze(sc, e, anim, f"playing move {mid} with L+R+{key}"):
        sc.sheet(anim[:1] + [e.snap("frozen")], f"{tag.replace(' ', '_')}_frozen",
                 f"move {mid}: frozen screen", scale=1.0)
        return False
    change = max((min_diff(idle, scene(f.img)) for f in anim), default=0.0)
    sc.check(f"{tag} ({key}): animation drew something", change > 0.003,
             f"up to {change:.1%} of the scene (HUD masked) differs from idle, "
             f"{len(dedupe(anim, 'top'))} distinct frames",
             why="nothing moved on screen while the tester said an animation was playing")
    bad = noisy_frames(anim)
    if bad:
        sc.warn(f"{tag}: frames look sane", f"{len(bad)} noisy: {', '.join(bad[:4])}")
    sc.sheet(anim, tag.replace(" ", "_"),
             f"{tag}: {'player->enemy' if key == 'A' else 'enemy->player'}, every 3 frames (deduped)",
             screen="top", dedupe_screen="top")
    if not sc.check(f"{tag}: animation finished", done is not None,
                    f"overlay hidden {done} frames after L+R+{key}" if done is not None else
                    f"overlay still up {len(anim) * 3} frames after L+R+{key}: the animation never "
                    "ended, so the command menu keeps ignoring input"):
        return False
    # The text comes back first; a broken state can garble it a few dozen frames later.
    e.run(10)
    e.snap(f"{tag} +10", after)
    e.run(80)
    shot = e.snap(f"{tag} +90", after)
    if restore:
        later = None
        if mid in LASTING_MOVES:
            e.run(60)
            later = e.snap(f"{tag} +150", after).img
        restore_check(sc, tag, idle, shot.img, mid, later)
    d = min_diff(base_boxes, text_box(shot.img))
    if not sc.check(f"{tag}: battle text restored", d < 0.02,
                    f"{d:.1%} of the text box differs from before the overlay (90 frames after)",
                    why="the message box was not restored (garbled or blank; see sheet_after)"):
        if not sc.check(f"{tag}: command menu still responds", menu_responds(e),
                        why="touching FIGHT no longer opens the move list: the battle is soft-locked"):
            return False
    return True


def restore_check(sc: Scenario, tag: str, idle: List[Image.Image], img: Image.Image, mid: int = 0,
                  later: Optional[Image.Image] = None) -> bool:
    """90 frames after a move the scene (HUD masked, above the text box) must be back to an idle frame:
    PASS <= RESTORE_PASS of the pixels differ from the closest one, WARN <= RESTORE_WARN, else FAIL.
    A LASTING_MOVES move (`later` = the scene 60 frames on) may leave its look behind as in a real
    battle, so its idle comparison is at most a WARN; instead the scene must have settled (+90 vs +150)."""
    d = min_diff(idle, scene(img))
    detail = f"{d:.2%} of the scene (HUD masked) differs from the closest idle frame, 90 frames after"
    if mid not in LASTING_MOVES or later is None:
        return sc.check(f"{tag}: normal look restored", d <= RESTORE_PASS, detail, warn_only=d <= RESTORE_WARN,
                        why="a sprite is still hidden, shrunk, replaced or swapped (see sheet_after)")
    s = diff_fraction(scene(img), scene(later))
    sc.check(f"{tag}: scene settled after the move", s <= RESTORE_PASS,
             f"{s:.2%} of the scene differs between +90 and +150 frames", warn_only=s <= RESTORE_WARN,
             why="the sprites are still changing: the animation left something running")
    return sc.check(f"{tag}: normal look restored", d <= RESTORE_PASS, detail, warn_only=True,
                    why=f"{LASTING_MOVES[mid]} stays as in a real battle, so this is only a WARN; if the mons are "
                        "flat boxes, the doll graphics never loaded (a move tester bug that the pre-chunk-3 main ROM "
                        "has too; see sheet_after)")


def sc_move_tester(sc: Scenario, e: Emu, args) -> None:
    if not _battle_ready(sc, e):
        return
    ov = Overlay(e)
    e.run(30)                                # let the menu's text box icons appear
    _sprite_flags(sc, e, args, FREEZE_IDLE)  # the restore checks compare against these idle frames
    idle_frames = e.record(60, every=5, label="idle")
    baseline = ([scene(f.img) for f in idle_frames], [text_box(f.img) for f in idle_frames])
    overlays: List[Frame] = []
    after: List[Frame] = []
    if not ov.show():
        _no_combo(sc, "L+R move-tester overlay shown", "the in-battle move tester")
        run_away(sc, e)
        return
    e.snap("overlay (start, expect Move 001)", overlays)
    cur, ok = 1, True
    order = args.moves + [m for m in args.sprite_moves if m not in args.moves]
    # Substitute and Transform leave their look behind for the rest of the battle (and on the main
    # ROM the move tester's Substitute turns both mons into flat boxes), so they go last: every
    # other "normal look restored" check still compares against the idle frames from before.
    order = [m for m in order if m not in LASTING_MOVES] + [m for m in order if m in LASTING_MOVES]
    if order != args.moves + [m for m in args.sprite_moves if m not in args.moves]:
        sc.note("Substitute and Transform are played last: their look lasts for the rest of the battle")
    for mid in order:
        mid = max(1, min(MOVE_ID_MAX, mid))
        for direction, key in (("fwd", "A"), ("rev", "Y"))[: 2 if args.reverse else 1]:
            ok = _tester_move(sc, e, args, ov, baseline, cur, mid, direction, key,
                              f"move {mid:03d} {direction}", overlays, after, restore=mid in args.sprite_moves)
            cur = mid
            if not ok:
                break
        if not ok:
            break

    # A real turn after the tester, then the tester again on turn 2: from then on the AI picks its
    # move while the menu is already up, so the tester has to wait for it before swapping overlays.
    if ok:
        if not e.battle_menu_up():
            e.wait_battle_menu(timeout=1800, advance_text=True)
        ok = e.battle_menu_up() and _fight_turn(sc, e, args, "turn 1 after tester")
    if ok:
        e.run(30)
        ok = _tester_move(sc, e, args, ov, baseline, cur, MOVE_ID_POUND, "fwd", "A",
                          "turn 2 move 001 fwd", overlays, after)
        cur = MOVE_ID_POUND
    if ok:
        ok = _fight_turn(sc, e, args, "turn 2 after tester")

    sc.sheet(overlays, "overlays", "L+R overlay before each animation (check the move name)",
             screen="top", cols=4, scale=1.0)
    sc.sheet(after, "after", "battle text 10 and 90 frames after each animation (should read 'What will ... do?')",
             screen="top", cols=4, scale=1.0)
    if not ok:
        sc.note("Skipped running away: the command menu is stuck or frozen.")
        return
    run_away(sc, e)


def sc_stage_toggle(sc: Scenario, e: Emu, args) -> None:
    # The save's own wild battle (Eterna Forest) has no arena, and there the overlay shows
    # "2D" with nothing for SELECT to toggle
    if not _plain_battle(sc, e, args.stage_tod):
        return
    ov = Overlay(e)
    shots: List[Frame] = []
    e.run(30)
    e.snap("idle (initial)", shots)
    base_samples = idle_samples(e)
    base_boxes = [s.crop(TEXT_BOX) for s in base_samples]
    if not ov.show():
        _no_combo(sc, "L+R overlay shown", "the in-battle move tester / stage toggle")
        run_away(sc, e)
        return
    ov0 = e.snap("overlay before SELECT", shots)
    states: List[Frame] = []
    stuck = False
    for i in (1, 2):
        if not ov.up() and not ov.show():
            sc.check(f"overlay back for SELECT #{i}", False, "holding L+R did not bring the overlay back")
            break
        e.hold("SELECT", 6, 10)
        o = e.snap(f"overlay after SELECT #{i}", shots)
        # The key line shows the stage state (see _toggle_stage)
        ov.key = e.screens().crop(OVERLAY_KEY)
        states.append(o)
        prev = ov0 if i == 1 else states[0]
        d = diff_fraction(text_box(prev.img), text_box(o.img))
        sc.check(f"SELECT #{i} changed the overlay text (3D stage ON/OFF)", d > 0.003,
                 f"{d:.2%} of the text box changed")
        e.release("L+R")
        e.run(30)
        s = e.snap(f"scene after SELECT #{i}", shots)
        sc.note(f"scene after SELECT #{i}: {min_diff(base_samples, top(s.img)):.2%} differs from the initial idle")
        check_screens(sc, s.img, f"after SELECT #{i}")
        d = min_diff(base_boxes, text_box(s.img))
        sc.check(f"battle text restored after SELECT #{i}", d < 0.02, f"{d:.1%} of the text box differs")
        # One short animation (Pound, the tester's current move) in this stage state.
        if not ov.show():
            sc.check(f"overlay back for Pound after SELECT #{i}", False)
            break
        anim, done = ov.play("A", args.anim_frames, f"pound s{i}")
        if froze(sc, e, anim, f"playing Pound (L+R+A) after SELECT #{i}"):
            shots.append(e.snap("frozen"))
            stuck = True
            break
        sc.sheet(anim, f"pound_after_select{i}", f"Pound after SELECT #{i}", screen="top", dedupe_screen="top")
        if not sc.check(f"Pound after SELECT #{i} finished", done is not None,
                        f"overlay hidden {done} frames after L+R+A" if done is not None else
                        f"overlay still up {len(anim) * 3} frames later: the command menu is stuck"):
            shots.append(e.snap("stuck"))
            stuck = True
            break
        e.run(90)
        s = e.snap(f"90 frames after Pound #{i}", shots)
        d = min_diff(base_boxes, text_box(s.img))
        if not sc.check(f"battle text restored after Pound #{i}", d < 0.02, f"{d:.1%} of the text box differs"):
            if not sc.check(f"command menu still responds after Pound #{i}", menu_responds(e),
                            why="touching FIGHT no longer opens the move list: the battle is soft-locked"):
                stuck = True
                break
    if len(states) == 2:
        d = diff_fraction(text_box(ov0.img), text_box(states[-1].img))
        sc.check("two SELECTs restore the original state text", d < 0.003, f"{d:.2%} differs", warn_only=True)
    sc.sheet(shots, "toggle", "stage toggle: overlay text (ON/OFF) and the scene after each SELECT",
             cols=4, scale=0.75)
    if stuck:
        sc.note("Skipped running away: the command menu is stuck or frozen.")
        return
    if not e.battle_menu_up():
        e.wait_battle_menu(timeout=1800, advance_text=True)
    if sc.check("command menu responds at the end", menu_responds(e),
                why="touching FIGHT did not open the move list"):
        run_away(sc, e)


# ---- 3D stage compatibility (chunk 1) --------------------------------------------------------

QB_PLAIN = 1                             # quick-battle entry 01: BACKGROUND_PLAIN / TERRAIN_PLAIN
QB_PLAIN_GRASS = 30                      # quick-battle entry 30: BACKGROUND_PLAIN / TERRAIN_GRASS
AB_THRESHOLD = 24                        # max channel difference that counts a pixel as changed
# Home pose vs classic (the same battle with the stage switched off), for stage_ab and
# all_backgrounds. The scene above the text box is compared with the HUD masked, after lining up
# the idle bob of the two states, on the per-pixel max channel difference:
#  - mean: an even tint or dimming of the whole arena raises it;
#  - big: the share of pixels off by more than AB_BIG (6 steps of the DS's 5-bit channels).
#    Misplaced geometry, a wrong texture or a palette error cause it; a gentle tint does not.
# At day the home pose should match classic nearly exactly (lit surfaces saturate to white), but
# texture filtering and the half-pixel convention leave a few stray pixels, hence a tolerance
# rather than an exact match. Twilight and night may add "a gentle tint and dimming", so their
# mean is looser; misalignment is judged the same way at every time of day.
AB_BIG = 48
AB_LIMITS = {        # time of day: ((PASS if mean <=, and big <=), (FAIL if mean >, or big >))
    "day": ((3.0, 0.01), (12.0, 0.05)),
    "twilight": ((10.0, 0.02), (24.0, 0.08)),
    "night": ((10.0, 0.02), (24.0, 0.08)),
}
# (move ID, name, least share of the scene that must change mid-animation)
SWITCHBG_MOVES = [
    (101, "Night Shade", 0.25),
    (94, "Psychic", 0.25),
    (399, "Dark Pulse", 0.25),
    (151, "Acid Armor", 0.01),
]
RESTORE_PASS, RESTORE_WARN = 0.02, 0.08
DEBUG_VIEWS = 4


STAGE_ENTRY = QB_PLAIN                   # --stage-terrain picks the entry the 3D stage scenarios use


def _plain_battle(sc: Scenario, e: Emu, tod: str = "clock") -> bool:
    """Boots, starts the Plain background quick battle (entry 01, or 30 with grass
    platforms under --stage-terrain grass) at time of day `tod` (see TODS) and waits for the menu."""
    if not boot(sc, e):
        return False
    panel: List[Frame] = []
    steps = STAGE_ENTRY if STAGE_ENTRY <= QB_ENTRIES // 2 else STAGE_ENTRY - QB_ENTRIES   # DOWN = +1, UP = -1
    started = _qb_start(sc, e, "A", steps, 0, panel, "plain", tod_taps=TODS.index(tod))
    if not started:
        sc.sheet(panel, "panel", "L+R quick-battle panel", screen="top", cols=4, scale=1.0)
        return False
    waited = e.wait_battle_menu(timeout=2400)
    if not sc.check("plain: battle menu reached", waited is not None,
                    f"{waited} frames" if waited is not None else "no command menu within 2400 frames"):
        return False
    e.run(30)                                # let the menu's text box icons appear
    return True


def _finish(sc: Scenario, e: Emu) -> None:
    if not e.battle_menu_up():
        e.wait_battle_menu(timeout=1800, advance_text=True)
    if sc.check("command menu responds at the end", menu_responds(e),
                why="touching FIGHT did not open the move list"):
        run_away(sc, e)


def pixel_diff(a: Image.Image, b: Image.Image, threshold: int = AB_THRESHOLD) -> dict:
    """Per pixel max channel difference: its mean and max, the share of pixels over threshold,
    over AB_BIG ("big") and exactly equal ("exact")."""
    r, g, bl = ImageChops.difference(a.convert("RGB"), b.convert("RGB")).split()
    m = ImageChops.lighter(ImageChops.lighter(r, g), bl)
    hist = m.histogram()
    n = float(a.size[0] * a.size[1])
    return {"mean": sum(v * c for v, c in enumerate(hist)) / n,
            "max": max(v for v, c in enumerate(hist) if c),
            "pct": sum(hist[threshold + 1:]) / n,
            "big": sum(hist[AB_BIG + 1:]) / n,
            "exact": hist[0] / n,
            "map": m}


def home_grade(st: dict, tod: str) -> str:
    """PASS / WARN / FAIL for a home pose vs classic pixel_diff (see AB_LIMITS)."""
    (pm, pb), (fm, fb) = AB_LIMITS.get(tod, AB_LIMITS["night"])
    if st["mean"] > fm or st["big"] > fb:
        return "FAIL"
    return "PASS" if st["mean"] <= pm and st["big"] <= pb else "WARN"


def limits_text(tod: str) -> str:
    (pm, pb), (fm, fb) = AB_LIMITS.get(tod, AB_LIMITS["night"])
    return (f"{tod} tolerance: PASS at mean <= {pm} and <= {pb:.0%} of pixels off by more than {AB_BIG}; "
            f"FAIL above mean {fm} or {fb:.0%}")


def diff_detail(st: dict) -> str:
    return (f"mean {st['mean']:.2f}, max {st['max']}, {st['big']:.2%} off by more than {AB_BIG}, "
            f"{st['pct']:.2%} by more than {AB_THRESHOLD}, {st['exact']:.1%} identical")


def write_heatmap(a: Image.Image, b: Image.Image, stats: dict, path: pathlib.Path) -> str:
    """Writes A | B | heat at 2x (black = equal, red -> yellow -> white = larger difference)."""
    m = stats["map"].point(lambda v: min(255, v * 4))
    heat = Image.merge("RGB", (m.point(lambda v: min(255, v * 3)),
                               m.point(lambda v: max(0, min(255, v * 3 - 255))),
                               m.point(lambda v: max(0, min(255, v * 3 - 510)))))
    w, h = a.size
    out = Image.new("RGB", (w * 3 + 4, h), (40, 40, 40))
    out.paste(a.convert("RGB"), (0, 0))
    out.paste(b.convert("RGB"), (w + 2, 0))
    out.paste(heat, (2 * w + 4, 0))
    out.resize((out.size[0] * 2, h * 2), Image.NEAREST).save(path)
    return str(path)


def best_pair(xs: List[Image.Image], ys: List[Image.Image]) -> tuple:
    """The (x, y) pair with the fewest changed pixels, which lines up the idle bob of two runs."""
    return min(((x, y) for x in xs for y in ys), key=lambda p: diff_fraction(p[0], p[1]))


def _toggle_stage(sc: Scenario, e: Emu, ov: Overlay, tag: str, shots: List[Frame]) -> bool:
    """L+R+SELECT at the command menu, then releases L+R and waits for the battle text."""
    if not ov.up() and not ov.show():
        sc.check(f"{tag}: overlay shown", False, "holding L+R did not bring the overlay up")
        return False
    before = text_box(e.screens())
    e.hold("SELECT", 6, 10)
    e.snap(f"{tag} overlay", shots)
    d = diff_fraction(before, text_box(e.screens()))
    ok = sc.check(f"{tag}: SELECT changed the overlay text", d > 0.003, f"{d:.2%} of the text box changed")
    # The overlay's key line shows the stage state, so re-key it or the next show() won't
    # recognise the overlay
    ov.key = e.screens().crop(OVERLAY_KEY)
    e.release("L+R")
    e.run(40)
    return ok


def sc_stage_ab(sc: Scenario, e: Emu, args) -> None:
    # The launcher forces the time of day (day by default), so the host clock cannot change
    # the palette or the tolerance between runs
    if not _plain_battle(sc, e, args.stage_tod):
        return
    # Sprites at rest and the classic shadow: then the day home pose must match classic exactly
    _sprite_flags(sc, e, args, FREEZE_IDLE | NO_BLOB_SHADOWS)
    ov = Overlay(e)
    shots: List[Frame] = []
    e.snap("initial (stage ON)", shots)
    first = idle_samples(e, n=24, every=3)
    if not ov.show():
        _no_combo(sc, "L+R overlay shown", "the in-battle move tester / stage toggle")
        run_away(sc, e)
        return
    if not _toggle_stage(sc, e, ov, "toggle 1", shots):
        run_away(sc, e)
        return
    e.snap("toggled (stage OFF)", shots)
    second = idle_samples(e, n=24, every=3)
    a, b = best_pair([scene(i) for i in first], [scene(i) for i in second])
    st = pixel_diff(a, b)
    path = write_heatmap(a, b, st, sc.dir / "stage_ab_heatmap.png")
    status = home_grade(st, args.stage_tod)
    sc.grade(f"stage ON matches the classic look (OFF) at the home pose ({args.stage_tod})", status,
             f"scene (HUD masked, text box cut): {diff_detail(st)} (ON | OFF | heat: {path})",
             why=limits_text(args.stage_tod) + "; " +
                 ("gross mismatch: the arena does not line up with the classic backdrop or has the wrong colours"
                  if status == "FAIL" else "small mismatch: see the heatmap"))
    a2, b2 = best_pair(first, second)
    sc.note(f"whole top screen (HUD and text box included): {diff_detail(pixel_diff(a2, b2))}")
    sc.note("Assumes the stage starts ON (the default); check the overlay text in sheet_ab.")
    check_screens(sc, e.screens(), "stage off")
    _toggle_stage(sc, e, ov, "toggle 2", shots)
    e.snap("toggled back (stage ON)", shots)
    sc.sheet(shots, "ab", "initial -> L+R+SELECT -> toggled -> L+R+SELECT -> back", cols=5, scale=0.75)
    sc.sheet([Frame("ON", 0, a2), Frame("OFF", 0, b2)], "ab_pair", "best-aligned ON / OFF pair",
             screen="top", cols=2, scale=1.0)
    _finish(sc, e)


def sc_switchbg_moves(sc: Scenario, e: Emu, args) -> None:
    if not _plain_battle(sc, e, args.stage_tod):
        return
    _sprite_flags(sc, e, args, FREEZE_IDLE)       # "normal look restored" compares against idle frames
    ov = Overlay(e)
    idle_frames = e.record(60, every=5, label="idle")
    idle = [scene(f.img) for f in idle_frames]
    boxes = [text_box(f.img) for f in idle_frames]
    if not ov.show():
        _no_combo(sc, "L+R overlay shown", "the in-battle move tester")
        run_away(sc, e)
        return
    after: List[Frame] = []
    cur = MOVE_ID_POUND
    for mid, name, need in SWITCHBG_MOVES:
        tag = f"{mid:03d} {name}"
        if not ov.up() and not ov.show():
            sc.check(f"{tag}: overlay shown", False, "holding L+R did not bring the overlay back")
            return
        _nav_move(e, cur, mid)
        cur = mid
        pre = scene(e.snap(f"{tag} pre", after).img)
        anim, done = ov.play("A", args.anim_frames, f"{mid:03d}")
        if froze(sc, e, anim, f"playing {name}"):
            return
        changes = [diff_fraction(pre, scene(f.img)) for f in anim]
        peak = max(changes, default=0.0)
        at = f" at {anim[changes.index(peak)].label}" if anim else ""
        sc.check(f"{tag}: special background shown mid-animation", peak >= need,
                 f"up to {peak:.1%} of the scene (HUD masked) differs from the pre-move frame{at}; "
                 f"needs {need:.0%}", why="the move's background never showed: the 3D stage may cover it")
        sc.sheet(anim, f"{mid:03d}", f"{tag}: player->enemy, every 3 frames (deduped)", screen="top",
                 dedupe_screen="top")
        if not sc.check(f"{tag}: animation finished", done is not None,
                        f"overlay hidden {done} frames after L+R+A" if done is not None else
                        f"overlay still up {len(anim) * 3} frames later"):
            sc.sheet(after, "after", "pre-move frame and 90 frames after each move", screen="top", cols=4, scale=1.0)
            return
        e.run(90)
        post = e.snap(f"{tag} +90", after)
        d = min_diff(idle, scene(post.img))
        sc.check(f"{tag}: normal look restored", d <= RESTORE_PASS,
                 f"{d:.2%} of the scene (HUD masked) differs from the closest idle frame, 90 frames after",
                 warn_only=d <= RESTORE_WARN, why="the backdrop did not come back (see sheet_after)")
        t = min_diff(boxes, text_box(post.img))
        sc.check(f"{tag}: battle text restored", t < 0.02, f"{t:.1%} of the text box differs")
    sc.sheet(after, "after", "pre-move frame and 90 frames after each move", screen="top", cols=4, scale=1.0)
    _finish(sc, e)


def _sub_menu_settled(e: Emu, menu: Image.Image) -> bool:
    """The bottom screen shows something other than the command menu, lit and no longer fading
    (the party screen fades through black first)."""
    now = bottom(e.screens())
    if diff_fraction(menu, now) < 0.5 or e.battle_menu_up() or mean_brightness(now) < 8:
        return False
    e.run(10)
    return diff_fraction(now, bottom(e.screens())) < 0.02


def _menu_round_trip(sc: Scenario, e: Emu, what: str, button: tuple, shots: List[Frame],
                     inside: Optional[tuple] = None) -> bool:
    """Opens a battle sub-menu from the command menu, backs out with B and compares the top screen."""
    before = idle_samples(e)
    below = bottom(e.screens())
    e.touch(*button, after=10)
    opened = e.wait_until(lambda em: _sub_menu_settled(em, below), timeout=300, step=5) is not None
    e.run(20)
    inner = e.snap(what, shots)
    if inside:
        e.touch(*inside, after=60)
        e.snap(f"{what} page", shots)
    sc.check(f"{what} opened", opened, "the bottom screen changed" if opened else "the bottom screen did not change")
    check_screens(sc, inner.img, f"in the {what}")
    closed = e.battle_close_bag()
    e.run(20)
    after = e.snap(f"after {what}", shots)
    if not sc.check(f"{what} closed back to the menu", closed, why="no command menu after B"):
        return False
    d = min_diff(before, top(after.img))
    detail = f"{d:.2%} of top pixels differ from the closest idle frame before the {what}"
    if d > RESTORE_PASS:
        a, b = best_pair(before, [top(after.img)])
        detail += f" (before | after | heat: {write_heatmap(a, b, pixel_diff(a, b), sc.dir / (what + '_heatmap.png'))})"
    sc.check(f"top screen unchanged after the {what}", d <= RESTORE_PASS, detail, warn_only=d <= RESTORE_WARN)
    return True


def sc_bag_party(sc: Scenario, e: Emu, args) -> None:
    if not _plain_battle(sc, e, args.stage_tod):
        return
    _sprite_flags(sc, e, args, FREEZE_IDLE)       # the round trips compare against idle frames
    shots: List[Frame] = []
    e.snap("menu", shots)
    ok = _menu_round_trip(sc, e, "bag", BTN_BAG, shots, inside=BAG_POCKET_HP)
    if ok:
        e.run(30)
        ok = _menu_round_trip(sc, e, "party", BTN_POKEMON, shots)
    sc.sheet(shots, "menus", "command menu -> bag -> pocket -> back -> party -> back", cols=4, scale=0.75)
    if ok:
        _finish(sc, e)


def sc_debug_views(sc: Scenario, e: Emu, args) -> None:
    if not _plain_battle(sc, e, args.stage_tod):
        return
    _sprite_flags(sc, e, args, FREEZE_IDLE)       # the views are compared against view 0
    ov = Overlay(e)
    if not ov.show():
        _no_combo(sc, "L+R overlay shown", "the in-battle move tester / debug views")
        run_away(sc, e)
        return
    e.run(20)
    views: List[Frame] = []
    base = [scene(s) for s in idle_samples(e, n=8, every=4)]
    views.append(e.snap("view 0"))
    changed = 0
    for v in range(1, DEBUG_VIEWS + 1):
        view = v % DEBUG_VIEWS
        if not ov.up() and not ov.show():
            sc.check(f"view {view}: overlay shown", False, "holding L+R did not bring the overlay back")
            break
        e.hold("B", 6, 40)                   # lets an eased camera move settle
        f = e.snap(f"view {view}" + (" (wrapped)" if v == DEBUG_VIEWS else ""), views)
        img = scene(f.img)
        d = min_diff(base, img)
        if v < DEBUG_VIEWS:
            changed += d > 0.02
            sc.check(f"view {view} differs from view 0", d > 0.02,
                     f"{d:.1%} of the scene (HUD masked, above the text box) differs from view 0",
                     why="L+R+B changed nothing (debug views not in this ROM, or no arena to look at)")
            raw = top(f.img).crop(SCENE)
            why = looks_broken(raw)
            bright = mean_brightness(raw)
            sc.check(f"view {view} not blank or black", why is None and bright >= 12,
                     f"brightness {bright:.1f}, {screen_health(raw)}", why=why or "the scene is (nearly) black")
        else:
            sc.check("a fourth L+R+B wraps back to view 0", d <= 0.02,
                     f"{d:.1%} of the scene differs from the first view 0", warn_only=True)
    sc.sheet(views, "views", "L+R+B debug views 0 -> 1 -> 2 -> 3 -> 0", screen="top", cols=5, scale=1.0)
    e.release("L+R")
    e.run(40)
    if not changed:
        sc.note("No view changed the scene; if the ROM has no L+R+B combo yet, that is the cause.")
    _finish(sc, e)


# ---- RAM through the xMAP (optional) ---------------------------------------------------------

# BattleStage in src/battle/battle_stage.c, one s32/pointer per field; brightness is format v2 only,
# debugFlags..blobShadows (+32..+48) chunk 3 only (docs/living_battle_stage/sprites.md)
STAGE_FIELDS = ("battleSys", "arena", "enabled", "suppressed", "view", "visible", "platformsHidden", "brightness",
                "debugFlags", "spriteMeshes", "idleFrames", "wobbleMask", "blobShadows")
STAGE_SIZE_BRIGHTNESS = 32               # sBattleStage at least this big: has brightness
STAGE_SIZE_SPRITES = 52                  # ... and the chunk 3 sprite debug fields
DEBUG_FLAGS_OFFSET = 32
SUPPRESS_BRIGHTNESS = 4                  # BATTLE_STAGE_SUPPRESS_BRIGHTNESS
# debugFlags bits, written by the critic. sBattleStage is in the battle overlay's .bss, which is zeroed
# on every battle load, so they must be written inside each battle (after the command menu is up);
# the renderer reads them every frame, so a write takes effect on the next drawn frame.
FREEZE_IDLE = 1                          # no breathing and no hit wobble (sprites at the rest pose)
NO_BLOB_SHADOWS = 2                      # blob shadows off, classic shadow back
CLASSIC_SPRITES = 4                      # sprites take the old unlit path even while the arena shows
FLAG_NAMES = ((FREEZE_IDLE, "FREEZE_IDLE"), (NO_BLOB_SHADOWS, "NO_BLOB_SHADOWS"), (CLASSIC_SPRITES, "CLASSIC_SPRITES"))


def flag_names(flags: int) -> str:
    return "|".join(n for b, n in FLAG_NAMES if flags & b) or "0"


def find_xmap(args) -> Optional[str]:
    """--map, else the xMAP next to the ROM or in the build dir it came from ("--map none" = no RAM)."""
    if args.map:
        return None if args.map.lower() == "none" else args.map
    rom = pathlib.Path(args.rom).resolve()
    for p in (rom.with_suffix(".xMAP"), rom.parent / "build" / "main.nef.xMAP",
              rom.parent.parent / "build" / "main.nef.xMAP"):
        if p.exists():
            return str(p)
    return None


class StageRam:
    """sBattleStage and the launcher's selection, read at the addresses in the build's xMAP. Every
    check that uses it also has a pixel counterpart, so a missing or mismatched xMAP only drops the
    RAM half (validate() catches an xMAP from another build)."""

    def __init__(self, e: Emu, xmap: Optional[str]):
        self.e = e
        self.syms = read_xmap(xmap) if xmap else {}
        self.stage = self.syms.get("sBattleStage")
        self.ok = self.stage is not None
        self.why = "" if self.ok else ("no xMAP (pass --map)" if not xmap else f"no sBattleStage in {xmap}")
        self.xmap = xmap

    @property
    def has_brightness(self) -> bool:
        return self.ok and self.stage[1] >= STAGE_SIZE_BRIGHTNESS

    @property
    def has_sprites(self) -> bool:
        """sBattleStage has the chunk 3 debug fields (debugFlags .. blobShadows at +32..+48)."""
        return self.ok and self.stage[1] >= STAGE_SIZE_SPRITES

    @property
    def sprite_why(self) -> str:
        """Why the sprite debug fields cannot be used ("" if they can)."""
        if not self.ok:
            return self.why
        if not self.has_sprites:
            return (f"sBattleStage is {self.stage[1]} bytes in {self.xmap}, under {STAGE_SIZE_SPRITES}: a ROM from "
                    "before chunk 3, without the sprite debug fields")
        return ""

    def read(self) -> Optional[dict]:
        if not self.ok:
            return None
        addr, size = self.stage
        n = min(size, 4 * len(STAGE_FIELDS)) // 4
        return dict(zip(STAGE_FIELDS, struct.unpack(f"<{n}i", self.e.read(addr, 4 * n))))

    def field(self, name: str) -> Optional[int]:
        """One field (None if the RAM checks are off or this build's sBattleStage lacks it)."""
        st = self.read()
        return None if st is None else st.get(name)

    def validate(self, st: Optional[dict]) -> bool:
        """Call in a battle: drops the RAM checks if sBattleStage does not look like one."""
        if not self.ok:
            return False
        if st["battleSys"] == 0:
            self.why = "sBattleStage is not set up in this battle (no 3D stage here)"
            return False
        good = (RAM_BASE <= st["battleSys"] < RAM_END and st["enabled"] in (0, 1) and st["visible"] in (0, 1)
                and 0 <= st["view"] < DEBUG_VIEWS)
        if not good:
            self.ok = False
            self.why = f"sBattleStage in {self.xmap} reads {st}: the xMAP is not from this ROM's build"
        return good

    def set_flags(self, flags: int, settle: int = 4) -> bool:
        """Writes debugFlags (sBattleStage+32) and runs `settle` frames so the renderer draws with them.
        Call in a battle, at the command menu. False (nothing written) on a ROM without the field or
        when sBattleStage does not validate, so a wrong xMAP never corrupts RAM."""
        if not self.has_sprites or not self.validate(self.read()):
            return False
        self.e.write(self.stage[0] + DEBUG_FLAGS_OFFSET, struct.pack("<I", flags))
        self.e.run(settle)
        return True

    def byte(self, name: str) -> Optional[int]:
        if not self.ok or name not in self.syms:
            return None
        return self.e.read(self.syms[name][0], 1)[0]


def _sprite_flags(sc: Scenario, e: Emu, args, flags: int, ram: Optional[StageRam] = None) -> StageRam:
    """At the command menu of a battle: sets sBattleStage.debugFlags (see FREEZE_IDLE) where the ROM has it,
    so comparisons against earlier frames are not thrown off by breathing, wobble or blob shadows.
    On an older ROM (or without a usable xMAP) it only notes why; those ROMs have no idle motion anyway."""
    ram = ram or StageRam(e, find_xmap(args))
    if ram.set_flags(flags):
        sc.note(f"debugFlags = {flag_names(flags)} (sBattleStage+{DEBUG_FLAGS_OFFSET} at {ram.stage[0]:#x})")
    else:
        sc.note(f"debugFlags {flag_names(flags)} not set: {ram.sprite_why or ram.why}; comparisons use the "
                "scene as drawn")
    return ram


# ---- all backgrounds and times of day (chunk 2) ----------------------------------------------

TODS = ("clock", "day", "twilight", "night")      # the launcher's SELECT cycle (sTimeOfDayChoice)
QB_NAMES = ["map", "Plain", "Water", "City", "Forest", "Mountain", "Snow", "Indoors1", "Indoors2", "Indoors3",
            "Cave1", "Cave2", "Cave3", "Aaron", "Bertha", "Flint", "Lucian", "Cynthia", "Distortion", "Tower",
            "Factory", "Arcade", "Castle", "Hall", "Plain/Sand", "Plain/Puddle", "Plain/Bridge", "Snow/Ice",
            "Forest/Marsh", "Dist/Giratina", "Plain/Grass"]
# Entries whose battle uses the time of day (ov16_0223EC04: the Plain, Water, City, Forest, Mountain
# and Snow backgrounds). The others are always drawn as day, so twilight/night repeat the day battle.
QB_TOD_ENTRIES = {1, 2, 3, 4, 5, 6, 24, 25, 26, 27, 28, 30}
# The BG0-only render with a magenta backdrop (Emu.render_layers) shows where the 3D layer drew
# nothing. The arena covers the whole scene at the home pose; the sprites alone cover under 10%.
ARENA_COVER = 0.95                       # least share of the scene the home pose's BG0 must cover
ARENA_GAIN = 0.30                        # ... and how much more than with the stage off
MARKER_SANE = 0.5                        # stage off: at least this much magenta, or the marker trick failed
# Holes: scene pixels a debug view leaves uncovered that the home pose covered
HOLE_PASS, HOLE_FAIL = 0.001, 0.01
BG_PER_SHEET = 10


def bg_plan(args) -> List[tuple]:
    """(tod, entry) battles for all_backgrounds, in play order."""
    bgs = args.bgs if args.bgs is not None else list(range(1, QB_ENTRIES))
    plan = []
    for tod in args.tods:
        for bg in bgs:
            if tod in ("day", "clock") or args.every_tod or bg in QB_TOD_ENTRIES:
                plan.append((tod, bg))
    return plan


def uncovered(img: Image.Image) -> float:
    return marker_fraction(img)


def _worst(statuses: List[str]) -> str:
    return "FAIL" if "FAIL" in statuses else ("WARN" if "WARN" in statuses else "PASS")


def _select_entry(sc: Scenario, e: Emu, ram: StageRam, cur: dict, bg: int, tod: str, tag: str) -> Optional[bool]:
    """With the launcher panel closed: opens it, steps to entry `bg` at time of day `tod`, presses A.
    True if a battle started, False if not, None if the panel never opened."""
    if hold_overlay(e, threshold=0.10) is None:
        _no_combo(sc, f"{tag}: L+R panel opened", "the overworld quick-battle panel")
        return None
    for _ in range(2):
        if ram.ok and ram.byte("sBackgroundChoice") is not None:
            cur["bg"], cur["tod"] = ram.byte("sBackgroundChoice"), ram.byte("sTimeOfDayChoice")
        steps = (bg - cur["bg"]) % QB_ENTRIES               # DOWN = +1, UP = -1, both wrap
        if steps > QB_ENTRIES // 2:
            steps -= QB_ENTRIES
        tap_held(e, "SELECT", (TODS.index(tod) - cur["tod"]) % len(TODS))
        tap_held(e, "DOWN" if steps >= 0 else "UP", abs(steps))
        cur["bg"], cur["tod"] = bg, TODS.index(tod)
        e.run(4)
        if not ram.ok or ram.byte("sBackgroundChoice") is None:
            break
        got = (ram.byte("sBackgroundChoice"), ram.byte("sTimeOfDayChoice"))
        if got == (bg, TODS.index(tod)):
            break
        sc.warn(f"{tag}: launcher selection", f"RAM shows entry {got[0]}, time of day {got[1]} after the "
                f"taps; stepping again")
    e.hold("A", 6, 0)
    e.release("L+R")
    if e.wait_until(lambda em: not em.in_overworld(), timeout=240, step=4) is None:
        return sc.check(f"{tag}: battle started", False, why="still in the overworld 240 frames after L+R+A")
    return True


def _bg_battle(sc: Scenario, e: Emu, args, ram: StageRam, tod: str, bg: int, rows: List[Frame]) -> Optional[dict]:
    """One all_backgrounds battle from the command menu: home pose, debug views 1-3, stage off.
    Returns the measurements (None if the overlay never came up)."""
    tag = f"{tod} {bg:02d} {QB_NAMES[bg]}"
    rec: dict = {"tod": tod, "bg": bg, "name": QB_NAMES[bg], "problems": []}
    st = ram.read()
    if st is not None and ram.validate(st):
        rec["ram_home"] = st
        # Home vs classic needs the sprites at rest and the classic shadow, as in stage_ab
        ram.set_flags(FREEZE_IDLE | NO_BLOB_SHADOWS)
    home = idle_samples(e, n=10, every=3)
    bg0 = top(e.render_layers(LAYER_BG0, marker=True)).crop(SCENE)
    rec["cover"] = 1.0 - uncovered(bg0)
    rows.append(Frame(f"{bg:02d} {QB_NAMES[bg]}", e.frame, home[-1]))
    ov = Overlay(e)
    if not ov.show():
        sc.check(f"{tag}: L+R overlay shown", False, "the move tester overlay never came up")
        return None
    rec["views"] = []
    for v in range(1, DEBUG_VIEWS):
        if not ov.up() and not ov.show():
            sc.check(f"{tag}: overlay back for view {v}", False, "holding L+R did not bring the overlay back")
            return None
        e.hold("B", 6, 36)                   # lets an eased camera move settle
        img = top(e.screens())
        st = ram.read() if ram.ok else None
        render = top(e.render_layers(LAYER_BG0, marker=True)).crop(SCENE)
        hole = max(0.0, uncovered(render) - (1.0 - rec["cover"]))
        broken = looks_broken(img.crop(SCENE))
        rec["views"].append({"view": v, "hole": hole, "ram_view": st["view"] if st else None,
                             "moved": diff_fraction(scene(home[-1]), scene(img)), "broken": broken})
        rows.append(Frame(f"v{v} hole {hole:.1%}", e.frame, img))
        if hole > HOLE_PASS and rec["cover"] >= ARENA_COVER:
            hdir = sc.dir / "holes"
            hdir.mkdir(exist_ok=True)
            render.resize((512, 288), Image.NEAREST).save(hdir / f"{tod}_{bg:02d}_v{v}.png")
    before = text_box(e.screens())
    e.hold("SELECT", 6, 10)
    rec["toggle_text"] = diff_fraction(before, text_box(e.screens()))
    st = ram.read() if ram.ok else None
    rec["ram_off"] = st
    e.release("L+R")
    e.run(40)
    classic = idle_samples(e, n=10, every=3)
    off = top(e.render_layers(LAYER_BG0, marker=True)).crop(SCENE)
    rec["cover_off"] = 1.0 - uncovered(off)
    a, b = best_pair([scene(i) for i in home], [scene(i) for i in classic])
    d = pixel_diff(a, b)
    rec["diff"] = {k: d[k] for k in ("mean", "max", "pct", "big", "exact")}
    rec["grade"] = home_grade(d, tod)
    if rec["grade"] != "PASS":
        ddir = sc.dir / "diff"
        ddir.mkdir(exist_ok=True)
        rec["heatmap"] = write_heatmap(a, b, d, ddir / f"{tod}_{bg:02d}.png")
    rec["broken_home"] = looks_broken(top(home[-1]).crop(SCENE))
    rec["broken_off"] = looks_broken(top(classic[-1]).crop(SCENE))
    rows.append(Frame(f"OFF m{d['mean']:.1f} b{d['big']:.1%}", e.frame, classic[-1]))
    return rec


def _bg_grades(rec: dict) -> dict:
    """PASS / WARN / FAIL per check for one battle, with the problem written into rec["problems"]."""
    g = {}
    tag = f"{rec['bg']:02d} {rec['name']}"
    ram = rec.get("ram_home")
    drawn = rec["cover"] >= ARENA_COVER and rec["cover"] - rec["cover_off"] >= ARENA_GAIN
    if ram is not None:
        drawn = drawn and ram["arena"] != 0 and ram["visible"] == 1
    g["arena"] = "PASS" if drawn else "FAIL"
    if not drawn:
        rec["problems"].append(f"{tag}: arena missing (BG0 covers {rec['cover']:.0%} of the scene, "
                               f"{rec['cover_off']:.0%} with the stage off" +
                               (f"; RAM arena {ram['arena']:#x}, visible {ram['visible']}" if ram else "") + ")")
    worst = max((v["hole"] for v in rec["views"]), default=0.0)
    g["holes"] = "PASS" if worst <= HOLE_PASS else ("WARN" if worst <= HOLE_FAIL else "FAIL")
    if g["holes"] != "PASS" and drawn:
        rec["problems"].append(f"{tag}: holes up to {worst:.2%} of the scene ("
                               + ", ".join(f"v{v['view']} {v['hole']:.2%}" for v in rec["views"]) + ")")
    elif not drawn:
        g["holes"] = "PASS"                  # nothing to have holes in; reported as missing above
    stuck = [v["view"] for v in rec["views"] if v["moved"] <= 0.02]
    wrong = [v["view"] for v in rec["views"] if v["ram_view"] is not None and v["ram_view"] != v["view"]]
    g["views"] = "PASS" if drawn and not stuck and not wrong else ("PASS" if not drawn else "WARN")
    if g["views"] != "PASS":
        rec["problems"].append(f"{tag}: views {stuck} did not change the scene" +
                               (f"; RAM view differs for {wrong}" if wrong else ""))
    bad = [f"home: {rec['broken_home']}"] if rec["broken_home"] else []
    bad += [f"v{v['view']}: {v['broken']}" for v in rec["views"] if v["broken"]]
    g["garbage"] = "PASS" if not bad else ("WARN" if rec["broken_off"] else "FAIL")
    if bad:
        rec["problems"].append(f"{tag}: " + "; ".join(bad) +
                               (f" (classic too: {rec['broken_off']})" if rec["broken_off"] else ""))
    g["home"] = rec["grade"]
    if rec["grade"] != "PASS":
        rec["problems"].append(f"{tag}: home vs classic {diff_detail(rec['diff'])} (heat: {rec.get('heatmap')})")
    off = rec.get("ram_off")
    g["toggle"] = "PASS" if rec["toggle_text"] > 0.003 and (off is None or off["enabled"] == 0) else "FAIL"
    if g["toggle"] != "PASS":
        rec["problems"].append(f"{tag}: L+R+SELECT did not switch the stage off (text box {rec['toggle_text']:.2%}"
                               + (f", RAM enabled {off['enabled']}" if off else "") + ")")
    g["marker"] = "PASS" if 1.0 - rec["cover_off"] >= MARKER_SANE else "WARN"
    if g["marker"] != "PASS":
        rec["problems"].append(f"{tag}: with the stage off only {1 - rec['cover_off']:.0%} of the scene showed the "
                               "magenta backdrop: the marker did not take, so coverage and holes are unreliable")
    return g


BG_CHECKS = [
    ("arena", "arena drawn at the home pose on every background",
     f"BG0-only render covers >= {ARENA_COVER:.0%} of the scene and >= {ARENA_GAIN:.0%} more than with the stage "
     "off (RAM: arena loaded and visible)"),
    ("holes", "no holes in debug views 1-3",
     f"share of the scene the view leaves uncovered that the home pose covered: PASS <= {HOLE_PASS:.1%}, "
     f"FAIL > {HOLE_FAIL:.0%}"),
    ("views", "debug views 1-3 move the camera", "each view changes > 2% of the scene (RAM: debugView = 1, 2, 3)"),
    ("garbage", "no garbage or blank frames", "looks_broken on the scene at the home pose and in each view "
     "(WARN only if the classic art trips it too)"),
    ("home", "home pose matches classic within tolerance", "see AB_LIMITS"),
    ("toggle", "L+R+SELECT switches the stage off", "overlay text changes (RAM: enabled = 0)"),
    ("marker", "magenta backdrop marker works", f"stage off: >= {MARKER_SANE:.0%} of the scene is magenta"),
]


def _bg_summary(sc: Scenario, recs: List[dict], tods: List[str]) -> None:
    grades = [(r, _bg_grades(r)) for r in recs]
    for tod in tods:
        mine = [(r, g) for r, g in grades if r["tod"] == tod]
        if not mine:
            continue
        for key, name, how in BG_CHECKS:
            statuses = [g[key] for _, g in mine]
            status = _worst(statuses)
            bad = [f"{r['bg']:02d} {r['name']} {g[key]}" for r, g in mine if g[key] != "PASS"]
            if key == "home":
                means = [r["diff"]["mean"] for r, _ in mine]
                bigs = [r["diff"]["big"] for r, _ in mine]
                drawn = sum(g["arena"] == "PASS" for _, g in mine)
                detail = (f"{len(mine)} battles ({drawn} with an arena), mean {min(means):.2f}..{max(means):.2f}, "
                          f"off by > {AB_BIG}: {min(bigs):.2%}..{max(bigs):.2%}")
                how = limits_text(tod)
            elif key == "holes":
                holes = [max((v["hole"] for v in r["views"]), default=0.0) for r, g in mine if g["arena"] == "PASS"]
                detail = (f"{len(holes)} battles with an arena, worst {max(holes):.2%}" if holes else
                          "no battle had an arena to look at")
            elif key == "arena":
                detail = f"{len(mine)} battles, BG0 cover {min(r['cover'] for r, _ in mine):.1%} at least"
            else:
                detail = f"{len(mine)} battles"
            if bad:
                detail += "; not PASS: " + ", ".join(bad)
            sc.grade(f"{tod}: {name}", status, detail, why=how)
    for r, _ in grades:
        for p in r["problems"]:
            sc.note(f"{r['tod']} {p}")


def write_bg_table(sc: Scenario, recs: List[dict]) -> pathlib.Path:
    lines = ["| tod | entry | cover | cover off | holes v1/v2/v3 | home vs classic mean / max / >48 / exact | grade |",
             "|---|---|---|---|---|---|---|"]
    for r in recs:
        d = r["diff"]
        lines.append(f"| {r['tod']} | {r['bg']:02d} {r['name']} | {r['cover']:.1%} | {r['cover_off']:.1%} | "
                     + "/".join(f"{v['hole']:.2%}" for v in r["views"])
                     + f" | {d['mean']:.2f} / {d['max']} / {d['big']:.2%} / {d['exact']:.1%} | {r['grade']} |")
    path = sc.dir / "all_backgrounds.md"
    path.write_text("\n".join(lines) + "\n")
    (sc.dir / "all_backgrounds.json").write_text(json.dumps(recs, indent=1, default=str))
    return path


def sc_all_backgrounds(sc: Scenario, e: Emu, args) -> None:
    plan = bg_plan(args)
    if not boot(sc, e):
        return
    ram = StageRam(e, find_xmap(args))
    skipped = [f"{tod} {bg:02d}" for tod in args.tods for bg in (args.bgs or range(1, QB_ENTRIES))
               if (tod, bg) not in plan]
    if skipped:
        sc.note(f"skipped {len(skipped)} battles whose background ignores the time of day (drawn as day; "
                f"--every-tod plays them): {', '.join(skipped)}")
    cur = {"bg": 0, "tod": 0}
    recs: List[dict] = []
    rows: Dict[str, List[Frame]] = {}
    t0 = time.time()
    for n, (tod, bg) in enumerate(plan):
        tag = f"{tod} {bg:02d} {QB_NAMES[bg]}"
        print(f"  -- {tag} ({n + 1}/{len(plan)}, {time.time() - t0:.0f}s)", flush=True)
        started = _select_entry(sc, e, ram, cur, bg, tod, tag)
        if started is None:
            break
        if not started:
            if not e.in_overworld() and not e.battle_escape():
                break
            continue
        if e.wait_battle_menu(timeout=2400) is None:
            sc.check(f"{tag}: battle menu reached", False, why="no command menu within 2400 frames")
            break
        e.run(20)
        row = rows.setdefault(tod, [])
        rec = _bg_battle(sc, e, args, ram, tod, bg, row)
        if rec is None:
            break
        recs.append(rec)
        if not e.battle_run():
            sc.check(f"{tag}: ran from the battle", False, "still not in the field after RUN/B for 1800 frames")
            break
    sc.note(f"{len(recs)} battles in {time.time() - t0:.0f}s ({(time.time() - t0) / max(1, len(recs)):.1f}s each)")
    if ram.ok:
        sc.note(f"RAM checks on (sBattleStage at {ram.stage[0]:#x}, {ram.stage[1]} bytes, from {ram.xmap})")
    else:
        sc.note(f"RAM checks off: {ram.why}; pixels only")
    sc.check("every planned battle played", len(recs) == len(plan), f"{len(recs)} of {len(plan)}")
    if recs:
        _bg_summary(sc, recs, args.tods)
        sc.note(f"per-battle table: {write_bg_table(sc, recs)}")
    per_row = DEBUG_VIEWS + 1                # home, views 1-3, stage off
    for tod, frames in rows.items():
        for i in range(0, len(frames), BG_PER_SHEET * per_row):
            chunk = frames[i:i + BG_PER_SHEET * per_row]
            sc.sheet(chunk, f"{tod}_{i // (BG_PER_SHEET * per_row)}",
                     f"{tod}: home, debug views 1-3 (hole = uncovered share), stage off (m = mean diff, "
                     f"b = share off by > {AB_BIG})", screen="top", cols=per_row, scale=0.5, save_frames=False)


# ---- Mega Evolution brightness (chunk 2) -----------------------------------------------------

MEGA_SPECIES = 445                       # Garchomp: L+R+START gives it with Garchompite (opponent choice 0)
MEGA_MOVE_SLOT = 3                       # its Swords Dance: no damage, so the turn stays short
# Sky strips clear of both Pokemon, the HUD boxes and the text box: arena (or BG3) only
MEGA_REGIONS = [(0, 0, 256, 16), (136, 16, 256, 48)]
MEGA_RECORD = 900                        # frames after picking the move to wait for the pulse
MEGA_DIM = (-10.0, -6.0)                 # charge: the 2D planes hold -8 (half); the arena's level must be in here
MEGA_FLASH = 12.0                        # reveal: the 2D planes peak at +16 (white); the arena must reach this
MEGA_SLACK = 2.0                         # in step: levels the arena may be off the 2D range of the frames around it
MEGA_COVER = 0.9                         # least share of the regions the arena must cover in every BG0 frame
REG_BLDCNT, REG_BLDY = 0x04000050, 0x04000054
BLD_PLANE_BG3 = 1 << 3


def blend_level(e: Emu) -> int:
    """The 2D brightness the game set for BG3 (-16..16) from BLDCNT/BLDY, 0 if none."""
    cnt, _, y = struct.unpack("<3H", e.read(REG_BLDCNT, 6))
    mode = cnt >> 6 & 3
    if not cnt & BLD_PLANE_BG3 or mode not in (2, 3):
        return 0
    y = min(16, y & 0x1F)
    return y if mode == 2 else -y


def _region_pixels(img: Image.Image) -> List[tuple]:
    out: List[tuple] = []
    for box in MEGA_REGIONS:
        out.extend(img.crop(box).getdata())
    return out


def _is_backdrop(px: tuple) -> bool:
    """A pixel of the magenta backdrop marker (also dimmed or whitened up to about 9/16 by the 2D blend,
    which includes the backdrop), or black: nothing in BG0 drew there."""
    r, g, b = px[:3]
    return (abs(r - b) <= 16 and r >= 60 and g <= r * 0.6) or max(r, g, b) < 24


def brightness_level(cur: List[tuple], base: List[tuple], skip: Optional[List[bool]] = None) -> Optional[float]:
    """The DS brightness level (-16..16) that turns `base` into `cur`, per pixel on luma, median over the pixels.
    Darken: c' = c * (1 - L/16). Brighten: c' = c + (255 - c) * L/16."""
    vals = []
    for i, (p, q) in enumerate(zip(cur, base)):
        if skip is not None and skip[i]:
            continue
        c = (p[0] * 299 + p[1] * 587 + p[2] * 114) / 1000.0
        o = (q[0] * 299 + q[1] * 587 + q[2] * 114) / 1000.0
        if c <= o and o >= 32:
            vals.append(-16.0 * (1.0 - c / o))
        elif c > o and o <= 224:
            vals.append(16.0 * (c - o) / (255.0 - o))
    if not vals:
        return None
    vals.sort()
    return vals[len(vals) // 2]


def write_curve(path: pathlib.Path, rows: List[dict]) -> str:
    """Levels per frame: 2D register (grey line), 2D pixels (blue), arena pixels (orange), RAM (green)."""
    f0, f1 = rows[0]["f"], rows[-1]["f"]
    sx, top_, h = 4, 20, 256
    img = Image.new("RGB", ((f1 - f0 + 1) * sx + 60, h + 40), (24, 24, 24))
    d = ImageDraw.Draw(img)

    def y(level):
        return top_ + int((16 - level) * h / 32)
    for lv in (16, 8, 0, -8, -16):
        d.line((40, y(lv), img.size[0], y(lv)), fill=(70, 70, 70))
        d.text((4, y(lv) - 5), f"{lv:+d}", fill=(160, 160, 160))
    d.text((40, 2), "grey: 2D register  blue: 2D pixels  orange: arena pixels  green: RAM brightness",
           fill=(220, 220, 220))
    prev = None
    for r in rows:
        x = 40 + (r["f"] - f0) * sx
        pt = (x, y(r["reg"]))
        if prev:
            d.line((prev, pt), fill=(150, 150, 150))
        prev = pt
        for key, col in (("px2d", (80, 140, 255)), ("arena", (255, 150, 40)), ("ram", (60, 220, 60))):
            if r.get(key) is not None:
                d.ellipse((x - 2, y(r[key]) - 2, x + 2, y(r[key]) + 2), fill=col)
    img.save(path)
    return str(path)


def _give_mega(sc: Scenario, e: Emu, args) -> bool:
    from make_save import PARTY_OFFSET, PK4_PARTY_SIZE, newest_partition
    raw = pathlib.Path(args.sav).read_bytes()
    base = newest_partition(raw)
    try:
        e.find_party(raw[base + PARTY_OFFSET:base + PARTY_OFFSET + PK4_PARTY_SIZE])
    except RuntimeError as exc:
        sc.check("party located in RAM", False, str(exc))
        return False
    panel: List[Frame] = []
    if hold_overlay(e, threshold=0.10) is None:
        _no_combo(sc, "L+R panel opened", "the overworld quick-battle panel")
        return False
    tap_held(e, "START")
    e.run(10)
    e.snap("after L+R+START", panel)
    e.release("L+R")
    e.run(30)
    party = e.party_species()
    idx = next((i for i, p in enumerate(party) if p["species"] == MEGA_SPECIES), None)
    if not sc.check("L+R+START gave the Mega Pokemon", idx is not None,
                    f"party species {[p['species'] for p in party]}",
                    why=f"no species {MEGA_SPECIES} (Garchomp) in the party"):
        sc.sheet(panel, "panel", "L+R+START", screen="top", cols=2, scale=1.0)
        return False
    if idx:
        e.swap_party(0, idx)             # the battle leads with slot 0
    lead = e.party_species()[0]
    return sc.check("Mega Pokemon leads the party", lead["species"] == MEGA_SPECIES,
                    f"slot 0: species {lead['species']}, item {lead['item']}, moves {lead['moves']}")


def _mega_measure(e: Emu, ram: StageRam, base_bg0: List[tuple], base_2d: List[tuple], f: int, mode: int,
                  keep: bool) -> dict:
    """One frame of the pulse recording, in one of three renders (mode 0 full, 1 BG0 only, 2 2D only)."""
    if mode == 0:
        e.run(1)
        img = e.screens()
    else:
        img = e.render_layers(LAYER_BG0 if mode == 1 else LAYERS_2D, marker=mode == 1)
    row: dict = {"f": f, "mode": mode, "reg": blend_level(e)}
    st = ram.read() if ram.ok else None
    if st is not None:
        row["suppressed"], row["visible"] = st["suppressed"], st["visible"]
        if ram.has_brightness:
            row["ram"] = st["brightness"]
    px = _region_pixels(img)
    if mode == 1:
        skip = [_is_backdrop(p) for p in px]
        row["cover"] = 1.0 - sum(skip) / float(len(skip))
        # Only where the arena really covers the regions: a strongly whitened backdrop no longer
        # looks magenta and would otherwise be measured as arena
        drawn = row["cover"] >= MEGA_COVER and row.get("visible", 1) == 1
        row["arena"] = brightness_level(px, base_bg0, skip) if drawn else None
    elif mode == 2:
        row["px2d"] = brightness_level(px, base_2d)
    if keep:
        row["img"] = top(img)
    return row


def sc_mega(sc: Scenario, e: Emu, args) -> None:
    if not boot(sc, e):
        return
    ram = StageRam(e, find_xmap(args))
    if not _give_mega(sc, e, args):
        return
    panel: List[Frame] = []
    # Plain at day: bright sky in the measured regions, the same art every run
    started = _qb_start(sc, e, "A", QB_PLAIN, 0, panel, "plain", tod_taps=TODS.index("day"))
    if not started or e.wait_battle_menu(timeout=2400) is None:
        sc.check("plain: battle menu reached", False, "no command menu")
        sc.sheet(panel, "panel", "L+R panel", screen="top", cols=4, scale=1.0)
        return
    e.run(30)
    st = ram.read()
    if st is not None and not ram.validate(st):
        sc.note(ram.why)
    base_bg0 = _region_pixels(e.render_layers(LAYER_BG0, marker=True))
    base_2d = _region_pixels(e.render_layers(LAYERS_2D))
    cover0 = 1.0 - sum(map(_is_backdrop, base_bg0)) / float(len(base_bg0))
    arena_up = cover0 >= MEGA_COVER and (not ram.ok or ram.read()["visible"] == 1)
    sc.check("arena drawn before the Mega Evolution", arena_up,
             f"BG0 covers {cover0:.0%} of the sky regions" + (f", RAM {ram.read()}" if ram.ok else ""),
             why="no arena to measure (the stage is off or this background has none)")
    shots: List[Frame] = [e.snap("menu")]
    e.touch(*BTN_FIGHT, after=40)
    if not sc.check("move list opened", e.move_list_up(), why="touching FIGHT did not open the move list"):
        sc.sheet(shots + [e.snap("after FIGHT")], "mega", "command menu / after FIGHT", cols=2, scale=0.75)
        return
    ml = bottom(e.screens())
    e.touch(*BTN_MEGA, after=20)
    shots.append(e.snap("MEGA touched"))
    toggled = diff_fraction(ml.crop((0, 150, 128, 192)), bottom(e.screens()).crop((0, 150, 128, 192))) > 0.05
    sc.check("MEGA button toggled", toggled, why="the MEGA button did not change: no Key Stone / Mega Stone, "
             "or the button is not at the expected place", warn_only=True)
    e.touch(*MOVE_SLOTS[MEGA_MOVE_SLOT], after=2)
    rows: List[dict] = []
    recent: List[dict] = []
    start, end = e.frame, None
    while e.frame - start < MEGA_RECORD:
        f = e.frame - start
        r = _mega_measure(e, ram, base_bg0, base_2d, f, f % 3, True)
        live = r["reg"] != 0 or (r.get("suppressed", 0) & SUPPRESS_BRIGHTNESS)
        if live or rows:
            if not rows:
                rows.extend(recent)          # a few frames of lead-in
            rows.append(r)
            if live:
                end = None
            elif end is None:
                end = f
            elif f - end > 30:
                break
        else:
            r.pop("img", None)
            recent = (recent + [r])[-6:]
    if not sc.check("Affine Pulse seen", bool(rows), f"2D brightness set for {len(rows)} frames" if rows else
                    f"no 2D brightness blend within {MEGA_RECORD} frames of picking the move: the Mega Evolution "
                    "did not happen"):
        sc.sheet(shots + [e.snap("end")], "mega", "menu / MEGA / end", cols=3, scale=0.75)
        return
    for r in rows:
        r.pop("img", None) if r["mode"] == 2 else None
    window = [r for r in rows if r["reg"] != 0]
    regs = {r["f"]: r["reg"] for r in rows}
    sc.note(f"pulse: 2D brightness from frame {window[0]['f']} to {window[-1]['f']}, "
            f"min {min(regs.values())}, max {max(regs.values())}")

    # Stage visible: RAM never suppressed for BRIGHTNESS and visible, pixels cover the regions (the
    # magenta test holds up to about 9/16 of 2D brightness, see _is_backdrop)
    bg0 = [r for r in rows if r["mode"] == 1 and window[0]["f"] <= r["f"] <= window[-1]["f"]]
    judged = [r for r in bg0 if abs(r["reg"]) <= 9]
    low = [r for r in judged if r["cover"] < MEGA_COVER]
    detail = f"BG0 covers the sky regions in {len(judged) - len(low)} of {len(judged)} frames"
    ram_bad = []
    if ram.ok:
        ram_bad = [r["f"] for r in rows if r.get("suppressed", 0) & SUPPRESS_BRIGHTNESS or r.get("visible") == 0]
        detail += f"; RAM: suppressed for brightness / not visible in {len(ram_bad)} of {len(rows)} frames"
    visible = not low and not ram_bad
    sc.check("stage stays visible through the pulse", visible, detail,
             why="the arena is hidden during the Mega Evolution (BattleStage_Suppress(BRIGHTNESS)); "
                 "the fog brightness (format v2) should replace the suppression")

    # Levels against the 2D planes
    measured = [r for r in bg0 if r.get("arena") is not None]
    px2d = [r for r in rows if r.get("px2d") is not None]
    err2d = [abs(r["px2d"] - r["reg"]) for r in px2d]
    if err2d:
        sc.note(f"method check: 2D pixel level vs BLDY register, mean error {sum(err2d) / len(err2d):.2f} "
                f"over {len(err2d)} frames (the arena is measured the same way)")
    if not measured:
        sc.warn("arena dims during the charge", "not measured: the arena was not drawn")
        sc.warn("arena flashes white on the reveal", "not measured: the arena was not drawn")
    else:
        dims = [r for r in measured if r["reg"] < 0 and all(regs.get(r["f"] + k, r["reg"]) == r["reg"]
                                                            for k in (-2, -1, 1, 2))]
        plateau = [r["arena"] for r in dims if r["reg"] == min(regs.values())]
        lvl = sorted(plateau)[len(plateau) // 2] if plateau else None
        sc.check("arena dims during the charge", lvl is not None and MEGA_DIM[0] <= lvl <= MEGA_DIM[1],
                 f"arena level {lvl:+.1f} (median of {len(plateau)} frames) while the 2D planes hold "
                 f"{min(regs.values())}" if lvl is not None else "no steady charge frames measured",
                 why=f"expected {MEGA_DIM[0]:+.0f}..{MEGA_DIM[1]:+.0f} (half brightness at -8)")
        flash = max((r["arena"] for r in measured if r["reg"] > 0), default=None)
        sc.check("arena flashes white on the reveal", flash is not None and flash >= MEGA_FLASH,
                 f"arena peaks at {flash:+.1f} while the 2D planes peak at {max(regs.values())}"
                 if flash is not None else "no reveal frames measured",
                 why=f"expected at least {MEGA_FLASH:+.0f}")
        off = []
        for r in measured:
            near = [regs[r["f"] + k] for k in range(-2, 3) if r["f"] + k in regs]
            if not min(near) - MEGA_SLACK <= r["arena"] <= max(near) + MEGA_SLACK:
                off.append(f"@{r['f']} arena {r['arena']:+.1f} vs 2D {min(near)}..{max(near)}")
        share = 1.0 - len(off) / float(len(measured))
        sc.check("arena brightness in step with the 2D planes", not off,
                 f"{share:.0%} of {len(measured)} BG0 frames within {MEGA_SLACK:.0f} levels of the 2D level "
                 f"of the frames +-2 around them" + (f"; off: {', '.join(off[:6])}" if off else ""),
                 warn_only=share >= 0.8)
    if ram.has_brightness:
        bad = [r["f"] for r in rows if r.get("ram") is not None and r["ram"] != r["reg"]
               and regs.get(r["f"] - 1) != r["ram"] and regs.get(r["f"] + 1) != r["ram"]]
        sc.check("RAM brightness follows the 2D blend", not bad,
                 f"sBattleStage.brightness differs from BLDY (+-1 frame) in {len(bad)} of {len(rows)} frames",
                 warn_only=True)
    else:
        sc.note("sBattleStage has no brightness field (format v1 build): RAM curve not checked")
    curve = write_curve(sc.dir / "mega_curve.png", rows)
    sc.note(f"level curve: {curve}")

    def lab(r):
        return f"2D{r['reg']:+d}" + (f" a{r['arena']:+.0f}" if r.get("arena") is not None else "")
    arena_at = {r["f"]: r.get("arena") for r in rows if r["mode"] == 1}
    full = []
    for r in rows:
        if r["mode"] == 0 and "img" in r:
            a = arena_at.get(r["f"] + 1)
            full.append(Frame(f"2D{r['reg']:+d}" + (f" a{a:+.0f}" if a is not None else ""), r["f"], r["img"]))
    sc.sheet(full, "pulse", "full frames through the pulse (2D = register level, a = arena level of the next "
             "BG0 frame)", screen="top", cols=8, scale=0.5)
    sc.sheet([Frame(lab(r), r["f"], r["img"]) for r in rows if r["mode"] == 1 and "img" in r], "pulse_bg0",
             "BG0 only (arena, sprites, particles; magenta = nothing drawn)", screen="top", cols=8, scale=0.5)
    sc.sheet(shots, "mega", "command menu / move list with MEGA touched", cols=2, scale=0.75)
    _finish(sc, e)


# ---- lit, deformable sprites (chunk 3) -------------------------------------------------------

# Where each mon is looked for on the top screen (inside SCENE), and the box used if the marker trick
# finds nothing there. The enemy stands at about (192, 70), the player's back sprite at about (64, 120).
SPRITE_WINDOWS = {"enemy": (136, 8, 256, 120), "player": (0, 40, 136, 144)}
SPRITE_FALLBACK = {"enemy": (152, 30, 232, 110), "player": (24, 72, 112, 144)}
BOX_PAD = 4                              # pixels added around the measured sprite boxes
BOX_MIN, BOX_MAX = 16, 120               # sane box width/height
IDLE_RECORD, IDLE_EVERY = 180, 6         # 3 s of command-menu idle, sampled every 6 frames
BREATHE_MIN = 0.01                       # least share of the enemy box that breathing must change in 3 s
REST_PASS, REST_WARN = 0.002, 0.01       # ... while the scene outside the boxes (HUD masked) stays within this
FREEZE_STILL = 0.002                     # FREEZE_IDLE: the enemy box changes at most this much in 60 frames
IDLE_ADVANCE_MIN = 30                    # idleFrames must advance this much in 180 frames
IDLE_STOP_MAX = 2                        # idleFrames may advance this much while a tester move plays
BLOB_DARKER = 8                          # a ground pixel counts as darker by more than this (luma) ...
BLOB_PIXELS = 30                         # ... and at least this many must be, with the mean luma lower
BLOB_BELOW = 10                          # the "under the mon" region reaches this far below the box
NIGHT_TINT_MIN = 4.0                     # night: mean max-channel difference on the mon's pixels vs stage off
NIGHT_BLACK = (24.0, 0.35)               # ... and not black: mean brightness >= 24 and >= 35% of stage off
SPRITE_COUNT = 2                         # singles: spriteMeshes and blobShadows at the home pose


def _marker_mask(img: Image.Image) -> Image.Image:
    """L image, 255 where a BG0-only marker render drew something (not the magenta backdrop)."""
    r, g, b = img.convert("RGB").split()
    hit = ImageChops.multiply(ImageChops.multiply(r.point(lambda v: 255 if v >= 240 else 0),
                                                  g.point(lambda v: 255 if v <= 8 else 0)),
                              b.point(lambda v: 255 if v >= 240 else 0))
    return ImageChops.invert(hit)


def sprite_boxes(e: Emu, n: int = 12, every: int = 5) -> tuple:
    """With the stage OFF only the sprites and their shadows draw on BG0, so the union of a few
    BG0-only marker renders (spanning the idle bob) is the sprite mask. Returns ({mon: box}, mask, found):
    boxes in top-screen coordinates (inside SCENE), `found` the mons actually measured (the others get
    SPRITE_FALLBACK)."""
    mask = None
    for _ in range(n):
        m = _marker_mask(top(e.render_layers(LAYER_BG0, marker=True)).crop(SCENE))
        mask = m if mask is None else ImageChops.lighter(mask, m)
        e.run(every)
    boxes, found = {}, []
    for mon, win in SPRITE_WINDOWS.items():
        bb = mask.crop(win).getbbox()
        if bb and BOX_MIN <= bb[2] - bb[0] <= BOX_MAX and BOX_MIN <= bb[3] - bb[1] <= BOX_MAX:
            boxes[mon] = (max(0, win[0] + bb[0] - BOX_PAD), max(0, win[1] + bb[1] - BOX_PAD),
                          min(SCENE[2], win[0] + bb[2] + BOX_PAD), min(SCENE[3], win[1] + bb[3] + BOX_PAD))
            found.append(mon)
        else:
            boxes[mon] = SPRITE_FALLBACK[mon]
    return boxes, mask, found


def outside_boxes(img: Image.Image, boxes: dict) -> Image.Image:
    """scene() with the sprite boxes blacked out too."""
    out = scene(img)
    for box in boxes.values():
        out.paste((0, 0, 0), box)
    return out


def box_change(frames: List[Image.Image], box: tuple) -> float:
    """Largest share of the box that differs from the first frame."""
    first = frames[0].crop(box)
    return max((diff_fraction(first, f.crop(box)) for f in frames[1:]), default=0.0)


def box_motion(frames: List[Image.Image], box: tuple) -> float:
    """Mean share of the box that differs from the first frame: breathing moves the sprite in most frames,
    a classic sprite's own brief idle changes (a blink) only in a few."""
    first = frames[0].crop(box)
    ds = [diff_fraction(first, f.crop(box)) for f in frames[1:]]
    return sum(ds) / len(ds) if ds else 0.0


def box_novelty(frames: List[Image.Image], ref: List[Image.Image], box: tuple) -> float:
    """Median, over `frames`, of the share of the box that differs from the closest `ref` frame. A
    classic sprite cycles through a few idle states (a blink, the player's bob), which all show up
    in a 3 s reference recording, so this is about 0 whatever the phase; breathing squashes the
    sprite into shapes the classic recording never shows, in most frames."""
    refs = [r.crop(box) for r in ref]
    ds = sorted(min(diff_fraction(r, f.crop(box)) for r in refs) for f in frames) if refs else []
    return ds[len(ds) // 2] if ds else 0.0


def _luma(img: Image.Image) -> List[int]:
    return list(img.convert("L").getdata())


def under_box(box: tuple) -> tuple:
    """The ground under a mon: the lower quarter of its box and BLOB_BELOW pixels below it."""
    x0, y0, x1, y1 = box
    return (x0, y1 - (y1 - y0) // 4, x1, min(SCENE[3], y1 + BLOB_BELOW))


def masked_stats(on: Image.Image, off: Image.Image, mask: Image.Image) -> dict:
    """Over the mask's pixels: mean max-channel difference ON vs OFF, and the mean brightness of each."""
    d = list(pixel_diff(on, off)["map"].getdata())
    idx = [i for i, v in enumerate(mask.getdata()) if v]
    if not idx:
        return {"n": 0, "diff": 0.0, "on": 0.0, "off": 0.0}
    lon, loff = _luma(on), _luma(off)
    k = float(len(idx))
    return {"n": len(idx), "diff": sum(d[i] for i in idx) / k,
            "on": sum(lon[i] for i in idx) / k, "off": sum(loff[i] for i in idx) / k}


def crop_sheet(cells: List[tuple], path: pathlib.Path, title: str, cols: int, zoom: int = 2) -> str:
    """A labelled grid of (label, image) crops of any size, each drawn `zoom` times as big."""
    cw = max(i.size[0] for _, i in cells) * zoom
    ch = max(i.size[1] for _, i in cells) * zoom
    lab, head = 12, 16
    rows = (len(cells) + cols - 1) // cols
    out = Image.new("RGB", (max(cols * (cw + 4) + 4, 8 * len(title)), head + rows * (ch + lab + 4) + 4), (32, 32, 32))
    d = ImageDraw.Draw(out)
    d.text((4, 2), title, fill=(230, 230, 230))
    for n, (label, img) in enumerate(cells):
        x, y = 4 + (n % cols) * (cw + 4), head + (n // cols) * (ch + lab + 4)
        d.text((x, y), label, fill=(230, 230, 120))
        out.paste(img.convert("RGB").resize((img.size[0] * zoom, img.size[1] * zoom), Image.NEAREST), (x, y + lab))
    out.save(path)
    return str(path)


def _crop_sheet(sc: Scenario, cells: List[tuple], key: str, title: str, cols: int, zoom: int = 2) -> Optional[str]:
    if not cells:
        return None
    path = crop_sheet(cells, sc.dir / f"sheet_{key}.png", f"{sc.name}: {title}", cols, zoom)
    sc.sheets.append({"sheet": path, "title": title, "frames": len(cells), "screen": "top (crops)"})
    return path


def _play_polled(e: Emu, ov: Overlay, ram: StageRam, key: str, frames: int, label: str, live: bool) -> tuple:
    """Overlay.play that also reads sBattleStage on every frame (when `live`).
    Returns (frames every 3, finished_after or None, [(frame, idleFrames, wobbleMask)])."""
    start = e.frame
    e.hold(key, 6, 0)
    e.release("L+R")
    anim: List[Frame] = []
    polls: List[tuple] = []
    while e.frame - start < frames:
        e.run(1)
        t = e.frame - start
        if live:
            st = ram.read()
            polls.append((t, st["idleFrames"], st["wobbleMask"]))
        if t % 3 == 0:
            f = e.snap(f"{label}+{t}")
            anim.append(f)
            if t >= 12 and not ov.up(f.img):
                break
    return anim, (e.frame - start if not ov.up() else None), polls


def _turn_polled(sc: Scenario, e: Emu, args, ram: StageRam, live: bool, what: str) -> tuple:
    """A real False Swipe turn (ours and the enemy's) with wobbleMask read every frame.
    Returns (menu back, OR of wobbleMask, frames every 3)."""
    if not sc.check(f"{what}: FIGHT opened the move list", e.battle_fight(FALSE_SWIPE_SLOT),
                    why="touching FIGHT did not open the move list"):
        return False, 0, []
    start, mask = e.frame, 0
    anim: List[Frame] = []
    while e.frame - start < args.max_anim_frames:
        e.run(1)
        if live:
            mask |= ram.field("wobbleMask") or 0
        if (e.frame - start) % 3 == 0:
            f = e.snap(f"turn+{e.frame - start}")
            anim.append(f)
            if e.frame - start >= 60 and e.battle_menu_up(f.img):
                break
    back = sc.check(f"{what}: menu returned after the turn", e.battle_menu_up(),
                    why=f"no command menu within {args.max_anim_frames} frames")
    return back, mask, anim


def sc_sprite_life(sc: Scenario, e: Emu, args) -> None:
    """Chunk 3 (docs/living_battle_stage/sprites.md): mesh sprites, breathing, blob shadows, the
    CLASSIC_SPRITES path, the night tint and hit wobble, on the Plain battle at day and at night.
    RAM checks need a ROM whose sBattleStage has the debug fields (>= 52 bytes in the xMAP); without
    them they are skipped with a note, and the pixel checks of the new features only WARN."""
    if not _plain_battle(sc, e, args.stage_tod):
        return
    tod = args.stage_tod
    grade_tod = "day" if tod == "clock" else tod
    ram = StageRam(e, find_xmap(args))
    live = ram.set_flags(0)
    if live:
        sc.note(f"RAM checks on: sBattleStage at {ram.stage[0]:#x}, {ram.stage[1]} bytes, from {ram.xmap}; "
                f"read {ram.read()}")
    else:
        sc.note(f"RAM half skipped: {ram.sprite_why or ram.why}. Checks that need the debug fields or a "
                "writable debugFlags are skipped; the pixel checks of the new features only WARN.")
    old_rom = "no sprite debug fields in this build (expected on a ROM from before chunk 3)"

    def feature(name: str, ok: bool, detail: str, why: str) -> bool:
        """A pixel check of a chunk 3 feature: FAIL if the ROM has the debug fields, else WARN."""
        return sc.grade(name, "PASS" if ok else ("FAIL" if live else "WARN"), detail,
                        why=why if live else f"{why}; {old_rom}")

    skipped: List[str] = []
    ov = Overlay(e)
    shots: List[Frame] = [e.snap("menu (stage ON)")]

    # -- mesh and blob counts, 3 s of idle, idleFrames
    if live:
        st = ram.read()
        sc.check("spriteMeshes == 2 at the command menu", st["spriteMeshes"] == SPRITE_COUNT,
                 f"spriteMeshes {st['spriteMeshes']}", why="the mons are not drawn as meshes")
        sc.check("blob shadows show (blobShadows == 2)", st["blobShadows"] == SPRITE_COUNT,
                 f"blobShadows {st['blobShadows']}")
    else:
        skipped += ["spriteMeshes == 2", "blobShadows == 2", "idleFrames advances"]
    if live:
        ram.set_flags(NO_BLOB_SHADOWS)   # breathing is judged against the classic frames: blobs would differ too
    i0 = ram.field("idleFrames") if live else 0
    idle = [top(f.img) for f in e.record(IDLE_RECORD, every=IDLE_EVERY, label="idle")]
    if live:
        i1 = ram.field("idleFrames")
        sc.check("idleFrames advances at the command menu", i1 - i0 >= IDLE_ADVANCE_MIN,
                 f"+{i1 - i0} over {IDLE_RECORD} frames (needs >= {IDLE_ADVANCE_MIN})", why="breathing did not advance")

    # -- stage OFF: sprite boxes (magenta trick) and the classic frames
    if not ov.show():
        _no_combo(sc, "L+R overlay shown", "the in-battle move tester / stage toggle")
        run_away(sc, e)
        return
    if not _toggle_stage(sc, e, ov, "stage OFF", shots):
        run_away(sc, e)
        return
    boxes, mask, found = sprite_boxes(e)
    mask.save(sc.dir / "sprite_mask_day.png")
    sc.check("sprite boxes measured (stage OFF, BG0 marker render)", len(found) == 2,
             ", ".join(f"{m} {boxes[m]}" for m in boxes), warn_only=True,
             why=f"not found: {[m for m in boxes if m not in found]}, using the fallback box")
    off = [top(f.img) for f in e.record(IDLE_RECORD, every=IDLE_EVERY, label="idle off")]
    shots.append(e.snap("stage OFF"))
    _toggle_stage(sc, e, ov, "stage ON", shots)
    shots.append(e.snap("stage ON again"))

    # -- breathing in pixels: the enemy box changes more than in the classic look (whose sprites have
    # their own small idle changes), the rest of the scene does not. The classic player (and its
    # healthbar) bob at the command menu, so only the enemy box is judged.
    eb, pb = boxes["enemy"], boxes["player"]
    nov_e, nov_p = box_novelty(idle, off, eb), box_novelty(idle, off, pb)
    feature("breathing: the enemy's box takes shapes the classic sprite never shows", nov_e >= BREATHE_MIN,
            f"median {nov_e:.2%} of the enemy box differs from the closest of the {len(off)} stage-off idle frames "
            f"(needs {BREATHE_MIN:.0%}); player box {nov_p:.2%}; for reference, change from the first frame: enemy "
            f"mean {box_motion(idle, eb):.2%} on, {box_motion(off, eb):.2%} off, player mean {box_motion(idle, pb):.2%} "
            f"on, {box_motion(off, pb):.2%} off (the classic sprites blink and bob on their own)",
            why="the enemy does not breathe")
    rest = max((diff_fraction(outside_boxes(idle[0], boxes), outside_boxes(i, boxes)) for i in idle[1:]),
               default=0.0)
    sc.check("breathing: the scene outside the sprite boxes stays still", rest <= REST_PASS,
             f"up to {rest:.2%} of the scene outside the boxes (HUD masked) changes over 3 s "
             f"(PASS <= {REST_PASS:.1%}, WARN <= {REST_WARN:.0%})",
             warn_only=rest <= REST_WARN, why="something besides the mons moves at the command menu")

    day_on: List[Image.Image]
    if live:
        # -- FREEZE_IDLE stops breathing
        ram.set_flags(FREEZE_IDLE)
        a = ram.field("idleFrames")
        frozen = [top(f.img) for f in e.record(60, every=6, label="frozen")]
        b = ram.field("idleFrames")
        sc.check("FREEZE_IDLE stops idleFrames", b == a, f"idleFrames {a} -> {b} over 60 frames")
        still, classic_most = box_change(frozen, eb), box_change(off, eb)
        sc.check("FREEZE_IDLE: the enemy's box is as still as in the classic look", still <= classic_most + FREEZE_STILL,
                 f"up to {still:.2%} of the enemy box changes over 60 frames (classic look: up to "
                 f"{classic_most:.2%} over {IDLE_RECORD}; allowed {FREEZE_STILL:.1%} more)")

        # -- blob shadows: darker under each mon than with NO_BLOB_SHADOWS
        with_blob = idle_samples(e, n=8, every=4)
        ram.set_flags(FREEZE_IDLE | NO_BLOB_SHADOWS)
        n_blob = ram.field("blobShadows")
        sc.check("NO_BLOB_SHADOWS turns the blobs off", n_blob == 0, f"blobShadows {n_blob}")
        day_on = idle_samples(e, n=8, every=4)
        blob_cells = []
        for mon in ("enemy", "player"):
            ub = under_box(boxes[mon])
            a_img, b_img = best_pair([i.crop(ub) for i in with_blob], [i.crop(ub) for i in day_on])
            la, lb = _luma(a_img), _luma(b_img)
            darker = sum(1 for p, q in zip(la, lb) if q - p > BLOB_DARKER)
            drop = (sum(lb) - sum(la)) / float(max(1, len(la)))
            sc.check(f"blob shadow darkens the ground under the {mon}", darker >= BLOB_PIXELS and drop > 0,
                     f"region {ub}: {darker} pixels darker by more than {BLOB_DARKER} with blobs than with "
                     f"NO_BLOB_SHADOWS (needs {BLOB_PIXELS}), mean luma {drop:+.1f} darker")
            blob_cells += [(f"{mon} blob ON", a_img), (f"{mon} blob OFF", b_img)]
        _crop_sheet(sc, blob_cells, "blobs", "ground under each mon with and without blob shadows (FREEZE_IDLE)",
                    cols=4, zoom=3)

        # -- CLASSIC_SPRITES: the sprites match the stage-off frames
        ram.set_flags(FREEZE_IDLE | NO_BLOB_SHADOWS | CLASSIC_SPRITES)
        meshes = ram.field("spriteMeshes")
        sc.check("CLASSIC_SPRITES draws no meshes", meshes == 0, f"spriteMeshes {meshes}")
        classic = idle_samples(e, n=12, every=3)
        for mon in ("enemy", "player"):
            box = boxes[mon]
            a_img, b_img = best_pair([i.crop(box) for i in classic], [i.crop(box) for i in off])
            d = pixel_diff(a_img, b_img)
            sc.grade(f"CLASSIC_SPRITES: the {mon} matches the stage-off frame", home_grade(d, grade_tod),
                     f"box {box}: {diff_detail(d)}", why=limits_text(grade_tod))
        ram.set_flags(0)
    else:
        skipped += ["FREEZE_IDLE stops idleFrames and the enemy's box",
                    "blob shadows darken the ground (needs NO_BLOB_SHADOWS)",
                    "CLASSIC_SPRITES matches stage off (needs the flag)"]
        day_on = idle_samples(e, n=8, every=4)

    # -- a tester move with the mons alive: idleFrames stops while it plays; wobble
    wobble = 0
    if not ov.up() and not ov.show():
        sc.check("overlay back for the tester Pound", False, "holding L+R did not bring the overlay back")
        return
    anim, done, polls = _play_polled(e, ov, ram, "A", args.anim_frames, "pound", live)
    if froze(sc, e, anim, "playing Pound (L+R+A)"):
        return
    sc.sheet(anim, "pound", "tester Pound (player->enemy), every 3 frames (deduped)", screen="top",
             dedupe_screen="top")
    if not sc.check("tester Pound finished", done is not None,
                    f"overlay hidden {done} frames after L+R+A" if done is not None else "overlay still up"):
        return
    if live:
        during = [p for p in polls if 10 <= p[0] <= done - 6]
        adv = during[-1][1] - during[0][1] if len(during) > 1 else 0
        span = f"frames {during[0][0]}..{during[-1][0]}" if during else "no frames"
        sc.check("idleFrames stops during a tester move", len(during) > 1 and adv <= IDLE_STOP_MAX,
                 f"+{adv} over {span} of the animation (at most {IDLE_STOP_MAX})",
                 why="breathing kept running during the move")
        for p in polls:
            wobble |= p[2]
        sc.note(f"wobbleMask during the tester Pound: {wobble:#x}")
    else:
        skipped.append("idleFrames stops during a tester move")
    e.run(90)

    # -- the sprite moves on the arena (move_tester plays them in the forest, where there is no arena and so
    # no mesh): each must finish and bring the normal look back, and whatever look it leaves must match the
    # classic look of the same state (stage toggled off). Sprites at rest and the classic shadow, so both
    # comparisons are exact at day.
    stuck = False
    if args.sprite_moves:
        _sprite_flags(sc, e, args, FREEZE_IDLE | NO_BLOB_SHADOWS, ram)
        base = e.record(60, every=5, label="idle")
        baseline = ([scene(f.img) for f in base], [text_box(f.img) for f in base])
        overlays: List[Frame] = []
        after: List[Frame] = []
        pairs: List[Frame] = []
        cur = MOVE_ID_POUND
        for mid in args.sprite_moves:
            tag = f"arena move {mid:03d}"
            if not _tester_move(sc, e, args, ov, baseline, cur, mid, "fwd", "A", tag, overlays, after, restore=True):
                stuck = True
                break
            cur = mid
            if not _classic_match(sc, e, ov, tag, grade_tod, pairs):
                stuck = True
                break
        sc.sheet(pairs, "moves_on_off", "after each sprite move: stage ON | stage OFF (best-aligned pair)",
                 screen="top", cols=4, scale=0.75)
        sc.sheet(overlays, "overlays", "L+R overlay before each sprite move (check the move name)",
                 screen="top", cols=5, scale=0.5)
        sc.sheet(after, "after", "10 and 90 frames after each sprite move (normal look expected at +90)",
                 screen="top", cols=4, scale=1.0)
        if stuck:
            sc.note("Stopped after the sprite moves: the command menu is stuck or frozen.")
            return
        if live:
            ram.set_flags(0)
        if not e.battle_menu_up():
            e.wait_battle_menu(timeout=1800, advance_text=True)

    # -- a real damaging turn: wobbleMask
    back, turn_mask, turn = _turn_polled(sc, e, args, ram, live, "False Swipe turn")
    sc.sheet(turn, "turn", "False Swipe + enemy turn, every 3 frames (deduped)", screen="top", dedupe_screen="top")
    if live:
        sc.check("wobble: a damaging move sets wobbleMask", (wobble | turn_mask) != 0,
                 f"tester Pound {wobble:#x}, False Swipe turn {turn_mask:#x} (bit n = battler n)",
                 why="no battler wobbled on a hit")
    else:
        skipped.append("wobble sets wobbleMask")
    sc.sheet(shots, "states", "stage ON / OFF / ON at the command menu", screen="top", cols=4, scale=0.5)
    idle_cells = [(f"{mon[0]} +{k * IDLE_EVERY}", idle[k].crop(boxes[mon]))
                  for mon in ("enemy", "player") for k in range(0, len(idle), 3)]
    _crop_sheet(sc, idle_cells, "idle", f"idle over {IDLE_RECORD} frames, row 1 enemy, row 2 player "
                "(+N = frames; breathing should show)", cols=(len(idle) + 2) // 3)
    crops = {("day", "ON"): (day_on, boxes), ("day", "OFF"): (off, boxes)}
    if back and run_away(sc, e):
        _night(sc, e, args, ram, tod, live, feature, boxes, crops, shots)
    cells = []
    for mon in ("enemy", "player"):
        for key in (("day", "ON"), ("day", "OFF"), ("night", "ON"), ("night", "OFF")):
            if key in crops:
                imgs, bxs = crops[key]
                cells.append((f"{mon} {key[0]} {key[1]}", imgs[0].crop(bxs[mon])))
    _crop_sheet(sc, cells, "day_night", "the mons with the stage ON (FREEZE_IDLE|NO_BLOB_SHADOWS where "
                "supported) and OFF, at day and at night", cols=4)
    if skipped:
        sc.note("SKIPPED (need the sprite debug fields): " + "; ".join(skipped))


def _classic_match(sc: Scenario, e: Emu, ov: Overlay, tag: str, tod: str, pairs: List[Frame]) -> bool:
    """After a tester move: the scene with the stage on vs the same state toggled off (the classic look),
    graded like stage_ab (AB_LIMITS). Leaves the stage on. False if the stage could not be toggled."""
    on = idle_samples(e, n=8, every=3)
    toggled: List[Frame] = []
    if not _toggle_stage(sc, e, ov, f"{tag}: stage OFF", toggled):
        return False
    off = idle_samples(e, n=8, every=3)
    if not _toggle_stage(sc, e, ov, f"{tag}: stage ON", toggled):
        return False
    a, b = best_pair([scene(i) for i in on], [scene(i) for i in off])
    d = pixel_diff(a, b)
    status = home_grade(d, tod)
    if status != "PASS":
        detail = f" (ON | OFF | heat: {write_heatmap(a, b, d, sc.dir / (tag.replace(' ', '_') + '_on_off.png'))})"
    else:
        detail = ""
    sc.grade(f"{tag}: the sprites match the classic look of the same state", status,
             f"scene (HUD masked): {diff_detail(d)}{detail}",
             why=limits_text(tod) + "; the mesh does not follow what the move did to the sprite")
    pairs += [Frame(f"{tag} ON", e.frame, a), Frame(f"{tag} OFF", e.frame, b)]
    return True


def _night(sc: Scenario, e: Emu, args, ram: StageRam, tod: str, live: bool, feature: Callable,
           boxes: dict, crops: dict, shots: List[Frame]) -> None:
    """sprite_life's night battle: the mons must be tinted (differ from stage off) and not black."""
    cur = {"bg": STAGE_ENTRY, "tod": TODS.index(tod)}
    started = _select_entry(sc, e, ram, cur, STAGE_ENTRY, "night", "night")
    if not started or e.wait_battle_menu(timeout=2400) is None:
        sc.check("night: battle menu reached", False, why="the night Plain battle did not start")
        return
    e.run(30)
    # The tint alone: sprites at rest and the classic shadow
    if ram.set_flags(FREEZE_IDLE | NO_BLOB_SHADOWS):
        sc.check("night: spriteMeshes == 2", ram.field("spriteMeshes") == SPRITE_COUNT,
                 f"spriteMeshes {ram.field('spriteMeshes')}")
    on = idle_samples(e, n=12, every=3)
    shots.append(e.snap("night stage ON"))
    ov = Overlay(e)
    if not ov.show() or not _toggle_stage(sc, e, ov, "night: stage OFF", shots):
        sc.check("night: stage switched off", False, why="L+R+SELECT did not work in the night battle")
        _finish(sc, e)
        return
    nboxes, nmask, found = sprite_boxes(e)
    if len(found) < 2:
        nboxes = boxes
    off = idle_samples(e, n=12, every=3)
    shots.append(e.snap("night stage OFF"))
    crops[("night", "ON")], crops[("night", "OFF")] = (on, nboxes), (off, nboxes)
    for mon in ("enemy", "player"):
        box = nboxes[mon]
        a_img, b_img = best_pair([i.crop(box) for i in on], [i.crop(box) for i in off])
        ms = masked_stats(a_img, b_img, nmask.crop(box))
        feature(f"night: the {mon} is tinted (differs from stage off)", ms["diff"] >= NIGHT_TINT_MIN,
                f"{ms['n']} sprite pixels: mean difference {ms['diff']:.1f} (needs {NIGHT_TINT_MIN})",
                why="the mon is not lit like the arena at night")
        ok = ms["n"] > 0 and ms["on"] >= NIGHT_BLACK[0] and ms["on"] >= NIGHT_BLACK[1] * ms["off"]
        sc.check(f"night: the {mon} is not black", ok,
                 f"mean brightness {ms['on']:.1f} with the stage on, {ms['off']:.1f} off (needs >= "
                 f"{NIGHT_BLACK[0]:.0f} and >= {NIGHT_BLACK[1]:.0%} of off)")
    _finish(sc, e)


SCENARIOS: Dict[str, Callable] = {
    "boot": sc_boot,
    "wild_battle": sc_wild_battle,
    "quick_battle": sc_quick_battle,
    "totem_battle": sc_totem_battle,
    "debug_party": sc_debug_party,
    "move_tester": sc_move_tester,
    "stage_toggle": sc_stage_toggle,
    "stage_ab": sc_stage_ab,
    "switchbg_moves": sc_switchbg_moves,
    "bag_party": sc_bag_party,
    "debug_views": sc_debug_views,
    "all_backgrounds": sc_all_backgrounds,
    "mega": sc_mega,
    "sprite_life": sc_sprite_life,
}
DEFAULT_SCENARIOS = ["boot", "wild_battle", "quick_battle", "move_tester", "stage_toggle"]


# --------------------------------------------------------------------------- report

def write_report(outdir: pathlib.Path, rom: str, results: List[Scenario], total: float) -> pathlib.Path:
    lines = [
        "# Emulator critic report",
        "",
        f"- ROM: `{rom}`",
        f"- Output: `{outdir}`",
        f"- Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}, total {total:.0f}s",
        "",
        "| scenario | result | time | frames | checks |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        counts = {s: sum(c["status"] == s for c in r.checks) for s in ("PASS", "WARN", "FAIL")}
        lines.append(f"| {r.name} | **{r.status}** | {r.seconds:.0f}s | {r.frames_emulated} | "
                     f"{counts['PASS']} pass / {counts['WARN']} warn / {counts['FAIL']} fail |")
    lines += ["", "Automatic checks only prove the game did not hang, crash or show garbage and that",
              "the expected screens were reached. Look at the contact sheets for everything else",
              "(sprite placement, animation quality, palette, 3D stage). Labels read `label @frame`.", ""]
    for r in results:
        lines += [f"## {r.name}: {r.status} ({r.seconds:.0f}s)", ""]
        for c in r.checks:
            lines.append(f"- **{c['status']}** {c['check']}" + (f": {c['detail']}" if c["detail"] else ""))
        if r.notes:
            lines += ["", "Notes:"] + [f"- {n}" for n in r.notes]
        if r.sheets:
            lines += ["", "Contact sheets:"]
            lines += [f"- `{s['sheet']}`: {s['title']} ({s['frames']} frames, {s['screen']})" for s in r.sheets]
        lines.append("")
    path = outdir / "report.md"
    path.write_text("\n".join(lines))
    (outdir / "report.json").write_text(json.dumps({
        "rom": rom, "total_seconds": round(total, 1),
        "scenarios": [r.dump() for r in results]}, indent=2))
    return path


def parse_entries(text: str) -> List[int]:
    out: List[int] = []
    for part in text.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        elif part:
            out.append(int(part))
    return [b % QB_ENTRIES for b in out]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rom")
    ap.add_argument("outdir")
    ap.add_argument("--scenario", nargs="+", choices=sorted(SCENARIOS), default=None,
                    help=f"default: {' '.join(DEFAULT_SCENARIOS)}")
    ap.add_argument("--sav", default=str(DEFAULT_SAV), help="raw .sav to boot (default: %(default)s)")
    ap.add_argument("--moves", default=",".join(map(str, DEFAULT_MOVES)),
                    help="move_tester: comma separated move IDs (generated/moves.txt line - 1)")
    ap.add_argument("--sprite-moves", default=",".join(map(str, SPRITE_MOVES)),
                    help="move_tester / sprite_life: moves that hide, shrink or swap a sprite, played after --moves "
                         "with a 'normal look restored' check ('' = none)")
    ap.add_argument("--reverse", action="store_true", help="move_tester: also play each move enemy->player (Y)")
    ap.add_argument("--anim-frames", type=int, default=1200,
                    help="move_tester/stage_toggle: max frames per animation (recording stops when it ends)")
    ap.add_argument("--max-anim-frames", type=int, default=1800, help="wild_battle: cap for the turn recording")
    ap.add_argument("--bgs", default=None,
                    help="quick_battle / all_backgrounds: background entries (0..30) to battle on "
                         "(default 0,1,29 / 1-30); ranges such as 1-6 work")
    ap.add_argument("--tods", default="day,twilight,night",
                    help="all_backgrounds: times of day (clock, day, twilight, night)")
    ap.add_argument("--every-tod", action="store_true",
                    help="all_backgrounds: also play twilight/night on backgrounds that ignore the time of day")
    ap.add_argument("--stage-tod", choices=TODS, default="day",
                    help="3D stage scenarios on the Plain battle: time of day the launcher forces (clock = the map's own)")
    ap.add_argument("--clock-hour", type=int, default=12,
                    help="hour the game sees after boot, so wild encounters (night Gastly knows Mean Look) and "
                         "the 'clock' time of day do not depend on the host clock; -1 = the real clock. "
                         "Needs the xMAP and a DEBUG_BATTLE_TOOLS build")
    ap.add_argument("--map", default=None,
                    help="xMAP of the ROM's build for the RAM checks (default: next to the ROM or its "
                         "build/main.nef.xMAP; 'none' = pixels only)")
    ap.add_argument("--species-steps", type=int, default=0, help="quick_battle: RIGHT presses before the first battle")
    ap.add_argument("--stage-terrain", choices=("plain", "grass"), default="plain",
                    help="3D stage scenarios: platforms of the Plain background battle (quick-battle entry 01 or 30)")
    ap.add_argument("--verbose", action="store_true", help="show DeSmuME's own stdout")
    ap.add_argument("--timeout", type=int, default=900, help="seconds before a scenario is killed")
    ap.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()
    args.moves = [int(m) for m in args.moves.split(",") if m.strip()]
    args.sprite_moves = [int(m) for m in args.sprite_moves.split(",") if m.strip()]
    args.bgs = parse_entries(args.bgs) if args.bgs else None
    args.tods = [t.strip() for t in args.tods.split(",") if t.strip()]
    bad = [t for t in args.tods if t not in TODS]
    if bad:
        ap.error(f"--tods: unknown {bad}, pick from {', '.join(TODS)}")
    global STAGE_ENTRY
    STAGE_ENTRY = QB_PLAIN_GRASS if args.stage_terrain == "grass" else QB_PLAIN
    outdir = pathlib.Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    names = args.scenario or DEFAULT_SCENARIOS
    if args.child:
        run_in_process(names[0], outdir, args)
        return 0

    # py-desmume cannot create a second emulator in one process (it segfaults), so
    # every scenario runs in its own child process; a crashed child is a FAIL.
    results: List[Scenario] = []
    t_all = time.time()
    passthrough = [a for a in sys.argv[3:] if a not in names and a != "--scenario"]
    for name in names:
        print(f"== {name}", flush=True)
        t = time.time()
        res = outdir / name / "result.json"
        if res.exists():
            res.unlink()
        cmd = [sys.executable, str(pathlib.Path(__file__).resolve()), args.rom, str(outdir),
               "--scenario", name, "--child"] + passthrough
        timeout = args.timeout
        if name == "all_backgrounds":            # about 7s a battle; never cut a full run short
            timeout = max(timeout, 120 + 15 * len(bg_plan(args)))
        code, emu_lines = run_child(cmd, timeout, outdir / name / "console.log")
        sc = Scenario(name, outdir)
        if res.exists():
            sc.load(json.loads(res.read_text()))
        cpu = [ln for ln in emu_lines if CPU_EXCEPTION.search(ln)]
        sc.check("no CPU exceptions in the emulator log", not cpu,
                 why=f"{len(cpu)} line(s), first: {cpu[0].strip() if cpu else ''} "
                     f"(full log {outdir / name / 'console.log'})")
        if code != 0:
            sc.check("scenario process exited cleanly", False,
                     f"timed out after {timeout}s" if code == "timeout" else
                     f"exit code {code}" + (" (emulator crashed)" if isinstance(code, int) and code < 0 else ""))
        if not res.exists():
            sc.seconds = time.time() - t
        print(f"   -> {sc.status} in {sc.seconds:.1f}s", flush=True)
        results.append(sc)
    report = write_report(outdir, args.rom, results, time.time() - t_all)
    print(f"report: {report}")
    return 1 if any(r.status == "FAIL" for r in results) else 0


CPU_EXCEPTION = re.compile(r"Undefined instruction|Data abort|Prefetch abort|Unimplemented|ARM[79].*(fault|exception)",
                           re.IGNORECASE)


def run_child(cmd: List[str], timeout: int, log_path: pathlib.Path):
    """Runs a scenario child, echoing its output live and keeping a full copy in log_path.
    DeSmuME prints thousands of identical lines during some animations ("STMIA with Rb in
    Rlist"); each distinct emulator line is echoed once, harness lines always.
    Returns (exit code, lines)."""
    lines: List[str] = []
    seen: set = set()
    hidden = 0
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w") as log:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
                             errors="replace")
        timer = threading.Timer(timeout, p.kill)
        timer.start()
        try:
            for ln in p.stdout:
                log.write(ln)
                lines.append(ln)
                harness = ln.startswith(("  [", "  note", "Traceback", "  File ", "    ")) or CPU_EXCEPTION.search(ln)
                key = re.sub(r"0x[0-9A-Fa-f]+|\d+", "#", ln.strip())
                if harness or key not in seen:
                    seen.add(key)
                    sys.stdout.write(ln)
                    sys.stdout.flush()
                else:
                    hidden += 1
            code = p.wait()
        finally:
            timed_out = not timer.is_alive()
            timer.cancel()
    if hidden:
        print(f"   ({hidden} repeated emulator lines not echoed; full log {log_path})", flush=True)
    return ("timeout" if timed_out and code != 0 else code), lines


def run_in_process(name: str, outdir: pathlib.Path, args) -> Scenario:
    global CLOCK_PIN
    sc = Scenario(name, outdir)
    xmap = find_xmap(args)
    addr = read_xmap(xmap).get("sDebugClockHour") if xmap and 0 <= args.clock_hour < 24 else None
    CLOCK_PIN = (addr[0], args.clock_hour) if addr else None
    if 0 <= args.clock_hour < 24 and not addr:
        sc.note(f"clock not pinned ({'no xMAP' if not xmap else 'no sDebugClockHour in ' + xmap}): "
                "wild encounters follow the host clock")
    t = time.time()
    e = None
    try:
        e = Emu(args.rom, args.sav, verbose=args.verbose)
        SCENARIOS[name](sc, e, args)
    except Exception as exc:                        # a scenario crash is a FAIL, not a crash of the run
        sc.check("scenario ran without a harness error", False, f"{type(exc).__name__}: {exc}")
        traceback.print_exc()
        if e is not None:
            try:
                sc.sheet([e.snap("at error")], "error", "screen when the harness error happened")
            except Exception:
                pass
    finally:
        if e is not None:
            sc.frames_emulated = e.frame
            sc.notes.extend(e.log)
    sc.seconds = time.time() - t
    (sc.dir / "result.json").write_text(json.dumps(sc.dump(), indent=2))
    if e is not None:
        e.close()
    return sc


if __name__ == "__main__":
    sys.exit(main())
