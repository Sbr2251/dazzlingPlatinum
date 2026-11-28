#include "battle/battle_bdsp_cam.h"

#include <ctype.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "constants/battle.h"

#include "battle/battle_hud.h"
#include "battle/battle_system.h"

extern void BattleStageCamera_GetBdspDeltas(float *yawDeg, float *pitchDeg, float *distScale, float *fovScale, float *shakeX, float *shakeY, int *isIdle);

#ifdef SDK_PORT
extern const char *SIM_Platform_WritableDir(void) __attribute__((weak));
extern const char *SIM_Platform_DataDir(void) __attribute__((weak));
#endif

#define BDSP_CAM_DT              (1.0f / 60.0f)
#define BDSP_CAM_MAX_KEYS        32
#define BDSP_CAM_MAX_FILE_BYTES  (256u * 1024u)
#define BDSP_CAM_MIN_EYE_Y       0.85f
#define BDSP_CAM_MIN_FOV         22.0f
#define BDSP_CAM_MAX_FOV         52.0f
#define BDSP_CAM_MAX_RADIUS_XZ   9.25f

enum BdspCamClipId {
    CAM_CLIP_INTRO_WILD = 0,
    CAM_CLIP_THROW_CUT,
    CAM_CLIP_WAIT_IDLE_0,
    CAM_CLIP_WAIT_IDLE_1,
    CAM_CLIP_WAIT_IDLE_2,
    CAM_CLIP_ATTACK_PLAYER,
    CAM_CLIP_ATTACK_ENEMY,
    CAM_CLIP_HIT_PLAYER,
    CAM_CLIP_HIT_ENEMY,
    CAM_CLIP_FAINT_CUT,
    CAM_CLIP_COUNT
};

static const char *const sClipNames[CAM_CLIP_COUNT] = {
    "intro_wild",
    "throw_cut",
    "wait_idle_0",
    "wait_idle_1",
    "wait_idle_2",
    "attack_player",
    "attack_enemy",
    "hit_player",
    "hit_enemy",
    "faint_cut",
};

enum BdspCamMode {
    CAM_MODE_UNINIT = 0,
    CAM_MODE_INTRO,
    CAM_MODE_THROW,
    CAM_MODE_IDLE,
    CAM_MODE_ATTACK,
    CAM_MODE_HIT,
    CAM_MODE_FAINT,
    CAM_MODE_RETURN_HOME
};

typedef struct BdspCamPose {
    float eye[3];
    float target[3];
    float fov;
} BdspCamPose;

typedef struct BdspCamKey {
    float t;
    float eye[3];
    float target[3];
    float fov;
} BdspCamKey;

typedef struct BdspCamClip {
    BOOL loaded;
    BOOL loop;
    float duration;
    int numKeys;
    BdspCamKey keys[BDSP_CAM_MAX_KEYS];
} BdspCamClip;

typedef struct BdspCamBank {
    BOOL attempted;
    BOOL loadedFromJson;
    BdspCamPose home;
    BdspCamClip clips[CAM_CLIP_COUNT];
} BdspCamBank;

typedef struct BdspCamState {
    int mode;
    int activeClip;
    float clipTime;
    int idleCycleIdx;
    int idlePassDir; // +1 forward, -1 reverse for smooth ping-pong
    BOOL isTrainerBattle;
    BOOL playerSeenVisible;
    BOOL throwTriggered;
    BOOL pendingAttack;
    int pendingAttacker;
    u16 pendingMove;
    BOOL pendingHit;
    int pendingDefender;
    BOOL pendingFaint;
    int pendingFaintBattler;
    BOOL faintIsPlayer;
    BOOL hasLastPose;
    BdspCamPose lastPose;
    BdspCamPose blendFrom;
    float blendTime;
    float blendDur;
    u32 frameCount;
} BdspCamState;

static BdspCamBank sBank;
static BdspCamState sCam;

static float Clampf(float v, float lo, float hi)
{
    if (v < lo) {
        return lo;
    }
    if (v > hi) {
        return hi;
    }
    return v;
}

static float Smoothstep01(float u)
{
    u = Clampf(u, 0.0f, 1.0f);
    return u * u * (3.0f - 2.0f * u);
}

static void LerpPose(const BdspCamPose *a, const BdspCamPose *b, float u, BdspCamPose *out)
{
    float s = Smoothstep01(u);
    float inv = 1.0f - s;
    int i;

    for (i = 0; i < 3; i++) {
        out->eye[i] = a->eye[i] * inv + b->eye[i] * s;
        out->target[i] = a->target[i] * inv + b->target[i] * s;
    }
    out->fov = a->fov * inv + b->fov * s;
}

static void ClampPose(BdspCamPose *p)
{
    int i;
    float r;

    for (i = 0; i < 3; i++) {
        if (!isfinite(p->eye[i]) || !isfinite(p->target[i])) {
            *p = sBank.home;
            return;
        }
    }
    if (!isfinite(p->fov)) {
        p->fov = sBank.home.fov;
    }

    r = sqrtf(p->eye[0] * p->eye[0] + p->eye[2] * p->eye[2]);
    if (r > BDSP_CAM_MAX_RADIUS_XZ && r > 0.001f) {
        float scale = BDSP_CAM_MAX_RADIUS_XZ / r;
        p->eye[0] *= scale;
        p->eye[2] *= scale;
    }

    if (p->eye[1] < BDSP_CAM_MIN_EYE_Y) {
        p->eye[1] = BDSP_CAM_MIN_EYE_Y;
    }

    p->fov = Clampf(p->fov, BDSP_CAM_MIN_FOV, BDSP_CAM_MAX_FOV);
}

static void SetKey(BdspCamClip *c, int idx, float t, float ex, float ey, float ez, float tx, float ty, float tz, float fov)
{
    if (idx < 0 || idx >= BDSP_CAM_MAX_KEYS) {
        return;
    }
    c->keys[idx].t = t;
    c->keys[idx].eye[0] = ex;
    c->keys[idx].eye[1] = ey;
    c->keys[idx].eye[2] = ez;
    c->keys[idx].target[0] = tx;
    c->keys[idx].target[1] = ty;
    c->keys[idx].target[2] = tz;
    c->keys[idx].fov = fov;
    if (idx + 1 > c->numKeys) {
        c->numKeys = idx + 1;
    }
}

// Built-in clean procedural fallback clips used only when battle_cameras.json is absent.
static void PopulateFallbackBank(void)
{
    BdspCamClip *c;

    memset(&sBank.clips, 0, sizeof(sBank.clips));
    sBank.home.eye[0] = -3.60f;
    sBank.home.eye[1] = 2.55f;
    sBank.home.eye[2] = 8.80f;
    sBank.home.target[0] = 0.60f;
    sBank.home.target[1] = 1.45f;
    sBank.home.target[2] = -2.00f;
    sBank.home.fov = 38.0f;

    // intro_wild
    c = &sBank.clips[CAM_CLIP_INTRO_WILD];
    c->loaded = TRUE;
    c->loop = FALSE;
    c->duration = 3.2f;
    SetKey(c, 0, 0.00f, -5.10f, 3.35f, 5.20f, 1.65f, 1.15f, -1.65f, 32.0f);
    SetKey(c, 1, 1.25f, -0.95f, 1.72f, 1.85f, 2.30f, 1.02f, -2.12f, 30.0f);
    SetKey(c, 2, 1.95f, 0.45f, 1.68f, 2.55f, 2.32f, 1.02f, -2.12f, 32.5f);
    SetKey(c, 3, 3.20f, -3.60f, 2.55f, 8.80f, 0.60f, 1.45f, -2.00f, 38.0f);

    // throw_cut
    c = &sBank.clips[CAM_CLIP_THROW_CUT];
    c->loaded = TRUE;
    c->loop = FALSE;
    c->duration = 1.8f;
    SetKey(c, 0, 0.00f, -3.85f, 1.62f, 5.55f, -1.35f, 1.32f, 1.35f, 33.0f);
    SetKey(c, 1, 0.45f, -4.55f, 1.82f, 4.95f, -0.85f, 1.48f, 0.55f, 34.5f);
    SetKey(c, 2, 1.10f, -4.10f, 2.25f, 7.20f, -0.10f, 1.42f, -1.10f, 37.0f);
    SetKey(c, 3, 1.80f, -3.60f, 2.55f, 8.80f, 0.60f, 1.45f, -2.00f, 38.0f);

    // wait_idle_0
    c = &sBank.clips[CAM_CLIP_WAIT_IDLE_0];
    c->loaded = TRUE;
    c->loop = TRUE;
    c->duration = 5.0f;
    SetKey(c, 0, 0.00f, -4.15f, 2.53f, 8.20f, 0.72f, 1.45f, -2.06f, 36.8f);
    SetKey(c, 1, 2.50f, -3.55f, 2.53f, 8.48f, 0.60f, 1.45f, -2.00f, 38.0f);
    SetKey(c, 2, 5.00f, -2.95f, 2.53f, 8.68f, 0.45f, 1.45f, -1.94f, 39.0f);

    // wait_idle_1
    c = &sBank.clips[CAM_CLIP_WAIT_IDLE_1];
    c->loaded = TRUE;
    c->loop = TRUE;
    c->duration = 5.0f;
    SetKey(c, 0, 0.00f, -4.80f, 2.08f, 7.45f, 0.55f, 1.38f, -1.90f, 36.5f);
    SetKey(c, 1, 2.50f, -4.35f, 2.08f, 7.95f, 0.45f, 1.38f, -1.90f, 36.5f);
    SetKey(c, 2, 5.00f, -3.85f, 2.08f, 8.35f, 0.35f, 1.38f, -1.90f, 36.5f);

    // wait_idle_2
    c = &sBank.clips[CAM_CLIP_WAIT_IDLE_2];
    c->loaded = TRUE;
    c->loop = TRUE;
    c->duration = 5.0f;
    SetKey(c, 0, 0.00f, -4.15f, 2.38f, 7.80f, 0.65f, 1.36f, -1.85f, 36.2f);
    SetKey(c, 1, 2.50f, -3.45f, 2.75f, 8.35f, 0.50f, 1.38f, -1.95f, 37.5f);
    SetKey(c, 2, 5.00f, -2.65f, 3.25f, 8.60f, 0.35f, 1.42f, -2.00f, 39.2f);

    // attack_player
    c = &sBank.clips[CAM_CLIP_ATTACK_PLAYER];
    c->loaded = TRUE;
    c->loop = FALSE;
    c->duration = 1.2f;
    SetKey(c, 0, 0.00f, -4.25f, 1.88f, 6.15f, -1.15f, 1.35f, 1.15f, 32.0f);
    SetKey(c, 1, 0.38f, -3.45f, 1.72f, 5.35f, -0.45f, 1.35f, 0.35f, 29.5f);
    SetKey(c, 2, 0.82f, -1.45f, 2.02f, 4.15f, 1.85f, 1.15f, -1.80f, 33.0f);
    SetKey(c, 3, 1.20f, -2.20f, 2.22f, 5.80f, 1.30f, 1.25f, -1.90f, 35.5f);

    // attack_enemy
    c = &sBank.clips[CAM_CLIP_ATTACK_ENEMY];
    c->loaded = TRUE;
    c->loop = FALSE;
    c->duration = 1.2f;
    SetKey(c, 0, 0.00f, -0.55f, 1.92f, 2.75f, 2.12f, 1.10f, -1.95f, 31.0f);
    SetKey(c, 1, 0.42f, -0.05f, 1.76f, 2.05f, 2.28f, 1.05f, -2.10f, 28.5f);
    SetKey(c, 2, 0.85f, -4.45f, 2.18f, 7.05f, -0.80f, 1.30f, 0.65f, 34.8f);
    SetKey(c, 3, 1.20f, -3.90f, 2.40f, 8.05f, 0.10f, 1.38f, -1.10f, 37.0f);

    // hit_player
    c = &sBank.clips[CAM_CLIP_HIT_PLAYER];
    c->loaded = TRUE;
    c->loop = FALSE;
    c->duration = 0.75f;
    SetKey(c, 0, 0.00f, -4.70f, 1.90f, 6.35f, -1.72f, 1.25f, 1.82f, 30.0f);
    SetKey(c, 1, 0.18f, -5.00f, 2.04f, 6.75f, -1.56f, 1.34f, 1.72f, 32.5f);
    SetKey(c, 2, 0.48f, -4.38f, 2.26f, 7.60f, -0.82f, 1.36f, 0.45f, 35.2f);
    SetKey(c, 3, 0.75f, -3.90f, 2.45f, 8.30f, 0.05f, 1.40f, -1.05f, 37.0f);

    // hit_enemy
    c = &sBank.clips[CAM_CLIP_HIT_ENEMY];
    c->loaded = TRUE;
    c->loop = FALSE;
    c->duration = 0.75f;
    SetKey(c, 0, 0.00f, -0.40f, 1.74f, 2.40f, 2.30f, 1.05f, -2.10f, 28.5f);
    SetKey(c, 1, 0.18f, -0.72f, 1.88f, 2.90f, 2.18f, 1.14f, -2.02f, 31.2f);
    SetKey(c, 2, 0.48f, -1.65f, 2.12f, 4.85f, 1.72f, 1.22f, -2.00f, 34.2f);
    SetKey(c, 3, 0.75f, -2.65f, 2.36f, 6.85f, 1.10f, 1.35f, -2.00f, 36.5f);

    // faint_cut
    c = &sBank.clips[CAM_CLIP_FAINT_CUT];
    c->loaded = TRUE;
    c->loop = FALSE;
    c->duration = 1.4f;
    SetKey(c, 0, 0.00f, -0.25f, 1.45f, 2.50f, 2.30f, 0.95f, -2.10f, 30.0f);
    SetKey(c, 1, 0.55f, -0.95f, 2.15f, 4.10f, 2.15f, 0.72f, -2.10f, 32.5f);
    SetKey(c, 2, 1.05f, -2.10f, 2.55f, 6.20f, 1.45f, 0.95f, -2.05f, 35.5f);
    SetKey(c, 3, 1.40f, -3.05f, 2.68f, 7.80f, 0.85f, 1.30f, -2.00f, 37.2f);
}

// --- Minimal, zero-dependency, allocation-free JSON scanner for battle_cameras.json ---

typedef struct JsonCursor {
    const char *p;
    const char *end;
} JsonCursor;

static void JsonSkipWs(JsonCursor *c)
{
    while (c->p < c->end && (*c->p == ' ' || *c->p == '\t' || *c->p == '\r' || *c->p == '\n')) {
        c->p++;
    }
}

static BOOL JsonConsumeChar(JsonCursor *c, char ch)
{
    JsonSkipWs(c);
    if (c->p < c->end && *c->p == ch) {
        c->p++;
        return TRUE;
    }
    return FALSE;
}

static BOOL JsonParseString(JsonCursor *c, char *buf, size_t bufSize)
{
    size_t len = 0;

    JsonSkipWs(c);
    if (c->p >= c->end || *c->p != '"') {
        return FALSE;
    }
    c->p++;

    while (c->p < c->end && *c->p != '"') {
        char ch = *c->p++;
        if (ch == '\\' && c->p < c->end) {
            ch = *c->p++;
        }
        if (buf != NULL && len + 1 < bufSize) {
            buf[len++] = ch;
        }
    }
    if (c->p >= c->end || *c->p != '"') {
        return FALSE;
    }
    c->p++;
    if (buf != NULL && bufSize > 0) {
        buf[len] = '\0';
    }
    return TRUE;
}

static BOOL JsonParseFloat(JsonCursor *c, float *out)
{
    char *next = NULL;
    float val;

    JsonSkipWs(c);
    if (c->p >= c->end) {
        return FALSE;
    }
    val = strtof(c->p, &next);
    if (next == c->p) {
        return FALSE;
    }
    c->p = next;
    *out = val;
    return TRUE;
}

static BOOL JsonParseBool(JsonCursor *c, BOOL *out)
{
    JsonSkipWs(c);
    if (c->end - c->p >= 4 && memcmp(c->p, "true", 4) == 0) {
        c->p += 4;
        *out = TRUE;
        return TRUE;
    }
    if (c->end - c->p >= 5 && memcmp(c->p, "false", 5) == 0) {
        c->p += 5;
        *out = FALSE;
        return TRUE;
    }
    return FALSE;
}

static BOOL JsonParseVec3(JsonCursor *c, float out[3])
{
    if (!JsonConsumeChar(c, '[')) {
        return FALSE;
    }
    if (!JsonParseFloat(c, &out[0]) || !JsonConsumeChar(c, ',')
        || !JsonParseFloat(c, &out[1]) || !JsonConsumeChar(c, ',')
        || !JsonParseFloat(c, &out[2]) || !JsonConsumeChar(c, ']')) {
        return FALSE;
    }
    return TRUE;
}

static BOOL JsonSkipValue(JsonCursor *c)
{
    JsonSkipWs(c);
    if (c->p >= c->end) {
        return FALSE;
    }

    if (*c->p == '"') {
        return JsonParseString(c, NULL, 0);
    }
    if (*c->p == '{') {
        c->p++;
        if (JsonConsumeChar(c, '}')) {
            return TRUE;
        }
        while (c->p < c->end) {
            if (!JsonParseString(c, NULL, 0) || !JsonConsumeChar(c, ':') || !JsonSkipValue(c)) {
                return FALSE;
            }
            if (JsonConsumeChar(c, ',')) {
                continue;
            }
            return JsonConsumeChar(c, '}');
        }
        return FALSE;
    }
    if (*c->p == '[') {
        c->p++;
        if (JsonConsumeChar(c, ']')) {
            return TRUE;
        }
        while (c->p < c->end) {
            if (!JsonSkipValue(c)) {
                return FALSE;
            }
            if (JsonConsumeChar(c, ',')) {
                continue;
            }
            return JsonConsumeChar(c, ']');
        }
        return FALSE;
    }

    // Number, boolean, or null literal
    while (c->p < c->end && *c->p != ',' && *c->p != '}' && *c->p != ']'
        && *c->p != ' ' && *c->p != '\t' && *c->p != '\r' && *c->p != '\n') {
        c->p++;
    }
    return TRUE;
}

static BOOL JsonParsePoseObj(JsonCursor *c, BdspCamPose *pose)
{
    char key[32];

    if (!JsonConsumeChar(c, '{')) {
        return FALSE;
    }
    if (JsonConsumeChar(c, '}')) {
        return TRUE;
    }
    while (c->p < c->end) {
        if (!JsonParseString(c, key, sizeof(key)) || !JsonConsumeChar(c, ':')) {
            return FALSE;
        }
        if (strcmp(key, "eye") == 0) {
            if (!JsonParseVec3(c, pose->eye)) {
                return FALSE;
            }
        } else if (strcmp(key, "target") == 0) {
            if (!JsonParseVec3(c, pose->target)) {
                return FALSE;
            }
        } else if (strcmp(key, "fov") == 0) {
            if (!JsonParseFloat(c, &pose->fov)) {
                return FALSE;
            }
        } else {
            if (!JsonSkipValue(c)) {
                return FALSE;
            }
        }
        if (JsonConsumeChar(c, ',')) {
            continue;
        }
        return JsonConsumeChar(c, '}');
    }
    return FALSE;
}

static BOOL JsonParseKeyObj(JsonCursor *c, BdspCamKey *out)
{
    char key[32];

    memset(out, 0, sizeof(*out));
    out->fov = 38.0f;

    if (!JsonConsumeChar(c, '{')) {
        return FALSE;
    }
    if (JsonConsumeChar(c, '}')) {
        return TRUE;
    }
    while (c->p < c->end) {
        if (!JsonParseString(c, key, sizeof(key)) || !JsonConsumeChar(c, ':')) {
            return FALSE;
        }
        if (strcmp(key, "t") == 0) {
            if (!JsonParseFloat(c, &out->t)) {
                return FALSE;
            }
        } else if (strcmp(key, "eye") == 0) {
            if (!JsonParseVec3(c, out->eye)) {
                return FALSE;
            }
        } else if (strcmp(key, "target") == 0) {
            if (!JsonParseVec3(c, out->target)) {
                return FALSE;
            }
        } else if (strcmp(key, "fov") == 0) {
            if (!JsonParseFloat(c, &out->fov)) {
                return FALSE;
            }
        } else {
            if (!JsonSkipValue(c)) {
                return FALSE;
            }
        }
        if (JsonConsumeChar(c, ',')) {
            continue;
        }
        return JsonConsumeChar(c, '}');
    }
    return FALSE;
}

static BOOL JsonParseClipObj(JsonCursor *c, BdspCamClip *clip)
{
    char key[32];
    BdspCamClip parsed;

    memset(&parsed, 0, sizeof(parsed));
    if (!JsonConsumeChar(c, '{')) {
        return FALSE;
    }
    if (JsonConsumeChar(c, '}')) {
        return TRUE;
    }
    while (c->p < c->end) {
        if (!JsonParseString(c, key, sizeof(key)) || !JsonConsumeChar(c, ':')) {
            return FALSE;
        }
        if (strcmp(key, "duration") == 0) {
            if (!JsonParseFloat(c, &parsed.duration)) {
                return FALSE;
            }
        } else if (strcmp(key, "loop") == 0) {
            if (!JsonParseBool(c, &parsed.loop)) {
                return FALSE;
            }
        } else if (strcmp(key, "keys") == 0) {
            if (!JsonConsumeChar(c, '[')) {
                return FALSE;
            }
            if (!JsonConsumeChar(c, ']')) {
                while (c->p < c->end) {
                    BdspCamKey k;
                    if (!JsonParseKeyObj(c, &k)) {
                        return FALSE;
                    }
                    if (parsed.numKeys < BDSP_CAM_MAX_KEYS) {
                        parsed.keys[parsed.numKeys++] = k;
                    }
                    if (JsonConsumeChar(c, ',')) {
                        continue;
                    }
                    if (!JsonConsumeChar(c, ']')) {
                        return FALSE;
                    }
                    break;
                }
            }
        } else {
            if (!JsonSkipValue(c)) {
                return FALSE;
            }
        }
        if (JsonConsumeChar(c, ',')) {
            continue;
        }
        if (!JsonConsumeChar(c, '}')) {
            return FALSE;
        }
        break;
    }

    if (parsed.numKeys >= 2 && parsed.duration > 0.05f) {
        parsed.loaded = TRUE;
        *clip = parsed;
    }
    return TRUE;
}

static int FindClipIdByName(const char *name)
{
    int i;

    for (i = 0; i < CAM_CLIP_COUNT; i++) {
        if (strcmp(name, sClipNames[i]) == 0) {
            return i;
        }
    }
    return -1;
}

static BOOL ParseCameraBankJson(const char *data, size_t size)
{
    JsonCursor cur;
    char key[48];
    int parsedCount = 0;

    cur.p = data;
    cur.end = data + size;

    if (!JsonConsumeChar(&cur, '{')) {
        return FALSE;
    }
    if (JsonConsumeChar(&cur, '}')) {
        return FALSE;
    }

    while (cur.p < cur.end) {
        if (!JsonParseString(&cur, key, sizeof(key)) || !JsonConsumeChar(&cur, ':')) {
            return FALSE;
        }
        if (strcmp(key, "home") == 0) {
            if (!JsonParsePoseObj(&cur, &sBank.home)) {
                return FALSE;
            }
            ClampPose(&sBank.home);
        } else if (strcmp(key, "clips") == 0) {
            char cname[48];
            if (!JsonConsumeChar(&cur, '{')) {
                return FALSE;
            }
            if (!JsonConsumeChar(&cur, '}')) {
                while (cur.p < cur.end) {
                    int cid;
                    if (!JsonParseString(&cur, cname, sizeof(cname)) || !JsonConsumeChar(&cur, ':')) {
                        return FALSE;
                    }
                    cid = FindClipIdByName(cname);
                    if (cid >= 0) {
                        if (!JsonParseClipObj(&cur, &sBank.clips[cid])) {
                            return FALSE;
                        }
                        if (sBank.clips[cid].loaded) {
                            parsedCount++;
                        }
                    } else {
                        if (!JsonSkipValue(&cur)) {
                            return FALSE;
                        }
                    }
                    if (JsonConsumeChar(&cur, ',')) {
                        continue;
                    }
                    if (!JsonConsumeChar(&cur, '}')) {
                        return FALSE;
                    }
                    break;
                }
            }
        } else {
            if (!JsonSkipValue(&cur)) {
                return FALSE;
            }
        }

        if (JsonConsumeChar(&cur, ',')) {
            continue;
        }
        if (!JsonConsumeChar(&cur, '}')) {
            return FALSE;
        }
        break;
    }

    return parsedCount > 0;
}

static BOOL TryLoadJsonFile(const char *path)
{
    FILE *fp;
    long sz;
    char *buf;
    size_t nread;
    BOOL ok;

    if (path == NULL || path[0] == '\0') {
        return FALSE;
    }

    fp = fopen(path, "rb");
    if (fp == NULL) {
        return FALSE;
    }

    if (fseek(fp, 0, SEEK_END) != 0) {
        fclose(fp);
        return FALSE;
    }
    sz = ftell(fp);
    if (sz <= 2 || (unsigned long)sz > BDSP_CAM_MAX_FILE_BYTES) {
        fclose(fp);
        return FALSE;
    }
    rewind(fp);

    buf = (char *)malloc((size_t)sz + 1u);
    if (buf == NULL) {
        fclose(fp);
        return FALSE;
    }

    nread = fread(buf, 1, (size_t)sz, fp);
    fclose(fp);
    buf[nread] = '\0';

    ok = ParseCameraBankJson(buf, nread);
    free(buf);
    return ok;
}

static void ExpandTildePath(const char *src, char *dst, size_t dstSize)
{
    if (src == NULL || src[0] == '\0' || dstSize == 0) {
        if (dstSize > 0) {
            dst[0] = '\0';
        }
        return;
    }

    if (src[0] == '~' && (src[1] == '/' || src[1] == '\0')) {
        const char *home = getenv("HOME");
        if (home != NULL && home[0] != '\0') {
            snprintf(dst, dstSize, "%s%s", home, src + 1);
            return;
        }
    }
    snprintf(dst, dstSize, "%s", src);
}

static void EnsureCameraBankLoaded(void)
{
    char base[512];
    char path[640];
    const char *envDir;

    if (sBank.attempted) {
        return;
    }
    sBank.attempted = TRUE;
    PopulateFallbackBank();

#ifdef SDK_PORT
    // 1. SIM_BDSP_ASSETS_DIR/cameras/battle_cameras.json
    envDir = getenv("SIM_BDSP_ASSETS_DIR");
    if (envDir != NULL && envDir[0] != '\0') {
        ExpandTildePath(envDir, base, sizeof(base));
        snprintf(path, sizeof(path), "%s/cameras/battle_cameras.json", base);
        if (TryLoadJsonFile(path)) {
            sBank.loadedFromJson = TRUE;
            return;
        }
    }

    // 2. <WritableDir>/bdsp_assets/cameras/battle_cameras.json
    if (SIM_Platform_WritableDir != NULL) {
        const char *wdir = SIM_Platform_WritableDir();
        if (wdir != NULL && wdir[0] != '\0') {
            snprintf(path, sizeof(path), "%s/bdsp_assets/cameras/battle_cameras.json", wdir);
            if (TryLoadJsonFile(path)) {
                sBank.loadedFromJson = TRUE;
                return;
            }
        }
    }

    // 3. <DataDir>/bdsp_assets/cameras/battle_cameras.json
    if (SIM_Platform_DataDir != NULL) {
        const char *ddir = SIM_Platform_DataDir();
        if (ddir != NULL && ddir[0] != '\0') {
            snprintf(path, sizeof(path), "%s/bdsp_assets/cameras/battle_cameras.json", ddir);
            if (TryLoadJsonFile(path)) {
                sBank.loadedFromJson = TRUE;
                return;
            }
        }
    }
#else
    (void)base;
    (void)path;
    (void)envDir;
#endif
}

static void SampleClip(int clipId, float t, BdspCamPose *out)
{
    const BdspCamClip *c;
    int i;

    if (clipId < 0 || clipId >= CAM_CLIP_COUNT || !sBank.clips[clipId].loaded || sBank.clips[clipId].numKeys <= 0) {
        *out = sBank.home;
        return;
    }

    c = &sBank.clips[clipId];
    if (c->numKeys == 1 || t <= c->keys[0].t) {
        memcpy(out->eye, c->keys[0].eye, sizeof(out->eye));
        memcpy(out->target, c->keys[0].target, sizeof(out->target));
        out->fov = c->keys[0].fov;
        return;
    }
    if (t >= c->keys[c->numKeys - 1].t) {
        const BdspCamKey *last = &c->keys[c->numKeys - 1];
        memcpy(out->eye, last->eye, sizeof(out->eye));
        memcpy(out->target, last->target, sizeof(out->target));
        out->fov = last->fov;
        return;
    }

    for (i = 0; i < c->numKeys - 1; i++) {
        const BdspCamKey *k0 = &c->keys[i];
        const BdspCamKey *k1 = &c->keys[i + 1];
        if (t >= k0->t && t <= k1->t) {
            float dt = k1->t - k0->t;
            float u = (dt > 0.0001f) ? (t - k0->t) / dt : 0.0f;
            BdspCamPose p0, p1;
            memcpy(p0.eye, k0->eye, sizeof(p0.eye));
            memcpy(p0.target, k0->target, sizeof(p0.target));
            p0.fov = k0->fov;
            memcpy(p1.eye, k1->eye, sizeof(p1.eye));
            memcpy(p1.target, k1->target, sizeof(p1.target));
            p1.fov = k1->fov;
            LerpPose(&p0, &p1, u, out);
            return;
        }
    }

    *out = sBank.home;
}

static BOOL IsPlayerBattler(BattleSystem *battleSys, int battler)
{
    int btype;

    if (battleSys == NULL || battler < 0 || battler >= SIM_BATTLE3D_MAX_BATTLERS) {
        return (battler == 0);
    }

    btype = BattleSystem_GetBattlerType(battleSys, battler);
    return btype == BATTLER_TYPE_SOLO_PLAYER
        || btype == BATTLER_TYPE_PLAYER_SIDE_SLOT_1
        || btype == BATTLER_TYPE_PLAYER_SIDE_SLOT_2;
}

static void StartBlend(float duration)
{
    if (sCam.hasLastPose) {
        sCam.blendFrom = sCam.lastPose;
    } else {
        sCam.blendFrom = sBank.home;
    }
    sCam.blendTime = 0.0f;
    sCam.blendDur = duration;
}

static void TransitionToMode(int mode, int clipId, float blendDur)
{
    StartBlend(blendDur);
    sCam.mode = mode;
    sCam.activeClip = clipId;
    sCam.clipTime = 0.0f;
}

void BattleBdspCam_Reset(void)
{
    memset(&sCam, 0, sizeof(sCam));
    sCam.mode = CAM_MODE_UNINIT;
    sCam.activeClip = CAM_CLIP_WAIT_IDLE_0;
    sCam.idlePassDir = 1;
}

void BattleBdspCam_NotifyIntroStart(BOOL isTrainerBattle)
{
    EnsureCameraBankLoaded();
    sCam.isTrainerBattle = isTrainerBattle;
    sCam.mode = CAM_MODE_INTRO;
    sCam.activeClip = CAM_CLIP_INTRO_WILD;
    sCam.clipTime = 0.0f;
    sCam.blendTime = 0.0f;
    sCam.blendDur = 0.0f;
    sCam.hasLastPose = FALSE;
}

void BattleBdspCam_NotifyTrainerThrow(void)
{
    EnsureCameraBankLoaded();
    sCam.throwTriggered = TRUE;
    TransitionToMode(CAM_MODE_THROW, CAM_CLIP_THROW_CUT, 0.22f);
}

void BattleBdspCam_NotifyAttack(int attacker, u16 move)
{
    sCam.pendingAttack = TRUE;
    sCam.pendingAttacker = attacker;
    sCam.pendingMove = move;
}

void BattleBdspCam_NotifyHit(int defender)
{
    sCam.pendingHit = TRUE;
    sCam.pendingDefender = defender;
    sCam.pendingAttack = FALSE;
}

void BattleBdspCam_NotifyFaint(int battler)
{
    sCam.pendingFaint = TRUE;
    sCam.pendingFaintBattler = battler;
    sCam.pendingHit = FALSE;
    sCam.pendingAttack = FALSE;
}

// Trainer-safe establishing intro sweep into home framing (avoids zooming onto an empty
// wild-mon spot before the opposing trainer sends out their Pokemon).
static void SampleTrainerIntroPose(float t, BdspCamPose *out)
{
    BdspCamPose pStart;
    float u = Clampf(t / 2.40f, 0.0f, 1.0f);

    pStart.eye[0] = -4.45f;
    pStart.eye[1] = 2.75f;
    pStart.eye[2] = 7.20f;
    pStart.target[0] = 0.40f;
    pStart.target[1] = 1.45f;
    pStart.target[2] = -1.60f;
    pStart.fov = 35.0f;

    LerpPose(&pStart, &sBank.home, u, out);
}

// Mirror enemy-anchored faint pose onto the player battler (-2.15, 0, 2.25) when player faints.
static void AdaptFaintPoseForPlayer(BdspCamPose *p)
{
    float u = Clampf(sCam.clipTime / 1.4f, 0.0f, 1.0f);
    BdspCamPose pStart, pEnd;

    pStart.eye[0] = -4.65f;
    pStart.eye[1] = 1.55f;
    pStart.eye[2] = 5.95f;
    pStart.target[0] = -2.05f;
    pStart.target[1] = 0.95f;
    pStart.target[2] = 2.10f;
    pStart.fov = 30.5f;

    pEnd.eye[0] = -3.75f;
    pEnd.eye[1] = 2.68f;
    pEnd.eye[2] = 8.40f;
    pEnd.target[0] = -0.20f;
    pEnd.target[1] = 1.30f;
    pEnd.target[2] = -0.80f;
    pEnd.fov = 37.2f;

    LerpPose(&pStart, &pEnd, u, p);
}

static void MaybeDumpCamera(const BdspCamPose *pose)
{
#ifdef SDK_PORT
    static FILE *sDumpFp = NULL;
    static BOOL sDumpChecked = FALSE;

    if (!sDumpChecked) {
        const char *path = getenv("SIM_BDSP_CAM_DUMP");
        sDumpChecked = TRUE;
        if (path != NULL && path[0] != '\0') {
            sDumpFp = fopen(path, "w");
        }
    }
    if (sDumpFp != NULL && (sCam.frameCount % 5u == 0u || sCam.clipTime < 0.02f)) {
        fprintf(sDumpFp,
            "frame=%u mode=%d clip=%s t=%.3f eye=(%.3f,%.3f,%.3f) trg=(%.3f,%.3f,%.3f) fov=%.2f json=%d\n",
            (unsigned)sCam.frameCount,
            sCam.mode,
            (sCam.activeClip >= 0 && sCam.activeClip < CAM_CLIP_COUNT) ? sClipNames[sCam.activeClip] : "none",
            sCam.clipTime,
            pose->eye[0], pose->eye[1], pose->eye[2],
            pose->target[0], pose->target[1], pose->target[2],
            pose->fov,
            sBank.loadedFromJson ? 1 : 0);
        fflush(sDumpFp);
    }
#else
    (void)pose;
#endif
}

void BattleBdspCam_Update(BattleSystem *battleSys, SIM_Battle3DFrame *frame)
{
    BdspCamPose rawPose;
    BdspCamPose outPose;
    BOOL playerVisible = FALSE;
    BOOL anyVisible = FALSE;
    BOOL menuVisible;
    float shakeX = 0.0f;
    float shakeY = 0.0f;
    float dummyYaw = 0.0f;
    float dummyPitch = 0.0f;
    float dummyDist = 1.0f;
    float dummyFov = 1.0f;
    int dummyIdle = 1;
    int i;

    if (battleSys == NULL || frame == NULL) {
        return;
    }

    // Gate strictly on BDSP 3D models mode so legacy/models-off goldens remain 100% byte-identical.
    if (!SIM_Battle3D_ModelsEnabled()) {
        return;
    }

    EnsureCameraBankLoaded();

    // Respect BattleStage suppression during legacy DS move animations (alpha <= 0.5f).
    if (frame->alpha <= 0.5f) {
        sCam.frameCount++;
        return;
    }

    // Auto-start intro choreography on the first active battle frame after Reset().
    if (sCam.mode == CAM_MODE_UNINIT) {
        BOOL isTrainer = (BattleSystem_GetBattleType(battleSys) & BATTLE_TYPE_TRAINER) != 0;
        BattleBdspCam_NotifyIntroStart(isTrainer);
    }

    for (i = 0; i < SIM_BATTLE3D_MAX_BATTLERS; i++) {
        if (frame->battlers[i].visible) {
            anyVisible = TRUE;
            if (frame->battlers[i].isPlayer) {
                playerVisible = TRUE;
            }
        }
    }
    for (i = 0; i < SIM_BATTLE3D_MAX_ACTORS; i++) {
        if (frame->actors[i].visible) {
            anyVisible = TRUE;
        }
    }
    menuVisible = BattleHud_IsWindowVisible();

    // Consume queued event notifications with priority: Faint > Hit > Attack,
    // clearing superseded lower-priority flags so stale events never overwrite a higher cut.
    if (sCam.pendingFaint) {
        sCam.pendingFaint = FALSE;
        sCam.pendingHit = FALSE;
        sCam.pendingAttack = FALSE;
        sCam.faintIsPlayer = IsPlayerBattler(battleSys, sCam.pendingFaintBattler);
        TransitionToMode(CAM_MODE_FAINT, CAM_CLIP_FAINT_CUT, 0.18f);
    } else if (sCam.pendingHit) {
        BOOL defIsPlayer = IsPlayerBattler(battleSys, sCam.pendingDefender);
        sCam.pendingHit = FALSE;
        sCam.pendingAttack = FALSE;
        TransitionToMode(CAM_MODE_HIT, defIsPlayer ? CAM_CLIP_HIT_PLAYER : CAM_CLIP_HIT_ENEMY, 0.12f);
    } else if (sCam.pendingAttack) {
        BOOL atkIsPlayer = IsPlayerBattler(battleSys, sCam.pendingAttacker);
        sCam.pendingAttack = FALSE;
        TransitionToMode(CAM_MODE_ATTACK, atkIsPlayer ? CAM_CLIP_ATTACK_PLAYER : CAM_CLIP_ATTACK_ENEMY, 0.18f);
    }

    // If player's Pokemon just appeared during intro without an explicit throw cut,
    // settle cleanly to idle/home so command selection opens on a composed view.
    if (playerVisible && !sCam.playerSeenVisible) {
        sCam.playerSeenVisible = TRUE;
        if (sCam.mode == CAM_MODE_INTRO && !sCam.throwTriggered) {
            TransitionToMode(CAM_MODE_IDLE, CAM_CLIP_WAIT_IDLE_0, 0.65f);
            sCam.idleCycleIdx = 0;
            sCam.idlePassDir = 1;
        }
    }

    // If command menu opened while still in intro or throw, ease gently into idle drift.
    if (menuVisible && (sCam.mode == CAM_MODE_INTRO || sCam.mode == CAM_MODE_THROW)) {
        TransitionToMode(CAM_MODE_IDLE, CAM_CLIP_WAIT_IDLE_0, 0.55f);
        sCam.idleCycleIdx = 0;
        sCam.idlePassDir = 1;
    }

    // Evaluate active mode pose and step deterministic 1/60s clock.
    switch (sCam.mode) {
    case CAM_MODE_INTRO: {
        float introDur;
        if (sCam.isTrainerBattle) {
            SampleTrainerIntroPose(sCam.clipTime, &rawPose);
            introDur = 2.40f;
        } else {
            const BdspCamClip *c = &sBank.clips[CAM_CLIP_INTRO_WILD];
            SampleClip(CAM_CLIP_INTRO_WILD, sCam.clipTime, &rawPose);
            introDur = c->duration;
        }
        // Hold opening frame until the battle scene actually reveals a battler/trainer
        // so the intro sweep plays on-screen rather than behind the black battle wipe.
        if (anyVisible) {
            sCam.clipTime += BDSP_CAM_DT;
        }
        if (sCam.clipTime >= introDur) {
            TransitionToMode(CAM_MODE_IDLE, CAM_CLIP_WAIT_IDLE_0, 0.60f);
            sCam.idleCycleIdx = 0;
            sCam.idlePassDir = 1;
        }
        break;
    }

    case CAM_MODE_THROW: {
        const BdspCamClip *c = &sBank.clips[CAM_CLIP_THROW_CUT];
        SampleClip(CAM_CLIP_THROW_CUT, sCam.clipTime, &rawPose);
        sCam.clipTime += BDSP_CAM_DT;
        if (sCam.clipTime >= c->duration) {
            TransitionToMode(CAM_MODE_IDLE, CAM_CLIP_WAIT_IDLE_0, 0.55f);
            sCam.idleCycleIdx = 0;
            sCam.idlePassDir = 1;
        }
        break;
    }

    case CAM_MODE_ATTACK: {
        const BdspCamClip *c = &sBank.clips[sCam.activeClip];
        SampleClip(sCam.activeClip, sCam.clipTime, &rawPose);
        sCam.clipTime += BDSP_CAM_DT;
        if (sCam.clipTime >= c->duration) {
            TransitionToMode(CAM_MODE_RETURN_HOME, CAM_CLIP_WAIT_IDLE_0, 0.55f);
        }
        break;
    }

    case CAM_MODE_HIT: {
        const BdspCamClip *c = &sBank.clips[sCam.activeClip];
        SampleClip(sCam.activeClip, sCam.clipTime, &rawPose);
        sCam.clipTime += BDSP_CAM_DT;
        if (sCam.clipTime >= c->duration) {
            TransitionToMode(CAM_MODE_RETURN_HOME, CAM_CLIP_WAIT_IDLE_0, 0.50f);
        }
        break;
    }

    case CAM_MODE_FAINT: {
        const BdspCamClip *c = &sBank.clips[CAM_CLIP_FAINT_CUT];
        if (sCam.faintIsPlayer) {
            AdaptFaintPoseForPlayer(&rawPose);
        } else {
            SampleClip(CAM_CLIP_FAINT_CUT, sCam.clipTime, &rawPose);
        }
        sCam.clipTime += BDSP_CAM_DT;
        if (sCam.clipTime >= c->duration) {
            TransitionToMode(CAM_MODE_RETURN_HOME, CAM_CLIP_WAIT_IDLE_0, 0.60f);
        }
        break;
    }

    case CAM_MODE_RETURN_HOME: {
        rawPose = sBank.home;
        sCam.clipTime += BDSP_CAM_DT;
        if (sCam.clipTime >= sCam.blendDur) {
            int nextIdle = CAM_CLIP_WAIT_IDLE_0 + (sCam.idleCycleIdx % 3);
            TransitionToMode(CAM_MODE_IDLE, nextIdle, 0.70f);
        }
        break;
    }

    case CAM_MODE_IDLE:
    default: {
        int clipId = CAM_CLIP_WAIT_IDLE_0 + (sCam.idleCycleIdx % 3);
        const BdspCamClip *c = &sBank.clips[clipId];
        float dur = (c->duration > 0.5f) ? c->duration : 5.0f;
        float sampleT = (sCam.idlePassDir > 0) ? sCam.clipTime : (dur - sCam.clipTime);

        sCam.activeClip = clipId;
        SampleClip(clipId, sampleT, &rawPose);
        sCam.clipTime += BDSP_CAM_DT;

        if (sCam.clipTime >= dur) {
            // Smoothly advance through wait_idle_0 -> wait_idle_1 -> wait_idle_2
            // just like BDSP's BattleWaitCameraData periodic angle transitions.
            sCam.idleCycleIdx = (sCam.idleCycleIdx + 1) % 3;
            sCam.idlePassDir = (sCam.idleCycleIdx % 2 == 0) ? 1 : -1;
            TransitionToMode(CAM_MODE_IDLE, CAM_CLIP_WAIT_IDLE_0 + sCam.idleCycleIdx, 0.90f);
        }
        break;
    }
    }

    // In doubles, keep attack/hit closeups slightly wider toward home so both slots remain framed.
    if ((BattleSystem_GetBattleType(battleSys) & BATTLE_TYPE_DOUBLES) != 0
        && (sCam.mode == CAM_MODE_ATTACK || sCam.mode == CAM_MODE_HIT)) {
        BdspCamPose widened;
        LerpPose(&rawPose, &sBank.home, 0.35f, &widened);
        rawPose = widened;
    }

    // Apply smooth cross-fade blend from previous pose when transitioning between modes/clips.
    if (sCam.blendDur > 0.001f && sCam.blendTime < sCam.blendDur) {
        float u = sCam.blendTime / sCam.blendDur;
        LerpPose(&sCam.blendFrom, &rawPose, u, &outPose);
        sCam.blendTime += BDSP_CAM_DT;
    } else {
        outPose = rawPose;
    }

    // Preserve any active battle impact shake from BattleStageCamera.
    BattleStageCamera_GetBdspDeltas(&dummyYaw, &dummyPitch, &dummyDist, &dummyFov, &shakeX, &shakeY, &dummyIdle);
    if (shakeX != 0.0f || shakeY != 0.0f) {
        float ox = outPose.eye[0] - outPose.target[0];
        float oz = outPose.eye[2] - outPose.target[2];
        float rx = oz;
        float rz = -ox;
        float rlen = sqrtf(rx * rx + rz * rz);
        float sx = shakeX * 0.040f;
        float sy = shakeY * 0.040f;
        if (rlen > 0.0001f) {
            rx /= rlen;
            rz /= rlen;
            outPose.eye[0] += rx * sx;
            outPose.eye[2] += rz * sx;
            outPose.target[0] += rx * sx;
            outPose.target[2] += rz * sx;
        }
        outPose.eye[1] += sy;
        outPose.target[1] += sy;
    }

    ClampPose(&outPose);

    frame->camEye[0] = outPose.eye[0];
    frame->camEye[1] = outPose.eye[1];
    frame->camEye[2] = outPose.eye[2];
    frame->camTarget[0] = outPose.target[0];
    frame->camTarget[1] = outPose.target[1];
    frame->camTarget[2] = outPose.target[2];
    frame->camFovDeg = outPose.fov;

    sCam.lastPose = outPose;
    sCam.hasLastPose = TRUE;
    MaybeDumpCamera(&outPose);
    sCam.frameCount++;
}
