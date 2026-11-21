#ifndef POKEPLATINUM_CONFIG_BATTLE_STAGE_H
#define POKEPLATINUM_CONFIG_BATTLE_STAGE_H

// Living 3D Battle Stage (docs/living_battle_stage/PLAN.md): draws the battle arena in 3D behind the sprites.
// Set to 0 to build the original 2D battle scene.
#define BATTLE_STAGE_3D 1

// Debug tools for testing the battle stage: the overworld quick-battle and the
// in-battle move tester. perf-build hook: compile out their state and ticks in release.
#ifdef PM_RELEASE_BUILD
#define DEBUG_BATTLE_TOOLS 0
#else
#define DEBUG_BATTLE_TOOLS 1
#endif

#endif // POKEPLATINUM_CONFIG_BATTLE_STAGE_H
