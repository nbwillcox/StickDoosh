#!/usr/bin/env python3
"""Stage 1 (Kokoro): say every tts take of tools/vocal/specs.py -> assets/raw_audio/vocal/tts/<name>__<take>.wav (24 kHz mono, pitched).

Run with the Kokoro venv:   tools/.venv/Scripts/python tools/vocal/make_tts.py [--only pistol,shotgun] [--force]
All Kokoro runs happen in this one process (model loaded once). Post effects / loudness happen later in master.py.
"""
import argparse
import os
import sys
import time

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import specs  # noqa: E402

SR = 24000
OUT = os.path.join(ROOT, 'assets', 'raw_audio', 'vocal', 'tts')


def trim(x, thr=0.008, pad=0.01):
    idx = np.where(np.abs(x) > thr)[0]
    if len(idx) == 0:
        return x
    return x[max(0, idx[0] - int(pad * SR)):min(len(x), idx[-1] + int(pad * SR * 2))]


def resample(x, f):
    if abs(f - 1.0) < 1e-3 or len(x) < 4:
        return x
    n = int(len(x) / f)
    return np.interp(np.arange(n) * f, np.arange(len(x)), x).astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', help='comma list of sfx names')
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args()
    only = set(a.only.split(',')) if a.only else None
    jobs = []
    for name in specs.ORDER:
        if only and name not in only:
            continue
        for t in specs.NAMES[name]['takes']:
            if t['src'] != 'tts':
                continue
            p = os.path.join(OUT, '%s__%s.wav' % (name, t['id']))
            if os.path.isfile(p) and not a.force:
                continue
            jobs.append((name, t, p))
    print('%d tts takes to say' % len(jobs), flush=True)
    if not jobs:
        return 0
    from kokoro_onnx import Kokoro
    k = Kokoro(os.path.join(ROOT, 'tools', 'models', 'kokoro-v1.0.onnx'), os.path.join(ROOT, 'tools', 'models', 'voices-v1.0.bin'))
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    bad = 0
    for i, (name, t, p) in enumerate(jobs):
        pitch = t['pitch']
        spd = float(np.clip(t['speed'] / pitch, 0.5, 2.0))
        s = None
        try:
            if t.get('ph'):
                s, sr = k.create(t['ph'], voice=t['voice'], speed=spd, lang='en-us', is_phonemes=True)
            else:
                s, sr = k.create(t['text'], voice=t['voice'], speed=spd, lang='en-us')
        except Exception as e:  # phoneme string rejected -> fall back to the spelled text
            print('  phoneme/text failed for %s/%s: %r -> retry text' % (name, t['id'], e), flush=True)
            try:
                s, sr = k.create(t['text'], voice=t['voice'], speed=spd, lang='en-us')
            except Exception as e2:
                print('  FAILED %s/%s: %r' % (name, t['id'], e2), flush=True)
                bad += 1
                continue
        s = np.asarray(s, np.float32)
        s = resample(trim(s), pitch)
        sf.write(p, s, SR, subtype='PCM_16')
        if i % 10 == 0 or i == len(jobs) - 1:
            print('[%d/%d] %s/%s %.2fs  (%.0fs elapsed)' % (i + 1, len(jobs), name, t['id'], len(s) / SR, time.time() - t0), flush=True)
    print('done, %d failed' % bad)
    return 0


if __name__ == '__main__':
    sys.exit(main())
