# Artwork: everything that needs to be drawn, modeled or animated (draft)

Mirrored in the "Artwork" tab of the story doc.

- Goal: Black/White-quality cutscenes for the story's biggest moments: a moving camera, legendaries bursting through portals, screen-filling effects.
- How: the same technique as the title screen's pre-rendered Giratina loop (already in the game). Render the hero shots offline in 3D, stream the frames on the DS, and cut back to the in-engine map, camera and particle effects for continuity. Short in-engine moments use the existing tools: camera moves, screen shake, flashes, fades and particle effects.
- DS limits to design around: two 256x192 screens, and 16-color palettes for sprites. Use both screens in cutscenes: the action on top, a reaction or a second angle on the bottom.

## Cutscenes

Four hero cutscenes, one for each time the creation trio bursts into the story, plus four smaller in-engine moments.

### Cutscene 1: Cast Out (opening, Act 1)

**When:** Right after Rowan's intro, replacing the current flashback. **Why:** Shows the player who Cyrus is and that Giratina threw him out. It's the core dramatic irony of the whole game.

**Shots:**

1. The Distortion World: floating islands turning in a void. The camera drifts toward the Giratina room.
2. The end of Platinum: Cynthia, the hero (a Lucas NPC) and Cyrus. Cyrus turns and walks away.
3. The ground under Cyrus tears open. Giratina rises out of the dark, enormous, filling the top screen; the bottom screen shows Cyrus looking up.
4. Giratina roars. A rift splits the sky. Giratina hurls Cyrus through it (white flash, screen shake).
5. Fall sequence: Cyrus tumbling through a tunnel of light and shadow.
6. Lake Verity at dusk, from high above: the castle, the lake. A portal bursts open over the castle terrace, and Cyrus crashes down.
7. Cut to the in-engine terrace: Cyrus lies still, then gets up. ("...Where am I?")

**Effects:** Distortion World void and floating islands; the rift tear; Giratina's emergence (shadow tendrils); the portal burst over the castle.

**Audio:** Silence at first, then Giratina's cry, then a low rumble building into the portal burst.

**Technique:** Pre-rendered: shots 1 and 3-6. In-engine: shot 2 (the existing flashback scene) and shot 7. **Length:** About 40-50 seconds.

**Assets:** Giratina 3D model and animation for rendering; Distortion World environment; Lake Verity castle exterior (render from the existing map); fall-tunnel effect.

### Cutscene 2: Dialga Awakens (the clockwork palace, Arc 3)

**When:** Scene 3.3: Saros's machine finishes in the clock chamber. **Why:** The first legendary falls. Shows how Darren loses: time stops.

**Shots:**

1. The clock-face ceiling. Every gear in the chamber speeds up until the ticking becomes a roar.
2. The giant clock face cracks down the middle, and blue light pours through.
3. Dialga bursts through the clock face. Shattered gears and brass rain down around it.
4. Shard chains snap around Dialga from Saros's machine (violet against Dialga's blue).
5. Dialga screams. A shockwave of grey sweeps across both screens: color drains, everything freezes mid-motion.
6. Frozen frame held for a beat, with falling gears hanging in the air. Saros and Garius walk out through the frozen room.
7. Color snaps back. The chamber is empty.

**Effects:** Gears spinning up; the clock face shattering; Dialga's blue light; violet shard chains; the grey time-freeze wave (a palette fade to greyscale over a frozen frame).

**Audio:** The ticking speeding up into Dialga's cry, then total silence during the freeze, then sound rushing back.

**Technique:** Pre-rendered: shots 2-4. In-engine: shots 1, 5-7 (the freeze is a greyscale palette effect over the paused map). **Length:** About 30-40 seconds.

**Assets:** Dialga 3D model and animation; the clockwork palace interior (from the new map); shard-chain effect.

### Cutscene 3: Palkia Folds the Castle (Lake Verity, Arc 3)

**When:** Scene 3.6: Kahn's machine on the terrace where Act 1 began. **Why:** The second legendary falls, at the place where the story started.

**Shots:**

1. The terrace from Act 1, same angle as the opening's crash. Kahn's machine hums.
2. Space above the castle ripples like water. A portal opens: the same spot as the Act 1 portal.
3. Palkia bursts through it, wings spread, pink light flooding the lake.
4. Shard chains wrap around Palkia.
5. Palkia roars, and the castle folds: towers bend inward, the terrace tilts, the sky wraps around. Both screens show the fold from two angles.
6. Everything snaps flat. Darren is standing at the castle gate, alone.

**Effects:** Space rippling; the portal (matching the Act 1 portal); Palkia's pink light; shard chains; the space-fold distortion (wavy screen warp, then a hard cut).

**Audio:** A deep hum, Palkia's cry, a sound like a huge sheet of glass bending, then quiet lake ambience.

**Technique:** Pre-rendered: shots 2-3 and 5. In-engine: shots 1, 4 and 6. **Length:** About 30-40 seconds.

**Assets:** Palkia 3D model and animation; the Lake Verity castle (render from the existing map); fold distortion.

### Cutscene 4: Giratina Rises (the Umbral Palace, Arc 3)

**When:** Scene 3.11: Indra raises her shards in the innermost hall. **Why:** The climax of the race, and Indra's closure.

**Shots:**

1. The innermost hall, towers hanging upside down from the cavern roof.
2. The floor tears open into the Distortion World. Gravity flips: the camera rolls 180 degrees.
3. Giratina rises out of the dark, shadow tendrils first, in its Origin form.
4. It looks at Indra's shards and doesn't move toward them. The shards dim.
5. Giratina's shadow spreads across the floor. Teo appears in it, smiling.
6. Teo fades into light. Indra drops the shards; they go dark on the floor.

**Effects:** The floor tearing into the Distortion World; the gravity flip; shadow tendrils; Teo's ghostly fade.

**Audio:** Giratina's cry, then a quiet, gentle theme under Teo's lines.

**Technique:** Pre-rendered: shots 2-3. In-engine: shots 1 and 4-6 (Teo is an overworld sprite with a translucent, fading palette). **Length:** About 40 seconds, plus dialogue.

**Assets:** Giratina Origin form 3D model and animation; the Umbral Palace (from the new map); Teo's ghost sprite.

### Smaller in-engine moments

- **The shards turn (Spear Pillar, scene 3.13):** Shards blaze around Saros and Kahn, then pour back into them. They fall. Garius walks down the steps. In-engine: flashes, a palette pulse, Dialga and Palkia's overworld sprites in chains.
- **Freedom at the waterfall (Route 223, scene 3.17):** The shard chains shatter. Dialga and Palkia hang free for a moment, look at Darren, and vanish. The split sky seals shut. In-engine with particles, with a short pre-rendered sky-closing shot if there's budget.
- **The first Mega Evolution (Meteor Shrine, scene 2.17b):** The meteorites glow, and Maylene's Lucario Mega Evolves in front of them. In-engine: the existing Mega Evolution effect, plus a glow on the meteorites.
- **The castle portal opens (Act 1 TV, BREAKING NEWS):** Already partly built. Upgrade the TV report with a short shot of the portal over the castle.

## Character sprites

### The three new main characters

| Character | Who | Sprites needed |
|---|---|---|
| Darren, boy | The protagonist (boy option). | Overworld: walk, run, bike, surf, fishing, Resonator-use pose (replaces the HM pose). Battle: back sprite with the throw animation. Trainer card, and the full-body sprite for Rowan's intro. |
| Darren, girl | The protagonist (girl option). | The same set as the boy. |
| Garius | The rival. | Overworld: walk and run. Trainer battle sprite. Optional: a second look after the reveal in Arc 3 (darker, with Eclipse colors). |
| Ruth | Rowan's assistant, replacing Dawn and Lucas. | Overworld: walk, run, and a pose holding her readings device. Battle back sprite with the throw animation, for the catching lesson. |

Darren needs two full sets, because the player can pick a girl or a boy.

### Other characters

- **Team Eclipse grunts (male and female):** Overworld and trainer battle sprites; a new trainer class. Uniform design: the Eclipse look (dark, with a violet eclipse ring).
- **Saros, Kahn, Indra:** Overworld and trainer battle sprites; new trainer classes. Indra also needs a version without her coat for scene 3.14.
- **Teo:** Ghostly overworld sprite with a translucent, fading palette (scene 3.11).
- **Looker's disguises (optional):** Overworld variants: janitor, newspaper-and-sunglasses, snowman.
- **The Meteor Shrine keeper (optional):** If Maylene's family elder appears on screen.
- **Already in the game:** Cyrus (overworld and trainer), Looker, Rowan, the Gym Leaders, Elite Four and Cynthia, Riley.

## Pokemon art

- Gen 5 battle sprites: covered by tools/gen5_sprites/gen5_stream.py (PokeAPI Black/White animated GIFs).
- Gen 5 party icons and footprints: still needed.
- Mega sprites for the three new stones: Mega Abomasnow, Mega Manectric, Mega Heracross (if built; each has a fallback).
- Totem ghost silhouettes for the Resonator: 8 short field animations (a ghostly Hitmonlee kicks the rock, a ghostly Lapras carries you, and so on).
- Already in the game: the custom Megas (including the three Sinnoh starters), the totem overworld sprites, the Gen 5-style animated sprites for #1-493, the Mawile sprite.

## Map artwork

- **New areas:** The clockwork palace (interior and exterior); the new Lake Valor southwest of Hearthome, with the Route 212 entrance; the Umbral Palace; the Mt. Coronet molten depths (art direction already in docs/coronet_1f_lava); 8 Distortion World totem puzzle maps.
- **Redesigns:** The Valor Basin (dry lakebed, the Valor Lakefront memorial plaque); the Route 218 fairy meadow (flowers, fairy ring, Mawile clearing, stream, pond); Route 223 (the final-battle summit at the top of the waterfall); the Eclipse Haven interior; the Meteor Shrine.
- **Visible-change pass (toward 40%):** Rift-scarred versions of the 8 totem sites; the rebuilt Galactic sites (Windworks, Veilstone depot, Fuego foundry, Spear Pillar ruin); Routes 216-217 (mountain pass, Teo's memorial ridge, Indra's camp); Solaceon Town (Eclipse banners, the memorial wall of photos); Route 215 (flooded lowland, boardwalks, truck ruts); Routes 206-207 (supply road, Coronet staging yard); the Sandgem lab annex; Route 222 (violet coast).
- **Shared tilesets that save work:** One "rift scar" tileset (warped ground, violet cracks) reused at every totem site; one Eclipse-industrial tileset (crates, trucks, machines, banners) reused at the Haven, the depot, the foundry and the supply road.
- **Already done:** The Lake Verity castle, and the Act 1 Distortion World wall-walk map.

## Objects and effects

- The rift portal: an animated overworld object for each totem site (reuse and recolor the Act 1 castle portal).
- Props: torture frames, shard machines, shard veins (glowing crystals), clock gears, meteorites, the memorial wall and plaque, Eclipse banners and flyers, trucks and crates.
- Weather and palette effects: drifting petals (Route 218), a violet sky over rift sites, heat shimmer in the molten depths, the time-freeze greyscale (Dialga), the space-fold warp (Palkia).

## UI and 2D art

- Item icons: the Resonator, Calm Shards, and the three new Mega Stones (the Eclipse Shard and Mega Stone icons already exist).
- Town Map and Fly map: Lake Valor's new spot, the Valor Basin, the Route 218 meadow, the Umbral Palace and other new places.
- Battle backgrounds: the Distortion World, the clockwork palace, the Umbral Palace, the molten depths, the Route 218 meadow, and the Route 223 summit.
- The TV BREAKING NEWS banner (Act 1).
- The Team Eclipse logo (banners, flyers, uniforms).
- Credits and the end screen.
- Already done: the title screen (pre-rendered Giratina loop and Distortion World top screen), the main menu card picker.

## Audio

- Not art, listed so it isn't forgotten: a Route 218 meadow theme; Team Eclipse battle and leader themes; cutscene music and stingers for the four hero cutscenes; Gen 5 cries.

