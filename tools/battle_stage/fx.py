"""Bit-exact NitroSDK camera math and DS geometry engine vertex transform.

The arena's texture coordinates come from projecting every vertex through the home
camera, so the tool has to land on exactly the same screen pixels as the DS. This
module mirrors, integer for integer:

    MTX_PerspectiveW  (G3_Perspective, libraries/fx/src/fx_mtx44.c)
    MTX_LookAt        (G3_LookAt, libraries/fx/src/fx_mtx43.c)
    VEC_Normalize, VEC_CrossProduct, VEC_DotProduct (fx_vec.c)
    FX_Div / FX_Mul / FX_Mul32x64c (fx_cp.c, fx.h)

and the geometry engine steps the renderer relies on:

    G3_Scale on the position matrix, clip matrix = position x projection,
    vertex x clip matrix, viewport transform to integer screen coordinates.

Matrices are row-vector style like the SDK: m[row][col], v' = v x M.
"""

FX32_SHIFT = 12
FX32_ONE = 1 << FX32_SHIFT


def to_fx32(value):
    """Nearest fx32 of a float."""
    return int(round(value * FX32_ONE))


def _trunc_div(numer, denom):
    """C-style signed division (rounds toward zero), as the DS divider does."""
    q = abs(numer) // abs(denom)
    return q if (numer >= 0) == (denom >= 0) else -q


def fx_mul(a, b):
    """FX_Mul: (a * b + 0x800) >> 12."""
    return (a * b + 0x800) >> FX32_SHIFT


def fx_div(numer, denom):
    """FX_Div: 64/32 divider on (numer << 32) / denom, then rounded to fx32."""
    return (_trunc_div(numer << 32, denom) + (1 << 19)) >> 20


def fx_mul32x64c(v32, v64c):
    """FX_Mul32x64c: fx32 times an fx64c (32 fraction bits), rounded."""
    return (v64c * v32 + 0x80000000) >> 32


def mtx_perspective_w(fovy_sin, fovy_cos, aspect, near, far, scale_w=FX32_ONE):
    """MTX_PerspectiveW. Returns a 4x4 fx32 matrix."""
    one_tan = fx_div(fovy_cos, fovy_sin)
    t = _trunc_div(FX32_ONE << 32, near - far)  # FX_InvAsyncImm + FX_GetInvResultFx64c

    if scale_w != FX32_ONE:
        one_tan = _trunc_div(one_tan * scale_w, FX32_ONE)
        t = _trunc_div(t * scale_w, FX32_ONE)

    m = [[0] * 4 for _ in range(4)]
    m[1][1] = one_tan
    m[2][3] = -scale_w
    m[2][2] = fx_mul32x64c(far + near, t)
    m[3][2] = fx_mul32x64c(fx_mul(near << 1, far), t)
    m[0][0] = fx_div(one_tan, aspect)
    return m


def vec_dot(a, b):
    return (a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + (1 << 11)) >> FX32_SHIFT


def vec_cross(a, b):
    half = 1 << 11
    return (
        (a[1] * b[2] - a[2] * b[1] + half) >> FX32_SHIFT,
        (a[2] * b[0] - a[0] * b[2] + half) >> FX32_SHIFT,
        (a[0] * b[1] - a[1] * b[0] + half) >> FX32_SHIFT,
    )


def _isqrt(n):
    """floor(sqrt(n)) for n >= 0 (the DS square root unit truncates)."""
    if n <= 0:
        return 0

    x = 1 << ((n.bit_length() + 1) // 2)

    while True:
        y = (x + n // x) // 2

        if y >= x:
            return x

        x = y


def vec_normalize(v):
    """VEC_Normalize: 64/64 divide of 2^56 by |v|^2 and a 64-bit square root."""
    t = v[0] * v[0] + v[1] * v[1] + v[2] * v[2]
    assert t > 0
    inv = (1 << 56) // t
    t = inv * _isqrt(t << 2)
    return tuple((t * c + (1 << 44)) >> 45 for c in v)


def mtx_look_at(cam_pos, cam_up, target):
    """MTX_LookAt. Returns the 4x3 matrix as a 4x4 (last column 0, 0, 0, FX32_ONE),
    which is what G3_LoadMtx43 puts in the position matrix."""
    look = vec_normalize(tuple(cam_pos[i] - target[i] for i in range(3)))
    right = vec_normalize(vec_cross(cam_up, look))
    up = vec_cross(look, right)

    return [
        [right[0], up[0], look[0], 0],
        [right[1], up[1], look[1], 0],
        [right[2], up[2], look[2], 0],
        [-vec_dot(cam_pos, right), -vec_dot(cam_pos, up), -vec_dot(cam_pos, look), FX32_ONE],
    ]


def mtx_mult44(a, b):
    """Geometry engine 4x4 multiply a x b, each element (sum of s64 products) >> 12."""
    return [[sum(a[i][k] * b[k][j] for k in range(4)) >> FX32_SHIFT for j in range(4)] for i in range(4)]


def mtx_scale_rows(m, s):
    """G3_Scale(s, s, s) on the current matrix: rows 0-2 are multiplied by s."""
    out = [row[:] for row in m]

    for i in range(3):
        out[i] = [(s * c) >> FX32_SHIFT for c in m[i]]

    return out


# FX_SinIdx / FX_CosIdx of FX_DEG_TO_IDX(FX32_CONST(deg)), from FX_SinCosTable_
# (libraries/fx/src/fx_sincos.c): {deg: (sin, cos)}
SIN_COS_DEG = {15: (1056, 3958), 20: (1398, 3850)}
FX32_CONST_0_8 = 3277  # FX32_CONST(0.8)

NUM_VIEWS = 4


def projection_scale_w(far):
    """BuildProjection's W scale for a far clip (fx32): 1024 / far units, 1..16."""
    far_units = far >> FX32_SHIFT
    scale_w = 1024 // far_units if far_units > 0 else 16
    return max(1, min(16, scale_w)) * FX32_ONE


def debug_view_cam_pos(cam_pos, cam_target, view):
    """Camera position of debug view 0..3, as BuildView (src/battle/battle_stage.c)
    computes it: 1 and 2 orbit the target by -20 / +20 degrees of yaw, 3 raises the
    camera by 15 degrees and moves it 20% closer."""
    offset = [cam_pos[i] - cam_target[i] for i in range(3)]

    if view in (1, 2):
        sin_a, cos_a = SIN_COS_DEG[20]

        if view == 1:
            sin_a = -sin_a

        x = offset[0]
        offset[0] = fx_mul(x, cos_a) + fx_mul(offset[2], sin_a)
        offset[2] = fx_mul(offset[2], cos_a) - fx_mul(x, sin_a)
    elif view == 3:
        sin_a, cos_a = SIN_COS_DEG[15]
        right = vec_normalize(vec_cross((0, FX32_ONE, 0), offset))
        lift = vec_cross(offset, right)
        offset = [fx_mul(fx_mul(offset[i], cos_a) + fx_mul(lift[i], sin_a), FX32_CONST_0_8) for i in range(3)]

    return tuple(cam_target[i] + offset[i] for i in range(3))


SCREEN_W = 256
SCREEN_H = 192


class Camera:
    """A G3_Perspective + G3_LookAt camera with the arena's G3_Scale, as the renderer sets
    it up (BuildProjection, BuildView). All inputs are fx32 integers. view selects one of
    the debug views; the home camera is view 0."""

    def __init__(self, cam_pos, cam_target, fovy_sin, fovy_cos, near, far, vertex_scale, view=0):
        self.home_cam_pos = tuple(cam_pos)
        self.cam_pos = debug_view_cam_pos(cam_pos, cam_target, view)
        self.cam_target = tuple(cam_target)
        self.fovy_sin = fovy_sin
        self.fovy_cos = fovy_cos
        self.near = near
        self.far = far
        self.vertex_scale = vertex_scale
        self.view = view

        # BuildProjection also remaps column 2 (depth), which moves nothing on screen
        self.scale_w = projection_scale_w(far)
        self.proj = mtx_perspective_w(fovy_sin, fovy_cos, FX32_ONE * 4 // 3, near, far, self.scale_w)
        # x / w and y / w per unit of view x / depth and y / depth
        self.p00 = self.proj[0][0] / self.scale_w
        self.p11 = self.proj[1][1] / self.scale_w
        self.look_at = mtx_look_at(self.cam_pos, (0, FX32_ONE, 0), self.cam_target)
        self.pos = mtx_scale_rows(self.look_at, vertex_scale)
        self.clip = mtx_mult44(self.pos, self.proj)

    def to_clip(self, v):
        """Clip coordinates (x, y, z, w) of an fx16 vertex (x, y, z), like the DS."""
        c = self.clip
        return tuple(
            (v[0] * c[0][j] + v[1] * c[1][j] + v[2] * c[2][j] + FX32_ONE * c[3][j]) >> FX32_SHIFT
            for j in range(4)
        )

    def to_screen(self, v):
        """(sx, sy, sxf, syf, w) of an fx16 vertex with G3_ViewPort(0, 0, 255, 191).

        sx, sy are the integer coordinates the DS rasterizer uses (the viewport
        transform divides and drops the fraction; no subpixel precision). sxf, syf are
        the exact rational values, useful to keep the dropped fraction small. The DS
        truncates toward zero; the floor used here only differs off screen, where the
        hardware clips the polygon instead."""
        x, y, _z, w = self.to_clip(v)
        assert w > 0, "vertex behind the camera"
        sxf = (x + w) * SCREEN_W / (2 * w)
        syf = (w - y) * SCREEN_H / (2 * w)
        sx = ((x + w) * SCREEN_W) // (2 * w)
        sy = ((w - y) * SCREEN_H) // (2 * w)
        return sx, sy, sxf, syf, w

    # Float helpers for generating geometry: the exact integer matrices as floats.

    def world_to_view(self, p):
        """View space (x right, y up, z toward the viewer) of a world point in world
        units (fx16 vertex units times vertexScale)."""
        m = self.look_at
        v = [p[0] * FX32_ONE, p[1] * FX32_ONE, p[2] * FX32_ONE]
        return tuple((v[0] * m[0][j] + v[1] * m[1][j] + v[2] * m[2][j]) / FX32_ONE ** 2 + m[3][j] / FX32_ONE for j in range(3))

    def ray(self, sx, sy):
        """Origin and direction (world units) of the ray through screen point (sx, sy)."""
        p00, p11 = self.p00, self.p11
        xv = (2 * sx / SCREEN_W - 1) / p00
        yv = (1 - 2 * sy / SCREEN_H) / p11
        # view direction (xv, yv, -1) back to world with the rotation part of look_at;
        # its rows are the camera right/up/look axes' components
        m = self.look_at
        right = [m[i][0] / FX32_ONE for i in range(3)]
        up = [m[i][1] / FX32_ONE for i in range(3)]
        look = [m[i][2] / FX32_ONE for i in range(3)]
        d = [xv * right[i] + yv * up[i] - look[i] for i in range(3)]
        origin = [c / FX32_ONE for c in self.cam_pos]
        return origin, d

    def project_float(self, p):
        """Float screen position of a world point (world units), from the float view
        transform and the exact projection scale factors."""
        x, y, z = self.world_to_view(p)
        w = -z
        p00, p11 = self.p00, self.p11
        return (x * p00 / w + 1) * SCREEN_W / 2, (1 - y * p11 / w) * SCREEN_H / 2, w
