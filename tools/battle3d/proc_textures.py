"""Pure-Python painterly RGBA8 procedural texture generators for BDSP 3D battle biomes."""

from __future__ import annotations

import math
import random
from typing import Tuple


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _lerp3(
    a: Tuple[float, float, float],
    b: Tuple[float, float, float],
    t: float,
) -> Tuple[float, float, float]:
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


def _smoothstep(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


class PeriodicNoise:
    """Fast deterministic periodic 2D value noise & fBM."""

    def __init__(self, seed: int):
        rng = random.Random(seed)
        self.grid = [rng.random() for _ in range(256 * 256)]
        self.perm = list(range(256))
        rng.shuffle(self.perm)

    def val(self, x: float, y: float, px: int, py: int) -> float:
        ix = math.floor(x)
        iy = math.floor(y)
        fx = _smoothstep(x - ix)
        fy = _smoothstep(y - iy)
        x0 = ix % px
        y0 = iy % py
        x1 = (x0 + 1) % px
        y1 = (y0 + 1) % py
        p = self.perm
        g = self.grid
        h00 = g[(p[x0 & 255] << 8) | p[y0 & 255]]
        h10 = g[(p[x1 & 255] << 8) | p[y0 & 255]]
        h01 = g[(p[x0 & 255] << 8) | p[y1 & 255]]
        h11 = g[(p[x1 & 255] << 8) | p[y1 & 255]]
        nx0 = h00 + (h10 - h00) * fx
        nx1 = h01 + (h11 - h01) * fx
        return nx0 + (nx1 - nx0) * fy

    def fbm(self, u: float, v: float, base_x: int, base_y: int, octaves: int = 4) -> float:
        total = 0.0
        amp = 0.5
        norm = 0.0
        fx, fy = base_x, base_y
        for _ in range(octaves):
            total += amp * self.val(u * fx, v * fy, fx, fy)
            norm += amp
            amp *= 0.5
            fx *= 2
            fy *= 2
        return total / norm


def _rgb_to_bytes(buf: bytearray, idx: int, r: float, g: float, b: float, a: float = 1.0) -> None:
    buf[idx] = int(_clamp01(r) * 255.0 + 0.5)
    buf[idx + 1] = int(_clamp01(g) * 255.0 + 0.5)
    buf[idx + 2] = int(_clamp01(b) * 255.0 + 0.5)
    buf[idx + 3] = int(_clamp01(a) * 255.0 + 0.5)


def make_sky_dome_texture(
    width: int,
    height: int,
    seed: int,
    zenith: Tuple[float, float, float],
    mid_sky: Tuple[float, float, float],
    horizon: Tuple[float, float, float],
    cloud_lit: Tuple[float, float, float] = (1.0, 0.99, 0.96),
    cloud_shade: Tuple[float, float, float] = (0.76, 0.85, 0.95),
    cloud_amount: float = 0.55,
    sun_dir_u: float = 0.18,
    sun_glow: Tuple[float, float, float] = (1.0, 0.96, 0.84),
    nebula_mode: bool = False,
) -> bytes:
    """Painterly sky dome texture: v=0 zenith, v=1 horizon, periodic in u."""
    noise = PeriodicNoise(seed)
    noise2 = PeriodicNoise(seed + 137)
    buf = bytearray(width * height * 4)
    inv_w = 1.0 / width
    inv_h = 1.0 / max(1, height - 1)

    for y in range(height):
        v = y * inv_h
        if v < 0.55:
            t = _smoothstep(v / 0.55)
            base_c = _lerp3(zenith, mid_sky, t)
        else:
            t = _smoothstep((v - 0.55) / 0.45)
            base_c = _lerp3(mid_sky, horizon, t)

        if nebula_mode:
            band = 0.35 + 0.65 * math.sin(min(1.0, v) * math.pi)
        else:
            if 0.16 < v < 0.93:
                b0 = _smoothstep(min(1.0, (v - 0.16) / 0.22))
                b1 = _smoothstep(min(1.0, (0.93 - v) / 0.14))
                band = b0 * b1
            else:
                band = 0.0

        row_off = y * width * 4
        for x in range(width):
            u = x * inv_w
            r, g, b = base_c

            du = abs(u - sun_dir_u)
            if du > 0.5:
                du = 1.0 - du
            dv = abs(v - 0.48)
            glow = math.exp(-(du * du * 28.0 + dv * dv * 14.0)) * (0.28 if not nebula_mode else 0.18)
            r = _lerp(r, sun_glow[0], glow)
            g = _lerp(g, sun_glow[1], glow)
            b = _lerp(b, sun_glow[2], glow)

            if nebula_mode:
                warp = noise2.fbm(u, v, 6, 4, 3) * 0.22
                n = noise.fbm((u + warp) % 1.0, _clamp01(v * 0.85 + warp * 0.4), 8, 5, 4)
                ribbons = _smoothstep(_clamp01((n - 0.40) * 2.5)) * band
                r = _lerp(r, cloud_lit[0], ribbons * 0.65)
                g = _lerp(g, cloud_lit[1], ribbons * 0.55)
                b = _lerp(b, cloud_lit[2], ribbons * 0.72)
                star = noise2.val(u * 96.0, v * 48.0, 96, 48)
                if star > 0.972 and v < 0.82:
                    sb = (star - 0.972) / 0.028
                    r = min(1.0, r + sb * 0.9)
                    g = min(1.0, g + sb * 0.85)
                    b = min(1.0, b + sb * 1.0)
            elif band > 0.001 and cloud_amount > 0.01:
                n_main = noise.fbm(u, v * 0.85, 7, 5, 4)
                n_puff = noise2.fbm(u + 0.13, v * 1.35, 14, 9, 3)
                shape = (n_main * 0.72 + n_puff * 0.28) * (0.85 + 0.30 * (1.0 - v))
                thresh = 0.66 - 0.28 * cloud_amount
                density = _smoothstep(_clamp01((shape - thresh) * 4.4)) * band
                if density > 0.005:
                    n_up = noise.fbm(u, max(0.0, v * 0.85 - 0.035), 7, 5, 3)
                    lit_t = _clamp01(0.55 + (n_main - n_up) * 2.6 + (0.72 - v) * 0.45)
                    cc = _lerp3(cloud_shade, cloud_lit, lit_t)
                    r = _lerp(r, cc[0], density * 0.94)
                    g = _lerp(g, cc[1], density * 0.94)
                    b = _lerp(b, cc[2], density * 0.94)

            _rgb_to_bytes(buf, row_off + x * 4, r, g, b, 1.0)
    return bytes(buf)


def make_painterly_ground_texture(
    size: int,
    seed: int,
    base_tint: Tuple[float, float, float] = (0.91, 0.93, 0.88),
    dark_tint: Tuple[float, float, float] = (0.72, 0.77, 0.69),
    speck_tint: Tuple[float, float, float] = (1.0, 0.99, 0.92),
    brush_strength: float = 1.0,
) -> bytes:
    """High-key seamless painterly grass-and-earth brushstroke texture designed for vertex-color blending."""
    n1 = PeriodicNoise(seed)
    n2 = PeriodicNoise(seed + 71)
    n3 = PeriodicNoise(seed + 211)
    buf = bytearray(size * size * 4)
    inv = 1.0 / size

    for y in range(size):
        v = y * inv
        row_off = y * size * 4
        for x in range(size):
            u = x * inv
            macro = n1.fbm(u, v, 6, 6, 3)
            tuft = n2.fbm(u, v, 24, 12, 3)
            fine = n3.val(u * 48.0, v * 48.0, 48, 48)
            m = _clamp01(0.5 + (macro - 0.5) * 1.35 * brush_strength + (tuft - 0.5) * 0.55 * brush_strength)
            c = _lerp3(dark_tint, base_tint, m)
            if fine > 0.78:
                st = (fine - 0.78) / 0.22 * 0.32 * brush_strength
                c = _lerp3(c, speck_tint, st)
            elif fine < 0.16:
                st = (0.16 - fine) / 0.16 * 0.18 * brush_strength
                c = _lerp3(c, dark_tint, st)
            _rgb_to_bytes(buf, row_off + x * 4, c[0], c[1], c[2], 1.0)
    return bytes(buf)


def make_rock_cliff_texture(
    size: int,
    seed: int,
    rock_light: Tuple[float, float, float],
    rock_mid: Tuple[float, float, float],
    rock_dark: Tuple[float, float, float],
    strata_freq: int = 8,
) -> bytes:
    """Seamless stylized BDSP cliff rock-face texture with horizontal strata and faceted crags."""
    n1 = PeriodicNoise(seed)
    n2 = PeriodicNoise(seed + 97)
    buf = bytearray(size * size * 4)
    inv = 1.0 / size

    for y in range(size):
        v = y * inv
        row_off = y * size * 4
        for x in range(size):
            u = x * inv
            warp = (n1.fbm(u, v, 6, 6, 3) - 0.5) * 0.16
            strata = 0.5 + 0.5 * math.sin((v + warp) * math.tau * strata_freq)
            crag = n2.fbm(u, v, 10, 14, 4)
            crack_n = abs(n1.fbm(u, v * 0.5, 16, 6, 3) - 0.5) * 2.0
            crack = _smoothstep(_clamp01(crack_n * 5.0))

            val = _clamp01(crag * 0.62 + strata * 0.38) * (0.58 + 0.42 * crack)
            if val < 0.45:
                c = _lerp3(rock_dark, rock_mid, val / 0.45)
            else:
                c = _lerp3(rock_mid, rock_light, (val - 0.45) / 0.55)
            _rgb_to_bytes(buf, row_off + x * 4, c[0], c[1], c[2], 1.0)
    return bytes(buf)


def make_foliage_texture(
    size: int,
    seed: int,
    dark: Tuple[float, float, float],
    mid: Tuple[float, float, float],
    bright: Tuple[float, float, float],
    needle_style: bool = True,
) -> bytes:
    """Seamless stylized pine-needle or leafy-bush painterly texture."""
    n1 = PeriodicNoise(seed)
    n2 = PeriodicNoise(seed + 151)
    buf = bytearray(size * size * 4)
    inv = 1.0 / size

    for y in range(size):
        v = y * inv
        row_off = y * size * 4
        for x in range(size):
            u = x * inv
            if needle_style:
                cluster = n1.fbm(u, v, 12, 8, 3)
                streak = n2.fbm(u, v, 32, 10, 3)
                scallop = 0.5 + 0.5 * math.sin(u * math.tau * 10.0 + v * math.tau * 3.0 + cluster * 2.5)
                val = _clamp01(cluster * 0.50 + streak * 0.34 + scallop * 0.16)
            else:
                cluster = n1.fbm(u, v, 10, 10, 3)
                dabs = n2.fbm(u, v, 22, 22, 3)
                val = _clamp01(cluster * 0.55 + dabs * 0.45)
            if val < 0.48:
                c = _lerp3(dark, mid, val / 0.48)
            else:
                c = _lerp3(mid, bright, (val - 0.48) / 0.52)
            _rgb_to_bytes(buf, row_off + x * 4, c[0], c[1], c[2], 1.0)
    return bytes(buf)


def make_bark_texture(
    size: int,
    seed: int,
    dark: Tuple[float, float, float] = (0.28, 0.19, 0.13),
    light: Tuple[float, float, float] = (0.50, 0.35, 0.24),
) -> bytes:
    """Seamless vertical fibrous tree bark texture."""
    n1 = PeriodicNoise(seed)
    buf = bytearray(size * size * 4)
    inv = 1.0 / size
    for y in range(size):
        v = y * inv
        row_off = y * size * 4
        for x in range(size):
            u = x * inv
            ridge = n1.fbm(u, v, 18, 4, 3)
            c = _lerp3(dark, light, _clamp01(ridge * 1.15 - 0.08))
            _rgb_to_bytes(buf, row_off + x * 4, c[0], c[1], c[2], 1.0)
    return bytes(buf)


def make_water_texture(
    size: int,
    seed: int,
    deep: Tuple[float, float, float] = (0.14, 0.48, 0.78),
    shallow: Tuple[float, float, float] = (0.34, 0.74, 0.94),
    shimmer: Tuple[float, float, float] = (0.86, 0.96, 1.0),
) -> bytes:
    """Seamless shimmering lake water texture with gentle caustics and wave sparkles."""
    n1 = PeriodicNoise(seed)
    n2 = PeriodicNoise(seed + 83)
    buf = bytearray(size * size * 4)
    inv = 1.0 / size
    for y in range(size):
        v = y * inv
        row_off = y * size * 4
        for x in range(size):
            u = x * inv
            w1 = n1.fbm(u, v, 8, 16, 3)
            w2 = n2.fbm((u + 0.2) % 1.0, (v + 0.1) % 1.0, 14, 24, 3)
            caustic = abs(w1 - w2)
            c = _lerp3(deep, shallow, _clamp01(w1 * 1.25 - 0.1))
            if caustic < 0.07:
                spark = _smoothstep(1.0 - caustic / 0.07) * 0.55
                c = _lerp3(c, shimmer, spark)
            _rgb_to_bytes(buf, row_off + x * 4, c[0], c[1], c[2], 0.94)
    return bytes(buf)


def make_plaza_stone_texture(
    size: int,
    seed: int,
    tile_a: Tuple[float, float, float] = (0.84, 0.82, 0.77),
    tile_b: Tuple[float, float, float] = (0.76, 0.74, 0.69),
    grout: Tuple[float, float, float] = (0.50, 0.49, 0.47),
    tiles: int = 4,
) -> bytes:
    """Seamless Sinnoh stone-paved plaza / cobblestone tile texture."""
    n1 = PeriodicNoise(seed)
    buf = bytearray(size * size * 4)
    inv = 1.0 / size
    for y in range(size):
        v = y * inv
        row_off = y * size * 4
        for x in range(size):
            u = x * inv
            ty = int(v * tiles)
            u_shift = (u + (0.5 / tiles if ty % 2 else 0.0)) % 1.0
            tx = int(u_shift * tiles)
            fx = (u_shift * tiles) % 1.0
            fy = (v * tiles) % 1.0
            edge = min(fx, 1.0 - fx, fy, 1.0 - fy)
            grain = n1.fbm(u, v, 12, 12, 3)
            base = tile_a if (tx + ty) % 2 == 0 else tile_b
            c = _lerp3(tile_b, base, 0.6 + 0.4 * grain)
            c = (c[0] * (0.90 + 0.18 * grain), c[1] * (0.90 + 0.18 * grain), c[2] * (0.90 + 0.18 * grain))
            if edge < 0.055:
                gt = _smoothstep(1.0 - edge / 0.055)
                c = _lerp3(c, grout, gt * 0.85)
            _rgb_to_bytes(buf, row_off + x * 4, c[0], c[1], c[2], 1.0)
    return bytes(buf)


def make_gym_court_texture(size: int, seed: int) -> bytes:
    """Non-tiling Sinnoh Gym / League polished stone battle floor with crisp court lines & Pokeball center."""
    n1 = PeriodicNoise(seed)
    buf = bytearray(size * size * 4)
    inv = 1.0 / size
    stone_light = (0.82, 0.84, 0.88)
    stone_dark = (0.66, 0.70, 0.76)
    line_white = (0.96, 0.97, 0.99)
    red_top = (0.86, 0.24, 0.26)
    blue_accent = (0.24, 0.48, 0.82)
    dark_ring = (0.20, 0.23, 0.28)

    for y in range(size):
        v = y * inv
        dy = v - 0.5
        row_off = y * size * 4
        for x in range(size):
            u = x * inv
            dx = u - 0.5
            r = math.sqrt(dx * dx + dy * dy)
            marble = n1.fbm(u, v, 8, 8, 3)
            gx = int(u * 12.0)
            gy = int(v * 12.0)
            c = _lerp3(stone_dark, stone_light, 0.35 + 0.65 * marble)
            if (gx + gy) % 2 == 0:
                c = (c[0] * 0.94, c[1] * 0.95, c[2] * 0.97)

            if 0.36 < max(abs(dx), abs(dy)) < 0.385:
                c = line_white
            elif 0.385 <= max(abs(dx), abs(dy)) < 0.42:
                c = blue_accent

            if abs(dy) < 0.012 and abs(dx) < 0.37:
                c = line_white

            if r < 0.16:
                if r > 0.142:
                    c = dark_ring
                elif abs(dy) < 0.014:
                    c = dark_ring
                elif r < 0.048:
                    c = line_white if r < 0.032 else dark_ring
                elif dy < 0.0:
                    c = _lerp3(red_top, (0.95, 0.38, 0.36), marble * 0.35)
                else:
                    c = _lerp3((0.88, 0.90, 0.94), line_white, marble * 0.4)

            _rgb_to_bytes(buf, row_off + x * 4, c[0], c[1], c[2], 1.0)
    return bytes(buf)


def make_crystal_texture(
    size: int,
    seed: int,
    core: Tuple[float, float, float] = (0.52, 0.88, 1.0),
    edge: Tuple[float, float, float] = (0.22, 0.46, 0.85),
) -> bytes:
    """Luminous faceted crystal texture for caves and Distortion World."""
    n1 = PeriodicNoise(seed)
    buf = bytearray(size * size * 4)
    inv = 1.0 / size
    for y in range(size):
        v = y * inv
        row_off = y * size * 4
        for x in range(size):
            u = x * inv
            facet = n1.fbm(u, v, 8, 16, 3)
            sheen = _smoothstep(_clamp01(1.0 - abs(v - 0.3) * 1.4))
            c = _lerp3(edge, core, _clamp01(facet * 0.65 + sheen * 0.55))
            _rgb_to_bytes(buf, row_off + x * 4, c[0], c[1], c[2], 1.0)
    return bytes(buf)
