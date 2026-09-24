"""Builds res/battle/particles/totem_aura.spa, the persistent aura drawn around a Totem Pokemon.

Usage: python3 tools/totem_aura/make_totem_aura_spa.py  (safe to re-run)

Three emitters that never expire (emitterLifeTime 0, not self-maintaining), so src/battle/totem_aura.c
decides when they stop:
  0: flame tongues licking up from a ring around the sprite, gold -> orange -> red
  1: a soft gold glow rising behind the sprite
  2: bright embers drifting up and fading
Emitter 3 is a one-shot flare that bursts outward when the aura first flares up (common_anims/totem_aura.s).
Greyscale textures are copied from stock archives; all colour comes from the emitters.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import spa  # noqa: E402

PARTICLES = os.path.join(HERE, "..", "..", "res/battle/particles")
OUT = os.path.join(PARTICLES, "totem_aura.spa")

TEX_FLAME, TEX_GLOW, TEX_SPARK = range(3)


def rgb(r, g, b):
    return r | g << 5 | b << 10


WHITE_GOLD = rgb(31, 30, 18)
GOLD = rgb(31, 23, 4)
ORANGE = rgb(31, 13, 1)
RED = rgb(24, 4, 2)


def fx(v):
    return int(round(v * 4096))


def misc(interval, texture, tile_s=0, scale_dir=0, air=0x80):
    return bytes((interval, 0x1F, air, texture, 1, 0, 0, tile_s | scale_dir << 4)) + b"\x00\x00\x37\x00"


def scale_anim(start, mid, end, curve_in, curve_out):
    return struct.pack("<hhhBBHH", fx(start), fx(mid), fx(end), curve_in, curve_out, 0, 0)


def color_anim(start, end, curve_in, peak, curve_out):
    return struct.pack("<HHBBBBHH", start, end, curve_in, peak, curve_out, 0, 0b100, 0)


def alpha_anim(start, mid, end, curve_in, curve_out, random_range=0):
    return struct.pack("<HHBBH", start | mid << 5 | end << 10, random_range, curve_in, curve_out, 0)


def resource(**kw):
    flags = {"circleAxis": 1, "hasScaleAnim": 1, "hasColorAnim": 1, "hasAlphaAnim": 1}
    flags.update(kw.pop("flags", {}))
    r = {
        "flags": flags, "posX": 0, "posY": 0, "posZ": 0, "emissionCount": fx(1), "radius": 0, "length": 0,
        "axisX": 0, "axisY": fx(1), "axisZ": 0, "color": GOLD, "initVelPosAmplifier": 0,
        "initVelAxisAmplifier": 0, "baseScale": fx(1), "aspectRatio": fx(1), "startDelay": 0, "minRotation": 0,
        "maxRotation": 0, "initAngle": 0, "reserved": 0, "emitterLifeTime": 0, "particleLifeTime": 20,
        "randomAttenuation": b"\x40\x00\x00\x00", "polygonX": 0, "polygonY": 0, "userData": b"\0" * 4,
    }
    r.update(kw)
    return r


def build():
    fire_spin = spa.read(os.path.join(PARTICLES, "fire_spin.spa"))
    swords_dance = spa.read(os.path.join(PARTICLES, "swords_dance.spa"))
    textures = [fire_spin["textures"][0], fire_spin["textures"][1], swords_dance["textures"][0]]

    flames = resource(
        flags={"emissionType": 6, "hasSpinBehavior": 1, "hasRandomBehavior": 1},
        posY=fx(-0.9), radius=fx(1.3), length=fx(0.72), color=GOLD,
        initVelPosAmplifier=fx(-0.02), initVelAxisAmplifier=fx(0.068), baseScale=fx(0.44),
        particleLifeTime=22, misc=misc(2, TEX_FLAME, tile_s=1, scale_dir=2, air=0x7C),
        scaleAnim=scale_anim(0.5, 1.0, 0.25, 0x40, 0xB0),
        colorAnim=color_anim(WHITE_GOLD, RED, 0x10, 0x60, 0xE0),
        alphaAnim=alpha_anim(0, 21, 0, 0x30, 0xA0, random_range=0x20),
        random=struct.pack("<hhhH", fx(0.02), 0, fx(0.02), 3),
        spin=struct.pack("<HH", 0x0300, 1),
    )
    glow = resource(
        flags={"emissionType": 7},
        posY=fx(-0.4), posZ=fx(-0.5), radius=fx(0.9), length=fx(1.2), color=GOLD,
        initVelAxisAmplifier=fx(0.02), baseScale=fx(1.3), particleLifeTime=40,
        misc=misc(4, TEX_GLOW),
        scaleAnim=scale_anim(0.7, 1.0, 1.2, 0x60, 0xC0),
        colorAnim=color_anim(GOLD, ORANGE, 0x20, 0x80, 0xFF),
        alphaAnim=alpha_anim(0, 11, 0, 0x60, 0xA0),
    )
    embers = resource(
        flags={"emissionType": 6, "hasRandomBehavior": 1},
        posY=fx(-0.6), radius=fx(1.2), length=fx(1.4), color=GOLD,
        initVelAxisAmplifier=fx(0.06), baseScale=fx(0.22), particleLifeTime=34,
        misc=misc(6, TEX_SPARK),
        scaleAnim=scale_anim(1.0, 1.0, 0.3, 0x20, 0x80),
        colorAnim=color_anim(WHITE_GOLD, ORANGE, 0x00, 0x50, 0xFF),
        alphaAnim=alpha_anim(31, 31, 0, 0x10, 0x90),
        random=struct.pack("<hhhH", fx(0.03), 0, fx(0.03), 4),
    )
    flare = resource(
        flags={"emissionType": 1, "selfMaintaining": 1, "hasGravityBehavior": 1},
        posY=fx(-0.2), radius=fx(0.7), emissionCount=fx(3), color=GOLD,
        initVelPosAmplifier=fx(0.088), baseScale=fx(0.56), emitterLifeTime=12, particleLifeTime=22,
        misc=misc(1, TEX_FLAME, tile_s=1, air=0x70),
        scaleAnim=scale_anim(0.6, 1.1, 0.2, 0x30, 0xA0),
        colorAnim=color_anim(WHITE_GOLD, RED, 0x08, 0x50, 0xE0),
        alphaAnim=alpha_anim(0, 26, 0, 0x20, 0xA0),
        gravity=struct.pack("<hhhH", 0, fx(0.006), 0, 0),
    )
    return {"magic": fire_spin["magic"], "version": fire_spin["version"], "resources": [flames, glow, embers, flare],
            "textures": textures}


def main():
    data = spa.write(build())
    open(OUT, "wb").write(data)
    assert spa.write(spa.read(OUT)) == data
    print(f"wrote {os.path.relpath(OUT)} ({len(data)} bytes)")


if __name__ == "__main__":
    main()
