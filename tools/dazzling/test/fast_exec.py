#!/usr/bin/env python3
"""Fast, opt-in frontend for the Dazzling Platinum scenario runner.

This module deliberately leaves run.py unchanged.  It rewrites only the
well-known title/Continue boilerplate and delegates scenario semantics,
screenshot comparison, and process cleanup to run.py.  ``--reuse-proc`` can
also concatenate compatible field scenarios with the same save/config/env so
one GameClient process executes the whole group.

The public ``optimize_scenario`` and ``plan_reuse_groups`` functions are kept
side-effect free so run.py can import them in a later integration.
"""
import argparse
import concurrent.futures
import copy
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import run as scenario_runner  # noqa: E402 - sibling module, stdlib-only tree


BOOT_WAIT = {"wait_until": {"app": "field"}, "timeout_frames": 600}
BOOT_SETTLE = {"step": 20}


def _is_step(step, low=None, high=None):
    value = step.get("step") if isinstance(step, dict) else None
    return isinstance(value, int) and (low is None or value >= low) and (high is None or value <= high)


def _is_a_press(step):
    if not isinstance(step, dict) or step.get("press") != "A":
        return False
    return int(step.get("frames", 1)) <= 10


def strip_boot_prefix(steps):
    """Return (new_steps, stripped).

    Recognizes both the current ``step 900`` + ``press_until app=field`` form
    and the older repeated A/290-frame Continue sequence still present in
    several real scenarios.  It intentionally refuses to rewrite anything
    without the leading 900-frame title step.
    """
    steps = copy.deepcopy(list(steps or []))
    if not steps or steps[0] != {"step": 900}:
        return steps, False

    end = 1
    if end < len(steps) and "press_until" in steps[end]:
        condition = steps[end].get("press_until") or {}
        if condition.get("app") != "field" and condition.get("value") != "field":
            return steps, False
        end += 1
        # Existing scenarios conventionally settle 240 frames after Continue.
        if end < len(steps) and _is_step(steps[end], 1, 600):
            end += 1
    else:
        # Legacy boilerplate: A for 10, step 290, repeated until Continue has
        # loaded, followed by one 300/600-frame settle.  Stop at the first
        # semantic command (warp, battle, menu input, screenshot, ...).
        saw_press = False
        while end < len(steps):
            if _is_a_press(steps[end]):
                saw_press = True
                end += 1
            elif saw_press and _is_step(steps[end], 200, 900):
                end += 1
            else:
                break
        if not saw_press:
            return steps, False

    return [copy.deepcopy(BOOT_WAIT), copy.deepcopy(BOOT_SETTLE)] + steps[end:], True


def optimize_scenario(scenario, fast_boot=True):
    """Deep-copy and optimize one parsed scenario dictionary."""
    result = copy.deepcopy(scenario)
    if fast_boot:
        result["steps"], stripped = strip_boot_prefix(result.get("steps"))
        if stripped:
            result["_fast_exec_boot_prefix_stripped"] = True
    return result


def compatibility_key(scenario):
    """Save/config/env identity required for safe process reuse."""
    start = scenario.get("start") or {}
    save = os.path.abspath(os.path.expanduser(start.get("save", "")))
    return (save, json.dumps(scenario.get("config") or {}, sort_keys=True),
            json.dumps(scenario.get("env") or {}, sort_keys=True))


def _reuse_kind(scenario):
    """Return field/battle when a scenario can safely follow a warm field."""
    start = scenario.get("start") or {}
    if set(start) - {"save"}:
        return None
    steps = scenario.get("steps") or []
    semantic = [s for s in steps if "wait_until" not in s and not _is_step(s, 0, 30)]
    if not semantic:
        return None
    if "warp" in semantic[0]:
        return "field"
    if "start_battle" in semantic[0]:
        return "battle"
    return None


def plan_reuse_groups(entries):
    """Group ``[(path, optimized_scenario), ...]`` without changing order.

    Field-reset scenarios may be chained freely.  A battle-reset scenario may
    be the final member (starting a battle directly on the already warm field),
    but is never followed by another scenario because the protocol has no
    generic reset-battle command.
    """
    buckets = {}
    order = []
    singles = []
    for entry in entries:
        kind = _reuse_kind(entry[1])
        if kind is None:
            singles.append([entry])
            continue
        key = compatibility_key(entry[1])
        if key not in buckets:
            buckets[key] = {"field": [], "battle": []}
            order.append(key)
        buckets[key][kind].append(entry)

    groups = singles
    for key in order:
        fields = buckets[key]["field"]
        battles = buckets[key]["battle"]
        if fields:
            group = list(fields)
            if battles:
                group.append(battles.pop(0))
            groups.append(group)
        groups.extend([[item] for item in battles])
    return groups


def merge_group(group):
    """Build one run.py-compatible scenario from a compatible group."""
    if len(group) == 1:
        return copy.deepcopy(group[0][1])
    first = group[0][1]
    merged = {
        "name": "warm[" + ",".join((s.get("name") or os.path.basename(p)) for p, s in group) + "]",
        "start": copy.deepcopy(first.get("start") or {}),
        "config": copy.deepcopy(first.get("config") or {}),
        "env": copy.deepcopy(first.get("env") or {}),
        "requires_exists": [],
        "steps": [],
        "timeout": sum(int(s.get("timeout") or 600) for _, s in group),
    }
    seen_requirements = set()
    for _path, scenario in group:
        for requirement in scenario.get("requires_exists") or []:
            if requirement not in seen_requirements:
                seen_requirements.add(requirement)
                merged["requires_exists"].append(requirement)
        merged["steps"].extend(copy.deepcopy(scenario.get("steps") or []))
        # Check each member before the next member mutates the warm field.
        for assertion in scenario.get("assertions") or []:
            merged["steps"].append({"assert": copy.deepcopy(assertion)})
    return merged


def _run_group(group, args, work_root):
    scenario = merge_group(group)
    # Keep the temporary beside the originals so all relative save/reference/
    # battle-spec paths retain exactly the same meaning.
    scenario_dir = os.path.dirname(os.path.abspath(group[0][0]))
    fd, temp_path = tempfile.mkstemp(prefix=".fast-exec-", suffix=".json", dir=scenario_dir, text=True)
    client = None
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(scenario, handle)
        env_extra = {"SIM_BOOT_DIRECT_SAVE": "1"} if args.fast_boot or args.reuse_proc else None
        name, ok, message, client = scenario_runner.run_scenario(
            temp_path, args.game, record=args.record, update=args.update,
            timeout=args.timeout, work_root=work_root, mock=args.mock,
            env_extra=env_extra)
        return name, ok, message, len(group)
    finally:
        if client is not None:
            client.close()
        try:
            os.unlink(temp_path)
        except OSError:
            pass


def _self_test():
    canonical = [{"step": 900}, {"press_until": {"app": "field"}}, {"step": 240}, {"warp": {"map": "M"}}]
    rewritten, ok = strip_boot_prefix(canonical)
    assert ok and rewritten[:2] == [BOOT_WAIT, BOOT_SETTLE] and "warp" in rewritten[2]
    legacy = [{"step": 900}, {"press": "A", "frames": 10}, {"step": 290}, {"step": 300}, {"start_battle": {}}]
    rewritten, ok = strip_boot_prefix(legacy)
    assert ok and "start_battle" in rewritten[2]
    untouched = [{"step": 899}, {"press_until": {"app": "field"}}]
    assert strip_boot_prefix(untouched) == (untouched, False)
    print("fast_exec.py: self-test passed")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenarios", nargs="*")
    parser.add_argument("--game", default="build_macos/main")
    parser.add_argument("--scenarios-dir", default=os.path.join(HERE, "scenarios"))
    parser.add_argument("--filter", default="")
    parser.add_argument("--fast-boot", action="store_true", help="direct-load saves and strip title/Continue boilerplate")
    parser.add_argument("--reuse-proc", action="store_true", help="group compatible scenarios onto warm processes (implies fast boot)")
    parser.add_argument("-j", "--jobs", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--work-root", default=None)
    parser.add_argument("--record", action="store_true")
    parser.add_argument("--update", action="store_true")
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return _self_test()
    if args.mock:
        args.game = os.path.join(HERE, "fake_game.py")

    paths = args.scenarios or sorted(os.path.join(args.scenarios_dir, name)
                                     for name in os.listdir(args.scenarios_dir) if name.endswith(".json"))
    if args.filter:
        paths = [path for path in paths if args.filter in os.path.basename(path)]
    if not paths:
        print("fast_exec.py: no scenarios selected")
        return 2

    entries = []
    for path in paths:
        with open(path, encoding="utf-8") as handle:
            entries.append((path, optimize_scenario(json.load(handle), args.fast_boot or args.reuse_proc)))
    groups = plan_reuse_groups(entries) if args.reuse_proc else [[entry] for entry in entries]
    work_root = args.work_root or tempfile.mkdtemp(prefix="dz-fast-")
    os.makedirs(work_root, exist_ok=True)
    print("fast_exec.py: %d scenario(s), %d process group(s), fast_boot=%s, work=%s" %
          (len(entries), len(groups), args.fast_boot or args.reuse_proc, work_root))

    passed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = [pool.submit(_run_group, group, args, work_root) for group in groups]
        for future in concurrent.futures.as_completed(futures):
            name, ok, message, count = future.result()
            print("[%s] %s: %s" % ("PASS" if ok else "FAIL", name, message), flush=True)
            if ok:
                passed += count
    print("fast_exec.py: %d/%d passed" % (passed, len(entries)))
    return 0 if passed == len(entries) else 1


if __name__ == "__main__":
    sys.exit(main())
