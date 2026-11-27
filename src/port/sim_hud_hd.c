// Game-side bridge to the HD battle HUD renderer (BDSP parity).
// The contract is subprojects/libntr/include/simulator/sim_hud_hd.h; the
// renderer symbols are weak so the game links and runs (drawing nothing)
// before/without the GPU implementation.

#include "port/sim_hud_hd.h"

#ifdef SDK_PORT
__attribute__((weak)) void SIM_HudHD_Submit(const SIM_HudHD_Frame *frame)
{
    (void)frame;
}

__attribute__((weak)) int SIM_HudHD_IsSupported(void)
{
    return 0;
}
#endif

BOOL GameHudHD_IsSupported(void)
{
#ifdef SDK_PORT
    return SIM_HudHD_IsSupported() ? TRUE : FALSE;
#else
    return FALSE;
#endif
}

void GameHudHD_Submit(const SIM_HudHD_Frame *frame)
{
#ifdef SDK_PORT
    if (frame != NULL) {
        SIM_HudHD_Submit(frame);
    }
#else
    (void)frame;
#endif
}
