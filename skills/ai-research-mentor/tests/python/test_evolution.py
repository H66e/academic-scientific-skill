"""SYNTHETIC maintenance receipts, not evidence of scientific improvement.

Cases exercise current bytes, independent-context declarations, immutable
evaluation inputs, and protected files. An optional actual Node oracle compares
the native port with the retained compatibility implementation.
"""
from __future__ import annotations

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
sys.path.insert(0, str(SKILL / "runtime"))

from research_mentor.evolution import (NOTICE, check_evolution, hash_checks,
                                       hash_file, read_run, snapshot_skill)

NODE = shutil.which("node")
NODE_URI = (SKILL / "scripts" / "evolution_guard.mjs").as_uri()
NODE_BRIDGE = r"""
import fs from 'node:fs';
const guard = await import(GUARD_URI);
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const answers = [];
for (const item of input) {
  if (item.action === 'check') answers.push(await guard.checkEvolution(item.run, item.root));
  if (item.action === 'snapshot') answers.push(await guard.snapshotSkill(item.root));
  if (item.action === 'hash') answers.push(await guard.hashFile(item.file));
  if (item.action === 'checks') answers.push(guard.hashChecks(item.value));
}
console.log(JSON.stringify(answers));
""".replace("GUARD_URI", json.dumps(NODE_URI))


class SyntheticEvolution:
    """Create explicit synthetic byte-bound records with no model invocation."""

    def __init__(self, root: str):
        self.root = Path(root)
        self.run_dir = self.root / "run-1"
        self.target = self.root / "target"
        self.baseline = self.run_dir / "baseline" / "ai-research-mentor"
        self.candidate = self.run_dir / "candidate" / "ai-research-mentor"
        (self.target / "references").mkdir(parents=True)
        (self.target / "SKILL.md").write_bytes(b"SYNTHETIC baseline instruction\n")
        (self.target / "references" / "data-contract.md").write_bytes(b"SYNTHETIC protected contract\n")
        shutil.copytree(self.target, self.baseline)
        shutil.copytree(self.target, self.candidate)
        (self.candidate / "SKILL.md").write_bytes(b"SYNTHETIC candidate instruction\n")
        self.suite = {"schema_version": 1, "max_attempts": 2, "allowed_paths": ["SKILL.md"],
                      "execution_config": {"model": "SYNTHETIC no model call", "tools": "None", "budget": "Fixture"},
                      "cases": [{"id": f"C{index + 1}", "split": split,
                                 "prompt": "SYNTHETIC fixed prompt", "criteria": ["SYNTHETIC fixed criterion"]}
                                for index, split in enumerate(("target", "regression", "holdout"))]}
        self.run = {"schema_version": 1, "run_id": "SYNTHETIC-run", "hypothesis": "SYNTHETIC behavior change",
                    "target_dir": str(self.target), "attempt": 1,
                    "baseline": {"directory": "baseline/ai-research-mentor", "hash": snapshot_skill(self.baseline)["hash"]},
                    "candidate": {"directory": "candidate/ai-research-mentor", "hash": snapshot_skill(self.candidate)["hash"]},
                    "suite": self.artifact("suite.json", self.suite), "checks": [], "review": {}}
        for name in ("unit_regressions", "skill_structure", "protected_principles"):
            self.run["checks"].append({"name": name, "passed": True,
                                       "baseline_hash": self.run["baseline"]["hash"],
                                       "candidate_hash": self.run["candidate"]["hash"],
                                       "suite_hash": self.run["suite"]["hash"],
                                       "artifact": self.artifact(f"checks/{name}.txt", b"SYNTHETIC check only\n")})
        self.review = {"kind": "independent", "author_context": "SYNTHETIC author",
                       "evaluator_context": "SYNTHETIC evaluator", "case_results": []}
        for index, case in enumerate(self.suite["cases"]):
            self.review["case_results"].append({"case_id": case["id"], "execution": "executed",
                                               "verdict": "better" if index == 0 else "tie",
                                               "hard_constraints_pass": True,
                                               "reason": "SYNTHETIC declared judgment; no real comparison",
                                               "baseline_output": self.artifact(f"outputs/{case['id']}-before.txt", b"SYNTHETIC old output\n"),
                                               "candidate_output": self.artifact(f"outputs/{case['id']}-after.txt", b"SYNTHETIC new output\n")})
        self.seal_review()

    def artifact(self, relative: str, value) -> dict:
        file = self.run_dir / relative
        file.parent.mkdir(parents=True, exist_ok=True)
        if not isinstance(value, bytes):
            value = json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")
        file.write_bytes(value)
        return {"file": relative, "hash": hashlib.sha256(value).hexdigest()}

    def seal_review(self):
        self.review.update({"baseline_hash": self.run["baseline"]["hash"],
                            "candidate_hash": self.run["candidate"]["hash"],
                            "suite_hash": self.run["suite"]["hash"],
                            "checks_hash": hash_checks(self.run["checks"])})
        self.run["review"] = self.artifact("review.json", self.review)

    def refresh_checks(self):
        for check in self.run["checks"]:
            check.update({"baseline_hash": self.run["baseline"]["hash"],
                          "candidate_hash": self.run["candidate"]["hash"], "suite_hash": self.run["suite"]["hash"]})


class EvolutionGuardTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="mentor-evolution-")
        self.addCleanup(self.temporary.cleanup)
        self.fixture = SyntheticEvolution(self.temporary.name)

    def check(self):
        return check_evolution(self.fixture.run, self.fixture.run_dir)

    def test_current_bound_synthetic_receipts_keep_and_preserve_all_bytes(self):
        f = self.fixture
        before = {str(file): file.read_bytes() for file in f.root.rglob("*") if file.is_file()}
        before_run = deepcopy(f.run)
        with mock.patch("subprocess.run", side_effect=AssertionError("runtime must not launch a process")):
            self.assertEqual(self.check(), {"decision": "KEEP", "reasons": [], "changed_paths": ["SKILL.md"]})
        self.assertEqual(f.run, before_run)
        self.assertEqual(before, {str(file): file.read_bytes() for file in f.root.rglob("*") if file.is_file()})
        self.assertIn("does not establish scientific quality", NOTICE)

    def test_ties_unclear_and_dry_run_cannot_claim_improvement(self):
        f = self.fixture
        for verdict, execution in (("tie", "executed"), ("unclear", "executed"), ("better", "dry_run")):
            with self.subTest(verdict=verdict, execution=execution):
                f.review["case_results"][0].update(verdict=verdict, execution=execution)
                f.seal_review()
                self.assertEqual(self.check()["decision"], "HOLD")

    def test_bound_regression_or_hard_failure_reject_even_with_target_improvement(self):
        f = self.fixture
        f.review["case_results"][2]["verdict"] = "worse"
        f.seal_review()
        self.assertIn("case regressed: C3", self.check()["reasons"])
        self.assertEqual(self.check()["decision"], "REJECT")
        f.review["case_results"][2]["verdict"] = "tie"
        f.review["case_results"][1]["hard_constraints_pass"] = False
        f.seal_review()
        self.assertEqual(self.check()["decision"], "REJECT")

    def test_unbound_or_missing_outputs_do_not_manufacture_observed_regression(self):
        f = self.fixture
        f.review["case_results"][2]["verdict"] = "worse"
        f.review["case_results"][2]["candidate_output"]["hash"] = "0" * 64
        f.seal_review()
        result = self.check()
        self.assertEqual(result["decision"], "HOLD")
        self.assertNotIn("case regressed: C3", result["reasons"])

    def test_self_review_and_same_context_declarations_cannot_keep(self):
        f = self.fixture
        f.review["kind"] = "self"
        f.seal_review()
        self.assertEqual(self.check()["decision"], "HOLD")
        f.review.update(kind="independent", evaluator_context=" SYNTHETIC author ")
        f.seal_review()
        self.assertEqual(self.check()["decision"], "HOLD")

    def test_missing_unknown_and_duplicate_cases_hold(self):
        f = self.fixture
        original = deepcopy(f.review["case_results"])
        for rows in (original[:-1], [dict(original[0], case_id="UNKNOWN"), *original[1:]],
                     [*original, deepcopy(original[0])]):
            f.review["case_results"] = rows
            f.seal_review()
            self.assertEqual(self.check()["decision"], "HOLD")

    def test_each_frozen_split_is_required(self):
        f = self.fixture
        f.suite["cases"][2]["split"] = "regression"
        f.run["suite"] = f.artifact("suite.json", f.suite)
        f.refresh_checks()
        f.seal_review()
        self.assertIn("suite requires at least one holdout case", self.check()["reasons"])

    def test_baseline_candidate_suite_and_output_tampering_make_receipts_stale(self):
        f = self.fixture
        mutations = [(f.baseline / "SKILL.md"), (f.candidate / "SKILL.md"),
                     (f.run_dir / "suite.json"), (f.run_dir / "outputs" / "C1-after.txt")]
        for file in mutations:
            with self.subTest(file=file):
                original = file.read_bytes()
                file.write_bytes(original + b"SYNTHETIC unreviewed change\n")
                self.assertEqual(self.check()["decision"], "HOLD")
                file.write_bytes(original)

    def test_target_user_edit_is_preserved_and_blocks_application(self):
        f = self.fixture
        file = f.target / "SKILL.md"
        file.write_bytes(b"SYNTHETIC user-owned new edit\n")
        self.assertIn("target no longer matches the baseline snapshot", self.check()["reasons"])
        self.assertEqual(file.read_bytes(), b"SYNTHETIC user-owned new edit\n")

    def test_old_check_logs_and_review_binding_cannot_authorize_changed_candidate(self):
        f = self.fixture
        (f.candidate / "SKILL.md").write_bytes(b"SYNTHETIC second candidate\n")
        f.run["candidate"]["hash"] = snapshot_skill(f.candidate)["hash"]
        f.seal_review()
        self.assertEqual(self.check()["decision"], "HOLD")
        self.assertTrue(any("check is stale or unbound:" in reason for reason in self.check()["reasons"]))

    def test_changed_check_artifact_or_status_invalidates_review(self):
        f = self.fixture
        f.run["checks"][0]["artifact"] = f.artifact("checks/replaced.txt", b"SYNTHETIC replacement\n")
        self.assertIn("review does not bind the current check statuses and artifacts", self.check()["reasons"])
        f.run["checks"][0]["passed"] = False
        self.assertEqual(self.check()["decision"], "REJECT")

    def test_required_checks_budget_and_no_change_candidate(self):
        f = self.fixture
        check = f.run["checks"].pop(0)
        f.seal_review()
        self.assertIn("missing required check: unit_regressions", self.check()["reasons"])
        f.run["checks"].insert(0, check)
        f.run["attempt"] = 3
        f.seal_review()
        self.assertIn("attempt exceeds the frozen suite budget", self.check()["reasons"])
        f.run["attempt"] = 1
        (f.candidate / "SKILL.md").write_bytes((f.baseline / "SKILL.md").read_bytes())
        f.run["candidate"]["hash"] = snapshot_skill(f.candidate)["hash"]
        f.refresh_checks()
        f.seal_review()
        self.assertIn("candidate has no file changes", self.check()["reasons"])

    def test_protected_modification_addition_and_deletion_cannot_be_permitted_by_suite(self):
        f = self.fixture
        protected = f.candidate / "references" / "data-contract.md"
        for operation in ("modify", "delete", "add"):
            with self.subTest(operation=operation):
                if operation == "modify":
                    protected.write_bytes(b"SYNTHETIC weakened contract\n")
                elif operation == "delete":
                    protected.unlink()
                else:
                    (f.candidate / "tests.py").write_bytes(b"SYNTHETIC bypass\n")
                f.suite["allowed_paths"] = ["SKILL.md", "references/data-contract.md", "tests.py"]
                f.run["suite"] = f.artifact("suite.json", f.suite)
                f.run["candidate"]["hash"] = snapshot_skill(f.candidate)["hash"]
                f.refresh_checks()
                f.seal_review()
                self.assertEqual(self.check()["decision"], "REJECT")

    def test_allowed_whitelist_edit_still_requires_suite_permission(self):
        f = self.fixture
        (f.candidate / "references" / "feedback.md").write_bytes(b"SYNTHETIC changed feedback\n")
        f.run["candidate"]["hash"] = snapshot_skill(f.candidate)["hash"]
        f.refresh_checks()
        f.seal_review()
        self.assertIn("change outside suite.allowed_paths: references/feedback.md", self.check()["reasons"])

    def test_traversal_urls_control_characters_and_drive_relative_paths_hold_without_read(self):
        f = self.fixture
        for path in ("../outside.txt", "https://example.org/file", "C:outside.txt", "file\x00.txt", ""):
            with self.subTest(path=path):
                f.run["checks"][0]["artifact"] = {"file": path, "hash": "0" * 64}
                with mock.patch("research_mentor.evolution._read_bytes", wraps=__import__("research_mentor.evolution", fromlist=["_read_bytes"])._read_bytes) as reader:
                    self.assertEqual(self.check()["decision"], "HOLD")
                    self.assertFalse(any(str(call.args[0]).endswith("outside.txt") for call in reader.call_args_list))

    def test_json_invalid_constants_and_bad_receipts_fail_closed(self):
        f = self.fixture
        for value in (b'{"kind":NaN}', b'{"kind":Infinity}', b"not-json", b"[]", b"null"):
            f.run["review"] = f.artifact("review.json", value)
            self.assertEqual(self.check()["decision"], "HOLD")

    def test_malformed_primitive_fields_and_boolean_numbers_are_not_coerced(self):
        f = self.fixture
        for field, values in (("attempt", (True, 0, -1, "1", [])), ("schema_version", (True, "1", None)),
                              ("checks", (None, {}, "passed")), ("run_id", (None, [], " "))):
            before = deepcopy(f.run)
            for value in values:
                with self.subTest(field=field, value=value):
                    f.run = deepcopy(before)
                    f.run[field] = value
                    self.assertEqual(self.check()["decision"], "HOLD")
            f.run = before

    def test_snapshot_hashes_every_file_exact_bytes_and_empty_directories_do_not_add_files(self):
        f = self.fixture
        directory = f.root / "snapshot"
        directory.mkdir()
        (directory / "empty").mkdir()
        payloads = {"2": b"\x00\xff", "10": b"SYNTHETIC\r\n", "tests/check.py": b"SYNTHETIC test\n",
                    "\U0001f9ea.md": "SYNTHETIC 中文".encode("utf-8")}
        for name, payload in payloads.items():
            file = directory / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(payload)
        result = snapshot_skill(directory)
        self.assertEqual(result["files"], {name: hashlib.sha256(payload).hexdigest() for name, payload in payloads.items()})
        self.assertEqual(result["hash"], hash_checks(result["files"]))

    def test_file_hash_streams_more_than_one_chunk_without_acceptance_drift(self):
        file = self.fixture.root / "large.bin"
        data = b"SYNTHETIC bytes\x00" * 150000
        file.write_bytes(data)
        self.assertEqual(hash_file(file), hashlib.sha256(data).hexdigest())

    def test_linked_leaf_and_directory_ancestor_are_rejected(self):
        f = self.fixture
        link = f.run_dir / "linked"
        try:
            if os.name == "nt":
                import _winapi
                _winapi.CreateJunction(str(f.baseline), str(link))
            else:
                os.symlink(f.baseline, link, target_is_directory=True)
        except (OSError, AttributeError) as error:
            self.skipTest(f"host cannot create a directory link: {error}")
        with self.assertRaisesRegex(ValueError, "symbolic links and junctions"):
            hash_file(link / "SKILL.md")
        with self.assertRaises(ValueError):
            snapshot_skill(link)
        f.run["baseline"]["directory"] = "linked"
        self.assertEqual(self.check()["decision"], "HOLD")

    def test_read_run_rejects_links_and_returns_the_absolute_run_file(self):
        f = self.fixture
        file = f.run_dir / "run.json"
        file.write_text(json.dumps(f.run), encoding="utf-8")
        run, run_file = read_run(file)
        self.assertEqual(run, f.run)
        self.assertEqual(run_file, file)


@unittest.skipUnless(NODE, "Node oracle is optional; native Python tests above remain runnable")
class EvolutionNodeConformanceTests(unittest.TestCase):
    @staticmethod
    def oracle(requests):
        result = subprocess.run([NODE, "--input-type=module", "-e", NODE_BRIDGE],
                                input=json.dumps(requests, ensure_ascii=True), text=True,
                                encoding="utf-8", capture_output=True, timeout=60)
        if result.returncode:
            raise AssertionError(result.stderr or result.stdout)
        return json.loads(result.stdout)

    def test_exact_hash_protocol_matches_actual_node_for_json_edges_and_snapshots(self):
        values = [{"10": "ten", "2": "two", "1": "one", "01": "leading"},
                  {"\U0001f9ea": "SYNTHETIC 中文", "\ue000": "bmp", "control": "\x00\n\r\t"},
                  [0.0, -0.0, 1e-7, 1e-6, 1e20, 1e21, 1.2345678901234567],
                  [{"passed": True, "nested": {"b": None, "a": False}}, 9007199254740992]]
        answers = self.oracle([{"action": "checks", "value": value} for value in values])
        self.assertEqual(answers, [hash_checks(value) for value in values])
        with tempfile.TemporaryDirectory(prefix="mentor-evolution-node-") as temporary:
            f = SyntheticEvolution(temporary)
            answers = self.oracle([{"action": "snapshot", "root": str(f.candidate)},
                                   {"action": "hash", "file": str(f.candidate / "SKILL.md")}])
            self.assertEqual(answers, [snapshot_skill(f.candidate), hash_file(f.candidate / "SKILL.md")])

    def test_frozen_decisions_reasons_and_changed_paths_match_actual_node(self):
        with tempfile.TemporaryDirectory(prefix="mentor-evolution-node-") as temporary:
            fixtures, expected = [], []

            def case(name, change):
                f = SyntheticEvolution(str(Path(temporary) / name))
                change(f)
                fixtures.append({"action": "check", "run": f.run, "root": str(f.run_dir)})
                expected.append(check_evolution(f.run, f.run_dir))

            case("keep", lambda f: None)
            case("all-tie", lambda f: (f.review["case_results"][0].update(verdict="tie"), f.seal_review()))
            case("regression", lambda f: (f.review["case_results"][2].update(verdict="worse"), f.seal_review()))
            case("hard", lambda f: (f.review["case_results"][1].update(hard_constraints_pass=False), f.seal_review()))
            case("dry", lambda f: (f.review["case_results"][0].update(execution="dry_run"), f.seal_review()))
            case("self", lambda f: (f.review.update(kind="self"), f.seal_review()))
            case("same-context", lambda f: (f.review.update(evaluator_context=f.review["author_context"]), f.seal_review()))
            case("missing-case", lambda f: (f.review["case_results"].pop(), f.seal_review()))
            case("unknown-case", lambda f: (f.review["case_results"][0].update(case_id="UNKNOWN"), f.seal_review()))
            case("duplicate-case", lambda f: (f.review["case_results"].append(deepcopy(f.review["case_results"][0])), f.seal_review()))
            case("stale-candidate", lambda f: (f.candidate / "SKILL.md").write_bytes(b"SYNTHETIC stale\n"))
            case("stale-target", lambda f: (f.target / "SKILL.md").write_bytes(b"SYNTHETIC user edit\n"))
            case("stale-output", lambda f: (f.run_dir / "outputs" / "C1-after.txt").write_bytes(b"SYNTHETIC stale\n"))
            case("stale-checks", lambda f: f.run["checks"][0].update(artifact=f.artifact("checks/other.txt", b"SYNTHETIC other\n")))
            case("failed-check", lambda f: f.run["checks"][0].update(passed=False))
            case("missing-check", lambda f: f.run["checks"].pop(0))
            case("budget", lambda f: f.run.update(attempt=3))
            case("traversal", lambda f: f.run["checks"][0].update(artifact={"file": "../outside.txt", "hash": "0" * 64}))
            case("invalid-run", lambda f: f.run.update(schema_version=True, attempt=True, run_id=[]))
            case("invalid-check", lambda f: f.run["checks"].append({"name": [], "passed": "true"}))

            def protected(f):
                (f.candidate / "references" / "data-contract.md").write_bytes(b"SYNTHETIC protected change\n")
                f.run["candidate"]["hash"] = snapshot_skill(f.candidate)["hash"]
                f.refresh_checks()
                f.seal_review()
            case("protected", protected)

            def restricted(f):
                (f.candidate / "references" / "feedback.md").write_bytes(b"SYNTHETIC outside suite\n")
                f.run["candidate"]["hash"] = snapshot_skill(f.candidate)["hash"]
                f.refresh_checks()
                f.seal_review()
            case("outside-suite", restricted)
            self.assertEqual(self.oracle(fixtures), expected)
