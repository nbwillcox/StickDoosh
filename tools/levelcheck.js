#!/usr/bin/env node
// STICK DOOSH - tools/levelcheck.js (owner: levels)
// Builds every theme with SGS.LevelGen and verifies the level contract (DESIGN §13).
//   node tools/levelcheck.js                 check all 12 themes (exit code 1 on failure)
//   node tools/levelcheck.js --ascii ice     print an ASCII thumbnail of one theme (also checks it)
//   node tools/levelcheck.js --only moon     check just one theme
//   node tools/levelcheck.js --seed 123      override the seed (default = the fixed per-theme seed)
//   node tools/levelcheck.js --diff ultra    difficulty (baby|normal|ultra) -> enemy density
//   node tools/levelcheck.js --seeds 25      stress: build N random seeds per theme, report the failure rate
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const root = path.join(__dirname, '..');
const args = process.argv.slice(2);
const opt = (n, d) => { const i = args.indexOf('--' + n); return i < 0 ? d : (args[i + 1] === undefined || args[i + 1].startsWith('--') ? true : args[i + 1]); };

// ---- load the game modules into a stubbed-window sandbox (no DOM)
const win = {};
const sandbox = { window: win, console, Math, Date, Uint8Array, Int16Array, Int32Array, Float32Array, Set, Map, performance: { now: () => Date.now() } };
vm.createContext(sandbox);
function load(f, required) {
  const p = path.join(root, 'js', f);
  if (!fs.existsSync(p)) { if (required) throw new Error('missing ' + f); return false; }
  try { vm.runInContext(fs.readFileSync(p, 'utf8'), sandbox, { filename: f }); return true; }
  catch (e) { if (required) throw e; console.log('  (warn) could not load ' + f + ': ' + e.message); return false; }
}
load('util.js'); load('config.js');
win.SGS = win.SGS || {};
if (!win.SGS.C) win.SGS.C = { T: 20 };           // inline fallback if core files are not there yet
load('themes.js', true); load('levelgen.js', true);
const S = win.SGS, LG = S.LevelGen, TD = S.Themes;
const T = (S.C && S.C.T) || 20;
const M = LG.MAT, SOLID = LG.SOLID, HAZ = LG.HAZ;
const IDS = LG.IDS;

// ---- checks
function check(id, seed, diff, quiet) {
  const errs = [], warns = [];
  const t0 = process.hrtime.bigint();
  const lv = LG.build(id, seed, diff);
  const ms = Number(process.hrtime.bigint() - t0) / 1e6;
  const w = lv.w, h = lv.h, t = lv.tiles;
  const cell = (x, y) => (y < 0 ? 0 : (x < 0 || x >= w || y >= h) ? M.BEDROCK : t[y * w + x]);
  const solid = (x, y) => SOLID[cell(x, y)] === 1;
  const stand = (x, y) => { const m = cell(x, y); return SOLID[m] === 1 || m === M.PLAT; };   // y = row under the feet
  const empty = (x, y) => { const m = cell(x, y); return !SOLID[m] && !HAZ[m]; };
  const tileOf = (e) => ({ x: Math.floor(e.x / T), y: Math.round(e.y / T) });

  // dims
  if (!(w >= 260 && w <= 345)) errs.push('width ' + w + ' outside 260..345');
  if (!(h >= 60 && h <= 92)) errs.push('height ' + h + ' outside 60..92');
  if (!(t instanceof Uint8Array) || t.length !== w * h) errs.push('tiles is not Uint8Array(w*h)');
  if (lv.T !== T) errs.push('level.T ' + lv.T + ' != C.T ' + T);
  // border: 2 bedrock columns each side + 2 rows bottom; top row open in the middle
  let badB = 0;
  for (let y = 0; y < h; y++) for (const x of [0, 1, w - 2, w - 1]) if (cell(x, y) !== M.BEDROCK) badB++;
  for (let x = 0; x < w; x++) for (const y of [h - 2, h - 1]) if (cell(x, y) !== M.BEDROCK) badB++;
  if (badB) errs.push('border not solid bedrock (' + badB + ' cells)');
  let topOpen = 0;
  for (let x = 2; x < w - 2; x++) if (cell(x, 0) === 0) topOpen++;
  if (topOpen < w * 0.8) errs.push('top row not open sky (' + topOpen + '/' + (w - 4) + ')');
  // spawn
  const sp = tileOf(lv.spawn);
  if (!stand(sp.x, sp.y)) errs.push('spawn not on solid ground');
  if (!empty(sp.x, sp.y - 1) || !empty(sp.x, sp.y - 2) || !empty(sp.x, sp.y - 3)) errs.push('spawn lacks headroom');
  if (sp.x > 20) errs.push('spawn not at the left (tx ' + sp.x + ')');
  // arena
  const A = lv.arena;
  if (!A) errs.push('no arena');
  else {
    const iw = A.tx1 - A.tx0 + 1, ih = A.ty1 - A.ty0 + 1;
    if (iw < 40 || iw > 48) errs.push('arena width ' + iw);
    if (ih < 18 || ih > 22) errs.push('arena height ' + ih);
    let bad = 0;
    for (let y = A.ty0; y <= A.ty1; y++) for (let x = A.tx0; x <= A.tx1; x++) if (cell(x, y) !== 0 && cell(x, y) !== M.PLAT) bad++;
    if (bad > 12) errs.push('arena interior has ' + bad + ' blocking cells');
    for (let x = A.tx0; x <= A.tx1; x++) {
      if (cell(x, A.ty1 + 1) !== M.BEDROCK) { errs.push('arena floor not bedrock'); break; }
      if (cell(x, A.ty0 - 1) !== M.BEDROCK) { errs.push('arena ceiling not bedrock'); break; }
    }
    for (let y = A.ty0; y <= A.ty1; y++) if (cell(A.tx1 + 1, y) !== M.BEDROCK) { errs.push('arena right wall not bedrock'); break; }
    for (let y = A.ty0; y < A.door.ty0; y++) if (cell(A.tx0 - 1, y) !== M.BEDROCK) { errs.push('arena left wall not bedrock above the door'); break; }
    for (let y = A.door.ty0; y <= A.door.ty1; y++) if (cell(A.tx0 - 1, y) !== 0) { errs.push('arena door is blocked'); break; }
    if (!(A.bossX > A.x0 + (A.x1 - A.x0) * 0.6 && A.bossX < A.x1)) errs.push('bossX not in the right third');
    if (Math.abs(A.bossY - A.y1) > 1) errs.push('bossY not on the floor');
    if (!(A.entryX < A.x0 + (A.x1 - A.x0) * 0.25)) errs.push('arena entrance not on the left');
  }
  // entities on ground
  const cnt = { enemy: 0, cage: 0, crate: 0, barrel: 0, goldbar: 0, pickup: 0, flag: 0, hazard: 0, ladderTop: 0 };
  const grounded = [];
  for (const e of lv.ents) {
    cnt[e.type] = (cnt[e.type] || 0) + 1;
    const p = tileOf(e);
    if (e.x < 2 * T || e.x > (w - 2) * T) errs.push(e.type + ' outside the border at ' + p.x);
    if (e.type === 'enemy') {
      if (e.water) { if (cell(p.x, p.y - 1) !== M.WATER) errs.push('water enemy ' + e.id + ' @' + p.x + ',' + p.y + ' not in water'); continue; }
      if (e.air) { if (solid(p.x, p.y - 1) || solid(p.x, p.y - 2)) errs.push('flying ' + e.id + ' inside terrain @' + p.x + ',' + p.y); continue; }
    }
    if (e.type === 'hazard' || e.type === 'ladderTop') continue;
    if (!stand(p.x, p.y)) errs.push(e.type + (e.id ? ' ' + e.id : '') + ' @' + p.x + ',' + p.y + ' not on solid ground (below=' + cell(p.x, p.y) + ')');
    else if (solid(p.x, p.y - 1) || (e.type === 'cage' || e.type === 'enemy') && solid(p.x, p.y - 2)) errs.push(e.type + ' @' + p.x + ',' + p.y + ' embedded in terrain');
    grounded.push({ e, p });
  }
  if (cnt.flag < 3) errs.push('only ' + cnt.flag + ' checkpoint flags');
  if (!lv.flags || lv.flags.length !== cnt.flag) errs.push('level.flags does not match flag ents');
  if (cnt.cage < 2 || cnt.cage > 4) errs.push(cnt.cage + ' cages (want 2-4)');
  if (cnt.crate < 8) errs.push('only ' + cnt.crate + ' crates');
  if (cnt.enemy < 30) warns.push('only ' + cnt.enemy + ' enemies');
  if (cnt.barrel < 3) warns.push('only ' + cnt.barrel + ' barrels');
  if (cnt.goldbar < 2) warns.push('only ' + cnt.goldbar + ' gold bars');
  // flags spaced out?
  for (let i = 1; i < lv.flags.length; i++) { const d = (lv.flags[i].x - lv.flags[i - 1].x) / T; if (d > 95) warns.push('flag gap ' + d.toFixed(0) + ' tiles'); }
  // enemy ids valid for theme
  const wts = TD[id].enemies;
  for (const e of lv.ents) if (e.type === 'enemy' && !(wts[e.id] > 0)) errs.push('enemy ' + e.id + ' is not in theme weights');
  // hazards: spikes/lava must never block the route => covered by reachability (analyze never enters them)
  // reachability
  const an = LG.analyze(lv), st = LG.analyze(lv, { strict: true });
  if (!an.door) errs.push('arena door NOT reachable from spawn');
  if (!an.goal) errs.push('arena floor NOT reachable from spawn');
  if (!st.ok) warns.push('arena not reachable under the STRICT movement model (tighter jumps)');
  for (const g of grounded) {
    const k = g.e.type;
    if (k !== 'flag' && k !== 'cage' && k !== 'crate' && k !== 'goldbar' && k !== 'enemy' && k !== 'pickup') continue;
    const fy = g.p.y - 1;
    if (fy < 0 || an.reach[fy * w + g.p.x] !== 1) {
      const nearby = an.reach[fy * w + g.p.x - 1] === 1 || an.reach[fy * w + g.p.x + 1] === 1 || an.reach[(fy - 1) * w + g.p.x] === 1;
      if (k === 'flag' || k === 'cage') errs.push(k + ' @' + g.p.x + ',' + g.p.y + ' unreachable');
      else if (!nearby && !g.e.hidden) warns.push(k + (g.e.id ? ' ' + g.e.id : '') + ' @' + g.p.x + ',' + g.p.y + ' unreachable');
    }
  }
  // vertical variety: surface range over the playable part
  let lo = 1e9, hi = -1e9;
  for (let x = 12; x < A.tx0 - 6; x++) { lo = Math.min(lo, lv.surface[x]); hi = Math.max(hi, lv.surface[x]); }
  const vert = hi - lo;
  if (vert < 14) errs.push('not enough vertical variety (surface range ' + vert + ' tiles)');
  // multi-level: count columns that have >=2 distinct walkable levels (floors above caves, towers...)
  let multi = 0;
  for (let x = 12; x < A.tx0 - 6; x += 2) {
    let levels = 0, prev = false;
    for (let y = 1; y < h - 3; y++) {
      const f = stand(x, y) && empty(x, y - 1) && empty(x, y - 2);
      if (f && !prev) levels++;
      prev = stand(x, y);
    }
    if (levels >= 2) multi++;
  }
  const multiPct = multi / ((A.tx0 - 18) / 2);
  if (multiPct < 0.18) warns.push('few stacked routes (' + (multiPct * 100).toFixed(0) + '% of columns)');
  if (themeRule(id, lv, errs, warns, cell, T)) { /* handled */ }
  if (ms > 30) warns.push('build took ' + ms.toFixed(1) + ' ms (>30)');
  return { id, lv, errs, warns, ms, cnt, vert, multiPct, reachCells: an.count, strictOK: st.ok };
}

// per-theme feature sanity (hazard identity of each theme)
function themeRule(id, lv, errs, warns, cell, T) {
  const count = (m) => { let n = 0; for (let i = 0; i < lv.tiles.length; i++) if (lv.tiles[i] === m) n++; return n; };
  const haz = (hid) => lv.ents.filter((e) => e.type === 'hazard' && e.id === hid).length;
  const need = (c, msg) => { if (!c) warns.push('theme feature missing: ' + msg); };
  switch (id) {
    case 'ice': need(count(M.ICE) > 60, 'ICE tiles'); need(haz('icicle') > 0, 'icicles'); break;
    case 'fire': need(count(M.LAVA) > 20, 'LAVA'); need(haz('firejet') > 0, 'fire jets'); break;
    case 'wind': need(haz('updraft') > 0, 'updrafts'); need(count(M.PLAT) > 20, 'floating platforms'); break;
    case 'water': need(count(M.WATER) > 200, 'WATER'); need(!!lv.water, 'tide band'); break;
    case 'mud': need(count(M.MUD) > 30, 'MUD'); need(haz('quicksand') > 0, 'quicksand'); break;
    case 'jungle': need(count(M.LADDER) > 20, 'vines/ladders'); need(count(M.SPIKES) > 5, 'spike pits'); break;
    case 'mountain': need(haz('rockslide') > 0, 'rockslides'); break;
    case 'plains': need(haz('stampede') > 0 || haz('ufo') > 0, 'stampede'); break;
    case 'fantasy': need(count(M.WATER) > 10 || count(M.WOOD) > 30, 'moat/drawbridge'); break;
    case 'moon': need(count(M.GLASS) > 5, 'glass domes'); break;
    case 'retro': need(count(M.SPIKES) > 3, 'spikes'); break;
    case 'fortress': need(count(M.STEEL) > 200, 'steel'); break;
  }
  return true;
}

// ---- ascii thumbnail
function ascii(res) {
  const lv = res.lv, w = lv.w, h = lv.h;
  const fx = 3, fy = 4;
  const rows = [];
  const pri = { ' ': 0, '.': 1, '#': 2, '=': 3, 'H': 4, '~': 5, 'x': 6, '%': 7, 'o': 8, 'e': 9, 'C': 10, 'F': 11, 'S': 12, 'B': 13, '$': 8, '^': 6, 'M': 4 };
  const marks = new Map();
  const mark = (e, ch) => { const k = Math.floor(Math.floor(e.y / T - 1) / fy) * 10000 + Math.floor(Math.floor(e.x / T) / fx); const cur = marks.get(k); if (!cur || pri[ch] > pri[cur]) marks.set(k, ch); };
  for (const e of lv.ents) {
    if (e.type === 'flag') mark(e, 'F'); else if (e.type === 'cage') mark(e, 'C'); else if (e.type === 'enemy') mark(e, 'e');
    else if (e.type === 'goldbar') mark(e, '$'); else if (e.type === 'crate' || e.type === 'barrel') mark(e, 'o');
  }
  mark({ x: lv.spawn.x, y: lv.spawn.y }, 'S');
  for (let by = 0; by < Math.ceil(h / fy); by++) {
    let line = '';
    for (let bx = 0; bx < Math.ceil(w / fx); bx++) {
      let best = ' ';
      for (let y = by * fy; y < Math.min(h, by * fy + fy); y++) for (let x = bx * fx; x < Math.min(w, bx * fx + fx); x++) {
        const m = lv.tiles[y * w + x];
        let ch = ' ';
        if (m === M.LAVA) ch = '%'; else if (m === M.SPIKES) ch = 'x'; else if (m === M.WATER) ch = '~';
        else if (m === M.LADDER) ch = 'H'; else if (m === M.PLAT) ch = '='; else if (m === M.MUD) ch = 'M';
        else if (SOLID[m]) ch = '#'; else if (lv.back && lv.back[y * w + x]) ch = '.';
        if (pri[ch] > pri[best]) best = ch;
      }
      const mk = marks.get(by * 10000 + bx);
      if (mk && pri[mk] > pri[best] - 0) best = mk;
      line += best;
    }
    rows.push(line);
  }
  const A = lv.arena;
  const bx0 = Math.floor(A.tx0 / fx), bx1 = Math.floor(A.tx1 / fx), by0 = Math.floor(A.ty0 / fy), by1 = Math.floor(A.ty1 / fy);
  for (let by = by0; by <= by1; by++) { const a = rows[by].split(''); for (let bx = bx0; bx <= bx1; bx++) if (a[bx] === ' ' || a[bx] === '.') a[bx] = ':'; rows[by] = a.join(''); }
  console.log('\n' + lv.id + ' ' + w + 'x' + h + ' (1 char = ' + fx + 'x' + fy + ' tiles)   S spawn  F flag  C cage  e enemy  o crate/barrel  $ gold  H ladder  = plat  ~ water  % lava  x spikes  M mud  : boss arena');
  console.log(rows.join('\n'));
}

// ---- main
const asciiId = opt('ascii', null);
const only = opt('only', null);
const seedArg = opt('seed', null);
const diff = opt('diff', 'normal');
const stress = +opt('seeds', 0);
const ids = asciiId && asciiId !== true ? [asciiId] : only && only !== true ? [only] : IDS;
let fails = 0;
LG.build('plains'); LG.build('moon');   // JIT warm-up (first-ever build in a process is ~2-3x slower)

if (stress) {
  console.log('stress: ' + stress + ' random seeds x ' + ids.length + ' themes');
  for (const id of ids) {
    let bad = 0, slow = 0, firstBad = null;
    for (let i = 0; i < stress; i++) {
      const seed = (i * 2654435761 + 12345) >>> 0;
      const r = check(id, seed, diff);
      if (r.errs.length) { bad++; if (!firstBad) firstBad = seed + ': ' + r.errs[0]; }
      if (r.ms > 30) slow++;
    }
    console.log((bad ? 'FAIL ' : 'ok   ') + id.padEnd(9) + ' bad ' + bad + '/' + stress + ' slow ' + slow + (firstBad ? '   e.g. seed ' + firstBad : ''));
    if (bad) fails++;
  }
  process.exit(fails ? 1 : 0);
}

console.log('levelcheck: ' + ids.length + ' theme(s), diff=' + diff + (seedArg ? ', seed=' + seedArg : ', default seeds'));
let totalMs = 0;
for (const id of ids) {
  if (!LG.PROF[id]) { console.log('FAIL ' + id + ': unknown theme'); fails++; continue; }
  const r = check(id, seedArg && seedArg !== true ? +seedArg : undefined, diff);
  totalMs += r.ms;
  const c = r.cnt;
  const line = (r.errs.length ? 'FAIL ' : 'ok   ') + id.padEnd(9) + ' ' + r.lv.w + 'x' + r.lv.h + '  ' + r.ms.toFixed(1).padStart(5) + 'ms' +
    '  en ' + String(c.enemy).padStart(2) + ' cage ' + c.cage + ' crate ' + String(c.crate).padStart(2) + ' barrel ' + String(c.barrel).padStart(2) +
    ' gold ' + c.goldbar + ' flag ' + c.flag + ' haz ' + String(c.hazard).padStart(2) + '  vert ' + r.vert + '  stacked ' + (r.multiPct * 100).toFixed(0) + '%' +
    '  strict:' + (r.strictOK ? 'ok' : 'NO');
  console.log(line);
  for (const e of r.errs.slice(0, 12)) console.log('       ERROR ' + e);
  if (r.errs.length > 12) console.log('       ... +' + (r.errs.length - 12) + ' more errors');
  for (const wmsg of r.warns.slice(0, 8)) console.log('       warn  ' + wmsg);
  if (r.errs.length) fails++;
  if (asciiId) ascii(r);
}
console.log(fails ? '\n' + fails + ' theme(s) FAILED' : '\nall ' + ids.length + ' themes passed  (total build ' + totalMs.toFixed(0) + ' ms)');
process.exit(fails ? 1 : 0);
