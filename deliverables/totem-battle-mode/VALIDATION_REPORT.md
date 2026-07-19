# Totem Battle Mode Validation Report

**Author:** Manus AI

**Date:** 2026-07-19

**Branch:** `feature/totem-battle-mode`

**Base:** `7ad48e3ff8f807fc129083fdf515f4a8434651a2`
**Status:** Validated

## Executive Summary

Totem Battle Mode is implemented for all eight scripted Totem encounters. Each battle starts with a dedicated Totem status marker, uses a fixed doubles-capable topology with only one player battler active, applies exactly one stage of Attack, Defense, Speed, Special Attack, and Special Defense to the Totem before command selection, and can summon at most two configured allies at completed turn boundaries.[1] [2] [3] [4]

The integrated feature passed a clean compile and link, a deterministic ten-contract source validator, native Platinum save verification, and a four-turn DeSmuME lifecycle test. The live sequence showed **Combee** as Vespiquen’s first ally, **Beautifly** replacing it after it fainted, no third summon after Beautifly fainted, and a clean return to the overworld after Vespiquen was defeated.[5] [6] [7] [8] [9]

## Implemented Behavior

The field scripts now launch Totems through `StartTotemBattle` with one of eight stable encounter IDs. The constructor creates a three-member enemy party, enables the static doubles topology, and marks the battle with `BATTLE_STATUS_TOTEM`; ordinary wild, legendary, trainer, and double battles remain on their existing paths.[1] [2] [3]

| Runtime rule | Validated behavior |
|---|---|
| Opening boost | Totem receives +1 Attack, Defense, Speed, Special Attack, and Special Defense exactly once before turn 1. Accuracy and evasion are untouched. |
| Player topology | Player battler 2 remains permanently inactive and never requests a command. |
| First summon | If the Totem survives a completed turn without an active ally, enemy party slot 1 is sent out. |
| Replacement summon | If ally 1 faints while the Totem survives, enemy party slot 2 is sent out at that turn’s end. |
| Living-ally gate | No summon occurs while enemy battler 2 has HP. |
| Summon cap | Exactly two successful summons are permitted; no third ally appears. |
| Totem defeat | Totem KO produces victory immediately, regardless of unsummoned party data or an active ally. |
| Player defeat | Zero usable player-party HP follows the normal loss path. |

The intro reuses the canonical five-stat boost subscript with `BATTLER_ENEMY_1` as the side-effect target. Ally activation reuses the established switch/update, send-out, health-bar, entry-hazard, and faint-on-entry battle-script operations.[4] [5] [6]

## Encounter Roster

The roster is centralized in one bounds-checked table. Every record contains one Totem and exactly two ordered allies.[1] [2]

| Encounter | Totem | Level | First ally | Level | Second ally | Level |
|---|---|---:|---|---:|---|---:|
| Hitmonlee | Hitmonlee | 20 | Meditite | 18 | Machop | 18 |
| Vespiquen | Vespiquen | 25 | Combee | 23 | Beautifly | 23 |
| Spiritomb | Spiritomb | 30 | Misdreavus | 28 | Haunter | 28 |
| Skarmory | Skarmory | 35 | Gligar | 33 | Magneton | 33 |
| Lapras | Lapras | 36 | Mantyke | 34 | Shellos | 34 |
| Aggron | Aggron | 42 | Lairon | 40 | Graveler | 40 |
| Mamoswine | Mamoswine | 44 | Snover | 42 | Sneasel | 42 |
| Kingdra | Kingdra | 50 | Seadra | 48 | Lanturn | 48 |

## Validation Results

The static validator passed all ten contracts. It checks constants and status-bit uniqueness, all eight roster records, all eight field call sites, constructor and build registrations, inactive battler topology, the exact opening boost, summon-gate ordering and cap enforcement, ally send-out behavior, Totem-specific battle results, and repository artifact hygiene.[7]

| Validation layer | Result | Evidence |
|---|---|---|
| Python compilation | Pass | `build_totem_mode_test_save.py` and `validate_totem_battle_mode.py` compile successfully. |
| Shell syntax | Pass | Runtime and encounter capture harnesses pass `bash -n`. |
| Source contracts | Pass | `10/10` deterministic contracts. |
| Clean compile/link | Pass | ARM9, scripts, resources, and final NDS image generated successfully. |
| Baseline checksum suite | Expected mismatch | The repository’s vanilla Platinum SHA-1 tests reject any intentionally modified ROM; no compiler, assembler, or linker error occurred. |
| Native save load | Pass | Both general and storage blocks in both save partitions validate; `native_main_load_result=OK`. |
| Emulator lifecycle | Pass | First summon, second replacement, cap exhaustion, Totem KO, and overworld return observed in one clean-ROM run. |
| Branch hygiene | Pass | No ROM, save, DSV, log, archive, or Python bytecode artifact is part of the source delta. |

The deterministic fixture builder preserves the adjacent field position, decrypts and re-encrypts the lead PK4 correctly, reduces the party to one durable level-100 lead, installs Splash and Aerial Ace for controlled turn passing and targeted KOs, clears the selected Totem outcome flags in both partitions, and refreshes the native checksums.[8]

## Clean Runtime Scenario

The final run used the freshly clean-built ROM and a freshly generated Vespiquen fixture. The four milestones were visually reviewed as follows.[9]

| Turn | Action | Expected transition | Observed result |
|---:|---|---|---|
| 1 | Splash | Summon party slot 1 | Combee appeared; both enemy sprites and health bars rendered; command selection resumed. |
| 2 | Aerial Ace on Combee | Vacate ally slot, then summon party slot 2 | Combee fainted; Beautifly appeared in the reused slot; command selection resumed. |
| 3 | Aerial Ace on Beautifly | Exhaust two-summon cap | Beautifly fainted; no third appearance occurred; Vespiquen continued alone. |
| 4 | Aerial Ace on Vespiquen | Totem victory | Vespiquen fainted and the game returned cleanly to Eterna Forest. |

The final milestone sheet also confirms that player battler 2 never renders, enemy battler 2 is reused safely, and no inactive-slot graphical corruption is present.

## Artifact Integrity

| Artifact | SHA-256 |
|---|---|
| Clean-built `pokeplatinum.us.nds` | `99bb0c1c59c5910dd8a347ccb85aa9ddd96e9846a25cf9779e600812e32d9cab` |
| Controlled Vespiquen raw save | `7d4f13826a5a3a3a38a48f343c8b4ac59c95ac0475f54087f869c2723441c116` |
| First-summon contact sheet | `00dc9dd6946bb78d4b3efb206f069e0a114ba41f253a3ee4b129e2154aa09c7a` |
| Second-summon contact sheet | `4871638d089539d2f64f632654baf4e0f1d8c73d265d74c5f65bdd6b8bae5096` |
| Summon-cap contact sheet | `01b790148dbbb69462b4af206c7d537e48a9ddceb129659d24df1ec084dce242` |
| Totem-victory contact sheet | `eb5e74f1d267804043d4793df5eb0180d2cd1cce68a5b299696168ccee119237` |
| Consolidated milestone sheet | `abf3f28bdcbedda95439f29237d00ccbc3183a4cf9551c124e7b4422241b9748` |

## Reproduction

The source contracts can be rerun with:

```bash
python3 tools/validate_totem_battle_mode.py
```

After building the ROM, a controlled fixture and the full emulator evidence can be regenerated with:

```bash
python3 tools/build_totem_mode_test_save.py \
  --species vespiquen \
  /path/to/adjacent-vespiquen.sav \
  /tmp/vespiquen-controlled.sav

tools/validate_totem_battle_mode_runtime.sh \
  build/pokeplatinum.us.nds \
  /tmp/vespiquen-controlled.sav \
  /tmp/totem-runtime-evidence \
  Right
```

The runtime harness requires DeSmuME, Openbox, `xdotool`, and ImageMagick and deliberately requires its output directory to be outside the repository.[9]

## References

[1]: ../../include/constants/totem_battle.h "Totem encounter constants"
[2]: ../../src/totem_battle.c "Totem encounter data and topology helpers"
[3]: ../../src/encounter.c "Totem encounter constructor"
[4]: ../../res/battle/scripts/subscripts/subscript_start_encounter.s "Totem encounter intro and opening boost"
[5]: ../../src/battle/battle_controller_player.c "Totem participation, summon gate, and battle-result behavior"
[6]: ../../res/battle/scripts/subscripts/subscript_totem_summon_ally.s "Totem ally send-out sequence"
[7]: ../../tools/validate_totem_battle_mode.py "Deterministic source-contract validator"
[8]: ../../tools/build_totem_mode_test_save.py "Deterministic Totem runtime save builder"
[9]: ../../tools/validate_totem_battle_mode_runtime.sh "Four-turn emulator lifecycle harness"
