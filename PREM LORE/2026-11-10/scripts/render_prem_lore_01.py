"""Prem Lore 01 — Shane Long, 7,69 s. Render 1080x1920 30 fps.
Uso: python3 render_prem_lore_01.py [--test t1,t2,...] """
import json, math, sys, subprocess, os, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from multiprocessing import Pool
import world as Wd
from world import Cam, W, H

FPS = 30
A = Wd.A
TM = json.load(open('/home/claude/prem/times.json'))
U = TM['units']                       # 30 unidades (inicio, fin) en s
TAIL = 1.3
DUR = TM['dur'] + TAIL
NF = int(round(DUR * FPS))
def us(i): return U[i - 1][0]
def ue(i): return U[i - 1][1]

SCRIPT = [
 "The fastest goal in Premier League history took less time than it takes to read this sentence.",
 "Seven point six nine seconds.",
 "April twenty-third, twenty nineteen.", "Vicarage Road.", "Watford against Southampton.",
 "Watford kick off, and Roberto Pereyra rolls it straight back to centre-back Craig Cathcart.",
 "Nothing to see here.", "The kind of pass that happens every single weekend.",
 "But Shane Long is already sprinting.",
 "Cathcart tries to launch it forward, and Long throws himself in the way.",
 "The ball smacks off him and runs loose.",
 "Suddenly he's through, with only Ben Foster to beat.",
 "He doesn't panic.", "He just lifts it over the keeper.",
 "Seven point six nine seconds.", "The fastest goal the Premier League has ever seen.",
 "It happened so fast, Elton John's \"Rocket Man\" was still playing over the stadium speakers.",
 "The record he broke belonged to Ledley King.",
 "Tottenham, away at Bradford, December two thousand.", "Nine point eight two seconds.",
 "It had stood for more than eighteen years.", "Long smashed it by over two seconds.",
 "And the twist?", "Southampton didn't even win.",
 "Watford equalised in the ninetieth minute.", "One all.",
 "Seven years later, nobody has even broken nine seconds.",
 "So...", "how long did it take you to read the title?",
 "Vote for tomorrow's story in the comments.",
]
assert len(SCRIPT) == len(U)

def F(name, size): return ImageFont.truetype(A + name, size)
ANTON = lambda s: F('Anton-Regular.ttf', s)
BEBAS = lambda s: F('BebasNeue-Regular.ttf', s)
GRAD = lambda s: F('Graduate-Regular.ttf', s)
YEL = (255, 214, 0)

def clamp(x, a=0, b=1): return max(a, min(b, x))
def ss(x): x = clamp(x); return x * x * (3 - 2 * x)
def lerp(a, b, t): return a + (b - a) * t
def lerpv(a, b, t): return tuple(lerp(x, y, t) for x, y in zip(a, b))

# ------------------------------------------------------------------ palabras / subtítulos
WORDS = []   # (texto, t0, t1, unidad)
for i, (txt, (a, b)) in enumerate(zip(SCRIPT, U)):
    ws = txt.split()
    wt = [len(w.strip('.,?!"')) + 2.2 + (1.5 if w[-1] in '.,?!' else 0) for w in ws]
    tot = sum(wt); t = a
    for w, k in zip(ws, wt):
        d = (b - a) * k / tot
        WORDS.append((w, t, t + d, i + 1)); t += d

# grupos de hasta 3 palabras (sin cruzar unidad)
GROUPS = []
cur = []
for w in WORDS:
    if cur and (len(cur) >= 3 or cur[-1][3] != w[3] or cur[-1][0][-1] in '.?!,'):
        GROUPS.append(cur); cur = []
    cur.append(w)
GROUPS.append(cur)

# ------------------------------------------------------------------ tiempo de juego
# mapa vídeo → tiempo de partido (tg)
TG_KEYS = [(0, 0.0), (us(6), 0.0), (ue(6), 2.4), (ue(8), 3.4), (ue(9), 4.3), (ue(10), 5.0),
           (ue(11), 5.6), (ue(12), 6.75), (ue(13), 7.02), (ue(14) + 0.02, 7.69), (ue(16), 11.0), (ue(17), 14.0)]
def tg_of(t):
    for (t0, g0), (t1, g1) in zip(TG_KEYS, TG_KEYS[1:]):
        if t <= t1:
            return g0 if t1 == t0 else lerp(g0, g1, (t - t0) / (t1 - t0))
    return TG_KEYS[-1][1]

def track(keys, tg):
    """keys: [(tg, x, y[, z])] interpolación suave tipo Catmull-Rom"""
    if tg <= keys[0][0]: return np.array(keys[0][1:], float)
    if tg >= keys[-1][0]: return np.array(keys[-1][1:], float)
    for i in range(len(keys) - 1):
        if keys[i][0] <= tg <= keys[i + 1][0]:
            p0 = np.array(keys[max(0, i - 1)][1:], float); p1 = np.array(keys[i][1:], float)
            p2 = np.array(keys[i + 1][1:], float); p3 = np.array(keys[min(len(keys) - 1, i + 2)][1:], float)
            u = (tg - keys[i][0]) / (keys[i + 1][0] - keys[i][0])
            return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)

# Watford defiende x=0 (portería izquierda), Southampton x=105
BALL = [(0, 52.5, 34, 0), (0.05, 52.5, 34, 0), (0.6, 49.0, 31.5, 0), (1.5, 43.5, 27.8, 0), (2.4, 38.4, 24.4, 0),
        (2.9, 37.2, 24.0, 0), (3.4, 36.4, 23.8, 0), (4.3, 35.7, 23.7, 0), (4.85, 35.45, 23.65, 0),
        (4.92, 35.9, 23.9, 0.5), (5.05, 34.8, 24.1, 0.2), (5.3, 32.4, 24.7, 0), (5.6, 29.8, 25.5, 0),
        (6.2, 24.6, 27.3, 0), (6.68, 20.6, 28.8, 0), (6.75, 20.2, 29.0, 0.05), (7.05, 15.6, 30.0, 3.2),
        (7.35, 8.8, 31.4, 3.9), (7.69, 0.0, 33.0, 1.25), (7.85, -1.5, 33.2, 0.4), (8.2, -1.8, 33.3, 0.1), (14, -1.8, 33.3, 0.1)]

PLAYERS = []   # dict(team, kit, keys, name, num, poses=fn)
def P(team, keys, name='', num=0, kit=None, seed=0):
    PLAYERS.append(dict(team=team, kit=kit or team, keys=keys, name=name, num=num, seed=seed))
    return PLAYERS[-1]

# --- protagonistas
LONG = P('SOU', [(0, 62.0, 30.5), (0.8, 61.2, 30.2), (1.6, 57.5, 29.0), (2.4, 51.0, 27.6), (3.4, 44.2, 26.0),
                 (4.3, 38.9, 24.8), (4.9, 36.5, 24.3), (5.05, 35.9, 24.3), (5.6, 31.6, 25.4), (6.2, 25.9, 27.3),
                 (6.68, 21.4, 28.8), (6.85, 20.4, 29.1), (7.69, 15.8, 31.0), (8.6, 10.5, 40.0), (10.0, 6.5, 55.0), (14, 3.5, 63.0)],
         'SHANE LONG', 7, seed=7)
CATH = P('WAT', [(0, 37.8, 22.5), (2.0, 37.6, 23.6), (2.4, 37.3, 23.8), (3.4, 36.9, 23.7), (4.85, 36.4, 23.6),
                 (5.6, 34.6, 24.4), (6.2, 30.4, 25.8), (6.75, 27.0, 27.0), (7.69, 22.0, 29.0), (14, 20.0, 30.0)],
         'CRAIG CATHCART', 15, seed=15)
PERE = P('WAT', [(0, 52.7, 34.7), (0.3, 52.8, 35.2), (2.4, 55.0, 34.0), (5.0, 58.0, 33.0), (7.69, 55.0, 32.0), (14, 50.0, 32.0)],
         'ROBERTO PEREYRA', 37, seed=37)
FOST = P('WAT', [(0, 5.5, 34.0), (4.0, 6.0, 33.6), (5.6, 8.0, 32.6), (6.75, 11.2, 31.6), (7.05, 12.0, 31.3), (7.69, 12.4, 31.2), (14, 9.0, 33.0)],
         'BEN FOSTER', 26, kit='WGK', seed=26)
GUNN = P('SOU', [(0, 99.5, 34.0), (14, 96.0, 34.0)], '', 28, kit='SGK', seed=28)
# --- resto: posiciones base + deriva
WAT_BASE = [(37.0, 9.0), (37.5, 46.0), (37.0, 59.0), (44.5, 13.0), (44.0, 28.5), (44.0, 40.0), (45.0, 55.0), (52.9, 37.6)]
SOU_BASE = [(80.0, 22.0), (81.0, 34.0), (80.0, 46.0), (67.0, 8.0), (65.0, 27.0), (65.0, 41.0), (67.0, 60.0), (61.0, 12.0), (61.0, 56.0)]
for i, (x, y) in enumerate(WAT_BASE):
    ks = [(0, x, y), (2.0, x + 0.6, y), (4.9, x + 2.6, y + (34 - y) * 0.05), (6.75, x - 2.0, y + (30 - y) * 0.12), (7.69, x - 5.5, y + (30 - y) * 0.18), (14, x - 12, y + (30 - y) * 0.3)]
    P('WAT', ks, seed=100 + i)
for i, (x, y) in enumerate(SOU_BASE):
    ks = [(0, x, y), (1.2, x - 0.6, y), (4.9, x - 7.0, y + (30 - y) * 0.1), (7.69, x - 13.0, y + (30 - y) * 0.2), (14, x - 20, y + (20 - y) * 0.4)]
    P('SOU', ks, seed=200 + i)

SKINS = [(214, 168, 130), (180, 128, 92), (120, 80, 55), (90, 60, 42), (232, 190, 160), (200, 150, 110)]
HAIRS = [(40, 28, 20), (20, 16, 14), (90, 60, 30), (150, 110, 60), (25, 20, 18)]
LONG['skin'], LONG['hair'] = (226, 180, 150), (70, 46, 26)
CATH['skin'], CATH['hair'] = (228, 186, 156), (60, 40, 24)
PERE['skin'], PERE['hair'] = (205, 158, 118), (30, 22, 16)
FOST['skin'], FOST['hair'] = (226, 182, 150), (40, 30, 20)
for p in PLAYERS:
    p.setdefault('skin', SKINS[p['seed'] % len(SKINS)]); p.setdefault('hair', HAIRS[(p['seed'] * 7) % len(HAIRS)])

def pose_of(p, tg, vel):
    sp = float(np.hypot(vel[0], vel[1]))
    nm = p['name']
    if nm == 'SHANE LONG':
        if 4.78 <= tg <= 5.08: return 'block', 0
        if 6.55 <= tg <= 6.92: return 'chip', (tg - 6.55) / 0.37
        if tg > 8.0: return 'celebrate', None
    if nm == 'CRAIG CATHCART' and 4.45 <= tg <= 4.95: return 'kick', (tg - 4.45) / 0.5
    if nm == 'ROBERTO PEREYRA' and -0.2 <= tg <= 0.25 and tg > 0: return 'kick', clamp(tg / 0.25)
    if nm == 'BEN FOSTER':
        if 7.0 <= tg <= 7.8: return 'reach', ss((tg - 7.0) / 0.3)
        return ('gk' if sp < 3 else 'run'), None
    if p['kit'] in ('SGK',): return 'gk', None
    if sp < 0.4: return 'stand', None
    if sp < 3.0: return 'jog', None
    return 'run', None

def player_state(p, tg):
    pos = track(p['keys'], tg)
    pos2 = track(p['keys'], tg + 0.05)
    vel = (pos2 - pos) / 0.05
    return pos, vel

# ------------------------------------------------------------------ plan de cámaras
def ball_at(tg): return track(BALL, tg)

def main_cam(target, fov, x_off=0.0):
    return Cam((52.5 + x_off, -26, 17.5), target, fov)

def camera_for(t, tg, sm_target):
    """devuelve (cam, escena, extra)"""
    if t < us(3) - 0.15:      # A: plano general de presentación desde lo alto de la grada
        k = t / (us(3))
        return Cam((52.5 - 8 * k, -10, 30 - 3 * k), (52.5, 44, 0), 56 - 6 * k), 'A'
    if t < us(6) - 0.15:      # B: detrás de la portería (presentar el campo)
        k = (t - us(3)) / (us(6) - us(3))
        return Cam((-13 + 4 * k, 34 - 2 * k, 13 - 2 * k), (40 + 4 * k, 33, 0), 48 - 4 * k), 'B'
    if t < us(15) - 0.1:      # C: cámara principal de banda que sigue el balón
        fov = 20
        if tg > 3.6: fov = lerp(20, 14.5, ss((tg - 3.6) / 0.9))
        if tg > 5.05: fov = lerp(14.5, 21, ss((tg - 5.05) / 1.0))
        if tg > 6.4: fov = lerp(21, 17, ss((tg - 6.4) / 0.8))
        return main_cam(sm_target, fov), 'C'
    if t < us(17) - 0.1:      # D: repetición desde detrás de la portería
        return Cam((-7.5, 36.5, 3.6), (19, 30, 1.0), 44), 'D'
    if t < us(18) - 0.1:      # E: panorámica hacia la pantalla del estadio
        k = ss((t - us(17)) / (ue(17) - us(17) - 0.8))
        tgt = lerpv((8, 50, 1.0), (-11, 79, 15.5), k)
        return Cam((52.5, -26, 17.5), tgt, lerp(30, 17, k)), 'E'
    if t < us(23) - 0.1:      # F: grafismo del récord sobre plano general
        k = (t - us(18)) / (ue(22) - us(18))
        return Cam((52.5 + 10 * k, -10, 28), (52.5, 44, 0), 56), 'F'
    if t < us(27) - 0.1:      # G: el giro — área del Southampton
        k = (t - us(23)) / (ue(26) - us(23))
        return Cam((80 + 6 * k, -24, 15), (96, 34, 0.5), 30 - 4 * k), 'G'
    if t < us(28) - 0.1:      # H: grafismo "nadie bajo 9 s"
        k = (t - us(27)) / (ue(27) - us(27))
        return Cam((40 - 8 * k, -10, 28), (52.5, 44, 0), 56), 'H'
    if t < us(30) - 0.1:      # I: vuelta al plano inicial con cronómetro
        k = (t - us(28)) / (ue(29) - us(28))
        return Cam((44 + 6 * k, -10, 29), (52.5, 44, 0), 54), 'I'
    k = (t - us(30)) / (DUR - us(30))
    return Cam((52.5, -10, 30 + 2 * k), (52.5, 44, 0), 56 + 4 * k), 'J'

# objetivo suavizado de la cámara principal (precalculado)
def precompute_targets():
    tgt = None; out = []
    for fi in range(NF):
        t = fi / FPS; tg = tg_of(t)
        b = ball_at(tg); b2 = ball_at(tg + 0.45)
        want = np.array([lerp(b[0], b2[0], 0.6) - 1.5, lerp(b[1], b2[1], 0.5) * 0.85 + 5.0, 0.5])
        if tg > 6.4:
            k = ss((tg - 6.4) / 0.8)
            want = want * (1 - k) + np.array([11.0, 31.0, 1.0]) * k
        if tgt is None: tgt = want
        else: tgt = tgt + (want - tgt) * 0.22
        out.append(tgt.copy())
    return out

# ------------------------------------------------------------------ recursos globales (por proceso)
G = {}
def init_resources():
    G['ground'] = Wd.make_ground()
    G['planes'] = Wd.build_stadium()
    G['screen_np'] = Wd.screen_plane([("NOW PLAYING", 1.1, (255, 214, 0)), ("ROCKET MAN", 2.2, (255, 255, 255)), ("ELTON JOHN", 0.9, (200, 200, 210))])
    G['screen_idle'] = Wd.screen_plane([("WATFORD", 1.6, (255, 214, 0)), ("v", 0.8, (220, 220, 220)), ("SOUTHAMPTON", 1.5, (255, 255, 255))])
    G['targets'] = precompute_targets()
    lg = Image.open(A + 'logo.png').convert('RGBA')
    G['logo'] = lg

# ------------------------------------------------------------------ dibujo de la escena 3D
def render_world(t, cam, scene, tg):
    night = clamp(0.35 + t / 80 * 0.65)
    fr = Wd.render_sky(cam, night)
    fr = Wd.render_ground(fr, cam, G['ground'])
    extra = [G['screen_np']] if scene == 'E' else []
    fr = Wd.render_planes(fr, cam, G['planes'] + extra)
    # brillo de focos / grado nocturno
    fr = fr * (0.98 - 0.06 * night) + 4
    img = Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8)).convert('RGBA')
    d = ImageDraw.Draw(img, 'RGBA')

    # objetos ordenados por profundidad
    objs = []
    for gx, sg in ((0.0, -1), (105.0, 1)):
        objs.append((cam.depth((gx + sg * 1.0, 34, 1.2)), 'goal', (gx, sg)))
    if scene in ('G',):
        tgx = 0.0
        # jugada del empate (minuto 90): balón entra en la portería del Southampton
        k = clamp((t - us(25)) / 1.3)
        bpos = np.array(lerpv((86.0, 38.0, 0.0), (105.6, 35.5, 0.9), ss(k)) if k < 1 else (106.4, 35.4, 0.3))
        bpos[2] = 0.9 * math.sin(math.pi * min(1, k)) * 0.8 if k < 1 else 0.3
    else:
        bpos = ball_at(tg)
    if scene == 'D':
        rtg = lerp(6.35, 8.1, clamp((t - us(15)) / (ue(16) - us(15) - 0.4)))
        bpos = ball_at(rtg); ptg = rtg
    else:
        ptg = tg
    # jugadores
    for p in PLAYERS:
        if scene == 'G':
            pos, vel = g_scene_player(p, t)
        else:
            pos, vel = player_state(p, ptg)
        objs.append((cam.depth((pos[0], pos[1], 0.9)), 'pl', (p, pos, vel)))
    objs.append((cam.depth(bpos), 'ball', bpos))
    # sombra del balón (en el suelo, antes que nada)
    u, v, z = cam.proj((bpos[0], bpos[1], 0))
    if z > 0.5:
        r = cam.f * 0.15 / z
        d.ellipse([u - r * 1.4, v - r * 0.5, u + r * 1.4, v + r * 0.5], fill=(0, 0, 0, 90))
    objs.sort(key=lambda o: -o[0])
    label_pts = {}
    for dep, kind, data in objs:
        if dep < 0.6: continue
        if kind == 'goal':
            Wd.draw_goal(d, cam, data[0], data[1])
        elif kind == 'ball':
            u, v, z = cam.proj(bpos)
            r = max(7.5, cam.f * 0.13 / z)
            d.ellipse([u - r - 2, v - r - 2, u + r + 2, v + r + 2], fill=(20, 20, 24, 200))
            d.ellipse([u - r, v - r, u + r, v + r], fill=(252, 252, 252, 255))
            if r > 5:
                d.ellipse([u - r * 0.35, v - r * 0.35, u + r * 0.25, v + r * 0.25], fill=(30, 30, 30, 255))
        else:
            p, pos, vel = data
            u, v, z = cam.proj((pos[0], pos[1], 0))
            if not (-200 < u < W + 200 and -400 < v < H + 400): continue
            hp = cam.f * 1.82 / z
            if hp < 6: continue
            # dirección en pantalla
            u2, _, _ = cam.proj((pos[0] + vel[0] * 0.1 + 0.001, pos[1] + vel[1] * 0.1, 0))
            facing = 1 if (u2 - u) > 0.3 else (-1 if (u2 - u) < -0.3 else p.get('_face', 1 if p['team'] == 'WAT' else -1))
            p['_face'] = facing
            pose, pt = pose_of(p, ptg if scene != 'G' else 2.0, vel)
            if scene == 'G': pose = g_pose(p, t, vel)
            dist = p['seed'] * 1.7 + (tg if scene not in ('D', 'G') else ptg) * float(np.hypot(*vel)) / 1.9
            ph = dist * 2.2 + p['seed']
            if pose in ('stand', 'gk'): ph = t * 2 + p['seed']
            sp, ax, ay = Wd.draw_player_sprite(hp, Wd.KITS[p['kit']], pose, ph, facing, pt or 0, p['skin'], p['hair'], p['seed'])
            # sombra
            d.ellipse([u - hp * 0.22, v - hp * 0.035, u + hp * 0.22, v + hp * 0.035], fill=(0, 0, 0, 70))
            img.alpha_composite(sp, (int(u - ax), int(v - ay)))
            if p['name']: label_pts[p['name']] = (u, v - hp * 1.05, hp)
    return img, label_pts

def g_scene_player(p, t):
    """escena del minuto 90: ataque del Watford sobre la portería del Southampton"""
    rnd = np.random.default_rng(p['seed'])
    if p['team'] == 'WAT' and p['kit'] == 'WAT':
        base = np.array([rnd.uniform(70, 94), rnd.uniform(12, 56)])
    elif p['kit'] == 'SOU':
        base = np.array([rnd.uniform(84, 101), rnd.uniform(16, 52)])
    elif p['kit'] == 'SGK':
        base = np.array([103.0, 34.5])
    else:
        base = np.array([38.0, 34.0])
    if p['name'] == 'SHANE LONG': base = np.array([70.0, 30.0])
    k = clamp((t - us(25)) / 1.3)
    drift = np.array([math.sin(t * 0.7 + p['seed']) * 1.5, math.cos(t * 0.5 + p['seed']) * 1.2])
    if p['kit'] == 'SGK': drift = np.array([0, -3.0 * ss(k)])
    pos = base + drift
    vel = np.array([math.cos(t * 0.7 + p['seed']) * 1.0, -math.sin(t * 0.5 + p['seed']) * 0.6])
    return pos, vel

def g_pose(p, t, vel):
    if p['kit'] == 'SGK': return 'reach' if t > us(25) + 0.7 else 'gk'
    if p['kit'] == 'WGK': return 'stand'
    k = t - us(25) - 1.3
    if p['kit'] == 'WAT' and k > 0: return 'celebrate'
    return 'jog'

# ------------------------------------------------------------------ grafismos
def text_c(d, xy, s, font, fill, stroke=0, sfill=(0, 0, 0), anchor='mm'):
    d.text(xy, s, font=font, fill=fill, stroke_width=stroke, stroke_fill=sfill, anchor=anchor)

def watermark(d):
    text_c(d, (W / 2, 70), '@premlore', BEBAS(54), (255, 255, 255, 170), 2, (0, 0, 0, 120))

def score_bug(d, clock, hs, as_, alpha=1.0, flash=0.0):
    x, y = 46, 120
    a = int(235 * alpha)
    d.rounded_rectangle([x, y, x + 470, y + 70], 10, fill=(12, 14, 26, a))
    d.rectangle([x + 10, y + 12, x + 22, y + 58], fill=(252, 210, 16, a))
    text_c(d, (x + 72, y + 36), 'WAT', BEBAS(52), (255, 255, 255, a))
    d.rectangle([x + 122, y + 8, x + 222, y + 62], fill=(255, 255, 255, a))
    text_c(d, (x + 172, y + 37), f'{hs} - {as_}', BEBAS(54), (12, 14, 26, a))
    text_c(d, (x + 272, y + 36), 'SOU', BEBAS(52), (255, 255, 255, a))
    d.rectangle([x + 320, y + 12, x + 332, y + 58], fill=(205, 24, 38, a))
    text_c(d, (x + 400, y + 37), clock, BEBAS(52), YEL + (a,))
    if flash > 0:
        d.rounded_rectangle([x, y + 74, x + 470, y + 134], 8, fill=(205, 24, 38, int(235 * flash)))
        text_c(d, (x + 235, y + 105), 'GOAL  ·  S. LONG  7.69s', BEBAS(48), (255, 255, 255, int(255 * flash)))

def stopwatch(d, cx, cy, val, scale=1.0, label='TIME', glow=0.0):
    w, h = 560 * scale, 210 * scale
    if glow > 0:
        for i in range(6):
            e = 14 * i * scale
            d.rounded_rectangle([cx - w / 2 - e, cy - h / 2 - e, cx + w / 2 + e, cy + h / 2 + e], int(30 * scale + e),
                                fill=(255, 214, 0, int(26 * glow * (6 - i) / 6)))
    d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], int(28 * scale), fill=(10, 12, 22, 235),
                        outline=(255, 214, 0, 255), width=max(2, int(6 * scale)))
    text_c(d, (cx, cy - h * 0.36), label, BEBAS(int(46 * scale)), (200, 200, 210, 255))
    text_c(d, (cx, cy + h * 0.10), f'{val:.2f}s', ANTON(int(128 * scale)), YEL + (255,))

def name_tag(d, pt, name, num, alpha):
    if pt is None or alpha <= 0: return
    u, v, hp = pt
    a = int(255 * alpha)
    f = BEBAS(46)
    s = f'{num}  {name}'
    tw = d.textlength(s, font=f)
    x0 = u - tw / 2 - 18; y0 = v - 86
    x0 = clamp(x0, 20, W - tw - 56)
    d.rounded_rectangle([x0, y0, x0 + tw + 36, y0 + 56], 8, fill=(12, 14, 26, int(220 * alpha)))
    d.rectangle([x0, y0 + 50, x0 + tw + 36, y0 + 56], fill=YEL + (a,))
    d.text((x0 + 18, y0 + 6), s, font=f, fill=(255, 255, 255, a))
    d.polygon([(u - 12, y0 + 56), (u + 12, y0 + 56), (u, v - 14)], fill=YEL + (a,))

def tele_arrow(d, p0, p1, alpha, prog=1.0):
    """flecha de telestrator (estilo TV) dibujada sobre el césped en pantalla"""
    if alpha <= 0: return
    a = int(255 * alpha)
    pts = []
    for i in range(41):
        k = i / 40 * prog
        x = lerp(p0[0], p1[0], k); y = lerp(p0[1], p1[1], k) - math.sin(k * math.pi) * 40
        pts.append((x, y))
    d.line(pts, fill=(255, 214, 0, a), width=12, joint='curve')
    if prog > 0.9:
        x, y = pts[-1]; x2, y2 = pts[-3]
        ang = math.atan2(y - y2, x - x2)
        L = 40
        d.polygon([(x + math.cos(ang) * 10, y + math.sin(ang) * 10),
                   (x - math.cos(ang - 0.5) * L, y - math.sin(ang - 0.5) * L),
                   (x - math.cos(ang + 0.5) * L, y - math.sin(ang + 0.5) * L)], fill=(255, 214, 0, a))

def lower_third(d, title, sub, alpha, y=1150):
    if alpha <= 0: return
    a = int(255 * alpha)
    off = (1 - ss(alpha)) * -120
    f1 = ANTON(78); f2 = BEBAS(54)
    w1 = d.textlength(title, font=f1) + 60
    w2 = d.textlength(sub, font=f2) + 50 if sub else 0
    x = 60 + off
    d.rectangle([x, y, x + w1, y + 104], fill=(12, 14, 26, int(230 * alpha)))
    d.rectangle([x, y, x + 12, y + 104], fill=YEL + (a,))
    d.text((x + 34, y + 8), title, font=f1, fill=(255, 255, 255, a))
    if sub:
        d.rectangle([x, y + 104, x + w2, y + 170], fill=YEL + (int(240 * alpha),))
        d.text((x + 26, y + 112), sub, font=f2, fill=(12, 14, 26, a))

def record_panel(d, t, mode):
    """barras de los goles más rápidos (sin años ni escudos)"""
    x0, y0, w = 70, 430, W - 140
    d.rounded_rectangle([x0, y0, x0 + w, y0 + 700], 26, fill=(10, 12, 22, 225), outline=(255, 214, 0, 255), width=5)
    head = 'FASTEST PREMIER LEAGUE GOALS' if mode == 'F' else 'FASTEST SINCE THAT NIGHT'
    text_c(d, (W / 2, y0 + 70), head, ANTON(62), (255, 255, 255, 255))
    bx0 = x0 + 50; bx1 = x0 + w - 50
    scale = lambda s: bx0 + (bx1 - bx0) * s / 10.5
    # eje
    for s in range(0, 11, 2):
        xx = scale(s)
        d.line([xx, y0 + 140, xx, y0 + 600], fill=(255, 255, 255, 40), width=2)
        text_c(d, (xx, y0 + 630), f'{s}s', BEBAS(40), (180, 180, 190, 255))
    def bar(row, name, sub, val, prog, col, show_val=True):
        yy = y0 + 160 + row * 210
        d.text((bx0, yy), name, font=ANTON(52), fill=(255, 255, 255, 255))
        if sub: d.text((bx0 + d.textlength(name, font=ANTON(52)) + 22, yy + 16), sub, font=BEBAS(40), fill=(190, 190, 200, 255))
        v = val * clamp(prog)
        d.rounded_rectangle([bx0, yy + 82, max(bx0 + 8, scale(v)), yy + 150], 10, fill=col + (255,))
        if show_val and prog > 0.12:
            text_c(d, (scale(v) - 14, yy + 116), f'{v:.2f}s', ANTON(52), (12, 14, 26, 255), 0, anchor='rm')
    if mode == 'F':
        pk = clamp((t - us(18)) / 0.6)
        if t >= us(18):
            kp = clamp((t - us(20)) / (ue(20) - us(20))) if t < ue(20) else 1.0
            if t < us(20): kp = 0.0
            bar(1, 'LEDLEY KING', 'TOTTENHAM' + ('  ·  AWAY AT BRADFORD' if t >= us(19) else ''), 9.82, kp, (230, 230, 235))
        if t >= us(22) - 0.2:
            lp = clamp((t - us(22) + 0.2) / 1.2)
            bar(0, 'SHANE LONG', 'SOUTHAMPTON', 7.69, lp, (255, 214, 0))
            if lp >= 1:
                text_c(d, (W / 2 + 200, y0 + 160 + 34), '-2.13s', ANTON(60), (120, 255, 150, 255), 3)

        if us(21) <= t < us(22) - 0.2 + 3:
            k = clamp((t - us(21)) / 1.2)
            yrs = int(round(18 * k))
            d.rounded_rectangle([W / 2 - 300, y0 + 730, W / 2 + 300, y0 + 830], 16, fill=(205, 24, 38, 255))
            text_c(d, (W / 2, y0 + 782), f'RECORD STOOD {yrs}+ YEARS', ANTON(64), (255, 255, 255, 255))
    else:
        bar(0, 'SHANE LONG', '', 7.69, 1, (255, 214, 0))
        bar(1, 'NEXT BEST', '', 9.11, clamp((t - us(27)) / 1.0), (230, 230, 235))
        xx = scale(9.0)
        k = clamp((t - us(27) - 0.9) / 0.6)
        if k > 0:
            for dy in range(y0 + 130, y0 + 610, 26):
                d.line([xx, dy, xx, dy + 14], fill=(205, 24, 38, int(255 * k)), width=6)
            d.rounded_rectangle([xx - 70, y0 + 118, xx + 70, y0 + 166], 10, fill=(205, 24, 38, int(255 * k)))
            text_c(d, (xx, y0 + 143), '9.00s', BEBAS(46), (255, 255, 255, int(255 * k)))

def subtitles(d, t):
    if t > ue(30) + 0.2: return
    g = None
    for gr in GROUPS:
        if gr[0][1] - 0.05 <= t <= gr[-1][2] + 0.25: g = gr
    if g is None: return
    f = ANTON(108)
    words = [w[0].upper().replace('"', '') for w in g]
    sp = 26
    widths = [d.textlength(w, font=f) for w in words]
    total = sum(widths) + sp * (len(words) - 1)
    lines = [list(range(len(words)))]
    if total > W - 120 and len(words) > 1:
        lines = [list(range(len(words) - 1)), [len(words) - 1]]
    y = 1500
    for li, ln in enumerate(lines):
        tot = sum(widths[i] for i in ln) + sp * (len(ln) - 1)
        x = (W - tot) / 2
        for i in ln:
            act = g[i][1] <= t < (g[i + 1][1] if i + 1 < len(g) else g[i][2] + 0.25)
            pop = 1.0
            col = YEL if act else (255, 255, 255)
            d.text((x, y + li * 128), words[i], font=f, fill=col + (255,), stroke_width=9, stroke_fill=(0, 0, 0, 255))
            x += widths[i] + sp

def closing(img, t):
    k = ss((t - us(30)) / 0.5)
    ov = Image.new('RGBA', img.size, (6, 8, 16, int(170 * k)))
    img.alpha_composite(ov)
    lg = G['logo']; sz = int(520 * lerp(0.85, 1.0, k))
    l2 = lg.resize((sz, sz), Image.LANCZOS)
    if k < 1:
        al = l2.getchannel('A').point(lambda v: int(v * k)); l2.putalpha(al)
    img.alpha_composite(l2, (int(W / 2 - sz / 2), int(560 - sz / 2)))
    d = ImageDraw.Draw(img, 'RGBA')
    a = int(255 * k)
    text_c(d, (W / 2, 930), "TOMORROW'S STORY?", ANTON(110), (255, 255, 255, a), 8)
    text_c(d, (W / 2, 1070), 'VOTE IN THE COMMENTS ↓', ANTON(76), YEL + (a,), 6)

# ------------------------------------------------------------------ fotograma
def render_frame(fi, with_subs=True):
    t = fi / FPS
    tg = tg_of(t)
    cam, scene = camera_for(t, tg, G['targets'][fi])
    img, labels = render_world(t, cam, scene, tg)
    # viñeta + desenfoque de fondo bajo grafismos grandes
    if scene in ('F', 'H') or (scene == 'J'):
        bl = img.filter(ImageFilter.GaussianBlur(9))
        img = Image.blend(img, bl, 0.85)
        img.alpha_composite(Image.new('RGBA', img.size, (0, 0, 0, 80)))
    d = ImageDraw.Draw(img, 'RGBA')

    # marcador de TV
    if us(3) + 0.3 <= t < us(18) - 0.1 or (scene == 'G'):
        if scene == 'G':
            k = clamp((t - us(23)) / (us(25) - us(23)))
            mins = int(lerp(8, 90, ss(k)))
            if t < us(25): clock = f'{mins:02d}:{int((k * 3000) % 60):02d}'
            else: clock = '90:00' if t < us(26) else 'FT'
            hs = 1 if t >= us(25) + 1.3 else 0
            score_bug(d, clock, hs, 1)
        else:
            gsec = tg if scene != 'D' else 7.69
            clock = f'00:{int(min(gsec, 59)):02d}'
            goal = t >= ue(14) + 0.02
            fl = clamp((t - ue(14)) / 0.3) * (1 - clamp((t - us(17)) / 0.4)) if goal else 0
            score_bug(d, clock, 0, 1 if goal else 0, flash=fl)
    # escena A: cronómetro gancho
    if scene == 'A':
        val = min(7.69, t / 6.3 * 7.69)
        stopwatch(d, W / 2, 760, val, 1.25, 'FASTEST PREMIER LEAGUE GOAL', glow=clamp((t - 6.3) / 0.3))
    if scene == 'B':
        k = clamp((t - us(4) + 0.2) / 0.4) * (1 - clamp((t - us(6) + 0.6) / 0.4))
        lower_third(d, 'VICARAGE ROAD', 'WATFORD  v  SOUTHAMPTON' if t > us(5) - 0.1 else 'WATFORD', k, 1180)
        if t < us(4):
            k2 = clamp((t - us(3)) / 0.3) * (1 - clamp((t - us(4) + 0.1) / 0.3))
            lower_third(d, '23 APRIL', 'TUESDAY NIGHT · 19:45 KICK-OFF', k2, 1180)
    if scene == 'C':
        # cronómetro pequeño del partido
        stopwatch(d, W - 220, 300, min(tg, 7.69), 0.62, 'SINCE KICK-OFF', glow=clamp((t - ue(14)) / 0.2))
        tags = [('ROBERTO PEREYRA', 37, us(6) + 0.5, us(6) + 2.6), ('CRAIG CATHCART', 15, us(6) + 2.9, ue(8)),
                ('SHANE LONG', 7, us(9) - 0.1, ue(9) + 0.5), ('BEN FOSTER', 26, us(12) + 0.6, ue(12))]
        for nm, num, a0, a1 in tags:
            al = clamp((t - a0) / 0.25) * (1 - clamp((t - a1) / 0.25))
            name_tag(d, labels.get(nm), nm.split()[-1], num, al)
        # flecha de telestrator: Long → Cathcart
        if us(9) <= t <= ue(9) + 0.4 and 'SHANE LONG' in labels and 'CRAIG CATHCART' in labels:
            pl = labels['SHANE LONG']; pc = labels['CRAIG CATHCART']
            al = 1 - clamp((t - ue(9)) / 0.4)
            tele_arrow(d, (pl[0], pl[1] + pl[2] * 1.05), (pc[0] + 30, pc[1] + pc[2] * 1.05), al, clamp((t - us(9)) / 0.9))
        if ue(14) <= t:
            k = clamp((t - ue(14)) / 0.15)
            text_c(d, (W / 2, 700), 'GOAL!', ANTON(220), YEL + (int(255 * k),), 12)
    if scene == 'D':
        d.rounded_rectangle([W - 260, 120, W - 46, 186], 10, fill=(205, 24, 38, 230))
        text_c(d, (W - 153, 154), 'REPLAY', BEBAS(54), (255, 255, 255, 255))
        if t >= us(15) + 0.4:
            k = ss((t - us(15) - 0.4) / 0.35)
            stopwatch(d, W / 2, 640, 7.69, lerp(1.6, 1.15, k), 'OFFICIAL TIME', glow=1.0)
        if t >= us(16):
            k = clamp((t - us(16)) / 0.3)
            d.rectangle([0, 840, W, 990], fill=(255, 214, 0, int(240 * k)))
            text_c(d, (W / 2, 916), 'NEW RECORD', ANTON(112), (12, 14, 26, int(255 * k)))
    if scene == 'E':
        k = clamp((t - us(17) - 2.0) / 0.4)
        lower_third(d, 'ON THE SPEAKERS', '"ROCKET MAN" STILL PLAYING', k, 1180)
    if scene == 'F':
        record_panel(d, t, 'F')
    if scene == 'G':
        if us(23) <= t < us(26):
            k = clamp((t - us(23)) / 0.3)
            d.rectangle([0, 520, W, 650], fill=(205, 24, 38, int(235 * k)))
            text_c(d, (W / 2, 586), 'THE TWIST', ANTON(100), (255, 255, 255, int(255 * k)))
        if t >= us(25) + 1.3:
            k = clamp((t - us(25) - 1.3) / 0.3)
            lower_third(d, "GRAY 90'", 'WATFORD EQUALISE', k, 1180)
        if t >= us(26):
            k = clamp((t - us(26)) / 0.25)
            d.rectangle([0, 700, W, 850], fill=(12, 14, 26, int(235 * k)))
            text_c(d, (W / 2, 776), 'FULL TIME  1 - 1', ANTON(104), YEL + (int(255 * k),))
    if scene == 'H':
        record_panel(d, t, 'H')
    if scene == 'I':
        val = max(0.0, t - us(28))
        stopwatch(d, W / 2, 620, val, 1.2, 'YOUR TIME')
        k = clamp((t - us(28)) / 0.3)
        f = ANTON(64)
        for i, ln in enumerate(['THE FASTEST GOAL IN', 'PREMIER LEAGUE HISTORY', 'TOOK LESS TIME THAN IT', 'TAKES TO READ THIS SENTENCE.']):
            text_c(d, (W / 2, 860 + i * 84), ln, f, (255, 255, 255, int(255 * k)), 5)
    if scene == 'J':
        closing(img, t); d = ImageDraw.Draw(img, 'RGBA')
    watermark(d)
    if with_subs: subtitles(d, t)
    return np.asarray(img.convert('RGB'))

def worker_init():
    init_resources()

def work(fi):
    return render_frame(fi).tobytes()

if __name__ == '__main__':
    out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else 'prem_lore_01.mp4'
    if '--test' in sys.argv:
        init_resources()
        ts = [float(x) for x in sys.argv[sys.argv.index('--test') + 1].split(',')]
        for t in ts:
            Image.fromarray(render_frame(int(t * FPS))).save(f'test_{t:05.1f}.jpg', quality=90)
        sys.exit()
    if '--cover' in sys.argv:
        init_resources()
        t = float(sys.argv[sys.argv.index('--cover') + 1])
        Image.fromarray(render_frame(int(t * FPS), with_subs=False)).save('prem_lore_01_portada.jpg', quality=95)
        sys.exit()
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                           '-i', '-', '-i', '/home/claude/prem/assets/voz.wav', '-af', 'apad', '-t', f'{DUR:.3f}',
                           '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p',
                           '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', out], stdin=subprocess.PIPE)
    with Pool(2, initializer=worker_init) as pool:
        for i, buf in enumerate(pool.imap(work, range(NF), chunksize=6)):
            ff.stdin.write(buf)
            if i % 150 == 0: print('frame', i, '/', NF, flush=True)
    ff.stdin.close(); ff.wait()
    print('done', out)
