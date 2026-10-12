"""Public SYNTHETIC protocol workflow; no real request or recall claim."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "skills/ai-research-mentor/runtime"))

from research_mentor.audit import rank_dossier, validate_dossier
from research_mentor.outputs import draft_dossier, export_bibtex, render_card
from research_mentor.sources import acquire_fulltext, search_crossref


class SourceWorkflowTests(unittest.TestCase):
    def dependencies(self, fetch):
        return {"lookup": lambda *_: [{"address": "1.1.1.1", "family": 4}], "fetch": fetch,
                "now": lambda: "2026-10-10T00:00:00.000Z", "pause": lambda *_: None}

    def test_acquired_metadata_validates_and_exports_without_manufacturing_approval(self):
        metadata = {"DOI": "10.5555/synthetic-workflow", "title": ["SYNTHETIC source; not a real paper"],
                    "published": {"date-parts": [[2026]]}, "author": [{"given": "Ada", "family": "Fixture"}]}
        response = {"status": 200, "headers": {"content-type": "application/json"},
                    "body": json.dumps({"status": "ok", "message": {"items": [metadata], "total-results": 1}}).encode()}
        with patch("socket.create_connection", side_effect=AssertionError("Synthetic workflow must stay offline")):
            sources = search_crossref({"query": metadata["title"][0], "rows": 2, "sensitivity": "public"},
                                      self.dependencies(lambda *_: response))
        notes = {"question": "SYNTHETIC: when would an invented tradeoff change?", "type": "measurement",
                 "known": ["Metadata protocol fixture only; technical sections have not been read."], "decision": "HOLD"}
        dossier = draft_dossier(notes, name="synthetic-workflow")
        dossier["searches"], dossier["papers"] = sources["searches"], sources["papers"]
        self.assertTrue(validate_dossier(dossier)["valid"])
        self.assertEqual(dossier["papers"][0]["version"], "unknown")
        for key in ("evidence", "ideas", "reviews", "pilots", "result_invalidations"):
            self.assertEqual(dossier[key], [])
        self.assertEqual(rank_dossier(dossier)["ranked"], [])
        bibliography = export_bibtex(dossier)
        self.assertEqual(bibliography["exported_count"], 1)
        self.assertIn("10.5555/synthetic-workflow", bibliography["bibtex"])
        self.assertIn("HOLD", render_card(notes))

    def test_failed_actual_attempt_stays_failed_without_becoming_novelty_evidence(self):
        def failure(*_):
            raise OSError("SYNTHETIC provider fixture unavailable")
        sources = search_crossref({"query": "SYNTHETIC research question", "sensitivity": "public"}, self.dependencies(failure))
        dossier = draft_dossier({"question": "SYNTHETIC Q", "limitations": ["Search failed; novelty is unassessed."]}, name="synthetic-failed")
        dossier["searches"], dossier["papers"] = sources["searches"], sources["papers"]
        self.assertEqual(dossier["searches"][0]["status"], "failed")
        self.assertTrue(validate_dossier(dossier)["valid"])
        self.assertEqual(dossier["papers"], [])
        self.assertEqual(dossier["ideas"], [])
        self.assertEqual(export_bibtex(dossier)["exported_count"], 0)

    def test_landing_html_remains_unassigned_material_throughout_the_workflow(self):
        response = {"status": 200, "headers": {"content-type": "text/html"},
                    "body": b'<html><h1 id="title">SYNTHETIC landing page</h1><p id="abstract">Abstract fixture.</p></html>'}
        source = acquire_fulltext({"url": "https://example.org/paper"}, self.dependencies(lambda *_: response))
        self.assertEqual(source["status"], "needs_host_review")
        self.assertEqual(source["reading_scope"], "not_assigned")
        self.assertEqual(source["content_kind"], "unknown")
        dossier = draft_dossier({"question": "SYNTHETIC Q", "limitations": ["HTML not established as paper body."]}, name="synthetic-html")
        self.assertEqual(dossier["evidence"], [])
        self.assertEqual(rank_dossier(dossier)["ranked"], [])


if __name__ == "__main__":
    unittest.main()
