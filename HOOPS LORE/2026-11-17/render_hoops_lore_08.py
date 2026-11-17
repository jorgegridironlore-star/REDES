"""Hoops Lore #08 - Klay Thompson, 37 puntos en un cuarto: Warriors 126, Kings 101 (23 ene 2015, Oracle Arena, Oakland).
Render: python3 render_hoops_lore_08.py [--test t1,t2] [--cover t]"""
import json, math, os, sys, subprocess, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import engine as E
import people as PP
from engine import Cam, ease, clamp, lerp, font

# pabellon moderno (Oracle Arena, 2015): paleta azul y oro de los Warriors
E.PAL = E.PAL_ORACLE
E.TSHIRTS = [(250, 184, 30), (240, 176, 24), (28, 70, 160), (24, 56, 130), (236, 236, 232), (250, 184, 30), (60, 62, 70), (26, 26, 30), (28, 70, 160), (214, 210, 200), (250, 196, 60)]
# (base: pabellon moderno 2004): pista de arce con zona de 16 pies, linea de 3, gradas pegadas a la pista
E.COURT_STYLE = 'modern'
E.LANE_HALF = 8.0
E.RIM_H = 10.0
E.FLOOR_X, E.FLOOR_Y = 52.0, 30.0
E.RINK_X, E.RINK_Y, E.RINK_R = 60.0, 36.0, 14.0
E.STANDS = E.build_stands()
HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 30; W1, H1 = 1080, 1920; W2, H2 = 2160, 3840
AUDIO = os.path.join(HERE, 'hoops_lore_08_voz.mp3')
LOGO = os.path.join(HERE, 'hoops_lore_logo.png')
HANDLE = '@hoopslore0'
PH = json.load(open(os.path.join(HERE, 'times_08.json')))
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
    'three': Cam((-6, -24, 12), (36, -2, 7.0), 1500 * 2, 1500 * 2, H2),      # detras del tirador, hacia la canasta
    'three2': Cam((-9, -17, 12), (36, -2, 7.0), 1500 * 2, 1500 * 2, H2),
    'ftR': Cam((9, -3.5, 9.5), (42, 0, 8.0), 1500 * 2, 1500 * 2, H2),         # tiro libre visto desde detras
    'exit': Cam((-14, 22, 10), (-60, -2, 5), 1500 * 2, 1500 * 2, H2),         # aficionados que se van por el tunel
    'board': Cam((0, -52, 24), (0, -9, 44), 1500 * 2, 1500 * 2, H2),          # marcador central colgado
}
BG = {}
def get_bg(key):
    if key not in BG:
        md = {'tight': 10, 'crowd': 10, 'vault': 10, 'rim': 10, 'ft': 10, 'table': 8, 'three': 10, 'three2': 10, 'ftR': 10, 'exit': 10, 'board': 10}.get(key, 45)
        BG[key] = E.render_background(CAMS[key], venue='oracle', occupancy=.97, min_depth=md)
    return BG[key]

# ------------------------------------------------------------------ actores (movimiento natural: curvas suaves con aceleracion,
# pequenos desplazamientos de peso, defensores que siguen a su hombre con retraso, bote sincronizado con la mano)
class Actor:
    def __init__(self, team=None, number=None, height=6.4, keys=None, skin='light', hair=(50, 38, 28), build=1.0,
                 ref=False, fan=None, seed=None, wander=0.25, wfreq=None, dribble=False):
        self.team, self.number, self.height = team, number, height
        self.keys = keys or [(0, (0, 0))]
        self.skin, self.hair, self.build, self.ref, self.fan = skin, hair, build, ref, fan
        if seed is None:
            seed = hash((team, number, round(self.keys[0][1][0], 1), round(self.keys[0][1][1], 1))) & 0xffff
        r = random.Random(seed)
        self.ph = [r.uniform(0, 6.3) for _ in range(4)]
        self.wander = wander
        self.wf = wfreq if wfreq is not None else r.uniform(.22, .38)
        self.dribble = dribble
        self._dcache = {}
    def base(self, t):
        ks = self.keys
        if t <= ks[0][0]: return ks[0][1]
        if t >= ks[-1][0]: return ks[-1][1]
        n = len(ks)
        def tan(i):
            if i == 0 or i == n - 1: return (0.0, 0.0)
            # se para en este punto si el tramo anterior o el siguiente es casi nulo
            if math.dist(ks[i][1], ks[i - 1][1]) < .3 or math.dist(ks[i][1], ks[i + 1][1]) < .3: return (0.0, 0.0)
            dt = ks[i + 1][0] - ks[i - 1][0]
            return ((ks[i + 1][1][0] - ks[i - 1][1][0]) / dt, (ks[i + 1][1][1] - ks[i - 1][1][1]) / dt)
        for i in range(n - 1):
            (t0, p0), (t1, p1) = ks[i], ks[i + 1]
            if t <= t1:
                h = max(t1 - t0, 1e-6); u = (t - t0) / h
                m0, m1 = tan(i), tan(i + 1)
                h00 = 2 * u ** 3 - 3 * u ** 2 + 1; h10 = u ** 3 - 2 * u ** 2 + u; h01 = -2 * u ** 3 + 3 * u ** 2; h11 = u ** 3 - u ** 2
                return tuple(h00 * p0[j] + h10 * h * m0[j] + h01 * p1[j] + h11 * h * m1[j] for j in range(2))
        return ks[-1][1]
    def sway(self, t):
        a = self.wander; w = 2 * math.pi * self.wf; p = self.ph
        return (a * (.65 * math.sin(w * t + p[0]) + .35 * math.sin(1.9 * w * t + p[1])),
                a * .7 * (.6 * math.sin(.8 * w * t + p[2]) + .4 * math.sin(2.3 * w * t + p[3])))
    def pos(self, t):
        b = self.base(t); s = self.sway(t)
        return (b[0] + s[0], b[1] + s[1])
    def vel(self, t):
        a = self.pos(t - .06); b = self.pos(t + .06)
        return ((b[0] - a[0]) / .12, (b[1] - a[1]) / .12)
    def dist(self, t):
        key = round(t, 3)
        if key in self._dcache: return self._dcache[key]
        n = max(4, int(abs(t) * 20)); d = 0; prev = self.pos(0)
        for i in range(1, n + 1):
            p = self.pos(t * i / n); d += math.hypot(p[0] - prev[0], p[1] - prev[1]); prev = p
        self._dcache[key] = d
        return d

class Shadow(Actor):
    """defensor que sigue a su atacante con un poco de retraso, colocado entre el y la canasta que defiende"""
    def __init__(self, man, basket=(RIM_X, 0), gap=3.0, lag=.35, side=0.0, **kw):
        kw.setdefault('wander', .15)
        super().__init__(keys=[(0, man.pos(0))], **kw)
        self.man, self.basket, self.gap, self.lag, self.side = man, basket, gap, lag, side
    def pos(self, t):
        mx, my = self.man.pos(t - self.lag)
        dx, dy = self.basket[0] - mx, self.basket[1] - my; d = math.hypot(dx, dy) or 1
        s = self.sway(t)
        ux, uy = dx / d, dy / d
        return (mx + ux * self.gap - uy * self.side + s[0], my + uy * self.gap + ux * self.side + s[1])

def pose_walk(ph, spd):
    """paso natural: zancada y braceo segun la velocidad real (andar -> trotar -> correr)"""
    s = clamp(spd / 17, .16, 1.0)
    p = E.pose_run(ph, s)
    if s < .45:   # andando: rodillas casi rectas, brazos sueltos
        p['lk'] = .1 + .35 * s + .25 * max(0, -math.cos(ph)) * s; p['rk'] = .1 + .35 * s + .25 * max(0, math.cos(ph)) * s
        p['le'] = .35; p['re'] = .35; p['lean'] = .05
    return p

def pose_dribble_move(ph, spd, bt):
    p = pose_walk(ph, spd)
    c = math.cos(2 * math.pi * bt)
    p['rs'] = .55 + .22 * c; p['re'] = .55 - .15 * c; p['ra'] = .35
    p['lean'] = max(p.get('lean', 0), .14); p['lk'] = max(p['lk'], .22); p['rk'] = max(p['rk'], .22)
    return p

DRIB_T = .62
def draw_actors(dr, cam, lst, t, k, off, dim=1.0):
    """lst: (actor, pose|None, face|None). face puede ser un angulo o ('look', (x, y))"""
    items = []
    for a, pose, face in lst:
        x, y = a.pos(t); items.append((cam.depth((x, y, 3)), a, pose, face))
    items.sort(key=lambda q: -q[0])
    out = {}
    for _, a, pose, face in items:
        x, y = a.pos(t)
        v = a.vel(t); spd = math.hypot(*v)
        if isinstance(face, tuple):
            face = math.atan2(face[1][1] - y, face[1][0] - x)
        if face is not None and spd > 6:   # corriendo: mira hacia donde va, girando la cabeza hacia lo indicado
            vf = math.atan2(v[1], v[0]); dd = (face - vf + math.pi) % (2 * math.pi) - math.pi
            f0 = vf + clamp(dd, -.6, .6)
        elif face is not None: f0 = face
        else: f0 = math.atan2(v[1], v[0]) if spd > .9 else -math.pi / 2
        arms = None
        if isinstance(pose, tuple) and pose[0] == 'arms': arms = pose[1]; pose = None
        if pose is None:
            if a.dribble: pose = pose_dribble_move(a.dist(t) / 2.4 * math.pi, spd, t / DRIB_T)
            elif spd > .9: pose = pose_walk(a.dist(t) / 2.4 * math.pi, spd)
            else: pose = E.pose_stand()
        if arms: pose = dict(pose); pose.update(arms)
        if a.fan:
            out[id(a)] = PP.draw_fan62(dr, cam, x, y, f0, pose, coat=a.fan[0], trousers=a.fan[1], hat=a.fan[2], skin=a.skin,
                                       hair=a.hair, k=k, off=off, dim=dim, height=a.height, shirt=a.fan[0], tie=None)
        else:
            out[id(a)] = PP.draw_player62(dr, cam, x, y, f0, pose, a.team, a.number, a.height, a.skin, a.hair, k, off, dim,
                                          a.build, a.ref)
    return out

def dribble_ball(J, t, a=None):
    """balon botando desde la mano derecha: arriba en la mano, abajo en el suelo, con caida acelerada"""
    w = J['rwr']; e = J['rel']
    hx, hy, hz = (w[i] + (w[i] - e[i]) * .25 for i in range(3))
    u = (t / DRIB_T) % 1.0
    f = abs(2 * u - 1)          # 1 en la mano, 0 en el suelo
    z = .4 + (hz - .55) * (1 - (1 - f) ** 2)
    return (hx, hy, max(.4, z))

def P2F(cam, P, x0, y0, kk):
    u, v, d = cam.p(P); return ((u - x0) * kk / 2, (v - y0) * kk / 2)

def hand_pos(J, side='r'):
    w = J[side + 'wr']; e = J[side + 'el']
    return tuple(w[i] + (w[i] - e[i]) * .25 for i in range(3))

# reparto: Kings (SAC, de morado, visitante) y Warriors (GSW, de blanco, local; atacan la canasta de la derecha).
# Sin caras reales: los protagonistas se ven de espaldas o a media distancia, con rasgos genericos.
KLAY = dict(team='GSW', number=11, height=6.58, skin='light2', hair=(46, 34, 26), build=.97)
SAC_R = [dict(team='SAC', number=n, height=h, skin=s, hair=hr) for n, h, s, hr in
         [(15, 6.92, 'dark', None), (23, 6.42, 'brown', (20, 16, 14)), (3, 6.25, 'dark', (20, 16, 14)), (35, 6.75, 'light', (90, 70, 50)), (7, 6.33, 'brown', None)]]
GSW_R = [dict(team='GSW', number=n, height=h, skin=s, hair=hr) for n, h, s, hr in
         [(12, 7.0, 'light', (120, 90, 60)), (30, 6.25, 'tan', (30, 24, 20)), (23, 6.58, 'dark', None), (40, 6.67, 'brown', (20, 16, 14)), (9, 6.5, 'brown', (20, 16, 14))]]
FW_R = SAC_R; MIN_R = GSW_R
def piston(i, keys, **kw):
    d = dict(FW_R[i]); d.update(kw); return Actor(keys=keys, **d)
def laker(i, keys, **kw):
    d = dict(MIN_R[i]); d.update(kw); return Actor(keys=keys, **d)
sac = piston; gsw = laker
REF = dict(team=None, number=None, height=6.1, skin='light', hair=(60, 50, 40), ref=True)

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
    """SAC (visitante) - GSW (local)"""
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    f = font('BebasNeue-Regular.ttf', 58); fs = font('Anton-Regular.ttf', 50)
    x = 60
    d.rounded_rectangle([x, y, x + 740, y + 84], radius=10, fill=(12, 14, 22, 235))
    d.rectangle([x + 10, y + 10, x + 22, y + 74], fill=(110, 70, 170)); d.text((x + 36, y + 44), 'SAC', font=f, fill='white', anchor='lm')
    d.text((x + 175, y + 44), str(phi), font=fs, fill='white', anchor='mm')
    d.rectangle([x + 232, y + 10, x + 244, y + 74], fill=(250, 184, 30)); d.text((x + 258, y + 44), 'GSW', font=f, fill='white', anchor='lm')
    d.text((x + 392, y + 44), str(ny), font=fs, fill='white', anchor='mm')
    d.rectangle([x + 440, y + 8, x + 442, y + 76], fill=(80, 80, 90))
    d.text((x + 456, y + 44), label, font=f, fill=(255, 214, 120), anchor='lm')
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

def stall_scene(lt, holder_x=-2.0, n_def=4, ph_speed=1.0, pass_t=1.2):
    """la 'congelacion': el base de los Olympians bota despacio; un companero se acerca, recibe un pase al pecho,
    aguanta y se la devuelve con un pase picado; los demas apenas se mueven. Cada defensor sigue a su hombre."""
    h = piston(0, [(0, (holder_x, -3)), (6, (holder_x + 1.5, -1.5))], wander=1.0, wfreq=.16)
    pt = pass_t
    rc = piston(1, [(0, (holder_x - 8, 10)), (pt + .3, (holder_x - 5, 6.5)), (pt + 2.3, (holder_x - 4.6, 6.8)), (pt + 4.0, (holder_x - 8, 9.5))], wander=.3)
    spots = [(2, [(0, (holder_x + 9, 11)), (6, (holder_x + 8, 12))]),
             (3, [(0, (holder_x + 14, -9)), (1.8, (holder_x + 17, -5)), (3.6, (holder_x + 13.5, -9.5)), (6, (holder_x + 14, -8))]),
             (4, [(0, (holder_x - 4, -14)), (6, (holder_x - 2, -15))])]
    pis = [rc] + [piston(i, keys, wander=.7) for i, keys in spots]
    dfh = Shadow(h, gap=4.6, lag=.25, **MIN_R[4])
    dfs = [Shadow(p, gap=3.4, lag=.45, **MIN_R[j]) for j, p in zip((0, 1, 2, 3), pis)][:n_def]
    plan = BallPlan([('own', h, -99, pt, 'dribble'), ('pass', h, rc, pt, pt + .5, 'chest'), ('own', rc, pt + .5, pt + 1.7, 'hold'),
                     ('pass', rc, h, pt + 1.7, pt + 2.3, 'bounce'), ('own', h, pt + 2.3, 99, 'dribble')])
    def dyn(dr, cam, k, off):
        for s_ in (-1, 1): E.draw_basket(dr, cam, s_, k=k, off=off)
        s = plan.seg(lt)
        bxy = (s[1] if s[0] == 'own' else (s[1] if lt < (s[3] + s[4]) / 2 else s[2])).pos(lt)
        lst = []
        for p in pis:
            ar = plan.arms(p, lt)
            if ar: pose = ('arms', ar)
            else: pose = None if math.hypot(*p.vel(lt)) > .9 else E.pose_stand()
            lst.append((p, pose, ('look', bxy)))
        lst += [(d_, pose_guard(lt * 1.3 + i * 1.7), ('look', d_.man.pos(lt))) for i, d_ in enumerate(dfs)]
        lst.append((dfh, pose_guard(lt * 2.1), ('look', bxy)))
        h.dribble = plan.dribbling(h, lt)
        ar = plan.arms(h, lt)
        lst.append((h, ('arms', ar) if ar else None, ('look', rc.pos(lt)) if pt - .5 < lt < pt + 2.4 else ('look', (RIM_X, 0))))
        J = draw_actors(dr, cam, lst, lt, k, off)
        bp = plan.ball(lt, J)
        if bp: E.draw_ball(dr, cam, bp, k, off, spin=lt * 3)
    return dyn

def transition_play(lt, T=3.0, x0=-30, x1=10, shot_clock=False):
    """contraataque de los Olympians: el base sube botando y da un pase adelantado al companero que llena la calle
    central, que recibe y sigue botando; los Royals vuelven andando hacia atras siguiendo a su hombre"""
    bh = piston(1, [(0, (x0, -6)), (T * .45, (x0 + (x1 - x0) * .55, -4)), (T, (x1, -2)), (T + 3, (x1 + 4, -2))], wander=.3)
    rcv = piston(3, [(0, (x0 + 4, 3)), (T, (x1 + 9, 5)), (T + 3, (x1 + 13, 5))], wander=.3)
    lanes = [rcv] + [piston(i, [(0, (x0 - 4 - 2 * i, y0)), (T * (.9 + .1 * i), (x1 + 8 + 2 * i, y1)), (T + 3, (x1 + 10 + 2 * i, y1 + 1))], wander=.4)
                     for i, y0, y1 in [(0, -14, -12), (2, 10, 13), (4, -20, -18)]]
    dfs = [Shadow(m, gap=g, lag=lg, side=sd, **MIN_R[j]) for j, m, g, lg, sd in zip((4, 2, 0, 1, 3), [bh] + lanes, (7.5, 6, 7, 6, 7.5), (.08, .3, .5, .45, .55), (-2.5, -1.0, 1.5, -1.5, 2.0))]
    tp = T * .42
    plan = BallPlan([('own', bh, -99, tp, 'dribble'), ('pass', bh, rcv, tp, tp + .45, 'chest'), ('own', rcv, tp + .45, 99, 'dribble')])
    def dyn(dr, cam, k, off):
        for s_ in (-1, 1): E.draw_basket(dr, cam, s_, k=k, off=off)
        s = plan.seg(lt)
        bxy = (s[1] if s[0] == 'own' else s[2]).pos(lt)
        lst = []
        for p in [bh] + lanes:
            p.dribble = plan.dribbling(p, lt)
            ar = plan.arms(p, lt)
            lst.append((p, ('arms', ar) if ar else None, ('look', rcv.pos(lt)) if p is bh and tp - .5 < lt < tp + .3 else None))
        lst += [(d_, pose_guard(lt * 2 + i) if math.hypot(*d_.vel(lt)) < 2.5 else None, ('look', bxy)) for i, d_ in enumerate(dfs)]
        J = draw_actors(dr, cam, lst, lt, k, off)
        bp = plan.ball(lt, J)
        if bp: E.draw_ball(dr, cam, bp, k, off, spin=lt * 5)
    def ball_x(t):
        s = plan.seg(t)
        if s[0] == 'own': return s[1].base(t)[0]
        u = clamp((t - s[3]) / (s[4] - s[3])); return lerp(s[1].base(t)[0], s[2].base(t)[0], u)
    return dyn, ball_x

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

# ------------------------------------------------------------------ tiros y pases
SHOT_D = 1.0      # duracion del gesto de tiro (s)
REL_U = .55       # momento de soltar el balon dentro del gesto

def pose_shot(u, jump=1.0):
    """tiro a una mano de la epoca: flexion con el balon en el pecho, sube el balon por encima de la frente,
    extiende el brazo y suelta en lo alto del salto, mantiene la mano arriba y cae flexionando."""
    u = clamp(u, 0, 1.25)
    if u < .3:
        k = ease(u / .3)
        legs = dict(lh=.05 + .38 * k, lk=.1 + .62 * k, rh=.0 + .36 * k, rk=.08 + .6 * k, lift=-.38 * k, lean=.05 + .1 * k)
        arms = dict(ls=1.0 + .1 * k, le=1.4, la=.12, rs=1.0 + .1 * k, re=1.4, ra=.12)
    elif u < REL_U:
        k = ease((u - .3) / (REL_U - .3))
        legs = dict(lh=.43 * (1 - k) + .02, lk=.72 * (1 - k) + .05, rh=.36 * (1 - k), rk=.68 * (1 - k) + .04,
                    lift=-.38 * (1 - k) + 1.45 * jump * k, lean=.15 * (1 - k))
        arms = dict(ls=lerp(1.1, 2.25, k), le=lerp(1.4, 1.3, k), la=.12, rs=lerp(1.1, 2.4, k), re=lerp(1.4, 1.2, k), ra=.1)
    elif u < .7:
        k = ease((u - REL_U) / (.7 - REL_U))
        legs = dict(lh=.02, lk=.05 + .1 * k, rh=0, rk=.04 + .1 * k, lift=1.45 * jump * (1 - .1 * k), lean=-.02)
        arms = dict(ls=lerp(2.25, 2.0, k), le=lerp(1.3, 1.0, k), la=.18, rs=lerp(2.4, 2.8, k), re=lerp(1.2, .12, k), ra=.08)
    else:
        k = ease((u - .7) / .3)
        land = max(0, 1 - abs(u - 1.02) / .15)
        legs = dict(lh=.02 + .3 * land, lk=.15 + .45 * land, rh=.25 * land, rk=.14 + .4 * land, lift=1.3 * jump * (1 - k) - .3 * land, lean=.05 * land)
        arms = dict(ls=lerp(2.0, .9, k), le=lerp(1.0, .5, k), la=.18, rs=lerp(2.8, 1.2, k), re=lerp(.12, .4, k), ra=.1)
    legs.update(arms); return legs

ARMS_PASS = lambda w: dict(ls=lerp(.95, 1.45, w), le=lerp(1.55, .08, w), la=.1, rs=lerp(.95, 1.45, w), re=lerp(1.55, .08, w), ra=.1)
ARMS_CATCH = dict(ls=1.25, le=.55, la=.22, rs=1.25, re=.55, ra=.22)
ARMS_HOLD = dict(ls=1.05, le=1.35, la=.05, rs=1.05, re=1.35, ra=.05)

class BallPlan:
    """quien tiene el balon en cada momento y los pases entre jugadores.
    segs: ('own', actor, t0, t1, 'dribble'|'hold') y ('pass', de, a, t0, t1, 'chest'|'bounce')"""
    def __init__(self, segs): self.segs = segs
    def seg(self, t):
        for s in self.segs:
            if s[2 if s[0] == 'own' else 3] <= t < s[3 if s[0] == 'own' else 4]: return s
        return self.segs[-1] if t >= 0 else self.segs[0]
    def arms(self, a, t):
        """brazos de 'a' en t (pase, recepcion o sujetar) o None"""
        for s in self.segs:
            if s[0] == 'pass':
                _, fr, to, t0, t1, _st = s
                if fr is a and t0 - .3 <= t <= t0 + .2: return ARMS_PASS(ease((t - (t0 - .12)) / .14) if t > t0 - .12 else 0)
                if to is a and t1 - .35 <= t <= t1 + .12:
                    return ARMS_CATCH if t < t1 else dict(ARMS_HOLD, ls=lerp(1.25, 1.05, (t - t1) / .12), le=lerp(.55, 1.35, (t - t1) / .12))
        s = self.seg(t)
        if s[0] == 'own' and s[1] is a and s[4] == 'hold': return ARMS_HOLD
        return None
    def dribbling(self, a, t):
        s = self.seg(t)
        if s[0] == 'own' and s[1] is a and s[4] == 'dribble':
            for p in self.segs:   # deja de botar justo antes de pasar
                if p[0] == 'pass' and p[1] is a and p[3] - .3 <= t <= p[3]: return False
            return True
        return False
    def ball(self, t, J):
        s = self.seg(t)
        if s[0] == 'own':
            j = J.get(id(s[1]))
            if j is None: return None
            return dribble_ball(j, t) if self.dribbling(s[1], t) else hold_ball(j)
        _, fr, to, t0, t1, st = s
        A = hold_ball(J[id(fr)]); B = hold_ball(J[id(to)])
        u = clamp((t - t0) / max(t1 - t0, .05))
        if st == 'bounce':
            if u < .55:
                w = u / .55; return (lerp(A[0], lerp(A[0], B[0], .55), w), lerp(A[1], lerp(A[1], B[1], .55), w), lerp(A[2], .4, w))
            w = (u - .55) / .45; return (lerp(lerp(A[0], B[0], .55), B[0], w), lerp(lerp(A[1], B[1], .55), B[1], w), lerp(.4, B[2], w))
        return (lerp(A[0], B[0], u), lerp(A[1], B[1], u), lerp(A[2], B[2], u) + .6 * math.sin(math.pi * u))

def release_point(shooter, tj, face, jump=1.0):
    x, y = shooter.pos(tj + REL_U * SHOT_D)
    J = E.skeleton(x, y, face, pose_shot(REL_U, jump), shooter.height)
    return hold_ball(J)

def flight(R, made, t, dur, arc=4.0, carom=None):
    """balon en el aire tras soltarlo: parabola hasta el aro; si entra, cae por la red y bota; si no, rebota en el aro"""
    rz = E.RIM_H
    T = (RIM_X - (0 if made else .62), 0.0, rz + (.05 if made else .2))
    if t <= dur:
        u = t / dur
        top = max(R[2], T[2]) + arc
        return (lerp(R[0], T[0], u), lerp(R[1], T[1], u), lerp(R[2], T[2], u) + 4 * (top - (R[2] + T[2]) / 2) * u * (1 - u))
    w = t - dur
    if made:
        if w < .28: return (RIM_X - .05 * w, 0, rz - 1.7 * (w / .28) ** 1.3)        # frenado por la red
        w2 = w - .28; z = rz - 1.7 - 16 * w2 * w2 - 2 * w2
        if z > .4: return (RIM_X - .8 * w2, .2 * w2, z)
        tb = math.sqrt(max(0, (rz - 2.1) / 16)); w3 = w2 - tb   # bote en el suelo
        return (RIM_X - .8 * w2, .2 * w2, .4 + max(0, 5.5 * w3 - 16 * w3 * w3))
    cx, cy, cz, cd, ca = carom or (RIM_X - 8, 4, 4.0, .9, 3.0)
    u = min(1, w / cd)
    return (lerp(T[0], cx, u), lerp(T[1], cy, u), lerp(T[2], cz, u) + ca * math.sin(math.pi * u))

def swish_amount(t, tj, dur):
    w = t - (tj + REL_U * SHOT_D + dur)
    return max(0.0, math.sin(math.pi * clamp(w / .45))) if w > 0 else 0.0

def rim_shot_scene(lt, tj, shooter, made, defender=None, extras=(), carom=None, apex=None, hook=False, rebounder=None, reb_t=None,
                   passer=None, pass_t=None, jump=1.0, arc=4.2, face=None, contact=False):
    """tiro al aro de la derecha. Con 'passer': el balon llega con un pase y el tirador recibe y tira."""
    if face is None:
        sx, sy = shooter.base(tj); face = math.atan2(-sy, RIM_X - sx)
    R = release_point(shooter, tj, face, jump)
    dur = .55 + math.hypot(RIM_X - R[0], R[1]) * .028
    segs = []
    if passer is not None:
        t_arr = tj - .08
        segs = [('own', passer, -99, pass_t, 'dribble'), ('pass', passer, shooter, pass_t, t_arr, 'chest'), ('own', shooter, t_arr, 99, 'hold')]
    else:
        segs = [('own', shooter, -99, tj, 'dribble'), ('own', shooter, tj, 99, 'hold')]
    plan = BallPlan(segs)
    def dyn(dr, cam, k, off):
        u = (lt - tj) / SHOT_D
        lst = [(a, None, None) if not isinstance(a, tuple) else (a[0], a[2](lt) if len(a) > 2 else None, a[1]) for a in extras]
        if passer is not None:
            passer.dribble = plan.dribbling(passer, lt)
            ar = plan.arms(passer, lt)
            lst.append((passer, ('arms', ar) if ar else None, ('look', shooter.pos(lt)) if lt > pass_t - .6 else None))
        if defender is not None:
            dj = (lt - tj - (.12 if contact else .28)) / .8
            lst.append((defender, E.pose_jump(dj, 'one', .9) if 0 < dj < 1 else (pose_guard(lt * 2) if dj <= 0 and math.hypot(*defender.vel(lt)) < 3 else None), ('look', shooter.pos(lt))))
        rj = None
        if rebounder is not None:
            rj = (lt - reb_t) / .9
            lst.append((rebounder, E.pose_jump(clamp(rj), 'both', 1.0) if 0 < rj < 1 else None, -.3 if lt > tj else None))
        shooter.dribble = plan.dribbling(shooter, lt)
        if 0 <= u <= 1.25: sp = pose_shot(u, jump)
        else:
            ar = plan.arms(shooter, lt)
            sp = ('arms', ar) if ar else (E.pose_stand() if u > 1.25 else None)
        lst.append((shooter, sp, face if u > -.35 else None))
        E.NET_SWISH[1] = swish_amount(lt, tj, dur) if made else 0.0
        E.draw_basket(dr, cam, -1, k=k, off=off); E.draw_basket(dr, cam, 1, k=k, off=off)
        E.NET_SWISH[1] = 0.0
        J = draw_actors(dr, cam, lst, lt, k, off)
        tr = tj + REL_U * SHOT_D
        if rebounder is not None and rj is not None and rj > .45:
            bp = hold_ball(J[id(rebounder)])
        elif lt >= tr:
            bp = flight(R, made, lt - tr, dur, arc, carom)
        elif u >= 0:
            bp = hold_ball(J[id(shooter)])
        else:
            bp = plan.ball(lt, J)
        E.draw_ball(dr, cam, bp, k, off, spin=lt * (9 if lt >= tr else 4))
    return dyn


def clock_tile(img, label, text, col=(255, 255, 255)):
    d = ImageDraw.Draw(img, 'RGBA'); x = W1 - 60 - 250; y = 170
    d.rounded_rectangle([x, y, x + 250, y + 150], radius=12, fill=(12, 14, 22, 235))
    d.text((x + 125, y + 32), label, font=font('BebasNeue-Regular.ttf', 40), fill=(255, 214, 120), anchor='mm')
    d.text((x + 125, y + 100), text, font=font('Anton-Regular.ttf', 76), fill=col, anchor='mm')

def ot_card(img, t, t0, title, score, y=430):
    big_card(img, t, t0, [(title, 'BebasNeue-Regular.ttf', 80, (255, 214, 120)),
                          (score, 'Anton-Regular.ttf', 170, (255, 255, 255))], y=y)

def mmss(sec):
    sec = max(0, sec); return f'{int(sec // 60)}:{int(sec % 60):02d}'

def made_shot(lt, tj, team_sh, i_sh, i_df, carom=None, pass_lead=.7):
    """pase desde lo alto al tirador, que recibe en movimiento y tira (camara 'rim')"""
    mk = piston if team_sh == 'IND' else laker
    other = laker if team_sh == 'IND' else piston
    sh = mk(i_sh, [(-1.5, (27.5, -10.5)), (tj - .1, (32.2, -6.2)), (8, (32.3, -6.1))], wander=.1)
    ps_ = mk(4, [(-2, (19, 1)), (tj - pass_lead, (23, 2.5)), (8, (24, 3.5))], wander=.2)
    df = Shadow(sh, gap=3.2, lag=.35, side=.6, **(MIN_R[i_df] if other is laker else FW_R[i_df]))
    dps = Shadow(ps_, gap=5, lag=.5, **(MIN_R[2] if other is laker else FW_R[2]))
    ex = [other(3, [(0, (34, 6)), (8, (35, 4))], wander=.5), mk(2, [(0, (36, 9)), (8, (37, 7))], wander=.5), dps]
    return rim_shot_scene(lt, tj, sh, True, df, ex, passer=ps_, pass_t=tj - pass_lead)

# ------------------------------------------------------------------ utilidades (de los videos 06/07)
def sas(d0, keys, **kw):
    d = dict(d0); d.update(kw); return Actor(keys=keys, **d)

def paint_lineup(shooter_team='HOU'):
    """jugadores en los puestos de la zona durante un tiro libre (canasta de la derecha)"""
    out = []
    spots = [(39.2, 9.2, 'SAS', 0), (39.2, -9.2, 'SAS', 3), (35.7, 9.2, 'HOU', 0), (35.7, -9.2, 'HOU', 3)]
    for x, y, tm, i in spots:
        d = dict((FW_R if tm == 'SAS' else MIN_R)[i]); 
        a = Actor(keys=[(0, (x, y))], wander=.12, **d)
        out.append((a, -math.pi / 2 if y > 0 else math.pi / 2))
    oth = MIN_R if shooter_team == 'HOU' else FW_R
    for j, (x, y) in enumerate([(22, -12), (21, 11)]):
        out.append((Actor(keys=[(0, (x, y))], wander=.2, **dict(oth[(j + 2) % 5])), 0.0))
    return out

def three_scene(lt, tj, shooter, defender_kw, gap=4.5, side=-.8, contact=False, extras=None, jump=1.0):
    df = Shadow(shooter, basket=(RIM_X, 0), gap=gap, lag=.3, side=side, **defender_kw)
    if extras is None:
        extras = [laker(0, [(0, (36, 5)), (8, (37, 3))], wander=.4), piston(0, [(0, (37.5, 2.5)), (8, (38, 1.5))], wander=.4),
                  laker(3, [(0, (30, 14)), (8, (31, 13))], wander=.5), piston(3, [(0, (31.5, 11)), (8, (32, 10))], wander=.5)]
    return rim_shot_scene(lt, tj, shooter, True, df, extras, arc=7.0, contact=contact, jump=jump), df

def made_time(shooter, tj, jump=1.0):
    sx, sy = shooter.base(tj); face = math.atan2(-sy, RIM_X - sx)
    R = release_point(shooter, tj, face, jump)
    return tj + REL_U * SHOT_D + .55 + math.hypot(RIM_X - R[0], R[1]) * .028

def ft_scene(lt, tjs, shooter_kw, team='HOU'):
    """tiro(s) libre(s) a la canasta de la derecha, visto desde detras del tirador; bota antes de cada tiro"""
    scenes = []
    for tj in tjs:
        sh = Actor(keys=[(0, (RIM_X - 15.2, -.3))], wander=.02, dribble=True, **shooter_kw)
        scenes.append((tj, rim_shot_scene(lt, tj, sh, True, None, paint_lineup(team), jump=.15, arc=4.0)))
    def dyn(dr, cam, k, off):
        cur = scenes[0][1]
        for tj, d_ in scenes:
            if lt > tj - .9: cur = d_
        cur(dr, cam, k, off)
    return dyn

def tunnel(dr, cam, k, off):
    """boca de vomitorio en el fondo: hueco oscuro con paredes grises y rotulo de salida verde (sin texto de marca)"""
    poly_k(dr, cam, [(-59.0, -4.2, 0), (-59.0, 4.2, 0), (-59.0, 4.2, 7.4), (-59.0, -4.2, 7.4)], (54, 54, 60), k, off)
    poly_k(dr, cam, [(-59.1, -3.6, 0), (-59.1, 3.6, 0), (-59.1, 3.6, 6.9), (-59.1, -3.6, 6.9)], (12, 12, 14), k, off)
    poly_k(dr, cam, [(-59.2, -2.8, 0), (-59.2, 2.8, 0), (-59.2, 2.8, 6.3), (-59.2, -2.8, 6.3)], (24, 22, 22), k, off)
    poly_k(dr, cam, [(-58.95, -1.2, 7.6), (-58.95, 1.2, 7.6), (-58.95, 1.2, 8.5), (-58.95, -1.2, 8.5)], (30, 170, 80), k, off)

def poly_k(dr, cam, pts, col, k, off):
    pp = [cam.p(p) for p in pts]
    if min(q[2] for q in pp) < .5: return
    dr.polygon([((q[0] - off[0]) * k, (q[1] - off[1]) * k) for q in pp], fill=col)

def persp_coeffs(dst, src):
    A = []; B = []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    return np.linalg.solve(np.array(A, float), np.array(B, float)).tolist()

def jumbo_text(dr, cam, k, off, lines):
    """pone el marcador en la pantalla sur del videomarcador central (proyectado en perspectiva)"""
    img = dr._image
    J = E.JUMBO; x, y, z0, z1 = J['x'] * .9, J['y'], J['z0'] + 1.4, J['z1'] - 1.4
    q = [(-x, -y - .05, z1), (x, -y - .05, z1), (x, -y - .05, z0), (-x, -y - .05, z0)]
    pp = [cam.p(p) for p in q]
    dst = [((p[0] - off[0]) * k, (p[1] - off[1]) * k) for p in pp]
    W_, H_ = 1100, 640
    sc = Image.new('RGB', (W_, H_), (14, 18, 34)); d = ImageDraw.Draw(sc)
    for (txt, yy, size, col) in lines:
        d.text((W_ / 2, yy), txt, font=font('Anton-Regular.ttf', size), fill=col, anchor='mm')
    src = [(0, 0), (W_, 0), (W_, H_), (0, H_)]
    co = persp_coeffs(dst, src)
    warped = sc.transform(img.size, Image.PERSPECTIVE, co, Image.BILINEAR)
    mask = Image.new('L', (W_, H_), 255).transform(img.size, Image.PERSPECTIVE, co, Image.BILINEAR)
    img.paste(warped, (0, 0), mask)

def bug_clock(c):
    return f'{c:.1f}' if c < 60 else mmss(c)

TS_STEAL = None
def game_clock_end(t):
    """reloj real desde el robo (7.9 s) hasta el ultimo triple (1.7 s)"""
    TR = wt(13, 'Good') - 1.3          # suelta el ultimo triple
    return 7.9 - 6.2 * clamp((t - TS_STEAL) / (TR - TS_STEAL))

def tmac_pts_tile(img, pts, pulse=0.0):
    d = ImageDraw.Draw(img, 'RGBA'); x = 60; y = 270; s_ = 1 + .1 * pulse
    d.rounded_rectangle([x, y, x + 470 * s_, y + 96 * s_], radius=10, fill=(176, 22, 44, 240))
    d.text((x + 20, y + 30 * s_), 'McGRADY', font=font('BebasNeue-Regular.ttf', int(46 * s_)), fill='white', anchor='lm')
    d.text((x + 20, y + 70 * s_), 'LAST 35 SECONDS', font=font('BebasNeue-Regular.ttf', int(32 * s_)), fill=(255, 214, 200), anchor='lm')
    d.text((x + 450 * s_, y + 50 * s_), f'{pts} PTS', font=font('Anton-Regular.ttf', int(62 * s_)), fill=YEL, anchor='rm')

# ------------------------------------------------------------------ escenas de 2015 (Klay Thompson, 37 en un cuarto)
def klay(keys, **kw):
    d = dict(KLAY); d.update(kw); return Actor(keys=keys, **d)

def klay_tile(img, pts, pulse=0.0):
    d = ImageDraw.Draw(img, 'RGBA'); x = 60; y = 270; s_ = 1 + .1 * pulse
    d.rounded_rectangle([x, y, x + 470 * s_, y + 96 * s_], radius=10, fill=(28, 70, 160, 240))
    d.text((x + 20, y + 30 * s_), 'THOMPSON', font=font('BebasNeue-Regular.ttf', int(46 * s_)), fill='white', anchor='lm')
    d.text((x + 20, y + 70 * s_), '3RD QUARTER', font=font('BebasNeue-Regular.ttf', int(32 * s_)), fill=(255, 220, 140), anchor='lm')
    d.text((x + 450 * s_, y + 50 * s_), f'{pts} PTS', font=font('Anton-Regular.ttf', int(62 * s_)), fill=YEL, anchor='rm')

def shift_keys(sh, tj0, tj):
    sh.keys = [(k_[0] + (tj - tj0), k_[1]) for k_ in sh.keys]

def timed_three(lt, keys, tj0, mk, defender, gap=4.8, side=-.6, extras=None):
    """triple que entra justo en mk (tiempo local)"""
    sh = klay(keys, dribble=True, wander=.05)
    tj = tj0 + (mk - made_time(sh, tj0)); shift_keys(sh, tj0, tj)
    dyn0, _ = three_scene(lt, tj, sh, defender, gap=gap, side=side, extras=extras)
    return dyn0

def stat_lines(img, t, items, y=300):
    """tarjeta de estadistica que va creciendo: items = [(t0, texto grande, texto pequeno)]"""
    shown = [it for it in items if t > it[0]]
    if not shown: return
    lines = []
    for it in shown:
        lines.append((it[1], 'Anton-Regular.ttf', 92, YEL if it is shown[-1] else (255, 255, 255)))
        lines.append((it[2], 'BebasNeue-Regular.ttf', 44, (255, 214, 120)))
    big_card(img, t, items[0][0], lines, y=y)

def frame_spec(t):
    E.RIM_H = 10.0
    # ---------- A: gancho - triple de Klay; 37 puntos en un cuarto, sin fallar
    if t < ps(1):
        cam = CAMS['three2']; lt = t
        mk = wt(0, 'quarter') - .2
        dyn0 = timed_three(lt, [(0, (7, -13)), (1.4, (13, -10)), (2.1, (16.4, -7.2)), (9, (16.4, -7.2))], 2.2, mk, SAC_R[1], gap=5.5, side=-1.2)
        cu, cv = cam.p((24, -6, 5))[:2]
        tn = wt(0, 'never') - .1
        def ov(img, x0, y0, kk):
            d = ImageDraw.Draw(img)
            if lt > mk - .6:
                s_ = 1 + .12 * max(0, 1 - abs(lt - mk + .3) / .3)
                text_stroke(d, (W1 / 2, 500), '37 POINTS', font('Anton-Regular.ttf', int(190 * s_)), YEL, 12)
                text_stroke(d, (W1 / 2, 680), 'IN ONE QUARTER', font('Anton-Regular.ttf', int(104 * s_)), (255, 255, 255), 9)
            if t > tn: tv_label(img, (W1 / 2, 840), 'NOT ONE MISSED SHOT', t - tn, 72)
        return dict(cam=cam, bg='three2', cu=cu, cv=cv + 60, zoom=1.25 + .12 * ease(lt / 5), dyn=lambda dr, k, off: dyn0(dr, cam, k, off), ov=ov)
    # ---------- B: el pabellon desde detras de la canasta
    if t < ps(2):
        cam = CAMS['end']; lt = t - ps(1)
        z = 1.2 + .1 * ease(lt / 4.5)
        att = [sac(i, [(0, p0), (5.5, p1)], wander=.6) for i, p0, p1 in
               [(2, (-24, -3), (-8, -1)), (0, (-30, 12), (-16, 14)), (1, (-34, -15), (-19, -12)), (3, (-20, 6), (-6, 8))]]
        dfn = [Shadow(m, basket=(-RIM_X, 0), gap=g, lag=.45, **GSW_R[j]) for j, m, g in zip((1, 0, 2, 3), att, (4.5, 4, 5, 4))]
        att[0].dribble = True
        def dyn(dr, k, off):
            E.draw_basket(dr, cam, 1, k=k, off=off)
            bp = att[0].pos(lt)
            J = draw_actors(dr, cam, [(p, None, None) for p in att] + [(d_, None, ('look', bp)) for d_ in dfn], lt, k, off)
            E.draw_ball(dr, cam, dribble_ball(J[id(att[0])], lt), k, off, spin=lt * 5)
            E.draw_basket(dr, cam, -1, k=k, off=off)
        te = wt(1, 'Oracle')
        def ov(img, x0, y0, kk):
            lower_third(img, ps(1) + .1, t, 'JANUARY 23, 2015', None, t_out=te - .25)
            lower_third(img, te - .05, t, 'ORACLE ARENA', 'OAKLAND, CALIFORNIA')
        return dict(cam=cam, bg='end', cu=cam.W / 2, cv=cam.p((-10, 0, 0))[1] - 250, zoom=z, dyn=dyn, ov=ov)
    # ---------- C: los Kings suben el balon (camara de banda siguiendo el balon)
    if t < ps(3):
        cam = CAMS['side']; lt = t - ps(2); T = ps(3) - ps(2)
        dyn0, ball_x = transition_play(lt, T=T, x0=-26, x1=6)
        bx = sum(ball_x(lt + d) for d in (-.3, -.15, 0, .15, .3)) / 5
        cu, cv = cam.p((bx + 2, 0, 3))[:2]
        def ov(img, x0, y0, kk):
            lower_third(img, ps(2) + .1, t, 'SACRAMENTO KINGS', 'AT GOLDEN STATE WARRIORS')
        return dict(cam=cam, bg='side', cu=cu, cv=cv - 120, zoom=2.0, dyn=lambda dr, k, off: dyn0(dr, cam, k, off), ov=ov)
    # ---------- D: primera parte, 3 de 9 (videomarcador central)
    if t < ps(4):
        cam = CAMS['board']; lt = t - ps(3)
        cu, cv = cam.p((0, -9, 47))[:2]
        def dyn(dr, k, off):
            jumbo_text(dr, cam, k, off, [('THOMPSON', 120, 120, (255, 255, 255)), ('1ST HALF', 270, 100, (250, 190, 50)),
                                         ('3 OF 9 FG', 450, 150, (255, 255, 255))])
        tk = wt(3, 'Klay') - .1
        def ov(img, x0, y0, kk):
            tv_label(img, (W1 / 2, 1480), 'HALFTIME', lt - .05, 70)
            if t > tk: lower_third(img, tk, t, 'KLAY THOMPSON', 'WARRIORS GUARD · #11', y=1580)
        return dict(cam=cam, bg='board', cu=cu, cv=cv + 120, zoom=1.15 + .1 * ease(lt / 4), dyn=dyn, ov=ov)
    # ---------- E: 9:45 del 3er cuarto, tiro en suspension: 60-58
    if t < ps(5):
        cam = CAMS['rim']; lt = t - ps(4)
        mk = wt(4, 'Warriors') - ps(4) - .15
        sh = klay([(0, (24, -12)), (2.5, (28.5, -8.5)), (3.3, (29.5, -7.6)), (9, (29.5, -7.6))], dribble=True, wander=.05)
        tj0 = 3.4; tj = tj0 + (mk - made_time(sh, tj0)); shift_keys(sh, tj0, tj)
        df = Shadow(sh, gap=3.2, lag=.35, side=.6, **SAC_R[1])
        ex = [sac(3, [(0, (34, 6)), (8, (35, 4))], wander=.5), gsw(3, [(0, (36, 9)), (8, (37, 7))], wander=.5),
              sac(0, [(0, (37, 2)), (8, (38, 1))], wander=.4), gsw(2, [(0, (26, 12)), (8, (27, 11))], wander=.5)]
        dyn0 = rim_shot_scene(lt, tj, sh, True, df, ex)
        cu, cv = cam.p((34, -4, 6))[:2]
        def ov(img, x0, y0, kk):
            tv_label(img, (W1 / 2, 430), '3RD QUARTER · 9:45 LEFT', lt - .05, 62)
            if lt > mk: tv_label(img, (W1 / 2, 560), 'JUMPER · GOOD', lt - mk, 90)
            klay_tile(img, 2 if lt > mk else 0, max(0, 1 - abs(lt - mk - .2) / .25))
        return dict(cam=cam, bg='rim', cu=cu, cv=cv + 80, zoom=1.15, dyn=lambda dr, k, off: dyn0(dr, cam, k, off), ov=ov,
                    bug=(58, 60 if lt > mk else 58, '3RD QTR', '9:45'))
    # ---------- F: robo y triple al contraataque
    if t < ps(6):
        cam = CAMS['three']; lt = t - ps(5)
        mk = wt(5, 'three') - ps(5) + .1
        ts = wt(5, 'steals') - ps(5)
        dyn0 = timed_three(lt, [(0, (-2, -15)), (1.0, (8, -14)), (1.9, (16.6, -12.0)), (2.3, (17.6, -11.4)), (9, (17.6, -11.4))], 2.3, mk, SAC_R[2], gap=6.5, side=-1.5,
                           extras=[sac(0, [(0, (4, -6)), (3, (22, -4)), (9, (24, -3))], wander=.3), gsw(0, [(0, (0, 4)), (3, (24, 8)), (9, (26, 7))], wander=.3)])
        cu, cv = cam.p((24, -8, 5))[:2]
        def ov(img, x0, y0, kk):
            if lt > ts - .1 and lt < mk: tv_label(img, (W1 / 2, 430), 'STEAL!', lt - ts + .1, 100)
            if lt > mk: tv_label(img, (W1 / 2, 560), 'THREE!', lt - mk, 120)
            klay_tile(img, 5 if lt > mk else 2, max(0, 1 - abs(lt - mk - .2) / .25))
        return dict(cam=cam, bg='three', cu=cu, cv=cv + 60, zoom=1.22 + .06 * ease(lt / 3), dyn=lambda dr, k, off: dyn0(dr, cam, k, off), ov=ov)
    # ---------- G: y no para: otro triple desde el ala
    ta = wt(7, 'And')
    if t < ta - .1:
        cam = CAMS['three2']; lt = t - ps(6)
        mk = wt(7, 'three', 2) - ps(6)
        dyn0 = timed_three(lt, [(0, (8, -2)), (1.0, (12, -5)), (1.5, (14.5, -6.0)), (9, (14.5, -6.0))], 1.6, mk, SAC_R[4], gap=4.0, side=-.4)
        cu, cv = cam.p((24, -6, 5))[:2]
        def ov(img, x0, y0, kk):
            if lt > mk: tv_label(img, (W1 / 2, 560), 'THREE!', lt - mk, 120)
            klay_tile(img, 8 if lt > mk else 5, max(0, 1 - abs(lt - mk - .2) / .25))
        return dict(cam=cam, bg='three2', cu=cu, cv=cv + 60, zoom=1.3, dyn=lambda dr, k, off: dyn0(dr, cam, k, off), ov=ov)
    # ---------- H: el publico de Oracle cada vez mas fuerte
    if t < ps(8):
        cam = CAMS['crowd']; lt = t - ta
        cu, cv = cam.p((10, 51, 9))[:2]; cu += 40 * math.sin(lt * 7) * .3
        def ov(img, x0, y0, kk):
            tv_label(img, (W1 / 2, 430), 'ORACLE ARENA IS ROCKING', lt - .05, 64)
        return dict(cam=cam, bg='crowd', cu=cu, cv=cv - 200 + 6 * math.sin(lt * 23), zoom=1.3 + .08 * ease(lt / 4), dyn=None, ov=ov)
    # ---------- I: ultimos 3:03, Klay 18 - Kings 3 (videomarcador)
    if t < ps(9):
        cam = CAMS['board']; lt = t - ps(8); T = ps(9) - ps(8)
        cu, cv = cam.p((0, -9, 47))[:2]
        def dyn(dr, k, off):
            jumbo_text(dr, cam, k, off, [('LAST 3:03 OF THE 3RD', 110, 90, (250, 190, 50)), ('THOMPSON  18', 290, 150, (255, 255, 255)),
                                         ('KINGS  3', 470, 150, (255, 255, 255))])
        def ov(img, x0, y0, kk):
            tv_label(img, (W1 / 2, 1480), 'KLAY ALONE: 18 – 3', lt - .3, 76)
            klay_tile(img, 19 + int(round(18 * ease(clamp(lt / (T - .4))))))
        return dict(cam=cam, bg='board', cu=cu, cv=cv + 120, zoom=1.15 + .1 * ease(lt / 4), dyn=dyn, ov=ov)
    # ---------- J: 13/13, 9/9 y 2/2 (con los dos tiros libres)
    if t < ps(12):
        cam = CAMS['ftR']; lt = t - ps(9)
        tj1 = wt(11, 'Two') - ps(9) - 1.9; tj2 = wt(11, 'Both') - ps(9) - 1.5
        dyn0 = ft_scene(lt, [tj1, tj2], KLAY, team='HOU')
        cu, cv = cam.p((38, -.4, 8.5))[:2]; cv -= 260
        def ov(img, x0, y0, kk):
            stat_lines(img, t, [(ps(9) + .05, '13 OF 13', 'FIELD GOALS'), (ps(10), '9 OF 9', 'THREE-POINTERS'), (ps(11), '2 OF 2', 'FREE THROWS')], y=170)
        return dict(cam=cam, bg='ftR', cu=cu, cv=cv + 120, zoom=1.0, dyn=lambda dr, k, off: dyn0(dr, cam, k, off), ov=ov)
    # ---------- K: record de la NBA
    if t < ps(13):
        cam = CAMS['crowd']; lt = t - ps(12)
        cu, cv = cam.p((10, 51, 9))[:2]; cu += 60 * math.sin(lt * .6)
        tr = wt(12, 'NBA') - .3
        def ov(img, x0, y0, kk):
            big_card(img, t, ps(12) + .05, [('37', 'Anton-Regular.ttf', 230, YEL), ('POINTS IN ONE QUARTER', 'BebasNeue-Regular.ttf', 80, (255, 255, 255))], y=380)
            if t > tr: tv_label(img, (W1 / 2, 960), 'NEW NBA RECORD', t - tr, 96)
        return dict(cam=cam, bg='crowd', cu=cu, cv=cv - 200, zoom=1.3, dyn=None, ov=ov, blur=2)
    # ---------- L: el record anterior: 33 (Gervin y Anthony)
    if t < ps(14):
        cam = CAMS['end']; lt = t - ps(13)
        tg = wt(13, 'George') - .1
        def ov(img, x0, y0, kk):
            big_card(img, t, ps(13) + .05, [('OLD RECORD', 'BebasNeue-Regular.ttf', 80, (255, 214, 120)), ('33', 'Anton-Regular.ttf', 200, (255, 255, 255))], y=330)
            if t > tg:
                big_card(img, t, tg, [('GEORGE GERVIN', 'Anton-Regular.ttf', 84, (255, 255, 255)), ('SPURS · 1978', 'BebasNeue-Regular.ttf', 56, (200, 200, 210)),
                                      ('CARMELO ANTHONY', 'Anton-Regular.ttf', 84, (255, 255, 255)), ('NUGGETS · 2008', 'BebasNeue-Regular.ttf', 56, (200, 200, 210))], y=760)
        return dict(cam=cam, bg='end', cu=cam.W / 2, cv=cam.p((-10, 0, 0))[1] - 250, zoom=1.2 + .05 * ease(lt / 3), dyn=None, ov=ov, blur=5, dim=.7)
    # ---------- M: los Kings, 22 en todo el cuarto (videomarcador)
    if t < ps(15):
        cam = CAMS['board']; lt = t - ps(14)
        cu, cv = cam.p((0, -9, 47))[:2]
        def dyn(dr, k, off):
            jumbo_text(dr, cam, k, off, [('3RD QUARTER', 110, 100, (250, 190, 50)), ('THOMPSON  37', 290, 150, (255, 255, 255)),
                                         ('KINGS  22', 470, 150, (255, 255, 255))])
        def ov(img, x0, y0, kk):
            tv_label(img, (W1 / 2, 1480), 'THE WHOLE KINGS TEAM: 22', lt - .2, 70)
        return dict(cam=cam, bg='board', cu=cu, cv=cv + 120, zoom=1.2 + .1 * ease(lt / 3), dyn=dyn, ov=ov)
    # ---------- N: final 126-101
    if t < ps(16):
        cam = CAMS['end']; lt = t - ps(15)
        def ov(img, x0, y0, kk):
            big_card(img, t, ps(15) + .05, [('FINAL', 'BebasNeue-Regular.ttf', 80, (255, 214, 120)),
                                           ('126 – 101', 'Anton-Regular.ttf', 170, (255, 255, 255)),
                                           ('WARRIORS WIN', 'BebasNeue-Regular.ttf', 76, (250, 200, 80))], y=430)
        return dict(cam=cam, bg='end', cu=cam.W / 2, cv=cam.p((-10, 0, 0))[1] - 250, zoom=1.2 + .05 * ease(lt / 3), dyn=None, ov=ov, bug=(101, 126, 'FINAL'), blur=5, dim=.7)
    # ---------- O: 52 puntos y sentado los ultimos 9 minutos y medio
    if t < ps(17):
        cam = CAMS['side']; lt = t - ps(16)
        cu, cv = cam.p((0, -12, 3))[:2]
        ts_ = wt(16, 'sat') - .1
        def ov(img, x0, y0, kk):
            big_card(img, t, ps(16) + .05, [('THOMPSON', 'BebasNeue-Regular.ttf', 80, (255, 214, 120)), ('52 POINTS', 'Anton-Regular.ttf', 170, (255, 255, 255))], y=380)
            if t > ts_: tv_label(img, (W1 / 2, 900), 'SAT OUT THE LAST 9½ MINUTES', t - ts_, 70)
        return dict(cam=cam, bg='side', cu=cu, cv=cv - 120, zoom=1.6, dyn=None, ov=ov, blur=4, dim=.75)
    # ---------- P: Steve Kerr, que jugo con Michael Jordan: "I never saw him do that"
    if t < ps(18):
        cam = CAMS['crowd']; lt = t - ps(17)
        cu, cv = cam.p((10, 51, 9))[:2]
        tq = wt(17, 'never') - .15
        def ov(img, x0, y0, kk):
            if t < tq: lower_third(img, ps(17) + .1, t, 'STEVE KERR', "WARRIORS COACH · MICHAEL JORDAN'S EX-TEAMMATE", y=1520)
            if t > wt(17, 'Jordan') - .2 and t < tq:
                tv_label(img, (W1 / 2, 600), 'HIS VERDICT?', t - wt(17, 'verdict') + .1, 90) if t > wt(17, 'verdict') - .1 else None
            if t > tq:
                quote_card(img, t, tq, ['"I NEVER SAW', 'HIM DO THAT."'], 'STEVE KERR', 'ON MICHAEL JORDAN', y=420)
        return dict(cam=cam, bg='crowd', cu=cu, cv=cv - 200, zoom=1.3, dyn=None, ov=ov, blur=4, dim=.6)
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
        render_frame(float(args[1]), subs=False).save('hoops_lore_08_portada.jpg', quality=95); sys.exit()
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
        cmd += (['-an', '-f', 'mp4', os.devnull] if pas == 1 else ['-c:a', 'aac', '-b:a', '96k', '-movflags', '+faststart', 'hoops_lore_08_tiktok.mp4'])
        subprocess.run(cmd, check=True)
    for f_ in ['_tmp_master.mp4', 'segs.txt'] + [f'seg{i}.mp4' for i in range(workers)] + [x for x in os.listdir('.') if x.startswith('_x264')]:
        try: os.remove(f_)
        except OSError: pass
    print('OK hoops_lore_08_tiktok.mp4', os.path.getsize('hoops_lore_08_tiktok.mp4') / 1e6, 'MB')
