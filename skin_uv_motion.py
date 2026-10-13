#!/usr/bin/env python3
"""Skin cross-section motion graphic (no text): UV rays descend onto the skin,
melanocytes in the basal layer activate and release melanin granules into the
epidermis, and the surface gradually darkens. Seamless 8 s loop.

usage: python3 skin_uv_motion.py output.mp4 [--fps 30] [--frames-only DIR]
"""
import argparse, math, os, random, subprocess, tempfile
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

BG = (0xFD, 0xF3, 0xEC)
SKIN = (0xF2, 0xC9, 0xA8)
MEL = (0x6B, 0x3F, 0x1D)
UV = (0xFF, 0xD8, 0x4D)

W, H = 1920, 1080
SS = 2                        # supersampling factor
DUR = 8.0                     # loop length (s)

X0, X1, YBOT = 180, 1740, 930  # slab extents
SC = 14                        # stratum corneum thickness
MX = [310 + 260 * i for i in range(6)]  # melanocyte x positions (ridge bottoms)


def mix(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def ease_out(t):
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


def ys(x):
    """Skin surface."""
    return 468 + 5 * np.sin(x / 83) + 3 * np.sin(x / 37 + 1.3)


def yb(x):
    """Epidermis / dermis boundary (rete ridges, deepest under melanocytes)."""
    return 600 + 50 * ((1 + np.cos(2 * np.pi * (x - MX[0]) / 260)) / 2) ** 1.5


def S(p):
    return (p[0] * SS, p[1] * SS)


def bez(p0, p1, p2, t):
    return ((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
            (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1])


# ---------------------------------------------------------------- static scene
def slab_poly(top_fn, bottom=YBOT, r=46):
    xs = np.linspace(X0, X1, 400)
    pts = [(x, float(top_fn(x))) for x in xs]
    for a in np.linspace(0, 90, 12):
        pts.append((X1 - r + r * math.cos(math.radians(a)), bottom - r + r * math.sin(math.radians(a))))
    for a in np.linspace(90, 180, 12):
        pts.append((X0 + r + r * math.cos(math.radians(a)), bottom - r + r * math.sin(math.radians(a))))
    return pts


def epi_poly():
    xs = np.linspace(X0, X1, 400)
    return [(x, float(ys(x))) for x in xs] + [(x, float(yb(x))) for x in xs[::-1]]


def build_static(rng):
    big = (W * SS, H * SS)
    img = Image.new("RGBA", big, BG + (255,))

    # soft shadow under the slab
    sh = Image.new("RGBA", big, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([S((X0 + 30, YBOT - 30)), S((X1 - 30, YBOT + 26))],
                                         radius=40 * SS, fill=mix(BG, MEL, 0.22) + (150,))
    img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(22 * SS)))

    slab_mask = Image.new("L", big, 0)
    ImageDraw.Draw(slab_mask).polygon([S(p) for p in slab_poly(ys)], fill=255)
    epi_mask = Image.new("L", big, 0)
    ImageDraw.Draw(epi_mask).polygon([S(p) for p in epi_poly()], fill=255)
    derm_mask = ImageChops.subtract(slab_mask, epi_mask)

    # dermis
    derm = Image.new("RGBA", big, mix(SKIN, BG, 0.42) + (255,))
    dd = ImageDraw.Draw(derm)
    fiber = mix(SKIN, MEL, 0.14)
    for _ in range(46):                                  # collagen fibres
        y0 = rng.uniform(680, YBOT - 20)
        x0 = rng.uniform(X0 - 100, X1)
        ln = rng.uniform(160, 360)
        ph, amp = rng.uniform(0, 6.28), rng.uniform(4, 9)
        pts = [S((x0 + k, y0 + amp * math.sin(k / 26 + ph) + k * 0.05)) for k in np.linspace(0, ln, 40)]
        dd.line(pts, fill=fiber + (95,), width=int(3 * SS), joint="curve")
    vessel = mix(SKIN, MEL, 0.26)
    for x in MX[:-1]:                                    # capillary loops in the papillae
        cx = x + 130
        top = float(yb(cx)) + 14
        loop = [S((cx - 14, top + 80))] + [S((cx + 14 * math.cos(a), top + 14 - 14 * math.sin(a)))
                                           for a in np.linspace(math.pi, 0, 18)] + [S((cx + 14, top + 80))]
        loop[1:1] = [S((cx - 14, top + 14))]
        dd.line(loop, fill=vessel + (170,), width=int(4 * SS), joint="curve")
    for cx, cy, rx in ((520, 860, 46), (1240, 850, 54)):  # deep vessels (cut)
        dd.ellipse([S((cx - rx, cy - rx * 0.55)), S((cx + rx, cy + rx * 0.55))], fill=mix(SKIN, BG, 0.15) + (255,),
                   outline=vessel + (200,), width=int(4 * SS))
    img.paste(derm, (0, 0), derm_mask)

    # epidermis: base tone + keratinocytes
    epi = Image.new("RGBA", big, mix(SKIN, MEL, 0.05) + (255,))
    ed = ImageDraw.Draw(epi)
    targets = []
    rows = 5
    for r in range(rows):
        cw = 46 + 13 * r
        off = (r % 2) * cw / 2
        x = X0 - cw + off
        while x < X1 + cw:
            top, bot = float(ys(x)) + SC, float(yb(x))
            v = (r + 0.5) / rows
            yc = bot + (top - bot) * v
            hh = (bot - top) / rows * 0.88 / 2
            ww = cw * 0.9 / 2
            skip = r == 0 and min(abs(x - m) for m in MX) < 34
            if not skip:
                ed.rounded_rectangle([S((x - ww, yc - hh)), S((x + ww, yc + hh))], radius=min(ww, hh) * SS,
                                     fill=mix(SKIN, BG, 0.22 - 0.03 * r) + (255,),
                                     outline=mix(SKIN, MEL, 0.16) + (255,), width=int(2 * SS))
                if r < 4:
                    nw, nh = ww * 0.36, hh * 0.46
                    ed.ellipse([S((x - nw, yc - nh)), S((x + nw, yc + nh))], fill=mix(SKIN, MEL, 0.2) + (255,))
                    if r >= 1:
                        targets.append((x, yc - nh - 2, ww, r))
            x += cw
    # stratum corneum
    xs = np.linspace(X0, X1, 400)
    ed.polygon([S((x, float(ys(x)))) for x in xs] + [S((x, float(ys(x)) + SC)) for x in xs[::-1]],
               fill=mix(SKIN, MEL, 0.1) + (255,))
    for k in range(3):
        ed.line([S((x, float(ys(x)) + 4 + 4 * k)) for x in xs], fill=mix(SKIN, MEL, 0.17) + (150,),
                width=int(1.5 * SS))
    img.paste(epi, (0, 0), epi_mask)

    d = ImageDraw.Draw(img)
    # basement membrane + surface line
    d.line([S((x, float(yb(x)))) for x in xs], fill=mix(SKIN, MEL, 0.32) + (255,), width=int(3 * SS), joint="curve")
    d.line([S((x, float(ys(x)))) for x in xs], fill=mix(SKIN, MEL, 0.3) + (255,), width=int(3 * SS), joint="curve")

    base = img.resize((W, H), Image.LANCZOS).convert("RGB")
    epi1 = np.asarray(epi_mask.resize((W, H), Image.LANCZOS)).astype(np.float32) / 255
    slab1 = np.asarray(slab_mask.resize((W, H), Image.LANCZOS)).astype(np.float32) / 255
    return base, epi1, slab1, targets


def build_maps(epi1):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    s, b = ys(xx), yb(xx)
    v = np.clip((yy - s) / (b - s), 0, 1)
    # darkening strength: strongest at the surface, weaker toward the basal layer
    dark = epi1 * (0.62 - 0.36 * v)
    # UV attenuation: full in air, fading through epidermis, gone in dermis
    att = np.where(yy < s, 1.0, 0.8 - 0.45 * v)
    below = np.clip((yy - b) / 50, 0, 1)
    att = np.where(yy > b, 0.35 * (1 - below), att)
    att = np.clip(att, 0, 1)
    return dark[..., None], att.astype(np.float32)


# --------------------------------------------------------------- actors
def build_actors(rng, targets):
    mels = []
    order = [0, 3, 1, 4, 2, 5]
    for i, x in enumerate(MX):
        body = (x, float(yb(x)) - 21)
        dends = []
        for ang in (-50 + rng.uniform(-8, 8), 4 + rng.uniform(-8, 8), 54 + rng.uniform(-8, 8)):
            a = math.radians(ang)
            L = rng.uniform(68, 92)
            dirv = (math.sin(a), -math.cos(a))
            perp = (-dirv[1], dirv[0])
            bend = rng.uniform(-16, 16)
            p2 = (body[0] + dirv[0] * L, body[1] + dirv[1] * L)
            p1 = (body[0] + dirv[0] * L * 0.5 + perp[0] * bend, body[1] + dirv[1] * L * 0.5 + perp[1] * bend)
            dends.append((body, p1, p2))
        t0 = 0.25 + 0.14 * order[i]          # ray launch
        mels.append(dict(body=body, dends=dends, t0=t0, hit=t0 + 1.55))

    theta = math.radians(13)
    dirv = (math.sin(theta), math.cos(theta))
    rays = []
    for m in mels:
        tgt = m["body"]
        start = (tgt[0] - dirv[0] * 820, tgt[1] - dirv[1] * 820)
        # param where the ray crosses the surface
        sh = next(s for s in np.linspace(0, 1, 2000)
                  if start[1] + (tgt[1] - start[1]) * s >= ys(start[0] + (tgt[0] - start[0]) * s))
        rays.append(dict(a=start, b=tgt, t0=m["t0"], s_hit=float(sh), te=4.85 + (m["t0"] - 0.25) * 0.8))

    parts = []
    for m in mels:
        near = [t for t in targets if abs(t[0] - m["body"][0]) < 128]
        rng.shuffle(near)
        for k in range(15):
            tx, ty, ww, r = near[k % len(near)]
            tgt = (tx + rng.uniform(-ww * 0.45, ww * 0.45), ty + rng.uniform(-3, 2))
            dend = m["dends"][k % 3]
            start = (m["body"][0] + rng.uniform(-8, 8), m["body"][1] + rng.uniform(-6, 6))
            parts.append(dict(src=start, dend=dend, tgt=tgt,
                              t=m["hit"] + 0.55 + 0.17 * k + rng.uniform(0, 0.12),
                              dur=rng.uniform(1.25, 1.6), r=rng.uniform(4.2, 6.6), ph=rng.uniform(0, 6.28)))
    return mels, rays, parts


def part_pos(p, u):
    d0, d1, d2 = p["dend"]
    if u < 0.45:
        q = u / 0.45
        tip = bez(p["src"], d1, d2, q)
        return tip
    q = (u - 0.45) / 0.55
    ctrl = (d2[0] + (p["tgt"][0] - d2[0]) * 0.2, min(d2[1], p["tgt"][1]) - 18)
    return bez(d2, ctrl, p["tgt"], q)


# --------------------------------------------------------------- per frame
def envelope(t):
    """Global return-to-rest factor so the loop closes seamlessly."""
    return 1 - ease_out((t - 6.25) / 1.6)


def render(t):
    G = STATE
    env = envelope(t)
    dk = ease_out((t - 2.6) / 3.2) * env
    arr = G["base_np"] + (np.array(MEL, np.float32) - G["base_np"]) * G["dark"] * dk
    frame = Image.fromarray(arr.clip(0, 255).astype(np.uint8)).convert("RGBA")

    # ---- rays
    big = (W * SS, H * SS)
    rl = Image.new("RGBA", big, UV + (0,))
    rd = ImageDraw.Draw(rl)
    gl = Image.new("RGBA", (W // 4, H // 4), UV + (0,))
    gd = ImageDraw.Draw(gl)
    for ry in G["rays"]:
        tip = ease_out((t - ry["t0"]) / 1.75)
        if tip <= 0:
            continue
        tail = ease_out((t - ry["te"]) / 1.2)
        if tail >= 0.999:
            continue
        a, b = ry["a"], ry["b"]
        P = lambda s: (a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s)
        s0, s1 = tail * tip, tip
        if s1 - s0 < 0.002:
            continue
        alpha = 1 - tail ** 2
        p0, p1 = P(s0), P(s1)
        gd.line([(p0[0] / 4, p0[1] / 4), (p1[0] / 4, p1[1] / 4)], fill=UV + (int(190 * alpha),), width=12)
        rd.line([S(p0), S(p1)], fill=UV + (int(120 * alpha),), width=int(30 * SS))
        rd.line([S(p0), S(p1)], fill=UV + (int(255 * alpha),), width=int(12 * SS))
        for e in (S(p1),):
            rr = 9 * SS
            rd.ellipse([e[0] - rr, e[1] - rr, e[0] + rr, e[1] + rr], fill=UV + (int(255 * alpha),))
        # travelling photons once the beam is established
        est = ease_out((t - ry["t0"] - 0.6) / 0.8) * alpha
        if est > 0:
            light = mix(UV, (255, 255, 255), 0.6)
            for j in range(5):
                f = ((t * 0.55 + j / 5 + ry["t0"]) % 1.0)
                s = s0 + (s1 - s0) * f
                if s > s1 - 0.02:
                    continue
                q0, q1 = P(s), P(min(s + 0.035, s1))
                rd.line([S(q0), S(q1)], fill=light + (int(230 * est * math.sin(math.pi * f)),), width=int(5 * SS))
    rl = rl.resize((W, H), Image.LANCZOS)
    gl = gl.filter(ImageFilter.GaussianBlur(5)).resize((W, H), Image.BICUBIC)
    for layer in (gl, rl):
        a = np.asarray(layer).astype(np.float32)
        a[..., 3] *= G["att"]
        frame = Image.alpha_composite(frame, Image.fromarray(a.astype(np.uint8)))

    # ---- surface splashes, melanocytes, particles
    ml = Image.new("RGBA", big, MEL + (0,))
    md = ImageDraw.Draw(ml)
    for ry in G["rays"]:
        th = ry["t0"] + 1.75 * (1 - (1 - ry["s_hit"]) ** (1 / 3))   # time the tip crosses the surface
        e = (t - th) / 0.9
        if 0 <= e <= 1:
            hp = (ry["a"][0] + (ry["b"][0] - ry["a"][0]) * ry["s_hit"], ry["a"][1] + (ry["b"][1] - ry["a"][1]) * ry["s_hit"])
            k = ease_out(e)
            rx, ryy = (12 + 52 * k) * SS, (4 + 13 * k) * SS
            c = S(hp)
            md.ellipse([c[0] - rx, c[1] - ryy, c[0] + rx, c[1] + ryy], outline=UV + (int(255 * (1 - e)),),
                       width=int(4 * SS))

    for m in G["mels"]:
        act = ease_out((t - m["hit"]) / 0.9) * env
        col = mix(SKIN, MEL, 0.34 + 0.4 * act)
        bx, by = m["body"]
        swell = 1 + 0.1 * act
        for (p0, p1, p2) in m["dends"]:
            n = 26
            for k in range(n + 1):
                q = k / n
                x, y = bez(p0, p1, p2, q)
                rr = (8.5 - 5.5 * q) * SS * (1 + 0.08 * act)
                md.ellipse([x * SS - rr, y * SS - rr, x * SS + rr, y * SS + rr], fill=col + (255,))
        rx, ry_ = 24 * swell, 18 * swell
        md.ellipse([S((bx - rx, by - ry_)), S((bx + rx, by + ry_))], fill=col + (255,),
                   outline=mix(col, MEL, 0.35) + (255,), width=int(2 * SS))
        md.ellipse([S((bx - 9, by - 7)), S((bx + 9, by + 7))], fill=mix(SKIN, MEL, 0.62 + 0.3 * act) + (255,))
        # UV absorption ring
        e = (t - m["hit"]) / 1.1
        if 0 <= e <= 1:
            k = ease_out(e)
            rr = (26 + 46 * k)
            md.ellipse([S((bx - rr, by - rr * 0.8)), S((bx + rr, by + rr * 0.8))],
                       outline=UV + (int(255 * (1 - e) ** 1.5),), width=int((6 - 3 * k) * SS))

    for p in G["parts"]:
        age = t - p["t"]
        if age < 0:
            continue
        u = ease_out(age / p["dur"])
        pop = ease_out(age / 0.35)
        fade = ease_out((t - 6.25 - (p["ph"] % 1) * 0.25) / 1.3)
        alpha = (1 - fade)
        if alpha <= 0.01:
            continue
        x, y = part_pos(p, u)
        y -= 16 * fade
        wob = 1.2 * math.sin(t * 2.4 + p["ph"]) * u
        x += wob
        r = p["r"] * pop * (1 - 0.45 * fade)
        if u < 0.97:
            for g in (1, 2, 3):
                gx, gy = part_pos(p, max(0.0, u - 0.035 * g))
                gr = r * (1 - 0.2 * g)
                md.ellipse([S((gx - gr, gy - gr)), S((gx + gr, gy + gr))],
                           fill=MEL + (int(70 * alpha * (1 - g / 4) * (1 - u)),))
        md.ellipse([S((x - r, y - r)), S((x + r, y + r))], fill=MEL + (int(240 * alpha),))
        hr = r * 0.35
        md.ellipse([S((x - r * 0.35 - hr, y - r * 0.35 - hr)), S((x - r * 0.35 + hr, y - r * 0.35 + hr))],
                   fill=mix(MEL, SKIN, 0.4) + (int(200 * alpha),))

    # dendrites/body/particles live inside the slab only
    ml = ml.resize((W, H), Image.LANCZOS)
    a = np.asarray(ml).astype(np.float32)
    a[..., 3] *= G["slab"]
    frame = Image.alpha_composite(frame, Image.fromarray(a.astype(np.uint8)))
    return frame.convert("RGB")


STATE = {}


def setup():
    rng = random.Random(7)
    base, epi1, slab1, targets = build_static(rng)
    dark, att = build_maps(epi1)
    mels, rays, parts = build_actors(rng, targets)
    STATE.update(base_np=np.asarray(base).astype(np.float32), dark=dark, att=att, slab=slab1,
                 mels=mels, rays=rays, parts=parts)


def _job(args):
    i, fps, outd = args
    render(i / fps).save(os.path.join(outd, f"{i:04d}.png"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dst")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--frames-only", help="write sample PNGs at these comma-separated times instead")
    a = ap.parse_args()
    setup()
    if a.frames_only:
        os.makedirs(a.dst, exist_ok=True)
        for ts in a.frames_only.split(","):
            render(float(ts)).save(os.path.join(a.dst, f"t{float(ts):04.1f}.png"))
        return
    n = int(DUR * a.fps)
    with tempfile.TemporaryDirectory() as outd:
        with Pool() as pool:
            pool.map(_job, [(i, a.fps, outd) for i in range(n)], chunksize=4)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(a.fps), "-i", os.path.join(outd, "%04d.png"),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-movflags", "+faststart", a.dst],
                       check=True)


if __name__ == "__main__":
    main()
