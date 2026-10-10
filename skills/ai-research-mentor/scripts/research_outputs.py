#!/usr/bin/env python3
"""Standalone organizer for supplied notes and bibliographic records."""
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))
from research_mentor.tool_cli import main

if __name__ == "__main__":
    raise SystemExit(main("outputs"))
