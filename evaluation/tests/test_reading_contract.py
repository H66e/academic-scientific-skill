"""Independent SYNTHETIC acceptance of cumulative reading and explicit withdrawal.

Local source acquisition and injected provider fixtures make no network calls.
These checks establish qualification/currency behavior, not honest reading or
scientific quality. They exercise real production judgment consumers.
"""
from __future__ import annotations

from copy import deepcopy
from itertools import permutations
from pathlib import Path
import sys
import unittest
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "skills" / "ai-research-mentor" / "runtime"))

import test_python_contract as source_contract
import research_mentor.judgment as judgment_module
from research_mentor.readings import effective_readings

CANDIDATE = "C-SYNTHETIC"


class ReadingContractTests(unittest.TestCase):
    def workflow(self, **options):
        # Compose its established offline source setup, without inheriting or
        # exposing an imported TestCase as another discoverable test suite.
        fixture = source_contract.ProjectionContractTests(
            "test_empty_projection_is_valid_and_has_no_approval")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        core, claim, evidence = fixture.bounded_workflow(**options)
        return fixture, core, claim, evidence

    def assess(self, judgment, **options):
        return judgment.assess(CANDIDATE, reason="SYNTHETIC independent reading contract check", **options)

    def readings(self, ledger, evidence):
        return effective_readings(ledger.read(), evidence)

    def assert_pending(self, judgment, previous):
        status = judgment.finalize(CANDIDATE)
        self.assertTrue(status["assessment_required"])
        self.assertEqual(status["approval_status"], "pending_human")
        self.assertIsNone(status["human_decision"])
        self.assertEqual(status["previous_recommendation"], previous)
        return status

    def test_supplement_preserves_deep_qualification_but_expires_go_and_human_decision(self):
        fixture, core, _, evidence = self.workflow()
        judgment = fixture.judgment
        judgment.confirm_read(evidence, "full_text", "SYNTHETIC entire short fixture inspected")
        review = self.assess(judgment)
        self.assertEqual(review["machine_recommendation"], "GO", review["missing"])
        decision = judgment.record_decision(review["review_id"], "GO",
            "SYNTHETIC explicit fixture instruction", human=True)
        before_events = fixture.ledger.read()
        supplemental = judgment.confirm_read(evidence, "abstract", "SYNTHETIC abstract-only later observation")
        self.assertEqual(fixture.ledger.read()[:len(before_events)], before_events)
        self.assertIn(supplemental["id"], [event["id"] for event in self.readings(fixture.ledger, evidence)])
        self.assert_pending(judgment, "GO")
        with self.assertRaisesRegex(ValueError, "stale"):
            judgment.record_decision(review["review_id"], "GO", "SYNTHETIC stale instruction", human=True)
        fresh = self.assess(judgment)
        self.assertEqual(fresh["machine_recommendation"], "GO", fresh["missing"])
        self.assertEqual(fresh["missing"], review["missing"], "Supplement cannot add a reading blocker")
        self.assertEqual(judgment.finalize(CANDIDATE)["approval_status"], "pending_human")
        judgment.record_decision(fresh["review_id"], "GO", "SYNTHETIC newly instructed decision", human=True)
        self.assertEqual(judgment.finalize(CANDIDATE)["approval_status"], "human_recorded")
        self.assertEqual(fixture.ledger.get(decision["id"])["data"]["human_decision"], "GO")
        self.assertTrue(core.verify_artifacts()["valid"])

    def test_section_supplement_can_remove_a_reading_blocker(self):
        fixture, _, _, evidence = self.workflow(read=False)
        judgment = fixture.judgment
        abstract = judgment.confirm_read(evidence, "abstract", "SYNTHETIC only fixture abstract inspected")
        held = self.assess(judgment)
        self.assertEqual(held["machine_recommendation"], "HOLD")
        self.assertTrue(any("relevant-section reading" in item for item in held["missing"]))
        section = judgment.confirm_read(evidence, "section", "SYNTHETIC relevant fixture section now inspected")
        self.assert_pending(judgment, "HOLD")
        advanced = self.assess(judgment)
        self.assertEqual(advanced["machine_recommendation"], "GO", advanced["missing"])
        self.assertEqual({item["id"] for item in self.readings(fixture.ledger, evidence)},
                         {abstract["id"], section["id"]})

    def test_explicit_retraction_of_last_deep_record_can_lower_qualification(self):
        fixture, _, _, evidence = self.workflow(read=False)
        judgment = fixture.judgment
        deep = judgment.confirm_read(evidence, "section", "SYNTHETIC initial deep declaration")
        abstract = judgment.confirm_read(evidence, "abstract", "SYNTHETIC separate narrow observation")
        reviewed = self.assess(judgment)
        self.assertEqual(reviewed["machine_recommendation"], "GO")
        historical = fixture.ledger.read()
        withdrawn = judgment.retract_read(deep["id"], "SYNTHETIC earlier deep declaration was mistaken")
        self.assertEqual(withdrawn["data"], {"target": deep["id"], "reason": "SYNTHETIC earlier deep declaration was mistaken"})
        self.assertEqual(fixture.ledger.read()[:-1], historical)
        self.assertEqual([item["id"] for item in self.readings(fixture.ledger, evidence)], [abstract["id"]])
        self.assert_pending(judgment, "GO")
        held = self.assess(judgment)
        self.assertEqual(held["machine_recommendation"], "HOLD")
        self.assertTrue(any("relevant-section reading" in item for item in held["missing"]))
        self.assertEqual(fixture.ledger.get(deep["id"]), deep)

    def test_full_withdrawal_has_no_fabricated_replacement_reading(self):
        fixture, _, _, evidence = self.workflow(read=False)
        judgment = fixture.judgment
        wrong = judgment.confirm_read(evidence, "full_text", "SYNTHETIC erroneous reading declaration")
        before = fixture.ledger.read()
        judgment.retract_read(wrong["id"], "SYNTHETIC no reading actually occurred")
        after = fixture.ledger.read()
        self.assertEqual(len(after), len(before) + 1)
        self.assertEqual(sum(item["type"] == "reading.confirm" for item in after), 1)
        self.assertEqual(after[-1]["type"], "reading.retract")
        self.assertEqual(self.readings(fixture.ledger, evidence), [])
        held = self.assess(judgment)
        self.assertEqual(held["machine_recommendation"], "HOLD")

    def test_partial_correction_is_two_distinct_append_events(self):
        fixture, _, _, evidence = self.workflow(read=False)
        judgment = fixture.judgment
        wrong = judgment.confirm_read(evidence, "full_text", "SYNTHETIC incorrectly broad declaration")
        before_count = len(fixture.ledger.read())
        withdrawn = judgment.retract_read(wrong["id"], "SYNTHETIC only abstract was inspected")
        self.assertEqual(self.readings(fixture.ledger, evidence), [])
        corrected = judgment.confirm_read(evidence, "abstract", "SYNTHETIC actual narrow observation")
        appended = fixture.ledger.read()[before_count:]
        self.assertEqual([item["type"] for item in appended], ["reading.retract", "reading.confirm"])
        self.assertEqual([item["id"] for item in appended], [withdrawn["id"], corrected["id"]])
        self.assertEqual([item["id"] for item in self.readings(fixture.ledger, evidence)], [corrected["id"]])
        with self.assertRaises(ValueError):
            judgment.retract_read(wrong["id"], "SYNTHETIC retired declaration cannot be withdrawn twice")

    def test_authorization_preserves_user_reading_and_allows_user_to_retract_model(self):
        fixture, _, _, evidence = self.workflow(read=False)
        judgment = fixture.judgment
        user = judgment.confirm_read(evidence, "full_text", "SYNTHETIC explicit person's fixture observation", human=True)
        model = judgment.confirm_read(evidence, "abstract", "SYNTHETIC model fixture observation")
        before = fixture.ledger.path.read_bytes(), fixture.ledger.anchor_path.read_bytes()
        with self.assertRaises(ValueError):
            judgment.retract_read(user["id"], "SYNTHETIC model cannot retire user declaration")
        self.assertEqual((fixture.ledger.path.read_bytes(), fixture.ledger.anchor_path.read_bytes()), before)
        user_retraction = judgment.retract_read(model["id"], "SYNTHETIC explicit user withdraws model declaration", human=True)
        self.assertEqual((user_retraction["actor"], user_retraction["trust"]), ("user", "T1"))
        self.assertEqual([item["id"] for item in self.readings(fixture.ledger, evidence)], [user["id"]])
        self.assertEqual(self.assess(judgment)["machine_recommendation"], "GO")
        judgment.retract_read(user["id"], "SYNTHETIC user explicitly withdraws own observation", human=True)
        self.assertEqual(self.readings(fixture.ledger, evidence), [])
        self.assertEqual(self.assess(judgment)["machine_recommendation"], "HOLD")

    def test_anchor_aliases_and_event_permutations_preserve_the_same_effective_set(self):
        fixture, core, _, evidence = self.workflow(read=False)
        anchor = next(item for item in fixture.ledger.read()
            if item["type"] == "evidence.anchor" and item["data"]["id"] == evidence)
        repeated = core.quote(anchor["data"]["source"], anchor["data"]["quote"],
            locator=anchor["data"]["locator"], block_id=anchor["data"]["block_id"])
        self.assertTrue(repeated.ok, repeated.errors)
        self.assertEqual(repeated.data["id"], evidence)
        fixture.ledger.clock = lambda: "2027-01-01T00:00:00Z"
        deep = fixture.judgment.confirm_read(anchor["id"], "full_text", "SYNTHETIC reading through original anchor alias")
        fixture.ledger.clock = lambda: "2020-01-01T00:00:00Z"
        abstract = fixture.judgment.confirm_read(repeated.ledger_events[0], "abstract",
            "SYNTHETIC supplemental reading through repeated anchor alias")
        self.assertEqual(deep["data"]["evidence_id"], evidence)
        self.assertEqual(abstract["data"]["evidence_id"], evidence)
        self.assertEqual(self.assess(fixture.judgment)["machine_recommendation"], "GO")
        fixture.ledger.clock = lambda: "2026-01-01T00:00:00Z"
        withdrawal = fixture.judgment.retract_read(deep["id"], "SYNTHETIC explicit causal withdrawal")
        base = [item for item in fixture.ledger.read() if not item["type"].startswith("reading.")]
        for ordering in permutations((deep, abstract, withdrawal)):
            for alias in (evidence, anchor["id"], repeated.ledger_events[0]):
                with self.subTest(order=[item["id"] for item in ordering], alias=alias):
                    effective = effective_readings([*base, *ordering], alias)
                    self.assertEqual([item["id"] for item in effective], [abstract["id"]])
        self.assertTrue(fixture.ledger.verify()["valid"])
        self.assertTrue(core.verify_artifacts()["valid"])

    def test_structurally_valid_ledger_cannot_authorize_invalid_reading_transitions(self):
        for error_kind in ("missing", "wrong_type", "already_retired", "unauthorized"):
            with self.subTest(error=error_kind):
                fixture, _, claim, evidence = self.workflow(read=False)
                reading = fixture.judgment.confirm_read(evidence, "full_text",
                    "SYNTHETIC transition target fixture", human=error_kind == "unauthorized")
                self.assertEqual(self.assess(fixture.judgment)["machine_recommendation"], "GO")
                target = reading["id"]
                if error_kind == "missing":
                    target = "EV-999999"
                elif error_kind == "wrong_type":
                    target = claim
                elif error_kind == "already_retired":
                    fixture.judgment.retract_read(target, "SYNTHETIC legitimate first withdrawal")
                fixture.ledger.append("reading.retract", {"target": target,
                    "reason": "SYNTHETIC deliberately invalid transition for consumer verification"},
                    actor="model", trust="T2")
                verification = fixture.ledger.verify()
                self.assertTrue(verification["valid"])
                self.assertEqual(verification["anchor"], "matched")
                before = fixture.ledger.path.read_bytes(), fixture.ledger.anchor_path.read_bytes()
                with self.assertRaises(ValueError):
                    effective_readings(fixture.ledger.read(), evidence)
                with self.assertRaises(ValueError):
                    self.assess(fixture.judgment)
                with self.assertRaises(ValueError):
                    fixture.judgment.finalize(CANDIDATE)
                self.assertEqual((fixture.ledger.path.read_bytes(), fixture.ledger.anchor_path.read_bytes()), before)

    def test_lossy_visual_consumer_uses_effective_readings(self):
        fixture, core, _, old_evidence = self.workflow(read=False)
        judgment = fixture.judgment
        candidate = deepcopy(next(item["data"] for item in fixture.ledger.read()
            if item["type"] == "candidate.upsert" and item["data"]["id"] == CANDIDATE))
        paper_id = candidate["nearest_work"][0]["paper_id"]
        html = Path(fixture.temporary.name) / "SYNTHETIC-lossy.html"
        html.write_text("<h2>SYNTHETIC Method</h2><p>SYNTHETIC lossy fixture supports a bounded comparison.</p><math>x</math>", encoding="utf-8")
        fetched = core.fetch(local_path=html, paper_id=paper_id)
        self.assertTrue(fetched.ok, fetched.errors)
        confirmed = core.confirm_source_identity(fetched.data["id"], paper_id, "unknown",
            "SYNTHETIC explicit fixture source identity instruction", human=True)
        self.assertTrue(confirmed.ok, confirmed.errors)
        quote = core.quote(fetched.data["id"], "SYNTHETIC lossy fixture supports a bounded comparison.")
        self.assertTrue(quote.ok, quote.errors)
        self.assertTrue(quote.data["lossy"], "Positive lossy source control is necessary")
        evidence = quote.data["id"]
        candidate["nearest_work"][0]["evidence_ids"] = [evidence]
        judgment.upsert_candidate(candidate)
        claim = judgment.add_claim("SYNTHETIC bounded fixture claim", CANDIDATE)
        judgment.link_claim(claim["id"], evidence, target="validation")
        model = judgment.confirm_read(evidence, "full_text", "SYNTHETIC extracted fixture inspected")
        visual = judgment.confirm_read(evidence, "abstract", "SYNTHETIC explicit page check instruction",
            human=True, visual_checked=True)
        self.assertEqual(self.assess(judgment)["machine_recommendation"], "GO")
        judgment.confirm_read(evidence, "abstract", "SYNTHETIC later supplemental observation")
        supplement = self.assess(judgment)
        self.assertEqual(supplement["machine_recommendation"], "GO", supplement["missing"])
        judgment.retract_read(visual["id"], "SYNTHETIC explicit user withdraws mistaken page check", human=True)
        held = self.assess(judgment)
        self.assertEqual(held["machine_recommendation"], "HOLD")
        self.assertTrue(any("page/visual check" in item for item in held["missing"]), held["missing"])
        self.assertFalse(any("relevant-section reading" in item for item in held["missing"]))
        self.assertIn(model["id"], [item["id"] for item in self.readings(fixture.ledger, evidence)])
        judgment.confirm_read(evidence, "section", "SYNTHETIC explicit fresh visual check", human=True, visual_checked=True)
        self.assertEqual(self.assess(judgment)["machine_recommendation"], "GO")
        self.assertTrue(core.verify_artifacts()["valid"])
        self.assertEqual(self.readings(fixture.ledger, old_evidence), [], "Another anchor's reading cannot transfer")

    def test_duplicate_kill_cannot_reuse_retracted_historical_deep_observations(self):
        fixture, _, _, evidence = self.workflow()
        judgment = fixture.judgment
        deep_events = [item for item in fixture.ledger.read() if item["type"] == "reading.confirm"]
        deep_events.append(judgment.confirm_read(evidence, "full_text", "SYNTHETIC another deep fixture observation"))
        candidate = deepcopy(next(item["data"] for item in fixture.ledger.read()
            if item["type"] == "candidate.upsert" and item["data"]["id"] == CANDIDATE))
        candidate["novelty"] = {"status": "duplicate", "reason": "SYNTHETIC equivalence assertion requires explicit support"}
        judgment.upsert_candidate(candidate)
        claim = judgment.add_claim("SYNTHETIC mechanism and assumptions match decisive fixture source",
            CANDIDATE, kind="mechanism_equivalence")
        judgment.link_claim(claim["id"], evidence, target="nearest_work")
        options = {"recommendation": "KILL", "kill_type": "duplicate", "scope": "scientific_framing"}
        positive = self.assess(judgment, **options)
        self.assertEqual(positive["machine_recommendation"], "KILL", positive["missing"])
        abstract = judgment.confirm_read(evidence, "abstract", "SYNTHETIC subsequent abstract observation")
        self.assert_pending(judgment, "KILL")
        self.assertEqual(self.assess(judgment, **options)["machine_recommendation"], "KILL")
        for reading in deep_events:
            judgment.retract_read(reading["id"], "SYNTHETIC explicit withdrawal of mistaken depth")
        self.assertEqual([item["id"] for item in self.readings(fixture.ledger, evidence)], [abstract["id"]])
        held = self.assess(judgment, **options)
        self.assertEqual(held["machine_recommendation"], "HOLD")
        self.assertTrue(any("relevant-section reading" in item for item in held["missing"]))
        for reading in deep_events:
            self.assertEqual(fixture.ledger.get(reading["id"]), reading)
        judgment.confirm_read(evidence, "section", "SYNTHETIC new real fixture section observation")
        self.assertEqual(self.assess(judgment, **options)["machine_recommendation"], "KILL")

    def test_policy_upgrade_expires_bound_go_without_rewriting_any_ledger_bytes(self):
        fixture, core, _, _ = self.workflow()
        judgment = fixture.judgment
        self.assertEqual(judgment_module.POLICY_VERSION, "python-credibility-v4")
        candidate = deepcopy(next(item["data"] for item in fixture.ledger.read()
            if item["type"] == "candidate.upsert" and item["data"]["id"] == CANDIDATE))
        candidate["id"] = "C-UNRELATED"
        judgment.upsert_candidate(candidate)
        evidence = candidate["nearest_work"][0]["evidence_ids"][0]
        claim = judgment.add_claim("SYNTHETIC unrelated candidate's bounded claim", "C-UNRELATED")
        judgment.link_claim(claim["id"], evidence, target="validation")
        with mock.patch.object(judgment_module, "POLICY_VERSION", "python-credibility-v3"):
            old = self.assess(judgment)
            self.assertEqual(old["machine_recommendation"], "GO", old["missing"])
            decision = judgment.record_decision(old["review_id"], "GO",
                "SYNTHETIC actual old-policy fixture instruction", human=True)
            self.assertEqual(judgment.finalize(CANDIDATE)["approval_status"], "human_recorded")
            unrelated = judgment.assess("C-UNRELATED", reason="SYNTHETIC unrelated old-policy candidate")
            self.assertEqual(unrelated["machine_recommendation"], "GO", unrelated["missing"])
            judgment.record_decision(unrelated["review_id"], "GO", "SYNTHETIC second explicit old-policy instruction", human=True)
            self.assertEqual(judgment.finalize("C-UNRELATED")["approval_status"], "human_recorded")
        before = fixture.ledger.path.read_bytes(), fixture.ledger.anchor_path.read_bytes()
        count = len(fixture.ledger.read())
        self.assert_pending(judgment, "GO")
        unrelated_status = judgment.finalize("C-UNRELATED")
        self.assertTrue(unrelated_status["assessment_required"])
        self.assertEqual(unrelated_status["previous_recommendation"], "GO")
        self.assertEqual(unrelated_status["approval_status"], "pending_human")
        self.assertIsNone(unrelated_status["human_decision"])
        self.assertNotEqual(judgment.snapshot(CANDIDATE), old["snapshot"])
        with self.assertRaisesRegex(ValueError, "stale"):
            judgment.record_decision(old["review_id"], "GO", "SYNTHETIC stale decision cannot restore approval", human=True)
        self.assertEqual((fixture.ledger.path.read_bytes(), fixture.ledger.anchor_path.read_bytes()), before)
        self.assertEqual(fixture.ledger.verify()["event_count"], count)
        self.assertTrue(fixture.ledger.verify()["valid"])
        self.assertTrue(core.verify_artifacts()["valid"])
        fresh = self.assess(judgment)
        self.assertEqual(fresh["policy_version"], "python-credibility-v4")
        self.assertEqual(judgment.export_dossier()["decision_contract_version"], 3,
                         "Python reading interpretation does not bump the Node decision contract")
        self.assertEqual(fresh["machine_recommendation"], "GO", fresh["missing"])
        self.assertEqual(judgment.finalize(CANDIDATE)["approval_status"], "pending_human")
        with self.assertRaises(ValueError):
            judgment.record_decision(fresh["review_id"], "GO", "SYNTHETIC model is not human approval")
        judgment.record_decision(fresh["review_id"], "GO", "SYNTHETIC newly instructed approval", human=True)
        self.assertEqual(judgment.finalize(CANDIDATE)["approval_status"], "human_recorded")
        self.assertEqual(fixture.ledger.get(decision["id"])["data"]["snapshot"], old["snapshot"])

    def test_pure_policy_upgrade_does_not_change_missing_or_scientific_inputs(self):
        fixture, core, _, evidence = self.workflow(read=False)
        judgment = fixture.judgment
        judgment.confirm_read(evidence, "abstract", "SYNTHETIC deliberately insufficient reading")
        before = fixture.ledger.path.read_bytes(), fixture.ledger.anchor_path.read_bytes()
        artifacts = core.verify_artifacts()
        readings = self.readings(fixture.ledger, evidence)
        with mock.patch.object(judgment_module, "POLICY_VERSION", "python-credibility-v3"):
            old = self.assess(judgment, record=False)
        upgraded = self.assess(judgment, record=False)
        self.assertEqual(old["machine_recommendation"], "HOLD")
        self.assertEqual(upgraded["machine_recommendation"], "HOLD")
        self.assertEqual(upgraded["missing"], old["missing"])
        self.assertNotEqual(upgraded["snapshot"], old["snapshot"])
        self.assertEqual(core.verify_artifacts(), artifacts)
        self.assertEqual(self.readings(fixture.ledger, evidence), readings)
        self.assertEqual((fixture.ledger.path.read_bytes(), fixture.ledger.anchor_path.read_bytes()), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
