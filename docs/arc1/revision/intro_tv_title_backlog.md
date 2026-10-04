## Arc 1 small items: where each one lives and what to change

I only read files: nothing was edited, built or committed. Line widths below are measured with `res/fonts/font_message.json` glyph widths. Field and intro message boxes are 27 tiles (216 px) wide, 2 lines per page. The widest stock line I checked is 192 px, and the shipped bedroom line "gaining followers at an unprecedented" is 203 px. Everything proposed here is 197 px or less.

### 1. Rowan intro
- **Now:** one message, `RowanIntro_Text_HelloThere` (`res/text/rowan_intro.json:5-11`), 2 pages. It's shown in `RI_STATE_DIALOGUE_WELCOME` (`src/applications/rowan_intro/rowan_intro_app.c:1360-1365`). The window template is at `:739-747` (width 0x1B, height 4).
- **Change:** text only. Grow the `HelloThere` array; the multi-page `\r` flow already works, so the C code doesn't change. It goes from 2 pages to 7:
  ```
  "Hello there! My name is Rowan.\n","Welcome to the world of Pokémon!\r",
  "The journey you are about to embark\n","upon is not the Sinnoh you remember.\r",   (197/197 px)
  "It is a parallel Sinnoh, a world much\n","like the one you know...\r",
  "...but where events have unfolded\n","differently, down to the very map.\r",     (map differences)
  "Your story begins after the tale\n","you know, when Team Galactic fell.\r",      (after the original Platinum story)
  "Some people you may recognize.\n","Some places may feel familiar.\r",
  "And some events...\n","may be very different.\r"
  ```
- That's about 5 more boxes. If the owner wants it shorter ("not too verbose"), drop page 3.

### 2. "Giratina Custom Opening Intro is too slow, 1.7x" (doc line 275)
**Most likely meaning: the pre-rendered Giratina title loop.** It's the custom Blender-made Giratina asset, the note sits among engine notes rather than in the story section, and "1.7x speed" reads like a playback rate. The other candidate is the new-game flashback, which the owner calls "the opening cut scene" at line 332. Both fixes are below; a one-line check with the owner settles it.

**A. Title loop.** `res/graphics/title_screen/giratina_prerender.bin` is 360 steps, each held 2 VBlanks, so 12.0 s.
- **Preferred: repack with no tool changes.** `pack_frames.py --schedule` takes a comma list of `A-B:STEP:HOLD`. Pass 212 single-frame entries (`f-f:1:2`, f = round(1 + i·360/212)). That gives a 7.07 s loop (1.70x) and keeps the current 15 fps smoothness. Check the heap and VRAM budgets with `simulate.py --schedule <same>`.
  - The source frames (`/tmp/gir_prerender/frames256.npy`) are gone. Either re-render with `render_frames.py` from `giratina_title_v2_snapshot.blend` (not on this box), or decode the current bin to PNGs with `simulate.py` (`s%03d.png`) and repack from those. The second route costs one extra dither pass.
  - Also change `LOGO_FLASH_FIRST_STEP` (`src/applications/title_screen.c:107`) from 219 to about 129. Optionally shorten `sLogoFlashWeights` (`:1695`).
- **Code-only alternative:** in `TitleScreen_PrerenderVBlank` (`title_screen.c:~1950`), replace `nextFlipAt += pendingHold` with a fixed-point accumulator (hold × 10/17, about 1.18 VBlanks per step).
  - This needs about 51 decodes per second, and the main loop does at most one per frame (`TitleScreen_PrerenderPrepareNext`, `:1905`).
  - Each decode means a card read, LZ, and a 48 KB copy. If the loop can't keep up, the existing resync just plays it slower. Quicker to try, but riskier.

**B. Flashback pacing** (`res/field/scripts/scripts_distortion_world_giratina_room.s:177-233`).
- **Waits:** the `WaitTime` calls at 179, 199, 202, 205, 210, 213, 215 and 223 add up to 254 frames. Scaling them by 1/1.7 gives 30→18, 20→12, 12→7.
- **Fade:** at `:224`, change `FADE_SCREEN_SPEED_SLOW` to normal.
- **Camera:** `Arc1CameraFollowCyrus` (`:288`) goes from `WalkNormalSouth 3` to `WalkFastSouth 3`.
- **Fly-by:** the two Giratina room passes in `Unk_ov9_02252414` (`src/overlay009/ov9_02249960.c:6522-6543`) change velocity from `FX32_ONE*48` to `*82` and frame count from `0x20` to `0x13`.
- **Limit:** most of the scene's length is the 14 dialogue boxes (msgs 15, 8, 9, 10), and only trimming text shortens those.

### 3. Flashback: "rises and hurls" vs. "shadow takes him"
- **Now:** since 77009099d, the shadow makes a high pass (`ScrCmd_321 1`), Cyrus notices (msg 17), it swoops low (`ScrCmd_321 2`), and `ScrCmd_312 130` makes him vanish. Msg 18 says "It took him...".
- **Earlier version:** 6d75c219b showed Giratina rising: it set `VAR_DISTORTION_WORLD_PROGRESS` to 13, spawned object 128 and played a lunge. 77009099d replaced that, presumably on purpose.
- **Cheapest match:** keep the swoop and turn it into a throw, in the script plus text.
  1. Before `ScrCmd_312 130` (`:212`), add `ShakeCamera` and a white `FadeScreenOut/In` (the rift flash).
  2. Give Cyrus a short knock-back movement (a backward fast step or jump) right before he vanishes.
  3. Reword msg 18 to "It threw him... straight through a rift." and say "rift" in the caption.
- **Doc's "rises" too:** add a third fly-by entry with Y velocity (Giratina climbing) to the same ov9 table.

### 4. Bedroom TV: breaking news
- **Script:** `TwinleafTownPlayerHouse2F_OnFrame_ConcludeSpecialProgram`, `res/field/scripts/scripts_twinleaf_town_player_house_2f.s:28-43`. Text is in `res/text/twinleaf_town_player_house_2f.json:4-39`. The stock `tv_app.c` no longer runs.
- **Change:** after `ProfRowanTeamEclipse` (`:35`), add `PlaySound SEQ_SE_DP_TV_NOISE` and `WaitSound`, then `BufferCounterpartName 0` (the stock macro, which gives Dawn or Lucas, opposite to the player per the spec), then a new message:
  ```
  "We interrupt this program with\n","breaking news!\r",
  "A strange portal has opened above\n","the castle at Lake Verity!\r",
  "Prof. Rowan and his assistant,\n","{STRVAR_1 3, 0, 0}, are on site investigating.\r",
  "Residents are urged to stay away\n","from the lake until further notice."
  ```
  Optionally wrap "BREAKING NEWS" in `{COLOR …}`; a graphic banner isn't cheap.
- **Outro:** drop `ThatConcludesOurSpecialProgram` and `SeeYouNextWeek` (`:36-38`), or move them before the interruption. Their "Broadcast live from Lake Verity" line contradicts the news.

### 5. Barry and Twinleaf exit lines (doc line 304); Running Shoes
- **Bedroom line:** `TwinleafTownPlayerHouse2F_Text_ThatTeamEclipseReallyIsSomething` (json `:74-82`). Replace with:
  `"Hey, {P}! Man, that Team\n","Eclipse really is something.\r","Anyways, did you see the news?!\r","There's a portal over the castle at\n","Lake Verity, and Rowan's up there\r","right now! We should go help him out!\r","Then maybe Rowan would owe us some\n","starter Pokémon!\r"`
  Also change `…WereGoingToSeeProfRowanAndGetPokemon` (`:99-106`) to "Oh, right, right! We're going to help / Prof. Rowan at Lake Verity!"
- **Exit lines:** Twinleaf's own scripts are stock. The D/P gating lives in Route 201:
  - `Route201_Text_Arc1ImGoingToLakeVerity` (`res/text/route_201.json:557-565`, used at `scripts_route_201.s:1309`): change it to "I'm going to Lake Verity to help / Prof. Rowan with that portal! / Help him out, and I bet he'll owe / us some Pokémon of our own!"
  - `ISaidTheLakesNotThatWay` (`:468-472`, used at `:1357`) is fine, but it contains a stock curly apostrophe.
- **Running Shoes: already done.** `scripts_twinleaf_town_player_house_1f.s:43-52` gives them in `OnFrame_RivalAlreadyLeft`, the first time downstairs (commit 3a09acc32).

### 6. Cyrus roof monologue
- **Where:** `LakeVerity_Arc1OnFrameRoofLanding` (`scripts_lake_verity.s:382-418`); the text is `LakeVerity_Text_Arc1CyrusWhereAmI` (`res/text/lake_verity.json:256-262`). These files belong to the Lake Verity agent, so coordinate with them.
- **Change:** first page becomes `"Cyrus: ...Where am I?\n","Is this a dream?\r"`. Then add a "differences" page after "Space holds its shape.":
  `"A castle... on Lake Verity?\n","There was never a castle here.\r"`
  and optionally `"The lake, the mountains... the same.\n","And yet, not the same at all.\r"`.
- **Optional:** "wanders the rooftop" could be a few `WalkSlow` steps added to `LakeVerity_Movement_Arc1CyrusLookAround` (`:677`).

### 7. Out-of-scope backlog (doc lines 1-80, 180-262)

| Item | Feasibility |
|---|---|
| Difficulty choice on new game | Medium: one save var, a choice in Rowan's intro, and alternate trainer tables. "Tournament-winner strategies" means hand-authoring teams and AI flags (large). |
| Boss/Totem battles | Partly there already: totem encounters, aura and BGM tools exist. More totems are content work. |
| FOE Pokémon (fast blobs, uncatchable, boosted) | Medium: reuse the totem overworld sprites and a scripted battle like `StartArc1MawileBattle`, plus a fast movement type. |
| Remove HMs, auto-unlock after gym/totem | Medium: change the field-move checks to flag checks and keep the HM moves out of the way. |
| Gym leaders with 6 Pokémon + Megas from the 3rd gym | Low to medium: `res/trainers` data. Megas are already in. |
| Starter Megas | Medium: sprite, data and item work, same as the existing 7 Megas. |
| Controlled pseudo-legendary availability | Low: encounter table edits. |
| Lava tiles at Mt. Coronet | `tools/coronet_lava` exists. Art work. |
| Quests, islands (Darkrai, Cresselia, Manaphy) | Large: maps, scripts and story. |
| Dual-screen 3D overworld | XL and risky (VRAM, 30 fps). |
| Streamed adaptive soundtrack | Large. The streaming code exists but no streams are set up yet. |