# Build backlog: every code task from the story docs

Mirrored in the "Build Backlog" tab of the story doc.

Suggested order: 1, then 2 (Arc 2 starts with the first totem and the Resonator), then 3 and 4, then the Arc 2 maps and scenes, then Arc 3, then Gen 5 last (it changes the save format).

## 1. Finish Arc 1 (playable through Gym 1)

- Rival name to Garius: the default rival name is "Barry" in res/text/generic_names.json. Check that every rival line uses the rival-name buffer, not a hardcoded name.
- Assistant to Ruth: replace BufferCounterpartName (about 30 uses across 8 script files: Lake Verity, Route 201, Route 202, Sandgem, Jubilife, Canalave Library and two gates) with the fixed name Ruth, and replace the Dawn/Lucas counterpart graphics (picked by player gender) with Ruth's new sprite.
- Arc 1 part 2 scenes (Act 1 tab, scenes 7-14): new VAR_ARC1_PROGRESS states after 8; remove the Route 201 "To be continued" trigger; Garius's mom's line; rival battles on Routes 201 and 203; Rowan takes the Eclipse Shard; Ruth's catching lesson; the Jubilife rally (Saros on the big screen, the Looker cameo, the camera pan to Cyrus); the Oreburgh miners; the mine rift scene with the Hitmonlee silhouette; Roark's lines.

## 2. Core systems

- Remove HMs: no HM items and no field-move menu. Add the Resonator key item; each field obstacle checks the matching Gym badge flag plus that totem's FLAG_TOTEM_*_DEFEATED, then plays a ghost-totem animation. Decide what happens to the HM moves themselves (normal TMs, tutors, or removed).
- Calm Shards: an item (or a counter on the Resonator) for each calmed totem.
- Totem rifts: a rift entrance at each of the 8 totem sites that warps into its Distortion World puzzle map; the existing totem battles at the end; calmed totems catchable in the postgame.
- Totem levels to match the new curve: Spiritomb 30 to 40, Aggron 42 to 45, Mamoswine 44 to 49, Kingdra 50 to 54 (src/totem_battle.c).
- New gym order (Oreburgh, Eterna, Veilstone, Pastoria, Hearthome, Canalave, Snowpoint, Sunyshore): trainer levels along the routes, and anything that counts badges (obedience levels, NPC checks).
- Story states: new progress VARs for Arcs 2 and 3; tag battle with Cyrus (Ravaged Path); double battle with Gardenia (Eclipse Haven); Cyrus as a rival trainer with five battles.

## 3. Trainers (Trainer Changes tab)

- Rebuild the Gym Leader, Elite Four and Champion teams in res/trainers/data/*.json: levels, held items, moves, "power" and AI flags.
- A trainer ability field (or personality-value control), so weather and trap strategies get the right abilities.
- AI tuning for Perish Trap (Fantina) and Baton Pass chains (Aaron).
- Mega Evolution lines for each Mega trainer (the TRMSG_MEGA_EVOLUTION message type already exists).
- Story trainers still to design: Garius, Cyrus, Saros, Kahn, Indra, Eclipse grunts.

## 4. Mega Evolution

- Move the Key Stone and Mega Stones off their Route 206 test spots (res/field/scripts/scripts_unk_0404.s) to the planned locations (Mega Evolution section of the Overarching Story tab).
- New Mega Stones and sprites: Abomasite, Manectite, Heracronite (each has a fallback).
- Mega form abilities: Gengar Shadow Tag, Gyarados Mold Breaker, Scizor Technician, Alakazam Trace, Lucario Adaptability.
- Maylene's trial at the Meteor Shrine, and the starter stones for Darren, Garius and Cyrus.

## 5. Wild Pokemon (Pokemon Route Changes tab)

- Gen 3 additions: encounter edits in res/field/encounters/*.json. Turn the Poke Radar and GBA dual-slot slots into normal encounters.
- Route 218 fairy meadow encounter tables.
- Gen 5: move the alternate forms out of species IDs 494+; resize the Pokedex save bitfields (DEX_SIZE_U32 in src/pokedex.c, NATIONAL_DEX_COUNT); this changes the save layout. Then species data, sprites through tools/gen5_sprites/gen5_stream.py, icons, cries, footprints, and missing abilities and moves.

## 6. Maps (NEEDS DESIGN)

- Distortion World: 8 totem puzzle maps (the Act 1 wall-walk is the template).
- New areas: the clockwork palace; the new Lake Valor southwest of Hearthome with its Route 212 entrance; the Umbral Palace; the Mt. Coronet molten depths (see docs/coronet_1f_lava).
- Redesigns: the Valor Basin (old Lake Valor site); Route 218 meadow; Route 223; the Eclipse Haven interior; the Meteor Shrine; the Lake Verity castle folding effect.
- Visible-change pass toward 40%: rift-scarred totem sites (8); rebuilt Galactic sites (Windworks, Veilstone depot, Fuego foundry, Spear Pillar ruin); Routes 216-217, Solaceon Town, Route 215, Routes 206-207, Sandgem annex, Route 222.

## 7. Checks before building

- Route 210 north: the stock fog comes before the fog-clearing power (Gym 5) in the new order. Remove it or turn it into rift mist.
- Ravaged Path: confirm the main path doesn't need Rock Smash, since its totem is what unlocks it.
- Surf (Gym 4) now comes before fog-clearing (Gym 5), the reverse of stock: check map access.
- Old Chateau: Gengarite needs the tree-cutting power (Gym 2 plus the Vespiquen totem).
- Route 218: with a land bridge, keep the Jubilife-side gate closed until after Gym 6.

## 8. Art and audio

The full list is in `artwork.md` (the "Artwork" tab): four hero cutscenes, character sprites, Pokemon art, maps, objects, UI and audio.


- Ruth (overworld and trainer sprites).
- Team Eclipse: grunt uniforms, Saros, Kahn and Indra (overworld and trainer sprites, new trainer classes).
- Garius: a new design, or Barry's sprite reused.
- Items: Resonator and Calm Shard icons; the three new Mega Stones.
- Optional: Route 218 meadow music, a Team Eclipse battle theme.

