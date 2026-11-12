#include <nitro.h>

#include "port/debug_field.h"

#include "field/field_system.h"
#include "script_manager.h"

static FieldSystem * s_fieldSystem = NULL;

FieldSystem * DEBUG_GetFieldSystem() {
    return s_fieldSystem;
}

void DEBUG_SetFieldSystem(FieldSystem * fieldSystem) {
    s_fieldSystem = fieldSystem;
}

DebugReloadResult DEBUG_ReloadMapScripts(void) {
    DebugReloadResult result = { 0, 0, -1, 0, 0, 0, 0 };

    if (s_fieldSystem == NULL) {
        return result;
    }

    if (ScriptManager_IsScriptRunning(s_fieldSystem) == TRUE) {
        result.scriptRunning = 1;
        return result;
    }

    result.ok = ScriptManager_ReloadCurrentMapData(s_fieldSystem, &result.mapHeader, &result.scriptArchive, &result.textBank, &result.scriptBytes, &result.textBytes) == TRUE;
    return result;
}