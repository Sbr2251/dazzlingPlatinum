// Memory panel: live heap usage + high-water per heap, and VRAM manager usage.
// Pattern: src/port/gui_battle_engine.cpp. Stats come from heap.c (Heap_GetStats)
// and vram_stats.c; both compute on demand, so this panel costs nothing while closed.
#include <nitro.h>
#include <simulator/sim.h>
#include <simulator/sim_gui.hpp>
#include <simulator/imgui/imgui.hpp>
#include <stdio.h>
#include <string.h>

#include "sim_gui_prj.hpp"

// heap.h cannot be included in this C++ TU: it pulls in <nnsys.h> under the
// caller's linkage. Declare the HeapStats C ABI here (must match include/heap.h),
// and include vram_stats.h directly for the full VramStats layout + OOM counters.
extern "C" {
typedef struct HeapStats {
    u32 id;
    u32 size;
    u32 used;
    u32 peak;
    u32 peakSize;
    u32 blocks;
    const char *name;
} HeapStats;
BOOL Heap_GetStats(u32 heapID, HeapStats *out);
u32 Heap_GetNumHeaps(void);
#include "vram_stats.h"
}

namespace SIM::GUI {

static const char *FmtBytes(char *buf, size_t cap, u32 bytes)
{
    if (bytes == 0xFFFFFFFFu) {
        snprintf(buf, cap, "--");
    } else if (bytes >= 1024 * 1024) {
        snprintf(buf, cap, "%.2f MB", bytes / (1024.0 * 1024.0));
    } else if (bytes >= 1024) {
        snprintf(buf, cap, "%.1f KB", bytes / 1024.0);
    } else {
        snprintf(buf, cap, "%u B", bytes);
    }
    return buf;
}

void MemoryMain(bool *openState) {
    ImGui::Begin("Memory", openState);
    ImGui::Text("Heaps are 4x their DS sizes on the port (heap scale 4, emulated main RAM 32 MB).");
    ImGui::Text("Peak is peak-ever used bytes per heap since boot; Used counts direct NNS allocations too.");

    VramStats vram;
    VramStats_GetFull(&vram);
    char b1[32], b2[32], b3[32], b4[32];
    bool texKnown = (vram.texTotal != 0xFFFFFFFFu && vram.texFree != 0xFFFFFFFFu);
    u32 texUsed = (texKnown && vram.texTotal >= vram.texFree) ? (vram.texTotal - vram.texFree) : 0;
    ImGui::Text("VRAM tex: %s total %s free %s (used %s)", vram.texKind,
        FmtBytes(b1, sizeof(b1), vram.texTotal), FmtBytes(b2, sizeof(b2), vram.texFree),
        texKnown ? FmtBytes(b3, sizeof(b3), texUsed) : "--");
    if (vram.texTotal != 0xFFFFFFFFu && vram.texFree != 0xFFFFFFFFu && vram.texTotal > 0) {
        float frac = (float)texUsed / (float)vram.texTotal;
        if (frac < 0.0f) frac = 0.0f;
        if (frac > 1.0f) frac = 1.0f;
        char overlay[64];
        snprintf(overlay, sizeof(overlay), "tex %.1f%% (%s / %s)",
            100.0f * frac, FmtBytes(b1, sizeof(b1), texUsed), FmtBytes(b2, sizeof(b2), vram.texTotal));
        ImGui::ProgressBar(frac, ImVec2(-1.0f, 0.0f), overlay);
    }

    bool plttKnown = (vram.plttTotal != 0xFFFFFFFFu && vram.plttFree != 0xFFFFFFFFu);
    u32 plttUsed = (plttKnown && vram.plttTotal >= vram.plttFree) ? (vram.plttTotal - vram.plttFree) : 0;
    ImGui::Text("VRAM pltt: %s total %s free %s (used %s)", vram.plttKind,
        FmtBytes(b1, sizeof(b1), vram.plttTotal), FmtBytes(b2, sizeof(b2), vram.plttFree),
        plttKnown ? FmtBytes(b4, sizeof(b4), plttUsed) : "--");
    if (vram.plttTotal != 0xFFFFFFFFu && vram.plttFree != 0xFFFFFFFFu && vram.plttTotal > 0) {
        float frac = (float)plttUsed / (float)vram.plttTotal;
        if (frac < 0.0f) frac = 0.0f;
        if (frac > 1.0f) frac = 1.0f;
        char overlay[64];
        snprintf(overlay, sizeof(overlay), "pltt %.1f%% (%s / %s)",
            100.0f * frac, FmtBytes(b1, sizeof(b1), plttUsed), FmtBytes(b2, sizeof(b2), vram.plttTotal));
        ImGui::ProgressBar(frac, ImVec2(-1.0f, 0.0f), overlay);
    }

    bool anyOom = (vram.texOomCount > 0 || vram.plttOomCount > 0 || vram.poolOomCount > 0);
    ImVec4 oomCol = anyOom ? ImVec4(1.0f, 0.3f, 0.3f, 1.0f) : ImVec4(0.65f, 0.65f, 0.65f, 1.0f);
    ImGui::TextColored(oomCol, "OOM: tex %u  pltt %u  pool %u",
        vram.texOomCount, vram.plttOomCount, vram.poolOomCount);

    ImGui::Text("VRAM is NOT enlarged: sizes are DS hardware limits (see g3d_pipeline.c).");

    if (ImGui::BeginTable("heaps", 6, ImGuiTableFlags_RowBg | ImGuiTableFlags_Borders | ImGuiTableFlags_ScrollY)) {
        ImGui::TableSetupColumn("ID");
        ImGui::TableSetupColumn("Name");
        ImGui::TableSetupColumn("Size");
        ImGui::TableSetupColumn("Used");
        ImGui::TableSetupColumn("Peak");
        ImGui::TableSetupColumn("Peak %");
        ImGui::TableHeadersRow();
        u32 totalSize = 0, totalUsed = 0, totalPeak = 0, totalPeakSize = 0;
        u32 n = Heap_GetNumHeaps();
        for (u32 i = 0; i < n; i++) {
            HeapStats st;
            if (!Heap_GetStats(i, &st) || (st.size == 0 && st.peak == 0)) continue;
            totalSize += st.size;
            totalUsed += st.used;
            totalPeak += st.peak;
            totalPeakSize += st.peakSize;
            char sizeBuf[32], usedBuf[32], peakBuf[32];
            ImGui::TableNextRow();
            ImGui::TableNextColumn(); ImGui::Text("%u", st.id);
            ImGui::TableNextColumn(); ImGui::Text("%s", st.name ? st.name : "(unnamed)");
            ImGui::TableNextColumn(); ImGui::Text("%s", FmtBytes(sizeBuf, sizeof(sizeBuf), st.size));
            ImGui::TableNextColumn(); ImGui::Text("%s", FmtBytes(usedBuf, sizeof(usedBuf), st.used));
            ImGui::TableNextColumn(); ImGui::Text("%s", FmtBytes(peakBuf, sizeof(peakBuf), st.peak));
            ImGui::TableNextColumn(); ImGui::Text("%.1f%%", st.peakSize ? (100.0 * st.peak / st.peakSize) : 0.0);
        }
        ImGui::TableNextRow();
        char sizeBuf[32], usedBuf[32], peakBuf[32];
        ImGui::TableNextColumn(); ImGui::Text("");
        ImGui::TableNextColumn(); ImGui::Text("TOTAL (live)");
        ImGui::TableNextColumn(); ImGui::Text("%s", FmtBytes(sizeBuf, sizeof(sizeBuf), totalSize));
        ImGui::TableNextColumn(); ImGui::Text("%s", FmtBytes(usedBuf, sizeof(usedBuf), totalUsed));
        ImGui::TableNextColumn(); ImGui::Text("%s", FmtBytes(peakBuf, sizeof(peakBuf), totalPeak));
        ImGui::TableNextColumn(); ImGui::Text("%.1f%%", totalPeakSize ? (100.0 * totalPeak / totalPeakSize) : 0.0);
        ImGui::EndTable();
    }
    ImGui::End();
}
}
