# Changelog

## Unreleased

- Complete native standard-library Python ports for dossier validation, v1/v2 migration, candidate fingerprints/ranking, actual independent receipts, Crossref/DOI/arXiv source utilities, note cards/drafts/BibTeX and read-only evolution checks. CLI adapters and APIs share implementations; no runtime command launches Node. Retain and exercise Node entrypoints as compatibility oracles.
- Preserve existing dossier contract 3 and ECMAScript-compatible fingerprints; keep ledger-json-v1 and snapshot-bound human decisions separate. Copying a receipt report never grants authorization, legacy migration does not revive approvals, and PDF acquisition does not imply extraction or reading.
- Add native repository checks and deterministic ZIP packaging, Python-only CLI regression cases and independent cross-language contract cases. Source-tool private queries are blocked before network access; fixed arXiv resource transport preserves the requested version and format across redirects.
- Refresh README, skill routing and usage references around direction exploration, brainstorm, topic assessment and gap discovery, with explicit unreleased/install boundaries. Design and limitations: [ADR 0006](docs/decisions/0006-native-python-toolchain.md). Scientific effectiveness, PDF extraction, experiment-log interpretation and lossless ledger/dossier conversion remain unimplemented or unmeasured; no release or installation sync is implied.

- 仓库清理修复 CONTRIBUTING.md 的许可证与 ADR 相对路径，避免从仓库根文档错误跳到父目录。

- 实现阅读补充与显式撤回：confirm-read 累计资格，独立 reading.retract 仅退役指名声明；T2 不可撤回 T1，完全误报无需虚构替代阅读。深读、视觉检查与 duplicate-KILL 共用有效集。所有补充/撤回仍使评审过期；解释规则与策略升级至 python-credibility-v4 同次落地，旧账本不重写，Node 合同仍为 3。

- 实现显式结果生命周期：Python 登记、同 run 重新分类、用户整次 run 失效与有效结果查询；因果引用计算有效头，反证与歧义统一用于 HOLD/KILL，解除阻塞仍需重评。策略升至 python-credibility-v3；历史账本不改写。
- Node schema/decision contract 3 显式记录 run_id、affected_claims 与 result_invalidations；完整分类历史和失效记录进入评审指纹。v1/v2 保留读取及显式迁移，旧评审归档并要求重评；Python 投影保留实际结果与失效，不转移批准。合成跨运行时回归比较科学事实与门控，不宣称哈希或科研效果等价。

- 此前 Step 1 闭合 Python 账本事件词表：`append` 与 `verify` 拒绝未注册类型，事件 schema 同步限定当时的类型。仅含受支持类型的既有账本保持兼容；旧实现曾接受的未知类型记录会验证失败，不自动删除、改名或忽略。当时合法事件解释未变，`POLICY_VERSION` 保持 `python-credibility-v2`；后续解释升级见本节新增记录。
- 此前 Step 1 在 [ADR 0004](docs/decisions/0004-result-lifecycle-semantics.md) 冻结语言无关的结果生命周期、评审依据、迁移与阅读补充/撤回语义。当时没有注册 `result.record`、`result.invalidate` 或 `reading.retract`，没有实现结果投影或切换阅读谓词；冻结与后续实施、实际验收分别记录。
- 修复 Python 账本无法发现自身尾部被截断的问题：哈希链只能校验仍在账本里的事件，删掉最后若干行后剩余链条依然自洽，此前 `verify-ledger` 会返回 `valid: true`。现新增 `ledger.anchor.json` 从链外记录期望的事件数与头部哈希，`verify-ledger` 报告 `anchor` 为 `matched`/`mismatch`/`absent`，`mismatch` 为硬失败（`append` 拒绝继续写入）；新增 `anchor-ledger` 命令为既有项目补记锚点。锚点与账本同目录，只防意外、丢失与半写，不防刻意改写两者的使用者。设计与替代方案见 [ADR 0003](docs/decisions/0003-ledger-tail-anchor.md)。
- 修正 `references/python-core.md` 中一处自相矛盾的表述：同一文件一边写 `--human-page-check` 等标志 "do not authenticate identity"，一边写 "a model cannot manufacture it"。后者读起来像在声称代码并不提供的保证，现改为与 Boundaries 节一致的措辞。同一节新增：独立评审（T3）在本 runtime 中不存在是**分工**而非待补缺口，并写明若将来要加，必须同时登记 `EVENT_ACTORS` 与 `schemas/ledger-event.schema.json`，且"独立"指上下文隔离而非身份隔离。
- CI 的 `validate` 作业此前只在 Ubuntu 运行，Node 侧没有任何 Windows 覆盖（Python 作业已有 Windows）。现增加 `windows-latest` + Node 24 一个作业，不展开为平台 × 版本笛卡尔积：两个维度相互独立，四个 Windows 作业是重复覆盖。新增作业尚未执行，配置存在不代表已通过。
- 修正两处验收记录（`evaluation/validation.md`、`evaluation/validation-v030.md`）中指向旧仓库名的 CI 运行链接：GitHub 仓库已由 `academic-scientific-skill-for-AI` 更名为 `academic-scientific-skill`。运行 ID 与记录内容未变。
- 增加仓库版本一致性检查 `evaluation/tests/test_version_consistency.py`：`VERSION` 为真源，核对 `pyproject.toml`、`research_mentor.__version__`、`README.md` 当前版本行与 `CHANGELOG.md` 小节。此前这四处靠人工核对，漏改一处无人发现。
- 采用 MIT 许可证（版权 `H66e`）并在所有分发路径上传播：`README.md`/`CONTRIBUTING.md` 声明许可，`pyproject.toml` 声明 SPDX `MIT` 与 `license-files`，发布包包含 `ai-research-mentor/LICENSE` 并由 `check-package.mjs` 核验。理由与替代方案见 [ADR 0002](docs/decisions/0002-license-selection.md)。
- Add a standard-library Python evidence runtime: append-only ledger, arXiv/Crossref acquisition receipts, exact text anchors, explicit reading statements, scoped strict machine recommendations and snapshot-bound human decisions.
- Keep private/unknown queries local; require public or deliberately de-identified classification, TLS/public-address checks and bounded requests for external acquisition. Local project outputs cannot enter the skill source tree.
- Add initial schema-2 dossier projection with no transferred reviews or approvals; retain all v0.3 Node commands as a tested compatibility path. Python ledger hashes are a separate versioned protocol, not Node fingerprint replacements.
- Add Python API/CLI, reproducible source/IR/anchor verification, query recheck and reference linting, Windows/Linux Python CI, workflow tests and migration ADR. PDF bytes remain unextracted and scientific effectiveness remains unmeasured.
- Require current load-bearing claim support for duplicate/refutation KILL; context-only claims cannot refute a candidate's core. Python judgment policy v2 invalidates previous weaker assessments while preserving history.
- 把结果分类与失效重评提升为 `SKILL.md` 的一等入口：六种运行/科学状态从段末单句改为独立小节并前置定义，开场定位补上"出现结果之后"的一半；触发路由行改为点明状态归类。判定细节仍以 `feedback.md` 为准。
- Clarify source-of-truth and workspace version governance for the formal v0.3 source, installed copy, and unreleased v0.4 candidate.
- Document that external retrieval is not private by default; use public or deliberately de-identified queries, keep private research materials local, and treat request logs and source artifacts as sensitive.
- Record the v0.4 provenance-repair requirement: structural validation alone does not authenticate fabricated source/evidence records, so strict provenance receipts and locator anchors must be designed before promotion.

## 0.3.0

- 修复独立 pilot 批准被用于完整验证，以及无关确认约束导致资源 KILL；完整验证使用最新独立阶段批准。
- 保留 schema 2，增加 decision_contract_version=2；旧评审可读取但需迁移和重新评审，不自动继承新批准。
- 增加限定目录下真实 JSON 回执的字节哈希与完整评审字段核验；自行填写 verified 不授权完整验证。
- 增加零第三方依赖的 Crossref 实际检索、DOI/arXiv 身份核验、受控 HTML/PDF 获取及诚实的离线/解析降级。
- 增加轻量决策/gap 卡、笔记转初步 dossier、BibTeX 导出和编辑器 JSON Schema；未知事实保持未知。
- 修复混合契约迁移恢复旧批准、畸形无关记录掩蔽引用错误、跨 DOI/arXiv/OpenReview 身份重复导出及正文未完整取得时的状态分类；产出工具支持标准输入。
- 补全文处理、gap 核验链、替代解释与控制失效，以及开题、提案、综述和基于真实结果的文稿流程。
- 保留 Darwin 受限维护协议；本次工具与契约升级作为单独接口维护，不放宽其默认受保护范围。

本版实际检查、联网试用与未覆盖范围见 [evaluation/validation-v030.md](evaluation/validation-v030.md)。

## 0.2.0

- 升级候选评审合同：明确候选与证据的关联、评审依赖范围和淘汰依据；评分权重变化与科学评审变化分别处理。
- 增加旧合同的只读检查和显式迁移路径；迁移保留旧评审历史并要求重新评审。
- 增加结构化筛选、检索能力与覆盖边界记录，区分错误与提醒。
- 保留科研和 Darwin 自优化回归；接口变更仍属于单独维护。
- 增加完整测试入口、Node.js 18 / 20 / 22 / 24 的 CI 配置、确定性 ZIP 构建和发布包逐文件字节校验。
- 增加三种明确标注的合成项目示例，以及两个真实论文有限语料试用与后续评价判据。

验证记录见 [evaluation/validation.md](evaluation/validation.md)。自动测试、合成案例和 CI 配置不证明真实文献覆盖率、科学正确性或选题成功率。

## 0.1.0

- 提供 AI / ML 选题、文献检索、查新、可行性评估与验证反馈流程。
- 提供研究记录审计工具和受控自优化验收机制。
