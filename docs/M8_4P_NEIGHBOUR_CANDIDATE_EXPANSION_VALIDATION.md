# M8.4p：同页邻居候选扩展影子验收

日期：2026-10-08。状态：**失败性离线实验，不改变生产切分、检索、重排或用户可见证据**。

设计依据见[同页邻居候选扩展开源拆解](research/2026-10-08-neighbour-candidate-expansion-shadow.md)。本轮承接 M8.4o 的“页对、片段错”失败，不再把邻居文本直接拼进 Top-5，而是把原混合检索 Top-30 的同页前／后相邻块加入内部候选，再由较快的固定 mMARCO 重排，最终仍只保留 5 条独立原文片段。BGE 在 M8.4n 的 Top-5 完整率与 mMARCO 相同、CPU 中位延迟约高 8.3 倍，本轮不重复扩大其候选池。

## 独立 RAG 论文结果

账本复用 M8.4i 的固定论文与问题，并以新的[同页事实账本](evaluations/m8_4p_candidate_expansion_support_spans.json)锁定 M8.4n 的 18 个必要事实组。

| 内部候选池 | 候选事实完整 | 重排后 Top-5 完整 | 平均候选数 | CPU 中位重排 |
| --- | ---: | ---: | ---: | ---: |
| 原 Top-30 | 7/8 | 7/8 | 30 | 约 0.60 秒 |
| 每个命中加前一个同页块 | 8/8 | 7/8 | 41 | 约 0.86 秒 |
| 每个命中加后一个同页块 | 8/8 | 7/8 | 42 | 约 0.79 秒 |
| 前后各加一个同页块 | 8/8 | 7/8 | 49 | 约 0.99 秒 |

三个扩展方向都把中文快速解码题所需事实带进了内部候选，证明相邻关系可以修复第一阶段缺失；但 mMARCO 没有把新增答案片段排入最终 Top-5，用户可见覆盖仍为 `7/8`。候选数增加约 37%–63%，中位重排耗时增加约 31%–64%，却没有产生 Top-5 收益。

## 旧三论文困难集复核

为避免只围绕一题调参，本轮同时使用 M8.4g 的 6 条中英正例与 3 条中文无答案题，并以 M8.4o 的[问题对齐事实账本](evaluations/m8_4m_hard_set_support_spans.json)绑定三篇 PDF 哈希。

| 内部候选池 | 候选事实完整 | 重排后 Top-5 完整 | 平均候选数 | CPU 中位重排 |
| --- | ---: | ---: | ---: | ---: |
| 原 Top-30 | 3/6 | 0/6 | 30 | 约 0.61 秒 |
| 加前一个同页块 | 5/6 | 0/6 | 38 | 约 0.75 秒 |
| 加后一个同页块 | 4/6 | 0/6 | 41 | 约 0.85 秒 |
| 前后各加一个同页块 | 5/6 | 0/6 | 47 | 约 0.94 秒 |

旧困难集再次显示“候选池里有事实”不等于“重排后 Top-5 含事实”。所有方向都没有改善最终覆盖，也没有消除正负最高分重叠。该账本的字符串事实只用于诊断，不能当作最终答案准确率。

## 实现与安全边界

- 新增纯函数只按 `(source_page, chunk_index)` 查找前后邻居；原片段文本不匹配、邻居缺失或跨页时拒绝／跳过。
- 原候选保持顺序与元数据，邻居仍是独立片段；最终 Top-5 数量、页码和片段索引均可核查，不拼接窗口文本。
- 离线脚本报告每种方向的候选事实覆盖、Top-5 覆盖、候选数、重排耗时和正负分数区间。
- 新增回归覆盖同页边界、稳定去重、原命中保持、陈旧文本拒绝和非法参数。
- 只读取本机公开 PDF 与固定模型缓存；未调用 DeepSeek，未修改论文、阅读记录、翻译缓存或真实 Vault。

## 决策

**不接入同页邻居候选扩展。** 它解决了独立失败题的候选池缺失，却没有解决最终排序，并在独立论文和旧困难集上都增加候选数与延迟而不提高 Top-5。后续不再围绕同一小账本扩大窗口或候选池；生成阶段的证据不足／拒答另设独立验收，任何检索策略升级须先取得更多不同结构论文的人工事实真值。

复现：

```bash
.venv/bin/python scripts/evaluate_context_window.py \
  --support docs/evaluations/m8_4p_candidate_expansion_support_spans.json \
  --reranker-model data/model_cache/models--cross-encoder--mmarco-mMiniLMv2-L12-H384-v1/snapshots/1427fd652930e4ba29e8149678df786c240d8825

.venv/bin/python scripts/evaluate_context_window.py \
  --truth docs/evaluations/m8_4g_matched_language_truth.json \
  --support docs/evaluations/m8_4m_hard_set_support_spans.json \
  --reranker-model data/model_cache/models--cross-encoder--mmarco-mMiniLMv2-L12-H384-v1/snapshots/1427fd652930e4ba29e8149678df786c240d8825
```
