#ifndef PORT_SIM_WIDE_H
#define PORT_SIM_WIDE_H

#include <nitro/types.h>
#include <nitro/fx/fx.h>

// Game-side facade over the simulator's wide-layout scene API
// (wide-OUT/API.md v1; the real header is <simulator/sim_layout.h> in
// libntr, owned by lane widecomp). Every wide behaviour in the game goes
// through here so that:
//  - this tree links and behaves exactly as today when libntr does not
//    provide the API yet (the simulator symbols are weak, see
//    src/port/sim_wide.c);
//  - when the symbols exist, calls are forwarded unconditionally, as the
//    API requires (they are no-ops unless ScreenLayout=wide on the GPU
//    renderer);
//  - headless verification can force the layout with SIM_WIDE_LAYOUT=1
//    (0 forces it off), mirroring SIM_FX_WIDE_CAMERA for DebugWideCamera.
//
// Scene values match SIM_Layout_Scene in the API (FIELD=1, BATTLE=2,
// MENU=3); they are redeclared here under game-owned names so no game
// file outside this facade includes the simulator header yet.

enum SIMWideScene {
    SIM_WIDE_SCENE_FIELD = 1, // overworld / field
    SIM_WIDE_SCENE_BATTLE = 2, // battle
    SIM_WIDE_SCENE_MENU = 3, // any full-screen app using both screens
    SIM_WIDE_SCENE_MENU_SINGLE = 4 // party/summary: main screen only + panel
};

// Tell the simulator which scene is active. Call at entry/exit points,
// not per frame; repeat calls with the same scene are dropped here.
void SIM_Wide_SetScene(enum SIMWideScene scene);
// Push a scene, saving the current one; Pop restores it. Used by
// party/summary so they show single-screen even when nested inside a
// MENU app (PC box, battle sub-menus, another menu).
void SIM_Wide_PushScene(enum SIMWideScene scene);
void SIM_Wide_PopScene(void);

// 1 while the battle awaits bottom-screen touch/menu input (command
// selection). Drives the auto-show of the docked panel in BATTLE.
void SIM_Wide_SetBattleTouchNeeded(int needsTouch);

// TRUE when the wide layout is actually in effect (ScreenLayout=wide on
// the GPU renderer, or SIM_WIDE_LAYOUT=1). Gate all wide game behaviour
// (camera aspect, cinematic retune) on this; FALSE = exactly as today.
BOOL SIM_Wide_IsWideLayout(void);

// battlehud hook: opt-in main-screen click routing (sim_layout.h).
void SIM_Wide_SetMainTouchEnabled(int enabled);
int SIM_Wide_PollMainTouch(int *x, int *y);

// Aspect ratio for game cameras: the wide aspect (16/9) when the wide
// layout is in effect, else the classic 4/3.
fx32 SIM_Wide_AspectRatio(void);

#endif // PORT_SIM_WIDE_H
