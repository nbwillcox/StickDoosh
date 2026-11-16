"""Stage 1 (Kokoro venv): 'bur' + rolled r candidates -> assets/raw_audio/vocal/mgv2/<tag>.wav, tools/vocal/mg_audition.html, use_mg_<tag>.bat
  tools/.venv/Scripts/python tools/vocal/mg_voice3.py
K1-K8: Kokoro says 'bɜ' + a run of flapped/trilled r phonemes.   H1-H8: Kokoro 'bɜ' + synthesized VOICED tongue-roll tail at the same pitch.
"""
import os
import numpy as np
import soundfile as sf
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'assets', 'raw_audio', 'vocal', 'mgv2'); os.makedirs(OUT, exist_ok=True)
from kokoro_onnx import Kokoro
k = Kokoro(os.path.join(ROOT, 'tools', 'models', 'kokoro-v1.0.onnx'), os.path.join(ROOT, 'tools', 'models', 'voices-v1.0.bin'))
VOICES = [('michael', 'am_michael', 120.0), ('puck', 'am_puck', 160.0), ('onyx', 'am_onyx', 95.0), ('adam', 'am_adam', 115.0)]


def say(ph, voice, speed=1.0):
    x, sr = k.create(ph, voice=voice, speed=speed, lang='en-us', is_phonemes=True)
    return np.asarray(x, np.float32), sr


def f0_of(x, sr, lo=70, hi=260):
    seg = x[-int(0.12 * sr):] if len(x) > 0.15 * sr else x
    seg = seg - seg.mean(); ac = np.correlate(seg, seg, 'full')[len(seg) - 1:]
    a, b = int(sr / hi), int(sr / lo)
    return sr / (a + int(np.argmax(ac[a:b]))) if b < len(ac) else 0


def roll(sr, dur, f0, rate, seed):
    """Voiced tongue roll: glottal-ish harmonic source through an 'uh/er' formant set, amplitude + formant dip at `rate` Hz."""
    rng = np.random.default_rng(seed); n = int(dur * sr); t = np.arange(n) / sr
    jit = 1 + 0.012 * np.convolve(rng.standard_normal(n), np.ones(600) / 600, 'same') * 12
    ph = np.cumsum(f0 * jit * (1 - 0.05 * np.sin(2 * np.pi * rate * t))) / sr
    x = np.zeros(n, np.float32)
    for h in range(1, int(5000 / f0)):
        fh = h * f0
        amp = (1 / h ** 0.9) * (np.exp(-((fh - 520) / 260) ** 2) * 1.0 + np.exp(-((fh - 1350) / 350) ** 2) * 0.7 + np.exp(-((fh - 1650) / 300) ** 2) * 0.5 + 0.05)
        x += amp * np.sin(2 * np.pi * h * ph + h)
    cyc = (t * rate + rng.uniform(0, 1)) % 1.0
    tap = 0.18 + 0.82 * np.clip(np.cos(np.pi * (cyc - 0.5) * 1.0), 0, 1) ** 1.4   # tongue touches palate once per cycle
    x *= tap
    x += 0.04 * rng.standard_normal(n).astype(np.float32) * tap                    # breath
    x = np.tanh(1.6 * x / (np.abs(x).max() + 1e-9))
    env = np.minimum(1, t / 0.03) * np.minimum(1, (dur - t) / 0.12)
    return (x * env).astype(np.float32)


def squeeze(x, sr, thr=0.05, min_gap=0.018, keep=0.003):
    """Remove dead air: any quiet run longer than min_gap is cut down to `keep` seconds, so bur + rolled r run together."""
    n = max(1, int(sr * 0.003)); e = np.convolve(np.abs(x), np.ones(n) / n, 'same'); q = e < thr * e.max()
    mask = np.ones(len(x), bool); i = 0; kn = int(keep * sr / 2)
    while i < len(x):
        if q[i]:
            j = i
            while j < len(x) and q[j]: j += 1
            if j - i > min_gap * sr and i > 0 and j < len(x):
                mask[i + kn: j - kn] = False
            i = j
        else:
            i += 1
    return x[mask]


def save(tag, x, sr):
    x = squeeze(x, sr)
    x = x / (np.abs(x).max() + 1e-9) * 0.85
    sf.write(os.path.join(OUT, tag + '.wav'), x.astype(np.float32), sr)


cands = []
i = 0
for nm, v, f0d in VOICES:
    i += 1; x, sr = say('bɜ' + 'ɾ' * 14, v, 1.25); save('K%d' % i, x, sr); cands.append(('K%d' % i, nm, 'bur + flapped r run'))
    i2 = i + 4; x, sr = say('bɜ' + 'r' * 14, v, 1.15); save('K%d' % i2, x, sr); cands.append(('K%d' % i2, nm, 'bur + trilled r run'))
j = 0
for nm, v, f0d in VOICES:
    pre, sr = say('bɜ', v, 1.1)
    f0 = f0_of(pre, sr) or f0d
    if not (60 < f0 < 280): f0 = f0d
    for rate, off in [(22, 0), (29, 4)]:
        j += 1
        tail = roll(sr, 1.4, f0, rate, j)
        x = np.concatenate([pre * 1.0, tail * (np.abs(pre).max() + 1e-6) * 0.9])
        save('H%d' % (j), x, sr); cands.append(('H%d' % j, nm, 'bur + synthesized voiced roll %d Hz, pitch %d Hz' % (rate, round(f0))))
cands.sort(key=lambda c: (c[0][0], int(c[0][1:])))
rows = ''.join('<tr><td><b>%s</b></td><td>%s</td><td>%s</td><td><audio controls preload="none" src="/assets/raw_audio/vocal/mgv2/%s.wav"></audio></td><td>use_mg_%s.bat</td></tr>' % (t, n, d, t, t) for t, n, d in cands)
html = ('<!doctype html><meta charset="utf-8"><title>MG audition</title><body style="font:16px sans-serif;max-width:900px;margin:20px auto;padding:0 12px">'
        '<h2>Machine gun: "bur" + rolling r</h2><p>Play any row. To put one in the game, double-click its <b>use_mg_&lt;id&gt;.bat</b> in <code>tools\\vocal\\</code>, then Ctrl+F5 in the game.</p>'
        '<table cellpadding="6">%s</table></body>' % rows)
open(os.path.join(ROOT, 'tools', 'vocal', 'mg_audition.html'), 'w').write(html)
PY = r'C:\Users\nicho\Documents\ComfyUI\.venv\Scripts\python.exe'
for t, n, d in cands:
    open(os.path.join(ROOT, 'tools', 'vocal', 'use_mg_%s.bat' % t), 'w').write(
        '@echo off\r\ncd /d "%%~dp0..\\.."\r\n"%s" tools\\vocal\\mg_voice2.py %s\r\npython tools\\make_audiolist.py\r\necho.\r\necho Done. Hard-refresh the game (Ctrl+F5).\r\npause\r\n' % (PY, t))
print(len(cands), 'candidates')
