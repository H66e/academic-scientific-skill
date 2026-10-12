"""Offline SYNTHETIC dossier contracts; no scientific effectiveness is asserted."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

SKILL = Path(__file__).resolve().parents[2]
REPO = SKILL.parents[1]
sys.path.insert(0, str(SKILL / "runtime"))
from research_mentor.audit import (
    canonical_stringify, create_initial_dossier, create_review_receipt,
    effective_result_state, fingerprint_idea, init_project, migrate_dossier,
    rank_dossier, ranking_config_hash, validate_dossier, verify_independent_receipts,
)

STAMP = "2026-10-10T00:00:00Z"
EXAMPLE = REPO / "examples" / "empirical-example" / "dossier.json"


def fixture():
    dossier = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    dossier["reviews"] = []
    dossier["pilots"] = []
    dossier["result_invalidations"] = []
    add_review(dossier)
    return dossier


def add_review(dossier, **changes):
    template = json.loads(EXAMPLE.read_text(encoding="utf-8"))["reviews"][0]
    idea = dossier["ideas"][0]
    template.update({"id": f"REVIEW-{len(dossier['reviews']) + 1}", "idea_id": idea["id"],
                     "idea_version": idea["version"], "reviewed_at": STAMP,
                     "review_basis_hash": fingerprint_idea(dossier, idea["id"]), **changes})
    dossier["reviews"].append(template)
    return template


def refresh(dossier):
    for review in dossier["reviews"]:
        review["review_basis_hash"] = fingerprint_idea(dossier, review["idea_id"])
        review["idea_version"] = next(idea["version"] for idea in dossier["ideas"] if idea["id"] == review["idea_id"])


def result(dossier, identifier="A", **changes):
    idea = dossier["ideas"][0]
    value = {"id": identifier, "run_id": identifier, "idea_id": idea["id"], "idea_version": idea["version"],
             "kind": "scientific", "outcome": "contradicted", "artifacts": ["SYNTHETIC-only.csv"],
             "summary": "SYNTHETIC declaration, no real experiment", "limitations": ["Fictional test"],
             "affected_claims": [], "actor": "model", "trust": "T2", **changes}
    dossier["pilots"].append(value)
    return value


def retire(dossier, observed):
    value = {"id": "INV-1", "run_id": observed["run_id"], "idea_id": observed["idea_id"],
             "idea_version": observed["idea_version"], "result_id": observed["id"],
             "reason": "SYNTHETIC run invalidity", "recorded_at": STAMP, "actor": "user", "trust": "T1"}
    dossier["result_invalidations"].append(value)
    return value


def independent(dossier, **changes):
    return add_review(dossier, **{"kind": "independent", "author_context": "SYNTHETIC author",
                      "evaluator_context": "SYNTHETIC separate evaluator", "artifact": "receipt.json",
                      "recommended_stage": "full_validation", "reviewed_at": "2026-10-10T01:00:00Z", **changes})


def seal(root, peer, receipt=None):
    data = (json.dumps(receipt if receipt is not None else create_review_receipt(peer), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    (Path(root) / peer["artifact"]).write_bytes(data)
    peer["artifact_sha256"] = hashlib.sha256(data).hexdigest()


def frozen_audit_batch(values):
    """Previously observed source responses; never regenerate from the runtime."""
    baseline = json.loads((REPO / "evaluation/fixtures/native-runtime-baseline.json").read_text(encoding="utf-8"))
    if baseline.get("synthetic") is not True:
        raise AssertionError("Contract baselines must be explicitly synthetic")
    encoded = json.dumps(values, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()
    key = hashlib.sha256(encoded).hexdigest()
    matches = [row for row in baseline["contracts"]["audit"] if row["inputs_sha256"] == key]
    if len(matches) != 1:
        raise AssertionError("Public synthetic inputs changed: review the contract rather than deriving expected output")
    if len(matches[0]["expected"]) != len(values):
        raise AssertionError("Frozen responses must cover every declared input")
    return matches[0]["expected"]


def snapshot(dossier):
    return {"validation": validate_dossier(dossier), "rank": rank_dossier(dossier),
            "hashes": [fingerprint_idea(dossier, idea["id"]) for idea in dossier["ideas"]],
            "config": ranking_config_hash(dossier),
            "states": [effective_result_state(dossier, idea["id"]) for idea in dossier["ideas"]] if dossier["schema_version"] == 3 else []}


def add_unrelated(dossier):
    """Separate public synthetic candidate; no shared provenance is invented."""
    paper = deepcopy(dossier["papers"][0])
    paper.update(id="P2", title="SYNTHETIC other paper", version="fixture-v2")
    search = deepcopy(dossier["searches"][0])
    search.update(id="S2", query="SYNTHETIC unrelated search", result_paper_ids=["P2"])
    evidence = deepcopy(dossier["evidence"][0])
    evidence.update(id="E2", paper_id="P2", observation="SYNTHETIC unrelated observation")
    idea = deepcopy(dossier["ideas"][0])
    idea.update(id="I2", title="SYNTHETIC other candidate", evidence_ids=["E2"], search_ids=["S2"])
    for link in idea["evidence_links"]:
        link["evidence_id"] = "E2"
    for nearest in idea["nearest_work"]:
        nearest.update(paper_id="P2", evidence_ids=["E2"])
    dossier["papers"].append(paper)
    dossier["searches"].append(search)
    dossier["evidence"].append(evidence)
    dossier["ideas"].append(idea)
    dossier["screening"].append({"id": "SC2", "search_id": "S2", "paper_id": "P2", "idea_ids": ["I2"],
        "stage": "full_text", "decision": "include", "reason": "SYNTHETIC unrelated relevance", "screened_at": STAMP})
    result(dossier, "X2", idea_id="I2", outcome="supported")
    return dossier


def behavior_fixture():
    dossier = fixture()
    dossier["screening"] = []
    refresh(dossier)
    return dossier


class DossierBehaviorTests(unittest.TestCase):
    """Independent assertions for behavior previously checked by the old suite."""

    def test_weights_change_order_and_scores_without_expiring_scientific_reviews(self):
        dossier = add_unrelated(behavior_fixture())
        add_review(dossier, idea_id="I2", decision_basis={"type": "advance", "evidence_ids": ["E2"],
            "pilot_ids": [], "dependency_names": [], "constraint_keys": [], "explanation": "SYNTHETIC I2 basis"})
        refresh(dossier)
        dossier["reviews"][0]["scores"] = {"scientific_value": 4, "differentiation": 1, "testability": 1}
        dossier["reviews"][1]["scores"] = {"scientific_value": 1, "differentiation": 4, "testability": 4}
        scientific = fingerprint_idea(dossier, "I1")
        config = ranking_config_hash(dossier)
        for weights, first_id, score in (([80, 10, 10], "I1", 85), ([10, 80, 10], "I2", 92.5)):
            dossier["config"]["ranking_weights"] = dict(zip(("scientific_value", "differentiation", "testability"), weights))
            ranked = rank_dossier(dossier)
            self.assertEqual(fingerprint_idea(dossier, "I1"), scientific)
            self.assertNotEqual(ranking_config_hash(dossier), config)
            self.assertEqual((ranked["ranked"][0]["idea_id"], ranked["ranked"][0]["score"]), (first_id, score))
            self.assertEqual(ranked["held"], [])

    def test_penalties_clamp_at_zero_and_negative_penalties_are_invalid(self):
        dossier = behavior_fixture()
        for key in dossier["reviews"][0]["scores"]:
            dossier["reviews"][0]["scores"][key] = 4
        for points, score in ((10, 90), (150, 0)):
            dossier["reviews"][0]["penalties"] = [{"points": points, "reason": "SYNTHETIC limitation"}]
            self.assertEqual(rank_dossier(dossier)["ranked"][0]["score"], score)
        dossier["reviews"][0]["penalties"][0]["points"] = -10
        self.assertFalse(validate_dossier(dossier)["valid"])
        with self.assertRaisesRegex(ValueError, "Invalid dossier"):
            rank_dossier(dossier)

    def test_confidence_is_explained_uncertainty_and_never_a_hidden_score_multiplier(self):
        dossier = behavior_fixture()
        dossier["reviews"][0].update(confidence={"scientific_value": "low", "differentiation": "medium", "testability": "high"},
            confidence_reasons={key: "SYNTHETIC uncertainty" for key in ("scientific_value", "differentiation", "testability")})
        validation = validate_dossier(dossier)
        self.assertTrue(validation["valid"], validation["errors"])
        self.assertTrue(validation["warnings"])
        self.assertEqual(rank_dossier(dossier)["ranked"][0]["score"], 50)
        for alteration in ("missing-reasons", "missing-dimension", "invalid-confidence"):
            changed = deepcopy(dossier)
            if alteration == "missing-reasons":
                changed["reviews"][0].pop("confidence_reasons")
            elif alteration == "missing-dimension":
                changed["reviews"][0]["confidence"].pop("testability")
            else:
                changed["reviews"][0]["confidence"]["scientific_value"] = "certain"
            with self.subTest(alteration=alteration):
                self.assertFalse(validate_dossier(changed)["valid"])

    def test_unknown_scores_and_explicit_hold_cannot_be_overridden_by_high_scores(self):
        for alteration in ("unknown-score", "hold", "unsupported-kill", "no-review"):
            dossier = behavior_fixture()
            if alteration == "unknown-score":
                dossier["reviews"][0]["scores"]["scientific_value"] = None
            elif alteration == "no-review":
                dossier["reviews"] = []
                dossier["ideas"][0]["novelty"]["status"] = "duplicate"
            else:
                dossier["reviews"][0]["decision"] = "HOLD" if alteration == "hold" else "KILL"
                dossier["reviews"][0]["decision_basis"]["type"] = "insufficient"
            with self.subTest(alteration=alteration):
                ranking = rank_dossier(dossier)
                self.assertEqual(ranking["ranked"], [])
                self.assertEqual(ranking["killed"], [])
                self.assertEqual(len(ranking["held"]), 1)

    def test_unrelated_records_and_their_edits_do_not_expire_another_candidate(self):
        dossier = behavior_fixture()
        before = fingerprint_idea(dossier, "I1")
        add_unrelated(dossier)
        self.assertTrue(validate_dossier(dossier)["valid"])
        self.assertEqual(fingerprint_idea(dossier, "I1"), before)
        dossier["papers"][1]["version"] = "fixture-v3"
        dossier["searches"][1]["limitations"].append("SYNTHETIC changed other coverage")
        dossier["evidence"][1]["observation"] = "SYNTHETIC revised other observation"
        dossier["pilots"][0]["summary"] = "SYNTHETIC changed other attempt"
        dossier["screening"][0]["decision"] = "uncertain"
        self.assertEqual(fingerprint_idea(dossier, "I1"), before)
        self.assertEqual(rank_dossier(dossier)["ranked"][0]["idea_id"], "I1")

    def test_collection_order_history_and_project_labels_preserve_the_scoped_fingerprint(self):
        dossier = add_unrelated(behavior_fixture())
        before = fingerprint_idea(dossier, "I1")
        for key in ("papers", "searches", "evidence", "ideas", "screening", "pilots", "result_invalidations"):
            dossier[key].reverse()
        dossier["project"]["id"] = "renamed-synthetic-project"
        dossier["history"].append({"event": "SYNTHETIC archival note"})
        self.assertEqual(fingerprint_idea(dossier, "I1"), before)
        self.assertEqual(canonical_stringify({"b": 2, "a": 1}), canonical_stringify({"a": 1, "b": 2}))

    def test_administrative_times_do_not_expire_reviews_but_search_dates_do(self):
        dossier = behavior_fixture()
        dossier["screening"].append({"id": "SC1", "search_id": "S1", "paper_id": "P1", "idea_ids": ["I1"],
            "stage": "full_text", "decision": "include", "reason": "SYNTHETIC relevance", "screened_at": STAMP})
        refresh(dossier)
        before = fingerprint_idea(dossier, "I1")
        dossier["papers"][0]["accessed_at"] = "2026-10-11T00:00:00Z"
        dossier["screening"][0]["screened_at"] = "2026-10-11T00:00:00Z"
        self.assertEqual(fingerprint_idea(dossier, "I1"), before)
        self.assertEqual(len(rank_dossier(dossier)["ranked"]), 1)
        dossier["searches"][0]["searched_at"] = "2026-10-11T00:00:00Z"
        self.assertNotEqual(fingerprint_idea(dossier, "I1"), before)
        self.assertEqual(rank_dossier(dossier)["ranked"], [])

    def test_search_evidence_and_screening_paths_each_extend_the_candidate_closure(self):
        for association in ("search-result", "evidence-link", "screening-link"):
            dossier = add_unrelated(behavior_fixture())
            before = fingerprint_idea(dossier, "I1")
            if association == "search-result":
                dossier["searches"][0]["result_paper_ids"].append("P2")
            elif association == "evidence-link":
                dossier["ideas"][0]["evidence_ids"].append("E2")
                dossier["ideas"][0]["evidence_links"].append({"evidence_id": "E2", "role": "context", "target": "problem",
                    "claim": "SYNTHETIC additional context", "relation": "context", "decision_relevant": False})
            else:
                dossier["screening"][0]["idea_ids"].append("I1")
            with self.subTest(association=association):
                associated = fingerprint_idea(dossier, "I1")
                self.assertNotEqual(associated, before)
                dossier["papers"][1]["version"] = "changed-public-synthetic-version"
                self.assertNotEqual(fingerprint_idea(dossier, "I1"), associated)

    def test_sharing_screening_preserves_original_basis_but_changing_inclusion_expires_it(self):
        dossier = add_unrelated(behavior_fixture())
        screening = {"id": "SC1", "search_id": "S1", "paper_id": "P1", "idea_ids": ["I1"], "stage": "full_text",
            "decision": "include", "reason": "SYNTHETIC relevance", "screened_at": STAMP}
        dossier["screening"].append(screening)
        refresh(dossier)
        before = fingerprint_idea(dossier, "I1")
        screening["idea_ids"].append("I2")
        self.assertEqual(fingerprint_idea(dossier, "I1"), before)
        results = deepcopy(dossier["searches"][0]["result_paper_ids"])
        screening["decision"] = "uncertain"
        self.assertNotEqual(fingerprint_idea(dossier, "I1"), before)
        self.assertEqual(dossier["searches"][0]["result_paper_ids"], results)

    def test_changed_scientific_inputs_expire_even_without_manual_version_change(self):
        paths = [("ideas", 0, "question"), ("ideas", 0, "nearest_work", 0, "delta"),
                 ("ideas", 0, "evidence_links", 0, "claim"), ("evidence", 0, "observation"),
                 ("evidence", 0, "version"), ("papers", 0, "version")]
        for path in paths:
            dossier = behavior_fixture()
            pointer = dossier
            for key in path[:-1]:
                pointer = pointer[key]
            pointer[path[-1]] = "SYNTHETIC changed scientific input"
            with self.subTest(path=path):
                self.assertEqual(dossier["ideas"][0]["version"], 1)
                ranked = rank_dossier(dossier)
                self.assertEqual(ranked["ranked"], [])
                self.assertTrue(any("stale" in reason.lower() for reason in ranked["held"][0]["reasons"]))
        dossier = behavior_fixture()
        dossier["project"]["constraints"]["budget"]["value"] = 0
        self.assertEqual(rank_dossier(dossier)["ranked"], [])

    def test_latest_stale_or_legacy_review_cannot_fall_back_to_an_older_go(self):
        for alteration in ("hash", "contract"):
            dossier = behavior_fixture()
            latest = add_review(dossier, reviewed_at="2026-10-10T01:00:00Z")
            latest["review_basis_hash" if alteration == "hash" else "decision_contract_version"] = "0" * 64 if alteration == "hash" else 1
            with self.subTest(alteration=alteration):
                self.assertEqual(rank_dossier(dossier)["ranked"], [])
                if alteration == "contract":
                    before = deepcopy(dossier)
                    migrated = migrate_dossier(dossier)
                    self.assertEqual(migrated["reviews"], [])
                    self.assertEqual([row["original_review"] for row in migrated["history"]], before["reviews"])
                    self.assertEqual(dossier, before)
                    self.assertEqual(migrate_dossier(migrated), migrated)

    def test_newer_current_review_survives_older_legacy_review_migration(self):
        dossier = behavior_fixture()
        dossier["reviews"][0]["decision_contract_version"] = 1
        latest = add_review(dossier, reviewed_at="2026-10-10T01:00:00Z")
        migrated = migrate_dossier(dossier)
        self.assertEqual(migrated["reviews"], [latest])
        self.assertEqual(len(rank_dossier(migrated)["ranked"]), 1)
        self.assertEqual(migrated["history"][0]["original_review"], dossier["reviews"][0])

    def test_theory_measurement_and_reproduction_can_use_deep_problem_contradictions(self):
        for research_type in ("theoretical", "measurement", "reproduction"):
            dossier = behavior_fixture()
            dossier["ideas"][0]["research_type"] = research_type
            dossier["evidence"][0]["polarity"] = "contradicts"
            dossier["ideas"][0]["evidence_links"][0].update(role="contradiction", target="problem", relation="contradicts",
                claim="SYNTHETIC flaw in an existing formulation motivates this different candidate")
            refresh(dossier)
            with self.subTest(research_type=research_type):
                self.assertEqual(len(rank_dossier(dossier)["ranked"]), 1)
        dossier = behavior_fixture()
        dossier["ideas"][0]["research_type"] = "theoretical"
        dossier["evidence"][0]["polarity"] = "context"
        dossier["ideas"][0]["evidence_links"][0]["relation"] = "context"
        refresh(dossier)
        self.assertEqual(len(rank_dossier(dossier)["ranked"]), 1)

    def test_scoped_decision_references_and_unrelated_errors_aggregate(self):
        for field, value in (("evidence_ids", ["E2"]), ("pilot_ids", ["X2"]),
                             ("dependency_names", ["missing"]), ("constraint_keys", ["missing"])):
            dossier = add_unrelated(behavior_fixture())
            dossier["reviews"][0]["decision_basis"][field] = value
            with self.subTest(field=field):
                self.assertFalse(validate_dossier(dossier)["valid"])
        for collection in ("screening", "searches", "papers", "evidence", "pilots"):
            dossier = add_unrelated(behavior_fixture())
            dossier["reviews"][0]["decision_basis"]["evidence_ids"] = ["E2"]
            dossier[collection].append(None)
            with self.subTest(collection=collection):
                validation = validate_dossier(dossier)
                self.assertFalse(validation["valid"])
                self.assertIn("Evidence E2 is not attached to this candidate", "\n".join(validation["errors"]))
                with self.assertRaisesRegex(ValueError, "Invalid dossier"):
                    rank_dossier(dossier)

    def test_historical_decision_basis_remains_readable_but_never_authorizes_changed_links(self):
        dossier = add_unrelated(behavior_fixture())
        idea = dossier["ideas"][0]
        idea.update(evidence_ids=["E2"], search_ids=["S2"], evidence_links=[{**idea["evidence_links"][0], "evidence_id": "E2"}],
                    nearest_work=[{**idea["nearest_work"][0], "paper_id": "P2", "evidence_ids": ["E2"]}])
        self.assertTrue(validate_dossier(dossier)["valid"])
        self.assertEqual(dossier["reviews"][0]["decision_basis"]["evidence_ids"], ["E1"])
        self.assertEqual(rank_dossier(dossier)["ranked"], [])

    def test_candidate_evidence_and_screening_references_cannot_borrow_other_scope(self):
        dossier = add_unrelated(behavior_fixture())
        dossier["ideas"][0]["evidence_links"][0]["evidence_id"] = "E2"
        self.assertFalse(validate_dossier(dossier)["valid"])
        for change in ({"search_id": "missing"}, {"paper_id": "missing"}, {"idea_ids": ["missing"]},
                       {"stage": "imagined-reading"}, {"decision": "possibly"}, {"paper_id": "P2"}):
            dossier = add_unrelated(behavior_fixture())
            dossier["screening"].append({"id": "SC1", "search_id": "S1", "paper_id": "P1", "idea_ids": ["I1"],
                "stage": "metadata", "decision": "uncertain", "reason": "SYNTHETIC uncertainty", "screened_at": STAMP, **change})
            with self.subTest(change=change):
                self.assertFalse(validate_dossier(dossier)["valid"])

    def test_warning_only_records_do_not_become_invalid_or_bypass_gates(self):
        dossier = behavior_fixture()
        dossier["evidence"][0].update(read_scope="full_text", locator="paper")
        validation = validate_dossier(dossier)
        self.assertTrue(validation["valid"])
        self.assertTrue(validation["warnings"])
        dossier = behavior_fixture()
        dossier["screening"].append({"id": "SC1", "search_id": "S1", "paper_id": "P1", "idea_ids": ["I1"],
            "stage": "full_text", "decision": "exclude", "reason": "SYNTHETIC exclusion requires reconciliation", "screened_at": STAMP})
        validation = validate_dossier(dossier)
        self.assertTrue(validation["valid"])
        self.assertTrue(validation["warnings"])
        dossier["ideas"] = [None]
        validation = validate_dossier(dossier)
        self.assertFalse(validation["valid"])
        self.assertGreaterEqual(len(validation["errors"]), 2)

    def test_unrelated_preferences_or_a_label_do_not_justify_constraints_kill(self):
        for alteration in ("met", "empty-binding", "missing-binding", "unrelated-preference", "unconfirmed"):
            dossier = behavior_fixture()
            dossier["project"]["constraints"].update(compute={"status": "confirmed", "value": 0, "source": "SYNTHETIC resource"},
                format={"status": "confirmed", "value": "Markdown", "source": "SYNTHETIC preference"})
            dossier["ideas"][0]["feasibility"]["status"] = "blocked"
            dependency = dossier["ideas"][0]["feasibility"]["dependencies"][0]
            dependency.update(status="failed", constraint_keys=["compute"])
            review = dossier["reviews"][0]
            review.update(decision="KILL", decision_scope="current_constraints")
            review["decision_basis"].update(type="constraints", constraint_keys=["compute"], dependency_names=[dependency["name"]])
            if alteration == "met":
                dependency["status"] = "met"
            elif alteration == "empty-binding":
                dependency["constraint_keys"] = []
            elif alteration == "missing-binding":
                dependency.pop("constraint_keys")
            elif alteration == "unrelated-preference":
                review["decision_basis"]["constraint_keys"] = ["format"]
            else:
                dossier["project"]["constraints"]["compute"]["status"] = "unknown"
            refresh(dossier)
            with self.subTest(alteration=alteration):
                ranking = rank_dossier(dossier)
                self.assertEqual(ranking["killed"], [])
                self.assertEqual(len(ranking["held"]), 1)

    def test_latest_peer_phase_and_hold_supersede_an_older_verified_full_approval(self):
        with tempfile.TemporaryDirectory(prefix="mentor-peer-order-") as root:
            for stage, decision in (("pilot", "GO"), ("full_validation", "HOLD")):
                dossier = behavior_fixture()
                first = independent(dossier)
                seal(root, first)
                later = independent(dossier, artifact="later.json", recommended_stage=stage, decision=decision)
                seal(root, later)
                add_review(dossier, recommended_stage="full_validation", reviewed_at="2026-10-10T02:00:00Z")
                verified = verify_independent_receipts(dossier, root=root)
                self.assertEqual(len(verified["verified"]), 2)
                self.assertEqual(rank_dossier(dossier, receipt_verification=verified)["ranked"], [])

    def test_peer_legacy_migration_never_revives_an_older_full_approval(self):
        with tempfile.TemporaryDirectory(prefix="mentor-peer-migration-") as root:
            dossier = behavior_fixture()
            first = independent(dossier)
            seal(root, first)
            blocker = independent(dossier, artifact="legacy.json", decision="HOLD", decision_contract_version=1,
                                  reviewed_at="2026-10-10T02:00:00Z")
            latest = add_review(dossier, recommended_stage="full_validation", reviewed_at="2026-10-10T03:00:00Z")
            before = deepcopy(dossier)
            self.assertEqual(rank_dossier(dossier, receipt_verification=verify_independent_receipts(dossier, root=root))["ranked"], [])
            migrated = migrate_dossier(dossier)
            self.assertEqual(migrated["reviews"], [dossier["reviews"][0], latest])
            self.assertEqual([row["original_review"] for row in migrated["history"]], [first, blocker])
            self.assertEqual(rank_dossier(migrated, receipt_verification=verify_independent_receipts(migrated, root=root))["ranked"], [])
            self.assertEqual(dossier, before)

    def test_source_notes_type_errors_aggregate_with_other_record_errors(self):
        for notes in ("unstructured", [], None, 3):
            dossier = behavior_fixture()
            dossier["project"]["notes"] = notes
            dossier["papers"][0]["year"] = True
            with self.subTest(notes=notes):
                validation = validate_dossier(dossier)
                self.assertFalse(validation["valid"])
                self.assertIn("project.notes", "\n".join(validation["errors"]))
                self.assertIn("year", "\n".join(validation["errors"]))

    def test_new_contract_fields_require_valid_enums_references_and_explanations(self):
        changes = [(('reviews', 0, 'decision_scope'), 'whole-field'),
                   (('reviews', 0, 'recommended_stage'), 'publication'),
                   (('reviews', 0, 'decision_basis', 'type'), 'automatic-truth'),
                   (('reviews', 0, 'decision_basis', 'explanation'), ''),
                   (('ideas', 0, 'evidence_links', 0, 'target'), 'whole-field'),
                   (('ideas', 0, 'evidence_links', 0, 'role'), 'ground-truth'),
                   (('ideas', 0, 'evidence_links', 0, 'relation'), 'proves'),
                   (('ideas', 0, 'evidence_links', 0, 'decision_relevant'), 'yes'),
                   (('reviews', 0, 'scores', 'testability'), 5),
                   (('reviews', 0, 'scores', 'testability'), 1.5),
                   (('reviews', 0, 'reviewed_at'), '2026-10-10'),
                   (('config', 'ranking_weights'), {'scientific_value': 0, 'differentiation': 0, 'testability': 0}),
                   (('config', 'ranking_weights', 'testability'), -1)]
        for path, replacement in changes:
            dossier = behavior_fixture()
            pointer = dossier
            for key in path[:-1]:
                pointer = pointer[key]
            pointer[path[-1]] = replacement
            with self.subTest(path=path, replacement=replacement):
                self.assertFalse(validate_dossier(dossier)["valid"])

    def test_theoretical_validation_needs_a_proof_obligation_without_invented_gpu_constraints(self):
        dossier = behavior_fixture()
        dossier["project"].update(research_type="theoretical", constraints={})
        dossier["ideas"][0]["research_type"] = "theoretical"
        dossier["ideas"][0]["validation"]["metric"] = "SYNTHETIC proof obligation or counterexample"
        refresh(dossier)
        self.assertEqual(len(rank_dossier(dossier)["ranked"]), 1)


class AuditContractTests(unittest.TestCase):
    def test_existing_examples_exact_hashes_rank_and_validation(self):
        dossiers = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((REPO / "examples").glob("*/dossier.json"))]
        expected = frozen_audit_batch([{"command": "snapshot", "value": value} for value in dossiers])
        for dossier, baseline in zip(dossiers, expected):
            with self.subTest(project=dossier["project"]["id"]):
                self.assertEqual(snapshot(dossier), baseline["value"])

    def test_canonical_numeric_unicode_and_rejection_boundaries(self):
        values = [None, True, {"10": "ten", "2": "two", "01": 0, "4294967295": "non-index"},
                  {"\ue000": "BMP", "\U00010000": "astral", "中文": "source"},
                  [0, -0.0, 2.0, 1e-7, 1e-6, 1e20, 1e21, 1e23, 0.0000123, 1.2345678901234567, 5e-324],
                  {"surrogate": "\ud800", "paired": "\ud83d\ude00"}, [9007199254740993, 1000000000000000100],
                  [{"nested": ["\n", "\t", "é", "\u2028"]}]]
        expected = frozen_audit_batch([{"command": "canonical", "value": value} for value in values])
        for value, baseline in zip(values, expected):
            with self.subTest(value=repr(value)):
                self.assertEqual(canonical_stringify(value), baseline["value"])
        for value in (float("nan"), float("inf"), object(), {1: "non-string"}):
            with self.assertRaises(ValueError):
                canonical_stringify(value)
        cycle = []
        cycle.append(cycle)
        with self.assertRaisesRegex(ValueError, "Circular"):
            canonical_stringify(cycle)
        shared = {"same": 1}
        self.assertEqual(canonical_stringify([shared, shared]), '[{"same":1},{"same":1}]')

    def test_all_frozen_lifecycle_cases_match_baseline(self):
        neutral = json.loads((REPO / "evaluation" / "fixtures" / "result-lifecycle.json").read_text(encoding="utf-8"))
        inputs = []
        for case in neutral["cases"]:
            dossier = fixture()
            idea = dossier["ideas"][0]
            idea.update(id=neutral["candidate_id"], version=case.get("candidate_version", neutral["candidate_version"]),
                        claims=[{"id": value, "candidate_version": 1} for value in neutral["claims"]])
            dossier["reviews"], dossier["screening"] = [], []
            dossier["ideas"].append({**deepcopy(idea), "id": "C-OTHER", "claims": []})
            for field, defaults in (("pilots", "record_defaults"), ("result_invalidations", "invalidation_defaults")):
                source = case["records"] if field == "pilots" else case["invalidations"]
                dossier[field] = []
                for item in source:
                    data = {**deepcopy(neutral[defaults]), **deepcopy(item)}
                    data["idea_id"] = data.pop("candidate_id")
                    data["idea_version"] = data.pop("candidate_version")
                    dossier[field].append(data)
            inputs.append(dossier)
        expected = frozen_audit_batch([{"command": "validate", "value": value} for value in inputs])
        valid_inputs = []
        for case, dossier, baseline in zip(neutral["cases"], inputs, expected):
            with self.subTest(case=case["name"]):
                actual = validate_dossier(dossier)
                self.assertEqual(actual, baseline["value"])
                self.assertEqual(actual["valid"], case["expected"]["valid"])
                if actual["valid"]:
                    valid_inputs.append(dossier)
                    state = effective_result_state(dossier, neutral["candidate_id"])
                    for key, value in case["expected"].items():
                        if key != "valid":
                            self.assertEqual(state[key], value)
        expected = frozen_audit_batch([{"command": "snapshot", "value": value} for value in valid_inputs])
        for dossier, baseline in zip(valid_inputs, expected):
            self.assertEqual(snapshot(dossier), baseline["value"])

    def test_malformed_required_fields_and_enums_match_baseline(self):
        cases = [None, {}, [], fixture()]
        cases[-1]["ideas"] = [None]
        base = fixture()
        for container in ((), ("project",), ("config",), ("ideas", 0), ("ideas", 0, "validation"),
                          ("ideas", 0, "feasibility"), ("reviews", 0), ("reviews", 0, "scores"),
                          ("reviews", 0, "decision_basis"), ("papers", 0), ("evidence", 0), ("searches", 0)):
            target = base
            for key in container:
                target = target[key]
            for field in target:
                changed = deepcopy(base)
                pointer = changed
                for key in container:
                    pointer = pointer[key]
                del pointer[field]
                cases.append(changed)
        for value in (True, False, [], {}, "bogus", None):
            for path in (("schema_version",), ("ideas", 0, "version"), ("papers", 0, "year"), ("reviews", 0, "scores", "scientific_value")):
                changed, pointer = deepcopy(base), None
                pointer = changed
                for key in path[:-1]:
                    pointer = pointer[key]
                pointer[path[-1]] = value
                cases.append(changed)
        expected = frozen_audit_batch([{"command": "validate", "value": value} for value in cases])
        for index, (value, baseline) in enumerate(zip(cases, expected)):
            with self.subTest(case=index):
                self.assertEqual(validate_dossier(value), baseline["value"])

    def test_whitespace_timezone_and_locator_contracts(self):
        cases = []
        for value in ("\ufeff", "\x1c", "\u0085", "\u2000", " \u3000\t", "\ufeffpaper\ufeff"):
            dossier = fixture()
            dossier["ideas"][0]["title"] = value
            dossier["evidence"][0]["locator"] = value
            cases.append(dossier)
        for stamp in ("0000-02-29T00:00:00Z", "1900-02-29T00:00:00Z", "2000-02-29T00:00:00Z",
                      "2026-10-10T23:59:59.123456789+2359", "2026-10-10T12:00+01:00", "2026-10-10T24:00:00Z"):
            dossier = fixture()
            dossier["reviews"][0]["reviewed_at"] = stamp
            cases.append(dossier)
        expected = frozen_audit_batch([{"command": "validate", "value": value} for value in cases])
        for value, baseline in zip(cases, expected):
            self.assertEqual(validate_dossier(value), baseline["value"])

    def test_scientific_and_constraint_kill_gates_and_ordering(self):
        cases = []
        for outcome in ("supported", "contradicted", "execution_failed", "inconclusive", "not_run"):
            dossier = fixture()
            observed = result(dossier, outcome=outcome)
            if outcome == "not_run":
                observed["artifacts"] = []
            refresh(dossier)
            cases.append(deepcopy(dossier))
            dossier["reviews"][0]["decision"] = "KILL"
            dossier["reviews"][0]["decision_basis"].update(type="scientific_refutation", evidence_ids=[], pilot_ids=[observed["id"]])
            cases.append(dossier)
        for value in ({}, [], [""], {"devices": None}, 0, False, "unavailable"):
            dossier = fixture()
            dossier["project"]["constraints"]["compute"] = {"status": "confirmed", "value": value, "source": "SYNTHETIC statement"}
            dependency = dossier["ideas"][0]["feasibility"]["dependencies"][0]
            dependency.update(status="failed", mandatory=True, constraint_keys=["compute"])
            review = dossier["reviews"][0]
            review.update(decision="KILL", decision_scope="current_constraints")
            review["decision_basis"].update(type="constraints", dependency_names=[dependency["name"]], constraint_keys=["compute"])
            refresh(dossier)
            cases.append(dossier)
        dossier = fixture()
        add_review(dossier, reviewed_at="2026-10-10T00:00:00.123456789Z", decision="HOLD")
        add_review(dossier, reviewed_at="2026-10-10T01:00:00.123456788+01:00")
        cases.append(dossier)
        expected = frozen_audit_batch([{"command": "snapshot", "value": value} for value in cases])
        for index, (value, baseline) in enumerate(zip(cases, expected)):
            with self.subTest(case=index):
                self.assertEqual(snapshot(value), baseline["value"])

    def test_migration_v1_v2_future_and_latest_legacy_preserve_authority(self):
        values = []
        for version in (1, 2, 3):
            dossier = fixture()
            observed = result(dossier)
            dossier["schema_version"] = version
            if version < 3:
                dossier.pop("result_invalidations")
                observed.pop("run_id")
                observed.pop("affected_claims")
                dossier["decision_contract_version"] = 2
                for review in dossier["reviews"]:
                    review["decision_contract_version"] = 2
            if version == 1:
                dossier.pop("screening")
                dossier.pop("decision_contract_version")
                for idea in dossier["ideas"]:
                    idea.pop("evidence_links")
                for review in dossier["reviews"]:
                    review["basis_hash"] = "0" * 64
                    for key in ("review_basis_hash", "decision_scope", "recommended_stage", "decision_basis", "decision_contract_version"):
                        review.pop(key)
            values.append(dossier)
        blocked = fixture()
        add_review(blocked, decision_contract_version=1, decision="HOLD", reviewed_at="2026-10-10T02:00:00Z")
        values.append(blocked)
        future = fixture()
        future["decision_contract_version"] = 4
        values.append(future)
        ignored = deepcopy(values[1])
        ignored["result_invalidations"] = [{"previously": "uninterpreted"}]
        values.append(ignored)
        expected = frozen_audit_batch([{"command": "migrate", "value": value} for value in values])
        for value, baseline in zip(values, expected):
            before = deepcopy(value)
            if baseline["ok"]:
                actual = migrate_dossier(value)
                self.assertEqual(actual, baseline["value"])
                self.assertEqual(migrate_dossier(actual), actual)
            else:
                with self.assertRaisesRegex(ValueError, "future decision contract|uninterpreted result_invalidations"):
                    migrate_dossier(value)
            self.assertEqual(value, before)

    def test_each_go_gate_and_duplicate_kill_matches_baseline(self):
        changes = [
            (("evidence", 0, "read_scope"), "abstract"),
            (("searches", 0, "result_paper_ids"), []),
            (("searches", 0, "status"), "failed"),
            (("ideas", 0, "nearest_work"), []),
            (("ideas", 0, "novelty", "status"), "duplicate"),
            (("ideas", 0, "feasibility", "status"), "pilot_only"),
            (("ideas", 0, "feasibility", "dependencies", 0, "status"), "unknown"),
            (("ideas", 0, "validation", "status"), "missing"),
            (("ideas", 0, "evidence_links"), []),
            (("ideas", 0, "evidence_links", 0, "decision_relevant"), False),
            (("reviews", 0, "recommended_stage"), "information_test"),
            (("reviews", 0, "scores", "scientific_value"), None),
            (("reviews", 0, "penalties"), [{"points": 1000, "reason": "SYNTHETIC penalty"}]),
            (("reviews", 0, "decision"), "HOLD"),
            (("reviews", 0, "decision_basis", "type"), "insufficient"),
        ]
        cases = []
        for path, value in changes:
            dossier = fixture()
            dossier["screening"] = []
            pointer = dossier
            for key in path[:-1]:
                pointer = pointer[key]
            pointer[path[-1]] = value
            refresh(dossier)
            cases.append(dossier)
        for target in ("problem", "hypothesis", "prerequisite", "validation"):
            dossier = fixture()
            dossier["ideas"][0]["evidence_links"][0].update(role="contradiction", target=target, relation="contradicts")
            refresh(dossier)
            cases.append(dossier)
        for depth in ("abstract", "section"):
            dossier = fixture()
            dossier["ideas"][0]["novelty"]["status"] = "duplicate"
            dossier["evidence"][0]["read_scope"] = depth
            dossier["reviews"][0].update(decision="KILL")
            dossier["reviews"][0]["decision_basis"]["type"] = "duplicate"
            refresh(dossier)
            cases.append(dossier)
        expected = frozen_audit_batch([{"command": "snapshot", "value": value} for value in cases])
        for value, baseline in zip(cases, expected):
            self.assertEqual(snapshot(value), baseline["value"])

    def test_receipt_binding_forgery_staleness_and_complete_field_comparison(self):
        with tempfile.TemporaryDirectory() as root:
            dossier = fixture()
            peer = independent(dossier)
            seal(root, peer)
            report = verify_independent_receipts(dossier, root=root)
            self.assertEqual(report["failed"], [])
            self.assertEqual(len(rank_dossier(dossier, receipt_verification=report)["ranked"]), 1)
            for forged in (dict(report), deepcopy(report), json.loads(json.dumps(report)), {"verified": [{"review_id": peer["id"]}]}):
                self.assertEqual(len(rank_dossier(dossier, receipt_verification=forged)["held"]), 1)
            dossier["history"].append({"event": "snapshot changed"})
            self.assertEqual(len(rank_dossier(dossier, receipt_verification=report)["held"]), 1)
            dossier["history"].clear()
            for field, replacement in (("decision", "HOLD"), ("recommended_stage", "pilot"), ("idea_version", 2),
                                       ("review_basis_hash", "0" * 64), ("evaluator_context", "changed"), ("reason", "changed")):
                receipt = create_review_receipt(peer)
                receipt["review"][field] = replacement
                seal(root, peer, receipt)
                checked = verify_independent_receipts(dossier, root=root)
                self.assertFalse(checked["verified"])
                self.assertIn("fields do not match", checked["failed"][0]["reason"])

    def test_receipt_stage_and_later_independent_hold_prevent_escalation(self):
        with tempfile.TemporaryDirectory() as root:
            for stage, decision in (("pilot", "GO"), ("full_validation", "HOLD")):
                dossier = fixture()
                peer = independent(dossier)
                peer.update(recommended_stage=stage, decision=decision)
                seal(root, peer)
                add_review(dossier, recommended_stage="full_validation", reviewed_at="2026-10-10T02:00:00Z")
                report = verify_independent_receipts(dossier, root=root)
                self.assertEqual(len(report["verified"]), 1)
                self.assertEqual(len(rank_dossier(dossier, receipt_verification=report)["held"]), 1)

    def test_receipt_bounded_path_hash_and_mutation_guards(self):
        with tempfile.TemporaryDirectory() as root:
            for location in ("../escape.json", "https://example.invalid/receipt.json", "file:///receipt.json", "missing.json"):
                dossier = fixture()
                independent(dossier, artifact=location, artifact_sha256="0" * 64)
                self.assertFalse(verify_independent_receipts(dossier, root=root)["verified"])
            dossier = fixture()
            peer = independent(dossier, artifact="real receipt.json")
            seal(root, peer)
            peer["artifact"] = str(Path(root) / peer["artifact"])
            self.assertEqual(len(verify_independent_receipts(dossier, root=root)["verified"]), 1)
            Path(peer["artifact"]).write_bytes(b"x" * (1024 * 1024 + 1))
            self.assertIn("1 MiB", verify_independent_receipts(dossier, root=root)["failed"][0]["reason"])
            seal(root, peer)
            original = os.read
            def changing(descriptor, count):
                contents = original(descriptor, count)
                dossier["history"].append({"event": "concurrent scientific snapshot edit"})
                return contents
            with mock.patch("research_mentor.audit.os.read", side_effect=changing):
                with self.assertRaisesRegex(ValueError, "Dossier changed"):
                    verify_independent_receipts(dossier, root=root)

    def test_symbolic_receipt_and_root_are_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            dossier = fixture()
            peer = independent(dossier)
            seal(root, peer)
            link = Path(root) / "linked.json"
            try:
                link.symlink_to(Path(root) / peer["artifact"])
            except OSError:
                self.skipTest("Host does not permit file symbolic links")
            peer["artifact"] = link.name
            self.assertIn("symbolic links", verify_independent_receipts(dossier, root=root)["failed"][0]["reason"])
            directory = Path(root) / "linked-root"
            directory.symlink_to(Path(root), target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "Directory links"):
                init_project(str(directory), "project")

    def test_project_init_never_overwrites_or_writes_into_skill(self):
        with tempfile.TemporaryDirectory() as root:
            for name in ("../escape", "..", ".", "a/b", "a\\b", "C:\\escape", "-bad", "a" * 65):
                with self.assertRaises(ValueError):
                    init_project(root, name)
            result_value = init_project(root, "valid-project")
            path = Path(result_value["dossier_path"])
            before = path.read_bytes()
            self.assertTrue(validate_dossier(json.loads(before))["valid"])
            with self.assertRaises(ValueError):
                init_project(root, "valid-project")
            self.assertEqual(path.read_bytes(), before)
            with self.assertRaises(OSError):
                init_project(str(Path(root) / "not-created"), "project")
        with self.assertRaisesRegex(ValueError, "installed skill"):
            init_project(str(SKILL), "should-never-exist")


if __name__ == "__main__":
    unittest.main()
