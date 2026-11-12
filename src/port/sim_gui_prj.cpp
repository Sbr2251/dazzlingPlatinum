#include <nitro.h>
#include <stdio.h>
#include <simulator/sim.h>
#include <simulator/sim_gui.hpp>
#include <simulator/imgui/imgui.hpp>
#include "sim_gui_prj.hpp"
#include "port/debug_field.h"

namespace SIM::GUI {

static bool sCreateMonOpen = false;
static bool sCreateItemOpen = false;
static bool sConfigPrjOpen = false;
static bool sCheatsOpen = false;
static bool sMapJumpOpen = false;
static bool sBattleEngineOpen = false;
static bool sBattleLabOpen = false;
static bool sMemoryOpen = false;

void PrjMain(bool * openState) {
    ImGui::Begin("pokeplatinum", openState);

    ImGui::Text("Git rev: %s", SIM_GetProjectGitHash());

    AppButton("Cheats", &sCheatsOpen, nullptr, CheatsMain);
    AppButton("Config", &sConfigPrjOpen, nullptr, ConfigPrjMain);
    AppButton("Gen Pokemon", &sCreateMonOpen, CreateMonInit, CreateMonMain);
    AppButton("Battle Engine", &sBattleEngineOpen, nullptr, BattleEngineMain);
    AppButton("Memory", &sMemoryOpen, nullptr, MemoryMain);
    AppButton("Gen Items", &sCreateItemOpen, CreateItemInit, CreateItemMain);

    if(DEBUG_GetFieldSystem() != nullptr) {
        AppButton("Jump to Map", &sMapJumpOpen, MapJumpInit, MapJumpMain);
        AppButton("Battle Lab", &sBattleLabOpen, nullptr, BattleLabMain);

        // Script hot-reload: after rebuilding the script/text targets with
        // ninja, re-read the current map's scripts and text bank from disk
        // without restarting. Refused while a script is running.
        static char sReloadMsg[256] = "";
        if (ImGui::Button("Reload Scripts", ImVec2(110, 20))) {
            DebugReloadResult r = DEBUG_ReloadMapScripts();
            if (r.scriptRunning) {
                snprintf(sReloadMsg, sizeof(sReloadMsg), "Reload deferred: a script is running.");
            } else if (r.ok) {
                snprintf(sReloadMsg, sizeof(sReloadMsg), "Reloaded map scripts (archive %u, %u bytes) and text bank %u (%u bytes).",
                         r.scriptArchive, r.scriptBytes, r.textBank, r.textBytes);
            } else {
                snprintf(sReloadMsg, sizeof(sReloadMsg), "Reload failed: script or text bank unreadable.");
            }
        }
        if (sReloadMsg[0]) ImGui::TextWrapped("%s", sReloadMsg);
    }

    ImGui::End();
}
}