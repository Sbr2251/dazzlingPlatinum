# Arc 2 sprites (art-ph)

Overworld art for the seven object graphics R0 registered with placeholders (`tools/integrate_arc2_field_sprites.py`,
mmodel members 484-490), plus placeholder battle sprites for the three Eclipse trainer classes. Only the PNGs change;
the registration is untouched.

Copyright: every pixel is either new or an edit/recolour of Platinum's own assets (stock walkers and trainer sprites).
Nothing is taken from other games.

| constant | sheet | built from | design |
|---|---|---|---|
| `OBJ_EVENT_GFX_INDRA` | `res/field/objects/arc2/indra.png` | Cynthia walker (0x75), head/collar redrawn, all colours remapped | Tired, hard Eclipse leader. Jaw-length dark-auburn bob with a heavy fringe swept from her right, pale face, heavy lids, shadows under the eyes. Long violet-black coat buttoned to a high collar with a dark violet lining, the Eclipse mark as a clasp at the throat and a large ring on the coat back. Cynthia's long hair is painted out. Shares the leaders' mark with Saros, not his silhouette (no collar points, no silver hair). |
| `OBJ_EVENT_GFX_KAHN` | `res/field/objects/arc2/kahn.png` | Sailor walker (0x36), recoloured, sleeves/badge/beard added | Quiet sailor turned leader. The white sailor cap becomes a navy officer's cap with an Eclipse-violet band and a small Eclipse badge; navy pea-coat sleeves over the sailor's bare arms; sea-teal jersey; the red neckerchief turned violet; dark trousers; weathered skin, dark hair and a short beard. |
| `OBJ_EVENT_GFX_LOOKER_JANITOR` | `res/field/objects/arc2/looker_janitor.png` | Looker walker (0x178) | Looker's own face and hair, his coat recoloured to slate-blue coveralls (tie becomes the zip), a matching cap with a white badge, a mop planted beside him (drawn behind the body, fixed to the cell). |
| `OBJ_EVENT_GFX_LOOKER_NEWSPAPER` | `res/field/objects/arc2/looker_newspaper.png` | Looker walker (0x178) | Brown fedora, black sunglasses, an open newspaper held in both hands, upside down (headline bar at the bottom). From behind, the paper's corners show past his shoulders; side-on, he holds it out in front. |
| `OBJ_EVENT_GFX_ECLIPSE_CRATE` | `res/field/objects/arc2/eclipse_crate.png` | new pixels | Wooden crate, plank lid, steel corner brackets, the Eclipse mark (black disc, violet ring, eight rays) stencilled on the front. Frame B only moves a glint. |
| `OBJ_EVENT_GFX_SHARD_FRAME` | `res/field/objects/arc2/shard_frame.png` | new pixels | Upright steel frame on a wide foot, a black crack through the top bar, violet scorch, two empty chains with open cuffs, Eclipse Shard crystals on both top corners and the base. Frame B: the shards' highlights jump and glow pixels light around them. |
| `OBJ_EVENT_GFX_RIFT_ARC2` | `res/field/objects/arc2/rift_arc2.png` | new pixels (procedural) | A tall, leaning violet tear, larger and rougher than Arc 1's mine rift: pale torn lips, black-violet void with white specks, hairline cracks running out into the air. Frame B pulses. |

Battle (trainer class) sprites, placeholder quality by plan (art-final draws the real ones):

| class | files | what |
|---|---|---|
| `TRAINER_CLASS_ECLIPSE_GRUNT_M` | `res/trainers/classes/eclipse_grunt_m/front.png`, `front_scan.png` | Galactic Grunt M with the white suit turned into the dark Eclipse uniform, violet shading, violet "G" glow, dark violet hood colour for the hair |
| `TRAINER_CLASS_ECLIPSE_GRUNT_F` | `res/trainers/classes/eclipse_grunt_f/front.png`, `front_scan.png` | Galactic Grunt F, same uniform, lilac-silver hair (matches the overworld grunt F) |
| `TRAINER_CLASS_ECLIPSE_LEADER` | `res/trainers/classes/eclipse_leader/front.png`, `front_scan.png` | Commander Mars recoloured as Indra: dark-auburn hair, violet-black coat, violet trim |

They are PLTE-only rewrites of the stock sources (`tools/arc2_sprites/trainer_sprites.py`): pixels, cell/anim JSON and
the scan keys are unchanged. The white half of the held Poke Ball shares the suit's white index, so it reads lavender.

Sheets:
- `arc2_sprites_sheet.png`: every frame of the seven sheets at 4x next to the stock sprite each was built from, with
  palettes.
- `arc2_sprites_ingame.png`: in game (scratch build, not committed) at 4x next to stock NPCs on Twinleaf, noon and
  night, the crate/frame grounding comparison, and the three battle intros.

## Known issue: the crate and frame float (needs a 2-line change outside art-ph)

R0 registered all three idle2 objects with the Totem renderer (`Unk_ov5_021FB0B4`). Its init (`ov5_021ECB34`) lifts the
billboard 24 units, like the floating lake guardians, and the shadow stays on the tile. That suits the rift, but it
leaves the crate and the shard frame hovering about 12 px above the ground. Pointing their two rows in the renderer
table (`Unk_ov5_021FB97C` in `src/overlay005/ov5_021FAF40.c`) at `Unk_ov5_021FAF9C` (Dialga/Palkia's renderer, no lift)
grounds them. This was tested in a scratch build; see the comparison in `arc2_sprites_ingame.png`. The patch is
`/tmp/a2/art-ph/ground_objects.patch`. Changing the model id in the animation table has no visible effect.

## Regenerating

```sh
python3 tools/arc2_sprites/gen_arc2_sprites.py            # writes the 7 PNGs (pure Python, reuses tools/arc1_sprites)
python3 tools/arc2_sprites/gen_arc2_sprites.py --check    # fails if a committed PNG is stale
python3 tools/arc2_sprites/trainer_sprites.py [--check]   # the 6 battle PNG palettes
python3 tools/integrate_arc2_field_sprites.py check       # the registration's own validator
~/.venvs/desmume/bin/python tools/arc2_sprites/design_sheet.py [--ingame SHOTS --battle BATTLE]
```

## In-game check

```sh
python3 tools/arc2_sprites/scratch_events.py A            # SCRATCH (A, B, or T): objects on Twinleaf
make release
mkdir -p /tmp/romA && cp out/dazzlingPlatinum.nds build/main.nef.xMAP /tmp/romA/
SDL_VIDEODRIVER=dummy A2_REPO=$PWD ~/.venvs/desmume39/bin/python tools/arc2_sprites/ingame_capture.py /tmp/romA SHOTS A 12 21
# scene T: battle_capture.py ROM_DIR BATTLE  (walks into each trainer's sight, saves the intro frames)
git checkout res/field/events/events_twinleaf_town.json   # never commit the scratch placement
```
