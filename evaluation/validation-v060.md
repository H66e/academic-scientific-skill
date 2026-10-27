# 0.6.0 发布验收记录

日期：2026-10-27。本地环境：Windows、CPython 3.14.5、无 Node。本版只改自进化/维护能力：写作模板纳入受控进化范围，验收回执逻辑收紧。设计与替代方案见 [ADR 0011](../docs/decisions/0011-evolvable-templates-and-stricter-receipts.md)；科研范围与 `python-credibility-v5` 判定策略不变。

## 变化

- 可改白名单：在 `SKILL.md` 与 literature/ideation/evaluation/research-outputs 四份细则之外，加入 `templates/paper.md`、`survey.md`、`proposal.md`；运行时、脚本、schema、测试、评测规则、data-contract 与自优化协议仍是保护文件，suite 不能扩大白名单。
- 模板护栏：任何 `templates/` 改动都必须附带通过且绑定当前基线/候选/suite 指纹的 `writing_template_guardrails` 检查。该检查由新增的 `python -B evaluation/skill_tools.py check-templates` 生成，验证“禁止编造”、`TODO(需来源)`、计划/已观察或事实/假设/计划/风险结构；CI 也会运行。
- 回执逻辑：`better` / `worse` 判定必须对应不同的基线/候选输出哈希；完全相同只能记 `tie` 或重跑。其余 KEEP 条件（独立评审、全部执行、硬条件、无退化、至少一个 target 改善）不变。
- 兼容：自进化仍只读、不自动应用、不自动推送；文件集合与检查契约变化后，旧维护轮的 suite、快照与回执不能复用，需从 0.6.0 重新冻结基线。

## 本地检查

| 检查 | 实际结果 | 边界 |
| --- | --- | --- |
| `python -B evaluation/run-python-tests.py` | **295 tests，OK，skipped=1** | 合成语料与注入协议；不是科研效果证明 |
| `check-skill` | valid；50 条技能内链接、107 行入口 | 结构/链接检查 |
| `check-examples` | valid；GO/GO/HOLD 三个合成示例 | 示例为虚构数据 |
| `check-templates` | valid；paper/survey/proposal 三份模板结构标记齐全 | 只验证结构标记，不验证引用真实性或写作质量 |
| `check-python-only` | valid；136 个文件 | 只排除语言/清单 |
| `package` | 51 个文件、680,613 字节、SHA-256 `2e761d5d…` | 发布包构建产物，不入 Git |
| `check-package` | valid，`deterministic: true`：两次独立构建逐字节一致 | 确定性不等于科学正确性 |

## 自进化逻辑的定向测试

- 模板改动：候选修改 `templates/paper.md` 且 suite 允许该路径时，缺少 `writing_template_guardrails` 检查得到 HOLD（原因含 “missing required check”）；补上通过且绑定指纹的检查后得到 KEEP。
- 输出差异：target 用例标记 `better` 但 baseline/candidate 输出为同一文件与哈希时得到 HOLD（原因含 “not supported by different outputs”），不能据此保留。
- `check-templates` 正反例：当前三份模板通过；移除 `禁止编造` 标记或删除某模板文件时返回 invalid 并指出具体文件/标记。
- 以上断言位于 `skills/ai-research-mentor/tests/python/test_evolution.py` 与 `evaluation/tests/test_skill_tools.py`；原有 24 个自进化测试继续通过。

## 未覆盖范围

- 模板结构检查只证明护栏标记存在，不证明引用真实、数字有据、写作质量或科学正确性；KEEP 仍不构成任何效果保证。
- 自进化不运行模型、不自动应用、不自动推送；独立评审与真实执行仍由宿主完成，工具只能核对文件与记录一致。
- 旧维护轮的基线、suite 和回执因文件集合/检查契约变化而失效，必须重新冻结；这是本轮唯一预期的兼容成本。
- 科研任务、结果退役兼容、账本协议与发布/安装边界未变；真实选题、查新与写作质量仍未测量。本机结果不替代 Linux 或 Python 3.10/3.12 的实际执行。
