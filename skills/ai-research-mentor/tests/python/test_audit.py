"""Offline SYNTHETIC dossier parity; no scientific effectiveness is asserted."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
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
AUDIT_URI = (SKILL / "scripts" / "research_audit.mjs").as_uri()
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


NODE_BATCH = r"""
import fs from 'node:fs';
const audit = await import(AUDIT_URI);
const values = JSON.parse(fs.readFileSync(0, 'utf8'));
const results = [];
for (const row of values) {
  try {
    if (row.command === 'canonical') results.push({ok:true, value:audit.canonicalStringify(row.value)});
    else if (row.command === 'validate') results.push({ok:true, value:audit.validateDossier(row.value)});
    else if (row.command === 'migrate') results.push({ok:true, value:audit.migrateDossier(row.value)});
    else if (row.command === 'receipt') results.push({ok:true, value:audit.createReviewReceipt(row.value)});
    else if (row.command === 'verify') results.push({ok:true, value:await audit.verifyIndependentReceipts(row.value,{root:row.root})});
    else if (row.command === 'rank-verified') {
      const report=await audit.verifyIndependentReceipts(row.value,{root:row.root});
      results.push({ok:true,value:audit.rankDossier(row.value,{receiptVerification:report})});
    } else if (row.command === 'snapshot') results.push({ok:true, value:{
      validation:audit.validateDossier(row.value), rank:audit.rankDossier(row.value),
      hashes:row.value.ideas.map(idea=>audit.fingerprintIdea(row.value,idea.id)),
      config:audit.rankingConfigHash(row.value),
      states:row.value.schema_version===3?row.value.ideas.map(idea=>audit.effectiveResultState(row.value,idea.id)):[]
    }});
  } catch (error) { results.push({ok:false,error:error.message}); }
}
process.stdout.write(JSON.stringify(results));
""".replace("AUDIT_URI", json.dumps(AUDIT_URI))


def node_batch(values):
    if shutil.which("node") is None:
        raise unittest.SkipTest("Node compatibility oracle unavailable")
    completed = subprocess.run(["node", "--input-type=module", "--eval", NODE_BATCH],
                               input=json.dumps(values, ensure_ascii=True), capture_output=True,
                               text=True, encoding="utf-8", timeout=45, check=False)
    if completed.returncode:
        raise AssertionError(completed.stderr)
    return json.loads(completed.stdout)


def snapshot(dossier):
    return {"validation": validate_dossier(dossier), "rank": rank_dossier(dossier),
            "hashes": [fingerprint_idea(dossier, idea["id"]) for idea in dossier["ideas"]],
            "config": ranking_config_hash(dossier),
            "states": [effective_result_state(dossier, idea["id"]) for idea in dossier["ideas"]] if dossier["schema_version"] == 3 else []}


class AuditParityTests(unittest.TestCase):
    def test_existing_examples_exact_hashes_rank_and_validation(self):
        dossiers = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((REPO / "examples").glob("*/dossier.json"))]
        expected = node_batch([{"command": "snapshot", "value": value} for value in dossiers])
        for dossier, node in zip(dossiers, expected):
            with self.subTest(project=dossier["project"]["id"]):
                self.assertEqual(snapshot(dossier), node["value"])

    def test_canonical_numeric_unicode_and_rejection_boundaries(self):
        values = [None, True, {"10": "ten", "2": "two", "01": 0, "4294967295": "non-index"},
                  {"\ue000": "BMP", "\U00010000": "astral", "中文": "source"},
                  [0, -0.0, 2.0, 1e-7, 1e-6, 1e20, 1e21, 1e23, 0.0000123, 1.2345678901234567, 5e-324],
                  {"surrogate": "\ud800", "paired": "\ud83d\ude00"}, [9007199254740993, 1000000000000000100],
                  [{"nested": ["\n", "\t", "é", "\u2028"]}]]
        expected = node_batch([{"command": "canonical", "value": value} for value in values])
        for value, node in zip(values, expected):
            with self.subTest(value=repr(value)):
                self.assertEqual(canonical_stringify(value), node["value"])
        for value in (float("nan"), float("inf"), object(), {1: "non-string"}):
            with self.assertRaises(ValueError):
                canonical_stringify(value)
        cycle = []
        cycle.append(cycle)
        with self.assertRaisesRegex(ValueError, "Circular"):
            canonical_stringify(cycle)
        shared = {"same": 1}
        self.assertEqual(canonical_stringify([shared, shared]), '[{"same":1},{"same":1}]')

    def test_all_frozen_lifecycle_cases_match_node(self):
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
        expected = node_batch([{"command": "validate", "value": value} for value in inputs])
        valid_inputs = []
        for case, dossier, node in zip(neutral["cases"], inputs, expected):
            with self.subTest(case=case["name"]):
                actual = validate_dossier(dossier)
                self.assertEqual(actual, node["value"])
                self.assertEqual(actual["valid"], case["expected"]["valid"])
                if actual["valid"]:
                    valid_inputs.append(dossier)
                    state = effective_result_state(dossier, neutral["candidate_id"])
                    for key, value in case["expected"].items():
                        if key != "valid":
                            self.assertEqual(state[key], value)
        expected = node_batch([{"command": "snapshot", "value": value} for value in valid_inputs])
        for dossier, node in zip(valid_inputs, expected):
            self.assertEqual(snapshot(dossier), node["value"])

    def test_malformed_required_fields_and_enums_aggregate_like_node(self):
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
        expected = node_batch([{"command": "validate", "value": value} for value in cases])
        for index, (value, node) in enumerate(zip(cases, expected)):
            with self.subTest(case=index):
                self.assertEqual(validate_dossier(value), node["value"])

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
        expected = node_batch([{"command": "validate", "value": value} for value in cases])
        for value, node in zip(cases, expected):
            self.assertEqual(validate_dossier(value), node["value"])

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
        expected = node_batch([{"command": "snapshot", "value": value} for value in cases])
        for index, (value, node) in enumerate(zip(cases, expected)):
            with self.subTest(case=index):
                self.assertEqual(snapshot(value), node["value"])

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
        expected = node_batch([{"command": "migrate", "value": value} for value in values])
        for value, node in zip(values, expected):
            before = deepcopy(value)
            if node["ok"]:
                actual = migrate_dossier(value)
                self.assertEqual(actual, node["value"])
                self.assertEqual(migrate_dossier(actual), actual)
            else:
                with self.assertRaisesRegex(ValueError, "future decision contract|uninterpreted result_invalidations"):
                    migrate_dossier(value)
            self.assertEqual(value, before)

    def test_each_go_gate_and_duplicate_kill_matches_node(self):
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
        expected = node_batch([{"command": "snapshot", "value": value} for value in cases])
        for value, node in zip(cases, expected):
            self.assertEqual(snapshot(value), node["value"])

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
            node = node_batch([{"command": "verify", "value": dossier, "root": root}, {"command": "rank-verified", "value": dossier, "root": root}])
            self.assertEqual(report, node[0]["value"])
            self.assertEqual(rank_dossier(dossier, receipt_verification=report), node[1]["value"])
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
