"""DSP + metrics for the vocal SFX pipeline (numpy + scipy; run with the ComfyUI venv python, it also has PyAV).

All arrays are mono float32 at SR = 24000.
"""
import hashlib
import os
import sys

import numpy as np
import scipy.signal as sig

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
_CA = os.path.join(ROOT, 'tools', 'comfy_audio')
sys.path.insert(0, _CA)
import audiolib as AL  # noqa: E402  (decode, write_wav, read_wav, encode_mp3, limit, _biquad_*)
sys.path.remove(_CA)  # comfy_audio has its own promote.py / build_audition.py: do not shadow ours

SR = 24000


def rng_for(key):
    return np.random.default_rng(int(hashlib.md5(key.encode()).hexdigest()[:8], 16))


# ------------------------------------------------------------------ filters / helpers
def _sos(kind, f, order=2):
    nyq = SR / 2.0
    if kind == 'bp':
        lo, hi = f
        return sig.butter(order, [max(20, lo) / nyq, min(hi, nyq * 0.96) / nyq], 'bandpass', output='sos')
    return sig.butter(order, min(f, nyq * 0.96) / nyq, 'lowpass' if kind == 'lp' else 'highpass', output='sos')


def lp(x, f, order=2):
    return sig.sosfilt(_sos('lp', f, order), x).astype(np.float32)


def hp(x, f, order=2):
    return sig.sosfilt(_sos('hp', f, order), x).astype(np.float32)


def bp(x, lo, hi, order=2):
    return sig.sosfilt(_sos('bp', (lo, hi), order), x).astype(np.float32)


def tv_reson(x, fc, q, blk=48):
    """time-varying resonant band-pass (RBJ, 0 dB peak). fc, q: scalar or per-sample arrays."""
    n = len(x)
    y = np.zeros(n, np.float32)
    zi = np.zeros(2)
    fca = np.broadcast_to(np.asarray(fc, np.float64), (n,))
    qa = np.broadcast_to(np.asarray(q, np.float64), (n,))
    for s in range(0, n, blk):
        e = min(n, s + blk)
        w0 = 2 * np.pi * min(float(fca[s]), SR * 0.45) / SR
        al = np.sin(w0) / (2 * max(0.3, float(qa[s])))
        b = np.array([al, 0.0, -al]) / (1 + al)
        a = np.array([1.0, -2 * np.cos(w0) / (1 + al), (1 - al) / (1 + al)])
        yb, zi = sig.lfilter(b, a, x[s:e], zi=zi)
        y[s:e] = yb
    return y


def smooth_noise(n, hz, rng):
    """slow random modulation in roughly [-1, 1] (low-passed noise at ~hz)"""
    w = rng.standard_normal(n + 400).astype(np.float32)
    w = lp(w, max(0.5, hz), 2)[200:200 + n]
    return (w / (np.abs(w).max() + 1e-9)).astype(np.float32)


def env_ar(n, a, r, curve=1.0):
    """attack/release envelope (seconds)"""
    e = np.ones(n, np.float32)
    na, nr = int(a * SR), int(r * SR)
    if na > 1:
        e[:na] = np.linspace(0, 1, min(na, n)) ** curve
    if nr > 1:
        nr = min(nr, n)
        e[-nr:] *= np.linspace(1, 0, nr) ** curve
    return e


def norm(x, peak=0.9):
    return (x / (np.abs(x).max() + 1e-9) * peak).astype(np.float32)


def rms_active(x):
    a = np.abs(x)
    g = a > 0.05 * (a.max() + 1e-9)
    return float(np.sqrt((x[g] ** 2).mean())) if g.any() else 1e-6


def resample_rate(x, f):
    """play x at constant speed f (pitch*f, duration/f)"""
    if abs(f - 1.0) < 1e-3 or len(x) < 4:
        return x
    n = int(len(x) / f)
    return np.interp(np.arange(n) * f, np.arange(len(x)), x).astype(np.float32)


def resample_var(x, rate):
    """variable-rate playback: rate is a per-OUTPUT-sample array (1.0 = normal)"""
    pos = np.cumsum(rate) - rate[0]
    keep = pos < len(x) - 1
    pos = pos[keep]
    return np.interp(pos, np.arange(len(x)), x).astype(np.float32)


# ------------------------------------------------------------------ post ops
def apply_post(x, ops, rng):
    for op in ops:
        k = op[0]
        if k == 'drive':
            r = rms_active(x) * 2.5
            x = (np.tanh(x / r * op[1]) * r).astype(np.float32)
        elif k == 'lp':
            x = lp(x, op[1])
        elif k == 'hp':
            x = hp(x, op[1])
        elif k == 'bp':
            x = bp(x, op[1], op[2])
        elif k == 'low':  # low shelf-ish boost
            x = x + (10 ** (op[2] / 20.0) - 1) * lp(x, op[1])
        elif k == 'high':
            x = x + (10 ** (op[2] / 20.0) - 1) * hp(x, op[1])
        elif k == 'pitch':
            x = resample_rate(x, op[1])
        elif k in ('glide', 'fall'):  # variable playback rate r0 -> r1 over the clip (fall: slide-whistle down)
            r0, r1 = op[1], op[2]
            n = int(len(x) / max(0.3, (r0 + r1) / 2)) + 8
            rate = np.linspace(r0, r1, n)
            x = resample_var(x, rate)
        elif k == 'vib':
            t = np.arange(len(x)) / SR
            warp = np.cumsum(1.0 + op[2] * np.sin(2 * np.pi * op[1] * t))
            warp *= (len(x) - 1) / max(warp[-1], 1)
            x = np.interp(warp, np.arange(len(x)), x).astype(np.float32)
        elif k == 'spring':  # boing: damped pitch wobble (depth, hz, decay)
            n = len(x) + 4
            t = np.arange(n) / SR
            rate = 1.0 + op[1] * np.exp(-op[3] * t) * np.sin(2 * np.pi * op[2] * t)
            x = resample_var(x, rate)
        elif k == 'wet':  # splorty flutter: amplitude + lowpass wobble
            t = np.arange(len(x)) / SR
            m = 1.0 - op[1] * (0.5 + 0.5 * np.sin(2 * np.pi * 38 * t + 3 * smooth_noise(len(x), 20, rng)))
            x = (x * m).astype(np.float32)
        elif k == 'cut':  # hard-trim to op[1] seconds with a short fade (staccato syllable)
            x = fades(x[:int(op[1] * SR)], 0.0, 0.03)
        elif k == 'gain':
            x = x * (10 ** (op[1] / 20.0))
        elif k == 'echo':
            d = int(op[1] * SR)
            y = np.concatenate([x, np.zeros(d, np.float32)])
            y[d:] += x * op[2]
            x = y
        elif k in ('sub', 'thump', 'rumble', 'blast'):
            x = add_layer(x, op, rng)
    return x.astype(np.float32)


def add_layer(x, op, rng):
    """synthetic layers under the voice: level is relative (dB) to the voice's active RMS"""
    k = op[0]
    r = rms_active(x)
    if k == 'thump':
        f0, f1, dur, db = op[1:5]
        off = 0.0
    elif k == 'sub':
        f0, f1, dur, db, off = op[1:6]
    elif k == 'rumble':
        dur, db, off = op[1:4]
    else:  # blast
        dur, db, lo, hi = op[1:5]
        off = 0.0
    n = int(dur * SR)
    t = np.arange(n) / SR
    if k in ('thump', 'sub'):
        f = f0 * (f1 / f0) ** (t / dur)
        ph = 2 * np.pi * np.cumsum(f) / SR
        lay = np.sin(ph) * np.exp(-t / (dur / 3.0)) * np.minimum(1, t / 0.006)
        amp = r * 1.41 * 10 ** (db / 20.0)
    elif k == 'rumble':
        w = rng.standard_normal(n).astype(np.float32)
        lay = lp(w, 140, 3) * (np.minimum(1, t / 0.05) * np.exp(-t / (dur / 2.5)))
        lay = lay / (np.abs(lay).max() + 1e-9)
        amp = r * 1.41 * 10 ** (db / 20.0)
    else:
        w = rng.standard_normal(n).astype(np.float32)
        lay = bp(w, lo, hi, 2) * np.exp(-t / (dur / 3.0)) * np.minimum(1, t / 0.002)
        lay = lay / (np.abs(lay).max() + 1e-9)
        amp = r * 1.41 * 10 ** (db / 20.0)
    lay = (lay * amp).astype(np.float32)
    o = int(off * SR)
    L = max(len(x), o + len(lay))
    y = np.zeros(L, np.float32)
    y[:len(x)] += x
    y[o:o + len(lay)] += lay
    return y


# ------------------------------------------------------------------ mastering
def kw(x):
    b1, a1 = AL._biquad_shelf(SR)
    b2, a2 = AL._biquad_hp(SR)
    return sig.lfilter(b2, a2, sig.lfilter(b1, a1, x)).astype(np.float32)


def loud_st(x):
    """short-term loudness (K-weighted): loudest 400 ms window, or the whole clip when shorter"""
    y = kw(x) ** 2
    w = min(len(y), int(0.4 * SR))
    cs = np.concatenate([[0.0], np.cumsum(y)])
    starts = np.arange(0, len(y) - w + 1, max(1, int(0.01 * SR)))
    z = (cs[starts + w] - cs[starts]) / w
    return float(-0.691 + 10 * np.log10(z.max() + 1e-12))


def env_db(x, ms=3.0):
    n = max(1, int(SR * ms / 1000))
    e = np.sqrt(np.convolve(x ** 2, np.ones(n) / n, mode='same') + 1e-14)
    return 20 * np.log10(e + 1e-9)


def trim_onset(x, on_db=-36.0, off_db=-50.0, pre=0.003):
    m = x.copy()
    pk = np.abs(m).max() + 1e-9
    e = env_db(m, 2.0) - 20 * np.log10(pk)
    up = np.nonzero(e > on_db)[0]
    if len(up) == 0:
        return None
    st = max(0, int(up[0]) - int(pre * SR))
    al = np.nonzero(e > off_db)[0]
    en = int(al[-1]) + 1
    return m[st:max(en, st + int(0.05 * SR))]


def fades(x, fin=0.0015, fout=0.012):
    y = x.copy()
    a, b = int(fin * SR), int(fout * SR)
    if a > 1:
        y[:a] *= np.linspace(0, 1, a)
    if b > 1 and len(y) > 2 * b:
        y[-b:] *= np.linspace(1, 0, b) ** 2
    return y


def make_loop(x, xf=0.05):
    """circular crossfade so the buffer can loop: the tail fades into the head, length shrinks by xf"""
    n = int(xf * SR)
    if len(x) < 4 * n:
        return x
    head, tail = x[:n], x[-n:]
    w = np.linspace(0, 1, n)
    mix = head * np.sqrt(w) + tail * np.sqrt(1 - w)
    return np.concatenate([mix, x[n:-n]]).astype(np.float32)


def best_window(x, secs):
    n = int(secs * SR)
    if len(x) <= n:
        return x
    p = np.concatenate([[0.0], np.cumsum(x ** 2)])
    s = int(np.argmax(p[n:] - p[:-n]))
    return x[s:s + n]


def f0_median(x):
    """crude autocorrelation pitch tracker (Hz) over voiced frames; None if nothing voiced"""
    fr, hop = int(0.04 * SR), int(0.01 * SR)
    pk = np.abs(x).max() + 1e-9
    outs = []
    for s in range(0, len(x) - fr, hop):
        f = x[s:s + fr]
        if np.sqrt(np.mean(f ** 2)) < 0.08 * pk:
            continue
        f = f - f.mean()
        ac = np.correlate(f, f, 'full')[fr - 1:]
        if ac[0] <= 0:
            continue
        lo, hi = int(SR / 500), int(SR / 70)
        seg = ac[lo:hi]
        if len(seg) < 3:
            continue
        i = int(np.argmax(seg)) + lo
        if ac[i] / ac[0] > 0.45:
            outs.append(SR / i)
    return float(np.median(outs)) if len(outs) >= 3 else None


def centroid(x):
    X = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    fr = np.fft.rfftfreq(len(x), 1.0 / SR)
    return float((X * fr).sum() / (X.sum() + 1e-12))


def master(x, target_lufs, loop=False, max_len=None, loop_xf=0.06):
    """trim to onset/fade, then loudness-match (short-term LUFS) under a -1 dBFS sample-peak ceiling"""
    x = x - np.mean(x)
    x = hp(x, 35, 2)
    if not loop:
        t = trim_onset(x)
        if t is None:
            return None
        x = t
        if max_len and len(x) > int(max_len * SR):
            x = x[:int(max_len * SR)]
            x = fades(x, 0.0015, 0.06)
        else:
            x = fades(x, 0.0015, 0.014)
    else:
        if max_len and len(x) > int(max_len * SR):
            x = x[:int(max_len * SR)]
        if loop_xf:
            x = make_loop(x, loop_xf)
    x = norm(x, 0.9)
    ceil = 10 ** (-1.0 / 20)
    g = 1.0
    y = x
    for _ in range(6):  # iterate: limiter eats some loudness, so top up (max +14 dB)
        y = AL.limit((x * g)[None, :], SR, ceiling_db=-1.0, look_ms=3.0)[0]
        y = np.clip(y, -ceil, ceil)
        d = target_lufs - loud_st(y)
        if abs(d) < 0.4 or (d > 0 and g > 10 ** (14 / 20.0)):
            break
        g *= 10 ** (d / 20.0)
    return y.astype(np.float32)


def band_stats(y):
    """(share of energy below 300 Hz, share in 800-4000 Hz, dominant frequency of the 300 Hz-smoothed spectrum)"""
    nfft = 1 << int(np.ceil(np.log2(max(len(y), 4096))))
    X = np.abs(np.fft.rfft(y * np.hanning(len(y)), nfft)) ** 2
    fr = np.fft.rfftfreq(nfft, 1.0 / SR)
    tot = X[fr > 50].sum() + 1e-12
    low = X[(fr > 50) & (fr < 300)].sum() / tot
    mid = X[(fr >= 800) & (fr <= 4000)].sum() / tot
    k = max(3, int(300 / (fr[1] - fr[0])))
    sm = np.convolve(X, np.ones(k) / k, 'same')
    sel = (fr > 100) & (fr < 8000)
    dom = float(fr[sel][int(np.argmax(sm[sel]))])
    return float(low), float(mid), dom


def count_hits(y):
    """number of separate percussive hits (peaks of the 6 ms RMS envelope, >=35 ms apart)"""
    k = int(0.006 * SR)
    env = np.sqrt(np.convolve(y ** 2, np.ones(k) / k, mode='same'))
    pk, _ = sig.find_peaks(env, height=0.25 * env.max(), prominence=0.2 * env.max(), distance=int(0.035 * SR))
    return int(len(pk))


def check(y, lo, hi, loop, f0c, target, kid=None):
    """objective checks -> (metrics dict, hard fail list, soft warning list).
    kid='shot'|'loop': the kid-machine-gun profile (dry, mid-high, percussive: NOT a low periodic frog buzz)."""
    dur = len(y) / SR
    pk = float(np.abs(y).max())
    m = {'dur': round(dur, 3), 'peak_db': round(20 * np.log10(pk + 1e-9), 1), 'lufs': round(loud_st(y), 1),
         'centroid': int(centroid(y))}
    f0 = f0_median(y)
    m['f0'] = int(f0) if f0 else None
    hard, soft = [], []
    if pk < 0.05:
        hard.append('silent')
    e = env_db(y, 2.0) - 20 * np.log10(pk + 1e-9)
    act = float((e > -30).mean()) * dur
    if act < 0.04:
        hard.append('too short/quiet')
    on = int(np.argmax(e > -30)) / SR
    m['onset_ms'] = round(on * 1000, 1)
    if not loop and on > 0.012:
        hard.append('late onset %.0f ms' % (on * 1000))
    if dur < lo or dur > hi:
        hard.append('length %.2f s outside %.2f-%.2f' % (dur, lo, hi))
    if m['peak_db'] > -0.4:
        hard.append('clipping')
    if abs(float(y.mean())) / (float(np.sqrt((y ** 2).mean())) + 1e-9) > 0.1:
        hard.append('DC offset')
    if f0c and m['f0']:
        if f0c[0] == 'min' and m['f0'] < f0c[1]:
            hard.append('pitch %d Hz < %d' % (m['f0'], f0c[1]))
        if f0c[0] == 'max' and m['f0'] > f0c[1]:
            hard.append('pitch %d Hz > %d' % (m['f0'], f0c[1]))
    if kid:
        lowsh, midsh, dom = band_stats(y)
        nh = count_hits(y)
        m.update(low300=round(lowsh, 2), mid=round(midsh, 2), dom=int(dom), hits=nh, hit_rate=round(nh / dur, 1))
        if not (800 <= dom <= 4000):
            hard.append('dominant energy %d Hz not in 800-4000 (frog/low buzz?)' % dom)
        if lowsh > 0.2:
            hard.append('%.0f%% energy below 300 Hz (low buzz)' % (lowsh * 100))
        if midsh < 0.4:
            soft.append('only %.0f%% energy in 800-4000 Hz' % (midsh * 100))
        if kid == 'loop' and not (9.0 <= nh / dur <= 18.0):
            hard.append('hit rate %.1f/s outside 9-18' % (nh / dur))
        if kid == 'shot' and not (1 <= nh <= 3):
            hard.append('%d hits in a single shot (want 1-3)' % nh)
    if not loop:
        tail = float(env_db(y[-int(0.03 * SR):], 5.0).mean()) - 20 * np.log10(pk + 1e-9)
        if tail > -30:
            soft.append('tail not decayed')
    d = np.abs(np.diff(y))
    if d.max() / (np.sqrt(np.mean(d ** 2)) + 1e-9) > 40:
        soft.append('click?')
    if m['lufs'] < target - 2.5:
        soft.append('quiet (%.1f LUFS, peak-limited)' % m['lufs'])
    return m, hard, soft
