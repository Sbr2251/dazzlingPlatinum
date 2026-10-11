# Trainer changes: Gym Leaders, Elite Four and Champion (draft)

Mirrored in the "Trainer Changes" tab of the story doc.

## The rules

- Every Gym Leader from Maylene (Gym 3) on Mega Evolves their ace, and so does every Elite Four member and the Champion. The AI already triggers Mega Evolution on its own, and each trainer gets a Mega Evolution line (the TRMSG_MEGA_EVOLUTION message type already exists).
- Stronger in three ways: a level bump of 3 to 5 over stock, real held items, and higher "power" (IVs). Use about 150 for the early Gyms, 200 for the late Gyms, 230 for the Elite Four and 255 (perfect IVs) for Cynthia. Stock is 50.
- Every team has a strategy, reflected in its moves, items and AI flags (WEATHER, SETUP_FIRST_TURN, BATON_PASS, CHECK_HP and so on). The Elite Four and Champion each use a strategy that was famous in real Pokemon competitive play.
- Everything uses Gen 4 moves and abilities that are already in the engine, except the three new Mega Stones noted below.

Gym order: 1 Oreburgh, 2 Eterna, 3 Veilstone, 4 Pastoria, 5 Hearthome, 6 Canalave, 7 Snowpoint, 8 Sunyshore.

## Gym 1: Roark (Oreburgh)

**Built (2026-10-10).** The game matches this table exactly: res/trainers/data/leader_roark.json has the same levels, items, moves and AI flags, power 150 on all three, and 2 Potions in Roark's bag. Mold Breaker is Cranidos's only ability, so no ability control was needed.

**Levels:** 13-16. **Mega:** None (before the Key Stone).

**Strategy:** Hazards and speed control. Geodude opens with Stealth Rock behind a Focus Sash, Onix slows you with Rock Tomb, and Cranidos hits hard once your switches are chipped.

**Where it comes from:** Stealth Rock leads were the defining opener of Gen 4 competitive singles (Smogon Gen 4 OU).

| Pokemon | Lv | Item | Moves | Role |
|---|---|---|---|---|
| Geodude | 13 | Focus Sash | Stealth Rock, Rock Throw, Magnitude, Defense Curl | Hazard lead; the Sash guarantees Stealth Rock goes up |
| Onix | 14 | Oran Berry | Rock Tomb, Screech, Rock Throw, Bind | Speed control: Rock Tomb drops your Speed |
| Cranidos | 16 | Sitrus Berry | Headbutt, Pursuit, Zen Headbutt, Leer | Ace (Mold Breaker); Pursuit punishes switching |

**AI flags:** BASIC, EVAL_ATTACK, EXPERT, CHECK_HP.

## Arc 1 route trainers (built)

The 14 trainers between Route 202 and Roark were rebuilt around the new Gen 3 and Gen 5 Pokemon, on a curve that climbs into Roark's 13-16. Every move is a level-up move the Pokemon knows at that level. Source: res/trainers/data. Garius (story battles) and Veteran Grant in Oreburgh Gate B1F are unchanged.

| Trainer | Where | Team (level) | AI, power |
|---|---|---|---|
| Youngster Tristan | Route 202 | Patrat 4, Zigzagoon 5 | BASIC; power 0 |
| Youngster Logan | Route 202 | Pidove 5, Taillow 6 | BASIC; power 0 |
| Lass Natalie | Route 202 | Wurmple 4, Lillipup 5 | BASIC+EXPERT; power 0 |
| Youngster Michael | Route 203 | Purrloin 6, Poochyena 7 | BASIC; power 20 |
| Youngster Sebastian | Route 203 | Timburr 7, Makuhita 8 | BASIC; power 20 |
| Lass Kaitlin | Route 203 | Budew 6, Sewaddle 6, Ralts 7 | BASIC+EXPERT; power 20 |
| Lass Madeline | Route 203 | Whismur 7, Psyduck 8 | BASIC+EXPERT; power 20 |
| Youngster Dallas | Route 203 | Taillow 7, Shinx 8 | BASIC; power 20 |
| Camper Curtis | Oreburgh Gate | Shinx 9, Aron 10 | BASIC+EVAL_ATTACK+EXPERT; power 30 |
| Picnicker Diana | Oreburgh Gate | Zigzagoon 9, Beautifly 10 | BASIC+EVAL_ATTACK+EXPERT; power 30 |
| Worker Colin | Oreburgh Mine B2F | Roggenrola 10, Makuhita 11 | BASIC; power 30 |
| Worker Mason | Oreburgh Mine B2F | Drilbur 10, Nosepass 11 | BASIC; power 30 |
| Youngster Jonathon | Oreburgh Gym | Roggenrola 11, Nosepass 12 | BASIC+EVAL_ATTACK; power 50 |
| Youngster Darius | Oreburgh Gym | Onix 11, Aron 12 | BASIC+EVAL_ATTACK; power 50 |

## Gym 2: Gardenia (Eterna)

**Levels:** 21-25. **Mega:** None (before the Key Stone).

**Strategy:** Sun. Cherrim sets Sunny Day with a Heat Rock, then Chlorophyll Pokemon outspeed and fire off one-turn Solar Beams while Roserade spreads status.

**Where it comes from:** Sun teams with Chlorophyll sweepers (VGC 2015's Ninetales and Venusaur sun, and Gen 4 Sunny Day teams).

| Pokemon | Lv | Item | Moves | Role |
|---|---|---|---|---|
| Cherrim | 21 | Heat Rock | Sunny Day, Magical Leaf, Leech Seed, Growth | Sun setter (Flower Gift) |
| Exeggcute | 22 | Miracle Seed | Solar Beam, Hypnosis, Confusion, Leech Seed | Chlorophyll sweeper |
| Tangela | 23 | Sitrus Berry | Solar Beam, Stun Spore, Ancient Power, Mega Drain | Chlorophyll sweeper |
| Roserade | 25 | Sitrus Berry | Magical Leaf, Stun Spore, Poison Jab, Toxic Spikes | Ace; status spreader |

**AI flags:** BASIC, EVAL_ATTACK, EXPERT, WEATHER, SETUP_FIRST_TURN.

## Gym 3: Maylene (Veilstone)

**Levels:** 27-31. **Mega:** Mega Lucario.

**Strategy:** Setup and priority. Hitmontop leads with Intimidate and Fake Out, Machoke burns itself with a Flame Orb to power up Guts and Facade, and Mega Lucario sets Swords Dance and cleans up with priority.

**Where it comes from:** Swords Dance plus priority (Gen 4 OU Lucario), and Guts with a Flame Orb (a Gen 4 standard).

| Pokemon | Lv | Item | Moves | Role |
|---|---|---|---|---|
| Hitmontop | 27 | Sitrus Berry | Fake Out, Rapid Spin, Mach Punch, Rock Slide | Lead (Intimidate); clears hazards |
| Meditite | 28 | Focus Sash | Bullet Punch, Force Palm, Detect, Confusion | Priority attacker (Pure Power) |
| Machoke | 29 | Flame Orb | Facade, Karate Chop, Revenge, Rock Slide | Guts wallbreaker |
| Lucario | 31 | Lucarionite | Swords Dance, Extreme Speed, Drain Punch, Bullet Punch | Mega ace: set up, then priority |

**AI flags:** BASIC, EVAL_ATTACK, EXPERT, SETUP_FIRST_TURN, CHECK_HP.

**Mega Evolution line:** "Lucario! Let's show them what a bond looks like!"

## Gym 4: Crasher Wake (Pastoria)

**Levels:** 31-35. **Mega:** Mega Gyarados.

**Strategy:** Rain. Pelipper sets Rain Dance with a Damp Rock, Swift Swim Pokemon double their Speed, Quagsire walls Electric moves, and Mega Gyarados Dragon Dances behind it.

**Where it comes from:** Rain Dance with Swift Swim sweepers (Gen 4 OU rain, and the Kingdra and Ludicolo rain teams of VGC 2010 and 2011).

| Pokemon | Lv | Item | Moves | Role |
|---|---|---|---|---|
| Pelipper | 31 | Damp Rock | Rain Dance, Water Pulse, Wing Attack, Protect | Rain setter |
| Floatzel | 32 | Mystic Water | Aqua Jet, Waterfall, Crunch, Bulk Up | Swift Swim sweeper |
| Ludicolo | 33 | Sitrus Berry | Surf, Giga Drain, Ice Beam, Fake Out | Swift Swim sweeper |
| Quagsire | 33 | Leftovers | Earthquake, Waterfall, Yawn, Amnesia | Electric check (Water Absorb) |
| Gyarados | 35 | Gyaradosite | Dragon Dance, Waterfall, Ice Fang, Earthquake | Mega ace (Mold Breaker) |

**AI flags:** BASIC, EVAL_ATTACK, EXPERT, WEATHER, SETUP_FIRST_TURN.

**Mega Evolution line:** "WHAAAH! Ride the storm, Gyarados! MEGA EVOLVE!"

## Gym 5: Fantina (Hearthome)

**Levels:** 35-39. **Mega:** Mega Gengar.

**Strategy:** Perish Trap. Mega Gengar's Shadow Tag (and Mismagius's Mean Look) stops you switching out. Perish Song starts a three-turn countdown, and Protect stalls until your Pokemon faints. Drifblim and Dusknoir burn and stall.

**Where it comes from:** Mega Gengar's Perish Trap, one of the most famous strategies of VGC 2015.

| Pokemon | Lv | Item | Moves | Role |
|---|---|---|---|---|
| Drifblim | 35 | Sitrus Berry | Will-O-Wisp, Shadow Ball, Baton Pass, Minimize | Lead (Unburden); burns and passes evasion |
| Dusknoir | 36 | Leftovers | Will-O-Wisp, Pain Split, Shadow Punch, Protect | Wall |
| Mismagius | 37 | Leftovers | Mean Look, Perish Song, Protect, Shadow Ball | Second Perish trapper |
| Banette | 37 | Focus Sash | Shadow Claw, Will-O-Wisp, Sucker Punch, Destiny Bond | Revenge killer |
| Gengar | 39 | Gengarite | Perish Song, Protect, Shadow Ball, Sludge Bomb | Mega ace (Shadow Tag): the trap |

**AI flags:** BASIC, EVAL_ATTACK, EXPERT, HARRASSMENT, CHECK_HP.

**Mega Evolution line:** "Ze curtain falls! Gengar, MEGA EVOLVE!"

> Note: The AI will need tuning to play Perish Trap properly (use Perish Song once, then Protect).

## Gym 6: Byron (Canalave)

**Levels:** 40-44. **Mega:** Mega Scizor.

**Strategy:** Trick Room. Bronzong sets Trick Room so the slowest Pokemon move first. Slow Steel types hit hard, Gyro Ball gets stronger the slower the user is, and Probopass's Magnet Pull traps your Steel types.

**Where it comes from:** Trick Room with Bronzong as the setter, a staple of VGC 2009 and 2010.

| Pokemon | Lv | Item | Moves | Role |
|---|---|---|---|---|
| Bronzong | 40 | Mental Herb | Trick Room, Gyro Ball, Hypnosis, Stealth Rock | Trick Room setter (Levitate); Mental Herb blocks Taunt |
| Bastiodon | 41 | Leftovers | Metal Burst, Iron Defense, Stone Edge, Roar | Wall that hits back |
| Probopass | 42 | Magnet | Magnet Bomb, Earth Power, Thunder Wave, Discharge | Steel trapper (Magnet Pull) |
| Steelix | 42 | Sitrus Berry | Gyro Ball, Earthquake, Stone Edge, Curse | Slow, heavy hitter |
| Scizor | 44 | Scizorite | Bullet Punch, Swords Dance, U-turn, Roost | Mega ace (Technician) |

**AI flags:** BASIC, EVAL_ATTACK, EXPERT, SETUP_FIRST_TURN.

**Mega Evolution line:** "Hard as steel, Scizor! MEGA EVOLVE!"

## Gym 7: Candice (Snowpoint)

**Levels:** 44-48. **Mega:** Mega Abomasnow (new stone needed).

**Strategy:** Hail. Abomasnow's Snow Warning sets hail, which makes Blizzard never miss. Froslass and Glaceon dodge with Snow Cloak, Walrein heals with Ice Body, and Medicham covers Steel types.

**Where it comes from:** Hail with Snow Warning and Blizzard (VGC 2010 hail, and Gen 4 hail teams).

| Pokemon | Lv | Item | Moves | Role |
|---|---|---|---|---|
| Froslass | 44 | Focus Sash | Spikes, Ice Beam, Shadow Ball, Destiny Bond | Lead (Snow Cloak); hazards |
| Walrein | 45 | Leftovers | Blizzard, Surf, Protect, Rest | Bulky (Ice Body) |
| Medicham | 46 | Choice Band | High Jump Kick, Ice Punch, Bullet Punch, Zen Headbutt | Steel breaker (Pure Power) |
| Glaceon | 46 | Bright Powder | Blizzard, Shadow Ball, Barrier, Wish | Evasive special attacker (Snow Cloak) |
| Abomasnow | 48 | Abomasite | Blizzard, Wood Hammer, Ice Shard, Earthquake | Mega ace (Snow Warning) |

**AI flags:** BASIC, EVAL_ATTACK, EXPERT, WEATHER.

**Mega Evolution line:** "Focus! Abomasnow, MEGA EVOLVE!"

> Note: Abomasite is not in the game yet. Fallback: Mega Empoleon.

## Gym 8: Volkner (Sunyshore)

**Levels:** 49-53. **Mega:** Mega Manectric (new stone needed).

**Strategy:** Pivoting and speed. U-turn and Choice Scarf keep momentum, Mega Manectric cycles Intimidate, Rotom-Wash covers Ground types, and Electivire absorbs Electric moves aimed at its team.

**Where it comes from:** Intimidate cycling with Mega Manectric (a VGC 2015 staple), and Rotom-Wash (a Gen 4 and Gen 5 OU staple).

| Pokemon | Lv | Item | Moves | Role |
|---|---|---|---|---|
| Jolteon | 49 | Choice Specs | Thunderbolt, Shadow Ball, Hidden Power (Ice), Baton Pass | Fast special attacker (Volt Absorb) |
| Raichu | 50 | Focus Sash | Nasty Plot, Thunderbolt, Grass Knot, Focus Blast | Setup sweeper |
| Rotom (Wash form) | 50 | Leftovers | Thunderbolt, Hydro Pump, Will-O-Wisp, Pain Split | Pivot; beats Ground types |
| Luxray | 51 | Choice Scarf | Crunch, Thunder Fang, Ice Fang, Superpower | Intimidate; scarfed revenge killer |
| Electivire | 51 | Life Orb | Thunder Punch, Cross Chop, Ice Punch, Earthquake | Mixed attacker (Motor Drive) |
| Manectric | 53 | Manectite | Thunderbolt, Overheat, Hidden Power (Ice), Roar | Mega ace (Intimidate) |

**AI flags:** BASIC, EVAL_ATTACK, EXPERT, CHECK_HP.

**Mega Evolution line:** "Finally, a real spark. Manectric, MEGA EVOLVE!"

> Note: Manectite is not in the game yet. Fallback: no Mega, or Mega Staraptor as a Flying-type ace.

## Elite Four: Aaron (Bug)

**Levels:** 55-58. **Mega:** Mega Heracross (new stone needed).

**Strategy:** Baton Pass chain. Ninjask's Speed Boost and Swords Dance stack up, then Baton Pass hands them to a receiver. Yanmega does the same with Speed Boost, Vespiquen stalls, and Mega Heracross receives the boosts and sweeps.

**Where it comes from:** Ninjask Baton Pass chains, one of the most notorious strategies of Gen 3 and Gen 4 competitive singles.

| Pokemon | Lv | Item | Moves | Role |
|---|---|---|---|---|
| Ninjask | 55 | Focus Sash | Swords Dance, Baton Pass, Protect, Substitute | Lead (Speed Boost); the passer |
| Yanmega | 56 | Wide Lens | Protect, Bug Buzz, Air Slash, U-turn | Speed Boost attacker |
| Vespiquen | 56 | Leftovers | Defend Order, Heal Order, Attack Order, Toxic | Stall |
| Drapion | 57 | Black Sludge | Swords Dance, Night Slash, Cross Poison, Earthquake | Receiver |
| Scizor | 57 | Choice Band | Bullet Punch, U-turn, Superpower, Pursuit | Revenge killer (Technician) |
| Heracross | 58 | Heracronite | Close Combat, Pin Missile, Rock Blast, Swords Dance | Mega ace (Skill Link); the receiver |

**AI flags:** BASIC, EVAL_ATTACK, EXPERT, BATON_PASS, SETUP_FIRST_TURN.

**Mega Evolution line:** "Bugs work together. Heracross, MEGA EVOLVE!"

> Note: Heracronite is not in the game yet. Fallback: Mega Scizor.

## Elite Four: Bertha (Ground)

**Levels:** 56-59. **Mega:** Mega Torterra.

**Strategy:** Sand and hazard stall. Hippowdon's Sand Stream chips everything that isn't Rock, Ground or Steel. Stealth Rock and Roar rack up damage on every switch, and Gliscor dodges in the sand.

**Where it comes from:** Hippowdon sand stall (Gen 4 OU), and stall teams built on hazards plus phazing.

| Pokemon | Lv | Item | Moves | Role |
|---|---|---|---|---|
| Hippowdon | 56 | Leftovers | Stealth Rock, Slack Off, Roar, Earthquake | Lead (Sand Stream) |
| Gliscor | 57 | Bright Powder | Earthquake, Roost, U-turn, Taunt | Evasive (Sand Veil) |
| Whiscash | 57 | Leftovers | Dragon Dance, Earthquake, Waterfall, Stone Edge | Setup sweeper |
| Rhyperior | 58 | Sitrus Berry | Stone Edge, Earthquake, Megahorn, Rock Polish | Tank (Solid Rock) |
| Golem | 58 | Focus Sash | Explosion, Stone Edge, Earthquake, Sucker Punch | Wallbreaker |
| Torterra | 59 | Torterrite | Wood Hammer, Earthquake, Stone Edge, Rock Polish | Mega ace |

**AI flags:** BASIC, EVAL_ATTACK, EXPERT, WEATHER, CHECK_HP.

**Mega Evolution line:** "Grounded, dear. Torterra, MEGA EVOLVE!"

> Note: If the player's starter is Turtwig, Bertha's Mega Torterra mirrors it, which is a fun moment.

## Elite Four: Flint (Fire)

**Levels:** 57-60. **Mega:** Mega Infernape.

**Strategy:** Sun hyper offense. Ninetales and Houndoom set Sunny Day with Heat Rocks, boosting every Fire move, and nobody on the team sits still.

**Where it comes from:** Sun hyper offense (VGC 2015 sun, with Ninetales's Drought and Mega Charizard Y).

| Pokemon | Lv | Item | Moves | Role |
|---|---|---|---|---|
| Ninetales | 57 | Heat Rock | Sunny Day, Fire Blast, Solar Beam, Will-O-Wisp | Sun setter |
| Houndoom | 58 | Life Orb | Nasty Plot, Fire Blast, Dark Pulse, Sunny Day | Second sun setter and sweeper |
| Rapidash | 58 | Choice Band | Flare Blitz, Megahorn, Bounce, Quick Attack | Physical attacker (Flash Fire) |
| Magmortar | 59 | Expert Belt | Fire Blast, Thunderbolt, Focus Blast, Hidden Power (Grass) | Coverage |
| Flareon | 59 | Toxic Orb | Flare Blitz, Superpower, Quick Attack, Facade | Guts attacker |
| Infernape | 60 | Infernapite | Flare Blitz, Close Combat, Mach Punch, U-turn | Mega ace |

**AI flags:** BASIC, EVAL_ATTACK, EXPERT, WEATHER, RISKY, DAMAGE_PRIORITY.

**Mega Evolution line:** "Let's burn bright! Infernape, MEGA EVOLVE!"

## Elite Four: Lucian (Psychic)

**Levels:** 58-61. **Mega:** Mega Alakazam.

**Strategy:** Dual screens hyper offense. Mr. Mime and Bronzong set Reflect and Light Screen with Light Clay. Behind the screens, Espeon and Gallade set up, and Mega Alakazam sweeps.

**Where it comes from:** Dual-screens hyper offense (Gen 4 OU's Azelf and Uxie screen leads, and VGC screens plus setup).

| Pokemon | Lv | Item | Moves | Role |
|---|---|---|---|---|
| Mr. Mime | 58 | Light Clay | Reflect, Light Screen, Psychic, Encore | Screens lead (Filter) |
| Bronzong | 59 | Light Clay | Reflect, Light Screen, Gyro Ball, Stealth Rock | Second screens setter |
| Espeon | 59 | Leftovers | Calm Mind, Psychic, Shadow Ball, Morning Sun | Setup sweeper |
| Gallade | 60 | Lum Berry | Swords Dance, Psycho Cut, Close Combat, Night Slash | Setup sweeper |
| Girafarig | 60 | Sitrus Berry | Nasty Plot, Psychic, Thunderbolt, Baton Pass | Passer |
| Alakazam | 61 | Alakazite | Psychic, Focus Blast, Shadow Ball, Calm Mind | Mega ace (Trace) |

**AI flags:** BASIC, EVAL_ATTACK, EXPERT, SETUP_FIRST_TURN.

**Mega Evolution line:** "Chapter's end. Alakazam, MEGA EVOLVE."

## Champion: Cynthia

**Levels:** 62-66. **Mega:** Mega Garchomp.

**Strategy:** Balanced, with a trick. Spiritomb leads with burns. Togekiss runs paraflinch: Thunder Wave, then Serene Grace Air Slash flinches half the time. Milotic and Lucario cover each other, and Mega Garchomp sets Swords Dance to finish.

**Where it comes from:** Togekiss paraflinch (infamous in Gen 4 and Gen 5), and the balanced "good stuff" teams of VGC 2009 and 2010.

| Pokemon | Lv | Item | Moves | Role |
|---|---|---|---|---|
| Spiritomb | 62 | Leftovers | Will-O-Wisp, Sucker Punch, Pain Split, Shadow Sneak | Lead; burns physical attackers |
| Roserade | 63 | Focus Sash | Toxic Spikes, Leaf Storm, Sludge Bomb, Shadow Ball | Hazards |
| Togekiss | 64 | Leftovers | Air Slash, Thunder Wave, Nasty Plot, Roost | Paraflinch (Serene Grace) |
| Milotic | 64 | Leftovers | Surf, Ice Beam, Recover, Mirror Coat | Bulky (Marvel Scale) |
| Lucario | 65 | Life Orb | Nasty Plot, Aura Sphere, Dark Pulse, Vacuum Wave | Special sweeper |
| Garchomp | 66 | Garchompite | Swords Dance, Earthquake, Outrage, Stone Edge | Mega ace |

**AI flags:** BASIC, EVAL_ATTACK, EXPERT, SETUP_FIRST_TURN, CHECK_HP.

**Mega Evolution line:** "This is where it ends. Garchomp, MEGA EVOLVE!"

## To build

- New Mega Stones and sprites: Abomasite (Candice), Manectite (Volkner), Heracronite (Aaron). Each has a fallback if you'd rather not build it.
- Ability control: weather and trap strategies depend on specific abilities (Swift Swim, Chlorophyll, Shadow Tag, Snow Cloak). Trainer data doesn't set abilities directly, so a trainer ability field (or personality-value control) is needed.
- Mega forms: Mega Gengar needs Shadow Tag, Mega Gyarados Mold Breaker, Mega Scizor Technician, Mega Alakazam Trace, and Mega Lucario Adaptability in their Mega form species data.
- AI tuning for Perish Trap (Fantina) and Baton Pass chains (Aaron): the stock AI doesn't play these well without help.
- Realign totem levels to the new curve: Spiritomb 30 to 40, Aggron 42 to 45, Mamoswine 44 to 49, Kingdra 50 to 54. The others already fit.
- Gym rematches and the Elite Four rematches: same strategies, roughly 10 levels higher, in the postgame.

Story battles (Garius, Cyrus, Saros, Kahn, Indra) aren't in this tab yet. They can follow the same format next.

