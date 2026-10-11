import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/tmp/a1r3/tools')
from dschars import *
from ds_cast import SKIRT_LEGS, COAT_LEGS

# Hand-authored heads (explicit colours): k outline, 1/2/3 hair light/mid/dark, 4/5/6 skin light/mid/dark,
# e eye (outline colour), E iris, w white, a/b top2, x accent, g glass glint.
# Bodies: region masks (T top, U sleeve, h hand, J inner/trim, P bottoms, M shoes, F skin) shaded by the engine.
# Every row is "start_col:pixels" inside the 17-px column band x=7..23; the last row is y=25.

# ================================================================ Darren (boy): curly dark hair, teal jacket
BOY2 = Design('boy', {
    'hair': [(112, 80, 62), (72, 48, 38), (42, 30, 26)],
    'skin': [(212, 152, 106), (176, 116, 78), (128, 80, 54)],
    'eye': (42, 30, 26),
    'top': [(118, 212, 188), (58, 158, 142), (30, 102, 100)],
    'top2': [(248, 248, 240), (196, 202, 210)],
    'bottom': [(86, 90, 118), (58, 60, 86)],
    'shoes': [(150, 76, 62), (150, 76, 62)],
}, {
    'down': """
6:kkkkk
4:kk21112kk
3:k211122223k
2:k21111222233k
1:k2211222112233k
1:k2322222322233k
1:k3221122211223k
1:k3323332333233k
1:k3654444444563k
1:k354e44444e453k
2:k54E44444E45k
3:k544444445k
4:k6555556k
4:TTJFFFJTT
2:UUTTJJJJJTTUU
1:UUUTTTJJJTTTUUU
1:hhUUTTTJTTTUUhh
1:hhh.TTTJTTT.hhh
4:TTTTTTTTT""",
    'up': """
6:kkkkk
4:kk21112kk
3:k211122223k
2:k21111222233k
1:k2211222112233k
1:k2322222322233k
1:k3221122211223k
1:k2332233223323k
1:k2211221122123k
1:k3332333233333k
2:k33233323333k
3:k333333333k
4:kk33333kk
4:TTTFFFTTT
2:UUTTTTTTTTTUU
1:UUUTTTTTTTTTUUU
1:hhUUTTTTTTTUUhh
1:hhh.TTTTTTT.hhh
4:TTTTTTTTT""",
    'left': """
5:kkkkkk
3:kk211112kk
2:k2112211222k
1:k211222112223k
1:k2112221122233k
1:k32233222332233k
1:k22112211222233k
1:k36544433233333k
0:k44444443323333k
0:k44e44444633333k
0:k44E4444463333k
1:k444445633k
1:kk5555566kk
5:FFFFTTT
4:JTTTTTTTT
3:JTTTVVVTTT
3:JTTTVVVTTT
3:JTTThhhTTT
4:TTTTTTTT""",
}, {})

# ================================================================ Darren (girl): light-blue hair, high ponytail, blue band
GIRL2 = Design('girl', {
    'hair': [(196, 232, 252), (128, 184, 238), (72, 116, 192)],
    'skin': [(252, 224, 196), (240, 188, 156), (204, 140, 116)],
    'eye': (50, 88, 178),
    'top': [(250, 250, 252), (212, 224, 244), (150, 166, 210)],
    'top2': [(88, 136, 224), (50, 88, 178)],
    'bottom': [(100, 128, 210), (66, 84, 158)],
    'shoes': [(70, 76, 140), (70, 76, 140)],
}, {
    'down': """
6:kkkkk
4:kk11112kk
3:k111122222k
2:kaaaaaaaaaaak
1:k2bbbbbbbbbbb3k
1:k2111211121223k
1:k2122212221223k
1:k2236222622633k
1:k2354444444532k
1:k254e44444e452k
1:k254E44444E452k
1:k3254444444523k
1:k32k6555556k23k
2:k3.TTJFJTT.3k
2:UUTTJJJJJTTUU
1:UUUTTTJJJTTTUUU
1:hhUTTTTTTTTTUhh
1:hhh.TTTTTTT.hhh
3:PPPPPPPPPPP""",
    'up': """
6:kkkkk
4:kk11112kk
3:k111122222k
2:kaaaaabaaaaak
1:k2bbbbb1bbbbb3k
1:k2111312131123k
1:k2121312131223k
1:k2212312132123k
1:k2221312132233k
1:k2322312133233k
1:k3323312133333k
2:k33331213333k
3:kk3k121k3kk
3:TTTk212kTTT
2:UUTTTk3kTTTUU
1:UUUTTTTTTTTTUUU
1:hhUTTTTTTTTTUhh
1:hhh.TTTTTTT.hhh
3:PPPPPPPPPPP""",
    'left': """
3:kkkkkk
1:kk211112kk
0:k21111222kkk
0:kaaaaaaaakbbk
0:k2bbbbbbbk12k
0:k211122221k122k
0:k212221222k1223k
0:k641222122k1233k
0:k444632223k233k
0:k44e4632233k33k
0:k44E44633333k3k
1:k4444563333kk
1:k5555563kk
4:FFTTTT
3:JTTTTTTT
3:JTTVVVTT
3:TTTVVVTT
3:TTThhhTT
2:PPPPPPPPP""",
}, {}, legs=SKIRT_LEGS)

# ================================================================ Garius: maroon spiky hair, red shirt, dark trousers
G2_PAL = {
    'hair': [(208, 112, 102), (154, 62, 68), (96, 36, 46)],
    'skin': [(250, 214, 178), (232, 170, 130), (184, 116, 92)],
    'eye': (96, 36, 46),
    'top': [(246, 100, 90), (204, 50, 58), (132, 28, 40)],
    'top2': [(76, 68, 78), (46, 42, 50)],
    'bottom': [(82, 82, 98), (54, 54, 66)],
    'shoes': [(172, 172, 182), (172, 172, 182)],
}
G2_GRIDS = {
    'down': """
3:k....k....k
2:k1k..k1k..k1k
1:k121kk121kk121k
1:k2112112112123k
0:k221122211222113k
-1:k22112221122211233k
0:k232222322232223k
-1:k33223222322232233k
1:k3232223222323k
1:k3364436334633k
1:k3643344433463k
1:k354e44444e453k
2:k54E44444E45k
3:k544444445k
4:k6555556k
4:TTTFFFTTT
2:UUTTJJJJJTTUU
1:UUUTTTTTTTTTUUU
1:hhUUTTTTTTTUUhh
1:hhh.TTTTTTT.hhh
4:JJJJJJJJJ""",
    'up': """
3:k....k....k
2:k1k..k1k..k1k
1:k121kk121kk121k
1:k2112112112123k
0:k221122211222113k
-1:k22112221122211233k
0:k232222322232223k
-1:k33223222322232233k
1:k3232223222323k
1:k2232223222323k
1:k3222322232223k
1:k2322232223233k
2:k33223332333k
3:k333333333k
4:kk33333kk
4:TTTFFFTTT
2:UUTTTTTTTTTUU
1:UUUTTTTTTTTTUUU
1:hhUUTTTTTTTUUhh
1:hhh.TTTTTTT.hhh
4:JJJJJJJJJ""",
    'left': """
10:k..k
8:kk1kk1kk
5:kkk11211212k
3:kk2111221122kk
2:k2111222112223k
1:k21122211222233k
1:k32233222332233k
0:k22112211222233k
0:k3322332233333k
0:k364443332333333k
0:k43344443323333k
0:k44e44444633333k
0:k44E4444463333k
1:k444445633k
1:kk5555566kk
5:FFFFTTT
4:TTTTTTTTT
3:TTTTVVVTTT
3:TTTTVVVTTT
3:TTTThhhTTT
4:JJJJJJJJ""",
}
GARIUS2 = Design('garius', G2_PAL, G2_GRIDS, {})
E2_PAL = dict(G2_PAL)
E2_PAL.update({
    'hair': [(116, 112, 146), (74, 70, 104), (42, 38, 64)],
    'eye': (42, 38, 64),
    'top': [(186, 130, 240), (134, 78, 200), (84, 44, 134)],
    'top2': [(62, 46, 88), (38, 28, 54)],
    'bottom': [(60, 54, 80), (40, 36, 54)],
    'shoes': [(122, 114, 144), (122, 114, 144)],
})
GARIUS2_ECLIPSE = Design('garius_eclipse', E2_PAL, G2_GRIDS, {})

# ================================================================ Ruth: long wild purple hair, glasses, white coat, red tie
RUTH2 = Design('ruth', {
    'hair': [(192, 144, 238), (138, 88, 202), (86, 48, 142)],
    'skin': [(252, 224, 196), (240, 188, 156), (204, 140, 116)],
    'eye': (86, 48, 142),
    'top': [(252, 252, 252), (214, 218, 232), (156, 160, 188)],
    'top2': [(176, 210, 246)],
    'acc': [(224, 62, 72)],
    'bottom': [(74, 66, 92), (50, 46, 62)],
    'shoes': [(140, 92, 66), (140, 92, 66)],
    'glass': (252, 252, 252),
}, {
    'down': """
6:kkkkk
4:kk21112kk
3:k211122112k
2:k21112221122k
1:k2211122211223k
0:k221122211122233k
0:k232222322232223k
0:k323223222322323k
0:k323644333644323k
0:k326555444555623k
0:k324kgkk4kkgk423k
0:k3244E44444E4423k
0:k332544444445233k
0:k332k6555556k233k
0:k333TTJJxJJTT333k
1:k3UUTTJxJTTUU3k
1:UUUTTTJxJTTTUUU
1:hhUTTTJxJTTTUhh
1:hhh.TTJJJTT.hhh
3:TTTTTTTTTTT""",
    'up': """
6:kkkkk
4:kk21112kk
3:k211122112k
2:k21112221122k
1:k2211122211223k
0:k221122211122233k
0:k232222322232223k
0:k323223222322323k
0:k232232223223233k
0:k223222322232233k
0:k322322232223323k
0:k332322323223333k
0:k333233323332333k
0:k333333333333333k
1:k3333333333333k
1:UUk333333333kUU
1:UUUTTkkkkkTTUUU
1:hhUTTTTTTTTTUhh
1:hhh.TTTTTTT.hhh
3:TTTTTTTTTTT""",
    'left': """
4:kkkkkk
2:kk211112kk
1:k2111221122k
0:k211122211222k
0:k22111222112233k
0:k221122211122233k
0:k232222322232223k
0:k323223222322323k
0:k364433323322333k
0:k44555433232333k
0:k4kgkk46322333k
0:k44E4444633333k
1:k44444563333k
1:kk555556k3333k
3:xJTTTTk333k
3:JTTVVVTk33k
3:JTTVVVTTkk
3:TTTVVVTTT
3:TTThhhTTT
3:TTTTTTTTT""",
}, {}, legs=COAT_LEGS)

CAST2 = [BOY2, GIRL2, GARIUS2, GARIUS2_ECLIPSE, RUTH2]
