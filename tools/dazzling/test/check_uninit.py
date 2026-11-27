#!/usr/bin/env python3
"""Parallel clang -Wuninitialized / -Wsometimes-uninitialized audit script.

Reads <build_dir>/compile_commands.json (auto-detecting build_macos_release or
build_macos), strips warning-suppression / codegen / PCH flags, and runs
clang -fsyntax-only -Wno-everything -Wuninitialized -Wsometimes-uninitialized
in parallel across matching translation units.

Usage:
    python3 tools/dazzling/test/check_uninit.py src/battle src/applications src/overlay009
    python3 tools/dazzling/test/check_uninit.py --all -j 8 --fail-on-warn
"""

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import re
import shlex
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.realpath(os.path.join(HERE, "..", "..", ".."))

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
DIAG_RE = re.compile(
    r"^(?P<file>.+?):(?P<line>\d+):(?P<col>\d+):\s+"
    r"(?P<level>warning|error|fatal error):\s+(?P<msg>.+)$"
)

FLAGS_DROP_NO_ARG = {
    "-w",
    "-c",
    "-MD",
    "-MMD",
    "-MP",
    "-M",
    "-MM",
}

FLAGS_DROP_WITH_ARG = {
    "-o",
    "-MF",
    "-MQ",
    "-MT",
}


def find_build_dir(explicit_build_dir):
    if explicit_build_dir:
        candidate = explicit_build_dir
        if not os.path.isabs(candidate):
            candidate = os.path.join(REPO_ROOT, candidate)
        cc_path = os.path.join(candidate, "compile_commands.json")
        if os.path.isfile(cc_path):
            return os.path.realpath(candidate)
        raise FileNotFoundError(
            "compile_commands.json not found in {}".format(candidate)
        )

    for name in ("build_macos_release", "build_macos"):
        candidate = os.path.join(REPO_ROOT, name)
        if os.path.isfile(os.path.join(candidate, "compile_commands.json")):
            return os.path.realpath(candidate)

    raise FileNotFoundError(
        "Could not find compile_commands.json in build_macos_release or build_macos"
    )


def normalize_rel_path(path, base_dir=REPO_ROOT):
    if not os.path.isabs(path):
        abs_path = os.path.realpath(os.path.join(base_dir, path))
    else:
        abs_path = os.path.realpath(path)
    try:
        rel = os.path.relpath(abs_path, REPO_ROOT)
    except ValueError:
        return abs_path
    return rel.replace(os.sep, "/")


def normalize_prefix(prefix):
    if os.path.isabs(prefix):
        rel = normalize_rel_path(prefix)
    else:
        rel = prefix.replace("\\", "/")
    while rel.startswith("./"):
        rel = rel[2:]
    return rel.rstrip("/")


def matches_prefixes(rel_file, prefixes):
    for p in prefixes:
        if rel_file == p or rel_file.startswith(p + "/"):
            return True
    return False


def build_pch_map(entries):
    pch_map = {}
    for entry in entries:
        out = entry.get("output", "")
        if out.endswith(".pch"):
            pch_map[out] = entry["file"]
    return pch_map


def rewrite_command(entry, pch_map):
    if "arguments" in entry:
        tokens = list(entry["arguments"])
    else:
        tokens = shlex.split(entry["command"])

    if not tokens:
        return None

    compiler = tokens[0]
    src_file = entry["file"]
    out = [compiler]

    i = 1
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        if tok in FLAGS_DROP_NO_ARG:
            i += 1
            continue
        if tok in FLAGS_DROP_WITH_ARG:
            i += 2
            continue
        if tok.startswith("-fdiagnostics-color"):
            i += 1
            continue
        if tok == "-include-pch" and i + 1 < n:
            pch_path = tokens[i + 1]
            hdr = pch_map.get(pch_path)
            if hdr is None and "global_pch" in pch_path:
                hdr = "../include/pch/global_pch.h"
            if hdr is not None:
                out.extend(["-include", hdr])
            i += 2
            continue
        # Drop the trailing input source if we re-append it at the end, or keep in place.
        if tok == src_file:
            i += 1
            continue
        out.append(tok)
        i += 1

    out.extend(
        [
            "-fsyntax-only",
            "-Qunused-arguments",
            "-fno-color-diagnostics",
            "-Wno-everything",
            "-Wuninitialized",
            "-Wsometimes-uninitialized",
            src_file,
        ]
    )
    return out


def check_one(item):
    rel_file, workdir, cmd = item
    proc = subprocess.run(
        cmd,
        cwd=workdir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    combined = (proc.stderr or "") + "\n" + (proc.stdout or "")
    warnings = []
    errors = []

    for raw_line in combined.splitlines():
        line = ANSI_RE.sub("", raw_line).strip()
        if not line:
            continue
        m = DIAG_RE.match(line)
        if not m:
            continue
        diag_file = normalize_rel_path(m.group("file"), base_dir=workdir)
        entry = (
            diag_file,
            int(m.group("line")),
            int(m.group("col")),
            m.group("msg"),
        )
        if m.group("level") == "warning":
            warnings.append(entry)
        else:
            errors.append(entry)

    if proc.returncode != 0 and not errors:
        tail = [
            ANSI_RE.sub("", l).strip()
            for l in combined.splitlines()
            if l.strip()
        ][-3:]
        errors.append(
            (rel_file, 0, 0, "clang exited {}: {}".format(proc.returncode, " | ".join(tail)))
        )

    return rel_file, warnings, errors


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Run clang -Wuninitialized -Wsometimes-uninitialized across "
            "translation units from compile_commands.json."
        )
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Optional repo-relative path prefixes or files (e.g. src/battle src/applications).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Check all translation units under src/.",
    )
    parser.add_argument(
        "--build-dir",
        "--build",
        dest="build_dir",
        default=None,
        help="Path to build directory containing compile_commands.json (default: auto-detect build_macos_release or build_macos).",
    )
    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=8,
        help="Number of parallel clang workers (default: 8).",
    )
    parser.add_argument(
        "--fail-on-warn",
        action="store_true",
        help="Exit non-zero if any warnings are reported.",
    )
    args = parser.parse_args(argv)

    if args.jobs < 1:
        parser.error("-j/--jobs must be >= 1")

    try:
        build_dir = find_build_dir(args.build_dir)
    except FileNotFoundError as exc:
        print("ERROR: {}".format(exc), file=sys.stderr)
        return 2

    cc_path = os.path.join(build_dir, "compile_commands.json")
    with open(cc_path, "r", encoding="utf-8") as fh:
        entries = json.load(fh)

    if args.all or not args.paths:
        prefixes = ["src"]
    else:
        prefixes = [normalize_prefix(p) for p in args.paths]

    pch_map = build_pch_map(entries)
    tasks = []
    seen_files = set()

    for entry in entries:
        out = entry.get("output", "")
        if out.endswith(".pch"):
            continue
        workdir = entry.get("directory", build_dir)
        rel_file = normalize_rel_path(entry["file"], base_dir=workdir)
        if rel_file in seen_files:
            continue
        if not matches_prefixes(rel_file, prefixes):
            continue
        cmd = rewrite_command(entry, pch_map)
        if not cmd:
            continue
        seen_files.add(rel_file)
        tasks.append((rel_file, workdir, cmd))

    tasks.sort(key=lambda t: t[0])

    if not tasks:
        print(
            "No matching translation units in {} for: {}".format(
                cc_path, ", ".join(prefixes)
            ),
            file=sys.stderr,
        )
        return 2

    warnings_by_file = defaultdict(set)
    errors_by_file = defaultdict(set)

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(check_one, item) for item in tasks]
        for fut in as_completed(futures):
            _tu, warns, errs = fut.result()
            for diag_file, line, col, msg in warns:
                warnings_by_file[diag_file].add((line, col, msg))
            for diag_file, line, col, msg in errs:
                errors_by_file[diag_file].add((line, col, msg))

    total_warnings = sum(len(v) for v in warnings_by_file.values())
    total_errors = sum(len(v) for v in errors_by_file.values())

    print(
        "Checked {} translation unit(s) using {}".format(
            len(tasks), normalize_rel_path(build_dir)
        )
    )

    if warnings_by_file:
        print("")
        print("Warnings by file:")
        print("{:<60} {:>6}".format("File", "Count"))
        print("-" * 67)
        for fpath in sorted(warnings_by_file.keys()):
            print("{:<60} {:>6}".format(fpath, len(warnings_by_file[fpath])))
        print("-" * 67)
        print("{:<60} {:>6}".format("TOTAL", total_warnings))
        print("")
        print("Details:")
        for fpath in sorted(warnings_by_file.keys()):
            print("  {}".format(fpath))
            for line, col, msg in sorted(warnings_by_file[fpath]):
                print("    {}:{}: {}".format(line, col, msg))
    else:
        print("0 warnings.")

    if errors_by_file:
        print("")
        print("Syntax/compile errors ({}):".format(total_errors), file=sys.stderr)
        for fpath in sorted(errors_by_file.keys()):
            for line, col, msg in sorted(errors_by_file[fpath]):
                print(
                    "  {}:{}:{}: {}".format(fpath, line, col, msg),
                    file=sys.stderr,
                )

    if total_errors > 0:
        return 1
    if args.fail_on_warn and total_warnings > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
