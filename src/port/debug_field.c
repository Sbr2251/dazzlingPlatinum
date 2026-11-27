#include <nitro.h>

#include "port/debug_field.h"

#include "field/field_system.h"
#include "field/field_system_sub2_t.h"
#include "overlay005/map_name_popup.h"
#include "field_map_change.h"
#include "field_task.h"
#include "savedata.h"
#include "script_manager.h"
#include "vars_flags.h"

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

static BOOL StoryReadVar(FieldSystem *fsys, VarsFlags *vf, u16 varID, u16 *out) {
    if (out == NULL) {
        return TRUE;
    }
    if (fsys != NULL && fsys->saveData != NULL) {
        *out = FieldSystem_TryGetVar(fsys, varID);
        return TRUE;
    }
    if (vf != NULL) {
        u16 *ptr = VarsFlags_GetVarAddress(vf, varID);
        if (ptr == NULL) {
            return FALSE;
        }
        *out = *ptr;
        return TRUE;
    }
    return FALSE;
}

static BOOL StoryWriteVar(FieldSystem *fsys, VarsFlags *vf, u16 varID, int value) {
    if (value < 0) {
        return TRUE;
    }
    if (value > 0xFFFF) {
        value = 0xFFFF;
    }
    if (fsys != NULL && fsys->saveData != NULL) {
        u16 *ptr = FieldSystem_GetVarPointer(fsys, varID);
        if (ptr == NULL) {
            return FALSE;
        }
        *ptr = (u16)value;
        return TRUE;
    }
    if (vf != NULL) {
        u16 *ptr = VarsFlags_GetVarAddress(vf, varID);
        if (ptr == NULL) {
            return FALSE;
        }
        *ptr = (u16)value;
        return TRUE;
    }
    return FALSE;
}

static BOOL StoryReadFlag(FieldSystem *fsys, VarsFlags *vf, u16 flagID, BOOL *out) {
    if (out == NULL) {
        return TRUE;
    }
    if (fsys != NULL && fsys->saveData != NULL) {
        *out = FieldSystem_CheckFlag(fsys, flagID);
        return TRUE;
    }
    if (vf != NULL) {
        *out = VarsFlags_CheckFlag(vf, flagID);
        return TRUE;
    }
    return FALSE;
}

static BOOL StoryWriteFlag(FieldSystem *fsys, VarsFlags *vf, u16 flagID, int value) {
    if (value < 0) {
        return TRUE;
    }
    if (fsys != NULL && fsys->saveData != NULL) {
        if (value != 0) {
            FieldSystem_SetFlag(fsys, flagID);
        } else {
            FieldSystem_ClearFlag(fsys, flagID);
        }
        return TRUE;
    }
    if (vf != NULL) {
        if (value != 0) {
            VarsFlags_SetFlag(vf, flagID);
        } else {
            VarsFlags_ClearFlag(vf, flagID);
        }
        return TRUE;
    }
    return FALSE;
}

BOOL DEBUG_StoryGetState(u16 *arc2Progress, u16 *solaceonProgress, BOOL *gameCompleted, BOOL *cineVisitedSolaceon) {
    FieldSystem *fsys = s_fieldSystem;
    VarsFlags *vf = NULL;
    if (fsys == NULL || fsys->saveData == NULL) {
        SaveData *save = SaveData_Ptr();
        if (save == NULL) {
            return FALSE;
        }
        vf = SaveData_GetVarsFlags(save);
        if (vf == NULL) {
            return FALSE;
        }
    }

    if (!StoryReadVar(fsys, vf, VAR_ARC2_PROGRESS, arc2Progress)) {
        return FALSE;
    }
    if (!StoryReadVar(fsys, vf, VAR_SOLACEON_PROGRESS, solaceonProgress)) {
        return FALSE;
    }
    if (!StoryReadFlag(fsys, vf, FLAG_GAME_COMPLETED, gameCompleted)) {
        return FALSE;
    }
    if (!StoryReadFlag(fsys, vf, FLAG_CINE_VISITED_SOLACEON, cineVisitedSolaceon)) {
        return FALSE;
    }
    return TRUE;
}

BOOL DEBUG_StorySetState(int arc2Progress, int solaceonProgress, int gameCompleted, int cineVisitedSolaceon) {
    FieldSystem *fsys = s_fieldSystem;
    VarsFlags *vf = NULL;
    if (fsys == NULL || fsys->saveData == NULL) {
        SaveData *save = SaveData_Ptr();
        if (save == NULL) {
            return FALSE;
        }
        vf = SaveData_GetVarsFlags(save);
        if (vf == NULL) {
            return FALSE;
        }
    }

    if (!StoryWriteVar(fsys, vf, VAR_ARC2_PROGRESS, arc2Progress)) {
        return FALSE;
    }
    if (!StoryWriteVar(fsys, vf, VAR_SOLACEON_PROGRESS, solaceonProgress)) {
        return FALSE;
    }
    if (!StoryWriteFlag(fsys, vf, FLAG_GAME_COMPLETED, gameCompleted)) {
        return FALSE;
    }
    if (!StoryWriteFlag(fsys, vf, FLAG_CINE_VISITED_SOLACEON, cineVisitedSolaceon)) {
        return FALSE;
    }
    return TRUE;
}

BOOL DEBUG_WarpToCoords(int mapHeaderID, int x, int z, int dir) {
    FieldSystem *fsys = s_fieldSystem;
    if (fsys == NULL) {
        return FALSE;
    }
    if (FieldSystem_IsRunningTask(fsys)) {
        return FALSE;
    }
    if (fsys->unk_04 != NULL && fsys->unk_04->mapPopup != NULL) {
        MapNamePopUp_Hide(fsys->unk_04->mapPopup);
    }
    FieldTask_StartMapChangeFly(fsys, (enum MapHeaderID)mapHeaderID, -1, x, z, dir);
    return TRUE;
}
