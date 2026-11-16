"""Shared helpers: paths, png->webp, objective image checks (no eyes involved), default picking."""
import json
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
RAW = os.path.join(ROOT, 'assets', 'raw_art')      # gitignored (assets/raw*/)
ART = os.path.join(ROOT, 'assets', 'art')          # shipped
SCORES = os.path.join(RAW, 'scores.json')
CHOSEN = os.path.join(RAW, 'chosen.json')          # {name: take}


def load_json(p, default):
    try:
        with open(p, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def save_json(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=1, sort_keys=True)


def raw_png(name, take):
    return os.path.join(RAW, '%s_%s.png' % (name, take))


def raw_webp(name, take):
    return os.path.join(RAW, '%s_%s.webp' % (name, take))


def to_webp(src_png, dst, size, q):
    im = Image.open(src_png).convert('RGB')
    if im.size != tuple(size):
        im = im.resize(tuple(size), Image.LANCZOS)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    im.save(dst, 'WEBP', quality=int(q), method=6)
    return os.path.getsize(dst)


def _band(v, lo, hi, soft):
    """1.0 inside [lo,hi], falling linearly to 0 over `soft` outside."""
    if v < lo:
        return max(0.0, 1.0 - (lo - v) / soft)
    if v > hi:
        return max(0.0, 1.0 - (v - hi) / soft)
    return 1.0


def metrics(png_path, kind='boss'):
    im = Image.open(png_path).convert('RGB')
    im.thumbnail((512, 512))
    a = np.asarray(im).astype(np.float32) / 255.0
    lum = a @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    mx, mn = a.max(2), a.min(2)
    sat = np.where(mx > 1e-3, (mx - mn) / np.maximum(mx, 1e-3), 0)
    q = (a * 15).astype(np.int32)
    key = q[..., 0] * 256 + q[..., 1] * 16 + q[..., 2]
    vals, cnt = np.unique(key, return_counts=True)
    gx = np.abs(np.diff(lum, axis=1))[:-1, :]
    gy = np.abs(np.diff(lum, axis=0))[:, :-1]
    edge = (np.maximum(gx, gy) > 0.18)
    h = edge.shape[0]
    m = {
        'mean_lum': float(lum.mean()), 'std_lum': float(lum.std()),
        'ncolors': int(len(vals)), 'dominant': float(cnt.max() / cnt.sum()),
        'ink': float((lum < 0.16).mean()), 'edge': float(edge.mean()), 'sat': float(sat.mean()),
        'edge_top': float(edge[: int(h * 0.30)].mean()), 'edge_bot': float(edge[int(h * 0.40):].mean()),
    }
    w = edge.shape[1]
    # the menu column (~330px) sits over the middle 20% of the title: fewer details there = squad not hidden
    m['edge_mid'] = float(edge[int(h * 0.40):, int(w * 0.40): int(w * 0.60)].mean())
    m['edge_sides'] = float(np.concatenate([edge[int(h * 0.40):, int(w * 0.10): int(w * 0.38)].ravel(),
                                            edge[int(h * 0.40):, int(w * 0.62): int(w * 0.90)].ravel()]).mean())
    ok = (0.12 < m['mean_lum'] < 0.92 and m['std_lum'] > 0.10 and m['ncolors'] >= 40 and m['dominant'] < 0.75
          and m['edge'] > 0.01)
    m['ok'] = bool(ok)
    s = 0.0
    s += _band(m['ink'], 0.04, 0.35, 0.05) * 1.5            # thick black ink lines present
    s += _band(m['edge'], 0.05, 0.28, 0.05) * 1.5           # fine detail but not noise
    s += min(m['sat'] / 0.45, 1.0)                            # saturated flat colour
    s += min(m['ncolors'] / 250.0, 1.0) * 0.5
    s -= max(0.0, m['dominant'] - 0.35) * 2.0                 # one colour swallowing the frame
    if kind == 'title':                                       # calm top area for the CSS logo
        s += (1.0 - min(m['edge_top'] / max(m['edge_bot'], 1e-4), 1.0)) * 1.5
        s += (1.0 - min(m['edge_mid'] / max(m['edge_sides'], 1e-4), 1.0)) * 1.5   # squad beside the menu, not under it
    m['score'] = round(float(s) if ok else float(s) - 10.0, 3)
    return m


def register(name, take, it):
    """Make the webp, score a (new or re-done) candidate and store it in scores.json."""
    png = raw_png(name, take)
    sz = to_webp(png, raw_webp(name, take), it['out'], it['q'])
    m = metrics(png, it['kind'])
    m['bytes'] = sz
    sc = load_json(SCORES, {})
    old = sc.get('%s_%s' % (name, take), {})
    m['seed'] = old.get('seed', 0)
    sc['%s_%s' % (name, take)] = m
    save_json(SCORES, sc)
    return m


def pick_default(name, takes):
    """Highest objective score wins. Returns take letter or None."""
    sc = load_json(SCORES, {})
    best, bs = None, -1e9
    for t in takes:
        r = sc.get('%s_%s' % (name, t))
        if r and r['score'] > bs:
            best, bs = t, r['score']
    return best
