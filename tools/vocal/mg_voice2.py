"""Stage 2 (ComfyUI venv python): turn Kokoro 'brrrr' wavs into assets/sfx mg, mg2-5 (short bursts) and mg_loop.
  python tools/vocal/mg_voice2.py [main_tag]   default main = en_ph2_am_michael
"""
import os, sys
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly, butter, sosfilt
from math import gcd
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'comfy_audio'))
import audiolib as AL
SRC = os.path.join(ROOT, 'assets', 'raw_audio', 'vocal', 'mgv'); SFX = os.path.join(ROOT, 'assets', 'sfx')
main = sys.argv[1] if len(sys.argv) > 1 else 'en_ph2_am_michael'
alts = []  # variants = pitch shifts of the chosen take only


def load(tag):
    d = os.path.join(SRC, tag + '.wav')
    if not os.path.exists(d): d = os.path.join(SRC.replace('mgv', 'mgv2'), tag + '.wav')
    sr, x = wavfile.read(d)
    x = x.astype(np.float32)
    if x.dtype.kind != 'f' or np.abs(x).max() > 2: x = x / 32768.0
    return x, sr


def rate(x, r):  # pitch+speed change by r
    f = int(round(r * 1000)); g = gcd(f, 1000)
    return resample_poly(x, 1000 // g, f // g).astype(np.float32)


def fin(x, sr, lufs=-15.0):
    x = x / (np.max(np.abs(x)) + 1e-9)
    gain = 10 ** ((lufs - AL.lufs(x[None, :], sr)) / 20)
    return np.clip(x * gain, -0.89, 0.89).astype(np.float32)


def save(name, x, sr):
    AL.encode_mp3(os.path.join(SFX, name + '.mp3'), x[None, :], sr, 96)


def active(x, sr):
    e = np.abs(x); n = int(sr * 0.01); e = np.convolve(e, np.ones(n) / n, 'same')
    idx = np.where(e > e.max() * 0.08)[0]
    return x[idx[0]: idx[-1] + 1] if len(idx) else x


def loopify(x, sr, length=0.9, xf=0.10):
    n = int(length * sr); xfn = int(xf * sr)
    a = int(0.30 * sr)                                   # skip the 'bur' onset, loop only the rolled r
    seg = x[a: a + n + xfn]
    if len(seg) < n + xfn:
        seg = np.pad(seg, (0, n + xfn - len(seg)), mode='wrap')
    w = np.sin(np.linspace(0, np.pi / 2, xfn)) ** 2
    out = seg[:n].copy(); out[:xfn] = seg[:xfn] * w + seg[n:n + xfn] * (1 - w)
    return out


x, sr = load(main); x = active(x, sr)
sos = butter(2, 120, 'high', fs=sr, output='sos'); x = sosfilt(sos, x).astype(np.float32)
# loop (played while the trigger is held) + short single burst (taps)
save('mg_loop', fin(loopify(x, sr), sr), sr)
short = x[: int(0.30 * sr)].copy(); short *= np.minimum(1, (len(short) - np.arange(len(short))) / (0.05 * sr))
save('mg', fin(short, sr), sr)
# variants: other voices + pitch shifts of the main, short bursts
vs = []
for t in alts:
    try:
        y, s2 = load(t); y = sosfilt(butter(2, 120, 'high', fs=s2, output='sos'), active(y, s2)).astype(np.float32)
        vs.append((y, s2))
    except Exception as e:
        print('skip', t, e)
vs += [(x, sr), (x, sr)]
rates = [1.0, 1.0, 1.10, 0.92, 1.18]
for i, name in enumerate(['mg2', 'mg3', 'mg4', 'mg5']):
    y, s2 = vs[i % len(vs)]
    y = rate(y, rates[i + 1])[: int(0.30 * s2)]
    y = y * np.minimum(1, (len(y) - np.arange(len(y))) / (0.05 * s2))
    save(name, fin(y, s2), s2)
print('mg set built from', main, 'alts', alts)
