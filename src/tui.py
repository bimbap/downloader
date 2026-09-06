#!/usr/bin/env python3
# =============================================================================
# downloader/src/tui.py – Backwards-compatibility wrapper pointing to main.py
# =============================================================================
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from main import main

if __name__ == "__main__":
    main()
