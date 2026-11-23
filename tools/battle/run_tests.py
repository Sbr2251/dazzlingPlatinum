#!/usr/bin/env python3
"""Run the headless battle specifications, optionally in parallel.

Examples:
  python3 tools/battle/run_tests.py --fast
  python3 tools/battle/run_tests.py -j 4 --reuse-proc --json-report report.json

``--reuse-proc`` assigns a group of specs to each worker and reuses that
worker's field process.  Tests remain sequential within a worker.
"""
import argparse
import concurrent.futures
import glob
import json
import os
import platform
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim as simmod


def check(result, events, expect):
    errs = []
    if expect.get("battle_ended", True) and not result:
        errs.append("no result")
    if "winner" in expect and result.get("winner") != expect["winner"]:
        errs.append(f"winner {result.get('winner')} != {expect['winner']}")
    if "damage_to_battler" in expect and not any(
            e.get("type") == "damage" and e.get("battler") == expect["damage_to_battler"] for e in events):
        errs.append("no damage event to battler")
    battlers = (result.get("final_battle") or {}).get("battlers", [{}])
    active = battlers[0].get("species") if battlers else None
    if "active_species" in expect and not any(
            e.get("type") in ("switch", "switch_in") and
            (e.get("to") or e.get("species")) == expect["active_species"] for e in events) and active != expect["active_species"]:
        errs.append("active species not observed")
    if "party_species_after" in expect:
        party = result.get("party_after") or []
        if not party or party[0].get("species") != expect["party_species_after"]:
            errs.append("party species after battle mismatch (mega revert check)")
    if "max_turns" in expect and result.get("turns", 999) > expect["max_turns"]:
        errs.append("too many turns")
    if "events_contain" in expect and not any(e.get("type") == expect["events_contain"] for e in events):
        errs.append(f"no {expect['events_contain']} event")
    if "effectiveness" in expect and not any(
            e.get("type") == "damage" and e.get("effectiveness") == expect["effectiveness"] for e in events):
        errs.append(f"no {expect['effectiveness']} damage event")
    if expect.get("crit_damage") and not any(e.get("type") == "damage" and e.get("critical") for e in events):
        errs.append("no critical damage event")
    return errs


def load_case(path):
    with open(path, encoding="utf-8") as src:
        test = json.load(src)
    return {"path": path, "test": test, "name": test.get("name", os.path.basename(path))}


def run_case(case, args, runner=None):
    test = case["test"]
    owned_runner = runner is None
    started = time.monotonic()
    if owned_runner:
        runner = simmod.BattleRunner(args.build_dir, args.save,
                                     seed=int(test["spec"].get("seed", 42)), fast=args.fast)
    try:
        result = runner.run_battle(test["spec"], policy=test.get("policy", "first"))
        errs = check(result, runner.events, test.get("expect", {}))
    except Exception as exc:
        errs, result = [str(exc)], None
    finally:
        if owned_runner:
            runner.close()
    return {"name": case["name"], "path": case["path"], "ok": not errs,
            "errors": errs, "seconds": round(time.monotonic() - started, 3),
            "result": result}


def run_chunk(chunk, args):
    """One worker, and therefore at most one warm game process."""
    if not args.reuse_proc:
        return [run_case(case, args) for case in chunk]
    work = tempfile.mkdtemp(prefix="battle-tests-worker-")
    runner = simmod.BattleRunner(args.build_dir, args.save,
                                 seed=int(chunk[0]["test"]["spec"].get("seed", 42)),
                                 fast=args.fast, work=work)
    try:
        return [run_case(case, args, runner) for case in chunk]
    finally:
        runner.close()
        # BattleRunner only removes implicit temp dirs in sim.py's CLI.
        import shutil
        shutil.rmtree(work, ignore_errors=True)


def main():
    default_build = "build_macos" if platform.system() == "Darwin" else "build_linux"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", default=default_build)
    parser.add_argument("--filter", default="")
    parser.add_argument("--save")
    parser.add_argument("--fast", action="store_true")
    parser.add_argument("--tests", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests"))
    parser.add_argument("-j", "--jobs", type=int, default=2)
    parser.add_argument("--reuse-proc", action="store_true",
                        help="reuse one booted game process per worker")
    parser.add_argument("--json-report", help="write a structured test report")
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be at least 1")

    if platform.system() == "Linux":
        # dbg-battle-fixtures hook: stable, inexpensive CI defaults.
        os.environ.setdefault("LP_NUM_THREADS", "2")
        os.environ.setdefault("SDL_VIDEO_DRIVER", "offscreen")

    if not args.save:
        args.save = next((path for path in simmod.DEFAULT_SAVES if os.path.exists(path)), None)
    if not args.save:
        parser.error("no test save found; pass --save or regenerate the in-repo fixture")

    cases = [load_case(path) for path in sorted(glob.glob(os.path.join(args.tests, "*.json")))]
    cases = [case for case in cases if not args.filter or args.filter in case["name"]]
    started = time.monotonic()
    # Injected wild battles can safely share a field process.  The engine's
    # special battle modes retain mode-specific globals, so isolate those;
    # also recycle after two injections to avoid unbounded overlay residue.
    if args.reuse_proc:
        chunks, pending_wild = [], []
        for case in cases:
            kind = case["test"].get("spec", {}).get("battle_type", "wild")
            if kind == "wild":
                pending_wild.append(case)
                if len(pending_wild) == 2:
                    chunks.append(pending_wild)
                    pending_wild = []
            else:
                chunks.append([case])
        if pending_wild:
            chunks.append(pending_wild)
    else:
        chunks = [[case] for case in cases]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        nested = list(pool.map(lambda chunk: run_chunk(chunk, args), chunks))
    by_path = {entry["path"]: entry for group in nested for entry in group}
    results = [by_path[case["path"]] for case in cases]
    elapsed = round(time.monotonic() - started, 3)

    for entry in results:
        detail = "; ".join(entry["errors"])
        if entry["ok"]:
            result = entry["result"] or {}
            detail = f"winner={result.get('winner')} turns={result.get('turns')}"
        print(("PASS " if entry["ok"] else "FAIL ") + entry["name"] + " " + detail)
    passed = sum(entry["ok"] for entry in results)
    print(f"battle tests: {passed}/{len(results)} passed in {elapsed:.3f}s")

    if args.json_report:
        report = {"schema_version": 1, "ok": passed == len(results),
                  "summary": {"total": len(results), "passed": passed,
                              "failed": len(results) - passed, "seconds": elapsed,
                              "jobs": args.jobs, "reuse_proc": args.reuse_proc,
                              "fast": args.fast},
                  "tests": results}
        report_dir = os.path.dirname(os.path.abspath(args.json_report))
        os.makedirs(report_dir, exist_ok=True)
        with open(args.json_report, "w", encoding="utf-8") as out:
            json.dump(report, out, indent=2, sort_keys=True)
            out.write("\n")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
