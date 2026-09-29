# M7.1 逐页解析质量关卡：开源产品拆解

检索日期：2026-09-29。

## 用户问题

英语论文的 PDF 文本层可能缺字、乱码，或与页面视觉顺序不同。直接把它送给翻译模型，会得到貌似流畅却不忠于原文的译文。用户需要在花费 API 费用前知道当前页是否适合机器翻译，以及何时应改用划词阅读。

## 参考项目与一手资料

| 项目 | 官方资料 | 交互、数据与处理流程 | 许可证与成本 |
| --- | --- | --- | --- |
| [Docling](https://github.com/docling-project/docling) | [统一文档模型](https://github.com/docling-project/docling/blob/main/docs/concepts/docling_document.md)、[PDF 流水线](https://github.com/docling-project/docling/blob/main/docling/pipeline/standard_pdf_pipeline.py)、[配置与许可](https://github.com/docling-project/docling/blob/main/pyproject.toml) | 文本、表格、图片分别成对象，保留页面框、出处和阅读顺序；布局、OCR、表格、阅读顺序是可区分的阶段。失败不应伪装成可靠正文。 | MIT；完整流水线需要模型和运行资源。 |
| [Marker](https://github.com/datalab-to/marker) | [README 的工作流程与局限](https://github.com/datalab-to/marker/blob/master/README.md) | 先用嵌入文本，逐页决定是否可用；差页才 OCR 或块级修复；公式/表格由专门处理，不假定纯文本能还原。 | 代码 Apache-2.0；模型权重有额外条款、下载和运行成本。 |
| [MinerU](https://github.com/opendatalab/MinerU) | [输出结构](https://github.com/opendatalab/MinerU/blob/master/docs/en/reference/output_files.md)、[项目说明](https://github.com/opendatalab/MinerU)、[许可证](https://github.com/opendatalab/MinerU/blob/master/LICENSE.md) | 输出正文、表格、公式及原位框；复杂页靠专用解析路径。 | 特定附加条款，依赖与模型体积大；本阶段只借鉴流程，不引入代码。 |

三者共同提示：纯文本抽取只是第一层；质量不明时先显式提示或拒绝，不能把语言模型的通顺措辞当成解析成功。

## 对 ResearchCopilot 的取舍

| 处理 | 决定 | 原因 |
| --- | --- | --- |
| 按页检查可抽取正文和损坏字符 | 借鉴 | 与现有页码、按需翻译天然一致；完全本地，零新依赖。 |
| 在用户点击翻译前显示结果 | 借鉴 | 让用户预知风险，避免无意义 API 调用。 |
| 坏页不发送 DeepSeek | 借鉴 | 不能把乱码翻译成看似可信的论文内容。 |
| 复杂版面给出保守提示，不称为精确检测 | 调整 | 现有 pypdf 不提供经过验证的阅读顺序/表格结构。 |
| 立即接入整套 Docling/Marker/MinerU | 暂拒 | 模型、许可、缓存、跨平台成本显著；需要先有质量基线和真实失败样例。 |

## 数据与隐私边界

质量检查只读本地 PDF 与既有逐页文本，不调用模型、不上传 PDF、不写新索引。返回页码、文本量和风险代码；译文仍是原有按论文隔离的缓存。使用者自己确认译文，不反向覆盖原文、证据或笔记。

## 架构影响与兼容性

沿用 `PaperSearchService.page_text` 的原文和 `PageTranslationService` 的单页入口；增设一个纯函数质量判定与轻量只读 API，不建立第二套论文/会话/翻译存储。中文或英文目标语言得到同一页质量报告；当前论文和跨论文通过 `paper_id` 隔离；会话不影响 PDF 质量；本地检测不触网，云端翻译仅在合格且用户点击后发生；pypdf 与判断逻辑须在 macOS/Windows 一致。已缓存的译文仍可查看，但展示质量风险。

## 实现顺序与验收标准

1. 对空页、少量文字、明显乱码、过长页、可抽取数学符号、正常文字给出稳定的状态和原因代码；空页/明显乱码/过长页不能发起云端翻译。数学页只提醒核对，不声称公式安全。
2. 只读 API 对有效论文和页码返回报告，对不存在的论文/页码清晰报错。
3. 译文面板在调用模型前显示风险；正常页仍可按原流程翻译，质量检查失败时提供降级提示。
4. 用真实 `sample.pdf` 页面检查结果，并运行后端测试与前端构建。

## 暂不实现

本阶段不声称能够自动修复双栏阅读顺序、行内公式、表格或扫描页，也不引入块级精确对齐。后续 M7.2 必须以保留坐标和类型的布局块为基础，而不是再次修改纯文本缓存。
