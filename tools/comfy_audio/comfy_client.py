"""Tiny ComfyUI HTTP client for Stick Doosh audio generation (local models only).

Uses Stable Audio 3 Medium (checkpoint stable_audio_3_medium.safetensors + t5gemma text encoder),
following the official ComfyUI template `audio_stable_audio_3_medium` (8 steps, lcm, cfg 1, simple).
"""
import json
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request

BASE = 'http://127.0.0.1:8188'
CLIENT = 'stickdoosh-audio-' + uuid.uuid4().hex[:8]


def _req(path, data=None, timeout=60):
    if data is not None:
        body = json.dumps(data).encode('utf-8')
        r = urllib.request.Request(BASE + path, data=body, headers={'Content-Type': 'application/json'})
    else:
        r = urllib.request.Request(BASE + path)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as f:
            return f.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError('HTTP %s on %s: %s' % (e.code, path, e.read().decode('utf-8', 'replace')[:3000]))


def sa3_graph(prompt, seconds, seed, batch=1, prefix='stickdoosh/audio', negative='',
              cfg=1.0, steps=8, sampler='lcm', scheduler='simple'):
    """API-format graph: SA3 Medium text-to-audio, saved as FLAC (lossless) for local post-processing."""
    return {
        '1': {'class_type': 'CheckpointLoaderSimple', 'inputs': {'ckpt_name': 'stable_audio_3_medium.safetensors'}},
        '2': {'class_type': 'CLIPLoader', 'inputs': {'clip_name': 't5gemma_b_b_ul2.safetensors', 'type': 'stable_audio'}},
        '3': {'class_type': 'CLIPTextEncode', 'inputs': {'text': prompt, 'clip': ['2', 0]}},
        '4': {'class_type': 'CLIPTextEncode', 'inputs': {'text': negative, 'clip': ['2', 0]}},
        '5': {'class_type': 'EmptyLatentAudio', 'inputs': {'seconds': float(seconds), 'batch_size': int(batch)}},
        '6': {'class_type': 'KSampler', 'inputs': {
            'model': ['1', 0], 'seed': int(seed), 'steps': int(steps), 'cfg': float(cfg),
            'sampler_name': sampler, 'scheduler': scheduler,
            'positive': ['3', 0], 'negative': ['4', 0], 'latent_image': ['5', 0], 'denoise': 1.0}},
        '7': {'class_type': 'VAEDecodeAudio', 'inputs': {'samples': ['6', 0], 'vae': ['1', 2]}},
        '8': {'class_type': 'SaveAudio', 'inputs': {'audio': ['7', 0], 'filename_prefix': prefix}},
    }


def run(graph, timeout=2400, poll=2.0):
    """Submit one prompt and block until it finishes. Returns (history_entry, seconds)."""
    r = json.loads(_req('/prompt', {'prompt': graph, 'client_id': CLIENT}))
    if r.get('node_errors'):
        raise RuntimeError('node errors: ' + json.dumps(r['node_errors'])[:3000])
    pid = r['prompt_id']
    t0 = time.time()
    while True:
        h = json.loads(_req('/history/' + pid))
        if pid in h:
            ent = h[pid]
            st = ent.get('status', {}) or {}
            if st.get('status_str') == 'error':
                raise RuntimeError('comfy error: ' + json.dumps(st.get('messages', []))[:3000])
            if st.get('completed') or ent.get('outputs'):
                return ent, time.time() - t0
        if time.time() - t0 > timeout:
            raise TimeoutError('prompt %s timed out' % pid)
        time.sleep(poll)


def fetch_audio(hist):
    """Download every audio output of a finished prompt, sorted by filename (= batch order)."""
    items = []
    for _nid, out in (hist.get('outputs') or {}).items():
        for a in out.get('audio', []) or []:
            items.append(a)
    items.sort(key=lambda a: a['filename'])
    res = []
    for a in items:
        q = urllib.parse.urlencode({'filename': a['filename'], 'subfolder': a.get('subfolder', ''),
                                    'type': a.get('type', 'output')})
        res.append((a['filename'], _req('/view?' + q, timeout=600)))
    return res


def generate(prompt, seconds, seed, batch=1, prefix='stickdoosh/audio', **kw):
    """Run SA3 and return (list of (filename, flac_bytes), elapsed_seconds)."""
    hist, dt = run(sa3_graph(prompt, seconds, seed, batch=batch, prefix=prefix, **kw))
    return fetch_audio(hist), dt
