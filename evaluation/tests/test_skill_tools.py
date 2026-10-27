"""Native maintenance and packaging acceptance on synthetic resources."""
from __future__ import annotations
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "evaluation"))
from skill_tools import build_package, read_package, source_files, verify_package, check_skill, check_templates


class NativePackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mentor-python-package-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.skill = self.root / "ai-research-mentor"
        (self.skill / "references").mkdir(parents=True)
        (self.skill / "SKILL.md").write_bytes(b"SYNTHETIC skill\n")
        (self.skill / "references" / "中文😀.md").write_bytes("SYNTHETIC 中文\n".encode("utf-8"))
        (self.skill / "empty.txt").write_bytes(b"")

    def test_deterministic_build_and_exact_utf8_empty_bytes(self):
        first = build_package(self.skill)
        self.assertEqual(first, build_package(self.skill))
        self.assertTrue(verify_package(self.skill, first)["valid"])
        files = read_package(first)
        self.assertEqual(files["ai-research-mentor/empty.txt"], b"")
        self.assertEqual(files["ai-research-mentor/references/中文😀.md"], "SYNTHETIC 中文\n".encode())

    def test_license_is_first_and_generated_bytecode_is_excluded(self):
        license_path = self.root / "LICENSE"
        license_path.write_text("SYNTHETIC license", encoding="utf-8")
        (self.skill / "__pycache__").mkdir()
        (self.skill / "__pycache__" / "private.pyc").write_bytes(b"GENERATED")
        (self.skill / "other.pyo").write_bytes(b"GENERATED")
        archive = build_package(self.skill, license_path=license_path)
        files = read_package(archive)
        self.assertEqual(next(iter(files)), "ai-research-mentor/LICENSE")
        self.assertEqual(len(files), 4)
        self.assertTrue(verify_package(self.skill, archive, license_path=license_path)["valid"])

    def test_changes_missing_and_extra_resources_are_rejected(self):
        archive = build_package(self.skill)
        (self.skill / "SKILL.md").write_text("CHANGED", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "changed.*SKILL"):
            verify_package(self.skill, archive)
        (self.skill / "SKILL.md").write_bytes(b"SYNTHETIC skill\n")
        (self.skill / "new.txt").write_text("SYNTHETIC", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "missing.*new"):
            verify_package(self.skill, archive)
        (self.skill / "new.txt").unlink()
        (self.skill / "empty.txt").unlink()
        with self.assertRaisesRegex(ValueError, "extra.*empty"):
            verify_package(self.skill, archive)

    def test_missing_license_collision_and_missing_entrypoint_are_rejected(self):
        license_path = self.root / "LICENSE"
        license_path.write_bytes(b"SYNTHETIC required license\n")
        archive = build_package(self.skill)
        with self.assertRaisesRegex(ValueError, "missing.*LICENSE"):
            verify_package(self.skill, archive, license_path=license_path)
        (self.skill / "LICENSE").write_bytes(b"SYNTHETIC different in-tree license\n")
        with self.assertRaisesRegex(ValueError, "Duplicate source package entry"):
            build_package(self.skill, license_path=license_path)
        (self.skill / "SKILL.md").unlink()
        with self.assertRaisesRegex(ValueError, "lacks SKILL.md"):
            build_package(self.skill)

    def test_corruption_truncation_and_local_name_mismatch_are_rejected(self):
        archive = build_package(self.skill)
        corrupt = bytearray(archive)
        offset = 30 + struct.unpack_from("<H", corrupt, 26)[0] + struct.unpack_from("<H", corrupt, 28)[0]
        corrupt[offset] ^= 1
        with self.assertRaisesRegex(ValueError, "checksum"):
            read_package(corrupt)
        with self.assertRaisesRegex(ValueError, "end record"):
            read_package(archive[:-1])
        corrupt = bytearray(archive)
        corrupt[30] = ord("z")
        with self.assertRaisesRegex(ValueError, "local name"):
            read_package(corrupt)

    def test_matching_central_and_local_traversal_is_rejected(self):
        corrupt = bytearray(build_package(self.skill))
        central = struct.unpack_from("<I", corrupt, len(corrupt) - 6)[0]
        corrupt[30:33] = b"../"
        corrupt[central + 46:central + 49] = b"../"
        with self.assertRaisesRegex(ValueError, "Unsafe package entry"):
            read_package(corrupt)

    def test_empty_directory_segments_cannot_hide_in_valid_zip_headers(self):
        archive = build_package(self.skill).replace(b"ai-research-mentor/empty.txt", b"ai-research-mentor/section//")
        with self.assertRaisesRegex(ValueError, "Unsafe package entry"):
            read_package(archive)

    def test_native_bytes_match_frozen_historical_archive(self):
        archive = (REPO / "evaluation" / "fixtures" / "package-synthetic.zip").read_bytes()
        self.assertEqual(hashlib.sha256(archive).hexdigest(),
                         "efab0c6443bb73c26ea9add532ba057eeda824be4a10e861dc898fd90b8f1fa7")
        self.assertEqual(build_package(self.skill), archive)

    def test_standard_library_independently_reads_native_package(self):
        expected = {"ai-research-mentor/SKILL.md": b"SYNTHETIC skill\n",
                    "ai-research-mentor/empty.txt": b"",
                    "ai-research-mentor/references/中文😀.md": "SYNTHETIC 中文\n".encode("utf-8")}
        with zipfile.ZipFile(io.BytesIO(build_package(self.skill))) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(archive.namelist(), list(expected))
            self.assertEqual({name: archive.read(name) for name in archive.namelist()}, expected)
            for entry in archive.infolist():
                self.assertEqual(entry.compress_type, zipfile.ZIP_STORED)
                self.assertEqual(entry.date_time, (1980, 1, 1, 0, 0, 0))
                self.assertEqual(entry.flag_bits, 0x0800)

    def test_reader_accepts_independently_generated_deflated_archive(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("ai-research-mentor/SKILL.md", b"SYNTHETIC independent writer\n")
            archive.writestr("ai-research-mentor/references/中文😀.md", "SYNTHETIC 中文\n".encode("utf-8"))
        self.assertEqual(read_package(stream.getvalue()), {
            "ai-research-mentor/SKILL.md": b"SYNTHETIC independent writer\n",
            "ai-research-mentor/references/中文😀.md": "SYNTHETIC 中文\n".encode("utf-8")})

    def test_linked_source_ancestor_is_rejected(self):
        link = self.root / "link"
        try:
            link.symlink_to(self.skill, target_is_directory=True)
        except OSError:
            if os.name != "nt":
                raise
            # Windows directory junctions do not require file-symlink privilege.
            made = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(self.skill)], capture_output=True)
            if made.returncode:
                self.skipTest("Host cannot create a link or junction")
        with self.assertRaisesRegex(ValueError, "Linked path"):
            source_files(link)


class NativeMaintenanceCommands(unittest.TestCase):
    def test_structure_and_examples_run_with_no_external_runtime_in_path(self):
        with tempfile.TemporaryDirectory(prefix="mentor-python-only-tools-") as directory:
            environment = {**os.environ, "PATH": directory, "PYTHONIOENCODING": "utf-8"}
            for command in ("check-skill", "check-examples"):
                with self.subTest(command=command):
                    result = subprocess.run([sys.executable, "-B", str(REPO / "evaluation" / "skill_tools.py"), command],
                                            capture_output=True, text=True, encoding="utf-8", env=environment, timeout=20)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    response = json.loads(result.stdout)
                    if command == "check-skill":
                        self.assertTrue(response["valid"])
                    else:
                        self.assertEqual([row["decision"] for row in response["examples"]], ["GO", "GO", "HOLD"])

    def test_incomplete_native_toolchain_is_not_called_valid(self):
        with tempfile.TemporaryDirectory(prefix="mentor-incomplete-skill-") as directory:
            result = check_skill(Path(directory) / "ai-research-mentor")
            self.assertFalse(result["valid"])
            self.assertTrue(any("research_audit.py" in error for error in result["errors"]))

    def test_retained_tests_are_required_and_array_schema_references_resolve(self):
        with tempfile.TemporaryDirectory(prefix="mentor-structure-fixture-") as directory:
            root = Path(directory) / "ai-research-mentor"
            shutil.copytree(REPO / "skills" / "ai-research-mentor", root, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
            schema_file = root / "schemas" / "notes.schema.json"
            schema = json.loads(schema_file.read_text(encoding="utf-8"))
            schema["allOf"] = [{"type": "object"}]
            schema["properties"]["pointer_test"] = {"$ref": "#/allOf/0"}
            schema_file.write_text(json.dumps(schema), encoding="utf-8")
            self.assertTrue(check_skill(root)["valid"])
            schema["properties"]["pointer_test"]["$ref"] = "#/allOf/1"
            schema_file.write_text(json.dumps(schema), encoding="utf-8")
            self.assertFalse(check_skill(root)["valid"])
            schema["properties"]["pointer_test"]["$ref"] = "#/allOf/0"
            schema_file.write_text(json.dumps(schema), encoding="utf-8")
            (root / "tests" / "python" / "test_audit.py").unlink()
            checked = check_skill(root)
            self.assertFalse(checked["valid"])
            self.assertTrue(any("tests/python/test_audit.py" in error for error in checked["errors"]))

    def test_forbidden_runtime_sources_and_manifests_are_rejected(self):
        for name in ("unexpected.js", "unexpected.mjs", "unexpected.cjs", "unexpected.ts",
                     "unexpected.tsx", "package.json", "package-lock.json", "build/payload.js",
                     ".venv/package.json", "venv/script.ts", "x.egg-info/package-lock.json"):
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory(prefix="mentor-forbidden-source-") as directory:
                    root = Path(directory) / "ai-research-mentor"
                    shutil.copytree(REPO / "skills" / "ai-research-mentor", root,
                                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
                    forbidden = root / name
                    forbidden.parent.mkdir(parents=True, exist_ok=True)
                    forbidden.write_bytes(b"SYNTHETIC forbidden fixture\n")
                    checked = check_skill(root)
                    self.assertFalse(checked["valid"])
                    self.assertTrue(any(name in error for error in checked["errors"]))
                    with self.assertRaisesRegex(ValueError, "(?i)forbidden|python-only|python only"):
                        build_package(root)


class WritingTemplateGuardrailTests(unittest.TestCase):
    def test_current_templates_keep_their_guardrails(self):
        result = check_templates(REPO / "skills" / "ai-research-mentor")
        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(result["templates"], ["paper.md", "proposal.md", "survey.md"])

    def test_removed_marker_or_missing_template_is_reported(self):
        with tempfile.TemporaryDirectory(prefix="mentor-template-guard-") as directory:
            root = Path(directory) / "ai-research-mentor"
            shutil.copytree(REPO / "skills" / "ai-research-mentor", root,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
            paper = root / "templates" / "paper.md"
            paper.write_text(paper.read_text(encoding="utf-8").replace("禁止编造", "SYNTHETIC removed guardrail"),
                             encoding="utf-8")
            checked = check_templates(root)
            self.assertFalse(checked["valid"])
            self.assertTrue(any("paper.md" in error and "禁止编造" in error for error in checked["errors"]))
            (root / "templates" / "survey.md").unlink()
            checked = check_templates(root)
            self.assertFalse(checked["valid"])
            self.assertTrue(any("Missing templates/survey.md" in error for error in checked["errors"]))
