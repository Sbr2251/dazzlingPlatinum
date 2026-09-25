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
import subprocess
import sys
import threading
import time
import traceback
from typing import Callable, Dict, List, Optional

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from emu import (  # noqa: E402
    BTN_CANCEL, BTN_FIGHT, Emu, Frame, bottom, contact_sheet, dedupe, diff_fraction,
    looks_broken, screen_health, top,
)
from PIL import Image, ImageChops  # noqa: E402

DEFAULT_SAV = HERE / "saves" / "eterna_forest_grass.sav"
FALSE_SWIPE_SLOT = 3                   # the committed save's lead has False Swipe here (never KOs)
MOVE_ID_MAX = 473                      # move tester wraps within 1..473
QB_ENTRIES = 30                        # quick-battle background entries 0..29
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


def boot(sc: Scenario, e: Emu, frames: Optional[list] = None) -> bool:
    t = time.time()
    ok = e.boot(into=frames)
    sc.check("booted to overworld", ok, f"{e.frame} frames, {time.time() - t:.1f}s"
             if ok else "Poketch never appeared on the bottom screen")
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
              label: str) -> Optional[bool]:
    """Opens the quick-battle panel, moves the selectors (entries_down < 0 = UP), presses `key` (A/X).
    True if a battle started, False if not, None if the panel never opened."""
    d = hold_overlay(e, threshold=0.10)
    if d is None:
        _no_combo(sc, f"{label}: L+R panel opened", "the overworld quick-battle panel")
        return None
    e.snap(f"{label} panel", panel)
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
    for n, bg in enumerate(args.bgs):
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


def sc_move_tester(sc: Scenario, e: Emu, args) -> None:
    if not _battle_ready(sc, e):
        return
    ov = Overlay(e)
    e.run(30)                                # let the menu's text box icons appear
    idle_frames = e.record(60, every=5, label="idle")
    idle = [scene(f.img) for f in idle_frames]
    base_boxes = [text_box(f.img) for f in idle_frames]
    overlays: List[Frame] = []
    after: List[Frame] = []
    if not ov.show():
        _no_combo(sc, "L+R move-tester overlay shown", "the in-battle move tester")
        run_away(sc, e)
        return
    e.snap("overlay (start, expect Move 001)", overlays)
    cur, stuck = 1, False
    for mid in args.moves:
        mid = max(1, min(MOVE_ID_MAX, mid))
        for direction, key in (("fwd", "A"), ("rev", "Y"))[: 2 if args.reverse else 1]:
            tag = f"move {mid:03d} {direction}"
            if not ov.up() and not ov.show():
                sc.check(f"{tag}: overlay shown", False, "holding L+R did not bring the overlay back")
                continue
            _nav_move(e, cur, mid)
            cur = mid
            e.snap(f"overlay {mid:03d}", overlays)
            anim, done = ov.play(key, args.anim_frames, f"{mid:03d}{direction}")
            if froze(sc, e, anim, f"playing move {mid} with L+R+{key}"):
                sc.sheet(anim[:1] + [e.snap("frozen")], f"move_{mid:03d}_{direction}_frozen",
                         f"move {mid}: frozen screen", scale=1.0)
                stuck = True
                break
            change = max((min_diff(idle, scene(f.img)) for f in anim), default=0.0)
            sc.check(f"{tag} ({key}): animation drew something", change > 0.003,
                     f"up to {change:.1%} of the scene (HUD masked) differs from idle, "
                     f"{len(dedupe(anim, 'top'))} distinct frames",
                     why="nothing moved on screen while the tester said an animation was playing")
            bad = noisy_frames(anim)
            if bad:
                sc.warn(f"{tag}: frames look sane", f"{len(bad)} noisy: {', '.join(bad[:4])}")
            sc.sheet(anim, f"move_{mid:03d}_{direction}",
                     f"move {mid} {'player->enemy' if key == 'A' else 'enemy->player'}, every 3 frames (deduped)",
                     screen="top", dedupe_screen="top")
            if not sc.check(f"{tag}: animation finished", done is not None,
                            f"overlay hidden {done} frames after L+R+{key}" if done is not None else
                            f"overlay still up {len(anim) * 3} frames after L+R+{key}: the animation never "
                            "ended, so the command menu keeps ignoring input"):
                stuck = True
                break
            # The text comes back first; a broken state can garble it a few dozen frames later.
            e.run(10)
            e.snap(f"after {mid:03d} +10", after)
            e.run(80)
            shot = e.snap(f"after {mid:03d} +90", after)
            d = min_diff(base_boxes, text_box(shot.img))
            if not sc.check(f"{tag}: battle text restored", d < 0.02,
                            f"{d:.1%} of the text box differs from before the overlay (90 frames after)",
                            why="the message box was not restored (garbled or blank; see sheet_after)"):
                if not sc.check(f"{tag}: command menu still responds", menu_responds(e),
                                why="touching FIGHT no longer opens the move list: the battle is soft-locked"):
                    stuck = True
                    break
        if stuck:
            break
    sc.sheet(overlays, "overlays", "L+R overlay before each animation (check the move name)",
             screen="top", cols=4, scale=1.0)
    sc.sheet(after, "after", "battle text 10 and 90 frames after each animation (should read 'What will ... do?')",
             screen="top", cols=4, scale=1.0)
    if stuck:
        sc.note("Skipped running away: the command menu is stuck or frozen.")
        return
    if not e.battle_menu_up():
        e.wait_battle_menu(timeout=1800, advance_text=True)
    if sc.check("command menu responds after the tester", e.battle_menu_up() and menu_responds(e),
                why="touching FIGHT did not open the move list"):
        run_away(sc, e)


def sc_stage_toggle(sc: Scenario, e: Emu, args) -> None:
    if not _battle_ready(sc, e):
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


SCENARIOS: Dict[str, Callable] = {
    "boot": sc_boot,
    "wild_battle": sc_wild_battle,
    "quick_battle": sc_quick_battle,
    "totem_battle": sc_totem_battle,
    "debug_party": sc_debug_party,
    "move_tester": sc_move_tester,
    "stage_toggle": sc_stage_toggle,
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rom")
    ap.add_argument("outdir")
    ap.add_argument("--scenario", nargs="+", choices=sorted(SCENARIOS), default=None,
                    help=f"default: {' '.join(DEFAULT_SCENARIOS)}")
    ap.add_argument("--sav", default=str(DEFAULT_SAV), help="raw .sav to boot (default: %(default)s)")
    ap.add_argument("--moves", default=",".join(map(str, DEFAULT_MOVES)),
                    help="move_tester: comma separated move IDs (generated/moves.txt line - 1)")
    ap.add_argument("--reverse", action="store_true", help="move_tester: also play each move enemy->player (Y)")
    ap.add_argument("--anim-frames", type=int, default=1200,
                    help="move_tester/stage_toggle: max frames per animation (recording stops when it ends)")
    ap.add_argument("--max-anim-frames", type=int, default=1800, help="wild_battle: cap for the turn recording")
    ap.add_argument("--bgs", default="0,1,29", help="quick_battle: background entries (0..29) to battle on")
    ap.add_argument("--species-steps", type=int, default=0, help="quick_battle: RIGHT presses before the first battle")
    ap.add_argument("--verbose", action="store_true", help="show DeSmuME's own stdout")
    ap.add_argument("--timeout", type=int, default=900, help="seconds before a scenario is killed")
    ap.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()
    args.moves = [int(m) for m in args.moves.split(",") if m.strip()]
    args.bgs = [int(b) % QB_ENTRIES for b in args.bgs.split(",") if b.strip()]
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
        code, emu_lines = run_child(cmd, args.timeout, outdir / name / "console.log")
        sc = Scenario(name, outdir)
        if res.exists():
            sc.load(json.loads(res.read_text()))
        cpu = [ln for ln in emu_lines if CPU_EXCEPTION.search(ln)]
        sc.check("no CPU exceptions in the emulator log", not cpu,
                 why=f"{len(cpu)} line(s), first: {cpu[0].strip() if cpu else ''} "
                     f"(full log {outdir / name / 'console.log'})")
        if code != 0:
            sc.check("scenario process exited cleanly", False,
                     f"timed out after {args.timeout}s" if code == "timeout" else
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
    sc = Scenario(name, outdir)
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
