#include "character_sprite.h"

#include <nitro.h>
#include <string.h>
#ifdef SDK_PORT
#include <stdlib.h>
#endif

#include "constants/graphics.h"
#include "constants/heap.h"
#include "constants/narc.h"
#include "constants/species.h"

#include "heap.h"
#include "narc.h"
#include "pokemon.h"
#include "pokemon_sprite.h"

#define SUB_REGION_ORDER { { 0x0, 0x0, 0x8, 0x8 }, { 0x8, 0x0, 0x2, 0x4 }, { 0x8, 0x4, 0x2, 0x4 }, { 0x0, 0x8, 0x4, 0x2 }, { 0x4, 0x8, 0x4, 0x2 }, { 0x8, 0x8, 0x2, 0x2 } }

#ifdef SDK_PORT
#define CHARACTER_SPRITE_CACHE_SIZE 128

typedef struct CharacterSpriteCacheEntry {
    enum NarcID narcID;
    int member;
    u32 stamp;
    NNSG2dCharacterData character;
    u8 *rawData;
} CharacterSpriteCacheEntry;

typedef struct CharacterPaletteCacheEntry {
    enum NarcID narcID;
    int member;
    BOOL valid;
    u8 data[PALETTE_SIZE_BYTES];
} CharacterPaletteCacheEntry;

static CharacterSpriteCacheEntry sCharacterSpriteCache[CHARACTER_SPRITE_CACHE_SIZE];
static CharacterPaletteCacheEntry sCharacterPaletteCache[CHARACTER_SPRITE_CACHE_SIZE];
static u32 sCharacterSpriteCacheClock;
#endif

static void CharacterSprite_CopyTileFromUntiledArray(const u8 *src, u8 *dest, int *srcOffset, int *destOffset, int tileWidth, int rowWidth)
{
    for (int i = 0; i < TILE_HEIGHT_PIXELS; i++) {
        memcpy(&dest[*destOffset], &src[*srcOffset], tileWidth);
        *srcOffset += rowWidth;
        *destOffset += tileWidth;
    }
}

static void CharacterSprite_LoadSpriteData(enum NarcID narcID, int narcIdx, enum HeapID heapID, NNSG2dCharacterData **charData)
{
    BOOL success;

#ifdef SDK_PORT
    CharacterSpriteCacheEntry *entry = NULL;
    CharacterSpriteCacheEntry *oldest = &sCharacterSpriteCache[0];

    for (int i = 0; i < CHARACTER_SPRITE_CACHE_SIZE; i++) {
        if (sCharacterSpriteCache[i].rawData != NULL
            && sCharacterSpriteCache[i].narcID == narcID
            && sCharacterSpriteCache[i].member == narcIdx) {
            sCharacterSpriteCache[i].stamp = ++sCharacterSpriteCacheClock;
            *charData = &sCharacterSpriteCache[i].character;
            return;
        }
        if (sCharacterSpriteCache[i].rawData == NULL) {
            entry = &sCharacterSpriteCache[i];
            break;
        }
        if (sCharacterSpriteCache[i].stamp < oldest->stamp) {
            oldest = &sCharacterSpriteCache[i];
        }
    }

    if (entry == NULL) {
        entry = oldest;
        free(entry->rawData);
        entry->rawData = NULL;
    }
#endif

    void *ngcrFile = NARC_AllocAndReadWholeMemberByIndexPair(narcID, narcIdx, heapID);
    GF_ASSERT(ngcrFile != NULL);

    NNSG2dCharacterData *unpacked;
    success = NNS_G2dGetUnpackedCharacterData(ngcrFile, &unpacked);
    GF_ASSERT(unpacked != NULL);
    GF_ASSERT(success != FALSE);

#ifdef SDK_PORT
    entry->rawData = malloc(unpacked->szByte);
    GF_ASSERT(entry->rawData != NULL);
    memcpy(entry->rawData, unpacked->pRawData, unpacked->szByte);
    entry->character = *unpacked;
    entry->character.pRawData = entry->rawData;
    entry->narcID = narcID;
    entry->member = narcIdx;
    entry->stamp = ++sCharacterSpriteCacheClock;
    PokemonSprite_Decrypt(entry->rawData, narcID);
    *charData = &entry->character;
#else
    *charData = unpacked;
    PokemonSprite_Decrypt(unpacked->pRawData, narcID);
#endif

    Heap_Free(ngcrFile);
}

static void CharacterSprite_TileUntiledPokemonSprite(int x, int y, int width, int height, NNSG2dCharacterData *monSpriteData, void *dest)
{
    u8 *untiledSpriteData = NULL;
    u8 *tiledData = NULL;
    int startIndex;
    int tiledDataOffset;
    int spriteWidth;

    GF_ASSERT(monSpriteData->W >= (x + width));
    GF_ASSERT(monSpriteData->H >= (y + height));

    untiledSpriteData = monSpriteData->pRawData;
    tiledData = dest;
    spriteWidth = (monSpriteData->W * TILE_WIDTH_4BPP);
    startIndex = (x * TILE_WIDTH_4BPP) + (y * spriteWidth);
    tiledDataOffset = 0;

    for (int row = y; row < (y + height); row++) {
        for (int col = x; col < (x + width); col++) {
            startIndex = (col * TILE_WIDTH_4BPP) + (row * spriteWidth * 8);
            CharacterSprite_CopyTileFromUntiledArray(untiledSpriteData, tiledData, &startIndex, &tiledDataOffset, TILE_WIDTH_4BPP, spriteWidth);
        }
    }
}

static BOOL CharacterSprite_SpeciesIsSpinda(enum Species species)
{
    enum Species listItem;
    const int speciesList[] = {
        SPECIES_SPINDA,
        SPECIES_BAD_EGG,
    };

    for (int i = 0; i < MAX_SPECIES; i++) {
        listItem = speciesList[i];

        if (listItem == SPECIES_BAD_EGG) {
            break;
        }

        if (listItem == species) {
            return TRUE;
        }
    }

    return FALSE;
}

static void CharacterSprite_LoadTiledPokemonSprite(enum NarcID narcID, int narcIdx, enum HeapID heapID, int x, int y, int width, int height, void *buffer, u32 personality, BOOL isAnimated, int face, enum Species species)
{
    BOOL speciesIsSpinda;
    NNSG2dCharacterData *monSpriteData = NULL;

    CharacterSprite_LoadSpriteData(narcID, narcIdx, heapID, &monSpriteData);

    speciesIsSpinda = CharacterSprite_SpeciesIsSpinda(species);

    if ((face == FACE_FRONT) && (speciesIsSpinda == TRUE)) {
        // Spot placement is personality-specific. Mutate a working copy so
        // the process cache always retains canonical decrypted Spinda pixels.
        NNSG2dCharacterData workingData = *monSpriteData;
        workingData.pRawData = Heap_Alloc(heapID, monSpriteData->szByte);
        memcpy(workingData.pRawData, monSpriteData->pRawData, monSpriteData->szByte);
        PokemonSprite_DrawSpindaSpots(workingData.pRawData, personality, isAnimated);
        CharacterSprite_TileUntiledPokemonSprite(x, y, width, height, &workingData, buffer);
        Heap_Free(workingData.pRawData);
        return;
    }

    CharacterSprite_TileUntiledPokemonSprite(x, y, width, height, monSpriteData, buffer);
}

static void *CharacterSprite_GetTiledPokemonSprite(enum NarcID narcID, int narcIdx, enum HeapID heapID, int x, int y, int width, int height, u32 personality, BOOL isAnimated, int face, enum Species species)
{
    int dataSize = ((width * height) * TILE_SIZE_4BPP);
    void *buffer = Heap_Alloc(heapID, dataSize);

    CharacterSprite_LoadTiledPokemonSprite(narcID, narcIdx, heapID, x, y, width, height, buffer, personality, isAnimated, face, species);

    return buffer;
}

void CharacterSprite_LoadTiledData(enum NarcID narcID, int narcIdx, enum HeapID heapID, int x, int y, int width, int height, void *dest)
{
    u8 *untiledSpriteData = NULL;
    u8 *tiledData = NULL;
    NNSG2dCharacterData *characterData = NULL;
    int tileWidth;
    int spriteIndex;
    int tiledDataOffset;
    int spriteWidth;

    CharacterSprite_LoadSpriteData(narcID, narcIdx, heapID, &characterData);
    GF_ASSERT(characterData->W >= (x + width));
    GF_ASSERT(characterData->H >= (y + height));

    tileWidth = TILE_WIDTH_4BPP;
    untiledSpriteData = characterData->pRawData;

    tiledData = dest;
    spriteWidth = (characterData->W * tileWidth);
    spriteIndex = (x * tileWidth) + (y * spriteWidth);

    tiledDataOffset = 0;

    for (int row = y; row < (y + height); row++) {
        for (int col = x; col < (x + width); col++) {
            spriteIndex = (col * tileWidth) + (row * spriteWidth * 8);
            CharacterSprite_CopyTileFromUntiledArray(untiledSpriteData, tiledData, &spriteIndex, &tiledDataOffset, tileWidth, spriteWidth);
        }
    }

}

static void *CharacterSprite_GetTiledSprite(enum NarcID narcID, int characterIdx, enum HeapID heapID, int x, int y, int width, int height)
{
    void *buffer;
    int numBytes = ((width * height) * TILE_SIZE_4BPP);
    buffer = Heap_Alloc(heapID, numBytes);

    CharacterSprite_LoadTiledData(narcID, characterIdx, heapID, x, y, width, height, buffer);

    return buffer;
}

static void CharacterSprite_CopyTilesRect(int sourceWidth, int sourceHeight, int x, int y, int width, int height, int *destOffset, const void *src, void *dest)
{
    u8 *srcPtr;
    u8 *destPtr;
    int srcTile;
    int finishCol;
    int finishRow;

    srcPtr = src;
    destPtr = dest;
    finishCol = x + width;
    finishRow = y + height;

    for (int row = y; row < finishRow; row++) {
        for (int col = x; col < finishCol; col++) {
            srcTile = (col * TILE_SIZE_4BPP) + (row * TILE_SIZE_4BPP * sourceWidth);
            memcpy(&destPtr[*destOffset], &srcPtr[srcTile], TILE_SIZE_4BPP);
            *destOffset += TILE_SIZE_4BPP;
        }
    }
}

static void CharacterSprite_CopyTilesRegion(int sourceWidth, int sourceHeight, const TileRegion *subRegion, int *destOffset, const void *sourceSprite, void *dest)
{
    CharacterSprite_CopyTilesRect(sourceWidth, sourceHeight, subRegion->x, subRegion->y, subRegion->width, subRegion->height, destOffset, sourceSprite, dest);
}

static void CharacterSprite_LoadSpriteRect(enum NarcID narcID, int characterIdx, enum HeapID heapID, int x, int y, int width, int height, void *dest)
{
    int numRegions;
    int destOffset;
    void *sprite = NULL;
    const TileRegion subRegions[] = SUB_REGION_ORDER;

    numRegions = NELEMS(subRegions);
    destOffset = 0;
    sprite = CharacterSprite_GetTiledSprite(narcID, characterIdx, heapID, x, y, width, height);

    for (int i = 0; i < numRegions; i++) {
        CharacterSprite_CopyTilesRegion(width, height, &subRegions[i], &destOffset, sprite, dest);
    }

    Heap_Free(sprite);
}

void CharacterSprite_LoadSpriteRegion(enum NarcID narcID, int narcIdx, enum HeapID heapID, const TileRegion *region, void *dest)
{
    CharacterSprite_LoadSpriteRect(narcID, narcIdx, heapID, region->x, region->y, region->width, region->height, dest);
}

void CharacterSprite_LoadSpriteFrame0(enum NarcID narcID, int narcIdx, enum HeapID heapID, void *dest)
{
    const TileRegion region = FRAME_0_REGION;
    CharacterSprite_LoadSpriteRegion(narcID, narcIdx, heapID, &region, dest);
}

void *CharacterSprite_LoadTiles(enum NarcID narcID, int narcIdx, enum HeapID heapID)
{
    int size = (MON_SPRITE_FRAME_WIDTH_TILES * MON_SPRITE_FRAME_HEIGHT_TILES * TILE_SIZE_4BPP);
    void *spriteData = Heap_Alloc(heapID, size);

    CharacterSprite_LoadSpriteFrame0(narcID, narcIdx, heapID, spriteData);

    return spriteData;
}

void *CharacterSprite_LoadPalette(enum NarcID narcID, int paletteIndex, enum HeapID heapID)
{
    NNSG2dPaletteData *paletteData;
    void *nclrFile;
    void *returnPtr;
    BOOL success;

    returnPtr = Heap_Alloc(heapID, PALETTE_SIZE_BYTES);
#ifdef SDK_PORT
    CharacterPaletteCacheEntry *cacheEntry = &sCharacterPaletteCache[((u32)narcID * 33 + paletteIndex) % CHARACTER_SPRITE_CACHE_SIZE];
    if (cacheEntry->valid && cacheEntry->narcID == narcID && cacheEntry->member == paletteIndex) {
        MI_CpuCopy16(cacheEntry->data, returnPtr, PALETTE_SIZE_BYTES);
        return returnPtr;
    }
#endif

    nclrFile = NARC_AllocAndReadWholeMemberByIndexPair(narcID, paletteIndex, heapID);
    success = NNS_G2dGetUnpackedPaletteData(nclrFile, &paletteData);

    GF_ASSERT(success == TRUE);
    MI_CpuCopy16(paletteData->pRawData, returnPtr, PALETTE_SIZE_BYTES);
#ifdef SDK_PORT
    cacheEntry->narcID = narcID;
    cacheEntry->member = paletteIndex;
    cacheEntry->valid = TRUE;
    MI_CpuCopy16(paletteData->pRawData, cacheEntry->data, PALETTE_SIZE_BYTES);
#endif

    Heap_Free(nclrFile);

    return returnPtr;
}

void CharacterSprite_LoadPokemonSpriteRect(enum NarcID narcID, int narcIdx, enum HeapID heapID, int x, int y, int width, int height, u8 *dest, u32 personality, BOOL isAnimated, int face, enum Species species)
{
    int numRegions;
    int destOffset;
    void *tiledData = NULL;
    const TileRegion subRegions[] = SUB_REGION_ORDER;

    numRegions = NELEMS(subRegions);
    destOffset = 0;

    tiledData = CharacterSprite_GetTiledPokemonSprite(narcID, narcIdx, heapID, x, y, width, height, personality, isAnimated, face, species);

    for (int i = 0; i < numRegions; i++) {
        CharacterSprite_CopyTilesRegion(width, height, &subRegions[i], &destOffset, tiledData, dest);
    }

    Heap_Free(tiledData);
}

void CharacterSprite_LoadPokemonSpriteRegion(enum NarcID narcID, int narcIdx, enum HeapID heapID, const TileRegion *frameTiles, void *dest, u32 personality, BOOL isAnimated, int face, enum Species species)
{
    CharacterSprite_LoadPokemonSpriteRect(narcID, narcIdx, heapID, frameTiles->x, frameTiles->y, frameTiles->width, frameTiles->height, dest, personality, isAnimated, face, species);
}

void CharacterSprite_LoadPokemonSprite(enum NarcID narcID, int narcIdx, enum HeapID heapID, void *destPtr, u32 personality, BOOL isAnimated, int face, enum Species species)
{
    const TileRegion region = FRAME_0_REGION;

    CharacterSprite_LoadPokemonSpriteRegion(narcID, narcIdx, heapID, &region, destPtr, personality, isAnimated, face, species);
}
