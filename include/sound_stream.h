#ifndef POKEPLATINUM_SOUND_STREAM_H
#define POKEPLATINUM_SOUND_STREAM_H

#include <nnsys.h>

// Priority of the NitroSystem stream (file read + ADPCM decode) thread.
// Higher than the main/launcher thread (OS_THREAD_LAUNCHER_PRIORITY = 16) so
// buffer refills can preempt long main-thread loads, lower than the CARD
// thread (CARD_THREAD_PRIORITY_DEFAULT = 4) whose reads it waits on.
#define SOUND_STREAM_THREAD_PRIORITY 10

void SoundStream_Init(NNSSndHeapHandle heap);

#endif // POKEPLATINUM_SOUND_STREAM_H
