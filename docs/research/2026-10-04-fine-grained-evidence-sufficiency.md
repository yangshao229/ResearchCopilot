# M8.4d 查询—原文细粒度证据充分性：开源产品拆解

检索日期：2026-10-04。阶段：先做离线可复现评测，不改变生产检索、网页或生成链，不复制第三方代码。

## 用户问题

M8.4c 已把两篇真实论文的人工页锚点找全，但句向量最大余弦分数无法把自然正例和自然负例分开：中文位置问题的一个真实正例分数低于中文量子纠缠负例。用户需要的是一个对“查询中的信息需求是否被原文页具体覆盖”更敏感的独立信号，并且必须在未参与门槛选择的问题上验证，而不是继续在同八个问题上调一个更好看的阈值。

本阶段只回答：细粒度查询词元到候选原文词元的覆盖分数，能否作为句向量召回之后的证据充分性关卡；校准集上选出的门槛，能否原样通过新增的真实自然问题。比较答案、自动主题笔记和生产默认路径继续关闭。

## 参考项目与一手资料

| 来源 | 许可证 | 直接观察到的成熟做法 | 本项目取舍 |
| --- | --- | --- | --- |
| [Sentence Transformers：Cross Encoder 用法](https://www.sbert.net/docs/cross_encoder/usage/usage.html)、[训练概览](https://www.sbert.net/docs/cross_encoder/training_overview.html)与[官方仓库](https://github.com/huggingface/sentence-transformers) | Apache-2.0 | Retrieve-and-rerank 将快速召回与较慢的查询—文档成对打分分开；Cross Encoder 常作第二阶段 reranker，分数的范围和激活取决于模型。 | 接受“先召回、再成对判断”的分层，不把句向量 Top-K 当证据；当前没有已缓存且许可已核对的多语 Cross Encoder，因此不联网下载、不假装已有交叉编码器结果。 |
| [BEIR 官方仓库](https://github.com/beir-cellar/beir)、[评测实现](https://github.com/beir-cellar/beir/blob/main/beir/retrieval/evaluation.py)与[论文](https://openreview.net/forum?id=wCu6T5xFjeJ) | Apache-2.0 | 用固定 corpus/query/qrels 评测 lexical、dense、sparse 与 reranking；指标和运行结果独立保存，跨数据集平均值不能替代逐数据集解释。 | 固定 PDF、哈希、问题、页锚点和 split；门槛只在 calibration 上选择，held-out 只验收一次并逐题报告，不用两篇论文冒充通用准确率。 |
| [FlagEmbedding 官方 BGE-M3 文档](https://github.com/FlagOpen/FlagEmbedding/blob/master/docs/source/bge/bge_m3.rst)、[官方仓库](https://github.com/FlagOpen/FlagEmbedding)与[多语 reranker 模型卡](https://huggingface.co/BAAI/bge-reranker-v2-m3) | FlagEmbedding 代码 MIT；`bge-reranker-v2-m3` 模型卡标注 Apache-2.0 | BGE-M3 明确区分 dense、sparse 与逐查询词元取文档词元最大相似度后平均的 multi-vector late interaction；官方推荐 hybrid retrieval 后 rerank。多语 reranker 以查询—文档对直接打分。 | 只借鉴可解释的 late-interaction 公式，在现有本地 E5 隐藏状态上做**实验性**词元覆盖探针；E5 并未按 BGE-M3 的 multi-vector 目标训练，结果只能作为本项目实测，不能引用 BGE 指标或称为 Cross Encoder。 |

共同结论：召回分数、重排分数和“有足够证据回答”不是同一个量。第二阶段信号必须对查询与候选原文成对计算，门槛须绑定具体模型/修订/数据，并在未参与选择的样本上验证。

## 流程拆解

1. 完整保留 M8.4c 的八个问题作为 `calibration`，包括 9 个正例论文组合和 7 个负例论文组合；不删除分数重叠的难例。
2. 新增四个 `held_out` 自然问题：中英文各一个训练硬件/时长正例，以及中英文各一个 ImageNet 图像分类准确率负例。硬件问题的人工页锚点为 Transformer PDF 第 7 页与 BERT PDF 第 13 页；ImageNet 问题在两篇正文均无答案，BERT 参考文献中的 ImageNet 字样不能算证据。
3. 第一阶段仍用 M8.4c 页级融合产生每篇最多三页候选；第二阶段对查询词元与这些页面上的候选块词元做归一化隐藏向量 late interaction：每个有效查询词元取其与原文词元的最大余弦，再对查询词元求平均，得到独立于 pooled sentence cosine 的细粒度覆盖分数。
4. 仅用 `calibration` 的正负组合枚举门槛，优先选择同时保持全部人工页锚点与拒绝全部负例的最低门槛；若不存在，明确记录不可分，不看 held-out 后反调门槛。
5. 用冻结门槛一次性评测 `held_out` 的 4 个正例组合和 4 个负例组合；同时报告人工页锚点、拒答、已知无关页、范围泄漏与逐组合分数。

## 对 ResearchCopilot 的取舍

| 决定 | 原因 |
| --- | --- |
| 复用固定 E5 权重与临时分页缓存，只新增离线细粒度评分器 | 不下载新模型、不新增用户存储，能先判断该信号是否值得继续。 |
| 分数只作用于 M8.4c 已召回的候选论文/页 | 它是证据关卡，不是替换资料库搜索，也不能挽救完全未召回的页面。 |
| calibration 与 held-out 明确写入机器可读账本 | 防止一边查看新问题结果一边调门槛造成数据泄漏。 |
| E5 late interaction 失败也算有效结论 | E5 未为词元级相似度训练；若不能分离，应转向经许可、固定修订的多语 Cross Encoder，而不是硬编码查询或答案。 |
| 不将 ImageNet 字面命中视为答案 | BERT 参考文献出现 ImageNet，但论文未报告图像分类准确率；这是验证“提到词”不等于“提供证据”的困难负例。 |

## 架构影响

- 复用 `real_multi_paper_evaluation.py` 的 PDF 哈希校验、分页、切块、页级融合、逐论文评分与本地 E5 修订。
- 在 `semantic_retriever.py` 增加仅供评测调用的成对细粒度评分能力，或以协议注入假模型做单元测试；生产 `semantic_search_chunks` 的 pooled embedding 行为不变。
- 新账本只增加 `split` 字段和 held-out 问题，不改变 `ReadingRecord`、`KnowledgeArtifact`、论文 UID、翻译缓存或 API schema。
- 新脚本只输出 JSON 报告；不写模型分数进用户数据，不接入前端或问答生成。

## 兼容性矩阵

| 场景 | 预期 |
| --- | --- |
| 当前论文 / 跨论文 | 当前阅读与生产检索不变；离线评测仍逐篇成对打分并检查范围。 |
| 英文 / 中文问题 | 同一多语 E5 修订处理两种语言；分别报告，不用英文结果代表中文。 |
| 原文 / 译文 | 只评分 PDF 抽取原文；不读取或修改译文缓存。 |
| calibration / held-out | 门槛只由 calibration 决定；held-out 结果不得反向修改门槛。 |
| 不同会话 | 不读取会话、阅读进度、历史或人工笔记。 |
| 本地 / 云端 | 模型仅从本地缓存加载；缺失权重时失败，不联网下载，不调用 DeepSeek。 |
| macOS / Windows | 固定模型名、修订、PDF 哈希与算法；CPU 可运行，设备数值差异需保留原始分数。 |

## 数据与隐私边界

只读两篇获准本地研究使用的 PDF 和本地模型缓存。分页文件位于临时目录，评测前后复核 PDF 哈希。不得读取密钥、用户笔记、阅读记录或译文缓存；不得将查询、原文或分数上传网络。来源网页只用于产品拆解，第三方代码不复制进项目。

## 验收标准

- 新账本完整包含原八题 `calibration` 与四题 `held_out`，固定两份 PDF 哈希、页码语义、每篇三页上限和模型修订。
- 单元测试覆盖 late-interaction 聚合、padding/special token 排除、候选页限制、门槛只从 calibration 选择，以及不存在可分门槛时的失败结论。
- 报告校准集与 held-out 的正例页锚点、负例拒答、逐组合分数和门槛；held-out 不参与选择。
- 只有 calibration 与 held-out 同时达到全部人工页锚点和全部负例拒答，才允许下一阶段讨论比较答案；否则生产路径继续关闭。
- 完整 pytest、前端生产构建和真实双论文离线脚本通过；PDF 哈希前后不变，无 DeepSeek、网络模型下载或用户数据副作用。

## 失败场景

- 若 calibration 的正负细粒度分数重叠，直接结论为该信号不足，不评选“最佳折中”上线。
- 若 calibration 可分但 held-out 失败，视为泛化失败；不得用 held-out 重新选门槛。
- 若候选前三页本身漏掉人工锚点，证据关卡不能补救，单独报告召回失败。
- 若本地模型修订缺失、PDF 哈希漂移、词元输出维度不一致或页面无可抽取文本，评测失败关闭。

## 实现顺序

1. 固定带 split 的账本和人工页锚点。
2. 实现可注入、可单测的细粒度查询—原文评分器。
3. calibration 选门槛并冻结，held-out 一次性验收。
4. 运行完整测试、前端构建和真实 PDF 评测，记录失败或通过。

## 暂不实现

不下载或接入新的 Cross Encoder，不调用 LLM 判断相关性，不生成跨论文答案，不写主题笔记，不改变生产 API，不做 OCR、整篇翻译或未评测逐块对齐。若实验性 E5 late interaction 失败，下一步应先取得用户允许并固定一个多语 reranker 的模型许可、修订、体积和离线安装方式，再建立新的独立评测，而不是偷偷联网或放宽拒答标准。
