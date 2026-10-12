# M8.4i：新论文上的独立检索验收

日期：2026-10-08。状态：**新增本机测试论文，未改变产品检索策略**。

## 材料与方法

使用 [arXiv 官方页面](https://arxiv.org/abs/2005.11401)发布的 *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks* v4 PDF。文件保存在 Git 忽略的本地 `data/raw/rag-lewis-2021-v4.pdf`，19 个 PDF 文件页，SHA-256 为 `23e3249e9a1e75418d82efecab0ea8c4d033b89c93742f63208d47ce01f21233`。它此前未参与本项目三篇论文上的模型选择或调参；原 PDF 不进入 Git，也不上传模型服务。

在运行两种重排器前，先根据 PDF 原文第 2、3、4 页锁定[4 组英／中同义正例与 1 组英／中无答案题](evaluations/m8_4i_independent_rag_truth.json)。正例覆盖参数化／非参数化记忆、RAG-Sequence 与 RAG-Token、固定文档编码器、快速解码。负例问 ImageNet 图像分类准确率；该论文不报告这一指标。锚点是从 1 开始的 PDF 文件页码，不是论文印刷页码。

没有引入新产品能力，因此沿用 [M8.4h 的开源重排方案拆解](M8_4H_MODEL_COMPARISON.md)和同一个离线评测器：本地混合检索取前 30 片段，两种模型只对同一批候选排序。评测强制离线，核对 PDF 指纹，不调用 DeepSeek、不生成回答、不写 Vault。

## 结果

| 独立 RAG 论文的 8 条有答案题 | 混合检索 | mMARCO 重排器 | BGE 候选 |
| --- | ---: | ---: | ---: |
| 正确 PDF 页进入前 30 个候选 | 8/8 | — | — |
| 正确 PDF 页进入前 5 个片段 | 7/8 | 8/8 | 8/8 |
| 中文 4 条正确页进入前 5 | 3/4 | 4/4 | 4/4 |

两种重排器都补上“参数化／非参数化记忆”的中文题，但 BGE 在这篇新论文上没有提高 Top-5 覆盖。单次本机 CPU 计时，10 题重排总耗时约 `6.15s`（mMARCO）与 `83.16s`（BGE）；它们不含 PDF 解析、E5 召回或服务启动，不是通用性能数字。两道无答案题仍都得到检索片段和分数，**这不证明模型会安全拒答**；分数也不能跨模型直接比较。

产品端只读检查：`/api/papers` 将新 PDF 识别为 19 页英文论文，资料库现可列出 4 篇 PDF；`/file` 返回完整原 PDF，`/structure` 读到带页码的论文书签目录；对该论文调用原有关键词检索，问题 `RAG-Sequence RAG-Token different document per token` 返回的前两个片段都锚定 PDF 第 3 页。未触发回答、翻译、保存笔记或真实 Vault 写入。新增 PDF 后完整 Python 回归仍为 `201 passed`，网页生产构建通过，只有既有的依赖弃用与大分块提示。

## 决策

独立论文支持“当前候选召回可找到这些明确信息、重排可以补一条中文题”的窄结论，不支持“读论文已经可靠”或“BGE 值得替换”。结合 [M8.4g 困难集](M8_4G_CROSS_LANGUAGE_DIAGNOSTIC.md)的回退与 [M8.4h 对照](M8_4H_MODEL_COMPARISON.md)的延迟，继续保留两种重排器的影子状态；生产仍用现有可核查的关键词／语义／混合检索。下一轮须增加更多不同结构和学科的独立 PDF，并把“页码命中”推进到“片段是否足以支持答案”的人工真值。

复现：`.venv/bin/python scripts/evaluate_reranker.py --truth docs/evaluations/m8_4i_independent_rag_truth.json`；BGE 对照需另加 `--model-path` 指向其本机固定修订目录。PDF 与模型权重不在 Git 中，另一台设备须分别显式取得。

后续 M8.4j 已进一步检查同一批结果中的[答案承载短语覆盖](M8_4J_ANSWER_BEARING_EVIDENCE_VALIDATION.md)：两种模型的正确页 Top-5 虽为 `8/8`，实际答案承载片段均只有 `7/8`，因此本页命中结论不能升级为证据充分性结论。
