#ifndef POKEPLATINUM_PORT_HIRESTEXT_H
#define POKEPLATINUM_PORT_HIRESTEXT_H

// Hi-res text overlay (lane hiresui, prototype). See docs/postfx.md for the
// pattern this follows: game code reports what it draws, the simulator
// (subprojects/libntr, sim_hirestext.cpp) renders it crisply.
//
// The DS text pipeline is untouched: glyphs still go into BG window tiles
// exactly as before (positions, colours, scrolling, text speed). When the
// HiResText config flag is on, the main dialogue box additionally reports
// each glyph here and the simulator draws a 4x version over the frame.
// Prototype scope: FONT_MESSAGE printers on wide main-screen windows (the
// field/battle dialogue box). Menus would need the same one-call hook in
// their printers plus per-window tracking in the simulator.
//
// The HiResText_* glyph/clear/scroll functions are implemented in libntr;
// HiResText_IsEnabled is implemented game-side in src/port/hirestext.c.

#include <nitro/types.h>

#ifdef __cplusplus
extern "C" {
#endif

BOOL HiResText_IsEnabled(void);

// gfx is TextGlyph.gfx (decompressed 4bpp). (x, y) in DS screen pixels.
void HiResText_Glyph(int isSub, int x, int y, int w, int h,
                     const unsigned char *gfx, int palette,
                     int fgColor, int shadowColor);
void HiResText_ClearRect(int isSub, int x, int y, int w, int h);
void HiResText_ScrollRectUp(int isSub, int x, int y, int w, int h, int dy);

#ifdef __cplusplus
}
#endif

#endif
