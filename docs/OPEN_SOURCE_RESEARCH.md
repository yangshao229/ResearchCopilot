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

## RAGFlow

- 仓库：https://github.com/infiniflow/ragflow
- 定位：面向复杂文档理解的完整 RAG 系统。
- 值得借鉴：可视化检查切分结果、人工修正文本块、使用固定 Embedding 空间、在生成回答前进行检索测试。
- 当前决定：不部署其多服务系统。等简单 PDF 抽取在双栏、表格、公式或扫描论文上失败时，再评估 DeepDoc 一类布局解析方案。

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
