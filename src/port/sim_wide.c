// Game-side facade over the simulator's wide-layout scene API
// (wide-OUT/API.md v1). See include/port/sim_wide.h.
//
// The simulator functions are declared weak here: libntr (lane widecomp)
// provides the strong definitions when its wide layout lands, and until
// then every call below is a no-op and SIM_Wide_IsWideLayout() is FALSE
// (unless forced for headless verification), so this tree builds and
// behaves exactly as today on its own. When the strong symbols are
// linked, the weak references bind to them and the calls go through
// unconditionally, as the API contract requires.

#include "port/sim_wide.h"

#include <nitro.h>
#include <stdio.h>
#include <stdlib.h>

// --- simulator API (API.md v1), weak until libntr provides it ---------
extern void SIM_Layout_SetScene(int scene) __attribute__((weak));
extern void SIM_Layout_SetBattleTouchNeeded(int needsTouch) __attribute__((weak));
extern int SIM_Layout_IsWide(void) __attribute__((weak));
extern float SIM_Layout_GetWideAspect(void) __attribute__((weak));
extern void SIM_Layout_SetMainTouchEnabled(int enabled) __attribute__((weak));
extern int SIM_Layout_GetMainTouch(int *x, int *y) __attribute__((weak));

static int sLastScene = -1;
static int sLastTouchNeeded = -1;

static BOOL WideDebugLog(void)
{
    const char *value = getenv("SIM_WIDE_DEBUG");
    return value != NULL && value[0] == '1';
}

void SIM_Wide_SetScene(enum SIMWideScene scene)
{
    if ((int)scene == sLastScene) {
        return;
    }
    sLastScene = (int)scene;

    if (WideDebugLog()) {
        fprintf(stderr, "[widegame] SIM_Layout_SetScene(%d)\n", (int)scene);
    }

    if (SIM_Layout_SetScene != NULL) {
        SIM_Layout_SetScene((int)scene);
    }
}

void SIM_Wide_SetBattleTouchNeeded(int needsTouch)
{
    needsTouch = needsTouch != 0;

    if (needsTouch == sLastTouchNeeded) {
        return;
    }
    sLastTouchNeeded = needsTouch;

    if (WideDebugLog()) {
        fprintf(stderr, "[widegame] SIM_Layout_SetBattleTouchNeeded(%d)\n", needsTouch);
    }

    if (SIM_Layout_SetBattleTouchNeeded != NULL) {
        SIM_Layout_SetBattleTouchNeeded(needsTouch);
    }
}

BOOL SIM_Wide_IsWideLayout(void)
{
    // Headless verification override, mirroring SIM_FX_WIDE_CAMERA:
    // SIM_WIDE_LAYOUT=1 forces the wide game behaviour on (with
    // DebugWideCamera standing in for the wide render), =0 forces off.
    const char *env = getenv("SIM_WIDE_LAYOUT");

    if (env != NULL && env[0] != '\0') {
        return env[0] != '0';
    }

    if (SIM_Layout_IsWide != NULL) {
        return SIM_Layout_IsWide() != 0;
    }

    return FALSE;
}

fx32 SIM_Wide_AspectRatio(void)
{
    if (!SIM_Wide_IsWideLayout()) {
        return FX32_ONE * 4 / 3;
    }

    if (SIM_Layout_GetWideAspect != NULL) {
        // fx32 is 20.12 fixed point; the API returns a float ratio.
        return (fx32)(SIM_Layout_GetWideAspect() * (float)FX32_ONE);
    }

    return FX32_ONE * 16 / 9;
}

// battlehud hook: main-touch facade (no-ops until libntr provides them).
void SIM_Wide_SetMainTouchEnabled(int enabled)
{
    if (SIM_Layout_SetMainTouchEnabled != NULL) {
        SIM_Layout_SetMainTouchEnabled(enabled);
    }
}

int SIM_Wide_PollMainTouch(int *x, int *y)
{
    if (SIM_Layout_GetMainTouch != NULL) {
        return SIM_Layout_GetMainTouch(x, y);
    }
    return 0;
}
