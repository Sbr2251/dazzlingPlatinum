#ifndef POKEPLATINUM_HEAP_H
#define POKEPLATINUM_HEAP_H

#include <nnsys.h>

#include "constants/heap.h"

typedef struct HeapParam {
    u32 size; // maximum size of the heap
    OSArenaId arena; // where to allocate the heap from
} HeapParam;

void Heap_InitSystem(const HeapParam *templates, u32 nTemplates, u32 totalNumHeaps, u32 preSize);
BOOL Heap_Create(enum HeapID parent, enum HeapID child, u32 size);
BOOL Heap_CreateAtEnd(enum HeapID parent, enum HeapID child, u32 size);
void Heap_Destroy(enum HeapID heapID);
void *Heap_Alloc(u32 heapID, u32 size);
void *Heap_AllocAtEnd(u32 heapID, u32 size);
void Heap_Free(void *ptr);
void Heap_FreeExplicit(u32 heapID, void *ptr);
u32 HeapExp_FndGetTotalFreeSize(u32 heapID);
void HeapExp_FndInitAllocator(NNSFndAllocator *pAllocator, u32 heapID, int alignment);
void Heap_Realloc(void *ptr, u32 newSize);
BOOL GF_heap_c_dummy_return_true(u32 heapID);

// --- Port heap telemetry (lane heap) -------------------------------------
// Heap sizes are scaled by HEAP_PORT_SCALE on the port (see heap.c); stats
// below report the scaled (effective) sizes. `peak` is the peak-ever used
// bytes for that HeapID since boot (Heap_InitSystem clears it); `used` is
// size minus the exp heap's current total free size, so it also counts
// allocations made through NNS allocators that bypass Heap_Alloc.
typedef struct HeapStats {
    u32 id;
    u32 size;
    u32 used;
    u32 peak;
    u32 peakSize; // the heap's size when its peak was recorded (a destroyed
                  // heap reports size 0 but keeps peak/peakSize, so headroom
                  // can still be computed as peakSize/peak)
    u32 blocks; // live Heap_Alloc/Heap_AllocAtEnd blocks (see numMemBlocks)
    const char *name; // e.g. "BATTLE", or NULL for unnamed HEAP_ID_<n> slots
} HeapStats;

void Heap_UpdatePeaks(void);
BOOL Heap_GetStats(u32 heapID, HeapStats *out);
u32 Heap_GetNumHeaps(void);
const char *Heap_GetHeapName(u32 heapID);

#endif // POKEPLATINUM_HEAP_H
