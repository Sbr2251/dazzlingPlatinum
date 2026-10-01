#ifndef POKEPLATINUM_SOUND_STREAM_H
#define POKEPLATINUM_SOUND_STREAM_H

#include <nnsys.h>

// Priority of the NitroSystem stream (file read + ADPCM decode) thread.
// Higher than the main/launcher thread (OS_THREAD_LAUNCHER_PRIORITY = 16) so
// buffer refills can preempt long main-thread loads, lower than the CARD
// thread (CARD_THREAD_PRIORITY_DEFAULT = 4) whose reads it waits on.
#define SOUND_STREAM_THREAD_PRIORITY 10

// Streamed BGM: an override table in sound_stream.c maps SEQ_* IDs to STRM_*
// IDs. Scripts and map headers keep requesting SEQ_* IDs; the sequence is
// still started (so all bookkeeping that reads the sound handles is
// unchanged) but is kept silent while the stream plays in its place.

void SoundStream_Init(NNSSndHeapHandle heap);

BOOL SoundStream_HasOverride(u16 seqID);
BOOL SoundStream_IsActive(void);
BOOL SoundStream_PlayForSeq(u16 seqID);
void SoundStream_Stop(int fadeFrames);
void SoundStream_MoveVolume(int volume, int frames);
void SoundStream_SetChannelVolume(int channel, int volume);
void SoundStream_PauseForFanfare(void);
void SoundStream_ResumeAfterFanfare(int fadeInFrames);

#endif // POKEPLATINUM_SOUND_STREAM_H
