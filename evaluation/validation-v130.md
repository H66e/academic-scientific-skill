# 0.13.0 发布验收记录

日期：2026-10-28。按 0.12.0 复审意见修复结构化近邻选择与主张绑定。设计见 [ADR 0018](../docs/decisions/0018-structured-nearest-set-and-claim-ids.md)。

## 变化

- 近邻选择改为 `nearest-set-json` 结构块：`created_at`、至少两条不同检索式、至少两个候选；每个候选含 rationale/status/reader/ledger/locator 和至少两个致命问题（q/answer/locator）。占位符、缺字段、非法状态直接失败；超过 180 天给 stale warning。
- 当前判断节的每条 bullet 必须带 `[C#]`；C 级 ID 不得出现在当前判断，只能出现在“暂定判断（C 级）”，并带 claim ID、翻转条件、最小核验、获取路径。
- A/B 主张必须绑定 nearest-set 中的候选 ledger，并从账本派生 user/T1 section/full_text 阅读；修复 0.12.0 的 projections 死代码、C 级 NFKC 键、反引号、URL 切片、C-only 误判和模板列数。
- 模板改为 JSON 近邻块 + 5 列引用；旧报告会失败。

## 本地检查

| 检查 | 实际结果 | 边界 |
| --- | --- | --- |
| `run-python-tests.py` | **314 tests，OK，skipped=1** | 合成文本/本地账本；不是效果证明 |
| `check-skill` | valid；66 链接、112 行入口 | 结构/链接 |
| `check-templates` | valid；四份模板 | 只验证结构标记 |
| `check-python-only` | valid；157 个文件 | 只排除语言/清单 |
| `package` | 58 文件、748,060 字节、SHA-256 `f602f314…` | 构建产物，不入 Git |
| `check-package` | valid，deterministic | 确定性不等于科学正确性 |

## 未解决

- 近邻选择是否完整、致命问题是否诚实回答、引用是否支持主张，checker 无法验证；只能人工抽样。
- `reader:model` 只是 nearest-set 字段，不是账本认证；模型代读没有独立账本事件。
- 超过 180 天只给 warning，不是自动失效重查。
- 没有效果证据；effect-protocol 未执行。
- 论文/综述仍不在 check-draft 范围。
