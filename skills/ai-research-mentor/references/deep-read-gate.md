# 近邻深读门

用于“这个方向新不新、值不值得做、要不要投入”这类高成本主张。规则不是“每次对话先读论文”，而是：**高成本主张必须绑定与其直接相关的近邻深读证据；没有就降级为暂定判断，并给出翻转条件。** 聊天中不硬阻断，报告定稿时硬检查。

## 1. 主张级证据等级

每个新颖性/缺口/机制等价/投入建议主张单独定级，不用“已读论文数”代替：

| 等级 | 条件 | 允许的表达 |
| --- | --- | --- |
| A | 覆盖主张所需范围的近邻深读（section/full_text）+ 定位 + 翻转条件 | 正式判断；仍限定“在已核验近邻范围内” |
| B | 至少 1 篇相关章节深读，但仍有未覆盖近邻/条件 | 判断 + 剩余风险 |
| C | 仅摘要/未读/无权限 | 只写“暂定判断 + 翻转条件 + 最小核验动作”，不得写成正式结论 |

A 级措辞只能是“在这 N 篇近邻中未发现等价机制”，不能写“该方向是新的”。

## 2. 致命问题驱动的深读

每篇关键近邻在阅读前先写至少 2 个“如果答案是 Y，当前主张就不成立”的问题；问题、答案与定位写在报告附录 `nearest-set-json` v2 的 `kill_questions` 数组里，**不是 Markdown 表**：

```json
"kill_questions": [
  {"q": "它是否也按成本选择空间动作？", "answer": "是", "locator": "§3.2 / Table 2"},
  {"q": "它的动作集合是否包含收缩/扩张？", "answer": "未读到", "locator": "§4"}
]
```

- `q` 非占位，且能直接指向一个会推翻当前主张的结果；每个候选至少 2 个问题。
- `answer` 只能是 `是`/`否`/`未读到`，不能用“大概/可能/已看”代替。
- `locator` 必须是真实定位（`§x.y`、`Table x`、`Fig x`、`p.x`、第 x 节/章/页、`附录 A` 等；不能写 `x` 或“大概在 §3”）；只记录“已读全文”而没有定位和答案，视为未读。答案“未读到”的定位可以写“无”；已读候选的定位还必须与账本阅读记录的定位一致。
- A/B 级主张对应的候选，其 `kill_questions` 里至少 2 个问题必须已回答 `是`/`否` 且定位有效，否则按 `CLAIM_CANDIDATE_KILL_QUESTIONS_UNANSWERED` 处理；已答问题的 locator 还必须与账本 reading locator 同类型、同数字前缀匹配，不能只是格式合法。

## 3. 近邻选择门

深读之前先证明近邻选得对，并把选择过程写进报告附录唯一的 `nearest-set-json` v2：

```json
{
  "schema": "nearest-set-v2",
  "created_at": "YYYY-MM-DD",
  "queries": ["检索式 1", "检索式 2"],
  "candidates": [
    {"id": "P1", "title": "论文标题", "rationale": "为什么最接近；可能漏掉什么",
     "status": "full_text", "reader": "model", "ledger": "ledger:E1", "locator": "§3.2",
     "kill_questions": [
       {"q": "它是否也按成本选择空间动作？", "answer": "是", "locator": "§3.2 / Table 2"},
       {"q": "它的动作集合是否包含收缩/扩张？", "answer": "未读到", "locator": "§4"}
     ]}
  ],
  "uncovered": ["可能漏掉的近邻簇"]
}
```

- 至少两种检索措辞/术语体系（例如 “mask refinement” 与 “inpainting mask expansion”）；记录候选集、排序理由、为什么最接近，以及可能漏掉的近邻簇；不能只挑最容易区分的论文。
- `schema` 固定 `nearest-set-v2`；`created_at` 用 `YYYY-MM-DD`；`queries` 至少 2 条互不相同的非占位检索式，每条至少 4 个有效字符（空白不计）。
- `candidates` 至少 2 条；`id` 必须匹配 `P[1-9][0-9]*` 且唯一；`ledger` 必须是 `ledger:<id>` 且不得重复，并能解析到账本来源或锚点；同一来源的 anchor/source 两种 id 视为同一来源，不能冒充两个候选。全文只能有一份 `nearest-set-json`。
- `status` 只能是 `full_text/section/abstract/unseen`，`reader` 只能是 `model/user`；`full_text` 需要账本中的 full_text 阅读，`section` 至少需要 section/full_text 阅读，否则 `NEAREST_CANDIDATE_STATUS_EXCEEDS_LEDGER_SCOPE`；已读候选必须至少有一个带真实定位的账本阅读，且候选 locator 与之匹配。
- `title/rationale/status/reader/ledger/locator` 必填且非占位；整格 `[...]`、模板示例短语（“检索式 1”“术语/数据库”“为什么最接近”“第二个致命问题”“若答案是 Y”“是/否/未读到”等）和 `x/xx/示例/待填/...` 都算占位。
- `uncovered` 记录可能漏掉的近邻簇；主张等级为 A 时还要求把 `status` 为 `abstract/unseen` 的候选写进 `uncovered`（写 id 或标题）。

## 4. 模型代读优先

有检索/全文工具时，模型先获取开放全文并完成定点问答；只有拿不到的部分交给用户。用户阅读确认必须附：论文身份、版本、scope、章节/定位、问题与答案。`reader: model` 与 `reader: user` 分列，不要把用户确认包装成真实性保证。

## 5. 暂定判断（C 级）与 provisional-json

无深读或只有摘要时，C 级主张不能写成正式结论；报告附录的“暂定判断（C 级）”节要保留人读文字，并包含唯一的 `provisional-json` v1：

```json
{
  "schema": "provisional-v1",
  "claims": [
    {"id": "C1", "tendency": "倾向 P1 与本方向机制等价", "flip": "若 P1 §3.2 给出同一机制，则该倾向不成立",
     "check": {"candidate": "P1", "question": "与 P1.kill_questions[].q 原文一致", "locator": "§3.2"},
     "access": "arXiv / 作者主页 / 补充材料 / 代码 README / 向作者索取"}
  ]
}
```

- C 级主张的机器可读字段只能通过这张表表达；每条 C 级主张恰好一个条目，id 与“主张—证据等级”表一致，`tendency/flip/access` 非占位；C 级主张的“近邻”列至少绑定一个候选，`check.candidate` 必须属于该候选集合；全文只能有一份 `provisional-json`。
- `check.candidate` 必须是 nearest-set 里的候选；若该 C 主张在表中绑定了候选，`check.candidate` 必须是其中之一。`check.question` 必须与对应候选的某个 `kill_questions[].q` 规范化后相同（不接受改写/转述），且该问题在 nearest-set 中的答案必须是“未读到”；已答“是/否”的问题说明证据已到手，应升级为 B 级。`check.locator` 必须与该问题的 locator 一致。
- 正文“当前判断与下一步”里若必须引用 C 级判断，只能用限定形式 `倾向……（见 [C1]）`，且同一块内要出现“倾向”和“见/暂定”；其他正文位置不得出现 C 级编号。

人读文字仍按固定四行写：

```text
暂定判断：……（置信：低；仅基于摘要/未读）
翻转条件：若近邻 P1 的 §3.2 也按成本选择动作，则“新颖”判断不成立。
最小核验动作：读 P1 §3.2 + Table 2，回答“是否按成本选择动作、动作集合是否含收缩/扩张”。
获取路径：arXiv / 作者主页 / 补充材料 / 代码 README / 向作者索取。
```

不能只回“无法判断”。

## 6. 缓存与过期

- 同一论文、同一版本、同一阅读范围可复用；
- 近邻集合带时间戳；超过 180 天时 `check-draft` 给 stale warning 并阻止 `delivery_ready`，降级重查是人工动作；出现新版本/新直接近邻时同样重查；
- 主张范围扩大或新增近邻时重新触发；
- 同一对话不重复索要同一阅读记录。

## 7 与报告检查的关系

`evidence_review` 及以上报告必须包含：

1. 唯一的机器可读近邻集：`nearest-set-json` v2（`schema/created_at/queries/candidates/uncovered`；候选含 `id/title/rationale/status/reader/ledger/locator/kill_questions`）。模板把该节放在文末“附录：机器可读块”；也可以放在正文“近邻选择与深读记录”节，两种布局都要求全文只有一份。
2. “主张—证据等级”表固定六列：`编号 | 主张 | 等级 | 近邻 | 依据 | 翻转条件`。编号 `C#` 唯一；A/B 级的“近邻”填候选 id（逗号/顿号分隔），“依据”必须是该候选绑定的 `ledger:<id>` 且能在账本投影中核验；C 级可写“摘要级/未读”。
3. 唯一 `provisional-json` v1：“暂定判断（C 级）”节只接受与该节 C 级主张编号一一对应的条目；`check.question` 必须是 nearest-set 中对应候选 `kill_questions[].q` 的原文。
4. 正文 `[C#]` 合同：“当前判断与下一步”的每个判断块至少一个 `[C#]`；计划块以“下一步/行动/核验动作/获取路径/成本与停止”开头可豁免，但计划块不能夹带正式判断词；引用块（`>`）和文档标题也参与扫描；C 级编号只能以 `倾向……（见 [C1]）` 的限定形式出现在本节，不能出现在其他正文位置。
5. “参考文献”表 5 列，单元格用反引号标注；阅读范围只能是 `full_text` 或 `section:<真实定位>`；section 声明要与账本阅读定位一致。

关键词启发式只拦少量明显越界措辞（如“新颖/首次提出/研究空白/机制等价/值得投入”），它不是语义核验。`check-draft` 只检查这些结构/绑定；它不能证明你读懂了、引用支持主张或近邻完整。
