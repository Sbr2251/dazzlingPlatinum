#include "port/hirestext.h"

#include <nitro.h>
#include <stdlib.h>

#include "port/sim_config_prj.h"

// Enabled = sim_config_prj.ini [General] HiResText (default false: this is a
// prototype), overridable with SIM_HIRESTEXT=0/1 for headless A/B runs.
// Turning it off clears the overlay so no stale glyphs remain.
BOOL HiResText_IsEnabled(void)
{
    static int sEnvChecked = 0;
    static int sEnvValue = -1;
    static int sWasEnabled = 0;
    int enabled;

    if (!sEnvChecked) {
        const char *env = getenv("SIM_HIRESTEXT");
        sEnvValue = (env && env[0]) ? (env[0] != '0') : -1;
        sEnvChecked = 1;
    }

    if (sEnvValue >= 0) {
        enabled = sEnvValue;
    } else {
        enabled = SIM_Config_prj_GetConfig()->hiResText ? 1 : 0;
    }

    if (sWasEnabled && !enabled) {
        HiResText_ClearRect(0, 0, 0, 256, 192);
        HiResText_ClearRect(1, 0, 0, 256, 192);
    }
    sWasEnabled = enabled;
    return enabled ? TRUE : FALSE;
}
