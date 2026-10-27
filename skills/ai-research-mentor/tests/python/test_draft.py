"""Structural draft-contract tests; synthetic text only, no scientific claims."""
from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest
from unittest import mock

SKILL = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SKILL / "runtime"))

from research_mentor.draft import check_draft


CONCEPT = """# 概念备忘录

<!-- report-tier: concept_memo -->

> 概念备忘录：引用未核验，不能当作证据审查。

## 当前判断与下一步

- 值不值得研究：未知。
- 差异：未确认。
- 能否验证：未知。

## 待核验清单

- Smith et al. 的结论尚未读全文。
"""

PLAN = """# 研究计划

<!-- report-tier: research_plan -->

## 当前判断与下一步

三问回答见下。已有来源 [1]。

## 2.2 研究问题、假设与判据

- H1：可检验假设。

## 4 实验设计

| 集合 | 规模 | 用途 |
| --- | --- | --- |
| 训练 | 10 | 合成 |

## 7 风险与应对

- 风险：无效。

## 参考文献

| 编号 | 条目 | 状态 |
| --- | --- | --- |
| [1] | SYNTHETIC verified reference | ledger:E1 |
"""


class DraftCheckTests(unittest.TestCase):
    def check(self, text, ledger=None):
        with tempfile.TemporaryDirectory(prefix="mentor-draft-") as directory:
            path = pathlib.Path(directory) / "draft.md"
            path.write_text(text, encoding="utf-8")
            return check_draft(path, ledger=ledger)

    def test_concept_memo_without_citations_is_valid(self):
        result = self.check(CONCEPT)
        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(result["tier"], "concept_memo")
        self.assertTrue(result["delivery_ready"])

    def test_concept_memo_rejects_numbered_citation(self):
        result = self.check(CONCEPT.replace("Smith et al. 的结论尚未读全文。", "已有结论 [1]。"))
        self.assertFalse(result["valid"])
        self.assertTrue(any("must not contain numbered citations" in error for error in result["errors"]))

    def test_concept_memo_rejects_author_year_and_doi(self):
        for addition in ("(Smith, 2023) 证明有效。", "doi:10.1234/example", "https://example.org/paper"):
            with self.subTest(addition=addition):
                result = self.check(CONCEPT + "\n" + addition)
                self.assertFalse(result["valid"])

    def test_concept_memo_rejects_experiment_section(self):
        result = self.check(CONCEPT + "\n## 4 实验设计\n\n样本量 20，预算 3 万。\n")
        self.assertFalse(result["valid"])
        self.assertTrue(any("forbidden section" in error or "forbidden content" in error for error in result["errors"]))

    def test_research_plan_requires_ledger(self):
        result = self.check(PLAN)
        self.assertFalse(result["valid"])
        self.assertTrue(any("requires --ledger" in error for error in result["errors"]))

    def test_research_plan_with_ledger_verified_entry_is_valid(self):
        with mock.patch("research_mentor.draft._ledger_verified", return_value=({"E1"}, {"SRC1"})):
            result = self.check(PLAN, ledger="ignored")
        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(result["stats"]["citations_used"], 1)

    def test_self_declared_verification_is_rejected(self):
        with mock.patch("research_mentor.draft._ledger_verified", return_value=({"E1"}, {"SRC1"})):
            result = self.check(PLAN.replace("ledger:E1", "已核验/已读全文"), ledger="ignored")
        self.assertFalse(result["valid"])
        self.assertTrue(any("must use ledger:" in error for error in result["errors"]))

    def test_unknown_ledger_id_is_rejected(self):
        with mock.patch("research_mentor.draft._ledger_verified", return_value=({"E1"}, {"SRC1"})):
            result = self.check(PLAN.replace("ledger:E1", "ledger:E999"), ledger="ignored")
        self.assertFalse(result["valid"])
        self.assertTrue(any("not verified" in error for error in result["errors"]))

    def test_unverified_substring_is_not_accepted(self):
        with mock.patch("research_mentor.draft._ledger_verified", return_value=({"E1"}, {"SRC1"})):
            result = self.check(PLAN.replace("ledger:E1", "unverified"), ledger="ignored")
        self.assertFalse(result["valid"])
        self.assertTrue(any("must use ledger:" in error for error in result["errors"]))

    def test_labels_are_rejected_even_next_to_chinese(self):
        for addition in ("建议HOLD", "做/等/放弃", "🟢"):
            with self.subTest(addition=addition):
                result = self.check(CONCEPT + "\n" + addition)
                self.assertFalse(result["valid"])

    def test_missing_tier_is_invalid(self):
        result = self.check(PLAN.replace("<!-- report-tier: research_plan -->", ""))
        self.assertFalse(result["valid"])
        self.assertTrue(any("report-tier" in error for error in result["errors"]))

    def test_citation_list_is_parsed(self):
        plan = PLAN.replace("[1] | SYNTHETIC verified reference", "[1] | A").replace(
            "| [1] | A | ledger:E1 |", "| [1] | A | ledger:E1 |\n| [2] | B | ledger:E1 |"
        ).replace("三问回答见下。", "三问回答见下 [1,2]。")
        with mock.patch("research_mentor.draft._ledger_verified", return_value=({"E1"}, {"SRC1"})):
            result = self.check(plan, ledger="ignored")
        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(result["stats"]["citations_used"], 2)


if __name__ == "__main__":
    unittest.main()
