#!/usr/bin/env python3
"""Tape-measure motion graphic: tracks the yellow tape in a video and draws an
animated dimension line that grows with the tape.

usage: python3 measure_overlay.py input.mp4 output.mp4 [--cm 180]
"""
import argparse, glob, math, os, subprocess, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ACCENT = (255, 61, 110)      # line color
INK = (255, 255, 255)
SS = 2                       # supersampling factor
OFFSET = 52                  # dimension line distance from the tape (px)
FONT = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"


def ease_out(t):
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


def track(frames):
    """Per frame: (start, tip) points of the yellow tape, or None."""
    raw = []
    for p in frames:
        a = np.asarray(Image.open(p).convert("RGB")).astype(int)
        r, g, b = a[..., 0], a[..., 1], a[..., 2]
        m = (r > 170) & (g > 140) & (b < 90) & (r - b > 110)
        ys, xs = np.nonzero(m)
        if len(xs) < 400:
            raw.append(None)
            continue
        pts = np.stack([xs, ys], 1).astype(float)
        c = pts.mean(0)
        u, s, vt = np.linalg.svd(pts - c, full_matrices=False)
        d = vt[0] if vt[0][0] > 0 else -vt[0]
        t = (pts - c) @ d
        # robust ends along the tape axis
        raw.append((c + d * np.percentile(t, 0.5), c + d * np.percentile(t, 99.7)))
    # smooth (moving average over valid neighbours)
    out = []
    for i, v in enumerate(raw):
        if v is None:
            out.append(None)
            continue
        win = [raw[j] for j in range(max(0, i - 2), min(len(raw), i + 3)) if raw[j] is not None]
        out.append((np.mean([w[0] for w in win], 0), np.mean([w[1] for w in win], 0)))
    return out


def font(sz):
    return ImageFont.truetype(FONT, sz)


def draw_frame(base, tr, i, first, last_move, total_cm, full_len):
    W, H = base.size
    layer = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if tr is None or i < first:
        return base
    S, T = tr
    S = np.array(S) * SS
    T = np.array(T) * SS
    v = T - S
    L = np.linalg.norm(v)
    if L < 8 * SS:
        return base
    u = v / L
    n = np.array([u[1], -u[0]])          # normal pointing "up" for a left->right tape
    if n[1] > 0:
        n = -n
    A = S + n * OFFSET * SS
    B = T + n * OFFSET * SS

    # intro: line wipes in from the start, caps pop in
    age = (i - first) / 8
    pop = ease_out(age)
    col = ACCENT + (255,)
    w = int(4 * SS)
    # extension lines (dashed)
    for P, Q in ((S, A), (T, B)):
        seg = Q - P
        ln = np.linalg.norm(seg)
        k = 0
        while k < ln * pop:
            a0 = P + seg / ln * k
            a1 = P + seg / ln * min(k + 6 * SS, ln * pop)
            d.line([tuple(a0), tuple(a1)], fill=ACCENT + (170,), width=int(1.6 * SS))
            k += 11 * SS
    # main line
    d.line([tuple(A), tuple(B)], fill=col, width=w)
    # ruler ticks every 20px of tape, longer every 100
    step = 20 * SS
    k = 0
    while k <= L:
        big = (k // step) % 5 == 0
        p = A + u * k
        ln_ = (11 if big else 6) * SS
        d.line([tuple(p), tuple(p - n * ln_)], fill=ACCENT + (255 if big else 190,), width=int(1.8 * SS))
        k += step
    # end caps
    for P in (A, B):
        d.line([tuple(P + n * 13 * SS), tuple(P - n * 13 * SS)], fill=col, width=w)
    r = 6 * SS * pop
    d.ellipse([*(S - r), *(S + r)], fill=col)
    d.ellipse([*(T - r), *(T + r)], fill=col)

    # glow
    glow = layer.filter(ImageFilter.GaussianBlur(7 * SS))
    glow = Image.eval(glow, lambda x: x)  # keep as is
    comp = Image.alpha_composite(glow, layer)

    # label: counts with the tape, pops when it stops
    cm = total_cm * (L / SS / full_len)
    if i >= last_move:
        cm = total_cm
    txt = f"{cm:,.0f} cm"
    settle = ease_out((i - last_move) / 10) if i >= last_move else 0
    scale = 1 + 0.12 * math.sin(settle * math.pi) if settle < 1 else 1
    f = font(int(30 * SS * scale))
    tmp = ImageDraw.Draw(comp)
    bb = tmp.textbbox((0, 0), txt, font=f)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    padx, pady = 20 * SS, 12 * SS
    mid = (A + B) / 2 + n * (38 * SS)
    box = [mid[0] - tw / 2 - padx, mid[1] - th / 2 - pady, mid[0] + tw / 2 + padx, mid[1] + th / 2 + pady]
    sh = Image.new("RGBA", comp.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([b + (3 * SS if j > 1 else 0) for j, b in enumerate(box)],
                                         radius=(th + 2 * pady) / 2, fill=(0, 0, 0, 90))
    comp = Image.alpha_composite(comp, sh.filter(ImageFilter.GaussianBlur(6 * SS)))
    dd = ImageDraw.Draw(comp)
    dd.rounded_rectangle(box, radius=(th + 2 * pady) / 2, fill=ACCENT + (255,))
    dd.text((mid[0] - tw / 2 - bb[0], mid[1] - th / 2 - bb[1]), txt, font=f, fill=INK)

    comp = comp.resize((W, H), Image.LANCZOS)
    return Image.alpha_composite(base.convert("RGBA"), comp).convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--cm", type=float, default=180, help="label value at full tape extension")
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        raw, outd = os.path.join(tmp, "raw"), os.path.join(tmp, "out")
        os.makedirs(raw); os.makedirs(outd)
        subprocess.run(["ffmpeg", "-v", "error", "-i", a.src, os.path.join(raw, "%04d.png")], check=True)
        fps = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries",
                                       "stream=r_frame_rate", "-of", "csv=p=0", a.src]).decode().strip()
        frames = sorted(glob.glob(os.path.join(raw, "*.png")))
        tr = track(frames)
        valid = [i for i, t in enumerate(tr) if t is not None]
        first = valid[0]
        lens = [np.linalg.norm(tr[i][1] - tr[i][0]) if tr[i] is not None else 0 for i in range(len(tr))]
        full_len = float(np.median(lens[-10:]))
        # frame where the tape reaches ~97% of its final length = "stopped"
        last_move = next(i for i, l in enumerate(lens) if l >= 0.97 * lens[-1])
        for i, p in enumerate(frames):
            im = draw_frame(Image.open(p).convert("RGB"), tr[i], i, first, last_move, a.cm, full_len)
            im.save(os.path.join(outd, f"{i + 1:04d}.png"))
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", fps, "-i", os.path.join(outd, "%04d.png"),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", a.dst], check=True)


if __name__ == "__main__":
    main()
