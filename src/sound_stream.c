#include "sound_stream.h"

#include <nitro.h>
#include <string.h>

#include "generated/sdat.h"

#include "sound.h"
#include "sound_system.h"

// Set to 0 to drop the proof-of-concept override (Pokemon Center theme ->
// STRM_TEST_LOOP) and go back to the sequenced Pokemon Center music.
#define SOUND_STREAM_ENABLE_TEST_OVERRIDE 1

#define SOUND_STREAM_NONE               -1
#define SOUND_STREAM_MAX_CHANNELS       4
#define SOUND_STREAM_RESUME_FADE_FRAMES 6 // Short fade-in on resume hides the ADPCM restart click
#define SOUND_STREAM_ALL_HW_CHANNELS    0xFFFF

typedef struct SoundStreamOverride {
    u16 seqID; // SEQ_* that scripts and map headers keep requesting
    u16 strmID; // STRM_* played instead
    u8 volume; // Extra stream volume (0-127) on top of the archive's strmInfo volume
} SoundStreamOverride;

// SEQ -> STRM override table. Removing a row brings back the sequenced
// version of that theme; no script or map change is needed either way.
// The table is terminated by a SEQ_NONE row.
static const SoundStreamOverride sStreamOverrides[] = {
#if SOUND_STREAM_ENABLE_TEST_OVERRIDE
    { SEQ_PC_01, STRM_TEST_LOOP, SOUND_VOLUME_MAX }, // Pokemon Center (day)
    { SEQ_PC_02, STRM_TEST_LOOP, SOUND_VOLUME_MAX }, // Pokemon Center (night)
#endif
    { SEQ_NONE, 0, 0 },
};

static NNSSndStrmHandle sStreamHandle;
static BOOL sInitialized;
static int sStrmID; // STRM_* currently owned by the BGM, or SOUND_STREAM_NONE
static u16 sOwnerSeqID; // The SEQ_* whose override is playing
static enum SoundHandleType sOwnerHandleType; // SOUND_HANDLE_TYPE_FIELD_BGM or SOUND_HANDLE_TYPE_BGM
static BOOL sPaused; // Stopped with its position saved (fanfare, battle, ...)
static u32 sPausedPosition; // Milliseconds, see NNS_SndArcStrmGetCurrentPlayingPos
static int sTableVolume;
static int sInitialVolume; // Mirrors NNS_SndPlayerSetInitialVolume on the owner handle
static int sFieldPlayerVolume; // Mirrors NNS_SndPlayerSetPlayerVolume(PLAYER_FIELD, ...)
static int sBGMPlayerVolume; // Mirrors NNS_SndPlayerSetPlayerVolume(PLAYER_BGM, ...)
static int sTargetVolume; // Last fader target, mirrors NNS_SndPlayerMoveVolume on the owner handle
static int sChannelVolumes[SOUND_STREAM_MAX_CHANNELS];
static u32 sStreamHWChannels; // Hardware channels used by stream player STRM_PLAYER_BGM
static u32 sFieldChannels; // Base allocatable channels of the sequence players that share them
static u32 sFanfareChannels;
static u32 sBGMChannels;
static BOOL sChannelsReserved;

static const SoundStreamOverride *SoundStream_FindOverride(u16 seqID)
{
    int i;

    if (seqID == SEQ_NONE) {
        return NULL;
    }

    for (i = 0; sStreamOverrides[i].seqID != SEQ_NONE; i++) {
        if (sStreamOverrides[i].seqID == seqID) {
            return &sStreamOverrides[i];
        }
    }

    return NULL;
}

static u32 SoundStream_GetPlayerBaseChannels(int playerID)
{
    const NNSSndArcPlayerInfo *info = NNS_SndArcGetPlayerInfo(playerID);

    if (info == NULL) {
        return 0;
    }

    return info->allocChBitFlag;
}

static int SoundStream_ClampVolume(int volume)
{
    if (volume < SOUND_VOLUME_MIN) {
        return SOUND_VOLUME_MIN;
    }

    if (volume > SOUND_VOLUME_MAX) {
        return SOUND_VOLUME_MAX;
    }

    return volume;
}

// Keeps the sequence players that share the stream's hardware channels from
// allocating them while a stream owns them. Only affects sequences started
// afterwards; the hardware channel lock taken by the stream itself covers
// anything already playing.
static void SoundStream_ReserveChannels(BOOL reserve)
{
    u32 mask = SOUND_STREAM_ALL_HW_CHANNELS;

    if (reserve == TRUE) {
        mask &= ~sStreamHWChannels;
    }

    sChannelsReserved = reserve;

    if (sFieldChannels != 0) {
        NNS_SndPlayerSetAllocatableChannel(PLAYER_FIELD, sFieldChannels & mask);
    }

    if (sFanfareChannels != 0) {
        NNS_SndPlayerSetAllocatableChannel(PLAYER_ME, sFanfareChannels & mask);
    }

    if (sBGMChannels != 0) {
        NNS_SndPlayerSetAllocatableChannel(PLAYER_BGM, sBGMChannels & mask);
    }
}

// A sequence that is overridden keeps running (so every vanilla check that
// asks the sound handle what is playing keeps working) but none of its tracks
// may allocate a hardware channel, so it is silent and costs no channels.
static void SoundStream_SetSequenceAudible(enum SoundHandleType handleType, BOOL audible)
{
    u32 channels = 0;

    if (audible == TRUE) {
        channels = (handleType == SOUND_HANDLE_TYPE_BGM) ? sBGMChannels : sFieldChannels;
    }

    NNS_SndPlayerSetTrackAllocatableChannel(SoundSystem_GetSoundHandle(handleType), SOUND_PLAYBACK_TRACK_ALL, channels);
}

static void SoundStream_ApplyVolume(void)
{
    int volume;
    int playerVolume;

    if (sStrmID == SOUND_STREAM_NONE || sPaused == TRUE) {
        return;
    }

    playerVolume = (sOwnerHandleType == SOUND_HANDLE_TYPE_BGM) ? sBGMPlayerVolume : sFieldPlayerVolume;

    volume = sTableVolume * sInitialVolume / SOUND_VOLUME_MAX;
    volume = volume * playerVolume / SOUND_VOLUME_MAX;

    NNS_SndArcStrmSetVolume(&sStreamHandle, SoundStream_ClampVolume(volume));
}

static void SoundStream_ApplyChannelVolumes(void)
{
    int i;

    for (i = 0; i < SOUND_STREAM_MAX_CHANNELS; i++) {
        if (sChannelVolumes[i] != SOUND_VOLUME_MAX) {
            NNS_SndArcStrmSetChannelVolume(&sStreamHandle, i, sChannelVolumes[i]);
        }
    }
}

static void SoundStream_ResetChannelVolumes(void)
{
    int i;

    for (i = 0; i < SOUND_STREAM_MAX_CHANNELS; i++) {
        sChannelVolumes[i] = SOUND_VOLUME_MAX;
    }
}

static BOOL SoundStream_Start(int strmID, u32 position)
{
    SoundStream_ReserveChannels(TRUE);

    if (NNS_SndArcStrmStart(&sStreamHandle, strmID, position) == FALSE) {
        SoundStream_ReserveChannels(FALSE);
        return FALSE;
    }

    return TRUE;
}

static void SoundStream_ClearState(void)
{
    sStrmID = SOUND_STREAM_NONE;
    sOwnerSeqID = SEQ_NONE;
    sPaused = FALSE;
    sPausedPosition = 0;
}

// A stream that is not looped frees its NNS player when it ends, which
// invalidates the handle. Forget it so the next request starts cleanly.
static void SoundStream_UpdateFinished(void)
{
    if (sStrmID == SOUND_STREAM_NONE || sPaused == TRUE) {
        return;
    }

    if (NNS_SndStrmHandleIsValid(&sStreamHandle) == FALSE) {
        if (sChannelsReserved == TRUE) {
            SoundStream_ReserveChannels(FALSE);
        }

        SoundStream_ClearState();
    }
}

// Must be called once at boot, right after NNS_SndArcPlayerSetup and before
// the first sound heap state is saved: the stream player buffers
// (512 * BLOCK_NUM(4) * channels bytes per stream player) are allocated here
// at the bottom of the sound heap so no heap state rollback ever frees them.
void SoundStream_Init(NNSSndHeapHandle heap)
{
    const NNSSndArcStrmPlayerInfo *strmPlayerInfo;
    int i;

    if (sInitialized == TRUE) {
        return;
    }

    NNS_SndArcStrmInit(SOUND_STREAM_THREAD_PRIORITY, heap);
    NNS_SndStrmHandleInit(&sStreamHandle);

    sStreamHWChannels = 0;
    strmPlayerInfo = NNS_SndArcGetStrmPlayerInfo(STRM_PLAYER_BGM);

    if (strmPlayerInfo != NULL) {
        for (i = 0; i < strmPlayerInfo->numChannels && i < (int)NELEMS(strmPlayerInfo->chNoList); i++) {
            sStreamHWChannels |= (1 << strmPlayerInfo->chNoList[i]);
        }
    }

    sFieldChannels = SoundStream_GetPlayerBaseChannels(PLAYER_FIELD);
    sFanfareChannels = SoundStream_GetPlayerBaseChannels(PLAYER_ME);
    sBGMChannels = SoundStream_GetPlayerBaseChannels(PLAYER_BGM);
    sChannelsReserved = FALSE;

    sTableVolume = SOUND_VOLUME_MAX;
    sInitialVolume = SOUND_VOLUME_MAX;
    sFieldPlayerVolume = SOUND_VOLUME_MAX;
    sBGMPlayerVolume = SOUND_VOLUME_MAX;
    sTargetVolume = SOUND_VOLUME_MAX;
    sOwnerHandleType = SOUND_HANDLE_TYPE_FIELD_BGM;
    SoundStream_ResetChannelVolumes();
    SoundStream_ClearState();

    sInitialized = TRUE;
}

BOOL SoundStream_HasOverride(u16 seqID)
{
    return SoundStream_FindOverride(seqID) != NULL;
}

// TRUE while a stream owns the BGM, including while it is paused for a fanfare
BOOL SoundStream_IsActive(void)
{
    SoundStream_UpdateFinished();
    return sStrmID != SOUND_STREAM_NONE;
}

// Starts the stream that overrides seqID. If the same stream is already
// audible (same BGM requested again, or two SEQs sharing one stream) it keeps
// playing without a restart. Does not touch the sequence itself.
BOOL SoundStream_PlayForSeq(u16 seqID)
{
    const SoundStreamOverride *entry;
    u8 playerID;

    if (sInitialized == FALSE) {
        return FALSE;
    }

    entry = SoundStream_FindOverride(seqID);
    if (entry == NULL) {
        return FALSE;
    }

    playerID = Sound_GetPlayerForSequence(seqID);
    if (playerID != PLAYER_FIELD && playerID != PLAYER_BGM) {
        return FALSE;
    }

    if (SoundStream_IsActive() == TRUE
        && sPaused == FALSE
        && sStrmID == entry->strmID
        && sTargetVolume > SOUND_VOLUME_MIN) {
        sOwnerSeqID = seqID;
        sOwnerHandleType = SoundSystem_GetSoundHandleTypeFromPlayerID(playerID);
        sTableVolume = entry->volume;
        sInitialVolume = SOUND_VOLUME_MAX;

        if (sTargetVolume != SOUND_VOLUME_MAX) {
            // The restarted sequence comes back at full volume, so does the stream
            sTargetVolume = SOUND_VOLUME_MAX;
            NNS_SndArcStrmMoveVolume(&sStreamHandle, SOUND_VOLUME_MAX, 0);
        }

        SoundStream_ApplyVolume();
        return TRUE;
    }

    SoundStream_Stop(0);
    SoundStream_ResetChannelVolumes();

    if (SoundStream_Start(entry->strmID, 0) == FALSE) {
        return FALSE;
    }

    sStrmID = entry->strmID;
    sOwnerSeqID = seqID;
    sOwnerHandleType = SoundSystem_GetSoundHandleTypeFromPlayerID(playerID);
    sPaused = FALSE;
    sPausedPosition = 0;
    sTableVolume = entry->volume;
    sInitialVolume = SOUND_VOLUME_MAX;
    sTargetVolume = SOUND_VOLUME_MAX;

    SoundStream_ApplyVolume();
    return TRUE;
}

void SoundStream_Stop(int fadeFrames)
{
    if (sStrmID == SOUND_STREAM_NONE) {
        return;
    }

    if (sPaused == FALSE) {
        if (fadeFrames < 0) {
            fadeFrames = 0;
        }

        // With fadeFrames > 0 NNS keeps the hardware channels locked until
        // the fade-out ends, so un-reserving them right away is safe.
        NNS_SndArcStrmStop(&sStreamHandle, fadeFrames);
    }

    if (sChannelsReserved == TRUE) {
        SoundStream_ReserveChannels(FALSE);
    }

    SoundStream_ClearState();
}

void SoundStream_MoveVolume(int volume, int frames)
{
    if (sStrmID == SOUND_STREAM_NONE) {
        return;
    }

    if (frames < 0) {
        frames = 0;
    }

    sTargetVolume = SoundStream_ClampVolume(volume);

    if (sPaused == FALSE) {
        NNS_SndArcStrmMoveVolume(&sStreamHandle, sTargetVolume, frames);
    }
}

// Per-channel volume (0-127) for future layered (4-channel) streams
void SoundStream_SetChannelVolume(int channel, int volume)
{
    if (channel < 0 || channel >= SOUND_STREAM_MAX_CHANNELS) {
        return;
    }

    sChannelVolumes[channel] = SoundStream_ClampVolume(volume);

    if (sStrmID != SOUND_STREAM_NONE && sPaused == FALSE) {
        NNS_SndArcStrmSetChannelVolume(&sStreamHandle, channel, sChannelVolumes[channel]);
    }
}

// NNS streams cannot pause: remember the position and stop. The hardware
// channels are released so the fanfare can use them.
void SoundStream_PauseForFanfare(void)
{
    if (SoundStream_IsActive() == FALSE || sPaused == TRUE) {
        return;
    }

    sPausedPosition = NNS_SndArcStrmGetCurrentPlayingPos(&sStreamHandle);
    NNS_SndArcStrmStop(&sStreamHandle, 0);

    if (sChannelsReserved == TRUE) {
        SoundStream_ReserveChannels(FALSE);
    }

    sPaused = TRUE;
}

// Restarts the paused stream from the saved position (snaps to the ADPCM
// block that contains it). If that fails the owner sequence is made audible
// again, so the player hears the sequenced version instead of silence.
void SoundStream_ResumeAfterFanfare(int fadeInFrames)
{
    if (sStrmID == SOUND_STREAM_NONE || sPaused == FALSE) {
        return;
    }

    sPaused = FALSE;

    if (SoundStream_Start(sStrmID, sPausedPosition) == FALSE) {
        SoundStream_SetSequenceAudible(sOwnerHandleType, TRUE);
        SoundStream_ClearState();
        return;
    }

    sPausedPosition = 0;

    if (fadeInFrames > 0) {
        NNS_SndArcStrmMoveVolume(&sStreamHandle, SOUND_VOLUME_MIN, 0);
        NNS_SndArcStrmMoveVolume(&sStreamHandle, sTargetVolume, fadeInFrames);
    } else if (sTargetVolume != SOUND_VOLUME_MAX) {
        NNS_SndArcStrmMoveVolume(&sStreamHandle, sTargetVolume, 0);
    }

    SoundStream_ApplyVolume();
    SoundStream_ApplyChannelVolumes();
}
