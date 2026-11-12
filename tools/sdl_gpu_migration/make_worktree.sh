#!/bin/bash
# make_worktree.sh <name> [--libntr <patch>] [--game <patch>] [--base <commit>]
# Creates /data/repos/dp-wt/sdl-<name> (branch sdl/<name>) from main, a libntr clone on branch sdl/<name> at the
# revision matching tools/macos/patches/libntr.patch, applies optional saved WIP patches, and builds build_linux.
# Based on the team-2 setup script (/data/repos/dp-wt/team2/setup.sh), which built ten trees this way.
# Not yet run in this form (written with the v2 plan, 2026-11-11): the integrator runs it once and fixes it first.
set -euo pipefail
n=$1; shift; LIBNTR_PATCH=; GAME_PATCH=; BASE=main
while [ $# -gt 0 ]; do case $1 in
  --libntr) LIBNTR_PATCH=$(realpath "$2"); shift 2;; --game) GAME_PATCH=$(realpath "$2"); shift 2;;
  --base) BASE=$2; shift 2;; *) echo "unknown arg $1"; exit 2;; esac; done
REPO=/data/repos/dp-wt/engine-core           # any clone of the outer repo with main fetched
W=/data/repos/dp-wt/sdl-$n; S=/data/repos/dp-wt/sdl-$n-scratch; REF=/data/repos/dp-wt/t2-integ
git -C "$REPO" worktree add -q "$W" -b "sdl/$n" "$BASE"
cd "$W"
for s in libntrsystem libntrwifi libntrdwc libvct metang tracy yyjson-0.12.0 meson-1.12.0 packagecache libsyscall; do
  [ -e "$REF/subprojects/$s" ] && cp -R "$REF/subprojects/$s" subprojects/
done
git clone -q "$REF/subprojects/libntr" subprojects/libntr
# libntr baseline = pinned upstream revision + this commit's patch, committed as one baseline commit
git -C subprojects/libntr checkout -q -b "sdl/$n" aa4fea1f8c148150482a17dcd24b4e2a2926a03a
git -C subprojects/libntr apply --index "$W/tools/macos/patches/libntr.patch"
git -C subprojects/libntr -c user.name=Sbr2251 -c user.email=sreddy9@meta.com commit -qm "Baseline: libntr.patch at $(git rev-parse --short HEAD)"
SYSREV=$(awk '$1=="libntrsystem"{print $2}' tools/macos/patches/REVISIONS)
if [ -n "$SYSREV" ]; then
  git -C subprojects/libntrsystem checkout -q -- . && git -C subprojects/libntrsystem checkout -q "$SYSREV"
  git -C subprojects/libntrsystem apply "$W/tools/macos/patches/libntrsystem.patch"
fi
[ -n "$LIBNTR_PATCH" ] && git -C subprojects/libntr apply --3way "$LIBNTR_PATCH"
[ -n "$GAME_PATCH" ] && git apply --3way "$GAME_PATCH"
mkdir -p "$S"
printf "[constants]\nroot = '%s'\n[binaries]\nc = '/opt/rh/gcc-toolset-15/root/usr/bin/gcc'\ncpp = '/opt/rh/gcc-toolset-15/root/usr/bin/g++'\nar = 'ar'\n" "$W" > "$S/root.ini"
source "$W/tools/sdl_gpu_migration/env_devserver.sh"
/usr/local/fbcode/platform010/bin/python3.12 subprojects/meson-1.12.0/meson.py setup build_linux \
  -Dbuild_target=linux -Ddefault_library=static --cross-file=meson/cross_pcport_linux.ini --cross-file="$S/root.ini" \
  --native-file=meson/native.ini --native-file="$S/root.ini" > "$S/setup.log" 2>&1
nice ninja -C build_linux -j32 > "$S/build.log" 2>&1 && echo "built $W/build_linux" || { echo "BUILD FAILED: $S/build.log"; tail -5 "$S/build.log"; exit 1; }
