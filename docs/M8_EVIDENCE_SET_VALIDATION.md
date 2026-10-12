# M8 统一证据包：第二步

日期：2026-10-06。按[架构收敛记录](research/2026-10-06-evidence-set-consolidation.md)落实既有蓝图的 `EvidenceSet`；无新按钮、无新模型、无新的检索权重或拒答门槛。

## 本轮完成

- `EvidenceSet` 统一承载问题、来源方式、范围与按顺序编号的候选原文片段。**候选不等于足够证据**；是否回答仍留给后续独立评测。
- “只查原文证据”与“生成带引用回答”现在使用 `PaperAnswerService.collect_evidence()` 同一条收集路径。选区翻译仍只使用选中的原文，不触发全文搜索。
- 模型可以返回证据编号，但引文文字、PDF 页码和 PDF 版本来源由证据包从真实候选生成。重复编号合并，未知编号忽略；若没有一条有效引用，既有失败关闭逻辑继续生效。
- 已有来源锚点若与当前 `paper_uid + pdf_sha256 + PDF 页码` 冲突，拒绝把候选重新标成当前 PDF。
- HTTP 响应、阅读记录与网页交互保持兼容；跨论文端点仍只收集候选，不产生比较答案。

## 文件与验证

- 核心改动：`src/research_copilot/domain.py`、`paper_answer_service.py`、`reading_service.py`、`web_app.py`。
- 新增回归：`tests/test_evidence_set.py`，覆盖编号约束、去重与真实短引、选区绕过检索、跨 PDF 版本拒绝；现有 API、翻译缓存和引用测试保持通过。
- Python 全量测试：`194 passed`，只有两条既有测试依赖弃用警告。前端 TypeScript 和生产构建通过；仍有原有的大分块提示。
- 未调用 DeepSeek、联网下载模型，也未修改真实论文、阅读历史、译文缓存或 Vault；保留工作树中其他未提交变更，未提交 Git。

## 尚未解决

本阶段结束时，两个 HTTP 动作仍会各自检索；这个请求间漂移已在下一阶段用[已查看证据快照](M8_EVIDENCE_SNAPSHOT_VALIDATION.md)失败关闭。无答案题的充分性判断仍须用独立真值测量，不能把 `EvidenceSet` 或快照令牌的存在当作质量改善。
