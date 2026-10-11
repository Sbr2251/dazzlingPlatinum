# Overworld sprite work in progress (parked 2026-10-10)

Not merged to main. Resume here.

- `ds_redraws/`: the current candidates. DS-proportion (24 px) redraws of the CC0 Openmon designs for Darren
  (boy and girl), Garius (plus an Eclipse recolour) and Ruth. Each has a 4x sheet, walk GIF, a comparison against stock
  sprites, and `*_platinum_walk.png` (128x128, 4-bit, 16 colours, index 0 transparent, ready for the walker tools). Also
  the flagged Poltergeist kit builds (Eevee Expo 317) for comparison. README has licence quotes and the quality check.
- `free_round_openmon/`: the earlier Gen 3-style Openmon round (rejected: GBA style), kept for the source designs.
- `tools/`: the conversion and redraw scripts (`build_ds.py`, `ds_cast2.py`, `dsdraw.py`, ...). Paths inside still point
  at /tmp/a1r3; adjust before re-running.
- The first round (sprites ripped from official games) was dropped by the owner and is intentionally not saved here.

Open decisions: put Garius and Ruth redraws in now? For Darren, a cleanup pass plus run/bike/surf/fish frames on the
redraws, or the flagged kit?
