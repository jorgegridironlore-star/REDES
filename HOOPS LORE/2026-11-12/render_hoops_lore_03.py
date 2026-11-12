"""Hoops Lore #03 - El 19-18: Fort Wayne Pistons 19, Minneapolis Lakers 18 (22 nov 1950, Minneapolis Auditorium).
Render: python3 render_hoops_lore_03.py [--test t1,t2] [--cover t]"""
import json, math, os, sys, subprocess, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import engine as E
import people as PP
from engine import Cam, ease, clamp, lerp, font

E.LANE_HALF = 3.0          # zona de 6 pies (hasta 1951)
HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 30; W1, H1 = 1080, 1920; W2, H2 = 2160, 3840
AUDIO = os.path.join(HERE, 'hoops_lore_03_voz.mp3')
LOGO = os.path.join(HERE, 'hoops_lore_logo.png')
HANDLE = '@hoopslore0'
PH = json.load(open(os.path.join(HERE, 'times_03.json')))
DUR = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', AUDIO]))
NFR = int(DUR * FPS)
def ps(i): return PH[i]['start']
def pe(i): return PH[i]['end']
def wt(i, word, nth=0):
    c = 0
    for w in PH[i]['words']:
        if word.lower() in w['w'].lower():
            if c == nth: return w['s']
            c += 1
    return ps(i)
YEL = (255, 221, 0)
RIM_X = E.COURT_L / 2 - 4 - .75     # 41.25

# ------------------------------------------------------------------ camaras y fondos
CAMS = {
    'side': Cam((0, -78, 30), (0, 6, 3), 1730 * 2, 3600 * 2, H2),
    'tight': Cam((0, -52, 11), (0, -10, 4.6), 2150 * 2, 5600 * 2, H2),
    'end': Cam((-76, 0, 30), (-18, 0, 0), 1450 * 2, 1300 * 2, H2, oy=-260),
    'crowd': Cam((-10, -40, 9), (25, 60, 34), 1500 * 2, 1500 * 2, H2),
    'vault': Cam((-70, -25, 14), (10, 15, 62), 1150 * 2, 1300 * 2, H2),
    'ft': Cam((-24, -30, 7.5), (-31, 0, 5.5), 1500 * 2, 1500 * 2, H2),
    'table': Cam((2.5, -23.5, 4.4), (0, -31, 3.3), 1600 * 2, 1500 * 2, H2),
    'rim': Cam((24, -24, 8.5), (39, -1, 7.5), 1500 * 2, 1500 * 2, H2),
}
BG = {}
def get_bg(key):
    if key not in BG:
        md = {'tight': 10, 'crowd': 10, 'vault': 10, 'rim': 10, 'ft': 10, 'table': 8}.get(key, 45)
        BG[key] = E.render_background(CAMS[key], venue='minneapolis', occupancy=.8, min_depth=md)
    return BG[key]

# ------------------------------------------------------------------ actores
class Actor:
    def __init__(self, team=None, number=None, height=6.4, keys=None, skin='light', hair=(50, 38, 28), build=1.0,
                 ref=False, fan=None, seed=0):
        self.team, self.number, self.height = team, number, height
        self.keys = keys or [(0, (0, 0))]
        self.skin, self.hair, self.build, self.ref, self.fan = skin, hair, build, ref, fan
    def pos(self, t):
        ks = self.keys
        if t <= ks[0][0]: return ks[0][1]
        for (t0, p0), (t1, p1) in zip(ks, ks[1:]):
            if t <= t1:
                u = (t - t0) / max(t1 - t0, 1e-6)
                u = ease(u) if len(ks) == 2 else u
                return (lerp(p0[0], p1[0], u), lerp(p0[1], p1[1], u))
        return ks[-1][1]
    def vel(self, t):
        a = self.pos(t - .05); b = self.pos(t + .05)
        return ((b[0] - a[0]) / .1, (b[1] - a[1]) / .1)
    def dist(self, t):
        n = max(2, int(t * 12)); d = 0; prev = self.pos(0)
        for i in range(1, n + 1):
            p = self.pos(t * i / n); d += math.hypot(p[0] - prev[0], p[1] - prev[1]); prev = p
        return d

def draw_actors(dr, cam, lst, t, k, off, dim=1.0):
    """lst: (actor, pose|None, face|None)"""
    items = []
    for a, pose, face in lst:
        x, y = a.pos(t); items.append((cam.depth((x, y, 3)), a, pose, face))
    items.sort(key=lambda q: -q[0])
    out = {}
    for _, a, pose, face in items:
        x, y = a.pos(t)
        v = a.vel(t); spd = math.hypot(*v)
        f0 = face if face is not None else (math.atan2(v[1], v[0]) if spd > .6 else -math.pi / 2)
        if pose is None:
            pose = E.pose_run(a.dist(t) / 2.4 * math.pi, clamp(spd / 18, .35, 1.0)) if spd > .6 else E.pose_stand()
        if a.fan:
            out[id(a)] = PP.draw_fan62(dr, cam, x, y, f0, pose, coat=a.fan[0], trousers=a.fan[1], hat=a.fan[2], skin=a.skin,
                                       hair=a.hair, k=k, off=off, dim=dim, height=a.height)
        else:
            out[id(a)] = PP.draw_player62(dr, cam, x, y, f0, pose, a.team, a.number, a.height, a.skin, a.hair, k, off, dim,
                                          a.build, a.ref)
    return out

def P2F(cam, P, x0, y0, kk):
    u, v, d = cam.p(P); return ((u - x0) * kk / 2, (v - y0) * kk / 2)

def hand_pos(J, side='r'):
    w = J[side + 'wr']; e = J[side + 'el']
    return tuple(w[i] + (w[i] - e[i]) * .25 for i in range(3))

# reparto (dorsales genericos salvo Mikan, que llevaba el 99; sin caras reales)
MIKAN = dict(team='MIN', number=99, height=6.83, skin='light', hair=(36, 28, 22), build=1.05)
FOUST = dict(height=6.75, skin='light', hair=(70, 52, 34), build=1.0)
def mikan(keys): return Actor(keys=keys, **MIKAN)
FW_R = [dict(team='FW', number=n, height=h, skin=s, hair=hr) for n, h, s, hr in
        [(14, 6.6, 'light', (60, 44, 30)), (10, 6.2, 'light2', (40, 30, 22)), (7, 6.1, 'light', (110, 80, 50)), (12, 6.4, 'tan', (30, 22, 18)), (5, 6.3, 'light', (80, 60, 40))]]
MIN_R = [dict(team='MIN', number=n, height=h, skin=s, hair=hr) for n, h, s, hr in
         [(99, 6.83, 'light', (36, 28, 22)), (17, 6.6, 'light', (90, 66, 40)), (11, 6.3, 'light2', (50, 36, 26)), (19, 6.5, 'light', (70, 50, 30)), (22, 6.1, 'tan', (40, 30, 22))]]
def piston(i, keys, **kw):
    d = dict(FW_R[i]); d.update(kw)
    if d.get('number', 1) is None: d['number'] = 16
    return Actor(keys=keys, **d)
def laker(i, keys): return Actor(keys=keys, **MIN_R[i])

# ------------------------------------------------------------------ poses especiales
def pose_underhand(t):
    """tiro libre por debajo (asi los tiraba Wilt esa temporada): flexiona y balancea los brazos hacia arriba"""
    if t < .35:   # se agacha con el balon entre las rodillas
        k = ease(t / .35); arm = .1; knee = .7 * k; lean = .25 * k
    else:
        k = ease((t - .35) / .4); arm = .1 + 1.7 * k; knee = .7 * (1 - k); lean = .25 * (1 - k)
    return dict(lh=.25 * (knee / .7) + .02, lk=knee + .05, rh=.25 * (knee / .7), rk=knee + .05,
                ls=arm, le=.1, la=.12, rs=arm, re=.1, ra=.12, lift=-.35 * (knee / .7) + .15 * max(0, k - .7) if t >= .35 else -.35 * (knee / .7), lean=lean)

def pose_dunk(t):
    """salto con el brazo derecho estirado por encima del aro"""
    up = math.sin(math.pi * clamp(t)) * 3.2
    crouch = max(0, 1 - t * 5) * .6
    return dict(lh=.5 * (1 - t) + .1, lk=.9 * crouch + .4, rh=.15, rk=.5 + crouch, ls=.6, le=.6, la=.3,
                rs=3.0, re=.05, ra=.05, lift=up - crouch * .5, lean=.1)

def pose_cheer(ph):
    a = 2.6 + .3 * math.sin(ph)
    return dict(lh=.05, lk=.08, rh=-.03, rk=.06, ls=a, le=.25, la=.35, rs=a - .2 * math.sin(ph * 1.3), re=.3, ra=.35, lift=.15 * abs(math.sin(ph)), lean=.02)

# ------------------------------------------------------------------ graficos (1x)
def text_stroke(d, xy, s, f, fill, sw=6, sf=(0, 0, 0), anchor='mm'):
    d.text(xy, s, font=f, fill=fill, anchor=anchor, stroke_width=sw, stroke_fill=sf)

def tv_label(img, xy, text, t, size=66):
    """rotulo amarillo tipo TV (sin circulos de rotulador)"""
    a = ease(t / .3)
    if a <= 0: return
    d = ImageDraw.Draw(img, 'RGBA'); f = font('BebasNeue-Regular.ttf', size)
    l, tp, r, bt = d.textbbox(xy, text, font=f, anchor='mm')
    d.rounded_rectangle([l - 22, tp - 14, r + 22, bt + 14], radius=10, fill=(250, 214, 0, int(245 * a)))
    d.text(xy, text, font=f, fill=(15, 15, 15, int(255 * a)), anchor='mm')

def lower_third(img, t_in, t, title, sub=None, y=1490, t_out=None):
    if t < t_in or (t_out and t > t_out + .3): return
    a = ease((t - t_in) / .35)
    if t_out and t > t_out: a = 1 - ease((t - t_out) / .3)
    d = ImageDraw.Draw(img, 'RGBA')
    f1 = font('BebasNeue-Regular.ttf', 66); f2 = font('BebasNeue-Regular.ttf', 44)
    w = max(d.textlength(title, font=f1), d.textlength(sub or '', font=f2)) + 80
    x0 = 70 - (1 - a) * (w + 100)
    h = 96 if not sub else 150
    d.rectangle([x0, y, x0 + w, y + h], fill=(14, 22, 48, 235))
    d.rectangle([x0, y, x0 + 12, y + h], fill=(236, 120, 30, 255))
    d.text((x0 + 40, y + 50), title, font=f1, fill=(255, 255, 255), anchor='lm')
    if sub: d.text((x0 + 40, y + 113), sub, font=f2, fill=(255, 214, 120), anchor='lm')

def score_bug(img, phi, ny, label='1ST QTR', clock='', y=170):
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    f = font('BebasNeue-Regular.ttf', 58); fs = font('Anton-Regular.ttf', 50)
    x = 60
    d.rounded_rectangle([x, y, x + 740, y + 84], radius=10, fill=(12, 14, 22, 235))
    d.rectangle([x + 10, y + 10, x + 22, y + 74], fill=(196, 34, 40)); d.text((x + 36, y + 44), 'FW', font=f, fill='white', anchor='lm')
    d.text((x + 175, y + 44), str(phi), font=fs, fill='white', anchor='mm')
    d.rectangle([x + 232, y + 10, x + 244, y + 74], fill=(232, 184, 52)); d.text((x + 258, y + 44), 'MIN', font=f, fill='white', anchor='lm')
    d.text((x + 370, y + 44), str(ny), font=fs, fill='white', anchor='mm')
    d.rectangle([x + 420, y + 8, x + 422, y + 76], fill=(80, 80, 90))
    d.text((x + 438, y + 44), label, font=f, fill=(255, 214, 120), anchor='lm')
    if clock: d.text((x + 725, y + 44), clock, font=f, fill='white', anchor='rm')
    img.paste(layer, (0, 0), layer)

def wilt_tile(img, pts, y=270, pulse=0.0):
    """contador de puntos de Wilt bajo el marcador"""
    d = ImageDraw.Draw(img, 'RGBA')
    x = 60; s = 1 + .12 * pulse
    d.rounded_rectangle([x, y, x + 330 * s, y + 96 * s], radius=10, fill=(24, 64, 160, 240))
    d.text((x + 20, y + 48 * s), 'WILT #13', font=font('BebasNeue-Regular.ttf', int(50 * s)), fill='white', anchor='lm')
    d.text((x + 312 * s, y + 48 * s), str(pts), font=font('Anton-Regular.ttf', int(64 * s)), fill=YEL, anchor='rm')

def big_card(img, t, t0, lines, y=560):
    a = ease((t - t0) / .35)
    if a <= 0: return
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    w = 900; h = sum(l[2] + 26 for l in lines) + 60
    x0 = (W1 - w) / 2
    d.rounded_rectangle([x0, y, x0 + w, y + h], radius=22, fill=(12, 14, 22, 236), outline=(255, 214, 120, 255), width=5)
    yy = y + 40
    for text, fname, size, col in [(l[0], l[1], l[2], l[3]) for l in lines]:
        d.text((W1 / 2, yy + size / 2), text, font=font(fname, size), fill=col, anchor='mm'); yy += size + 26
    layer.putalpha(layer.getchannel('A').point(lambda v: int(v * a)))
    img.paste(layer, (0, 0), layer)

def tv_static(img, t, box=None, strength=1.0):
    rng = np.random.default_rng(int(t * 997))
    if box is None: box = (0, 0, W1, H1)
    w, h = box[2] - box[0], box[3] - box[1]
    n = rng.integers(0, 255, (h // 3 + 1, w // 3 + 1), dtype=np.uint8).repeat(3, 0).repeat(3, 1)[:h, :w]
    lines = (np.sin(np.arange(h) / 3 + t * 40) * 18).astype(np.int16)[:, None]
    n = np.clip(n.astype(np.int16) + lines, 0, 255).astype(np.uint8)
    st = Image.fromarray(n).convert('RGB')
    if strength >= 1: img.paste(st, box[:2])
    else:
        reg = img.crop(box); img.paste(Image.blend(reg, st, strength), box[:2])

# ------------------------------------------------------------------ props
def draw_table(dr, cam, k, off, dim=1.0, clock=None, t=0.0):
    """mesa de anotadores en la banda cercana; clock: 'game' (reloj de partido), 'stopwatch' o 'shot' (reloj de 24 s de esfera)"""
    def P(X):
        u, v, d = cam.p(X); return ((u - off[0]) * k, (v - off[1]) * k)
    def D(c): return tuple(int(v * dim) for v in c)
    x0, x1, y0, y1, h = -9, 9, -32.5, -30, 2.6
    dr.polygon([P((x0, y0, h)), P((x1, y0, h)), P((x1, y1, h)), P((x0, y1, h))], fill=D((96, 66, 42)))
    dr.polygon([P((x0, y1, 0)), P((x1, y1, 0)), P((x1, y1, h)), P((x0, y1, h))], fill=D((70, 46, 30)))
    dr.polygon([P((x0, y1 + .05, .3)), P((x1, y1 + .05, .3)), P((x1, y1 + .05, h - .15)), P((x0, y1 + .05, h - .15))], fill=D((32, 54, 120)))
    for xx in range(-8, 9, 2):
        dr.line([P((xx, y1 + .06, .3)), P((xx, y1 + .06, h - .15))], fill=D((24, 42, 92)), width=2)
    sc = cam.f * k / max(cam.depth((0, -31.2, h)), 1)
    # libro de actas y lapiz
    bx, by = P((4.8, -31.3, h))
    dr.polygon([(bx - 1.1 * sc, by - .1 * sc), (bx + 1.1 * sc, by - .1 * sc), (bx + 1.2 * sc, by + .25 * sc), (bx - 1.2 * sc, by + .25 * sc)], fill=D((236, 232, 220)))
    for i in range(4): dr.line([(bx - .9 * sc, by + i * .07 * sc), (bx + .9 * sc, by + i * .07 * sc)], fill=D((150, 150, 170)), width=1)
    if clock == 'game':
        cx, cy = P((0.0, -31.2, h + .8)); r = .7 * sc
        dr.rectangle([cx - r * 1.2, cy - r * 1.2, cx + r * 1.2, cy + r * 1.15 + .2 * sc], fill=D((58, 44, 34)))
        dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=D((240, 236, 222)), outline=D((20, 20, 20)), width=max(1, int(.05 * sc)))
        for i in range(12):
            a = i / 12 * 2 * math.pi
            dr.line([(cx + .8 * r * math.sin(a), cy - .8 * r * math.cos(a)), (cx + .92 * r * math.sin(a), cy - .92 * r * math.cos(a))], fill=D((20, 20, 20)), width=max(1, int(.03 * sc)))
        a = 2 * math.pi * (.62 + t / 60)
        dr.line([(cx, cy), (cx + .75 * r * math.sin(a), cy - .75 * r * math.cos(a))], fill=D((20, 20, 20)), width=max(1, int(.05 * sc)))
    elif clock == 'stopwatch':
        cx, cy = P((0.0, -31.0, h + .32)); r = .34 * sc
        dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=D((176, 176, 180)), outline=D((60, 60, 64)), width=max(1, int(.04 * sc)))
        dr.rectangle([cx - .07 * sc, cy - r - .14 * sc, cx + .07 * sc, cy - r], fill=D((150, 150, 156)))
        rr = r * .82
        dr.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=D((246, 244, 236)))
        for i in range(12):
            a = i / 12 * 2 * math.pi
            dr.line([(cx + .8 * rr * math.sin(a), cy - .8 * rr * math.cos(a)), (cx + .95 * rr * math.sin(a), cy - .95 * rr * math.cos(a))], fill=D((30, 30, 30)), width=1)
        a = 2 * math.pi * (t / 6)
        dr.line([(cx, cy), (cx + .85 * rr * math.sin(a), cy - .85 * rr * math.cos(a))], fill=D((200, 30, 30)), width=max(1, int(.03 * sc)))
    elif clock == 'shot':
        # reloj de 24 segundos de la epoca: caja de madera con esfera, encima de la mesa
        cx, cy = P((0.0, -31.2, h + 1.0)); r = .8 * sc
        dr.rectangle([cx - r * 1.25, cy - r * 1.35, cx + r * 1.25, cy + r * 1.3], fill=D((64, 46, 32)), outline=D((30, 22, 16)), width=max(1, int(.05 * sc)))
        dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=D((244, 240, 228)), outline=D((20, 20, 20)), width=max(1, int(.05 * sc)))
        f = font('BebasNeue-Regular.ttf', max(8, int(.28 * sc)))
        for n in range(0, 24, 4):
            a = n / 24 * 2 * math.pi
            dr.text((cx + .74 * r * math.sin(a), cy - .74 * r * math.cos(a)), str(24 if n == 0 else n), font=f, fill=D((20, 20, 20)), anchor='mm')
        a = 2 * math.pi * (-min(t, 23.9) / 24)
        dr.line([(cx, cy), (cx + .62 * r * math.sin(a), cy - .62 * r * math.cos(a))], fill=D((200, 30, 30)), width=max(2, int(.06 * sc)))
        dr.ellipse([cx - .07 * sc, cy - .07 * sc, cx + .07 * sc, cy + .07 * sc], fill=D((20, 20, 20)))
    return P

def draw_tv(img, cx, cy, w, t, mode='static'):
    """televisor de los 60 (sin marca)"""
    d = ImageDraw.Draw(img)
    h = w * .78
    d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], radius=int(w * .06), fill=(86, 62, 42), outline=(30, 22, 16), width=6)
    sx0, sy0, sx1, sy1 = int(cx - w * .4), int(cy - h * .38), int(cx + w * .26), int(cy + h * .38)
    d.rounded_rectangle([sx0 - 8, sy0 - 8, sx1 + 8, sy1 + 8], radius=30, fill=(20, 20, 20))
    if mode == 'static': tv_static(img, t, (sx0, sy0, sx1, sy1))
    else: d.rounded_rectangle([sx0, sy0, sx1, sy1], radius=26, fill=(14, 16, 18))
    for i, yy in enumerate((cy - h * .25, cy - h * .05)):
        d.ellipse([cx + w * .31, yy - w * .05, cx + w * .41, yy + w * .05], fill=(200, 190, 170), outline=(40, 30, 20), width=3)
    for i in range(6):
        yy = cy + h * .12 + i * h * .045
        d.line([(cx + w * .3, yy), (cx + w * .42, yy)], fill=(50, 36, 24), width=4)
    d.line([(cx - w * .3, cy + h / 2), (cx - w * .36, cy + h / 2 + w * .12)], fill=(40, 30, 20), width=10)
    d.line([(cx + w * .3, cy + h / 2), (cx + w * .36, cy + h / 2 + w * .12)], fill=(40, 30, 20), width=10)

# ------------------------------------------------------------------ escenas
def pose_hold(ph=0.0):
    """jugador parado sujetando el balon a la altura del pecho (la 'congelacion')"""
    s = .03 * math.sin(ph)
    return dict(lh=.12, lk=.25, rh=.05, rk=.22, ls=1.05 + s, le=1.35, la=.05, rs=1.05 - s, re=1.35, ra=.05, lift=-.12, lean=.12)

def pose_guard(ph=0.0):
    """defensor esperando, rodillas flexionadas, brazos abiertos"""
    s = .05 * math.sin(ph)
    return dict(lh=.3, lk=.55, rh=.25, rk=.5, ls=.7 + s, le=.4, la=.9, rs=.7 - s, re=.4, ra=.9, lift=-.3, lean=.18)

def pose_boo(ph):
    a = 1.9 + .5 * abs(math.sin(ph))
    return dict(lh=.05, lk=.08, rh=-.03, rk=.06, ls=a, le=1.2, la=.25, rs=.25, re=.4, ra=.15, lift=.08 * abs(math.sin(ph * 2)), lean=.05)

def hold_ball(J):
    hl = hand_pos(J, 'l'); hr = hand_pos(J, 'r')
    return tuple((hl[i] + hr[i]) / 2 for i in range(3))

def stall_scene(lt, holder_x=-2.0, n_def=4, ph_speed=1.0):
    """Pistons quietos en el medio campo con el balon; Lakers esperando en la zona con Mikan"""
    h = piston(0, [(0, (holder_x, -3))])
    pis = [piston(i, [(0, p)]) for i, p in [(1, (-8, 12)), (2, (8, 14)), (3, (12, -12)), (4, (-10, -15))]]
    mk = mikan([(0, (34, 0))])
    lak = [laker(i, [(0, p)]) for i, p in [(1, (26, 7)), (2, (26, -7)), (3, (20, 2)), (4, (22, -11))]][:n_def]
    def dyn(dr, cam, k, off):
        for s_ in (-1, 1): E.draw_basket(dr, cam, s_, k=k, off=off)
        lst = [(p, E.pose_stand(), math.pi / 2 if p.pos(0)[1] < 0 else -math.pi / 2) for p in pis]
        lst += [(l, pose_guard(lt * 2 + i), math.pi) for i, l in enumerate(lak)] + [(mk, pose_guard(lt * 1.5), math.pi)]
        lst.append((h, pose_hold(lt * ph_speed), 0))
        J = draw_actors(dr, cam, lst, lt, k, off)
        E.draw_ball(dr, cam, hold_ball(J[id(h)]), k, off, spin=0)
    return dyn

def frame_spec(t):
    # ---------- A: gancho - el marcador final mas bajo de la historia
    if t < ps(1):
        cam = CAMS['side']; lt = t
        dyn0 = stall_scene(lt)
        cu, cv = cam.p((6, 0, 4))[:2]
        def ov(img, x0, y0, kk):
            d = ImageDraw.Draw(img)
            s = 1 + .12 * max(0, 1 - abs(lt - .35) / .3)
            if lt > .15:
                text_stroke(d, (W1 / 2, 640), '19–18', font('Anton-Regular.ttf', int(300 * s)), YEL, 12)
                text_stroke(d, (W1 / 2, 830), 'FINAL SCORE', font('BebasNeue-Regular.ttf', 96), (255, 255, 255), 6)
            if lt > 1.3: tv_label(img, (W1 / 2, 960), 'LOWEST-SCORING GAME IN NBA HISTORY', lt - 1.3, 54)
        return dict(cam=cam, bg='side', cu=cu, cv=cv - 120, zoom=1.9 + .1 * ease(lt / 4), dyn=lambda dr, k, off: dyn0(dr, cam, k, off), ov=ov,
                    bug=(19, 18, 'FINAL'))
    # ---------- B: el Minneapolis Auditorium desde detras de la canasta
    if t < ps(2):
        cam = CAMS['end']; lt = t - ps(1)
        z = 1.2 + .1 * ease(lt / 4)
        players = [piston(i, [(0, (-30 + 9 * i, -14 + 7 * i)), (5, (-22 + 9 * i, -8 + 6 * i))]) for i in range(3)] + \
                  [laker(i, [(0, (10 + 8 * i, 14 - 9 * i)), (5, (16 + 8 * i, 8 - 9 * i))]) for i in range(3)]
        def dyn(dr, k, off):
            E.draw_basket(dr, cam, 1, k=k, off=off)
            draw_actors(dr, cam, [(p, None, None) for p in players], lt, k, off)
            E.draw_basket(dr, cam, -1, k=k, off=off)
        def ov(img, x0, y0, kk):
            lower_third(img, ps(1) + .1, t, 'NOVEMBER 22, 1950', None, t_out=wt(1, 'The', 0) - .25)
            lower_third(img, wt(1, 'The', 0) - .05, t, 'MINNEAPOLIS AUDITORIUM', 'MINNEAPOLIS, MINNESOTA')
        return dict(cam=cam, bg='end', cu=cam.W / 2, cv=cam.p((-10, 0, 0))[1] - 250, zoom=z, dyn=dyn, ov=ov)
    # ---------- C: Pistons de visita contra los campeones
    if t < ps(3):
        cam = CAMS['side']; lt = t - ps(2); T = 2.6
        mk = mikan([(0, (34, -8)), (T, (3.5, 0))])
        lak = [mk] + [laker(i, [(0, (40 - 3 * i, 16 - 8 * i)), (T, (12 - 2 * i, 14 - 8 * i))]) for i in range(1, 5)]
        pis = [piston(0, [(0, (-34, 10)), (T, (-3.5, 0))])] + [piston(i, [(0, (-40 + 3 * i, -16 + 7 * i)), (T, (-12 + 2 * i, -14 + 8 * i))]) for i in range(1, 5)]
        cx = lerp(-10, 0, ease(lt / T))
        cu, cv = cam.p((cx, 0, 3))[:2]
        def dyn(dr, k, off):
            for s_ in (-1, 1): E.draw_basket(dr, cam, s_, k=k, off=off)
            draw_actors(dr, cam, [(p, None, (0 if p.team == 'FW' else math.pi) if lt > T else None) for p in pis + lak], lt, k, off)
        def ov(img, x0, y0, kk):
            lower_third(img, ps(2) + .1, t, 'FORT WAYNE PISTONS', 'AT MINNEAPOLIS LAKERS')
            if t > wt(2, 'defending') - .1: tv_label(img, (W1 / 2, 520), 'DEFENDING CHAMPIONS', t - wt(2, 'defending') + .1)
        return dict(cam=cam, bg='side', cu=cu, cv=cv - 120, zoom=2.1, dyn=dyn, ov=ov, bug=(0, 0, '1ST QTR'))
    # ---------- D: George Mikan - gancho cerca del aro
    if t < ps(4):
        cam = CAMS['rim']; lt = t - ps(3); tj = 1.4
        mk = mikan([(0, (31, -6)), (tj, (36.5, -2.5)), (4, (36.6, -2.4))])
        d1 = piston(1, [(0, (33, -3)), (tj, (37.5, 0)), (4, (37.4, .2))])
        d2 = piston(2, [(0, (28, 6)), (4, (31, 4))])
        m1 = laker(1, [(0, (22, -11)), (4, (25, -10))])
        cu, cv = cam.p((36.5, -1, 6.5))[:2]
        def dyn(dr, k, off):
            jt = (lt - tj) / .9
            lst = [(d2, None, None), (m1, None, None)]
            dj = (lt - tj + .1) / .8
            lst.append((d1, E.pose_jump(clamp(dj), 'both', .8) if 0 < dj < 1 else None, math.pi))
            lst.append((mk, E.pose_jump(jt, 'one', 1.0) if 0 < jt < 1 else None, .35 if jt > -.4 else None))
            E.draw_basket(dr, cam, -1, k=k, off=off); E.draw_basket(dr, cam, 1, k=k, off=off)
            J = draw_actors(dr, cam, lst, lt, k, off)
            x, y = mk.pos(lt)
            if jt < 0: bp = (x + .8, y - .8, .5 + 2.6 * abs(math.sin(lt * 5.5)))
            elif jt < .45: bp = hand_pos(J[id(mk)], 'r')
            elif jt < 1.05:
                u = (jt - .45) / .6; bp = (lerp(x + .4, RIM_X, u), lerp(y, 0, u), 11.2 + 2.0 * math.sin(math.pi * u) - 1.0 * u)
            else:
                u = min(1, (jt - 1.05) / .5); bp = (RIM_X, 0, 10.2 - 9 * u)
            E.draw_ball(dr, cam, bp, k, off, spin=lt * 5)
        def ov(img, x0, y0, kk):
            lower_third(img, ps(3) + .2, t, 'GEORGE MIKAN · #99', "LAKERS CENTER · 6'10\"")
        return dict(cam=cam, bg='rim', cu=cu, cv=cv, zoom=1.0 + .08 * ease(lt / 3.5), dyn=dyn, ov=ov, bug=None)
    # ---------- E: el plan - que Mikan no toque el balon: no tirar
    if t < ps(5):
        cam = CAMS['side']; lt = t - ps(4)
        dyn0 = stall_scene(lt)
        cu, cv = cam.p((lerp(4, 14, ease(lt / 4)), 0, 4))[:2]
        def ov(img, x0, y0, kk):
            tv_label(img, (W1 / 2, 500), "FORT WAYNE'S PLAN", lt - .1, 62)
            if lt > .6: tv_label(img, (W1 / 2, 610), 'KEEP THE BALL AWAY FROM MIKAN', lt - .6, 56)
            if t > wt(4, 'shoot') - .35:
                d = ImageDraw.Draw(img); s = 1 + .12 * max(0, 1 - abs(t - wt(4, 'shoot') - .1) / .3)
                text_stroke(d, (W1 / 2, 820), "DON'T SHOOT.", font('Anton-Regular.ttf', int(160 * s)), YEL, 10)
        return dict(cam=cam, bg='side', cu=cu, cv=cv - 120, zoom=2.0, dyn=lambda dr, k, off: dyn0(dr, cam, k, off), ov=ov, bug=None)
    # ---------- F: no habia reloj de posesion (mesa de anotadores: solo el reloj de partido)
    if t < ps(6):
        cam = CAMS['table']; lt = t - ps(5)
        cu, cv = cam.p((0, -31, 3.4))[:2]
        def dyn(dr, k, off):
            draw_table(dr, cam, k, off, clock='game')
        def ov(img, x0, y0, kk):
            tv_label(img, (W1 / 2, 400), 'NO SHOT CLOCK', lt, 80)
            if lt > .4: tv_label(img, (W1 / 2, 520), 'NO TIME LIMIT TO SHOOT', lt - .4, 54)
        return dict(cam=cam, bg='table', cu=cu, cv=cv + 150, zoom=1.0 + .06 * ease(lt / 2), dyn=dyn, ov=ov, bug=None)
    # ---------- G: posesiones de hasta tres minutos
    if t < ps(7):
        cam = CAMS['tight']; lt = t - ps(6)
        dyn0 = stall_scene(lt, holder_x=-8, ph_speed=.6)
        cu, cv = cam.p((-6, -3, 4))[:2]
        def ov(img, x0, y0, kk):
            u = clamp((lt - .3) / (ps(7) - ps(6) - .6))
            secs = int(180 * u)
            d = ImageDraw.Draw(img, 'RGBA'); y = 470
            d.rounded_rectangle([250, y, W1 - 250, y + 230], radius=18, fill=(12, 14, 22, 232), outline=(196, 34, 40, 255), width=6)
            d.text((W1 / 2, y + 52), 'ONE POSSESSION', font=font('BebasNeue-Regular.ttf', 60), fill=(255, 255, 255), anchor='mm')
            d.text((W1 / 2, y + 150), f'{secs // 60}:{secs % 60:02d}', font=font('Anton-Regular.ttf', 120), fill=YEL, anchor='mm')
        return dict(cam=cam, bg='tight', cu=cu, cv=cv - 60, zoom=1.15, dyn=lambda dr, k, off: dyn0(dr, cam, k, off), ov=ov, bug=(11, 13, 'HALFTIME'))
    # ---------- H: 7.021 aficionados abucheando
    if t < ps(8):
        cam = CAMS['crowd']; lt = t - ps(7)
        cu, cv = cam.p((10, 51, 9))[:2]; cu += 60 * math.sin(lt * .8)
        fans = [Actor(keys=[(0, (-6 + i * 4.2, 49.5 + (i % 2) * 2.4))], height=5.8 + (i % 3) * .15, skin=random.Random(i).choice(['light', 'light2', 'tan', 'light']),
                      fan=(random.Random(i * 3).choice([(60, 52, 46), (40, 44, 58), (92, 76, 58), (70, 70, 74), (120, 100, 80)]), (46, 44, 48),
                           (44, 38, 34) if i % 3 != 1 else None)) for i in range(9)]
        def dyn(dr, k, off):
            for i, f in enumerate(fans):
                pose = dict(pose_boo(lt * 7 + i * 1.3) if (i % 3 != 2 or lt > 1) else E.pose_stand())
                stomp = .12 * max(0, math.sin(lt * 9 + i))
                pose['lift'] = pose.get('lift', 0) + 4.0 + 1.85 * (1 if f.pos(0)[1] > 50 else 0) + stomp
                x, y = f.pos(lt)
                PP.draw_fan62(dr, cam, x, y, -math.pi / 2 - .3, pose, coat=f.fan[0], trousers=f.fan[1], hat=f.fan[2], skin=f.skin, k=k, off=off, height=f.height)
        def ov(img, x0, y0, kk):
            d = ImageDraw.Draw(img); sh = 6 * math.sin(t * 40)
            text_stroke(d, (W1 / 2 + sh, 640), 'BOOOO!', font('Anton-Regular.ttf', 190), (255, 255, 255), 10)
            n = int(7021 * ease((lt - .1) / 1.6))
            lower_third(img, ps(7) + .1, t, f'ATTENDANCE: {n:,}', 'BOOING AND STOMPING')
        return dict(cam=cam, bg='crowd', cu=cu, cv=cv - 200, zoom=1.35, dyn=dyn, ov=ov, bug=None)
    # ---------- I: los Lakers, un punto en todo el ultimo cuarto
    if t < ps(9):
        cam = CAMS['side']; lt = t - ps(8)
        dyn0 = stall_scene(lt, holder_x=-4)
        cu, cv = cam.p((8, 0, 4))[:2]
        def ov(img, x0, y0, kk):
            big_card(img, t, ps(8) + .1, [('LAKERS · 4TH QUARTER', 'BebasNeue-Regular.ttf', 70, (255, 214, 120)),
                                          ('1', 'Anton-Regular.ttf', 220, YEL),
                                          ('POINT', 'BebasNeue-Regular.ttf', 90, (255, 255, 255))], y=420)
        return dict(cam=cam, bg='side', cu=cu, cv=cv - 120, zoom=1.9, dyn=lambda dr, k, off: dyn0(dr, cam, k, off), ov=ov, bug=None, dim=.75)
    # ---------- J: ultimos segundos, 18-17 para los Lakers
    if t < ps(10):
        cam = CAMS['side']; lt = t - ps(9)
        dyn0 = stall_scene(lt, holder_x=lerp(-2, 6, ease(lt / 3)), ph_speed=3)
        cu, cv = cam.p((lerp(8, 18, ease(lt / 3)), 0, 4))[:2]
        def ov(img, x0, y0, kk):
            tv_label(img, (W1 / 2, 520), 'FINAL SECONDS', lt - .05, 76)
        return dict(cam=cam, bg='side', cu=cu, cv=cv - 120, zoom=2.0, dyn=lambda dr, k, off: dyn0(dr, cam, k, off), ov=ov, bug=(17, 18, '4TH QTR'))
    # ---------- K: Foust por encima de los brazos de Mikan
    if t < ps(11):
        cam = CAMS['rim']; lt = t - ps(10); tj = 1.5
        fo = piston(0, [(0, (28, -9)), (tj, (36.2, -3.0)), (4, (36.3, -2.9))], number=None, **FOUST)
        mk = mikan([(0, (36, 3)), (tj, (38.0, -.6)), (4, (38.0, -.6))])
        o1 = laker(1, [(0, (24, 8)), (4, (29, 6))]); o2 = piston(2, [(0, (20, -14)), (4, (24, -12))])
        cu, cv = cam.p((36.5, -1, 6.5))[:2]
        def dyn(dr, k, off):
            jt = (lt - tj) / .9; mj = (lt - tj - .05) / .85
            lst = [(o1, None, None), (o2, None, None)]
            lst.append((mk, E.pose_jump(clamp(mj), 'both', 1.0) if 0 < mj < 1 else None, math.pi + .4 if lt > .5 else None))
            lst.append((fo, E.pose_jump(jt, 'one', 1.0) if 0 < jt < 1 else None, .2 if jt > -.4 else None))
            E.draw_basket(dr, cam, -1, k=k, off=off); E.draw_basket(dr, cam, 1, k=k, off=off)
            J = draw_actors(dr, cam, lst, lt, k, off)
            x, y = fo.pos(lt)
            if jt < 0: bp = (x + .8, y - .8, .5 + 2.6 * abs(math.sin(lt * 5.5)))
            elif jt < .5: bp = hand_pos(J[id(fo)], 'r')
            elif jt < 1.15:
                u = (jt - .5) / .65; bp = (lerp(x + .5, RIM_X, u), lerp(y, 0, u), 11.6 + 3.2 * math.sin(math.pi * u) - 1.4 * u)
            else:
                u = min(1, (jt - 1.15) / .5); bp = (RIM_X, 0, 10.2 - 9 * u)
            E.draw_ball(dr, cam, bp, k, off, spin=lt * 5)
        made = lt > tj + 1.2
        def ov(img, x0, y0, kk):
            lower_third(img, ps(10) + .15, t, 'LARRY FOUST', 'PISTONS ROOKIE')
            if made:
                d = ImageDraw.Draw(img); s = 1 + .15 * max(0, 1 - (lt - tj - 1.2) / .3)
                text_stroke(d, (W1 / 2, 650), 'GOOD!', font('Anton-Regular.ttf', int(200 * s)), YEL, 10)
        return dict(cam=cam, bg='rim', cu=cu, cv=cv, zoom=1.0 + .1 * ease(lt / 3), dyn=dyn, ov=ov, bug=(19 if made else 17, 18, '4TH QTR'))
    # ---------- L: final 19-18
    if t < ps(12):
        cam = CAMS['end']; lt = t - ps(11)
        def ov(img, x0, y0, kk):
            big_card(img, t, ps(11) + .05, [('FINAL', 'BebasNeue-Regular.ttf', 80, (255, 214, 120)),
                                           ('19 – 18', 'Anton-Regular.ttf', 170, (255, 255, 255)),
                                           ('PISTONS  ·  LAKERS', 'BebasNeue-Regular.ttf', 66, (230, 200, 200))], y=430)
            if t > wt(11, 'Thirty') - .1: tv_label(img, (W1 / 2, 960), '37 POINTS IN 48 MINUTES', t - wt(11, 'Thirty') + .1, 62)
        return dict(cam=cam, bg='end', cu=cam.W / 2, cv=cam.p((-10, 0, 0))[1] - 250, zoom=1.2 + .05 * ease(lt / 3), dyn=None, ov=ov, bug=(19, 18, 'FINAL'), blur=5, dim=.7)
    # ---------- M: Mikan, 15 de los 18
    if t < ps(13):
        cam = CAMS['end']; lt = t - ps(12)
        mk = mikan([(0, (-20, 3))])
        def dyn(dr, k, off):
            E.draw_basket(dr, cam, 1, k=k, off=off)
            draw_actors(dr, cam, [(mk, E.pose_stand(), 0)], lt, k, off)
        def ov(img, x0, y0, kk):
            a = ease((lt - .1) / .4)
            if a <= 0: return
            d = ImageDraw.Draw(img, 'RGBA'); y = 470
            d.rounded_rectangle([110, y, W1 - 110, y + 400], radius=20, fill=(12, 14, 22, int(232 * a)), outline=(232, 184, 52, int(255 * a)), width=6)
            d.text((W1 / 2, y + 60), 'LAKERS POINTS', font=font('BebasNeue-Regular.ttf', 66), fill=(255, 255, 255), anchor='mm')
            bx0, bx1, by = 170, W1 - 170, y + 150
            u = ease((lt - .4) / 1.2)
            d.rectangle([bx0, by, bx1, by + 90], fill=(60, 62, 70))
            d.rectangle([bx0, by, bx0 + (bx1 - bx0) * 15 / 18 * u, by + 90], fill=(232, 184, 52))
            d.text((bx0 + 20, by + 45), 'MIKAN', font=font('BebasNeue-Regular.ttf', 58), fill=(20, 20, 20), anchor='lm')
            d.text((W1 / 2, y + 320), f'{int(round(15 * u))} OF 18', font=font('Anton-Regular.ttf', 110), fill=YEL, anchor='mm')
        return dict(cam=cam, bg='end', cu=cam.W / 2, cv=cam.p((-10, 0, 0))[1] - 250, zoom=1.3, dyn=dyn, ov=ov, bug=(19, 18, 'FINAL'), dim=.8)
    # ---------- N: la congelacion se extiende - el baloncesto aburre
    if t < ps(14):
        cam = CAMS['side']; lt = t - ps(13)
        dyn0 = stall_scene(lt, holder_x=-14, ph_speed=.3)
        cu, cv = cam.p((lerp(-4, 4, ease(lt / 3)), 0, 4))[:2]
        def ov(img, x0, y0, kk):
            tv_label(img, (W1 / 2, 520), 'STALLING SPREADS', lt - .05, 70)
            if t > wt(13, 'boring') - .2:
                d = ImageDraw.Draw(img)
                text_stroke(d, (W1 / 2, 720), 'BORING.', font('Anton-Regular.ttf', 170), (255, 255, 255), 10)
        return dict(cam=cam, bg='side', cu=cu, cv=cv - 120, zoom=1.7, dyn=lambda dr, k, off: dyn0(dr, cam, k, off), ov=ov, bug=None,
                    dim=1 - .3 * ease(lt / 2.5))
    # ---------- O: Danny Biasone - un limite de tiempo por posesion (cronometro en la mesa)
    if t < ps(15):
        cam = CAMS['table']; lt = t - ps(14)
        cu, cv = cam.p((0, -31, 3.4))[:2]
        def dyn(dr, k, off):
            draw_table(dr, cam, k, off, clock='stopwatch', t=lt)
        def ov(img, x0, y0, kk):
            lower_third(img, ps(14) + .1, t, 'DANNY BIASONE', 'OWNER · SYRACUSE NATIONALS')
            if t > wt(14, 'time') - .1: tv_label(img, (W1 / 2, 560), 'A TIME LIMIT ON EVERY POSSESSION', t - wt(14, 'time') + .1, 58)
        return dict(cam=cam, bg='table', cu=cu, cv=cv + 150, zoom=1.0 + .1 * ease(lt / 4), dyn=dyn, ov=ov, bug=None)
    # ---------- P: el reloj de 24 segundos (1954-55), en la mesa
    if t < ps(16):
        cam = CAMS['table']; lt = t - ps(15)
        t24 = wt(15, 'twenty-four') - ps(15)
        cu, cv = cam.p((0, -31, 3.4))[:2]
        def dyn(dr, k, off):
            draw_table(dr, cam, k, off, clock='shot', t=max(0, lt - t24))
        def ov(img, x0, y0, kk):
            tv_label(img, (W1 / 2, 300), 'THE 1954–55 SEASON', lt - .05, 58)
            if lt > t24 - .1:
                d = ImageDraw.Draw(img)
                text_stroke(d, (W1 / 2, 440), '24 SECONDS', font('Anton-Regular.ttf', 150), YEL, 10)
                text_stroke(d, (W1 / 2, 570), 'TO SHOOT', font('BebasNeue-Regular.ttf', 96), (255, 255, 255), 6)
        return dict(cam=cam, bg='table', cu=cu, cv=cv + 150, zoom=1.12, dyn=dyn, ov=ov, bug=None)
    # ---------- Q: +13 puntos por partido
    if t < ps(17):
        cam = CAMS['side']; lt = t - ps(16)
        run = [piston(i, [(0, (-30 + 6 * i, -12 + 6 * i)), (4, (20 + 4 * i, -10 + 5 * i))]) for i in range(4)] + \
              [laker(i, [(0, (-24 + 6 * i, -9 + 6 * i)), (4, (26 + 4 * i, -7 + 5 * i))]) for i in range(1, 5)]
        cu, cv = cam.p((lerp(-12, 22, ease(lt / 4)), 0, 4))[:2]
        def dyn(dr, k, off):
            for s_ in (-1, 1): E.draw_basket(dr, cam, s_, k=k, off=off)
            draw_actors(dr, cam, [(p, None, None) for p in run], lt, k, off)
            x, y = run[0].pos(lt); E.draw_ball(dr, cam, (x + .8, y - .8, .5 + 2.6 * abs(math.sin(lt * 6))), k, off, spin=lt * 5)
        def ov(img, x0, y0, kk):
            big_card(img, t, ps(16) + .1, [('THE NEXT SEASON', 'BebasNeue-Regular.ttf', 66, (255, 214, 120)),
                                          ('+13', 'Anton-Regular.ttf', 220, YEL),
                                          ('POINTS PER GAME', 'BebasNeue-Regular.ttf', 80, (255, 255, 255))], y=400)
            shot_clock_tile(img, 24 - int(clamp(lt / 4) * 20))
        return dict(cam=cam, bg='side', cu=cu, cv=cv - 120, zoom=1.9, dyn=dyn, ov=ov, bug=None)
    # ---------- R: cada posesion de hoy corre con ese reloj
    if t < ps(18):
        cam = CAMS['rim']; lt = t - ps(17); tj = 2.6
        sh = piston(3, [(0, (24, -10)), (tj, (33, -5)), (6, (33, -5))])
        df = laker(2, [(0, (27, -7)), (tj, (35, -3.4)), (6, (35, -3.4))])
        o1 = laker(3, [(0, (30, 8)), (6, (33, 5))]); o2 = piston(1, [(0, (18, 6)), (6, (22, 8))])
        cu, cv = cam.p((34, -1, 6.5))[:2]
        def dyn(dr, k, off):
            jt = (lt - tj) / .9
            lst = [(o1, None, None), (o2, None, None), (df, E.pose_jump(clamp(jt + .1), 'both', .8) if 0 < jt + .1 < 1 else None, math.pi + .4)]
            lst.append((sh, E.pose_jump(jt, 'one', 1.0) if 0 < jt < 1 else None, .3 if jt > -.4 else None))
            E.draw_basket(dr, cam, -1, k=k, off=off); E.draw_basket(dr, cam, 1, k=k, off=off)
            J = draw_actors(dr, cam, lst, lt, k, off)
            x, y = sh.pos(lt)
            if jt < 0: bp = (x + .8, y - .8, .5 + 2.6 * abs(math.sin(lt * 6)))
            elif jt < .5: bp = hand_pos(J[id(sh)], 'r')
            elif jt < 1.3:
                u = (jt - .5) / .8; bp = (lerp(x + .5, RIM_X, u), lerp(y, 0, u), 11.4 + 4.5 * math.sin(math.pi * u) - 1.2 * u)
            else:
                u = min(1, (jt - 1.3) / .5); bp = (RIM_X, 0, 10.2 - 9 * u)
            E.draw_ball(dr, cam, bp, k, off, spin=lt * 5)
        def ov(img, x0, y0, kk):
            tv_label(img, (W1 / 2, 500), 'EVERY POSSESSION, EVER SINCE', lt - .1, 60)
            if t > wt(17, 'because') - .1: tv_label(img, (W1 / 2, 620), 'THANKS TO A 19–18 GAME', t - wt(17, 'because') + .1, 60)
            shot_clock_tile(img, 24 - int(clamp(lt / (tj + .9)) * 21))
        return dict(cam=cam, bg='rim', cu=cu, cv=cv, zoom=1.0 + .1 * ease(lt / 5), dyn=dyn, ov=ov, bug=None)
    return dict(close=True)

def shot_clock_tile(img, n):
    d = ImageDraw.Draw(img, 'RGBA'); x = W1 - 60 - 230; y = 170
    d.rounded_rectangle([x, y, x + 230, y + 150], radius=12, fill=(12, 14, 22, 235))
    d.text((x + 115, y + 32), 'SHOT CLOCK', font=font('BebasNeue-Regular.ttf', 40), fill=(255, 214, 120), anchor='mm')
    d.text((x + 115, y + 100), str(max(0, n)), font=font('Anton-Regular.ttf', 80), fill=(255, 70, 50), anchor='mm')


# ------------------------------------------------------------------ subtitulos, marca, cierre, acabado
def subtitle_groups():
    groups = []
    for ph in PH:
        cur = []
        for w in ph['words']:
            cur.append(w)
            txt = ' '.join(x['w'] for x in cur)
            if len(cur) >= 3 or len(txt) > 15 or w['w'].endswith(('.', '?', ',', ':', '...', '!"', '!')):
                groups.append(cur); cur = []
        if cur: groups.append(cur)
    return groups
GROUPS = subtitle_groups()

def draw_subs(img, t):
    g = None
    for gr in GROUPS:
        if gr[0]['s'] - .05 <= t <= gr[-1]['e'] + .25: g = gr
    if g is None: return
    d = ImageDraw.Draw(img)
    f = font('Anton-Regular.ttf', 112)
    words = [w['w'].upper().replace('...', '…') for w in g]
    sp = d.textlength(' ', font=f)
    widths = [d.textlength(w, font=f) for w in words]
    lines = [[0]]; cw = widths[0]
    for i in range(1, len(words)):
        if cw + sp + widths[i] > 960: lines.append([i]); cw = widths[i]
        else: lines[-1].append(i); cw += sp + widths[i]
    y = 1290 - (len(lines) - 1) * 65
    for ln in lines:
        tw = sum(widths[i] for i in ln) + sp * (len(ln) - 1)
        x = W1 / 2 - tw / 2
        for i in ln:
            act = g[i]['s'] <= t < (g[i + 1]['s'] if i + 1 < len(g) else g[i]['e'] + .25)
            d.text((x, y), words[i], font=f, fill=YEL if act else (255, 255, 255), anchor='lm', stroke_width=9, stroke_fill=(0, 0, 0))
            x += widths[i] + sp
        y += 130

def watermark(img):
    d = ImageDraw.Draw(img, 'RGBA')
    d.text((W1 / 2, 84), HANDLE, font=font('Anton-Regular.ttf', 50), fill=(255, 255, 255, 195), anchor='mm', stroke_width=3, stroke_fill=(0, 0, 0, 160))

LOGO_IMG = None; CLOSE_BG = None
def close_frame(t):
    global LOGO_IMG, CLOSE_BG
    t0 = ps(18)
    if CLOSE_BG is None:
        bg = get_bg('end')
        b = bg.resize((W1 * bg.width // W2, H1), Image.LANCZOS)
        x0 = (b.width - W1) // 2
        b = b.crop((x0, 0, x0 + W1, H1)).filter(ImageFilter.GaussianBlur(14))
        CLOSE_BG = Image.eval(b, lambda v: int(v * .28))
    img = CLOSE_BG.copy()
    if LOGO_IMG is None: LOGO_IMG = Image.open(LOGO).convert('RGBA')
    a = ease((t - t0) / .5)
    s = int(lerp(520, 600, a))
    lg = LOGO_IMG.resize((s, s), Image.LANCZOS)
    if a < 1: lg.putalpha(lg.getchannel('A').point(lambda v: int(v * a)))
    img.paste(lg, (W1 // 2 - s // 2, 520 - s // 2 + 40), lg)
    d = ImageDraw.Draw(img)
    a2 = ease((t - wt(18, 'tomorrow')) / .3)
    if a2 > 0:
        text_stroke(d, (W1 / 2, 1010), "TOMORROW'S STORY?", font('Anton-Regular.ttf', int(110 * (.85 + .15 * a2))), (255, 255, 255), 8)
    a3 = ease((t - wt(18, 'vote')) / .3)
    if a3 > 0:
        bob = 10 * math.sin(t * 6)
        text_stroke(d, (W1 / 2 - 40, 1160), 'VOTE IN THE COMMENTS', font('BebasNeue-Regular.ttf', 92), YEL, 6)
        ax = W1 / 2 + 370; ay = 1160 + bob
        tri = [(ax - 26, ay - 10), (ax + 26, ay - 10), (ax, ay + 32)]
        d.rectangle([ax - 9, ay - 44, ax + 9, ay - 8], fill=YEL, outline=(0, 0, 0), width=4)
        d.polygon(tri, fill=YEL, outline=(0, 0, 0)); d.line(tri + [tri[0]], fill=(0, 0, 0), width=4)
        d.rectangle([ax - 6, ay - 41, ax + 6, ay - 6], fill=YEL)
    return img

VIGNETTE = None
def finish(img1, t):
    global VIGNETTE
    if VIGNETTE is None:
        yy, xx = np.mgrid[0:H1, 0:W1]
        r = np.sqrt(((xx - W1 / 2) / (W1 * .75)) ** 2 + ((yy - H1 / 2) / (H1 * .62)) ** 2)
        VIGNETTE = np.clip(1.08 - .38 * r ** 2, .55, 1.0)[..., None].astype(np.float32)
    a = np.asarray(img1).astype(np.float32) * VIGNETTE
    a[..., 0] *= 1.03; a[..., 2] *= .96
    rng = np.random.default_rng(int(t * 1000))
    a += rng.normal(0, 3.2, (H1 // 4, W1 // 4, 1)).repeat(4, 0).repeat(4, 1)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

def render_frame(t, subs=True):
    sp = frame_spec(t)
    if sp.get('close'):
        img = finish(close_frame(t), t); watermark(img); return img
    cam = sp['cam']; bg = get_bg(sp['bg'])
    z = sp['zoom']; cw, ch = W2 / z, H2 / z
    x0 = clamp(sp['cu'] - cw / 2, 0, bg.width - cw); y0 = clamp(sp['cv'] - ch / 2, 0, bg.height - ch)
    frame = bg.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch)))
    if frame.size != (W2, H2): frame = frame.resize((W2, H2), Image.BILINEAR)
    kk = W2 / int(cw)
    if sp.get('dim') is not None and sp['dim'] < 1:
        frame = Image.eval(frame, lambda v, d_=sp['dim']: int(v * d_))
    dr = ImageDraw.Draw(frame)
    if sp.get('dyn'): sp['dyn'](dr, kk, (x0, y0))
    img = frame.resize((W1, H1), Image.LANCZOS)
    if sp.get('blur'): img = img.filter(ImageFilter.GaussianBlur(sp['blur']))
    img = finish(img, t)
    if sp.get('ov'): sp['ov'](img, x0, y0, kk)
    if sp.get('bug'): score_bug(img, *sp['bug'])
    if subs: draw_subs(img, t)
    watermark(img)
    return img

def render_range(a, b, out):
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W1}x{H1}', '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '16', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
    for i in range(a, b):
        p.stdin.write(render_frame(i / FPS).tobytes())
        if i % 150 == 0: print('frame', i, flush=True)
    p.stdin.close(); p.wait()

if __name__ == '__main__':
    args = sys.argv[1:]
    if args and args[0] == '--test':
        for tt in args[1].split(','):
            render_frame(float(tt)).save(f'test_{float(tt):05.2f}.jpg', quality=88)
        sys.exit()
    if args and args[0] == '--cover':
        render_frame(float(args[1]), subs=False).save('hoops_lore_03_portada.jpg', quality=95); sys.exit()
    workers = int(os.environ.get('WORKERS', '4'))
    from multiprocessing import Process
    bounds = [NFR * i // workers for i in range(workers + 1)]
    procs = [Process(target=render_range, args=(bounds[i], bounds[i + 1], f'seg{i}.mp4')) for i in range(workers)]
    for p in procs: p.start()
    for p in procs: p.join()
    open('segs.txt', 'w').write(''.join(f"file 'seg{i}.mp4'\n" for i in range(workers)))
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', 'segs.txt', '-i', AUDIO, '-map', '0:v', '-map', '1:a',
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k', '-shortest', '_tmp_master.mp4'], check=True)
    # solo version TikTok: 950 kbps en dos pasadas (<10 MB)
    for pas in (1, 2):
        cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-i', '_tmp_master.mp4', '-c:v', 'libx264', '-preset', 'slow', '-b:v', '950k', '-pass', str(pas),
               '-passlogfile', '_x264', '-pix_fmt', 'yuv420p', '-r', '30']
        cmd += (['-an', '-f', 'mp4', os.devnull] if pas == 1 else ['-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', 'hoops_lore_03_tiktok.mp4'])
        subprocess.run(cmd, check=True)
    for f_ in ['_tmp_master.mp4', 'segs.txt'] + [f'seg{i}.mp4' for i in range(workers)] + [x for x in os.listdir('.') if x.startswith('_x264')]:
        try: os.remove(f_)
        except OSError: pass
    print('OK hoops_lore_03_tiktok.mp4', os.path.getsize('hoops_lore_03_tiktok.mp4') / 1e6, 'MB')
