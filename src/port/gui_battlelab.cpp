#include <nitro.h>
#include <simulator/sim.h>
#include <simulator/sim_gui.hpp>
#include <simulator/imgui/imgui.hpp>

#include <dirent.h>
#include <stdio.h>
#include <string.h>

#include "sim_gui_prj.hpp"

extern "C" {
#include "port/headless_battle.h"
}

// Battle Lab: launch a battle spec (tools/battle/specs, copied into the
// build/app dir as battle_specs/ at build time) from the debug GUI.
// Starts the battle through the same start_battle path as the headless
// protocol. Close the panel and play/spectate the battle normally.
namespace SIM::GUI {

static char sBattleLabStatus[256] = "Pick a battle spec. You must be in the field (not already in battle).";

static char sSpecDir[64] = "battle_specs";

static void StartSpec(const char *fileName) {
    char cmd[1024];
    char reply[512];
    snprintf(cmd, sizeof(cmd), "{\"cmd\":\"start_battle\",\"spec_path\":\"%s/%s\"}", sSpecDir, fileName);
    HeadlessBattle_Start(cmd, reply, sizeof(reply));
    snprintf(sBattleLabStatus, sizeof(sBattleLabStatus), "%s -> %s", fileName, reply);
}

void BattleLabMain(bool *openState) {
    ImGui::Begin("Battle Lab", openState);
    ImGui::TextWrapped("%s", sBattleLabStatus);
    ImGui::Separator();

    DIR *dir = opendir(sSpecDir);
    if (dir == nullptr) {
        snprintf(sSpecDir, sizeof(sSpecDir), "tools/battle/specs");
        dir = opendir(sSpecDir);
    }
    if (dir == nullptr) {
        ImGui::Text("No battle_specs/ directory next to the game.");
        ImGui::Text("Build copies tools/battle/specs/*.json there.");
    } else {
        bool any = false;
        struct dirent *ent;
        while ((ent = readdir(dir)) != nullptr) {
            const char *name = ent->d_name;
            size_t len = strlen(name);
            if (len < 6 || strcmp(name + len - 5, ".json") != 0) {
                continue;
            }
            any = true;
            if (ImGui::Button(name)) {
                StartSpec(name);
            }
        }
        closedir(dir);
        if (!any) {
            ImGui::Text("battle_specs/ is empty.");
        }
    }

    ImGui::Separator();
    ImGui::TextWrapped("Mega Evolution: pick a move after using the Mega button on the move menu (L). Totem battles are doubles.");
    ImGui::End();
}

}
