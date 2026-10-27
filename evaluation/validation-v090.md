# 0.9.0 发布验收记录

日期：2026-10-27。本版是两位严厉评委（Claude Fable 5.1 / Opus 5.5）评审后的结构性大改：把“防编造”从口号变成可执行的 `check-draft`，给报告分级，删除自相矛盾的资源默认值与标签残留，修正版本交付，并把自优化降级为“提示词/模板变更审计”。设计见 [ADR 0014](../docs/decisions/0014-major-revision-after-review.md)。

## 变化

- 新增 `runtime/research_mentor/draft.py` 与 `scripts/research_draft.py`：检查 `report-tier` 标记、引用键、已核验/未核验状态、GO/HOLD/KILL 标签、计划混入结果/摘要节、`TODO(需来源)`；只做结构与记录检查，不做真实性判定。
- 报告分四级：`concept_memo` / `evidence_review` / `preregistration` / `research_plan`；概念备忘录必须带“引用未核验”横幅，非概念等级必须引用已核验条目；模板按研究类型（经验/理论/测量/数据集/复现）裁剪。
- 清理冲突：删除“决策摘要（做/等/放弃）”，统一“当前判断与下一步”；go/no-go 改“继续/停止判据”；澄清协议删除 24GB/2 周默认值，资源未知写未知，venue 规则永不默认，问题缩到 2–3 个阻塞问题。
- `SKILL.md` 精简 CLI 语义；自优化改称“提示词/模板变更审计”，明确只证明记录与结构一致，不证明科研质量或效果提升。
- 新增 [effect-protocol.md](effect-protocol.md)（预注册草案，未执行）：24 个真实任务、skill/裸模型对照、3 次采样、外部盲评、编造引用率/近邻召回/可执行性；未执行前不得声称效果。
- 版本交付：README 安装/校验示例统一到 0.9.0；新增测试检查安装块版本；演示报告降级为 `concept_memo` 并记录 check-draft 结果。

## 本地检查

| 检查 | 实际结果 | 边界 |
| --- | --- | --- |
| `python -B evaluation/run-python-tests.py` | **304 tests，OK，skipped=1** | 合成语料与合同测试；不是科研效果证明 |
| `check-skill` | valid；63 条技能内链接、111 行入口 | 结构/链接检查 |
| `check-examples` | valid；GO/GO/HOLD 三个合成示例 | 示例为虚构数据；标签是 runtime 用例状态 |
| `check-templates` | valid；paper/survey/proposal/report 四份模板结构标记齐全 | 只验证结构标记，不验证引用真实性或写作质量 |
| `check-python-only` | valid；149 个文件 | 只排除语言/清单 |
| `package` | 56 个文件、717,046 字节、SHA-256 `815a7f6e…` | 发布包构建产物，不入 Git |
| `check-package` | valid，`deterministic: true`：两次独立构建逐字节一致 | 确定性不等于科学正确性 |
| `research_draft.py`（演示报告） | valid；tier=`concept_memo`；2 条警告（4 条未用引用、9 个 TODO） | 只说明结构/记录一致，不说明引用真实或报告可发表 |

## 行为检查

- `test_draft.py` 覆盖：概念备忘录允许未核验引用（需横幅）、非概念等级拒绝未核验引用、缺 tier 拒绝、GO/HOLD/KILL/做等放弃拒绝、结果节出现计划标记拒绝、引用无条目拒绝。
- `test_version_consistency` 新增安装块检查：README 安装链接与包名必须是当前版本，且不得残留 0.5.0 安装提示。
- 演示报告已加 `concept_memo` 横幅，移除标签，`check-draft` 通过但保留 2 条可见警告；它不再被当作“证据审查”或“完整研究计划”。

## 未覆盖范围与诚实声明

- **没有效果证据**：未执行 effect-protocol；没有真实用户研究或外部盲评。两位评委的核心批评（“没有证明比裸强模型更好”）本版没有解决，只是不再声称已解决。
- `check-draft` 只检查结构/记录，无法证明引用支持论点、数字正确、近邻完备或写作质量；它不能替代人工核验。
- 报告分级与模板裁剪是提示词/结构约束，不是强制语义检查；模型仍可能用空洞文字填满合格章节。
- 账本、dossier、`python-credibility-v5` 与全部门控行为未变；本机结果不替代 Linux 或 Python 3.10/3.12 的实际执行。
- 自优化审计仍不能证明科研效果；`KEEP` 只表示记录/结构通过，不表示能力提升。
