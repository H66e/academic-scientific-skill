"""Native output parity with supplied SYNTHETIC metadata and adverse inputs."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil
import subprocess
import unittest

from research_mentor.outputs import draft_dossier, export_bibtex, render_card, validate_notes

SKILL = Path(__file__).resolve().parents[2]
PAPER = {"id": "SYNTHETIC-P1", "title": "SYNTHETIC: supplied mechanism", "year": 2024,
         "url": "https://example.org/paper", "identifiers": {"doi": "10.1234/synthetic"},
         "authors": [{"given": "Jane", "family": "Doe"}]}


class OutputTests(unittest.TestCase):
    def test_minimal_card_does_not_manufacture_an_approval(self):
        card = render_card({"question": "SYNTHETIC: Why does the effect change?"})
        self.assertIn("未记录，待评估", card)
        self.assertNotIn("GO", card)
        self.assertNotIn("已知结论与来源条件", card)

    def test_recorded_opinion_and_unexecuted_search_remain_notes(self):
        notes = {"question": "SYNTHETIC Q", "decision": "GO", "reverse_search": "Not executed.",
                 "gap": "Provisional boundary; not a field-wide gap.", "source_observations": ["Section 3 under A."]}
        card = render_card(notes)
        self.assertIn("GO（本卡不构成机器门控或独立评审回执）", card)
        for key in ("reverse_search", "gap"):
            self.assertIn(notes[key], card)
        self.assertIn("- Section 3 under A.", card)

    def test_validation_never_repairs_malformed_or_missing_inputs(self):
        for notes in (None, [], {"question": ""}, {"question": "Q", "type": "magic"},
                      {"question": "Q", "decision": "PIVOT"}, {"question": "Q", "alternatives": [None]},
                      {"question": "Q", "constraints": "guess GPU"}, {"question": "Q", "assumptions": [0]}):
            with self.subTest(notes=notes):
                self.assertFalse(validate_notes(notes)["valid"])
                with self.assertRaises(ValueError):
                    render_card(notes)

    def test_draft_preserves_notes_without_creating_scientific_records(self):
        notes = {"question": "  SYNTHETIC Q  ", "type": "theoretical", "decision": "GO",
                 "constraints": {"time": {"status": "unknown"}}, "assumptions": ["Untested A"],
                 "known": ["SYNTHETIC source: theorem 2"], "reverse_search": "Not executed."}
        before = copy.deepcopy(notes)
        dossier = draft_dossier(notes, name="synthetic-question")
        self.assertEqual(notes, before)
        self.assertEqual(dossier["project"]["question"], "SYNTHETIC Q")
        self.assertEqual(dossier["project"]["notes"]["decision"], "GO")
        for key in ("searches", "papers", "evidence", "ideas", "reviews", "pilots", "result_invalidations"):
            self.assertEqual(dossier[key], [])

    def test_invalid_project_slugs_are_rejected(self):
        for name in ("../escape", "UPPER", "a_underscore", "a" * 65, None):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "slug"):
                draft_dossier({"question": "Q"}, name=name)

    def test_bibliography_preserves_supplied_author_and_identifier(self):
        result = export_bibtex([PAPER])
        self.assertIn("author = {Doe, Jane}", result["bibtex"])
        self.assertIn("doi = {10.1234/synthetic}", result["bibtex"])
        self.assertTrue(result["bibtex"].startswith("@misc{"))
        self.assertNotIn("journal =", result["bibtex"])
        self.assertNotIn("booktitle =", result["bibtex"])

    def test_missing_names_and_years_stay_missing(self):
        result = export_bibtex([{"id": "SYNTHETIC", "title": "Supplied title", "year": None}])
        self.assertNotIn("author =", result["bibtex"])
        self.assertNotIn("year =", result["bibtex"])
        self.assertTrue(any("authors not supplied" in warning for warning in result["warnings"]))
        self.assertTrue(any("year unverified" in warning for warning in result["warnings"]))

    def test_tex_control_text_is_escaped_as_data(self):
        result = export_bibtex([{**PAPER, "title": "A } \\input{private} & 50% $x_1$"}])
        self.assertNotIn("\\input{", result["bibtex"])
        self.assertIn("\\textbackslash{}input\\{private\\}", result["bibtex"])
        self.assertIn("\\& 50\\% \\$x\\_1\\$", result["bibtex"])

    def test_identity_bridge_unifies_all_records_without_mutating_sources(self):
        records = [{**PAPER, "id": "DOI-only", "year": None, "authors": []},
                   {**PAPER, "id": "arxiv-only", "identifiers": {"arxiv": "2401.00001v1"}},
                   {**PAPER, "id": "bridge", "identifiers": {"doi": "https://doi.org/10.1234/SYNTHETIC", "arxiv": "2401.00001v1"}}]
        before = copy.deepcopy(records)
        result = export_bibtex(records)
        self.assertEqual(result["exported_count"], 1)
        self.assertEqual(len(set(result["keys"].values())), 1)
        self.assertIn("eprint = {2401.00001v1}", result["bibtex"])
        self.assertIn("year = {2024}", result["bibtex"])
        self.assertEqual(records, before)
        self.assertEqual(export_bibtex(list(reversed(records)))["exported_count"], 1)

    def test_conflicts_are_not_hidden_by_duplicate_consolidation(self):
        for change, message in (({"title": "Other"}, "Conflicting metadata"),
                                ({"year": 2023}, "Conflicting metadata"),
                                ({"authors": ["Someone else"]}, "Conflicting authors"),
                                ({"citation_key": "other"}, "Conflicting citation keys"),
                                ({"venue": "different"}, "Conflicting venue"),
                                ({"version": "v2"}, "Conflicting source versions"),
                                ({"identifiers": {"doi": "10.1234/synthetic", "arxiv": "2401.00001v2"}}, "Conflicting identifier")):
            first = {**PAPER, "citation_key": "actual", "venue": "given", "version": "v1",
                     "identifiers": {"doi": "10.1234/synthetic", "arxiv": "2401.00001v1"}}
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, message):
                export_bibtex([first, {**first, "id": "SYNTHETIC-P2", **change}])

    def test_malformed_duplicate_is_validated_before_consolidation(self):
        for change in ({"authors": 2}, {"citation_key": "bad}\\input{x}"}, {"identifiers": []},
                       {"url": "https://name:secret@example.org/"}, {"year": True}, {"version": 2}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                export_bibtex([PAPER, {**PAPER, "id": "SYNTHETIC-P2", **change}])
        with self.assertRaisesRegex(ValueError, "Duplicate paper ID"):
            export_bibtex([PAPER, PAPER])

    def test_openreview_is_case_sensitive_and_unknown_version_can_be_filled(self):
        records = [{**PAPER, "id": "first", "identifiers": {"openreview": "CaseSensitive"}, "version": "unknown"},
                   {**PAPER, "id": "same", "identifiers": {"openreview": "CaseSensitive"}, "version": "revision-2"},
                   {**PAPER, "id": "other", "identifiers": {"openreview": "casesensitive"}, "version": "revision-2"}]
        result = export_bibtex(records)
        self.assertEqual(result["exported_count"], 2)
        self.assertEqual(result["keys"]["first"], result["keys"]["same"])
        self.assertNotEqual(result["keys"]["first"], result["keys"]["other"])

    def test_special_identifier_and_empty_bibliography(self):
        result = export_bibtex([{**PAPER, "id": "__proto__"}])
        self.assertIn("__proto__", json.loads(json.dumps(result["keys"])))
        empty = export_bibtex([])
        self.assertEqual(empty["bibtex"], "")
        self.assertEqual(empty["exported_count"], 0)

    def test_javascript_whitespace_and_numeric_year_semantics(self):
        self.assertFalse(validate_notes({"question": "\ufeff"})["valid"])
        self.assertTrue(validate_notes({"question": "\u0085"})["valid"])
        card = render_card({"question": "\ufeffSYNTHETIC Q\ufeff", "known": "A\u0085B"})
        self.assertIn("研究问题：SYNTHETIC Q", card)
        self.assertIn("A\u0085B", card)
        result = export_bibtex([{**PAPER, "year": 2024.0}])
        self.assertIn("year = {2024}", result["bibtex"])

    @unittest.skipUnless(shutil.which("node"), "Node is optional and only used by differential development tests")
    def test_native_node_differential_cards_bibliographies_and_rejections(self):
        bridge = [{**PAPER, "id": "doi-only"},
                  {**PAPER, "id": "arxiv-only", "identifiers": {"arxiv": "2401.00001v1"}},
                  {**PAPER, "id": "bridge", "identifiers": {"doi": "10.1234/synthetic", "arxiv": "2401.00001v1"}}]
        cases = [{"fn": "renderCard", "data": {"question": "SYNTHETIC Q"}},
                 {"fn": "renderCard", "data": {"question": "SYNTHETIC Q", "decision": "GO", "gap": ["Unknown A"], "known": []}},
                 {"fn": "renderCard", "data": {"question": "Q", "decision": "PIVOT"}},
                 {"fn": "validateNotes", "data": {"question": "Q", "constraints": []}},
                 {"fn": "validateNotes", "data": {"question": "\ufeff"}},
                 {"fn": "validateNotes", "data": {"question": "\u0085"}},
                 {"fn": "renderCard", "data": {"question": "\ufeffQ\ufeff", "known": "A\u0085B\u001cC"}},
                 {"fn": "exportBibtex", "data": bridge},
                 {"fn": "exportBibtex", "data": list(reversed(bridge))},
                 {"fn": "exportBibtex", "data": [{**PAPER, "title": "中文 } \\input{x} & x²", "id": "__proto__"}]},
                 {"fn": "exportBibtex", "data": [{"id": "No-authors", "title": "Known"}]},
                 {"fn": "exportBibtex", "data": [{**PAPER, "year": 2024.0, "title": "A\ufeffB\u0085C"}]},
                 {"fn": "exportBibtex", "data": [{**PAPER, "id": "\ud800", "year": 1e21}]},
                 {"fn": "exportBibtex", "data": []}]
        for change in ({"title": "Other"}, {"authors": ["Someone"]}, {"authors": 2},
                       {"citation_key": "bad}\\input{x}"}, {"url": "https://name:secret@example.org/"}, {"version": 2}):
            cases.append({"fn": "exportBibtex", "data": [PAPER, {**PAPER, "id": "P2", **change}]})
        script = r'''
import fs from 'node:fs';
const api = await import(process.argv[1]);
const cases = JSON.parse(fs.readFileSync(0, 'utf8'));
const results = cases.map(c => { try { return {ok: true, value: api[c.fn](c.data)}; }
  catch (error) { return {ok: false, error: error.message}; } });
process.stdout.write(JSON.stringify(results));
'''
        result = subprocess.run([shutil.which("node"), "--input-type=module", "-e", script,
                                 (SKILL / "scripts/research_outputs.mjs").as_uri()],
                                input=json.dumps(cases, ensure_ascii=True), text=True, encoding="utf-8",
                                capture_output=True, timeout=30, check=True)
        node = json.loads(result.stdout)
        functions = {"renderCard": render_card, "validateNotes": validate_notes, "exportBibtex": export_bibtex}
        for case, expected in zip(cases, node):
            with self.subTest(case=case):
                try:
                    actual = {"ok": True, "value": functions[case["fn"]](case["data"])}
                except ValueError as exc:
                    actual = {"ok": False, "error": str(exc)}
                self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
