# academic-scientific-skill

[![Validate skill and release package](https://github.com/H66e/academic-scientific-skill/actions/workflows/test.yml/badge.svg)](https://github.com/H66e/academic-scientific-skill/actions/workflows/test.yml)

**AI Research Mentor：科研报告的可审计结构层。** 它把“检索/获取 → 来源身份 → 阅读确认 → 主张分级 → 报告合同”做成可执行、可检查的本地流程，服务于 AI/ML 科研的方向判断、查新与写作准备；适用于 Codex，也可由其他支持 `SKILL.md` 的宿主按需读取。

当前版本 **0.14.1**（[v0.14.1 Release](https://github.com/H66e/academic-scientific-skill/releases/tag/v0.14.1)，[全部发布](https://github.com/H66e/academic-scientific-skill/releases)）。版本变更历史见 [CHANGELOG.md](CHANGELOG.md)，不再在 README 中重复。

## 它做什么 / 不做什么

| 可执行、可检查的机制 | 不能声称或尚未证明 |
| --- | --- |
| 检索/获取带哈希入账（`ledger-json-v1`，追加式） | 近邻是否选全、致命问题是否被诚实回答、引用是否支持主张 |
| DOI/arXiv/URL/标题身份与账本来源对账 | `check-draft` 通过不等于科研质量可信 |
| user/T1 `section`/`full_text` 阅读确认才计入等级 | `reader:model` 只是声明，不是账本认证 |
| A/B/C 主张绑定近邻候选、账本阅读与定位 | 尚未执行效果评测；没有“比裸模型更好”的证据 |
| 报告合同检查：`nearest-set-json` v2、六列主张表、`provisional-json`、五列引用与阅读范围 | PDF 正文提取、自动实验日志解析未实现；不承诺新颖性、实验成功或论文录用 |
| 出网前隐私分类门控、确定性打包与发布校验 | 论文/综述不在 `check-draft` 范围 |

报告合同的机器真源是 `skills/ai-research-mentor/runtime/research_mentor/draft.py` 与 [deep-read-gate.md](skills/ai-research-mentor/references/deep-read-gate.md)；ADR、模板、SKILL 摘要和验收记录都只是它们的说明，冲突时以检查器行为为准。

## 快速开始

完整 skill 位于 [`skills/ai-research-mentor`](skills/ai-research-mentor)。推荐从 [v0.14.1 Release](https://github.com/H66e/academic-scientific-skill/releases/tag/v0.14.1) 下载 `ai-research-mentor-0.14.1.zip`，解压后得到 `ai-research-mentor/` 文件夹；也可以从源码构建：`python -B evaluation/skill_tools.py package` 生成 `dist/ai-research-mentor.zip`（不入 Git）。压缩包内的 `ai-research-mentor` 文件夹包含全部运行资源。

安装到 Codex（默认 `~/.codex/skills/`；设置了 `CODEX_HOME` 则用其 `skills` 子目录）：

```powershell
$researchSkills = Join-Path $env:USERPROFILE '.codex\skills'
$researchTarget = Join-Path $researchSkills 'ai-research-mentor'
if (Test-Path -LiteralPath $researchTarget) { throw '已有同名 skill，请先备份或移走现有版本再安装 0.14.1。' }
New-Item -ItemType Directory -Path $researchSkills -Force | Out-Null
Copy-Item -LiteralPath '.\skills\ai-research-mentor' -Destination $researchSkills -Recurse
```

最小本地检查（需要 Python 3.10+，仅标准库）：

```text
python -B evaluation/run-python-tests.py
python -B skills/ai-research-mentor/scripts/research_mentor.py --project ../research-private/example doctor
python -B skills/ai-research-mentor/scripts/research_mentor.py --project ../research-private/example init --question "A concrete AI/ML research question"
```

写报告时先读 [报告模板](skills/ai-research-mentor/templates/report.md)，交付前运行：

```text
python -B skills/ai-research-mentor/scripts/research_draft.py <draft.md> --ledger <project>
```

命令与边界详见 [python-core.md](skills/ai-research-mentor/references/python-core.md)；检索、全文核验与证据记录默认阻止 `private` 查询，只有 public/deidentified 分类可以出网。

## 报告合同（v2 摘要）

`evidence_review` 及以上报告需要：唯一的 `nearest-set-json` v2（检索式、候选、状态、reader、账本绑定、定位、致命问题、`uncovered`）、六列主张表（编号/主张/等级/近邻/依据/翻转条件）、唯一的 `provisional-json` v1（C 级主张、翻转条件、获取路径、仍未读的核验问题），以及五列参考文献（阅读范围只接受 `full_text` 或 `section:<定位>`）。正文“当前判断与下一步”的判断单元必须带 `[C#]`；计划单元以“下一步/行动/核验动作/获取路径/成本与停止”开头可豁免，但不得夹带正式判断词。

结构检查与模板护栏：

```text
python -B evaluation/skill_tools.py check-skill
python -B evaluation/skill_tools.py check-templates
python -B evaluation/skill_tools.py check-examples
python -B evaluation/skill_tools.py check-python-only
python -B evaluation/skill_tools.py package
python -B evaluation/skill_tools.py check-package
```

## 效果评测（未执行）

v0.14.0（commit `efc6a0f`）已冻结为评测基线。效果协议在 [evaluation/effect-protocol.md](evaluation/effect-protocol.md)，可执行材料包在 [evaluation/effect-pilot/](evaluation/effect-pilot/README.md)：任务模板、三臂提示、去格式脚本、盲评表、manifest 示例和预注册停止判据。**协议尚未执行，没有任何效果结论**；没有真实任务提供者、独立盲评者和预注册判据时，不得用测试通过、CI 或 API 评审分数替代效果证据。

## 现实定位与范围（维护期冻结）

- **保留主线**：ledger 栈（检索、获取、引用身份、阅读确认、隐私门控）与报告合同检查。
- **维护期只读**：dossier/reference 栈、自进化审计（`evolution_guard`）、内部 GO/HOLD/KILL 状态与回执排序。它们保留原有数据合同，只做安全与正确性修复，不再新增 provider 或科学能力；详见 [获取合同映射](docs/design/acquisition-contract-map.md) 与 [工作区治理](docs/WORKSPACE_GOVERNANCE.md)。
- **暂停**：新增报告类型、新数据合同、自动近邻完备性、更多模板字段或检查规则；这些要等效果评测给出信号后再动。
- 研究材料、私有论文、请求日志与运行输出始终留在仓库外；仓库只保存源码、合同与可复现测试。

## 发布与安装边界

`VERSION` 是版本真源；`evaluation/tests/test_version_consistency.py` 核对 `pyproject.toml`、`research_mentor.__version__`、README 版本行与 CHANGELOG 小节。tag 指向构建发布包的提交且不可变；发布包由 `package` 确定性构建、不入 Git，CI 在 Ubuntu/Windows × Python 3.10/3.12/3.14 的 6 个作业中运行测试并构建产物。GitHub Release 附带同一个包与 `.sha256`；校验只说明下载文件与资产一致，不认证其他副本。Codex 安装副本只在显式同步后更新，源码提交不会自动进入安装目录；流程见 [CONTRIBUTING.md](CONTRIBUTING.md) 与 [ADR 0008](docs/decisions/0008-release-identity-and-package-artifacts.md)。

## 维护与反馈

维护、变更和发布流程见 [CONTRIBUTING.md](CONTRIBUTING.md)；结构与设计来源见 [design-basis.md](skills/ai-research-mentor/references/design-basis.md) 和 `docs/decisions/`。安全问题不要开公开 issue，按 [SECURITY.md](SECURITY.md) 私下报告。本项目采用 [MIT 许可证](LICENSE)，版权归 `H66e`，选择理由见 [ADR 0002](docs/decisions/0002-license-selection.md)。
