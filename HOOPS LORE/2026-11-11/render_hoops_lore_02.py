"""Hoops Lore #02 - Wilt Chamberlain, 100 puntos (2 mar 1962, Hershey Sports Arena).
Render: python3 render_hoops_lore_02.py [--test t1,t2] [--cover t]"""
import json, math, os, sys, subprocess, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import engine as E
import people as PP
from engine import Cam, ease, clamp, lerp, font

E.LANE_HALF = 6.0          # zona de 12 pies (1951-1964)
HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 30; W1, H1 = 1080, 1920; W2, H2 = 2160, 3840
AUDIO = os.path.join(HERE, 'hoops_lore_02_voz.mp3')
LOGO = os.path.join(HERE, 'hoops_lore_logo.png')
HANDLE = '@hoopslore0'
PH = json.load(open(os.path.join(HERE, 'times.json')))
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
        BG[key] = E.render_background(CAMS[key], venue='hershey', occupancy=.5, min_depth=md)
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

# reparto (dorsales genericos salvo Wilt, que llevaba el 13)
WILT = dict(team='PHI', number=13, height=7.08, skin='dark', hair=(18, 14, 12), build=.86)
def wilt(keys): return Actor(keys=keys, **WILT)
PHI_MATES = [dict(team='PHI', number=n, height=h, skin=s, hair=hr) for n, h, s, hr in
             [(11, 6.4, 'light', (60, 44, 30)), (17, 6.2, 'light2', (40, 30, 22)), (24, 6.6, 'brown', (20, 16, 14)), (8, 6.3, 'light', (90, 66, 40))]]
NYK = [dict(team='NYK', number=n, height=h, skin=s, hair=hr) for n, h, s, hr in
       [(18, 6.9, 'light', (70, 50, 30)), (12, 6.4, 'deep', (16, 12, 10)), (6, 6.2, 'light2', (50, 36, 26)), (21, 6.6, 'tan', (30, 22, 18)), (9, 6.3, 'light', (110, 80, 50))]]
def mate(i, keys): return Actor(keys=keys, **PHI_MATES[i])
def knick(i, keys): return Actor(keys=keys, **NYK[i])

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
    d.rectangle([x + 10, y + 10, x + 22, y + 74], fill=(24, 64, 160)); d.text((x + 36, y + 44), 'PHI', font=f, fill='white', anchor='lm')
    d.text((x + 175, y + 44), str(phi), font=fs, fill='white', anchor='mm')
    d.rectangle([x + 232, y + 10, x + 244, y + 74], fill=(240, 128, 36)); d.text((x + 258, y + 44), 'NY', font=f, fill='white', anchor='lm')
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
def draw_table(dr, cam, k, off, dim=1.0, mic=True):
    """mesa de anotadores / prensa en la banda cercana, con microfono de radio de la epoca"""
    def P(X):
        u, v, d = cam.p(X); return ((u - off[0]) * k, (v - off[1]) * k)
    def D(c): return tuple(int(v * dim) for v in c)
    x0, x1, y0, y1, h = -9, 9, -32.5, -30, 2.6
    dr.polygon([P((x0, y0, h)), P((x1, y0, h)), P((x1, y1, h)), P((x0, y1, h))], fill=D((96, 66, 42)))
    dr.polygon([P((x0, y1, 0)), P((x1, y1, 0)), P((x1, y1, h)), P((x0, y1, h))], fill=D((70, 46, 30)))
    # faldon del frente (hacia la pista)
    dr.polygon([P((x0, y1 + .05, .3)), P((x1, y1 + .05, .3)), P((x1, y1 + .05, h - .15)), P((x0, y1 + .05, h - .15))], fill=D((30, 52, 110)))
    for xx in range(-8, 9, 2):
        dr.line([P((xx, y1 + .06, .3)), P((xx, y1 + .06, h - .15))], fill=D((24, 42, 92)), width=2)
    if mic:
        # microfono de cinta sobre soporte de mesa + placa de la emisora (sin logos)
        mx = 1.5
        base = P((mx, -31.2, h)); top = P((mx, -31.2, h + 1.1))
        sc = cam.f * k / max(cam.depth((mx, -31.2, h)), 1)
        dr.line([base, top], fill=D((40, 40, 42)), width=max(2, int(.08 * sc)))
        dr.ellipse([base[0] - .3 * sc, base[1] - .08 * sc, base[0] + .3 * sc, base[1] + .08 * sc], fill=D((30, 30, 32)))
        dr.rounded_rectangle([top[0] - .22 * sc, top[1] - .45 * sc, top[0] + .22 * sc, top[1] + .2 * sc], radius=max(1, .1 * sc), fill=D((150, 150, 156)), outline=D((60, 60, 64)), width=max(1, int(.03 * sc)))
        for i in range(5):
            yy = top[1] - .35 * sc + i * .11 * sc
            dr.line([(top[0] - .16 * sc, yy), (top[0] + .16 * sc, yy)], fill=D((90, 90, 96)), width=max(1, int(.02 * sc)))
        # magnetofono de bobina
        rx, ry = P((-3.5, -31.2, h + .45))
        dr.rectangle([rx - .9 * sc, ry - .2 * sc, rx + .9 * sc, ry + .45 * sc], fill=D((60, 52, 46)))
        for sx in (-.45, .45):
            dr.ellipse([rx + sx * sc - .32 * sc, ry - .55 * sc, rx + sx * sc + .32 * sc, ry + .05 * sc], fill=D((120, 116, 110)), outline=D((30, 28, 26)), width=max(1, int(.03 * sc)))
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
def frame_spec(t):
    S = {}
    # ---------- A: gancho - el mate del 100, y la imagen se pierde
    if t < ps(2):
        cam = CAMS['rim']
        lt = t
        tj = 1.05
        w_ = wilt([(0, (33.0, -5.0)), (tj, (39.6, -1.6)), (3, (39.8, -1.5))])
        d1 = knick(0, [(0, (35, -1)), (tj, (38.8, .8)), (3, (38.6, 1.0))])
        d2 = knick(1, [(0, (30, 5)), (3, (34, 3))])
        m1 = mate(0, [(0, (24, -10)), (3, (27, -9))])
        z = 1.0 + .1 * ease(lt / 2.8)
        cu, cv = cam.p((38.5, -1, 6.5))[:2]
        def dyn(dr, k, off):
            jt = (lt - tj + .35) / .9
            lst = [(d2, None, None), (m1, None, None)]
            lst.append((d1, E.pose_jump(clamp((lt - tj + .2) / .8), 'both', .85) if 0 < (lt - tj + .2) / .8 < 1 else None, math.pi))
            lst.append((w_, pose_dunk(jt) if 0 < jt < 1 else None, 0 if jt > 0 else None))
            E.draw_basket(dr, cam, -1, k=k, off=off); E.draw_basket(dr, cam, 1, k=k, off=off)
            J = draw_actors(dr, cam, lst, lt, k, off)
            # balon: llega en globo y entra
            if lt < tj:
                u = lt / tj; bp = (lerp(26, 40.2, u), lerp(-9, -1.3, u), 7 + 9 * math.sin(math.pi * u * .9))
            elif jt < .55:
                bp = hand_pos(J[id(w_)], 'r')
            else:
                u = min(1, (jt - .55) / .5); bp = (RIM_X, 0, 10.6 - 10 * u * u)
            E.draw_ball(dr, cam, bp, k, off, spin=lt * 5)
            E.draw_basket(dr, cam, 1, k=k, off=off) if 0.55 < jt < .9 else None
        def ov(img, x0, y0, kk):
            pts = 100 if t > tj + .55 else 98
            wilt_tile(img, pts, pulse=max(0, 1 - abs(t - tj - .6) / .3))
            if t > ps(1) - .1:
                a = ease((t - ps(1) + .1) / .5)
                tv_static(img, t, strength=.55 + .45 * a)
                d = ImageDraw.Draw(img, 'RGBA')
                d.rectangle([0, 760, W1, 940], fill=(0, 0, 0, int(200 * a)))
                text_stroke(d, (W1 / 2, 850), 'NO FOOTAGE', font('Anton-Regular.ttf', 130), (255, 255, 255), 8)
        return dict(cam=cam, bg='rim', cu=cu, cv=cv, zoom=z, dyn=dyn, ov=ov, bug=('', '', '4TH QTR', '0:46'))
    # ---------- B: Hershey, plano desde detras de la canasta
    if t < ps(4):
        cam = CAMS['end']; lt = t - ps(2)
        z = 1.2 + .1 * ease(lt / 4)
        players = [mate(i, [(0, (-30 + 9 * i, -14 + 7 * i)), (5, (-22 + 9 * i, -8 + 6 * i))]) for i in range(3)] + \
                  [knick(i, [(0, (10 + 8 * i, 14 - 9 * i)), (5, (16 + 8 * i, 8 - 9 * i))]) for i in range(3)]
        def dyn(dr, k, off):
            E.draw_basket(dr, cam, 1, k=k, off=off)
            draw_actors(dr, cam, [(p, None, None) for p in players], lt, k, off)
            E.draw_basket(dr, cam, -1, k=k, off=off)
        def ov(img, x0, y0, kk):
            lower_third(img, ps(2) + .1, t, 'MARCH 2, 1962', None, t_out=ps(3) - .25)
            lower_third(img, ps(3) - .05, t, 'HERSHEY SPORTS ARENA', 'HERSHEY, PENNSYLVANIA')
        return dict(cam=cam, bg='end', cu=cam.W / 2, cv=cam.p((-10, 0, 0))[1] - 250, zoom=z, dyn=dyn, ov=ov)
    # ---------- C: boveda de hormigon - un pabellon de hockey
    if t < ps(6):
        cam = CAMS['vault']; lt = t - ps(4)
        cu = cam.W / 2 + lerp(-200, 200, ease(lt / 4)); cv = cam.H / 2 + lerp(300, -150, ease(lt / 4))
        def ov(img, x0, y0, kk):
            if t > ps(5): tv_label(img, (W1 / 2, 520), 'BUILT FOR ICE HOCKEY', t - ps(5) - .3)
            if t > wt(5, 'chocolate') - .1: tv_label(img, (W1 / 2, 640), 'IN "CHOCOLATE TOWN"', t - wt(5, 'chocolate') + .1, 54)
        return dict(cam=cam, bg='vault', cu=cu, cv=cv, zoom=1.05, dyn=None, ov=ov)
    # ---------- D: Warriors contra Knicks
    if t < ps(7):
        cam = CAMS['side']; lt = t - ps(6)
        phi = [wilt([(0, (-34, 10)), (2.4, (-3.5, 0))])] + [mate(i, [(0, (-40 + 3 * i, -16 + 7 * i)), (2.4, (-12 + 2 * i, -14 + 8 * i))]) for i in range(4)]
        ny = [knick(i, [(0, (40 - 3 * i, 16 - 8 * i)), (2.4, (3.5 + 6 * i if i == 0 else 12 - 2 * i, 0 if i == 0 else 14 - 8 * i))]) for i in range(5)]
        cx = lerp(-12, 0, ease(lt / 2.4))
        cu, cv = cam.p((cx, 0, 3))[:2]
        def dyn(dr, k, off):
            for s_ in (-1, 1): E.draw_basket(dr, cam, s_, k=k, off=off)
            draw_actors(dr, cam, [(p, None, (0 if p.team == 'PHI' else math.pi) if lt > 2.4 else None) for p in phi + ny], lt, k, off)
        def ov(img, x0, y0, kk):
            lower_third(img, ps(6) + .1, t, 'PHILADELPHIA WARRIORS', 'VS NEW YORK KNICKS')
        return dict(cam=cam, bg='side', cu=cu, cv=cv - 120, zoom=2.1, dyn=dyn, ov=ov, bug=(0, 0, '1ST QTR'))
    # ---------- E: 4.124 aficionados en un pabellon de mas de 8.000
    if t < ps(8):
        cam = CAMS['crowd']; lt = t - ps(7)
        cu = cam.W / 2 + lerp(-300, 300, ease(lt / 3.4)); cv = cam.H / 2
        def ov(img, x0, y0, kk):
            n = int(4124 * ease((lt - .1) / 2.0))
            big_card(img, t, ps(7), [('ATTENDANCE', 'BebasNeue-Regular.ttf', 64, (255, 214, 120)),
                                     (f'{n:,}', 'Anton-Regular.ttf', 130, (255, 255, 255)),
                                     ('ARENA CAPACITY: 8,000+', 'BebasNeue-Regular.ttf', 52, (200, 200, 200))], y=520)
        return dict(cam=cam, bg='crowd', cu=cu, cv=cv, zoom=1.0, dyn=None, ov=ov, bug=(0, 0, '1ST QTR'))
    # ---------- F: ni una camara de TV - en la mesa solo hay un microfono de radio
    if t < ps(9):
        cam = CAMS['table']; lt = t - ps(8)
        cu, cv = cam.p((0, -31, 3.4))[:2]
        def dyn(dr, k, off):
            draw_table(dr, cam, k, off)
        def ov(img, x0, y0, kk):
            tv_label(img, (W1 / 2, 560), 'NO TELEVISION CAMERAS', lt)
            if lt > .45: tv_label(img, (W1 / 2, 680), 'ONLY A RADIO MICROPHONE', lt - .45, 56)
        return dict(cam=cam, bg='table', cu=cu, cv=cv + 150, zoom=1.0, dyn=dyn, ov=ov, bug=(0, 0, '1ST QTR'))
    # ---------- G: Wilt anota 100 - jugada en la cancha (gancho en suspension a tabla)
    if t < ps(12):
        cam = CAMS['side']; lt = t - ps(9)
        tshot = 2.2
        w_ = wilt([(0, (18, 8)), (tshot - .4, (33, 3)), (tshot + 2, (32, 3)), (4, (20, 0)), (7, (10, -4))])
        d1 = knick(0, [(0, (21, 6)), (tshot - .4, (35.5, 2)), (7, (14, -2))])
        others = [mate(1, [(0, (8, -10)), (7, (14, -8))]), knick(1, [(0, (12, -6)), (7, (16, -4))]), mate(2, [(0, (24, 14)), (7, (26, 12))])]
        bx = w_.pos(lt)[0]
        cu, cv = cam.p((clamp(bx, 6, 30), 0, 4))[:2]
        def dyn(dr, k, off):
            jt = (lt - tshot) / .9
            lst = [(o, None, None) for o in others] + [(d1, E.pose_jump(clamp(jt + .1), 'both', .9) if 0 < jt + .1 < 1 else None, math.pi if jt > -1 else None)]
            lst.append((w_, E.pose_jump(jt, 'one', 1.0) if 0 < jt < 1 else None, 0 if jt > -.3 and jt < 1.5 else None))
            for s_ in (-1, 1): E.draw_basket(dr, cam, s_, k=k, off=off)
            J = draw_actors(dr, cam, lst, lt, k, off)
            x, y = w_.pos(lt)
            if jt < 0: bp = (x + .9, y - .9, .5 + 2.6 * abs(math.sin(lt * 5.5)))
            elif jt < .5: bp = hand_pos(J[id(w_)], 'r')
            elif jt < 1.1:
                u = (jt - .5) / .6; hp = hand_pos(J[id(w_)], 'r') if jt < .52 else (x + .5, y, 11.5)
                bp = (lerp(x + .6, RIM_X, u), lerp(y, 0, u), 11 + 2.2 * math.sin(math.pi * u) - .8 * u)
            else:
                u = min(1, (jt - 1.1) / .5); bp = (RIM_X, 0, 10.2 - 9 * u)
            E.draw_ball(dr, cam, bp, k, off, spin=lt * 5)
        def ov(img, x0, y0, kk):
            lower_third(img, ps(9) + .2, t, 'WILT CHAMBERLAIN', "PHILADELPHIA WARRIORS · 7'1\"", t_out=ps(10) - .2)
            # contador grande de 0 a 100
            u = ease((t - ps(9) - .3) / (ps(10) - ps(9) - .1))
            pts = int(100 * u)
            d = ImageDraw.Draw(img)
            if t > ps(10) - .2:
                s = 1 + .1 * max(0, 1 - abs(t - ps(10)) / .3)
                text_stroke(d, (W1 / 2, 640), '100', font('Anton-Regular.ttf', int(300 * s)), YEL, 12)
                text_stroke(d, (W1 / 2, 820), 'POINTS', font('BebasNeue-Regular.ttf', 90), (255, 255, 255), 6)
            if t > ps(11) - .1:
                tv_label(img, (W1 / 2, 940), 'ONE PLAYER', t - ps(11) + .1, 70)
            wilt_tile(img, pts)
        return dict(cam=cam, bg='side', cu=cu, cv=cv - 100, zoom=2.3, dyn=dyn, ov=ov, bug=None)
    # ---------- H: tiros libres por debajo: 28 de 32
    if t < ps(14):
        cam = CAMS['ft']; lt = t - ps(12)
        w_ = wilt([(0, (-RIM_X + 15, 0))])
        refp = Actor(keys=[(0, (-30.5, 9.5))], team=None, number=None, height=6.0, skin='light', ref=True)
        lane = [mate(1, [(0, (-38, 6.7))]), knick(0, [(0, (-35, 6.7))]), knick(1, [(0, (-38, -6.7))]), mate(2, [(0, (-35, -6.7))])]
        shots = [.3, 2.2, 4.0]
        cu, cv = cam.p((-31, 0, 5))[:2]
        def dyn(dr, k, off):
            st = None
            for s0 in shots:
                if s0 <= lt < s0 + 1.4: st = s0
            pose = pose_underhand((lt - st) / 1.0) if st is not None else E.pose_stand()
            E.draw_basket(dr, cam, 1, k=k, off=off)
            lst = [(p, E.pose_stand(), 0 if p.pos(0)[1] > 0 else 0) for p in lane]
            lst.append((refp, E.pose_stand(), math.pi / 2))
            lst.append((w_, pose, math.pi))
            J = draw_actors(dr, cam, lst, lt, k, off)
            if st is not None:
                u = (lt - st) / 1.0
                if u < .72:
                    hl = hand_pos(J[id(w_)], 'l'); hr = hand_pos(J[id(w_)], 'r')
                    bp = tuple((hl[i] + hr[i]) / 2 for i in range(3)); bp = (bp[0] - .35, bp[1], bp[2])
                else:
                    v = min(1, (u - .72) / .55); x0_ = -RIM_X + 14.2
                    bp = (lerp(x0_, -RIM_X, v), 0, lerp(5.6, 10.3, v) + 5 * math.sin(math.pi * v))
                    if v >= 1: bp = (-RIM_X, 0, 10.3 - 9 * min(1, (u - 1.27) / .3))
            else:
                bp = (-RIM_X + 14.6, -.5, 3.2)
            E.draw_ball(dr, cam, bp, k, off, spin=lt * 3)
            E.draw_basket(dr, cam, -1, k=k, off=off)
        def ov(img, x0, y0, kk):
            if t > ps(12) + .3: tv_label(img, (W1 / 2, 470), 'SHOT HIS FREE THROWS UNDERHANDED', t - ps(12) - .3, 58)
            a = ease((t - wt(13, 'twenty')) / .3)
            if a > 0:
                d = ImageDraw.Draw(img, 'RGBA'); y = 560
                d.rounded_rectangle([210, y, W1 - 210, y + 210], radius=16, fill=(12, 14, 22, int(230 * a)), outline=(24, 64, 160, int(255 * a)), width=6)
                d.text((W1 / 2, y + 50), 'FREE THROWS', font=font('BebasNeue-Regular.ttf', 60), fill=(255, 255, 255, int(255 * a)), anchor='mm')
                d.text((W1 / 2, y + 140), '28 / 32', font=font('Anton-Regular.ttf', 110), fill=(255, 221, 0, int(255 * a)), anchor='mm')
        return dict(cam=cam, bg='ft', cu=cam.p((-28, 0, 5))[0], cv=cv + 60, zoom=1.35, dyn=dyn, ov=ov, bug=(None, None, '', '') if False else None)
    # ---------- I: "Give it to Wilt!"
    if t < ps(16):
        cam = CAMS['crowd']; lt = t - ps(14)
        cu, cv = cam.p((10, 51, 9))[:2]; cu += 60 * math.sin(lt * .8)
        fans = [Actor(keys=[(0, (-6 + i * 4.2, 49.5 + (i % 2) * 2.4))], height=5.8 + (i % 3) * .15, skin=random.Random(i).choice(['light', 'light2', 'tan', 'brown']),
                      fan=(random.Random(i * 3).choice([(60, 52, 46), (40, 44, 58), (92, 76, 58), (70, 70, 74), (120, 100, 80)]), (46, 44, 48),
                           (44, 38, 34) if i % 3 == 0 else None)) for i in range(9)]
        def dyn(dr, k, off):
            lst = [(f, pose_cheer(lt * 6 + i) if lt > (ps(15) - ps(14) - .4) or i % 2 == 0 else E.pose_stand(), -math.pi / 2 - .3) for i, f in enumerate(fans)]
            # estan de pie sobre las gradas: elevacion de la fila
            for f, pose, face in lst:
                pose = dict(pose); pose['lift'] = pose.get('lift', 0) + 4.0 + 1.85 * (1 if f.pos(0)[1] > 50 else 0)
                x, y = f.pos(lt)
                PP.draw_fan62(dr, cam, x, y, face, pose, coat=f.fan[0], trousers=f.fan[1], hat=f.fan[2], skin=f.skin, k=k, off=off, height=f.height)
        def ov(img, x0, y0, kk):
            if t > ps(15) - .1:
                d = ImageDraw.Draw(img)
                sh = 6 * math.sin(t * 40)
                text_stroke(d, (W1 / 2 + sh, 620), '"GIVE IT', font('Anton-Regular.ttf', 150), (255, 255, 255), 10)
                text_stroke(d, (W1 / 2 - sh, 800), 'TO WILT!"', font('Anton-Regular.ttf', 150), YEL, 10)
            wilt_tile(img, 69 + int(29 * ease((t - ps(14)) / (ps(16) - ps(14)))))
        return dict(cam=cam, bg='crowd', cu=cu, cv=cv - 200, zoom=1.35, dyn=dyn, ov=ov, bug=(125, 106, '4TH QTR'))
    # ---------- J: quedan 46 segundos - el punto 100
    if t < ps(17):
        cam = CAMS['rim']; lt = t - ps(16)
        tj = 2.0
        w_ = wilt([(0, (30, -7)), (tj, (39.6, -1.6)), (4, (39.8, -1.5))])
        d1 = knick(0, [(0, (33, -3)), (tj, (38.8, .8)), (4, (38.6, 1.0))])
        d2 = knick(3, [(0, (27, 6)), (4, (33, 3))])
        m1 = mate(3, [(0, (16, -12)), (4, (22, -10))])
        z = 1.0 + .1 * ease(lt / 3.5)
        cu, cv = cam.p((37.5, -1, 6.5))[:2]
        def dyn(dr, k, off):
            jt = (lt - tj + .35) / .9
            lst = [(d2, None, None), (m1, E.pose_stand() if lt > .9 else None, 0)]
            dj = (lt - tj + .2) / .8
            lst.append((d1, E.pose_jump(clamp(dj), 'both', .85) if 0 < dj < 1 else None, math.pi))
            lst.append((w_, pose_dunk(jt) if 0 < jt < 1 else None, 0 if jt > 0 else None))
            E.draw_basket(dr, cam, -1, k=k, off=off); E.draw_basket(dr, cam, 1, k=k, off=off)
            J = draw_actors(dr, cam, lst, lt, k, off)
            if lt < .9: bp = hand_pos(J[id(m1)], 'r') if False else (m1.pos(lt)[0] + .8, m1.pos(lt)[1] - .4, 4 + 1.5 * abs(math.sin(lt * 5)))
            elif lt < tj:
                u = (lt - .9) / (tj - .9); mp = m1.pos(lt)
                bp = (lerp(mp[0] + .8, 40.2, u), lerp(mp[1], -1.3, u), 6 + 9 * math.sin(math.pi * u * .9) + 4 * u)
            elif jt < .55: bp = hand_pos(J[id(w_)], 'r')
            else:
                u = min(1, (jt - .55) / .5); bp = (RIM_X, 0, 10.6 - 10 * u * u)
            E.draw_ball(dr, cam, bp, k, off, spin=lt * 5)
        made = lt > tj + .55
        def ov(img, x0, y0, kk):
            wilt_tile(img, 100 if made else 98, pulse=max(0, 1 - abs(lt - tj - .6) / .3))
            if made:
                d = ImageDraw.Draw(img)
                s = 1 + .15 * max(0, 1 - (lt - tj - .55) / .3)
                text_stroke(d, (W1 / 2, 700), '100', font('Anton-Regular.ttf', int(280 * s)), YEL, 12)
        return dict(cam=cam, bg='rim', cu=cu, cv=cv, zoom=z, dyn=dyn, ov=ov, bug=('', '', '4TH QTR', '0:46'))
    # ---------- K: el publico invade la pista
    if t < ps(18):
        cam = CAMS['side']; lt = t - ps(17)
        w_ = wilt([(0, (36, -2))])
        rng = random.Random(5)
        fans = []
        for i in range(26):
            sx = rng.uniform(-10, 46); sy = rng.choice([-44, 46]) + rng.uniform(-2, 2)
            tx = 36 + rng.uniform(-7, 7); ty = rng.uniform(-7, 7)
            t0 = rng.uniform(0, .9)
            fans.append(Actor(keys=[(0, (sx, sy)), (t0, (sx, sy)), (t0 + 2.2, (tx, ty)), (9, (tx + rng.uniform(-1, 1), ty))], height=rng.uniform(5.5, 6.1),
                              skin=rng.choice(['light', 'light2', 'tan', 'brown', 'light']),
                              fan=(rng.choice([(60, 52, 46), (40, 44, 58), (92, 76, 58), (70, 70, 74), (130, 110, 86), (34, 34, 38)]), rng.choice([(46, 44, 48), (60, 56, 50), (30, 30, 34)]),
                                   rng.choice([None, None, (44, 38, 34), (70, 62, 54)]))))
        mates = [mate(i, [(0, (30 + 3 * i, -6 + 4 * i))]) for i in range(3)]
        bx = 30
        cu, cv = cam.p((bx, 0, 4))[:2]
        def dyn(dr, k, off):
            E.draw_basket(dr, cam, 1, k=k, off=off)
            lst = [(f, None, None) for f in fans] + [(m, E.pose_stand(), math.pi) for m in mates] + [(w_, pose_cheer(lt * 3), -math.pi / 2)]
            draw_actors(dr, cam, lst, lt, k, off)
        def ov(img, x0, y0, kk):
            tv_label(img, (W1 / 2, 520), 'GAME STOPPED', t - wt(17, 'stop') + .1)
            wilt_tile(img, 100)
        return dict(cam=cam, bg='side', cu=cu, cv=cv - 160, zoom=1.6, dyn=dyn, ov=ov, bug=('', '', '4TH QTR', '0:46'))
    # ---------- L: resultado final
    if t < ps(20):
        cam = CAMS['end']; lt = t - ps(18)
        def ov(img, x0, y0, kk):
            big_card(img, t, ps(18) + .1, [('FINAL', 'BebasNeue-Regular.ttf', 80, (255, 214, 120)),
                                          ('169 – 147', 'Anton-Regular.ttf', 170, (255, 255, 255)),
                                          ('WARRIORS  ·  KNICKS', 'BebasNeue-Regular.ttf', 66, (190, 200, 230)),
                                          ('WILT: 100 PTS', 'Anton-Regular.ttf', 90, YEL)], y=430)
        return dict(cam=cam, bg='end', cu=cam.W / 2, cv=cam.p((-10, 0, 0))[1] - 250, zoom=1.2 + .05 * ease(lt / 3), dyn=None, ov=ov, bug=(169, 147, 'FINAL'), blur=5, dim=.7)
    # ---------- M: la radio - solo sobrevivio el audio
    if t < ps(22):
        cam = CAMS['table']; lt = t - ps(20)
        cu, cv = cam.p((0, -31, 3.4))[:2]
        def dyn(dr, k, off):
            draw_table(dr, cam, k, off)
        def ov(img, x0, y0, kk):
            if t > ps(21) - .1:
                d = ImageDraw.Draw(img, 'RGBA')
                y = 520; d.rounded_rectangle([120, y - 90, W1 - 120, y + 150], radius=18, fill=(12, 14, 22, 220))
                d.text((W1 / 2, y - 45), 'RADIO BROADCAST', font=font('BebasNeue-Regular.ttf', 62), fill=(255, 214, 120), anchor='mm')
                rng = np.random.default_rng(int(t * 30))
                for i in range(56):
                    x = 160 + i * 14.5
                    h = 10 + 70 * abs(math.sin(i * .7 + t * 9)) * rng.uniform(.4, 1)
                    d.rectangle([x, y + 55 - h / 2, x + 8, y + 55 + h / 2], fill=(255, 221, 0, 230))
                if t > wt(21, 'part') - .1:
                    tv_label(img, (W1 / 2, 760), 'ONLY PART OF IT SURVIVED', t - wt(21, 'part') + .1, 58)
        return dict(cam=cam, bg='table', cu=cu, cv=cv + 150, zoom=1.0 + .1 * ease(lt / 5), dyn=dyn, ov=ov, bug=None)
    # ---------- N: la foto del "100" en el vestuario (recreacion, sin cara real)
    if t < ps(24):
        lt = t - ps(22)
        return dict(photo=True, lt=lt)
    # ---------- O: no existe video - el record sigue en pie
    if t < ps(26) + .2:
        cam = CAMS['table']; lt = t - ps(24)
        dim = 1 - .55 * ease(lt / 1.5)
        cu, cv = cam.p((0, -31, 3.4))[:2]
        def dyn(dr, k, off):
            draw_table(dr, cam, k, off, dim=dim, mic=False)
        def ov(img, x0, y0, kk):
            T_ = P2F(cam, (0, -31.2, 4.6), x0, y0, kk)
            draw_tv(img, W1 / 2, 720, 640, t, 'static')
            d = ImageDraw.Draw(img, 'RGBA')
            d.rectangle([0, 1040, W1, 1150], fill=(0, 0, 0, 210))
            text_stroke(d, (W1 / 2, 1095), 'NO VIDEO EXISTS', font('Anton-Regular.ttf', 92), (255, 255, 255), 6)
            if t > ps(25) + .2:
                tv_label(img, (W1 / 2, 330), 'RECORD: STILL STANDING', t - ps(25) - .2, 66)
        return dict(cam=cam, bg='table', cu=cu, cv=cv + 150, zoom=1.0, dyn=dyn, ov=ov, bug=None, dim=dim)
    return dict(close=True)

# ------------------------------------------------------------------ foto del "100"
PHOTO = None
def photo_print():
    """recreacion en blanco y negro: jugador generico (#13, sin rasgos reales) sujetando un folio con '100'"""
    global PHOTO
    if PHOTO is not None: return PHOTO
    cam = Cam((0, -6.2, 5.6), (0, 0, 5.3), 1900, 1400, 1700)
    img = Image.new('RGB', (1400, 1700), (150, 146, 138))
    d = ImageDraw.Draw(img)
    for y in range(0, 1700, 70):
        for x in range(0 if (y // 70) % 2 == 0 else -50, 1400, 100):
            d.rectangle([x + 3, y + 3, x + 97, y + 67], fill=(176, 172, 164))
    for i in range(6):
        x = 40 + i * 230
        d.rectangle([x, 380, x + 210, 1700], fill=(118, 116, 112), outline=(70, 68, 66), width=6)
        for j in range(5): d.line([(x + 40, 440 + j * 22), (x + 170, 440 + j * 22)], fill=(80, 78, 74), width=6)
    # sujeta el folio a la altura del pecho
    pose = dict(lh=.02, lk=.05, rh=-.02, rk=.05, ls=.3, le=1.3, la=0.0, rs=.3, re=1.3, ra=0.0, lift=0, lean=0)
    J = PP.draw_player62(d, cam, 0, 0, -math.pi / 2, pose, 'PHI', None, 7.08, 'dark', (18, 14, 12), build=.86)
    hl = cam.p(hand_pos(J, 'l')); hr = cam.p(hand_pos(J, 'r'))
    cx = (hl[0] + hr[0]) / 2; cy = (hl[1] + hr[1]) / 2 - 20
    pw, ph = max(380, abs(hr[0] - hl[0]) + 60), 300
    d.polygon([(cx - pw / 2, cy - ph / 2 - 10), (cx + pw / 2, cy - ph / 2 + 6), (cx + pw / 2 - 6, cy + ph / 2), (cx - pw / 2 + 4, cy + ph / 2 - 8)], fill=(246, 244, 238))
    f = font('Graduate-Regular.ttf', 200)
    d.text((cx, cy), '100', font=f, fill=(30, 30, 30), anchor='mm')
    for hp, sx in ((hl, -1 if hl[0] < hr[0] else 1), (hr, 1 if hl[0] < hr[0] else -1)):
        hx = hp[0]
        d.ellipse([hx - 40, cy - 30, hx + 40, cy + 60], fill=PP.SKINS['dark'])
        for k_ in range(4):
            d.ellipse([hx - sx * 30 - 14, cy - 40 + k_ * 22, hx - sx * 30 + 14, cy - 18 + k_ * 22], fill=PP.SKINS['dark'])
    g = img.convert('L').filter(ImageFilter.GaussianBlur(1.2))
    arr = np.asarray(g).astype(np.float32)
    arr = (arr - 128) * 1.15 + 128 + np.random.default_rng(3).normal(0, 9, arr.shape)
    g = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert('RGB')
    framed = Image.new('RGB', (g.width + 80, g.height + 200), (238, 234, 222))
    framed.paste(g, (40, 40))
    PHOTO = framed
    return PHOTO

def photo_frame(t, lt):
    bg = get_bg('table'); cam = CAMS['table']
    cu, cv = cam.p((0, -31, 3.4))[:2]
    z = 1.0; cw, ch = W2 / z, H2 / z
    x0 = clamp(cu - cw / 2, 0, bg.width - cw); y0 = clamp(cv + 150 - ch / 2, 0, bg.height - ch)
    base = bg.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W1, H1), Image.BILINEAR).filter(ImageFilter.GaussianBlur(10))
    base = Image.eval(base, lambda v: int(v * .35))
    img = base
    p = photo_print()
    a = ease(lt / .5)
    s = lerp(.55, .66, ease(lt / 6))
    pi = p.resize((int(p.width * s), int(p.height * s)), Image.LANCZOS).rotate(-3 + 2 * a, expand=True, resample=Image.BICUBIC, fillcolor=(0, 0, 0))
    m = Image.new('L', p.size, 255).resize(pi.size if False else (int(p.width * s), int(p.height * s))).rotate(-3 + 2 * a, expand=True)
    x = W1 // 2 - pi.width // 2; y = int(lerp(H1, 330, a))
    shadow = Image.new('RGB', pi.size, (0, 0, 0))
    img.paste(shadow, (x + 20, y + 26), m.point(lambda v: v // 2))
    img.paste(pi, (x, y), m)
    # destello de flash al empezar
    if lt < .25:
        img = Image.blend(img, Image.new('RGB', img.size, (255, 255, 255)), 1 - lt / .25)
    img = finish(img, t)
    d = ImageDraw.Draw(img)
    if lt > .6: tv_label(img, (W1 / 2, 230), 'THE LOCKER ROOM PHOTO', lt - .6, 60)
    lower_third(img, ps(22) + .8, t, 'RECREATION', 'NOT THE ORIGINAL PHOTO', y=1700)
    return img

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
    t0 = ps(26)
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
    a2 = ease((t - wt(27, 'tomorrow')) / .3)
    if a2 > 0:
        text_stroke(d, (W1 / 2, 1010), "TOMORROW'S STORY?", font('Anton-Regular.ttf', int(110 * (.85 + .15 * a2))), (255, 255, 255), 8)
    a3 = ease((t - wt(28, 'vote')) / .3)
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
    if sp.get('photo'):
        img = photo_frame(t, sp['lt'])
        if subs: draw_subs(img, t)
        watermark(img); return img
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
        render_frame(float(args[1]), subs=False).save('hoops_lore_02_portada.jpg', quality=95); sys.exit()
    workers = int(os.environ.get('WORKERS', '4'))
    from multiprocessing import Process
    bounds = [NFR * i // workers for i in range(workers + 1)]
    procs = [Process(target=render_range, args=(bounds[i], bounds[i + 1], f'seg{i}.mp4')) for i in range(workers)]
    for p in procs: p.start()
    for p in procs: p.join()
    open('segs.txt', 'w').write(''.join(f"file 'seg{i}.mp4'\n" for i in range(workers)))
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', 'segs.txt', '-i', AUDIO, '-map', '0:v', '-map', '1:a',
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', 'hoops_lore_02.mp4'], check=True)
    print('OK hoops_lore_02.mp4')
