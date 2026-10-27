# 0.7.0 发布验收记录

日期：2026-10-27。本地环境：Windows、CPython 3.14.5、无 Node。本版新增“方向 → 完整研究报告”工作流与先澄清协议，属于 prompt/reference/template 层变化；运行时、账本、dossier 与 `python-credibility-v5` 判定策略未变。设计与替代方案见 [ADR 0012](../docs/decisions/0012-direction-to-report-workflow.md)。

## 变化

- 新增 `templates/report.md`：完整研究报告骨架（输入假设与范围、摘要、引言与近邻定位、问题定义与可证伪假设/判据、方法、实验设计、预期结果与失败分析、计划与分工、风险、结论、参考文献/待核验清单）。
- 新增 `references/clarification.md`：方向类报告先做一轮 3–5 个高杠杆提问（目标与用途、硬约束、证据现状、成功标准与风险偏好、交付形式），给默认假设并做意图回述；用户要求先出草稿时按显式假设推进。
- `SKILL.md` 增加方向 → 完整报告路由、写作边界与交付要求；`research-outputs.md` 增加报告结构、决策闭合、假设可证伪、近邻差异、证据/计划分离、成本可行性与失败路径检查。
- 检查：`report.md` 与 `clarification.md` 纳入技能结构检查；`report.md` 纳入模板护栏检查（禁止编造、TODO(需来源)、研究问题、实验设计、风险标记）；两者加入固定自进化白名单，报告模板改动仍需 `writing_template_guardrails`。

## 本地检查

| 检查 | 实际结果 | 边界 |
| --- | --- | --- |
| `python -B evaluation/run-python-tests.py` | **296 tests，OK，skipped=1** | 合成语料与注入协议；不是科研效果证明 |
| `check-skill` | valid；60 条技能内链接、113 行入口 | 结构/链接检查 |
| `check-examples` | valid；GO/GO/HOLD 三个合成示例 | 示例为虚构数据 |
| `check-templates` | valid；paper/survey/proposal/report 四份模板结构标记齐全 | 只验证结构标记，不验证引用真实性或写作质量 |
| `check-python-only` | valid；140 个文件 | 只排除语言/清单 |
| `package` | 53 个文件、701,386 字节、SHA-256 `fecf8e61…` | 发布包构建产物，不入 Git |
| `check-package` | 待复算确认 | 确定性不等于科学正确性 |

## 本轮定向验证

- 版本一致性测试通过：`VERSION`、`pyproject.toml`、`__version__`、README 当前版本行与 CHANGELOG 小节均为 0.7.0。
- 新增模板护栏测试：当前四份模板通过；移除 `report.md` 的护栏标记或删除模板文件会被 `check-templates` 拒绝。
- 新增自进化白名单测试：`templates/report.md` 与 `references/clarification.md` 可编辑，运行时与测试仍为保护文件。
- 按新工作流做了一次演示：以“指代式图像编辑中的空间控制决策”为方向，从用户提供的既有报告草稿与文献清单出发，产出 `output/reports/` 下的完整报告（演示稿）；该演示用于检查结构、提问与证据边界，不构成对方向本身的效果证明。

## 未覆盖范围

- 报告模板只保证结构与提示词边界，不证明引用真实、近邻完整、假设成立、实验可行或报告可发表；真实质量仍需人工核验。
- 没有任何真实文献检索、全文阅读或实验执行被本版本完成；演示稿中的引用来自用户提供的草稿，均需核对原文。
- 先澄清协议是行为规范，不是强制交互流程；宿主不提问直接写作时，仍需把默认假设写进报告。
- 运行时、账本、dossier 与判定策略未变；本机结果不替代 Linux 或 Python 3.10/3.12 的实际执行。
