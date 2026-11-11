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

void CheatsMain(bool * openState) {
    ImGui::Begin("Cheats", openState);
    SIM_Config_prj_type * myConfig = SIM_Config_prj_GetConfig();
    bool configChanged = false;

    ConfigCheckBox("Walk Through Walls", (bool*)&myConfig->walkThroughWalls, configChanged);
    ConfigCheckBox("Disable Random Encounters", (bool*)&myConfig->disableRandomEncounters, configChanged);
    ConfigCheckBox("Run from Trainer Battles", (bool*)&myConfig->runFromTrainerBattles, configChanged);



    if(configChanged) {
        SIM_Config_prj_SaveConfigFile(myConfig);
    }


    ImGui::End();
}
}