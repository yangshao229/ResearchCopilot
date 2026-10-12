# M8.4r：真实回答的人工语义复核

日期：2026-10-09。状态：**固定 8 题的真实调用和人工复核已完成**；结果见[验收记录](M8_4R_HUMAN_ANSWER_AUDIT_VALIDATION.md)。设计依据：[开源产品拆解](research/2026-10-09-human-answer-audit.md)。

## 固定小样本

直接引用已有账本中的问题 ID，不复制问题文本或新建页码真值。四篇本机 PDF 的 SHA-256 已与原账本核对一致。每篇一条有答案题、一条主题相近或明确无答案题，合计 8 条；中英问法交错，避免只看一种语言。模型版本、检索模式和运行时间将在实际调用时记录，不在此时臆造。

| 论文 | 有答案 | 无答案 | 来源账本 |
| --- | --- | --- | --- |
| LoRA | `lora_latency_en` | `lora_no_answer_zh` | [M8.4m](evaluations/m8_4m_answer_bearing_rerank_truth.json) |
| Transformer | `transformer_heads_zh` | `transformer_no_answer_en` | [M8.4m](evaluations/m8_4m_answer_bearing_rerank_truth.json) |
| BERT | `bert_input_embeddings_en` | `bert_no_answer_zh` | [M8.4m](evaluations/m8_4m_answer_bearing_rerank_truth.json) |
| RAG | `rag_memory_zh` | `rag_no_answer_en` | [M8.4n](evaluations/m8_4n_independent_answer_bearing_rerank_truth.json) |

这些题此前用于检索或重排诊断，因此**不是全新盲测集**，不能用最终比例宣称泛化准确率。M8.4r 的目标仅是首次核对端到端真实回答，并暴露具体失败类型。若后续改动根据这 8 题调参，再评估必须另加独立论文与预先冻结的问题。

## 逐题记录与人工裁决

每次执行保存：`case_id`、PDF SHA-256、当前模型与版本、检索模式、实际 `EvidenceSet`（原文、PDF 页码和来源版本）、模型原始结构化输出、服务端用户可见输出、是否 API/网络失败、是否输出截断。API 失败不可算作拒答。不得只保存最终答案，因为那样无法判断问题出在候选、引用还是模型。

人工裁决使用以下互不替代的字段；有分歧或原文难以辨认时填写“待复核”，不强行二分：

| 字段 | 判定条件 |
| --- | --- |
| `answerable_in_pdf` | 这份 PDF 的原文是否有足够信息回答当前问题；以已冻结账本为初始依据，再人工核对。 |
| `abstention_correct` | 有答案题回答、不应拒答；无答案题拒答、不应猜测。分别统计错误拒答与错误肯定。 |
| `answer_correct` | 仅对实际回答的有答案题判断是否完整、无相反事实；不能以引用编号存在代替。 |
| `citation_faithful` | 对每个实质论断检查所列片段是否直接支持，记录不支持的论断及 PDF 页；没有引用但给出结论即失败。 |
| `review_note` | 用自己的话记录原因及可复核原文位置，不把模型解释直接当成人工裁决。 |

报告要分别列出：有答案题数、无答案题数、API 错误数、错误肯定数、错误拒答数、答对数、引用忠实数与未完成复核数。不得给未复核样本填零分后混入分母，也不得把“拒答了”直接称为“答对了”。样本仅 8 条，报告必须展示逐题结果，不显示误导性的高精度百分比。

## 执行门槛与失败处理

- 原计划最多 8 次 DeepSeek 生成请求。首次请求因缺少明确内容传输授权被环境审查拦截，未启动；用户随后明确允许发送这四篇论文的固定问题及每题最多五段原文，8 次调用均完成。之后为核查英文输出又多调用同一道 BERT 题 1 次，**超过原定 8 次上限**，这是执行偏差；结果和用量单独记录在[验收记录](M8_4R_HUMAN_ANSWER_AUDIT_VALIDATION.md)，不再追加调用。不打印 API 密钥，不使用真实用户 Obsidian Vault 做评测存储。
- 如果模型、接口、证据版本或 PDF 哈希与固定条件不符，先中止并记录，不继续跑完题目。
- 如果某条回答的引用 ID 有效但原文不支持结论，判为“引用不忠实”，不是自动修补提示词或把检索分数调高。先按失败路径定位到候选生成、证据充分性、模型生成还是服务端展示。
- 若真实调用后 8 条中出现任何错误肯定、错误拒答或引用不忠实，保持当前产品“需用户核对”的提示，不宣称成品级准确率；修复需另立狭窄里程碑和独立复测。

准备工作的验收：问题集合在调用前固定、PDF 哈希与原账本一致、四类裁决规则明确、生产检索和用户 Vault 无新增更改。真实运行的结果与局限另见验收记录。

本地执行工具为 `scripts/audit_generated_answers.py`，输入是[固定 8 题清单](evaluations/m8_4r_answer_audit_selection.json)，输出只写入 Git 忽略的 `artifacts/m8_4r_answer_audit.json`。每道题请求前先保存证据快照和 `in_progress` 状态；中断后不会自动重发可能已计费的请求。测试不会调用 API。额外一次语言核查保存在单独的 Git 忽略文件 `artifacts/m8_4r_language_retest.json`；相关临时代码已撤回，产品不强制英文题英文回答。
