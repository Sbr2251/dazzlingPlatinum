#!/bin/bash
# Create a workstream's private copy of the repo (sources, subprojects and the built build_linux), on its own
# branches, optionally with saved work-in-progress applied.
#   tools/sdl_gpu_migration/make_tree.sh <tree-name> [--libntr <patch>]... [--game <patch>]...
# Example: tools/sdl_gpu_migration/make_tree.sh seam --libntr docs/sdl_gpu_migration/wip/seam-libntr.patch
# The copy lands in $WT/<tree-name> (default: ../wt next to the repo), on branch team/<tree-name> in the outer repo
# and in subprojects/libntr. Patches are applied to the working tree, not committed. Build and run the copy with
# wt_run.sh. Run setup_env.sh and build_linux.sh first so the copy starts from a finished build (about 3 GB each).
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
WT=${WT:-$(dirname "$ROOT")/wt}
name=${1:?usage: make_tree.sh <tree-name> [--libntr <patch>]... [--game <patch>]...}; shift
[ ! -e "$WT/$name" ] || { echo "$WT/$name already exists" >&2; exit 2; }
[ -f "$ROOT/build_linux/main" ] || echo "warning: $ROOT/build_linux/main is missing; the copy will need a full build" >&2
mkdir -p "$WT"
cp -a "$ROOT" "$WT/$name"
git -C "$WT/$name" checkout -q -b "team/$name"
git -C "$WT/$name/subprojects/libntr" checkout -q -b "team/$name"
while [ $# -gt 0 ]; do
  case "$1" in
    --libntr) git -C "$WT/$name/subprojects/libntr" apply "$(cd "$ROOT" && realpath "$2")"; echo "applied $2 to subprojects/libntr"; shift 2 ;;
    --game)   git -C "$WT/$name" apply "$(cd "$ROOT" && realpath "$2")"; echo "applied $2 to the game repo"; shift 2 ;;
    *) echo "unknown argument $1" >&2; exit 2 ;;
  esac
done
echo "tree ready: $WT/$name (build with: tools/sdl_gpu_migration/wt_run.sh $name ninja -j2 -C build_linux)"
