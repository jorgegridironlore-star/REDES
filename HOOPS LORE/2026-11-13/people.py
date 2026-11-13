"""Personas mas realistas para Hoops Lore: volumen con luz cenital, cuello, cara generica
(sin parecido a nadie real), manos, zapatillas de lona de cana alta, medias de tubo,
camiseta de tirantes con sisas y dorsal, pantalon corto de los 60. Tambien publico civil."""
import math
import numpy as np
from PIL import ImageDraw
import engine as E

def _mix(c, k):
    return tuple(int(max(0, min(255, v * k))) for v in c)

TEAMS62 = {
    # Warriors (local): blanco con azul real; Knicks (visitante): azul con naranja y blanco
    'PHI': dict(jersey=(238, 238, 232), trim=(24, 64, 160), shorts=(238, 238, 232), strim=(24, 64, 160),
                socks=(244, 244, 240), sockstripe=(24, 64, 160), shoes=(240, 238, 228), num=(24, 64, 160), numtrim=(200, 40, 40)),
    'NYK': dict(jersey=(34, 76, 168), trim=(240, 128, 36), shorts=(34, 76, 168), strim=(240, 128, 36),
                socks=(244, 244, 240), sockstripe=(240, 128, 36), shoes=(36, 34, 34), num=(255, 255, 255), numtrim=(240, 128, 36)),
}
# 1950: Pistons blanco con rojo; Lakers azul con dorado (sin logos)
TEAMS62['FW'] = dict(jersey=(240, 238, 232), trim=(196, 34, 40), shorts=(240, 238, 232), strim=(196, 34, 40),
                     socks=(244, 244, 240), sockstripe=(196, 34, 40), shoes=(36, 34, 34), num=(196, 34, 40), numtrim=(30, 30, 30))
TEAMS62['MIN'] = dict(jersey=(32, 64, 150), trim=(232, 184, 52), shorts=(32, 64, 150), strim=(232, 184, 52),
                      socks=(244, 244, 240), sockstripe=(232, 184, 52), shoes=(34, 32, 32), num=(232, 184, 52), numtrim=(255, 255, 255))
# 1954: Hawks (visitante) blanco con rojo y azul marino (sin logos)
TEAMS62['MIL'] = dict(jersey=(240, 238, 232), trim=(178, 30, 44), shorts=(240, 238, 232), strim=(26, 36, 78),
                      socks=(244, 244, 240), sockstripe=(178, 30, 44), shoes=(36, 34, 34), num=(26, 36, 78), numtrim=(178, 30, 44))
SKINS = {
    'light': (230, 192, 164), 'light2': (220, 178, 146), 'tan': (196, 150, 112),
    'brown': (140, 96, 68), 'dark': (104, 70, 50), 'deep': (82, 54, 40),
}

class Painter:
    def __init__(self, draw, cam, k=1.0, off=(0, 0), dim=1.0):
        self.d = draw; self.cam = cam; self.k = k; self.off = off; self.dim = dim
    def P(self, X):
        u, v, z = self.cam.p(X); return ((u - self.off[0]) * self.k, (v - self.off[1]) * self.k), self.cam.f * self.k / max(z, .1)
    def C(self, c):
        return tuple(int(v * self.dim) for v in c)
    def cap(self, A, r, col):
        self.d.ellipse([A[0] - r, A[1] - r, A[0] + r, A[1] + r], fill=self.C(col))
    def quad(self, A, ra, B, rb, col):
        dx, dy = B[0] - A[0], B[1] - A[1]; L = math.hypot(dx, dy) or 1e-6
        nx, ny = -dy / L, dx / L
        self.d.polygon([(A[0] + nx * ra, A[1] + ny * ra), (B[0] + nx * rb, B[1] + ny * rb),
                        (B[0] - nx * rb, B[1] - ny * rb), (A[0] - nx * ra, A[1] - ny * ra)], fill=self.C(col))
    def limb(self, A, sa, B, sb, wa, wb, col, shade=True, caps=True):
        """segmento con silueta continua y sombra plana en el lado contrario a la luz (abajo-derecha)"""
        ra, rb = wa * sa / 2, wb * sb / 2
        self.quad(A, ra, B, rb, col)
        if caps: self.cap(A, ra, col); self.cap(B, rb, col)
        if shade:
            dx, dy = B[0] - A[0], B[1] - A[1]; L = math.hypot(dx, dy) or 1e-6
            nx, ny = -dy / L, dx / L
            if nx + ny < 0: nx, ny = -nx, -ny          # normal hacia abajo-derecha (sombra)
            A2 = (A[0] + nx * ra * .62, A[1] + ny * ra * .62); B2 = (B[0] + nx * rb * .62, B[1] + ny * rb * .62)
            self.quad(A2, ra * .38, B2, rb * .38, _mix(col, .78))
            A3 = (A[0] - nx * ra * .55, A[1] - ny * ra * .55); B3 = (B[0] - nx * rb * .55, B[1] - ny * rb * .55)
            self.quad(A3, ra * .14, B3, rb * .14, _mix(col, 1.08))

def limb3(pa, A, sa, M, sm, B, sb, wa, wm, wb, col, shade=True):
    """miembro con abultamiento en M (musculo) y sombra continua de A a B (sin escalones)"""
    ra, rm, rb = wa * sa / 2, wm * sm / 2, wb * sb / 2
    pa.quad(A, ra, M, rm, col); pa.quad(M, rm, B, rb, col)
    pa.cap(A, ra, col); pa.cap(M, rm, col); pa.cap(B, rb, col)
    if not shade: return
    dx, dy = B[0] - A[0], B[1] - A[1]; L = math.hypot(dx, dy) or 1e-6
    nx, ny = -dy / L, dx / L
    if nx + ny < 0: nx, ny = -nx, -ny
    def strip(f0, f1, c):
        pts_a = [(P[0] + nx * r * f0, P[1] + ny * r * f0) for P, r in ((A, ra), (M, rm), (B, rb))]
        pts_b = [(P[0] + nx * r * f1, P[1] + ny * r * f1) for P, r in ((A, ra), (M, rm), (B, rb))]
        pa.d.polygon(pts_a + pts_b[::-1], fill=pa.C(c))
    strip(.25, .98, _mix(col, .86))
    strip(.6, .98, _mix(col, .76))
    strip(-.75, -.45, _mix(col, 1.07))

def hull(pts):
    pts = sorted(set((round(p[0], 2), round(p[1], 2)) for p in pts))
    if len(pts) < 3: return pts
    def cr(o, a, b): return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cr(up[-2], up[-1], p) <= 0: up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]

def lerp3(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))

def draw_player62(draw, cam, x, y, face, pose, team, number=None, height=6.5, skin='light', hair=(40, 30, 24),
                  k=1.0, off=(0, 0), dim=1.0, build=1.0, ref=False, hold_ball=False):
    """jugador de 1962. build<1 = mas delgado (Wilt: alto y fibroso)."""
    J = E.skeleton(x, y, face, pose, height)
    pa = Painter(draw, cam, k, off, dim)
    if cam.depth(J['pelvis']) < 1: return J
    S = SKINS.get(skin, skin) if isinstance(skin, str) else skin
    if ref:
        T = dict(jersey=(240, 240, 236), trim=(20, 20, 20), shorts=(30, 30, 34), strim=(30, 30, 34), socks=(30, 30, 30),
                 sockstripe=(30, 30, 30), shoes=(20, 20, 20), num=(20, 20, 20), numtrim=(20, 20, 20))
    else:
        T = TEAMS62[team]
    P = {n: pa.P(v) for n, v in J.items()}
    def pt(n): return P[n][0]
    def sc(n): return P[n][1]
    def seg(a, b, t):
        X = lerp3(J[a], J[b], t); return pa.P(X)
    dl = cam.depth(J['lsh']); dr = cam.depth(J['rsh'])
    far, near = ('l', 'r') if dl > dr else ('r', 'l')
    bw = build
    # ----- sombra en el suelo
    sh = []
    for i in range(18):
        a = 2 * math.pi * i / 18
        sh.append(pa.P((x + 1.0 * math.cos(a) + .25, y + .7 * math.sin(a), .07))[0])
    draw.polygon(sh, fill=pa.C((92, 62, 36)))

    def leg(sd):
        hip, knee, ank, toe = sd + 'hip', sd + 'knee', sd + 'ank', sd + 'toe'
        if ref:
            pa.limb(pt(hip), sc(hip), pt(knee), sc(knee), .62 * bw, .46 * bw, T['shorts'])
            pa.limb(pt(knee), sc(knee), pt(ank), sc(ank), .46 * bw, .36 * bw, T['shorts'])
        else:
            # muslo (piel, se ve bajo el pantalon corto)
            mq, sq = seg(hip, knee, .4)
            limb3(pa, pt(hip), sc(hip), mq, sq, pt(knee), sc(knee), .68 * bw, .6 * bw, .4 * bw, S)
            kc, ks = seg(hip, knee, .96)
            pa.cap(kc, .17 * ks * bw, _mix(S, 1.05))
            # rodilla marcada
            # gemelo con su curva
            m1, s1 = seg(knee, ank, .3)
            limb3(pa, pt(knee), sc(knee), m1, s1, pt(ank), sc(ank), .38 * bw, .46 * bw, .26 * bw, S)
            # medias de tubo hasta media pantorrilla con dos franjas
            a2, s2 = seg(knee, ank, .42)
            pa.limb(a2, s2, pt(ank), sc(ank), .46 * bw, .3 * bw, T['socks'])
            for t0, t1 in ((.46, .5), (.54, .58)):
                b0, z0 = seg(knee, ank, t0); b1, z1 = seg(knee, ank, t1)
                pa.limb(b0, z0, b1, z1, .46 * bw, .44 * bw, T['sockstripe'], shade=False, caps=False)
        # zapatilla de lona de cana alta (puntera y suela blancas)
        an, as_ = pt(ank), sc(ank); tn, ts = pt(toe), sc(toe)
        pa.limb(an, as_, tn, ts, .42, .34, T['shoes'])
        pa.cap(an, .22 * as_, T['shoes'])
        tc = (an[0] + (tn[0] - an[0]) * .8, an[1] + (tn[1] - an[1]) * .8)
        pa.cap(tc, .16 * ts, (236, 232, 222))
        # suela
        dx, dy = tn[0] - an[0], tn[1] - an[1]
        pa.quad((an[0] - dx * .1, an[1] + .12 * as_), .05 * as_, (tn[0] + dx * .08, tn[1] + .1 * ts), .05 * ts, (236, 232, 222))
        pa.cap((tn[0], tn[1]), .13 * ts, (236, 232, 222))

    def arm(sd, sleeve_col=None):
        sh_, el, wr = sd + 'sh', sd + 'el', sd + 'wr'
        c = sleeve_col or S
        mb, sb = seg(sh_, el, .35)
        limb3(pa, pt(sh_), sc(sh_), mb, sb, pt(el), sc(el), .44 * bw, .39 * bw, .28 * bw, c)
        mf, sf = seg(el, wr, .3)
        limb3(pa, pt(el), sc(el), mf, sf, pt(wr), sc(wr), .29 * bw, .31 * bw, .2 * bw, c if ref else S)
        # mano con pulgar
        w, ws = pt(wr), sc(wr)
        ex, ey = w[0] - pt(el)[0], w[1] - pt(el)[1]; L = math.hypot(ex, ey) or 1
        hx, hy = w[0] + ex / L * .22 * ws, w[1] + ey / L * .22 * ws
        draw.ellipse([hx - .17 * ws, hy - .2 * ws, hx + .17 * ws, hy + .2 * ws], fill=pa.C(_mix(S, .92)))
        draw.ellipse([hx - .13 * ws - ey / L * .1 * ws, hy - .1 * ws + ex / L * .1 * ws, hx + .05 * ws - ey / L * .1 * ws, hy + .08 * ws + ex / L * .1 * ws], fill=pa.C(S))

    # ----- orden: pierna lejana, brazo lejano, cuerpo, pierna cercana, brazo cercano, cabeza
    leg(far)
    sleeve = T['jersey'] if ref else None
    arm(far, sleeve)
    # pantalon corto de los 60: cintura alta, pernera hasta un tercio del muslo
    def P3(X): return pa.P(X)[0]
    hl, hr = J['lhip'], J['rhip']
    ol = P3(lerp3(hl, lerp3(hl, hr, -0.35), 1)); orr = P3(lerp3(hr, lerp3(hr, hl, -0.35), 1))
    wl_ = P3(lerp3(lerp3(hl, hr, -0.3), J['lsh'], .1)); wr__ = P3(lerp3(lerp3(hr, hl, -0.3), J['rsh'], .1))
    def leg_open(sd, other):
        hip = J[sd + 'hip']; kn = J[sd + 'knee']
        c = lerp3(hip, kn, .38)
        side = tuple(hip[i] - J[other + 'hip'][i] for i in range(3))
        o = P3(tuple(c[i] + side[i] * .6 for i in range(3))); n_ = P3(tuple(c[i] - side[i] * .35 for i in range(3)))
        return o, n_
    lo, li = leg_open('l', 'r'); ro, ri = leg_open('r', 'l')
    crotch = P3(lerp3(lerp3(hl, hr, .5), lerp3(J['lknee'], J['rknee'], .5), .18))
    fwd0 = (math.cos(face), math.sin(face))
    pc = lerp3(hl, hr, .5)
    def o3(X, d, dz=0.0): return P3((X[0] + fwd0[0] * d, X[1] + fwd0[1] * d, X[2] + dz))
    sh_pts = [wl_, wr__, ol, orr, o3(pc, .38, .35), o3(pc, -.4, .35), o3(pc, .3, -.3), o3(pc, -.42, -.3)]
    if not ref:
        draw.polygon(hull(sh_pts), fill=pa.C(T['shorts']))
        # perneras (cada pierna lleva su tubo de tela)
        for sd, other in (('l', 'r'), ('r', 'l')):
            p1, s1 = seg(sd + 'hip', sd + 'knee', .5)
            pa.limb(pt(sd + 'hip'), sc(sd + 'hip'), p1, s1, .8 * bw, .7 * bw, T['shorts'])
        for sd in ('l', 'r'):
            a_, sa_ = seg(sd + 'hip', sd + 'knee', .05); b_, sb_ = seg(sd + 'hip', sd + 'knee', .48)
            pa.limb(a_, sa_, b_, sb_, .1, .1, T['strim'], shade=False)
    pel, sp = pt('pelvis'), sc('pelvis')
    # torso: hombros -> cintura (forma en V suave)
    nk = pt('neck'); ls, rs = pt('lsh'), pt('rsh')
    wl = seg('lhip', 'lsh', .12)[0]; wr_ = seg('rhip', 'rsh', .12)[0]
    def toward(a, b, t): return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
    armpit_l = toward(ls, wl, .3); armpit_r = toward(rs, wr_, .3)
    # deltoides (piel) por debajo de la camiseta de tirantes
    if not ref:
        for s_, n_ in (('lsh', 'l'), ('rsh', 'r')):
            pa.cap(pt(s_), .24 * sc(s_) * bw, S)
    strap_l = toward(nk, ls, .55); strap_r = toward(nk, rs, .55)
    fwd = (math.cos(face), math.sin(face), 0.0)
    def off3(X, d, dz=0.0): return pa.P((X[0] + fwd[0] * d, X[1] + fwd[1] * d, X[2] + dz))[0]
    chest = lerp3(J['lsh'], J['rsh'], .5); chest = (chest[0], chest[1], chest[2] - .55)
    waist = lerp3(J['lhip'], J['rhip'], .5); waist = (waist[0], waist[1], waist[2] + .45)
    side_l = lerp3(J['lsh'], J['lhip'], .3); side_r = lerp3(J['rsh'], J['rhip'], .3)
    tor_pts = [toward(ls, nk, .15), toward(rs, nk, .15), pa.P(side_l)[0], pa.P(side_r)[0], wl, wr_,
               off3(chest, .6 * bw), off3(chest, -.52 * bw), off3(waist, .5 * bw), off3(waist, -.46 * bw),
               off3(lerp3(J['lsh'], J['lhip'], .5), .4 * bw), off3(lerp3(J['lsh'], J['lhip'], .5), -.38 * bw),
               off3(lerp3(J['rsh'], J['rhip'], .5), .4 * bw), off3(lerp3(J['rsh'], J['rhip'], .5), -.38 * bw),
               off3(J['lsh'], .28 * bw, -.25), off3(J['lsh'], -.3 * bw, -.25), off3(J['rsh'], .28 * bw, -.25), off3(J['rsh'], -.3 * bw, -.25),
               off3(J['neck'], .2, -.15), off3(J['neck'], -.2, -.15)]
    body = hull(tor_pts)
    if ref:
        draw.polygon(body, fill=pa.C(T['jersey']))
        # rayas verticales del arbitro
        n = 7
        for i in range(n):
            if i % 2: continue
            t0, t1 = i / n, (i + 1) / n
            draw.polygon([toward(ls, rs, t0), toward(ls, rs, t1), toward(wl, wr_, t1), toward(wl, wr_, t0)], fill=pa.C((22, 22, 22)))
    else:
        draw.polygon(body, fill=pa.C(T['jersey']))
        # sisas: se ve la piel bajo el hombro
        for s_ in ('lsh', 'rsh'):
            pa.cap(pt(s_), .19 * sc(s_) * bw, S)
        # sombreado lateral del torso (lado lejano a la luz)
        side = (wr_, armpit_r) if (rs[0] - ls[0]) > 0 else (wl, armpit_l)
        cx = (wl[0] + wr_[0]) / 2
        shade_poly = [side[1], side[0], toward(side[0], (cx, side[0][1]), .35), toward(side[1], (cx, side[1][1]), .3)]
        draw.polygon(shade_poly, fill=pa.C(_mix(T['jersey'], .8)))
        # ribete de cuello y sisas
        draw.line([toward(nk, ls, .25), toward((nk[0], nk[1] + .55 * sc('neck')), nk, 0), toward(nk, rs, .25)], fill=pa.C(T['trim']), width=max(1, int(.09 * sc('neck'))))
        for a_, b_, c_ in ((strap_l, armpit_l, ls), (strap_r, armpit_r, rs)):
            mid = toward(toward(a_, b_, .5), c_, -.15)
            draw.line([a_, mid, b_], fill=pa.C(T['trim']), width=max(1, int(.07 * sp)))
        # dorsal
        if number is not None and sp > 7:
            cxn = (ls[0] + rs[0] + wl[0] + wr_[0]) / 4; cyn = (ls[1] + rs[1] + wl[1] + wr_[1]) / 4 - .05 * sp
            wpx = abs(ls[0] - rs[0])
            if wpx > .55 * sp:
                f = E.font('Graduate-Regular.ttf', max(6, int(.8 * sp)))
                draw.text((cxn, cyn), str(number), font=f, fill=pa.C(T['num']), anchor='mm',
                          stroke_width=max(1, int(.05 * sp)), stroke_fill=pa.C(T['numtrim']))
        # cinturilla del pantalon
        draw.line([wl, wr_], fill=pa.C(T['strim']), width=max(1, int(.12 * sp)))
    leg(near)
    if not ref:
        # la pernera de la pierna cercana va por encima del muslo (antes el muslo tapaba el pantalon)
        p1, s1 = seg(near + 'hip', near + 'knee', .5)
        pa.limb(pt(near + 'hip'), sc(near + 'hip'), p1, s1, .8 * bw, .7 * bw, T['shorts'])
        a_, sa_ = seg(near + 'hip', near + 'knee', .05); b_, sb_ = seg(near + 'hip', near + 'knee', .48)
        pa.limb(a_, sa_, b_, sb_, .1, .1, T['strim'], shade=False)
        draw.line([wl, wr_], fill=pa.C(T['strim']), width=max(1, int(.12 * sp)))
    arm(near, sleeve)
    # ----- cuello y cabeza
    h, hs = pt('head'), sc('head')
    r = .39 * hs
    pa.limb(nk, sc('neck'), (h[0], h[1] + r * .6), hs, .42, .36, S)
    # orientacion de la cara respecto a la camara
    fx = math.cos(face); fy = math.sin(face)
    tip = pa.P((J['head'][0] + fx * .5, J['head'][1] + fy * .5, J['head'][2]))[0]
    yaw = max(-1, min(1, (tip[0] - h[0]) / (r * 1.1 + 1e-6)))
    to_cam = (cam.pos[0] - J['head'][0]) * fx + (cam.pos[1] - J['head'][1]) * fy
    facing = to_cam > 0
    # orejas
    for sx in (-1, 1):
        if facing or True:
            ex_ = h[0] + sx * r * .9 - yaw * r * .25
            draw.ellipse([ex_ - r * .15, h[1] - r * .15, ex_ + r * .15, h[1] + r * .3], fill=pa.C(_mix(S, .85)))
    # craneo y mandibula
    draw.ellipse([h[0] - r * .86, h[1] - r * 1.08, h[0] + r * .86, h[1] + r * .9], fill=pa.C(_mix(S, .8)))
    draw.ellipse([h[0] - r * .8 + yaw * r * .08, h[1] - r * 1.04, h[0] + r * .74 + yaw * r * .08, h[1] + r * .82], fill=pa.C(S))
    jaw = [(h[0] - r * .7, h[1] + r * .1), (h[0] + r * .7, h[1] + r * .1), (h[0] + r * .3 + yaw * r * .2, h[1] + r * 1.0), (h[0] - r * .3 + yaw * r * .2, h[1] + r * 1.0)]
    draw.polygon(jaw, fill=pa.C(S))
    # pelo corto de los 60
    draw.chord([h[0] - r * .92, h[1] - r * 1.22, h[0] + r * .92, h[1] + r * .1], 180, 360, fill=pa.C(hair))
    draw.chord([h[0] - r * .8, h[1] - r * 1.3, h[0] + r * .7, h[1] - r * .5], 180, 360, fill=pa.C(_mix(hair, 1.15)))
    if not facing:
        draw.ellipse([h[0] - r * .86, h[1] - r * 1.1, h[0] + r * .86, h[1] + r * .5], fill=pa.C(hair))
    elif r > 5:
        # rasgos genericos (no corresponden a nadie real)
        cx = h[0] + yaw * r * .35
        ink = _mix(S, .45)
        for sx in (-1, 1):
            exx = cx + sx * r * .32 * (1 - abs(yaw) * .4)
            draw.line([(exx - r * .16, h[1] - r * .28), (exx + r * .16, h[1] - r * .3)], fill=pa.C(_mix(hair, 1.0)), width=max(1, int(r * .09)))
            draw.ellipse([exx - r * .09, h[1] - r * .16, exx + r * .09, h[1] - r * .04], fill=pa.C((40, 30, 26)))
        draw.polygon([(cx, h[1] - r * .1), (cx + r * .1 + yaw * r * .12, h[1] + r * .28), (cx - r * .08, h[1] + r * .3)], fill=pa.C(_mix(S, .78)))
        draw.line([(cx - r * .2, h[1] + r * .55), (cx + r * .2, h[1] + r * .55)], fill=pa.C(ink), width=max(1, int(r * .07)))
    return J

def draw_fan62(draw, cam, x, y, face, pose, coat=(70, 60, 52), trousers=(50, 48, 52), hat=None, skin='light',
               hair=(50, 38, 28), k=1.0, off=(0, 0), dim=1.0, height=5.9, shirt=(230, 228, 220), tie=(120, 30, 30)):
    """aficionado de 1962: americana o abrigo, pantalon, camisa y corbata, sombrero opcional"""
    J = E.skeleton(x, y, face, pose, height)
    pa = Painter(draw, cam, k, off, dim)
    if cam.depth(J['pelvis']) < 1: return J
    S = SKINS.get(skin, skin) if isinstance(skin, str) else skin
    P = {n: pa.P(v) for n, v in J.items()}
    def pt(n): return P[n][0]
    def sc(n): return P[n][1]
    dl = cam.depth(J['lsh']); dr = cam.depth(J['rsh'])
    far, near = ('l', 'r') if dl > dr else ('r', 'l')
    def leg(sd):
        pa.limb(pt(sd + 'hip'), sc(sd + 'hip'), pt(sd + 'knee'), sc(sd + 'knee'), .6, .46, trousers)
        pa.limb(pt(sd + 'knee'), sc(sd + 'knee'), pt(sd + 'ank'), sc(sd + 'ank'), .46, .38, trousers)
        pa.limb(pt(sd + 'ank'), sc(sd + 'ank'), pt(sd + 'toe'), sc(sd + 'toe'), .34, .3, (28, 22, 20))
    def arm(sd):
        pa.limb(pt(sd + 'sh'), sc(sd + 'sh'), pt(sd + 'el'), sc(sd + 'el'), .44, .36, coat)
        pa.limb(pt(sd + 'el'), sc(sd + 'el'), pt(sd + 'wr'), sc(sd + 'wr'), .36, .3, coat)
        w, ws = pt(sd + 'wr'), sc(sd + 'wr'); pa.cap(w, .17 * ws, S)
    leg(far); arm(far)
    ls, rs = pt('lsh'), pt('rsh')
    lk = pa.P(lerp3(J['lhip'], J['lknee'], .2))[0]; rk = pa.P(lerp3(J['rhip'], J['rknee'], .2))[0]
    leg(near)
    draw.polygon([ls, rs, rk, lk], fill=pa.C(coat))
    nk = pt('neck'); sn = sc('neck')
    # camisa y corbata en el pecho
    draw.polygon([(nk[0] - .22 * sn, nk[1]), (nk[0] + .22 * sn, nk[1]), (nk[0], nk[1] + .9 * sn)], fill=pa.C(shirt))
    draw.polygon([(nk[0] - .06 * sn, nk[1] + .1 * sn), (nk[0] + .06 * sn, nk[1] + .1 * sn), (nk[0], nk[1] + .8 * sn)], fill=pa.C(tie))
    arm(near)
    h, hs = pt('head'), sc('head'); r = .37 * hs
    pa.limb(nk, sn, (h[0], h[1] + r * .5), hs, .3, .28, S)
    draw.ellipse([h[0] - r * .85, h[1] - r, h[0] + r * .85, h[1] + r * .95], fill=pa.C(S))
    if hat:
        draw.ellipse([h[0] - r * 1.5, h[1] - r * .7, h[0] + r * 1.5, h[1] - r * .2], fill=pa.C(hat))
        draw.rounded_rectangle([h[0] - r * .85, h[1] - r * 1.45, h[0] + r * .85, h[1] - r * .4], radius=max(1, r * .3), fill=pa.C(hat))
    else:
        draw.chord([h[0] - r * .88, h[1] - r * 1.05, h[0] + r * .88, h[1] + r * .2], 180, 360, fill=pa.C(hair))
    return J
