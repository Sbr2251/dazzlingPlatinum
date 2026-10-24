// DW puzzle engine state (engine-a) lives in the MAIN binary's RAM.
//
// A warp into a DW map -- including a same-map warp (fold, fall) --
// reloads overlay 9 and zeroes its .bss, which would wipe the
// fall-pending flag, the checkpoint snapshot and the group state
// mid-fall. Main-binary RAM survives overlay reloads, so the fall warp
// keeps the state and the frame hook can restore + respawn after it.
// The debug struct stays in overlay 9 (it is repopulated every frame by
// RefreshDebug, and the harness reads it from the xMAP-listed symbol).
// The actor tiles stay in overlay 9 too: engine-b re-syncs them from its
// core state on every map load (DwActors_Init -> SyncActorTiles), so the
// warp wipe is harmless, and the harness pokes them by xMAP symbol.
// The test-mode flag intentionally stays in overlay 9
// (src/overlay009/dw_puzzle.c): a warp resets it to off (the safe
// production default); the harness re-enables it after each warp.
//
// This file is in the main binary (src/meson.build), NOT in overlay 9
// (platinum.us/main.lsf) -- that is the whole point. Do not move it.

#include "overlay009/dw_puzzle.h"

DwPuzzleState gDwPuzzleState;
