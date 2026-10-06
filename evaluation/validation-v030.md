# 0.3.0 验收记录

日期：2026-10-06。本地环境：Windows、Node.js v24.18.0。本版增加来源获取与研究产出接口，决策记录仍使用 schema 2，decision_contract_version 升为 2。工作区已有改动先冻结，再在独立副本完成核查与修补。

## 软件与发布检查

```text
node evaluation/run-tests.mjs
node evaluation/check-skill.mjs skills/ai-research-mentor
node evaluation/check-examples.mjs
node evaluation/package-skill.mjs
node evaluation/check-package.mjs
```

实际回归共 **185 项：184 通过、1 跳过、0 失败**。跳过的是文件符号链接回执用例：本机 Windows 未授予创建文件符号链接的权限，不能将跳过写成该路径已测通过。各组为科研审计 96、来源协议 33、研究产出 20、Darwin 24、打包 9、来源到产出集成 3。协议与行为测试使用注入响应和合成记录，不访问外网。

入口检查通过：SKILL.md 88 行、36 个本地引用。三个明确标为 synthetic 的经验、理论、测量示例均合法，当前状态分别为 GO、GO、HOLD；这些状态不是科学推荐。notes/dossier Schema 用于编辑辅助，不替代动态引用、真实阅读或决策门控。

发布包由仓库构建器生成，23 个运行资源、358877 字节，SHA-256：`864e0dea0f834dc720c6f37b941a2b399d92cec92756cdb9fbcc4f8ae016220f`。检查器核对完整资源集合与逐文件字节。本机没有 Python，未运行 skill-creator 的 quick_validate.py；本地检查器不是官方验证器或通用 YAML/JSON Schema 实现。

源码提交 `a9647a9` 在 Ubuntu 的 Node.js 18、20、22、24 四个 CI 作业均已实际完成并通过，见 [本版 GitHub Actions 记录](https://github.com/H66e/academic-scientific-skill-for-AI/actions/runs/37427631869)。作业执行完整回归、入口引用、合成示例和发布包字节核对；这与上述 Windows 本地结果分别记录，未复用 v0.2.0 的旧 CI 结果。

## 本版关键回归

- 独立 pilot 不能批准完整验证；最新独立 HOLD、pilot 或过期记录阻挡较早完整批准。
- 约束 KILL 需要确认约束与实际失败的必要依赖关联，无关偏好或 blocked 标签不能淘汰。
- 完整验证读取受限目录内的实际 JSON 回执，核对字节哈希及评审全部字段；自填 verified 无效。
- 旧契约评审不授权当前决定；迁移原样归档，且不会因移除最新旧评审而恢复更早 GO 或独立批准。
- 无关畸形记录不会掩盖仍可检查的候选引用错误；无效 dossier 仍拒绝排序。
- 来源超时、字节超限、限流、空结果和完整响应的格式错误分别记录；下载不自动创建实读证据。
- DOI/arXiv/OpenReview 身份关联归并 BibTeX；冲突不静默合并，未知作者和年份不补造。
- 卡片和 stdin 草稿只整理真实输入；即使笔记写 GO，也不制造候选、论文、证据或评审。

Darwin 工具、测试和默认可改范围保持原样。本轮工具与契约变更属于已授权的接口维护，不通过放宽 evolution_guard 的保护文件清单获取 KEEP，也不宣称有限回归证明科研效果提高。

## 实际公共来源调用

[本版来源检查](real-world/v030-source-checks.json)保留真实日期、请求、HTTP 状态、响应字节哈希及边界。不是自动测试的 fixture。

- Crossref 实际执行 GQA 题名查询，两页、每页两条，cursor 确实改变，按提供方 score 降序取得四个不同 DOI；页数预算用尽时保留 partial，不声称检索完备。返回中包含 component，命中不能直接当论文数量。
- 实际获取 arXiv `2305.13245v1` HTML：HTTP 200，159510 字节，169 个提取块，其中 141 个有锚点。工具输出仍为 needs_host_review、reading_scope=not_assigned，提取块不等于全文阅读。
- 2026-10-05 的旧接口联网 smoke 保留在 v030-live-smoke.json；日期和当时版本保持不变，不冒充本轮最终版本的重新执行。

独立新上下文执行了三个[前向研究请求](real-world/v030-forward/README.md)，未读取作者讨论、tests 或预期答案。实际交付提案与近邻比较、相关工作及 BibTeX、理论下一步，并生成轻量卡片。记录 8 项逻辑来源请求，来源脚本实际获取 553601 字节；宿主 web 不暴露传输总量，因此未认证全程 8 MiB 上限。

固定公共历史论文上的构造请求不能证明真实选题成功率、全领域近邻召回、专家认可或长期改进。PDF/OCR、决定性图表与公式仍需宿主实际提取和页面核验；无可用能力时明确保留缺口。
