#!/usr/bin/env python3
"""Check a user-facing research report draft; structural only, not truth."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))

from research_mentor.draft import main

if __name__ == "__main__":
    raise SystemExit(main())
