"""Motor 3D para Gridiron Lore 04 (Ice Bowl, Lambeau Field 1967).
Camara pinhole, suelo y gradas como planos texturizados (homografia), jugadores con esqueleto 3D
y sombreado cilindrico, sombras largas de sol de invierno, vaho. Unidades: yardas. x = largo del
campo (0 y 100 = lineas de gol), y = ancho (0 = centro), z = arriba."""
import math, random, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
def font(name, size):
    return ImageFont.truetype(os.path.join(HERE, 'fonts', name), int(size))

def lerp(a, b, t): return a + (b - a) * t
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease(t): t = clamp(t); return t * t * (3 - 2 * t)
def mix(c1, c2, t): return tuple(int(round(lerp(a, b, t))) for a, b in zip(c1, c2))
def shade(c, k): return tuple(max(0, min(255, int(v * k))) for v in c)

UP = np.array([0, 0, 1.0])
SUN = np.array([-0.55, 0.62, 0.33]); SUN /= np.linalg.norm(SUN)   # sol bajo de invierno (hacia el SO)

# ---------------------------------------------------------------- camara
class Cam:
    def __init__(self, pos, look, f, W, H, roll=0.0):
        self.pos = np.array(pos, float); self.f = float(f); self.W = W; self.H = H
        fw = np.array(look, float) - self.pos; fw /= np.linalg.norm(fw)
        r = np.cross(fw, UP); r /= np.linalg.norm(r)
        u = np.cross(r, fw)
        if roll:
            c, s = math.cos(roll), math.sin(roll)
            r, u = r * c + u * s, -r * s + u * c
        self.fw, self.r, self.u = fw, r, u
    def depth(self, P):
        return float(np.dot(np.asarray(P, float) - self.pos, self.fw))
    def p(self, P):
        d = np.asarray(P, float) - self.pos
        z = max(float(np.dot(d, self.fw)), 0.02)
        return (self.W / 2 + self.f * float(np.dot(d, self.r)) / z,
                self.H / 2 - self.f * float(np.dot(d, self.u)) / z, z)
    def pts(self, Ps):
        D = np.asarray(Ps, float) - self.pos
        z = np.maximum(D @ self.fw, 0.02)
        return np.stack([self.W / 2 + self.f * (D @ self.r) / z, self.H / 2 - self.f * (D @ self.u) / z, z], 1)
    def ray(self, u, v):
        return self.fw + (u - self.W / 2) / self.f * self.r - (v - self.H / 2) / self.f * self.u

def plane_coeffs(cam, origin, ax, ay, sx, sy):
    """Coeficientes de Image.transform(PERSPECTIVE): pixel de salida -> pixel de textura, para el plano
    P = origin + a*ax + b*ay, con textura (a*sx, b*sy)."""
    O = np.asarray(origin, float); A = np.asarray(ax, float); B = np.asarray(ay, float)
    N = np.cross(A, B)
    src, dst = [], []
    for (u, v) in [(0, cam.H), (cam.W, cam.H), (cam.W, cam.H * 0.5), (0, cam.H * 0.5), (cam.W * .5, cam.H * .75)]:
        d = cam.ray(u, v)
        den = float(np.dot(d, N))
        if abs(den) < 1e-9: continue
        t = float(np.dot(O - cam.pos, N)) / den
        P = cam.pos + d * t
        # resolver a, b por minimos cuadrados
        M = np.stack([A, B], 1)
        ab = np.linalg.lstsq(M, P - O, rcond=None)[0]
        src.append((u, v)); dst.append((ab[0] * sx, ab[1] * sy))
    # homografia por DLT con los puntos (u,v)->(x,y)
    rows, rhs = [], []
    for (u, v), (x, y) in zip(src, dst):
        rows.append([u, v, 1, 0, 0, 0, -u * x, -v * x]); rhs.append(x)
        rows.append([0, 0, 0, u, v, 1, -u * y, -v * y]); rhs.append(y)
    c = np.linalg.lstsq(np.array(rows), np.array(rhs), rcond=None)[0]
    return tuple(float(k) for k in c)

def clip_poly(cam, pts3, near=0.3):
    C = [np.asarray(P, float) for P in pts3]
    dz = [cam.depth(P) for P in C]
    if min(dz) > near: return [cam.p(P)[:2] for P in C]
    if max(dz) <= near: return None
    out = []
    n = len(C)
    for i in range(n):
        A, B = C[i], C[(i + 1) % n]; da, db = dz[i], dz[(i + 1) % n]
        if da > near: out.append(A)
        if (da > near) != (db > near):
            t = (near - da) / (db - da); out.append(A + (B - A) * t)
    if len(out) < 3: return None
    return [cam.p(P)[:2] for P in out]

def textured_plane(img, cam, tex, origin, ax, ay, la, lb, extra_mask_pts=None):
    """Pinta la textura tex (que cubre a en [0,la], b en [0,lb]) sobre el plano."""
    poly = clip_poly(cam, [origin, np.add(origin, np.multiply(ax, la)),
                           np.add(np.add(origin, np.multiply(ax, la)), np.multiply(ay, lb)), np.add(origin, np.multiply(ay, lb))])
    if not poly: return
    xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
    if max(xs) < 0 or min(xs) > cam.W or max(ys) < 0 or min(ys) > cam.H: return
    c = plane_coeffs(cam, origin, ax, ay, tex.size[0] / la, tex.size[1] / lb)
    warped = tex.transform((cam.W, cam.H), Image.PERSPECTIVE, c, Image.BILINEAR)
    mask = Image.new('L', (cam.W, cam.H), 0)
    ImageDraw.Draw(mask).polygon(poly, fill=255)
    img.paste(warped, (0, 0), mask)

# ---------------------------------------------------------------- texturas
GX0, GX1, GY0, GY1, GPX = -32.0, 132.0, -44.0, 44.0, 14   # suelo: x, y en yardas; px por yarda
FIELD_W = 53.33

def make_ground(seed=1):
    rng = np.random.default_rng(seed)
    W = int((GX1 - GX0) * GPX); H = int((GY1 - GY0) * GPX)
    def X(x): return (x - GX0) * GPX
    def Y(y): return (y - GY0) * GPX
    # base: cesped helado (verde apagado con escarcha) y tierra helada fuera
    base = np.zeros((H, W, 3), np.float32)
    n1 = rng.random((H // 8 + 2, W // 8 + 2)).astype(np.float32)
    n1 = np.array(Image.fromarray((n1 * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32) / 255
    n2 = rng.random((H // 2 + 2, W // 2 + 2)).astype(np.float32)
    n2 = np.array(Image.fromarray((n2 * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32) / 255
    n3 = rng.random((H, W)).astype(np.float32)
    grass = np.array([92, 112, 74], np.float32); frost = np.array([200, 208, 206], np.float32)
    fmix = np.clip((n1 * 0.7 + n2 * 0.3) * 1.25 - 0.35, 0, 1)[..., None] * 0.55 + 0.12
    base = grass * (1 - fmix) + frost * fmix
    base *= (0.9 + 0.18 * n3[..., None])
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    # fuera del campo: nieve apartada y tierra helada
    snow = (226, 230, 234)
    for (x0, x1) in ((GX0, -10.6), (110.6, GX1)):
        d.rectangle([X(x0), 0, X(x1), H], fill=(150, 150, 140))
    for (y0, y1) in ((GY0, -FIELD_W / 2 - 3), (FIELD_W / 2 + 3, GY1)):
        d.rectangle([0, Y(y0), W, Y(y1)], fill=(150, 150, 140))
    rr = random.Random(seed)
    # nieve apartada junto a las bandas: franja irregular con ruido
    for side in (-1, 1):
        for i in range(1400):
            x = rr.uniform(-28, 128); y = side * rr.uniform(FIELD_W / 2 + 6.5, FIELD_W / 2 + 14)
            r = rr.uniform(0.3, 0.9)
            d.ellipse([X(x - r * 1.6), Y(y - r), X(x + r * 1.6), Y(y + r)], fill=mix(snow, (176, 182, 192), rr.random() * .6))
    # lineas: banda, fondo, gol, cada 5 yardas
    lw = max(2, int(GPX * 0.11))
    white = (240, 242, 244)
    for x in range(0, 101, 5):
        d.line([X(x), Y(-FIELD_W / 2), X(x), Y(FIELD_W / 2)], fill=white, width=lw if x % 10 else lw + 1)
    for x in (-10, 110):
        d.line([X(x), Y(-FIELD_W / 2), X(x), Y(FIELD_W / 2)], fill=white, width=lw)
    for y in (-FIELD_W / 2, FIELD_W / 2):
        d.line([X(-10), Y(y), X(110), Y(y)], fill=white, width=lw + 2)
    # hash marks (NFL 1967: a 23,33 yd de cada banda) y marcas de 1 yarda
    for x in range(1, 100):
        if x % 5 == 0: continue
        for y in (-FIELD_W / 2 + 0.3, FIELD_W / 2 - 0.9, -3.08, 3.08 - 0.6):
            d.line([X(x), Y(y), X(x), Y(y + 0.6)], fill=white, width=lw)
    # numeros cada 10 yardas
    fnt = font('Anton-Regular.ttf', GPX * 2.2)
    for x in range(10, 100, 10):
        n = x if x <= 50 else 100 - x
        for y, rot in ((-FIELD_W / 2 + 12, 180), (FIELD_W / 2 - 12, 0)):
            t = Image.new('L', (int(GPX * 5), int(GPX * 3)), 0)
            ImageDraw.Draw(t).text((t.size[0] / 2, t.size[1] / 2), str(n), font=fnt, fill=235, anchor='mm')
            t = t.rotate(rot + 90, expand=True).transpose(Image.FLIP_TOP_BOTTOM)
            img.paste(Image.new('RGB', t.size, white), (int(X(x) - t.size[0] / 2), int(Y(y) - t.size[1] / 2)), t)
    # pisadas y barro helado en el centro del campo
    for i in range(2600):
        x = rr.gauss(50, 24); y = rr.gauss(0, 9)
        r = rr.uniform(0.06, 0.22)
        d.ellipse([X(x - r * 1.5), Y(y - r), X(x + r * 1.5), Y(y + r)], fill=mix((116, 118, 98), (150, 156, 140), rr.random()))
    img = img.filter(ImageFilter.GaussianBlur(0.7))
    return img

GROUND = None
def ground():
    global GROUND
    if GROUND is None:
        p = os.path.join(HERE, 'cache_ground.png')
        if os.path.exists(p): GROUND = Image.open(p).convert('RGB')
        else:
            GROUND = make_ground(); GROUND.save(p)
    return GROUND

COATS = [(46, 44, 50), (70, 54, 44), (96, 92, 88), (34, 36, 44), (120, 98, 70), (58, 66, 78), (140, 120, 92),
         (82, 40, 36), (60, 74, 58), (160, 150, 130), (28, 28, 30), (104, 70, 50), (190, 180, 160), (50, 70, 110)]
HATS = [(222, 96, 30), (230, 110, 40), (196, 40, 40), (34, 90, 60), (230, 200, 60), (240, 240, 236), (40, 40, 44),
        (90, 70, 50), (60, 60, 90), (150, 30, 30)]
SKINS = [(232, 190, 160), (220, 172, 140), (238, 204, 178), (196, 150, 118), (150, 104, 76)]

def make_crowd(W, rows, seed, seatpx=13, rowpx=26, light=1.0, cheer=0.0):
    """Textura de una grada: filas de bancos con aficionados abrigados vistos de frente y algo desde arriba."""
    rng = random.Random(seed)
    H = rows * rowpx
    img = Image.new('RGB', (W, H), (120, 116, 108))
    d = ImageDraw.Draw(img)
    for r in range(rows):
        y0 = r * rowpx
        # contrahuella de hormigon y banco de madera
        d.rectangle([0, y0, W, y0 + rowpx], fill=(132, 128, 120))
        d.rectangle([0, y0 + rowpx - 6, W, y0 + rowpx - 3], fill=(150, 132, 104))
        d.line([0, y0 + rowpx - 1, W, y0 + rowpx - 1], fill=(96, 92, 86), width=1)
        x = -rng.uniform(0, seatpx)
        seat = 0
        while x < W:
            seat += 1
            if seat % 28 == 0:          # pasillo con escaleras
                d.rectangle([x, y0, x + seatpx * 1.4, y0 + rowpx], fill=(160, 158, 152))
                d.line([x, y0 + rowpx // 2, x + seatpx * 1.4, y0 + rowpx // 2], fill=(130, 128, 122))
                x += seatpx * 1.4; continue
            if rng.random() < 0.97:
                coat = rng.choice(COATS); hat = rng.choice(HATS); skin = rng.choice(SKINS)
                k = light * rng.uniform(0.85, 1.08)
                coat = shade(coat, k); hat = shade(hat, k)
                bw = seatpx * rng.uniform(0.8, 0.98)
                up = rowpx * (0.95 if rng.random() > cheer else 1.25)
                cx = x + seatpx / 2 + rng.uniform(-1, 1)
                by = y0 + rowpx - 4
                # cuerpo (abrigo) con hombros redondeados
                d.rounded_rectangle([cx - bw / 2, by - up * 0.62, cx + bw / 2, by], radius=int(bw * .35), fill=coat)
                d.rectangle([cx - bw / 2 + 1, by - up * 0.62 + bw * .3, cx - bw / 2 + 2, by], fill=shade(coat, 1.15))
                # bufanda
                if rng.random() < 0.6:
                    d.rectangle([cx - bw * .32, by - up * 0.66, cx + bw * .32, by - up * 0.56], fill=shade(rng.choice(HATS), k))
                # cabeza
                hr = bw * 0.27
                hy = by - up * 0.66 - hr
                d.ellipse([cx - hr, hy - hr, cx + hr, hy + hr], fill=shade(skin, k * .95))
                # gorro / orejeras
                kind = rng.random()
                if kind < 0.55:
                    d.chord([cx - hr * 1.12, hy - hr * 1.35, cx + hr * 1.12, hy + hr * .55], 180, 360, fill=hat)
                    d.rectangle([cx - hr * 1.12, hy - hr * .1, cx - hr * .8, hy + hr * .6], fill=hat)
                    d.rectangle([cx + hr * .8, hy - hr * .1, cx + hr * 1.12, hy + hr * .6], fill=hat)
                elif kind < 0.8:
                    d.chord([cx - hr * 1.05, hy - hr * 1.2, cx + hr * 1.05, hy + hr * .3], 180, 360, fill=hat)
                    d.ellipse([cx - hr * .3, hy - hr * 1.55, cx + hr * .3, hy - hr * .95], fill=shade(hat, 1.2))
                else:
                    d.rectangle([cx - hr * 1.3, hy - hr * .55, cx + hr * 1.3, hy - hr * .35], fill=hat)
                    d.chord([cx - hr * .95, hy - hr * 1.4, cx + hr * .95, hy - hr * .2], 180, 360, fill=hat)
                # rostro tapado: sombra de ojos/bufanda
                d.line([cx - hr * .45, hy + hr * .05, cx + hr * .45, hy + hr * .05], fill=shade(skin, .65), width=1)
                if up > rowpx:   # brazos en alto celebrando
                    d.line([cx - bw / 2, by - up * .55, cx - bw * .7, by - up * 1.1], fill=coat, width=max(2, int(bw * .22)))
                    d.line([cx + bw / 2, by - up * .55, cx + bw * .7, by - up * 1.1], fill=coat, width=max(2, int(bw * .22)))
            x += seatpx
    return img

# ---------------------------------------------------------------- estadio
STAND_IN = 41.0          # distancia de la primera fila al centro (laterales)
END_IN = 24.0            # distancia de la primera fila desde la linea de fondo
WALL_H = 1.6
RISE = 22.0              # altura de la ultima fila sobre el muro
DEPTH = 34.0             # profundidad horizontal de la grada
NROWS = 52

_crowd_cache = {}
def crowd_tex(key, W, cheer=0.0):
    k = (key, cheer > 0)
    if k not in _crowd_cache:
        _crowd_cache[k] = make_crowd(W, NROWS, seed=hash(key) % 1000, cheer=cheer)
    return _crowd_cache[k]

def stand_planes():
    """(origin, ax, ay, la, lb, key, texW) para las 4 gradas. ax a lo largo, ay hacia arriba de la grada."""
    L0, L1 = -10 - END_IN - 6, 110 + END_IN + 6
    slope = np.array([0, 1.0, RISE / DEPTH]); lb = float(np.linalg.norm([DEPTH, RISE]))
    out = []
    # lateral norte (y+): origen en la primera fila
    out.append(((L1, STAND_IN, WALL_H), (-1, 0, 0), (0, DEPTH / lb, RISE / lb), L1 - L0, lb, 'N', 3400))
    out.append(((L0, -STAND_IN, WALL_H), (1, 0, 0), (0, -DEPTH / lb, RISE / lb), L1 - L0, lb, 'S', 3400))
    # fondos
    out.append(((-10 - END_IN, -STAND_IN - 4, WALL_H), (0, 1, 0), (-DEPTH / lb, 0, RISE / lb), 2 * STAND_IN + 8, lb, 'W', 1400))
    out.append(((110 + END_IN, STAND_IN + 4, WALL_H), (0, -1, 0), (DEPTH / lb, 0, RISE / lb), 2 * STAND_IN + 8, lb, 'E', 1400))
    return out

def sky(img, cam):
    d = ImageDraw.Draw(img)
    top, hor = (92, 138, 196), (206, 220, 232)
    for y in range(0, cam.H, 4):
        # elevacion del rayo
        r = cam.ray(cam.W / 2, y); el = r[2] / np.linalg.norm(r)
        t = clamp(el * 3.2)
        d.rectangle([0, y, cam.W, y + 4], fill=mix(hor, top, t))

def wall(img, cam):
    d = ImageDraw.Draw(img)
    L0, L1 = -10 - END_IN - 6, 110 + END_IN + 6
    col = (52, 70, 58)
    quads = [
        [(L0, STAND_IN, 0), (L1, STAND_IN, 0), (L1, STAND_IN, WALL_H), (L0, STAND_IN, WALL_H)],
        [(L0, -STAND_IN, 0), (L1, -STAND_IN, 0), (L1, -STAND_IN, WALL_H), (L0, -STAND_IN, WALL_H)],
        [(-10 - END_IN, -STAND_IN - 4, 0), (-10 - END_IN, STAND_IN + 4, 0), (-10 - END_IN, STAND_IN + 4, WALL_H), (-10 - END_IN, -STAND_IN - 4, WALL_H)],
        [(110 + END_IN, -STAND_IN - 4, 0), (110 + END_IN, STAND_IN + 4, 0), (110 + END_IN, STAND_IN + 4, WALL_H), (110 + END_IN, -STAND_IN - 4, WALL_H)],
    ]
    for q in quads:
        p = clip_poly(cam, q)
        if p: d.polygon(p, fill=col)

def rim(img, cam):
    """Borde superior del estadio y palco de prensa (lado oeste = y negativo)."""
    d = ImageDraw.Draw(img)
    L0, L1 = -10 - END_IN - 6, 110 + END_IN + 6
    zt = WALL_H + RISE
    yo = STAND_IN + DEPTH
    for sgn in (1, -1):
        q = [(L0, sgn * yo, zt), (L1, sgn * yo, zt), (L1, sgn * yo, zt + 1.6), (L0, sgn * yo, zt + 1.6)]
        p = clip_poly(cam, q)
        if p: d.polygon(p, fill=(150, 148, 140))
    # palco de prensa: caja alargada sobre la grada sur (y-)
    box = [(15, -yo + 2, zt), (85, -yo + 2, zt), (85, -yo + 2, zt + 7), (15, -yo + 2, zt + 7)]
    p = clip_poly(cam, box)
    if p:
        d.polygon(p, fill=(176, 172, 160))
        win = [(17, -yo + 1.9, zt + 3), (83, -yo + 1.9, zt + 3), (83, -yo + 1.9, zt + 5.6), (17, -yo + 1.9, zt + 5.6)]
        p2 = clip_poly(cam, win)
        if p2: d.polygon(p2, fill=(60, 72, 86))
    # marcadores en los fondos
    for xe in (-10 - END_IN - DEPTH + 3, 110 + END_IN + DEPTH - 3):
        q = [(xe, -12, zt), (xe, 12, zt), (xe, 12, zt + 7), (xe, -12, zt + 7)]
        p = clip_poly(cam, q)
        if p: d.polygon(p, fill=(28, 30, 32))
    # mastiles con banderas
    for x in (-8, 50, 108):
        A = (x, -yo - 1, zt); B = (x, -yo - 1, zt + 9)
        a, b = cam.p(A), cam.p(B)
        if a[2] > 1 and b[2] > 1:
            d.line([a[:2], b[:2]], fill=(200, 200, 200), width=max(1, int(cam.f * .15 / a[2])))

def goalpost(draw, cam, xg):
    """Poste de horquilla (amarillo) en la linea de gol, como en 1967."""
    Y = (230, 196, 40)
    base = (xg - 0.0, 0, 0)
    def L(A, B, w):
        pa, pb = cam.p(A), cam.p(B)
        if pa[2] < 0.5 or pb[2] < 0.5: return
        ww = max(1, int(cam.f * w / ((pa[2] + pb[2]) / 2)))
        draw.line([pa[:2], pb[:2]], fill=Y, width=ww)
    off = -1.5 if xg < 50 else 1.5
    L((xg + off, 0, 0), (xg + off, 0, 3.0), 0.12)
    L((xg + off, 0, 3.0), (xg, 0, 3.4), 0.1)
    L((xg, -3.08, 3.33), (xg, 3.08, 3.33), 0.09)
    for y in (-3.08, 3.08):
        L((xg, y, 3.33), (xg, y, 10.5), 0.07)
    # banderola en lo alto
    for y in (-3.08, 3.08):
        p = cam.p((xg, y, 10.5))
        if p[2] > 1:
            s = cam.f / p[2]
            draw.polygon([(p[0], p[1]), (p[0] + s * .8, p[1] + s * .2), (p[0], p[1] + s * .45)], fill=(200, 40, 40))

def render_world(cam, extras=None, cheer=0.0, goalposts=True):
    img = Image.new('RGB', (cam.W, cam.H))
    sky(img, cam)
    rim(img, cam)
    g = ground()
    textured_plane(img, cam, g, (GX0, GY0, 0), (1, 0, 0), (0, 1, 0), GX1 - GX0, GY1 - GY0)
    planes = stand_planes()
    planes.sort(key=lambda q: -cam.depth(np.add(q[0], np.add(np.multiply(q[1], q[3] / 2), np.multiply(q[2], q[4] / 2)))))
    for (o, ax, ay, la, lb, key, tw) in planes:
        # no pintar la grada si la camara esta detras de ella
        n = np.cross(ax, ay)
        if np.dot(cam.pos - np.asarray(o, float), n) < 0: n = -n
        textured_plane(img, cam, crowd_tex(key, tw, cheer), o, ax, ay, la, lb)
    wall(img, cam)
    return img

# ---------------------------------------------------------------- jugadores
TEAM = {
    'GB': dict(helmet=(222, 170, 40), hstripe=[(30, 84, 52), (240, 240, 240), (30, 84, 52)], mask=(150, 150, 150),
               jersey=(28, 82, 50), num=(240, 240, 236), numout=(222, 170, 40), sleeve=[(222, 170, 40), (240, 240, 236), (222, 170, 40)],
               pants=(214, 166, 44), pstripe=[(30, 84, 52), (240, 240, 236)], sock=(28, 82, 50), sockstripe=(222, 170, 40),
               shoe=(24, 24, 26), skin=None),
    'DAL': dict(helmet=(176, 184, 196), hstripe=[(24, 50, 120), (240, 240, 240), (24, 50, 120)], mask=(90, 90, 96),
                jersey=(242, 242, 240), num=(24, 50, 120), numout=(24, 50, 120), sleeve=[(24, 50, 120), (24, 50, 120)],
                pants=(168, 180, 196), pstripe=[(24, 50, 120), (240, 240, 240)], sock=(24, 50, 120), sockstripe=(240, 240, 240),
                shoe=(24, 24, 26), skin=None),
    'REF': dict(helmet=None, cap=(244, 244, 244), jersey='stripes', num=None, sleeve=None,
                pants=(240, 240, 238), pstripe=None, sock=(24, 24, 24), sockstripe=None, shoe=(18, 18, 18)),
    'COACH': dict(helmet=None, coat=(176, 140, 96), furhat=(70, 56, 44), pants=(50, 48, 52), shoe=(20, 20, 20)),
}
SKIN_T = [(224, 180, 150), (196, 148, 112), (120, 82, 60), (232, 194, 166), (92, 62, 46)]

# longitudes (yardas; jugador ~6 ft 2 in con casco)
THIGH, SHIN, FOOT = 0.50, 0.48, 0.16
TORSO, NECK = 0.56, 0.07
UARM, FARM = 0.33, 0.31
SHW, HIPW = 0.27, 0.11
HEAD_R = 0.14

def rotv(v, axis, ang):
    axis = axis / np.linalg.norm(axis)
    return v * math.cos(ang) + np.cross(axis, v) * math.sin(ang) + axis * np.dot(axis, v) * (1 - math.cos(ang))

def pose_joints(P, yaw, pz=None, pitch=0.0, legs=((0.1, 0.15), (-0.1, 0.15)), arms=((0.1, 0.4, 0.15), (0.1, 0.4, 0.15)),
                ground=True, roll=0.0, head_pitch=None):
    """P: (x,y) o (x,y,z) de la pelvis. yaw: direccion (rad) a la que mira. legs: (flexion de cadera, flexion de
    rodilla) [izq, der]. arms: (flexion de hombro, flexion de codo, abduccion). Devuelve dict de puntos 3D."""
    f = np.array([math.cos(yaw), math.sin(yaw), 0.0]); s = np.cross(UP, f)   # s = izquierda
    pel = np.array([P[0], P[1], P[2] if len(P) > 2 else 0.98])
    tdir = UP * math.cos(pitch) + f * math.sin(pitch)
    if roll: tdir = rotv(tdir, f, roll)
    J = {}
    neck = pel + tdir * TORSO
    J['pelvis'] = pel; J['neck'] = neck
    hp = head_pitch if head_pitch is not None else -pitch * 0.75
    hdir = rotv(tdir, s, -hp) if hp else tdir
    J['head'] = neck + hdir * (NECK + HEAD_R * 0.95) + f * 0.02
    J['face'] = f
    sh_c = neck - tdir * 0.06
    for i, sg in ((0, 1), (1, -1)):
        side = 'L' if sg > 0 else 'R'
        hip = pel + s * HIPW * sg
        hf, kf = legs[i]
        down = -tdir if not ground else -UP
        thd = rotv(-tdir, s, -hf) if True else down
        knee = hip + thd * THIGH
        shd = rotv(thd, s, kf)
        ank = knee + shd * SHIN
        toe = ank + rotv(shd, s, -1.45) * FOOT
        J['hip' + side], J['knee' + side], J['ank' + side], J['toe' + side] = hip, knee, ank, toe
        a, e, ab = arms[i]
        sh = sh_c + s * SHW * sg
        ud = rotv(-tdir, s, -a)
        if ab: ud = rotv(ud, f, ab * sg)
        el = sh + ud * UARM
        fd = rotv(ud, s, -e)
        if ab: fd = fd
        wr = el + fd * FARM
        J['sh' + side], J['el' + side], J['wr' + side] = sh, el, wr
    if ground and (len(P) <= 2):
        mz = min(J['ankL'][2], J['ankR'][2], J['toeL'][2] + 0.02, J['toeR'][2] + 0.02)
        dz = 0.07 - mz
        for k in J:
            if k != 'face': J[k] = J[k] + UP * dz
    J['f'] = f; J['s'] = s; J['tdir'] = tdir
    return J

def run_pose(P, yaw, phase, speed=1.0, lean=0.22, carry=None):
    ph = phase * 2 * math.pi
    A = 0.55 * speed
    legs = []
    for o in (0, math.pi):
        h = A * math.sin(ph + o) + 0.15
        k = 0.25 + 1.25 * speed * max(0.0, math.cos(ph + o - 0.4)) ** 1.4
        legs.append((h, k))
    arms = []
    for i, o in enumerate((math.pi, 0)):
        a = 0.7 * speed * math.sin(ph + o) + 0.15
        arms.append((a, 1.45, 0.12))
    if carry == 'R': arms[1] = (0.55, 1.9, 0.05)
    if carry == 'L': arms[0] = (0.55, 1.9, 0.05)
    return pose_joints(P, yaw, pitch=lean * speed, legs=tuple(legs), arms=tuple(arms))

def stance_pose(P, yaw, kind='3pt'):
    if kind == '3pt':
        return pose_joints(P, yaw, pitch=1.15, legs=((1.25, 1.55), (1.05, 1.35)), arms=((0.25, 0.1, 0.05), (0.55, 1.6, 0.25)), head_pitch=-0.75)
    if kind == 'qb':
        return pose_joints(P, yaw, pitch=0.5, legs=((0.75, 1.1), (0.75, 1.1)), arms=((0.75, 0.45, 0.05), (0.75, 0.45, 0.05)), head_pitch=-0.2)
    if kind == 'block':
        return pose_joints(P, yaw, pitch=0.85, legs=((0.95, 1.0), (0.35, 0.6)), arms=((1.35, 0.35, 0.1), (1.35, 0.35, 0.1)), head_pitch=-0.6)
    if kind == 'ready':
        return pose_joints(P, yaw, pitch=0.35, legs=((0.55, 0.8), (0.55, 0.8)), arms=((0.25, 0.7, 0.2), (0.25, 0.7, 0.2)))
    if kind == 'stand':
        return pose_joints(P, yaw, pitch=0.02, legs=((0.05, 0.08), (-0.05, 0.08)), arms=((0.05, 0.25, 0.12), (0.05, 0.25, 0.12)))
    if kind == 'hands_hips':
        return pose_joints(P, yaw, pitch=0.0, legs=((0.08, 0.06), (-0.08, 0.06)), arms=((0.35, 1.9, 0.75), (0.35, 1.9, 0.75)))
    raise ValueError(kind)

def blend(J1, J2, t):
    return {k: (J1[k] * (1 - t) + J2[k] * t) for k in J1}

# ---- dibujo con sombreado cilindrico
def _light_side(cam, A, B):
    """Devuelve el vector 2D perpendicular al segmento que apunta hacia la luz."""
    d = np.array(B[:2]) - np.array(A[:2]); n = np.array([-d[1], d[0]])
    nl = np.linalg.norm(n)
    if nl < 1e-6: return np.array([0.0, -1.0])
    n /= nl
    # direccion de la luz en pantalla
    sp = np.array([np.dot(SUN, cam.r), -np.dot(SUN, cam.u)])
    if np.dot(n, sp) < 0: n = -n
    return n

def capsule(draw, cam, A3, B3, rA, rB, col, outline=True, sh=True):
    a = cam.p(A3); b = cam.p(B3)
    if a[2] < 0.3 or b[2] < 0.3: return
    ra = rA * cam.f / a[2]; rb = rB * cam.f / b[2]
    A = np.array(a[:2]); B = np.array(b[:2])
    n = _light_side(cam, a, b)
    def quad(oa, ob, wa, wb, c):
        pa = A + n * oa; pb = B + n * ob
        pts = [tuple(pa + n * wa), tuple(pb + n * wb), tuple(pb - n * wb), tuple(pa - n * wa)]
        draw.polygon(pts, fill=c)
        draw.ellipse([pa[0] - wa, pa[1] - wa, pa[0] + wa, pa[1] + wa], fill=c)
        draw.ellipse([pb[0] - wb, pb[1] - wb, pb[0] + wb, pb[1] + wb], fill=c)
    dark = shade(col, 0.55)
    if outline: quad(0, 0, ra * 1.06, rb * 1.06, shade(col, 0.35))
    quad(0, 0, ra, rb, dark)
    quad(ra * 0.18, rb * 0.18, ra * 0.78, rb * 0.78, col)
    if sh: quad(ra * 0.5, rb * 0.5, ra * 0.28, rb * 0.28, mix(col, (255, 250, 240), 0.28))

def blob(draw, cam, C3, r, col, hl=True):
    c = cam.p(C3)
    if c[2] < 0.3: return
    R = r * cam.f / c[2]
    sp = np.array([np.dot(SUN, cam.r), -np.dot(SUN, cam.u)]); sp /= (np.linalg.norm(sp) + 1e-9)
    draw.ellipse([c[0] - R * 1.05, c[1] - R * 1.05, c[0] + R * 1.05, c[1] + R * 1.05], fill=shade(col, .35))
    draw.ellipse([c[0] - R, c[1] - R, c[0] + R, c[1] + R], fill=shade(col, .6))
    o = sp * R * 0.2
    draw.ellipse([c[0] + o[0] - R * .8, c[1] + o[1] - R * .8, c[0] + o[0] + R * .8, c[1] + o[1] + R * .8], fill=col)
    if hl:
        o = sp * R * 0.45
        draw.ellipse([c[0] + o[0] - R * .3, c[1] + o[1] - R * .3, c[0] + o[0] + R * .3, c[1] + o[1] + R * .3], fill=mix(col, (255, 255, 255), .45))

def shadow(img_draw_rgba, cam, J, alpha=110):
    """Sombra larga proyectada en el suelo en la direccion opuesta al sol."""
    d = img_draw_rgba
    sd = -SUN / SUN[2]
    def proj(P): Q = np.array(P) + sd * P[2]; Q[2] = 0.01; return Q
    segs = [('ankL', 'kneeL', .09), ('kneeL', 'hipL', .12), ('ankR', 'kneeR', .09), ('kneeR', 'hipR', .12),
            ('pelvis', 'neck', .2), ('shL', 'elL', .07), ('elL', 'wrL', .06), ('shR', 'elR', .07), ('elR', 'wrR', .06)]
    col = (20, 30, 40, alpha)
    for a, b, w in segs:
        pa, pb = cam.p(proj(J[a])), cam.p(proj(J[b]))
        if pa[2] < 0.3 or pb[2] < 0.3: continue
        ww = max(1, int(cam.f * w * 2 / ((pa[2] + pb[2]) / 2)))
        d.line([pa[:2], pb[:2]], fill=col, width=ww)
    h = cam.p(proj(J['head']))
    if h[2] > 0.3:
        R = cam.f * HEAD_R * 1.3 / h[2]
        d.ellipse([h[0] - R * 1.6, h[1] - R * .7, h[0] + R * 1.6, h[1] + R * .7], fill=col)

def stripe_on_capsule(draw, cam, A3, B3, t, r, col, w=0.03):
    P = np.array(A3) + (np.array(B3) - np.array(A3)) * t
    Q = np.array(A3) + (np.array(B3) - np.array(A3)) * min(1, t + w / max(1e-6, np.linalg.norm(np.array(B3) - np.array(A3))))
    capsule(draw, cam, P, Q, r, r, col, outline=False, sh=False)

def draw_player(draw, cam, J, team, num='', skin=0, breath=0.0, ball=None, helmet_on=True):
    T = TEAM[team]
    sk = SKIN_T[skin % len(SKIN_T)]
    f, s = J['f'], J['s']
    # orden de pintado: lo mas lejano primero (por lado)
    dl = cam.depth(J['shL']); dr = cam.depth(J['shR'])
    far, near = ('L', 'R') if dl > dr else ('R', 'L')
    facing_cam = np.dot(f, cam.fw) < 0
    def leg(side):
        hip, knee, ank, toe = J['hip' + side], J['knee' + side], J['ank' + side], J['toe' + side]
        if team == 'COACH':
            capsule(draw, cam, knee, ank, .075, .06, T['pants'])
            capsule(draw, cam, ank, toe, .055, .05, T['shoe'], sh=False)
            return
        capsule(draw, cam, hip, knee, .105, .085, T['pants'])
        if T.get('pstripe'):
            for i, c in enumerate(T['pstripe']):
                pass
        capsule(draw, cam, knee, ank, .072, .052, T['sock'])
        if T.get('sockstripe'):
            stripe_on_capsule(draw, cam, knee, ank, 0.18, .074, T['sockstripe'], .045)
            stripe_on_capsule(draw, cam, knee, ank, 0.32, .072, T['sockstripe'], .03)
        # rodilla (pantalon por debajo de la rodilla, como en la epoca)
        capsule(draw, cam, knee - (knee - hip) * 0.05, knee + (ank - knee) * 0.12, .09, .08, T['pants'], outline=False)
        capsule(draw, cam, ank, toe, .06, .05, T['shoe'], sh=False)
    def arm(side, sleeve=True):
        sh_, el, wr = J['sh' + side], J['el' + side], J['wr' + side]
        if team == 'COACH':
            capsule(draw, cam, sh_, el, .085, .075, T['coat']); capsule(draw, cam, el, wr, .075, .065, T['coat'])
            blob(draw, cam, wr + (wr - el) * 0.15, .05, (60, 46, 36), hl=False)
            return
        jc = T['jersey'] if T['jersey'] != 'stripes' else (36, 36, 38)
        capsule(draw, cam, sh_, el, .085, .07, jc)
        if team == 'REF':
            for t in (0.15, 0.45, 0.75): stripe_on_capsule(draw, cam, sh_, el, t, .087, (236, 236, 236), .05)
        capsule(draw, cam, el, wr, .068, .055, jc)
        if team == 'REF':
            for t in (0.2, 0.55): stripe_on_capsule(draw, cam, el, wr, t, .07, (236, 236, 236), .05)
        if T.get('sleeve'):
            for i, c in enumerate(T['sleeve']):
                stripe_on_capsule(draw, cam, sh_, el, 0.55 + i * 0.1, .088, c, .03)
        blob(draw, cam, wr + (wr - el) * 0.18, .05, sk if team != 'DAL' else (236, 236, 232), hl=False)
    def torso():
        pel, neck = J['pelvis'], J['neck']
        if team == 'COACH':
            # abrigo largo hasta la rodilla
            kneeM = (J['kneeL'] + J['kneeR']) / 2
            capsule(draw, cam, neck - J['tdir'] * .05, kneeM + J['tdir'] * .05, .2, .2, T['coat'])
            capsule(draw, cam, neck, pel, .21, .19, T['coat'])
            return
        jc = T['jersey'] if T['jersey'] != 'stripes' else (36, 36, 38)
        capsule(draw, cam, pel - J['tdir'] * 0.05, pel + J['tdir'] * .12, .17, .17, T['pants'])
        capsule(draw, cam, pel + J['tdir'] * 0.08, neck - J['tdir'] * 0.12, .17, .215 if team != 'REF' else .19, jc)
        if team == 'REF':
            for k in range(-3, 4):
                off = s * k * 0.06
                capsule(draw, cam, pel + J['tdir'] * 0.12 + off, neck - J['tdir'] * 0.14 + off * 1.15, .016, .016, (240, 240, 240), outline=False, sh=False)
        else:
            # hombreras
            capsule(draw, cam, J['shL'] + J['tdir'] * .02, J['shR'] + J['tdir'] * .02, .12, .12, jc)
        # numero (pecho o espalda segun la camara)
        if num:
            c = cam.p(pel + J['tdir'] * 0.36 + (f if facing_cam else -f) * 0.17)
            if c[2] > 0.3:
                size = cam.f * 0.2 / c[2]
                if size > 3:
                    draw.text((c[0], c[1]), num, font=font('Anton-Regular.ttf', size), fill=T['num'], anchor='mm',
                              stroke_width=max(1, int(size * .07)), stroke_fill=T['numout'])
    def head():
        H = J['head']
        if team == 'REF':
            blob(draw, cam, J['neck'] + J['tdir'] * .05, .06, sk, hl=False)
            blob(draw, cam, H, HEAD_R * .82, sk)
            # gorra blanca con visera
            blob(draw, cam, H + J['tdir'] * .05 - f * .01, HEAD_R * .84, T['cap'])
            capsule(draw, cam, H + J['tdir'] * .01 + f * .07, H + J['tdir'] * .0 + f * .17, .03, .03, shade(T['cap'], .85), outline=False)
            return
        if team == 'COACH':
            blob(draw, cam, H, HEAD_R * .8, sk)
            blob(draw, cam, H + J['tdir'] * .07, HEAD_R * .92, T['furhat'])
            capsule(draw, cam, J['neck'], J['neck'] + J['tdir'] * .06, .09, .09, (90, 30, 30), outline=False)   # bufanda
            return
        blob(draw, cam, J['neck'] + J['tdir'] * .03, .07, sk, hl=False)
        blob(draw, cam, H, HEAD_R, T['helmet'])
        # franja central del casco (de delante atras)
        if T.get('hstripe'):
            for i, c in enumerate(T['hstripe']):
                o = (i - 1) * 0.022
                A = H - f * HEAD_R * 0.8 + J['tdir'] * HEAD_R * 0.7 + s * o
                B = H + f * HEAD_R * 0.7 + J['tdir'] * HEAD_R * 0.75 + s * o
                M = H + J['tdir'] * HEAD_R * 1.0 + s * o
                if np.dot(J['tdir'], -cam.fw) > -0.2:
                    capsule(draw, cam, A, M, .012, .012, c, outline=False, sh=False)
                    capsule(draw, cam, M, B, .012, .012, c, outline=False, sh=False)
        # mascara y cara si mira hacia la camara
        if np.dot(f, -cam.fw) > -0.3:
            fc = H + f * HEAD_R * 0.78 - J['tdir'] * HEAD_R * 0.15
            blob(draw, cam, fc, HEAD_R * 0.48, shade(sk, .8), hl=False)
            for dz in (-0.03, 0.04):
                capsule(draw, cam, fc + s * .07 + J['tdir'] * dz + f * .05, fc - s * .07 + J['tdir'] * dz + f * .05, .011, .011, T['mask'], outline=False, sh=False)
            capsule(draw, cam, fc + J['tdir'] * .06 + f * .05, fc - J['tdir'] * .07 + f * .06, .011, .011, T['mask'], outline=False, sh=False)
        # orejera
        eside = s if np.dot(s, -cam.fw) > 0 else -s
        blob(draw, cam, H + eside * HEAD_R * 0.8 - J['tdir'] * .03, .035, shade(T['helmet'], .75), hl=False)
    leg(far); arm(far)
    if np.dot(f, cam.fw) > 0:   # de espaldas: cabeza detras del torso? no: cabeza siempre encima
        torso(); leg(near); head(); arm(near)
    else:
        torso(); leg(near); head(); arm(near)
    if ball is not None:
        football(draw, cam, ball)
    if breath > 0:
        vapor(draw, cam, J['head'] + f * HEAD_R * 1.4 + J['tdir'] * -.02, breath)

def football(draw, cam, P, ang=0.4):
    c = cam.p(P)
    if c[2] < 0.3: return
    R = cam.f * 0.16 / c[2]
    pts = []
    for i in range(20):
        t = i / 20 * 2 * math.pi
        x, y = R * math.cos(t), R * 0.6 * math.sin(t)
        pts.append((c[0] + x * math.cos(ang) - y * math.sin(ang), c[1] + x * math.sin(ang) + y * math.cos(ang)))
    draw.polygon(pts, fill=(112, 58, 30))
    draw.line([(c[0] - R * .3 * math.cos(ang), c[1] - R * .3 * math.sin(ang)), (c[0] + R * .3 * math.cos(ang), c[1] + R * .3 * math.sin(ang))], fill=(235, 235, 230), width=max(1, int(R * .12)))

def vapor(draw, cam, P, k):
    """Vaho: nubecillas blancas translucidas (dibujar en capa RGBA)."""
    c = cam.p(P)
    if c[2] < 0.3: return
    R = cam.f * 0.1 / c[2] * (0.6 + k)
    a = int(70 * (1 - k * 0.6))
    for i, (dx, dy, rr) in enumerate([(0, 0, 1), (R * .8, -R * .3, .8), (R * 1.5, -R * .7, .6)]):
        draw.ellipse([c[0] + dx - R * rr, c[1] + dy - R * rr, c[0] + dx + R * rr, c[1] + dy + R * rr], fill=(250, 252, 255, a))

def draw_people(img, cam, people, breath_t=0.0):
    """people: lista de dicts {J, team, num, skin, ball, breath}. Pinta sombras, cuerpos y vaho."""
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    for p in people:
        if p.get('shadow', True): shadow(sd, cam, p['J'])
    sh = sh.filter(ImageFilter.GaussianBlur(max(1, cam.W / 900)))
    img.paste(sh, (0, 0), sh)
    d = ImageDraw.Draw(img)
    for p in sorted(people, key=lambda q: -cam.depth(q['J']['pelvis'])):
        draw_player(d, cam, p['J'], p['team'], p.get('num', ''), p.get('skin', 0), 0, p.get('ball'))
    va = Image.new('RGBA', img.size, (0, 0, 0, 0))
    vd = ImageDraw.Draw(va)
    for i, p in enumerate(people):
        if p.get('team') in ('GB', 'DAL', 'REF', 'COACH'):
            k = ((breath_t * 0.7 + i * 0.37) % 1.0)
            if k < 0.6:
                J = p['J']
                vapor(vd, cam, J['head'] + J['f'] * HEAD_R * (1.2 + k) + UP * k * 0.08, k / 0.6)
    va = va.filter(ImageFilter.GaussianBlur(max(2, cam.W / 400)))
    img.paste(va, (0, 0), va)
