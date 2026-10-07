"""Run standard-library Python tests and optional Node projection checks."""
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True
repo = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo / "skills" / "ai-research-mentor" / "runtime"))
suite = unittest.TestSuite()
for directory in (repo / "skills" / "ai-research-mentor" / "tests" / "python", repo / "evaluation" / "tests"):
    suite.addTests(unittest.TestLoader().discover(str(directory), pattern="test_*.py"))
if not suite.countTestCases():
    raise SystemExit("No Python tests discovered")
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
