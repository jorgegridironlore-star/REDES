#!/usr/bin/env python3
"""Gridiron Lore 06 - Miracle at the New Meadowlands (19 dic 2010). Motor del 04/05 (engine04 + figures).
Uso: python3 render_gridiron_lore_06.py voz.mp3 out.mp4 [--preview t1,t2,...] [--cover t] [--range a b]"""
import sys, json, math, random, subprocess, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import engine04 as E
from engine04 import (Cam, render_world, pose_joints, run_pose, stance_pose, blend, UP, ease, lerp, clamp, mix, shade)
import figures as FG
import base03 as B
import metlife as ML

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
SS = 1.5
SW, SH = int(W * SS), int(H * SS)
YEL = (255, 204, 41); WHITE = (255, 255, 255); BLACK = (0, 0, 0)
NYB = (12, 36, 96); NYR = (196, 30, 44); PHG = (0, 76, 84); PHS = (165, 172, 175)

SCRIPT = [l.strip() for l in open(os.path.join(HERE, 'gridiron_lore_06_guion.txt')) if l.strip()]
TIMES = json.load(open(os.path.join(HERE, 'times.json')))
SEGS = json.load(open(os.path.join(HERE, 'times_segs.json')))
CH = B.chunks(B.build_words(TIMES, SEGS))

def AF(sz): return B.F(B.ANTON, int(sz))
def BF(sz): return B.F(B.BEBAS, int(sz))

def watermark(d):
    d.text((W // 2, 150), '@nflgridironlore', font=AF(50), fill=WHITE, anchor='mm', stroke_width=4, stroke_fill=BLACK)
B.watermark = watermark

# ---------------------------------------------------------------- 2010: equipos sin logos. 'GB' = Giants (local), 'DAL' = Eagles (blanco)
E.TEAM['GB'] = dict(helmet=(22, 40, 98), hstripe=[(196, 30, 44)], mask=(150, 150, 154),
                    jersey=(14, 38, 100), num=(245, 245, 245), numout=(196, 30, 44), sleeve=[(196, 30, 44), (245, 245, 245)],
                    pants=(170, 174, 178), pstripe=[(196, 30, 44), (14, 38, 100)], sock=(14, 38, 100), sockstripe=(196, 30, 44),
                    shoe=(20, 20, 22), skin=None)
E.TEAM['DAL'] = dict(helmet=(0, 72, 80), hstripe=[], mask=(40, 40, 42),
                     jersey=(244, 244, 242), num=(0, 76, 84), numout=(20, 20, 22), sleeve=[(0, 76, 84), (20, 20, 22)],
                     pants=(236, 236, 234), pstripe=[(0, 76, 84)], sock=(0, 76, 84), sockstripe=(244, 244, 242),
                     shoe=(20, 20, 22), skin=None)
E.TEAM['COACH'] = dict(helmet=None, coat=(20, 28, 54), furhat=(16, 22, 44), pants=(36, 36, 40), shoe=(18, 18, 18))
# publico de diciembre en Nueva Jersey: mucho azul, rojo, negro y gris
E.COATS = [(18, 40, 104), (22, 46, 112), (24, 24, 28), (170, 30, 40), (90, 92, 98), (30, 34, 60), (236, 236, 232),
           (16, 36, 96), (60, 62, 70), (0, 76, 84), (40, 40, 46), (190, 34, 44), (22, 46, 112), (120, 122, 128)]
E.HATS = [(18, 40, 104), (196, 30, 44), (24, 24, 28), (236, 236, 232), (120, 120, 126), (18, 40, 104), (0, 76, 84),
          (196, 30, 44), (40, 40, 46), (22, 46, 112)]

def make_ground6(seed=3):
    """Cesped artificial de 2010: verde uniforme con franjas suaves, numeros, hashes NFL y zonas de anotacion lisas."""
    GX0, GX1, GY0, GY1, GPX = E.GX0, E.GX1, E.GY0, E.GY1, E.GPX
    FW = E.FIELD_W
    rng = np.random.default_rng(seed)
    Wd = int((GX1 - GX0) * GPX); Hd = int((GY1 - GY0) * GPX)
    def X(x): return (x - GX0) * GPX
    def Y(y): return (y - GY0) * GPX
    n1 = rng.random((Hd // 12 + 2, Wd // 12 + 2)).astype(np.float32)
    n1 = np.array(Image.fromarray((n1 * 255).astype(np.uint8)).resize((Wd, Hd), Image.BICUBIC), np.float32) / 255
    n3 = rng.random((Hd, Wd)).astype(np.float32)
    xs = (np.arange(Wd) / GPX + GX0)
    stripe = ((np.floor(xs / 5) % 2) * 0.05)[None, :]
    grass = np.array([46, 118, 56], np.float32)
    base = grass[None, None, :] * (0.92 + 0.06 * n1[..., None] + stripe[..., None] + 0.08 * (n3[..., None] - 0.5))
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    lw = max(2, int(GPX * 0.11)); white = (242, 244, 244)
    for x in range(0, 101, 5):
        d.line([X(x), Y(-FW / 2), X(x), Y(FW / 2)], fill=white, width=lw if x % 10 else lw + 1)
    for x in (-10, 110):
        d.line([X(x), Y(-FW / 2), X(x), Y(FW / 2)], fill=white, width=lw)
    for y in (-FW / 2, FW / 2):
        d.line([X(-10), Y(y), X(110), Y(y)], fill=white, width=lw + 4)
    for x in range(1, 100):
        if x % 5 == 0: continue
        for y in (-FW / 2 + 0.3, FW / 2 - 0.9, -3.08, 3.08 - 0.6):
            d.line([X(x), Y(y), X(x), Y(y + 0.6)], fill=white, width=lw)
    for x in (2.0, 98.0):   # marca del punto extra
        d.line([X(x), Y(-0.33), X(x), Y(0.33)], fill=white, width=lw)
    fnt = E.font('Anton-Regular.ttf', GPX * 2.0)
    for x in range(10, 100, 10):
        n = x if x <= 50 else 100 - x
        for y, rot in ((-FW / 2 + 12, 180), (FW / 2 - 12, 0)):
            t = Image.new('L', (int(GPX * 5), int(GPX * 3)), 0)
            ImageDraw.Draw(t).text((t.size[0] / 2, t.size[1] / 2), str(n), font=fnt, fill=235, anchor='mm')
            t = t.rotate(rot + 90, expand=True).transpose(Image.FLIP_TOP_BOTTOM)
            img.paste(Image.new('RGB', t.size, white), (int(X(x) - t.size[0] / 2), int(Y(y) - t.size[1] / 2)), t)
    # zonas de anotacion: verde algo mas oscuro con borde blanco
    for (x0, x1) in ((-10, 0), (100, 110)):
        d.rectangle([X(x0) + lw, Y(-FW / 2) + lw, X(x1) - lw, Y(FW / 2) - lw], fill=(38, 102, 50))
        d.line([X(x0), Y(-FW / 2 + 0.6), X(x1), Y(-FW / 2 + 0.6)], fill=white, width=lw)
        d.line([X(x0), Y(FW / 2 - 0.6), X(x1), Y(FW / 2 - 0.6)], fill=white, width=lw)
    # fuera del campo: banda de cesped artificial mas oscuro
    for (x0, x1) in ((GX0, -10.3), (110.3, GX1)):
        d.rectangle([X(x0), 0, X(x1), Hd], fill=(40, 92, 52))
    for (y0, y1) in ((GY0, -FW / 2 - 0.4), (FW / 2 + 0.4, GY1)):
        d.rectangle([0, Y(y0), Wd, Y(y1)], fill=(40, 92, 52))
    # zona del banquillo (rectangulo amarillo de la zona de entrenadores)
    for y in (-FW / 2 - 2.0, FW / 2 + 2.0):
        d.line([X(32), Y(y), X(68), Y(y)], fill=(236, 214, 70), width=lw)
    return img.filter(ImageFilter.GaussianBlur(0.5))

_gp = os.path.join(HERE, 'cache_ground06.png')
if os.path.exists(_gp): E.GROUND = Image.open(_gp).convert('RGB')
else:
    E.GROUND = make_ground6(); E.GROUND.save(_gp)

def cam(pos, look, f, roll=0.0):
    return Cam(pos, look, f * SS, SW, SH, roll)

def world(c, cheer=0.0):
    img = ML.render_world_metlife(c, cheer=cheer)
    d = ImageDraw.Draw(img)
    E.goalpost(d, c, -10); E.goalpost(d, c, 110)   # postes de horquilla en la linea de fondo (desde 1974)
    return img

def finish(img):
    return img.resize((W, H), Image.LANCZOS)

def P(J, team, num='', skin=0, **kw):
    p = dict(J=J, team=team, num=num, skin=skin); p.update(kw); return p

def carrier(x, y, yaw, phase, team, num, skin=0, speed=1.0, ball=True):
    J = run_pose((x, y), yaw, phase, speed=speed, carry='R' if ball else None)
    bp = J['elR'] * 0.45 + J['wrR'] * 0.55 + J['f'] * 0.04 if ball else None
    return P(J, team, num, skin, ball=bp)

# ---------------------------------------------------------------- graficos de TV
def score_bug(d, nyg, phi, clock='4TH  8:17', extra=None, flash=None, y=232):
    x0 = 60; f = BF(54)
    d.rounded_rectangle([x0, y, W - 60, y + 76], 8, fill=(12, 14, 22))
    fl = flash == 'PHI'
    d.rectangle([x0 + 10, y + 8, x0 + 330, y + 68], fill=PHG if not fl else YEL)
    d.text((x0 + 28, y + 38), 'EAGLES', font=f, fill=WHITE if not fl else BLACK, anchor='lm')
    d.text((x0 + 312, y + 38), str(phi), font=f, fill=WHITE if not fl else BLACK, anchor='rm')
    fl = flash == 'NYG'
    d.rectangle([x0 + 340, y + 8, x0 + 660, y + 68], fill=NYB if not fl else YEL)
    d.rectangle([x0 + 340, y + 8, x0 + 348, y + 68], fill=NYR)
    d.text((x0 + 362, y + 38), 'GIANTS', font=f, fill=WHITE if not fl else BLACK, anchor='lm')
    d.text((x0 + 642, y + 38), str(nyg), font=f, fill=WHITE if not fl else BLACK, anchor='rm')
    d.text((x0 + 810, y + 38), clock, font=f, fill=YEL, anchor='mm')
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

def tele_arrow(d, pts, col=YEL, w=12, head=34):
    d.line(pts, fill=col, width=w, joint='curve')
    (ax, ay), (bx, by) = pts[-2], pts[-1]
    ang = math.atan2(by - ay, bx - ax)
    d.polygon([(bx + head * math.cos(ang), by + head * math.sin(ang)), (bx + head * .85 * math.cos(ang + 2.3), by + head * .85 * math.sin(ang + 2.3)),
               (bx + head * .85 * math.cos(ang - 2.3), by + head * .85 * math.sin(ang - 2.3))], fill=col)

def ball_prop(bp, ax, k=1.0, bias=0.0):
    ax = np.asarray(ax, float); ax = ax / np.linalg.norm(ax)
    def draw(C, L, c_):
        A = bp - ax * 0.12 * k; Bq = bp + ax * 0.12 * k
        FG.cone(C, c_, A, bp, .02 * k, .085 * k, (120, 62, 30), L, spec=.3)
        FG.cone(C, c_, bp, Bq, .085 * k, .02 * k, (120, 62, 30), L, spec=.3)
    return dict(J={'pelvis': bp}, team='PROP', prims=lambda c_: [(c_.depth(bp) - bias, lambda C, L: draw(C, L, c_))])

# ================================================================ LA JUGADA FINAL (simulada una vez, determinista)
T10 = TIMES[10][0]
T_SNAP = T10 + 0.55
T_KICK = T_SNAP + 1.45
T_ARR = T_KICK + 2.9          # el balon llega a Jackson (su 35)
T_GO = TIMES[12][0] - 0.3      # arranca (tras recogerlo y retroceder hasta su 30)
LOS = 71.0; PUNTER_X = 84.0     # los Giants despejan desde su 29
JX0, JY0 = 35.0, 1.0
T_GL = T_GO + 6.85             # llega a la linea de gol por la banda cercana
T_IN = TIMES[15][0] + 0.35     # entra en la end zone
T_THROW = T_IN + 1.0           # tira el balon a la grada
T_BLK = T_GO + 2.3             # Avant bloquea a DeOssie en la 46 de los Giants
# Fuentes: muff en su 35 y retrocede a su 30; atraviesa un grupo de Giants hasta medio campo; bloqueo de Avant
# en la 46; sube por la banda con el brazo en alto; corre paralelo a la linea de gol casi todo el ancho; entra.
JWP = [(0, JX0, JY0), (T_ARR + 0.9, JX0 + 0.6, JY0), (T_ARR + 1.3, JX0 + 0.5, 0.9), (T_GO, 30.0, 0.0),
       (T_GO + 2.0, 50.0, -5.0), (T_GO + 2.95, 59.5, -12.5), (T_GO + 3.95, 69.0, -21.0), (T_GL, 98.9, -23.0),
       (T_IN - 0.5, 99.2, 13.0), (T_IN + 0.3, 101.8, 13.6), (T_IN + 0.9, 103.0, 13.9), (999, 103.0, 13.9)]
_RUN = (T_GO, T_GL)

def jpos(t):
    for (t0, x0, y0), (t1, x1, y1) in zip(JWP[:-1], JWP[1:]):
        if t <= t1:
            u = clamp((t - t0) / (t1 - t0))
            if t0 >= T_GO + 0.5 and t1 <= T_GL + 0.01:
                u = u   # carrera: velocidad constante por tramos
            else:
                u = ease(u)
            return np.array([lerp(x0, x1, u), lerp(y0, y1, u)])
    return np.array(JWP[-1][1:])

DT = 1 / FPS
TS = np.arange(T10 - 0.5, TIMES[17][0] + 0.2, DT)
JP = np.array([jpos(t) for t in TS])

def _idx(t): return int(clamp((t - TS[0]) / DT, 0, len(TS) - 1))

# cobertura de los Giants (punt team) y Eagles (rushers / bloqueadores)
rng = random.Random(6)
COV0 = [(LOS + 0.9, y) for y in (-3.4, -2.3, -1.15, 1.15, 2.3, 3.4)] + [(LOS + 0.9, -20.0), (LOS + 0.9, 20.0), (LOS + 4.5, -1.6), (LOS + 4.5, 1.6)]
COV_OFF = [(-1.5, -4.5), (-1.0, 3.5), (0.5, -6.5), (0.0, 6.0), (1.0, -3.0), (1.2, 2.5), (-2.0, -8.0), (-2.5, 8.5), (2.0, -5.0), (2.4, 4.6)]
COV_NUM = ['57', '67', '61', '69', '64', '66', '31', '23', '44', '52']
RUSH0 = [(LOS - 0.9, y) for y in (-4.0, -2.8, -1.6, -0.5, 0.6, 1.8, 3.0, 4.2)] + [(LOS - 1.0, -19.0), (LOS - 1.0, 19.0)]
RUSH_OFF = [(5, -3), (7, 3), (9, -6), (11, 5), (13, -2), (14, 7), (16, -8), (18, 1), (20, -4), (22, 6)]
RUSH_NUM = ['94', '91', '97', '58', '50', '95', '54', '29', '24', '21']

def simulate():
    cov = np.array(COV0, float); rush = np.array(RUSH0, float)
    CP, RP = [], []
    for i, t in enumerate(TS):
        j = JP[i]
        if t > T_KICK + 0.25:
            if t < T_ARR: sp, md = 7.4, 6.0
            elif t < T_GO: sp, md = 2.2, 7.0          # frenados por los bloqueos de los Eagles
            elif t < T_GL: sp, md = 7.6, 3.2
            else: sp, md = 3.5, 8.0                   # ya no le alcanzan
            sp *= DT
            for k in range(len(cov)):
                tgt = j + np.array(COV_OFF[k]) * (0.5 if t > T_ARR else 1.6)
                if t > T_GO and cov[k, 0] < j[0] - 1.0:      # ya les ha superado: persecucion por detras
                    tgt = j + np.array([-6.0 - k * 1.2, COV_OFF[k][1] * 0.8])
                v = tgt - cov[k]; n = np.linalg.norm(v)
                if n > 1e-6: cov[k] += v / n * min(sp, n)
                dj = cov[k] - j; nd = np.linalg.norm(dj)
                if nd < md: cov[k] = j + dj / (nd + 1e-6) * md
            spr = 8.6 * DT
            for k in range(len(rush)):
                if t < T_GO:
                    tgt = np.array([j[0] + RUSH_OFF[k][0] * 0.9, RUSH_OFF[k][1] * 1.6])
                elif t < T_GL - 1.5:
                    tgt = j + np.array(RUSH_OFF[k]) * np.array([0.45, 0.9])
                elif t < T_IN + 0.5:                   # en la linea de gol se quedan detras de el
                    tgt = j + np.array([-4.0 - RUSH_OFF[k][0] * 0.35, -abs(RUSH_OFF[k][1]) * 1.1 - 2])
                else:                                  # celebran juntos en la end zone
                    tgt = j + np.array([-1.5 + (k % 3), RUSH_OFF[k][1] * 0.35])
                v = tgt - rush[k]; n = np.linalg.norm(v)
                if n > 1e-6: rush[k] += v / n * min(spr, n)
                dj = rush[k] - j; nd = np.linalg.norm(dj)
                if nd < 2.5: rush[k] = j + dj / (nd + 1e-6) * 2.5
        CP.append(cov.copy()); RP.append(rush.copy())
    return np.array(CP), np.array(RP)

CP, RP = simulate()

def _motion(arr, i):
    a = arr[max(0, i - 3)]; b = arr[min(len(arr) - 1, i + 3)]
    v = (b - a) / (6 * DT)
    return v

def _cumdist(arr):
    dd = np.linalg.norm(np.diff(arr, axis=0), axis=-1)
    return np.concatenate([np.zeros((1,) + dd.shape[1:]), np.cumsum(dd, axis=0)], axis=0)
CD_C = _cumdist(CP); CD_R = _cumdist(RP); CD_J = _cumdist(JP)

def runner_from(pos, vel, dist, team, num, skin, face_default, ball=False):
    sp = np.linalg.norm(vel)
    if sp < 0.6:
        J = stance_pose((pos[0], pos[1]), face_default, 'ready')
        return P(J, team, num, skin)
    yaw = math.atan2(vel[1], vel[0])
    k = clamp(sp / 8.0, 0.35, 1.0)
    return carrier(pos[0], pos[1], yaw, dist / 2.3, team, num, skin, speed=k, ball=ball)

def punt_ball(t):
    """(posicion, eje) del balon en la jugada del punt antes de que Jackson lo controle; None si lo lleva Jackson."""
    if t < T_SNAP:
        return np.array([LOS - 0.1, 0.0, 0.12]), np.array([1.0, 0, 0.05])
    if t < T_SNAP + 0.6:                      # snap alto
        u = (t - T_SNAP) / 0.6
        return np.array([lerp(LOS, PUNTER_X - 0.4, u), lerp(0, 0.35, u), 0.3 + lerp(0, 2.0, u) + 2.2 * math.sin(u * math.pi)]), np.array([1.0, 0, 0.3])
    if t < T_KICK:
        u = ease((t - T_SNAP - 0.6) / (T_KICK - T_SNAP - 0.6))
        return np.array([PUNTER_X - 0.4 - 0.9 * u, 0.35, lerp(2.3, 0.75, u)]), np.array([-1.0, 0, 0.2])
    if t < T_ARR:                             # line drive bajo
        u = (t - T_KICK) / (T_ARR - T_KICK)
        x = lerp(PUNTER_X - 1.6, JX0 + 0.45, u); y = lerp(0.35, JY0, u)
        z = lerp(0.8, 1.25, u) + 4 * 8.5 * u * (1 - u)
        return np.array([x, y, z]), np.array([-1.0, 0.05 * math.sin(t * 30), 0.15 * math.cos(t * 30)])
    lb = t - T_ARR
    if lb < 0.55:                             # rebota en sus manos
        return np.array([JX0 + 0.45 + 0.5 * lb, JY0, 1.25 + 0.55 * math.sin(lb / 0.55 * math.pi)]), np.array([math.cos(lb * 14), 0.2, math.sin(lb * 14)])
    if lb < 0.9:                              # cae al cesped
        u = (lb - 0.55) / 0.35
        return np.array([JX0 + 0.72 + 0.2 * u, JY0 - 0.1 * u, lerp(1.25, 0.12, u * u)]), np.array([math.cos(lb * 10), 0.3, math.sin(lb * 10)])
    if lb < 1.15:
        return np.array([JX0 + 0.95, JY0 - 0.1, 0.12]), np.array([0.3, 1.0, 0.05])
    if t > T_THROW:                           # vuela a la grada detras de la end zone
        u = clamp((t - T_THROW) / 1.1)
        j = JP[_idx(T_THROW)]
        return np.array([lerp(j[0] + 0.3, 126.0, u), lerp(j[1], j[1] + 6, u), 2.3 + 10 * u - 3 * u * u]), np.array([1.0, 0.1, 0.3])
    return None, None

def jackson_person(t):
    i = _idx(t); pos = JP[i]
    lb = t - T_ARR
    if t < T_ARR - 0.6:
        J = stance_pose((pos[0], pos[1]), 0.0, 'ready')
        return P(J, 'DAL', '10', 2)
    if t < T_ARR + 0.6:                       # brazos arriba para atraparlo
        a = 1.25 + 0.25 * math.sin(max(0, lb) * 18)
        J = pose_joints((pos[0], pos[1]), 0.0, pitch=0.12, legs=((0.3, 0.45), (0.15, 0.3)), arms=((a, 0.9, 0.1), (a, 0.9, 0.1)), head_pitch=-0.1)
        return P(J, 'DAL', '10', 2)
    if t < T_ARR + 1.35:                      # se agacha a recogerlo
        u = ease((lb - 0.6) / 0.5) * (1 - ease((lb - 1.15) / 0.2))
        J = pose_joints((pos[0], pos[1]), 0.0, pitch=lerp(0.2, 1.05, u), legs=((lerp(0.4, 1.2, u), lerp(0.5, 1.5, u)), (lerp(0.2, 0.6, u), lerp(0.3, 0.9, u))),
                        arms=((lerp(0.8, 1.3, u), 0.5, 0.05), (lerp(0.8, 1.3, u), 0.5, 0.05)))
        return P(J, 'DAL', '10', 2)
    if t < T_GO:                              # da unos pasos atras con el balon
        u = (t - T_ARR - 1.35)
        J = run_pose((pos[0], pos[1]), 0.0, -u * 1.6, speed=0.35, carry='R')
        return P(J, 'DAL', '10', 2, ball=J['elR'] * 0.45 + J['wrR'] * 0.55 + J['f'] * 0.04)
    v = _motion(JP, i)
    if t > T_THROW - 0.35:                    # tira el balon a la grada y celebra
        k = clamp((t - T_THROW + 0.35) / 0.35)
        J = pose_joints((pos[0], pos[1]), 0.15, pitch=lerp(-0.1, 0.15, k), legs=((0.3, 0.2), (-0.2, 0.3)),
                        arms=((0.6, 0.3, 0.2), (lerp(2.9, 1.4, k), lerp(1.4, 0.1, k), 0.15)))
        bl = None if t > T_THROW else J['wrR'] + UP * 0.08
        return P(J, 'DAL', '10', 2, ball=bl)
    if T_GO + 2.6 < t < T_GL - 0.25:          # por la banda, con el brazo en alto
        Pp = runner_from(pos, v, CD_J[i], 'DAL', '10', 2, 0.0, ball=True)
        J = Pp['J']; sh = J['shL']
        J['elL'] = sh + UP * 0.32 + J['f'] * 0.05; J['wrL'] = J['elL'] + UP * 0.3 + J['f'] * 0.04
        return Pp
    if T_GL - 0.2 < t < T_IN - 0.4:           # bailando por la linea de gol, mirando atras
        yaw = math.atan2(v[1], v[0])
        J = run_pose((pos[0], pos[1]), yaw, CD_J[i] / 2.0, speed=0.55, carry='R', lean=0.05)
        return P(J, 'DAL', '10', 2, ball=J['elR'] * 0.45 + J['wrR'] * 0.55 + J['f'] * 0.04)
    return runner_from(pos, v, CD_J[i], 'DAL', '10', 2, 0.0, ball=True)

def punt_people(t, include_cov=True):
    i = _idx(t)
    Pl = []
    snapped = t > T_SNAP
    if t < T_KICK + 0.25:
        for k, (x, y) in enumerate(COV0):
            if abs(y) > 10:
                J = stance_pose((x, y), math.pi, 'ready') if not snapped else run_pose((x - (t - T_SNAP) * 3.5, y), math.pi, (t - T_SNAP) * 2, speed=0.8)
            else:
                J = stance_pose((x, y), math.pi, 'block' if snapped else ('3pt' if x < LOS + 2 else 'ready'))
            Pl.append(P(J, 'GB', COV_NUM[k], k))
        for k, (x, y) in enumerate(RUSH0):
            if snapped:
                J = pose_joints((x - 0.3 + (t - T_SNAP) * 0.6, y), 0.0, pitch=0.6, legs=((0.7, 0.9), (0.1, 0.3)), arms=((2.4, 0.3, 0.3), (2.4, 0.3, 0.3)))
            else:
                J = stance_pose((x, y), 0.0, '3pt' if abs(y) < 10 else 'ready')
            Pl.append(P(J, 'DAL', RUSH_NUM[k], k + 1))
    else:
        for k in range(len(COV0)):
            Pl.append(runner_from(CP[i, k], _motion(CP[:, k], i), CD_C[i, k], 'GB', COV_NUM[k], k, math.pi))
        for k in range(len(RUSH0)):
            if k == 3: continue
            Pl.append(runner_from(RP[i, k], _motion(RP[:, k], i), CD_R[i, k], 'DAL', RUSH_NUM[k], k + 1, math.pi))
        Pl += block_pair(t)
    # long snapper Zak DeOssie (#51)
    if t < T_KICK + 0.25:
        Pl.append(P(stance_pose((LOS + 0.5, 0.0), math.pi, 'block' if snapped else '3pt'), 'GB', '51', 3))
    # punter (de espaldas a la camara de banda, mira hacia x-)
    if t < T_SNAP + 0.3:
        J = stance_pose((PUNTER_X, 0.35), math.pi, 'ready')
    elif t < T_SNAP + 0.65:
        J = pose_joints((PUNTER_X, 0.35), math.pi, pitch=-0.05, legs=((0.05, 0.1), (-0.05, 0.1)), arms=((2.7, 0.2, 0.1), (2.7, 0.2, 0.1)))
    elif t < T_KICK + 0.6:
        k = clamp((t - T_SNAP - 0.65) / (T_KICK + 0.1 - T_SNAP - 0.65))
        if k < 0.6:
            J = run_pose((PUNTER_X - 1.2 * k, 0.35), math.pi, k * 2.2, speed=0.5)
        else:
            sw = ease((k - 0.6) / 0.4)
            J = pose_joints((PUNTER_X - 0.75, 0.35), math.pi, pitch=lerp(0.1, -0.25, sw), legs=((0.1, 0.25), (lerp(-0.4, 1.9, sw), lerp(1.2, 0.05, sw))),
                            arms=((0.9, 0.3, 0.5), (0.9, 0.3, 0.5)))
    else:
        J = run_pose((PUNTER_X - 0.75 - (t - T_KICK - 0.6) * 5, 0.35), math.pi, (t - T_KICK) * 2, speed=0.6)
    Pl.append(P(J, 'GB', '', 4))
    Pl.append(jackson_person(t))
    bp, ax = punt_ball(t)
    if bp is not None:
        Pl.append(ball_prop(bp, ax, 1.6, 0.3))
    return Pl

def _path(t, pts):
    for (t0, x0, y0), (t1, x1, y1) in zip(pts[:-1], pts[1:]):
        if t <= t1:
            u = clamp((t - t0) / (t1 - t0)); return np.array([lerp(x0, x1, u), lerp(y0, y1, u)]), np.array([x1 - x0, y1 - y0]) / max(1e-3, t1 - t0)
    return np.array(pts[-1][1:]), np.zeros(2)

DEO = [(T_KICK + 0.25, LOS + 0.5, 0.0), (T_GO, 60.0, -1.0), (T_BLK, 54.6, -3.4), (999, 54.6, -3.4)]
AVA = [(T_KICK + 0.25, LOS - 1.0, -0.5), (T_ARR, 62.0, -2.0), (T_GO + 1.2, 52.5, -4.6), (T_BLK, 54.0, -3.8), (999, 54.0, -3.8)]
def block_pair(t):
    """Jason Avant (#81) bloquea a Zak DeOssie (#51) en la 46 de los Giants: los dos acaban en el suelo."""
    out = []
    for path, team, num, yaw_down, sk in ((DEO, 'GB', '51', math.pi, 3), (AVA, 'DAL', '81', 0.0, 4)):
        pos, vel = _path(t, path)
        if t < T_BLK - 0.15:
            sp = np.linalg.norm(vel)
            yaw = math.atan2(vel[1], vel[0]) if sp > 0.5 else yaw_down
            out.append(carrier(pos[0], pos[1], yaw, t * 2.3, team, num, sk, speed=clamp(sp / 8, 0.4, 1.0), ball=False))
        else:
            k = ease((t - T_BLK + 0.15) / 0.45)
            yaw = math.pi * 0.9 if team == 'GB' else 0.15
            z = lerp(0.98, 0.32, k); pitch = lerp(0.4, 1.45, k) * (1 if team == 'DAL' else -1)
            J = pose_joints((pos[0], pos[1], z), yaw, pitch=pitch, legs=((lerp(0.4, 0.2, k), 0.4), (lerp(0.2, 0.1, k), 0.3)),
                            arms=((lerp(1.4, 2.6, k), 0.4, 0.4), (lerp(1.4, 2.4, k), 0.3, 0.4)), ground=False)
            out.append(P(J, team, num, sk))
    return out

def game_clock(t):
    if t < T_ARR: return '4TH  0:14'
    s = max(0, int(math.ceil(14 - (t - T_ARR) - 1e-6)))
    return f'4TH  0:{s:02d}'

# ---------------------------------------------------------------- formaciones genericas
def scrimmage(xl, off='DAL', dirn=1, snapped=False, nums=None):
    """Linea de scrimmage en xl; el ataque (off) avanza hacia dirn (+1 = x creciente)."""
    dfn = 'GB' if off == 'DAL' else 'DAL'
    yo = 0.0 if dirn > 0 else math.pi; yd = math.pi - yo
    Pl = []
    on = ['72', '79', '62', '69', '68', '87', '18'] if off == 'DAL' else ['66', '76', '60', '74', '67', '85', '80']
    for i, y in enumerate([-3.4, -2.3, -1.15, 0, 1.15, 2.3, 3.4]):
        Pl.append(P(stance_pose((xl - 0.9 * dirn, y), yo, 'block' if snapped else '3pt'), off, on[i], i))
    Pl.append(P(stance_pose((xl - 5.0 * dirn, 0.2), yo, 'qb'), off, '7' if off == 'DAL' else '10', 2))
    Pl.append(P(stance_pose((xl - 1.2 * dirn, -12), yo, 'ready'), off, '10' if off == 'DAL' else '81', 3))
    dn = ['91', '98', '75', '90', '55', '58', '59', '21', '29', '24', '20']
    for i, y in enumerate([-3.0, -1.2, 1.2, 3.0]):
        Pl.append(P(stance_pose((xl + 0.9 * dirn, y), yd, '3pt'), dfn, dn[i], i + 1))
    for i, y in enumerate([-4.5, 0.0, 4.5]):
        Pl.append(P(stance_pose((xl + 4.5 * dirn, y), yd, 'ready'), dfn, dn[4 + i], i))
    for i, y in enumerate([-12, 11]):
        Pl.append(P(stance_pose((xl + 7 * dirn, y), yd, 'ready'), dfn, dn[7 + i], i + 2))
    return Pl

def chase(rx, ry, t, n, team, lag=3.0, seed=1, spread=4.0):
    r = random.Random(seed); Pl = []
    for k in range(n):
        dx = -lag - k * 1.6 - r.uniform(0, 1.2); dy = r.uniform(-spread, spread)
        Pl.append(carrier(rx + dx, ry + dy, 0.0, t * 1.9 + k * 0.3, team, ['21', '24', '29', '55'][k % 4], k, speed=0.9, ball=False))
    return Pl

def tracking_cam(x, y, z=9.0, back=16, side=-40, f=2700, lz=0.6):
    return cam((x - back, side, z), (x + 2, y * 0.6, lz), f)

# ---------------------------------------------------------------- vistas
def wide_ez(t, k_desc=0.0, cheer=0.0, z0=26, z1=14):
    z = lerp(z0, z1, ease(k_desc))
    c = cam((-18 + 4 * k_desc, -5 + 5 * k_desc, z), (38, 0, -6), 1150)
    return world(c, cheer=cheer), c

BG_CACHE = {}
def blurred_stadium(key='bars'):
    if key not in BG_CACHE:
        img, c = wide_ez(0, 1.0)
        img = finish(img).filter(ImageFilter.GaussianBlur(16))
        BG_CACHE[key] = Image.blend(img, Image.new('RGB', img.size, (8, 12, 22)), 0.5)
    return BG_CACHE[key].copy()

def goal_line_view(t, cheer=0.0, refs_up=0.0):
    """Camara alta detras de la end zone de los Giants (x=110), mirando a la linea de gol."""
    j = JP[_idx(t)]
    yy = clamp(j[1], -21, 12)
    c = cam((125, yy - 13, 7.5), (98.5, yy, 0.4), 3000)
    img = world(c, cheer=cheer)
    Pl = punt_people(t)
    for sg in (1, -1):
        a = lerp(0.05, 2.95, ease(refs_up))
        Pl.append(P(pose_joints((100.6, sg * 9.5), math.pi, legs=((0.06, 0.08), (-0.06, 0.08)), arms=((a, 0.1, 0.1), (a, 0.1, 0.1))), 'REF', skin=sg + 2))
    img = FG.draw_people(img, c, Pl, t)
    return img, c

# ---------------------------------------------------------------- escenas por frase
def S0(t, T0, T1):
    # gancho: el final de la jugada (Jackson por la linea de gol) mientras se anuncia el desenlace
    lt = t - T0
    tt = T_GL + 0.6 + lt * 0.7
    img, c = goal_line_view(tt)
    img = finish(img); d = ImageDraw.Draw(img)
    t2 = SEGS[0][1][0] if len(SEGS[0]) > 1 else T1 - 1.2
    if t < t2 - 0.1:
        B.headline(d, 420, 'UP 21 POINTS', 150)
        B.headline(d, 580, '8 MINUTES LEFT', 130, YEL)
    else:
        B.headline(d, 480, 'THEY STILL', 160)
        B.headline(d, 650, 'LOST', 210, (255, 80, 70))
    return img

def S1(t, T0, T1):
    lt = t - T0; dur = T1 - T0
    img, c = wide_ez(t, k_desc=lt / dur)
    img = finish(img); d = ImageDraw.Draw(img)
    lower_third(d, 1180, 'THE NEW MEADOWLANDS', 'EAST RUTHERFORD, N.J. · DECEMBER 19', acc=NYR, t=lt)
    return img

def S2(t, T0, T1):
    lt = t - T0
    Pl = scrimmage(40, 'GB', -1)
    c = cam((40 - 18 + lt * 0.5, -40, 8), (41 + lt * 0.5, 0.5, -0.4), 3000)
    img = FG.draw_people(world(c), c, Pl, t)
    img = finish(img); d = ImageDraw.Draw(img)
    lower_third(d, 1180, 'GIANTS VS. EAGLES', 'WEEK 15', acc=PHG, t=lt)
    return img

def throw_pose(x, y, yaw, k):
    """Lanzamiento del QB (diestro): k 0 = brazo armado atras, 1 = balon soltado y brazo cruzado."""
    k = clamp(k)
    return pose_joints((x, y), yaw, pitch=lerp(-0.08, 0.25, k), legs=((lerp(0.35, -0.1, k), 0.25), (lerp(-0.2, 0.45, k), lerp(0.2, 0.6, k))),
                       arms=((lerp(0.9, 1.1, k), 0.6, 0.3), (lerp(2.6, 1.1, k), lerp(1.7, 0.2, k), lerp(0.9, 0.2, k))))

def S3(t, T0, T1):
    # tras el TD de los Giants (8:17): los Giants se preparan para sacar desde su 30
    lt = t - T0
    Pl = []
    for i, y in enumerate([-22, -17, -12, -7, -3, 3, 7, 12, 17, 22]):
        Pl.append(P(stance_pose((71.2, y), math.pi, 'ready'), 'GB', str([28, 41, 57, 23, 45, 52, 34, 85, 31, 44][i]), i))
    Pl.append(P(stance_pose((76.0, 0.6), math.pi, 'stand'), 'GB', '', 4))
    for i, y in enumerate([-15, -8, -2, 4, 10, 16]):
        Pl.append(P(stance_pose((55.0, y), 0.0, 'ready'), 'DAL', str([59, 50, 81, 94, 58, 86][i]), i))
    for i, y in enumerate([-10, 0, 10]):
        Pl.append(P(stance_pose((40.0, y), 0.0, 'ready'), 'DAL', str([26, 22, 30][i]), i + 1))
    Pl.append(P(stance_pose((6.0, -1.0), 0.0, 'ready'), 'DAL', '25', 2))
    c = cam((50 + lt * 0.6, -44, 12), (62 + lt * 0.6, 2, -1.5), 1900)
    img = FG.draw_people(world(c), c, Pl, t)
    img = finish(img); d = ImageDraw.Draw(img)
    score_bug(d, 31, 10, '4TH  8:17', extra='GIANTS LEAD BY 21')
    B.headline(d, 640, '31–10', 230, YEL)
    return img

def S4(t, T0, T1):
    # Vick a Celek desde la 35 de los Eagles: pase profundo por el centro, rozando la mano de Tuck;
    # Celek deja atras a Phillips y se va solo. Corte a la camara de end zone para el TD.
    lt = t - T0; dur = T1 - T0
    tsn, tth, tca = 0.25, 1.05, 2.05
    t_cut = dur - 1.15
    if lt < t_cut:
        Pl = []
        sn = lt > tsn
        for i, y in enumerate([-3.4, -2.3, -1.15, 0, 1.15]):
            Pl.append(P(stance_pose((34.1 - (0.6 if sn else 0), y), 0.0, 'block' if sn else '3pt'), 'DAL', ['72', '79', '62', '69', '68'][i], i))
        for i, y in enumerate([-3.0, -1.2, 1.2]):
            Pl.append(P(stance_pose((35.9 - (0.8 if sn else 0), y), math.pi, 'block' if sn else '3pt'), 'GB', ['98', '75', '90'][i], i + 1))
        # Tuck (#91) se libra y salta con el brazo arriba
        ku = clamp((lt - tsn) / 0.8)
        tx = lerp(35.9, 30.4, ku); ty = lerp(3.0, 1.0, ku)
        if lt < tth - 0.25:
            Jt = run_pose((tx, ty), math.pi + 0.3, lt * 2.2, speed=0.8) if sn else stance_pose((35.9, 3.0), math.pi, '3pt')
        else:
            Jt = pose_joints((tx, ty, 1.15), math.pi + 0.3, pitch=-0.1, legs=((0.3, 0.6), (0.1, 0.4)), arms=((3.0, 0.05, 0.15), (2.2, 0.3, 0.2)), ground=False)
        Pl.append(P(Jt, 'GB', '91', 1))
        # Vick (#7) en escopeta: retrocede y lanza
        if lt < tsn:
            Jv = stance_pose((30.0, 0.2), 0.0, 'qb')
        elif lt < tth - 0.35:
            Jv = run_pose((lerp(30.0, 28.2, (lt - tsn) / (tth - 0.35 - tsn)), 0.2), 0.0, -lt * 2, speed=0.4)
        else:
            Jv = throw_pose(28.2, 0.2, 0.0, (lt - tth + 0.35) / 0.45)
        Pl.append(P(Jv, 'DAL', '7', 2))
        # Celek (#87): ruta por el centro
        if lt < tsn:
            cx, cy = 34.0, 3.4
            Jc = stance_pose((cx, cy), 0.0, '3pt'); Pl.append(P(Jc, 'DAL', '87', 1))
        else:
            u = (lt - tsn)
            cx = 34.0 + min(u, tca - tsn) * 9.0 + max(0, u - (tca - tsn)) * 9.6
            cy = lerp(3.4, -1.0, clamp(u / (tca - tsn)))
            Pl.append(carrier(cx, cy, 0.0 if u > 0.4 else 0.1, cx / 2.3, 'DAL', '87', 1, speed=0.95, ball=lt > tca))
        # Phillips (#21) llega tarde y se tira al suelo
        if lt < tca + 0.2:
            px = lerp(62, 54.5, clamp(lt / (tca + 0.2))); Pl.append(carrier(px, -2.0, math.pi, lt * 2.2, 'GB', '21', 2, speed=0.9, ball=False))
        else:
            k = ease((lt - tca - 0.2) / 0.4)
            Pl.append(P(pose_joints((54.0 - k * 1.2, -1.6, lerp(0.9, 0.3, k)), math.pi + 0.4, pitch=lerp(0.5, 1.45, k), legs=((0.2, 0.4), (0.1, 0.3)), arms=((2.7, 0.1, 0.3), (2.5, 0.1, 0.3)), ground=False), 'GB', '21', 2))
        for i, y in enumerate([-10, 9]):
            Pl.append(carrier(lerp(42, 48, clamp(lt / 2)), y, math.pi * 0.85 if y > 0 else -math.pi * 0.85, lt * 2, 'GB', ['24', '29'][i], i, speed=0.8, ball=False))
        if tth <= lt < tca:
            u = (lt - tth) / (tca - tth)
            bp = np.array([lerp(28.6, cx + 0.3, u), lerp(0.3, cy, u), lerp(2.3, 1.5, u) + 4 * 6.5 * u * (1 - u)])
            Pl.append(ball_prop(bp, np.array([1.0, 0, 0.25]), 1.7, 0.3))
        elif lt < tth:
            pass
        fx = clamp(lerp(31, cx, clamp((lt - tth + 0.3) / 1.0)), 31, 70)
        c = cam((fx - 12, -42, 9), (fx + 3, 0.3, -0.4), 3100)
        img = FG.draw_people(world(c), c, Pl, t)
        done = False
    else:
        u = clamp((lt - t_cut) / 0.9)
        rx = lerp(93, 102.5, u); ry = -1.0
        Pl = [carrier(rx, ry, 0.0, rx / 2.3, 'DAL', '87', 1)] + chase(rx, ry, lt, 2, 'GB', lag=7.0, seed=4, spread=3)
        c = cam((124, -9, 8), (97, -1.5, 0.6), 2600)
        done = rx > 100
        img = FG.draw_people(world(c, cheer=1.0 if done else 0.0), c, Pl, t)
    img = finish(img); d = ImageDraw.Draw(img)
    score_bug(d, 31, 17 if done else 10, '4TH  7:28', flash='PHI' if done else None)
    lower_third(d, 1180, 'VICK TO CELEK', '65-YARD TOUCHDOWN', acc=PHG, t=lt)
    return img

def S5(t, T0, T1):
    # onside kick de Akers hacia la izquierda; 10 Eagles (4 a su derecha, 5 a su izquierda); la primera linea
    # de los Giants a 15 yardas; Riley Cooper la atrapa y avanza hasta la 43 de los Eagles
    lt = t - T0
    tk = 0.6; tc = 1.75
    Pl = []
    ys = [-19, -14, -9, -4, 4, 8, 12, 16, 21]
    nums = ['82', '31', '26', '53', '59', '88', '14', '22', '84']
    for i, y in enumerate(ys):
        go = max(0.0, lt - tk + 0.25)
        x = 29.2 + min(go * 7.5, 11.5 + (i % 2))
        yy = y + (12 - y) * 0.45 * clamp((lt - tc) / 1.0) if y > 0 else y
        if nums[i] == '14':
            if lt < tc: x, yy = 29.2 + min(go * 7.0, 12.2), lerp(12, 13, clamp(go / 1.4))
            else: x, yy = lerp(41.4, 43.0, clamp((lt - tc) / 0.7)), 13.0
            Pl.append(carrier(x, yy, 0.05, lt * 2.3, 'DAL', '14', 3, speed=0.9, ball=lt >= tc))
            continue
        Pl.append(carrier(x, yy, 0.0, lt * 2.3 + i * 0.3, 'DAL', nums[i], i, speed=0.9 if lt > tk - 0.25 else 0.15, ball=False))
    for i, y in enumerate([-19, -11, -4, 4, 11, 19]):
        k = clamp((lt - tk - 0.3) / 1.6)
        yy = lerp(y, 8 + y * 0.3, k) if y > -5 else y
        Pl.append(carrier(lerp(45.0, 43.6, k), yy, math.pi + (0.6 if y > -5 else 0), lt * 2, 'GB', str([85, 81, 89, 86, 33, 49][i]), i, speed=0.6 * k + 0.1, ball=False))
    # Akers (#2)
    if lt < tk:
        Pl.append(carrier(lerp(24.5, 29.4, lt / tk), 0.0, 0.0, lt * 2.4, 'DAL', '2', 3, speed=0.6, ball=False))
    else:
        Pl.append(carrier(29.6 + (lt - tk) * 3.0, 0.4, 0.2, lt * 2, 'DAL', '2', 3, speed=0.5, ball=False))
    if lt < tk:
        bp = np.array([30.0, 0.0, 0.25]); ax = np.array([0, 0, 1.0])
    elif lt < tc:
        u = (lt - tk) / (tc - tk)
        x = lerp(30.0, 41.4, u); y = lerp(0.0, 13.0, u)
        bounce = abs(math.sin(u * math.pi * 2.0)) * 1.4 * (1 - u * 0.4)
        bp = np.array([x, y, 0.15 + bounce]); ax = np.array([math.cos(u * 20), 0.3, math.sin(u * 20)])
    else:
        bp = None
    if bp is not None: Pl.append(ball_prop(bp, ax, 1.8, 0.3))
    c = cam((26, -44, 15), (37, 6, -1.0), 2050)
    img = FG.draw_people(world(c), c, Pl, t)
    img = finish(img); d = ImageDraw.Draw(img)
    score_bug(d, 31, 17, '4TH  7:28')
    t2 = SEGS[5][1][0] if len(SEGS[5]) > 1 else T0 + 1.5
    if t < t2:
        lower_third(d, 1180, 'ONSIDE KICK', None, acc=PHG, t=lt)
    else:
        lower_third(d, 1180, 'ONSIDE KICK', 'EAGLES RECOVER AT THEIR 43', acc=PHG, t=lt)
    return img

def S6(t, T0, T1):
    # 3.er down y gol desde la 4: Vick escapa de la presion y entra corriendo
    lt = t - T0; dur = T1 - T0
    tsn = 0.12
    Pl = []
    sn = lt > tsn
    for i, y in enumerate([-3.4, -2.3, -1.15, 0, 1.15, 2.3]):
        Pl.append(P(stance_pose((95.1 - (0.5 if sn else 0), y), 0.0, 'block' if sn else '3pt'), 'DAL', ['72', '79', '62', '69', '68', '87'][i], i))
    for i, y in enumerate([-3.0, -1.2, 1.2, 3.0]):
        Pl.append(P(stance_pose((96.9 - (0.7 if sn else 0), y), math.pi, 'block' if sn else '3pt'), 'GB', ['91', '98', '75', '90'][i], i + 1))
    u = clamp((lt - tsn) / (dur - 0.55))
    pts = [(0, 91.0, 0.0), (0.35, 91.2, -2.8), (0.6, 94.5, -5.2), (1.0, 101.2, -6.2)]
    for (u0, x0, y0), (u1, x1, y1) in zip(pts[:-1], pts[1:]):
        if u <= u1:
            k = (u - u0) / (u1 - u0); vx, vy = lerp(x0, x1, k), lerp(y0, y1, k); yaw = math.atan2(y1 - y0, x1 - x0); break
    if not sn:
        Pl.append(P(stance_pose((91.0, 0.0), 0.0, 'qb'), 'DAL', '7', 2))
    else:
        Pl.append(carrier(vx, vy, yaw, vx * 0.6 + lt * 2, 'DAL', '7', 2, speed=0.9))
    # blitz de los Giants que le persigue
    for i, (x0, y0) in enumerate([(97.5, -5.5), (98.0, 1.5)]):
        k = clamp((lt - tsn) / 1.0)
        Pl.append(carrier(lerp(x0, vx - 1.6 - i, k), lerp(y0, vy + 1.5 + i, k), math.pi * 0.9, lt * 2.3, 'GB', ['58', '55'][i], i, speed=0.9, ball=False))
    Pl.append(carrier(lerp(102, 100.3, clamp(lt / 1.4)), lerp(-9, -7.0, clamp(lt / 1.4)), -2.8, lt * 2, 'GB', '24', 3, speed=0.7, ball=False))
    c = cam((86, -40, 9), (95.5, -2.5, -0.4), 3200)
    done = vx > 100
    img = FG.draw_people(world(c, cheer=1.0 if done else 0.0), c, Pl, t)
    img = finish(img); d = ImageDraw.Draw(img)
    score_bug(d, 31, 24 if done else 17, '4TH  5:28', flash='PHI' if done else None, extra=None if done else '3RD & GOAL')
    lower_third(d, 1180, 'MICHAEL VICK #7', 'SCRAMBLES IN FROM THE 4', acc=PHG, t=lt)
    return img

def S7(t, T0, T1):
    # 2.o y 3 desde la 13: curl corto de Maclin por la izquierda, la atrapa en la 5, finta a Terrell Thomas y entra
    lt = t - T0
    tsn, tth, tca = 0.25, 0.85, 1.35
    sn = lt > tsn
    Pl = []
    for i, y in enumerate([-3.4, -2.3, -1.15, 0, 1.15]):
        Pl.append(P(stance_pose((86.1 - (0.5 if sn else 0), y), 0.0, 'block' if sn else '3pt'), 'DAL', ['72', '79', '62', '69', '68'][i], i))
    for i, y in enumerate([-3.0, -1.2, 1.2, 3.0]):
        Pl.append(P(stance_pose((87.9 - (0.6 if sn else 0), y), math.pi, 'block' if sn else '3pt'), 'GB', ['91', '98', '75', '90'][i], i + 1))
    Jv = stance_pose((82.0, 0.2), 0.0, 'qb') if lt < tth - 0.35 else throw_pose(82.0, 0.2, 0.9, (lt - tth + 0.35) / 0.45)
    Pl.append(P(Jv, 'DAL', '7', 2))
    # Maclin (#18), abierto a la izquierda
    if lt < tsn:
        mx, my = 86.0, 17.0; Pl.append(P(stance_pose((mx, my), 0.0, 'ready'), 'DAL', '18', 1))
    elif lt < tca:
        k = (lt - tsn) / (tca - tsn)
        mx = lerp(86.0, 95.0, ease(k)); my = lerp(17.0, 15.0, k)
        if k < 0.8: Pl.append(carrier(mx, my, 0.0, mx / 2.2, 'DAL', '18', 1, speed=0.9, ball=False))
        else: Pl.append(P(pose_joints((mx, my), math.pi * 0.9, pitch=0.2, legs=((0.4, 0.5), (0.1, 0.3)), arms=((1.4, 0.4, 0.1), (1.4, 0.4, 0.1))), 'DAL', '18', 1))
    else:
        k = clamp((lt - tca) / 1.2)
        pts = [(0, 95.0, 15.0), (0.3, 95.6, 16.8), (0.55, 97.8, 13.6), (1.0, 101.6, 12.0)]
        for (u0, x0, y0), (u1, x1, y1) in zip(pts[:-1], pts[1:]):
            if k <= u1:
                q = (k - u0) / (u1 - u0); mx, my = lerp(x0, x1, q), lerp(y0, y1, q); yaw = math.atan2(y1 - y0, x1 - x0); break
        Pl.append(carrier(mx, my, yaw, mx / 1.8, 'DAL', '18', 1, speed=0.85, ball=True))
    # Terrell Thomas (#24): cierra, muerde la finta y se queda atras
    if lt < tca + 0.3:
        tx, ty = lerp(93.5, 96.6, clamp(lt / (tca + 0.3))), lerp(13.5, 16.0, clamp(lt / (tca + 0.3)))
        Pl.append(carrier(tx, ty, 0.6, lt * 2.2, 'GB', '24', 3, speed=0.7, ball=False))
    else:
        k = clamp((lt - tca - 0.3) / 0.8)
        Pl.append(carrier(lerp(96.6, 97.6, k), lerp(16.0, 17.6, k), 1.2, lt * 2.2, 'GB', '24', 3, speed=0.5, ball=False))
    Pl.append(carrier(lerp(97, 99, clamp(lt / 2)), 6.0, 2.6, lt * 2, 'GB', '21', 2, speed=0.6, ball=False))
    if tth <= lt < tca:
        u = (lt - tth) / (tca - tth)
        bp = np.array([lerp(82.4, mx - 0.4, u), lerp(0.4, my - 0.2, u), lerp(2.2, 1.4, u) + 4 * 1.2 * u * (1 - u)])
        Pl.append(ball_prop(bp, np.array([1.0, 1.0, 0.15]), 1.7, 0.3))
    c = cam((123, 22, 12), (92, 11, -0.6), 2300)
    tied = mx > 100 and lt >= tca
    img = FG.draw_people(world(c, cheer=1.0 if tied else 0.0), c, Pl, t)
    img = finish(img); d = ImageDraw.Draw(img)
    score_bug(d, 31, 31 if tied else 24, '4TH  1:16', flash='PHI' if tied else None)
    t2 = SEGS[7][1][0] if len(SEGS[7]) > 1 else T0 + 1.8
    if t < t2:
        lower_third(d, 1180, 'JEREMY MACLIN #18', '13-YARD TOUCHDOWN', acc=PHG, t=lt)
    else:
        B.headline(d, 640, 'TIED 31–31', 180, YEL)
    return img

def S8(t, T0, T1):
    lt = t - T0
    c = cam((LOS + 26 - lt * 0.6, -40, 8.5), (LOS + 4 - lt * 0.6, 0.5, -0.5), 2600)
    img = FG.draw_people(world(c), c, punt_people(T_SNAP - 1.0), t)
    img = finish(img); d = ImageDraw.Draw(img)
    score_bug(d, 31, 31, '4TH  0:14', extra='14 SECONDS LEFT')
    t2 = SEGS[8][1][0] if len(SEGS[8]) > 1 else T0 + 1.5
    if t >= t2:
        lower_third(d, 1180, 'GIANTS PUNT', 'TO DESEAN JACKSON', acc=NYR, t=t - t2)
    return img

def S9(t, T0, T1):
    # plano alto desde detras del punter con la orden dibujada: fuera del campo
    lt = t - T0
    c = cam((PUNTER_X + 20, 4, 14), (PUNTER_X - 14, -9, 0), 1500)
    img = FG.draw_people(world(c), c, punt_people(T_SNAP - 0.8), t)
    img = finish(img); d = ImageDraw.Draw(img)
    k = ease(lt / 0.9)
    pts3 = [(PUNTER_X - 1.0, 0.3, 1.0), (PUNTER_X - 8, -9, 6.0), (PUNTER_X - 14, -19, 4.0), (PUNTER_X - 17, -27.5, 0.5)]
    pp = [c.p(q) for q in pts3]
    pp = [(x / SS, y / SS) for x, y, _ in pp]
    n = max(2, int(2 + k * 10))
    curve = []
    for i in range(n):
        s = i / 10.0 * 3
        a = min(int(s), 2); f = s - a
        curve.append((lerp(pp[a][0], pp[a + 1][0], f), lerp(pp[a][1], pp[a + 1][1], f)))
    if len(curve) >= 2: tele_arrow(d, curve)
    score_bug(d, 31, 31, '4TH  0:14')
    B.headline(d, 560, 'KICK IT', 150)
    B.headline(d, 720, 'OUT OF BOUNDS', 130, YEL)
    return img

def S10(t, T0, T1):
    # snap alto, patada en linea y seguimiento del balon hasta Jackson
    bp, _ = punt_ball(t)
    if t < T_KICK + 0.1:
        fx = PUNTER_X - 6
    else:
        fx = clamp(bp[0] - 1.0, JX0 + 3, PUNTER_X - 6) if bp is not None else JX0 + 3
    c = cam((fx + 16, -38, 8.5), (fx - 2, 0.5, 0.2), 2500)
    img = FG.draw_people(world(c), c, punt_people(t), t)
    img = finish(img); d = ImageDraw.Draw(img)
    score_bug(d, 31, 31, game_clock(t))
    if t < T_KICK + 0.3:
        lower_third(d, 1180, 'HIGH SNAP', None, acc=NYR, t=t - T_SNAP)
    else:
        lower_third(d, 1180, 'LINE DRIVE', 'STRAIGHT TO JACKSON', acc=NYR, t=t - T_KICK - 0.3)
    return img

def S11(t, T0, T1):
    lt = t - T0
    j = JP[_idx(t)]
    c = cam((j[0] - 9, j[1] - 9, 3.2), (j[0] + 3, j[1] + 1, 1.0), 2300)
    img = FG.draw_people(world(c), c, punt_people(t), t)
    img = finish(img); d = ImageDraw.Draw(img)
    score_bug(d, 31, 31, game_clock(t))
    lower_third(d, 1180, 'DESEAN JACKSON #10', "BOBBLE AT THE EAGLES' 35", acc=PHG, t=lt)
    return img

def S12(t, T0, T1):
    lt = t - T0
    j = JP[_idx(t)]
    c = cam((j[0] - 12, -40, 8.0), (j[0] + 4, j[1] * 0.5, 0.3), 2700)
    img = FG.draw_people(world(c), c, punt_people(t), t)
    img = finish(img); d = ImageDraw.Draw(img)
    score_bug(d, 31, 31, game_clock(t))
    return img

def S13(t, T0, T1):
    # camara de banda que corre con el: banda sur, a la altura del jugador
    j = JP[_idx(t)]
    c = cam((j[0] - 9, -38, 7.0), (j[0] + 3, j[1] * 0.7, 0.4), 3000)
    img = FG.draw_people(world(c), c, punt_people(t), t)
    img = finish(img); d = ImageDraw.Draw(img)
    score_bug(d, 31, 31, game_clock(t))
    labs = ['MIDFIELD', 'THE 40', 'THE 30', 'NOBODY CAN CATCH HIM']
    k = -1
    for i, xx in enumerate((48.5, 58.5, 68.5, 80.0)):
        if j[0] >= xx: k = i
    if k >= 0:
        B.headline(d, 600, labs[k], 150 if k < 3 else 100, YEL if k < 3 else WHITE)
    return img

def S14(t, T0, T1):
    img, c = goal_line_view(t)
    img = finish(img); d = ImageDraw.Draw(img)
    clk = game_clock(t)
    score_bug(d, 31, 31, clk)
    # reloj grande de TV
    d.rounded_rectangle([W // 2 - 190, 520, W // 2 + 190, 690], 16, fill=(12, 14, 22))
    d.text((W // 2, 605), clk.split()[-1], font=AF(150), fill=(255, 80, 70) if clk.endswith('0:00') else YEL, anchor='mm')
    return img

def S15(t, T0, T1):
    lt = t - T0
    sc = t > T_IN
    img, c = goal_line_view(t, cheer=1.0 if sc else 0.0, refs_up=clamp((t - T_IN) / 0.3))
    img = finish(img); d = ImageDraw.Draw(img)
    if sc:
        B.headline(d, 600, 'TOUCHDOWN!', 170, YEL)
        score_bug(d, 31, 38, 'FINAL', flash='PHI')
    else:
        score_bug(d, 31, 31, '4TH  0:00')
    return img

def S16(t, T0, T1):
    lt = t - T0
    img = blurred_stadium(); d = ImageDraw.Draw(img)
    B.headline(d, 440, '28 POINTS', 150, YEL)
    B.headline(d, 570, 'IN 7:28', 110)
    rows = [('7:28', 'VICK TO CELEK · 65 YDS', '+7'), ('7:28', 'ONSIDE KICK RECOVERED', ''), ('5:28', 'VICK RUN · 4 YDS', '+7'),
            ('1:16', 'VICK TO MACLIN · 13 YDS', '+7'), ('0:00', 'JACKSON PUNT RETURN · 65 YDS', '+7')]
    for i, (clk, txt, pts) in enumerate(rows):
        k = ease((lt - i * 0.35) / 0.35)
        if k <= 0: continue
        y = 700 + i * 120; x = 70 - int((1 - k) * 60)
        d.rounded_rectangle([x, y, W - 70, y + 100], 10, fill=(12, 14, 22) if i < 4 else (40, 40, 10))
        d.rectangle([x, y, x + 12, y + 100], fill=PHG if i < 4 else YEL)
        d.text((x + 40, y + 50), clk, font=BF(58), fill=YEL, anchor='lm')
        d.text((x + 175, y + 50), txt, font=BF(54), fill=WHITE, anchor='lm')
        if pts: d.text((W - 100, y + 50), pts, font=AF(56), fill=YEL, anchor='rm')
    return img

def S17(t, T0, T1):
    # Coughlin de espaldas en la banda de los Giants: tira sus notas y sale a por el punter
    lt = t - T0
    cx = 58.0; cy = 28.6 - clamp((lt - 1.6) / 2.0) * 3.0
    c = cam((cx - 3.5, 36.5, 2.6), (cx + 3.0, 18, 1.0), 1700)
    img = world(c)
    Pl = []
    thr = clamp((lt - 0.4) / 0.35)
    if lt < 1.6:
        a = lerp(1.6, 0.2, ease(thr)) if lt > 0.4 else 1.2
        J = pose_joints((cx, cy), -math.pi / 2, pitch=lerp(0.0, 0.25, thr), legs=((0.08, 0.06), (-0.08, 0.06)), arms=((a, 0.4, 0.1), (0.3, 0.3, 0.1)))
    else:
        J = run_pose((cx, cy), -math.pi / 2 + 0.2, lt * 1.6, speed=0.45)
    Pl.append(P(J, 'COACH', skin=0, breath=True))
    for k, (x, y) in enumerate([(cx + 5, 29.5), (cx + 7.5, 30.2), (cx - 4, 30.4), (cx + 10, 29.8)]):
        Pl.append(P(stance_pose((x, y), -math.pi / 2, 'stand'), 'GB', ['57', '96', '41', '84'][k], k))
    Pl.append(P(stance_pose((cx + 6.0, 22.5), math.pi / 2 + 0.3, 'stand'), 'GB', '', 4))   # el punter, a media distancia
    img = FG.draw_people(img, c, Pl, t)
    # notas que vuelan
    if lt > 0.55:
        d0 = ImageDraw.Draw(img)
        w = J['wrL']; base = c.p(w)
        r = random.Random(17)
        for k in range(7):
            u = lt - 0.55
            vx = r.uniform(-0.6, 0.6); vz = r.uniform(0.2, 1.4); vy = r.uniform(-1.6, -0.6)
            pos = np.array([w[0] + vx * u, w[1] + vy * u, max(0.02, w[2] + vz * u - 1.6 * u * u)])
            p = c.p(pos)
            if p[2] < 0.5: continue
            s = c.f * 0.11 / p[2]; ang = u * 6 + k
            pts = [(p[0] + s * math.cos(ang + a) * (1.0 if i % 2 == 0 else 0.75), p[1] + s * math.sin(ang + a) * 0.6) for i, a in enumerate((0.6, 2.5, 3.7, 5.7))]
            d0.polygon(pts, fill=(245, 245, 238) if k % 2 else (226, 226, 214))
    img = finish(img); d = ImageDraw.Draw(img)
    lower_third(d, 1180, 'TOM COUGHLIN', 'GIANTS HEAD COACH', acc=NYR, t=lt)
    return img

def S18(t, T0, T1):
    lt = t - T0; dur = T1 - T0
    img, c = wide_ez(t, k_desc=1 - lt / dur * 0.6, z0=34, z1=16, cheer=1.0)
    img = finish(img); d = ImageDraw.Draw(img)
    B.headline(d, 560, 'FIRST IN', 150)
    B.headline(d, 720, 'NFL HISTORY', 150, YEL)
    lower_third(d, 1180, 'WALK-OFF PUNT RETURN TD', 'NO TIME LEFT ON THE CLOCK', acc=PHG, t=lt - 0.5)
    return img

LOGO = None
def S19(t, T0, T1):
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

SCENES = [S0, S1, S2, S3, S4, S5, S6, S7, S8, S9, S10, S11, S12, S13, S14, S15, S16, S17, S18, S19]
assert len(SCENES) == len(TIMES) == len(SCRIPT)

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
    if '--preview' in a:
        ts = [float(x) for x in a[a.index('--preview') + 1].split(',')]
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
