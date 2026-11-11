#!/usr/bin/env python3
"""Gridiron Lore 03 - The Heidi Game (1968). Renderer PIL -> ffmpeg.
Uso: python3 render_gridiron_lore_03.py voz.mp3 times.json out.mp4 [--preview N] [--cover cover.jpg]
times.json: lista de [inicio, fin] por frase (15 frases).
"""
import sys, json, math, random, subprocess, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
FONTDIR = os.environ.get("GL_FONTS", os.path.join(HERE, "fonts"))
FALLBACK = "/mnt/skills/examples/canvas-design/canvas-fonts/BigShoulders-Bold.ttf"

def fpath(name):
    p = os.path.join(FONTDIR, name)
    return p if os.path.exists(p) else FALLBACK

ANTON = fpath("Anton-Regular.ttf")
BEBAS = fpath("BebasNeue-Regular.ttf")
_fc = {}
def F(path, size):
    k = (path, size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(path, size)
    return _fc[k]

YEL = (255, 204, 41)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
NAVY = (14, 20, 34)
GRASS1 = (46, 125, 50)
GRASS2 = (40, 112, 45)
JET_G = (18, 87, 64)
RAI_BLK = (22, 22, 24)
RAI_SIL = (172, 176, 182)

SCRIPT = [
 "Millions of football fans missed the wildest ending of the season. Because of a little girl in the Alps.",
 "November seventeenth, nineteen sixty-eight. The Jets visit the Raiders, the two best teams in the AFL.",
 "Sixty-five seconds left. The Jets kick a field goal. Thirty-two to twenty-nine.",
 "But back east, it's seven o'clock. And at seven, NBC has a movie scheduled. Heidi.",
 "Executives tried to call in and keep the game on. They couldn't get through. Fans had jammed every line.",
 "So the broadcast went to commercial. And never came back.",
 "Here's what nobody on the East Coast saw.",
 "Lamonica throws deep to Charlie Smith. Touchdown. Raiders lead.",
 "On the kickoff, the Jets fumble. Preston Ridlehuber dives into the end zone. Touchdown again.",
 "Two touchdowns in nine seconds. Raiders win, forty-three to thirty-two.",
 "Jets fans? They were watching a Swiss girl and her grandfather.",
 "So many people called NBC that the switchboard blew its fuses.",
 "NBC apologized. Then it put a special phone in the control room, just for moments like this. The Heidi Phone.",
 "And since that night, the game stays on until the very last play.",
 "Tomorrow's story? Vote in the comments.",
]

def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)

def lerp(a, b, t):
    return a + (b - a) * t

def mix(c1, c2, t):
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))

# ---------------------------------------------------------------- texto
def text_outline(d, xy, s, font, fill, stroke=8, anchor="mm", sc=BLACK):
    d.text(xy, s, font=font, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=sc)

def headline(d, y, s, size=120, fill=WHITE, t=1.0):
    if t <= 0: return
    f = F(ANTON, size)
    text_outline(d, (W // 2, y), s, f, fill, stroke=max(4, size // 14))

def watermark(d):
    d.text((W // 2, 150), "@NFLGRIDIRONLORE", font=F(BEBAS, 46), fill=WHITE, anchor="mm",
           stroke_width=3, stroke_fill=BLACK)

# ---------------------------------------------------------------- multitud
_rng = random.Random(7)
def crowd_tex(w, h, palette, cw=7, ch=9, gap=2, seed=1, light=1.0):
    r = random.Random(seed)
    im = Image.new("RGB", (w, h), (30, 30, 36))
    d = ImageDraw.Draw(im)
    y = 0
    row = 0
    while y < h:
        d.rectangle([0, y + ch, w, y + ch + gap], fill=(50, 50, 58))
        x = -r.randint(0, cw)
        while x < w:
            c = r.choice(palette)
            k = light * r.uniform(0.75, 1.1)
            c = tuple(min(255, int(v * k)) for v in c)
            d.rectangle([x, y + 2, x + cw - 2, y + ch], fill=c)
            d.ellipse([x + 1, y - 1, x + cw - 3, y + 4], fill=tuple(min(255, int(v * k)) for v in r.choice(SKIN)))
            x += cw + r.randint(0, 2)
        y += ch + gap
        row += 1
    return im

SKIN = [(224, 172, 135), (198, 140, 100), (141, 85, 56), (90, 56, 38), (236, 190, 160)]
CROWD_PAL = [(30, 30, 32), (180, 182, 190), (200, 60, 50), (240, 240, 235), (60, 80, 140),
             (120, 90, 60), (20, 20, 20), (150, 150, 150), (90, 120, 70), (210, 180, 120)]

# ---------------------------------------------------------------- jugadores
TEAMS = {
    "OAK": dict(helmet=RAI_SIL, jersey=RAI_BLK, num=WHITE, numsh=RAI_SIL, pants=RAI_SIL,
                stripe=RAI_BLK, sock=RAI_BLK, mask=(60, 60, 60)),
    "NYJ": dict(helmet=JET_G, jersey=(245, 245, 245), num=JET_G, numsh=JET_G, pants=(245, 245, 245),
                stripe=JET_G, sock=JET_G, mask=(230, 230, 230)),
}

def rot(p, c, a):
    x, y = p[0] - c[0], p[1] - c[1]
    ca, sa = math.cos(a), math.sin(a)
    return (c[0] + x * ca - y * sa, c[1] + x * sa + y * ca)

def limb(d, a, b, w, col):
    d.line([a, b], fill=col, width=int(w))
    r = w / 2
    for p in (a, b):
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=col)

def player(d, x, y, s, team, num="", face=1, pose="stand", ph=0.0, throw=0.0, label=None):
    """x,y = pies en el suelo. s = escala (altura ~ 200*s). face 1=derecha, -1=izquierda."""
    T = TEAMS[team]
    sk = (120, 80, 55) if team == "OAK" else (205, 160, 125)
    sh = (0, 0, 0, 90)
    d.ellipse([x - 55 * s, y - 10 * s, x + 55 * s, y + 10 * s], fill=(20, 60, 25))
    hip = (x, y - 92 * s)
    if pose == "dive":
        # cuerpo casi horizontal
        ang = -1.25 * face
        hip = (x, y - 40 * s)
    # piernas
    if pose == "run":
        sw = math.sin(ph * 2 * math.pi)
        la, lb = 0.65 * sw, -0.65 * sw
    elif pose == "dive":
        la, lb = 1.2, 1.4
    elif pose == "kick":
        la, lb = -0.2, -1.3 * ease(throw) + 0.4
    else:
        la, lb = 0.12, -0.12
    def leg(a, front):
        a = a * face
        knee = rot((hip[0], hip[1] + 48 * s), hip, -a)
        kb = -0.35 * face if front else 0.1 * face
        foot = rot((knee[0], knee[1] + 46 * s), knee, -a - (abs(a) * 0.6 * face if pose == "run" else 0))
        if pose == "dive":
            knee = (hip[0] - face * 45 * s, hip[1] + 8 * s * (1 if front else -0.3))
            foot = (knee[0] - face * 44 * s, knee[1] + 6 * s)
        limb(d, hip, knee, 30 * s, T["pants"])
        d.line([hip, knee], fill=T["stripe"], width=max(1, int(5 * s)))
        d.ellipse([knee[0] - 15 * s, knee[1] - 15 * s, knee[0] + 15 * s, knee[1] + 15 * s], fill=mix(T["pants"], BLACK, 0.15))
        limb(d, knee, foot, 22 * s, T["sock"])
        d.ellipse([foot[0] - 15 * s + face * 6 * s, foot[1] - 8 * s, foot[0] + 15 * s + face * 6 * s, foot[1] + 7 * s], fill=(15, 15, 15))
    leg(lb, False)
    # torso
    if pose == "dive":
        neck = (hip[0] + face * 70 * s, hip[1] - 12 * s)
    else:
        lean = 0.18 if pose == "run" else 0.0
        neck = (hip[0] + face * 70 * s * math.sin(lean), hip[1] - 78 * s)
    tw = 62 * s
    poly = [(hip[0] - 26 * s, hip[1]), (hip[0] + 26 * s, hip[1]),
            (neck[0] + tw / 2 + 6 * s, neck[1] + 6 * s), (neck[0] - tw / 2 - 6 * s, neck[1] + 6 * s)]
    if pose == "dive":
        poly = [(hip[0], hip[1] - 26 * s), (hip[0], hip[1] + 26 * s), (neck[0], neck[1] + 34 * s), (neck[0], neck[1] - 30 * s)]
    leg(la, True)
    d.polygon(poly, fill=T["jersey"])
    # hombreras
    if pose != "dive":
        d.ellipse([neck[0] - tw / 2 - 12 * s, neck[1] - 6 * s, neck[0] + tw / 2 + 12 * s, neck[1] + 34 * s], fill=T["jersey"])
    else:
        d.ellipse([neck[0] - 26 * s, neck[1] - 34 * s, neck[0] + 14 * s, neck[1] + 40 * s], fill=T["jersey"])
    if num:
        cx = (hip[0] + neck[0]) / 2
        cy = (hip[1] + neck[1]) / 2 + 4 * s
        d.text((cx, cy), num, font=F(ANTON, max(8, int(46 * s))), fill=T["num"], anchor="mm",
               stroke_width=max(1, int(2 * s)), stroke_fill=T["numsh"] if T["numsh"] != T["num"] else BLACK)
    # cabeza / casco
    hc = (neck[0] + face * 4 * s, neck[1] - 24 * s) if pose != "dive" else (neck[0] + face * 26 * s, neck[1] - 2 * s)
    r = 25 * s
    d.ellipse([hc[0] - r, hc[1] - r, hc[0] + r, hc[1] + r], fill=T["helmet"])
    d.chord([hc[0] - r, hc[1] - r, hc[0] + r, hc[1] + r], 200, 340, fill=mix(T["helmet"], WHITE, 0.25))
    # mascara (barras)
    mx = hc[0] + face * r * 0.75
    d.line([(mx, hc[1] - r * 0.1), (mx + face * r * 0.35, hc[1] + r * 0.25), (mx, hc[1] + r * 0.7)], fill=T["mask"], width=max(1, int(4 * s)))
    d.line([(hc[0] + face * r * 0.4, hc[1] + r * 0.3), (mx + face * r * 0.35, hc[1] + r * 0.25)], fill=T["mask"], width=max(1, int(4 * s)))
    # brazos
    sh_back = (neck[0] - face * 26 * s, neck[1] + 12 * s)
    sh_front = (neck[0] + face * 26 * s, neck[1] + 12 * s)
    ball = None
    if pose == "throw":
        # throw 0..1: 0-0.45 armado atras, 0.45-0.7 lanzamiento, >0.7 seguimiento
        if throw < 0.45:
            k = ease(throw / 0.45)
            ang = lerp(0.3, 2.5, k)
        elif throw < 0.7:
            k = ease((throw - 0.45) / 0.25)
            ang = lerp(2.5, -0.6, k)
        else:
            ang = lerp(-0.6, -1.0, ease((throw - 0.7) / 0.3))
        sh_t = sh_back
        el = (sh_t[0] - face * 34 * s * math.sin(ang), sh_t[1] - 34 * s * math.cos(ang) + 10 * s)
        hd = (el[0] - face * 30 * s * math.sin(ang + 0.5), el[1] - 30 * s * math.cos(ang + 0.5))
        limb(d, sh_t, el, 17 * s, T["jersey"]); limb(d, el, hd, 15 * s, T["jersey"])
        d.ellipse([hd[0] - 8 * s, hd[1] - 8 * s, hd[0] + 8 * s, hd[1] + 8 * s], fill=sk)
        if throw < 0.62:
            ball = hd
        # brazo guia
        g = (sh_front[0] + face * 30 * s, sh_front[1] + 6 * s)
        limb(d, sh_front, g, 17 * s, T["jersey"]); limb(d, g, (g[0] + face * 22 * s, g[1] + 16 * s), 15 * s, T["jersey"])
    elif pose == "catch":
        for shp in (sh_back, sh_front):
            el = (shp[0] + face * 18 * s, shp[1] - 30 * s)
            hd = (el[0] + face * 10 * s, el[1] - 28 * s)
            limb(d, shp, el, 17 * s, T["jersey"]); limb(d, el, hd, 15 * s, T["jersey"])
            d.ellipse([hd[0] - 8 * s, hd[1] - 8 * s, hd[0] + 8 * s, hd[1] + 8 * s], fill=sk)
    elif pose == "dive":
        for i, shp in enumerate((sh_back, sh_front)):
            shp = (neck[0], neck[1] + (8 if i else -8) * s)
            hd = (shp[0] + face * 70 * s, shp[1] - 4 * s)
            limb(d, shp, hd, 16 * s, T["jersey"])
            d.ellipse([hd[0] - 8 * s, hd[1] - 8 * s, hd[0] + 8 * s, hd[1] + 8 * s], fill=sk)
    else:
        sw = math.sin(ph * 2 * math.pi) if pose == "run" else 0.15
        for i, shp in enumerate((sh_back, sh_front)):
            a = (sw if i else -sw) * 0.9 * face
            el = rot((shp[0], shp[1] + 34 * s), shp, a)
            hd = rot((el[0], el[1] + 30 * s), el, a - 0.6 * face)
            limb(d, shp, el, 17 * s, T["jersey"]); limb(d, el, hd, 15 * s, T["jersey"])
            d.ellipse([hd[0] - 8 * s, hd[1] - 8 * s, hd[0] + 8 * s, hd[1] + 8 * s], fill=sk)
    if label:
        d.text((hc[0], hc[1] - 50 * s - 20), label, font=F(BEBAS, 40), fill=WHITE, anchor="mm",
               stroke_width=3, stroke_fill=BLACK)
    return ball

def football(d, x, y, s=1.0, a=0.0):
    pts = []
    for i in range(24):
        th = i / 24 * 2 * math.pi
        pts.append(rot((x + 16 * s * math.cos(th), y + 10 * s * math.sin(th)), (x, y), a))
    d.polygon(pts, fill=(120, 62, 30), outline=(70, 35, 15))
    d.line([rot((x - 6 * s, y), (x, y), a), rot((x + 6 * s, y), (x, y), a)], fill=WHITE, width=max(1, int(2 * s)))

# ---------------------------------------------------------------- estadio: camara de end zone
def endzone_bg(sky_t=0.0):
    """Coliseo de Oakland, tarde. Camara detras de la end zone."""
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    top, bot = (250, 170, 110), (120, 150, 200)
    for y in range(0, 560):
        d.line([(0, y), (W, y)], fill=mix(bot, top, y / 560))
    crowd = crowd_tex(W, 1500, CROWD_PAL, seed=3, light=0.95)
    im.paste(crowd, (0, 380))
    # anillo superior / torres de luz
    d.rectangle([0, 360, W, 392], fill=(70, 72, 80))
    for lx in (90, W - 90):
        d.rectangle([lx - 6, 120, lx + 6, 370], fill=(80, 80, 88))
        d.rectangle([lx - 60, 90, lx + 60, 140], fill=(60, 60, 66))
        for i in range(4):
            for j in range(2):
                d.ellipse([lx - 52 + i * 27, 96 + j * 22, lx - 34 + i * 27, 114 + j * 22], fill=(255, 245, 210))
    return im

def persp(X, Z):
    # X en anchos de campo (-0.5..0.5), Z profundidad 1 (cerca) .. 4.6 (lejos)
    K = 1360.0
    y = 560 + K / Z
    x = W / 2 + X * 1500.0 / Z
    return (x, y)

def draw_field_endzone(d, offset=0.0):
    Zn, Zf = 1.0, 4.6
    # muro / pista
    d.polygon([persp(-0.72, Zn), persp(0.72, Zn), persp(0.72, Zf + 0.5), persp(-0.72, Zf + 0.5)], fill=(105, 78, 48))
    d.polygon([persp(-0.62, Zn), persp(0.62, Zn), persp(0.62, Zf + 0.3), persp(-0.62, Zf + 0.3)], fill=(38, 100, 42))
    n = 12
    for i in range(n):
        z0 = lerp(Zn, Zf, i / n); z1 = lerp(Zn, Zf, (i + 1) / n)
        d.polygon([persp(-0.5, z0), persp(0.5, z0), persp(0.5, z1), persp(-0.5, z1)], fill=GRASS1 if i % 2 else GRASS2)
    # end zone lejana
    d.polygon([persp(-0.5, Zf - 0.28), persp(0.5, Zf - 0.28), persp(0.5, Zf), persp(-0.5, Zf)], fill=(30, 30, 32))
    for i in range(0, 11):
        z = lerp(Zn + 0.12, Zf - 0.28, i / 10)
        a, b = persp(-0.5, z), persp(0.5, z)
        d.line([a, b], fill=WHITE, width=max(2, int(6 / z)))
        for hx in (-0.09, 0.09):
            p = persp(hx, z + 0.04)
            d.line([(p[0], p[1] - 2), (p[0], p[1] + 4)], fill=WHITE, width=2)
    for sx in (-0.5, 0.5):
        d.line([persp(sx, Zn), persp(sx, Zf)], fill=WHITE, width=6)
    # porteria (en la linea de gol en 1968), amarilla
    gx = persp(0, Zf - 0.28)
    hw = 0.08 * 1500 / (Zf - 0.28)
    hh = 90
    d.line([(gx[0], gx[1]), (gx[0], gx[1] - 40)], fill=YEL, width=5)
    d.line([(gx[0] - hw, gx[1] - 40), (gx[0] + hw, gx[1] - 40)], fill=YEL, width=5)
    for s_ in (-1, 1):
        d.line([(gx[0] + s_ * hw, gx[1] - 40), (gx[0] + s_ * hw, gx[1] - 40 - hh)], fill=YEL, width=5)

def score_bug(d, a, b, qtr="4TH QTR", clock="1:05", y=250, extra=None, t=1.0, flash=None):
    if t <= 0: return
    x0 = 60
    f = F(BEBAS, 54)
    d.rounded_rectangle([x0, y, W - 60, y + 76], 8, fill=(12, 14, 22))
    d.rectangle([x0 + 10, y + 8, x0 + 290, y + 68], fill=JET_G)
    d.text((x0 + 30, y + 38), "JETS", font=f, fill=WHITE, anchor="lm")
    d.text((x0 + 270, y + 38), str(a), font=f, fill=WHITE, anchor="rm")
    d.rectangle([x0 + 300, y + 8, x0 + 600, y + 68], fill=(40, 40, 44) if flash != "OAK" else YEL)
    d.text((x0 + 320, y + 38), "RAIDERS", font=f, fill=WHITE if flash != "OAK" else BLACK, anchor="lm")
    d.text((x0 + 580, y + 38), str(b), font=f, fill=WHITE if flash != "OAK" else BLACK, anchor="rm")
    d.text((x0 + 700, y + 38), qtr, font=f, fill=WHITE, anchor="mm")
    d.text((x0 + 880, y + 38), clock, font=f, fill=YEL, anchor="mm")
    if extra:
        d.rectangle([x0, y + 80, x0 + 26 + d.textlength(extra, font=F(BEBAS, 44)), y + 130], fill=(190, 30, 30))
        d.text((x0 + 13, y + 105), extra, font=F(BEBAS, 44), fill=WHITE, anchor="lm")

# ---------------------------------------------------------------- camara de banda (lateral)
SIDE_HY = 560
def side_scale(v):  # v: 0 banda lejana .. 1 banda cercana
    return 0.62 + 0.55 * v

def side_y(v):
    return SIDE_HY + 40 + v * 1250

def side_x(X, v, camX, ppy=26.0):
    return W / 2 + (X - camX) * ppy * side_scale(v)

def side_bg():
    im = Image.new("RGB", (W, H), (30, 30, 36))
    crowd = crowd_tex(W, SIDE_HY, CROWD_PAL, seed=11, cw=8, ch=10, light=0.95)
    im.paste(crowd, (0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([0, SIDE_HY - 20, W, SIDE_HY + 40], fill=(105, 78, 48))
    return im

def draw_side_field(d, camX, ppy=26.0):
    """X en yardas: 0 = linea de gol izquierda (Jets defienden derecha?), 100 = gol derecha."""
    v0, v1 = 0.0, 1.0
    yl, yn = side_y(v0), side_y(v1)
    d.rectangle([0, yl, W, H], fill=GRASS1)
    # franjas cada 5 yardas
    for k in range(-10, 23):
        X0, X1 = k * 5, k * 5 + 5
        a, b = side_x(X0, 0, camX, ppy), side_x(X1, 0, camX, ppy)
        c, e = side_x(X1, 1.08, camX, ppy), side_x(X0, 1.08, camX, ppy)
        col = GRASS1 if k % 2 else GRASS2
        if X0 >= 100 or X1 <= 0:
            col = (24, 24, 26)  # end zones negras del Coliseo
        d.polygon([(a, yl), (b, yl), (c, H + 80), (e, H + 80)], fill=col)
    for k in range(0, 21):
        X = k * 5
        a, c = side_x(X, 0, camX, ppy), side_x(X, 1.08, camX, ppy)
        d.line([(a, yl), (c, H + 80)], fill=WHITE, width=5 if k % 2 == 0 else 3)
        if k % 2 == 0 and 0 < X < 100:
            n = X if X <= 50 else 100 - X
            p = side_x(X, 0.78, camX, ppy)
            d.text((p, side_y(0.78)), str(n), font=F(ANTON, 70), fill=(235, 240, 235), anchor="mm")
    # hash marks
    for X in range(0, 101):
        for v in (0.38, 0.62):
            p = side_x(X, v, camX, ppy)
            d.line([(p, side_y(v) - 8), (p, side_y(v) + 8)], fill=WHITE, width=3)
    d.line([(0, yl), (W, yl)], fill=WHITE, width=6)
    # porterias en la linea de gol (H vista de lado: dos postes a distinta profundidad)
    for X in (0, 100):
        for v in (0.44, 0.56):
            p = side_x(X, v, camX, ppy)
            if -200 < p < W + 200:
                sc = side_scale(v)
                base = side_y(v)
                if v == 0.44:
                    d.line([(p, base), (p, base - 170 * sc)], fill=YEL, width=int(9 * sc))
                d.line([(p, base - 170 * sc), (p, base - 560 * sc)], fill=YEL, width=int(7 * sc))
        a, b = side_x(X, 0.44, camX, ppy), side_x(X, 0.56, camX, ppy)
        if -200 < a < W + 200:
            d.line([(a, side_y(0.44) - 170 * side_scale(0.44)), (b, side_y(0.56) - 170 * side_scale(0.56))], fill=YEL, width=8)

# ---------------------------------------------------------------- TV de los 60 / salon
def living_room(d, dim=1.0):
    d.rectangle([0, 0, W, H], fill=mix((40, 30, 24), (92, 70, 52), dim))
    # papel pintado
    for x in range(0, W, 60):
        d.line([(x, 0), (x, 1180)], fill=mix((50, 38, 30), (104, 82, 60), dim), width=18)
    d.rectangle([0, 1180, W, H], fill=mix((40, 28, 20), (80, 56, 36), dim))
    for y in range(1180, H, 44):
        d.line([(0, y), (W, y)], fill=mix((30, 22, 16), (66, 46, 30), dim), width=3)

TV_BOX = (120, 520, 960, 1180)
TV_SCREEN = (190, 580, 890, 1100)
def tv_set(im, screen_img, glow=1.0):
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = TV_BOX
    d.rounded_rectangle([x0, y0, x1, y1 + 120], 30, fill=(96, 60, 32))
    d.rounded_rectangle([x0 + 14, y0 + 14, x1 - 14, y1 + 106], 24, outline=(60, 36, 18), width=6)
    # patas
    for px in (x0 + 80, x1 - 80):
        d.polygon([(px - 14, y1 + 120), (px + 14, y1 + 120), (px + 6, y1 + 230), (px - 6, y1 + 230)], fill=(50, 32, 18))
    # rejilla altavoz y mandos
    for i in range(10):
        d.line([(x0 + 60 + i * 30, y1 + 30), (x0 + 60 + i * 30, y1 + 90)], fill=(60, 36, 18), width=8)
    for k, cx in enumerate((x1 - 200, x1 - 110)):
        d.ellipse([cx - 32, y1 + 28, cx + 32, y1 + 92], fill=(200, 190, 170))
        d.line([(cx, y1 + 60), (cx + 20, y1 + 40 - k * 10)], fill=(60, 50, 40), width=6)
    sx0, sy0, sx1, sy1 = TV_SCREEN
    scr = screen_img.resize((sx1 - sx0, sy1 - sy0))
    mask = Image.new("L", scr.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, scr.size[0], scr.size[1]], 70, fill=255)
    im.paste(scr, (sx0, sy0), mask)
    d.rounded_rectangle([sx0, sy0, sx1, sy1], 70, outline=(30, 26, 22), width=14)

def tvize(img):
    """Aspecto de TV 1968: algo desaturado, lineas de barrido."""
    g = img.convert("L").convert("RGB")
    img = Image.blend(img, g, 0.35)
    d = ImageDraw.Draw(img)
    for y in range(0, img.size[1], 6):
        d.line([(0, y), (img.size[0], y)], fill=(0, 0, 0), width=1)
    return img

def static_img(w, h, seed):
    r = random.Random(seed)
    im = Image.new("L", (w // 4, h // 4))
    im.putdata([r.randint(30, 230) for _ in range((w // 4) * (h // 4))])
    return im.resize((w, h), Image.NEAREST).convert("RGB")

def alps_img(w, h, t=0.0, people=True):
    im = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(im)
    for y in range(h):
        d.line([(0, y), (w, y)], fill=mix((120, 175, 230), (220, 235, 250), y / h))
    def mt(pts, col, snow):
        d.polygon(pts, fill=col)
        pk = min(pts[1:-1], key=lambda p: p[1])
        d.polygon([pk, (pk[0] - w * 0.06, pk[1] + h * 0.12), (pk[0] + w * 0.05, pk[1] + h * 0.11)], fill=snow)
    mt([(0, h * 0.7), (w * 0.22, h * 0.22), (w * 0.48, h * 0.7)], (110, 120, 140), WHITE)
    mt([(w * 0.3, h * 0.72), (w * 0.62, h * 0.12), (w * 1.0, h * 0.72)], (95, 105, 128), WHITE)
    d.polygon([(0, h * 0.62), (w * 0.4, h * 0.55), (w, h * 0.64), (w, h), (0, h)], fill=(90, 160, 70))
    # chalet
    cx, cy = w * 0.72, h * 0.62
    d.rectangle([cx - 60, cy - 40, cx + 60, cy + 30], fill=(130, 80, 40))
    d.polygon([(cx - 80, cy - 40), (cx, cy - 95), (cx + 80, cy - 40)], fill=(90, 50, 25))
    d.rectangle([cx - 14, cy - 5, cx + 14, cy + 30], fill=(70, 40, 20))
    # flores
    r = random.Random(4)
    for _ in range(60):
        fx, fy = r.uniform(0, w), r.uniform(h * 0.7, h)
        d.ellipse([fx - 4, fy - 4, fx + 4, fy + 4], fill=r.choice([(255, 255, 255), (255, 220, 60), (230, 90, 120)]))
    if people:
        # nina (generica) con trenzas y vestido, y abuelo con barba; cabras
        gx = w * 0.32 + 10 * math.sin(t * 3)
        gy = h * 0.86
        d.polygon([(gx - 26, gy), (gx + 26, gy), (gx + 12, gy - 70), (gx - 12, gy - 70)], fill=(200, 40, 50))
        d.rectangle([gx - 14, gy - 100, gx + 14, gy - 70], fill=WHITE)
        d.ellipse([gx - 18, gy - 140, gx + 18, gy - 104], fill=(236, 196, 160))
        d.chord([gx - 20, gy - 144, gx + 20, gy - 110], 180, 360, fill=(220, 170, 60))
        d.line([(gx - 18, gy - 122), (gx - 26, gy - 92)], fill=(220, 170, 60), width=7)
        d.line([(gx + 18, gy - 122), (gx + 26, gy - 92)], fill=(220, 170, 60), width=7)
        ox = w * 0.5; oy = h * 0.88
        d.rectangle([ox - 26, oy - 120, ox + 26, oy], fill=(90, 70, 50))
        d.ellipse([ox - 22, oy - 168, ox + 22, oy - 122], fill=(225, 185, 150))
        d.polygon([(ox - 22, oy - 140), (ox + 22, oy - 140), (ox, oy - 100)], fill=(240, 240, 240))
        d.chord([ox - 24, oy - 176, ox + 24, oy - 140], 180, 360, fill=(70, 60, 50))
        for k, gx2 in enumerate((w * 0.12, w * 0.86)):
            gy2 = h * 0.9
            d.ellipse([gx2 - 40, gy2 - 40, gx2 + 40, gy2 - 6], fill=(245, 245, 240) if k else (160, 120, 80))
            d.ellipse([gx2 + 26, gy2 - 60, gx2 + 52, gy2 - 32], fill=(245, 245, 240) if k else (160, 120, 80))
            for lx in (-28, -10, 10, 28):
                d.line([(gx2 + lx, gy2 - 14), (gx2 + lx, gy2 + 14)], fill=(60, 50, 40), width=6)
    return im

def field_tv_img(w, h, t):
    im = Image.new("RGB", (W, H))
    im.paste(side_bg(), (0, 0))
    d = ImageDraw.Draw(im)
    draw_side_field(d, 60 + t * 2)
    for i in range(5):
        player(d, side_x(55 + i * 3, 0.45 + i * 0.05, 60 + t * 2), side_y(0.45 + i * 0.05), 0.9, "NYJ" if i % 2 else "OAK", "", 1, "run", ph=t + i * 0.2)
    return im.crop((0, 200, W, 200 + int(W * h / w))).resize((w, h))

# ---------------------------------------------------------------- centralita
def switchboard(im, t, chaos=0.0, sparks=0.0):
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, H], fill=(46, 40, 36))
    d.rectangle([0, 1450, W, H], fill=(60, 44, 30))
    x0, y0, x1, y1 = 80, 380, 1000, 1460
    d.rectangle([x0, y0, x1, y1], fill=(70, 48, 30))
    d.rectangle([x0 + 30, y0 + 30, x1 - 30, y0 + 640], fill=(25, 22, 20))
    r = random.Random(int(t * 12))
    cols, rows = 12, 10
    for i in range(cols):
        for j in range(rows):
            cx = x0 + 70 + i * 72
            cy = y0 + 70 + j * 58
            lit = r.random() < (0.15 + 0.8 * chaos)
            d.ellipse([cx - 14, cy - 14, cx + 14, cy + 14], fill=(255, 210, 80) if lit else (70, 60, 40))
            d.ellipse([cx - 7, cy + 18, cx + 7, cy + 32], fill=(10, 10, 10))
    # mesa con clavijas y cables
    d.rectangle([x0 - 20, y0 + 660, x1 + 20, y0 + 760], fill=(110, 76, 44))
    rr = random.Random(5)
    for k in range(14):
        a = (x0 + 70 + rr.randint(0, 11) * 72, y0 + 70 + rr.randint(0, 9) * 58 + 25)
        b = (x0 + 60 + k * 62, y0 + 700)
        mid = ((a[0] + b[0]) / 2, max(a[1], b[1]) + 60)
        d.line([a, mid, b], fill=rr.choice([(200, 40, 40), (30, 30, 30), (220, 200, 60)]), width=6, joint="curve")
    # fusibles arriba
    for k in range(6):
        fx = x0 + 110 + k * 145
        d.rectangle([fx - 30, 250, fx + 30, 340], fill=(200, 200, 205))
        blown = sparks > 0 and k <= int(sparks * 6)
        d.rectangle([fx - 18, 270, fx + 18, 320], fill=(40, 30, 30) if blown else (240, 230, 150))
        if blown:
            rs = random.Random(int(t * 30) + k)
            for _ in range(10):
                a = rs.uniform(0, 2 * math.pi); L = rs.uniform(20, 90)
                d.line([(fx, 295), (fx + L * math.cos(a), 295 + L * math.sin(a))], fill=(255, rs.randint(180, 255), 60), width=4)
    return d

# ---------------------------------------------------------------- reloj / guia TV
def wall_clock(d, cx, cy, R, minutes):
    d.ellipse([cx - R - 18, cy - R - 18, cx + R + 18, cy + R + 18], fill=(60, 40, 24))
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(245, 240, 225))
    for i in range(12):
        a = i / 12 * 2 * math.pi
        p1 = (cx + R * 0.82 * math.sin(a), cy - R * 0.82 * math.cos(a))
        p2 = (cx + R * 0.94 * math.sin(a), cy - R * 0.94 * math.cos(a))
        d.line([p1, p2], fill=BLACK, width=8)
    h = (minutes / 60.0) % 12
    a = h / 12 * 2 * math.pi
    d.line([(cx, cy), (cx + R * 0.5 * math.sin(a), cy - R * 0.5 * math.cos(a))], fill=BLACK, width=16)
    a = (minutes % 60) / 60 * 2 * math.pi
    d.line([(cx, cy), (cx + R * 0.8 * math.sin(a), cy - R * 0.8 * math.cos(a))], fill=BLACK, width=10)
    d.ellipse([cx - 14, cy - 14, cx + 14, cy + 14], fill=(190, 30, 30))

# ---------------------------------------------------------------- subtitulos
def build_words(times, segs=None):
    words = []
    pairs = [((a, b), txt) for row in segs for a, b, txt in row] if segs else [((s_, e_), l) for (s_, e_), l in zip(times, SCRIPT)]
    for (s, e), line in pairs:
        toks = line.split()
        L = sum(len(t) + 2 for t in toks)
        acc = 0
        for tk in toks:
            w0 = s + (e - s) * acc / L
            acc += len(tk) + 2
            words.append((w0, s + (e - s) * acc / L, tk))
    return words

def chunks(words, n=3):
    out, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= n or w[2][-1] in ".?!,":
            out.append(cur); cur = []
    if cur: out.append(cur)
    return out

def draw_subs(d, t, CH, y=1440):
    for ch in CH:
        if ch[0][0] - 0.05 <= t < ch[-1][1] + 0.05:
            f = F(ANTON, 104)
            parts = [w[2].upper() for w in ch]
            widths = [d.textlength(p, font=f) for p in parts]
            sp = 26
            total = sum(widths) + sp * (len(parts) - 1)
            scale = 1.0
            if total > W - 80:
                scale = (W - 80) / total
                f = F(ANTON, int(104 * scale))
                widths = [d.textlength(p, font=f) for p in parts]
                sp = int(26 * scale)
                total = sum(widths) + sp * (len(parts) - 1)
            x = (W - total) / 2
            for (w0, w1, _), p, wd in zip(ch, parts, widths):
                col = YEL if w0 <= t < w1 + 0.02 else WHITE
                d.text((x, y), p, font=f, fill=col, anchor="lm", stroke_width=9, stroke_fill=BLACK)
                x += wd + sp
            return

# ---------------------------------------------------------------- escenas
class Ctx: pass
C = Ctx()

def scene_hook(t, T0, T1, im):
    """Frase 0: TV de los 60 con el partido -> nieve -> HEIDI en los Alpes."""
    d = ImageDraw.Draw(im)
    living_room(d, 0.9)
    lt = t - T0
    dur = T1 - T0
    if lt < dur * 0.45:
        scr = tvize(field_tv_img(700, 520, lt))
        sd = ImageDraw.Draw(scr)
        sd.rectangle([20, 20, 380, 70], fill=(12, 14, 22))
        sd.text((30, 45), "JETS 32  RAIDERS 29", font=F(BEBAS, 40), fill=WHITE, anchor="lm")
    elif lt < dur * 0.55:
        scr = static_img(700, 520, int(t * 30))
    else:
        scr = tvize(alps_img(700, 520, lt, people=True))
        sd = ImageDraw.Draw(scr)
        text_outline(sd, (350, 90), "HEIDI", F(ANTON, 110), (255, 240, 200), stroke=6, sc=(90, 40, 20))
    tv_set(im, scr)
    d = ImageDraw.Draw(im)
    headline(d, 330, "MILLIONS MISSED", 130)
    headline(d, 460, "THE ENDING", 130, YEL)

def scene_stadium_intro(t, T0, T1, im):
    lt = t - T0
    im.paste(endzone_bg(), (0, 0))
    d = ImageDraw.Draw(im)
    draw_field_endzone(d)
    # jugadores pequenos en el campo
    for i in range(11):
        for tm, z in (("OAK", 2.6), ("NYJ", 2.75)):
            X = -0.32 + i * 0.064
            p = persp(X, z)
            player(d, p[0], p[1], 0.33, tm, "", 1 if tm == "OAK" else -1, "stand")
    k = ease(lt / 0.6)
    score_bug(d, 0, 0, "OAKLAND", "NOV 17", t=k)
    d.rectangle([0, 0, W, 0], fill=BLACK)
    headline(d, 520, "JETS  @  RAIDERS", 120)
    headline(d, 640, "AFL'S TWO BEST", 80, YEL)

def side_cam_scene(im, camX, drawers, bug=None, ppy=26.0):
    im.paste(side_bg(), (0, 0))
    d = ImageDraw.Draw(im)
    draw_side_field(d, camX, ppy)
    items = sorted(drawers, key=lambda q: q[0])
    for v, fn in items:
        fn(d)
    if bug:
        score_bug(d, *bug[0], **bug[1])
    return d

def scene_fg(t, T0, T1, im):
    lt = t - T0; dur = T1 - T0
    k = min(1, lt / (dur * 0.55))
    # Jets atacan hacia la izquierda: FG a la porteria X=0 desde la 26 (X=19 balon colocado ~ X=16 snap)
    camX = 22 - 8 * ease(k)
    dr = []
    holdX = 26
    kickT = ease(min(1, max(0, (lt - dur * 0.15) / (dur * 0.2))))
    dr.append((0.5, lambda d: player(d, side_x(holdX + 2.5, 0.5, camX), side_y(0.5), 1.0, "NYJ", "11", -1, "kick", throw=kickT, label="TURNER")))
    dr.append((0.48, lambda d: player(d, side_x(holdX - 0.5, 0.47, camX), side_y(0.47), 0.95, "NYJ", "", -1, "stand")))
    for i in range(6):
        v = 0.3 + i * 0.09
        dr.append((v, (lambda i, v: lambda d: player(d, side_x(holdX - 6 - (i % 2), v, camX), side_y(v), 0.95, "NYJ", "", -1, "stand"))(i, v)))
        dr.append((v + 0.01, (lambda i, v: lambda d: player(d, side_x(holdX - 8.5, v, camX), side_y(v), 0.95, "OAK", "", 1, "stand"))(i, v)))
    d = side_cam_scene(im, camX, dr)
    # balon
    bt = max(0, (lt - dur * 0.3) / (dur * 0.35))
    if bt <= 0:
        football(d, side_x(holdX - 0.3, 0.5, camX), side_y(0.5) - 20, 1.0)
    elif bt < 1:
        X = lerp(holdX - 0.3, -1, bt)
        z = math.sin(bt * math.pi) * 380 + bt * 330
        football(d, side_x(X, 0.5, camX), side_y(0.5) - 20 - z, 1.0 - 0.4 * bt, bt * 9)
    good = lt > dur * 0.62
    score_bug(d, 32 if good else 29, 29, "4TH QTR", "1:05" if good else "1:08",
              extra="FIELD GOAL - GOOD" if good else None)
    if good:
        headline(d, 520, "32 - 29", 150, WHITE)
        headline(d, 650, "65 SECONDS LEFT", 80, YEL)

def scene_clock(t, T0, T1, im):
    lt = t - T0; dur = T1 - T0
    d = ImageDraw.Draw(im)
    living_room(d, 0.85)
    m = 7 * 60 - 3 + min(3, lt * 3 / max(0.1, dur * 0.4))
    wall_clock(d, W // 2, 760, 300, m)
    headline(d, 330, "7:00 PM", 140)
    headline(d, 450, "EASTERN TIME", 80, YEL)
    if lt > dur * 0.5:
        # guia de TV
        k = ease((lt - dur * 0.5) / 0.4)
        y = lerp(H, 1180, k)
        d.rounded_rectangle([140, y, 940, y + 230], 14, fill=(250, 245, 230), outline=(30, 30, 30), width=5)
        d.text((180, y + 60), "7:00", font=F(BEBAS, 80), fill=(190, 30, 30), anchor="lm")
        d.text((360, y + 60), "NBC - CHANNEL 4", font=F(BEBAS, 60), fill=BLACK, anchor="lm")
        d.text((180, y + 160), "\"HEIDI\" - SPECIAL MOVIE", font=F(BEBAS, 66), fill=BLACK, anchor="lm")

def scene_calls(t, T0, T1, im):
    lt = t - T0; dur = T1 - T0
    switchboard(im, t, chaos=min(1, lt / dur * 1.4))
    d = ImageDraw.Draw(im)
    headline(d, 230 - 80, "", 10)
    headline(d, 1600, "", 10)
    d.rounded_rectangle([140, 1640, 940, 1740], 12, fill=(190, 30, 30))
    d.text((W // 2, 1690), "ALL LINES BUSY", font=F(BEBAS, 80), fill=WHITE, anchor="mm")

def scene_commercial(t, T0, T1, im):
    lt = t - T0; dur = T1 - T0
    d = ImageDraw.Draw(im)
    living_room(d, 0.8)
    if lt < dur * 0.55:
        scr = Image.new("RGB", (700, 520), (20, 30, 80))
        sd = ImageDraw.Draw(scr)
        sd.text((350, 220), "WE'LL BE", font=F(ANTON, 90), fill=WHITE, anchor="mm")
        sd.text((350, 330), "RIGHT BACK", font=F(ANTON, 90), fill=YEL, anchor="mm")
        scr = tvize(scr)
    else:
        scr = tvize(alps_img(700, 520, lt, people=True))
        text_outline(ImageDraw.Draw(scr), (350, 90), "HEIDI", F(ANTON, 110), (255, 240, 200), stroke=6, sc=(90, 40, 20))
    tv_set(im, scr)
    d = ImageDraw.Draw(im)
    if lt > dur * 0.55:
        headline(d, 380, "NEVER CAME BACK", 120, YEL)

def scene_reveal(t, T0, T1, im):
    lt = t - T0
    im.paste(endzone_bg(), (0, 0))
    d = ImageDraw.Draw(im)
    draw_field_endzone(d)
    for i in range(11):
        for tm, z in (("OAK", 2.0), ("NYJ", 2.15)):
            p = persp(-0.32 + i * 0.064, z)
            player(d, p[0], p[1], 0.42, tm, "", 1, "stand")
    score_bug(d, 32, 29, "4TH QTR", "0:50")
    k = ease(lt / 0.5)
    d.rectangle([0, 470, W, 470 + int(200 * k)], fill=(190, 30, 30))
    if k > 0.5:
        d.text((W // 2, 535), "WHAT THE EAST COAST", font=F(ANTON, 76), fill=WHITE, anchor="mm")
        d.text((W // 2, 615), "NEVER SAW", font=F(ANTON, 76), fill=YEL, anchor="mm")

def scene_td1(t, T0, T1, im):
    """Lamonica (3) lanza largo a Charlie Smith (23). Raiders atacan hacia X=100."""
    lt = t - T0; dur = T1 - T0
    throwT = min(1, lt / (dur * 0.22))
    qbX = 52
    flight = max(0, min(1, (lt - dur * 0.15) / (dur * 0.33)))
    rec0, rec1 = 74, 97
    recX = lerp(rec0, rec1, ease(min(1, lt / (dur * 0.5))))
    ballX = lerp(qbX, 95, flight)
    camX = qbX + 2 if flight <= 0 else lerp(qbX + 2, 92, ease(flight))
    if lt > dur * 0.5: camX = 92
    dr = []
    ball = []
    def qb(d):
        b = player(d, side_x(qbX, 0.55, camX), side_y(0.55), 1.0, "OAK", "3", 1, "throw", throw=throwT, label="LAMONICA")
        ball.append(b)
    dr.append((0.55, qb))
    caught = flight >= 1
    dr.append((0.45, lambda d: player(d, side_x(recX, 0.45, camX), side_y(0.45), 0.95, "OAK", "23", 1,
                                       "catch" if 0.75 < flight else "run", ph=lt * 2.2, label="C. SMITH")))
    dr.append((0.5, lambda d: player(d, side_x(recX - 3.5, 0.5, camX), side_y(0.5), 0.97, "NYJ", "", 1, "run", ph=lt * 2.2 + 0.3)))
    for i in range(4):
        v = 0.3 + i * 0.12
        dr.append((v, (lambda v, i: lambda d: player(d, side_x(qbX + 5 + i * 0.6, v, camX), side_y(v), 0.95, "NYJ", "", -1, "run", ph=lt * 2 + i))(v, i)))
        dr.append((v + 0.01, (lambda v, i: lambda d: player(d, side_x(qbX + 3.5 + i * 0.5, v, camX), side_y(v), 0.95, "OAK", "", 1, "stand"))(v, i)))
    d = side_cam_scene(im, camX, dr)
    if 0 < flight < 1:
        z = math.sin(flight * math.pi) * 420
        football(d, side_x(ballX, lerp(0.55, 0.45, flight), camX), lerp(side_y(0.55), side_y(0.45), flight) - 150 - z, 1.2, 0.3)
    elif flight <= 0 and ball and ball[0]:
        football(d, ball[0][0], ball[0][1], 1.1, -0.6)
    td = lt > dur * 0.5
    score_bug(d, 32, 36 if td else 29, "4TH QTR", "0:42", extra="TOUCHDOWN RAIDERS" if td else None, flash="OAK" if td else None)
    if td:
        headline(d, 560, "TOUCHDOWN", 150, YEL)

def scene_td2(t, T0, T1, im):
    """Kickoff de los Raiders; Christy (NYJ) suelta el balon; Ridlehuber (37) se tira en la end zone (X=100)."""
    lt = t - T0; dur = T1 - T0
    p1 = min(1, lt / (dur * 0.3))      # balon por el aire
    fumble = lt > dur * 0.3
    dive = max(0, min(1, (lt - dur * 0.5) / (dur * 0.2)))
    camX = lerp(70, 93, ease(p1))
    dr = []
    retX = lerp(100, 94, ease(min(1, lt / (dur * 0.35))))
    dr.append((0.5, lambda d: player(d, side_x(retX, 0.5, camX), side_y(0.5), 1.0, "NYJ", "", -1, "run", ph=lt * 2.5, label="CHRISTY")))
    rX = lerp(88, 99.5, ease(min(1, lt / (dur * 0.68))))
    dr.append((0.56, lambda d: player(d, side_x(rX, 0.56, camX), side_y(0.56), 1.0, "OAK", "37", 1,
                                       "dive" if dive > 0 else "run", ph=lt * 2.5, label="RIDLEHUBER")))
    for i in range(5):
        v = 0.3 + i * 0.11
        dr.append((v, (lambda v, i: lambda d: player(d, side_x(lerp(80, 95, ease(min(1, lt / dur * 1.6))) - i, v, camX), side_y(v), 0.95, "OAK", "", 1, "run", ph=lt * 2.4 + i))(v, i)))
    d = side_cam_scene(im, camX, dr)
    if not fumble:
        z = math.sin(p1 * math.pi) * 380
        football(d, side_x(lerp(65, 96, p1), 0.5, camX), side_y(0.5) - 60 - z, 1.1, p1 * 12)
    else:
        bt = min(1, (lt - dur * 0.3) / (dur * 0.25))
        bx = lerp(95, 98.5, bt)
        bz = abs(math.sin(bt * 3 * math.pi)) * 60 * (1 - bt)
        if dive < 1:
            football(d, side_x(bx, 0.56, camX), side_y(0.56) - 12 - bz, 1.1, bt * 8)
        if bt < 0.6:
            d.text((side_x(95, 0.5, camX), side_y(0.5) - 300), "FUMBLE!", font=F(ANTON, 90), fill=YEL, anchor="mm", stroke_width=7, stroke_fill=BLACK)
    td = lt > dur * 0.72
    score_bug(d, 32, 43 if td else 36, "4TH QTR", "0:33", extra="TOUCHDOWN RAIDERS" if td else None, flash="OAK" if td else None)
    if td:
        headline(d, 560, "TOUCHDOWN AGAIN", 120, YEL)

def scene_nine(t, T0, T1, im):
    lt = t - T0; dur = T1 - T0
    im.paste(endzone_bg(), (0, 0))
    d = ImageDraw.Draw(im)
    draw_field_endzone(d)
    score_bug(d, 32, 43, "FINAL", "0:00", flash="OAK")
    # contador 9 segundos
    k = min(9, int(lt / max(0.1, dur * 0.5) * 9) + 1)
    d.rounded_rectangle([290, 470, 790, 830], 30, fill=(12, 14, 22), outline=YEL, width=8)
    d.text((W // 2, 620), f"0:0{k}" if k < 10 else "0:09", font=F(BEBAS, 220), fill=YEL, anchor="mm")
    d.text((W // 2, 780), "2 TOUCHDOWNS", font=F(BEBAS, 70), fill=WHITE, anchor="mm")
    if lt > dur * 0.55:
        headline(d, 1000, "RAIDERS 43", 140, WHITE)
        headline(d, 1140, "JETS 32", 110, (200, 230, 210))

def scene_fans(t, T0, T1, im):
    lt = t - T0
    d = ImageDraw.Draw(im)
    living_room(d, 0.9)
    scr = tvize(alps_img(700, 520, lt))
    text_outline(ImageDraw.Draw(scr), (350, 90), "HEIDI", F(ANTON, 110), (255, 240, 200), stroke=6, sc=(90, 40, 20))
    tv_set(im, scr)
    d = ImageDraw.Draw(im)
    # sofa y espectadores de espaldas con gorro verde
    d.rounded_rectangle([60, 1500, 1020, 1800], 40, fill=(120, 40, 40))
    d.rounded_rectangle([40, 1440, 1040, 1560], 40, fill=(140, 50, 50))
    for i, x in enumerate((300, 540, 780)):
        bob = 6 * math.sin(lt * 4 + i)
        d.ellipse([x - 70, 1330 + bob, x + 70, 1480 + bob], fill=(40, 30, 24))
        d.rounded_rectangle([x - 110, 1440, x + 110, 1640], 50, fill=JET_G if i != 1 else (245, 245, 245))
        d.chord([x - 74, 1320 + bob, x + 74, 1420 + bob], 180, 360, fill=JET_G)
    headline(d, 330, "JETS FANS?", 130)
    headline(d, 460, "WATCHING HEIDI", 100, YEL)

def scene_fuses(t, T0, T1, im):
    lt = t - T0; dur = T1 - T0
    switchboard(im, t, chaos=1.0, sparks=min(1, lt / (dur * 0.7)))
    d = ImageDraw.Draw(im)
    if lt > dur * 0.5:
        d.rounded_rectangle([140, 1640, 940, 1740], 12, fill=(190, 30, 30))
        d.text((W // 2, 1690), "SWITCHBOARD DOWN", font=F(BEBAS, 80), fill=WHITE, anchor="mm")

def scene_phone(t, T0, T1, im):
    lt = t - T0; dur = T1 - T0
    d = ImageDraw.Draw(im)
    # sala de control: monitores con el partido
    d.rectangle([0, 0, W, H], fill=(28, 30, 36))
    for i in range(3):
        for j in range(2):
            x0 = 60 + i * 330; y0 = 260 + j * 260
            scr = tvize(field_tv_img(300, 220, lt + i)) if (i + j) % 2 == 0 else tvize(alps_img(300, 220, lt))
            im.paste(scr, (x0, y0))
            d.rectangle([x0, y0, x0 + 300, y0 + 220], outline=(10, 10, 10), width=8)
    d.rectangle([0, 820, W, 1000], fill=(70, 72, 80))
    d.rectangle([0, 1000, W, H], fill=(48, 40, 34))
    # telefono rojo
    cx, cy = W // 2, 1260
    ring = math.sin(lt * 40) * 6 if (lt % 1.0) < 0.5 else 0
    d.rounded_rectangle([cx - 230, cy - 60, cx + 230, cy + 170], 40, fill=(190, 25, 30))
    d.ellipse([cx - 110, cy - 20, cx + 110, cy + 150], fill=(150, 18, 22))
    for k in range(10):
        a = k / 10 * 2 * math.pi
        d.ellipse([cx + 75 * math.cos(a) - 14, cy + 65 + 75 * math.sin(a) - 14, cx + 75 * math.cos(a) + 14, cy + 65 + 75 * math.sin(a) + 14], fill=(240, 230, 220))
    hx = cx + ring
    d.rounded_rectangle([hx - 280, cy - 150, hx + 280, cy - 70], 40, fill=(210, 30, 36))
    d.ellipse([hx - 300, cy - 170, hx - 180, cy - 40], fill=(210, 30, 36))
    d.ellipse([hx + 180, cy - 170, hx + 300, cy - 40], fill=(210, 30, 36))
    if lt > dur * 0.6:
        d.rounded_rectangle([200, 1640, 880, 1750], 14, fill=YEL)
        d.text((W // 2, 1697), "THE HEIDI PHONE", font=F(ANTON, 80), fill=BLACK, anchor="mm")
    else:
        headline(d, 1690, "NBC: WE'RE SORRY", 90)

def scene_legacy(t, T0, T1, im):
    lt = t - T0; dur = T1 - T0
    im.paste(endzone_bg(), (0, 0))
    d = ImageDraw.Draw(im)
    draw_field_endzone(d)
    for i in range(11):
        for tm, z in (("OAK", 2.3), ("NYJ", 2.45)):
            p = persp(-0.32 + i * 0.064, z)
            player(d, p[0], p[1], 0.38, tm, "", 1, "stand")
    score_bug(d, 32, 43, "FINAL", "0:00")
    headline(d, 520, "EVERY GAME", 140)
    headline(d, 660, "TO THE LAST PLAY", 100, YEL)
    k = ease(lt / 0.6)
    d.rounded_rectangle([190, 820, 890, 900], 12, fill=(12, 14, 22))
    d.rectangle([200, 830, 200 + int(680 * k), 890], fill=(190, 30, 30))
    d.text((W // 2, 860), "LIVE", font=F(BEBAS, 60), fill=WHITE, anchor="mm")

LOGO = None
def scene_outro(t, T0, T1, im):
    global LOGO
    lt = t - T0
    d = ImageDraw.Draw(im)
    for y in range(H):
        d.line([(0, y), (W, y)], fill=mix((24, 36, 58), (6, 8, 14), y / H))
    if LOGO is None:
        LOGO = Image.open(os.path.join(HERE, "logo.png")).convert("RGBA").resize((480, 480))
        m = Image.new("L", (480, 480), 0); ImageDraw.Draw(m).ellipse([0, 0, 479, 479], fill=255)
        LOGO.putalpha(Image.composite(LOGO.getchannel("A"), m, m))
    k = ease(lt / 0.5)
    sz = int(480 * (0.8 + 0.2 * k))
    lg = LOGO.resize((sz, sz))
    im.paste(lg, (W // 2 - sz // 2, 600 - sz // 2), lg)
    headline(d, 960, "TOMORROW'S STORY?", 120)
    d.rounded_rectangle([200, 1640, 880, 1760], 24, fill=YEL)
    d.text((W // 2, 1700), "VOTE IN THE COMMENTS", font=F(BEBAS, 76), fill=BLACK, anchor="mm")
    by = 1800 + 8 * math.sin(lt * 6)
    d.polygon([(W // 2 - 30, by), (W // 2 + 30, by), (W // 2, by + 36)], fill=YEL)

SCENES = [scene_hook, scene_stadium_intro, scene_fg, scene_clock, scene_calls, scene_commercial,
          scene_reveal, scene_td1, scene_td2, scene_nine, scene_fans, scene_fuses, scene_phone,
          scene_legacy, scene_outro]

# caches de fondos
_bg = {}
_orig_endzone = endzone_bg
def endzone_bg(sky_t=0.0):
    if "ez" not in _bg:
        _bg["ez"] = _orig_endzone()
    return _bg["ez"]
_orig_side = side_bg
def side_bg():
    if "sd" not in _bg:
        _bg["sd"] = _orig_side()
    return _bg["sd"]
_alps = {}
_orig_alps = alps_img
def alps_img(w, h, t=0.0, people=True):
    k = (w, h, people, int(t * 6) % 12)
    if k not in _alps:
        _alps[k] = _orig_alps(w, h, t, people)
    return _alps[k].copy()

def frame(t, times, CH, subs=True):
    im = Image.new("RGB", (W, H), BLACK)
    # escena por frase (los huecos entre frases pertenecen a la frase siguiente)
    idx = len(times) - 1
    for i, (s, e) in enumerate(times):
        nxt = times[i + 1][0] if i + 1 < len(times) else 1e9
        if t < nxt:
            idx = i; break
    T0 = times[idx][0] if idx > 0 else 0.0
    T1 = times[idx + 1][0] if idx + 1 < len(times) else times[idx][1] + 1.5
    SCENES[idx](t, T0, T1, im)
    d = ImageDraw.Draw(im)
    watermark(d)
    if subs and idx < len(SCENES) - 1:
        draw_subs(d, t, CH)
    # transicion: fundido corto a negro entre escenas de distinto lugar
    fade = 0.12
    if idx > 0 and t - T0 < fade:
        a = 1 - (t - T0) / fade
        im = Image.blend(im, Image.new("RGB", (W, H), BLACK), a * 0.6)
    return im

def main():
    args = sys.argv[1:]
    mp3, tj, out = args[0], args[1], args[2]
    times = json.load(open(tj))
    assert len(times) == len(SCRIPT), (len(times), len(SCRIPT))
    sp = tj.replace(".json", "_segs.json")
    segs = json.load(open(sp)) if os.path.exists(sp) else None
    CH = chunks(build_words(times, segs))
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", mp3]).strip())
    total = dur + 0.6
    if "--preview" in args:
        ts = [float(x) for x in args[args.index("--preview") + 1].split(",")]
        for k, t in enumerate(ts):
            frame(t, times, CH).save(out.replace(".mp4", f"_p{k:02d}.jpg"), quality=85)
        return
    if "--cover" in args:
        t = float(args[args.index("--cover") + 1])
        frame(t, times, CH, subs=False).save(out, quality=92)
        return
    n = int(total * FPS)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-i", mp3, "-af", "apad", "-t", f"{total:.2f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                          "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for i in range(n):
        p.stdin.write(frame(i / FPS, times, CH).tobytes())
        if i % 300 == 0:
            print(f"{i}/{n}", flush=True)
    p.stdin.close(); p.wait()

if __name__ == "__main__":
    main()
