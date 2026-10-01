#include "sound_stream.h"

#include <nitro.h>
#include <string.h>

#include "generated/sdat.h"

static BOOL sInitialized;

// Must be called once at boot, right after NNS_SndArcPlayerSetup and before
// the first sound heap state is saved: the stream player buffers
// (512 * BLOCK_NUM(4) * channels bytes per stream player) are allocated here
// at the bottom of the sound heap so no heap state rollback ever frees them.
void SoundStream_Init(NNSSndHeapHandle heap)
{
    if (sInitialized == TRUE) {
        return;
    }

    NNS_SndArcStrmInit(SOUND_STREAM_THREAD_PRIORITY, heap);
    sInitialized = TRUE;
}
