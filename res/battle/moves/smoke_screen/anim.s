#include "macros/btlanimcmd.inc"
#include "macros/btlanimcam.inc"

// Per-move camera template "twoshot" (moves.md, "Templates"): both mons for the whole move, a punch on the hit.
L_0:
    LoadParticleResource 0, smoke_screen_spa
    LoadParticleResource 1, smoke_screen_spa
    CamTplTwoShotOpen
    CreateEmitter 1, 1, EMITTER_CB_SET_POS_TO_DEFENDER
    Delay 1
    CreateEmitterEx 0, 1, 0, EMITTER_CB_SET_POS_TO_ATTACKER
    Func_MoveEmitterA2BParabolic 1, 0, 0, 0, 13, 64
    PlayMovingSoundEffectAtkDef SEQ_SE_DP_W104, BATTLE_SOUND_PAN_LEFT, BATTLE_SOUND_PAN_RIGHT, 4, 2
    Delay 13
    PlayLoopedSoundEffectR SEQ_SE_DP_W028B, 3, 6
    WaitForAllEmitters
    UnloadParticleSystem 0
    UnloadParticleSystem 1
    CamTplClose
    End
