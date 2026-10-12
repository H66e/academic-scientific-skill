"""SYNTHETIC ledger/dossier result semantics, not scientific-effectiveness tests.

The fixture expectations are independent of both implementations. Adapters map
declared identity/provenance to each production API; they do not implement a
third result fold or compare incompatible runtime fingerprint numbers.
"""
from __future__ import annotations

from copy import deepcopy
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "skills" / "ai-research-mentor" / "runtime"))

from research_mentor.audit import (
    DECISION_CONTRACT_VERSION, create_initial_dossier, effective_result_state,
    fingerprint_idea, migrate_dossier, rank_dossier, validate_dossier,
)
from research_mentor.judgment import Judgment
from research_mentor.ledger import Ledger, PROTOCOL, digest
from research_mentor.results import candidate_result_state

FIXTURE = REPO / "evaluation" / "fixtures" / "result-lifecycle.json"
STAMP = "2026-10-10T00:00:00Z"


def synthetic_candidate(identifier="C-SYNTHETIC", **changes):
    """Minimal candidate setup; missing research inputs remain honestly missing."""
    data = {
        "id": identifier, "title": "SYNTHETIC lifecycle candidate",
        "question": "Can an invented bounded claim be tested?",
        "research_type": "empirical", "hypothesis": "SYNTHETIC untested hypothesis",
        "contribution": "SYNTHETIC contract illustration", "search_ids": [], "nearest_work": [],
    }
    data.update(changes)
    return data


def expand_case(fixture, case):
    value = deepcopy(case)
    value["records"] = [{**deepcopy(fixture["record_defaults"]), **item} for item in case["records"]]
    value["invalidations"] = [{**deepcopy(fixture["invalidation_defaults"]), **item}
                              for item in case["invalidations"]]
    return value


def python_facts(state):
    """Adapt API names only; gate predicates remain production-computed."""
    return {
        "valid": True,
        **{key: state[key] for key in ("contradiction_blocker", "ambiguity_blocker", "requires_hold",
                                       "affected_claims_degraded")},
        "scientific_refutation_ids": sorted(item["id"] for item in state["scientific_refutation_basis"]),
    }




class ResultConformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        if cls.fixture.get("synthetic") is not True:
            raise AssertionError("Public conformance material must be explicitly synthetic")
        cls.cases = [expand_case(cls.fixture, case) for case in cls.fixture["cases"]]
        cls.temporary = tempfile.TemporaryDirectory(prefix="mentor-result-conformance-")
        cls.addClassCleanup(cls.temporary.cleanup)
        ledger = Ledger(Path(cls.temporary.name) / "base", clock=lambda: STAMP)
        judgment = Judgment(ledger)
        judgment.upsert_candidate(synthetic_candidate())
        judgment.upsert_candidate(synthetic_candidate("C-OTHER"))
        cls.claim_ids = {name: judgment.add_claim("SYNTHETIC explanatory claim " + name,
            cls.fixture["candidate_id"])["id"] for name in cls.fixture["claims"]}
        cls.base_events = ledger.read()

    @classmethod
    def events_for(cls, case):
        """In-memory event views, including intentionally malformed negatives.

        Result ordering tests reorder this view, not the persisted hash chain.
        Ledger integrity is separately tested; production folds cannot use the
        sequence/timestamp as a substitute for explicit causal references.
        """
        events = deepcopy(cls.base_events)
        if case.get("candidate_version", cls.fixture["candidate_version"]) == 2:
            prior = next(event for event in events if event["type"] == "candidate.upsert"
                         and event["data"]["id"] == cls.fixture["candidate_id"])
            versioned = deepcopy(prior)
            versioned["data"]["version"] = 2
            versioned.update(seq=len(events) + 1, id=f"EV-{len(events) + 1:06d}", prev=events[-1]["sha256"])
            versioned.pop("sha256")
            versioned["sha256"] = digest(versioned)
            events.append(versioned)
        for event_type, records in (("result.record", case["records"]),
                                     ("result.invalidate", case["invalidations"])):
            for record in records:
                data = deepcopy(record)
                actor, trust = data.pop("actor"), data.pop("trust")
                timestamp = data["recorded_at"]
                if event_type == "result.record":
                    data.pop("recorded_at")
                    if isinstance(data.get("affected_claims"), list):
                        for claim in data["affected_claims"]:
                            if isinstance(claim, dict) and "claim_id" in claim:
                                claim["claim_id"] = cls.claim_ids.get(claim["claim_id"], claim["claim_id"])
                seq = len(events) + 1
                event = {"seq": seq, "id": f"EV-{seq:06d}", "ts": timestamp, "type": event_type,
                         "actor": actor, "trust": trust, "data": data,
                         "prev": events[-1]["sha256"] if events else None, "protocol": PROTOCOL}
                event["sha256"] = digest(event)
                events.append(event)
        return events

    @classmethod
    def python_check(cls, case, events=None):
        try:
            state = candidate_result_state(events if events is not None else cls.events_for(case),
                cls.fixture["candidate_id"], case.get("candidate_version", cls.fixture["candidate_version"]))
        except ValueError as exc:
            return {"facts": {"valid": False}, "errors": [str(exc)]}
        return {"facts": python_facts(state), "warnings": state["warnings"],
                "runs": [{"run_id": run["run_id"], "eligible": not run["invalidated"],
                          "head_ids": sorted(head["id"] for head in run["heads"])} for run in state["runs"]]}

    def dossier_check(self, cases, *, currency=None):
        """Adapt identity fields only; all folds and gates are production APIs."""
        original = json.loads((REPO / "examples/empirical-example/dossier.json").read_text(encoding="utf-8"))

        def dossier_for(value):
            dossier = create_initial_dossier("synthetic-result-conformance")
            idea = deepcopy(original["ideas"][0])
            idea.update(id=self.fixture["candidate_id"],
                        version=value.get("candidate_version", self.fixture["candidate_version"]),
                        claims=[{"id": identifier, "candidate_version": 1} for identifier in self.fixture["claims"]])
            dossier["ideas"] = [idea, {**deepcopy(idea), "id": "C-OTHER", "claims": []}]
            for key in ("papers", "searches", "evidence"):
                dossier[key] = deepcopy(original[key])
            dossier["screening"] = []
            for source, target in (("records", "pilots"), ("invalidations", "result_invalidations")):
                dossier[target] = []
                for record in value[source]:
                    fields = deepcopy(record)
                    fields["idea_id"] = fields.pop("candidate_id")
                    fields["idea_version"] = fields.pop("candidate_version")
                    dossier[target].append(fields)
            return dossier

        def add_review(dossier, decision="GO", pilot_ids=None):
            review = deepcopy(original["reviews"][0])
            review.update(id="REVIEW-SYNTHETIC", idea_id=self.fixture["candidate_id"],
                          idea_version=dossier["ideas"][0]["version"],
                          decision_contract_version=DECISION_CONTRACT_VERSION,
                          decision=decision,
                          review_basis_hash=fingerprint_idea(dossier, self.fixture["candidate_id"]))
            if decision == "KILL":
                review["decision_basis"] = {"type": "scientific_refutation", "evidence_ids": [],
                    "pilot_ids": pilot_ids or [], "dependency_names": [], "constraint_keys": [],
                    "explanation": "SYNTHETIC bounded refutation basis"}
            dossier["reviews"] = [review]

        def decision(dossier):
            ranking = rank_dossier(dossier)
            row = next(item for group in ("ranked", "held", "killed") for item in ranking[group]
                       if item["idea_id"] == self.fixture["candidate_id"])
            return {key: row[key] for key in ("decision", "reasons")}

        checked = []
        for value in cases:
            dossier = dossier_for(value)
            validation = validate_dossier(dossier)
            if not validation["valid"]:
                checked.append({"facts": {"valid": False}, "errors": validation["errors"]})
                continue
            state = effective_result_state(dossier, self.fixture["candidate_id"],
                                           value.get("candidate_version", self.fixture["candidate_version"]))
            facts = {"valid": True, **{key: state[key] for key in ("contradiction_blocker",
                "ambiguity_blocker", "requires_hold", "affected_claims_degraded")},
                "scientific_refutation_ids": sorted(state["scientific_refutation_ids"])}
            add_review(dossier)
            go = decision(dossier)
            add_review(dossier, "KILL", [pilot["id"] for pilot in dossier["pilots"]
                if pilot["outcome"] == "contradicted" and pilot["idea_version"] == dossier["ideas"][0]["version"]])
            checked.append({"facts": facts, "warnings": state["warnings"], "go": go,
                            "kill": decision(dossier), "runs": [{"run_id": run["run_id"],
                            "eligible": run["eligible"], "head_ids": sorted(run["head_ids"])} for run in state["runs"]]})
        if currency is None:
            return {"checked": checked}

        empty = dossier_for({"records": [], "invalidations": []})
        add_review(empty)
        before = decision(empty)
        initial_hash = empty["reviews"][0]["review_basis_hash"]
        empty["pilots"] = dossier_for(currency["contradiction"])["pilots"]
        after_record = decision(empty)
        add_review(empty)
        contradicted_hash = empty["reviews"][0]["review_basis_hash"]
        empty["pilots"] = dossier_for(currency["correction"])["pilots"]
        after_correction = decision(empty)
        corrected_hash = fingerprint_idea(empty, self.fixture["candidate_id"])
        add_review(empty)
        after_reassessment = decision(empty)
        invalidated = dossier_for(currency["contradiction"])
        add_review(invalidated)
        pre_invalidation_hash = invalidated["reviews"][0]["review_basis_hash"]
        invalidated["result_invalidations"] = dossier_for(currency["invalidation"])["result_invalidations"]
        after_invalidation = decision(invalidated)
        invalidated_hash = fingerprint_idea(invalidated, self.fixture["candidate_id"])
        add_review(invalidated)
        return {"checked": checked, "currency": {"before": before, "afterRecord": after_record,
            "afterCorrection": after_correction, "afterReassessment": after_reassessment,
            "afterInvalidation": after_invalidation, "invalidationReassessed": decision(invalidated),
            "recordChangedBasis": initial_hash != contradicted_hash,
            "correctionChangedBasis": corrected_hash != contradicted_hash,
            "invalidationChangedBasis": invalidated_hash != pre_invalidation_hash}}

    def test_python_effective_facts_match_independent_frozen_cases(self):
        for case in self.cases:
            with self.subTest(case=case["name"]):
                observed = self.python_check(case)
                self.assertEqual(observed["facts"], case["expected"], observed)
                if case["expected"].get("ambiguity_blocker") or case["expected"].get("affected_claims_degraded"):
                    self.assertTrue(observed["warnings"], "Ambiguity/degradation must be visible")

    def test_both_production_folds_and_ranking_obey_the_same_cases(self):
        dossier = self.dossier_check(self.cases)["checked"]
        self.assertEqual(len(dossier), len(self.cases))
        for case, observed in zip(self.cases, dossier):
            with self.subTest(case=case["name"]):
                self.assertEqual(observed["facts"], case["expected"], observed)
                self.assertEqual(observed["facts"], self.python_check(case)["facts"])
                if not case["expected"]["valid"]:
                    self.assertTrue(observed["errors"])
                    continue
                self.assertEqual(observed["runs"], self.python_check(case)["runs"],
                                 "Causal classification heads and run eligibility must survive adapters")
                self.assertEqual(observed["go"]["decision"], "HOLD" if case["expected"]["requires_hold"] else "GO")
                self.assertEqual(observed["kill"]["decision"],
                    "KILL" if case["expected"]["scientific_refutation_ids"] else "HOLD")
                if case["expected"].get("ambiguity_blocker") or case["expected"].get("affected_claims_degraded"):
                    self.assertTrue(observed["warnings"])

        frozen_heads = {
            "independent_support_cannot_cancel_contradiction": [
                {"run_id": "RUN1", "eligible": True, "head_ids": ["R1"]},
                {"run_id": "RUN2", "eligible": True, "head_ids": ["R2"]}],
            "same_run_visible_correction": [{"run_id": "RUN1", "eligible": True, "head_ids": ["R2"]}],
            "replacement_chain_does_not_revive_ancestor": [{"run_id": "RUN1", "eligible": True, "head_ids": ["R3"]}],
            "supported_children_of_one_contradiction_remain_ambiguous": [
                {"run_id": "RUN1", "eligible": True, "head_ids": ["R2", "R3"]}],
            "later_classification_cannot_revive_invalidated_run": [
                {"run_id": "RUN1", "eligible": False, "head_ids": ["R2"]}],
            "old_candidate_version_remains_historical": [{"run_id": "RUN-NEW", "eligible": True, "head_ids": ["R2"]}],
        }
        for case, observed in zip(self.cases, dossier):
            if case["name"] in frozen_heads:
                with self.subTest(case=case["name"], expected="frozen causal heads"):
                    self.assertEqual(observed["runs"], frozen_heads[case["name"]])

    def test_classification_permutations_do_not_change_effective_facts(self):
        variants = []
        for case in self.cases:
            if not case["expected"]["valid"] or len(case["records"]) < 2:
                continue
            events = self.events_for(case)
            base = [event for event in events if event["type"] not in {"result.record", "result.invalidate"}]
            results = [event for event in events if event["type"] in {"result.record", "result.invalidate"}]
            for ordering in itertools.permutations(results):
                with self.subTest(case=case["name"], ids=[item["data"]["id"] for item in ordering]):
                    checked = self.python_check(case, [*base, *ordering])
                    self.assertEqual(checked["facts"], case["expected"])
                    self.assertEqual(checked["runs"], self.python_check(case)["runs"])
            for ordering in itertools.permutations(case["records"]):
                variant = deepcopy(case)
                variant["records"] = list(ordering)
                variants.append(variant)
        dossier = self.dossier_check(variants)["checked"]
        for case, observed in zip(variants, dossier):
            with self.subTest(case=case["name"], ids=[item["id"] for item in case["records"]]):
                self.assertEqual(observed["facts"], case["expected"], observed)
                self.assertEqual(observed["runs"], self.python_check(case)["runs"])

    def test_dossier_removing_result_gate_never_restores_old_review(self):
        by_name = {case["name"]: case for case in self.cases}
        correction = by_name["same_run_visible_correction"]
        contradiction = deepcopy(correction)
        contradiction["records"] = contradiction["records"][:1]
        result = self.dossier_check([], currency={"contradiction": contradiction,
            "correction": correction, "invalidation": by_name["invalidation_withdraws_whole_run"]})["currency"]
        self.assertEqual(result["before"]["decision"], "GO", "Positive ranking control is necessary")
        for field in ("afterRecord", "afterCorrection", "afterInvalidation"):
            self.assertEqual(result[field]["decision"], "HOLD")
            self.assertTrue(any("stale" in reason.lower() for reason in result[field]["reasons"]))
        self.assertEqual(result["afterReassessment"]["decision"], "GO")
        self.assertEqual(result["invalidationReassessed"]["decision"], "GO")
        for field in ("recordChangedBasis", "correctionChangedBasis", "invalidationChangedBasis"):
            self.assertTrue(result[field], field)

    def test_dossier_legacy_migration_preserves_contradiction_and_record_identity(self):
        legacy = json.loads((REPO / "examples/empirical-example/dossier.json").read_text(encoding="utf-8"))
        legacy.update(schema_version=2, decision_contract_version=2)
        for review in legacy["reviews"]:
            review["decision_contract_version"] = 2
        legacy.pop("result_invalidations", None)
        idea_id = legacy["ideas"][0]["id"]
        legacy["pilots"] = [
            {"id": "EV-000003", "idea_id": idea_id, "idea_version": 1, "kind": "scientific", "outcome": "contradicted",
             "artifacts": ["SYNTHETIC-result.json"], "summary": "SYNTHETIC legacy contradiction", "limitations": ["Invented fixture only"]},
            {"id": "LEGACY-SUPPORT", "idea_id": idea_id, "idea_version": 1, "kind": "scientific", "outcome": "supported",
             "artifacts": ["SYNTHETIC-support.json"], "summary": "SYNTHETIC independent support", "limitations": ["Invented fixture only"]}]
        before = deepcopy(legacy)
        migrated = migrate_dossier(legacy)
        state = effective_result_state(migrated, idea_id, 1)
        extra = deepcopy(legacy)
        extra["result_invalidations"] = [{"id": "IGNORED-LEGACY-INV", "run_id": "EV-000003", "idea_id": idea_id,
            "idea_version": 1, "result_id": "EV-000003", "reason": "SYNTHETIC previously uninterpreted field",
            "recorded_at": STAMP, "actor": "user", "trust": "T1"}]
        with self.assertRaisesRegex(ValueError, "(?i)legacy|invalidation"):
            migrate_dossier(extra)
        value = {"legacyValid": validate_dossier(legacy)["valid"], "legacyInputUnchanged": legacy == before,
            "migratedValid": validate_dossier(migrated)["valid"], "schemaVersion": migrated["schema_version"],
            "contractVersion": migrated["decision_contract_version"], "runIds": [pilot["run_id"] for pilot in migrated["pilots"]],
            "pilotIds": [pilot["id"] for pilot in migrated["pilots"]], "artifacts": [pilot["artifacts"] for pilot in migrated["pilots"]],
            "invalidations": migrated["result_invalidations"], "reviewCount": len(migrated["reviews"]),
            "archivedReviews": [item["original_review"] for item in migrated["history"] if "original_review" in item],
            "originalReviews": legacy["reviews"], "blocker": state["contradiction_blocker"],
            "extraLegacyReadable": validate_dossier(extra)["valid"]}
        self.assertTrue(value["legacyValid"])
        self.assertTrue(value["legacyInputUnchanged"])
        self.assertTrue(value["migratedValid"])
        self.assertEqual(value["schemaVersion"], 3)
        self.assertEqual(value["contractVersion"], 3)
        self.assertEqual(value["runIds"], ["EV-000003", "LEGACY-SUPPORT"])
        self.assertEqual(value["pilotIds"], value["runIds"])
        self.assertEqual(value["artifacts"], [["SYNTHETIC-result.json"], ["SYNTHETIC-support.json"]])
        self.assertEqual(value["invalidations"], [])
        self.assertEqual(value["reviewCount"], 0)
        self.assertEqual(value["archivedReviews"], value["originalReviews"])
        self.assertTrue(value["blocker"], "Migration cannot erase a legacy contradiction")
        self.assertTrue(value["extraLegacyReadable"])

    def test_python_assessment_and_projection_preserve_effective_results(self):
        """Run real private writes, assess/finalize and the production export."""
        with tempfile.TemporaryDirectory(prefix="mentor-result-production-") as directory:
            judgment = Judgment(Ledger(directory, clock=lambda: STAMP))
            judgment.upsert_candidate(synthetic_candidate())
            initial = judgment.assess("C-SYNTHETIC", reason="SYNTHETIC missing inputs honestly yield HOLD")
            judgment.record_decision(initial["review_id"], "HOLD", "SYNTHETIC actual test instruction", human=True)
            data = deepcopy(self.fixture["record_defaults"])
            for key in ("actor", "trust", "recorded_at"):
                data.pop(key)
            artifact = Path(directory) / "SYNTHETIC-result.json"
            artifact.write_text('{"synthetic":true,"finding":null}\n', encoding="utf-8")
            data.update(id="R-PRODUCTION", run_id="RUN-PRODUCTION", outcome="contradicted", artifacts=[str(artifact)])
            recorded = judgment.record_result(data)
            after_record = judgment.finalize("C-SYNTHETIC")
            self.assertTrue(after_record["assessment_required"])
            self.assertEqual(after_record["approval_status"], "pending_human")
            self.assertIsNone(after_record["human_decision"])
            contradicted = judgment.assess("C-SYNTHETIC", reason="SYNTHETIC contradiction requires HOLD")
            self.assertEqual(contradicted["machine_recommendation"], "HOLD")
            self.assertTrue(judgment.results("C-SYNTHETIC")["contradiction_blocker"])
            judgment.reclassify_result(recorded["id"], "supported", reason="SYNTHETIC explicit interpretation correction")
            corrected_state = judgment.results("C-SYNTHETIC")
            self.assertFalse(corrected_state["requires_hold"])
            self.assertTrue(judgment.finalize("C-SYNTHETIC")["assessment_required"])
            correction_review = judgment.assess("C-SYNTHETIC", reason="SYNTHETIC remaining missing inputs still HOLD")
            self.assertEqual(correction_review["machine_recommendation"], "HOLD")
            judgment.invalidate_result(recorded["id"], "SYNTHETIC entire attempt invalidated", human=True)
            self.assertTrue(judgment.finalize("C-SYNTHETIC")["assessment_required"])
            exported = judgment.export_dossier()
            self.assertEqual(exported["schema_version"], 3)
            self.assertEqual(len(exported["pilots"]), 2)
            self.assertEqual(len(exported["result_invalidations"]), 1)
            self.assertEqual(exported["reviews"], [], "Ledger approval cannot transfer to dossier")
            validation = validate_dossier(exported)
            value = {"validation": validation, "state": effective_result_state(exported, "C-SYNTHETIC", 1) if validation["valid"] else None,
                     "ranking": rank_dossier(exported) if validation["valid"] else None}
            self.assertTrue(value["validation"]["valid"], value["validation"])
            expected = python_facts(judgment.results("C-SYNTHETIC"))
            actual = value["state"]
            self.assertEqual(expected, {"valid": True, **{key: actual[key] for key in expected if key != "valid"}})
            self.assertEqual(value["ranking"]["ranked"], [])
            self.assertEqual(value["ranking"]["held"][0]["decision"], "HOLD")

    def test_cli_migration_emits_reassessment_without_overwriting_legacy_input(self):
        legacy = json.loads((REPO / "examples/empirical-example/dossier.json").read_text(encoding="utf-8"))
        legacy["schema_version"] = 1
        for key in ("screening", "decision_contract_version", "result_invalidations"):
            legacy.pop(key)
        for idea in legacy["ideas"]:
            idea.pop("evidence_links")
        for review in legacy["reviews"]:
            review["basis_hash"] = review["review_basis_hash"]
            for key in ("review_basis_hash", "decision_scope", "recommended_stage", "decision_basis", "decision_contract_version"):
                review.pop(key)
        self.assertTrue(validate_dossier(legacy)["valid"])
        with tempfile.TemporaryDirectory(prefix="mentor-legacy-cli-") as directory:
            file = Path(directory) / "legacy.json"
            file.write_text(json.dumps(legacy, ensure_ascii=False), encoding="utf-8")
            original_bytes = file.read_bytes()
            process = subprocess.run([sys.executable, "-B", str(REPO / "skills/ai-research-mentor/scripts/research_audit.py"), "migrate", str(file)],
                env={**os.environ, "PATH": str(Path(directory) / "no-executables")}, capture_output=True, timeout=20)
            self.assertEqual(process.returncode, 0, process.stderr.decode("utf-8", errors="replace"))
            migrated = json.loads(process.stdout.decode("utf-8"))
            self.assertTrue(validate_dossier(migrated)["valid"])
            self.assertEqual(migrated["schema_version"], 3)
            self.assertEqual(migrated["reviews"], [])
            self.assertEqual([row["original_review"] for row in migrated["history"]], legacy["reviews"])
            self.assertEqual(rank_dossier(migrated)["ranked"], [])
            self.assertEqual(file.read_bytes(), original_bytes)


if __name__ == "__main__":
    unittest.main(verbosity=2)
