#!/usr/bin/env python3
"""Install one take of a vocal SFX as the game's sound.   (plain python 3, stdlib only)

    python tools/vocal/promote.py shotgun doosh2        # assets/sfx/shotgun.mp3 <- tools/vocal/takes/shotgun/doosh2.mp3
    python tools/vocal/promote.py --list [name]         # show takes + what is installed
    python tools/vocal/promote.py --old pistol          # put the ORIGINAL (pre-vocal) sfx back from assets/raw_audio/sfx_old/

The takes in tools/vocal/takes are already mastered (mono, 24 kHz, 96 kbps mp3, peak -1 dBFS, loudness-matched), so
promoting is a file copy + manifest update ("pinned": master.py will not overwrite a pinned choice) + rebuild of
tools/vocal/audition.html + `python tools/make_audiolist.py` so js/audiolist.js lists the file.
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
MAN = os.path.join(HERE, 'manifest.json')
TAKES = os.path.join(HERE, 'takes')
SFX = os.path.join(ROOT, 'assets', 'sfx')
OLD = os.path.join(ROOT, 'assets', 'raw_audio', 'sfx_old')


def load():
    with open(MAN, 'r', encoding='utf-8') as fh:
        return json.load(fh)


def save(man):
    with open(MAN, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(man, fh, indent=1)


def backup(name):
    """keep the pre-vocal file once (never overwrite an existing backup)"""
    src = os.path.join(SFX, name + '.mp3')
    dst = os.path.join(OLD, name + '.mp3')
    if os.path.isfile(src) and not os.path.isfile(dst):
        os.makedirs(OLD, exist_ok=True)
        shutil.copy2(src, dst)


def take_dir(man, name):
    return man['names'][name].get('variant_of') or name


def install(man, name, take, pin=True):
    ent = man['names'][name]
    base = take_dir(man, name)
    src = os.path.join(TAKES, base, take + '.mp3')
    if not os.path.isfile(src):
        raise SystemExit('no such take: %s' % src)
    if ent.get('installed') is None:  # first vocal install of this name only: never back up one of our own files as 'old'
        backup(name)
    shutil.copy2(src, os.path.join(SFX, name + '.mp3'))
    ent['installed'] = take
    if pin:
        ent['pinned'] = True


def rebuild(quiet=False):
    sys.path.insert(0, HERE)
    import build_audition
    build_audition.build()
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'make_audiolist.py')], capture_output=True, text=True)
    if not quiet:
        print(r.stdout.strip() or r.stderr.strip())


def main(argv):
    if not argv or argv[0] in ('-h', '--help'):
        print(__doc__)
        return 0
    man = load()
    if argv[0] == '--list':
        for n in ([argv[1]] if len(argv) > 1 else man['order']):
            e = man['names'][n]
            tk = man['names'][take_dir(man, n)]['takes']
            print('%-14s installed=%-7s default=%-7s takes: %s' % (n, e.get('installed'), e.get('default'), ' '.join(tk)))
        return 0
    if argv[0] == '--old':
        n = argv[1]
        src = os.path.join(OLD, n + '.mp3')
        if not os.path.isfile(src):
            raise SystemExit('no backup for %s in %s' % (n, OLD))
        shutil.copy2(src, os.path.join(SFX, n + '.mp3'))
        man['names'][n]['installed'] = 'ORIGINAL'
        man['names'][n]['pinned'] = True
        save(man)
        rebuild()
        print('restored original %s.mp3' % n)
        return 0
    if len(argv) != 2:
        raise SystemExit('usage: promote.py <name> <take>   (or --list / --old <name>)')
    name, take = argv
    if name not in man['names']:
        raise SystemExit('unknown sfx name %r; known: %s' % (name, ', '.join(man['order'])))
    tk = man['names'][take_dir(man, name)]['takes']
    if take not in tk:
        raise SystemExit('unknown take %r for %s; takes: %s' % (take, name, ', '.join(tk)))
    install(man, name, take)
    save(man)
    rebuild()
    print('promoted %s <- %s  (assets/sfx/%s.mp3)' % (name, take, name))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
