#!/usr/bin/env python3
"""Stage 1b: mouth-noise synth + Stable Audio 3 attempts -> assets/raw_audio/vocal/{synth,ai}/*.wav (24 kHz mono).

Run with the ComfyUI venv python (numpy + scipy + PyAV):
    C:/Users/nicho/Documents/ComfyUI/.venv/Scripts/python.exe tools/vocal/make_raw.py --synth [--only mg,flame]
    C:/Users/nicho/Documents/ComfyUI/.venv/Scripts/python.exe tools/vocal/make_raw.py --ai      (needs ComfyUI on :8188; local SA3 only)

Synth = source/filter models of a human mouth: glottal saw + noise through formant resonators, lip-flutter gates,
fricative bands. Nothing here is judged by ear: audition in tools/vocal/audition.html.
"""
import argparse
import os
import sys

import numpy as np
import scipy.signal as sig

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import specs  # noqa: E402
import vlib as V  # noqa: E402
from vlib import SR, bp, hp, lp, tv_reson, smooth_noise, env_ar, norm, rms_active  # noqa: E402

RAW = os.path.join(V.ROOT, 'assets', 'raw_audio', 'vocal')


def trap(t01, a, b, c, d):
    up = np.clip((t01 - a) / max(1e-6, b - a), 0, 1)
    dn = np.clip((d - t01) / max(1e-6, d - c), 0, 1)
    return (up * dn).astype(np.float32)


def pop(n_ms=25, f0=190, f1=80, amp=1.0):
    n = int(n_ms / 1000 * SR)
    t = np.arange(n) / SR
    f = f0 * (f1 / f0) ** (t / (n / SR))
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.008) * amp).astype(np.float32)


def _trill_body(n, f0, flutter, rng, ph0=0.45):
    t = np.arange(n) / SR
    fl = flutter * (1 + 0.10 * smooth_noise(n, 6, rng))
    ph = np.cumsum(fl) / SR + ph0
    g = (0.5 + 0.5 * np.cos(2 * np.pi * ph)) ** 2.0
    g = (0.07 + 0.93 * g).astype(np.float32)
    ff = f0 * (1 + 0.05 * smooth_noise(n, 5, rng) - 0.08 * g)
    saw = 2 * ((np.cumsum(ff) / SR) % 1) - 1
    w = rng.standard_normal(n).astype(np.float32)
    src = (saw * 0.9 + 0.6 * lp(w, 3500)) * g
    y = 1.0 * bp(src, 350, 700) + 0.8 * bp(src, 1100, 1800) + 0.35 * bp(src, 2200, 3000) + 0.5 * lp(src, 250)
    return y.astype(np.float32), t


def trill(p, rng):
    n = int(p['dur'] * SR)
    y, t = _trill_body(n, p['f0'], p['flutter'], rng)
    y = norm(y, 0.8)
    pp = pop(25, p['f0'] * 1.7, p['f0'] * 0.8, 0.85)
    y[:len(pp)] += pp
    return norm(y * env_ar(n, 0.003, 0.02), 0.9)


def trill_loop(p, rng):
    n = int(p['dur'] * SR)
    y, t = _trill_body(n, p['f0'], p['flutter'], rng)
    y = norm(y, 0.8)
    starts = [int((s + 0.012) * SR) for s in p['pattern']]
    gate = np.zeros(n, np.float32)
    gap = int(0.04 * SR)
    for i, s in enumerate(starts):
        e = (starts[i + 1] - gap) if i + 1 < len(starts) else n - gap
        e = max(e, s + int(0.05 * SR))
        seg = np.ones(e - s, np.float32)
        r = min(int(0.012 * SR), len(seg) // 2)
        seg[:r] = np.linspace(0, 1, r)
        seg[-r:] = np.linspace(1, 0, r)
        seg *= 0.85 + 0.15 * rng.random()
        gate[s:e] = seg[:max(0, min(len(seg), n - s))]
    y = y * gate
    for s in starts:
        pp = pop(22, p['f0'] * 1.7, p['f0'] * 0.8, 0.55)
        e = min(n, s + len(pp))
        y[s:e] += pp[:e - s]
    return norm(y, 0.9)


def hiss(p, rng, loop=False):
    n = int(p['dur'] * SR)
    t01 = np.linspace(0, 1, n)
    c0, c1 = p['c0'], p['c1']
    shape = p.get('shape', 'rise')
    breath = p.get('breath', 0.18)
    w = rng.standard_normal(n).astype(np.float32)
    if loop:
        u = 0.5 + 0.18 * smooth_noise(n, 0.8, rng)
        e = (1 + 0.14 * smooth_noise(n, 1.5, rng))
    elif shape == 'pass':
        u = np.where(t01 < 0.62, t01 / 0.62, 1 - (t01 - 0.62) / 0.38 * 0.75)
        e = np.sin(np.pi * np.clip(t01, 0, 1) ** 0.75) ** 1.1
    else:
        u = t01 ** 0.8
        e = (0.45 + 0.55 * t01 ** 1.2) * np.clip((1 - t01) / 0.14, 0, 1)
    fc = c0 + (c1 - c0) * u
    sh = tv_reson(w, fc, 1.0) + 0.7 * tv_reson(w, fc * 1.5, 1.3)
    br = bp(w, 250, 1200) * breath * 2.0
    y = (sh + br) * e * (1 + 0.12 * smooth_noise(n, 9, rng))
    y = norm(y, 0.8)
    if not loop:
        y *= np.clip(t01 * p['dur'] / 0.07, 0, 1) ** 1.5
    if p.get('onset_t'):
        k = int(0.02 * SR)
        y[:k] += hp(rng.standard_normal(k).astype(np.float32), 2500) * np.exp(-np.arange(k) / SR / 0.006) * 1.5
    return norm(y, 0.9)


def fwoosh(p, rng, loop=False):
    dur, f0, rasp = p['dur'], p['f0'], p['rasp']
    n = int(dur * SR)
    t = np.arange(n) / SR
    t01 = t / dur
    w = rng.standard_normal(n).astype(np.float32)
    if loop:
        e_f = np.full(n, 0.15, np.float32)
        e_oo = (0.85 + 0.15 * smooth_noise(n, 2, rng)).astype(np.float32)
        e_sh = (0.55 + 0.2 * smooth_noise(n, 1.5, rng)).astype(np.float32)
    else:
        e_f = trap(t01, 0.0, 0.02, 0.07, 0.17)
        e_oo = trap(t01, 0.05, 0.22, 0.5, 0.8)
        e_sh = trap(t01, 0.3, 0.55, 0.75, 1.0)
    ff = f0 * (1 + 0.3 * smooth_noise(n, 15, rng))
    saw = 2 * ((np.cumsum(ff) / SR) % 1) - 1
    rph = np.cumsum(70 * (1 + 0.3 * smooth_noise(n, 10, rng))) / SR
    m = lp(1 - rasp * 0.9 * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * rph))).astype(np.float32), 500)
    src = (0.7 * saw + 0.8 * lp(w, 2500)) * m
    F1 = 330 + 70 * t01
    F2 = 750 + 250 * t01
    oo = tv_reson(src, F1, 5) + 0.9 * tv_reson(src, F2, 6) + 0.4 * lp(src, 200)
    sh = 0.8 * tv_reson(w, 2300 + 1300 * t01, 1.2) + 0.15 * hp(w, 4500)
    fp = hp(w, 1400)
    oo = oo / (rms_active(oo) + 1e-6)
    sh = sh / (rms_active(sh) + 1e-6)
    fp = fp / (rms_active(fp) + 1e-6)
    y = 0.35 * fp * e_f + 0.8 * oo * e_oo + 0.9 * sh * e_sh
    if not loop:
        y *= env_ar(n, 0.02, 0.1)
    return norm(y, 0.9)


def bzzt(p, rng):
    dur, fa, fb = p['dur'], p['fa'], p['fb']
    n = int(dur * SR)
    t = np.arange(n) / SR
    t01 = t / dur
    f0 = fa * (fb / fa) ** t01
    ph = np.cumsum(f0) / SR
    saw = 2 * (ph % 1) - 1
    w = rng.standard_normal(n).astype(np.float32)
    vo = 0.8 * bp(saw, 250, 450) + 0.7 * bp(saw, 1800, 2800) + 0.4 * bp(saw, 3500, 5500)
    fr = hp(w, 3500) * (0.5 + 0.5 * np.cos(2 * np.pi * ph))
    y = vo / (rms_active(vo) + 1e-6) * 0.8 + fr / (rms_active(fr) + 1e-6) * 0.5
    if p.get('trem'):
        y *= 1 - 0.35 * (0.5 + 0.5 * np.sin(2 * np.pi * p['trem'] * t))
    y *= env_ar(n, 0.012, 0.03)
    y = norm(y, 0.85)
    if p.get('glide'):  # leading 'p'
        k = int(0.012 * SR)
        y[:k] += lp(rng.standard_normal(k).astype(np.float32), 1500) * np.exp(-np.arange(k) / SR / 0.004) * 1.2
    else:  # trailing 't' click
        k = int(0.02 * SR)
        y = np.concatenate([y, np.zeros(k, np.float32)])
        y[-k:] += hp(rng.standard_normal(k).astype(np.float32), 4000) * np.exp(-np.arange(k) / SR / 0.004) * 0.9
    return norm(y, 0.9)


def tss(p, rng):
    dur, hi = p['dur'], p.get('hi', 5500)
    n = int(dur * SR)
    w = rng.standard_normal(n).astype(np.float32)
    s = bp(w, 3200, hi)
    cr = np.clip(1 + 0.7 * smooth_noise(n, 120, rng), 0.15, 2.0)
    imp = (rng.random(n) < 60 / SR).astype(np.float32)
    pops = hp(imp, 2000) * 6
    y = s * cr + pops * 0.5
    k = int(0.015 * SR)
    y[:k] += hp(rng.standard_normal(k).astype(np.float32), 2500) * np.exp(-np.arange(k) / SR / 0.005) * 2
    y *= env_ar(n, 0.006, 0.4 * dur)
    return norm(y, 0.9)


def whoosh(p, rng):
    dur, fa, fb = p['dur'], p['fa'], p['fb']
    n = int(dur * SR)
    t01 = np.linspace(0, 1, n)
    w = rng.standard_normal(n).astype(np.float32)
    fc = fa * (fb / fa) ** (t01 ** 0.7)
    y = tv_reson(w, fc, 1.1) + 0.3 * bp(w, 200, 700)
    y *= np.sin(np.pi * np.clip(t01, 0, 1) ** 0.8) ** 1.3
    return norm(y, 0.9)


def _kid_hit(f0, cf, voiced, rng, dur=0.12, tau_n=0.012, tau_v=0.035, breath=0.0):
    """one dry mouth plosive ("da"/"ka"/"tk"): spit click + 1-4 kHz noise burst + a faint child-pitched voiced 'ah' + optional puff"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    w = rng.standard_normal(n).astype(np.float32)
    y = bp(w, cf * 0.55, cf * 1.7) * np.exp(-t / tau_n) * np.minimum(1, t / 0.0006)
    y = y / (np.abs(y).max() + 1e-9)
    k = int(0.0018 * SR)
    y[:k] += hp(w[:k], 3000) / (np.abs(hp(w[:k], 3000)).max() + 1e-9) * 0.6
    if voiced > 0:
        ff = f0 * (1 - 0.12 * np.minimum(1, t / 0.08))
        saw = 2 * ((np.cumsum(ff) / SR) % 1) - 1
        v = bp(saw, 700, 1100) + 0.7 * bp(saw, 1300, 1900) + 0.3 * bp(saw, 2300, 3200)
        v = v / (np.abs(v).max() + 1e-9) * np.exp(-t / tau_v) * np.minimum(1, t / 0.004)
        y = y + voiced * v
    if breath > 0:
        br = hp(w, 2500) * np.exp(-t / 0.05) * np.minimum(1, t / 0.01)
        y = y + breath * br / (np.abs(br).max() + 1e-9)
    return y.astype(np.float32)


def mg_shot(p, rng):
    n = int(p['dur'] * SR)
    y = np.zeros(n + int(0.2 * SR), np.float32)
    h = _kid_hit(p['f0'], p['cf'], p['voiced'], rng, 0.12, p.get('tau_n', 0.012), breath=p.get('breath', 0.0))
    y[:len(h)] += h
    if p.get('hits', 1) > 1:
        s = int(p['gap'] * SR)
        h2 = _kid_hit(p['f0'] * 1.08, p['cf'] * 1.12, p['voiced'], rng, 0.12, p.get('tau_n', 0.012))
        y[s:s + len(h2)] += 0.75 * h2
    return norm(y[:n] * env_ar(n, 0.0004, 0.012), 0.9)


def hits_loop(p, rng):
    """circular train of kid mouth hits (rate hits/s, uneven timing, per-hit pitch/band wobble): wraps, so it loops seamlessly"""
    dur, R = p['dur'], p['rate']
    n = int(dur * SR)
    N = int(round(R * dur))
    T = dur / N
    acc = p.get('accent', (1.0,))
    y = np.zeros(n, np.float32)
    ph = rng.random() * 6.28
    for k in range(N):
        tk = k * T + float(np.clip(rng.normal(0, p['jitter'] * T), -0.4 * T, 0.4 * T))
        f0 = p['f0'] * (1 + 0.10 * np.sin(2 * np.pi * k / 6.5 + ph) + 0.04 * rng.normal())
        cf = p['cf'] * (1 + 0.2 * rng.uniform(-1, 1))
        h = _kid_hit(f0, cf, p['voiced'], rng, 0.1, p.get('tau_n', 0.012), p.get('tau_v', 0.035))
        amp = acc[k % len(acc)] * (0.78 + 0.22 * rng.random())
        idx = (int(round(tk * SR)) + np.arange(len(h))) % n
        np.add.at(y, idx, h * amp)
    return norm(y, 0.9)


KINDS = {
    'mg_shot': mg_shot, 'hits_loop': hits_loop,
    'trill': trill, 'trill_loop': trill_loop,
    'hiss': hiss, 'hiss_loop': lambda p, r: hiss(p, r, True),
    'fwoosh': fwoosh, 'fwoosh_loop': lambda p, r: fwoosh(p, r, True),
    'bzzt': bzzt, 'tss': tss, 'whoosh': whoosh,
}


def run_synth(only):
    out = os.path.join(RAW, 'synth')
    n = 0
    for name in specs.ORDER:
        if only and name not in only:
            continue
        for t in specs.NAMES[name]['takes']:
            if t['src'] != 'synth':
                continue
            rng = V.rng_for('%s/%s' % (name, t['id']))
            x = KINDS[t['kind']](t['params'], rng)
            V.AL.write_wav(os.path.join(out, '%s__%s.wav' % (name, t['id'])), SR, x[None, :])
            n += 1
    print('synth: wrote %d raw takes' % n)


def run_ai(keys=None):
    import comfy_client as CC
    CC_ = CC
    out = os.path.join(RAW, 'ai')
    for key, job in specs.AI_JOBS.items():
        if keys and key not in keys:
            continue
        print('SA3 %s: "%s" %.1fs x%d ...' % (key, job['prompt'][:60], job['seconds'], job['batch']), flush=True)
        try:
            items, dt = CC_.generate(job['prompt'], job['seconds'], job['seed'], batch=job['batch'], prefix='stickdoosh/vocal_' + key,
                                     negative=specs.AI_NEG)
        except Exception as e:
            print('  FAILED: %r' % (e,), flush=True)
            continue
        for i, (fn, data) in enumerate(items):
            sr, x = V.AL.decode(data)
            m = x.mean(axis=0)
            if sr != SR:
                g = np.gcd(sr, SR)
                m = sig.resample_poly(m, SR // g, sr // g)
            V.AL.write_wav(os.path.join(out, '%s__%d.wav' % (key, i)), SR, m[None, :].astype(np.float32))
        print('  %d clips in %.0fs' % (len(items), dt), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--synth', action='store_true')
    ap.add_argument('--ai', action='store_true')
    ap.add_argument('--only')
    ap.add_argument('--keys', help='comma list of AI job keys (default all)')
    a = ap.parse_args()
    sys.path.insert(0, os.path.join(V.ROOT, 'tools', 'comfy_audio'))
    only = set(a.only.split(',')) if a.only else None
    if a.synth:
        run_synth(only)
    if a.ai:
        run_ai(set(a.keys.split(',')) if a.keys else None)
    return 0


if __name__ == '__main__':
    sys.exit(main())
