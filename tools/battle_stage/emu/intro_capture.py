"""Battle intro capture (docs/living_battle_stage/intro.md). intro_capture.py ROM XMAP OUTDIR MODE

MODE: wild (Plain quick battle, day), totem (L+R+X), taylor (A2-19 Aroma Lady Taylor, single),
twins (A2-19 Twins Liv & Liz, double), tag25 (A2-09 -> Ravaged Path, the Arc 2 2.5 tag battle).
Append "classic" (wildclassic, taylorclassic) to switch the stage off as soon as the battle sets it
up (sBattleStage.enabled = 0, as L+R+SELECT would): the classic opening.
One mode per process (one emulator per process). Records every 2 frames from the battle start to
40 frames after the first command menu: OUTDIR/<mode>_NN.png (both screens, deduplicated, each cell
labelled with camFlags and the opponent/player anchor scales), <mode>_overview.png (top screen every
16 frames), frames/<mode>/NNNNN.png (every 4th frame) and <mode>_log.json (the camera per sample).
The owner saves are read from $INTRO_SAVES (default /tmp/bw2vis/saves/raw_sav); the trainer modes
move the player with make_save.py --at, tag25 also changes the saved map to Route 204 South.
Run with SDL_VIDEODRIVER=dummy ~/.venvs/desmume39/bin/python."""
import json, os, pathlib, struct, subprocess, sys

EMU_DIR = str(pathlib.Path(__file__).resolve().parent)
sys.path.insert(0, EMU_DIR)
import critic as C  # noqa: E402
from emu import Emu, Frame, contact_sheet, H, _near, dedupe  # noqa: E402

PY = sys.executable
MK = EMU_DIR + "/make_save.py"
RAW = os.environ.get("INTRO_SAVES", "/tmp/bw2vis/saves/raw_sav")
WORK = pathlib.Path(os.environ.get("INTRO_WORK", "/tmp/intro_capture_work"))
WORK.mkdir(parents=True, exist_ok=True)


def field_any(e, img=None):
    img = img or e.screens()
    if e.in_overworld(img):
        return True
    return all(_near(img.getpixel(q), (176, 160, 104), 20) for q in ((60, H + 96), (200, H + 150), (128, H + 60), (20, H + 180)))


def boot2(e):
    for i in range(11):
        e.run(60)
    for _ in range(4):
        e.tap("A", 100)
    streak = 0
    for i in range(80):
        if field_any(e):
            streak += 1
            if streak >= 4:
                e.run(30)
                return True
            e.run(20)
            continue
        streak = 0
        e.tap("B", 54)
    return False


def cam_label(ram, f):
    c = ram.cam() if ram else None
    if c is None:
        return f"t{f}", None
    fl = C.cam_names(c["camFlags"]).replace("AT_HOME", "H").replace("EASING", "E").replace("SHAKING", "S").replace("CAMERA_SCRIPT", "CS")
    row = {"f": f, "flags": c["camFlags"], "cine": c["cinematicsSeen"], "scales": c["scales"], "anchors": c["anchors"],
           "visible": c.get("visible")}
    return f"t{f} {fl} s{c['scales'][1]}/{c['scales'][0]}", row


def record_intro(e, ram, out, name, title, timeout=4000, press_a=False, classic=False):
    fr, rows = [], []
    s = e.frame
    menu_at = None
    disabled = not classic
    while e.frame - s < timeout:
        if not disabled:
            # the stage off before the opening (as L+R+SELECT would): the classic path
            for _ in range(2):
                e.run(1)
                st = ram.read() if ram else None
                if ram.plausible(st) and st["enabled"] == 1 and st["arena"] != 0 and not field_any(e):
                    e.write(ram.stage[0] + 8, struct.pack("<I", 0))
                    disabled = True
                    print("stage disabled at", e.frame - s, flush=True)
        else:
            e.run(2)
        lab, row = cam_label(ram, e.frame - s)
        rows.append(row)
        fr.append(Frame(lab, e.frame - s, e.screens()))
        if menu_at is None and e.battle_menu_up():
            menu_at = e.frame - s
        if menu_at is not None and e.frame - s > menu_at + 40:
            break
        if press_a and (e.frame - s) % 60 == 0:
            e.tap("A", 0)
    out.mkdir(parents=True, exist_ok=True)
    sym = os.environ.get("DUMPSYM")
    if sym and ram is not None and sym in ram.syms:
        addr, size = ram.syms[sym]
        vals = struct.unpack(f"<{size // 4}I", e.read(addr, size))
        open(out / f"{name}_{sym}.txt", "w").write(" ".join(f"{v:#x}" for v in vals) + "\n")
    json.dump({"menu_at": menu_at, "rows": rows}, open(out / f"{name}_log.json", "w"))
    (out / "frames" / name).mkdir(parents=True, exist_ok=True)
    for f in fr[::2]:
        f.img.save(out / "frames" / name / f"{f.frame:05d}.png")
    keep = dedupe(fr, screen="both", threshold=0.002)
    for i in range(0, len(keep), 64):
        contact_sheet(keep[i:i + 64], out / f"{name}_{i // 64:02d}.png", f"{title} ({i // 64})", screen="both", cols=8, scale=0.5)
    # top-only overview, every 8th recorded frame (16 screen frames)
    contact_sheet(fr[::8], out / f"{name}_overview.png", f"{title}: top screen every 16 frames", screen="top", cols=10, scale=0.5)
    print(name, "menu at", menu_at, "frames", len(fr), flush=True)
    return menu_at


def edit_save(src, dst, at=None, mapid=None):
    args = [PY, MK, src, dst, "--heal"]
    if at:
        args += ["--at", at]
    subprocess.run(args, check=True, capture_output=True)
    if mapid is not None:
        sys.path.insert(0, EMU_DIR)
        import make_save as M
        raw = bytearray(pathlib.Path(dst).read_bytes())
        base = M.newest_partition(raw)
        m, w, x, z, d = M.location(raw, base)
        struct.pack_into("<iiiii", raw, base + M.LOCATION_OFFSET, mapid, -1, x, z, d)
        M.fix_crc(raw, base)
        pathlib.Path(dst).write_bytes(raw)


def trainer_approach(e, key, steps=1):
    for i in range(steps):
        e.hold(key, 16, 4)
    for i in range(80):
        e.run(20)
        if not field_any(e):
            e.run(10)
            if not field_any(e) and not e.in_overworld():
                return True
        e.tap("A", 10)
    return False


def main():
    rom, xmap, out, mode = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3]), sys.argv[4]
    C.XMAP_PATH = xmap
    out.mkdir(parents=True, exist_ok=True)
    sc = C.Scenario("intro_" + mode, WORK / ("sc_" + mode))
    classic = mode.endswith("classic")
    if classic:
        mode = mode[:-len("classic")]
    if mode in ("wild", "totem"):
        sav = EMU_DIR + "/saves/eterna_forest_grass.sav"
        with Emu(rom, sav) as e:
            ram = C.StageRam(e, xmap)
            assert C.boot(sc, e), "boot"
            panel = []
            if mode == "wild":
                steps = C.STAGE_ENTRY if C.STAGE_ENTRY <= C.QB_ENTRIES // 2 else C.STAGE_ENTRY - C.QB_ENTRIES
                ok = C._qb_start(sc, e, "A", steps, 0, panel, "plain", tod_taps=C.TODS.index("day"))
            else:
                ok = C._qb_start(sc, e, "X", 0, 0, panel, "totem")
            assert ok, "no battle"
            record_intro(e, ram, out, mode + ("classic" if classic else ""), f"{mode} intro{' (stage off)' if classic else ''} (every 2 frames, deduped)", classic=classic)
        return
    if mode in ("taylor", "twins"):
        at = {"taylor": "177,697,0", "twins": "175,683,0"}[mode]
        sav = str(WORK / f"{mode}.sav")
        edit_save(f"{RAW}/A2-19_route204_resonator.sav", sav, at=at)
        with Emu(rom, sav) as e:
            assert boot2(e), "boot"
            ram = C.StageRam(e, xmap)
            if classic:
                # disable as soon as the battle sets the stage up
                for i in range(3000):
                    e.run(1)
                    if i == 0:
                        e.hold("UP", 16, 4)
                    if i % 20 == 0:
                        e.tap("A", 0)
                    st = ram.read()
                    if i > 60 and ram.plausible(st) and st["enabled"] == 1 and st["arena"] != 0 and not field_any(e):
                        e.write(ram.stage[0] + 8, struct.pack("<I", 0))
                        break
            else:
                assert trainer_approach(e, "UP"), "no battle"
            record_intro(e, ram, out, mode + ("classic" if classic else ""), f"{mode} intro{' (stage off)' if classic else ''} (every 2 frames, deduped)")
        return
    if mode == "tag25":
        sav = str(WORK / "tag25.sav")
        edit_save(f"{RAW}/A2-09_jubilife_after_confession.sav", sav, at="171,706,0", mapid=345)
        with Emu(rom, sav) as e:
            assert boot2(e), "boot"
            pre = [e.snap("booted")]
            e.hold("UP", 16, 60)          # into the cave warp
            e.run(90)
            pre.append(e.snap("cave"))
            e.hold("UP", 16, 4)           # onto row 49: the 2.5 scene
            ok = False
            for i in range(200):
                e.run(20)
                if i % 10 == 0:
                    pre.append(e.snap(f"s{i}"))
                if not field_any(e) and not e.in_overworld():
                    e.run(6)
                    if not field_any(e) and not e.in_overworld():
                        ok = True
                        break
                e.tap("A", 10)
            contact_sheet(pre[-24:], out / "tag25_pre.png", "tag25: approach", screen="both", cols=8, scale=0.5)
            assert ok, "no battle"
            ram = C.StageRam(e, xmap)
            record_intro(e, ram, out, mode, "Arc 2 2.5 tag battle intro (every 2 frames, deduped)")
        return
    raise SystemExit("unknown mode " + mode)


if __name__ == "__main__":
    main()
