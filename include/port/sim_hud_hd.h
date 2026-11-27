#ifndef PORT_SIM_HUD_HD_H
#define PORT_SIM_HUD_HD_H

#include <nitro/types.h>

#ifdef SDK_PORT
#include <simulator/sim_hud_hd.h>
#else
typedef struct SIM_HudHD_Frame SIM_HudHD_Frame;
#endif

// Game-side facade over the HD battle HUD renderer (weak; see sim_hud_hd.c).
BOOL GameHudHD_IsSupported(void);
void GameHudHD_Submit(const SIM_HudHD_Frame *frame);

#endif // PORT_SIM_HUD_HD_H
