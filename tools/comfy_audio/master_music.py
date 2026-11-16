"""Analyse + master every raw music candidate, write audition previews, encode defaults.

  python master_music.py            # all candidates found in assets/raw_audio/music
  python master_music.py --only title
  python master_music.py --analyze-only title_abP1 title_abP2

Per candidate: objective checks (duration, silence, loudness, clipping, guitar-band energy), loop cut
(80-102 s, start/end chosen by spectral+rhythm similarity, 0.25 s seam cross-fade, 30 ms edge fades),
-14 LUFS normalisation, -1.5 dBFS limiter, 112 kbps stereo MP3 preview.
Default per track = candidate A unless it has objective problems (or tools/comfy_audio/choices.json
says otherwise). The default preview is copied to assets/music/<id>.mp3.
"""
import argparse
import glob
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audiolib as al  # noqa: E402
import defs  # noqa: E402

MANIFEST = os.path.join(defs.HERE, 'music_manifest.json')
CHOICES = os.path.join(defs.HERE, 'choices.json')


def load_json(p, d):
    try:
        with open(p, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return d


def process(wav):
    sr, x = al.read_wav(wav)
    raw = al.analyze_music(x, sr)
    y, info = al.master_music(x, sr)
    mast = al.analyze_music(y, sr)
    return sr, y, raw, info, mast


def master_one(tid, cand, write_preview=True):
    wav = os.path.join(defs.RAW_MUSIC, '%s_%s.wav' % (tid, cand))
    sr, y, raw, info, mast = process(wav)
    ent = {'wav': os.path.relpath(wav, defs.ROOT).replace('\\', '/'), 'raw': raw, 'master': info,
           'problems': al.music_problems(mast), 'score': al.music_score(raw)}
    meta = load_json(wav[:-4] + '.json', {})
    ent['prompt'] = meta.get('prompt')
    ent['seed'] = meta.get('seed')
    ent['pipeline'] = meta.get('pipeline')
    if write_preview:
        pv = os.path.join(defs.PREV_MUSIC, '%s_%s.mp3' % (tid, cand))
        ent['preview_bytes'] = al.encode_mp3(pv, y, sr, defs.MUSIC_KBPS)
        ent['preview'] = os.path.relpath(pv, defs.ROOT).replace('\\', '/')
    return ent


def pick_default(tid, cands, choices):
    if tid in choices.get('music', {}) and choices['music'][tid] in cands:
        return choices['music'][tid], 'user choice'
    order = sorted(cands.keys(), key=lambda c: (c != 'A', c != 'B', c))
    for c in order:
        if not cands[c]['problems']:
            return c, 'first candidate without objective problems'
    best = max(cands, key=lambda c: cands[c]['score'])
    return best, 'all candidates flagged; highest objective score'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default=None)
    ap.add_argument('--analyze-only', nargs='*', default=None)
    a = ap.parse_args()
    if a.analyze_only:
        for stem in a.analyze_only:
            sr, y, raw, info, mast = process(os.path.join(defs.RAW_MUSIC, stem + '.wav'))
            print(stem, json.dumps({'raw': raw, 'master': info, 'problems': al.music_problems(mast),
                                    'score': al.music_score(raw)}, indent=1))
        return
    man = load_json(MANIFEST, {})
    choices = load_json(CHOICES, {})
    ids = [a.only] if a.only else defs.MUSIC_IDS
    for tid in ids:
        wavs = sorted(glob.glob(os.path.join(defs.RAW_MUSIC, tid + '_*.wav')))
        if not wavs:
            print('no candidates for', tid)
            continue
        cands = {}
        for w in wavs:
            c = os.path.basename(w)[len(tid) + 1:-4]
            cands[c] = master_one(tid, c)
            e = cands[c]
            print('%-9s %-5s dur %5.1f lufs %6.2f->%6.2f loop %.3f guitar %.2f crunch %.2f probs %s' % (
                tid, c, e['master']['dur_s'], e['raw']['lufs'], e['master']['lufs_out'], e['master']['loop_score'],
                e['raw']['guitar_100_5k'], e['raw']['crunch_1k_5k'], e['problems']), flush=True)
        d, why = pick_default(tid, cands, choices)
        os.makedirs(defs.OUT_MUSIC, exist_ok=True)
        dst = os.path.join(defs.OUT_MUSIC, tid + '.mp3')
        shutil.copyfile(os.path.join(defs.ROOT, cands[d]['preview']), dst)
        man[tid] = {'default': d, 'why': why, 'file': 'assets/music/%s.mp3' % tid,
                    'bytes': os.path.getsize(dst), 'cands': cands}
        print('  -> default', d, '(%s)' % why, flush=True)
        with open(MANIFEST, 'w', encoding='utf-8') as f:
            json.dump(man, f, indent=1)
    tot = sum(os.path.getsize(p) for p in glob.glob(os.path.join(defs.OUT_MUSIC, '*.mp3')))
    print('assets/music total: %.2f MB' % (tot / 1e6))


if __name__ == '__main__':
    main()
