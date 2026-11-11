#include <nitro.h>
#include <simulator/sim.h>
#include <simulator/sim_gui.hpp>
#include <simulator/imgui/imgui.hpp>

#include "sim_gui_prj.hpp"

#include "port/sim_config_prj.h"

namespace SIM::GUI {

static void ConfigCheckBox(const char * label, bool * configVar, bool& configChanged) {
    if(ImGui::Checkbox(label, configVar)) {
        configChanged = true;
    }
}

void ConfigPrjMain(bool * openState) {
    ImGui::Begin("pokeplatinum Config", openState);
    SIM_Config_prj_type * myConfig = SIM_Config_prj_GetConfig();
    bool configChanged = false;

    ConfigCheckBox("60 FPS", (bool*)&myConfig->enable60fps, configChanged);
    ConfigCheckBox("60 FPS Speed Fix", (bool*)&myConfig->enable60fpsSpeedFix, configChanged);
    ConfigCheckBox("Enable GF_Asserts", (bool*)&myConfig->enableAsserts, configChanged);
    ConfigCheckBox("DebugBreak on GF assertion fail", (bool*)&myConfig->breakDebuggerOnGfAssert, configChanged);

    if(configChanged) {
        SIM_Config_prj_SaveConfigFile(myConfig);
    }


    ImGui::End();
}
}