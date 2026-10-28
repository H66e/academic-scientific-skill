# 0.12.0 发布验收记录

日期：2026-10-28。根据两位评委对“近邻深读门”的建议实现六点优化。设计见 [ADR 0017](../docs/decisions/0017-nearest-work-deep-read-gate.md)。

## 变化

- 新增 `references/deep-read-gate.md`：主张级 A/B/C 等级、致命问题（问题+答案+定位）、近邻选择门（两种检索措辞+候选表）、模型代读优先、C 级证伪模板、缓存/6 个月过期。
- 报告模板：evidence_review 及以上新增“近邻选择与深读记录”“主张—证据等级”“暂定判断（C 级）”三节；C 级主张不能写进“当前判断与下一步”。
- `check-draft`：非概念报告要求至少两条检索式、近邻候选表、主张表；A/B 主张必须绑定 `ledger:<id>` 且该来源有 user/T1 section/full_text 阅读；C 主张必须有翻转条件与完整 C 级节；C 主张不得出现在当前判断节。
- 聊天不硬阻断：没有深读时允许输出暂定判断，但必须标 C 级，并给翻转条件与最小核验动作。
- 缓存/过期规则只写在规范中，不做自动过期计算；报告检查不验证近邻选择是否完整。

## 本地检查

| 检查 | 实际结果 | 边界 |
| --- | --- | --- |
| `python -B evaluation/run-python-tests.py` | **314 tests，OK，skipped=1** | 合成文本/本地账本；不是科研效果证明 |
| `check-skill` | valid；66 条技能内链接、112 行入口 | 结构/链接检查 |
| `check-templates` | valid；paper/survey/proposal/report 四份模板 | 只验证结构标记 |
| `check-python-only` | valid；157 个文件 | 只排除语言/清单 |
| `package` | 58 个文件、743,506 字节、SHA-256 `702da9c8…` | 发布包构建产物，不入 Git |
| `check-package` | valid，`deterministic: true` | 确定性不等于科学正确性 |

## 诚实边界

- 仍然**没有效果证据**：未执行 effect-protocol，没有外部盲评；深读门是否真的减少“凭摘要下结论”尚未测量。
- `check-draft` 只检查主张表、等级、账本绑定与 C 级结构；不验证近邻选择完整性、阅读忠实性、引用支持关系或科研判断质量。
- C 级判断仍可能被写成“看起来比较新”；语义规避无法完全由结构检查拦住。
- `reader:user` 仍是账本声明；不声称身份认证。
- 论文/综述仍不在 check-draft 范围；深读门是报告/判断层规范，不是论文 Results 检查。
