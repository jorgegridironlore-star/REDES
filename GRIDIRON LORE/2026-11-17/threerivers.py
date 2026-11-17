"""Estadio estilo Three Rivers Stadium (Pittsburgh, 1970) para el motor engine04 (derivado de metlife.py).
Cuenco 'cookie-cutter' casi circular y cerrado: grada inferior, anillo intermedio con fachada de hormigon,
gran grada superior; asientos amarillos/dorados, hormigon claro, coronacion abierta con torres de focos y un
videomarcador grande sobre el fondo. Cielo cubierto de diciembre (dia gris). Sin logos."""
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import engine04 as E
from engine04 import clip_poly, plane_coeffs, mix, shade, clamp
import metlife as ML

CX = 50.0
IX, IY = 72.0, 41.0
NSEG = 12
EXP = 2.6                     # superelipse: casi circulo pero que se ajusta al campo

PROFILE = [
    (0.0, 1.6, 19.0, 12.5, 'seats', 28, 0),
    (19.0, 12.5, 19.4, 17.0, 'fascia', 0, 0),
    (19.4, 17.0, 26.0, 21.5, 'seats', 10, 1),
    (26.0, 21.5, 26.4, 26.0, 'fascia', 0, 1),
    (26.4, 26.0, 50.0, 46.5, 'seats', 34, 2),
    (50.0, 46.5, 50.4, 49.5, 'rim', 0, 0),
]

def _pt(theta, d):
    a, b = IX + d, IY + d
    c, s = math.cos(theta), math.sin(theta)
    x = a * math.copysign(abs(c) ** (2 / EXP), c)
    y = b * math.copysign(abs(s) ** (2 / EXP), s)
    return np.array([CX + x, y])

def ring(d):
    return [_pt(2 * math.pi * (k + 0.5) / NSEG, d) for k in range(NSEG)]

SKINS = ML.SKINS
# diciembre en Pittsburgh: abrigos oscuros, negro y oro, algun gorro naranja de cazador
COATS = [(24, 24, 28), (40, 40, 46), (70, 54, 44), (96, 92, 88), (34, 36, 44), (214, 166, 44), (58, 66, 78),
         (120, 98, 70), (28, 28, 30), (150, 40, 36), (230, 186, 50), (60, 62, 70), (86, 70, 52), (20, 20, 22)]
HATS = [(230, 186, 50), (24, 24, 28), (222, 96, 30), (196, 40, 40), (240, 240, 236), (40, 40, 44), (230, 186, 50), (60, 50, 40)]
SEATCOL = [(206, 160, 30), (190, 54, 40), (206, 160, 30)]   # inferior, intermedia, superior

def make_seats(Wd, rows, seed, tier=0, seatpx=12, rowpx=24, occ=0.96, cheer=False):
    rng = random.Random(seed)
    Hh = rows * rowpx
    img = Image.new('RGB', (Wd, Hh), (150, 146, 138))
    d = ImageDraw.Draw(img)
    sc = SEATCOL[tier]
    for r in range(rows):
        y0 = r * rowpx
        d.rectangle([0, y0, Wd, y0 + rowpx], fill=(156, 152, 144))
        d.rectangle([0, y0 + rowpx - 9, Wd, y0 + rowpx - 2], fill=shade(sc, 0.8))
        x = -rng.uniform(0, seatpx); seat = 0
        while x < Wd:
            seat += 1
            if seat % 24 == 0:
                d.rectangle([x, y0, x + seatpx * 1.3, y0 + rowpx], fill=(172, 168, 160))
                x += seatpx * 1.3; continue
            cx = x + seatpx / 2; by = y0 + rowpx - 3
            if rng.random() < occ:
                coat = shade(rng.choice(COATS), rng.uniform(0.85, 1.08)); skin = rng.choice(SKINS)
                bw = seatpx * rng.uniform(0.8, 0.98)
                up = rowpx * (0.95 if not (cheer and rng.random() < 0.6) else 1.25)
                d.rounded_rectangle([cx - bw / 2, by - up * 0.62, cx + bw / 2, by], radius=int(bw * .35), fill=coat)
                hr = bw * 0.27; hy = by - up * 0.66 - hr
                d.ellipse([cx - hr, hy - hr, cx + hr, hy + hr], fill=skin)
                if rng.random() < 0.7:
                    d.chord([cx - hr * 1.1, hy - hr * 1.3, cx + hr * 1.1, hy + hr * .4], 180, 360, fill=rng.choice(HATS))
                if up > rowpx:
                    for sg in (-1, 1):
                        d.line([cx + sg * bw / 2, by - up * .55, cx + sg * bw * .7, by - up * 1.1], fill=coat, width=max(2, int(bw * .22)))
            else:
                d.rectangle([cx - seatpx * .4, by - 10, cx + seatpx * .4, by], fill=sc)
            x += seatpx
    return img

def make_fascia(Wd, seed, tier):
    img = Image.new('RGB', (Wd, 120), (186, 180, 168)); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, Wd, 10], fill=(204, 198, 186)); d.rectangle([0, 108, Wd, 120], fill=(150, 144, 134))
    if tier == 0:   # palcos / cabinas con ventanas oscuras
        r = random.Random(seed)
        for x in range(0, Wd, 52):
            d.rectangle([x + 4, 34, x + 48, 92], fill=mix((40, 46, 56), (120, 112, 96), r.uniform(0, .5)))
    return img

def make_rim(Wd):
    img = Image.new('RGB', (Wd, 80), (196, 190, 178)); d = ImageDraw.Draw(img)
    for x in range(0, Wd, 90):
        d.line([x, 0, x, 80], fill=(170, 164, 152), width=3)
    d.rectangle([0, 0, Wd, 8], fill=(214, 208, 196))
    return img

_TEX = {}
def tex(kind, seg, length, rows=0, tier=0, cheer=False):
    key = (kind, seg, round(length), rows, tier, cheer)
    if key in _TEX: return _TEX[key]
    Wd = max(200, int(length * 22))
    if kind == 'seats': t = make_seats(Wd, rows, seed=(seg * 31 + tier * 7) % 997, tier=tier, cheer=cheer)
    elif kind == 'fascia': t = make_fascia(Wd, seg, tier)
    else: t = make_rim(Wd)
    t = t.transpose(Image.FLIP_TOP_BOTTOM)
    _TEX[key] = t
    return t

# ---------------------------------------------------------------- cielo cubierto de diciembre
_SKY = None
def sky_pano():
    global _SKY
    if _SKY is None:
        Wp, Hp = 1440, 360
        el = np.linspace(80, -10, Hp)[:, None]
        t = np.clip((el + 2) / 50.0, 0, 1)
        top = np.array([128, 136, 150], np.float32); hor = np.array([200, 202, 204], np.float32)
        base = hor + (top - hor) * t[..., None]
        img = Image.fromarray(np.clip(np.broadcast_to(base, (Hp, Wp, 3)), 0, 255).astype(np.uint8))
        cl = Image.new('L', (Wp, Hp), 0); d = ImageDraw.Draw(cl); r = random.Random(7)
        for i in range(110):
            x = r.uniform(0, Wp); y = r.uniform(20, 260); w = r.uniform(90, 300); h = w * r.uniform(0.15, 0.3)
            d.ellipse([x - w / 2, y - h / 2, x + w / 2, y + h / 2], fill=int(r.uniform(60, 160)))
        cl = cl.filter(ImageFilter.GaussianBlur(14))
        img.paste(Image.new('RGB', (Wp, Hp), (104, 110, 122)), (0, 0), cl)
        _SKY = np.asarray(img)
    return _SKY

def sky(img, cam):
    old = ML._SKY
    ML._SKY = sky_pano()
    ML.sky(img, cam)
    ML._SKY = old

def stadium(img, cam, cheer=False):
    rings = {}
    def R(d):
        if d not in rings: rings[d] = ring(d)
        return rings[d]
    segs = []
    for si in range(NSEG):
        for (d0, z0, d1, z1, kind, rows, tier) in PROFILE:
            a0, b0 = R(d0)[si], R(d0)[(si + 1) % NSEG]
            a1, b1 = R(d1)[si], R(d1)[(si + 1) % NSEG]
            A0 = np.array([a0[0], a0[1], z0]); B0 = np.array([b0[0], b0[1], z0])
            A1 = np.array([a1[0], a1[1], z1]); B1 = np.array([b1[0], b1[1], z1])
            segs.append((si, kind, rows, tier, A0, B0, A1, B1))
    segs.sort(key=lambda s: -cam.depth((s[4] + s[5] + s[6] + s[7]) / 4))
    for si, kind, rows, tier, A0, B0, A1, B1 in segs:
        L = float(np.linalg.norm(B0 - A0))
        ML.quad_tex(img, cam, tex(kind, si, L, rows, tier, cheer), A0, B0, A1, B1)
    r0 = R(0.0)
    for si in range(NSEG):
        a, b = r0[si], r0[(si + 1) % NSEG]
        ML.solid(img, cam, [(a[0], a[1], 0), (b[0], b[1], 0), (b[0], b[1], 1.6), (a[0], a[1], 1.6)], (40, 52, 44))
        ML.solid(img, cam, [(a[0], a[1], 1.35), (b[0], b[1], 1.35), (b[0], b[1], 1.6), (a[0], a[1], 1.6)], (200, 196, 186))
    return img

DUGOUT_X = (34.0, 46.0)   # banquillo de beisbol en la pared cercana (y<0): alli estaba el telefono
def dugout(img, cam):
    y = -IY + 0.02
    x0, x1 = DUGOUT_X
    ML.solid(img, cam, [(x0, y, 0), (x1, y, 0), (x1, y, 1.3), (x0, y, 1.3)], (14, 14, 16))
    ML.solid(img, cam, [(x0 - 0.3, y + 0.05, 1.3), (x1 + 0.3, y + 0.05, 1.3), (x1 + 0.3, y + 0.05, 1.6), (x0 - 0.3, y + 0.05, 1.6)], (200, 196, 186))
    for k in range(4):   # escalones
        z = 0.08 + k * 0.08
        ML.solid(img, cam, [(x0 + 0.5, y + 0.1, z), (x1 - 0.5, y + 0.1, z), (x1 - 0.5, y + 0.1, z + 0.03), (x0 + 0.5, y + 0.1, z + 0.03)], (60, 60, 62))
    # telefono en la pared lateral del banquillo
    px = x1 - 1.0
    ML.solid(img, cam, [(px, y + 0.06, 0.95), (px + 0.35, y + 0.06, 0.95), (px + 0.35, y + 0.06, 1.2), (px, y + 0.06, 1.2)], (70, 70, 74))

def lights_and_board(img, cam):
    d = ImageDraw.Draw(img)
    rt = ring(50.4)
    for si in range(NSEG):
        if si % 2: continue
        a, b = rt[si], rt[(si + 1) % NSEG]
        c = (a + b) / 2
        inward = np.array([CX, 0.0]) - c; inward = inward / np.linalg.norm(inward)
        base = np.array([c[0], c[1], 49.5]); top = base + np.array([inward[0] * 1.5, inward[1] * 1.5, 9.0])
        pa, pb = cam.p(base), cam.p(top)
        if pa[2] < 1 or pb[2] < 1: continue
        w = max(1, int(cam.f * 0.3 / pa[2]))
        d.line([pa[:2], pb[:2]], fill=(150, 150, 154), width=w)
        along = (b - a) / np.linalg.norm(b - a)
        for row in range(3):
            for col in range(-3, 4):
                P = top + np.array([along[0] * col * 0.7, along[1] * col * 0.7, -row * 0.7])
                p = cam.p(P)
                if p[2] < 1: continue
                rr = max(1.0, cam.f * 0.26 / p[2])
                d.ellipse([p[0] - rr, p[1] - rr, p[0] + rr, p[1] + rr], fill=(236, 234, 220))
    # marcador grande sobre el fondo de x>100 (zona del 'center field')
    a = _pt(-0.32, 50.0); b = _pt(0.32, 50.0)
    P0 = np.array([a[0], a[1], 47.0]); P1 = np.array([b[0], b[1], 47.0])
    up = np.array([0, 0, 13.0])
    ML.solid(img, cam, [P0, P1, P1 + up, P0 + up], (22, 22, 24))
    ML.quad_tex(img, cam, board_texture(), P0 + np.array([0, 0, 1.0]), P1 + np.array([0, 0, 1.0]), P0 + np.array([0, 0, 12.0]), P1 + np.array([0, 0, 12.0]))

_BOARD = None
def board_texture():
    global _BOARD
    if _BOARD is None:
        im = Image.new('RGB', (1200, 340), (16, 16, 18)); d = ImageDraw.Draw(im)
        r = random.Random(3)
        for y in range(20, 320, 14):            # matriz de bombillas
            for x in range(20, 1180, 14):
                on = r.random() < 0.1
                d.ellipse([x, y, x + 8, y + 8], fill=(240, 210, 120) if on else (44, 40, 34))
        d.rectangle([60, 40, 560, 140], fill=(30, 30, 32)); d.rectangle([640, 40, 1140, 140], fill=(30, 30, 32))
        _BOARD = im.transpose(Image.FLIP_TOP_BOTTOM)
    return _BOARD

def render_world(cam, cheer=0.0, dug=True):
    img = Image.new('RGB', (cam.W, cam.H))
    sky(img, cam)
    g = E.ground()
    E.textured_plane(img, cam, g, (E.GX0, E.GY0, 0), (1, 0, 0), (0, 1, 0), E.GX1 - E.GX0, E.GY1 - E.GY0)
    stadium(img, cam, cheer=cheer > 0)
    if dug: dugout(img, cam)
    lights_and_board(img, cam)
    return img
