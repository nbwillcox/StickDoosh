"""Swap a different candidate into the game.

  python tools/comfy_audio/promote.py <id> <candidate>
    music:  promote.py title B        (candidates: A, B, plus title A/B test takes like abP2s5151)
    sfx:    promote.py pistol 2       (takes: 1, 2, 3)

Re-masters the candidate from its raw WAV in assets/raw_audio/ (same chain as the batch scripts),
overwrites assets/music/<id>.mp3 or assets/sfx/<id>.mp3, stores the pick in
tools/comfy_audio/choices.json (so later batch re-runs keep it) and rebuilds tools/audition.html.
Run with the ComfyUI venv python (has numpy/scipy/PyAV):
  "C:\\Users\\nicho\\Documents\\ComfyUI\\.venv\\Scripts\\python.exe" tools/comfy_audio/promote.py title B
"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audiolib as al  # noqa: E402
import build_audition  # noqa: E402
import defs  # noqa: E402
import master_music as mmod  # noqa: E402
import master_sfx as smod  # noqa: E402

CHOICES = os.path.join(defs.HERE, 'choices.json')


def save_json(p, d):
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(d, f, indent=1)


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    tid, cand = sys.argv[1], sys.argv[2]
    choices = mmod.load_json(CHOICES, {})
    if tid in defs.MUSIC_IDS:
        wav = os.path.join(defs.RAW_MUSIC, '%s_%s.wav' % (tid, cand))
        if not os.path.exists(wav):
            sys.exit('no such candidate: ' + wav)
        ent = mmod.master_one(tid, cand)
        dst = os.path.join(defs.OUT_MUSIC, tid + '.mp3')
        shutil.copyfile(os.path.join(defs.ROOT, ent['preview']), dst)
        man = mmod.load_json(mmod.MANIFEST, {})
        t = man.setdefault(tid, {'cands': {}, 'file': 'assets/music/%s.mp3' % tid})
        t['cands'][cand] = ent
        t.update({'default': cand, 'why': 'user choice', 'bytes': os.path.getsize(dst)})
        save_json(mmod.MANIFEST, man)
        choices.setdefault('music', {})[tid] = cand
        print('music %s <- %s  (%.1f s, %.2f LUFS, %d KB)' % (tid, cand, ent['master']['dur_s'],
                                                           ent['master']['lufs_out'], os.path.getsize(dst) // 1000))
    elif tid in defs.SFX_IDS:
        wav = os.path.join(defs.RAW_SFX, '%s_%s.wav' % (tid, cand))
        if not os.path.exists(wav):
            sys.exit('no such take: ' + wav)
        y, sr, info = smod.render_take(tid, cand)
        if y is None:
            sys.exit('take is unusable: %s' % info)
        pv = os.path.join(defs.PREV_SFX, '%s_%s.mp3' % (tid, cand))
        info['preview_bytes'] = al.encode_mp3(pv, y, sr, defs.SFX_KBPS)
        info['preview'] = os.path.relpath(pv, defs.ROOT).replace('\\', '/')
        info['wav'] = 'assets/raw_audio/sfx/%s_%s.wav' % (tid, cand)
        dst = os.path.join(defs.OUT_SFX, tid + '.mp3')
        shutil.copyfile(pv, dst)
        man = smod.load_json(smod.MANIFEST, {})
        t = man.setdefault(tid, {'takes': {}, 'file': 'assets/sfx/%s.mp3' % tid, 'prompt': defs.sfx_prompt(tid)})
        t['takes'][cand] = info
        t.update({'default': cand, 'why': 'user choice', 'bytes': os.path.getsize(dst)})
        save_json(smod.MANIFEST, man)
        choices.setdefault('sfx', {})[tid] = cand
        print('sfx %s <- take %s  (%.2f s, %d bytes)' % (tid, cand, info['dur_s'], os.path.getsize(dst)))
    else:
        sys.exit('unknown id %r (music: %s | sfx: %s)' % (tid, ' '.join(defs.MUSIC_IDS), ' '.join(defs.SFX_IDS)))
    save_json(CHOICES, choices)
    build_audition.main()


if __name__ == '__main__':
    main()
