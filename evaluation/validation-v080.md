# 0.8.0 发布验收记录

日期：2026-10-27。本地环境：Windows、CPython 3.14.5、无 Node。本版只改用户面向判断的表达方式：报告、决策卡与对话不再默认输出 GO/HOLD/KILL 标签，改为回答三件事并给出证据、未知、下一步与改变判断的判据。设计与替代方案见 [ADR 0013](../docs/decisions/0013-no-go-hold-kill-labels.md)。

## 变化

- `SKILL.md` 的“判断与决策”不再定义 GO/HOLD/KILL 作为用户建议，而是要求回答：值不值得研究；相对最近工作的差异（机制/条件/可检验预测）；在当前真实约束下能否做有意义的验证。随后给决定性依据、最强反方、未知、下一步和“什么结果会改变判断”。
- 报告模板新增“当前判断与下一步”节，明确不写标签；`research-outputs.md` 的报告结构、质量检查和轻量决策卡说明同步改为三问 + 下一步。
- `evaluation.md` 把 GO/HOLD/KILL 明确标注为账本内部状态；Python 账本、dossier 合同、排序和人工决定绑定继续使用，只有用户明确要求对接账本/合同字段时才出现，并标明它不是研究结论。
- 运行时、schema、`python-credibility-v5` 判定与全部门控行为不变；冻结示例与 dossier fixtures 保留原标签。改动属于 prompt/reference/template 层。

## 本地检查

| 检查 | 实际结果 | 边界 |
| --- | --- | --- |
| `python -B evaluation/run-python-tests.py` | **296 tests，OK，skipped=1** | 合成语料与注入协议；不是科研效果证明 |
| `check-skill` | valid；62 条技能内链接、117 行入口 | 结构/链接检查 |
| `check-examples` | valid；GO/GO/HOLD 三个合成示例 | 示例为虚构数据；标签是 runtime 示例，不是报告默认输出 |
| `check-templates` | valid；paper/survey/proposal/report 四份模板结构标记齐全 | 只验证结构标记，不验证引用真实性或写作质量 |
| `check-python-only` | valid；143 个文件 | 只排除语言/清单 |
| `package` | 53 个文件、703,497 字节、SHA-256 `f689289b…` | 发布包构建产物，不入 Git |
| `check-package` | valid，`deterministic: true`：两次独立构建逐字节一致 | 确定性不等于科学正确性 |

## 行为检查

- `SKILL.md` 用户面向段不再提供 GO/HOLD/KILL 定义；`evaluation.md` 顶层明确把三者标为“账本内部状态”。
- 报告模板的“当前判断与下一步”只包含三问答案、下一步与判据，不含标签。
- 旧维护轮的冻结示例、dossier fixtures 与 runtime 测试未改；`check-examples` 的 GO/GO/HOLD 仍表示 runtime 用例状态，且该检查本身注明“示例为虚构数据”。
- `output/reports/` 中的 v0.2 演示生成于 0.7.0，仍含 HOLD 标签；它作为历史产物保留，不代表 0.8.0 的报告默认输出。

## 未覆盖范围

- 本版不改变“什么算值得做”的科学标准，只改变表达方式；没有真实用户研究验证“去标签是否减少误判”这一假设，需要后续人工盲评或访谈。
- 三问答案仍依赖真实来源、近邻比较与可行性证据；没有证据时仍只能写“未确认/待补证”，不能用更长的文字代替证据。
- 运行时、账本、dossier 与判定策略未变；本机结果不替代 Linux 或 Python 3.10/3.12 的实际执行。
