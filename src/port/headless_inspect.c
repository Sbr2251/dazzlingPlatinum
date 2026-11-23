// Rich read-only diagnostics for the lockstep protocol. // dbg-inspect hook
#include <nitro.h>
#include <nitro/gx/g2_oam.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#include "billboard.h"
#include "bg_window.h"
#include "camera.h"
#include "constants/charcode.h"
#include "field/field_system.h"
#include "field/field_system_sub2_t.h"
#include "field_overworld_state.h"
#include "headless_names.h"
#include "map_header.h"
#include "map_object.h"
#include "particle_system.h"
#include "player_avatar.h"
#include "port/debug_field.h"
#include "port/headless_game.h"
#include "savedata.h"
#include "script_manager.h"
#include "string_gf.h"

#ifdef SDK_PORT
extern unsigned long long SIM_Headless_FrameCount(void);

typedef struct InspectOut {
    char *buf;
    size_t cap;
    size_t len;
} InspectOut;

static void Put(InspectOut *out, const char *fmt, ...)
{
    va_list args;
    int n;
    if (out->cap == 0 || out->len >= out->cap - 1) {
        return;
    }
    va_start(args, fmt);
    n = vsnprintf(out->buf + out->len, out->cap - out->len, fmt, args);
    va_end(args);
    if (n > 0) {
        size_t room = out->cap - out->len;
        out->len += (size_t)n < room ? (size_t)n : room - 1;
    }
}

static BOOL GetString(const char *line, const char *key, char *dst, size_t cap)
{
    char pattern[64];
    const char *p, *end;
    size_t n;
    snprintf(pattern, sizeof(pattern), "\"%s\"", key);
    p = strstr(line, pattern);
    if (p == NULL || (p = strchr(p + strlen(pattern), ':')) == NULL) return FALSE;
    do { p++; } while (*p == ' ' || *p == '\t');
    if (*p++ != '"' || (end = strchr(p, '"')) == NULL) return FALSE;
    n = (size_t)(end - p);
    if (n >= cap) n = cap - 1;
    memcpy(dst, p, n);
    dst[n] = 0;
    return TRUE;
}

static ScriptManager *ActiveScript(FieldSystem *field)
{
    void *env;
    if (field == NULL || field->task == NULL) return NULL;
    env = FieldTask_GetEnv(field->task);
    if (env != NULL && ((ScriptManager *)env)->magic == SCRIPT_MANAGER_MAGIC_NUMBER) return env;
    return NULL;
}

static void PutJsonChar(InspectOut *out, char c)
{
    if (c == '"' || c == '\\') Put(out, "\\%c", c);
    else if (c == '\n') Put(out, "\\n");
    else if ((unsigned char)c >= 0x20) Put(out, "%c", c);
}

static char DecodeChar(charcode_t c)
{
    if (c >= CHAR_0 && c <= CHAR_9) return (char)('0' + c - CHAR_0);
    if (c >= CHAR_A && c <= CHAR_Z) return (char)('A' + c - CHAR_A);
    if (c >= CHAR_a && c <= CHAR_z) return (char)('a' + c - CHAR_a);
    if (c == CHAR_SPACE || c == CHAR_WIDE_SPACE) return ' ';
    if (c == CHAR_CR) return '\n';
    if (c == CHAR_EXCLAMATION) return '!';
    if (c == CHAR_QUESTION) return '?';
    if (c == CHAR_PERIOD) return '.';
    if (c == CHAR_COMMA) return ',';
    if (c == CHAR_SINGLE_QUOTE_OPEN || c == CHAR_SINGLE_QUOTE_CLOSE) return '\'';
    if (c == CHAR_DOUBLE_QUOTE_OPEN || c == CHAR_DOUBLE_QUOTE_CLOSE || c == CHAR_DOUBLE_QUOTE_CLOSE_INVERTED) return '"';
    if (c == CHAR_MINUS) return '-';
    if (c == CHAR_COLON) return ':';
    if (c == CHAR_SLASH) return '/';
    if (c == CHAR_PAREN_OPEN) return '(';
    if (c == CHAR_PAREN_CLOSE) return ')';
    return '?';
}

static void PutString(InspectOut *out, const String *string)
{
    u32 i;
    Put(out, "\"");
    if (string != NULL) {
        for (i = 0; i < string->size && i < 512; i++) {
            charcode_t c = string->data[i];
            if (c == CHAR_EOS) break;
            if (c == CHAR_ELLIPSIS) {
                Put(out, "...");
            } else if (c == 0xFFFE) {
                // Skip string format tag (tag + count + args)
                if (i + 2 < string->size) {
                    u16 argc = string->data[i + 2];
                    i += 2 + argc;
                }
            } else {
                PutJsonChar(out, DecodeChar(c));
            }
        }
    }
    Put(out, "\"");
}

static const char *LocalIdName(int mapHeader, int localId)
{
    for (int i = 0; i < kHeadlessLocalsCount; i++) {
        if (kHeadlessLocals[i].mapHeader == mapHeader && kHeadlessLocals[i].localId == localId) {
            return kHeadlessLocals[i].name;
        }
    }
    return NULL;
}

static void InspectObjects(InspectOut *out, FieldSystem *field)
{
    MapObject *object = NULL;
    int index = 0, count = 0, emitted = 0;
    BOOL truncated = FALSE;
    int header = (field != NULL && field->location != NULL) ? field->location->mapHeaderID : -1;
    Put(out, "{\"objects\":[");
    if (field != NULL && field->mapObjMan != NULL) {
        while (MapObjectMan_FindObjectWithStatus(field->mapObjMan, &object, &index, MAP_OBJ_STATUS_0) == TRUE) {
            count++;
            if (out->cap > out->len + 256) {
                u32 lid = MapObject_GetLocalID(object);
                const char *name = LocalIdName(header, (int)lid);
                Put(out, "%s{\"localid\":%u,\"name\":", emitted ? "," : "", lid);
                if (name != NULL) Put(out, "\"%s\"", name); else Put(out, "null");
                Put(out, ",\"gfx_id\":%u,\"x\":%d,\"y\":%d,\"z\":%d,"
                    "\"dir\":%d,\"visible\":%s,\"moving\":%s,\"script_id\":%u,\"movement_type\":%u}",
                    MapObject_GetEffectiveGraphicsID(object),
                    MapObject_GetX(object), MapObject_GetY(object), MapObject_GetZ(object), MapObject_GetFacingDir(object),
                    MapObject_IsHidden(object) ? "false" : "true", MapObject_IsMoving(object) ? "true" : "false",
                    MapObject_GetScript(object), MapObject_GetMovementType(object));
                emitted++;
            } else {
                truncated = TRUE;
            }
        }
    }
    Put(out, "],\"count\":%d,\"truncated\":%s}", count, truncated ? "true" : "false");
}

static void InspectCamera(InspectOut *out, FieldSystem *field)
{
    if (field == NULL || field->camera == NULL) {
        Put(out, "{\"active\":false}");
        return;
    }
    const Camera *cam = field->camera;
    VecFx32 pos = Camera_GetPosition(cam);
    VecFx32 tgt = Camera_GetTarget(cam);
    CameraAngle ang = Camera_GetAngle(cam);
    const VecFx32 *ppos = field->playerAvatar != NULL ? PlayerAvatar_GetPos(field->playerAvatar) : NULL;
    Put(out, "{\"active\":true,\"position_fx\":[%d,%d,%d],\"target_fx\":[%d,%d,%d],"
        "\"distance\":%d,\"angle\":[%u,%u,%u],\"fov_y\":%u,\"projection\":%u,"
        "\"tracking_target\":%s",
        pos.x, pos.y, pos.z, tgt.x, tgt.y, tgt.z,
        Camera_GetDistance(cam), ang.x, ang.y, ang.z, Camera_GetFOV(cam), (unsigned)cam->projection,
        cam->targetPos != NULL ? "true" : "false");
    if (ppos != NULL) {
        Put(out, ",\"player_pos_fx\":[%d,%d,%d]", ppos->x, ppos->y, ppos->z);
    }
    Put(out, "}");
}

static void InspectBillboards(InspectOut *out)
{
    const BillboardList *lists;
    int listCount = 0, activeLists = 0, total = 0, visible = 0, drawn = 0, emitted = 0;
    lists = BillboardLists_Inspect(&listCount);
    Put(out, "{\"list_count\":%d,\"billboards\":[", listCount);
    for (int i = 0; lists != NULL && i < listCount; i++) {
        const BillboardList *list = &lists[i];
        const Billboard *billboard;
        if (!list->active) continue;
        activeLists++;
        billboard = list->sentinelData.next;
        while (billboard != NULL && billboard != &list->sentinelData) {
            BOOL isVisible = billboard->state != BILLBOARD_STATE_INACTIVE;
            total++;
            if (isVisible) visible++;
            if (billboard->draw) drawn++;
            if (emitted < 32) {
                Put(out, "%s{\"list\":%d,\"pos_fx\":[%d,%d,%d],\"visible\":%s,\"draw\":%s,\"anim\":%u}",
                    emitted ? "," : "", i, billboard->pos.x, billboard->pos.y, billboard->pos.z,
                    isVisible ? "true" : "false", billboard->draw ? "true" : "false", billboard->animNum);
                emitted++;
            }
            billboard = billboard->next;
        }
    }
    Put(out, "],\"active_lists\":%d,\"count\":%d,\"active\":%d,\"visible\":%d,\"drawn\":%d,\"truncated\":%s}",
        activeLists, total, visible, visible, drawn, total > emitted ? "true" : "false");
}

static void InspectText(InspectOut *out, FieldSystem *field)
{
    ScriptManager *script = ActiveScript(field);
    long offset = -1;
    int windows = 0;
    if (script != NULL && script->ctx[SCRIPT_CONTEXT_MAIN] != NULL) {
        ScriptContext *ctx = script->ctx[SCRIPT_CONTEXT_MAIN];
        if (ctx->scripts != NULL && ctx->scriptPtr != NULL) offset = (long)(ctx->scriptPtr - ctx->scripts);
        windows += Window_IsInUse(&script->window) ? 1 : 0;
        windows += Window_IsInUse(&script->specialCurrencyWindow) ? 1 : 0;
        windows += Window_IsInUse(&script->moneyWindow) ? 1 : 0;
    }
    if (field != NULL && field->signpost != NULL && field->signpost->active) windows++;
    Put(out, "{\"message_waiting\":%s,\"signpost_active\":%s,\"script_id\":%d,\"script_offset\":%ld,\"window_count\":%d,\"text\":",
        script && script->isMsgBoxOpen ? "true" : "false",
        field && field->signpost && field->signpost->active ? "true" : "false",
        script ? script->scriptID : -1, offset, windows);
    if (script != NULL && script->msgBuf != NULL) PutString(out, script->msgBuf); else Put(out, "null");
    Put(out, "}");
}

static int CountVisibleOam(const u8 *memory)
{
    const GXOamAttr *attrs = (const GXOamAttr *)memory;
    int count = 0;
    for (int i = 0; i < 128; i++) {
        if ((attrs[i].attr0 & GX_OAM_ATTR01_RSENABLE_MASK) != (u16)GX_OAM_EFFECT_NODISPLAY) count++;
    }
    return count;
}

static void InspectUI(InspectOut *out, FieldSystem *field)
{
    int bgCount = 0;
    int mainMask = GX_GetVisiblePlane();
    int subMask = GXS_GetVisiblePlane();
    if (field != NULL && field->bgConfig != NULL) {
        for (int i = 0; i < BG_LAYER_MAX; i++) if (field->bgConfig->bgs[i].tilemapBuffer != NULL) bgCount++;
    }
    Put(out, "{\"overlay\":%d,\"app\":\"%s\",\"bg_main_mask\":%d,\"bg_sub_mask\":%d,"
        "\"active_bg_layers\":%d,\"oam_main_active\":%d,\"oam_sub_active\":%d}",
        Headless_GetOverlay(), Headless_GetBattleSystem() ? "battle" : field ? "field" : "other",
        mainMask, subMask, bgCount,
        (mainMask & GX_PLANEMASK_OBJ) ? CountVisibleOam((const u8 *)HW_OAM) : 0,
        (subMask & GX_PLANEMASK_OBJ) ? CountVisibleOam((const u8 *)HW_DB_OAM) : 0);
}

static void InspectWeather(InspectOut *out, FieldSystem *field)
{
    int header = field && field->location ? field->location->mapHeaderID : -1;
    int mapWeather = header >= 0 ? MapHeader_GetWeatherType(header) : -1;
    int activeWeather = -1;
    BOOL systemActive = FALSE;
    if (field != NULL && field->saveData != NULL) {
        activeWeather = FieldOverworldState_GetWeather(SaveData_GetFieldOverworldState(field->saveData));
        systemActive = field->unk_04 != NULL && field->unk_04->unk_0C != NULL;
    }
    int particleSystems = ParticleSystem_GetActiveAmount();
    Put(out, "{\"map_header_weather\":%d,\"field_weather\":%d,\"field_system_active\":%s,"
        "\"particle_systems\":%d,\"emitters\":%d}", mapWeather, activeWeather,
        systemActive ? "true" : "false", particleSystems, particleSystems == 0 ? 0 : -1);
}

int HeadlessInspect_Handle(const char *line, char *reply, size_t cap)
{
    char what[32];
    FieldSystem *field;
    InspectOut out = { reply, cap, 0 };
    if (!GetString(line, "what", what, sizeof(what))) {
        snprintf(reply, cap, "{\"ok\":false,\"error\":\"inspect needs what\"}");
        return 1;
    }
    field = DEBUG_GetFieldSystem();
    Put(&out, "{\"ok\":true,\"frame\":%llu,\"what\":\"%s\",\"data\":", SIM_Headless_FrameCount(), what);
    if (!strcmp(what, "objects")) InspectObjects(&out, field);
    else if (!strcmp(what, "billboards")) InspectBillboards(&out);
    else if (!strcmp(what, "text")) InspectText(&out, field);
    else if (!strcmp(what, "ui")) InspectUI(&out, field);
    else if (!strcmp(what, "weather")) InspectWeather(&out, field);
    else if (!strcmp(what, "camera")) InspectCamera(&out, field);
    else {
        snprintf(reply, cap, "{\"ok\":false,\"error\":\"unknown inspect target\"}");
        return 1;
    }
    Put(&out, "}");
    return 1;
}
#else
int HeadlessInspect_Handle(const char *line, char *reply, size_t cap)
{
    (void)line; (void)reply; (void)cap;
    return 0;
}
#endif
