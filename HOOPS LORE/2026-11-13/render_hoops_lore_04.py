"""Hoops Lore #04 - El partido de los aros a 12 pies: Milwaukee Hawks 63, Minneapolis Lakers 65 (7 mar 1954, Minneapolis Auditorium).
Render: python3 render_hoops_lore_04.py [--test t1,t2] [--cover t]"""
import json, math, os, sys, subprocess, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import engine as E
import people as PP
from engine import Cam, ease, clamp, lerp, font

E.LANE_HALF = 6.0          # zona de 12 pies (1951-64)
E.RIM_H = 12.0
HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 30; W1, H1 = 1080, 1920; W2, H2 = 2160, 3840
AUDIO = os.path.join(HERE, 'hoops_lore_04_voz.mp3')
LOGO = os.path.join(HERE, 'hoops_lore_logo.png')
HANDLE = '@hoopslore0'
PH = json.load(open(os.path.join(HERE, 'times_04.json')))
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
FW_R = [dict(team='MIL', number=n, height=h, skin=s, hair=hr) for n, h, s, hr in
        [(14, 6.6, 'light', (60, 44, 30)), (10, 6.2, 'light2', (40, 30, 22)), (7, 6.1, 'light', (110, 80, 50)), (12, 6.4, 'tan', (30, 22, 18)), (5, 6.3, 'light', (80, 60, 40))]]
MIN_R = [dict(team='MIN', number=n, height=h, skin=s, hair=hr) for n, h, s, hr in
         [(99, 6.83, 'light', (36, 28, 22)), (19, 6.6, 'light', (90, 66, 40)), (17, 6.3, 'light2', (50, 36, 26)), (34, 6.5, 'light', (70, 50, 30)), (22, 5.83, 'light', (40, 30, 22))]]
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
    """MIL (visitante) - MIN (local)"""
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    f = font('BebasNeue-Regular.ttf', 58); fs = font('Anton-Regular.ttf', 50)
    x = 60
    d.rounded_rectangle([x, y, x + 740, y + 84], radius=10, fill=(12, 14, 22, 235))
    d.rectangle([x + 10, y + 10, x + 22, y + 74], fill=(178, 30, 44)); d.text((x + 36, y + 44), 'MIL', font=f, fill='white', anchor='lm')
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

def hawk(i, keys, **kw): return piston(i, keys, **kw)

def rim_z(): return E.RIM_H

def shot_path(J, x, y, jt, made=True, rel=.5, flight=.7, apex=3.5, carom=None, lt=0.0):
    """posicion del balon en un tiro al aro de la derecha (RIM_X, 0, RIM_H).
    jt<0: bota; hasta rel: en la mano; luego vuelo; luego entra o rebota (carom=(x, y, z, dur, apex))."""
    rz = rim_z()
    if jt < 0: return (x + .8, y - .8, .5 + 2.6 * abs(math.sin(lt * 5.5)))
    if jt < rel: return hand_pos(J, 'r')
    if jt < rel + flight:
        u = (jt - rel) / flight
        z0 = 9.2 + .25 * (rz - 10)
        return (lerp(x + .5, RIM_X - (0 if made else .55), u), lerp(y, 0, u), lerp(z0, rz + .35, u) + apex * math.sin(math.pi * u))
    w = jt - rel - flight
    if made:
        u = min(1, w / .55); return (RIM_X, 0, rz + .2 - (rz - .8) * u * u)
    cx, cy, cz, dur, ap = carom or (RIM_X - 9, 5, 4.0, .9, 3.0)
    u = min(1, w / dur)
    return (lerp(RIM_X - .55, cx, u), lerp(0, cy, u), lerp(rz + .4, cz, u) + ap * math.sin(math.pi * u))

def quote_card(img, t, t0, quote_lines, who, sub=None, y=420, col=(255, 214, 120)):
    lines = [(q, 'Anton-Regular.ttf', 92, (255, 255, 255)) for q in quote_lines]
    lines += [('— ' + who, 'BebasNeue-Regular.ttf', 62, col)]
    if sub: lines += [(sub, 'BebasNeue-Regular.ttf', 46, (200, 200, 210))]
    big_card(img, t, t0, lines, y=y)

def stat_tile(img, label, value, y=270, pulse=0.0, col=(32, 64, 150)):
    d = ImageDraw.Draw(img, 'RGBA'); x = 60; s = 1 + .12 * pulse
    d.rounded_rectangle([x, y, x + 400 * s, y + 96 * s], radius=10, fill=col + (240,))
    d.text((x + 20, y + 48 * s), label, font=font('BebasNeue-Regular.ttf', int(50 * s)), fill='white', anchor='lm')
    d.text((x + 382 * s, y + 48 * s), value, font=font('Anton-Regular.ttf', int(64 * s)), fill=YEL, anchor='rm')

def rim_shot_scene(lt, tj, shooter, made, defender=None, extras=(), carom=None, apex=3.5, hook=False, rebounder=None, reb_t=None):
    """escena de cámara junto al aro: tiro de 'shooter' a los tj s; opcional rebote atrapado por 'rebounder'"""
    def dyn(dr, cam, k, off):
        jt = (lt - tj) / .9
        lst = [(a, None, None) for a in extras]
        if defender is not None:
            dj = (lt - tj + .1) / .8
            lst.append((defender, E.pose_jump(clamp(dj), 'both', .8) if 0 < dj < 1 else None, math.pi))
        rj = None
        if rebounder is not None:
            rj = (lt - reb_t) / .9
            lst.append((rebounder, E.pose_jump(clamp(rj), 'both', 1.0) if 0 < rj < 1 else None, -.3 if lt > tj else None))
        lst.append((shooter, E.pose_jump(jt, 'one', 1.0) if 0 < jt < 1 else None, (.35 if hook else .25) if jt > -.4 else None))
        E.draw_basket(dr, cam, -1, k=k, off=off); E.draw_basket(dr, cam, 1, k=k, off=off)
        J = draw_actors(dr, cam, lst, lt, k, off)
        x, y = shooter.pos(lt)
        if rebounder is not None and rj is not None and rj > .45:
            bp = hold_ball(J[id(rebounder)])
        else:
            bp = shot_path(J[id(shooter)], x, y, jt, made, apex=apex, carom=carom, lt=lt)
        E.draw_ball(dr, cam, bp, k, off, spin=lt * 5)
    return dyn

def frame_spec(t):
    E.RIM_H = 12.0
    # ---------- A: gancho - un partido oficial con los aros dos pies mas altos
    if t < ps(1):
        cam = CAMS['rim']; lt = t; tj = .5
        sh = laker(3, [(0, (30, -7)), (tj, (33.5, -4)), (5, (33.6, -4))])
        df = hawk(1, [(0, (31, -3)), (tj, (35.2, -2.6)), (5, (35.2, -2.6))])
        ex = [hawk(2, [(0, (27, 8)), (5, (29, 6))]), laker(1, [(0, (25, -12)), (5, (27, -10))])]
        dyn0 = rim_shot_scene(lt, tj, sh, False, df, ex, carom=(RIM_X - 6, 7, 3.5, 1.0, 2.5))
        cu, cv = cam.p((36, -1, 7.5))[:2]
        def ov(img, x0, y0, kk):
            d = ImageDraw.Draw(img)
            s_ = 1 + .12 * max(0, 1 - abs(lt - .35) / .3)
            if lt > .1:
                text_stroke(d, (W1 / 2, 560), '12-FOOT', font('Anton-Regular.ttf', int(230 * s_)), YEL, 12)
                text_stroke(d, (W1 / 2, 750), 'RIMS', font('Anton-Regular.ttf', int(150 * s_)), (255, 255, 255), 10)
            if lt > 1.2: tv_label(img, (W1 / 2, 890), 'ONE OFFICIAL NBA GAME', lt - 1.2, 60)
        return dict(cam=cam, bg='rim', cu=cu, cv=cv, zoom=1.0 + .08 * ease(lt / 4), dyn=lambda dr, k, off: dyn0(dr, cam, k, off), ov=ov)
    # ---------- B: el Minneapolis Auditorium desde detras de la canasta
    if t < ps(2):
        cam = CAMS['end']; lt = t - ps(1)
        z = 1.2 + .1 * ease(lt / 4)
        players = [hawk(i, [(0, (-30 + 9 * i, -14 + 7 * i)), (5, (-22 + 9 * i, -8 + 6 * i))]) for i in range(3)] + \
                  [laker(i, [(0, (10 + 8 * i, 14 - 9 * i)), (5, (16 + 8 * i, 8 - 9 * i))]) for i in range(3)]
        def dyn(dr, k, off):
            E.draw_basket(dr, cam, 1, k=k, off=off)
            draw_actors(dr, cam, [(p, None, None) for p in players], lt, k, off)
            E.draw_basket(dr, cam, -1, k=k, off=off)
        def ov(img, x0, y0, kk):
            lower_third(img, ps(1) + .1, t, 'MARCH 7, 1954', None, t_out=wt(1, 'The', 0) - .25)
            lower_third(img, wt(1, 'The', 0) - .05, t, 'MINNEAPOLIS AUDITORIUM', 'MINNEAPOLIS, MINNESOTA')
        return dict(cam=cam, bg='end', cu=cam.W / 2, cv=cam.p((-10, 0, 0))[1] - 250, zoom=z, dyn=dyn, ov=ov)
    # ---------- C: Hawks de visita contra los Lakers
    if t < ps(3):
        cam = CAMS['side']; lt = t - ps(2); T = 2.4
        mk = mikan([(0, (34, -8)), (T, (3.5, 0))])
        lak = [mk] + [laker(i, [(0, (40 - 3 * i, 16 - 8 * i)), (T, (12 - 2 * i, 14 - 8 * i))]) for i in range(1, 5)]
        haw = [hawk(0, [(0, (-34, 10)), (T, (-3.5, 0))])] + [hawk(i, [(0, (-40 + 3 * i, -16 + 7 * i)), (T, (-12 + 2 * i, -14 + 8 * i))]) for i in range(1, 5)]
        cx = lerp(-10, 0, ease(lt / T))
        cu, cv = cam.p((cx, 0, 3))[:2]
        def dyn(dr, k, off):
            for s_ in (-1, 1): E.draw_basket(dr, cam, s_, k=k, off=off)
            draw_actors(dr, cam, [(p, None, (0 if p.team == 'MIL' else math.pi) if lt > T else None) for p in haw + lak], lt, k, off)
        def ov(img, x0, y0, kk):
            lower_third(img, ps(2) + .1, t, 'MILWAUKEE HAWKS', 'AT MINNEAPOLIS LAKERS')
        return dict(cam=cam, bg='side', cu=cu, cv=cv - 120, zoom=2.1, dyn=dyn, ov=ov, bug=(0, 0, '1ST QTR'))
    # ---------- D: los aros suben de 10 a 12 pies
    if t < ps(4):
        cam = CAMS['rim']; lt = t - ps(3)
        t0 = wt(3, 'ten') - ps(3); t1 = wt(3, 'twelve') - ps(3) + .4
        u = ease(clamp((lt - t0) / max(t1 - t0, .5)))
        E.RIM_H = 10 + 2 * u
        ref = Actor(keys=[(0, (32, -6))], height=5.9, ref=True)
        mk = mikan([(0, (34, 3))])
        cu, cv = cam.p((37, -1, 7.5))[:2]
        def dyn(dr, k, off):
            E.draw_basket(dr, cam, -1, k=k, off=off); E.draw_basket(dr, cam, 1, k=k, off=off)
            draw_actors(dr, cam, [(ref, E.pose_stand(), .4), (mk, E.pose_stand(), .2)], lt, k, off)
        def ov(img, x0, y0, kk):
            tv_label(img, (W1 / 2, 400), 'FOR ONE NIGHT', lt - .05, 64)
            d = ImageDraw.Draw(img)
            ft = 10 + 2 * u
            text_stroke(d, (W1 / 2, 600), f'{ft:.0f} FT' if (u < .02 or u > .98) else f'{ft:.1f} FT', font('Anton-Regular.ttf', 190), YEL if u > .98 else (255, 255, 255), 10)
            if u > .98: tv_label(img, (W1 / 2, 760), 'BASKETS RAISED TWO FEET', lt - t1, 56)
        return dict(cam=cam, bg='rim', cu=cu, cv=cv, zoom=1.0, dyn=dyn, ov=ov)
    # ---------- E: el objetivo - los grandes como Mikan
    if t < ps(5):
        cam = CAMS['rim']; lt = t - ps(4); tj = 1.4
        mk = mikan([(0, (31, -6)), (tj, (36.5, -2.5)), (5, (36.6, -2.4))])
        d1 = hawk(1, [(0, (33, -3)), (tj, (37.5, 0)), (5, (37.4, .2))])
        ex = [hawk(2, [(0, (28, 6)), (5, (31, 4))]), laker(1, [(0, (22, -11)), (5, (25, -10))])]
        dyn0 = rim_shot_scene(lt, tj, mk, False, d1, ex, hook=True, carom=(RIM_X - 5, -6, 4.0, .9, 2.5), apex=2.2)
        cu, cv = cam.p((36.5, -1, 7.5))[:2]
        def ov(img, x0, y0, kk):
            tv_label(img, (W1 / 2, 420), 'THE TARGET: BIG MEN', lt - .05, 64)
            lower_third(img, ps(4) + .6, t, 'GEORGE MIKAN · #99', "LAKERS CENTER · 6'10\"")
        return dict(cam=cam, bg='rim', cu=cu, cv=cv, zoom=1.0 + .08 * ease(lt / 3.5), dyn=lambda dr, k, off: dyn0(dr, cam, k, off), ov=ov)
    # ---------- F: los universitarios debatian aros mas altos; la NBA lo prueba antes
    if t < ps(6):
        cam = CAMS['table']; lt = t - ps(5)
        cu, cv = cam.p((0, -31, 3.4))[:2]
        def dyn(dr, k, off):
            draw_table(dr, cam, k, off, clock='game', t=lt)
        def ov(img, x0, y0, kk):
            tv_label(img, (W1 / 2, 380), 'COLLEGES DEBATE HIGHER RIMS', lt - .05, 60)
            if t > wt(5, 'so') - .1: tv_label(img, (W1 / 2, 500), 'THE NBA TESTS IT FIRST', t - wt(5, 'so') + .1, 60)
        return dict(cam=cam, bg='table', cu=cu, cv=cv + 150, zoom=1.0 + .08 * ease(lt / 4), dyn=dyn, ov=ov)
    # ---------- G: "Nobody could hit the darn thing" - John Kundla
    if t < ps(7):
        cam = CAMS['side']; lt = t - ps(6); tj = .6
        sh = hawk(3, [(0, (22, -9)), (tj, (30, -6)), (6, (30, -6))])
        df = laker(2, [(0, (26, -5)), (tj, (32, -4)), (6, (32, -4))])
        ex = [laker(0, [(0, (34, 2))]), hawk(0, [(0, (28, 8)), (6, (30, 6))]), laker(1, [(0, (24, 10)), (6, (27, 9))])]
        dyn0 = rim_shot_scene(lt, tj, sh, False, df, ex, carom=(RIM_X - 8, 3, 3.0, 1.0, 3.0), apex=4.5)
        cu, cv = cam.p((30, 0, 5))[:2]
        def ov(img, x0, y0, kk):
            quote_card(img, t, ps(6) + .15, ['"NOBODY COULD HIT', 'THE DARN THING."'], 'JOHN KUNDLA', 'LAKERS COACH', y=380)
        return dict(cam=cam, bg='side', cu=cu, cv=cv - 60, zoom=2.4, dyn=lambda dr, k, off: dyn0(dr, cam, k, off), ov=ov)
    # ---------- H: los Lakers, 28,6 % en tiros de campo
    if t < ps(8):
        cam = CAMS['side']; lt = t - ps(7)
        run = [laker(i, [(0, (-24 + 6 * i, -10 + 5 * i)), (4, (18 + 4 * i, -8 + 4 * i))]) for i in range(1, 5)] + \
              [hawk(i, [(0, (-18 + 6 * i, -8 + 6 * i)), (4, (24 + 4 * i, -6 + 5 * i))]) for i in range(4)]
        cu, cv = cam.p((lerp(-8, 20, ease(lt / 4)), 0, 4))[:2]
        def dyn(dr, k, off):
            for s_ in (-1, 1): E.draw_basket(dr, cam, s_, k=k, off=off)
            draw_actors(dr, cam, [(p, None, None) for p in run], lt, k, off)
            x, y = run[0].pos(lt); E.draw_ball(dr, cam, (x + .8, y - .8, .5 + 2.6 * abs(math.sin(lt * 6))), k, off, spin=lt * 5)
        def ov(img, x0, y0, kk):
            u = ease((lt - .3) / 1.2)
            big_card(img, t, ps(7) + .1, [('LAKERS FIELD GOALS', 'BebasNeue-Regular.ttf', 70, (255, 214, 120)),
                                          (f'{28.6 * u:.1f}%', 'Anton-Regular.ttf', 200, YEL),
                                          ('22 OF 77 SHOTS', 'BebasNeue-Regular.ttf', 80, (255, 255, 255))], y=400)
        return dict(cam=cam, bg='side', cu=cu, cv=cv - 120, zoom=1.9, dyn=dyn, ov=ov, dim=.8)
    # ---------- I: Mikan falla los 12 primeros; acaba 2 de 14
    if t < ps(9):
        cam = CAMS['rim']; lt = t - ps(8); tj = 1.0
        mk = mikan([(0, (32, 5)), (tj, (36.3, 2.6)), (5, (36.3, 2.6))])
        d1 = hawk(4, [(0, (34, 3)), (tj, (37.6, 1.0)), (5, (37.6, 1.0))], height=6.7)
        ex = [hawk(2, [(0, (26, -8)), (5, (29, -6))]), laker(3, [(0, (24, 9)), (5, (27, 8))])]
        dyn0 = rim_shot_scene(lt, tj, mk, False, d1, ex, hook=True, carom=(RIM_X - 7, -4, 3.8, .9, 2.8), apex=2.2)
        cu, cv = cam.p((36.5, 0, 7.5))[:2]
        tf = wt(8, 'finished') - ps(8)
        def ov(img, x0, y0, kk):
            if lt < tf: stat_tile(img, 'MIKAN FG', f'0/{min(12, 1 + int(lt / max(tf - .3, .1) * 12))}', y=200)
            else: stat_tile(img, 'MIKAN FG', '2/14', y=200, pulse=max(0, 1 - (lt - tf) / .3))
            if lt > tf: tv_label(img, (W1 / 2, 560), '2 OF 14', lt - tf, 90)
        return dict(cam=cam, bg='rim', cu=cu, cv=cv, zoom=1.0 + .08 * ease(lt / 3.5), dyn=lambda dr, k, off: dyn0(dr, cam, k, off), ov=ov)
    # ---------- J: pero los grandes seguian cogiendo el rebote (rebote largo)
    if t < ps(10):
        cam = CAMS['rim']; lt = t - ps(9); tj = .3
        sh = hawk(3, [(0, (27, -10)), (tj, (31, -8)), (5, (31, -8))])
        rb = Actor(keys=[(0, (34.5, 4.5)), (1.2, (32.8, 3.4)), (5, (32.8, 3.4))], **dict(MIN_R[1], height=6.75))
        small = hawk(2, [(0, (33, 1)), (1.3, (33.6, 2.2)), (5, (33.6, 2.2))], height=6.0)
        ex = [laker(4, [(0, (24, 9)), (5, (26, 8))])]
        reb_arr = tj + .9 * (.5 + .7) + .8
        dyn0 = rim_shot_scene(lt, tj, sh, False, None, ex + [small], carom=(32.8, 3.4, 10.8, .8, 2.6), apex=4.0, rebounder=rb, reb_t=reb_arr - .45 * .9)
        cu, cv = cam.p((35, 0, 7.5))[:2]
        def ov(img, x0, y0, kk):
            if lt > reb_arr: tv_label(img, (W1 / 2, 460), 'BIG MEN STILL GOT THE REBOUNDS', lt - reb_arr, 58)
        return dict(cam=cam, bg='rim', cu=cu, cv=cv, zoom=1.0, dyn=lambda dr, k, off: dyn0(dr, cam, k, off), ov=ov)
    # ---------- K: Mikan - "threw the whole game out of sync"
    if t < ps(11):
        cam = CAMS['end']; lt = t - ps(10)
        mk = mikan([(0, (-20, 3))])
        def dyn(dr, k, off):
            E.draw_basket(dr, cam, 1, k=k, off=off)
            draw_actors(dr, cam, [(mk, E.pose_stand(), 0)], lt, k, off)
        def ov(img, x0, y0, kk):
            quote_card(img, t, ps(10) + .1, ['"IT THREW THE', 'WHOLE GAME', 'OUT OF SYNC."'], 'GEORGE MIKAN', 'TOUGHER ON THE SMALLER MAN', y=360)
        return dict(cam=cam, bg='end', cu=cam.W / 2, cv=cam.p((-10, 0, 0))[1] - 250, zoom=1.3, dyn=dyn, ov=ov, dim=.75)
    # ---------- L: Slater Martin, 5'10", queria una canasta de 6 pies
    if t < ps(12):
        cam = CAMS['tight']; lt = t - ps(11)
        sm = laker(4, [(0, (-12, -9)), (6, (-4, -7))])
        mk = mikan([(0, (-10, -5)), (6, (-2, -4))])
        hw = [hawk(1, [(0, (-6, -6)), (6, (2, -4))]), hawk(2, [(0, (-15, -2)), (6, (-6, 0))])]
        tq = wt(11, 'It', 0) - ps(11)
        cu, cv = cam.p((lerp(-9, -3, ease(lt / 6)), -7, 4))[:2]
        def dyn(dr, k, off):
            draw_actors(dr, cam, [(sm, None, None), (mk, None, None)] + [(h, None, None) for h in hw], lt, k, off)
            x, y = sm.pos(lt); E.draw_ball(dr, cam, (x + .7, y - .7, .5 + 2.2 * abs(math.sin(lt * 6))), k, off, spin=lt * 5)
        def ov(img, x0, y0, kk):
            lower_third(img, ps(11) + .1, t, 'SLATER MARTIN · #22', "LAKERS GUARD · 5'10\"", t_out=tq - .3)
            if lt > .9 and lt < tq: tv_label(img, (W1 / 2, 460), 'WANTED: A SIX-FOOT BASKET', lt - .9, 60)
            if lt >= tq - .1: quote_card(img, t, ps(11) + tq - .1, ['"IT WOULD MAKE', 'A MIKAN OUT OF ME."'], 'SLATER MARTIN', y=380)
        return dict(cam=cam, bg='tight', cu=cu, cv=cv - 60, zoom=1.15, dyn=dyn, ov=ov)
    # ---------- M: final 65-63 para los Lakers
    if t < ps(13):
        cam = CAMS['end']; lt = t - ps(12)
        def ov(img, x0, y0, kk):
            big_card(img, t, ps(12) + .05, [('FINAL', 'BebasNeue-Regular.ttf', 80, (255, 214, 120)),
                                           ('65 – 63', 'Anton-Regular.ttf', 170, (255, 255, 255)),
                                           ('LAKERS  ·  HAWKS', 'BebasNeue-Regular.ttf', 66, (232, 200, 120))], y=430)
        return dict(cam=cam, bg='end', cu=cam.W / 2, cv=cam.p((-10, 0, 0))[1] - 250, zoom=1.2 + .05 * ease(lt / 3), dyn=None, ov=ov, bug=(63, 65, 'FINAL'), blur=5, dim=.7)
    # ---------- N: esa primavera, campeones
    if t < ps(14):
        cam = CAMS['crowd']; lt = t - ps(13)
        cu, cv = cam.p((10, 51, 9))[:2]; cu += 50 * math.sin(lt * .8)
        fans = [Actor(keys=[(0, (-6 + i * 4.2, 49.5 + (i % 2) * 2.4))], height=5.8 + (i % 3) * .15, skin=random.Random(i).choice(['light', 'light2', 'tan', 'light']),
                      fan=(random.Random(i * 3).choice([(60, 52, 46), (40, 44, 58), (92, 76, 58), (70, 70, 74), (120, 100, 80)]), (46, 44, 48),
                           (44, 38, 34) if i % 3 != 1 else None)) for i in range(9)]
        def dyn(dr, k, off):
            for i, f in enumerate(fans):
                pose = dict(pose_cheer(lt * 6 + i * 1.1))
                pose['lift'] = pose.get('lift', 0) + 4.0 + 1.85 * (1 if f.pos(0)[1] > 50 else 0)
                x, y = f.pos(lt)
                PP.draw_fan62(dr, cam, x, y, -math.pi / 2 - .3, pose, coat=f.fan[0], trousers=f.fan[1], hat=f.fan[2], skin=f.skin, k=k, off=off, height=f.height)
        def ov(img, x0, y0, kk):
            big_card(img, t, ps(13) + .1, [('THAT SPRING', 'BebasNeue-Regular.ttf', 70, (255, 214, 120)),
                                          ('NBA', 'Anton-Regular.ttf', 150, YEL),
                                          ('CHAMPIONS', 'Anton-Regular.ttf', 130, (255, 255, 255))], y=420)
        return dict(cam=cam, bg='crowd', cu=cu, cv=cv - 200, zoom=1.35, dyn=dyn, ov=ov)
    # ---------- O: nunca se volvio a probar - los aros bajan
    if t < ps(15):
        cam = CAMS['rim']; lt = t - ps(14)
        u = ease(clamp((lt - .8) / 1.4)); E.RIM_H = 12 - 2 * u
        cu, cv = cam.p((37, -1, 7.5))[:2]
        def dyn(dr, k, off):
            E.draw_basket(dr, cam, -1, k=k, off=off); E.draw_basket(dr, cam, 1, k=k, off=off)
        def ov(img, x0, y0, kk):
            tv_label(img, (W1 / 2, 420), 'NEVER TRIED AGAIN IN THE NBA', lt - .05, 60)
        return dict(cam=cam, bg='rim', cu=cu, cv=cv, zoom=1.0, dyn=dyn, ov=ov)
    # ---------- P: setenta anos despues, siguen a 10 pies (canasta a 10 pies)
    if t < ps(16):
        cam = CAMS['rim']; lt = t - ps(15); tj = 1.6; E.RIM_H = 10.0
        sh = hawk(0, [(0, (27, -9)), (tj, (33, -5)), (6, (33, -5))])
        df = laker(2, [(0, (29, -6)), (tj, (35, -3.4)), (6, (35, -3.4))])
        ex = [laker(3, [(0, (30, 8)), (6, (33, 5))]), hawk(1, [(0, (18, 6)), (6, (22, 8))])]
        dyn0 = rim_shot_scene(lt, tj, sh, True, df, ex, apex=4.0)
        cu, cv = cam.p((35, -1, 6.5))[:2]
        def ov(img, x0, y0, kk):
            d = ImageDraw.Draw(img)
            text_stroke(d, (W1 / 2, 560), '10 FEET', font('Anton-Regular.ttf', 190), YEL, 10)
            tv_label(img, (W1 / 2, 730), 'STILL, 70+ YEARS LATER', lt - .3, 58)
        return dict(cam=cam, bg='rim', cu=cu, cv=cv, zoom=1.0 + .1 * ease(lt / 5), dyn=lambda dr, k, off: dyn0(dr, cam, k, off), ov=ov)
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
    t0 = ps(16)
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
    a2 = ease((t - wt(16, 'tomorrow')) / .3)
    if a2 > 0:
        text_stroke(d, (W1 / 2, 1010), "TOMORROW'S STORY?", font('Anton-Regular.ttf', int(110 * (.85 + .15 * a2))), (255, 255, 255), 8)
    a3 = ease((t - wt(16, 'vote')) / .3)
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
        render_frame(float(args[1]), subs=False).save('hoops_lore_04_portada.jpg', quality=95); sys.exit()
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
        cmd += (['-an', '-f', 'mp4', os.devnull] if pas == 1 else ['-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', 'hoops_lore_04_tiktok.mp4'])
        subprocess.run(cmd, check=True)
    for f_ in ['_tmp_master.mp4', 'segs.txt'] + [f'seg{i}.mp4' for i in range(workers)] + [x for x in os.listdir('.') if x.startswith('_x264')]:
        try: os.remove(f_)
        except OSError: pass
    print('OK hoops_lore_04_tiktok.mp4', os.path.getsize('hoops_lore_04_tiktok.mp4') / 1e6, 'MB')
