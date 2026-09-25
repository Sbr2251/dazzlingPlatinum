#ifndef POKEPLATINUM_BATTLE_BATTLE_STAGE_FORMAT_H
#define POKEPLATINUM_BATTLE_BATTLE_STAGE_FORMAT_H

// On-disk format of battle_stage.narc, written by tools/battle_stage/ and read by
// src/battle/battle_stage.c. See docs/living_battle_stage/stage_format.md.
//
// NARC members:
//   [0, BACKGROUND_MAX)                           backdrop piece for each BACKGROUND_*
//   [BACKGROUND_MAX, BACKGROUND_MAX + TERRAIN_MAX) platform piece for each TERRAIN_*
// A piece with numMeshes == 0 means "no arena yet": the stage stays off and the
// classic BG3 backdrop and OBJ platforms are used.
//
// All offsets are in bytes from the start of the piece. Everything is little endian
// and 4-byte aligned.

#define BATTLE_STAGE_MAGIC   0x47545342 // "BSTG"
#define BATTLE_STAGE_VERSION 1

enum BattleStagePaletteSource {
    // Texture indices are BG palette indices; the palette is copied from the live
    // (faded) main BG palette every frame, so BG3 palette effects apply to the arena too
    BATTLE_STAGE_PALETTE_BG = 0,
    // 16-colour texture; the palette is the live OBJ palette row used by the side's
    // platform sprite, copied every frame
    BATTLE_STAGE_PALETTE_PLATFORM_OBJ,
    // Use the palette stored in the file
    BATTLE_STAGE_PALETTE_EMBEDDED,
};

enum BattleStageMeshFlag {
    // Translated with the player/enemy platform OBJ so it slides in with the intro
    BATTLE_STAGE_MESH_FOLLOW_PLATFORM_PLAYER = 1 << 0,
    BATTLE_STAGE_MESH_FOLLOW_PLATFORM_ENEMY = 1 << 1,
    // Palette index 0 is transparent
    BATTLE_STAGE_MESH_COLOR0_TRANSPARENT = 1 << 2,
    // Scroll the texture with the BG3 offset (texture matrix), like the classic backdrop
    BATTLE_STAGE_MESH_FOLLOW_BG3_SCROLL = 1 << 3,
    // Texture wrap outside 0..size (GX_TEXREPEAT_* / GX_TEXFLIP_*); without these the
    // texture clamps
    BATTLE_STAGE_MESH_REPEAT_S = 1 << 4,
    BATTLE_STAGE_MESH_REPEAT_T = 1 << 5,
    BATTLE_STAGE_MESH_FLIP_S = 1 << 6, // mirror on repeat, needs REPEAT_S
    BATTLE_STAGE_MESH_FLIP_T = 1 << 7,
};

typedef struct BattleStageFileHeader {
    u32 magic;
    u16 version;
    u16 numTextures;
    u16 numMeshes;
    u16 padding;
    u32 texturesOffset; // BattleStageFileTexture[numTextures]
    u32 meshesOffset; // BattleStageFileMesh[numMeshes]
    // Home camera; only used from the backdrop piece. Matches G3_LookAt/G3_Perspective,
    // viewport 0..255 x 0..191, aspect 4:3. At this pose the arena lands on the same
    // pixels as the classic backdrop and platforms.
    s32 camPos[3]; // fx32
    s32 camTarget[3]; // fx32
    s32 fovySin; // fx32, sin(fovy / 2)
    s32 fovyCos; // fx32, cos(fovy / 2)
    s32 nearClip; // fx32
    s32 farClip; // fx32
    s32 vertexScale; // fx32, applied with G3_Scale to the fx16 vertex positions
    // World units per screen pixel of platform OBJ offset, at each platform's depth
    s32 platformPixelToWorld[2]; // fx32, [0] player, [1] enemy
} BattleStageFileHeader;

typedef struct BattleStageFileTexture {
    u32 dataOffset;
    u32 dataSize;
    u16 width; // 8..1024, power of two
    u16 height;
    u8 format; // GX_TEXFMT_PLTT16 or GX_TEXFMT_PLTT256
    u8 paletteSource; // enum BattleStagePaletteSource
    u16 padding;
    u32 paletteOffset; // embedded palette (GXRgb), always present as a fallback
    u32 paletteSize; // bytes
} BattleStageFileTexture;

typedef struct BattleStageFileMesh {
    u32 vertexOffset; // BattleStageFileVertex[numVertices]
    u16 numVertices;
    u8 primitive; // GX_BEGIN_TRIANGLES, _QUADS, _TRIANGLE_STRIP or _QUAD_STRIP
    u8 alpha; // 0..31
    u16 textureIndex;
    u16 flags; // enum BattleStageMeshFlag
} BattleStageFileMesh;

typedef struct BattleStageFileVertex {
    s16 pos[3]; // fx16, multiplied by header.vertexScale
    s16 texCoord[2]; // texels * 16 (G3_TexCoord units)
    u16 color; // GXRgb vertex colour (baked shading); 0x7FFF = unshaded
    u16 padding;
} BattleStageFileVertex;

#endif // POKEPLATINUM_BATTLE_BATTLE_STAGE_FORMAT_H
