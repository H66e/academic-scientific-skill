"""Structural draft-check tests; synthetic text only, no scientific claims."""
from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

SKILL = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SKILL / "runtime"))

from research_mentor.draft import check_draft


CONCEPT = """# 概念备忘录

> 概念备忘录：引用未核验，不能当作证据审查。

<!-- report-tier: concept_memo -->

## 当前判断与下一步

- 值不值得研究：未知。
- 差异：未确认。
- 能否验证：未知。

## 近邻

一个未核验条目 [1]。

## 参考文献

| 编号 | 条目 | 状态 |
| --- | --- | --- |
| [1] | SYNTHETIC user draft reference | 待核验/未读全文 |
"""

PLAN = """# 研究计划

<!-- report-tier: research_plan -->

## 当前判断与下一步

三问回答见下。

一个已核验来源 [1]。

## 2.2 研究问题、假设与判据

- H1：可检验假设。

## 4 实验设计

| 集合 | 规模 | 用途 |
| --- | --- | --- |
| 训练 | 10 | 合成 |

## 参考文献

| 编号 | 条目 | 状态 |
| --- | --- | --- |
| [1] | SYNTHETIC verified reference | 已核验/已读全文 |
"""


class DraftCheckTests(unittest.TestCase):
    def check(self, text):
        with tempfile.TemporaryDirectory(prefix="mentor-draft-") as directory:
            path = pathlib.Path(directory) / "draft.md"
            path.write_text(text, encoding="utf-8")
            return check_draft(path)

    def test_concept_memo_allows_unverified_with_banner(self):
        result = self.check(CONCEPT)
        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(result["tier"], "concept_memo")
        self.assertEqual(result["stats"]["unverified_citations"], 1)

    def test_research_plan_with_verified_source_is_valid(self):
        result = self.check(PLAN)
        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(result["stats"]["verified_citations"], 1)

    def test_research_plan_cannot_cite_unverified(self):
        result = self.check(PLAN.replace("已核验/已读全文", "待核验/未读全文"))
        self.assertFalse(result["valid"])
        self.assertTrue(any("unverified" in error for error in result["errors"]))

    def test_missing_tier_is_invalid(self):
        result = self.check(PLAN.replace("<!-- report-tier: research_plan -->", ""))
        self.assertFalse(result["valid"])
        self.assertTrue(any("report-tier" in error for error in result["errors"]))

    def test_user_facing_labels_are_invalid(self):
        result = self.check(PLAN + "\n当前建议：HOLD。\n")
        self.assertFalse(result["valid"])
        self.assertTrue(any("labels" in error for error in result["errors"]))
        result = self.check(PLAN + "\n当前建议：做/等/放弃。\n")
        self.assertFalse(result["valid"])
        self.assertTrue(any("做/等/放弃" in error for error in result["errors"]))

    def test_planned_marker_in_result_section_is_invalid(self):
        result = self.check(PLAN.replace("## 4 实验设计", "## 结果\n\n[PLANNED: 尚未执行]\n\n## 4 实验设计"))
        self.assertFalse(result["valid"])
        self.assertTrue(any("planned material" in error for error in result["errors"]))

    def test_inline_citation_without_entry_is_invalid(self):
        result = self.check(PLAN.replace("| [1] | SYNTHETIC verified reference | 已核验/已读全文 |", ""))
        self.assertFalse(result["valid"])
        self.assertTrue(any("no reference entry" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
