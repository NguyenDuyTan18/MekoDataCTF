#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'meko_boutique'))
from common import main

sys.exit(main('crypto', root=ROOT / 'rpc'))
