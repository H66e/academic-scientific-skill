# 设计依据与维护

仅在审查或修改本 skill 时读取。创建于 2026-10-05，基于用户提供 research-topic-agent-v1.zip 的评估及公开项目的静态阅读。这里是设计来源说明，不是这些项目效果的背书。本 skill 的文字与辅助程序独立编写；没有引入外部仓库代码、安装器或论文语料。

## 保留与改造

保留原版的最近工作、反方证据、假设与低成本验证原则。改为单入口按需加载；取消固定候选数量、Top3 与两周实验；用可定位证据和候选级查新支撑判断；资源作为前置条件；支持理论、测量、数据集和复现贡献；加入输入版本绑定、失败分类和条件化历史。

借鉴的具体机制：

| 来源 | 使用的设计启发 | 未照搬的部分 |
|---|---|---|
| [ResearchStudio：quality_contract.py](https://github.com/microsoft/ResearchStudio/blob/main/ResearchStudio-Idea/skills/idea_spark/scripts/quality_contract.py) | 评审必须对应当前输入；变化后重开检查 | 完整调度器与高调用量流程 |
| [ResearchStudio：scoop_check](https://github.com/microsoft/ResearchStudio/blob/main/ResearchStudio-Idea/skills/scoop_check/SKILL.md) | 最近工作差异需要可核验比较 | 空检索=最高新颖性、按重合轴计数打分 |
| [Academic-Research-Agent-Skill](https://github.com/ngtiendong/Academic-Research-Agent-Skill/blob/main/references/reality_gate.md) | 检查前置能力、指标和干预；最便宜的决定性测试 | 大量证书和统一审批流程 |
| [claude-scholar：research-contract](https://github.com/Galaxy-Dawn/claude-scholar/blob/codex/skills/research-ideation/references/research-contract.md) | 问题—证据—允许主张强度 | 整套写作工具与固定连接器依赖 |
| [ChineseResearchLaTeX：research-idea](https://github.com/huangwb8/ChineseResearchLaTeX/blob/main/skills/research-idea/SKILL.md) | 每个保留候选单独查新；零合格候选；证据不足不升级主张 | 固定多轮多人审查与配套内核 |
| [Research Opportunity Graph](https://github.com/DajunG-77/research-opportunity-graph-skill/blob/main/SKILL.md) | 已知结果—局限/矛盾—缺失知识—可检验机会 | 将临时推理图当作持久知识系统 |
| [NoviScl/AI-Researcher](https://github.com/NoviScl/AI-Researcher/blob/main/ai_researcher/src/lit_review.py) | 方向检索与候选核查分离，保留查询轨迹 | 摘要二元等价判断、以模型偏好估计接收 |
| [PaperQA](https://github.com/Future-House/paper-qa/blob/main/src/paperqa/agents/tools.py) | 找论文、收集证据和回答分开 | 默认获得完整全球语料的假设 |
| [AstaBench：PaperFindingBench](https://github.com/allenai/asta-bench/blob/main/astabench/evals/paper_finder/README.md) | 用具体查找任务验收检索行为 | 把能力分数当作选题价值或完备性证明 |
| [AutoSci：research_wiki.py](https://github.com/skyllwt/AutoSci/blob/main/tools/research_wiki.py) | 保存失败原因和适用条件，后续复用 | 永久 banlist 和新颖性加权的自动淘汰 |
| [autoresearch：program.md](https://github.com/karpathy/autoresearch/blob/master/program.md) | 固定比较协议、日志关联版本、失败类别区分 | 单指标优化代替科学价值判断 |

这些来源的部分代码为 MIT 或 Apache-2.0，部分早期参考资料有其他许可；若未来实际复制文本、代码或数据，需要逐项检查当时的适用许可。本版本不依赖这些仓库的运行环境。

## 验收范围

运行 `node --test tests/research_audit.test.mjs`。检查权重确实生效、负惩罚拒绝、KILL 不被高分覆盖、未知保持 HOLD、关键近邻只读摘要不能 GO、过期评审被拒绝、结果反馈导致复核、路径不能逃出指定项目根目录。测试数据是虚构的，只用于代码行为。

还需要独立上下文前向测试：提供现实用户请求与原始材料，不透露预期答案；检查它是否忠实区分读取范围、零候选、前置条件和结果类别。结构校验和离线模拟不能证明真实文献检索质量、全方向科研有效性或投稿成功率。未来升级应基于实际使用中的失败，避免不断增加普遍硬规则。
