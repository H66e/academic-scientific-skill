"""Repository version-consistency regression test.

`VERSION` is the source of truth. Five places claim the current package version:
`VERSION`, `pyproject.toml`, `research_mentor.__version__`, the README version
line and the CHANGELOG section heading. Nothing compared them, so a bump that
missed one drifted silently.

Two exclusions are deliberate. `schema_version` and `decision_contract_version`
count dossier contract revisions, not releases, and are not expected to track
`VERSION`. `docs/WORKSPACE_GOVERNANCE.md` describes the released and installed
copy, which is allowed to lag this working tree by design.

The readers below handle this repository's own files, not general TOML or
Markdown. They fail loudly: if a claim is reworded so a reader can no longer
find it, the test errors with the unreadable value rather than passing quietly.
"""
from __future__ import annotations

from pathlib import Path
import re
import sys
import unittest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "skills" / "ai-research-mentor" / "runtime"))

from research_mentor import __version__  # noqa: E402

VERSION_PATTERN = re.compile(r"\d+\.\d+\.\d+")
README_VERSION_PATTERN = re.compile(r"当前版本\s*\*\*([^*]+)\*\*")


def read_text(relative):
    return (REPO / relative).read_text(encoding="utf-8")


def project_version(text):
    """Read `[project].version` without tomllib; Python 3.10 has no tomllib."""
    table = ""
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if line.startswith("[") and line.endswith("]"):
            table = line[1:-1].strip()
        elif table == "project":
            key, separator, value = line.partition("=")
            if separator and key.strip() == "version":
                return value.strip().strip("\"'")
    return None


def readme_version(text):
    match = README_VERSION_PATTERN.search(text)
    return match.group(1).strip() if match else None


def changelog_section_versions(text):
    return [match.group(1).strip() for match in re.finditer(r"^##\s+(\S+)\s*$", text, re.MULTILINE)]


class VersionConsistencyTests(unittest.TestCase):
    def test_every_current_version_claim_equals_version_file(self):
        declared = read_text("VERSION").strip()
        self.assertRegex(declared, VERSION_PATTERN, "VERSION must be MAJOR.MINOR.PATCH")

        claims = {
            "pyproject.toml [project].version": project_version(read_text("pyproject.toml")),
            "research_mentor.__version__": __version__,
            "README.md version line": readme_version(read_text("README.md")),
        }
        disagreeing = {where: value for where, value in claims.items() if value != declared}
        self.assertEqual(disagreeing, {},
                         f"version claims disagreeing with VERSION ({declared}): {disagreeing}"
                         " — an unreadable value means the claim was reworded and this reader needs updating")

        self.assertIn(declared, changelog_section_versions(read_text("CHANGELOG.md")),
                      f"CHANGELOG.md has no '## {declared}' section")

    def test_readers_reject_input_they_cannot_read_confidently(self):
        self.assertIsNone(project_version("[project]\nname = \"x\"\n"), "a missing key must read as unreadable, not as a guess")
        self.assertIsNone(project_version("[tool.other]\nversion = \"9.9.9\"\n"), "another table's version must not be borrowed")
        self.assertEqual(project_version("[project]\nversion = \"1.2.3\"\n\n[tool.x]\n"), "1.2.3")
        self.assertIsNone(readme_version("当前版本尚未确定"), "a reworded line must read as unreadable")
        self.assertEqual(readme_version("当前版本 **1.2.3**。"), "1.2.3")
        self.assertEqual(changelog_section_versions("# c\n\n## Unreleased\n\n## 1.2.3\n"), ["Unreleased", "1.2.3"])


if __name__ == "__main__":
    unittest.main()
