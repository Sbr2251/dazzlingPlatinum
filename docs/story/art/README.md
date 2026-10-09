# Arc 1 field sprites (Art stream)

Final overworld art for the five object graphics the Arc 1 part 2 pre-work registered with placeholders
(see `docs/arc1/part2/sprites.md` for the registration). Only the five PNG sheets change; nothing in the
registration (gfx list, overlay 5 tables, mmodel meson, `tools/integrate_arc1_field_sprites.py`) does.

| constant | sheet | built from | design |
|---|---|---|---|
| `OBJ_EVENT_GFX_SAROS` | `res/field/objects/arc1/saros.png` | Prof. Rowan walker (member 0x5E) | Team Eclipse leader. Long blue-black coat with a tall stand-up collar (his silhouette), violet waistcoat, Eclipse brooch at the throat, large Eclipse ring on the coat back. Swept-back slate hair gone silver at the temples, gaunt pale face, heavy brows: grief has aged him. Reads apart from Cyrus (blue spikes), Looker (trench coat) and Rowan (white hair) in the same scenes. |
| `OBJ_EVENT_GFX_ECLIPSE_GRUNT_M` | `res/field/objects/arc1/eclipse_grunt_m.png` | Galactic Grunt M walker (0x67) | "The Eclipse look: dark, with a violet eclipse ring" (`docs/story/artwork.md`). Dark hooded uniform instead of Galactic's teal bowl cut and white suit; the Eclipse mark (black disc in a glowing violet ring) on the hood front, hood back, hood side and chest; violet belt; grey boots. |
| `OBJ_EVENT_GFX_ECLIPSE_GRUNT_F` | `res/field/objects/arc1/eclipse_grunt_f.png` | Galactic Grunt F walker (0x68) | Same uniform and palette as the male, plus lilac-silver hair falling out of the hood at the front and a ponytail out of the back. |
| `OBJ_EVENT_GFX_ARC1_RIFT` | `res/field/objects/arc1/arc1_rift.png` | procedural | Scene 14's "small violet rift hangs in the air": a jagged vertical tear above the ground, black-violet core with a slow swirl, hot violet rim, pale glow, drifting shards, a faint glow on the floor. Frame B breathes (a pixel narrower), the rim flicker and swirl move and the shards rise. |
| `OBJ_EVENT_GFX_TOTEM_HITMONLEE_VIOLET` | `res/field/objects/arc1/totem_hitmonlee_violet.png` | stock totem frames (`res/field/objects/totems/hitmonlee_idle_{a,b}.png`) | "A Hitmonlee, far too big, wreathed in a violet aura": the totem recoloured to a dark violet silhouette with glowing eyes, inside a two-pixel aura whose outer ring, glints and rising wisps alternate between the frames. |

Design sheets:
- `arc1_sprites_sheet.png`: every frame of the five sheets at 4x, next to the stock sprite each was built
  from, with the palettes.
- `arc1_sprites_ingame.png`: the sprites in game (scratch build, not committed) at noon and at night
  on Twinleaf, the scene 14 staging in Oreburgh Mine B2F, the Jubilife TV plaza, and walk cycles.

## Sheet format (unchanged from the pre-work)

- Walkers: 128x128, rows up/down/left/right, columns stand/step A/stand/step B. Right is the exact mirror
  of left, as in every stock Platinum walker.
- Idle objects: 64x32, frame A then frame B, looped like the Totem idle, the same for every facing. Use
  `MOVEMENT_TYPE_NONE`.
- 4-bit indexed PNG, 16 colours, index 0 transparent. Colours are stored already snapped to BGR555, so
  the PNG shows exactly what the DS shows.

## Regenerating

```sh
python3 tools/arc1_sprites/gen_arc1_sprites.py           # writes the five PNGs (pure Python, no PIL)
python3 tools/arc1_sprites/gen_arc1_sprites.py --check   # fails if a committed PNG is stale
python3 tools/integrate_arc1_field_sprites.py check      # the registration's own validator
~/.venvs/desmume/bin/python tools/arc1_sprites/design_sheet.py [--ingame DIR]   # design sheets (PIL)
```

How the walkers are made (`tools/arc1_sprites/walker.py`): the stock walker supplies the walk cycle (leg
poses and the 1 px bob of the step frames). The generator remaps its colours onto the character palette,
clears the stock head, paints a hand-drawn head for each direction (ASCII grids in `saros.py` and
`eclipse_grunts.py`) that follows the bob, and adds overlays (collars, emblems, belts). To change a
design, edit the grids or palettes and rerun the generator.

## In-game check (how the second sheet was made)

```sh
python3 tools/arc1_sprites/scratch_events.py   # SCRATCH: adds objects to 3 events JSON files
flock .build.lock make release
mkdir -p /tmp/rom && cp out/dazzlingPlatinum.nds build/main.nef.xMAP /tmp/rom/
SDL_VIDEODRIVER=dummy A1P2_REPO=$PWD ~/.venvs/desmume39/bin/python tools/arc1_sprites/ingame_capture.py /tmp/rom /tmp/shots
~/.venvs/desmume/bin/python tools/arc1_sprites/ingame_capture.py --check /tmp/shots
git checkout res/field/events/                 # never commit the scratch placement
```

`ingame_capture.py` uses the Arc 1 part 2 harness (`/tmp/act1p2/harness`) and pins the clock through
`sDebugClockHour`. In the palette check, every inner pixel of every unoccluded walker matched a colour of
its palette, and most matched the exact index. The misses were sprites cut off by the screen edge or
covered by the pond's reflection layer. Idle objects matched 93-100%; the stock totem scored the same
way, because neighbouring billboards overlap and the totem quad is resampled.

## Notes

- Scope: overworld sprites only. There are no Eclipse grunt or Saros battle sprites or trainer classes
  in Arc 1, because there are no battles with them yet (decisions D2/D3). These are follow-ups.
- The grunts are dark by design. They read well on Jubilife's pavement in daylight and at night. On very
  dark floors, lean on the violet ring and belt.
- Keep the distinct gfx count low on crowded screens (the spec's Jubilife budget). Saros plus both grunts
  adds 3 textures.
