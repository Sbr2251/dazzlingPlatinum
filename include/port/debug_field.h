#ifndef DEBUG_FIELD_H
#define DEBUG_FIELD_H
#include <nitro.h>
#include "field/field_system_decl.h"

#ifdef __cplusplus
extern "C" {
#endif

FieldSystem * DEBUG_GetFieldSystem();
void DEBUG_SetFieldSystem(FieldSystem * fieldSystem);

// Result of a debug script hot-reload (ScriptManager_ReloadCurrentMapData).
typedef struct {
    int ok;            // re-read succeeded; next script start uses the new files
    int scriptRunning; // refused because a field script is currently running
    int mapHeader;
    u32 scriptArchive;
    u32 textBank;
    u32 scriptBytes;
    u32 textBytes;
} DebugReloadResult;

DebugReloadResult DEBUG_ReloadMapScripts(void);

// Read/write story and Solaceon progression vars/flags (safe when not in the
// field or before a save is loaded; returns FALSE if neither field nor save
// exists). For DEBUG_StorySetState, pass -1 to leave a field unchanged.
BOOL DEBUG_StoryGetState(u16 *arc2Progress, u16 *solaceonProgress, BOOL *gameCompleted, BOOL *cineVisitedSolaceon);
BOOL DEBUG_StorySetState(int arc2Progress, int solaceonProgress, int gameCompleted, int cineVisitedSolaceon);

// Warp to a map header and tile coordinates while in the field. Returns FALSE
// if not in the field or if a field task (script/transition) is already running.
BOOL DEBUG_WarpToCoords(int mapHeaderID, int x, int z, int dir);

#ifdef __cplusplus
}
#endif

#endif
