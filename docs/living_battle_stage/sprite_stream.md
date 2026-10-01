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
- Megas;
- the Egg.

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
  - The PL_OTHERPOKE table is empty for now.
  - The step 1 index had no header (its first `u16` is 0); the readers still take it.
- **Every other member** is one stream:
  - a header with the animation's box in the canvas;
  - frame offsets, in order and on 4-byte boundaries;
  - `{frame, duration}` steps on the 60 Hz clock;
  - LZ77 frames that cover the box only.

The NARC is 27.4 MB (26.1 MiB). The ROM now uses 96.3 MB of a 128 MiB cartridge. A stream is
19 KB at the median, and members are capped at 96 KB. A stream over the cap drops its most
similar frames until it fits ("dropped" in `report.json`). Six faces lost frames:

| | dropped frames |
|---|---|
| Masquerain back | 127 |
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

**Canvas.** The canvas is 128x96: a whole texture row wide, with the classic 80x80 frame at
(24, 8). A Gen 5 frame is 96x96, centred, with the union of all frames standing on row 87.

**Fit.** Art taller than the room above the ground row (88 rows), or wider than the canvas,
is cropped at the top when it overflows by a few rows. Otherwise it is scaled down. 12 faces
are cropped (Charizard's front, Steelix's back, ...), and 12 are scaled down, to 0.75 at the
least (Fearow, Lugia, Ho-Oh, Hydreigon, Pidgeotto, Moltres).

**Back sprites.** Black/White draw back sprites at twice their size, so the Gen 5 back art is
half the size of Gen 4's. The tool scales the back frames up (nearest neighbour) by up to 2x,
in steps of 1/8. The scale is the largest that keeps the union no taller than the classic
frame (80) and no wider than the canvas (128). `report.json` lists every species.

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
- **Draw (`Bind`).** The draw hook binds the battler's texture and draws the 128x96 canvas
  around the classic frame's centre (`BattleStageStream_CanvasRect`). Mosaic,
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

- **Forms and Spinda.** The PL_OTHERPOKE table is empty, so the form species draw classic.
  Spinda's spots are painted on the classic frame only.
- **80x80 crop.** The other screens and the battle's move copies show only the classic window
  of the canvas. Wide or tall art loses what is outside it.
- **Doubles.** Not measured. Four streams hold about 40 KB, well inside the 128 KB floor, but
  four frame reads and decodes in one frame would pass the budget, so some battlers would wait.
- **Read cost.** Reads can't use DMA (see above), so each costs the game thread about 1 ms. A
  later step could read only when no HBlank DMA runs, or read during the VBlank wait.
- **Hatch.** The hatch screen opts in but hasn't been run.
- **Dropped frames.** Six large faces lost frames to the 96 KB cap (see Data).
- **Timing.** The GIF frame durations are used as-is, and haven't been checked against
  footage of the games.
- **Back scale.** The back scale is per species and capped at the classic frame's height. B/W
  draw backs at a flat 2x and let big mons run off the screen.
- **Stray files.** `gen5_stream.py` wrote `male_front.png` and `male_back.png` for the 15
  female-only species (Blissey, Chansey, Cresselia, ...). No `meson.build` lists them. Delete
  them, and stop the tool from writing them.
