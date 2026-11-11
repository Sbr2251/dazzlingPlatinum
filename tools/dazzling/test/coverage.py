#!/usr/bin/env python3
"""Map SIM_SCRIPT_COVERAGE logs to file:label and report reached story labels.

Usage: python3 tools/dazzling/test/coverage.py [--root DIR] [--build DIR]
           coverage.txt [more-coverage.txt ...]
The game (with SIM_SCRIPT_COVERAGE=<file>) appends "<archive> <offset>"
lines, one per field script start (see src/field_script_context.c).
Archive ids index res/field/scripts.order (the scr_seq.narc member order;
if build_macos has a scr_seq.naix it is preferred when found).
Offset -> label: the reached file is assembled once (cached under
/tmp/dz-coverage) with tools/scripts/make_script_bin.sh -c and its symbol
table read with arm-none-eabi-objdump; the label is the greatest symbol
at or before the offset. Without the ARM toolchain, falls back to naming
the file and the nearest preceding ScriptEntry, and says so.
"""
import argparse, glob, json, os, re, subprocess, sys, tempfile

def resolve_stem(root, stem):
    name = stem[len("scripts_"):] if stem.startswith("scripts_") else stem
    for cand in (os.path.join(root, "res/field/scripts", name + ".s"),
                 os.path.join(root, "res/field/maps", name, "scripts.s"),
                 os.path.join(root, "res/field/scripts", stem + ".s")):
        if os.path.exists(cand):
            return cand
    return None

def script_entries(path):
    out = []
    for line in open(path, encoding="utf-8", errors="replace"):
        m = re.match(r'\s*ScriptEntry\s+([A-Za-z_]\w*)', line)
        if m:
            out.append(m.group(1))
        if re.match(r'\s*ScriptEntryEnd\b', line):
            break
    return out

def labels_in(path):
    return [m.group(1) for m in
            (re.match(r'^([A-Za-z_]\w*):', l) for l in open(path, encoding="utf-8", errors="replace")) if m]

class LabelMapper:
    def __init__(self, root):
        self.root, self.cache, self.failed = root, {}, set()
        self.cache_dir = tempfile.mkdtemp(prefix="dz-coverage-")

    def symbols(self, path):
        if path in self.cache:
            return self.cache[path]
        syms = None
        obj = os.path.join(self.cache_dir, os.path.basename(path) + ".o")
        script_bin = os.path.join(self.root, "tools/scripts/make_script_bin.sh")
        try:
            r = subprocess.run(["bash", script_bin, "-c", "-O", obj, path],
                               cwd=self.root, capture_output=True, text=True, timeout=120)
            if r.returncode == 0 and os.path.exists(obj):
                dump = subprocess.run(["arm-none-eabi-objdump", "-t", obj],
                                      capture_output=True, text=True, timeout=60)
                syms = []
                for line in dump.stdout.splitlines():
                    parts = line.split()
                    if len(parts) >= 6 and parts[-2] in (".text", "*ABS*"):
                        try:
                            syms.append((int(parts[0], 16), parts[-1]))
                        except ValueError:
                            pass
                syms.sort()
        except Exception:
            syms = None
        if not syms:
            self.failed.add(path)
            syms = []
        self.cache[path] = syms
        return syms

    def label_at(self, path, offset):
        syms = self.symbols(path)
        best = None
        for addr, name in syms:
            if addr <= offset:
                best = name
            else:
                break
        return best

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--root", default=".")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.root)
    order_path = os.path.join(root, "res/field/scripts.order")
    order = [l.strip() for l in open(order_path) if l.strip()]
    hits = {}
    unknown_archives = set()
    for log in args.logs:
        for line in open(log, encoding="utf-8", errors="replace"):
            parts = line.split()
            if len(parts) != 2:
                continue
            try:
                archive, offset = int(parts[0]), int(parts[1])
            except ValueError:
                continue
            hits.setdefault((archive, offset), 0)
            hits[(archive, offset)] += 1
    mapper = LabelMapper(root)
    by_file, reached_labels = {}, set()
    unresolved = 0
    total_entries, reached_entries = 0, set()
    for (archive, offset), count in sorted(hits.items()):
        if archive >= len(order):
            unknown_archives.add(archive)
            continue
        stem = order[archive]
        path = resolve_stem(root, stem)
        if path is None:
            unresolved += 1
            continue
        rel = os.path.relpath(path, root)
        label = mapper.label_at(path, offset)
        if label is None:
            entries = script_entries(path)
            label = f"<offset {offset}; nearest entry unknown without ARM toolchain>"
            unresolved += 1
        else:
            reached_labels.add((rel, label))
        by_file.setdefault(rel, []).append((offset, label, count))
    for rel in by_file:
        entries = script_entries(os.path.join(root, rel))
        total_entries += len(entries)
        for e in entries:
            if (rel, e) in reached_labels:
                reached_entries.add((rel, e))
    report = {
        "distinct_script_starts": len(hits),
        "files_reached": len(by_file),
        "labels_resolved": len(reached_labels),
        "story_entries_in_reached_files": total_entries,
        "story_entries_reached": len(reached_entries),
        "unknown_archives": sorted(unknown_archives),
        "unresolved": unresolved,
        "by_file": {rel: [{"offset": o, "label": l, "count": c} for o, l, c in sorted(v)]
                    for rel, v in sorted(by_file.items())},
    }
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"coverage: {report['distinct_script_starts']} distinct script starts, "
              f"{report['files_reached']} files, {len(reached_entries)}/{total_entries} "
              f"story ScriptEntry labels in reached files")
        if unknown_archives:
            print(f"coverage: WARNING unknown archive ids: {sorted(unknown_archives)}")
        if unresolved:
            print(f"coverage: {unresolved} hit(s) unresolved (no ARM toolchain or unknown file)")
        for rel, rows in sorted(by_file.items()):
            print(f"\n{rel}:")
            for offset, label, count in sorted(rows):
                print(f"  @{offset:<7} {label}  (x{count})")
    return 0

if __name__ == "__main__":
    sys.exit(main())
