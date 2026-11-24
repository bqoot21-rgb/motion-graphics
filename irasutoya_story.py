#!/usr/bin/env python3
"""Story-style irasutoya short (~22s, 1080x1920): full-bleed backgrounds, camera
moves, layered props with labels, word-synced motion, whip-pan transitions,
colour grade, synthesized SFX + BGM.

usage: python3 irasutoya_story.py ASSET_DIR TTS_DIR OUT.mp4
  TTS_DIR holds 0.mp3..N.mp3 and words.json {"lines": [...], "words": [[[s, e, w], ...], ...]}
"""
import json, math, os, subprocess, sys, tempfile, wave
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
FB = "/usr/share/fonts/truetype/nanum/NanumSquareRoundB.ttf"
FX = "/usr/share/fonts/truetype/nanum/NanumSquareB.ttf"
YELLOW = (255, 214, 0)
RED = (232, 52, 52)

ASSETS, TTS, OUT = sys.argv[1:4]
_j = json.load(open(os.path.join(TTS, "words.json")))
LINES, WORDS = _j["lines"], _j["words"]

LEAD, TAIL, OUTRO, XF = 0.12, 0.22, 0.9, 0.32
STARTS, DUR = [], []
_t = 0.0
for k, ws in enumerate(WORDS):
    STARTS.append(_t)
    DUR.append(LEAD + ws[-1][1] + TAIL + (OUTRO if k == len(WORDS) - 1 else 0))
    _t += DUR[-1]
TOTAL = _t
NFRAMES = int(round(TOTAL * FPS))


def wt(k, i, end=False):
    return LEAD + WORDS[k][i][1 if end else 0]


# ---------------- easing ----------------
def cl(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def eo(x):
    x = cl(x)
    return 1 - (1 - x) ** 3


def eio(x):
    x = cl(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def eback(x, s=1.9):
    x = cl(x)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def spring(x, f=2.0, d=5.0):
    return 0.0 if x <= 0 else 1 - math.exp(-d * x) * math.cos(2 * math.pi * f * x)


def lerp(a, b, x):
    return a + (b - a) * x


# ---------------- assets ----------------
def load(n):
    return Image.open(os.path.join(ASSETS, n)).convert("RGBA")


SPR = {
    "woman_fist": load("yaruki_aru_casual_woman.png"),
    "woman_sigh": load("mukiryoku_woman.png"),
    "woman_tempt": load("gaman_okashi.png"),
    "woman_burger": load("syokuji_hamburger_girl.png"),
    "woman_scale": load("taijukei4_himan_woman.png"),
    "woman_snack": load("jisyuku_futoru_woman.png"),
    "fridge": load("reizouko_akeppanashi.png"),
    "clock": load("kakedokei.png"),
    "calendar": load("calender_himekuri.png"),
    "chicken": load("food_fried_chicken.png"),
    "toppogi": load("food_toppogi.png"),
    "ramen": load("food_instant_fukuro_ra-men.png"),
    "wing": load("tenshi_wing1.png"),
    "burst": load("syuchusen1.png"),
}
BGS = {
    "living": load("big_bg_house_living.jpg"),
    "night": load("big_bg_moon_sky_mangetsu_building.jpg"),
    "kitchen": load("big_bg_house_kitchen.jpg"),
    "speed": load("bg_koukasen_color1.png"),
}
# soft depth-of-field on backgrounds so the foreground characters read first
BGS = {k: v.filter(ImageFilter.GaussianBlur(2.2 if k != "speed" else 0)) for k, v in BGS.items()}

_fonts = {}


def font(sz, f=FB):
    if (sz, f) not in _fonts:
        _fonts[(sz, f)] = ImageFont.truetype(f, sz)
    return _fonts[(sz, f)]


# vignette + grain (precomputed)
_yy, _xx = np.mgrid[0:H, 0:W]
_r = np.sqrt(((_xx - W / 2) / (W * 0.72)) ** 2 + ((_yy - H / 2) / (H * 0.62)) ** 2)
VIG = np.clip((_r - 0.55) / 0.6, 0, 1)[..., None] ** 1.6
_rng = np.random.RandomState(7)
GRAIN = [(_rng.randn(H // 2, W // 2) * 5).repeat(2, 0).repeat(2, 1)[..., None] for _ in range(6)]


# ---------------- camera & drawing ----------------
class Cam:
    def __init__(self, z=1.0, cx=540, cy=960, rot=0.0, dx=0.0, dy=0.0):
        self.z, self.cx, self.cy, self.dx, self.dy = z, cx, cy, dx, dy

    def pt(self, x, y):
        return (x - self.cx) * self.z + W / 2 + self.dx, (y - self.cy) * self.z + H / 2 + self.dy


def draw_bg(name, cam, pan=0.0, parallax=0.55, darken=0.0):
    """Cover-fit the 16:9 background to the frame height; pan in world px."""
    src = BGS[name]
    z = 1 + (cam.z - 1) * parallax
    hw = H * 1.04
    s = z * hw / src.height
    ww = src.width * s
    left = W / 2 - ww / 2 + pan * z + cam.dx * parallax
    top = H / 2 - hw * z / 2 + (cam.cy - 960) * -0.3 + cam.dy * parallax
    im = src.transform((W, H), Image.AFFINE, (1 / s, 0, -left / s, 0, 1 / s, -top / s), resample=Image.BILINEAR)
    if darken:
        im = Image.blend(im, Image.new("RGBA", (W, H), (0, 0, 0, 255)), darken)
    return im


def place(c, cam, name, x, y, h, sc=1.0, rot=0.0, alpha=1.0, anchor="bottom", flip=False, shadow=False):
    if sc <= 0.01 or alpha <= 0.01:
        return None
    src = SPR[name]
    hh = max(2, int(h * sc * cam.z))
    ww = max(2, int(src.width * hh / src.height))
    im = src.resize((ww, hh), Image.LANCZOS)
    if flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    if rot:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 1:
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    sx, sy = cam.pt(x, y)
    if shadow:
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        r = ww * 0.4
        ImageDraw.Draw(sh).ellipse([sx - r, sy - 22 * cam.z, sx + r, sy + 18 * cam.z], fill=(0, 0, 0, int(70 * alpha)))
        c.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
    px = int(sx - im.width / 2)
    py = int(sy - im.height) if anchor == "bottom" else int(sy - im.height / 2)
    c.alpha_composite(im, (px, py))
    return sx, sy, ww, hh


def winged(c, cam, name, x, y, h, t, sc=1.0, rot=0.0):
    """Sprite with two flapping wings (like irasutoya's flying money)."""
    if sc <= 0.01:
        return
    flap = math.sin(t * 22) * 22
    wh = h * 0.42
    src = SPR[name]
    wdt = src.width * h / src.height
    for side in (-1, 1):
        ang = (flap + 8) * side + rot
        ox = side * wdt * 0.48 * sc
        place(c, cam, "wing", x + ox, y - h * 0.15 * sc, wh, sc, rot=ang, anchor="center", flip=(side == 1))
    place(c, cam, name, x, y, h, sc, rot=rot, anchor="center")


def label(c, s, x, y, sz, fg=(40, 30, 20), bg=(255, 246, 220), rot=0.0, sc=1.0, alpha=1.0, pad=(26, 14),
          border=(60, 45, 30)):
    """Paper tag with Korean text (text living on objects, not only captions)."""
    if sc <= 0.02 or alpha <= 0.02:
        return
    f = font(sz)
    d0 = ImageDraw.Draw(c)
    l, t, r, b = d0.textbbox((0, 0), s, font=f)
    tw, th = r - l + pad[0] * 2, b - t + pad[1] * 2
    lay = Image.new("RGBA", (tw + 20, th + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([10, 10, 10 + tw, 10 + th], radius=14, fill=bg, outline=border, width=5)
    d.text((10 + pad[0] - l, 10 + pad[1] - t), s, font=f, fill=fg)
    lay = lay.resize((max(1, int(lay.width * sc)), max(1, int(lay.height * sc))), Image.LANCZOS)
    if rot:
        lay = lay.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 1:
        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * alpha)))
    c.alpha_composite(lay, (int(x - lay.width / 2), int(y - lay.height / 2)))


def bigtext(c, s, x, y, sz, fill, t0, t, rot=0.0, stroke=14, sfill=(255, 255, 255), wobble=0.0, f=FB):
    p = (t - t0) / 0.4
    if p <= 0:
        return
    sc = eback(p, 2.8)
    fnt = font(sz, f)
    l, tt, r, b = ImageDraw.Draw(c).textbbox((0, 0), s, font=fnt, stroke_width=stroke)
    lay = Image.new("RGBA", (r - l + 40, b - tt + 40), (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((20 - l, 20 - tt), s, font=fnt, fill=fill, stroke_width=stroke, stroke_fill=sfill)
    lay = lay.resize((max(1, int(lay.width * sc)), max(1, int(lay.height * sc))), Image.LANCZOS)
    rr = rot + wobble * math.sin(t * 9)
    if rr:
        lay = lay.rotate(rr, resample=Image.BICUBIC, expand=True)
    c.alpha_composite(lay, (int(x - lay.width / 2), int(y - lay.height / 2)))


def wavy_text(c, s, x, y, sz, fill, t0, t, amp=14):
    """Per-glyph wave + pop (for sound effects like 꼬르륵)."""
    if t < t0:
        return
    d = ImageDraw.Draw(c)
    f = font(sz)
    widths = [d.textlength(ch, font=f) for ch in s]
    tot = sum(widths)
    cx = x - tot / 2
    for i, ch in enumerate(s):
        p = eback((t - t0 - i * 0.06) / 0.35, 2.5)
        if p <= 0:
            cx += widths[i]
            continue
        yy = y + amp * math.sin(t * 10 - i * 0.9)
        g = Image.new("RGBA", (int(widths[i] + 60), sz + 60), (0, 0, 0, 0))
        ImageDraw.Draw(g).text((30, 20), ch, font=f, fill=fill, stroke_width=10, stroke_fill=(255, 255, 255))
        g = g.resize((max(1, int(g.width * p)), max(1, int(g.height * p))), Image.LANCZOS)
        g = g.rotate(8 * math.sin(t * 7 + i), resample=Image.BICUBIC, expand=True)
        c.alpha_composite(g, (int(cx + widths[i] / 2 - g.width / 2), int(yy - g.height / 2)))
        cx += widths[i]


def burst(c, x, y, size, t, alpha=1.0, color=(255, 255, 255)):
    """Manga focus-lines burst (irasutoya syuchusen), tinted & spinning."""
    src = SPR["burst"]
    s = int(size)
    im = src.resize((s, s), Image.BILINEAR).rotate(t * 25, resample=Image.BICUBIC)
    col = Image.new("RGBA", im.size, color + (0,))
    col.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    c.alpha_composite(col, (int(x - s / 2), int(y - s / 2)))


def subtitle(c, k, t):
    ws = WORDS[k]
    toks = LINES[k].replace("...", "…").split(" ")
    if len(toks) != len(ws):  # fall back to TTS tokens if punctuation split differs
        toks = [w[2] for w in ws]
    f = font(70)
    d = ImageDraw.Draw(c)
    sp = 20
    wid = [d.textlength(x, font=f) for x in toks]
    rows, cur, cw = [], [], 0
    for i, w_ in enumerate(wid):
        if cur and cw + sp + w_ > 940:
            rows.append(cur)
            cur, cw = [], 0
        cw += (sp if cur else 0) + w_
        cur.append(i)
    rows.append(cur)
    p = eo((t - 0.02) / 0.2)
    if p <= 0:
        return
    y0 = 1630 - (len(rows) - 1) * 96
    for ri, row in enumerate(rows):
        rw = sum(wid[i] for i in row) + sp * (len(row) - 1)
        x = W / 2 - rw / 2
        y = y0 + ri * 96 + (1 - p) * 30
        for i in row:
            s0, s1 = LEAD + ws[i][0], LEAD + ws[i][1]
            on = s0 <= t < s1 + 0.06
            col = YELLOW if on else (255, 255, 255)
            lift = 8 * math.sin(cl((t - s0) / 0.22) * math.pi) if on else 0
            d.text((x, y - lift), toks[i], font=f, fill=col + (int(255 * p),), stroke_width=11,
                   stroke_fill=(25, 25, 30, int(255 * p)))
            x += wid[i] + sp


# ---------------- scenes ----------------
def s0(t):  # New year's resolution — living room, day
    cam = Cam(z=lerp(1.0, 1.12, eio(t / DUR[0])), cy=lerp(980, 940, eio(t / DUR[0])))
    c = draw_bg("living", cam, pan=lerp(260, 120, eio(t / DUR[0])))
    # torn-off calendar page "1" flutters onto the scene
    cp = spring((t - 0.05) / 1.1, 1.6, 5)
    place(c, cam, "calendar", 210, 330, 250, sc=cp, rot=6 * math.sin(t * 2.4), anchor="center")
    label(c, "1월 1일", *cam.pt(210, 480), 44, sc=eback((t - 0.35) / 0.4), rot=-4)
    # resolution banner drops & swings at "진짜"
    tb = wt(0, 3) - 0.1
    bp = (t - tb)
    if bp > 0:
        drop = eback(bp / 0.45, 1.4)
        sw = 7 * math.exp(-bp * 2.2) * math.sin(bp * 9)
        lay = Image.new("RGBA", (680, 260), (0, 0, 0, 0))
        dd = ImageDraw.Draw(lay)
        dd.line([120, 0, 120, 70], fill=(90, 70, 50), width=6)
        dd.line([560, 0, 560, 70], fill=(90, 70, 50), width=6)
        dd.rounded_rectangle([20, 60, 660, 240], radius=18, fill=(255, 250, 238), outline=(200, 40, 40), width=10)
        f = font(96)
        s = "올해는 진짜!"
        l, tt, r, b = dd.textbbox((0, 0), s, font=f)
        dd.text((340 - (r - l) / 2 - l, 150 - (b - tt) / 2 - tt), s, font=f, fill=RED)
        lay = lay.rotate(sw, resample=Image.BICUBIC, expand=True, center=(340, 0))
        sx, sy = cam.pt(640, -260 + 520 * drop)
        c.alpha_composite(lay, (int(sx - lay.width / 2), int(sy)))
    # heroine pops in, pumping fists
    td = wt(0, 6)
    ent = spring((t - 0.1) / 1.0, 1.8, 5)
    pump = 14 * abs(math.sin(t * 6)) * cl((t - td) * 3)
    if t > td:
        burst(c, *cam.pt(540, 1050), 1100 * eback((t - td) / 0.35), t, 0.8, (255, 240, 150))
    place(c, cam, "woman_fist", 540, 1640 - pump, 940, sc=ent, shadow=True)
    subtitle(c, 0, t)
    return c, (255, 225, 190), 0.10


def s1(t):  # 11 p.m., stomach growls — night
    cam = Cam(z=lerp(1.05, 1.18, eio(t / DUR[1])))
    tg = wt(1, 5)
    if t > tg:  # growl rumble
        a = 7 * math.exp(-(t - tg) * 2)
        cam.dx, cam.dy = a * math.sin(t * 70), a * math.cos(t * 55)
    c = draw_bg("night", cam, pan=lerp(-150, 0, eio(t / DUR[1])), darken=0.05)
    # pendulum clock swings; pulses at "열한 시"
    t11 = wt(1, 2)
    pul = 1 + 0.18 * math.exp(-max(0, t - t11) * 4) * (t > t11)
    place(c, cam, "clock", 540, 560, 520, sc=eback((t - 0.05) / 0.5) * pul, rot=5 * math.sin(t * 3.2),
          anchor="center")
    if t > t11:
        label(c, "PM 11:00", *cam.pt(540, 880), 64, fg=(255, 230, 120), bg=(30, 40, 70), border=(255, 230, 120),
              sc=eback((t - t11) / 0.35))
    # sad heroine curled up
    ent = eo((t - 0.05) / 0.5)
    sq = 1 + 0.03 * math.sin(t * 2.5)
    place(c, cam, "woman_sigh", 540, 1760 + (1 - ent) * 300, 880 * sq, shadow=True)
    wavy_text(c, "꼬르륵~", *cam.pt(760, 1260), 110, (255, 160, 60), tg - 0.05, t)
    subtitle(c, 1, t)
    return c, (60, 90, 170), 0.22


FOODS = [("chicken", 0, 330, -1), ("toppogi", 1, 380, 0), ("ramen", 2, 360, 1)]


def s2(t):  # Winged food flies out of the fridge
    cam = Cam(z=lerp(1.0, 1.1, eio(t / DUR[2])), cy=960)
    c = draw_bg("kitchen", cam, pan=lerp(-420, -560, eio(t / DUR[2])))
    # glowing fridge
    fx, fy = 540, 760
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gp = 0.75 + 0.25 * math.sin(t * 5)
    sx, sy = cam.pt(fx, fy)
    for r, a in [(560, 40), (420, 60), (280, 90)]:
        ImageDraw.Draw(glow).ellipse([sx - r, sy - r, sx + r, sy + r], fill=(255, 250, 200, int(a * gp)))
    c.alpha_composite(glow.filter(ImageFilter.GaussianBlur(60)))
    place(c, cam, "fridge", fx, fy, 560, sc=eback((t - 0.02) / 0.5), anchor="center")
    # foods launch at their words, then swoop toward the heroine at "부르네요"
    tcall = wt(2, 6)
    for name, wi, hgt, side in FOODS:
        t0 = wt(2, wi)
        p = (t - t0)
        if p <= 0:
            continue
        rise = eo(p / 0.7)
        hx = fx + side * 330 * rise + 30 * math.sin(t * 3 + wi)
        hy = fy - 120 - [300, 400, 320][wi] * rise + 24 * math.sin(t * 4 + wi * 2)
        if t > tcall:  # swoop down toward her face
            q = eio((t - tcall) / 0.9)
            hx = lerp(hx, 560 + side * 200, q)
            hy = lerp(hy, 1100 - wi * 60, q)
        sc = eback(p / 0.45) * (1 - 0.25 * cl((t - tcall) / 0.9))
        winged(c, cam, name, hx, hy, hgt * 0.8, t + wi, sc=sc, rot=8 * math.sin(t * 3 + wi))
        lx, ly = cam.pt(hx, hy + hgt * 0.42 * sc + 30)
        label(c, ["치킨", "떡볶이", "라면"][wi], lx, ly, 46, sc=eback((p - 0.1) / 0.4) * sc, rot=side * -5)
    # tempted heroine in the foreground (bottom-left, cropped)
    tw = 6 * math.sin(t * 30) * cl((t - tcall) * 2) * 0.4
    place(c, cam, "woman_tempt", 800 + tw, 1800, 900, sc=eo((t - 0.1) / 0.5), shadow=False)
    if t > tcall:
        label(c, "이리 와~♥", *cam.pt(300, 1130), 54, fg=(220, 40, 90), bg=(255, 235, 242), border=(220, 40, 90),
              sc=eback((t - tcall) / 0.35), rot=-6)
    subtitle(c, 2, t)
    return c, (255, 230, 170), 0.08


def s3(t):  # "Just one bite..." — speed lines, then TV-off blackout
    tm = wt(3, 4)
    zoom = lerp(1.0, 1.25, eio(t / 2.0))
    cam = Cam(z=zoom)
    a = 9 if t < tm else 3
    cam.dx, cam.dy = a * math.sin(t * 47), a * math.cos(t * 61)
    c = draw_bg("speed", cam, parallax=1.0)
    c.alpha_composite(Image.new("RGBA", (W, H), (255, 170, 60, 70)))
    burst(c, W / 2, 900, 1900, t, 0.55, (255, 255, 255))
    # foods get sucked into her mouth one after another
    mouth = (560, 1000)
    for i, (name, _, hgt, side) in enumerate(FOODS * 2):
        t0 = 0.15 + i * 0.22
        p = (t - t0) / 0.5
        if 0 < p < 1:
            ang = i * 1.9
            r = 700 * (1 - eio(p))
            x = mouth[0] + r * math.cos(ang)
            y = mouth[1] + r * math.sin(ang) * 0.8
            place(c, cam, name, x, y, hgt * 0.7, sc=1 - 0.7 * p, rot=p * 400, anchor="center")
    chomp = 1 + 0.04 * math.sin(t * 28)
    place(c, cam, "woman_burger", 540, 1840, 1250 * chomp, sc=eback((t - 0.0) / 0.4))
    wavy_text(c, "냠냠냠!", *cam.pt(540, 380), 140, RED, wt(3, 1), t, amp=10)
    subtitle(c, 3, t)
    # "last memory": CRT switch-off
    off = (t - wt(3, 5, end=True) + 0.15) / 0.35
    if off > 0:
        arr = np.asarray(c).copy()
        hgt = int(H * (1 - eio(off)) + 6)
        sq = Image.fromarray(arr).resize((W, max(6, hgt)), Image.BILINEAR)
        c = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        c.alpha_composite(sq, (0, (H - sq.height) // 2))
        if off > 0.8:
            c.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * cl((off - 0.8) / 0.2)))))
    return c, (255, 200, 140), 0.0


def lcd(c, x, y, val, t, alarm):
    lay = Image.new("RGBA", (560, 230), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([0, 0, 559, 229], radius=36, fill=(250, 250, 250), outline=(60, 60, 70), width=10)
    on = alarm and int(t * 8) % 2 == 0
    d.rounded_rectangle([30, 30, 529, 199], radius=20, fill=(255, 90, 90) if on else (170, 210, 160))
    f = font(130, FX)
    s = f"{val:5.1f}"
    l, tt, r, b = d.textbbox((0, 0), s, font=f)
    d.text((400 - (r - l) - l, 115 - (b - tt) / 2 - tt), s, font=f, fill=(30, 40, 30))
    d.text((415, 110), "kg", font=font(60, FX), fill=(30, 40, 30))
    c.alpha_composite(lay, (int(x - 280), int(y - 115)))


def s4(t):  # The scale screams
    ts = wt(4, 4)
    punch = 1 + 0.12 * eback((t - ts) / 0.25) if t > ts else 1
    cam = Cam(z=lerp(1.0, 1.06, eio(t / DUR[4])) * punch, cy=lerp(900, 980, eio(t / DUR[4])))
    if t > ts:
        a = 14 * math.exp(-(t - ts) * 3)
        cam.dx, cam.dy = a * math.sin(t * 80), a * math.cos(t * 63)
    c = draw_bg("living", cam, pan=lerp(-300, -200, eio(t / DUR[4])))
    if t > ts:
        c.alpha_composite(Image.new("RGBA", (W, H), (255, 40, 40, int(70 * (0.5 + 0.5 * math.sin(t * 25))))))
        burst(c, *cam.pt(540, 1100), 1700, t, 0.8, (255, 255, 255))
    place(c, cam, "woman_scale", 540, 1720, 1050, sc=eo((t - 0.0) / 0.4), shadow=True)
    # LCD counter climbs, then alarms
    tc = wt(4, 3)
    v = 52.0 + 6.7 * eio((t - tc) / (ts - tc + 0.1))
    lx, ly = cam.pt(540, 470)
    if t > 0.15:
        lcd(c, lx, ly + (1 - eback((t - 0.15) / 0.4)) * -400, v, t, t > ts)
    bigtext(c, "삐빅!!", *cam.pt(820, 260), 130, RED, ts, t, rot=12, wobble=4)
    bigtext(c, "+6.7kg", *cam.pt(250, 700), 100, RED, ts + 0.2, t, rot=-8)
    subtitle(c, 4, t)
    return c, (255, 240, 215), 0.06


def s5(t):  # Punchline
    cam = Cam(z=lerp(1.12, 1.0, eio(t / 1.2)))
    c = draw_bg("living", cam, pan=lerp(320, 420, eio(t / DUR[5])))
    tr = wt(5, 2)
    place(c, cam, "woman_snack", 540, 1640, 980, sc=eo((t - 0.0) / 0.4), shadow=True)
    # resolution note
    if t > tr - 0.1:
        label(c, "다이어트 결심 ×2", *cam.pt(540, 300), 64, sc=eback((t - tr + 0.1) / 0.4), rot=-3)
    tm = wt(5, 4)
    if t > tm:
        # red stamp slam
        p = cl((t - tm) / 0.18)
        sc = lerp(2.4, 1.0, eo(p))
        lay = Image.new("RGBA", (900, 300), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        d.rounded_rectangle([10, 10, 890, 290], radius=30, outline=RED + (235,), width=16)
        f = font(150)
        s = "내일부터!"
        l, tt, r, b = d.textbbox((0, 0), s, font=f)
        d.text((450 - (r - l) / 2 - l, 150 - (b - tt) / 2 - tt), s, font=f, fill=RED + (235,))
        lay = lay.resize((int(900 * sc), int(300 * sc)), Image.LANCZOS).rotate(-8, resample=Image.BICUBIC,
                                                                              expand=True)
        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * cl(p * 2))))
        c.alpha_composite(lay, (int(W / 2 - lay.width / 2), int(560 - lay.height / 2)))
        if p >= 1:
            sh = 10 * math.exp(-(t - tm - 0.18) * 8)
            c = c.transform(c.size, Image.AFFINE, (1, 0, sh * math.sin(t * 90), 0, 1, 0))
    subtitle(c, 5, t)
    fo = cl((t - (DUR[5] - 0.4)) / 0.4)
    if fo > 0:
        c.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * fo))))
    return c, (255, 225, 190), 0.08


SCENES = [s0, s1, s2, s3, s4, s5]


def grade(img, tint, amt, fi):
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    if amt:
        a = a * (1 - amt) + (a * np.array(tint, np.float32) / 255.0) * amt * 1.0 + np.array(tint) * amt * 0.0
    a = a * (1 - 0.55 * VIG)
    a += GRAIN[fi % len(GRAIN)]
    return np.clip(a, 0, 255).astype(np.uint8)


def hblur(arr, r):
    if r < 1:
        return arr
    r = int(r)
    cs = np.cumsum(np.pad(arr.astype(np.int32), ((0, 0), (r + 1, r), (0, 0)), mode="edge"), axis=1)
    return ((cs[:, 2 * r + 1:] - cs[:, :-2 * r - 1]) / (2 * r + 1)).astype(np.uint8)


def scene_frame(k, t, fi):
    img, tint, amt = SCENES[k](t)
    return grade(img, tint, amt, fi)


def render(fi):
    t = fi / FPS
    k = max(i for i, s in enumerate(STARTS) if s <= t + 1e-9)
    lt = t - STARTS[k]
    # whip-pan: last XF/2 of previous scene slides out left, next slides in from right
    if k > 0 and lt < XF / 2 and k != 4:
        p = 0.5 + lt / XF  # 0.5..1
        a = scene_frame(k - 1, t - STARTS[k - 1], fi)
        b = scene_frame(k, lt, fi)
    elif k < len(SCENES) - 1 and DUR[k] - lt < XF / 2 and k + 1 != 4:
        p = 0.5 - (DUR[k] - lt) / XF  # 0..0.5
        a = scene_frame(k, lt, fi)
        b = scene_frame(k + 1, 0.0, fi)
    else:
        return scene_frame(k, lt, fi)
    e = eio(p)
    off = int(e * W)
    out = np.concatenate([a, b], axis=1)[:, off:off + W]
    blur = 60 * math.sin(math.pi * p)
    return hblur(out, blur)


# ---------------- audio ----------------
SR = 44100


def synth():
    n = int((TOTAL + 1) * SR)
    sfx, mus = np.zeros(n), np.zeros(n)

    def add(buf, at, sig):
        i = int(at * SR)
        if i < n:
            buf[i:i + len(sig)] += sig[: n - i]

    tt = lambda d: np.arange(int(d * SR)) / SR

    def pop(f0=800, d=0.12, g=0.25):
        x = tt(d)
        f = f0 * np.exp(-x * 18) + f0 * 0.5
        return g * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 30)

    def whoosh(d=0.35, g=0.22):
        x = np.random.RandomState(3).randn(int(d * SR))
        y = np.convolve(x, np.ones(25) / 25, "same")
        return g * 3 * y * np.sin(np.linspace(0, np.pi, len(y))) ** 2

    def ding(f0=1320, g=0.15, d=0.8):
        x = tt(d)
        return g * (np.sin(2 * np.pi * f0 * x) + 0.4 * np.sin(2 * np.pi * f0 * 2.01 * x)) * np.exp(-x * 5)

    def growl(d=0.9, g=0.35):
        x = tt(d)
        f = 70 + 25 * np.sin(2 * np.pi * 7 * x) + 30 * np.sin(2 * np.pi * 2.3 * x)
        s = np.sin(2 * np.pi * np.cumsum(f) / SR)
        s = np.tanh(3 * s)
        return g * s * np.sin(np.pi * x / d)

    def flap(g=0.12):
        out = np.zeros(int(0.5 * SR))
        rng = np.random.RandomState(5)
        for j in range(5):
            b = rng.randn(int(0.04 * SR)) * np.exp(-np.arange(int(0.04 * SR)) / SR * 80)
            i = int(j * 0.09 * SR)
            out[i:i + len(b)] += b
        return g * np.convolve(out, np.ones(8) / 8, "same")

    def beep(f=2400, d=0.09, g=0.16):
        x = tt(d)
        return g * np.sign(np.sin(2 * np.pi * f * x)) * 0.5

    def thud(g=0.6):
        x = tt(0.35)
        return g * np.sin(2 * np.pi * (55 + 90 * np.exp(-x * 25)) * x) * np.exp(-x * 9)

    def chomp(g=0.18):
        x = np.random.RandomState(9).randn(int(0.07 * SR))
        return g * np.convolve(x, np.ones(4) / 4, "same") * np.exp(-np.arange(len(x)) / SR * 50)

    def tvoff(g=0.25):
        x = tt(0.35)
        return g * np.sin(2 * np.pi * np.cumsum(1800 * np.exp(-x * 9) + 60) / SR) * np.exp(-x * 4)

    S = STARTS
    for k in range(1, len(S)):
        if k != 4:
            add(sfx, S[k] - XF / 2, whoosh())
    add(sfx, S[0] + 0.1, pop(700))
    add(sfx, S[0] + wt(0, 3), pop(400, 0.2, 0.3))
    add(sfx, S[0] + wt(0, 6), ding(1568))
    add(sfx, S[1] + wt(1, 2), ding(880, 0.18, 1.2))
    add(sfx, S[1] + wt(1, 5), growl())
    for i in range(3):
        add(sfx, S[2] + wt(2, i), pop(600 + 200 * i, 0.12, 0.2))
        add(sfx, S[2] + wt(2, i) + 0.05, flap())
    add(sfx, S[2] + wt(2, 6), whoosh(0.6, 0.15))
    for j in range(int(wt(3, 5, True) / 0.16)):
        add(sfx, S[3] + 0.15 + j * 0.16, chomp())
    add(sfx, S[3] + wt(3, 5, True) - 0.15, tvoff())
    for j in range(6):
        add(sfx, S[4] + wt(4, 3) + j * 0.08, beep(1800 + 120 * j, 0.04, 0.08))
    for j in range(8):
        add(sfx, S[4] + wt(4, 4) + j * 0.14, beep(2600, 0.09, 0.14))
    add(sfx, S[5] + wt(5, 4), thud())
    add(sfx, S[5] + wt(5, 4) + 0.05, ding(1046, 0.12))

    # light pizzicato BGM loop (C–Am–F–G), ducked under the voice later
    bpm = 118
    beat = 60 / bpm
    chords = [[60, 64, 67], [57, 60, 64], [53, 57, 60], [55, 59, 62]]
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)

    def pluck(f, d=0.35, g=0.06):
        x = tt(d)
        return g * (np.sin(2 * np.pi * f * x) + 0.3 * np.sin(2 * np.pi * 2 * f * x)) * np.exp(-x * 9)

    b = 0
    while b * beat < S[3] or (S[4] <= b * beat < TOTAL - 0.4):
        if S[3] <= b * beat < S[4]:  # music drops out for the binge/blackout gag
            b += 1
            continue
        ch = chords[(b // 4) % 4]
        at = b * beat
        add(mus, at, pluck(hz(ch[0] - 12), 0.5, 0.09))
        if b % 2 == 1:
            for m in ch:
                add(mus, at, pluck(hz(m + 12), 0.25, 0.035))
        add(mus, at + beat / 2, pluck(hz(ch[(b % 3)] + 12), 0.2, 0.03))
        b += 1
    return sfx, mus


def write_wav(path, x):
    x = np.clip(x, -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def main():
    tmp = tempfile.mkdtemp()
    sfx, mus = synth()
    write_wav(os.path.join(tmp, "sfx.wav"), sfx)
    write_wav(os.path.join(tmp, "mus.wav"), mus)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                           "-crf", "18", "-pix_fmt", "yuv420p", os.path.join(tmp, "v.mp4")], stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for i, fr in enumerate(pool.imap(render, range(NFRAMES), chunksize=3)):
            ff.stdin.write(fr.tobytes())
            if i % 90 == 0:
                print(f"frame {i}/{NFRAMES}", flush=True)
    ff.stdin.close()
    ff.wait()
    ins, flt = [], []
    n = len(WORDS)
    for k in range(n):
        ins += ["-i", os.path.join(TTS, f"{k}.mp3")]
        ms = int((STARTS[k] + LEAD) * 1000)
        flt.append(f"[{k + 1}:a]aresample=44100,adelay={ms}|{ms}[v{k}]")
    flt.append("".join(f"[v{k}]" for k in range(n)) + f"amix=inputs={n}:normalize=0,asplit[voice][key]")
    flt.append(f"[{n + 2}:a]volume=1.0[m0];[m0][key]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=300[mus]")
    flt.append(f"[voice][{n + 1}:a][mus]amix=inputs=3:normalize=0,loudnorm=I=-14:TP=-1.5[aout]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(tmp, "v.mp4"), *ins,
                    "-i", os.path.join(tmp, "sfx.wav"), "-i", os.path.join(tmp, "mus.wav"),
                    "-filter_complex", ";".join(flt), "-map", "0:v", "-map", "[aout]", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", OUT], check=True)
    print("done", OUT, f"{TOTAL:.2f}s")


if __name__ == "__main__":
    main()
