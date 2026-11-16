"""One-shot batch: (1) kid 'brrrr' machine gun (mg, mg2-5, mg_loop), (2) extra variants name_v2.. from existing takes.
Run with the ComfyUI venv python:  python tools/vocal/batch_fix.py   (then python tools/make_audiolist.py)
"""
import json, os, shutil, sys
import numpy as np
from scipy.signal import butter, sosfilt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'comfy_audio'))
import audiolib as AL  # noqa: E402

SR = 24000
SFX = os.path.join(ROOT, 'assets', 'sfx')


def bp(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], btype='band', fs=SR, output='sos'), x)


def hp(x, f):
    return sosfilt(butter(2, f, btype='high', fs=SR, output='sos'), x)


def lp(x, f):
    return sosfilt(butter(2, f, btype='low', fs=SR, output='sos'), x)


def brr(dur, rate, seed, f0=250.0, drift=0.0):
    """Kid lip-roll: pulse train (rate Hz) of breathy noise + weak voiced buzz, formant shaped, dry, no low croak."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    # pulse phase with jitter + slow rate drift
    inst = rate * (1 + drift * np.sin(2 * np.pi * 0.9 * t + rng.uniform(0, 6)))
    inst = inst * (1 + 0.05 * np.convolve(rng.standard_normal(n), np.ones(400) / 400, 'same') * 8)
    ph = np.cumsum(inst) / SR
    pulse = np.clip(np.sin(2 * np.pi * ph), 0, None) ** 1.6          # lips open only half of each cycle
    noise = rng.standard_normal(n)
    breath = bp(noise, 700, 3600) * 0.9 + bp(noise, 1800, 5200) * 0.35
    # voiced buzz (kid pitch) with vibrato, gated by the lip pulses
    fi = f0 * (1 + 0.03 * np.sin(2 * np.pi * 5 * t))
    v = np.sign(np.sin(2 * np.pi * np.cumsum(fi) / SR))
    v = bp(v, 380, 2600) * 0.45
    x = (breath + v) * pulse
    x += 0.6 * np.tanh(2.5 * x)                                       # light grit = 'real gun' bite
    x = hp(x, 260)                                                    # no frog-low croak
    # spit/puff transient at the start and soft end
    pf = bp(rng.standard_normal(int(0.012 * SR)), 1500, 6000)
    x[:len(pf)] += pf * np.hanning(len(pf)) * 1.4
    env = np.minimum(1, t / 0.006) * np.minimum(1, (dur - t) / 0.03)
    return x * env


def fin(x, lufs=-17.0):
    x = x / (np.max(np.abs(x)) + 1e-9)
    g = 10 ** ((lufs - AL.lufs(x.astype(np.float32)[None, :], SR)) / 20)
    x = np.clip(x * g, -0.89, 0.89)
    return x.astype(np.float32)


def save(name, x):
    AL.encode_mp3(os.path.join(SFX, name + '.mp3'), x[None, :], SR, 96)


def make_mg():
    specs = [('mg', 0.15, 29, 1), ('mg2', 0.14, 26, 2), ('mg3', 0.16, 33, 3), ('mg4', 0.15, 31, 4), ('mg5', 0.15, 28, 5)]
    for name, dur, rate, seed in specs:
        save(name, fin(brr(dur, rate, seed, f0=240 + seed * 14)))
    # seamless ~1.4 s loop: generate 1.6 s, cross-fade tail into head
    x = brr(1.6, 28, 11, drift=0.05)
    xf = int(0.12 * SR)
    head, tail = x[:xf], x[-xf:]
    w = np.linspace(0, 1, xf)
    loop = x[xf:-xf].copy()
    loop[:xf] = loop[:xf] * w + tail * (1 - w) * 0 + 0
    mixed = x[:-xf].copy()
    mixed[:xf] = head * w + tail * (1 - w)
    save('mg_loop', fin(mixed[: int(1.45 * SR)]))
    print('mg done')


NAMES = ['pistol', 'dual', 'spread', 'shotgun', 'laser', 'rocket_launch', 'flame', 'grenade_throw', 'explode',
         'explode_big', 'bigboom', 'crash', 'punch', 'hit', 'hit_metal', 'slam', 'gib', 'splat', 'hurt', 'die', 'jump',
         'land', 'alert', 'pickup', 'powerup', 'gold', 'whoosh', 'bounce', 'boing', 'thoom']


def variants(maxv=3):
    man = json.load(open(os.path.join(HERE, 'manifest.json')))['names']
    total = 0
    for nm in NAMES:
        m = man.get(nm)
        if not m:
            continue
        inst = os.path.join(SFX, nm + '.mp3')
        cur = open(inst, 'rb').read() if os.path.exists(inst) else b''
        cands = []
        for tk, d in m['takes'].items():
            p = os.path.join(HERE, d['file'])
            if not os.path.exists(p) or open(p, 'rb').read() == cur:
                continue
            cands.append((0 if d.get('ok') else 1, -d.get('score', 0), tk, p))
        cands.sort()
        # prefer distinct voices/words
        seen, k = set(), 2
        for _, _, tk, p in cands:
            key = m['takes'][tk].get('say', tk)
            if key in seen:
                continue
            seen.add(key)
            shutil.copyfile(p, os.path.join(SFX, '%s_v%d.mp3' % (nm, k)))
            k += 1
            total += 1
            if k > maxv + 1:
                break
    print('variants installed:', total)


if __name__ == '__main__':
    make_mg()
    variants()
