# Contributing

先说明可复现的问题、研究任务和预期行为，再提交范围明确的修改。用合成材料复现时明确标记；用户论文、项目记录和未发表结果不得作为默认公开测试资料。

在仓库根目录运行：

```text
python -B evaluation/run-python-tests.py
python -B evaluation/skill_tools.py check-skill
python -B evaluation/skill_tools.py check-examples
python -B evaluation/skill_tools.py check-python-only
python -B evaluation/skill_tools.py package
python -B evaluation/skill_tools.py check-package
```

Python 3.10+ 工具链只使用标准库，源码位于 `skills/ai-research-mentor/runtime/research_mentor/`；CLI 与导入 API 共用该实现。`pip install -e .` 是可选开发安装，不是使用 Skill 的前提。Python 测试包含工具自动回执、账本完整性、文本锚点、默认隐私、过期决定，以及 dossier 投影合法但不恢复 GO 的检查。dossier 审计、来源工具、产出和自优化验收均为原生 Python。既有 dossier 指纹与迁移前冻结的协议观察值比较；ledger 的哈希仍是独立协议，不能混用。

运行、维护、测试、CI 与打包只使用 Python，不保留另一个语言实现或调用桥接。旧脚本与导入接口已退役；将调用改为 Python CLI 或 `research_mentor` API，参见 [ADR 0007](docs/decisions/0007-python-only-toolchain.md)。旧 dossier 数据和既有指纹不因此改写，旧合同记录仍须显式迁移重评。来源工具默认拒绝 private 查询；公共 fixture 和实际公开查询均须明确分类。

Python 新字段的修改应更新 [python-core.md](skills/ai-research-mentor/references/python-core.md)、对应测试和 ADR。CI 的 Python 作业配置 Windows/Linux × 3.10/3.12/3.14；本地实际执行版本及范围见 [Python 核心验收记录](evaluation/validation-python-core.md)，配置存在不代表 CI 已通过。使用 `-B` 防止字节码混入工作树，打包也排除 `__pycache__` 和 `.pyc/.pyo`。

测试入口发现 skill 的 `tests/python/` 与仓库 `evaluation/tests/` 下的 `test_*.py`，包含科研审计、来源协议、研究产出、自优化验收与发布包完整性。来源自动测试注入协议响应，不使用外网；真实联网试用单独保留请求、状态、字节哈希与未读范围，不把 fixture 当召回测试。ZIP 由固定文件顺序与固定时间戳生成，包含 skill 目录中的完整文件集合，以及仓库根 `LICENSE`（打包为 `ai-research-mentor/LICENSE`，由 `python -B evaluation/skill_tools.py check-package` 一并核验）；更新 skill 资源或 `LICENSE` 后必须同步发布包。

修改 schema、评审指纹、证据关联或决策门控时，同步更新 [data-contract.md](skills/ai-research-mentor/references/data-contract.md)、迁移行为和回归测试。保留旧记录与历史判断，不把旧评审包装成新合同下的有效评审。

`schemas/*.schema.json` 用于编辑辅助；动态引用、必要条件、当前契约与收据核验仍由审计工具负责。决策语义变化须同步 decision_contract_version，不以 schema_version 未变为由继续使用旧批准。

发布时更新 `VERSION` 与 `CHANGELOG.md`，列出实际验证和剩余限制。未发布维护改动记入 Unreleased，不自动提升发行版。`VERSION` 是版本真源：`evaluation/tests/test_version_consistency.py` 核对 `pyproject.toml`、`research_mentor.__version__`、`README.md` 的当前版本行与 `CHANGELOG.md` 的对应小节，改漏任一处即失败。`schema_version` 与 `decision_contract_version` 计的是 dossier 契约修订，不是发行版本，不随 `VERSION` 变动；`docs/WORKSPACE_GOVERNANCE.md` 描述的是已发布安装副本，按设计可以落后于本工作树，同样不参与核对。CI 配置为 Ubuntu × Windows × Python 3.10 / 3.12 / 3.14 的矩阵。配置存在不代表这些环境已经执行通过。

自优化候选只能修改 [self-improvement.md](skills/ai-research-mentor/references/self-improvement.md) 允许的范围。接口、测试和验收规则变更应作为单独维护任务，不由待验候选自行放宽规则。

本项目采用 [MIT 许可证](LICENSE)，版权归 `H66e`，选择理由见 [ADR 0002](docs/decisions/0002-license-selection.md)。版权署名与许可证类型由项目所有者决定；更改时必须同步 `README.md`、`pyproject.toml` 与发布包，而不是只改根目录的 `LICENSE`。
