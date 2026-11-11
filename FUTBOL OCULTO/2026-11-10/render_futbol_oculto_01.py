# -*- coding: utf-8 -*-
"""Fútbol Oculto · Vídeo 1 · Atlético Aviación (1939-41)
Render vertical 1080x1920 30 fps. Un único estadio 3D (cámara pinhole) que se transforma:
Metropolitano dañado → Mestalla (promoción) → Chamartín (campeón). B/N → color.
Uso: python3 render_futbol_oculto_01.py [--preview N] [--frames a b] [--audio voz.mp3]
Lee times.json (lista de [inicio, fin] por frase) si existe.
"""
import os, sys, json, math, random, subprocess, argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.environ.get("FO_FONTS", os.path.join(HERE, "fonts"))
LOGO = os.environ.get("FO_LOGO", os.path.join(HERE, "futbol_oculto_logo.png"))
HANDLE = "@futbol.oculto"

FALLBACK = "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf"
_fc = {}
def font(name, size):
    key = (name, size)
    if key not in _fc:
        p = os.path.join(FONTS, {"anton": "Anton-Regular.ttf", "bebas": "BebasNeue-Regular.ttf",
                                 "grad": "Graduate-Regular.ttf"}[name])
        try:
            _fc[key] = ImageFont.truetype(p, size)
        except OSError:
            _fc[key] = ImageFont.truetype(FALLBACK, int(size * 0.8))
    return _fc[key]

SENTENCES = [l.strip() for l in open(os.path.join(HERE, "guion.txt"), encoding="utf-8") if l.strip()]
N = len(SENTENCES)

def load_times():
    p = os.path.join(HERE, "times.json")
    if os.path.exists(p):
        return json.load(open(p))
    tot, w = 74.0, [len(s) for s in SENTENCES]
    t, out = 0.4, []
    for x in w:
        d = (tot - 0.4 - 0.35 * N) * x / sum(w)
        out.append([t, t + d]); t += d + 0.35
    return out

TIMES = load_times()
DUR = TIMES[-1][1] + 3.2

def seg_at(t):
    for i in range(N - 1, -1, -1):
        if t >= TIMES[i][0] - (0.0 if i else 99):
            s = TIMES[i][0] if i else 0.0
            e = TIMES[i + 1][0] if i + 1 < N else DUR
            return i, (t - s), (e - s)
    return 0, t, TIMES[1][0]

def ease(x):
    x = min(1, max(0, x)); return x * x * (3 - 2 * x)

def lerp(a, b, u):
    return a + (b - a) * u

# ----------------------------------------------------------------------------- cámara
class Cam:
    def __init__(self, pos, tgt, f=1350):
        self.c = np.array(pos, float); t = np.array(tgt, float)
        fw = t - self.c; fw /= np.linalg.norm(fw)
        r = np.cross(fw, [0, 0, 1.0]); r /= np.linalg.norm(r)
        u = np.cross(r, fw)
        self.R = np.stack([r, u, fw]); self.f = f
    def proj(self, P):
        P = np.asarray(P, float)
        d = (P - self.c) @ self.R.T
        z = d[..., 2]
        zs = np.where(z > 0.5, z, 0.5)
        x = W / 2 + self.f * d[..., 0] / zs
        y = H * 0.40 - self.f * d[..., 1] / zs
        return x, y, z

def camlerp(a, b, u):
    return Cam(lerp(np.array(a[0]), np.array(b[0]), u), lerp(np.array(a[1]), np.array(b[1]), u),
               lerp(a[2] if len(a) > 2 else 1350, b[2] if len(b) > 2 else 1350, u))

# ----------------------------------------------------------------------------- estadio
rng = np.random.default_rng(7)
PL, PW = 105.0, 68.0
ROWS = 22

def build_crowd():
    pts, col, hat = [], [], []
    coats = np.array([[40, 42, 48], [62, 58, 52], [30, 30, 34], [85, 78, 66], [52, 60, 72],
                      [96, 92, 86], [120, 70, 60], [70, 52, 40], [200, 196, 186], [150, 140, 120]])
    def add(xs, ys, zs):
        n = len(xs)
        pts.append(np.stack([xs, ys, zs], 1))
        c = coats[rng.integers(0, len(coats), n)] + rng.integers(-12, 12, (n, 3))
        col.append(np.clip(c, 0, 255)); hat.append(rng.random(n) < 0.55)
    for r in range(ROWS):
        z = 0.9 + 0.52 * r + 0.75
        for side in (-1, 1):
            xs = np.arange(-6, PL + 6, 0.62)
            xs = xs + rng.uniform(-0.1, 0.1, len(xs))
            yv = (PW + 5.5 + 0.85 * r) if side > 0 else (-5.5 - 0.85 * r)
            add(xs, np.full(len(xs), yv), np.full(len(xs), z))
            ys = np.arange(-4, PW + 4, 0.62); ys = ys + rng.uniform(-0.1, 0.1, len(ys))
            xv = (PL + 5.5 + 0.85 * r) if side > 0 else (-5.5 - 0.85 * r)
            add(np.full(len(ys), xv), ys, np.full(len(ys), z))
    P = np.concatenate(pts); C = np.concatenate(col); Hh = np.concatenate(hat)
    keep = rng.random(len(P)) < 0.93
    return P[keep], C[keep], Hh[keep]

CROWD_P, CROWD_C, CROWD_H = build_crowd()
SKIN = np.array([214, 170, 140])

def stand_quads():
    """escalones: (polígono 3D, tono)"""
    q = []
    for r in range(ROWS):
        z0, z1 = 0.9 + 0.52 * r, 0.9 + 0.52 * (r + 1)
        d0, d1 = 5.0 + 0.85 * r, 5.0 + 0.85 * (r + 1)
        shade = 128 + (r % 2) * 10
        # lado largo lejano / cercano
        for s in (1, -1):
            y0 = PW + d0 if s > 0 else -d0; y1 = PW + d1 if s > 0 else -d1
            q.append(([(-8 - .85 * r, y0, z0), (PL + 8 + .85 * r, y0, z0), (PL + 8 + .85 * r, y0, z1), (-8 - .85 * r, y0, z1)], shade - 25, ('y', s)))
            q.append(([(-8 - .85 * r, y0, z1), (PL + 8 + .85 * r, y0, z1), (PL + 8 + .85 * r, y1, z1), (-8 - .85 * r, y1, z1)], shade, ('y', s)))
            x0 = PL + d0 if s > 0 else -d0; x1 = PL + d1 if s > 0 else -d1
            q.append(([(x0, -5, z0), (x0, PW + 5, z0), (x0, PW + 5, z1), (x0, -5, z1)], shade - 25, ('x', s)))
            q.append(([(x0, -5, z1), (x0, PW + 5, z1), (x1, PW + 5, z1), (x1, -5, z1)], shade, ('x', s)))
    return q

STANDQ = stand_quads()
BACK = 5.0 + 0.85 * ROWS

# ----------------------------------------------------------------------------- dibujo de escena
def poly(dr, cam, P, fill, outline=None, width=1, zn=1.0):
    P = np.array(P, float)
    d = (P - cam.c) @ cam.R.T
    if np.all(d[:, 2] < zn): return
    if np.any(d[:, 2] < zn):   # recorte contra el plano cercano
        out = []
        for k in range(len(d)):
            a, b = d[k], d[(k + 1) % len(d)]
            ia, ib = a[2] >= zn, b[2] >= zn
            if ia: out.append(a)
            if ia != ib:
                v = (zn - a[2]) / (b[2] - a[2]); out.append(a + v * (b - a))
        if len(out) < 3: return
        d = np.array(out)
    x = W / 2 + cam.f * d[:, 0] / d[:, 2]; y = H * 0.40 - cam.f * d[:, 1] / d[:, 2]
    dr.polygon(list(zip(x, y)), fill=fill, outline=outline)

def line3(dr, cam, P, fill, wm=0.12):
    P = np.array(P); x, y, z = cam.proj(P)
    for i in range(len(P) - 1):
        if z[i] < 1 or z[i + 1] < 1:
            continue
        w = max(1, int(cam.f * wm / ((z[i] + z[i + 1]) / 2) + 0.5))
        dr.line([(x[i], y[i]), (x[i + 1], y[i + 1])], fill=fill, width=w)

def circle3(cx, cy, r, a0=0, a1=2 * math.pi, n=48):
    return [(cx + r * math.cos(a), cy + r * math.sin(a), 0.02) for a in np.linspace(a0, a1, n)]

def draw_sky(img, st):
    a = np.zeros((H, W, 3), np.uint8)
    top = np.array([118, 150, 186]) if not st.get('war') else np.array([120, 118, 112])
    bot = np.array([196, 206, 214]) if not st.get('war') else np.array([170, 160, 150])
    g = np.linspace(0, 1, H)[:, None]
    a[:] = (top * (1 - g) + bot * g).astype(np.uint8)[:, None, :]
    img.paste(Image.fromarray(a))
    dr = ImageDraw.Draw(img, 'RGBA')
    rr = random.Random(3)
    for i in range(9):
        cx = (rr.uniform(-200, 1300) + st['t'] * 6) % 1500 - 200; cy = rr.uniform(40, 520)
        for k in range(7):
            dr.ellipse([cx + rr.uniform(-90, 90) - 90, cy + rr.uniform(-25, 25) - 30,
                        cx + rr.uniform(-90, 90) + 90, cy + rr.uniform(-25, 25) + 30], fill=(240, 240, 238, 70))

def draw_stands(img, cam, st):
    dr = ImageDraw.Draw(img, 'RGBA')
    hide = st.get('hide', set())
    quads = [q for q in STANDQ if q[2] not in hide]
    def dist(q):
        p = np.mean(np.array(q[0]), 0); return -np.linalg.norm(p - cam.c)
    quads.sort(key=dist)
    for P, sh, _ in quads:
        c = (sh, sh - 4, sh - 10) if not st.get('war') else (sh - 20, sh - 24, sh - 26)
        poly(dr, cam, P, c)
    # tribuna cubierta en el lado lejano
    if ('y', 1) not in hide:
        for x in np.arange(14, 92, 9.75):
            line3(dr, cam, [(x, PW + BACK - 1, 0.9 + 0.52 * ROWS), (x, PW + BACK - 1, 16.0)], (60, 58, 56), 0.35)
        poly(dr, cam, [(12, PW + 7, 15.2), (93, PW + 7, 15.2), (93, PW + BACK + 1, 16.6), (12, PW + BACK + 1, 16.6)], (78, 74, 70))
        poly(dr, cam, [(12, PW + 7, 12.6), (93, PW + 7, 12.6), (93, PW + 7, 15.2), (12, PW + 7, 15.2)], (236, 232, 222))
        poly(dr, cam, [(-10, PW + BACK, 0.9 + .52 * ROWS), (12, PW + BACK, 0.9 + .52 * ROWS), (12, PW + BACK, 16.6), (-10, PW + BACK, 13)], (150, 146, 138))
        poly(dr, cam, [(93, PW + BACK, 0.9 + .52 * ROWS), (115, PW + BACK, 0.9 + .52 * ROWS), (115, PW + BACK, 13), (93, PW + BACK, 16.6)], (150, 146, 138))
    # público (vectorizado)
    if st.get('crowd', 1.0) > 0:
        a = np.array(img)
        P, C, Hh = CROWD_P, CROWD_C, CROWD_H
        m = np.ones(len(P), bool)
        if ('y', -1) in hide: m &= P[:, 1] > -1
        if ('y', 1) in hide: m &= P[:, 1] < PW + 1
        if ('x', -1) in hide: m &= P[:, 0] > -1
        if ('x', 1) in hide: m &= P[:, 0] < PL + 1
        dens = st.get('crowd', 1.0)
        if dens < 1: m &= (np.arange(len(P)) * 0.6180339 % 1) < dens
        P, C, Hh = P[m], C[m], Hh[m]
        bob = 0.12 * st.get('cheer', 0) * np.abs(np.sin(st['t'] * 9 + P[:, 0] * 1.7 + P[:, 1]))
        Pz = P.copy(); Pz[:, 2] += bob
        x, y, z = cam.proj(Pz)
        s = cam.f * 0.46 / np.maximum(z, 0.5)
        ok = (z > 2) & (x > -10) & (x < W + 10) & (y > -10) & (y < H + 10)
        idx = np.where(ok)[0]; idx = idx[np.argsort(-z[idx])]
        x, y, s, C, Hh = x[idx], y[idx], s[idx], C[idx], Hh[idx]
        bw = np.maximum(1, (s * 0.9)).astype(int); bh = np.maximum(1, (s * 1.25)).astype(int)
        hr = np.maximum(1, (s * 0.42)).astype(int)
        xi = x.astype(int); yi = y.astype(int)
        mx = int(min(14, bw.max() if len(bw) else 1)); my = int(min(18, bh.max() if len(bh) else 1))
        for dy in range(my):
            for dx in range(-mx // 2, mx - mx // 2):
                k = (dy < bh) & (np.abs(dx) <= bw // 2)
                yy = np.clip(yi[k] - dy, 0, H - 1); xx = np.clip(xi[k] + dx, 0, W - 1)
                sh = (C[k] * (1 - 0.18 * (dx > 0))).astype(np.uint8)
                a[yy, xx] = sh
        mh = int(min(8, hr.max() if len(hr) else 1))
        for dy in range(-mh, mh + 1):
            for dx in range(-mh, mh + 1):
                k = (dx * dx + dy * dy) <= hr * hr
                yy = np.clip(yi[k] - bh[k] - hr[k] + dy, 0, H - 1); xx = np.clip(xi[k] + dx, 0, W - 1)
                hk = Hh[k] & (dy < 0)
                c = np.where(hk[:, None], np.array([34, 32, 30]), SKIN).astype(np.uint8)
                a[yy, xx] = c
        img.paste(Image.fromarray(a))
    if st.get('war'):
        dr = ImageDraw.Draw(img, 'RGBA')
        rr = random.Random(11)
        for i in range(14):   # escombros / tramos rotos de grada
            xw = rr.uniform(0, PL); r0 = rr.randint(2, 14); ww = rr.uniform(3, 9)
            z0 = 0.9 + 0.52 * r0; yv = PW + 5 + 0.85 * r0
            poly(dr, cam, [(xw, yv, z0), (xw + ww, yv, z0), (xw + ww * 0.7, yv + 3.4, z0 + 2.6), (xw + 0.3 * ww, yv + 2.8, z0 + 2.9)], (62, 58, 54))
            for k in range(6):
                bx = xw + rr.uniform(0, ww); by = PW + 4.5; poly(dr, cam, [(bx, by, 0), (bx + .8, by, 0), (bx + .4, by - .5, .6)], (90, 86, 80))

def draw_sign(img, cam, text):
    if not text: return
    x, y, z = cam.proj(np.array([52.5, PW + 7, 13.9]))
    if z < 2: return
    size = int(cam.f * 2.6 / z)
    if size < 6: return
    dr = ImageDraw.Draw(img)
    f = font('bebas', size)
    dr.text((x, y), text, font=f, fill=(150, 30, 34), anchor='mm')

def draw_pitch(img, cam, st):
    dr = ImageDraw.Draw(img, 'RGBA')
    war = st.get('war')
    base = (70, 118, 58) if not war else (112, 108, 70)
    poly(dr, cam, [(-4.5, -4.5, 0), (PL + 4.5, -4.5, 0), (PL + 4.5, PW + 4.5, 0), (-4.5, PW + 4.5, 0)], (120, 108, 84))
    poly(dr, cam, [(-3, -3, 0), (PL + 3, -3, 0), (PL + 3, PW + 3, 0), (-3, PW + 3, 0)], base)
    for i in range(0, 12, 2):
        x0 = i * PL / 12; x1 = (i + 1) * PL / 12
        poly(dr, cam, [(x0, -3, 0), (x1, -3, 0), (x1, PW + 3, 0), (x0, PW + 3, 0)], (96, 150, 78, 120) if not war else (130, 124, 84, 110))
    # zonas gastadas (porterías y centro)
    for cx in (5, 52.5, 100):
        pts = [(cx + (6 if cx != 52.5 else 9) * math.cos(a) * 1.4, 34 + 9 * math.sin(a), 0.01) for a in np.linspace(0, 2 * math.pi, 20)]
        poly(dr, cam, pts, (138, 128, 92, 70))
    wc = (238, 238, 230) if not war else (200, 196, 180)
    L = [[(0, 0, .02), (PL, 0, .02), (PL, PW, .02), (0, PW, .02), (0, 0, .02)], [(PL / 2, 0, .02), (PL / 2, PW, .02)]]
    for s in (0, 1):
        x0 = 0 if s == 0 else PL; d = 1 if s == 0 else -1
        L.append([(x0, 34 - 20.16, .02), (x0 + d * 16.5, 34 - 20.16, .02), (x0 + d * 16.5, 34 + 20.16, .02), (x0, 34 + 20.16, .02)])
        L.append([(x0, 34 - 9.16, .02), (x0 + d * 5.5, 34 - 9.16, .02), (x0 + d * 5.5, 34 + 9.16, .02), (x0, 34 + 9.16, .02)])
        ang = math.acos(5.5 / 9.15)
        if s == 0: L.append(circle3(11, 34, 9.15, -ang, ang, 20))
        else: L.append(circle3(PL - 11, 34, 9.15, math.pi - ang, math.pi + ang, 20))
    L.append(circle3(PL / 2, 34, 9.15))
    for l in L: line3(dr, cam, l, wc, 0.12)
    for px in (11, PL / 2, PL - 11):
        x, y, z = cam.proj(np.array([px, 34, 0.02]))
        if z > 1:
            r = max(1.5, cam.f * 0.15 / z); dr.ellipse([x - r, y - r * 0.5, x + r, y + r * 0.5], fill=wc)
    for cx, cy in ((0, 0), (PL, 0), (0, PW), (PL, PW)):   # banderines
        line3(dr, cam, [(cx, cy, 0), (cx, cy, 1.5)], (230, 220, 200), 0.05)
        poly(dr, cam, [(cx, cy, 1.5), (cx, cy + (0.6 if cy == 0 else -0.6), 1.35), (cx, cy, 1.2)], (220, 40, 40))

def draw_goal(img, cam, gx):
    dr = ImageDraw.Draw(img, 'RGBA')
    d = -2.0 if gx == 0 else 2.0
    y0, y1, h = 34 - 3.66, 34 + 3.66, 2.44
    net = (235, 235, 235, 120)
    for k in np.linspace(0, 1, 9):
        line3(dr, cam, [(gx, lerp(y0, y1, k), h), (gx + d, lerp(y0, y1, k), h * 0.8), (gx + d, lerp(y0, y1, k), 0)], net, 0.03)
    for k in np.linspace(0, 1, 5):
        line3(dr, cam, [(gx + d, y0, h * 0.8 * k), (gx + d, y1, h * 0.8 * k)], net, 0.03)
    for y in (y0, y1):
        for k in np.linspace(0, 1, 5):
            line3(dr, cam, [(gx, y, h * k), (gx + d, y, h * .8 * k)], net, 0.03)
    line3(dr, cam, [(gx, y0, 0), (gx, y0, h), (gx, y1, h), (gx, y1, 0)], (250, 250, 246), 0.13)

# ----------------------------------------------------------------------------- jugadores
KITS = {
    'ath': dict(shirt=[(205, 28, 40), (246, 244, 238)], shorts=(28, 44, 110), socks=(30, 40, 90), top=(205, 28, 40)),
    'osa': dict(shirt=[(186, 24, 36)], shorts=(20, 26, 60), socks=(20, 24, 40), top=(186, 24, 36)),
    'gk1': dict(shirt=[(48, 48, 52)], shorts=(240, 238, 232), socks=(40, 40, 44), top=(48, 48, 52), cap=True),
    'gk2': dict(shirt=[(62, 70, 58)], shorts=(30, 30, 34), socks=(30, 30, 34), top=(62, 70, 58)),
    'coach': dict(coat=(48, 44, 40), shirt=[(48, 44, 40)], shorts=(36, 34, 34), socks=(36, 34, 34), top=(36, 34, 34)),
}

def limb(dr, p0, a, L):
    return (p0[0] + L * math.sin(a), p0[1] + L * math.cos(a))

def draw_player(img, foot, hpx, kit, phase, run, face, arms_up=0.0, jump=0.0, shadow=True):
    """foot=(x,y) pantalla; hpx=altura en px; face=+1 derecha/-1 izquierda"""
    if hpx < 6: return
    dr = ImageDraw.Draw(img, 'RGBA')
    fx, fy = foot; s = hpx
    if shadow:
        dr.ellipse([fx - .16 * s, fy - .025 * s, fx + .16 * s, fy + .025 * s], fill=(0, 0, 0, 70))
    fy -= jump * s
    K = KITS[kit]
    lw = max(2, int(.075 * s))
    hip = (fx, fy - .50 * s); sh = (fx + face * .02 * s, fy - .80 * s)
    sw = math.sin(phase) * 0.75 * run
    skin = (212, 168, 136)
    # piernas (atrás primero)
    for k, sg in ((1, -1), (0, 1)):
        a1 = sg * sw * face; kn = limb(dr, hip, a1, .26 * s)
        a2 = a1 - face * (0.15 + 0.7 * run * max(0, -sg * math.sin(phase + 0.6)))
        an = limb(dr, kn, a2, .23 * s)
        col_sock = K['socks']
        dr.line([hip, kn], fill=K['shorts'], width=int(lw * 1.7))
        dr.line([kn, an], fill=col_sock, width=lw)
        dr.line([(kn[0], kn[1]), (kn[0] + (an[0] - kn[0]) * .18, kn[1] + (an[1] - kn[1]) * .18)], fill=K['top'], width=lw + 1)
        dr.ellipse([an[0] - lw * .9 + face * lw * .5, an[1] - lw * .5, an[0] + lw * .9 + face * lw * .5, an[1] + lw * .6], fill=(36, 26, 20))
    # pantalón ancho (hasta la rodilla)
    dr.polygon([(hip[0] - .11 * s, hip[1] - .02 * s), (hip[0] + .11 * s, hip[1] - .02 * s),
                (hip[0] + .13 * s + face * sw * .08 * s, hip[1] + .17 * s), (hip[0] - .13 * s + face * sw * .08 * s, hip[1] + .17 * s)], fill=K['shorts'])
    # torso (camiseta, a rayas si toca)
    tl = (sh[0] - .12 * s, sh[1]); tr = (sh[0] + .12 * s, sh[1])
    bl = (hip[0] - .10 * s, hip[1]); br = (hip[0] + .10 * s, hip[1])
    if kit == 'coach':
        dr.polygon([(sh[0] - .13 * s, sh[1]), (sh[0] + .13 * s, sh[1]), (fx + .15 * s, fy - .22 * s), (fx - .15 * s, fy - .22 * s)], fill=K['coat'])
    else:
        cols = K['shirt']
        dr.polygon([tl, tr, br, bl], fill=cols[0])
        if len(cols) > 1:
            n = 5
            for i in range(1, n, 2):
                u0, u1 = i / n, (i + 1) / n
                dr.polygon([(lerp(tl[0], tr[0], u0), tl[1]), (lerp(tl[0], tr[0], u1), tl[1]),
                            (lerp(bl[0], br[0], u1), bl[1]), (lerp(bl[0], br[0], u0), bl[1])], fill=cols[1])
    # brazos (manga larga)
    arm_c = K['shirt'][0] if kit != 'coach' else K['coat']
    for sg in (-1, 1):
        if arms_up > 0:
            a = math.pi + sg * (0.5 + 0.3 * math.sin(phase))
            el = limb(dr, (sh[0] + sg * .1 * s, sh[1]), lerp(-sg * sw * face * 0.8, a, arms_up), .17 * s)
            ha = limb(dr, el, lerp(-sg * sw * face * 0.8 + face * 0.5, a, arms_up), .16 * s)
        elif kit == 'coach':
            el = limb(dr, (sh[0] + sg * .1 * s, sh[1]), sg * 0.12, .17 * s); ha = limb(dr, el, -sg * 0.35, .14 * s)
        else:
            el = limb(dr, (sh[0] + sg * .1 * s, sh[1]), -sg * sw * face * 0.8, .17 * s)
            ha = limb(dr, el, -sg * sw * face * 0.8 - face * 0.6 * run, .16 * s)
        dr.line([(sh[0] + sg * .1 * s, sh[1] + .02 * s), el, ha], fill=arm_c, width=int(lw * 1.05))
        if kit != 'coach':
            dr.ellipse([ha[0] - lw * .55, ha[1] - lw * .55, ha[0] + lw * .55, ha[1] + lw * .55], fill=skin)
    # cuello y cabeza (sin cara: escala de retransmisión)
    hc = (sh[0] + face * .015 * s, sh[1] - .1 * s); hr = .065 * s
    dr.line([(sh[0], sh[1] + .01 * s), (hc[0], hc[1] + hr)], fill=skin, width=lw)
    dr.ellipse([hc[0] - hr, hc[1] - hr * 1.1, hc[0] + hr, hc[1] + hr], fill=skin)
    dr.chord([hc[0] - hr * 1.02, hc[1] - hr * 1.15, hc[0] + hr * 1.02, hc[1] + hr * .6], 180 if face > 0 else 180, 360, fill=(40, 30, 24))
    if K.get('cap') or kit == 'coach':
        dr.chord([hc[0] - hr * 1.1, hc[1] - hr * 1.25, hc[0] + hr * 1.1, hc[1] + hr * .3], 180, 360, fill=(36, 34, 32) if kit == 'coach' else (30, 30, 30))
        dr.line([(hc[0], hc[1] - hr * .4), (hc[0] + face * hr * 1.6, hc[1] - hr * .35)], fill=(36, 34, 32), width=max(1, int(hr * .35)))
    if kit != 'coach':  # cuello de camiseta clásico
        dr.line([(sh[0] - .05 * s, sh[1] + .005 * s), (sh[0] + .05 * s, sh[1] + .005 * s)], fill=(246, 244, 238), width=max(1, lw // 2))

# formaciones 2-3-5 (época): atacan hacia +x (ath) / -x (osa)
F235 = [(3, 34), (18, 24), (18, 44), (32, 16), (32, 34), (32, 52), (46, 8), (47, 22), (48, 34), (47, 46), (46, 60)]

def team_positions(team, ball, t, attack_right=True, kickoff=False):
    out = []
    for i, (bx, by) in enumerate(F235):
        if kickoff:
            x = bx * 0.92 + 2 if i else 3
            if i >= 6: x = 50.5 - (0 if i != 8 else 0)
        else:
            x = bx + (0.55 * (ball[0] - 52.5) if i else 0.08 * (ball[0] - 52.5)) + 8
            x = min(x, 100)
        y = by + 0.22 * (ball[1] - 34) + 1.2 * math.sin(t * 0.9 + i)
        x += 0.8 * math.sin(t * 0.7 + i * 2.1)
        if not attack_right:
            x = PL - x; y = PW - y
        out.append([x, y])
    return out

def ball_path(keys, u):
    """keys: [(u, x, y, z)] lineal por tramos con altura parabólica"""
    for k in range(len(keys) - 1):
        u0, *a = keys[k]; u1, *b = keys[k + 1]
        if u0 <= u <= u1:
            v = (u - u0) / max(1e-6, u1 - u0)
            x = lerp(a[0], b[0], v); y = lerp(a[1], b[1], v)
            z = lerp(a[2], b[2], v) + 4 * a[3] * v * (1 - v) if len(a) > 3 else lerp(a[2], b[2], v)
            return np.array([x, y, z])
    k = keys[-1] if u > keys[-1][0] else keys[0]
    return np.array(k[1:4])

def draw_ball(img, cam, b):
    dr = ImageDraw.Draw(img, 'RGBA')
    gx, gy, gz = cam.proj(np.array([b[0], b[1], 0.0]))
    x, y, z = cam.proj(np.array([b[0], b[1], b[2] + 0.11]))
    if z < 1: return
    r = max(2.5, cam.f * 0.11 / z)
    dr.ellipse([gx - r * 1.2, gy - r * .35, gx + r * 1.2, gy + r * .35], fill=(0, 0, 0, 80))
    dr.ellipse([x - r, y - r, x + r, y + r], fill=(122, 76, 40), outline=(70, 44, 22))
    dr.arc([x - r * .7, y - r * .7, x + r * .7, y + r * .7], 200, 320, fill=(176, 126, 80), width=max(1, int(r * .25)))

def draw_players(img, cam, ath, osa, t, ball=None, carrier=None, celebrate=0.0, prev=None):
    items = []
    for team, P in (('ath', ath), ('osa', osa)):
        for i, p in enumerate(P):
            kit = team if i else ('gk1' if team == 'ath' else 'gk2')
            items.append((kit, p, i))
    if ball is not None:
        items.append(('ball', ball, -1))
    def zz(it):
        p = it[1]; return -np.linalg.norm(np.array([p[0], p[1], 0]) - cam.c)
    items.sort(key=zz)
    for kit, p, i in items:
        if kit == 'ball':
            draw_ball(img, cam, p); continue
        x, y, z = cam.proj(np.array([p[0], p[1], 0.0]))
        if z < 1.5 or x < -100 or x > W + 100: continue
        _, yh, _ = cam.proj(np.array([p[0], p[1], 1.78]))
        hpx = y - yh
        run = 1.0 if celebrate == 0 else 0.6
        face = 1 if (kit in ('ath', 'gk1')) else -1
        if ball is not None and celebrate == 0:
            bx, _, _ = cam.proj(np.array([ball[0], ball[1], 0])); face = 1 if bx > x else -1
        ph = t * 10.5 + i * 1.3 + (0 if kit[0] == 'a' else 2)
        draw_player(img, (x, y), hpx, kit, ph, run, face,
                    arms_up=celebrate if kit == 'ath' else 0, jump=(0.12 * abs(math.sin(t * 6 + i)) * celebrate if kit == 'ath' else 0))

# ----------------------------------------------------------------------------- gráficos TV
def text_stroke(dr, xy, txt, f, fill, stroke=(0, 0, 0), sw=6, anchor='mm'):
    dr.text(xy, txt, font=f, fill=fill, anchor=anchor, stroke_width=sw, stroke_fill=stroke)

def score_bug(img, a, b, half, alpha=1.0, flash=0.0):
    if alpha <= 0: return
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
    x0, y0 = 60, 190; f = font('bebas', 58); fs = font('bebas', 34)
    dr.rounded_rectangle([x0, y0, x0 + 76 + f.getlength('AT. AVIACIÓN') + 146 + f.getlength('OSASUNA') + 50, y0 + 84], 10, fill=(16, 18, 24, 235))
    for i in range(6):  # chip rojiblanco
        dr.rectangle([x0 + 12 + i * 8, y0 + 14, x0 + 20 + i * 8, y0 + 70], fill=(205, 28, 40) if i % 2 == 0 else (246, 244, 238))
    xa = x0 + 76
    dr.text((xa, y0 + 42), "AT. AVIACIÓN", font=f, fill=(255, 255, 255), anchor='lm')
    xs = xa + f.getlength("AT. AVIACIÓN") + 18
    dr.rectangle([xs, y0 + 8, xs + 110, y0 + 76], fill=(250, 210, 30) if flash > 0 else (240, 240, 240))
    dr.text((xs + 55, y0 + 43), f"{a}-{b}", font=f, fill=(10, 10, 10), anchor='mm')
    xo = xs + 128
    dr.text((xo, y0 + 42), "OSASUNA", font=f, fill=(255, 255, 255), anchor='lm')
    xe = xo + f.getlength("OSASUNA") + 16
    dr.rectangle([xe, y0 + 14, xe + 18, y0 + 70], fill=(186, 24, 36))
    dr.rounded_rectangle([x0, y0 + 90, x0 + 190, y0 + 136], 8, fill=(250, 210, 30, 235))
    dr.text((x0 + 95, y0 + 114), half, font=fs, fill=(10, 10, 10), anchor='mm')
    if alpha < 1: ov.putalpha(Image.eval(ov.getchannel('A'), lambda v: int(v * alpha)))
    img.alpha_composite(ov) if img.mode == 'RGBA' else img.paste(ov, (0, 0), ov)

def panel(img, title, rows, u, y=560, hl=None):
    """tabla tipo TV: rows=[(pos, nombre, nota, color_nota)]"""
    a = ease(u * 4)
    if a <= 0: return
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
    x0 = int(lerp(-900, 70, a)); w = 940
    rh = 96
    dr.rectangle([x0, y, x0 + w, y + 96], fill=(250, 210, 30, 245))
    dr.text((x0 + 30, y + 50), title, font=font('anton', 62), fill=(12, 12, 12), anchor='lm')
    for k, (pos, name, note, nc) in enumerate(rows):
        yy = y + 96 + k * rh; ak = ease(u * 4 - 0.5 - k * 0.35)
        if ak <= 0: continue
        bg = (18, 20, 28, int(235 * ak)) if hl != k else (120, 20, 26, int(240 * ak))
        dr.rectangle([x0, yy, x0 + w, yy + rh - 6], fill=bg)
        dr.text((x0 + 30, yy + 45), pos, font=font('anton', 50), fill=(250, 210, 30, int(255 * ak)), anchor='lm')
        nx = x0 + (110 if len(pos) <= 2 else 200)
        dr.text((nx, yy + 45), name.strip(), font=font('bebas', 64), fill=(255, 255, 255, int(255 * ak)), anchor='lm')
        if note:
            dr.text((x0 + w - 30, yy + 45), note, font=font('bebas', 52), fill=nc + (int(255 * ak),), anchor='rm')
    img.paste(ov, (0, 0), ov)

def stamp(img, txt, u, color=(206, 30, 36), y=820, size=150, rot=-8):
    a = ease((u) * 5)
    if a <= 0: return
    f = font('anton', size)
    tw = int(f.getlength(txt)) + 80
    lay = Image.new('RGBA', (tw, size + 70), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle([6, 6, tw - 6, size + 64], 14, outline=color + (255,), width=12)
    d.text((tw // 2, (size + 70) // 2), txt, font=f, fill=color + (255,), anchor='mm')
    sc = lerp(2.2, 1.0, a)
    lay = lay.resize((max(1, int(tw * sc)), max(1, int((size + 70) * sc))), Image.LANCZOS).rotate(rot, expand=True, resample=Image.BICUBIC)
    lay.putalpha(Image.eval(lay.getchannel('A'), lambda v: int(v * min(1, a * 1.4))))
    img.paste(lay, (W // 2 - lay.width // 2, y - lay.height // 2), lay)

def name_plate(img, top, big, u, y=600, sub=None, morph=None):
    a = ease(u * 4)
    if a <= 0: return
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
    x0 = 60; w = 960
    dr.rectangle([x0, y, x0 + int(w * a), y + 70], fill=(250, 210, 30, 245))
    dr.text((x0 + 26, y + 36), top, font=font('bebas', 54), fill=(12, 12, 12), anchor='lm')
    dr.rectangle([x0, y + 70, x0 + int(w * a), y + 230], fill=(16, 18, 26, 238))
    for i in range(10):
        dr.rectangle([x0 + int(w * a) - 26, y + 70 + i * 16, x0 + int(w * a) - 10, y + 86 + i * 16], fill=(205, 28, 40) if i % 2 == 0 else (246, 244, 238))
    txt = big
    if morph:  # (texto_antes, texto_despues, progreso)
        b, c, p = morph
        n = max(len(b), len(c)); k = int(p * n)
        txt = (c[:k] + b[k:]) if p < 1 else c
    f = font('anton', 104)
    while f.getlength(txt) > w - 90 and f.size > 40: f = font('anton', f.size - 6)
    dr.text((x0 + 30, y + 150), txt, font=f, fill=(255, 255, 255), anchor='lm')
    if sub:
        dr.rectangle([x0, y + 230, x0 + int(w * 0.62 * a), y + 290], fill=(205, 28, 40, 240))
        dr.text((x0 + 26, y + 260), sub, font=font('bebas', 48), fill=(255, 255, 255), anchor='lm')
    if a < 1: ov.putalpha(Image.eval(ov.getchannel('A'), lambda v: int(v * a)))
    img.paste(ov, (0, 0), ov)

def telestrator(img, cam, p, label, u):
    a = ease(u * 3)
    if a <= 0: return
    dr = ImageDraw.Draw(img, 'RGBA')
    x, y, z = cam.proj(np.array([p[0], p[1], 0.0]))
    _, yh, _ = cam.proj(np.array([p[0], p[1], 1.9]))
    h = y - yh; rx = h * 0.55
    dr.arc([x - rx, y - h * 1.12, x + rx, y + h * 0.12], -90, -90 + 360 * a, fill=(250, 214, 30), width=10)
    if a > 0.7:
        f = font('bebas', 64); tw = f.getlength(label)
        bx = min(W - tw - 60, max(30, x - tw / 2)); by = y - h * 1.12 - 110
        dr.rectangle([bx - 18, by - 6, bx + tw + 18, by + 70], fill=(250, 214, 30, 240))
        dr.text((bx, by + 32), label, font=f, fill=(10, 10, 10), anchor='lm')

def biplane(dr, x, y, s, t):
    c = (40, 44, 40)
    dr.polygon([(x - 1.6 * s, y), (x + 1.4 * s, y - .12 * s), (x + 1.6 * s, y + .05 * s), (x - 1.4 * s, y + .18 * s)], fill=c)
    dr.polygon([(x - .2 * s, y - .55 * s), (x + .55 * s, y - .55 * s), (x + .45 * s, y - .45 * s), (x - .3 * s, y - .45 * s)], fill=c)
    dr.polygon([(x - .25 * s, y + .05 * s), (x + .5 * s, y + .02 * s), (x + .42 * s, y + .14 * s), (x - .33 * s, y + .16 * s)], fill=c)
    dr.line([(x, y - .5 * s), (x + .05 * s, y + .05 * s)], fill=c, width=max(1, int(s * .05)))
    dr.line([(x + .35 * s, y - .5 * s), (x + .38 * s, y + .05 * s)], fill=c, width=max(1, int(s * .05)))
    dr.polygon([(x - 1.6 * s, y), (x - 1.75 * s, y - .38 * s), (x - 1.45 * s, y - .02 * s)], fill=c)
    pr = .35 * s * abs(math.sin(t * 40))
    dr.line([(x + 1.62 * s, y - pr), (x + 1.62 * s, y + pr + .05 * s)], fill=(70, 70, 70), width=max(1, int(s * .04)))

# ----------------------------------------------------------------------------- subtítulos
def chunks(sentence):
    words = sentence.replace('…', '… ').split()
    out, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= 3 or w[-1] in ',.:?…;':
            out.append(cur); cur = []
    if cur: out.append(cur)
    return out

def subtitles(img, t):
    for i, (s, e) in enumerate(TIMES):
        if s <= t <= e + 0.25:
            ch = chunks(SENTENCES[i]); words = [w for c in ch for w in c]
            lens = np.array([len(w) + 2 for w in words], float); cum = np.cumsum(lens) / lens.sum()
            u = (t - s) / max(0.01, e - s); wi = int(np.searchsorted(cum, min(u, 0.999)))
            k = 0
            for c in ch:
                if wi < k + len(c): break
                k += len(c)
            dr = ImageDraw.Draw(img)
            f = font('anton', 112)
            txt = [w.upper() for w in c]
            while sum(f.getlength(w + ' ') for w in txt) > W - 100 and f.size > 60: f = font('anton', f.size - 6)
            tot = sum(f.getlength(w + ' ') for w in txt) - f.getlength(' ')
            x = W / 2 - tot / 2; y = 1430
            for j, w in enumerate(txt):
                col = (255, 222, 0) if (k + j) == wi else (255, 255, 255)
                dr.text((x, y), w, font=f, fill=col, anchor='lm', stroke_width=9, stroke_fill=(0, 0, 0))
                x += f.getlength(w + ' ')
            return

# ----------------------------------------------------------------------------- post (B/N, grano)
def grade(img, sat, grain, t, vign=0.0):
    a = np.asarray(img).astype(np.float32)
    if sat < 0.999:
        g = a @ np.array([0.299, 0.587, 0.114], np.float32)
        g = g[..., None]
        sep = np.array([1.03, 1.0, 0.93], np.float32) * (1 - sat) + sat  # ligero tono de época
        a = (g + sat * (a - g)) * sep
    if grain > 0:
        r = np.random.default_rng(int(t * 30)).normal(0, 10 * grain, (H // 2, W // 2)).astype(np.float32)
        r = np.repeat(np.repeat(r, 2, 0), 2, 1)
        a += r[..., None]
    if vign > 0:
        yy, xx = np.ogrid[:H, :W]
        v = 1 - vign * (((xx - W / 2) / (W * .75)) ** 2 + ((yy - H / 2) / (H * .7)) ** 2)
        a *= v[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

# ----------------------------------------------------------------------------- dirección por frase
SIDE = lambda bx, z=26, f=1150: ((bx, -6, z), (bx, 30, 0), f)
FOLLOW = lambda b: Cam((b[0], -18, 10), (b[0], b[1] + 9, 0), 3600)
CELEB = lambda u: camlerp(((50, 11, 5.0), (52.5, 32, 1.2), 1450), ((54, 15, 3.6), (52.5, 32, 1.3), 1550), u)
HIDE_SIDE = {('y', -1)}
HIDE_END_L = {('x', -1)}

def scene(t):
    i, lt, ld = seg_at(t); u = lt / max(ld, 0.01)
    st = dict(t=t, hide=HIDE_SIDE, crowd=1.0)
    sat, grain, vign = 0.0, 0.7, 0.35
    sign = "METROPOLITANO"
    ath = osa = None; ball = None; celebrate = 0.0; bug = None; overlays = []
    camd = camlerp(SIDE(40), SIDE(62), u)

    def match_static(kick=True):
        b = np.array([52.5, 34, 0])
        return team_positions('ath', b, t, True, kick), team_positions('osa', b, t, False, kick), b

    if i == 0:   # gancho: campeones… ¿descendidos?
        sat, grain, vign = 1.0, 0.25, 0.25; sign = "CHAMARTÍN"; st['cheer'] = 1
        camd = CELEB(u)
        b = np.array([52.5, 30, 0]); ath = [[52.5 + 9 * math.cos(k / 11 * 6.28 + t * .3), 30 + 5 * math.sin(k / 11 * 6.28 + t * .3)] for k in range(11)]
        osa = []; celebrate = 1.0
        overlays.append(lambda im, cam: stamp(im, "CAMPEÓN DE LIGA", u * 2, (250, 210, 30), y=640, size=130, rot=0))
        overlays.append(lambda im, cam: stamp(im, "DESCENDIDO", u * 2 - 0.9, (210, 30, 36), y=860, size=150))
    elif i == 1:
        sat = 0.0; st['crowd'] = 0.8
        camd = camlerp(SIDE(30, 26), SIDE(52, 22), u)
        ath, osa, ball = match_static(); ath = ath; ball = None
        overlays.append(lambda im, cam: panel(im, "PRIMERA DIVISIÓN 35-36", [("…", "", "", (255, 255, 255)), ("↓", "ATHLETIC DE MADRID", "DESCENSO", (255, 90, 90))], u, hl=1))
    elif i == 2:
        st['crowd'] = max(0, 1 - u * 1.6); st['war'] = u > 0.5; sat = 0
        camd = camlerp(SIDE(56, 26), SIDE(64, 34), u)
        overlays.append(lambda im, cam: stamp(im, "LIGA SUSPENDIDA", u * 1.5 - 0.3, (230, 230, 225), y=820, size=120, rot=-4))
    elif i == 3:
        st['crowd'] = 0; st['war'] = True; sign = "METROPOLITANO"
        camd = camlerp(((60, 10, 9), (52, 75, 6), 1150), ((44, 18, 7), (52, 76, 7), 1250), u)
        st['hide'] = HIDE_SIDE
    elif i == 4:  # aviones del Aviación Nacional
        st['crowd'] = 0.15; st['war'] = True
        camd = camlerp(((52, -10, 6), (52, 70, 22), 1150), ((52, -10, 6), (52, 70, 30), 1150), u)
        st['planes'] = u
    elif i == 5:
        st['crowd'] = 0.35; sign = ""
        camd = camlerp(((52, -10, 6), (52, 70, 26), 1150), SIDE(52, 24), ease(u * 1.5))
        overlays.append(lambda im, cam: name_plate(im, "4 DE OCTUBRE · ACUERDO", "", u, y=560, sub="CLUB AVIACIÓN NACIONAL",
                                                    morph=("ATHLETIC DE MADRID", "ATHLETIC AVIACIÓN", ease(u * 2 - 0.6))))
    elif i == 6:
        st['crowd'] = 0.35; sign = ""
        camd = camlerp(SIDE(52, 24), SIDE(58, 26), u)
        overlays.append(lambda im, cam: panel(im, "SOBRE EL PAPEL…", [("2ª", "ATHLETIC AVIACIÓN", "SEGUNDA", (255, 90, 90))], u, hl=0))
    elif i == 7:
        st['crowd'] = 0.5; sign = ""
        camd = camlerp(SIDE(58, 26), ((52, 2, 12), (52, 60, 6), 1500), ease(u))
        overlays.append(lambda im, cam: stamp(im, "LA SUERTE", u * 1.3, (250, 210, 30), y=760, size=150, rot=-5))
    elif i == 8:
        st['crowd'] = 0; st['war'] = True; sign = ""
        camd = camlerp(SIDE(20, 22), SIDE(34, 22), u)
        overlays.append(lambda im, cam: panel(im, "PRIMERA DIVISIÓN 39-40", [("X", "REAL OVIEDO", "ESTADIO DESTRUIDO", (255, 120, 120))], u, hl=0))
    elif i == 9:
        st['crowd'] = 0.6; sign = ""
        camd = camlerp(SIDE(34, 22), SIDE(52, 22), u)
        overlays.append(lambda im, cam: panel(im, "PRIMERA DIVISIÓN 39-40", [("X", "REAL OVIEDO", "NO JUEGA", (255, 120, 120)),
                                                                          ("?", "PLAZA LIBRE", "", (255, 255, 255))], u, hl=1 if int(t * 3) % 2 else None))
    elif i == 10:  # Mestalla, presentación desde detrás de la portería
        sign = "MESTALLA"; st['cheer'] = 0.4; st['hide'] = HIDE_END_L
        camd = camlerp(((-15, 34, 10), (40, 34, 0), 1250), ((-11, 34, 7.5), (46, 34, 0), 1350), u)
        ath, osa, ball = match_static(True)
        if u > 0.8:
            ball = np.array([lerp(52.5, 46, ease((u - .8) * 5)), 34, 0])
        bug = ("0", "0", "1ª PARTE")
    elif i == 11:  # gol de Osasuna (Vergara)
        sign = "MESTALLA"; st['cheer'] = 0.6
        keys = [(0, 44, 30, 0), (0.35, 26, 40, 0, 0.5), (0.6, 13, 36, 0), (0.8, -0.8, 32.5, 1.2), (1, -1.6, 32.5, 0.2)]
        ball = ball_path(keys, min(1, u * 1.15))
        ath = team_positions('ath', ball, t, True); osa = team_positions('osa', ball, t, False)
        near = min(range(1, 11), key=lambda k: (osa[k][0] - ball[0]) ** 2 + (osa[k][1] - ball[1]) ** 2)
        if u < 0.65: osa[near] = [ball[0] + 0.7, ball[1] + 0.2]
        camd = FOLLOW((max(14, ball[0]), ball[1]))
        scored = u * 1.15 > 0.8
        bug = ("0", "1" if scored else "0", "1ª PARTE", scored)
    elif i == 12:  # remontada 3-1
        sign = "MESTALLA"; st['cheer'] = 1.0
        keys = [(0, 58, 32, 0), (0.25, 76, 20, 0, 0.6), (0.45, 90, 32, 0), (0.6, 105.8, 35.5, 1.0), (1, 106.6, 35.5, 0.2)]
        ball = ball_path(keys, min(1, u * 1.2))
        ath = team_positions('ath', ball, t, True); osa = team_positions('osa', ball, t, False)
        near = min(range(1, 11), key=lambda k: (ath[k][0] - ball[0]) ** 2 + (ath[k][1] - ball[1]) ** 2)
        if u * 1.2 < 0.58: ath[near] = [ball[0] - 0.7, ball[1] - 0.2]
        camd = FOLLOW((min(91, ball[0]), ball[1]))
        uu = u * 1.2
        sc = "0" if uu < 0.6 else ("1" if uu < 0.7 else ("2" if uu < 0.8 else "3"))
        bug = (sc, "1", "2ª PARTE", 0.6 < uu < 0.95)
        if uu > 0.7: celebrate = ease((uu - 0.7) * 4)
    elif i == 13:  # Zamora en el banquillo
        sign = "MESTALLA"
        camd = camlerp(((48, -16, 4.5), (53, -2, 1.2), 1500), ((50, -14, 4.0), (53, -2, 1.3), 1700), u)
        st['bench'] = True
        b = np.array([70, 30, 0]); ath = team_positions('ath', b, t, True); osa = team_positions('osa', b, t, False)
        overlays.append(lambda im, cam: telestrator(im, cam, (53, -3.2), "RICARDO ZAMORA · ENTRENADOR", u))
        bug = ("3", "1", "FINAL")
    elif i == 14:  # Chamartín: vuelve el color, campeón
        sign = "CHAMARTÍN"; st['cheer'] = 1.0
        sat = ease(u * 1.6); grain = lerp(0.7, 0.25, sat); vign = lerp(.35, .25, sat)
        camd = CELEB(u)
        ath = [[52.5 + 8 * math.cos(k / 11 * 6.28 + t * .4), 30 + 4.5 * math.sin(k / 11 * 6.28 + t * .4)] for k in range(11)]
        osa = []; celebrate = 1.0
        overlays.append(lambda im, cam: panel(im, "CAMPEÓN DE LIGA 39-40", [("1º", "ATHLETIC AVIACIÓN", "CAMPEÓN", (250, 210, 30))], u * 1.2 - 0.3, hl=None))
    elif i == 15:
        sign = "CHAMARTÍN"; st['cheer'] = 1.0; sat, grain, vign = 1, .25, .25
        camd = CELEB(1 - u)
        ath = [[52.5 + 8 * math.cos(k / 11 * 6.28 + t * .4), 30 + 4.5 * math.sin(k / 11 * 6.28 + t * .4)] for k in range(11)]
        osa = []; celebrate = 1.0
        overlays.append(lambda im, cam: panel(im, "CAMPEÓN DE LIGA", [("39-40", "  ATHLETIC AVIACIÓN", "CAMPEÓN", (250, 210, 30)),
                                                                   ("40-41", "  ATHLETIC AVIACIÓN", "CAMPEÓN", (250, 210, 30))], u, hl=None))
    elif i == 16:
        sign = "CHAMARTÍN"; sat, grain, vign = 1, .2, .2; st['cheer'] = 0.3
        camd = camlerp(SIDE(40, 24), SIDE(64, 24), u)
        overlays.append(lambda im, cam: name_plate(im, "1947 · NUEVO NOMBRE", "", u, y=560,
                                                    morph=("ATHLETIC AVIACIÓN", "ATLÉTICO DE MADRID", ease(u * 2 - 0.5))))
    elif i == 17:
        sign = "CHAMARTÍN"; sat, grain, vign = 1, .2, .2
        camd = camlerp(SIDE(64, 24), SIDE(36, 26), u)
        overlays.append(lambda im, cam: panel(im, "PRIMERA DIVISIÓN 40-41", [("↑", "REAL OVIEDO", "VUELVE", (120, 230, 120))], u, hl=None))
    else:
        sign = "CHAMARTÍN"; sat, grain, vign = 1, .2, .2
        camd = camlerp(SIDE(36, 26), ((52, -10, 34), (52, 34, 0), 1100), ease(u))
        st['end'] = ease((t - TIMES[-1][0]) / 1.2)
    return i, u, camd, st, sat, grain, vign, sign, ath, osa, ball, celebrate, bug, overlays

LOGO_IMG = None
def render_frame(t, subs=True):
    global LOGO_IMG
    i, u, cam, st, sat, grain, vign, sign, ath, osa, ball, celebrate, bug, overlays = scene(t)
    img = Image.new('RGB', (W, H))
    draw_sky(img, st)
    dr0 = ImageDraw.Draw(img)
    poly(dr0, cam, [(-60, -60, 0), (PL + 60, -60, 0), (PL + 60, PW + 5.2, 0), (-60, PW + 5.2, 0)], (128, 116, 92) if not st.get('war') else (118, 110, 96))
    draw_stands(img, cam, st)
    draw_sign(img, cam, sign)
    if cam.f > 2400:   # profundidad de campo en planos cerrados
        img = img.filter(ImageFilter.GaussianBlur(1.6))
    draw_pitch(img, cam, st)
    draw_goal(img, cam, 0); draw_goal(img, cam, PL)
    if st.get('bench'):
        dr = ImageDraw.Draw(img, 'RGBA')
        poly(dr, cam, [(49, -4.2, 0.5), (57, -4.2, 0.5), (57, -4.8, 0.5), (49, -4.8, 0.5)], (110, 80, 50))
        poly(dr, cam, [(49, -4.8, 0.5), (57, -4.8, 0.5), (57, -4.8, 1.1), (49, -4.8, 1.1)], (90, 64, 40))
        x, y, z = cam.proj(np.array([53, -3.2, 0.0])); _, yh, _ = cam.proj(np.array([53, -3.2, 1.78]))
    if ath is not None or (osa is not None and len(osa)):
        draw_players(img, cam, ath or [], osa or [], t, ball, celebrate=celebrate)
    elif ball is not None:
        draw_ball(img, cam, ball)
    if st.get('bench'):
        draw_player(img, (x, y), y - yh, 'coach', 0, 0, 1)
    if st.get('planes') is not None:
        dr = ImageDraw.Draw(img, 'RGBA'); p = st['planes']
        for k in range(3):
            px = lerp(-300, W + 500, p) - k * 210; py = 330 + k * 120 - p * 60
            biplane(dr, px, py, 70 - k * 8, t)
    img = grade(img, sat, grain, t, vign)
    img = img.convert('RGBA')
    if bug:
        score_bug(img, bug[0], bug[1], bug[2], 1.0, flash=1 if (len(bug) > 3 and bug[3]) else 0)
    for o in overlays: o(img, cam)
    if st.get('end') is not None:
        e = st['end']
        dark = Image.new('RGBA', (W, H), (8, 10, 14, int(170 * e))); img.alpha_composite(dark)
        if LOGO_IMG is None and os.path.exists(LOGO):
            LOGO_IMG = Image.open(LOGO).convert('RGBA').resize((560, 560), Image.LANCZOS)
        if LOGO_IMG is not None and e > 0:
            lg = LOGO_IMG.copy(); lg.putalpha(Image.eval(lg.getchannel('A'), lambda v: int(v * e)))
            img.alpha_composite(lg, (W // 2 - 280, 330))
        dr = ImageDraw.Draw(img)
        if e > 0.3:
            text_stroke(dr, (W / 2, 1030), "¿LA PRÓXIMA HISTORIA?", font('anton', 104), (255, 222, 0), sw=8)
            text_stroke(dr, (W / 2, 1160), "VOTA EN LOS COMENTARIOS ↓", font('anton', 80), (255, 255, 255), sw=7)
    if subs and t < TIMES[-1][0]:
        subtitles(img, t)
    dr = ImageDraw.Draw(img)
    dr.text((W / 2, 96), HANDLE, font=font('anton', 46), fill=(255, 255, 255, 200), anchor='mm', stroke_width=3, stroke_fill=(0, 0, 0))
    return img.convert('RGB')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--preview', type=float, nargs='*')
    ap.add_argument('--frames', type=int, nargs=2)
    ap.add_argument('--out', default=os.path.join(HERE, 'frames'))
    a = ap.parse_args()
    if a.preview is not None:
        os.makedirs(os.path.join(HERE, 'prev'), exist_ok=True)
        for t in a.preview:
            render_frame(t).save(os.path.join(HERE, 'prev', f'p_{t:05.1f}.jpg'), quality=85)
        return
    os.makedirs(a.out, exist_ok=True)
    n = int(DUR * FPS); f0, f1 = a.frames if a.frames else (0, n)
    for k in range(f0, min(f1, n)):
        p = os.path.join(a.out, f'f{k:05d}.jpg')
        if os.path.exists(p): continue
        render_frame(k / FPS).save(p, quality=92)

if __name__ == '__main__':
    main()
