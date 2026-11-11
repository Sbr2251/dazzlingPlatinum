#include "vram_stats.h"

#include <nnsys/gfd/VramManager/gfd_LinkedListPlttVramMan.h>
#include <nnsys/gfd/VramManager/gfd_LinkedListTexVramMan.h>

// Tracks which NNS VRAM manager is active and its total size, so usage can
// be reported. Free space for the linked-list managers comes from the
// managers' own dump callbacks, which visit every free block.

#define VRAM_UNKNOWN 0xFFFFFFFFu

typedef enum VramManagerKind {
    VRAM_KIND_UNKNOWN = 0,
    VRAM_KIND_LNK,
    VRAM_KIND_FRM,
} VramManagerKind;

static VramManagerKind sTexKind = VRAM_KIND_UNKNOWN;
static VramManagerKind sPlttKind = VRAM_KIND_UNKNOWN;
static u32 sTexTotal = VRAM_UNKNOWN;
static u32 sPlttTotal = VRAM_UNKNOWN;

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

static void SumFreeBlock(u32 addr, u32 szByte, void *userData)
{
    (void)addr;
    *(u32 *)userData += szByte;
}

void VramStats_Get(VramStats *out)
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
