# 0.14.0 发布验收记录

日期：2026-10-30。按两位评委对 0.13.0 的验收复审（Fable 6.5/10、Opus 5/10，均为大修）收紧报告合同，修复“照抄模板也能通过”和候选/主张/阅读绑定过弱的问题。设计见 [ADR 0019](../docs/decisions/0019-nearest-claim-provisional-contract.md)。

## 复审背景

- 0.13.0 验收评审（本地材料）：`output/reviews/v013-audit-fable.md`、`output/reviews/v013-audit-opus.md`。两份都认为 0.13.0 修掉了 A/B 死代码、NFKC、C-only、URL、反引号等工程缺陷，但不建议发布：模板原样（只改日期）仍可通过；A/B 可绑定 abstract/unseen 候选与自答致命问题；等级校验回退；C ID 可被改写绕过；当前判断只检查 bullet；引用反引号与范围声明仍误判；JSON 类型错误会崩溃。
- 本轮共同优先级：候选—主张—阅读强绑定；claim ID 成为正文合同；JSON 语义最小值与防照抄模板；模板/文档/检查器对齐并经真实账本端到端验证。

## 变化

- `nearest-set-json` v2：`schema`、`created_at`、至少两条不同且非占位的检索式、至少两个候选与 `uncovered`；候选唯一 `P#`、唯一 `ledger:` 绑定、标题、理由、状态、reader、真实定位；`section`/`full_text` 不得超出账本实际阅读范围；致命问题答案限定“是/否/未读到”，少于 2 个或占位失败。
- 六列主张表（编号/主张/等级/近邻/依据/翻转条件）：A/B 绑定候选及其账本，每个候选至少两个已答“是/否”的致命问题；A 级覆盖全部已读近邻、未读候选进 `uncovered`，并拒绝“首次/全新”式绝对措辞；等级只接受 A/B/C。
- 正文 claim-ID 合同：当前判断的段落与列表项都必须带 `[C#]`（计划单元以“下一步/行动/核验动作/获取路径/成本与停止”开头可豁免）；C 级只允许 `倾向……（见 [C#]）` 限定形式；其他章节的硬判断词无 ID 失败（启发式边界）。
- `provisional-json` v1：每条 C 级主张一条，含倾向（tendency）/翻转条件/获取路径与 `check`（候选必须存在、问题必须与 `kill_questions[].q` 规范化后一致、定位必须真实）。
- 健壮性与兼容：引用单元格允许反引号；阅读范围只接受 `full_text` 或 `section:<真实定位>`；JSON 类型错误返回错误而非崩溃；未来日期失败；重复候选/账本、重复 ID、非法等级失败；近邻集超过 180 天除 warning 外还阻止 `delivery_ready`。
- 报告模板整理为“各等级章节 + 文末共享 `附录：机器可读块` + 一份共享参考文献表”，消除三处重复 JSON；`check-draft` 允许该附录标题，两种布局都只要求全文一份机器块。
- 文档同步：`deep-read-gate.md`、`SKILL.md` 的 check-draft 摘要、ADR 0019、README、CHANGELOG 与工作区治理版本说明。

## 本地检查

| 检查 | 实际结果 | 边界 |
| --- | --- | --- |
| `run-python-tests.py` | **359 tests，OK，skipped=1** | 合成文本/本地账本；不是效果证明 |
| `check-skill` | valid；67 链接、112 行入口 | 结构/链接 |
| `check-examples` | valid；3 个合成示例 | 合成 schema |
| `check-templates` | valid；四份模板 | 只验证结构标记 |
| `check-python-only` | valid；161 个文件（含本地 dist；干净树 160） | 只排除语言/清单 |
| `package` | 58 文件、809,089 字节、SHA-256 `21db3bca…` | 构建产物，不入 Git |
| `check-package` | valid，deterministic | 确定性不等于科学正确性 |

## 送审记录

评审材料在 `output/reviews/`（本地材料，不随包发布）。四轮独立 API 评审：

| 轮次 | 对象 | Fable 5.1 | Opus 5.5 | 结论 |
| --- | --- | --- | --- | --- |
| 1 | v0.13.0 验收 | 6.5/10 大修 | 5/10 大修 | 修 0.13 合同 |
| 2 | v0.14.0 首审 | 7.0/10 大修 | 7/10 小修（偏大） | 加固候选/定位/计划块 |
| 3 | v0.14.0 二次终审 | 7.8/10 小修（偏大） | 7.5/10 小修 | 补真实端到端正例、kill 定位对账 |
| 4 | v0.14.0 发布确认 | 8.6/10 小修 | 8.3/10 小修 | 只剩“section 定位缺失时对账”和“验收记录重跑” |

第 4 轮后已修复两处小修：`section:` 声明在账本无定位时直接失败；用终审后实际重跑的数据更新本记录，并给真实端到端正例补断言（URL 来源 `title=None` 时只跳过标题比对，不伪造）、给 `RealLedgerTierTests` 固定 `_today`、清理空操作测试、修正 CHANGELOG 顺序。两份终审均写明“修完可直接发布，不需要再做方向性评审”。

## 终审后重跑

- `run-python-tests.py`：**359 tests，OK，skipped=1**。
- 真实账本端到端正例 `RealLedgerEndToEndTests.test_filled_report_passes_check_draft_with_a_real_ledger`：`valid=True`、`delivery_ready=True`，未 mock `derive_tier`；两个 URL 来源的投影 `title` 均为 `None`（无 `paper.resolve`），因此引用标题比对按缺失信息跳过，不伪造标题。
- `check-skill` valid（67 链接、112 行）；`check-templates` valid；`check-examples` valid；`check-python-only` valid（161 文件，含本地 dist；干净树 160）。
- `package` / `check-package`：58 文件、809,089 字节、SHA-256 `21db3bca…`，deterministic。

## 二次复审与加固

- 0.14.0 首轮送审（Fable 7.0/10 “大修”、Opus 7/10 “小修（偏大）”）仍不建议发布，具体指出：同一来源可用 anchor/source 两种 ledger 冒充两个候选；读过的候选可写伪造 §9 定位；当前判断的引用块、H1 与“下一步/行动”计划块可裸写结论；`provisional` 的候选/致命问题/locator 未与 C 主张绑定；`unseen` 被逼编造章节定位；机器块可重复出现；模板 C1 的 `full_text` 候选与“仅基于摘要”自相矛盾；测试仍以 mock 为主。
- 本轮加固：候选 ledger 归一化到 source 后去重；已读候选与引用 `section:` 定位和账本 reading locator 对账；`abstract/unseen` 及“未读到”允许定位“无”；引用块、H1、计划块纳入扫描且计划块不得夹带判断词；`provisional` 的候选必须是同一 C 主张绑定者、问题必须仍未读、locator 必须与该致命问题一致；全文 `nearest-set-json`/`provisional-json` 各只允许一份；模板 P1 改为 `abstract` 并统一定位；粗体副标题不再被当作标题；新增真实账本端到端正例测试。
- 加固后本地复验：358 tests OK（1 skip）；check-skill / check-templates / check-examples / check-python-only / package / check-package 全过；包 58 文件 / 808,000 字节 / `467b7848…`，deterministic。
- 三次复审（终审）前再加固：已答“是/否”的致命问题 locator 必须与账本阅读定位同类型且同数字前缀匹配（`§2` 不再匹配 `Table 2`）；已读候选必须有真实阅读定位；C 级主张必须绑定候选，`provisional` 候选必须属于该集合；H1 同时拒绝绝对新颖措辞；测试固定检查日期，并保留真实账本端到端 `check_draft` 正例（不 mock `derive_tier`）。

## 未解决

- 近邻选择是否完整、致命问题是否诚实回答、引用是否支持主张、报告是否真的更好，`check-draft` 都无法验证；关键词启发式只能拦少量明显越界措辞。
- `reader:model` 仍是 nearest-set 里的声明，不是账本认证；模型代读没有独立账本事件。
- 近邻超过 180 天只给 warning 并阻止 `delivery_ready`，不是自动失效重查。
- 0.13.0 报告格式不兼容且没有自动迁移（缺失绑定无法推断）。
- 没有效果证据；`effect-protocol` 未执行；论文/综述仍不在 check-draft 范围。
