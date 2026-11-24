#!/usr/bin/env python3
"""Story short "the wrong Dave": pinned hook title, irasutoya scenes, chat-phone UI,
multi-voice TTS, word-synced motion, whip pans, SFX + BGM.

usage: python3 irasutoya_dave.py ASSET_DIR TTS_DIR OUT.mp4
  TTS_DIR: 0.mp3.. + segments.json [{scene, speaker, text, words:[[s,e,w],..]}, ..]
"""
import json, math, os, subprocess, sys, tempfile, wave
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
TOPH = 400                      # pinned title band
VW, VH = W, H - TOPH            # scene viewport
FB = "/usr/share/fonts/truetype/nanum/NanumSquareRoundB.ttf"
FR = "/usr/share/fonts/truetype/nanum/NanumSquareRoundR.ttf"
FX = "/usr/share/fonts/truetype/nanum/NanumSquareB.ttf"
YEL = (255, 214, 0)
RED = (232, 52, 52)
BLUE = (52, 120, 246)
INK = (30, 32, 40)

TITLE = ["문자 한 통 잘못 보냈다가", "남의 집 불륜 의심 폭발함"]

ASSETS, TTS, OUT = sys.argv[1:4]
SEGS = json.load(open(os.path.join(TTS, "segments.json")))

# ---------------- timeline ----------------
SCENES = []   # dict(key, start, dur, segs=[(local_start, seg_index)])
_cur = 0.0
for i, s in enumerate(SEGS):
    new = not SCENES or SCENES[-1]["key"] != s["scene"]
    if new:
        if SCENES:
            SCENES[-1]["dur"] = _cur + 0.22 - SCENES[-1]["start"]
            _cur += 0.22
        SCENES.append({"key": s["scene"], "start": _cur, "segs": []})
    st = _cur + (0.18 if new else 0.14)
    s["abs"] = st
    SCENES[-1]["segs"].append((st - SCENES[-1]["start"], i))
    _cur = st + s["words"][-1][1]
SCENES[-1]["dur"] = _cur + 1.6 - SCENES[-1]["start"]
TOTAL = SCENES[-1]["start"] + SCENES[-1]["dur"]
NFRAMES = int(round(TOTAL * FPS))
XF = 0.3


class Ctx:
    """per-scene helper: wt(segment#, word#) -> scene-local time."""

    def __init__(self, sc):
        self.sc = sc
        self.dur = sc["dur"]

    def seg(self, j):
        return self.sc["segs"][j]

    def wt(self, j, w=0, end=False):
        ls, si = self.sc["segs"][j]
        ws = SEGS[si]["words"]
        w = min(w, len(ws) - 1) if w >= 0 else len(ws) + w
        return ls + ws[w][1 if end else 0]

    def segend(self, j):
        return self.wt(j, -1, True)


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


SPR = {k: load(v) for k, v in {
    "pool": "pool_asobu_couple.png", "lady": "pet_dog_sanpo_woman.png", "wine": "red_wine.png",
    "beer": "beer_man.png", "jealous": "shitto_man.png", "angry": "face_angry_man4.png",
    "rage": "pose_sugoi_okoru_man.png", "dogeza": "pose_syazai_sliding_dogeza_man.png",
    "tv": "tv_haishin_owarai_man.png", "scale": "tenbin1_unbalanced.png", "chair": "kagu_deck_chair.png",
    "wife": "face_angry_woman5.png", "party": "party_beer_garden_casual_day.png",
    "burst": "syuchusen1.png", "wing": "tenshi_wing1.png",
}.items()}
BGS = {
    "street": load("bg_outside_jutaku.jpg").filter(ImageFilter.GaussianBlur(2.4)),
    "dusk": load("bg_outside_jutaku_yuyake.jpg").filter(ImageFilter.GaussianBlur(2.4)),
    "living": load("bg_house_living.jpg").filter(ImageFilter.GaussianBlur(2.2)),
    "speed": load("bg_koukasen_color1.png"),
}
_fonts = {}


def font(sz, f=FB):
    if (sz, f) not in _fonts:
        _fonts[(sz, f)] = ImageFont.truetype(f, sz)
    return _fonts[(sz, f)]


_yy, _xx = np.mgrid[0:VH, 0:VW]
_r = np.sqrt(((_xx - VW / 2) / (VW * 0.72)) ** 2 + ((_yy - VH / 2) / (VH * 0.62)) ** 2)
VIG = np.clip((_r - 0.55) / 0.6, 0, 1)[..., None] ** 1.6
_rng = np.random.RandomState(7)
GRAIN = [(_rng.randn(VH // 2, VW // 2) * 4).repeat(2, 0).repeat(2, 1)[..., None] for _ in range(6)]


# ---------------- drawing primitives ----------------
class Cam:
    def __init__(self, z=1.0, cx=VW / 2, cy=VH / 2, dx=0.0, dy=0.0):
        self.z, self.cx, self.cy, self.dx, self.dy = z, cx, cy, dx, dy

    def pt(self, x, y):
        return (x - self.cx) * self.z + VW / 2 + self.dx, (y - self.cy) * self.z + VH / 2 + self.dy


def shake(cam, t, t0, amp=12, decay=3.0):
    if t > t0:
        a = amp * math.exp(-(t - t0) * decay)
        cam.dx += a * math.sin(t * 77)
        cam.dy += a * math.cos(t * 59)


def draw_bg(name, cam, pan=0.0, parallax=0.55, darken=0.0, tint=None):
    src = BGS[name]
    z = 1 + (cam.z - 1) * parallax
    hw = VH * 1.04
    s = z * hw / src.height
    ww = src.width * s
    left = VW / 2 - ww / 2 + pan * z + cam.dx * parallax
    top = VH / 2 - hw * z / 2 + cam.dy * parallax
    im = src.transform((VW, VH), Image.AFFINE, (1 / s, 0, -left / s, 0, 1 / s, -top / s), resample=Image.BILINEAR)
    if darken:
        im = Image.blend(im, Image.new("RGBA", (VW, VH), (10, 10, 20, 255)), darken)
    if tint:
        im.alpha_composite(Image.new("RGBA", (VW, VH), tint))
    return im


def place(c, cam, name, x, y, h, sc=1.0, rot=0.0, alpha=1.0, anchor="bottom", flip=False, shadow=False):
    if sc <= 0.01 or alpha <= 0.01:
        return
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
        sh = Image.new("RGBA", (VW, VH), (0, 0, 0, 0))
        r = ww * 0.38
        ImageDraw.Draw(sh).ellipse([sx - r, sy - 20 * cam.z, sx + r, sy + 16 * cam.z], fill=(0, 0, 0, int(70 * alpha)))
        c.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
    c.alpha_composite(im, (int(sx - im.width / 2), int(sy - im.height) if anchor == "bottom" else int(sy - im.height / 2)))


def paste_layer(c, lay, x, y, sc=1.0, rot=0.0, alpha=1.0):
    if sc <= 0.02 or alpha <= 0.02:
        return
    if sc != 1:
        lay = lay.resize((max(1, int(lay.width * sc)), max(1, int(lay.height * sc))), Image.LANCZOS)
    if rot:
        lay = lay.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 1:
        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * alpha)))
    c.alpha_composite(lay, (int(x - lay.width / 2), int(y - lay.height / 2)))


def label(c, s, x, y, sz, fg=(40, 30, 20), bg=(255, 246, 220), border=(60, 45, 30), sc=1.0, rot=0.0, alpha=1.0):
    f = font(sz)
    l, t, r, b = ImageDraw.Draw(c).textbbox((0, 0), s, font=f)
    px, py = int(sz * 0.5), int(sz * 0.28)
    tw, th = r - l + px * 2, b - t + py * 2
    lay = Image.new("RGBA", (tw + 16, th + 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([8, 8, 8 + tw, 8 + th], radius=int(sz * 0.35), fill=bg, outline=border, width=max(3, sz // 12))
    d.text((8 + px - l, 8 + py - t), s, font=f, fill=fg)
    paste_layer(c, lay, x, y, sc, rot, alpha)


def bigtext(c, s, x, y, sz, fill, t0, t, rot=0.0, stroke=14, sfill=(255, 255, 255), wobble=0.0, dur=0.4):
    p = (t - t0) / dur
    if p <= 0:
        return
    fnt = font(sz)
    l, tt, r, b = ImageDraw.Draw(c).textbbox((0, 0), s, font=fnt, stroke_width=stroke)
    lay = Image.new("RGBA", (r - l + 40, b - tt + 40), (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((20 - l, 20 - tt), s, font=fnt, fill=fill, stroke_width=stroke, stroke_fill=sfill)
    paste_layer(c, lay, x, y, eback(p, 2.8), rot + wobble * math.sin(t * 9))


def burst(c, x, y, size, t, alpha=1.0, color=(255, 255, 255)):
    s = int(size)
    im = SPR["burst"].resize((s, s), Image.BILINEAR).rotate(t * 25, resample=Image.BICUBIC)
    col = Image.new("RGBA", im.size, color + (0,))
    col.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    c.alpha_composite(col, (int(x - s / 2), int(y - s / 2)))


def wrap(d, text, f, maxw):
    lines, cur = [], ""
    for tok in text.split(" "):
        tr = (cur + " " + tok).strip()
        if d.textlength(tr, font=f) <= maxw or not cur:
            cur = tr
        else:
            lines.append(cur)
            cur = tok
    lines.append(cur)
    return lines


def speech_bubble(c, text, x, y, t0, t, maxw=760, sz=54, tail=(0, 1), words=None, fill=(255, 255, 255),
                  fg=INK, border=INK):
    """Comic speech bubble; if `words` (list of local start times) is given, text types on word by word."""
    p = (t - t0) / 0.35
    if p <= 0:
        return
    f = font(sz)
    d0 = ImageDraw.Draw(c)
    lines = wrap(d0, text, f, maxw)
    lh = int(sz * 1.35)
    tw = max(d0.textlength(l_, font=f) for l_ in lines)
    bw, bh = int(tw + sz * 1.6), int(lh * len(lines) + sz * 1.1)
    lay = Image.new("RGBA", (bw + 120, bh + 140), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    ox, oy = 60, 20
    tx = ox + bw / 2 + tail[0] * bw * 0.3
    d.polygon([(tx - 34, oy + bh - 10), (tx + 34, oy + bh - 10), (tx + tail[0] * 60, oy + bh + 90)], fill=fill,
              outline=border)
    d.rounded_rectangle([ox, oy, ox + bw, oy + bh], radius=int(sz * 0.9), fill=fill, outline=border, width=7)
    d.polygon([(tx - 28, oy + bh - 14), (tx + 28, oy + bh - 14), (tx + tail[0] * 54, oy + bh + 80)], fill=fill)
    # typing: reveal tokens whose start time has passed
    shown = None
    if words is not None:
        shown = sum(1 for wt_ in words if t >= wt_ - 0.02)
    k = 0
    for li, line in enumerate(lines):
        toks = line.split(" ")
        xx = ox + sz * 0.8
        for tok in toks:
            if shown is None or k < shown:
                d.text((xx, oy + sz * 0.5 + li * lh), tok, font=f, fill=fg)
            xx += d.textlength(tok + " ", font=f)
            k += 1
    paste_layer(c, lay, x, y, eback(p, 2.2))


# ---------------- phone UI ----------------
PW, PH = 600, 1060


def phone(c, x, y, sc, title, msgs, t, rot=0.0, badge=0, crack=0.0, contacts=None):
    """msgs: [(side 'in'/'out', text, appear_time)]. Newest at bottom; older scroll up."""
    lay = Image.new("RGBA", (PW + 40, PH + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([20, 20, PW + 20, PH + 20], radius=80, fill=(28, 30, 36))
    sx0, sy0, sx1, sy1 = 44, 44, PW - 4, PH - 4
    d.rounded_rectangle([sx0, sy0, sx1, sy1], radius=60, fill=(245, 246, 250))
    # header
    d.rounded_rectangle([sx0, sy0, sx1, sy0 + 170], radius=60, fill=(255, 255, 255))
    d.rectangle([sx0, sy0 + 100, sx1, sy0 + 170], fill=(255, 255, 255))
    d.line([sx0, sy0 + 170, sx1, sy0 + 170], fill=(220, 222, 230), width=3)
    d.rounded_rectangle([PW / 2 - 60, sy0 + 18, PW / 2 + 100, sy0 + 48], radius=15, fill=(28, 30, 36))
    d.text((sx0 + 40, sy0 + 70), "‹", font=font(60, FX), fill=BLUE)
    f = font(44)
    tw = d.textlength(title, font=f)
    d.text((20 + PW / 2 - tw / 2, sy0 + 86), title, font=f, fill=INK)
    body = Image.new("RGBA", (sx1 - sx0, sy1 - sy0 - 172), (0, 0, 0, 0))
    bd = ImageDraw.Draw(body)
    if contacts:
        fy = 20
        for i, (name, hi) in enumerate(contacts):
            ry = 20 + i * 118
            bd.ellipse([30, ry + 14, 110, ry + 94], fill=[(255, 190, 120), (130, 190, 255), (160, 220, 160),
                                                         (240, 160, 200), (200, 180, 255)][i % 5])
            bd.text((58, ry + 30), name[0], font=font(40), fill=(255, 255, 255))
            bd.text((140, ry + 32), name, font=font(46), fill=INK)
            bd.line([140, ry + 116, body.width - 20, ry + 116], fill=(225, 227, 235), width=2)
            if hi > 0:
                a = int(255 * cl(hi))
                bd.rounded_rectangle([12, ry + 4, body.width - 12, ry + 110], radius=24, outline=RED + (a,), width=8)
    else:
        bf = font(44)
        items = []
        for side, text, ta in msgs:
            if t < ta:
                continue
            lines = wrap(bd, text, bf, 400)
            bh = 58 * len(lines) + 40
            bw = max(bd.textlength(l_, font=bf) for l_ in lines) + 56
            items.append((side, lines, bh, bw, ta))
        ybot = body.height - 30
        for side, lines, bh, bw, ta in reversed(items):
            p = eback((t - ta) / 0.3, 2.2)
            sh = bh * cl(p * 1.2)
            top = ybot - sh
            if top + bh < 0:
                break
            x0 = 28 if side == "in" else body.width - 28 - bw
            col = (229, 230, 236) if side == "in" else BLUE
            tc = INK if side == "in" else (255, 255, 255)
            bub = Image.new("RGBA", (int(bw), int(bh)), (0, 0, 0, 0))
            dd = ImageDraw.Draw(bub)
            dd.rounded_rectangle([0, 0, bw - 1, bh - 1], radius=34, fill=col)
            for li, l_ in enumerate(lines):
                dd.text((28, 18 + li * 58), l_, font=bf, fill=tc)
            ps = max(0.05, p)
            bub = bub.resize((max(1, int(bw * ps)), max(1, int(bh * ps))), Image.LANCZOS)
            ax = x0 if side == "in" else x0 + bw - bub.width
            body.alpha_composite(bub, (int(ax), int(top + bh - bub.height)))
            ybot = top - 22
    lay.alpha_composite(body, (sx0, sy0 + 172))
    if badge:
        bx, by = PW - 10, 40
        d.ellipse([bx - 50, by - 50, bx + 50, by + 50], fill=RED, outline=(255, 255, 255), width=6)
        s = str(badge)
        fw = d.textlength(s, font=font(48))
        d.text((bx - fw / 2, by - 28), s, font=font(48), fill=(255, 255, 255))
    if crack > 0:
        rng = np.random.RandomState(4)
        cx0, cy0 = PW * 0.55, PH * 0.45
        for k in range(9):
            ang = k * 0.7 + rng.uniform(-0.2, 0.2)
            pts = [(cx0, cy0)]
            L = 0
            while L < 700 * crack:
                L += rng.uniform(40, 90)
                ang += rng.uniform(-0.35, 0.35)
                pts.append((cx0 + L * math.cos(ang), cy0 + L * math.sin(ang)))
            d.line(pts, fill=(255, 255, 255, 230), width=5)
            d.line([(p_[0] + 3, p_[1] + 3) for p_ in pts], fill=(60, 60, 70, 150), width=3)
    mask = Image.new("L", lay.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([20, 20, PW + 20, PH + 20], radius=80, fill=255)
    lay.putalpha(Image.fromarray(np.minimum(np.asarray(lay.getchannel("A")), np.asarray(mask))))
    # drop shadow
    shd = Image.new("RGBA", (VW, VH), (0, 0, 0, 0))
    s2 = sc
    ImageDraw.Draw(shd).rounded_rectangle([x - PW * s2 / 2 + 20, y - PH * s2 / 2 + 40, x + PW * s2 / 2 + 20,
                                           y + PH * s2 / 2 + 40], radius=80 * s2, fill=(0, 0, 0, 80))
    c.alpha_composite(shd.filter(ImageFilter.GaussianBlur(24)))
    paste_layer(c, lay, x, y, sc, rot)


def notif(c, title, text, y, t0, t):
    """iOS-like banner dropping in from the top of the viewport."""
    p = (t - t0) / 0.45
    if p <= 0:
        return
    yy = lerp(-140, y, eback(p, 1.6))
    lay = Image.new("RGBA", (980, 190), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([0, 0, 979, 189], radius=46, fill=(255, 255, 255, 245))
    d.rounded_rectangle([30, 40, 130, 140], radius=26, fill=(60, 200, 90))
    d.rectangle([52, 66, 108, 112], outline=(255, 255, 255), width=5)
    d.line([52, 68, 80, 92, 108, 68], fill=(255, 255, 255), width=5)
    d.text((160, 34), title, font=font(40), fill=(120, 124, 135))
    d.text((160, 96), text, font=font(50), fill=INK)
    sh = Image.new("RGBA", (VW, VH), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([60, yy - 80, 1020, yy + 110], radius=46, fill=(0, 0, 0, 70))
    c.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)))
    c.alpha_composite(lay, (50, int(yy - 95)))


# ---------------- subtitles ----------------
QUOTE_HIDDEN = set()  # segment indices shown in bubbles instead


def subtitle(c, si, lt_seg):
    s = SEGS[si]
    ws = s["words"]
    toks = s["text"].split(" ")
    if len(toks) != len(ws):
        toks = [w[2] for w in ws]
    f = font(64)
    d = ImageDraw.Draw(c)
    sp = 18
    wid = [d.textlength(x, font=f) for x in toks]
    rows, cur, cw = [], [], 0
    for i, w_ in enumerate(wid):
        if cur and cw + sp + w_ > 960:
            rows.append(cur)
            cur, cw = [], 0
        cw += (sp if cur else 0) + w_
        cur.append(i)
    rows.append(cur)
    p = eo((lt_seg + 0.05) / 0.18)
    y0 = 1190 - (len(rows) - 1) * 88
    for ri, row in enumerate(rows):
        rw = sum(wid[i] for i in row) + sp * (len(row) - 1)
        x = VW / 2 - rw / 2
        y = y0 + ri * 88 + (1 - p) * 24
        for i in row:
            on = ws[i][0] <= lt_seg < ws[i][1] + 0.06
            col = YEL if on else (255, 255, 255)
            lift = 7 * math.sin(cl((lt_seg - ws[i][0]) / 0.22) * math.pi) if on else 0
            d.text((x, y - lift), toks[i], font=f, fill=col + (int(255 * p),), stroke_width=10,
                   stroke_fill=(20, 20, 28, int(255 * p)))
            x += wid[i] + sp


# ---------------- scenes ----------------
def sc_pool(t, x):
    cam = Cam(z=lerp(1.0, 1.1, eio(t / x.dur)))
    c = draw_bg("street", cam, pan=lerp(300, 180, eio(t / x.dur)))
    # bunting
    lay = Image.new("RGBA", (VW, 260), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    pts = [(xx, 60 + 50 * math.sin(xx / VW * math.pi)) for xx in range(-20, VW + 40, 20)]
    d.line(pts, fill=(90, 80, 70), width=5)
    cols = [RED, YEL, BLUE, (60, 190, 110), (255, 140, 60)]
    for k, xx in enumerate(range(20, VW, 90)):
        yy = 60 + 50 * math.sin(xx / VW * math.pi)
        sw = 6 * math.sin(t * 3 + k)
        d.polygon([(xx, yy), (xx + 70, yy + 4), (xx + 35 + sw, yy + 80)], fill=cols[k % 5])
    p = eo(t / 0.5)
    c.alpha_composite(lay, (0, int(-140 * (1 - p))))
    label(c, "마이크네 수영장 파티", VW / 2, 250, 64, fg=(255, 255, 255), bg=BLUE, border=(255, 255, 255),
          sc=eback((x.wt(0, 1) - 0.1 - 0 + t - x.wt(0, 1)) / 0.4) if t > x.wt(0, 1) - 0.1 else 0, rot=-2)
    place(c, cam, "party", 540, 900, 520, sc=eo((t - 0.1) / 0.5), alpha=0.95)
    bob = 10 * math.sin(t * 3)
    place(c, cam, "pool", 560, 1230 + bob * 0.3, 720, sc=spring((t - x.wt(0, 2) + 0.2) / 0.9, 1.8, 5), shadow=True)
    place(c, cam, "beer", 900, 1560, 640, sc=spring((t - x.wt(0, 4)) / 0.8), rot=-4 + 3 * math.sin(t * 4))
    if t > x.wt(0, 4) + 0.3:
        label(c, "나", *cam.pt(820, 900), 56, sc=eback((t - x.wt(0, 4) - 0.3) / 0.35), rot=6)
    return c, (255, 236, 200), 0.08


def sc_lady(t, x):
    cam = Cam(z=lerp(1.05, 1.15, eio(t / x.dur)))
    c = draw_bg("street", cam, pan=lerp(140, -40, eio(t / x.dur)))
    place(c, cam, "pool", 880, 1200, 520, alpha=0.95)
    walk = eio((t - 0.05) / 1.6)
    lx = lerp(-260, 400, walk)
    step = abs(math.sin(t * 9)) * 18 * (1 - cl((t - 1.6) * 3))
    place(c, cam, "lady", lx, 1400 - step, 820, shadow=True, rot=2 * math.sin(t * 9) * (1 - walk * 0.7))
    ta = x.wt(0, 4)
    if t > ta:
        label(c, "동네 아줌마", *cam.pt(lx - 40, 500), 58, sc=eback((t - ta) / 0.35), rot=-4)
        # pointer
        sx, sy = cam.pt(lx - 40, 570)
        d = ImageDraw.Draw(c)
        d.polygon([(sx - 18, sy), (sx + 18, sy), (sx, sy + 30)], fill=(60, 45, 30))
    tz = x.wt(0, 5)
    if t > tz:
        label(c, "잠깐만 들름", *cam.pt(780, 640), 50, fg=(255, 255, 255), bg=(255, 120, 60), border=(255, 255, 255),
              sc=eback((t - tz) / 0.35), rot=5)
    return c, (255, 236, 200), 0.08


def sc_ask(t, x):
    cam = Cam(z=lerp(1.25, 1.35, eio(t / x.dur)), cx=420, cy=900)
    c = draw_bg("street", cam, pan=-40, darken=0.05)
    place(c, cam, "lady", 400, 1400, 820, shadow=True)
    tw = x.wt(0, 5)
    place(c, cam, "wine", 780, 1180, 360, sc=eback((t - tw) / 0.4), rot=8 * math.sin(t * 2))
    ls, si = x.seg(0)
    words = [ls + w[0] for w in SEGS[si]["words"]]
    QUOTE_HIDDEN.add(si)
    speech_bubble(c, SEGS[si]["text"], VW / 2, 330, ls - 0.25, t, maxw=820, sz=56, tail=(-0.6, 1), words=words)
    return c, (255, 236, 200), 0.08


def sc_contact(t, x):
    t2 = x.wt(0, 4)
    cam = Cam(z=lerp(1.0, 1.08, eio(t / x.dur)) + 0.12 * eback((t - t2) / 0.4) * (t > t2))
    shake(cam, t, t2, 10)
    c = draw_bg("street", cam, pan=200, darken=0.35)
    hi = cl((t - t2) / 0.2)
    rows = [("다니엘", 0), ("데이브", hi), ("데이브", hi), ("데보라", 0), ("드웨인", 0)]
    phone(c, *cam.pt(540, 640), 0.95 * cam.z, "연락처", [], t, rot=-2 + 1.5 * math.sin(t * 1.5),
          contacts=rows)
    if t > t2:
        bigtext(c, "?!", *cam.pt(900, 360), 200, RED, t2, t, rot=10, wobble=5)
        label(c, "데이브 2명", *cam.pt(220, 300), 60, fg=(255, 255, 255), bg=RED, border=(255, 255, 255),
              sc=eback((t - t2 - 0.1) / 0.35), rot=-6)
    return c, (230, 236, 255), 0.05


MSG = "나 마이크네서 와인 한 잔만 하고 갈게"


def sc_wrong(t, x):
    t1 = x.seg(1)[0]
    if t < t1 - 0.05:
        cam = Cam(z=1.0)
        c = draw_bg("dusk", cam, pan=lerp(-100, 0, t / t1), darken=0.1)
        p = eio((t - 0.2) / 1.2)
        # message envelope flies from phone (left) to wrong Dave (right)
        phone(c, 260, 560, 0.55, "데이브", [("out", MSG, 0.0)], t, rot=-6)
        place(c, cam, "jealous", 800, 1300, 600, sc=eo((t - 0.4) / 0.5), shadow=True)
        if 0 < p < 1:
            fx = lerp(330, 760, p)
            fy = lerp(500, 820, p) - 300 * math.sin(math.pi * p)
            lay = Image.new("RGBA", (220, 150), (0, 0, 0, 0))
            d = ImageDraw.Draw(lay)
            d.rounded_rectangle([10, 10, 210, 140], radius=18, fill=(255, 255, 255), outline=INK, width=6)
            d.line([10, 14, 110, 80, 210, 14], fill=INK, width=6)
            for side in (-1, 1):
                place(c, cam, "wing", fx + side * 110, fy - 20, 90, rot=side * (20 * math.sin(t * 25) + 10),
                      anchor="center", flip=side == 1)
            paste_layer(c, lay, fx, fy, 1.0, 20 * math.sin(p * 6))
        tw = x.wt(0, 1)
        if t > tw:
            label(c, "엉뚱한 데이브", *cam.pt(800, 560), 62, fg=(255, 255, 255), bg=RED, border=(255, 255, 255),
                  sc=eback((t - tw) / 0.35), rot=4)
        return c, (255, 210, 170), 0.1
    lt = t - t1
    cam = Cam(z=lerp(1.0, 1.25, eio(lt / (x.dur - t1))), cx=560, cy=900)
    c = draw_bg("dusk", cam, pan=0, darken=0.35, tint=(120, 0, 30, 40))
    place(c, cam, "jealous", 560, 1380, 900, shadow=True)
    ts = x.wt(1, 6)
    if t > x.wt(1, 4):
        label(c, "아내 ♥ 마이크?", *cam.pt(330, 540), 70, fg=RED, bg=(255, 240, 245), border=RED,
              sc=eback((t - x.wt(1, 4)) / 0.35), rot=-5)
    if t > ts:
        bigtext(c, "의심 중...", *cam.pt(760, 400), 90, (90, 40, 150), ts, t, rot=6, wobble=2)
    return c, (200, 150, 200), 0.12


def chat_msgs(x, upto_scene_offset=0.0):
    """Shared conversation for the bomb/knew/last scenes, in absolute time."""
    bomb = next(s for s in SCENES if s["key"] == "bomb")
    knew = next(s for s in SCENES if s["key"] == "knew")
    last = next(s for s in SCENES if s["key"] == "last")
    m = [("out", MSG, -99)]
    for ls, si in bomb["segs"][1:]:
        m.append(("in", SEGS[si]["text"], bomb["start"] + ls))
    m.append(("in", "둘이 같이 있는 사진 찍어서 보내요", knew["start"] + knew["segs"][0][0] + 1.0))
    m.append(("in", "나 처음부터 알고 있었어", knew["start"] + knew["segs"][1][0]))
    m.append(("out", "죄송해요 잘못 보냈어요ㅠㅠ 다른 데이브한테 보낼 거였어요", next(s for s in SCENES if s["key"] == "sorry")["start"] + 1.6))
    m.append(("in", SEGS[last["segs"][1][1]]["text"], last["start"] + last["segs"][1][0]))
    return m


def sc_bomb(t, x):
    A = x.sc["start"]
    msgs = chat_msgs(x)
    arrivals = [ta - A for side, _, ta in msgs if side == "in" and 0 <= ta - A <= x.dur]
    cam = Cam(z=lerp(1.0, 1.1, eio(t / x.dur)))
    for a in arrivals:
        shake(cam, t, a, 14, 6)
    tb = x.wt(0, 2)
    shake(cam, t, tb, 10, 4)
    c = draw_bg("dusk", cam, pan=-200, darken=0.45)
    if t > tb:
        burst(c, VW / 2, 640, 1500, t, 0.35, (255, 220, 120))
    n = sum(1 for a in arrivals if t >= a)
    for ls, si in x.sc["segs"][1:]:
        QUOTE_HIDDEN.add(si)
    phone(c, *cam.pt(540, 650), 0.98, "데이브", [(s, tx, ta - A) for s, tx, ta in msgs], t,
          rot=2 * math.sin(t * 40) * sum(math.exp(-(t - a) * 6) for a in arrivals if t > a), badge=n * 3)
    if n:
        place(c, cam, "angry", 140, 380, 300, sc=eback((t - arrivals[0]) / 0.35), anchor="center",
              rot=6 * math.sin(t * 20))
    bigtext(c, "답장 폭탄", *cam.pt(830, 220), 96, RED, tb, t, rot=8, wobble=3)
    return c, (220, 200, 255), 0.06


def sc_knew(t, x):
    A = x.sc["start"]
    t2 = x.seg(1)[0]
    msgs = chat_msgs(x)
    if t < t2 - 0.05:
        cam = Cam(z=lerp(1.1, 1.18, eio(t / t2)))
        c = draw_bg("dusk", cam, pan=-200, darken=0.45)
        a = x.seg(0)[0] + 1.0
        shake(cam, t, a, 14, 6)
        phone(c, *cam.pt(540, 650), 0.98, "데이브", [(s, tx, ta - A) for s, tx, ta in msgs], t, badge=12)
        if t > a:
            label(c, "인증샷 요구", *cam.pt(820, 230), 60, fg=(255, 255, 255), bg=(255, 120, 60),
                  border=(255, 255, 255), sc=eback((t - a) / 0.35), rot=6)
        return c, (220, 200, 255), 0.06
    lt = t - t2
    cam = Cam(z=lerp(1.0, 1.15, eio(lt / 1.5)))
    shake(cam, t, t2, 16, 2.5)
    c = draw_bg("speed", cam, parallax=1.0)
    c.alpha_composite(Image.new("RGBA", (VW, VH), (255, 40, 30, 120)))
    place(c, cam, "rage", 540, 1450, 980, sc=eback(lt / 0.35))
    si = x.seg(1)[1]
    QUOTE_HIDDEN.add(si)
    words = [t2 + w[0] for w in SEGS[si]["words"]]
    speech_bubble(c, "나 처음부터 알고 있었어.", VW / 2, 260, t2 - 0.1, t, maxw=900, sz=76, words=words,
                  fill=(255, 255, 255), fg=RED, border=RED)
    return c, (255, 190, 170), 0.05


def sc_beer(t, x):
    cam = Cam(z=lerp(1.0, 1.1, eio(t / x.dur)))
    c = draw_bg("street", cam, pan=lerp(-200, -320, eio(t / x.dur)))
    place(c, cam, "pool", 540, 1250, 760, shadow=True)
    place(c, cam, "beer", 380, 1260 + 8 * math.sin(t * 3), 700, sc=spring(t / 0.8), rot=3 * math.sin(t * 2.5))
    # forgotten phone on the deck chair, buzzing
    place(c, cam, "chair", 860, 1430, 360)
    buzz = 6 * math.sin(t * 60) * (int(t * 2) % 2)
    cnt = int(cl(t / (x.dur - 0.5)) * 37)
    lay = Image.new("RGBA", (150, 250), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([0, 0, 149, 249], radius=24, fill=(28, 30, 36))
    d.rounded_rectangle([10, 10, 139, 239], radius=18, fill=(70, 90, 140) if int(t * 4) % 2 else (40, 50, 80))
    sx, sy = cam.pt(860 + buzz, 1240)
    paste_layer(c, lay, sx, sy, cam.z * 0.9, -70)
    if cnt:
        label(c, f"읽지 않음 {cnt}", sx - 90, sy - 170, 46, fg=(255, 255, 255), bg=RED, border=(255, 255, 255))
    tz = x.wt(0, 7)
    if t > tz:
        label(c, "폰 안 봄", *cam.pt(380, 520), 70, sc=eback((t - tz) / 0.35), rot=-5)
    # clock fast-forward
    tc = x.wt(0, 3)
    if t > tc:
        lay = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        d.ellipse([6, 6, 194, 194], fill=(255, 255, 255), outline=INK, width=8)
        for ang, ln, wdt in [((t - tc) * 900, 0.75, 6), ((t - tc) * 75, 0.5, 10)]:
            a = math.radians(ang - 90)
            d.line([100, 100, 100 + 94 * ln * math.cos(a), 100 + 94 * ln * math.sin(a)], fill=INK, width=wdt)
        paste_layer(c, lay, 150, 220, eback((t - tc) / 0.35))
        label(c, "1시간 순삭", 150, 360, 44, sc=eback((t - tc - 0.15) / 0.35))
    return c, (255, 236, 200), 0.06


def sc_wife(t, x):
    t2 = x.seg(1)[0]
    cam = Cam(z=1.0 + (0.1 * eback((t - t2) / 0.3) if t > t2 else 0))
    shake(cam, t, t2, 14, 3)
    c = draw_bg("street", cam, pan=-300, darken=0.2 + 0.25 * cl((t - t2) * 3))
    place(c, cam, "beer", 540, 1500, 800, rot=0)
    tn = x.wt(0, 6)
    if t > t2:
        burst(c, VW / 2, 820, 1700, t, 0.6, (255, 120, 120))
        place(c, cam, "wife", 540, 900, 760, sc=eback((t - t2) / 0.35), anchor="center")
    si = x.seg(1)[1]
    QUOTE_HIDDEN.add(si)
    notif(c, "데이브 아내", "왜 없는 얘기를 지어내요?", 150, tn - 0.1, t)
    if t > t2 + 0.6:
        bigtext(c, "헉", *cam.pt(880, 1080), 150, (255, 255, 255), t2 + 0.6, t, rot=10, sfill=INK)
    return c, (255, 220, 210), 0.05


def sc_sorry(t, x):
    cam = Cam(z=lerp(1.0, 1.06, eio(t / x.dur)))
    c = draw_bg("street", cam, pan=lerp(0, -120, eio(t / x.dur)), darken=0.1)
    sl = eo((t - 0.05) / 0.6)
    place(c, cam, "dogeza", lerp(1400, 540, sl), 1420, 620, shadow=True)
    tb = x.wt(0, 1)
    if t > tb:
        label(c, "아줌마네 데이브", *cam.pt(250, 330), 50, sc=eback((t - tb) / 0.35), rot=-4)
        label(c, "엉뚱한 데이브", *cam.pt(820, 330), 50, fg=(255, 255, 255), bg=RED, border=(255, 255, 255),
              sc=eback((t - tb - 0.1) / 0.35), rot=4)
        for k, (tx_, ty_) in enumerate([(250, 520), (820, 520)]):
            p = cl((t - tb - 0.2 - k * 0.15) / 0.5)
            if p > 0:
                bx = lerp(540, tx_, eio(p))
                by = lerp(1000, ty_, eio(p)) - 120 * math.sin(math.pi * p)
                label(c, "죄송합니다ㅠㅠ", *cam.pt(bx, by), 44, fg=(255, 255, 255), bg=BLUE,
                      border=(255, 255, 255), sc=0.6 + 0.4 * eo(p))
    tr = x.wt(1, 0) if len(x.sc["segs"]) > 1 else x.wt(0, 3)
    if t > tr:
        label(c, "원래 보내려던 건 다른 데이브", *cam.pt(540, 760), 52, fg=INK, bg=(255, 250, 200),
              sc=eback((t - tr) / 0.35))
    return c, (255, 236, 200), 0.05


def sc_last(t, x):
    A = x.sc["start"]
    msgs = chat_msgs(x)
    t2 = x.seg(1)[0]
    cam = Cam(z=lerp(1.0, 1.2, eio(t / x.dur)))
    shake(cam, t, t2, 12, 4)
    c = draw_bg("dusk", cam, pan=-200, darken=0.55)
    si = x.seg(1)[1]
    QUOTE_HIDDEN.add(si)
    cr = eo((t - x.wt(1, 3)) / 0.4) if t > x.wt(1, 3) else 0
    phone(c, *cam.pt(540, 650), 0.98, "엉뚱한 데이브", [(s, tx, ta - A) for s, tx, ta in msgs], t, crack=cr)
    if t > t2:
        place(c, cam, "angry", 160, 300, 280, sc=eback((t - t2) / 0.35), anchor="center")
    label(c, "마지막 답장", *cam.pt(820, 200), 56, fg=(255, 255, 255), bg=INK, border=(255, 255, 255),
          sc=eback((t - 0.1) / 0.35), rot=4)
    return c, (200, 200, 230), 0.08


def sc_clue(t, x):
    cam = Cam(z=lerp(1.0, 1.12, eio(t / x.dur)))
    c = draw_bg("living", cam, pan=lerp(-200, -340, eio(t / x.dur)))
    place(c, cam, "tv", 540, 1350, 640, shadow=True)
    for k in range(4):
        q = (t * 0.8 + k * 0.25) % 1
        bigtext(c, "ㅋ", *cam.pt(820 + 60 * math.sin(k * 2 + t), 900 - 400 * q), 70, (255, 140, 40), -1, 1)
    tj = x.wt(0, 1)
    if t > tj:
        label(c, "진짜 데이브", *cam.pt(780, 520), 62, fg=(255, 255, 255), bg=BLUE, border=(255, 255, 255),
              sc=eback((t - tj) / 0.35), rot=4)
    tm = x.wt(0, 6)
    if t > tm:
        # stamp
        p = cl((t - tm) / 0.18)
        lay = Image.new("RGBA", (640, 200), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        d.rounded_rectangle([8, 8, 632, 192], radius=24, outline=RED + (235,), width=12)
        f = font(96)
        s = "아무것도 모름"
        l, tt, r, b = d.textbbox((0, 0), s, font=f)
        d.text((320 - (r - l) / 2 - l, 100 - (b - tt) / 2 - tt), s, font=f, fill=RED + (235,))
        paste_layer(c, lay, 300, 330, lerp(2.2, 1.0, eo(p)), -8, cl(p * 2))
    if len(x.sc["segs"]) > 1:
        t2 = x.seg(1)[0]
        if t > t2 - 0.1:
            p = eback((t - t2 + 0.1) / 0.4)
            r = 230 * p
            cx, cy = 290, 760
            inset = Image.new("RGBA", (VW, VH), (0, 0, 0, 0))
            d = ImageDraw.Draw(inset)
            d.ellipse([cx - r - 10, cy - r - 10, cx + r + 10, cy + r + 10], fill=(255, 255, 255))
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 220, 170))
            c.alpha_composite(inset)
            if p > 0.3:
                wl = 40 * math.sin(t * 2)
                place(c, Cam(), "lady", cx + wl, cy + r * 0.85, r * 1.55)
                label(c, "산책 좀 길게 함", cx, cy + r + 50, 46, sc=p)
    return c, (255, 236, 205), 0.05


def sc_poll(t, x):
    cam = Cam(z=lerp(1.0, 1.06, eio(t / x.dur)))
    c = draw_bg("living", cam, pan=200, darken=0.45)
    tw = x.wt(0, 5)
    tip = math.sin(t * 2.2) * 9 if t > tw else 6 * eo(t / 0.6)
    lay = SPR["scale"]
    place(c, cam, "scale", 540, 900, 600, sc=eback(t / 0.5), rot=tip * 0.0)
    # beam labels bob with the tip
    ly = 560
    label(c, "원래 금 간 부부", *cam.pt(250, ly - tip * 6), 52, fg=(255, 255, 255), bg=(120, 90, 200),
          border=(255, 255, 255), sc=eback((t - x.wt(0, 1)) / 0.35) if t > x.wt(0, 1) else 0, rot=-3)
    label(c, "남의 이름 넣은 문자", *cam.pt(820, ly + tip * 6), 52, fg=(255, 255, 255), bg=(255, 110, 60),
          border=(255, 255, 255), sc=eback((t - tw) / 0.35) if t > tw else 0, rot=3)
    vs = x.wt(0, 5) - 0.2
    bigtext(c, "VS", *cam.pt(540, 420), 110, YEL, vs, t, sfill=INK, stroke=10)
    if len(x.sc["segs"]) > 1:
        t2 = x.seg(1)[0]
        if t > t2:
            label(c, "누구 잘못? 댓글로 알려주세요!", VW / 2, 1000, 56, fg=INK, bg=YEL, border=INK,
                  sc=eback((t - t2) / 0.35) * (1 + 0.04 * math.sin(t * 6)))
    fo = cl((t - (x.dur - 0.5)) / 0.5)
    if fo > 0:
        c.alpha_composite(Image.new("RGBA", (VW, VH), (0, 0, 0, int(255 * fo))))
    return c, (230, 220, 255), 0.06


SCENE_FN = {"pool": sc_pool, "lady": sc_lady, "ask": sc_ask, "contact": sc_contact, "wrong": sc_wrong,
            "bomb": sc_bomb, "knew": sc_knew, "beer": sc_beer, "wife": sc_wife, "sorry": sc_sorry,
            "last": sc_last, "clue": sc_clue, "poll": sc_poll}


# ---------------- frame assembly ----------------
def title_band():
    band = Image.new("RGBA", (W, TOPH), (18, 20, 28, 255))
    d = ImageDraw.Draw(band)
    label(band, "실화 썰", W / 2, 70, 40, fg=INK, bg=YEL, border=YEL)
    for i, (s, sz, col) in enumerate([(TITLE[0], 76, (255, 255, 255)), (TITLE[1], 88, YEL)]):
        f = font(sz)
        l, t, r, b = d.textbbox((0, 0), s, font=f, stroke_width=4)
        d.text((W / 2 - (r - l) / 2 - l, [140, 245][i] - t), s, font=f, fill=col, stroke_width=4,
               stroke_fill=(0, 0, 0))
    d.rectangle([0, TOPH - 6, W, TOPH], fill=YEL)
    return band


BAND = None


def scene_frame(k, t, fi):
    sc = SCENES[k]
    x = Ctx(sc)
    img, tint, amt = SCENE_FN[sc["key"]](t, x)
    for ls, si in sc["segs"]:
        nxt = [l2 for l2, _ in sc["segs"] if l2 > ls]
        end = min(nxt) - 0.1 if nxt else sc["dur"] - 0.15
        if ls - 0.05 <= t < end and si not in QUOTE_HIDDEN:
            subtitle(img, si, t - ls)
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    if amt:
        a = a * (1 - amt) + a * (np.array(tint, np.float32) / 255.0) * amt
    a = a * (1 - 0.5 * VIG) + GRAIN[fi % len(GRAIN)]
    return np.clip(a, 0, 255).astype(np.uint8)


def hblur(arr, r):
    r = int(r)
    if r < 1:
        return arr
    cs = np.cumsum(np.pad(arr.astype(np.int32), ((0, 0), (r + 1, r), (0, 0)), mode="edge"), axis=1)
    return ((cs[:, 2 * r + 1:] - cs[:, :-2 * r - 1]) / (2 * r + 1)).astype(np.uint8)


def _prime_quotes():
    # run every scene once at t=0 so QUOTE_HIDDEN is filled before any subtitle is drawn
    for k, sc in enumerate(SCENES):
        SCENE_FN[sc["key"]](0.0, Ctx(sc))


def render(fi):
    global BAND
    if BAND is None:
        BAND = np.asarray(title_band().convert("RGB"))
        _prime_quotes()
    t = fi / FPS
    k = max(i for i, s in enumerate(SCENES) if s["start"] <= t + 1e-9)
    lt = t - SCENES[k]["start"]
    if k > 0 and lt < XF / 2:
        p = 0.5 + lt / XF
        a, b = scene_frame(k - 1, t - SCENES[k - 1]["start"], fi), scene_frame(k, lt, fi)
    elif k < len(SCENES) - 1 and SCENES[k]["dur"] - lt < XF / 2:
        p = 0.5 - (SCENES[k]["dur"] - lt) / XF
        a, b = scene_frame(k, lt, fi), scene_frame(k + 1, 0.0, fi)
    else:
        p = None
        v = scene_frame(k, lt, fi)
    if p is not None:
        off = int(eio(p) * VW)
        v = hblur(np.concatenate([a, b], axis=1)[:, off:off + VW], 55 * math.sin(math.pi * p))
    return np.concatenate([BAND, v], axis=0)


# ---------------- audio ----------------
SR = 44100


def synth():
    n = int((TOTAL + 1) * SR)
    sfx, mus = np.zeros(n), np.zeros(n)

    def add(buf, at, sig):
        i = int(at * SR)
        if 0 <= i < n:
            buf[i:i + len(sig)] += sig[: n - i]

    tt = lambda d: np.arange(int(d * SR)) / SR

    def pop(f0=800, d=0.12, g=0.22):
        x = tt(d)
        return g * np.sin(2 * np.pi * np.cumsum(f0 * np.exp(-x * 18) + f0 * 0.5) / SR) * np.exp(-x * 30)

    def whoosh(d=0.32, g=0.2):
        x = np.random.RandomState(3).randn(int(d * SR))
        y = np.convolve(x, np.ones(25) / 25, "same")
        return g * 3 * y * np.sin(np.linspace(0, np.pi, len(y))) ** 2

    def ding(f0=1320, g=0.14, d=0.8):
        x = tt(d)
        return g * (np.sin(2 * np.pi * f0 * x) + 0.4 * np.sin(2 * np.pi * f0 * 2.01 * x)) * np.exp(-x * 5)

    def buzz(g=0.2):
        x = tt(0.35)
        return g * np.sign(np.sin(2 * np.pi * 150 * x)) * 0.4 * (np.sin(2 * np.pi * 14 * x) > 0)

    def msgin(g=0.16):
        return np.concatenate([ding(1760, g, 0.12), ding(2350, g, 0.5)])

    def thud(g=0.55):
        x = tt(0.35)
        return g * np.sin(2 * np.pi * (55 + 90 * np.exp(-x * 25)) * x) * np.exp(-x * 9)

    def boom(g=0.5):
        x = tt(0.9)
        nz = np.convolve(np.random.RandomState(2).randn(len(x)), np.ones(60) / 60, "same")
        return g * (np.sin(2 * np.pi * (45 + 60 * np.exp(-x * 8)) * x) + 2 * nz) * np.exp(-x * 4)

    def crack(g=0.3):
        x = np.random.RandomState(8).randn(int(0.3 * SR))
        return g * x * np.exp(-np.arange(len(x)) / SR * 14)

    for k in range(1, len(SCENES)):
        add(sfx, SCENES[k]["start"] - XF / 2, whoosh())
    S = {s["key"]: s for s in SCENES}
    X = {k: Ctx(v) for k, v in S.items()}
    A = lambda key, j, w=0: S[key]["start"] + X[key].wt(j, w)
    add(sfx, A("pool", 0, 1), pop(700))
    add(sfx, A("pool", 0, 2), pop(500, 0.2, 0.3))
    add(sfx, A("lady", 0, 4), pop(900))
    add(sfx, A("ask", 0, 5), ding(1568, 0.12))
    add(sfx, A("contact", 0, 4), thud())
    add(sfx, A("contact", 0, 4) + 0.05, ding(660, 0.12))
    add(sfx, S["wrong"]["start"] + 0.2, whoosh(1.0, 0.18))
    add(sfx, A("wrong", 0, 1), pop(300, 0.25, 0.3))
    add(sfx, A("bomb", 0, 2), boom())
    for side, _, ta in chat_msgs(None):
        if side == "in" and ta > 0:
            add(sfx, ta, msgin())
            add(sfx, ta + 0.02, buzz(0.12))
    add(sfx, S["knew"]["start"] + X["knew"].seg(1)[0], boom(0.6))
    for j in range(8):
        add(sfx, S["beer"]["start"] + 0.3 + j * 0.5, buzz(0.07))
    add(sfx, S["wife"]["start"] + X["wife"].wt(0, 6) - 0.1, msgin(0.2))
    add(sfx, S["wife"]["start"] + X["wife"].seg(1)[0], thud(0.6))
    add(sfx, S["sorry"]["start"] + 0.1, whoosh(0.6, 0.25))
    add(sfx, A("last", 1, 3), crack())
    add(sfx, A("clue", 0, 6), thud())
    add(sfx, A("poll", 0, 5) - 0.2, pop(500, 0.2, 0.3))
    add(sfx, S["poll"]["start"] + X["poll"].seg(1)[0], ding(1046, 0.15))

    # quirky pizzicato BGM; tense minor during the reply bomb/rage
    bpm = 116
    beat = 60 / bpm
    major = [[60, 64, 67], [57, 60, 64], [53, 57, 60], [55, 59, 62]]
    minor = [[57, 60, 64], [53, 57, 60], [52, 56, 59], [57, 60, 64]]
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    tense0, tense1 = S["bomb"]["start"], S["beer"]["start"]
    last0, last1 = S["last"]["start"], S["clue"]["start"]

    def pluck(f, d=0.35, g=0.06):
        x = tt(d)
        return g * (np.sin(2 * np.pi * f * x) + 0.3 * np.sin(2 * np.pi * 2 * f * x)) * np.exp(-x * 9)

    b = 0
    while b * beat < TOTAL - 1.0:
        at = b * beat
        tense = tense0 <= at < tense1 or last0 <= at < last1
        ch = (minor if tense else major)[(b // 4) % 4]
        add(mus, at, pluck(hz(ch[0] - 12), 0.5, 0.09))
        if b % 2 == 1:
            for m in ch:
                add(mus, at, pluck(hz(m + 12), 0.25, 0.032))
        add(mus, at + beat / 2, pluck(hz(ch[b % 3] + 12), 0.2, 0.028))
        if tense and b % 2 == 0:
            add(mus, at, pluck(hz(ch[0] - 24), 0.3, 0.12))
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
                           "-crf", "25", "-pix_fmt", "yuv420p", os.path.join(tmp, "v.mp4")], stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for i, fr in enumerate(pool.imap(render, range(NFRAMES), chunksize=3)):
            ff.stdin.write(fr.tobytes())
            if i % 150 == 0:
                print(f"frame {i}/{NFRAMES}", flush=True)
    ff.stdin.close()
    ff.wait()
    ins, flt = [], []
    n = len(SEGS)
    for k, s in enumerate(SEGS):
        ins += ["-i", os.path.join(TTS, f"{k}.mp3")]
        ms = int(s["abs"] * 1000)
        flt.append(f"[{k + 1}:a]aresample=44100,adelay={ms}|{ms}[v{k}]")
    flt.append("".join(f"[v{k}]" for k in range(n)) + f"amix=inputs={n}:normalize=0,asplit[voice][key]")
    flt.append(f"[{n + 2}:a]anull[m0];[m0][key]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=300[mus]")
    flt.append(f"[voice][{n + 1}:a][mus]amix=inputs=3:normalize=0,loudnorm=I=-14:TP=-1.5[aout]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(tmp, "v.mp4"), *ins,
                    "-i", os.path.join(tmp, "sfx.wav"), "-i", os.path.join(tmp, "mus.wav"),
                    "-filter_complex", ";".join(flt), "-map", "0:v", "-map", "[aout]", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", OUT], check=True)
    print("done", OUT, f"{TOTAL:.2f}s")


if __name__ == "__main__":
    main()
