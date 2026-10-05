# Offline forward-testing materials

These cases are synthetic and are not actual papers, searches or scientific results. Use them only in a separate evaluation workspace. No browsing, training or external writes are authorized in these cases.

## Case A — 用户请求

“我做大模型 agent，想提出一种按任务难度动态决定是否调用检索的门控机制。下面是我现有的材料，都是摘要。帮我评估这个选题是否值得推进，推荐下一步。先不要训练，我还没确定算力预算。”

资料：

- 合成论文 A，2025，摘要：“A policy selects whether to retrieve based on task uncertainty. We compare against always-retrieve and never-retrieve policies on question-answering tasks.” 无全文、无稳定论文 ID。
- 合成论文 B，2026，摘要：“We route agent tasks to retrieval or internal reasoning using a learned difficulty estimator. The abstract reports an accuracy-cost tradeoff.” 无全文、无可核验统计数据。
- 用户的一次搜索记录：“Google 搜索 dynamic retrieval gate agent，前十条没有直接匹配标题。” 没有实际检索时间，没有覆盖说明。

## Case B — 用户请求

“继续评估我的视觉模型选题。第一次 pilot 启动报错，日志是 `ModuleNotFoundError: vision_backend`。同事认为这证明假设失败了，要永久淘汰这个方向。你帮我更新判断，并建议下一步。这次只分析记录，不安装依赖、不重跑。”

资料：

- 原假设：“在固定训练预算下，改变采样策略能够改善遮挡条件下的识别性能。”
- 目前只有环境启动日志，训练、评价和对照都没有运行。
- 数据集授权还未确认。
- 历史记载：“2026-09 因大规模计算预算不足暂缓；若有小规模可判别实验，可以重评。”

## Case C — 用户请求

“我想做强化学习理论，研究在改变策略类别限制后一个现有误差界能否继续成立。我有论文相关定理的完整段落和假设列表，但还没有候选命题的证明或反例。请帮我规划验证步骤，别给我训练计划。手头没有 GPU。”

资料：

- 合成原定理：“在有限状态、策略类别满足条件 C、奖励有界时，上界 B 成立。”
- 用户要探索移除条件 C，而保留其他假设。
- 目前不能确认已有放宽条件 C 的工作；未完成针对等价定理表述的检索。
- 用户希望先构造最小状态系统中的反例，再决定是否写完整证明。
