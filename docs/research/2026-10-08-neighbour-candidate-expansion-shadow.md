# 同页邻居候选扩展：开源方案拆解

日期与官方资料复核日期：2026-10-08。范围：**离线候选生成实验，不改变产品默认检索、用户可见证据或回答**。

## 用户问题

M8.4n 证明，重排器只能排序候选池里已有的片段。独立 RAG 论文的中文快速解码题虽然召回了正确 PDF 页，却没有把同页下一个、真正含完整答案的片段放进前 30，导致 mMARCO 与 BGE 都失败。需要验证一个更窄的问题：能否只把已召回片段的同页相邻片段加入**内部重排候选**，仍只输出原来的 5 条片段，从而补回答案事实而不扩大用户可见证据预算。

## 参考项目与一手资料

1. [LlamaIndex `SentenceWindowNodeParser` 官方源代码](https://github.com/run-llama/llama_index/blob/main/llama-index-core/llama_index/core/node_parser/text/sentence_window.py)与[官方示例](https://docs.llamaindex.ai/en/v0.10.34/examples/node_postprocessor/MetadataReplacementDemo/)：小节点用于定位，节点元数据保留相邻句窗口；MIT。它默认在送入模型前用窗口替换命中节点，本轮只借鉴“命中节点与相邻节点有显式关系”，不直接扩大最终文本。
2. [LangChain `ParentDocumentRetriever` 官方源代码](https://github.com/langchain-ai/langchain/blob/master/libs/langchain/langchain_classic/retrievers/parent_document_retriever.py)：用小块检索、再映射到较大父块，以平衡定位和上下文；MIT。本轮不引入父文档存储，只把相邻小块作为第二阶段候选。
3. [Haystack `AutoMergingRetriever` 官方文档](https://docs.haystack.deepset.ai/docs/automergingretriever)与[官方源代码](https://github.com/deepset-ai/haystack/blob/main/haystack/components/retrievers/auto_merging_retriever.py)：当多个叶块支持同一父块时返回父块；Apache-2.0。本轮拒绝自动合并整段，只保留同页、相邻、可核对的候选关系。
4. [Sentence Transformers 官方 Retrieve & Re-Rank 文档](https://www.sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html)：先取有限候选，再由 Cross Encoder 排序并只展示较小 Top-k；Apache-2.0。本轮保持“内部候选数”和“用户可见 Top-5”两个预算分离。

以上项目只用于设计对照，不复制代码、不新增依赖。现有 PDF 解析、E5 与两个本机 Cross Encoder 版本均保持不变。

## 各项目的成熟做法

| 项目 | 成熟做法 | 适用价值 | 本轮限制 |
| --- | --- | --- | --- |
| LlamaIndex | 小节点检索，保留相邻窗口 | 处理答案跨越切分边界 | 不直接把窗口送入生成 |
| LangChain | 子块定位，父块恢复上下文 | 分开检索粒度与上下文粒度 | 不建第二套父块索引 |
| Haystack | 命中多个子块后条件式合并父块 | 避免碎片化上下文 | 不以命中比例自动替换证据 |
| Sentence Transformers | 大候选池，Cross Encoder 排序，小 Top-k 输出 | 分离召回与展示预算 | 分数不用于拒答 |

## 对 ResearchCopilot 的取舍

- 直接借鉴：第一阶段候选与第二阶段输出预算分离；只对有限候选运行 Cross Encoder；保留可追溯的页码与片段索引。
- 按项目调整：从原混合检索 Top-30 出发，只追加每个命中片段在**同一 PDF 页**的前／后相邻块，去重后重排，最终仍取 5 条原始片段。邻居本身保持独立证据项，不拼接文本。
- 明确拒绝：全页父块、跨页邻居、整页窗口、查询翻译、生成式查询扩展、模型分数拒答，以及为了命中真值而把人工短语用于运行时选候选。
- 对照顺序：原候选、只加前一个、只加后一个、前后各一个。冻结方向后必须在独立 RAG 账本与旧三论文困难集同时复核，不能只看唯一失败题。

## 数据、隐私与失败处理

- 只读固定本地 PDF、已有切分结果、E5 与本机固定模型快照；不联网下载模型、不调用 DeepSeek。
- 相邻关系以 `(source_page, chunk_index)` 查找；没有唯一匹配、跨页、重复文本或缺字段时不追加，不能猜测。
- 新候选只进入离线重排；用户可见证据仍是 5 条，且每条保持原文、PDF 页码和片段索引。
- PDF 哈希、问题账本、支持事实账本或模型快照不匹配时失败关闭。
- 负例即使得到高分也仍判为“拒答未验证”；候选扩展不得写阅读记录、译文缓存或 Vault。

## 架构影响

在 `context_window_evaluation.py` 增加一个纯函数，根据现有候选和完整切分列表返回去重的同页邻居候选；在离线脚本中比较不同方向，再复用 `rerank_candidates` 和既有同页事实覆盖函数。生产 `hybrid_search_chunks`、`EvidenceSet`、API、网页和快照契约均不改。若实验失败，只保留评测与失败记录。

## 兼容性矩阵

| 组合 | 预期 |
| --- | --- |
| 当前论文／跨论文 | 每篇独立扩展；绝不跨论文 |
| 原文／译文 | 仅原 PDF 抽取块；译文不参与 |
| 英文／中文问题 | 相同规则，分别报告 |
| 不同会话 | 离线评测无会话状态 |
| 本地／云端 | 全程本地；DeepSeek 不参与 |
| macOS／Windows | 纯 Python 逻辑应一致；本轮仅在 Mac 实测，Windows 未实机验证 |
| 有答案／无答案 | 正例统计同页事实覆盖；负例只诊断分数，不宣称拒答 |

## 实现顺序与验收标准

1. 冻结独立 RAG 失败题和旧三论文困难集的同页支持事实，不修改问题或 PDF。
2. 单元测试证明只追加同页相邻块、稳定去重、顺序确定，缺失／跨页邻居不会混入。
3. 比较四种内部候选池；最终重排仍只输出 5 条，不拼接窗口文本。
4. 独立 RAG 账本必须报告候选事实覆盖、重排 Top-5 覆盖、候选数和延迟；旧困难集必须报告改善与退化。
5. 若收益只出现在一题、旧集退化、负例风险增加或候选数／延迟明显膨胀，保持影子状态。
6. 完整 `pytest`、前端生产构建与真实 PDF 哈希检查通过。

## 暂不实现的内容

不改变生产切分、索引、检索、证据快照或生成；不做整页父块、跨页窗口、自动查询改写、OCR、整篇翻译、逐块对齐、模型阈值拒答，也不把字符串命中当作最终答案正确性。
