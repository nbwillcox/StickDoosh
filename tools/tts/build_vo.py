#!/usr/bin/env python3
"""Stick Doosh voice builder: Kokoro TTS (kokoro-onnx, CPU) -> assets/vo/<speaker>/<event>_<n>.mp3

Setup (already done once):  python -m venv tools/.venv ; tools/.venv/Scripts/pip install kokoro-onnx soundfile lameenc
Models (gitignored):        tools/models/kokoro-v1.0.onnx + voices-v1.0.bin  (thewh1teagle/kokoro-onnx release model-files-v1.0)
Run:   node tools/tts/export_lines.js            # js/voice.js catalogue -> tools/tts/lines.json (single source of truth)
       tools/.venv/Scripts/python tools/tts/build_vo.py [--only sgt,goon] [--force] [--limit N]
       python tools/make_audiolist.py            # refresh js/audiolist.js

Curse words ({braces} in the catalogue) are synthesised as SEPARATE segments and concatenated, so their exact
[start,end] seconds are recorded in tools/tts/vo_manifest.json (the game mutes + beeps over them in bleep mode).
"""
import argparse
import hashlib
import io
import json
import os
import re
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
MODELS = os.path.join(ROOT, 'tools', 'models')
OUT = os.path.join(ROOT, 'assets', 'vo')
MANIFEST = os.path.join(HERE, 'vo_manifest.json')
SR = 24000
BITRATE = 56  # kbps mono mp3 @ 24 kHz
TARGET_RMS = 0.085

# --------------------------------------------------------------------------- speaker casting
# voice, speed (Kokoro), pitch (resample factor: >1 higher+faster, speed is pre-compensated), lang, fx list
SPEAKERS = {
    'sgt':       dict(voice='am_onyx', speed=0.92, pitch=0.97, fx=[('drive', 1.3)]),
    'pete':      dict(voice='am_puck', speed=1.08, pitch=1.2, fx=[]),
    'brenda':    dict(voice='af_bella', speed=1.1, pitch=1.0, fx=[('drive', 2.4)], gain=1.15),
    'major':     dict(voice='bm_george', speed=0.95, pitch=1.0, lang='en-gb', fx=[]),
    'gramps':    dict(voice='bm_lewis', speed=0.8, pitch=0.95, lang='en-gb', fx=[('vibrato', 5.0, 0.018), ('lowpass', 4200)]),
    'goon':      dict(voice=['am_adam', 'am_eric', 'am_liam', 'am_echo', 'am_michael'], speed=1.15, pitch=1.0, fx=[('radio',)]),
    'announcer': dict(voice='am_fenrir', speed=0.95, pitch=0.96, fx=[('drive', 2.6), ('echo', 0.085, 0.28)], gain=1.1),
    'boss_ice':      dict(voice='am_liam', speed=0.9, pitch=0.88, fx=[('lowpass', 5200), ('echo', 0.07, 0.2)]),
    'boss_fire':     dict(voice='am_eric', speed=1.2, pitch=1.05, fx=[('drive', 1.8), ('crackle', 0.02)]),
    'boss_wind':     dict(voice='am_adam', speed=1.0, pitch=0.9, fx=[('drive', 1.4), ('breath', 0.02)]),
    'boss_water':    dict(voice='bm_daniel', speed=0.9, pitch=0.9, lang='en-gb', fx=[('vibrato', 3.0, 0.01), ('lowpass', 3000)]),
    'boss_mud':      dict(voice='bm_lewis', speed=0.78, pitch=0.8, lang='en-gb', fx=[('vibrato', 2.2, 0.025), ('lowpass', 2300), ('drive', 1.6)]),
    'boss_jungle':   dict(voice='am_onyx', speed=1.05, pitch=0.78, fx=[('drive', 2.0)]),
    'boss_mountain': dict(voice='am_fenrir', speed=1.1, pitch=1.2, fx=[('vibrato', 8.0, 0.035)]),
    'boss_plains':   dict(voice='am_santa', speed=0.92, pitch=0.97, fx=[('drive', 1.2)]),
    'boss_fantasy':  dict(voice='bm_fable', speed=0.9, pitch=0.95, lang='en-gb', fx=[('echo', 0.13, 0.32)]),
    'boss_moon':     dict(voice='am_echo', speed=1.0, pitch=1.35, fx=[('ring', 55.0, 0.45), ('echo', 0.09, 0.25)]),
    'boss_retro':    dict(voice='am_michael', speed=1.0, pitch=1.0, fx=[('crush', 3, 5), ('ring', 28.0, 0.25)]),
    'boss_fortress': dict(voice='am_michael', speed=0.85, pitch=0.8, fx=[('drive', 2.2), ('echo', 0.1, 0.35)], gain=1.05),
}

# --------------------------------------------------------------------------- text prep (TTS spells sound effects out)
RESPELL = [
    (r'\bg\.o\.a\.t\.', 'goat'),
    (r'\bbr{2,}-ing\b', 'bring'),
    (r'\bbr{2,}t?\b', 'burrrt'),
    (r'\ba{2,}r+g+h*\b', 'argh'),
    (r'\ba{2,}h+\b', 'ahh'),
    (r'\bho{3,}\b', 'whoo'),
    (r'\bpf{2,}\b', 'puff'),
    (r'\bbzz+t\b', 'buzz'),
    (r'\bdo{3,}sh\b', 'doooosh'),
    (r'\bka-do{3,}sh\b', 'kah dooosh'),
]
PH_WORDS = [(r'^baa+$', 'bˈɛːːː'), (r'^zzz+$', 'zˈːːː')]  # whole-token phoneme overrides
HUSH = re.compile(r'\bsh{2,}\b', re.I)


def prep_text(t):
    """lowercase shouty words (all-caps gets spelled out), apply respellings"""
    def lower_caps(m):
        w = m.group(0)
        return w.lower() if len(w) > 1 and w.isupper() else w
    t = re.sub(r"[A-Z][A-Z0-9'.\-]*[A-Z0-9]", lower_caps, t)
    t = t.replace('GL1TCH', 'glitch')
    for pat, rep in RESPELL:
        t = re.sub(pat, rep, t, flags=re.I)
    t = t.replace('glitch dot exe', 'glitch dot e x e')
    return t


def parse(text):
    out, last = [], 0
    for m in re.finditer(r'\{([^}]+)\}', text):
        if m.start() > last:
            out.append(('t', text[last:m.start()]))
        out.append(('c', m.group(1)))
        last = m.end()
    if last < len(text):
        out.append(('t', text[last:]))
    return out


# --------------------------------------------------------------------------- DSP (numpy only)
def resample(x, f):
    """play x at rate f (pitch*f, duration/f)"""
    if abs(f - 1.0) < 1e-3 or len(x) < 4:
        return x
    n = int(len(x) / f)
    return np.interp(np.arange(n) * f, np.arange(len(x)), x).astype(np.float32)


def fftfilt(x, lo=None, hi=None):
    n = len(x)
    if n < 16:
        return x
    X = np.fft.rfft(x)
    fr = np.fft.rfftfreq(n, 1.0 / SR)
    m = np.ones_like(fr)
    if lo:
        m *= 1.0 / (1.0 + np.exp(-(fr - lo) / (lo * 0.12 + 20)))
    if hi:
        m *= 1.0 / (1.0 + np.exp((fr - hi) / (hi * 0.08 + 20)))
    return np.fft.irfft(X * m, n).astype(np.float32)


def rms_active(x):
    a = np.abs(x)
    g = a > 0.02 * (a.max() + 1e-9)
    return float(np.sqrt((x[g] ** 2).mean())) if g.any() else 1e-6


def fx_apply(x, spec, rng):
    kind = spec[0]
    t = np.arange(len(x)) / SR
    if kind == 'drive':
        k = spec[1]
        r = rms_active(x)
        y = np.tanh(x / (r * 2.5) * k) * r * 2.5
        return y.astype(np.float32)
    if kind == 'lowpass':
        return fftfilt(x, None, spec[1])
    if kind == 'echo':
        d = int(spec[1] * SR)
        y = np.concatenate([x, np.zeros(d, np.float32)])
        y[d:] += x * spec[2]
        return y
    if kind == 'vibrato':  # zero-mean pitch wobble (length preserved)
        rate, depth = spec[1], spec[2]
        warp = np.cumsum(1.0 + depth * np.sin(2 * np.pi * rate * t)) - 1.0
        warp *= (len(x) - 1) / max(warp[-1], 1)
        return np.interp(warp, np.arange(len(x)), x).astype(np.float32)
    if kind == 'ring':  # alien / robot: amplitude-modulate with a sine, mix with dry
        f, mix = spec[1], spec[2]
        return (x * (1 - mix) + x * np.sin(2 * np.pi * f * t) * mix * 1.6).astype(np.float32)
    if kind == 'crush':  # bit-crush: sample-hold every N samples, quantise to bits
        hold, bits = spec[1], spec[2]
        y = x[::hold].repeat(hold)[:len(x)]
        q = 2 ** (bits - 1)
        return (np.round(y * q * 1.5) / (q * 1.5)).astype(np.float32)
    if kind == 'radio':  # walkie-talkie: band-pass, grit, hiss, squelch tail
        y = fftfilt(x, 420, 3200)
        r = rms_active(y)
        y = np.tanh(y / (r * 2.2) * 2.0) * r * 2.2
        hiss = fftfilt(rng.standard_normal(len(y)).astype(np.float32), 1500, 5000) * 0.015
        tail = np.zeros(int(0.07 * SR), np.float32)
        tail += fftfilt(rng.standard_normal(len(tail)).astype(np.float32), 800, 4500) * 0.08 * np.linspace(1, 0, len(tail))
        return np.concatenate([y + hiss, tail]).astype(np.float32)
    if kind == 'crackle':  # fire: random pops
        y = x.copy()
        for _ in range(int(len(x) / SR * 28)):
            i = int(rng.integers(0, max(1, len(x) - 80)))
            y[i:i + 60] += (rng.standard_normal(60) * spec[1] * np.linspace(1, 0, 60)).astype(np.float32)
        return y
    if kind == 'breath':  # wind: airy noise under the voice
        return (x + fftfilt(rng.standard_normal(len(x)).astype(np.float32), 800, 6000) * spec[1] * (np.abs(x) > 0.01)).astype(np.float32)
    return x


def hush(n_h, rng):
    """a real 'shhhh': band-passed noise burst"""
    dur = min(0.95, 0.3 + 0.1 * max(0, n_h - 2))
    n = int(dur * SR)
    x = fftfilt(rng.standard_normal(n).astype(np.float32), 2200, 8500)
    env = np.minimum(1, np.arange(n) / (0.07 * SR)) * np.minimum(1, (n - np.arange(n)) / (0.16 * SR))
    x = x * env.astype(np.float32)
    return x / (np.abs(x).max() + 1e-9) * 0.35


def silence(sec):
    return np.zeros(int(sec * SR), np.float32)


def trim(x, thr=0.012, pad=0.03):
    idx = np.where(np.abs(x) > thr)[0]
    if len(idx) == 0:
        return x, 0
    a = max(0, idx[0] - int(pad * SR))
    b = min(len(x), idx[-1] + int(pad * SR * 2))
    return x[a:b], a


# --------------------------------------------------------------------------- synthesis
class Synth:
    def __init__(self):
        from kokoro_onnx import Kokoro
        self.k = Kokoro(os.path.join(MODELS, 'kokoro-v1.0.onnx'), os.path.join(MODELS, 'voices-v1.0.bin'))

    def say(self, text, cfg, voice, ph=None):
        pitch = cfg.get('pitch', 1.0)
        spd = float(np.clip(cfg.get('speed', 1.0) / pitch, 0.5, 2.0))
        lang = cfg.get('lang', 'en-us')
        if ph:
            s, sr = self.k.create(ph, voice=voice, speed=spd, lang=lang, is_phonemes=True)
        else:
            s, sr = self.k.create(text, voice=voice, speed=spd, lang=lang)
        assert sr == SR
        s = np.asarray(s, np.float32)
        s, _ = trim(s, 0.01, 0.01)
        return resample(s, pitch)

    def line(self, speaker, line_id, text):
        cfg = SPEAKERS[speaker]
        voice = cfg['voice']
        if isinstance(voice, list):
            voice = voice[int(hashlib.md5(line_id.encode()).hexdigest(), 16) % len(voice)]
        rng = np.random.default_rng(int(hashlib.md5(line_id.encode()).hexdigest()[:8], 16))
        parts, curses, cursor = [], [], 0.0
        pieces = []
        for kind, seg in parse(text):
            if kind == 'c':
                pieces.append(('c', seg))
            else:
                last = 0
                for m in HUSH.finditer(seg):
                    if m.start() > last:
                        pieces.append(('t', seg[last:m.start()]))
                    pieces.append(('h', len(m.group(0))))
                    last = m.end()
                if last < len(seg):
                    pieces.append(('t', seg[last:]))
        for kind, seg in pieces:
            if kind == 'h':
                a = hush(seg, rng)
                gap = 0.04
            elif kind == 'c':
                a = self.say(prep_text(seg).lower() + '!', cfg, voice)
                gap = 0.03
            else:
                t = prep_text(seg).strip()
                if not re.search(r'[A-Za-z0-9]', t):
                    continue
                ph = None
                for pat, p in PH_WORDS:
                    if re.match(pat, re.sub(r'[^A-Za-z]', '', t), re.I) and len(t) < 12:
                        ph = p + ('?' if t.endswith('?') else '!' if t.endswith('!') else '')
                a = self.say(t, cfg, voice, ph)
                gap = 0.05
            start = cursor
            parts.append(a)
            cursor += len(a) / SR
            if kind == 'c':
                curses.append([start, cursor])
            parts.append(silence(gap))
            cursor += gap
        x = np.concatenate(parts) if parts else silence(0.2)
        # per-speaker effects (time-invariant except vibrato, which preserves length)
        for spec in cfg['fx']:
            x = fx_apply(x, spec, rng)
        # trim silence, shift curse ranges by the leading trim
        x, off = trim(x)
        off = off / SR
        curses = [[round(max(0.0, a - off - 0.02), 3), round(min(len(x) / SR, b - off + 0.02), 3)] for a, b in curses]
        # loudness
        r = rms_active(x)
        x = x * (TARGET_RMS * cfg.get('gain', 1.0) / r)
        x = np.tanh(x * 1.1) / 1.1  # soft limiter
        x = x * min(1.0, 0.95 / (np.abs(x).max() + 1e-9))
        return x.astype(np.float32), curses, voice


def encode_mp3(x):
    import lameenc
    enc = lameenc.Encoder()
    enc.set_bit_rate(BITRATE)
    enc.set_in_sample_rate(SR)
    enc.set_out_sample_rate(SR)
    enc.set_channels(1)
    enc.set_quality(2)
    pcm = (np.clip(x, -1, 1) * 32767).astype('<i2').tobytes()
    return bytes(enc.encode(pcm)) + bytes(enc.flush())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', help='comma list of speakers')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--limit', type=int, default=0)
    args = ap.parse_args()
    with open(os.path.join(HERE, 'lines.json'), 'r', encoding='utf-8') as fh:
        data = json.load(fh)
    lines = data['lines']
    if args.only:
        keep = set(args.only.split(','))
        lines = [l for l in lines if l['speaker'] in keep]
    man = {}
    if os.path.isfile(MANIFEST):
        with open(MANIFEST, 'r', encoding='utf-8') as fh:
            man = json.load(fh)
    # drop manifest entries for lines that no longer exist
    live = {l['id'] for l in data['lines']}
    for k in list(man):
        if k not in live:
            man.pop(k)
            p = os.path.join(OUT, k + '.mp3')
            if os.path.isfile(p):
                os.remove(p)
    todo = []
    for l in lines:
        p = os.path.join(OUT, l['id'] + '.mp3')
        if not args.force and l['id'] in man and man[l['id']].get('h') == l['h'] and os.path.isfile(p):
            continue
        todo.append(l)
    if args.limit:
        todo = todo[:args.limit]
    print('%d lines to build (%d total)' % (len(todo), len(lines)), flush=True)
    if not todo:
        return 0
    synth = Synth()
    t0 = time.time()
    for n, l in enumerate(todo):
        try:
            x, curses, voice = synth.line(l['speaker'], l['id'], l['text'])
        except Exception as e:  # keep going; a line without an mp3 is just bubble-only
            print('FAILED %s: %r' % (l['id'], e), flush=True)
            continue
        mp3 = encode_mp3(x)
        p = os.path.join(OUT, l['id'] + '.mp3')
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'wb') as fh:
            fh.write(mp3)
        man[l['id']] = {'h': l['h'], 'd': round(len(x) / SR, 2), 'curses': curses, 'voice': voice, 'bytes': len(mp3)}
        if n % 10 == 0 or n == len(todo) - 1:
            print('[%d/%d] %s  %.1fs  %.0fs elapsed' % (n + 1, len(todo), l['id'], len(x) / SR, time.time() - t0), flush=True)
            with open(MANIFEST, 'w', encoding='utf-8') as fh:
                json.dump(man, fh, indent=0, sort_keys=True)
    with open(MANIFEST, 'w', encoding='utf-8') as fh:
        json.dump(man, fh, indent=0, sort_keys=True)
    tot = sum(v['bytes'] for v in man.values())
    dur = sum(v['d'] for v in man.values())
    print('done: %d lines, %.1f s audio, %.2f MB' % (len(man), dur, tot / 1e6), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
