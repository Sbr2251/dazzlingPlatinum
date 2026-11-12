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

#ifdef __cplusplus
}
#endif

#endif
