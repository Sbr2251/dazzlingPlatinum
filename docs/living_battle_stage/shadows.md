# Battler shadows (BW2 style)

`src/battle/battle_stage_shadow.c`, called from `BattleStageSprites_DrawBlobs`
(`battle_stage_sprites.c`). It replaces the blob shadow (sprites.md, "Blob shadows") for every
battler drawn from a Gen 5 stream. The blob stays for the rest.

## What BW2 does

pokebw2, read-only reference: `src/system/mcss.c` (`MCSSSys_Draw`, `MCSS_DrawQuad`) and
`src/ov168/btlv_mcss.c` (`BtlvMcss_AddPokemon`, `BtlvMcss_GetShadowOffset`, the table
`data_ov168_021f3414`).

- MCSS draws every cell quad of a sprite a second time. The second quad uses the shadow palette
  (btlv file 355: colour 0 transparent, 1 to 15 black) at half the sprite's alpha
  (`MCSS_SHADOW_ALPHA_HALF`: `alpha / 2`, so 15 of 31), polygon ID 1, no light.
- The shadow's matrix, in BW2's world (y up, the enemy at -z):
  `translate(foot + offset) * RotX(0xc400) * RotZ(rotZ) * the sprite's own quads`.
  - RotX(0xc400) tips the sprite back by 84.4 degrees. Its "up" points away from the camera,
    5.6 degrees off the ground, so the shadow falls behind the mon.
  - RotZ turns it first, in its own plane. The default is 0xf800 (-11.25 degrees: the top leans
    left).
  - The default offset is (-0.25, 0, -0.375) world units.
  - The scale is the battler's perspective scale (0x1030 back, 0x11bf front in singles). A quad
    is 1/16 unit per art pixel at scale 1.
- The per-species adjust table has 48 entries (24 species-face pairs, both sides of some). Each
  sets the offset, rotZ, or turns the shadow off. Off: the Diglett and Dugtrio fronts and both
  Hippowdon faces.
- The shadow is the animated sprite itself, so it moves with every part.

## What we draw

One quad per battler: the battler's current stream frame (the texture `BattleStageStream_Bind`
binds for the sprite this frame), with BW2's mapping, laid on the arena's ground.

- **Texture and colour.** The stream texture (4bpp, the battler's 128x128 slot from
  `sSpriteStreamStats.vramAddr`), with `GX_TEXGEN_NONE` because the arena may leave a texture
  matrix loaded. A 32-byte palette of our own (all black, colour 0 transparent) in texture
  palette VRAM. Polygon alpha `transforms->alpha / 2` (15 for an opaque mon), polygon ID 62. That
  is the blobs' ID: a translucent pixel never covers its own ID, so two shadows (or a shadow and a
  blob) that overlap in doubles don't darken twice. Unlit and unfogged.
- **Depth.** As the blobs: the flattened projection puts every pixel at NDC depth 4000. That is
  in front of the arena (4010 to 4094) and behind the sprites, so the mon covers its own shadow.
- **Placement.** The foot point is on the ground at the sprite's x (`xCenter + xOffset`). The
  classic per-species `shadow.xOffset` is not used: the silhouette lines up with the art itself.
  - For a front, the ground point is under the bottom of its home frame (`yCenter + 40`, where
    the stream's ground row `MON_STREAM_GROUND_V` is drawn).
  - For a back, it is the player side's blob row (142), as the blob. The feet are under the text
    box.
  - Texel (u, v) of the canvas box sits at (u - 64, 88 - v) screen pixels from the foot point,
    scaled by the stream's scale and the sprite's `scaleX` (a negative scaleX flips it) and
    `scaleY`.
- **Floaters** (item 3). The classic altitude `shadow.height` (enemy fronts) lifts the sprite,
  not the shadow. The shadow stays on the ground under the mon. Our streams stand every
  animation on the ground row and the altitude lifts them; BW2 bakes the hover into the art,
  above its foot point. So, as in BW2, the hover is added to the art's height before the shadow
  is laid down: a floater's shadow starts that many pixels behind its foot point, on the ground.
- **BW2's axes on our ground.** Our home camera looks straight down -z. BW2's camera sits 21.2
  degrees to the side (x 6.7, z 17.3 from its target). The shadow is laid along BW2's world axes
  as BW2's camera sees them:
  - BW2 +x is our camera-right turned 21.2 degrees.
  - BW2 -z is straight ahead (away from our camera) turned 21.2 degrees to the right.

  So on screen it falls back and to the right, as on BW2's screen: about 10 degrees right of
  straight back once rotZ is applied. Our camera's pitch at the battlers (15 degrees at the
  enemy, 26 at the player) is close to BW2's (13 and 28), so the shadow is foreshortened about
  as much.
- **Offsets.** The table's x and z, in world units, become screen pixels as BW2's art pixels per
  unit (16 / perspective scale: 14.4 front, 15.8 back) times our art's scale on screen (1 front,
  1.75 back). They are applied along BW2's x and back after the rotation, as in BW2.
- **It follows the animation every frame.** It samples the same texture slot the sprite draws,
  which the stream updates as it plays (including slower speeds at low HP or asleep, and frozen
  solid).

## Which battlers get what

`BattleStageSprites_DrawBlobs` builds the set a shadow shows for (the blob rule: active, not
`hide`/`hide2`, not `partialDraw`, not hidden by a move's `hideShadows`). Then:

| battler | shadow |
|---|---|
| table entry with the shadow off (Diglett and Dugtrio fronts, Hippowdon) | none, and no blob (BUG 1) |
| drawn from its stream last frame, stream bound now, `NO_SPRITE_STREAM` off, not `excludeIdentity` | silhouette |
| enemy with `SHADOW_SIZE_NONE` (the classic path's "no shadow") | none (BUG 1: it used to get a 40 px blob) |
| anything else: classic sprites (forms, Spinda, Mega fronts, the Substitute doll), a battler whose stream isn't in yet | blob |

- **Hidden states.** Fly's up-and-away and Dig's burrow end in `hide` or `partialDraw`, so the
  shadow goes (Dig's hole still draws). The faint slide and the send-out reveal are partial
  draws: no shadow, as before.
- **Substitute.** The doll is a classic sprite, so it gets the blob.
- **Mega.** The Mega front is classic, so it gets the blob. The Mega back is a one-frame stream,
  so it gets a silhouette with the default parameters, because the template (pl_otherpoke) names
  no species.
- **Transform.** The table is looked up from the species the template shows (pl_pokegra
  `character / 6`; front when `(character % 6) / 2 == FACE_FRONT / 2`), so a transformed mon takes
  its new look's entry.
- **Debug flags.** `NO_BLOB_SHADOWS` turns the silhouettes off too, and the classic shadow comes
  back. `stage_ab` relies on this. With `CLASSIC_SPRITES` the stage draws no shadows. The classic
  path (stage off, L+R+SELECT) is untouched: it draws Platinum's shadow from `shadow.size` and
  `shadow.xOffset`.
- `blobShadows` (sBattleStage+48) counts silhouettes and blobs together, so the critic's "2 in
  singles" still holds.

## The adjust table

`sShadowAdjust` in `battle_stage_shadow.c` is BW2's table entry for entry, keyed by our
`SPECIES_` constants. BW2's species numbers are the national dex, and ours keep the same names for
the same species. That includes the Gen 5 species this hack added, which have other numbers
here. 38 of BW2's 48 entries are for species in this game. Left out: Samurott, Zoroark,
Galvantula, Haxorus, Mienfoo, Bouffalant, Reshiram, Zekrom.
`python3 tools/battle_shadow/bw2_shadow_table.py` checks the table against pokebw2's.

BW2's table has no size column: the size comes from the silhouette (the art's size on screen).

## Classic shadow x offsets of the Gen 5 species

`gen5_species.py` copied each added species' `sprite_data.json` from a Sinnoh stand-in, so
`shadow.x_offset` belonged to the stand-in's art. It is used by the blob fallback and by the
classic path. `tools/battle_shadow/gen5_x_offsets.py` measures the B/W art (frame 0 of
`male_front.png`): the median of four estimates of the body's centre line. Over the 475 Platinum
species with a shadow, it is within 2.6 px of Platinum's own value at the median. Values were
changed where the measure and a look at the art agree that the stand-in's is off:

| species | stand-in value | measured | now |
|---|---|---|---|
| Patrat | 1 | -5.6 | -6 |
| Stoutland | 5 | 0.7 | 1 |
| Liepard | -9 | -4.3 | -4 |
| Tranquill | 0 | -6.0 | -5 |
| Unfezant | -1 | -9.2 (tail) | -6 |
| Drilbur | 5 | -2.2 | -2 |
| Leavanny | -12 | 1.1 | 1 |
| Krokorok | 0 | -7.5 (tail) | -3 |
| Krookodile | 8 | 7.1 (tail) | 2 |
| Cofagrigus | -6 | -1.5 | -2 |
| Deino | 0 | 4.2 | 4 |

`shadow.size` is left as it is: on the art, the width of the feet predicts Platinum's size class
poorly.

## Budget

- **Polygons.** One quad per battler, the same as the blob it replaces: the count is unchanged.
  Measured with RAM_COUNT (0x04000604) at the command menu, frozen idle:

  | scene | before (blobs) | after (silhouettes) |
  |---|---|---|
  | Plain or Water, singles (Garchomp, Gastly, Steelix, Onix, Liepard...) | 641 | 641 |
  | Cave 1, singles | 694 | 694 |
  | Diglett or Hippowdon front (shadow off, BUG 1) | 641 (Plain), 694 (Cave) | 640, 693 |
  | Totem battle, Plain | 667 | 667 |
  | doubles, Plain or Water, day (test ROM, 4 battlers) | 771 | 771 |
  | doubles, Cave 1, night (test ROM) | 824 | 824 |
  | the classic shadow path (`NO_BLOB_SHADOWS`), Plain singles | 639 | 639 |

  The hardware limit is 2,048 per frame.
- **Vertices.** 4 per battler, the same as the blob.
- **VRAM.** No texture: the stream frame is already there. One 32-byte palette in texture
  palette VRAM.
- **CPU.** A table lookup and four vertices per battler, per frame.

## Debug fields

`sStageShadowStats` (`BattleStageShadowStats`, battle_stage_shadow.h), read through the xMAP:

- `silhouetteMask`, `offMask`: the battlers drawn with a silhouette, and those whose shadow is
  off, in the last frame that drew shadows.
- `silhouettes`: their count.
- `drawnFrames`: frames with at least one silhouette, this battle.
- `plttAddr`: the palette's address, 0 without one.

## Sources

No asset is copied from pokebw2. The palette is built at run time: black, which is what btlv
file 355 holds. The geometry and the table values come from pokebw2's C (`mcss.c`,
`btlv_mcss.c`, `btlv_camera.c`).
