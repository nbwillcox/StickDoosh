# STICK DOOSH — Design + Build Contract

Silly-first, Broforce-fast, comic-book stick-figure run-and-gun. Web-only (plain HTML5 canvas, classic
`<script>` tags, no build step, no frameworks), one codebase for desktop / phone / controller / keyboard.
Ships to https://github.com/nbwillcox/StickDoosh (GitHub Pages) and the NicTools.dev arcade. CC BY-NC 4.0.

**Pillars:** fast, ridiculous, readable. Nothing is a bullet sponge except bosses. Every gun is a comic word.

## 1. User decisions (locked)
- Engine: web-only JS, ONE build that detects the device (touch => on-screen controls + lighter FX tier).
- Team of 5 = lives (Broforce swap-on-death). Rescue caged stick dudes to get dead members back.
- Aiming (UPDATED 2026-11-16, replaces the old "left/right + up/down only"): full 360-degree omnidirectional
  aim on every input: mouse crosshair, gamepad dual stick (left move / right aim), touch dual stick (floating
  move + aim stick), keyboard 8-way (optional arrows-aim twin-stick). Aim mode Auto/Mouse/Stick/Keys + aim assist.
- Terrain: fully destructible tile grid (explosions carve holes, dig shortcuts, barrels chain).
- Cursing: bleeped by default (beep + `@#$%!` grawlix in bubbles), Settings toggle for uncensored.
- Voices: Kokoro TTS (installed standalone, offline build step) -> mp3 voice lines.
- Mega Man X: beating a boss grants its SUPER (special weapon w/ ammo) + each boss is WEAK to one other super.
  Beat all 11 => final level "DOOSH FORTRESS" unlocks.
- Single player v1 (keep code co-op-friendly: player is an entity, input is read through Input).
- Contra power-ups, infinite-lives cheat code, Mega Man X boss-select screen, shop of permanent upgrades.
- Music: ~15 classic heavy-metal tracks (ComfyUI Stable Audio / MiniMax), bosses have their own music.
- FF6-style boss death: flash-crash, flash-crash, burn burn, EXPLODE.

## 2. Look
- **Comic book.** Thick black ink outlines (#141018), flat SATURATED colors, halftone/Ben-Day dot shading,
  jagged burst shapes, speed lines, caption boxes. Font: "Bangers" (Google Fonts link) fallback Impact.
- **Stick people**: colored limbs with black ink outline (draw black line ~1.9x width first, then color),
  round head (white/skin fill, black outline), tiny expressive face, SILLY props (giant hats, pompadours,
  beards, fishbowl helmets). All characters are procedural (Rig) so animation + giblets are free.
- AI art (ComfyUI, later): title splash, boss mugshots (level select + VS screen), dude portraits (HUD +
  menus), far-background paintings per theme (optional), shop keeper. Everything has a procedural fallback.
- Retro level renders the world pixelated on purpose (low-res offscreen + nearest upscale, 4-color-ish).

### Onomatopoeia (core feature)
| gun | word | behaviour |
|---|---|---|
| pistol / dual | `PEW` | small, yellow, pops at muzzle each shot, random tilt |
| shotgun | `DOOSH` | big, orange-red burst shape behind it, screen kick |
| machine gun | `BRRBRBRRRBRR` | ONE stream word glued to the muzzle that grows letters while firing |
| rocket / missile | `SHHHHHHH` | trails BEHIND the flying missile, letters fade along the path; impact `KA-BOOM` |
| flamethrower | `FWOOOSH` | stream word, stretches with o's |
| laser | `BZZZZT` | along the beam |
| grenade/explosion | `KA-BLAM` `BOOM` `KRAKOOM` | big burst |
| melee | `WHAP!` `BONK!` `THWACK!` | |
| hits/deaths | `SPLAT` `OOF` `POOF` | |

## 3. Controls
Actions: `left right up down jump fire special melee cycle pause` (+ menu `confirm back`).
- Keyboard default: A/D or arrows move, W/Up aim up/climb, S/Down aim down/drop-through, Space jump (also K),
  J fire (also mouse left), L special (also mouse right), ; or Shift melee (also mouse middle... and F),
  Q cycle special, Esc/P pause. Every action has 2 rebindable slots.
- Mouse: virtual crosshair aims 360 from the shoulder; left fire (hold = auto), right special, middle melee, wheel cycle.
- Gamepad: left stick move, RIGHT STICK AIMS 360 (option: fire when pushed), A jump, X / RT fire, B / LT special,
  Y melee, LB/RB cycle, Start pause. Single-stick fallback = 8-way aim from left stick/d-pad.
- Touch: floating move stick (left) + floating AIM stick (right, hold-fire while pushed), buttons FIRE (at current
  aim), JUMP, SPECIAL, MELEE, CYCLE, pause (top). Settings: size, opacity, left-handed swap, floating/fixed, aim stick.
- Player compat fields: `aimAng` (rad, 0=right, up=-PI/2), `aimDir`, `facing`, `aim` ('up'|'down'|'fwd').
  Settings: Save.settings.input.{aim,aimAssist,aimDead,aimSens,mouseSens,padAimFire,kbTwin,cross{},touch.aimStick}.
- Mouse lock setting: Pointer Lock while playing (Esc releases + pauses).

## 4. Player
- One dude on screen at a time. 5-dude team (6 with legendary). HP hearts (base 3) + armor pips.
- Run fast, variable jump, coyote + buffer, WALL CLIMB (Broforce: hold toward wall in air => climb up;
  jump off wall = wall-jump; auto-vault ledges), ladders/vines, drop through one-way platforms (down+jump),
  melee (instakill grunts, breaks 1 tile), special (per-dude, 3 per life) + boss supers (ammo 0..28).
- Death: giblets/confetti, next living dude drops in at last checkpoint flag. All dead => level FAILED.
- Power-up persists until that dude dies (Contra). Same letter again => MEGA version.

### The team (silly)
| id | name | look | gun | special | voice |
|---|---|---|---|---|---|
| sgt | Sgt. Doosh | red limbs, huge blond pompadour, aviators, headband "DOOSH" | shotgun DOOSH | Doosh Grenade | deep action hero |
| pete | Pew Pew Pete | tiny, GIANT cowboy hat, handlebar mustache | dual pistols PEW PEW | Pew Storm (8-way volley) | squeaky cowboy |
| brenda | Brenda Brrrt | purple, balloon biceps, pink mohawk, eye-black | minigun BRRBRBRR (spin-up) | Ground Pound THOOM | loud gym coach |
| major | Major Shhh | British, fishbowl helmet, monocle INSIDE the bowl, moustache | rocket launcher SHHHH | Airstrike (3 missiles from sky) | posh British |
| gramps | Grandpappy Fwoosh | grey, beard to knees, nightcap, slippers, hunched | flamethrower FWOOOSH | Denture Grenade (chattering teeth hop then explode) | cranky old man |

## 5. Weapons + power-ups
Weapon ids (SGS.Weapons): `pistol dual shotgun mg rocket flame laser spread` (+MEGA variants by `lvl:2`).
Pickups (comic star badge with letter, float out of crates / flying capsules / dropped by officers):
`S` spread, `M` machine gun, `D` DOOSH shotgun, `R` rockets (homing at MEGA), `F` flame, `L` laser,
`B` barrier (10 s invincible bubble), `⚡` rapid (x1.6 rate, until death), `+` heal, `$` gold bag,
`1UP` frees a fallen dude. Specials refill: `ammo` capsule.

## 6. Levels + themes (MMX select)
12 levels. Select screen = 3x4 grid of comic panels (boss mugshot + name). FORTRESS locked until 11 beaten.
Each level: seeded (fixed seed per theme => same layout every time), ~3-5 minutes, wide AND tall
(multi-level: towers, shafts, caves, bunkers), checkpoint flags (raise = respawn point), 2-4 caged prisoners,
crates, explosive barrels, hidden gold bars, theme hazards, boss arena at the end, then
"GET TO THE CHOPPA": helicopter ladder drops after the boss dies => grab it => CLEAR.

| theme id | name | boss | hazard / physics | super granted | boss weak to |
|---|---|---|---|---|---|
| ice | Brrr-zerker Glacier | Frosty McChillface (yeti on snowmobile, tiny scarf) | slippery ice, falling icicles, snow drifts | Freeze Grenade (enemies -> ice blocks) | napalm (fire) |
| fire | Mount Ka-Blammo | Captain Combustion (fireman who is ON FIRE) | lava pools, fire jets, ash | Napalm Strike (ground fire line) | tidal (water) |
| wind | Gustbuster Skyway | Gustav Blowhard (huge lungs, leaf blower, cloud) | gusts push sideways, floating platforms, windmills | Tornado (sucks + flings) | boulder (mountain) |
| water | Soggy Bottom Docks | Admiral Soggybottom (pirate in a bathtub) | water: swim (slow, floaty), rising tide | Tidal Wave | gravity (moon) |
| mud | Sludge Bog | Sir Sludgington (mud golem, monocle, top hat) | mud = slow, quicksand sink | Mud Bomb (slow + mud platform) | tornado (wind) |
| jungle | Bananarama Temple | Chimpanzilla (giant stick gorilla, tank top) | vines (climb), spike traps, rolling logs | Banana Boomerang | mudbomb (mud) |
| mountain | Mount Doosh-more | Billy the Kidd (goat king with jetpack) | tall vertical climb, rockslides | Boulder (rolls, breaks terrain) | cow (plains) |
| plains | Cornfed Plains | Colonel Cornhusk (scarecrow on a combine harvester) | barns, silos, cow stampede, UFO cows | Cow Launcher (MOOO -> KA-MOO) | freeze (ice) |
| fantasy | Castle Wizzlebeard | Wizard Wizzlebeard (absurd beard, tiny dragon) | castle, drawbridges, skeletons | Magic Missiles (3 homing) | banana (jungle) |
| moon | Moon Base Bonkers | Emperor Zorp (alien in tiny UFO w/ mech arms) | gravity 0.35 (ragdolls float away), craters | Gravity Bomb (enemies float off) | pixel (retro) |
| retro | 8-Bit Bonanza | GL1TCH.EXE (giant pixel stick man) | pixelated render, chiptune-metal, "PRESS START" gags | Pixel Bomb (enemies go 8-bit then shatter) | magic (fantasy) |
| fortress | DOOSH FORTRESS | General Doom-Doosh (evil goatee twin) in the DOOSHINATOR mech | everything | — | the shotgun (DOOSH) |

Weakness chain is one 11-loop: ice<fire<water<moon<retro<fantasy<jungle<mud<wind<mountain<plains<ice
(read `a<b` as "a is weak to b's super"). Weak hit = x4 damage + stagger + big `WEAK!` word.

## 7. Enemies (few HP; ~1-4 shots)
Killability rule (2026-11-16, user: "some enemies seem indestructible ... keep gameplay fast"): regular enemies are
1-2 HP; every enemy dies within ~1.2 s of sustained fire from any default gun; hurtbox >= 26 px tall (chest-high
shots must hit); flyers swoop into range; verified by `node tools/ttktest.js` (matrix + 12-theme sweep).
Base roster (re-skinned per theme with hats/colors): grunt (2 hp pistol, `HUH?!` on alert), shotgunner (2),
gunner (2, MG bursts), rocketeer (2, telegraphed SHHHH rockets), grenadier (2, lobs), shield (1 hp + 3 chip points
of shield: frontal bullets crack it, 3rd hit breaks it (CRACK!); explosives/melee/lasers/back hit the body, says
`NOPE`), dog (1, fast), jetpack (2, drops bombs, swoops), brute (6, minigun, slow, big gold, hp pips), turret (3, MG nest),
sniper (2, laser sight telegraph), officer (2, blows whistle => reinforcements, drops power-up), skeleton (1,
bone pile reassembles ONCE after 1.8 s unless hit), barrel-roller (pushes explosive barrels).
Theme extras: ice snowman/penguin-slider, fire imp/magma blob, wind kite-goon/fan turret, water scuba/piranha,
mud mud-man/gator, jungle monkey (coconuts)/snake, mountain goat/rock thrower, plains angry cow/crows,
fantasy skeleton knight/apprentice, moon little green alien/bouncer, retro 8-bit goon/pixel ghost.
Enemies telegraph every shot (~0.35-0.6 s wind-up flash) so deaths feel fair. Alert bubbles are comic.

## 8. Bosses
Each: own arena, intro (comic VS splash + taunt line), 3-4 attack patterns, 2 phases (enrage at 50%), HP bar,
boss music, weakness, death sequence. Bosses ARE sponges (~45-75 s with default guns; ~20 s with weakness).
**FF6 death**: (1) FLASH-CRASH x2: boss flashes white + screen pulse + crash sfx (respect Reduce Flashing:
then use a slow red tint pulse instead); (2) BURN BURN: boss tinted red/orange, explosions popping all over its
body one after another, top-to-bottom scanline dissolve (FF6 boss dissolve), sparks; (3) EXPLODE: giant comic
burst `KA-DOOOOSH!!!`, hit-stop + slow-mo 0.6 s, giblets/bolts, gold rain, then the chopper arrives.

## 9. Economy + shop (permanent, localStorage)
Gold from enemies (3-8), crates (10-30), gold bars (50), rescues (25), boss (400 + 150 per boss already beaten),
level clear (200 + time bonus). Later levels pay more: x(1 + 0.25 * bossesBeaten). Failed level keeps 50%.
Price(level n) = round5(base * growth^n). Tiers: Common g1.55 (base 25-150), Rare g1.7 (300-1200),
Epic g1.8 (1800-6000), Legendary (one level, 9k-50k, unlocked by beating a specific boss).
Shop opens automatically after every level (then level select). Catalog + stat keys: see §13 `Shop.stats()`.

## 10. Settings
- Controls: Keyboard (rebind 2 slots/action), Controller (rebind, dead zone, vibration), Touch (size, opacity,
  left-handed, floating/fixed stick), Lock mouse to window.
- Video: Screen shake Full/Minimal/Off, Reduce flashing, Gore Off/Giblets/MAXIMUM GIBLETS, Comic word size,
  Quality Auto/High/Low, Show FPS.
- Audio: Master, Music, SFX, Voices volumes; Play audio in background (default off => mute when tab hidden);
  Cursing Bleeped/Uncensored; Commentary Off/Some/Constant; Speech bubbles on/off.
- Gameplay: Difficulty Baby Doosh / Doosh / ULTRA DOOSH; hold-to-autofire.
- Cheats: code entry box (works on phones). Title-screen code: Up Up Down Down Left Right Left Right B A
  (keyboard or pad) => INFINITE LIVES. Text codes: `DOOSHFOREVER` (inf lives), `BIGHEADS`, `MOONWALK`
  (moon gravity everywhere), `GIBLETS` (max gore), `PEWPEWPEW` (everyone gets dual pistols lol).

## 11. Audio
- Buses: master > music / sfx / voice. Unknown sfx names fall back to procedural WebAudio synth (always works).
- Music track ids (15): `title select ice fire wind water mud jungle mountain plains fantasy moon retro boss final`.
  Fortress stage plays `title`; every boss fight plays `boss`; the final boss plays `final`. Shop uses `select`.
  Streamed via `<audio>` -> MediaElementSource, lazy-loaded per screen; procedural metal fallback until loaded.
- Voices: lines per speaker per event (see voice.js). Curse words are separate TTS segments so the manifest knows
  their time ranges; bleep mode mutes the voice there and plays a 1 kHz beep.

## 12. Architecture (files) + OWNERSHIP
Namespace `window.SGS` (series convention). Classic scripts, load order = index.html order.
**Rule: no DOM/canvas access at load time** (only inside init/draw functions) so every module loads in Node
with a tiny `window` stub for tests. Never use ES modules. 2-space indent, semicolons, `'use strict'` per file
inside an IIFE: `(function(){ 'use strict'; const S = window.SGS; ... })();`

| file | owner | contents |
|---|---|---|
| index.html, css/style.css (base) | core | canvas, DOM roots, script tags with `?v=N` |
| js/util.js | core | `SGS.U` math, rng |
| js/config.js | core | `SGS.C` tunables |
| js/save.js | core | `SGS.Save` profile + settings defaults |
| js/input.js | core | `SGS.Input` keyboard/mouse/pad/touch, rebinding, pointer lock, touch overlay draw |
| js/comic.js | core | `SGS.Comic` words, streams, trails, bubbles, bursts, halftone patterns |
| js/fx.js | core | `SGS.FX` particles, giblets, shake, flash, hitstop |
| js/terrain.js | core | `SGS.Terrain` grid, materials, damage, explode, raycast, chunk render; `SGS.Phys` |
| js/rig.js | core (+cast adds props) | `SGS.Rig` stick figure renderer, poses, `Rig.PROPS` registry |
| js/weapons.js | core | `SGS.Weapons` defs, `SGS.Shots` projectiles |
| js/entities.js | core | pickups, crates, barrels, cages, flags, chopper, gold |
| js/player.js | core | `SGS.Player` controller |
| js/game.js | core | `SGS.Game` level session, camera, spawning, damage routing, state machine |
| js/render.js | core | `SGS.Render` world drawing, retro filter |
| js/hud.js | core | `SGS.HUD` |
| js/main.js | core | `SGS.Main` loop, resize, adaptive quality, device detection, boot, URL flags |
| js/audio.js, js/music.js, js/voice.js | audio | `SGS.Audio`, `SGS.Music`, `SGS.Voice`; tools/tts/* |
| js/ui.js, js/shop.js, css/ui.css | ui | DOM screens, settings, select, shop catalog |
| js/themes.js, js/backdrops.js, js/levelgen.js | levels | `SGS.Themes`, `SGS.Backdrops`, `SGS.LevelGen` |
| js/dudes.js, js/props.js | cast | `SGS.Dudes`, extra `Rig.PROPS` |
| js/enemies.js | cast | `SGS.Enemies`, `SGS.EnemyDefs` (core ships a minimal grunt; cast replaces) |
| js/bosses.js, js/supers.js | bosses | `SGS.BossDefs`, `SGS.Bosses`, `SGS.Supers` |

Only edit files you own. If you need a hook in someone else's file, use Edit (never Write/overwrite) for a
tiny, clearly commented change, and mention it in your final report.

## 13. API contract (all world coords in px; entity `x` = center, `y` = FEET (bottom))
```
SGS.U: clamp(v,a,b) lerp(a,b,t) rand(a,b) randi(a,b) pick(arr) chance(p) sign(v) approach(v,target,step)
       dist(ax,ay,bx,by) TAU  rng(seed)->{next(),range(a,b),int(a,b),pick(arr),chance(p)}  easeOutBack(t) easeOutCubic(t)
SGS.C: T=20 (tile px), VIEW_H=450 (logical view height; width follows aspect, clamped 640..1000), GRAV=1500,
       MAX_FALL=900, RUN=215, JUMP=-500, CLIMB=170, PARTICLES_DESK=900, PARTICLES_MOBILE=320
SGS.Save: data{v,gold,upgrades{id:lvl},beaten{themeId:true},best{themeId:sec},cheats{infLives,bigHeads,moon,gore,pew},
       stats{kills,deaths,gold,rescues},settings{...}}, settings (alias), load(), save(), reset(), defaults()
  settings = { audio:{master:.8,music:.7,sfx:.9,voice:.9,background:false,cursing:'bleep'|'raw',chatter:'some'|'off'|'lots',bubbles:true},
               video:{shake:'full'|'min'|'off',reduceFlash:false,gore:'on'|'off'|'max',wordSize:1,quality:'auto'|'high'|'low',fps:false},
               input:{mouseLock:true,keys:{action:[code,code]},pad:{action:[btn,btn]},deadzone:.25,vibrate:true,
                      touch:{size:1,opacity:.55,leftHanded:false,stick:'floating'|'fixed'}},
               game:{difficulty:'baby'|'normal'|'ultra',autofire:true} }
SGS.Input: init(canvas) update() endFrame() down(a) pressed(a) released(a) axisX() device('kb'|'pad'|'touch')
       touchOn  drawTouch(ctx,W,H)  defaults{keys,pad}  bindKey(action,slot,code) bindPad(action,slot,btn)
       captureKey(cb) capturePad(cb)  lockMouse(on)  vibrate(ms,strength)  onCheatSeq(cb)  keyName(code) padName(btn)
SGS.Audio: init() unlock() sfx(name,{vol,pitch,x}) loop(name,key,{vol})/stopLoop(key) setVolumes() beep(dur)  ctx  bus{master,music,sfx,voice}
SGS.Music: play(id,{fade}) stop(fade) duck(amt,sec) current
SGS.Voice: say(speaker,event,{x,y,follow,force}) line(speaker,text) update(dt)   speakers: sgt pete brenda major gramps goon boss_<theme> announcer
SGS.Comic: word(text,x,y,{size,color,stroke,angle,life,vy,burst,burstColor,pop}) stream(key,text,x,y,{...}) endStream(key)
       trail(shot)  bubble(text,x,y,{follow,life,speaker})  update(dt) draw(ctx,cam)  pattern(ctx,color,dot,gap)
       burst(ctx,x,y,r1,r2,n,seed)  font(size)
SGS.FX: spark(x,y,n,color) smoke(x,y,n) dust(x,y,n) explosion(x,y,r) gibs(ent,look,dirX) blood(x,y,dx) confetti(x,y,n)
       shell(x,y,dir) shake(amt) flash(color,sec) hitstop(sec) slowmo(scale,sec) update(dt) draw(ctx,cam) drawTop(ctx,W,H)
SGS.Terrain: MAT{EMPTY:0,DIRT:1,ROCK:2,STEEL:3,WOOD:4,PLAT:5,LADDER:6,SPIKES:7,ICE:8,BEDROCK:9,LAVA:10,WATER:11,MUD:12,
       SAND:13,CRATE:14,GLASS:15}  PROPS[m]{solid,oneway,climb,hp,liquid,hazard,slippery,slow,burn,dmgMul}
       load(level) get(tx,ty) set(tx,ty,m) solid(tx,ty) solidPx(x,y) damageTile(tx,ty,dmg,src) explode(x,y,r,dmg)
       raycast(x0,y0,x1,y1)->{x,y,tx,ty}|null  draw(ctx,cam)  W H (tiles)  onBreak(cb)
SGS.Phys: move(e,dt)  // e{x,y,w,h,vx,vy,grav=1,onGround,wall(-1/0/1),inLiquid,liquid,drop,slippery,noTerrain}
SGS.Rig: draw(ctx,x,y,st)  joints(st)->{hip,neck,head{x,y,r},handF,handB,elbowF,elbowB,kneeF,kneeB,footF,footB,muzzle}
       st = {facing:1|-1, pose:'idle'|'run'|'jump'|'fall'|'climb'|'wall'|'hurt'|'melee'|'crouch'|'swim'|'dead',
             t, aim:'fwd'|'up'|'down', recoil:0..1, look, gun:'pistol'|..., flash(0..1 white), tint}
       look = {limb:'#hex', head:'#fff', ink:'#141018', scale:1, headR:7, thick:3.2, body:'stick'|'muscle'|'tiny'|'fat'|'hunch',
               face:'grin'|'angry'|'scared'|'old'|'derp', props:[...names]}   PROPS[name]=fn(ctx,J,look,st)
       GUNS[id]=fn(ctx,J,st) draws the held gun
SGS.Weapons: [id]={id,name,word,wordSize,color,rate,auto,dmg,speed,life,count,spread,kind:'bullet'|'pellet'|'rocket'|'flame'|'laser'|'grenade',
       tileDmg,blast,blastDmg,recoil,shake,sfx,homing,spin}   fire(owner,id,lvl)   // owner has x,y,facing,aim,team
SGS.Shots: list, add(s), update(dt), draw(ctx)  // s{x,y,vx,vy,team,dmg,kind,life,owner,blast,tileDmg,grav,homing,word,...}
SGS.Game: start(levelId,opts) state('intro'|'play'|'boss'|'bossdeath'|'chopper'|'clear'|'fail') level theme player team[] ents[]
       cam{x,y,w,h} time gold kills rescues  spawn(e) spawnEnemy(id,x,y,opts) damage(target,dmg,src) explode(x,y,r,dmg,team,opts)
       hurtArea(x,y,r,dmg,team,src) nearestEnemy(x,y,team,range) addGold(n,x,y) checkpoint{x,y} onBossDead(boss)
       pause() resume() quit()   difficulty{dmgMul,enemyRate,hpBonus}  isPlayerTeam(e)
       // entities: {kind:'enemy'|'boss'|'pickup'|'prop'|'npc', team:'player'|'enemy'|'neutral', x,y,w,h,vx,vy,hp,maxHp,dead,
       //            update(dt), draw(ctx), hurt(dmg,src,info)->bool, onDeath()}  info{dirX,kind,superId,blast}
SGS.Enemies: make(id,x,y,opts)->entity   SGS.EnemyDefs[id]   // core ships grunt; cast agent supplies full roster
SGS.Bosses: make(themeId,x,y)->entity  deathSequence(boss)  SGS.BossDefs[themeId]{name,title,hp,weakTo,super,music,arena{w,h},intro}
SGS.Supers: [id]{name,themeId,icon,color,ammoCost,use(owner)}  ids: freeze napalm tornado tidal mudbomb banana boulder cow magic gravity pixel
SGS.Dudes: [id]{name,look,gun,special,voice,speed,jump,blurb}  order ['sgt','pete','brenda','major','gramps']
       SGS.Specials[id]{name,icon,use(owner)}  ids: dooshnade pewstorm groundpound airstrike dentures
SGS.Themes[id]{id,name,boss,music,sky:[top,bot],ink,mats{matId:{base,dark,light,top,pattern}},gravity,wind,
       enemies{id:weight},extras[],ambient:'snow'|'ash'|'leaves'|'bubbles'|'dust'|'stars'|'pixels'|null,retro:bool,water:level?}
SGS.Backdrops[id](ctx,cam,t,W,H)  // parallax far layers; cache to offscreen canvases, never repaint per frame
SGS.LevelGen.build(themeId,seed,diff)->{w,h,tiles:Uint8Array,spawn{x,y},ents:[{type,id,x,y,...}],
       arena{x0,y0,x1,y1,bossX,bossY},flags:[{x,y}],water:?}
       ent types: 'enemy'(id) 'crate'(loot) 'barrel' 'cage' 'flag' 'pickup'(id) 'goldbar' 'hazard'(id) 'ladderTop'
SGS.Shop: items[] price(id) canBuy(id) buy(id) level(id) stats()->{maxHp,armor,regen,extraLives,secondWind,dmgMul,rateMul,
       specials,blastMul,crit,ricochet,superAmmo,speedMul,jumpMul,doubleJump,climbMul,airDash,stomp,magnet,goldMul,luck,
       discount,partyHats,bay,bigHeads,kazoo,loudWords,keepPowerup,startPowerup,megaPickups,frostRounds,burnRounds,hover,
       sharkDrone,dmgReduce,bananaMines,charge,cowBuddy,dragonShells,moonBoots,extraDude,bigDoosh,goldenGun}
SGS.UI: init() show(id) hide(id) toast(msg) onLevelClear(result) onLevelFail(result) onPause() onBossIntro(def,cb)
       result = {theme,time,kills,gold,rescues,bossBeaten:bool,newSuper,firstClear}
SGS.HUD: draw(ctx,W,H)
SGS.Main: mode('menu'|'play'|'pause') W H scale dpr device{touch,mobile,low} flags{} step(dt) render()
```

## 14. Performance
60 fps cap, dpr cap 1.5 desktop / 1.25 touch, adaptive resolution on frame-time EMA, no `shadowBlur`, terrain
drawn from cached chunk canvases (16x16 tiles) re-rendered only when dirty (<=4/frame), enemies only update
within camera + 2 screens, particle caps (C), comic words cap 40 (20 mobile), text drawn with cached sprites
where repeated. Audio lazy-loaded; total first load target < 3 MB.

## 15. Debug URL flags
`?level=<theme>` straight into a level, `?boss=1` start at the boss arena, `?god=1`, `?gold=N`, `?beatall=1`,
`?touch=1` force touch UI, `?seed=N`, `?dude=<id>`, `?weapon=<id>`, `?fps=1`, `?nomusic=1`.
Testing (browser pane is usually hidden => rAF paused): `SGS.Main.mode='pause'`, loop `SGS.Main.step(1/120)`,
then `SGS.Main.render()` and screenshot (screenshots lag one capture; take two).

## 16. Tooling quirks on this machine
Bash heredocs > ~7 KB fail: use the Write tool for files. Git in this folder needs
`GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0='G:/Claude - Sprite Space Shooter/StickDoosh'`.
Dev server: launch.json `doosh` (port 8146). ComfyUI at http://127.0.0.1:8188 (Stable Audio 3 Medium, MiniMax
music, Z-Image Turbo, Flux 2 Klein, Qwen Image). ComfyUI python: `C:\Users\nicho\Documents\ComfyUI\.venv\Scripts\python.exe`.
