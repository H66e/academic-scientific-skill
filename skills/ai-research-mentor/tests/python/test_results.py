"""Offline SYNTHETIC result declarations; no real experiment is asserted."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "runtime"))
from research_mentor.judgment import Judgment, POLICY_VERSION
from research_mentor.ledger import Ledger, LedgerError, canonical_json, digest


def candidate():
    return {"id": "C-SYNTHETIC", "title": "SYNTHETIC candidate", "question": "SYNTHETIC question",
            "hypothesis": "SYNTHETIC untested hypothesis", "contribution": "SYNTHETIC protocol case",
            "research_type": "empirical", "search_ids": [], "nearest_work": []}


def classification(**changes):
    data = {"id": "R1", "run_id": "RUN1", "candidate_id": "C-SYNTHETIC", "candidate_version": 1,
            "kind": "scientific", "outcome": "contradicted", "artifacts": ["SYNTHETIC-result.json"],
            "summary": "SYNTHETIC observation declaration only", "limitations": ["Invented fixture"],
            "affected_claims": []}
    data.update(changes)
    return data


class ResultLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mentor-result-")
        self.addCleanup(self.temp.cleanup)
        self.ledger = Ledger(self.temp.name, clock=lambda: "2026-10-10T00:00:00Z")
        self.judgment = Judgment(self.ledger)
        self.judgment.upsert_candidate(candidate())

    def test_result_payload_is_closed_and_rejections_leave_history_unchanged(self):
        before = self.ledger.path.read_bytes(), self.ledger.anchor_path.read_bytes()
        bad = [{}, classification(unrecognized=True), classification(candidate_version=True),
               classification(kind=[]), classification(outcome=None), classification(artifacts=[]),
               classification(summary=" "), classification(limitations=[False]),
               classification(affected_claims=["H1"]), classification(affected_claims=[{"claim_id": "H1", "reason": ""}]),
               classification(supersedes="R0"), classification(reason="Correction without target"),
               classification(artifacts=["javascript:alert(1)"]), classification(artifacts=["https://"]),
               classification(artifacts=["https://user:password@example.org/result"]),
               classification(artifacts=["result\x00.json"])]
        for data in bad:
            with self.subTest(data=data), self.assertRaises((ValueError, LedgerError)):
                self.judgment.record_result(data)
            self.assertEqual(before, (self.ledger.path.read_bytes(), self.ledger.anchor_path.read_bytes()))

    def test_not_run_has_no_fabricated_artifacts_or_scientific_refutation(self):
        self.judgment.record_result(classification(outcome="not_run", artifacts=[]))
        self.assertFalse(self.judgment.results("C-SYNTHETIC")["requires_hold"])
        result = self.judgment.assess("C-SYNTHETIC", "KILL", reason="SYNTHETIC not executed", kill_type="scientific_refutation")
        self.assertEqual(result["machine_recommendation"], "HOLD")

    def test_ambiguous_result_event_alias_cannot_silently_target_another_observation(self):
        first = self.judgment.record_result(classification())
        second = self.judgment.record_result(classification(id=first["id"], run_id="RUN2", outcome="supported"))
        before = self.ledger.path.read_bytes(), self.ledger.anchor_path.read_bytes()
        with self.assertRaisesRegex(ValueError, "ambiguous result.record ID"):
            self.judgment.reclassify_result(first["id"], "inconclusive", reason="SYNTHETIC ambiguous alias")
        with self.assertRaisesRegex(ValueError, "ambiguous result.record ID"):
            self.judgment.invalidate_result(first["id"], "SYNTHETIC ambiguous alias", human=True)
        self.assertEqual(before, (self.ledger.path.read_bytes(), self.ledger.anchor_path.read_bytes()))
        # The unique canonical first result ID remains a safe explicit target.
        corrected = self.judgment.reclassify_result("R1", "inconclusive", reason="SYNTHETIC unambiguous canonical ID")
        self.assertEqual(corrected["data"]["supersedes"], "R1")
        self.assertEqual(self.ledger.get(second["id"])["data"]["outcome"], "supported")

    def test_supported_independent_run_does_not_cancel_observed_contradiction(self):
        self.judgment.record_result(classification())
        self.judgment.record_result(classification(id="R2", run_id="RUN2", outcome="supported"))
        result = self.judgment.assess("C-SYNTHETIC", reason="SYNTHETIC independent support cannot erase contradiction")
        self.assertEqual(result["machine_recommendation"], "HOLD")
        self.assertTrue(result["result_state"]["contradiction_blocker"])
        explicit = self.judgment.assess("C-SYNTHETIC", "KILL", reason="SYNTHETIC declared effective refutation",
                                         kill_type="scientific_refutation")
        self.assertEqual(explicit["machine_recommendation"], "KILL")
        wrong_scope = self.judgment.assess("C-SYNTHETIC", "KILL", reason="SYNTHETIC wrong scope",
                                          scope="current_constraints", kill_type="scientific_refutation")
        self.assertEqual(wrong_scope["machine_recommendation"], "HOLD")

    def test_reclassification_is_visible_and_makes_review_and_decision_stale(self):
        first = self.judgment.record_result(classification())
        review = self.judgment.assess("C-SYNTHETIC", reason="SYNTHETIC unresolved contradiction")
        self.judgment.record_decision(review["review_id"], "HOLD", "SYNTHETIC actual user instruction", human=True)
        second = self.judgment.reclassify_result(first["id"], "supported", reason="SYNTHETIC analysis correction")
        third = self.judgment.reclassify_result(second["id"], "inconclusive", reason="SYNTHETIC uncertainty retained")
        state = self.judgment.results("C-SYNTHETIC")
        self.assertFalse(state["requires_hold"])
        self.assertEqual([h["id"] for h in state["runs"][0]["heads"]], [third["data"]["id"]])
        self.assertEqual(self.ledger.get(first["id"])["data"]["outcome"], "contradicted")
        final = self.judgment.finalize("C-SYNTHETIC")
        self.assertTrue(final["assessment_required"])
        self.assertEqual(final["previous_recommendation"], "HOLD")
        self.assertIsNone(final["human_decision"])
        with self.assertRaisesRegex(ValueError, "review is stale"):
            self.judgment.record_decision(review["review_id"], "HOLD", "SYNTHETIC stale instruction", human=True)
        no_basis = self.judgment.assess("C-SYNTHETIC", "KILL", reason="SYNTHETIC retired contradiction cannot refute",
                                       kill_type="scientific_refutation")
        self.assertEqual(no_basis["machine_recommendation"], "HOLD")

    def test_supported_fork_is_ambiguous_and_contradicted_fork_cannot_alone_kill(self):
        first = self.judgment.record_result(classification(outcome="supported"))
        self.judgment.reclassify_result(first["id"], "supported", reason="SYNTHETIC branch A")
        branch = self.judgment.reclassify_result(first["id"], "supported", reason="SYNTHETIC branch B")
        state = self.judgment.results("C-SYNTHETIC")
        self.assertTrue(state["ambiguity_blocker"])
        self.assertFalse(state["contradiction_blocker"])
        self.judgment.reclassify_result(branch["id"], "contradicted", reason="SYNTHETIC unresolved competing branch")
        review = self.judgment.assess("C-SYNTHETIC", "KILL", reason="SYNTHETIC ambiguous observation",
                                     kill_type="scientific_refutation")
        self.assertEqual(review["machine_recommendation"], "HOLD")
        self.assertTrue(review["warnings"])

    def test_only_user_invalidates_whole_run_and_reclassification_cannot_revive_it(self):
        first = self.judgment.record_result(classification())
        with self.assertRaisesRegex(ValueError, "actual human"):
            self.judgment.invalidate_result(first["id"], "SYNTHETIC model lacks instruction")
        review = self.judgment.assess("C-SYNTHETIC", reason="SYNTHETIC before control failure")
        invalidation = self.judgment.invalidate_result("R1", "SYNTHETIC control failure", human=True)
        self.assertEqual((invalidation["actor"], invalidation["trust"]), ("user", "T1"))
        self.assertTrue(self.judgment.finalize("C-SYNTHETIC")["assessment_required"])
        self.judgment.reclassify_result(first["id"], "contradicted", reason="SYNTHETIC same invalidated run")
        state = self.judgment.results("C-SYNTHETIC")
        self.assertFalse(state["requires_hold"])
        self.assertTrue(state["runs"][0]["invalidated"])
        self.assertEqual(state["scientific_refutation_basis"], [])
        self.judgment.record_result(classification(id="R-new", run_id="RUN-new"))
        self.assertTrue(self.judgment.results("C-SYNTHETIC")["contradiction_blocker"])

    def test_explanatory_claim_resolution_does_not_control_result_gate(self):
        claim = self.judgment.add_claim("SYNTHETIC explanatory hypothesis", "C-SYNTHETIC")
        self.judgment.record_result(classification(affected_claims=[{"claim_id": claim["id"], "reason": "SYNTHETIC target"}]))
        initial = self.judgment.results("C-SYNTHETIC")
        self.assertFalse(initial["affected_claims_degraded"])
        self.judgment.reclassify_result("R1", "contradicted", reason="SYNTHETIC explanation change",
            affected_claims=[{"claim_id": "H-missing", "reason": "SYNTHETIC dangling explanation"}])
        changed = self.judgment.results("C-SYNTHETIC")
        self.assertEqual(initial["requires_hold"], changed["requires_hold"])
        self.assertTrue(changed["affected_claims_degraded"])

    def test_missing_cross_run_version_and_duplicate_identity_fail_before_append(self):
        self.judgment.record_result(classification())
        before = self.ledger.path.read_bytes()
        for payload in [classification(id="R2", supersedes="absent", reason="SYNTHETIC missing"),
                        classification(id="R2", run_id="RUN2", supersedes="R1", reason="SYNTHETIC wrong run"),
                        classification(id="R2", candidate_version=2), classification(),
                        classification(id="R2", candidate_id="missing")]:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self.judgment.record_result(payload)
            self.assertEqual(before, self.ledger.path.read_bytes())
        self.judgment.upsert_candidate(candidate())
        with self.assertRaisesRegex(ValueError, "run_id belongs"):
            self.judgment.record_result(classification(id="R2", candidate_version=2))
        self.assertFalse(self.judgment.results("C-SYNTHETIC")["contradiction_blocker"])
        self.assertTrue(self.judgment.results("C-SYNTHETIC", candidate_version=1)["contradiction_blocker"])

    def test_ledger_rejects_invalidation_payload_and_model_actor(self):
        valid = {"id": "RI1", "run_id": "RUN1", "candidate_id": "C-SYNTHETIC", "candidate_version": 1,
                 "result_id": "R1", "reason": "SYNTHETIC invalidation", "recorded_at": "2026-10-10T00:00:00Z"}
        for data in [{}, {**valid, "reason": ""}, {**valid, "recorded_at": "2026-10-10"}, {**valid, "scope": "full_text"}]:
            with self.subTest(data=data), self.assertRaises(LedgerError):
                self.ledger.append("result.invalidate", data, actor="user", trust="T1")
        with self.assertRaises(LedgerError):
            self.ledger.append("result.invalidate", valid, actor="model", trust="T2")

    def test_correctly_hashed_malformed_payload_is_not_valid_ledger(self):
        self.judgment.record_result(classification())
        events = self.ledger.read()
        events[-1]["data"]["affected_claims"] = ["unstructured"]
        events[-1]["sha256"] = digest({k: v for k, v in events[-1].items() if k != "sha256"})
        self.ledger.path.write_text("".join(canonical_json(e) + "\n" for e in events), encoding="utf-8")
        self.ledger.anchor_path.write_text(canonical_json({"protocol": "ledger-anchor-v1", "event_count": len(events),
                                                        "head": events[-1]["sha256"]}) + "\n", encoding="utf-8")
        report = self.ledger.verify()
        self.assertFalse(report["valid"])
        self.assertEqual(report["anchor"], "matched")
        self.assertTrue(any("invalid result payload" in e for e in report["errors"]))

    def test_policy_upgrade_stales_finalized_decision_without_rewriting_history(self):
        with mock.patch("research_mentor.judgment.POLICY_VERSION", "python-credibility-v2"):
            old = self.judgment.assess("C-SYNTHETIC", reason="SYNTHETIC old policy review")
            self.judgment.record_decision(old["review_id"], "HOLD", "SYNTHETIC old explicit instruction", human=True)
            self.assertEqual(self.judgment.finalize("C-SYNTHETIC")["approval_status"], "human_recorded")
        ledger_bytes, anchor_bytes = self.ledger.path.read_bytes(), self.ledger.anchor_path.read_bytes()
        count = len(self.ledger.read())
        final = self.judgment.finalize("C-SYNTHETIC")
        self.assertTrue(final["assessment_required"])
        self.assertEqual(final["approval_status"], "pending_human")
        self.assertEqual(final["previous_recommendation"], "HOLD")
        self.assertIsNone(final["human_decision"])
        self.assertTrue(self.ledger.verify()["valid"])
        self.assertEqual(count, len(self.ledger.read()))
        self.assertEqual((ledger_bytes, anchor_bytes), (self.ledger.path.read_bytes(), self.ledger.anchor_path.read_bytes()))
        with self.assertRaisesRegex(ValueError, "review is stale"):
            self.judgment.record_decision(old["review_id"], "HOLD", "SYNTHETIC old review rejected", human=True)
        fresh = self.judgment.assess("C-SYNTHETIC", reason="SYNTHETIC new policy review")
        self.assertEqual(old["missing"], fresh["missing"], "A policy label alone must not change scientific gates")
        self.assertNotEqual(old["snapshot"], fresh["snapshot"])
        self.assertEqual(fresh["policy_version"], POLICY_VERSION)
        self.assertIsNone(self.judgment.finalize("C-SYNTHETIC")["human_decision"])
        self.judgment.record_decision(fresh["review_id"], "HOLD", "SYNTHETIC newly instructed decision", human=True)
        self.assertEqual(self.judgment.finalize("C-SYNTHETIC")["approval_status"], "human_recorded")

    def test_projection_preserves_history_scope_provenance_and_no_approvals(self):
        first = self.judgment.record_result(classification())
        self.judgment.reclassify_result(first["id"], "supported", reason="SYNTHETIC correction")
        self.judgment.invalidate_result(first["id"], "SYNTHETIC controls failed", human=True)
        dossier = self.judgment.export_dossier()
        self.assertEqual((dossier["schema_version"], dossier["decision_contract_version"]), (3, 3))
        self.assertEqual(len(dossier["pilots"]), 2)
        self.assertEqual(dossier["pilots"][1]["supersedes"], "R1")
        self.assertEqual({p["run_id"] for p in dossier["pilots"]}, {"RUN1"})
        self.assertEqual(dossier["result_invalidations"][0]["result_id"], "R1")
        self.assertEqual(dossier["result_invalidations"][0]["trust"], "T1")
        self.assertEqual(dossier["reviews"], [])
        self.assertEqual(dossier["evidence"], [])


if __name__ == "__main__":
    unittest.main()
