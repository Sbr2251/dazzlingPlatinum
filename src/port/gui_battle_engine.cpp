// Battle Engine panel: live event log + instant-animations toggle.
// See docs/battle_engine.md. Events come from the engine-side history in
// battle_events.c (collected whenever a battle runs, panel or not).
#include <nitro.h>
#include <simulator/sim.h>
#include <simulator/sim_gui.hpp>
#include <simulator/imgui/imgui.hpp>
#include <stdio.h>
#include <string.h>
#include <string>

#include "sim_gui_prj.hpp"
#include "port/sim_config_prj.h"

#ifdef __cplusplus
extern "C" {
#endif
#include "battle/battle_events.h"
#ifdef __cplusplus
}
#endif

namespace SIM::GUI {

static std::string PrettyLine(const char *json) {
    // "#<seq> turn <n> <type> <rest>" - good enough for a live log; the raw
    // JSON stays available via Copy / Save.
    int seq = -1, turn = -1; char type[48] = "?";
    const char *p;
    if ((p = strstr(json, "\"seq\":"))) seq = atoi(p + 6);
    if ((p = strstr(json, "\"turn\":"))) turn = atoi(p + 7);
    if ((p = strstr(json, "\"type\":\""))) { int i = 0; p += 8; while (p[i] && p[i] != '"' && i < 47) { type[i] = p[i]; i++; } type[i] = 0; }
    char buf[640];
    snprintf(buf, sizeof(buf), "#%d turn %d %s  %s", seq, turn, type, json);
    return std::string(buf);
}

void BattleEngineMain(bool *openState) {
    ImGui::Begin("Battle Engine", openState);
    SIM_Config_prj_type *cfg = SIM_Config_prj_GetConfig();

    bool instant = cfg->battleInstantAnimations != FALSE;
    if (ImGui::Checkbox("Instant battle animations (fast mode)", &instant)) {
        cfg->battleInstantAnimations = instant ? TRUE : FALSE;
        // Safe mid-battle: fast mode is consulted per client command receipt;
        // animations already running finish normally, later ones skip.
        BattleEvents_SetFastEnabled(-1); // follow config/env
        SIM_Config_prj_SaveConfigFile(cfg);
    }
    ImGui::TextWrapped("Skips message, HP/EXP gauge and move-animation waits. Rules and RNG are unchanged; events stay identical (see docs/battle_engine.md).");

    int count = BattleEvents_HistoryCount();
    ImGui::Text("Events: %d", count);
    ImGui::SameLine();
    if (ImGui::Button("Copy events")) {
        std::string all;
        for (int i = 0; i < count; i++) { all += BattleEvents_HistoryLine(i); all += "\n"; }
        ImGui::SetClipboardText(all.c_str());
    }
    ImGui::SameLine();
    static char sSaveMsg[128] = "";
    if (ImGui::Button("Save events")) {
        snprintf(sSaveMsg, sizeof(sSaveMsg), "%s", BattleEvents_SaveHistory("battle_events.jsonl") ? "saved battle_events.jsonl (app data dir)" : "save failed");
    }
    ImGui::SameLine();
    if (ImGui::Button("Save replay")) {
        snprintf(sSaveMsg, sizeof(sSaveMsg), "%s", BattleEvents_SaveReplay("battle_replay.jsonl") ? "saved battle_replay.jsonl (app data dir)" : "save failed");
    }
    ImGui::SameLine();
    if (ImGui::Button("Clear")) BattleEvents_ClearHistory();
    if (sSaveMsg[0]) ImGui::Text("%s", sSaveMsg);

    ImGui::BeginChild("battle_event_log", ImVec2(0, 0), true, 0);
    for (int i = 0; i < count; i++) {
        std::string line = PrettyLine(BattleEvents_HistoryLine(i));
        ImGui::TextUnformatted(line.c_str());
    }
    static int sLastCount = 0;
    if (count != sLastCount) { ImGui::SetScrollHereY(1.0f); sLastCount = count; }
    ImGui::EndChild();
    ImGui::End();
}
}
