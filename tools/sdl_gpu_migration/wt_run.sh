#!/bin/bash
# Run a command inside a workstream's copy of the repo.
#   tools/sdl_gpu_migration/wt_run.sh <tree-name> <command...>
# A meson build directory only works at the path it was configured for. Each workstream therefore gets a full copy
# of the repo (make_tree.sh) and this wrapper mounts that copy over the repo's own path in a private mount
# namespace, so the copied build_linux rebuilds only what the workstream changed. Inside the wrapper the copy IS the
# repo path; outside it (editors, other tools) the copy is at $WT/<tree-name>. Needs root (unshare).
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
WT=${WT:-$(dirname "$ROOT")/wt}
DEPS=${DEPS:-$(dirname "$ROOT")/deps}
name=${1:?usage: wt_run.sh <tree-name> <command...>}; shift
[ -d "$WT/$name" ] || { echo "no tree $WT/$name (create it with make_tree.sh)" >&2; exit 2; }
export PKG_CONFIG_PATH="$DEPS/prefix/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
export LD_LIBRARY_PATH="$DEPS/prefix/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec unshare -m --propagation private bash -c \
  'mount --bind "$0" "$1" && cd "$1" && shift && exec "$@"' "$WT/$name" "$ROOT" "$@"
