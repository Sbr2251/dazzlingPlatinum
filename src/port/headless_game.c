// Game-side headless protocol handlers (docs/headless_protocol.md, step 3).
// Implements the weak HeadlessGame_Command / HeadlessGame_State hooks that the
// simulator's lockstep control (sim_headless_control.cpp) calls. Symbolic names
// come from the build-generated tables in headless_names.c (gen_headless_names.py).
#include <nitro.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "generated/pokemon_data_params.h"
#include "headless_names.h"

#include "port/debug_field.h"
#include "port/headless_game.h"
#include "port/headless_battle.h"

#include "field/field_system.h"
#include "field/field_system_sub2_t.h"
#include "overlay005/land_data.h"
#include "overlay005/map_name_popup.h"
#include "field_map_change.h"
#include "map_header_data.h"
#include "map_object.h"
#include "player_avatar.h"
#include "script_manager.h"
#include "terrain_collision_manager.h"

#include "bag.h"
#include "party.h"
#include "pokemon.h"
#include "savedata.h"
#include "vars_flags.h"

#include "battle/battle_controller_player.h"
#include "battle/battle_system.h"

#include "gui_createitem_utils.h"
#include "gui_mapjump_utils.h"

// ---------------------------------------------------------------- registry

static BattleSystem *sBattleSys = NULL;
static int sOverlayId = -1;

void Headless_SetBattleSystem(BattleSystem *battleSys) { sBattleSys = battleSys; }
void Headless_SetOverlay(int overlayId) { sOverlayId = overlayId; }

// Injected press for `talk`: the control layer takes it after our reply.
static unsigned sInjectMask = 0;
static int sInjectFrames = 0;

int HeadlessGame_TakeInjectedPress(unsigned *mask, unsigned *xy, int *frames) {
    if (sInjectFrames <= 0) return 0;
    *mask = sInjectMask; *xy = 0; *frames = sInjectFrames;
    sInjectMask = 0; sInjectFrames = 0;
    return 1;
}

// ---------------------------------------------------------------- JSON in

static BOOL FindKey(const char *s, const char *key, const char **pos) {
    char pat[64];
    snprintf(pat, sizeof(pat), "\"%s\"", key);
    const char *p = strstr(s, pat);
    if (!p) return FALSE;
    p = strchr(p + strlen(pat), ':');
    if (!p) return FALSE;
    *pos = p + 1;
    return TRUE;
}
static BOOL JsonStr(const char *s, const char *key, char *out, size_t cap) {
    const char *p;
    if (!FindKey(s, key, &p)) return FALSE;
    while (*p == ' ' || *p == '\t') p++;
    if (*p != '"') return FALSE;
    const char *e = strchr(p + 1, '"');
    if (!e) return FALSE;
    size_t n = (size_t)(e - (p + 1));
    if (n >= cap) n = cap - 1;
    memcpy(out, p + 1, n); out[n] = 0;
    return TRUE;
}
static BOOL JsonLong(const char *s, const char *key, long *out) {
    const char *p;
    if (!FindKey(s, key, &p)) return FALSE;
    *out = strtol(p, NULL, 10);
    return TRUE;
}
static BOOL JsonBoolVal(const char *s, const char *key, BOOL *out) {
    const char *p;
    if (!FindKey(s, key, &p)) return FALSE;
    while (*p == ' ' || *p == '\t') p++;
    *out = strncmp(p, "true", 4) == 0;
    return TRUE;
}

// Extract a string array for a key ("vars":["VAR_X",...]) into out (NUL-separated list not needed:
// caller iterates with this helper by index).
static int JsonStrArrayItem(const char *s, const char *key, int index, char *out, size_t cap) {
    const char *p;
    if (!FindKey(s, key, &p)) return 0;
    p = strchr(p, '[');
    if (!p) return 0;
    for (int i = 0;; i++) {
        p = strchr(p, '"');
        if (!p) return 0;
        const char *e = strchr(p + 1, '"');
        if (!e) return 0;
        if (i == index) {
            size_t n = (size_t)(e - (p + 1));
            if (n >= cap) n = cap - 1;
            memcpy(out, p + 1, n); out[n] = 0;
            return 1;
        }
        p = e + 1;
        const char *comma = strchr(p, ',');
        const char *close = strchr(p, ']');
        if (close && (!comma || close < comma)) return 0;
    }
}

// ---------------------------------------------------------------- JSON out

typedef struct { char *buf; size_t cap; size_t len; } Out;
static void OutFmt(Out *o, const char *fmt, ...) {
    va_list ap; va_start(ap, fmt);
    if (o->len < o->cap) {
        int n = vsnprintf(o->buf + o->len, o->cap - o->len, fmt, ap);
        if (n > 0) o->len += (size_t)n;
    }
    va_end(ap);
}
static void ErrOut(char *reply, size_t cap, const char *msg) {
    snprintf(reply, cap, "{\"ok\":false,\"error\":\"%s\"}", msg);
}

// ---------------------------------------------------------------- helpers

extern unsigned long long SIM_Headless_FrameCount(void);

static const char *DirName(int dir) {
    const char *n = Headless_NameOf(kHeadlessDirs, kHeadlessDirsCount, dir);
    return n ? n : "DIR_NONE";
}

static MapObject *FindObject(FieldSystem *fsys, int localId) {
    MapObject *obj = NULL;
    int idx = 0;
    while (MapObjectMan_FindObjectWithStatus(fsys->mapObjMan, &obj, &idx, MAP_OBJ_STATUS_0) == TRUE) {
        if ((int)MapObject_GetLocalID(obj) == localId) return obj;
    }
    return NULL;
}

// ---------------------------------------------------------------- commands

static void CmdWarp(const char *line, char *reply, size_t cap) {
    char name[128]; long x = 0, z = 0; char dirName[64] = "DIR_SOUTH";
    if (!JsonStr(line, "map", name, sizeof(name))) { ErrOut(reply, cap, "warp needs map"); return; }
    const HeadlessName *m = Headless_Lookup(kHeadlessMapHeaders, kHeadlessMapHeadersCount, name);
    if (!m) { ErrOut(reply, cap, "unknown map"); return; }
    FieldSystem *fsys = DEBUG_GetFieldSystem();
    if (!fsys) { ErrOut(reply, cap, "not in the field"); return; }
    JsonLong(line, "x", &x); JsonLong(line, "z", &z);
    JsonStr(line, "dir", dirName, sizeof(dirName));
    const HeadlessName *d = Headless_Lookup(kHeadlessDirs, kHeadlessDirsCount, dirName);
    // Hide the map-name popup first: its task outlives the field BgConfig during map
    // teardown and would clear a window into freed memory (pre-existing race, hit when
    // warping while the popup is up - exactly what a test runner does after loading).
    if (fsys->unk_04 && fsys->unk_04->mapPopup) MapNamePopUp_Hide(fsys->unk_04->mapPopup);
    FieldTask_StartMapChangeFly(fsys, (enum MapHeaderID)m->id, -1, (int)x, (int)z, d ? d->id : DIR_SOUTH);
    snprintf(reply, cap, "{\"ok\":true}");
}

static void CmdSetVar(const char *line, char *reply, size_t cap) {
    char name[128]; long value = 0;
    if (!JsonStr(line, "name", name, sizeof(name)) || !JsonLong(line, "value", &value)) { ErrOut(reply, cap, "set_var needs name and value"); return; }
    const HeadlessName *v = Headless_Lookup(kHeadlessVars, kHeadlessVarsCount, name);
    if (!v) { ErrOut(reply, cap, "unknown var"); return; }
    FieldSystem *fsys = DEBUG_GetFieldSystem();
    if (fsys) {
        u16 *ptr = FieldSystem_GetVarPointer(fsys, (u16)v->id);
        if (!ptr) { ErrOut(reply, cap, "var has no storage here"); return; }
        *ptr = (u16)value;
    } else {
        SaveData *save = SaveData_Ptr();
        if (!save) { ErrOut(reply, cap, "no save data"); return; }
        *VarsFlags_GetVarAddress(SaveData_GetVarsFlags(save), (u16)v->id) = (u16)value;
    }
    snprintf(reply, cap, "{\"ok\":true}");
}

static void CmdSetFlag(const char *line, char *reply, size_t cap) {
    char name[160]; BOOL value = TRUE;
    if (!JsonStr(line, "name", name, sizeof(name))) { ErrOut(reply, cap, "set_flag needs name"); return; }
    JsonBoolVal(line, "value", &value);
    const HeadlessName *f = Headless_Lookup(kHeadlessFlags, kHeadlessFlagsCount, name);
    if (!f) { ErrOut(reply, cap, "unknown flag"); return; }
    FieldSystem *fsys = DEBUG_GetFieldSystem();
    if (fsys) {
        if (value) FieldSystem_SetFlag(fsys, (u16)f->id); else FieldSystem_ClearFlag(fsys, (u16)f->id);
    } else {
        SaveData *save = SaveData_Ptr();
        if (!save) { ErrOut(reply, cap, "no save data"); return; }
        VarsFlags *vf = SaveData_GetVarsFlags(save);
        if (value) VarsFlags_SetFlag(vf, (u16)f->id); else VarsFlags_ClearFlag(vf, (u16)f->id);
    }
    snprintf(reply, cap, "{\"ok\":true}");
}

static void CmdGiveItem(const char *line, char *reply, size_t cap) {
    char name[128]; long qty = 1;
    if (!JsonStr(line, "item", name, sizeof(name))) { ErrOut(reply, cap, "give_item needs item"); return; }
    JsonLong(line, "qty", &qty);
    const HeadlessName *it = Headless_Lookup(kHeadlessItems, kHeadlessItemsCount, name);
    if (!it) { ErrOut(reply, cap, "unknown item"); return; }
    if (!SaveData_Ptr()) { ErrOut(reply, cap, "no save data"); return; }
    GUI_CreateItem_GenItems(it->id, (int)qty);
    snprintf(reply, cap, "{\"ok\":true}");
}

static void CmdTalk(const char *line, char *reply, size_t cap) {
    FieldSystem *fsys = DEBUG_GetFieldSystem();
    if (!fsys || !fsys->playerAvatar) { ErrOut(reply, cap, "not in the field"); return; }
    long objNum = -1;
    int localId = -1;
    char locName[160];
    if (JsonLong(line, "object", &objNum)) {
        localId = (int)objNum;
    } else if (JsonStr(line, "localid", locName, sizeof(locName))) {
        int header = fsys->location ? fsys->location->mapHeaderID : -1;
        for (int i = 0; i < kHeadlessLocalsCount; i++)
            if (kHeadlessLocals[i].mapHeader == header && strcmp(kHeadlessLocals[i].name, locName) == 0) { localId = kHeadlessLocals[i].localId; break; }
        if (localId < 0) { ErrOut(reply, cap, "unknown localid on this map"); return; }
    } else { ErrOut(reply, cap, "talk needs localid or object"); return; }

    MapObject *obj = FindObject(fsys, localId);
    if (!obj) { ErrOut(reply, cap, "object not found"); return; }
    int ox = MapObject_GetX(obj), oz = MapObject_GetZ(obj);
    // Player goes on a free adjacent tile, facing the object; then A is pressed (injected).
    static const int dx[4] = {0, 0, -1, 1};   // from DIR_NORTH..DIR_EAST offsets to stand at
    static const int dz[4] = {-1, 1, 0, 0};
    static const int face[4] = {DIR_SOUTH, DIR_NORTH, DIR_EAST, DIR_WEST}; // facing back at the object
    for (int d = 0; d < 4; d++) {
        int px = ox + dx[d], pz = oz + dz[d];
        if (TerrainCollisionManager_CheckCollision(fsys, px, pz)) continue;
        if (!MapHeaderData_IsPosFreeOfObjectEvents(fsys, (u16)px, (u16)pz)) continue;
        PlayerAvatar_SetPosDirFromCoords(fsys->playerAvatar, px, pz, face[d]);
        // Match the object's elevation: interaction requires the same height level
        // (sub_0203C9B0), and the teleport otherwise leaves the player at Y=0.
        Player_SetYPos(fsys->playerAvatar, MapObject_GetPosY(obj));
        // Resync the map lazy loader's tracked position with the teleported player,
        // or its next tick asserts on a diagonal "move" (land_data.c).
        if (fsys->landDataMan) LandDataManager_TrackTarget(PlayerAvatar_GetPos(fsys->playerAvatar), fsys->landDataMan);
        // Start the object's script exactly as the A-button interaction does
        // (field_control.c: ScriptManager_Set with the object's script). Doing it
        // directly, rather than pressing A and hoping, makes talk deterministic:
        // a wandering NPC can step off the faced tile before a pressed A lands.
        {
            ScriptManager *sm = NULL;
            if (fsys->task) {
                void *env = FieldTask_GetEnv(fsys->task);
                if (env && ((ScriptManager *)env)->magic == SCRIPT_MANAGER_MAGIC_NUMBER) sm = env;
            }
            if (sm) { ErrOut(reply, cap, "a script is already running"); return; }
            // Push the script onto the field task stack (ScriptManager_Set would
            // assert: the field always has a current task while idling).
            if (fsys->task) ScriptManager_Start(fsys->task, MapObject_GetScript(obj), obj, NULL);
            else ScriptManager_Set(fsys, MapObject_GetScript(obj), obj);
        }
        snprintf(reply, cap, "{\"ok\":true,\"object\":{\"localid\":%d,\"x\":%d,\"z\":%d},\"player\":{\"x\":%d,\"z\":%d,\"dir\":\"%s\"}}",
                 localId, ox, oz, px, pz, DirName(face[d]));
        return;
    }
    ErrOut(reply, cap, "no free adjacent tile");
}

int HeadlessGame_Command(const char *line, char *reply, size_t cap) {
    char cmd[64];
    if (!JsonStr(line, "cmd", cmd, sizeof(cmd))) return 0;
    if (strcmp(cmd, "warp") == 0) CmdWarp(line, reply, cap);
    else if (strcmp(cmd, "set_var") == 0) CmdSetVar(line, reply, cap);
    else if (strcmp(cmd, "set_flag") == 0) CmdSetFlag(line, reply, cap);
    else if (strcmp(cmd, "give_item") == 0) CmdGiveItem(line, reply, cap);
    else if (strcmp(cmd, "talk") == 0) CmdTalk(line, reply, cap);
    else if (strcmp(cmd, "start_battle") == 0) return HeadlessBattle_Start(line, reply, cap);
    else return 0;
    return 1;
}

// ---------------------------------------------------------------- state

int HeadlessGame_State(const char *line, char *reply, size_t cap) {
    Out o = { reply, cap, 0 };
    FieldSystem *fsys = DEBUG_GetFieldSystem();
    OutFmt(&o, "{\"ok\":true,\"frame\":%llu", SIM_Headless_FrameCount());
    OutFmt(&o, ",\"overlay\":%d", sOverlayId);
    if (sBattleSys) {
        BattleContext *ctx = BattleSystem_GetBattleContext(sBattleSys);
        OutFmt(&o, ",\"app\":\"battle\",\"battle\":{\"turn\":%d,\"waiting\":%s,\"battlers\":[",
          ctx ? ctx->totalTurns : 0,
          (ctx && ctx->command == BATTLE_CONTROL_COMMAND_SELECTION_INPUT) ? "true" : "false");
        int max = BattleSystem_GetMaxBattlers(sBattleSys);
        for (int i = 0; i < max; i++) {
            const BattleMon *mon = ctx ? &ctx->battleMons[i] : NULL;
            if (!mon || mon->species == 0) continue;
            const char *sp = Headless_NameOf(kHeadlessSpecies, kHeadlessSpeciesCount, mon->species);
            const char *held = Headless_NameOf(kHeadlessItems, kHeadlessItemsCount, mon->heldItem);
            OutFmt(&o, "%s{\"battler\":%d,\"species\":\"%s\",\"species_id\":%d,\"level\":%d,\"hp\":%d,\"max_hp\":%d,\"held_item\":\"%s\"}",
              i ? "," : "", i, sp ? sp : "SPECIES_?", mon->species, mon->level, mon->curHP, (int)mon->maxHP, held ? held : "ITEM_NONE");
        }
        OutFmt(&o, "]}");
    } else if (fsys) {
        int header = fsys->location ? fsys->location->mapHeaderID : -1;
        const char *mapName = Headless_NameOf(kHeadlessMapHeaders, kHeadlessMapHeadersCount, header);
        OutFmt(&o, ",\"app\":\"field\",\"map\":\"%s\",\"map_id\":%d", mapName ? mapName : "MAP_HEADER_?", header);
        if (fsys->playerAvatar) {
            OutFmt(&o, ",\"player\":{\"x\":%d,\"z\":%d,\"dir\":\"%s\"}",
              PlayerAvatar_GetXPos(fsys->playerAvatar), PlayerAvatar_GetZPos(fsys->playerAvatar),
              DirName(PlayerAvatar_GetFacingDir(fsys->playerAvatar)));
        }
        // Running script + message box, via the script manager if a script task is active.
        ScriptManager *sm = NULL;
        if (fsys->task) {
            void *env = FieldTask_GetEnv(fsys->task);
            if (env && ((ScriptManager *)env)->magic == SCRIPT_MANAGER_MAGIC_NUMBER) sm = env;
        }
        if (sm) {
            ScriptContext *ctx = sm->ctx[SCRIPT_CONTEXT_MAIN];
            long offset = -1;
            if (ctx && ctx->scripts && ctx->scriptPtr) offset = (long)(ctx->scriptPtr - ctx->scripts);
            OutFmt(&o, ",\"script\":{\"id\":%d,\"offset\":%ld}", sm->scriptID, offset);
            OutFmt(&o, ",\"message_waiting\":%s", sm->isMsgBoxOpen ? "true" : "false");
        } else {
            OutFmt(&o, ",\"script\":null,\"message_waiting\":false");
        }
    } else {
        OutFmt(&o, ",\"app\":\"other\"");
    }

    // Party: always reported (species, level, hp, held item).
    SaveData *save = SaveData_Ptr();
    if (save) {
        Party *party = SaveData_GetParty(save);
        OutFmt(&o, ",\"party\":[");
        int count = party ? Party_GetCurrentCount(party) : 0;
        for (int i = 0; i < count; i++) {
            Pokemon *mon = Party_GetPokemonBySlotIndex(party, i);
            if (!mon) continue;
            u32 species = Pokemon_GetValue(mon, MON_DATA_SPECIES, NULL);
            u32 level = Pokemon_GetValue(mon, MON_DATA_LEVEL, NULL);
            u32 hp = Pokemon_GetValue(mon, MON_DATA_HP, NULL);
            u32 maxHp = Pokemon_GetValue(mon, MON_DATA_MAX_HP, NULL);
            u32 held = Pokemon_GetValue(mon, MON_DATA_HELD_ITEM, NULL);
            const char *sp = Headless_NameOf(kHeadlessSpecies, kHeadlessSpeciesCount, (int)species);
            const char *hi = Headless_NameOf(kHeadlessItems, kHeadlessItemsCount, (int)held);
            OutFmt(&o, "%s{\"species\":\"%s\",\"species_id\":%u,\"level\":%u,\"hp\":%u,\"max_hp\":%u,\"held_item\":\"%s\"}",
              i ? "," : "", sp ? sp : "SPECIES_?", species, level, hp, maxHp, hi ? hi : "ITEM_NONE");
        }
        OutFmt(&o, "]");
    }

    // Requested vars/flags.
    char name[160];
    if (strstr(line, "\"vars\"")) {
        OutFmt(&o, ",\"vars\":{");
        int first = 1;
        for (int i = 0; JsonStrArrayItem(line, "vars", i, name, sizeof(name)); i++) {
            const HeadlessName *v = Headless_Lookup(kHeadlessVars, kHeadlessVarsCount, name);
            long val = -1;
            if (v && fsys) val = FieldSystem_TryGetVar(fsys, (u16)v->id);
            else if (v && save) val = *VarsFlags_GetVarAddress(SaveData_GetVarsFlags(save), (u16)v->id);
            OutFmt(&o, "%s\"%s\":%ld", first ? "" : ",", name, val);
            first = 0;
        }
        OutFmt(&o, "}");
    }
    if (strstr(line, "\"flags\"")) {
        OutFmt(&o, ",\"flags\":{");
        int first = 1;
        for (int i = 0; JsonStrArrayItem(line, "flags", i, name, sizeof(name)); i++) {
            const HeadlessName *f = Headless_Lookup(kHeadlessFlags, kHeadlessFlagsCount, name);
            BOOL val = FALSE;
            if (f && fsys) val = FieldSystem_CheckFlag(fsys, (u16)f->id);
            else if (f && save) val = VarsFlags_CheckFlag(SaveData_GetVarsFlags(save), (u16)f->id);
            OutFmt(&o, "%s\"%s\":%s", first ? "" : ",", name, val ? "true" : "false");
            first = 0;
        }
        OutFmt(&o, "}");
    }
    // Requested bag counts: {"bag":["ITEM_X",...]}
    if (strstr(line, "\"bag\"")) {
        OutFmt(&o, ",\"bag\":{");
        int first = 1;
        Bag *bag = save ? SaveData_GetBag(save) : NULL;
        for (int i = 0; JsonStrArrayItem(line, "bag", i, name, sizeof(name)); i++) {
            const HeadlessName *it = Headless_Lookup(kHeadlessItems, kHeadlessItemsCount, name);
            long qty = (it && bag) ? Bag_GetItemQuantity(bag, (u16)it->id, HEAP_ID_SYSTEM) : -1;
            OutFmt(&o, "%s\"%s\":%ld", first ? "" : ",", name, qty);
            first = 0;
        }
        OutFmt(&o, "}");
    }
    OutFmt(&o, "}");
    return 1;
}
