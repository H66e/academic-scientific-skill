"""Strict shared argument parsing and the fail-closed CLI envelope.

Both CLIs must reject repeated/abbreviated long options before any work starts,
and a malformed event inside a structurally valid ledger must be reported as a
standard envelope instead of printing a traceback.
"""
from __future__ import annotations
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr

REPO = Path(__file__).resolve().parents[2]
SKILL = REPO / "skills" / "ai-research-mentor"
sys.path.insert(0, str(SKILL / "runtime"))
from research_mentor.cli import parser
from research_mentor.ledger import Ledger, canonical_json, digest
from research_mentor.strict_cli import StrictArgumentParser
from research_mentor.tool_cli import sources_parser

ENVELOPE_KEYS = {"ok", "status", "data", "warnings", "errors", "ledger_events", "next"}


def subparsers(root):
    return next(action for action in root._actions if hasattr(action, "add_parser"))


class SharedStrictParserTests(unittest.TestCase):
    def test_main_and_native_tool_clis_share_the_strict_parser(self):
        root = parser()
        self.assertIs(type(root), StrictArgumentParser)
        self.assertIs(type(sources_parser()), StrictArgumentParser)
        self.assertIs(type(subparsers(root).choices["status"]), StrictArgumentParser)
        self.assertIs(type(subparsers(sources_parser()).choices["verify"]), StrictArgumentParser)

    def test_direct_parsing_rejects_abbreviation_and_repetition(self):
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as repeated:
                parser().parse_args(["--project", "synthetic", "status", "--format", "json", "--format", "json"])
            self.assertEqual(repeated.exception.code, 2)
            with self.assertRaises(SystemExit) as abbreviated:
                parser().parse_args(["--project", "synthetic", "status", "--form", "json"])
            self.assertEqual(abbreviated.exception.code, 2)
            well_formed = parser().parse_args(["--project", "synthetic", "status"])
            self.assertEqual(well_formed.command, "status")


class StrictMainCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mentor-strict-cli-")
        self.addCleanup(self.temp.cleanup)
        self.project = str(Path(self.temp.name))
        self.environment = {**os.environ, "PATH": str(Path(self.temp.name) / "no-executables"), "PYTHONIOENCODING": "utf-8"}

    def command(self, *arguments):
        return subprocess.run([sys.executable, "-B", str(SKILL / "scripts" / "research_mentor.py"), *map(str, arguments)],
                              text=True, encoding="utf-8", capture_output=True, env=self.environment,
                              cwd=str(REPO), timeout=30)

    def test_repeated_long_options_are_rejected(self):
        cases = (("--project", self.project, "--project", self.project, "status"),
                 ("--project=" + self.project, "--project=" + self.project, "status"),
                 ("--project", self.project, "--format", "json", "--format", "markdown", "status"),
                 ("--project", self.project, "search", "SYNTHETIC query",
                  "--sensitivity", "public", "--sensitivity", "private"))
        for arguments in cases:
            with self.subTest(arguments=arguments):
                run = self.command(*arguments)
                self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
                self.assertIn("Repeated option", run.stderr)
                self.assertNotIn("Traceback", run.stderr)

    def test_abbreviated_long_options_are_rejected(self):
        for arguments in (("--project", self.project, "status", "--proj", self.project),
                          ("--project", self.project, "status", "--form", "json")):
            with self.subTest(arguments=arguments):
                run = self.command(*arguments)
                self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
                self.assertIn("unrecognized arguments", run.stderr)
                self.assertNotIn("Traceback", run.stderr)

    def test_single_well_formed_flags_keep_working(self):
        run = self.command("--project", self.project, "--format", "markdown", "status")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn("current: ok", run.stdout)
        tool = subprocess.run([sys.executable, "-B", str(SKILL / "scripts" / "research_sources.py"), "verify",
                               "--doi", "10.5555/synthetic-cli", "--offline"],
                              text=True, encoding="utf-8", capture_output=True, env=self.environment, timeout=30)
        self.assertEqual(tool.returncode, 0, tool.stdout + tool.stderr)
        self.assertIn("offline", tool.stdout)


def write_ledger(project: Path, candidate: dict) -> None:
    """Write a hash-chain-valid, anchored ledger containing one candidate event."""
    rows = (("project.init", "tool", "T0", {"project_id": "P-SYNTHETIC", "core_version": "0.4.0"}),
            ("candidate.upsert", "model", "T2", candidate))
    events, previous = [], None
    for sequence, (event_type, actor, trust, data) in enumerate(rows, 1):
        event = {"seq": sequence, "id": f"EV-{sequence:06d}", "ts": "2026-10-10T00:00:00Z", "type": event_type,
                 "actor": actor, "trust": trust, "data": data, "prev": previous, "protocol": "ledger-json-v1"}
        event["sha256"] = digest(event)
        previous = event["sha256"]
        events.append(event)
    project.mkdir(parents=True, exist_ok=True)
    (project / "ledger.jsonl").write_text("".join(canonical_json(event) + "\n" for event in events), encoding="utf-8")
    anchor = {"protocol": "ledger-anchor-v1", "event_count": len(events), "head": previous}
    (project / "ledger.anchor.json").write_text(canonical_json(anchor) + "\n", encoding="utf-8")


ADMISSIBLE_NESTED_CANDIDATE = {
    "id": "C-SYNTHETIC", "version": 1, "title": "SYNTHETIC candidate",
    "question": "SYNTHETIC question", "hypothesis": "SYNTHETIC hypothesis",
    "contribution": "SYNTHETIC contribution", "research_type": "empirical", "search_ids": [],
    "nearest_work": [{"paper_id": "P-SYNTHETIC", "evidence_ids": []}],
    "novelty": {"status": "unclear"}, "feasibility": {"status": "unknown"},
    "validation": {"status": "missing"},
}


class FailClosedEnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mentor-fail-closed-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.environment = {**os.environ, "PATH": str(self.root / "no-executables"), "PYTHONIOENCODING": "utf-8"}

    def command(self, project, *arguments):
        return subprocess.run([sys.executable, "-B", str(SKILL / "scripts" / "research_mentor.py"),
                               "--project", str(project), *map(str, arguments)],
                              text=True, encoding="utf-8", capture_output=True, env=self.environment,
                              cwd=str(REPO), timeout=30)

    def test_low_level_candidate_without_id_is_reported_as_an_envelope(self):
        project = self.root / "missing-id"
        write_ledger(project, {"title": "SYNTHETIC event without an id"})
        run = self.command(project, "--format", "json", "status")
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        self.assertNotIn("Traceback", run.stderr)
        envelope = json.loads(run.stdout)
        self.assertEqual(set(envelope), ENVELOPE_KEYS)
        self.assertFalse(envelope["ok"])
        self.assertEqual(envelope["status"], "failed")
        self.assertTrue(envelope["errors"])

    def test_unexpected_exception_inside_run_is_fail_closed(self):
        project = self.root / "nested-payload"
        write_ledger(project, ADMISSIBLE_NESTED_CANDIDATE)
        self.assertTrue(Ledger(project).verify()["valid"], "fixture must pass payload admission")
        run = self.command(project, "--format", "json", "assess", "C-SYNTHETIC", "--reason", "SYNTHETIC nested payload")
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        self.assertNotIn("Traceback", run.stderr)
        envelope = json.loads(run.stdout)
        self.assertEqual(set(envelope), ENVELOPE_KEYS)
        self.assertFalse(envelope["ok"])
        self.assertEqual(envelope["status"], "failed")
        self.assertIn("KeyError", envelope["errors"][0])

    def test_unexpected_exception_is_reported_in_markdown_mode_too(self):
        project = self.root / "nested-markdown"
        write_ledger(project, ADMISSIBLE_NESTED_CANDIDATE)
        run = self.command(project, "--format", "markdown", "assess", "C-SYNTHETIC", "--reason", "SYNTHETIC nested payload")
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        self.assertNotIn("Traceback", run.stderr)
        self.assertTrue(run.stdout.startswith("failed: failed"), run.stdout)
        self.assertIn("- Error:", run.stdout)


if __name__ == "__main__":
    unittest.main()
