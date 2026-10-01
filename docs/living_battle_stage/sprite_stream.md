# Gen 5 animated battle sprites (sprite stream prototype)

This is step 1 of the Gen 5 sprite plan. It streams Black/White's animated battle sprites into
the battle for a few species, and it measures what that costs. It builds on sprites.md: the
stage's sprite mesh draws the stream in place of the classic 80x80 frame.

Species with a stream (16): finneon, trapinch, luxio, monferno, noctowl, garchomp, buneary,
budew, wurmple, kricketot, bidoof, silcoon, cascoon, gastly, beautifly and dustox. Every other
species draws exactly as before.

## Data

`tools/gen5_sprites/gen5_stream.py SPECIES...` builds
`res/prebuilt/battle/graphic/mon_stream.narc` from the PokeAPI B/W animated GIFs. The GIFs
are cached in `~/.cache/gen5_sprites` and are not checked in. The tool's docstring has the
member format:

- member 0 is an index, `u16 [species][back, front]`;
- every other member is one stream: a header, the animation's box in the canvas, frame
  offsets, `{frame, duration}` steps on the 60 Hz clock, and LZ77 frames that cover the box
  only.

The tool also rewrites, from the same art, each species' `{male,female}_{front,back}.png`
(frame A and a mid-loop frame B, cut from the canvas's classic window), `normal.pal` and
`shiny.pal`. So everything that still draws the classic sprite matches the stream (summary
screen, Pokédex, fallbacks), and so does the battler's palette slot. The tool also sets
`y_offset` to 0, because the art already stands on the frame's last row.

**Canvas.** The canvas is 128x96: a whole texture row wide, with the classic 80x80 frame at
(24, 8). A Gen 5 frame is 96x96, centred, with the union of all frames standing on row 87.

**Back sprites.** Black/White draw back sprites at twice their size, so the Gen 5 back art is
half the size of Gen 4's. The tool scales the back frames up (nearest neighbour) by up to 2x,
in steps of 1/8. The scale is the largest that keeps the union no taller than the classic
frame (80) and no wider than the canvas (128). Examples: Finneon 1.75, Bidoof 1.75,
Cascoon 2.0, Garchomp and Gastly 1.0. `report.json` lists every species.

## Runtime

`src/battle/battle_stage_stream.c`:

- **VRAM.** One `NNS_GfdAllocTexVram` of 4 x 6 KB, one 128x96 4bpp texture per battler. It
  must end below 0x20000, like the arena textures.
- **Load.** When a battler's sprite template changes, the runtime reads the whole stream member
  onto `HEAP_ID_BATTLE`, plus a 6 KB copy of the texture. It refuses the load (the battler then
  draws classic) when that would leave less than 128 KB of the heap free.
- **Each frame (`BeginFrame`).** The runtime advances the steps by VBlank count. If the frame
  changed, it decompresses it (`MI_UncompressLZ8`) and copies the box rows into the texture
  copy. Then it queues those rows on the battle's `VramTransfer` list. Whole textures are sent
  after the arena was hidden, since other screens reuse the VRAM.
  - `FREEZE_IDLE` holds step 0, the classic frame A.
- **Draw (`Bind`).** The draw hook binds the battler's texture and draws the 128x96 canvas
  around the classic frame's centre. A partial draw (the send-out reveal) takes the same part of
  the classic window. Mosaic, `excludeIdentity` and the `NO_SPRITE_STREAM` debug flag (bit 6)
  fall back to the classic texture.
  - Frames queued this frame can be bound: the VBlank transfer lands before the hardware
    renders this frame's geometry.

## Measurements

These come from a wild battle in Eterna Forest, Finneon against a wild Buneary or Bidoof, read
from `sSpriteStreamStats` (1 tick = 1.91 µs).

| | |
|---|---|
| Upload, worst frame | 9.7 KB (two battlers changing frame at once, scaled back) |
| Upload, steady state | 159 of 240 frames upload, mean 4.3 KB |
| Decode and copy, worst frame | 1524 ticks = 2.9 ms (both battlers) |
| Stream load, worst | 28255 ticks = 54 ms, a hitch of about 3 frames when a mon appears |
| Heap held | 92 KB for two streams, 293 KB still free |
| VRAM | 24 KB at 0x14400 |

Texture VRAM can only be written while the 3D engine isn't reading it. That leaves about
1.4 ms after VBlank begins (the engine starts the next frame at line 214). At DMA speed that is
about 40 KB, so 10 KB in a frame fits with room left for the battle's own transfers.

## Known gaps (later steps)

- **Load hitch.** The member is read from the card in one go. Large streams (Gastly's back is
  70 KB) cost about 3 frames. A step 2 could load in slices, or preload at send-out.
- **Heap in doubles.** Four large streams would hit the 128 KB floor, and the battler that
  doesn't fit draws classic (`loadFailures`).
- **Female art.** It reuses the male art. The GIFs have no female set for these species.
- **Timing.** The GIF frame durations are used as-is, and haven't been checked against
  footage of the games.
- **Other screens.** OBJ paths and other screens (summary, Pokédex) still show the
  static frame A.
- **Back scale.** The back scale is per species and capped at the classic frame's height. B/W
  draw backs at a flat 2x and let big mons run off the screen.
