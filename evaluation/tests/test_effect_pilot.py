"""Tests for the effect-pilot de-formatting script.

The module lives under a hyphenated directory, so it is loaded by path rather
than imported as a package. No network, model, or third-party package is used.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "evaluation" / "effect-pilot" / "strip_artifact.py"

_SPEC = importlib.util.spec_from_file_location("effect_pilot_strip_artifact", SCRIPT)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover - import wiring guard
    raise RuntimeError(f"cannot load {SCRIPT}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
strip_artifact = _MODULE.strip_artifact

SAMPLE = """# Report

Intro [C12] stays.

<!-- report-tier: evidence_review -->

Finding [C1] matters.

```nearest-set-json
{"schema": "nearest-set-v2"}
```

```provisional-json
{"schema": "provisional-v1"}
```

Lists [C1, C2] here.

After [C2].
"""

PROSE = """# 标题

机制不同 [C1]。

```python
print("keep")
```

ABC 保留 [1]。
"""

PROSE_EXPECTED = """# 标题

机制不同。

```python
print("keep")
```

ABC 保留 [1]。
"""


class StripArtifactTests(unittest.TestCase):
    def test_removes_machine_blocks_comments_tier_markers_and_claim_ids(self):
        stripped = strip_artifact(SAMPLE)

        for marker in (
            "nearest-set-json",
            "provisional-json",
            "report-tier",
            "<!--",
            '"schema": "nearest-set-v2"',
            '"schema": "provisional-v1"',
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, stripped)
        self.assertNotRegex(stripped, r"\[C\d")
        for prose in ("# Report", "Intro stays.", "Finding matters.", "Lists here.", "After."):
            with self.subTest(prose=prose):
                self.assertIn(prose, stripped)

    def test_preserves_prose_case_language_citations_and_ordinary_fences(self):
        self.assertEqual(strip_artifact(PROSE), PROSE_EXPECTED)
        self.assertIn("机制不同。", strip_artifact(PROSE))
        self.assertIn("[1]", strip_artifact(PROSE))
        self.assertIn('print("keep")', strip_artifact(PROSE))
        self.assertNotIn("[C1]", strip_artifact(PROSE))

    def test_is_deterministic_idempotent_and_silent_in_function_mode(self):
        first = strip_artifact(SAMPLE)
        second = strip_artifact(SAMPLE)
        self.assertEqual(first, second)
        self.assertEqual(strip_artifact(first), first)

        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            result = strip_artifact(SAMPLE)
        self.assertEqual(captured.getvalue(), "")
        self.assertEqual(result, first)

    def test_cli_writes_stdout_or_out_and_never_changes_the_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            input_path = Path(temporary) / "artifact.md"
            with open(input_path, "w", encoding="utf-8", newline="") as handle:
                handle.write(SAMPLE)
            before = input_path.read_bytes()
            expected = strip_artifact(SAMPLE)

            completed = subprocess.run(
                [sys.executable, "-B", str(SCRIPT), str(input_path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stdout, expected)
            self.assertEqual(input_path.read_bytes(), before)

            out_path = Path(temporary) / "blind.md"
            completed = subprocess.run(
                [sys.executable, "-B", str(SCRIPT), str(input_path), "--out", str(out_path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(out_path.read_text(encoding="utf-8"), expected)
            self.assertEqual(input_path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
