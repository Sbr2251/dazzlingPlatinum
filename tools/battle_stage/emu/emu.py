"""Headless py-desmume harness for dazzlingPlatinum.

Run with the Python 3.9 venv (the 3.12 venv's desmume is broken for this):

    SDL_VIDEODRIVER=dummy ~/.venvs/desmume39/bin/python ...

Typical use::

    from emu import Emu
    with Emu(rom, "saves/eterna_forest_grass.sav") as e:
        e.boot()                                  # title -> Continue -> overworld
        e.walk_until_battle()                     # pace in the grass
        e.wait_battle_menu(snap_every=15, label="intro")
        e.battle_fight(0)
        ...

Coordinates for `touch` are bottom-screen pixels (0..255, 0..191). Screenshots
from `screens()` are 256x384 (top screen above the bottom screen).

Nothing in Emu depends on symbol addresses, so it keeps working across rebuilds:
game state is read from pixels, and the few RAM lookups (player position,
party) are found by scanning RAM for values that are known from the save.
`read_xmap` is the exception, for callers that want a static variable: pass it
the xMAP of the same build as the ROM.

Gotchas:
- Every Emu copies the ROM to a unique temp file. DeSmuME keys its battery
  file on the ROM name, so two runs of the same ROM path share saves.
- The DS clock is the host clock: time of day (battle background palette) and
  the RNG differ between runs. Scenarios must not depend on exact encounters.
- Savestates (.dst) go stale on every rebuild; always boot from a .sav.
"""

from __future__ import annotations

import os
import pathlib
import re
import shutil
import struct
import sys
import tempfile
import uuid
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageStat

try:
    from desmume.controls import Keys, keymask
    from desmume.emulator import DeSmuME
except ImportError as exc:  # pragma: no cover
    raise SystemExit(f"py-desmume not importable ({exc}); use ~/.venvs/desmume39/bin/python") from exc

KEYS = {
    "A": Keys.KEY_A, "B": Keys.KEY_B, "X": Keys.KEY_X, "Y": Keys.KEY_Y,
    "START": Keys.KEY_START, "SELECT": Keys.KEY_SELECT,
    "UP": Keys.KEY_UP, "DOWN": Keys.KEY_DOWN, "LEFT": Keys.KEY_LEFT, "RIGHT": Keys.KEY_RIGHT,
    "L": Keys.KEY_L, "R": Keys.KEY_R,
}
DIRS = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}

W, H = 256, 192            # one screen
RAM_BASE, RAM_END = 0x02000000, 0x02400000

# Battle bottom-screen touch targets (singles).
BTN_FIGHT = (128, 90)
BTN_BAG = (40, 172)
BTN_RUN = (128, 178)
BTN_POKEMON = (216, 172)
BTN_CANCEL = (128, 176)                                  # in the move list
MOVE_SLOTS = ((64, 48), (192, 48), (64, 110), (192, 110))
BTN_MEGA = (64, 172)                                     # in the move list, when the battler can Mega Evolve

# Main-screen layers for Emu.render_layers (DeSmuME's own layer switches; the game never sees them).
# BG0 is the 3D layer: the battle stage arena, the Pokemon sprites and the particles.
LAYER_BG0, LAYER_BG1, LAYER_BG2, LAYER_BG3, LAYER_OBJ = (1 << i for i in range(5))
LAYERS_ALL = 0x1F
LAYERS_2D = LAYERS_ALL & ~LAYER_BG0
BG_PALETTE = 0x05000000                                  # main BG palette RAM; colour 0 is the backdrop
BACKDROP_MARKER = 0x7C1F                                 # magenta, BGR555: no battle art uses it

PARTY_REC = 236            # encrypted party record (PK4 + battle stats)


# --------------------------------------------------------------------------- image helpers

def top(img: Image.Image) -> Image.Image:
    return img.crop((0, 0, W, H))


def bottom(img: Image.Image) -> Image.Image:
    return img.crop((0, H, W, 2 * H))


def diff_fraction(a: Image.Image, b: Image.Image, threshold: int = 24) -> float:
    """Fraction of pixels whose max channel difference exceeds `threshold`."""
    d = ImageChops.difference(a.convert("RGB"), b.convert("RGB")).convert("L")
    hist = d.point(lambda v: 255 if v > threshold else 0).histogram()
    return hist[255] / float(a.size[0] * a.size[1])


def dominant_fraction(img: Image.Image) -> float:
    """Share of the most common colour; ~1.0 means a flat (black/white/stuck) screen."""
    colors = img.convert("RGB").getcolors(maxcolors=1 << 16)
    if not colors:
        return 0.0
    return max(c for c, _ in colors) / float(img.size[0] * img.size[1])


def noise_score(img: Image.Image) -> float:
    """Mean |pixel - right neighbour| (0..255). Game frames sit well under ~25; VRAM garbage is far higher."""
    g = img.convert("L")
    shifted = g.crop((1, 0, g.size[0], g.size[1]))
    base = g.crop((0, 0, g.size[0] - 1, g.size[1]))
    return ImageStat.Stat(ImageChops.difference(base, shifted)).mean[0]


def mean_brightness(img: Image.Image) -> float:
    return ImageStat.Stat(img.convert("L")).mean[0]


def screen_health(img: Image.Image) -> dict:
    """Numbers a critic can threshold: flat = stuck/blank screen, noise = garbage."""
    return {
        "flat": round(dominant_fraction(img), 3),
        "noise": round(noise_score(img), 1),
        "bright": round(mean_brightness(img), 1),
    }


def looks_broken(img: Image.Image, flat_max: float = 0.97, noise_max: float = 45.0) -> Optional[str]:
    h = screen_health(img)
    if h["flat"] > flat_max:
        return f"flat screen ({h['flat']:.0%} one colour, brightness {h['bright']})"
    if h["noise"] > noise_max:
        return f"noisy screen (noise {h['noise']}), possible garbage"
    return None


def marker_fraction(img: Image.Image) -> float:
    """Share of pixels showing BACKDROP_MARKER (magenta), i.e. where no enabled layer drew anything."""
    r, g, b = img.convert("RGB").split()
    hit = ImageChops.multiply(ImageChops.multiply(r.point(lambda v: 255 if v >= 240 else 0),
                                                  g.point(lambda v: 255 if v <= 8 else 0)),
                              b.point(lambda v: 255 if v >= 240 else 0))
    return hit.histogram()[255] / float(img.size[0] * img.size[1])


def read_xmap(path) -> Dict[str, Tuple[int, int]]:
    """Symbol -> (address, size) from a mwldarm .xMAP, for lines such as
    `  02281BE8 0000001C .bss    sBattleStage\t(src_battle_battle_stage.c.o)`. A static name that
    several files define is dropped, since it could not be told apart."""
    rx = re.compile(r"^\s+([0-9A-Fa-f]{8}) ([0-9A-Fa-f]{8}) \.(?:bss|data|rodata|sbss|sdata)\s+(\S+)\t")
    out: Dict[str, Tuple[int, int]] = {}
    dup = set()
    with open(path, errors="replace") as f:
        for ln in f:
            m = rx.match(ln)
            if not m:
                continue
            name = m.group(3)
            if name in out:
                dup.add(name)
            out[name] = (int(m.group(1), 16), int(m.group(2), 16))
    for name in dup:
        del out[name]
    return out


def _near(px, rgb, tol=24) -> bool:
    return all(abs(int(a) - int(b)) <= tol for a, b in zip(px[:3], rgb))


# --------------------------------------------------------------------------- contact sheets

class Frame:
    __slots__ = ("label", "frame", "img")

    def __init__(self, label: str, frame: int, img: Image.Image):
        self.label, self.frame, self.img = label, frame, img


def dedupe(frames: Sequence[Frame], screen: str = "top", threshold: float = 0.002) -> List[Frame]:
    """Drops frames that are (nearly) identical to the previously kept one."""
    out: List[Frame] = []
    crop = top if screen == "top" else (bottom if screen == "bottom" else (lambda i: i))
    for f in frames:
        if not out or diff_fraction(crop(out[-1].img), crop(f.img)) > threshold:
            out.append(f)
    return out


def contact_sheet(frames: Sequence[Frame], path, title: str = "", screen: str = "both",
                  cols: int = 8, scale: float = 0.5, max_frames: int = 96) -> Optional[str]:
    """Writes a labelled grid. screen: 'both' (256x384), 'top' or 'bottom'."""
    if not frames:
        return None
    frames = list(frames)
    if len(frames) > max_frames:                     # keep first/last, thin the middle evenly
        step = (len(frames) - 1) / float(max_frames - 1)
        frames = [frames[round(i * step)] for i in range(max_frames)]
    crop = {"top": top, "bottom": bottom, "both": lambda i: i}[screen]
    sw, sh = int(W * scale), int((H if screen != "both" else 2 * H) * scale)
    lab = 12
    cols = max(1, min(cols, len(frames)))
    rows = (len(frames) + cols - 1) // cols
    head = 16 if title else 0
    sheet = Image.new("RGB", (cols * (sw + 2), head + rows * (sh + lab + 2)), (40, 40, 40))
    d = ImageDraw.Draw(sheet)
    if title:
        d.text((4, 2), title, fill=(255, 255, 0))
    for k, f in enumerate(frames):
        x, y = (k % cols) * (sw + 2), head + (k // cols) * (sh + lab + 2)
        sheet.paste(crop(f.img).resize((sw, sh), Image.NEAREST), (x, y + lab))
        d.text((x + 2, y), f"{f.label} @{f.frame}"[: sw // 6], fill=(255, 255, 255))
    path = str(path)
    sheet.save(path)
    return path


# --------------------------------------------------------------------------- emulator

class Emu:
    """One headless DeSmuME instance booted from a raw .sav."""

    def __init__(self, rom, sav, workdir: Optional[str] = None, verbose: bool = False):
        self.tmp = tempfile.mkdtemp(prefix="bsemu_", dir=workdir)
        self.rom = os.path.join(self.tmp, f"rom_{uuid.uuid4().hex[:10]}.nds")
        shutil.copyfile(rom, self.rom)
        self.sav = str(sav)
        self._quiet_start(verbose)
        self.frame = 0
        self.log: List[str] = []
        self.pos_addr: Optional[int] = None
        self.party_addr: Optional[int] = None

    def _quiet_start(self, verbose: bool) -> None:
        # DeSmuME prints a lot on stdout from C; silence fd 1 while it initialises.
        saved = None
        if not verbose:
            sys.stdout.flush()
            saved = os.dup(1)
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, 1)
            os.close(devnull)
        try:
            self.e = DeSmuME()
            self.e.open(self.rom)
            self.e.backup.import_file(self.sav)
            self.e.reset()
            self.e.volume_set(0)
        finally:
            if saved is not None:
                sys.stdout.flush()
                os.dup2(saved, 1)
                os.close(saved)

    def close(self) -> None:
        try:
            self.e.destroy()
        except Exception:
            pass
        shutil.rmtree(self.tmp, ignore_errors=True)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def note(self, msg: str) -> None:
        self.log.append(f"[{self.frame}] {msg}")

    # ---- time and input ------------------------------------------------------------------

    def run(self, n: int = 1) -> None:
        for _ in range(n):
            self.e.cycle(with_joystick=False)
        self.frame += n

    @staticmethod
    def _keys(keys) -> List[str]:
        if isinstance(keys, str):
            keys = keys.split("+")
        return [k.strip().upper() for k in keys if k.strip()]

    def press(self, keys) -> None:
        for k in self._keys(keys):
            self.e.input.keypad_add_key(keymask(KEYS[k]))

    def release(self, keys) -> None:
        for k in self._keys(keys):
            self.e.input.keypad_rm_key(keymask(KEYS[k]))

    def hold(self, keys, frames: int, after: int = 0) -> None:
        """Holds keys ('A', 'L+R+UP', ['L', 'R']) for `frames`, then runs `after` more frames."""
        self.press(keys)
        self.run(frames)
        self.release(keys)
        self.run(after)

    def tap(self, keys, after: int = 30) -> None:
        self.hold(keys, 6, after)

    def combo(self, held="L+R", key: str = "A", settle: int = 6, press: int = 6, after: int = 20,
              snap: Optional[str] = None) -> None:
        """Holds `held`, waits `settle` frames, taps `key` (edge), keeps `held` for `after` frames, releases."""
        self.press(held)
        self.run(settle)
        self.hold(key, press, after)
        if snap:
            self.snap(snap)
        self.release(held)
        self.run(2)

    def touch(self, x: int, y: int, after: int = 30, frames: int = 8) -> None:
        self.e.input.touch_set_pos(int(x), int(y))
        self.run(frames)
        self.e.input.touch_release()
        self.run(after)

    # ---- capture -------------------------------------------------------------------------

    def screens(self) -> Image.Image:
        return self.e.screenshot().convert("RGB")

    def render_layers(self, mask: int, marker: bool = False) -> Image.Image:
        """Runs one frame with only the main-screen layers in `mask` shown and returns it (both
        screens). With `marker` the backdrop is magenta for that frame (see marker_fraction),
        so uncovered pixels can be told apart from dark art. Everything is restored after."""
        e = self.e
        for layer in range(5):
            e.gpu_set_layer_main_enable_state(layer, bool(mask >> layer & 1))
        old = None
        if marker:
            old = struct.unpack("<H", self.read(BG_PALETTE, 2))[0]
            e.memory.write_short(BG_PALETTE, BACKDROP_MARKER)
        try:
            self.run(1)
            return self.screens()
        finally:
            if old is not None:
                e.memory.write_short(BG_PALETTE, old)
            for layer in range(5):
                e.gpu_set_layer_main_enable_state(layer, True)

    def snap(self, label: str, into: Optional[list] = None) -> Frame:
        f = Frame(label, self.frame, self.screens())
        if into is not None:
            into.append(f)
        return f

    def record(self, frames: int, every: int = 3, label: str = "", into: Optional[list] = None,
               stop: Optional[Callable[["Emu"], bool]] = None, min_frames: int = 0) -> List[Frame]:
        """Runs `frames` frames, snapping every `every`. Stops early once stop(self) is true after min_frames."""
        got: List[Frame] = []
        start = self.frame
        while self.frame - start < frames:
            self.run(every)
            f = self.snap(f"{label}+{self.frame - start}", into)
            got.append(f)
            if stop is not None and self.frame - start >= min_frames and stop(self):
                break
        return got

    def is_alive(self, frames: int = 90, every: int = 15, region: str = "top") -> bool:
        """True if the chosen screen changes at all over `frames` (idle animations keep it moving)."""
        crop = top if region == "top" else bottom
        first = crop(self.screens())
        for _ in range(frames // every):
            self.run(every)
            if diff_fraction(first, crop(self.screens()), threshold=8) > 0.0005:
                return True
        return False

    # ---- waiting -------------------------------------------------------------------------

    def wait_until(self, pred: Callable[["Emu"], bool], timeout: int = 1800, step: int = 5,
                   snap_every: int = 0, label: str = "wait", into: Optional[list] = None) -> Optional[int]:
        """Runs until pred(self); returns frames waited or None on timeout. Optionally snaps periodically."""
        start = self.frame
        last_snap = start
        while self.frame - start <= timeout:
            if pred(self):
                return self.frame - start
            self.run(step)
            if snap_every and self.frame - last_snap >= snap_every:
                self.snap(f"{label}+{self.frame - start}", into)
                last_snap = self.frame
        return None

    # ---- state detection (pixels) --------------------------------------------------------

    def in_overworld(self, img: Optional[Image.Image] = None) -> bool:
        """The Poketch's green LCD fills the bottom screen in the field."""
        # The battle's end screen is also green (pokeball backdrop), so require the
        # Poketch's red side button too and a clearly green LCD (g well above r and b).
        img = img or self.screens()
        if not all(_near(img.getpixel(p), (248, 64, 72), 30) for p in ((240, H + 80), (240, H + 120))):
            return False
        good = 0
        for p in ((60, H + 108), (190, H + 150), (128, H + 30)):
            r, g, b = img.getpixel(p)[:3]
            good += g > 130 and g > r + 40 and g > b + 40
        return good >= 2

    def battle_menu_up(self, img: Optional[Image.Image] = None) -> bool:
        """The big red FIGHT button of the command menu is on the bottom screen."""
        img = img or self.screens()
        return all(_near(img.getpixel(p), (232, 56, 56), 20) for p in ((60, H + 60), (200, H + 60), (128, H + 105)))

    def move_list_up(self, img: Optional[Image.Image] = None) -> bool:
        """The FIGHT sub-menu: a blue CANCEL bar along the bottom and no red FIGHT button. The bar
        is shorter when a MEGA button sits to its left, so only its right half is tested."""
        img = img or self.screens()
        bar = all(_near(img.getpixel(p), (40, 144, 200), 24) for p in ((160, H + 178), (216, H + 170), (216, H + 186)))
        return bar and not self.battle_menu_up(img)

    def top_is_black(self, img: Optional[Image.Image] = None) -> bool:
        img = img or self.screens()
        return mean_brightness(top(img)) < 8

    # ---- boot ----------------------------------------------------------------------------

    def boot(self, timeout: int = 2400, into: Optional[list] = None) -> bool:
        """Title -> Continue -> overworld. Returns True once the Poketch is visible.
        With `into`, a frame is captured at each step (for a boot contact sheet)."""
        snap = (lambda lab: self.snap(lab, into)) if into is not None else (lambda lab: None)
        for i in range(11):
            self.run(60)
            if i % 3 == 2:
                snap("title")
        for _ in range(4):                               # intro, title, Continue, (journal)
            self.tap("A", 100)
            snap("A")
        # The adventure journal ("Started from ...") sits on the top screen, with a black
        # bottom screen, until B. Tap B (an occasional A in case we are still on the
        # title menu) until the Poketch is visible for a few consecutive checks.
        start, ok, streak, taps = self.frame, False, 0, 0
        while self.frame - start < timeout:
            if self.in_overworld():
                streak += 1
                if streak >= 3:
                    ok = True
                    break
                self.run(20)
                continue
            streak = 0
            taps += 1
            self.tap("A" if taps % 8 == 0 else "B", 54)
            snap("B")
        self.run(30)
        snap("overworld" if ok else "boot-timeout")
        self.note(f"boot {'ok' if ok else 'FAILED'}")
        return ok

    # ---- RAM helpers (build independent) -------------------------------------------------

    def ram(self) -> bytes:
        return bytes(self.e.memory.read(RAM_BASE, RAM_END, 1, False))

    def read(self, addr: int, n: int) -> bytes:
        return bytes(self.e.memory.read(addr, addr + n, 1, False))

    def write(self, addr: int, data: bytes) -> None:
        for i, b in enumerate(data):
            self.e.memory.write_byte(addr + i, b)

    def find_player(self, start: Tuple[int, int]) -> Tuple[int, int]:
        """Locates the player's (x, z) s32 pair in RAM by taking a step. `start` = tile from the save."""
        before = self.ram()
        cands = [o for o in range(0, len(before) - 8, 4) if struct.unpack_from("<ii", before, o) == tuple(start)]
        for key in ("DOWN", "UP", "RIGHT", "LEFT"):
            self.hold(key, 8, 30)
            if not self.in_overworld():
                self.battle_escape()
            after = self.ram()
            for o in cands:
                x, z = struct.unpack_from("<ii", after, o)
                if (x, z) != tuple(start) and abs(x - start[0]) + abs(z - start[1]) <= 2:
                    self.pos_addr = RAM_BASE + o
                    return self.pos()
        raise RuntimeError("could not locate player position in RAM")

    def pos(self) -> Tuple[int, int]:
        assert self.pos_addr, "call find_player() first"
        return struct.unpack("<ii", self.read(self.pos_addr, 8))

    def find_party(self, sav_record: bytes) -> int:
        """RAM address of party slot 0 (the encrypted 236-byte record is identical to the save's)."""
        blob = self.ram()
        o = blob.find(sav_record)
        if o < 0:
            raise RuntimeError("party record from the save not found in RAM")
        self.party_addr = RAM_BASE + o
        return self.party_addr

    def party_species(self) -> List[dict]:
        """Decrypts the live party (needs find_party first)."""
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
        from platinum_save_utils import decrypt_pk4, u16
        n = self.party_count()
        out = []
        for i in range(min(n, 6)):
            r = decrypt_pk4(self.read(self.party_addr + i * PARTY_REC, PARTY_REC))
            out.append({"species": u16(r, 8), "item": u16(r, 0x0A), "level": r[0x8C],
                        "moves": [u16(r, 0x28 + 2 * j) for j in range(4)]})
        return out

    def party_count(self) -> int:
        return struct.unpack("<I", self.read(self.party_addr - 4, 4))[0]

    def swap_party(self, i: int, j: int) -> None:
        """Swaps two party slots in RAM (needs find_party). Each record is self-contained, so the
        game takes the new order as is; a battle started afterwards leads with slot 0."""
        a, b = self.party_addr + i * PARTY_REC, self.party_addr + j * PARTY_REC
        ra, rb = self.read(a, PARTY_REC), self.read(b, PARTY_REC)
        self.write(a, rb)
        self.write(b, ra)

    # ---- overworld -----------------------------------------------------------------------

    def walk_until_battle(self, max_steps: int = 200, keys: Sequence[str] = ("UP", "DOWN"),
                          step_frames: int = 16) -> Optional[int]:
        """Paces back and forth (stand in tall grass / a cave) until a wild battle starts.
        Returns the number of steps taken, or None if no encounter."""
        if not self.in_overworld():
            self.note("walk_until_battle: not in the overworld")
            return None
        for i in range(max_steps):
            self.hold(keys[i % len(keys)], step_frames, 4)
            if not self.in_overworld():
                self.run(10)
                if not self.in_overworld():
                    self.note(f"encounter after {i + 1} steps")
                    return i + 1
        return None

    def walk(self, key: str, tiles: int) -> Tuple[int, int]:
        """Walks `tiles` in a direction one tile at a time (needs find_player). Stops at walls."""
        dx, dz = DIRS[key]
        for _ in range(tiles):
            x0, z0 = self.pos()
            self.press(key)
            for _ in range(40):
                self.run(1)
                if self.pos() == (x0 + dx, z0 + dz):
                    break
            self.release(key)
            self.run(10)
            if not self.in_overworld():
                self.battle_escape()
            if self.pos() == (x0, z0):
                break
        return self.pos()

    # ---- battle --------------------------------------------------------------------------

    def wait_battle_menu(self, timeout: int = 2400, snap_every: int = 0, label: str = "intro",
                         into: Optional[list] = None, advance_text: bool = False) -> Optional[int]:
        """Waits for the command menu (optionally tapping B to advance text every ~40 frames)."""
        start = self.frame
        last = start
        while self.frame - start <= timeout:
            if self.battle_menu_up():
                self.run(10)                             # let the slide-in finish
                if self.battle_menu_up():
                    return self.frame - start
            if advance_text and self.frame - last >= 40:
                self.tap("B", 0)
                last = self.frame
            self.run(5)
            if snap_every and (self.frame - start) % snap_every < 5:
                self.snap(f"{label}+{self.frame - start}", into)
        return None

    def battle_fight(self, slot: int = 0) -> bool:
        """FIGHT -> move `slot` (singles). Returns False if the move list did not open."""
        self.touch(*BTN_FIGHT, after=40)
        if not self.move_list_up():
            self.note("move list did not open")
            return False
        self.touch(*MOVE_SLOTS[slot], after=4)
        return True

    def battle_open_bag(self, into: Optional[list] = None) -> bool:
        before = bottom(self.screens())
        self.touch(*BTN_BAG, after=10)
        ok = self.wait_until(lambda e: diff_fraction(before, bottom(e.screens())) > 0.5 and not e.battle_menu_up(),
                             timeout=240, step=5) is not None
        self.run(40)
        return ok

    def battle_close_bag(self) -> bool:
        """Leaves the battle bag with B and waits for the command menu."""
        for _ in range(3):
            self.tap("B", 30)
            if self.wait_battle_menu(timeout=240) is not None:
                return True
        return False

    def battle_run(self, timeout: int = 1800, into: Optional[list] = None) -> bool:
        """RUN until back in the overworld (retries if escape fails). Returns True on success.
        With `into`, a frame is captured after every action."""
        start = self.frame
        while self.frame - start < timeout:
            if into is not None:
                self.snap("run", into)
            if self.in_overworld():
                self.run(30)
                return True
            if self.battle_menu_up():
                self.touch(*BTN_RUN, after=30)
                continue
            if self.move_list_up():
                self.touch(*BTN_CANCEL, after=30)
                continue
            self.tap("B", 25)
        return self.in_overworld()

    def battle_escape(self) -> bool:
        """Runs from an unexpected battle. Returns True if one was handled."""
        if self.in_overworld():
            return False
        self.run(60)
        if self.in_overworld():
            return False
        self.wait_battle_menu(timeout=1800, advance_text=True)
        return self.battle_run()
