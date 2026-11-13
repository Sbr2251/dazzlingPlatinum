#include "fx_lighting.h"

#include <nitro.h>
#include <simulator/sim_lights.h>
#include <stdlib.h>

#include "constants/battle.h"
#include "generated/pokemon_types.h"
#include "move_table.h"
#include "port/sim_config_prj.h"

// ---------------------------------------------------------------------------
// Feature gates (same pattern as fx_arena.c)
// ---------------------------------------------------------------------------

static int EnvFlag(const char *name)
{
    const char *env = getenv(name);

    if (env == NULL || env[0] == 0) {
        return -1;
    }

    return env[0] != '0' ? 1 : 0;
}

static BOOL FxEnabled(int configValue, const char *envName)
{
    static int sHeadless = -1;
    int env;

    if (sHeadless < 0) {
        const char *headless = getenv("SIM_HEADLESS");
        sHeadless = (headless != NULL && headless[0] != 0 && headless[0] != '0') ? 1 : 0;
    }

    env = EnvFlag(envName);

    if (sHeadless) {
        return env == 1 ? TRUE : FALSE;
    }

    if (env >= 0) {
        return env == 1 ? TRUE : FALSE;
    }

    return configValue ? TRUE : FALSE;
}

BOOL FxLighting_SceneLightsEnabled(void)
{
    return FxEnabled(SIM_Config_prj_GetConfig()->sceneLights, "SIM_FX_LIGHTS");
}

BOOL FxLighting_SpriteRimLightEnabled(void)
{
    return FxEnabled(SIM_Config_prj_GetConfig()->spriteRimLight, "SIM_FX_RIM");
}

// ---------------------------------------------------------------------------
// Move light table: move type -> light colour / radius / flicker style
// ---------------------------------------------------------------------------

typedef struct {
    float r, g, b;
    float radius;
    float intensity;
    int flash; // 0 = steady/flicker, 1 = hard electric-style flash pulses
} FxMoveLight;

static FxMoveLight MoveLightForType(int type)
{
    FxMoveLight light = { 1.0f, 1.0f, 1.0f, 0.9f, 0.55f, 0 };

    // Intensities are kept low enough that sprites keep their detail:
    // the light tints the scene, it does not wash it to flat colour.
    // Radii are local (a flame / a bolt), never full-screen.
    switch (type) {
    case TYPE_FIRE:
        light.r = 1.0f; light.g = 0.55f; light.b = 0.20f; light.radius = 0.75f; light.intensity = 0.60f;
        break;
    case TYPE_ELECTRIC:
        // Warm white-yellow, hard falloff (small radius), short flash.
        light.r = 1.0f; light.g = 0.98f; light.b = 0.85f; light.radius = 0.55f; light.intensity = 0.90f; light.flash = 1;
        break;
    case TYPE_WATER:
        light.r = 0.30f; light.g = 0.60f; light.b = 1.0f; light.radius = 0.80f; light.intensity = 0.55f;
        break;
    case TYPE_GRASS:
        light.r = 0.45f; light.g = 1.0f; light.b = 0.45f; light.radius = 0.75f; light.intensity = 0.48f;
        break;
    case TYPE_ICE:
        light.r = 0.75f; light.g = 0.95f; light.b = 1.0f; light.radius = 0.75f; light.intensity = 0.52f;
        break;
    case TYPE_PSYCHIC:
        light.r = 1.0f; light.g = 0.55f; light.b = 0.85f; light.radius = 0.75f; light.intensity = 0.52f;
        break;
    case TYPE_DARK:
    case TYPE_GHOST:
        light.r = 0.55f; light.g = 0.35f; light.b = 0.85f; light.radius = 0.70f; light.intensity = 0.42f;
        break;
    case TYPE_DRAGON:
        light.r = 1.0f; light.g = 0.45f; light.b = 0.30f; light.radius = 0.85f; light.intensity = 0.62f;
        break;
    case TYPE_FAIRY:
        light.r = 1.0f; light.g = 0.75f; light.b = 0.90f; light.radius = 0.75f; light.intensity = 0.48f;
        break;
    case TYPE_GROUND:
    case TYPE_ROCK:
        light.r = 0.85f; light.g = 0.70f; light.b = 0.45f; light.radius = 0.70f; light.intensity = 0.42f;
        break;
    case TYPE_FLYING:
        light.r = 0.80f; light.g = 0.90f; light.b = 1.0f; light.radius = 0.70f; light.intensity = 0.42f;
        break;
    case TYPE_POISON:
        light.r = 0.70f; light.g = 0.40f; light.b = 0.90f; light.radius = 0.70f; light.intensity = 0.45f;
        break;
    case TYPE_BUG:
        light.r = 0.70f; light.g = 0.95f; light.b = 0.40f; light.radius = 0.70f; light.intensity = 0.42f;
        break;
    case TYPE_STEEL:
        light.r = 0.85f; light.g = 0.90f; light.b = 1.0f; light.radius = 0.70f; light.intensity = 0.45f;
        break;
    case TYPE_FIGHTING:
        light.r = 1.0f; light.g = 0.70f; light.b = 0.40f; light.radius = 0.70f; light.intensity = 0.45f;
        break;
    case TYPE_NORMAL:
    case TYPE_MYSTERY:
    default:
        light.r = 1.0f; light.g = 0.95f; light.b = 0.85f; light.radius = 0.65f; light.intensity = 0.34f;
        break;
    }

    return light;
}

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

static BOOL sMoveActive = FALSE;
static int sMoveType = TYPE_NORMAL;
static int sAttacker = BATTLER_PLAYER_1;
static int sDefender = BATTLER_ENEMY_1;
static u32 sFrame = 0;
static u32 sSeed = 0;
// Afterglow: after the animation script ends, the light decays over
// this many Update calls instead of cutting out (embers / a fading
// flash read naturally, and the light is still on for the damage
// frames that follow the animation).
static int sTail = 0;
#define FX_LIGHTING_TAIL_FRAMES 60

// Deterministic flicker in [0, 1): an LCG stepped from the move seed,
// so the same move and frame give the same light under lockstep.
static float Flicker(u32 frame)
{
    u32 x = sSeed + frame * 2654435761u;
    x ^= x >> 16;
    x *= 2246822519u;
    x ^= x >> 13;
    return (float)(x & 0xFFFFFF) / 16777216.0f;
}

// Battler -> NDC position on the G3 screen. Player sprites sit
// lower-left, enemy sprites upper-right; doubles partners offset in x.
static void BattlerPos(int battler, float *outX, float *outY)
{
    switch (battler) {
    case BATTLER_PLAYER_1:
        *outX = -0.55f; *outY = -0.40f;
        break;
    case BATTLER_PLAYER_2:
        *outX = -0.25f; *outY = -0.55f;
        break;
    case BATTLER_ENEMY_1:
        *outX = 0.50f; *outY = 0.30f;
        break;
    case BATTLER_ENEMY_2:
        *outX = 0.75f; *outY = 0.10f;
        break;
    default:
        *outX = 0.0f; *outY = 0.0f;
        break;
    }
}

void FxLighting_StartMove(int move, int attacker, int defender)
{
    if (move < 0) {
        move = 0;
    }

    sMoveActive = TRUE;
    sMoveType = (int)MoveTable_LoadParam(move, MOVEATTRIBUTE_TYPE);
    sAttacker = attacker;
    sDefender = defender;
    sFrame = 0;
    sTail = 0;
    sSeed = (u32)(move * 2654435761u + 12345u);
}

void FxLighting_EndMove(void)
{
    // Start the afterglow tail; Update clears the move when it runs out.
    sTail = FX_LIGHTING_TAIL_FRAMES;
    FxLighting_Update();
}

void FxLighting_UpdateBattleFrame(void)
{
    SIM_LightsState state;

    // A move is active: the anim system owns the state this frame.
    if (sMoveActive) {
        return;
    }

    if (!FxLighting_SceneLightsEnabled() && !FxLighting_SpriteRimLightEnabled()) {
        SIM_Lights_Clear();
        return;
    }

    state.ambientR = 1.0f;
    state.ambientG = 1.0f;
    state.ambientB = 1.0f;
    state.keyDirX = -0.5f;
    state.keyDirY = 0.8f;
    state.keyR = 1.0f;
    state.keyG = 0.98f;
    state.keyB = 0.90f;
    state.count = 0;
    state.rimStrength = FxLighting_SpriteRimLightEnabled() ? 0.38f : 0.0f;
    SIM_Lights_Set(&state);
}

void FxLighting_Update(void)
{
    SIM_LightsState state;
    float rim, fade, flick, intensity;
    float atkX, atkY, defX, defY;
    FxMoveLight track;

    if (!FxLighting_SceneLightsEnabled() && !FxLighting_SpriteRimLightEnabled()) {
        SIM_Lights_Clear();
        return;
    }

    state.ambientR = 1.0f;
    state.ambientG = 1.0f;
    state.ambientB = 1.0f;
    state.keyDirX = -0.5f;
    state.keyDirY = 0.8f;
    state.keyR = 1.0f;
    state.keyG = 0.98f;
    state.keyB = 0.90f;
    state.count = 0;
    rim = FxLighting_SpriteRimLightEnabled() ? 0.38f : 0.0f;
    state.rimStrength = rim;

    if (sMoveActive && FxLighting_SceneLightsEnabled()) {
        track = MoveLightForType(sMoveType);
        // Fade in over the first 6 frames so the light grows with the
        // move animation instead of popping on. In the tail, fade out
        // linearly over the remaining tail frames.
        fade = sFrame < 6 ? (float)(sFrame + 1) / 6.0f : 1.0f;
        if (sTail > 0) {
            fade *= (float)sTail / (float)FX_LIGHTING_TAIL_FRAMES;
            sTail--;
            if (sTail == 0) {
                sMoveActive = FALSE;
            }
        }
        if (track.flash) {
            // Electric: a short flash (2 of every 16 frames, bright),
            // near-dark between, so it reads as a bolt strike.
            flick = (sFrame % 16) < 2 ? 1.9f : 0.05f;
        } else {
            // Fire and friends: warm flicker around the base level.
            flick = 0.78f + 0.42f * Flicker(sFrame);
        }
        intensity = track.intensity * fade * flick;

        BattlerPos(sAttacker, &atkX, &atkY);
        BattlerPos(sDefender, &defX, &defY);

        // Three local lights, no full-screen wash: the attacker (a
        // brief lit edge), the projectile/flame at the midpoint
        // between attacker and target (the strongest light), and the
        // target (the impact reads there). Light falls off well
        // before the screen edge, so sprites keep their detail.
        state.lights[0].x = atkX;
        state.lights[0].y = atkY;
        state.lights[0].radius = track.radius * 0.8f;
        state.lights[0].intensity = intensity * 0.5f;
        state.lights[0].r = track.r;
        state.lights[0].g = track.g;
        state.lights[0].b = track.b;
        state.lights[1].x = (atkX + defX) * 0.5f;
        state.lights[1].y = (atkY + defY) * 0.5f;
        state.lights[1].radius = track.radius;
        state.lights[1].intensity = intensity * 0.9f;
        state.lights[1].r = track.r;
        state.lights[1].g = track.g;
        state.lights[1].b = track.b;
        state.lights[2].x = defX;
        state.lights[2].y = defY;
        state.lights[2].radius = track.radius * 0.8f;
        state.lights[2].intensity = intensity * 0.8f;
        state.lights[2].r = track.r;
        state.lights[2].g = track.g;
        state.lights[2].b = track.b;
        state.count = 3;
        sFrame++;
    }

    SIM_Lights_Set(&state);
}

void FxLighting_Clear(void)
{
    sMoveActive = FALSE;
    sTail = 0;
    sFrame = 0;
    SIM_Lights_Clear();
}
