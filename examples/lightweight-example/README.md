# Lightweight notes example

**SYNTHETIC EXAMPLE — NOT A REAL SCIENTIFIC CLAIM**

本示例只有问题与待核验笔记，没有真实论文、检索、评审或实验。可以先输出 Markdown 卡片，再按需生成合法但未评审的项目草稿。在仓库根目录执行：

```text
node skills/ai-research-mentor/scripts/research_outputs.mjs card examples/lightweight-example/notes.json
node skills/ai-research-mentor/scripts/research_outputs.mjs draft examples/lightweight-example/notes.json --name example-question
```

两个命令都只写标准输出。草稿保留原始笔记和显式事实，不制造 papers、searches、evidence、ideas 或 reviews；后续需要宿主根据实际执行逐项填写。

编辑器可关联 `skills/ai-research-mentor/schemas/notes.schema.json`；持续记录可关联 `dossier.schema.json`。Schema 是编辑辅助，决策门控仍由研究证据、宿主复核与审计工具负责。
