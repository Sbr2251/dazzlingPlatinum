#!/usr/bin/env python3
"""Static checks for Dazzling Platinum content. No game build needed.

Usage: python3 tools/dazzling/test/static_checks.py [--root DIR] [--check NAME] [-v]
Exit 1 if any check fails. Each failure line is: <check>: <file>:<line>: <message>

Checks:
  script_targets   every GoTo/Call/movement target is a label in its file
                   (folds in tools/dazzling/check_script_targets.py)
  text_labels      every Message-family label used by a script exists in a
                   text bank that script includes (res/text/bank/<bank>.h ->
                   res/text/<bank>.json)
  event_scripts    every events.json "script" reference is a defined label
  json_data        events.json / header.json / data JSON validate
                   (required fields, types, known constants where a
                   generated constants list exists)
  curly            no curly apostrophes (U+2018/U+2019) in text/data beyond
                   the grandfathered baseline (tools/dazzling/test/
                   curly_baseline.json). Vanilla pret banks use U+2019 as
                   the in-game apostrophe glyph, so pre-existing files are
                   baselined by count; any NEW file or increased count fails.
                   Regenerate (review the diff!): --write-curly-baseline
  waitfanfare      after WaitFanfare: the next command must be a real script
                   command (known macro), and a GoTo/Call there must not
                   target movement data or a constant. Regression guard for
                   the pret-merge damage repaired in 02a21151a8.
"""
import argparse, glob, json, os, re, sys
from collections import Counter

LABEL_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*):\s*$')
IDENT_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
MSG_CMDS = ("Message", "MessageInstant", "MessageUnown", "NPCMessage", "EventMessage")
SCRIPT_GLOBS = ["res/field/maps/*/scripts.s", "res/field/maps/*/init.s", "res/field/scripts/*.s"]

def read_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read().splitlines()

def script_files(root):
    out = []
    for pat in SCRIPT_GLOBS:
        out += glob.glob(os.path.join(root, pat))
    return sorted(out)

def parse_script(path):
    labels, label_order = {}, []
    for i, line in enumerate(read_lines(path)):
        m = LABEL_RE.match(line)
        if m:
            labels[m.group(1)] = i + 1
            label_order.append((m.group(1), i))
    return labels, label_order

def strip_comment(line):
    return line.split("//")[0].strip()

# ---------------------------------------------------------------- commands
def load_command_names(root):
    """Real script commands = .macro names in asm/macros/scrcmd.inc (+ movement)."""
    names = set()
    for rel in ("asm/macros/scrcmd.inc", "asm/macros/movement.inc"):
        p = os.path.join(root, rel)
        if os.path.exists(p):
            for line in read_lines(p):
                m = re.match(r'\s*\.macro\s+([A-Za-z_][\w]*)', line)
                if m:
                    names.add(m.group(1))
    return names

_MOVE_CMDS = None
def movement_label_set(root, path, lines, labels):
    """Labels whose block is movement data (first commands are movement macros)."""
    global _MOVE_CMDS
    movement = set()
    if _MOVE_CMDS is None:
        _MOVE_CMDS = set()
        p = os.path.join(root, "asm/macros/movement.inc")
        if os.path.exists(p):
            for line in read_lines(p):
                m = re.match(r'\s*\.macro\s+([A-Za-z_][\w]*)', line)
                if m:
                    _MOVE_CMDS.add(m.group(1))
    move_cmds = _MOVE_CMDS
    starts = sorted(labels.items(), key=lambda kv: kv[1])
    for idx, (name, lineno) in enumerate(starts):
        end = starts[idx + 1][1] - 1 if idx + 1 < len(starts) else len(lines)
        for line in lines[lineno:end]:
            s = strip_comment(line)
            if not s:
                continue
            first = s.split()[0]
            if first in move_cmds or first.startswith("Movement"):
                movement.add(name)
            break
    return movement

# ---------------------------------------------------------------- checks
def check_script_targets(root):
    errs = []
    for path in script_files(root):
        rel = os.path.relpath(path, root)
        lines = read_lines(path)
        labels, _ = parse_script(path)
        for i, line in enumerate(lines):
            s = strip_comment(line)
            if not s:
                continue
            op = s.split()[0]
            if re.match(r'^(GoTo|Call)(If\w*)?$', op) or op in ("ApplyMovement", "ApplyFreeCameraMovement"):
                args = [a.strip() for a in s[len(op):].split(",")]
                target = args[-1]
                if IDENT_RE.match(target) and target not in labels:
                    errs.append(f"script_targets: {rel}:{i+1}: {op} target '{target}' is not a label in this file")
    return errs

def check_text_labels(root):
    errs = []
    bank_cache = {}
    def bank_ids(bank):
        if bank not in bank_cache:
            p = os.path.join(root, "res/text", bank + ".json")
            ids = set()
            if os.path.exists(p):
                try:
                    data = json.load(open(p, encoding="utf-8"))
                    ids = {m.get("id") for m in data.get("messages", []) if m.get("id")}
                except Exception:
                    pass
            bank_cache[bank] = ids
        return bank_cache[bank]
    for path in script_files(root):
        rel = os.path.relpath(path, root)
        text = "\n".join(read_lines(path))
        banks = re.findall(r'res/text/bank/([\w]+)\.h', text)
        if not banks:
            continue
        allowed = set()
        for b in banks:
            allowed |= bank_ids(b)
        if not allowed:
            continue
        for i, line in enumerate(text.splitlines()):
            s = strip_comment(line)
            m = re.match(r'(?:' + "|".join(MSG_CMDS) + r')\s+([A-Za-z_][\w]*)', s)
            if m and m.group(1) not in allowed:
                errs.append(f"text_labels: {rel}:{i+1}: text label '{m.group(1)}' not in included bank(s) {banks} (res/text/<bank>.json)")
    return errs

def all_labels(root):
    labels = set()
    for path in script_files(root):
        labels |= set(parse_script(path)[0])
    return labels

def check_event_scripts(root):
    errs, labels = [], all_labels(root)
    for path in sorted(glob.glob(os.path.join(root, "res/field/maps/*/events.json"))):
        rel = os.path.relpath(path, root)
        try:
            data = json.load(open(path, encoding="utf-8"))
        except Exception as e:
            errs.append(f"event_scripts: {rel}: invalid JSON: {e}")
            continue
        def walk(obj, where=""):
            if isinstance(obj, dict):
                ref = obj.get("script")
                if isinstance(ref, str) and ref and ref not in labels:
                    errs.append(f"event_scripts: {rel}: script reference '{ref}'{where} is not a defined script label")
                for v in obj.values():
                    walk(v, where)
            elif isinstance(obj, list):
                for v in obj:
                    walk(v, where)
        walk(data)
    return errs

def load_consts(root, *relpaths):
    consts = set()
    for rel in relpaths:
        p = os.path.join(root, rel)
        if os.path.exists(p):
            if rel.endswith(".txt"):
                consts |= {l.strip() for l in read_lines(p) if l.strip()}
            else:
                for line in read_lines(p):
                    consts |= set(re.findall(r'\b([A-Z][A-Z0-9_]{2,})\s*(?:=[^,]*)?,?\s*(?://.*)?$', line.strip()))
    return consts

def check_json_data(root):
    errs = []
    text_banks = load_consts(root, "generated/text_banks.txt")
    weathers = load_consts(root, "include/constants/overworld_weather.h")
    map_types = set()
    mh = os.path.join(root, "include/constants/fieldmap.h")
    if os.path.exists(mh):
        map_types = {m for m in re.findall(r'\b(MAP_TYPE_[A-Z0-9_]+)', "\n".join(read_lines(mh)))}
    header_required = {"areaData": str, "mapGroup": str, "locationName": str, "textBank": str,
                       "weather": str, "cameraType": str, "mapType": str,
                       "musicDay": str, "musicNight": str, "isBikeAllowed": bool,
                       "isRunningAllowed": bool, "isEscapeRopeAllowed": bool, "isFlyAllowed": bool}
    for path in sorted(glob.glob(os.path.join(root, "res/field/maps/*/header.json"))):
        rel = os.path.relpath(path, root)
        try:
            data = json.load(open(path, encoding="utf-8"))
        except Exception as e:
            errs.append(f"json_data: {rel}: invalid JSON: {e}"); continue
        for key, typ in header_required.items():
            if key not in data:
                errs.append(f"json_data: {rel}: header.json missing required field '{key}'")
            elif not isinstance(data[key], typ):
                errs.append(f"json_data: {rel}: header field '{key}' should be {typ.__name__}, got {type(data[key]).__name__}")
        if text_banks and data.get("textBank") not in text_banks:
            errs.append(f"json_data: {rel}: unknown textBank constant '{data.get('textBank')}'")
        if weathers and data.get("weather") not in weathers:
            errs.append(f"json_data: {rel}: unknown weather constant '{data.get('weather')}'")
        if map_types and data.get("mapType") not in map_types:
            errs.append(f"json_data: {rel}: unknown mapType constant '{data.get('mapType')}'")
    for path in sorted(glob.glob(os.path.join(root, "res/field/maps/*/events.json"))):
        rel = os.path.relpath(path, root)
        try:
            data = json.load(open(path, encoding="utf-8"))
        except Exception as e:
            errs.append(f"json_data: {rel}: invalid JSON: {e}"); continue
        if not isinstance(data, dict):
            errs.append(f"json_data: {rel}: events.json top level must be an object"); continue
        for section, items in data.items():
            if not isinstance(items, list):
                errs.append(f"json_data: {rel}: events section '{section}' must be a list"); continue
            for idx, item in enumerate(items):
                if not isinstance(item, dict):
                    errs.append(f"json_data: {rel}: {section}[{idx}] must be an object"); continue
                for coord in ("x", "z"):
                    if coord in item and not isinstance(item[coord], (int, float)):
                        errs.append(f"json_data: {rel}: {section}[{idx}].{coord} must be a number")
    # data JSON: moves / items / pokemon
    for path in sorted(glob.glob(os.path.join(root, "res/moves/*/data.json"))):
        rel = os.path.relpath(path, root)
        try:
            d = json.load(open(path, encoding="utf-8"))
        except Exception as e:
            errs.append(f"json_data: {rel}: invalid JSON: {e}"); continue
        for key in ("name", "description", "class", "type", "power", "accuracy", "pp", "effect", "range"):
            if key not in d:
                errs.append(f"json_data: {rel}: move data missing required field '{key}'")
    for path in sorted(glob.glob(os.path.join(root, "res/items/data/*.json"))):
        rel = os.path.relpath(path, root)
        try:
            d = json.load(open(path, encoding="utf-8"))
        except Exception as e:
            errs.append(f"json_data: {rel}: invalid JSON: {e}"); continue
        for key in ("name", "plural", "article", "description"):
            if key not in d:
                errs.append(f"json_data: {rel}: item data missing required field '{key}' (missing article/plural gives 'picked up ???')")
    for path in sorted(glob.glob(os.path.join(root, "res/pokemon/*/data.json"))):
        rel = os.path.relpath(path, root)
        try:
            d = json.load(open(path, encoding="utf-8"))
        except Exception as e:
            errs.append(f"json_data: {rel}: invalid JSON: {e}"); continue
        for key in ("base_stats", "types", "abilities"):
            if key not in d:
                errs.append(f"json_data: {rel}: pokemon data missing required field '{key}'")
        bs = d.get("base_stats") or {}
        for stat in ("hp", "attack", "defense", "speed", "special_attack", "special_defense"):
            if stat not in bs:
                errs.append(f"json_data: {rel}: pokemon base_stats missing '{stat}'")
    return errs

CURLY = ("\u2018", "\u2019")
def curly_counts(root):
    counts = Counter()
    pats = ["res/text/*.json", "res/moves/*/data.json", "res/items/data/*.json", "res/pokemon/*/data.json"]
    for pat in pats:
        for path in sorted(glob.glob(os.path.join(root, pat))):
            try:
                text = open(path, encoding="utf-8").read()
            except Exception:
                continue
            n = sum(text.count(c) for c in CURLY)
            if n:
                counts[os.path.relpath(path, root)] = n
    return counts

def check_curly(root, args):
    baseline_path = os.path.join(root, "tools/dazzling/test/curly_baseline.json")
    counts = curly_counts(root)
    if args.write_curly_baseline:
        with open(baseline_path, "w", encoding="utf-8") as f:
            json.dump(dict(sorted(counts.items())), f, indent=1, sort_keys=True)
            f.write("\n")
        print(f"curly: wrote baseline for {len(counts)} files to {baseline_path}")
        return []
    baseline = {}
    if os.path.exists(baseline_path):
        baseline = json.load(open(baseline_path, encoding="utf-8"))
    errs = []
    for rel, n in sorted(counts.items()):
        if n > baseline.get(rel, 0):
            errs.append(f"curly: {rel}: {n} curly apostrophe(s), baseline {baseline.get(rel, 0)}: use ASCII ' in new text (run with --write-curly-baseline only after review)")
    return errs

def check_waitfanfare(root):
    errs = []
    commands = load_command_names(root)
    for path in script_files(root):
        rel = os.path.relpath(path, root)
        lines = read_lines(path)
        labels, _ = parse_script(path)
        movement = movement_label_set(root, path, lines, labels)
        for i, line in enumerate(lines):
            if strip_comment(line) != "WaitFanfare":
                continue
            # next meaningful line: skip blanks/comments; a label starts a new block (ok)
            j = i + 1
            nxt = None
            while j < len(lines):
                s = strip_comment(lines[j])
                if s:
                    nxt = (j, s)
                    break
                j += 1
            if nxt is None:
                errs.append(f"waitfanfare: {rel}:{i+1}: WaitFanfare at end of file with no following command")
                continue
            j, s = nxt
            if LABEL_RE.match(lines[j]):
                continue
            op = s.split()[0].split(",")[0]
            if commands and op not in commands and not op.startswith("."):
                errs.append(f"waitfanfare: {rel}:{j+1}: command after WaitFanfare ('{op}' in '{s}') is not a real script command")
                continue
            if re.match(r'^(GoTo|Call)(If\w*)?$', op):
                target = [a.strip() for a in s[len(op):].split(",")][-1]
                if target in movement:
                    errs.append(f"waitfanfare: {rel}:{j+1}: {op} after WaitFanfare targets movement data '{target}', not a script label (pret-merge WaitFanfare damage)")
                elif IDENT_RE.match(target) and target not in labels:
                    errs.append(f"waitfanfare: {rel}:{j+1}: {op} after WaitFanfare targets '{target}', which is not a label in this file (constant used as jump target?)")
    return errs

CHECKS = {
    "script_targets": check_script_targets,
    "text_labels": check_text_labels,
    "event_scripts": check_event_scripts,
    "json_data": check_json_data,
    "curly": check_curly,
    "waitfanfare": check_waitfanfare,
}

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--check", action="append", choices=list(CHECKS), help="run only this check (repeatable)")
    ap.add_argument("--write-curly-baseline", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.root)
    names = args.check or list(CHECKS)
    total = 0
    for name in names:
        fn = CHECKS[name]
        errs = fn(root, args) if name == "curly" else fn(root)
        for e in errs:
            print(e)
        if args.verbose or errs:
            print(f"{name}: {len(errs)} problem(s)")
        total += len(errs)
    if not args.write_curly_baseline:
        print(f"static_checks: {total} problem(s) across {len(names)} check(s)")
    return 1 if total else 0

if __name__ == "__main__":
    sys.exit(main())
