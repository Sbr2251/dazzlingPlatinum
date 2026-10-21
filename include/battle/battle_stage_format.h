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
#define BATTLE_STAGE_VERSION 3

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
    // Lit by the arena light (light 0 and the material colours of the backdrop piece's
    // atmosphere): each vertex sends its normal instead of its colour
    BATTLE_STAGE_MESH_LIT = 1 << 8,
    // Polygons carry the fog bit, so the atmosphere's distance fog and the arena
    // brightness (BattleStage_SetBrightness) apply to them
    BATTLE_STAGE_MESH_FOG = 1 << 9,
    // The texture sways by scrollAmplitude texels over scrollPeriod frames (water surfaces).
    // Adds to FOLLOW_BG3_SCROLL when both are set
    BATTLE_STAGE_MESH_SCROLL = 1 << 10,
};

// Lighting columns of the atmosphere. [0..2] are the classic time-of-day columns that
// ov16_0223EC04 picks (and the classic BG palettes follow); the renderer blends the others in
// at battle start by the RTC hour and minute and the field weather (battle_stage_light.c,
// stage_format.md "Time of day and weather")
enum BattleStageLightingColumn {
    BATTLE_STAGE_LIGHTING_DAY = 0,
    BATTLE_STAGE_LIGHTING_TWILIGHT,
    BATTLE_STAGE_LIGHTING_NIGHT,
    BATTLE_STAGE_LIGHTING_MORNING, // cool blue, 06:00-09:00
    BATTLE_STAGE_LIGHTING_DUSK, // orange, 18:30
    // Field weather at battle start (each "day under that weather")
    BATTLE_STAGE_LIGHTING_RAIN,
    BATTLE_STAGE_LIGHTING_STORM, // heavy rain, thunderstorm
    BATTLE_STAGE_LIGHTING_SNOW, // snow, heavy snow, hail
    BATTLE_STAGE_LIGHTING_BLIZZARD,
    BATTLE_STAGE_LIGHTING_FOG, // fog, deep fog
    BATTLE_STAGE_LIGHTING_SAND,
    BATTLE_STAGE_LIGHTING_RIFT_MIST, // the hack's violet mist (Route 210 North)
    BATTLE_STAGE_LIGHTING_MAX,
};

#define BATTLE_STAGE_LIGHTING_TOD_COUNT (BATTLE_STAGE_LIGHTING_DUSK + 1)
#define BATTLE_STAGE_HAZE_FULL          128

// Arena light and fog for one lighting column (enum BattleStageLightingColumn)
typedef struct BattleStageFileLighting {
    s16 lightDir[3]; // fx16 world-space direction the light travels, |v| < 1 (G3_LightVector)
    u16 lightColor; // GXRgb
    u16 diffuse; // GXRgb, G3_MaterialColorDiffAmb
    u16 ambient; // GXRgb
    u16 emission; // GXRgb, G3_MaterialColorSpecEmi (specular is always black)
    u16 fogColor; // GXRgb
    u8 fogAlpha; // 0..31
    u8 haze; // 0..BATTLE_STAGE_HAZE_FULL: how much of the atmosphere's haze fog (weather) applies
    u8 padding[2];
} BattleStageFileLighting;

// Only read from the backdrop piece
typedef struct BattleStageFileAtmosphere {
    u8 fogEnabled; // 0: no distance fog (FOG meshes still take the brightness)
    u8 fogShift; // G3X_SetFog slope: GX_FOGSLOPE_*, 0..10
    u16 fogOffset; // G3X_SetFog offset, 15-bit depth where fogTable[0] starts
    u8 fogTable[32]; // density 0..127 (G3X_SetFogTable)
    BattleStageFileLighting lighting[BATTLE_STAGE_LIGHTING_MAX];
    // Weather haze: a fog grid that starts just in front of the platforms. With a lighting
    // haze h > 0 the renderer uses hazeShift/hazeOffset and the table
    // hazeBase + (hazeTable - hazeBase) * h / BATTLE_STAGE_HAZE_FULL
    u8 hazeShift;
    u8 hazePadding;
    u16 hazeOffset;
    u8 hazeBase[32]; // the distance fog above, resampled on the haze grid
    u8 hazeTable[32]; // full-strength haze (never below hazeBase)
} BattleStageFileAtmosphere;

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
    u32 atmosphereOffset; // BattleStageFileAtmosphere; 0 = none (unlit white, no fog)
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
    // BATTLE_STAGE_MESH_SCROLL: texcoord offset = amplitude * (sin(a), sin(2a)), a = 2pi * frame / period
    // (a figure eight that is 0 at frame 0)
    u8 scrollAmplitude[2]; // texels, s and t
    u16 scrollPeriod; // frames, > 0
} BattleStageFileMesh;

typedef struct BattleStageFileVertex {
    s16 pos[3]; // fx16, multiplied by header.vertexScale
    s16 texCoord[2]; // texels * 16 (G3_TexCoord units)
    u16 color; // GXRgb vertex colour (baked shading); 0x7FFF = unshaded. Unused by LIT meshes
    u32 normal; // GX_VECFX10 packed unit normal (G3_Normal); only used by LIT meshes
} BattleStageFileVertex;

#endif // POKEPLATINUM_BATTLE_BATTLE_STAGE_FORMAT_H
