#!/usr/bin/env python3
"""Unified stdlib-only validation gate for AI and developer changes."""
import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))


def map_changed_paths(paths):
    """Map repository paths to scenario tags and whether battle tests apply."""
    tags = set()
    battle = False
    compare_note = False
    release = False
    known = False
    for raw in paths:
        path = raw.replace("\\", "/").lstrip("./")
        if path.startswith(("src/battle/", "src/battle_anim/")):
            tags.add("battle"); battle = True; known = True
        if path.startswith(("src/overlay005/", "res/field/")):
            tags.add("field"); known = True
        if path.startswith("src/applications/"):
            tags.add("menu"); known = True
        if any(part in path for part in ("render_gpu/", "gpu/", "sim_g2", "sim_g3")):
            tags.add("visual"); compare_note = True; known = True
        if "sim_touchpad" in path or path.startswith("tools/ios/"):
            tags.add("touchpad"); known = True
        if "sim_save_flash" in path or path.startswith("src/savedata"):
            tags.add("save"); known = True
        if os.path.basename(path) in ("meson.build", "meson.options"):
            tags.add("smoke"); release = True; known = True
    if not paths or not known:
        tags = {"smoke"}
    return {"tags": sorted(tags), "battle": battle,
            "compare_backends_note": compare_note, "release": release}


def capture_changed_paths():
    paths = set()
    commands = (["git", "diff", "--name-only", "origin/main...HEAD"],
                ["git", "diff", "--name-only"],
                ["git", "diff", "--name-only", "--cached"])
    for cmd in commands:
        proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
        if proc.returncode == 0:
            paths.update(line.strip() for line in proc.stdout.splitlines() if line.strip())
    proc = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"],
                          cwd=ROOT, text=True, capture_output=True)
    if proc.returncode == 0:
        paths.update(line.strip() for line in proc.stdout.splitlines() if line.strip())
    return sorted(paths)


def run_step(name, command, results):
    print(f"gate: START {name}: {' '.join(command)}", flush=True)
    began = time.monotonic()
    proc = subprocess.run(command, cwd=ROOT)
    elapsed = round(time.monotonic() - began, 3)
    results.append({"name": name, "ok": proc.returncode == 0,
                    "returncode": proc.returncode, "elapsed_sec": elapsed,
                    "command": command})
    print(f"gate: {'PASS' if proc.returncode == 0 else 'FAIL'} {name} ({elapsed:.2f}s)", flush=True)
    return proc.returncode == 0


def patch_integrity(changed, results):
    relevant = any(p == "subprojects/libntr" or p.startswith("subprojects/libntr/")
                   or p in ("tools/macos/patches/libntr.patch",
                            "tools/macos/patches/libntrsystem.patch") for p in changed)
    if not relevant:
        return True
    ok = run_step("patch-diff-check", ["git", "diff", "--check"], results)
    libntr = os.path.join(ROOT, "subprojects", "libntr")
    if os.path.isdir(os.path.join(libntr, ".git")) or os.path.isfile(os.path.join(libntr, ".git")):
        ok = run_step("libntr-diff-check", ["git", "-C", libntr, "diff", "--check"], results) and ok
    # --numstat parses every patch without mutating a checkout; applicability is
    # covered by the clean subproject diff check when the vendor tree changed.
    for filename in ("libntr.patch", "libntrsystem.patch"):
        patch = os.path.join(ROOT, "tools", "macos", "patches", filename)
        if os.path.exists(patch):
            ok = run_step(f"parse-{filename}", ["git", "apply", "--numstat", patch], results) and ok
    return ok


def find_release_game(explicit):
    if explicit:
        return explicit
    for candidate in ("build_linux_rel/main", "build_macos_release/main"):
        if os.path.exists(os.path.join(ROOT, candidate)):
            return candidate
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", choices=("smoke", "fast", "full"), default="smoke")
    parser.add_argument("--changed", action="store_true")
    parser.add_argument("--full", action="store_true", help="alias for --tier full")
    parser.add_argument("--release-game")
    parser.add_argument("--compare-backends", action="store_true")
    parser.add_argument("--json-report")
    parser.add_argument("--skip-static", action="store_true")
    parser.add_argument("--skip-patches", action="store_true")
    parser.add_argument("--skip-battle", action="store_true")
    args = parser.parse_args(argv)
    began = time.monotonic()
    results = []
    changed = capture_changed_paths() if args.changed else []
    mapping = map_changed_paths(changed) if args.changed else {
        "tags": [], "battle": False, "compare_backends_note": False, "release": False}
    if args.changed:
        print("gate: changed=" + (",".join(changed) if changed else "<none>"))
        print("gate: tags=" + ",".join(mapping["tags"]))
        if mapping["compare_backends_note"] and not args.compare_backends:
            print("gate: NOTE GPU paths changed; consider --compare-backends when the GPU renderer is available")

    ok = True
    if not args.skip_static:
        ok = run_step("static", [sys.executable, os.path.join(HERE, "static_checks.py")], results) and ok
    if not args.skip_patches:
        ok = patch_integrity(changed, results) and ok
    if mapping["battle"] and not args.skip_battle:
        ok = run_step("battle", [sys.executable, os.path.join(ROOT, "tools", "battle", "run_tests.py")], results) and ok

    run_cmd = [sys.executable, os.path.join(HERE, "run.py")]
    if args.changed and mapping["tags"] != ["smoke"]:
        run_cmd += [item for tag in mapping["tags"] for item in ("--tag", tag)]
    else:
        run_cmd += ["--tier", "full" if args.full else args.tier]
    if args.compare_backends:
        run_cmd.append("--compare-backends")
    ok = run_step("scenarios", run_cmd, results) and ok

    release_game = find_release_game(args.release_game)
    if release_game and (args.release_game or mapping["release"]):
        release_cmd = [sys.executable, os.path.join(HERE, "run.py"),
                       "--game", release_game, "--tier", "smoke"]
        ok = run_step("release-smoke", release_cmd, results) and ok

    report = {"ok": ok, "total_sec": round(time.monotonic() - began, 3),
              "changed_paths": changed, "mapping": mapping, "steps": results}
    if args.json_report:
        os.makedirs(os.path.dirname(os.path.abspath(args.json_report)), exist_ok=True)
        with open(args.json_report, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, sort_keys=True); f.write("\n")
    print(f"gate: {'PASS' if ok else 'FAIL'} {sum(r['ok'] for r in results)}/{len(results)} steps ({report['total_sec']:.2f}s)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
