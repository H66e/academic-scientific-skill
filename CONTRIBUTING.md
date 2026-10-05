# Contributing

先说明可复现的问题、研究任务和预期行为，再提交范围明确的修改。用合成材料复现时明确标记；用户论文、项目记录和未发表结果不得作为默认公开测试资料。

在仓库根目录运行：

```text
node evaluation/run-tests.mjs
node evaluation/check-skill.mjs skills/ai-research-mentor
node evaluation/check-examples.mjs
node evaluation/package-skill.mjs
node evaluation/check-package.mjs
```

测试入口发现 skill 与 evaluation 下的所有 `.test.mjs`，包含科研审计、自优化验收与发布包完整性。ZIP 由固定文件顺序与固定时间戳生成，包含 skill 目录中的完整文件集合；更新 skill 资源后必须同步发布包。打包工具只覆盖本仓库指定的 `dist/ai-research-mentor.zip`，拒绝符号链接和不安全的归档路径。

修改 schema、评审指纹、证据关联或决策门控时，同步更新 [data-contract.md](skills/ai-research-mentor/references/data-contract.md)、迁移行为和回归测试。保留旧记录与历史判断，不把旧评审包装成新合同下的有效评审。

更新 `VERSION` 与 `CHANGELOG.md`，列出实际验证和剩余限制。CI 配置检查 Node.js 18 / 20 / 22 / 24；配置存在不代表这些环境已经执行通过。

自优化候选只能修改 [self-improvement.md](skills/ai-research-mentor/references/self-improvement.md) 允许的范围。接口、测试和验收规则变更应作为单独维护任务，不由待验候选自行放宽规则。

仓库目前尚未选择 `LICENSE`，许可证类型由项目所有者确定。
