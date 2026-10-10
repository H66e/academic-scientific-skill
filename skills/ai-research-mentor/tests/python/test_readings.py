"""SYNTHETIC local reading declarations; no real paper is claimed as read."""
from copy import deepcopy
from itertools import permutations
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "runtime"))
from research_mentor.core import ResearchCore
from research_mentor.judgment import Judgment, POLICY_VERSION
from research_mentor.ledger import LedgerError, canonical_json, digest
from research_mentor.readings import effective_readings


def candidate(candidate_id="C-SYNTHETIC"):
    return {"id": candidate_id, "title": "SYNTHETIC candidate", "question": "SYNTHETIC question",
            "hypothesis": "SYNTHETIC hypothesis", "contribution": "SYNTHETIC protocol fixture",
            "research_type": "empirical", "search_ids": [], "nearest_work": []}


class ReadingLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mentor-reading-")
        self.addCleanup(self.temp.cleanup)
        self.core = ResearchCore(self.temp.name)
        self.ledger = self.core.ledger
        self.judgment = Judgment(self.ledger)
        local = Path(self.temp.name) / "SYNTHETIC-source.txt"
        local.write_text("SYNTHETIC section alpha. SYNTHETIC section beta. No research finding.", encoding="utf-8")
        source = self.core.fetch(local_path=local)
        self.assertTrue(source.ok, source.errors)
        self.source_id = source.data["id"]
        anchored = self.core.quote(self.source_id, "SYNTHETIC section alpha")
        self.assertTrue(anchored.ok, anchored.errors)
        self.evidence_id = anchored.data["id"]
        self.judgment.upsert_candidate(candidate())

    def confirm(self, scope="section", *, human=False, visual=False):
        return self.judgment.confirm_read(self.evidence_id, scope, "SYNTHETIC actual fixture reading declaration",
                                          human=human, visual_checked=visual)

    def test_complete_false_report_can_be_withdrawn_without_inventing_replacement(self):
        declared = self.confirm("full_text")
        anchor_events = [e for e in self.ledger.read() if e["type"] == "evidence.anchor"]
        before = len(self.ledger.read())
        withdrawn = self.judgment.retract_read(declared["id"], "SYNTHETIC report was entirely false")
        self.assertEqual(set(withdrawn["data"]), {"target", "reason"})
        self.assertEqual(len(self.ledger.read()), before + 1)
        self.assertEqual(effective_readings(self.ledger.read(), self.evidence_id), [])
        self.assertEqual(self.ledger.get(declared["id"]), declared)
        self.assertEqual([e for e in self.ledger.read() if e["type"] == "evidence.anchor"], anchor_events)
        self.assertEqual(sum(e["type"] == "reading.confirm" for e in self.ledger.read()), 1)

    def test_supplement_preserves_deep_visual_qualification_and_withdrawal_is_targeted(self):
        deep = self.confirm("full_text", human=True, visual=True)
        abstract = self.confirm("abstract")
        active = effective_readings(self.ledger.read(), self.evidence_id)
        self.assertEqual({e["id"] for e in active}, {deep["id"], abstract["id"]})
        self.assertTrue(any(e["data"]["scope"] == "full_text" for e in active))
        self.assertTrue(any(e["data"]["visual_checked"] for e in active))
        self.judgment.retract_read(deep["id"], "SYNTHETIC explicit user correction", human=True)
        self.assertEqual([e["id"] for e in effective_readings(self.ledger.read(), self.evidence_id)], [abstract["id"]])
        fresh = self.confirm("section")
        active_ids = {e["id"] for e in effective_readings(self.ledger.read(), self.evidence_id)}
        self.assertEqual(active_ids, {abstract["id"], fresh["id"]})
        self.assertNotIn(deep["id"], active_ids, "New reading must not revive an old withdrawn assertion")

    def test_model_cannot_retire_user_and_user_can_retire_either_declared_actor(self):
        user = self.confirm(human=True)
        model = self.confirm()
        before = self.ledger.path.read_bytes(), self.ledger.anchor_path.read_bytes()
        with self.assertRaisesRegex(ValueError, "model cannot retract"):
            self.judgment.retract_read(user["id"], "SYNTHETIC unapproved user withdrawal")
        self.assertEqual(before, (self.ledger.path.read_bytes(), self.ledger.anchor_path.read_bytes()))
        for confirmation in (user, model):
            withdrawn = self.judgment.retract_read(confirmation["id"], "SYNTHETIC actual user instruction", human=True)
            self.assertEqual((withdrawn["actor"], withdrawn["trust"]), ("user", "T1"))
        self.assertEqual(effective_readings(self.ledger.read()), [])

    def test_missing_wrong_type_retraction_target_and_retired_target_fail_without_append(self):
        read = self.confirm()
        withdrawn = self.judgment.retract_read(read["id"], "SYNTHETIC wrong report")
        anchor = next(e for e in self.ledger.read() if e["type"] == "evidence.anchor")
        before = self.ledger.path.read_bytes(), self.ledger.anchor_path.read_bytes()
        for target in ("EV-999999", anchor["id"], withdrawn["id"], read["id"]):
            with self.subTest(target=target), self.assertRaises(ValueError):
                self.judgment.retract_read(target, "SYNTHETIC invalid withdrawal", human=True)
            self.assertEqual(before, (self.ledger.path.read_bytes(), self.ledger.anchor_path.read_bytes()))

    def test_payload_is_closed_and_nonempty_reason_is_required(self):
        read = self.confirm()
        valid = {"target": read["id"], "reason": "SYNTHETIC correction"}
        before = self.ledger.path.read_bytes(), self.ledger.anchor_path.read_bytes()
        for data in ({}, {"target": read["id"]}, {**valid, "reason": " "}, {**valid, "scope": "abstract"},
                     {**valid, "evidence_id": self.evidence_id}, {**valid, "target": []}):
            with self.subTest(data=data), self.assertRaises(LedgerError):
                self.ledger.append("reading.retract", data, actor="model", trust="T2")
            self.assertEqual(before, (self.ledger.path.read_bytes(), self.ledger.anchor_path.read_bytes()))
        for value in ("false", 1, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.judgment.retract_read(read["id"], "SYNTHETIC typed human flag", human=value)
        self.assertEqual(before, (self.ledger.path.read_bytes(), self.ledger.anchor_path.read_bytes()))

    def test_ledger_checks_structure_and_consumers_reject_invalid_transitions(self):
        read = self.confirm(human=True)
        # The raw ledger intentionally does not become a second lifecycle engine.
        self.ledger.append("reading.retract", {"target": read["id"], "reason": "SYNTHETIC unauthorized transition"},
                           actor="model", trust="T2")
        self.assertTrue(self.ledger.verify()["valid"])
        with self.assertRaisesRegex(ValueError, "model cannot retract"):
            effective_readings(self.ledger.read())
        with self.assertRaisesRegex(ValueError, "model cannot retract"):
            self.judgment.assess("C-SYNTHETIC", reason="SYNTHETIC invalid science must not be judged")

    def test_correct_hash_and_anchor_do_not_legalize_bad_retraction_payload(self):
        read = self.confirm()
        self.judgment.retract_read(read["id"], "SYNTHETIC honest withdrawal")
        events = self.ledger.read()
        events[-1]["data"]["scope"] = "abstract"
        events[-1]["sha256"] = digest({k: v for k, v in events[-1].items() if k != "sha256"})
        self.ledger.path.write_text("".join(canonical_json(e) + "\n" for e in events), encoding="utf-8")
        self.ledger.anchor_path.write_text(canonical_json({"protocol": "ledger-anchor-v1", "event_count": len(events),
                                                          "head": events[-1]["sha256"]}) + "\n", encoding="utf-8")
        report = self.ledger.verify()
        self.assertEqual(report["anchor"], "matched")
        self.assertFalse(report["valid"])
        self.assertTrue(any("invalid reading retraction payload" in error for error in report["errors"]))

    def test_reordered_event_views_never_resurrect_or_silently_replace_reading(self):
        deep = self.confirm("full_text")
        abstract = self.confirm("abstract")
        withdrawn = self.judgment.retract_read(deep["id"], "SYNTHETIC explicit withdrawal")
        base = [e for e in self.ledger.read() if not e["type"].startswith("reading.")]
        for ordering in permutations((deep, abstract, withdrawn)):
            self.assertEqual([e["id"] for e in effective_readings([*base, *ordering], self.evidence_id)], [abstract["id"]])
        bad = deepcopy(withdrawn)
        bad["id"] = "EV-999999"
        with self.assertRaisesRegex(ValueError, "already retracted"):
            effective_readings([*self.ledger.read(), bad])

    def test_identical_anchor_can_be_quoted_again_without_losing_reading(self):
        deep = self.confirm("full_text")
        again = self.core.quote(self.source_id, "SYNTHETIC section alpha")
        self.assertTrue(again.ok, again.errors)
        self.assertEqual(again.data["id"], self.evidence_id)
        abstract = self.confirm("abstract")
        self.assertEqual({e["id"] for e in effective_readings(self.ledger.read(), self.evidence_id)}, {deep["id"], abstract["id"]})
        self.assertTrue(self.core.verify_artifacts()["valid"])

    def test_retraction_uses_expected_head_against_concurrent_scientific_change(self):
        read = self.confirm()
        original = self.ledger.append
        def concurrent_append(event_type, data, **kwargs):
            if event_type == "reading.retract":
                original("reading.confirm", {"evidence_id": self.evidence_id, "scope": "abstract",
                    "context": "SYNTHETIC independent concurrent reader", "visual_checked": False}, actor="model", trust="T2")
            return original(event_type, data, **kwargs)
        with mock.patch.object(self.ledger, "append", side_effect=concurrent_append):
            with self.assertRaisesRegex(LedgerError, "ledger changed"):
                self.judgment.retract_read(read["id"], "SYNTHETIC stale write precondition")
        self.assertFalse(any(e["type"] == "reading.retract" for e in self.ledger.read()))
        self.assertIn(read["id"], {e["id"] for e in effective_readings(self.ledger.read())})

    def test_policy_upgrade_stales_all_candidate_decisions_without_touching_ledger(self):
        self.judgment.upsert_candidate(candidate("C-UNRELATED"))
        reviews = {}
        with mock.patch("research_mentor.judgment.POLICY_VERSION", "python-credibility-v3"):
            for candidate_id in ("C-SYNTHETIC", "C-UNRELATED"):
                reviews[candidate_id] = self.judgment.assess(candidate_id, reason="SYNTHETIC prior-policy assessment")
                self.judgment.record_decision(reviews[candidate_id]["review_id"], "HOLD", "SYNTHETIC prior actual user instruction", human=True)
            self.assertTrue(all(self.judgment.finalize(cid)["approval_status"] == "human_recorded" for cid in reviews))
        before = self.ledger.path.read_bytes(), self.ledger.anchor_path.read_bytes(), len(self.ledger.read())
        for cid, review in reviews.items():
            final = self.judgment.finalize(cid)
            self.assertTrue(final["assessment_required"])
            self.assertEqual(final["approval_status"], "pending_human")
            self.assertIsNone(final["human_decision"])
            self.assertEqual(final["previous_recommendation"], "HOLD")
            with self.assertRaisesRegex(ValueError, "review is stale"):
                self.judgment.record_decision(review["review_id"], "HOLD", "SYNTHETIC stale approval cannot transfer", human=True)
            assessed = self.judgment.assess(cid, reason="SYNTHETIC pure version change", record=False)
            self.assertEqual(assessed["missing"], review["missing"])
            self.assertEqual(assessed["policy_version"], POLICY_VERSION)
            self.assertNotEqual(assessed["snapshot"], review["snapshot"])
        self.assertEqual(before, (self.ledger.path.read_bytes(), self.ledger.anchor_path.read_bytes(), len(self.ledger.read())))
        self.assertTrue(self.ledger.verify()["valid"])
        fresh = self.judgment.assess("C-SYNTHETIC", reason="SYNTHETIC fresh policy review")
        self.assertIsNone(self.judgment.finalize("C-SYNTHETIC")["human_decision"])
        self.judgment.record_decision(fresh["review_id"], "HOLD", "SYNTHETIC new user instruction", human=True)
        self.assertEqual(self.judgment.finalize("C-SYNTHETIC")["approval_status"], "human_recorded")
        self.assertEqual(self.judgment.finalize("C-UNRELATED")["approval_status"], "pending_human")

    def test_supplement_stales_unrelated_review_even_when_qualification_is_unchanged(self):
        deep = self.confirm("full_text")
        self.judgment.upsert_candidate(candidate("C-UNRELATED"))
        review = self.judgment.assess("C-UNRELATED", reason="SYNTHETIC whole-project snapshot")
        self.judgment.record_decision(review["review_id"], "HOLD", "SYNTHETIC actual user instruction", human=True)
        self.confirm("abstract")
        self.assertIn(deep["id"], {e["id"] for e in effective_readings(self.ledger.read())})
        final = self.judgment.finalize("C-UNRELATED")
        self.assertTrue(final["assessment_required"])
        self.assertEqual(final["approval_status"], "pending_human")
        self.assertIsNone(final["human_decision"])


if __name__ == "__main__":
    unittest.main()
