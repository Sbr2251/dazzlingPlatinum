// DW puzzle actor core state (engine-b), in MAIN-binary RAM.
//
// Same reason as engine-a's DwPuzzleState (src/dw_puzzle_state.c): a warp
// into a DW map -- including a same-map warp (fold, fall, battle return)
// -- reloads overlay 9 and zeroes its .bss. Actor state (stones,
// snapshots, shadow phase, pad state) must survive that, so it lives
// here, not in overlay 9. This file is in the main binary's object list
// (platinum.us/main.lsf, Static main), NOT in overlay 9.

#include "overlay009/dw_puzzle_actors.h"

DwActorState gDwActorState;
