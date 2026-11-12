#!/bin/bash
# One-command sanitizer run: build the ASan+UBSan variant and run the
# scenario suite, the battle tests, and short soaks under it.
# Exit non-zero if any sanitizer report fires (or any test fails).
#
# One-time setup (Linux devserver; see docs/headless_protocol.md, the
# "Sanitizer build" section): configure build_asan once with
#   python3 subprojects/meson-1.12.0/meson.py setup build_asan \
#     -Dbuild_target=linux -Dbuild_variant=asan -Ddefault_library=static \
#     --cross-file=meson/cross_pcport_linux.ini \
#     --cross-file=<scratch>/root.ini \
#     --native-file=meson/native.ini \
#     --native-file=<scratch>/native_clang.ini \
#     --native-file=<scratch>/root.ini
# with LIBRARY_PATH/CPATH pointing at the deps prefix (and the clang
# compiler-rt archives, because the devserver GCC 15 toolset lacks the
# 64-bit sanitizer runtime). This script only builds the existing
# build_asan dir; if it does not exist it prints the setup and exits 2.
#
# Env overrides:
#   SANITIZE_BUILD_DIR   build dir (default build_asan)
#   SANITIZE_SOAK_FRAMES overworld/menu soak frames (default 6000)
#   SANITIZE_BATTLE_SOAK_N random-battle soak count (default 20)
#   SANITIZE_SKIP_BUILD=1  skip the ninja step
#   SANITIZE_SKIP_SUITE=1 / SANITIZE_SKIP_BATTLE=1 / SANITIZE_SKIP_SOAK=1
#   LIBRARY_PATH / CPATH    as needed for the asan link on this machine
set -euo pipefail
cd "$(dirname "$0")/../../.."

export LP_NUM_THREADS=2
# On the shared devserver the ASan link needs the deps prefix and the
# clang compiler-rt archives (the GCC 15 toolset lacks the 64-bit
# sanitizer runtime). Pick them up automatically when present; a caller
# that already set LIBRARY_PATH/CPATH wins.
_DEPS=/data/repos/dp-wt/team-debug-headless-scratch/deps/prefix
_ASANRT=/data/repos/dp-wt/team-debug-headless-scratch/asanrt
if [ -d "$_DEPS/lib" ] && [ -z "${LIBRARY_PATH:-}" ]; then
    export LIBRARY_PATH="$_ASANRT:$_DEPS/lib"
fi
if [ -d "$_DEPS/include" ] && [ -z "${CPATH:-}" ]; then
    export CPATH="$_DEPS/include"
fi
unset _DEPS _ASANRT
BUILD_DIR="${SANITIZE_BUILD_DIR:-build_asan}"
SUPPRESSIONS="$PWD/tools/dazzling/test/ubsan_suppressions.txt"

if [ ! -d "$BUILD_DIR" ]; then
    echo "sanitize.sh: $BUILD_DIR does not exist; configure it first (see the header of this script)." >&2
    exit 2
fi

if [ "${SANITIZE_SKIP_BUILD:-0}" != "1" ]; then
    echo "sanitize.sh: building $BUILD_DIR"
    # Build-time host tools are ASan-instrumented too, and makelcf leaks,
    # so the build itself runs with leak detection off and UBSan
    # non-fatal. The game runs below use the strict options.
    ASAN_OPTIONS=detect_leaks=0 UBSAN_OPTIONS=halt_on_error=0:print_stacktrace=0 \
        nice ninja -C "$BUILD_DIR" -j32
fi

# Gate options for the game runs: any ASan report aborts, any UBSan
# report halts (allocator-internal alignment is covered by the
# suppressions file; see its header). Leaks are not yet gated
# (detect_leaks=0): the game intentionally never frees some arenas.
export ASAN_OPTIONS=detect_leaks=0:abort_on_error=1
export UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1:suppressions=$SUPPRESSIONS"

if [ "${SANITIZE_SKIP_SUITE:-0}" != "1" ]; then
    echo "sanitize.sh: scenario suite under ASan/UBSan"
    # The ASan build runs several times slower than dev (and the suite runs
    # 3 games in parallel on a shared devserver): the longest scenario
    # needs ~830s alone on ASan, so the 600s default scenario timeout is
    # too small and fails healthy scenarios. Give each scenario 1800s.
    python3 tools/dazzling/test/run.py -j 3 --timeout 1800 --game "$BUILD_DIR/main"
fi

if [ "${SANITIZE_SKIP_BATTLE:-0}" != "1" ]; then
    echo "sanitize.sh: battle tests under ASan/UBSan"
    # faint_forced_switch is a known test-DRIVER failure (lane testbugs):
    # the driver picks the switch slot from a stale party-HP snapshot (the
    # fainted lead still shows full HP), so it keeps sending the fainted mon
    # and the battle never ends. It is not a sanitizer report (the game
    # never aborts; the test fails on max_steps). Tolerate exactly that one
    # FAIL; any other FAIL -- including a sanitizer abort (exit 134) --
    # fails the gate. Also fail on any sanitizer report text, even if a
    # test somehow still passed.
    BATTLE_LOG="$(mktemp)"
    trap 'rm -f "$BATTLE_LOG"' EXIT
    python3 tools/battle/run_tests.py --build-dir "$BUILD_DIR" --fast >"$BATTLE_LOG" 2>&1 || true
    cat "$BATTLE_LOG"
    BAD_FAILS="$(grep '^FAIL' "$BATTLE_LOG" | grep -v 'faint_forced_switch' || true)"
    if [ -n "$BAD_FAILS" ]; then
        echo "sanitize.sh: battle tests failed:" >&2
        printf '%s\n' "$BAD_FAILS" >&2
        exit 1
    fi
    if grep -q -e 'runtime error' -e 'AddressSanitizer' "$BATTLE_LOG"; then
        echo "sanitize.sh: sanitizer report in battle tests" >&2
        exit 1
    fi
fi

if [ "${SANITIZE_SKIP_SOAK:-0}" != "1" ]; then
    echo "sanitize.sh: soaks under ASan/UBSan"
    python3 tools/dazzling/test/soak.py --game "$BUILD_DIR/main" \
        --frames "${SANITIZE_SOAK_FRAMES:-6000}" --seed 7
    python3 tools/battle/sim.py --n "${SANITIZE_BATTLE_SOAK_N:-20}" --random \
        --build-dir "$BUILD_DIR" --seed 1
fi

echo "sanitize.sh: clean (no sanitizer reports, all tests passed)"
