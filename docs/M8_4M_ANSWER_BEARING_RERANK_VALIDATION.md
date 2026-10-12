# M8.4m：答案承载重排与拒答分离验收

日期：2026-10-08。状态：**离线影子对照，不改变生产检索或回答**。

设计依据：[答案承载重排与拒答分离拆解](research/2026-10-08-answer-bearing-rerank-abstention.md)。本轮把 M8.4h 的 12 条 LoRA、Transformer、BERT 中英正例与 M8.4e/M8.4g 的 6 条中英无答案题合并为[冻结账本](evaluations/m8_4m_answer_bearing_rerank_truth.json)。正例沿用 M8.4l 人工核对的必要原文短语，且所有必要事实必须在同一 PDF 页共同出现；账本绑定三篇 PDF 的 SHA-256。

## 固定前 30 候选、前 5 预算结果

| 指标 | 混合检索 | mMARCO | BGE |
| --- | ---: | ---: | ---: |
| 正确页进入 Top-5（12 条正例） | 8/12 | 11/12 | 12/12 |
| 同页答案承载短语完整 Top-5 | 5/12 | 11/12 | 12/12 |
| 同页答案承载短语完整 Top-1 | 1/12 | 2/12 | 8/12 |
| 每页只留一片段后的短语完整 Top-5 | — | 10/12 | 10/12 |
| 本机 CPU 单题重排中位耗时 | — | 约 1.01 秒 | 约 4.94 秒 |

三篇论文的 12 条正例在前 30 候选中都已有完整答案短语，所以这批失败主要是排序问题。mMARCO 只剩中文 Transformer 缩放题失败，分论文为 LoRA `4/4`、Transformer `3/4`、BERT `4/4`；BGE 为三篇各 `4/4`。按语言看，mMARCO 英文 `6/6`、中文 `5/6`，BGE 中英文均 `6/6`。

BGE 在这组**已参与此前模型比较的三篇论文**上达到 `12/12`，不是新论文泛化证据。其 CPU 中位延迟约为 mMARCO 的 4.9 倍，而且 M8.4h 已记录它在另一组旧困难题上回退，不能挑选本轮有利账本替换生产检索。两种模型按页去重后都降至 `10/12`，再次说明同页多个互补片段不能被简单压成一条。

## 无答案题与分数重叠

| 模型 | 正例最高候选分数下界 | 负例最高候选分数上界 | 单一阈值可分离 |
| --- | ---: | ---: | --- |
| mMARCO | `0.5208` | `1.6792` | 否 |
| BGE | `0.0952` | `0.4156` | 否 |

两种模型的 6 条无答案题最高分都与正例区间重叠。mMARCO 的最高负例来自中文 LoRA 量子纠缠题，BGE 的最高负例来自英文 BERT ImageNet 题；因此不能选择一个统一分数阈值，在保住全部正例的同时拒绝全部负例。重排覆盖改善不等于无答案能力成立，输出中的 `no_answer_abstention_supported` 继续为 `false`。

## 安全、兼容与失败边界

- 两个模型读取完全相同的混合检索前 30 候选；没有调候选权重、模型或真值。
- 必要短语必须在同一 PDF 页的 Top-k 片段内共同出现；跨页各取一半不会计为完整证据。
- 字符串覆盖仍不能证明关系理解、生成答案或引用忠实；6 条负例也不足以训练或校准拒答器。
- 只读取本机公开 PDF、E5 与固定模型缓存；未联网下载模型、调用 DeepSeek、修改论文、阅读记录、翻译缓存或真实 Vault。
- macOS 完成实测；Windows 尚未实机验证。两种模型仍只属于离线候选。

## 自动回归与决策

新增汇总回归覆盖正负分数分离、分数重叠、缺少负例时的兼容行为；答案覆盖新增可选的同页一致性约束。完整 Python 测试 `210 passed`，前端 TypeScript 与生产构建通过，只有既有依赖弃用与大分块提示；`git diff --check` 通过。

**决策：不接入任一重排器，不以分数阈值实现拒答。** 本轮证明“若完整答案片段已经进入前 30，BGE 可以在这 12 条旧问题中将其全部排入前 5”，但同时证明它更慢且分数无法拒答。下一步必须在未参与本轮选择的新论文上复核答案承载排序，并把生成阶段的证据不足／拒答验收与检索排名分开。

复现：

```bash
.venv/bin/python scripts/evaluate_reranker.py \
  --truth docs/evaluations/m8_4m_answer_bearing_rerank_truth.json

.venv/bin/python scripts/evaluate_reranker.py \
  --truth docs/evaluations/m8_4m_answer_bearing_rerank_truth.json \
  --model-path data/model_cache/models--BAAI--bge-reranker-v2-m3/snapshots/953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e
```
