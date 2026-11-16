"""Stick Doosh art manifest: every image the game loads from assets/art/, its prompt and its sizes.

gen = ComfyUI latent size, out = final webp size, q = webp quality, takes = candidate letters.
The UI crops with object-fit:cover (boss mugshots + shopkeeper circle) or background-size:cover (title),
so subjects are kept CENTERED with breathing room.
"""

STYLE = ("A silly comic book illustration in a stick figure cartoon style: thick black ink outlines, flat saturated "
         "bright colors, Ben-Day halftone dot shading, bold simple shapes, funny ridiculous characters with tiny "
         "stick arms and legs, clean vector look, no photorealism. ")

BG_NOTE = " Fun colorful comic book background with halftone dots and speed lines. The character is centered in the frame."


def boss(prompt, bg):
    return {'kind': 'boss', 'gen': (800, 640), 'out': (640, 512), 'q': 78, 'takes': 'ab',
            'prompt': STYLE + prompt + ' Background: ' + bg + BG_NOTE}


ITEMS = {
    'boss_ice': boss(
        "A huge fluffy white yeti with a goofy angry grin and tiny stick arms and legs, riding a tiny little red "
        "snowmobile that is much too small for him, wearing a tiny red and white striped scarf.",
        "snowy blue mountains, pine trees with snow, icy cyan sky, falling snowflakes."),
    'boss_fire': boss(
        "A cheerful stick figure fireman in a big red fire helmet who is himself completely on fire, flames "
        "roaring off his head and body, giving a calm thumbs up while holding a fire hose.",
        "an erupting orange and red volcano with lava and drifting ash, hot yellow sky."),
    'boss_wind': boss(
        "A skinny stick figure man with an enormous round barrel chest and gigantic lungs, cheeks puffed out, "
        "blowing hard, holding a big green leaf blower, riding on a fluffy white cloud.",
        "bright blue sky with swirling wind lines, flying green and orange leaves, little windmills."),
    'boss_water': boss(
        "A grumpy pirate admiral with a big black tricorn hat, an eyepatch and a bushy beard, sitting in a "
        "bathtub full of soap bubbles, surrounded by yellow rubber ducks.",
        "teal ocean waves, a wooden dock, seagulls and a sunny sky."),
    'boss_mud': boss(
        "A lumpy brown mud golem made of dripping sludge with tiny stick limbs, wearing a black top hat and a "
        "gold monocle, with a smug sophisticated expression.",
        "a murky swamp with bubbling mud puddles, cattails and green brown fog."),
    'boss_jungle': boss(
        "A giant muscular stick figure gorilla wearing a tight tank top, beating his chest with both fists, "
        "big angry grin, a banana in his mouth.",
        "a jungle temple with vines, big green leaves and golden light."),
    'boss_mountain': boss(
        "A royal goat king with big curly horns, a long beard and a small golden crown, wearing a smoking "
        "jetpack on his back and flying through the air.",
        "rocky snowcapped mountain peaks, bright blue sky with puffy clouds."),
    'boss_plains': boss(
        "A stitched-smile scarecrow with a floppy straw hat and tiny stick arms, driving a huge red combine "
        "harvester that is much too big for him.",
        "golden wheat fields, a red barn and a silo, sunny sky with big clouds."),
    'boss_fantasy': boss(
        "An old wizard with an absurdly long fluffy white beard that curls down past his feet, a tall pointy "
        "purple hat with yellow stars, holding a magic staff, a tiny green dragon sitting on his shoulder.",
        "a fairytale castle with towers, purple twilight sky with sparkling stars."),
    'boss_moon': boss(
        "A green alien emperor with huge black eyes and a tiny golden crown, sitting inside a tiny silver "
        "flying saucer UFO that has two big robotic mech arms.",
        "gray moon surface with craters, black starry sky, a blue Earth in the distance."),
    'boss_retro': boss(
        "A giant glitching stick man built entirely out of big chunky square 8-bit pixels in hot magenta and "
        "cyan, with glitch distortion, scanlines and stray pixel fragments.",
        "dark purple retro arcade grid with scattered colorful pixels."),
    'boss_fortress': boss(
        "An evil general with a pointy black goatee, a spiked helmet and a menacing grin, piloting a huge "
        "cartoon battle mech with giant cannons and spikes, red and dark steel.",
        "a dark fortress with searchlights, red stormy sky and smoke."),
    'title': {
        'kind': 'title', 'gen': (1280, 720), 'out': (1280, 720), 'q': 76, 'takes': 'abcdef',
        'prompt': STYLE + "Wide action scene: five silly stick figure soldiers charging toward the viewer in a "
        "line across the lower half of the image, guns blazing. From left to right: a grey old grandpa with a "
        "knee-length white beard and a nightcap holding a flamethrower; a tiny cowboy with a gigantic cowboy "
        "hat holding two pistols; a stick figure with red arms and legs, a huge blond pompadour and aviator "
        "sunglasses holding a shotgun; a muscular purple stick figure with huge balloon biceps and a pink "
        "mohawk holding a minigun; a British officer wearing a fishbowl helmet with a monocle and moustache "
        "holding a rocket launcher. Behind them: big orange explosions, flames, flying debris and jagged comic "
        "burst shapes. The upper third of the image is calm and mostly empty: a bright yellow and orange "
        "sunburst sky with halftone dots."},
    'shopkeeper': {
        'kind': 'shop', 'gen': (768, 768), 'out': (384, 384), 'q': 80, 'takes': 'ab',
        'prompt': STYLE + "Close-up portrait of a funny stick figure shopkeeper standing behind a wooden shop "
        "counter, an enormous grin full of shiny gold teeth, wearing a striped apron and a ridiculous tall "
        "stack of five different hats on his head, tiny stick arms resting on the counter. Behind him are "
        "shelves with crates and gold coins. Background: bright pink halftone dots. The face is exactly in "
        "the center of the frame."},
}


# ---- dude portraits (results screen + How To Play roster): bust of each playable bro, centered, 512x512 ---------
def dude(prompt, bg):
    return {'kind': 'shop', 'gen': (768, 768), 'out': (512, 512), 'q': 78, 'takes': 'ab',
            'prompt': STYLE + "Close-up bust portrait of a funny stick figure hero, round white head, " + prompt +
            " Background: " + bg + " The face is exactly in the center of the frame."}


ITEMS.update({
    'dude_sgt': dude("a tall red-and-black pompadour hairdo, cool aviator sunglasses, a blue headband with the word "
                     "DOOSH, a confident cocky grin, red stick body.", "bright yellow halftone dots."),
    'dude_pete': dude("a huge oversized brown cowboy hat, a curly handlebar mustache, a red neckerchief scarf, a "
                      "cheeky grin, tiny small yellow-orange stick body.", "bright orange halftone dots."),
    'dude_brenda': dude("a tall pink mohawk, black eye-black stripes under the eyes, an angry determined scowl, "
                        "huge balloon-like purple bicep muscles.", "bright pink halftone dots."),
    'dude_major': dude("a clear glass fishbowl space helmet over the head, a monocle, a curly mustache and a red "
                       "bow tie inside the helmet, a posh grin, blue stick body.", "bright blue halftone dots."),
    'dude_gramps': dude("a very long white beard down to the chest, a floppy blue nightcap, wrinkly old man face, "
                        "pink fluffy slippers visible, hunched grey stick body.", "bright green halftone dots."),
})

# ---- second-round re-rolls: takes a/b of these two read weakly (wind = a literal leaf, jungle = white gorilla)
def _extra(name, prompts):
    it = ITEMS[name]
    it['takes'] = 'ab' + ''.join(prompts)
    it['prompts'] = {t: STYLE + p + BG_NOTE for t, p in prompts.items()}


_extra('boss_wind', {
    'c': "A scrawny stick figure man with a gigantic round barrel chest and huge puffed-out cheeks, blasting a big "
         "green leaf blower machine with a long nozzle and a backpack engine, a swirl of wind and leaves shooting "
         "out of the nozzle, standing on a fluffy white cloud. Background: bright blue sky with wind lines and "
         "little windmills.",
    'd': "A tiny stick figure man with an absurdly huge round chest and enormous lungs, red face, cheeks puffed, "
         "riding on a fluffy white cloud and holding a loud green leaf blower that blows a tornado of orange and "
         "green leaves. Background: sunny blue sky, speed lines, halftone dots."})
_extra('boss_jungle', {
    'c': "A giant muscular gorilla with dark brown fur and a black face wearing a tight white tank top, beating his "
         "chest with both fists and roaring with a wide open mouth, a banana in his hand. Background: a jungle "
         "temple with vines, big green leaves and golden light.",
    'd': "A huge angry dark brown gorilla with enormous arms and tiny stick legs, wearing a stretched white tank "
         "top, thumping his chest, bananas flying around. Background: bright green jungle with ancient stone "
         "temple ruins and hanging vines."})

# ---- title splash, composited variant (title_d/e/f by compose_title.py) -------------------------------------
# The menu column covers the middle of the title screen, so besides the one-shot takes a/b/c we generate the
# five dudes separately on white, cut them out and arrange them in two groups either side of the menu.
PART_STYLE = ("A silly comic book illustration in a stick figure cartoon style: thick black ink outlines, flat "
              "saturated bright colors, Ben-Day halftone dot shading, bold simple shapes, funny ridiculous "
              "character with tiny stick arms and legs, clean vector look. Full body, one single character "
              "charging forward toward the viewer in a dynamic running pose, firing his weapon with a bright "
              "muzzle flash. Plain pure white background, nothing else in the picture, no ground, no shadow. ")


def part(prompt):
    return {'kind': 'part', 'gen': (640, 768), 'takes': 'ab', 'prompt': PART_STYLE + prompt}


PARTS = {
    'part_sgt': part("A soldier stick figure with bright red arms and legs, a huge blond pompadour hair and black "
                     "aviator sunglasses, a determined grin, holding a big pump shotgun."),
    'part_pete': part("A tiny stick figure cowboy with a gigantic brown cowboy hat that is much too big for him, a "
                      "handlebar mustache and a red bandana, firing two revolvers."),
    'part_brenda': part("A muscular purple stick figure woman with huge balloon biceps, a bright pink mohawk and "
                        "black stripes under her eyes, holding a big chunky minigun."),
    'part_major': part("A British officer stick figure wearing a round glass fishbowl helmet over his head with a "
                       "monocle inside the bowl and a bushy moustache, holding a rocket launcher on his shoulder."),
    'part_gramps': part("A grumpy grey old stick figure grandpa with a white beard hanging down to his knees, a "
                        "nightcap and slippers, hunched over, holding a flamethrower that shoots a stream of fire."),
    'part_bg': {'kind': 'part', 'gen': (1280, 720), 'takes': 'ab', 'prompt': STYLE +
                "A wide comic book action background with no characters at all: a bright yellow and orange "
                "sunburst radiating from the center with halftone dots, big orange and red comic explosion burst "
                "shapes with flames and smoke on the left side, on the right side and in the middle, flying "
                "debris, a plain white ground strip along the bottom. The top third is calm and empty."},
}
# a/b drew a stray character / a white band, so c/d re-roll the backdrop with a purely abstract description
PARTS['part_bg']['takes'] = 'abcd'
PARTS['part_bg']['prompts'] = {
    'c': STYLE + "A wide abstract comic book explosion backdrop pattern, nobody in it: bright yellow and orange "
         "sunburst rays with halftone dots covering the whole picture, three huge jagged comic explosion bursts "
         "with black outlines, flames and puffs of smoke (one on the far left, one in the middle, one on the far "
         "right), flying sparks and debris, and a flat pale ground along the bottom edge.",
    'd': STYLE + "A wide comic book battlefield backdrop pattern, empty scene: a giant red, orange and yellow "
         "sunburst filling the sky, halftone dots, fiery explosion bursts with black outlines and smoke clouds "
         "low on the left and right, scorched flat ground along the bottom."}
