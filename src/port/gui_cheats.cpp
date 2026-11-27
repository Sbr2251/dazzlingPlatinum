#include <nitro.h>
#include <stdio.h>
#include <simulator/sim.h>
#include <simulator/sim_gui.hpp>
#include <simulator/imgui/imgui.hpp>

#include "sim_gui_prj.hpp"

#include "constants/fieldmap.h"
#include "constants/map_object.h"
#include "port/debug_field.h"
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

    ImGui::Separator();
    if (ImGui::CollapsingHeader("Story & Solaceon Presets")) {
        u16 liveArc2 = 0, liveSol = 0;
        BOOL livePostgame = FALSE, liveCineSol = FALSE;
        if (!DEBUG_StoryGetState(&liveArc2, &liveSol, &livePostgame, &liveCineSol)) {
            ImGui::TextDisabled("No save data loaded.");
        } else {
            static bool sInitialized = false;
            static u16 sLastArc2 = 0, sLastSol = 0;
            static BOOL sLastPostgame = FALSE, sLastCineSol = FALSE;
            static int sEditArc2 = 0, sEditSol = 0;
            static bool sEditPostgame = false, sEditCineSol = false;
            static bool sResetEntryCine = false;
            static char sStatusMsg[128] = "";

            if (!sInitialized || liveArc2 != sLastArc2 || liveSol != sLastSol
                || livePostgame != sLastPostgame || liveCineSol != sLastCineSol) {
                sEditArc2 = (int)liveArc2;
                sEditSol = (int)liveSol;
                sEditPostgame = (livePostgame != FALSE);
                sEditCineSol = (liveCineSol != FALSE);
                sLastArc2 = liveArc2;
                sLastSol = liveSol;
                sLastPostgame = livePostgame;
                sLastCineSol = liveCineSol;
                sInitialized = true;
            }

            ImGui::Text("Live: VAR_ARC2_PROGRESS=%u  VAR_SOLACEON_PROGRESS=%u",
                (unsigned)liveArc2, (unsigned)liveSol);
            ImGui::Text("      FLAG_GAME_COMPLETED=%d  FLAG_CINE_VISITED_SOLACEON=%d",
                livePostgame ? 1 : 0, liveCineSol ? 1 : 0);

            ImGui::PushItemWidth(120.0f);
            ImGui::InputInt("VAR_ARC2_PROGRESS", &sEditArc2, 1, 10);
            ImGui::InputInt("VAR_SOLACEON_PROGRESS", &sEditSol, 1, 10);
            ImGui::PopItemWidth();
            if (sEditArc2 < 0) sEditArc2 = 0;
            if (sEditArc2 > 65535) sEditArc2 = 65535;
            if (sEditSol < 0) sEditSol = 0;
            if (sEditSol > 65535) sEditSol = 65535;

            ImGui::Checkbox("FLAG_GAME_COMPLETED", &sEditPostgame);
            ImGui::Checkbox("FLAG_CINE_VISITED_SOLACEON", &sEditCineSol);

            if (ImGui::Button("Apply")) {
                if (DEBUG_StorySetState(sEditArc2, sEditSol, sEditPostgame ? 1 : 0, sEditCineSol ? 1 : 0)) {
                    snprintf(sStatusMsg, sizeof(sStatusMsg), "Applied: arc2=%d sol=%d postgame=%d cine_sol=%d",
                        sEditArc2, sEditSol, sEditPostgame ? 1 : 0, sEditCineSol ? 1 : 0);
                } else {
                    snprintf(sStatusMsg, sizeof(sStatusMsg), "Apply failed: no save/field state.");
                }
            }

            ImGui::Separator();
            ImGui::Text("Solaceon Band Presets:");
            auto ApplyBand = [&](const char *label, int arc2, int sol, int postgame) {
                if (ImGui::Button(label)) {
                    if (DEBUG_StorySetState(arc2, sol, postgame, -1)) {
                        snprintf(sStatusMsg, sizeof(sStatusMsg), "Set %s (arc2=%d, sol=%d, postgame=%d)",
                            label, arc2, sol, postgame);
                    } else {
                        snprintf(sStatusMsg, sizeof(sStatusMsg), "Preset failed: no save/field state.");
                    }
                }
            };

            ApplyBand("Band A (Pilgrim, 45)", 45, 0, 0);
            ApplyBand("Band B (Security, 60)", 60, 0, 0);
            ApplyBand("Band C (Splits, 90)", 90, 0, 0);
            ApplyBand("Band D (Briefing/Raid Ready, 99/10)", 99, 10, 0);
            ApplyBand("Band R (Raid Active, 99/20)", 99, 20, 0);
            ApplyBand("Band E (Seized, 99/50)", 99, 50, 0);
            ApplyBand("Band F (Postgame, 99/50)", 99, 50, 1);

            ImGui::Separator();
            if (DEBUG_GetFieldSystem() != nullptr) {
                ImGui::Checkbox("Reset entry cine", &sResetEntryCine);
                if (ImGui::Button("Warp: Route 209 Seam (560,674)")) {
                    if (DEBUG_WarpToCoords(MAP_HEADER_ROUTE_209, 560, 674, DIR_NORTH)) {
                        if (sResetEntryCine) {
                            DEBUG_StorySetState(-1, -1, -1, 0);
                        }
                        snprintf(sStatusMsg, sizeof(sStatusMsg), "Warping to Route 209 Seam (560,674)%s",
                            sResetEntryCine ? " [entry cine reset]" : "");
                    } else {
                        snprintf(sStatusMsg, sizeof(sStatusMsg), "Warp deferred: a field task/script is running.");
                    }
                }
                if (ImGui::Button("Warp: Solaceon Sanctuary Door (580,653)")) {
                    if (DEBUG_WarpToCoords(MAP_HEADER_SOLACEON_TOWN, 580, 653, DIR_NORTH)) {
                        snprintf(sStatusMsg, sizeof(sStatusMsg), "Warping to Solaceon Sanctuary Door (580,653)");
                    } else {
                        snprintf(sStatusMsg, sizeof(sStatusMsg), "Warp deferred: a field task/script is running.");
                    }
                }
            } else {
                ImGui::TextDisabled("Enter the field to enable quick warps.");
            }

            if (sStatusMsg[0] != '\0') {
                ImGui::TextWrapped("%s", sStatusMsg);
            }
        }
    }

    ImGui::End();
}
}
