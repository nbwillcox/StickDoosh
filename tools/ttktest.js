#!/usr/bin/env node
// STICK DOOSH - tools/ttktest.js (owner: enemies)  ---  "is every enemy easy to kill?" time-to-kill matrix + level sweep.
//
//   node tools/ttktest.js                       flat-floor matrix (every enemy x pistol + the 5 dudes' guns, aimed + horizontal) + elevated tests
//   node tools/ttktest.js --only grunt,shield   some enemies
//   node tools/ttktest.js --trials 8            trials per cell (default 6)
//   node tools/ttktest.js --sweep               ALSO sweep the 12 real levels: bot teleported in front of every enemy spawn must hit + kill it
//   node tools/ttktest.js --sweeponly [--themes ice,fire]
//   node tools/ttktest.js --json                machine readable
// Browser: open tools/ttktest.html (same code, real game scripts, results in the page).
//
// The bot is a "fair player": a god-mode dude standing on a flat test floor, firing at the real gun cadence (Weapons.rateOf), starting
// 0.25 s after the enemy exists, aiming with a +-3 degree error. Two aim modes: AIMED (omnidirectional aim at the body centre) and FLAT
// (horizontal only: what the old fwd/up/down aim could do). The enemy runs its REAL AI the whole time (it walks, shoots, takes cover, etc).
// PASS targets: regular enemies die in <= 1.2 s median with every default gun (shield <= 2.0 s, brute <= 2.5 s), nothing needs more than
// 4 pistol shots (brute excepted), and no enemy is unkillable from any reachable position (level sweep).
(function () {
  'use strict';
  const IN_NODE = typeof window === 'undefined';
  const argv = IN_NODE ? process.argv.slice(2) : [];
  const opt = (n, d) => { const i = argv.indexOf('--' + n); if (i < 0) return d; const v = argv[i + 1]; return (v === undefined || v.startsWith('--')) ? true : v; };
  const DT = 1 / 60;
  const THEMES = ['ice', 'fire', 'wind', 'water', 'mud', 'jungle', 'mountain', 'plains', 'fantasy', 'moon', 'retro', 'fortress'];
  const GUNS = [['pistol', 'pistol'], ['sgt', 'shotgun'], ['pete', 'dual'], ['brenda', 'mg'], ['major', 'rocket'], ['gramps', 'flame']];
  const REACH = { flame: 85, shotgun: 150 };
  // HP before the killability pass (for the report)
  const HP_BEFORE = { grunt: 2, shotgunner: 3, gunner: 3, rocketeer: 3, grenadier: 2, shield: 3, dog: 1, jetpack: 2, brute: 8, turret: 4, sniper: 2, officer: 3, roller: 2, snowman: 2, penguin: 2, imp: 2, magma: 3,
    kite: 2, fanturret: 3, scuba: 2, piranha: 1, mudman: 3, gator: 3, monkey: 2, snake: 2, goat: 3, rockthrower: 3, cow: 3, crow: 1, skeleton: 2, apprentice: 2, alien: 2, bouncer: 3, bitgoon: 2, pixelghost: 2 };
  const FLYERS = ['jetpack', 'kite', 'crow', 'pixelghost'], PERCHED = ['turret', 'sniper', 'monkey', 'rockthrower', 'fanturret'], WATERERS = ['scuba', 'piranha'];

  let S, seedFn = null;
  function mulberry(seed) { let a = (seed >>> 0) || 1; return () => { a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
  function setSeed(n) { if (seedFn) seedFn(n); }

  // ------------------------------------------------------------------------------------------------ environment
  function nodeEnv() {
    const fs = require('fs'), path = require('path'), vm = require('vm');
    const root = path.join(__dirname, '..');
    const win = {}, noop = () => {};
    const ctxStub = new Proxy({}, { get: (t, k) => (k === 'canvas' ? {} : noop), set: () => true });
    const doc = { createElement: () => ({ getContext: () => ctxStub, width: 0, height: 0, style: {} }), getElementById: () => null };
    const store = {};
    let rnd = mulberry(1);
    const M = {}; for (const k of Object.getOwnPropertyNames(Math)) M[k] = Math[k]; M.random = () => rnd();
    const sandbox = { window: win, document: doc, console, Math: M, Date, Uint8Array, Int16Array, Int32Array, Float32Array, Float64Array, Set, Map, JSON, Object, Array, Number, String, Error, Proxy,
      performance: { now: () => Date.now() }, localStorage: { getItem: (k) => store[k] || null, setItem: (k, v) => { store[k] = v; } }, setTimeout, clearTimeout,
      navigator: { userAgent: 'node', maxTouchPoints: 0 }, location: { search: '' }, requestAnimationFrame: noop };
    win.localStorage = sandbox.localStorage; win.document = doc; win.navigator = sandbox.navigator; win.addEventListener = noop; win.location = sandbox.location;
    vm.createContext(sandbox);
    for (const f of ['util', 'config', 'save', 'comic', 'fx', 'terrain', 'rig', 'props', 'dudes', 'themes', 'levelgen', 'weapons', 'supers', 'entities', 'enemies', 'bosses', 'player', 'game']) {
      vm.runInContext(fs.readFileSync(path.join(root, 'js', f + '.js'), 'utf8'), sandbox, { filename: f + '.js' });
    }
    const s = win.SGS;
    stubs(s);
    seedFn = (n) => { rnd = mulberry(n); };
    s.Save.load();
    return s;
  }
  function stubs(s) {
    const noop = () => {}, sim = {}, held = {};
    // a do-nothing Input (no keys held, 'keys' aim mode): any method the player / game asks for that is not listed answers undefined
    const base = {
      update: noop, endFrame: noop, down: (a) => !!held[a], pressed: () => false, released: () => false, axisX: () => 0, vibrate: noop, lockMouse: noop, clearSim: noop, setSim: (a, v) => { sim[a] = v; },
      aimMode: () => 'keys', cfg: () => 0, assistCone: () => 0, kbTwin: false, kbAim: { x: 0, y: 0 }, mouse: { x: 0, y: 0, has: false }, aimStick: { active: false, x: 0, y: 0 },
    };
    if (!(s.Input && s.Input.setSim && !s.Input.__stub)) s.Input = new Proxy(base, { get: (t, k) => (k in t ? t[k] : (k === '__stub' ? true : noop)) });
    s.Main = s.Main || { mode: 'play', flags: {}, W: 800, H: 450, step(dt) { s.Game.update(dt); } };
    s.Main.W = 800; s.Main.flags = s.Main.flags || {};
    if (!s.Main.pause) s.Main.pause = noop;
  }
  function browserEnv() {
    const s = window.SGS; stubs(s);
    if (s.Save && s.Save.load) s.Save.load();
    let rnd = Math.random; const orig = Math.random; Math.random = () => rnd(); void orig;
    seedFn = (n) => { rnd = mulberry(n); };
    return s;
  }

  // ------------------------------------------------------------------------------------------------ test worlds
  function flatLevel(o) {
    o = o || {};
    const C = S.C, T = C.T, M = S.Terrain.MAT, w = 170, h = 44, tiles = new Uint8Array(w * h);
    for (let x = 0; x < w; x++) for (let y = 28; y < h; y++) tiles[y * w + x] = M.DIRT;
    for (let y = 0; y < h; y++) { tiles[y * w] = M.BEDROCK; tiles[y * w + w - 1] = M.BEDROCK; }
    if (o.pool) for (let x = o.pool[0]; x <= o.pool[1]; x++) for (let y = 28; y < 36; y++) tiles[y * w + x] = M.WATER;
    if (o.tower) for (let x = o.tower.x0; x <= o.tower.x1; x++) for (let y = 28 - o.tower.h; y < 28; y++) tiles[y * w + x] = M.DIRT;
    return { id: 'default', theme: 'default', w, h, T, tiles, spawn: { x: 400, y: 28 * T }, ents: [], flags: [], arena: null, water: null, gravity: 1 };
  }
  function applyDiff() { const d = opt('diff', null); if (d && S.Save && S.Save.data) S.Save.data.settings.game.difficulty = d; }
  function startFlat(o) {
    const lvl = flatLevel(o), G = S.Game, keep = S.LevelGen && S.LevelGen.build;
    if (S.LevelGen) S.LevelGen.build = () => lvl;
    G.start(o.theme || 'plains', { god: true, nomusic: true });
    if (S.LevelGen) S.LevelGen.build = keep;
    G.state = 'play'; G.stateT = 5; G.capT = 1e9;
    G.ents.length = 0; G.ents.push(G.player); S.Shots.clear();
    return lvl;
  }

  // ------------------------------------------------------------------------------------------------ the shooter
  function muzzleOf(p, gun) {
    try { const sv = p.gun; p.gun = gun; const j = p.joints(); p.gun = sv; if (j && j.muzzle) return { dx: (j.muzzle.x - p.x) * (p.facing || 1), dy: p.y - j.muzzle.y }; } catch (e) { /* fall through */ }
    return { dx: 14, dy: 19 };
  }
  // one trigger pull: fires the real weapon from a proxy owner, then rotates the new volley onto the aim line
  function volley(p, e, gun, mode, jit, eye, aimDy) {
    const W = S.Weapons, side = e.x >= p.x ? 1 : -1;
    const mz = eye || muzzleOf(p, gun), mx = p.x + side * mz.dx, my = p.y - mz.dy;
    const owner = { team: 'player', uid: 777777, x: p.x, y: p.y, facing: side, aim: 'fwd', vx: 0, vy: 0, muzzleX: mx, muzzleY: my, dmgMul: p.dmgMul || 1, rateMul: p.rateMul || 1, crit: 0, ricochet: 0, rapid: false };
    const list = S.Shots.list, n0 = list.length;
    W.fire(owner, gun, 1);
    const base = side > 0 ? 0 : Math.PI;
    let ang = base;
    if (mode === 'aimed') ang = Math.atan2((e.y + (aimDy != null ? aimDy : -(e.def.h || e.h) * 0.5)) - my, e.x - mx);
    ang += jit;
    const d = ang - base;
    if (Math.abs(d) > 1e-4) {
      const c = Math.cos(d), s = Math.sin(d);
      for (let i = n0; i < list.length; i++) { const sh = list[i]; if (sh.team !== 'player' || sh.kind === 'beam') continue; const vx = sh.vx, vy = sh.vy; sh.vx = vx * c - vy * s; sh.vy = vx * s + vy * c; }
    }
  }
  // fight one enemy with one gun; returns {killed,t,volleys}
  function fight(e, p, gun, o) {
    const G = S.Game, W = S.Weapons, rnd = Math.random;
    const mode = o.mode || 'aimed', maxT = o.maxT || 10, reach = REACH[gun] || 160, rate = W.rateOf(gun, 1, { rateMul: 1 });
    const mz = muzzleOf(p, gun);
    let t = 0, fireT = o.delay == null ? 0.25 : o.delay, volleys = 0, t0 = null;
    while (t < maxT) {
      const dx = e.x - p.x, side = dx >= 0 ? 1 : -1;
      p.facing = side;
      if (o.chase !== false && Math.abs(dx) > reach + 15) { p.x += side * 200 * DT; p.vx = 0; }
      fireT -= DT;
      const inRange = o.chase === false || Math.abs(dx) <= reach + 60;
      if (fireT <= 0 && !e.dead) {
        if (inRange) { volley(p, e, gun, mode, (rnd() + rnd() - 1) * 0.05, mz, o.aimDy); volleys++; if (t0 == null) t0 = t; fireT += 1 / rate; } else fireT = 0;
      }
      G.update(DT); t += DT;
      if (G.player !== p || p.dead) break;
      if (e.dead) return { killed: true, t: t - (t0 == null ? t : t0), volleys };
      if (e.fellOut) break;
    }
    return { killed: false, t: maxT, volleys, hp: e.hp, at: Math.round(e.x) + ',' + Math.round(e.y), player: Math.round(p.x) + ',' + Math.round(p.y), state: e.state, dead: e.dead, wall: [e.wallL, e.wallR], og: e.onGround, stuck: e.stuckT, tiles: [-3,-2,-1,0,1,2,3].map((k) => S.Terrain.get(Math.floor(e.x / 20) + k, Math.floor((e.y - 10) / 20)) + '/' + S.Terrain.get(Math.floor(e.x / 20) + k, Math.floor((e.y - 30) / 20)) + '/' + S.Terrain.get(Math.floor(e.x / 20) + k, Math.floor((e.y - 50) / 20))).join(' ') };
  }

  // ------------------------------------------------------------------------------------------------ flat matrix
  function runCell(id, gun, o) {
    const G = S.Game, T = S.C.T;
    setSeed(o.seed);
    startFlat({ pool: o.water ? [52, 130] : null, tower: o.tower });
    const p = G.player; p.x = 1000; p.y = 28 * T; p.vx = p.vy = 0; p.facing = 1; G.snapCamera();
    const dist = o.dist || (REACH[gun] || 160);
    const ex = p.x + dist;
    const ey = o.water ? 28 * T + 50 : o.air ? 28 * T - (o.dy || 120) : o.tower ? (28 - o.tower.h) * T : 28 * T;
    const e = G.spawnEnemy(id, ex, ey, { facing: -1, air: !!o.air, perch: !!o.tower, water: !!o.water });
    return fight(e, p, gun, o);
  }
  const median = (a) => { const b = a.slice().sort((x, y) => x - y); return b.length ? b[Math.floor((b.length - 1) / 2)] : NaN; };
  function cell(id, gun, o, trials) {
    const ts = [], vs = []; let fails = 0;
    for (let i = 0; i < trials; i++) {
      const r = runCell(id, gun, Object.assign({}, o, { seed: 1000 + i * 7919 + id.length * 31 }));
      if (r.killed) { ts.push(r.t); vs.push(r.volleys); } else fails++;
    }
    return { t: ts.length ? median(ts) : Infinity, max: ts.length ? Math.max.apply(null, ts) : Infinity, v: vs.length ? median(vs) : Infinity, vmax: vs.length ? Math.max.apply(null, vs) : Infinity, fails, n: trials };
  }
  function limitFor(id) { return id === 'shield' ? 2.0 : id === 'brute' ? 2.5 : 1.2; }

  function matrix(ids, trials, log) {
    const rows = [];
    for (const id of ids) {
      const water = WATERERS.indexOf(id) >= 0;
      const row = { id, hpBefore: HP_BEFORE[id], hp: S.EnemyDefs[id].hp, aimed: {}, flat: {}, issues: [] };
      for (const [dude, gun] of GUNS) {
        row.aimed[gun] = cell(id, gun, { mode: 'aimed', water }, trials);
        row.flat[gun] = water ? row.aimed[gun] : cell(id, gun, { mode: 'flat' }, trials);
      }
      const lim = limitFor(id);
      for (const [dude, gun] of GUNS) {
        const a = row.aimed[gun], f = row.flat[gun];
        if (!(a.t <= lim) || a.fails > 0) row.issues.push('aimed ' + gun + ' ' + fmt(a.t) + 's' + (a.fails ? ' (' + a.fails + ' fail)' : ''));
        if (!(f.t <= lim * 1.5) || f.fails > Math.max(1, trials * 0.15)) row.issues.push('flat ' + gun + ' ' + fmt(f.t) + 's' + (f.fails ? ' (' + f.fails + ' fail)' : ''));
      }
      if (id !== 'brute' && !(row.aimed.pistol.vmax <= 4)) row.issues.push('pistol needs ' + row.aimed.pistol.vmax + ' shots (max)');
      row.pass = row.issues.length === 0;
      rows.push(row);
      if (log) log(id + (row.pass ? ' ok' : ' ISSUES: ' + row.issues.join('; ')));
    }
    return rows;
  }
  function fmt(x) { return isFinite(x) ? x.toFixed(2) : 'X'; }

  // elevated variants: flyers (spawned 120 px above the floor like levelgen's air spawns) + perched (on a tower / wall top)
  function elevated(ids, trials, log) {
    const rows = [];
    for (const id of ids) {
      const row = { id, kind: FLYERS.indexOf(id) >= 0 ? 'flyer' : 'perched', res: {} };
      const guns = ['pistol', 'dual', 'mg', 'shotgun'];
      const variants = row.kind === 'flyer' ? [{ n: 'air120', air: true, dy: 120 }, { n: 'air160', air: true, dy: 160 }] :
        [{ n: 'tower5x6', tower: { x0: 56, x1: 61, h: 5 } }, { n: 'wall6x3', tower: { x0: 58, x1: 60, h: 6 } }, { n: 'ledge3', tower: { x0: 54, x1: 66, h: 3 } }];
      for (const v of variants) for (const mode of ['flat', 'aimed']) for (const gun of guns) {
        const o = { mode, maxT: 14, dist: v.air ? 160 : 150 }; if (v.air) { o.air = true; o.dy = v.dy; } else o.tower = v.tower;
        if (gun === 'shotgun') o.dist = 150;
        // tower spans tiles 56..61 => x 1140..1260; player x=1000 => dist 160 from tower centre 1200 = 200; use dist = 200 for towers
        if (!v.air) o.dist = (((v.tower.x0 + v.tower.x1 + 1) / 2) * 20) - 1000;
        row.res[v.n + '/' + mode + '/' + gun] = cell(id, gun, o, Math.max(2, trials >> 1));
      }
      const bad = []; for (const k in row.res) { const r = row.res[k]; if (k.indexOf('/aimed/') > 0 && (r.fails > 0 || r.t > 6)) bad.push(k + ' ' + fmt(r.t) + (r.fails ? ' (' + r.fails + ' fail)' : '')); }
      row.issues = bad; row.pass = bad.length === 0; rows.push(row);
      if (log) log('elev ' + id + (row.pass ? ' ok' : ' ISSUES: ' + bad.join('; ')));
    }
    return rows;
  }

  // ------------------------------------------------------------------------------------------------ level sweep
  function standing(T, tx, ty) { // feet on the top of tile (tx,ty), 2 tiles of headroom
    const P = T.PROPS, m = T.get(tx, ty); if (!(P[m].solid || P[m].oneway) || P[m].liquid) return false;
    return !P[T.get(tx, ty - 1)].solid && !P[T.get(tx, ty - 2)].solid && !P[T.get(tx, ty - 1)].hazard;
  }
  function reachableCells(lv) {
    const T = S.Terrain, W = T.W, H = T.H, cols = [];
    for (let x = 0; x < W; x++) { const c = []; for (let y = 3; y < H - 1; y++) if (standing(T, x, y)) c.push(y); cols.push(c); }
    const key = (x, y) => x * 4096 + y, seen = new Set(), out = [];
    const sx = Math.floor(lv.spawn.x / S.C.T), sy = Math.round(lv.spawn.y / S.C.T);
    let start = null, bd = 1e9;
    for (let x = Math.max(0, sx - 3); x <= Math.min(W - 1, sx + 3); x++) for (const y of cols[x]) { const d = Math.abs(y - sy) + Math.abs(x - sx); if (d < bd) { bd = d; start = [x, y]; } }
    if (!start) return { cells: [], cols };
    const q = [start]; seen.add(key(start[0], start[1]));
    while (q.length) {
      const [x, y] = q.pop(); out.push([x, y]);
      for (let nx = Math.max(0, x - 7); nx <= Math.min(W - 1, x + 7); nx++) {
        const c = cols[nx], adx = Math.abs(nx - x);
        for (let i = 0; i < c.length; i++) {
          const ny = c[i], up = y - ny;
          if (up > 4 && !(up <= 12 && adx <= 2)) { if (up > 12) continue; else if (!(adx <= 2)) continue; }
          if (up < -24) continue;
          const k = key(nx, ny); if (seen.has(k)) continue;
          seen.add(k); q.push([nx, ny]);
        }
      }
    }
    return { cells: out, cols };
  }
  function sweepTheme(themeId, log, opts) {
    opts = opts || {};
    const G = S.Game, T = S.Terrain, TS = S.C.T;
    setSeed(4242);
    G.start(themeId, { god: true, nomusic: true });
    G.state = 'play'; G.stateT = 5; G.capT = 1e9;
    const lv = G.level, p = G.player;
    const specs = lv.ents.filter((s) => s.type === 'enemy');
    const reach = reachableCells(lv);
    const res = { theme: themeId, total: specs.length, killed: 0, noLos: [], notKilled: [], flatOnlyNo: [], rows: [] };
    const swimCells = (ex, ey) => { const out = []; const cx = Math.floor(ex / TS), cy = Math.floor(ey / TS); for (let x = cx - 10; x <= cx + 10; x++) for (let y = cy - 3; y <= cy + 3; y++) { const m = T.get(x, y); if (T.PROPS[m] && T.PROPS[m].liquid && !T.PROPS[T.get(x, y - 1)].solid) out.push([x, y]); } return out; };
    // best reachable firing spot (clear line to some part of the body) for an enemy standing at (ex,ey)
    function pickSpot(e, water) {
      const ex = e.x, ey = e.y, h = e.hitHeight ? Math.min(e.hitHeight(), Math.max(e.h, e.def.h || 30)) : (e.def.h || 30);
      const cand = [];
      for (const c of reach.cells) { const px = (c[0] + 0.5) * TS, py = c[1] * TS; if (Math.abs(px - ex) <= 330 && Math.abs(px - ex) >= 30 && Math.abs(py - ey) <= 260) cand.push({ x: px, y: py }); }
      if (water) for (const c of swimCells(ex, ey)) { const px = (c[0] + 0.5) * TS, py = (c[1] + 0.5) * TS + 12; if (Math.abs(px - ex) >= 30 && Math.abs(px - ex) <= 330) cand.push({ x: px, y: py, swim: true }); }
      const sample = [ey - h * 0.5, ey - h * 0.8, ey - h * 0.25];
      let best = null, bs = 1e9, flatOk = false;
      for (const c of cand) {
        const my = c.y - 20; let adv = null;
        for (const ty of sample) { if (!T.raycast(c.x, my, ex, ty)) { adv = ty - ey; break; } }
        if (adv == null) continue;
        if (!flatOk && my >= ey - h - 2 && my <= ey + 2 && !T.raycast(c.x, my, ex, my)) flatOk = true;
        const d = Math.abs(c.x - ex), sc = Math.abs(d - 170) + Math.abs(c.y - ey) * 0.35 + (c.x > ex ? 35 : 0) + (c.swim ? 15 : 0);
        if (sc < bs) { bs = sc; best = c; c.aimDy = adv; }
      }
      return { best, flatOk };
    }
    for (const spec of specs) {
      const id = S.EnemyDefs[spec.id] ? spec.id : 'grunt';
      G.ents.length = 0; G.ents.push(p); S.Shots.clear(); G._hostile = { player: [], enemy: [], neutral: [] };
      p.dead = false; p.hidden = false; p.hp = p.maxHp; G.player = p;
      const e = G.spawnEnemy(id, spec.x, spec.y, { facing: spec.facing || -1, air: spec.air, perch: spec.perch, water: spec.water, srcId: spec.id });
      const water = !!spec.water || id === 'scuba' || id === 'piranha';
      const row = { id, x: Math.round(spec.x), y: Math.round(spec.y), perch: !!spec.perch, air: !!spec.air, water: !!spec.water, los: false, flatOk: false, moved: Math.round(Math.hypot(e.x - spec.x, e.y - spec.y)) };
      let t = 0, volleys = 0, attempts = 0, last = null;
      while (attempts < 3 && !e.dead) {
        const pk = pickSpot(e, water);
        if (attempts === 0) row.flatOk = pk.flatOk;
        if (!pk.best) break;
        row.los = true; last = pk.best;
        p.x = pk.best.x; p.y = pk.best.y; p.vx = p.vy = 0; G.snapCamera();
        const r = fight(e, p, 'pistol', { mode: 'aimed', maxT: attempts < 2 ? 3.5 : 6, chase: false, delay: 0.25, aimDy: pk.best.aimDy });
        t += r.t; volleys += r.volleys; attempts++;
      }
      row.killed = e.dead; row.t = t; row.volleys = volleys; row.attempts = attempts;
      if (e.dead) res.killed++;
      else if (!row.los) res.noLos.push(row);
      else { res.notKilled.push(row); row.hpLeft = e.hp; row.cx = Math.round(last.x); row.cy = Math.round(last.y); const tx = Math.floor(e.x / TS), ty = Math.floor((e.y - 1) / TS); row.diag = 'now@' + Math.round(e.x) + ',' + Math.round(e.y) + ' state ' + e.state + ' alerted ' + e.alerted + ' tiles[feet-1,feet-2,above] ' + [T.get(tx, ty), T.get(tx, ty - 1), T.get(tx, ty - 2)].join(','); }
      if (!row.flatOk) res.flatOnlyNo.push(row);
      res.rows.push(row);
    }
    if (log) log('sweep ' + themeId + ': ' + res.killed + '/' + res.total + ' killed, noLOS ' + res.noLos.length + ', notKilled ' + res.notKilled.length + ', no horizontal spot ' + res.flatOnlyNo.length);
    return res;
  }

  // ------------------------------------------------------------------------------------------------ reporting
  function tables(rows) {
    const L = [], pad = (s, n) => String(s).padEnd(n), gs = GUNS.map((g) => g[1]);
    L.push(pad('enemy', 12) + pad('hp', 7) + gs.map((g) => pad(g, 14)).join('') + ' [aimed s/shots | flat s]  limit');
    for (const r of rows) {
      const cells = gs.map((g) => { const a = r.aimed[g], f = r.flat[g]; return pad(fmt(a.t) + '/' + (isFinite(a.v) ? a.v : 'X') + '|' + fmt(f.t), 14); }).join('');
      L.push(pad(r.id, 12) + pad(r.hpBefore + '>' + r.hp, 7) + cells + (r.pass ? '  ok' : '  FAIL ' + limitFor(r.id)));
    }
    return L.join('\n');
  }
  function elevTables(rows) {
    const L = [];
    for (const r of rows) {
      L.push(r.id + ' (' + r.kind + ') ' + (r.pass ? 'ok' : 'ISSUES ' + r.issues.join('; ')));
      for (const k in r.res) { const c = r.res[k]; if (/pistol|mg/.test(k)) L.push('    ' + k.padEnd(26) + fmt(c.t) + 's  fails ' + c.fails + '/' + c.n); }
    }
    return L.join('\n');
  }
  function sweepSummary(all) {
    const L = []; let tot = 0, ok = 0;
    for (const r of all) {
      tot += r.total; ok += r.killed;
      L.push(r.theme.padEnd(10) + ' ' + String(r.killed).padStart(3) + '/' + String(r.total).padEnd(4) + ' noLOS ' + r.noLos.length + '  notKilled ' + r.notKilled.length + '  noHorizontalSpot ' + r.flatOnlyNo.length);
      for (const x of r.noLos) L.push('     NO-LOS     ' + x.id + ' @' + x.x + ',' + x.y + (x.perch ? ' perch' : '') + (x.air ? ' air' : '') + (x.water ? ' water' : ''));
      for (const x of r.notKilled) L.push('     NOT-KILLED ' + x.id + ' @' + x.x + ',' + x.y + ' from ' + x.cx + ',' + x.cy + ' hpLeft ' + x.hpLeft + ' ' + (x.diag || ''));
    }
    L.push('TOTAL ' + ok + '/' + tot);
    return L.join('\n');
  }

  // ------------------------------------------------------------------------------------------------ main
  function run(o) {
    o = o || {};
    const log = o.log || (() => {});
    const ids = (o.only ? String(o.only).split(',') : S.Enemies.ids().filter((k) => k !== 'barrelroller' && S.EnemyDefs[k]));
    const trials = +o.trials || 6;
    const out = { matrix: null, elevated: null, sweep: null };
    if (!o.sweeponly) {
      out.matrix = matrix(ids, trials, log);
      out.elevated = elevated(ids.filter((k) => FLYERS.indexOf(k) >= 0 || PERCHED.indexOf(k) >= 0), trials, log);
    }
    if (o.sweep || o.sweeponly) {
      const th = o.themes ? String(o.themes).split(',') : THEMES;
      out.sweep = th.map((t) => sweepTheme(t, log, o));
    }
    return out;
  }
  function report(out) {
    const L = [];
    if (out.matrix) { L.push('=== TTK MATRIX (median seconds / volleys aimed | seconds flat), flat floor, enemy 160 px away (flame 85, shotgun 150) ==='); L.push(tables(out.matrix)); }
    if (out.elevated) { L.push(''); L.push('=== ELEVATED (flyers 120/160 px up, perched on tower/wall/ledge) ==='); L.push(elevTables(out.elevated)); }
    if (out.sweep) { L.push(''); L.push('=== LEVEL SWEEP (bot teleported to a reachable spot with line of fire, pistol, real AI) ==='); L.push(sweepSummary(out.sweep)); }
    return L.join('\n');
  }

  function probe(spec) { // --probe theme,x,y : print the tile map around a spot (debug aid)
    const [th, px, py] = String(spec).split(','), T = S.Terrain, TS = S.C.T;
    setSeed(4242); S.Game.start(th, { god: true, nomusic: true });
    const tx = Math.floor(+px / TS), ty = Math.floor((+py - 1) / TS), L = [];
    for (let y = ty - 8; y <= ty + 3; y++) { let r = String(y).padStart(4) + ' '; for (let x = tx - 14; x <= tx + 14; x++) { const m = T.get(x, y); r += (x === tx && y === ty ? '[' + m + ']' : ' ' + m + ' ').padEnd(3); } L.push(r); }
    console.log('tiles around tx=' + tx + ' ty=' + ty + ' (materials: 0 empty 1 dirt 2 rock 3 steel 4 wood 5 plat 9 bedrock 15 glass):\n' + L.join('\n'));
    const ents = S.Game.level.ents.filter((e) => Math.abs(e.x - px) < 200 && Math.abs(e.y - py) < 120).map((e) => e.type + ':' + (e.id || '') + '@' + Math.round(e.x) + ',' + Math.round(e.y));
    console.log('level ents nearby: ' + ents.join(' '));
  }
  if (IN_NODE) {
    S = nodeEnv(); applyDiff();
    if (opt('probe', null)) { probe(opt('probe', null)); return; }
    if (opt('trace', null)) { // --trace id,gun,mode : every trial of one cell, with the enemy's final state
      const [id, gun, mode] = String(opt('trace', null)).split(',');
      for (let i = 0; i < (+opt('trials', 12)); i++) { const r = runCell(id, gun, { mode: mode || 'aimed', water: WATERERS.indexOf(id) >= 0, seed: 1000 + i * 7919 + id.length * 31, trace: true }); console.log(i, JSON.stringify(r)); }
      return;
    }
    const t0 = Date.now();
    const out = run({ only: opt('only', null), trials: opt('trials', 6), sweep: !!opt('sweep', false), sweeponly: !!opt('sweeponly', false), themes: opt('themes', null), log: (m) => { if (opt('verbose', false)) console.error(m); } });
    if (opt('json', false)) console.log(JSON.stringify(out)); else console.log(report(out));
    console.error('done in ' + ((Date.now() - t0) / 1000).toFixed(1) + 's');
  } else {
    window.TTK = { run, report, init() { S = browserEnv(); return S; } };
  }
})();
