# academic-scientific-skill

**AI Research Mentor**：重点帮助 AI / ML 科研的方向探索、brainstorm、选题评估与 gap 查找。文献检索、全文核验和研究材料整理服务于这些判断。适用于 Codex，也可由其他支持 `SKILL.md` 的宿主按需读取。

当前版本 **0.3.0**。变更记录见 [CHANGELOG.md](CHANGELOG.md)。

**源码包含未发布的 Python 改动，发行版与安装副本仍为 0.3.0。** Python 3.10+ 标准库核心已实现来源回执、精确文本锚点、本地只追加账本、结果与阅读生命周期，以及绑定当前评审的人工决定。推送源码不等于发布或同步安装。

| 范围 | 当前状态 |
| --- | --- |
| 新项目的 Python 证据与判断主流程 | 已实现；记录机器建议与实际人工决定，不自动执行实验 |
| 旧 dossier 审计、迁移、独立评审回执与排序 | 原生 Python 已实现；Node 保留为兼容路径 |
| 决策卡、初步项目、BibTeX 与自优化验收 | 原生 Python 已实现；Node 保留为兼容路径 |
| Python ledger 与 dossier 的数据关系 | 可以投影导出，不是无损双向迁移，不转移旧批准 |
| PDF 正文提取、自动实验日志解析 | 尚未实现；宿主取得正文并实际阅读后再记录 |
| 真实选题、brainstorm 和 gap 质量 | 尚无效果证明；自动测试检查合同与回归，不证明科研价值 |

完整命令与边界见 [Python 工作流](skills/ai-research-mentor/references/python-core.md)，实际执行结果见 [Python 验收记录](evaluation/validation-python-core.md)。

```text
python -B skills/ai-research-mentor/scripts/research_mentor.py --project ../research-private/example doctor
python -B skills/ai-research-mentor/scripts/research_mentor.py --project ../research-private/example init --question "A concrete AI/ML research question"
python -B evaluation/run-python-tests.py
```

外部检索默认阻止 private query；只有 public/deidentified 分类可发送。上述路径是本地研究数据，不能发布或同步到安装源码中。CLI/API 使用同一 `runtime/research_mentor` 包，`pip install -e .` 可选；无需为 Skill 安装 pip 包。

结果与阅读生命周期以 [ADR 0004](docs/decisions/0004-result-lifecycle-semantics.md) 为共同规范。Python 的 `record-result/reclassify-result/invalidate-result/results` 保存真实声明、显式纠正与运行失效；Node v3 和 Python 投影保留完整结果历史。`confirm-read` 累计资格，`retract-read` 显式撤回误报；两者都使旧评审过期。解除阻塞仍须重评，不能恢复旧 GO。各阶段实施状态与策略迁移见 [ADR 0005](docs/decisions/0005-policy-bound-lifecycle-rollout.md)。

正式源码、安装副本和未发布 v0.4 候选的边界见 [工作区与版本治理说明](docs/WORKSPACE_GOVERNANCE.md)。当前 Codex 加载的是最后同步的 v0.3.0；本工作树中的未发布改动不会自动进入安装副本，v0.4 candidate 仍处于开发和审查阶段。

从具体研究问题出发，将已有证据、推断和待验证假设分开，帮助决定下一步值得投入什么；拿到实验结果之后，再判断这个结果实际支持了什么、哪些结论因此失效。它不会承诺新颖性、实验成功或论文录用。

## 能做什么

- 探索方向：从已知结果、局限、矛盾和失败模式形成少量可检验候选，允许零个合格选题。
- 文献查找：记录实际检索、筛选理由、文献身份、版本、阅读范围和证据定位，区分基础工作、最近更新和技术上最接近的工作。
- 实际来源工具：Crossref 查询、DOI/arXiv 身份核验，以及有预算边界的 HTML/PDF 获取；取得内容后再由宿主实读与核验。
- 研究缺口：对照已知条件、缺失知识、最强替代解释和已有绕行方案，用真实反向检索及判别测试检查 gap。
- 科研产出：轻量决策/gap 卡、近邻比较、开题、研究提案、综述及带来源草稿；论文结果以真实材料为依据。
- 选题评估：逐候选查新，检查强基线、前置条件、资源、指标与反证方法，给出 GO / HOLD / KILL 及依据。
- 类型适配：支持经验、理论、测量、数据集和复现研究，不强制固定候选数量或两周训练计划。
- 验证反馈：区分跑通、执行失败、支持、反驳、无结论和尚未运行；选题、约束或证据变化后重新评估。
- 持续记录：dossier 按候选实际依赖计算评审指纹，ledger 使用全项目科学输入的保守快照；两种流程都可使用 Python。单独记录排序权重，保存有适用条件和重访条件的历史判断。
- 受控自优化：从实际流程失误提出小改动，在独立副本与冻结用例上验证，明确改善且科研原则不退化才保留。

## 安装与使用

完整 skill 位于 [`skills/ai-research-mentor`](skills/ai-research-mentor)，可下载独立包 [`dist/ai-research-mentor.zip`](dist/ai-research-mentor.zip)。压缩包内的 `ai-research-mentor` 文件夹包含全部运行资源。

Codex 用户将该文件夹放入用户技能目录，默认为 `~/.codex/skills/`。Windows PowerShell 可在仓库根目录执行：

```powershell
$researchSkills = Join-Path $env:USERPROFILE '.codex\skills'
$researchTarget = Join-Path $researchSkills 'ai-research-mentor'
if (Test-Path -LiteralPath $researchTarget) { throw '已有同名 skill，请先检查现有版本。' }
New-Item -ItemType Directory -Path $researchSkills -Force | Out-Null
Copy-Item -LiteralPath '.\skills\ai-research-mentor' -Destination $researchSkills -Recurse
```

如果设置了 `CODEX_HOME`，请使用其 `skills` 子目录。让宿主重新发现技能后，可显式调用：

```text
使用 $ai-research-mentor 帮我探索大模型 agent 的研究问题。
先梳理已有认识和最接近的论文，评估贡献与可行性，再建议下一步。
我的已有材料和资源约束是：……
```

也可以只请求找论文、评估一个想法或分析一次负结果，skill 会按任务加载相关细则。

普通科研讨论不强制启用脚本、模型 API key 或研究代理框架。需要可复现工具时使用 Python 3.10+ 标准库来源工具，或宿主实际提供的搜索、PDF 和文献库能力。分别记录检索来源、全文访问、引用扩展和代码访问能力，以及实际覆盖和失败；离线时明确语料边界，不冒充完成外部查新。

## 从实际来源到研究材料

在仓库根目录可运行以下独立命令；它们按当前请求组合，不要求每次执行全部步骤：

```text
python -B skills/ai-research-mentor/scripts/research_sources.py search --sensitivity public --query "grouped query attention" --rows 10 --pages 1
python -B skills/ai-research-mentor/scripts/research_sources.py verify --doi 10.18653/v1/2023.emnlp-main.298 --expect-year 2023
python -B skills/ai-research-mentor/scripts/research_sources.py fulltext --arxiv 2305.13245v1 --format pdf
python -B skills/ai-research-mentor/scripts/research_outputs.py card examples/lightweight-example/notes.json
python -B skills/ai-research-mentor/scripts/research_outputs.py draft examples/lightweight-example/notes.json --name example-question
python -B skills/ai-research-mentor/scripts/research_outputs.py bibtex source-records.json
```

`search` 输出实际 `searches`/`papers`，`verify` 返回身份与可选元数据对照；宿主检查后再合并记录。Crossref 未覆盖的预印本及前后向引用由实际可用来源补充。`fulltext` 取得 HTML 块或 PDF 字节，分别标记 `needs_host_review` / `needs_host_extraction`，不自动记为 section/full_text 证据。

透明代理的 fake-IP 环境可显式使用 `--trusted-provider-transport`，仅适用于内部构造的固定 Crossref/arXiv 请求，不能用于任意 `--url`。工具保持 TLS、超时、请求与字节预算；不更改系统网络设置。详见 [source-tools.md](skills/ai-research-mentor/references/source-tools.md)。

`card` 整理已有笔记；`draft` 只创建初步项目结构，不制造论文、评审或 GO；`bibtex` 只导出提供的元数据，未知项提醒并省略，冲突需解决。这些命令默认只写标准输出，正文缓存需要显式 `--root` 和新 `--out`。轻量示例见 [examples/lightweight-example](examples/lightweight-example/README.md)，编辑辅助 Schema 在 [schemas](skills/ai-research-mentor/schemas)。

三个产出命令也接受 `-` 从标准输入读取 JSON，例如 `python -B skills/ai-research-mentor/scripts/research_outputs.py card -`。BibTeX 根据实际 DOI/arXiv/OpenReview 身份关联归并同源条目；身份或版本冲突仍需先核对来源，不猜测合并。

gap 方法见 [ideation.md](skills/ai-research-mentor/references/ideation.md)，全文实读见 [fulltext.md](skills/ai-research-mentor/references/fulltext.md)，开题、综述及论文草稿见 [research-outputs.md](skills/ai-research-mentor/references/research-outputs.md)。未执行的验证写为计划，不写成发现。

## 可选项目记录工具

审计程序优先使用 **Python 3.10+ 标准库**，无需 pip 安装；旧 Node.js 18+ 入口保留并持续进行兼容测试。它只检查记录、版本、回执与排序必要条件，不联网，也不判断论文真实性或科学正确性；联网能力由独立来源工具提供。

在仓库根目录运行：

```text
python -B skills/ai-research-mentor/scripts/research_audit.py init --root ../research-private --name my-topic
python -B skills/ai-research-mentor/scripts/research_audit.py validate ../research-private/my-topic/dossier.json
python -B skills/ai-research-mentor/scripts/research_audit.py fingerprint ../research-private/my-topic/dossier.json IDEA-ID
python -B skills/ai-research-mentor/scripts/research_audit.py rank ../research-private/my-topic/dossier.json
```

先在仓库外准备已有的私有工作目录（上例为 `../research-private`），再由研究者或宿主填写项目事实、实际来源、候选和评估。初始化文件不含论文或评审；当前 `fingerprint` 的 `review_basis_hash` 写入对应评审后，排序才会检查其是否仍然有效。

当前 schema_version=3、decision_contract_version=3 保留候选 evidence_links，并显式标识运行、因果分类纠正与失效。v1/v2 可以验证读取，但须迁移重评。资源 KILL 必须把确认约束关联到实际失败的必要依赖。完整验证需要最新同阶段独立 GO，且当次读取真实 JSON 回执核对字节哈希和全部评审字段：

```text
python -B skills/ai-research-mentor/scripts/research_audit.py verify-receipts ../research-private/my-topic/dossier.json --root ../research-private/my-topic
python -B skills/ai-research-mentor/scripts/research_audit.py rank ../research-private/my-topic/dossier.json --receipt-root ../research-private/my-topic
```

原生 Python 与旧 Node 审计使用相同的 dossier 指纹和回执门槛；没有已核验回执时，裸 `rank` 不批准 full_validation。回执核验不能证明评审者实际独立或科学结论正确。HOLD 可建议补信息；有界 pilot 也需基础科学门槛。

`validate` 返回结构错误与提醒；warnings 不使合法的初步构思无效，也不替代决策门控。旧 schema 1 或旧决策契约可读取，但旧评审不授权当前决定，需显式迁移并重新评审：

```text
python -B skills/ai-research-mentor/scripts/research_audit.py migrate old-project/dossier.json
```

迁移输出到标准输出，不覆盖输入；检查后用 UTF-8 另存新文件。旧 reviews 完整归档到 history 并要求重评，旧 pilots 物化 run_id、保留原结果和产物；迁移不会编造分类替代、失效、新证据角色或新评审指纹。

字段说明见 [`data-contract.md`](skills/ai-research-mentor/references/data-contract.md)，评分锚点与门控见 [`evaluation.md`](skills/ai-research-mentor/references/evaluation.md)。无 Python 时可使用旧 Node 兼容入口或依合同手动核验，明确自动检查未运行。

## 验证

```text
python -B evaluation/run-python-tests.py
python -B evaluation/skill_tools.py check-skill
python -B evaluation/skill_tools.py check-examples
python -B evaluation/skill_tools.py package
python -B evaluation/skill_tools.py check-package
```

以上测试与维护命令可以在只有 Python 的环境执行。安装了 Node 时，Python 测试另外运行差分检查；开发验收设置 `RESEARCH_MENTOR_REQUIRE_NODE_CONFORMANCE=1`，避免缺少兼容工具时静默跳过。旧 Node 回归与维护入口继续保留：

```text
node evaluation/run-tests.mjs
node evaluation/check-skill.mjs skills/ai-research-mentor
node evaluation/check-examples.mjs
node evaluation/package-skill.mjs
node evaluation/check-package.mjs
```

测试入口包含科研审计、来源协议、研究产出、Darwin 自优化验收及发布包测试；Python 与 Node 构建相同的确定性 ZIP，包检查比较完整文件集合和逐文件字节。CI 配置覆盖 Windows/Linux 的 Python 3.10 / 3.12 / 3.14，以及旧 Node 兼容矩阵；配置存在不代表 CI 已通过。未发布迁移验收见 [`evaluation/validation-python-core.md`](evaluation/validation-python-core.md)，发行版验收见 [`evaluation/validation-v030.md`](evaluation/validation-v030.md)。

自动测试与原离线案例使用合成资料；[真实论文有限语料试用与评估协议](evaluation/real-world/README.md) 单独记录来源、实际答复和未测范围。真实科研评估应记录原始检索和输出、近邻发现、引用忠实性、过度断言、误淘汰和下一步建议质量；尚未完成的评估不作为性能证明。历史回测以当时可得信息判断决策，不把后来的实验失败等同于当时应该 KILL。

三个[合成项目示例](examples/) 展示经验、理论和测量任务的不同验证对象；其中论文、证据和资源全部虚构，不能用作科研依据。

## 如何启动自优化

```text
使用 $ai-research-mentor 优化这个科研 skill。
针对我刚才指出的证据定位错误，最多尝试两轮。
保持科研证据门槛，用两版实际输出和独立迁移用例验收。
```

普通使用先积累可追溯反馈；明确维护请求后在预算内运行“冻结基线 → 修改副本 → 实际对照 → 独立审查 → 保留或丢弃”。科研假设失败不是 skill 缺陷。全 tie、自审、干跑、缺迁移验证和科研原则退化均不会获准保留。

按 [`self-improvement.md`](skills/ai-research-mentor/references/self-improvement.md) 保存本轮独立目录、两版内容、冻结用例、输出和评估回执。只读工具核验文件、检查日志和评估版本：

```text
python -B skills/ai-research-mentor/scripts/evolution_guard.py snapshot <维护目录>
python -B skills/ai-research-mentor/scripts/evolution_guard.py checks-hash <本轮目录>/run.json
python -B skills/ai-research-mentor/scripts/evolution_guard.py check <本轮目录>/run.json
```

工具返回 KEEP / REJECT / HOLD，但不运行模型或自动写入文件；宿主在既有维护授权内执行测试和应用，应用前核对正式目录仍等于受评基线。科学记录合同、评测脚本、测试和优化规则默认不可由候选修改；工具与决策契约升级属于单独维护任务。普通优化不自动推送仓库或上传用户材料。

这一模式借鉴 [Darwin Skill](https://github.com/alchaincyf/darwin-skill) 的小步验证思路，独立实现版本与验收检查，无需安装 Darwin。当前 Darwin 的优化主体是宿主流程，通用自评分及其历史数据不作为本 skill 的效果证明。

## 结构与设计来源

```text
skills/ai-research-mentor/
├── SKILL.md
├── agents/openai.yaml
├── references/
│   ├── literature.md
│   ├── ideation.md
│   ├── evaluation.md
│   ├── feedback.md
│   ├── data-contract.md
│   ├── retrieval-adapters.md
│   ├── source-tools.md
│   ├── python-core.md
│   ├── fulltext.md
│   ├── research-outputs.md
│   ├── self-improvement.md
│   └── design-basis.md
├── scripts/
│   ├── research_mentor.py
│   ├── research_audit.py
│   ├── research_sources.py
│   ├── research_outputs.py
│   ├── evolution_guard.py
│   ├── research_audit.mjs
│   ├── research_sources.mjs
│   ├── research_outputs.mjs
│   └── evolution_guard.mjs
├── runtime/research_mentor/      # Python CLI/API 共用的证据、审计、产出与维护实现
├── schemas/
│   ├── notes.schema.json
│   ├── ledger-event.schema.json
│   └── dossier.schema.json
└── tests/
    ├── python/test_core.py
    ├── research_audit.test.mjs
    ├── research_sources.test.mjs
    ├── research_outputs.test.mjs
    └── evolution_guard.test.mjs
```

采用单入口、按需加载细则；文献工具与宿主解耦，不依赖其他 skill 的安装。设计参考了 ResearchStudio、Academic-Research-Agent-Skill、claude-scholar、ChineseResearchLaTeX、NoviScl/AI-Researcher、PaperQA、AstaBench 和 AutoSci 等项目，并保留各自的适用边界。对应来源与未采用的规则见 [`design-basis.md`](skills/ai-research-mentor/references/design-basis.md)。

维护说明见 [CONTRIBUTING.md](CONTRIBUTING.md)。本项目采用 [MIT 许可证](LICENSE)，版权归 `H66e`；选择理由见 [ADR 0002](docs/decisions/0002-license-selection.md)。
