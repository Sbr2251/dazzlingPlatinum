# Arc 1, part 2 ("finish Act 1"): implementation contract (v1)

Base: branch `arc1-part2` at `25607dc5e5` (== main). This file is the contract between the parallel workstreams:
scope, owner decisions (with defaults), shared story state, file ownership, handoffs, per-scene notes, tests, risks.
It is modeled on `docs/arc1/revision/spec.md`. Every rule in that spec's "Build and test" section still applies
(ASCII text only, 27-tile boxes, 2 lines per page, about 192-197 px per line, "Pokémon" with the e-acute like the
neighbouring stock text) unless this file says otherwise.

Sources: `docs/story/arc1_part2_screenplay.md` (= `/tmp/act1p2/act1.txt` part 2, scenes 7-14), backlog item 1
(`/tmp/act1p2/backlog.txt`), the six recon reports `/tmp/act1p2/recon_*.md`. When this spec and a recon report
disagree, this spec wins.

---

## 1. Scope

### In scope ("Arc 1 playable through Gym 1")

1. **Garius rename.** The default rival name becomes "Garius". The rival is still the `BufferRivalName` buffer, the
   `TRAINER_CLASS_RIVAL` trainers and `OBJ_EVENT_GFX_BARRY` (`src/trainer_data.c:39-40` swaps in the saved name at
   battle time). The naming screen stays skipped.
2. **Ruth rename and placeholder sprite.**
   - Both counterpart names become "Ruth".
   - Every Ruth object reachable in Arc 1 uses one fixed placeholder sprite, regardless of the player's gender.
   - Ruth's catching-tutorial back sprite is fixed to the female one, and her music is fixed.
   - Hardcoded "Dawn:"/"Lucas:" text and gender branches go away on every map that Arc 1 reaches.
3. **Part 1 parity fixes.** These are text only:
   - Rowan's intro.
   - The deal logic.
   - Garius's DW line.
   - Rowan names his lab at Lake Verity.
   - The Ruth sprite at Lake Verity.
4. **Scenes 7-14** of the Act 1 screenplay, ending at **END OF ARC 1** after the mine rift (scene 14). The ladder is
   `VAR_ARC1_PROGRESS` 9-16.
5. **Neutralizing the stock content those scenes collide with:**
   - Barry's burst-out, the town tour, the Parcel and the Trainers' School.
   - Dawn's Jubilife escort and Looker's Pokétch block.
   - The post-Gym-1 Galactic tag battle and Looker's Pal Pad scene.
   - Barry's post-badge scene.
   - The reachable Arc 2 Hitmonlee totem.

### Out of scope

- Arc 2 and later: the Cyrus confession and the Ravaged Path rift and totem fight; Dawn/Lucas text on Arc 2+ maps
  (Canalave, Veilstone, Route 206/207/218 gates, `scripts_unk_1051.s` small talk).
- HM removal and the Resonator (backlog 2). The Oreburgh Gate HM06 hiker (`VAR_UNK_0x4093`) stays stock.
- New art: Ruth, Garius, Saros, Eclipse grunts, banner, big screen. Placeholders only. The one exception is the
  optional Stream E placeholder field sprites (rift, violet Hitmonlee), which are generated from existing assets.
- New maps, map-model or area edits, new scrcmds or engine work. Stream E's append-only sprite tables are the only
  C change outside lead pre-work.
- Trainer rebalancing beyond Garius's Route 203 team. Roark's team per `docs/story/trainers.md` is optional (Stream D,
  only if time allows).
- Existing saves. The rival name is saved once at the end of the intro (`rowan_intro_app.c:345`). **Test with a new
  game** (or the golden save in section 6).

### Playable end point

1. After Gym 1, the screen shakes and a miner runs up.
2. Mine B2F rift scene.
3. Fade, then the "END OF ARC 1 / To be continued..." field message. `VAR_ARC1_PROGRESS` = 16.
4. The player is then free to roam:
   - The Ravaged Path totem stays hidden.
   - Jubilife's north exit shows "To be continued..." at 16.
   - Rock Smash past Ravaged Path is already impossible without `FLAG_TOTEM_HITMONLEE_DEFEATED`
     (`scripts_field_moves.s:130-132`).

---

## 2. Owner decisions (only genuine ones; each has a default so work can proceed)

| # | question | **default if no answer** | who implements |
|---|---|---|---|
| D1 | Ruth's interim overworld sprite | **`OBJ_EVENT_GFX_DP_PLAYER_F`** (253, Dawn's D/P outfit). Same renderer as the player sprites, with walk and run frames, unused on every map, and it matches the `DP_PLAYER_FEMALE` class. Fallback if it misrenders in the smoke test: `OBJ_EVENT_GFX_SCIENTIST_F` (30, walk frames only; matches the lab aide). Streams write the literal with the comment `/* Ruth placeholder (D1) */` so a later art swap is one grep. | L picks after the smoke test (L6); every stream uses it |
| D2 | Saros "on the big screen" | **Text-only speaker "Saros (on screen):"**: camera tilts to the Jubilife TV facade, `SEQ_TV_HOUSOU` + `SEQ_SE_DP_TV_NOISE` (the bedroom TV's pair, `scripts_twinleaf_town_player_house_2f.s:31-41`), and a white `FadeScreen` flash. No Saros sprite. | C |
| D3 | Eclipse grunt look | **`OBJ_EVENT_GFX_GRUNT_M` / `GRUNT_F`** placeholders (Galactic doesn't exist in this world, so re-skinning these two later re-skins every grunt). No battle, so no trainer class. | C |
| D4 | Stock Looker in Jubilife | **Reuse object 31 as the "Man in a Trench Coat" cameo during the rally**, then hide him (`FLAG_UNK_0x0181`). Drop the stock Pal Pad scene (Gym line 34) and the VS Recorder intro (state 0 chain). | C (cameo), D (Gym line) |
| D5 | Rowan's intro text | **Adopt the parity recon's 6-page replacement** (`/tmp/act1p2/recon_part1_parity.md`, item 3): adds "a world that resembles the one you know..." and removes "It begins after Team Galactic fell", which contradicts `bible.md:19`. | A |
| D6 | Deal logic | **Reword msg 50** (`LakeVerity_Text_Arc1RowanADealIsADeal`, `lake_verity.json:477-483`) to acknowledge the forbid ("I made no promise... but you kept your end of it all the same. Very well. A deal is a deal - the starters are yours."). **Reword the DW line** (`distortion_world_arc1_seams.json:78`) to "We found it! Now Rowan owes us one!" | A |
| D7 | Cyrus's "Take it to Rowan when he's ready to listen" (`LakeVerity_Text_Arc1CyrusTakeItToRowan`) | **Keep**. Scene 9 pays it off: Garius makes the player show the shard. | - |
| D8 | Stock items the new flow removes | **Town Map**: Ruth gives it on Route 202 right after the 5 Poké Balls (`GiveItemQuantity` prints the stock "obtained" line, so no new dialogue). **Journal**: kept (Mom, after the Pokédex). **Parcel**: dropped. **TM27** (town tour): dropped. **VS Recorder**: dropped in Arc 1. **Pokétch campaign**: kept as optional side content. | B (Town Map, tour), A (Journal/Parcel), C (Pokétch) |
| D9 | Losing on Route 203 | **Stock blackout** (`scripts_route_203.s:133`); the trigger re-arms. Route 201 stays non-losing (`StartFirstBattle`), as the doc says. | C |
| D10 | Garius's Route 203 team ("I caught two more") | **Starly Lv 7 + Bidoof Lv 7 + counter-starter Lv 9**. Edit only the party in the 3 `rival_route_203_*.json` files. Bidoof is stock on Routes 201/202 and doesn't depend on the Gen 3 encounter work. | C |
| D11 | Mine visuals | **Placeholders**:<br>- Rift: Stream E's `OBJ_EVENT_GFX_ARC1_RIFT`, or white flashes plus `ShakeCamera` if E hasn't landed.<br>- Giant Hitmonlee: Stream E's violet recolour of the totem sprite (fallback: stock `OBJ_EVENT_GFX_TOTEM_HITMONLEE`), shown for about 0.5 s with `PlayCry SPECIES_HITMONLEE` + `ShakeCamera` + a flash.<br>- "One frame Giratina shadow": a 2-4 frame black `FadeScreen` blip with no reaction from anyone. | D, E |
| D12 | Lines that clash with the bible | Garius's mom: in Arc 1-reachable states, swap the present-tense "I wonder who he takes after?" lines (`twinleaf_town_rival_house_1f.json:13,25,36,45,63`) for the doc's scene 7 lines. Rival at the Oreburgh Gym door, msg 0 ("I wonder how he compares to my dad..."): **reword to past tense** as a soft track-G hint ("...how he'd have done against my dad. ...Huh? Forget it."). | A, D |
| D13 | Post-Arc-1 gate | Show the **"To be continued..." field message at Jubilife's north exit** at state 16 and walk the player back one step, mirroring Route 201 in part 1. The world is otherwise open. | C |
| D14 | Ruth's music | **Always `SEQ_THE_GIRL`** (L4). | L |

Already approved in part 1 and not reopened: the forbid, Garius runs in first, Ruth closes the portal, the Eclipse
Shard, the heal after the Mawile battle, no alcove item, no drawn BREAKING NEWS banner. The lead mirrors them into
the Google Doc (lead post-work L9).

---

## 3. Story state

### 3.1 `VAR_ARC1_PROGRESS` (0x406C) ladder 9-16

Coord events compare with `==`, so each gating beat gets its own value. Literal numbers in scripts (as in part 1),
always with a comment naming the state. Saves at 8 stay valid. No C code reads values above 7
(`grep -rn VAR_ARC1_PROGRESS src` lists only 0/1/3/4/5/7), so 9+ is safe.

| val | meaning | set by (stream, script) | what blocks/gates the player in this state |
|---|---|---|---|
| 8 | part 1 done; heading home | Lake Verity (existing, `scripts_lake_verity.s:810`) | Route 201 coord 2 (x115 z852-855, script 19) becomes a **go-home nudge**: a short line, then step west. The player can't reach Sandgem without seeing Mom. |
| **9** | Mom scene done; Garius waits on Route 201 | **A**: Twinleaf player house 1F frame script (new ScriptEntry 12) | Route 201 new coord (x110 z857 w4 l1, value 9) at the Twinleaf exit row runs the Garius battle. Garius is visible only at 9. Coord 2 (state 8) is inert. |
| **10** | Route 201 battle done; Sandgem open | **A**: `Route201_TriggerArc1RivalBattle` (new), after `RemoveObject` | Sandgem's stock arrival coord (x164 z842-847, `VAR_UNK_0x4071 == 0`) has Ruth walk the player to the lab, then the lab's frame script (`VAR_UNK_0x40A6 == 0`) runs the scene. Route 202's stock coord pushes the player back while the state is below 11. |
| **11** | Lab done: Pokédex given, shard handed over, "Come with me" | **B**: lab `_01AE` (rewritten) | Sandgem frame script (`VAR_UNK_0x4071 == 1`, stock script 3 `_057C`, rewritten) has Ruth lead the player north. Route 202 coord (x180 z825-829, `VAR_UNK_0x4087 == 0`) runs the lesson. |
| **12** | Lesson done: 5 Poké Balls + Town Map | **B**: Route 202 `_00C7` chain, next to `:162` | Jubilife: rally cast visible. New coord at the east exit (x188 z757-760, value 12) says "over here", then the player steps west. Talking to Garius at the TV runs the rally. |
| **13** | Rally done | **C**: Jubilife rally script (new) | Route 203 stock coord (x196 z757-760, `VAR_UNK_0x4088 == 0`) runs Garius battle 2. Jubilife east exit is open. |
| **14** | Route 203 battle done; heading to Oreburgh | **C**: `scripts_route_203.s`, next to `:128` | Stock Oreburgh: Youngster escort (`VAR_OREBURGH_STATE == 0`), Garius at the Gym door until the player meets Roark in Mine B2F, then the Gym. |
| **15** | Coal Badge won; rift sequence pending | **D**: `OreburghGym_Roark`, next to `:35` | Oreburgh City frame script (value 15) runs the shake and the miner, sets `VAR_OREBURGH_STATE` to 3 (stock coord 1 `_00D7` goes inert) and warps to Mine B2F (12,17). The B2F frame script (value 15) runs the rift scene. Re-entering B2F at 15 replays the scene. |
| **16** | END OF ARC 1 | **D**: B2F rift scene, last line before the card | Jubilife north exit coord (value 16) shows "To be continued..." and steps the player back. The Ravaged Path totem stays hidden while the state is below 17. |

Arc 2 starts at 17, which isn't defined here. `scripts_ravaged_path.s` unhides the totem at `>= 17` (section 5, D).

### 3.2 Stock state variables each scene must leave consistent (so stock triggers can't fire)

| var/flag | value after | set by | why |
|---|---|---|---|
| `VAR_PLAYER_HOUSE_STATE` | 5 at the Mom scene | A | Mom heals on every talk (`:175`) and gives the Journal once `FLAG_HAS_POKEDEX` is set (`:174`) |
| `VAR_PLAYER_HOUSE_STATE` | 6 straight after the Journal (skip `RivalsMomEnters`, `:283`) | A | no Parcel |
| `VAR_UNK_0x4071` | 1 when Ruth walks the player in (stock `:214`), 2 at the end of the rewritten `_057C` | B | the stock tour is gone |
| `VAR_UNK_0x40A6` | 1 at the end of the lab (stock `:311`) | B | |
| `VAR_UNK_0x4087` | 1 at the end of the lesson (stock `:162`) | B | |
| `VAR_JUBILIFE_STATE` | 2 at the first Jubilife load with progress >= 12 | C | makes coord 0 (escort), coord 2 (Looker block) and `_00AC` inert |
| `FLAG_UNK_0x00F1`, `FLAG_UNK_0x01F4` | set (same block) | C | "Trainers' School done", Barry hidden in the School |
| `VAR_UNK_0x40E7` | 2, plus `ClearFlag FLAG_UNK_0x01F6`/`0x01F5` (same block) | C | the Pokétch campaign becomes optional, without the forced intro (coord 4) |
| `VAR_UNK_0x4088` | 1 (stock `:128`) | C | |
| `VAR_OREBURGH_STATE` | 3 in the city's frame script at 15 | D | stock coord 1 (state 2) and `_00D7` never fire |
| `VAR_JUBILIFE_STATE`, `VAR_JUBILIFE_LOOKER_PALPAD` | **not touched by the Gym**: delete `oreburgh_city_gym.s:34` and `:37-40` | D | no Galactic tag battle, no Pal Pad Looker |

### 3.3 New flags (lead renames these lines in place in `generated/vars_flags.txt`; never insert lines)

A flag's ID is its 0-based line index. `FLAG_UNK_0x0910`..`0x095F` are referenced nowhere in `res/ src/ include/
asm/ tools/`; I verified that for 0x910-0x95F. 0x910 is line 2321 (1-based). This block sits after
`FLAG_HIDE_TOTEM_KINGDRA` (0x90F), outside the trainer-flag range (`FLAG_OFFSET_TRAINER_DEFEATED 1360`,
`include/script_manager.h:103`, 928 trainers, ending 0x8EF), the hidden-item range and the map-load and daily
reset ranges.

| ID | line | new name | owner | meaning |
|---|---|---|---|---|
| 0x910 | 2321 | `FLAG_HIDE_ARC1_LAB_GARIUS` | B | Garius in the Sandgem lab (new object) |
| 0x911 | 2322 | `FLAG_HIDE_ARC1_JUBILIFE_RALLY` | C | rally crowd + 2 grunts |
| 0x912 | 2323 | `FLAG_HIDE_ARC1_JUBILIFE_RALLY_CAST` | C | Garius + Cyrus at the rally (both `RemoveObject` in the scene) |
| 0x913 | 2324 | `FLAG_HIDE_ARC1_MINE_SEAL` | D | B2F rubble boulders over the NW bay |
| 0x914 | 2325 | `FLAG_HIDE_ARC1_MINE_CAST` | D | B2F Garius, Rowan, Ruth |
| 0x915 | 2326 | `FLAG_HIDE_ARC1_MINE_RIFT` | D | B2F rift object |
| 0x916 | 2327 | `FLAG_HIDE_ARC1_MINE_SILHOUETTE` | D | B2F giant Hitmonlee silhouette |
| 0x917 | 2328 | `FLAG_HIDE_ARC1_OREBURGH_RUNNER` | D | Oreburgh City miner who runs up after the Gym |
| 0x918 | 2329 | `FLAG_ARC1_SPARE_A` | A | spare for A, if needed |
| 0x919 | 2330 | `FLAG_ARC1_SPARE_B` | B | spare for B |
| 0x91A | 2331 | `FLAG_HIDE_ARC1_JUBILIFE_SAROS` | C | hide flag for Saros on the Jubilife TV screen (was spare C) |
| 0x91B | 2332 | `FLAG_ARC1_SPARE_D` | D | spare for D |

A stream that uses its spare reports the new name in its final report, and the lead renames it at merge. Until
then the stream uses the `FLAG_ARC1_SPARE_x` name. Don't use `FLAG_UNUSED_2421/2448/2449`, `VAR_UNUSED_0x406F` or
`VAR_UNUSED_0x4031`; they stay reserved for Arc 2.

**No new vars.** Reused stock hide flags:
- `FLAG_HIDE_ROUTE_201_RIVAL` (Route 201 Garius)
- `FLAG_HIDE_SANDGEM_TOWN_COUNTERPART` (Sandgem Ruth)
- `FLAG_UNK_0x0199` (lab Ruth)
- `FLAG_UNK_0x0188` (Route 202 Ruth)
- `FLAG_UNK_0x0181` (Jubilife Looker)
- `FLAG_UNK_0x0238` (Jubilife clown 27, unused by any script)
- `FLAG_UNK_0x018A` (Roark, B2F local 0)
- `FLAG_HIDE_TOTEM_HITMONLEE`

**Hide-flag rules:**
- `RemoveObject` sets the object's own `hidden_flag`.
- Objects that must vanish at different times need different flags.
- Set hide flags in the map's **OnTransition**, keyed on `VAR_ARC1_PROGRESS`, so they work for any save
  (precedent: `scripts_lake_verity.s:30-45`). Don't put them in `scripts_init_new_game.s`.

---

## 4. Workstreams and file ownership

Five streams and the lead. Each stream works in its own git worktree, on branch `a1p2/<stream>`, cut from the lead's
pre-work commit. Only edit files you own. A file you need from another stream goes in your final report as an exact
patch. Nobody commits to `arc1-part2` except the lead. Streams commit on their own branch, by path.

Glob notes:
- `scripts_X*.s` covers `scripts_X*.s` **and** `scripts_init_X*.s`.
- "text" means `res/text/<bank>.json` with the same stem.
- "events" means `res/field/events/events_<stem>.json`.

### Lead pre-work (one commit, before any stream starts)

| id | change | file:line |
|---|---|---|
| L1 | Rename the 12 flag lines in section 3.3 | `generated/vars_flags.txt:2321-2332` |
| L2 | Both counterpart names become "Ruth" | `res/text/counterpart_names.json:6` ("Lucas"), `:10` ("Dawn") |
| L3 | Default rival "Garius": append `{"id": "RowanIntro_Text_RivalDefaultName", "en_US": "Garius"}` to the end of `res/text/rowan_intro.json`; point `rowan_intro_app.c:1600` at it and fix the comment at `:1599`. Don't edit `RivalChoiceBarry` (`:77-78`), which the dead menu still uses (`rowan_intro_app.c:795`). After this commit, Stream A owns `rowan_intro.json`. | `src/applications/rowan_intro/rowan_intro_app.c:1599-1600` |
| L4 | Ruth's music is always "The Girl": `CommonScript_SetCounterpartBGM` does `StopMusic 0` + `SetBGM SEQ_THE_GIRL`, with no gender branch | `res/field/scripts/scripts_common.s:1579-1585` |
| L5 | Ruth's catching-tutorial trainer is female: `TrainerInfo_SetGender(..., GENDER_FEMALE)` and `MessageLoader_GetString(msgLoader, 1, ...)` | `src/field_battle_data_transfer.c:188,193` |
| L6 | Smoke-test `OBJ_EVENT_GFX_DP_PLAYER_F` as an NPC: in a scratch build only (not committed), temporarily point Lake Verity's setter at it and screenshot walk and run. Then publish D1's final value. | `/tmp/act1p2/handoff/ruth_gfx.txt` (a single line: the constant) |
| L7 | Harness: `/tmp/act1p2/harness/a1p2emu.py` (section 6) and the golden state-8 save `/tmp/act1p2/harness/golden_s8.sav`, made with the L1-L5 ROM | outside the repo |
| L8 | Copy this spec to `docs/arc1/part2/spec.md` | `docs/arc1/part2/` |

The lead owns, for the whole project:
- `generated/vars_flags.txt`
- `res/text/counterpart_names.json`
- `res/text/generic_names.json` (no edit planned; the naming screen is unreachable)
- `src/applications/rowan_intro/**`
- `src/field_battle_data_transfer.c`
- `res/field/scripts/scripts_common.s`
- `res/field/scripts/scripts_init_new_game.s` (no edit planned)
- `docs/**`
- the shared harness

Lead post-work:
- L9: refresh the stale `docs/arc1/screenplay.md` and write `docs/arc1/part2/STATUS.md`.
- L10: merge the streams into `arc1-part2` in the order E, A, B, C, D. Ownership is disjoint, so the merges are
  trivial.
- L11: the end-to-end run, a build, then push. Per memory, push to an explicit `refs/heads/arc1-part2` over SSH.

### Stream A: "Home" (part 1 parity + scenes 7-8). Sets 9 and 10.

**Owns:**
- `res/text/rowan_intro.json` (after L3)
- `scripts_lake_verity.s`, `events_lake_verity.json`, `res/text/lake_verity.json`
- `res/text/distortion_world_arc1_seams.json` (text only, no script changes)
- `scripts_twinleaf_town*.s`, `events_twinleaf_town*.json`, `res/text/twinleaf_town*.json`
- `scripts_route_201.s`, `events_route_201.json`, `res/text/route_201.json`

**Work:**
- **D5 intro.**
- **D6 deal text.**
- **Lake Verity:**
  - `LakeVerity_Text_Arc1RowanItsGone` (`lake_verity.json:493-498`) adds Rowan telling the kids to come to his lab
    in Sandgem once they've rested. Scene 8's "Rowan said to come by his lab" depends on it.
  - The counterpart setter at `scripts_lake_verity.s:45-57` uses the D1 constant for both genders.
- **Scene 7:** Mom, the living-room TV, Garius's mom.
- **Scene 8:** the go-home nudge at 8, the Garius battle at 9.

**Interfaces:**
- **Produces:** 9 (Mom), 10 (after the battle; Garius is removed).
- **Needs:** nothing from other streams.
- Garius's last line on Route 201 points to the lab. B's lab scene assumes he arrives first.

**Acceptance (emulator):**
1. From the golden save (state 8, Lake Verity terrace or Route 201):
   - walking east past x115 shows the nudge and the player steps back;
   - entering the house runs the Mom scene: 3 lines, a heal (check party HP after damaging it by save patch or a
     battle), `VAR_PLAYER_HOUSE_STATE` = 5, progress = 9;
   - the TV shows the news line;
   - Garius's mom shows the doc lines.
2. At 9:
   - walking north through z857 at each of x110-113 has Garius run up; the battle starts with
     `TRAINER_RIVAL_ROUTE_201_<player starter>`;
   - **win** shows the win line, the 10-million line, he exits east, progress = 10;
   - **loss** (patch the party to 1 HP) returns to the field with no blackout, shows the lose line, and gives the
     same end state.
3. At 10, coord 2 and the battle coord are both inert, and Garius is not visible on Route 201.
4. With a patched `FLAG_HAS_POKEDEX`, Mom gives the Journal and Garius's mom does **not** enter (no Parcel in the
   bag).
5. New game: the intro shows the new text, and the rival name is "Garius" (2F TV line, Lake Verity lines).

### Stream B: "Sandgem" (scenes 9-10). Sets 11 and 12.

**Owns:**
- `scripts_sandgem_town*.s` (town, lab, counterpart house 1F/2F, all Sandgem interiors and their init scripts)
- `events_sandgem_town*.json`, `res/text/sandgem_town*.json`
- `scripts_route_202.s` (and `scripts_init_route_202.s`), `events_route_202.json`, `res/text/route_202.json`

**Work:**
- Ruth at the lab door (reuse `_0085`).
- Lab rewrite: Garius present, Pokédex, shard hand-over.
- Replace the town tour with "Come with me".
- Route 202 lesson: the gate is re-keyed, Ruth's 3 lines, 5 Poké Balls + Town Map, she exits toward Sandgem.
- The counterpart-house family lines become Ruth's (keep the house as Ruth's family home, and force the
  sister-branch lines).
- Ruth setters use D1.

**Interfaces:**
- **Needs:** 10 from A; Garius has already left Route 201 eastward.
- **Produces:**
  - 11 (end of the lab)
  - 12 (end of the lesson)
  - `VAR_UNK_0x4071` = 2, `VAR_UNK_0x40A6` = 1, `VAR_UNK_0x4087` = 1
  - `FLAG_HAS_POKEDEX`
  - `ITEM_ECLIPSE_SHARD` removed, `ITEM_POKE_BALL` x5 and `ITEM_TOWN_MAP` given
- C assumes the player arrives in Jubilife at 12 from the south with a Pokédex and Poké Balls. Ruth is **not** in
  Jubilife.

**Acceptance:**
1. Golden save patched to 10 at Route 201 (150,843):
   - walking east into Sandgem has Ruth walk the player in, saying the doc line;
   - the lab scene plays in doc order, with Garius at the desk;
   - the bag loses the Eclipse Shard; `FLAG_HAS_POKEDEX` is set;
   - Garius runs out;
   - Ruth: "Come with me", then the player is back in Sandgem;
   - Ruth leads north, then she's gone; progress = 11.
2. At 11, walking north on Route 202 fires the lesson at every z 825-829:
   - catching demo vs Bidoof (Ruth's name is "Ruth", female back sprite);
   - the 3 doc lines, 5 Poké Balls + Town Map;
   - Ruth walks back south/east and is removed; progress = 12.
3. At 10, patched onto Route 202 (181,827): pushed back, with no softlock.
4. Talk to every visible Ruth in Sandgem, the lab and Route 202 at 10-12: no "Dawn"/"Lucas" text anywhere. Script
   10300 is never reached.

### Stream C: "Jubilife" (scenes 11-12 + post-arc gate). Sets 13 and 14.

**Owns:**
- `scripts_jubilife_city.s` (and its init), `events_jubilife_city.json`, `res/text/jubilife_city.json`
- `scripts_trainers_school.s`, `events_trainers_school.json`, `res/text/trainers_school.json` (only if needed;
  the flags are set from Jubilife)
- `scripts_route_203.s` (and its init), `events_route_203.json`, `res/text/route_203.json`
- `res/trainers/data/rival_route_203_{turtwig,chimchar,piplup}.json`

**Work:**
- One stock-skip block.
- Rally objects and show/hide logic.
- The rally cutscene: two free-camera moves, Saros (D2), the grunt and flyer, Garius, the trench coat (D4) and the
  pan to Cyrus.
- East-exit block at 12.
- North-exit "To be continued" at 16 (D13).
- Route 203 text, Yes/No, team (D10).

**Interfaces:**
- **Needs:** 12 from B.
- **Produces:** 13 (rally done), 14 (Route 203 done), and the Jubilife stock state per section 3.2.
- **Consumes:** 16 from D (north gate).
- Must not depend on `VAR_JUBILIFE_STATE` 3 / `FLAG_HIDE_JUBILIFE_{COUNTERPART,ROWAN,GALACTIC_GRUNTS}`, because D
  stops the Gym from setting them.

**Acceptance:**
1. Golden save patched to 12, with `FLAG_HAS_POKEDEX`, at Route 202 (174,800). Walk north into Jubilife:
   - no Dawn escort, no Looker scene;
   - `VAR_JUBILIFE_STATE` = 2;
   - the crowd, grunts, Garius, Looker and Cyrus are visible;
   - the east exit pushes back.
2. Talk to Garius:
   - the full cutscene runs; the camera returns to the player;
   - Cyrus and Garius are removed; progress = 13;
   - no hang, no garbage gfx. Screenshot the Saros, flyer and Cyrus beats.
3. Reload the map at 13: the cast flag hides Garius and Cyrus; the east exit is open.
4. Route 203 at 13:
   - battle with the 3-Pokémon team;
   - **win**: Yes, then the No reply; replay with No, then the other reply; progress = 14;
   - **loss**: blackout, then the trigger re-arms.
5. At 16, the north exit shows "To be continued...", then the player steps back.
6. Talk to the Trainers' School: no Barry. Talk to the president/clowns: the Pokétch is optional and still
   obtainable.

### Stream D: "Oreburgh" (scenes 13-14). Sets 15 and 16.

**Owns:**
- `scripts_oreburgh_city.s` (and its init), `events_oreburgh_city.json`, `res/text/oreburgh_city.json`
- `scripts_oreburgh_city_gym.s`, `res/text/oreburgh_city_gym.json`
- `scripts_oreburgh_mine_b2f.s` (and its init), `events_oreburgh_mine_b2f.json`, `res/text/oreburgh_mine_b2f.json`
- `scripts_ravaged_path.s` (and its init)
- optional: `res/trainers/data/leader_roark.json`

**Work:**
- 2 entrance miners.
- HM-wording rewrites (D12 dad line).
- B2F sealed bay.
- Gym: progress 15, and delete the stock post-badge lines.
- City frame script at 15.
- B2F OnTransition + frame script at 15: the rift scene, 17 lines, cast; ends at 16 with the END card.
- Ravaged Path totem gate.

**Interfaces:**
- **Needs:** 14 from C.
- **Produces:** 15 and 16.
- From E: `/tmp/act1p2/handoff/e_sprites.txt`. D uses placeholders until it exists, then swaps two `graphics_id`
  values.
- D must not reference `OBJ_EVENT_GFX_ARC1_*` before that file exists and E is merged. If D finishes first, the
  lead does the swap at merge.

**Acceptance:**
1. Golden save patched to 14 at Oreburgh Gate exit, i.e. Oreburgh (259,749) facing east:
   - the stock Youngster escort runs;
   - Garius is at the Gym door, with the past-tense dad line;
   - mine entrance miners: 2 lines;
   - B2F: the bay is sealed, with its custom text; Roark's stock meeting has the reworded no-HM lines;
   - Garius is gone from the door.
2. Patch a strong party (section 6). Beat Roark:
   - the reworded badge text; progress = 15;
   - `VAR_JUBILIFE_STATE` unchanged (2);
   - `VAR_JUBILIFE_LOOKER_PALPAD` unchanged (0).
3. Exit the Gym:
   - shake, miner, line, fade, then B2F (12,17);
   - the scene plays in doc order;
   - END card; progress = 16, `VAR_OREBURGH_STATE` = 3;
   - the cast, rift and silhouette are gone on reload.
4. At 16, walk Oreburgh's west exit: `_00D7` does **not** play.
5. Ravaged Path (golden save patched to 13 at its entrance): no totem. Patch 17: the totem is visible.
6. Save inside the Gym at 15, reload, walk out: the scene still fires.

### Stream E (optional, parallel from day 1): "Arc 1 field sprites"

**Owns:**
- `generated/object_events_gfx.txt` (append only)
- `src/overlay005/ov5_021FAF40.c` (append rows only)
- `res/prebuilt/data/mmodel/mmodel/meson.build`
- new `res/field/objects/arc1/**`
- new `tools/integrate_arc1_field_sprites.py`

**Work:** clone the totem pipeline (`tools/integrate_totem_overworld_sprites.py`, commit `bfe72932eb`; Mawile
`863febcd39`; `docs/arc1/mawile_sprite.md`) to add:
- `OBJ_EVENT_GFX_ARC1_RIFT`: a 32x32, 2-frame violet swirl, generated procedurally, with no new hand art;
- `OBJ_EVENT_GFX_ARC1_HITMONLEE_SHADOW`: the `hitmonlee_idle_{a,b}.png` frames recoloured to a violet silhouette.

Both are swap-ready PNGs. They are also reused by backlog 2 (totem rifts).

**Stretch (only with the lead's go-ahead):** a swap-ready `OBJ_EVENT_GFX_RUTH` cloned from the D1 sprite's
resource. If it lands, the lead sweeps the `/* Ruth placeholder (D1) */` setters at merge.

**Publishes:** once the ROM builds and both sprites render in a test map, write
`/tmp/act1p2/handoff/e_sprites.txt`, one line per constant.

**Acceptance:** a scratch script (not committed) shows each object on Route 201 next to the player; screenshots
show the animation and no corruption of neighbouring sprites.

### Shared-file rules

- **Append, never reorder:**
  - ScriptEntries (an object's or coord's `script` is the 1-based entry index);
  - `object_events` (local ID = array index);
  - text messages (stock scripts use numeric `Message N`).
- Never delete a ScriptEntry or an object. Hide objects with flags, and leave unused entries in place.
- New text IDs are named with the bank's prefix plus `Arc1` (for example `JubilifeCity_Text_Arc1SarosOnScreen1`).
  Mixed ID styles build fine (precedent: `canalave_city.json`).
- Nobody but the lead touches the files in "Lead pre-work".
- Nobody adds scrcmds, or edits `src/scrcmd.c` or `asm/macros/scrcmd.inc`. If one turns out to be necessary, ask
  the lead, who serializes it.
- Every new or rewritten line uses straight `'` and `"`. Stock banks are full of U+2019. Check before committing:
  `grep -nP '[\x{2018}\x{2019}\x{201C}\x{201D}]' <your new lines>`.

---

## 5. Per-scene implementation notes

### Scene 7: Twinleaf (A)

**Mom** (`scripts_twinleaf_town_player_house_1f.s`)
- Add `InitScriptGoToIfEqual VAR_ARC1_PROGRESS, 8, 12` to the frame table in
  `scripts_init_twinleaf_town_player_house_1f.s`. There are 11 ScriptEntries today, so the new one is entry 12.
- The new ScriptEntry runs:
  1. Mom (local 0, at (7,8)) notices the player (an `ApplyMovement` with the `EmoteExclamationMark` movement macro) and faces them.
  2. Either works: no walking, which is safest because the player can enter from the door (6,10) or the stairs
     (10,3); or branch on `GetPlayerMapPos`.
  3. The 3 doc lines.
  4. Heal with the stock pattern in `TwinleafTownPlayerHouse1F_TakeAQuickRest` (`FadeScreenOut`, `SEQ_ASA`,
     `HealParty`).
  5. `SetVar VAR_PLAYER_HOUSE_STATE, 5`, then `SetVar VAR_ARC1_PROGRESS, 9`.
- Talking to Mom then heals via the stock state 5 path (`:175`).
- **Journal / Parcel:** in `TwinleafTownPlayerHouse1F_MomGiveJournal` (`:257`), after `ThatsAJournal`, skip
  `RivalsMomEnters` (`:283`): `SetVar VAR_PLAYER_HOUSE_STATE, 6`, `ReleaseAll`. The Parcel is never given, and
  `FLAG_RECEIVED_PARCEL` is no longer used by any Arc 1 gate (B re-keys Route 202).

**TV** (`TwinleafTownPlayerHouse1F_TV`, `:790`, bg events at (6,5)/(7,5))
- `GoToIfGe VAR_ARC1_PROGRESS, 8` plus `GoToIfLt VAR_ARC1_PROGRESS, 13`: show the doc's news line, with
  `SEQ_SE_DP_TV_NOISE` optional.
- Otherwise, stock.

**Garius's mom** (`scripts_twinleaf_town_rival_house_1f.s:8-19`)
- Add first: `GoToIfGe VAR_ARC1_PROGRESS, 8` gives the 3 doc lines in one message flow.
- Past-tense "his father's habit". Nobody comments on it.
- This branch replaces both the `FLAG_HAS_POKEDEX` and the `VAR_VISITED_LAKE_VERITY_WITH_RIVAL` branches, so the
  "takes after" lines are unreachable in Arc 1 (D12).

**Stock conflicts:** none on the Twinleaf map itself. `FLAG_HIDE_TWINLEAF_TOWN_RIVAL` stays set.

### Scene 8: Route 201 (A)

**`Route201_OnTransition`** (`scripts_route_201.s:26-32`)
- Replace `CallIfGe VAR_ARC1_PROGRESS, 4, Route201_Arc1HideRival` with:
  - hide at >= 4;
  - then `CallIfEq VAR_ARC1_PROGRESS, 9, <show>`: `ClearFlag FLAG_HIDE_ROUTE_201_RIVAL`, put local 2
    (`LOCALID_RIVAL`) at (112,855) facing south, with a look/stand movement type.
- The counterpart setter (`:29-40`) uses D1 (Route 201's counterpart object is never shown in Arc 1, but stay
  consistent).

**Battle trigger**
- New `coord_events[3] = {script 20, x 110, z 857, width 4, length 1, VAR_ARC1_PROGRESS, 9}`, with a new
  ScriptEntry 20 `Route201_TriggerArc1RivalBattle` appended before `ScriptEntryEnd`. There are 19 entries today
  (`scripts_route_201.s:5-23`), so the new one is entry 20.
- **Verify** in the emulator that row z857, x110-113 is the only Twinleaf-to-Route 201 crossing. Stock coord 0
  uses the same row.

**Script**
1. `LockAll`.
2. `ApplyMovement LOCALID_RIVAL, Route201_Movement_RivalNoticePlayer` (`:425`).
3. Run to the player using the existing `Route201_Arc1RivalRunToPlayerX110..113` (`:1326-1345`).
4. `SetRivalBGM`.
5. The 2 doc lines (`BufferRivalName`).
6. Branch on `GetPlayerStarterSpecies` and call `StartFirstBattle TRAINER_RIVAL_ROUTE_201_*` (copy
   `:365-380`).
7. `CheckWonBattle`:
   - loss: `ReturnToField`, `FadeScreenIn`, `WaitFadeScreen` (pattern `Route201_RivalWonLetsGoHome`, `:393`),
     then the lose line;
   - win: the win line.
8. `HealParty` (doc: "losing doesn't end the game").
9. The "10 million" line.
10. Garius runs east along rows 855/853 (reuse stock run movements) and leaves screen.
11. `RemoveObject LOCALID_RIVAL`, `SetVar VAR_ARC1_PROGRESS, 10`, `FadeToDefaultMusic`, `ReleaseAll`.

**State-8 nudge:** `Route201_TriggerArc1ToBeContinued` (script 19, coord 2) keeps its coord and its ScriptEntry
line. The text `Route201_Text_Arc1ToBeContinued` (`route_201.json:568`) changes to a go-home line (for example
"Mom must be worried sick. Better head home first."), and the player steps one tile west.

**Trainers:** unchanged (`generated/trainers.txt:851-853`, Lv 5 counter-starter, name replaced at runtime). The
in-battle defeat text in `rival_route_201_*.json` is optional (ASCII).

### Scene 9: Sandgem and the lab (B)

**Sandgem arrival** (`scripts_sandgem_town.s` `_0085`, `:40`; coord x164 z842-847, `VAR_UNK_0x4071 == 0`)
- Keep the walk-in movements (`_03AC`..).
- Replace the gender branches and the Barry burst-out (`_02B5`, `:164-185`; Barry local 3 stays hidden by
  `FLAG_UNK_0x0197`) with Ruth's doc line ("Ruth: Oh, it's you!..."). Nested quotes are ASCII.
- Keep `SetVar VAR_UNK_0x4071, 1` + `Warp MAP_HEADER_SANDGEM_TOWN_POKEMON_RESEARCH_LAB, 0, 7, 15, 0` (`:214-217`).
- **Guard:** add `GoToIfNe VAR_ARC1_PROGRESS, 10, <release>` at the top of `_0085`. That covers the save-patch
  edge cases; in normal play the coord can't be reached before 10.

**Sandgem OnTransition** (`_0032`, `:19`)
- The counterpart setter (`_0075`/`_007D`) uses D1.
- Ruth (local 4) visible at 10 (her stock position (168,845), 3 south of the lab door) and at 11 (set by the
  `_005F` reposition).

**Lab** (`scripts_sandgem_town_pokemon_research_lab.s`)
- `_003E` (OnTransition, `:22`) gets:
  - the D1 setter; today the lab has none and relies on Sandgem's;
  - `GoToIfEq VAR_ARC1_PROGRESS, 10` clears `FLAG_HIDE_ARC1_LAB_GARIUS`, otherwise sets it.
- New object 5: Garius, `OBJ_EVENT_GFX_BARRY`, at (6,6) facing north, `hidden_flag FLAG_HIDE_ARC1_LAB_GARIUS`,
  `MOVEMENT_TYPE_LOOK_NORTH` (tune near Rowan (7,5)).
- Rewrite `_01AE` (`:128`, frame script, `VAR_UNK_0x40A6 == 0`). Keep:
  - the stock walk-in to Rowan;
  - the lab BGM;
  - `GivePokedex` + `SetFlag FLAG_HAS_POKEDEX` (`:248-249`);
  - the give pose (`SetPlayerState`/`PlayerGive` as stock).
- Order:
  1. The doc lines up to "Take these", then `GivePokedex` and a "Garius received a Pokédex too" beat.
  2. Garius: "show him the rock".
  3. `RemoveItem ITEM_ECLIPSE_SHARD, 1, VAR_RESULT` plus a new message "{player} handed over the Eclipse Shard."
  4. The remaining doc lines.
  5. Garius runs out via (6,7), (7,7), then down column 7 to the warp at (7,15); `RemoveObject 5`.
  6. Ruth (local 3, `FLAG_UNK_0x0199`) says "Come with me" and leaves the way the stock assistant does.
  7. `ClearFlag FLAG_HIDE_SANDGEM_TOWN_COUNTERPART`, `SetVar VAR_UNK_0x40A6, 1`, `SetVar VAR_ARC1_PROGRESS, 11`.
- The stock nickname offer: keep it only if it's cheap. The doc doesn't need it, and the DW pick offers none.
- **Script 10300 risk:** Ruth objects in Sandgem (local 4) and the lab (local 3) have `script 10300`, the generic
  counterpart small talk (`scripts_unk_1051.s`, hardcoded "Dawn:" text). Any Ruth who stays talkable in 10-12 gets
  a new local script; set the object's `script` to a new ScriptEntry.

**Town tour replacement** (`_057C`, `:435`, Sandgem frame script, `VAR_UNK_0x4071 == 1`)
- New body: Ruth says "This way!", walks north toward Route 202 (tiles to verify: Sandgem north exit near the arrow
  sign (183,825)), the player follows with `ApplyMovement LOCALID_PLAYER`, Ruth exits north, `RemoveObject 4`,
  `SetVar VAR_UNK_0x4071, 2`.
- **TM27 is dropped** (D8), and so are the Rowan/Mart/Pokécenter tour and the `FLAG_UNK_0x02C4` Rowan.
- Handoff option A (recon 10-12): the lesson triggers from the stock coord when the player walks north. Don't
  warp-escort.

**Counterpart house** (`scripts_sandgem_town_counterpart_house_1f.s`)
- Force the sister branches (`:36-49`, `:69-86`).
- Text that says "my sister Dawn" becomes "my sister Ruth" (`sandgem_town_counterpart_house_1f.json:76/88`).
- The "big brother" variants become unreachable.

**Stock lab text with Dawn/Lucas** (msgs 7/8, 15/16, 19/20, 52/53): unreachable after the rewrite, or rewritten
where reused. Ruth's lines use a literal `Ruth:` prefix, not `BufferCounterpartName`, so they read correctly even
in a build without L2.

### Scene 10: Route 202 lesson (B)

**`_001E`** (OnTransition, `:14`)
- D1 setter.
- If `VAR_UNK_0x4087 == 0`: `SetFlag FLAG_UNK_0x0188` while progress < 11 (Ruth hidden), `ClearFlag` at 11.
- Keep the post-game `_005B` branch.

**`_00C7`** (script 6, coord x180 z825-829, `VAR_UNK_0x4087 == 0`)
- `:96`: replace `GoToIfUnset FLAG_RECEIVED_PARCEL, _027C` with `GoToIfLt VAR_ARC1_PROGRESS, 11, <pushback>`.
  - The pushback reuses `_02F4`/`_03B1` (the player steps back) with a new narration line, because Ruth isn't
    there. The doc's lab handoff makes this unreachable in normal play.
  - **Required.** Otherwise the missing Parcel softlocks the player.
- Collapse the gender branches `_019F`/`_01B2`, `_0205`/`_0211`, `_024D`/`_0259` into one Ruth path:
  1. Optional short intro (`SetCounterpartBGM`, now always The Girl).
  2. Both step west, then `StartCatchingTutorial`.
  3. "Weaken it first..."
  4. Keep `GiveItemQuantity ITEM_POKE_BALL 5` (`:140-142`).
  5. **Add** `ITEM_TOWN_MAP` x1 (D8).
  6. "Between you and me..." (the inner quote uses ASCII `"`), then "Anyway! Jubilife City is straight ahead.
     Good luck!".
- **Exit:** `_0498` (`:344`, today west 12 toward Jubilife) becomes a walk back south/east toward Sandgem
  (east about 4, then south past z830). Then `RemoveObject 3`, `SetVar VAR_UNK_0x4087, 1` (`:162`),
  `SetVar VAR_ARC1_PROGRESS, 12`.
- The demo engine needs no change: Bidoof Lv 2 vs the third starter Lv 5; Ruth's name and back sprite come from
  L2/L5. Owner note: the demo Pokémon is the starter left in the briefcase, which is acceptable.
- The post-game Poké Radar demo (`_04C4`, script 7) is untouched; it's outside Arc 1.

### Scene 11: Jubilife rally (C)

**Stock skip** (top of `_0072`, `:36`, *before* `CallIfEq VAR_JUBILIFE_STATE, 0, _00AC`)
- `CallIfGe VAR_ARC1_PROGRESS, 12, JubilifeCity_Arc1SkipStockIntro`. If `VAR_JUBILIFE_STATE` < 2, it does:
  - `SetVar VAR_JUBILIFE_STATE, 2`
  - `SetFlag FLAG_UNK_0x00F1`, `SetFlag FLAG_UNK_0x01F4`
  - `SetVar VAR_UNK_0x40E7, 2`, `ClearFlag FLAG_UNK_0x01F6`, `ClearFlag FLAG_UNK_0x01F5`
- `poketch_co_1f.s:15` only reads state >= 2 for a TV-interview flag, which is harmless.
- During Arc 1 the player can only enter Jubilife from the south, so this always runs first.
- The counterpart setter (`_00D8`/`_00E0`) uses D1, though no Ruth is visible here.

**Rally show/hide (still in `_0072`)**
- Crowd and grunts: cleared at 12 and 13, otherwise `SetFlag FLAG_HIDE_ARC1_JUBILIFE_RALLY` (D11 default: the crowd
  thins out after the scene).
- Cast: cleared only at 12, otherwise set.
- At 12:
  - Twin 3 moves out of the plaza with `SetObjectEventPos 3, ...`;
  - clown 27 (164,752, at the TV door) gets `SetFlag FLAG_UNK_0x0238`;
  - Looker 31 moves to the crowd edge with `SetObjectEventPos 31, 157, 755` / `SetObjectEventDir 31, DIR_EAST`.
- At >= 13: `ClearFlag FLAG_UNK_0x0238` and `SetFlag FLAG_UNK_0x0181` (Looker gone).

**New objects** (append; local IDs 33+; 33 objects today, cap 64 at `src/field_map_change.c:344`)

| object | gfx | position (tune in the emulator) | flag | talk |
|---|---|---|---|---|
| Garius | `OBJ_EVENT_GFX_BARRY` | (164,753), facing north, in front of the TV door (warp at (164,751)) | `_RALLY_CAST` | starts the scene |
| Cyrus | `OBJ_EVENT_GFX_CYRUS` | (175,753), facing northwest | `_RALLY_CAST` | none (or a "...") |
| grunt (flyer) | `OBJ_EVENT_GFX_GRUNT_M` | (162,752), facing south | `_RALLY` | flyer line |
| grunt 2 | `OBJ_EVENT_GFX_GRUNT_F` | (157,753) | `_RALLY` | flyer line |
| crowd ×8-10 | about 6 distinct stock human gfx (`MIDDLE_AGED_MAN/WOMAN`, `OLD_MAN`, `SCHOOL_KID_M`, `LADY`, `POKEFAN_F`, plus the existing `ACE_TRAINER_*` already in the map) | rows z753-755, x158-172, aisle at x=164 left open; `MOVEMENT_TYPE_LOOK_NORTH` | `_RALLY` | one short line each |

- Keep the avenue (z756-760) and the north corridor clear. Keep the **visible distinct gfx at about 20 or fewer**
  (stock Hearthome runs 19).
- Cyrus must exist from map load: an object added off-screen isn't drawn until it moves
  (`scripts_lake_verity.s:522-523`).

**Cutscene** (new ScriptEntry 29 = Garius's talk script)

1. Garius faces the player, then north.
2. `GetPlayerMapPos`, `AddFreeCamera`, `ApplyFreeCameraMovement` north about 3 to the TV facade, `WaitMovement`.
   This is the pattern at `scripts_lake_verity.s:512-535` and `scripts_distortion_world_giratina_room.s:198-240`.
3. `PlayFanfare SEQ_SE_DP_TV_NOISE`, a white `FadeScreen` flash, `PlayMusic SEQ_TV_HOUSOU`.
4. 3 lines from "Saros (on screen):". Camera back south.
5. Crowd turns, plus narration "The crowd murmurs."
6. The flyer grunt walks to Garius (164,752) and says "Everybody's lost somebody, kid."
7. Garius `WalkOnSpotNormalSouth`, `WaitTime` about 60. Optional narration "{rival} folds the flyer and pockets it."
8. "...What? It's just a flyer. Come on, Oreburgh's this way."
9. Camera east about 11 to Cyrus: his line, he walks north into the Route 204 corridor, `RemoveObject`.
10. Camera back, `RestoreCamera`.
11. Garius runs east along z757 off-screen, `RemoveObject`.
12. `FadeToDefaultMusic`, `SetVar VAR_ARC1_PROGRESS, 13`.

**Looker cameo**
- At the top of `_0954` (`:756`): `GoToIfEq VAR_ARC1_PROGRESS, 12` gives "Man in a Trench Coat: Hm. Hm hm..." and
  `ReleaseAll`.
- Optional: put it in the cutscene as an aside. The doc marks it optional.

**Banner "WHO DID YOU LOSE?"**
- Signboard 14 (167,755), script 26 → `_1096` (`:1335`): at 12-13, branch to a sign message "WHO DID YOU LOSE?"
  (`ShowScrollingSign` or a plain message).
- A real banner prop is art (out of scope).

**East block:** new coord at x188 z757-760, value 12: "Garius: Hey! Over here, by the TV!", then the player steps
1 west. It overlaps stock coords 2 and 5, which key on other vars; that's fine.

**North gate (D13):** new coord at value 16 on the north-exit row. The stock grunt coord 1 uses x173 z743 w3;
**verify** that row is airtight with `/tmp/act1p2/recon1012/render2.py`. Text "To be continued...", then step
south 1.

**Post-Gym stock (owned by D):** nothing for C to do, but C must not re-arm `VAR_JUBILIFE_STATE 3`.

### Scene 12: Route 203 (C)

**`_0085`** (`:39`)
- msg 0 becomes "Hey! I caught two more Pokémon already. Rematch! Right now!"
- Keep the 3 starter branches and `StartTrainerBattle TRAINER_RIVAL_ROUTE_203_*`.
- Win path:
  1. "...Hey. That Eclipse guy on the screen..."
  2. `ShowYesNoMenu VAR_RESULT`: Yes/No replies.
  3. "Forget it. Race you to Oreburgh!"
  4. Stock run east, `RemoveObject 5`, `SetVar VAR_UNK_0x4088, 1` (`:128`), `SetVar VAR_ARC1_PROGRESS, 14`.
- Loss: stock `BlackOutFromBattle` (`:133`, D9).
- Trainer JSONs: D10 team. Edit only the party; replace any curly apostrophes in the battle messages you touch.

### Scene 13: Oreburgh City and the mine (D)

- **Stock chain kept as is:**
  - Youngster `_03F8` (coord 0, state 0)
  - Garius at the Gym door (local 3, `_005A`, `FLAG_UNK_0x017C`)
  - Roark in B2F `_0016`
  - the Gym
- **Text:**
  - `oreburgh_city.json` #0 dad line (D12).
  - No-HM rewording: `oreburgh_mine_b2f.json` #0-1 (keep the `ScrCmd_29E 2` rock-smash animation, since it's his
    own Pokémon), `oreburgh_city_gym.json` #3 `OreburghGym_Text_RoarkExplainCoalBadge`, `oreburgh_city.json` #21
    (Battle Girl, `_0634`, `:509`).
  - Nothing may promise HM use.
- **Entrance miners:**
  - Objects 28/29 `OBJ_EVENT_GFX_WORKER` at (299,793) `LOOK_EAST` and (305,793) `LOOK_WEST`, y 3, flag 0.
  - New ScriptEntries 23/24, stock talk pattern, the 2 doc lines.
- **Sealed bay in B2F:**
  - Objects 11-13 `OBJ_EVENT_GFX_ROCK_SMASH` (or `STRENGTH_BOULDER`) at (8,15), (9,15), (10,15), y 0,
    `FLAG_HIDE_ARC1_MINE_SEAL`.
  - A custom talk script (not 10001): "The tunnel's been sealed off with rubble. ...From somewhere beyond it, a
    faint crying."
  - **Verify** in a screenshot that the NW bay reads as a tunnel mouth. If not, pick another dead end and report
    it.
- **Ravaged Path** (`scripts_ravaged_path.s` `_0006`, the OnTransition):
  - if `FLAG_TOTEM_HITMONLEE_DEFEATED` is unset: `SetFlag FLAG_HIDE_TOTEM_HITMONLEE` while `VAR_ARC1_PROGRESS` < 17,
    else `ClearFlag`;
  - the totem is local 31 at (19,45).

### Scene 14: after Gym 1 (D)

**Gym** (`OreburghGym_Roark`)
- Delete `:34` (`VAR_JUBILIFE_LOOKER_PALPAD`) and `:37-40` (`VAR_JUBILIFE_STATE 3` + 3 `ClearFlag FLAG_HIDE_JUBILIFE_*`).
- Keep `:32-33`, `:35` (`VAR_OREBURGH_STATE 2`) and `:41` (`FLAG_UNK_0x0198`, which hides the lab Rowan).
- Add `SetVar VAR_ARC1_PROGRESS, 15` after `:35`.

**City frame script**
- `scripts_init_oreburgh_city.s` gets `InitScriptEntry_OnFrameTable` + `InitScriptGoToIfEqual VAR_ARC1_PROGRESS, 15,
  25`. That's new ScriptEntry 25 (23/24 are the miners). Precedent: `scripts_init_canalave_city.s`.
- The script:
  1. `LockAll`, `PlayFanfare SEQ_SE_DP_WALL_HIT2`, `ShakeCamera 24, 4` (precedent `scripts_lake_verity.s:408-409`).
  2. Runner miner (object 30, `WORKER`, `FLAG_HIDE_ARC1_OREBURGH_RUNNER`): `ClearFlag`, `SetObjectEventPos` about
     (292,758), `AddObject`, run west to the player (who stands at (282,757) after the door). Pattern `_00D7`,
     `:77-123`.
  3. "The sealed tunnel! It's glowing!"
  4. `RemoveObject 30`, `SetVar VAR_OREBURGH_STATE, 3`, `FadeScreenOut`,
     `Warp MAP_HEADER_OREBURGH_MINE_B2F, 0, 12, 17, DIR_WEST`, `FadeScreenIn`.

**B2F init** (`scripts_init_oreburgh_mine_b2f.s`, empty today)
- `InitScriptEntry_OnTransition 6` + `InitScriptEntry_OnFrameTable` with
  `InitScriptGoToIfEqual VAR_ARC1_PROGRESS, 15, 7`. Precedent `scripts_init_lake_verity.s:4-16`.
- OnTransition (new entry 6):
  - D1 setter;
  - < 15: seal shown, the rest hidden;
  - == 15: seal hidden, cast + rift shown, silhouette hidden (it appears in the scene);
  - >= 16: everything hidden.

**Cast** (append 14+)

| who | gfx | where | notes |
|---|---|---|---|
| Garius | `BARRY` | (9,16), facing north | already there |
| Rowan | `PROF_ROWAN` | starts around (15,13) in the north shaft | walks to row 17 |
| Ruth | `COUNTERPART` (D1 via the setter) | behind Rowan | |
| rift | E's `ARC1_RIFT`, else omitted | (9,15) | `FLAG_HIDE_ARC1_MINE_RIFT` |
| silhouette | E's `ARC1_HITMONLEE_SHADOW`, else `TOTEM_HITMONLEE` | (9,14) | `FLAG_HIDE_ARC1_MINE_SILHOUETTE` |
| Roark | **reuse local 0** | | `ClearFlag FLAG_UNK_0x018A`, `SetObjectEventPos 0`, `AddObject 0`, walk in from the shaft; `RemoveObject 0` at the end |

**Scene** (new entry 7, about 17 doc lines, gender-neutral)
1. Rowan and Ruth arrive.
2. "Another one."
3. Roar: `PlayCry SPECIES_HITMONLEE` + `ShakeCamera` + show the silhouette about 30 frames + flash, then remove it.
4. The Giratina blip (D11).
5. Garius "GIANT Hitmonlee?!"
6. Rowan's 3 totem lines, then the Ruth/Rowan/Garius/Rowan/Rowan exchange.
7. Rift shudders: short `ShakeCamera`, flash, `RemoveObject` rift.
8. Ruth "...Route 204", Rowan "It's waiting."
9. Roark's 2 lines.
10. Rowan "one person...", Garius "Spacesuit guy?", Rowan "...Find him. Bring him to me."

**End**
1. `FadeScreenOut`.
2. `RemoveObject` the cast and Roark.
3. `SetVar VAR_ARC1_PROGRESS, 16`.
4. `FadeScreenIn`.
5. Message "END OF ARC 1\nTo be continued..." (precedent `Route201_Text_Arc1ToBeContinued`).
6. `ReleaseAll`.
7. Music: `FadeToDefaultMusic`. Don't use `PlayBattleMusic SEQ_BATTLE_TOTEM` outside a battle; it's untested.

The player stays in B2F at (12,17) and walks out normally.

---

## 6. Test plan

### Harness (lead, L7): `/tmp/act1p2/harness/a1p2emu.py`

- Based on `/tmp/arc1/lead/arc1emu.py`: `Arc1Emu`, `var`/`set_var`/`map_id`/`ppos`, symbols `sSaveDataPtr`/`sFieldSystem`
  from the build's `main.nef.xMAP`. Copy the ROM and the xMAP **together**.
- Uses `/tmp/arc1/dw/dwemu.py` `make_save()` for file-based patching: location, player object, vars, flags,
  `fix_crc`. **Pass `dw_features=False`** for non-DW maps.
- Adds:
  - `flag_id(name)`: the 0-based line index in `generated/vars_flags.txt`. The stub in dwemu is broken (`:35-39`).
  - `boot_state(rom, xmap, map, x, z, dir, vars, flags)`: make_save from the golden save, boot, Continue, dismiss
    the journal.
  - `graft_party(src_sav)`: copy the party count + 6 × 236-byte party records from
    `tools/battle_stage/emu/saves/eterna_forest_grass.sav` (Lv 29 team) into the patched save, then `fix_crc`. Used
    for the Roark and Route 203 win tests.
  - `faint_party_to_1hp()`: optional, for the Route 201 loss path. The alternative is a weak party graft.
- `.dst` savestates are build-specific. Checkpoint with exported `.sav` files only.

**Golden save** (`golden_s8.sav`)
1. Use the L1-L5 ROM.
2. Fix `/tmp/arc1/lead/flow.py`:
   - stage 4 still has the DW steps from before commits `439457f028` and `85549c4e00`;
   - stage 5 got stuck at Lake Verity (38,32) in the last run;
   - its "reached" check must assert that the var and the "To be continued" text actually happened.
3. Run stages 0-5 to state 8 and export the save (`emu.py` save export).
4. Record the starter species in `golden_s8.json`.

### Per-stream checks

Each stream:
1. Builds in its worktree (`make release`).
2. Copies `out/dazzlingPlatinum.nds` + `build/main.nef.xMAP` to `/tmp/act1p2/<stream>/`.
3. Runs its section 4 acceptance list with `boot_state`.
4. Takes screenshots at every beat into `/tmp/act1p2/<stream>/shots/` and builds a contact sheet
   (`emu.contact_sheet`).
5. Checks for hangs: `controllable()` returns within N frames after each scene.
6. Asserts each final `VAR_ARC1_PROGRESS` and stock var from section 3.2 with `var()`.

Battle scenes are tested for **both** win and loss where the doc allows a loss (Route 201, Route 203).

Fast-forward recipes (map, x, z, vars, flags):

| target | patch |
|---|---|
| scene 7 | golden save as is (state 8), standing at Twinleaf (in front of the house) |
| scene 8 | `VAR_ARC1_PROGRESS=9`, `VAR_PLAYER_HOUSE_STATE=5`, Twinleaf just south of Route 201 |
| scene 9 | `=10`, `MAP_HEADER_ROUTE_201` (150,843) |
| scene 10 | `=11`, `VAR_UNK_0x40A6=1`, `VAR_UNK_0x4071=2`, `FLAG_HAS_POKEDEX`, `FLAG_HIDE_SANDGEM_TOWN_COUNTERPART`, Sandgem north (183,830). The shard doesn't need removing. |
| scene 11 | scene 10 patch + `=12`, `VAR_UNK_0x4087=1`, `MAP_HEADER_ROUTE_202` (174,800) |
| scene 12 | `=13`, `VAR_JUBILIFE_STATE=2`, Jubilife (186,758) |
| scene 13 | `=14`, `VAR_UNK_0x4088=1`, Oreburgh (259,749), `graft_party` |
| scene 14 | `=15`, `VAR_OREBURGH_STATE=2`, Coal Badge (play the Roark battle with `graft_party`, or stand in the Gym at 15 after a real win), then walk out |

### Final end-to-end (lead, L11)

One run with the merged ROM:
1. **New game** (checks the Garius default and the new intro).
2. flow.py stages 0-5 to state 8.
3. New stages 6-13, one per scene, each ending on a `VAR_ARC1_PROGRESS` assertion and a contact sheet:
   1. home and the Mom scene (9)
   2. Route 201 battle, win (10)
   3. Sandgem lab (11)
   4. Route 202 lesson (12)
   5. Jubilife rally (13)
   6. Route 203 (14)
   7. Oreburgh: escort, mine Roark meeting, Gym. The Gym battle may use `graft_party` **once**; log it as the only
      patched step.
   8. Mine rift and END card (16)
4. Then walk to Jubilife's north exit: "To be continued", step back.
5. Visit Ravaged Path: no totem.

Expected runtime is about 20 minutes (part 1 took about 8-9). Checkpoint at each stage with exported `.sav`.
Extra assertions:
- no "Dawn"/"Lucas"/"Barry"/"Galactic" on screen in Arc 1. Use a text dump, or grep every message the new scripts
  reference;
- `ITEM_PARCEL` never in the bag; `ITEM_ECLIPSE_SHARD` gone after 11; `ITEM_TOWN_MAP` present after 12.

---

## 7. Risks and estimates

### Risks (top first)

1. **Softlocks from stock gates.**
   - The Parcel gate (`route_202.s:96`).
   - The Sandgem frame tour (`VAR_UNK_0x4071==1`).
   - The Jubilife state 0/1 chain.
   - The Gym's Galactic chain.
   - Section 3.2 is the checklist, and every stream's acceptance tests walk the next map's entry.
2. **Index shifts.** Deleting a ScriptEntry, object or message silently rewires coords, objects and `Message N`. Only
   append (section 4 rules).
3. **Hide-flag semantics.** `RemoveObject` sets the object's own flag. Objects added off-screen aren't drawn until
   they move. Cast objects must exist at map load.
4. **Ruth talk script 10300.** It shows hardcoded "Dawn:" small talk on any talkable stock counterpart object (B).
5. **Placeholder sprite D1.** `DP_PLAYER_F` has never been shown on a stock map. L6 smoke-tests it before the streams
   depend on it; the fallback is `SCIENTIST_F`.
6. **Jubilife object and gfx budget.** About 47 objects; keep the visible distinct gfx at about 20 or fewer.
   Free-camera pans across a busy plaza. Test on screen early, crowd before cutscene.
7. **Reachability assumptions** need the emulator: Route 201 row z857, Sandgem x164, Route 202 x180, Jubilife x188 /
   north row, Route 203 x196. Each owning stream verifies its own map.
8. **Harness staleness.** flow.py stage 4/5 are broken today (infra recon). L7 blocks the end-to-end, not the
   streams: streams can test from patched saves.
9. **Text.** Curly quotes from copied stock lines break the build. Watch line widths, the "Pokémon" e-acute, and
   gender-neutral wording (the player can be either gender, and no line assumes which).
10. **Worktrees.**
    - Each needs the ignored `subprojects/` downloads (324 MB). Symlink each ignored entry
      (`git -C /data/repos/dazzlingPlatinum status --ignored --porcelain subprojects`), or `cp -al`. Don't let meson
      re-download.
    - About 1 GB each; the disk has 70 GB free (91% used).
    - Build with `make release` only, never plain `make`.
11. **Existing saves keep "Barry".** Always test from a new game or the golden save.

### Estimates

| stream | content | size |
|---|---|---|
| Lead pre-work L1-L8 | flags, names, 2 C one-liners, common script, smoke test, harness + golden save | M (half a day; the golden save is most of it) |
| A Home | parity text, Mom/TV/Garius's mom, Route 201 nudge + battle | M (about 1 day) |
| B Sandgem | door, lab rewrite, tour replacement, Route 202 lesson, family text | M-L (1-1.5 days) |
| C Jubilife | stock skip, 14 objects, 2-camera cutscene, about 25 messages, east/north gates, Route 203 | L (about 2 days, including position tuning) |
| D Oreburgh | miners, seal, Gym edits, frame scene, B2F scene (17 lines, 6 actors), totem gate, text rewording | M-L (about 1.5 days) |
| E Field sprites (optional) | 2 placeholder overworld objects via the existing pipeline | M (about 1 day) |
| Lead post-work L9-L11 | docs, merges, end-to-end, push | M |

Critical path: L (golden save), then C. A, B, D and E start right after the L1-L5 commit; none of them needs
another stream's code to build. They depend on each other only through ladder values, which patched saves cover.
