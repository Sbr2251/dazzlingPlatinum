# Pokemon route changes: more Gen 3, and Gen 5 (draft)

Mirrored in the "Pokemon Route Changes" tab of the story doc.

## The rules

- Gen 3 Pokemon are already in the game's data (all 493 species are). Adding more of them only means editing encounter tables.
- Gen 5 is partly in: Deino, Zweilous and Hydreigon (#494-496) and the 21 Arc 1 species (#497-517). The rest of Gen 5 isn't in yet. See "Built so far" below.
- Gen 5 sprites are covered: tools/gen5_sprites/gen5_stream.py already builds the game's battle sprites from the PokeAPI sprites repository's Black/White animated GIFs, which include every Gen 5 species (#494-649), with front, back, shiny and female versions. The same tool can import them, and it also writes the classic 80x80 sprites used outside battle.
- What Gen 5 still costs: (1) Engine room. The save file's Pokedex block has seen/caught bitfields sized for 493 species, and Platinum stores alternate forms (Deoxys, Wormadam, Giratina-Origin, Shaymin-Sky, Rotom) in the species IDs right after #493. Adding #494+ means moving those forms and resizing the Pokedex save data, which breaks old saves. (2) Data: base stats, learnsets, evolutions and Pokedex entries (available from PokeAPI or Showdown data). (3) Icons, cries and footprints. (4) Some Gen 5 abilities and moves need adding or substituting. Because of (1), it's worth doing all of Gen 5's IDs in one pass, even if only phase 1 gets placed in the wild at first.
- Add, don't replace: Sinnoh's own Pokemon stay. New species mostly take swarm, day/night, Poke Radar and GBA dual-slot slots, which players can't otherwise use in this hack.
- Placement follows the story and the new maps where it can: grief Pokemon in the memorial town, clockwork Pokemon at the Dialga palace, meteor Pokemon at the Meteor Shrine.
- Levels follow the new gym order.

## Gen 5, phase 1: tied to the story and the new maps (27 lines)

| Gen 5 line | Where |
|---|---|
| Roggenrola | Oreburgh Mine (built), Iron Island |
| Drilbur | Oreburgh Mine (built), Iron Island |
| Timburr | Oreburgh Mine (built), Routes 206-207 |
| Woobat | Ravaged Path, Mt. Coronet |
| Sewaddle | Route 203 (built), Eterna Forest |
| Venipede | Eterna Forest |
| Cottonee | Route 204, Route 218 |
| Throh and Sawk | Route 211 |
| Mienfoo | Route 210 |
| Sigilyph | Celestic Town ruins |
| Yamask | Solaceon Town |
| Litwick | Old Chateau, Lost Tower |
| Tympole | Route 215, Great Marsh |
| Elgyem | Meteor Shrine, Veilstone |
| Sandile | Valor Basin, Route 214 |
| Scraggy | Route 214 |
| Pawniard | Route 214 |
| Stunfisk | Great Marsh |
| Frillish | Routes 213, 222, 223 |
| Klink | The clockwork palace, Fuego Ironworks |
| Cubchoo | Routes 216-217 |
| Vanillite | Routes 216-217 |
| Tynamo | Route 222 |
| Golett | Umbral Palace |
| Axew | Victory Road |
| Deino | Victory Road (rare) |
| Larvesta | Mt. Coronet molten depths (rare) |

## Gen 5, phase 2: nice to have (23 lines)

Patrat, Lillipup, Pidove, Purrloin, Blitzle, Emolga, Ducklett, Foongus, Minccino, Gothita, Trubbish, Karrablast, Shelmet, Alomomola, Joltik, Heatmor, Durant, Druddigon, Cryogonal, Darumaka, Petilil, Rufflet, Vullaby. Patrat, Lillipup, Pidove and Purrloin are already in, on Routes 201-202.

## Arc 1: start to Gym 1 (built)

| Area | Theme | Add: Gen 3 | Add: Gen 5, phase 1 | Add: Gen 5, phase 2 | Notes |
|---|---|---|---|---|---|
| Route 201 | Start of the game | Zigzagoon, Wurmple | - | Patrat, Lillipup | **Built** |
| Route 202 | First catches | Poochyena (night), Taillow | - | Pidove, Purrloin (night) | **Built** |
| Route 203 | On the way to Oreburgh | Ralts (rare), Whismur | Sewaddle | - | **Built** |
| Oreburgh Gate and Oreburgh Mine | Mines; Act 1 ends here | Aron, Nosepass, Makuhita | Roggenrola, Drilbur, Timburr | - | **Built**, plus the new Mine side tunnel |
| Lake Verity | The castle lake | Surskit, Lotad (Surf, later) | - | Ducklett (Surf, later) | **Built** (Surskit, Lotad). Ducklett not added. |

### As built: real species and rates (res/field/encounters)

Grass and cave rates use the stock slot odds (20, 20, 10, 10, 10, 10, 5, 5, 4, 4, 1, 1). The day column is the daytime table; the time-of-day slots are the two 10% slots.

| Area | Rate | Day | Morning, night and other |
|---|---|---|---|
| Route 201 | Grass 30 | Starly 30%, Bidoof 30%, Zigzagoon 14%, Wurmple 14%, Patrat 6%, Lillipup 6% (Lv 2-3) | Morning: Kricketot 10% in place of 10% Bidoof. Night: Bidoof 30%, Starly 20%, Kricketot 10%. |
| Route 202 | Grass 30 | Bidoof 31%, Shinx 30%, Taillow 15%, Starly 11%, Pidove 9%, Kricketot 4% (Lv 2-4) | Morning: Bidoof 21%, Kricketot 14%. Night: Purrloin 10% and Poochyena 10% take the day/night slots (Bidoof 21%, Starly 1%). |
| Route 203 | Grass 30 | Starly 30%, Shinx 20%, Whismur 15%, Bidoof 11%, Abra 10%, Sewaddle 9%, Ralts 5% (Lv 4-7) | Morning: Kricketot 10% in place of 10% Bidoof. Night: Zubat 10% and Kricketot 10% in place of 10% Starly and 10% Bidoof. Surf: Psyduck 90%, Golduck 10%. |
| Oreburgh Gate 1F | Cave 10 | Zubat 30%, Psyduck 30%, Geodude 15%, Makuhita 10%, Timburr 5%, Aron 4%, Nosepass 4%, Drilbur 1%, Roggenrola 1% (Lv 5-7) | Same at every time of day. B1F (behind field obstacles): the same mix at Lv 6-10, plus Golbat 4%. |
| Oreburgh Mine B1F | Cave 10 | Zubat 21%, Geodude 20%, Roggenrola 20%, Aron 10%, Nosepass 10%, Onix 5%, Timburr 5%, Drilbur 5%, Makuhita 4% (Lv 5-8) | Same at every time of day. |
| Oreburgh Mine B2F | Cave 10 | The same mix as B1F, one level higher (Lv 6-9) | Same at every time of day. |
| Oreburgh Mine side tunnel (new map) | Cave 10 | Roggenrola 35%, Drilbur 34%, Timburr 21%, Geodude 5%, Zubat 5% (Lv 7-10) | Gen 5 is 90% of encounters. Swarm: Drilbur. Poke Radar: Timburr, Drilbur, Roggenrola. Opened by the Oreburgh Machop quest; stays open. |
| Lake Verity | Grass 30 | Bidoof 50%, Starly 35%, Surskit 15% (Lv 2-4) | Surf: Psyduck 60%, Lotad 30% (Lv 25), Golduck 10%. |

### Built so far: Gen 5 and the Sinnoh Pokedex (2026-10-10)

- **21 Gen 5 species are in, as #497-517:** Patrat, Watchog, Lillipup, Herdier, Stoutland, Purrloin, Liepard, Pidove, Tranquill, Unfezant, Roggenrola, Boldore, Gigalith, Drilbur, Excadrill, Timburr, Gurdurr, Conkeldurr, Sewaddle, Swadloon and Leavanny, after Deino, Zweilous and Hydreigon (#494-496). Each has Gen 5 stats, B/W learnsets and Pokedex entries, B/W battle sprites, icons, footprints and its real B/W cry (no cry was substituted). Existing saves still load: the Pokedex save layout didn't move.
- **Move substitutions** (tools/gen5_sprites/gen5_species_report.json): After You to Helping Hand, Work Up to Howl, Retaliate to Facade, Hone Claws to Sharpen, Autotomize to Rock Polish, Smack Down to Rock Throw, Heavy Slam to Gyro Ball, Drill Run to Drill Peck, Chip Away to Headbutt, Struggle Bug to Silver Wind, Entrainment to Worry Seed. Dropped with no stand-in: Foul Play (Purrloin egg move), Bestow (Pidove egg move), Wide Guard (Timburr egg move).
- **Ability substitutions:** Sand Rush to Sand Veil (Herdier, Stoutland, Drilbur, Excadrill), Big Pecks to Keen Eye (the Pidove line), Sheer Force to Iron Fist (the Timburr line). 18 of the 21 species lose their hidden ability.
- **Evolution change:** Boldore and Gurdurr evolve at Lv 37 instead of by trade.
- **The Sinnoh Pokedex now has 250 entries** (stock 210). The new Gen 3 and Gen 5 lines are slotted in where the player first meets them: after Bibarel (Route 201), Luxray (Route 202), Alakazam (Route 203), Steelix (Oreburgh Gate and Mine) and Golduck (Lake Verity). Every number after Bibarel moved.

## Arc 2: Gyms 2 to 5

| Area | Theme | Add: Gen 3 | Add: Gen 5, phase 1 | Add: Gen 5, phase 2 | Notes |
|---|---|---|---|---|---|
| Route 204 and Ravaged Path | First totem (Hitmonlee) | Shroomish, Whismur (Ravaged Path) | Woobat (Ravaged Path), Cottonee | - | - |
| Route 205, Floaroma, Valley Windworks | Flowers and wind | Electrike, Plusle and Minun (Windworks), Lotad (water) | - | Blitzle, Emolga, Ducklett | - |
| Eterna Forest | Second totem (Vespiquen) | Seedot, Shroomish, Nincada | Sewaddle, Venipede | Foongus, Karrablast (night) | - |
| Old Chateau | Haunted mansion | Shuppet | Litwick (rare) | - | Gengarite is hidden here. |
| Route 211 and the Mt. Coronet crossing | Mountain road to Celestic | Meditite, Makuhita, Numel | Throh and Sawk, Woobat, Roggenrola | - | - |
| Celestic Town | Ruins and the elder's shrine | Baltoy | Sigilyph (an ancient guardian, at the ruins) | - | - |
| Route 210 | Fog and cliffs | Swablu, Absol (rare: it senses disaster, and the rifts) | Mienfoo | - | Remove the stock fog on the north half, or make it rift mist (gym order check). |
| Solaceon Town and Route 209 | The town of Eclipse's believers, with the memorial wall | Duskull | Yamask (it carries the face of who it used to be) | Minccino, Gothita | Yamask in a town full of grief is deliberate. |
| Lost Tower | Graves; the Spiritomb totem | Duskull, Shuppet | Litwick | - | - |
| Route 215 | Flooded lowland, Eclipse truck route | Lotad, Surskit, Castform (rain) | Tympole | Shelmet | - |
| Veilstone City and the Meteor Shrine | The fallen star | Lunatone (night), Solrock (day), Beldum (very rare, postgame) | Elgyem | - | Meteor Pokemon at the meteor shrine. |
| Route 214 | Skarmory totem; violet sky over the rift | Zangoose (day), Seviper (night), Absol (rare, near the rift) | Sandile, Scraggy, Pawniard | - | - |
| Valor Lakefront and the Valor Basin | The dry lakebed | Trapinch, Cacnea, Barboach (fishing in the puddles) | Sandile | Darumaka | - |
| Route 213 and Pastoria | Beach; the Lapras totem | Wingull, Corphish, Carvanha (fishing), Clamperl (Surf), Wailmer (Surf) | Frillish (Surf) | Alomomola (Surf) | - |
| Great Marsh | Swamp | Tropius, Kecleon, Lotad | Stunfisk, Tympole | Karrablast, Shelmet | - |
| Route 212 and the new Lake Valor | Rain road, and the clockwork palace | Kecleon (Route 212 south), Baltoy (palace grounds) | Klink (palace grounds) | Petilil, Cottonee | - |
| Route 208 and Hearthome | - | Swablu | - | Minccino | - |

## Arc 3: Gym 6 to the League

| Area | Theme | Add: Gen 3 | Add: Gen 5, phase 1 | Add: Gen 5, phase 2 | Notes |
|---|---|---|---|---|---|
| Canalave City and Route 218 | The fairy route: a serene meadow (see the design brief below) | Day: Kirlia, Marill and Azumarill, Snubbull and Granbull, Mawile, Jigglypuff. Night: Clefairy and Clefable (by the fairy ring), Mr. Mime. Rare: Togetic, Gardevoir | Cottonee (needs Fairy typing when added) | - | All the Gen 3-and-earlier species listed are already Fairy type in the game. Levels about 38-44 (Arc 3, around Gym 6). |
| Iron Island | Aggron totem; deep tunnels | Aron, Lairon | Drilbur, Roggenrola | Durant | Lucarionite comes from Riley here. |
| Fuego Ironworks | Eclipse's shard-machine foundry | Magnemite | Klink | Joltik, Trubbish | Scizorite is hidden here. |
| Routes 206 and 207 | Eclipse's supply road into Mt. Coronet | Gulpin, Numel | Timburr | Trubbish | - |
| Routes 216 and 217, Acuity Lakefront, Snowpoint | The mountain pass, Teo's memorial; the Mamoswine totem | Snorunt, Spheal | Cubchoo, Vanillite | Cryogonal (night, rare) | - |
| Mt. Coronet molten depths | The race for Giratina | Numel, Torkoal, Slugma | Larvesta (rare) | Heatmor, Durant (a predator and its prey, together) | - |
| Umbral Palace | Half in the Distortion World | Sableye | Golett | - | - |
| Route 222 | Coast lit violet by the Route 223 rift | Electrike and Manectric, Wingull | Tynamo, Frillish | Ducklett | - |
| Route 223 | Kingdra totem; the final battle | Wailmer and Wailord, Relicanth (rare, Super Rod) | Frillish | Alomomola | - |
| Victory Road | The last cave | Bagon (rare) | Axew, Deino (rare) | Druddigon | - |

## Design brief: Route 218, the serene fairy meadow

- Today Route 218 is a short sea crossing between Jubilife and Canalave with a couple of small land strips, so it needs a real redesign to be a serene field. NEEDS DESIGN.
- Layout: the strait becomes a wide flower meadow on a land bridge. Low hills of tall pink and white flowers, a winding stone path, a clear stream with stepping stones, and a small pond. Calm and open, a deliberate breather after the dark Arc 2 and before the Palkia chase.
- A fairy ring at the center: a circle of white flowers and stones. At night, Clefairy gather there to dance (an encounter-rich spot, and a nod to Mt. Moon).
- The Mawile clearing: a quiet glade where Mawile live. A callback to the Act 1 Mawile, the first shard victim. An NPC can mention how gentle they are when nobody hurts them.
- Music and mood: a soft, gentle route theme. Petals drifting (weather effect), no trainers in the center, a few relaxed ones along the edges.
- Story placement: Arc 3, scene 3.6. You cross it on the way to Lake Verity, right before the castle folds in on itself. The peace of the meadow makes the next scene hit harder.
- Access: with a land bridge, the route no longer needs Surf. That's fine in the new order, because the story first sends you here after Gym 6 from the Canalave side. Keep the Jubilife-side gate closed until then (for example, a gatekeeper: the meadow's flowers are blooming and the path is closed).

## Postgame

| Area | Theme | Add: Gen 3 | Add: Gen 5, phase 1 | Add: Gen 5, phase 2 | Notes |
|---|---|---|---|---|---|
| Postgame routes (224-230), Stark Mountain, Battle Zone | After the credits | Absol, Relicanth, Zangoose and Seviper, Tropius, Bagon and Beldum (rare) | - | Rufflet and Vullaby (Route 228 desert), Druddigon, Heatmor | - |
| Postgame gift | - | Rowan gives one of the Gen 3 starters (Treecko, Torchic or Mudkip), already in the game's data | - | - | Gen 5 starters could follow if Gen 5 is added. |

