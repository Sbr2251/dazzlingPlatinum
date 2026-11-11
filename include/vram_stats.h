#ifndef POKEPLATINUM_VRAM_STATS_H
#define POKEPLATINUM_VRAM_STATS_H

#include <nitro.h>

// VRAM manager usage reporting (lane heap).
//
// 3D texture/palette VRAM is NOT enlarged (see g3d_pipeline.c): the sizes
// are hardware-encoded. This module only reports usage of whichever NNS
// VRAM manager is currently active, so the Memory panel and the headless
// `memory` command can show it.
//
// Totals are tracked from the init calls the game makes: linked-list
// managers via G3DPipeline_InitEx, frame managers via the direct
// NNS_GfdInitFrm* calls (VramStats_NoteFrm). `total`/`free` are
// 0xFFFFFFFF ("unknown") for a manager kind whose total is not tracked
// (frame managers take a slot count / byte count the game does not record
// at every site) or before any manager is initialised.
typedef struct VramStats {
    const char *texKind; // "lnk", "frm", or "unknown"
    u32 texTotal;
    u32 texFree;
    const char *plttKind;
    u32 plttTotal;
    u32 plttFree;
} VramStats;

void VramStats_NoteTexLnk(u32 totalBytes);
void VramStats_NotePlttLnk(u32 totalBytes);
void VramStats_NoteTexFrm(void);
void VramStats_NotePlttFrm(void);
void VramStats_NoteFrm(void); // both managers switched to frame type
void VramStats_Get(VramStats *out);

#endif // POKEPLATINUM_VRAM_STATS_H
