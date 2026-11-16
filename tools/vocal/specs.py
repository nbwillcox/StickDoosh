"""Stick Doosh VOCAL WEAPON SFX: the catalogue (pure data, no heavy imports).

Every game sfx name below is "mouth-made": a human voice (Kokoro TTS, tools/.venv) or a hand-built mouth noise
(lip trill, shhh breath, raspy fwoosh ... synthesised in tools/vocal/make_raw.py) or a Stable Audio 3 attempt.

Take source kinds:
  tts(...)  Kokoro voice says a word (text or IPA phonemes), pitched by resampling, then `post` DSP ops.
  syn(...)  numpy mouth-noise synth (see make_raw.py kinds).
  ai(...)   ComfyUI Stable Audio 3 Medium generation (local), cropped to a window.
post ops (vlib.apply_post): ('drive',k) ('lp',hz) ('hp',hz) ('bp',lo,hi) ('low',hz,dB) ('high',hz,dB) ('pitch',r)
  ('glide',r0,r1) ('vib',hz,depth) ('spring',depth,hz,decay) ('sub',f0,f1,dur,dB,offset) ('thump',f0,f1,dur,dB)
  ('rumble',dur,dB,offset) ('blast',dur,dB,lo,hi) ('gain',dB) ('echo',sec,amt) ('wet',depth) ('fall',r0,r1)
"""

# group, voice label, spoken word, min/max seconds, loudness class ('v' voice -16 LUFS-ish, 'L' loud -13)
NAMES = {}
ORDER = []


def tts(id, voice, text, speed=1.0, pitch=1.0, post=(), ph=None, note=''):
    return dict(id=id, src='tts', voice=voice, text=text, ph=ph, speed=speed, pitch=pitch, post=list(post), note=note)


def syn(id, kind, post=(), note='', **kw):
    return dict(id=id, src='synth', kind=kind, params=kw, post=list(post), note=note)


def ai(id, key, idx, crop=None, post=(), note=''):
    return dict(id=id, src='ai', key=key, idx=idx, crop=crop, post=list(post), note=note)


def add(name, grp, voice, word, lo, hi, takes, loud='v', loop=False, variant_of=None, default=None, f0=None, desc='', kid=None):
    NAMES[name] = dict(grp=grp, voice=voice, word=word, lo=lo, hi=hi, takes=list(takes), loud=loud, loop=loop,
                       variant_of=variant_of, default=default, f0=f0, desc=desc, kid=kid)
    ORDER.append(name)


# ------------------------------------------------------------------ AI (Stable Audio 3) generation batches
AI_JOBS = {
    'shh': dict(prompt='a man makes a long steady shhhhhh sound with his mouth, breath hiss, mouth sound effect, no music',
                seconds=3.0, batch=3, seed=1101),
    'brr': dict(prompt='a man blows a rapid lip trill brrrrrrr with his lips, motorboat raspberry, mouth sound effect, no music',
                seconds=3.0, batch=3, seed=2202),
    'fwoosh': dict(prompt='a man makes a raspy fwooooosh whoosh blowing sound with his mouth, breathy, mouth sound effect, no music',
                   seconds=2.0, batch=3, seed=3303),
    'kid': dict(prompt='a little kid making machine gun sounds with his mouth, dadadadada, playful, dry, fast, no music',
                seconds=3.0, batch=4, seed=5505),
    'kid2': dict(prompt='a child makes tk tk tk tk tk machine gun noises with his mouth, whispered spit bursts, fast, playful, no music',
                 seconds=3.0, batch=3, seed=6606),
    'bzzt': dict(prompt='a woman makes a bzzzzt zapping buzz sound with her mouth, laser, mouth sound effect, no music',
                 seconds=1.5, batch=2, seed=4404),
}
AI_NEG = 'music, singing, drums, speech, reverb, guitar, melody'

F, M, L_ = 'female', 'average male', 'LOW male'

# ------------------------------------------------------------------ WEAPONS
add('pistol', 'weapon', F, 'pew', 0.12, 0.40, [
    tts('pew1', 'af_bella', 'pew!', 1.3, 1.12, [('hp', 180), ('high', 3000, 3)]),
    tts('pew2', 'af_sky', 'pyew!', 1.35, 1.15, [('hp', 180), ('high', 3000, 3)]),
    tts('pew3', 'af_nicole', 'peow!', 1.25, 1.1, [('hp', 180), ('high', 3000, 3)]),
    tts('pew4', 'af_heart', 'pew', 1.4, 1.18, [('hp', 180), ('high', 3000, 3)], ph='pjˈuː'),
], f0=('min', 160), desc='single pistol shot (dual pistols use it too: weapons.js d.sfx = pistol)')
add('dual', 'weapon', F, 'pew pew', 0.25, 0.60, [
    tts('pp1', 'af_bella', 'pew pew!', 1.5, 1.1, [('hp', 180), ('high', 3000, 3)]),
    tts('pp2', 'af_nicole', 'pew, pew!', 1.45, 1.1, [('hp', 180), ('high', 3000, 3)]),
    tts('pp3', 'af_sky', 'pyew pyew!', 1.5, 1.12, [('hp', 180), ('high', 3000, 3)]),
], f0=('min', 160), desc='optional alternate for dual pistols (game does not call it yet: sfx(\'dual\'))')
add('spread', 'weapon', F, 'pew pew pew', 0.35, 0.80, [
    tts('ppp1', 'af_bella', 'pew pew pew!', 1.6, 1.1, [('hp', 180), ('high', 3000, 3)]),
    tts('ppp2', 'af_sky', 'pew-pew-pew!', 1.6, 1.12, [('hp', 180), ('high', 3000, 3)]),
    tts('ppp3', 'af_heart', 'pyew pyew pyew!', 1.6, 1.1, [('hp', 180), ('high', 3000, 3)]),
], f0=('min', 160), desc='spread gun (S pickup) + Pew Storm special')
add('shotgun', 'weapon', L_, 'DOOSH', 0.45, 0.90, [
    tts('doosh1', 'am_onyx', 'doosh!', 0.75, 0.82, [('drive', 2.2), ('low', 180, 5), ('thump', 90, 45, 0.14, -8)]),
    tts('doosh2', 'am_onyx', 'doosh', 0.6, 0.78, [('drive', 2.4), ('low', 160, 6), ('thump', 80, 40, 0.16, -8)], ph='dˈuːʃ'),
    tts('doosh3', 'am_onyx', 'dooosh!', 0.7, 0.85, [('drive', 2.0), ('low', 180, 5), ('blast', 0.12, -14, 300, 3000)]),
    tts('doosh4', 'am_onyx', 'doo-osh!', 0.65, 0.8, [('drive', 2.6), ('low', 200, 6), ('thump', 70, 38, 0.18, -7), ('blast', 0.1, -15, 400, 3500)]),
], loud='L', f0=('max', 130), desc='shotgun / DOOSH (also boss doosh volleys)')
# --- MG v2: a KID making machine-gun noises (the first "brr" lip-trill takes sounded like a frog: kept as brr*/kk1/ai*, now fail the checks)
# kid = fast, dry, percussive, mid-high, airy plosive bursts (da/ka/tk/pa), 11-16 hits/s in loops, one 1-3 hit burst per shot.
add('mg', 'weapon', M, 'tk / da / ka (kid mouth machine gun)', 0.09, 0.19, [
    syn('ksyn1', 'mg_shot', f0=280, cf=2200, voiced=0.5, hits=1, dur=0.14, note='dry da-ish, voiced under'),
    syn('ksyn2', 'mg_shot', f0=320, cf=2700, voiced=0.35, hits=1, dur=0.13, note='brighter ka-ish'),
    syn('ksyn3', 'mg_shot', f0=250, cf=1900, voiced=0.5, hits=2, gap=0.058, dur=0.17, note='da-ka double tap'),
    syn('ksyn4', 'mg_shot', f0=360, cf=2900, voiced=0.08, tau_n=0.024, hits=1, dur=0.13, note='whispery tk, high'),
    syn('ksyn5', 'mg_shot', f0=300, cf=3500, voiced=0.0, hits=1, dur=0.16, breath=0.7, note='breathy pchoo puff'),
    tts('kida', 'af_nicole', 'da!', 1.8, 1.3, [('hp', 550), ('high', 2200, 5), ('cut', 0.15)], ph='dˈɑ', note='child-like Kokoro'),
    tts('kika', 'af_sky', 'ka!', 1.8, 1.3, [('hp', 550), ('high', 2200, 5), ('cut', 0.15)], ph='kˈɑ', note='child-like Kokoro'),
    tts('kita', 'am_puck', 'ta!', 1.8, 1.35, [('hp', 550), ('high', 2200, 5), ('cut', 0.15)], ph='tˈɑ', note='child-like Kokoro'),
    tts('kipa', 'af_nicole', 'pa!', 1.8, 1.3, [('hp', 550), ('high', 2200, 5), ('cut', 0.15)], ph='pˈɑ', note='child-like Kokoro'),
    tts('kipc', 'af_sky', 'pchoo!', 1.7, 1.3, [('hp', 550), ('high', 2200, 5), ('cut', 0.15)], ph='pʧˈu', note='child-like Kokoro, puff'),
    ai('kai1', 'kid', 0, crop=('best', 0.1), note='Stable Audio 3, kid prompt'),
    ai('kai2', 'kid', 1, crop=('best', 0.1), note='Stable Audio 3, kid prompt'),
    ai('kai3', 'kid', 2, crop=('best', 0.1), note='Stable Audio 3, kid prompt'),
    ai('kai4', 'kid', 3, crop=('best', 0.1), note='Stable Audio 3, kid prompt'),
    # --- v1 (user: sounds like a FROG): kept for the record
    syn('brr1', 'trill', f0=105, flutter=30, dur=0.15, note='v1 lip trill (frog)'),
    syn('brr2', 'trill', f0=118, flutter=34, dur=0.13, note='v1 lip trill (frog)'),
    syn('brr3', 'trill', f0=96, flutter=27, dur=0.16, note='v1 lip trill (frog)'),
    syn('brr4', 'trill', f0=126, flutter=36, dur=0.12, note='v1 lip trill (frog)'),
    syn('brr5', 'trill', f0=110, flutter=31, dur=0.14, note='v1 lip trill (frog)'),
    tts('kk1', 'am_adam', 'brrr!', 1.6, 1.0, [], note='v1 Kokoro attempt, probably spells it'),
    ai('ai1', 'brr', 0, crop=('best', 0.15), note='v1 Stable Audio 3 lip trill'),
    ai('ai2', 'brr', 1, crop=('best', 0.15), note='v1 Stable Audio 3 lip trill'),
], f0=('min', 150), kid='shot', desc='machine gun, ONE round per call (14/s): kid mouth-gun burst; variants mg2..mg5 give 5 pitches')
for _i, _t in ((2, 'ksyn2'), (3, 'ksyn3'), (4, 'ksyn4'), (5, 'ksyn5')):
    add('mg%d' % _i, 'weapon', M, 'kid mouth gun variant %d' % _i, 0.09, 0.19, [], variant_of='mg', default=_t,
        desc='pitch/timbre variant of mg (core may cycle mg,mg2..mg5 per shot)')
add('mg_loop', 'weapon', M, 'dadadadadadada (kid loop)', 1.0, 1.5, [
    syn('kl1', 'hits_loop', dur=1.2, rate=12.5, f0=300, cf=2200, voiced=0.5, jitter=0.18, note='voiced da-da-da, even-ish'),
    syn('kl2', 'hits_loop', dur=1.2, rate=14.5, f0=330, cf=2800, voiced=0.12, jitter=0.25, note='whispered tk-tk-tk, uneven'),
    syn('kl3', 'hits_loop', dur=1.2, rate=15.0, f0=340, cf=2400, voiced=0.45, jitter=0.2, accent=(1.0, 0.55, 0.55, 0.7), note='ra-ta-ta-ta accents'),
    syn('kl4', 'hits_loop', dur=1.2, rate=11.5, f0=260, cf=1700, voiced=0.65, jitter=0.12, tau_n=0.02, tau_v=0.05, note='dddd tongue flutter, softer'),
    syn('kl5', 'hits_loop', dur=1.2, rate=16.0, f0=310, cf=3300, voiced=0.25, jitter=0.3, note='fast bright ka-ka-ka'),
    tts('kt1', 'af_nicole', 'da-da-da-da-da-da-da-da-da-da-da-da-da-da', 2.3, 1.3, [('hp', 600), ('high', 2200, 4)], ph='dɑ' * 16, note='child-like Kokoro'),
    tts('kt2', 'af_sky', 'ka-ka-ka-ka-ka-ka-ka-ka-ka-ka-ka-ka-ka-ka', 2.3, 1.3, [('hp', 600), ('high', 2200, 4)], ph='kɑ' * 16, note='child-like Kokoro'),
    tts('kt3', 'am_puck', 'ra-ta-ta-ta-ta-ta-ta-ta-ta-ta-ta-ta', 1.9, 1.35, [('hp', 600), ('high', 2200, 4)], ph='ɹɑ' + 'tɑ' * 20, note='child-like Kokoro'),
    tts('kt4', 'af_nicole', 'pa-pa-pa-pa-pa-pa-pa-pa-pa-pa-pa-pa-pa-pa', 2.3, 1.3, [('hp', 600), ('high', 2200, 4)], note='child-like Kokoro, text spelling'),
    ai('lai1', 'kid', 0, crop=('best', 1.2), note='Stable Audio 3, kid prompt'),
    ai('lai2', 'kid', 1, crop=('best', 1.2), note='Stable Audio 3, kid prompt'),
    ai('lai3', 'kid', 2, crop=('best', 1.2), note='Stable Audio 3, kid prompt'),
    ai('lai4', 'kid2', 0, crop=('best', 1.2), note='Stable Audio 3, tk prompt'),
    ai('lai5', 'kid2', 1, crop=('best', 1.2), note='Stable Audio 3, tk prompt'),
    # --- v1 (frog): kept
    syn('lp1', 'trill_loop', f0=108, flutter=30, dur=1.2, pattern=(0.0, 0.28, 0.55, 0.78), note='v1 lip trill loop (frog)'),
    syn('lp2', 'trill_loop', f0=100, flutter=33, dur=1.2, pattern=(0.0, 0.2, 0.5, 0.62, 0.9), note='v1 lip trill loop (frog)'),
    syn('lp3', 'trill_loop', f0=118, flutter=28, dur=1.2, pattern=(0.0, 0.4, 0.7), note='v1 lip trill loop (frog)'),
    ai('ai1', 'brr', 2, crop=('best', 1.2), note='v1 Stable Audio 3 lip trill'),
], loop=True, f0=('min', 150), kid='loop', desc="seamless 1.2 s kid machine-gun loop for Audio.loop('mg_loop',key) while MG fire is held")
add('rocket_launch', 'weapon', M, 'shhhhhhh', 1.0, 1.45, [
    syn('shh1', 'hiss', dur=1.25, c0=2200, c1=4600, shape='rise'),
    syn('shh2', 'hiss', dur=1.3, c0=2000, c1=5200, shape='pass', onset_t=True),
    syn('shh3', 'hiss', dur=1.2, c0=1800, c1=3600, shape='rise', breath=0.35),
    tts('kk1', 'am_adam', 'shhh', 0.5, 0.9, [('glide', 0.85, 1.25), ('hp', 800)], ph='ʃːːːːː', note='Kokoro attempt'),
    ai('ai1', 'shh', 0, crop=('best', 1.25), note='Stable Audio 3'),
    ai('ai2', 'shh', 1, crop=('best', 1.25), note='Stable Audio 3'),
], desc='rocket / missile launch (alias rocket, missile; boss missiles, Airstrike)')
add('rocket_loop', 'weapon', M, 'shhhhhh (loop)', 0.9, 1.45, [
    syn('rl1', 'hiss_loop', dur=1.2, c0=2800, c1=3200),
    syn('rl2', 'hiss_loop', dur=1.2, c0=2300, c1=3800, breath=0.3),
    ai('ai1', 'shh', 2, crop=('best', 1.2), note='Stable Audio 3'),
], loop=True, desc='flying-missile trail loop (the game does not play rocket_loop yet)')
add('flame', 'weapon', M, 'fwooooosh', 0.5, 0.9, [
    syn('fw1', 'fwoosh', dur=0.7, f0=85, rasp=0.55),
    syn('fw2', 'fwoosh', dur=0.72, f0=100, rasp=0.4),
    syn('fw3', 'fwoosh', dur=0.68, f0=75, rasp=0.7),
    tts('kk1', 'am_onyx', 'fwoosh', 0.8, 0.9, [('drive', 1.6), ('wet', 0.5)], ph='fwˈuːʃ', note='Kokoro attempt'),
    ai('ai1', 'fwoosh', 0, crop=('best', 0.7), note='Stable Audio 3'),
    ai('ai2', 'fwoosh', 1, crop=('best', 0.7), note='Stable Audio 3'),
], desc='flamethrower (fires 28x/s: use flame_loop with Audio.loop)')
add('flame_loop', 'weapon', M, 'fwooooosh (loop)', 0.9, 1.45, [
    syn('fl1', 'fwoosh_loop', dur=1.2, f0=85, rasp=0.55),
    syn('fl2', 'fwoosh_loop', dur=1.2, f0=95, rasp=0.45),
    ai('ai1', 'fwoosh', 2, crop=('best', 1.2), note='Stable Audio 3'),
], loop=True, desc='seamless raspy flame loop for Audio.loop(\'flame_loop\',key)')
add('laser', 'weapon', F, 'bzzzzt / pzzew', 0.35, 0.70, [
    syn('bz1', 'bzzt', dur=0.5, fa=430, fb=290, trem=30),
    syn('bz2', 'bzzt', dur=0.5, fa=620, fb=200, trem=0, glide=True),
    tts('pz1', 'af_bella', 'pzew!', 0.7, 1.1, [('glide', 1.25, 0.7), ('high', 2500, 3)], ph='pzjˈuː'),
    tts('pz2', 'af_nicole', 'bzzzt!', 0.7, 1.1, [('glide', 1.1, 0.8), ('drive', 1.5)], ph='bzˈɛt', note='Kokoro attempt'),
    ai('ai1', 'bzzt', 0, crop=('best', 0.5), note='Stable Audio 3'),
], f0=None, desc='laser rifle')
add('grenade_throw', 'weapon', M, 'hup!', 0.10, 0.30, [
    tts('hup1', 'am_adam', 'hup!', 1.3, 1.0, [('hp', 120)]),
    tts('hup2', 'am_michael', 'hup!', 1.35, 0.95, [('hp', 120)]),
    tts('hup3', 'am_eric', 'hyup!', 1.3, 1.0, [('hp', 120)]),
    tts('hup4', 'am_adam', 'hah!', 1.3, 0.95, [('hp', 120)]),
], desc='grenade throw (game plays throw -> alias grenade_throw; boss grenades too)')
add('fuse', 'weapon', M, 'tsss', 0.2, 0.65, [
    syn('tss1', 'tss', dur=0.4),
    syn('tss2', 'tss', dur=0.5, hi=6500),
    syn('tss3', 'tss', dur=0.35, hi=5000),
], desc='fuse sizzle (entities.js plays fuse)')
add('bounce', 'weapon', M, 'boing', 0.18, 0.50, [
    tts('bo1', 'am_adam', 'boing!', 1.4, 1.2, [('spring', 0.25, 11, 4.5)]),
    tts('bo2', 'af_nicole', 'boing!', 1.4, 1.1, [('spring', 0.25, 12, 4.5)]),
    tts('bo3', 'am_michael', 'doing!', 1.4, 1.2, [('spring', 0.3, 10, 4.0)]),
    tts('bo4', 'am_eric', 'bwoing', 1.3, 1.15, [('spring', 0.28, 12, 5.0)], ph='bwˈɔɪŋ'),
], desc='grenade/giblet bounce (quiet, frequent)')
add('boing', 'weapon', M, 'BOOOING', 0.30, 0.85, [
    tts('bg1', 'am_michael', 'boing!', 0.9, 1.0, [('spring', 0.4, 8, 2.8)]),
    tts('bg2', 'am_onyx', 'boooing!', 0.85, 0.95, [('spring', 0.35, 7, 2.5)]),
    tts('bg3', 'af_bella', 'boing!', 0.95, 1.05, [('spring', 0.4, 9, 3.0)]),
], desc='boss hop / jump-pad boing')

# ------------------------------------------------------------------ EXPLOSIONS + IMPACTS
add('explode', 'explosion', M, 'BOOM!', 0.5, 1.05, [
    tts('bm1', 'am_adam', 'boom!', 0.8, 0.85, [('drive', 1.8), ('sub', 70, 32, 0.6, -5, 0.02), ('blast', 0.25, -12, 150, 2500)]),
    tts('bm2', 'am_onyx', 'boom!', 0.8, 0.9, [('drive', 1.8), ('sub', 65, 30, 0.6, -5, 0.02), ('blast', 0.25, -12, 150, 2500)]),
    tts('bm3', 'am_michael', 'kaboom!', 0.85, 0.9, [('drive', 1.6), ('sub', 70, 32, 0.55, -6, 0.12), ('blast', 0.2, -12, 200, 3000)]),
    tts('bm4', 'am_eric', 'bwoom!', 0.8, 0.88, [('drive', 1.8), ('sub', 68, 30, 0.6, -5, 0.04), ('blast', 0.22, -12, 150, 2500)]),
], loud='L', desc='grenade / barrel / rocket explosion (13 call sites)')
add('explode_big', 'explosion', L_, 'KRAKOOOOM', 1.2, 1.85, [
    tts('kr1', 'am_onyx', 'krakoom', 0.55, 0.7, [('drive', 2.0), ('sub', 55, 26, 1.3, -4, 0.2), ('rumble', 1.4, -9, 0.1), ('blast', 0.3, -13, 120, 2200)], ph='kɹɐkˈuːm'),
    tts('kr2', 'am_onyx', 'krakoom!', 0.5, 0.72, [('drive', 2.0), ('sub', 55, 26, 1.3, -4, 0.2), ('rumble', 1.4, -9, 0.1), ('blast', 0.3, -13, 120, 2200)]),
    tts('kr3', 'am_onyx', 'kablam!', 0.5, 0.72, [('drive', 2.2), ('sub', 55, 26, 1.2, -4, 0.25), ('rumble', 1.3, -9, 0.1), ('blast', 0.3, -13, 120, 2200)]),
    tts('kr4', 'am_onyx', 'kaboooom!', 0.45, 0.7, [('drive', 1.8), ('sub', 52, 24, 1.4, -4, 0.3), ('rumble', 1.5, -9, 0.1), ('blast', 0.3, -13, 120, 2200)]),
], loud='L', f0=('max', 130), desc='huge explosion (Sgt. Doosh grenade super etc.)')
add('bigboom', 'explosion', L_, 'KA-DOOOOSH', 1.3, 1.9, [
    tts('kd1', 'am_onyx', 'ka-doooosh!', 0.5, 0.72, [('drive', 2.0), ('sub', 55, 26, 1.4, -4, 0.35), ('rumble', 1.5, -9, 0.1), ('blast', 0.3, -13, 120, 2200)]),
    tts('kd2', 'am_onyx', 'ka dooosh', 0.5, 0.74, [('drive', 2.0), ('sub', 55, 26, 1.4, -4, 0.3), ('rumble', 1.5, -9, 0.1), ('blast', 0.3, -13, 120, 2200)], ph='kɑː dˈuːːːʃ'),
    tts('kd3', 'am_onyx', 'ka-dooooosh!!', 0.45, 0.7, [('drive', 2.2), ('sub', 52, 24, 1.5, -4, 0.4), ('rumble', 1.6, -9, 0.1), ('blast', 0.3, -13, 120, 2200)]),
], loud='L', f0=('max', 130), desc='FF6 boss death finale (game.js plays bigboom): KA-DOOOOSH')
add('crash', 'explosion', M, 'KRASH!', 0.30, 0.75, [
    tts('kc1', 'am_eric', 'krash!', 1.0, 0.9, [('drive', 1.8), ('blast', 0.18, -9, 800, 6000)]),
    tts('kc2', 'am_adam', 'kraaash!', 0.95, 0.9, [('drive', 1.8), ('blast', 0.18, -9, 800, 6000)]),
    tts('kc3', 'am_onyx', 'kraka!', 1.0, 0.85, [('drive', 1.8), ('blast', 0.18, -9, 800, 6000)]),
], loud='L', desc='boss FLASH-CRASH (game.js plays crash)')
add('thoom', 'explosion', L_, 'THOOM', 0.4, 0.95, [
    tts('th1', 'am_onyx', 'thoom!', 0.7, 0.75, [('drive', 1.8), ('sub', 60, 30, 0.5, -5, 0.02)]),
    tts('th2', 'am_onyx', 'thoom', 0.65, 0.72, [('drive', 1.8), ('sub', 58, 28, 0.5, -5, 0.02)], ph='θˈuːm'),
    tts('th3', 'am_onyx', 'thum!', 0.7, 0.78, [('drive', 1.8), ('sub', 62, 30, 0.5, -5, 0.02)]),
], loud='L', f0=('max', 130), desc='ground pound / shockwave (Brenda, bosses)')
add('punch', 'impact', M, 'WHAP!', 0.12, 0.42, [
    tts('wh1', 'am_adam', 'whap!', 1.3, 1.0, [('hp', 100), ('drive', 1.4)]),
    tts('wh2', 'am_michael', 'whap!', 1.3, 0.95, [('hp', 100), ('drive', 1.4)]),
    tts('wh3', 'am_eric', 'wap!', 1.3, 1.0, [('hp', 100), ('drive', 1.4)]),
    tts('wh4', 'am_adam', 'pow!', 1.3, 0.95, [('hp', 100), ('drive', 1.4)]),
], desc='melee hit (alias melee, whap, bonk)')
add('hit', 'impact', M, 'bap! / oof', 0.07, 0.28, [
    tts('bp1', 'am_adam', 'bap!', 1.5, 1.1, [('hp', 120)]),
    tts('bp2', 'am_michael', 'pap!', 1.5, 1.1, [('hp', 120)]),
    tts('bp3', 'am_eric', 'uh!', 1.5, 1.0, [('hp', 120)]),
    tts('bp4', 'am_adam', 'oof!', 1.5, 1.1, [('hp', 120)]),
], desc='bullet hits enemy (frequent: keep it tiny)')
add('hit_metal', 'impact', M, 'BONK!', 0.12, 0.45, [
    tts('bk1', 'am_adam', 'bonk!', 1.3, 1.0, [('hp', 120), ('high', 2500, 2)]),
    tts('bk2', 'am_eric', 'tonk!', 1.3, 1.05, [('hp', 120), ('high', 2500, 2)]),
    tts('bk3', 'am_michael', 'bonk!', 1.3, 0.95, [('hp', 120), ('high', 2500, 2)]),
], desc='shield / metal clang')
add('slam', 'impact', M, 'THWACK!', 0.18, 0.55, [
    tts('tw1', 'am_eric', 'thwack!', 1.1, 0.9, [('drive', 1.6)]),
    tts('tw2', 'am_adam', 'thwack!', 1.1, 0.9, [('drive', 1.6)]),
    tts('tw3', 'am_onyx', 'thwack!', 1.1, 0.9, [('drive', 1.8), ('thump', 80, 45, 0.1, -9)]),
], desc='slam (game.js plays slam)')
add('gib', 'impact', M, 'SPLORT', 0.18, 0.65, [
    tts('sp1', 'am_adam', 'splort!', 1.15, 0.95, [('wet', 0.6)]),
    tts('sp2', 'am_michael', 'splurt!', 1.15, 0.95, [('wet', 0.6)]),
    tts('sp3', 'am_eric', 'splort', 1.1, 0.9, [('wet', 0.7)], ph='splˈɔːɹt'),
], desc='enemy bursts into giblets')
add('splat', 'impact', M, 'SPLAT!', 0.12, 0.55, [
    tts('sl1', 'am_adam', 'splat!', 1.3, 1.0, [('wet', 0.5)]),
    tts('sl2', 'am_eric', 'splat!', 1.25, 0.95, [('wet', 0.5)]),
    tts('sl3', 'am_michael', 'splat!', 1.3, 1.0, [('wet', 0.5)]),
], desc='blood splat')
add('whoosh', 'impact', M, 'fwip', 0.18, 0.55, [
    syn('wo1', 'whoosh', dur=0.3, fa=700, fb=2600),
    syn('wo2', 'whoosh', dur=0.35, fa=900, fb=3200),
    syn('wo3', 'whoosh', dur=0.28, fa=500, fb=2200),
], desc='melee swing / boss charge')

# ------------------------------------------------------------------ BODY + PICKUPS
add('hurt', 'body', M, 'ow!', 0.12, 0.55, [
    tts('ow1', 'am_adam', 'ow!', 1.2, 1.0, [('hp', 100)]),
    tts('ow2', 'am_michael', 'ouch!', 1.2, 1.0, [('hp', 100)]),
    tts('ow3', 'am_eric', 'oof!', 1.2, 1.0, [('hp', 100)]),
    tts('ow4', 'af_bella', 'ow!', 1.2, 1.0, [('hp', 150)]),
], desc='dude takes a hit')
add('die', 'body', M, 'aaaah!', 0.45, 1.15, [
    tts('aa1', 'am_adam', 'aaaah', 0.7, 1.0, [('fall', 1.15, 0.6), ('hp', 100)], ph='ˈɑːːːːː'),
    tts('aa2', 'am_michael', 'aaaah!', 0.7, 1.0, [('fall', 1.1, 0.6), ('hp', 100)]),
    tts('aa3', 'af_bella', 'aaaah!', 0.7, 1.0, [('fall', 1.1, 0.6), ('hp', 150)]),
    tts('aa4', 'am_eric', 'waaaah!', 0.75, 1.0, [('fall', 1.1, 0.65), ('hp', 100)]),
], desc='dude dies')
add('jump', 'body', M, 'hup', 0.08, 0.32, [
    tts('ju1', 'am_adam', 'hup!', 1.5, 1.05, [('hp', 120)]),
    tts('ju2', 'am_michael', 'hoop!', 1.5, 1.05, [('hp', 120)]),
    tts('ju3', 'am_eric', 'hup!', 1.5, 1.0, [('hp', 120)]),
    tts('ju4', 'af_heart', 'hup!', 1.5, 1.05, [('hp', 150)]),
], desc='jump / wall jump / double jump (frequent: tiny)')
add('land', 'body', M, 'oof', 0.08, 0.32, [
    tts('la1', 'am_adam', 'oof!', 1.5, 0.9, [('hp', 100)]),
    tts('la2', 'am_eric', 'uff!', 1.5, 0.9, [('hp', 100)]),
    tts('la3', 'am_michael', 'oomf!', 1.5, 0.9, [('hp', 100)]),
], desc='landing')
add('alert', 'body', M, 'huh?!', 0.15, 0.50, [
    tts('hu1', 'am_adam', 'huh?!', 1.3, 1.0, [('hp', 120)]),
    tts('hu2', 'am_eric', 'hey!', 1.3, 1.0, [('hp', 120)]),
    tts('hu3', 'am_michael', 'huh?', 1.3, 1.0, [('hp', 120)]),
], desc='enemy notices you')
add('pickup', 'pickup', F, 'ding!', 0.18, 0.65, [
    tts('di1', 'af_heart', 'ding!', 1.1, 1.15, [('hp', 200), ('high', 3000, 2)]),
    tts('di2', 'af_bella', 'ding!', 1.1, 1.15, [('hp', 200), ('high', 3000, 2)]),
    tts('di3', 'af_sky', 'ding!', 1.1, 1.15, [('hp', 200), ('high', 3000, 2)]),
], f0=('min', 160), desc='generic pickup')
add('powerup', 'pickup', F, 'yoink!', 0.25, 0.85, [
    tts('yo1', 'af_bella', 'yoink!', 1.0, 1.1, [('hp', 200)]),
    tts('yo2', 'af_nicole', 'yoink!', 1.0, 1.1, [('hp', 200)]),
    tts('yo3', 'af_sky', 'yoink!', 1.0, 1.1, [('hp', 200)], ph='jˈɔɪŋk'),
], f0=('min', 160), desc='power-up / super get / drop-in / cheat')
add('gold', 'pickup', F, 'cha-ching!', 0.22, 0.75, [
    tts('ch1', 'af_bella', 'cha-ching!', 1.3, 1.1, [('hp', 200)]),
    tts('ch2', 'af_nicole', 'cha ching!', 1.3, 1.1, [('hp', 200)]),
    tts('ch3', 'af_heart', 'ching!', 1.2, 1.15, [('hp', 200)]),
    tts('ch4', 'af_sky', 'ka-ching!', 1.3, 1.1, [('hp', 200)]),
], f0=('min', 160), desc='gold coin (alias coin)')

# default take ranking prior: earlier takes win ties (see master.py)
