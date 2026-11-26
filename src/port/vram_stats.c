#include "vram_stats.h"

#include <nnsys/gfd/VramManager/gfd_LinkedListPlttVramMan.h>
#include <nnsys/gfd/VramManager/gfd_LinkedListTexVramMan.h>
#include <stdio.h>

// Tracks which NNS VRAM manager is active and its total size, so usage can
// be reported. Free space for the linked-list managers comes from the
// managers' own dump callbacks, which visit every free block.

#define VRAM_UNKNOWN       0xFFFFFFFFu
#define VRAM_OOM_LOG_LIMIT 16u

typedef enum VramManagerKind {
    VRAM_KIND_UNKNOWN = 0,
    VRAM_KIND_LNK,
    VRAM_KIND_FRM,
} VramManagerKind;

static VramManagerKind sTexKind = VRAM_KIND_UNKNOWN;
static VramManagerKind sPlttKind = VRAM_KIND_UNKNOWN;
static u32 sTexTotal = VRAM_UNKNOWN;
static u32 sPlttTotal = VRAM_UNKNOWN;
static u32 sTexOomCount = 0;
static u32 sPlttOomCount = 0;
static u32 sPoolOomCount = 0;

void VramStats_NoteTexLnk(u32 totalBytes)
{
    sTexKind = VRAM_KIND_LNK;
    sTexTotal = totalBytes;
}

void VramStats_NotePlttLnk(u32 totalBytes)
{
    sPlttKind = VRAM_KIND_LNK;
    sPlttTotal = totalBytes;
}

void VramStats_NoteTexFrm(void)
{
    sTexKind = VRAM_KIND_FRM;
    sTexTotal = VRAM_UNKNOWN;
}

void VramStats_NotePlttFrm(void)
{
    sPlttKind = VRAM_KIND_FRM;
    sPlttTotal = VRAM_UNKNOWN;
}

void VramStats_NoteFrm(void)
{
    VramStats_NoteTexFrm();
    VramStats_NotePlttFrm();
}

void VramStats_NoteShutdown(void)
{
    sTexKind = VRAM_KIND_UNKNOWN;
    sPlttKind = VRAM_KIND_UNKNOWN;
    sTexTotal = VRAM_UNKNOWN;
    sPlttTotal = VRAM_UNKNOWN;
}

static void SumFreeBlock(u32 addr, u32 szByte, void *userData)
{
    (void)addr;
    *(u32 *)userData += szByte;
}

void VramStats_NoteTexOom(const char *site, u32 requestedBytes, BOOL is4x4)
{
    sTexOomCount++;
    if (sTexOomCount <= VRAM_OOM_LOG_LIMIT) {
        long freeBytes = -1;
        if (sTexKind == VRAM_KIND_LNK) {
            u32 freeAcc = 0;
            NNS_GfdDumpLnkTexVramManagerEx(SumFreeBlock, SumFreeBlock, &freeAcc);
            freeBytes = (long)freeAcc;
        }
        fprintf(stderr,
            "[VRAM-OOM] tex alloc failed at %s: req=%u bytes (4x4=%d) free=%ld total=%ld count=%u%s\n",
            site != NULL ? site : "?",
            (unsigned)requestedBytes,
            is4x4 ? 1 : 0,
            freeBytes,
            sTexTotal == VRAM_UNKNOWN ? -1L : (long)sTexTotal,
            (unsigned)sTexOomCount,
            sTexOomCount == VRAM_OOM_LOG_LIMIT ? " (further tex OOM logs suppressed)" : "");
        fflush(stderr);
    }
}

void VramStats_NotePlttOom(const char *site, u32 requestedBytes, BOOL is4Pltt)
{
    sPlttOomCount++;
    if (sPlttOomCount <= VRAM_OOM_LOG_LIMIT) {
        long freeBytes = -1;
        if (sPlttKind == VRAM_KIND_LNK) {
            u32 freeAcc = 0;
            NNS_GfdDumpLnkPlttVramManagerEx(SumFreeBlock, &freeAcc);
            freeBytes = (long)freeAcc;
        }
        fprintf(stderr,
            "[VRAM-OOM] pltt alloc failed at %s: req=%u bytes (4pltt=%d) free=%ld total=%ld count=%u%s\n",
            site != NULL ? site : "?",
            (unsigned)requestedBytes,
            is4Pltt ? 1 : 0,
            freeBytes,
            sPlttTotal == VRAM_UNKNOWN ? -1L : (long)sPlttTotal,
            (unsigned)sPlttOomCount,
            sPlttOomCount == VRAM_OOM_LOG_LIMIT ? " (further pltt OOM logs suppressed)" : "");
        fflush(stderr);
    }
}

void VramStats_NotePoolOom(const char *site, int id, int capacity)
{
    sPoolOomCount++;
    if (sPoolOomCount <= VRAM_OOM_LOG_LIMIT) {
        fprintf(stderr,
            "[POOL-OOM] pool alloc failed at %s: id=%d cap=%d count=%u%s\n",
            site != NULL ? site : "?",
            id,
            capacity,
            (unsigned)sPoolOomCount,
            sPoolOomCount == VRAM_OOM_LOG_LIMIT ? " (further pool OOM logs suppressed)" : "");
        fflush(stderr);
    }
}

static void FillBaseVramStats(VramStats *out)
{
    if (out == NULL) {
        return;
    }
    out->texKind = (sTexKind == VRAM_KIND_LNK) ? "lnk" : (sTexKind == VRAM_KIND_FRM) ? "frm" : "unknown";
    out->plttKind = (sPlttKind == VRAM_KIND_LNK) ? "lnk" : (sPlttKind == VRAM_KIND_FRM) ? "frm" : "unknown";
    out->texTotal = sTexTotal;
    out->plttTotal = sPlttTotal;
    out->texFree = VRAM_UNKNOWN;
    out->plttFree = VRAM_UNKNOWN;
    if (sTexKind == VRAM_KIND_LNK) {
        u32 freeBytes = 0;
        NNS_GfdDumpLnkTexVramManagerEx(SumFreeBlock, SumFreeBlock, &freeBytes);
        out->texFree = freeBytes;
    }
    if (sPlttKind == VRAM_KIND_LNK) {
        u32 freeBytes = 0;
        NNS_GfdDumpLnkPlttVramManagerEx(SumFreeBlock, &freeBytes);
        out->plttFree = freeBytes;
    }
}

#undef VramStats_Get
void VramStats_Get(VramStats *out)
{
    FillBaseVramStats(out);
}

void VramStats_GetFull(VramStats *out)
{
    if (out == NULL) {
        return;
    }
    FillBaseVramStats(out);
    out->texOomCount = sTexOomCount;
    out->plttOomCount = sPlttOomCount;
    out->poolOomCount = sPoolOomCount;
}
