# Changelog

## 0.5.0

2026-10-27. 范围收窄版本：技能专精为“找方向、查新、判断值不值得做、写论文/综述/开题”，结果解释退役，写作扩到完整初稿。设计见 [ADR 0010](docs/decisions/0010-scope-refocus-0.5.0.md)。

- 范围：`SKILL.md` 与技能入口改为四个任务；移除“结果分类与重评”整节、试验/负结果路由与 `feedback.md` 的全部引用；阅读生命周期（`confirm-read`/`retract-read`）、来源获取、锚点、claims、GO/HOLD/KILL 与人工决定绑定保持不变。
- 结果解释软退役：删除 `record-result`、`reclassify-result`、`invalidate-result`、`results` 四个 CLI 命令及对应 `Judgment` 公共方法；账本 17 类事件词表（含 `result.record`/`result.invalidate`）与 payload 校验保留，旧账本仍可 `verify-ledger`/`verify-artifacts`，但结果不再参与判定、快照或 KILL。
- 判定策略升为 `python-credibility-v5`：assess 不再读取结果状态；结果型 `scientific_refutation` KILL 移除，文献证据矛盾、duplicate/mechanism_equivalence 与已确认约束的 KILL 保留；快照摘要排除结果事件。既有评审因策略标识与快照变化而过期一次，需重评；工具不重写旧记录。
- 写作一等化：`research-outputs.md` 扩为完整写作工作流（论文/综述/开题的结构、证据清单、分节起草、claims→evidence 映射、引用纪律、缺失结果的计划性写法、修改清单），新增 `templates/paper.md`、`templates/survey.md`、`templates/proposal.md`。允许基于真实来源的完整初稿；禁止编造引用、数字、实验、结果或 venue 规则，未执行实验必须标为计划，投稿前必须人工审。
- 兼容：dossier 合同（schema 3 / decision contract 3）与其结果/pilot 字段仍由维护栈只读支持，不新增结果能力；仍需要结果登记的用途停留在 0.4.x。旧 0.4.x 的验收记录与 ADR 0004/0005 保留原观察值，只加退役说明。
- 未变：真实选题、gap 与写作质量仍未测量；PDF 抽取、实验日志自动解释、ledger↔dossier 无损互转仍不在范围内。

## 0.4.0

2026-10-26. 发布版本。0.3.0 是 Node 实现的最后一版（`v0.3.0` tag 回填在当时的 0.3.0 提交上）；本版是 Python-only 重建后的第一个发布，发布包由源码构建、不再入库，见 [ADR 0008](docs/decisions/0008-release-identity-and-package-artifacts.md)。

- 发布身份收口：`VERSION`、`pyproject.toml`、`research_mentor.__version__`、README 与 CHANGELOG 一致为 0.4.0；`v0.4.0` tag 与 GitHub Release 指向构建该包的提交，`v0.3.0` 指向历史 0.3.0 提交。`dist/ai-research-mentor.zip` 不再提交到 Git：由 `python -B evaluation/skill_tools.py package` 从源码确定性生成，CI 构建后用 `check-package` 复算，发布时作为 release asset 附加。
- 隐私：独立来源工具的 `verify` 与 `fulltext` 现在和 `search` 一样，在出网前执行 `check_outbound`；`--sensitivity private` 在这三个命令上都会阻断请求。此前该参数只对 `search` 生效，`verify`/`fulltext` 静默忽略分类，与 [python-core.md](skills/ai-research-mentor/references/python-core.md) 的声明不一致。
- 账本准入：17 类已注册事件全部有 payload 校验，`Ledger.append` 与 `verify-ledger` 共用同一规则；缺失或类型错误的必需字段不再能写入，也不能通过验证。事件词表、actor/trust、`ledger-json-v1` 哈希链与外部锚点语义不变；旧账本若含缺失必需字段的事件将验证失败并需人工检查，工具不自动改写历史。
- CLI 严格化：主入口与独立工具入口共用严格参数解析，拒绝重复长选项与缩写（如 `--project A --project B`、`--proj`、重复的 `--format`/`--sensitivity`）。运行期意外异常统一输出标准 JSON envelope 并以非零码退出，不再打印 traceback；`--format markdown` 同样返回结构化错误。
- `verify-artifacts` 对 `source.fetch` 补上回执元数据重放：provider、url、`http_status`、字节数与哈希、content-type，以及从保留字节重新派生的 IR 字段；伪造这些元数据即使重算哈希链与锚点也会报不一致。`search.result` / `paper.resolve` 的既有重放规则不变。
- 文档：新增 [ADR 0008](docs/decisions/0008-release-identity-and-package-artifacts.md)（发布身份与包构建）和 [ADR 0009](docs/decisions/0009-acquisition-direction-and-payload-admission.md)（获取实现方向与 payload 准入）；README、工作区治理与 CONTRIBUTING 更新版本/安装/发布边界，删除过期的“发行版仍为 0.3.0”与本机绝对路径；修复 README 中失效的 BibTeX 示例路径。
- 兼容边界：0.3.0 的 dossier 数据合同（schema 3 / decision contract 3）与 `python-credibility-v4` 判定策略不变；旧 Node 入口已由 ADR 0007 退役，本版不恢复。PDF 抽取、实验日志自动解析、ledger↔dossier 无损互转与科研有效性仍不在本版范围内。

### 此前 0.4.0 开发记录

- 修复实际 Python CI 暴露的跨环境兼容问题：日期比较在解析前标准化高精度小数秒和无冒号时区，保留原精度排序；回执校验接受 Windows 同一已核验根目录的短名与完整名，同时保留越界、链接、身份、字节哈希和快照守卫。冻结回归与科研合同不变。

- 清理公开历史调用日志中的三个本机绝对路径，以明确标记替代共同前缀，保留调用、阅读和来源观察；补充 pytest 缓存忽略规则，移除本地未跟踪缓存。此次清理不改变运行、科研合同或安装包。

- Unify the maintained project on Python: retire the superseded JavaScript entrypoints, tests, runners and CI dependencies; preserve native APIs and existing dossier canonical bytes, schema/decision contract 3, `ledger-json-v1` and `python-credibility-v4`.
- Replace live cross-language execution with frozen, provenance-bearing protocol observations and native behavioral regressions. Add a Python-only source check to validation and CI; structure and packaging reject unsupported source rather than silently excluding it. Old script/import callers must use Python; changed maintenance file sets require a new frozen baseline. See [ADR 0007](docs/decisions/0007-python-only-toolchain.md). No release promotion or installation synchronization is implied.

### 此前迁移阶段记录

以下条目记录先前实际完成的双运行时迁移、兼容检查和 CI 配置；其中第二运行时的持续维护承诺现由 ADR 0007 取代，原观察值与历史发行记录不改写。

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
