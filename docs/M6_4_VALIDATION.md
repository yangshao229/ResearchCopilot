# M6.4 章节感知检索验收

日期：2026-09-25

## 设计依据

章节检索在编码前完成开源产品拆解：[章节感知检索](research/2026-09-25-section-aware-retrieval.md)。主要借鉴 Docling 的结构优先分块、SkimRead 按章节边界处理长文档、PaperQA 的证据收集与范围控制。

## 实现

- 对话问题中出现编号章节（如 `1.1 节`、`section 3.2.1`）时，按编号和目录匹配。
- “总结 Results”一类表述在有唯一标题匹配时可识别目标章节。
- 章节从标题起始 PDF 页开始，到下一同级或更高级标题的前一页结束。
- 关键词、语义和混合检索共用现有检索器，只在分块前筛选页码。
- 问答结果、阅读历史和单条 Markdown 草稿保存实际范围。
- 阅读界面展示有效范围，章节无命中时提供“改为全文检索”。
- 用户可以在提问框选择自动识别章节或全文。
- 标题不存在、同名标题、书签页码越界、同页相邻章节无法分隔时回退全文并说明。
- Search API 仍返回原有数组 JSON；范围状态通过可选的 `X-Reading-Scope` 响应头提供，旧客户端可以忽略。

## 自动验收

- `tests/test_section_scope.py` 覆盖编号子章节、标题名识别、无效/歧义标题、同页边界与手动全文。
- `tests/test_paper_search.py` 覆盖检索限定到指定 PDF 页范围。
- 完整后端测试：`76 passed`，2 条来自 Starlette/httpx 的弃用警告。
- 前端 TypeScript 类型检查与生产构建通过；Vite 仍报告包含 PDF.js 的 JS chunk 超过 500 kB。
- `git diff --check` 通过。

## 三篇真实论文检查（2026-09-25）

验收使用仓库现有 `data/raw/sample.pdf`（*Attention Is All You Need*），另从 arXiv 临时获取 *LoRA: Low-Rank Adaptation of Large Language Models*（<https://arxiv.org/abs/2106.09685>）和 *BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding*（<https://arxiv.org/abs/1810.04805>）。两篇外部 PDF 只放在 `/tmp` 临时目录，未加入 `data/raw`、未进入 Git，也没有调用 DeepSeek。

| 论文 | 结构来源 | 固定章节问题 | 识别结果 | 检索页码检查 |
| --- | --- | --- | --- | --- |
| Attention Is All You Need | PDF 书签，22 标题，15 页 | `解释 Model Architecture 章节` | 第 2–5 页 | 10 条结果均在第 2–5 页 |
| LoRA | PDF 书签，37 标题，26 页 | `解释 4 Our Method 章节` | 第 4 页 | 命中结果在第 4 页 |
| BERT | 文本规则推断，31 标题，16 页 | `Summarize 3.1 Pre-training BERT` | 第 4 页 | 5 条结果均在第 4 页 |

失败路径也进行了真实结构检查：不存在的章节名称（`Summarize a nonexistent section`、`Explain section 99.7`）会产生带原因的全文回退；只提到泛化标题 `Results` 时不会强行误认 BERT 的多个 Results 类标题。全文模式相关的检索算法自动测试仍通过。

固定评测脚本的实时 MRR/Recall 重跑未完成：当前执行环境不能访问 Hugging Face，且该环境没有所需的 Embedding 模型缓存。此前记录的 M4 基线为 Recall@5 `1.00`、混合检索 MRR `1.00`；本次未将旧记录冒充为刚刚重跑的结果。

外部 PDF 清理方式：验收完成后可删除本次 `/tmp/researchcopilot-pdf-validation.*` 目录；正式论文资料库没有新增文件。
