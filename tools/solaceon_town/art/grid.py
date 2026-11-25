#!/usr/bin/env python3
"""A tiny pixel-art grid for the kit's paint scripts. Cells hold colour names from palette.py (None = transparent).

All drawing is integer and deterministic. `wrap=True` on the drawing calls wraps x/y, for tileable textures.
"""
import math


class G:
    def __init__(self, w, h, fill=None):
        self.w, self.h = w, h
        self.p = [[fill] * w for _ in range(h)]

    def copy(self):
        g = G(self.w, self.h)
        g.p = [r[:] for r in self.p]
        return g

    def get(self, x, y, wrap=True):
        if wrap:
            return self.p[y % self.h][x % self.w]
        return self.p[y][x] if 0 <= x < self.w and 0 <= y < self.h else None

    def set(self, x, y, v, wrap=False):
        if wrap:
            self.p[y % self.h][x % self.w] = v
        elif 0 <= x < self.w and 0 <= y < self.h:
            self.p[y][x] = v

    def rect(self, x, y, w, h, v, wrap=False):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.set(xx, yy, v, wrap)

    def hline(self, x, y, w, v, wrap=False):
        self.rect(x, y, w, 1, v, wrap)

    def vline(self, x, y, h, v, wrap=False):
        self.rect(x, y, 1, h, v, wrap)

    def bevel(self, x, y, w, h, face, hi, lo, wrap=False):
        """A raised block: face fill, 1 px highlight on top/left, 1 px shadow on bottom/right."""
        self.rect(x, y, w, h, face, wrap)
        self.hline(x, y, w, hi, wrap)
        self.vline(x, y, h, hi, wrap)
        self.hline(x, y + h - 1, w, lo, wrap)
        self.vline(x + w - 1, y, h, lo, wrap)

    def stamp(self, x, y, rows, cmap, wrap=False):
        """rows: strings; each char maps through cmap to a colour name; ' ' and '.' leave the cell alone."""
        for dy, row in enumerate(rows):
            for dx, ch in enumerate(row):
                if ch in " .":
                    continue
                self.set(x + dx, y + dy, cmap[ch], wrap)

    def disc(self, cx, cy, r, v, wrap=False):
        """Cells whose centre lies within r of (cx, cy) (cx, cy in cell units; a cell centre is x + 0.5)."""
        for yy in range(int(cy - r - 1), int(cy + r + 2)):
            for xx in range(int(cx - r - 1), int(cx + r + 2)):
                if (xx + 0.5 - cx) ** 2 + (yy + 0.5 - cy) ** 2 <= r * r:
                    self.set(xx, yy, v, wrap)

    def ring(self, cx, cy, r0, r1, v, wrap=False):
        for yy in range(int(cy - r1 - 1), int(cy + r1 + 2)):
            for xx in range(int(cx - r1 - 1), int(cx + r1 + 2)):
                d = math.hypot(xx + 0.5 - cx, yy + 0.5 - cy)
                if r0 <= d <= r1:
                    self.set(xx, yy, v, wrap)

    def line(self, x0, y0, x1, y1, v, wrap=False):
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            self.set(x0, y0, v, wrap)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def replace(self, x, y, w, h, frm, to, prob=1.0, rng=None, wrap=False):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                if self.get(xx, yy, wrap) == frm and (prob >= 1 or rng.random() < prob):
                    self.set(xx, yy, to, wrap)

    def outline(self, colour, inside=False):
        """Mark transparent cells next to opaque ones (or opaque cells next to transparent ones when inside)."""
        src = [r[:] for r in self.p]
        for y in range(self.h):
            for x in range(self.w):
                nb = [src[y + dy][x + dx] if 0 <= x + dx < self.w and 0 <= y + dy < self.h else None
                      for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
                if inside and src[y][x] is not None and any(n is None for n in nb):
                    self.p[y][x] = colour
                if not inside and src[y][x] is None and any(n is not None for n in nb):
                    self.p[y][x] = colour

    def blit(self, other, x, y, wrap=False):
        for yy in range(other.h):
            for xx in range(other.w):
                v = other.p[yy][xx]
                if v is not None:
                    self.set(x + xx, y + yy, v, wrap)

    def names(self):
        out = []
        for r in self.p:
            for v in r:
                if v is not None and v not in out:
                    out.append(v)
        return out
