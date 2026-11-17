"""Estadio estilo MetLife / New Meadowlands Stadium (2010) para el motor engine04.
Cuenco cerrado de esquinas achaflanadas, 3 anillos de grada con asientos grises (inferior, mezzanine, superior),
bandas de palcos acristalados en los laterales, ribbon board continuo, 4 videomarcadores en las esquinas,
coronacion de lamas de aluminio con luz azul (Giants) y baterias de focos encendidas. Cielo de tarde de diciembre
(33 F, parcialmente nuboso; el partido acabo hacia las 16:20, casi al atardecer)."""
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import engine04 as E
from engine04 import clip_poly, plane_coeffs, mix, shade, clamp

CX = 50.0
IX, IY = 74.0, 41.0          # semiejes del borde interior de la grada (x desde el centro, y)
CH0 = 16.0                   # chaflan de las esquinas en el borde interior
K = math.tan(math.radians(22.5))

# perfil de la grada: (d0, z0, d1, z1, tipo, filas) con d = distancia horizontal desde el borde interior
PROFILE = [
    (0.0, 1.6, 21.0, 14.5, 'seats', 30),
    (21.0, 14.5, 21.4, 15.7, 'ribbon', 0),
    (21.4, 15.7, 21.8, 21.5, 'suites', 0),
    (21.8, 21.5, 31.0, 27.5, 'seats', 12),
    (31.0, 27.5, 31.4, 28.5, 'ribbon2', 0),
    (31.4, 28.5, 31.8, 32.5, 'suites', 0),
    (31.8, 32.5, 56.0, 53.0, 'seats', 34),
    (56.0, 53.0, 56.3, 57.5, 'louver', 0),
]

def ring(d):
    """8 vertices (sentido antihorario visto desde arriba) del anillo a distancia d."""
    X, Y, c = IX + d, IY + d, CH0 + d * K
    return [np.array(p) for p in [(CX + X, -Y + c), (CX + X, Y - c), (CX + X - c, Y), (CX - X + c, Y),
                                   (CX - X, Y - c), (CX - X, -Y + c), (CX - X + c, -Y), (CX + X - c, -Y)]]

SKINS = [(232, 190, 160), (220, 172, 140), (238, 204, 178), (196, 150, 118), (150, 104, 76), (120, 84, 60)]
COATS = [(18, 40, 104), (22, 46, 112), (24, 24, 28), (170, 30, 40), (90, 92, 98), (30, 34, 60), (236, 236, 232),
         (16, 36, 96), (60, 62, 70), (0, 76, 84), (40, 40, 46), (190, 34, 44), (22, 46, 112), (120, 122, 128), (14, 30, 80)]
HATS = [(18, 40, 104), (196, 30, 44), (24, 24, 28), (236, 236, 232), (120, 120, 126), (0, 76, 84), (40, 40, 46), (22, 46, 112)]

def make_seats(W, rows, seed, seatpx=12, rowpx=24, occ=0.95, cheer=False):
    rng = random.Random(seed)
    H = rows * rowpx
    img = Image.new('RGB', (W, H), (112, 114, 118))
    d = ImageDraw.Draw(img)
    for r in range(rows):
        y0 = r * rowpx
        d.rectangle([0, y0, W, y0 + rowpx], fill=(126, 128, 130))                 # contrahuella de hormigon
        d.rectangle([0, y0 + rowpx - 9, W, y0 + rowpx - 2], fill=(92, 96, 102))    # respaldos grises
        x = -rng.uniform(0, seatpx); seat = 0
        while x < W:
            seat += 1
            if seat % 26 == 0:                                                      # escalera
                d.rectangle([x, y0, x + seatpx * 1.3, y0 + rowpx], fill=(150, 150, 150))
                x += seatpx * 1.3; continue
            cx = x + seatpx / 2
            by = y0 + rowpx - 3
            if rng.random() < occ:
                coat = shade(rng.choice(COATS), rng.uniform(0.85, 1.08)); skin = rng.choice(SKINS)
                bw = seatpx * rng.uniform(0.78, 0.96)
                up = rowpx * (0.95 if not (cheer and rng.random() < 0.55) else 1.25)
                d.rounded_rectangle([cx - bw / 2, by - up * 0.62, cx + bw / 2, by], radius=int(bw * .35), fill=coat)
                hr = bw * 0.27; hy = by - up * 0.66 - hr
                d.ellipse([cx - hr, hy - hr, cx + hr, hy + hr], fill=skin)
                if rng.random() < 0.6:
                    hat = rng.choice(HATS)
                    d.chord([cx - hr * 1.1, hy - hr * 1.3, cx + hr * 1.1, hy + hr * .4], 180, 360, fill=hat)
                if up > rowpx:
                    d.line([cx - bw / 2, by - up * .55, cx - bw * .7, by - up * 1.1], fill=coat, width=max(2, int(bw * .22)))
                    d.line([cx + bw / 2, by - up * .55, cx + bw * .7, by - up * 1.1], fill=coat, width=max(2, int(bw * .22)))
            else:
                d.rectangle([cx - seatpx * .4, by - 10, cx + seatpx * .4, by], fill=(104, 108, 114))
            x += seatpx
    return img

def make_suites(W, seed, side=True):
    rng = random.Random(seed)
    H = 140
    img = Image.new('RGB', (W, H), (34, 40, 50))
    d = ImageDraw.Draw(img)
    if side:
        for x in range(0, W, 44):
            warm = rng.random() < 0.8
            col = mix((70, 84, 100), (196, 170, 120), rng.uniform(0.3, 0.8)) if warm else (52, 62, 76)
            d.rectangle([x + 3, 18, x + 41, H - 22], fill=col)
            for k in range(rng.randint(0, 3)):                                      # siluetas dentro del palco
                px = x + rng.uniform(8, 36)
                d.ellipse([px - 4, 52, px + 4, 60], fill=(40, 34, 30)); d.rectangle([px - 6, 60, px + 6, H - 24], fill=(36, 34, 40))
            d.line([x + 1, 14, x + 1, H - 18], fill=(150, 156, 164), width=3)
        d.rectangle([0, 10, W, 16], fill=(170, 174, 180))
        d.rectangle([0, H - 22, W, H], fill=(64, 70, 80))
    else:
        d.rectangle([0, 0, W, H], fill=(46, 52, 62))
        for x in range(0, W, 60):
            d.rectangle([x + 4, 30, x + 56, H - 30], fill=(28, 34, 44))
    return img

def make_ribbon(W, seed, blue=True):
    rng = random.Random(seed)
    img = Image.new('RGB', (W, 40), (10, 12, 18))
    d = ImageDraw.Draw(img)
    x = 0
    while x < W:
        w = rng.randint(160, 420)
        kind = rng.random()
        if kind < 0.45:
            d.rectangle([x, 4, x + w, 36], fill=(16, 50, 150))
            for k in range(0, w - 20, 26):
                d.polygon([(x + k + 6, 10), (x + k + 18, 20), (x + k + 6, 30)], fill=(235, 240, 255))
        elif kind < 0.7:
            d.rectangle([x, 4, x + w, 36], fill=(200, 30, 44))
            d.rectangle([x + 10, 16, x + w - 10, 24], fill=(250, 250, 250))
        else:
            d.rectangle([x, 4, x + w, 36], fill=(236, 238, 240))
            d.rectangle([x + 8, 12, x + w - 8, 28], fill=(20, 52, 150))
        x += w + 6
    return img

def make_louvers(W):
    img = Image.new('RGB', (W, 120), (60, 80, 140))
    d = ImageDraw.Draw(img)
    for y in range(120):
        d.line([0, y, W, y], fill=mix((40, 90, 210), (150, 170, 210), y / 120))     # luz azul de los Giants
    for x in range(0, W, 14):
        d.rectangle([x, 0, x + 8, 120], fill=(196, 200, 206))                      # lamas de aluminio
        d.line([x + 8, 0, x + 8, 120], fill=(130, 134, 140), width=2)
    d.rectangle([0, 0, W, 8], fill=(214, 216, 220))
    return img

_TEX = {}
def tex(kind, seg, length, cheer=False):
    key = (kind, seg, round(length), cheer)
    if key in _TEX: return _TEX[key]
    side = seg in (2, 6)   # segmentos laterales largos (y+ y y-)
    if kind[0] == 'seats':
        rows = kind[1]
        t = make_seats(max(200, int(length * 22)), rows, seed=hash(key) % 997, cheer=cheer)
    elif kind[0] == 'suites':
        t = make_suites(max(200, int(length * 22)), seed=seg * 7 + 1, side=side)
    elif kind[0] in ('ribbon', 'ribbon2'):
        t = make_ribbon(max(200, int(length * 22)), seed=seg * 3 + len(kind[0]))
    else:
        t = make_louvers(max(200, int(length * 22)))
    t = t.transpose(Image.FLIP_TOP_BOTTOM)
    _TEX[key] = t
    return t

def quad_tex(img, cam, texture, A0, B0, A1, B1):
    """Pinta una textura en el trapecio A0-B0 (borde bajo) / A1-B1 (borde alto); coordenadas por el plano."""
    poly = clip_poly(cam, [A0, B0, B1, A1])
    if not poly: return
    xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
    if max(xs) < 0 or min(xs) > cam.W or max(ys) < 0 or min(ys) > cam.H: return
    ax = B0 - A0; L = np.linalg.norm(ax); ax = ax / L
    up = (A1 + B1) / 2 - (A0 + B0) / 2
    ay = up - ax * np.dot(up, ax); Hh = np.linalg.norm(ay); ay = ay / Hh
    ext = max(abs(np.dot(A1 - A0, ax)), abs(np.dot(B1 - B0, ax) - 0)) + 1.0
    org = A0 - ax * ext
    la = L + 2 * ext
    c = plane_coeffs(cam, org, ax, ay, texture.size[0] / la, texture.size[1] / Hh)
    warped = texture.transform((cam.W, cam.H), Image.PERSPECTIVE, c, Image.BILINEAR)
    m = Image.new('L', (cam.W, cam.H), 0); ImageDraw.Draw(m).polygon(poly, fill=255)
    img.paste(warped, (0, 0), m)

def solid(img, cam, pts, col):
    p = clip_poly(cam, [np.asarray(q, float) for q in pts])
    if p: ImageDraw.Draw(img).polygon(p, fill=col)

# ---------------------------------------------------------------- cielo de tarde de diciembre
_SKY = None
def sky_pano():
    global _SKY
    if _SKY is None:
        Wp, Hp = 1440, 360        # azimut 0..360 (4 px/grado), elevacion -10..80
        el = np.linspace(80, -10, Hp)[:, None]
        t = np.clip((el + 2) / 40.0, 0, 1)
        top = np.array([92, 128, 178], np.float32); mid = np.array([170, 190, 214], np.float32); hor = np.array([238, 206, 172], np.float32)
        az = np.linspace(0, 360, Wp)[None, :]
        warm = np.clip(np.cos(np.radians(az - 230)), 0, 1) ** 2 * np.clip(1 - el / 25, 0, 1)   # atardecer al SO
        base = np.where(t[..., None] > 0.35, mid + (top - mid) * ((t[..., None] - 0.35) / 0.65), hor + (mid - hor) * (t[..., None] / 0.35))
        base = base + warm[..., None] * np.array([30, 6, -26], np.float32)
        img = Image.fromarray(np.clip(np.broadcast_to(base, (Hp, Wp, 3)), 0, 255).astype(np.uint8))
        cl = Image.new('L', (Wp, Hp), 0); d = ImageDraw.Draw(cl); r = random.Random(12)
        for i in range(70):                               # nubes sueltas (parcialmente nuboso)
            x = r.uniform(0, Wp); y = r.uniform(40, 250); w = r.uniform(60, 220); h = w * r.uniform(0.12, 0.25)
            for k in range(5):
                ox = r.uniform(-w * .4, w * .4); oy = r.uniform(-h * .3, h * .3)
                d.ellipse([x + ox - w / 3, y + oy - h / 2, x + ox + w / 3, y + oy + h / 2], fill=int(r.uniform(120, 210)))
        cl = cl.filter(ImageFilter.GaussianBlur(9))
        cloud = Image.new('RGB', (Wp, Hp), (236, 228, 222))
        img.paste(cloud, (0, 0), cl)
        _SKY = np.asarray(img)
    return _SKY

def sky(img, cam):
    S = sky_pano(); Hp, Wp = S.shape[:2]
    gw, gh = cam.W // 8 + 1, cam.H // 8 + 1
    us = np.linspace(0, cam.W, gw); vs = np.linspace(0, cam.H, gh)
    U, V = np.meshgrid(us, vs)
    R = cam.fw[None, None, :] + ((U - cam.W / 2) / cam.f)[..., None] * cam.r[None, None, :] - ((V - cam.H / 2) / cam.f)[..., None] * cam.u[None, None, :]
    R = R / np.linalg.norm(R, axis=-1, keepdims=True)
    az = (np.degrees(np.arctan2(R[..., 1], R[..., 0])) % 360) / 360 * (Wp - 1)
    el = np.degrees(np.arcsin(np.clip(R[..., 2], -1, 1)))
    yi = np.clip((80 - el) / 90 * (Hp - 1), 0, Hp - 1)
    small = S[yi.astype(int), az.astype(int)]
    im = Image.fromarray(small.astype(np.uint8)).resize((cam.W, cam.H), Image.BILINEAR)
    img.paste(im)

# ---------------------------------------------------------------- estadio
def stadium(img, cam, cheer=False):
    rings = {}
    def R(d):
        if d not in rings: rings[d] = ring(d)
        return rings[d]
    segs = []
    for si in range(8):
        for (d0, z0, d1, z1, kind, rows) in PROFILE:
            a0, b0 = R(d0)[si], R(d0)[(si + 1) % 8]
            a1, b1 = R(d1)[si], R(d1)[(si + 1) % 8]
            A0 = np.array([a0[0], a0[1], z0]); B0 = np.array([b0[0], b0[1], z0])
            A1 = np.array([a1[0], a1[1], z1]); B1 = np.array([b1[0], b1[1], z1])
            segs.append((si, kind, rows, A0, B0, A1, B1))
    # pintar de lejos a cerca
    segs.sort(key=lambda s: -cam.depth((s[3] + s[4] + s[5] + s[6]) / 4))
    for si, kind, rows, A0, B0, A1, B1 in segs:
        n = np.cross(B0 - A0, A1 - A0)
        L = float(np.linalg.norm(B0 - A0))
        if kind == 'suites' and si not in (2, 6):
            t = tex(('suites',), si, L)
        elif kind == 'suites':
            t = tex(('suites',), si, L)
        elif kind == 'seats':
            t = tex(('seats', rows), si, L, cheer)
        else:
            t = tex((kind,), si, L)
        quad_tex(img, cam, t, A0, B0, A1, B1)
    # muro del campo (acolchado azul oscuro con banda publicitaria neutra)
    r0 = R(0.0)
    for si in range(8):
        a, b = r0[si], r0[(si + 1) % 8]
        solid(img, cam, [(a[0], a[1], 0), (b[0], b[1], 0), (b[0], b[1], 1.6), (a[0], a[1], 1.6)], (22, 34, 70))
        solid(img, cam, [(a[0], a[1], 1.05), (b[0], b[1], 1.05), (b[0], b[1], 1.45), (a[0], a[1], 1.45)], (200, 204, 210))
    return img

def lights_and_boards(img, cam, board_img=None):
    d = ImageDraw.Draw(img)
    rt = ring(56.3)
    # baterias de focos sobre la coronacion de los laterales
    for si in (2, 6, 0, 4):
        a, b = rt[si], rt[(si + 1) % 8]
        n = 9 if si in (2, 6) else 4
        for k in range(n):
            u = (k + 0.5) / n
            c = a + (b - a) * u
            inward = np.array([CX, 0.0]) - c; inward = inward / np.linalg.norm(inward)
            base = np.array([c[0], c[1], 57.5]); top = base + np.array([inward[0] * 1.5, inward[1] * 1.5, 4.5])
            pa, pb = cam.p(base), cam.p(top)
            if pa[2] < 1 or pb[2] < 1: continue
            w = max(1, int(cam.f * 0.25 / pa[2]))
            d.line([pa[:2], pb[:2]], fill=(170, 174, 180), width=w)
            along = (b - a) / np.linalg.norm(b - a)
            for row in range(3):
                for col in range(-3, 4):
                    P = top + np.array([along[0] * col * 0.7, along[1] * col * 0.7, -row * 0.7])
                    p = cam.p(P)
                    if p[2] < 1: continue
                    rr = max(1.0, cam.f * 0.28 / p[2])
                    d.ellipse([p[0] - rr, p[1] - rr, p[0] + rr, p[1] + rr], fill=(255, 250, 230))
    # 4 videomarcadores de 30x118 pies colgados en las esquinas del anillo superior
    for si in (1, 3, 5, 7):
        a, b = ring(40.0)[si], ring(40.0)[(si + 1) % 8]
        m = (a + b) / 2; along = (b - a) / np.linalg.norm(b - a)
        half = 19.5
        P0 = np.array([m[0] - along[0] * half, m[1] - along[1] * half, 40.0]); P1 = np.array([m[0] + along[0] * half, m[1] + along[1] * half, 40.0])
        q = [P0, P1, P1 + np.array([0, 0, 10.0]), P0 + np.array([0, 0, 10.0])]
        solid(img, cam, [P0 - np.array([0, 0, 0.6]), P1 - np.array([0, 0, 0.6]), P1 + np.array([0, 0, 10.6]), P0 + np.array([0, 0, 10.6])], (18, 18, 22))
        if board_img is not None:
            quad_tex(img, cam, board_img, q[0], q[1], q[3], q[2])
        else:
            solid(img, cam, q, (20, 50, 140))

_BOARD = None
def board_texture():
    global _BOARD
    if _BOARD is None:
        im = Image.new('RGB', (1180, 300), (14, 30, 90)); d = ImageDraw.Draw(im)
        # imagen en directo: grada al fondo y cesped con lineas, con un rotulo de marcador abajo
        for y in range(120):
            d.line([0, y, 1180, y], fill=mix((40, 46, 70), (70, 80, 110), y / 120))
        r = random.Random(4)
        for i in range(900):
            x = r.uniform(0, 1180); y = r.uniform(0, 115)
            d.rectangle([x, y, x + 5, y + 5], fill=r.choice([(18, 40, 104), (170, 30, 40), (200, 200, 200), (40, 40, 46)]))
        d.rectangle([0, 120, 1180, 300], fill=(48, 120, 58))
        for x in range(-400, 1600, 120):
            d.line([x, 300, x + 260, 120], fill=(235, 240, 235), width=5)
        for k in range(9):
            x = 380 + k * 55 + r.uniform(-10, 10)
            d.ellipse([x - 10, 170, x + 10, 190], fill=(14, 38, 100) if k % 2 else (240, 240, 240))
            d.rectangle([x - 12, 188, x + 12, 236], fill=(14, 38, 100) if k % 2 else (240, 240, 240))
        d.rectangle([0, 262, 1180, 300], fill=(12, 14, 22))
        d.rectangle([20, 268, 300, 294], fill=(0, 76, 84)); d.rectangle([320, 268, 600, 294], fill=(14, 38, 100))
        im = im.transpose(Image.FLIP_TOP_BOTTOM)
        _BOARD = im
    return _BOARD

def render_world_metlife(cam, cheer=0.0):
    img = Image.new('RGB', (cam.W, cam.H))
    sky(img, cam)
    g = E.ground()
    E.textured_plane(img, cam, g, (E.GX0, E.GY0, 0), (1, 0, 0), (0, 1, 0), E.GX1 - E.GX0, E.GY1 - E.GY0)
    stadium(img, cam, cheer=cheer > 0)
    lights_and_boards(img, cam, board_texture())
    return img
