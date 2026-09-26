# Emulator critic harness

Headless DeSmuME (py-desmume) scripts that play the ROM, save frames and
labelled contact sheets, and write a PASS / WARN / FAIL report. A reviewer (a
person, or an agent that can read images) uses that output to judge a build of
the Living 3D Battle Stage work without opening an emulator.

| file | what |
|---|---|
| `emu.py` | library: the `Emu` class (boot, input, touch, pixel state detection, battle helpers, RAM scans) plus image helpers (`contact_sheet`, `dedupe`, `diff_fraction`, `looks_broken`) |
| `critic.py` | runs the scenarios and writes the report |
| `make_save.py` | edits a raw .sav (position, party, heal, moves); also `--info` |
| `saves/eterna_forest_grass.sav` | the save every scenario boots |

## Running it

```sh
cp out/dazzlingPlatinum.nds /tmp/critic_rom.nds      # optional; see the note on copies below
SDL_VIDEODRIVER=dummy ~/.venvs/desmume39/bin/python tools/battle_stage/emu/critic.py \
    /tmp/critic_rom.nds /tmp/bs_critic                              # default scenario set
SDL_VIDEODRIVER=dummy ~/.venvs/desmume39/bin/python tools/battle_stage/emu/critic.py \
    out/dazzlingPlatinum.nds /tmp/bs_critic --scenario wild_battle move_tester --moves 1,57,89
SDL_VIDEODRIVER=dummy ~/.venvs/desmume39/bin/python tools/battle_stage/emu/critic.py \
    /tmp/critic_rom.nds /tmp/bs_stage --scenario stage_ab switchbg_moves bag_party debug_views
```

- Use the Python 3.9 venv. `~/.venvs/desmume` (3.12) fails to load DeSmuME with a libglib error.
- Write the output to `/tmp` or another path outside git. Nothing under
  `tools/battle_stage/emu` is written at run time.
- Each scenario copies the ROM to a unique temp file itself, so running on
  `out/dazzlingPlatinum.nds` directly is safe. Copying the ROM first protects
  against a rebuild in the middle of a run.
- Exit status 1 means at least one check FAILed.

Options:

| option | default | meaning |
|---|---|---|
| `--scenario A B ...` | boot wild_battle quick_battle move_tester stage_toggle | scenarios to run |
| `--sav` | `saves/eterna_forest_grass.sav` | save to boot |
| `--moves` | 1,52,53,57,85,89,94,104,144,164,326,332,399,63 | move_tester move IDs (the line in `generated/moves.txt`, minus 1) |
| `--reverse` | off | move_tester also plays each move enemy->player (Y) |
| `--anim-frames` | 1200 | move_tester / stage_toggle / switchbg_moves: longest wait for one animation to end |
| `--max-anim-frames` | 1800 | wild_battle: longest recording of the FIGHT turn |
| `--bgs` | 0,1,29 | quick_battle background entries (0..30) |
| `--stage-terrain` | plain | platforms of the Plain background battle the 3D stage scenarios use: `plain` (quick-battle entry 01) or `grass` (entry 30) |
| `--species-steps` | 0 | quick_battle: RIGHT presses (species) before the first battle |
| `--timeout` | 900 | seconds before a scenario's process is killed |
| `--verbose` | off | show DeSmuME's own stdout |

### Runtimes

Measured on the devserver against the 2026-09-25 15:16 ROM. The emulator runs at about 270 fps.

| scenario | time |
|---|---|
| boot | 6 s |
| wild_battle | 20 s |
| quick_battle (default `--bgs 0,1,29`) | 22 s, about 7 s per battle |
| totem_battle | 12 s |
| debug_party | 7 s |
| move_tester | about 10 s of setup, 2-4 s per move, then 10 s for the two turns after the tester (55 s with the 13 moves in `--moves 1,19,33,52,57,85,89,91,94,126,242,337,382`) |
| stage_toggle | 15 s |
| stage_ab | 13 s |
| switchbg_moves | 23 s |
| bag_party | 18 s |
| debug_views | 13 s |
| default set (boot, wild_battle, quick_battle, move_tester, stage_toggle) | 78 s |

## Output

```
<outdir>/report.md                 summary table, every check with its detail, notes, sheet paths
<outdir>/report.json               the same, machine readable
<outdir>/<scenario>/sheet_*.png    contact sheets; every cell is labelled "label @frame"
<outdir>/<scenario>/frames/<sheet>/NNNNNN_label.png   the full-size frames of each sheet
<outdir>/<scenario>/console.log    the scenario's full stdout, including DeSmuME's
<outdir>/<scenario>/result.json    that scenario's checks
```

Contact sheets show both screens (256x384) unless the title says top only. They are deduplicated: identical consecutive frames are dropped, so a long pause shows up as a jump in the `@frame` numbers.

## Scenarios and their checks

Every scenario boots from the save and adds two checks at the end:

- **no CPU exceptions in the emulator log**: DeSmuME's log is searched for `Undefined instruction`, `Data abort`, `Prefetch abort` and similar lines.
- **scenario process exited cleanly**: this check is added only if the process crashed or timed out.

| scenario | what it does | checks |
|---|---|---|
| `boot` | title screen -> Continue -> journal -> overworld; turns left and right | booted to overworld (the Poketch is on the bottom screen); screens are not black or garbage; the overworld responds |
| `wild_battle` | walks the grass until an encounter; records the intro; FIGHT with False Swipe, recorded every 3 frames; bag round trip (opens the HP/PP pocket); RUN | wild encounter; battle menu reached; screens sane; not frozen at the menu; FIGHT opened the move list; the move animation played (at least 10 distinct frames); the menu came back after the turn; bag opened / closed; **battle scene intact after the bag**: the top screen is compared with 12 idle frames taken before the bag (PASS at 2% or less, WARN up to 8%, FAIL above that, with a diff image); returned to the overworld and it is not frozen |
| `quick_battle` | for each `--bgs` entry: holds L+R in the field, moves the selector the short way (DOWN +1, UP -1, both wrap), presses A (wild battle), records the transition and intro, then runs | L+R panel opened; the panel responds to the d-pad; L+R+A started a battle (if not: the player can still turn and the panel reopens, otherwise the scenario stops there); battle menu reached; screens sane; not frozen; returned to the overworld |
| `totem_battle` | not in the default set. L+R+X on entry 0: Totem doubles | L+R+X started a battle; battle menu reached; screens sane. Totem battles cannot be fled, so the scenario ends in battle |
| `debug_party` | not in the default set. L+R+START in the field | the party in RAM changed (Key Stone and a Lv50 Mega mon); still in the overworld |
| `move_tester` | wild battle, then at the command menu: hold L+R (overlay "Move NNN: name"), step to each move (UP/DOWN +-10, RIGHT/LEFT +-1), A (Y with `--reverse`), release L+R, record every 3 frames until the overlay hides (that is when the animation ends) | overlay shown; **animation drew something**: the scene, with the healthbar boxes masked, differs by more than 0.3% from idle; the animation finished (overlay hidden) within `--anim-frames`; the battle text is restored 90 frames later; if not, the command menu still responds (touching FIGHT opens the move list). Then a real turn: FIGHT -> False Swipe plays and the menu comes back; the tester again on turn 2 (Pound: drew, finished, text restored), when the AI picks its move while the menu is already up; a second real turn; run away |
| `stage_toggle` | Plain quick battle (the save's Eterna Forest battle has no arena to toggle); L+R overlay; SELECT twice (3D stage ON <-> OFF). After each SELECT: release, snapshot the scene, then play Pound | SELECT changed the overlay text; screens sane after each toggle; battle text restored; Pound finished; battle text restored 90 frames after Pound, or the menu still responds; two SELECTs restore the original ON/OFF text (WARN); command menu responds; run away |
| `stage_ab` | not in the default set. Quick battle entry 01 (Plain background and terrain). 24 idle frames with the stage in its initial state (ON), L+R+SELECT, 24 idle frames in the toggled state (OFF), L+R+SELECT back | SELECT changed the overlay text (both times); **stage ON matches the classic look**: on the best-aligned ON/OFF pair of the top screen it reports the mean and max pixel difference and the share of pixels differing by more than 24. FAIL above 5% or a mean of 12, WARN above 0.5% or a mean of 2. The scene-only numbers (HUD masked) are a note. `stage_ab_heatmap.png` is ON / OFF / heat, and `sheet_ab_pair` shows the pair; command menu responds; run away |
| `switchbg_moves` | not in the default set. Quick battle entry 01, stage in its default (ON) state. In the move tester: Night Shade (101), Psychic (94), Dark Pulse (399) and Acid Armor (151), each recorded every 3 frames | per move: **special background shown mid-animation**: the peak share of the scene (HUD masked) that differs from the frame just before the move is at least 25% (1% for Acid Armor, which moves the battler onto BG2); the animation finished; **normal look restored** 90 frames later, against the idle frames from before the tester (PASS at 2% or less, WARN up to 8%); battle text restored; then the command menu responds and the battle is fled |
| `bag_party` | not in the default set. Quick battle entry 01. Bag (opens the HP/PP pocket) and back with B, then POKEMON (the party screen) and back with B | bag / party opened (the bottom screen settled on a new, lit screen); screens sane inside each; closed back to the menu; **top screen unchanged after the bag / party** against 12 idle frames from before (PASS at 2% or less, WARN up to 8%, with a heatmap above 2%); command menu responds; run away |
| `debug_views` | not in the default set. Quick battle entry 01. Holds L+R and taps B four times (views 1, 2, 3, then back to 0), 40 frames after each | views 1-3 each differ from view 0 in more than 2% of the scene (HUD masked); views 1-3 not blank or black (brightness 12 or more, not flat or noisy); the fourth tap wraps back to view 0 (WARN); `sheet_views` shows all five; command menu responds; run away. Needs the renderer's L+R+B combo and the arena. Without them every "differs" check FAILs with "L+R+B changed nothing" |

The last four check the Living 3D Battle Stage compatibility hooks (see `docs/living_battle_stage/compat.md`). Until the arena is drawn, `stage_ab` reports a difference of about 0 and `debug_views` FAILs.

When the debug combos are missing, `quick_battle`, `move_tester` and `stage_toggle` report a single FAIL ("holding L+R changed nothing ... not in this ROM") and move on. So do the four stage scenarios. That happens when the ROM lacks the feature or the save uses the "L=A" button mode.

## How a critic agent should use this

1. Run the scenarios that touch the change under review, then read `<outdir>/report.md`.
2. Treat a FAIL as a real finding: a hang, crash, soft lock, garbage screen, or a combo that did nothing. Each check's detail names the frame counts. The matching sheet shows what the screen looked like.
3. Automatic checks prove only that the game kept running, reached the expected screens and drew something. Judge the rest by opening the sheets listed under each scenario: sprite placement and scale, animation quality, palettes, whether the 3D stage looks right, and text. Open the full-size PNG in `frames/<sheet>/` for detail.
4. When you report, cite the sheet path and the `label @frame` of the cell you mean. Rerun a single scenario with `--scenario X` to confirm a fix.
5. Encounters, time of day and RNG follow the host clock (see gotchas). Do not treat a different wild species or a different background palette between runs as a regression.

Using the library directly (for a one-off probe):

```python
import sys; sys.path.insert(0, "tools/battle_stage/emu")
from emu import Emu, contact_sheet
with Emu("out/dazzlingPlatinum.nds", "tools/battle_stage/emu/saves/eterna_forest_grass.sav") as e:
    e.boot(); e.walk_until_battle(); e.wait_battle_menu()
    frames = e.record(300, every=5, label="idle")
    contact_sheet(frames, "/tmp/probe.png", "idle at the command menu")
```

Only one `Emu` can exist per process; a second one segfaults. Run each probe in its own process.

## The save

`saves/eterna_forest_grass.sav` puts the player in Eterna Forest (map 203) at (74, 47), in tall grass, facing down.

- Party: Finneon Lv29 and four other mons around Lv29, all fully healed.
- The lead's move slot 3 is False Swipe. It is a damaging move that never KOs, so the battle can continue to the bag and RUN steps.
- The Vespiquen totem is nearby. The harness only paces up and down in the grass and never walks into it.
- `make_save.py`'s docstring has the exact command used to make the save. The source saves were scratch copies of the user's saves.
- Use `make_save.py SAV --info` to inspect a save.

Boot from a `.sav`. Savestates (`.dst`) break on every rebuild.

The repo's `.gitignore` ignores `*.sav`. To commit an updated save, use `git add -f`.

## Gotchas

- **Unique ROM copies.** DeSmuME names the battery file after the ROM, so two runs of the same ROM path share (and overwrite) the save. `Emu` copies the ROM to a unique temp name each time.
- **One emulator per process.** py-desmume segfaults on a second `DeSmuME()` in the same process. That is why `critic.py` runs each scenario in a child process.
- **Host clock.** The DS RTC is the host clock. The wild species, time-of-day palettes and RNG change from run to run.
- **Boot.** Continue shows the journal ("Started from ...") on the top screen over a black bottom screen, and it needs B. `boot()` taps B until the Poketch shows.
- **Overworld detection.** The overworld is detected by the Poketch's red button plus its green LCD. The end-of-battle screen is green too, so the red button is required.
- **Battle input.** Battle menus are driven by touch; the coordinates are in `emu.py`. B does not leave the move list; use the CANCEL bar. The player mon and its healthbar bob at the command menu, so screen comparisons use the closest of several idle frames.
- **Walking.** Holding a direction walks more than one tile. `walk()` presses the key only until the player's RAM position changes by one tile. RAM addresses (player position, party) move between runs, so they are found by scanning RAM for values known from the save.
- **Console spam.** DeSmuME prints thousands of "STMIA with Rb in Rlist" lines during some animations. `critic.py` echoes each distinct emulator line once; `console.log` keeps everything.
- **Build lock.** If you rebuild, use `flock /tmp/dazzling_build.lock make release`. Only one build can use `build/` at a time.
