# Gen 5 animated battle sprites (sprite stream)

This is step 2 of the Gen 5 sprite plan. Step 1 streamed Black/White's animated battle sprites
into the battle for 16 species and measured the cost. Step 2 does every species that has B/W
art. It reads the frames from the card while the battle runs, so a stream costs a few KB of
heap instead of the whole member. It also plays the animation on the summary screen, in the
Pokedex and on the evolution screen. It builds on sprites.md: in battle, the stage's sprite
mesh draws the stream in place of the classic 80x80 frame.

Species with a stream: 483, with 1152 streams. 93 species have their own female front and
back art. Species without a stream draw exactly as before:

- the form species, whose battle sprite comes from PL_OTHERPOKE: Arceus, Burmy, Castform,
  Cherrim, Deoxys, Gastrodon, Giratina, Rotom, Shaymin, Shellos, Unown, Wormadam;
- Spinda;
- the Egg.

The 11 Megas have no B/W art. Each Mega's classic back becomes a still stream (see Megas), and
its front stays classic.

## Data

`tools/gen5_sprites/gen5_stream.py` builds `res/prebuilt/battle/graphic/mon_stream.narc` from
the PokeAPI B/W animated GIFs. With no arguments it does every species. The GIFs are cached in
`~/.cache/gen5_sprites` and are not checked in, and so is each species' result, so a rerun
takes seconds. The tool's docstring has the member format:

- **Member 0** is the index, version 2: `{u16 version, numPokegra, numOtherpoke, reserved}`,
  then one `u16` member per PL_POKEGRA file, by `PokemonSpriteTemplate.character`
  (species * 6 + file: 0 female back, 1 male back, 2 female front, 3 male front), then one
  per PL_OTHERPOKE file.
  - 0 means no stream. A female file with 0 falls back to the male file's member.
  - The PL_OTHERPOKE table holds only the Mega backs, at each Mega's `spriteCharacter`.
  - The step 1 index had no header (its first `u16` is 0); the readers still take it.
- **Every other member** is one stream:
  - a header with the animation's box in the canvas and its draw scale in eighths
    (`u8 numFrames, scale`; 0 reads as 8, 1:1, so step 1 members still work);
  - frame offsets, in order and on 4-byte boundaries;
  - `{frame, duration}` steps on the 60 Hz clock;
  - LZ77 frames that cover the box only.

The NARC is 24.8 MB (23.6 MiB). The ROM now uses 93.7 MB of a 128 MiB cartridge. A stream is
17 KB at the median, and members are capped at 96 KB. A stream over the cap drops its most
similar frames until it fits ("dropped" in `report.json`). Six faces lost frames:

| | dropped frames |
|---|---|
| Masquerain back | 117 |
| Yanmega back | 79 |
| Vespiquen back | 74 |
| Masquerain front | 9 |
| Magmortar back | 1 |
| Yanmega front | 1 |

The tool also rewrites, from the same art, each species' `{male,female}_{front,back}.png`,
`normal.pal` and `shiny.pal`. The PNGs hold frame A and a mid-loop frame B, cut from the
canvas's classic window. So everything that still draws the classic sprite matches the
stream, and so does the battler's palette slot.

- `shiny.pal` is mapped index for index: each colour is paired with the shiny colour at the
  same pixels of the shiny GIF, so a battler's shiny palette slot just works.
- The tool sets `y_offset` in `sprite_data.json` to 0, because the art already stands on the
  frame's last row. `res/pokemon/meson.build` lists every `sprite_data.json` as a dependency of
  `height.narc`, so that edit rebuilds the NARC.

**Canvas.** The canvas is 128x96: a whole texture row wide. A Gen 5 frame is 96x96, centred,
with the union of all frames standing on row 87. At 1:1 the classic 80x80 frame is the
canvas window at (24, 8).

**Scale.** A member's scale is in eighths. Fronts are 1:1. Backs are stored 1:1 and drawn at a
flat 1.75x (14/8). Black/White draw them at 2x, but at 2x Garchomp's back is about 166 px tall,
more than the 144 px above the textbox; at 1.75x it just fits. Every path maps a classic frame
pixel (x, y) to the texel `u = ((x - 40) * 8 + 64s) / s`, `v = ((y - 80) * 8 + 88s) / s`
(`MON_STREAM_TEXEL_U/V`, nearest neighbour), so the canvas's centre column stays on the frame's
centre and the ground row stays on its bottom row. At 1.75x the classic window of a back holds
only its bottom-centre 46x46 texels; the PNGs, the move copies and the other screens all show
that window.

**Sink.** The healthbars are OBJs, drawn over the 3D layer, so a tall back reaching the
opponent's HP box (its bottom is about 86 screen px above the player's feet) has its head
hidden behind it. Black/White have the same layering, but their textbox is on the touch screen,
which leaves them 48 more rows. So a back taller than 100 frame px sinks by the excess, at most
40 (`BACK_ROOM`, `BACK_MAX_SINK` in `battle_stage_stream.c`), and its feet go behind the
textbox, the way B/W's screen edge crops tall backs. Garchomp, Torterra and 67 others sink the
full 40, Lucario 15, Staraptor 19; about half the backs (Budew, Finneon, ...) don't move. The
blob shadow stays on the ground. The sink is in `BattleStageStream_CanvasRect`, so every draw
of the battler, the faint slide and the send-out included, takes it; the move copies don't.

**Megas.** B/W has no Megas, and their classic backs, drawn 1:1, came out about half the size
of the B/W backs around them (Mega Lucario 65 px against Lucario's 116). The tool makes each
Mega's frame A from `forms/mega/back.png` a one-frame stream in the Mega's own palette, standing
on the ground row, at the scale that matches its base form's back height: at least 1.75x, at
most 2x (`MON_STREAM_MAX_SCALE`). Lucario, Alakazam, Empoleon and Staraptor get 1.75x; Gengar,
Gyarados and Torterra 1.875x; Garchomp, Gardevoir, Infernape and Scizor 2x. The sink applies the
same way (Mega Garchomp 36, Mega Lucario 13). The base species' `y_offset` is 0, and the Mega
uses it too, so the stream stands where the base form does. The members are in `report.json`
under `megas`. The fronts aren't streamed: at 1:1 most are already about as big as their
base form's B/W front. Mega Gyarados is the smallest, at about two thirds of Gyarados.

**Fit.** Art taller than the room above the ground row (88 rows), or wider than the canvas, is
cropped at the top when it overflows by a few rows; otherwise a front is scaled down. Backs are
never scaled down: at 1.75x the room's top rows are off the screen anyway, so they are only
cropped. (A back wider than 137 texels would also pass the mesh's 240-pixel quad; the canvas is
narrower.)

- Fronts: 5 cropped (Yanmega, Kingdra, ...), 7 scaled down, to 0.75 at the least (Pidgeotto,
  Hydreigon, Lugia, Fearow, Ho-Oh, Rayquaza, Moltres).
- Backs: 11 cropped. Fearow and Hydreigon lose 24 rows, Rayquaza 19, Lugia 10 rows and 18
  columns, Ho-Oh 9, the rest 7 or fewer.

`report.json` lists every species.

## Runtime

One format header serves both runtimes: `include/pokemon_sprite_stream.h`. It has the index
lookup (`MonStream_IndexEntries`: v1 and v2, the female fallback, no Spinda), the member checks
(`MonStream_IsValid`, `MonStream_FrameEnd`, `MonStream_IsFrameValid`, which checks a frame's
LZ77 header before decoding) and `MonStream_ReadFile`. A member or frame that fails a check
draws the classic sprite.

**No card DMA.** Every stream read takes the CPU path, never card DMA. The card DMA is an auto
DMA, and so is the HBlank DMA that the battle's wavy scrolls restart every VBlank (Extrasensory,
for one). If either starts while the other runs, `MIi_CheckAnotherAutoDMA` stops the game with
an `OS_Panic`. `CARDi_TryReadCardDma` uses DMA only for whole 512-byte pages into a destination
on a 32-byte boundary. So the battle reads into a buffer 4 bytes past such a boundary, and
`MonStream_ReadFile` reads the first word alone when the destination is aligned. Before this
fix, Extrasensory froze the battle whenever a battler's stream was animating.

### Battle (`src/battle/battle_stage_stream.c`)

- **VRAM.** One `NNS_GfdAllocTexVram` of 4 x 6 KB, one 128x96 4bpp texture per battler. It
  must end at or below 0x20000, like the arena textures. Without it, or without the index,
  every battler draws classic.
- **Load.** The index (member 0, 6 KB) is read once per battle. When a battler's sprite
  template changes, the runtime reads only the stream's tables. It then allocates a 6 KB copy
  of the texture and a buffer for the largest frame (2 KB at most).
  - The load is refused when it would leave less than 128 KB of `HEAP_ID_BATTLE` free. The
    battler then draws classic.
  - The classic frame shows until the first stream frame is in.
- **Frame reads.** Each battler has its own `FSFile` on the NARC. It asks for the next frame
  the steps change to, one frame ahead, with `FS_ReadFileAsync`.
  - The card thread outranks the game's, so the read is done before the call returns.
  - A step whose frame isn't in yet holds the step before it (`stallFrames`).
  - A failed read drops the stream for good; the battler draws classic.
- **Each frame (`BeginFrame`).** The runtime advances the steps by VBlank count. When the step's
  frame is in, it decompresses it (`MI_UncompressLZ8`) and copies the box rows into the texture
  copy. Then it queues those rows on the battle's `VramTransfer` list.
  - Budgets for all battlers together: 1600 ticks (3 ms) of decoding and 12 KB of upload a
    frame. A battler past the budget waits a frame, and the order turns every frame.
  - Whole textures are sent after a menu took the VRAM.
  - `FREEZE_IDLE` holds step 0, the classic frame A.
- **Draw (`Bind`).** The draw hook binds the battler's texture and draws the canvas around
  the classic frame (`BattleStageStream_CanvasRect`): the whole 128x96 canvas at 1:1, the
  stream's box at its scale otherwise. Mosaic,
  `excludeIdentity` and the `NO_SPRITE_STREAM` debug flag (bit 6) fall back to the classic
  texture.
  - A partial draw (the faint slide, the send-out reveal) keeps its cuts where the window cuts
    the classic frame. On each side where the window reaches the frame's edge it takes the
    canvas out to its own edge, so wide backs don't lose their sides when the slide starts.
  - Frames queued this frame can be bound: the VBlank transfer lands before the hardware
    renders this frame's geometry.

### Other battle paths

- **Arena hidden.** With the arena hidden but its texture VRAM kept (the debug toggle, a move's
  backdrop: `BattleStage_KeepsTextureVram`), the streams go on, and the draw hook draws the
  canvas flat (`DrawFlatStream`). Hiding the arena then doesn't snap a battler back to frame A.
- **Move copies.** A move's BG or OAM copy of a battler (`LoadPokemonSpriteIntoBg`,
  `AddPokemonSprite`, `ov12_022234F8`) takes the classic 80x80 window of the frame on screen
  (`BattleStage_GetStreamFrameTiles`), not frame A. Contests keep frame A.
- **Overlay copies.** Copies that only sit over the battler (SpriteToOAM, the send-out copies)
  stay hidden while it is streamed (`BattleStage_IsSpriteStreamed`), so frame A doesn't double
  the animated sprite.
- **Transform and Substitute.** Transform streams the target's art. The Substitute doll is
  classic.

### Other screens (`src/pokemon_sprite_stream.c`)

`PokemonSpriteManager` streams the sprites a screen opts in to
(`PokemonSpriteManager_SetStreamMask`). Each drawn frame, it cuts the stream frame to the
classic 80x80 window and writes it over the sprite's frame in the manager's char data. The rows
that changed go to VRAM at the next VBlank.

- **Load.** A stream of 24 KB or less is held whole when that leaves twice the screen's heap
  spare. Otherwise only its tables are held, and each frame is read from the card when it is
  drawn (paged).
- **Opt-ins.** The summary screen, the Pokedex entry and the evolution screen opt in. So does
  the hatch screen, which is untested.
- **Fallbacks.** Flipped vertically, mosaic, no heap and a bad frame draw classic.
- **Off.** `SetStreamMask(0)` frees everything the streams hold, the open NARC included. The
  Pokedex calls it when an entry closes.
- **Battle.** A manager the battle stage draws from must not opt in.

## Measurements

These come from the emulator, read from `sSpriteStreamStats` (battle) and
`sMonSpriteStreamStats` (the other screens). 1 tick = 1.91 us. Battle: a wild battle in
Eterna Forest, Finneon against a wild Budew or Buneary (two critic runs; the worse value is shown).

| Battle | |
|---|---|
| Upload, worst frame | 10.3 KB (two battlers changing frame at once; budget 12 KB) |
| Decode and copy, worst frame | 1635 ticks = 3.1 ms (both battlers; the second may start just under the 1600 budget) |
| Frame read, worst | 645 ticks = 1.2 ms, on the game thread (the CPU copies it) |
| Stream load, worst | 1021 ticks = 1.9 ms (step 1: 54 ms) |
| Stalls | 2 to 3 steps held in the first 120 frames, while the first frames came in |
| Heap held | 20 KB for two streams with the index (step 1: 92 KB), 368 KB still free |
| VRAM | 24 KB at 0x14400 |

| Screen | Summary | Pokedex | Evolution |
|---|---|---|---|
| Streams | 1, paged | 1, whole (Turtwig) or paged | 2, paged |
| Load, worst | 1836 ticks = 3.5 ms | 5088 ticks = 9.7 ms (whole) | 1601 ticks = 3.1 ms |
| Frame read, worst | 639 ticks = 1.2 ms | 845 ticks = 1.6 ms | 626 ticks = 1.2 ms |
| Write a frame, worst (read included) | 1807 ticks = 3.5 ms | 1874 ticks = 3.6 ms | 1682 ticks = 3.2 ms |
| Upload, worst frame | 3.1 KB | 3.1 KB | 6.3 KB |
| Heap left free | 36 KB | 87 to 97 KB | 113 KB |

Texture VRAM can only be written while the 3D engine isn't reading it. That leaves about
1.4 ms after VBlank begins (the engine starts the next frame at line 214). At DMA speed that is
about 40 KB, so 10 KB in a frame fits with room left for the battle's own transfers.

The card timing is the emulator's. A frame read costs the game thread about 0.3 ms a page.

## Known gaps (later steps)

- **Forms and Spinda.** The PL_OTHERPOKE table has only the Mega backs, so the form species
  draw classic. The Mega backs are still frames.
  Spinda's spots are painted on the classic frame only.
- **80x80 crop.** The other screens and the battle's move copies show only the classic window
  of the canvas. Wide or tall art loses what is outside it, and a back shows only its
  bottom-centre 46x46 texels.
- **Doubles.** Not measured. Four streams hold about 40 KB, well inside the 128 KB floor, but
  four frame reads and decodes in one frame would pass the budget, so some battlers would wait.
- **Read cost.** Reads can't use DMA (see above), so each costs the game thread about 1 ms. A
  later step could read only when no HBlank DMA runs, or read during the VBlank wait.
- **Hatch.** The hatch screen opts in but hasn't been run.
- **Dropped frames.** Six large faces lost frames to the 96 KB cap (see Data).
- **Timing.** The GIF frame durations are used as-is, and haven't been checked against
  footage of the games.
- **Stray files.** `gen5_stream.py` wrote `male_front.png` and `male_back.png` for the 15
  female-only species (Blissey, Chansey, Cresselia, ...). No `meson.build` lists them. Delete
  them, and stop the tool from writing them.
