"""Prem Lore — mundo 3D de fútbol: estadio nocturno con focos, césped a franjas,
cámaras de TV (proyección perspectiva) y jugadores con equipación completa."""
import numpy as np, cv2, math, random
from PIL import Image, ImageDraw, ImageFilter

W, H = 1080, 1920
PL, PW = 105.0, 68.0            # campo
A = '/home/claude/prem/assets/'

def norm(v):
    v = np.asarray(v, float); return v / (np.linalg.norm(v) + 1e-9)

# ------------------------------------------------------------------ cámara
class Cam:
    def __init__(s, pos, target, fovh):
        s.pos = np.array(pos, float); s.target = np.array(target, float)
        s.f = (W / 2) / math.tan(math.radians(fovh) / 2)
        s.fwd = norm(s.target - s.pos)
        s.right = norm(np.cross(s.fwd, [0, 0, 1]))
        s.up = np.cross(s.right, s.fwd)
        s.Ru = s.f * s.right + (W / 2) * s.fwd
        s.Rv = -s.f * s.up + (H / 2) * s.fwd
        s.Rw = s.fwd
        s.M = np.stack([s.Ru, s.Rv, s.Rw])
    def depth(s, p):
        return float(np.dot(np.asarray(p, float) - s.pos, s.fwd))
    def proj(s, p):
        d = np.asarray(p, float) - s.pos
        zc = d @ s.fwd
        u = W / 2 + s.f * (d @ s.right) / zc
        v = H / 2 - s.f * (d @ s.up) / zc
        return u, v, zc
    def plane_H(s, O, a, b, ppm):
        """homografía textura(px) -> imagen para el plano O + a*s/ppm + b*t/ppm"""
        O = np.asarray(O, float); a = np.asarray(a, float); b = np.asarray(b, float)
        cols = [s.M @ a / ppm, s.M @ b / ppm, s.M @ (O - s.pos)]
        return np.stack(cols, 1)
    def horizon_v(s):
        if abs(s.up[2]) < 1e-6: return -1e9
        return H / 2 + s.f * s.fwd[2] / s.up[2]

# ------------------------------------------------------------------ texturas
GPPM = 24.0
GX0, GY0, GX1, GY1 = -14.0, -12.0, 119.0, 80.0

def make_ground():
    w = int((GX1 - GX0) * GPPM); h = int((GY1 - GY0) * GPPM)
    rng = np.random.default_rng(3)
    X = GX0 + (np.arange(w) + .5) / GPPM
    Y = GY0 + (np.arange(h) + .5) / GPPM
    XX, YY = np.meshgrid(X, Y)
    stripe = (np.floor((XX + 0.0) / (PL / 18)) % 2).astype(np.float32)
    light = np.array([70, 146, 62], np.float32); dark = np.array([54, 122, 50], np.float32)
    img = light[None, None] * (1 - stripe[..., None]) + dark[None, None] * stripe[..., None]
    n = rng.normal(0, 1, (h // 4 + 1, w // 4 + 1)).astype(np.float32)
    n = cv2.resize(n, (w, h), interpolation=cv2.INTER_CUBIC)[:h, :w]
    n2 = rng.normal(0, 1, (h, w)).astype(np.float32)
    img += (n * 4 + n2 * 3)[..., None]
    # vignette de luz de focos (más luz en el centro)
    cx = (XX - 52.5) / 70; cy = (YY - 34) / 50
    img *= (1.05 - 0.18 * (cx ** 2 + cy ** 2))[..., None]
    # pista exterior
    out = (XX < -4) | (XX > 109) | (YY < -4) | (YY > 72)
    img[out] = np.array([38, 52, 40]) + n2[out][:, None] * 3
    img = np.clip(img, 0, 255).astype(np.uint8)
    L = img.copy()
    def P(x, y): return (int(round((x - GX0) * GPPM * 8)), int(round((y - GY0) * GPPM * 8)))
    col = (236, 240, 236); th = max(2, int(0.12 * GPPM))
    def line(a, b): cv2.line(L, P(*a), P(*b), col, th, cv2.LINE_AA, 3)
    def rect(x0, y0, x1, y1):
        line((x0, y0), (x1, y0)); line((x1, y0), (x1, y1)); line((x1, y1), (x0, y1)); line((x0, y1), (x0, y0))
    rect(0, 0, PL, PW); line((52.5, 0), (52.5, PW))
    def circ(c, r, a0=0, a1=360):
        cv2.ellipse(L, P(*c), (int(r * GPPM * 8), int(r * GPPM * 8)), 0, a0, a1, col, th, cv2.LINE_AA, 3)
    circ((52.5, 34), 9.15)
    for cx_, sgn in ((0, 1), (PL, -1)):
        x16 = cx_ + sgn * 16.5; x6 = cx_ + sgn * 5.5
        rect(min(cx_, x16), 34 - 20.16, max(cx_, x16), 34 + 20.16)
        rect(min(cx_, x6), 34 - 9.16, max(cx_, x6), 34 + 9.16)
        ps = (cx_ + sgn * 11, 34)
        cv2.circle(L, P(*ps), int(0.15 * GPPM * 8), col, -1, cv2.LINE_AA, 3)
        ang = math.degrees(math.acos(5.5 / 9.15))
        if sgn > 0: circ(ps, 9.15, -ang, ang)
        else: circ(ps, 9.15, 180 - ang, 180 + ang)
    cv2.circle(L, P(52.5, 34), int(0.15 * GPPM * 8), col, -1, cv2.LINE_AA, 3)
    for c, a0 in (((0, 0), 0), ((PL, 0), 90), ((PL, PW), 180), ((0, PW), 270)):
        circ(c, 1.0, a0, a0 + 90)
    return L

def crowd_texture(length, depth, ppm, seed, palette, away=None):
    """grada: filas continuas de asientos con público pequeño. Fila 0 = delante."""
    rng = random.Random(seed)
    w = int(length * ppm); h = int(depth * ppm)
    img = Image.new('RGB', (w, h), (58, 24, 28))
    d = ImageDraw.Draw(img)
    row_h = 0.80 * ppm; seat_w = 0.52 * ppm
    nrows = int(depth / 0.80)
    for r in range(nrows):
        ytop = h - (r + 1) * row_h        # dibujado natural: fila 0 abajo
        # escalón de hormigón y respaldo de asientos
        d.rectangle([0, ytop + row_h * 0.78, w, ytop + row_h], fill=(70, 70, 74))
        d.rectangle([0, ytop + row_h * 0.45, w, ytop + row_h * 0.78], fill=(150, 28, 34))
        if r % 9 == 4:   # pasillo horizontal (vomitorio) no, mantenemos continuo
            pass
        x = rng.random() * seat_w
        while x < w:
            xm = x / ppm
            if rng.random() < 0.90:
                pal = palette
                if away and away[0] <= xm <= away[1]: pal = [(200, 30, 36), (235, 235, 235), (200, 30, 36), (30, 30, 34)]
                c = pal[rng.randrange(len(pal))]
                sk = rng.choice([(232, 190, 160), (205, 150, 115), (150, 100, 70), (95, 65, 45), (240, 205, 180)])
                bw = seat_w * rng.uniform(0.62, 0.84); bh = row_h * rng.uniform(0.42, 0.55)
                bx = x + (seat_w - bw) / 2 + rng.uniform(-1, 1)
                by = ytop + row_h * 0.80 - bh
                d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=max(1, bw * 0.3), fill=c)
                hr = bw * 0.33
                hx = bx + bw / 2; hy = by - hr * 0.7
                d.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=sk)
                if rng.random() < 0.6:
                    hc = rng.choice([(30, 22, 18), (70, 50, 30), (20, 20, 20), (150, 120, 70), (200, 200, 200)])
                    d.chord([hx - hr, hy - hr * 1.05, hx + hr, hy + hr * 0.4], 180, 360, fill=hc)
                if rng.random() < 0.08:   # brazo/bufanda
                    d.rectangle([bx - 1, by + 1, bx + bw + 1, by + bh * 0.25], fill=rng.choice(palette))
            x += seat_w
    # pasillos verticales cada ~22 m
    for xm in np.arange(11, length, 22):
        xp = int(xm * ppm)
        d.rectangle([xp - int(0.6 * ppm), 0, xp + int(0.6 * ppm), h], fill=(84, 84, 88))
        for r in range(nrows):
            yy = h - (r + 1) * row_h + row_h * 0.78
            d.line([xp - int(0.6 * ppm), yy, xp + int(0.6 * ppm), yy], fill=(60, 60, 64), width=1)
    a = np.asarray(img).astype(np.float32)
    # luz: filas altas bajo cubierta más oscuras
    g = np.linspace(0.62, 1.0, h)[:, None, None]
    a *= g
    a = np.flipud(a).copy()     # fila 0 = delante (t=0 en el plano)
    return np.clip(a, 0, 255).astype(np.uint8)

def board_texture(length, ppm, seed):
    rng = random.Random(seed)
    from PIL import ImageFont
    f = ImageFont.truetype(A + 'BebasNeue-Regular.ttf', int(0.8 * ppm))
    w = int(length * ppm); h = int(0.9 * ppm)
    img = Image.new('RGB', (w, h), (14, 16, 28)); d = ImageDraw.Draw(img)
    words = [('@PREMLORE', (255, 214, 0)), ('MATCHDAY', (240, 240, 240)), ('FOOTBALL', (80, 200, 255)),
             ('LORE', (255, 214, 0)), ('HOME OF THE STORIES', (240, 240, 240)), ('KICK OFF', (120, 255, 160))]
    x = 0; seg = int(14 * ppm)
    while x < w:
        t, c = words[rng.randrange(len(words))]
        bg = rng.choice([(14, 16, 28), (20, 24, 60), (12, 12, 12)])
        d.rectangle([x, 0, x + seg, h], fill=bg)
        tw = d.textlength(t, font=f)
        d.text((x + (seg - tw) / 2, h * 0.02), t, font=f, fill=c)
        d.line([x, 0, x, h], fill=(5, 5, 5), width=2)
        x += seg
    a = np.asarray(img).astype(np.float32) * 1.25 + 10
    return np.flipud(np.clip(a, 0, 255)).astype(np.uint8)

def wall_texture(length, ppm):
    w = int(length * ppm); h = int(4 * ppm)
    a = np.zeros((h, w, 3), np.uint8); a[:] = (34, 34, 40)
    for x in range(0, w, int(9 * ppm)):
        cv2.rectangle(a, (x + int(2 * ppm), int(1.2 * ppm)), (x + int(4 * ppm), int(3.2 * ppm)), (20, 20, 24), -1)
        cv2.rectangle(a, (x + int(2.6 * ppm), int(0.6 * ppm)), (x + int(3.4 * ppm), int(0.95 * ppm)), (40, 200, 90), -1)
    return np.flipud(a).copy()

def roof_under_texture(length, depth, ppm):
    w = int(length * ppm); h = int(depth * ppm)
    a = np.zeros((h, w, 3), np.float32); a[:] = (28, 30, 36)
    for y in range(0, h, int(1.5 * ppm)):
        a[y:y + 2] = (40, 42, 50)
    # la fila de focos está en el borde delantero (t = depth)
    a[h - int(1.4 * ppm):h - int(0.2 * ppm)] = (90, 92, 100)
    for x in range(int(2 * ppm), w, int(4 * ppm)):
        cv2.rectangle(a, (x, h - int(1.3 * ppm)), (x + int(2.2 * ppm), h - int(0.3 * ppm)), (255, 252, 235), -1)
    return np.clip(a, 0, 255).astype(np.uint8)

def roof_top_texture(length, depth, ppm):
    w = int(length * ppm); h = int(depth * ppm)
    a = np.zeros((h, w, 3), np.float32); a[:] = (96, 100, 108)
    for x in range(0, w, max(2, int(0.6 * ppm))):
        a[:, x:x + 1] = (80, 84, 92)
    a[h - int(1.0 * ppm):] = (255, 250, 230)
    return np.clip(a, 0, 255).astype(np.uint8)

def screen_texture(ppm, lines):
    from PIL import ImageFont
    w = int(12 * ppm); h = int(6.5 * ppm)
    img = Image.new('RGB', (w, h), (6, 8, 16)); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w - 1, h - 1], outline=(60, 60, 70), width=max(2, int(0.25 * ppm)))
    y = h * 0.12
    for txt, size, col in lines:
        f = ImageFont.truetype(A + ('Anton-Regular.ttf' if size > 1.2 else 'BebasNeue-Regular.ttf'), int(size * ppm))
        tw = d.textlength(txt, font=f)
        d.text(((w - tw) / 2, y), txt, font=f, fill=col)
        y += size * ppm * 1.25
    a = np.asarray(img).astype(np.float32) * 1.15
    return np.flipud(np.clip(a, 0, 255)).astype(np.uint8)

# ------------------------------------------------------------------ geometría del estadio
SPPM = 20.0
class Plane:
    def __init__(s, O, a, b, length, depth, tex, ppm, name, glow=0.0, roof=None):
        s.O = np.array(O, float); s.a = norm(a); s.b = norm(b)
        s.length = length; s.depth = depth; s.tex = tex; s.ppm = ppm; s.name = name
        s.glow = glow; s.roof = roof   # roof=(tex_under, tex_top)

def build_stadium():
    rng_pal_home = [(250, 205, 20), (250, 205, 20), (25, 25, 28), (190, 30, 40), (240, 240, 240), (60, 60, 70), (250, 205, 20)]
    planes = []
    slope_d, slope_h = 20.0, 13.8
    L_side = 146.0; L_end = 110.0
    sl = math.hypot(slope_d, slope_h)
    defs = [  # name, front-origin, a, outward
        ('far',  (-20.5, PW + 7, 1.2), (1, 0, 0), (0, 1, 0), L_side, (82, 112)),
        ('near', (-20.5, -7, 1.2), (1, 0, 0), (0, -1, 0), L_side, None),
        ('left', (-7, -21, 1.2), (0, 1, 0), (-1, 0, 0), L_end, None),
        ('right', (PL + 7, -21, 1.2), (0, 1, 0), (1, 0, 0), L_end, None),
    ]
    for i, (nm, O, a, out, Ln, away) in enumerate(defs):
        out = np.array(out, float)
        b = norm(out * slope_d + np.array([0, 0, slope_h]))
        if away is not None:
            away_rng = away
        else:
            away_rng = None
        tex = crowd_texture(Ln, sl, SPPM, 10 + i, rng_pal_home, away_rng)
        planes.append(Plane(O, a, b, Ln, sl, tex, SPPM, nm))
        top = np.array(O) + b * sl
        planes.append(Plane(top, a, (0, 0, 1), Ln, 4.0, wall_texture(Ln, 10), 10, nm + '_wall'))
        rtop = top + np.array([0, 0, 4.0])
        inward = -out
        rd = 18.0
        planes.append(Plane(rtop, a, norm(inward * rd + np.array([0, 0, 0.6])), Ln, rd,
                            None, 10, nm + '_roof', roof=(roof_under_texture(Ln, rd, 10), roof_top_texture(Ln, rd, 10))))
    # vallas publicitarias LED
    for nm, O, a, Ln in (('b_far', (-4, PW + 4, 0), (1, 0, 0), 113), ('b_near', (-4, -4, 0), (1, 0, 0), 113),
                         ('b_left', (-4, -4, 0), (0, 1, 0), 76), ('b_right', (PL + 4, -4, 0), (0, 1, 0), 76)):
        planes.append(Plane(O, a, (0, 0, 1), Ln, 0.9, board_texture(Ln, 30, hash(nm) % 100), 30, nm, glow=0.35))
    return planes

def screen_plane(lines):
    f = norm((62, -44, 0)); a = np.array([-f[1], f[0], 0.0])   # perpendicular, lectura correcta
    a = norm((0.578, 0.816, 0))
    c = np.array([-11.0, 79.0, 13.5])
    O = c - a * 6
    return Plane(O, a, (0, 0, 1), 12, 6.5, screen_texture(30, lines), 30, 'screen', glow=0.6)

def plane_visible(pl, cam):
    """no dibujar gradas/vallas cuando la cámara está dentro o detrás de ellas"""
    n = pl.name
    p = cam.pos
    if n.startswith('near') or n == 'b_near':
        return p[1] > -4.5
    if n.startswith('far') or n == 'b_far':
        return p[1] < PW + 4.5
    if n.startswith('left') or n == 'b_left':
        return p[0] > -4.5
    if n.startswith('right') or n == 'b_right':
        return p[0] < PL + 4.5
    return True

def render_planes(frame, cam, planes, strip_m=4.0):
    """pinta planos texturizados en tiras, ordenadas de lejos a cerca"""
    items = []
    for pl in planes:
        if not plane_visible(pl, cam): continue
        tex = pl.tex
        if pl.roof is not None:
            # ¿vemos la cara de arriba o la de abajo?
            nrm = np.cross(pl.a, pl.b)
            side = np.dot(cam.pos - pl.O, nrm)
            up_face = nrm[2] * side > 0 if abs(nrm[2]) > 0.3 else True
            tex = pl.roof[1] if up_face else pl.roof[0]
        n = max(1, int(math.ceil(pl.length / strip_m)))
        for k in range(n):
            s0 = k * pl.length / n; s1 = (k + 1) * pl.length / n
            c = pl.O + pl.a * (s0 + s1) / 2 + pl.b * pl.depth / 2
            items.append((cam.depth(c), pl, tex, s0, s1))
    items.sort(key=lambda t: -t[0])
    for dep, pl, tex, s0, s1 in items:
        corners = [pl.O + pl.a * s0, pl.O + pl.a * s1, pl.O + pl.a * s1 + pl.b * pl.depth, pl.O + pl.a * s0 + pl.b * pl.depth]
        us, vs, zs = [], [], []
        ok = True
        for c in corners:
            u, v, z = cam.proj(c)
            if z < 0.8: ok = False; break
            us.append(u); vs.append(v)
        if not ok: continue
        x0 = int(max(0, math.floor(min(us)))); x1 = int(min(W, math.ceil(max(us)) + 1))
        y0 = int(max(0, math.floor(min(vs)))); y1 = int(min(H, math.ceil(max(vs)) + 1))
        if x1 <= x0 or y1 <= y0: continue
        if (x1 - x0) * (y1 - y0) > W * H * 2: continue
        ppm_t = tex.shape[1] / pl.length
        th, tw = tex.shape[:2]
        tx0 = int(s0 * ppm_t); tx1 = min(tw, int(math.ceil(s1 * ppm_t)) + 1)
        sub = tex[:, tx0:tx1]
        Hm = cam.plane_H(pl.O + pl.a * (tx0 / ppm_t), pl.a, pl.b, ppm_t * 1.0)
        # escala del eje b: la textura cubre depth en th px
        Hm = Hm @ np.diag([1.0, (pl.depth * ppm_t) / th, 1.0]) if th != int(pl.depth * ppm_t) else Hm
        T = np.array([[1, 0, -x0], [0, 1, -y0], [0, 0, 1]], float)
        Hp = T @ Hm
        ow, oh = x1 - x0, y1 - y0
        patch = cv2.warpPerspective(sub, Hp, (ow, oh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        mask = cv2.warpPerspective(np.full(sub.shape[:2], 255, np.uint8), Hp, (ow, oh), flags=cv2.INTER_LINEAR)
        m = (mask.astype(np.float32) / 255.0)[..., None]
        region = frame[y0:y1, x0:x1]
        p = patch.astype(np.float32)
        if pl.glow:
            p = p * (1 + pl.glow)
        region[:] = region * (1 - m) + np.clip(p, 0, 255) * m
    return frame

def render_ground(frame, cam, gtex):
    T = np.array([[1 / GPPM, 0, GX0], [0, 1 / GPPM, GY0], [0, 0, 1]], float)
    Hm = cam.plane_H((0, 0, 0), (1, 0, 0), (0, 1, 0), 1.0) @ T
    hv = cam.horizon_v()
    if hv >= H: return frame
    y0 = int(max(0, hv + 2))
    Tt = np.array([[1, 0, 0], [0, 1, -y0], [0, 0, 1]], float)
    patch = cv2.warpPerspective(gtex, Tt @ Hm, (W, H - y0), flags=cv2.INTER_LINEAR,
                                borderMode=cv2.BORDER_CONSTANT, borderValue=(16, 18, 26))
    frame[y0:] = patch
    return frame

def render_sky(cam, night):
    """cielo: atardecer (night=0) → noche cerrada (night=1); resplandor de focos"""
    v = np.arange(H, dtype=np.float32)[:, None]
    # ángulo de elevación por fila (aprox, sin roll)
    el = cam.fwd[2] - (v - H / 2) / cam.f * cam.up[2]
    el = np.clip(el, -0.2, 1.0)
    top_d = np.array([40, 60, 120]); hor_d = np.array([210, 120, 80])
    top_n = np.array([6, 10, 26]); hor_n = np.array([40, 46, 80])
    top = top_d * (1 - night) + top_n * night
    hor = hor_d * (1 - night) + hor_n * night
    k = np.clip(el / 0.5, 0, 1)
    col = hor[None] * (1 - k) + top[None] * k
    sky = np.repeat(col[:, None, :], W, 1).astype(np.float32)
    return sky

# ------------------------------------------------------------------ porterías
def draw_goal(draw, cam, gx, sgn, scale_img=1):
    """sgn = dirección hacia fuera del campo (-1 portería izquierda, +1 derecha)"""
    y0, y1, hgt, dpt = 34 - 3.66, 34 + 3.66, 2.44, 2.0
    def P(x, y, z):
        u, v, zc = cam.proj((x, y, z)); return u, v, zc
    def seg(a, b, wm, col):
        ua, va, za = P(*a); ub, vb, zb = P(*b)
        if za < 0.5 or zb < 0.5: return
        wpx = max(1, cam.f * wm / ((za + zb) / 2))
        draw.line([(ua, va), (ub, vb)], fill=col, width=int(round(wpx)))
    netc = (225, 228, 232, 120)
    xb = gx + sgn * dpt; xt = gx + sgn * 1.0
    # red: laterales, techo, fondo
    for i in range(0, 13):
        z = hgt * i / 12
        seg((gx, y0, z), (xb if z < 0.01 else xt + (xb - xt) * (1 - z / hgt), y0, z), 0.02, netc)
        seg((gx, y1, z), (xb if z < 0.01 else xt + (xb - xt) * (1 - z / hgt), y1, z), 0.02, netc)
    for j in range(0, 25):
        y = y0 + (y1 - y0) * j / 24
        seg((gx, y, hgt), (xt, y, hgt), 0.02, netc)
        seg((xt, y, hgt), (xb, y, 0), 0.02, netc)
    for i in range(0, 9):
        f = i / 8
        seg((xt + (xb - xt) * f, y0, hgt * (1 - f)), (xt + (xb - xt) * f, y1, hgt * (1 - f)), 0.02, netc)
        seg((gx + (xt - gx) * f, y0, hgt), (gx + (xt - gx) * f, y1, hgt), 0.02, netc)
    white = (250, 250, 250, 255)
    seg((gx, y0, 0), (gx, y0, hgt), 0.12, white)
    seg((gx, y1, 0), (gx, y1, hgt), 0.12, white)
    seg((gx, y0 - 0.06, hgt), (gx, y1 + 0.06, hgt), 0.12, white)

# ------------------------------------------------------------------ jugadores
KITS = {
    'WAT': dict(shirt=(252, 210, 16), shirt2=(252, 210, 16), trim=(20, 20, 20), shorts=(22, 22, 24), socks=(252, 210, 16), stripes=False),
    'SOU': dict(shirt=(240, 240, 240), shirt2=(205, 24, 38), trim=(20, 20, 20), shorts=(22, 22, 24), socks=(240, 240, 240), stripes=True),
    'WGK': dict(shirt=(30, 160, 90), shirt2=(30, 160, 90), trim=(10, 60, 30), shorts=(30, 160, 90), socks=(30, 160, 90), stripes=False, gloves=True),
    'SGK': dict(shirt=(40, 70, 170), shirt2=(40, 70, 170), trim=(10, 20, 60), shorts=(40, 70, 170), socks=(40, 70, 170), stripes=False, gloves=True),
}

def _ang(x): return x

def player_pose(pose, ph, t=0.0):
    """devuelve ángulos (rad, 0 = hacia abajo, + = hacia delante):
    thigh_f, shin_f(rel), thigh_b, shin_b, arm_f, fore_f, arm_b, fore_b, lean, lift"""
    s, c = math.sin(ph), math.cos(ph)
    if pose == 'run':
        tf = 0.62 * s; tb = -0.62 * s
        kf = -(0.25 + 1.05 * max(0, -math.sin(ph + 1.2)))
        kb = -(0.25 + 1.05 * max(0, -math.sin(ph + 1.2 + math.pi)))
        af = -0.75 * s; ab = 0.75 * s
        return dict(tf=tf, kf=kf, tb=tb, kb=kb, af=af, ff=1.45, ab=ab, fb=1.45, lean=0.16, lift=0.025 * abs(c))
    if pose == 'jog':
        tf = 0.35 * s; tb = -0.35 * s
        kf = -(0.15 + 0.6 * max(0, -math.sin(ph + 1.2)))
        kb = -(0.15 + 0.6 * max(0, -math.sin(ph + 1.2 + math.pi)))
        return dict(tf=tf, kf=kf, tb=tb, kb=kb, af=-0.4 * s, ff=1.3, ab=0.4 * s, fb=1.3, lean=0.08, lift=0.01 * abs(c))
    if pose == 'stand':
        return dict(tf=0.05, kf=-0.05, tb=-0.05, kb=-0.05, af=0.1, ff=0.3, ab=-0.08, fb=0.3, lean=0.02 + 0.01 * s, lift=0)
    if pose == 'ready':
        return dict(tf=0.35, kf=-0.65, tb=-0.1, kb=-0.55, af=0.35, ff=0.6, ab=0.0, fb=0.7, lean=0.30, lift=-0.03)
    if pose == 'kick':     # t: 0..1  (atrás → golpeo → seguimiento)
        if t < 0.5: sw = -0.9 * (t / 0.5); kn = -1.6 * (t / 0.5)
        else: q = (t - 0.5) / 0.5; sw = -0.9 + 2.3 * q; kn = -1.6 + 1.6 * min(1, q * 1.5)
        return dict(tf=sw, kf=kn, tb=-0.12, kb=-0.15, af=-0.9, ff=0.6, ab=0.9, fb=0.5, lean=-0.05, lift=0)
    if pose == 'block':    # se lanza con la pierna por delante
        return dict(tf=1.2, kf=-0.1, tb=-0.5, kb=-0.6, af=1.0, ff=0.4, ab=-0.9, fb=0.4, lean=-0.15, lift=-0.06)
    if pose == 'chip':
        if t < 0.45: sw = -0.6 * (t / 0.45); kn = -1.3 * (t / 0.45)
        else: q = (t - 0.45) / 0.55; sw = -0.6 + 1.7 * q; kn = -1.3 + 1.1 * q
        return dict(tf=sw, kf=kn, tb=-0.1, kb=-0.15, af=-0.7, ff=0.5, ab=0.8, fb=0.6, lean=-0.12, lift=0)
    if pose == 'reach':    # portero se estira hacia arriba
        return dict(tf=0.25, kf=-0.3, tb=-0.25, kb=-0.4, af=2.9, ff=0.1, ab=2.7, fb=0.1, lean=-0.1, lift=0.05 * t)
    if pose == 'gk':
        return dict(tf=0.3, kf=-0.6, tb=-0.3, kb=-0.6, af=0.9, ff=0.5, ab=0.6, fb=0.5, lean=0.25, lift=-0.04)
    if pose == 'celebrate':
        tf = 0.5 * s; tb = -0.5 * s
        kf = -(0.2 + 0.9 * max(0, -math.sin(ph + 1.2)))
        kb = -(0.2 + 0.9 * max(0, -math.sin(ph + 1.2 + math.pi)))
        return dict(tf=tf, kf=kf, tb=tb, kb=kb, af=2.8, ff=0.2, ab=-0.5 * s, fb=1.2, lean=0.05, lift=0.02 * abs(c))
    return player_pose('stand', ph)

def draw_player_sprite(hpx, kit, pose, ph, facing, t=0.0, skin=(214, 168, 130), hair=(40, 28, 20), seed=0):
    """sprite RGBA de un futbolista visto de lado (mirando a la derecha si facing>0).
    Devuelve (img, ancla_x, ancla_y) con ancla en el punto entre los pies."""
    S = 3 if hpx < 140 else 2
    h = hpx * S
    Wd = int(h * 1.2) + 8; Hd = int(h * 1.25) + 8
    img = Image.new('RGBA', (Wd, Hd), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    a = player_pose(pose, ph, t)
    fx, fy = Wd / 2, Hd - 4 - h * 0.02
    lift = a['lift'] * h
    hip = (fx, fy - h * 0.50 - lift)
    lean = a['lean']
    sh = (hip[0] + math.sin(lean) * h * 0.32, hip[1] - math.cos(lean) * h * 0.32)
    def limb(p, ang, L):
        return (p[0] + math.sin(ang) * L, p[1] + math.cos(ang) * L)
    def cap(p, r, col): d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=col)
    def seg(p, q, wdt, col):
        d.line([p, q], fill=col, width=max(1, int(wdt))); cap(p, wdt / 2, col); cap(q, wdt / 2, col)
    darker = lambda c, k=0.72: tuple(int(v * k) for v in c[:3])
    thL = h * 0.245; shL = h * 0.235
    uaL = h * 0.165; faL = h * 0.15
    legw = h * 0.072; armw = h * 0.052
    def leg(tang, kang, back):
        k = 0.78 if back else 1.0
        knee = limb(hip, tang, thL)
        ankle = limb(knee, tang + kang, shL)
        skn = darker(skin, k)
        # muslo (piel), pantalón cubre el 45 % superior
        seg(hip, knee, legw, skn)
        mid = (hip[0] + (knee[0] - hip[0]) * 0.5, hip[1] + (knee[1] - hip[1]) * 0.5)
        seg(hip, mid, legw * 1.35, darker(kit['shorts'], k))
        # espinilla: media con espinillera cubre del 15 % hacia abajo
        sock_top = (knee[0] + (ankle[0] - knee[0]) * 0.18, knee[1] + (ankle[1] - knee[1]) * 0.18)
        seg(knee, sock_top, legw * 0.92, skn)
        seg(sock_top, ankle, legw * 0.95, darker(kit['socks'], k))
        # bota
        fa = tang + kang - math.pi / 2 + 0.1
        toe = (ankle[0] + math.sin(fa + math.pi) * -h * 0.075, ankle[1] + math.cos(fa + math.pi) * -h * 0.075)
        toe = (ankle[0] + math.cos(tang + kang) * h * 0.07, ankle[1] - math.sin(tang + kang) * h * 0.07 + h * 0.012)
        seg(ankle, toe, legw * 0.8, darker((18, 18, 20), k))
        d.line([ankle, toe], fill=(230, 230, 230, 255) if not back else (170, 170, 170, 255), width=max(1, int(h * 0.008)))
    def arm(aang, fang, back):
        k = 0.78 if back else 1.0
        shp = (sh[0], sh[1] + h * 0.02)
        elbow = limb(shp, aang, uaL)
        hand = limb(elbow, aang + fang, faL)
        sleeve = (shp[0] + (elbow[0] - shp[0]) * 0.55, shp[1] + (elbow[1] - shp[1]) * 0.55)
        skn = darker(skin, k)
        seg(sleeve, elbow, armw, skn)
        glove = kit.get('gloves')
        seg(elbow, hand, armw * 0.95, skn)
        if glove: cap(hand, armw * 0.85, darker((240, 240, 240), k))
        seg(shp, sleeve, armw * 1.35, darker(kit['shirt2'] if kit['stripes'] else kit['shirt'], k))
    leg(a['tb'], a['kb'], True)
    arm(a['ab'], a['fb'], True)
    # torso (camiseta)
    tw_ = h * 0.115
    nx, ny = math.cos(lean), math.sin(lean)
    p1 = (sh[0] - nx * tw_, sh[1] - ny * tw_); p2 = (sh[0] + nx * tw_ * 1.05, sh[1] + ny * tw_)
    p3 = (hip[0] + nx * tw_ * 0.95, hip[1] + ny * tw_ * 0.9 + h * 0.02); p4 = (hip[0] - nx * tw_ * 0.9, hip[1] - ny * tw_ * 0.9 + h * 0.02)
    d.polygon([p1, p2, p3, p4], fill=kit['shirt'])
    if kit['stripes']:
        n = 5
        for i in range(n):
            if i % 2 == 0: continue
            f0, f1 = i / n, (i + 1) / n
            q1 = (p1[0] + (p2[0] - p1[0]) * f0, p1[1] + (p2[1] - p1[1]) * f0)
            q2 = (p1[0] + (p2[0] - p1[0]) * f1, p1[1] + (p2[1] - p1[1]) * f1)
            q3 = (p4[0] + (p3[0] - p4[0]) * f1, p4[1] + (p3[1] - p4[1]) * f1)
            q4 = (p4[0] + (p3[0] - p4[0]) * f0, p4[1] + (p3[1] - p4[1]) * f0)
            d.polygon([q1, q2, q3, q4], fill=kit['shirt2'])
    # cuello y ribete
    d.line([p1, p2], fill=kit['trim'], width=max(1, int(h * 0.012)))
    # cuello/cabeza
    neck = (sh[0] + math.sin(lean) * h * 0.035, sh[1] - h * 0.035)
    seg(sh, neck, h * 0.05, darker(skin, 0.9))
    hc = (neck[0] + math.sin(lean) * h * 0.06 + h * 0.01, neck[1] - h * 0.065)
    hr = h * 0.066
    d.ellipse([hc[0] - hr * 0.95, hc[1] - hr * 1.05, hc[0] + hr * 0.95, hc[1] + hr * 1.05], fill=skin)
    d.chord([hc[0] - hr * 1.0, hc[1] - hr * 1.12, hc[0] + hr * 0.95, hc[1] + hr * 0.5], 160, 360, fill=hair)
    d.ellipse([hc[0] + hr * 0.55, hc[1] - hr * 0.05, hc[0] + hr * 1.02, hc[1] + hr * 0.4], fill=darker(skin, 0.92))  # nariz/perfil
    d.ellipse([hc[0] - hr * 0.45, hc[1] - hr * 0.15, hc[0] - hr * 0.1, hc[1] + hr * 0.3], fill=darker(skin, 0.85))   # oreja
    # pantalón (cadera)
    d.ellipse([hip[0] - tw_ * 0.95, hip[1] - h * 0.035, hip[0] + tw_ * 0.95, hip[1] + h * 0.05], fill=kit['shorts'])
    leg(a['tf'], a['kf'], False)
    arm(a['af'], a['ff'], False)
    if facing < 0: img = img.transpose(Image.FLIP_LEFT_RIGHT)
    img = img.resize((max(1, Wd // S), max(1, Hd // S)), Image.LANCZOS)
    ax = (Wd / 2) / S; ay = (Hd - 4) / S
    return img, ax, ay
