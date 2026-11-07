"""The pixpocket program, as the generators run it: in the document's folder,
which is how Pixpocket finds the document, so nothing passes --document.

The program is the one this repo pins (.pixpocket-version), which
scripts/install-pixpocket.sh puts in .tools/pixpocket/; PIXPOCKET picks
another. PIXPOCKET_DOC and PIXPOCKET_SITE would win over the folder, so
they're left out of its environment."""
import os, subprocess, sys

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
PINNED = open(os.path.join(REPO, '.pixpocket-version')).read().strip()
TOOL = os.path.join(REPO, '.tools', 'pixpocket', 'pixpocket')
PX = os.environ.get('PIXPOCKET') or TOOL
PX = os.path.abspath(PX) if os.sep in PX else PX
ENV = {k: v for k, v in os.environ.items() if k not in ('PIXPOCKET_DOC', 'PIXPOCKET_SITE')}

if not os.environ.get('PIXPOCKET'):
    if not os.path.exists(TOOL):
        sys.exit(f'No pinned pixpocket in .tools/: run scripts/install-pixpocket.sh (pixpocket {PINNED}).')
    got = subprocess.run([TOOL, '--version'], capture_output=True, text=True).stdout.strip()
    if got != f'pixpocket {PINNED}':
        sys.exit(f'.tools/ has {got or "an unknown pixpocket"}, the repo pins {PINNED}: run scripts/install-pixpocket.sh.')


def run(doc, *args, **kw):
    """Run pixpocket in doc's folder, on that document."""
    return subprocess.run([PX, *args], cwd=doc, env=ENV, capture_output=True, text=True, **kw)
