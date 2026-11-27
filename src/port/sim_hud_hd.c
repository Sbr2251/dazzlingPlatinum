// Game-side bridge to the HD battle HUD renderer (BDSP parity).
// The contract is subprojects/libntr/include/simulator/sim_hud_hd.h; the
// renderer symbols are weak so the game links and runs (drawing nothing)
// before/without the GPU implementation.

#include "port/sim_hud_hd.h"

#ifdef SDK_PORT
extern void SIM_HudHD_Submit(const SIM_HudHD_Frame *frame) __attribute__((weak));
extern int SIM_HudHD_IsSupported(void) __attribute__((weak));
#endif

BOOL GameHudHD_IsSupported(void)
{
#ifdef SDK_PORT
    return (SIM_HudHD_IsSupported != NULL && SIM_HudHD_IsSupported()) ? TRUE : FALSE;
#else
    return FALSE;
#endif
}

void GameHudHD_Submit(const SIM_HudHD_Frame *frame)
{
#ifdef SDK_PORT
    if (frame != NULL && SIM_HudHD_Submit != NULL) {
        SIM_HudHD_Submit(frame);
    }
#else
    (void)frame;
#endif
}
