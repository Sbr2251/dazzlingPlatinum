#include "g3d_pipeline.h"

#include "nitro/hw/common/lcd.h"
#include <nitro.h>

#include "constants/graphics.h"

#include "gx_layers.h"
#include "heap.h"
#include "vram_stats.h"

#define TEXTURE_VRAM_BLOCK_SIZE 0x20000
#define PALETTE_VRAM_BLOCK_SIZE 0x2000

static void SetupDefaultPipelineState(void);

G3DPipelineBuffers *G3DPipeline_InitEx(enum HeapID heapID, enum VramManagerType texVramManagerType, enum TextureVramSize texVramSize, enum VramManagerType plttVramManagerType, enum PaletteVramSize plttVramSize, G3DPipelineSetupCallback cb)
{
    G3DPipelineBuffers *buffers = Heap_Alloc(heapID, sizeof(G3DPipelineBuffers));
    buffers->heapID = heapID;

    NNS_G3dInit();

    G3X_InitMtxStack();
    G3_SwapBuffers(GX_SORTMODE_AUTO, GX_BUFFERMODE_W);

    // VRAM is NOT enlarged (lane heap): the NNS VRAM managers' sizes are the
    // DS hardware limits. Texture VRAM is the GX VRAM banks mapped for
    // textures (GX_VRAMCNT encodes each bank with a 2-bit offset, banks are
    // fixed at 128/64/16 KB, LCDC VRAM totals 656 KB shared with BG/OBJ),
    // so the pipeline's 512 KB tex / 96 KB pltt maxima are already the
    // hardware ceiling; the simulator's LCDC mapping and texture cache are
    // keyed on those DS addresses, and game code assumes texture VRAM
    // layout (e.g. battle_stage_sprites.c keeps blob/statfx textures in
    // bank B below 0x20000 because menus unmap the banks above it).
    // Enlarging would need a new bank map plus simulator rework, for no
    // observed exhaustion. Usage is reported via vram_stats instead.
    if (texVramManagerType == VRAM_MANAGER_TYPE_LINKED_LIST) {
        int bufferSize = NNS_GfdGetLnkTexVramManagerWorkSize(128 * texVramSize);
        buffers->textureBuffer = Heap_Alloc(buffers->heapID, bufferSize);
        NNS_GfdInitLnkTexVramManager(texVramSize * TEXTURE_VRAM_BLOCK_SIZE, 0, buffers->textureBuffer, bufferSize, TRUE);
        VramStats_NoteTexLnk((u32)texVramSize * TEXTURE_VRAM_BLOCK_SIZE);
    } else {
        NNS_GfdInitFrmTexVramManager(texVramSize, TRUE);
        VramStats_NoteTexFrm();
    }

    if (plttVramManagerType == VRAM_MANAGER_TYPE_LINKED_LIST) {
        int bufferSize = NNS_GfdGetLnkPlttVramManagerWorkSize(256 * plttVramSize);
        buffers->paletteBuffer = Heap_Alloc(buffers->heapID, bufferSize);
        NNS_GfdInitLnkPlttVramManager(plttVramSize * PALETTE_VRAM_BLOCK_SIZE, buffers->paletteBuffer, bufferSize, TRUE);
        VramStats_NotePlttLnk((u32)plttVramSize * PALETTE_VRAM_BLOCK_SIZE);
    } else {
        // BUG: This should be NNS_GfdInitFrmPlttVramManager
        NNS_GfdInitFrmTexVramManager(plttVramSize * PALETTE_VRAM_BLOCK_SIZE, TRUE);
        VramStats_NotePlttFrm();
    }

    if (cb != NULL) {
        cb();
    } else {
        SetupDefaultPipelineState();
    }

    return buffers;
}

void G3DPipelineBuffers_Free(G3DPipelineBuffers *state)
{
    Heap_Free(state->paletteBuffer);
    Heap_Free(state->textureBuffer);
    Heap_Free(state);
}

static void SetupDefaultPipelineState(void)
{
    GXLayers_EngineAToggleLayers(GX_PLANEMASK_BG0, TRUE);

    G2_SetBG0Priority(0);
    G3X_SetShading(GX_SHADING_TOON);
    G3X_AntiAlias(FALSE);
    G3X_AlphaTest(FALSE, 0);
    G3X_AlphaBlend(FALSE);
    G3X_EdgeMarking(FALSE);
    G3X_SetFog(FALSE, GX_FOGBLEND_COLOR_ALPHA, GX_FOGSLOPE_0x8000, 0);
    G3X_SetClearColor(COLOR_BLACK, 0, G3X_DEPTH_MAX, 63, FALSE);
    G3_ViewPort(0, 0, HW_LCD_WIDTH - 1, HW_LCD_HEIGHT - 1);
}
