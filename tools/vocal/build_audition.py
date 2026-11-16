#!/usr/bin/env python3
"""Rebuild tools/vocal/audition.html from tools/vocal/manifest.json  (plain python 3, stdlib only).

Open it through a web server (the game's own preview server works: http://localhost:8146/tools/vocal/audition.html)
so the page can decode the mp3s for the rapid-fire / loop simulators; from file:// only the plain players work.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# shots per second the game fires each weapon (js/weapons.js rate) + the pitch spread js/audio.js applies per call (VAR)
RATE = {'pistol': (5, 0.07), 'dual': (9, 0.07), 'spread': (4, 0.05), 'shotgun': (1.7, 0.05), 'mg': (14, 0.08), 'mg2': (14, 0.08),
        'mg3': (14, 0.08), 'mg4': (14, 0.08), 'mg5': (14, 0.08), 'flame': (28, 0.05), 'laser': (3.2, 0.05),
        'rocket_launch': (1.25, 0.05), 'hit': (10, 0.1), 'gold': (6, 0.05), 'bounce': (6, 0.05)}

PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stick Doosh - vocal SFX audition</title>
<style>
:root{--bg:#14101c;--panel:#1f1830;--ink:#f4efe6;--dim:#a79cc2;--line:#3a2f55;--hot:#ffd23f;--red:#ff4d5e;--ok:#6fe39a;--blu:#59b8ff}
@media (prefers-color-scheme: light){:root{--bg:#fbf6ea;--panel:#fff;--ink:#1c1530;--dim:#5d5578;--line:#d9cfe8;--hot:#c27d00;--red:#d6243a;--ok:#12803f;--blu:#1b6fc0}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,Segoe UI,sans-serif}
.wrap{max-width:1040px;margin:0 auto;padding:16px}
h1{font:400 34px/1.1 Impact,'Arial Narrow Bold',sans-serif;letter-spacing:1px;margin:6px 0 10px;color:var(--hot)}
.readme{background:var(--panel);border:2px solid var(--line);border-radius:10px;padding:12px 16px;margin-bottom:14px}
.readme h2{margin:0 0 6px;font-size:16px}.readme li{margin:3px 0}.readme code{background:rgba(127,127,127,.2);padding:1px 5px;border-radius:4px}
.bar{position:sticky;top:0;z-index:5;background:var(--bg);padding:8px 0;display:flex;gap:8px;flex-wrap:wrap;align-items:center;border-bottom:1px solid var(--line)}
button{font:inherit;cursor:pointer;border:2px solid var(--line);background:var(--panel);color:var(--ink);border-radius:8px;padding:4px 10px}
button:hover{border-color:var(--hot)}button.on{background:var(--hot);color:#1c1530;border-color:var(--hot)}
.chip{padding:2px 9px;font-size:13px}
.card{background:var(--panel);border:2px solid var(--line);border-radius:10px;margin:14px 0;padding:10px 14px}
.card h3{margin:0;font:400 24px/1.2 Impact,sans-serif;letter-spacing:.5px}
.meta{color:var(--dim);font-size:13px;margin:2px 0 6px}
.tag{display:inline-block;font-size:11px;font-weight:700;padding:1px 7px;border-radius:99px;margin-left:6px;vertical-align:middle;color:#1c1530}
.t-def{background:var(--hot)}.t-ins{background:var(--ok)}.t-bad{background:var(--red);color:#fff}.t-ai{background:var(--blu)}
table{width:100%;border-collapse:collapse}td{padding:4px 6px;border-top:1px solid var(--line);vertical-align:middle;font-size:13px}
td.id{font-weight:700;font-size:15px;white-space:nowrap}td.m{color:var(--dim);white-space:nowrap}.warn{color:var(--red)}.soft{color:var(--hot)}
tr.isdef td{background:rgba(255,210,63,.08)}
.v{opacity:.85}
@media (max-width:700px){td.m.opt{display:none}}
</style></head><body><div class="wrap">
<h1>STICK DOOSH - VOCAL WEAPON SFX</h1>
<div class="readme"><h2>README</h2><ul>
<li>Every gun/impact sound is now a <b>human mouth</b>: LOW male "DOOSH" (shotgun), female "pew" (pistol), average male lip-trill "brr" (MG), male breath "shhhh" (rockets), raspy "fwoosh" (flame)... plus Kokoro TTS words, hand-built mouth-noise synth and Stable Audio 3 attempts, 3-8 takes each.</li>
<li><b>Nothing here was judged by ear</b> (the agent that built it cannot listen). <span class="tag t-def">DEFAULT</span> = best by objective checks only (non-silent, onset at start, length window, clean, decodes, right pitch class) with a prior toward the first take. <span class="tag t-ins">INSTALLED</span> = what is in <code>assets/sfx/&lt;name&gt;.mp3</code> right now. You decide by ear.</li>
<li><b>MG v2 (kid, not frog).</b> The first lip-trill "brr" takes (<code>brr*</code>, <code>lp*</code>, <code>kk1</code>, <code>ai*</code>) sounded like a frog (low, periodic, tonal buzz). They are kept but now FAIL new checks (dominant energy must be 800-4000 Hz, &lt;20% below 300 Hz, no pitch &lt;150 Hz, 1-3 hits per shot / 9-18 hits/s in the loop). New candidates: <code>ksyn*</code> + <code>kl*</code> (synth: dry plosive bursts with spit click and a faint child-pitch "ah"), <code>ki*</code> + <code>kt*</code> (child-like Kokoro "da/ka/ta/pa"), <code>kai*</code> + <code>lai*</code> (Stable Audio 3 "little kid machine gun"). Still not judged by ear.</li>
<li>Press <b>copy promote cmd</b> next to a take, paste it in a terminal at the repo root: <code>python tools/vocal/promote.py &lt;name&gt; &lt;take&gt;</code>. It copies that take into <code>assets/sfx</code>, rebuilds this page and <code>js/audiolist.js</code>. <code>python tools/vocal/promote.py --old &lt;name&gt;</code> restores the original pre-vocal sound.</li>
<li><b>rapid</b> simulates how the game retriggers a weapon (its fire rate, +/- the random pitch js/audio.js adds). <b>loop</b> plays loop takes seamlessly (needs http, not file://). <b>mg cycle</b> alternates mg, mg2..mg5 per shot.</li>
<li>Files: mono, 24 kHz, 96 kbps mp3, trimmed to onset, peak -1 dBFS, short-term loudness voices -16 / shotgun+explosions -13 / loops -19 LUFS. Regenerate everything: see the top of <code>tools/vocal/master.py</code>.</li></ul></div>
<div class="bar"><button id="stop">stop all</button><button id="seq">play all installed in order</button><span id="grps"></span><span class="meta" id="status"></span></div>
<div id="cards"></div>
</div>
<script>
const D=/*DATA*/null, RATE=/*RATE*/null;
const $=(s,e)=>(e||document).querySelector(s);
const SRCN={tts:'Kokoro',synth:'mouth synth',ai:'Stable Audio 3'};
let ctx=null,active=[],audios=[],cache={},canWA=location.protocol.indexOf('http')===0;
function AC(){if(!ctx)ctx=new (window.AudioContext||window.webkitAudioContext)();if(ctx.state==='suspended')ctx.resume();return ctx}
async function buf(url){if(cache[url])return cache[url];const r=await fetch(url);const ab=await r.arrayBuffer();return cache[url]=await AC().decodeAudioData(ab)}
function stopAll(){active.forEach(s=>{try{s.stop()}catch(e){}});active=[];audios.forEach(a=>{a.pause()});audios=[];document.querySelectorAll('button.on').forEach(b=>b.classList.remove('on'))}
function mkSrc(b,when,rate,vol,loop){const c=AC(),s=c.createBufferSource(),g=c.createGain();s.buffer=b;s.playbackRate.value=rate||1;s.loop=!!loop;g.gain.value=vol==null?0.8:vol;s.connect(g);g.connect(c.destination);s.start(when);active.push(s);return s}
async function playOnce(url){if(!canWA){const a=new Audio(url);audios.push(a);a.play();return new Promise(r=>{a.onended=r})}
  const b=await buf(url);const s=mkSrc(b,0,1,0.9);return new Promise(r=>{s.onended=r})}
async function loopPlay(url,btn){const was=btn.classList.contains('on');stopAll();if(was)return;if(!canWA){const a=new Audio(url);a.loop=true;audios.push(a);a.play();btn.classList.add('on');return}
  const b=await buf(url);mkSrc(b,0,1,0.8,true);btn.classList.add('on')}
async function rapid(urls,rate,vr,btn){stopAll();if(!canWA){alert('rapid needs http (serve the folder)');return}
  btn.classList.add('on');const bs=await Promise.all(urls.map(buf));const c=AC(),t0=c.currentTime+0.05,n=Math.round(rate*1.8);
  for(let i=0;i<n;i++){mkSrc(bs[i%bs.length],t0+i/rate,1+(Math.random()*2-1)*vr,0.8)}
  setTimeout(()=>btn.classList.remove('on'),1900)}
function copy(txt,btn){const done=()=>{const o=btn.textContent;btn.textContent='copied!';setTimeout(()=>btn.textContent=o,1200)};
  if(navigator.clipboard&&window.isSecureContext)navigator.clipboard.writeText(txt).then(done,()=>fb());else fb();
  function fb(){const t=document.createElement('textarea');t.value=txt;document.body.appendChild(t);t.select();try{document.execCommand('copy')}catch(e){}t.remove();done()}}
function takesOf(n){const e=D.names[n];return e.variant_of?D.names[e.variant_of].takes:e.takes}
function orderOf(n){const e=D.names[n];return e.variant_of?D.names[e.variant_of].order:e.order}
function urlOf(n,t){const e=D.names[n];return e.variant_of?(D.names[e.variant_of].takes[t].file):e.takes[t].file}
function card(n){const e=D.names[n],tk=takesOf(n),od=orderOf(n),div=document.createElement('div');div.className='card';div.dataset.grp=e.grp;div.id='n-'+n;
  const rt=RATE[n];
  div.innerHTML=`<h3>${n}${e.loop?' <span class="tag t-ai" style="background:var(--blu)">LOOP</span>':''} <span style="font-size:17px;color:var(--hot)">"${e.word}"</span></h3>
  <div class="meta">${e.grp} &middot; ${e.voice} voice &middot; ${e.lo}-${e.hi} s &middot; ${e.desc}${e.variant_of?' &middot; takes shared with <b>'+e.variant_of+'</b>':''}${rt?' &middot; game fires ~'+rt[0]+'/s':''} &middot; installed: <b>${e.installed||'-'}</b>${e.pinned?' (pinned)':''}</div><table></table>`;
  const tb=$('table',div);
  od.forEach(id=>{const t=tk[id],tr=document.createElement('tr');const isdef=id===e.default,isins=id===e.installed;if(isdef)tr.className='isdef';
    const issues=(t.fails||[]).map(f=>'<span class="warn">'+f+'</span>').concat((t.soft||[]).map(f=>'<span class="soft">'+f+'</span>')).join(' ');
    tr.innerHTML=`<td class="id">${id}${isdef?'<span class="tag t-def">DEFAULT</span>':''}${isins?'<span class="tag t-ins">INSTALLED</span>':''}${t.ok===false?'<span class="tag t-bad">FAIL</span>':''}</td>
    <td class="m">${SRCN[t.src]||t.src}${t.say?' &middot; <i>'+(t.voice||'')+': '+t.say+'</i>':''}${t.note?' &middot; '+t.note:''}</td>
    <td class="m opt">${t.dur!=null?t.dur+' s &middot; '+t.lufs+' LU &middot; '+t.peak_db+' dB &middot; f0 '+(t.f0||'-')+' &middot; '+t.centroid+' Hz':''}<br>${issues}</td><td class="act"></td>`;
    const act=$('.act',tr);
    if(t.missing){act.textContent='(missing)';tb.appendChild(tr);return}
    const url=t.file;
    const b1=document.createElement('button');b1.textContent='▶ play';b1.onclick=()=>{stopAll();playOnce(url)};act.appendChild(b1);
    if(e.loop){const bl=document.createElement('button');bl.textContent='loop';bl.onclick=()=>loopPlay(url,bl);act.appendChild(bl)}
    if(rt){const br=document.createElement('button');br.textContent='rapid x'+rt[0];br.onclick=()=>rapid([url],rt[0],rt[1],br);act.appendChild(br)}
    if(n==='mg'){const bc=document.createElement('button');bc.textContent='mg cycle';bc.onclick=()=>{const us=['mg','mg2','mg3','mg4','mg5'].map(m=>D.names[m].installed?urlOf(m,D.names[m].installed):urlOf(m,D.names[m].default));rapid(us,14,0.08,bc)};act.appendChild(bc)}
    const bp=document.createElement('button');bp.textContent='copy promote cmd';bp.onclick=()=>copy('python tools/vocal/promote.py '+n+' '+id,bp);act.appendChild(bp);
    tb.appendChild(tr)});
  return div}
const cards=$('#cards');D.order.forEach(n=>cards.appendChild(card(n)));
const grps=[...new Set(D.order.map(n=>D.names[n].grp))];const gs=$('#grps');
['all'].concat(grps).forEach(g=>{const b=document.createElement('button');b.className='chip';b.textContent=g;b.onclick=()=>{document.querySelectorAll('.card').forEach(c=>c.style.display=(g==='all'||c.dataset.grp===g)?'':'none')};gs.appendChild(b)});
$('#stop').onclick=stopAll;
$('#seq').onclick=async()=>{stopAll();const st=$('#status');for(const n of D.order){const e=D.names[n];const t=e.installed&&e.installed!=='ORIGINAL'?e.installed:e.default;st.textContent='playing '+n+' ('+t+')';await playOnce(urlOf(n,t));await new Promise(r=>setTimeout(r,300))}st.textContent='done'};
</script></body></html>
'''


def build():
    with open(os.path.join(HERE, 'manifest.json'), 'r', encoding='utf-8') as fh:
        man = json.load(fh)
    html = PAGE.replace('/*DATA*/null', json.dumps(man, separators=(',', ':'))).replace('/*RATE*/null', json.dumps(RATE))
    with open(os.path.join(HERE, 'audition.html'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(html)


if __name__ == '__main__':
    build()
    print('audition.html rebuilt')
    sys.exit(0)
