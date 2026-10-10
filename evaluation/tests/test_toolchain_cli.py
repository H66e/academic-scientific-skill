"""Native command workflows on fixed synthetic data, including no-Node execution."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
SKILL = REPO / "skills" / "ai-research-mentor"
sys.path.insert(0, str(SKILL / "runtime"))
from research_mentor.tool_cli import read_json, INPUT_LIMIT
from research_mentor.transport import Transport, TransportError


class NativeToolCommandTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mentor-native-cli-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.environment = {**os.environ, "PATH": str(self.root / "no-executables"), "PYTHONIOENCODING": "utf-8"}

    def command(self, script, *arguments, stdin=None):
        return subprocess.run([sys.executable, "-B", str(SKILL / "scripts" / script), *map(str, arguments)],
                              input=stdin, text=True, encoding="utf-8", capture_output=True,
                              env=self.environment, timeout=20)

    def write_json(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    def test_native_dossier_validate_fingerprint_rank_without_node(self):
        dossier = REPO / "examples" / "empirical-example" / "dossier.json"
        record = json.loads(dossier.read_text(encoding="utf-8"))
        checked = self.command("research_audit.py", "validate", dossier)
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        self.assertTrue(json.loads(checked.stdout)["valid"])
        idea = record["ideas"][0]
        fingerprint = self.command("research_audit.py", "fingerprint", dossier, idea["id"])
        self.assertEqual(fingerprint.returncode, 0, fingerprint.stdout + fingerprint.stderr)
        expected = next(review for review in record["reviews"] if review["idea_id"] == idea["id"])
        self.assertEqual(json.loads(fingerprint.stdout)["review_basis_hash"], expected["review_basis_hash"])
        ranked = self.command("research_audit.py", "rank", dossier)
        self.assertEqual(ranked.returncode, 0, ranked.stdout + ranked.stderr)
        self.assertEqual(json.loads(ranked.stdout)["ranked"][0]["decision"], "GO")

    def test_invalid_dossier_has_nonzero_exit_and_explicit_errors(self):
        path = self.write_json("invalid.json", {"schema_version": 3})
        output = self.command("research_audit.py", "validate", path)
        self.assertEqual(output.returncode, 1, output.stdout + output.stderr)
        checked = json.loads(output.stdout)
        self.assertFalse(checked["valid"])
        self.assertTrue(checked["errors"])

    def test_fingerprint_malformed_json_has_structured_failure(self):
        for record in (None, [], "SYNTHETIC wrong input"):
            with self.subTest(record=record):
                output = self.command("research_audit.py", "fingerprint", "-", "I1", stdin=json.dumps(record))
                self.assertEqual(output.returncode, 1)
                self.assertFalse(json.loads(output.stdout)["ok"])
                self.assertNotIn("Traceback", output.stderr)

    def test_full_validation_requires_actual_receipt_in_same_native_rank_call(self):
        from research_mentor.audit import create_review_receipt
        dossier = json.loads((REPO / "examples" / "empirical-example" / "dossier.json").read_text(encoding="utf-8"))
        review = dossier["reviews"][0]
        review.update(kind="independent", recommended_stage="full_validation",
                      author_context="SYNTHETIC author", evaluator_context="SYNTHETIC separate evaluator",
                      artifact="receipt.json")
        receipt = json.dumps(create_review_receipt(review), ensure_ascii=False).encode("utf-8")
        (self.root / "receipt.json").write_bytes(receipt)
        review["artifact_sha256"] = hashlib.sha256(receipt).hexdigest()
        file = self.write_json("full-stage.json", dossier)
        without = self.command("research_audit.py", "rank", file)
        self.assertEqual(without.returncode, 0, without.stdout + without.stderr)
        self.assertEqual(json.loads(without.stdout)["held"][0]["decision"], "HOLD")
        verified = self.command("research_audit.py", "rank", file, "--receipt-root", self.root)
        self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)
        actual = json.loads(verified.stdout)
        self.assertEqual(actual["ranked"][0]["decision"], "GO")
        self.assertEqual(len(actual["receipt_verification"]["verified"]), 1)
        before = file.read_bytes()
        (self.root / "receipt.json").write_bytes(receipt + b" ")
        stale = self.command("research_audit.py", "rank", file, "--receipt-root", self.root)
        self.assertEqual(stale.returncode, 0, stale.stdout + stale.stderr)
        self.assertEqual(json.loads(stale.stdout)["held"][0]["decision"], "HOLD")
        self.assertEqual(file.read_bytes(), before)

    def test_native_init_never_overwrites_existing_project(self):
        first = self.command("research_audit.py", "init", "--root", self.root, "--name", "synthetic-native")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        dossier = self.root / "synthetic-native" / "dossier.json"
        before = dossier.read_bytes()
        self.assertFalse(json.loads(before)["reviews"])
        second = self.command("research_audit.py", "init", "--root", self.root, "--name", "synthetic-native")
        self.assertEqual(second.returncode, 1)
        self.assertEqual(dossier.read_bytes(), before)

    def test_outputs_stdin_is_utf8_and_draft_does_not_create_approval(self):
        notes = json.loads((REPO / "examples" / "lightweight-example" / "notes.json").read_text(encoding="utf-8"))
        notes["question"] += " 中文合成材料"
        content = json.dumps(notes, ensure_ascii=False)
        card = self.command("research_outputs.py", "card", "-", stdin=content)
        self.assertEqual(card.returncode, 0, card.stdout + card.stderr)
        self.assertIn("中文合成材料", card.stdout)
        draft = self.command("research_outputs.py", "draft", "-", "--name", "synthetic-draft", stdin=content)
        self.assertEqual(draft.returncode, 0, draft.stdout + draft.stderr)
        record = json.loads(draft.stdout)
        self.assertFalse(record["reviews"])
        self.assertFalse(record["pilots"])
        path = self.write_json("draft.json", record)
        checked = self.command("research_audit.py", "validate", path)
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

    def test_bibtex_reports_missing_metadata_separately(self):
        record = {"papers": [{"id": "P-SYNTHETIC", "title": "SYNTHETIC 中文 source", "identifiers": {"doi": "10.5555/synthetic-cli"}}]}
        output = self.command("research_outputs.py", "bibtex", "-", stdin=json.dumps(record, ensure_ascii=False))
        self.assertEqual(output.returncode, 0, output.stdout + output.stderr)
        self.assertIn("中文", output.stdout)
        self.assertIn("10.5555/synthetic-cli", output.stdout)
        result = json.loads(output.stderr)
        self.assertEqual(result["exported_count"], 1)
        self.assertTrue(any("authors" in value for value in result["warnings"]))
        self.assertNotIn("year =", output.stdout)

    def test_source_offline_paths_need_neither_node_nor_network(self):
        for args in (("search", "--query", "SYNTHETIC public fixture", "--sensitivity", "public", "--offline"),
                     ("verify", "--doi", "10.5555/synthetic-cli", "--offline"),
                     ("fulltext", "--arxiv", "2305.13245v1", "--offline")):
            with self.subTest(args=args):
                output = self.command("research_sources.py", *args)
                self.assertEqual(output.returncode, 0, output.stdout + output.stderr)
                self.assertIn("offline", output.stdout)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_private_source_query_is_rejected_before_network(self):
        output = self.command("research_sources.py", "search", "--query", "SYNTHETIC unpublished direction")
        self.assertNotEqual(output.returncode, 0)
        self.assertIn("private", (output.stdout + output.stderr).lower())

    def test_repeated_cli_flags_are_rejected(self):
        output = self.command("research_sources.py", "verify", "--doi", "10.5555/synthetic", "--offline", "--offline")
        self.assertEqual(output.returncode, 2)
        self.assertIn("Repeated option", output.stderr)
        abbreviated = self.command("research_sources.py", "verify", "--doi", "10.5555/synthetic", "--off")
        self.assertEqual(abbreviated.returncode, 2)

    def test_evolution_native_snapshot_and_hash_bind_exact_bytes(self):
        directory = self.root / "synthetic-skill"
        directory.mkdir()
        file = directory / "SKILL.md"
        file.write_text("SYNTHETIC 中文 skill\n", encoding="utf-8")
        snapshot = self.command("evolution_guard.py", "snapshot", directory)
        hashed = self.command("evolution_guard.py", "hash", file)
        self.assertEqual(snapshot.returncode, 0, snapshot.stdout + snapshot.stderr)
        self.assertEqual(hashed.returncode, 0, hashed.stdout + hashed.stderr)
        self.assertEqual(json.loads(snapshot.stdout)["files"]["SKILL.md"], json.loads(hashed.stdout)["hash"])
        run = self.write_json("incomplete-run.json", {"checks": []})
        checks = self.command("evolution_guard.py", "checks-hash", run)
        self.assertEqual(checks.returncode, 0, checks.stdout + checks.stderr)
        decision = self.command("evolution_guard.py", "check", run)
        self.assertEqual(decision.returncode, 0, decision.stdout + decision.stderr)
        self.assertEqual(json.loads(decision.stdout)["decision"], "HOLD")

    def test_bounded_input_rejects_large_and_nonfinite_json(self):
        path = self.root / "too-large.json"
        path.write_bytes(b" " * (INPUT_LIMIT + 1))
        with self.assertRaises(ValueError):
            read_json(str(path))
        path.write_text('{"score": NaN}', encoding="utf-8")
        with self.assertRaises(ValueError):
            read_json(str(path))


class NativeResourceTransportTests(unittest.TestCase):
    def test_millisecond_timeout_conversion_does_not_accept_nonfinite(self):
        self.assertEqual(Transport(timeout=0.001).timeout, 0.001)
        for timeout in (False, float("nan"), float("inf"), 0, 61):
            with self.subTest(timeout=timeout), self.assertRaises(TransportError):
                Transport(timeout=timeout)

    def test_trusted_pdf_redirect_cannot_switch_version_or_format(self):
        import threading
        import time
        original = "https://arxiv.org/pdf/2305.13245v1"
        for location in ("/pdf/2305.13245v2", "/html/2305.13245v1"):
            with self.subTest(location=location):
                response = mock.Mock(code=302, headers={"location": location})
                transport = Transport(trusted_provider_transport=True)
                with mock.patch("urllib.request.build_opener") as opener:
                    opener.return_value.open.return_value = response
                    with self.assertRaisesRegex(TransportError, "changes.*resource"):
                        transport._get(original, allowed_hosts={"arxiv.org"}, trusted_provider=True,
                                       trusted_resource=original, deadline=time.monotonic() + 3,
                                       active={}, cancelled=threading.Event())
                self.assertEqual(len(transport.requests), 1)

    def test_resource_cannot_grant_trust_to_arbitrary_url(self):
        import threading
        import time
        transport = Transport(trusted_provider_transport=True)
        with self.assertRaisesRegex(TransportError, "exact.*arXiv"):
            transport._get("https://example.org/pdf/2305.13245v1", allowed_hosts={"example.org"},
                           trusted_provider=True, trusted_resource="https://example.org/pdf/2305.13245v1",
                           deadline=time.monotonic() + 3, active={}, cancelled=threading.Event())
        self.assertFalse(transport.requests)
