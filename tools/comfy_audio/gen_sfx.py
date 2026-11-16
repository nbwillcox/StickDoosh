"""Generate raw SFX takes with Stable Audio 3 Medium (pipeline P2 settings) via the local ComfyUI.

  python gen_sfx.py                 # all SFX, 3 takes each (one batched job per SFX)
  python gen_sfx.py --names pistol,mg --takes 3 --force --seed 99

Writes assets/raw_audio/sfx/<name>_<k>.wav (+ .json). Existing takes are skipped unless --force.
"""
import argparse
import json
import os
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audiolib as al  # noqa: E402
import comfy_client as cc  # noqa: E402
import defs  # noqa: E402

SFX_PIPE = dict(defs.PIPELINES['P2'])
SFX_PIPE['negative'] = 'music, melody, singing, voice, speech, background noise, hum, reverb wash, quiet, muffled'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--names', default='all')
    ap.add_argument('--takes', type=int, default=3)
    ap.add_argument('--first', type=int, default=1, help='number of the first take (to add more takes)')
    ap.add_argument('--seed', type=int, default=None)
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args()
    names = defs.SFX_IDS if a.names == 'all' else a.names.split(',')
    os.makedirs(defs.RAW_SFX, exist_ok=True)
    for nm in names:
        ks = list(range(a.first, a.first + a.takes))
        wavs = [os.path.join(defs.RAW_SFX, '%s_%d.wav' % (nm, k)) for k in ks]
        if not a.force and all(os.path.exists(w) for w in wavs):
            print('skip', nm, flush=True)
            continue
        prompt = defs.sfx_prompt(nm)
        secs = defs.SFX[nm][2]
        seed = a.seed if a.seed is not None else (zlib.crc32(('sfx-%s-%d' % (nm, a.first)).encode()) & 0x7fffffff)
        try:
            files, dt = cc.generate(prompt, secs, seed, batch=len(ks), prefix='stickdoosh/sfx_%s' % nm, **SFX_PIPE)
        except Exception as e:
            print('  FAILED', nm, repr(e)[:800], flush=True)
            continue
        for i, (k, w) in enumerate(zip(ks, wavs)):
            if i >= len(files):
                continue
            sr, x = al.decode(files[i][1])
            al.write_wav(w, sr, x)
            with open(w[:-4] + '.json', 'w', encoding='utf-8') as f:
                json.dump({'name': nm, 'take': k, 'prompt': prompt, 'seconds': secs, 'seed': seed, 'batch_index': i,
                           'pipeline_cfg': SFX_PIPE, 'gen_s': round(dt, 1)}, f, indent=1)
        print('gen', nm, '%d takes in %.1fs' % (len(files), dt), flush=True)


if __name__ == '__main__':
    main()
