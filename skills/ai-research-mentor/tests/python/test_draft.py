"""Tier-contract tests; synthetic text and real local ledgers only."""
from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest
from unittest import mock

SKILL = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SKILL / "runtime"))

from research_mentor.core import ResearchCore
from research_mentor.draft import check_draft, derive_tier
from research_mentor.judgment import Judgment

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
            "readings": [{"anchor": "E1", "scopes": ["full_text"], "locator": "text"}],
        },
        "S2": {
            "canonical": "arxiv:2401.00002",
            "title": "Synthetic Paper Two",
            "doi": None,
            "arxiv": "2401.00002v1",
            "version": "v1",
            "url": None,
            "readings": [{"anchor": "E2", "scopes": ["full_text"], "locator": "text"}],
        }
    },
    "anchor_to_source": {"E1": "S1", "E2": "S2"},
}

EVIDENCE = """# 研究报告

<!-- report-tier: evidence_review -->

## 当前判断与下一步

两个已核验来源 [1,2]。

## 近邻选择与深读记录

```nearest-set-json
{
  "created_at": "2026-10-28",
  "queries": ["mask refinement", "inpainting mask expansion"],
  "candidates": [
    {"id": "P1", "rationale": "动作集合相近", "status": "full_text", "reader": "model", "ledger": "ledger:E1", "locator": "§3",
     "kill_questions": [{"q": "是否按成本选择动作", "answer": "否", "locator": "§3"}, {"q": "动作是否含收缩", "answer": "是", "locator": "§4"}]},
    {"id": "P2", "rationale": "另一种掩码路线", "status": "section", "reader": "user", "ledger": "ledger:E2", "locator": "§2",
     "kill_questions": [{"q": "是否比较净收益", "answer": "未读到", "locator": "§2"}, {"q": "是否等成本", "answer": "未读到", "locator": "§3"}]}
  ]
}
```

## 主张—证据等级

| 编号 | 主张 | 等级 | 依据 | 翻转条件 |
| --- | --- | --- | --- | --- |
| C1 | 与 P1 在动作集合上不同 | A | ledger:E1 | 若 P1 也按成本选择动作则不成立 |

## 证据、近邻与差异

已有证据。

## 覆盖边界与待核验清单

覆盖有限。

## 参考文献

| 编号 | 文献标题 | 标识 | 账本绑定 | 阅读范围 |
| --- | --- | --- | --- | --- |
| [1] | Synthetic Paper | arXiv:2401.00001v1 | ledger:S1 | full_text |
| [2] | Synthetic Paper Two | arXiv:2401.00002v1 | ledger:S2 | full_text |
"""


class DraftContractTests(unittest.TestCase):
    def check(self, text, ledger=None, projection=PROJECTION):
        with tempfile.TemporaryDirectory(prefix="mentor-draft-") as directory:
            path = pathlib.Path(directory) / "draft.md"
            path.write_text(text, encoding="utf-8")
            with mock.patch("research_mentor.draft.derive_tier", return_value=projection):
                return check_draft(path, ledger=ledger)

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
        self.assertTrue(any("LEDGER_REQUIRED" in error for error in result["errors"]))

    def test_declared_tier_above_derived_fails(self):
        plan = EVIDENCE.replace("evidence_review", "research_plan")
        result = self.check(plan, ledger="x")
        self.assertFalse(result["valid"])
        self.assertTrue(any("TIER_EXCEEDS_EVIDENCE" in error for error in result["errors"]))

    def test_valid_evidence_review_with_bound_identity(self):
        result = self.check(EVIDENCE, ledger="x")
        self.assertTrue(result["valid"], result["errors"])

    def test_identity_mismatch_is_rejected(self):
        result = self.check(EVIDENCE.replace("arXiv:2401.00001v1", "arXiv:2401.99999v1"), ledger="x")
        self.assertFalse(result["valid"])
        self.assertTrue(any("CITATION_IDENTITY_MISMATCH" in error for error in result["errors"]))

    def test_duplicate_source_binding_is_rejected(self):
        duplicate = EVIDENCE.replace(
            "| [2] | Synthetic Paper Two | arXiv:2401.00002v1 | ledger:S2 | full_text |",
            "| [2] | Synthetic Paper | arXiv:2401.00001v1 | ledger:S1 | full_text |",
        )
        result = self.check(duplicate, ledger="x")
        self.assertFalse(result["valid"])
        self.assertTrue(any("DUPLICATE_SOURCE" in error for error in result["errors"]))

    def test_reference_trailing_content_is_rejected(self):
        for suffix in ("\n**结果**\n提升 15%。", "\n结果\n---\n提升 15%。", "\n<p>提升 15%</p>"):
            with self.subTest(suffix=suffix):
                result = self.check(EVIDENCE + suffix, ledger="x")
                self.assertFalse(result["valid"])
                self.assertTrue(any("CONTENT_AFTER_REFERENCES" in error for error in result["errors"]))

    def test_research_plan_without_citations_cannot_claim_results(self):
        plan = """<!-- report-tier: research_plan -->

## 当前判断与下一步

实验表明本方法提升 15%。

## 研究问题、假设与判据

- H1

## 方法与实验设计

10 个样本。

## 风险与继续/停止判据

无。
"""
        result = self.check(plan)
        self.assertFalse(result["valid"])
        self.assertTrue(any("NO_VERIFIED_CITATIONS" in error for error in result["errors"]))

    def test_nearest_selection_requires_two_queries(self):
        result = self.check(EVIDENCE.replace('"queries": ["mask refinement", "inpainting mask expansion"]', '"queries": ["mask refinement"]'), ledger="x")
        self.assertFalse(result["valid"])
        self.assertTrue(any("NEAREST_SET_REQUIRES_TWO_DISTINCT_QUERIES" in error for error in result["errors"]))

    def test_c_claim_must_be_provisional(self):
        c_claim = EVIDENCE.replace(
            "| C1 | 与 P1 在动作集合上不同 | A | ledger:E1 | 若 P1 也按成本选择动作则不成立 |",
            "| C1 | 与 P1 在动作集合上不同 | C | 摘要级/未读 | 若 P1 也按成本选择动作则不成立 |",
        )
        result = self.check(c_claim, ledger="x")
        self.assertFalse(result["valid"])
        self.assertTrue(any("C_CLAIM_SECTION_INCOMPLETE" in error for error in result["errors"]))

    def test_a_or_b_claim_with_bad_ledger_fails(self):
        result = self.check(EVIDENCE.replace("ledger:E1", "ledger:NOPE"), ledger="x")
        self.assertFalse(result["valid"])
        self.assertTrue(any("A_B_CLAIM_NOT_VERIFIED" in error for error in result["errors"]))

    def test_c_only_report_is_valid_if_provisional_section_is_complete(self):
        c_only = EVIDENCE.replace(
            "| C1 | 与 P1 在动作集合上不同 | A | ledger:E1 | 若 P1 也按成本选择动作则不成立 |",
            "| C1 | 与 P1 在动作集合上不同 | C | 摘要级/未读 | 若 P1 也按成本选择动作则不成立 |",
        ).replace(
            "## 证据、近邻与差异",
            "## 暂定判断（C 级）\n\n- 暂定判断：倾向不同 [C1]，置信低。\n- 翻转条件：若 P1 也按成本选择动作则不成立。\n- 最小核验：读 P1 §3。\n- 获取路径：arXiv。\n\n## 证据、近邻与差异",
        )
        result = self.check(c_only, ledger="x")
        self.assertTrue(result["valid"], result["errors"])

    def test_go_term_is_not_a_label(self):
        result = self.check(CONCEPT.replace("- 未知。", "- GO term enrichment 需要核对。"))
        self.assertTrue(result["valid"], result["errors"])

    def test_hold_label_is_rejected(self):
        result = self.check(CONCEPT.replace("- 未知。", "- 建议HOLD。"))
        self.assertFalse(result["valid"])


class RealLedgerTierTests(unittest.TestCase):
    def test_two_local_read_sources_derive_evidence_review(self):
        with tempfile.TemporaryDirectory(prefix="mentor-real-ledger-") as directory:
            project = pathlib.Path(directory) / "project"
            core = ResearchCore(project)
            judgment = Judgment(core.ledger)
            for name, text in (("one.txt", "Synthetic source one: a fixture sentence."),
                               ("two.txt", "Synthetic source two: another fixture sentence.")):
                path = pathlib.Path(directory) / name
                path.write_text(text, encoding="utf-8")
                acquired = core.fetch(local_path=path)
                self.assertTrue(acquired.ok, acquired.errors)
                quote = core.quote(acquired.data["id"], text)
                self.assertTrue(quote.ok, quote.errors)
                judgment.confirm_read(quote.data["id"], "full_text", "synthetic fixture read", human=True)
            result = derive_tier(project)
            self.assertTrue(result["chain_ok"], result)
            self.assertTrue(result["artifacts_ok"], result)
            self.assertEqual(result["derived_tier"], "evidence_review", result)


if __name__ == "__main__":
    unittest.main()
