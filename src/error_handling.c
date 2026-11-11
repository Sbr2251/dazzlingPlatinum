#include "error_handling.h"

#include <nitro.h>
#include <stdlib.h>
#include <string.h>

#include "comm_manager.h"
#include "error_message_reset.h"

#ifdef SDK_PORT
#include "port/sim_config_prj.h"
#include <simulator/sim_headless.h>
#ifdef SDK_BUILD_LINUX
#include <signal.h>
#endif
#endif

void ErrorHandling_AssertFail(const char *file, int line, const char *expr)
{
#ifdef SDK_PORT
    // Headless/control runs always fail loudly (backtrace to stderr, exit 134),
    // regardless of the interactive assert config. See docs/headless_protocol.md.
    if (SIM_Headless_Enabled() || SIM_Control_Enabled()) {
        SIM_Headless_AssertFail(file, line, expr);
    }

    SIM_Config_prj_type * myConfig = SIM_Config_prj_GetConfig();
    if (!(myConfig->enableAsserts)) {
        return;
    }
    if (myConfig->breakDebuggerOnGfAssert) {
#ifdef SDK_BUILD_LINUX
        raise(SIGTRAP);
#endif
#ifdef SDK_BUILD_WIN64
        __debugbreak();
#endif
    }
    // Interactive with asserts enabled: log.txt + message box, then exit (SIM_Headless_AssertFail
    // handles the non-headless presentation and never returns).
    SIM_Headless_AssertFail(file, line, expr);
#endif

    if (CommManager_IsInitialized() && (OS_GetProcMode() != OS_PROCMODE_IRQ)) {
        ErrorMessageReset_PrintErrorAndReset();
    }
}
