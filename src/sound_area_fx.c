#include "sound_area_fx.h"

#include <nitro.h>

#include "generated/battle_backgrounds.h"

#include "map_header.h"
#include "sound.h"
#include "sound_system.h"

/*
 * Area FX: capture-unit effects that follow the player's location.
 *
 * Buffer model (NitroSystem capture.c): the mixer output is captured into
 * the SoundSystem capture buffer (SOUND_SYSTEM_CAPTURE_BUFFER_SIZE bytes, the
 * first half for L, the second half for R) and played back by hw channels 1
 * and 3, which are routed straight to the speakers. With interval
 * SOUND_FILTER_INTERVAL (2) each half is split into two blocks, and an SND
 * alarm calls SoundAreaFx_CaptureCallback() each time a block has been
 * captured: bufferL/bufferR point at that block, length is its size in BYTES
 * (0x400 = 512 PCM16 samples per channel), and the samples are modified in
 * place before playback reaches them (about one half-buffer, ~47 ms, later).
 * The callback runs in interrupt context (no capture thread is created), so
 * it uses only shifts and multiplies (no division) and touches no heap.
 *
 * Real sample rate: SND_TIMER_CLOCK / ((16756991 / 22000 + 16) & ~31)
 * = 16756991 / 768 = ~21819 Hz. A callback fires every ~23.5 ms.
 *
 * All DSP state lives in this file, so delay lines and filters stay
 * continuous from one callback to the next. All math is integer: s32
 * accumulators, gains in Q15 (AREA_FX_Q15_ONE = 1.0), one-pole coefficients
 * in Q12, saturated to s16 on output.
 *
 * Effect level ("ramp", Q15) moves by AREA_FX_RAMP_STEP per sample
 * (0 -> 1.0 in 4096 samples, ~190 ms), so starting, stopping and switching
 * effects never clicks: a mode change first ramps the old effect down to 0,
 * then swaps the DSP state at the start of the next block and ramps up.
 *
 * RAM: sDelayLine 8192 bytes + state ~64 bytes (BSS), sine table 514 bytes
 * (rodata). The capture buffer itself is the existing SoundSystem one.
 *
 * tools/audio_fx_preview/preview.py parses the AREA_FX_* defines and the sine
 * table from this file and runs a bit-exact Python port of the callback.
 */

// Set to FALSE to stop surfing from muffling the sound. See
// SoundAreaFx_ResolveMode() for the priority between zone and water effects.
#define AREA_FX_MUFFLE_WHILE_SURFING TRUE

#define AREA_FX_Q15_ONE   32768
#define AREA_FX_RAMP_STEP 8

#define AREA_FX_LINE_LEN  4096 // s16 entries in sDelayLine (power of two)
#define AREA_FX_LINE_MASK (AREA_FX_LINE_LEN - 1)

// ECHO: mono feedback comb with a damped (low-passed) feedback path.
#define AREA_FX_ECHO_DELAY    3272 // samples, ~150 ms
#define AREA_FX_ECHO_FEEDBACK 13107 // Q15, 0.4
#define AREA_FX_ECHO_WET      9830 // Q15, 0.3
#define AREA_FX_ECHO_DAMP     2048 // Q12, one-pole low-pass on the echo, 0.5

// MUFFLE: two cascaded one-pole low-passes per channel (~860 Hz each, about
// 550 Hz -3 dB overall). State is kept in Q4 for precision.
#define AREA_FX_MUFFLE_COEF 899 // Q12, 1 - exp(-2 * pi * 860 / 21819)
#define AREA_FX_MUFFLE_WET  32768 // Q15, 1.0 (fully muffled)

// WARP: per-channel short delay whose length is swept by a slow sine LFO
// (vibrato, about +-33 cents), with feedback, mixed with the dry signal and
// lightly ring-modulated.
#define AREA_FX_WARP_LEN          2048 // samples per channel (two halves of sDelayLine)
#define AREA_FX_WARP_MASK         (AREA_FX_WARP_LEN - 1)
#define AREA_FX_WARP_BASE_DELAY   320 // samples, ~15 ms
#define AREA_FX_WARP_DEPTH        192 // samples, +-8.8 ms
#define AREA_FX_WARP_LFO_INC      68896 // 0.35 Hz: f * 2^32 / 21819
#define AREA_FX_WARP_STEREO_PHASE 0x40000000 // R LFO is 90 degrees ahead of L
#define AREA_FX_WARP_FEEDBACK     9830 // Q15, 0.3
#define AREA_FX_WARP_WET          24576 // Q15, 0.75
#define AREA_FX_WARP_RING_INC     13779171 // 70 Hz carrier
#define AREA_FX_WARP_RING_DEPTH   6554 // Q15, 0.2 (0 disables the ring mod)

#define AREA_FX_START_RETRY_FRAMES 60

typedef struct AreaFxDsp {
    volatile int mode; // Mode rendered by the callback
    volatile s32 ramp; // Effect level, Q15 in [0, AREA_FX_Q15_ONE]
    u32 writePos;
    s32 echoDamp;
    s32 muffle[2][2]; // [channel][pole], Q4
    u32 lfoPhase;
    u32 ringPhase;
} AreaFxDsp;

typedef struct AreaFxState {
    volatile int requestedMode; // Read by the callback once per block
    u32 suspendMask;
    BOOL ownsCapture;
    BOOL surfing;
    u8 zoneMode;
    u8 startRetryFrames;
} AreaFxState;

static void SoundAreaFx_CaptureCallback(void *bufferL, void *bufferR, u32 length, NNSSndCaptureFormat format, void *arg);
static void SoundAreaFx_ResetDsp(int mode);
static enum SoundAreaFxMode SoundAreaFx_ResolveMode(void);
static void SoundAreaFx_StopCapture(void);

static AreaFxState sAreaFx;
static AreaFxDsp sAreaFxDsp;
static s16 sDelayLine[AREA_FX_LINE_LEN] ATTRIBUTE_ALIGN(32);

// round(32767 * sin(2 * pi * i / 256)), plus a guard entry for interpolation
static const s16 sSineTable[257] = {
    0, 804, 1608, 2410, 3212, 4011, 4808, 5602,
    6393, 7179, 7962, 8739, 9512, 10278, 11039, 11793,
    12539, 13279, 14010, 14732, 15446, 16151, 16846, 17530,
    18204, 18868, 19519, 20159, 20787, 21403, 22005, 22594,
    23170, 23731, 24279, 24811, 25329, 25832, 26319, 26790,
    27245, 27683, 28105, 28510, 28898, 29268, 29621, 29956,
    30273, 30571, 30852, 31113, 31356, 31580, 31785, 31971,
    32137, 32285, 32412, 32521, 32609, 32678, 32728, 32757,
    32767, 32757, 32728, 32678, 32609, 32521, 32412, 32285,
    32137, 31971, 31785, 31580, 31356, 31113, 30852, 30571,
    30273, 29956, 29621, 29268, 28898, 28510, 28105, 27683,
    27245, 26790, 26319, 25832, 25329, 24811, 24279, 23731,
    23170, 22594, 22005, 21403, 20787, 20159, 19519, 18868,
    18204, 17530, 16846, 16151, 15446, 14732, 14010, 13279,
    12539, 11793, 11039, 10278, 9512, 8739, 7962, 7179,
    6393, 5602, 4808, 4011, 3212, 2410, 1608, 804,
    0, -804, -1608, -2410, -3212, -4011, -4808, -5602,
    -6393, -7179, -7962, -8739, -9512, -10278, -11039, -11793,
    -12539, -13279, -14010, -14732, -15446, -16151, -16846, -17530,
    -18204, -18868, -19519, -20159, -20787, -21403, -22005, -22594,
    -23170, -23731, -24279, -24811, -25329, -25832, -26319, -26790,
    -27245, -27683, -28105, -28510, -28898, -29268, -29621, -29956,
    -30273, -30571, -30852, -31113, -31356, -31580, -31785, -31971,
    -32137, -32285, -32412, -32521, -32609, -32678, -32728, -32757,
    -32767, -32757, -32728, -32678, -32609, -32521, -32412, -32285,
    -32137, -31971, -31785, -31580, -31356, -31113, -30852, -30571,
    -30273, -29956, -29621, -29268, -28898, -28510, -28105, -27683,
    -27245, -26790, -26319, -25832, -25329, -24811, -24279, -23731,
    -23170, -22594, -22005, -21403, -20787, -20159, -19519, -18868,
    -18204, -17530, -16846, -16151, -15446, -14732, -14010, -13279,
    -12539, -11793, -11039, -10278, -9512, -8739, -7962, -7179,
    -6393, -5602, -4808, -4011, -3212, -2410, -1608, -804,
    0,
};

static inline s16 AreaFx_Sat16(s32 value)
{
    if (value > 32767) {
        return 32767;
    }

    if (value < -32768) {
        return -32768;
    }

    return (s16)value;
}

static inline s32 AreaFx_Sine(u32 phase)
{
    u32 index = phase >> 24;
    s32 frac = (s32)((phase >> 8) & 0xFFFF);
    s32 a = sSineTable[index];
    s32 b = sSineTable[index + 1];

    return a + (((b - a) * frac) >> 16);
}

static inline s32 AreaFx_StepRamp(s32 ramp, s32 target)
{
    if (ramp < target) {
        ramp += AREA_FX_RAMP_STEP;

        if (ramp > target) {
            ramp = target;
        }
    } else if (ramp > target) {
        ramp -= AREA_FX_RAMP_STEP;

        if (ramp < target) {
            ramp = target;
        }
    }

    return ramp;
}

static void SoundAreaFx_ProcessEcho(s16 *bufL, s16 *bufR, int count, s32 target)
{
    AreaFxDsp *dsp = &sAreaFxDsp;
    s32 ramp = dsp->ramp;
    u32 pos = dsp->writePos;
    s32 damp = dsp->echoDamp;
    int i;

    for (i = 0; i < count; i++) {
        s32 l = bufL[i];
        s32 r = bufR[i];
        s32 mono = (l + r) >> 1;
        s32 tap = sDelayLine[(pos - AREA_FX_ECHO_DELAY) & AREA_FX_LINE_MASK];
        s32 wet, dry;

        damp += ((tap - damp) * AREA_FX_ECHO_DAMP) >> 12;
        sDelayLine[pos] = AreaFx_Sat16(mono + ((damp * AREA_FX_ECHO_FEEDBACK) >> 15));
        pos = (pos + 1) & AREA_FX_LINE_MASK;

        ramp = AreaFx_StepRamp(ramp, target);
        wet = (ramp * AREA_FX_ECHO_WET) >> 15;
        dry = AREA_FX_Q15_ONE - (wet >> 1);

        bufL[i] = AreaFx_Sat16((l * dry + damp * wet) >> 15);
        bufR[i] = AreaFx_Sat16((r * dry + damp * wet) >> 15);
    }

    dsp->writePos = pos;
    dsp->echoDamp = damp;
    dsp->ramp = ramp;
}

static void SoundAreaFx_ProcessMuffle(s16 *bufL, s16 *bufR, int count, s32 target)
{
    AreaFxDsp *dsp = &sAreaFxDsp;
    s32 ramp = dsp->ramp;
    s32 l1 = dsp->muffle[0][0];
    s32 l2 = dsp->muffle[0][1];
    s32 r1 = dsp->muffle[1][0];
    s32 r2 = dsp->muffle[1][1];
    int i;

    for (i = 0; i < count; i++) {
        s32 l = bufL[i];
        s32 r = bufR[i];
        s32 wet, dry;

        l1 += ((l * 16 - l1) * AREA_FX_MUFFLE_COEF) >> 12;
        l2 += ((l1 - l2) * AREA_FX_MUFFLE_COEF) >> 12;
        r1 += ((r * 16 - r1) * AREA_FX_MUFFLE_COEF) >> 12;
        r2 += ((r1 - r2) * AREA_FX_MUFFLE_COEF) >> 12;

        ramp = AreaFx_StepRamp(ramp, target);
        wet = (ramp * AREA_FX_MUFFLE_WET) >> 15;
        dry = AREA_FX_Q15_ONE - wet;

        bufL[i] = AreaFx_Sat16((l * dry + (l2 >> 4) * wet) >> 15);
        bufR[i] = AreaFx_Sat16((r * dry + (r2 >> 4) * wet) >> 15);
    }

    dsp->muffle[0][0] = l1;
    dsp->muffle[0][1] = l2;
    dsp->muffle[1][0] = r1;
    dsp->muffle[1][1] = r2;
    dsp->ramp = ramp;
}

// Reads the warp delay line of one channel (base = 0 or AREA_FX_WARP_LEN) at
// a fractional delay set by the LFO, then writes the new input with feedback.
static inline s32 AreaFx_WarpChannel(s32 in, u32 base, u32 pos, u32 phase)
{
    s32 delay = (AREA_FX_WARP_BASE_DELAY << 8) + ((AREA_FX_WARP_DEPTH * AreaFx_Sine(phase)) >> 7); // Q8 samples
    u32 whole = (u32)(delay >> 8);
    s32 frac = delay & 0xFF;
    s32 a = sDelayLine[base + ((pos - whole) & AREA_FX_WARP_MASK)];
    s32 b = sDelayLine[base + ((pos - whole - 1) & AREA_FX_WARP_MASK)];
    s32 tap = a + (((b - a) * frac) >> 8);

    sDelayLine[base + pos] = AreaFx_Sat16(in + ((tap * AREA_FX_WARP_FEEDBACK) >> 15));

    return tap;
}

static void SoundAreaFx_ProcessWarp(s16 *bufL, s16 *bufR, int count, s32 target)
{
    AreaFxDsp *dsp = &sAreaFxDsp;
    s32 ramp = dsp->ramp;
    u32 pos = dsp->writePos;
    u32 lfo = dsp->lfoPhase;
    u32 ring = dsp->ringPhase;
    int i;

    for (i = 0; i < count; i++) {
        s32 l = bufL[i];
        s32 r = bufR[i];
        s32 tapL = AreaFx_WarpChannel(l, 0, pos, lfo);
        s32 tapR = AreaFx_WarpChannel(r, AREA_FX_WARP_LEN, pos, lfo + AREA_FX_WARP_STEREO_PHASE);
        s32 ringGain = (AREA_FX_Q15_ONE - AREA_FX_WARP_RING_DEPTH) + ((AREA_FX_WARP_RING_DEPTH * AreaFx_Sine(ring)) >> 15);
        s32 wet, dry;

        tapL = (tapL * ringGain) >> 15;
        tapR = (tapR * ringGain) >> 15;

        pos = (pos + 1) & AREA_FX_WARP_MASK;
        lfo += AREA_FX_WARP_LFO_INC;
        ring += AREA_FX_WARP_RING_INC;

        ramp = AreaFx_StepRamp(ramp, target);
        wet = (ramp * AREA_FX_WARP_WET) >> 15;
        dry = AREA_FX_Q15_ONE - wet;

        bufL[i] = AreaFx_Sat16((l * dry + tapL * wet) >> 15);
        bufR[i] = AreaFx_Sat16((r * dry + tapR * wet) >> 15);
    }

    dsp->writePos = pos;
    dsp->lfoPhase = lfo;
    dsp->ringPhase = ring;
    dsp->ramp = ramp;
}

// Only called while the callback can not run (capture stopped), or from the
// callback itself.
static void SoundAreaFx_ResetDsp(int mode)
{
    AreaFxDsp *dsp = &sAreaFxDsp;

    dsp->ramp = 0;
    dsp->writePos = 0;
    dsp->echoDamp = 0;
    dsp->muffle[0][0] = 0;
    dsp->muffle[0][1] = 0;
    dsp->muffle[1][0] = 0;
    dsp->muffle[1][1] = 0;
    dsp->lfoPhase = 0;
    dsp->ringPhase = 0;

    if (mode == SOUND_AREA_FX_ECHO || mode == SOUND_AREA_FX_WARP) {
        MI_CpuClear32(sDelayLine, sizeof(sDelayLine));
    }

    dsp->mode = mode;
}

static void SoundAreaFx_CaptureCallback(void *bufferL, void *bufferR, u32 length, NNSSndCaptureFormat format, void *arg)
{
    AreaFxDsp *dsp = &sAreaFxDsp;
    int requested = sAreaFx.requestedMode;
    int count;
    s32 target;

    (void)arg;

    if (format != NNS_SND_CAPTURE_FORMAT_PCM16) {
        return;
    }

    count = (int)(length >> 1);

    // A mode change waits until the old effect has faded out completely.
    if (dsp->mode != requested && dsp->ramp == 0) {
        SoundAreaFx_ResetDsp(requested);
    }

    target = (dsp->mode == requested) ? AREA_FX_Q15_ONE : 0;

    switch (dsp->mode) {
    case SOUND_AREA_FX_ECHO:
        SoundAreaFx_ProcessEcho((s16 *)bufferL, (s16 *)bufferR, count, target);
        break;
    case SOUND_AREA_FX_MUFFLE:
        SoundAreaFx_ProcessMuffle((s16 *)bufferL, (s16 *)bufferR, count, target);
        break;
    case SOUND_AREA_FX_WARP:
        SoundAreaFx_ProcessWarp((s16 *)bufferL, (s16 *)bufferR, count, target);
        break;
    default:
        return; // SOUND_AREA_FX_NONE: the block passes through untouched
    }

    DC_FlushRange(bufferL, length);
    DC_FlushRange(bufferR, length);
}

static enum SoundAreaFxMode SoundAreaFx_ResolveMode(void)
{
    // The Distortion World always warps, even while surfing there.
    if (sAreaFx.zoneMode == SOUND_AREA_FX_WARP) {
        return SOUND_AREA_FX_WARP;
    }

#if AREA_FX_MUFFLE_WHILE_SURFING
    // Water muffling. To muffle specific maps instead, return
    // SOUND_AREA_FX_MUFFLE from SoundAreaFx_GetModeForMapHeader(); for rain,
    // check the field weather here instead of sAreaFx.surfing.
    if (sAreaFx.surfing) {
        return SOUND_AREA_FX_MUFFLE;
    }
#endif

    return (enum SoundAreaFxMode)sAreaFx.zoneMode;
}

static void SoundAreaFx_StopCapture(void)
{
    if (sAreaFx.ownsCapture) {
        NNS_SndCaptureStopEffect();
        sAreaFx.ownsCapture = FALSE;
    }

    SoundAreaFx_ResetDsp(SOUND_AREA_FX_NONE);
}

void SoundAreaFx_Update(void)
{
    u8 *mainScene = SoundSystem_GetParam(SOUND_SYSTEM_PARAM_MAIN_SCENE);
    int desired;

    // Battles, contests, cutscenes and the title screen run in other sound
    // scenes; area FX only plays in the field.
    if (*mainScene == SOUND_SCENE_FIELD) {
        sAreaFx.suspendMask &= ~SOUND_AREA_FX_SUSPEND_SCENE;
    } else {
        sAreaFx.suspendMask |= SOUND_AREA_FX_SUSPEND_SCENE;
    }

    desired = (sAreaFx.suspendMask != 0) ? SOUND_AREA_FX_NONE : SoundAreaFx_ResolveMode();
    sAreaFx.requestedMode = desired;

    if (sAreaFx.ownsCapture) {
        if (NNS_SndCaptureIsActive() == FALSE) {
            // Someone else stopped the capture unit.
            sAreaFx.ownsCapture = FALSE;
            SoundAreaFx_ResetDsp(SOUND_AREA_FX_NONE);
        } else if (desired == SOUND_AREA_FX_NONE && sAreaFxDsp.mode == SOUND_AREA_FX_NONE) {
            // The callback has faded the effect out; give the unit back.
            SoundAreaFx_StopCapture();
        }

        return;
    }

    if (sAreaFx.startRetryFrames != 0) {
        sAreaFx.startRetryFrames--;
        return;
    }

    if (desired == SOUND_AREA_FX_NONE || NNS_SndCaptureIsActive()) {
        return;
    }

    SoundAreaFx_ResetDsp(desired);

    if (NNS_SndCaptureStartEffect(
            SoundSystem_GetParam(SOUND_SYSTEM_PARAM_CAPTURE_BUFFER),
            SOUND_SYSTEM_CAPTURE_BUFFER_SIZE,
            NNS_SND_CAPTURE_FORMAT_PCM16,
            SOUND_FILTER_SAMPLE_RATE,
            SOUND_FILTER_INTERVAL,
            SoundAreaFx_CaptureCallback,
            NULL)) {
        sAreaFx.ownsCapture = TRUE;
    } else {
        SoundAreaFx_ResetDsp(SOUND_AREA_FX_NONE);
        sAreaFx.startRetryFrames = AREA_FX_START_RETRY_FRAMES;
    }
}

enum SoundAreaFxMode SoundAreaFx_GetModeForMapHeader(u32 mapHeaderID)
{
    switch (MapHeader_GetBattleBG(mapHeaderID)) {
    case BACKGROUND_CAVE_1:
    case BACKGROUND_CAVE_2:
    case BACKGROUND_CAVE_3:
        return SOUND_AREA_FX_ECHO;
    case BACKGROUND_DISTORTION_WORLD:
        return SOUND_AREA_FX_WARP;
    default:
        return SOUND_AREA_FX_NONE;
    }
}

void SoundAreaFx_OnMapChange(u32 mapHeaderID)
{
    sAreaFx.zoneMode = (u8)SoundAreaFx_GetModeForMapHeader(mapHeaderID);
}

void SoundAreaFx_SetSurfing(BOOL surfing)
{
    sAreaFx.surfing = surfing;
}

void SoundAreaFx_SetMode(enum SoundAreaFxMode mode)
{
    if (mode >= SOUND_AREA_FX_MODE_COUNT) {
        mode = SOUND_AREA_FX_NONE;
    }

    sAreaFx.zoneMode = (u8)mode;
}

enum SoundAreaFxMode SoundAreaFx_GetMode(void)
{
    return (enum SoundAreaFxMode)sAreaFx.zoneMode;
}

enum SoundAreaFxMode SoundAreaFx_GetEffectiveMode(void)
{
    if (sAreaFx.ownsCapture == FALSE) {
        return SOUND_AREA_FX_NONE;
    }

    return (enum SoundAreaFxMode)sAreaFxDsp.mode;
}

void SoundAreaFx_SuspendFor(u32 reasons)
{
    sAreaFx.suspendMask |= reasons;
    sAreaFx.requestedMode = SOUND_AREA_FX_NONE;

    // The caller is about to use the capture unit itself, so there is no
    // time for a fade-out.
    if (sAreaFx.ownsCapture) {
        SoundAreaFx_StopCapture();
    }
}

void SoundAreaFx_ResumeFor(u32 reasons)
{
    sAreaFx.suspendMask &= ~reasons;
}

BOOL SoundAreaFx_OwnsCapture(void)
{
    return sAreaFx.ownsCapture;
}
