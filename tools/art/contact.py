"""Build tools/art/contact.html: every default + every candidate, with the objective scores, the in-game crops
(panel 3:2, VS square, shop circle) and a click-to-copy promote command, so the user picks by EYE.

  python tools/art/contact.py        # then open tools/art/contact.html (served or file://)
"""
import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import artlib as A  # noqa: E402
from art_defs import ITEMS  # noqa: E402

CSS = """
:root{--ink:#141018;--bg:#1b1626;--card:#2a2238;--yel:#ffd60a;--red:#ff2e3e;--ok:#3bd16f}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:#fff;font:14px/1.35 system-ui,Segoe UI,sans-serif;padding:18px}
h1{font-family:Impact,'Arial Black',sans-serif;letter-spacing:.04em;color:var(--yel);text-shadow:3px 3px 0 var(--ink);margin:0 0 4px;font-size:34px}
.sub{opacity:.75;margin-bottom:16px}
.item{background:var(--card);border:3px solid var(--ink);box-shadow:5px 5px 0 var(--ink);margin:0 0 22px;padding:12px;border-radius:6px}
.item h2{margin:0 0 8px;font-size:18px;font-family:Impact,'Arial Black',sans-serif;letter-spacing:.05em}
.item h2 small{font:12px system-ui;opacity:.7;margin-left:8px;letter-spacing:0}
.row{display:flex;flex-wrap:wrap;gap:14px;align-items:flex-start}
.take{background:#120e1a;border:3px solid #3a2f4d;border-radius:6px;padding:8px;width:min(100%,var(--w,420px))}
.take.def{border-color:var(--yel)}
.take img.main{display:block;width:100%;height:auto;border:2px solid var(--ink);background:#000;image-rendering:auto}
.tag{display:inline-block;font:700 11px system-ui;padding:2px 7px;border-radius:99px;background:#444;margin-right:6px}
.tag.def{background:var(--yel);color:var(--ink)}.tag.bad{background:var(--red)}.tag.good{background:var(--ok);color:var(--ink)}
.meta{font:11px ui-monospace,Consolas,monospace;opacity:.85;margin:6px 0}
.crops{display:flex;gap:8px;align-items:flex-end;margin:6px 0}
.crop{border:2px solid var(--ink);background:#000 center 25%/cover no-repeat;flex:none}
.cmd{display:block;width:100%;text-align:left;font:12px ui-monospace,Consolas,monospace;background:#000;color:#9ff;border:1px dashed #556;padding:5px 7px;cursor:pointer;border-radius:4px}
.cmd:active{background:#133}
.toast{position:fixed;right:14px;bottom:14px;background:var(--yel);color:var(--ink);padding:8px 14px;border:3px solid var(--ink);font-weight:700;opacity:0;transition:opacity .2s}
.toast.on{opacity:1}
"""

JS = """
function cp(t){navigator.clipboard&&navigator.clipboard.writeText(t).catch(function(){});var e=document.getElementById('t');e.textContent='Copied: '+t;e.classList.add('on');setTimeout(function(){e.classList.remove('on')},1800)}
"""


def crops(kind, url):
    if kind == 'boss':      # level-select panel (3:2, cover @25%), VS square, portrait phone panel
        return ('<div class="crops"><div class="crop" style="width:150px;height:100px;background-image:url(%s)" title="select panel ~3:2"></div>'
                '<div class="crop" style="width:100px;height:100px;background-image:url(%s)" title="VS square"></div>'
                '<div class="crop" style="width:64px;height:100px;background-image:url(%s)" title="portrait phone panel"></div></div>') % (url, url, url)
    if kind == 'shop':      # 56px circle in the header, plus a bigger circle
        return ('<div class="crops"><div class="crop" style="width:56px;height:56px;border-radius:50%%;background-position:center;background-image:url(%s)"></div>'
                '<div class="crop" style="width:112px;height:112px;border-radius:50%%;background-position:center;background-image:url(%s)"></div></div>') % (url, url)
    return ''


def main():
    scores = A.load_json(A.SCORES, {})
    chosen = A.load_json(A.CHOSEN, {})
    out = ['<!doctype html><meta charset="utf-8"><title>Stick Doosh art contact sheet</title><style>%s</style>' % CSS,
           '<h1>STICK DOOSH ART</h1><div class="sub">Yellow border = the shipped default (assets/art/). Scores are objective checks '
           '(ink lines, detail, saturation, colour variety, calm top for the title) - pick by eye, then click a command to copy it and run it from the repo root. '
           'Then re-run <code>python tools/art/contact.py</code>.</div>']
    for name, it in ITEMS.items():
        cur = chosen.get(name, {})
        dtake = cur.get('take')
        cells = []
        shipped = os.path.join(A.ART, name + '.webp')
        w = '560px' if it['kind'] == 'title' else ('300px' if it['kind'] == 'shop' else '420px')
        for t in it['takes']:
            if not os.path.exists(A.raw_png(name, t)):
                continue
            m = scores.get('%s_%s' % (name, t), {})
            isdef = (t == dtake)
            url = '../../assets/raw_art/%s_%s.webp' % (name, t)
            tags = '<span class="tag%s">%s</span>' % (' def' if isdef else '', 'DEFAULT' if isdef else 'take ' + t)
            if isdef and not cur.get('auto', True):
                tags += '<span class="tag good">manual</span>'
            if m and not m.get('ok', True):
                tags += '<span class="tag bad">failed checks</span>'
            meta = ('score %s | %s KB | ink %.2f edge %.2f sat %.2f colors %d' % (
                m.get('score', '?'), round(m.get('bytes', 0) / 1024), m.get('ink', 0), m.get('edge', 0), m.get('sat', 0), m.get('ncolors', 0))) if m else ''
            cmd = 'python tools/art/promote.py %s %s' % (name, t)
            cells.append('<div class="take%s" style="--w:%s">%s<img class="main" loading="lazy" src="%s" alt="%s %s">'
                         '<div class="meta">%s</div>%s<button class="cmd" onclick="cp(this.textContent)">%s</button></div>' % (
                             ' def' if isdef else '', w, tags, url, name, t, html.escape(meta), crops(it['kind'], url), html.escape(cmd)))
        if os.path.exists(shipped):
            kb = round(os.path.getsize(shipped) / 1024)
            cells.insert(0, '<div class="take def" style="--w:%s"><span class="tag def">SHIPPED</span><span class="tag">assets/art/%s.webp</span>'
                         '<img class="main" src="../../assets/art/%s.webp?%d" alt="shipped %s"><div class="meta">%d KB, %dx%d</div></div>' % (
                             w, name, name, int(os.path.getmtime(shipped)), name, kb, it['out'][0], it['out'][1]))
        out.append('<section class="item"><h2>%s<small>%s %dx%d - %s</small></h2><div class="row">%s</div></section>' % (
            name, it['kind'], it['out'][0], it['out'][1], 'default: take ' + str(dtake), ''.join(cells)))
    out.append('<div class="toast" id="t"></div><script>%s</script>' % JS)
    p = os.path.join(A.HERE, 'contact.html')
    with open(p, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))
    print('wrote', p)


if __name__ == '__main__':
    main()
