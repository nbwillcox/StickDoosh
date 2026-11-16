#!/usr/bin/env node
// STICK DOOSH - tools/dodgetest.js (owner: bosses)  ---  "is every boss attack dodgeable?" proof harness.
//
//   node tools/dodgetest.js                      full matrix (12 bosses x every pattern x phase 1/2 x 12 start positions) + audit
//   node tools/dodgetest.js --only ice,fire      some bosses
//   node tools/dodgetest.js --starts 4           fewer start positions (quick check)
//   node tools/dodgetest.js --fights             also run one full fight per boss with a shooting bot (non-god) and report hits taken
//   node tools/dodgetest.js --fightsonly         only the fights
//   node tools/dodgetest.js --parallel           one child process per boss (much faster)
//   node tools/dodgetest.js --react 0.25 --seed 7 --verbose
// Browser: open tools/dodgetest.html (same code, real game scripts, results table).
//
// The bot is a "fair player": it never sees the future. Every 0.1 s it reads boss.threats() (exactly what a human sees on screen: hatched
// zones, locked aim rays, projectiles, the ram lane) and ignores each threat for the first 0.25 s after it appears (human reaction time).
// It then simulates its OWN body (the real SGS.Phys, run speed 215, jump -500, wall climb) for 2.4 s under a menu of macro moves
// {stay, run L/R for 0.25/0.5/1/until the wall (= wall climb), jump, jump-run L/R} each with an optional 0..0.5 s delay and takes the first
// one that avoids every threat volume. A pattern PASSES when the bot takes ZERO hits from it, from every start position.
(function () {
  'use strict';
  const IN_NODE = typeof window === 'undefined';
  const argv = IN_NODE ? process.argv.slice(2) : [];
  const opt = (n, d) => { const i = argv.indexOf('--' + n); if (i < 0) return d; const v = argv[i + 1]; return (v === undefined || v.startsWith('--')) ? true : v; };

  // ------------------------------------------------------------------------------------------------ environment
  let S, press, seedRandom;
  function nodeEnv() {
    const fs = require('fs'), path = require('path'), vm = require('vm');
    const root = path.join(__dirname, '..');
    const win = {}, noop = () => {};
    const ctxStub = new Proxy({}, { get: (t, k) => (k === 'canvas' ? {} : noop), set: () => true });
    const doc = { createElement: () => ({ getContext: () => ctxStub, width: 0, height: 0, style: {} }), getElementById: () => null };
    const store = {};
    let rnd = () => 0.5, errCount = 0;
    const M = {}; for (const k of Object.getOwnPropertyNames(Math)) M[k] = Math[k]; M.random = () => rnd();
    const con = Object.assign({}, console, { error: function () { errCount++; if (errCount <= 3) console.error.apply(console, arguments); } });
    const sandbox = { window: win, document: doc, console: con, Math: M, Date, Uint8Array, Int16Array, Int32Array, Float32Array, Float64Array, Set, Map, JSON, Object, Array, Number, String, Error, Proxy,
      performance: { now: () => Date.now() }, localStorage: { getItem: (k) => store[k] || null, setItem: (k, v) => { store[k] = v; } }, setTimeout, clearTimeout,
      navigator: { userAgent: 'node', maxTouchPoints: 0 }, location: { search: '' }, requestAnimationFrame: noop };
    win.localStorage = sandbox.localStorage; win.document = doc; win.navigator = sandbox.navigator; win.addEventListener = noop; win.location = sandbox.location;
    vm.createContext(sandbox);
    for (const f of ['util', 'config', 'save', 'comic', 'fx', 'terrain', 'rig', 'props', 'dudes', 'themes', 'levelgen', 'weapons', 'supers', 'entities', 'enemies', 'bosses', 'player', 'game']) {
      vm.runInContext(fs.readFileSync(path.join(root, 'js', f + '.js'), 'utf8'), sandbox, { filename: f + '.js' });
    }
    const s = win.SGS, sim = {}, prev = {}, held = {};
    s.Input = {
      update() { for (const a in sim) { prev[a] = held[a]; held[a] = !!sim[a]; } },
      endFrame: noop, down: (a) => !!held[a], pressed: (a) => !!held[a] && !prev[a], released: () => false,
      axisX: () => (held.right ? 1 : 0) - (held.left ? 1 : 0), vibrate: noop,
      // twin-stick aim API (player.aimStep): the bot plays on plain keys (8-way aim: up / left / right)
      aimMode: () => (s.Input.fightAim ? 'stick' : 'keys'), mouse: { has: true, x: 0, y: 0 }, aimStick: { active: false, x: 0, y: 0, mag: 0 }, kbAim: { x: 0, y: 0 }, kbTwin: false, cfg: () => undefined, assistCone: () => 0, lockMouse: noop, clearSim() { for (const k in sim) sim[k] = false; }, setSim(a, v) { sim[a] = !!v; },
    };
    s.Main = { mode: 'play', flags: {}, W: 800, H: 450, step(dt) { s.Input.update(); s.Game.update(dt); s.Input.endFrame(); } };
    s.Save.load();
    return { S: s, errors: () => errCount, press: (a, v) => { if (sim[a] === undefined) { sim[a] = false; held[a] = false; prev[a] = false; } sim[a] = !!v; }, seed(n) { rnd = mulberry(n); } };
  }
  function browserEnv() {
    const s = window.SGS; s.Main.pause = function () {}; s.Main.mode = 'play';
    const upd = s.Input.update; // the real Input.update() re-polls the pad every frame and would clear the bot's twin-stick aim: re-apply it afterwards
    s.Input.update = function () { upd.call(this); const I = s.Input; if (I.fightAim && I.fightVec) { I.aimStick.active = true; I.aimStick.x = I.fightVec[0]; I.aimStick.y = I.fightVec[1]; I.aimStick.mag = 1; } };
    let rnd = Math.random; const orig = Math.random; Math.random = () => rnd();
    void orig;
    return { S: s, press: (a, v) => s.Input.setSim(a, v), seed(n) { rnd = mulberry(n); } };
  }
  function mulberry(seed) { let a = (seed >>> 0) || 1; return () => { a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
  function hash(str) { let h = 2166136261; for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }

  const THEMES = ['ice', 'fire', 'wind', 'water', 'mud', 'jungle', 'mountain', 'plains', 'fantasy', 'moon', 'retro', 'fortress'];
  const DT = 1 / 60;

  // ------------------------------------------------------------------------------------------------ the bot
  function makeBot(o) {
    o = o || {};
    const C = S.C, U = S.U, B = S.Bosses, G = S.Game;
    const react = o.react == null ? 0.25 : o.react, H = o.horizon || 2.4, fight = !!o.fight;
    const bot = { seen: new Map(), plan: null, planT0: 0, lastDecide: -9, sig: '', noSafe: 0, decisions: 0, hits: [], jumpKey: false };

    const approach = (v, t, d) => (v < t ? Math.min(v + d, t) : Math.max(v - d, t));
    function clonePlayer(p) {
      const st = G.stats || {};
      return { x: p.x, y: p.y, w: p.w, h: p.h, vx: p.vx, vy: p.vy, onGround: p.onGround, wall: p.wall || 0, coyote: p.onGround ? C.COYOTE : (p.coyote || 0), jumped: !!p.jumped, pushT: p.pushT || 0,
        facing: p.facing || 1, spd: p.speedMul(), jmul: (st.jumpMul || 1) * ((p.def && p.def.jump) || 1), climbMul: st.climbMul || 1, slippery: p.slippery, slow: p.slow, inLiquid: p.inLiquid, drop: false, stepUp: true, noGrav: false, wantDown: false, climbing: false };
    }
    function stepSim(e, ax, jumpPress, jumpHeld, windAx) { // the subset of Player.update that decides where the body goes
      const maxV = C.RUN * e.spd, jv = C.JUMP * e.jmul;
      const acc = e.onGround ? (e.slippery ? 520 : C.ACCEL_GROUND) : C.ACCEL_AIR;
      if (ax !== 0) e.vx = approach(e.vx, ax * maxV, acc * DT); else e.vx = approach(e.vx, 0, (e.onGround ? (e.slippery ? 160 : C.FRICTION) : 350) * DT);
      if (windAx) e.vx += windAx * DT;
      if (e.onGround) { e.coyote = C.COYOTE; e.jumped = false; } else e.coyote -= DT;
      if (jumpPress) {
        if (e.coyote > 0) { e.vy = jv; e.coyote = 0; e.jumped = true; e.onGround = false; }
        else if (e.wall && !e.onGround) { e.vy = jv * 0.92; e.vx = -e.wall * C.RUN * 0.95; e.jumped = true; }
      }
      if (!jumpHeld && e.vy < jv * 0.38 && e.jumped) e.vy *= 0.5; // releasing jump early cuts the arc
      const push = e.wall !== 0 && ax !== 0 && Math.sign(ax) === e.wall;
      if (push && e.onGround) e.pushT += DT; else if (!push) e.pushT = 0;
      if (push && (!e.onGround || e.pushT > 0.1)) { e.vy = -C.CLIMB * e.climbMul * 1.15; e.vx = e.wall * 20; }
      if (e.wall && !e.onGround && !push && e.vy > 70) e.vy = 70;
      S.Phys.move(e, DT);
    }
    // ---- threat preparation (once per decision)
    function prep(th) {
      const rects = [], balls = [], winds = [];
      for (const t of th) {
        if (t.k === 'rect') rects.push(t);
        else if (t.k === 'wind') winds.push(t);
        else if (t.k === 'ball') {
          const b = Object.assign({}, t, { path: null });
          if (!t.hom) { // pre-sample the ballistic path (stops on terrain unless noTerrain)
            const n = Math.ceil(Math.min(t.t1 - t.t0, 4) * 60), xs = new Float32Array(n + 1), ys = new Float32Array(n + 1); let end = n;
            for (let i = 0; i <= n; i++) {
              const tau = i / 60;
              xs[i] = t.x + t.vx * tau; ys[i] = t.sine ? t.sine.y0 + t.sine.a * Math.sin((t.sine.age + tau) * t.sine.f + t.sine.ph) : t.y + t.vy * tau + 0.5 * t.g * tau * tau;
              if (!t.noTerrain && i > 0 && S.Terrain.solidPx(xs[i], ys[i])) { end = i; break; }
            }
            b.path = { xs, ys, n: end };
            if (t.burst && end < n) rects.push({ k: 'rect', x0: xs[end] - t.burst.w / 2, x1: xs[end] + t.burst.w / 2, y0: Math.floor(ys[end] / C.T) * C.T - t.burst.h, y1: Math.floor(ys[end] / C.T) * C.T, vx: 0, vy: 0, t0: t.t0 + end / 60, t1: t.t0 + end / 60 + t.burst.life });
          }
          balls.push(b);
        }
      }
      return { rects, balls, winds };
    }
    let M = 2; // px of safety margin the bot keeps (humans are not pixel perfect); decisions try 20, 10 then 2 px
    function windAt(P, t, x) { let a = 0; for (const w of P.winds) if (t >= w.t0 && t <= w.t1) { const s = x >= w.src ? 1 : -1; a += (w.mag > 0 ? s : -s) * Math.abs(w.mag); } return a; }
    // run one candidate; returns time of the first hit (Infinity = safe)
    function simulate(P, p, cand) {
      const e = clonePlayer(p), steps = Math.ceil(H / DT);
      const hb = P.balls.map((b) => (b.hom ? { x: b.x, y: b.y, vx: b.vx, vy: b.vy } : null));
      for (let i = 0; i < steps; i++) {
        const t = i * DT, u = t - cand.d;
        let ax = 0, jp = false, jh = false;
        if (u >= 0) { ax = cand.ax(u); if (cand.jump) { jp = u < DT * 0.99 && (cand.d > 0 || bot.canRepress); jh = u < 0.5; } }
        stepSim(e, ax, jp, jh, windAt(P, t, e.x));
        if (!isFinite(e.x)) return 0;
        for (const r of P.rects) {
          if (t < r.t0 - 0.02 || t > r.t1 + 0.05) continue;
          const dt_ = t - r.t0, ox = r.vx * dt_, oy = (r.vy || 0) * dt_;
          if (e.x + 5 + M > r.x0 + ox && e.x - 5 - M < r.x1 + ox && e.y + M > r.y0 + oy + 2 && e.y - 30 - M < r.y1 + oy) return t;
        }
        for (let k = 0; k < P.balls.length; k++) {
          const b = P.balls[k];
          if (t < b.t0 || t > b.t1) continue;
          let bx, by;
          if (b.hom) { // slow seeker: turn toward the (simulated) player at its published turn rate (for homeT seconds), then fly straight
            const h = hb[k]; if (t > b.t0) { const steer = (t - b.t0) < b.homeT; const want = Math.atan2(e.y - 16 - h.y, e.x - h.x), cur = Math.atan2(h.vy, h.vx); let da = want - cur; while (da > Math.PI) da -= 2 * Math.PI; while (da < -Math.PI) da += 2 * Math.PI; const na = steer ? cur + Math.max(-b.hom * DT, Math.min(b.hom * DT, da)) : cur, v = Math.hypot(h.vx, h.vy); h.vx = Math.cos(na) * v; h.vy = Math.sin(na) * v; h.x += h.vx * DT; h.y += h.vy * DT; }
            bx = h.x; by = h.y;
          } else {
            const idx = Math.round((t - b.t0) * 60); if (idx > b.path.n) continue;
            bx = b.path.xs[idx]; by = b.path.ys[idx];
          }
          if (Math.abs(e.x - bx) < 5 + b.r + M && by > e.y - 30 - b.r - M && by < e.y - 2 + b.r + M) return t;
        }
      }
      return Infinity;
    }
    function buildCands(dirB, intent) {
      const mk = (name, ax, jump) => ({ name, ax, jump });
      const run = (dir, dur) => mk('run' + (dir < 0 ? 'L' : 'R') + dur, (u) => (u < dur ? dir : 0), false);
      const jmp = (dir, dur) => mk('jump' + (dir ? (dir < 0 ? 'L' : 'R') + dur : ''), (u) => (dir && u < dur ? dir : 0), true);
      const base = [mk('stay', () => 0, false), run(-1, 0.25), run(1, 0.25), run(-1, 0.5), run(1, 0.5), jmp(0), jmp(-1, 0.7), jmp(1, 0.7), run(-1, 1), run(1, 1), jmp(-1, 9), jmp(1, 9), run(-1, 9), run(1, 9)];
      const out = [];
      if (intent) out.push(Object.assign(run(intent, 9), { d: 0, name: 'intent' }));
      for (const d of [0, 0.15, 0.3, 0.5]) for (const c of base) { if (d > 0 && c.name === 'stay') continue; out.push(Object.assign({}, c, { d })); }
      void dirB;
      return out;
    }
    // ---- one frame of control
    bot.control = function () {
      const p = G.player, b = G.boss, now = G.time;
      if (!p || p.dead || !b || b.dead) { for (const a of ['left', 'right', 'jump', 'fire', 'up']) press(a, false); return; }
      const th = b.threats ? b.threats() : [];
      if (fight) for (const s of S.Shots.list) { // enemy bullets of the minions are visible to a human too
        if (s.dead || s.team !== 'enemy' || s.bossShot || s.kind === 'beam') continue;
        s._tid = s._tid || ('e' + (bot.eid = (bot.eid || 0) + 1));
        th.push({ id: s._tid, k: 'ball', x: s.x, y: s.y, vx: s.vx, vy: s.vy, g: s.grav ? C.GRAV * s.grav * (G.grav || 1) : 0, r: (s.r || 3) + 1, t0: 0, t1: Math.max(0.1, s.life), hom: 0 });
      }
      for (const t of th) if (!bot.seen.has(t.id)) bot.seen.set(t.id, now);
      if (bot.seen.size > 400) for (const [k, v] of bot.seen) if (now - v > 8) bot.seen.delete(k);
      const known = th.filter((t) => t.pre || now - bot.seen.get(t.id) >= react - 1e-6); // 'pre' = already announced by a hatched marker
      const sig = known.map((t) => t.id).join(',');
      let tgt = null, intent = 0;
      if (fight) {
        let best = 1e9; for (const e of G.ents) { if (e.dead || (e.kind !== 'enemy' && e.kind !== 'boss') || e._dying) continue; const d = Math.abs(e.x - p.x) + (e.kind === 'boss' ? 60 : 0); if (d < best && d < 520) { best = d; tgt = e; } }
        if (!tgt) tgt = b;
        const dx = tgt.x - p.x, ad = Math.abs(dx);
        intent = ad > 280 ? Math.sign(dx) : ad < 130 ? -Math.sign(dx) : 0;
      }
      const need = known.length > 0 || intent !== 0;
      if (need && (!bot.plan || sig !== bot.sig || now - bot.lastDecide >= 0.1)) {
        bot.lastDecide = now; bot.sig = sig; bot.decisions++;
        const P = prep(known), cands = buildCands(0, intent);
        bot.canRepress = !bot.jumpKey || p.onGround || p.vy > -150; // a held jump key can only be re-pressed (wall-jump) if releasing it would not cut a fast rise
        let chosen = null, bestT = -1, bestC = null;
        const ev = [];
        for (const mg of [20, 10, 2]) {
          M = mg;
          for (const c of cands) { const t = simulate(P, p, c); if (bot.log) ev.push(mg + ':' + c.name + '+' + c.d + ':' + (t === Infinity ? 'ok' : t.toFixed(2))); if (t === Infinity) { chosen = c; break; } if (mg === 2 && t > bestT + 1e-9) { bestT = t; bestC = c; } }
          if (chosen) break;
        }
        M = 2;
        if (bot.log) bot.log.push({ gt: now, ev: ev.join(' '), known: known.length });
        if (!chosen) { chosen = bestC; bot.noSafe++; }
        // re-choosing the same move keeps its original start time (so a delayed jump is not postponed forever); otherwise the new plan starts now+d
        const absNew = now + chosen.d;
        if (!(bot.plan && bot.plan.name === chosen.name && Math.abs(absNew - bot.plan.abs) <= 0.12)) { bot.plan = Object.assign({}, chosen, { abs: absNew }); bot.newPlan = true; }
      } else if (!need) bot.plan = null;
      // keys
      let ax = 0, wantJump = false;
      if (bot.plan) { const u = now - bot.plan.abs; if (u >= 0) { ax = bot.plan.ax(u); if (bot.plan.jump && u < 0.5) wantJump = true; } }
      press('left', ax < 0); press('right', ax > 0);
      // jump needs a rising edge (key up the frame before). A started jump is held up to 0.5 s; a plan switch to a non-jump move releases it.
      if (wantJump) {
        if (!bot.jumpActive || (bot.newPlan && bot.plan.jump && !p.onGround && p.vy > -150 && bot.jumpKey)) { bot.jumpActive = false; if (bot.jumpKey) { press('jump', false); bot.jumpKey = false; } else { press('jump', true); bot.jumpKey = true; bot.jumpActive = true; bot.jumpEnd = now + 0.5; } }
        else if (now < bot.jumpEnd) { press('jump', true); bot.jumpKey = true; } else { press('jump', false); bot.jumpKey = false; }
      } else { press('jump', false); bot.jumpKey = false; bot.jumpActive = false; }
      if (p.onGround && bot.jumpActive && now > bot.jumpEnd) bot.jumpActive = false;
      bot.newPlan = false;
      // shooting (fights): the twin-stick aim points at the target, fire is held while it is in range
      if (fight && tgt) {
        const I = S.Input, sx = p.x, sy = p.y - 26, tx = tgt.x, ty = tgt.y - (tgt.h || 30) * 0.5, L = Math.hypot(tx - sx, ty - sy) || 1;
        I.fightAim = true; I.fightVec = [(tx - sx) / L, (ty - sy) / L]; I.aimStick.active = true; I.aimStick.x = I.fightVec[0]; I.aimStick.y = I.fightVec[1]; I.aimStick.mag = 1;
        press('fire', L < 560);
      }
    };
    bot.releaseAll = () => { for (const a of ['left', 'right', 'jump', 'fire', 'up', 'down']) press(a, false); bot.jumpKey = false; };
    return bot;
  }

  // ------------------------------------------------------------------------------------------------ scenario driver
  function stepFrame() { S.Main.step(DT); }
  function startFight(theme, seed, opts) {
    opts = opts || {};
    seedRandom(seed);
    const G = S.Game;
    S.Main.mode = 'play';
    G.start(theme, Object.assign({ boss: true, god: false, nomusic: true }, opts.flags || {}));
    const A = G.level.arena;
    G.player.x = A.x0 + 120; G.player.y = A.y1; G.player.vx = 0; G.player.vy = 0;
    for (let i = 0; i < 400 && !(G.boss && G.state === 'boss'); i++) { G.player.x = Math.max(G.player.x, A.x0 + 120); stepFrame(); }
    if (!G.boss) throw new Error('boss did not spawn for ' + theme);
    return G;
  }
  function platforms(G) {
    const A = G.level.arena, T = S.Terrain, C = S.C, out = [];
    for (let ty = A.ty0; ty <= A.ty1 + 1; ty++) {
      let run = null;
      for (let tx = A.tx0; tx <= A.tx1 + 1; tx++) {
        if (T.get(tx, ty) === T.MAT.PLAT) { if (!run) run = { x0: tx * C.T, x1: (tx + 1) * C.T, y: ty * C.T }; else run.x1 = (tx + 1) * C.T; } else if (run) { out.push(run); run = null; }
      }
      if (run) out.push(run);
    }
    return out;
  }
  function startPositions(G, n, rnd) {
    const A = G.level.arena, pl = platforms(G), out = [];
    out.push({ x: A.x0 + 8, y: A.y1, tag: 'wallL' }, { x: A.x1 - 8, y: A.y1, tag: 'wallR' });
    pl.slice(0, 2).forEach((q, i) => out.push({ x: (q.x0 + q.x1) / 2, y: q.y, tag: 'plat' + i }));
    while (out.length < n) out.push({ x: A.x0 + 8 + rnd() * (A.x1 - A.x0 - 16), y: A.y1, tag: 'rnd' });
    return out.slice(0, n);
  }
  function liveThreats(b) { return b.threats().filter((t) => t.t1 > 0.05); }
  function classify(src) { if (!src) return 'env'; if (src.bossFx || src.bossShot || src.kind === 'boss' || src.isBoss) return 'boss'; if (src.kind === 'enemy') return 'minion'; return 'env'; }

  // run ONE forced pattern from one start position. returns {hits, other, frames}
  function runPattern(theme, patId, phase, pos, bossX, seed, o) {
    o = o || {};
    const G = startFight(theme, seed), p = G.player, b = G.boss, A = G.level.arena;
    const B = S.Bosses; B.audit.on = true; B.audit.log.length = 0;
    b.interrupt('rest', 99); b.noStartT = 1e9; b.mode = 'rest'; b.mt = 99;
    if (phase === 2) { b.hp = Math.floor(b.maxHp * 0.49); b.goEnraged(); b.interrupt('rest', 99); b.noStartT = 1e9; }
    G.godMode = false; p.hp = p.maxHp = 99; p.inv = 0; p.hurtT = 0; p.barrier = 0;
    p.x = pos.x; p.y = pos.y; p.vx = 0; p.vy = 0; p.onGround = true;
    const bd = { l: A.x0 + (b.hw || b.w / 2) + 6, r: A.x1 - (b.hw || b.w / 2) - 6 };
    b.x = Math.max(bd.l, Math.min(bd.r, bossX)); if (!b.impl.hoverKeep) { /* hover bosses re-settle their own y */ }
    const hits = [], origHurt = p.hurt;
    p.hurt = function (dmg, src, info) { const r = origHurt.call(this, dmg, src, info); if (r !== false) hits.push({ t: G.time - t0, kind: classify(src), what: src && (src.style || src.shape || src.id || src.kind), x: p.x, y: p.y }); return r; };
    const bot = makeBot({ react: o.react }); if (o.trace) bot.log = [];
    const drive = o.statue ? () => {} : () => bot.control(); // statue = a player who never moves (shows the attack really threatens)
    for (let i = 0; i < 4; i++) { drive(); stepFrame(); } // settle
    p.inv = 0; p.hurtT = 0;
    const t0 = G.time;
    if (!b.forcePattern(patId)) throw new Error('no pattern ' + patId);
    let calm = 0, ended = false, frames = 0;
    for (; frames < 60 * 16; frames++) {
      drive();
      if (o.trace && frames % 6 === 0) { const th = b.threats().filter((t) => t.t1 > 0); o.trace.push({ t: +(G.time - t0).toFixed(2), px: Math.round(p.x), py: Math.round(p.y), vx: Math.round(p.vx), plan: bot.plan ? bot.plan.name + '+' + bot.plan.d : '-', mode: b.mode, bx: Math.round(b.x), th: th.map((q) => (q.k === 'rect' ? 'R[' + Math.round(q.x0) + '..' + Math.round(q.x1) + ' y' + Math.round(q.y0) + '..' + Math.round(q.y1) + ' v' + Math.round(q.vx) + ' t' + q.t0.toFixed(2) + '-' + q.t1.toFixed(2) + ']' : q.k === 'ball' ? 'B[' + Math.round(q.x) + ',' + Math.round(q.y) + ' v' + Math.round(q.vx) + ',' + Math.round(q.vy) + ' t' + q.t0.toFixed(2) + ']' : 'W')).join(' ') }); }
      stepFrame();
      if (G.boss !== b || b.dead) break;
      if (b.mode !== 'tele' && b.mode !== 'act') ended = true;
      if (ended) { calm = liveThreats(b).length ? 0 : calm + DT; if (calm > 0.4) break; }
    }
    p.hurt = origHurt; bot.releaseAll();
    const audit = B.audit.log.slice(); B.audit.on = false; if (o.trace) o.trace.botLog = bot.log.map((l) => Object.assign(l, { gt: +(l.gt - t0).toFixed(2) }));
    return { hits, frames, ended, noSafe: bot.noSafe, audit, time: G.time - t0 };
  }
  function traceRun(spec) {
    const [theme, pat, ph, idx] = spec.split(':'), phase = +ph, i = +idx;
    const rnd = mulberry(hash(theme + pat + phase)), g0 = startFight(theme, 2), poss = startPositions(g0, +opt('starts', 12), rnd), A = g0.level.arena;
    let ps, bossX;
    for (let k = 0; k <= i; k++) { ps = poss[k]; bossX = k % 3 === 0 ? ps.x + (rnd() < 0.5 ? -1 : 1) * (40 + rnd() * 80) : A.x0 + 60 + rnd() * (A.x1 - A.x0 - 120); }
    const tr = [], r = runPattern(theme, pat, phase, ps, bossX, 1000 + i * 17 + phase + (+opt('seedbase', 0)) * 7919, { trace: tr });
    console.log('start', JSON.stringify(ps), 'bossX', Math.round(bossX), 'hits', JSON.stringify(r.hits));
    const h = r.hits.length ? r.hits[0].t : 99;
    if (process.argv.includes('--decisions')) for (const l of tr.botLog) if (l.gt >= h - 0.6 && l.gt <= h + 0.1) console.log('  dec', l.gt, 'known', l.known, l.ev.slice(0, 400));
    for (const f of tr) if (f.t >= h - 1.6 && f.t <= h + 0.2) console.log(f.t, 'p', f.px, f.py, 'v', f.vx, f.plan, f.mode, 'boss', f.bx, '|', f.th.slice(0, 260));
  }

  function auditViolations(a, enraged) {
    const v = [];
    for (const r of a) {
      if (r.k === 'zone' && !r.pre && r.tele < 0.499) v.push('zone armed after only ' + r.tele.toFixed(2) + ' s (' + r.style + ')');
      if (r.k === 'zone' && r.onPlayer && r.tele < 0.7 && !r.pre) v.push('zone spawned on the player with a ' + r.tele.toFixed(2) + ' s telegraph');
      if (r.k === 'proj' && !r.falling && r.speed > (r.enraged ? 421 : 331) && r.speed < 1e5 && r.r !== undefined) v.push('projectile speed ' + Math.round(r.speed));
      if (r.k === 'proj' && !r.falling && r.dist < Math.max(119.9, 0.55 * r.speed - 0.5)) v.push('projectile spawned ' + Math.round(r.dist) + ' px from the player (' + Math.round(r.speed) + ' px/s)');
      if (r.k === 'pattern' && r.tele < 0.59) v.push('pattern ' + r.id + ' telegraph ' + r.tele.toFixed(2) + ' s');
      if (r.k === 'minion' && (r.dist < 249 || r.warn < 0.799)) v.push('minion spawned ' + Math.round(r.dist) + ' px away / warn ' + r.warn);
    }
    void enraged;
    return Array.from(new Set(v));
  }

  function matrix(themes, o) {
    o = o || {};
    const starts = o.starts || 12, res = [];
    for (const theme of themes) {
      const probe = startFight(theme, 1), impl = S.Bosses.Impl[theme], A = probe.level.arena;
      for (const pat of impl.patterns) {
        for (const phase of [1, 2]) {
          if ((phase === 1 && pat.p2) || (phase === 2 && pat.p1)) continue;
          const rnd = mulberry(hash(theme + pat.id + phase)), cell = { theme, pattern: pat.id, phase, runs: 0, hits: 0, failed: [], noSafe: 0, violations: [], boss: 0, minion: 0 };
          const g0 = startFight(theme, 2), poss = startPositions(g0, starts, rnd);
          for (let i = 0; i < poss.length; i++) {
            const ps = poss[i];
            const bossX = i % 3 === 0 ? ps.x + (rnd() < 0.5 ? -1 : 1) * (40 + rnd() * 80) : A.x0 + 60 + rnd() * (A.x1 - A.x0 - 120);
            const r = runPattern(theme, pat.id, phase, ps, bossX, 1000 + i * 17 + phase + (o.seedBase || 0) * 7919, { react: o.react, statue: o.statue });
            cell.runs++;
            const bh = r.hits.filter((h) => h.kind === 'boss'), mh = r.hits.filter((h) => h.kind === 'minion');
            cell.boss += bh.length; cell.minion += mh.length; cell.noSafe += r.noSafe;
            if (bh.length) { cell.hits += bh.length; cell.failed.push({ i, tag: ps.tag, x: Math.round(ps.x), bossX: Math.round(bossX), hit: bh.map((h) => h.what + '@' + h.t.toFixed(2)).join(',') }); }
            for (const v of auditViolations(r.audit, phase === 2)) if (!cell.violations.includes(v)) cell.violations.push(v);
            if (!r.ended && o.verbose) cell.violations.push('pattern did not end in 16 s');
          }
          res.push(cell);
          if (o.log) o.log(cell);
        }
      }
    }
    return res;
  }

  // ---- full fight with a shooting, non-god bot (the player has 99 hp so hits can be counted instead of ending the run)
  function fight(theme, seed, o) {
    o = o || {};
    S.Bosses.audit.on = true; S.Bosses.audit.log.length = 0;
    const G = startFight(theme, seed, { flags: { weapon: o.weapon || 'mg' } }), p0 = G.player, b = G.boss;
    p0.hp = p0.maxHp = 99; p0.inv = 0; p0.barrier = 0;
    var bot; const hits = [], pw = new WeakSet();
    const wrap = (p) => { if (pw.has(p)) return; pw.add(p); const oh = p.hurt; p.hurt = function (d, src, info) { const r = oh.call(this, d, src, info); if (r !== false) { const k = classify(src); hits.push({ t: G.time, kind: k, what: src && (src.style || src.shape || src.id || src.kind) }); if (k === 'boss' && o.verbose) { const th = b.threats().filter((q) => (q.k === 'rect' ? q.x1 > this.x - 200 && q.x0 < this.x + 200 : Math.abs(q.x - this.x) < 200)).map((q) => (q.k === 'rect' ? 'R[' + Math.round(q.x0) + '..' + Math.round(q.x1) + ' y' + Math.round(q.y0) + '..' + Math.round(q.y1) + ' v' + Math.round(q.vx) + ' t' + q.t0.toFixed(2) + '-' + q.t1.toFixed(2) + (q.pre ? ' pre' : '') + ']' : 'B[' + Math.round(q.x) + ',' + Math.round(q.y) + ' t' + q.t0.toFixed(2) + (q.pre ? ' pre' : '') + ']')); console.log('   HIT@' + G.time.toFixed(1) + ' p=(' + Math.round(this.x) + ',' + Math.round(this.y) + ') v=' + Math.round(this.vx) + ',' + Math.round(this.vy) + ' plan=' + (bot.plan ? bot.plan.name + '+' + bot.plan.d : '-') + ' boss=' + b.mode + '/' + (b.pat && b.pat.id) + ' ' + th.join(' ')); console.log('     ents: ' + G.ents.filter((e) => e.bossFx && !e.dead && Math.abs(e.x - this.x) < 260).map((e) => (e.noHit ? 'M' : 'Z') + '[' + Math.round(e.x) + ' w' + e.w + ' t' + e.t.toFixed(2) + '/' + e.tele.toFixed(2) + (e.thr ? ' thr' : '') + (e.pre ? ' pre' : '') + ']').join(' ') + ' | seenAge: ' + Array.from(bot.seen.entries()).filter(([k, v]) => G.time - v < 1.2).map(([k, v]) => k + '@' + (G.time - v).toFixed(2)).join(' '));
 for (const l of bot.log.slice(-3)) console.log('     dec ' + (G.time - l.gt).toFixed(2) + 's ago known=' + l.known + ' ' + l.ev.slice(0, 330)); } if (this.hp < 20) this.hp = 99; } return r; }; };
    wrap(p0);
    bot = makeBot({ fight: true, react: o.react }); if (o.verbose) bot.log = []; const t0 = G.time, cap = o.cap || 300;
    let frames = 0;
    for (; frames < 60 * cap; frames++) {
      if (G.player && !G.player.dead) wrap(G.player);
      bot.control(); stepFrame();
      if (G.state === 'bossdeath' || G.state === 'chopper' || G.state === 'clear' || b.dying || b._dying || b.dead) break;
      if (G.state === 'fail') break;
    }
    bot.releaseAll();
    const alog = S.Bosses.audit.log.slice(); S.Bosses.audit.on = false;
    const rv = auditViolations(alog, true), pats = alog.filter((r) => r.k === 'pattern'), spawn = alog.find((r) => r.k === 'spawn'), en = alog.find((r) => r.k === 'enrage');
    if (spawn && pats.length && pats[0].t - spawn.t < 3.4) rv.push('first attack ' + (pats[0].t - spawn.t).toFixed(2) + ' s after the boss appeared');
    if (en) for (const q of pats) if (q.t > en.t && q.t - en.t < 3.1) rv.push('attack ' + (q.t - en.t).toFixed(2) + ' s after the enrage roar began');
    for (const h of hits) for (const q of pats) if (q.t > h.t + 0.001 && q.t - h.t < 0.9) rv.push('attack started ' + (q.t - h.t).toFixed(2) + ' s after the player was hurt');
    const won = !!(b.dying || b._dying || b.dead || G.state === 'bossdeath' || G.state === 'chopper');
    return { theme, won, time: +(G.time - t0).toFixed(1), hp: Math.max(0, Math.round(b.hp)), maxHp: b.maxHp, bossHits: hits.filter((h) => h.kind === 'boss').length, minionHits: hits.filter((h) => h.kind === 'minion').length, envHits: hits.filter((h) => h.kind === 'env').length, hitList: hits.map((h) => h.kind + ':' + h.what + '@' + h.t.toFixed(0)).join(' '), noSafe: bot.noSafe, phase2: b.enraged, patterns: pats.length, violations: Array.from(new Set(rv)) };
  }

  // ------------------------------------------------------------------------------------------------ CLI
  function fmtCell(c) { return (c.hits === 0 && !c.violations.length ? 'PASS' : 'FAIL') + '  ' + c.theme.padEnd(9) + c.pattern.padEnd(12) + 'P' + c.phase + '  hits ' + c.hits + '/' + c.runs + (c.minion ? ' (+' + c.minion + ' minion)' : '') + (c.noSafe ? '  noSafePlan ' + c.noSafe : '') + (c.violations.length ? '  VIOLATIONS: ' + c.violations.join('; ') : ''); }
  function run(cfg) {
    const themes = cfg.only ? cfg.only.split(',') : THEMES, out = { cells: [], fights: [] };
    if (!cfg.fightsonly) {
      out.cells = matrix(themes, { starts: cfg.starts, react: cfg.react, verbose: cfg.verbose, seedBase: cfg.seedBase, statue: cfg.statue, log: cfg.quiet ? null : (c) => { console.log(fmtCell(c)); if (c.hits) for (const f of c.failed.slice(0, 3)) console.log('      start#' + f.i + ' ' + f.tag + ' x=' + f.x + ' boss x=' + f.bossX + ' -> ' + f.hit); } });
    }
    if (cfg.fights || cfg.fightsonly) for (const th of themes) { const r = fight(th, cfg.seed || 5, { react: cfg.react, verbose: cfg.verbose }); out.fights.push(r); console.log('FIGHT ' + th.padEnd(9) + (r.won ? 'WON ' : 'LOST') + ' ' + r.time + 's  boss hp left ' + r.hp + '/' + r.maxHp + '  hits: boss ' + r.bossHits + ' (noSafePlan ' + r.noSafe + ') minion ' + r.minionHits + ' env ' + r.envHits + (r.violations.length ? '  RULE VIOLATIONS: ' + r.violations.join('; ') : '') + (cfg.verbose ? '  ' + r.hitList : '')); }
    return out;
  }
  if (IN_NODE) {
    const env = nodeEnv(); S = env.S; press = env.press; seedRandom = env.seed; process.on('exit', () => { if (env.errors()) { console.error('!!! ' + env.errors() + ' game errors were logged: results are NOT valid'); process.exitCode = 2; } });
    if (require.main === module) {
      if (opt('trace', null)) { traceRun(opt('trace', null)); return; }
      const cfg = { only: opt('only', null), starts: +opt('starts', 12), react: +opt('react', 0.25), seed: +opt('seed', 5), seedBase: +opt('seedbase', 0), statue: !!opt('statue', false), fights: !!opt('fights', false), fightsonly: !!opt('fightsonly', false), verbose: !!opt('verbose', false), quiet: !!opt('quiet', false) };
      if (opt('parallel', false) && !cfg.only) {
        const { spawn } = require('child_process'); const fs = require('fs'), os = require('os'), path = require('path');
        const results = {}; let pending = THEMES.length;
        const extra = process.argv.slice(2).filter((a, i, arr) => a !== '--parallel');
        THEMES.forEach((th) => {
          const f = path.join(os.tmpdir(), 'dodge_' + th + '.json'); const ch = spawn(process.execPath, [__filename, '--only', th, '--json', f, '--quiet'].concat(extra.filter((a) => a !== '--quiet')), { stdio: ['ignore', 'pipe', 'inherit'] });
          let buf = ''; ch.stdout.on('data', (d) => { buf += d; });
          ch.on('close', () => { try { results[th] = JSON.parse(fs.readFileSync(f, 'utf8')); } catch (e) { results[th] = { cells: [], fights: [], error: String(e) }; } process.stdout.write(buf); if (--pending === 0) summarize(results); });
        });
      } else {
        const out = run(cfg);
        const jf = opt('json', null); if (jf && jf !== true) require('fs').writeFileSync(jf, JSON.stringify(out));
        if (!jf) summarize({ all: out }, true);
      }
    }
  } else {
    window.DodgeTest = { init() { const env = browserEnv(); S = env.S; press = env.press; seedRandom = env.seed; return env; }, run, matrix, fight, runPattern, startFight, THEMES, makeBot };
  }
  function summarize(results, solo) {
    const cells = [], fights = [];
    for (const k in results) { cells.push(...(results[k].cells || [])); fights.push(...(results[k].fights || [])); }
    if (!cells.length && !fights.length) return;
    const bad = cells.filter((c) => c.hits || c.violations.length);
    if (!solo || cells.length) console.log('\n=== DODGE MATRIX: ' + (cells.length - bad.length) + '/' + cells.length + ' pattern-phase cells clean (' + cells.reduce((a, c) => a + c.runs, 0) + ' runs, ' + cells.reduce((a, c) => a + c.hits, 0) + ' boss hits) ===');
    for (const c of bad) console.log(fmtCell(c));
    if (fights.length) { const n = fights.length, avg = fights.reduce((a, f) => a + f.bossHits, 0) / n, avgm = fights.reduce((a, f) => a + f.bossHits + f.minionHits, 0) / n; console.log('=== FIGHTS: ' + fights.filter((f) => f.won).length + '/' + n + ' won, avg boss-attack hits per fight ' + avg.toFixed(2) + ', incl. minions ' + avgm.toFixed(2) + ' ==='); }
    if (IN_NODE) process.exitCode = bad.length ? 1 : 0;
  }
})();
