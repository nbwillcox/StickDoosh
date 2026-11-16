"""Generate raw music candidates with Stable Audio 3 Medium via the local ComfyUI.

  python gen_music.py --ids all --pipeline P1 --cands A,B
  python gen_music.py --ids title --pipeline P2 --cands abP2 --seed 777

One ComfyUI job per track (batch = number of candidates), submitted sequentially.
Writes assets/raw_audio/music/<id>_<cand>.wav + .json sidecar. Existing WAVs are skipped (resume-safe).
"""
import argparse
import json
import os
import sys
import time
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audiolib as al  # noqa: E402
import comfy_client as cc  # noqa: E402
import defs  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ids', default='all')
    ap.add_argument('--pipeline', default='P1')
    ap.add_argument('--cands', default='A,B')
    ap.add_argument('--seconds', type=float, default=defs.MUSIC_SECONDS)
    ap.add_argument('--seed', type=int, default=None)
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args()
    ids = defs.MUSIC_IDS if a.ids == 'all' else a.ids.split(',')
    cands = a.cands.split(',')
    pl = defs.PIPELINES[a.pipeline]
    os.makedirs(defs.RAW_MUSIC, exist_ok=True)
    for tid in ids:
        wavs = [os.path.join(defs.RAW_MUSIC, '%s_%s.wav' % (tid, c)) for c in cands]
        if not a.force and all(os.path.exists(w) for w in wavs):
            print('skip', tid, flush=True)
            continue
        prompt = defs.music_prompt(tid, a.seconds)
        seed = a.seed if a.seed is not None else (zlib.crc32(('doosh-' + tid).encode()) & 0x7fffffff)
        print('gen', tid, a.pipeline, cands, 'seed', seed, flush=True)
        t0 = time.time()
        try:
            files, dt = cc.generate(prompt, a.seconds, seed, batch=len(cands),
                                    prefix='stickdoosh/music_%s' % tid, **pl)
        except Exception as e:  # keep going with the other tracks
            print('  FAILED', tid, repr(e)[:800], flush=True)
            continue
        for i, (c, w) in enumerate(zip(cands, wavs)):
            if i >= len(files):
                print('  missing output for', c, flush=True)
                continue
            sr, x = al.decode(files[i][1])
            al.write_wav(w, sr, x)
            meta = {'id': tid, 'cand': c, 'pipeline': a.pipeline, 'pipeline_cfg': pl, 'prompt': prompt,
                    'seconds': a.seconds, 'seed': seed, 'batch_index': i, 'comfy_file': files[i][0],
                    'gen_s': round(dt, 1), 'model': 'stable_audio_3_medium.safetensors + t5gemma_b_b_ul2'}
            with open(w[:-4] + '.json', 'w', encoding='utf-8') as f:
                json.dump(meta, f, indent=1)
            print('  saved', os.path.basename(w), '%.1fs audio' % (x.shape[1] / sr), flush=True)
        print('  done in %.1fs' % (time.time() - t0), flush=True)


if __name__ == '__main__':
    main()
