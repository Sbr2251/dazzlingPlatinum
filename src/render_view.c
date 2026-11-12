#include "render_view.h"

#include <nnsys.h>

void InitRenderer(NNSG2dRendererInstance *renderer, fx32 spriteZOffset)
{
    NNS_G2dInitRenderer(renderer);
    NNS_G2dSetRendererSpriteZoffset(renderer, spriteZOffset);
}

void InitRenderSurface(NNSG2dRenderSurface *surface, NNSG2dViewRect *viewRect, NNSG2dOamRegisterFunction oamRegisterFunc, NNSG2dAffineRegisterFunction oamAffineRegisterFunc, NNSG2dRndCellCullingFunction visibilityCullingFunc, NNSG2dSurfaceType surfaceType, NNSG2dRendererInstance *renderer)
{
    NNS_G2dInitRenderSurface(surface);

    surface->viewRect = *viewRect;
    surface->pFuncOamRegister = oamRegisterFunc;
    surface->pFuncOamAffineRegister = oamAffineRegisterFunc;
    surface->pFuncVisibilityCulling = visibilityCullingFunc;
    surface->type = surfaceType;

    if (renderer) {
        NNS_G2dAddRendererTargetSurface(renderer, surface);
    }
}

void SetRenderSurfaceViewRect(NNSG2dRenderSurface *surface, NNSG2dViewRect *viewRect)
{
    surface->viewRect = *viewRect;
}

BOOL IsObjectInView(const NNSG2dCellData *cellData, const MtxFx32 *objectCoords, const NNSG2dViewRect *viewRect)
{
    const NNSG2dCellBoundingRectS16 *boundingRect = NNS_G2dGetCellBoundingRect(cellData);
    const fx32 boundingRadius = NNS_G2dGetCellBoundingSphereR(cellData);
    const fx32 originX = objectCoords->_20 - viewRect->posTopLeft.x;
    const fx32 originY = objectCoords->_21 - viewRect->posTopLeft.y;

    fx32 minY, maxY;
    fx32 minX, maxX;
    fx32 tmp;

    // Shift in unsigned: the bounding-rect coordinates can be negative
    // and the radius is negated, and left-shifting a negative value is UB
    // in C. Shifting the two's-complement bit pattern in u32 gives the
    // same result the DS compiler produced.
    if (NNS_G2dCellHasBR(cellData) == TRUE) {
        minY = (fx32)((u32)(s32)boundingRect->minY << FX32_SHIFT);
        maxY = (fx32)((u32)(s32)boundingRect->maxY << FX32_SHIFT);
        minX = (fx32)((u32)(s32)boundingRect->minX << FX32_SHIFT);
        maxX = (fx32)((u32)(s32)boundingRect->maxX << FX32_SHIFT);
    } else {
        minY = (fx32)(0u - ((u32)boundingRadius << FX32_SHIFT));
        maxY = (fx32)((u32)boundingRadius << FX32_SHIFT);
        minX = (fx32)(0u - ((u32)boundingRadius << FX32_SHIFT));
        maxX = (fx32)((u32)boundingRadius << FX32_SHIFT);
    }

    minY = FX_Mul(minY, objectCoords->_01) + FX_Mul(minY, objectCoords->_11) + originY;
    maxY = FX_Mul(maxY, objectCoords->_01) + FX_Mul(maxY, objectCoords->_11) + originY;
    minX = FX_Mul(minX, objectCoords->_00) + FX_Mul(minX, objectCoords->_10) + originX;
    maxX = FX_Mul(maxX, objectCoords->_00) + FX_Mul(maxX, objectCoords->_10) + originX;

    if (maxY < minY) {
        tmp = maxY;
        maxY = minY;
        minY = tmp;
    }

    if (maxX < minX) {
        tmp = maxX;
        maxX = minX;
        minX = tmp;
    }

    return maxY > 0 && minY < viewRect->sizeView.y && maxX > 0 && minX < viewRect->sizeView.x;
}
