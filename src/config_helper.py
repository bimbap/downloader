#!/usr/bin/env python3
# =============================================================================
# downloader/src/config_helper.py – Backwards-compatibility wrapper
# =============================================================================
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from core.config import *
