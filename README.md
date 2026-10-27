# academic-scientific-skill

[![Validate skill and release package](https://github.com/H66e/academic-scientific-skill/actions/workflows/test.yml/badge.svg)](https://github.com/H66e/academic-scientific-skill/actions/workflows/test.yml)

**AI Research Mentor**：帮助 AI / ML 科研做四件事——找研究方向、查新（有没有人做过、最近的在做什么）、判断一个方向值不值得投入、写论文/综述/开题。文献检索、全文核验和证据记录服务于这四件事。适用于 Codex，也可由其他支持 `SKILL.md` 的宿主按需读取。

当前版本 **0.9.0**（[v0.9.0 Release](https://github.com/H66e/academic-scientific-skill/releases/tag/v0.9.0)，[全部发布](https://github.com/H66e/academic-scientific-skill/releases)）。变更记录见 [CHANGELOG.md](CHANGELOG.md)。

**0.9.0 是两位评委评审后的大改：报告分级、check-draft、删除资源默认值与标签残留。** 0.8.0 改为“回答三件事、默认不给 GO/HOLD/KILL 标签”。 0.7.0 增加“方向 → 完整研究报告”工作流与先澄清协议。 0.6.0 是自进化维护版本：写作模板纳入受控进化、回执验收更严。 0.5.0 收窄范围（结果解释退役、写作扩到完整初稿）；0.4.0 是 Python-only 重建后的第一个发布，0.3.0 是最后的 Node 实现版本。不同版本的包不同，版本号不能互相指代。本仓库是发布源码：发布包由源码确定性构建、不再提交到 Git，tag 与 GitHub Release 指向构建该包的提交，流程见[发布与版本](#发布与版本)。Codex 安装目录是运行时拷贝，只有显式同步后才会更新，源码提交不会自动进入安装副本。

| 范围 | 当前状态 |
| --- | --- |
| 找方向、查新、gap 检查 | 已实现；记录真实检索、版本、阅读范围与证据定位 |
| 判断方向值不值得做 | 已实现；回答“值不值得、差异在哪、现在能否验证”，给依据、风险与下一步最小验证；默认不输出 GO/HOLD/KILL 标签 |
| 论文、综述、开题写作 | 0.5.0 提升为一等任务；可从真实来源产出完整初稿，模板见 `templates/`，投稿前必须人工核验 |
| 方向 → 完整研究报告 | 0.7.0 新增：先澄清目标/约束/证据/交付，再按报告模板产出可讨论、可执行的完整报告 |
| 实验结果解释（六种状态、结果纠正/失效） | 0.5.0 起退役；旧账本结果事件只读保留、不参与判定，见 [ADR 0010](docs/decisions/0010-scope-refocus-0.5.0.md) |
| 旧 dossier 审计、迁移、独立评审回执与排序 | 维护期只读合同，保留原有数据合同 |
| PDF 正文提取、自动实验日志解析 | 尚未实现；宿主取得正文并实际阅读后再记录 |
| 真实选题、brainstorm 和 gap 质量 | 尚无效果证明；自动测试检查合同与回归，不证明科研价值 |

完整命令与边界见 [Python 工作流](skills/ai-research-mentor/references/python-core.md) 与 [写作工作流](skills/ai-research-mentor/references/research-outputs.md)，实际执行结果见 [0.5.0 发布验收记录](evaluation/validation-v050.md) 与 [历史验收记录](evaluation/validation-v040.md)。

```text
python -B skills/ai-research-mentor/scripts/research_mentor.py --project ../research-private/example doctor
python -B skills/ai-research-mentor/scripts/research_mentor.py --project ../research-private/example init --question "A concrete AI/ML research question"
python -B evaluation/run-python-tests.py
```

外部检索默认阻止 private query；只有 public/deidentified 分类可发送。独立来源工具的 `search`、`verify` 与 `fulltext` 都会在出网前检查分类，`--sensitivity private` 以零请求阻断。上述路径是本地研究数据，不能发布或同步到安装源码中。CLI/API 使用同一 `runtime/research_mentor` 包，`pip install -e .` 可选；无需为 Skill 安装 pip 包。

结果解释已从 0.5.0 起退役：不再提供结果分类、纠正或失效命令，账本里的旧结果事件保留只读、不参与判定（[ADR 0010](docs/decisions/0010-scope-refocus-0.5.0.md)）。阅读资格仍由 `confirm-read` 累计、`retract-read` 显式撤回；两者都使旧评审过期，解除阻塞仍须重评，不能恢复旧 GO。

正式源码、发布包与安装副本的边界见 [工作区与版本治理说明](docs/WORKSPACE_GOVERNANCE.md)。当前发布版本是 0.9.0；如果本机 Codex 仍加载旧副本，需要显式同步，源码更新不会自动进入安装目录。

从具体研究问题出发，把已有证据、推断和待验证假设分开，帮助决定下一步值得投入什么；需要产出时再基于真实来源写论文、综述或开题。它不会承诺新颖性、实验成功或论文录用，也不替你解释实验结果。

## 双栈现状与命令归属

Python 运行时目前包含两套并列且都受支持的获取/审计界面，使用不同的冻结数据合同，命令不能互相替代：

- **ledger 栈**（`research_mentor.py --project ...`）拥有新的获取、证据、阅读、候选与决策能力，写入追加式 `ledger-json-v1` 账本，判定策略为 `python-credibility-v5`。
- **dossier/reference 栈**（`research_audit.py`、`research_sources.py`、`research_outputs.py`、`evolution_guard.py`）服务已发布的 dossier schema 3 / decision contract 3 及独立来源、产出与维护用例；它是**维护期**界面，只做安全与正确性修复、合同兼容和冻结回归证据，不再新增 provider 或科学能力。它的结果/pilot 字段是旧合同，只读保留。

合并两套解析/获取实现被有意推迟：dossier schema 3 / decision contract 3 与 `ledger-json-v1` 都已冻结，一次性合并会同时改动发布数据合同和回归基线，超出当前发布加固范围；合并前保留重复实现作为已记录的技术债。新功能应只进入 ledger 栈，不新增第三个界面。逐模块的合同归属、冻结项和已知分歧见[获取合同映射](docs/design/acquisition-contract-map.md)。

| 命令 | 栈 | 依赖/写入的合同 |
| --- | --- | --- |
| `research_mentor.py --project ... init/doctor/status` | ledger | `ledger-json-v1` |
| `research_mentor.py ... search/resolve/fetch/quote/show-source/confirm-source` | ledger | `ledger-json-v1`；出站分类门控 |
| `research_mentor.py ... candidate/claim/link/coverage/next/assess` | ledger | `ledger-json-v1` + `python-credibility-v5` |
| `research_mentor.py ... confirm-read/retract-read` | ledger | `ledger-json-v1` + `python-credibility-v5` |
| `research_mentor.py ... decision/finalize/revoke` | ledger | `ledger-json-v1` + `python-credibility-v5` |
| `research_mentor.py ... export-dossier` | ledger → dossier 投影 | 输出 schema 3 投影；不含证据关联与评审，不转移批准 |
| `research_mentor.py ... verify-ledger/anchor-ledger/verify-artifacts` | ledger | `ledger-json-v1`、`ledger-anchor-v1`、`text-normalized-v1` 锚点 |
| `research_mentor.py ... lint/recheck` | ledger | 已登记来源/检索的只读检查或重复查询 |
| `research_audit.py init/validate/migrate/fingerprint/rank/verify-receipts` | dossier/reference | dossier schema 3 / decision contract 3（指纹为 dossier canonical JSON） |
| `research_sources.py search/verify/fulltext` | dossier/reference（独立工具） | 不写账本；出站分类门控 |
| `research_outputs.py card/draft/bibtex` | dossier/reference（独立工具） | 提供的笔记/来源记录 |
| `evolution_guard.py snapshot/hash/checks-hash/check` | dossier/reference（维护期） | 提示词/模板变更审计记录，只读 |

两套栈的 paper ID、块/偏移模型和默认隐私分类并不等价；跨栈复制 ID 或偏移没有意义，具体差异与代码位置见合同映射。命令归属依据 [python-core.md](skills/ai-research-mentor/references/python-core.md) 与 [ADR 0009](docs/decisions/0009-acquisition-direction-and-payload-admission.md)。

## 0.9.0 的变化与兼容性

- **check-draft**：新增 `scripts/research_draft.py`，检查报告等级、引用键/核验状态、标签、计划混入结果节与 TODO；只做结构与记录检查，不做真实性判定。
- **报告分级**：`templates/report.md` 要求选择 `concept_memo` / `evidence_review` / `preregistration` / `research_plan`；没有核验来源就停在概念备忘录，不硬填实验设计。
- **删默认值与残留**：澄清不再默认 24GB/2 周；资源未知写未知；venue 规则永不默认；“做/等/放弃”、go/no-go 等残留改为三问 + 继续/停止判据。
- **审计降级**：自优化改称“提示词/模板变更审计”，只证明记录与结构一致；新增未执行的[效果评测协议](evaluation/effect-protocol.md)，在真实盲评前不声称效果。
- **兼容**：账本、dossier 与判定策略不变；旧报告若没有 `report-tier` 或引用未核验，会被 check-draft 判为不完整。

## 0.8.0 的变化与兼容性

- **不再默认给标签**：面向用户的报告、决策卡和对话只回答三件事——值不值得研究、相对最近工作的差异、当前约束下能否做有意义的验证——再给决定性依据、最强反方、未知、下一步与改变判断的判据。不默认输出 GO/HOLD/KILL，也不用“做/等/放弃”代替论证。
- **内部状态仍存在**：Python 账本、dossier 合同、排序与人工决定绑定继续使用 GO/HOLD/KILL 作为机器状态；只有用户明确要求对接账本/合同字段时才出现，并标明它是记录状态，不是研究结论。
- **报告模板**：新增“当前判断与下一步”节，报告结构改为三问 + 证据 + 下一步 + 判据；设计见 [ADR 0013](docs/decisions/0013-no-go-hold-kill-labels.md)。
- **兼容**：运行时、schema、`python-credibility-v5` 与全部门控行为不变；旧报告中的标签可保留为历史，新报告默认不再产生。

## 0.7.0 的变化与兼容性

- **方向 → 完整研究报告**：新增 [报告模板](skills/ai-research-mentor/templates/report.md)。用户给出方向后可产出包含输入假设、近邻定位、可证伪假设与判据、实验设计、统计与启动实验、预期结果与失败分析、计划分工、风险与结论的完整报告，而不是一段问答或文献清单。
- **先澄清**：新增 [澄清协议](skills/ai-research-mentor/references/clarification.md)。方向类报告先问 3–5 个高杠杆问题（目标与用途、硬约束、证据现状、成功标准与风险偏好、交付形式），给默认假设并回述意图；用户说“先出草稿”时按显式假设推进。
- **检查与自进化**：报告模板与澄清协议纳入技能结构检查、模板护栏检查与固定可改白名单；报告模板改动仍需 `writing_template_guardrails` 通过。
- **兼容**：运行时、账本、dossier 与 `python-credibility-v5` 判定不变；报告仍是待人工核验的草稿，不承诺引用真实、新颖性、可行性或录用；文件集合变化后旧包哈希与安装副本需重新同步。

## 0.6.0 的变化与兼容性

- **自进化范围**：固定可改白名单加入 `templates/paper.md`、`templates/survey.md`、`templates/proposal.md`；运行时、脚本、schema、测试、评测规则、data-contract 与自优化协议仍是保护文件，提交的 suite 不能扩大白名单。设计见 [ADR 0011](docs/decisions/0011-evolvable-templates-and-stricter-receipts.md)。
- **模板护栏**：任何模板改动必须附带通过且绑定当前指纹的 `writing_template_guardrails` 检查（由 `check-templates` 生成）；它验证“禁止编造”、`TODO(需来源)`、计划/已观察或事实/假设/计划/风险结构仍在，CI 也会运行。
- **回执逻辑收紧**：`better` / `worse` 必须对应不同的基线/候选输出哈希；两份输出完全相同只能记 `tie` 或重跑；独立评审、全部执行、硬条件、无退化、至少一个 target 改善等 KEEP 条件不变。
- **兼容**：自进化仍只读、不自动应用、不自动推送；文件集合与检查契约变化后，旧维护轮次的 suite、快照与回执不能复用，需从 0.6.0 源码重新冻结基线。科研范围与 `python-credibility-v5` 判定策略不变。

## 0.5.0 的变化与兼容性

- **范围收窄**：技能专精为“找方向、查新、判断值不值得做、写论文/综述/开题”；其他能力后续按研究需要再加。设计见 [ADR 0010](docs/decisions/0010-scope-refocus-0.5.0.md)。
- **结果解释退役**：删除结果分类章节、试验/负结果路由、`feedback.md` 与 `record-result`/`reclassify-result`/`invalidate-result`/`results` 四个命令；判定不再读取结果，结果型 KILL 移除。旧账本中的 result 事件保留只读校验、不影响判定，旧评审因 policy 变化过期一次，需重评。
- **写作一等化**：可以从真实来源产出论文、综述、开题的完整初稿，新增 [写作工作流](skills/ai-research-mentor/references/research-outputs.md) 与 `templates/` 模板；禁止编造引用、数字、实验、结果或 venue 规则，未执行实验必须标为计划，投稿前必须人工核验。
- **兼容**：dossier schema 3 / decision contract 3 与其结果字段仍由维护栈只读支持；`ledger-json-v1` 与 17 类事件词表不变，旧账本可继续 `verify-ledger`/`verify-artifacts`；0.4.x 可作为仍需结果登记的旧版本保留。
- **未变**：真实选题、gap 与写作质量仍未测量；PDF 抽取与实验日志解释仍未实现。

0.4.0 及更早的行为变化（发布包不入 Git、隐私分类门禁、严格 CLI、失败 envelope、`source.fetch` 回执重放）继续有效，细节见 [CHANGELOG.md](CHANGELOG.md)。

## 能做什么

- 探索方向：从已知结果、局限、矛盾和失败模式形成少量可检验候选，允许零个合格选题。
- 文献查找：记录实际检索、筛选理由、文献身份、版本、阅读范围和证据定位，区分基础工作、最近更新和技术上最接近的工作。
- 实际来源工具：Crossref 查询、DOI/arXiv 身份核验，以及有预算边界的 HTML/PDF 获取；取得内容后再由宿主实读与核验。
- 研究缺口：对照已知条件、缺失知识、最强替代解释和已有绕行方案，用真实反向检索及判别测试检查 gap。
- 科研产出：轻量决策/gap 卡、近邻比较、开题、研究提案、综述，以及基于真实来源的论文完整初稿；未执行实验写成计划，未核验引用不进正文。
- 选题评估：逐候选查新，检查强基线、前置条件、资源、指标与反证方法，回答三件事（值不值得、差异在哪、现在能否验证）及依据、风险与下一步；默认不给 GO/HOLD/KILL 标签。
- 类型适配：支持经验、理论、测量、数据集和复现研究，不强制固定候选数量或两周训练计划。
- 持续记录：dossier 按候选实际依赖计算评审指纹，ledger 使用科学输入的保守快照；两种流程都可使用 Python。单独记录排序权重，保存有适用条件和重访条件的历史判断。
- 提示词/模板变更审计：从实际流程失误提出小改动，在独立副本与冻结用例上验证；通过只说明记录与结构一致，不证明科研质量或效果提升。

## 安装与使用

完整 skill 位于 [`skills/ai-research-mentor`](skills/ai-research-mentor)。推荐从 [v0.9.0 Release](https://github.com/H66e/academic-scientific-skill/releases/tag/v0.9.0) 下载 `ai-research-mentor-0.9.0.zip`，解压后得到 `ai-research-mentor/` 文件夹；也可以从源码构建：`python -B evaluation/skill_tools.py package` 生成 `dist/ai-research-mentor.zip`（不入 Git）。压缩包内的 `ai-research-mentor` 文件夹包含全部运行资源。

Codex 用户将该文件夹放入用户技能目录，默认为 `~/.codex/skills/`。升级时先把旧目录移走或改名备份，避免两版文件混用；Windows PowerShell 的本地源码安装示例：

```powershell
$researchSkills = Join-Path $env:USERPROFILE '.codex\skills'
$researchTarget = Join-Path $researchSkills 'ai-research-mentor'
if (Test-Path -LiteralPath $researchTarget) { throw '已有同名 skill，请先备份或移走现有版本再安装 0.9.0。' }
New-Item -ItemType Directory -Path $researchSkills -Force | Out-Null
Copy-Item -LiteralPath '.\skills\ai-research-mentor' -Destination $researchSkills -Recurse
```

如果设置了 `CODEX_HOME`，请使用其 `skills` 子目录。让宿主重新发现技能后，可显式调用：

```text
使用 $ai-research-mentor 帮我探索大模型 agent 的研究问题。
先梳理已有认识和最接近的论文，评估贡献与可行性，再建议下一步。
我的已有材料和资源约束是：……
```

也可以只请求找论文、评估一个想法，或让它帮你起草论文、综述与开题，skill 会按任务加载相关细则。

普通科研讨论不强制启用脚本、模型 API key 或研究代理框架。需要可复现工具时使用 Python 3.10+ 标准库来源工具，或宿主实际提供的搜索、PDF 和文献库能力。分别记录检索来源、全文访问、引用扩展和代码访问能力，以及实际覆盖和失败；离线时明确语料边界，不冒充完成外部查新。

## 发布与版本

`VERSION` 是版本真源；`evaluation/tests/test_version_consistency.py` 核对 `pyproject.toml`、`research_mentor.__version__`、README 当前版本行与 CHANGELOG 小节。当前发布是 [v0.9.0](https://github.com/H66e/academic-scientific-skill/releases/tag/v0.9.0)（报告分级与 check-draft），历史发布是 [v0.8.0](https://github.com/H66e/academic-scientific-skill/releases/tag/v0.8.0)（三问代替标签），历史发布是 [v0.7.0](https://github.com/H66e/academic-scientific-skill/releases/tag/v0.7.0)（研究报告与澄清）、[v0.6.0](https://github.com/H66e/academic-scientific-skill/releases/tag/v0.6.0)（自进化模板纳管）、[v0.5.0](https://github.com/H66e/academic-scientific-skill/releases/tag/v0.5.0)（范围收窄）、[v0.4.0](https://github.com/H66e/academic-scientific-skill/releases/tag/v0.4.0)（Python-only 重建）、[v0.3.0](https://github.com/H66e/academic-scientific-skill/releases/tag/v0.3.0)（最后的 Node 实现），见[全部发布](https://github.com/H66e/academic-scientific-skill/releases)。不同版本对应不同的包，不能用同一版本号互相指代；tag 一旦推送即不可变。发布流程：

```text
python -B evaluation/run-python-tests.py
python -B evaluation/skill_tools.py package
python -B evaluation/skill_tools.py check-package
```

`package` 从源码确定性构建 `dist/ai-research-mentor.zip`，该文件不入 Git（`dist/` 被忽略）；CI 在 6 个矩阵作业中构建并用 `check-package` 复算，GitHub Release 附加同一次构建的包。设计理由与替代方案见 [ADR 0008](docs/decisions/0008-release-identity-and-package-artifacts.md)。Codex 安装副本不由 CI 修改，同步是单独的显式动作。

发布同时提供包与同名 `.sha256` 文件（如 `ai-research-mentor-0.9.0.zip.sha256`）。下载后先在本地重算并比对，而不是只信任文件名或下载页面：

```text
sha256sum ai-research-mentor-0.9.0.zip                    # Linux/macOS
Get-FileHash -Algorithm SHA256 -LiteralPath '.\ai-research-mentor-0.9.0.zip'   # Windows PowerShell
```

把输出中的哈希值（`sha256sum` 输出第一列、PowerShell 的 `Hash` 字段）与 `.sha256` 文件中的哈希值比较，一致后再解压；`.sha256` 行内记录的是构建产物文件名（Release 资产或 CI 产物可能同名不同前缀），重命名下载文件不影响哈希比较。该文件由 CI 从同一次构建计算，但校验只说明下载文件与这个发布资产一致，不证明内容正确或安全，也不认证 Release 之外的副本；校验失败时重新下载，不要改用其他来源的同名文件。发布资产同时有 SHA-256 与 tag==VERSION 检查，见 [CONTRIBUTING.md](CONTRIBUTING.md#发布流程)。

## 从实际来源到研究材料

在仓库根目录可运行以下独立命令；它们按当前请求组合，不要求每次执行全部步骤：

```text
python -B skills/ai-research-mentor/scripts/research_sources.py search --sensitivity public --query "grouped query attention" --rows 10 --pages 1
python -B skills/ai-research-mentor/scripts/research_sources.py verify --doi 10.18653/v1/2023.emnlp-main.298 --expect-year 2023
python -B skills/ai-research-mentor/scripts/research_sources.py fulltext --arxiv 2305.13245v1 --format pdf
python -B skills/ai-research-mentor/scripts/research_outputs.py card examples/lightweight-example/notes.json
python -B skills/ai-research-mentor/scripts/research_outputs.py draft examples/lightweight-example/notes.json --name example-question
python -B skills/ai-research-mentor/scripts/research_outputs.py bibtex evaluation/real-world/v030-forward/source-records.json
```

`search` 输出实际 `searches`/`papers`，`verify` 返回身份与可选元数据对照；宿主检查后再合并记录。Crossref 未覆盖的预印本及前后向引用由实际可用来源补充。`fulltext` 取得 HTML 块或 PDF 字节，分别标记 `needs_host_review` / `needs_host_extraction`，不自动记为 section/full_text 证据。

透明代理的 fake-IP 环境可显式使用 `--trusted-provider-transport`，仅适用于内部构造的固定 Crossref/arXiv 请求，不能用于任意 `--url`。工具保持 TLS、超时、请求与字节预算；不更改系统网络设置。详见 [source-tools.md](skills/ai-research-mentor/references/source-tools.md)。

`card` 整理已有笔记；`draft` 只创建初步项目结构，不制造论文、评审或 GO；`bibtex` 只导出提供的元数据，未知项提醒并省略，冲突需解决。这些命令默认只写标准输出，正文缓存需要显式 `--root` 和新 `--out`。轻量示例见 [examples/lightweight-example](examples/lightweight-example/README.md)，编辑辅助 Schema 在 [schemas](skills/ai-research-mentor/schemas)。

三个产出命令也接受 `-` 从标准输入读取 JSON，例如 `python -B skills/ai-research-mentor/scripts/research_outputs.py card -`。BibTeX 根据实际 DOI/arXiv/OpenReview 身份关联归并同源条目；身份或版本冲突仍需先核对来源，不猜测合并。

gap 方法见 [ideation.md](skills/ai-research-mentor/references/ideation.md)，全文实读见 [fulltext.md](skills/ai-research-mentor/references/fulltext.md)，开题、综述及论文草稿见 [research-outputs.md](skills/ai-research-mentor/references/research-outputs.md)。未执行的验证写为计划，不写成发现。

## 可选项目记录工具

审计程序使用 **Python 3.10+ 标准库**，无需 pip 安装。运行、API、测试、CI 与打包统一使用 Python。它只检查记录、版本、回执与排序必要条件，不联网，也不判断论文真实性或科学正确性；联网能力由独立来源工具提供。

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

Python 审计保留既有 dossier 指纹格式和回执门槛；没有已核验回执时，裸 `rank` 不批准 full_validation。回执核验不能证明评审者实际独立或科学结论正确。HOLD 可建议补信息；有界 pilot 也需基础科学门槛。

`validate` 返回结构错误与提醒；warnings 不使合法的初步构思无效，也不替代决策门控。旧 schema 1 或旧决策契约可读取，但旧评审不授权当前决定，需显式迁移并重新评审：

```text
python -B skills/ai-research-mentor/scripts/research_audit.py migrate old-project/dossier.json
```

迁移输出到标准输出，不覆盖输入；检查后用 UTF-8 另存新文件。旧 reviews 完整归档到 history 并要求重评，旧 pilots 物化 run_id、保留原结果和产物；迁移不会编造分类替代、失效、新证据角色或新评审指纹。

字段说明见 [`data-contract.md`](skills/ai-research-mentor/references/data-contract.md)，评分锚点与门控见 [`evaluation.md`](skills/ai-research-mentor/references/evaluation.md)。无 Python 时依合同手动核验，明确自动检查未运行。旧脚本和导入接口已退役，请将调用改为当前 Python 入口；已有研究数据无需因此改写，迁移边界见 [ADR 0007](docs/decisions/0007-python-only-toolchain.md)。

## 验证

```text
python -B evaluation/run-python-tests.py
python -B evaluation/skill_tools.py check-skill
python -B evaluation/skill_tools.py check-examples
python -B evaluation/skill_tools.py check-templates
python -B skills/ai-research-mentor/scripts/research_draft.py <draft.md>
python -B evaluation/skill_tools.py check-python-only
python -B evaluation/skill_tools.py package
python -B evaluation/skill_tools.py check-package
```

以上测试与维护命令只需要 Python。测试入口包含科研审计、来源协议、研究产出、Darwin 自优化验收及发布包测试；冻结协议用例保留迁移前的实际观察值，新增原生测试检查当前实现。0.4.0 新增的回归覆盖包括出站隐私分类（含 `https://` 被误判为本地路径的修复）、严格 CLI 参数、失败 envelope、17 类账本事件 payload 准入、`source.fetch` 回执与 IR 重放（[`test_privacy_policy.py`](evaluation/tests/test_privacy_policy.py)、[`test_cli_strict.py`](evaluation/tests/test_cli_strict.py)、[`test_ledger_payloads.py`](evaluation/tests/test_ledger_payloads.py)、[`test_verification_metadata.py`](evaluation/tests/test_verification_metadata.py)）。0.5.0 新增/更新的回归覆盖包括：旧账本结果事件只读兼容与 legacy_result_events_ignored 提示、v5 判定不读取结果、四个结果命令未注册、写作模板与技能内链接检查（0.5.0 本地 291 tests，OK，1 skip，见 [validation-v050.md](evaluation/validation-v050.md)）。0.6.0 新增/更新的回归覆盖包括：模板改动强制 `writing_template_guardrails` 检查、`check-templates` 正反例、`better`/`worse` 必须有不同输出哈希。0.7.0 新增/更新的回归覆盖包括：报告模板与澄清协议纳入结构检查、四份模板护栏检查、报告/澄清文件进入自进化白名单。0.8.0 将三者标为账本内部状态；0.9.0 新增报告分级、check-draft、删除资源默认值与标签残留，并明确未执行效果评测（本轮本地 **304 tests，OK，1 skip**，见 [validation-v090.md](evaluation/validation-v090.md)）。ZIP 使用确定性文件顺序和时间戳；`check-package` 先复算一次源码构建，若本地已用 `package` 生成发布包则再逐字节比较两次构建（确定性检查）。CI 在 Windows/Linux × Python 3.10 / 3.12 / 3.14 的 6 个作业中运行全量测试、结构检查、构建发布包并保存为运行产物；某个历史配置存在不代表当前提交已通过，实际矩阵结果以仓库 Actions 记录为准。迁移验收见 [`evaluation/validation-python-core.md`](evaluation/validation-python-core.md)，0.9.0 发布验收见 [`evaluation/validation-v090.md`](evaluation/validation-v090.md)，0.8.0 发布验收见 [`evaluation/validation-v080.md`](evaluation/validation-v080.md)，0.7.0 发布验收见 [`evaluation/validation-v070.md`](evaluation/validation-v070.md)，0.6.0 发布验收见 [`evaluation/validation-v060.md`](evaluation/validation-v060.md)，0.5.0 发布验收见 [`evaluation/validation-v050.md`](evaluation/validation-v050.md)，0.4.0 发布验收见 [`evaluation/validation-v040.md`](evaluation/validation-v040.md)，发行版历史验收见 [`evaluation/validation-v030.md`](evaluation/validation-v030.md)。

自动测试与原离线案例使用合成资料；[真实论文有限语料试用与评估协议](evaluation/real-world/README.md) 单独记录来源、实际答复和未测范围。真实科研评估应记录原始检索和输出、近邻发现、引用忠实性、过度断言、误淘汰和下一步建议质量；尚未完成的评估不作为性能证明。历史回测以当时可得信息判断决策，不把后来的实验失败等同于当时应该 KILL。

三个[合成项目示例](examples/) 展示经验、理论和测量任务的不同验证对象；其中论文、证据和资源全部虚构，不能用作科研依据。

## 如何启动提示词/模板变更审计

```text
使用 $ai-research-mentor 优化这个科研 skill。
针对我刚才指出的证据定位错误，最多尝试两轮。
保持科研证据门槛，用两版实际输出和独立迁移用例验收。
```

普通使用先积累可追溯反馈；明确维护请求后在预算内运行“冻结基线 → 修改副本 → 实际对照 → 独立审查 → 保留或丢弃”。这是提示词/模板变更审计，只证明记录与结构一致，不证明科研质量或效果提升。科研假设失败不是 skill 缺陷。全 tie、自审、干跑、缺迁移验证和科研原则退化均不会获准保留。自优化可改的固定白名单是 `SKILL.md`、literature/ideation/evaluation/research-outputs/clarification 五份细则和四个写作模板；运行时、脚本、schema、测试与评测规则仍是保护文件。改模板时回执必须附带 `writing_template_guardrails` 检查（由 `check-templates` 生成），且 `better` / `worse` 判定必须有可观察的基线/候选输出差异，否则只能记 tie 或重跑。

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
│   ├── data-contract.md
│   ├── retrieval-adapters.md
│   ├── source-tools.md
│   ├── python-core.md
│   ├── fulltext.md
│   ├── research-outputs.md
│   ├── clarification.md
│   ├── self-improvement.md
│   └── design-basis.md
├── templates/
│   ├── paper.md
│   ├── survey.md
│   ├── proposal.md
│   └── report.md
├── scripts/
│   ├── research_mentor.py
│   ├── research_audit.py
│   ├── research_sources.py
│   ├── research_outputs.py
│   └── evolution_guard.py
├── runtime/research_mentor/      # Python CLI/API 共用的证据、审计、产出与维护实现
├── schemas/
│   ├── notes.schema.json
│   ├── ledger-event.schema.json
│   └── dossier.schema.json
└── tests/
    ├── python/test_core.py
    ├── python/test_audit.py
    ├── python/test_sources.py
    ├── python/test_outputs.py
    ├── python/test_evolution.py
    └── python/test_readings.py
```

采用单入口、按需加载细则；文献工具与宿主解耦，不依赖其他 skill 的安装。设计参考了 ResearchStudio、Academic-Research-Agent-Skill、claude-scholar、ChineseResearchLaTeX、NoviScl/AI-Researcher、PaperQA、AstaBench 和 AutoSci 等项目，并保留各自的适用边界。对应来源与未采用的规则见 [`design-basis.md`](skills/ai-research-mentor/references/design-basis.md)。

维护说明见 [CONTRIBUTING.md](CONTRIBUTING.md)。安全问题不要开公开 issue，按 [SECURITY.md](SECURITY.md) 私下报告；支持版本、代码实际保证的边界和不处理的事项也在该文件。本项目采用 [MIT 许可证](LICENSE)，版权归 `H66e`；选择理由见 [ADR 0002](docs/decisions/0002-license-selection.md)。
