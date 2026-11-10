#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'meko_boutique'))
from common import main

if __name__ == '__main__':
    raise SystemExit(main('ecdsa_nonce', root=ROOT / 'rpc'))
