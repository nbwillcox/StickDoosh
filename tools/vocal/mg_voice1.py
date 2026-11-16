"""Stage 1 (Kokoro venv): say 'brrrrr' many ways -> assets/raw_audio/vocal/mgv/*.wav + metrics.json.
  tools/.venv/Scripts/python tools/vocal/mg_voice1.py
"""
import json, os, sys
import numpy as np
import soundfile as sf
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'assets', 'raw_audio', 'vocal', 'mgv'); os.makedirs(OUT, exist_ok=True)
from kokoro_onnx import Kokoro
k = Kokoro(os.path.join(ROOT, 'tools', 'models', 'kokoro-v1.0.onnx'), os.path.join(ROOT, 'tools', 'models', 'voices-v1.0.bin'))

# (tag, lang, voice, text, is_phonemes)
J = []
for v in ['am_adam', 'am_michael', 'am_puck', 'am_onyx', 'af_bella']:
    J += [('en_ph1_' + v, 'en-us', v, 'bɹɹɹɹɹɹɹɹɹɹɹɹɹɹ', True),
          ('en_ph2_' + v, 'en-us', v, 'brrrrrrrrrrrrrrrr', True),
          ('en_ph3_' + v, 'en-us', v, 'bʙʙʙʙʙʙʙʙʙʙʙʙʙ', True)]
for v in ['em_alex', 'em_santa', 'ef_dora']:
    J += [('es_rr_' + v, 'es', v, 'rrrrrrrrrrrrrrrrrrrr', False), ('es_brr_' + v, 'es', v, 'brrrrrrrrrrrrrrrrrr', False),
          ('es_perro_' + v, 'es', v, 'prrrrrrrrrrrrrrr', False)]
for v in ['im_nicola', 'if_sara']:
    J += [('it_rr_' + v, 'it', v, 'rrrrrrrrrrrrrrrrrrrr', False), ('it_brr_' + v, 'it', v, 'brrrrrrrrrrrrrrrrrr', False)]
for v in ['am_puck', 'am_adam']:
    J += [('en_txt_' + v, 'en-us', v, 'brrrrrrrrrrrrrrrr', False), ('en_drr_' + v, 'en-us', v, 'drrrrrrrrrrrrrrr', False)]


def trill_score(x, sr):
    e = np.abs(x); n = int(sr * 0.004); e = np.convolve(e, np.ones(n) / n, 'same')
    e = e[: int(sr * 1.5)]; e = e - e.mean()
    if e.std() < 1e-6 or len(e) < sr * 0.3:
        return 0.0, 0.0
    ac = np.correlate(e, e, 'full')[len(e) - 1:]; ac /= ac[0] + 1e-12
    lo, hi = int(sr / 45), int(sr / 18)
    i = lo + int(np.argmax(ac[lo:hi])); return float(ac[i]), float(sr / i)


res = {}
for tag, lang, voice, text, ph in J:
    try:
        x, sr = k.create(text, voice=voice, speed=1.0, lang=lang, is_phonemes=ph)
    except Exception as ex:
        res[tag] = {'err': str(ex)[:80]}; continue
    x = np.asarray(x, dtype=np.float32)
    s, hz = trill_score(x, sr)
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    fr = np.fft.rfftfreq(len(x), 1 / sr)
    cen = float((spec * fr).sum() / (spec.sum() + 1e-9))
    sf.write(os.path.join(OUT, tag + '.wav'), x, sr)
    res[tag] = {'dur': round(len(x) / sr, 2), 'trill': round(s, 3), 'hz': round(hz, 1), 'centroid': round(cen)}
json.dump(res, open(os.path.join(OUT, 'metrics.json'), 'w'), indent=1)
top = sorted([(v.get('trill', 0), t, v) for t, v in res.items() if 'trill' in v], reverse=True)[:12]
for s, t, v in top: print(t, v)
print('errors:', [t for t, v in res.items() if 'err' in v][:8])
