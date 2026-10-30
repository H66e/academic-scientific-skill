"""Tier-contract tests; synthetic text and real local ledgers only."""
from __future__ import annotations

import copy
import datetime as dt
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

SKILL = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SKILL / "runtime"))

from research_mentor import draft as draft_module
from research_mentor.core import ResearchCore
from research_mentor.draft import check_draft, derive_tier
from research_mentor.judgment import Judgment
from research_mentor.transport import Response

CONCEPT = """# 概念备忘录

<!-- report-tier: concept_memo -->

> 概念备忘录：引用未核验 / 待核验，不能当作证据审查。

## 当前判断与下一步

- 值不值得研究：未知。
- 差异：未确认。
- 能否验证：未知。

## 问题与未知

- 未知。

## 待核验线索

- 只列标题，不写编号引用。

## 下一步

- 查一项。
"""

PROJECTION = {
    "chain_ok": True,
    "artifacts_ok": True,
    "derived_tier": "evidence_review",
    "sources": {
        "S1": {
            "canonical": "arxiv:2401.00001",
            "title": "Synthetic Paper",
            "doi": None,
            "arxiv": "2401.00001v1",
            "version": "v1",
            "url": None,
            "readings": [{"anchor": "E1", "scopes": ["full_text"], "locator": "§3.2"},
                            {"anchor": "E1", "scopes": ["full_text"], "locator": "§4 / Table 2"}],
        },
        "S2": {
            "canonical": "arxiv:2401.00002",
            "title": "Synthetic Paper Two",
            "doi": None,
            "arxiv": "2401.00002v1",
            "version": "v1",
            "url": None,
            "readings": [{"anchor": "E2", "scopes": ["full_text"], "locator": "§2"},
                            {"anchor": "E2", "scopes": ["full_text"], "locator": "§3"}],
        }
    },
    "anchor_to_source": {"E1": "S1", "E2": "S2"},
}

NEAREST = """```nearest-set-json
{
  "schema": "nearest-set-v2",
  "created_at": "2026-10-28",
  "queries": ["mask refinement", "inpainting mask expansion"],
  "candidates": [
    {"id": "P1", "title": "Synthetic Paper", "rationale": "动作集合与掩码路线最接近，可能漏掉多模态近邻",
     "status": "full_text", "reader": "user", "ledger": "ledger:E1", "locator": "§3.2",
     "kill_questions": [{"q": "是否也按成本选择动作", "answer": "否", "locator": "§3.2"},
                        {"q": "动作集合是否含收缩", "answer": "是", "locator": "§4 / Table 2"}]},
    {"id": "P2", "title": "Synthetic Paper Two", "rationale": "另一种掩码扩展路线，可能遗漏的检索术语",
     "status": "section", "reader": "model", "ledger": "ledger:E2", "locator": "§2",
     "kill_questions": [{"q": "是否比较净收益", "answer": "是", "locator": "§2"},
                        {"q": "是否等成本比较", "answer": "否", "locator": "§3"}]}
  ],
  "uncovered": ["可能漏掉的多模态近邻簇"]
}
```"""

CLAIMS = """| 编号 | 主张 | 等级 | 近邻 | 依据 | 翻转条件 |
| --- | --- | --- | --- | --- | --- |
| C1 | 与 P1 在动作集合上不同 | A | P1, P2 | ledger:E1 | 若 P1 也按成本选择动作则不成立 |
| C2 | P2 的净收益比较与当前路线不同 | B | P2 | ledger:E2 | 若 P2 也等成本比较则不成立 |"""

PROVISIONAL = """```provisional-json
{"schema": "provisional-v1", "claims": [
  {"id": "C1", "tendency": "倾向与 P1 不同", "flip": "若 P1 也按成本选择动作则不成立",
   "check": {"candidate": "P1", "question": "是否也按成本选择动作", "locator": "§3.2"},
   "access": "arXiv:2401.00001v1"}
]}
```"""

EVIDENCE = f"""# 研究报告

<!-- report-tier: evidence_review -->

## 当前判断与下一步

- 值不值得研究：在已核验的两篇近邻内未发现等价机制 [C1]。
- 相对最近工作的差异：动作集合不同 [C2]。
- 下一步：补读 P2 的 §3。

## 近邻选择与深读记录

{NEAREST}

## 主张—证据等级

{CLAIMS}

## 证据、近邻与差异

已有证据 [1,2]。

## 覆盖边界与待核验清单

覆盖有限。

## 参考文献

| 编号 | 文献标题 | 标识 | 账本绑定 | 阅读范围 |
| --- | --- | --- | --- | --- |
| [1] | Synthetic Paper | `arXiv:2401.00001v1` | `ledger:S1` | `full_text` |
| [2] | Synthetic Paper Two | `arXiv:2401.00002v1` | `ledger:S2` | `full_text` |
"""


UNREAD_P2 = (
    '{"q": "是否比较净收益", "answer": "未读到", "locator": "无"}, '
    '{"q": "是否等成本比较", "answer": "未读到", "locator": "无"}'
)


def c_only(*, provisional=None, qualified=True):
    if provisional is None:
        provisional = PROVISIONAL.replace(
            '"candidate": "P1", "question": "是否也按成本选择动作", "locator": "§3.2"',
            '"candidate": "P2", "question": "是否比较净收益", "locator": "无"',
        )
    text = EVIDENCE.replace(
        '"q": "是否比较净收益", "answer": "是", "locator": "§2"',
        '"q": "是否比较净收益", "answer": "未读到", "locator": "无"',
    ).replace(
        '"q": "是否等成本比较", "answer": "否", "locator": "§3"',
        '"q": "是否等成本比较", "answer": "未读到", "locator": "无"',
    )
    text = text.replace(
        "| C1 | 与 P1 在动作集合上不同 | A | P1, P2 | ledger:E1 | 若 P1 也按成本选择动作则不成立 |\n"
        "| C2 | P2 的净收益比较与当前路线不同 | B | P2 | ledger:E2 | 若 P2 也等成本比较则不成立 |",
        "| C1 | 与 P1 在动作集合上不同 | C | P2 | 摘要级/未读 | 若 P1 也按成本选择动作则不成立 |",
    )
    text = text.replace(
        "- 值不值得研究：在已核验的两篇近邻内未发现等价机制 [C1]。\n"
        "- 相对最近工作的差异：动作集合不同 [C2]。",
        "- 值不值得研究：倾向与 P1 不同（置信低，见 [C1]）。" if qualified else
        "- 值不值得研究：与 P1 不同 [C1]。",
    )
    text = text.replace("## 证据、近邻与差异", f"## 暂定判断（C 级）\n\n{provisional}\n\n## 证据、近邻与差异")
    return text


class DraftContractTests(unittest.TestCase):
    def check(self, text, ledger=None, projection=None):
        with tempfile.TemporaryDirectory(prefix="mentor-draft-") as directory:
            path = pathlib.Path(directory) / "draft.md"
            path.write_text(text, encoding="utf-8")
            with mock.patch("research_mentor.draft.derive_tier",
                            return_value=copy.deepcopy(PROJECTION if projection is None else projection)), \
                    mock.patch("research_mentor.draft._today", return_value=dt.date(2026, 10, 30)):
                return check_draft(path, ledger=ledger)

    def codes(self, result):
        return "\n".join(result["errors"])

    # --- baseline behaviour -------------------------------------------------
    def test_concept_memo_is_valid_without_ledger(self):
        result = self.check(CONCEPT)
        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(result["declared_tier"], "concept_memo")

    def test_concept_memo_rejects_citations_and_synonym_headings(self):
        self.assertFalse(self.check(CONCEPT.replace("只列标题，不写编号引用。", "一个引用 [1]。"))["valid"])
        self.assertFalse(self.check(CONCEPT.replace("## 待核验线索", "## 验证路径"))["valid"])

    def test_concept_memo_rejects_author_year_and_url(self):
        for addition in ("(Smith et al., 2023) 证明有效。", "https://example.org/paper", "arXiv 2305.13245"):
            with self.subTest(addition=addition):
                self.assertFalse(self.check(CONCEPT + "\n" + addition)["valid"])

    def test_non_concept_requires_ledger(self):
        result = self.check(EVIDENCE)
        self.assertFalse(result["valid"])
        self.assertIn("LEDGER_REQUIRED", self.codes(result))

    def test_valid_evidence_review_with_bound_contract(self):
        result = self.check(EVIDENCE, ledger="x")
        self.assertTrue(result["valid"], result["errors"])

    def test_machine_block_appendix_heading_is_allowed(self):
        """The shared template appendix groups the machine blocks under one heading."""
        result = self.check(EVIDENCE.replace(
            "## 近邻选择与深读记录", "## 附录：机器可读块\n\n### 近邻选择与深读记录"), ledger="x")
        self.assertTrue(result["valid"], result["errors"])

    def test_declared_tier_above_derived_fails(self):
        plan = EVIDENCE.replace("evidence_review", "research_plan")
        result = self.check(plan, ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("TIER_EXCEEDS_EVIDENCE", self.codes(result))

    # --- identity / references ---------------------------------------------
    def test_identity_mismatch_is_rejected(self):
        result = self.check(EVIDENCE.replace("arXiv:2401.00001v1", "arXiv:2401.99999v1"), ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("CITATION_IDENTITY_MISMATCH", self.codes(result))

    def test_duplicate_source_binding_is_rejected(self):
        duplicate = EVIDENCE.replace(
            "| [2] | Synthetic Paper Two | `arXiv:2401.00002v1` | `ledger:S2` | `full_text` |",
            "| [2] | Synthetic Paper | `arXiv:2401.00001v1` | `ledger:S1` | `full_text` |",
        )
        result = self.check(duplicate, ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("DUPLICATE_SOURCE", self.codes(result))

    def test_reference_scope_must_be_full_text_or_section(self):
        result = self.check(EVIDENCE.replace("`full_text` |", "`full` |"), ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("CITATION_SCOPE_INVALID", self.codes(result))

    def test_reference_trailing_content_is_rejected(self):
        for suffix in ("\n**结果**\n提升 15%。", "\n结果\n---\n提升 15%。", "\n<p>提升 15%</p>"):
            with self.subTest(suffix=suffix):
                result = self.check(EVIDENCE + suffix, ledger="x")
                self.assertFalse(result["valid"])
                self.assertIn("CONTENT_AFTER_REFERENCES", self.codes(result))

    # --- nearest-set v2 -----------------------------------------------------
    def test_nearest_set_requires_schema(self):
        result = self.check(EVIDENCE.replace('"schema": "nearest-set-v2",', ''), ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("NEAREST_SET_SCHEMA_INVALID", self.codes(result))

    def test_nearest_set_requires_two_distinct_queries(self):
        one = EVIDENCE.replace('["mask refinement", "inpainting mask expansion"]', '["mask refinement"]')
        self.assertIn("NEAREST_SET_REQUIRES_TWO_DISTINCT_QUERIES", self.codes(self.check(one, ledger="x")))
        same = EVIDENCE.replace('["mask refinement", "inpainting mask expansion"]', '["mask refinement", "Mask refinement"]')
        self.assertIn("NEAREST_SET_REQUIRES_TWO_DISTINCT_QUERIES", self.codes(self.check(same, ledger="x")))

    def test_template_placeholders_are_rejected(self):
        result = self.check(EVIDENCE.replace(
            '["mask refinement", "inpainting mask expansion"]',
            '["x", "inpainting mask expansion"]'), ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("NEAREST_SET_QUERY_INVALID", self.codes(result))
        template_shaped = EVIDENCE.replace(
            '["mask refinement", "inpainting mask expansion"]',
            '["检索式 1（术语/数据库）", "检索式 2（另一种措辞）"]',
        )
        self.assertIn("NEAREST_SET_QUERY_INVALID", self.codes(self.check(template_shaped, ledger="x")))

    def test_future_created_at_is_rejected(self):
        result = self.check(EVIDENCE.replace('"created_at": "2026-10-28"', '"created_at": "2999-01-01"'), ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("NEAREST_SET_CREATED_AT_IN_FUTURE", self.codes(result))

    def test_stale_nearest_set_blocks_delivery(self):
        result = self.check(EVIDENCE.replace('"created_at": "2026-10-28"', '"created_at": "2020-01-01"'), ledger="x")
        self.assertTrue(result["valid"], result["errors"])
        self.assertFalse(result["delivery_ready"])
        self.assertTrue(any("NEAREST_SET_STALE" in warning for warning in result["warnings"]))

    def test_nearest_json_is_never_allowed_to_crash(self):
        array_payload = EVIDENCE.replace(NEAREST, "```nearest-set-json\n[1, 2]\n```")
        self.assertIn("NEAREST_SET_JSON_INVALID", self.codes(self.check(array_payload, ledger="x")))
        broken_json = EVIDENCE.replace(NEAREST, "```nearest-set-json\n{not json\n```")
        self.assertIn("NEAREST_SET_JSON_INVALID", self.codes(self.check(broken_json, ledger="x")))
        wrong_types = EVIDENCE.replace(NEAREST, '```nearest-set-json\n{"schema": "nearest-set-v2", "created_at": 1}\n```')
        typed = self.check(wrong_types, ledger="x")
        self.assertFalse(typed["valid"])
        self.assertIn("NEAREST_SET_CREATED_AT_REQUIRED", self.codes(typed))

    def test_candidate_ids_and_ledgers_must_be_unique(self):
        duplicate_id = EVIDENCE.replace('"id": "P2"', '"id": "P1"')
        self.assertIn("NEAREST_CANDIDATE_DUPLICATE_ID", self.codes(self.check(duplicate_id, ledger="x")))
        duplicate_ledger = EVIDENCE.replace('"ledger": "ledger:E2"', '"ledger": "ledger:E1"')
        self.assertIn("NEAREST_CANDIDATE_DUPLICATE_LEDGER", self.codes(self.check(duplicate_ledger, ledger="x")))

    def test_candidate_ledger_must_resolve(self):
        result = self.check(EVIDENCE.replace('"ledger": "ledger:E2"', '"ledger": "ledger:NOPE"'), ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("NEAREST_CANDIDATE_LEDGER_UNBOUND", self.codes(result))

    def test_candidate_status_cannot_exceed_ledger_scope(self):
        projection = copy.deepcopy(PROJECTION)
        for reading in projection["sources"]["S1"]["readings"]:
            reading["scopes"] = ["section"]
        result = self.check(EVIDENCE, ledger="x", projection=projection)
        self.assertFalse(result["valid"])
        self.assertIn("NEAREST_CANDIDATE_STATUS_EXCEEDS_LEDGER_SCOPE", self.codes(result))

    def test_kill_questions_need_enum_answers_and_locators(self):
        result = self.check(EVIDENCE.replace('"answer": "否", "locator": "§3.2"', '"answer": "也许", "locator": "x"'), ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("NEAREST_KILL_QUESTION_ANSWER_INVALID", self.codes(result))
        self.assertIn("NEAREST_KILL_QUESTION_LOCATOR_INVALID", self.codes(result))

    def test_kill_questions_need_at_least_two(self):
        trimmed = EVIDENCE.replace(
            ',\n                        {"q": "动作集合是否含收缩", "answer": "是", "locator": "§4 / Table 2"}', '')
        self.assertIn("NEAREST_CANDIDATE_NEEDS_TWO_KILL_QUESTIONS", self.codes(self.check(trimmed, ledger="x")))

    # --- claim table and claim binding --------------------------------------
    def test_claim_grade_must_be_abc(self):
        result = self.check(EVIDENCE.replace("| A | P1, P2 |", "| [A/B/C] | P1, P2 |"), ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("CLAIM_GRADE_INVALID", self.codes(result))

    def test_claim_id_must_be_unique_and_known(self):
        duplicate = EVIDENCE.replace("| C2 | P2 的净收益比较与当前路线不同 | B |", "| C1 | P2 的净收益比较与当前路线不同 | B |")
        self.assertIn("CLAIM_ID_DUPLICATE", self.codes(self.check(duplicate, ledger="x")))
        unknown = EVIDENCE.replace("未发现等价机制 [C1]。", "未发现等价机制 [C9]。")
        self.assertIn("CLAIM_ID_UNKNOWN", self.codes(self.check(unknown, ledger="x")))

    def test_claim_table_requires_six_columns(self):
        result = self.check(EVIDENCE.replace(
            "| C2 | P2 的净收益比较与当前路线不同 | B | P2 | ledger:E2 | 若 P2 也等成本比较则不成立 |",
            "| C2 | P2 的净收益比较与当前路线不同 | B | P2 | ledger:E2 |"), ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("CLAIM_TABLE_COLUMNS", self.codes(result))

    def test_a_or_b_claim_with_bad_ledger_fails(self):
        result = self.check(EVIDENCE.replace("| P1, P2 | ledger:E1 |", "| P1, P2 | ledger:NOPE |"), ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("A_B_CLAIM_NOT_IN_NEAREST_SET", self.codes(result))

    def test_a_or_b_claim_must_bind_a_verified_nearest_source(self):
        projection = copy.deepcopy(PROJECTION)
        projection["sources"]["S1"]["readings"] = []
        result = self.check(EVIDENCE, ledger="x", projection=projection)
        self.assertFalse(result["valid"])
        self.assertIn("A_B_CLAIM_NOT_VERIFIED", self.codes(result))

    def test_a_or_b_claim_cannot_bind_unread_candidate(self):
        abstract = EVIDENCE.replace('"status": "section"', '"status": "abstract"').replace(
            '"answer": "是", "locator": "§2"', '"answer": "未读到", "locator": "§2"').replace(
            '"answer": "否", "locator": "§3"', '"answer": "未读到", "locator": "§3"')
        result = self.check(abstract, ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("CLAIM_CANDIDATE_UNREAD", self.codes(result))

    def test_a_grade_must_cover_all_read_nearest(self):
        result = self.check(EVIDENCE.replace("| A | P1, P2 |", "| A | P1 |"), ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("A_CLAIM_MUST_COVER_READ_NEAREST", self.codes(result))

    def test_a_grade_requires_absolute_novelty_wording_removed(self):
        result = self.check(EVIDENCE.replace("与 P1 在动作集合上不同", "首次提出该方向"), ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("A_CLAIM_ABSOLUTE_NOVELTY_WORDING", self.codes(result))

    # --- current-judgment claim-ID contract ---------------------------------
    def test_current_judgment_units_need_claim_id(self):
        paragraph = EVIDENCE.replace(
            "- 下一步：补读 P2 的 §3。",
            "\n动作集合不同，值得投入。\n\n- 下一步：补读 P2 的 §3。",
        )
        result = self.check(paragraph, ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("CURRENT_JUDGMENT_CLAIM_ID_MISSING", self.codes(result))

    def test_plan_units_are_exempt_from_claim_ids(self):
        result = self.check(EVIDENCE.replace("- 下一步：补读 P2 的 §3。", "- 下一步：补读 P2 的 §3，补做一次复现。"), ledger="x")
        self.assertTrue(result["valid"], result["errors"])

    def test_plan_unit_cannot_carry_a_bare_conclusion(self):
        result = self.check(EVIDENCE.replace("- 下一步：补读 P2 的 §3。", "- 下一步：本方向全新，值得投入，直接开做。"), ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("PLAN_UNIT_CONTAINS_JUDGMENT", self.codes(result))

    def test_judgment_terms_outside_claim_sections_need_claim_id(self):
        result = self.check(EVIDENCE.replace("已有证据 [1,2]。", "已有证据 [1,2]。该方向是新颖的，值得做。"), ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("JUDGMENT_OUTSIDE_CLAIM_CONTRACT", self.codes(result))

    def test_blockquote_conclusion_in_current_judgment_needs_claim_id(self):
        result = self.check(EVIDENCE.replace(
            "- 下一步：补读 P2 的 §3。",
            "\n> 该方向首次提出、填补研究空白、值得投入。\n\n- 下一步：补读 P2 的 §3。"), ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("CURRENT_JUDGMENT_CLAIM_ID_MISSING", self.codes(result))

    def test_document_title_with_a_bare_judgment_is_rejected(self):
        result = self.check(EVIDENCE.replace("# 研究报告", "# 研究报告：首次填补研究空白"), ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("JUDGMENT_OUTSIDE_CLAIM_CONTRACT", self.codes(result))

    def test_duplicate_machine_blocks_are_rejected(self):
        duplication = EVIDENCE.replace("## 证据、近邻与差异", NEAREST + "\n\n## 证据、近邻与差异")
        result = self.check(duplication, ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("NEAREST_SET_BLOCK_DUPLICATE", self.codes(result))

    def test_same_source_with_two_ledger_aliases_is_rejected(self):
        result = self.check(EVIDENCE.replace('"ledger": "ledger:E2"', '"ledger": "ledger:S1"'), ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("NEAREST_CANDIDATE_DUPLICATE_SOURCE", self.codes(result))

    def test_candidate_locator_must_match_a_ledger_reading_locator(self):
        result = self.check(EVIDENCE.replace('"locator": "§3.2",\n', '"locator": "§9",\n', 1), ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("NEAREST_CANDIDATE_LOCATOR_NOT_IN_READING", self.codes(result))

    def test_unread_candidate_may_use_no_locator(self):
        unread = EVIDENCE.replace('"status": "section"', '"status": "unseen"').replace(
            '"status": "full_text"', '"status": "unseen"').replace(
            '{"q": "是否比较净收益", "answer": "是", "locator": "§2"}, {"q": "是否等成本比较", "answer": "否", "locator": "§3"}',
            UNREAD_P2).replace(
            "| C1 | 与 P1 在动作集合上不同 | A | P1, P2 | ledger:E1 | 若 P1 也按成本选择动作则不成立 |\n"
            "| C2 | P2 的净收益比较与当前路线不同 | B | P2 | ledger:E2 | 若 P2 也等成本比较则不成立 |",
            "| C1 | 暂定：与其他近邻可能等价 | C | P2 | 摘要级/未读 | 若 P1 §3.2 给出同一机制则不成立 |")
        result = self.check(unread, ledger="x")
        self.assertFalse(any("NEAREST_CANDIDATE_LOCATOR_INVALID" in error for error in result["errors"]),
                         result["errors"])
        self.assertFalse(any("NEAREST_KILL_QUESTION_LOCATOR_INVALID" in error for error in result["errors"]),
                         result["errors"])

    def test_provisional_candidate_must_be_bound_by_the_c_claim(self):
        wrong = c_only().replace(
            "| C1 | 与 P1 在动作集合上不同 | C | P2 |",
            "| C1 | 与 P1 在动作集合上不同 | C | P1 |")
        result = self.check(wrong, ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("PROVISIONAL_CHECK_CANDIDATE_NOT_BOUND", self.codes(result))

    def test_provisional_question_must_still_be_unanswered(self):
        wrong = c_only().replace(
            '"check": {"candidate": "P2", "question": "是否比较净收益", "locator": "无"}',
            '"check": {"candidate": "P2", "question": "是否比较净收益", "locator": "无"}')
        wrong = wrong.replace(
            '"q": "是否比较净收益", "answer": "未读到", "locator": "无"',
            '"q": "是否比较净收益", "answer": "是", "locator": "§2"')
        result = self.check(wrong, ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("PROVISIONAL_CHECK_QUESTION_ALREADY_ANSWERED", self.codes(result))

    def test_provisional_locator_must_match_the_kill_question_locator(self):
        wrong = c_only().replace('"question": "是否比较净收益", "locator": "无"',
                                 '"question": "是否比较净收益", "locator": "§9"')
        result = self.check(wrong, ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("PROVISIONAL_CHECK_LOCATOR_MISMATCH", self.codes(result))

    # --- provisional (C) contract -------------------------------------------
    def test_c_only_report_is_valid_with_provisional_block(self):
        result = self.check(c_only(), ledger="x")
        self.assertTrue(result["valid"], result["errors"])

    def test_c_id_in_current_judgment_needs_qualified_form(self):
        result = self.check(c_only(qualified=False), ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("C_CLAIM_STATED_IN_CURRENT_JUDGMENT", self.codes(result))

    def test_c_id_outside_provisional_section_is_rejected(self):
        result = self.check(c_only().replace("覆盖有限。", "覆盖有限，倾向不同 [C1]。"), ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("C_CLAIM_STATED_OUTSIDE_PROVISIONAL_SECTION", self.codes(result))

    def test_c_claim_requires_provisional_block(self):
        result = self.check(c_only(provisional=""), ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("PROVISIONAL_BLOCK_MISSING", self.codes(result))

    def test_provisional_check_question_must_match_kill_question(self):
        wrong = c_only(provisional=PROVISIONAL.replace('"question": "是否也按成本选择动作"', '"question": "是否按成本选择动作"'))
        result = self.check(wrong, ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("PROVISIONAL_CHECK_QUESTION_NOT_IN_NEAREST", self.codes(result))

    def test_provisional_claims_must_be_complete(self):
        result = self.check(c_only(provisional=PROVISIONAL.replace('"tendency": "倾向与 P1 不同"', '"tendency": ""')),
                            ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("PROVISIONAL_CLAIM_INCOMPLETE", self.codes(result))

    def test_answered_kill_question_locator_must_match_a_reading_locator(self):
        result = self.check(EVIDENCE.replace(
            '{"q": "是否也按成本选择动作", "answer": "否", "locator": "§3.2"}',
            '{"q": "是否也按成本选择动作", "answer": "否", "locator": "§9"}'), ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("NEAREST_KILL_QUESTION_LOCATOR_NOT_IN_READING", self.codes(result))

    def test_read_candidate_needs_a_real_reading_locator(self):
        projection = copy.deepcopy(PROJECTION)
        for reading in projection["sources"]["S1"]["readings"]:
            reading["locator"] = "text"
        result = self.check(EVIDENCE, ledger="x", projection=projection)
        self.assertFalse(result["valid"])
        self.assertIn("NEAREST_CANDIDATE_READING_LOCATOR_MISSING", self.codes(result))

    def test_c_claim_must_bind_a_nearest_candidate(self):
        result = self.check(c_only().replace(
            "| C1 | 与 P1 在动作集合上不同 | C | P2 |",
            "| C1 | 与 P1 在动作集合上不同 | C |  |"), ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("C_CLAIM_CANDIDATE_ID_REQUIRED", self.codes(result))

    def test_h1_with_absolute_novelty_is_rejected(self):
        result = self.check(EVIDENCE.replace("# 研究报告", "# 全新的掩码细化方法"), ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("JUDGMENT_OUTSIDE_CLAIM_CONTRACT", self.codes(result))

    def test_citation_section_scope_locator_must_match_a_reading_locator(self):
        result = self.check(EVIDENCE.replace("| `ledger:S1` | `full_text` |",
                                             "| `ledger:S1` | `section:§9` |"), ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("CITATION_SCOPE_LOCATOR_NOT_IN_READING", self.codes(result))

    def test_citation_section_scope_fails_without_a_reading_locator(self):
        projection = copy.deepcopy(PROJECTION)
        for reading in projection["sources"]["S1"]["readings"]:
            reading["locator"] = "text"
        result = self.check(EVIDENCE.replace("| `ledger:S1` | `full_text` |",
                                             "| `ledger:S1` | `section:§3.2` |"),
                            ledger="x", projection=projection)
        self.assertFalse(result["valid"])
        self.assertIn("CITATION_SCOPE_LOCATOR_NOT_IN_READING", self.codes(result))

    # --- generic contract checks -------------------------------------------
    def test_go_term_is_not_a_label(self):
        result = self.check(CONCEPT.replace("- 未知。", "- GO term enrichment 需要核对。"))
        self.assertTrue(result["valid"], result["errors"])

    def test_hold_label_is_rejected(self):
        result = self.check(CONCEPT.replace("- 未知。", "- 建议HOLD。"))
        self.assertFalse(result["valid"])

    def test_effect_claim_requires_citation(self):
        result = self.check(EVIDENCE.replace("已有证据 [1,2]。", "已有证据 [1,2]。\n\n实验表明提升 15%。"), ledger="x")
        self.assertFalse(result["valid"])
        self.assertIn("UNSUPPORTED_EFFECT_CLAIM", self.codes(result))


class RealLedgerTierTests(unittest.TestCase):
    def _project(self, directory):
        project = pathlib.Path(directory) / "project"
        core = ResearchCore(project)
        judgment = Judgment(core.ledger)
        anchors = []
        for name, text, locator in (
                ("one.txt", "Synthetic source one: a fixture sentence about masks.", "§3.2"),
                ("two.txt", "Synthetic source two: another fixture sentence about actions.", "§2")):
            path = pathlib.Path(directory) / name
            path.write_text(text, encoding="utf-8")
            acquired = core.fetch(local_path=path)
            self.assertTrue(acquired.ok, acquired.errors)
            extra_locators = ["§4 / Table 2"] if locator == "§3.2" else ["§3"]
            first_anchor = ""
            for current_locator in [locator, *extra_locators]:
                quote = core.quote(acquired.data["id"], text, locator=current_locator)
                self.assertTrue(quote.ok, quote.errors)
                judgment.confirm_read(quote.data["id"], "full_text", "synthetic fixture read", human=True)
                if not first_anchor:
                    first_anchor = quote.data["id"]
            anchors.append((acquired.data["id"], first_anchor))
        return project, anchors

    def test_two_local_read_sources_derive_evidence_review(self):
        with tempfile.TemporaryDirectory(prefix="mentor-real-ledger-") as directory:
            project, _ = self._project(directory)
            result = derive_tier(project)
            self.assertTrue(result["chain_ok"], result)
            self.assertTrue(result["artifacts_ok"], result)
            self.assertEqual(result["derived_tier"], "evidence_review", result)

    def test_nearest_and_claim_binding_against_a_real_ledger(self):
        with tempfile.TemporaryDirectory(prefix="mentor-real-draft-") as directory:
            project, anchors = self._project(directory)
            projections = derive_tier(project)
            e1, e2 = anchors[0][1], anchors[1][1]
            body = EVIDENCE.splitlines()
            text = EVIDENCE.replace("ledger:E1", f"ledger:{e1}").replace("ledger:E2", f"ledger:{e2}")
            lines = text.splitlines()
            with mock.patch("research_mentor.draft._today", return_value=dt.date(2026, 10, 30)):
                candidates, uncovered, stale, errors, warnings = draft_module._nearest_contract(lines, projections)
            self.assertFalse(errors, errors)
            self.assertFalse(stale)
            claims, c_ids, claim_errors, claim_warnings = draft_module._claims_contract(
                lines, candidates, uncovered, projections)
            self.assertFalse(claim_errors, claim_errors)
            self.assertIn("C1", claims)
            self.assertEqual(c_ids, set())

    def test_real_ledger_section_reading_cannot_support_full_text_candidate(self):
        with tempfile.TemporaryDirectory(prefix="mentor-real-section-") as directory:
            project = pathlib.Path(directory) / "project"
            anchors = []
            for name, text, locator, scope in (
                    ("one.txt", "Synthetic section-scope source sentence.", "§2", "section"),
                    ("two.txt", "Synthetic full-text source sentence.", "§3", "full_text")):
                core = ResearchCore(project)
                judgment = Judgment(core.ledger)
                path = pathlib.Path(directory) / name
                path.write_text(text, encoding="utf-8")
                acquired = core.fetch(local_path=path)
                self.assertTrue(acquired.ok, acquired.errors)
                quote = core.quote(acquired.data["id"], text, locator=locator)
                self.assertTrue(quote.ok, quote.errors)
                judgment.confirm_read(quote.data["id"], scope, "synthetic fixture read", human=True)
                anchors.append(quote.data["id"])
            projections = derive_tier(project)
            nearest = NEAREST.replace("ledger:E1", f"ledger:{anchors[0]}").replace(
                "ledger:E2", f"ledger:{anchors[1]}")
            text = EVIDENCE.replace(NEAREST, nearest)
            with mock.patch("research_mentor.draft._today", return_value=dt.date(2026, 10, 30)):
                candidates, uncovered, stale, errors, warnings = draft_module._nearest_contract(
                    text.splitlines(), projections)
            self.assertIn("NEAREST_CANDIDATE_STATUS_EXCEEDS_LEDGER_SCOPE", "\n".join(errors))
            self.assertIn("P1", candidates)
            self.assertEqual(candidates["P1"]["status"], "full_text")


class ProtocolTransport:
    """Injected synthetic HTTP protocol; never opens a network connection."""

    def __init__(self, body=b"", headers=None):
        self.body = body
        self.headers = headers or {"content-type": "text/html; charset=utf-8"}
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(url)
        return Response(url, 200, self.headers, self.body, "synthetic_protocol")


class RealLedgerEndToEndTests(unittest.TestCase):
    def test_filled_report_passes_check_draft_with_a_real_ledger(self):
        with tempfile.TemporaryDirectory(prefix="mentor-e2e-") as directory:
            project = pathlib.Path(directory) / "project"
            anchors = []
            for index, (url, locators) in enumerate((("https://example.org/paper-one", ["§3.2", "§4 / Table 2"]),
                                                     ("https://example.org/paper-two", ["§2", "§3"])), 1):
                excerpt = f"SYNTHETIC fetched body {index} about masks and actions."
                core = ResearchCore(project, transport=ProtocolTransport(f"<p>{excerpt}</p>".encode()))
                judgment = Judgment(core.ledger)
                with mock.patch("research_mentor.core.check_outbound"):
                    fetched = core.fetch(url=url, sensitivity="public")
                self.assertTrue(fetched.ok, fetched.errors)
                first_anchor = ""
                for locator in locators:
                    quote = core.quote(fetched.data["id"], excerpt, locator=locator)
                    self.assertTrue(quote.ok, quote.errors)
                    judgment.confirm_read(quote.data["id"], "full_text", "synthetic fixture read", human=True)
                    if not first_anchor:
                        first_anchor = quote.data["id"]
                anchors.append((url, first_anchor))
            (url1, a1), (url2, a2) = anchors
            report = f"""# 研究报告

<!-- report-tier: evidence_review -->

## 当前判断与下一步

- 在已核验的两篇近邻内未发现等价机制 [C1]。
- 相对最近工作的差异：动作集合不同 [C2]。
- 下一步：补读 P2 的 §4。

## 附录：机器可读块

### 近邻选择与深读记录

```nearest-set-json
{{
  "schema": "nearest-set-v2",
  "created_at": "2026-10-28",
  "queries": ["mask refinement", "inpainting mask expansion"],
  "candidates": [
    {{"id": "P1", "title": "Synthetic URL Paper One", "rationale": "动作集合与掩码路线最接近",
      "status": "full_text", "reader": "user", "ledger": "ledger:{a1}", "locator": "§3.2",
      "kill_questions": [{{"q": "是否也按成本选择动作", "answer": "否", "locator": "§3.2"}},
                         {{"q": "动作集合是否含收缩", "answer": "是", "locator": "§4 / Table 2"}}]}},
    {{"id": "P2", "title": "Synthetic URL Paper Two", "rationale": "另一种掩码扩展路线，可能遗漏术语",
      "status": "section", "reader": "model", "ledger": "ledger:{a2}", "locator": "§2",
      "kill_questions": [{{"q": "是否比较净收益", "answer": "是", "locator": "§2"}},
                         {{"q": "是否等成本比较", "answer": "否", "locator": "§3"}}]}}
  ],
  "uncovered": ["可能漏掉的多模态近邻簇"]
}}
```

### 主张—证据等级

| 编号 | 主张 | 等级 | 近邻 | 依据 | 翻转条件 |
| --- | --- | --- | --- | --- | --- |
| C1 | 与 P1 在动作集合上不同 | A | P1, P2 | ledger:{a1} | 若 P1 也按成本选择动作则不成立 |
| C2 | P2 的净收益比较与当前路线不同 | B | P2 | ledger:{a2} | 若 P2 也等成本比较则不成立 |

## 证据、近邻与差异

已有证据 [1,2]。

## 覆盖边界与待核验清单

覆盖有限。

## 参考文献

| 编号 | 文献标题 | 标识 | 账本绑定 | 阅读范围 |
| --- | --- | --- | --- | --- |
| [1] | Synthetic URL Paper One | `url:{url1}` | `ledger:{a1}` | `full_text` |
| [2] | Synthetic URL Paper Two | `url:{url2}` | `ledger:{a2}` | `full_text` |
"""
            from research_mentor.draft import derive_tier
            projections = derive_tier(project)
            self.assertTrue(all(source.get("title") is None for source in projections["sources"].values()))
            draft = pathlib.Path(directory) / "draft.md"
            draft.write_text(report, encoding="utf-8")
            with mock.patch("research_mentor.draft._today", return_value=dt.date(2026, 10, 30)):
                result = check_draft(draft, ledger=project)
            self.assertTrue(result["valid"], result["errors"])
            self.assertTrue(result["delivery_ready"], result["warnings"])

if __name__ == "__main__":
    unittest.main()
