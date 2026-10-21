# Animated battle trainers (BW2 art for generic classes)

BW2 animates almost every battle trainer (173 of 188 fronts, MCSS idle loops). Platinum animates 25 of its 108
fronts, and only with a one-shot gesture (leaders, Elite Four, rival, Frontier Brains). This adds BW2's animated
art for the generic trainer classes that have a clear Unova counterpart. Everyone the story depends on keeps our
art.

## Revert

Two switches, either one is enough:

- `include/battle/battle_trainer_bw2.h`: `#define BW2_TRAINER_FRONTS 1`. Set it to 0 and every class shows its
  Platinum art again (the archive stays in the ROM, unused).
- `tools/bw2_trainers/mapping.py`: `MAPPING`, our class directory -> BW2 sprite. Delete a row to put one class
  back, then rerun `~/.venvs/desmume/bin/python tools/bw2_trainers/build_bw2_trainers.py`. That rewrites
  `res/trainers/bw2/` and `src/battle/battle_trainer_bw2_table.h`. Keep at least one row (the archive is always
  built); to drop everything use the flag.

Platinum's own trainer art (`res/trainers/classes/`) is not touched.

## Mapping

40 classes: Ace Trainer F/M, Artist, Battle Girl, Beauty, Black Belt, Breeder F/M, Clown (-> Harlequin),
Cyclist F/M, Fisherman, Gentleman, Guitarist (-> Musician: BW2's Guitarist is female, the Musician is the man
with the guitar), Hiker, Lady, Lass, Maid, Parasol Lady, Pokefan F/M, Policeman, Psychic F/M, Ranger F/M,
Rich Boy, Roughneck, School Kid F/M, Scientist (-> scientist_m_52), Socialite, Swimmer F/M, Twins, Veteran
(-> veteran_m), Waiter, Waitress, Worker (-> worker_26), Youngster.

Kept on our art:
- story characters: gym leaders, Elite Four, Champion, Galactic boss (Cyrus), commanders and grunts (Team
  Eclipse uses the eclipse_* and galactic_* classes), rival/Garius, the partner trainers (Buck, Cheryl, Marley,
  Mira, Riley), the Frontier Brains, the player in every form;
- Sinnoh classes with no Unova counterpart: Aroma Lady, Bird Keeper, Bug Catcher, Cameraman, Camper,
  Collector, Cowgirl, Dragon Tamer, Idol, Jogger, Ninja Boy (BW2's ninja sprites are empty placeholders),
  Picnicker, Poke Kid, Rancher, Reporter, Ruin Maniac, Sailor, Skier F/M, Tuber F/M, the snow Ace Trainers
  (winter outfits), and the pair classes (Young Couple, Double Team, Belle & Pa, Sis & Bro, Interviewers).

The brief's examples Backpacker, Nurse and Doctor have no Platinum trainer class, so there is nothing to map.

## Format

Platinum's battle trainer front (`trfgra.narc`, 5 files per class) is a VRAM-transfer cell sprite:

- one 80x80 4bpp frame is a cell of six OAMs (64x64, two 16x32, two 32x16, 16x16; 100 tiles), and the NCER's
  `transferData` gives each cell its 3200 bytes of the NCGR. The OBJ VRAM slot is one frame (3200 bytes,
  `vramTransferMaxSize`); the whole NCGR stays in the battle heap and the cell animation DMAs the current frame.
- `front.png` stacks the frames with a 1 px gap: nitrogfx's `-cell` mode reads one cell per frame;
- `front_anim.json`: sequence 0 is the still frame. The 25 animated classes add sequence 1, a one-shot gesture
  that the encounter task plays when the trainer arrives (`battle_display.c` ov16_0225FA70 state 3), waiting
  for it to end. Frame user attributes steer it (ov16_02264650): 1 = white flash, 4095 = done,
  0x1nn = "set sequence nn-1, done".

The BW2 fronts use the same format in a separate archive, `poketool/trgra/trfgra_bw2.narc` (4 files per entry:
NCGR, NCLR, NCER, NANR), so only the battle shows them. The union room, Wi-Fi club, Hall of Fame and the field
encounter effect read `trfgra.narc` directly and keep Platinum's art. `BattleTrainerBW2_NewFront`
(`src/battle/battle_trainer_bw2.c`) is called from `ov16_022643B8` before `sub_02076994` and loads with the same
resource IDs, template and priorities, so the battle's unload code and `RaiseIntroSprites` treat it like any
trainer.

Animation:
- sequence 0: frame 0, held while the trainer slides in (BW2 also holds the trainer's animation until the
  throw);
- sequence 1: BW2's idle loop (NMAR sequence 0), looping. Its frame 0 carries 0x102, so the encounter task
  starts the loop and goes on at once: the intro is not lengthened (BW2 never waits on the trainer either).
  The throw (`ov16_0225FD5C`) restarts sequence 1 as the trainer slides off; it keeps looping.
- the mid-battle and defeat slide-in (`ov16_0225D414`) starts the loop at once through
  `BattleTrainerBW2_StartIdle`, which only acts on fronts whose sequence 1 frame 0 is 0x102 (BW2 plays the
  trainer's animation while it moves in, `btl_client.c`). Platinum's leaders keep their still frame there.

## Converter

`tools/bw2_trainers/mcss_trainer.py` flattens a trainer MCSS (adapted from the gap audit's
`/tmp/bw2gap/sprites/mcss_render.py`): `mcss.bin` is the quad table, `sheet.png` + `normal.pal` the texture,
`animations.nanr` the per-node SRT keys, `multi_cells.nmcr` the hierarchy, `multi_animations.nmar` the idle.
It keeps palette indices, so frames go straight into a 4bpp OBJ with BW2's own 16-colour palette.

`build_bw2_trainers.py`, per class:
- renders every 60 Hz tick of the idle loop, at 1x (BW2 draws trainers flat at 1x; the scale matches
  Platinum's 80x80 art);
- picks one 80x80 window for the whole loop: the feet on the bottom row (Platinum's art stands on row 79); a
  pose taller than 80 loses its top (Harlequin 12 px of hat, Ace Trainer M 9 px at the top of his throw,
  Parasol Lady 4 px of parasol, Pokefan M 2, Psychic F 1); horizontally the MCSS foot point stays at x 40
  unless the loop is wider (Fisherman, 87 px with the rod cast: the window keeps the most pixels and 7 px of rod tip go);
- keeps at most 12 distinct frames: frames are merged into their nearest neighbour, the least visible first
  (pixel difference x ticks shown), until 12 are left. 25 classes needed merging (Ranger M 26 -> 12 is the
  most); the loop timing is kept exactly;
- writes the delays in 60 Hz frames: the battle animates OBJs once per frame (measured: the Youngster's 6-tick
  steps change every 6 frames in the emulator).

## Budgets

| | Platinum art | BW2 front |
|---|---|---|
| OBJ VRAM | 3200 bytes (one frame) | 3200 bytes, unchanged |
| OAMs | 6 | 6 |
| Palettes | 1 | 1 |
| Battle heap while the trainer is on screen | 3.2 KB (still), up to 22.4 KB (7-frame gesture) | 19.2-38.4 KB (6-12 frames) |
| ROM | | +1.47 MB (`trfgra_bw2.narc`, 40 classes) |

The heap is held from the trainer's arrival to the end of its slide-off, and again for a defeat line. The
sprite streams refuse to load below 128 KB free; with two streams the battle has about 368 KB free
(sprite_stream.md), so even a tag battle with two 12-frame trainers keeps well clear. No polygons are added (the
trainers are 2D OBJs).

## Classes without a match

No idle motion was added to the classes that keep Platinum art. An affine "breathing" scale on the trainer OBJ
would need an affine matrix slot and per-OAM repositioning across the six-OAM cell; at the 1-2% scale that
reads as breathing, the 64x64 and 16x32 OAMs shift by a pixel against each other on alternate frames, which
looks like jitter on pixel art, and any scale above 1 clips at the OAM edges (no double-size). Not cheap enough
for what it adds.

## Player back sprite

Unchanged: the player is our character, and Platinum's 9-frame throw (`player_male/back_anim.json`) already
animates with our art. No throw polish was added.

## Sources

BW2 trainer MCSS from pokebw2's checked-in `res/trainers/sprites/front/<class>/` (battle visuals only, per the
asset policy). Nothing from any other game.
