#!/usr/bin/env python3
"""Gridiron Lore 09 - The Immaculate Reception (23 dic 1972, Three Rivers Stadium). Motor engine04 + figures.
Uso: python3 render_gridiron_lore_09.py voz.mp3 out.mp4 [--preview t1,t2,...] [--cover t] [--range a b]
Coordenadas: los Steelers atacan hacia x DECRECIENTE en la jugada final (su 40 = x 60; end zone de los Raiders en x<0).
La banda cercana a la camara principal es y<0 = la izquierda de los Steelers (por ahi corre Harris)."""
import sys, json, math, random, subprocess, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import engine04 as E
from engine04 import (Cam, pose_joints, run_pose, stance_pose, UP, ease, lerp, clamp, mix, shade)
import figures as FG
import base03 as B
import threerivers as TR

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
SS = 1.5
SW, SH = int(W * SS), int(H * SS)
YEL = (255, 204, 41); WHITE = (255, 255, 255); BLACK = (0, 0, 0)
PITB = (24, 24, 26); PITG = (214, 170, 46); OAKS = (170, 176, 184); OAKB = (20, 20, 22)

SCRIPT = [l.strip() for l in open(os.path.join(HERE, 'gridiron_lore_09_guion.txt')) if l.strip()]
TIMES = json.load(open(os.path.join(HERE, 'times.json')))
SEGS = json.load(open(os.path.join(HERE, 'times_segs.json')))
CH = B.chunks(B.build_words(TIMES, SEGS))

def AF(sz): return B.F(B.ANTON, int(sz))
def BF(sz): return B.F(B.BEBAS, int(sz))

def watermark(d):
    d.text((W // 2, 150), '@nflgridironlore', font=AF(50), fill=WHITE, anchor='mm', stroke_width=4, stroke_fill=BLACK)
B.watermark = watermark

# ---------------------------------------------------------------- 1972, sin logos. 'GB' = Steelers (local, negro), 'DAL' = Raiders (blanco)
E.TEAM['GB'] = dict(helmet=(22, 22, 24), hstripe=[(214, 170, 46)], mask=(150, 150, 154),
                    jersey=(24, 24, 26), num=(226, 182, 52), numout=None, sleeve=[(226, 182, 52), (226, 182, 52)],
                    pants=(208, 166, 60), pstripe=[(24, 24, 26)], sock=(24, 24, 26), sockstripe=(226, 182, 52),
                    shoe=(20, 20, 22), skin=None)
E.TEAM['DAL'] = dict(helmet=(176, 180, 188), hstripe=[(20, 20, 22)], mask=(150, 150, 154),
                     jersey=(244, 244, 242), num=(20, 20, 22), numout=None, sleeve=[(20, 20, 22), (170, 176, 184)],
                     pants=(172, 178, 186), pstripe=[(20, 20, 22)], sock=(20, 20, 22), sockstripe=(176, 180, 188),
                     shoe=(20, 20, 22), skin=None)
E.TEAM['COACH'] = dict(helmet=None, coat=(40, 40, 46), furhat=(214, 170, 46), pants=(50, 48, 52), shoe=(20, 20, 20))

def make_ground9(seed=9):
    """Tartan Turf de 1972: verde algo azulado y uniforme, numeros cada 10, hashes NFL de 1972, end zones lisas."""
    GX0, GX1, GY0, GY1, GPX = E.GX0, E.GX1, E.GY0, E.GY1, E.GPX
    FW = E.FIELD_W
    rng = np.random.default_rng(seed)
    Wd = int((GX1 - GX0) * GPX); Hd = int((GY1 - GY0) * GPX)
    def X(x): return (x - GX0) * GPX
    def Y(y): return (y - GY0) * GPX
    n1 = rng.random((Hd // 16 + 2, Wd // 16 + 2)).astype(np.float32)
    n1 = np.array(Image.fromarray((n1 * 255).astype(np.uint8)).resize((Wd, Hd), Image.BICUBIC), np.float32) / 255
    n3 = rng.random((Hd, Wd)).astype(np.float32)
    xs = (np.arange(Wd) / GPX + GX0)
    seam = ((np.abs((xs % 5.0) - 2.5) < 0.05) * -0.03)[None, :]          # costuras de los rollos de cesped artificial
    grass = np.array([44, 112, 70], np.float32)
    base = grass[None, None, :] * (0.94 + 0.05 * n1[..., None] + seam[..., None] + 0.06 * (n3[..., None] - 0.5))
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    lw = max(2, int(GPX * 0.11)); white = (240, 242, 240)
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
    for x in (2.0, 98.0):
        d.line([X(x), Y(-0.33), X(x), Y(0.33)], fill=white, width=lw)
    fnt = E.font('Anton-Regular.ttf', GPX * 2.0)
    for x in range(10, 100, 10):
        n = x if x <= 50 else 100 - x
        for y, rot in ((-FW / 2 + 12, 180), (FW / 2 - 12, 0)):
            t = Image.new('L', (int(GPX * 5), int(GPX * 3)), 0)
            ImageDraw.Draw(t).text((t.size[0] / 2, t.size[1] / 2), str(n), font=fnt, fill=235, anchor='mm')
            t = t.rotate(rot + 90, expand=True).transpose(Image.FLIP_TOP_BOTTOM)
            img.paste(Image.new('RGB', t.size, white), (int(X(x) - t.size[0] / 2), int(Y(y) - t.size[1] / 2)), t)
    for (x0, x1) in ((-10, 0), (100, 110)):
        d.rectangle([X(x0) + lw, Y(-FW / 2) + lw, X(x1) - lw, Y(FW / 2) - lw], fill=(40, 102, 64))
    # alrededor del campo: el mismo cesped artificial algo mas oscuro (estadio multiusos)
    for (x0, x1) in ((GX0, -10.3), (110.3, GX1)):
        d.rectangle([X(x0), 0, X(x1), Hd], fill=(38, 96, 60))
    for (y0, y1) in ((GY0, -FW / 2 - 0.4), (FW / 2 + 0.4, GY1)):
        d.rectangle([0, Y(y0), Wd, Y(y1)], fill=(38, 96, 60))
    return img.filter(ImageFilter.GaussianBlur(0.5))

_gp = os.path.join(HERE, 'cache_ground09.png')
if os.path.exists(_gp): E.GROUND = Image.open(_gp).convert('RGB')
else:
    E.GROUND = make_ground9(); E.GROUND.save(_gp)

def cam(pos, look, f, roll=0.0):
    return Cam(pos, look, f * SS, SW, SH, roll)

def world(c, cheer=0.0):
    img = TR.render_world(c, cheer=cheer)
    d = ImageDraw.Draw(img)
    E.goalpost(d, c, 0); E.goalpost(d, c, 100)   # 1972: postes de horquilla EN la linea de gol (se movieron en 1974)
    return img

def finish(img):
    return img.resize((W, H), Image.LANCZOS)

def P(J, team, num='', skin=0, **kw):
    p = dict(J=J, team=team, num=num, skin=skin); p.update(kw); return p

def carrier(x, y, yaw, phase, team, num, skin=0, speed=1.0, ball=True, arm='R'):
    J = run_pose((x, y), yaw, phase, speed=speed, carry=arm if ball else None)
    bp = (J['el' + arm] * 0.45 + J['wr' + arm] * 0.55 + J['f'] * 0.04) if ball else None
    return P(J, team, num, skin, ball=bp)

# ---------------------------------------------------------------- graficos de TV
def score_bug(d, oak, pit, clock='4TH  0:22', extra=None, flash=None, y=232):
    x0 = 60; f = BF(54)
    d.rounded_rectangle([x0, y, W - 60, y + 76], 8, fill=(12, 14, 22))
    fl = flash == 'OAK'
    d.rectangle([x0 + 10, y + 8, x0 + 330, y + 68], fill=(60, 64, 70) if not fl else YEL)
    d.rectangle([x0 + 10, y + 8, x0 + 18, y + 68], fill=OAKS)
    d.text((x0 + 32, y + 38), 'RAIDERS', font=f, fill=WHITE if not fl else BLACK, anchor='lm')
    d.text((x0 + 312, y + 38), str(oak), font=f, fill=WHITE if not fl else BLACK, anchor='rm')
    fl = flash == 'PIT'
    d.rectangle([x0 + 340, y + 8, x0 + 660, y + 68], fill=PITB if not fl else YEL)
    d.rectangle([x0 + 340, y + 8, x0 + 348, y + 68], fill=PITG)
    d.text((x0 + 362, y + 38), 'STEELERS', font=f, fill=WHITE if not fl else BLACK, anchor='lm')
    d.text((x0 + 642, y + 38), str(pit), font=f, fill=WHITE if not fl else BLACK, anchor='rm')
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

def tag(d, c, P3, text, dy=-150, col=YEL):
    """Rotulo de TV (caja amarilla) sobre un jugador, con una linea fina hasta el; sin circulos."""
    p = c.p(P3)
    x, y = p[0] / SS, p[1] / SS
    f = BF(56); tw = d.textlength(text, font=f)
    bx = clamp(x - tw / 2 - 18, 40, W - tw - 76); by = clamp(y + dy, 330, H - 500)
    d.line([x, y - 30, bx + tw / 2 + 18, by + 62], fill=col, width=5)
    d.rectangle([bx, by, bx + tw + 36, by + 62], fill=col)
    d.text((bx + 18, by + 31), text, font=f, fill=BLACK, anchor='lm')

def ball_prop(bp, ax, k=1.0, bias=0.0):
    ax = np.asarray(ax, float); ax = ax / np.linalg.norm(ax)
    def draw(C, L, c_):
        A = bp - ax * 0.12 * k; Bq = bp + ax * 0.12 * k
        FG.cone(C, c_, A, bp, .02 * k, .085 * k, (120, 62, 30), L, spec=.3)
        FG.cone(C, c_, bp, Bq, .085 * k, .02 * k, (120, 62, 30), L, spec=.3)
    return dict(J={'pelvis': bp}, team='PROP', prims=lambda c_: [(c_.depth(bp) - bias, lambda C, L: draw(C, L, c_))])

def throw_pose(x, y, yaw, k):
    """Lanzamiento del QB (diestro): k 0 = brazo armado atras, 1 = balon soltado y brazo cruzado."""
    k = clamp(k)
    return pose_joints((x, y), yaw, pitch=lerp(-0.08, 0.25, k), legs=((lerp(0.35, -0.1, k), 0.25), (lerp(-0.2, 0.45, k), lerp(0.2, 0.6, k))),
                       arms=((lerp(0.9, 1.1, k), 0.6, 0.3), (lerp(2.6, 1.1, k), lerp(1.7, 0.2, k), lerp(0.9, 0.2, k))))

# ================================================================ LA JUGADA (tiempo de jugada p, s desde el snap)
# Fuentes: 4.o y 10 en la 40 de Pittsburgh, 22 s, sin tiempos muertos; Bradshaw esquiva la presion y lanza por el centro
# a Fuqua (en la 35 de Oakland); Tatum choca con Fuqua; el balon sale hacia atras; Harris lo atrapa a ras de suelo en la 42
# de Oakland y corre por la banda IZQUIERDA; esquiva el ultimo placaje de Jimmy Warren en la 10; TD (quedaban 5 s).
LOS = 60.0
P_THROW = 3.6; P_HIT = 5.2; P_CATCH = 6.1; P_TD = 11.8
CATCH_PT = np.array([35.3, 0.4, 1.7]); SCOOP_PT = np.array([42.2, -2.0, 0.18])

def path(p, K, smooth=False):
    if p <= K[0][0]: return np.array(K[0][1:], float), np.zeros(2)
    for (t0, x0, y0), (t1, x1, y1) in zip(K[:-1], K[1:]):
        if p <= t1:
            u = (p - t0) / max(1e-6, t1 - t0)
            if smooth: u = ease(u)
            return np.array([lerp(x0, x1, u), lerp(y0, y1, u)]), np.array([x1 - x0, y1 - y0]) / max(1e-3, t1 - t0)
    return np.array(K[-1][1:], float), np.zeros(2)

QB = [(0, 61.0, 0.0), (1.5, 67.5, 0.2), (2.3, 67.8, 0.4), (3.2, 67.2, 4.6), (99, 67.2, 4.6)]
FUQ = [(0, 65.0, -1.5), (1.2, 58.5, -3.5), (3.0, 45.0, -1.5), (4.6, 36.5, 0.3), (5.2, 35.3, 0.5)]
TAT = [(0, 45.0, -3.5), (2.0, 36.0, -4.0), (3.6, 31.5, -3.0), (4.6, 32.8, -1.2), (5.2, 34.9, 0.25), (5.6, 36.0, 0.8), (99, 36.0, 0.8)]
HAR = [(0, 65.0, 1.5), (1.0, 64.0, 2.5), (2.4, 63.5, 3.0), (5.0, 46.5, -1.0), (6.1, 42.3, -2.0), (6.35, 41.5, -2.5),
       (8.2, 32.0, -14.0), (10.4, 12.5, -22.8), (10.65, 10.3, -23.1), (11.8, 0.3, -23.2), (12.4, -3.2, -22.9), (99, -3.6, -22.8)]
WAR = [(0, 40.0, -16.0), (3.0, 30.0, -18.0), (6.1, 24.0, -16.0), (9.6, 13.5, -20.0), (10.6, 10.9, -22.0)]
OL_Y = [-2.3, -1.15, 0.0, 1.15, 2.3]; OL_N = ['72', '57', '56', '62', '79']
DL_Y = [-3.0, -1.0, 1.0, 3.0]; DL_N = ['77', '74', '71', '83']
# los dos de dentro rompen la linea y casi le cazan; Bradshaw escapa a su derecha (+y)
DL_K = [[(0, 59.1, -3.0), (1.0, 61.0, -3.2), (2.4, 63.0, -2.8), (99, 63.5, -2.0)],
        [(0, 59.1, -1.0), (1.0, 61.6, -0.8), (2.3, 66.4, -0.3), (3.0, 66.8, 1.8), (3.8, 66.5, 3.2), (99, 66.5, 3.4)],
        [(0, 59.1, 1.0), (1.0, 61.6, 0.9), (2.3, 66.9, 0.9), (3.0, 67.4, 2.9), (3.8, 67.0, 3.9), (99, 67.0, 4.0)],
        [(0, 59.1, 3.0), (1.0, 61.0, 3.3), (2.4, 63.0, 4.0), (99, 63.5, 4.4)]]
# Raiders en cobertura (seis defensive backs, PFHOF) + un linebacker
COV = [dict(K=[(0, 54.0, 0.5), (2.0, 49.0, 1.0), (5.0, 41.0, 2.0)], num='56', lag=0.9, off=3.5),
       dict(K=[(0, 61.0, 16.5), (3.0, 40.0, 15.0), (5.5, 36.0, 10.0)], num='20', lag=1.4, off=6.0),
       dict(K=[(0, 61.0, -17.5), (3.0, 36.0, -17.0), (6.0, 30.0, -15.0)], num='26', lag=1.1, off=2.5),
       dict(K=[(0, 48.0, 10.0), (3.0, 38.0, 8.0), (5.4, 37.0, 3.5)], num='44', lag=1.7, off=4.5),
       dict(K=[(0, 50.0, -10.0), (3.0, 37.5, -9.0), (5.6, 31.0, -5.0)], num='43', lag=2.0, off=1.5)]
WR = [[(0, 61.0, -18.0), (3.5, 33.0, -17.0), (6.3, 27.0, -15.0), (10.0, 14.0, -18.0)],
      [(0, 61.0, 17.0), (3.5, 34.0, 15.5), (7.0, 28.0, 8.0), (10.0, 20.0, 0.0)],
      [(0, 60.9, 3.4), (1.2, 60.4, 3.6), (3.4, 50.0, 6.0), (6.5, 44.0, 3.0), (9.0, 38.0, -6.0)]]
WR_N = ['82', '88', '84']

def hpos(p): return path(p, HAR)[0]

def cov_pos(k, p):
    c = COV[k]
    a, v = path(p, c['K'], smooth=True)
    if p <= 6.0: return a, v
    q = p - c['lag']
    hp = hpos(q) + np.array([0, c['off']]); hp[0] += 1.2
    w = ease((p - 6.0) / 1.3)
    return a * (1 - w) + hp * w, v

# ---------------------------------------------------------------- movimiento natural: trayectorias suavizadas,
# velocidad continua, zancada ligada a la distancia recorrida y mezcla suave entre posturas
HZ = 120
PGRID = np.arange(-1.0, 14.0, 1.0 / HZ)

def _wrap(a): return (a + math.pi) % (2 * math.pi) - math.pi

class Track:
    def __init__(self, fn, win=0.3, yaw0=0.0):
        raw = np.array([fn(p) for p in PGRID], float)
        n = max(1, int(win * HZ / 2))
        ker = np.ones(2 * n + 1) / (2 * n + 1)
        sm = np.stack([np.convolve(np.pad(raw[:, i], (n, n), mode='edge'), ker, mode='valid') for i in range(2)], 1)
        v = np.gradient(sm, 1.0 / HZ, axis=0)
        sp = np.linalg.norm(v, axis=1)
        k = np.clip(sp / 8.5, 0, 1)
        self.PH = np.cumsum(sp / HZ / (1.1 + 1.2 * k))          # ciclos de zancada (1 ciclo = 2 pasos)
        yaw = np.zeros(len(sp)); last = yaw0
        for i in range(len(sp)):
            if sp[i] > 0.7:
                tgt = math.atan2(v[i, 1], v[i, 0])
                last = last + _wrap(tgt - last) * min(1.0, 9.0 / HZ * (1 + sp[i] / 3))   # giro progresivo
            yaw[i] = last
        self.P, self.V, self.S, self.Y = sm, v, sp, yaw
    def at(self, p):
        i = int(clamp((p - PGRID[0]) * HZ, 0, len(PGRID) - 1))
        return self.P[i], self.V[i], self.S[i], self.Y[i], self.PH[i]

def blendJ(J1, J2, w):
    if w <= 0: return J1
    if w >= 1: return J2
    J = {k: J1[k] * (1 - w) + J2[k] * w for k in J1}
    for k in ('f', 's', 'tdir'):
        J[k] = J[k] / (np.linalg.norm(J[k]) + 1e-9)
    return J

def ball_in(J, arm):
    return J['el' + arm] * 0.45 + J['wr' + arm] * 0.55 + J['f'] * 0.04

def move_J(tr, p, rest='ready', carry=None, back=False):
    """Postura a partir de la pista: carrera si va rapido, postura de espera si esta parado, mezcla en medio."""
    pos, v, sp, yaw, ph = tr.at(p)
    if back: yaw = _wrap(yaw + math.pi)
    k = clamp(sp / 8.5, 0, 1)
    Jr = run_pose((pos[0], pos[1]), yaw, -ph if back else ph, speed=max(0.3, k), lean=0.22 if not back else -0.05, carry=carry)
    w = ease(clamp((sp - 0.5) / 1.8))
    if w >= 1: return Jr
    Js = stance_pose((pos[0], pos[1]), yaw, rest)
    if carry:
        Js = blendJ(Js, pose_joints((pos[0], pos[1]), yaw, pitch=0.3, legs=((0.5, 0.75), (0.5, 0.75)),
                                    arms=((0.55, 1.9, 0.05), (0.55, 1.9, 0.05))), 1.0)
    return blendJ(Js, Jr, w)

def move_person(tr, p, team, num, skin, rest='ready', ball=False, arm='R', back=False):
    J = move_J(tr, p, rest, carry=arm if ball else None, back=back)
    return P(J, team, num, skin, ball=ball_in(J, arm) if ball else None)

def shuffle_block(x, y, yaw, p, seed=0):
    """Bloqueo de pase: pasos cortos alternos hacia atras, no un muñeco que se desliza."""
    ph = p * 2.6 + seed * 0.37
    a = 0.18 * math.sin(ph * 2 * math.pi)
    return pose_joints((x, y, 0.9 + 0.02 * math.sin(ph * 4 * math.pi)), yaw, pitch=0.8,
                       legs=((0.95 + a, 1.05 + a * 0.5), (0.45 - a, 0.65 - a * 0.5)),
                       arms=((1.35 + 0.1 * math.sin(ph * 6.28 + 1), 0.4, 0.1), (1.35 + 0.1 * math.sin(ph * 6.28 + 2), 0.4, 0.1)),
                       head_pitch=-0.5, ground=True)

TR_QB = Track(lambda p: path(p, QB)[0], 0.25, math.pi)
TR_FUQ = Track(lambda p: path(p, FUQ)[0], 0.25, math.pi)
TR_TAT = Track(lambda p: path(p, TAT)[0], 0.2, 0.0)
TR_HAR = Track(lambda p: path(p, HAR)[0], 0.3, math.pi)
TR_WAR = Track(lambda p: path(p, WAR)[0], 0.4, 0.0)
TR_COV = [Track(lambda p, k=k: cov_pos(k, p)[0], 0.4, 0.0) for k in range(len(COV))]
TR_WR = [Track(lambda p, K=K: path(p, K)[0], 0.4, math.pi) for K in WR]

# ---------------------------------------------------------------- linea: bloqueos que se mantienen y persecucion
# Cada liniero de los Steelers tiene un rival. Mientras le bloquea se queda pegado a el, entre el rival y Bradshaw.
# Si el rival le gana (los dos de dentro, en ~1,5 s) se gira y le persigue. Tras el pase, todos corren hacia el balon.
OL_ASSIGN = [0, 1, 1, 2, 3]            # el center ayuda en el doble bloqueo sobre el 74
OL_OFF = [0.0, -0.35, 0.45, 0.0, 0.0]  # desplazamiento lateral en el doble bloqueo
DL_BEAT = [3.9, 1.5, 1.5, 3.9]         # cuando se libra cada defensor (o se suelta tras el pase)
P_REL = 3.9
def _simulate_line():
    n = len(PGRID); dt = 1.0 / HZ
    DL = np.zeros((4, n, 2)); OL = np.zeros((5, n, 2))
    dl = np.array([[59.1, y] for y in DL_Y]); ol = np.array([[60.9, y] for y in OL_Y])
    dlv = np.zeros((4, 2)); olv = np.zeros((5, 2))
    for gi, p in enumerate(PGRID):
        qb = path(max(p, 0), QB)[0]
        tgt_run = hpos(max(p, P_CATCH)) if p > P_CATCH else np.array(ball_state(p)[0][:2]) if ball_state(p)[0] is not None else qb
        for i in range(4):
            if p < 0: dl[i] = [59.1, DL_Y[i]]
            elif p < P_REL: dl[i] = path(p, DL_K[i])[0]
            else:      # tras el pase: se gira y corre hacia el balon, acelerando
                d = tgt_run + np.array([2.5 + i * 1.2, (i - 1.5) * 2.0]) - dl[i]
                want = d / (np.linalg.norm(d) + 1e-6) * min(6.5, 1.5 + (p - P_REL) * 4.0)
                dlv[i] += (want - dlv[i]) * min(1, 4 * dt); dl[i] = dl[i] + dlv[i] * dt
            DL[i, gi] = dl[i]
        for j in range(5):
            a = OL_ASSIGN[j]
            if p < 0: ol[j] = [60.9, OL_Y[j]]; OL[j, gi] = ol[j]; continue
            u = qb - dl[a]; u = u / (np.linalg.norm(u) + 1e-6); perp = np.array([-u[1], u[0]])
            hold = dl[a] + u * 0.85 + perp * OL_OFF[j]
            if p < DL_BEAT[a]:
                ol[j] = ol[j] + (hold - ol[j]) * min(1, 10 * dt) if p > 0.25 else ol[j] + (hold - ol[j]) * min(1, 3 * dt)
                olv[:] = olv * 0.9
            else:
                if p < P_REL:   # le han ganado: persigue a su rival por detras
                    goal = dl[a] - u * 0.2 + perp * (0.6 if OL_OFF[j] >= 0 else -0.6) + np.array([0.8, 0])
                    vmax = 5.5
                else:           # tras el pase: corre detras de la jugada
                    goal = tgt_run + np.array([4.0 + j * 1.3, (j - 2) * 2.2]); vmax = min(5.5, 1.0 + (p - P_REL) * 3.5)
                d = goal - ol[j]; dist = np.linalg.norm(d)
                want = d / (dist + 1e-6) * min(vmax, dist * 3)
                olv[j] += (want - olv[j]) * min(1, 5 * dt); ol[j] = ol[j] + olv[j] * dt
            OL[j, gi] = ol[j]
    return DL, OL

def qb_person(p):
    if p < 0:
        return P(stance_pose((61.0, 0.0), math.pi, 'qb'), 'GB', '12', 3)
    pos, v, sp, yaw, ph = TR_QB.at(p)
    if p < 1.55:                            # retrocede de espaldas a su zona, balon en las manos
        J = move_J(TR_QB, p, 'qb', carry='R', back=True)
        w = ease(clamp(p / 0.25))
        J = blendJ(stance_pose((61.0, 0.0), math.pi, 'qb'), J, w)
        return P(J, 'GB', '12', 3, ball=ball_in(J, 'R'))
    set_J = pose_joints((pos[0], pos[1]), math.pi + 0.1, pitch=0.12, legs=((0.3, 0.4), (0.25, 0.35)), arms=((0.9, 1.4, 0.1), (1.0, 1.5, 0.1)))
    if p < 2.3:
        J = blendJ(move_J(TR_QB, p, 'qb', carry='R', back=True), set_J, ease((p - 1.55) / 0.25))
        return P(J, 'GB', '12', 3, ball=(J['wrL'] + J['wrR']) / 2 + J['f'] * 0.06)
    if p < 3.25:
        Jr = move_J(TR_QB, p, 'ready', carry='R')
        J = blendJ(set_J, Jr, ease((p - 2.3) / 0.25))
        return P(J, 'GB', '12', 3, ball=ball_in(J, 'R'))
    tyaw = math.atan2(CATCH_PT[1] - pos[1], CATCH_PT[0] - pos[0])
    k = (p - 3.25) / 0.5
    J = throw_pose(pos[0], pos[1], tyaw, k)
    J = blendJ(move_J(TR_QB, 3.25, 'ready', carry='R'), J, ease((p - 3.25) / 0.12))
    bl = J['wrR'] + UP * 0.08 if p < P_THROW else None
    return P(J, 'GB', '12', 3, ball=bl)

REL = np.array([66.9, 4.5, 2.3])
def ball_state(p):
    """(pos, eje) del balon cuando no lo lleva nadie; None si va en la mano."""
    if p < 0: return np.array([LOS + 0.3, 0.0, 0.12]), np.array([1.0, 0, 0])
    if p < P_THROW: return None, None
    if p < P_HIT:
        u = (p - P_THROW) / (P_HIT - P_THROW)
        pos = REL + (CATCH_PT - REL) * u + np.array([0, 0, 4 * 5.0 * u * (1 - u)])
        ax = (CATCH_PT - REL); ax = ax / np.linalg.norm(ax) + np.array([0, 0, 0.3 - 0.6 * u])
        return pos, ax
    if p < P_CATCH - 0.12:
        u = (p - P_HIT) / (P_CATCH - 0.12 - P_HIT)
        tgt = np.array([TR_HAR.at(P_CATCH - 0.12)[0][0] + 0.25, TR_HAR.at(P_CATCH - 0.12)[0][1], 0.22])
        pos = CATCH_PT + (tgt - CATCH_PT) * u + np.array([0, 0, 4 * 2.0 * u * (1 - u)])
        return pos, np.array([math.cos(p * 17), 0.4, math.sin(p * 17)])
    return None, None

_DLA, _OLA = _simulate_line()
def _arr_fn(A):
    return lambda p: A[int(clamp((p - PGRID[0]) * HZ, 0, len(PGRID) - 1))]
TR_DL = [Track(_arr_fn(_DLA[i]), 0.3, 0.0) for i in range(4)]
TR_OL = [Track(_arr_fn(_OLA[j]), 0.25, math.pi) for j in range(5)]

def fuqua_person(p):
    if p < 0: return P(stance_pose((65.0, -1.5), math.pi, 'ready'), 'GB', '33', 2)
    pos, v, sp, yaw, ph = TR_FUQ.at(p)
    Jm = move_J(TR_FUQ, min(p, 4.75), 'ready')
    if p < 4.75: return P(Jm, 'GB', '33', 2)
    if p < P_HIT:   # se gira hacia el QB con los brazos arriba
        k = ease((p - 4.75) / 0.35)
        Jc = pose_joints((pos[0], pos[1]), lerp(math.pi, 0.15, k), pitch=0.15, legs=((0.35, 0.5), (0.1, 0.3)),
                         arms=((lerp(0.8, 2.5, k), 0.5, 0.15), (lerp(0.8, 2.5, k), 0.5, 0.15)))
        return P(blendJ(Jm, Jc, ease((p - 4.75) / 0.15)), 'GB', '33', 2)
    k = ease((p - P_HIT) / 0.7)            # golpeado por la espalda: cae hacia delante
    x = pos[0] + 0.9 * k; y = pos[1] + 0.2 * k
    J = pose_joints((x, y, lerp(0.98, 0.3, k)), 0.15, pitch=lerp(0.2, 1.45, k), legs=((lerp(0.3, 0.1, k), lerp(0.5, 0.4, k)), (lerp(0.1, 0.05, k), 0.3)),
                    arms=((lerp(2.5, 2.9, k), 0.3, 0.4), (lerp(2.5, 2.7, k), 0.3, 0.4)), ground=False)
    return P(J, 'GB', '33', 2)

def tatum_person(p):
    if p < 0: return P(stance_pose((45.0, -3.5), 0.0, 'ready'), 'DAL', '32', 4)
    pos, v, sp, yaw, ph = TR_TAT.at(p)
    Jm = move_J(TR_TAT, min(p, 4.95), 'ready')
    if p < 4.95: return P(Jm, 'DAL', '32', 4)
    if p < 5.7:
        k = ease((p - 4.95) / 0.3)
        Jh = pose_joints((pos[0], pos[1]), 0.25, pitch=lerp(0.4, 0.75, k), legs=((0.6, 0.6), (-0.1, 0.4)),
                         arms=((lerp(0.8, 1.5, k), 0.6, 0.3), (lerp(0.8, 1.5, k), 0.6, 0.3)))
        return P(blendJ(Jm, Jh, ease((p - 4.95) / 0.12)), 'DAL', '32', 4)
    Jh = pose_joints((pos[0], pos[1]), 0.25, pitch=0.75, legs=((0.6, 0.6), (-0.1, 0.4)), arms=((1.5, 0.6, 0.3), (1.5, 0.6, 0.3)))
    return P(blendJ(Jh, stance_pose((pos[0], pos[1]), 0.6, 'ready'), ease((p - 5.7) / 0.5)), 'DAL', '32', 4)

def harris_person(p):
    if p < 0: return P(stance_pose((65.0, 1.5), math.pi, 'ready'), 'GB', '32', 1)
    pos, v, sp, yaw, ph = TR_HAR.at(p)
    if p < 2.4:
        Jb = shuffle_block(pos[0], pos[1], math.pi, p, 7)
        return P(blendJ(stance_pose((65.0, 1.5), math.pi, 'ready'), Jb, ease(p / 0.3)), 'GB', '32', 1)
    carry = 'L' if p >= P_CATCH else None
    Jm = move_J(TR_HAR, p, 'ready', carry=carry)
    if p < 2.8:
        Jm = blendJ(shuffle_block(pos[0], pos[1], math.pi, 2.4, 7), Jm, ease((p - 2.4) / 0.4))
    if 5.75 <= p < 6.45:   # lo recoge a ras de suelo, sin dejar de correr
        k = math.sin(clamp((p - 5.75) / 0.7) * math.pi)
        Js = pose_joints((pos[0], pos[1], 0.74), yaw, pitch=1.0, legs=((1.2, 1.4), (0.5, 0.9)),
                         arms=((1.0, 0.3, 0.08), (1.0, 0.3, 0.08)), ground=False)
        J = blendJ(Jm, Js, ease(k))
        bl = None
        if p >= P_CATCH - 0.12:
            bl = (J['wrL'] + J['wrR']) / 2 + J['f'] * 0.07
            if p > P_CATCH + 0.05: bl = bl * (1 - ease((p - P_CATCH - 0.05) / 0.25)) + ball_in(J, 'L') * ease((p - P_CATCH - 0.05) / 0.25)
            bl[2] = max(bl[2], 0.14)
        return P(J, 'GB', '32', 1, ball=bl)
    if p < P_TD + 0.5:
        return P(Jm, 'GB', '32', 1, ball=ball_in(Jm, 'L') if carry else None)
    # en la end zone, balon en alto
    Jc = pose_joints((pos[0], pos[1]), math.pi - 0.4, pitch=0.0, legs=((0.1, 0.1), (-0.1, 0.1)), arms=((0.4, 0.4, 0.2), (2.8, 0.2, 0.2)))
    J = blendJ(Jm, Jc, ease((p - P_TD - 0.5) / 0.4))
    return P(J, 'GB', '32', 1, ball=ball_in(J, 'L') * (1 - ease((p - P_TD - 0.5) / 0.4)) + (Jc['wrR'] + UP * 0.08) * ease((p - P_TD - 0.5) / 0.4))

def warren_person(p):
    if p < 0: return P(stance_pose((40.0, -16.0), 0.0, 'ready'), 'DAL', '', 0)
    Jm = move_J(TR_WAR, min(p, 10.35), 'ready')
    if p < 10.35: return P(Jm, 'DAL', '', 0)
    pos = TR_WAR.at(10.35)[0]
    k = ease((p - 10.35) / 0.65)         # se lanza al placaje y se queda en el suelo; Harris pasa
    x = lerp(pos[0], 10.4, k); y = lerp(pos[1], -23.6, k)
    Jd = pose_joints((x, y, lerp(0.95, 0.3, k)), -1.75, pitch=lerp(0.5, 1.45, k), legs=((0.2, 0.3), (0.05, 0.2)),
                     arms=((lerp(1.5, 2.8, k), 0.2, 0.3), (lerp(1.5, 2.8, k), 0.2, 0.3)), ground=False)
    return P(blendJ(Jm, Jd, ease((p - 10.35) / 0.15)), 'DAL', '', 0)

def play_people(p, extra_refs=True):
    Pl = []
    sn = p >= 0
    for j, y in enumerate(OL_Y):
        if not sn:
            Pl.append(P(stance_pose((60.9, y), math.pi, '3pt'), 'GB', OL_N[j], j)); continue
        pos = TR_OL[j].at(p)[0]; a = OL_ASSIGN[j]
        dp = TR_DL[a].at(p)[0]
        yaw_b = math.atan2(dp[1] - pos[1], dp[0] - pos[0])
        Jb = shuffle_block(pos[0], pos[1], yaw_b, p, j)
        if p < DL_BEAT[a]:
            J = blendJ(stance_pose((60.9, y), math.pi, '3pt'), Jb, ease(p / 0.25))
        else:
            J = blendJ(Jb, move_J(TR_OL[j], p, 'ready'), ease((p - DL_BEAT[a]) / 0.3))
        Pl.append(P(J, 'GB', OL_N[j], j))
    for i in range(len(DL_K)):
        if not sn:
            Pl.append(P(stance_pose((59.1, DL_Y[i]), 0.0, '3pt'), 'DAL', DL_N[i], i + 1)); continue
        pos, v, sp, yaw, ph = TR_DL[i].at(p)
        qb = TR_QB.at(p)[0]
        Jb = shuffle_block(pos[0], pos[1], math.atan2(qb[1] - pos[1], qb[0] - pos[0]), p, i + 3)
        if p < DL_BEAT[i]:
            J = blendJ(stance_pose((59.1, DL_Y[i]), 0.0, '3pt'), Jb, ease(p / 0.25))
        else:
            J = blendJ(Jb, move_J(TR_DL[i], p, 'ready'), ease((p - DL_BEAT[i]) / 0.3))
            if i in (1, 2):      # se lanzan a por Bradshaw con los brazos arriba
                w = math.sin(clamp((p - 1.9) / 1.0) * math.pi)
                if w > 0:
                    Ja = pose_joints((pos[0], pos[1]), yaw, pitch=0.5, legs=((0.6, 0.7), (0.0, 0.3)), arms=((2.3, 0.3, 0.3), (2.3, 0.3, 0.3)))
                    J = blendJ(J, Ja, ease(w))
        Pl.append(P(J, 'DAL', DL_N[i], i + 1))
    for k in range(len(COV)):
        if not sn:
            a = np.array(COV[k]['K'][0][1:]); Pl.append(P(stance_pose((a[0], a[1]), 0.0, 'ready'), 'DAL', COV[k]['num'], k)); continue
        Pl.append(move_person(TR_COV[k], p, 'DAL', COV[k]['num'], k))
    for i in range(len(WR)):
        if not sn:
            a = WR[i][0]; Pl.append(P(stance_pose((a[1], a[2]), math.pi, 'ready' if i < 2 else '3pt'), 'GB', WR_N[i], i)); continue
        Pl.append(move_person(TR_WR[i], p, 'GB', WR_N[i], i))
    Pl += [qb_person(p), fuqua_person(p), tatum_person(p), harris_person(p), warren_person(p)]
    if extra_refs:
        Pl.append(P(stance_pose((70.5, -4.0), math.pi, 'stand'), 'REF', skin=0))   # el arbitro, detras del ataque
    bp, ax = ball_state(p)
    if bp is not None: Pl.append(ball_prop(bp, ax, 1.25, 0.3))
    return Pl

def game_clock(p):
    s = 22 if p < 0 else max(5, int(math.ceil(22 - p * (17 / P_TD) - 1e-6)))
    return f'4TH  0:{s:02d}'

def play_bug(d, p):
    score_bug(d, 7, 6, game_clock(p))   # el marcador no cambia hasta que el arbitro lo da por bueno

# ---------------------------------------------------------------- vistas
def side_cam(fx, fy=0.0, z=10.0, f=2700, back=7.0, side=-44.0):
    return cam((fx + back, side, z), (fx - 2.0, fy * 0.5, -0.4), f)

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

def seg2(i, default):
    return SEGS[i][1][0] if len(SEGS[i]) > 1 else default

def pmap(t, T0, T1, p0, p1):
    return lerp(p0, p1, clamp((t - T0) / max(1e-3, T1 - T0)))

def low_cam_collision(p, k=0.0):
    """Camara baja a media distancia, lateral, para el choque y la recogida."""
    c = cam((38.5 - 1.5 * k, -11.0, 2.2), (35.8, 0.3, 1.2), 2700)
    return c

# ---------------------------------------------------------------- escenas por frase
def S0(t, T0, T1):
    lt = t - T0
    t2 = seg2(0, T1 - 2.2)
    if t < t2 - 0.1:
        img, c = wide_ez(t, k_desc=lt / 4.0)
        img = finish(img); d = ImageDraw.Draw(img)
        B.headline(d, 470, '40 YEARS', 170)
        if lt > 1.3: B.headline(d, 650, '0 PLAYOFF WINS', 130, YEL)
        return img
    p = pmap(t, t2 - 0.1, T1, 4.85, 5.55)
    c = low_cam_collision(p)
    img = FG.draw_people(world(c), c, play_people(p), t)
    img = finish(img); d = ImageDraw.Draw(img)
    play_bug(d, p)
    return img

def S1(t, T0, T1):
    lt = t - T0; dur = T1 - T0
    img, c = wide_ez(t, k_desc=lt / dur)
    img = finish(img); d = ImageDraw.Draw(img)
    lower_third(d, 1180, 'THREE RIVERS STADIUM', 'PITTSBURGH · DECEMBER 23', acc=PITG, t=lt)
    return img

def S2(t, T0, T1):
    lt = t - T0
    c = cam((70 - lt * 0.8, -42, 9), (58 - lt * 0.8, 0.5, 0.0), 2900)
    img = FG.draw_people(world(c), c, play_people(-1.0), t)
    img = finish(img); d = ImageDraw.Draw(img)
    lower_third(d, 1180, 'RAIDERS VS. STEELERS', 'AFC DIVISIONAL PLAYOFF', acc=PITG, t=lt)
    return img

STAB_K = [(0, 70.0, 0.0), (0.9, 66.5, 0.5), (1.4, 67.0, 5.0), (2.2, 75.0, 11.0), (3.8, 92.0, 13.5), (4.5, 101.0, 13.0), (9, 102.5, 12.5)]
TR_STAB = Track(lambda p: path(p, STAB_K)[0], 0.3, 0.0)

def S3(t, T0, T1):
    # carrera de 30 yardas de Stabler (zurdo, #12) hacia la end zone de x=100; luego el marcador
    lt = t - T0
    t2 = seg2(3, T1 - 2.0)
    K = STAB_K
    p = pmap(t, T0, t2 + 0.3, 0.3, 4.6) if t < t2 + 0.3 else 4.6 + (t - t2 - 0.3) * 0.6
    pos = TR_STAB.at(p)[0]
    Pl = []
    Jm = move_J(TR_STAB, min(p, 4.5), 'ready', carry='L')
    if p < 4.5:
        Pl.append(P(Jm, 'DAL', '12', 3, ball=ball_in(Jm, 'L')))
    else:
        Jc = pose_joints((pos[0], pos[1]), 0.3, legs=((0.1, 0.1), (-0.1, 0.1)), arms=((2.8, 0.2, 0.2), (0.4, 0.4, 0.2)))
        w = ease((p - 4.5) / 0.4); J = blendJ(Jm, Jc, w)
        Pl.append(P(J, 'DAL', '12', 3, ball=ball_in(J, 'L') * (1 - w) + (Jc['wrL'] + UP * 0.08) * w))
    r = random.Random(3)
    for k in range(5):   # los Steelers persiguen
        lag = 0.7 + k * 0.35
        q, _ = path(max(0.6, p - lag), K)
        y = q[1] - 3 - k * 1.5 if k % 2 else q[1] + 2 + k
        Pl.append(carrier(q[0] - 1.5, y, 0.25, p * 2.2 + k * 0.3, 'GB', ['59', '58', '47', '24', '75'][k], k, speed=0.9, ball=False))
    for k, (x, y) in enumerate([(71, -3), (71, 3), (73, -6), (70.5, 0.5)]):   # linea de los Raiders
        Pl.append(carrier(x + p * 2.5, y + p * 1.5, 0.4, p * 2, 'DAL', ['76', '65', '78', '00'][k], k, speed=0.6, ball=False))
    if t < t2:
        c = side_cam(pos[0] - 4, pos[1], z=10, f=2500, back=-8)
        c = cam((pos[0] - 7, pos[1] - 24, 6), (pos[0] + 2, pos[1], 0.8), 3000)
        scored = False
    else:
        c = cam((121, 20, 8), (99, 12, 0.8), 3200)
        scored = p >= 4.5
    img = FG.draw_people(world(c, cheer=0.0), c, Pl, t)
    img = finish(img); d = ImageDraw.Draw(img)
    score_bug(d, 7 if scored else 0, 6, '4TH  1:13' if scored else '4TH  1:17', flash='OAK' if scored else None)
    lower_third(d, 1180, 'KEN STABLER #12', '30-YARD TOUCHDOWN RUN', acc=OAKS, t=lt)
    return img

def S4(t, T0, T1):
    lt = t - T0
    c = cam((70 + lt * 0.3, -38, 7.0), (60 + lt * 0.3, 0.5, 0.2), 3500)
    img = FG.draw_people(world(c), c, play_people(-0.5), t)
    img = finish(img); d = ImageDraw.Draw(img)
    s2 = SEGS[4]
    score_bug(d, 7, 6, '4TH  0:22', extra='4TH & 10' if t >= s2[min(1, len(s2) - 1)][0] - 0.1 else None)
    if t < s2[min(1, len(s2) - 1)][0] - 0.1:
        B.headline(d, 600, '0:22', 230, YEL)
    elif len(s2) > 2 and t >= s2[2][0] - 0.1:
        B.headline(d, 600, 'NO TIMEOUTS', 150, (255, 80, 70))
    else:
        lower_third(d, 1180, "PITTSBURGH'S OWN 40", '4TH AND 10', acc=PITG, t=t - s2[min(1, len(s2) - 1)][0])
    return img

def S5(t, T0, T1):
    p = pmap(t, T0, T1, -0.3, 2.55)
    c = cam((73, -27, 6.5), (63.5, 1.5, 0.5), 3900)   # camara de banda alta, cerrada sobre el pocket
    img = FG.draw_people(world(c), c, play_people(p), t)
    img = finish(img); d = ImageDraw.Draw(img)
    play_bug(d, p)
    lower_third(d, 1180, 'TERRY BRADSHAW #12', 'STEELERS QB', acc=PITG, t=t - T0)
    return img

def S6(t, T0, T1):
    p = pmap(t, T0, T1, 2.55, 4.5)
    bp, _ = ball_state(p)
    fx = 64.0 if bp is None else clamp(bp[0] + 2.0, 40.0, 64.0)
    c = cam((fx + 8, -38, 8), (fx - 2, 1.0, 0.4), 3400)
    img = FG.draw_people(world(c), c, play_people(p), t)
    img = finish(img); d = ImageDraw.Draw(img)
    play_bug(d, p)
    if p > P_THROW:
        lower_third(d, 1180, 'TO FRENCHY FUQUA #33', 'DOWN THE MIDDLE', acc=PITG, t=p - P_THROW)
    return img

def S7(t, T0, T1):
    t2 = seg2(7, T1 - 0.6)
    if t < t2 - 0.05:
        p = pmap(t, T0, t2 - 0.05, 4.4, P_HIT)
    else:
        p = P_HIT + (t - t2 + 0.05) * 0.08
    c = cam((41.5, -13.0, 2.8), (35.5, 0.2, 1.2), 2600 + 300 * clamp((t - T0) / (T1 - T0)))
    img = FG.draw_people(world(c), c, play_people(p), t)
    img = finish(img); d = ImageDraw.Draw(img)
    play_bug(d, p)
    if t < t2 - 0.05:
        lower_third(d, 1180, 'JACK TATUM #32', 'RAIDERS SAFETY', acc=OAKS, t=t - T0)
    else:
        if (t - t2) < 0.12:
            img.paste(Image.new('RGB', img.size, (255, 255, 255)), (0, 0), Image.new('L', img.size, 150))
            d = ImageDraw.Draw(img)
        B.headline(d, 620, 'BANG!', 220, YEL)
    return img

def S8(t, T0, T1):
    p = pmap(t, T0, T1, P_HIT, 6.05)
    bp, _ = ball_state(p)
    bx = bp[0] if bp is not None else SCOOP_PT[0]
    c = cam((bx + 2.0, -15.0, 3.2), (bx - 0.5, -0.6, 0.8), 2300)   # sigue al balon hacia atras
    img = FG.draw_people(world(c), c, play_people(p), t)
    img = finish(img); d = ImageDraw.Draw(img)
    play_bug(d, p)
    B.headline(d, 560, 'BACKWARD', 150, YEL)
    return img

def S9(t, T0, T1):
    p = pmap(t, T0, T1, 5.8, 6.7)
    c = cam((45.5, -8.5, 1.4), (41.8, -2.0, 0.45), 2100)
    img = FG.draw_people(world(c), c, play_people(p), t)
    img = finish(img); d = ImageDraw.Draw(img)
    play_bug(d, p)
    lower_third(d, 1180, 'FRANCO HARRIS #32', 'ROOKIE RUNNING BACK', acc=PITG, t=t - T0)
    return img

def S10(t, T0, T1):
    p = pmap(t, T0, T1, 6.7, 11.0)
    h = hpos(p)
    c = cam((h[0] + 7, -42, 5.5), (h[0] - 2, h[1], 0.7), 4300)
    img = FG.draw_people(world(c), c, play_people(p), t)
    img = finish(img); d = ImageDraw.Draw(img)
    play_bug(d, p)
    if p > 10.2:
        lower_third(d, 1180, 'PAST THE LAST TACKLE', 'AT THE 10', acc=PITG, t=p - 10.2)
    elif p > 7.2:
        lower_third(d, 1180, 'DOWN THE LEFT SIDELINE', None, acc=PITG, t=p - 7.2)
    return img

def S11(t, T0, T1):
    p = pmap(t, T0, T1 + 0.2, 11.2, 12.6)
    c = cam((-19, -25, 6.5), (1.0, -22.0, 0.8), 3400)       # camara de end zone, detras de los postes
    img = FG.draw_people(world(c, cheer=1.0 if p > P_TD else 0.0), c, play_people(p), t)
    img = finish(img); d = ImageDraw.Draw(img)
    play_bug(d, p)
    if p > P_TD: B.headline(d, 600, 'TOUCHDOWN!', 170, YEL)
    return img

def S12(t, T0, T1):
    t2 = seg2(12, T0 + 1.0)
    if t < t2 - 0.1:
        lt = t - T0
        c = cam((24.0 - lt * 1.2, -7.0, 6.0), (35.6, 0.3, 1.2), 3000 + lt * 500)
        img = FG.draw_people(world(c), c, play_people(P_HIT), t)
        img = finish(img); d = ImageDraw.Draw(img)
        play_bug(d, P_HIT)
        tag(d, c, np.array([35.6, 0.5, 2.0]), 'FUQUA #33', dy=-260)
        tag(d, c, np.array([34.9, 0.25, 1.9]), 'TATUM #32', dy=-120)
        B.headline(d, 1180, 'WHO TOUCHED IT?', 120, YEL)
        return img
    lt = t - t2
    img = blurred_stadium(); d = ImageDraw.Draw(img)
    B.headline(d, 430, 'THE RULE', 150, YEL)
    B.headline(d, 570, 'BACK THEN', 110)
    rows = [('BALL TOUCHES TATUM', 'HARRIS CAN CATCH IT', (40, 130, 70)), ('BALL TOUCHES ONLY FUQUA', 'INCOMPLETE PASS', (190, 30, 30))]
    for i, (a, b, col) in enumerate(rows):
        k = ease((lt - i * 0.6) / 0.35)
        if k <= 0: continue
        y = 720 + i * 230; x = 70 - int((1 - k) * 60)
        d.rounded_rectangle([x, y, W - 70, y + 200], 12, fill=(12, 14, 22))
        d.rectangle([x, y, x + 14, y + 200], fill=col)
        d.text((x + 44, y + 60), a, font=BF(64), fill=WHITE, anchor='lm')
        d.text((x + 44, y + 140), '= ' + b, font=BF(64), fill=YEL, anchor='lm')
    return img

def ref_walk(t, T0, T1):
    u = clamp((t - T0) / max(1e-3, (T1 - T0) * 0.8))
    x = lerp(41.0, 44.9, ease(u)); y = lerp(-31.0, -40.3, ease(u))
    return x, y, u

def S13(t, T0, T1):
    lt = t - T0
    x, y, u = ref_walk(t, T0, T1)
    if u < 1.0:
        J = run_pose((x, y), math.atan2(-40.3 + 31.0, 44.9 - 41.0), lt * 1.5, speed=0.3, lean=0.05)
    else:
        J = pose_joints((x, y), -math.pi / 2, legs=((0.06, 0.08), (-0.06, 0.08)), arms=((0.1, 0.3, 0.12), (2.3, 2.4, 0.35)))
    Pl = [P(J, 'REF', skin=0)]
    for k, (px, py, tm, n) in enumerate([(36.0, -27.0, 'GB', '75'), (38.5, -25.5, 'DAL', '34'), (48.0, -26.0, 'GB', '68'), (34.0, -24.0, 'DAL', '41')]):
        Pl.append(P(stance_pose((px, py), -math.pi / 2 + (k - 1.5) * 0.3, 'hands_hips' if k % 2 else 'stand'), tm, n, k))
    c = cam((43.0, -22.0, 3.2), (44.2, -40.0, 1.2), 2600)
    img = FG.draw_people(world(c), c, Pl, t)
    img = finish(img); d = ImageDraw.Draw(img)
    score_bug(d, 7, 6, '4TH  0:05', extra='RULING PENDING')
    lower_third(d, 1180, 'REFEREE FRED SWEARINGEN', 'TO THE PHONE BY THE FIELD', acc=YEL, t=lt)
    return img

def S14(t, T0, T1):
    lt = t - T0
    t2 = seg2(14, T1 - 0.7)
    k = ease((lt - 0.6) / 0.6)
    J = pose_joints((44.6, -38.8), math.pi / 2, legs=((0.06, 0.08), (-0.06, 0.08)),
                    arms=((lerp(0.1, 3.0, k), 0.1, 0.12), (lerp(0.1, 3.0, k), 0.1, 0.12)))
    Pl = [P(J, 'REF', skin=0)]
    r = random.Random(5)
    for k2 in range(9):   # jugadores de los Steelers celebrando en el campo
        px = 30 + k2 * 3.0 + r.uniform(-1, 1); py = -22 + r.uniform(-4, 6)
        a = 2.7 if k > 0.5 and k2 % 2 == 0 else 0.3
        Pl.append(P(pose_joints((px, py), -math.pi / 2 + r.uniform(-.5, .5), legs=((0.1, 0.1), (-0.1, 0.1)), arms=((a, 0.2, 0.2), (a, 0.2, 0.2))), 'GB', str(r.choice([75, 68, 52, 82, 47, 24, 59])), k2))
    c = cam((47.0, -50.0, 7.6), (44.0, -28.0, 0.8), 1700)
    img = FG.draw_people(world(c, cheer=1.0 if k > 0.5 else 0.0), c, Pl, t)
    img = finish(img); d = ImageDraw.Draw(img)
    score_bug(d, 7, 12 if k > 0.5 else 6, '4TH  0:05', flash='PIT' if k > 0.5 else None)
    if t >= t2 - 0.1:
        B.headline(d, 600, 'TOUCHDOWN', 170, YEL)
    return img

def S15(t, T0, T1):
    lt = t - T0
    c = cam((-16, -30, 13), (14, -8, -0.5), 1500)
    Pl = []
    r = random.Random(11)
    for k in range(26):   # aficionados que saltan al campo (quedaban 5 segundos)
        sx = r.uniform(-6, 30); sy = -26.7 - r.uniform(0.5, 1.5)
        u = clamp((lt - k * 0.06) / 2.0)
        px = sx + r.uniform(-2, 6) * u; py = lerp(sy, r.uniform(-24, -6), u)
        Pl.append(P(run_pose((px, py), 1.4 + r.uniform(-0.6, 0.6), lt * 2 + k, speed=0.6, lean=0.1), 'COACH', skin=k))
    for k in range(8):
        px = r.uniform(-4, 4); py = r.uniform(-24, -16)
        Pl.append(P(pose_joints((px, py), r.uniform(-2, 2), legs=((0.1, 0.1), (-0.1, 0.1)), arms=((2.7, 0.2, 0.2), (2.7, 0.2, 0.2))), 'GB', str(r.choice([32, 75, 68, 52, 82, 12])), k))
    img = FG.draw_people(world(c, cheer=1.0), c, Pl, t)
    img = finish(img); d = ImageDraw.Draw(img)
    score_bug(d, 7, 13, '4TH  0:05', flash='PIT')
    B.headline(d, 620, '13–7', 230, YEL)
    return img

def S16(t, T0, T1):
    lt = t - T0
    img = blurred_stadium(); d = ImageDraw.Draw(img)
    B.headline(d, 440, 'FIRST PLAYOFF WIN', 120, YEL)
    B.headline(d, 570, 'IN 40 YEARS', 110)
    rows = [('1933', 'STEELERS FOUNDED'), ('1947', 'FIRST PLAYOFF GAME: LOST 21–0'), ('1972', 'FIRST PLAYOFF WIN')]
    for i, (yr, txt) in enumerate(rows):
        k = ease((lt - i * 0.45) / 0.35)
        if k <= 0: continue
        y = 720 + i * 130; x = 70 - int((1 - k) * 60)
        last = i == 2
        d.rounded_rectangle([x, y, W - 70, y + 108], 10, fill=(12, 14, 22) if not last else (44, 36, 8))
        d.rectangle([x, y, x + 12, y + 108], fill=PITG if not last else YEL)
        d.text((x + 40, y + 54), yr, font=BF(62), fill=YEL, anchor='lm')
        d.text((x + 180, y + 54), txt, font=BF(56), fill=WHITE, anchor='lm')
    return img

def S17(t, T0, T1):
    lt = t - T0; dur = T1 - T0
    p = pmap(t, T0, T1, 5.9, 6.5)
    c = cam((45.5 - lt * 0.3, -8.5, 1.4), (41.8, -2.0, 0.45), 2100 + lt * 120)
    img = FG.draw_people(world(c), c, play_people(p), t)
    img = finish(img); d = ImageDraw.Draw(img)
    if lt > dur * 0.45:
        B.headline(d, 520, 'THE IMMACULATE', 120, YEL)
        B.headline(d, 660, 'RECEPTION', 150, YEL)
    return img

def S18(t, T0, T1):
    lt = t - T0
    c = cam((52.0 + lt * 0.4, 9.0, 7.0), (35.4, 0.3, 1.1), 2800 + lt * 300)
    img = FG.draw_people(world(c), c, play_people(P_HIT + 0.02), t)
    img = img.convert('L').convert('RGB')
    img = finish(img); d = ImageDraw.Draw(img)
    tag(d, c, np.array([35.3, 0.5, 2.0]), 'FUQUA?', dy=-230)
    tag(d, c, np.array([34.9, 0.25, 1.9]), 'TATUM?', dy=-90)
    B.headline(d, 1170, 'STILL UNSOLVED', 120, YEL)
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
