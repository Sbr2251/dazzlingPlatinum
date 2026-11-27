#include "billboard_vram_transfer.h"

#include "ascii_util.h"
#include "billboard.h"
#include "heap.h"
#include "vram_transfer.h"

static void RequestBillboardVRAMTransfer(BillboardVRAMTransfer *transfer, const u16 index);
static void *GetBillboardTextureVRAMBuffer(BillboardVRAMTransfer *transfer, const BillboardTexPlttIndex *texPlttIndex);
static void *GetBillboardPlttVRAMBuffer(BillboardVRAMTransfer *transfer, const BillboardTexPlttIndex *texPlttIndex);
static void ResetBillboardVRAMTransfer(BillboardVRAMTransfer *transfer);
static void RequestBillboardTextureVRAMTransfer(BillboardVRAMTransfer *transfer, const BillboardTexPlttIndex *texPlttIndexes);
static void RequestBillboardPlttVRAMTransfer(BillboardVRAMTransfer *transfer, const BillboardTexPlttIndex *texPlttIndexes);

BillboardListVRAMTransfer *BillboardListVRAMTransfer_New(int maxElements, enum HeapID heapID)
{
    BillboardListVRAMTransfer *listTransfer = Heap_Alloc(heapID, sizeof(BillboardListVRAMTransfer));
    listTransfer->billboardTransfers = Heap_Alloc(heapID, sizeof(BillboardVRAMTransfer) * maxElements);
    listTransfer->maxElements = maxElements;

    for (int i = 0; i < listTransfer->maxElements; i++) {
        ResetBillboardVRAMTransfer(&listTransfer->billboardTransfers[i]);
    }

    return listTransfer;
}

void BillboardListVRAMTransfer_Free(BillboardListVRAMTransfer *listTransfer)
{
    BillboardListVRAMTransfer_ResetAll(listTransfer);
    Heap_Free(listTransfer->billboardTransfers);
    Heap_Free(listTransfer);
}

BillboardVRAMTransfer *BillboardListVRAMTransfer_NewBillboardTransfer(BillboardListVRAMTransfer *listTransfer, const BillboardGfxSequence *gfxSequence, const NNSG3dResTex *texture, NNSGfdTexKey texKey, NNSGfdPlttKey plttKey, const fx32 index)
{
    BillboardVRAMTransfer *transfer = NULL;

    for (int i = 0; i < listTransfer->maxElements; i++) {
        if (listTransfer->billboardTransfers[i].gfxSequence == NULL) {
            transfer = &listTransfer->billboardTransfers[i];
            break;
        }
    }

    if (transfer == NULL) {
        return NULL;
    }

    transfer->gfxSequence = gfxSequence;
    transfer->texture = texture;
    transfer->texKey = texKey;
    transfer->plttKey = plttKey;
    transfer->textureIdx = -1;
    transfer->plttIdx = -1;

    RequestBillboardVRAMTransfer(transfer, index >> FX32_SHIFT);

    return transfer;
}

void BillboardVRAMTransfer_Reset(BillboardVRAMTransfer *transfer)
{
    ResetBillboardVRAMTransfer(transfer);
}

void BillboardListVRAMTransfer_ResetAll(BillboardListVRAMTransfer *listTransfer)
{
    for (int i = 0; i < listTransfer->maxElements; i++) {
        ResetBillboardVRAMTransfer(listTransfer->billboardTransfers + i);
    }
}

void BillboardVRAMTransfer_Request(BillboardVRAMTransfer *transfer, const fx32 indexFx32)
{
    u16 index = indexFx32 >> FX32_SHIFT;
    RequestBillboardVRAMTransfer(transfer, index);
}

static void ResetBillboardVRAMTransfer(BillboardVRAMTransfer *transfer)
{
    transfer->gfxSequence = NULL;
    transfer->texture = NULL;
    transfer->texKey = 0;
    transfer->plttKey = 0;
    transfer->textureIdx = 0;
    transfer->plttIdx = 0;
}

static void RequestBillboardVRAMTransfer(BillboardVRAMTransfer *transfer, const u16 index)
{
    BillboardTexPlttIndex texPlttIndexes = BillboardGfxSequence_GetTexPlttIndexAt(transfer->gfxSequence, index);

    if (transfer->textureIdx != texPlttIndexes.textureIdx) {
        RequestBillboardTextureVRAMTransfer(transfer, &texPlttIndexes);
    }

    if (transfer->plttIdx != texPlttIndexes.plttIdx) {
        RequestBillboardPlttVRAMTransfer(transfer, &texPlttIndexes);
    }
}

static u32 CalcTextureDataByteSize(const NNSG3dResTex *texture, u8 index)
{
    if (texture == NULL) {
        return 0;
    }

    const NNSG3dResDictTexData *textureData = NNS_G3dGetTexDataByIdx(texture, index);
    if (textureData == NULL) {
        return 0;
    }

    u32 param = textureData->texImageParam;
    u32 w = 8u << ((param >> 20) & 7u);
    u32 h = 8u << ((param >> 23) & 7u);
    u32 fmt = (param >> 26) & 7u;
    u32 pixels = w * h;
    u32 byteSize = 0;

    switch (fmt) {
    case GX_TEXFMT_A3I5:
    case GX_TEXFMT_A5I3:
    case GX_TEXFMT_PLTT256:
        byteSize = pixels;
        break;
    case GX_TEXFMT_PLTT4:
        byteSize = pixels >> 2;
        break;
    case GX_TEXFMT_PLTT16:
        byteSize = pixels >> 1;
        break;
    case GX_TEXFMT_COMP4x4:
        byteSize = pixels >> 2;
        break;
    case GX_TEXFMT_DIRECT:
        byteSize = pixels << 1;
        break;
    default:
        return 0;
    }

    u32 texOffset = ((param & NNS_G3D_TEXIMAGE_PARAM_TEX_ADDR_MASK) + texture->texInfo.vramKey) << 3;
    u32 totalTexBytes = (u32)texture->texInfo.sizeTex << 3;
    if (texOffset >= totalTexBytes) {
        return 0;
    }
    u32 avail = totalTexBytes - texOffset;
    if (byteSize > avail) {
        byteSize = avail;
    }
    return byteSize;
}

static void RequestBillboardTextureVRAMTransfer(BillboardVRAMTransfer *transfer, const BillboardTexPlttIndex *texPlttIndexes)
{
    void *buffer = GetBillboardTextureVRAMBuffer(transfer, texPlttIndexes);
    u32 destSize = NNS_GfdGetTexKeySize(transfer->texKey);
    u32 srcSize = CalcTextureDataByteSize(transfer->texture, texPlttIndexes->textureIdx);
    u32 copySize = (srcSize > 0 && srcSize < destSize) ? srcSize : destSize;
    if (buffer != NULL && copySize > 0) {
        VramTransfer_Request(NNS_GFD_DST_3D_TEX_VRAM, NNS_GfdGetTexKeyAddr(transfer->texKey), buffer, copySize);
    }
    transfer->textureIdx = texPlttIndexes->textureIdx;
}

static void RequestBillboardPlttVRAMTransfer(BillboardVRAMTransfer *transfer, const BillboardTexPlttIndex *texPlttIndexes)
{
    void *buffer = GetBillboardPlttVRAMBuffer(transfer, texPlttIndexes);
    u32 destSize = NNS_GfdGetPlttKeySize(transfer->plttKey);
    u32 copySize = destSize;
    if (transfer->texture != NULL) {
        const NNSG3dResDictPlttData *plttData = NNS_G3dGetPlttDataByIdx(transfer->texture, texPlttIndexes->plttIdx);
        u32 totalPlttBytes = (u32)transfer->texture->plttInfo.sizePltt << 3;
        if (plttData != NULL) {
            u32 plttOff = ((u32)plttData->offset + transfer->texture->plttInfo.vramKey) << 3;
            if (plttOff < totalPlttBytes) {
                u32 avail = totalPlttBytes - plttOff;
                if (copySize > avail) {
                    copySize = avail;
                }
            } else {
                copySize = 0;
            }
        }
    }
    if (buffer != NULL && copySize > 0) {
        VramTransfer_Request(NNS_GFD_DST_3D_TEX_PLTT, NNS_GfdGetPlttKeyAddr(transfer->plttKey), buffer, copySize);
    }
    transfer->plttIdx = texPlttIndexes->plttIdx;
}

static void *GetBillboardTextureVRAMBuffer(BillboardVRAMTransfer *transfer, const BillboardTexPlttIndex *texPlttIndex)
{
    return GetTextureDataVRAMBuffer(transfer->texture, texPlttIndex->textureIdx);
}

static void *GetBillboardPlttVRAMBuffer(BillboardVRAMTransfer *transfer, const BillboardTexPlttIndex *texPlttIndex)
{
    return GetPlttDataVRAMBuffer(transfer->texture, texPlttIndex->plttIdx);
}

void *GetTextureDataVRAMBuffer(NNSG3dResTex *texture, const u8 index)
{
    const NNSG3dResDictTexData *textureData = NNS_G3dGetTexDataByIdx(texture, index);

    if (textureData == NULL) {
        return NULL;
    }

    u32 address = (textureData->texImageParam & NNS_G3D_TEXIMAGE_PARAM_TEX_ADDR_MASK) + texture->texInfo.vramKey;
    return (void *)((u8 *)texture + texture->texInfo.ofsTex + (address << 3));
}

void *GetPlttDataVRAMBuffer(NNSG3dResTex *texture, const u8 index)
{
    const NNSG3dResDictPlttData *plttData = NNS_G3dGetPlttDataByIdx(texture, index);

    if (plttData == NULL) {
        return NULL;
    }

    return (void *)((u8 *)texture + texture->plttInfo.ofsPlttData + (plttData->offset << 3));
}

static void *GetTextureDataBuffer(NNSG3dResTex *texture, const NNSG3dResDictTexData *textureData)
{
    u32 address = (textureData->texImageParam & NNS_G3D_TEXIMAGE_PARAM_TEX_ADDR_MASK) << 3;
    address += NNS_GfdGetTexKeyAddr(texture->texInfo.vramKey);
    return (void *)address;
}

void *GetTextureDataBufferFromResourceName(NNSG3dResTex *texture, const char *name)
{
    NNSG3dResName resName;
    Ascii_SetResourceName(&resName, name);
    const NNSG3dResDictTexData *textureData = NNS_G3dGetTexDataByName(texture, &resName);

    if (textureData == NULL) {
        return NULL;
    }

    return GetTextureDataBuffer(texture, textureData);
}

static int CalcTextureDataSize(NNSG3dResTex *texture, const NNSG3dResDictTexData *textureData)
{
    u32 textureFormat = (textureData->texImageParam & NNS_G3D_TEXIMAGE_PARAM_TEXFMT_MASK) >> NNS_G3D_TEXIMAGE_PARAM_TEXFMT_SHIFT;
    u32 texelSize;

    switch (textureFormat) {
    case GX_TEXFMT_PLTT4:
        texelSize = 4;
        break;
    case GX_TEXFMT_PLTT16:
        texelSize = 2;
        break;
    case GX_TEXFMT_PLTT256:
        texelSize = 1;
        break;
    case GX_TEXFMT_A3I5:
        texelSize = 1;
        break;
    case GX_TEXFMT_A5I3:
        texelSize = 1;
        break;
    default:
        return 0;
    }

    u32 sSize = (textureData->texImageParam & NNS_G3D_TEXIMAGE_PARAM_S_SIZE_MASK) >> NNS_G3D_TEXIMAGE_PARAM_S_SIZE_SHIFT;
    sSize <<= 4;

    u32 tSize = (textureData->texImageParam & NNS_G3D_TEXIMAGE_PARAM_T_SIZE_MASK) >> NNS_G3D_TEXIMAGE_PARAM_T_SIZE_SHIFT;
    tSize <<= 4;

    return (sSize * tSize) / texelSize;
}

int CalcTextureDataSizeFromResourceName(NNSG3dResTex *texture, const char *name)
{
    NNSG3dResName resName;
    Ascii_SetResourceName(&resName, name);
    const NNSG3dResDictTexData *textureData = NNS_G3dGetTexDataByName(texture, &resName);

    return CalcTextureDataSize(texture, textureData);
}
