"""Synthetic reading CLI integration; no real paper or reading is asserted."""
from pathlib import Path
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "skills/ai-research-mentor/runtime"))
from research_mentor.cli import parser, run
from research_mentor.core import ResearchCore
from research_mentor.readings import effective_readings


class ReadingCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="synthetic-reading-cli-")
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.core = ResearchCore(self.project)
        source = self.project / "synthetic.txt"
        source.write_text("SYNTHETIC exact fixture excerpt, no scientific result.", encoding="utf-8")
        acquired = self.core.fetch(local_path=source)
        self.assertTrue(acquired.ok, acquired.errors)
        self.source_id = acquired.data["id"]
        anchored = self.core.quote(acquired.data["id"], "SYNTHETIC exact fixture excerpt")
        self.assertTrue(anchored.ok, anchored.errors)
        self.evidence_id = anchored.data["id"]

    def invoke(self, *args):
        return run(parser().parse_args(["--project", str(self.project), *args]))

    def test_complete_false_statement_can_be_withdrawn_without_new_reading(self):
        read = self.invoke("confirm-read", self.evidence_id, "--scope", "full_text",
            "--context", "SYNTHETIC mistaken statement")
        withdrawn = self.invoke("retract-read", read.ledger_events[0],
            "--reason", "SYNTHETIC statement completely withdrawn")
        self.assertTrue(withdrawn.ok)
        events = self.core.ledger.read()
        self.assertEqual(len([e for e in events if e["type"] == "reading.confirm"]), 1)
        self.assertEqual(effective_readings(events, self.evidence_id), [])
        self.assertEqual(set(withdrawn.data), {"target", "reason"})
        self.assertTrue(self.invoke("verify-ledger").ok)

    def test_repeated_exact_anchor_does_not_make_reading_lookup_ambiguous(self):
        repeated = self.core.quote(self.source_id, "SYNTHETIC exact fixture excerpt")
        self.assertTrue(repeated.ok, repeated.errors)
        self.assertEqual(repeated.data["id"], self.evidence_id)
        reading = self.invoke("confirm-read", self.evidence_id, "--scope", "section",
            "--context", "SYNTHETIC actual statement after repeated quote")
        self.assertTrue(reading.ok)
        self.assertEqual(len(effective_readings(self.core.ledger.read(), self.evidence_id)), 1)

    def test_human_statement_does_not_imply_visual_check_and_model_cannot_retire_it(self):
        read = self.invoke("confirm-read", self.evidence_id, "--scope", "section",
            "--context", "SYNTHETIC person's statement", "--human")
        self.assertFalse(read.data["visual_checked"])
        before = self.core.ledger.read()
        with self.assertRaises(ValueError):
            self.invoke("retract-read", read.ledger_events[0], "--reason", "Model cannot withdraw this")
        self.assertEqual(self.core.ledger.read(), before)
        withdrawn = self.invoke("retract-read", read.ledger_events[0],
            "--reason", "SYNTHETIC actual person's instruction", "--human")
        self.assertTrue(withdrawn.ok)
        self.assertEqual(effective_readings(self.core.ledger.read(), self.evidence_id), [])
