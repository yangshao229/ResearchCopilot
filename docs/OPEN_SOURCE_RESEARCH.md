# 开源项目调研与技术取舍

调研日期：2026-09-20

本项目优先帮助学习者读懂 AI 论文。以下项目用于学习设计思想，不直接把大型成品系统整体嵌入 ResearchCopilot。

## PaperQA2

- 仓库：https://github.com/Future-House/paper-qa
- 定位：面向科学文献的高准确率、带引用的 Agentic RAG。
- 值得借鉴：元数据感知 Embedding、证据检索、LLM 重排序、上下文摘要、答案内引用、本地论文仓库搜索和 LitQA 评测思路。
- 当前决定：把它作为最重要的算法与评测参考，但不直接添加为依赖。ResearchCopilot 先自己实现透明的关键词、Embedding、重排序和引用流程，确保学习者理解每层机制。

## Open Notebook

- 仓库：https://github.com/lfnovo/open-notebook
- 定位：强调隐私和模型可选性的研究笔记系统，组织 notebooks、sources 和 notes，并提供语义搜索与对话。
- 值得借鉴：把原始来源、AI 生成内容和人工笔记分开；允许本地或云端模型；围绕资料集合组织对话。
- 当前决定：借鉴资源组织模型，不部署其 Docker、数据库和完整服务。Markdown/PDF 继续作为 ResearchCopilot 的核心资料。

## 面向深度阅读的本地 PDF 工作台

### pdfpal

- 仓库：https://github.com/andrepaim/pdfpal
- 值得借鉴：可调整大小的 PDF/聊天分栏；记住每篇论文的阅读进度；选中文字后提问或高亮；每篇论文独立保存对话；项目、论文集合和 Markdown 笔记共享同一套核心接口。
- 当前决定：采用“人读原文、AI 在旁辅助”的产品原则，以及阅读进度、论文级会话和选区提问设计。暂不照搬其 Node.js 服务和依赖外部 Agent CLI 的调用方式。

### Paperview 与 Zotero AI Explain

- Paperview：https://github.com/Carstenhanekamp/Paperview
- Zotero AI Explain：https://github.com/vishnutskumar/zotero-ai-explain
- 值得借鉴：使用 PDF.js 在浏览器显示本地 PDF；引用不仅显示页码，还可以点击并跳转到对应页面；当前 PDF 的提问只检索当前论文，资料库提问才跨论文检索；每个文本块必须携带来源页码。
- 当前决定：第一版网页阅读器优先采用 PDF.js 思路；明确区分“当前论文问答”和“跨论文问答”。页码引用设计成可操作的导航对象，而不是答案末尾的一段普通文字。

### Annot

- 仓库：https://github.com/rkka02/Annot
- 值得借鉴：高亮可以附个人备注；论文会话与文件夹会话分开；从完整问答历史生成逐轮总结；总结和高亮导出为 Markdown 前先预览、再由人确认。
- 当前决定：先实现论文级会话和“选择有价值的问答生成总结”，再实现文件夹级跨论文会话。AI 总结永远以草稿保存，不自动覆盖个人笔记。

### AI Notebook 与 nano-NotebookLM

- AI Notebook：https://github.com/lukoplt/AI-notebook
- nano-NotebookLM：https://github.com/ArthurYangX/nano-NotebookLM
- 值得借鉴：把语义检索与关键词检索融合；将 AI 回答保存成可编辑笔记；用点击式引用返回 PDF；将论文原文证据与外部补充知识分开呈现；API 提供商与 Embedding 模型可以独立替换。
- 当前决定：在语义检索基线之后加入关键词与向量结果融合，而不是只依赖单一向量相似度。第一版不做知识图谱、测验和复杂数据库，避免偏离论文阅读主线。

## 阅读界面取舍

调研后的第一版产品流程为：

```text
本地论文列表
    ↓
PDF 阅读器 + 论文级提问侧栏
    ↓
选择原文 / 输入问题
    ↓
混合检索与重排序
    ↓
基于证据的解释 + 可点击页码引用
    ↓
人工选择值得保留的问答
    ↓
可编辑的阅读总结 / Markdown 论文卡片
```

不在第一版实现：知识图谱、自动播客、团队协作、复杂账户系统和 Windows 论文复现。这些功能只有在核心阅读闭环稳定后再评估。

## RAGFlow

- 仓库：https://github.com/infiniflow/ragflow
- 定位：面向复杂文档理解的完整 RAG 系统。
- 值得借鉴：可视化检查切分结果、人工修正文本块、使用固定 Embedding 空间、在生成回答前进行检索测试。
- 当前决定：不部署其多服务系统。等简单 PDF 抽取在双栏、表格、公式或扫描论文上失败时，再评估 DeepDoc 一类布局解析方案。

## Zotero、Sioyek 与 Paperlib

- Zotero PDF 阅读器：https://github.com/zotero/zotero-docs/blob/main/content/pdf_reader.md
- Sioyek：https://github.com/joshpwn/sioyek-pdf-reader
- Paperlib：https://github.com/Future-Scholars/paperlib
- 值得借鉴：Zotero 将高亮拖入笔记并保留回到原文的链接；Sioyek 针对论文中的图表和参考文献提供快速跳转；Paperlib 使用集合、标签、评分、旗标、全文搜索和元数据抓取管理长期论文库。
- 当前决定：单篇阅读阶段优先实现高亮到笔记和引用回跳。集合、标签、评分和相关论文管理放在阅读闭环之后；图表与参考文献智能跳转作为第二阶段阅读增强。

## Docling 与 Marker

- Docling：https://github.com/docling-project/docling
- Marker：https://github.com/datalab-to/marker
- 定位：处理双栏、表格、公式、图片和扫描件等复杂文档，输出结构化 JSON 或 Markdown。
- 当前决定：继续保留当前轻量分页抽取作为快速基线，并增加解析质量检测。只有普通抽取失败时才按需使用布局感知解析或 OCR，避免所有论文都承担较重的模型和依赖成本。

## LitQA

- 仓库：https://github.com/Future-House/LitQA
- 值得借鉴：评测问题应依赖论文全文中的具体细节，不能只靠摘要回答；参考答案和来源论文要经过人工检查。
- 当前决定：为真实 AI 论文建立小型人工问题集，分别测量解析、检索、引用和回答，而不是只用“看起来回答不错”判断系统质量。

## DVC 与 MLflow

- DVC：https://github.com/iterative/dvc
- MLflow：https://github.com/mlflow/mlflow
- 定位：大文件、数据、流水线和实验的版本管理与追踪。
- 当前决定：暂不引入。只有开始在 Windows/CUDA 上复现具体论文，并产生多个数据集、模型和实验运行后再评估。当前继续用 Git 保存代码、配置和小型评测结果。

## 第一版 Embedding 选择

- 模型：https://huggingface.co/intfloat/multilingual-e5-small
- 原因：支持中文问题到英文论文的跨语言检索；模型权重约 471 MB；384 维向量；适合 MacBook 本地运行。
- 使用约定：问题添加 `query: ` 前缀，论文片段添加 `passage: ` 前缀，并对向量归一化。
- 已知限制：输入最多 512 tokens，因此必须保留文本切分；绝对相似度不是置信度，主要比较同一次检索中的相对排序。

## 当前架构结论

```text
PDF / Markdown
      ↓
带页码的结构化文本
      ↓
可比较的切分策略
      ↓
关键词检索 + 多语种 Embedding 检索
      ↓
证据重排序与原文页码
      ↓
基于证据的解释和问答
      ↓
待人工确认的论文卡片与跨论文知识连接
```

Windows 复现是后续按论文触发的支线，不改变当前阅读主线。
