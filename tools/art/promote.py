"""Promote a candidate take to the shipped default.

  python tools/art/promote.py boss_ice b        # assets/raw_art/boss_ice_b.png -> assets/art/boss_ice.webp
  python tools/art/promote.py title a
  python tools/art/promote.py --list            # show every name, its default take and its candidates

Re-encodes from the lossless PNG at the size/quality in art_defs.py and records the pick in
assets/raw_art/chosen.json (so gen_art.py will not auto-overwrite it). Then re-run tools/art/contact.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import artlib as A  # noqa: E402
from art_defs import ITEMS  # noqa: E402


def main(argv):
    if not argv or argv[0] in ('-h', '--help'):
        print(__doc__)
        return 0
    chosen = A.load_json(A.CHOSEN, {})
    if argv[0] == '--list':
        for n, it in ITEMS.items():
            have = [t for t in it['takes'] if os.path.exists(A.raw_png(n, t))]
            c = chosen.get(n, {})
            print('%-16s default=%-2s %s candidates=%s' % (n, c.get('take', '-'), '(manual)' if c and not c.get('auto', True) else '(auto)  ', ','.join(have)))
        return 0
    if len(argv) != 2 or argv[0] not in ITEMS:
        print('usage: promote.py <name> <take>   names: ' + ' '.join(ITEMS))
        return 2
    name, take = argv
    src = A.raw_png(name, take)
    if not os.path.exists(src):
        print('no such candidate: %s' % src)
        return 1
    it = ITEMS[name]
    dst = os.path.join(A.ART, name + '.webp')
    sz = A.to_webp(src, dst, it['out'], it['q'])
    chosen[name] = {'take': take, 'auto': False}
    A.save_json(A.CHOSEN, chosen)
    print('%s <- take %s  (%d bytes)  => %s' % (name, take, sz, dst))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
