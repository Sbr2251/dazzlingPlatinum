    // Per-move camera templates for the 3D battle stage (docs/living_battle_stage/moves.md,
    // "Per-move camera", "Templates"). Include it after btlanimcmd.inc:
    //     #include "macros/btlanimcmd.inc"
    //     #include "macros/btlanimcam.inc"
    //
    // The poses approximate Black 2/White 2's camera presets (pokebw2 src/ov168/btlv_effvm.c:762-1124,
    // CmdCameraMovePreset, and the preset poses of btlv_camera.c): every preset is a truck of the home
    // camera onto a mon, with no rotation. BW2 frames the enemy's mon at about 1.50x home size and the
    // player's mon at about 0.91x (a pan with a slight pull-back, never a push-in), and shakes the camera
    // on the hit. These macros are built from the stage camera commands 85-89 and 91 (btlanimcmd.inc).
    //
    // Every template opens with a CamTpl*Open macro at the top of the script and ends with
    // CamTplClose before each End, so the script hands the camera back at home (camera.md, "The home
    // guard"). CamTplImpact goes right before the hit (the defender's Func_Shake). Like the other
    // camera commands they do nothing in contests or while the classic scene shows.
    //
    // Particles are still drawn flat and follow one 2D similarity off home (moves.md, "The limits"),
    // so each template keeps the battler its emitters sit on in the frame: tools/battle_stage/
    // camera_templates.py picks the template per move from where its particles are.

    // Distances (StageCameraMove distancePct) by the side of the framed mon (moves.md, "Distance by
    // side"). A mon on the player's side stands nearer the camera than the home focus: 78% from it frames
    // it at about 0.91x, BW2's player shot (a pan with a slight pull-back; 100% is 0.71x, 48% is 1.46x).
    // A mon on the enemy's side stands farther away: 92% from it is a push-in to about 1.35x. BW2's enemy
    // shot is 1.50x (85%), but at that size the sparks around the hit fly off the screen (moves.md,
    // "Templates").
#define CAMTPL_CLOSE_PLAYER 78
#define CAMTPL_CLOSE_ENEMY 92
#define CAMTPL_SELF_PLAYER 78
#define CAMTPL_SELF_ENEMY 92
#define CAMTPL_BETWEEN 95       // both mons in the frame
#define CAMTPL_WIDE 112         // the pull-back; the arenas reach well past the home frustum (arena.py)

    // Frames a pose around the attacker or the defender at a distance that depends on its side.
    // role: BATTLER_ROLE_ATTACKER or BATTLER_ROLE_DEFENDER; focus: the matching STAGE_CAMERA_FOCUS_*.
    .macro CamTplFrame role:req, focus:req, distPlayer:req, distEnemy:req, yawDeg:req, pitchDeg:req, frames:req
    JumpIfBattlerSide \role, camtpl_player\@, camtpl_enemy\@
camtpl_player\@:
    StageCameraMove \focus, \distPlayer, \yawDeg, \pitchDeg, \frames
    Jump camtpl_done\@
camtpl_enemy\@:
    StageCameraMove \focus, \distEnemy, \yawDeg, \pitchDeg, \frames
camtpl_done\@:
    .endm

    // Template "contact": the attacker in focus for the wind-up, then a cut to the defender, where the
    // whole move then plays (its particles must all sit on the defender). Adds 8 frames before the
    // move's own animation. Pair with CamTplImpact for the punch on the hit.
    .macro CamTplContactOpen
    StageHealthbars FALSE
    CamTplFrame BATTLER_ROLE_ATTACKER, STAGE_CAMERA_FOCUS_ATTACKER, CAMTPL_CLOSE_PLAYER, CAMTPL_CLOSE_ENEMY, 6, 0, 8
    Delay 8
    CamTplFrame BATTLER_ROLE_DEFENDER, STAGE_CAMERA_FOCUS_DEFENDER, CAMTPL_CLOSE_PLAYER, CAMTPL_CLOSE_ENEMY, -6, 0, 6
    .endm

    // Template "push": a two-shot (both mons, a little closer than home) while the projectile or beam
    // flies, then CamTplPushImpact pushes in on the defender at the hit.
    .macro CamTplPushOpen
    StageHealthbars FALSE
    StageCameraMove STAGE_CAMERA_FOCUS_BETWEEN, CAMTPL_BETWEEN, -4, 0, 10
    .endm

    // The push-in of template "push", at the hit (before the defender's Func_Shake).
    .macro CamTplPushImpact
    CamTplFrame BATTLER_ROLE_DEFENDER, STAGE_CAMERA_FOCUS_DEFENDER, CAMTPL_CLOSE_PLAYER, CAMTPL_CLOSE_ENEMY, -6, 0, 6
    .endm

    // Template "self": a close shot of the attacker with a slow orbit, for stat and self moves whose
    // particles all sit on the attacker.
    .macro CamTplSelfOpen
    StageHealthbars FALSE
    CamTplFrame BATTLER_ROLE_ATTACKER, STAGE_CAMERA_FOCUS_ATTACKER, CAMTPL_SELF_PLAYER, CAMTPL_SELF_ENEMY, -8, 2, 10
    StageCameraOrbit 14, 40
    .endm

    // Template "wide": a pull-back over the whole field, a little higher, for spread and field moves.
    // The focus is the arena's home target, so particles anywhere on the field stay put.
    .macro CamTplWideOpen
    StageCameraMove STAGE_CAMERA_FOCUS_CENTER, CAMTPL_WIDE, 0, 3, 12
    .endm

    // Template "twoshot": the two-shot of template "push" for the whole move, with a punch on each hit
    // but no push-in; for projectiles and beams whose particles are still near the attacker at the hit.
    .macro CamTplTwoShotOpen
    StageHealthbars FALSE
    StageCameraMove STAGE_CAMERA_FOCUS_BETWEEN, CAMTPL_BETWEEN, -4, 0, 10
    .endm

    // Template "shake": the camera stays home and only shakes on the hit; for moves whose particles
    // would drift in any close shot. Put CamTplImpact before the hit; CamTplShakeOpen is a no-op that
    // marks the script.
    .macro CamTplShakeOpen
    .endm

    // The punch on the hit: a short camera shake (BW2's CmdCameraShake). amplitudePx, frames as
    // StageCameraShake.
    .macro CamTplImpact amplitudePx=2, frames=6
    StageCameraShake \amplitudePx, \frames
    .endm

    // Every template's end: back home, the healthbars the open hid come back halfway, and the script
    // waits for home before it goes on to End.
    .macro CamTplClose
    StageCameraHome 12
    Delay 6
    StageHealthbars TRUE
    StageCameraWait
    .endm
