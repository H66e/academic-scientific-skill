# academic-scientific-skill

**AI Research Mentor**：面向 AI / ML 科研的选题、文献查找、查新、可行性评估与验证反馈 skill。适用于 Codex，也可由其他支持 `SKILL.md` 的宿主按需读取。

从具体研究问题出发，将已有证据、推断和待验证假设分开，帮助决定下一步值得投入什么。它不会承诺新颖性、实验成功或论文录用。

## 能做什么

- 探索方向：从已知结果、局限、矛盾和失败模式形成少量可检验候选，允许零个合格选题。
- 文献查找：记录实际检索、文献身份、版本、阅读范围和证据定位，区分基础工作、最近更新和技术上最接近的工作。
- 选题评估：逐候选查新，检查强基线、前置条件、资源、指标与反证方法，给出 GO / HOLD / KILL 及依据。
- 类型适配：支持经验、理论、测量、数据集和复现研究，不强制固定候选数量或两周训练计划。
- 验证反馈：区分跑通、执行失败、支持、反驳、无结论和尚未运行；选题、约束或证据变化后重新评估。
- 持续记录：使用输入指纹避免沿用过期评审；保存有适用条件和重访条件的历史判断。
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

普通科研讨论不需要额外 Python 环境、模型 API key 或研究代理框架。联网搜索、PDF 阅读和文献库访问使用宿主实际提供的能力；离线时明确语料边界，不冒充完成外部查新。

## 可选项目记录工具

辅助程序使用 **Node.js 18+ 标准库**，无需 npm 安装。它只检查记录、版本和排序必要条件，不联网，也不判断论文真实性或科学正确性。

在仓库根目录运行：

```text
node skills/ai-research-mentor/scripts/research_audit.mjs init --root . --name my-topic
node skills/ai-research-mentor/scripts/research_audit.mjs validate my-topic/dossier.json
node skills/ai-research-mentor/scripts/research_audit.mjs fingerprint my-topic/dossier.json IDEA-ID
node skills/ai-research-mentor/scripts/research_audit.mjs rank my-topic/dossier.json
```

先由研究者或宿主填写项目事实、实际来源、候选和评估。初始化文件不含论文或评审；`fingerprint` 的 `basis_hash` 写入对应评审后，排序才会检查其是否仍然有效。项目记录应保存于用户工作区，不放进安装后的 skill 目录。

字段说明见 [`data-contract.md`](skills/ai-research-mentor/references/data-contract.md)，评分锚点与门控见 [`evaluation.md`](skills/ai-research-mentor/references/evaluation.md)。无 Node 时仍可依这些规范手动完成任务。

## 验证

```text
node --test skills/ai-research-mentor/tests/research_audit.test.mjs skills/ai-research-mentor/tests/evolution_guard.test.mjs
node evaluation/check-skill.mjs skills/ai-research-mentor
```

当前版本通过 **59 项回归测试**、入口元数据与本地引用检查，以及科研与自优化模式的独立上下文离线案例。案例与验收范围见 [`evaluation/validation.md`](evaluation/validation.md)。测试材料明确为合成资料，不是实际论文或科研结果；这些检查不证明真实联网检索覆盖或选题成功率。

## 如何启动自优化

```text
使用 $ai-research-mentor 优化这个科研 skill。
针对我刚才指出的证据定位错误，最多尝试两轮。
保持科研证据门槛，用两版实际输出和独立迁移用例验收。
```

普通使用先积累可追溯反馈；明确维护请求后在预算内运行“冻结基线 → 修改副本 → 实际对照 → 独立审查 → 保留或丢弃”。科研假设失败不是 skill 缺陷。全 tie、自审、干跑、缺迁移验证和科研原则退化均不会获准保留。

按 [`self-improvement.md`](skills/ai-research-mentor/references/self-improvement.md) 保存本轮独立目录、两版内容、冻结用例、输出和评估回执。只读工具核验文件、检查日志和评估版本：

```text
node skills/ai-research-mentor/scripts/evolution_guard.mjs snapshot <维护目录>
node skills/ai-research-mentor/scripts/evolution_guard.mjs checks-hash <本轮目录>/run.json
node skills/ai-research-mentor/scripts/evolution_guard.mjs check <本轮目录>/run.json
```

工具返回 KEEP / REJECT / HOLD，但不运行模型或自动写入文件；宿主在既有维护授权内执行测试和应用，应用前核对正式目录仍等于受评基线。科学记录合同、评测脚本、测试和优化规则默认不可由候选修改。普通优化不自动推送仓库或上传用户材料。

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
│   ├── self-improvement.md
│   └── design-basis.md
├── scripts/
│   ├── research_audit.mjs
│   └── evolution_guard.mjs
└── tests/
    ├── research_audit.test.mjs
    └── evolution_guard.test.mjs
```

采用单入口、按需加载细则；文献工具与宿主解耦，不依赖其他 skill 的安装。设计参考了 ResearchStudio、Academic-Research-Agent-Skill、claude-scholar、ChineseResearchLaTeX、NoviScl/AI-Researcher、PaperQA、AstaBench 和 AutoSci 等项目，并保留各自的适用边界。对应来源与未采用的规则见 [`design-basis.md`](skills/ai-research-mentor/references/design-basis.md)。
