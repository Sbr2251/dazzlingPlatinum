# HD Battle HUD Assets (`hudhd`)

- **Font**: `MPLUSRounded1c-Bold.ttf` (fallback: `MPLUSRounded1c-Medium.ttf`)
  - **Family**: M PLUS Rounded 1c (Medium)
  - **Source**: Google Fonts (`https://github.com/google/fonts/tree/main/ofl/mplusrounded1c`)
  - **License**: SIL Open Font License 1.1 (`OFL.txt` in this directory)
  - **Usage**: Rasterized at runtime via `imstb_truetype.h` (public domain) into a display-resolution glyph atlas for the native HD battle HUD (`fx_hudhd.cpp`).
- **Icons**: All UI icons (gender symbols, status badges, Poké Ball / battle / bag / run / category / Mega / Quick Ball / arrow / brackets) are drawn procedurally via SDF shapes and vector line segments in `fx_hudhd.cpp` with no third-party or Nintendo/Game Freak art.
