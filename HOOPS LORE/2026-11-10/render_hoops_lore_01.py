"""Hoops Lore #01 - "In the very first NBA game, you got in for free if you were taller than this guy."
Render: python3 render_hoops_lore_01.py [--test t1,t2,...] [--workers N]
Lee los tiempos de times.json (frases y palabras alineadas con la voz)."""
import json, math, os, sys, subprocess, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import engine as E
from engine import Cam, ease, clamp, lerp, font

HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 30; W1, H1 = 1080, 1920; W2, H2 = 2160, 3840
AUDIO = os.path.join(HERE, 'hoops_lore_01_voz.mp3')
LOGO = os.path.join(HERE, 'hoops_lore_logo.png')
HANDLE = '@hoopslore0'
PH = json.load(open(os.path.join(HERE, 'times.json')))
DUR = 75.47
NFR = int(DUR * FPS)

def ps(i): return PH[i]['start']
def pe(i): return PH[i]['end']
def wt(i, word):
    """inicio de la primera palabra de la frase i que contiene `word`"""
    for w in PH[i]['words']:
        if word.lower() in w['w'].lower(): return w['s']
    return ps(i)

YEL = (255, 221, 0); TELE = (255, 236, 80)

# ------------------------------------------------------------------ fondos
BG = {}
def sign_extra(img, cam, dim):
    """cartel colgado sobre la grada del fondo con los precios"""
    tw, th = 1400, 520
    t = Image.new('RGB', (tw, th), (32, 44, 78))
    d = ImageDraw.Draw(t)
    d.rectangle([14, 14, tw - 14, th - 14], outline=(230, 210, 150), width=10)
    d.text((tw / 2, 120), 'ADMISSION', font=font('Graduate-Regular.ttf', 120), fill=(236, 232, 220), anchor='mm')
    d.text((tw / 2, 330), '75¢  —  $2.50', font=font('Anton-Regular.ttf', 220), fill=(255, 214, 90), anchor='mm')
    d.text((tw / 2, 460), 'BASKETBALL TONIGHT', font=font('BebasNeue-Regular.ttf', 70), fill=(236, 232, 220), anchor='mm')
    t = t.point(lambda v: int(v * dim))
    corners = [(70, 14, 48), (70, -14, 48), (70, -14, 37.5), (70, 14, 37.5)]   # TL TR BR BL (mirando hacia -x)
    pp = [cam.p(P) for P in corners]
    if min(q[2] for q in pp) < 2: return
    # cables
    dr = ImageDraw.Draw(img)
    for yy in (-10, 10):
        E.line3(dr, cam, (70, yy, 48), (70, yy, 80), (60, 58, 54), .12)
    mask = Image.new('L', img.size, 0); ImageDraw.Draw(mask).polygon([q[:2] for q in pp], fill=255)
    coeffs = find_coeffs([q[:2] for q in pp], [(0, 0), (tw, 0), (tw, th), (0, th)])
    warped = t.transform(img.size, Image.PERSPECTIVE, coeffs, Image.BICUBIC)
    img.paste(warped, (0, 0), mask)

def boards_banner_extra(img, cam, dim):
    """rotulo pintado en la valla lejana"""
    tw, th = 3000, 150
    t = Image.new('RGB', (tw, th), (236, 234, 226)); d = ImageDraw.Draw(t)
    d.text((tw / 2, th / 2 + 4), 'BASKETBALL  ASSOCIATION  OF  AMERICA', font=font('Graduate-Regular.ttf', 108), fill=(28, 52, 120), anchor='mm')
    t = t.point(lambda v: int(v * dim))
    y = E.RINK_Y - .02
    corners = [(-34, y, 3.1), (34, y, 3.1), (34, y, .85), (-34, y, .85)]
    pp = [cam.p(P) for P in corners]
    if min(q[2] for q in pp) < 2: return
    mask = Image.new('L', img.size, 0); ImageDraw.Draw(mask).polygon([q[:2] for q in pp], fill=255)
    coeffs = find_coeffs([q[:2] for q in pp], [(0, 0), (tw, 0), (tw, th), (0, th)])
    img.paste(t.transform(img.size, Image.PERSPECTIVE, coeffs, Image.BICUBIC), (0, 0), mask)

def find_coeffs(pa, pb):
    """coeficientes para Image.PERSPECTIVE: mapea destino pa -> origen pb"""
    M = []
    for (x, y), (X, Y) in zip(pa, pb):
        M.append([x, y, 1, 0, 0, 0, -X * x, -X * y]); M.append([0, 0, 0, x, y, 1, -Y * x, -Y * y])
    A = np.array(M, float); B = np.array(pb, float).reshape(8)
    return np.linalg.solve(A, B).tolist()

def cams():
    return {
        'side': Cam((0, -78, 30), (0, 6, 3), 1730 * 2, 3600 * 2, H2),
        'tight': Cam((0, -52, 11), (0, -10, 4.6), 2150 * 2, 5600 * 2, H2),
        'end': Cam((-76, 0, 30), (-18, 0, 0), 1450 * 2, 1300 * 2, H2, oy=-260),
        'sign': Cam((-76, 0, 30), (70, 0, 40), 3600 * 2, 1300 * 2, H2),
        'crowd': Cam((-10, -40, 9), (25, 60, 34), 1500 * 2, 1500 * 2, H2),
    }
CAMS = cams()

def get_bg(key):
    if key not in BG:
        cam = CAMS[key]
        ex = [boards_banner_extra] if key in ('side', 'tight') else []
        if key in ('end', 'sign', 'crowd'): ex.append(sign_extra)
        BG[key] = E.render_background(cam, extras=ex, min_depth=(10 if key in ('tight', 'crowd') else 45))
        if key == 'tight':  # la grada cercana queda fuera, nos aseguramos
            pass
    return BG[key]

# ------------------------------------------------------------------ actores
class Actor:
    def __init__(self, team=None, number=None, height=6.4, keys=None, skin=None, hair=None, civilian=None, ref=False, seed=0):
        rng = random.Random(seed)
        self.team, self.number, self.height = team, number, height
        self.keys = keys or [(0, (0, 0))]
        self.skin = skin or rng.choice(E.SKIN)
        self.hair = hair or rng.choice([(54, 40, 28), (30, 24, 20), (96, 70, 40), (70, 52, 34)])
        self.civilian = civilian; self.ref = ref; self.face0 = None
    def pos(self, t):
        ks = self.keys
        if t <= ks[0][0]: return ks[0][1]
        for (t0, p0), (t1, p1) in zip(ks, ks[1:]):
            if t <= t1:
                u = ease((t - t0) / max(t1 - t0, 1e-6)) if len(ks) == 2 else (t - t0) / max(t1 - t0, 1e-6)
                return (lerp(p0[0], p1[0], u), lerp(p0[1], p1[1], u))
        return ks[-1][1]
    def vel(self, t):
        a = self.pos(t - .05); b = self.pos(t + .05)
        return ((b[0] - a[0]) / .1, (b[1] - a[1]) / .1)
    def dist(self, t):
        # distancia recorrida (para la fase de carrera)
        n = max(2, int(t * 10)); d = 0; prev = self.pos(0)
        for i in range(1, n + 1):
            p = self.pos(t * i / n); d += math.hypot(p[0] - prev[0], p[1] - prev[1]); prev = p
        return d

def auto_pose(a, t, face_default):
    v = a.vel(t); sp = math.hypot(*v)
    if sp > .6:
        face = math.atan2(v[1], v[0])
        ph = a.dist(t) / 2.6 * math.pi
        return face, E.pose_run(ph, clamp(sp / 18, .35, 1.0))
    return face_default, E.pose_stand()

def draw_actor(dr, cam, a, t, k, off, pose=None, face=None, dim=1.0):
    x, y = a.pos(t)
    f0, p0 = auto_pose(a, t, face if face is not None else -math.pi / 2)
    if pose is not None: p0 = pose
    if face is not None and pose is not None: f0 = face
    E.shadow(dr, cam, x, y, 1.1, k, off)
    return E.draw_player(dr, cam, x, y, f0, p0, a.team, a.number, a.height, a.skin, a.hair, k, off, a.civilian, dim, a.ref)

def draw_actors(dr, cam, lst, t, k, off, dim=1.0):
    """lst: (actor, pose|None, face|None)  -> se ordenan por profundidad"""
    items = []
    for a, pose, face in lst:
        x, y = a.pos(t); items.append((cam.depth((x, y, 3)), a, pose, face))
    items.sort(key=lambda q: -q[0])
    out = {}
    for _, a, pose, face in items:
        out[id(a)] = draw_actor(dr, cam, a, t, k, off, pose, face, dim)
    return out

def P2F(cam, P, x0, y0, z):
    """3D -> coordenadas del fotograma final (1x)"""
    u, v, d = cam.p(P); return ((u - x0) * z / 2, (v - y0) * z / 2)

# ------------------------------------------------------------------ graficos 1x
def text_stroke(d, xy, s, f, fill, sw=6, sf=(0, 0, 0), anchor='mm'):
    d.text(xy, s, font=f, fill=fill, anchor=anchor, stroke_width=sw, stroke_fill=sf)

def tele_arrow(img, A, B, t, label=None, lab_pos=None):
    """flecha de telestrator con trazo que se dibuja (t 0..1)"""
    t = clamp(t)
    if t <= 0: return
    d = ImageDraw.Draw(img)
    n = 24; pts = []
    mx, my = (A[0] + B[0]) / 2, (A[1] + B[1]) / 2
    nx, ny = -(B[1] - A[1]) * .15, (B[0] - A[0]) * .15
    for i in range(int(n * t) + 1):
        u = i / n
        x = (1 - u) ** 2 * A[0] + 2 * (1 - u) * u * (mx + nx) + u * u * B[0]
        y = (1 - u) ** 2 * A[1] + 2 * (1 - u) * u * (my + ny) + u * u * B[1]
        pts.append((x, y))
    if len(pts) > 1:
        d.line(pts, fill=(0, 0, 0), width=17, joint='curve'); d.line(pts, fill=TELE, width=10, joint='curve')
    if t >= 1:
        x1, y1 = pts[-1]; x0, y0 = pts[-3]
        ang = math.atan2(y1 - y0, x1 - x0)
        for da in (2.6, -2.6):
            q = (x1 + 46 * math.cos(ang + da), y1 + 46 * math.sin(ang + da))
            d.line([q, (x1, y1)], fill=(0, 0, 0), width=17); d.line([q, (x1, y1)], fill=TELE, width=10)
    if label and t > .3:
        f = font('BebasNeue-Regular.ttf', 74)
        text_stroke(d, lab_pos or (A[0], A[1] - 50), label, f, TELE, 6)

def tele_circle(img, C, rx, ry, t, label=None, lab_pos=None):
    """antes: círculo de rotulador. Ahora: solo un rótulo tipo TV (sin rodear nada)."""
    t = clamp(t)
    if t <= 0 or not label: return
    d = ImageDraw.Draw(img, 'RGBA')
    f = font('BebasNeue-Regular.ttf', 66)
    x, y = lab_pos or (C[0], C[1] - ry - 50)
    l, tp, r, bt = d.textbbox((x, y), label, font=f, anchor='mm')
    a = int(255 * ease(t / .4))
    d.rounded_rectangle([l - 22, tp - 14, r + 22, bt + 14], radius=10, fill=(250, 214, 0, a))
    d.text((x, y), label, font=f, fill=(15, 15, 15, a), anchor='mm')

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

def score_bug(img, tor, ny, label='1ST QTR', clock='12:00', alpha=1.0, y=170):
    if alpha <= 0: return
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    f = font('BebasNeue-Regular.ttf', 58); fs = font('Anton-Regular.ttf', 50)
    x = 60
    d.rounded_rectangle([x, y, x + 720, y + 84], radius=10, fill=(12, 14, 22, 235))
    d.rectangle([x + 10, y + 10, x + 22, y + 74], fill=(28, 64, 150)); d.text((x + 36, y + 44), 'TOR', font=f, fill='white', anchor='lm')
    d.text((x + 175, y + 44), str(tor), font=fs, fill='white', anchor='mm')
    d.rectangle([x + 222, y + 10, x + 234, y + 74], fill=(236, 120, 30)); d.text((x + 248, y + 44), 'NY', font=f, fill='white', anchor='lm')
    d.text((x + 360, y + 44), str(ny), font=fs, fill='white', anchor='mm')
    d.rectangle([x + 402, y + 8, x + 404, y + 76], fill=(80, 80, 90))
    d.text((x + 420, y + 44), label, font=f, fill=(255, 214, 120), anchor='lm')
    if clock: d.text((x + 705, y + 44), clock, font=f, fill='white', anchor='rm')
    if alpha < 1: layer.putalpha(layer.getchannel('A').point(lambda v: int(v * alpha)))
    img.paste(layer, (0, 0), layer)

def big_final(img, t, t0):
    a = ease((t - t0) / .45)
    if a <= 0: return
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    cx, cy = W1 / 2, 640; s = .85 + .15 * a
    w, h = 900 * s, 460 * s
    d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], radius=24, fill=(12, 14, 22, 240), outline=(255, 214, 120, 255), width=6)
    d.text((cx, cy - h / 2 + 62 * s), 'FINAL', font=font('BebasNeue-Regular.ttf', int(84 * s)), fill=(255, 214, 120), anchor='mm')
    fA = font('Anton-Regular.ttf', int(170 * s)); fT = font('BebasNeue-Regular.ttf', int(80 * s))
    d.text((cx - 220 * s, cy + 10 * s), '66', font=fA, fill=(220, 220, 220), anchor='mm')
    d.text((cx + 220 * s, cy + 10 * s), '68', font=fA, fill=(255, 255, 255), anchor='mm')
    d.text((cx - 220 * s, cy + 150 * s), 'HUSKIES', font=fT, fill=(150, 180, 240), anchor='mm')
    d.text((cx + 220 * s, cy + 150 * s), 'KNICKS', font=fT, fill=(255, 160, 80), anchor='mm')
    d.text((cx, cy + 10 * s), '–', font=fA, fill=(150, 150, 150), anchor='mm')
    layer.putalpha(layer.getchannel('A').point(lambda v: int(v * a)))
    img.paste(layer, (0, 0), layer)

NEWS = None
def newspaper():
    global NEWS
    if NEWS: return NEWS
    w, h = 860, 1080
    rng = np.random.default_rng(4)
    base = np.ones((h, w, 3)) * np.array([232, 222, 196]) + rng.normal(0, 6, (h, w, 1))
    yy, xx = np.mgrid[0:h, 0:w]
    edge = np.minimum(np.minimum(xx, w - xx), np.minimum(yy, h - yy)) / 60
    base *= (0.86 + 0.14 * np.clip(edge, 0, 1))[..., None]
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(img)
    ink = (34, 30, 26)
    d.text((w / 2, 60), 'SPORTS', font=font('BebasNeue-Regular.ttf', 64), fill=ink, anchor='mm')
    d.line([(40, 100), (w - 40, 100)], fill=ink, width=4); d.line([(40, 108), (w - 40, 108)], fill=ink, width=1)
    # columnas de texto (lineas grises, ilegibles)
    r = random.Random(2)
    for col in range(3):
        x0 = 40 + col * 265
        for i in range(52):
            yv = 140 + i * 17
            if 300 < yv < 860 and col == 1: continue
            d.line([(x0, yv), (x0 + r.randint(170, 240), yv)], fill=(120, 112, 100), width=5)
    # anuncio recuadrado
    ax0, ay0, ax1, ay1 = 120, 290, w - 120, 880
    d.rectangle([ax0, ay0, ax1, ay1], fill=(240, 232, 208), outline=ink, width=6)
    d.rectangle([ax0 + 12, ay0 + 12, ax1 - 12, ay1 - 12], outline=ink, width=2)
    fS = 'LibreBaskerville-Regular.ttf'
    def F(n, s): return ImageFont.truetype(f"/mnt/skills/examples/canvas-design/canvas-fonts/{n}", s) if os.path.exists(f"/mnt/skills/examples/canvas-design/canvas-fonts/{n}") else font('BebasNeue-Regular.ttf', s)
    cx = w / 2
    d.text((cx, ay0 + 70), 'HUSKIES BASKETBALL', font=F('Gloock-Regular.ttf', 44), fill=ink, anchor='mm')
    d.text((cx, ay0 + 160), 'FREE', font=font('Anton-Regular.ttf', 120), fill=ink, anchor='mm')
    d.text((cx, ay0 + 250), 'ADMISSION', font=font('Anton-Regular.ttf', 74), fill=ink, anchor='mm')
    d.text((cx, ay0 + 330), 'to anyone taller than our center', font=F('LibreBaskerville-Regular.ttf', 26), fill=ink, anchor='mm')
    d.text((cx, ay0 + 395), 'GEORGE NOSTRAND', font=F('Gloock-Regular.ttf', 50), fill=ink, anchor='mm')
    d.text((cx, ay0 + 460), '6 ft. 8 in.', font=F('Gloock-Regular.ttf', 44), fill=ink, anchor='mm')
    d.text((cx, ay0 + 530), 'Be measured at the team office', font=F('LibreBaskerville-Regular.ttf', 24), fill=ink, anchor='mm')
    d.text((cx, ay0 + 562), 'the day before the game', font=F('LibreBaskerville-Regular.ttf', 24), fill=ink, anchor='mm')
    NEWS = img
    return img

# ------------------------------------------------------------------ escenas
def mk_team(team, pts, seed, numbers):
    return [Actor(team, n, 6.2 + random.Random(seed + i).uniform(-.2, .3), [(0, p)], seed=seed + i) for i, (p, n) in enumerate(zip(pts, numbers))]

NOSTRAND = Actor('TOR', 15, 6.67, [(0, (-6, -23.5))], skin=(228, 190, 160), hair=(40, 30, 22), seed=11)
FAN = Actor(height=6.0, keys=[(0, (12, -26)), (1, (12, -26))], civilian=((66, 54, 44), (48, 46, 50), (40, 34, 30)), skin=(222, 182, 150), seed=12)
POST = (-3.4, -23.5)

def draw_post(dr, cam, k, off):
    def P(x, y, z):
        u, v, d = cam.p((x, y, z)); return ((u - off[0]) * k, (v - off[1]) * k, cam.f * k / d)
    a = P(POST[0], POST[1], 0); b = P(POST[0], POST[1], 8.2)
    w = .3 * a[2]
    dr.line([a[:2], b[:2]], fill=(150, 110, 66), width=int(w))
    dr.rectangle([a[0] - w * 1.6, a[1] - w * .4, a[0] + w * 1.6, a[1] + w * .2], fill=(90, 66, 40))
    for i in range(0, 17):
        z = i * .5; q = P(POST[0], POST[1], z)
        L = w * (1.1 if i % 2 == 0 else .6)
        dr.line([(q[0] - w / 2, q[1]), (q[0] - w / 2 + L, q[1])], fill=(30, 22, 14), width=max(2, int(w * .12)))
    # chapa en 6'8"
    q = P(POST[0], POST[1], 6.667)
    dr.rectangle([q[0] - w * .9, q[1] - w * .25, q[0] + w * .9, q[1] + w * .25], fill=(230, 60, 40))

def virtual_line(img, cam, x0, y0, z, t, xa, xb, yv=-23.5, label='6 FT 8 IN'):
    """linea virtual tipo 'first down' a la altura 6'8"."""
    a = ease(t)
    if a <= 0: return
    A = P2F(cam, (xa, yv, 6.667), x0, y0, z); B = P2F(cam, (lerp(xa, xb, a), yv, 6.667), x0, y0, z)
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    d.line([A, B], fill=(255, 221, 0, 120), width=26); d.line([A, B], fill=(255, 230, 60, 255), width=8)
    img.paste(layer, (0, 0), layer)
    if a > .6 and label:
        d = ImageDraw.Draw(img, 'RGBA')
        f = font('BebasNeue-Regular.ttf', 70)
        tx = B[0] - 10; ty = B[1] - 62
        wlab = d.textlength(label, font=f) + 36
        d.rounded_rectangle([tx - wlab, ty - 40, tx, ty + 36], radius=8, fill=(255, 221, 0, 240))
        d.text((tx - wlab / 2, ty), label, font=f, fill=(10, 10, 10), anchor='mm')

def fan_keys(t_arrive):
    return [(0, (16, -26.5)), (t_arrive - 1.6, (16, -26.5)), (t_arrive, (-2.2, -24.2)), (999, (-2.2, -24.2))]

WARM = [Actor('TOR', 7, 6.3, [(0, (30, 8)), (4, (36, 2)), (8, (30, -6)), (12, (34, 8))], seed=21),
        Actor('NY', 12, 6.2, [(0, (-30, 6)), (5, (-36, -4)), (10, (-30, 6))], seed=22)]

def scene_height_set(t, t0, fan_t=None, line_t=None, label_t=None, arrow_t=None, mode='hook'):
    """set de la altura: Nostrand junto al poste medidor, a pie de pista."""
    cam = CAMS['tight']; bg = get_bg('tight')
    lt = t - t0
    zoom = 1.25 + .1 * ease(lt / 6)
    cu, cv = cam.p((-3.5, -23.5, 4.2))[:2]
    return dict(cam=cam, bg='tight', cu=cu, cv=cv - 60, zoom=zoom)

def frame_spec(t):
    """devuelve dict con camara/fondo y callbacks de dibujo para el tiempo t."""
    S = {}
    # ---------- A: gancho
    if t < ps(2):
        cam = CAMS['tight']
        z = 1.7 + .15 * ease(t / 5)
        cu, cv = cam.p((-3.6, -23.5, 3.6))[:2]
        FAN.keys = fan_keys(4.2)
        def dyn(dr, k, off):
            draw_actors(dr, cam, [(w, None, None) for w in WARM], t, k, off)
            draw_post(dr, cam, k, off)
            draw_actors(dr, cam, [(NOSTRAND, E.pose_stand(), -math.pi / 2), (FAN, None, None if t < 4.2 else -math.pi / 2)], t, k, off)
        def ov(img, x0, y0, zz):
            virtual_line(img, cam, x0, y0, zz, (t - .25) / .6, -10, -.2)
            A = P2F(cam, (-6, -23.5, 7.2), x0, y0, zz)
            tele_arrow(img, (A[0] + 300, A[1] - 150), (A[0] + 40, A[1] - 10), (t - wt(1, 'this')) / .35, 'THIS GUY', (A[0] + 340, A[1] - 205))
        return dict(cam=cam, bg='tight', cu=cu, cv=cv, zoom=z, dyn=dyn, ov=ov, bug=None)
    # ---------- B: plano desde detras de la canasta
    if t < ps(4):
        cam = CAMS['end']; lt = t - ps(2)
        z = 1.22 + .08 * ease(lt / 4)
        cu, cv = cam.W / 2, cam.p((-10, 0, 0))[1] - 250
        players = [Actor('TOR', 4 + i, 6.3, [(0, (-30 + 10 * i, -12 + 6 * i)), (6, (-24 + 10 * i, -6 + 5 * i))], seed=30 + i) for i in range(3)] + \
                  [Actor('NY', 10 + i, 6.3, [(0, (8 + 8 * i, 14 - 9 * i)), (6, (14 + 8 * i, 8 - 9 * i))], seed=40 + i) for i in range(3)]
        def dyn(dr, k, off):
            E.draw_basket(dr, cam, 1, k=k, off=off)
            draw_actors(dr, cam, [(p, None, None) for p in players], lt, k, off)
            E.draw_basket(dr, cam, -1, k=k, off=off)
        def ov(img, x0, y0, zz):
            lower_third(img, ps(3) - .1, t, 'MAPLE LEAF GARDENS', 'TORONTO', t_out=ps(4) - .3)
        return dict(cam=cam, bg='end', cu=cu, cv=cv, zoom=z, dyn=dyn, ov=ov, bug=None)
    # ---------- C: los dos equipos en la pista (camara lateral)
    if t < ps(7):
        cam = CAMS['side']; lt = t - ps(4)
        tor = [Actor('TOR', n, 6.2 + .1 * i, [(0, (-40 + 4 * i, -18 + 9 * i)), (5, (-14 + 2 * i, -16 + 8 * i))], seed=50 + i) for i, n in enumerate([4, 7, 9, 12])]
        tor.append(Actor('TOR', 15, 6.67, [(0, (-38, 16)), (5, (-6, 1))], seed=11, skin=NOSTRAND.skin, hair=NOSTRAND.hair))
        ny = [Actor('NY', n, 6.2 + .1 * i, [(0, (40 - 4 * i, 18 - 9 * i)), (5, (14 - 2 * i, 16 - 8 * i))], seed=60 + i) for i, n in enumerate([5, 8, 11, 14])]
        ny.append(Actor('NY', 3, 6.6, [(0, (38, -16)), (5, (6, -1))], seed=65))
        cx = lerp(-14, 0, ease(lt / 5))
        cu, cv = cam.p((cx, 0, 2))[:2]
        z = 1.12
        def dyn(dr, k, off):
            for s_ in (-1, 1): E.draw_basket(dr, cam, s_, k=k, off=off)
            draw_actors(dr, cam, [(p, None, (0 if p.team == 'TOR' else math.pi) if lt > 5 else None) for p in tor + ny], lt, k, off)
        def ov(img, x0, y0, zz):
            if t > ps(5) - .1:
                C = P2F(cam, (0, E.RINK_Y, 2.0), x0, y0, zz)
                tele_circle(img, C, 470, 70, (t - ps(5)) / .5, 'NOT THE NBA... YET', (C[0], C[1] - 140))
            if t > ps(6) - .05:
                lower_third(img, ps(6) - .05, t, 'BASKETBALL ASSOCIATION OF AMERICA', 'RENAMED "NBA" THREE YEARS LATER')
        return dict(cam=cam, bg='side', cu=cu, cv=cv - 250, zoom=1.35, dyn=dyn, ov=ov, bug=(0, 0, '1ST QTR', '12:00'))
    # ---------- D: la pista sobre el hielo (camara baja junto a la banda)
    if t < ps(10):
        cam = CAMS['tight']; lt = t - ps(7)
        t_slip = wt(9, 'slippery') - .35
        ball_h = Actor('TOR', 9, 6.3, [(0, (-22, -21.5)), (t_slip - ps(7), (-2, -21.5)), (t_slip - ps(7) + 1.2, (1.5, -22)), (t_slip - ps(7) + 3, (1.5, -22)), (9.7, (12, -21.5))], seed=52)
        defd = Actor('NY', 8, 6.3, [(0, (-14, -17)), (t_slip - ps(7), (4, -18)), (9.7, (16, -18))], seed=61)
        slip_t = t - t_slip
        cxw = clamp(ball_h.pos(lt)[0], -16, 10)
        cu, cv = cam.p((cxw + 2, -24, 2.0))[:2]
        z = 1.5
        def dyn(dr, k, off):
            if 0 < slip_t < 1.6:
                st = slip_t / .55 if slip_t < .55 else max(0, 1 - (slip_t - .55) / 1.0)
                pose = E.pose_slip(st); face = 0
            else:
                pose = None; face = None
            J = draw_actors(dr, cam, [(defd, None, None), (ball_h, pose, face)], lt, k, off)
            # balon botando
            x, y = ball_h.pos(lt)
            if 0 < slip_t < 1.6:
                bx, by, bz = x + 1.6 + slip_t * 3, y + .5, 1.0 + 2.0 * abs(math.sin(slip_t * 4)) * (1 - slip_t / 1.6)
            else:
                bounce = abs(math.sin(lt * 5.2)); bx, by, bz = x + 1.0, y - .9, .4 + 2.6 * bounce
            E.draw_ball(dr, cam, (bx, by, bz), k, off, spin=lt * 3)
        def ov(img, x0, y0, zz):
            A = P2F(cam, (-14, -31, 0), x0, y0, zz)
            tele_arrow(img, (A[0] - 120, A[1] + 300), (A[0], A[1] + 30), (t - wt(8, 'hockey')) / .4, 'HOCKEY RINK UNDERNEATH', (A[0] + 80, A[1] + 360))
            B = P2F(cam, (8, E.RINK_Y * -1, 3.0), x0, y0, zz)
            tele_arrow(img, (B[0] + 160, B[1] + 240), (B[0] + 40, B[1] + 30), (t - wt(9, 'boards')) / .4, 'HOCKEY BOARDS', (B[0] + 170, B[1] + 300))
        return dict(cam=cam, bg='tight', cu=cu, cv=cv + 60, zoom=z, dyn=dyn, ov=ov, bug=(0, 0, '1ST QTR', '12:00'))
    # ---------- E: precios (cartel colgado sobre el fondo)
    if t < ps(12):
        if t < ps(11):
            cam = CAMS['end']; lt = t - ps(10)
            z = 1.0 + .25 * ease(lt / 3)
            uS, vS = cam.p((70, 0, 43))[:2]
            cu, cv = lerp(cam.W / 2, uS, ease(lt / 3)), lerp(cam.H / 2, vS + 900, ease(lt / 3))
            def dyn(dr, k, off):
                E.draw_basket(dr, cam, 1, k=k, off=off); E.draw_basket(dr, cam, -1, k=k, off=off)
            return dict(cam=cam, bg='end', cu=cu, cv=cv, zoom=z, dyn=dyn, ov=None, bug=(0, 0, '1ST QTR', '12:00'))
        cam = CAMS['sign']; lt = t - ps(11)
        z = 1.05 + .1 * ease(lt / 3.5)
        uS, vS = cam.p((70, 0, 43))[:2]
        def ov(img, x0, y0, zz):
            C = P2F(cam, (70, 0, 42.3), x0, y0, zz)
            tele_circle(img, (C[0], C[1] + 40), 430, 120, (t - wt(11, 'seventy')) / .5)
        return dict(cam=cam, bg='sign', cu=uS, cv=vS + 330, zoom=z, dyn=None, ov=ov, bug=(0, 0, '1ST QTR', '12:00'))
    # ---------- F: anuncio en el periodico
    if t < ps(13):
        cam = CAMS['tight']; cu, cv = cam.p((-3.6, -23.5, 3.6))[:2]
        FAN.keys = [(0, (16, -26.5))]
        def dyn(dr, k, off):
            draw_post(dr, cam, k, off); draw_actor(dr, cam, NOSTRAND, t, k, off, E.pose_stand(), -math.pi / 2)
        def ov(img, x0, y0, zz):
            lt = t - ps(12)
            a = ease(lt / .45)
            np_ = newspaper().rotate(-4 + 3 * a, expand=True, resample=Image.BICUBIC, fillcolor=None)
            npi = np_.convert('RGBA')
            sc = .95 + .05 * a
            npi = npi.resize((int(npi.width * sc), int(npi.height * sc)))
            dark = Image.new('RGBA', img.size, (0, 0, 0, int(150 * a))); img.paste(dark, (0, 0), dark)
            x = int(W1 / 2 - npi.width / 2); y = int(lerp(H1 + 50, 300, a))
            sh = Image.new('RGBA', npi.size, (0, 0, 0, 120)); img.paste(sh, (x + 18, y + 22), npi)
            img.paste(npi, (x, y), npi)
        return dict(cam=cam, bg='tight', cu=cu, cv=cv - 40, zoom=1.7, dyn=dyn, ov=ov, bug=None, blur=6)
    # ---------- G: Nostrand, 6'8", entrar gratis, el aficionado se mide
    if t < ps(17):
        cam = CAMS['tight']; lt = t - ps(13)
        z = 1.75 + .1 * ease(lt / 8)
        cu, cv = cam.p((-3.0, -23.5, 3.6))[:2]
        FAN.keys = fan_keys(ps(16) + 1.3)
        def dyn(dr, k, off):
            draw_actors(dr, cam, [(w, None, None) for w in WARM], t, k, off)
            draw_post(dr, cam, k, off)
            arrived = t > ps(16) + 1.3
            draw_actors(dr, cam, [(NOSTRAND, E.pose_stand(), -math.pi / 2), (FAN, None, -math.pi / 2 if arrived else None)], t, k, off)
        def ov(img, x0, y0, zz):
            lower_third(img, ps(13) + .2, t, 'GEORGE NOSTRAND', 'HUSKIES CENTER', t_out=ps(16) - .2)
            virtual_line(img, cam, x0, y0, zz, (t - ps(14)) / .5, -10, -.2)
            if t > ps(15):
                d = ImageDraw.Draw(img); a = ease((t - ps(15)) / .25)
                s = int(lerp(150, 100, a))
                text_stroke(d, (W1 / 2 + 190, 560), 'FREE ENTRY', font('Anton-Regular.ttf', s), (255, 221, 0), 8)
            if t > ps(16) + 1.5:
                F_ = P2F(cam, (-2.2, -24.2, 6.4), x0, y0, zz)
                d = ImageDraw.Draw(img)
                text_stroke(d, (F_[0] + 150, F_[1] + 20), 'TOO SHORT', font('BebasNeue-Regular.ttf', 70), (255, 90, 70), 6)
        return dict(cam=cam, bg='tight', cu=cu, cv=cv, zoom=z, dyn=dyn, ov=ov, bug=None)
    # ---------- H: la grada llena: 7.090
    if t < ps(18):
        cam = CAMS['crowd']; lt = t - ps(17)
        cu = cam.W / 2 + lerp(-300, 300, ease(lt / 6.5)); cv = cam.H / 2
        def ov(img, x0, y0, zz):
            a = ease(lt / .3)
            n = int(7090 * ease((lt - .2) / 2.2))
            d = ImageDraw.Draw(img, 'RGBA')
            y = 620
            d.rounded_rectangle([140, y, W1 - 140, y + 230], radius=18, fill=(12, 14, 22, int(230 * a)), outline=(255, 214, 120, int(255 * a)), width=5)
            d.text((W1 / 2, y + 52), 'ATTENDANCE', font=font('BebasNeue-Regular.ttf', 64), fill=(255, 214, 120, int(255 * a)), anchor='mm')
            d.text((W1 / 2, y + 150), f'{n:,}', font=font('Anton-Regular.ttf', 130), fill=(255, 255, 255, int(255 * a)), anchor='mm')
            lower_third(img, wt(17, 'first') - .1, t, 'FIRST PRO BASKETBALL GAME', 'EVER PLAYED IN CANADA')
        return dict(cam=cam, bg='crowd', cu=cu, cv=cv, zoom=1.0, dyn=None, ov=ov, bug=(0, 0, '1ST QTR', '12:00'))
    # ---------- I: salto inicial = face-off
    if t < ps(19):
        cam = CAMS['tight']; lt = t - ps(18)
        tj = 1.5  # el arbitro lanza
        ref = Actor(None, None, 6.0, [(0, (-1.0, -2.5))], ref=True, seed=70)
        cA = Actor('TOR', 15, 6.67, [(0, (-1.6, 0))], skin=NOSTRAND.skin, hair=NOSTRAND.hair, seed=11)
        cB = Actor('NY', 3, 6.6, [(0, (1.6, 0))], seed=65)
        ring = [Actor('TOR', n, 6.3, [(0, p)], seed=80 + i) for i, (n, p) in enumerate(zip([4, 7, 9, 12], [(-8, -7), (-9, 6), (-14, -1), (-7, 9)]))] + \
               [Actor('NY', n, 6.3, [(0, p)], seed=90 + i) for i, (n, p) in enumerate(zip([5, 8, 11, 14], [(8, -7), (9, 6), (14, 1), (7, 9)]))]
        cu, cv = cam.p((0, 0, 4))[:2]
        z = 1.45 + .1 * ease(lt / 4)
        jt = (lt - tj - .25) / .9
        def dyn(dr, k, off):
            lst = [(p, E.pose_run(lt * 2 + i, .3) if lt > tj + .6 else E.pose_stand(), 0 if p.team == 'TOR' else math.pi) for i, p in enumerate(ring)]
            pr = E.pose_stand(); pr['rs'] = 2.8 if lt < tj + .3 else .3; pr['re'] = .1
            lst.append((ref, pr, math.pi / 2))
            if 0 < jt < 1:
                lst += [(cA, E.pose_jump(jt, 'one', 1), 0), (cB, E.pose_jump(jt * .95, 'one', 1), math.pi)]
            else:
                lst += [(cA, E.pose_stand(), 0), (cB, E.pose_stand(), math.pi)]
            draw_actors(dr, cam, lst, lt, k, off)
            # balon
            if lt < tj: bp = (-1.0 + .2, -2.2, 6.6)
            elif lt < tj + .75:
                u = (lt - tj) / .75; bp = (-.5 + .5 * u, -1.5 + 1.5 * u, 6.6 + 8 * u - 3 * u * u)
            elif lt < tj + 1.6:
                u = (lt - tj - .75) / .85; bp = (0 + 4 * u, 0 - 2 * u, 11.6 - 4 * u * u)
            else:
                u = min(1, (lt - tj - 1.6) / .8); bp = (4 + 3 * u, -2 - 1 * u, 7.6 - 6 * u)
            E.draw_ball(dr, cam, bp, k, off, spin=lt * 4)
            S['ball'] = bp
        def ov(img, x0, y0, zz):
            if 'ball' in S:
                C = P2F(cam, S['ball'], x0, y0, zz)
                ft = wt(18, 'face')
                tele_circle(img, C, 90, 90, (t - ft + .25) / .35, 'HOCKEY FACE-OFF?', (C[0], C[1] - 150))
        return dict(cam=cam, bg='tight', cu=cu, cv=cv - 60, zoom=z, dyn=dyn, ov=ov, bug=(0, 0, '1ST QTR', '12:00'))
    # ---------- J: primera canasta - Schectman
    if t < ps(20):
        cam = CAMS['side']; lt = t - ps(19)
        tl = 2.35  # momento de la bandeja
        osc = Actor('NY', 7, 6.0, [(0, (4, -10)), (tl - .25, (37.5, -2.5)), (tl + .8, (40, -1.5)), (4, (36, -6))], seed=95)
        d1 = Actor('TOR', 12, 6.3, [(0, (-2, -6)), (tl, (33, -5)), (4, (35, -6))], seed=82)
        d2 = Actor('TOR', 15, 6.67, [(0, (12, 6)), (tl, (36, 3)), (4, (37, 2))], seed=11, skin=NOSTRAND.skin, hair=NOSTRAND.hair)
        m2 = Actor('NY', 3, 6.6, [(0, (-6, 8)), (tl, (24, 6)), (4, (26, 6))], seed=65)
        bx = osc.pos(lt)[0]
        cu, cv = cam.p((clamp(bx, 0, 34), 0, 3))[:2]
        z = 1.75
        def dyn(dr, k, off):
            lay = (lt - tl + .45) / .9
            lst = [(d1, None, None), (d2, None, None), (m2, None, None)]
            if 0 < lay < 1: lst.append((osc, E.pose_jump(lay, 'one', 1.0), 0))
            else: lst.append((osc, None if lay < 0 else E.pose_stand(), None if lay < 0 else 0))
            for s_ in (-1, 1): E.draw_basket(dr, cam, s_, k=k, off=off)
            draw_actors(dr, cam, lst, lt, k, off)
            x, y = osc.pos(lt)
            if lay < .45:
                bp = (x + 1.1, y - .8, .5 + 2.5 * abs(math.sin(lt * 6))) if lay < 0 else (x + .7, y - .4, 7 + 4 * lay)
            elif lay < 1.1:
                u = (lay - .45) / .65; bp = (lerp(x + .7, 41.75, u), lerp(y, 0, u), 8.8 + 2 * math.sin(math.pi * u) + 1.5 * u)
            else:
                u = min(1, (lay - 1.1) / .5); bp = (41.75, 0, 10 - 9 * u)
            E.draw_ball(dr, cam, bp, k, off, spin=lt * 5)
        def ov(img, x0, y0, zz):
            lower_third(img, ps(19) + .2, t, 'OSSIE SCHECTMAN', 'FIRST BASKET IN LEAGUE HISTORY')
        made = lt > tl + 1.0
        return dict(cam=cam, bg='side', cu=cu, cv=cv - 120, zoom=z, dyn=dyn, ov=ov, bug=(0, 2 if made else 0, '1ST QTR', ''))
    # ---------- K: Nostrand, 16 puntos (tiro a dos manos, desde detras de la canasta)
    if t < ps(21):
        cam = CAMS['end']; lt = t - ps(20)
        nos = Actor('TOR', 15, 6.67, [(0, (-29, 11))], skin=NOSTRAND.skin, hair=NOSTRAND.hair, seed=11)
        dfd = Actor('NY', 3, 6.6, [(0, (-32.5, 5.0)), (1, (-32, 5.4))], seed=65)
        z = 1.7; cu, cv = cam.p((-33, 6, 6))[:2]
        def dyn(dr, k, off):
            st = lt / 1.0
            E.draw_basket(dr, cam, 1, k=k, off=off)
            draw_actors(dr, cam, [(nos, E.pose_set_shot(st), math.atan2(-11, -12.7)), (dfd, E.pose_jump(clamp((lt - .3) / .8), 'both', .9), 0)], lt, k, off)
            if st < .7: bp = (-29.6, 10.6, 5.0 + 2.6 * ease(st / .7))
            else:
                u = min(1, (st - .7) / .9)
                bp = (lerp(-29.6, -41.75, u), lerp(10.6, 0, u), lerp(7.6, 10.2, u) + 7 * math.sin(math.pi * u))
                if u >= 1: bp = (-41.75, 0, 10 - 8 * min(1, (st - 1.6) / .4))
            E.draw_ball(dr, cam, bp, k, off, spin=lt * 4)
            E.draw_basket(dr, cam, -1, k=k, off=off)
        def ov(img, x0, y0, zz):
            a = ease((t - wt(20, 'sixteen')) / .3)
            if a > 0:
                d = ImageDraw.Draw(img, 'RGBA'); y = 330
                d.rounded_rectangle([200, y, W1 - 200, y + 200], radius=16, fill=(12, 14, 22, int(230 * a)), outline=(28, 64, 150, int(255 * a)), width=6)
                d.text((W1 / 2, y + 50), 'GEORGE NOSTRAND', font=font('BebasNeue-Regular.ttf', 58), fill=(255, 255, 255, int(255 * a)), anchor='mm')
                d.text((W1 / 2, y + 135), '16 PTS', font=font('Anton-Regular.ttf', 100), fill=(255, 221, 0, int(255 * a)), anchor='mm')
        return dict(cam=cam, bg='end', cu=cu, cv=cv - 60, zoom=z, dyn=dyn, ov=ov, bug=None)
    # ---------- L: final 68-66
    if t < ps(22):
        cam = CAMS['side']; lt = t - ps(21)
        walk = [Actor('NY', n, 6.3, [(0, (8 + 3 * i, -4 + 4 * i)), (4, (30 + 3 * i, -12 + 4 * i))], seed=60 + i) for i, n in enumerate([5, 8, 11, 14, 3])] + \
               [Actor('TOR', n, 6.3, [(0, (-6 - 3 * i, 4 - 4 * i)), (4, (-26 - 3 * i, 14 - 4 * i))], seed=50 + i) for i, n in enumerate([4, 7, 9, 12, 15])]
        cu, cv = cam.p((0, 0, 3))[:2]
        def dyn(dr, k, off):
            for s_ in (-1, 1): E.draw_basket(dr, cam, s_, k=k, off=off)
            draw_actors(dr, cam, [(p, None, None) for p in walk], lt * .5, k, off)
        def ov(img, x0, y0, zz):
            big_final(img, t, wt(21, 'sixty') - .15)
        return dict(cam=cam, bg='side', cu=cu, cv=cv - 200, zoom=1.5, dyn=dyn, ov=ov, bug=(66, 68, 'FINAL', ''))
    # ---------- M: una sola temporada / los Knicks siguen
    if t < ps(24):
        cam = CAMS['end']; lt = t - ps(22)
        dim = 1 - .82 * ease(lt / 1.6)
        hus = Actor('TOR', 15, 6.67, [(0, (-20, 6)), (4.5, (-4, 24))], skin=NOSTRAND.skin, hair=NOSTRAND.hair, seed=11)
        kn = Actor('NY', 7, 6.0, [(0, (-24, -2))], seed=95)
        z = 1.7; cu, cv = cam.p((-22, 0, 4))[:2]
        def dyn(dr, k, off):
            hd = 1 - .85 * ease((lt - 1.4) / 1.4)
            lst = [(hus, None, None)]
            draw_actors(dr, cam, lst, lt, k, off, dim=max(.12, hd) * max(dim, .55))
            if t > ps(23) - .15:
                draw_actors(dr, cam, [(kn, E.pose_stand(), math.pi)], lt, k, off, dim=1.0)
                E.draw_ball(dr, cam, (-24.9, -1.4, 3.6), k, off)
            E.draw_basket(dr, cam, -1, k=k, off=off, dim=max(dim, .35))
        def ov(img, x0, y0, zz):
            lower_third(img, ps(22) + .3, t, 'TORONTO HUSKIES', 'ONE SEASON. THEN GONE.', t_out=ps(23) - .3)
            if t > ps(23) - .1:
                lower_third(img, ps(23) - .1, t, 'NEW YORK KNICKS', 'STILL HERE')
        spot = None
        if t > ps(23) - .15:
            spot = (cam, (-24, -2, 0), ease((t - ps(23) + .15) / .3))
        return dict(cam=cam, bg='end', cu=cu, cv=cv - 120, zoom=z, dyn=dyn, ov=ov, bug=None, dim=dim, spot=spot)
    # ---------- N: cierre
    return dict(close=True)

# ------------------------------------------------------------------ composicion
FONT_SUB = None
def subtitle_groups():
    groups = []
    for ph in PH:
        ws = ph['words']; cur = []
        for w in ws:
            cur.append(w)
            txt = ' '.join(x['w'] for x in cur)
            if len(cur) >= 3 or len(txt) > 15 or w['w'].endswith(('.', '?', ',', ':', '...')):
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
    # una linea o dos si no cabe
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
            pop = 1.0
            d.text((x, y), words[i], font=f, fill=YEL if act else (255, 255, 255), anchor='lm', stroke_width=9, stroke_fill=(0, 0, 0))
            x += widths[i] + sp
        y += 130

def watermark(img):
    d = ImageDraw.Draw(img, 'RGBA')
    d.text((W1 / 2, 84), HANDLE, font=font('Anton-Regular.ttf', 50), fill=(255, 255, 255, 190), anchor='mm', stroke_width=3, stroke_fill=(0, 0, 0, 160))

LOGO_IMG = None
CLOSE_BG = None
def close_frame(t):
    global LOGO_IMG, CLOSE_BG
    t0 = ps(24) - .1
    if CLOSE_BG is None:
        cam = CAMS['end']; bg = get_bg('end')
        b = bg.resize((W1 * bg.width // W2, H1), Image.LANCZOS)
        x0 = (b.width - W1) // 2
        b = b.crop((x0, 0, x0 + W1, H1)).filter(ImageFilter.GaussianBlur(14))
        CLOSE_BG = Image.eval(b, lambda v: int(v * .28))
    img = CLOSE_BG.copy()
    if LOGO_IMG is None:
        LOGO_IMG = Image.open(LOGO).convert('RGBA')
    a = ease((t - t0) / .5)
    s = int(lerp(520, 600, a))
    lg = LOGO_IMG.resize((s, s), Image.LANCZOS)
    if a < 1: lg.putalpha(lg.getchannel('A').point(lambda v: int(v * a)))
    img.paste(lg, (W1 // 2 - s // 2, 520 - s // 2 + 40), lg)
    d = ImageDraw.Draw(img)
    a2 = ease((t - wt(25, 'tomorrow')) / .3)
    if a2 > 0:
        text_stroke(d, (W1 / 2, 1010), "TOMORROW'S STORY?", font('Anton-Regular.ttf', int(110 * (.85 + .15 * a2))), (255, 255, 255), 8)
    a3 = ease((t - wt(26, 'vote')) / .3)
    if a3 > 0:
        bob = 10 * math.sin(t * 6)
        text_stroke(d, (W1 / 2 - 40, 1160), 'VOTE IN THE COMMENTS', font('BebasNeue-Regular.ttf', 92), YEL, 6)
        ax = W1 / 2 + 370; ay = 1160 + bob
        tri = [(ax - 26, ay - 10), (ax + 26, ay - 10), (ax, ay + 32)]
        d.rectangle([ax - 9, ay - 44, ax + 9, ay - 8], fill=YEL, outline=(0, 0, 0), width=4)
        d.polygon(tri, fill=YEL, outline=(0, 0, 0)); d.line(tri + [tri[0]], fill=(0, 0, 0), width=4)
        d.rectangle([ax - 6, ay - 41, ax + 6, ay - 6], fill=YEL)
    return img

def grade(img2x):
    """tono de retransmision: contraste suave, calidez, vineta, grano"""
    return img2x

VIGNETTE = None
def finish(img1, t, add_subs=True):
    global VIGNETTE
    if VIGNETTE is None:
        yy, xx = np.mgrid[0:H1, 0:W1]
        r = np.sqrt(((xx - W1 / 2) / (W1 * .75)) ** 2 + ((yy - H1 / 2) / (H1 * .62)) ** 2)
        VIGNETTE = np.clip(1.08 - .38 * r ** 2, .55, 1.0)[..., None].astype(np.float32)
    a = np.asarray(img1).astype(np.float32)
    a = a * VIGNETTE
    a[..., 0] *= 1.03; a[..., 2] *= .96
    rng = np.random.default_rng(int(t * 1000))
    a += rng.normal(0, 3.2, (H1 // 4, W1 // 4, 1)).repeat(4, 0).repeat(4, 1)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

def render_frame(t, subs=True):
    sp = frame_spec(t)
    if sp.get('close'):
        img = close_frame(t)
        img = finish(img, t)
        watermark(img)
        return img
    cam = sp['cam']; bg = get_bg(sp['bg'])
    z = sp['zoom']; cw, ch = W2 / z, H2 / z
    x0 = clamp(sp['cu'] - cw / 2, 0, bg.width - cw); y0 = clamp(sp['cv'] - ch / 2, 0, bg.height - ch)
    frame = bg.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch)))
    if frame.size != (W2, H2): frame = frame.resize((W2, H2), Image.BILINEAR)
    kk = W2 / int(cw)
    if sp.get('dim') is not None and sp['dim'] < 1:
        frame = Image.eval(frame, lambda v, d_=sp['dim']: int(v * d_))
    if sp.get('spot'):
        c_, P, a = sp['spot']
        u, v = P2F(c_, P, x0, y0, kk)
        u *= 2; v *= 2
        m = Image.new('L', (W2, H2), 0); md = ImageDraw.Draw(m)
        md.ellipse([u - 520, v - 1150, u + 520, v + 260], fill=int(255 * a))
        m = m.filter(ImageFilter.GaussianBlur(120))
        lit = bg.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W2, H2), Image.BILINEAR)
        frame = Image.composite(lit, frame, m)
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
        render_frame(float(args[1]), subs=False).save('hoops_lore_01_portada.jpg', quality=95); sys.exit()
    workers = 2
    from multiprocessing import Process
    bounds = [NFR * i // workers for i in range(workers + 1)]
    procs = [Process(target=render_range, args=(bounds[i], bounds[i + 1], f'seg{i}.mp4')) for i in range(workers)]
    for p in procs: p.start()
    for p in procs: p.join()
    open('segs.txt', 'w').write(''.join(f"file 'seg{i}.mp4'\n" for i in range(workers)))
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', 'segs.txt', '-i', AUDIO, '-map', '0:v', '-map', '1:a',
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', 'hoops_lore_01.mp4'], check=True)
    print('OK hoops_lore_01.mp4')
