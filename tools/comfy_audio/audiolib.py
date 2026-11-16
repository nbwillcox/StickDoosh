"""Audio helpers for Stick Doosh: decode, WAV I/O, BS.1770 loudness, analysis, loop cutting,
mastering and MP3 encoding (PyAV libmp3lame; no ffmpeg binary needed).

Arrays are float32 shaped (channels, samples) in [-1, 1].
"""
import io
import os

import numpy as np
import scipy.io.wavfile as wavfile
import scipy.ndimage as ndi
import scipy.signal as sig

# ----------------------------------------------------------------------------- I/O

def decode(src):
    """Decode any audio file (path or bytes) with PyAV -> (sr, float32 [ch, n])."""
    import av
    f = io.BytesIO(src) if isinstance(src, (bytes, bytearray)) else src
    with av.open(f) as c:
        st = c.streams.audio[0]
        chunks = []
        sr = st.codec_context.sample_rate
        for fr in c.decode(st):
            a = fr.to_ndarray()
            if fr.format.is_packed:
                a = a.reshape(-1, len(fr.layout.channels)).T
            if a.dtype.kind == 'i':
                a = a.astype(np.float32) / float(np.iinfo(a.dtype).max)
            chunks.append(a.astype(np.float32))
    return sr, np.concatenate(chunks, axis=1)


def write_wav(path, sr, x):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    y = np.clip(x, -1.0, 1.0)
    wavfile.write(path, sr, (y.T * 32767.0).astype(np.int16))


def read_wav(path):
    sr, d = wavfile.read(path)
    if d.dtype.kind == 'i':
        d = d.astype(np.float32) / float(np.iinfo(d.dtype).max)
    d = d.astype(np.float32)
    if d.ndim == 1:
        d = d[None, :]
    else:
        d = d.T
    return sr, np.ascontiguousarray(d)


def encode_mp3(path, x, sr, kbps):
    """CBR MP3 via PyAV/libmp3lame. x: (ch, n) float32, ch 1 or 2."""
    import av
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ch = x.shape[0]
    layout = 'stereo' if ch == 2 else 'mono'
    x = np.ascontiguousarray(np.clip(x, -1.0, 1.0).astype(np.float32))
    tmp = path + '.tmp'
    out = av.open(tmp, 'w', format='mp3')
    st = out.add_stream('libmp3lame', rate=sr, layout=layout)
    st.bit_rate = int(kbps * 1000)
    fs = 1152
    n = x.shape[1]
    for i in range(0, n, fs):
        chunk = np.ascontiguousarray(x[:, i:i + fs])
        fr = av.AudioFrame.from_ndarray(chunk, format='fltp', layout=layout)
        fr.sample_rate = sr
        fr.pts = i
        for p in st.encode(fr):
            out.mux(p)
    for p in st.encode(None):
        out.mux(p)
    out.close()
    os.replace(tmp, path)
    return os.path.getsize(path)

# ----------------------------------------------------------------------------- loudness

def _biquad_shelf(fs, G=3.99984385397, Q=0.7071752369554193, fc=1681.9744509555319):
    A = 10 ** (G / 40.0)
    w0 = 2 * np.pi * fc / fs
    alpha = np.sin(w0) / (2 * Q)
    c = np.cos(w0)
    b = [A * ((A + 1) + (A - 1) * c + 2 * np.sqrt(A) * alpha), -2 * A * ((A - 1) + (A + 1) * c),
         A * ((A + 1) + (A - 1) * c - 2 * np.sqrt(A) * alpha)]
    a = [(A + 1) - (A - 1) * c + 2 * np.sqrt(A) * alpha, 2 * ((A - 1) - (A + 1) * c),
         (A + 1) - (A - 1) * c - 2 * np.sqrt(A) * alpha]
    return np.array(b) / a[0], np.array(a) / a[0]


def _biquad_hp(fs, Q=0.5003270373253953, fc=38.13547087613982):
    w0 = 2 * np.pi * fc / fs
    alpha = np.sin(w0) / (2 * Q)
    c = np.cos(w0)
    b = [(1 + c) / 2, -(1 + c), (1 + c) / 2]
    a = [1 + alpha, -2 * c, 1 - alpha]
    return np.array(b) / a[0], np.array(a) / a[0]


def lufs(x, sr):
    """Integrated loudness (ITU-R BS.1770-4, gated). Returns -inf-ish (-99) for silence."""
    b1, a1 = _biquad_shelf(sr)
    b2, a2 = _biquad_hp(sr)
    y = sig.lfilter(b2, a2, sig.lfilter(b1, a1, x, axis=1), axis=1)
    blk = int(0.4 * sr)
    hop = int(0.1 * sr)
    if y.shape[1] < blk:
        z = np.mean(y ** 2, axis=1).sum()
        return float(-0.691 + 10 * np.log10(z + 1e-12))
    p = y ** 2
    cs = np.concatenate([np.zeros((p.shape[0], 1)), np.cumsum(p, axis=1)], axis=1)
    starts = np.arange(0, y.shape[1] - blk + 1, hop)
    z = ((cs[:, starts + blk] - cs[:, starts]) / blk).sum(axis=0)
    l = -0.691 + 10 * np.log10(z + 1e-12)
    g = z[l > -70]
    if g.size == 0:
        return -99.0
    rel = -0.691 + 10 * np.log10(g.mean()) - 10
    g2 = z[(l > -70) & (l > rel)]
    if g2.size == 0:
        return -99.0
    return float(-0.691 + 10 * np.log10(g2.mean()))


def true_peak_db(x, sr):
    y = sig.resample_poly(x, 4, 1, axis=1)
    return float(20 * np.log10(np.max(np.abs(y)) + 1e-12))


def peak_db(x):
    return float(20 * np.log10(np.max(np.abs(x)) + 1e-12))


def limit(x, sr, ceiling_db=-1.5, look_ms=5.0):
    """Look-ahead brickwall limiter (sample peak). Never overshoots the ceiling."""
    thr = 10 ** (ceiling_db / 20.0)
    a = np.max(np.abs(x), axis=0)
    if a.max() <= thr:
        return x
    g = np.minimum(1.0, thr / np.maximum(a, 1e-9))
    L = max(3, int(sr * look_ms / 1000.0) | 1)
    g = ndi.minimum_filter1d(g, L, mode='nearest')
    g = ndi.uniform_filter1d(g, L, mode='nearest')
    return x * g[None, :]

# ----------------------------------------------------------------------------- analysis

def band_shares(x, sr):
    mono = x.mean(axis=0)
    f, P = sig.welch(mono, sr, nperseg=8192)
    tot = P[(f >= 20)].sum() + 1e-20

    def sh(lo, hi):
        return float(P[(f >= lo) & (f < hi)].sum() / tot)
    cen = float((f * P).sum() / (P.sum() + 1e-20))
    m = (f >= 300) & (f < 5000)
    flat = float(np.exp(np.mean(np.log(P[m] + 1e-20))) / (np.mean(P[m]) + 1e-20))
    return {'sub_lt100': sh(20, 100), 'body_100_1k': sh(100, 1000), 'crunch_1k_5k': sh(1000, 5000),
            'air_5k_16k': sh(5000, 16000), 'guitar_100_5k': sh(100, 5000), 'centroid_hz': cen,
            'flatness_300_5k': flat}


def analyze_music(x, sr):
    n = x.shape[1]
    w = int(0.05 * sr)
    k = n // w
    r = np.sqrt(np.mean(x[:, :k * w].reshape(x.shape[0], k, w) ** 2, axis=(0, 2)) + 1e-12)
    rdb = 20 * np.log10(r)
    sil = rdb < -50
    longest = 0
    run = 0
    for s in sil:
        run = run + 1 if s else 0
        longest = max(longest, run)
    st = rdb[~sil] if (~sil).any() else rdb
    d = {'dur_s': round(n / sr, 2), 'lufs': round(lufs(x, sr), 2), 'peak_db': round(peak_db(x), 2),
         'clip_frac': float(np.mean(np.abs(x) > 0.999)), 'silence_frac': round(float(sil.mean()), 4),
         'longest_silence_s': round(longest * 0.05, 2), 'rms_db_std': round(float(np.std(st)), 2)}
    d.update({k2: round(v, 4) for k2, v in band_shares(x, sr).items()})
    return d


def music_problems(m, min_dur=70):
    p = []
    if m['dur_s'] < min_dur:
        p.append('short')
    if m['silence_frac'] > 0.03 or m['longest_silence_s'] > 1.5:
        p.append('silence')
    if m['lufs'] < -30 or m['lufs'] > -4:
        p.append('loudness')
    if m['guitar_100_5k'] < 0.35:
        p.append('little guitar-range energy')
    if m['clip_frac'] > 0.002:
        p.append('clipping')
    return p


def music_score(m):
    """Higher = more 'full-band distorted rock' and fewer defects. Objective proxy only."""
    s = 2.0 * m['crunch_1k_5k'] + 1.0 * m['guitar_100_5k'] + 0.5 * m['air_5k_16k'] + 0.5 * m['flatness_300_5k']
    s -= 5.0 * m['silence_frac'] + 0.2 * len(music_problems(m))
    return round(float(s), 4)

# ----------------------------------------------------------------------------- loop cutting

def _feats(mono, sr, hop=512, nfft=2048, nb=40):
    f, _t, Z = sig.stft(mono, sr, nperseg=nfft, noverlap=nfft - hop, boundary=None, padded=False)
    S = np.abs(Z) ** 2
    edges = np.geomspace(40, min(16000, sr / 2 - 1), nb + 1)
    idx = np.digitize(f, edges) - 1
    B = np.zeros((nb, S.shape[1]))
    for kk in range(nb):
        m = idx == kk
        if m.any():
            B[kk] = S[m].sum(axis=0)
    L = np.log10(B + 1e-10)
    on = np.concatenate([[0.0], np.maximum(0, np.diff(L, axis=1)).sum(axis=0)])
    L = (L - L.mean(axis=1, keepdims=True)) / (L.std(axis=1, keepdims=True) + 1e-6)
    return L.T, on, hop


def _zn(v):
    v = v - v.mean(axis=-1, keepdims=True)
    return v / (np.linalg.norm(v, axis=-1, keepdims=True) + 1e-9)


def find_loop(x, sr, min_len=80.0, max_len=102.0, win_s=3.0, tail_guard_s=3.0):
    """Pick (start, end) samples so that the music right after `end` resembles the music right after
    `start` (spectral bands + onset rhythm). Returns dict with a, b (samples) and score in [-1, 1]."""
    mono = x.mean(axis=0)
    F, on, hop = _feats(mono, sr)
    T = F.shape[0]
    fps = sr / hop
    W = int(win_s * fps)
    fr_rms = np.sqrt(np.mean(F ** 2, axis=1))
    lvl = np.array([np.sqrt(np.mean(mono[i * hop:i * hop + hop] ** 2) + 1e-12) for i in range(T)])
    ldb = 20 * np.log10(lvl)
    ref = np.percentile(ldb, 95)
    lead = int(np.argmax(ldb > ref - 30))
    # start candidates: strong onsets within 4 s after the music starts
    seg = on[lead:lead + int(4 * fps)]
    cands = [lead]
    if seg.size > 3:
        pk, _ = sig.find_peaks(seg, height=0.35 * seg.max(), distance=max(1, int(0.15 * fps)))
        cands += [lead + int(p) for p in pk[:8]]
    cands = sorted(set(cands))
    best = None
    lo = int(min_len * fps)
    hi = int(max_len * fps)
    last = T - W - int(tail_guard_s * fps)
    for a in cands:
        bs = np.arange(a + lo, min(a + hi, last))
        if bs.size == 0:
            continue
        A = _zn(F[a:a + W].ravel())
        Ao = _zn(on[a:a + W])
        sc = np.empty(bs.size)
        for j0 in range(0, bs.size, 256):
            bb = bs[j0:j0 + 256]
            blk = np.stack([F[b:b + W].ravel() for b in bb])
            ob = np.stack([on[b:b + W] for b in bb])
            sc[j0:j0 + 256] = 0.6 * (_zn(blk) @ A) + 0.4 * (_zn(ob) @ Ao)
        j = int(np.argmax(sc))
        total = sc[j] - 0.01 * (a - lead) / fps
        if best is None or total > best[0]:
            best = (total, a, int(bs[j]), float(sc[j]))
    if best is None:  # too short: use everything
        return {'a': 0, 'b': x.shape[1], 'score': 0.0}
    _, a, b, s = best
    a_s, b_s = a * hop, b * hop
    # sample-level phase alignment of the end to the start (+-1 hop)
    N = 4096
    ref_w = mono[a_s:a_s + N]
    lags = np.arange(-hop, hop + 1)
    cc = [float(np.dot(ref_w, mono[b_s + d:b_s + d + N])) for d in lags if b_s + d + N < mono.size]
    if cc:
        b_s += int(lags[int(np.argmax(cc))])
    return {'a': int(a_s), 'b': int(b_s), 'score': round(s, 4)}


def cut_loop(x, sr, a, b, xfade_s=0.25, edge_fade_s=0.03):
    """Loop body x[a:b]; its head is cross-faded with the audio that followed `b` so the seam
    end->start is continuous, then 30 ms fades at both edges (protects against MP3 padding clicks)."""
    y = x[:, a:b].copy()
    nx = int(xfade_s * sr)
    nx = min(nx, x.shape[1] - b, y.shape[1] // 4)
    if nx > 16:
        t = np.linspace(0, np.pi / 2, nx)
        y[:, :nx] = y[:, :nx] * np.sin(t)[None, :] + x[:, b:b + nx] * np.cos(t)[None, :]
    ne = int(edge_fade_s * sr)
    if ne > 1:
        r = np.linspace(0.0, 1.0, ne)[None, :]
        y[:, :ne] *= r
        y[:, -ne:] *= r[:, ::-1]
    return y


def master_music(x, sr, target_lufs=-14.0, min_len=80.0, max_len=102.0):
    """Loop-cut + loudness-normalise + limit. Returns (y, info)."""
    x = x - x.mean(axis=1, keepdims=True)
    lp = find_loop(x, sr, min_len=min_len, max_len=max_len)
    y = cut_loop(x, sr, lp['a'], lp['b'])
    l0 = lufs(y, sr)
    y = y * (10 ** ((target_lufs - l0) / 20.0))
    y = limit(y, sr, ceiling_db=-1.5)
    info = {'loop_start_s': round(lp['a'] / sr, 3), 'loop_end_s': round(lp['b'] / sr, 3),
            'loop_score': lp['score'], 'lufs_in': round(l0, 2), 'lufs_out': round(lufs(y, sr), 2),
            'true_peak_db': round(true_peak_db(y, sr), 2), 'dur_s': round(y.shape[1] / sr, 2)}
    return y.astype(np.float32), info

# ----------------------------------------------------------------------------- sfx

def env_db(m, sr, ms=3.0):
    L = max(1, int(sr * ms / 1000.0))
    e = np.sqrt(ndi.uniform_filter1d(m.astype(np.float64) ** 2, L) + 1e-14)
    return 20 * np.log10(e)


def process_sfx(x, sr, max_len=1.0, min_len=0.08, on_db=-30.0, off_db=-48.0, peak_target_db=-1.0):
    """Mono, DC-blocked, trimmed to the main event, faded and peak-normalised. Returns (y, info)."""
    m = x.mean(axis=0)
    b, a = sig.butter(2, 25.0 / (sr / 2), 'highpass')
    m = sig.filtfilt(b, a, m)
    pk = np.max(np.abs(m)) + 1e-12
    e = env_db(m, sr) - 20 * np.log10(pk)
    above = np.nonzero(e > on_db)[0]
    if above.size == 0:
        return None, {'ok': False, 'why': 'silent'}
    on = int(above[0])
    st = max(0, on - int(0.004 * sr))
    pre_noise = float(np.max(e[:st])) if st > int(0.01 * sr) else -99.0
    alive = np.nonzero(e > off_db)[0]
    end = int(alive[-1]) + 1
    end = min(end, st + int(max_len * sr))
    end = max(end, st + int(min_len * sr))
    y = m[st:end].copy()
    truncated = (int(alive[-1]) + 1) > st + int(max_len * sr)
    fi = min(int(0.002 * sr), y.size // 4)
    if fi > 1:
        y[:fi] *= np.linspace(0, 1, fi)
    fo = min(int((0.12 if truncated else 0.02) * sr), y.size // 3)
    if fo > 1:
        y[-fo:] *= np.linspace(1, 0, fo) ** 2
    y = y / (np.max(np.abs(y)) + 1e-12) * (10 ** (peak_target_db / 20.0))
    # count separate loud events (re-triggers) after the first
    ey = env_db(y, sr, 8.0)
    ey = ey - ey.max()
    events, armed = 0, True
    for v in ey[::int(sr * 0.005)]:
        if armed and v > -6:
            events += 1
            armed = False
        elif v < -22:
            armed = True
    info = {'ok': True, 'onset_s': round(on / sr, 3), 'dur_s': round(y.size / sr, 3), 'truncated': bool(truncated),
            'pre_noise_db': round(pre_noise, 1), 'events': int(events),
            'crest_db': round(float(20 * np.log10((np.max(np.abs(y)) + 1e-12) / (np.sqrt(np.mean(y ** 2)) + 1e-12))), 1),
            'lufs': round(lufs(y[None, :], sr), 1)}
    return y[None, :].astype(np.float32), info


def loop_sfx(x, sr, min_len=1.4, max_len=2.0, xfade_s=0.12):
    """Loopable chunk (e.g. helicopter): pick a segment from the steady middle whose end matches its start."""
    m = x.mean(axis=0)
    b, a = sig.butter(2, 25.0 / (sr / 2), 'highpass')
    m = sig.filtfilt(b, a, m)
    n = m.size
    s0 = int(n * 0.3)
    env = np.sqrt(ndi.uniform_filter1d(m ** 2, int(0.01 * sr)) + 1e-12)
    W = int(0.4 * sr)
    best = None
    for L in np.arange(int(min_len * sr), int(max_len * sr), int(0.005 * sr)):
        if s0 + L + W + int(xfade_s * sr) >= n:
            break
        c = float(np.dot(_zn(env[s0:s0 + W]), _zn(env[s0 + L:s0 + L + W])))
        if best is None or c > best[0]:
            best = (c, int(L))
    if best is None:
        return None, {'ok': False, 'why': 'too short'}
    L = best[1]
    y = cut_loop(m[None, :], sr, s0, s0 + L, xfade_s=xfade_s, edge_fade_s=0.005)
    y = y / (np.max(np.abs(y)) + 1e-12) * (10 ** (-3.0 / 20.0))
    return y.astype(np.float32), {'ok': True, 'dur_s': round(L / sr, 3), 'loop_corr': round(best[0], 3),
                                  'onset_s': 0.0, 'events': 0, 'truncated': False, 'pre_noise_db': -99.0,
                                  'crest_db': 0.0, 'lufs': round(lufs(y, sr), 1)}
