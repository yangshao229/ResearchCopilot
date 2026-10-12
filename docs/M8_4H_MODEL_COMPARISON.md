# M8.4h：两种多语重排器的离线对照

日期：2026-10-07。状态：**影子评测，不接入产品**。

## 为什么比较

M8.4g 的三组中英同义问题暴露了跨语排序不稳，但不能仅凭三题选择新模型。本轮先冻结[另一组 6 个概念、12 条中英文同义问题](evaluations/m8_4h_model_comparison_truth.json)，然后使用相同的 PDF、相同的前 30 个混合检索候选，比较已有的 `mmarco-mMiniLMv2-L12-H384-v1` 和候选 `bge-reranker-v2-m3`。这一组与 M8.4g **问题不同，但仍来自同三篇论文**，所以是问题级对照，不是独立论文测试集。

## 开源产品／模型拆解与取舍

- [Sentence Transformers 的 Retrieve & Re-rank 方案](https://www.sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html)把快速召回与精细重排分开；本项目继续沿用这一结构，没有让 Cross Encoder 扫描整篇 PDF。
- [原模型官方卡](https://huggingface.co/cross-encoder/mmarco-mMiniLMv2-L12-H384-v1)说明其用于对候选段落排序；[BAAI 候选模型官方卡](https://huggingface.co/BAAI/bge-reranker-v2-m3)和[官方使用文档](https://bge-model.com/bge/bge_reranker_v2.html)将 `bge-reranker-v2-m3`定位为多语重排器，支持用查询－段落对评分。两者不能由模型卡的通用指标直接推断在本项目论文场景中的效果。
- 候选使用 Apache-2.0 权重与 `safetensors`，固定修订 `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`；约 2.1 GB 权重仅保存在 Git 忽略的本机模型缓存，不进入源码仓库，也不要求 Windows 同步。

沿用现有 `scripts/evaluate_reranker.py`，没有新增运行依赖、网页入口或生产代码。脚本强制离线，校验三篇 PDF 的 SHA-256；模型只给相同的 30 个候选重新排序。没有调用 DeepSeek、上传 PDF 或写真实 Obsidian Vault。

## 结果

指标是“正确 PDF 文件页是否出现在前 5 个**片段**中”，不是答案准确率、引文充分性或拒答率。

| 冻结的 12 条问题 | 原混合检索 | mMARCO 重排器 | BGE 候选 |
| --- | ---: | ---: | ---: |
| 全部正例 | 8/12 | 11/12 | 12/12 |
| 英文 6 条 | 5/6 | 6/6 | 6/6 |
| 中文 6 条 | 3/6 | 5/6 | 6/6 |

BGE 在这组问题补上了“为什么注意力点积除以键维度平方根”的中文题，正确页由原模型名次 7 升到 1。然而在**先前冻结、没有用于选择候选的困难集 M8.4g**，正确页前五：原模型为 `4/6`，BGE 只有 `2/6`；其中 LoRA 低秩矩阵的英／中两题和 Transformer 位置编码的英／中两题，BGE 都未进入前五。BGE 的页级去重影子结果在该困难集为 `4/6`，但中文仍仅 `1/3`，不能称为跨语问题已解决。

同一台 Mac、CPU、同一批 30 个候选上，12 题的重排计时中位数：原模型约 `0.63s/题`，BGE 约 `4.93s/题`。这是一次机器本地测量，不是通用性能基准。困难集三道中文无答案题，BGE 仍都能给某段原文评分；最高分分别约 `0.14`、`0.08`、`0.41`。不同模型的分数尺度不能互比，且这里的分数并非可直接用于安全拒答的概率。

## 决策与边界

**保留现有产品行为；两个重排器都不接入默认问答。** 候选在一组问题上多命中 1 题，却在原困难集少命中 2 题，同时显著增加本机等待时间，无法证明整体体验更好。12 条正例没有无答案题；困难集虽有负例，但当前评测器只测排序，不测生成回答是否正确拒答。

下一轮不继续凭三篇熟悉的论文调参数。先加入来源独立、可合法使用的新论文，并冻结中文／英文正例与无答案题；分别衡量候选召回、页级证据排序、引文充分性与拒答，再决定是否引入更小的模型或针对论文语料改进切分。首篇独立论文的跟进结果见 [M8.4i 验收](M8_4I_INDEPENDENT_PAPER_VALIDATION.md)。真实 Safari 与用户 Vault 的人工阅读闭环仍需单独验收。

复现：`.venv/bin/python scripts/evaluate_reranker.py --truth docs/evaluations/m8_4h_model_comparison_truth.json --model-path <本地模型快照目录>`；原模型可省略 `--model-path`。命令中的模型目录需先在本机显式准备，不会在评测时联网下载。
