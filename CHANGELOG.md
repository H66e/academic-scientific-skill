# Changelog

## Unreleased

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
