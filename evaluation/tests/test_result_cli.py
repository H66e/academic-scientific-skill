"""Synthetic CLI-to-ledger integration; no experiment or network is executed."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "skills/ai-research-mentor/runtime"))
from research_mentor.cli import parser, run
from research_mentor.judgment import Judgment
from research_mentor.ledger import Ledger


class ResultCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="synthetic-result-cli-")
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.judgment = Judgment(Ledger(self.project))
        self.judgment.upsert_candidate({
            "id": "C-SYNTHETIC", "title": "SYNTHETIC CLI test",
            "question": "SYNTHETIC untested question", "hypothesis": "Untested",
            "contribution": "No research finding", "research_type": "empirical",
        })
        self.input = self.project / "input.json"
        self.input.write_text(json.dumps({
            "id": "R-SYNTHETIC", "run_id": "RUN-SYNTHETIC",
            "candidate_id": "C-SYNTHETIC", "candidate_version": 1,
            "kind": "scientific", "outcome": "contradicted",
            "artifacts": ["synthetic-output.txt"], "summary": "SYNTHETIC declaration",
            "limitations": ["Not a real measurement"], "affected_claims": [],
        }), encoding="utf-8")

    def invoke(self, *args):
        return run(parser().parse_args(["--project", str(self.project), *args]))

    def test_correction_and_human_invalidation_preserve_history_and_export(self):
        recorded = self.invoke("record-result", str(self.input))
        self.assertTrue(recorded.ok)
        self.assertTrue(self.invoke("results", "C-SYNTHETIC").data["requires_hold"])
        corrected = self.invoke("reclassify-result", recorded.data["id"],
            "--outcome", "inconclusive", "--reason", "SYNTHETIC interpretation corrected")
        self.assertTrue(corrected.ok)
        self.assertFalse(self.invoke("results", "C-SYNTHETIC").data["requires_hold"])
        self.invoke("invalidate-result", corrected.data["id"],
            "--reason", "SYNTHETIC person's withdrawal", "--human-confirmed")
        output = self.invoke("export-dossier").data
        self.assertEqual((output["schema_version"], output["decision_contract_version"]), (3, 3))
        self.assertEqual(len(output["pilots"]), 2)
        self.assertEqual(output["pilots"][1]["supersedes"], output["pilots"][0]["id"])
        self.assertEqual(len(output["result_invalidations"]), 1)
        self.assertEqual(output["reviews"], [])
        self.assertTrue(self.invoke("verify-ledger").ok)

    def test_missing_human_instruction_rejects_invalidation_without_an_append(self):
        self.invoke("record-result", str(self.input))
        before = self.judgment.ledger.read()
        with self.assertRaises(ValueError):
            self.invoke("invalidate-result", "R-SYNTHETIC", "--reason", "No person instructed this")
        self.assertEqual(self.judgment.ledger.read(), before)
        count = len(before)
        self.invoke("results", "C-SYNTHETIC", "--candidate-version", "1")
        self.assertEqual(len(self.judgment.ledger.read()), count)
