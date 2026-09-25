# Living 3D Battle Stage - Implementation Plan

Goal: replace the flat battle backdrop with a lit 3D arena, turn the Pokemon
sprites into lit, deformable meshes, and let the camera move for cinematic
moments (battle intro, Mega Evolution, Totem intro), without breaking the ~470
existing move animations.

The work is split into 7 chunks. Each ends with a ROM the user validates in
their own emulator before the next chunk starts.

---

## What the code does today (research summary)

- **3D layer.** BG0 is 3D (priority 1); BG3 is the 256-colour backdrop (priority 3);
  BG2 is the move-animation effect layer; BG1 is the text box. Set up in
  `ov16_0223C004` / `ov16_0223CD9C` (`src/battle/ov16_0223B140.c`): toon shading,
  alpha blend and antialias on, fog/edge marking off, no lights, no toon table.
- **Frame order** (`ov16_0223CF48`): particles -> `PokemonSpriteManager_DrawSprites`
  -> OBJ -> `G3_RequestSwapBuffers(MANUAL, Z)`. In the bag/party menus
  (`unk_23F9 == 3`) particles are skipped.
- **Pokemon sprites** (`src/pokemon_sprite.c:453`): each mon is ONE unlit quad
  (`NNS_G2dDrawSpriteFast`, `GX_LIGHTMASK_NONE`) under an ortho camera where
  1 unit = 1 screen pixel (`NNS_G2dSetupSoftwareSpriteCamera`). Scale changes the
  quad size, flip/mosaic are CPU texture rewrites, fade is a CPU palette blend,
  shadows are separate quads at z = -1000.
- **Platforms** are 2D OBJ sprites (`src/battle/ov16_02268520.c`), per terrain.
  **Backdrop** comes from prebuilt `pl_batt_bg.narc` (23 backgrounds x 3
  time-of-day palettes). Chosen by map header + tile behaviour
  (`src/field_battle_data_transfer.c`).
- **VRAM.** 256 KB texture (banks B+C), 16 KB palette managed. Sprites own the
  first 32 KB; particles allocate dynamically (median 3.4 KB, max 31 KB).
  **Bank C is unmapped while the bag/party menu is open**, so anything in the
  upper 128 KB is lost and must be re-uploaded afterwards.
- **No 3D models exist in battle, and no tool can author a model from scratch**
  (only patchers for existing NSBMD/NSBTX). `Easy3DModel_*` helpers exist for
  drawing NSBMD if we ever produce one.
- **Cameras.** Only the particle systems have one (forced orthographic,
  `battle_anim_system.c:415`). Battler particle positions are a hand-tuned
  table (`battle_anim_util.c:196`).
- **Move-animation mechanisms at risk** (37 of 87 script funcs move sprites):
  direct x/y/scale/rotation writes, partial draw (UV clip), mon copied to BG2
  + HBlank wave (Acid Armor, Extrasensory, Spite, Camouflage), mon copied to
  OAM (Double Team, Agility, Aerial Ace, Surf, ...), window masks/blends that
  assume a 2D rectangle (Harden, Fake Out, stat changes), `SwitchBg` backdrop
  swaps (55 scripts), particles at fixed positions.
- **Custom hack effects touching this:** Mega Affine Pulse (brightness blend that
  deliberately excludes BG0), Totem aura (persistent ortho particle system
  that follows the sprite), Mega charge/burst particles.
- **No debug battle launcher and no hack feature flags exist.**

---

## Core design decisions

1. **"Home pose" rule.** The stage camera has a home pose where every sprite
   lands on exactly the same screen pixels as today. Move animations only
   ever run at home pose; the camera only leaves home during scripted
   cinematic moments and is forced back (`BattleStage_CameraReturnHome`)
   before any move animation starts. This keeps nearly all move animations
   working unchanged and confines breakage to the rendering-mode changes.
2. **Sprites keep their 2D logical coordinates.** Move animations keep writing
   `MON_SPRITE_X_CENTER` etc. in screen pixels. The new renderer maps the 2D
   logical position to a world-space position on the arena floor. At home pose
   that mapping is identity-on-screen.
3. **Arena is generated, not modelled by hand.** A Python tool builds each
   arena from the art the game already has: the backdrop image becomes a
   curved panorama (real parallax when the camera moves), the ground comes from
   the lower backdrop band + platform art, and platforms become low-poly discs
   textured with the existing platform sprites. That gives all 23 backgrounds
   in a consistent style for free. Hand-authored props (trees, rocks, pillars)
   can come later per terrain.
4. **Own display-list format, not NSBMD.** Since nothing can author NSBMD, the
   tool emits a compact binary (vertex/UV/normal/colour lists + DS texture
   formats) packed into a new NARC, and `src/battle/battle_stage.c` draws it
   with G3 commands. Avoids building an NSBMD writer.
5. **Budgets.** Arena <= ~600 polygons and <= 64 KB textures placed in the
   lower 128 KB (bank B), so it survives the menu bank swap without a reload.
   The 4 sprite meshes add <= 4 x 64 quads. Total stays well under the 2048
   polygon / 6144 vertex hardware limit even with heavy particles.
6. **Compile-time switch** `BATTLE_STAGE_3D` (new header
   `include/config/battle_stage.h`) plus a debug-only runtime toggle, so the
   old path stays available for A/B comparison and as a fallback.

---

## Agent team

For each chunk:

| Role | Who | Does |
|---|---|---|
| Lead | main session | Owns this plan and the interfaces between pieces, splits the work, merges, runs the ONE `make release`, commits/pushes, tells the user the ROM is ready |
| Implementers | 2-4 subagents, each in its own git worktree | Each owns disjoint files (e.g. tool vs renderer vs compatibility). They write code and do NOT run `make release` in the main tree |
| Reviewer | 1 subagent per merge | Adversarial review against DS constraints: fixed-point overflow, geometry FIFO/polygon budget, VRAM layout and menu bank swap, matrix stack push/pop balance, and preserving every `MON_SPRITE_*` attribute |
| Visual critic | 1 subagent per chunk | Runs `tools/battle_stage/emu/critic.py` on the built ROM (headless py-desmume, scripted scenarios through the debug combos), inspects the contact sheets, and reports obvious breakage (black or garbled screens, freezes, missing sprites, broken menus) before the ROM reaches the user. Issues go back to the implementers |
| Move fixers (chunk 6) | 1 subagent per breakage category, with a critic | Redo the broken moves |

Chunk 6 runs as a workflow (parallel per category, loop with the critic).
Chunks 0-5 are mostly sequential, with 2-4 parallel implementers inside
each chunk.

---

## Chunks

### Chunk 0 - Foundations and test tools (no visible gameplay change)

Build:
- `BATTLE_STAGE_3D` config header, and `src/battle/battle_stage.c/.h` skeleton hooked into
  battle init/teardown/draw (draws nothing yet).
- **Debug quick-battle** (`DEBUG_BATTLE_TOOLS` only). In the overworld, hold L+R and press:
  UP/DOWN to cycle a background+terrain pair (shown on screen), LEFT/RIGHT to
  cycle the opponent species, A to start a wild battle there, X to start a Totem
  battle with its intro, START to get the debug party (Key Stone + a Mega-capable
  mon holding its stone). SELECT stays free for the registered item.
- **Debug move tester:** in battle, at the command menu, hold L+R: LEFT/RIGHT
  changes the move ID by 1, UP/DOWN by 10, A plays its animation player->enemy
  without running the move, Y enemy->player.
- **In-battle A/B toggle:** hold L+R and press SELECT to flip the 3D stage on/off live.
- **Critic harness:** `tools/battle_stage/emu/` (scenarios, contact sheets, report).

User validates: normal play is unchanged. The debug combos work: backgrounds
cycle, the move tester plays animations, the Totem combo starts the intro.
A save next to grass is still useful but no longer needed.

### Chunk 1 - Static 3D arena, one background (PLAIN / grass)

Build:
- `tools/battle_stage/`: extract backdrop/platform art from `pl_batt_bg.narc` /
  `pl_batt_obj.narc`, generate the panorama + ground + platform-disc meshes,
  convert textures to DS formats, write `battle_stage.narc`.
- Renderer: stage camera (perspective) at home pose; draw the arena first, then
  restore the sprite ortho camera for particles/sprites. Hide BG3 and the 2D
  platform OBJs while the stage is on.
- Compatibility basics: when a move uses `SwitchBg` or a BG3 effect, fade
  the arena out and show BG3 again, then restore it. Keep the text box, HP bars and
  menu transitions untouched. Survive the bag/party bank swap.

User validates (grass battle via the debug launcher): it looks like today but the
ground and platforms are 3D (the A/B toggle shows the difference). Sprites and
shadows sit correctly on the platforms. Opening the bag/party and returning
leaves nothing corrupted. A few `SwitchBg` moves (e.g. Night Shade, Psychic,
Dark Pulse) still show their special backgrounds.

### Chunk 2 - Light, atmosphere, and all 23 backgrounds

Build:
- Hardware directional light + ambient for the arena, toon/highlight table,
  distance fog, optional edge outlines. Light colour and direction follow time of
  day (morning / day / night palettes already exist).
- Generate arenas for all 23 backgrounds (caves darker with fog, snow bright,
  water with a moving UV-scrolled surface, Elite Four / Champion rooms,
  Distortion World, Frontier). Map each terrain to its platform disc.
- Fix the Mega Affine Pulse brightness so the arena dims/flashes with the scene.

User validates: cycle all backgrounds with the debug launcher at different
times of day. Lighting and fog look right, nothing is missing or glitched, and the
Mega flash dims the arena too.

### Chunk 3 - Lit, deformable Pokemon sprites

Build:
- Replace the single quad with an N x N grid (8 x 8 to start) with per-vertex normals,
  lit by the same light as the arena. Keep every `MON_SPRITE_*` attribute
  working: partial draw (clip the grid UVs), flip/mosaic/fade (unchanged CPU
  paths), alpha, dim (material), rotation and scale (applied to the grid).
- Idle "breathing": squash/stretch anchored at the feet plus a slight sway,
  phase-offset per battler, paused during move animations.
- Shadows drawn as soft blobs on the 3D ground under each mon.
- Hit reaction: a quick grid wobble when damage is dealt.

User validates: mons breathe and are lit consistently with the arena. The
silhouette intro, Mega squeeze/reveal and Totem aura still look right.
Minimize, Dig/Fly (partial draw), Substitute and Transform are fine in the move tester.

### Chunk 4 - Camera system and cinematic moments

Build:
- Keyframed stage camera (position/target/FOV, eased) with world-space sprite
  billboards when off home pose, and exact home-pose equivalence.
- The particle camera follows the stage camera during cinematics so the Mega
  charge/burst and Totem aura stay attached.
- New anim-script commands: `StageCameraMove`, `StageCameraOrbit`,
  `StageCameraShake`, `StageCameraHome`, plus the hard "return home before move
  animation" guard.
- Cinematics: battle-start sweep across the arena onto the opponent, a Mega
  Evolution orbit around the mon during charge -> burst, a Totem intro push-in,
  a small camera kick on critical hits and on fainting.

User validates: the intro sweep, a Mega Evolution, the Totem intro, crits and faints.
Every move in the move tester still plays at home pose.

### Chunk 5 - Move compatibility audit and generic fixes

Build:
- A headless-free audit: agents classify every move's anim script by the
  at-risk mechanisms above and produce `docs/living_battle_stage/move_audit.md`
  (move -> mechanisms -> expected breakage -> fix class).
- Generic fixes in shared helpers so whole categories work at once:
  `LoadPokemonSpriteIntoBg` / `AddPokemonSprite` copies match the lit mesh
  (bake the lighting into the copy, hide the mesh while the copy shows),
  window masks that include the arena, `SetSpriteBgBlending` targets,
  HBlank wave effects over the arena, `SwitchBg` transitions.

User validates: walk the move tester through the audit's "high risk" list and
mark what still looks wrong. That list feeds chunk 6.

### Chunk 6 - Redo the moves that still break

Build (a workflow: one agent per breakage category, each paired with a critic):
- Per-move rewrites of what the generic fixes couldn't handle, optionally
  upgrading them to use the stage (Earthquake shakes the camera, Fly/Bounce
  cut to a low angle, Surf's wave crosses the arena floor, Dig opens a hole in
  the ground mesh, Double Team spreads copies in depth).
- Batched by category so each batch is one ROM to validate.

User validates: each batch's moves in the move tester, and a normal
playthrough battle or two.

---

## Main risks

- **Home-pose match.** The perspective arena plus the ortho sprites must line up to the pixel;
  if they don't, sprites look like they float. Mitigation: the chunk 1 A/B toggle,
  and sprite depth taken from the platform position.
- **BG0 is shared.** The Totem aura, particles, sprites and now the arena all live in the
  3D layer. Translucency ordering (`GX_SORTMODE_MANUAL`) and the existing
  "exclude BG0 from brightness" Mega blend need care.
- **VRAM/menu swap.** Arena textures must stay in bank B, or be re-uploaded after menus.
- **Toon shading is on with no toon table.** Turning lights on changes the look of
  everything drawn MODULATE, including particles, so light masks must be set per
  object.
- **Emulator differences.** melonDS and DeSmuME differ on edge marking, fog and
  capture. The user should test chunk 2 in both.
- **Arena art quality.** Generated panoramas from 2D art may look flat up close;
  hand-made props per terrain are a possible follow-up chunk.
