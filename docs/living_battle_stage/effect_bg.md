# 3D battle stage: Black 2/White 2 effect backgrounds (bw2vis effect-bg)

55 moves swap BG3 to a full-screen picture with `SwitchBg` (move_audit.md, mechanism `switch_bg`; the 55 whose
`suppress` has `bg_switch`). They used Platinum's pictures from `pl_batt_bg.narc`, and the 3D arena faded out
for them (compat.md, F6). They now show Black 2/White 2's effect backgrounds, imported from pokebw2's extracted
graphics, and most of them cut from the arena to the picture the way Gen 5 does.

**Asset source.** `/data/repos/pokebw2/res/graphics/btlv_effvm_bg` (BW2 archive `a/0/9/4`,
`ARCID_BTLV_EFFVM_BG`) and `btlv_effvm_pal_anim` (`a/2/3/1`, `ARCID_BTLV_EFFVM_PAL_ANIM`), read-only. BW2
battle assets are allowed for battle visuals (/tmp/bw2vis/COMMON.md, "Asset policy"). Nothing from any other
game. BW2's move scripts (`a/0/6/5`, which pick each move's background) are not extracted, so the
move-to-background mapping below is a judgement, not BW2's own.

## What BW2 has

`btlv_effvm_bg` holds 77 backgrounds (NSCR, tile PNG, palette triples, file ids 0, 3, ... 228) and, after them,
17 Poke Ball OBJ sheets (ids 233-265, with the NCER/NANR at 231/232), which are not backgrounds. So "94" counts
the PNGs; 77 are effect backgrounds. `BtlvEffvm_CmdLoadBg` (`btlv_effvm.c:1874`) loads one onto BG3 at
priority 1 with its palette at BG row 8; `BtlvEffvm_CmdBgPalAnim` (`:1916`, task `:4410`) cycles one of the 23
palette anims over row 8.

Most of the first ~60 are redraws of Platinum's pictures (Platinum's red burst 0-4 is BW2 003, its streams 9-13
are BW2 018-027, its moon 54 is BW2 108, its grid room 57 is BW2 165 and so on). BW2 added new ones (the 'pow'
star, the psychic marble, the fire vortex, the warped space grids, V-create's jets).

Contact sheets (rendered from the extracted files with `tools/effect_bg/bw2_effect_bg.py sheet`):
`/tmp/bw2vis/effect-bg/catalogue/bw2_effect_bgs.png` (all 77 at scroll 0,0 with BW2's 8 px margin),
`bw2_pal_anims.png` (every anim's rows on its background), `bw2_ball_sheets.png`, `mapping.png` (each move's
Platinum picture next to its BW2 one as our screen shows it).

| BW2 id | kind | what it shows | size | imported as |
|---|---|---|---|---|
| 000 | flash | plain white screen (a flash / white-out; anims 10 and 22 tint it red) | screen | - |
| 003 | impact | red radial burst, orange spikes around a red core | screen | `BATTLE_BG_BW2_RED_BURST` |
| 006 | impact | magenta radial burst, pink spikes around a hot pink core | screen | `BATTLE_BG_BW2_MAGENTA_BURST` |
| 009 | impact | orange-yellow starburst with a white-hot centre | screen | `BATTLE_BG_BW2_ORANGE_BURST` |
| 012 | impact | yellow-white spiky 'pow' star on purple (anim 0 cycles the star) | screen | `BATTLE_BG_BW2_STAR_IMPACT` |
| 015 | fighting | red-orange kaleidoscope burst (anims 1 and 2 cycle it) | screen | `BATTLE_BG_BW2_KALEIDOSCOPE` |
| 018 | water | blue horizontal stream with white bubble highlights | wide | `BATTLE_BG_BW2_BLUE_STREAM` |
| 021 | poison/psychic | purple horizontal stream with lilac highlights | wide | `BATTLE_BG_BW2_PURPLE_STREAM` |
| 024 | fire/fighting | red horizontal stream with pink highlights | wide | `BATTLE_BG_BW2_RED_STREAM` |
| 027 | electric | yellow horizontal stream with pale highlights | wide | `BATTLE_BG_BW2_YELLOW_STREAM` |
| 030 | ice | grey snowstorm: white flakes and drifts over streaking grey | wide | `BATTLE_BG_BW2_SNOWSTORM` |
| 033 | normal/grass | yellow-green field with dark green ripples top and bottom | wide | `BATTLE_BG_BW2_GREEN_RIPPLE` |
| 036 | space | dark blue night column with falling gold sparks | tall | `BATTLE_BG_BW2_FALLING_SPARKS` |
| 039 | weather | black sky under dark storm clouds | wide | `BATTLE_BG_BW2_STORM_CLOUDS` |
| 042 | ground | brown packed-earth texture | screen | `BATTLE_BG_BW2_EARTH` |
| 045 | psychic | pink zigzag psychic waves | tall | `BATTLE_BG_BW2_PSYCHIC_WAVES` |
| 048 | psychic | magenta/violet wavy psychic pattern | screen | - |
| 051 | ice/speed | cyan horizontal speed lines | wide | `BATTLE_BG_BW2_CYAN_SPEED` |
| 054 | fire | white sun blast with red and yellow rays | screen | `BATTLE_BG_BW2_SUN_BLAST` |
| 057 | normal | white-pink glow with red rays (a blinding burst) | screen | `BATTLE_BG_BW2_WHITE_BLAST` |
| 060 | fire | orange-red rays around a yellow star (anim 3 pulses it red) | screen | - |
| 063 | water/ice | blue and lavender zigzag waves (rapids) | tall | `BATTLE_BG_BW2_RAPIDS` |
| 066 | sky | light blue sky with white cloud bands | tall | - |
| 069 | ghost/dark | dark purple field with black swirls | tall | `BATTLE_BG_BW2_NIGHTMARE_SWIRLS` |
| 072 | psychic | magenta liquid-marble swirls | screen | `BATTLE_BG_BW2_PSYCHIC_MARBLE` |
| 075 | water | smooth cyan whirlpool swirl | screen | `BATTLE_BG_BW2_WHIRLPOOL` |
| 078 | water/wind | teal cel-shaded vortex (anim 4 spins it) | screen | `BATTLE_BG_BW2_WIND_VORTEX` |
| 081 | water | blue radial lines around a blue disc (anim 5 pulses it) | screen | - |
| 084 | aura | blue glowing ellipse with dark edges | screen | `BATTLE_BG_BW2_BLUE_AURA` |
| 087 | dark/electric | black ellipse ringed by a yellow glow | screen | `BATTLE_BG_BW2_DARK_HALO` |
| 090 | dragon | magenta flames over pale grey | wide | `BATTLE_BG_BW2_MAGENTA_FLAMES` |
| 093 | fire | wall of red and yellow flames (anim 6 flickers it) | wide | - |
| 096 | fire/ghost | blue-violet flames over teal | wide | `BATTLE_BG_BW2_TEAL_FLAMES` |
| 099 | water/wind | blue and white swirling clouds (mist, storm) | wide | `BATTLE_BG_BW2_MIST_CLOUDS` |
| 102 | fire | orange explosion with white core and sparks | screen | `BATTLE_BG_BW2_FIRE_EXPLOSION` |
| 105 | fire/psychic | red concentric rings on red (anim 7 ripples them) | screen | - |
| 108 | moon | full moon on a dark grey night | tall | `BATTLE_BG_BW2_FULL_MOON` |
| 111 | speed | cyan, grey and blue horizontal speed lines | wide | `BATTLE_BG_BW2_GREY_SPEED` |
| 114 | water | deep blue water with rising bubbles | tall | - |
| 117 | light/ice | cyan sky with a white light burst | screen | `BATTLE_BG_BW2_LIGHT_BURST` |
| 120 | impact | the 'pow' star of 12 with another palette | screen | - |
| 123 | fire | red-yellow molten lava marble (anim 9 churns it) | screen | - |
| 126 | space | deep space: stars, nebula and galaxies | tall | `BATTLE_BG_BW2_SPACE` |
| 129 | sky/light | white vertical light pillar on blue | tall | `BATTLE_BG_BW2_LIGHT_PILLAR` |
| 132 | sky/ice | white upward chevrons on cyan (an updraft) | tall | `BATTLE_BG_BW2_UPDRAFT` |
| 135 | misc | red, white and green diagonal stripes | screen | - |
| 138 | grass | pale green column with falling leaves | tall | `BATTLE_BG_BW2_FALLING_LEAVES` |
| 141 | electric | yellow lightning cracks on black (anim 11 flashes them) | screen | - |
| 144 | water | deep blue sea over a rocky seabed silhouette | wide | `BATTLE_BG_BW2_SEABED` |
| 147 | water | underwater: light rays over rolling waves | wide | `BATTLE_BG_BW2_UNDERWATER` |
| 150 | energy | purple radial spikes around a red core (anim 12 cycles it) | screen | - |
| 153 | water/speed | blue and teal horizontal speed lines | wide | `BATTLE_BG_BW2_WATER_SPEED` |
| 156 | fire | fire vortex around a dark eye (anim 13 spins it) | screen | `BATTLE_BG_BW2_FIRE_VORTEX` |
| 159 | water/sky | light blue surface with horizontal ripples | wide | `BATTLE_BG_BW2_SKY_RIPPLES` |
| 162 | energy | navy screen hiding a radial burst that only anim 14 reveals | screen | - |
| 165 | psychic | perspective grid room (Trick Room) | screen | `BATTLE_BG_BW2_GRID_ROOM` |
| 168 | grass | green field with leaves blowing sideways | wide | `BATTLE_BG_BW2_LEAF_WIND` |
| 171 | grass | green starburst with a cyan core | screen | `BATTLE_BG_BW2_GREEN_BURST` |
| 174 | dark | black hole inside dark radial lines (anim 15 pulses it red) | screen | - |
| 177 | fire | red and yellow horizontal fire streaks | wide | `BATTLE_BG_BW2_FIRE_SPEED` |
| 180 | impact | orange starburst with a white core on teal | screen | `BATTLE_BG_BW2_ORANGE_FLARE` |
| 183 | fairy/psychic | pink radial mandala (anim 16 cycles it) | screen | `BATTLE_BG_BW2_PINK_MANDALA` |
| 186 | moon | crescent moon on a dark night | tall | `BATTLE_BG_BW2_CRESCENT_MOON` |
| 189 | fire | yellow heat with orange spots (anim 8 shimmers it) | tall | `BATTLE_BG_BW2_MAGMA_DOTS` |
| 192 | rock/ghost | grey jagged wave bands | tall | `BATTLE_BG_BW2_GREY_BANDS` |
| 195 | space | blue warped space grid | screen | - |
| 198 | space | beige warped space grid | screen | - |
| 201 | fire | vertical fire column split by lightning | tall | - |
| 204 | psychic | purple and red concentric hypnosis rings (anim 17 moves them) | screen | `BATTLE_BG_BW2_HYPNO_RINGS` |
| 207 | light | pale yellow beams radiating on black (anim 18 cycles them) | screen | - |
| 210 | fire | orange-white explosion cloud | screen | - |
| 213 | electric | white electric sphere with tendrils on black | screen | - |
| 216 | fire/water | blue fluid flames | wide | - |
| 219 | electric | single cyan lightning line across black (anim 19 flickers it) | wide | - |
| 222 | ice | cyan ice crystals (anim 20 glints them) | screen | - |
| 225 | fire | V-shaped fire jets on brown (V-create; anim 21 cycles it) | screen | - |
| 228 | ui | a black bar with 'AUTO CENTER' text: a UI overlay, not an effect | screen | - |

`size`: "screen" is one 256x192 picture plus an 8 px margin; "wide" is 512 px wide, for a sideways scroll;
"tall" repeats every 256 px vertically, for a vertical scroll.

The palette anims, matched to their backgrounds by comparing each anim's rows with the backgrounds' first row and
checked on renders:

| anim | background | what it does | rows | frame counts |
|---|---|---|---|---|
| 00 | 012 | cycles the star 4 rows and back, 3 frames each | 8,9,10,11,10,9 | 3,3,3,3,3,3 |
| 01 | 015 | cycles the kaleidoscope 4 rows and back, 3 frames each | 11,10,9,8,9,10 | 3,3,3,3,3,3 |
| 02 | 015 | steps the kaleidoscope through 6 rows, 4 frames each | 8,9,10,11,12,13 | 4,4,4,4,4,4 |
| 03 | 060 | pulses the rays dark red to bright red, 6 frames each | 8,9,10,11,12,13 | 6,6,6,6,6,6 |
| 04 | 078 | spins the vortex, 6 rows, 3 frames each | 8,9,10,11,12,13 | 3,3,3,3,3,3 |
| 05 | 081 | pulses the radial lines, 4 rows and back, 6 frames each | 8,9,10,11,10,9 | 6,6,6,6,6,6 |
| 06 | 093 | flickers the flames, 6 rows, 3 frames each | 8,9,10,11,12,13 | 3,3,3,3,3,3 |
| 07 | 105 | ripples the rings outward, fast (1-2 frames) | 14,13,12,10,9,8 | 1,1,1,1,1,2 |
| 08 | 189 | shimmers the heat spots, 4 rows, 5 frames each | 8,9,10,11 | 5,5,5,5 |
| 09 | 123 | churns the lava 7 rows and back, 8-10 frames each | 8,9,10,11,12,13,14,13,12,11,10,9,8 | 10,8,8,8,8,8,8,8,8,8,8,8,8 |
| 10 | 000 | one-shot red flash with a black blink | 8,9,10,11,12,8 | 4,10,10,4,20,4 |
| 11 | 141 | flashes the lightning, 4 rows, 3 frames each | 8,9,10,11 | 3,3,3,3 |
| 12 | 150 | cycles the radial spikes, 7 rows, 4 frames each | 8,9,10,11,12,13,14 | 4,4,4,4,4,4,4 |
| 13 | 156 | spins the fire vortex up and down, 1-4 frames | 8,9,10,11,12,13,14,13,12,11,10,9,8 | 4,4,4,3,2,1,1,1,2,3,4,4,0 |
| 14 | 162 | holds navy 90 frames, then reveals a white, gold, orange and violet burst | 13,8,9,10,11,12,13 | 90,4,4,5,6,7,4 |
| 15 | 174 | pulses the black hole red and back | 8,9,10,11,10,9,10,11,10,9,8 | 2,2,2,20,4,4,4,4,4,4,4 |
| 16 | 183 | cycles the mandala, 6 rows, 5 frames each | 13,12,11,10,9,8 | 5,5,5,5,5,5 |
| 17 | 204 | moves the rings, 5 rows, 2 frames each | 12,11,10,9,8 | 2,2,2,2,2 |
| 18 | 207 | cycles the beams, 6 rows, 6 frames each | 8,9,10,11,13,14 | 6,6,6,6,6,6 |
| 19 | 219 | flickers the lightning line | 8,9,10,11,10,9 | 6,3,3,4,3,3 |
| 20 | 222 | glints the crystals, 20-frame hold then 6 rows | 8,9,10,11,12,13,8 | 20,6,6,6,6,1,6 |
| 21 | 225 | cycles the V jets, 6 rows, 3 frames each | 13,12,11,10,9,8 | 3,3,3,3,3,3 |
| 22 | 000 | fades the white screen to red, 60 frames a step | 8,9,10,11 | 60,60,60,60 |

## The mapping

Rule: a move gets BW2's redraw of the Platinum picture it showed, since BW2 kept those pictures and most of
those moves. Where Platinum's picture is a generic one several unrelated moves share (the red burst 0-4, the
blue burst 31-33, the blue stream 9/10, the black screen 20), or two moves share one picture and BW2 has a
closer one for one of them, the move gets the BW2 picture that reads as its type. A move that scrolls the
picture (`BATTLE_BG_SWITCH_FLAG_MOVE`) gets one that repeats in that direction: "wide" for a sideways scroll,
"tall" for a vertical one.

| move | Platinum bgID | BW2 background | transition | why |
|---|---|---|---|---|
| 019 fly | 55 | 129 `LIGHT_PILLAR` | cut | BW2's redraw of Platinum's light pillar; tall, so the 32 px/frame vertical rush stays seamless |
| 025 mega_kick | 0 | 012 `STAR_IMPACT` (anim 00) | cut | Platinum's 0-4 are one generic red burst; a Normal kick gets BW2's 'pow' star, animated |
| 038 double_edge | 6 | 009 `ORANGE_BURST` | cut | BW2's redraw of Platinum's orange-white burst |
| 056 hydro_pump | 9 | 018 `BLUE_STREAM` | cut | BW2's redraw of the blue stream; 512 wide for the sideways scroll |
| 059 blizzard | 50 | 030 `SNOWSTORM` | cut | BW2's redraw of the grey snowfield: a blowing snowstorm, 512 wide |
| 063 hyper_beam | 14 | 033 `GREEN_RIPPLE` | cut | BW2's redraw of Platinum's yellow-green ripple field, 512 wide |
| 069 seismic_toss | 51 | 036 `FALLING_SPARKS` | cut | BW2's redraw of the night column with gold sparks; tall, for the vertical toss |
| 087 thunder | 19 | 039 `STORM_CLOUDS` | cut | BW2's redraw of the storm-cloud sky |
| 090 fissure | 53 | 042 `EARTH` | cut | BW2's redraw of the brown earth |
| 093 confusion | 20 | 204 `HYPNO_RINGS` (anim 17) | cut | Platinum's 20 is a black screen; BW2's hypnosis rings, animated, read as confusion |
| 094 psychic | 52 | 045 `PSYCHIC_WAVES` | cut | BW2's redraw of the pink psychic waves; tall, for the vertical scroll |
| 097 agility | 47 | 051 `CYAN_SPEED` | cut | BW2's cyan speed lines, the redraw of Platinum's |
| 120 selfdestruct | 21 | 057 `WHITE_BLAST` | cut | BW2's redraw of the white-pink blast with red rays |
| 126 fire_blast | 22 | 054 `SUN_BLAST` | cut | BW2's redraw of the star-shaped fire blast |
| 127 waterfall | 23 | 063 `RAPIDS` | cut | BW2's redraw of the blue zigzag rapids; tall, for the climb |
| 143 sky_attack | 18 | 159 `SKY_RIPPLES` | cut | BW2's redraw of Platinum's light blue streaked sky, 512 wide |
| 171 nightmare | 24 | 069 `NIGHTMARE_SWIRLS` | fade | BW2's redraw of the dark swirls; the fade to black is the nightmare falling, kept |
| 177 aeroblast | 25 | 078 `WIND_VORTEX` (anim 04) | cut | BW2's teal vortex, the redraw of Platinum's, spun by palette anim 4 |
| 192 zap_cannon | 26 | 084 `BLUE_AURA` | cut | BW2's redraw of the blue glowing ellipse |
| 200 outrage | 28 | 090 `MAGENTA_FLAMES` | cut | BW2's redraw of the magenta flames, 512 wide |
| 221 sacred_fire | 29 | 096 `TEAL_FLAMES` | cut | BW2's redraw of the blue-violet flames, 512 wide |
| 223 dynamic_punch | 1 | 015 `KALEIDOSCOPE` (anim 01) | cut | generic red burst in Platinum; BW2's fighting kaleidoscope burst, animated |
| 224 megahorn | 2 | 003 `RED_BURST` | cut | BW2's redraw of the red burst |
| 236 moonlight | 54 | 108 `FULL_MOON` | fade | BW2's redraw of the full moon; the fade is night falling, kept |
| 245 extreme_speed | 47 | 111 `GREY_SPEED` | cut | shares Platinum's speed lines with Agility; BW2's grey Normal speed lines tell them apart |
| 250 whirlpool | 35 | 075 `WHIRLPOOL` | cut | Platinum's night sea is shared with Water Pulse; BW2's whirlpool swirl under the line wave |
| 264 focus_punch | 31 | 117 `LIGHT_BURST` | cut | BW2's redraw of Platinum's blue light burst (31-33) |
| 273 wish | 56 | 126 `SPACE` | fade | BW2's redraw of deep space; the slow fade into the night sky is the wish, kept |
| 276 superpower | 3 | 003 `RED_BURST` | cut | BW2's redraw of the red burst |
| 296 mist_ball | 10 | 099 `MIST_CLOUDS` | cut | Platinum's 10 is the Hydro Pump stream again; BW2's swirling mist clouds, 512 wide |
| 308 hydro_cannon | 17 | 147 `UNDERWATER` | cut | Platinum's 17 recolours Hyper Beam's ripples; BW2's underwater view, 512 wide |
| 315 overheat | 32 | 102 `FIRE_EXPLOSION` | cut | generic blue burst in Platinum; BW2's fire explosion |
| 322 cosmic_power | 56 | 126 `SPACE` | fade | BW2's redraw of deep space; the fade into space is kept |
| 327 sky_uppercut | 55 | 132 `UPDRAFT` | cut | shares Fly's pillar in Platinum; BW2's upward chevrons for the rising blow, tall |
| 338 frenzy_plant | 34 | 138 `FALLING_LEAVES` | cut | BW2's redraw of the leaf column; tall, for the vertical scroll |
| 344 volt_tackle | 27 | 087 `DARK_HALO` | cut | BW2's redraw of the black ellipse in a yellow glow |
| 352 water_pulse | 35 | 144 `SEABED` | cut | BW2's redraw of Platinum's night sea over hills, under the line wave |
| 354 psycho_boost | 4 | 072 `PSYCHIC_MARBLE` | cut | generic red burst in Platinum; BW2's psychic marble |
| 370 close_combat | 36 | 153 `WATER_SPEED` | cut | BW2's redraw of the blue speed lines, 512 wide |
| 394 flare_blitz | 33 | 156 `FIRE_VORTEX` (anim 13) | cut | generic blue burst in Platinum; BW2's fire vortex, spun by palette anim 13 |
| 396 aura_sphere | 11 | 027 `YELLOW_STREAM` | cut | BW2's redraw of the yellow stream, 512 wide |
| 411 focus_blast | 12 | 024 `RED_STREAM` | cut | BW2's redraw of the red stream, 512 wide |
| 413 brave_bird | 18 | 159 `SKY_RIPPLES` | cut | BW2's redraw of the streaked sky (shared with Sky Attack in Platinum) |
| 416 giga_impact | 5 | 006 `MAGENTA_BURST` | cut | BW2's redraw of the magenta burst |
| 433 trick_room | 57 | 165 `GRID_ROOM` | blend | BW2's redraw of the grid room; the half blend over the backdrop is the effect, kept |
| 437 leaf_storm | 38 | 168 `LEAF_WIND` | cut | BW2's redraw of the leaves blowing sideways, 512 wide |
| 438 power_whip | 7 | 171 `GREEN_BURST` | cut | BW2's redraw of the green burst |
| 439 rock_wrecker | 39 | 177 `FIRE_SPEED` | cut | BW2's redraw of the orange-red streaks, 512 wide |
| 441 gunk_shot | 13 | 021 `PURPLE_STREAM` | cut | BW2's redraw of the purple stream, 512 wide |
| 457 head_smash | 40 | 180 `ORANGE_FLARE` | cut | BW2's redraw of the orange flare on blue |
| 460 spacial_rend | 41 | 183 `PINK_MANDALA` (anim 16) | cut | BW2's redraw of the pink radial rays, cycled by palette anim 16 |
| 461 lunar_dance | 42 | 186 `CRESCENT_MOON` | fade | BW2's redraw of the crescent moon; the fade into night is kept |
| 463 magma_storm | 43 | 189 `MAGMA_DOTS` (anim 08) | cut | BW2's redraw of the yellow heat with orange spots, shimmered by palette anim 8; tall |
| 464 dark_void | 44 | 192 `GREY_BANDS` | fade | BW2's redraw of the grey bands; the fade to black is the void, kept |
| 468 moonblast | 42 | 186 `CRESCENT_MOON` | fade | the crescent moon Platinum's 42 shows, redrawn; the fade into night is kept |

The trap-damage common anims `damage_magma_storm.s`, `damage_nightmare.s` and `damage_whirlpool.s` show the
same background as their moves, with the fade (they play every turn while the trap holds).

In a contest, a BW2 bgID shows the Platinum picture the entry names (`contestBg`), because the contest BG layout
differs; contests never touch the stage.

## How a BW2 background is built and loaded

`tools/effect_bg/bw2_effect_bg.py build` converts each entry and writes `res/graphics/battle/effect_bg/`
(tile PNG, JASC palette, screen and mirrored screen per entry, the anims' `.bin` and palettes, the order file,
`meson.build`), `include/constants/battle/battle_effect_bg.h` (the `BATTLE_BG_BW2_*` bgIDs, from 64, and
`BATTLE_BG_PAL_ANIM_*`) and `include/battle_anim/bw2_effect_bg_table.h`. Meson builds the NCGRs (LZ) and NCLRs
with nitrogfx, LZ-compresses the screens and packs `bw2_effect_bg.narc` (`/battle/graphic/bw2_effect_bg.narc`),
like `res/graphics/battle/moves`. The tool is deterministic; rerun it after changing `ENTRIES`.

- **Screen.** BW2's is 512x512 with the picture in the top-left 256x192 and an 8 px margin all round. Our BG3
  screen is 512x256 (`ov16_0223B140.c`, 0x1000 bytes at screen base 0x3000; a 512x512 screen would run into
  BG1's tiles at 0x4000). Map rows 0-27 are kept and rows 60-63 (y -32..-1) become rows 28-31, so the margin
  stays above the picture and a 256-period tall pattern stays seamless.
  A one-screen picture leaves x 264-503 empty, which Nightmare's and Whirlpool's per-line wave pulled into view
  as black wedges; the converter repeats the picture there (BW2's own 8 px margins stay).
- **Mirrored screen.** For an enemy attacker (`BATTLE_ANIM_VAR_BG_SCREEN_MODE`, Platinum's NSCR2), mirrored about
  the visible centre x = 128.
- **Palette.** BW2 row 8 goes to our row 9 (`BATTLE_BG_PALETTE_EFFECT`, where the anims write), rows 9-13 to our
  rows 12, 13, 14, 15, 8. Rows 12-15 are unused during a move (the intro fills them, nothing reads them later);
  row 8 is the BG2 mon copy's (`BATTLE_BG_PALETTE_MON_SPRITE`), which none of these moves uses. Colour 0 is
  transparent; the backdrop colour (BG colour 0) is set black while a BW2 background shows, as BW2's is. Every
  restore reloads the whole BG palette.
- **Tiles.** 4bpp at BG3's char base. In FADE and CUT mode that is 0x10000, where the backdrop's tiles were;
  every restore reloads them from the battle's copy (Platinum's Aeroblast picture, 67 KB, already overwrote
  them). In BLEND mode (Trick Room) the tiles go at 0xc000 under the backdrop BG2 still shows, so that entry is
  capped at 512 tiles (16 KB); the converter merged its 53 closest tiles.
- `BattleBgSwitch_SetBg` sends a bgID from `BATTLE_BG_BW2_FIRST` to `BattleEffectBg_Load`
  (`src/battle_anim/battle_anim_effect_bg.c`); 0-57 load from `pl_batt_bg.narc` as before. The FADE switch and
  restore fade all of a BW2 background's rows (`BattleBgSwitch_EffectPalettes`), and `Func_FadeBg
  FADE_BG_TYPE_EFFECT` does too (`BattleEffectBg_CurrentPaletteMask`).

### VRAM and heap budget

| | Platinum picture | BW2 background |
|---|---|---|
| BG3 tiles | 16 KB (512 tiles; Aeroblast 66 KB) | 3.8-29.2 KB, at most 1024 tiles (32 KB); Trick Room 16 KB at 0xc000 |
| BG3 screen | 4 KB (512x256) | 4 KB, the same buffer |
| BG palette | row 9 | up to 6 rows: 9, 12-15, 8 |
| heap while loading | NCGR + screen files | up to 30 KB of tiles + 4 KB screen, freed the next frame (a cut) or at once |
| palette anim | - | 1 task, a 664-byte work buffer (`PalAnim`) |
| ROM | - | `bw2_effect_bg.narc`, 736 KB |

No texture, OBJ VRAM or polygon cost: the arena is hidden while the picture shows.

| entry | BW2 id | tiles | BG VRAM | palette rows | anim |
|---|---|---|---|---|---|
| RED_BURST | 003 | 696 | 21.8 KB | 9, 12, 13, 14, 15, 8 | - |
| MAGENTA_BURST | 006 | 696 | 21.8 KB | 9, 12, 13, 14, 15, 8 | - |
| ORANGE_BURST | 009 | 263 | 8.2 KB | 9, 12, 14, 15, 8 | - |
| STAR_IMPACT | 012 | 301 | 9.4 KB | 9 | 00 |
| KALEIDOSCOPE | 015 | 793 | 24.8 KB | 9 | 01 |
| BLUE_STREAM | 018 | 526 | 16.4 KB | 9, 12, 13, 14, 15, 8 | - |
| PURPLE_STREAM | 021 | 526 | 16.4 KB | 9, 12, 13, 14, 15, 8 | - |
| RED_STREAM | 024 | 526 | 16.4 KB | 9, 12, 13, 14, 15, 8 | - |
| YELLOW_STREAM | 027 | 526 | 16.4 KB | 9, 12, 13, 14, 15, 8 | - |
| SNOWSTORM | 030 | 874 | 27.3 KB | 9, 12, 13, 15, 8 | - |
| GREEN_RIPPLE | 033 | 919 | 28.7 KB | 9, 12, 13, 14, 15, 8 | - |
| FALLING_SPARKS | 036 | 160 | 5.0 KB | 9, 12, 13, 14, 15, 8 | - |
| STORM_CLOUDS | 039 | 481 | 15.0 KB | 9, 12, 13, 14, 8 | - |
| EARTH | 042 | 487 | 15.2 KB | 9, 12, 13, 15 | - |
| PSYCHIC_WAVES | 045 | 572 | 17.9 KB | 9, 12, 13, 14, 15 | - |
| CYAN_SPEED | 051 | 293 | 9.2 KB | 9, 12, 13, 14, 15, 8 | - |
| SUN_BLAST | 054 | 458 | 14.3 KB | 9 | - |
| WHITE_BLAST | 057 | 171 | 5.3 KB | 9, 12, 13, 14, 15, 8 | - |
| RAPIDS | 063 | 544 | 17.0 KB | 9, 12, 13, 14, 15, 8 | - |
| NIGHTMARE_SWIRLS | 069 | 640 | 20.0 KB | 9 | - |
| PSYCHIC_MARBLE | 072 | 934 | 29.2 KB | 9, 12, 13, 14, 15, 8 | - |
| WHIRLPOOL | 075 | 779 | 24.3 KB | 9, 12, 13, 14, 15, 8 | - |
| WIND_VORTEX | 078 | 505 | 15.8 KB | 9 | 04 |
| BLUE_AURA | 084 | 185 | 5.8 KB | 9, 12, 13, 15 | - |
| DARK_HALO | 087 | 319 | 10.0 KB | 9, 12, 13, 14, 15, 8 | - |
| MAGENTA_FLAMES | 090 | 565 | 17.7 KB | 9, 12, 13, 14, 15, 8 | - |
| TEAL_FLAMES | 096 | 595 | 18.6 KB | 9, 12, 13, 14, 15, 8 | - |
| MIST_CLOUDS | 099 | 698 | 21.8 KB | 9, 12, 13, 14, 15, 8 | - |
| FIRE_EXPLOSION | 102 | 842 | 26.3 KB | 9, 12, 13, 14, 15, 8 | - |
| FULL_MOON | 108 | 158 | 4.9 KB | 12, 14, 15 | - |
| GREY_SPEED | 111 | 301 | 9.4 KB | 9, 12, 13, 14, 15, 8 | - |
| LIGHT_BURST | 117 | 765 | 23.9 KB | 9, 12, 13, 14, 15, 8 | - |
| SPACE | 126 | 735 | 23.0 KB | 9, 12, 13, 14, 15, 8 | - |
| LIGHT_PILLAR | 129 | 421 | 13.2 KB | 9, 12, 13, 14 | - |
| UPDRAFT | 132 | 626 | 19.6 KB | 9, 12, 13, 14, 15 | - |
| FALLING_LEAVES | 138 | 503 | 15.7 KB | 9, 12, 13, 14, 15, 8 | - |
| SEABED | 144 | 353 | 11.0 KB | 9, 14 | - |
| UNDERWATER | 147 | 723 | 22.6 KB | 9, 12, 13, 14, 15, 8 | - |
| WATER_SPEED | 153 | 286 | 8.9 KB | 9, 12, 13, 14, 15, 8 | - |
| FIRE_VORTEX | 156 | 814 | 25.4 KB | 9 | 13 |
| SKY_RIPPLES | 159 | 922 | 28.8 KB | 9, 12, 13, 14, 15, 8 | - |
| GRID_ROOM | 165 | 512 (53 merged, BLEND) | 16.0 KB | 9, 12, 13, 14, 15, 8 | - |
| LEAF_WIND | 168 | 558 | 17.4 KB | 9, 12, 13, 14, 15, 8 | - |
| GREEN_BURST | 171 | 263 | 8.2 KB | 9, 12, 14, 15, 8 | - |
| FIRE_SPEED | 177 | 432 | 13.5 KB | 9, 12, 13, 14, 15, 8 | - |
| ORANGE_FLARE | 180 | 689 | 21.5 KB | 9, 12, 13, 14, 15, 8 | - |
| PINK_MANDALA | 183 | 832 | 26.0 KB | 9 | 16 |
| CRESCENT_MOON | 186 | 121 | 3.8 KB | 12, 13, 14, 15 | - |
| MAGMA_DOTS | 189 | 566 | 17.7 KB | 9, 12, 13, 14, 8 | 08 |
| GREY_BANDS | 192 | 900 | 28.1 KB | 9, 12, 13, 14 | - |
| HYPNO_RINGS | 204 | 763 | 23.8 KB | 9 | 17 |

## Palette-cycle playback

New in our move system. `BattleEffectBg_StartPalAnim` reads a BW2 anim (rows ended by 0xff, then at 0x80 the
frame counts ended by 0xff98) and its palette, and a SysTask writes the rows over BG row 9 exactly as
`BtlvEffvm_PalAnimTask` does: the first row at once, each next one after its count (as BW2 counts: a row holds
until the timer reaches count - 2). It writes the unfaded buffer, and the faded one too when no palette fade is
running, so a FADE switch still fades the cycling picture in. One step per battle frame (30 Hz); BW2's own rate
is not known without its main loop, so anims may run at half or full BW2 speed.

- **The BG-load hook.** An entry with an anim (`ENTRIES`, 7 of them) starts it, looping, when it loads.
- **The command.** `BgPalAnim anim, loops` (command 96 in `btlanimcmd.inc`; 92-95 are left free for the camera
  streams) replaces the running anim; `loops` 0 runs until the background goes, and `BATTLE_BG_PAL_ANIM_STOP`
  stops it. Only the anims of imported backgrounds are in the NARC.
- `RestoreBg` stops the anim, and so does the anim system's Delete at the script end, with everything else this
  module keeps (`BattleEffectBg_Reset`). The battle_anim overlay swaps with trainer_ai every turn, so nothing of
  it may outlive the script.

## Cut instead of fade

Gen 5's grammar for an effect background is `BtlvEffect_SetVanish` (`btlv_effect.c:776`, hide the stage)
plus `LoadBg`: the stage goes and the picture is there. `BATTLE_BG_SWITCH_MODE_CUT` (3; the restores moved to
mode + 4) does that:

- The SwitchBg command runs the switch's first state itself, so the arena is hidden (new suppression reason
  `BATTLE_STAGE_SUPPRESS_EFFECT_BG_CUT`, instant like the menu's and not counted as a hard pop) before the
  stage draws again.
- The BW2 picture's mode, tiles and screen go to VRAM in the next VBlank (`BattleEffectBg_UploadOnVBlank`), with
  its palette, which PaletteData commits in the same VBlank. No frame shows it half loaded, and there is no
  black frame (`effect_bg_cut` below).
- `RestoreBg ... BATTLE_BG_SWITCH_MODE_CUT` puts the backdrop back the same way and clears the reason; the arena
  comes back at once (its instant comeback after an instant hide).
- `WaitForPartialBgSwitch` also passes when the switch has already finished, since a cut can finish first.
- Without the stage (classic, L+R+SELECT), the same code makes a 2D cut between backdrop and picture.

**Where the fade stays** (an anim that depends on it):

- Moonlight, Wish, Cosmic Power, Lunar Dance, Moonblast: the scene darkening into the night sky or space is the
  move.
- Nightmare and Dark Void: the fade to black is the nightmare or the void falling.
- Trick Room: BLEND mode, the room grid half-blended over the backdrop, is the effect.
- The three trap-damage common anims.

Every other move cuts, both ways.

## The 17 shake moves that faded the arena

gen5_camera_gaps.md and moves.md (chunk 6) list 17 SwitchBg moves that shake BG3 under a faded arena (Mega Kick,
Double-Edge, Hydro Pump, Hyper Beam, Seismic Toss, Fissure, Selfdestruct, Aeroblast, Zap Cannon, Dynamic Punch,
Megahorn, Focus Punch, Volt Tackle, Giga Impact, Leaf Storm, Head Smash, Spacial Rend). All 17 now cut to their
BW2 picture, and the shake moves the picture, as BW2's background shake does with the stage hidden. `redo/shake.json`
marks them `expect: cut`. Focus Punch's tester run plays its focus branch, so it shows no picture there.
Re-verified on the stage, day and night (`move_redo`): for the other 16, fades +1 became +0, hardPops stays 0,
the arena is hidden 15-33 frames less per move (no fade out and in), arenaAlpha is 31 and the camera home after.

## Checking

The critic (tools/battle_stage/emu/critic.py) knows this work through `docs/living_battle_stage/redo/effect_bg.json`
(written by `bw2_effect_bg.py redo`): per move `expect` (`cut` or `fade`), `bw2_bg_id` and `pal_anim`.

- `move_redo --moves <list>`: expect `cut` checks that the arena hid with no fade (hiddenFrames up, fades 0), and
  every effect_bg move that `sBattleEffectBgStats` (battle_anim_effect_bg.c, read through the xMAP) loaded the
  right BW2 bgID, counted a cut, stepped its palette anim, and left no cut or anim running 90 frames later.
- `switchbg_moves --moves <list>`: plays the list instead of its four moves, with the same checks.
- New scenario `effect_bg_cut --moves <list>`: every frame around the switch in and back, stage on and off.
  A cut move must never show an arenaAlpha between 0 and 31, and at most 2 black frames per transition; a fade
  move must still fade. Sheets `cut_<id>_<tod>[_classic].png`.

Evidence: `/tmp/bw2vis/effect-bg/README.md`.
