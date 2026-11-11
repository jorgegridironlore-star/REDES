#!/usr/bin/env python3
"""Gridiron Lore 04 - The Ice Bowl (1967). Todo en Lambeau Field helado, camaras de TV.
Uso: python3 render_gridiron_lore_04.py voz.mp3 out.mp4 [--preview t1,t2,...] [--cover t] [--range a b]"""
import sys, json, math, random, subprocess, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from engine04 import (Cam, render_world, goalpost, pose_joints, run_pose, stance_pose, blend, UP, HEAD_R, SUN,
                      ease, lerp, clamp, mix, shade, font)
import figures as FG
import base03 as B

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
SS = 1.5
SW, SH = int(W * SS), int(H * SS)
YEL = (255, 204, 41); WHITE = (255, 255, 255); BLACK = (0, 0, 0)
GBG = (24, 74, 46); GBY = (222, 170, 40); DALB = (24, 50, 120)

SCRIPT = [l.strip() for l in open(os.path.join(HERE, 'guion.txt')) if l.strip()]
TIMES = json.load(open(os.path.join(HERE, 'times.json')))
SEGS = json.load(open(os.path.join(HERE, 'times_segs.json')))
CH = B.chunks(B.build_words(TIMES, SEGS))

def AF(sz): return B.F(B.ANTON, int(sz))
def BF(sz): return B.F(B.BEBAS, int(sz))

def finish(img):
    """Escala a 1080x1920 con antialias, viñeta suave y grano fino de emision."""
    im = img.resize((W, H), Image.LANCZOS)
    return im

def cam(pos, look, f, roll=0.0):
    return Cam(pos, look, f * SS, SW, SH, roll)

# ---------------------------------------------------------------- graficos de TV
def score_bug(d, gb, dal, qtr='4TH QTR', extra=None, flash=None, y=232, title=None):
    x0 = 60
    f = BF(54)
    d.rounded_rectangle([x0, y, W - 60, y + 76], 8, fill=(12, 14, 22))
    d.rectangle([x0 + 10, y + 8, x0 + 330, y + 68], fill=DALB if flash != 'DAL' else YEL)
    d.text((x0 + 28, y + 38), 'COWBOYS', font=f, fill=WHITE if flash != 'DAL' else BLACK, anchor='lm')
    d.text((x0 + 312, y + 38), str(dal), font=f, fill=WHITE if flash != 'DAL' else BLACK, anchor='rm')
    d.rectangle([x0 + 340, y + 8, x0 + 660, y + 68], fill=GBG if flash != 'GB' else YEL)
    d.text((x0 + 358, y + 38), 'PACKERS', font=f, fill=WHITE if flash != 'GB' else BLACK, anchor='lm')
    d.text((x0 + 642, y + 38), str(gb), font=f, fill=WHITE if flash != 'GB' else BLACK, anchor='rm')
    d.text((x0 + 810, y + 38), qtr, font=f, fill=YEL, anchor='mm')
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
    wbig = d.textlength(big, font=AF(76)) + 70
    x0 = 60; x1 = x0 + int(wbig * k)
    d.rectangle([x0, y, x1, y + 104], fill=col)
    d.rectangle([x0, y, x0 + 12, y + 104], fill=acc)
    if k > 0.9:
        d.text((x0 + 40, y + 52), big, font=AF(76), fill=WHITE, anchor='lm')
    if small and k > 0.9:
        ws = d.textlength(small, font=BF(48)) + 50
        d.rectangle([x0, y + 108, x0 + ws, y + 166], fill=acc)
        d.text((x0 + 25, y + 137), small, font=BF(48), fill=BLACK, anchor='lm')

def thermo(d, cx, cy, value_txt, sub, k=1.0, level=0.15):
    """Grafico de TV de temperatura."""
    if k <= 0: return
    k = ease(k)
    w, h = 700, 300
    x0 = cx - w // 2; y0 = cy - h // 2 + int((1 - k) * 60)
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], 26, fill=(10, 16, 30))
    d.rounded_rectangle([x0, y0, x0 + w, y0 + 56], 26, fill=(40, 110, 190))
    d.rectangle([x0, y0 + 30, x0 + w, y0 + 56], fill=(40, 110, 190))
    d.text((cx, y0 + 30), sub, font=BF(44), fill=WHITE, anchor='mm')
    # termometro
    tx = x0 + 90
    d.rounded_rectangle([tx - 18, y0 + 80, tx + 18, y0 + 250], 18, fill=(230, 236, 244))
    d.ellipse([tx - 32, y0 + 220, tx + 32, y0 + 284], fill=(230, 236, 244))
    d.ellipse([tx - 24, y0 + 228, tx + 24, y0 + 276], fill=(60, 150, 230))
    lv = y0 + 250 - int(160 * level * k)
    d.rectangle([tx - 9, lv, tx + 9, y0 + 252], fill=(60, 150, 230))
    for i in range(6):
        yy = y0 + 95 + i * 27
        d.line([tx + 22, yy, tx + 36, yy], fill=(150, 160, 180), width=3)
    d.text((x0 + w // 2 + 50, y0 + 175), value_txt, font=AF(150), fill=WHITE, anchor='mm')

def snow_streaks(img, t, density=1.0, alpha=110):
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    r = random.Random(7)
    n = int(260 * density)
    for i in range(n):
        y = r.uniform(0, img.size[1]); sp = r.uniform(900, 1700); L = r.uniform(30, 90)
        x = (r.uniform(0, img.size[0] + 400) + t * sp) % (img.size[0] + 400) - 200
        y2 = y + (t * 60 + i * 13) % 80
        w = r.choice((2, 3, 4))
        d.line([x, y2, x + L, y2 + L * 0.12], fill=(255, 255, 255, int(alpha * r.uniform(.4, 1))), width=w)
    lay = lay.filter(ImageFilter.GaussianBlur(1.2))
    img.paste(lay, (0, 0), lay)

def sparkle(img, t, n=160):
    """Cristales de hielo flotando (polvo de diamante) al sol."""
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    r = random.Random(3)
    for i in range(n):
        x = (r.uniform(0, img.size[0]) + t * r.uniform(10, 40)) % img.size[0]
        y = (r.uniform(0, img.size[1]) + t * r.uniform(15, 50)) % img.size[1]
        a = int(160 * (0.5 + 0.5 * math.sin(t * 6 + i)))
        s = r.uniform(1.5, 3.5)
        d.ellipse([x - s, y - s, x + s, y + s], fill=(255, 255, 255, a))
    img.paste(lay, (0, 0), lay)

def frost_vignette(img, k=0.35):
    """Escarcha en las esquinas del objetivo (camara a -13 F)."""
    w, h = img.size
    m = Image.new('L', (w, h), 0)
    d = ImageDraw.Draw(m)
    r = random.Random(5)
    for i in range(900):
        cx = r.choice((0, w)) + r.gauss(0, w * 0.08) * (1 if r.random() < .5 else -1)
        cy = r.uniform(0, h)
        if r.random() < 0.5:
            cx = r.uniform(0, w); cy = r.choice((0, h)) + r.gauss(0, h * 0.05)
        s = r.uniform(4, 22)
        d.ellipse([cx - s, cy - s, cx + s, cy + s], fill=int(r.uniform(60, 200)))
    m = m.filter(ImageFilter.GaussianBlur(10))
    m = m.point(lambda v: int(v * k))
    white = Image.new('RGB', (w, h), (236, 244, 252))
    img.paste(white, (0, 0), m)

# ---------------------------------------------------------------- escenas 3D
def team_line(xlos, gb_dir=1, gb_nums=None, dal_nums=None, spacing=1.15, offset=0.0, poses=('3pt', '3pt')):
    """Linea de scrimmage: 5 linieros + extras por equipo. gb_dir: +1 si los Packers atacan hacia x+."""
    P = []
    gbn = gb_nums or ['76', '64', '57', '63', '75', '81', '86']
    dln = dal_nums or ['74', '75', '54', '66', '88', '55', '40']
    for i, yy in enumerate([-2.3, -1.15, 0, 1.15, 2.3]):
        P.append(dict(J=stance_pose((xlos - gb_dir * 0.9, yy + offset), 0 if gb_dir > 0 else math.pi, poses[0]), team='GB', num=gbn[i], skin=i))
        P.append(dict(J=stance_pose((xlos + gb_dir * 0.9, yy * 1.05 + offset + 0.3), math.pi if gb_dir > 0 else 0, poses[1]), team='DAL', num=dln[i], skin=i + 1))
    return P

def whistle_macro(t, lt, dur):
    """Primerisimo plano: silbato metalico clasico cubierto de escarcha, colgando del cordon,
    con el estadio desenfocado detras y vaho."""
    c = cam((44, -18, 2.0), (52, 6, 4.5), 600)
    bg = render_world(c).filter(ImageFilter.GaussianBlur(24 * SS / 1.5))
    base = np.asarray(bg, np.float32).copy()
    C = FG.Canvas(bg)
    wc = Cam((0, -1.0, 0), (0, 0, 0), 1050 * SS, SW, SH)
    L = FG._light(wc)
    sw = 0.03 * math.sin(lt * 1.6)
    cx, cz = 0.12 + sw * .3, -0.02 + sw
    metal = (188, 192, 200)
    # cordon
    d0 = ImageDraw.Draw(bg)
    # mouthpiece (tubo plano hacia la izquierda)
    FG.cone(C, wc, (cx - .1, 0, cz + .05), (cx - .52, 0, cz + .085), .07, .062, metal, L, spec=1.0)
    FG.cone(C, wc, (cx - .52, -.01, cz + .085), (cx - .55, -.01, cz + .088), .066, .066, shade(metal, .6), L)
    # barril redondo
    FG.cone(C, wc, (cx, -.09, cz), (cx, .09, cz), .2, .2, metal, L, spec=1.2)
    FG.sphere(C, wc, (cx, -.1, cz), .19, shade(metal, 1.02), L, spec=1.4)
    # ranura superior (oscura)
    FG.cone(C, wc, (cx - .14, -.05, cz + .17), (cx - .02, -.05, cz + .2), .025, .02, (40, 42, 46), L, amb=.6)
    img = C.image()
    d = ImageDraw.Draw(img)
    pr = wc.p((cx + .2, 0, cz + .02)); R = wc.f * .065 / pr[2]
    d.ellipse([pr[0] - R * .4, pr[1] - R, pr[0] + R * 1.6, pr[1] + R], outline=(150, 154, 162), width=int(R * .38))
    d.line([pr[0] + R * 1.5, pr[1] - R * .2, pr[0] + SW * 0.5, -50], fill=(26, 26, 28), width=int(R * .35))
    # escarcha solo sobre el metal y sobre todo en la parte de arriba
    arr = np.asarray(img, np.float32)
    m = (np.abs(arr - base).sum(2) > 18).astype(np.float32)
    m = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(5)), np.float32) / 255
    grow = clamp(lt / 1.2) * 0.7 + 0.3
    rng = np.random.default_rng(3)
    nz = rng.random(m.shape).astype(np.float32)
    ys = np.linspace(1, 0, m.shape[0], dtype=np.float32)[:, None]
    yy = np.where(m.any(1))[0]
    if len(yy):
        top, bot = yy.min(), yy.max()
        rel = np.clip((np.arange(m.shape[0]) - top) / max(1, bot - top), 0, 1)[:, None]
        tw = 1.0 - rel * 0.75
    else:
        tw = 1.0
    specks = (nz > 1 - 0.09 * grow).astype(np.float32)
    specks = np.asarray(Image.fromarray((specks * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3)), np.float32) / 255
    haze = np.asarray(Image.fromarray((nz * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(5)), np.float32) / 255
    fr = np.clip(m * tw * (specks * 0.9 + haze * 0.55 * grow), 0, 1)[..., None]
    arr = arr * (1 - fr) + np.array([246, 250, 255], np.float32) * fr
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    # vaho delante
    va = Image.new('RGBA', img.size, (0, 0, 0, 0)); vd = ImageDraw.Draw(va)
    k = (lt * 0.6) % 1.0
    for jj in range(5):
        x = SW * (0.15 + 0.12 * jj + 0.25 * k); y = SH * (0.66 - 0.08 * k - 0.02 * jj); rr = SW * (0.09 + 0.06 * k)
        vd.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(255, 255, 255, int(80 * (1 - k))))
    va = va.filter(ImageFilter.GaussianBlur(40))
    img.paste(va, (0, 0), va)
    return img

def ImageChopsMul(a, b):
    from PIL import ImageChops
    return ImageChops.multiply(a, b)

def ref_shot(t, lt, dur, mode):
    """Arbitro en plano medio-americano. mode: 'whistle', 'pull', 'stop', 'stand'."""
    push = ease(lt / max(dur, 0.1)) * 0.6
    c = cam((25.2 + push, -8.4 + push * 0.6, 1.65), (28.6, -4.6, 1.25), 1650)
    img = render_world(c)
    yaw = math.radians(28)
    if mode == 'whistle':
        k = ease(lt / 0.8)
        arms = ((lerp(0.05, 1.05, k), lerp(0.25, 2.65, k), lerp(0.12, 0.42, k)), (0.05, 0.25, 0.12))
    elif mode == 'pull':
        k = ease(lt / 0.6)
        arms = ((lerp(1.05, 0.9, k), lerp(2.65, 2.0, k), 0.42), (lerp(0.05, 1.2, k), lerp(0.25, 2.55, k), lerp(.12, .55, k)))
    elif mode == 'stop':
        k = ease(lt / 0.5)
        wave = 0.15 * math.sin(lt * 9)
        arms = ((lerp(0.1, 2.75, k) + wave, 0.25, 0.5), (lerp(0.1, 2.75, k) - wave, 0.25, 0.5))
    else:
        arms = ((0.05, 0.25, 0.12), (0.05, 0.25, 0.12))
    J = pose_joints((28.6, -4.6), yaw, legs=((0.06, 0.08), (-0.08, 0.1)), arms=arms, head_pitch=-0.05)
    people = [dict(J=J, team='REF', skin=0)]
    # jugadores al fondo
    for i in range(5):
        people.append(dict(J=stance_pose((37 + i * 0.4, 2 + i * 1.6), math.pi, 'stand'), team='DAL', num=str(70 + i), skin=i))
        people.append(dict(J=stance_pose((35.5, 1.5 + i * 1.7), 0, 'hands_hips'), team='GB', num=str(60 + i), skin=i + 2))
    img = FG.draw_people(img, c, people, t)
    # silbato en la boca
    d = ImageDraw.Draw(img)
    if (mode == 'whistle' or (mode == 'pull' and lt < 0.25)) and np.dot(J['f'], -c.fw) > 0:
        P = J['head'] + J['f'] * HEAD_R * 0.95 - J['tdir'] * 0.06
        p = c.p(P)
        if p[2] > 0.3:
            R = c.f * 0.03 / p[2]
            d.ellipse([p[0] - R * 1.4, p[1] - R, p[0] + R * 1.4, p[1] + R], fill=(214, 220, 228), outline=(120, 124, 130), width=2)
            d.ellipse([p[0] - R * .7, p[1] - R * .5, p[0] + R * .1, p[1] + R * .1], fill=(250, 252, 255))
    # cordon del silbato
    nk = c.p(J['neck'] + J['f'] * 0.1); ch = c.p(J['pelvis'] + J['tdir'] * 0.35 + J['f'] * 0.17)
    return img, c

def wide_ez(t, lt, k_desc=0.0, cheer=0.0, players='kickoff', z0=26, z1=14):
    z = lerp(z0, z1, ease(k_desc))
    c = cam((-18 + 4 * k_desc, -5 + 5 * k_desc, z), (38, 0, -6), 1150)
    img = render_world(c, cheer=cheer)
    d = ImageDraw.Draw(img)
    goalpost(d, c, 0); goalpost(d, c, 100)
    people = []
    if players == 'kickoff':
        for i in range(11):
            people.append(dict(J=stance_pose((33.5, -21 + i * 4.2), 0, 'ready'), team='GB', num=str(20 + i * 3), skin=i))
            people.append(dict(J=stance_pose((52 + (i % 3) * 6, -18 + i * 3.6), math.pi, 'ready'), team='DAL', num=str(30 + i * 4), skin=i + 1))
        people.append(dict(J=stance_pose((30, 0), 0, 'stand'), team='GB', num='34'))
    img = FG.draw_people(img, c, people, t)
    return img, c

def sideline(t, lt, focus_x, people, f=4200, zoom=1.0, y_cam=-60, z_cam=19):
    c = cam((focus_x, y_cam, z_cam), (focus_x, 4.5, -1.0), f * zoom * 1.35)
    img = render_world(c)
    d = ImageDraw.Draw(img)
    goalpost(d, c, 0); goalpost(d, c, 100)
    img = FG.draw_people(img, c, people, t)
    return img, c

def virtual_line(img, c, x, col=(255, 214, 40), a=170):
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    q = [c.p((x - .12, -26.6, 0.02)), c.p((x + .12, -26.6, 0.02)), c.p((x + .12, 26.6, 0.02)), c.p((x - .12, 26.6, 0.02))]
    if min(p[2] for p in q) > 0.3:
        d.polygon([p[:2] for p in q], fill=col + (a,))
    img.paste(lay, (0, 0), lay)

# ---------------------------------------------------------------- escenas por frase
def S0(t, T0, T1):
    lt = t - T0; dur = T1 - T0
    if lt < 2.7:
        img = whistle_macro(t, lt, 2.7)
        img = finish(img); d = ImageDraw.Draw(img)
        B.headline(d, 360, 'TOO COLD', 150)
        B.headline(d, 520, 'FOR WHISTLES', 130, YEL)
        return img
    img, c = ref_shot(t, lt - 2.7, dur - 2.7, 'whistle')
    img = finish(img); frost_vignette(img, 0.5); d = ImageDraw.Draw(img)
    B.headline(d, 360, 'THE COLDEST', 140)
    B.headline(d, 510, 'GAME EVER', 140, YEL)
    return img

def S1(t, T0, T1):
    lt = t - T0; dur = T1 - T0
    img, c = wide_ez(t, lt, k_desc=lt / dur)
    img = finish(img); sparkle(img, t); frost_vignette(img, 0.3); d = ImageDraw.Draw(img)
    lower_third(d, 1180, 'LAMBEAU FIELD', 'GREEN BAY · DECEMBER 31', t=lt)
    return img

def S2(t, T0, T1):
    lt = t - T0
    fx = 40 + lt * 0.8
    P = team_line(40, 1, poses=('3pt', '3pt'))
    P.append(dict(J=stance_pose((37.6, 0.3), 0, 'qb'), team='GB', num='15'))
    P.append(dict(J=stance_pose((34.5, -1), 0, 'ready'), team='GB', num='23', skin=2))
    P.append(dict(J=stance_pose((45, 4), math.pi, 'ready'), team='DAL', num='54', skin=3))
    P.append(dict(J=stance_pose((44.5, -5), math.pi, 'ready'), team='DAL', num='55', skin=4))
    img, c = sideline(t, lt, fx, P, f=5200)
    img = finish(img); d = ImageDraw.Draw(img)
    score_bug(d, 0, 0, '1ST QTR', title='NFL CHAMPIONSHIP')
    lower_third(d, 1180, 'PACKERS', 'VS. DALLAS COWBOYS', acc=GBY, t=lt)
    return img

def S3(t, T0, T1):
    lt = t - T0; dur = T1 - T0
    img, c = wide_ez(t, lt + 4, k_desc=1.0)
    img = finish(img); sparkle(img, t, 220); frost_vignette(img, 0.45); d = ImageDraw.Draw(img)
    thermo(d, W // 2, 760, '-13°F', 'KICKOFF TEMPERATURE', k=lt / 0.6, level=lerp(0.6, 0.12, ease(lt / 1.5)))
    return img

def S4(t, T0, T1):
    lt = t - T0
    img, c = wide_ez(t, lt + 7, k_desc=1.0)
    img = finish(img); snow_streaks(img, t, 1.0); frost_vignette(img, 0.55); d = ImageDraw.Draw(img)
    thermo(d, W // 2, 760, '-40°F', 'WITH THE WIND: OR WORSE', k=1.0, level=0.04)
    return img

def S5(t, T0, T1):
    lt = t - T0; dur = T1 - T0
    # camara a ras de suelo sobre el cesped helado, un jugador resbala
    k = clamp((lt - 1.2) / 1.6)
    x = 30 - lt * 2.2
    c = cam((x - 7.5, -4.2, 0.7), (x, 1.0, 0.75), 1650)
    img = render_world(c)
    if k <= 0:
        J = run_pose((x, 1.2), math.radians(185), lt * 1.7, speed=0.9)
    else:
        # resbalon: piernas se van hacia delante y cae de lado
        J0 = run_pose((x, 1.2), math.radians(185), lt * 1.7, speed=0.9)
        J1 = pose_joints((x, 1.2, lerp(0.95, 0.35, ease(k))), math.radians(185), pitch=lerp(0.2, -0.9, ease(k)),
                         legs=((1.1, 0.3), (0.7, 0.5)), arms=((1.6, 0.3, 0.9), (1.2, 0.4, 0.9)), ground=False)
        J = blend(J0, J1, ease(k)); J['f'] = J0['f']; J['s'] = J0['s']; J['tdir'] = J1['tdir']
    P = [dict(J=J, team='GB', num='87', skin=2)]
    img = FG.draw_people(img, c, P, t)
    img = finish(img); sparkle(img, t, 120); frost_vignette(img, 0.5); d = ImageDraw.Draw(img)
    if lt < dur * 0.45:
        lower_third(d, 1180, 'HEATING SYSTEM', 'UNDER THE FIELD', t=lt)
    else:
        lower_third(d, 1180, 'FAILED', 'THE TURF FROZE SOLID', col=(150, 24, 24), acc=(230, 240, 250), t=lt - dur * 0.45)
    return img

def kick_pose(P, yaw, k):
    """k 0..1: carrera, plantado, patada."""
    if k < 0.6:
        return run_pose(P, yaw, k * 3.2, speed=0.8)
    kk = (k - 0.6) / 0.4
    return pose_joints(P, yaw, pitch=lerp(0.15, -0.15, kk), legs=((lerp(-0.3, 1.5, ease(kk)), lerp(1.2, 0.15, ease(kk))), (0.15, 0.25)),
                       arms=((0.4, 0.4, 0.9), (0.2, 0.4, 0.7)))

def S6(t, T0, T1):
    lt = t - T0; dur = T1 - T0
    split = dur * 0.55
    if lt < split:
        k = lt / split
        kx = lerp(28, 35, min(1, k / 0.75))
        P = [dict(J=kick_pose((kx, 0.3), 0, k), team='GB', num='34')]
        for i in range(10):
            yy = -22 + i * 4.8 + (2 if i >= 5 else 0)
            P.append(dict(J=run_pose((kx - 1 + k * 3, yy), 0, k * 2 + i * .3, speed=0.5 + k * .5), team='GB', num=str(20 + i * 3), skin=i))
        kb = clamp((k - 0.9) / 0.1)
        if kb <= 0:
            bp = np.array([35.35, 0.3, 0.14])
        else:
            bp = np.array([35.35 + kb * 9, 0.3, 0.14 + math.sin(kb * 1.4) * 4.5])
        P.append(dict(J={'pelvis': bp}, team='PROP', prims=lambda c_, bp=bp: [(c_.depth(bp), lambda C, L: FG.football3(C, c_, bp, np.array([0, 0, 1.0]) if kb <= 0 else np.array([0.8, 0, 0.6]), L))]))
        img, c = sideline(t, lt, kx - 1.5 + k * 3, P, f=2600)
        d = ImageDraw.Draw(img)
        if k > 0.95:
            FG  # noop
        img = finish(img); d = ImageDraw.Draw(img)
        score_bug(d, 0, 0, '1ST QTR', title='OPENING KICKOFF')
        return img
    img, c = ref_shot(t, lt - split, dur - split, 'whistle')
    img = finish(img); frost_vignette(img, 0.55); d = ImageDraw.Draw(img)
    lower_third(d, 1180, 'WHISTLES FROZE', 'TO THE OFFICIALS\' LIPS', t=lt - split)
    return img

def S7(t, T0, T1):
    lt = t - T0
    img, c = ref_shot(t, lt + 0.8, T1 - T0, 'pull')
    img = finish(img); frost_vignette(img, 0.55); d = ImageDraw.Draw(img)
    lower_third(d, 1180, 'IT TORE THE SKIN', None, col=(150, 24, 24), acc=(230, 240, 250), t=lt)
    return img

def S8(t, T0, T1):
    lt = t - T0
    img, c = ref_shot(t, lt, T1 - T0, 'stop')
    img = finish(img); frost_vignette(img, 0.45); d = ImageDraw.Draw(img)
    if lt > 0.6:
        B.headline(d, 560, '"STOP!"', 190, YEL)
    lower_third(d, 1180, 'NO WHISTLES', 'OFFICIALS YELLED INSTEAD', t=lt)
    return img

def band_props(cam_, frost=1.0):
    """Sillas de la banda con instrumentos helados junto a la banda (sideline sur)."""
    def prims(c):
        out = []
        r = random.Random(4)
        for i in range(14):
            x = 32 + i * 2.6 + r.uniform(-.3, .3); y = -31.5 - (i % 2) * 1.6
            chair = (120, 80, 50)
            out.append((c.depth((x, y, .5)), lambda C, L, x=x, y=y: FG.cone(C, c, (x, y, .02), (x, y, .45), .03, .03, (60, 60, 64), L)))
            out.append((c.depth((x, y, .5)) - .1, lambda C, L, x=x, y=y: FG.cone(C, c, (x - .2, y, .46), (x + .2, y, .46), .06, .06, chair, L)))
            kind = i % 3
            brass = mix((200, 166, 70), (236, 240, 246), 0.35 * frost)
            if kind == 0:   # sousafon
                out.append((c.depth((x, y, 1)) - .2, lambda C, L, x=x, y=y, b=brass: FG.sphere(C, c, (x, y + .05, 1.15), .32, b, L, spec=.8, squash=1.0)))
                out.append((c.depth((x, y, 1)) - .25, lambda C, L, x=x, y=y: FG.sphere(C, c, (x, y - .2, 1.15), .22, (40, 32, 20), L)))
                out.append((c.depth((x, y, 1)) - .1, lambda C, L, x=x, y=y, b=brass: FG.cone(C, c, (x, y, .5), (x, y + .1, 1.0), .09, .14, b, L, spec=.8)))
            elif kind == 1:   # bombo
                out.append((c.depth((x, y, .8)) - .2, lambda C, L, x=x, y=y: FG.cone(C, c, (x - .15, y, .8), (x + .15, y, .8), .3, .3, (230, 232, 236), L)))
                out.append((c.depth((x, y, .8)) - .25, lambda C, L, x=x, y=y: FG.cone(C, c, (x - .17, y, .8), (x - .14, y, .8), .31, .31, (160, 30, 30), L)))
            else:   # trompeta sobre la silla
                out.append((c.depth((x, y, .6)) - .2, lambda C, L, x=x, y=y, b=brass: FG.cone(C, c, (x - .25, y, .55), (x + .2, y, .58), .02, .07, b, L, spec=1.0)))
        return out
    return dict(J={'pelvis': np.array([50, -32, .5])}, team='PROP', prims=prims)

def S9(t, T0, T1):
    lt = t - T0; dur = T1 - T0
    c = cam((40 + lt * 1.0, -60, 19), (40 + lt * 1.0, 4.5, -1.0), 4200)
    img = render_world(c)
    d0 = ImageDraw.Draw(img); goalpost(d0, c, 0)
    img = finish(img); sparkle(img, t, 150); frost_vignette(img, 0.5); d = ImageDraw.Draw(img)
    score_bug(d, 14, 10, 'HALFTIME')
    if lt > 0.3:
        B.headline(d, 600, 'HALFTIME SHOW', 120)
        B.headline(d, 730, 'CANCELLED', 150, (255, 80, 70))
    if lt > dur * 0.45:
        lower_third(d, 1180, 'THE BAND\'S INSTRUMENTS FROZE', 'SEVERAL MEMBERS: HYPOTHERMIA', t=lt - dur * 0.45)
    return img

def S10(t, T0, T1):
    lt = t - T0; dur = T1 - T0
    c = cam((50 + lt * 1.5, 12, 4), (52 + lt * 1.5, 60, 15), 1500)
    img = render_world(c)
    img = finish(img)
    # vaho sobre la grada
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d0 = ImageDraw.Draw(lay)
    r = random.Random(9)
    for i in range(60):
        x = (r.uniform(-100, W + 100) + t * 20) % (W + 200) - 100; y = r.uniform(300, 1300)
        rr = r.uniform(40, 120)
        d0.ellipse([x - rr, y - rr * .6, x + rr, y + rr * .6], fill=(255, 255, 255, int(r.uniform(15, 45))))
    lay = lay.filter(ImageFilter.GaussianBlur(25)); img.paste(lay, (0, 0), lay)
    frost_vignette(img, 0.4)
    d = ImageDraw.Draw(img)
    n = int(lerp(0, 50861, ease(lt / (dur * 0.7))))
    B.headline(d, 640, f'{n:,} FANS', 150)
    B.headline(d, 790, 'STAYED ANYWAY', 110, YEL)
    return img

def drive_people(x_ball, lt, phase='run', speed=1.0):
    P = []
    for i, yy in enumerate([-2.3, -1.15, 0, 1.15, 2.3]):
        P.append(dict(J=stance_pose((x_ball - 0.3 + lt * .3, yy), 0, 'block'), team='GB', num=['76', '64', '57', '63', '75'][i], skin=i))
        P.append(dict(J=stance_pose((x_ball + 0.7 + lt * .3, yy * 1.05 + .2), math.pi, 'block'), team='DAL', num=['74', '75', '54', '66', '88'][i], skin=i + 1))
    return P

def S11(t, T0, T1):
    lt = t - T0
    P = team_line(68, 1)
    P.append(dict(J=stance_pose((65.6, 0.3), 0, 'qb'), team='GB', num='15'))
    P.append(dict(J=stance_pose((62.5, -1), 0, 'ready'), team='GB', num='36', skin=2))
    P.append(dict(J=stance_pose((73, 4), math.pi, 'ready'), team='DAL', num='55', skin=3))
    P.append(dict(J=stance_pose((74, -5), math.pi, 'ready'), team='DAL', num='54', skin=4))
    img, c = sideline(t, lt, 67 + lt * .5, P, f=4600)
    virtual_line(img, c, 78)
    img = finish(img); d = ImageDraw.Draw(img)
    score_bug(d, 14, 17, '4TH QTR', extra='FINAL MINUTES')
    return img

def S12(t, T0, T1):
    lt = t - T0; dur = T1 - T0
    xb = 78 + lt * 1.8
    P = drive_people(78, lt)
    # corredor con el balon que avanza resbalando
    J = run_pose((xb - 1.5, -1.5 + lt * .4), 0.15, lt * 1.8, speed=0.95, carry='R')
    P.append(dict(J=J, team='GB', num='36', skin=2, ball=J['wrR'] + J['f'] * 0.05 + J['tdir'] * .05))
    P.append(dict(J=run_pose((xb + 1.6, 0.5), math.pi + 0.2, lt * 1.9, speed=0.9), team='DAL', num='40', skin=3))
    img, c = sideline(t, lt, 80 + lt * 1.4, P, f=4600)
    virtual_line(img, c, 88)
    img = finish(img); snow_streaks(img, t, 0.3, 60); d = ImageDraw.Draw(img)
    score_bug(d, 14, 17, '4TH QTR')
    lower_third(d, 1180, 'INCH BY INCH', 'ON A FROZEN FIELD', t=lt)
    return img

def goal_line_people(snap=0.0, dive=0.0, lt=0.0):
    """Formacion en la yarda 1 (Packers atacan hacia x=100). dive 0..1: Starr se lanza tras su guard."""
    P = []
    xl = 99.0
    gbn = ['75', '64', '57', '76', '63']   # 64 = Kramer, guard derecho
    dln = ['66', '75', '74', '54', '88']   # 75 = Pugh
    push = ease(dive) * 0.8
    for i, yy in enumerate([-2.3, -1.15, 0, 1.15, 2.3]):
        pose_gb = '3pt' if snap <= 0 else 'block'
        pose_dl = '3pt' if snap <= 0 else 'block'
        dx = push if gbn[i] in ('64', '57') else push * 0.3
        P.append(dict(J=stance_pose((xl - 0.9 + dx, yy), 0, pose_gb), team='GB', num=gbn[i], skin=i))
        P.append(dict(J=stance_pose((xl + 0.75 + dx * 0.9, yy * 1.05 + .15), math.pi, pose_dl), team='DAL', num=dln[i], skin=i + 1))
    # tight ends y backs
    P.append(dict(J=stance_pose((xl - 0.9, -3.6), 0, '3pt' if snap <= 0 else 'block'), team='GB', num='81', skin=3))
    P.append(dict(J=stance_pose((xl - 0.9, 3.6), 0, '3pt' if snap <= 0 else 'block'), team='GB', num='87', skin=4))
    P.append(dict(J=stance_pose((xl - 4.5, -0.7), 0, 'ready'), team='GB', num='36', skin=2))
    P.append(dict(J=stance_pose((xl - 4.5, 0.9), 0, 'ready'), team='GB', num='30', skin=0))
    P.append(dict(J=stance_pose((xl + 3.5, -2), math.pi, 'ready'), team='DAL', num='55', skin=3))
    P.append(dict(J=stance_pose((xl + 3.5, 2.2), math.pi, 'ready'), team='DAL', num='54', skin=4))
    # Bart Starr (15)
    if dive <= 0:
        J = stance_pose((xl - 1.9 + snap * 0.2, -0.05), 0, 'qb')
    else:
        k = ease(dive)
        x = lerp(xl - 1.7, 100.6, k)
        J = pose_joints((x, -0.85 * k, lerp(0.9, 0.55, k)), 0, pitch=lerp(0.6, 1.3, k), legs=((lerp(0.7, -0.2, k), lerp(1.0, 0.3, k)), (lerp(0.7, 0.2, k), lerp(1.0, 0.9, k))),
                        arms=((0.55, 2.1, 0.05), (0.6, 2.0, 0.05)), ground=False, head_pitch=-0.9)
    ball = J['pelvis'] + J['tdir'] * 0.35 + J['f'] * 0.22
    P.append(dict(J=J, team='GB', num='15', skin=0, ball=ball))
    return P

def S13(t, T0, T1):
    lt = t - T0
    c = cam((113, 8, 6.0), (98.0, -0.5, 0.0), 1750)
    img = render_world(c)
    d = ImageDraw.Draw(img); goalpost(d, c, 100)
    virtual_line(img, c, 99, (60, 140, 255), 150)
    img = FG.draw_people(img, c, goal_line_people(), t)
    img = finish(img); frost_vignette(img, 0.4); d = ImageDraw.Draw(img)
    score_bug(d, 14, 17, '4TH QTR', extra='3RD & GOAL · NO TIMEOUTS')
    return img

def S14(t, T0, T1):
    lt = t - T0; dur = T1 - T0
    # entrenador en la banda con abrigo y gorro de piel, de espaldas, mirando al campo
    c = cam((88 - lt * .3, -36.5, 1.9), (98, -10, 1.0), 1500)
    img = render_world(c)
    P = [dict(J=pose_joints((90.5, -31.2), math.radians(70), legs=((0.04, 0.05), (-0.06, 0.08)), arms=((0.25, 0.9, 0.18), (0.25, 0.9, 0.18))), team='COACH', skin=0)]
    for i, (xx, yy) in enumerate([(86, -31.8), (93.5, -32.4), (95.5, -31.6)]):
        P.append(dict(J=stance_pose((xx, yy), math.radians(80), 'stand'), team='GB', num=str(31 + i * 22), skin=i + 1))
    P += goal_line_people()
    img = FG.draw_people(img, c, P, t)
    img = finish(img); frost_vignette(img, 0.45); d = ImageDraw.Draw(img)
    if lt < dur * 0.45:
        lower_third(d, 1180, 'FIELD GOAL = TIE', 'SAFE CHOICE', t=lt)
    else:
        lower_third(d, 1180, 'LOMBARDI GOES', 'FOR THE WIN', acc=GBY, t=lt - dur * 0.45)
    return img

def S15(t, T0, T1):
    lt = t - T0; dur = T1 - T0
    snap = clamp(lt / 0.4)
    dive = clamp((lt - 0.4) / (dur * 0.62))
    c = cam((111.5 - lt * .4, 7.5, 5.2), (98.4, -0.6, 0.2), 2050)
    img = render_world(c)
    d = ImageDraw.Draw(img); goalpost(d, c, 100)
    img = FG.draw_people(img, c, goal_line_people(snap, dive, lt), t)
    img = finish(img); d = ImageDraw.Draw(img)
    if 0.15 < dive < 0.95:
        # flecha de telestrator hacia el hueco del guard derecho
        a = c.p((98.6, -0.2, .9)); b = c.p((100.6, -1.0, .9))
        ax, ay = a[0] / SS, a[1] / SS; bx, by = b[0] / SS, b[1] / SS
        d.line([ax, ay, bx, by], fill=YEL, width=12)
        ang = math.atan2(by - ay, bx - ax)
        d.polygon([(bx + 30 * math.cos(ang), by + 30 * math.sin(ang)), (bx + 26 * math.cos(ang + 2.3), by + 26 * math.sin(ang + 2.3)),
                   (bx + 26 * math.cos(ang - 2.3), by + 26 * math.sin(ang - 2.3))], fill=YEL)
    score_bug(d, 14, 17, '4TH QTR', extra='QB SNEAK · STARR #15')
    lower_third(d, 1180, 'BART STARR', 'BEHIND HIS GUARD, #64', acc=GBY, t=lt - 0.3 if lt > 0.45 else 0)
    return img

def S16(t, T0, T1):
    lt = t - T0
    c = cam((111 - lt * .4, 7.5, 5.0), (98.5, -0.8, 0.3), 1800)
    img = render_world(c, cheer=1.0)
    d = ImageDraw.Draw(img); goalpost(d, c, 100)
    P = goal_line_people(1, 1)
    # celebracion: brazos arriba de dos packers
    for p in P:
        if p['team'] == 'GB' and p['num'] in ('57', '76', '36'):
            J = p['J']
            p['J'] = pose_joints((J['pelvis'][0], J['pelvis'][1]), 0, legs=((0.1, .15), (-.1, .15)), arms=((2.9 + .15 * math.sin(lt * 8), .2, .35), (2.9 - .15 * math.sin(lt * 8), .2, .35)))
    img = FG.draw_people(img, c, P, t)
    img = finish(img); d = ImageDraw.Draw(img)
    B.headline(d, 600, 'TOUCHDOWN', 170, YEL)
    score_bug(d, 21, 17, '4TH QTR', flash='GB')
    return img

def S17(t, T0, T1):
    lt = t - T0; dur = T1 - T0
    img, c = wide_ez(t, lt, k_desc=1 - lt / dur, cheer=1.0, players='none', z0=34, z1=18)
    img = finish(img); sparkle(img, t, 200); frost_vignette(img, 0.35); d = ImageDraw.Draw(img)
    score_bug(d, 21, 17, 'FINAL', flash='GB')
    B.headline(d, 640, '3RD STRAIGHT', 140)
    B.headline(d, 790, 'NFL TITLE', 150, YEL)
    if lt > dur * 0.55:
        lower_third(d, 1180, 'AND NOT ONE', 'WHISTLE ALL GAME', t=lt - dur * 0.55)
    return img

LOGO = None
def S18(t, T0, T1):
    global LOGO
    lt = t - T0
    img, c = wide_ez(t, 10, k_desc=1.0, players='none')
    img = finish(img).filter(ImageFilter.GaussianBlur(14))
    img = Image.blend(img, Image.new('RGB', img.size, (6, 10, 20)), 0.55)
    d = ImageDraw.Draw(img)
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
