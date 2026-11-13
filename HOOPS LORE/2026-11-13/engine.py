"""Motor 3D sencillo para Hoops Lore: camara pinhole, Maple Leaf Gardens (pista sobre hielo),
gradas con publico de los 40, canastas de epoca y jugadores con esqueleto 3D."""
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT_DIR = __import__('os').path.join(__import__('os').path.dirname(__file__), 'fonts')
def font(name, size):
    return ImageFont.truetype(f"{FONT_DIR}/{name}", size)

# ---------------------------------------------------------------- camara
class Cam:
    def __init__(self, pos, look, f, W, H, oy=0.0):
        self.pos = np.array(pos, float); self.f = f; self.W = W; self.H = H; self.oy = oy
        fw = np.array(look, float) - self.pos; fw /= np.linalg.norm(fw)
        r = np.cross(fw, [0, 0, 1.0]); r /= np.linalg.norm(r)
        u = np.cross(r, fw)
        self.fw, self.r, self.u = fw, r, u
    def depth(self, P):
        return float(np.dot(np.asarray(P, float) - self.pos, self.fw))
    def p(self, P):
        d = np.asarray(P, float) - self.pos
        z = float(np.dot(d, self.fw)); z = max(z, 0.05)
        return (self.W / 2 + self.f * float(np.dot(d, self.r)) / z,
                self.H / 2 + self.oy - self.f * float(np.dot(d, self.u)) / z, z)
    def scale(self, P):
        return self.f / max(self.depth(P), 0.05)

# ---------------------------------------------------------------- geometria
COURT_L, COURT_W = 94.0, 50.0
RINK_X, RINK_Y, RINK_R = 100.0, 42.5, 28.0
BOARD_H = 3.6
FLOOR_X, FLOOR_Y = 50.0, 28.5   # el entarimado sobresale un poco de las lineas

def rink_path(n_corner=10, inset=0.0):
    X, Y, R = RINK_X - inset, RINK_Y - inset, RINK_R - inset
    pts = []
    for cx, cy, a0 in [(X - R, Y - R, 0), (-X + R, Y - R, 90), (-X + R, -Y + R, 180), (X - R, -Y + R, 270)]:
        for i in range(n_corner + 1):
            a = math.radians(a0 + 90 * i / n_corner)
            pts.append((cx + R * math.cos(a), cy + R * math.sin(a)))
    return pts

def lerp(a, b, t): return a + (b - a) * t
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease(t): t = clamp(t); return t * t * (3 - 2 * t)

def poly(draw, cam, pts3, fill, outline=None, width=1, near=0.5):
    C = [np.asarray(P, float) for P in pts3]
    dz = [float(np.dot(P - cam.pos, cam.fw)) for P in C]
    if min(dz) <= near:
        if max(dz) <= near: return
        out = []
        n = len(C)
        for i in range(n):
            A, B = C[i], C[(i + 1) % n]; da, db = dz[i], dz[(i + 1) % n]
            if da > near: out.append(A)
            if (da > near) != (db > near):
                t = (near - da) / (db - da); out.append(A + (B - A) * t)
        C = out
        if len(C) < 3: return
    pp = [cam.p(P) for P in C]
    draw.polygon([(q[0], q[1]) for q in pp], fill=fill, outline=outline)

def line3(draw, cam, A, B, col, w_ft, near=0.5):
    A = np.asarray(A, float); B = np.asarray(B, float)
    da, db = cam.depth(A), cam.depth(B)
    if da <= near and db <= near: return
    if da <= near: A = A + (B - A) * (near - da) / (db - da)
    elif db <= near: B = B + (A - B) * (near - db) / (da - db)
    a = cam.p(A); b = cam.p(B)
    w = max(1, int(round(w_ft * cam.f / ((a[2] + b[2]) / 2))))
    draw.line([(a[0], a[1]), (b[0], b[1])], fill=col, width=w)

# ---------------------------------------------------------------- fondo
COAT_COLS = [(38, 40, 52), (58, 46, 38), (72, 70, 68), (30, 30, 34), (92, 76, 58), (48, 54, 66),
             (110, 92, 70), (64, 38, 34), (84, 84, 88), (140, 128, 110), (36, 48, 40), (170, 160, 140)]
HAT_COLS = [(34, 30, 28), (52, 46, 40), (70, 64, 58), (28, 28, 32), (88, 74, 60), (60, 60, 64)]
SKIN = [(226, 188, 160), (214, 172, 140), (236, 200, 172), (200, 158, 126), (222, 182, 150)]
SEAT_SECTIONS = [(120, 40, 36), (36, 60, 110), (40, 96, 64), (150, 120, 50), (90, 90, 96)]

def build_stands(seed=3):
    """Lista de filas: cada fila = (puntos de la contrahuella/huella, color) y personas."""
    rng = random.Random(seed)
    rows, people = [], []
    NR = 34
    for side in (+1, -1):           # gradas laterales (y>0 lejos, y<0 cerca)
        for r in range(NR):
            y = side * (RINK_Y + 4 + r * 2.5); z = 4.0 + r * 1.85
            sec = SEAT_SECTIONS[min(r // 8, 4)]
            rows.append(('side', side, r, y, z, sec))
            x = -RINK_X + RINK_R - 6
            seat = 0
            while x < RINK_X - RINK_R + 6:
                seat += 1
                if seat % 15 == 0: x += 3.2; continue   # pasillo
                if rng.random() < 0.94:
                    people.append(dict(P=(x + rng.uniform(-.15, .15), y + side * 1.0, z), side=side,
                                       coat=rng.choice(COAT_COLS), skin=rng.choice(SKIN),
                                       hat=rng.choice(HAT_COLS) if rng.random() < 0.58 else None,
                                       lean=rng.uniform(-.15, .15), stand=rng.random() < 0.04))
                x += 1.85
    for side in (+1, -1):           # fondos
        for r in range(NR):
            x = side * (RINK_X + 4 + r * 2.5); z = 4.0 + r * 1.85
            sec = SEAT_SECTIONS[min(r // 8, 4)]
            rows.append(('end', side, r, x, z, sec))
            y = -RINK_Y + 4; seat = 0
            while y < RINK_Y - 4:
                seat += 1
                if seat % 15 == 0: y += 3.2; continue
                if rng.random() < 0.92:
                    people.append(dict(P=(x + side * 1.0, y + rng.uniform(-.15, .15), z), side=side * 2,
                                       coat=rng.choice(COAT_COLS), skin=rng.choice(SKIN),
                                       hat=rng.choice(HAT_COLS) if rng.random() < 0.58 else None,
                                       lean=rng.uniform(-.15, .15), stand=rng.random() < 0.04))
                y += 1.85
    # esquinas: gradas en arco para que no queden huecos
    for qx, qy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        cx, cy = qx * (RINK_X - RINK_R), qy * (RINK_Y - RINK_R)
        a0 = math.atan2(qy, 0) if False else 0
        for r in range(NR):
            R = RINK_R + 4 + r * 2.5; z = 4.0 + r * 1.85
            sec = SEAT_SECTIONS[min(r // 8, 4)]
            angs = (0, math.pi / 2) if (qx > 0 and qy > 0) else (math.pi / 2, math.pi) if (qx < 0 and qy > 0) else (math.pi, 1.5 * math.pi) if (qx < 0) else (1.5 * math.pi, 2 * math.pi)
            rows.append(('arc', (cx, cy, angs), r, R, z, sec))
            n = int(R * math.pi / 2 / 1.85)
            for i in range(n):
                if rng.random() < 0.92:
                    a = angs[0] + (angs[1] - angs[0]) * (i + .5) / n
                    people.append(dict(P=(cx + (R + 1) * math.cos(a), cy + (R + 1) * math.sin(a), z), side=0,
                                       coat=rng.choice(COAT_COLS), skin=rng.choice(SKIN),
                                       hat=rng.choice(HAT_COLS) if rng.random() < 0.58 else None,
                                       lean=rng.uniform(-.15, .15), stand=rng.random() < 0.04))
    return rows, people

STANDS = build_stands()

def row_segments(row):
    kind, side, r, c, z, col = row
    out = []
    if kind == 'side':
        x0, x1 = -RINK_X + RINK_R - 8, RINK_X - RINK_R + 8
        n = 12
        for i in range(n):
            a = x0 + (x1 - x0) * i / n; b = x0 + (x1 - x0) * (i + 1) / n
            out.append((('side', side, r, c, z, col, a, b), ((a + b) / 2, c + side * 1.2, z)))
    elif kind == 'end':
        y0, y1 = -RINK_Y + 2, RINK_Y - 2; n = 6
        for i in range(n):
            a = y0 + (y1 - y0) * i / n; b = y0 + (y1 - y0) * (i + 1) / n
            out.append((('end', side, r, c, z, col, a, b), (c + (1.2 if side > 0 else -1.2), (a + b) / 2, z)))
    else:
        cx, cy, (a0, a1) = side; n = 6
        for i in range(n):
            t0 = a0 + (a1 - a0) * i / n; t1 = a0 + (a1 - a0) * (i + 1) / n; tm = (t0 + t1) / 2
            out.append((('arc', (cx, cy, (t0, t1)), r, c, z, col), (cx + (c + 1.2) * math.cos(tm), cy + (c + 1.2) * math.sin(tm), z)))
    return out

SEAT_TINT = None
def draw_row(draw, cam, row, dim=1.0):
    if row[0] in ('side', 'end') and len(row) == 8:
        kind, side, r, c, z, col, a, b = row
    else:
        a = b = None
    if a is None: kind, side, r, c, z, col = row
    if SEAT_TINT is not None:
        col = tuple(int(col[i] * .3 + SEAT_TINT[i] * .7) for i in range(3))
    col = tuple(int(v * dim) for v in col)
    riser = tuple(int(v * 0.55 * dim) for v in (150, 140, 125))
    if kind == 'arc':
        cx, cy, (a0, a1) = side; R = c
        n = 2
        for i in range(n):
            t0 = a0 + (a1 - a0) * i / n; t1 = a0 + (a1 - a0) * (i + 1) / n
            A = (cx + R * math.cos(t0), cy + R * math.sin(t0)); B = (cx + R * math.cos(t1), cy + R * math.sin(t1))
            A2 = (cx + (R + 2.5) * math.cos(t0), cy + (R + 2.5) * math.sin(t0)); B2 = (cx + (R + 2.5) * math.cos(t1), cy + (R + 2.5) * math.sin(t1))
            poly(draw, cam, [(A[0], A[1], z - 1.85), (B[0], B[1], z - 1.85), (B[0], B[1], z), (A[0], A[1], z)], riser)
            poly(draw, cam, [(A[0], A[1], z), (B[0], B[1], z), (B2[0], B2[1], z), (A2[0], A2[1], z)], col)
        return
    if kind == 'side':
        x0, x1 = a, b
        y0, y1 = c, c + side * 2.5
        poly(draw, cam, [(x0, y0, z - 1.85), (x1, y0, z - 1.85), (x1, y0, z), (x0, y0, z)], riser)
        poly(draw, cam, [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)], col)
        # respaldo de los asientos
        poly(draw, cam, [(x0, y1 - side * .4, z), (x1, y1 - side * .4, z), (x1, y1 - side * .4, z + 1.2), (x0, y1 - side * .4, z + 1.2)],
             tuple(int(v * .8) for v in col))
    else:
        y0, y1 = a, b
        x0, xx = c, c + (2.5 if side > 0 else -2.5)
        poly(draw, cam, [(x0, y0, z - 1.85), (x0, y1, z - 1.85), (x0, y1, z), (x0, y0, z)], riser)
        poly(draw, cam, [(x0, y0, z), (x0, y1, z), (xx, y1, z), (xx, y0, z)], col)

def draw_fan_seated(draw, cam, p, dim=1.0):
    x, y, z = p['P']
    base = (x, y, z)
    u, v, d = cam.p(base)
    if d < 2: return
    s = cam.f / d
    if s < 0.6: return
    if u < -50 or u > cam.W + 50 or v < -50 or v > cam.H + 50: return
    dc = lambda c: tuple(int(k * dim) for k in c)
    h = 3.9 if p['stand'] else 2.9
    tw, th = 1.35 * s, 2.0 * s
    tu = u + p['lean'] * s
    # torso / abrigo
    draw.rounded_rectangle([tu - tw / 2, v - (h - 0.2) * s, tu + tw / 2, v - (h - 0.2) * s + th], radius=max(1, tw * .3), fill=dc(p['coat']))
    # cabeza
    hr = 0.40 * s; hv = v - (h + 0.35) * s
    draw.ellipse([tu - hr, hv - hr, tu + hr, hv + hr], fill=dc(p['skin']))
    if p['hat']:
        hc = dc(p['hat'])
        draw.ellipse([tu - hr * 1.7, hv - hr * .55, tu + hr * 1.7, hv - hr * .05], fill=hc)
        draw.rounded_rectangle([tu - hr * .95, hv - hr * 1.35, tu + hr * .95, hv - hr * .25], radius=max(1, hr * .3), fill=hc)
    else:
        draw.chord([tu - hr, hv - hr, tu + hr, hv + hr * .3], 180, 360, fill=dc((50, 38, 28)))

def render_background(cam, dim=1.0, extras=None, seed=1, min_depth=45, venue='toronto', occupancy=1.0):
    """Pinta el pabellon completo visto por `cam`. Devuelve Image RGB."""
    W, H = cam.W, cam.H
    img = Image.new('RGB', (W, H))
    # techo oscuro con degradado
    arr = np.zeros((H, W, 3), np.float32)
    g = np.linspace(0, 1, H)[:, None]
    arr[..., 0] = (14 + 18 * g); arr[..., 1] = (13 + 16 * g); arr[..., 2] = (16 + 18 * g)
    img = Image.fromarray(np.clip(arr * dim, 0, 255).astype(np.uint8))
    draw = ImageDraw.Draw(img)
    global SEAT_TINT
    SEAT_TINT = (96, 64, 46) if venue == 'hershey' else (112, 52, 44) if venue == 'minneapolis' else None
    lamp_z = 70
    if venue == 'hershey':
        # boveda de canon de hormigon (Hershey Sports Arena) con nervios
        def zarch(yy): return 66 + 38 * math.sqrt(max(0.0, 1 - (yy / 140.0) ** 2))
        ys = [-140 + 280 * i / 28 for i in range(29)]
        for i in range(-12, 12):
            x0, x1 = i * 10, (i + 1) * 10
            for j in range(len(ys) - 1):
                ya, yb = ys[j], ys[j + 1]
                t = 1 - abs((ya + yb) / 2) / 140
                col = tuple(int(c * dim) for c in (54 + 22 * (1 - t), 52 + 20 * (1 - t), 48 + 18 * (1 - t)))
                poly(draw, cam, [(x0, ya, zarch(ya)), (x1, ya, zarch(ya)), (x1, yb, zarch(yb)), (x0, yb, zarch(yb))], col)
        for i in range(-12, 13):
            x = i * 10
            for j in range(len(ys) - 1):
                line3(draw, cam, (x, ys[j], zarch(ys[j]) - .3), (x, ys[j + 1], zarch(ys[j + 1]) - .3), tuple(int(c * dim) for c in (84, 80, 72)), .9)
        # muro del fondo hasta la boveda
        for sx in (-1, 1):
            X = sx * 120
            poly(draw, cam, [(X, -140, 0), (X, 140, 0), (X, 140, 66), (X, -140, 66)], tuple(int(c * dim) for c in (58, 54, 48)))
        lamp_z = 52
    else:
        # cerchas del techo
        for i in range(-6, 7):
            x = i * 34
            line3(draw, cam, (x, -110, 92), (x, 110, 92), tuple(int(v * dim) for v in (40, 38, 36)), 1.2)
    for lx in range(-90, 91, 30):
        for ly in (-30, 0, 30):
            u, v, d = cam.p((lx, ly, lamp_z))
            if d < 3: continue
            r = 2.2 * cam.f / d
            g = Image.new('L', (int(r * 8) + 2, int(r * 8) + 2), 0); gd = ImageDraw.Draw(g)
            gd.ellipse([r * 2, r * 2, r * 6, r * 6], fill=int(90 * dim)); g = g.filter(ImageFilter.GaussianBlur(r))
            img.paste((255, 236, 190), (int(u - r * 4), int(v - r * 4)), g)
            draw.ellipse([u - r * .6, v - r * .35, u + r * .6, v + r * .35], fill=tuple(int(c * dim) for c in (255, 244, 214)))
            line3(draw, cam, (lx, ly, lamp_z + .5), (lx, ly, lamp_z + 40), tuple(int(c * dim) for c in (50, 48, 44)), .15)
    if venue in ('hershey', 'minneapolis'):
        floor = [(-200, -200, 0), (200, -200, 0), (200, 200, 0), (-200, 200, 0)]
        poly(draw, cam, floor, tuple(int(v * dim) for v in ((112, 110, 104) if venue == 'hershey' else (74, 64, 56))))
    rows, people = STANDS
    items = []
    for row in rows:
        for seg, P in row_segments(row):
            d = cam.depth(P)
            if d > 1 and (min_depth is None or d > min_depth): items.append((d + 0.8, 0, seg))
    occ_rng = random.Random(77)
    for p in people:
        if occupancy < 1:
            x_, y_, z_ = p['P']
            r_ = (z_ - 4) / 1.85
            # mas gente abajo y en el centro; huecos por bloques (secciones vacias)
            blk = (int((x_ + 200) // 22) * 7 + int((y_ + 200) // 22) * 13 + int(r_ // 6) * 5) % 10
            keep = occupancy * (1.5 - 1.1 * r_ / 34) * (1.2 - .45 * min(1, abs(x_) / 95)) * (.35 if blk in (2, 5, 7) else 1.0)
            if occ_rng.random() > keep: continue
        d = cam.depth(p['P'])
        if d > 2 and (min_depth is None or d > min_depth): items.append((d, 1, p))
    items.sort(key=lambda t: -t[0])
    # se dibuja fila a fila: primero la fila, luego su publico (ordenado por profundidad)
    for d, k, it in items:
        if k == 0: draw_row(draw, cam, it, dim)
        else: draw_fan_seated(draw, cam, it, dim)
    if venue == 'minneapolis':
        # Minneapolis Auditorium (1950): pista portatil sobre el suelo del auditorio, sin hielo ni vallas;
        # barandilla baja delante de la primera fila
        for sx in (-1, 1):
            poly(draw, cam, [(-RINK_X + RINK_R - 8, sx * (RINK_Y + 3.2), 0), (RINK_X - RINK_R + 8, sx * (RINK_Y + 3.2), 0),
                             (RINK_X - RINK_R + 8, sx * (RINK_Y + 3.2), 2.6), (-RINK_X + RINK_R - 8, sx * (RINK_Y + 3.2), 2.6)],
                 tuple(int(v * dim) for v in (58, 40, 32)))
    elif venue == 'hershey':
        # suelo de cemento de la pista de hockey (sin hielo)
        rng = random.Random(seed)
        for _ in range(140):
            x = rng.uniform(-RINK_X + 5, RINK_X - 5); y = rng.uniform(-RINK_Y + 1, RINK_Y - 1)
            if abs(x) < FLOOR_X and abs(y) < FLOOR_Y: continue
            line3(draw, cam, (x, y, .02), (x + rng.uniform(-6, 6), y + rng.uniform(-.5, .5), .02), tuple(int(v * dim) for v in (100, 98, 92)), .15)
    else:
        # hielo (suelo de la pista de hockey)
        ice = [(x, y, 0) for x, y in rink_path()]
        poly(draw, cam, ice, tuple(int(v * dim) for v in (214, 226, 234)))
        # marcas del hielo visibles fuera del entarimado: linea roja central y azules
        for xl, col, w in [(0, (178, 40, 44), 1.0), (-30, (40, 70, 150), 1.0), (30, (40, 70, 150), 1.0)]:
            for ys in [(-RINK_Y + .5, -FLOOR_Y), (FLOOR_Y, RINK_Y - .5)]:
                poly(draw, cam, [(xl - w / 2, ys[0], .01), (xl + w / 2, ys[0], .01), (xl + w / 2, ys[1], .01), (xl - w / 2, ys[1], .01)],
                     tuple(int(v * dim) for v in col))
        # rayado del hielo
        rng = random.Random(seed)
        for _ in range(260):
            x = rng.uniform(-RINK_X + 5, RINK_X - 5); y = rng.choice([rng.uniform(-RINK_Y + 1, -FLOOR_Y), rng.uniform(FLOOR_Y, RINK_Y - 1), rng.uniform(-RINK_Y, RINK_Y)])
            if abs(x) < FLOOR_X and abs(y) < FLOOR_Y: continue
            a = rng.uniform(0, math.pi)
            line3(draw, cam, (x, y, .02), (x + 3 * math.cos(a), y + 3 * math.sin(a), .02), tuple(int(v * dim) for v in (196, 208, 218)), .08)
    draw_court(img, cam, dim)
    draw = ImageDraw.Draw(img)
    # vallas de hockey (ordenadas de lejos a cerca)
    path = rink_path(8) if venue not in ('hershey', 'minneapolis') else []
    segs = []
    for i in range(len(path)):
        a = path[i]; b = path[(i + 1) % len(path)]
        segs.append((cam.depth(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 1.5)), a, b))
    segs.sort(key=lambda s: -s[0])
    for d, a, b in segs:
        if d < 1: continue
        wcol = tuple(int(v * dim) for v in (236, 234, 226))
        poly(draw, cam, [(a[0], a[1], 0), (b[0], b[1], 0), (b[0], b[1], BOARD_H), (a[0], a[1], BOARD_H)], wcol)
        poly(draw, cam, [(a[0], a[1], 0), (b[0], b[1], 0), (b[0], b[1], 0.7), (a[0], a[1], 0.7)], tuple(int(v * dim) for v in (196, 170, 84)))
        line3(draw, cam, (a[0], a[1], BOARD_H), (b[0], b[1], BOARD_H), tuple(int(v * dim) for v in (90, 70, 50)), .35)
        # postes de la valla
        line3(draw, cam, (a[0], a[1], 0.7), (a[0], a[1], BOARD_H), tuple(int(v * dim) for v in (200, 198, 190)), .12)
    if extras:
        for fn in extras: fn(img, cam, dim)
    return img

LANE_HALF = 3.0
def draw_court(img, cam, dim=1.0):
    draw = ImageDraw.Draw(img)
    base = np.array((196, 142, 84)) * dim
    poly(draw, cam, [(-FLOOR_X, -FLOOR_Y, .05), (FLOOR_X, -FLOOR_Y, .05), (FLOOR_X, FLOOR_Y, .05), (-FLOOR_X, FLOOR_Y, .05)], tuple(int(v) for v in base))
    # canto del entarimado (se ve que esta "puesto" sobre el hielo)
    for (a, b) in [((-FLOOR_X, -FLOOR_Y), (FLOOR_X, -FLOOR_Y)), ((FLOOR_X, -FLOOR_Y), (FLOOR_X, FLOOR_Y)), ((-FLOOR_X, FLOOR_Y), (-FLOOR_X, -FLOOR_Y))]:
        poly(draw, cam, [(a[0], a[1], 0), (b[0], b[1], 0), (b[0], b[1], .05), (a[0], a[1], .05)], tuple(int(v * .55 * dim) for v in (196, 142, 84)))
    # tablas: franjas de tono ligeramente distinto
    rng = random.Random(7)
    y = -FLOOR_Y
    while y < FLOOR_Y:
        w = 0.9
        x = -FLOOR_X + rng.uniform(0, 8)
        k = rng.uniform(.9, 1.08)
        col = tuple(int(clamp(v * k, 0, 255)) for v in base)
        poly(draw, cam, [(-FLOOR_X, y, .051), (FLOOR_X, y, .051), (FLOOR_X, y + w, .051), (-FLOOR_X, y + w, .051)], col)
        line3(draw, cam, (-FLOOR_X, y, .052), (FLOOR_X, y, .052), tuple(int(v * .82) for v in base), .03)
        # juntas a tope
        while x < FLOOR_X:
            line3(draw, cam, (x, y, .052), (x, y + w, .052), tuple(int(v * .8) for v in base), .03)
            x += rng.uniform(6, 12)
        y += w
    lc = tuple(int(v * dim) for v in (40, 26, 18)); LW = .17
    L2, W2 = COURT_L / 2, COURT_W / 2
    for a, b in [((-L2, -W2), (L2, -W2)), ((L2, -W2), (L2, W2)), ((L2, W2), (-L2, W2)), ((-L2, W2), (-L2, -W2)), ((0, -W2), (0, W2))]:
        line3(draw, cam, (a[0], a[1], .06), (b[0], b[1], .06), lc, LW)
    def circle(cx, cy, r, a0=0, a1=360, dashed=False):
        n = 48
        for i in range(n):
            if dashed and i % 2: continue
            t0 = math.radians(a0 + (a1 - a0) * i / n); t1 = math.radians(a0 + (a1 - a0) * (i + 1) / n)
            line3(draw, cam, (cx + r * math.cos(t0), cy + r * math.sin(t0), .06), (cx + r * math.cos(t1), cy + r * math.sin(t1), .06), lc, LW)
    circle(0, 0, 6)
    for s in (-1, 1):
        ftx = s * (L2 - 19)
        # carril estrecho de 6 pies (regla de la epoca)
        for yy in (-LANE_HALF, LANE_HALF):
            line3(draw, cam, (s * L2, yy, .06), (ftx, yy, .06), lc, LW)
        line3(draw, cam, (ftx, -6, .06), (ftx, 6, .06), lc, LW)
        if s > 0:
            circle(ftx, 0, 6, 90, 270); circle(ftx, 0, 6, -90, 90, dashed=True)
        else:
            circle(ftx, 0, 6, -90, 90); circle(ftx, 0, 6, 90, 270, dashed=True)

# ---------------------------------------------------------------- canasta de epoca
RIM_H = 10.0   # altura del aro en pies (12 en el experimento del 7 mar 1954)
def draw_basket(draw, cam, s, dim=1.0, k=1.0, off=(0, 0), rim_h=None):
    """Canasta en x = s*... con poste-soporte de tubo y tablero de madera blanco. rim_h: altura del aro (pies)."""
    dz = (RIM_H if rim_h is None else rim_h) - 10.0
    def P(x, y, z):
        u, v, d = cam.p((x, y, z)); return ((u - off[0]) * k, (v - off[1]) * k, d)
    def L(A, B, col, w):
        a = P(*A); b = P(*B)
        if a[2] < .5 or b[2] < .5: return
        ww = max(1, int(w * cam.f * k / ((a[2] + b[2]) / 2)))
        draw.line([a[:2], b[:2]], fill=col, width=ww)
    bx = s * (COURT_L / 2 - 4)   # tablero 4 pies dentro de la linea de fondo
    pipe = tuple(int(v * dim) for v in (70, 72, 76))
    # base y poste fuera de la pista
    L((s * 53, -1.5, 0), (s * 53, 1.5, 0), pipe, .5)
    L((s * 53, 0, 0), (s * 53, 0, 13.2 + dz), pipe, .45)
    L((s * 53, 0, 13.2 + dz), (bx + s * .3, 0, 13.2 + dz), pipe, .35)
    L((s * 53, 0, 4), (bx + s * .3, 0, 12 + dz), pipe, .25)
    L((s * 53, -1.2, 0), (s * 53, 0, 6), pipe, .2); L((s * 53, 1.2, 0), (s * 53, 0, 6), pipe, .2)
    # tablero
    q = [P(bx, -3, 9 + dz), P(bx, 3, 9 + dz), P(bx, 3, 13 + dz), P(bx, -3, 13 + dz)]
    if min(t[2] for t in q) > .5:
        draw.polygon([t[:2] for t in q], fill=tuple(int(v * dim) for v in (238, 236, 228)), outline=tuple(int(v * dim) for v in (60, 50, 40)))
        q2 = [P(bx - s * .02, -1, 10 + dz), P(bx - s * .02, 1, 10 + dz), P(bx - s * .02, 1, 11.5 + dz), P(bx - s * .02, -1, 11.5 + dz)]
        draw.polygon([t[:2] for t in q2], outline=tuple(int(v * dim) for v in (60, 50, 40)))
    # aro y red
    rx = bx - s * 0.75
    ring = []
    for i in range(25):
        a = 2 * math.pi * i / 24
        ring.append((rx + .75 * math.cos(a), .75 * math.sin(a), 10 + dz))
    rc = tuple(int(v * dim) for v in (200, 80, 30))
    net = tuple(int(v * dim) for v in (235, 235, 235))
    for i in range(0, 24, 2):
        A = ring[i]; B = (rx + .45 * math.cos(2 * math.pi * (i + 1) / 24), .45 * math.sin(2 * math.pi * (i + 1) / 24), 8.6 + dz)
        L(A, B, net, .05)
        C = ring[(i + 2) % 24]; L(C, B, net, .05)
    for i in range(24):
        L(ring[i], ring[i + 1], rc, .09)
    L((bx, 0, 10 + dz), (rx + s * .75, 0, 10 + dz), rc, .1)

# ---------------------------------------------------------------- personas
TEAMS = {
    'TOR': dict(jersey=(240, 240, 236), trim=(28, 64, 150), shorts=(240, 240, 236), strim=(28, 64, 150),
                socks=(28, 64, 150), shoes=(240, 238, 230), num=(28, 64, 150)),
    'NY': dict(jersey=(30, 70, 160), trim=(236, 120, 30), shorts=(30, 70, 160), strim=(236, 120, 30),
               socks=(236, 120, 30), shoes=(30, 30, 32), num=(255, 255, 255)),
}

def pose_stand(t=0, arms_down=True):
    return dict(lh=0.05, lk=0.08, rh=-0.03, rk=0.06, ls=0.12, le=0.25, la=0.12, rs=0.1, re=0.25, ra=0.12, lift=0, lean=0.02)

def pose_run(ph, speed=1.0):
    s = math.sin(ph); c = math.cos(ph)
    a = 0.42 * speed
    return dict(lh=a * s, lk=0.2 + 0.85 * speed * max(0, -c) ** 1.5, rh=-a * s, rk=0.2 + 0.85 * speed * max(0, c) ** 1.5,
                ls=-0.5 * speed * s, le=1.2, la=0.12, rs=0.5 * speed * s, re=1.2, ra=0.12,
                lift=0.12 * speed * abs(math.sin(ph)), lean=0.18 * speed)

def pose_jump(t, arm='both', reach=1.0):
    """t: 0..1 a lo largo del salto."""
    up = math.sin(math.pi * clamp(t)) * 2.4
    crouch = max(0, 1 - t * 4) * 0.6
    d = dict(lh=0.35 * crouch + 0.15, lk=0.6 * crouch + 0.35, rh=0.1 + 0.35 * crouch, rk=0.55 * crouch + 0.45,
             ls=2.9 * reach, le=0.15, la=0.15, rs=2.9 * reach if arm == 'both' else 0.3, re=0.2 if arm == 'both' else 1.2, ra=0.15,
             lift=up - crouch * 0.6, lean=-0.05)
    return d

def pose_dribble(ph):
    d = pose_run(ph, 0.55)
    d['rs'] = 0.65 + 0.15 * math.sin(ph * 2); d['re'] = 0.5; d['ra'] = 0.35
    return d

def pose_slip(t):
    """resbalon: pie de apoyo se va hacia delante, brazos abiertos."""
    k = ease(t)
    return dict(lh=0.2 + 0.9 * k, lk=0.1, rh=-0.3 - 0.2 * k, rk=0.7 * k + 0.2, ls=0.8 + 0.8 * k, le=0.3, la=0.9 * k + 0.2,
                rs=0.6 + 0.9 * k, re=0.4, ra=0.9 * k + 0.2, lift=-0.5 * k, lean=-0.45 * k)

def pose_set_shot(t):
    """tiro a dos manos de la epoca: carga a la altura del pecho, extiende arriba."""
    k = ease((t - 0.2) / 0.5)
    return dict(lh=0.1, lk=0.4 * (1 - k) + 0.05, rh=0.0, rk=0.4 * (1 - k) + 0.05,
                ls=1.4 + 1.3 * k, le=1.6 * (1 - k) + 0.1, la=0.25, rs=1.4 + 1.3 * k, re=1.6 * (1 - k) + 0.1, ra=0.25,
                lift=0.5 * k, lean=-0.05)

def skeleton(x, y, face, pose, height=6.4):
    k = height / 6.4
    th = 1.72 * k; sh = 1.72 * k; ua = 1.12 * k; fa = 1.08 * k
    lift = pose.get('lift', 0)
    lean = pose.get('lean', 0)
    hipz = 3.38 * k + lift
    cf, sf = math.cos(face), math.sin(face)
    def W(lx, ly, lz):
        return (x + lx * cf - ly * sf, y + lx * sf + ly * cf, lz)
    J = {}
    J['pelvis'] = W(0, 0, hipz)
    chest = (math.sin(lean) * 2.0 * k, 0, hipz + math.cos(lean) * 2.0 * k)
    J['neck'] = W(chest[0] * 1.12, 0, hipz + math.cos(lean) * 2.3 * k)
    J['head'] = W(chest[0] * 1.2, 0, hipz + math.cos(lean) * 2.72 * k)
    for side, sy in (('l', 0.44), ('r', -0.44)):
        hip = (0, sy * k, hipz)
        a = pose[side + 'h']; kn = pose[side + 'k']
        knee = (hip[0] + th * math.sin(a), hip[1], hip[2] - th * math.cos(a))
        b = a - kn
        ank = (knee[0] + sh * math.sin(b), knee[1], knee[2] - sh * math.cos(b))
        toe = (ank[0] + 0.75 * k * math.cos(b * 0.3), ank[1], ank[2] - 0.1)
        J[side + 'hip'] = W(*hip); J[side + 'knee'] = W(*knee); J[side + 'ank'] = W(*ank); J[side + 'toe'] = W(*toe)
        shp = (chest[0], sy * 1.68 * k, chest[2] - 0.1 * k)
        s_ = pose[side + 's']; e_ = pose[side + 'e']; ab = pose[side + 'a']
        sgn = 1 if side == 'l' else -1
        el = (shp[0] + ua * math.sin(s_) * math.cos(ab), shp[1] + sgn * ua * math.sin(ab), shp[2] - ua * math.cos(s_) * math.cos(ab))
        s2 = s_ + e_
        wr = (el[0] + fa * math.sin(s2) * math.cos(ab * .6), el[1] + sgn * fa * math.sin(ab * .6), el[2] - fa * math.cos(s2) * math.cos(ab * .6))
        J[side + 'sh'] = W(*shp); J[side + 'el'] = W(*el); J[side + 'wr'] = W(*wr)
    return J

def draw_player(draw, cam, x, y, face, pose, team=None, number=None, height=6.4, skin=(226, 188, 160),
                hair=(54, 40, 28), k=1.0, off=(0, 0), civilian=None, dim=1.0, ref=False):
    J = skeleton(x, y, face, pose, height)
    PP = {n: cam.p(P) for n, P in J.items()}
    if PP['pelvis'][2] < 1: return J
    def pt(n): u, v, d = PP[n]; return ((u - off[0]) * k, (v - off[1]) * k)
    def sc(n): return cam.f * k / PP[n][2]
    def D(c): return tuple(int(v * dim) for v in c)
    def limb(a, b, w, col):
        A = pt(a); B = pt(b); ww = max(1, w * (sc(a) + sc(b)) / 2)
        draw.line([A, B], fill=D(col), width=int(round(ww)))
        for P_, s_ in ((A, sc(a)), (B, sc(b))):
            r = w * s_ / 2
            draw.ellipse([P_[0] - r, P_[1] - r, P_[0] + r, P_[1] + r], fill=D(col))
    def taper_pts(A, sa, B, sb, wa, wb, col):
        ra = wa * sa / 2; rb = wb * sb / 2
        dx, dy = B[0] - A[0], B[1] - A[1]; L = math.hypot(dx, dy) or 1e-6
        nx, ny = -dy / L, dx / L
        draw.polygon([(A[0] + nx * ra, A[1] + ny * ra), (B[0] + nx * rb, B[1] + ny * rb),
                      (B[0] - nx * rb, B[1] - ny * rb), (A[0] - nx * ra, A[1] - ny * ra)], fill=D(col))
        for P_, r in ((A, ra), (B, rb)):
            draw.ellipse([P_[0] - r, P_[1] - r, P_[0] + r, P_[1] + r], fill=D(col))
    def taper(a, b, wa, wb, col):
        taper_pts(pt(a), sc(a), pt(b), sc(b), wa, wb, col)
    def seg_point(a, b, t):
        A = np.array(J[a]); B = np.array(J[b]); Pq = A + (B - A) * t
        u, v, d = cam.p(Pq); return ((u - off[0]) * k, (v - off[1]) * k), cam.f * k / d, tuple(Pq)
    # orden: lado lejano primero
    dl = cam.depth(J['lsh']); dr = cam.depth(J['rsh'])
    far, near = ('l', 'r') if dl > dr else ('r', 'l')
    if civilian:
        coat, trousers, hat = civilian
        for sd in (far, near):
            limb(sd + 'hip', sd + 'knee', .55, trousers); limb(sd + 'knee', sd + 'ank', .48, trousers)
            limb(sd + 'ank', sd + 'toe', .34, (24, 20, 18))
        limb(far + 'sh', far + 'el', .42, coat); limb(far + 'el', far + 'wr', .38, coat)
        # abrigo largo
        T = [pt('lsh'), pt('rsh')]
        rk = seg_point('rhip', 'rknee', .7)[0]; lk = seg_point('lhip', 'lknee', .7)[0]
        if dl > dr: quad = [pt('lsh'), pt('rsh'), rk, lk]
        else: quad = [pt('lsh'), pt('rsh'), rk, lk]
        draw.polygon(quad, fill=D(coat))
        limb('lsh', 'rsh', .5, coat)
        limb(near + 'sh', near + 'el', .42, coat); limb(near + 'el', near + 'wr', .38, coat)
        for sd in (far, near):
            w_ = pt(sd + 'wr'); r = .2 * sc(sd + 'wr'); draw.ellipse([w_[0] - r, w_[1] - r, w_[0] + r, w_[1] + r], fill=D(skin))
        h = pt('head'); r = .42 * sc('head')
        draw.ellipse([h[0] - r * .55, h[1] + r * .5, h[0] + r * .55, h[1] + r * 1.6], fill=D(skin))
        draw.ellipse([h[0] - r, h[1] - r, h[0] + r, h[1] + r], fill=D(skin))
        if hat:
            draw.ellipse([h[0] - r * 1.75, h[1] - r * .65, h[0] + r * 1.75, h[1] - r * .05], fill=D(hat))
            draw.rounded_rectangle([h[0] - r * .95, h[1] - r * 1.45, h[0] + r * .95, h[1] - r * .3], radius=max(1, r * .3), fill=D(hat))
        return J
    T = TEAMS[team] if team else None
    if ref:
        T = dict(jersey=(206, 206, 200), trim=(40, 40, 44), shorts=(34, 34, 38), strim=(34, 34, 38), socks=(30, 30, 32), shoes=(24, 24, 26), num=(30, 30, 30))
    # piernas (formas anatómicas con grosor variable, sin rodilleras)
    for sd in (far, near):
        if ref:
            taper(sd + 'hip', sd + 'knee', .62, .46, T['shorts']); taper(sd + 'knee', sd + 'ank', .46, .40, T['shorts'])
        else:
            # muslo: ancho en la cadera, se estrecha hacia la rodilla
            taper(sd + 'hip', sd + 'knee', .66, .36, skin)
            # gemelo: estrecho en la rodilla, abultado arriba, fino en el tobillo
            mid, smid, _ = seg_point(sd + 'knee', sd + 'ank', .32)
            taper_pts(pt(sd + 'knee'), sc(sd + 'knee'), mid, smid, .35, .42, skin)
            taper_pts(mid, smid, pt(sd + 'ank'), sc(sd + 'ank'), .42, .25, skin)
            # medias hasta media pantorrilla con franja
            a2, s2, _ = seg_point(sd + 'knee', sd + 'ank', .45)
            taper_pts(a2, s2, pt(sd + 'ank'), sc(sd + 'ank'), .43, .28, T['socks'])
            a3, s3, _ = seg_point(sd + 'knee', sd + 'ank', .45)
            a4, s4, _ = seg_point(sd + 'knee', sd + 'ank', .49)
            taper_pts(a3, s3, a4, s4, .43, .42, T['trim'])
        # zapatilla de lona de caña alta
        limb(sd + 'ank', sd + 'toe', .34, T['shoes'])
        an = pt(sd + 'ank'); r = .17 * sc(sd + 'ank')
        draw.ellipse([an[0] - r, an[1] - r, an[0] + r, an[1] + r], fill=D(T['shoes']))
    # brazo lejano
    if ref:
        limb(far + 'sh', far + 'el', .36, T['jersey']); limb(far + 'el', far + 'wr', .3, T['jersey'])
    else:
        taper(far + 'sh', far + 'el', .40, .27, skin); taper(far + 'el', far + 'wr', .29, .19, skin)
    # pantalon corto de cintura alta (hasta medio muslo)
    sh_pts = []
    for sd in ('l', 'r'):
        p1, s1, _ = seg_point(sd + 'hip', sd + 'knee', .55)
        taper_pts(pt(sd + 'hip'), sc(sd + 'hip'), p1, s1, .70, .52, T['shorts'])
    hp = [pt('lhip'), pt('rhip')]
    pel = pt('pelvis'); sp = sc('pelvis')
    draw.ellipse([pel[0] - .66 * sp, pel[1] - .55 * sp, pel[0] + .66 * sp, pel[1] + .35 * sp], fill=D(T['shorts']))
    # cinturon/franja del pantalon
    draw.line([(pel[0] - .66 * sp, pel[1] - .4 * sp), (pel[0] + .66 * sp, pel[1] - .4 * sp)], fill=D(T['strim']), width=max(1, int(.14 * sp)))
    # camiseta de tirantes
    nk = pt('neck')
    lsh, rsh = pt('lsh'), pt('rsh')
    torso = [lsh, rsh, (pel[0] + (rsh[0] - nk[0]) * .75, pel[1] - .35 * sp), (pel[0] + (lsh[0] - nk[0]) * .75, pel[1] - .35 * sp)]
    draw.polygon(torso, fill=D(T['jersey']))
    limb('lsh', 'rsh', .42, T['jersey'])
    # ribete de cuello y sisas
    r = .26 * sc('neck')
    draw.ellipse([nk[0] - r, nk[1] - r * .6, nk[0] + r, nk[1] + r * .9], fill=D(T['trim']))
    draw.ellipse([nk[0] - r * .7, nk[1] - r * .5, nk[0] + r * .7, nk[1] + r * .6], fill=D(skin))
    # dorsal
    if number is not None and sp > 9:
        cx = (lsh[0] + rsh[0] + torso[2][0] + torso[3][0]) / 4; cy = (lsh[1] + rsh[1] + torso[2][1] + torso[3][1]) / 4
        wpx = abs(lsh[0] - rsh[0])
        if wpx > .5 * sp:
            f = font('Graduate-Regular.ttf', max(6, int(.75 * sp)))
            draw.text((cx, cy), str(number), font=f, fill=D(T['num']), anchor='mm', stroke_width=max(1, int(.04 * sp)), stroke_fill=D(T['trim']))
    # brazo cercano
    col = T['jersey'] if ref else skin
    taper(near + 'sh', near + 'el', .40, .27, col); taper(near + 'el', near + 'wr', .29, .19, col)
    for sd in (far, near):
        w_ = pt(sd + 'wr'); r = .19 * sc(sd + 'wr'); draw.ellipse([w_[0] - r, w_[1] - r, w_[0] + r, w_[1] + r], fill=D(skin))
    # cabeza y pelo corto con raya
    h = pt('head'); r = .4 * sc('head')
    draw.ellipse([h[0] - r * .5, h[1] + r * .4, h[0] + r * .5, h[1] + r * 1.5], fill=D(skin))
    draw.ellipse([h[0] - r, h[1] - r * 1.05, h[0] + r, h[1] + r * 1.05], fill=D(skin))
    draw.chord([h[0] - r * 1.02, h[1] - r * 1.12, h[0] + r * 1.02, h[1] + r * .35], 180, 360, fill=D(hair))
    # orejas
    for sx in (-1, 1):
        draw.ellipse([h[0] + sx * r * .92 - r * .14, h[1] - r * .1, h[0] + sx * r * .92 + r * .14, h[1] + r * .3], fill=D(tuple(int(v * .92) for v in skin)))
    return J

def draw_ball(draw, cam, P, k=1.0, off=(0, 0), dim=1.0, spin=0.0):
    u, v, d = cam.p(P)
    if d < 1: return
    s = cam.f * k / d; r = .4 * s
    u = (u - off[0]) * k; v = (v - off[1]) * k
    draw.ellipse([u - r, v - r, u + r, v + r], fill=tuple(int(c * dim) for c in (150, 84, 40)), outline=tuple(int(c * dim) for c in (60, 32, 16)), width=max(1, int(r * .08)))
    # costuras y cordones (balon de cuero de la epoca)
    if r > 4:
        a = spin
        draw.arc([u - r * .9, v - r * .4, u + r * .9, v + r * .4], 0 + math.degrees(a), 180 + math.degrees(a), fill=(60, 32, 16), width=max(1, int(r * .07)))
        draw.line([(u - r * .9 * math.cos(a), v - r * .9 * math.sin(a)), (u + r * .9 * math.cos(a), v + r * .9 * math.sin(a))], fill=(60, 32, 16), width=max(1, int(r * .07)))
        draw.line([(u - r * .25, v - r * .5), (u + r * .25, v - r * .5)], fill=(230, 220, 200), width=max(1, int(r * .12)))
        # brillo
        draw.ellipse([u - r * .55, v - r * .65, u - r * .1, v - r * .3], fill=tuple(int(c * dim) for c in (180, 110, 60)))

def shadow(draw, cam, x, y, rad=1.2, k=1.0, off=(0, 0), alpha=70):
    pts = []
    for i in range(16):
        a = 2 * math.pi * i / 16
        u, v, d = cam.p((x + rad * math.cos(a), y + rad * .8 * math.sin(a), .07))
        pts.append(((u - off[0]) * k, (v - off[1]) * k))
    draw.polygon(pts, fill=(60, 40, 22))
