"""Trim/normalise every raw SFX take, score them objectively, write previews, encode the best.

  python master_sfx.py              # all
  python master_sfx.py --only pistol

Per take: mono, DC-blocked, start at the onset (-30 dB re peak, 4 ms pre-roll), end where the envelope
drops below -48 dB (capped per SFX), short fades, peak-normalised to -1 dBFS, 96 kbps mono MP3.
`heli` instead gets a 1.4-2.0 s loop cut from the steady middle (cross-faded seam).
Best take = highest objective score (non-silent, onset near start, little pre-noise, not truncated,
single event for one-shot sounds) unless tools/comfy_audio/choices.json names a take.
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

MANIFEST = os.path.join(defs.HERE, 'sfx_manifest.json')
CHOICES = os.path.join(defs.HERE, 'choices.json')


def load_json(p, d):
    try:
        with open(p, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return d


def render_take(nm, take):
    """Process one raw take. Returns (y, sr, info) — y None if unusable."""
    wav = os.path.join(defs.RAW_SFX, '%s_%s.wav' % (nm, take))
    sr, x = al.read_wav(wav)
    _p, _l, _g, max_len, kind = defs.SFX[nm]
    raw_peak = al.peak_db(x)
    if kind == 'loop':
        y, info = al.loop_sfx(x, sr, min_len=1.4, max_len=max_len)
    else:
        y, info = al.process_sfx(x, sr, max_len=max_len)
    info['raw_peak_db'] = round(raw_peak, 1)
    info['score'] = score(info, kind, max_len)
    return y, sr, info


def score(i, kind, max_len):
    if not i.get('ok') or i.get('raw_peak_db', -99) < -40:
        return -9.0
    if kind == 'loop':
        return round(i.get('loop_corr', 0.0), 3)
    s = 1.0
    s -= 1.5 * max(0.0, i['onset_s'] - 0.15)
    if i['pre_noise_db'] > -40:
        s -= 0.02 * (i['pre_noise_db'] + 40)
    if i['truncated']:
        s -= 0.4 if kind == 'one' else 0.15
    if kind == 'one' and i['events'] > 1:
        s -= 0.5 * (i['events'] - 1)
    if kind == 'multi' and i['events'] > 4:
        s -= 0.1 * (i['events'] - 4)
    if kind != 'one' and i['dur_s'] < 0.25 * max_len:
        s -= 0.3
    if i['dur_s'] < 0.08:
        s -= 1.0
    return round(s, 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default=None)
    a = ap.parse_args()
    man = load_json(MANIFEST, {})
    choices = load_json(CHOICES, {})
    names = [a.only] if a.only else defs.SFX_IDS
    os.makedirs(defs.OUT_SFX, exist_ok=True)
    for nm in names:
        takes = sorted(os.path.basename(w)[len(nm) + 1:-4]
                       for w in glob.glob(os.path.join(defs.RAW_SFX, nm + '_*.wav'))
                       if os.path.basename(w)[len(nm) + 1:-4].isdigit())
        if not takes:
            print('no takes for', nm)
            continue
        ent = {}
        for t in takes:
            y, sr, info = render_take(nm, t)
            if y is not None:
                pv = os.path.join(defs.PREV_SFX, '%s_%s.mp3' % (nm, t))
                info['preview_bytes'] = al.encode_mp3(pv, y, sr, defs.SFX_KBPS)
                info['preview'] = os.path.relpath(pv, defs.ROOT).replace('\\', '/')
            info['wav'] = 'assets/raw_audio/sfx/%s_%s.wav' % (nm, t)
            ent[t] = info
        usable = [t for t in takes if ent[t].get('preview')]
        if not usable:
            print('!! no usable take for', nm)
            continue
        if nm in choices.get('sfx', {}) and choices['sfx'][nm] in usable:
            best, why = choices['sfx'][nm], 'user choice'
        else:
            best, why = max(usable, key=lambda t: (ent[t]['score'], -int(t))), 'highest objective score'
        dst = os.path.join(defs.OUT_SFX, nm + '.mp3')
        shutil.copyfile(os.path.join(defs.ROOT, ent[best]['preview']), dst)
        man[nm] = {'default': best, 'why': why, 'file': 'assets/sfx/%s.mp3' % nm, 'bytes': os.path.getsize(dst),
                   'prompt': defs.sfx_prompt(nm), 'takes': ent}
        print('%-13s best %s  ' % (nm, best) + '  '.join(
            '%s:%+.2f %.2fs ev%s%s' % (t, ent[t]['score'], ent[t].get('dur_s', 0), ent[t].get('events', '-'),
                                      ' T' if ent[t].get('truncated') else '') for t in takes), flush=True)
    with open(MANIFEST, 'w', encoding='utf-8') as f:
        json.dump(man, f, indent=1)
    tot = sum(os.path.getsize(p) for p in glob.glob(os.path.join(defs.OUT_SFX, '*.mp3')))
    print('assets/sfx total: %.1f KB' % (tot / 1e3))


if __name__ == '__main__':
    main()
