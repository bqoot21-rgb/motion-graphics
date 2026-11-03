"""Crayon Case demo: score + foley + mix → mix.wav (48 kHz stereo). Everything is synthesized here (numpy), no samples.
Score: a slow music box in A minor that winds down and stops mid-phrase, a low drone, one low note under the pink.
Foley from events.json: crayon writing / lines / colouring, eraser, the stain's wet creep, the pink crayon, room tone, a clock.
Usage: python audio.py <project folder>   (LIB must point at the Lemo-Opuscar library for core/audio/sfx.py)"""
import json, os, sys
import numpy as np
LIB = os.environ.get('LIB', os.path.expanduser('~/lemo-opuscar'))
sys.path.insert(0, os.path.join(LIB, 'core', 'audio'))
from sfx import SR, t_, bp, lp, hp, noise, norm, brown, add, limit  # noqa: E402
import soundfile as sf  # noqa: E402

P = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
E = json.load(open(os.path.join(P, 'events.json')))
DUR = E['dur']
rng = np.random.default_rng(11)
N = int(DUR * SR)
music = np.zeros((N, 2)); foley = np.zeros((N, 2)); amb = np.zeros((N, 2))
mtof = lambda m: 440 * 2 ** ((m - 69) / 12)


# ——— instruments ———
def musicbox(f, v=1.0, d=3.2):
    """Comb tine: inharmonic partials, fast-decaying highs, a tiny pluck click."""
    tt = t_(d); x = np.zeros_like(tt)
    for k, (r, a, tau) in enumerate([(1, 1, 1.5), (2.76, .32, .45), (5.40, .12, .18), (8.9, .05, .08)]):
        x += a * np.sin(2 * np.pi * f * r * tt * (1 + .0015 * k)) * np.exp(-tt / tau)
    x += .5 * np.sin(2 * np.pi * f * 1.002 * tt) * np.exp(-tt / 1.3)   # second tine, slightly detuned
    click = hp(noise(.01), 3000) * np.exp(-t_(.01) / .002) * .25
    x[:len(click)] += click
    return x * np.minimum(1, tt / .002) * v


def reverb(x, secs=1.1, wet=.16):
    ir = rng.standard_normal(int(secs * SR)) * np.exp(-t_(secs) / (secs / 5)); ir = lp(ir, 3500); ir /= np.sqrt(np.sum(ir ** 2))
    from scipy.signal import fftconvolve
    out = np.stack([fftconvolve(x[:, c], np.roll(ir, 97 * c))[:len(x)] for c in range(2)], 1)
    return x + out * wet


# ——— score ———
# phrase A (first half of the theme), then it starts again and winds down: slower, flatter, and stops mid-phrase at 13.9 s
NOTES = [  # (time, midi, velocity, pitch factor)
    (1.00, 76, .9, 1), (2.05, 72, .75, 1), (3.10, 69, .8, 1), (4.15, 71, .7, 1),
    (5.20, 72, .75, 1), (5.75, 71, .6, 1), (6.30, 69, .7, 1), (7.45, 64, .75, 1),
    (8.60, 77, .8, 1), (9.70, 76, .7, 1), (10.75, 74, .7, 1), (11.45, 72, .65, .995),
    (12.25, 71, .6, .985), (13.20, 69, .5, .965),
    (26.00, 76, .6, 1), (27.10, 72, .5, .99), (28.30, 71, .42, .975),   # three broken notes at the end; never resolves
]
for t, m, v, pf in NOTES:
    add(music, musicbox(mtof(m) * pf, v), t, .14, pan=-.15 + .3 * ((m - 64) / 14))
# the mechanism running down: the last notes droop in pitch and a soft spring rattle stops it
rattle = bp(noise(.35), 900, 3000) * (rng.random(int(.35 * SR)) > .985) * np.exp(-t_(.35) / .12) * 2
add(music, rattle, 13.88, .12, .1)
music[int(13.95 * SR):int(15.5 * SR)] *= 0   # stopped mid-phrase: hard silence for the music

# low drone: A1 + A2 + a little E2, slow beating, filtered noise air; in at 5 s, gone in the silence, swelling under the stain
tt = t_(DUR)
drone = (np.sin(2 * np.pi * 55 * tt) * .55 + np.sin(2 * np.pi * 110.18 * tt) * .3 * (1 + .3 * np.sin(2 * np.pi * .11 * tt))
         + np.sin(2 * np.pi * 82.3 * tt) * .14 + lp(hp(noise(DUR), 60), 220) * .06)
g = np.interp(tt, [0, 5, 8.5, 13.7, 13.95, 15.6, 17.5, 22.6, 24.5, 27, 29], [0, 0, .7, .7, 0, 0, .75, 1.0, .65, .5, 0])
drone *= g
add(music, drone, 0, .16)
# one low note under the pink: a felt-muted bass, struck once
d = 4.0; tl = t_(d)
low = (np.sin(2 * np.pi * 55 * tl) + .4 * np.sin(2 * np.pi * 110 * tl) * np.exp(-tl / .6)) * np.exp(-tl / 1.8) * np.minimum(1, tl / .006)
add(music, low, 23.68, .32)
music = reverb(music, 1.3, .22)


# ——— foley ———
def crayon(d, v=1.0, lo=1200, hi=6000, strokes=2.6, grain=90, heavy=0.0):
    """Wax on paper: stick-slip grain (random micro-impulses) in a band, shaped into strokes."""
    tt = t_(d); n = len(tt)
    imp = (rng.random(n) < grain / SR) * rng.uniform(.4, 1, n)
    grit = np.convolve(imp, np.exp(-np.arange(200) / 30), 'same')
    x = bp(noise(d), lo, hi) * (.45 + 1.6 * grit)
    if heavy: x += bp(noise(d), 300, 1100) * heavy * (.6 + grit)
    ph = np.cumsum(np.full(n, strokes / SR) * (1 + .25 * np.sin(2 * np.pi * .7 * tt)))
    sw = np.clip(np.sin(np.pi * (ph % 1)), 0, 1) ** .7          # each stroke: press, drag, lift
    e = np.minimum(1, tt / .03) * np.minimum(1, (d - tt) / .06)
    return x * sw * e * v


def eraser(d, v=1.0):
    """Rubber on paper: low-mid friction in short back-and-forth bursts."""
    tt = t_(d); n = len(tt)
    x = bp(noise(d), 220, 1400) * .9 + bp(noise(d), 1400, 3200) * .25
    ph = (tt * 4.3) % 1
    sw = np.clip(np.sin(np.pi * ph), 0, 1) ** 1.6 * (.75 + .25 * np.sin(2 * np.pi * .4 * tt))
    chatter = 1 + .6 * (rng.random(n) < 300 / SR)
    e = np.minimum(1, tt / .05) * np.minimum(1, (d - tt) / .1)
    return x * sw * chatter * e * v


def brush_off(v=1.0):
    d = .45; tt = t_(d)
    return bp(noise(d), 1500, 7000) * np.sin(np.pi * tt / d) ** 2 * v


def stain(d, v=1.0):
    """A spill creeping through paper: slow low swell, a fine wet crackle, tiny drips."""
    tt = t_(d); n = len(tt)
    body = lp(brown(d), 520) * np.interp(tt, [0, d * .25, d * .8, d], [0, 1, .8, 0])
    crackle = hp(noise(d), 2500) * (rng.random(n) < 900 / SR) * .8
    crackle = lp(crackle, 7000) * np.interp(tt, [0, d * .3, d], [.2, 1, .3])
    x = norm(body) * .8 + crackle * .35
    for k in range(7):
        at = rng.uniform(.5, d - .5); dd = .12; td = t_(dd)
        drop = np.sin(2 * np.pi * (900 + 600 * rng.random()) * td * (1 + 2 * td)) * np.exp(-td / .02) * .25
        s = int(at * SR); x[s:s + len(drop)] += drop[:max(0, n - s)]
    return x * v


for e in E['ev']:
    t, ty, pan = e['t'], e['type'], e.get('pan', 0)
    if ty == 'write': add(foley, crayon(e['dur'], 1, 1500, 6500, strokes=4.2, grain=120), t, .5, pan)
    elif ty == 'line': add(foley, crayon(e['dur'], 1, 1100, 5000, strokes=1.0, grain=80), t, .24 if not e.get('soft') else .2, pan)
    elif ty == 'colour': add(foley, crayon(e['dur'], 1, 900, 4200, strokes=5.5, grain=70), t, .2, pan)
    elif ty == 'erase':
        add(foley, eraser(e["dur"]), t, .95, pan); add(foley, brush_off(), t + e['dur'] + .1, .25, pan)
    elif ty == 'stain': add(foley, stain(e['dur'] + .6), t, .5, 0)
    elif ty == 'pink': add(foley, crayon(e['dur'], 1, 700, 5200, strokes=6.5, grain=150, heavy=.6), t, .62, pan)

# room tone, faint wind, a distant clock (most audible in the silence)
add(amb, lp(brown(DUR), 260), 0, .05); add(amb, bp(brown(DUR), 200, 900) * (.5 + .5 * np.sin(2 * np.pi * .05 * tt)), 0, .02)
for s in range(1, int(DUR)):
    d = .03; tk = bp(noise(d), 2200, 5200) * np.exp(-t_(d) / .004)
    add(amb, tk, s + .02, .05 if not 13.9 < s < 15.6 else .1, .45)

mix = music * 1.0 + foley * 1.0 + amb
if os.environ.get('STEMS'):
    for nm, b in (('music', music), ('foley', foley), ('amb', amb)): sf.write(os.path.join(P, f'stem_{nm}.wav'), b.astype(np.float32), SR)
mix = np.stack([limit(mix[:, c], .9) for c in range(2)], 1)
mix[-int(.05 * SR):] *= np.linspace(1, 0, int(.05 * SR))[:, None]
sf.write(os.path.join(P, 'mix.wav'), mix.astype(np.float32), SR)
print('mix.wav', DUR, 's, peak', float(np.abs(mix).max()))
