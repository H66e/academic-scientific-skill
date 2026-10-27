# 0.5.0 发布验收记录

日期：2026-10-27。本地环境：Windows、CPython 3.14.5、无 Node。本版是范围收窄版本：结果解释软退役，写作扩到完整初稿。设计与兼容性边界见 [ADR 0010](../docs/decisions/0010-scope-refocus-0.5.0.md)；以下均为本机实际执行结果，CI 矩阵在推送后独立执行。

## 范围变化

- 技能只保留四项工作：找方向、查新、判断方向值不值得做、写论文/综述/开题；`SKILL.md` 的结果分类章节、试验/负结果路由与 `feedback.md` 已移除。
- 结果解释退役：`record-result` / `reclassify-result` / `invalidate-result` / `results` 四个 CLI 命令与对应 `Judgment` 方法删除；判定策略升为 `python-credibility-v5`，assess 不读取结果、快照摘要排除结果事件、结果型 KILL 移除；文献证据矛盾、duplicate/mechanism_equivalence 与已确认约束的 KILL 保留。
- 兼容：账本 17 类事件词表、`event_payloads` 准入与 `results.py` 校验器保留，旧账本仍可 `verify-ledger` / `verify-artifacts`；`export-dossier` 保留结果投影但标注为历史声明；dossier 合同（schema 3 / decision contract 3）及其 pilots/result_invalidations 字段由维护栈只读支持。
- 写作：`research-outputs.md` 扩为完整写作工作流，新增 `templates/paper.md`、`templates/survey.md`、`templates/proposal.md`；完整初稿只允许基于真实提供/获取的来源，禁止编造引用、数字、实验、结果与 venue 规则，未执行实验标为计划，投稿前必须人工核验。

## 本地检查

| 检查 | 实际结果 | 边界 |
| --- | --- | --- |
| `python -B evaluation/run-python-tests.py` | **291 tests，OK，skipped=1** | 合成语料与注入协议；不是科研效果证明 |
| `check-skill` | valid；47 条技能内链接、107 行入口 | 结构/链接检查 |
| `check-examples` | valid；GO/GO/HOLD 三个合成示例 | 示例为虚构数据 |
| `check-python-only` | valid；133 个文件 | 只排除语言/清单 |
| `package` | 51 个文件、677,386 字节、SHA-256 `22604650…` | 发布包构建产物，不入 Git |
| `check-package` | valid，`deterministic: true`：两次独立构建逐字节一致 | 确定性不等于科学正确性 |

## 结果退役的实测证据

- 删除的测试：`skills/ai-research-mentor/tests/python/test_results.py`（13 用例：结果记录/纠正/失效/查询生命周期）、`evaluation/tests/test_result_cli.py`（2 用例：四个结果 CLI）、`evaluation/tests/test_result_conformance.py`（7 用例：结果 fold 与冻结生命周期一致性）。这些是行为退役，不是删除证据；原用例仍可在 `v0.4.0` tag 取得。
- 新增/更新的反向与兼容测试（`evaluation/tests/test_python_contract.py`）：含 legacy `contradicted` result 的旧账本在 v5 下仍可给出 GO，且 `legacy_result_events_ignored` 可见且不进入 `missing`；旧账本 `verify-ledger`/`verify-artifacts` 通过；`export-dossier` 仍投影 pilots/result_invalidations 并标明历史声明；快照与不含结果事件的账本一致；四个结果命令不再注册。
- `test_ledger_payloads.py` 仍覆盖 17 类事件（含 `result.record`/`result.invalidate` 的旧 payload 准入）；`test_reading_contract.py` 的策略断言改为 v5；`test_evolution.py` 的自优化可编辑清单把已删除的 `feedback.md` 换成 `research-outputs.md`，并对冻结基线 batch 2 只做该路径的显式迁移比较。
- 未修改任何 frozen fixture；`evaluation/fixtures/result-lifecycle.json` 仍由 dossier 维护栈的 `test_audit.py` 使用。

## CI

同一提交在 GitHub Actions 的 6 个矩阵作业（Ubuntu/Windows × Python 3.10/3.12/3.14）全部成功；构建与校验步骤按上方本地命令执行，发布包另存为运行产物（run 记录附于 Release 说明）。

## 未覆盖范围

- 真实选题、查新、gap、写作质量仍未测量；模板与检查只保证结构与来源边界，不保证内容正确或可发表。
- 旧账本升级后，含退役结果事件的评审一律过期，需要人工重评；工具不迁移、不改写旧评审，也不能阻止第三方直接 `Ledger.append` 旧结果事件（文档已声明其非受支持工作流）。
- 0.4.x 可结构读取含 v5 评审的账本，但 v5 评审在旧版本中显示过期，不能当作有效决定；升降级都需要重评。
- 需要结果登记的用途停留在 0.4.x；PDF 抽取、实验日志解释、ledger↔dossier 无损互转仍不在范围。
- 本机结果不替代 Linux 或 Python 3.10/3.12 的实际执行；矩阵结果以 Actions 记录为准。
