#!/usr/bin/env python3
"""Gridiron Lore 05 - Tom Dempsey, 63 yardas (Tulane Stadium, 8 nov 1970). Motor del 04 (engine04 + figures).
Uso: python3 render_gridiron_lore_05.py voz.mp3 out.mp4 [--preview t1,t2,...] [--cover t] [--range a b]"""
import sys, json, math, random, subprocess, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import engine04 as E
from engine04 import (Cam, render_world, pose_joints, run_pose, stance_pose, blend, UP, ease, lerp, clamp, mix, shade)
import figures as FG
import base03 as B

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
SS = 1.5
SW, SH = int(W * SS), int(H * SS)
YEL = (255, 204, 41); WHITE = (255, 255, 255); BLACK = (0, 0, 0)
NOG = (200, 164, 80); NOB = (22, 22, 24); DETB = (0, 110, 182); DETS = (176, 183, 188)

SCRIPT = [l.strip() for l in open(os.path.join(HERE, 'gridiron_lore_05_guion.txt')) if l.strip()]
TIMES = json.load(open(os.path.join(HERE, 'times.json')))
SEGS = json.load(open(os.path.join(HERE, 'times_segs.json')))
CH = B.chunks(B.build_words(TIMES, SEGS))

def AF(sz): return B.F(B.ANTON, int(sz))
def BF(sz): return B.F(B.BEBAS, int(sz))

# ---------------------------------------------------------------- Tulane 1970: equipos, cesped natural, publico sin abrigos
# 'GB' = Saints (local, negro y dorado) · 'DAL' = Lions (azul Honolulu y plata). Sin logos.
E.TEAM['GB'] = dict(helmet=(204, 168, 86), hstripe=[(22, 22, 24), (240, 240, 240), (22, 22, 24)], mask=(140, 140, 140),
                    jersey=(24, 24, 26), num=(240, 240, 236), numout=(204, 168, 86), sleeve=[(204, 168, 86), (240, 240, 236), (204, 168, 86)],
                    pants=(204, 168, 86), pstripe=[(22, 22, 24), (240, 240, 236)], sock=(24, 24, 26), sockstripe=(204, 168, 86),
                    shoe=(20, 20, 22), skin=None)
E.TEAM['DAL'] = dict(helmet=(178, 184, 190), hstripe=[(0, 110, 182), (240, 240, 240), (0, 110, 182)], mask=(90, 90, 96),
                     jersey=(0, 104, 176), num=(240, 240, 240), numout=(240, 240, 240), sleeve=[(240, 240, 240), (240, 240, 240)],
                     pants=(178, 184, 190), pstripe=[(0, 110, 182), (240, 240, 240)], sock=(0, 104, 176), sockstripe=(240, 240, 240),
                     shoe=(20, 20, 22), skin=None)
E.COATS = [(236, 236, 230), (214, 222, 236), (200, 164, 80), (24, 24, 26), (238, 226, 190), (170, 196, 220), (120, 120, 126),
           (226, 210, 160), (196, 60, 50), (90, 110, 150), (240, 240, 236), (200, 164, 80), (60, 60, 64), (150, 170, 130)]
E.HATS = [(40, 30, 24), (60, 44, 30), (24, 22, 20), (110, 80, 50), (180, 150, 100), (150, 150, 150), (40, 30, 24),
          (226, 214, 170), (200, 164, 80), (60, 44, 30)]

def make_ground5(seed=1):
    GX0, GX1, GY0, GY1, GPX = E.GX0, E.GX1, E.GY0, E.GY1, E.GPX
    FW = E.FIELD_W
    rng = np.random.default_rng(seed)
    Wd = int((GX1 - GX0) * GPX); Hd = int((GY1 - GY0) * GPX)
    def X(x): return (x - GX0) * GPX
    def Y(y): return (y - GY0) * GPX
    n1 = rng.random((Hd // 10 + 2, Wd // 10 + 2)).astype(np.float32)
    n1 = np.array(Image.fromarray((n1 * 255).astype(np.uint8)).resize((Wd, Hd), Image.BICUBIC), np.float32) / 255
    n3 = rng.random((Hd, Wd)).astype(np.float32)
    xs = (np.arange(Wd) / GPX + GX0)
    stripe = ((np.floor(xs / 5) % 2) * 0.07)[None, :]
    grass = np.array([62, 122, 52], np.float32)
    base = grass[None, None, :] * (0.86 + 0.18 * n1[..., None] + stripe[..., None] + 0.1 * (n3[..., None] - 0.5))
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    rr = random.Random(seed)
    # zonas gastadas (tierra) entre los hashes en el centro
    for i in range(1400):
        x = rr.gauss(50, 22); y = rr.gauss(0, 5)
        r = rr.uniform(0.05, 0.16)
        d.ellipse([X(x - r * 1.5), Y(y - r), X(x + r * 1.5), Y(y + r)], fill=mix((92, 104, 60), (66, 112, 54), rr.random()))
    lw = max(2, int(GPX * 0.11)); white = (240, 242, 244)
    for x in range(0, 101, 5):
        d.line([X(x), Y(-FW / 2), X(x), Y(FW / 2)], fill=white, width=lw if x % 10 else lw + 1)
    for x in (-10, 110):
        d.line([X(x), Y(-FW / 2), X(x), Y(FW / 2)], fill=white, width=lw)
    for y in (-FW / 2, FW / 2):
        d.line([X(-10), Y(y), X(110), Y(y)], fill=white, width=lw + 2)
    for x in range(1, 100):
        if x % 5 == 0: continue
        for y in (-FW / 2 + 0.3, FW / 2 - 0.9, -3.33, 3.33 - 0.6):
            d.line([X(x), Y(y), X(x), Y(y + 0.6)], fill=white, width=lw)
    fnt = E.font('Anton-Regular.ttf', GPX * 2.2)
    for x in range(10, 100, 10):
        n = x if x <= 50 else 100 - x
        for y, rot in ((-FW / 2 + 12, 180), (FW / 2 - 12, 0)):
            t = Image.new('L', (int(GPX * 5), int(GPX * 3)), 0)
            ImageDraw.Draw(t).text((t.size[0] / 2, t.size[1] / 2), str(n), font=fnt, fill=235, anchor='mm')
            t = t.rotate(rot + 90, expand=True).transpose(Image.FLIP_TOP_BOTTOM)
            img.paste(Image.new('RGB', t.size, white), (int(X(x) - t.size[0] / 2), int(Y(y) - t.size[1] / 2)), t)
    # fuera del campo: pista de ceniza/hierba mas oscura
    for (x0, x1) in ((GX0, -10.4), (110.4, GX1)):
        d.rectangle([X(x0), 0, X(x1), Hd], fill=(70, 104, 52))
    for (y0, y1) in ((GY0, -FW / 2 - 3), (FW / 2 + 3, GY1)):
        d.rectangle([0, Y(y0), Wd, Y(y1)], fill=(70, 104, 52))
    return img.filter(ImageFilter.GaussianBlur(0.6))

_gp = os.path.join(HERE, 'cache_ground05.png')
if os.path.exists(_gp): E.GROUND = Image.open(_gp).convert('RGB')
else:
    E.GROUND = make_ground5(); E.GROUND.save(_gp)

def goalpost_H(draw, cam, xg):
    """Poste en H (dos postes verticales) sobre la linea de gol, como en Tulane Stadium."""
    Yc = (236, 214, 70)
    def L(A, B, w):
        pa, pb = cam.p(A), cam.p(B)
        if pa[2] < 0.5 or pb[2] < 0.5: return
        ww = max(2, int(cam.f * w / ((pa[2] + pb[2]) / 2)))
        draw.line([pa[:2], pb[:2]], fill=Yc, width=ww)
    for y in (-3.08, 3.08):
        L((xg, y, 0), (xg, y, 3.33), 0.12)
        L((xg, y, 3.33), (xg, y, 10.5), 0.08)
    L((xg, -3.08, 3.33), (xg, 3.08, 3.33), 0.1)
    # proteccion acolchada en la base de los postes
    for y in (-3.08, 3.08):
        L((xg, y, 0), (xg, y, 2.0), 0.2)
        L((xg, y, 0), (xg, y, 2.0), 0.0)

def cam(pos, look, f, roll=0.0):
    return Cam(pos, look, f * SS, SW, SH, roll)

def world(c, cheer=0.0):
    img = render_world(c, cheer=cheer)
    d = ImageDraw.Draw(img)
    goalpost_H(d, c, 0); goalpost_H(d, c, 100)
    return img

def finish(img):
    return img.resize((W, H), Image.LANCZOS)

def P(J, team, num='', skin=0, **kw):
    p = dict(J=J, team=team, num=num, skin=skin, breath=False); p.update(kw); return p

# ---------------------------------------------------------------- graficos de TV
def score_bug(d, det, no, clock='4TH  0:02', extra=None, flash=None, y=232, title=None):
    x0 = 60; f = BF(54)
    d.rounded_rectangle([x0, y, W - 60, y + 76], 8, fill=(12, 14, 22))
    fl = flash == 'DET'
    d.rectangle([x0 + 10, y + 8, x0 + 330, y + 68], fill=DETB if not fl else YEL)
    d.text((x0 + 28, y + 38), 'LIONS', font=f, fill=WHITE if not fl else BLACK, anchor='lm')
    d.text((x0 + 312, y + 38), str(det), font=f, fill=WHITE if not fl else BLACK, anchor='rm')
    fl = flash == 'NO'
    d.rectangle([x0 + 340, y + 8, x0 + 660, y + 68], fill=NOB if not fl else YEL)
    d.rectangle([x0 + 340, y + 8, x0 + 348, y + 68], fill=NOG)
    d.text((x0 + 362, y + 38), 'SAINTS', font=f, fill=NOG if not fl else BLACK, anchor='lm')
    d.text((x0 + 642, y + 38), str(no), font=f, fill=WHITE if not fl else BLACK, anchor='rm')
    d.text((x0 + 810, y + 38), clock, font=f, fill=YEL, anchor='mm')
    if title:
        tw = d.textlength(title, font=BF(44))
        d.rectangle([x0, y - 52, x0 + tw + 28, y - 4], fill=(12, 14, 22))
        d.text((x0 + 14, y - 28), title, font=BF(44), fill=WHITE, anchor='lm')
    if extra:
        tw = d.textlength(extra, font=BF(46))
        d.rectangle([x0, y + 82, x0 + tw + 30, y + 134], fill=(190, 30, 30))
        d.text((x0 + 15, y + 108), extra, font=BF(46), fill=WHITE, anchor='lm')

def lower_third(d, y, big, small=None, col=(12, 14, 22), acc=YEL, t=1.0):
    if t <= 0: return
    k = ease(t / 0.35)
    fb = AF(76)
    wbig = d.textlength(big, font=fb) + 70
    if wbig > W - 120:
        fb = AF(76 * (W - 190) / (wbig - 70)); wbig = d.textlength(big, font=fb) + 70
    x0 = 60; x1 = x0 + int(wbig * k)
    d.rectangle([x0, y, x1, y + 104], fill=col)
    d.rectangle([x0, y, x0 + 12, y + 104], fill=acc)
    if k > 0.9:
        d.text((x0 + 40, y + 52), big, font=fb, fill=WHITE, anchor='lm')
    if small and k > 0.9:
        ws = d.textlength(small, font=BF(48)) + 50
        d.rectangle([x0, y + 108, x0 + ws, y + 166], fill=acc)
        d.text((x0 + 25, y + 137), small, font=BF(48), fill=BLACK, anchor='lm')

def tele_arrow(d, a, b, col=YEL, w=12, head=34):
    ax, ay = a; bx, by = b
    d.line([ax, ay, bx, by], fill=col, width=w)
    ang = math.atan2(by - ay, bx - ax)
    d.polygon([(bx + head * math.cos(ang), by + head * math.sin(ang)), (bx + head * .85 * math.cos(ang + 2.3), by + head * .85 * math.sin(ang + 2.3)),
               (bx + head * .85 * math.cos(ang - 2.3), by + head * .85 * math.sin(ang - 2.3))], fill=col)

# ---------------------------------------------------------------- bota de punta plana (sin pie)
def draw_shoe(img, cx, cy, sc, ang=0.0, hl=0.0):
    """Bota de patada de piel negra, cana alta, cordones blancos, tacos, y frontal plano y cuadrado (placa)."""
    ca, sa = math.cos(ang), math.sin(ang)
    def T(x, y):
        x -= 0.5; y -= 0.25
        return (cx + (x * ca - y * sa) * sc, cy - (x * sa + y * ca) * sc)
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    # sombra en el cesped
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
    a, b = T(-0.02, -0.07), T(1.08, -0.02)
    sd.ellipse([min(a[0], b[0]), min(a[1], b[1]) - sc * 0.05, max(a[0], b[0]), max(a[1], b[1]) + sc * 0.06], fill=(0, 0, 0, 120))
    sh = sh.filter(ImageFilter.GaussianBlur(sc * 0.03)); img.paste(sh, (0, 0), sh)
    upper = [(0.03, 0.07), (0.0, 0.18), (0.01, 0.34), (0.05, 0.5), (0.09, 0.56), (0.2, 0.57), (0.3, 0.56), (0.35, 0.52),
             (0.47, 0.44), (0.6, 0.37), (0.72, 0.32), (0.8, 0.305), (0.9, 0.3), (0.975, 0.295), (0.985, 0.28), (0.985, 0.07)]
    d.polygon([T(*p) for p in upper], fill=(26, 26, 28))
    # brillo de la piel (franja superior)
    gl = Image.new('RGBA', img.size, (0, 0, 0, 0)); gd = ImageDraw.Draw(gl)
    gd.line([T(0.06, 0.46), T(0.2, 0.53), T(0.33, 0.5), T(0.5, 0.4), T(0.7, 0.32), T(0.95, 0.28)], fill=(150, 150, 156, 150), width=int(sc * .03))
    gd.line([T(0.05, 0.25), T(0.4, 0.2), T(0.8, 0.22)], fill=(110, 110, 116, 70), width=int(sc * .05))
    gl = gl.filter(ImageFilter.GaussianBlur(sc * 0.012))
    # recortar el brillo a la silueta
    m = Image.new('L', img.size, 0); ImageDraw.Draw(m).polygon([T(*p) for p in upper], fill=255)
    gl.putalpha(Image.fromarray(np.minimum(np.asarray(gl.split()[3]), np.asarray(m))))
    lay = Image.alpha_composite(lay, gl); d = ImageDraw.Draw(lay)
    # costuras
    for pts in ([(0.04, 0.12), (0.5, 0.11), (0.97, 0.12)], [(0.7, 0.32), (0.72, 0.2), (0.7, 0.1)], [(0.06, 0.5), (0.1, 0.4), (0.1, 0.12)]):
        for (x1, y1), (x2, y2) in zip(pts[:-1], pts[1:]):
            for k in range(0, 10, 2):
                p1 = T(lerp(x1, x2, k / 10), lerp(y1, y2, k / 10)); p2 = T(lerp(x1, x2, (k + 1) / 10), lerp(y1, y2, (k + 1) / 10))
                d.line([p1, p2], fill=(96, 96, 100), width=max(1, int(sc * .005)))
    # cuello acolchado
    d.line([T(0.08, 0.555), T(0.2, 0.565), T(0.31, 0.555)], fill=(60, 60, 62), width=int(sc * .025))
    # lengueta y cordones
    d.polygon([T(0.3, 0.6), T(0.36, 0.61), T(0.4, 0.5), T(0.33, 0.52)], fill=(40, 40, 42))
    for i in range(7):
        u = i / 6
        x = lerp(0.36, 0.66, u); y = lerp(0.51, 0.36, u)
        d.line([T(x - 0.035, y - 0.02), T(x + 0.035, y + 0.03)], fill=(236, 236, 230), width=max(2, int(sc * .012)))
        d.line([T(x - 0.035, y + 0.03), T(x + 0.035, y - 0.02)], fill=(220, 220, 214), width=max(2, int(sc * .012)))
    # suela y tacos
    d.polygon([T(0.02, 0.075), T(1.0, 0.075), T(1.0, 0.03), T(0.03, 0.03)], fill=(44, 36, 30))
    for x in (0.08, 0.2, 0.52, 0.66, 0.8, 0.93):
        d.polygon([T(x - 0.02, 0.03), T(x + 0.02, 0.03), T(x + 0.014, -0.025), T(x - 0.014, -0.025)], fill=(30, 30, 32))
    # frontal plano: placa cuadrada vista en tres cuartos
    front = [T(0.985, 0.295), T(1.035, 0.32), T(1.035, 0.085), T(0.985, 0.06)]
    c0 = mix((70, 70, 74), (150, 150, 156), hl)
    d.polygon(front, fill=c0)
    d.line([front[0], front[1]], fill=mix((120, 120, 126), (230, 230, 236), hl), width=max(2, int(sc * .008)))
    d.line([front[1], front[2]], fill=(40, 40, 42), width=max(2, int(sc * .006)))
    img.paste(lay, (0, 0), lay)
    return T

def shoe_bg(t, blur=26):
    c = cam((44 + t * 0.15, -6, 0.7), (60, 4, 1.5), 700)
    img = world(c).filter(ImageFilter.GaussianBlur(blur))
    return finish(img)

def shoe_shot(t, lt, ang=0.0, hl=0.0, x=W // 2 - 20, y=1010, sc=640):
    img = shoe_bg(t)
    # cesped nitido en primer plano bajo la bota
    T = draw_shoe(img, x, y, sc * (1 + 0.03 * lt), ang + 0.02 * math.sin(lt * 0.7), hl)
    return img, T

# ---------------------------------------------------------------- fisica de la patada
KICK_X = 37.0
def ball_prop(bp, ax, k=1.0, bias=0.0):
    ax = ax / np.linalg.norm(ax)
    def draw(C, L, c_):
        A = bp - ax * 0.12 * k; Bq = bp + ax * 0.12 * k
        FG.cone(C, c_, A, bp, .02 * k, .085 * k, (120, 62, 30), L, spec=.3)
        FG.cone(C, c_, bp, Bq, .085 * k, .02 * k, (120, 62, 30), L, spec=.3)
    return dict(J={'pelvis': bp}, team='PROP', prims=lambda c_: [(c_.depth(bp) - bias, lambda C, L: draw(C, L, c_))])

def flight(s):
    """s=0 contacto, s=1 cruza la linea de gol (x=100)."""
    u = 0.934 * s
    x = KICK_X + 67.4 * u
    z = 0.12 + 4 * 17 * u * (1 - u)
    y = 0.25 + 0.4 * u
    return np.array([x, y, z])

def kick_s(t):
    tk = TIMES[10][0] + 1.3
    return (t - tk) / 4.0

def kick_pose5(Pp, yaw, k):
    """Patada de punta (estilo de Dempsey) con la pierna DERECHA. k 0..1: dos pasos, apoyo, golpeo."""
    if k < 0.55:
        return run_pose(Pp, yaw, k * 2.6, speed=0.6)
    kk = (k - 0.55) / 0.45
    sw = ease(kk)
    return pose_joints(Pp, yaw, pitch=lerp(0.1, -0.2, sw), legs=((0.12, 0.3), (lerp(-0.5, 1.6, sw), lerp(1.4, 0.05, sw))),
                       arms=((0.5 + 0.6 * sw, 0.4, 0.9), (0.3, 0.4, 0.7)))

def holder_pose(hold=1.0):
    # rodilla derecha en el suelo, izquierda adelantada; manos sobre el balon
    J = pose_joints((KICK_X + 0.15, 0.95, 0.6), math.radians(-70), pitch=0.45, legs=((1.35, 1.45), (0.05, 1.55)),
                    arms=((lerp(1.2, 0.85, hold), lerp(0.4, 0.2, hold), 0.05), (lerp(1.2, 0.95, hold), lerp(0.4, 0.2, hold), 0.05)),
                    ground=False, head_pitch=-0.5)
    return J

def fg_people(t, phase):
    """Formacion de gol de campo: linea en la 45 (Saints atacan hacia x=100). phase: 'set' o tiempo desde el snap."""
    Pl = []
    xl = 45.0
    snapped = phase != 'set' and phase > 0
    for i, yy in enumerate([-3.4, -2.3, -1.15, 0, 1.15, 2.3, 3.4]):
        Pl.append(P(stance_pose((xl - 0.9, yy), 0, 'block' if snapped else '3pt'), 'GB', ['80', '73', '62', '56', '65', '74', '85'][i], i))
    Pl.append(P(stance_pose((xl - 1.9, -4.4), 0.3, 'block' if snapped else 'ready'), 'GB', '33', 2))
    Pl.append(P(stance_pose((xl - 1.9, 4.4), -0.3, 'block' if snapped else 'ready'), 'GB', '40', 3))
    for i, yy in enumerate([-4.0, -2.8, -1.4, -0.3, 0.8, 2.0, 3.2, 4.4]):
        if snapped:
            Pl.append(P(pose_joints((xl + 0.6, yy), math.pi, pitch=0.5, legs=((0.6, 0.9), (0.1, 0.3)), arms=((2.8, 0.2, 0.3), (2.8, 0.2, 0.3))), 'DAL', ['76', '71', '75', '78', '79', '72', '74', '86'][i], i + 1))
        else:
            Pl.append(P(stance_pose((xl + 0.9, yy), math.pi, '3pt'), 'DAL', ['76', '71', '75', '78', '79', '72', '74', '86'][i], i + 1))
    Pl.append(P(stance_pose((xl + 5, -2.5), math.pi, 'ready'), 'DAL', '20', 2))
    Pl.append(P(stance_pose((xl + 5, 2.5), math.pi, 'ready'), 'DAL', '24', 4))
    return Pl

def kick_scene_people(t):
    """Personas y balon en la jugada completa, en tiempo absoluto t (frase 10)."""
    T10 = TIMES[10][0]
    lt = t - T10
    snap = lt - 0.35
    Pl = fg_people(t, 'set' if snap <= 0 else snap)
    # balon
    if snap <= 0:
        bp = np.array([45.0, 0.0, 0.12]); ax = np.array([1.0, 0, 0.2])
    elif snap < 0.3:
        u = snap / 0.3
        bp = np.array([lerp(45, KICK_X + 0.1, u), lerp(0, 0.3, u), 0.12 + 0.5 * math.sin(u * math.pi) + 0.35 * u]); ax = np.array([1.0, 0, 0.1])
    elif snap < 0.55:
        u = ease((snap - 0.3) / 0.25)
        bp = np.array([KICK_X + 0.05, 0.28, lerp(0.47, 0.17, u)]); ax = np.array([0.1 * (1 - u), 0, 1.0])
    elif kick_s(t) <= 0:
        bp = np.array([KICK_X, 0.25, 0.17]); ax = np.array([0.05, 0, 1.0])
    else:
        s = kick_s(t)
        bp = flight(s); ax = np.array([math.cos(s * 40), 0, math.sin(s * 40) + 1e-3])
    hold = clamp((snap - 0.3) / 0.25) if snap > 0 else 0.0
    Pl.append(P(holder_pose(hold), 'GB', '42', 1))
    kk = clamp((lt - 0.5) / 0.8)
    kx = lerp(KICK_X - 3.0, KICK_X - 0.5, min(1, kk / 0.6))
    if lt < 0.5:
        Jk = stance_pose((KICK_X - 3.0, 0.15), 0, 'stand')
    else:
        Jk = kick_pose5((kx, 0.15), 0, kk if kick_s(t) < 0.12 else 1.0)
    Pl.append(P(Jk, 'GB', '19', 0))
    Pl.append(ball_prop(bp, ax, 1.0 + 1.6 * clamp(kick_s(t) / 0.15)))
    return Pl, bp

def endzone_cam_view(t, s, people_far=True, refs_up=0.0, cheer=0.0, cz=6.0, f=1500):
    c = cam((117, -1.5, cz), (70, 0, 8.5), f)
    img = world(c, cheer=cheer)
    Pl = []
    if people_far:
        Pl += fg_people(t, 1.0)
        Pl.append(P(holder_pose(1), 'GB', '42', 1))
        Pl.append(P(stance_pose((KICK_X, 0.15), 0, 'stand'), 'GB', '19', 0))
    for sg in (1, -1):
        a = lerp(0.05, 2.95, ease(refs_up))
        Pl.append(P(pose_joints((101.2, sg * 4.2), math.pi, legs=((0.06, 0.08), (-0.06, 0.08)), arms=((a, 0.1, 0.1), (a, 0.1, 0.1))), 'REF', skin=sg + 2))
    if s is not None and s > -0.01:
        bp = flight(s); ax = np.array([math.cos(s * 40), 0, math.sin(s * 40)])
        Pl.append(ball_prop(bp, ax + np.array([0, 0, 1e-3]), 2.2, 50))
    img = FG.draw_people(img, c, Pl, t)
    return img, c

def wide_ez(t, k_desc=0.0, cheer=0.0, z0=26, z1=14):
    z = lerp(z0, z1, ease(k_desc))
    c = cam((-18 + 4 * k_desc, -5 + 5 * k_desc, z), (38, 0, -6), 1150)
    return world(c, cheer=cheer), c

def sideline_cam(t, fx, people, f=4200, look_z=-0.4, y_cam=-40, z_cam=8.0):
    # camara de banda algo adelantada y mas baja: la linea se abre en diagonal en vez de apelotonarse
    c = cam((fx - 24, y_cam, z_cam), (fx + 1.5, 0.5, look_z), f)
    img = world(c)
    img = FG.draw_people(img, c, people, t)
    return img, c

def virtual_line(img, c, x, col=(255, 214, 40), a=170):
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    q = [c.p((x - .12, -26.6, 0.02)), c.p((x + .12, -26.6, 0.02)), c.p((x + .12, 26.6, 0.02)), c.p((x - .12, 26.6, 0.02))]
    if min(p[2] for p in q) > 0.3:
        d.polygon([p[:2] for p in q], fill=col + (a,))
    img.paste(lay, (0, 0), lay)

# ---------------------------------------------------------------- barra comparativa
BG_CACHE = {}
def blurred_stadium(key='bars'):
    if key not in BG_CACHE:
        img, c = wide_ez(0, 1.0)
        img = finish(img).filter(ImageFilter.GaussianBlur(16))
        BG_CACHE[key] = Image.blend(img, Image.new('RGB', img.size, (8, 12, 22)), 0.5)
    return BG_CACHE[key].copy()

def bars(lt, rows, title, hi=None):
    """rows: lista de (yardas, etiqueta, color, t_inicio)."""
    img = blurred_stadium(); d = ImageDraw.Draw(img)
    B.headline(d, 470, title, 104, YEL)
    x0, x1 = 90, W - 90
    scale = (x1 - x0) / 70.0
    for i, (yd, lab, col, t0) in enumerate(rows):
        y = 620 + i * 210
        k = ease((lt - t0) / 0.7)
        if lt < t0: continue
        # pista de cesped con marcas cada 10 yardas
        d.rounded_rectangle([x0, y + 50, x1, y + 140], 10, fill=(40, 90, 44))
        for yy in range(10, 70, 10):
            xx = x0 + yy * scale
            d.line([xx, y + 54, xx, y + 136], fill=(230, 236, 230), width=3)
        d.rounded_rectangle([x0, y + 58, x0 + max(20, yd * scale * k), y + 132], 8, fill=col)
        n = int(round(yd * k))
        d.text((x0, y + 20), lab, font=BF(52), fill=WHITE, anchor='ls', stroke_width=3, stroke_fill=BLACK)
        tc = BLACK if sum(col) > 360 else WHITE
        if k > 0.25:
            d.text((x0 + yd * scale * k - 16, y + 95), f'{n} YDS', font=AF(62), fill=tc, anchor='rm')
        if hi == i and k >= 1:
            d.rounded_rectangle([x0 - 8, y + 42, x1 + 8, y + 148], 14, outline=YEL, width=6)
    return img

# ---------------------------------------------------------------- escenas por frase
def S0(t, T0, T1):
    lt = t - T0
    if lt < 2.6:
        img, Tm = shoe_shot(t, lt, ang=0.03, hl=0.6)
        d = ImageDraw.Draw(img)
        B.headline(d, 400, 'BORN', 150)
        B.headline(d, 560, 'WITHOUT TOES', 140, YEL)
        return img
    s = 0.62 + (lt - 2.6) / 4.0 * 0.6
    img, c = endzone_cam_view(t, s, refs_up=clamp((s - 1.0) / 0.1), cheer=1.0 if s > 1 else 0.0)
    img = finish(img); d = ImageDraw.Draw(img)
    B.headline(d, 400, 'NFL RECORD KICK', 120)
    B.headline(d, 540, 'FOR 43 YEARS', 140, YEL)
    return img

def S1(t, T0, T1):
    lt = t - T0; dur = T1 - T0
    # Dempsey (#19) de espaldas en la banda, mirando al campo; camara baja a media distancia
    x = 40 + lt * 0.25
    c = cam((x - 1.2, -35.5, 1.7), (x + 1.2, -20, 1.9), 1500)
    img = world(c)
    Pl = [P(pose_joints((x + 0.25, -31.2), math.radians(78), legs=((0.05, 0.06), (-0.05, 0.06)), arms=((0.1, 0.35, 0.15), (0.1, 0.35, 0.15))), 'GB', '19', 0)]
    for i, (xx, yy) in enumerate([(x - 4.5, -30.2), (x + 5.5, -30.6), (x + 7.5, -29.9)]):
        Pl.append(P(stance_pose((xx, yy), math.radians(85), 'stand'), 'GB', str(52 + i * 11), i + 1))
    Pl += fg_people(t, 'set')
    img = FG.draw_people(img, c, Pl, t)
    img = finish(img); d = ImageDraw.Draw(img)
    if lt < dur * 0.5:
        lower_third(d, 1180, 'TOM DEMPSEY #19', 'NO TOES ON HIS RIGHT FOOT', acc=NOG, t=lt)
    else:
        lower_third(d, 1180, 'TOM DEMPSEY #19', 'NO FINGERS ON HIS RIGHT HAND', acc=NOG, t=lt - dur * 0.5 + 0.35)
    return img

def S2(t, T0, T1):
    lt = t - T0
    hl = 0.5 + 0.5 * ease((lt - 1.0) / 0.8)
    img, Tm = shoe_shot(t, lt, ang=0.0, hl=hl)
    d = ImageDraw.Draw(img)
    if lt > 1.2:
        a = Tm(0.95, 0.72); b = Tm(1.01, 0.36)
        tele_arrow(d, a, b)
        d.text((a[0], a[1] - 50), 'FLAT FRONT', font=AF(80), fill=YEL, anchor='mm', stroke_width=6, stroke_fill=BLACK)
    lower_third(d, 1180, 'SPECIAL KICKING SHOE', 'FLAT, SQUARED-OFF FRONT', t=lt)
    return img

def S3(t, T0, T1):
    lt = t - T0; dur = T1 - T0
    img, c = wide_ez(t, k_desc=lt / dur)
    img = finish(img); d = ImageDraw.Draw(img)
    lower_third(d, 1180, 'TULANE STADIUM', 'NEW ORLEANS · NOVEMBER 8', acc=NOG, t=lt)
    return img

def S4(t, T0, T1):
    lt = t - T0
    img, c = sideline_cam(t, 42 + lt * 0.4, fg_people(t, 'set'), f=3200)
    img = finish(img); d = ImageDraw.Draw(img)
    score_bug(d, 17, 16, '4TH QTR')
    lower_third(d, 1180, 'SAINTS', 'VS. DETROIT LIONS', acc=NOG, t=lt)
    return img

def S5(t, T0, T1):
    lt = t - T0
    Pl = fg_people(t, 'set')
    Pl.append(P(holder_pose(0), 'GB', '42', 1))
    Pl.append(P(stance_pose((KICK_X - 3.0, 0.15), 0, 'stand'), 'GB', '19', 0))
    img, c = sideline_cam(t, 40.5 + lt * 0.2, Pl, f=3200)
    img = finish(img); d = ImageDraw.Draw(img)
    clock = '4TH  0:02'
    score_bug(d, 17, 16, clock, extra='2 SECONDS LEFT')
    return img

def S6(t, T0, T1):
    lt = t - T0
    Pl = fg_people(t, 'set')
    Pl.append(P(holder_pose(0), 'GB', '42', 1))
    Pl.append(P(stance_pose((KICK_X - 3.0, 0.15), 0, 'stand'), 'GB', '19', 0))
    img, c = sideline_cam(t, 39.5 + lt * 0.15, Pl, f=3300)
    virtual_line(img, c, KICK_X, (60, 140, 255), 150)
    img = finish(img); d = ImageDraw.Draw(img)
    score_bug(d, 17, 16, '4TH  0:02')
    lower_third(d, 1180, "SAINTS' OWN 37", 'THE SPOT OF THE HOLD', acc=NOG, t=lt)
    return img

def S7(t, T0, T1):
    lt = t - T0; dur = T1 - T0
    # plano de seguimiento: la camara recorre a la altura del balon las 63 yardas desde el punto del hold hasta los postes
    k = ease(clamp((lt - 0.15) / (dur - 0.35)))
    fx = lerp(KICK_X, 93, k)
    zc = 2.6 + 3.2 * math.sin(k * math.pi)
    c = cam((fx - 7.5, -2.2, zc), (fx + 14, 0.2, zc * 0.55 + 1.2), 1250)
    img = world(c)
    Pl = fg_people(t, 'set') + [P(holder_pose(0), 'GB', '42', 1), P(stance_pose((KICK_X - 3.0, 0.15), 0, 'stand'), 'GB', '19', 0)]
    Pl.append(ball_prop(np.array([KICK_X + 0.05, 0.28, 0.17]), np.array([0.05, 0, 1.0])))
    img = FG.draw_people(img, c, Pl, t)
    img = finish(img); d = ImageDraw.Draw(img)
    n = int(round(63 * k))
    B.headline(d, 560, f'{n} YARDS', 190, YEL)
    score_bug(d, 17, 16, '4TH  0:02')
    return img

def S8(t, T0, T1):
    lt = t - T0
    return bars(lt, [(56, 'NFL RECORD AT THE TIME', (230, 232, 236), 0.0), (63, 'THIS KICK?', NOG, 1.4)], 'THE RECORD')

def S9(t, T0, T1):
    lt = t - T0
    c = cam((50 + lt * 1.5, 12, 4), (52 + lt * 1.5, 60, 15), 1500)
    img = world(c)
    img = finish(img); d = ImageDraw.Draw(img)
    B.headline(d, 640, 'NOBODY THOUGHT', 120)
    B.headline(d, 780, 'IT WAS POSSIBLE', 120, YEL)
    return img

def S10(t, T0, T1):
    lt = t - T0
    s_ = kick_s(t)
    clock = '4TH  0:02' if s_ < 0.15 else '4TH  0:01' if s_ < 0.5 else '4TH  0:00'
    if s_ < 0.1:
        Pl, bp = kick_scene_people(t)
        img, c = sideline_cam(t, 40.0, Pl, f=3100)
    else:
        # plano de seguimiento del balon: camara detras y por encima, viajando con el
        bp = flight(s_); bq = flight(s_ + 0.05)
        dv = (bq - bp); dv = dv / np.linalg.norm(dv)
        k = ease(clamp((s_ - 0.1) / 0.12))
        pos = bp - dv * lerp(6, 8, k) + np.array([0, -2.6, lerp(1.8, 2.2, k)])
        look = bp + np.array([12, 0.6, -lerp(0.5, 3.5, k)])
        c = cam(pos, look, 1150)
        img = world(c)
        Pl, _ = kick_scene_people(t)
        Pl = [p for p in Pl if p['team'] != 'PROP']
        ax = np.array([math.cos(s_ * 40), 0, math.sin(s_ * 40) + 1e-3])
        Pl.append(ball_prop(bp, ax, 1.0))
        img = FG.draw_people(img, c, Pl, t)
    img = finish(img); d = ImageDraw.Draw(img)
    score_bug(d, 17, 16, clock)
    return img

def S11(t, T0, T1):
    lt = t - T0
    s = kick_s(t)
    img, c = endzone_cam_view(t, s if s < 1.25 else None, refs_up=clamp((s - 1.0) / 0.12), cheer=1.0 if s > 1 else 0.0)
    img = finish(img); d = ImageDraw.Draw(img)
    if s > 1.02:
        B.headline(d, 600, "IT'S GOOD!", 190, YEL)
        score_bug(d, 17, 19, 'FINAL', flash='NO')
    else:
        score_bug(d, 17, 16, '4TH  0:00')
    return img

def S12(t, T0, T1):
    lt = t - T0
    img = bars(lt + 1.5, [(56, 'OLD RECORD', (230, 232, 236), 0.0), (63, 'TOM DEMPSEY', NOG, 0.0)], '+7 YARDS', hi=1)
    return img

def S13(t, T0, T1):
    lt = t - T0
    img, Tm = shoe_shot(t, lt + 4, ang=-0.02, hl=0.8)
    d = ImageDraw.Draw(img)
    B.headline(d, 420, 'UNFAIR', 170, (255, 80, 70))
    B.headline(d, 590, 'ADVANTAGE?', 150, (255, 80, 70))
    return img

def S14(t, T0, T1):
    lt = t - T0; dur = T1 - T0
    img, Tm = shoe_shot(t, lt + 7, ang=-0.02, hl=0.8)
    img = Image.blend(img, Image.new('RGB', img.size, (8, 12, 22)), 0.25 * ease(lt / 0.6))
    d = ImageDraw.Draw(img)
    k = ease(lt / 0.5)
    y = 470 + int((1 - k) * 40)
    d.rounded_rectangle([90, y - 130, W - 90, y + 130], 18, fill=(12, 14, 22))
    d.rectangle([90, y - 130, W - 90, y - 118], fill=NOG)
    d.text((W // 2, y - 40), 'THE TOM DEMPSEY RULE', font=AF(92), fill=WHITE, anchor='mm')
    d.text((W // 2, y + 70), '1977', font=AF(110), fill=YEL, anchor='mm')
    if lt > dur * 0.2:
        lower_third(d, 1180, 'NEW RULES', 'FOR KICKING SHOES', t=lt - dur * 0.2)
    return img

def S15(t, T0, T1):
    lt = t - T0; dur = T1 - T0
    img, c = wide_ez(t, k_desc=1 - lt / dur * 0.5, z0=34, z1=16)
    img = finish(img); d = ImageDraw.Draw(img)
    n = int(round(lerp(0, 43, ease(lt / (dur * 0.7)))))
    B.headline(d, 600, 'RECORD STOOD', 120)
    B.headline(d, 770, f'{n} YEARS', 170, YEL)
    return img

def S16(t, T0, T1):
    lt = t - T0
    return bars(lt + 1.0, [(56, 'OLD RECORD', (230, 232, 236), 0.0), (63, 'TOM DEMPSEY', NOG, 0.0), (68, 'CAM LITTLE · 2025', DETB, 1.8)],
                'TODAY: 68 YARDS', hi=2)

def S17(t, T0, T1):
    lt = t - T0; dur = T1 - T0
    img, c = wide_ez(t, k_desc=1 - lt / dur, z0=34, z1=18)
    img = finish(img); d = ImageDraw.Draw(img)
    B.headline(d, 620, 'ONE FLAT SHOE', 150)
    B.headline(d, 780, 'NEW ORLEANS', 130, YEL)
    return img

LOGO = None
def S18(t, T0, T1):
    global LOGO
    lt = t - T0
    img = blurred_stadium('outro'); d = ImageDraw.Draw(img)
    if LOGO is None:
        LOGO = Image.open(os.path.join(HERE, 'logo.png')).convert('RGBA').resize((480, 480))
        m = Image.new('L', (480, 480), 0); ImageDraw.Draw(m).ellipse([0, 0, 479, 479], fill=255)
        LOGO.putalpha(m)
    k = ease(lt / 0.5)
    sz = int(480 * (0.8 + 0.2 * k)); lg = LOGO.resize((sz, sz))
    img.paste(lg, (W // 2 - sz // 2, 600 - sz // 2), lg)
    B.headline(d, 960, "TOMORROW'S STORY?", 120)
    d.rounded_rectangle([200, 1640, 880, 1760], 24, fill=YEL)
    d.text((W // 2, 1700), 'VOTE IN THE COMMENTS', font=BF(76), fill=BLACK, anchor='mm')
    by = 1800 + 8 * math.sin(lt * 6)
    d.polygon([(W // 2 - 30, by), (W // 2 + 30, by), (W // 2, by + 36)], fill=YEL)
    return img

SCENES = [S0, S1, S2, S3, S4, S5, S6, S7, S8, S9, S10, S11, S12, S13, S14, S15, S16, S17, S18]

def frame(t, subs=True):
    idx = len(TIMES) - 1
    for i in range(len(TIMES)):
        nxt = TIMES[i + 1][0] if i + 1 < len(TIMES) else 1e9
        if t < nxt: idx = i; break
    T0 = TIMES[idx][0] if idx > 0 else 0.0
    T1 = TIMES[idx + 1][0] if idx + 1 < len(TIMES) else TIMES[idx][1] + 1.5
    img = SCENES[idx](t, T0, T1)
    d = ImageDraw.Draw(img)
    B.watermark(d)
    if subs and idx < len(SCENES) - 1:
        B.draw_subs(d, t, CH)
    return img

def main():
    a = sys.argv[1:]
    mp3, out = a[0], a[1]
    dur = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', mp3]).strip())
    total = dur + 1.6
    if '--preview' in a or '--test' in a:
        key = '--preview' if '--preview' in a else '--test'
        ts = [float(x) for x in a[a.index(key) + 1].split(',')]
        for k, t in enumerate(ts):
            frame(t).save(out.replace('.mp4', f'_p{k:02d}.jpg'), quality=88)
        return
    if '--cover' in a:
        frame(float(a[a.index('--cover') + 1]), subs=False).save(out, quality=93)
        return
    n = int(total * FPS)
    i0, i1 = 0, n
    if '--range' in a:
        i0 = int(a[a.index('--range') + 1]); i1 = min(n, int(a[a.index('--range') + 2]))
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                          '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
    for i in range(i0, i1):
        p.stdin.write(frame(i / FPS).tobytes())
        if i % 150 == 0: print(f'{i}/{i1}', flush=True)
    p.stdin.close(); p.wait()

if __name__ == '__main__':
    main()
