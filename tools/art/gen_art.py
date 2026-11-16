"""Batch-generate candidates for every image in art_defs.ITEMS (local ComfyUI, one GPU).

  python tools/art/gen_art.py                 # everything missing
  python tools/art/gen_art.py boss_ice title  # only these names
  python tools/art/gen_art.py --redo title    # regenerate even if the take exists
  python tools/art/gen_art.py --takes c title # only take 'c'

All jobs are queued at once (ComfyUI still runs them strictly one after another) so the 12 GB model stays
loaded instead of being swapped out between jobs when other agents also use the GPU.
Per take: assets/raw_art/<name>_<take>.png (lossless) + .webp (what ships), scored; then the best-scoring
take becomes the default in assets/art/<name>.webp unless promote.py already made a manual pick.
"""
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import artlib as A  # noqa: E402
import comfy_art as C  # noqa: E402
from art_defs import ITEMS, PARTS  # noqa: E402

cc = C.cc
ALL = dict(ITEMS)
ALL.update(PARTS)   # parts = raw ingredients (cut-out dudes, backgrounds) that compose_title.py assembles


def seed_for(name, take):
    h = int(hashlib.md5(('%s:%s' % (name, take)).encode()).hexdigest()[:8], 16)
    return h % 2_000_000_000


def submit(graph):
    r = json.loads(cc._req('/prompt', {'prompt': graph, 'client_id': cc.CLIENT}))
    if r.get('node_errors'):
        raise RuntimeError('node errors: ' + json.dumps(r['node_errors'])[:1500])
    return r['prompt_id']


def wait(pid, timeout=5400):
    t0 = time.time()
    while True:
        h = json.loads(cc._req('/history/' + pid))
        if pid in h:
            st = h[pid].get('status', {}) or {}
            if st.get('status_str') == 'error':
                raise RuntimeError('comfy error: ' + json.dumps(st.get('messages', []))[:800])
            if st.get('completed') or h[pid].get('outputs'):
                return h[pid]
        if time.time() - t0 > timeout:
            raise TimeoutError(pid)
        time.sleep(2)


def main(argv):
    redo = '--redo' in argv
    only_takes = argv[argv.index('--takes') + 1] if '--takes' in argv else None
    names = [a for a in argv if a in ALL] or list(ITEMS)
    scores = A.load_json(A.SCORES, {})
    chosen = A.load_json(A.CHOSEN, {})
    os.makedirs(A.RAW, exist_ok=True)
    os.makedirs(A.ART, exist_ok=True)

    jobs = []  # (name, take, prompt_id)
    for name in names:
        it = ALL[name]
        for take in it['takes']:
            if only_takes and take not in only_takes:
                continue
            if name in ITEMS and it['kind'] == 'title' and take in 'def':
                continue  # composited by compose_title.py
            if os.path.exists(A.raw_png(name, take)) and not redo:
                continue
            g = C.zimage_graph(it.get('prompts', {}).get(take, it['prompt']), it['gen'][0], it['gen'][1], seed_for(name, take),
                               'stickdoosh/art/%s_%s' % (name, take))
            try:
                jobs.append((name, take, submit(g)))
            except Exception as e:
                print('SUBMIT FAIL %s_%s: %s' % (name, take, str(e)[:400]), flush=True)
    print('queued %d jobs' % len(jobs), flush=True)

    t_start = time.time()
    done_names = set()
    for name, take, pid in jobs:
        it = ALL[name]
        try:
            hist = wait(pid)
            imgs = C.fetch_images(hist)
            if not imgs:
                raise RuntimeError('no image output')
        except Exception as e:
            print('FAIL %s_%s: %s' % (name, take, str(e)[:400]), flush=True)
            continue
        png = A.raw_png(name, take)
        with open(png, 'wb') as f:
            f.write(imgs[0][1])
        if it['kind'] == 'part':
            print('%-16s %s t=%4.0fs (part png saved)' % (name, take, time.time() - t_start), flush=True)
            continue
        sz = A.to_webp(png, A.raw_webp(name, take), it['out'], it['q'])
        m = A.metrics(png, it['kind'])
        m['bytes'] = sz
        m['seed'] = seed_for(name, take)
        scores['%s_%s' % (name, take)] = m
        A.save_json(A.SCORES, scores)
        print('%-16s %s t=%4.0fs webp %6d B score %6.2f ok=%s ink=%.2f edge=%.2f sat=%.2f' % (
            name, take, time.time() - t_start, sz, m['score'], m['ok'], m['ink'], m['edge'], m['sat']), flush=True)
        done_names.add(name)

    # (re)pick defaults unless the user promoted one by hand
    scores = A.load_json(A.SCORES, {})
    for name in [n for n in names if n in ITEMS]:
        it = ITEMS[name]
        for take in it['takes']:  # re-score existing candidates with the current checks
            if os.path.exists(A.raw_png(name, take)):
                A.register(name, take, it)
        cur = chosen.get(name)
        if cur and not cur.get('auto', True):
            continue
        best = A.pick_default(name, it['takes'])
        if best:
            A.to_webp(A.raw_png(name, best), os.path.join(A.ART, name + '.webp'), it['out'], it['q'])
            chosen[name] = {'take': best, 'auto': True}
            A.save_json(A.CHOSEN, chosen)
            print('default %-16s -> take %s' % (name, best), flush=True)
    print('DONE', flush=True)


if __name__ == '__main__':
    main(sys.argv[1:])
