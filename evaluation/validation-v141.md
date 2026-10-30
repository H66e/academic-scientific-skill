# 0.14.1 发布验收记录

日期：2026-10-30。文档补丁：采用两位独立评委（Fable 5.1 / Opus 5.5）对 0.14.0 的范围建议——收窄定位、统一合同口径、冻结效果评测基线，并加入尚未执行的效果评测材料。没有新增检查规则或运行时行为。

## 变化

- README 重写为“科研报告的可审计结构层”的一页定位：能力/非能力边界、快速开始、报告合同摘要、效果评测状态、维护期冻结范围与发布边界；版本变更历史统一由 CHANGELOG 维护。
- 统一计划单元豁免前缀为 5 个（下一步/行动/核验动作/获取路径/成本与停止），同步 SKILL 摘要与 ADR 0019 的表述；检查器行为不变。
- 修复 0.14.0 CHANGELOG 小节的条目顺序（二次加固在前、三次加固在后）。
- 新增未执行的效果评测材料包 `evaluation/effect-pilot/`（任务模板、三臂提示、去格式脚本、盲评表、manifest 示例、预注册停止判据），并重写 `evaluation/effect-protocol.md`；0.14.0（commit `efc6a0f`）冻结为评测基线。
- 范围收窄：dossier/reference 栈、自进化审计与内部 GO/HOLD/KILL 状态维持只读冻结，移出 README 主路径；效果数据出现前暂停新增报告类型、数据合同、模板字段与检索规则。

## 本地检查

| 检查 | 实际结果 | 边界 |
| --- | --- | --- |
| `run-python-tests.py` | **363 tests，OK，skipped=1** | 合成文本/本地账本；不是效果证明 |
| `check-skill` | valid；67 链接、112 行入口 | 结构/链接 |
| `check-templates` | valid；四份模板 | 只验证结构标记 |
| `check-examples` | valid；3 个合成示例 | 合成 schema |
| `check-python-only` | valid；171 个文件（含本地 dist；干净树 170） | 只排除语言/清单 |
| `package` | 58 文件、809,105 字节、SHA-256 `068ec3fa…` | 构建产物，不入 Git |
| `check-package` | valid，deterministic | 确定性不等于科学正确性 |

## 效果评测状态

- **NOT EXECUTED**：`evaluation/effect-pilot/` 只包含预注册材料；没有任务提供者、盲评者、运行或结果。测试、CI、发布包校验与 API 评审分数都不是效果证据。
- 冻结基线：v0.14.0，commit `efc6a0f9fbc20e83f4fe17a515653b0760613673`，包 SHA-256 `21db3bca28ee4b27c086e69092f8444d8c653df864269fd29281c06c291a7195`。
- 任务库 `EP-TB-01`：12 个任务、5 个非作者提供者槽位（未绑定）、4 个已知重复方向；任务库文件 `evaluation/effect-pilot/task-template.md` SHA-256 `841ffa362b79a6568c94afdb5bd9078b34f97e4cc28cc4d5d23f458b27c87b86`；gold-bank commitment `ceabe71b1da3944d05ad9c1aa02ebf0fe3800feb205a04b3f7360213a884ac47`（本记录按任务模板第 2 节的规则逐条复算，12 条记录与 bank commitment 均一致）。
- 四轮 API 评审与两轮独立评估原文在 `output/reviews/`（本地材料，不随包发布）；它们不构成效果证据，也不再作为质量测量使用。

## 未解决

- `check-draft` 仍只做结构/账本一致性；近邻完整性、致命问题诚实度、引用支持、科研质量无法验证；关键词启发式只覆盖少量明显越界措辞。
- `reader:model` 仍是 nearest-set 中的声明，不是账本认证；模型代读没有独立账本事件。
- 0.13/0.14.0 报告合同不兼容且无自动迁移（缺失绑定无法推断）；本轮没有新增检查规则。
- 没有效果证据；`effect-protocol` 与 pilot pack 均未执行，执行前需要至少 4 名非作者任务提供者与 2 名非作者盲评者，作者不得参与评分。
- 论文/综述仍不在 `check-draft` 范围；PDF 提取与自动实验日志解析仍未实现。
