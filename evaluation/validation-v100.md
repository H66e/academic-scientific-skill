# 0.10.0 发布验收记录

日期：2026-10-27。第二轮复审后的结构性修复：核验状态改为账本派生，报告等级变成交付合同。设计见 [ADR 0015](../docs/decisions/0015-ledger-derived-draft-contracts.md)。

## 变化

- `check-draft` 不再接受“已核验/已读全文”自填字符串：非 concept 等级的参考文献条目必须写 `ledger:<source-or-evidence-id>`，并带 `--ledger <project>`；只有账本中 user/T1、scope=section/full_text 的有效 `reading.confirm` 才算核验。修掉 `unverified` 被子串误判为 verified 的真 bug。
- 等级变成章节合同：`concept_memo` 禁止编号引用、参考文献、实验设计、统计、预算、结果，必须有可见“概念备忘录 + 未核验”横幅；`evidence_review` / `preregistration` / `research_plan` 各有必需与禁止章节。
- 对抗检查：`[2,3]` 以外的作者-年份/DOI/URL/脚注引用、`unverified` 子串、汉字紧邻标签、setext/HTML/加粗标题、参考文献后藏正文、量化效应断言、完成态断言、交通灯 emoji。
- 报告模板改为四级轮廓，只保留所选等级；删除预写的“作者已核对/AI 未生成未核验引用”等未发生陈述。
- 清理残留：问题数统一“2–3 个阻塞问题，最多 4 个”；venue 缺失时内容可写但格式标待用户提供；删除 `"decision": "HOLD"` 示例；修正安装后脚本路径；README 验收链接改为最新。
- effect-protocol 改为三项 co-primary（不存在的引用率、不支持的引用率、近邻召回、可执行性中的三项），去掉 composite 权重与决策冲突；仍未执行。

## 本地检查

| 检查 | 实际结果 | 边界 |
| --- | --- | --- |
| `python -B evaluation/run-python-tests.py` | **309 tests，OK，skipped=1** | 合成语料与合同测试；不是科研效果证明 |
| `check-skill` | valid；63 条技能内链接、111 行入口 | 结构/链接检查 |
| `check-examples` | valid；GO/GO/HOLD 三个合成示例 | 示例为虚构数据；标签是 runtime 用例状态 |
| `check-templates` | valid；paper/survey/proposal/report 四份模板结构标记齐全 | 只验证结构标记，不验证引用真实性或写作质量 |
| `check-python-only` | valid；151 个文件 | 只排除语言/清单 |
| `package` | 56 个文件、720,699 字节、SHA-256 `32e0451f…` | 发布包构建产物，不入 Git |
| `check-package` | valid，`deterministic: true` | 确定性不等于科学正确性 |
| `research_draft.py`（概念备忘录） | valid；tier=`concept_memo`；无错误无警告；`delivery_ready=true` | 只证明结构/账本记录一致 |

## 行为检查

- 新增对抗测试覆盖：concept_memo 无编号引用、拒绝作者-年份/DOI/URL、拒绝实验设计章节；非概念等级无 `--ledger` 失败；伪造“已核验”字符串失败；未知 ledger ID 失败；汉字紧邻 `HOLD` 失败；`[1,2]` 引用解析；缺 tier 失败。
- `_ledger_verified` 只承认 `actor=user`、`trust=T1`、`scope in {section, full_text}` 的 `reading.confirm`；账本读取失败 fail-closed。
- 概念备忘录模板与演示报告已按新合同裁剪；旧完整报告移到 `output/reports/legacy-pre-010/`，不再作为交付。

## 未覆盖范围与诚实声明

- **没有效果证据**：未执行 effect-protocol；没有真实用户研究或外部盲评。评审的核心批评（“没有证明比裸强模型更好”）仍未解决。
- **账本 ID ≠ 论断支持**：checker 只证明该来源被 user/T1 读过相应范围，不证明它支持某一句话；这一限制写在代码与验收记录中。
- 章节白名单与量化断言检查是启发式，可能误报/漏报；它不能替代人工核验。
- `concept_memo` 不得出现引用，可能让一些需要背景引用的短报告被迫升级；这是有意的权衡。
- 账本、dossier、`python-credibility-v5` 与全部门控行为未变；本机结果不替代 Linux 或 Python 3.10/3.12 的实际执行。
