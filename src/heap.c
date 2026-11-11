#include "heap.h"

#include <nitro.h>
#include <string.h>

#include "comm_manager.h"
#include "error_message_reset.h"

// Port heap scaling (lane heap): on the PC port every heap carved by
// Heap_InitSystem / Heap_Create is HEAP_PORT_SCALE times its DS size.
// Parent and child scale together, so nesting ratios, AllocAtEnd order and
// relative layout are preserved, and no call site needs a per-site factor
// (the pre-existing per-site *2 hacks on 64-bit simply become *8 —
// wasteful but safe). DS/ARM builds keep scale 1 (DS behaviour untouched).
// The scaled roots only fit because libntr's emulated main RAM grew with
// them (8 MB -> 32 MB); heap pointers stay inside emulated RAM, so DMA/GX
// address translation is unchanged (host-malloc backing would break it).
#ifdef SDK_PORT
#define HEAP_PORT_SCALE 4
#else
#define HEAP_PORT_SCALE 1
#endif

typedef struct HeapInfo {
    NNSFndHeapHandle *heapHandles;
    NNSFndHeapHandle *parentHeapHandles;
    void **subHeapRawPtrs;
    u16 *numMemBlocks;
    u32 *heapSizes; // effective (scaled) size per HeapID, 0 when not live
    u32 *heapPeaks; // peak-ever used bytes per HeapID since Heap_InitSystem
    u32 *heapPeakSizes; // heap size when the peak was recorded
    u8 *heapIdxs;
    u16 totalNumHeaps;
    u16 nTemplates;
    u16 maxHeaps;
    u16 unallocatedHeapID;
} HeapInfo;

typedef struct MemoryBlock {
    u8 filler_00[12];
    u32 heapID : 8;
    u32 filler_0D : 24;
} MemoryBlock;

static HeapInfo sHeapInfo;

static BOOL CreateHeapInternal(enum HeapID parent, enum HeapID child, u32 size, s32 alignment);

void Heap_InitSystem(const HeapParam *templates, u32 nTemplates, u32 totalNumHeaps, u32 preSize)
{
    void *ptr;
    u32 i;
    u32 usableHeaps = nTemplates + 24;

    if (totalNumHeaps < usableHeaps) {
        totalNumHeaps = usableHeaps;
    }

    if (preSize != 0) {
        // force align
        while (preSize % 4 != 0) {
            preSize++;
        }
        OS_AllocFromMainArenaLo(preSize, 4);
    }

    sHeapInfo.heapHandles = OS_AllocFromMainArenaLo(
        (usableHeaps + 1) * sizeof(NNSFndHeapHandle)
            + usableHeaps * sizeof(NNSFndHeapHandle)
            + usableHeaps * sizeof(void *)
            + totalNumHeaps * sizeof(u16)
            + totalNumHeaps * sizeof(u32) * 3
            + totalNumHeaps,
        4);
    sHeapInfo.parentHeapHandles = sHeapInfo.heapHandles + (usableHeaps + 1);
    sHeapInfo.subHeapRawPtrs = (void **)(sHeapInfo.parentHeapHandles + usableHeaps);
    sHeapInfo.numMemBlocks = (u16 *)(sHeapInfo.subHeapRawPtrs + usableHeaps);
    sHeapInfo.heapSizes = (u32 *)(sHeapInfo.numMemBlocks + totalNumHeaps);
    sHeapInfo.heapPeaks = sHeapInfo.heapSizes + totalNumHeaps;
    sHeapInfo.heapPeakSizes = sHeapInfo.heapPeaks + totalNumHeaps;
    sHeapInfo.heapIdxs = (u8 *)(sHeapInfo.heapPeakSizes + totalNumHeaps);
    sHeapInfo.totalNumHeaps = (u16)totalNumHeaps;
    sHeapInfo.nTemplates = (u16)nTemplates;
    sHeapInfo.unallocatedHeapID = (u16)usableHeaps;
    sHeapInfo.maxHeaps = (u16)usableHeaps;

    for (i = 0; i < nTemplates; i++) {
        // APPLICATION is the parent of nearly every other heap, so its
        // "used" is mostly child reservations, which scale with the child
        // factor: a uniform factor leaves its headroom ratio unchanged
        // (measured 89% used at 4x). Give it twice the child factor so its
        // headroom vs the sum of live child reservations is >= 2x.
        u32 scale = HEAP_PORT_SCALE * (i == (u32)HEAP_ID_APPLICATION ? 2 : 1);
        u32 effSize = templates[i].size * scale;
        switch (templates[i].arena) {
        case OS_ARENA_MAIN:
        default:
            ptr = OS_AllocFromMainArenaLo(effSize, 4);
            break;
        case OS_ARENA_MAINEX:
            ptr = OS_AllocFromMainExArenaHi(effSize, 4);
            break;
        }

        if (ptr != NULL) {
            sHeapInfo.heapHandles[i] = NNS_FndCreateExpHeap(ptr, effSize);
            sHeapInfo.heapIdxs[i] = (u8)i;
            sHeapInfo.heapSizes[i] = effSize;
        } else {
            GF_ASSERT(FALSE);
        }
    }

    for (i = nTemplates; i < usableHeaps + 1; i++) {
        sHeapInfo.heapHandles[i] = NNS_FND_HEAP_INVALID_HANDLE;
        sHeapInfo.heapIdxs[i] = (u8)sHeapInfo.unallocatedHeapID;
    }

    while (i < totalNumHeaps) {
        sHeapInfo.heapIdxs[i++] = (u8)sHeapInfo.unallocatedHeapID;
    }

    for (i = 0; i < totalNumHeaps; i++) {
        sHeapInfo.numMemBlocks[i] = 0;
        if (i >= nTemplates) {
            sHeapInfo.heapSizes[i] = 0;
        }
        sHeapInfo.heapPeaks[i] = 0;
        sHeapInfo.heapPeakSizes[i] = 0;
    }
}

static s32 FindFirstAvailableHeapHandle(void)
{
    s32 i;

    for (i = sHeapInfo.nTemplates; i < sHeapInfo.maxHeaps; i++) {
        if (sHeapInfo.heapHandles[i] == NNS_FND_HEAP_INVALID_HANDLE) {
            return i;
        }
    }

    return -1;
}

BOOL Heap_Create(enum HeapID parent, enum HeapID child, u32 size)
{
    return CreateHeapInternal(parent, child, size, 4);
}

BOOL Heap_CreateAtEnd(enum HeapID parent, enum HeapID child, u32 size)
{
    return CreateHeapInternal(parent, child, size, -4);
}

static BOOL CreateHeapInternal(enum HeapID parent, enum HeapID child, u32 size, s32 alignment)
{
    GF_ASSERT(OS_GetProcMode() != OS_PROCMODE_IRQ);

    u8 *ptr = sHeapInfo.heapIdxs;
    if (sHeapInfo.unallocatedHeapID == ptr[child]) {
        NNSFndHeapHandle parentHeap = sHeapInfo.heapHandles[ptr[parent]];
        if (parentHeap != NNS_FND_HEAP_INVALID_HANDLE) {
            u32 effSize = size * HEAP_PORT_SCALE;
            void *newHeapAddr = NNS_FndAllocFromExpHeapEx(parentHeap, effSize, alignment);
            if (newHeapAddr != NULL) {
                s32 i = FindFirstAvailableHeapHandle();
                if (i >= 0) {
                    sHeapInfo.heapHandles[i] = NNS_FndCreateExpHeap(newHeapAddr, effSize);

                    if (sHeapInfo.heapHandles[i] != NNS_FND_HEAP_INVALID_HANDLE) {
                        sHeapInfo.parentHeapHandles[i] = parentHeap;
                        sHeapInfo.subHeapRawPtrs[i] = newHeapAddr;
                        sHeapInfo.heapIdxs[child] = (u8)i;
                        if ((u32)child < sHeapInfo.totalNumHeaps) {
                            sHeapInfo.heapSizes[child] = effSize;
                        }

                        return TRUE;
                    } else {
                        GF_ASSERT(FALSE);
                    }
                } else {
                    GF_ASSERT(FALSE);
                }
            } else {
                GF_ASSERT(FALSE);
            }
        } else {
            GF_ASSERT(FALSE);
        }
    } else {
        GF_ASSERT(FALSE);
    }
    return FALSE;
}

void Heap_Destroy(enum HeapID heapID)
{
    GF_ASSERT(OS_GetProcMode() != OS_PROCMODE_IRQ);

    NNSFndHeapHandle handle = sHeapInfo.heapHandles[sHeapInfo.heapIdxs[heapID]];

    if (handle != NNS_FND_HEAP_INVALID_HANDLE) {
        NNS_FndDestroyExpHeap(handle);

        u8 index = sHeapInfo.heapIdxs[heapID];
        NNSFndHeapHandle parentHeap = sHeapInfo.parentHeapHandles[index];
        void *childRaw = sHeapInfo.subHeapRawPtrs[index];
        if (parentHeap != NNS_FND_HEAP_INVALID_HANDLE && childRaw != NULL) {
            NNS_FndFreeToExpHeap(parentHeap, childRaw);
        } else {
            GF_ASSERT(FALSE);
        }

        sHeapInfo.heapHandles[sHeapInfo.heapIdxs[heapID]] = NULL;
        sHeapInfo.parentHeapHandles[sHeapInfo.heapIdxs[heapID]] = NULL;
        sHeapInfo.subHeapRawPtrs[sHeapInfo.heapIdxs[heapID]] = NULL;

        // Peak is peak-ever: keep it after destroy so headroom reports
        // still show the worst case this HeapID reached this boot.
        if ((u32)heapID < sHeapInfo.totalNumHeaps) {
            sHeapInfo.heapSizes[heapID] = 0;
        }
        sHeapInfo.heapIdxs[heapID] = (u8)sHeapInfo.unallocatedHeapID;
    }
}

static void *AllocFromHeapInternal(NNSFndHeapHandle heap, u32 size, s32 alignment, enum HeapID heapID)
{
    GF_ASSERT(heap != NNS_FND_HEAP_INVALID_HANDLE);

    OSIntrMode intrMode = OS_DisableInterrupts();
    size += sizeof(MemoryBlock);
    void *ptr = NNS_FndAllocFromExpHeapEx(heap, size, alignment);

    OS_RestoreInterrupts(intrMode);
    if (ptr != NULL) {
        ((MemoryBlock *)ptr)->heapID = heapID;

        ptr += sizeof(MemoryBlock);
    }

    return ptr;
}

static void AllocFail(void)
{
    if (CommManager_IsInitialized()) {
        ErrorMessageReset_PrintErrorAndReset();
    }
}

void *Heap_Alloc(u32 heapID, u32 size)
{
    void *ptr = NULL;

    if ((u32)heapID < sHeapInfo.totalNumHeaps) {
        u8 index = sHeapInfo.heapIdxs[heapID];
        ptr = AllocFromHeapInternal(sHeapInfo.heapHandles[index], size, 4, heapID);
    }

    if (ptr != NULL) {
        sHeapInfo.numMemBlocks[heapID]++;
    } else {
        AllocFail();
    }

    return ptr;
}

void *Heap_AllocAtEnd(u32 heapID, u32 size)
{
    void *ptr = NULL;

    if ((u32)heapID < sHeapInfo.totalNumHeaps) {
        u8 index = sHeapInfo.heapIdxs[heapID];
        ptr = AllocFromHeapInternal(sHeapInfo.heapHandles[index], size, -4, heapID);
    }

    if (ptr != NULL) {
        sHeapInfo.numMemBlocks[heapID]++;
    } else {
        AllocFail();
    }

    return ptr;
}

void Heap_Free(void *ptr)
{
    ptr -= sizeof(MemoryBlock);
    enum HeapID heapID = (enum HeapID)((MemoryBlock *)ptr)->heapID;

    if ((u32)heapID < sHeapInfo.totalNumHeaps) {
        u8 index = sHeapInfo.heapIdxs[heapID];
        NNSFndHeapHandle heap = sHeapInfo.heapHandles[index];

        GF_ASSERT(heap != NNS_FND_HEAP_INVALID_HANDLE);

        if (sHeapInfo.numMemBlocks[heapID] == 0) {
            GF_heap_c_dummy_return_true(heapID);
        }

        GF_ASSERT(sHeapInfo.numMemBlocks[heapID] != 0);

        sHeapInfo.numMemBlocks[heapID]--;

        OSIntrMode intrMode = OS_DisableInterrupts();
        NNS_FndFreeToExpHeap(heap, ptr);
        OS_RestoreInterrupts(intrMode);
        return;
    }

    GF_ASSERT(FALSE);
}

void Heap_FreeExplicit(u32 heapID, void *ptr)
{
    GF_ASSERT(OS_GetProcMode() != OS_PROCMODE_IRQ);

    if ((u32)heapID < sHeapInfo.totalNumHeaps) {
        u8 index = sHeapInfo.heapIdxs[heapID];
        NNSFndHeapHandle heap = sHeapInfo.heapHandles[index];

        GF_ASSERT(heap != NNS_FND_HEAP_INVALID_HANDLE);

        ptr -= sizeof(MemoryBlock);
        GF_ASSERT(((MemoryBlock *)ptr)->heapID == heapID);

        NNS_FndFreeToExpHeap(heap, ptr);
        GF_ASSERT(sHeapInfo.numMemBlocks[heapID] != 0);
        sHeapInfo.numMemBlocks[heapID]--;
        return;
    }

    GF_ASSERT(FALSE);
}

u32 HeapExp_FndGetTotalFreeSize(u32 heapID)
{
    if ((u32)heapID < sHeapInfo.totalNumHeaps) {
        u8 index = sHeapInfo.heapIdxs[heapID];
        return NNS_FndGetTotalFreeSizeForExpHeap(sHeapInfo.heapHandles[index]);
    }

    GF_ASSERT(FALSE);
    return 0;
}

void HeapExp_FndInitAllocator(NNSFndAllocator *pAllocator, u32 heapID, int alignment)
{
    if ((u32)heapID < sHeapInfo.totalNumHeaps) {
        u8 index = sHeapInfo.heapIdxs[heapID];
        NNS_FndInitAllocatorForExpHeap(pAllocator, sHeapInfo.heapHandles[index], alignment);
        return;
    }

    GF_ASSERT(FALSE);
}

void Heap_Realloc(void *ptr, u32 newSize)
{
    GF_ASSERT(OS_GetProcMode() != OS_PROCMODE_IRQ);

    newSize += sizeof(MemoryBlock);
    ptr -= sizeof(MemoryBlock);

    if (NNS_FndGetSizeForMBlockExpHeap(ptr) >= newSize) {
        u32 heapID = ((MemoryBlock *)ptr)->heapID;
        u8 index = sHeapInfo.heapIdxs[heapID];

        NNS_FndResizeForMBlockExpHeap(sHeapInfo.heapHandles[index], ptr, newSize);
        return;
    }
    GF_ASSERT(FALSE);
}

BOOL GF_heap_c_dummy_return_true(u32 heapID)
{
    return TRUE;
}

// --- Heap telemetry -------------------------------------------------------

static const char *const sHeapNames[HEAP_ID_MAX] = {
    [HEAP_ID_SYSTEM] = "SYSTEM",
    [HEAP_ID_SAVE] = "SAVE",
    [HEAP_ID_DEBUG] = "DEBUG",
    [HEAP_ID_APPLICATION] = "APPLICATION",
    [HEAP_ID_FIELD1] = "FIELD1",
    [HEAP_ID_BATTLE] = "BATTLE",
    [HEAP_ID_BAG] = "BAG",
    [HEAP_ID_POKETCH_MAIN] = "POKETCH_MAIN",
    [HEAP_ID_POKETCH_APP] = "POKETCH_APP",
    [HEAP_ID_BOX_DATA] = "BOX_DATA",
    [HEAP_ID_BOX_GRAPHICS] = "BOX_GRAPHICS",
    [HEAP_ID_FIELD2] = "FIELD2",
    [HEAP_ID_PARTY_MENU] = "PARTY_MENU",
    [HEAP_ID_COMMUNICATION] = "COMMUNICATION",
    [HEAP_ID_TOWN_MAP] = "TOWN_MAP",
    [HEAP_ID_NAMING_SCREEN_APP] = "NAMING_SCREEN_APP",
    [HEAP_ID_POKEMON_SUMMARY_SCREEN] = "POKEMON_SUMMARY_SCREEN",
    [HEAP_ID_TRAINER_CASE] = "TRAINER_CASE",
    [HEAP_ID_TRADE_ROOM] = "TRADE_ROOM",
    [HEAP_ID_MINING] = "MINING",
    [HEAP_ID_DISTORTION_WORLD_WARP] = "DISTORTION_WORLD_WARP",
    [HEAP_ID_FIELD3] = "FIELD3",
    [HEAP_ID_UNDERGROUND] = "UNDERGROUND",
    [HEAP_ID_BERRY_TAG] = "BERRY_TAG",
    [HEAP_ID_POKEDEX] = "POKEDEX",
    [HEAP_ID_OPTIONS_MENU] = "OPTIONS_MENU",
    [HEAP_ID_DRAWING] = "DRAWING",
    [HEAP_ID_MAIL] = "MAIL",
    [HEAP_ID_MAIL_VIEWER] = "MAIL_VIEWER",
    [HEAP_ID_JOURNAL] = "JOURNAL",
    [HEAP_ID_POFFIN_CASE] = "POFFIN_CASE",
    [HEAP_ID_POFFIN_MANAGER] = "POFFIN_MANAGER",
    [HEAP_ID_POFFIN_CUTSCENE] = "POFFIN_CUTSCENE",
    [HEAP_ID_CHOOSE_STARTER_APP] = "CHOOSE_STARTER_APP",
    [HEAP_ID_NINTENDO_WFC] = "NINTENDO_WFC",
    [HEAP_ID_POFFIN_BERRY_SELECTION] = "POFFIN_BERRY_SELECTION",
    [HEAP_ID_TRADE_SEQUENCE] = "TRADE_SEQUENCE",
    [HEAP_ID_TRADE_SEQUENCE_PHASE] = "TRADE_SEQUENCE_PHASE",
    [HEAP_ID_PC_HALL_OF_FAME] = "PC_HALL_OF_FAME",
    [HEAP_ID_HALL_OF_FAME] = "HALL_OF_FAME",
    [HEAP_ID_MOVE_REMINDER] = "MOVE_REMINDER",
    [HEAP_ID_EGG_HATCH] = "EGG_HATCH",
    [HEAP_ID_BOAT_CUTSCENE] = "BOAT_CUTSCENE",
    [HEAP_ID_EVOLUTION] = "EVOLUTION",
    [HEAP_ID_BATTLE_TOWER_RECORDS_APP] = "BATTLE_TOWER_RECORDS_APP",
    [HEAP_ID_END_CREDITS] = "END_CREDITS",
    [HEAP_ID_GAME_START] = "GAME_START",
    [HEAP_ID_MIGRATE_FROM_GBA] = "MIGRATE_FROM_GBA",
    [HEAP_ID_RANKINGS_MACHINE] = "RANKINGS_MACHINE",
    [HEAP_ID_MAIN_MENU] = "MAIN_MENU",
    [HEAP_ID_ROWAN_INTRO] = "ROWAN_INTRO",
    [HEAP_ID_ROWAN_INTRO_TV] = "ROWAN_INTRO_TV",
    [HEAP_ID_DIPLOMA] = "DIPLOMA",
    [HEAP_ID_RANGER_LINK] = "RANGER_LINK",
    [HEAP_ID_MYSTERY_GIFT_APP] = "MYSTERY_GIFT_APP",
    [HEAP_ID_WONDER_CARDS_APP] = "WONDER_CARDS_APP",
    [HEAP_ID_NETWORK_ICON] = "NETWORK_ICON",
    [HEAP_ID_BATTLE_FACTORY_APP] = "BATTLE_FACTORY_APP",
    [HEAP_ID_BATTLE_HALL_APP] = "BATTLE_HALL_APP",
    [HEAP_ID_BATTLE_CASTLE_APP] = "BATTLE_CASTLE_APP",
    [HEAP_ID_BATTLE_ARCADE_APP] = "BATTLE_ARCADE_APP",
    [HEAP_ID_FRONTIER_RECORD_APP] = "FRONTIER_RECORD_APP",
    [HEAP_ID_SCRATCH_OFF_CARD_APP] = "SCRATCH_OFF_CARD_APP",
    [HEAP_ID_LIBRARY_TV] = "LIBRARY_TV",
    [HEAP_ID_PARTY_MENU1] = "PARTY_MENU1",
    [HEAP_ID_PARTY_MENU2] = "PARTY_MENU2",
};

const char *Heap_GetHeapName(u32 heapID)
{
    if (heapID < (u32)HEAP_ID_MAX) {
        return sHeapNames[heapID];
    }
    return NULL;
}

u32 Heap_GetNumHeaps(void)
{
    return sHeapInfo.totalNumHeaps;
}

static u32 Heap_UsedFor(u32 heapID)
{
    if (heapID >= sHeapInfo.totalNumHeaps) {
        return 0;
    }
    u32 size = sHeapInfo.heapSizes[heapID];
    if (size == 0) {
        return 0;
    }
    u8 index = sHeapInfo.heapIdxs[heapID];
    NNSFndHeapHandle handle = (index < sHeapInfo.maxHeaps) ? sHeapInfo.heapHandles[index] : NNS_FND_HEAP_INVALID_HANDLE;
    if (handle == NNS_FND_HEAP_INVALID_HANDLE || handle == NULL) {
        return 0;
    }
    u32 freeSize = NNS_FndGetTotalFreeSizeForExpHeap(handle);
    return (freeSize >= size) ? 0 : (size - freeSize);
}

void Heap_UpdatePeaks(void)
{
    if (sHeapInfo.heapHandles == NULL || sHeapInfo.totalNumHeaps == 0) {
        return;
    }
    for (u32 heapID = 0; heapID < sHeapInfo.totalNumHeaps; heapID++) {
        if (sHeapInfo.heapSizes[heapID] == 0) {
            continue;
        }
        u32 used = Heap_UsedFor(heapID);
        if (used > sHeapInfo.heapPeaks[heapID]) {
            sHeapInfo.heapPeaks[heapID] = used;
            sHeapInfo.heapPeakSizes[heapID] = sHeapInfo.heapSizes[heapID];
        }
    }
}

BOOL Heap_GetStats(u32 heapID, HeapStats *out)
{
    if (out == NULL || heapID >= sHeapInfo.totalNumHeaps) {
        return FALSE;
    }
    out->id = heapID;
    out->size = sHeapInfo.heapSizes[heapID];
    out->used = Heap_UsedFor(heapID);
    out->peak = sHeapInfo.heapPeaks[heapID];
    if (out->peak < out->used) {
        out->peak = out->used;
        sHeapInfo.heapPeaks[heapID] = out->used;
        sHeapInfo.heapPeakSizes[heapID] = out->size;
    }
    out->peakSize = sHeapInfo.heapPeakSizes[heapID];
    out->blocks = sHeapInfo.numMemBlocks[heapID];
    out->name = Heap_GetHeapName(heapID);
    return TRUE;
}
