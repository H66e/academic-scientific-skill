# 0.4.0 发布验收记录

日期：2026-10-26。本地环境：Windows、CPython 3.14.5、无 Node。本版是 Python-only 重建后的第一个发布，也是 [ADR 0008](../docs/decisions/0008-release-identity-and-package-artifacts.md) 与 [ADR 0009](../docs/decisions/0009-acquisition-direction-and-payload-admission.md) 的落地版本。以下均为本机实际执行结果；CI 矩阵在推送后独立执行，其状态以 GitHub Actions 的实际记录为准。

## 发布身份

- `VERSION`、`pyproject.toml`、`research_mentor.__version__`、README 当前版本行与 CHANGELOG 小节均为 `0.4.0`，由 `evaluation/tests/test_version_consistency.py` 强制。
- `v0.3.0` 回填到最后的 Node 实现提交（0.3.0 归档 358,877 字节、SHA-256 `864e0dea…`），`v0.4.0` 指向本记录对应的发布提交。两个 tag 是不同实现、不同包。
- 发布包不再提交：`dist/` 被忽略；`package` 从源码确定性构建，`check-package` 重新构建并比较。

## 本地检查

| 检查 | 实际结果 | 边界 |
| --- | --- | --- |
| `python -B evaluation/run-python-tests.py` | **310 tests，OK，skipped=1**（skip 是既有文件符号链接权限用例） | 合成语料与注入协议；不是科研效果证明 |
| `check-skill` | valid；44 条技能内链接、111 行入口 | 结构/链接检查 |
| `check-examples` | valid；GO/GO/HOLD 三个合成示例 | 示例为虚构数据 |
| `check-python-only` | valid；126 个文件 | 只排除语言/清单，不证明 stdlib-only 之外的事 |
| `package` | 50 个文件、670,138 字节、SHA-256 `29891da1…` | 发布包构建产物，不入 Git |
| `check-package`（有本地包） | valid，`deterministic: true`：两次独立构建逐字节相同 | 确定性不等于科学正确性 |
| `check-package`（无本地包） | valid：仅验证一次内存构建 | 用于 fresh clone |

CI：同一提交在 GitHub Actions 的 6 个矩阵作业（Ubuntu/Windows × Python 3.10/3.12/3.14）全部成功；构建与校验步骤按上方本地命令执行，发布包另存为运行产物（[run 记录](https://github.com/H66e/academic-scientific-skill/actions/runs/40330556524)）。配置存在或一次成功都不代表其他环境也被覆盖。

## P0 修复的实测证据

- **隐私分类**：独立来源工具的 `verify` 与 `fulltext` 在出网前调用 `check_outbound`，默认 `public`；`--sensitivity private` 在 0 次 DNS/HTTP 请求前阻断。同时修复了 `check_outbound` 把 `https://` 中 `s:/` 当 Windows 盘符、从而误拒所有公网 URL 的缺陷；`core.fetch` 的公共 URL 分支现在可实际获取并通过 `verify-artifacts`（见 `evaluation/tests/test_privacy_policy.py`）。
- **账本 payload 准入**：17 类已注册事件全部校验必需字段；0.3.0 的 producer 产出的正常账本仍可 verify；手写或极旧的最小 payload 会被拒并需人工检查，工具不改写历史（见 `evaluation/tests/test_ledger_payloads.py`）。
- **CLI 严格化**：主 CLI 与工具 CLI 均拒绝重复长选项与缩写；`--project A --project B`、`--proj`、重复 `--format`/`--sensitivity` 均以 argparse 错误退出（见 `evaluation/tests/test_cli_strict.py`）。
- **失败收口**：合法哈希链但消费端意外出错时，`json` 与 `markdown` 都返回标准 envelope 且非零退出，不再打印 traceback（见 `evaluation/tests/test_cli_strict.py`）。
- **回执重放**：`verify-artifacts` 对 `source.fetch` 重放 provider/url/`http_status`/字节数与哈希/content-type，以及从保留字节重新派生的 IR 字段（`ir_sha256`/`ir_path`/`text_sha256`/`block_count`/`extractor`/`normalization`/`needs_host_extraction`/`limitations`）与 `needs_host_review`；`public_url` 的最终 host 必须等于请求 host（传输只允许同 host redirect）。`retrieved_at` 只校验时区感知 ISO 格式，因为不存在可对照的外部时刻，不声称重放具体时间。伪造上述字段并重算事件哈希与锚点后仍报 invalid；`search.result` 的既有重放是有效对照（见 `evaluation/tests/test_verification_metadata.py`）。

## 未覆盖范围

- 真实选题、查新、gap 与写作质量仍未测量；本记录只证明软件合同与发布流程。
- PDF/OCR 抽取、实验日志自动解释、ledger↔dossier 无损互转、独立评审身份认证仍不在范围内。
- 出站启发式只拦截明显的路径、凭据、邮箱与常见令牌前缀，不是 DLP；用户仍需实际判断查询是否可外发。
- Codex 安装副本是 0.3.0（Node）运行时拷贝，本版不自动同步；同步是发布后的单独显式动作。
- 本机 Windows/CPython 3.14.5 的结果不能替代 Linux 或 Python 3.10/3.12 的实际执行；矩阵结果以 Actions 记录为准。
- CI 自动阻止 `dist/ai-research-mentor.zip` 被重新跟踪，但不自动核对 tag 与 VERSION 一致；后者仍是发布流程的人工检查项（ADR 0008）。
