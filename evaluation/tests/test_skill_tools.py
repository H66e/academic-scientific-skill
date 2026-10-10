"""Native maintenance and packaging acceptance on synthetic resources."""
from __future__ import annotations
import base64
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "evaluation"))
from skill_tools import build_package, read_package, source_files, verify_package, check_skill


class NativePackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mentor-python-package-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.skill = self.root / "ai-research-mentor"
        (self.skill / "references").mkdir(parents=True)
        (self.skill / "SKILL.md").write_text("SYNTHETIC skill\n", encoding="utf-8")
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
        (self.skill / "SKILL.md").write_text("SYNTHETIC skill\n", encoding="utf-8")
        (self.skill / "new.txt").write_text("SYNTHETIC", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "missing.*new"):
            verify_package(self.skill, archive)
        (self.skill / "new.txt").unlink()
        (self.skill / "empty.txt").unlink()
        with self.assertRaisesRegex(ValueError, "extra.*empty"):
            verify_package(self.skill, archive)

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

    def test_native_bytes_match_node_builder(self):
        node = shutil.which("node")
        if not node:
            if os.environ.get("RESEARCH_MENTOR_REQUIRE_NODE_CONFORMANCE") == "1":
                self.fail("Node compatibility oracle is required")
            self.skipTest("Node compatibility oracle unavailable")
        code = "import {buildPackage} from " + json.dumps((REPO / "evaluation" / "package-skill.mjs").as_uri()) + "; const b=await buildPackage(process.argv[1]);process.stdout.write(b.bytes.toString('base64'));"
        result = subprocess.run([node, "--input-type=module", "-e", code, str(self.skill)],
                                capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(build_package(self.skill), base64.b64decode(result.stdout))

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
    def test_structure_and_examples_run_with_no_node_in_path(self):
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
            (root / "tests" / "research_audit.test.mjs").unlink()
            checked = check_skill(root)
            self.assertFalse(checked["valid"])
            self.assertTrue(any("tests/research_audit.test.mjs" in error for error in checked["errors"]))
