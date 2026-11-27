#!/usr/bin/env python3
"""Headless in-game verification for Route 222 — Violet-Lit Coast (standard library only).

Runs a built game (`main`, SIM_CONTROL=stdio; the harness of tools/everspring/verify_route218.py) with this work
tree's Route 222 data overlaid on it, so a build of the base commit (no rebuild needed) shows the redesign:

  * land_data.narc members 149..151   <- res/field/mapmodels/data/map_data_149..151.bin (compress_land_data.py)
  * map_tex_set.narc member 81        <- map_texture_set_081.nsbtx
  * arealight.narc member 9           <- lighting_set_009.json (tools/jsoncnv/lighting.py)
  * scr_seq.narc / zone_event.narc / pl_msg.narc route_222 members <- scripts.s / events.json / route_222.json
    (make_script_bin.sh, mapproc, msgenc from the build dir)

Usage:
  python3 tools/routes/r222/verify_route222.py <base build_dir> <output_dir> [--night] [--keep]

The build dir must be built from this branch's base (the routes-wave2 contract commit) so every other archive member
matches. Tour: the three showcase viewpoints (and a few more) by day (and night with --night), the stranded
Pokemon and both lamp signs (dialogue opens and closes), walking the promenade past the lamps, the west seam into
Valor Lakefront and the Sunyshore gate warp. Exit status 0 when every assertion passes.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "everspring"))
sys.path.insert(0, os.path.join(ROOT, "tools", "coronet_lava"))
import verify_route218 as V  # noqa: E402
import narc  # noqa: E402

ROUTE = "MAP_HEADER_ROUTE_222"
VALOR = "MAP_HEADER_VALOR_LAKEFRONT"
GATE = "MAP_HEADER_ROUTE_222_GATE_TO_SUNYSHORE_CITY"

# (name, x, z, facing): the player stands there; the camera centres on the player
VIEWPOINTS = [
    ("01_blackout_promenade", 792, 777, "DIR_NORTH"),     # showcase 1: the dead lamps on the stone promenade
    ("02_stranded_beach", 790, 788, "DIR_SOUTH"),         # showcase 2: Psyduck on the violet tide line
    ("03_sunyshore_violet_approach", 821, 788, "DIR_EAST"),   # showcase 3: the violet lamps by the gate
    ("04_valor_cliff_lamps", 747, 790, "DIR_SOUTH"),
    ("05_beach_west_crystals", 768, 788, "DIR_SOUTH"),
    ("06_east_strip_prinplup", 811, 795, "DIR_EAST"),
]
INTERACTIONS = [  # (shot, label, stand x, z, facing)
    ("07_psyduck", "Route222_StrandedPsyduck", 791, 789, "DIR_SOUTH"),
    ("08_piplup", "Route222_StrandedPiplup", 803, 790, "DIR_SOUTH"),
    ("09_prinplup", "Route222_StrandedPrinplup", 812, 795, "DIR_EAST"),
    ("10_blackout_lamp", "Route222_BlackoutLamp", 792, 776, "DIR_NORTH"),
    ("11_violet_lamp", "Route222_VioletLamp", 821, 790, "DIR_WEST"),
]


def sh(cmd, **kw):
    subprocess.run(cmd, check=True, capture_output=True, **kw)


def replace_members(src, dst, members):
    header, btnf, files = narc.read_files(src)
    for idx, data in members.items():
        assert 0 <= idx < len(files), (src, idx, len(files))
        files[idx] = data
    narc.write_files(dst, header, btnf, files)


def naix_index(path, name):
    for line in open(path):
        p = line.split()
        if len(p) == 3 and p[0] == "#define" and p[1] == name:
            return int(p[2])
    raise KeyError(name)


def assemble(build, scratch):
    """A virtual build dir: symlinks to `build`, with data/, fielddata/, msgdata/ mirrored file by file and the
    Route 222 archives replaced. -> path."""
    vdir = os.path.join(scratch, "build")
    os.makedirs(vdir)
    mirrored = ("data", "fielddata", "msgdata")
    for e in os.listdir(build):
        src = os.path.join(build, e)
        if e in mirrored:
            for dp, dns, fns in os.walk(src):
                rel = os.path.relpath(dp, build)
                os.makedirs(os.path.join(vdir, rel), exist_ok=True)
                for f in fns:
                    os.symlink(os.path.join(dp, f), os.path.join(vdir, rel, f))
        else:
            os.symlink(src, os.path.join(vdir, e))
    work = os.path.join(scratch, "work")
    os.makedirs(work)

    def out(rel):
        p = os.path.join(vdir, rel)
        os.remove(p)
        return p
    # land data
    members = {}
    for c in (149, 150, 151):
        dst = os.path.join(work, f"map_data_{c}.bin")
        sh([sys.executable, os.path.join(ROOT, "tools/scripts/compress_land_data.py"),
            os.path.join(ROOT, f"res/field/mapmodels/data/map_data_{c}.bin"), dst])
        members[c] = open(dst, "rb").read()
    replace_members(os.path.join(build, "fielddata/land_data/land_data.narc"), out("fielddata/land_data/land_data.narc"),
                    members)
    # texture set 081
    replace_members(os.path.join(build, "fielddata/areadata/area_map_tex/map_tex_set.narc"),
                    out("fielddata/areadata/area_map_tex/map_tex_set.narc"),
                    {81: open(os.path.join(ROOT, "res/field/mapmodels/texture_sets/map_texture_set_081.nsbtx"), "rb").read()})
    # lighting 009
    lt = os.path.join(work, "lighting_set_009")
    sh([sys.executable, os.path.join(ROOT, "tools/jsoncnv/lighting.py"),
        os.path.join(ROOT, "res/field/lighting/lighting_set_009.json"), lt], env=dict(os.environ, PYTHONPATH=build))
    replace_members(os.path.join(build, "data/arealight.narc"), out("data/arealight.narc"), {9: open(lt, "rb").read()})
    # text
    msgenc = os.path.join(build, "tools/msgenc/msgenc")
    os.makedirs(os.path.join(work, "res/text/bank"))
    tb = os.path.join(work, "route_222.msg")
    sh([msgenc, "-e", "--json", "-c", os.path.join(build, "tools/msgenc/charmap.txt"), "-H",
        os.path.join(work, "res/text/bank/route_222.h"), os.path.join(ROOT, "res/text/route_222.json"), tb])
    replace_members(os.path.join(build, "msgdata/pl_msg.narc"), out("msgdata/pl_msg.narc"),
                    {naix_index(os.path.join(build, "res/text/pl_msg.naix"), "route_222"): open(tb, "rb").read()})
    # events (mapproc over this tree's maps; it needs the common script-label headers of the build)
    mo = os.path.join(work, "maps")
    os.makedirs(mo)
    for f in os.listdir(os.path.join(build, "res/field/maps")):
        if f.startswith("scripts_") and f.endswith(".h"):
            shutil.copy(os.path.join(build, "res/field/maps", f), mo)
    sh([os.path.join(build, "tools/dataproc/mapproc"), "-M", os.path.join(mo, "x.d"), "-o", mo,
        os.path.join(ROOT, "include/constants/fieldmap.h"), os.path.join(ROOT, "res/field/maps")], cwd=mo)
    _, _, mine = narc.read_files(os.path.join(mo, "zone_event.narc"))
    _, _, base = narc.read_files(os.path.join(build, "fielddata/eventdata/zone_event.narc"))
    changed = [i for i, (a, b) in enumerate(zip(mine, base)) if a != b]
    assert len(mine) == len(base) and len(changed) == 1, f"zone_event: members changed {changed}"
    shutil.copy(os.path.join(mo, "zone_event.narc"), out("fielddata/eventdata/zone_event.narc"))
    # scripts
    sb = os.path.join(work, "scripts_route_222")
    sh([os.path.join(ROOT, "tools/scripts/make_script_bin.sh"), "-i", work, "-i", mo, "-i", os.path.join(ROOT, "include"),
        "-i", os.path.join(ROOT, "asm"), "-i", build, "--enumproc", os.path.join(build, "tools/enumproc/enumproc"),
        os.path.join(ROOT, "res/field/maps/route_222/scripts.s"), "-O", sb], cwd=work)
    replace_members(os.path.join(build, "fielddata/script/scr_seq.narc"), out("fielddata/script/scr_seq.narc"),
                    {naix_index(os.path.join(build, "res/field/maps/scr_seq.naix"), "scripts_route_222"): open(sb, "rb").read()})
    print(f"assembled overlay build in {vdir} (zone_event member {changed[0]} replaced)", flush=True)
    return vdir


def interact(game, out_dir, run, shot, label, x, z, facing, results, shots):
    V.warp(game, x, z, facing, results, mapname=ROUTE)
    game.cmd({"cmd": "press", "keys": ["A"], "frames": 8})
    opened = False
    st = game.state()
    for _ in range(30):
        game.cmd({"cmd": "step", "frames": 10})
        st = game.state()
        if st.get("message_waiting") or st.get("script") is not None:
            opened = True
            break
    V.expect(opened, f"{label} from ({x}, {z}) {facing} opened (script={st.get('script')}, "
             f"msg={st.get('message_waiting')})", results)
    game.cmd({"cmd": "step", "frames": 60})
    V.shoot(game, out_dir, f"{run}_{shot}", shots, results)
    presses = 0
    for _ in range(40):
        st = game.state()
        if V.is_field_idle(st):
            break
        game.cmd({"cmd": "press", "keys": ["A"], "frames": 8})
        game.cmd({"cmd": "step", "frames": 50})
        presses += 1
    st = V.settle(game, 300)
    m, pos = V.where(st)
    V.expect(V.is_field_idle(st) and m == ROUTE and pos == (x, z),
             f"{label} closed cleanly after {presses} presses, player idle at {pos}", results)


def tour(game, out_dir, run, results, shots, gameplay):
    for i, (name, x, z, facing) in enumerate(VIEWPOINTS):
        V.warp(game, x, z, facing, results, mapname=ROUTE)
        if i == 0:
            objs = game.cmd({"cmd": "objects"})
            if objs.get("ok"):
                game.log.write(f"## Route 222 objects ({run}): {json.dumps(objs.get('objects', []))}\n")
                ids = {(o.get("x"), o.get("z")) for o in objs.get("objects", [])}
                for xx, zz in ((791, 790), (803, 791), (813, 795)):
                    V.expect((xx, zz) in ids or not ids, f"stranded Pokemon object present at ({xx}, {zz})", results)
        V.shoot(game, out_dir, f"{run}_{name}", shots, results)
    if not gameplay:
        return
    for shot, label, x, z, facing in INTERACTIONS:
        interact(game, out_dir, run, shot, label, x, z, facing, results, shots)
    # walk the promenade under the dead lamps (792..797 along z 777)
    V.warp(game, 786, 777, "DIR_EAST", results, mapname=ROUTE)
    for k in range(1, 9):
        st = V.walk_one(game, "RIGHT")
        V.expect(V.where(st) == (ROUTE, (786 + k, 777)), f"promenade step {k}/8 reached {V.where(st)[1]}", results)
    V.shoot(game, out_dir, f"{run}_12_promenade_walk", shots, results)
    # the lamp verge tiles in 149 are blocked now: walking into (756, 780) from (755, 780) must not move
    V.warp(game, 755, 780, "DIR_EAST", results, mapname=ROUTE)
    game.cmd({"cmd": "press", "keys": ["RIGHT"], "frames": 16})
    game.cmd({"cmd": "step", "frames": 30})
    st = V.settle(game, 120)
    V.expect(V.where(st) == (ROUTE, (755, 780)), f"lamp verge (756, 780) blocks (player at {V.where(st)[1]})", results)
    # west seam into Valor Lakefront
    V.warp(game, 737, 789, "DIR_WEST", results, mapname=ROUTE)
    st = V.walk_until_map(game, "LEFT", VALOR, max_steps=3)
    V.expect(V.where(st)[0] == VALOR, f"west seam: walked into {V.where(st)[0]} at {V.where(st)[1]}", results)
    V.shoot(game, out_dir, f"{run}_13_valor_seam", shots, results)
    # Sunyshore gate warp
    V.warp(game, 824, 790, "DIR_EAST", results, mapname=ROUTE)
    st = V.walk_until_map(game, "RIGHT", GATE)
    V.expect(V.where(st)[0] == GATE, f"Sunyshore gate (825, 790) warped to {V.where(st)[0]}", results)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("build_dir")
    ap.add_argument("output_dir")
    ap.add_argument("--night", action="store_true")
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--save", default=V.DEFAULT_SAVE)
    ap.add_argument("--renderer", default="auto")
    args = ap.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    scratch = tempfile.mkdtemp(prefix="dz-r222-")
    results, shots, ok = [], [], True
    try:
        vbuild = assemble(os.path.abspath(args.build_dir), scratch)
        for run in (("day", "night") if args.night else ("day",)):
            run_dir = os.path.join(scratch, f"run_{run}")
            os.makedirs(run_dir)
            env = V.build_extra_env(run, False, args.renderer, False)
            with open(os.path.join(args.output_dir, f"log_{run}.txt"), "w") as log:
                game = V.Game(vbuild, run_dir, log, extra_env=env)
                try:
                    V.boot(game, args.save, results)
                    tour(game, args.output_dir, run, results, shots, gameplay=(run == "day"))
                except V.Failure as e:
                    ok = False
                    if not results or not results[-1].startswith("FAIL"):
                        results.append(f"FAIL {e}")
                        print(results[-1], flush=True)
                    try:
                        log.write("LAST_STATE: " + json.dumps(game.state()) + "\n")
                        V.shoot(game, args.output_dir, f"{run}_failure", shots, results)
                    except Exception:
                        pass
                finally:
                    game.close()
                    if os.path.exists(game.stderr_path):
                        shutil.copy(game.stderr_path, os.path.join(args.output_dir, f"game_{run}.stderr.log"))
                log.write("\n".join(results) + "\n")
    finally:
        if not args.keep:
            shutil.rmtree(scratch, ignore_errors=True)
    print(f"{sum(1 for r in results if r.startswith('ok'))} ok, {sum(1 for r in results if r.startswith('FAIL'))} "
          f"failed; screenshots in {args.output_dir}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
