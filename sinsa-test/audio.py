"""Crayon Case test "June 14th, 1998": narration + score + foley + mix → mix.wav (48 kHz stereo). Everything is synthesized here (numpy), no samples.
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
# music box: two slow phrases above ground, gone below the street; three broken notes at the door
NOTES = [(0.6, 76, .8, 1), (1.9, 72, .65, 1), (3.2, 69, .7, 1), (4.5, 71, .6, 1), (5.8, 72, .65, 1), (7.1, 71, .55, 1), (8.4, 69, .6, 1),
         (9.7, 77, .7, 1), (11.0, 76, .6, 1), (12.3, 74, .55, .99), (13.5, 72, .45, .97),
         (19.6, 76, .5, 1), (20.9, 72, .42, .99), (22.4, 71, .36, .975)]
for t, m, v, pf in NOTES:
    add(music, musicbox(mtof(m) * pf, v), t, .12, pan=-.15 + .3 * ((m - 64) / 14))
tt = t_(DUR)
drone = (np.sin(2 * np.pi * 55 * tt) * .55 + np.sin(2 * np.pi * 110.18 * tt) * .3 * (1 + .3 * np.sin(2 * np.pi * .11 * tt))
         + np.sin(2 * np.pi * 82.3 * tt) * .14 + lp(hp(noise(DUR), 60), 220) * .06)
drone *= np.interp(tt, [0, 12.5, 14.5, 18, 22, 24.5], [0, 0, .7, 1, .8, 0])
add(music, drone, 0, .17)
d = 4.0; tl = t_(d)
low = (np.sin(2 * np.pi * 55 * tl) + .4 * np.sin(2 * np.pi * 110 * tl) * np.exp(-tl / .6)) * np.exp(-tl / 1.8) * np.minimum(1, tl / .006)
add(music, low, 18.4, .3)
music = reverb(music, 1.3, .22)

# the match on TV: a stadium crowd through a small speaker; louder close-up, many TVs as we pull out, muffled through the ceiling below
def crowd(d, seed=0):
    r = np.random.default_rng(seed); n = len(t_(d)); tt2 = t_(d)
    x = bp(r.standard_normal(n), 350, 3200)
    sw = np.interp(tt2, np.arange(0, d + 1, .7), .55 + .45 * r.random(len(np.arange(0, d + 1, .7))))
    return x * lp(sw, 3)
tvA = crowd(DUR, 1); tvB = crowd(DUR, 2)
gA = np.interp(tt, [0, .4, 8.6, 13.2, 13.6, 24.5], [0, .5, .5, .3, 0, 0])
gB = np.interp(tt, [0, 8.6, 11, 13.2, 14.2, 24.5], [0, 0, .5, .45, 0, 0])
muff = lp(crowd(DUR, 3), 380, 4) * np.interp(tt, [0, 13.4, 14.4, 20.6, 21.2, 22.8, 24.5], [0, 0, .5, .5, 1.6, .5, .3])
amb[:, 0] += tvA * gA * .2 + tvB * gB * .2 * 1.2 + muff * .2
amb[:, 1] += tvA * gA * .2 + tvB * gB * .2 * .8 + muff * .2

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


vox = np.zeros((N, 2)); voice_at = []
for e in E['ev']:
    t, ty, pan = e['t'], e['type'], e.get('pan', 0)
    if ty == 'write': add(foley, crayon(e['dur'], 1, 1500, 6500, strokes=4.2, grain=120), t, .5, pan)
    elif ty == 'line': add(foley, crayon(e['dur'], 1, 1100, 5000, strokes=1.0, grain=80), t, .24 if not e.get('soft') else .2, pan)
    elif ty == 'colour': add(foley, crayon(e['dur'], 1, 900, 4200, strokes=5.5, grain=70), t, .2, pan)
    elif ty == 'erase':
        add(foley, eraser(e["dur"]), t, .95, pan); add(foley, brush_off(), t + e['dur'] + .1, .25, pan)
    elif ty == 'stain' or ty == 'seep': add(foley, stain(e['dur'] + .6), t, .42, 0)
    elif ty == 'voice':
        v, vsr = sf.read(os.path.join(P, 'voices', e['id'] + '.wav'))
        if v.ndim > 1: v = v.mean(1)
        if vsr != SR:
            from scipy.signal import resample_poly
            v = resample_poly(v, SR, vsr)
        v = hp(v, 75); v = norm(v, .9)
        voice_at.append((t, len(v) / SR)); add(vox, v, t, .55, 0)
    elif ty == 'pink': add(foley, crayon(e['dur'], 1, 700, 5200, strokes=6.5, grain=150, heavy=.6), t, .62, pan)

# room tone, faint wind, a distant clock (most audible in the silence)
add(amb, lp(brown(DUR), 260), 0, .05); add(amb, bp(brown(DUR), 200, 900) * (.5 + .5 * np.sin(2 * np.pi * .05 * tt)), 0, .02)
for s in range(1, int(DUR)):
    d = .03; tk = bp(noise(d), 2200, 5200) * np.exp(-t_(d) / .004)
    add(amb, tk, s + .02, .05 if not 13.9 < s < 15.6 else .1, .45)

duck = np.ones(N)
for t0, d in voice_at:
    duck[int(max(0, t0 - .3) * SR):int((t0 + d + .3) * SR)] = .5
from scipy.ndimage import uniform_filter1d
duck = uniform_filter1d(duck, int(.25 * SR))[:, None]
vox = vox + reverb(vox, .5, .06) - vox * 0   # a small dry room
mix = music * duck + foley * duck ** .6 + amb * duck ** .8 + vox
if os.environ.get('STEMS'):
    for nm, b in (('music', music * duck), ('foley', foley * duck ** .6), ('amb', amb * duck ** .8), ('vox', vox)): sf.write(os.path.join(P, f'stem_{nm}.wav'), b.astype(np.float32), SR)
mix = np.stack([limit(mix[:, c], .9) for c in range(2)], 1)
mix[-int(.05 * SR):] *= np.linspace(1, 0, int(.05 * SR))[:, None]
sf.write(os.path.join(P, 'mix.wav'), mix.astype(np.float32), SR)
print('mix.wav', DUR, 's, peak', float(np.abs(mix).max()))
