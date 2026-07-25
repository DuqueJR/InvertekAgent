import sys
from pathlib import Path

# The repo root is not a package, so put it on sys.path to allow
# `from agent.tools.ptb...` imports when pytest is run from anywhere.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
