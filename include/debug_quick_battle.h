#ifndef POKEPLATINUM_DEBUG_QUICK_BATTLE_H
#define POKEPLATINUM_DEBUG_QUICK_BATTLE_H

#include "config/battle_stage.h"

#include "field/field_system_decl.h"

#if DEBUG_BATTLE_TOOLS
// Opens the quick-battle panel when L+R are held while the player stands free in the overworld.
// Returns TRUE if the panel took over this frame's input.
BOOL DebugQuickBattle_TryStart(FieldSystem *fieldSystem, u32 heldKeys);
#endif

#endif // POKEPLATINUM_DEBUG_QUICK_BATTLE_H
