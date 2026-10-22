#ifndef POKEPLATINUM_BATTLE_BATTLE_STAGE_PARTICLES_H
#define POKEPLATINUM_BATTLE_BATTLE_STAGE_PARTICLES_H

#include <nitro.h>

#include "struct_decls/battle_system.h"

#include "battle/battle_stage_camera.h"

// Battle particles in stage space (docs/living_battle_stage/camera.md, "Particles follow the
// camera"). Internal to the battle stage: battle_stage_camera.c owns the projection hook and
// calls these.
//
// A battle particle system draws with its own camera, which gives the classic 2D picture. Off
// the home pose each particle is moved the way the mons are: the mons are camera-facing
// billboards, each moved by the similarity of its foot (its world foot point through the stage
// camera, scaled by its depth), and each particle takes the similarity of the mons around its
// classic screen position. At home nothing changes.

// debugFlags bits (sBattleStage+32), for A/B captures: the old single 2D similarity, or the
// battle plane below instead of the particle field. (Bits 20-22: bit 12 is layout's
// PLATINUM_LAYOUT, which the critic sets by default.)
#define BATTLE_STAGE_DEBUG_PARTICLES_2D    (1 << 20)
#define BATTLE_STAGE_DEBUG_PARTICLES_PLANE (1 << 21)
// debugFlags bit: the move tester keeps its debug view (1-3) through the animation, an off-home
// test bed for any move's particles (the view still resets when the overlay hides)
#define BATTLE_STAGE_DEBUG_KEEP_VIEW_IN_MOVES (1 << 22)

// At BattleStageCamera_Init, when there is an arena (installs the particle hook). debugFlags is
// the stage's debugFlags field.
void BattleStageParticles_Init(BattleSystem *battleSys, const BattleStageCameraHome *home, const u32 *debugFlags);
void BattleStageParticles_Free(void);

// What BattleStageParticles_BeginSystem did with a particle system
enum BattleStageParticlesDraw {
    BATTLE_STAGE_PARTICLES_NONE = 0, // no battler has a similarity: the caller's fallback
    BATTLE_STAGE_PARTICLES_SHARED, // the mons share one similarity (a shake, a pan): it is in the projection
    BATTLE_STAGE_PARTICLES_FIELD, // call DrawParticle before each particle
};

// The particle field (the default off home). BeginSystem, from the projection hook with the
// system's own projection, takes this frame's battler similarities (once per frame). When the mons
// share one (a shake, a pan), it puts that in the projection and nothing runs per particle;
// otherwise DrawParticle, before each particle, loads the projection that gives that particle the
// similarity of the battlers around it: a mon's own near that mon, a blend between them. viewPos is
// the particle's centre, anchorViewPos the point it was emitted from: particles near their
// emission point move rigidly with it.
int BattleStageParticles_BeginSystem(MtxFx44 *projection);
void BattleStageParticles_DrawParticle(const VecFx32 *viewPos, const VecFx32 *anchorViewPos);

// The battle plane (debug A/B; the true 3D placement, for sprites drawn in perspective): turns
// a particle system's projection into one that puts every particle on the upright plane through
// both sides' feet and draws it with the stage camera. FALSE (the projection is left alone)
// when there is no plane, e.g. no battler on a side.
BOOL BattleStageParticles_ProjectOnPlane(MtxFx44 *projection);

// BATTLE_STAGE_DEBUG_KEEP_VIEW_IN_MOVES is set (battle_debug.c's move tester)
BOOL BattleStageParticles_KeepDebugViewInMoves(void);

#endif // POKEPLATINUM_BATTLE_BATTLE_STAGE_PARTICLES_H
