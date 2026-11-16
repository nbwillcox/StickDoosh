#!/usr/bin/env python3
"""Stage 2: raw takes -> mastered mp3 takes (tools/vocal/takes/<name>/<take>.mp3) + manifest.json + default install.

    C:/Users/nicho/Documents/ComfyUI/.venv/Scripts/python.exe tools/vocal/master.py [--only shotgun,mg] [--no-install]

Per take: post DSP -> trim to onset (<= ~3 ms pre-roll) -> fades -> loudness match (short-term LUFS: voices -16, shotgun and
explosions -13, loops -19) under a -1 dBFS sample-peak limiter -> mono 24 kHz 96 kbps mp3 -> objective checks
(non-silent, onset, length window, clipping, DC, pitch class, tail, click, decodes). The highest scoring take of each name
is the DEFAULT and is copied to assets/sfx/<name>.mp3 (the old file is backed up once in assets/raw_audio/sfx_old/)
unless you pinned a take with promote.py. Finally audition.html and js/audiolist.js are rebuilt.
"""
import argparse
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import specs  # noqa: E402
import vlib as V  # noqa: E402
import promote as P  # noqa: E402
from vlib import SR  # noqa: E402

RAW = os.path.join(V.ROOT, 'assets', 'raw_audio', 'vocal')


def raw_path(name, t):
    if t['src'] == 'tts':
        return os.path.join(RAW, 'tts', '%s__%s.wav' % (name, t['id']))
    if t['src'] == 'synth':
        return os.path.join(RAW, 'synth', '%s__%s.wav' % (name, t['id']))
    return os.path.join(RAW, 'ai', '%s__%d.wav' % (t['key'], t['idx']))


def target_lufs(ent):
    if ent['loop']:
        return -19.0
    return -13.0 if ent['loud'] == 'L' else -16.0


def process_take(name, ent, t):
    p = raw_path(name, t)
    if not os.path.isfile(p):
        return None, 'raw missing (%s)' % os.path.basename(p)
    sr, x = V.AL.read_wav(p)
    x = x.mean(axis=0).astype(np.float32)
    if sr != SR:
        return None, 'unexpected raw sample rate %d' % sr
    if t.get('crop'):
        x = V.best_window(x, t['crop'][1] * (1.0 if ent['loop'] else 1.6))
    rng = V.rng_for('post/%s/%s' % (name, t['id']))
    x = V.apply_post(x, t['post'], rng)
    xf = 0.0 if (t['src'] == 'synth' and t['kind'] in ('trill_loop', 'hits_loop')) else 0.06
    y = V.master(x, target_lufs(ent), loop=ent['loop'], max_len=ent['hi'] + (0.02 if not ent['loop'] else 0), loop_xf=xf)
    if y is None:
        return None, 'silent'
    return y, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only')
    ap.add_argument('--no-install', action='store_true')
    a = ap.parse_args()
    only = set(a.only.split(',')) if a.only else None
    man = {'names': {}, 'order': list(specs.ORDER)}
    if os.path.isfile(P.MAN):
        old = P.load()
        man['names'] = old.get('names', {})
    t0 = time.time()
    total = 0
    for name in specs.ORDER:
        ent = specs.NAMES[name]
        if ent['variant_of']:
            continue
        if only and name not in only:
            continue
        prev = man['names'].get(name, {})
        me = dict(grp=ent['grp'], voice=ent['voice'], word=ent['word'], desc=ent['desc'], lo=ent['lo'], hi=ent['hi'],
                  loop=ent['loop'], loud=ent['loud'], takes={}, order=[], pinned=prev.get('pinned', False),
                  installed=prev.get('installed'))
        for idx, t in enumerate(ent['takes']):
            y, err = process_take(name, ent, t)
            tk = dict(src=t['src'], note=t['note'] or '', file='takes/%s/%s.mp3' % (name, t['id']))
            if t['src'] == 'tts':
                tk['voice'] = t['voice']
                tk['say'] = t['ph'] or t['text']
            if y is None:
                tk.update(ok=False, fails=[err], soft=[], score=-99.0, missing=True)
                me['takes'][t['id']] = tk
                me['order'].append(t['id'])
                continue
            m, hard, soft = V.check(y, ent['lo'], ent['hi'], ent['loop'], ent['f0'], target_lufs(ent), ent.get('kid'))
            path = os.path.join(P.TAKES, name, t['id'] + '.mp3')
            os.makedirs(os.path.dirname(path), exist_ok=True)
            size = V.AL.encode_mp3(path, y[None, :], SR, 96)
            try:  # the mp3 must decode and still contain the sound
                dsr, dx = V.AL.decode(path)
                dd = dx.shape[1] / dsr
                if abs(dd - m['dur']) > 0.12 or np.abs(dx).max() < 0.05:
                    hard.append('mp3 decode mismatch (%.2fs)' % dd)
                m['dec_dur'] = round(dd, 3)
            except Exception as e:  # noqa: BLE001
                hard.append('mp3 does not decode: %r' % (e,))
            bonus = 0.0
            if ent.get('kid'):  # kid machine-gun profile: prefer bright/mid-dominant, single hits per shot, ~13.5 hits/s in loops
                bonus = 1.5 * m['mid'] - (0.3 * (m['hits'] - 1) if ent['kid'] == 'shot' else 0.15 * abs(m['hit_rate'] - 13.5))
            score = 10.0 - 3.0 * len(hard) - 0.7 * len(soft) - 0.15 * idx - (2.5 if t['src'] == 'ai' else 0.0) + bonus
            tk.update(m)
            tk.update(ok=not hard, fails=hard, soft=soft, score=round(score, 2), bytes=size)
            me['takes'][t['id']] = tk
            me['order'].append(t['id'])
            total += size
        best = max(me['order'], key=lambda i: (me['takes'][i]['score'], -me['order'].index(i)))
        me['default'] = best
        man['names'][name] = me
        print('%-14s default=%-7s  %s' % (name, best, ' '.join('%s%s' % (i, '' if me['takes'][i]['ok'] else '(x)') for i in me['order'])), flush=True)
    # variants (mg2..mg5): same takes as their base, different default (spec default if it passes the checks, else the best unused passing take)
    used = {}
    for name in specs.ORDER:
        ent = specs.NAMES[name]
        if ent['variant_of'] and (not only or ent['variant_of'] in only or name in only):
            base = man['names'][ent['variant_of']]
            u = used.setdefault(ent['variant_of'], {base['default']})
            ok = [i for i in base['order'] if base['takes'][i]['ok'] and i not in u]
            dflt = ent['default'] if ent['default'] in ok else (max(ok, key=lambda i: base['takes'][i]['score']) if ok else ent['default'])
            u.add(dflt)
            prev = man['names'].get(name, {})
            man['names'][name] = dict(grp=ent['grp'], voice=ent['voice'], word=ent['word'], desc=ent['desc'], lo=ent['lo'], hi=ent['hi'],
                                      loop=False, loud=ent['loud'], variant_of=ent['variant_of'], default=dflt,
                                      pinned=prev.get('pinned', False), installed=prev.get('installed'))
    # install defaults (pinned choices are re-copied from the re-mastered take)
    if not a.no_install:
        for name in specs.ORDER:
            ent = man['names'].get(name)
            if not ent or (only and name not in only and specs.NAMES[name]['variant_of'] not in (only or ())):
                continue
            take = ent['installed'] if (ent.get('pinned') and ent.get('installed') not in (None, 'ORIGINAL')) else ent['default']
            if ent.get('pinned') and ent.get('installed') == 'ORIGINAL':
                continue
            P.install(man, name, take, pin=ent.get('pinned', False))
    P.save(man)
    P.rebuild()
    print('mastered in %.0fs; takes %.0f KB' % (time.time() - t0, total / 1024))
    return 0


if __name__ == '__main__':
    sys.exit(main())
