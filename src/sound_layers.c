#include "sound_layers.h"

#include <nitro.h>

#include "sound.h"
#include "sound_system.h"

// Battle themes all play on PLAYER_BGM, so the layers only ever touch that player's tracks.
#define LAYER_SOUND_HANDLE SOUND_HANDLE_TYPE_BGM

#define LAYER_MAX_TRACKS   16
#define LAYER_VOLUME_MAX   SOUND_VOLUME_MAX
// Volume change per SoundLayers_Update call: a full fade takes 43 frames, about 0.7 s at 60 fps
#define LAYER_FADE_STEP    3

#define LAYER_TRACK(n) (1 << (n))

typedef struct BGMLayerTracks {
    u16 trackMask; // Sequence tracks that make up the layer
    u8 volume; // Track volume (0-127, as for NNS_SndPlayerSetTrackVolume) while the layer is on
} BGMLayerTracks;

typedef struct BGMLayerSong {
    u16 seqID;
    BGMLayerTracks layers[BGM_LAYER_COUNT];
} BGMLayerSong;

// Layer tracks keep their normal volume inside the sequence and are held silent from code with
// NNS_SndPlayerSetTrackVolume, which can only attenuate. The authored layer tracks also rest through
// the song's intro, so a few frames between the song starting and SoundLayers_Reset/Update silencing
// them can't be heard.
static const BGMLayerSong sLayerSongs[] = {
    {
        // SEQ_BA_POKE: track 11 is a percussion ostinato (16th-note hi-hats with tom fills) that
        // starts at the loop point. All three layers bring in the same track.
        .seqID = SEQ_BATTLE_WILD_POKEMON,
        .layers = {
            [BGM_LAYER_LOW_HP] = { LAYER_TRACK(11), LAYER_VOLUME_MAX },
            [BGM_LAYER_MEGA] = { LAYER_TRACK(11), LAYER_VOLUME_MAX },
            [BGM_LAYER_TOTEM_ALLY] = { LAYER_TRACK(11), LAYER_VOLUME_MAX },
        },
    },
};

static const BGMLayerSong *sSong = NULL; // Table entry for sSeqID, NULL if the song has no layers
static int sSeqID = -1; // Song the layer track volumes were last applied to
static u8 sLayersOn = 0; // Bitmask of enum BGMLayer
static u8 sTrackVolumes[LAYER_MAX_TRACKS];

static const BGMLayerSong *SoundLayers_FindSong(int seqID)
{
    int i;

    for (i = 0; i < NELEMS(sLayerSongs); i++) {
        if (sLayerSongs[i].seqID == seqID) {
            return &sLayerSongs[i];
        }
    }

    return NULL;
}

static u16 SoundLayers_GetSongTrackMask(const BGMLayerSong *song)
{
    int layer;
    u16 mask = 0;

    for (layer = 0; layer < BGM_LAYER_COUNT; layer++) {
        mask |= song->layers[layer].trackMask;
    }

    return mask;
}

// The loudest volume asked for by any active layer that uses the track
static int SoundLayers_GetTargetVolume(const BGMLayerSong *song, int track)
{
    int layer;
    int volume = 0;

    for (layer = 0; layer < BGM_LAYER_COUNT; layer++) {
        if ((sLayersOn & (1 << layer))
            && (song->layers[layer].trackMask & LAYER_TRACK(track))
            && song->layers[layer].volume > volume) {
            volume = song->layers[layer].volume;
        }
    }

    return volume;
}

// Follows the song on the BGM player. A newly started song begins with every track at full
// volume, so its layer tracks are silenced straight away. Returns TRUE if the song has layers.
static BOOL SoundLayers_SyncSong(void)
{
    int i;
    u16 mask;
    NNSSndHandle *handle = SoundSystem_GetSoundHandle(LAYER_SOUND_HANDLE);
    int seqID = Sound_GetSequenceIDFromSoundHandle(handle);

    if (seqID != sSeqID) {
        sSeqID = seqID;
        sSong = SoundLayers_FindSong(seqID);

        if (sSong != NULL) {
            for (i = 0; i < LAYER_MAX_TRACKS; i++) {
                sTrackVolumes[i] = 0;
            }

            mask = SoundLayers_GetSongTrackMask(sSong);

            if (mask != 0) {
                NNS_SndPlayerSetTrackVolume(handle, mask, 0);
            }
        }
    }

    return sSong != NULL;
}

void SoundLayers_Reset(void)
{
    sLayersOn = 0;

    // Forget the current song so it is silenced again even if the same song was just restarted
    sSeqID = -1;
    sSong = NULL;

    SoundLayers_SyncSong();
}

void SoundLayers_Set(enum BGMLayer layer, BOOL on)
{
    if ((u32)layer >= BGM_LAYER_COUNT) {
        return;
    }

    if (on) {
        sLayersOn |= (1 << layer);
    } else {
        sLayersOn &= ~(1 << layer);
    }
}

void SoundLayers_Update(void)
{
    int track;
    int volume;
    int target;
    u16 mask;
    NNSSndHandle *handle;

    // TODO: when a layered stream replaces the battle BGM (SoundStream_IsActive() in sound_stream.h),
    // fade its layer channels with SoundStream_SetChannelVolume(ch, vol) instead of sequence tracks.
    if (SoundLayers_SyncSong() == FALSE) {
        return;
    }

    handle = SoundSystem_GetSoundHandle(LAYER_SOUND_HANDLE);
    mask = SoundLayers_GetSongTrackMask(sSong);

    for (track = 0; track < LAYER_MAX_TRACKS; track++) {
        if ((mask & LAYER_TRACK(track)) == 0) {
            continue;
        }

        volume = sTrackVolumes[track];
        target = SoundLayers_GetTargetVolume(sSong, track);

        if (volume == target) {
            continue;
        }

        if (volume < target) {
            volume += LAYER_FADE_STEP;

            if (volume > target) {
                volume = target;
            }
        } else {
            volume -= LAYER_FADE_STEP;

            if (volume < target) {
                volume = target;
            }
        }

        sTrackVolumes[track] = volume;
        NNS_SndPlayerSetTrackVolume(handle, LAYER_TRACK(track), volume);
    }
}
