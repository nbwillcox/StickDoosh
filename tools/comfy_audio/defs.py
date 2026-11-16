"""Prompt definitions for Stick Doosh music + SFX (Stable Audio 3 Medium caption style:
'Genre with instruments ... creating mood. BPM: X. Length: Y seconds')."""
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
RAW = os.path.join(ROOT, 'assets', 'raw_audio')
RAW_MUSIC = os.path.join(RAW, 'music')
RAW_SFX = os.path.join(RAW, 'sfx')
PREV_MUSIC = os.path.join(RAW, 'music_preview')
PREV_SFX = os.path.join(RAW, 'sfx_preview')
OUT_MUSIC = os.path.join(ROOT, 'assets', 'music')
OUT_SFX = os.path.join(ROOT, 'assets', 'sfx')
HERE = os.path.dirname(os.path.abspath(__file__))

MUSIC_SECONDS = 112  # generated length; the loop cut keeps 80-102 s of it
MUSIC_KBPS = 112
SFX_KBPS = 96

# Pipelines compared in the title A/B (both Stable Audio 3 Medium: the only local music model).
PIPELINES = {
    'P1': {'cfg': 1.0, 'steps': 8, 'sampler': 'lcm', 'scheduler': 'simple', 'negative': ''},
    'P2': {'cfg': 1.8, 'steps': 8, 'sampler': 'lcm', 'scheduler': 'simple',
           'negative': 'vocals, singing, voice, speech, lyrics, rap, choir, lo-fi, muffled, quiet, ambient, soft'},
}

_I = 'instrumental with no vocals'
MUSIC = [
    ('title', 140, 'Anthemic 1980s arena heavy metal ' + _I + ', twin distorted electric guitars playing a big '
     'triumphant riff, soaring harmonized guitar leads and a shredding guitar solo, driving bass guitar, pounding '
     'drum kit with double bass drums and huge cymbal crashes, creating heroic, epic, fist-pumping energy'),
    ('select', 112, 'Mid-tempo heavy metal ' + _I + ', chugging palm-muted distorted electric guitar riffs, steady '
     'groovy bass guitar, solid rock drum kit with tight kick and snare, and short melodic guitar lead fills, '
     'creating confident, cool, steady head-nodding energy'),
    ('ice', 180, 'Thrash metal ' + _I + ', opening with an icy clean chorus electric guitar arpeggio then exploding '
     'into fast aggressive palm-muted distorted guitar riffs, galloping bass guitar, rapid double bass drums and '
     'crashing cymbals, creating cold, sharp, frantic energy'),
    ('fire', 92, 'Heavy doom metal ' + _I + ', slow crushing down-tuned distorted guitar riffs, thick rumbling bass '
     'guitar, heavy pounding drums with big cymbal crashes, and a fast blazing shred guitar solo, creating dark, '
     'fiery, powerful energy'),
    ('wind', 200, 'Speed metal ' + _I + ', blazing fast tremolo-picked distorted electric guitar riffs, rapid '
     'galloping bass, relentless double bass drums with fast snare, and screaming whammy bar guitar leads, '
     'creating rushing, windswept, breakneck energy'),
    ('water', 150, 'Pirate shanty folk metal ' + _I + ', galloping distorted electric guitars playing a swashbuckling '
     'sea shanty melody, accordion and fiddle layers, driving bass guitar, pounding drums with double bass, '
     'creating rowdy, swaying, adventurous energy'),
    ('mud', 96, 'Sludgy groove metal ' + _I + ', thick down-tuned fuzzy distorted guitar riffs with a swampy heavy '
     'groove, grinding bass guitar, slow stomping drums with heavy kick and snare, and bluesy guitar bends, '
     'creating dirty, muddy, swaggering energy'),
    ('jungle', 126, 'Tribal heavy metal ' + _I + ', pounding tribal tom drums and jungle percussion, heavy distorted '
     'electric guitar riffs, rumbling bass guitar, driving rock drum kit, and wailing guitar leads, creating '
     'primal, wild, adventurous energy'),
    ('mountain', 160, 'Epic power metal ' + _I + ', soaring harmonized twin electric guitar leads, fast distorted '
     'rhythm guitars, majestic synth strings, driving bass, rapid double bass drums and huge cymbal crashes, '
     'creating heroic, triumphant, climbing energy'),
    ('plains', 132, 'Southern rock boogie metal ' + _I + ', crunchy overdriven electric guitars playing a bluesy '
     'boogie riff, slide guitar licks, driving bass guitar, shuffle rock drums with cowbell, creating rowdy, '
     'sunny, good-time energy'),
    ('fantasy', 156, 'Symphonic power metal ' + _I + ', baroque harpsichord arpeggios, fast distorted electric guitar '
     'riffs, neoclassical shred guitar leads, orchestral strings, driving bass and double bass drums, creating '
     'magical, medieval, epic fantasy energy'),
    ('moon', 120, 'Space rock metal ' + _I + ', heavy distorted electric guitar riffs, spacey analog synth '
     'arpeggios and cosmic synth pads, driving bass guitar, pounding rock drums, and soaring delay-drenched guitar '
     'leads, creating cosmic, floating, sci-fi energy'),
    ('retro', 160, 'Chiptune metal ' + _I + ', 8-bit square wave synth leads and video game arpeggios, heavy '
     'distorted electric guitar power chord riffs, driving bass, fast metal drums with double bass, creating '
     'retro, energetic, video game boss-level energy'),
    ('boss', 190, 'Fast aggressive thrash metal ' + _I + ', frantic palm-muted distorted electric guitar riffs, '
     'urgent pounding double bass drums, fast snare, pulsing bass guitar and a screaming dissonant guitar solo, '
     'creating intense, urgent, dangerous battle energy'),
    ('final', 170, 'Epic final boss heavy metal ' + _I + ', crushing distorted electric guitars, dramatic choir-like '
     'synth pads and pipe organ, orchestral strings, thunderous double bass drums and cymbal crashes, and a '
     'blazing shred guitar solo, creating dark, apocalyptic, climactic energy'),
]
MUSIC_IDS = [m[0] for m in MUSIC]


def music_prompt(tid, seconds=MUSIC_SECONDS):
    for i, bpm, desc in MUSIC:
        if i == tid:
            return '%s. BPM: %d. Length: %d seconds' % (desc, bpm, int(seconds))
    raise KeyError(tid)


# SFX: name -> (prompt text, prompt length s, generated latent s, max kept s, kind)
# kind: 'one' = single event preferred, 'multi' = several transients OK, 'loop' = loopable chunk
SFX = {
    'pistol': ('Single pistol gunshot, sharp punchy crack with a short snappy tail, close-up, dry, action game', 1, 3, 0.5, 'one'),
    'shotgun': ('Single loud shotgun blast, huge booming punchy crack with deep low end and a short tail, close-up, action movie', 1, 3, 0.9, 'one'),
    'mg': ('Single machine gun bullet shot, one short tight punchy gunshot crack, dry, close-up', 1, 3, 0.3, 'one'),
    'rocket_launch': ('Rocket launcher firing, punchy launch thump followed by a hissing whoosh of the rocket flying away', 2, 3, 1.2, 'multi'),
    'flame': ('Flamethrower short burst, roaring whoosh of fire with gas hiss, close-up', 1, 3, 0.9, 'multi'),
    'laser': ('Retro sci-fi laser gun zap, bright descending electric pew with buzzing energy, arcade game', 1, 3, 0.6, 'one'),
    'explode': ('Punchy explosion, short boom with crackling debris and deep bass, action game', 2, 3, 1.3, 'multi'),
    'explode_big': ('Huge massive explosion, deep booming blast with rumbling debris, cinematic', 3, 4, 1.5, 'multi'),
    'grenade_throw': ('Quick whoosh of a small object thrown fast through the air, short swish, close-up', 1, 3, 0.6, 'one'),
    'hit': ('Bullet hitting a body, short meaty punchy thud impact, cartoon game', 1, 3, 0.4, 'one'),
    'hit_metal': ('Bullet ricochet hitting metal, sharp metallic ping clang', 1, 3, 0.6, 'one'),
    'punch': ('Cartoon punch impact, punchy whack with a deep thump, comic fight sound', 1, 3, 0.5, 'one'),
    'tile_break': ('Stone bricks crumbling and breaking, short rocky crunch with small debris falling', 1, 3, 0.8, 'multi'),
    'dirt_break': ('Dirt clod breaking apart, soft crumbly earthy crunch with falling soil', 1, 3, 0.7, 'multi'),
    'glass': ('Glass window shattering, sharp crash with tinkling shards falling', 2, 3, 1.2, 'multi'),
    'cage_break': ('Wooden cage smashed open, loud splintering wood crack with metal bars clanging', 1, 3, 1.0, 'multi'),
    'gold': ('Retro arcade coin pickup sound, bright two-note chime ding, 8-bit style', 1, 3, 0.8, 'multi'),
    'pickup': ('Video game item pickup sound, quick rising bright bleep chime', 1, 3, 0.6, 'multi'),
    'powerup': ('Video game power up sound, fast ascending sparkling synth arpeggio, rewarding', 2, 3, 1.3, 'multi'),
    'boss_crash': ('Heavy metallic crash impact, loud clang with a cymbal-like crash and distorted boom, dramatic hit', 2, 3, 1.3, 'one'),
    'boss_explode': ('Gigantic explosion finale, enormous boom with rolling thunder and debris, cinematic', 3, 4, 1.5, 'multi'),
    'alarm': ('Military base alarm klaxon, loud blaring siren horn, two short blasts', 2, 3, 1.5, 'multi'),
    'whistle': ('Referee whistle blown once, sharp loud shrill whistle blast', 1, 3, 1.0, 'one'),
    'heli': ('Helicopter rotor blades thumping, steady rhythmic chopping while hovering, close-up', 6, 6, 2.0, 'loop'),
    'moo': ('Cow mooing loudly, single funny moo, close-up farm animal', 2, 3, 1.5, 'one'),
    'baa': ('Sheep bleating, single baa, close-up farm animal', 1, 3, 1.2, 'one'),
    'splash': ('Water splash, an object falling into water with a big splash', 1, 3, 1.2, 'multi'),
    'freeze': ('Ice freezing magic spell, crackling crystallizing ice with a sparkling shimmer', 1, 3, 1.2, 'multi'),
}
SFX_IDS = list(SFX.keys())


def sfx_prompt(name):
    p, ln = SFX[name][0], SFX[name][1]
    return '%s. Length: %d second%s' % (p, ln, '' if ln == 1 else 's')
