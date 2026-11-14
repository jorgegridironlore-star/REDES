"""Personas con sombreado volumetrico real (por pixel) sobre un lienzo numpy: conos-capsula y esferas
con normal aproximada, luz del sol bajo + luz de cielo, borde antialias. Mucho mas realista que las
capsulas planas."""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from engine04 import (SUN, UP, HEAD_R, TEAM, SKIN_T, shade, mix, font, shadow, vapor, clamp)

SUNCOL = np.array([1.06, 1.0, 0.92], np.float32)     # sol calido
SKYCOL = np.array([0.80, 0.88, 1.05], np.float32)    # relleno frio del cielo

class Canvas:
    def __init__(self, img):
        self.a = np.asarray(img, np.float32).copy()
        self.H, self.W = self.a.shape[:2]
    def image(self):
        return Image.fromarray(np.clip(self.a, 0, 255).astype(np.uint8))

def _light(cam):
    L = np.array([np.dot(SUN, cam.r), -np.dot(SUN, cam.u), -np.dot(SUN, cam.fw)], np.float32)
    return L / np.linalg.norm(L)

def _shade(col, nx, ny, nz, L, amb=0.34, spec=0.0):
    dif = np.maximum(0, nx * L[0] + ny * L[1] + nz * L[2])
    skyf = np.clip(-ny * 0.5 + 0.5, 0, 1) * 0.22            # de arriba llega luz de cielo
    rim = (1 - nz) ** 3 * 0.10
    c = np.asarray(col, np.float32)
    out = c[None, None, :] * (amb + (0.78 * dif)[..., None] * SUNCOL + (skyf + rim)[..., None] * SKYCOL)
    if spec:
        # brillo especular (cascos)
        hx, hy, hz = L[0], L[1], L[2] + 1.0
        hn = math.sqrt(hx * hx + hy * hy + hz * hz)
        sp = np.maximum(0, (nx * hx + ny * hy + nz * hz) / hn) ** 24 * spec * 255
        out = out + sp[..., None]
    return out

def cone(C, cam, A3, B3, ra, rb, col, L, spec=0.0, amb=0.34):
    a = cam.p(A3); b = cam.p(B3)
    if a[2] < 0.3 or b[2] < 0.3: return
    Ra = ra * cam.f / a[2]; Rb = rb * cam.f / b[2]
    if max(Ra, Rb) < 0.35: return
    A = np.array(a[:2], np.float32); B = np.array(b[:2], np.float32)
    R = max(Ra, Rb)
    x0 = int(max(0, min(A[0], B[0]) - R - 2)); x1 = int(min(C.W, max(A[0], B[0]) + R + 2))
    y0 = int(max(0, min(A[1], B[1]) - R - 2)); y1 = int(min(C.H, max(A[1], B[1]) + R + 2))
    if x1 <= x0 or y1 <= y0: return
    ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    ys += 0.5; xs += 0.5
    AB = B - A; l2 = float(AB @ AB) + 1e-6
    t = np.clip(((xs - A[0]) * AB[0] + (ys - A[1]) * AB[1]) / l2, 0, 1)
    cx = A[0] + t * AB[0]; cy = A[1] + t * AB[1]
    dx = xs - cx; dy = ys - cy
    d = np.sqrt(dx * dx + dy * dy)
    r = Ra + (Rb - Ra) * t
    alpha = np.clip(r - d + 0.5, 0, 1)
    if not alpha.any(): return
    rr = np.maximum(r, 1e-3)
    nx = dx / rr; ny = dy / rr
    nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1))
    c = _shade(col, nx, ny, nz, L, amb, spec)
    sub = C.a[y0:y1, x0:x1]
    al = alpha[..., None]
    sub[:] = sub * (1 - al) + c * al

def sphere(C, cam, P3, r, col, L, spec=0.0, squash=1.0, amb=0.34):
    p = cam.p(P3)
    if p[2] < 0.3: return
    R = r * cam.f / p[2]
    if R < 0.35: return
    x0 = int(max(0, p[0] - R - 2)); x1 = int(min(C.W, p[0] + R + 2))
    y0 = int(max(0, p[1] - R * squash - 2)); y1 = int(min(C.H, p[1] + R * squash + 2))
    if x1 <= x0 or y1 <= y0: return
    ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    nx = (xs + 0.5 - p[0]) / R; ny = (ys + 0.5 - p[1]) / (R * squash)
    d = np.sqrt(nx * nx + ny * ny)
    alpha = np.clip((1 - d) * R + 0.5, 0, 1)
    if not alpha.any(): return
    nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1))
    c = _shade(col, nx, ny, nz, L, amb, spec)
    sub = C.a[y0:y1, x0:x1]
    al = alpha[..., None]
    sub[:] = sub * (1 - al) + c * al

def text_on(C, cam, P3, txt, size_yd, col, outline=None, L=None, flat=1.0):
    p = cam.p(P3)
    if p[2] < 0.3: return
    sz = size_yd * cam.f / p[2]
    if sz < 4: return
    fnt = font('Anton-Regular.ttf', sz)
    w = int(sz * 1.6 + 6); h = int(sz * 1.3 + 6)
    m = Image.new('L', (w, h), 0); dm = ImageDraw.Draw(m)
    dm.text((w / 2, h / 2), txt, font=fnt, fill=255, anchor='mm')
    mo = None
    if outline is not None:
        mo = Image.new('L', (w, h), 0)
        ImageDraw.Draw(mo).text((w / 2, h / 2), txt, font=fnt, fill=255, anchor='mm', stroke_width=max(1, int(sz * .08)))
    x0 = int(p[0] - w / 2); y0 = int(p[1] - h / 2)
    for mask, c in ((mo, outline), (m, col)):
        if mask is None: continue
        arr = np.asarray(mask, np.float32) / 255
        xa, ya = max(0, x0), max(0, y0); xb, yb = min(C.W, x0 + w), min(C.H, y0 + h)
        if xb <= xa or yb <= ya: continue
        al = arr[ya - y0:yb - y0, xa - x0:xb - x0][..., None]
        sub = C.a[ya:yb, xa:xb]
        cc = np.asarray(c, np.float32) * flat
        sub[:] = sub * (1 - al) + cc * al

# ---------------------------------------------------------------- figura
def player_prims(cam, J, team, num='', skin=0, ball=None):
    """Lista de primitivas (profundidad, funcion) para pintar con el algoritmo del pintor."""
    T = TEAM[team]
    sk = SKIN_T[skin % len(SKIN_T)]
    f, s, td = J['f'], J['s'], J['tdir']
    pr = []
    def add(P, fn, bias=0.0):
        pr.append((cam.depth(P) - bias, fn))
    tocam = -cam.fw
    for side in ('L', 'R'):
        hip, knee, ank, toe = J['hip' + side], J['knee' + side], J['ank' + side], J['toe' + side]
        sh_, el, wr = J['sh' + side], J['el' + side], J['wr' + side]
        if team == 'COACH':
            add((knee + ank) / 2, lambda C, L, a=knee, b=ank: cone(C, cam, a, b, .075, .062, T['pants'], L))
            add((ank + toe) / 2, lambda C, L, a=ank, b=toe: cone(C, cam, a, b, .055, .048, T['shoe'], L, spec=.4))
            add((sh_ + el) / 2, lambda C, L, a=sh_, b=el: cone(C, cam, a, b, .095, .08, T['coat'], L))
            add((el + wr) / 2, lambda C, L, a=el, b=wr: cone(C, cam, a, b, .085, .075, T['coat'], L))
            add(wr, lambda C, L, a=wr + (wr - el) * .2: sphere(C, cam, a, .05, (66, 50, 40), L))
            continue
        # piernas
        add((ank + toe) / 2, lambda C, L, a=ank, b=toe: cone(C, cam, a, b, .058, .046, T['shoe'], L, spec=.35))
        add((knee + ank) / 2, lambda C, L, a=knee, b=ank: cone(C, cam, a, b, .068, .05, T['sock'], L))
        if T.get('sockstripe'):
            for tt, w in ((0.16, .05), (0.3, .03)):
                A = knee + (ank - knee) * tt; B = knee + (ank - knee) * (tt + w / SHIN_)
                add((A + B) / 2, lambda C, L, a=A, b=B: cone(C, cam, a, b, .07, .068, T['sockstripe'], L), .004)
        add((hip + knee) / 2, lambda C, L, a=hip, b=knee: cone(C, cam, a, b, .118, .088, T['pants'], L))
        if T.get('pstripe'):
            # franja lateral del pantalon
            out = s * (0.1 if side == 'L' else -0.1)
            for k, c in enumerate(T['pstripe'][:1]):
                A = hip + out * 1.0 + (knee - hip) * .05; B = knee + out * 0.8
                add((A + B) / 2, lambda C, L, a=A, b=B, c=c: cone(C, cam, a, b, .022, .018, c, L), .06)
        add(knee, lambda C, L, a=knee: sphere(C, cam, a, .082, T['pants'], L), .005)
        # brazos
        jc = T['jersey'] if T['jersey'] != 'stripes' else (232, 232, 230)
        add((sh_ + el) / 2, lambda C, L, a=sh_, b=el: cone(C, cam, a, b, .09, .072, jc, L))
        add((el + wr) / 2, lambda C, L, a=el, b=wr: cone(C, cam, a, b, .072, .056, jc, L))
        if team == 'REF':
            for tt in (0.08, 0.26, 0.44, 0.62, 0.8):
                A = sh_ + (el - sh_) * tt; B = sh_ + (el - sh_) * (tt + 0.07)
                add((A + B) / 2, lambda C, L, a=A, b=B: cone(C, cam, a, b, .092, .089, (28, 28, 30), L), .003)
            for tt in (0.1, 0.3, 0.5, 0.7):
                A = el + (wr - el) * tt; B = el + (wr - el) * (tt + 0.08)
                add((A + B) / 2, lambda C, L, a=A, b=B: cone(C, cam, a, b, .074, .071, (28, 28, 30), L), .003)
        elif T.get('sleeve'):
            for k, c in enumerate(T['sleeve']):
                tt = 0.62 + k * 0.09
                A = sh_ + (el - sh_) * tt; B = sh_ + (el - sh_) * (tt + 0.07)
                add((A + B) / 2, lambda C, L, a=A, b=B, c=c: cone(C, cam, a, b, .086, .084, c, L), .003)
        hand = T.get('gloves') or sk
        add(wr, lambda C, L, a=wr + (wr - el) * .22: sphere(C, cam, a, .052, hand, L))
    pel, neck = J['pelvis'], J['neck']
    if team == 'COACH':
        kneeM = (J['kneeL'] + J['kneeR']) / 2
        add((neck + kneeM) / 2, lambda C, L: cone(C, cam, neck - td * .06, kneeM + td * .02, .2, .25, T['coat'], L))
        add(neck, lambda C, L: cone(C, cam, J['shL'], J['shR'], .1, .1, T['coat'], L), .02)
        add(neck, lambda C, L: sphere(C, cam, neck + td * .02, .085, (110, 34, 34), L), .05)      # bufanda
    else:
        jc = T['jersey'] if T['jersey'] != 'stripes' else (232, 232, 230)
        add(pel, lambda C, L: cone(C, cam, J['hipL'] + td * .02, J['hipR'] + td * .02, .135, .135, T['pants'], L))
        add((pel + neck) / 2, lambda C, L: cone(C, cam, pel + td * .1, neck - td * .14, .15, .2 if team != 'REF' else .17, jc, L))
        if team == 'REF':
            # rayas verticales del jersey en la cara visible del torso
            fwd = tocam - td * np.dot(tocam, td); fwd = fwd / (np.linalg.norm(fwd) + 1e-6)
            side = np.cross(td, fwd)
            for k in range(-5, 6):
                o = side * k * 0.031
                dep = fwd * 0.16 * math.sqrt(max(0, 1 - (k * 0.031 / 0.19) ** 2))
                A = pel + td * .12 + o + dep; B = neck - td * .15 + o * 1.15 + dep * 1.15
                add((A + B) / 2, lambda C, L, a=A, b=B: cone(C, cam, a, b, .0155, .017, (28, 28, 30), L), .2)
        else:
            add(neck, lambda C, L: cone(C, cam, J['shL'] + td * .015, J['shR'] + td * .015, .125, .125, jc, L), .0)
            for sd in ('L', 'R'):
                add(J['sh' + sd], lambda C, L, a=J['sh' + sd]: sphere(C, cam, a + td * .015, .132, jc, L), .01)
        if num and team in ('GB', 'DAL'):
            front = np.dot(f, tocam) > 0
            nrm = f if front else -f
            P = pel + td * 0.36 + nrm * 0.19
            if np.dot(nrm, tocam) > 0.25:
                add(P, lambda C, L, P=P: text_on(C, cam, P, num, 0.21, T['num'], T['numout'], flat=0.95), .3)
    # cabeza
    H = J['head']
    if team == 'REF':
        add(neck, lambda C, L: sphere(C, cam, neck + td * .05, .065, sk, L), -.01)
        add(H, lambda C, L: sphere(C, cam, H, HEAD_R * .86, sk, L))
        add(H, lambda C, L: sphere(C, cam, H - f * .035 + td * .015, HEAD_R * .84, (58, 44, 34), L), .005)
        facing = np.dot(f, tocam)
        if facing > -0.2:
            add(H, lambda C, L: sphere(C, cam, H + f * .1 - td * .005, .03, shade(sk, .95), L), .12)   # nariz
            for sg in (1, -1):
                add(H, lambda C, L, sg=sg: sphere(C, cam, H + f * .088 + s * sg * .042 + td * .022, .022, shade(sk, .8), L), .1)
        for sg in (1, -1):
            add(H + s * sg * .12, lambda C, L, sg=sg: sphere(C, cam, H + s * sg * .112, .024, shade(sk, .9), L), .0)
        add(H, lambda C, L: sphere(C, cam, H + td * .075 - f * .015, HEAD_R * .9, T['cap'], L, squash=.62), .02)
        add(H, lambda C, L: cone(C, cam, H + td * .035 - f * .05 + s * .1, H + td * .035 - f * .05 - s * .1, .03, .03, (70, 52, 40), L), -.03)
        add(H, lambda C, L: cone(C, cam, H + td * .055 + f * .08, H + td * .045 + f * .2, .04, .035, shade(T['cap'], .92), L), .05)
        return pr
    if team == 'COACH':
        add(H, lambda C, L: sphere(C, cam, H, HEAD_R * .82, sk, L))
        if np.dot(f, tocam) > -0.2:
            add(H, lambda C, L: sphere(C, cam, H + f * .1 - td * .01, .028, shade(sk, .95), L), .12)
        add(H, lambda C, L: sphere(C, cam, H + td * .075, HEAD_R * .95, T['furhat'], L, squash=.85), .03)
        return pr
    add(neck, lambda C, L: sphere(C, cam, neck + td * .035, .072, sk, L), -.02)
    add(H, lambda C, L: sphere(C, cam, H, HEAD_R, T['helmet'], L, spec=.55))
    if T.get('hstripe') and np.dot(td, tocam) > -0.6:
        for k, c in enumerate(T['hstripe']):
            o = (k - 1) * 0.026
            pts = [H + td * HEAD_R * math.cos(a) * 1.0 + f * HEAD_R * math.sin(a) * 1.0 + s * o for a in np.linspace(-1.6, 1.3, 6)]
            for A, B in zip(pts[:-1], pts[1:]):
                add((A + B) / 2, lambda C, L, a=A, b=B, c=c: cone(C, cam, a, b, .013, .013, c, L, spec=.3), .03)
    if np.dot(f, tocam) > -0.25:
        fc = H + f * HEAD_R * 0.62 - td * HEAD_R * 0.18
        add(fc, lambda C, L: sphere(C, cam, fc, HEAD_R * .5, shade(sk, .62), L, amb=.25), .04)
        mk = T['mask']
        for dz in (-0.035, 0.035):
            A = fc + s * .085 + td * dz + f * .07; B = fc - s * .085 + td * dz + f * .07
            add(fc, lambda C, L, a=A, b=B: cone(C, cam, a, b, .011, .011, mk, L, spec=.3), .12)
        add(fc, lambda C, L: cone(C, cam, fc + td * .06 + f * .06, fc - td * .075 + f * .075, .011, .011, mk, L), .13)
    for sg in (1, -1):
        E = H + s * sg * HEAD_R * 0.9 - td * .02
        add(E, lambda C, L, E=E: sphere(C, cam, E, .03, shade(T['helmet'], .8), L), .0)
    if ball is not None:
        add(ball, lambda C, L: football3(C, cam, ball, f, L), .2)
    return pr

SHIN_ = 0.48

def football3(C, cam, P, axis, L):
    A = P - axis * 0.12; B = P + axis * 0.12; M = P
    cone(C, cam, A, M, .02, .085, (120, 62, 30), L, spec=.3)
    cone(C, cam, M, B, .085, .02, (120, 62, 30), L, spec=.3)

def draw_people(img, cam, people, breath_t=0.0, shadows=True):
    if shadows:
        sh = Image.new('RGBA', img.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(sh)
        for p in people:
            if p.get('shadow', True) and p['team'] != 'PROP':
                shadow(sd, cam, p['J'], p.get('salpha', 105))
        sh = sh.filter(ImageFilter.GaussianBlur(max(1.5, cam.W / 700)))
        img.paste(sh, (0, 0), sh)
    C = Canvas(img)
    L = None
    from figures import _light
    L = _light(cam)
    figs = []
    for p in people:
        figs.append((cam.depth(p['J']['pelvis']), p))
    for _, p in sorted(figs, key=lambda q: -q[0]):
        if p['team'] == 'PROP':
            prims = p['prims'](cam)
        else:
            prims = player_prims(cam, p['J'], p['team'], p.get('num', ''), p.get('skin', 0), p.get('ball'))
        for _, fn in sorted(prims, key=lambda q: -q[0]):
            fn(C, L)
    out = C.image()
    va = Image.new('RGBA', img.size, (0, 0, 0, 0))
    vd = ImageDraw.Draw(va)
    any_v = False
    for i, p in enumerate(people):
        if p['team'] in ('GB', 'DAL', 'REF', 'COACH') and p.get('breath', True):
            k = ((breath_t * 0.55 + i * 0.37) % 1.0)
            if k < 0.6:
                J = p['J']
                vapor(vd, cam, J['head'] + J['f'] * HEAD_R * (1.3 + k * 1.5) + UP * k * 0.1 - J['tdir'] * .05, k / 0.6)
                any_v = True
    if any_v:
        va = va.filter(ImageFilter.GaussianBlur(max(2, cam.W / 360)))
        out.paste(va, (0, 0), va)
    return out
