"""Write tools/audition.html from music_manifest.json + sfx_manifest.json.

  python build_audition.py
"""
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import defs  # noqa: E402

PY = r'C:\Users\nicho\Documents\ComfyUI\.venv\Scripts\python.exe'
OUT = os.path.join(defs.ROOT, 'tools', 'audition.html')


def load(p):
    try:
        with open(os.path.join(defs.HERE, p), encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def esc(s):
    return html.escape(str(s if s is not None else ''))


def rel(p):  # manifest paths are project-relative; the page lives in tools/
    return '../' + p


CSS = """
:root{--bg:#f6f3ec;--card:#fff;--ink:#141018;--mut:#6b6470;--acc:#e0352b;--ok:#1f8a4c;--line:#e2dccf}
@media (prefers-color-scheme:dark){:root{--bg:#141218;--card:#1f1c24;--ink:#f1edf5;--mut:#a39cab;--acc:#ff5a4e;--ok:#4cc27f;--line:#34303b}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,Segoe UI,sans-serif}
main{max-width:1100px;margin:0 auto;padding:20px 16px 60px}h1{font:900 34px Impact,system-ui;letter-spacing:.5px;margin:0 0 4px}
h2{font:800 24px Impact,system-ui;margin:34px 0 10px;border-bottom:3px solid var(--ink);padding-bottom:4px}
.readme{background:var(--card);border:2px solid var(--ink);border-radius:10px;padding:12px 16px}
.readme code,.cmd{font:13px Consolas,monospace;background:rgba(127,127,127,.15);padding:1px 5px;border-radius:4px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin:12px 0}
.card h3{margin:0 0 2px;font-size:19px}.prompt{color:var(--mut);font-size:13px;margin:0 0 8px}
.row{display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px;padding:6px 0;border-top:1px dashed var(--line)}
.row audio{height:34px;width:300px;max-width:100%}.tag{font:700 12px system-ui;padding:2px 8px;border-radius:99px;border:1px solid var(--line)}
.def{background:var(--acc);color:#fff;border-color:var(--acc)}.meta{color:var(--mut);font-size:12.5px}
.prob{color:var(--acc);font-weight:700;font-size:12.5px}button{font:600 12px system-ui;border:1px solid var(--line);
background:transparent;color:var(--ink);border-radius:6px;padding:3px 8px;cursor:pointer}button:hover{border-color:var(--ink)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:10px}.grid .card{margin:0}
.cur{font-size:13px}.cur audio{height:30px;width:260px;max-width:100%;vertical-align:middle}
"""

JS = """
document.addEventListener('click',e=>{const b=e.target.closest('button[data-cmd]');if(!b)return;
const t=b.getAttribute('data-cmd');(navigator.clipboard?navigator.clipboard.writeText(t):Promise.reject()).then(
()=>{b.textContent='copied!';setTimeout(()=>b.textContent='copy promote cmd',1200)},()=>prompt('Run this:',t));});
document.addEventListener('play',e=>{document.querySelectorAll('audio').forEach(a=>{if(a!==e.target)a.pause()})},true);
"""


def main():
    mm = load('music_manifest.json')
    sm = load('sfx_manifest.json')
    o = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width,initial-scale=1">',
         '<title>Doosh Audio Audition</title><style>' + CSS + '</style></head><body><main>',
         '<h1>STICK DOOSH &mdash; audio audition</h1>',
         '<div class="readme"><b>How this works.</b> Every music track and SFX below has several AI candidates '
         '(Stable Audio 3 Medium via local ComfyUI). The one marked <span class="tag def">DEFAULT</span> is what '
         'the game currently ships in <code>assets/music/</code> / <code>assets/sfx/</code>. Candidates were picked by '
         '<i>objective checks only</i> (no silence, loudness, guitar-band energy, onset at start) &mdash; nobody has '
         'listened to them yet.<br><br><b>To swap one in:</b> click <i>copy promote cmd</i> next to the candidate you '
         'like and run it from the project folder, e.g.<br><code>"' + esc(PY) + '" tools/comfy_audio/promote.py '
         'title B</code><br>It re-masters that candidate from its raw WAV (music: loop cut, -14 LUFS, 112 kbps stereo; '
         'SFX: trim, -1 dBFS peak, 96 kbps mono), overwrites the game file, records the pick in '
         '<code>tools/comfy_audio/choices.json</code> (so re-runs keep it) and rebuilds this page. Reload to see it. '
         'Raw WAVs + previews live in <code>assets/raw_audio/</code> (git-ignored, local only). Open this page via '
         'the dev server (<code>http://localhost:8146/tools/audition.html</code>) or straight from disk.</div>']
    o.append('<h2>Music (%d tracks)</h2>' % len(mm))
    for tid in defs.MUSIC_IDS:
        if tid not in mm:
            continue
        e = mm[tid]
        any_c = next(iter(e['cands'].values()))
        o.append('<div class="card" id="m-%s"><h3>%s</h3>' % (esc(tid), esc(tid)))
        o.append('<p class="prompt">%s</p>' % esc(e['cands'].get('A', any_c).get('prompt')))
        o.append('<div class="cur">In game now (<code>%s</code>, %.0f KB): <audio controls preload="none" src="%s">'
                 '</audio></div>' % (esc(e['file']), e['bytes'] / 1e3, rel(e['file'])))
        order = sorted(e['cands'], key=lambda c: (not c in ('A', 'B'), c))
        for c in order:
            ce = e['cands'][c]
            r, m = ce['raw'], ce['master']
            tag = '<span class="tag def">DEFAULT</span>' if c == e['default'] else ''
            pl = ' &middot; %s' % esc(ce.get('pipeline')) if ce.get('pipeline') else ''
            o.append('<div class="row"><span class="tag">%s</span>%s<audio controls preload="none" src="%s"></audio>'
                     '<span class="meta">%.0f s loop (%.1f&ndash;%.1f s of raw), seam %.2f, raw %.1f LUFS, '
                     'guitar band %.0f%%, 1-5k %.0f%%, seed %s%s</span>' % (
                         esc(c), tag, rel(ce['preview']), m['dur_s'], m['loop_start_s'], m['loop_end_s'],
                         m['loop_score'], r['lufs'], 100 * r['guitar_100_5k'], 100 * r['crunch_1k_5k'],
                         esc(ce.get('seed')), pl))
            if ce['problems']:
                o.append('<span class="prob">flagged: %s</span>' % esc(', '.join(ce['problems'])))
            o.append('<button data-cmd="&quot;%s&quot; tools/comfy_audio/promote.py %s %s">copy promote cmd</button>'
                     '</div>' % (esc(PY), esc(tid), esc(c)))
        o.append('</div>')
    o.append('<h2>Sound effects (%d)</h2><div class="grid">' % len(sm))
    for nm in defs.SFX_IDS:
        if nm not in sm:
            continue
        e = sm[nm]
        o.append('<div class="card" id="s-%s"><h3>%s</h3><p class="prompt">%s</p>' % (esc(nm), esc(nm), esc(e['prompt'])))
        for t in sorted(e['takes'], key=lambda s: int(s) if s.isdigit() else 99):
            ti = e['takes'][t]
            if not ti.get('preview'):
                o.append('<div class="row"><span class="tag">%s</span><span class="prob">unusable (%s)</span></div>' % (
                    esc(t), esc(ti.get('why', 'silent'))))
                continue
            tag = '<span class="tag def">DEFAULT</span>' if t == e['default'] else ''
            extra = (' loop corr %.2f' % ti['loop_corr']) if 'loop_corr' in ti else (
                ', onset %.2fs, %s event(s)%s' % (ti['onset_s'], ti['events'], ', cut' if ti['truncated'] else ''))
            o.append('<div class="row"><span class="tag">%s</span>%s<audio controls preload="none" src="%s"></audio>'
                     '<span class="meta">%.2f s, score %+.2f%s</span><button data-cmd="&quot;%s&quot; '
                     'tools/comfy_audio/promote.py %s %s">copy promote cmd</button></div>' % (
                         esc(t), tag, rel(ti['preview']), ti['dur_s'], ti['score'], extra, esc(PY), esc(nm), esc(t)))
        o.append('</div>')
    o.append('</div><script>' + JS + '</script></main></body></html>')
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(o))
    print('wrote', OUT)


if __name__ == '__main__':
    main()
