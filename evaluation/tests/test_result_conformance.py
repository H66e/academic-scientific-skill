"""SYNTHETIC cross-runtime result semantics, not scientific-effectiveness tests.

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
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "skills" / "ai-research-mentor" / "runtime"))

from research_mentor.judgment import Judgment
from research_mentor.ledger import Ledger, PROTOCOL, digest
from research_mentor.results import candidate_result_state

FIXTURE = REPO / "evaluation" / "fixtures" / "result-lifecycle.json"
AUDIT_URI = (REPO / "skills" / "ai-research-mentor" / "scripts" / "research_audit.mjs").as_uri()
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


# Node receives the neutral fixtures and builds a valid public synthetic context
# with its production initializer. This bridge adapts fields, never folds runs.
NODE_BRIDGE = r"""
import fs from 'node:fs';
const audit = await import(AUDIT_URI);
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const original = JSON.parse(fs.readFileSync(input.example, 'utf8'));
function dossierFor(value) {
  const dossier = audit.createInitialDossier('synthetic-result-conformance');
  const idea = structuredClone(original.ideas[0]);
  Object.assign(idea, {id: input.candidate_id, version: value.candidate_version ?? input.candidate_version,
    claims: input.claims.map(id => ({id, candidate_version: 1}))});
  dossier.ideas = [idea, {...structuredClone(idea), id: 'C-OTHER', claims: []}];
  for (const key of ['papers', 'searches', 'evidence']) dossier[key] = structuredClone(original[key]);
  dossier.screening = [];
  dossier.pilots = value.records.map(record => {
    const {candidate_id, candidate_version, ...fields} = record;
    return {...fields, idea_id: candidate_id, idea_version: candidate_version};
  });
  dossier.result_invalidations = value.invalidations.map(record => {
    const {candidate_id, candidate_version, ...fields} = record;
    return {...fields, idea_id: candidate_id, idea_version: candidate_version};
  });
  return dossier;
}
function facts(state) {
  return {valid: true, contradiction_blocker: state.contradiction_blocker,
    ambiguity_blocker: state.ambiguity_blocker, requires_hold: state.requires_hold,
    scientific_refutation_ids: [...state.scientific_refutation_ids].sort(),
    affected_claims_degraded: state.affected_claims_degraded};
}
function addReview(dossier, decision='GO', pilotIds=[]) {
  const review = structuredClone(original.reviews[0]);
  Object.assign(review, {id: 'REVIEW-SYNTHETIC', idea_id: input.candidate_id,
    idea_version: dossier.ideas[0].version, decision_contract_version: audit.DECISION_CONTRACT_VERSION,
    decision, review_basis_hash: audit.fingerprintIdea(dossier, input.candidate_id)});
  if (decision === 'KILL') review.decision_basis = {
    type: 'scientific_refutation', evidence_ids: [], pilot_ids: pilotIds,
    dependency_names: [], constraint_keys: [], explanation: 'SYNTHETIC bounded refutation basis'};
  dossier.reviews = [review];
}
function decision(dossier) {
  const ranking = audit.rankDossier(dossier);
  const row = [...ranking.ranked, ...ranking.held, ...ranking.killed]
    .find(item => item.idea_id === input.candidate_id);
  return {decision: row.decision, reasons: row.reasons};
}
const checked = input.cases.map(value => {
  const dossier = dossierFor(value);
  const validation = audit.validateDossier(dossier);
  if (!validation.valid) return {facts: {valid:false}, errors:validation.errors};
  const state = audit.effectiveResultState(dossier, input.candidate_id, value.candidate_version ?? input.candidate_version);
  addReview(dossier);
  const go = decision(dossier);
  addReview(dossier, 'KILL', dossier.pilots.filter(pilot => pilot.outcome === 'contradicted' && pilot.idea_version === dossier.ideas[0].version).map(pilot => pilot.id));
  const kill = decision(dossier);
  return {facts: facts(state), warnings:state.warnings,
    runs:state.runs.map(run=>({run_id:run.run_id, eligible:run.eligible, head_ids:[...run.head_ids].sort()})), go, kill};
});
if (input.currency) {
  const empty = dossierFor({records: [], invalidations: []});
  addReview(empty);
  const before = decision(empty);
  const initialHash = empty.reviews[0].review_basis_hash;
  empty.pilots = dossierFor(input.currency.contradiction).pilots;
  const afterRecord = decision(empty);
  addReview(empty);
  const contradictedHash = empty.reviews[0].review_basis_hash;
  empty.pilots = dossierFor(input.currency.correction).pilots;
  const afterCorrection = decision(empty);
  const correctedHash = audit.fingerprintIdea(empty, input.candidate_id);
  addReview(empty);
  const afterReassessment = decision(empty);
  const invalidated = dossierFor(input.currency.contradiction);
  addReview(invalidated);
  const preInvalidationHash = invalidated.reviews[0].review_basis_hash;
  invalidated.result_invalidations = dossierFor(input.currency.invalidation).result_invalidations;
  const afterInvalidation = decision(invalidated);
  const invalidatedHash = audit.fingerprintIdea(invalidated, input.candidate_id);
  addReview(invalidated);
  const invalidationReassessed = decision(invalidated);
  console.log(JSON.stringify({checked, currency: {before, afterRecord, afterCorrection, afterReassessment,
    afterInvalidation, invalidationReassessed,
    recordChangedBasis: initialHash !== contradictedHash,
    correctionChangedBasis: correctedHash !== contradictedHash,
    invalidationChangedBasis: invalidatedHash !== preInvalidationHash}}));
} else console.log(JSON.stringify({checked}));
""".replace("AUDIT_URI", json.dumps(AUDIT_URI))


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
        if os.environ.get("RESEARCH_MENTOR_REQUIRE_NODE_CONFORMANCE") == "1" and shutil.which("node") is None:
            raise RuntimeError("CI requires Node conformance; unavailable Node must fail, not skip")

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

    def node_check(self, cases, *, currency=None):
        if shutil.which("node") is None:
            self.skipTest("Node unavailable locally; CI requires cross-runtime conformance")
        payload = {key: self.fixture[key] for key in ("candidate_id", "candidate_version", "claims")}
        payload.update(cases=cases, example=str(REPO / "examples" / "empirical-example" / "dossier.json"))
        if currency:
            payload["currency"] = currency
        completed = subprocess.run(["node", "--input-type=module", "-e", NODE_BRIDGE],
            input=json.dumps(payload, ensure_ascii=False).encode("utf-8"), capture_output=True,
            timeout=60, cwd=REPO)
        self.assertEqual(completed.returncode, 0, completed.stderr.decode("utf-8", errors="replace"))
        return json.loads(completed.stdout.decode("utf-8"))

    def test_python_effective_facts_match_independent_frozen_cases(self):
        for case in self.cases:
            with self.subTest(case=case["name"]):
                observed = self.python_check(case)
                self.assertEqual(observed["facts"], case["expected"], observed)
                if case["expected"].get("ambiguity_blocker") or case["expected"].get("affected_claims_degraded"):
                    self.assertTrue(observed["warnings"], "Ambiguity/degradation must be visible")

    def test_both_production_folds_and_ranking_obey_the_same_cases(self):
        node = self.node_check(self.cases)["checked"]
        self.assertEqual(len(node), len(self.cases))
        for case, observed in zip(self.cases, node):
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
        for case, observed in zip(self.cases, node):
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
        node = self.node_check(variants)["checked"]
        for case, observed in zip(variants, node):
            with self.subTest(case=case["name"], ids=[item["id"] for item in case["records"]]):
                self.assertEqual(observed["facts"], case["expected"], observed)
                self.assertEqual(observed["runs"], self.python_check(case)["runs"])

    def test_node_removing_result_gate_never_restores_old_review(self):
        by_name = {case["name"]: case for case in self.cases}
        correction = by_name["same_run_visible_correction"]
        contradiction = deepcopy(correction)
        contradiction["records"] = contradiction["records"][:1]
        result = self.node_check([], currency={"contradiction": contradiction,
            "correction": correction, "invalidation": by_name["invalidation_withdraws_whole_run"]})["currency"]
        self.assertEqual(result["before"]["decision"], "GO", "Positive ranking control is necessary")
        for field in ("afterRecord", "afterCorrection", "afterInvalidation"):
            self.assertEqual(result[field]["decision"], "HOLD")
            self.assertTrue(any("stale" in reason.lower() for reason in result[field]["reasons"]))
        self.assertEqual(result["afterReassessment"]["decision"], "GO")
        self.assertEqual(result["invalidationReassessed"]["decision"], "GO")
        for field in ("recordChangedBasis", "correctionChangedBasis", "invalidationChangedBasis"):
            self.assertTrue(result[field], field)

    def test_node_legacy_migration_preserves_contradiction_and_record_identity(self):
        if shutil.which("node") is None:
            self.skipTest("Node unavailable locally; CI requires cross-runtime conformance")
        script = r"""
import fs from 'node:fs';
const audit = await import(AUDIT_URI);
const legacy = JSON.parse(fs.readFileSync('examples/empirical-example/dossier.json', 'utf8'));
legacy.schema_version = 2; legacy.decision_contract_version = 2;
for (const review of legacy.reviews) review.decision_contract_version = 2;
delete legacy.result_invalidations;
legacy.pilots = [
  {id:'EV-000003', idea_id:legacy.ideas[0].id, idea_version:1, kind:'scientific', outcome:'contradicted',
    artifacts:['SYNTHETIC-result.json'], summary:'SYNTHETIC legacy contradiction', limitations:['Invented fixture only']},
  {id:'LEGACY-SUPPORT', idea_id:legacy.ideas[0].id, idea_version:1, kind:'scientific', outcome:'supported',
    artifacts:['SYNTHETIC-support.json'], summary:'SYNTHETIC independent support', limitations:['Invented fixture only']}
];
const before = JSON.stringify(legacy);
const migrated = audit.migrateDossier(legacy);
const state = audit.effectiveResultState(migrated, legacy.ideas[0].id, 1);
const extra = structuredClone(legacy);
extra.result_invalidations = [{id:'IGNORED-LEGACY-INV',run_id:'EV-000003',idea_id:legacy.ideas[0].id,
  idea_version:1,result_id:'EV-000003',reason:'SYNTHETIC previously uninterpreted field',
  recorded_at:'2026-10-10T00:00:00Z',actor:'user',trust:'T1'}];
let rejected = false, error = null;
try { audit.migrateDossier(extra); } catch (failure) { rejected = true; error = failure.message; }
console.log(JSON.stringify({legacyValid:audit.validateDossier(legacy).valid,
  legacyInputUnchanged:before===JSON.stringify(legacy), migratedValid:audit.validateDossier(migrated).valid,
  schemaVersion:migrated.schema_version, contractVersion:migrated.decision_contract_version,
  runIds:migrated.pilots.map(pilot=>pilot.run_id), pilotIds:migrated.pilots.map(pilot=>pilot.id),
  artifacts:migrated.pilots.map(pilot=>pilot.artifacts), invalidations:migrated.result_invalidations,
  reviewCount:migrated.reviews.length,
  archivedReviews:migrated.history.filter(record=>record.original_review).map(record=>record.original_review),
  originalReviews:legacy.reviews, blocker:state.contradiction_blocker,
  extraLegacyReadable:audit.validateDossier(extra).valid, extraRejected:rejected, extraError:error}));
""".replace("AUDIT_URI", json.dumps(AUDIT_URI))
        completed = subprocess.run(["node", "--input-type=module", "-e", script],
            capture_output=True, timeout=30, cwd=REPO)
        self.assertEqual(completed.returncode, 0, completed.stderr.decode("utf-8", errors="replace"))
        value = json.loads(completed.stdout.decode("utf-8"))
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
        self.assertTrue(value["extraRejected"], "Previously ignored withdrawals cannot silently acquire semantics")
        self.assertRegex(value["extraError"], r"(?i)legacy|invalidation")

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
            self.assertEqual(exported["reviews"], [], "Python approval cannot transfer to Node")
            if shutil.which("node") is None:
                if os.environ.get("RESEARCH_MENTOR_REQUIRE_NODE_CONFORMANCE") == "1":
                    self.fail("Node required in CI")
                return
            script = (
                "import fs from 'node:fs';const a=await import(" + json.dumps(AUDIT_URI) + ");"
                "const d=JSON.parse(fs.readFileSync(0,'utf8'));const v=a.validateDossier(d);"
                "console.log(JSON.stringify({validation:v,state:v.valid?a.effectiveResultState(d,'C-SYNTHETIC',1):null,"
                "ranking:v.valid?a.rankDossier(d):null}));"
            )
            checked = subprocess.run(["node", "--input-type=module", "-e", script],
                input=json.dumps(exported, ensure_ascii=False).encode("utf-8"), capture_output=True, timeout=30, cwd=REPO)
            self.assertEqual(checked.returncode, 0, checked.stderr.decode("utf-8", errors="replace"))
            value = json.loads(checked.stdout.decode("utf-8"))
            self.assertTrue(value["validation"]["valid"], value["validation"])
            expected = python_facts(judgment.results("C-SYNTHETIC"))
            actual = value["state"]
            self.assertEqual(expected, {"valid": True, **{key: actual[key] for key in expected if key != "valid"}})
            self.assertEqual(value["ranking"]["ranked"], [])
            self.assertEqual(value["ranking"]["held"][0]["decision"], "HOLD")


if __name__ == "__main__":
    unittest.main(verbosity=2)
