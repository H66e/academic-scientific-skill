#!/usr/bin/env python3
"""Thin standalone entry: no installation or virtual environment required."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))
from research_mentor.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
