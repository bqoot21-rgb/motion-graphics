#!/usr/bin/env python3
"""20-second vertical explainer: irasutoya illustrations + AI voice, with motion
synced to word timings from Edge TTS.

usage: python3 irasutoya_explainer.py ASSET_DIR TTS_DIR OUT.mp4
  ASSET_DIR: tired.png thirsty.png body.png drink.png glass.png genki.png
  TTS_DIR:   0.mp3 .. 4.mp3 + words.json  (list of [start, end, word] per line)
"""
import json, math, os, subprocess, sys, tempfile, wave
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
FB = "/usr/share/fonts/truetype/nanum/NanumSquareRoundB.ttf"
FR = "/usr/share/fonts/truetype/nanum/NanumSquareRoundR.ttf"
INK = (34, 40, 58)
MUTED = (160, 168, 186)
WATER = (64, 156, 255)

ASSETS, TTS, OUT = sys.argv[1:4]
WORDS = json.load(open(os.path.join(TTS, "words.json")))
LINES = [
    "오후만 되면, 머리가 멍하고 피곤하신가요?",
    "어쩌면 그 이유는, 물 부족일지도 몰라요.",
    "우리 몸의 약 60퍼센트는 물로 이루어져 있거든요.",
    "하루 여덟 잔, 조금씩 자주 마셔 보세요.",
    "작은 습관 하나가, 하루를 바꿉니다.",
]
BG = [(226, 232, 244), (255, 236, 222), (222, 240, 255), (224, 247, 238), (255, 243, 196)]
DECO = [(205, 214, 232), (255, 214, 192), (196, 224, 252), (196, 238, 220), (255, 226, 140)]

# ---------- timeline ----------
LEAD, TAIL, OUTRO = 0.25, 0.5, 0.9
STARTS, AUDIO_AT, DUR = [], [], []
t = 0.0
for k, ws in enumerate(WORDS):
    STARTS.append(t)
    AUDIO_AT.append(t + LEAD)
    d = LEAD + ws[-1][1] + TAIL + (OUTRO if k == len(WORDS) - 1 else 0)
    DUR.append(d)
    t += d
TOTAL = t
NFRAMES = int(round(TOTAL * FPS))
TRANS = 0.42


def word_t(k, i):
    """scene-local time when word i of line k starts."""
    return LEAD + WORDS[k][i][0]


# ---------- easing ----------
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def e_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def e_inout(x):
    x = clamp(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def e_back(x, s=1.9):
    x = clamp(x)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def spring(x, f=2.2, damp=5.5):
    if x <= 0:
        return 0.0
    return 1 - math.exp(-damp * x) * math.cos(2 * math.pi * f * x)


# ---------- assets ----------
_fonts = {}


def font(sz, bold=True):
    key = (sz, bold)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(FB if bold else FR, sz)
    return _fonts[key]


SPR = {n: Image.open(os.path.join(ASSETS, n + ".png")).convert("RGBA")
       for n in ["tired", "thirsty", "body", "drink", "glass", "genki"]}


def place(canvas, name, cx, cy, height, scale=1.0, rot=0.0, alpha=1.0, anchor="bottom", shadow=True):
    """Paste sprite with its bottom-centre (or centre) at (cx, cy)."""
    if scale <= 0.01 or alpha <= 0.01:
        return
    src = SPR[name]
    h = max(2, int(height * scale))
    w = max(2, int(src.width * h / src.height))
    im = src.resize((w, h), Image.LANCZOS)
    if rot:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 1:
        a = im.getchannel("A").point(lambda v: int(v * alpha))
        im.putalpha(a)
    if shadow and anchor == "bottom":
        sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        sw = w * 0.42
        ImageDraw.Draw(sh).ellipse([cx - sw, cy - 16 * scale, cx + sw, cy + 16 * scale],
                                   fill=(20, 30, 60, int(40 * alpha)))
        canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
    x = int(cx - im.width / 2)
    y = int(cy - im.height) if anchor == "bottom" else int(cy - im.height / 2)
    canvas.alpha_composite(im, (x, y))


def background(k, lt):
    c = Image.new("RGBA", (W, H), BG[k] + (255,))
    d = ImageDraw.Draw(c)
    rng = np.random.RandomState(k * 7 + 3)
    for j in range(7):
        bx, by = rng.uniform(0, W), rng.uniform(0, H)
        r = rng.uniform(60, 190)
        sp = rng.uniform(12, 30)
        ph = rng.uniform(0, 6.28)
        y = by - sp * lt + 14 * math.sin(lt * 1.3 + ph)
        x = bx + 10 * math.cos(lt * 0.9 + ph)
        d.ellipse([x - r, y - r, x + r, y + r], fill=DECO[k] + (255,))
    return c


def text_center(d, y, s, sz, fill, bold=True, stroke=0, stroke_fill=None, x=W / 2):
    f = font(sz, bold)
    l, t_, r, b = d.textbbox((0, 0), s, font=f, stroke_width=stroke)
    d.text((x - (r - l) / 2 - l, y - t_), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
    return r - l, b - t_


def pop_text(canvas, s, cx, cy, sz, fill, t0, lt, rot=0, stroke=10, pill=None):
    """Text that scales in with overshoot at local time t0."""
    p = (lt - t0) / 0.45
    if p <= 0:
        return
    sc = e_back(p, 2.6)
    a = clamp(p * 3)
    f = font(sz)
    l, t_, r, b = ImageDraw.Draw(canvas).textbbox((0, 0), s, font=f, stroke_width=stroke)
    pad = 40
    tw, th = r - l + pad * 2, b - t_ + pad * 2
    layer = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if pill:
        d.rounded_rectangle([pad - 34, pad - 22, tw - pad + 34, th - pad + 22], radius=(th - pad) // 2 + 10, fill=pill)
    d.text((pad - l, pad - t_), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=(255, 255, 255))
    w2, h2 = max(1, int(tw * sc)), max(1, int(th * sc))
    layer = layer.resize((w2, h2), Image.LANCZOS)
    if rot:
        layer = layer.rotate(rot, resample=Image.BICUBIC, expand=True)
    if a < 1:
        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * a)))
    canvas.alpha_composite(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)))


def subtitle(canvas, k, lt):
    """Karaoke caption: spoken words ink, current word highlighted, rest muted."""
    ws = WORDS[k]
    tokens = LINES[k].split(" ")
    f = font(62)
    d = ImageDraw.Draw(canvas)
    space = 18
    widths = [d.textlength(tk, font=f) for tk in tokens]
    rows, cur, cw = [], [], 0
    for i, wd in enumerate(widths):
        if cur and cw + space + wd > 900:
            rows.append(cur)
            cur, cw = [], 0
        cw += (space if cur else 0) + wd
        cur.append(i)
    rows.append(cur)
    lh = 86
    box_h = lh * len(rows) + 56
    y0 = 1560 - box_h / 2
    p = e_out((lt - 0.05) / 0.35)
    yoff = (1 - p) * 40
    bw = max(sum(widths[i] for i in r) + space * (len(r) - 1) for r in rows) + 96
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([W / 2 - bw / 2, y0 + yoff + 10, W / 2 + bw / 2, y0 + box_h + yoff + 10],
                                         radius=44, fill=(20, 30, 60, int(45 * p)))
    canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
    d.rounded_rectangle([W / 2 - bw / 2, y0 + yoff, W / 2 + bw / 2, y0 + box_h + yoff], radius=44,
                        fill=(255, 255, 255, int(245 * p)))
    for ri, row in enumerate(rows):
        rw = sum(widths[i] for i in row) + space * (len(row) - 1)
        x = W / 2 - rw / 2
        y = y0 + 28 + ri * lh + yoff
        for i in row:
            s0 = LEAD + ws[i][0]
            s1 = LEAD + ws[i][1]
            if lt >= s0 and lt < s1 + 0.08:
                col = WATER
                lift = 6 * math.sin(clamp((lt - s0) / 0.25) * math.pi)
            elif lt >= s1:
                col, lift = INK, 0
            else:
                col, lift = MUTED, 0
            a = int(255 * p)
            d.text((x, y - lift), tokens[i], font=f, fill=col + (a,))
            x += widths[i] + space


# ---------- scenes (lt = scene-local seconds) ----------
def scene0(lt):
    c = background(0, lt)
    d = ImageDraw.Draw(c)
    # kicker title
    p = e_out((lt - 0.1) / 0.5)
    text_center(d, 250 - (1 - p) * 40, "오후 3시의 당신", 92, INK + (int(255 * p),))
    # clock badge
    cp = e_back((lt - 0.25) / 0.5)
    if cp > 0:
        cx, cy, r = 540, 470, 70 * cp
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255), outline=INK, width=max(1, int(8 * cp)))
        for ang, ln, wd in [(-90 + 360 * (lt * 0.6) % 360, 0.78, 6), (0 + 20 * lt, 0.55, 9)]:
            a = math.radians(ang)
            d.line([cx, cy, cx + math.cos(a) * r * ln, cy + math.sin(a) * r * ln], fill=INK, width=wd)
    # tired man: rises, then droops with a slow sway
    ent = spring((lt - 0.15) / 1.2)
    sway = 2.5 * math.sin(lt * 2.0) * clamp(lt - 0.8)
    droop = 1 + 0.025 * math.sin(lt * 2.0 + 1.0)
    place(c, "tired", 540, 1330 + (1 - ent) * 700, 760 * droop, rot=sway)
    # gloomy squiggles above head at "멍하고"
    tq = word_t(0, 3)
    for j in range(3):
        q = e_back((lt - tq - j * 0.1) / 0.4)
        if q > 0:
            bx = 720 + j * 95
            by = 760 - j * 60 - 15 * math.sin(lt * 3 + j)
            pts = [(bx + 30 * math.cos(u / 6 * 2 * math.pi) * q * (1 - u / 40),
                    by + 30 * math.sin(u / 6 * 2 * math.pi) * q * (1 - u / 40)) for u in range(26)]
            d.line(pts, fill=(110, 120, 150), width=7, joint="curve")
    subtitle(c, 0, lt)
    return c


def scene1(lt):
    c = background(1, lt)
    d = ImageDraw.Draw(c)
    ent = e_back((lt - 0.05) / 0.6, 1.4)
    tw = word_t(1, 3)  # "물"
    shake = 0
    if lt > tw:
        shake = 10 * math.sin((lt - tw) * 55) * math.exp(-(lt - tw) * 2.5)
    place(c, "thirsty", 540 + shake, 1330, 820, scale=ent)
    pop_text(c, "물 부족?!", 540, 330, 150, (235, 75, 70), tw, lt, rot=-6, stroke=14)
    # sweat drops
    for j, (ox, oy) in enumerate([(-260, -560), (250, -620), (300, -470)]):
        q = (lt - tw - 0.15 - j * 0.12) / 0.8
        if 0 < q < 1:
            y = 1330 + oy + 120 * q * q
            a = int(255 * (1 - q))
            x = 540 + ox
            d.ellipse([x - 16, y - 8, x + 16, y + 24], fill=WATER + (a,))
            d.polygon([(x - 13, y), (x + 13, y), (x, y - 30)], fill=WATER + (a,))
    subtitle(c, 1, lt)
    return c


def scene2(lt):
    c = background(2, lt)
    d = ImageDraw.Draw(c)
    ent = e_out((lt - 0.05) / 0.6)
    cx, base, hgt = 540, 1340, 900
    place(c, "body", cx, base + (1 - ent) * 120, hgt, alpha=ent, shadow=True)
    # water filling the silhouette up to 60%
    t0 = word_t(2, 3)
    fill = 0.60 * e_inout((lt - t0 + 0.2) / 1.5)
    if fill > 0:
        src = SPR["body"]
        w = int(src.width * hgt / src.height)
        mask = src.resize((w, hgt), Image.LANCZOS).getchannel("A")
        top = base + (1 - ent) * 120 - hgt
        water = Image.new("RGBA", (w, hgt), (0, 0, 0, 0))
        wd = ImageDraw.Draw(water)
        lvl = hgt * (1 - fill)
        pts = [(x, lvl + 10 * math.sin(x / 55 + lt * 5)) for x in range(0, w + 1, 6)]
        wd.polygon(pts + [(w, hgt), (0, hgt)], fill=WATER + (200,))
        pts2 = [(x, lvl + 8 + 8 * math.sin(x / 40 - lt * 4)) for x in range(0, w + 1, 6)]
        wd.polygon(pts2 + [(w, hgt), (0, hgt)], fill=(40, 120, 230, 200))
        water.putalpha(Image.fromarray(np.minimum(np.asarray(water.getchannel("A")),
                                                  np.asarray(mask))))
        c.alpha_composite(water, (int(cx - w / 2), int(top)))
        # level marker
        ly = top + lvl
        d.line([cx + w / 2 + 10, ly, cx + w / 2 + 70, ly], fill=INK, width=6)
    # counter
    if lt > t0 - 0.2:
        val = int(round(fill * 100))
        p = e_back((lt - t0 + 0.2) / 0.4)
        pop_text(c, f"{val}%", 540, 300, 190, WATER, t0 - 0.2, lt, stroke=14)
        if lt > t0 + 0.6:
            q = e_out((lt - t0 - 0.6) / 0.4)
            text_center(d, 440 + (1 - q) * 20, "몸의 대부분은 물", 60, INK + (int(255 * q),))
    subtitle(c, 2, lt)
    return c


def scene3(lt):
    c = background(3, lt)
    d = ImageDraw.Draw(c)
    ent = spring((lt - 0.05) / 1.1, 1.8, 6)
    bob = 8 * math.sin(lt * 4) * clamp(lt - 0.5)
    place(c, "drink", 540, 860 + bob + (1 - ent) * 400, 560, alpha=clamp(ent * 2), rot=-3 * math.sin(lt * 2))
    # eight glasses pop in, synced from "여덟" to "잔"
    t0 = word_t(3, 1)
    gap = (word_t(3, 2) + 0.25 - t0) / 8
    for i in range(8):
        r, col = divmod(i, 4)
        gx = 540 + (col - 1.5) * 200
        gy = 1170 + r * 190
        q = (lt - t0 - i * gap) / 0.4
        if q > 0:
            sc = e_back(q, 2.4)
            # gentle wave after "조금씩 자주"
            wave = 0
            tw = word_t(3, 3)
            if lt > tw:
                wave = -18 * max(0, math.sin((lt - tw) * 6 - i * 0.6)) * math.exp(-(lt - tw) * 1.2)
            place(c, "glass", gx, gy + wave, 150, scale=sc, shadow=False)
    # counter pill
    n = sum(1 for i in range(8) if lt > t0 + i * gap)
    if n:
        pop_text(c, f"하루 {n}잔", 540, 220, 110, (255, 255, 255), t0, lt, stroke=0, pill=WATER + (255,))
    subtitle(c, 3, lt)
    return c


def scene4(lt):
    c = background(4, lt)
    # rotating sunburst
    rays = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rays)
    cx, cy = 540, 900
    a0 = lt * 12
    ra = e_out(lt / 0.8)
    for i in range(16):
        a = math.radians(a0 + i * 22.5)
        b = math.radians(a0 + i * 22.5 + 10)
        R = 1400 * ra
        rd.polygon([(cx, cy), (cx + R * math.cos(a), cy + R * math.sin(a)),
                    (cx + R * math.cos(b), cy + R * math.sin(b))], fill=(255, 255, 255, 110))
    c.alpha_composite(rays)
    d = ImageDraw.Draw(c)
    ent = spring((lt - 0.1) / 1.0, 2.0, 5)
    jump = abs(math.sin(lt * 4.2)) * 30 * clamp(lt - 0.9)
    sq = 1 + 0.03 * math.sin(lt * 8.4)
    place(c, "genki", 540, 1340 - jump, 800 * sq, scale=ent)
    # sparkles
    for j in range(9):
        ang = j * 40 + lt * 20
        rr = 380 + 40 * math.sin(lt * 3 + j)
        q = e_back((lt - 0.4 - j * 0.07) / 0.4)
        if q > 0:
            x = cx + rr * math.cos(math.radians(ang))
            y = 940 + rr * 1.05 * math.sin(math.radians(ang))
            s = (16 + 10 * math.sin(lt * 6 + j)) * q
            d.polygon([(x, y - s * 2), (x + s * 0.5, y - s * 0.5), (x + s * 2, y), (x + s * 0.5, y + s * 0.5),
                       (x, y + s * 2), (x - s * 0.5, y + s * 0.5), (x - s * 2, y), (x - s * 0.5, y - s * 0.5)],
                      fill=(255, 196, 0))
    t1 = word_t(4, 3)
    pop_text(c, "작은 습관", 540, 230, 100, INK, 0.3, lt, stroke=12)
    pop_text(c, "큰 변화!", 540, 370, 150, (255, 120, 40), t1, lt, rot=-4, stroke=14)
    subtitle(c, 4, lt)
    # outro fade
    fo = clamp((lt - (DUR[4] - 0.35)) / 0.35)
    if fo > 0:
        c.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(255 * fo))))
    return c


SCENES = [scene0, scene1, scene2, scene3, scene4]


def render(fi):
    t = fi / FPS
    k = max(i for i, s in enumerate(STARTS) if s <= t + 1e-9)
    lt = t - STARTS[k]
    img = SCENES[k](lt)
    if k > 0 and lt < TRANS:
        # circle-wipe from the previous scene (which keeps moving underneath)
        prev = SCENES[k - 1](t - STARTS[k - 1])
        p = e_inout(lt / TRANS)
        R = p * math.hypot(W, H) * 0.6
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).ellipse([W / 2 - R, H * 0.45 - R, W / 2 + R, H * 0.45 + R], fill=255)
        prev.paste(img, (0, 0), m)
        # ring on the wipe edge
        ImageDraw.Draw(prev).ellipse([W / 2 - R, H * 0.45 - R, W / 2 + R, H * 0.45 + R],
                                     outline=(255, 255, 255), width=int(18 * (1 - p)) + 1)
        img = prev
    # first-frame fade-in
    if t < 0.2:
        img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(255 * (1 - t / 0.2)))))
    return img.convert("RGB")


# ---------- audio: voice + synthesized SFX ----------
SR = 44100


def sfx_track():
    n = int(TOTAL * SR) + SR
    buf = np.zeros(n)

    def add(at, sig):
        i = int(at * SR)
        buf[i:i + len(sig)] += sig[: max(0, n - i)]

    def pop(f0=880, dur=0.12, g=0.25):
        tt = np.arange(int(dur * SR)) / SR
        f = f0 * np.exp(-tt * 18) + f0 * 0.5
        return g * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 30)

    def whoosh(dur=0.45, g=0.18):
        rng = np.random.RandomState(1)
        x = rng.randn(int(dur * SR))
        env = np.sin(np.linspace(0, np.pi, len(x))) ** 2
        y = np.convolve(x, np.ones(30) / 30, mode="same")
        return g * y * env * 3

    def ding(f0=1320, g=0.18):
        tt = np.arange(int(0.9 * SR)) / SR
        return g * (np.sin(2 * np.pi * f0 * tt) + 0.4 * np.sin(2 * np.pi * f0 * 2.01 * tt)) * np.exp(-tt * 5)

    for k in range(1, 5):
        add(STARTS[k] - 0.05, whoosh())
    add(STARTS[1] + word_t(1, 3), pop(300, 0.25, 0.35))
    add(STARTS[2] + word_t(2, 3) + 1.3, ding(1046))
    t0 = word_t(3, 1)
    gap = (word_t(3, 2) + 0.25 - t0) / 8
    for i in range(8):
        add(STARTS[3] + t0 + i * gap, pop(700 + 60 * i, 0.1, 0.18))
    add(STARTS[4] + word_t(4, 3), ding(1568, 0.2))
    add(STARTS[4] + 0.3, pop(600, 0.15, 0.22))
    return buf


def main():
    tmp = tempfile.mkdtemp()
    sfx = np.clip(sfx_track(), -1, 1)
    with wave.open(os.path.join(tmp, "sfx.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((sfx * 32767).astype(np.int16).tobytes())

    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                           os.path.join(tmp, "v.mp4")], stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for i, im in enumerate(pool.imap(render, range(NFRAMES), chunksize=4)):
            ff.stdin.write(im.tobytes())
            if i % 60 == 0:
                print(f"frame {i}/{NFRAMES}", flush=True)
    ff.stdin.close()
    ff.wait()

    inputs, filt = [], []
    for k in range(len(WORDS)):
        inputs += ["-i", os.path.join(TTS, f"{k}.mp3")]
        ms = int(AUDIO_AT[k] * 1000)
        filt.append(f"[{k + 1}:a]aresample=44100,adelay={ms}|{ms}[a{k}]")
    n = len(WORDS)
    filt.append(f"[{n + 1}:a]volume=0.9[s]")
    filt.append("".join(f"[a{k}]" for k in range(n)) + f"[s]amix=inputs={n + 1}:normalize=0,"
                "loudnorm=I=-15:TP=-1.5[aout]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(tmp, "v.mp4"), *inputs,
                    "-i", os.path.join(tmp, "sfx.wav"), "-filter_complex", ";".join(filt),
                    "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", OUT], check=True)
    print("done", OUT, f"{TOTAL:.2f}s")


if __name__ == "__main__":
    main()
