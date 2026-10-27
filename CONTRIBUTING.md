# Contributing

先说明可复现的问题、研究任务和预期行为，再提交范围明确的修改。用合成材料复现时明确标记；用户论文、项目记录和未发表结果不得作为默认公开测试资料。安全问题不要开公开 issue，按 [SECURITY.md](SECURITY.md) 私下报告；该文件同时说明支持版本与代码实际保证的边界。

在仓库根目录运行：

```text
python -B evaluation/run-python-tests.py
python -B evaluation/skill_tools.py check-skill
python -B evaluation/skill_tools.py check-examples
python -B evaluation/skill_tools.py check-templates
python -B evaluation/skill_tools.py check-python-only
python -B evaluation/skill_tools.py package
python -B evaluation/skill_tools.py check-package
```

Python 3.10+ 工具链只使用标准库，源码位于 `skills/ai-research-mentor/runtime/research_mentor/`；CLI 与导入 API 共用该实现。`pip install -e .` 是可选开发安装，不是使用 Skill 的前提。Python 测试包含工具自动回执、账本完整性、文本锚点、默认隐私、过期决定，以及 dossier 投影合法但不恢复 GO 的检查。dossier 审计、来源工具、产出和自优化验收均为原生 Python。既有 dossier 指纹与迁移前冻结的协议观察值比较；ledger 的哈希仍是独立协议，不能混用。

运行、维护、测试、CI 与打包只使用 Python，不保留另一个语言实现或调用桥接。旧脚本与导入接口已退役；将调用改为 Python CLI 或 `research_mentor` API，参见 [ADR 0007](docs/decisions/0007-python-only-toolchain.md)。旧 dossier 数据和既有指纹不因此改写，旧合同记录仍须显式迁移重评。来源工具默认拒绝 private 查询；公共 fixture 和实际公开查询均须明确分类。

Python 新字段的修改应更新 [python-core.md](skills/ai-research-mentor/references/python-core.md)、对应测试和 ADR。CI 的 Python 作业配置 Windows/Linux × 3.10/3.12/3.14；本地实际执行版本及范围见 [Python 核心验收记录](evaluation/validation-python-core.md)，配置存在不代表 CI 已通过。使用 `-B` 防止字节码混入工作树，打包也排除 `__pycache__` 和 `.pyc/.pyo`。

测试入口发现 skill 的 `tests/python/` 与仓库 `evaluation/tests/` 下的 `test_*.py`，包含科研审计、来源协议、研究产出、自优化验收与发布包完整性。来源自动测试注入协议响应，不使用外网；真实联网试用单独保留请求、状态、字节哈希与未读范围，不把 fixture 当召回测试。ZIP 由固定文件顺序与固定时间戳生成，包含 skill 目录中的完整文件集合，以及仓库根 `LICENSE`（打包为 `ai-research-mentor/LICENSE`）。发布包是构建产物而不是源码：`dist/` 被 Git 忽略，`python -B evaluation/skill_tools.py package` 本地构建，`check-package` 复算并与本地包逐字节比较；不要把 `dist/ai-research-mentor.zip` 提交进仓库，发布时使用同一次构建的文件。

修改 schema、评审指纹、证据关联或决策门控时，同步更新 [data-contract.md](skills/ai-research-mentor/references/data-contract.md)、迁移行为和回归测试。保留旧记录与历史判断，不把旧评审包装成新合同下的有效评审。

`schemas/*.schema.json` 用于编辑辅助；动态引用、必要条件、当前契约与收据核验仍由审计工具负责。决策语义变化须同步 decision_contract_version，不以 schema_version 未变为由继续使用旧批准。

发布时更新 `VERSION` 与 `CHANGELOG.md`，列出实际验证和剩余限制。`VERSION` 是版本真源：`evaluation/tests/test_version_consistency.py` 核对 `pyproject.toml`、`research_mentor.__version__`、`README.md` 的当前版本行与 `CHANGELOG.md` 的对应小节，改漏任一处即失败。`schema_version` 与 `decision_contract_version` 计的是 dossier 契约修订，不是发行版本，不随 `VERSION` 变动。CI 在 Ubuntu × Windows × Python 3.10 / 3.12 / 3.14 的矩阵中运行全量测试、结构检查、构建发布包并保存运行产物；配置存在不代表这些环境已经执行通过，实际结果以 Actions 记录为准。

## 发布流程

1. 在 CHANGELOG 写清楚的发布小节，更新 `VERSION`、`pyproject.toml`、README 当前版本行，并补齐验收记录。
2. 本地运行 `python -B evaluation/run-python-tests.py` 与 `check-skill`、`check-examples`、`check-python-only`、`package`、`check-package`。
3. 提交并以该提交打 annotated tag（`v<VERSION>`）；tag 一旦推送即视为不可变，后续改动必须升版本。CI 在 tag 推送时额外核对 `GITHUB_REF_NAME` 等于 `v` 加 `VERSION` 内容，不一致即失败，因此打 tag 前先确认版本四处一致。
4. 用该 tag 构建的同一个包创建 GitHub Release 并附加为 asset；发布资产同时附带该包的 `.sha256` 校验文件（如 `ai-research-mentor-0.8.0.zip.sha256`），由 CI 从同一次构建计算，CI 运行产物中的包应与之一致。README 的本地校验步骤只证明下载文件与该资产一致，不认证 Release 之外的副本。
5. 同步 Codex 安装副本是发布之后的单独显式动作，不由 CI 自动执行；同步前确认安装副本未被并发修改。

自优化候选只能修改 [self-improvement.md](skills/ai-research-mentor/references/self-improvement.md) 允许的范围。接口、测试和验收规则变更应作为单独维护任务，不由待验候选自行放宽规则。

本项目采用 [MIT 许可证](LICENSE)，版权归 `H66e`，选择理由见 [ADR 0002](docs/decisions/0002-license-selection.md)。版权署名与许可证类型由项目所有者决定；更改时必须同步 `README.md`、`pyproject.toml` 与发布包，而不是只改根目录的 `LICENSE`。
