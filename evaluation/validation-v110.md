# 0.11.0 发布验收记录

日期：2026-10-27。按两位评委的修改规范实现：等级由账本推导、引用身份绑定、块解析修复。设计见 [ADR 0016](../docs/decisions/0016-ledger-derived-tiers-and-identity.md)。

## 变化

- 新增 `report_tier.py`：从经过 `Ledger.verify()` 与 `ResearchCore.verify_artifacts()` 的账本推导允许等级。只有 user/T1、scope=section/full_text 的有效 `reading.confirm` 计数；至少 2 个不同 canonical 来源才到 `evidence_review`。
- **等级封顶**：`ledger-json-v1` 没有预注册/计划事件，因此 `preregistration` / `research_plan` 不能推导，声明它们会失败。本版不伪造 higher tier。
- `check-draft --ledger`：声明等级不得超过推导等级；参考文献必须是最后一节，后面任何标题/粗体/段落/HTML 都是 `CONTENT_AFTER_REFERENCES`；标题为闭集，同义标题直接失败。
- 参考文献改为五列：编号、标题、标识（`doi:`/`arXiv:` 带版本/`url:`）、`ledger:<id>`、阅读范围。每引用绑定来源身份/版本/范围；同一 canonical 来源只能占一个编号。
- 修复：无引用 research_plan 不再通过；无引用却写“实验表明提升 15%”失败；参考文献后藏正文（ATX/setext/HTML/粗体）失败；`[PLANNED:` 只豁免同句而非整节；concept memo 同义标题失败；`GO term` 不再误报；concept memo 上限按可见字符 4000。
- 新增真实账本测试：用 `ResearchCore.fetch` + `quote` + human `confirm_read` 构造本地账本，断言 `derive_tier` 返回 `evidence_review`；不再 mock `_ledger_verified`/`effective_readings`。
- 报告模板改为四级轮廓、五列引用与等级封顶说明；effect-protocol 仍未执行。

## 本地检查

| 检查 | 实际结果 | 边界 |
| --- | --- | --- |
| `python -B evaluation/run-python-tests.py` | **310 tests，OK，skipped=1** | 合成语料/本地账本；不是科研效果证明 |
| `check-skill` | valid；63 条技能内链接、111 行入口 | 结构/链接检查 |
| `check-templates` | valid；paper/survey/proposal/report 四份模板 | 只验证结构标记 |
| `check-python-only` | valid；154 个文件 | 只排除语言/清单 |
| `package` | 57 个文件、728,090 字节、SHA-256 `4622baee…` | 发布包构建产物，不入 Git |
| `check-package` | valid，`deterministic: true` | 确定性不等于科学正确性 |
| `research_draft.py`（概念备忘录） | valid；tier=concept_memo；无错误/警告 | 只证明结构与记录一致 |

## 行为检查

- 13 项 draft 测试覆盖：concept memo 无引用/同义标题/作者-年份/URL、非概念无 ledger、声明超推导、身份不匹配、重复来源、参考文献后藏正文、无引用 research_plan 的量化断言、GO term 不误报、HOLD 标签。
- 真实账本测试用两个本地来源、`ResearchCore.fetch`、`quote`、human `confirm_read` 构造；`derive_tier` 返回 `evidence_review`，链与 artifact 校验通过。
- 报告模板使用五列引用；`check-templates` 仍通过。

## 未覆盖与诚实声明

- **没有效果证据**：effect-protocol 未执行；没有真实用户研究/外部盲评，不能声称比裸强模型更好。
- **等级封顶**：`preregistration`/`research_plan` 目前不可交付；这是账本 schema 的限制，不是已解决能力。
- 账本 ID + 身份只证明“该来源身份/版本/范围与记录一致”，不证明它支持正文那句话；不能证明数字正确、近邻完备或写作质量。
- check-draft 只适用于研究报告，不检查论文/综述；论文/综述仍是人工核对 + 现有模板。
- `actor=user` 是账本声明，不是身份认证；check-draft 不声称能证明真实阅读。
- 本机结果不替代 Linux 或 Python 3.10/3.12 的实际执行。
