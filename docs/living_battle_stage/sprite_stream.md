# Gen 5 animated battle sprites (sprite stream)

This is step 3 of the Gen 5 sprite plan. Step 1 streamed Black/White's animated battle sprites into
the battle for 16 species and measured the cost. Step 2 did every species that had B/W art, from the
PokeAPI B/W GIFs. Step 3 (bw2vis, workstream sprite-source) re-sources every stream from Black 2/
White 2's own sprite data, played the way BW2's battle plays it. The frames are read from the card while
the battle runs, so a stream costs a few KB of heap instead of the whole member. The animation also
plays on the summary screen, in the Pokedex and on the evolution screen. It builds on sprites.md: in
battle, the stage's sprite mesh draws the stream in place of the classic 80x80 frame.

Streams: 523 species (every species with B/W art, the 43 Gen 5 species added after Arceus included),
1390 faces in 1369 members. 96 species have their own female front and back art. The 12 form species
have a stream per form (150 form faces, see Forms), and so has the Substitute doll. Without a stream,
and drawn exactly as before:

- Spinda (see Spinda);
- Arceus's ??? form (BW2 has no ??? type);
- the Egg.

The 11 Megas have no B/W art. Each Mega's classic back and front become still streams (see Megas).

## Data

`tools/gen5_sprites/gen5_stream.py` builds `res/prebuilt/battle/graphic/mon_stream.narc`. With no
arguments it does every species, the forms and the doll; each unit's result is cached in
`~/.cache/gen5_sprites/built`, so a rerun takes seconds (a cold run about 15 s on the devserver).

**Source.** pokebw2's extracted MCSS data (`/data/repos/pokebw2/res/pokemon/<species>[/form_<n>]/`,
read-only; the battle side of this hack already uses B/W art, see the bw2vis asset policy): the NMAR
multi-cell animation, the NMCR multi-cells, the NANR cell animations, `info.bin` (MCSS's quad table
and idle nodes), the 256x128 atlas (`front.png`, `front_female.png`, `back*.png`) and `normal.pal`/
`shiny.pal`. Species map to pokebw2's folders by national dex number (`dex_numbers.json` for the species
after Arceus; pokebw2's `generated/species.txt` gives the folder). A species pokebw2 lacked would fall
back to the step 2 path, the PokeAPI B/W animated GIFs (`--gif` builds everything that way); today none
does.

**Playback.** `tools/gen5_sprites/mcss.py` plays a face one 60 Hz tick at a time and draws it, ported
from pokebw2:

- NitroSystem's animation controller (`lib/nnsys/src/g2d/g2d_Animation.c`), line for line: loop start,
  the four play modes, zero-length frames, the end-of-sequence callback.
- The multi-cell animation in share-cell-animation mode (`g2d_MultiCellAnimation.c`): at each NMAR
  keyframe every node's cell animation is bound again, and a node in play mode CONTINUE is played on to
  the multi-cell animation's total time.
- MCSS's draw (`src/system/mcss.c` `MCSSSys_Draw`, `MCSS_DrawQuad`): multi-cell offset, rotation and
  scale; node position plus cell translation; cell rotation and scale; quad offset and size. Nodes from
  node 0 with the depth stepping back per quad, so node 0 and a cell's second quad are in front. Ortho
  ("flat") at one texel per pixel, nearest texel at each pixel centre. Tick 0 matches pokebw2's
  `front_single.png` stills to within a few pixels.
- The battle's loop (`src/ov168/btlv_mcss.c` `BtlvMcss_Main`, `BtlvMcss_OnAnimationEnd`): a face
  without idle data restarts the animation the frame after its loop ends, so its loop is the pose at the
  loop's end followed by ticks 1 .. L-1; a face with idle data runs on into the next loop until an idle,
  and the first loop (ticks 0 .. L-1) is kept.

So the frames, their durations and the loop length are BW2's, every part moves at full rate, and the
colours are BW2's normal and shiny palettes, index for index. Each distinct frame is stored once; the
steps give each its duration in 60 Hz ticks.

**Classic files.** The tool also writes, from the same frames, each species'
`{male,female}_{front,back}.png`, `normal.pal` and `shiny.pal` (BW2's palettes, colour 0 the repo's
transparent grey), each form's `forms/<form>/{front,back}.png` and palettes, and the doll's
`.shared/substitute_{front,back}.png` and `substitute.pal`. The PNGs hold frame A (step 0) and a mid-loop
frame B, cut from the canvas's classic window, so everything that still draws the classic sprite matches
the stream, and so does the battler's palette slot. Their first four pixels are always transparent:
pokegra and otherpoke NCGRs are encrypted front to back with the `.png.key` (nitrogfx `-scan`) and
the game takes the first encrypted u16 as the seed, which only holds when those pixels are 0; otherwise the
whole classic sprite decodes to noise. In `sprite_data.json` the tool sets `y_offset` to 0 and the
front's `addl_y_offset` to the species' lift (Hover); in `res/prebuilt/poketool/pokegra/height_o.narc` it
sets the y_offset of every streamed form face and of the doll to 0 (`LoadPokemonSpriteYOffset` reads
HEIGHT_O for the form species; its index is the PL_OTHERPOKE character, plus 2 from Shaymin on, and 134
and 135 are the doll's).

### Member format

- **Member 0** is the index, version 3: `{u16 version, numPokegra, numOtherpoke, reserved}`, then one
  `u16` member per PL_POKEGRA file, by `PokemonSpriteTemplate.character` (species * 6 + file: 0 female
  back, 1 male back, 2 female front, 3 male front), then one per PL_OTHERPOKE file.
  - 0 means no stream. A female file with 0 falls back to the male file's member.
  - The PL_OTHERPOKE table holds the form species' forms (their characters in `BuildPokemonSpriteTemplate`,
    which is how the form index reaches the lookup), the Mega backs and fronts, and the doll (the two
    PL_OTHERPOKE files after the species' ones, `SUBSTITUTE_BACK_NCGR`/`SUBSTITUTE_FRONT_NCGR`).
  - Identical members are stored once (Arceus's forms differ only in their palettes).
  - Version 2 had the same index with 8-byte stream headers. The runtimes take only version 3; any other
    index draws everything classic.
- **Every other member** is one stream (`MonStreamHeader`, `include/pokemon_sprite_stream.h`):
  - a 12-byte header: `u8 numFrames, scale` (eighths; 8 fronts, 14 backs, 14 to 16 Mega backs),
    `u16 numSteps`, the animation's box in the canvas (`u8 left, width` in bytes, `top, height` in rows),
    `u8 idleKind, numIdleSteps, u16 reserved` (see Idle data);
  - frame offsets, in order and on 4-byte boundaries;
  - the loop's `{u8 frame, u8 duration}` steps on the 60 Hz clock, then the idle clip's;
  - LZ77 frames that cover the box only.

### Idle data

What BW2 does at the end of a loop (pokebw2 `btlv_mcss.c` `BtlvMcss_OnAnimationEnd` :2055-2091,
`BtlvMcss_IdleTask` :1921-1954, `BtlvMcss_IdleNodeCallback`): a face whose `info.bin` idle node count is
0xFF just restarts. Any other face rolls an idle, with a chance of 1/3, then 1/2, then 1 at successive
loop ends (back to 1/3 after an idle). An idle switches to the face's second NMAR sequence if it has one
(always a single keyframe: a pose, often eyes shut), stops the multi-cell clock and every node's cell
animation except the listed idle nodes, holds for 48, 56 or 64 frames (`data_ov168_021f4184`, at random),
then restarts sequence 0 from tick 0.

| `idleKind` | BW2 | idle steps | faces (species' male faces) |
|---|---|---|---|
| `MON_STREAM_IDLE_NONE` 0 | idle node count 0xFF (Zubat, Beautifly, Hydreigon...) | none | 43 fronts, 43 backs |
| `MON_STREAM_IDLE_FREEZE` 1 | no second sequence | one step: step 0's frame (what is on screen as the loop wraps), 64 ticks | 442 fronts, 443 backs |
| `MON_STREAM_IDLE_POSE` 2 | a second sequence: the pose, with the idle nodes (flames, Gastly's gas...) still moving, the rest held | the pose rendered at 60 Hz for 64 ticks, one step per change (1 step without idle nodes) | 38 fronts, 37 backs |

The idle clip's frames are in the member's frame table (shared when identical), so the idle nodes need no
per-part data at runtime. `numIdleSteps` is 0 exactly when `idleKind` is NONE. `MonStream_Steps` and
`MonStream_IdleSteps` give the two step tables; in battle, `BattleStageStream_GetHeader(battler)` returns
the loaded member (header, offsets, both step tables, already in RAM; NULL for a classic battler). The
battle plays it (bw2vis:idle, Runtime "Special idle"): at a loop wrap it rolls BW2's chance, plays the
idle steps for the wait and restarts the loop at step 0.

### Counts and sizes

The NARC is 31.0 MB (26.98 MB in step 2). The ROM now uses 101.1 MB of its 128 MiB (97.2 MB before;
measured on main plus this work, before the other bw2vis workstreams).
A stream is 18 KB at the median (17.7 KB before). Members stay capped at 96 KB (`MAX_MEMBER`, kept for
the ROM size) and at 255 frames (a step's frame is a u8). A stream over either drops its most similar
frames: the frame before it in the loop takes its steps, so every step keeps its duration and the loop its
BW2 length ("dropped" in `report.json`). The faces that lost frames are the fast wing-beaters and the
busiest bodies:

| | distinct frames | dropped |
|---|---|---|
| Yanmega front / back | 351 / 351 | 269 / 265 |
| Vespiquen front / back | 308 / 320 | 210 / 216 |
| Masquerain front / back | 230 / 232 | 122 / 118 |
| Scizor front / back (female the same) | 183 / 156 | 99 / 63 |
| Beedrill front | 177 | 78 |
| Tentacruel front / back | 110 / 112 | 32 / 37 |
| Magmortar front / back | 92 / 95 | 28 / 26 |
| Swoobat front / back | | 27 / 21 |
| Gastly front / back | 132 / 132 | 16 / 4 |
| Dodrio front (female 10), Yanma front | | 9, 6 |

(Step 2's GIFs had 10 to 20 fps steps; the kept frames are still at least that dense.)

### Canvas, scale and hover

**Canvas.** The canvas is 128x96: a whole texture row wide. The foot point (MCSS's origin, where BW2's
battle puts the Pokemon) is on the canvas's centre column (64) and on the top edge of row 88, the first
row below the classic frame's last; art may reach 8 rows below it (Turtwig, Excadrill). A face is shifted
sideways only as far as it must to fit (Gyarados, Gorebyss). At 1:1 the classic 80x80 frame is the
canvas window at (24, 8).

**Scale.** A member's scale is in eighths. Fronts are 1:1, as in BW2. Backs are stored 1:1 and drawn
at a flat 1.75x (14/8); BW2 draws them at 2x (the layout workstream owns the drawn scale). Every path
maps a classic frame pixel (x, y) to the texel `u = ((x - 40) * 8 + 64s) / s`,
`v = ((y - 80) * 8 + 88s) / s` (`MON_STREAM_TEXEL_U/V`, nearest neighbour), so the canvas's centre column
stays on the frame's centre and the ground row on its bottom row. At 1.75x the classic window of a back
holds only its bottom-centre 46x46 texels; the PNGs, the move copies and the other screens all show that
window.

**Hover.** BW2 has no altitude table: every battler stands at the same y, and a floater's hover is in
its art, above the foot point (pokebw2 `btlv_mcss.c:192-195`). Step 2 stood every animation's lowest
point on the ground row and kept Platinum's `addl_y_offset`, tuned for Platinum's art, so 120 species sank
into the platform (Metagross 12 px), 34 grounded ones floated (Whimsicott 18) and the Gen 5 species had
their Sinnoh stand-in's value (`gen5_species.py`). Now:

- Backs carry their hover in the canvas, exactly as BW2 draws them (119 backs hover).
- A front is drawn down in the canvas by its species' lift, the hover of its lowest point over the whole
  loop and idle clip (the least over the species' front faces: male, female, forms), and
  `addl_y_offset` (the battle's shadow height, which raises enemy fronts: `battle_display.c`,
  `pokemon_sprite.c`) is that lift. Every front frame then lands where BW2 draws it relative to the foot
  point; floaters keep their canvas room, and move animations aiming at `MON_SPRITE_SHADOW_HEIGHT` aim at
  the body. 118 species have a lift (Wingull 26, Zubat and Magnemite 22, Woobat 14, Bronzor and Frillish 7); a floater that dips to
  the ground somewhere in its loop has lift 0 and its hover in the canvas (Gastly, which sinks to the
  ground mid-loop; Hydreigon; Jellicent).
- Measured in battle (`/tmp/bw2vis/sprite-source/README.md`): every enemy front's BW2 foot point lands on
  the same screen row.

**Sink.** The healthbars are OBJs, drawn over the 3D layer, so a tall back reaching the opponent's HP
box (its bottom is about 86 screen px above the player's feet) has its head hidden behind it. BW2 has the
same layering but another layout: its player foot point is about 20 px below the bottom of the top screen,
so BW2 crops tall backs at the screen edge. (Its message window is on the top screen too, rows 152-184,
and fades out before move animations: `btlv_scu.c:420,432`. Step 2 said it was on the touch screen; it
isn't.) So a back taller than 100 frame px above its feet sinks by the excess, at most 40 (`BACK_ROOM`,
`BACK_MAX_SINK` in `battle_stage_stream.c`), and its feet go behind the textbox. A back's baked hover
counts in that height, so a high floater's back sinks too (Zubat 24). The shadow stays on the
ground. The sink is in `BattleStageStream_CanvasRect`, so every draw of the battler, the faint slide,
the send-out and the move copies included, takes it.

**Fit.** A front that would reach more than 8 rows above the canvas once lifted, or is wider than it,
is scaled down about its feet (Pillow's box filter, colours back to the palette); one at most 8 rows over
loses its top rows. Backs are never scaled down: at 1.75x the room's top rows are off the screen anyway,
so they are only cropped, and their sides are cut to the canvas.

- Fronts scaled down: Pidgeotto 0.76, Hydreigon 0.82, Lugia 0.84, Fearow 0.85, Ho-Oh 0.87, Swoobat
  0.89, Rayquaza 0.91, Moltres 0.98. Cropped at the top: Giratina Origin 9 rows, Yanmega 6, Kingdra and
  Charizard 3, Mesprit 2, Chandelure, Giratina, Rayquaza 1.
- Backs cropped at the top: Hydreigon 23 rows, Pidgeotto 22, Fearow 21, Lugia 18 (and 18 columns),
  Rayquaza 13, Latios 12, Chandelure 11, Mismagius and Swoobat 6, Kingdra 5, Ho-Oh 4, the rest 2 or fewer.
- Art more than 8 rows below the feet loses its bottom rows: Yanmega back 4, Excadrill back 2, Conkeldurr
  front 1. Shifted sideways to fit: Gyarados front 10 px, Moltres front 5, Gorebyss back 5, Drapion back 1.

`report.json` lists every face: source folder, loop length, distinct and kept frames, steps, idle kind
and steps, bytes, box, lift, hover, shrink, crops, shift.

### Forms

The form species draw from PL_OTHERPOKE (`BuildPokemonSpriteTemplate`), so each form face's stream is at
its PL_OTHERPOKE character: the form index reaches the stream through the template. The tool reads each
species' `meson.build` (`otherpoke_index`) for the characters and palette files, and maps our form
directories to pokebw2's (`FORM_BW2`, checked against pokebw2's `form_<n>.json` types):

| species | forms streamed |
|---|---|
| Unown | 28: A-Z, !, ? (one shared palette, as in BW2) |
| Arceus | 17 types (BW2's forms are palettes on the base art); ??? stays classic |
| Rotom | 6 | 
| Castform, Deoxys | 4 each (Deoxys: one shared palette) |
| Burmy, Wormadam | 3 each |
| Shellos, Gastrodon, Cherrim, Giratina, Shaymin | 2 each |

### Substitute doll

BW2's doll (`res/pokemon/shared/substitute`, one still keyframe front and back) is a stream at the doll's
two PL_OTHERPOKE characters: the front 1:1, the back at the backs' 1.75x. Its classic PNGs and
`substitute.pal` are rewritten from it, and its HEIGHT_O y_offsets (134, 135) are 0.

### Megas

B/W has no Megas. Each Mega's classic back, drawn 1:1, came out about half the size of the B/W backs
around them, so frame A of `forms/mega/back.png` is a one-frame stream in the Mega's own palette,
standing on the ground row, at the scale that matches its base form's back height: at least 1.75x, at
most 2x (`MON_STREAM_MAX_SCALE`). Frame A of `forms/mega/front.png` is a one-frame stream at 1:1, standing
on the ground row: the Mega shares its base species' `y_offset` (0) and `addl_y_offset` (the B/W art's
lift, 0 for all 11 bases), so its classic front would float by its own blank rows (Mega Gyarados 12).
Members: `report.json` under `megas`.

### Spinda

Not streamed. BW2 paints Spinda's spots into the MCSS atlas at load, per personality
(`mcss_tool.c` `MCSS_DrawSpindaSpots`: two copies of four spots, one for the head cells sampled from atlas
rows 0-24, which rotate by up to 20 degrees in a quarter of the front's frames, one for the face cell
from rows 48-96), and the parts then move with them. A pre-rendered stream can't carry 2^32 spot layouts,
and painting them at runtime needs each frame's atlas-to-canvas map for those cells plus a painter in
both stream runtimes. Platinum's classic spot overlay can't simply be laid on a stream frame either: it
paints fixed places of the classic frame, which the moving head leaves. So Spinda keeps its classic
sprite, whose spots are right for its personality.

## Runtime

One format header serves both runtimes: `include/pokemon_sprite_stream.h`. It has the index
lookup (`MonStream_IndexEntries`: version 3 only, the female fallback, no Spinda), the member checks
(`MonStream_IsValid`, which also checks the idle steps, `MonStream_FrameEnd`, `MonStream_IsFrameValid`,
which checks a frame's LZ77 header before decoding), the step tables (`MonStream_Steps`,
`MonStream_IdleSteps`) and `MonStream_ReadFile`. A member or frame that fails a check
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
- **Frame reads.** Each battler has its own `FSFile` on the NARC. It asks, one draw ahead, for the
  frame of the step the next draw lands on (`StepAfter`: as many vblanks on as the last draw took,
  at the battler's rate), or else the next frame the steps change to, with `FS_ReadFileAsync`.
  - The card thread outranks the game's, so the read is done before the call returns.
  - The battle draws every second vblank and B2W2's steps can last one, so the steps skip the frames
    no draw lands on, and their time never stops: a step whose frame isn't in yet leaves the frame
    on screen one draw longer (`stallFrames`). Step 2 held the step instead, which slowed B2W2's
    fast loops (Vespiquen by 11%).
  - A failed read drops the stream for good; the battler draws classic.
- **Each frame (`BeginFrame`).** The runtime advances the steps by VBlank count. When the step's
  frame is in, it decompresses it (`MI_UncompressLZ8`) and copies the box rows into the texture
  copy. Then it queues those rows on the battle's `VramTransfer` list.
  - Budgets for all battlers together: 1600 ticks (3 ms) of decoding and 12 KB of upload a
    frame. A battler past the budget waits a frame, and the order turns every frame.
  - Whole textures are sent after a menu took the VRAM.
  - `FREEZE_IDLE` holds step 0, the classic frame A.
- **Conditions (as B/W).** `battle_stage_sprites.c` (`UpdateConditions`) reads each
  battler's healthbar every frame: the HP colour and status it shows. It sets the battler's
  rate (`BattleStageStream_SetRate`, of 256), which scales the vblanks the steps count and
  the breathing.
  - The values come from disassembling pokeblack's overlay 94: the battle sprites' per-frame
    update at 0x021FEBAC, which reads the healthbar the same way. Which of its cases is which
    status is inferred from the colours and behaviour, and its timings assume it runs once a
    60 Hz frame.
  - With no status, red or empty HP plays at 85/256 (B/W's 0x555 of 0x1000, a third) and
    green or yellow at full speed. Asleep is a flat 85/256, whatever the HP.
  - Paralysis, poison and burn don't set the speed: it stays what it was when the status
    began, as in B/W. Frozen holds the frame on screen and keeps that speed for when it thaws.
  - Frozen tints the palette a steady GX_RGB(15,15,31) at 8/16. Paralysis, poison and burn
    pulse GX_RGB(15,15,0), (15,0,15) and (15,0,0): 0 up to 12/16 and back, a step every 26
    frames (624 frames round). Each battler has its own pulse, back to 0 when its status
    changes. Sleep has no tint. `FREEZE_IDLE` holds the pulse at 12/16.
  - The tint is `PokemonSpriteManager_SetTint`: `BufferPokemonSpritePlttData` blends the
    unfaded palette toward the colour when no palette fade holds the sprite, so a move's fade
    (a hit flash) runs on the untinted colours and the tint comes back after it. It colours
    the classic sprite as well; the rates only reach the streams and the breathing.
  - The Substitute doll takes no tint, and the mon's condition waits until it comes back. The
    doll is told by its sprite template (pl_otherpoke's doll members).
  - No healthbar (hidden, the send-out, a faint) keeps the battler's last rate and tint, as
    B/W does. A new mon (an inactive sprite, or a different sprite template) starts at full
    speed with no tint.
  - Special idle (bw2vis:idle): at a loop's end B/W may hold the mon for 48-64 frames; the
    stream plays it as a second step table, from the member's idle clip or, without one, the
    loop's first frame held (sprites.md, "Gen 5 motion").
  - Still missing: B/W closes the eyes asleep and blinks at random (1 in 100 a frame, about
    5 frames shut). The streams carry no eyes-shut frames beyond the POSE idle clips (BW2's
    second sequence, 47 species).
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
- **Move copies.** (bw2vis:idle) A move's OAM copy of a streamed battler (`AddPokemonSprite`) is
  drawn by the stage from the live stream frame at the mesh's scale, its 2D tiles blank; a BG2
  copy (`LoadPokemonSpriteIntoBg`) is the live frame at the mesh's scale in BG2's tiles (sprites.md,
  "Gen 5 motion", "Move copies"). `ov12_022234F8`'s copies and contests keep the classic 80x80
  window of the frame on screen (`BattleStage_GetStreamFrameTiles`), contests frame A.
- **Overlay copies.** Copies that only sit over the battler (SpriteToOAM, the send-out copies)
  stay hidden while it is streamed (`BattleStage_IsSpriteStreamed`), so frame A doesn't double
  the animated sprite.
- **Transform and Substitute.** Transform streams the target's art, form included. The Substitute
  doll streams BW2's doll (still, one frame).

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

- **Spinda.** Classic (see Spinda).
- **Blink.** BW2's random blink (a visibility flicker, `BtlvMcss_Blink`) needs no art; the idle
  workstream owns it with the special idle (Idle data).
- **Loops 2 and 3 of an idling face.** BW2 runs an idling face's loop on (up to three times before an
  idle), and a node in CONTINUE mode whose length doesn't divide the loop's then shows other phases than
  in the first loop. The stream holds the first loop only.
- **Dropped frames.** 22 large faces lost frames to the 96 KB and 255-frame caps (see Counts and sizes);
  their timing stays BW2's. A member format with frames stored as differences was tried and came out
  larger (XOR against frame A: 1.23x), since whole bodies move.
- **Back scale.** Backs are drawn at 1.75x, BW2 at 2x (the layout workstream owns it). Backs whose BW2
  art hovers high also sink (see Sink), which eats part of their hover (Zubat: 24 of its 42 screen px).
- **80x80 crop.** The other screens show only the classic window of the canvas. Wide or tall art
  loses what is outside it, and a back shows only its bottom-centre 46x46 texels. The battle's
  move copies no longer do (bw2vis:idle), except `ov12_022234F8`'s.
- **Mega fronts on the classic path.** With the stage off, a Mega front draws its classic frame with the
  base species' offsets (both 0 now), so it stands its blank rows above the ground (Mega Gyarados 12 px;
  4 px with step 2's Platinum offset).
- **Doubles.** Not measured. Four streams hold about 30 KB, well inside the 128 KB floor, but
  four frame reads and decodes in one frame would pass the budget, so some battlers would wait.
- **Read cost.** Reads can't use DMA (see above), so each costs the game thread about 1 ms. A
  later step could read only when no HBlank DMA runs, or read during the VBlank wait.
- **Hatch.** The hatch screen opts in but hasn't been run. The Egg has no stream (BW2's Egg is MCSS,
  26 keyframes, but it is not a battle sprite).
